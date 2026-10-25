# SPDX-License-Identifier: Apache-2.0
"""The comparator and the fold of variants fail where `docs/specification/README.md`, "Case files", says."""

import math
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from materica.core.jsonio import JsonValue
from materica.shapes import Suite
from tests.conformance import runner
from tests.conformance.runner import CaseFile, CaseFileError, JsonObject, Outcome

MALFORMED: JsonObject = {"code": "malformed"}
UNSTATED: JsonObject = {"code": "condition_unstated", "condition": "shear_rate"}


def case(
    expected: JsonObject,
    members: tuple[str, ...] = ("status", "reasons", "value"),
    *,
    operation: str = "content_hash",
    claims: JsonObject | None = None,
    **compare: JsonValue,
) -> CaseFile:
    document: JsonObject = {
        "case": "XX-001",
        "variant": "arm",
        "suite": "hash",
        "schema_version": "0.1.0",
        "inputs": {},
        "request": {"operation": operation},
        "expected": expected,
        "compare": {"members": list(members), **compare},
    }
    if claims is not None:
        document["claims"] = claims
    return CaseFile.from_document(Path("XX-001.arm.json"), document)


def differences(case_file: CaseFile, result: JsonObject) -> list[str]:
    return runner.compare(case_file, result)


def test_the_expected_answer_passes() -> None:
    expected: JsonObject = {"status": "unknown", "reasons": [UNSTATED, MALFORMED], "value": "sha256:0"}
    result: JsonObject = {"status": "unknown", "reasons": [MALFORMED, UNSTATED], "value": "sha256:0"}
    assert differences(case(expected), result) == []


def test_detail_is_never_compared() -> None:
    expected: JsonObject = {"status": "not_met", "reasons": [MALFORMED]}
    result: JsonObject = {"status": "not_met", "reasons": [{"code": "malformed", "detail": "anything"}]}
    assert differences(case(expected), result) == []


@pytest.mark.parametrize(
    "reasons",
    [
        pytest.param([MALFORMED, UNSTATED], id="extra"),
        pytest.param([], id="missing"),
        pytest.param([MALFORMED, MALFORMED], id="duplicated"),
        pytest.param([{"code": "malformed", "condition": "temperature"}], id="condition_added"),
        pytest.param([{"code": "absent"}], id="other_code"),
    ],
)
def test_reasons_are_a_multiset_of_code_and_condition(reasons: list[JsonValue]) -> None:
    expected: JsonObject = {"status": "not_met", "reasons": [MALFORMED]}
    assert differences(case(expected), {"status": "not_met", "reasons": reasons})


def test_a_wrong_condition_fails() -> None:
    expected: JsonObject = {"status": "unknown", "reasons": [UNSTATED]}
    result: JsonObject = {
        "status": "unknown",
        "reasons": [{"code": "condition_unstated", "condition": "frequency"}],
    }
    assert differences(case(expected), result)


OUTSIDE: JsonObject = {"code": "condition_outside", "condition": "temperature"}


def outside(index: JsonValue) -> JsonObject:
    return {**OUTSIDE, "alternative": index}


@pytest.mark.parametrize(
    "reasons",
    [
        pytest.param([OUTSIDE], id="dropped"),
        pytest.param([outside(1.0)], id="another_index"),
        pytest.param([outside(-0.0)], id="minus_zero_under_exact"),
        pytest.param([outside(False)], id="a_bool"),
        pytest.param([outside("0")], id="a_string"),
        pytest.param([outside(None)], id="null"),
        pytest.param([outside(0.0), OUTSIDE], id="one_more_without"),
    ],
)
def test_a_reason_s_alternative_is_compared(reasons: list[JsonValue]) -> None:
    expected: JsonObject = {"status": "not_met", "reasons": [outside(0.0)]}
    assert differences(case(expected, exact=True), {"status": "not_met", "reasons": [outside(0.0)]}) == []
    assert differences(case(expected, exact=True), {"status": "not_met", "reasons": reasons})


def test_two_reasons_that_differ_only_by_alternative_are_two() -> None:
    expected: JsonObject = {"status": "not_met", "reasons": [outside(0.0), outside(1.0)]}
    swapped: JsonObject = {"status": "not_met", "reasons": [outside(1.0), outside(0.0)]}
    assert differences(case(expected, exact=True), swapped) == []
    assert differences(
        case(expected, exact=True), {"status": "not_met", "reasons": [outside(0.0), outside(0.0)]}
    )


def test_an_alternative_is_never_compared_at_a_tolerance_and_needs_one() -> None:
    expected: JsonObject = {"status": "not_met", "reasons": [outside(0.0)]}
    tolerant = case(expected, relative_tolerance=0.5)
    assert differences(tolerant, {"status": "not_met", "reasons": [outside(-0.0)]}) == []
    assert differences(tolerant, {"status": "not_met", "reasons": [outside(0.25)]})
    with pytest.raises(CaseFileError):
        differences(case(expected), {"status": "not_met", "reasons": [outside(0.0)]})


def without_alternatives(reasons: JsonValue) -> list[JsonValue]:
    assert isinstance(reasons, list)
    return [
        {name: value for name, value in reason.items() if name != "alternative"}
        if isinstance(reason, dict)
        else reason
        for reason in reasons
    ]


