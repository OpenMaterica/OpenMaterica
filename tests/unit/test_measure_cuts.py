# SPDX-License-Identifier: Apache-2.0
"""The cut kind of the measurement tool (`scripts/measure.py`, `.github/workflows/measure.yml`): a request
names selections of the input coverage's baseline; the matrix splits each into slices by its timing; a job
runs its slice and keeps the selection's report; the summary merges the slices, refuses a slice missing or
recording other cuts, and holds a pull request's to the baseline, a dispatch's findings flags; a pull request
makes the cuts of what it changes, and none where it changes nothing measured.

The jobs run `scripts/input_coverage.py` on a tree of their own, written here, with copies of the runner and
the plugin, as `tests/unit/test_input_coverage.py` does."""

import fnmatch
import json
import math
import re
import shutil
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from scripts import input_coverage, measure
from scripts.measure import Job, MeasureError
from tests.unit.throwaway_git import throwaway_repository

REPOSITORY = Path(__file__).resolve().parents[2]

# A composite drawing one of two values, of which one test holds the value "a" alone: the cut dropping "a" is
# held, the one dropping "b" is not.
HOLDS = """
from hypothesis import find, given, settings, strategies as st

DERANDOMIZED = settings(derandomize=True, database=None, max_examples=40, deadline=None)


@st.composite
def drawn(draw):
    return draw(st.sampled_from(["a", "b"]))


@DERANDOMIZED
@given(drawn())
def test_drawn(example):
    assert example in "ab"


def test_a_is_drawn():
    find(drawn(), lambda example: example == "a", settings=DERANDOMIZED)
"""
FAILS = (
    HOLDS
    + """

def test_always_fails():
    assert False, "fails with no cut"
"""
)
SITE = "tests/test_holds.py::drawn::st.sampled_from(['a', 'b'])"
DROP_A, DROP_B = f"{SITE} :: drop 'a'", f"{SITE} :: drop 'b'"
# Hypothesis's own defaults, whatever variables the machine sets (tests/unit/test_input_coverage.py says why).
CONFTEST = """
from hypothesis import settings

settings.register_profile("fixture", parent=settings.get_profile("default"))
settings.load_profile("fixture")
"""
ENTRY: dict[str, Any] = {
    "tests": ["tests/test_holds.py"],
    "sites": ["tests/test_holds.py::*"],
    "excused": {},
    "timing": {"cuts": 2, "seconds": 10.0, "measured": "a fixture"},
    "left_out": {"sites": 0, "cuts": 0, "uncut": 0, "reason": "nothing is left out"},
    "cuts": {},
    "uncut": {},
}


