# SPDX-License-Identifier: Apache-2.0
"""Examples of the build's report (`declarations.md` section 2; the S7 design's 4.2 and 4.5): a result's
members and its JSON, the value to use and the two values that are not one, the verdict on the build, the
result looked up, the watches S7a-4 emits, and the lines `materica status` prints, each reason nothing covers
beside what would cover it, from section 4.2's table."""

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import materica
from materica import shapes
from materica.core import report
from materica.core.build import check_build
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult
from materica.core.reasons import Reason
from materica.core.report import BuildRefusal, BuildReport, BuildResult, UnusedAcceptance
from materica.core.vocabulary import VOCABULARY
from tests.spec_sync.schemas import validator

BUILD_CHECKS = Path(materica.__file__).parent / "data" / "conformance" / "build_checks"
WATER = MaterialRef(
    "conformance/water_fixture",
    "1.0.0",
    "sha256:c21a2c7f46e66bcfb5e74f18d2a08644468d5a92bafb4fa57a03651facf96e2d",
)
VISCOSITY = "fluid.dynamic_viscosity"


def built(name: str) -> BuildReport:
    """The report of a build-check file's declaration over its records."""
    document = json.loads((BUILD_CHECKS / "cases" / f"{name}.json").read_text(encoding="utf-8"))
    store = materica.load_records(
        [BUILD_CHECKS / "inputs" / record for record in document["inputs"]["records"]]
    )
    return check_build((BUILD_CHECKS / "inputs" / document["inputs"]["declaration"]).read_bytes(), store)


def a_result(
    read: ReadResult | None, *, accepted: bool = True, trainable_by: int | None = None
) -> BuildResult:
    reasons = () if read is None else read.reasons
    return BuildResult(
        "drag",
        WATER,
        VISCOSITY,
        read,
        reasons,
        "unknown" if read is None else read.status,
        accepted,
        (0,) if accepted else (),
        () if accepted else reasons,
        trainable_by=trainable_by,
    )


def assumed(kind: str) -> ReadResult:
    assumption = cast(shapes.Assumption, {"acceptance": kind, "value": 0.0007})
    return ReadResult("not_met", (Reason("want_mismatch"),), value=0.0007, unit="Pa.s", assumption=assumption)


MET = ReadResult("met", (), ("materica.fluid.newtonian.v1",), value=0.000692, unit="Pa.s")


# "`value`, and the two values that are not one" (the S7 design's 4.2): the value at the operating
# conditions where accepted, the end value under an extrapolation, the initial value on a trainable field,
# and none on a result not accepted or with no value.


@pytest.mark.parametrize(
    ("result", "values"),
    [
        pytest.param(a_result(MET), (0.000692, None, None), id="met"),
        pytest.param(a_result(assumed("nominal")), (0.0007, None, None), id="under_a_nominal"),
        pytest.param(a_result(assumed("extrapolation")), (None, 0.0007, None), id="under_an_extrapolation"),
        pytest.param(a_result(MET, trainable_by=0), (None, None, 0.000692), id="trainable"),
        pytest.param(a_result(MET, accepted=False), (None, None, None), id="not_accepted"),
        pytest.param(
            a_result(assumed("extrapolation"), accepted=False), (None, None, None), id="not_accepted_end"
        ),
        pytest.param(a_result(None), (None, None, None), id="no_read"),
    ],
)
def test_the_value_to_use_and_the_two_that_are_not_the_value_at_the_operating_conditions(
    result: BuildResult, values: tuple[object, object, object]
) -> None:
    assert (result.value, result.end_value, result.initial_value) == values


def test_a_results_read_members_are_read_from_its_read() -> None:
    result = a_result(MET)
    assert (result.unit, result.labels, result.conditions, result.provenance, result.assumption) == (
        "Pa.s",
        ("materica.fluid.newtonian.v1",),
        None,
        None,
        None,
    )
    nothing = a_result(None)
    assert (nothing.unit, nothing.labels, nothing.conditions, nothing.provenance) == (None, (), None, None)


# A result's JSON (section 2): "the read result ... with `model`, ... `record`, `field`,
# `specimen_differences`, `accepted`, `accepted_by`, `not_accepted` ... added", its status and reasons the
# build's (item 8); a field read with no requirement "holds `status`, `reasons` and the build's members
# alone" (section 1 item 1).