def test_every_case_file_whose_reasons_hold_an_alternative_fails_without_it() -> None:
    """A control through the real case files: a reader that drops a reason's `alternative`, on the one
    alternative left or picked or anywhere, fails each file that expects one. Until S4's code can run them,
    the expected answer with its indexes dropped stands for that reader's result."""
    holding = [
        case_file
        for case_file in runner.discover()
        if without_alternatives(case_file.expected.get("reasons", []))
        != case_file.expected.get("reasons", [])
    ]
    assert [case_file for case_file in holding if "value" in case_file.expected]
    for case_file in holding:
        dropped: JsonObject = {
            **case_file.expected,
            "reasons": without_alternatives(case_file.expected["reasons"]),
        }
        assert differences(case_file, dict(case_file.expected)) == [], case_file.path.name
        assert differences(case_file, dropped), case_file.path.name


def test_a_member_compared_but_not_expected_must_be_absent() -> None:
    expected: JsonObject = {"status": "not_met", "reasons": [MALFORMED]}
    assert differences(case(expected), {"status": "not_met", "reasons": [MALFORMED], "value": "sha256:0"})
    assert (
        differences(
            case(expected, ("status", "reasons")), {"status": "not_met", "reasons": [MALFORMED], "value": 1.0}
        )
        == []
    )


def test_an_expected_member_missing_from_the_result_fails() -> None:
    expected: JsonObject = {"status": "met", "reasons": [], "value": "sha256:0"}
    assert differences(case(expected), {"status": "met", "reasons": []})


def test_status_is_compared() -> None:
    expected: JsonObject = {"status": "met", "reasons": []}
    assert differences(case(expected), {"status": "unknown", "reasons": []})


LABELLED = ("status", "reasons", "value", "labels")


def test_labels_are_a_set_and_absent_is_empty() -> None:
    expected: JsonObject = {
        "status": "met",
        "reasons": [],
        "labels": ["user_extracted", "no_independent_witness"],
    }
    result: JsonObject = {
        "status": "met",
        "reasons": [],
        "labels": ["no_independent_witness", "user_extracted"],
    }
    assert differences(case(expected, LABELLED), result) == []
    assert (
        differences(case({"status": "met", "reasons": []}, LABELLED), {"status": "met", "reasons": []}) == []
    )
    assert differences(case(expected, LABELLED), {"status": "met", "reasons": []})


def test_hash_not_checked_is_compared_only_under_a_hash_claim() -> None:
    expected: JsonObject = {"status": "not_met", "reasons": [MALFORMED], "labels": []}
    result: JsonObject = {"status": "not_met", "reasons": [MALFORMED], "labels": ["hash_not_checked"]}
    assert differences(case(expected, LABELLED), result) == []
    assert differences(case(expected, LABELLED, claims={"hash": False}), result)
    assert differences(case(expected, LABELLED, claims={"hash": True}), result)


def test_numbers_need_a_tolerance_or_exact() -> None:
    expected: JsonObject = {"status": "met", "reasons": [], "value": 0.000692}
    with pytest.raises(CaseFileError):
        differences(case(expected), {"status": "met", "reasons": [], "value": 0.000692})


def test_relative_tolerance() -> None:
    expected: JsonObject = {"status": "met", "reasons": [], "value": [1000.0, 0.0]}
    tolerant = case(expected, relative_tolerance=1e-6)
    assert differences(tolerant, {"status": "met", "reasons": [], "value": [1000.0009, 9e-7]}) == []
    assert differences(tolerant, {"status": "met", "reasons": [], "value": [1000.0011, 0.0]})
    assert differences(tolerant, {"status": "met", "reasons": [], "value": [1000.0, 1.1e-6]})


def test_a_table_evaluation_tolerance_is_one_per_precision() -> None:
    expected: JsonObject = {"evaluations": [{"refused": True}]}
    tolerances: JsonObject = {"binary64": 1e-12, "binary32": 3e-7}
    read = case(expected, ("evaluations",), operation="evaluate", relative_tolerance=tolerances)
    assert read.precision_tolerances == {"binary64": 1e-12, "binary32": 3e-7}
    assert read.relative_tolerance is None
    broken_tolerances: list[JsonValue] = [
        {"binary64": 1e-12},
        {"binary64": 1e-12, "binary32": -1.0},
        {**tolerances, "bfloat16": 1e-2},
    ]
    for broken in broken_tolerances:
        with pytest.raises(CaseFileError):
            case(expected, ("evaluations",), operation="evaluate", relative_tolerance=broken)
    with pytest.raises(CaseFileError):
        case(expected, ("evaluations",), operation="evaluate", relative_tolerance=tolerances, exact=True)


def test_exact_compares_bits() -> None:
    expected: JsonObject = {"status": "met", "reasons": [], "value": -0.0}
    assert differences(case(expected, exact=True), {"status": "met", "reasons": [], "value": -0.0}) == []
    assert differences(case(expected, exact=True), {"status": "met", "reasons": [], "value": 0.0})


