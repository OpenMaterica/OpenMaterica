# SPDX-License-Identifier: Apache-2.0
"""Every conformance case file: those this implementation runs must pass, those the reference evaluator runs
must be verified against it, and the rest are counted.

A case file that is not run is never a pytest item, so it cannot read as a pass or a skip; the counts below
and the terminal summary (`conftest.py`) account for it. A case file is not yet runnable while its operation
has no executor or a step it needs is not done (`tests/spec_sync/case_steps.json`).
"""

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from materica.core.jsonio import JsonValue
from materica.shapes import Suite
from tests.conformance import runner
from tests.conformance.runner import CONFIGURATIONS, EXECUTORS, CaseFile, Executor, Outcome
from tests.spec_sync.schemas import validator

CASE_FILES = runner.discover()
RUN = [
    case_file
    for case_file in CASE_FILES
    if runner.not_run_because(case_file, configurations=CONFIGURATIONS, executors=EXECUTORS) is None
]


@pytest.mark.parametrize("case_file", RUN, ids=[case_file.path.name for case_file in RUN])
def test_case_file(case_file: CaseFile) -> None:
    case_run = runner.run(case_file, configurations=CONFIGURATIONS, executors=EXECUTORS)
    assert case_run.outcome is runner.passing_outcome(case_file), "\n".join(case_run.differences)


def results_refused(
    case_files: list[CaseFile], executors: Mapping[str, runner.Executor], schema: str = "read_result.json"
) -> list[str]:
    """Each case file whose result, as `executors` give it under the first configuration that agrees with
    it, `schema` refuses, with the first reason."""
    takes_result = validator(schema)
    refused: list[str] = []
    for case_file in case_files:
        claims = runner.agreeing(case_file, CONFIGURATIONS)[0]
        result = json.loads(json.dumps(executors[case_file.operation](case_file, claims)))
        if problems := takes_result(result):
            refused.append(f"{case_file.path.name}: {problems[0]}")
    return refused


def test_every_result_a_run_case_file_gets_validates_against_the_result_schema() -> None:
    """`read_result.json` takes each result this implementation gives a case file it runs, not only each case
    file's expected answer (S2a-4's review, L1). A table evaluation case is no read: its result holds a run
    for each precision and side the evaluator claims, which the result schema does not describe."""
    reads = [case_file for case_file in RUN if case_file.operation not in ("evaluate", "check_build")]
    assert len(reads) > 700
    assert results_refused(reads, EXECUTORS) == []


def test_every_report_a_run_build_check_file_gets_validates_against_the_report_schema() -> None:
    """`build_report.json` takes each report this implementation gives a build-check file it runs, as
    `read_result.json` takes each read's result: 104 refused on their own, and 58 with results. The control: a
    report holding both a refusal and a result, which section 2 does not give, is refused for each, a result
    taken whole from one of the reports the schema takes being added to a refused one, and a refusal to one
    with results."""
    builds = [case_file for case_file in RUN if case_file.operation == "check_build"]
    assert len(builds) == 162
    assert results_refused(builds, EXECUTORS, "build_report.json") == []
    reports = [
        EXECUTORS["check_build"](case_file, runner.agreeing(case_file, CONFIGURATIONS)[0])
        for case_file in builds
    ]
    with_results = [report for report in reports if report["results"]]
    assert len(with_results) == 58
    a_result = cast(list[JsonValue], with_results[0]["results"])[0]

    def with_both(case_file: CaseFile, claims: frozenset[Suite]) -> runner.JsonObject:
        report = EXECUTORS["check_build"](case_file, claims)
        if report["refusals"]:
            return {**report, "results": [a_result]}
        return {**report, "refusals": [{"item": "BC-048", "pointer": "/models"}]}

    assert len(results_refused(builds, {"check_build": with_both}, "build_report.json")) == 162


def test_a_result_the_result_schema_refuses_is_found() -> None:
    def with_a_member_no_result_holds(case_file: CaseFile, claims: frozenset[Suite]) -> runner.JsonObject:
        return {**EXECUTORS[case_file.operation](case_file, claims), "x_note": 1.0}

    executors = dict.fromkeys(EXECUTORS, with_a_member_no_result_holds)
    assert len(results_refused(RUN[:3], executors)) == 3


