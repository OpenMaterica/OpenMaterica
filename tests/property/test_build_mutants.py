# SPDX-License-Identifier: Apache-2.0
"""Mutants of the build's results and verdict (`core/acceptance.py`, `core/build.py`, `core/report.py`, and
the read's `resting_on` where the build reads it), each with one fault, and the part of HP43 to HP46
(`test_build_properties.py`) that must kill it: the S7 design's mutants of HP43 to HP46 (its section 6.5),
the five the review of S7-cases-2 added (R01 to R03, R05, R07), and those the reviews of S7a-2a, S7a-2b and
S7a-2m left to these properties. As in the other mutant modules, each must die within the examples the `ci`
profile gives a property, at both sizes, at an example of a way it names, and at the assertion it names, and
records the examples its kill took as `examples_to_kill`.

A fault is injected where the build looks a name up when it runs: a module-level function or table of
`acceptance` (`judge`, `_covers`, `_under`, `located_at`, `COVERAGE`) or `build` (`_results`, `_request`,
`_given`, `_applied`, `_shown`, `_fills`, `_IMPLIED_MEMBERS`, `_stored`, `_build_reasons`, `_unused`,
`_requirement`, and the names it imports, `judge`, `located_at`, `read` and `BuildResult`), the vocabulary's
reason table, or `BuildReport.refused`.

Not here: HP45's `_trusted` and `_label_rests` mutants (an inferred basis trusted, a stated one not, the basis
read from the read result; review and label presence not checked), which wait for label trust, after
0.1.0.dev4 (maintainer, 2026-10-21).
"""

import dataclasses
import re
from collections.abc import Callable, Sequence
from typing import Any, NamedTuple, cast

import pytest
from hypothesis import strategies as st

from materica.core import acceptance, build
from materica.core.acceptance import Judgement
from materica.core.declarations import CLAIMS, Acceptance, Declaration, ModelEntry, Requirement
from materica.core.identifiers import MaterialRef
from materica.core.read import ReadResult, read
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from materica.core.report import BuildReport, BuildResult, UnusedAcceptance
from materica.core.resolve import ResolvedRecord, resolve_record
from materica.core.value_shapes import JsonObject
from materica.core.vocabulary import VOCABULARY, CoverageRow
from tests.property import build_strategies as strategies
from tests.property import test_build_properties as properties
from tests.property.strategies import ORIGINAL, SMALL, Size
from tests.property.test_condition_mutants import kill

Examples = Callable[[Size, tuple[str, ...]], st.SearchStrategy[Any]]
# Each property part that kills a mutant, by name: its examples at a size over a stratum of its ways, its
# strata, and its check. HP43's `indexes` and HP46 draw no way: their one stratum is their part's name.
Killer = tuple[Examples, tuple[tuple[str, ...], ...], Callable[[Any], None]]


def judged_in(part: str) -> Examples:
    return lambda size, ways: strategies.judged(part, size, ways)


def whole(examples: Callable[[Size], st.SearchStrategy[Any]]) -> Examples:
    return lambda size, _: examples(size)


KILLERS: dict[str, Killer] = {
    **{
        f"HP43 {part}": (judged_in(part), strategies.STRATA[part], properties.check_judged)
        for part in strategies.HP43_PARTS
    },
    "HP43 indexes": (whole(strategies.indexes), (("indexes",),), properties.check_indexes),
    "HP44 requests": (strategies.requests, strategies.STRATA["requests"], properties.check_reads),
    "HP44 coverage": (strategies.coverage, strategies.STRATA["coverage"], properties.check_reads),
    "HP45 label": (strategies.labels, strategies.STRATA["label"], properties.check_own_reasons),
    "HP45 review": (strategies.reviews, strategies.STRATA["review"], properties.check_own_reasons),
    "HP45 label_waiver": (
        strategies.label_waivers,
        strategies.STRATA["label_waiver"],
        properties.check_label_waiver,
    ),
    "HP46": (whole(properties.permuted_worlds), (("permutation",),), properties.check_permutation),
}


class Mutant(NamedTuple):
    name: str
    function: str  # the name the fault replaces, in its module
    killer: str  # a key of KILLERS
    inject: Callable[[pytest.MonkeyPatch], None]
    dies_at: tuple[str, ...]  # the ways, one of which the example that kills it must show
    says: str  # a pattern the message of the assertion that kills it must match: what the fault changes
    fault: str  # the fault, in words


def stratum(mutant: Mutant) -> tuple[str, ...]:
    """The stratum of its killer's ways holding every way the mutant names: the test whose draws kill it."""
    return next(ways for ways in KILLERS[mutant.killer][1] if set(mutant.dies_at) <= set(ways))


# The functions and tables the faults wrap, taken before any replaces them.
COVERS = acceptance._covers  # pyright: ignore[reportPrivateUsage]
UNDER = acceptance._under  # pyright: ignore[reportPrivateUsage]
LOCATED_AT = acceptance.located_at
JUDGE = acceptance.judge
COVERAGE = acceptance.COVERAGE
RESULTS = build._results  # pyright: ignore[reportPrivateUsage]
REQUEST = build._request  # pyright: ignore[reportPrivateUsage]
GIVEN = build._given  # pyright: ignore[reportPrivateUsage]
APPLIED = build._applied  # pyright: ignore[reportPrivateUsage]
SHOWN = build._shown  # pyright: ignore[reportPrivateUsage]
STORED = build._stored  # pyright: ignore[reportPrivateUsage]
BUILD_REASONS = build._build_reasons  # pyright: ignore[reportPrivateUsage]
UNUSED = build._unused  # pyright: ignore[reportPrivateUsage]
REQUIREMENT = build._requirement  # pyright: ignore[reportPrivateUsage]
READ = read
IMPLIED_MEMBERS = build._IMPLIED_MEMBERS  # pyright: ignore[reportPrivateUsage]
REFUSED = BuildReport.refused