def test_a_bool_never_equals_a_number() -> None:
    expected: JsonObject = {"status": "met", "reasons": [], "value": [1.0]}
    assert differences(case(expected, exact=True), {"status": "met", "reasons": [], "value": [True]})


def test_a_listing_is_a_set() -> None:
    water: JsonObject = {"id": "conformance/water_fixture", "version": "1.0.0"}
    glycerol: JsonObject = {"id": "conformance/glycerol_fixture", "version": "1.0.0"}
    listing = case({"status": "met", "reasons": [], "value": [water, glycerol]}, operation="list_records")
    assert differences(listing, {"status": "met", "reasons": [], "value": [glycerol, water]}) == []
    assert differences(listing, {"status": "met", "reasons": [], "value": [water]})
    assert differences(listing, {"status": "met", "reasons": [], "value": [water, glycerol, {"id": "x"}]})


TEMPERATURE: JsonObject = {
    "name": "temperature",
    "status": "met",
    "record": {"value": 310.15, "unit": "K", "basis": "stated"},
    "operating": {"value": 310.15, "unit": "K"},
}
SHEAR_RATE: JsonObject = {"name": "shear_rate", "status": "unknown", "record": {"status": "unstated"}}
HUMIDITY: JsonObject = {"name": "humidity", "status": "unknown"}
CONDITIONS = ("status", "reasons", "conditions")


def test_conditions_are_a_set_keyed_by_name() -> None:
    expected: JsonObject = {
        "status": "unknown",
        "reasons": [UNSTATED],
        "conditions": [TEMPERATURE, SHEAR_RATE],
    }
    compared = case(expected, CONDITIONS, exact=True)
    by_name: list[JsonValue] = [
        entry for entry in sorted((TEMPERATURE, SHEAR_RATE), key=lambda entry: str(entry["name"]))
    ]
    assert differences(compared, {**expected, "conditions": by_name}) == []
    assert differences(compared, {**expected, "conditions": [SHEAR_RATE, TEMPERATURE]}) == []
    wrong: list[list[JsonValue]] = [
        [TEMPERATURE],
        [TEMPERATURE, SHEAR_RATE, HUMIDITY],
        [TEMPERATURE, SHEAR_RATE, SHEAR_RATE],
        [TEMPERATURE, {**SHEAR_RATE, "status": "met"}],
        [TEMPERATURE, {"status": "unknown", "record": {"status": "unstated"}}],
    ]
    for entries in wrong:
        assert differences(compared, {**expected, "conditions": entries}), entries


def test_a_case_that_expects_a_condition_twice_is_a_defect() -> None:
    expected: JsonObject = {
        "status": "unknown",
        "reasons": [UNSTATED],
        "conditions": [SHEAR_RATE, SHEAR_RATE],
    }
    with pytest.raises(CaseFileError):
        differences(case(expected, CONDITIONS, exact=True), {**expected, "conditions": [SHEAR_RATE]})


def test_an_alternative_entry_compares_its_conditions_and_labels_as_the_results() -> None:
    first: JsonObject = {
        "alternative": 0.0,
        "value": 0.000692,
        "conditions": [TEMPERATURE, SHEAR_RATE],
        "labels": ["materica.fluid.newtonian.v1", "mixed_conditions"],
    }
    second: JsonObject = {"alternative": 1.0, "value": 0.000695, "conditions": [TEMPERATURE], "labels": []}
    expected: JsonObject = {
        "status": "unknown",
        "reasons": [{"code": "no_pick"}],
        "alternative_values": [first, second],
    }
    no_pick = case(expected, ("status", "reasons", "alternative_values"), exact=True)
    permuted: JsonObject = {
        **first,
        "conditions": [SHEAR_RATE, TEMPERATURE],
        "labels": ["mixed_conditions", "hash_not_checked", "materica.fluid.newtonian.v1"],
    }
    unlabelled: JsonObject = {key: value for key, value in second.items() if key != "labels"}
    assert differences(no_pick, {**expected, "alternative_values": [permuted, second]}) == []
    assert differences(no_pick, {**expected, "alternative_values": [first, unlabelled]}) == []
    wrong: list[list[JsonValue]] = [
        [second, first],
        [first],
        [{**first, "conditions": [TEMPERATURE]}, second],
        [{**first, "conditions": [TEMPERATURE, SHEAR_RATE, HUMIDITY]}, second],
        [{**first, "labels": ["materica.fluid.newtonian.v1"]}, second],
        [{**first, "specimen": {}}, second],
        [{key: value for key, value in first.items() if key != "value"}, second],
    ]
    for entries in wrong:
        assert differences(no_pick, {**expected, "alternative_values": entries}), entries
    hashed = case(expected, ("status", "reasons", "alternative_values"), exact=True, claims={"hash": True})
    assert differences(hashed, {**expected, "alternative_values": [permuted, second]})