def cut_tree(root: Path, module: str = HOLDS, entry: dict[str, Any] | None = None) -> Path:
    """A tree with the runner, the plugin, one selection `fixture` in its baseline and its test module."""
    (root / "tests" / "property").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (root / "tests" / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    for package in ("tests", "tests/property"):
        (root / package / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy(REPOSITORY / "tests" / "property" / "input_coverage.py", root / "tests" / "property")
    shutil.copy(REPOSITORY / "scripts" / "input_coverage.py", root / "scripts")
    (root / "tests" / "test_holds.py").write_text(module, encoding="utf-8")
    write_baseline(root, {"fixture": entry or ENTRY})
    return root


def write_baseline(root: Path, baseline: dict[str, Any]) -> None:
    (root / measure.BASELINE).write_text(json.dumps(baseline), encoding="utf-8")


def slices(count: int, expect: str = "") -> list[Job]:
    return [
        Job(f"cuts-fixture-{part}", "cuts", "fixture", part, count, expect=expect) for part in range(count)
    ]


def ran(root: Path, jobs: list[Job], records: Path) -> list[dict[str, Any]]:
    return [measure.run_job(job, records / f"record-{job.id}-1", 2, root) for job in jobs]


def results(record: dict[str, Any]) -> dict[str, str | None]:
    return {name: cut.get("result") for name, cut in record["report"]["cuts"].items()}


def test_each_cut_job_runs_its_slice_and_the_summary_merges_them_and_holds_them_to_the_baseline(
    tmp_path: Path,
) -> None:
    root = cut_tree(tmp_path / "tree")
    jobs = slices(2)
    first, second = ran(root, jobs, tmp_path / "records")
    # Each slice runs its own cut, and records the selection whole: the other cut is another share's.
    assert (results(first), results(second)) == (
        {DROP_A: "held", DROP_B: None},
        {DROP_A: None, DROP_B: "not held"},
    )
    assert first["problems"] == second["problems"] == []
    assert first["baseline"] == ENTRY
    # Each job says how many cuts its share held, and the table sums them.
    assert (first["cuts_in_share"], second["cuts_in_share"]) == (1, 1)
    text, ok = measure.summary(tmp_path / "records", jobs, "success", 1)
    assert ok, text
    assert "| `fixture` | all | 2 | 1 | 2 | 1 | 1 |" in text
    assert "| 0, 0, 0 | 2 |" in text
    assert f"- fixture: not held, and not in the baseline: {DROP_B}" in text
    # A pull request's slices are held to the baseline: the same finding is a problem there.
    held = slices(2, expect="baseline")
    for job, record in zip(held, (first, second), strict=True):
        record["job"] = job.data()
        (tmp_path / "records" / f"record-{job.id}-1" / "record.json").write_text(json.dumps(record))
    text, ok = measure.summary(tmp_path / "records", held, "success", 1)
    assert not ok
    assert f"fixture, held to the baseline: not held, and not in the baseline: {DROP_B}" in text
    # `input_coverage.py check` reads the records as `fetch` downloads them, and passes once the baseline
    # lists the cut not held.
    check = ["check", "fixture", "--records", str(tmp_path / "records"), "--root", str(root)]
    check += ["--baseline", str(root / measure.BASELINE)]
    assert input_coverage.main(check) == 1
    listed = ENTRY | {"cuts": {DROP_B: {"result": "not held", "reason": "a gap: no test needs 'b'"}}}
    write_baseline(root, {"fixture": listed})
    assert input_coverage.main(check) == 0


def test_the_summary_refuses_a_slice_missing_and_slices_that_recorded_other_cuts(tmp_path: Path) -> None:
    root = cut_tree(tmp_path / "tree")
    jobs = slices(2)
    _, second = ran(root, jobs, tmp_path / "records")
    shutil.rmtree(tmp_path / "records" / f"record-{jobs[1].id}-1")
    text, ok = measure.summary(tmp_path / "records", jobs, "success", 1)
    assert not ok
    assert "fixture: slice 1 of 2: no report" in text
    second["report"]["cuts"][f"{SITE} :: drop 'c'"] = {"site_id": SITE, "change": "drop", "key": "'c'"}
    (tmp_path / "records" / f"record-{jobs[1].id}-1").mkdir()
    (tmp_path / "records" / f"record-{jobs[1].id}-1" / "record.json").write_text(json.dumps(second))
    text, ok = measure.summary(tmp_path / "records", jobs, "success", 1)
    assert not ok
    assert "fixture: slice 1 recorded other cuts, uncut draws or left-out counts than the first" in text


def test_a_cut_job_whose_selection_fails_with_no_cut_or_runs_out_of_time_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failing = cut_tree(tmp_path / "failing", FAILS)
    (record,) = ran(failing, slices(1), tmp_path / "records")
    assert record["report"] is None
    assert record["problems"] == [
        "the selection was not recorded: it fails with no cut, or the tool failed (input-coverage.log)"
    ]
    # Out of time: started two hours ago, the job starts no cut, and counts those it did not run.
    root = cut_tree(tmp_path / "tree")
    monkeypatch.setenv("JOB_STARTED", str(int(time.time()) - 7200))
    monkeypatch.setenv("JOB_MINUTES", str(measure.CUT_JOB_MINUTES))
    (late,) = ran(root, slices(1), tmp_path / "late")
    assert results(late) == {DROP_A: None, DROP_B: None}
    assert late["problems"] == ["2 of the 2 cuts of the job's share not run in its time"]


def test_a_cut_job_stops_starting_cuts_one_and_a_half_longest_cuts_before_its_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = cut_tree(tmp_path / "tree")
    job = slices(1)[0]
    monkeypatch.delenv("JOB_STARTED", raising=False)
    assert measure.cut_budget(job, root) is None
    started = int(time.time())
    monkeypatch.setenv("JOB_STARTED", str(started))
    monkeypatch.setenv("JOB_MINUTES", "120")
    budget = measure.cut_budget(job, root)
    assert budget is not None
    # The interrupt three minutes before the timeout, less one and a half of the 10 s longest cut.
    assert started + 117 * 60 - 15 - time.time() - 1 <= budget <= started + 117 * 60 - 15 - time.time() + 1


TIMED = {
    "one": ENTRY | {"timing": {"cuts": 100, "seconds": 300.0, "measured": "x"}, "left_out": {"cuts": 200}},
    "two": ENTRY | {"timing": {"cuts": 10, "seconds": 60.0, "measured": "x"}, "left_out": {"cuts": 0}},
}


def test_the_cut_matrix_splits_each_selection_by_its_cuts_and_its_longest_cut(tmp_path: Path) -> None:
    write_root = tmp_path / "tests" / "property"
    write_root.mkdir(parents=True)
    write_baseline(tmp_path, TIMED)
    request = {"kind": "cuts", "selection": "one all:whole two", "count": "", "per_job": "", "base": ""}
    jobs = measure.matrix(request | {"python": "3.15"}, tmp_path)
    capacity = measure.CUT_PLANNED * measure.CUT_JOB_MINUTES * 60 * measure.CUTS_AT_ONCE
    planned = {
        "one": math.ceil(100 * 300 / capacity),
        "one:whole": math.ceil(300 * 300 / capacity),
        "two:whole": 1,
        "two": 1,
    }
    assert planned == {"one": 5, "one:whole": 13, "two:whole": 1, "two": 1}
    made: dict[str, list[tuple[int, int]]] = {}
    for job in jobs:
        made.setdefault(job.nodes, []).append((job.first, job.length))
    assert made == {name: [(part, count) for part in range(count)] for name, count in planned.items()}
    assert len({job.id for job in jobs}) == len(jobs)
    # A job's id becomes an artifact's name, which cannot hold a colon; a selection named twice is one.
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+", job.id) for job in jobs), [job.id for job in jobs]
    twice = measure.matrix(request | {"selection": "all one", "python": "3.15"}, tmp_path)
    assert [job.nodes for job in twice].count("one") == planned["one"]
    assert len(twice) == planned["one"] + planned["two"] == len({job.id for job in twice})
    # Twice the longest cut, twice the slices.
    write_baseline(tmp_path, {"one": TIMED["one"] | {"timing": {"cuts": 100, "seconds": 600.0}}})
    assert len(measure.matrix(request | {"selection": "one", "python": "3.15"}, tmp_path)) == 9
    write_baseline(tmp_path, {"one": TIMED["one"] | {"timing": {"cuts": 10**6, "seconds": 600.0}}})
    with pytest.raises(MeasureError, match="more than a matrix holds"):
        measure.matrix(request | {"selection": "one", "python": "3.15"}, tmp_path)


CUT_REQUEST = {"KIND": "cuts", "SELECTION": "extrapolation", "COUNT": "", "PER_JOB": "", "BASE": ""}


@pytest.mark.parametrize(
    ("name", "value", "problem"),
    [
        ("SELECTION", "all table_alternatives:whole", ""),
        ("SELECTION", "nothing", "'nothing' is not all or a selection of"),
        ("SELECTION", "extrapolation:half", "'extrapolation:half' is not all or a selection"),
        ("COUNT", "3", "the cut kind takes no count"),
        ("PER_JOB", "1", "the cut kind takes no count"),
    ],
)
def test_the_cut_request_takes_selections_of_the_baseline_and_no_count(
    name: str, value: str, problem: str
) -> None:
    environment = CUT_REQUEST | {"PYTHON_VERSION": "3.15", name: value}
    if not problem:
        checked = measure.checked_request(environment, REPOSITORY)
        assert (checked["kind"], checked["selection"], checked["count"]) == ("cuts", value, "")
        return
    with pytest.raises(MeasureError) as raised:
        measure.checked_request(environment, REPOSITORY)
    assert any(problem in each for each in raised.value.problems), raised.value.problems


def test_a_cut_job_is_checked_again_as_its_job_reads_it() -> None:
    job = Job("x", "cuts", "extrapolation", 1, 3, scope="*tests/property/tables.py::*")
    assert measure.job_from(json.dumps(job.data())) == job
    for changed in (
        {"nodes": "all"},
        {"nodes": "nothing"},
        {"nodes": "extrapolation:half"},
        {"first": 3},
        {"scope": "*\x7f"},
    ):
        with pytest.raises(MeasureError):
            measure.job_from(json.dumps(job.data() | changed))


def option(command: list[str], flag: str, words: int = 1) -> list[str]:
    start = command.index(flag) + 1
    return command[start : start + words]


def test_a_cut_job_runs_two_cuts_at_once_on_two_workers_each_in_its_slice_and_scope(tmp_path: Path) -> None:
    job = Job("x", "cuts", "fixture:whole", 1, 3, scope="*a.py::* *b.py::*")
    command = measure.cut_command(job, tmp_path / "report.json", 4, tmp_path, 12.9)
    assert option(command, "--workers") == ["2"]
    assert option(command, "--parallel") == ["2"]
    assert option(command, "--slice") == ["1/3"]
    assert option(command, "--scope", 2) == ["*a.py::*", "*b.py::*"]
    assert option(command, "--budget") == ["12"]
    assert "--whole" in command
    # Cuts at once follow the job's workers, from one: four vCPUs two at once, eight four, one one.
    for given, at_once in ((1, "1"), (2, "1"), (8, "4")):
        other = measure.cut_command(job, tmp_path / "report.json", given, tmp_path, None)
        assert option(other, "--parallel") == [at_once]
    plain = measure.cut_command(
        Job("x", "cuts", "fixture", 0, 1), tmp_path / "report.json", 4, tmp_path, None
    )
    assert not {"--whole", "--scope", "--budget"} & set(plain)


def test_a_cut_job_reports_the_cuts_its_share_held_and_a_scope_that_holds_none_is_named(
    tmp_path: Path,
) -> None:
    listed = {DROP_B: {"result": "not held", "reason": "a gap: no test needs 'b'"}}
    root = cut_tree(tmp_path / "tree", entry=ENTRY | {"cuts": listed})
    drifted = "*::no_such_function::*"
    both = "*::drawn::*"
    # A pull request's job whose scope holds no cut checks nothing: the job says so, the table names it, and
    # the report does not fail (the run is advisory); the control, a scope that holds both cuts, passes.
    nothing = Job("cuts-fixture-0", "cuts", "fixture", 0, 1, expect="baseline", scope=drifted)
    (empty,) = ran(root, [nothing], tmp_path / "nothing")
    assert (empty["cuts_in_share"], empty["problems"]) == (0, [])
    text, ok = measure.summary(tmp_path / "nothing", [nothing], "success", 1)
    assert ok, text
    assert "| 0 in scope: nothing checked |" in text
    assert "- fixture: 0 in scope: nothing checked" in text
    scoped = nothing._replace(scope=both)
    (full,) = ran(root, [scoped], tmp_path / "scoped")
    assert (full["cuts_in_share"], full["problems"]) == (2, [])
    text, ok = measure.summary(tmp_path / "scoped", [scoped], "success", 1)
    assert ok, text
    assert "nothing checked" not in text
    # The self-test says how many cuts its pattern must match: a pattern that drifts off its site fails.
    expecting = nothing._replace(expect="baseline:2")
    (_,) = ran(root, [expecting], tmp_path / "drifted")
    text, ok = measure.summary(tmp_path / "drifted", [expecting], "success", 1)
    assert not ok
    assert "fixture: 0 cuts in scope, and the self-test's pattern must match 2" in text
    expecting = scoped._replace(expect="baseline:2")
    (_,) = ran(root, [expecting], tmp_path / "held")
    text, ok = measure.summary(tmp_path / "held", [expecting], "success", 1)
    assert ok, text


def test_the_self_tests_cut_pattern_still_names_a_cut_of_the_baseline_and_expects_two() -> None:
    (cuts,) = [row for row in measure.SELF_TEST if row[0] == "cuts"]
    name, _, pattern = cuts[1].partition(" ")
    assert cuts[2] == "baseline:2"
    listed = measure.baseline_of(REPOSITORY)[name]["cuts"]
    assert any(fnmatch.fnmatchcase(each, pattern) for each in listed), pattern


def test_a_cut_job_whose_tool_exits_outside_zero_to_two_fails_though_it_wrote_its_report(
    tmp_path: Path,
) -> None:
    listed = {DROP_B: {"result": "not held", "reason": "a gap: no test needs 'b'"}}
    root = cut_tree(tmp_path / "tree", entry=ENTRY | {"cuts": listed})
    (ok,) = ran(root, slices(1), tmp_path / "ok")
    assert ok["problems"] == []
    tool = root / "scripts" / "input_coverage.py"
    tool.write_text(tool.read_text(encoding="utf-8").replace("sys.exit(main())", "sys.exit(main() + 3)"))
    (record,) = ran(root, slices(1), tmp_path / "exits")
    assert record["report"] is not None
    assert record["problems"] == ["scripts/input_coverage.py exited 3 (input-coverage.log)"]


def test_the_summary_and_fetch_and_a_local_run_all_refuse_a_slice_missing_or_doubled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = cut_tree(tmp_path / "tree")
    jobs = slices(2)
    first, second = ran(root, jobs, tmp_path / "records")
    # `fetch`: the run's matrix names both slices' jobs, and the records hold only the first's twice? No: the
    # first alone, so that the matrix count passes and only the merge can say a slice is missing.
    downloaded = tmp_path / "downloaded"
    (downloaded / "measure-table-1").mkdir(parents=True)
    (downloaded / "measure-table-1" / measure.MATRIX_FILE).write_text(json.dumps([jobs[0].id]))
    (downloaded / f"record-{jobs[0].id}-1").mkdir()
    (downloaded / f"record-{jobs[0].id}-1" / "record.json").write_text(json.dumps(first))

    def downloaded_already(run: str, directory: Path, tries: int = 3) -> list[str]:
        return []

    monkeypatch.setattr(measure, "fetched", downloaded_already)
    assert measure.main(["fetch", "1", "--out", str(downloaded)]) == 1
    assert "fixture: slice 1 of 2: no report" in capsys.readouterr().out
    # A local run reports the same: the first slice twice, the second never.
    answers = {jobs[0].id: first, jobs[1].id: first}

    def no_selection_problems(kind: str, words: Sequence[str], root: Path) -> list[str]:
        return []

    def the_jobs(request: dict[str, str], root: Path = measure.REPOSITORY) -> list[Job]:
        return jobs

    def run_as_answered(job: Job, out: Path, workers: int, root: Path = measure.REPOSITORY) -> dict[str, Any]:
        return answers[job.id]

    monkeypatch.setattr(measure, "selection_problems", no_selection_problems)
    monkeypatch.setattr(measure, "matrix", the_jobs)
    monkeypatch.setattr(measure, "run_job", run_as_answered)
    assert measure.local("cuts", ["fixture"], 0, "", tmp_path / "local", 4) == 1
    said = capsys.readouterr().out
    assert "fixture: slice 0 of 2: 2 reports" in said
    assert "fixture: slice 1 of 2: no report" in said
    # The control: each slice once, and the local run passes.
    answers[jobs[1].id] = second
    assert measure.local("cuts", ["fixture"], 0, "", tmp_path / "local", 4) == 0


def git(*words: str) -> str:
    return subprocess.run(["git", *words], capture_output=True, text=True, check=True).stdout.strip()


def committed(message: str) -> str:
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return git("rev-parse", "HEAD")


FILES = {
    "tests/property/drawn_strategies.py": "from tests.property import deep_strategies\nWAYS = 1\n",
    "tests/property/deep_strategies.py": "DEEP = 1\n",
    "tests/property/other_strategies.py": "OTHER = 1\n",
    "tests/property/test_drawn.py": (
        "from tests.property.drawn_strategies import WAYS\nfrom tests.property import other_strategies\n"
    ),
    "tests/property/test_second.py": "SECOND = 1\n",
    "tests/property/unrelated.py": "ELSE = 1\n",
    "tests/conftest.py": "PROFILES = 1\n",
    "tests/property/conftest.py": "SHARED = 1\n",
}
BASELINE_OF_TWO = {
    "drawn": ENTRY | {"tests": ["tests/property/test_drawn.py::test_x"]},
    "second": ENTRY | {"tests": ["tests/property/test_second.py"]},
}


def pull_request_repository(root: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A throwaway repository holding `FILES` and the baseline of two selections; its base commit."""
    root = throwaway_repository(root, monkeypatch)
    (root / "tests" / "property").mkdir(parents=True)
    (root / "scripts").mkdir()
    shutil.copy(REPOSITORY / "scripts" / "input_coverage.py", root / "scripts")
    for name, text in FILES.items():
        (root / name).write_text(text, encoding="utf-8")
    write_baseline(root, BASELINE_OF_TWO)
    return committed("base")


def request_of(base: str, head: str) -> dict[str, str]:
    return {"kind": "pull_request", "base": f"{base}...{head}", "python": "3.15"}


def test_a_pull_request_makes_the_cuts_of_what_it_changes_and_none_where_it_changes_nothing_measured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    base = pull_request_repository(tmp_path, monkeypatch)
    counts = {"held": 3}
    asked: list[tuple[str, str]] = []

    def counted(name: str, scope: str, root: Path) -> int:
        asked.append((name, scope))
        return counts["held"]

    monkeypatch.setattr(measure, "scope_cuts", counted)

    def jobs_of(*edits: tuple[str, str | None]) -> list[Job]:
        for name, text in edits:
            if text is None:
                (Path(name)).unlink()
            else:
                Path(name).write_text(text, encoding="utf-8")
        head = committed(f"change {edits}")
        made = measure.matrix(request_of(base, head), Path.cwd())
        git("reset", "-q", "--hard", base)
        return made

    def appended(name: str) -> tuple[str, str]:
        return name, Path(name).read_text(encoding="utf-8") + "# changed\n"

    # A strategy module the tests import: the cuts of the sites naming it, of its selection alone.
    (strategies,) = jobs_of(appended("tests/property/drawn_strategies.py"))
    assert (strategies.nodes, strategies.scope, strategies.expect) == (
        "drawn",
        "*tests/property/drawn_strategies.py::*",
        "baseline",
    )
    # One it imports only through another module (the closure is transitive).
    (deep,) = jobs_of(appended("tests/property/deep_strategies.py"))
    assert (deep.nodes, deep.scope) == ("drawn", "*tests/property/deep_strategies.py::*")
    # Two modules changed together are both in the scope.
    (both,) = jobs_of(
        appended("tests/property/drawn_strategies.py"), appended("tests/property/other_strategies.py")
    )
    assert both.scope == "*tests/property/drawn_strategies.py::* *tests/property/other_strategies.py::*"
    assert asked[-1] == ("drawn", both.scope)
    # A test of a selection: every cut of it.
    (tests,) = jobs_of(appended("tests/property/test_drawn.py"))
    assert (tests.nodes, tests.scope, tests.expect) == ("drawn", "", "baseline")
    assert jobs_of(appended("tests/property/unrelated.py")) == []
    # A test deleted is a change to what its selection runs, not nothing.
    (deleted,) = jobs_of(("tests/property/test_drawn.py", None))
    assert (deleted.nodes, deleted.scope) == ("drawn", "")
    # The Hypothesis profiles are every selection's tests.
    for conftest in ("tests/conftest.py", "tests/property/conftest.py"):
        assert {job.nodes for job in jobs_of(appended(conftest))} == {"drawn", "second"}, conftest
    # The baseline: an entry that differs from the base's, or is new, selects that selection's full run.
    edited = json.loads(json.dumps(BASELINE_OF_TWO))
    edited["second"]["uncut"] = {"another": "a person's note"}
    text = json.dumps(edited)
    assert [(job.nodes, job.scope) for job in jobs_of((measure.BASELINE.as_posix(), text))] == [
        ("second", "")
    ]
    edited["third"] = edited["second"]
    assert {job.nodes for job in jobs_of((measure.BASELINE.as_posix(), json.dumps(edited)))} == {
        "second",
        "third",
    }
    # An unchanged entry, and a removed one, make no job.
    assert jobs_of((measure.BASELINE.as_posix(), json.dumps({"drawn": BASELINE_OF_TWO["drawn"]}))) == []

    # A scope sized from its recording: slices of the cuts it holds, one where it holds few, none where it
    # holds none, and then a notice that names what was changed.
    capsys.readouterr()
    # The fixture's longest cut is 10 s and a slice plans 7200 cut-seconds: 720 cuts fill one.
    counts["held"] = 720
    assert [(job.first, job.length) for job in jobs_of(appended("tests/property/drawn_strategies.py"))] == [
        (0, 1)
    ]
    counts["held"] = 721
    jobs = jobs_of(appended("tests/property/drawn_strategies.py"))
    assert [(job.first, job.length) for job in jobs] == [(0, 2), (1, 2)]
    counts["held"] = 0
    assert jobs_of(appended("tests/property/drawn_strategies.py")) == []
    assert "nothing to check" in capsys.readouterr().out


def test_a_pull_request_diffs_against_the_merge_base_not_the_bases_own_new_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = pull_request_repository(tmp_path, monkeypatch)

    def one_cut(name: str, scope: str, root: Path) -> int:
        return 1

    monkeypatch.setattr(measure, "scope_cuts", one_cut)
    # The pull request changes a strategy module; the base branch has moved on, changing a test.
    git("checkout", "-q", "-b", "feature", base)
    Path("tests/property/drawn_strategies.py").write_text("WAYS = 2\n", encoding="utf-8")
    head = committed("feature")
    git("checkout", "-q", "-b", "moved", base)
    Path("tests/property/test_second.py").write_text("SECOND = 2\n", encoding="utf-8")
    moved = committed("the base moves on")
    jobs = measure.matrix(request_of(moved, head), Path.cwd())
    assert [(job.nodes, job.scope) for job in jobs] == [("drawn", "*tests/property/drawn_strategies.py::*")]


@pytest.mark.parametrize(
    ("base", "head"),
    [
        ("--output=/tmp/x", "b" * 40),
        ("A" * 40, "b" * 40),
        ("a" * 39, "b" * 40),
        ("a" * 40, "b" * 41),
        ("a" * 40, ""),
        ("", "b" * 40),
        ("a" * 40, "b" * 40 + "\n"),
    ],
)
def test_a_pull_request_takes_two_commits_by_their_full_names_and_nothing_else(base: str, head: str) -> None:
    with pytest.raises(MeasureError, match="are not two commits"):
        measure.checked_request({"EVENT": "pull_request", "PR_BASE": base, "PR_HEAD": head}, REPOSITORY)
    good = {"EVENT": "pull_request", "PR_BASE": "a" * 40, "PR_HEAD": "b" * 40}
    assert measure.checked_request(good, REPOSITORY)["base"] == f"{'a' * 40}...{'b' * 40}"