def replacing(module: object, name: str, value: object) -> Callable[[pytest.MonkeyPatch], None]:
    return lambda monkeypatch: monkeypatch.setattr(module, name, value)


def judging(value: Callable[..., Judgement]) -> Callable[[pytest.MonkeyPatch], None]:
    """`judge` replaced where the verdict is drawn directly and where the build looks it up."""

    def inject(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(acceptance, "judge", value)
        monkeypatch.setattr(build, "judge", value)

    return inject


def locating(value: Callable[[Acceptance, MaterialRef], bool]) -> Callable[[pytest.MonkeyPatch], None]:
    """`located_at` replaced where the verdict looks it up and where the build gives a read its
    acceptances."""

    def inject(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(acceptance, "located_at", value)
        monkeypatch.setattr(build, "located_at", value)

    return inject


# `_covers` and `_under`: what covers which reason.

Covers = Callable[[Acceptance, Reason, ReadResult | None, MaterialRef, str], bool]


def covering_also(extra: Callable[[Acceptance, Reason], bool]) -> Covers:
    """`_covers`, and besides, a waiver that names the result's field, is located at its record and names the
    reason's code and condition, where `extra` holds."""

    def faulty(
        found: Acceptance, reason: Reason, read: ReadResult | None, record: MaterialRef, field: str
    ) -> bool:
        named = (
            found.kind == "waiver"
            and found.field == field
            and LOCATED_AT(found, record)
            and found.members.get("code") == reason.code
            and found.members.get("condition") == reason.condition
        )
        return COVERS(found, reason, read, record, field) or (named and extra(found, reason))

    return faulty


def _not_met(_: Acceptance, reason: Reason) -> bool:
    return VOCABULARY.reasons[reason.code].status == "not_met"


def _coded(code: str) -> Callable[[Acceptance, Reason], bool]:
    return lambda _, reason: reason.code == code


def _unlisted(_: Acceptance, reason: Reason) -> bool:
    return not any(reason.code in row.reasons for row in COVERAGE)


def _covers_no_alternative(
    found: Acceptance, reason: Reason, read: ReadResult | None, record: MaterialRef, field: str
) -> bool:
    return reason.alternative is None and COVERS(found, reason, read, record, field)


def _covers_any_field(
    found: Acceptance, reason: Reason, read: ReadResult | None, record: MaterialRef, field: str
) -> bool:
    return COVERS(dataclasses.replace(found, field=field), reason, read, record, field)


Under = Callable[[CoverageRow, Acceptance, Reason, ReadResult | None], bool]


def under_without(change: Callable[[CoverageRow], CoverageRow], kind: str) -> Under:
    """`_under`, its row changed by `change` for an acceptance of `kind`."""

    def faulty(row: CoverageRow, found: Acceptance, reason: Reason, read: ReadResult | None) -> bool:
        return UNDER(change(row) if found.kind == kind else row, found, reason, read)

    return faulty


def _naming_no_condition(row: CoverageRow) -> CoverageRow:
    return dataclasses.replace(row, names_condition=False)


def _naming_no_code(row: CoverageRow) -> CoverageRow:
    return dataclasses.replace(row, names_code=False)


def _on_no_assumption(row: CoverageRow) -> CoverageRow:
    return dataclasses.replace(row, on_assumption=False)


def _without_the_pick_row() -> tuple[CoverageRow, ...]:
    return tuple(row for row in COVERAGE if row.kind != "pick")


def _extrapolation_row_without(code: str) -> tuple[CoverageRow, ...]:
    """Section 4.2's rows, `code` left out of the row an extrapolation covers with no condition of its own
    (`range_unstated`, `outside_coverage`)."""
    return tuple(
        dataclasses.replace(row, reasons=tuple(each for each in row.reasons if each != code))
        if row.kind == "extrapolation" and not row.on_assumption
        else row
        for row in COVERAGE
    )


def _at_edge_beside_range_unstated() -> tuple[CoverageRow, ...]:
    return tuple(
        dataclasses.replace(row, reasons=(*row.reasons, "at_edge"))
        if "range_unstated" in row.reasons
        else row
        for row in COVERAGE
    )


# `located_at`.


def located_by(*members: str) -> Callable[[Acceptance, MaterialRef], bool]:
    """`located_at`, comparing the record's `members` alone."""

    def faulty(found: Acceptance, record: MaterialRef) -> bool:
        if found.location is None or {"region", "interval"} & found.members.keys():
            return LOCATED_AT(found, record)
        return all(getattr(found.location, member) == getattr(record, member) for member in members)

    return faulty


def _located_wherever_it_names_the_record(found: Acceptance, record: MaterialRef) -> bool:
    return found.location == record if found.location is not None else LOCATED_AT(found, record)


# `judge`.


def _without_the_applied(reasons: Sequence[Reason], read: ReadResult | None, *rest: Any) -> Judgement:
    record, field, offered, _ = rest
    return JUDGE(reasons, read, record, field, offered, ())


def _with_what_covered_nothing(reasons: Sequence[Reason], read: ReadResult | None, *rest: Any) -> Judgement:
    record, field, offered, applied = rest
    found = JUDGE(reasons, read, record, field, offered, applied)
    near = {one.index for one in offered if one.field == field and LOCATED_AT(one, record)}
    return dataclasses.replace(found, accepted_by=tuple(sorted({*found.accepted_by, *near})))


def _not_accepted_whole(reasons: Sequence[Reason], *rest: Any) -> Judgement:
    return dataclasses.replace(JUDGE(reasons, *rest), not_accepted=tuple(reasons))


def _labelled_waivers_trusted(
    reasons: Sequence[Reason],
    read: ReadResult | None,
    record: MaterialRef,
    field: str,
    offered: Sequence[Acceptance],
    applied: Sequence[int],
) -> Judgement:
    """A waiver naming a label covering as one naming none, its label never judged."""
    unlabelled = [
        dataclasses.replace(
            one, members={name: value for name, value in one.members.items() if name != "label"}
        )
        for one in offered
    ]
    return JUDGE(reasons, read, record, field, unlabelled, applied)


def _raised_wherever_a_labelled_waiver_fits(
    reasons: Sequence[Reason],
    read: ReadResult | None,
    record: MaterialRef,
    field: str,
    offered: Sequence[Acceptance],
    applied: Sequence[int],
) -> Judgement:
    """Label trust's raise wherever a waiver naming a label fits a reason, the result decided or not."""
    for one in offered:
        if "label" in one.members and any(COVERS(one, reason, read, record, field) for reason in reasons):
            raise NotImplementedError(
                f"the waiver /acceptances/{one.index} names a label: label trust judges it"
            )
    return JUDGE(reasons, read, record, field, offered, applied)


# `_results`: a model's results judged by every model's acceptances (R02).


def _judged_by_every_model(monkeypatch: pytest.MonkeyPatch) -> None:
    every: list[Acceptance] = []

    def results(declared: Declaration, *rest: Any) -> Any:
        every[:] = [one for model in declared.models for one in model.acceptances]
        return RESULTS(declared, *rest)

    def judged(reasons: Sequence[Reason], read: ReadResult | None, *rest: Any) -> Judgement:
        record, field, _, applied = rest
        return JUDGE(reasons, read, record, field, every, applied)

    monkeypatch.setattr(build, "_results", results)
    monkeypatch.setattr(build, "judge", judged)


# `_applied` and `_shown`: what a read applied.

Applied = Callable[[ReadResult, Sequence[Acceptance]], tuple[int, ...]]


def applied_with(kind: str) -> Applied:
    """`_applied`, and every acceptance of `kind` given."""

    def faulty(result: ReadResult, offered: Sequence[Acceptance]) -> tuple[int, ...]:
        return tuple(sorted({*APPLIED(result, offered), *(one.index for one in offered if one.kind == kind)}))

    return faulty


def _applied_by_position(result: ReadResult, offered: Sequence[Acceptance]) -> tuple[int, ...]:
    """Each acceptance applied by its position among those given, not its index in the model's list."""
    shown = set(APPLIED(result, offered))
    return tuple(position for position, one in enumerate(offered) if one.index in shown)


def _shown_where_every_condition_is_filled(found: Acceptance, result: ReadResult) -> bool:
    if found.kind != "implied_condition":
        return SHOWN(found, result)
    implies = cast(JsonObject, found.members["implies"])
    return all(
        SHOWN(dataclasses.replace(found, members={**found.members, "implies": {name: value}}), result)
        for name, value in implies.items()
    )


def _shown_under_any_assumption(found: Acceptance, result: ReadResult) -> bool:
    if found.kind == "extrapolation":
        return result.assumption is not None
    return SHOWN(found, result)


def _fills_by_equality(entry: JsonObject | None, implied: JsonObject) -> bool:
    supplied = build._supplied(implied)  # pyright: ignore[reportPrivateUsage]
    return entry is not None and entry == supplied


# `_request` and `_given`: the read each result is.


def _given_wherever(
    acceptances: Sequence[Acceptance], record: MaterialRef, field: str
) -> tuple[Acceptance, ...]:
    """Every acceptance of a kind a read takes that names the field, wherever it is located."""
    return tuple(one for one in acceptances if one.kind in build._GIVEN_KINDS and one.field == field)  # pyright: ignore[reportPrivateUsage]


def _given_by_section(
    acceptances: Sequence[Acceptance], record: MaterialRef, field: str
) -> tuple[Acceptance, ...]:
    section = field.partition(".")[0]
    return tuple(
        one
        for one in acceptances
        if one.kind in build._GIVEN_KINDS  # pyright: ignore[reportPrivateUsage]
        and (one.field or "").partition(".")[0] == section
        and LOCATED_AT(one, record)
    )


def request_changed(change: Callable[[dict[str, Any], Requirement], None]) -> Callable[..., Any]:
    def faulty(
        operating: Any, record: MaterialRef, requirement: Requirement, offered: Sequence[Acceptance]
    ) -> Any:
        request = cast(dict[str, Any], REQUEST(operating, record, requirement, offered))
        change(request, requirement)
        return request

    return faulty


def _label_and_review_given(request: dict[str, Any], requirement: Requirement) -> None:
    if requirement.label is not None:
        request["requirement"]["label"] = requirement.label
    if requirement.reviewed:
        request["requirement"]["review"] = "reviewed"


def _unnamed_operating_dropped(request: dict[str, Any], requirement: Requirement) -> None:
    request["operating_conditions"] = {
        name: value
        for name, value in request["operating_conditions"].items()
        if name in requirement.conditions
    }


def _want_defaulted(request: dict[str, Any], requirement: Requirement) -> None:
    request["requirement"]["want"] = "value"


def given_changed(change: Callable[[list[Acceptance]], list[Acceptance]]) -> Callable[..., Any]:
    def faulty(
        operating: Any, record: MaterialRef, requirement: Requirement, offered: Sequence[Acceptance]
    ) -> Any:
        return REQUEST(operating, record, requirement, change(list(offered)))

    return faulty


def _read_under_the_default_claims(request: Any, store: RecordStore, *, claims: Any) -> ReadResult:
    return READ(request, store)


def read_resting(change: Callable[[ReadResult], ReadResult]) -> Callable[..., ReadResult]:
    def faulty(request: Any, store: RecordStore, *, claims: Any) -> ReadResult:
        return change(READ(request, store, claims=claims))

    return faulty


def _on_the_first_under_want_mismatch(result: ReadResult) -> ReadResult:
    codes = {reason.code for reason in result.reasons}
    if (
        result.resting_on is None
        and "want_mismatch" in codes
        and {reason.alternative for reason in result.reasons} - {None}
    ):
        return dataclasses.replace(result, resting_on=(0,))
    return result


def _on_the_field_refused_at_steps_2_to_5(result: ReadResult) -> ReadResult:
    codes = {reason.code for reason in result.reasons}
    if result.resting_on is None and codes & {"other_version", "malformed", "unknown_type"}:
        return dataclasses.replace(result, resting_on=())
    return result


# `_results` and `check_build`: which results, and their status.


def _every_record_in_the_store(monkeypatch: pytest.MonkeyPatch) -> None:
    def results(declared: Declaration, store: RecordStore, claims: Any) -> Any:
        every = tuple(
            MaterialRef(found.id, found.version, str(found.value["content_hash"]))
            for found in store.list_records()
        )
        models = tuple(dataclasses.replace(model, records=every) for model in declared.models)
        return RESULTS(dataclasses.replace(declared, models=models), store, claims)

    monkeypatch.setattr(build, "_results", results)


def _no_requirement_read(model: ModelEntry, field: str) -> Requirement:
    found = REQUIREMENT(model, field)
    return Requirement(field, "value", {}, None, False) if found is None else found


def _deduplicated_by_field(*offered: Any) -> Any:
    kept: dict[str, Any] = {}
    for reading in RESULTS(*offered):
        kept.setdefault(reading[0].field, reading)
    return list(kept.values())


def _in_reverse(*offered: Any) -> Any:
    return list(reversed(RESULTS(*offered)))


def result_changed(change: Callable[[BuildResult], BuildResult]) -> Callable[[pytest.MonkeyPatch], None]:
    def inject(monkeypatch: pytest.MonkeyPatch) -> None:
        def made(*members: Any, **more: Any) -> BuildResult:
            return change(BuildResult(*members, **more))

        monkeypatch.setattr(build, "BuildResult", made)

    return inject


def _met_when_accepted(result: BuildResult) -> BuildResult:
    return dataclasses.replace(result, status="met") if result.accepted else result


def _unknown_when_not_reviewed(result: BuildResult) -> BuildResult:
    if any(reason.code == "not_reviewed" for reason in result.reasons):
        return dataclasses.replace(result, status="unknown")
    return result


# `_stored`: the value a label is checked against.


def _stored_from_the_result(
    store: RecordStore, record: MaterialRef, field: str, result: ReadResult, claims: Any
) -> JsonObject | None:
    held = [label for label in result.labels if label.startswith("materica.")]
    return None if result.resting_on is None else ({"label": held[0]} if held else {})


def _stored_of_the_section(
    store: RecordStore, record: MaterialRef, field: str, result: ReadResult, claims: Any
) -> JsonObject | None:
    """The `label` of the section holding the field, in place of the value's."""
    found = STORED(store, record, field, result, claims)
    if found is None:
        return None
    resolved = resolve_record(record, store, claims)
    assert isinstance(resolved, ResolvedRecord)
    sections = cast(JsonObject, cast(JsonObject, resolved.record.value["body"])["sections"])
    held = cast(JsonObject, sections[field.partition(".")[0]])
    return {"label": held["label"]} if "label" in held else {}


def _stored_under_the_default_claims(
    store: RecordStore, record: MaterialRef, field: str, result: ReadResult, claims: Any
) -> JsonObject | None:
    return STORED(store, record, field, result, CLAIMS)


# `_build_reasons`: the build's own reasons.

BuildReasons = Callable[[Requirement | None, ReadResult | None, JsonObject | None], tuple[Reason, ...]]


def reasons_changed(change: Callable[[BuildReasons], BuildReasons]) -> Callable[[pytest.MonkeyPatch], None]:
    return replacing(build, "_build_reasons", change(BUILD_REASONS))


def _without(code: str) -> Callable[[BuildReasons], BuildReasons]:
    def change(original: BuildReasons) -> BuildReasons:
        def faulty(
            requirement: Requirement | None, result: ReadResult | None, stored: JsonObject | None
        ) -> tuple[Reason, ...]:
            return tuple(one for one in original(requirement, result, stored) if one.code != code)

        return faulty

    return change


def _not_checked_with_a_reason_reviewed(original: BuildReasons) -> BuildReasons:
    def faulty(
        requirement: Requirement | None, result: ReadResult | None, stored: JsonObject | None
    ) -> tuple[Reason, ...]:
        found = original(requirement, result, stored)
        review = {} if result is None or result.provenance is None else result.provenance.review
        return tuple(one for one in found if one.code != "not_reviewed") if "reason" in review else found

    return faulty


def _not_reviewed_without_provenance(original: BuildReasons) -> BuildReasons:
    def faulty(
        requirement: Requirement | None, result: ReadResult | None, stored: JsonObject | None
    ) -> tuple[Reason, ...]:
        found = original(requirement, result, stored)
        if (
            requirement is not None
            and requirement.reviewed
            and result is not None
            and result.provenance is None
        ):
            return (*found, Reason("not_reviewed"))
        return found

    return faulty


def _label_mismatch_on_no_stored_value(original: BuildReasons) -> BuildReasons:
    def faulty(
        requirement: Requirement | None, result: ReadResult | None, stored: JsonObject | None
    ) -> tuple[Reason, ...]:
        return original(requirement, result, {} if stored is None and requirement is not None else stored)

    return faulty


def _label_only_on_a_read_otherwise_met(original: BuildReasons) -> BuildReasons:
    def faulty(
        requirement: Requirement | None, result: ReadResult | None, stored: JsonObject | None
    ) -> tuple[Reason, ...]:
        found = original(requirement, result, stored)
        if result is not None and result.status == "not_met":
            return tuple(one for one in found if one.code != "label_mismatch")
        return found

    return faulty


def _label_only_where_the_read_is_not_met(original: BuildReasons) -> BuildReasons:
    def faulty(
        requirement: Requirement | None, result: ReadResult | None, stored: JsonObject | None
    ) -> tuple[Reason, ...]:
        found = original(requirement, result, stored)
        if result is not None and result.status == "met":
            return tuple(one for one in found if one.code != "label_mismatch")
        return found

    return faulty


def _not_reviewed_as_not_met(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = VOCABULARY.reasons["not_reviewed"]
    monkeypatch.setitem(VOCABULARY.reasons, "not_reviewed", dataclasses.replace(spec, status="not_met"))


# `_unused`.

Unused = Callable[[Declaration, Sequence[BuildResult]], tuple[UnusedAcceptance, ...]]


def _unused_by_covering_alone(
    declared: Declaration, results: Sequence[BuildResult]
) -> tuple[UnusedAcceptance, ...]:
    """Used read from what covered a reason alone, so that one a read applied is listed unused."""
    found: list[UnusedAcceptance] = []
    for model in declared.models:
        used = {
            one.index
            for result in results
            if result.model == model.name
            for reason in result.reasons
            for one in model.acceptances
            if COVERS(one, reason, result.read, result.record, result.field)
        }
        found += [
            UnusedAcceptance(model.name, one.index) for one in model.acceptances if one.index not in used
        ]
    return tuple(found)


def _unused_named_after_the_first(
    declared: Declaration, results: Sequence[BuildResult]
) -> tuple[UnusedAcceptance, ...]:
    first = declared.models[0].name
    return tuple(dataclasses.replace(found, model=first) for found in UNUSED(declared, results))


def _unused_shared(declared: Declaration, results: Sequence[BuildResult]) -> tuple[UnusedAcceptance, ...]:
    used = {index for result in results for index in result.accepted_by}
    return tuple(
        UnusedAcceptance(model.name, one.index)
        for model in declared.models
        for one in model.acceptances
        if one.index not in used
    )


# `BuildReport.refused`.


def _refused_by_the_first_model(report: BuildReport) -> bool:
    first = report.results[0].model if report.results else None
    return bool(report.refusals) or not all(
        result.accepted for result in report.results if result.model == first
    )


# The assertion of `check_judged` a fault of the verdict fails first. A fault by which an acceptance covers a
# reason it should not, or leaves one uncovered it should cover, changes `accepted` where that reason decides
# the verdict, and otherwise `accepted_by`, which gains or loses the acceptance: `COVERED`. Where that
# acceptance can also cover another reason of the result (a waiver whose code, or condition, an extra reason
# may hold, or a waiver covering several reasons), `accepted_by` may stay as it was, and `not_accepted` is the
# assertion that changes: `VERDICT`. Whole builds name the result first (`check_verdicts`):
# `VERDICT_OF_A_RESULT`.
COVERED = r"^accepted(_by)? "
VERDICT = r"^(accepted|accepted_by|not_accepted) "
VERDICT_OF_A_RESULT = r": (accepted|accepted_by|not_accepted) "
WAIVERS = strategies.HP43_PARTS["waivers"]
ASSUMPTIONS = strategies.HP43_PARTS["assumptions"]
NEVER = strategies.HP43_PARTS["never"]
REQUESTS = strategies.HP44_PARTS["requests"]
COVERAGE_WAYS = strategies.HP44_PARTS["coverage"]
LABEL = strategies.HP45_PARTS["label"]
REVIEW = strategies.HP45_PARTS["review"]
LABEL_WAIVER = strategies.HP45_PARTS["label_waiver"]

MUTANTS = [
    # `_covers` and `_under` (HP43).
    Mutant(
        "waiver_covers_not_met",
        "_covers",
        "HP43 never",
        replacing(acceptance, "_covers", covering_also(_not_met)),
        ("unlisted_not_met",),
        COVERED,
        "a waiver naming a `not_met` reason covers it",
    ),
    Mutant(
        "waiver_ignores_its_condition",
        "_under",
        "HP43 waivers",
        replacing(acceptance, "_under", under_without(_naming_no_condition, "waiver")),
        ("condition_differs",),
        VERDICT,
        "a waiver covers a reason of its code whatever condition it names",
    ),
    Mutant(
        "waiver_ignores_its_code",
        "_under",
        "HP43 waivers",
        replacing(acceptance, "_under", under_without(_naming_no_code, "waiver")),
        ("code_differs",),
        VERDICT,
        "a waiver covers a reason its row lists whatever code it names",
    ),
    Mutant(
        "nominal_covers_without_its_assumption",
        "_under",
        "HP43 assumptions",
        replacing(acceptance, "_under", under_without(_on_no_assumption, "nominal")),
        ("nominal_not_named",),
        COVERED,
        "a nominal covers `want_mismatch` on a result whose `assumption` does not name it",
    ),
    Mutant(
        "extrapolation_covers_without_its_assumption",
        "_under",
        "HP43 assumptions",
        replacing(acceptance, "_under", under_without(_on_no_assumption, "extrapolation")),
        ("extrapolation_not_named",),
        COVERED,
        "an extrapolation covers `outside_range` on a result whose `assumption` does not name it",
    ),
    Mutant(
        "pick_covers_nothing",
        "COVERAGE",
        "HP43 assumptions",
        replacing(acceptance, "COVERAGE", _without_the_pick_row()),
        ("pick",),
        COVERED,
        "a pick covers nothing (section 4.2's `no_pick` row left out)",
    ),
    Mutant(
        "extrapolation_leaves_range_unstated",
        "COVERAGE",
        "HP43 assumptions",
        replacing(acceptance, "COVERAGE", _extrapolation_row_without("range_unstated")),
        ("extrapolation_unconditioned",),
        COVERED,
        "an extrapolation does not cover `range_unstated`",
    ),
    Mutant(
        "extrapolation_leaves_outside_coverage",
        "COVERAGE",
        "HP43 assumptions",
        replacing(acceptance, "COVERAGE", _extrapolation_row_without("outside_coverage")),
        ("extrapolation_unconditioned",),
        COVERED,
        "an extrapolation does not cover `outside_coverage`",
    ),
    Mutant(
        "extrapolation_covers_at_an_edge",
        "COVERAGE",
        "HP43 never",
        replacing(acceptance, "COVERAGE", _at_edge_beside_range_unstated()),
        ("at_edge",),
        COVERED,
        "`at_edge` covered by an extrapolation, as `range_unstated` is",
    ),
    Mutant(
        "waiver_covers_no_pick",
        "_covers",
        "HP43 never",
        replacing(acceptance, "_covers", covering_also(_coded("no_pick"))),
        ("no_pick",),
        COVERED,
        "`no_pick` covered by a waiver naming it",
    ),
    Mutant(
        "waiver_covers_label_mismatch",
        "_covers",
        "HP43 never",
        replacing(acceptance, "_covers", covering_also(_coded("label_mismatch"))),
        ("label_mismatch",),
        COVERED,
        "`label_mismatch` covered by a waiver naming it",
    ),
    Mutant(
        "waiver_covers_a_code_no_row_lists",
        "_covers",
        "HP43 never",
        replacing(acceptance, "_covers", covering_also(_unlisted)),
        ("unlisted_not_met", "no_pick"),
        COVERED,
        "a waiver covers a code no row of section 4.2 lists, where it names it",
    ),
    Mutant(
        "waiver_covers_no_reason_of_an_alternative",
        "_covers",
        "HP43 waivers",
        replacing(acceptance, "_covers", _covers_no_alternative),
        ("matching", "code_differs"),
        VERDICT,
        "an acceptance covers no reason that carries an `alternative` (R07)",
    ),
    Mutant(
        "waiver_ignores_its_field",
        "_covers",
        "HP43 waivers",
        replacing(acceptance, "_covers", _covers_any_field),
        ("field_differs",),
        COVERED,
        "an acceptance covers a reason of a result of another field",
    ),
    # `located_at` (HP43).
    Mutant(
        "located_by_id_alone",
        "located_at",
        "HP43 waivers",
        locating(located_by("id")),
        ("location_differs",),
        COVERED,
        "an acceptance located at every record of its record's `id` (R06)",
    ),
    Mutant(
        "located_ignoring_the_version",
        "located_at",
        "HP43 waivers",
        locating(located_by("id", "content_hash")),
        ("location_differs",),
        COVERED,
        "an acceptance located at its record's `id` and `content_hash`, whatever the `version`",
    ),
    Mutant(
        "located_ignoring_the_id",
        "located_at",
        "HP43 waivers",
        locating(located_by("version", "content_hash")),
        ("location_differs",),
        COVERED,
        "an acceptance located at its record's `version` and `content_hash`, whatever the `id`",
    ),
    Mutant(
        "region_taken_at_a_record",
        "located_at",
        "HP43 waivers",
        locating(_located_wherever_it_names_the_record),
        ("location_differs",),
        COVERED,
        "an acceptance naming a region or an interval beside a record located at that record",
    ),
    # `judge` (HP43).
    Mutant(
        "accepted_by_without_the_applied",
        "judge",
        "HP43 assumptions",
        judging(_without_the_applied),
        ("other_reason",),
        "accepted_by ",
        "`accepted_by` holds what covered a reason, not what the read applied",
    ),
    Mutant(
        "accepted_by_with_what_covered_nothing",
        "judge",
        "HP43 waivers",
        judging(_with_what_covered_nothing),
        ("matching", "code_differs"),
        "accepted_by ",
        "`accepted_by` holds every acceptance of the result's field located at its record",
    ),
    Mutant(
        "not_accepted_holds_covered_reasons",
        "judge",
        "HP43 waivers",
        judging(_not_accepted_whole),
        ("matching", "code_differs"),
        "not_accepted ",
        "`not_accepted` holds every reason, covered or not",
    ),
    Mutant(
        "judged_by_every_models_acceptances",
        "_results",
        "HP43 indexes",
        _judged_by_every_model,
        ("indexes",),
        VERDICT_OF_A_RESULT,
        "a model's results judged by every model's acceptances (R02)",
    ),
    # `_applied`, `_shown` and `_fills`: "applied" (HP43's `indexes`).
    Mutant(
        "unfilled_implied_condition_applied",
        "_applied",
        "HP43 indexes",
        replacing(build, "_applied", applied_with("implied_condition")),
        ("indexes",),
        "accepted_by ",
        "an implied condition given to a read counted applied, whether or not it filled a condition",
    ),
    Mutant(
        "extrapolation_at_an_edge_applied",
        "_applied",
        "HP43 indexes",
        replacing(build, "_applied", applied_with("extrapolation")),
        ("indexes",),
        "accepted_by ",
        "an extrapolation given to a read counted applied, at an edge among others",
    ),
    Mutant(
        "implied_applied_where_every_condition_filled",
        "_shown",
        "HP43 indexes",
        replacing(build, "_shown", _shown_where_every_condition_is_filled),
        ("indexes",),
        "accepted_by ",
        "an implied condition applied only where it fills every condition it implies",
    ),
    Mutant(
        "implied_range_not_recognised",
        "_IMPLIED_MEMBERS",
        "HP43 indexes",
        replacing(build, "_IMPLIED_MEMBERS", tuple(name for name in IMPLIED_MEMBERS if name != "range")),
        ("indexes",),
        "accepted_by ",
        "an implied range not recognised in the condition it fills",
    ),
    Mutant(
        "implied_token_not_recognised",
        "_IMPLIED_MEMBERS",
        "HP43 indexes",
        replacing(build, "_IMPLIED_MEMBERS", tuple(name for name in IMPLIED_MEMBERS if name != "token")),
        ("indexes",),
        "accepted_by ",
        "an implied token not recognised in the condition it fills",
    ),
    Mutant(
        "implied_value_compared_by_equality",
        "_fills",
        "HP43 indexes",
        replacing(build, "_fills", _fills_by_equality),
        ("indexes",),
        "accepted_by ",
        "an implied value compared with the condition it fills by equality, so that -0 is 0",
    ),
    Mutant(
        "extrapolation_applied_under_any_assumption",
        "_shown",
        "HP43 indexes",
        replacing(build, "_shown", _shown_under_any_assumption),
        ("indexes",),
        "accepted_by ",
        "an extrapolation counted applied on a result with any `assumption`, a nominal's among them",
    ),
    # `_unused` (HP43's `indexes`).
    Mutant(
        "unused_lists_the_applied",
        "_unused",
        "HP43 indexes",
        replacing(build, "_unused", _unused_by_covering_alone),
        ("indexes",),
        "^unused ",
        "an acceptance a read applied, and that covered no reason, listed unused",
    ),
    Mutant(
        "unused_named_after_the_first_model",
        "_unused",
        "HP43 indexes",
        replacing(build, "_unused", _unused_named_after_the_first),
        ("indexes",),
        "^unused ",
        "each unused acceptance named after the first model (R01)",
    ),
    Mutant(
        "unused_shared_by_every_model",
        "_unused",
        "HP43 indexes",
        replacing(build, "_unused", _unused_shared),
        ("indexes",),
        "^unused ",
        "one set of used acceptances shared by every model (R03)",
    ),
    # `_request` and `_given` (HP44's `requests`).
    Mutant(
        "acceptance_at_another_record_given",
        "_given",
        "HP44 requests",
        replacing(build, "_given", _given_wherever),
        ("nominal",),
        "the read ",
        "an acceptance given to a read wherever it is located",
    ),
    Mutant(
        "acceptance_of_another_field_of_the_section_given",
        "_given",
        "HP43 indexes",
        replacing(build, "_given", _given_by_section),
        ("indexes",),
        "accepted_by ",
        "an acceptance for another field of the read's section given to it, and so counted applied where the"
        " result's `assumption` names one alike",
    ),
    Mutant(
        "requirement_label_and_review_given",
        "_request",
        "HP44 requests",
        replacing(build, "_request", request_changed(_label_and_review_given)),
        ("operating_value", "operating_range"),
        "the read ",
        "the requirement's `label` and `review` given in the read's request (`request_incomplete`)",
    ),
    Mutant(
        "unnamed_operating_condition_dropped",
        "_request",
        "HP44 requests",
        replacing(build, "_request", request_changed(_unnamed_operating_dropped)),
        ("operating_value", "operating_range"),
        "the read ",
        "an operating condition the requirement does not name dropped from the request",
    ),
    Mutant(
        "want_defaulted",
        "_request",
        "HP44 requests",
        replacing(build, "_request", request_changed(_want_defaulted)),
        ("operating_value", "operating_range"),
        "the read ",
        "the request's `want` defaulted to `value`",
    ),
    Mutant(
        "only_the_first_acceptance_given",
        "_request",
        "HP44 requests",
        replacing(build, "_request", given_changed(lambda offered: offered[:1])),
        ("implied",),
        "the read ",
        "the first acceptance given alone, of several",
    ),
    Mutant(
        "claims_dropped_from_the_read",
        "read",
        "HP44 requests",
        replacing(build, "read", _read_under_the_default_claims),
        ("operating_value", "operating_range"),
        "the read ",
        "the build's own read made under the default claims, not the build's",
    ),
    # `check_build` and `_results` (HP44).
    Mutant(
        "every_record_in_the_store_read",
        "_results",
        "HP44 coverage",
        _every_record_in_the_store,
        ("unlisted_record",),
        "^results ",
        "results for every record in the store, listed or not",
    ),
    Mutant(
        "field_with_no_requirement_read",
        "_requirement",
        "HP44 coverage",
        replacing(build, "_requirement", _no_requirement_read),
        ("unlisted_record", "no_requirement"),
        "a field with no requirement read",
        "a field with no requirement read for a value",
    ),
    Mutant(
        "status_lowered_when_accepted",
        "BuildResult",
        "HP44 requests",
        result_changed(_met_when_accepted),
        ("operating_value", "operating_range"),
        "status ",
        "the status of an accepted result made `met`",
    ),
    Mutant(
        "not_reviewed_status_unknown",
        "BuildResult",
        "HP44 requests",
        result_changed(_unknown_when_not_reviewed),
        ("nominal",),
        "status ",
        "`not_reviewed` making the status `unknown` over a read's `not_met` (R05)",
    ),
    # `_stored` and `resting_on` (HP45's `label`).
    Mutant(
        "label_from_the_result_only",
        "_stored",
        "HP45 label",
        replacing(build, "_stored", _stored_from_the_result),
        ("early_refusal",),
        "own reasons ",
        "the label read from the result's labels, which a refusal before step 12 leaves out",
    ),
    Mutant(
        "label_of_the_section",
        "_stored",
        "HP45 label",
        replacing(build, "_stored", _stored_of_the_section),
        ("equal", "differs"),
        "own reasons ",
        "the section's `label` in place of the value's",
    ),
    Mutant(
        "stored_under_the_default_claims",
        "_stored",
        "HP45 label",
        replacing(build, "_stored", _stored_under_the_default_claims),
        ("equal", "differs"),
        "^the build raised AssertionError",
        "the stored label read under the default claims, not the build's",
    ),
    Mutant(
        "rests_on_the_first_alternative_under_want_mismatch",
        "read",
        "HP45 label",
        replacing(build, "read", read_resting(_on_the_first_under_want_mismatch)),
        ("no_stored_value",),
        "own reasons ",
        "a result over two alternatives that stay, under `want_mismatch`, resting on the first",
    ),
    Mutant(
        "refusal_at_steps_2_to_5_rests_on_the_field",
        "read",
        "HP45 label",
        replacing(build, "read", read_resting(_on_the_field_refused_at_steps_2_to_5)),
        ("no_stored_value",),
        "^the build raised AssertionError",
        "a record refused at steps 2 to 5 resting on its field",
    ),
    Mutant(
        "label_mismatch_on_no_stored_value",
        "_build_reasons",
        "HP45 label",
        reasons_changed(_label_mismatch_on_no_stored_value),
        ("no_stored_value",),
        "own reasons ",
        "`label_mismatch` on a result that rests on no stored value",
    ),
    Mutant(
        "label_mismatch_left_out_beside_a_not_met",
        "_build_reasons",
        "HP45 label",
        reasons_changed(_label_only_on_a_read_otherwise_met),
        ("differs",),
        "own reasons ",
        "`label_mismatch` given only beside no `not_met` of the read's",
    ),
    Mutant(
        "label_mismatch_left_out_of_a_read_met",
        "_build_reasons",
        "HP45 label",
        reasons_changed(_label_only_where_the_read_is_not_met),
        ("absent_met",),
        "own reasons ",
        "`label_mismatch` given only where the read is not `met`",
    ),
    # `_build_reasons` (HP45's `review`).
    Mutant(
        "review_not_required",
        "_build_reasons",
        "HP45 review",
        reasons_changed(_without("not_reviewed")),
        ("not_checked",),
        "own reasons ",
        "`not_reviewed` never given",
    ),
    Mutant(
        "not_checked_with_a_reason_taken_as_reviewed",
        "_build_reasons",
        "HP45 review",
        reasons_changed(_not_checked_with_a_reason_reviewed),
        ("not_checked",),
        "own reasons ",
        "a review `not_checked` with a `reason` taken as completed",
    ),
    Mutant(
        "not_reviewed_read_as_not_met",
        "VOCABULARY.reasons",
        "HP45 review",
        _not_reviewed_as_not_met,
        ("not_checked",),
        "status ",
        "`not_reviewed` read as `not_met`",
    ),
    Mutant(
        "not_reviewed_given_without_provenance",
        "_build_reasons",
        "HP45 review",
        reasons_changed(_not_reviewed_without_provenance),
        ("reviewed", "not_checked"),
        "own reasons ",
        "`not_reviewed` given to a result that holds no `provenance` (R04)",
    ),
    # A waiver naming a label (HP45's `label_waiver`).
    Mutant(
        "labelled_waiver_covers_untrusted",
        "judge",
        "HP45 label_waiver",
        judging(_labelled_waivers_trusted),
        ("reviewed_and_labelled", "unreviewed"),
        "(decided where label trust|accepted_by )",
        "a waiver naming a label covers as one naming none, its label never judged",
    ),
    Mutant(
        "label_trust_raised_where_decided",
        "judge",
        "HP45 label_waiver",
        judging(_raised_wherever_a_labelled_waiver_fits),
        ("unlabelled", "another_label"),
        "^the build raised NotImplementedError",
        "label trust's raise where a waiver naming a label fits a reason of a result refused whatever",
    ),
    # The refusal law and order (HP46).
    Mutant(
        "refused_read_from_the_first_model_only",
        "BuildReport.refused",
        "HP46",
        replacing(BuildReport, "refused", property(_refused_by_the_first_model)),
        ("permutation",),
        "^refused ",
        "`refused` read from the first model's results only",
    ),
    Mutant(
        "acceptances_matched_by_position",
        "_applied",
        "HP46",
        replacing(build, "_applied", _applied_by_position),
        ("permutation",),
        "^permuted, the verdicts",
        "an acceptance a read applied mapped by its position among those given, not its index",
    ),
    Mutant(
        "results_deduplicated_by_field",
        "_results",
        "HP46",
        replacing(build, "_results", _deduplicated_by_field),
        ("permutation",),
        "^permuted, the verdicts",
        "one result per field, of the first model and record that read it",
    ),
    Mutant(
        "results_in_reverse",
        "_results",
        "HP46",
        replacing(build, "_results", _in_reverse),
        ("permutation",),
        "^permuted, the verdicts",
        "the results in the reverse of the order the declaration lists models, records and fields",
    ),
]


@pytest.mark.parametrize("size", [pytest.param(SMALL, id="small"), pytest.param(ORIGINAL, id="original")])
@pytest.mark.parametrize("mutant", MUTANTS, ids=[mutant.name for mutant in MUTANTS])
def test_the_build_mutant_is_killed(
    mutant: Mutant,
    size: Size,
    monkeypatch: pytest.MonkeyPatch,
    record_property: Callable[[str, object], None],
) -> None:
    """At an example of one of the ways it names, and at the assertion it names."""
    mutant.inject(monkeypatch)
    examples, _, check = KILLERS[mutant.killer]
    said: list[str] = []

    def checked(example: Any) -> None:
        try:
            check(example)
        except AssertionError as error:
            said.append(str(error))
            raise

    tried, example = kill(examples(size, stratum(mutant)), checked)
    record_property("examples_to_kill", tried)
    assert example.way in mutant.dies_at, example.way
    assert re.search(mutant.says, said[0]), said[0]