@pytest.mark.parametrize(
    ("variants", "outcome"),
    [
        pytest.param([Outcome.PASSED, Outcome.PASSED], Outcome.PASSED, id="all_passed"),
        pytest.param([Outcome.PASSED, Outcome.NOT_RUN], Outcome.PASSED, id="one_ran"),
        pytest.param([Outcome.PASSED, Outcome.FAILED], Outcome.FAILED, id="one_failed"),
        pytest.param([Outcome.VERIFIED, Outcome.NOT_RUN], Outcome.VERIFIED, id="one_verified"),
        pytest.param([Outcome.VERIFIED, Outcome.FAILED], Outcome.FAILED, id="one_verified_one_failed"),
        pytest.param([Outcome.NOT_RUN, Outcome.NOT_YET_RUNNABLE], Outcome.NOT_RUN, id="none_ran"),
        pytest.param([Outcome.NOT_YET_RUNNABLE], Outcome.NOT_YET_RUNNABLE, id="no_executor"),
        pytest.param([], Outcome.NOT_RUN, id="no_variants"),
    ],
)
def test_a_case_that_did_not_run_never_passes(variants: list[Outcome], outcome: Outcome) -> None:
    assert runner.case_outcome(variants) is outcome


@pytest.mark.parametrize(
    ("claims", "claimed", "outcome"),
    [
        pytest.param({"hash": False}, {"hash"}, Outcome.NOT_RUN, id="claim_absent_but_claimed"),
        pytest.param(
            {"fits_and_reference_data": True}, {"hash"}, Outcome.NOT_RUN, id="claim_present_not_claimed"
        ),
        pytest.param({}, {"plain_read"}, Outcome.NOT_RUN, id="suite_not_claimed"),
        pytest.param({"fits_and_reference_data": False}, {"hash"}, Outcome.PASSED, id="control_claims_agree"),
    ],
)
def test_claims_decide_which_variants_run(claims: JsonObject, claimed: set[Suite], outcome: Outcome) -> None:
    ran: list[CaseFile] = []

    def execute(case_file: CaseFile, claims: frozenset[Suite]) -> JsonObject:
        ran.append(case_file)
        return {"status": "met", "reasons": []}

    case_file = case({"status": "met", "reasons": []}, claims=claims)
    run = runner.run(case_file, configurations=[frozenset(claimed)], executors={"content_hash": execute})
    assert run.outcome is outcome
    assert bool(ran) is (outcome is Outcome.PASSED)


def test_a_case_runs_under_every_configuration_that_agrees_and_fails_if_one_fails() -> None:
    without_fd: frozenset[Suite] = frozenset({"hash"})
    with_fd: frozenset[Suite] = frozenset({"hash", "fits_and_reference_data"})
    with_plain_read: frozenset[Suite] = frozenset({"plain_read", "hash", "fits_and_reference_data"})
    given: list[frozenset[Suite]] = []

    def execute(case_file: CaseFile, claims: frozenset[Suite]) -> JsonObject:
        given.append(claims)
        return {"status": "met" if claims == with_fd else "unknown", "reasons": []}

    case_file = case({"status": "met", "reasons": []}, claims={"fits_and_reference_data": True})
    run = runner.run(
        case_file,
        configurations=[without_fd, with_fd, with_plain_read],
        executors={"content_hash": execute},
    )
    assert given == [with_fd, with_plain_read]
    assert run.claimed == (with_fd, with_plain_read)
    assert run.outcome is Outcome.FAILED
    assert [difference.partition(":")[0] for difference in run.differences] == [
        "claiming fits_and_reference_data, hash, plain_read"
    ]


# A table evaluation case's entries, one of each kind (README, "Case files"): at an interior knot, between
# knots, where the readable range is one point, outside it, and at an edge. The comparison reads no table, so
# the request holds none.
EVALUATIONS: list[JsonValue] = [
    {"in_range": True, "value": 996.0, "derivative": {"left": -0.2, "right": -0.3}},
    {"in_range": True, "value": 992.85, "derivative": -0.3},
    {"in_range": True, "value": 993.0, "derivative": "none"},
    {"in_range": False, "value": 1000.0, "derivative": 0.0},
    {"refused": True},
]
AT: list[JsonValue] = [300.0, 310.5, 310.0, 279.0, 273.0]


def answer(side: str) -> list[JsonValue]:
    """A right answer, from an evaluator declaring `side`."""
    return [
        {"refused": False, "in_range": True, "value": 996.0, "derivative": -0.2 if side == "left" else -0.3},
        {"refused": False, "in_range": True, "value": 992.85, "derivative": -0.3},
        {"refused": False, "in_range": True, "value": 993.0},
        {"refused": False, "in_range": False, "value": 1000.0, "derivative": 0.0},
        {"refused": True},
    ]


def evaluation_case(
    evaluations: list[JsonValue] = EVALUATIONS, at: list[JsonValue] = AT, tolerance: JsonValue = None
) -> CaseFile:
    document: JsonObject = {
        "case": "TE-099",
        "variant": "arm",
        "suite": "table_evaluation",
        "schema_version": "0.1.0",
        "inputs": {},
        "request": {"operation": "evaluate", "form": "table", "table": {}, "at": at},
        "expected": {"evaluations": evaluations},
        "compare": {
            "members": ["evaluations"],
            "relative_tolerance": {"binary64": 1e-12, "binary32": 3e-7} if tolerance is None else tolerance,
        },
    }
    return CaseFile.from_document(Path("TE-099.arm.json"), document)