def test_a_results_json_is_its_reads_with_the_builds_reasons_status_and_members() -> None:
    read = ReadResult("unknown", (Reason("condition_unstated", "shear_rate"),), value=0.000692, unit="Pa.s")
    result = BuildResult(
        "drag", WATER, VISCOSITY, read, (*read.reasons, Reason("label_mismatch")), "not_met", False, (), ()
    )
    assert dict(result.to_json()) == {
        "model": "drag",
        "record": WATER.to_json(),
        "field": VISCOSITY,
        "status": "not_met",
        "reasons": [{"code": "condition_unstated", "condition": "shear_rate"}, {"code": "label_mismatch"}],
        "value": 0.000692,
        "unit": "Pa.s",
        "labels": [],
        "specimen_differences": [],
        "accepted": False,
        "accepted_by": [],
        "not_accepted": [],
    }


def test_a_field_read_with_no_requirement_holds_no_member_of_a_read() -> None:
    result = BuildResult(
        "drag", WATER, VISCOSITY, None, (Reason("no_requirement"),), "unknown", True, (0,), ()
    )
    assert set(result.to_json()) == {
        "model",
        "record",
        "field",
        "status",
        "reasons",
        "specimen_differences",
        "accepted",
        "accepted_by",
        "not_accepted",
    }
    assert (
        "trainable_by"
        in BuildResult("drag", WATER, VISCOSITY, None, (), "met", True, (), (), trainable_by=0).to_json()
    )


def test_each_results_json_validates_against_the_reports_field_result() -> None:
    report = built("BC-003.field_read_with_no_requirement_waived")
    assert validator("build_report.json")(cast(JsonValue, report.to_json())) == []
    field_result = validator("build_report.json#/$defs/field_result")
    for result in [a_result(MET), a_result(None), a_result(assumed("nominal"))]:
        assert field_result(cast(JsonValue, result.to_json())) == []


# The verdict on the build (section 2 item 5): "The build MUST refuse to build while any result is not
# accepted", and while the report holds a refusal.


def test_the_build_is_refused_where_a_result_is_not_accepted_or_the_declaration_refused() -> None:
    assert not BuildReport((), {}, results=(a_result(MET), a_result(MET))).refused
    assert BuildReport((), {}, results=(a_result(MET), a_result(MET, accepted=False))).refused
    assert BuildReport((BuildRefusal("BC-048", ""),), {}).refused
    assert not BuildReport((), {}).refused
    assert not built("BC-010.all_accepted").refused
    assert built("BC-010.one_accepted_one_not_in_one_model").refused
    assert built("BC-010.two_models_each_not_accepted").refused


def test_a_result_is_found_by_its_model_field_and_record_and_none_is_a_key_error() -> None:
    first, second = a_result(MET), BuildResult("lift", WATER, VISCOSITY, None, (), "unknown", True, (), ())
    report = BuildReport((), {}, results=(first, second))
    assert report.result("drag", VISCOSITY, WATER) is first
    assert report.result("lift", VISCOSITY, WATER) is second
    for model, field, record in (
        ("drag", "bulk.density", WATER),
        ("drag", VISCOSITY, MaterialRef(WATER.id, WATER.version, "sha256:" + "0" * 64)),
        ("buoyancy", VISCOSITY, WATER),
    ):
        with pytest.raises(KeyError):
            report.result(model, field, record)


def test_the_watches_raise_and_the_json_leaves_them_out() -> None:
    """Watches are S7a-4's: the report omits them rather than hold an empty list (the S7 design's 9)."""
    report = built("BC-009.one_waiver_index")
    with pytest.raises(NotImplementedError, match="S7a-4"):
        report.watches  # noqa: B018
    assert "watches" not in report.to_json()
    assert cast(list[JsonValue], report.to_json()["unused"]) == [{"model": "drag", "acceptance": 0}]
    assert report.consumer == {"name": "conformance_consumer", "version": "1.0.0"}


def test_the_reports_json_holds_its_records_results_and_unused() -> None:
    report = built("BC-053.unused_per_model")
    found = report.to_json()
    assert found["records"] == [WATER.to_json()]
    assert [(result["model"], result["accepted"]) for result in found["results"]] == [
        ("drag", True),
        ("lift", False),
    ]
    assert cast(list[JsonValue], found["unused"]) == [{"model": "lift", "acceptance": 0}]
    assert report.unused == (UnusedAcceptance("lift", 0),)


# What `materica status` prints (the S7 design's 4.5): pinned, since no case compares it. Each "covered by"
# line comes from section 4.2's rows through `coverage.json`; a reason no row lists prints "nothing covers
# it".


