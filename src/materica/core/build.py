# SPDX-License-Identifier: Apache-2.0
"""The build check (`declarations.md`): a consumer's declaration checked against the records.

S7a-1 builds the declaration's own check (section 1). A declaration it refuses gives a report of its refusals
alone, and nothing is read for it.

S7a-2 builds the results over records and the verdict (section 2). `_results`: for each model, each record its
`checked_over` lists, in the order listed, and each field in its `reads`, in that order, one result. A field
with no requirement is read for nothing (section 1 item 1). Any other is read through `read` by the build's
own request (`_request`, item 7), which is given the acceptances of the kinds a read takes, overlays aside,
that name the field and are located at the record (`_given`). The acceptances applied, by the build's terms
(which define "applied" on the result), are mapped to their indexes in the model's `acceptances`
(`_applied`). The build's own reasons (`_build_reasons`, item 8) join the read's: `no_requirement` for a field
with no requirement; `label_mismatch` where the requirement names a label and the value the result rests on
stores another or none (`_stored`), and none where it rests on no stored value; `not_reviewed` where the
requirement holds `review` and the result's provenance holds no completed review, and none where it holds no
provenance. The result's status is the worst of them all, and `judge` (`core/acceptance.py`) gives its verdict
by the model's own acceptances. The report holds the records a read resolved, the results, and per model the
acceptances none of its results used.

Before any read, a declaration holding what a later piece reads raises `NotImplementedError`, naming each,
so that no answer is given that the later piece would change (the S7 design's 1.3): a pick or an overlay,
which S7c applies; a non-empty `target` or `combinations`, whose specimen differences and combinations S7a-3
gives; and a non-empty `trainable`, which S7a-4 reads. A read lets through the `NotImplementedError` it raises
itself (a checked record that is an overlay, `want: fit` on a field holding a fit record), and the verdict
raises where label trust could change a result's verdict: a waiver naming a label fits a reason, and every
reason of the result fits some acceptance (`core/acceptance.py`).
"""

import copy
from collections.abc import Collection, Sequence
from typing import cast

from materica import shapes
from materica.core.acceptance import judge, located_at, names, unused
from materica.core.conditions import said
from materica.core.declarations import (
    CLAIMS,
    Acceptance,
    Declaration,
    DeclarationInput,
    ModelEntry,
    Requirement,
    parse_declaration,
)
from materica.core.fields import RecordField, find_field
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult, read
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from materica.core.report import BuildReport, BuildResult, UnusedAcceptance
from materica.core.resolve import ResolvedRecord, resolve_record
from materica.core.status import worst
from materica.core.value_shapes import IMPLIED_BASIS, JsonObject, a_list, an_object
from materica.core.vocabulary import VOCABULARY
from materica.shapes import Suite

# The kinds of acceptance the build gives a read (section 2 item 7): of those a read takes ("A request's
# `acceptances` take only the kinds `pick`, `overlay`, `extrapolation`, `nominal`, `implied_condition` and
# `trainable`", `read_side_contract.md` section 1), overlays aside (which overlays a read is given is not
# decided yet); and the `trainable` acceptance is the one the build makes from a `trainable` entry
# (section 7), never a declaration's.
_GIVEN_KINDS = ("pick", "extrapolation", "nominal", "implied_condition")

# The kinds of acceptance a later piece applies, and that piece: the build raises for each before any read.
_APPLIED_LATER = {"pick": "S7c", "overlay": "S7c"}

# The members of a record condition's shapes an implied condition's value holds (section 4.1's row), its
# `basis` aside, which the declaration may give and nothing reads.
_IMPLIED_MEMBERS = ("value", "range", "unit", "token")

# The review result a completed review holds (section 1 item 11; `provenance.md` section 2 item 6).
_REVIEWED = "reviewed"

# A result, beside what it was judged with: the indexes, in the model's `acceptances`, of those the read
# applied (`_applied`), and the label and its basis as stored on the value the result rests on (`_stored`).
Reading = tuple[BuildResult, tuple[int, ...], JsonObject | None]


def check_build(
    declaration: DeclarationInput, store: RecordStore, *, claims: Collection[Suite] = CLAIMS
) -> BuildReport:
    """Check `declaration` against the records in `store`, as a build that claims `claims`.

    `declaration` is JSON text, a `str` or bytes-like, or a value, read as `read` reads a request. The claims
    are checked first: `ValueError` for claims no implementation makes (a suite not in the README's list, or
    claims without plain read or without the build checks). Where the build claims the scene suite, USD read
    or the sampling suite and the declaration holds a member that suite checks, it raises
    `NotImplementedError`, whatever else is wrong. A declaration that departs from its shape, or breaks a rule
    of section 1, gives a report of its refusals alone, and nothing is read. Any other gives the report of its
    results (section 2), but that it raises `NotImplementedError` in this version: before any read, naming
    each pick, overlay, `target`, `combinations` and `trainable` entry and the piece that reads it; and where
    a waiver naming a label fits a reason of a result that label trust could still accept, which S7a-2's
    label trust judges.
    """
    checked = Declaration.from_json(declaration, claims)
    if isinstance(checked, tuple):
        given: JsonValue | Reason = parse_declaration(declaration)
        return BuildReport(checked, given)
    _not_built(checked)
    results = tuple(result for result, _, _ in _results(checked, store, claims))
    resolved = (result.record for result in results if result.read is not None and result.read.resolved)
    return BuildReport(
        (),
        checked.given,
        records=tuple(dict.fromkeys(resolved)),
        results=results,
        unused=_unused(checked, results),
    )