def run_of(evaluations: list[JsonValue], precision: str = "binary64", side: str = "left") -> JsonObject:
    return {"precision": precision, "side": side, "evaluations": evaluations}


def evaluated(*runs: JsonObject) -> JsonObject:
    listed: list[JsonValue] = list(runs)
    return {"runs": listed}


def changed(index: int, entry: JsonValue, side: str = "left") -> list[JsonValue]:
    evaluations = answer(side)
    evaluations[index] = entry
    return evaluations


def test_a_table_evaluation_passes_under_the_side_each_run_declares() -> None:
    both = evaluated(run_of(answer("left"), side="left"), run_of(answer("right"), side="right"))
    assert differences(evaluation_case(), both) == []
    assert differences(evaluation_case(), evaluated(run_of(answer("right"), side="left")))
    assert differences(evaluation_case(), evaluated(run_of(answer("left"), side="right")))


def test_its_entries_are_compared_in_order_one_per_axis_value() -> None:
    swapped = answer("left")
    swapped[1], swapped[3] = swapped[3], swapped[1]
    assert differences(evaluation_case(), evaluated(run_of(swapped)))
    assert differences(evaluation_case(), evaluated(run_of(answer("left")[:-1])))
    assert differences(evaluation_case(), evaluated(run_of([*answer("left"), {"refused": True}])))


NAN = math.nan


@pytest.mark.parametrize(
    ("index", "entry"),
    [
        pytest.param(4, {"refused": True, "in_range": False}, id="refused_beside_in_range"),
        pytest.param(4, {"refused": True, "value": NAN, "derivative": NAN}, id="refused_beside_nan"),
        # A JSON `null` is no number: it reads as absent, beside a refusal as elsewhere.
        pytest.param(4, {"refused": True, "value": None, "derivative": None}, id="refused_beside_null"),
        pytest.param(
            3, {"refused": False, "in_range": False, "value": None, "derivative": None}, id="outside_null"
        ),
        pytest.param(
            2, {"refused": False, "in_range": True, "value": 993.0, "derivative": None}, id="none_as_null"
        ),
        pytest.param(3, {"refused": False, "in_range": False}, id="outside_without_numbers"),
        pytest.param(
            3, {"refused": False, "in_range": False, "value": NAN, "derivative": NAN}, id="outside_nan"
        ),
        pytest.param(
            3, {"refused": False, "in_range": False, "value": 1000.0, "derivative": -0.0}, id="minus_zero"
        ),
        pytest.param(
            2, {"refused": False, "in_range": True, "value": 993.0, "derivative": NAN}, id="none_as_nan"
        ),
        pytest.param(
            1,
            {"refused": False, "in_range": True, "value": 992.85 * (1 + 5e-13), "derivative": -0.3},
            id="tolerance",
        ),
    ],
)
def test_an_entry_compares_only_what_it_holds_and_a_number_may_be_absent_or_nan_where_the_text_says(
    index: int, entry: JsonObject
) -> None:
    assert differences(evaluation_case(), evaluated(run_of(changed(index, entry)))) == []


@pytest.mark.parametrize(
    ("index", "entry"),
    [
        pytest.param(
            4, {"refused": False, "in_range": True, "value": 1000.0, "derivative": -0.05}, id="not_refused"
        ),
        pytest.param(4, {"refused": True, "value": 1000.0}, id="refused_beside_a_value"),
        pytest.param(
            4, {"refused": True, "value": math.inf, "derivative": math.inf}, id="refused_beside_infinity"
        ),
        pytest.param(4, {"refused": True, "value": NAN, "derivative": -0.05}, id="refused_beside_one_number"),
        pytest.param(
            4, {"refused": True, "value": None, "derivative": -0.05}, id="refused_beside_null_and_a_number"
        ),
        pytest.param(4, {"refused": True, "derivative": -math.inf}, id="refused_beside_minus_infinity"),
        pytest.param(4, {"in_range": False}, id="refusal_unreported"),
        pytest.param(1, {"refused": True}, id="refused_where_none_is_due"),
        pytest.param(3, {"refused": True}, id="refused_outside"),
        # The right answer but for the refusal, so that only the refusal can fail it.
        pytest.param(
            1,
            {"refused": True, "in_range": True, "value": 992.85, "derivative": -0.3},
            id="refused_beside_the_right_answer",
        ),
        pytest.param(
            3,
            {"refused": True, "in_range": False, "value": 1000.0, "derivative": 0.0},
            id="refused_beside_the_right_answer_outside",
        ),
        pytest.param(
            3, {"refused": False, "in_range": True, "value": 1000.0, "derivative": 0.0}, id="in_range"
        ),
        pytest.param(
            3, {"refused": False, "in_range": False, "value": 999.0, "derivative": 0.0}, id="outside_value"
        ),
        pytest.param(3, {"refused": False, "in_range": False, "value": math.inf}, id="outside_infinity"),
        pytest.param(
            3,
            {"refused": False, "in_range": False, "value": 1000.0, "derivative": 1e-300},
            id="zero_by_tolerance",
        ),
        pytest.param(
            2, {"refused": False, "in_range": True, "value": 993.0, "derivative": -0.3}, id="not_none"
        ),
        pytest.param(1, {"refused": False, "in_range": True, "derivative": -0.3}, id="inside_without_value"),
        pytest.param(
            1, {"refused": False, "in_range": True, "value": NAN, "derivative": -0.3}, id="inside_nan"
        ),
        pytest.param(
            1,
            {"refused": False, "in_range": True, "value": 992.85 * (1 + 2e-12), "derivative": -0.3},
            id="off",
        ),
        pytest.param(
            0, {"refused": False, "in_range": True, "value": 996.0, "derivative": -0.3}, id="other_side"
        ),
        pytest.param(0, {"refused": False, "in_range": True, "value": 996.0}, id="knot_without_derivative"),
    ],
)
def test_an_entry_that_breaks_the_text_fails(index: int, entry: JsonObject) -> None:
    assert differences(evaluation_case(), evaluated(run_of(changed(index, entry))))


