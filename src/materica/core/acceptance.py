# SPDX-License-Identifier: Apache-2.0
"""What accepts which reason (`declarations.md` section 4.2), and the build's verdict on a result by the
build's terms (section 2).

`COVERAGE` is section 4.2's table, row by row, as `scripts/gen_vocabulary.py` reads it into
`schema/0.1/vocabulary/coverage.json`: the codes each row covers and the rule of what covers them. A reason no
row lists is never accepted.

`judge` gives a result's verdict (section 2 item 4). An acceptance covers a reason of a result where it names
the result's field, is located at the result's record (`located_at`), and is of the kind a row listing the
reason names, under that row's own condition, whatever the reason's `alternative` (`_covers`). The result is
accepted where every reason is covered; `accepted_by` holds every acceptance used for it, each that covered a
reason and each the read applied; `not_accepted` each reason nothing covers. `unused` lists, per model, each
acceptance none of that model's results used (item 9).

A waiver naming a `label` covers only where the stored label is that label and is trusted (section 4.1 item
4), which this version does not judge. `judge` raises `NotImplementedError`, naming S7a-2's label trust, which
comes after 0.1.0.dev4 (maintainer, 2026-10-21), where label trust could change the result's verdict: such a
waiver fits a reason, and every reason of the result fits some acceptance. Where one fits none, the result is
refused whatever label trust says: `accepted` is final, and `accepted_by`, `not_accepted` and the unused list
are those of a judgement that does not trust the label.
Rows no acceptance here can meet are never reached: a `pick` raises before any read (S7c), an
`overlay_scope` names no field, and no declared acceptance is the `trainable` one section 7 gives (S7a-4).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import NoReturn, cast

from materica.core.declarations import Acceptance, ModelEntry
from materica.core.identifiers import MaterialRef
from materica.core.read import ReadResult
from materica.core.reasons import Reason
from materica.core.report import UnusedAcceptance
from materica.core.value_shapes import JsonObject
from materica.core.vocabulary import VOCABULARY, CoverageRow

COVERAGE: tuple[CoverageRow, ...] = VOCABULARY.coverage

# The members that place an acceptance at a region or an interval, never at a record.
_ELSEWHERE = frozenset({"region", "interval"})


@dataclass(frozen=True)
class Judgement:
    """A result's verdict (section 2 item 4): whether it is accepted, the indexes, in the model's
    `acceptances`, of every acceptance used for it, and each reason nothing covers."""

    accepted: bool
    accepted_by: tuple[int, ...]
    not_accepted: tuple[Reason, ...]


def judge(
    reasons: Sequence[Reason],
    read: ReadResult | None,
    record: MaterialRef,
    field: str,
    acceptances: Sequence[Acceptance],
    applied: Iterable[int],
) -> Judgement:
    """The verdict on the result of `field` at `record` that holds `reasons`, the read's and the build's own,
    and `read`'s other members, by the model's `acceptances`, of which those at `applied` the read applied."""
    used = set(applied)
    not_accepted: list[Reason] = []
    waiting: list[Acceptance] = []
    fitted = True
    for reason in reasons:
        fitting = [
            acceptance for acceptance in acceptances if _covers(acceptance, reason, read, record, field)
        ]
        covering = [acceptance for acceptance in fitting if "label" not in acceptance.members]
        waiting += [acceptance for acceptance in fitting if "label" in acceptance.members]
        used.update(acceptance.index for acceptance in covering)
        if not covering:
            not_accepted.append(reason)
        fitted &= bool(fitting)
    if waiting and fitted:
        _label_rests(waiting[0])
    return Judgement(not not_accepted, tuple(sorted(used)), tuple(not_accepted))


def unused(model: ModelEntry, accepted_by: Iterable[Sequence[int]]) -> tuple[UnusedAcceptance, ...]:
    """Section 2 item 9: each acceptance of `model` that none of its results used, given the `accepted_by` of
    each of its results, in the order the model lists them."""
    used = {index for indexes in accepted_by for index in indexes}
    return tuple(
        UnusedAcceptance(model.name, acceptance.index)
        for acceptance in model.acceptances
        if acceptance.index not in used
    )


def names(assumption: JsonObject | None, acceptance: Acceptance) -> bool:
    """Whether a result's `assumption` names `acceptance`: the declaration the value rests on, its kind and
    its kind's own members as the request gave them (`read_side_contract.md` section 2)."""
    return assumption is not None and all(
        acceptance.members.get(name) == value for name, value in assumption.items()
    )


def located_at(acceptance: Acceptance, record: MaterialRef) -> bool:
    """The build's terms (section 2): an acceptance is located at a result's record where it names that
    record, equal in `id`, `version` and `content_hash`; one located at a region or an interval is located at
    no record; and an accepted difference with no location is located at every location its model is checked
    over, among which is every record it has a result at."""
    if _ELSEWHERE & acceptance.members.keys():
        return False
    if acceptance.location is None:
        return acceptance.kind == "accepted_difference"
    return acceptance.location == record


def _covers(
    acceptance: Acceptance, reason: Reason, read: ReadResult | None, record: MaterialRef, field: str
) -> bool:
    """The build's terms (section 2): `acceptance` covers `reason` where it names the result's field, is
    located at its record, and is of the kind a row of section 4.2 listing the reason names, under that row's
    own condition. A waiver naming a label also needs the label trusted (section 4.1 item 4), which `judge`
    decides."""
    if acceptance.field != field or not located_at(acceptance, record):
        return False
    rows = (row for row in COVERAGE if reason.code in row.reasons and row.kind == acceptance.kind)
    return any(_under(row, acceptance, reason, read) for row in rows)


def _under(row: CoverageRow, acceptance: Acceptance, reason: Reason, read: ReadResult | None) -> bool:
    """Whether `acceptance` meets `row`'s own condition for `reason`: the code and the condition it names,
    and the result's `assumption` naming it."""
    members = acceptance.members
    assumption = None if read is None else cast(JsonObject | None, read.assumption)
    return (
        (not row.names_code or members.get("code") == reason.code)
        and (not row.names_condition or members.get("condition") == reason.condition)
        and (not row.on_assumption or names(assumption, acceptance))
    )


def _label_rests(waiver: Acceptance) -> NoReturn:
    """Section 4.1 item 4: a waiver naming a label covers only on a result whose stored label is that label
    and is trusted. Not judged before S7a-2's label trust (maintainer, 2026-10-21)."""
    raise NotImplementedError(
        f"the waiver /acceptances/{waiver.index} names the label {waiver.members['label']!r}, and would "
        "cover a reason only where that label is trusted (declarations.md section 4.1 item 4): S7a-2's label "
        "trust, after 0.1.0.dev4, judges it"
    )