def _not_built(declaration: Declaration) -> None:
    """Raise, before any read, for a declaration holding what a later piece reads (the S7 design's 1.3). An
    `overlay_scope` and an accepted difference raise nothing: with no overlay applied and no specimen
    difference (an empty `target` names no fact), neither covers anything."""
    named: dict[str, list[str]] = {}
    for model in declaration.models:
        at = f"/models/{model.index}"
        for acceptance in model.acceptances:
            if (piece := _APPLIED_LATER.get(acceptance.kind)) is not None:
                named.setdefault(piece, []).append(
                    f"the {acceptance.kind} {at}/acceptances/{acceptance.index}"
                )
        if model.target:
            named.setdefault("S7a-3", []).append(f"the target {at}/target")
        if model.combinations:
            named.setdefault("S7a-3", []).append(f"the combinations {at}/combinations")
        for position, _ in enumerate(a_list(model.entry.get("trainable", []))):
            named.setdefault("S7a-4", []).append(f"the trainable entry {at}/trainable/{position}")
    if named:
        listed = "; ".join(f"{piece} reads {', '.join(items)}" for piece, items in sorted(named.items()))
        raise NotImplementedError(
            "the declaration passed its own check, and this version reads none of its records while it "
            f"holds what a later piece reads: {listed}"
        )


def _results(declaration: Declaration, store: RecordStore, claims: Collection[Suite]) -> list[Reading]:
    """Section 2: one result per model, record listed in its `checked_over`, in the order listed, and field
    in its `reads`, in that order; none for a record not listed. A field with no requirement is read for
    nothing (section 1 item 1); any other gives the read of the build's own request (item 7). Each result
    holds the build's own reasons joined to the read's, the worst status of them all, and its verdict by its
    model's acceptances."""
    results: list[Reading] = []
    for model in declaration.models:
        for record in model.records:
            for field in model.reads:
                requirement = _requirement(model, field)
                result: ReadResult | None = None
                applied: tuple[int, ...] = ()
                stored: JsonObject | None = None
                if requirement is not None:
                    given = _given(model.acceptances, record, field)
                    request = _request(declaration.operating_conditions, record, requirement, given)
                    result = read(request, store, claims=claims)
                    applied = _applied(result, given)
                    stored = _stored(store, record, field, result, claims)
                own = _build_reasons(requirement, result, stored)
                reasons = (*(() if result is None else result.reasons), *own)
                status = worst(
                    (
                        *(() if result is None else (result.status,)),
                        *(VOCABULARY.reasons[r.code].status for r in own),
                    )
                )
                verdict = judge(reasons, result, record, field, model.acceptances, applied)
                built = BuildResult(
                    model.name,
                    record,
                    field,
                    result,
                    reasons,
                    status,
                    verdict.accepted,
                    verdict.accepted_by,
                    verdict.not_accepted,
                )
                results.append((built, applied, stored))
    return results


def _build_reasons(
    requirement: Requirement | None, result: ReadResult | None, stored: JsonObject | None
) -> tuple[Reason, ...]:
    """Section 2 item 8: the build's own reasons, which join the read's. `no_requirement` for a field read
    with no requirement, for which nothing is read (section 1 item 1); `label_mismatch` where the requirement
    names a label and the label stored on the value the result rests on (`stored`) differs or is absent,
    whatever else the read found, and none where the result rests on no stored value (section 1 item 5);
    `not_reviewed` where the requirement holds `review` and the result's `provenance` holds no completed
    review, one whose `result` is `reviewed`, and none where the result holds no `provenance` (item 11)."""
    if requirement is None:
        return (
            Reason("no_requirement", detail="the model reads the field and declares no requirement for it"),
        )
    assert result is not None, "a field with a requirement is read"
    found: list[Reason] = []
    if requirement.label is not None and stored is not None and stored.get("label") != requirement.label:
        held = f"the label {stored['label']!r}" if "label" in stored else "no label"
        found.append(
            Reason(
                "label_mismatch",
                detail=f"the requirement names the label {requirement.label!r}; the value read stores {held}",
            )
        )
    if (
        requirement.reviewed
        and result.provenance is not None
        and result.provenance.review.get("result") != _REVIEWED
    ):
        found.append(
            Reason(
                "not_reviewed",
                detail="the requirement needs a reviewed value; the value's review is not completed",
            )
        )
    return tuple(found)