def test_the_tolerance_is_the_claimed_precisions() -> None:
    near = changed(1, {"refused": False, "in_range": True, "value": 992.85 * (1 + 1e-9), "derivative": -0.3})
    assert differences(evaluation_case(), evaluated(run_of(near, precision="binary32"))) == []
    assert differences(evaluation_case(), evaluated(run_of(near, precision="binary64")))


def test_an_expected_value_of_zero_takes_the_tolerance_as_absolute() -> None:
    zero_case = evaluation_case([{"in_range": True, "value": 0.0, "derivative": -1.0}], [1.0])
    entry: JsonObject = {"refused": False, "in_range": True, "derivative": -1.0}
    assert differences(zero_case, evaluated(run_of([{**entry, "value": 1e-13}]))) == []
    assert differences(zero_case, evaluated(run_of([{**entry, "value": 1e-11}])))


@pytest.mark.parametrize(
    "result",
    [
        pytest.param({}, id="no_runs"),
        pytest.param(evaluated(), id="empty_runs"),
        pytest.param(evaluated(run_of(answer("left"), precision="bfloat16")), id="unknown_precision"),
        pytest.param(evaluated(run_of(answer("left"), side="both")), id="unknown_side"),
        pytest.param(
            evaluated(run_of(answer("left")), run_of(answer("left"), precision="binary32", side="right")),
            id="one_run_of_two_wrong",
        ),
    ],
)
def test_every_run_is_compared_and_one_is_needed(result: JsonObject) -> None:
    assert differences(evaluation_case(), result)


def test_a_table_evaluation_case_that_breaks_the_case_rules_is_a_defect() -> None:
    with pytest.raises(CaseFileError):
        differences(evaluation_case(tolerance=1e-12), evaluated(run_of(answer("left"))))
    with pytest.raises(CaseFileError):
        differences(evaluation_case(at=AT[:-1]), evaluated(run_of(answer("left"))))


@pytest.mark.parametrize(
    "table",
    [
        pytest.param({}, id="no_members"),
        pytest.param({"x": [0.0, 1.0], "y": [0.0, 1.0], "scheme": "cubic", "edges": []}, id="unknown_scheme"),
        pytest.param({"x": [1.0, 0.0], "y": [0.0, 1.0], "scheme": "linear", "edges": []}, id="x_decreasing"),
        pytest.param(
            {"x": [0.0, 1.0], "y": [0.0, 1.0], "scheme": "linear", "edges": [], "source_range": [0.5]},
            id="source_range_of_one_number",
        ),
    ],
)
def test_a_table_evaluation_case_whose_table_the_record_format_refuses_is_a_defect(table: JsonObject) -> None:
    case_file = evaluation_case([{"in_range": True, "value": 0.5, "derivative": 1.0}], [0.5])
    request = case_file.request
    assert isinstance(request, dict)
    broken = replace(case_file, request={**request, "table": table})
    with pytest.raises(CaseFileError):
        runner.EXECUTORS["evaluate"](broken, runner.REFERENCE_EVALUATOR)
    control = replace(
        case_file,
        request={**request, "table": {"x": [0.0, 1.0], "y": [0.0, 1.0], "scheme": "linear", "edges": []}},
    )
    assert differences(control, runner.EXECUTORS["evaluate"](control, runner.REFERENCE_EVALUATOR)) == []


def test_a_table_evaluation_case_that_passes_is_verified_never_passed() -> None:
    def execute(case_file: CaseFile, claims: frozenset[Suite]) -> JsonObject:
        return evaluated(run_of(answer("left")))

    configurations = [runner.REFERENCE_EVALUATOR]
    run = runner.run(evaluation_case(), configurations=configurations, executors={"evaluate": execute})
    assert run.outcome is Outcome.VERIFIED
    control = case({"status": "met", "reasons": []})
    run = runner.run(
        control,
        configurations=[frozenset({"hash"})],
        executors={"content_hash": lambda case_file, claims: {"status": "met", "reasons": []}},
    )
    assert run.outcome is Outcome.PASSED


# A build's report (README, "Case files"; the S7 design's 5.1).

BUILD_MEMBERS = ("refusals", "results", "watches", "unused")


