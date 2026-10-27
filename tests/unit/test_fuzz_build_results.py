# SPDX-License-Identifier: Apache-2.0
"""The build's results relations of the fuzz oracle (`tests/fuzz/build_results_oracle.py`): quiet on every
build-check case's report as the build gives it, and each failing on a build broken for it, 4.2's own law and
the model's on the fault the S7 design names for the target's control (`_covers` letting a waiver naming
`condition_outside` cover it), the refusal law on `refused` read from the first model's results alone, the
model's on each member it compares of a result changed alone and on `refused`, and 4.2's own law on a reason
after one an assumption covers."""

import dataclasses
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import materica
from materica.core import acceptance
from materica.core.build import check_build
from materica.core.declarations import CLAIMS
from materica.core.reasons import Reason
from materica.core.report import BuildReport
from tests.conformance import runner
from tests.fuzz.build_results_oracle import check_against_the_model, check_results
from tests.fuzz.seeded_fault import faulty_covers

CASES = [case for case in runner.discover() if case.suite == "build_checks"]


def records_of(case: runner.CaseFile) -> list[Path]:
    return case.input_paths("records") if "records" in case.inputs else []


def report_of(case: runner.CaseFile) -> BuildReport | None:
    """The build's report on the case's declaration over its records, under the default claims; None where
    the build raises for what a later piece reads."""
    try:
        return check_build(case.input_bytes("declaration"), materica.load_records(records_of(case)))
    except NotImplementedError:
        return None


REPORTS = {case.path.name: report for case in CASES if (report := report_of(case)) is not None}


def against_the_model(case: runner.CaseFile, report: BuildReport) -> None:
    sources = [path.read_bytes() for path in records_of(case)]
    check_against_the_model(case.input_bytes("declaration"), sources, CLAIMS, report)


def test_every_build_check_cases_report_keeps_the_relations() -> None:
    assert len(REPORTS) > 100
    assert any(report.results for report in REPORTS.values())
    for case in CASES:
        if (report := REPORTS.get(case.path.name)) is not None:
            check_results(report)
            against_the_model(case, report)


def first_model_alone(report: BuildReport) -> bool:
    first = report.results[0].model if report.results else None
    return bool(report.refusals) or not all(
        result.accepted for result in report.results if result.model == first
    )


def failing(check: Callable[[BuildReport], None], report: BuildReport) -> bool:
    try:
        check(report)
    except AssertionError:
        return True
    return False


def test_4_2s_own_law_fails_where_a_waiver_covers_condition_outside(monkeypatch: pytest.MonkeyPatch) -> None:
    case = next(case for case in CASES if case.path.name == "BC-038.waiver_of_condition_outside.json")
    report = report_of(case)
    assert report is not None
    check_results(report)
    monkeypatch.setattr(acceptance, "_covers", faulty_covers)
    broken = report_of(case)
    assert broken is not None
    with pytest.raises(AssertionError, match="accepted with condition_outside"):
        check_results(broken)
    with pytest.raises(AssertionError, match="the model's"):
        against_the_model(case, broken)


def test_the_model_relation_fails_where_a_result_or_an_unused_acceptance_is_left_out() -> None:
    case = next(case for case in CASES if case.path.name == "BC-053.unused_per_model.json")
    report = report_of(case)
    assert report is not None
    against_the_model(case, report)
    assert report.results
    assert report.unused
    with pytest.raises(AssertionError, match=r"^results"):
        against_the_model(case, dataclasses.replace(report, results=report.results[1:]))
    with pytest.raises(AssertionError, match=r"^unused"):
        against_the_model(case, dataclasses.replace(report, unused=report.unused[1:]))


def test_the_refusal_law_fails_where_refused_reads_the_first_model_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BuildReport, "refused", property(first_model_alone))
    caught = [name for name, report in REPORTS.items() if failing(check_results, report)]
    assert caught, "no case's report holds a result not accepted after a first model's all accepted"
    assert all(len({result.model for result in REPORTS[name].results}) > 1 for name in caught), caught


def test_a_result_accepted_under_an_assumption_or_trainable_keeps_4_2s_law() -> None:
    """The law's own arms: `outside_range` under an extrapolation's assumption, and under a trainable
    acceptance on a result that carries a value, keep it; under a nominal's, it fails."""
    case = next(
        case for case in CASES if case.path.name == "BC-019.outside_range_under_an_extrapolation.json"
    )
    report = report_of(case)
    assert report is not None
    (result,) = report.results
    assert result.accepted
    assert result.assumption is not None
    check_results(report)
    assert result.read is not None
    nominal = dataclasses.replace(result.read, assumption={"acceptance": "nominal", "value": 1000.0})
    as_nominal = dataclasses.replace(report, results=(dataclasses.replace(result, read=nominal),))
    assert failing(check_results, as_nominal)
    unassumed = dataclasses.replace(result.read, assumption=None)
    trained = dataclasses.replace(result, read=unassumed, trainable_by=0)
    check_results(dataclasses.replace(report, results=(trained,)))


# A result the build accepts under an extrapolation's assumption, with a reason, `accepted_by` and no
# `not_accepted`: each member the model relation compares changed alone, and the law read past its first
# reason.
EXTRAPOLATED = "BC-019.outside_range_under_an_extrapolation.json"
OUTSIDE = Reason("outside_range", "temperature")


def with_its_result(report: BuildReport, **changes: Any) -> BuildReport:
    (result,) = report.results
    return dataclasses.replace(report, results=(dataclasses.replace(result, **changes),))


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "met"},
        {"reasons": ()},
        {"reasons": (OUTSIDE, Reason("outside_range", "shear_rate"))},
        {"accepted": False},
        {"accepted_by": ()},
        {"accepted_by": (0, 1)},
        {"not_accepted": (OUTSIDE,)},
    ],
    ids=[
        "status",
        "reasons-none",
        "reasons-another",
        "accepted",
        "accepted-by-none",
        "accepted-by-another",
        "not-accepted",
    ],
)
def test_the_model_relation_fails_where_one_member_of_a_result_differs(changes: dict[str, Any]) -> None:
    """Each member the relation compares of a result (its status, its reasons, the verdict, `accepted_by` and
    `not_accepted`) changed alone fails it, at the result's line."""
    case = next(case for case in CASES if case.path.name == EXTRAPOLATED)
    report = REPORTS[EXTRAPOLATED]
    (result,) = report.results
    assert result.accepted
    assert result.accepted_by == (0,)
    assert result.reasons == (OUTSIDE,)
    assert not result.not_accepted
    assert result.status == "not_met"
    against_the_model(case, report)
    with pytest.raises(AssertionError, match=r"^\('drag', .*\): \(.*\), the model's \("):
        against_the_model(case, with_its_result(report, **changes))


def test_the_model_relation_fails_where_refused_differs_from_the_model_s(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = next(case for case in CASES if case.path.name == EXTRAPOLATED)
    report = REPORTS[EXTRAPOLATED]
    assert not report.refused
    monkeypatch.setattr(BuildReport, "refused", property(lambda _: True))
    with pytest.raises(AssertionError, match=r"^refused True, the model's False$"):
        against_the_model(case, report)


def test_4_2s_own_law_reads_every_reason_of_an_accepted_result() -> None:
    """A reason no assumption covers after one the result's extrapolation covers fails the law."""
    report = REPORTS[EXTRAPOLATED]
    check_results(report)
    later = with_its_result(report, reasons=(OUTSIDE, Reason("condition_outside", "shear_rate")))
    with pytest.raises(AssertionError, match="accepted with condition_outside"):
        check_results(later)