def test_every_case_file_is_counted() -> None:
    runs = runner.run_all(CASE_FILES, configurations=CONFIGURATIONS, executors=EXECUTORS)
    assert len(runs) == 1686
    assert Counter(case_run.outcome for case_run in runs) == {
        Outcome.PASSED: 1344,
        Outcome.VERIFIED: 35,
        Outcome.NOT_YET_RUNNABLE: 307,
    }
    by_operation = Counter((case_run.outcome, case_run.case_file.operation) for case_run in runs)
    assert by_operation == {
        (Outcome.PASSED, "content_hash"): 51,
        (Outcome.PASSED, "read"): 1106,
        (Outcome.PASSED, "list_records"): 25,
        (Outcome.PASSED, "check_build"): 162,
        (Outcome.VERIFIED, "evaluate"): 35,
        (Outcome.NOT_YET_RUNNABLE, "read"): 110,
        (Outcome.NOT_YET_RUNNABLE, "check"): 184,
        (Outcome.NOT_YET_RUNNABLE, "quote_sha256"): 13,
    }


def test_each_configuration_runs_every_case_file_that_holds_for_it() -> None:
    claims = Counter(
        claimed for case_file in CASE_FILES for claimed in runner.agreeing(case_file, CONFIGURATIONS)
    )
    assert claims == {
        CONFIGURATIONS[0]: 1277,
        CONFIGURATIONS[1]: 1219,
        CONFIGURATIONS[2]: 1277,
        CONFIGURATIONS[3]: 1439,
        CONFIGURATIONS[4]: 1381,
        CONFIGURATIONS[5]: 1438,
        runner.REFERENCE_EVALUATOR: 35,
    }


TABLE_EVALUATIONS = [case_file for case_file in CASE_FILES if case_file.operation == "evaluate"]
# The reference evaluator's four configurations (the S3 design's S3Q15): each precision, declaring each side.
FOUR_CONFIGURATIONS = [
    ("binary64", "left"),
    ("binary64", "right"),
    ("binary32", "left"),
    ("binary32", "right"),
]


def configurations_run(case_file: CaseFile, executor: Executor) -> list[tuple[JsonValue, JsonValue]]:
    """The precision and the side of each run in the executor's result, in order."""
    runs = executor(case_file, runner.REFERENCE_EVALUATOR)["runs"]
    assert isinstance(runs, list)
    return [(run.get("precision"), run.get("side")) for run in runs if isinstance(run, dict)]


@pytest.mark.parametrize(
    "case_file", TABLE_EVALUATIONS, ids=[case_file.path.name for case_file in TABLE_EVALUATIONS]
)
def test_the_reference_evaluator_runs_each_te_file_under_its_four_configurations(case_file: CaseFile) -> None:
    # The comparison passes a result holding any one run, so the runs are counted here.
    assert configurations_run(case_file, EXECUTORS["evaluate"]) == FOUR_CONFIGURATIONS
    # Control: an executor claiming the first configuration alone runs that one.
    first = runner.evaluate_executor(claims=runner.EVALUATOR_CLAIMS[:1])
    assert configurations_run(case_file, first) == FOUR_CONFIGURATIONS[:1]


def test_a_case_passes_only_where_a_variant_ran() -> None:
    outcomes = runner.case_outcomes(
        runner.run_all(CASE_FILES, configurations=CONFIGURATIONS, executors=EXECUTORS)
    )
    assert len(outcomes) == 148
    assert Counter(outcomes.values()) == {
        Outcome.PASSED: 118,
        Outcome.VERIFIED: 10,
        Outcome.NOT_YET_RUNNABLE: 20,
    }


def test_a_case_file_runs_once_every_step_it_needs_is_done(tmp_path: Path) -> None:
    case_file = next(case_file for case_file in CASE_FILES if case_file.path.name == "PR-310.absent.json")
    entries: list[tuple[str | list[str] | None, bool]] = [
        ("S1", True),
        ("S3", False),
        (["S1", "S3"], False),
        (None, True),
    ]
    for number, (entry, done) in enumerate(entries):
        case_steps = tmp_path / f"case_steps_{number}.json"  # one file each: the runner reads each path once
        mapped = {} if entry is None else {case_file.path.name: entry}
        case_steps.write_text(json.dumps({"done": ["S1"], "case_files": mapped}), encoding="utf-8")
        assert runner.step_done(case_file, case_steps) is done, entry