def build_case(
    refusals: list[JsonValue],
    rules: tuple[str, ...] = (),
    result_members: tuple[str, ...] = (),
    **expected: JsonValue,
) -> CaseFile:
    compare: JsonObject = {"members": list(BUILD_MEMBERS), "exact": True}
    if rules:
        compare["rules_compared"] = list(rules)
    if result_members:
        compare["result_members"] = list(result_members)
    document: JsonObject = {
        "case": "BC-048",
        "variant": "arm",
        "suite": "build_checks",
        "schema_version": "0.1.0",
        "inputs": {"records": [], "declaration": "a.json"},
        "request": {"operation": "check_build"},
        "expected": {"refusals": refusals, **expected},
        "compare": compare,
    }
    return CaseFile.from_document(Path("BC-048.arm.json"), document)


def refusal(item: str, pointer: str, **more: JsonValue) -> JsonObject:
    return {"item": item, "pointer": pointer, **more}


REPORT: JsonObject = {
    "records": [],
    "refusals": [refusal("BC-048", "/models/1"), refusal("BC-051", "/sampling", detail="words")],
    "results": [],
    "unused": [],
}


def test_a_builds_refusals_are_a_set_of_item_and_pointer_and_detail_is_never_compared() -> None:
    expected: list[JsonValue] = [refusal("BC-051", "/sampling"), refusal("BC-048", "/models/1")]
    assert differences(build_case(expected), REPORT) == []
    assert differences(build_case(expected), {**REPORT, "refusals": [*expected, expected[0]]}) == []


@pytest.mark.parametrize(
    "refusals",
    [
        [refusal("BC-048", "/models/1")],
        [refusal("BC-048", "/models/1"), refusal("BC-051", "/sampling"), refusal("BC-048", "")],
        [refusal("BC-048", "/models/0"), refusal("BC-051", "/sampling")],
        [refusal("BC-040", "/models/1"), refusal("BC-051", "/sampling")],
        [{"item": "BC-048"}, refusal("BC-051", "/sampling")],
    ],
)
def test_a_refusal_missing_extra_or_moved_fails(refusals: list[JsonValue]) -> None:
    expected: list[JsonValue] = [refusal("BC-048", "/models/1"), refusal("BC-051", "/sampling")]
    found = differences(build_case(expected), {**REPORT, "refusals": refusals})
    assert len(found) == 1
    assert found[0].startswith("refusals: ")


def test_only_the_rules_compared_are_compared_where_a_case_names_them() -> None:
    expected: list[JsonValue] = [refusal("BC-051", "/sampling")]
    assert differences(build_case(expected, ("BC-051",)), REPORT) == []
    assert differences(build_case(expected), REPORT) != []
    assert differences(build_case([], ("BC-040",)), REPORT) == []
    assert differences(build_case([refusal("BC-040", "/models/0")], ("BC-040",)), REPORT) != []


@pytest.mark.parametrize("member", ["results", "watches", "unused"])
def test_a_list_compared_and_not_expected_must_be_absent_or_empty(member: str) -> None:
    expected: list[JsonValue] = [refusal("BC-048", "/models/1"), refusal("BC-051", "/sampling")]
    without = {name: held for name, held in REPORT.items() if name != member}
    assert differences(build_case(expected), without) == []
    assert differences(build_case(expected), {**REPORT, member: []}) == []
    assert differences(build_case(expected), {**REPORT, member: [{"model": "drag", "acceptance": 0}]}) == [
        f"{member}: must be absent or empty, got [{{'model': 'drag', 'acceptance': 0}}]"
    ]


def test_a_build_case_that_expects_watches_is_not_compared_before_s7a_4() -> None:
    watch: JsonValue = {"model": "drag", "field": "fluid.dynamic_viscosity", "condition": "temperature"}
    with pytest.raises(CaseFileError, match="arrives with S7a-4"):
        differences(build_case([], watches=[watch]), REPORT)


# A build's results: "compared as a set keyed by `model`, the location and `field` ...; each result's members
# compared as a read result's are (above), `accepted_by` as a set of indexes, and `not_accepted` as a
# multiset of reasons, as `reasons` are, and of specimen differences by `section` and `fact`"; and `unused`,
# "as a set of `{"model", "acceptance"}`".

WATER_PIN: JsonObject = {"id": "conformance/water_fixture", "version": "1.0.0", "content_hash": "sha256:0"}
PLASMA_PIN: JsonObject = {"id": "conformance/plasma_fixture", "version": "1.0.0", "content_hash": "sha256:1"}
VERDICT = ("status", "reasons", "value", "accepted", "accepted_by", "not_accepted")


def a_result(record: JsonObject = WATER_PIN, model: str = "drag", **members: JsonValue) -> JsonObject:
    return {
        "model": model,
        "record": record,
        "field": "fluid.dynamic_viscosity",
        "status": "unknown",
        "reasons": [UNSTATED],
        "accepted": True,
        "accepted_by": [0.0],
        "not_accepted": [],
        **members,
    }


def results_case(*results: JsonObject, members: tuple[str, ...] = VERDICT) -> CaseFile:
    return build_case([], result_members=members, results=list(results))


