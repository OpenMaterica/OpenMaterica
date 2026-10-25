# SPDX-License-Identifier: Apache-2.0
"""Examples of the build's verdict by its terms (`declarations.md` section 2, S7a-2b): what covers which
reason by section 4.2's rows (`COVERAGE`, `_covers`), where an acceptance is located (`located_at`), the
verdict on a result (`judge`) and the acceptances unused (`unused`). Each test plants what a wrong verdict
would give beside the one the text gives, for the faults of the S7 design's HP43 that no build-check file
can show: the files hold one kind of each fault where these hold every code, kind and location."""

from collections.abc import Sequence
from dataclasses import replace
from typing import cast

import pytest

from materica import shapes
from materica.core import acceptance as acceptance_module
from materica.core.acceptance import COVERAGE, Judgement, judge, located_at, names, unused
from materica.core.declarations import Acceptance, ModelEntry
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult
from materica.core.reasons import Reason
from materica.core.report import UnusedAcceptance
from materica.core.value_shapes import JsonObject
from materica.core.vocabulary import VOCABULARY
from materica.shapes import ReasonCode

covers = acceptance_module._covers  # pyright: ignore[reportPrivateUsage]

VISCOSITY, DENSITY = "fluid.dynamic_viscosity", "bulk.density"
WATER = MaterialRef(
    "conformance/water_fixture",
    "1.0.0",
    "sha256:c21a2c7f46e66bcfb5e74f18d2a08644468d5a92bafb4fa57a03651facf96e2d",
)
# Another copy of water: its id and version, another hash.
WATER_COPY = MaterialRef(WATER.id, WATER.version, "sha256:" + "0" * 64)
PLASMA = MaterialRef(
    "conformance/plasma_fixture",
    "1.0.0",
    "sha256:b1f42e0a1770b14e3e5a2e64060b1055f4c49e08814c949634a3463e545415a4",
)
# The codes whose reasons always carry a condition (`declarations.md` section 1, a waiver's `code`).
NAMING_A_CONDITION = {
    "condition_unstated",
    "condition_unknown_name",
    "condition_unchecked",
    "condition_outside",
    "condition_not_accepted",
    "condition_uncertain",
    "outside_range",
    "at_edge",
    "range_unstated",
}


def an_acceptance(
    kind: str,
    members: JsonObject,
    index: int = 0,
    at: MaterialRef | None = WATER,
    field: str | None = VISCOSITY,
) -> Acceptance:
    """An acceptance as the declaration's check gives it: its members as given, its location their
    `record`."""
    given: JsonObject = {"acceptance": kind, "reason": "planted"}
    if at is not None:
        given["record"] = cast(JsonValue, at.to_json())
    if field is not None:
        given["field"] = field
    return Acceptance(index, kind, at, field, {**given, **members})


def a_waiver(
    code: str, condition: str | None = None, index: int = 0, more: JsonObject | None = None
) -> Acceptance:
    named: JsonObject = {"code": code} if condition is None else {"code": code, "condition": condition}
    return an_acceptance("waiver", {**named, **(more or {})}, index)


NOMINAL = an_acceptance("nominal", {"value": 0.0007, "basis": "the supplier's grade"})
EXTRAPOLATION = an_acceptance(
    "extrapolation", {"method": "constant", "law": "held at the end value", "basis": "usual"}
)
# Every code of `read_side_contract.md` section 4.
CODES: list[ReasonCode] = [spec.code for spec in VOCABULARY.reasons.values()]


def assumed(acceptance: Acceptance | None) -> ReadResult:
    """A result whose `assumption` names `acceptance`, as the read gives it: its kind and its kind's own
    members, `basis` aside; None for a result with none."""
    if acceptance is None:
        return ReadResult("not_met", ())
    own = {
        name: value
        for name, value in acceptance.members.items()
        if name in ("value", "params", "method", "law")
    }
    return ReadResult(
        "not_met", (), assumption=cast(shapes.Assumption, {"acceptance": acceptance.kind, **own})
    )


def covered(acceptance: Acceptance, reason: Reason, read: ReadResult | None = None) -> bool:
    return covers(acceptance, reason, read, WATER, VISCOSITY)