def _unused(declaration: Declaration, results: Sequence[BuildResult]) -> tuple[UnusedAcceptance, ...]:
    """Section 2 item 9: per model, in the order declared, each of its acceptances none of its own results
    used."""
    return tuple(
        found
        for model in declaration.models
        for found in unused(model, (result.accepted_by for result in results if result.model == model.name))
    )


def _requirement(model: ModelEntry, field: str) -> Requirement | None:
    """The model's requirement for `field`, of which there is at most one (section 1), or None."""
    return next((requirement for requirement in model.requirements if requirement.field == field), None)


def _given(acceptances: Sequence[Acceptance], record: MaterialRef, field: str) -> tuple[Acceptance, ...]:
    """Section 2 item 7: the acceptances, in the order the model lists them, of the kinds the build gives a
    read (`_GIVEN_KINDS`), that name the read's field and are located at its record."""
    return tuple(
        acceptance
        for acceptance in acceptances
        if acceptance.kind in _GIVEN_KINDS and acceptance.field == field and located_at(acceptance, record)
    )


def _request(
    operating_conditions: shapes.OperatingConditions,
    record: MaterialRef,
    requirement: Requirement,
    given: Sequence[Acceptance],
) -> shapes.ReadRequest:
    """Section 2 item 7: the build's own read request for the requirement's field at `record`. It holds the
    requirement's `want` and `conditions`, and no other member of the requirement (a read refuses its `label`
    and `review`); the declared operating conditions, each of them, whether or not the requirement names it;
    and the acceptances `given`, each as declared, in that order."""
    return {
        "target": {"record": record.to_json(), "field": requirement.field},
        "operating_conditions": cast(
            dict[str, shapes.OperatingCondition], copy.deepcopy(dict(operating_conditions))
        ),
        "requirement": {
            "want": requirement.want,
            "conditions": cast(dict[str, shapes.RequirementCondition], copy.deepcopy(requirement.conditions)),
        },
        "acceptances": [cast(shapes.Acceptance, copy.deepcopy(acceptance.members)) for acceptance in given],
    }


def _applied(result: ReadResult, given: Sequence[Acceptance]) -> tuple[int, ...]:
    """The indexes, in the model's `acceptances`, of the acceptances given to the read that it applied. The
    build's terms define "applied" on the result alone (`declarations.md` section 2: "A read **applied** an
    acceptance given to it where its result shows it"), so an acceptance given is applied wherever the result
    shows it (`_shown`), whether or not the read itself named it in `result.applied`: of two implied
    conditions of one value, each is applied once an entry shows that value, though only one may state a token
    the field's specimen states."""
    return tuple(sorted({acceptance.index for acceptance in given if _shown(acceptance, result)}))


def _shown(acceptance: Acceptance, result: ReadResult) -> bool:
    """The build's terms (section 2): a read applied an implied condition that filled a condition (a
    `conditions` entry whose `record` is the value the implied condition supplies, with basis `implied`), and
    a nominal or an extrapolation that the result's `assumption` names. No other kind given to a read in this
    version is shown applied: a pick raises before any read (S7c)."""
    if acceptance.kind == "implied_condition":
        filled = {entry.name: entry.record for entry in result.conditions or ()}
        implies = an_object(acceptance.members["implies"])
        return any(_fills(filled.get(name), an_object(value)) for name, value in implies.items())
    if acceptance.kind in ("nominal", "extrapolation"):
        return names(cast(JsonObject | None, result.assumption), acceptance)
    return False


def _fills(entry: JsonObject | None, implied: JsonObject) -> bool:
    """Whether the condition `entry` is what `implied` supplies, its numbers bit for bit as the read compares
    two implied values (`read_side_contract.md` section 1), so that `-0` is no `0`."""
    return entry is not None and entry == _supplied(implied) and said(entry) == said(implied)


def _supplied(implied: JsonObject) -> JsonObject:
    """The condition an implied condition's value fills, as the record would state it with the basis
    `implied` (section 4.1's row)."""
    return {
        **{name: implied[name] for name in _IMPLIED_MEMBERS if name in implied},
        "basis": IMPLIED_BASIS,
    }


def _stored(
    store: RecordStore, record: MaterialRef, field: str, result: ReadResult, claims: Collection[Suite]
) -> JsonObject | None:
    """The `label` and `label_basis`, each where stored, on the value the result rests on (section 2 item 8):
    the field, or the alternative read (`ReadResult.resting_on`), read from the record as stored in `store`,
    never from the result, whose labels a read that ends before step 12 leaves out; None where the result
    rests on no stored value."""
    if result.resting_on is None:
        return None
    resolved = resolve_record(record, store, claims)
    assert isinstance(resolved, ResolvedRecord), "a result resting on a stored value resolved its record"
    found = find_field(resolved.record.value, VOCABULARY.fields[field])
    assert isinstance(found, RecordField), "a result resting on a stored value found its field"
    value = found.value
    for index in result.resting_on:
        value = a_list(an_object(value)["alternatives"])[index]
    held = value if isinstance(value, dict) else {}
    return {name: copy.deepcopy(held[name]) for name in ("label", "label_basis") if name in held}