def with_results(*results: JsonValue, unused: list[JsonValue] | None = None) -> JsonObject:
    return {**REPORT, "refusals": [], "results": list(results), "unused": unused or []}


def test_a_builds_results_are_a_set_keyed_by_model_location_and_field() -> None:
    expected = results_case(a_result(), a_result(PLASMA_PIN))
    assert differences(expected, with_results(a_result(PLASMA_PIN), a_result())) == []
    for found in (
        with_results(a_result()),
        with_results(a_result(), a_result(PLASMA_PIN), a_result(PLASMA_PIN, model="lift")),
        with_results(a_result(), a_result(PLASMA_PIN), a_result()),
        with_results(a_result(), a_result({**PLASMA_PIN, "content_hash": "sha256:2"})),
        with_results(a_result(), {**a_result(PLASMA_PIN), "field": "bulk.density"}),
        with_results(a_result(), "not a result"),
    ):
        (difference,) = differences(expected, found)
        assert difference.startswith("results: "), difference


def test_an_expected_result_given_twice_is_a_defect_in_the_case() -> None:
    with pytest.raises(CaseFileError, match="twice"):
        differences(results_case(a_result(), a_result()), with_results(a_result()))


@pytest.mark.parametrize(
    ("changed", "member"),
    [
        ({"status": "not_met"}, "status"),
        ({"reasons": [UNSTATED, UNSTATED]}, "reasons"),
        ({"reasons": [{**UNSTATED, "alternative": 1.0}]}, "reasons"),
        ({"accepted": False}, "accepted"),
        ({"accepted_by": [1.0]}, "accepted_by"),
        ({"accepted_by": [0.0, 1.0]}, "accepted_by"),
        ({"accepted_by": [-0.0]}, "accepted_by"),
        ({"accepted_by": [True]}, "accepted_by"),
        ({"not_accepted": [UNSTATED]}, "not_accepted"),
        ({"not_accepted": [{"section": "fluid", "fact": "species"}]}, "not_accepted"),
        ({"value": 0.000692}, "value"),
    ],
)
def test_a_result_member_compared_that_differs_fails(changed: JsonObject, member: str) -> None:
    (difference,) = differences(results_case(a_result()), with_results({**a_result(), **changed}))
    assert difference.startswith(f"results: {runner.result_key(a_result())}: {member}: "), difference


def test_accepted_by_is_a_set_and_not_accepted_a_multiset() -> None:
    expected = a_result(accepted=False, accepted_by=[0.0, 2.0], not_accepted=[UNSTATED, UNSTATED, MALFORMED])
    found = a_result(
        accepted=False, accepted_by=[2.0, 0.0, 0.0], not_accepted=[MALFORMED, UNSTATED, UNSTATED]
    )
    assert differences(results_case(expected), with_results(found)) == []
    fewer: JsonObject = {**found, "not_accepted": [MALFORMED, UNSTATED]}
    assert differences(results_case(expected), with_results(fewer)) != []
    difference: JsonObject = {"section": "fluid", "fact": "species", "record": {"status": "unstated"}}
    with_difference = a_result(accepted=False, not_accepted=[difference])
    other_record: JsonObject = {**difference, "record": {"status": "not_applicable"}}
    assert (
        differences(
            results_case(with_difference), with_results(a_result(accepted=False, not_accepted=[other_record]))
        )
        == []
    )
    # A specimen difference is its section and its fact: another of either is another difference.
    for name, other in (("section", "tissue"), ("fact", "genus")):
        moved: JsonObject = {**difference, name: other}
        (found_difference,) = differences(
            results_case(with_difference), with_results(a_result(accepted=False, not_accepted=[moved]))
        )
        assert found_difference.startswith("results: "), name
        assert "not_accepted: missing" in found_difference, name


def test_only_the_result_members_named_are_compared_and_one_named_not_expected_must_be_absent() -> None:
    found = a_result(labels=["materica.fluid.newtonian.v1"], provenance={"origin": "derived"})
    assert differences(results_case(a_result()), with_results(found)) == []
    (difference,) = differences(
        results_case(a_result(), members=(*VERDICT, "provenance")), with_results(found)
    )
    assert difference.endswith("provenance: must be absent, got {'origin': 'derived'}")
    assert differences(results_case(a_result(), members=(*VERDICT, "labels")), with_results(found)) != []


def test_unused_acceptances_are_a_set_of_model_and_index() -> None:
    expected = build_case(
        [], unused=[{"model": "drag", "acceptance": 1.0}, {"model": "lift", "acceptance": 0.0}]
    )
    report = with_results(unused=[{"model": "lift", "acceptance": 0.0}, {"model": "drag", "acceptance": 1.0}])
    assert differences(expected, report) == []
    for unused in (
        [{"model": "drag", "acceptance": 1.0}],
        [{"model": "drag", "acceptance": 1.0}, {"model": "drag", "acceptance": 0.0}],
        [{"model": "drag", "acceptance": 1.0}, {"model": "lift", "acceptance": 0.0}, {"model": "lift"}],
    ):
        (difference,) = differences(expected, with_results(unused=cast(list[JsonValue], unused)))
        assert difference.startswith("unused: "), difference