# What a waiver covers: section 4.2's rows that name a `waiver`, the code, and the condition where the row
# says "naming that condition and code"; "A waiver covers a reason whatever its `alternative`".


@pytest.mark.parametrize("code", sorted(CODES))
def test_a_waiver_covers_a_code_exactly_where_a_row_lists_it_for_a_waiver(code: ReasonCode) -> None:
    """Every code of `read_side_contract.md` section 4, a waiver naming it, and its condition where it carries
    one: covered only where a row of section 4.2 lists it for a waiver, so never a `not_met` reason,
    `label_mismatch`, `no_pick`, `at_edge` or `condition_unknown_name`."""
    condition = "shear_rate" if code in NAMING_A_CONDITION else None
    listed = any(code in row.reasons and row.kind == "waiver" for row in COVERAGE)
    assert covered(a_waiver(code, condition), Reason(code, condition)) is listed
    if listed:
        assert VOCABULARY.reasons[code].status == "unknown"
    assert not covered(a_waiver(code, condition), Reason("absent"))


def test_the_codes_a_waiver_covers_are_those_section_4_2_lists_and_only_some_name_a_condition() -> None:
    """A waiver naming the reason's condition covers the codes of the three rows of section 4.2 that name a
    waiver; one naming another condition, only the codes of the two rows "naming that code", which compare
    no condition."""
    by_code = {
        "no_requirement",
        "stated_without_origin",
        "outside_check_points",
        "fill_in_version_mismatch",
        "entries_withheld",
        "not_reviewed",
        "engine_mass_not_comparable",
    }
    same = {code for code in CODES if covered(a_waiver(code, "shear_rate"), Reason(code, "shear_rate"))}
    assert same == {"condition_unstated", "condition_unchecked", "condition_uncertain", *by_code}
    other = {code for code in CODES if covered(a_waiver(code, "temperature"), Reason(code, "shear_rate"))}
    assert other == by_code


def test_a_waiver_covers_only_its_own_condition_and_code_whatever_the_alternative() -> None:
    waiver = a_waiver("condition_unstated", "shear_rate")
    assert covered(waiver, Reason("condition_unstated", "shear_rate"))
    assert covered(waiver, Reason("condition_unstated", "shear_rate", alternative=1))
    assert not covered(waiver, Reason("condition_unstated", "temperature"))
    assert not covered(waiver, Reason("condition_unstated", "temperature", alternative=1))
    assert not covered(waiver, Reason("condition_unchecked", "shear_rate"))
    assert covered(a_waiver("not_reviewed"), Reason("not_reviewed", alternative=0))


def test_a_waiver_covers_only_a_reason_of_its_own_field_at_its_own_record() -> None:
    reason = Reason("condition_unstated", "shear_rate")
    assert not covers(a_waiver("condition_unstated", "shear_rate"), reason, None, WATER, DENSITY)
    assert not covers(a_waiver("condition_unstated", "shear_rate"), reason, None, PLASMA, VISCOSITY)
    assert not covers(a_waiver("condition_unstated", "shear_rate"), reason, None, WATER_COPY, VISCOSITY)
    assert covers(a_waiver("condition_unstated", "shear_rate"), reason, None, WATER, VISCOSITY)


# What a nominal and an extrapolation cover: "a `nominal`, only on a result whose `assumption` names it"
# (`want_mismatch`); "an `extrapolation`, only on a result whose `assumption` names it" (`outside_range`);
# "an `extrapolation` only" (`range_unstated`, `outside_coverage`).


def test_a_nominal_covers_want_mismatch_only_on_a_result_whose_assumption_names_it() -> None:
    reason = Reason("want_mismatch")
    assert covered(NOMINAL, reason, assumed(NOMINAL))
    # Step 0's or step 7's `want_mismatch` carries no assumption.
    assert not covered(NOMINAL, reason, assumed(None))
    assert not covered(NOMINAL, reason, None)
    other = an_acceptance("nominal", {"value": 0.0009, "basis": "another grade"})
    assert not covered(NOMINAL, reason, assumed(other))
    assert not covered(NOMINAL, reason, assumed(EXTRAPOLATION))
    assert not covered(NOMINAL, Reason("outside_range", "temperature"), assumed(NOMINAL))


