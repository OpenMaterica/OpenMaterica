# SPDX-License-Identifier: Apache-2.0
"""The measurement tool gives the answers that are known and changes them where its input changes: a thin
feature's floor is flagged, a tree against itself keeps every share and a way dropped does not, stream 0 is
the recorded kill and another stream moves it, a fuzz control with no fault finds nothing, and the summary
refuses a record missing, one twice and a failed job. tests/unit/test_ci_workflows.py runs the workflow's
steps."""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from scripts import measure
from scripts.measure import CONTROLS, Job, MeasureError

REPOSITORY = Path(__file__).resolve().parents[2]
CI = (REPOSITORY / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

# A property drawing one of three ways alike, and one drawing a rare value as one of two: the floors of `ci`
# hold the rare one (one example in a hundred, declared one in two) far below its floor.
SAMPLE = """
import pytest
from hypothesis import event, given, settings, strategies as st

WAYS = ("a", "b", "c")


@settings(max_examples=2000)
@pytest.mark.drawn(*WAYS)
@given(st.sampled_from(WAYS), st.integers())
def test_ways(way, number):
    event("feature: " + way)


@settings(max_examples=2000)
@pytest.mark.drawn("common", "rare")
@given(st.integers(0, 10**9))
def test_thin(number):
    event("feature: " + ("rare" if number % 100 == 57 else "common"))
"""
MARKERS = "[pytest]\nmarkers =\n" + "".join(
    f"    {name}: x\n" for name in ("drawn", "features", "chances", "deep_chances", "deep_controls")
)
# The property conftest's audit, as far as a measured run meets it: it judges every run of an item that is no
# audit control (`deep_controls`), so a measured run that it judged fails here.
AUDIT = """
import pytest


@pytest.hookimpl(wrapper=True, trylast=True)
def pytest_runtest_call(item):
    if item.get_closest_marker("deep_controls") is None:
        pytest.fail("the audit judged a measured run")
    return (yield)
"""
# A fuzz target that runs as libFuzzer does: it finds the fault only where the control's own is seeded, and
# otherwise runs its seconds.
TARGET = """
import os, sys, time
limit = [int(a.partition("=")[2]) for a in sys.argv if a.startswith("-max_total_time=")][0]
print("#2\\tINITED cov: 1")
print("#1024\\tpulse  cov: 2")
if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") == "1":
    print("IndexError: the seeded fault in parse")
    sys.exit(1)
time.sleep(limit)
print("Done 4096 runs in 1 second(s)")
"""


def sample_tree(root: Path, ways: str = '("a", "b", "c")') -> Path:
    (root / "tests" / "property").mkdir(parents=True)
    (root / "tests" / "fuzz").mkdir()
    for package in ("tests", "tests/property", "tests/fuzz"):
        (root / package / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy(REPOSITORY / "tests" / "property" / "audits.py", root / "tests" / "property" / "audits.py")
    sample = SAMPLE.replace("@given(st.sampled_from(WAYS)", f"@given(st.sampled_from({ways})")
    (root / "tests" / "property" / "test_sample_properties.py").write_text(sample, encoding="utf-8")
    (root / "tests" / "fuzz" / "properties.py").write_text(TARGET, encoding="utf-8")
    (root / "tests" / "property" / "conftest.py").write_text(AUDIT, encoding="utf-8")
    (root / "pytest.ini").write_text(MARKERS, encoding="utf-8")
    return root


def measured(
    kind: str, nodes: str, root: Path, out: Path, streams: int = 2, side: str = "head"
) -> dict[str, Any]:
    record = measure.run_job(Job("j", kind, nodes, 0, streams), out, 2, root)
    record["job"]["side"] = side
    return record


def test_a_floor_held_by_a_thin_feature_is_flagged_and_one_held_by_a_common_feature_is_not(
    tmp_path: Path,
) -> None:
    tree = sample_tree(tmp_path / "tree")
    record = measured("floors", "tests/property/test_sample_properties.py::test_thin", tree, tmp_path / "out")
    assert record["problems"] == []
    assert [run["stream"] for run in record["runs"]] in ([0, 1], [1, 0])
    run = record["runs"][0]
    assert run["examples"] == 2000
    assert run["floors"] == {"common": 440, "rare": 440}
    lines, flags = measure.report_floors([record])
    assert [flag.split("`")[1] for flag in flags] == ["rare"], flags
    assert any("`common`" in line for line in lines)


def test_a_tree_against_itself_keeps_every_share_and_a_way_dropped_falls_below_the_ratio(
    tmp_path: Path,
) -> None:
    tree = sample_tree(tmp_path / "tree")
    dropped = sample_tree(tmp_path / "dropped", ways='("a", "b")')
    node = "tests/property/test_sample_properties.py::test_ways"
    base = measured("regions", node, tree, tmp_path / "base", side="base")
    same = measured("regions", node, tree, tmp_path / "same")
    _, flags = measure.report_regions([base, same])
    assert flags == []
    lines, _ = measure.report_regions([base, same])
    assert sum("| 1.00 |" in line for line in lines) == 3
    _, flags = measure.report_regions([base, measured("regions", node, dropped, tmp_path / "head")])
    assert flags == [
        f"{node} `c`: 0.00 of the base's mean share, below 0.8",
        f"{node} `c`: least share 0.0000 below its floor 245 of 2000",
    ], flags


SEARCH = (
    "tests/property/test_alternatives_mutants.py::test_the_alternatives_mutant_is_killed"
    "[cannot_give_sets_aside-small]"
)


def test_drift_at_stream_0_is_the_recorded_kill_and_another_stream_moves_it(tmp_path: Path) -> None:
    record = measured("drift", SEARCH, REPOSITORY, tmp_path / "out")
    kills = {run["stream"]: run["kill"] for run in record["runs"]}
    recorded = json.loads((REPOSITORY / "tests/property/kill_points.json").read_text(encoding="utf-8"))
    pair = recorded["kills"]["test_alternatives_mutants.py::test_the_alternatives_mutant_is_killed"]
    assert record["recorded"] == {SEARCH: pair["cannot_give_sets_aside"][0]}
    assert kills[0] == pair["cannot_give_sets_aside"][0]
    assert kills[1] != kills[0], kills
    assert {run["status"] for run in record["runs"]} == {"killed"}
    assert measure.report_drift([record])[1] == []
    record["recorded"][SEARCH] = kills[0] + 1
    assert measure.report_drift([record])[1] == [
        f"{SEARCH}: stream 0 killed at {kills[0]}, recorded at {kills[0] + 1}"
    ]


def test_drift_flags_a_kill_near_the_guard_one_past_it_and_one_elsewhere() -> None:
    runs = [
        {"node": "s", "stream": 0, "kill": 399, "status": "killed", "message": ""},
        {"node": "s", "stream": 1, "kill": 400, "status": "killed", "message": ""},
        {"node": "s", "stream": 2, "kill": 501, "status": "killed", "message": ""},
        {"node": "s", "stream": 3, "kill": 9, "status": "killed elsewhere", "message": "no_pick\nmore"},
        {"node": "s", "stream": 4, "kill": None, "status": "survived", "message": "survived 2000"},
    ]
    _, flags = measure.report_drift([{"runs": runs, "recorded": {"s": 399}}])
    assert flags == [
        "s: stream 3 killed elsewhere: no_pick",
        "s: stream 4 survived: survived 2000",
        "s: stream 1 killed at example 400, near the margin guard at 500",
        "s: stream 2 killed at example 501, past the margin guard at 500",
    ]


def fuzz_job(fault: str) -> Job:
    return Job("f", "fuzz", control="properties", fault=fault)


def test_the_fastest_control_finds_its_fault_and_finds_nothing_with_none_seeded(tmp_path: Path) -> None:
    tree = sample_tree(tmp_path / "tree")
    found = measure.run_fuzz(fuzz_job("1"), tmp_path / "found", 1, tree, seconds=3)
    missed = measure.run_fuzz(fuzz_job("none"), tmp_path / "missed", 1, tree, seconds=3)
    assert (found["found"], found["inputs"], found["line"]) == (
        True,
        1024,
        "IndexError: the seeded fault in parse",
    )
    assert (missed["found"], missed["inputs"]) == (False, 4096)
    _, flags = measure.report_fuzz([found, missed])
    assert flags == [
        "properties: a run of 3 s, not the control's 180",
        "properties: a run of 3 s, not the control's 180",
    ]
    assert found["problems"] == missed["problems"] == []
    missed["found"], missed["line"] = True, "IndexError: x"
    assert "properties with no fault seeded found one: IndexError: x" in measure.report_fuzz([missed])[1]


def test_a_run_that_ended_on_another_failure_is_flagged_with_its_problem() -> None:
    """A run that stopped at another failure before its seconds counts as a miss, and the report says why, so
    that the miss is not read as a run that ran its seconds and found nothing."""
    ended = "the target ended with status 77 after 44 s of its 180, without the control's find (see fuzz.log)"
    run: dict[str, Any] = {"control": "properties", "fault": "1", "line": "", "inputs": 10, "limit": 180}
    runs: list[dict[str, Any]] = [
        run | {"run": 1, "found": False, "seconds": 44.0, "problems": [ended]},
        run | {"run": 0, "found": True, "seconds": 9.0, "problems": list[str]()},
    ]
    _, flags = measure.report_fuzz(runs)
    assert flags[0] == "properties: 1 of 2 runs found no fault within 180 s"
    assert f"properties, run 1: {ended}" in flags
    runs[0]["fault"] = "none"
    assert f"properties with no fault seeded, run 1: {ended}" in measure.report_fuzz(runs)[1]


def test_a_find_spoiled_by_its_exception_is_no_find() -> None:
    tables = CONTROLS["tables"]
    implementation = "AssertionError: the implementation gives ['form_invalid'], the model "
    assert measure.found_in(f"x\n{implementation}[]\n", tables)
    assert not measure.found_in(f"{implementation}['form_invalid']\n", tables)
    assert not measure.found_in(" " + implementation + "[]", tables)


GIVES = "AssertionError: the implementation gives "
AT = "'/models/{}/acceptances/{}'"


@pytest.mark.parametrize(
    ("line", "found"),
    [
        # Two forms of the ten finds of run 40275055796: the implementation's BC-048 there beside, and none.
        (f"{GIVES}[('BC-048', {AT.format(0, 2)})], the model [('BC-005', {AT.format(0, 2)})]", True),
        (f"{GIVES}[], the model [('BC-005', {AT.format(0, 4)})]", True),
        (f"{GIVES}[], the model [('BC-005', {AT.format(0, 10)})]", True),
        (f"{GIVES}[], the model [('BC-005', {AT.format(0, 0)})]", False),
        (f"{GIVES}[('BC-048', {AT.format(1, 1)})], the model [('BC-005', {AT.format(1, 1)})]", False),
        (f"{GIVES}[('BC-005', {AT.format(0, 2)})], the model []", False),
        (f"{GIVES}[], the model [('BC-048', {AT.format(0, 2)})]", False),
    ],
)
def test_the_declarations_find_is_the_model_s_bc_005_after_a_model_s_second_acceptance(
    line: str, found: bool
) -> None:
    """The control's fault skips item 4 at acceptances 2 and after alone: the model's BC-005 that the check
    does not give is its find there, and none at acceptance 0 or 1."""
    assert bool(measure.found_in(line, CONTROLS["declarations"])) == found


RESULT = "drag conformance/water_fixture fluid.dynamic_viscosity"
LAW = "which no assumption or trainable acceptance covers"
KEY = "('drag', ('conformance/water_fixture', '1.0.0', 'sha256:c21a'), 'fluid.dynamic_viscosity')"


@pytest.mark.parametrize(
    ("line", "found"),
    [
        # The fault's, BC-038's seed under it: section 4.2's own law, a result accepted with the code.
        (f"AssertionError: {RESULT} accepted with condition_outside, {LAW}", True),
        # The law for another code; the law's line in the traceback, not the exception's; and every other
        # message the target can raise, the relations to the models among them where they hold the code.
        (f"AssertionError: {RESULT} accepted with outside_range, {LAW}", False),
        (f"    AssertionError: {RESULT} accepted with condition_outside, {LAW}", False),
        ("AssertionError: refused False, where its refusals and results give True", False),
        (
            f"AssertionError: {KEY}: ('not_met', (('condition_outside', 'temperature', None),), False, "
            "(1,), ()), the model's ('not_met', (('condition_outside', 'temperature', None),), False, (1,), "
            "(('condition_outside', 'temperature', None),))",
            False,
        ),
        (f"AssertionError: results [{KEY}], the model's []", False),
        ("AssertionError: unused [], the model's [('drag', 0)]", False),
        ("AssertionError: refused True, the model's False", False),
        ("AssertionError: refusals [], the model's [('BC-048', '/models/0/acceptances/1')]", False),
        ("AssertionError: refused [('BC-048', '/consumer')], the model takes it", False),
        (
            "AssertionError: the implementation gives [], the model [('BC-005', '/models/0/acceptances/2')]",
            False,
        ),
        ("AssertionError: a refusal of BC-038, which no rule of the declaration's names", False),
        ("AssertionError: a refusal at '/models/9', which names no member", False),
        ("AssertionError: NotImplementedError of no piece: condition_outside", False),
    ],
)
def test_the_judge_find_is_4_2s_own_law_on_a_result_accepted_with_condition_outside(
    line: str, found: bool
) -> None:
    """The control's fault lets a waiver cover `condition_outside`, which no correct build accepts uncovered
    (no assumption covers it, and a `trainable` entry, which could, the build does not read yet): its find is
    the line of section 4.2's own law for that code, and no other line the target raises."""
    assert bool(measure.found_in(line, CONTROLS["judge"])) == found


def control_step() -> str:
    """ci.yml's fuzz control step, its continued lines joined and its variables of one value written out."""
    start = CI.index("      - name: Control, the faults seeded")
    step = CI[start : CI.index("\n      - ", start + 10)].replace("\\\n", " ")
    for name, value in re.findall(r'(?m)^\s*(\w+)="([^"$]*)"$', step):
        step = step.replace(f'"${name}', f'"{value}').replace(f"${name} ", f"{value} ")
    return step


def control_problems(controls: dict[str, measure.Control]) -> list[str]:
    """Where a control is not run as ci.yml's control step runs it: its fault, target, arguments, seconds and
    the lines that are a find."""
    step = control_step()
    problems: list[str] = []
    for name, control in controls.items():
        prefix = "" if control.fault == "1" else f"MATERICA_FUZZ_SEEDED_FAULT={control.fault} "
        wanted = [*control.arguments, f"-max_total_time={control.seconds}", "-artifact_prefix="]
        wanted += ["-dict=" for _ in control.dictionary[:1]]
        patterns = (control.found, control.unless) if control.unless else (control.found,)
        problems += [
            f"{name}: {pattern!r} not in the step" for pattern in patterns if f'"{pattern}"' not in step
        ]
        runs = [
            line.split()
            for line in step.splitlines()
            if line.strip().startswith(f"{prefix}uv run python -m tests.fuzz.{control.target} ")
            and "--seed" not in line
            and "--dict" not in line
        ]
        if not any(all(any(word.startswith(each) for word in words) for each in wanted) for words in runs):
            problems.append(f"{name}: no run of tests.fuzz.{control.target} with {prefix}{wanted}")
    return problems


def test_each_control_runs_as_the_control_step_runs_it() -> None:
    assert control_problems(CONTROLS) == []
    assert control_problems({"x": CONTROLS["table_alternatives"]._replace(seconds=600)}) != []
    assert control_problems({"x": CONTROLS["tables"]._replace(fault="table_edges")}) != []
    assert control_problems({"x": CONTROLS["bytes"]._replace(arguments=("-max_len=4096",))}) == []
    assert control_problems({"x": CONTROLS["bytes"]._replace(arguments=("-max_len=8192",))}) != []
    assert control_problems({"x": CONTROLS["tables"]._replace(unless="the model .*'outside'")}) != []


def test_the_rate_and_misses_are_s4ds_figures() -> None:
    """Seven finds in 6,348 s (tests/fuzz/README.md, S4d's control): 1.1e-3 a second, its one-sided 95 % lower
    bound 5.2e-4, and on a runner 1.4 times slower a pair of 900 s misses with 0.24."""
    rate = 7 / 6348
    assert round(rate, 4) == 0.0011
    assert round(measure.rate_lower(7, 6348), 5) == 0.00052
    assert round(measure.miss(rate, 2, 900 / 1.4), 2) == 0.24
    assert measure.rate_lower(0, 6348) == 0.0


def test_the_false_failure_is_the_audits_model_at_its_floor() -> None:
    """At the floor `draw_floor` gives, the model's chance is at most 1e-6; one draw higher, above it."""
    floor = 440  # drawn among two, 2,000 examples
    assert measure.below(2000 // 8, 0.5, floor / 5) <= 1e-6 < measure.below(2000 // 8, 0.5, (floor + 5) / 5)
    assert measure.below(10, 0.0, 1) == 1.0
    assert measure.below(10, 0.5, 0) == 0.0


def record(job: Job, problems: list[str] | None = None) -> dict[str, Any]:
    return {
        "tool": "measure",
        "job": job.data(),
        "commit": "c",
        "python": "3.15",
        "hypothesis": "",
        "runs": [],
        "problems": problems or [],
    }


JOBS = [
    Job("floors-head-0-0", "floors", "tests/property/test_slip_properties.py", 0, 2),
    Job("b", "floors", "tests/property/test_slip_properties.py", 2, 2),
]


def write_records(directory: Path, records: list[dict[str, Any]]) -> None:
    for index, each in enumerate(records):
        (directory / f"record-{index}").mkdir(parents=True)
        (directory / f"record-{index}" / "record.json").write_text(json.dumps(each), encoding="utf-8")


@pytest.mark.parametrize(
    ("records", "result", "attempt", "problem"),
    [
        ([record(JOBS[0]), record(JOBS[1])], "success", 1, ""),
        ([record(JOBS[0])], "success", 1, "job b: no record"),
        ([record(JOBS[0]), record(JOBS[1]), record(JOBS[1])], "success", 1, "job b: 2 records"),
        ([record(JOBS[0]), record(JOBS[1])], "failure", 1, "the measurement jobs ended in 'failure'"),
        ([record(JOBS[0]), record(JOBS[1], ["interrupted"])], "success", 1, "job b: interrupted"),
        ([record(JOBS[0]), record(JOBS[1])], "success", 2, "attempt 2 of the run"),
        (
            [record(JOBS[0]), record(JOBS[1]), record(JOBS[1]._replace(id="c"))],
            "success",
            1,
            "no requested job: c",
        ),
    ],
    ids=["whole", "missing", "twice", "failed", "unfinished", "attempt", "unrequested"],
)
def test_the_summary_counts_the_records_first(
    records: list[dict[str, Any]], result: str, attempt: int, problem: str, tmp_path: Path
) -> None:
    write_records(tmp_path, records)
    text, ok = measure.summary(tmp_path, JOBS, result, attempt)
    assert ok == (not problem)
    assert problem in text


def test_a_self_test_job_that_gives_another_answer_fails_the_summary(tmp_path: Path) -> None:
    job = Job("f", "fuzz", control="properties", fault="none", expect="no_finds")
    found = record(job) | {
        "control": "properties",
        "fault": "none",
        "found": True,
        "line": "x",
        "seconds": 1.0,
        "inputs": 1,
        "limit": 180,
    }
    write_records(tmp_path, [found])
    text, ok = measure.summary(tmp_path, [job], "success", 1)
    assert not ok
    assert "f: expected no find" in text


ENVIRONMENT = {
    "KIND": "floors",
    "SELECTION": "tests/property/test_slip_properties.py",
    "COUNT": "",
    "PER_JOB": "",
    "BASE": "main",
    "PYTHON_VERSION": "3.15",
}


@pytest.mark.parametrize(
    ("name", "value", "problem"),
    [
        ("KIND", "kills", "the kind 'kills' is not one of"),
        ("SELECTION", "tests/unit/test_measure.py", "not a path or node under tests/property"),
        ("SELECTION", "tests/property/../unit", "not a path or node under tests/property"),
        ("SELECTION", "tests/property/test_missing.py", "names no file or directory"),
        ("SELECTION", "", "the selection is empty"),
        ("COUNT", "0", "the count 0 is not from 1 to 200"),
        ("COUNT", "010", "the count '010' is not a whole number"),
        ("COUNT", "a[$(touch ran)]", "is not a whole number"),
        ("PER_JOB", "3", ""),
        ("PER_JOB", "21", "the streams a job 21 is not from 1 to 20"),
        ("PYTHON_VERSION", "3.10", "the Python '3.10' is not one of"),
    ],
)
def test_the_request_refuses_what_it_cannot_run_as_asked(name: str, value: str, problem: str) -> None:
    environment = ENVIRONMENT | {name: value}
    if not problem:
        assert measure.checked_request(environment, REPOSITORY)["per_job"] == value
        return
    with pytest.raises(MeasureError) as raised:
        measure.checked_request(environment, REPOSITORY)
    assert any(problem in each for each in raised.value.problems), raised.value.problems


def test_the_request_takes_the_rules_counts_and_a_control_with_no_fault() -> None:
    assert measure.checked_request(ENVIRONMENT, REPOSITORY)["count"] == "20"
    fuzz = measure.checked_request(
        ENVIRONMENT | {"KIND": "fuzz", "SELECTION": "properties tables:none"}, REPOSITORY
    )
    assert (fuzz["count"], fuzz["python"]) == ("10", "3.14")
    regions = ENVIRONMENT | {"KIND": "regions", "BASE": "-x"}
    with pytest.raises(MeasureError, match="the base '-x' is not a branch"):
        measure.checked_request(regions, REPOSITORY)
    pulled = {"EVENT": "pull_request", "PR_BASE": "a" * 40, "PR_HEAD": "b" * 40}
    checked = measure.checked_request(pulled, REPOSITORY)
    assert (checked["kind"], checked["base"]) == ("pull_request", f"{'a' * 40}...{'b' * 40}")
    with pytest.raises(MeasureError, match="are not two commits"):
        measure.checked_request(pulled | {"PR_HEAD": "main"}, REPOSITORY)


def test_the_matrix_makes_a_job_of_each_property_function_and_chunk_and_none_of_another_test(
    tmp_path: Path,
) -> None:
    tree = sample_tree(tmp_path / "tree")
    request = {
        "kind": "floors",
        "selection": "tests/property",
        "count": "5",
        "per_job": "2",
        "base": "",
        "python": "3.15",
    }
    jobs = measure.matrix(request, tree)
    assert [(job.nodes.split("::")[1], job.first, job.length) for job in jobs] == [
        ("test_ways", 0, 2),
        ("test_ways", 2, 2),
        ("test_ways", 4, 1),
        ("test_thin", 0, 2),
        ("test_thin", 2, 2),
        ("test_thin", 4, 1),
    ]
    with pytest.raises(MeasureError, match="holds no search"):
        measure.matrix(request | {"kind": "drift"}, tree)
    with pytest.raises(MeasureError, match="more than a matrix holds"):
        measure.matrix(request | {"count": "200", "per_job": "1"}, tree)


def test_a_job_is_checked_again_as_its_job_reads_it() -> None:
    job = Job("x", "fuzz", control="properties", fault="1")
    assert measure.job_from(json.dumps(job.data())) == job
    for changed in (
        {"kind": "pytest"},
        {"control": "nothing"},
        {"base": "main"},
        {"first": "-1"},
        {"extra": "1"},
    ):
        with pytest.raises(MeasureError):
            measure.job_from(json.dumps(job.data() | changed))


@pytest.mark.parametrize(
    ("matrix", "status", "said"),
    [
        (["floors-head-0-0"], 0, ""),
        (["floors-head-0-0", "floors-head-0-1"], 1, "job floors-head-0-1: no record"),
        (["other"], 1, "a record of no requested job: floors-head-0-0"),
        (None, 1, "the run kept no table"),
    ],
)
def test_fetch_reports_a_runs_records_counted_against_the_runs_matrix(
    matrix: list[str] | None,
    status: int,
    said: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    payload = json.dumps(record(JOBS[0]) | {"streams": [0, 1]})
    gh = bin_directory / "gh"
    table = (
        ""
        if matrix is None
        else 'if "measure-table-*" in sys.argv:\n  d = base / "measure-table-1"\n  d.mkdir()\n'
        f'  (d / "matrix.json").write_text({json.dumps(matrix)!r})\n'
    )
    gh.write_text(
        f"#!{sys.executable}\nimport sys, pathlib\n"
        'base = pathlib.Path(sys.argv[sys.argv.index("-D") + 1])\n'
        'd = base / "record-x"\n'
        f'd.mkdir(parents=True)\n(d / "record.json").write_text({payload!r})\n' + table,
        encoding="utf-8",
    )
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_directory}{os.pathsep}{os.environ['PATH']}")
    assert measure.main(["fetch", "123"]) == status
    out = capsys.readouterr().out
    assert "## floors" in out
    assert said in out


def test_the_summary_keeps_the_matrix_beside_the_table_for_fetch_to_count_against(tmp_path: Path) -> None:
    write_records(tmp_path / "records", [record(JOBS[0]), record(JOBS[1])])
    environment = {"MATRIX": json.dumps([job.data() for job in JOBS]), "RESULT": "success", "ATTEMPT": "1"}
    with pytest.MonkeyPatch.context() as patch:
        for name, value in environment.items():
            patch.setenv(name, value)
        measure.main(["summary", str(tmp_path / "records"), str(tmp_path / "table")])
    assert json.loads((tmp_path / "table" / "matrix.json").read_text(encoding="utf-8")) == [
        job.id for job in JOBS
    ]


def test_the_self_test_resolves_to_a_job_of_each_kind_with_its_answer() -> None:
    jobs = measure.self_test("3.15", REPOSITORY)
    assert sorted({(job.kind, job.side, job.expect) for job in jobs}) == [
        ("cuts", "head", "baseline:2"),
        ("drift", "head", "recorded"),
        ("floors", "head", "counted"),
        ("fuzz", "head", "finds"),
        ("fuzz", "head", "no_finds"),
        ("kills", "head", "ratio_one"),
        ("regions", "base", "ratio_one"),
        ("regions", "head", "ratio_one"),
    ]
    assert {(job.kind, job.length) for job in jobs if job.kind in ("floors", "drift", "regions")} == {
        ("floors", 20),
        ("drift", 40),
        ("regions", 18),
    }
    assert Counter(job.fault for job in jobs if job.kind == "fuzz") == {"1": 10, "none": 10}
    assert {job.python for job in jobs if job.kind == "fuzz"} == {"3.14"}
    assert len({job.id for job in jobs}) == len(jobs)
    head = next(job.base for job in jobs if job.kind == "regions")
    assert all(measure.job_from(json.dumps(job.data())) == job for job in jobs)
    assert re.fullmatch(r"[0-9a-f]{40}", head)


def test_an_interrupt_is_passed_on_to_the_measuring_processes_and_said(tmp_path: Path) -> None:
    """As the job's `timeout --foreground --signal=INT` interrupts the script: its processes stop at once and
    the record says why, rather than the job being cancelled without one."""
    code = (
        "import subprocess, time; from scripts import measure; started = time.monotonic();"
        " statuses, problems = measure.waited([subprocess.Popen(['sleep', '60']) for _ in range(2)]);"
        " print(statuses, problems, round(time.monotonic() - started))"
    )
    done = subprocess.run(
        ["timeout", "--foreground", "--signal=INT", "1s", sys.executable, "-c", code],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.stdout.strip() == '[-2, -2] ["interrupted before the job\'s timeout"] 1', done.stderr