@pytest.mark.parametrize(
    ("name", "lines"),
    [
        pytest.param(
            "BC-010.one_accepted_one_not_in_one_model",
            [
                "build refused: 1 of 2 results not accepted; the declaration's own check passed",
                "  ok  drag  conformance/water_fixture 1.0.0  fluid.dynamic_viscosity  unknown, accepted by "
                "#0 (waiver: condition_unstated(shear_rate))",
                "  x   drag  conformance/glycerol_fixture 1.0.0  fluid.dynamic_viscosity  not_met",
                "        absent: nothing covers it (declarations.md 4.2)",
                "  unused: none",
            ],
            id="one_of_two_not_accepted",
        ),
        pytest.param(
            "BC-053.unused_per_model",
            [
                "build refused: 1 of 2 results not accepted; the declaration's own check passed",
                "  ok  drag  conformance/water_fixture 1.0.0  fluid.dynamic_viscosity  unknown, accepted by "
                "#0 (waiver: condition_unstated(shear_rate))",
                "  x   lift  conformance/water_fixture 1.0.0  fluid.dynamic_viscosity  unknown",
                "        condition_unstated(shear_rate): covered by a waiver naming that condition and code; "
                "or its trainable entry (section 7), on a result that carries a value (declarations.md 4.2), "
                "and nothing declared covers it",
                "  unused: lift #0 (waiver: condition_unchecked(shear_rate))",
            ],
            id="covered_by_and_unused",
        ),
        pytest.param(
            "BC-019.outside_range_under_an_extrapolation",
            [
                "build accepted: 1 result, each accepted; the declaration's own check passed",
                "  ok  drag  conformance/density_table_fixture 1.0.0  bulk.density  not_met, accepted by #0 "
                "(extrapolation, method constant): end value 1000.0 kg/m3, at the readable range's nearest "
                "end; the value at the operating conditions is yours to compute",
                "  unused: none",
            ],
            id="extrapolated",
        ),
        pytest.param(
            "BC-049.not_checked_gives_not_reviewed",
            [
                "build refused: 1 of 1 result not accepted; the declaration's own check passed",
                "  x   drag  conformance/water_fixture 1.0.0  fluid.dynamic_viscosity  unknown",
                "        not_reviewed: covered by a waiver naming that code (declarations.md 4.2), and "
                "nothing declared covers it",
                "  unused: none",
            ],
            id="not_reviewed",
        ),
        pytest.param(
            "BC-049.not_reviewed_waived",
            [
                "build accepted: 1 result, each accepted; the declaration's own check passed",
                "  ok  drag  conformance/water_fixture 1.0.0  fluid.dynamic_viscosity  unknown, accepted "
                "unreviewed by #0 (waiver: condition_unstated(shear_rate)), #1 (waiver: not_reviewed)",
                "  unused: none",
            ],
            id="accepted_unreviewed",
        ),
        pytest.param(
            "BC-005.waiver_without_reason",
            [
                "build refused: the declaration's own check refused it, 1 refusal",
                "  BC-005  /models/0/acceptances/0",
            ],
            id="refused_on_its_own",
        ),
    ],
)
def test_the_status_lines_of_a_report(name: str, lines: list[str]) -> None:
    assert list(built(name).status_lines()) == lines


def test_the_covered_by_lines_are_read_from_section_4_2s_table() -> None:
    """The control: the table read with `not_reviewed` dropped from its row, and with its waiver row's cell
    reworded, changes the lines, which are never written by hand."""
    rows = VOCABULARY.coverage
    dropped = tuple(
        replace(row, reasons=tuple(code for code in row.reasons if code != "not_reviewed")) for row in rows
    )
    reworded = tuple(
        replace(row, covered_by="a `waiver` of that code") if "not_reviewed" in row.reasons else row
        for row in rows
    )
    tail = "(declarations.md 4.2), and nothing declared covers it"
    line = f"        not_reviewed: covered by a waiver naming that code {tail}"
    assert line in built("BC-049.not_checked_gives_not_reviewed").status_lines()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(report, "VOCABULARY", replace(VOCABULARY, coverage=dropped))
        assert (
            "        not_reviewed: nothing covers it (declarations.md 4.2)"
            in built("BC-049.not_checked_gives_not_reviewed").status_lines()
        )
        patch.setattr(report, "VOCABULARY", replace(VOCABULARY, coverage=reworded))
        assert (
            f"        not_reviewed: covered by a waiver of that code {tail}"
            in built("BC-049.not_checked_gives_not_reviewed").status_lines()
        )