def test_an_extrapolation_covers_outside_range_only_where_named_and_range_unstated_wherever() -> None:
    outside = Reason("outside_range", "temperature")
    assert covered(EXTRAPOLATION, outside, assumed(EXTRAPOLATION))
    assert not covered(EXTRAPOLATION, outside, assumed(None))
    assert not covered(EXTRAPOLATION, outside, assumed(NOMINAL))
    for code in ("range_unstated", "outside_coverage"):
        assert covered(EXTRAPOLATION, Reason(code, "temperature" if code == "range_unstated" else None))
    assert not covered(EXTRAPOLATION, Reason("at_edge", "temperature"), assumed(EXTRAPOLATION))
    assert not covered(EXTRAPOLATION, Reason("want_mismatch"), assumed(EXTRAPOLATION))


def test_an_implied_condition_covers_no_reason() -> None:
    implied = an_acceptance("implied_condition", {"fact": "tissue_state", "token": "in_vivo", "implies": {}})
    assert not any(covered(implied, Reason(code, "temperature")) for code in CODES)


def test_no_row_lists_a_code_the_table_never_accepts() -> None:
    assert not any("condition_unknown_name" in row.reasons for row in COVERAGE)
    assert not any(
        code in row.reasons for row in COVERAGE for code in ("label_mismatch", "at_edge", "absent")
    )


# Where an acceptance is located (the build's terms): "when it names the record read, equal in `id`,
# `version` and `content_hash`; one located at a region or an interval is located at no record, and an
# accepted difference with no location is located at every location its model is checked over".


def test_an_acceptance_is_located_at_the_record_it_names_by_id_version_and_hash() -> None:
    waiver = a_waiver("condition_unstated", "shear_rate")
    assert located_at(waiver, WATER)
    assert not located_at(waiver, WATER_COPY)
    assert not located_at(waiver, MaterialRef(WATER.id, "1.0.1", WATER.content_hash))
    assert not located_at(waiver, PLASMA)


def test_an_acceptance_at_a_region_or_an_interval_is_at_no_record() -> None:
    places: list[JsonObject] = [{"region": "lumen"}, {"interval": {"path": "wall", "index": 0}}]
    for elsewhere in places:
        assert not located_at(a_waiver("condition_unstated", "shear_rate", more=elsewhere), WATER)
        assert not located_at(
            an_acceptance("waiver", {"code": "no_requirement", **elsewhere}, at=None), WATER
        )


def test_an_accepted_difference_with_no_location_is_at_every_record_and_no_other_kind_is() -> None:
    difference = an_acceptance(
        "accepted_difference", {"section": "fluid", "fact": "species", "value": "any"}, at=None, field=None
    )
    assert located_at(difference, WATER)
    assert located_at(difference, PLASMA)
    overlay = cast(JsonValue, WATER.to_json())
    scope = an_acceptance("overlay_scope", {"overlay": overlay, "accepts": ["model"]}, at=None, field=None)
    assert not located_at(scope, WATER)


# The verdict on a result (section 2 item 4): "`accepted` is true when each reason ... is covered", and
# "`accepted_by` lists ... every acceptance used, the ones the read itself applied ... included";
# "`not_accepted` lists each reason ... that nothing covers, empty exactly when `accepted` is true".

SHEAR = Reason("condition_unstated", "shear_rate")
TEST_METHOD = Reason("condition_unchecked", "test_method")


def verdict(
    reasons: Sequence[Reason], acceptances: Sequence[Acceptance], applied: Sequence[int] = ()
) -> Judgement:
    return judge(reasons, None, WATER, VISCOSITY, acceptances, applied)


def test_a_result_is_accepted_where_every_reason_is_covered_and_lists_what_covered_each() -> None:
    acceptances = [
        a_waiver("condition_unstated", "shear_rate", 0),
        a_waiver("condition_unchecked", "test_method", 1),
    ]
    assert verdict([SHEAR, TEST_METHOD], acceptances) == Judgement(True, (0, 1), ())
    assert verdict([SHEAR], acceptances) == Judgement(True, (0,), ())
    assert verdict([], acceptances) == Judgement(True, (), ())


