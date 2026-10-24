# SPDX-License-Identifier: Apache-2.0
"""The cut kind of the measurement tool (`scripts/measure.py`, `.github/workflows/measure.yml`): a request
names selections of the input coverage's baseline; the matrix splits each into slices by its timing; a job
runs its slice and keeps the selection's report; the summary merges the slices, refuses a slice missing or
recording other cuts, and holds a pull request's to the baseline, a dispatch's findings flags; a pull request
makes the cuts of what it changes, and none where it changes nothing measured.

The jobs run `scripts/input_coverage.py` on a tree of their own, written here, with copies of the runner and
the plugin, as `tests/unit/test_input_coverage.py` does."""

import json
import math
import shutil
import subprocess
import time
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
    text, ok = measure.summary(tmp_path / "records", jobs, "success", 1)
    assert ok, text
    assert "| `fixture` | all | 2 | 1 | 2 | 1 | 1 |" in text
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


def git(*words: str) -> str:
    return subprocess.run(["git", *words], capture_output=True, text=True, check=True).stdout.strip()


def committed(message: str) -> str:
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return git("rev-parse", "HEAD")


def test_a_pull_request_makes_the_cuts_of_what_it_changes_and_none_where_it_changes_nothing_measured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = throwaway_repository(tmp_path, monkeypatch)
    (root / "tests" / "property").mkdir(parents=True)
    (root / "scripts").mkdir()
    shutil.copy(REPOSITORY / "scripts" / "input_coverage.py", root / "scripts")
    files = {
        "tests/property/drawn_strategies.py": "WAYS = 1\n",
        "tests/property/test_drawn.py": "from tests.property.drawn_strategies import WAYS\n",
        "tests/property/unrelated.py": "OTHER = 1\n",
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    entry = ENTRY | {"tests": ["tests/property/test_drawn.py::test_x"]}
    write_baseline(root, {"drawn": entry})
    base = committed("base")

    def jobs_of(name: str) -> list[Job]:
        (root / name).write_text((root / name).read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
        head = committed(f"change {name}")
        made = measure.matrix({"kind": "pull_request", "base": f"{base}...{head}", "python": "3.15"}, root)
        git("reset", "-q", "--hard", base)
        return made

    (strategies,) = jobs_of("tests/property/drawn_strategies.py")
    assert (strategies.nodes, strategies.scope, strategies.expect) == (
        "drawn",
        "*tests/property/drawn_strategies.py::*",
        "baseline",
    )
    (tests,) = jobs_of("tests/property/test_drawn.py")
    assert (tests.nodes, tests.scope, tests.expect) == ("drawn", "", "baseline")
    assert jobs_of("tests/property/unrelated.py") == []

    # A change to the tool runs the self-test besides.
    def self_test(python: str, root: Path) -> list[Job]:
        return [Job("self", "fuzz")]

    monkeypatch.setattr(measure, "self_test", self_test)
    assert [job.id for job in jobs_of("scripts/input_coverage.py")] == ["self"]