def test_a_reason_nothing_covers_is_not_accepted_and_the_others_still_cite_what_covered_them() -> None:
    acceptances = [
        a_waiver("condition_unstated", "shear_rate", 0),
        a_waiver("stated_without_origin", None, 1),
    ]
    absent = Reason("absent")
    assert verdict([SHEAR, TEST_METHOD, absent], acceptances) == Judgement(False, (0,), (TEST_METHOD, absent))


def test_accepted_by_holds_the_acceptances_the_read_applied_beside_those_that_covered() -> None:
    acceptances = [a_waiver("condition_unstated", "shear_rate", 0), replace(NOMINAL, index=1)]
    assert verdict([], acceptances, (1,)) == Judgement(True, (1,), ())
    assert verdict([SHEAR], acceptances, (1,)) == Judgement(True, (0, 1), ())
    assert verdict([TEST_METHOD], acceptances, (1,)) == Judgement(False, (1,), (TEST_METHOD,))


def test_two_acceptances_covering_one_reason_are_both_cited() -> None:
    acceptances = [
        a_waiver("condition_unstated", "shear_rate", 0),
        a_waiver("condition_unstated", "shear_rate", 1),
    ]
    assert verdict([SHEAR], acceptances) == Judgement(True, (0, 1), ())


def test_a_reason_given_twice_by_alternative_is_covered_each_time() -> None:
    """A waiver covers each alternative's reason, as BC-016's arm gives two."""
    first, second = (Reason("condition_unstated", "shear_rate", alternative=index) for index in (0, 1))
    assert verdict([first, second], [a_waiver("condition_unstated", "shear_rate")]) == Judgement(
        True, (0,), ()
    )


# A waiver naming a label: "It covers its reason only on a result whose stored label ... is that label and is
# trusted" (section 4.1 item 4), which this version does not judge (maintainer, 2026-10-21: label trust
# after 0.1.0.dev4).


def test_a_waiver_naming_a_label_raises_where_it_would_cover_and_not_where_it_would_not() -> None:
    labelled = a_waiver("condition_unstated", "shear_rate", more={"label": "materica.fluid.newtonian.v1"})
    with pytest.raises(NotImplementedError, match="S7a-2's label trust"):
        covered(labelled, SHEAR)
    assert not covered(labelled, TEST_METHOD)
    assert not covers(labelled, SHEAR, None, PLASMA, VISCOSITY)


# The acceptances unused (item 9): "per model, each acceptance not used (the build's terms)".


def a_model(name: str, acceptances: Sequence[Acceptance]) -> ModelEntry:
    return ModelEntry(
        0, name, "1.0.0", "sha256:", (WATER,), {}, (VISCOSITY,), (), (), tuple(acceptances), (), {}
    )


def test_unused_lists_the_models_own_acceptances_none_of_its_results_used() -> None:
    nominal, extrapolation = (
        replace(found, index=index) for found, index in ((NOMINAL, 1), (EXTRAPOLATION, 2))
    )
    drag = a_model("drag", [a_waiver("condition_unstated", "shear_rate", 0), nominal, extrapolation])
    assert unused(drag, [(0,), ()]) == (UnusedAcceptance("drag", 1), UnusedAcceptance("drag", 2))
    assert unused(drag, [(0, 1), (2,)]) == ()
    assert unused(drag, []) == tuple(UnusedAcceptance("drag", index) for index in range(3))
    assert unused(a_model("lift", []), [(0,)]) == ()


def test_the_assumption_names_an_acceptance_by_its_kind_and_own_members() -> None:
    assert names({"acceptance": "nominal", "value": 0.0007}, NOMINAL)
    assert not names({"acceptance": "nominal", "value": 0.0009}, NOMINAL)
    assert not names({"acceptance": "extrapolation", "value": 0.0007}, NOMINAL)
    assert not names(None, NOMINAL)
