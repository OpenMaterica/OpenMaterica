# SPDX-License-Identifier: Apache-2.0
"""The measurements a property piece makes before review, run alike on a laptop and as the jobs of
`.github/workflows/measure.yml` (maintainer, 2026-10-23: the battery runs on CI as a matrix, with the same
counts and judgement; only the machine changes).

    uv run python scripts/measure.py floors NODE ... [--streams N]          # 20 by default
    uv run python scripts/measure.py drift NODE ... [--streams N]           # 40
    uv run python scripts/measure.py regions NODE ... --base REF [--streams N]  # 18, and the kills
    uv run python scripts/measure.py fuzz CONTROL[:none] ... [--runs N]      # 10, on Python 3.12 to 3.14
    uv run python scripts/measure.py cuts SELECTION[:whole] ...               # or `all`
    python3 scripts/measure.py report RECORD_OR_DIRECTORY ...
    python3 scripts/measure.py fetch RUN_ID [--out DIRECTORY]                # a CI run's records, reported

Each kind splits into jobs, and each job writes one record (`record.json`: its inputs, the commit, the Python,
the Hypothesis version, the profile, the streams or runs, the raw counts and the timings); `report` merges
records into one table a kind. Locally the jobs run one after another; on CI each is a job of the matrix
(`request`, `job`, `summary`).

- `floors`: each property test function over N derandomised runs at `ci`, each its own stream: every
  feature's mean and least share, its count's variance ratio, and for each feature `ci` judges, its false
  failure by `tests/property/audits.py`'s model at the declared chance and at the variance measured (the count
  as r Bin(n / r, p), r the variance ratio), reported at the mean share and at the least share, and flagged
  above the model's 1e-6 at the least, as the S4d review's probe judged; and the most draws a run rejected.
- `drift`: each mutant search over K streams a size: the kill per stream, whether the search's own assertions
  (the way and the assertion it names) passed, the latest kill, stream 0 against `kill_points.json`, and any
  kill past four fifths of the margin guard (`NEAR`).
- `regions`: the property functions at a base ref and at the head, each in its own tree and environment:
  each recorded feature's mean share at the head against the base's (flagged below `RATIO`), its least share
  against its floor; and a run of every mutant search at the head (`gen_kill_counts.py --measure`'s), whose
  kills are held to the base's and the head's `kill_points.json`.
- `fuzz`: a seeded fuzz control run R times as `ci.yml`'s control step runs it (`CONTROLS`), each in a job of
  its own: each run's find, seconds and inputs; the rate a second and a million inputs; the miss chance of a
  pair and of CI's runs at the fitted rate. `CONTROL:none` runs it with no fault seeded.
- `cuts`: the cuts of `scripts/input_coverage.py`'s selections (`all`, or names of its baseline; `NAME:whole`
  without the selection's `!` patterns, so that the cuts they leave out run too), each selection's cuts split
  into jobs of about equal planned time by its longest cut measured (the baseline's `timing`), a slice each:
  each job records the selection and runs its slice, two cuts at once; the report merges the slices into the
  selection's report and holds it to the baseline (`input_coverage.py check`), a finding a flag. On a pull
  request, the cuts of the sites its change names, held to the baseline (`pull_request_jobs`).

A run of a test is its own: the test's checks run, and a failing check ends that stream's run, recorded as
such; the audit's judgement is skipped and its counts kept. Stream 0 is the test's own derandomised stream;
stream i salts the function's digest. Adding a kind: a function that runs its job, one that reports its
records, an entry in `KINDS`, and a subcommand (`tests/README.md`, "Measurements on CI"). Standard library
only at import: the pytest plugin's hooks below import pytest and Hypothesis when the tree's pytest loads this
file (`-p measure`).
"""

import argparse
import contextlib
import importlib.metadata
import importlib.util
import io
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Generator, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple, cast

REPOSITORY = Path(__file__).resolve().parents[1]
REPO = "OpenMaterica/OpenMaterica"
TOOL = "measure"

# The rules' counts (maintainer, 2026-10-23): 20 runs or more for floors, 40 streams for drift, 18 or more for
# regions, ten runs for a fuzz control. They are the defaults; a smaller count is reported as below its rule.
RATIO = 0.8  # regions: a share at the head keeps at least this of the base's mean
NEAR = 400  # drift: four fifths of the margin guard's 500 (`gen_kill_counts.MARGIN`)
MARGIN = 500
MAX_JOBS = 256  # GitHub's matrix
MAX_STREAMS = 200
MAX_RUNS = 50
PYTHONS = ("3.11", "3.12", "3.13", "3.14", "3.15")
# The cut kind (`scripts/input_coverage.py`): workers a cut and cuts at once on GitHub's runner of four vCPUs,
# the minutes of its job, and the share of them its cuts are planned to fill, by the selection's longest cut
# measured; the rest is the selection's recording and a margin for a runner slower than the one measured on.
CUT_WORKERS = 2
CUTS_AT_ONCE = 2
CUT_JOB_MINUTES = 120
CUT_PLANNED = 0.5
ALL, WHOLE_SELECTION = "all", "whole"
BASELINE = Path("tests/property/input_coverage_baseline.json")
# The files whose change on a pull request runs the self-test: this workflow's own, and the cut kind's tool.
SELF_TESTED = (
    ".github/workflows/measure.yml",
    "scripts/measure.py",
    "scripts/input_coverage.py",
    "tests/property/input_coverage.py",
)
# Tests every selection runs under: the Hypothesis profiles (an example count lowered there would lower every
# selection's).
SHARED_TESTS = ("tests/conftest.py", "tests/property/conftest.py")
SHA = re.compile(r"[0-9a-f]{40}")
PATTERN = re.compile(r"[\x21-\x7e]+")
FUZZ_PYTHON = "3.14"  # Atheris 3.1.0's wheels: 3.12 to 3.14
PROFILE = "ci"

# A plugin run's settings, from the runner to the tree's pytest.
LINES, MODE, STREAMS = "MEASURE_LINES", "MEASURE_MODE", "MEASURE_STREAMS"
ADD_DIGEST = "_hypothesis_internal_add_digest"
CASE = re.compile(
    r"tests/property/(?P<file>test_\w+\.py)::(?P<function>test_\w+)\[(?P<mutant>.+)-(?P<size>small|original)\]"
)
NODE = re.compile(r"tests/property(?:/[A-Za-z0-9_.-]+)*(?:\.py)?(?:::[\x20-\x7e]+)?")
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}")
WHOLE = re.compile(r"0|[1-9][0-9]*")


class Control(NamedTuple):
    """A fuzz control as `ci.yml`'s control step runs it: the fault seeded, the target, the seconds of one
    run, the line that is a find and a line that spoils it, the corpus and dictionary written first, the
    arguments, and how many runs CI makes at most."""

    fault: str
    target: str
    seconds: int
    found: str
    unless: str = ""
    corpus: str = ""
    dictionary: str = ""
    arguments: tuple[str, ...] = ()
    ci_runs: int = 1


SEEDED = "IndexError: the seeded fault"
FIELDS: dict[str, Any] = {"corpus": "fields", "dictionary": "value_field.dict"}
ENTROPIC = ("-entropic_scale_per_exec_time=1",)


def model_disagrees(code: str) -> tuple[str, str]:
    """The model's assertion where the implementation gives `code` and the model does not."""
    return f"^AssertionError: the implementation gives .*'{code}'.*, the model ", f"the model .*'{code}'"


CONTROLS = {
    "bytes": Control(
        "1",
        "jsonio_bytes",
        180,
        f"{SEEDED} in parse",
        corpus="corpus",
        arguments=("-dict=tests/fuzz/json.dict", "-max_len=4096"),
    ),
    "properties": Control("1", "properties", 180, f"{SEEDED} in parse"),
    "record_properties": Control("1", "record_properties", 180, f"{SEEDED} in the read"),
    "read_field_bytes": Control(
        "1", "read_field_bytes", 900, f"{SEEDED} in step 10", **FIELDS, arguments=ENTROPIC, ci_runs=2
    ),
    "tables": Control(
        "tables",
        "read_field_bytes",
        480,
        *model_disagrees("form_invalid"),
        **FIELDS,
        arguments=ENTROPIC,
        ci_runs=2,
    ),
    "table_edges": Control(
        "table_edges",
        "read_field_bytes",
        900,
        "ArithmeticError: the seeded fault in a table's value",
        **FIELDS,
        arguments=ENTROPIC,
        ci_runs=4,
    ),
    "extrapolation_method": Control(
        "extrapolation_method",
        "read_acceptance_bytes",
        480,
        "AssertionError: an extrapolation that breaks its shape not refused",
        corpus="acceptances",
        dictionary="acceptance.dict",
        ci_runs=4,
    ),
    # The model's BC-005 at an acceptance that the implementation does not give, whatever else either gives:
    # the implementation's BC-048 at that acceptance shows beside it only where the model gives none there.
    # The fault skips acceptances 2 and after alone, so a line with the model's BC-005 at acceptance 0 or 1 is
    # no find of it (one that also holds it at a later acceptance needs a second difference beside the fault).
    "declarations": Control(
        "declarations",
        "build_bytes",
        900,
        "^AssertionError: the implementation gives .*, "
        "the model .*'BC-005', '/models/[0-9]*/acceptances/[0-9]*'",
        "the model .*'BC-005', '/models/[0-9]*/acceptances/[01]'",
        corpus="declarations",
        dictionary="declaration.dict",
        ci_runs=4,
    ),
    # Rounds of four, another only where none of a round found it, three at most.
    "table_alternatives": Control(
        "table_alternatives",
        "read_field_bytes",
        900,
        *model_disagrees("outside_range"),
        **FIELDS,
        arguments=ENTROPIC,
        ci_runs=12,
    ),
}
NO_FAULT = "none"

# The counts of stream 0 of the floors self-test's property, as the draft's own CI run recorded them (a
# stream's draws are the same on any machine): a Hypothesis or property change that moves them is a change to
# look at.
SELF_FLOORS_EXAMPLES = 2000
SELF_FLOORS_STREAM_0 = {
    "added": 618,
    "far_swap": 150,
    "none": 797,
    "plural": 163,
    "substituted": 246,
    "swapped": 132,
    "through_an_empty_word": 303,
    "two_edits": 496,
    "underscore": 147,
}

# The measurement a pull request that changes this tool runs on CI (`measure.yml`'s `pull_request` trigger),
# each kind at its rule's count on one small selection, with the answer it must give: stream 0 the recorded
# kill; a tree against itself
# every share's ratio 1 and every kill the recorded one; the fastest control finding its fault, and finding
# nothing with none seeded; and the cuts of one site, a `one_of` S3c builds at module level (its selection's
# name, then the cuts' pattern), one held and one not, each with the baseline's result, and the two cuts the
# pattern must match (`baseline:2`): a pattern that drifts off its site would otherwise check nothing.
SELF_TEST: tuple[tuple[str, str, str], ...] = (
    (
        "floors",
        "tests/property/test_slip_properties.py::test_one_slip_is_what_the_neighbour_generator_reaches",
        "counted",
    ),
    (
        "drift",
        "tests/property/test_table_alternatives_mutants.py::test_the_table_alternatives_mutant_is_killed"
        "[entry_labels_of_the_last_alternative-small]",
        "recorded",
    ),
    ("regions", "tests/property/test_slip_properties.py", "ratio_one"),
    ("fuzz", "properties", "finds"),
    ("fuzz", f"properties:{NO_FAULT}", "no_finds"),
    ("cuts", "extrapolation *::<module>::st.one_of(NOT_TEXT,*", "baseline:2"),
)


class Job(NamedTuple):
    """One job of the matrix: what it measures and over which streams (or which run, or which slice of a
    selection's cuts), as text."""

    id: str
    kind: str  # floors, drift, regions, kills, fuzz or cuts
    nodes: str = ""  # pytest node ids, space-separated; for cuts, a selection, `NAME` or `NAME:whole`
    first: int = 0
    length: int = 1  # streams, from `first`; a fuzz job's run is `first`; cuts: slice `first` of `length`
    side: str = "head"  # regions: base or head
    base: str = ""  # regions and kills: the base commit
    control: str = ""
    fault: str = ""
    python: str = "3.15"
    expect: str = ""
    scope: str = ""  # cuts: fnmatch patterns of the cuts to run, space-separated; all where empty

    def data(self) -> dict[str, object]:
        return dict(self._asdict())


class Kind(NamedTuple):
    rule: int  # the rule's runs or streams
    run: Callable[[Job, Path, int, Path], dict[str, Any]]  # a job, its record's directory, workers, the tree
    report: Callable[[list[dict[str, Any]]], tuple[list[str], list[str]]]  # Markdown, flags


class MeasureError(Exception):
    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = list(problems)


# --- the request --------------------------------------------------------------------------------------------


def whole(name: str, text: str, low: int, high: int, problems: list[str]) -> int:
    if not WHOLE.fullmatch(text):
        problems.append(f"{name} {text!r} is not a whole number in plain digits")
        return low
    if not low <= int(text) <= high:
        problems.append(f"{name} {text} is not from {low} to {high}")
        return low
    return int(text)


def selection_problems(kind: str, words: Sequence[str], root: Path) -> list[str]:
    if not words:
        return ["the selection is empty"]
    problems: list[str] = []
    selections = baseline_of(root) if kind == "cuts" else {}
    for word in words:
        if kind == "cuts":
            name, colon, whole = word.partition(":")
            if (name != ALL and name not in selections) or (colon and whole != WHOLE_SELECTION):
                problems.append(
                    f"{word!r} is not {ALL} or a selection of {BASELINE} ({', '.join(selections)}),"
                    f" alone or with :{WHOLE_SELECTION}"
                )
        elif kind == "fuzz":
            name, _, fault = word.partition(":")
            if name not in CONTROLS or fault not in ("", NO_FAULT):
                problems.append(
                    f"{word!r} is not a control of {', '.join(CONTROLS)}, alone or with :{NO_FAULT}"
                )
        elif not NODE.fullmatch(word) or ".." in word.split("::")[0].split("/"):
            problems.append(f"{word!r} is not a path or node under tests/property in printable ASCII")
        elif not (root / word.split("::")[0]).exists():
            problems.append(f"{word!r} names no file or directory of the tree")
    return problems


def checked_request(environment: Mapping[str, str], root: Path) -> dict[str, str]:
    """The dispatch's inputs, checked; on a pull request, its base and head, from which the matrix takes
    what it changes (`pull_request_jobs`)."""
    if environment.get("EVENT") == "pull_request":
        pull = f"{environment.get('PR_BASE', '')}...{environment.get('PR_HEAD', '')}"
        if not all(SHA.fullmatch(each) for each in pull.split("...")):
            raise MeasureError([f"the pull request's base and head {pull!r} are not two commits"])
        return {
            "kind": "pull_request",
            "selection": "",
            "count": "",
            "per_job": "",
            "base": pull,
            "python": "3.15",
        }
    problems: list[str] = []
    kind = environment.get("KIND", "")
    if kind not in REQUESTABLE:
        problems.append(f"the kind {kind!r} is not one of {', '.join(REQUESTABLE)}")
        raise MeasureError(problems)
    words = environment.get("SELECTION", "").split()
    problems += selection_problems(kind, words, root)
    count, per_job = 0, environment.get("PER_JOB", "")
    if kind == "cuts":
        if environment.get("COUNT", "") or per_job:
            problems.append(
                "the cut kind takes no count and no streams a job: its jobs are its selections' slices"
            )
    else:
        count_text = environment.get("COUNT", "") or str(KINDS[kind].rule)
        count = whole("the count", count_text, 1, MAX_RUNS if kind == "fuzz" else MAX_STREAMS, problems)
    if per_job and kind not in ("fuzz", "cuts"):
        whole("the streams a job", per_job, 1, count, problems)
    base = environment.get("BASE", "")
    if kind == "regions" and not REF.fullmatch(base):
        problems.append(f"the base {base!r} is not a branch, tag or commit name")
    python = environment.get("PYTHON_VERSION", "")
    if python not in PYTHONS:
        problems.append(f"the Python {python!r} is not one of {', '.join(PYTHONS)}")
    if problems:
        raise MeasureError(problems)
    return {
        "kind": kind,
        "selection": " ".join(words),
        "count": str(count) if kind != "cuts" else "",
        "per_job": per_job if kind not in ("fuzz", "cuts") else "",
        "base": base if kind == "regions" else "",
        "python": FUZZ_PYTHON if kind == "fuzz" else python,
    }


def collected(
    nodes: Sequence[str],
    root: Path = REPOSITORY,
    python: Sequence[str] = (),
    tolerated: Sequence[int] = (),
) -> list[dict[str, str]]:
    """What the tree's pytest collects of `nodes` at `ci`: each item's node id and whether it is a property
    (a Hypothesis test) or a mutant search (a test of a `*mutants` module that records its kill)."""
    with tempfile.TemporaryDirectory(prefix="measure-collect-") as scratch:
        lines = Path(scratch) / "lines.jsonl"
        done = subprocess.run(
            [*measuring_pytest(python), "--collect-only", "-q", *nodes],
            cwd=root,
            env=plugin_environment(Path(scratch), lines, "collect", ()),
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode in tolerated:
            return []
        if done.returncode != 0:
            raise MeasureError(
                [
                    f"pytest collected none of {' '.join(nodes)} (exit {done.returncode}):"
                    f" {done.stdout[-2000:]}{done.stderr[-2000:]}"
                ]
            )
        return [json.loads(line) for line in lines.read_text(encoding="utf-8").splitlines()]


def chunks(count: int, per_job: int) -> list[tuple[int, int]]:
    return [(first, min(per_job, count - first)) for first in range(0, count, per_job)]


def baseline_of(root: Path) -> dict[str, Any]:
    """The input coverage's selections (`scripts/input_coverage.py`'s baseline)."""
    path = root / BASELINE
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8"))) if path.exists() else {}


def input_coverage(root: Path = REPOSITORY) -> Any:
    """`scripts/input_coverage.py`, loaded from its file (standard library only, as this script)."""
    spec = importlib.util.spec_from_file_location("input_coverage", root / "scripts" / "input_coverage.py")
    if spec is None or spec.loader is None:
        raise MeasureError(["scripts/input_coverage.py cannot be loaded"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def slices_for(cuts: int, seconds: float) -> int:
    """The slices that `cuts` cuts of up to `seconds` each need, so that a slice's cuts fill `CUT_PLANNED` of
    its job's minutes at most, `CUTS_AT_ONCE` at once."""
    capacity = CUT_PLANNED * CUT_JOB_MINUTES * 60 * CUTS_AT_ONCE
    return max(1, math.ceil(cuts * seconds / capacity))


def cut_jobs(
    words: Sequence[str], python: str, root: Path, expect: str = "", scope: str = "", count: int = 0
) -> list[Job]:
    """The jobs of a cut request: each selection named (`all`, every one) split into slices of about equal
    planned time, by the cuts its baseline's `timing` counts (`cuts`, or `whole_cuts`, those of a recording
    without its `!` patterns, where whole) and its longest cut measured (`slices_for`); `count` slices where
    given."""
    baseline = baseline_of(root)
    named: list[tuple[str, str]] = []
    for word in words:
        name, _, whole = word.partition(":")
        for each in baseline if name == ALL else [name]:
            if (each, whole) not in named:
                named.append((each, whole))
    jobs: list[Job] = []
    for name, whole in named:
        entry = baseline[name]
        timing: dict[str, Any] = entry["timing"]
        cuts = timing["whole_cuts"] if whole else timing["cuts"]
        slices = count or slices_for(cuts, timing["seconds"])
        selection = f"{name}:{whole}" if whole else name
        jobs += [
            Job(
                f"cuts-{selection.replace(':', '-')}-{part}",
                "cuts",
                selection,
                part,
                slices,
                python=python,
                expect=expect,
                scope=scope,
            )
            for part in range(slices)
        ]
    return jobs


def changed_files(pull: str, root: Path) -> list[str]:
    """The files a pull request changes, from its base and head (`BASE...HEAD`): those it deletes too, since
    a deleted test of a selection changes what the selection runs."""
    done = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", pull, "--"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise MeasureError([f"git diff {pull} failed: {done.stderr[-500:]}"])
    return sorted(done.stdout.splitlines())


def imported_closure(files: Sequence[str], root: Path) -> set[str]:
    """The modules of the tree that `files` import, and those they import, and so on (as paths)."""
    module = input_coverage(root)
    found: set[str] = set()
    waiting = [name for name in files if (root / name).is_file()]
    while waiting:
        name = waiting.pop()
        if name in found:
            continue
        found.add(name)
        try:
            imports: set[str] = module.imported(root / name, root)
        except SyntaxError:
            continue  # a module that does not parse fails its own tests; it names nothing it imports
        waiting += [each for each in imports if (root / each).is_file()]
    return found


def baseline_at(commit: str, root: Path) -> dict[str, Any]:
    """The input coverage's selections as a commit holds them (none where it holds no baseline)."""
    done = subprocess.run(
        ["git", "show", f"{commit}:{BASELINE.as_posix()}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return cast(dict[str, Any], json.loads(done.stdout)) if done.returncode == 0 else {}


def scope_cuts(name: str, scope: str, root: Path) -> int:
    """The cuts of a selection that a scope's patterns match, counted from the selection's recording
    (`scripts/input_coverage.py list`, on its default workers): a scope's size is known only so."""
    with tempfile.TemporaryDirectory(prefix="measure-scope-") as scratch:
        report_path = Path(scratch) / "report.json"
        command = [sys.executable, str(root / "scripts" / "input_coverage.py"), "list", name]
        command += ["--report", str(report_path), "--root", str(root), "--baseline", str(root / BASELINE)]
        done = subprocess.run(
            [*command, "--scope", *scope.split()], capture_output=True, text=True, check=False
        )
        if not report_path.exists():
            raise MeasureError(
                [f"the selection {name!r} was not recorded to count a scope's cuts: {done.stdout[-1500:]}"]
            )
        report: dict[str, Any] = json.loads(report_path.read_text(encoding="utf-8"))
    return len(input_coverage(root).shared(report))


def pull_request_jobs(
    changed: Sequence[str],
    python: str,
    root: Path,
    pull: str = "",
    counted: Callable[[str, str, Path], int] | None = None,
) -> list[Job]:
    """The cut jobs of a pull request: for each selection, all its cuts where the change touches one of its
    tests (or `SHARED_TESTS`, the Hypothesis profiles) or edits its entry of the baseline against the base's,
    the cuts of the sites that name a module it changes where that module is one its tests import (in slices
    planned from the cuts that scope holds, none where it holds none: a named note), and none otherwise;
    each slice held to the baseline (its answer `baseline`)."""
    base = baseline_at(pull.partition("...")[0], root) if BASELINE.as_posix() in changed else {}
    jobs: list[Job] = []
    for name, entry in baseline_of(root).items():
        tests = sorted({test.partition("::")[0] for test in entry["tests"]})
        edited = BASELINE.as_posix() in changed and entry != base.get(name)
        if edited or (set(tests) | set(SHARED_TESTS)) & set(changed):
            jobs += cut_jobs([name], python, root, expect="baseline")
            continue
        closure = imported_closure(tests, root)
        touched = [each for each in changed if each in closure and each.endswith(".py")]
        if not touched:
            continue
        scope = " ".join(f"*{each}::*" for each in touched)
        held = (counted or scope_cuts)(name, scope, root)
        if not held:
            names = " ".join(touched)
            print(f"::notice title=Measure::{name}: no cut names {names}, so there is nothing to check")
            continue
        slices = slices_for(held, float(entry["timing"]["seconds"]))
        jobs += cut_jobs([name], python, root, expect="baseline", scope=scope, count=slices)
    return jobs


def matrix(request: Mapping[str, str], root: Path = REPOSITORY) -> list[Job]:
    """The jobs a checked request makes: one a test function (a run of the base and one of the head for
    regions, and one run of every mutant search) and stream chunk, one a control's run, or one a slice of a
    selection's cuts; on a pull request, the self-test where it changes the tool (`SELF_TESTED`), and the cuts
    of what it changes (`pull_request_jobs`)."""
    kind = request["kind"]
    if kind == "pull_request":
        changed = changed_files(request["base"], root)
        jobs = self_test(request["python"], root) if set(changed) & set(SELF_TESTED) else []
        return jobs + pull_request_jobs(changed, request["python"], root, request["base"])
    words = request["selection"].split()
    if kind == "cuts":
        jobs = cut_jobs(words, request["python"], root)
        if len(jobs) > MAX_JOBS:
            raise MeasureError([f"{len(jobs)} jobs, more than a matrix holds ({MAX_JOBS}): select less"])
        return jobs
    count = int(request["count"])
    if kind == "fuzz":
        return [
            Job(
                f"fuzz-{word.replace(':', '-')}-{run}",
                "fuzz",
                first=run,
                control=word.partition(":")[0],
                fault=word.partition(":")[2] or CONTROLS[word.partition(":")[0]].fault,
                python=request["python"],
            )
            for word in words
            for run in range(count)
        ]
    wanted = "search" if kind == "drift" else "property"
    groups: dict[str, list[str]] = defaultdict(list)
    for item in collected(words, root):
        if item["what"] == wanted:
            groups[item["node"].split("[")[0]].append(item["node"])
    if not groups:
        raise MeasureError([f"the selection holds no {wanted} for {kind} to measure"])
    base = resolved(request["base"], root) if kind == "regions" else ""
    sides = ("base", "head") if kind == "regions" else ("head",)
    jobs = [
        Job(
            f"{kind}-{side}-{number}-{first}",
            kind,
            " ".join(nodes),
            first,
            size,
            side,
            base,
            python=request["python"],
        )
        for number, nodes in enumerate(groups.values())
        for first, size in chunks(count, int(request["per_job"] or count))
        for side in sides
    ]
    if kind == "regions":
        jobs.append(Job("kills", "kills", base=base, python=request["python"]))
    if len(jobs) > MAX_JOBS:
        raise MeasureError(
            [f"{len(jobs)} jobs, more than a matrix holds ({MAX_JOBS}): select less, or more streams a job"]
        )
    return jobs


def self_test(python: str, root: Path) -> list[Job]:
    """The self-test's jobs (`SELF_TEST`), each with its answer."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    jobs: list[Job] = []
    for index, (each, selection, expect) in enumerate(SELF_TEST):
        if each == "cuts":
            name, _, scope = selection.partition(" ")
            made = cut_jobs([name], python, root, expect=expect, scope=scope, count=1)
        else:
            asked = {
                "kind": each,
                "selection": selection,
                "count": str(KINDS[each].rule),
                "per_job": "",
                "base": head,
                "python": FUZZ_PYTHON if each == "fuzz" else python,
            }
            made = [job._replace(expect=expect) for job in matrix(asked, root)]
        jobs += [job._replace(id=f"self{index}-{job.id}") for job in made]
    return jobs


def resolved(ref: str, root: Path) -> str:
    for name in (f"origin/{ref}", ref):
        done = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{name}^{{commit}}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode == 0:
            return done.stdout.strip()
    raise MeasureError([f"the base {ref!r} is no commit of the repository"])


def job_from(text: str) -> Job:
    """A job as the matrix gave it to its job, checked again."""
    data: Any = json.loads(text)
    fields = Job._fields
    if not isinstance(data, dict) or set(cast(dict[str, Any], data)) != set(fields):
        raise MeasureError([f"the job {text[:200]!r} is not one of the matrix's"])
    given = cast(dict[str, object], data)
    text_of = {name: str(given[name]) for name in fields}
    if not (WHOLE.fullmatch(text_of["first"]) and WHOLE.fullmatch(text_of["length"])):
        raise MeasureError([f"the job {text[:200]!r} has a stream that is no whole number"])
    job = Job(
        text_of["id"],
        text_of["kind"],
        text_of["nodes"],
        int(text_of["first"]),
        int(text_of["length"]),
        text_of["side"],
        text_of["base"],
        text_of["control"],
        text_of["fault"],
        text_of["python"],
        text_of["expect"],
        text_of["scope"],
    )
    problems: list[str] = []
    if job.kind not in KINDS or job.python not in PYTHONS or job.side not in ("base", "head"):
        problems.append(f"the job {job.id!r} has an unknown kind, Python or side")
    if job.kind == "fuzz" and (
        job.control not in CONTROLS or job.fault not in (NO_FAULT, CONTROLS[job.control].fault)
    ):
        problems.append(f"the job {job.id!r} names no control of CONTROLS")
    if job.base and not re.fullmatch(r"[0-9a-f]{40}", job.base):
        problems.append(f"the job {job.id!r} has a base that is no commit")
    if job.kind in ("floors", "drift", "regions"):
        problems += selection_problems(job.kind, job.nodes.split(), REPOSITORY)
    if job.kind == "cuts":
        problems += selection_problems("cuts", [job.nodes], REPOSITORY)
        if ALL in job.nodes.split(":") or not job.first < job.length:
            problems.append(f"the job {job.id!r} is no slice of one selection's cuts")
        if not all(PATTERN.fullmatch(pattern) for pattern in job.scope.split()):
            problems.append(f"the job {job.id!r} has a scope that is no printable pattern")
    if problems:
        raise MeasureError(problems)
    return job


# --- running a job ------------------------------------------------------------------------------------------


def git_commit(root: Path) -> str:
    done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False
    )
    return done.stdout.strip() + ("+changes" if dirty.stdout.strip() else "") if done.returncode == 0 else ""


def plugin_environment(scratch: Path, lines: Path, mode: str, streams: Sequence[int]) -> dict[str, str]:
    """The environment of a measuring pytest: this file on the path as the plugin `measure`, the profile `ci`,
    no other run's variables."""
    plugin = scratch / "plugin"
    plugin.mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(__file__), plugin / "measure.py")
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("PYTEST_", "MEASURE_", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"))
    }
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [str(plugin), os.environ.get("PYTHONPATH", "")]))
    return environment | {
        "MATERICA_HYPOTHESIS_PROFILE": PROFILE,
        LINES: str(lines),
        MODE: mode,
        STREAMS: ",".join(map(str, streams)),
    }


def measuring_pytest(python: Sequence[str] = ()) -> list[str]:
    """A measuring pytest: the plugin loaded, and no cache written into the tree."""
    return [*(python or [sys.executable]), "-m", "pytest", "-p", "measure", "-p", "no:cacheprovider", "-q"]


def exported(commit: str, root: Path = REPOSITORY) -> tuple[Path, str]:
    """The tree of `commit`, exported with `git archive`, to run in an environment of its own, and the commit
    the archive itself names."""
    tree = Path(tempfile.mkdtemp(prefix="measure-base-"))
    archive = subprocess.run(
        ["git", "archive", "--format=tar", commit], cwd=root, capture_output=True, check=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        named = str(tar.pax_headers.get("comment", ""))
        tar.extractall(tree, filter="data")
    return tree, named


def base_interpreter(tree: Path) -> list[str]:
    """The Python of the base's own locked environment."""
    return ["uv", "run", "--locked", "--quiet", "--directory", str(tree), "python"]


def present_in(tree: Path, python: Sequence[str], nodes: Sequence[str]) -> list[str]:
    """The `nodes` the tree has, from its own collection of their files: a file it lacks, or one that holds no
    test (pytest's exit 5), holds none of them. Any other failure of its collection (a conftest that cannot
    be imported, options it refuses) is the base's problem, and fails the job."""
    have: set[str] = set()
    for file in sorted({node.partition("::")[0] for node in nodes}):
        if (tree / file).exists():
            have.update(item["node"] for item in collected([file], tree, python, tolerated=(5,)))
    return [node for node in nodes if node in have]


def run_pytest_kind(job: Job, out: Path, workers: int, root: Path = REPOSITORY) -> dict[str, Any]:
    """A job of floors, drift or regions: its streams split among `workers` pytest processes of the tree."""
    tree, python, names = root, [sys.executable], job.nodes.split()
    commit = ""
    if job.side == "base":
        tree, commit = exported(job.base, root)
        python = base_interpreter(tree)
        names = present_in(
            tree, python, names
        )  # a node the base lacks is the head's alone: a flag, no problem
    mode = "searches" if job.kind == "drift" else "draws"
    streams = list(range(job.first, job.first + job.length))
    slices = [streams[index::workers] for index in range(min(workers, len(streams)))]
    processes: list[tuple[subprocess.Popen[bytes], Path]] = []
    with tempfile.TemporaryDirectory(prefix="measure-run-") as scratch, contextlib.ExitStack() as logs:
        for index, part in enumerate(slices):
            lines = out / f"lines-{index}.jsonl"
            log = logs.enter_context((out / f"pytest-{index}.log").open("wb"))
            environment = plugin_environment(Path(scratch) / str(index), lines, mode, part)
            if not names:
                break
            command = [*measuring_pytest(python), *names]
            process = subprocess.Popen(
                command, cwd=tree, stdout=log, stderr=subprocess.STDOUT, env=environment
            )
            processes.append((process, lines))
        statuses, problems = waited([process for process, _ in processes])
    runs: list[dict[str, Any]] = []
    for _, lines in processes:
        for line in lines.read_text(encoding="utf-8").splitlines() if lines.exists() else []:
            try:
                runs.append(json.loads(line))
            except ValueError:
                problems.append(f"a line cut short in {lines.name}: {line[:100]!r}")
        lines.unlink(missing_ok=True)  # the record holds them
    problems += [
        f"pytest {index} exited {status} (pytest-{index}.log)"
        for index, status in enumerate(statuses)
        if status != 0
    ]
    nodes = sorted({run["node"] for run in runs})
    problems += [
        f"{node}: no run of stream {stream}"
        for node in nodes
        for stream in streams
        if not any(run["node"] == node and run["stream"] == stream for run in runs)
    ]
    if not nodes and (job.side != "base" or names):
        problems.append("no test of the job ran")
    record: dict[str, Any] = {
        "commit": commit or git_commit(tree),
        "streams": streams,
        "runs": runs,
        "problems": problems,
    }
    if job.side == "base":
        version = subprocess.run(
            [*python, "-c", "import sys; print(sys.version.split()[0])"],
            cwd=tree,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if version:
            record["python"] = version  # the base environment's own, not this interpreter's
        if not commit:
            problems.append("git archive named no commit for the base tree")
    if job.kind == "drift":
        record["recorded"] = recorded_kills(tree, nodes)
    if job.side == "base":
        shutil.rmtree(tree, ignore_errors=True)
    return record


def waited(processes: Sequence[subprocess.Popen[bytes]]) -> tuple[list[int], list[str]]:
    """Each process's exit status; an interrupt (the job's `timeout`) is passed on to each, which then stops
    and keeps what it measured."""
    try:
        return [process.wait() for process in processes], []
    except KeyboardInterrupt:
        for process in processes:
            if process.poll() is None:
                process.send_signal(2)
        with contextlib.suppress(subprocess.TimeoutExpired):
            for process in processes:
                process.wait(timeout=60)
        for process in processes:
            if process.poll() is None:
                process.kill()
        return [process.wait() for process in processes], ["interrupted before the job's timeout"]


def recorded_kills(tree: Path, nodes: Sequence[str]) -> dict[str, int | None]:
    path = tree / "tests" / "property" / "kill_points.json"
    kills: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))["kills"] if path.exists() else {}
    found: dict[str, int | None] = {}
    for node in nodes:
        match = CASE.fullmatch(node)
        group: dict[str, Any] = kills.get(f"{match['file']}::{match['function']}", {}) if match else {}
        pair: list[int] | None = group.get(match["mutant"]) if match else None
        found[node] = pair[0 if match and match["size"] == "small" else 1] if pair else None
    return found


def run_kills(job: Job, out: Path, workers: int, root: Path = REPOSITORY) -> dict[str, Any]:
    """Every mutant search at the head, as `gen_kill_counts.py --measure` runs them, and the kills of the
    base's and the head's `kill_points.json`."""
    spec = importlib.util.spec_from_file_location("gen_kill_counts", root / "scripts" / "gen_kill_counts.py")
    if spec is None or spec.loader is None:
        raise MeasureError(["scripts/gen_kill_counts.py cannot be loaded"])
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = subprocess.run(
        ["git", "show", f"{job.base}:tests/property/kill_points.json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    with tempfile.TemporaryDirectory(prefix="measure-kills-") as directory:
        report = module.measured(workers, Path(directory))
        measured: dict[str, Any] = module.reported([report]).kills if report is not None else {}
    return {
        "commit": git_commit(root),
        "measured": measured,
        "base_recorded": json.loads(base)["kills"],
        "head_recorded": json.loads((root / "tests/property/kill_points.json").read_text())["kills"],
        "problems": [] if report is not None else ["a mutant search failed: see the job's log"],
    }


def found_in(text: str, control: Control) -> str:
    """The first line of `text` that is the control's find, as the control step's `grep`s read it."""
    for line in text.splitlines():
        if re.search(control.found, line) and not (control.unless and re.search(control.unless, line)):
            return line
    return ""


def inputs_run(text: str) -> int:
    """The inputs libFuzzer ran, from its status lines (`#N`) and its last line (`Done N runs`)."""
    counts = [int(number) for number in re.findall(r"^#(\d+)\s", text, re.MULTILINE)]
    counts += [int(number) for number in re.findall(r"^Done (\d+) runs in", text, re.MULTILINE)]
    return max(counts, default=0)


def run_fuzz(job: Job, out: Path, workers: int, root: Path = REPOSITORY, seconds: int = 0) -> dict[str, Any]:
    """One run of a control, as the control step runs it: corpus and dictionary written, then the target until
    its find or its seconds. The record keeps the run's log and what it found, not the corpus."""
    control = CONTROLS[job.control]
    seconds = seconds or control.seconds
    work = Path(tempfile.mkdtemp(prefix="measure-fuzz-"))
    (out / "findings").mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, MATERICA_HYPOTHESIS_PROFILE=PROFILE, MATERICA_FUZZ_SEEDED_FAULT="1")
    module = [sys.executable, "-m", f"tests.fuzz.{control.target}"]
    arguments = [*control.arguments]
    if control.corpus:
        subprocess.run([*module, "--seed", str(work / control.corpus)], cwd=root, env=environment, check=True)
        arguments.insert(0, str(work / control.corpus))
    if control.dictionary:
        subprocess.run(
            [*module, "--dict", str(work / control.dictionary)], cwd=root, env=environment, check=True
        )
        arguments.insert(1, f"-dict={work / control.dictionary}")
    if job.fault == NO_FAULT:
        del environment["MATERICA_FUZZ_SEEDED_FAULT"]
    else:
        environment["MATERICA_FUZZ_SEEDED_FAULT"] = control.fault
    log = out / "fuzz.log"
    started = time.monotonic()
    with log.open("wb") as output:
        process = subprocess.Popen(
            [*module, *arguments, f"-max_total_time={seconds}", f"-artifact_prefix={out / 'findings'}/"],
            cwd=root,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        statuses, problems = waited([process])
    took = time.monotonic() - started
    shutil.rmtree(work, ignore_errors=True)
    text = log.read_text(encoding="utf-8", errors="replace")
    find = found_in(text, control)
    inputs = inputs_run(text)
    if not inputs:
        problems.append("the target ran no input (see fuzz.log)")
    if not find and (statuses[0] != 0 or took < seconds - 1) and not problems:
        problems.append(
            f"the target ended with status {statuses[0]} after {took:.0f} s of its {seconds}, without the"
            " control's find (see fuzz.log)"
        )
    return {
        "commit": git_commit(root),
        "control": job.control,
        "fault": job.fault,
        "run": job.first,
        "limit": seconds,
        "found": bool(find),
        "line": find[:500],
        "seconds": round(took, 3),
        "inputs": inputs,
        "status": statuses[0],
        "problems": problems,
    }


def cut_budget(job: Job, root: Path) -> float | None:
    """The seconds after which a cut job starts no cut: those to the job's interrupt (three minutes before
    its timeout, counted from its start, as the workflow gives them), less one and a half times the
    selection's longest cut measured, so that the last cut started finishes before it. None outside CI."""
    started, minutes = os.environ.get("JOB_STARTED", ""), os.environ.get("JOB_MINUTES", "")
    if not (WHOLE.fullmatch(started) and WHOLE.fullmatch(minutes)):
        return None
    longest = float(baseline_of(root)[job.nodes.partition(":")[0]]["timing"]["seconds"])
    return int(started) + (int(minutes) - 3) * 60 - time.time() - 1.5 * longest


def cut_command(job: Job, report_path: Path, workers: int, root: Path, budget: float | None) -> list[str]:
    """`scripts/input_coverage.py run` for a cut job: the job's slice and scope as the report's share,
    `CUT_WORKERS` workers a cut and as many cuts at once as the job's workers allow, and no cut started after
    the budget."""
    name, _, whole = job.nodes.partition(":")
    command = [
        sys.executable,
        str(root / "scripts" / "input_coverage.py"),
        "run",
        name,
        *("--report", str(report_path), "--root", str(root), "--baseline", str(root / BASELINE)),
        *("--workers", str(CUT_WORKERS), "--parallel", str(max(1, workers // CUT_WORKERS))),
        *("--slice", f"{job.first}/{job.length}"),
    ]
    if whole:
        command.append("--whole")
    if job.scope:
        command += ["--scope", *job.scope.split()]
    if budget is not None:
        command += ["--budget", str(max(0, int(budget)))]
    return command


def run_cuts_job(job: Job, out: Path, workers: int, root: Path = REPOSITORY) -> dict[str, Any]:
    """A slice of a selection's cuts (`cut_command`); the report, with every cut of the share's result, the
    number of cuts the share held (`cuts_in_share`: none means nothing was checked), and the selection's
    baseline entry at this commit are the record's. Its problems: the selection not recorded (it fails with no
    cut), a cut of the share not run in the job's time, an interrupt, the tool's own failure. A cut not held
    that the baseline does not list is a finding of the report, not of the job."""
    name = job.nodes.partition(":")[0]
    report_path = out / "report.json"
    command = cut_command(job, report_path, workers, root, cut_budget(job, root))
    with (out / "input-coverage.log").open("wb") as log:
        process = subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        statuses, problems = waited([process])
    report: dict[str, Any] | None = None
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report_path.unlink()
    held = 0
    if report is None or "cuts" not in report:
        problems.append(
            "the selection was not recorded: it fails with no cut, or the tool failed (input-coverage.log)"
        )
    else:
        share = input_coverage(root).shared(report)
        held = len(share)
        left = sum("result" not in report["cuts"][name] for name in share)
        if left:
            problems.append(f"{left} of the {len(share)} cuts of the job's share not run in its time")
    if statuses[0] not in (0, 1, 2) and not problems:
        problems.append(f"scripts/input_coverage.py exited {statuses[0]} (input-coverage.log)")
    entry: dict[str, Any] = baseline_of(root).get(name, {})
    return {
        "commit": git_commit(root),
        "report": report,
        "baseline": entry,
        "cuts_in_share": held,
        "problems": problems,
    }


def hypothesis_version(runs: Sequence[dict[str, Any]]) -> str:
    """The version the measured tree's runs report, or this environment's."""
    return next((str(run["hypothesis"]) for run in runs), "") or importlib.metadata.version("hypothesis")


def run_job(job: Job, out: Path, workers: int, root: Path = REPOSITORY) -> dict[str, Any]:
    """The job run, and its record written to `out/record.json`."""
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    record = KINDS[job.kind].run(job, out, workers, root)
    record = {
        "tool": TOOL,
        "job": job.data(),
        "python": sys.version.split()[0],
        "profile": PROFILE,
        "hypothesis": hypothesis_version(record.get("runs", [])),
        **record,
        "seconds": round(time.monotonic() - started, 1),
    }
    (out / "record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


# --- the plugin, loaded into the measured tree's pytest (`-p measure`) -------------------------------------


@contextlib.contextmanager
def salted(stream: int) -> Generator[None, None, None]:
    """Stream `stream` of every derandomised run inside: Hypothesis seeds one from its function's digest, to
    which this adds a salt; stream 0 is the run's own."""
    import hypothesis.core as core

    namespace: dict[str, Any] = core.__dict__
    original: Callable[[Any], bytes] = namespace["function_digest"]
    salt = f"measure-stream-{stream}".encode()

    def digest(function: Any) -> bytes:
        held = getattr(function, ADD_DIGEST, None)
        setattr(function, ADD_DIGEST, (held or b"") + salt)
        try:
            return original(function)
        finally:
            if held is None:
                delattr(function, ADD_DIGEST)
            else:
                setattr(function, ADD_DIGEST, held)

    if stream:
        namespace["function_digest"] = digest
    try:
        yield
    finally:
        namespace["function_digest"] = original


def written(line: dict[str, Any]) -> None:
    with Path(os.environ[LINES]).open("a", encoding="utf-8") as lines:
        lines.write(json.dumps(line) + "\n")


def declared(item: Any) -> dict[str, dict[str, Any]]:
    """Each feature the item declares, by its marker: a least share, a chance, a deep chance, or drawn alike
    among several (`tests/property/conftest.py`)."""
    found: dict[str, dict[str, Any]] = {}
    for marker in ("features", "chances", "deep_chances"):
        held = item.get_closest_marker(marker)
        values: dict[str, float] = {} if held is None else held.kwargs
        found |= {name: {"how": marker, "value": float(value)} for name, value in values.items()}
    held = item.get_closest_marker("drawn")
    drawn: tuple[str, ...] = () if held is None else held.args
    return found | {name: {"how": "drawn", "value": 1 / len(drawn)} for name in drawn}


def drawn_runs(item: Any, test: Any, arguments: dict[str, Any], streams: Sequence[int]) -> None:
    from hypothesis import HealthCheck, settings

    from tests.property import audits

    function = getattr(test, "__func__", test)
    held = function._hypothesis_internal_use_settings
    function._hypothesis_internal_use_settings = settings(
        held,
        derandomize=True,
        database=None,
        phases=[phase for phase in held.phases if phase.name not in ("shrink", "explain")],
        suppress_health_check=[
            *held.suppress_health_check,
            HealthCheck.too_slow,
            HealthCheck.filter_too_much,
            HealthCheck.data_too_large,
            HealthCheck.large_base_example,
        ],
    )
    features = declared(item)
    model = {
        "cluster": audits.CLUSTER,
        "shown": audits.SHOWN,
        "false_failure": audits.FALSE_FAILURE,
        "least_draws": audits.LEAST_DRAWS,
        "judged_from": audits.JUDGED_FROM,
        "max_rejection": audits.MAX_REJECTION,
    }
    try:
        for stream in streams:
            started = time.monotonic()
            outcome, message = "passed", ""
            with audits.counting() as counts:
                try:
                    with salted(stream):
                        test(**arguments)
                except Exception as error:  # a failing check ends this stream's run
                    outcome, message = "failed", f"{type(error).__name__}: {error}"[:2000]
            examples = counts.draws["valid"] + counts.draws["interesting"]
            floors = {
                name: audits.draw_floor(examples, spec["value"])
                for name, spec in features.items()
                if spec["how"] in ("drawn", "chances", "deep_chances")
            }
            written(
                {
                    "node": item.nodeid,
                    "stream": stream,
                    "examples": examples,
                    "invalid": counts.draws["invalid"],
                    "features": dict(counts.features),
                    "declared": features,
                    "floors": floors,
                    "model": model,
                    "outcome": outcome,
                    "message": message,
                    "seconds": round(time.monotonic() - started, 2),
                    "hypothesis": importlib.metadata.version("hypothesis"),
                }
            )
    finally:
        function._hypothesis_internal_use_settings = held


def search_runs(item: Any, test: Any, arguments: dict[str, Any], streams: Sequence[int]) -> None:
    for stream in streams:
        captured: dict[str, object] = {}
        given = dict(arguments)
        if "record_property" in given:
            given["record_property"] = captured.__setitem__
        status, message = "killed", ""
        started = time.monotonic()
        try:
            with salted(stream):
                test(**given)
        except AssertionError as error:
            status, message = (
                ("killed elsewhere" if "examples_to_kill" in captured else "survived"),
                str(error),
            )
        except Exception as error:
            status, message = "error", f"{type(error).__name__}: {error}"
        finally:
            if arguments.get("monkeypatch") is not None:
                arguments["monkeypatch"].undo()
        written(
            {
                "node": item.nodeid,
                "stream": stream,
                "kill": captured.get("examples_to_kill"),
                "status": status,
                "message": message[:2000],
                "seconds": round(time.monotonic() - started, 2),
                "hypothesis": importlib.metadata.version("hypothesis"),
            }
        )


def pytest_collection_modifyitems(items: list[Any]) -> None:
    if os.environ.get(MODE) != "collect":
        return
    from hypothesis import is_hypothesis_test

    for item in items:
        search = "record_property" in getattr(item, "fixturenames", ()) and item.path.stem.endswith("mutants")
        what = (
            "property" if is_hypothesis_test(getattr(item, "obj", None)) else "search" if search else "other"
        )
        written({"node": item.nodeid, "what": what})


def pytest_runtest_setup(item: Any) -> None:
    if os.environ.get(MODE) in ("draws", "searches"):
        # The property conftest skips its audit for such an item: this run judges nothing and keeps counts.
        item.add_marker("deep_controls")


def pytest_pyfunc_call(pyfuncitem: Any) -> object:
    mode = os.environ.get(MODE)
    if mode not in ("draws", "searches"):
        return None
    from hypothesis import is_hypothesis_test

    test = pyfuncitem.obj
    arguments = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
    streams = [int(each) for each in os.environ[STREAMS].split(",") if each]
    if mode == "draws" and is_hypothesis_test(test):
        drawn_runs(pyfuncitem, test, arguments, streams)
    elif mode == "searches":
        search_runs(pyfuncitem, test, arguments, streams)
    return True


# --- the reports --------------------------------------------------------------------------------------------


def row(*cells: object) -> str:
    return "| " + " | ".join(map(str, cells)) + " |"


def below(trials: float, chance: float, threshold: float) -> float:
    """P(Bin(floor(trials), chance) < threshold)."""
    n, top = int(trials), math.ceil(threshold) - 1
    if top < 0:
        return 0.0
    if chance <= 0:
        return 1.0
    if chance >= 1:
        return 1.0 if top >= n else 0.0
    return min(
        1.0,
        sum(
            math.exp(
                math.lgamma(n + 1)
                - math.lgamma(k + 1)
                - math.lgamma(n - k + 1)
                + k * math.log(chance)
                + (n - k) * math.log1p(-chance)
            )
            for k in range(min(top, n) + 1)
        ),
    )


def shares(runs: Sequence[dict[str, Any]], name: str) -> tuple[float, float, float, int]:
    """A feature's mean and least share over runs, its count's variance over a binomial's, and the
    examples."""
    examples = min(run["examples"] for run in runs)
    values = [run["features"].get(name, 0) / run["examples"] if run["examples"] else 0.0 for run in runs]
    mean = statistics.fmean(values)
    spread = mean * (1 - mean)
    ratio = statistics.variance(values) * examples / spread if len(values) > 1 and spread > 0 else 1.0
    return mean, min(values), ratio, examples


def judged(spec: dict[str, Any], floor: int | None, examples: int, model: dict[str, Any]) -> float | None:
    """The count below which `ci` fails the feature in a run of `examples`; None where `ci` judges none."""
    if spec["how"] == "deep_chances":
        return None
    if spec["how"] == "features":
        least = spec["value"]
        return least * examples if least * examples >= model["judged_from"] else None
    return floor


def by_node(records: Sequence[dict[str, Any]], side: str = "") -> dict[str, list[dict[str, Any]]]:
    nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if not side or record["job"]["side"] == side:
            for run in record.get("runs", []):
                if run.get("outcome", "passed") == "passed":
                    nodes[run["node"]].append(run)
    return nodes


def first_line(message: str) -> str:
    return (message.splitlines() or [""])[0][:300]


def failed_runs(records: Sequence[dict[str, Any]]) -> list[str]:
    return [
        f"{record['job']['side']} {run['node']}: stream {run['stream']} failed: {first_line(run['message'])}"
        for record in records
        for run in record.get("runs", [])
        if run.get("outcome", "passed") != "passed"
    ]


def report_floors(records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    lines = [
        "| Test | Feature | Judged as | Runs | Mean | Least | Variance ratio | Floor | P at the model |"
        " P at the variance measured, mean share | P at the variance measured, least share |"
        " Most rejected |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    flags = failed_runs(records)
    for node, runs in sorted(by_node(records).items()):
        last = runs[-1]
        rejected = max(
            (run["invalid"] / (run["invalid"] + run["examples"]) for run in runs if run["examples"]),
            default=0.0,
        )
        allowed = last["model"].get("max_rejection", 0.40)
        if rejected > allowed:
            flags.append(
                f"{node}: up to {rejected:.0%} of the draws rejected in a run, above the audit's"
                f" {allowed:.0%}"
            )
        for name, spec in sorted(last["declared"].items()):
            mean, least, ratio, examples = shares(runs, name)
            threshold = judged(spec, last["floors"].get(name), examples, last["model"])
            model = last["model"]
            at_model = at_mean = at_least = None
            if threshold is not None and spec["how"] != "features" and threshold < model["least_draws"]:
                flags.append(
                    f"{node} `{name}`: a floor of {threshold:g}, below {model['least_draws']}, which"
                    " `ci` fails whatever the count"
                )
            if threshold is not None:
                if spec["how"] != "features":
                    at_model = below(examples // model["cluster"], spec["value"], threshold / model["shown"])
                stretch = max(ratio, 1.0)
                at_mean = below(examples / stretch, mean, threshold / stretch)
                at_least = below(examples / stretch, least, threshold / stretch)
                if at_least > model["false_failure"]:  # the least share, as the S4d review's probe judged
                    flags.append(
                        f"{node} `{name}`: false failure {at_least:.1e} a run at the variance measured and"
                        f" the least share ({at_mean:.1e} at the mean), above {model['false_failure']:.0e}"
                    )
            lines.append(
                row(
                    f"`{node}`",
                    f"`{name}`",
                    f"{spec['how']} {spec['value']:.3g}",
                    len(runs),
                    f"{mean:.3f}",
                    f"{least:.3f}",
                    f"{ratio:.2f}",
                    "not at ci" if threshold is None else f"{threshold:g}",
                    "" if at_model is None else f"{at_model:.1e}",
                    "" if at_mean is None else f"{at_mean:.1e}",
                    "" if at_least is None else f"{at_least:.1e}",
                    f"{rejected:.0%}",
                )
            )
    return lines, flags


def report_drift(records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    recorded = {node: kill for record in records for node, kill in record.get("recorded", {}).items()}
    lines = [
        "| Search | Streams | Killed where it names | Latest kill | Stream 0 | Recorded |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    flags: list[str] = []
    searches: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        for run in record.get("runs", []):
            searches[run["node"]].append(run)
    for node, runs in sorted(searches.items()):
        named = [run for run in runs if run["status"] == "killed"]
        kills = [run["kill"] for run in runs if run["kill"] is not None]
        zero = next((run["kill"] for run in runs if run["stream"] == 0), None)
        latest = max(kills, default=None)
        lines.append(
            f"| `{node}` | {len(runs)} | {len(named)} | {latest} | {'' if zero is None else zero}"
            f" | {recorded.get(node)} |"
        )
        flags += [
            f"{node}: stream {run['stream']} {run['status']}: {first_line(run['message'])}"
            for run in runs
            if run["status"] != "killed"
        ]
        flags += [
            f"{node}: stream {run['stream']} killed at example {run['kill']},"
            f" {'past' if run['kill'] > MARGIN else 'near'} the margin guard at {MARGIN}"
            for run in runs
            if run["kill"] is not None and run["kill"] >= NEAR
        ]
        if zero is not None and recorded.get(node) not in (None, zero):
            flags.append(f"{node}: stream 0 killed at {zero}, recorded at {recorded.get(node)}")
    return lines, flags


def report_regions(records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    base, head = by_node(records, "base"), by_node(records, "head")
    lines = [
        "| Test | Feature | Base mean | Head mean | Ratio | Head least | Floor | Runs (base, head) |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    flags = failed_runs([record for record in records if record["job"]["kind"] == "regions"])
    for node in sorted(set(base) | set(head)):
        if not base.get(node) or not head.get(node):
            flags.append(f"{node}: measured on {'the head' if head.get(node) else 'the base'} alone")
            continue
        last = head[node][-1]
        names = set(last["declared"]) | {name for run in base[node] + head[node] for name in run["features"]}
        for name in sorted(names):
            base_mean = shares(base[node], name)[0]
            mean, least, _, examples = shares(head[node], name)
            ratio = mean / base_mean if base_mean else (1.0 if mean == 0 else math.inf)
            spec = last["declared"].get(name)
            threshold = judged(spec, last["floors"].get(name), examples, last["model"]) if spec else None
            lines.append(
                f"| `{node}` | `{name}` | {base_mean:.4f} | {mean:.4f} | {ratio:.2f} | {least:.4f}"
                f" | {'' if threshold is None else f'{threshold:g}'} | {len(base[node])}, {len(head[node])} |"
            )
            if ratio < RATIO:
                flags.append(f"{node} `{name}`: {ratio:.2f} of the base's mean share, below {RATIO}")
            if threshold is not None and least * examples < threshold:
                flags.append(
                    f"{node} `{name}`: least share {least:.4f} below its floor {threshold:g} of {examples}"
                )
    for record in records:
        if record["job"]["kind"] == "kills":
            kill_lines, kill_flags = kills_moved(record)
            lines += ["", *kill_lines]
            flags += kill_flags
    return lines, flags


def kills_moved(record: dict[str, Any]) -> tuple[list[str], list[str]]:
    measured, base, head = record["measured"], record["base_recorded"], record["head_recorded"]
    moved: list[str] = []
    flags: list[str] = []
    count = 0
    for group, mutants in sorted(measured.items()):
        for mutant, sizes in sorted(mutants.items()):
            for index, size in enumerate(("small", "original")):
                kill = sizes.get(size)
                count += 1
                was = base.get(group, {}).get(mutant, [None, None])[index]
                if kill != was:
                    moved.append(f"| `{group}` | `{mutant}` | {size} | {was} | {kill} |")
                if kill != head.get(group, {}).get(mutant, [None, None])[index]:
                    flags.append(
                        f"{group} {mutant} {size}: killed at {kill}, the head records"
                        f" {head.get(group, {}).get(mutant, [None, None])[index]}"
                    )
                if kill is not None and kill > MARGIN:
                    flags.append(
                        f"{group} {mutant} {size}: killed at {kill}, past the margin guard at {MARGIN}"
                    )
    lines = [
        f"Mutant searches run at the head: {count}; kills that moved from the base's record: {len(moved)}."
    ]
    if moved:
        lines += ["", "| Group | Mutant | Size | Base | Head |", "|---|---|---|---:|---:|", *moved]
    return lines, flags + record.get("problems", [])


def miss(rate: float, runs: int, seconds: float) -> float:
    return math.exp(-runs * rate * seconds)


def rate_lower(finds: int, exposure: float, confidence: float = 0.95) -> float:
    """The one-sided lower bound of a Poisson rate from `finds` in `exposure` seconds."""
    if finds == 0 or exposure <= 0:
        return 0.0

    def at_least(rate: float) -> float:
        mean = rate * exposure
        return 1 - sum(math.exp(-mean + k * math.log(mean) - math.lgamma(k + 1)) for k in range(finds))

    low, high = 0.0, finds / exposure
    for _ in range(200):
        middle = (low + high) / 2
        low, high = (middle, high) if at_least(middle) < 1 - confidence else (low, middle)
    return low


def report_fuzz(records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    lines = [
        "| Control | Fault | Runs | Found | Find times (s) | Seconds | Inputs | Finds a second |"
        " A million inputs | Lower bound | Pair misses | CI's runs miss |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    flags: list[str] = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["control"], record["fault"])].append(record)
    for (name, fault), runs in sorted(groups.items()):
        control = CONTROLS[name]
        finds = [run for run in runs if run["found"]]
        exposure = sum(run["seconds"] for run in runs)
        inputs = sum(run["inputs"] for run in runs)
        rate = len(finds) / exposure if exposure else 0.0
        low = rate_lower(len(finds), exposure)
        times = ", ".join(f"{run['seconds']:g}" for run in sorted(finds, key=lambda run: run["seconds"]))
        per_million = len(finds) / inputs * 1e6 if inputs else 0.0
        lines.append(
            row(
                name,
                fault,
                len(runs),
                len(finds),
                times,
                f"{exposure:.0f}",
                inputs,
                f"{rate:.2e}",
                f"{per_million:.2f}",
                f"{low:.2e}",
                f"{miss(rate, 2, control.seconds):.1e}",
                f"{miss(rate, control.ci_runs, control.seconds):.1e} ({control.ci_runs})",
            )
        )
        if fault != NO_FAULT:
            if len(finds) < len(runs):
                flags.append(
                    f"{name}: {len(runs) - len(finds)} of {len(runs)} runs found no fault within"
                    f" {control.seconds} s"
                )
            if miss(rate, 2, control.seconds) > 1e-3:
                flags.append(
                    f"{name}: a pair misses with {miss(rate, 2, control.seconds):.1e} at the fitted rate,"
                    " above the bar of 1e-3"
                )
        elif finds:
            flags.append(f"{name} with no fault seeded found one: {finds[0]['line'][:200]}")
        flags += [
            f"{name}: a run of {run['limit']} s, not the control's {control.seconds}"
            for run in runs
            if run["limit"] != control.seconds
        ]
        # A run that ended early on another failure is a miss in the counts above; its own words say why.
        flags += [
            f"{name}{' with no fault seeded' if fault == NO_FAULT else ''}, run {run.get('run')}: {problem}"
            for run in runs
            for problem in run.get("problems", [])
        ]
    return lines, flags


def reported_under_regions(records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    return [], []


CUT_RESULTS = ("held", "not held", "empty", "invalid", "not applied", "error", "not run")


def cut_groups(records: Sequence[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """The cut kind's records by selection and scope: the slices of one report each."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["job"]["kind"] == "cuts":
            groups[(record["job"]["nodes"], record["job"]["scope"])].append(record)
    return dict(sorted(groups.items()))


NOTHING_CHECKED = "0 in scope: nothing checked"


def cuts_in_scope(group: Sequence[dict[str, Any]]) -> int:
    """The cuts a selection's slices held between them, as its jobs reported them (a record from before the
    jobs reported it: counted from its report)."""
    module = input_coverage()
    return sum(
        int(record["cuts_in_share"])
        if "cuts_in_share" in record
        else len(module.shared(record["report"]))
        if record.get("report")
        else 0
        for record in group
    )


def merged_cuts(group: Sequence[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[str]]:
    """A selection's report merged from its slices' records, and where they do not make one: a slice that
    recorded nothing, slices that recorded other cuts, a slice missing or doubled."""
    reports = [record["report"] for record in group if record.get("report")]
    if not reports:
        return None, ["no slice recorded the selection"]
    merged, problems = input_coverage().merged_reports(reports)
    return merged, list(problems)


def report_cuts(records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """A row a selection (and scope): its sites, its cuts by result, its uncut draws and what its `!`
    patterns leave out, merged from its slices; every place it and the baseline disagree a flag."""
    lines = [
        "| Selection | Scope | Slices | Sites | Cuts | "
        + " | ".join(result.capitalize() for result in CUT_RESULTS)
        + " | Uncut | Left out (sites, cuts, uncut) | In scope |",
        "|---|---|---:|---:|---:|" + "---:|" * len(CUT_RESULTS) + "---:|---|---:|",
    ]
    flags: list[str] = []
    module = input_coverage()
    for (selection, scope), group in cut_groups(records).items():
        merged, _ = merged_cuts(group)
        if merged is None:
            flags.append(f"{selection}: no slice recorded the selection")
            continue
        counts = module.results(merged)
        left: dict[str, int] = merged.get("left_out") or {}
        lines.append(
            row(
                f"`{selection}`",
                " ".join(f"`{pattern}`" for pattern in scope.split()) or "all",
                len(group),
                len(merged["sites"]),
                sum(counts[result] for result in CUT_RESULTS),
                *(counts[result] for result in CUT_RESULTS),
                len(merged["uncut"]),
                f"{left.get('sites', 0)}, {left.get('cuts', 0)}, {left.get('uncut', 0)}",
                cuts_in_scope(group) or NOTHING_CHECKED,
            )
        )
        if not cuts_in_scope(group):
            flags.append(f"{selection}: {NOTHING_CHECKED}")
        flags += [
            f"{selection}: {problem}" for problem in module.problems(merged, group[0].get("baseline", {}))
        ]
    return lines, flags


def cut_problems(records: Sequence[dict[str, Any]]) -> list[str]:
    """Where the cut kind's records do not make one report a selection (`merged_cuts`), and, of a job whose
    answer is the baseline (a pull request's), each place its slice and the baseline disagree, and, of the
    self-test's (`baseline:N`), a count of cuts in scope other than N."""
    problems: list[str] = []
    for (selection, _), group in cut_groups(records).items():
        merged, found = merged_cuts(group)
        problems += [f"{selection}: {problem}" for problem in found]
        answer, _, needed = group[0]["job"]["expect"].partition(":")
        if answer == "baseline" and merged is not None:
            entry = group[0].get("baseline", {})
            problems += [
                f"{selection}, held to the baseline: {each}"
                for each in input_coverage().problems(merged, entry)
            ]
        if answer == "baseline" and needed and cuts_in_scope(group) != int(needed):
            held = cuts_in_scope(group)
            problems.append(
                f"{selection}: {held} cuts in scope, and the self-test's pattern must match {needed}"
            )
    return problems


KINDS: dict[str, Kind] = {
    "floors": Kind(20, run_pytest_kind, report_floors),
    "drift": Kind(40, run_pytest_kind, report_drift),
    "regions": Kind(18, run_pytest_kind, report_regions),
    "kills": Kind(1, run_kills, reported_under_regions),
    "fuzz": Kind(10, run_fuzz, report_fuzz),
    # No count: a selection's cuts are run each once.
    "cuts": Kind(0, run_cuts_job, report_cuts),
}
# The kinds a request may name; `kills` runs within regions.
REQUESTABLE = tuple(kind for kind in KINDS if kind != "kills")


def records_in(paths: Sequence[Path]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for path in paths:
        for each in sorted(path.rglob("record.json")) if path.is_dir() else [path]:
            data: Any = json.loads(each.read_text(encoding="utf-8"))
            if isinstance(data, dict) and cast(dict[str, Any], data).get("tool") == TOOL:
                found.append(cast(dict[str, Any], data))
    return found


def least_counted(records: Sequence[dict[str, Any]]) -> int:
    """The least a test function's streams over all the records (however the jobs split them), or a fuzz
    control's runs: what the rule's count is held against."""
    streams = Counter(
        (record["job"]["side"], run["node"]) for record in records for run in record.get("runs", [])
    )
    if streams:
        return min(streams.values())
    controls = Counter(
        (record.get("control"), record.get("fault")) for record in records if "control" in record
    )
    if controls:
        return min(controls.values())
    return min((len(record["streams"]) for record in records if "streams" in record), default=0)


def report(records: Sequence[dict[str, Any]]) -> tuple[str, list[str]]:
    """One Markdown section a kind, and every flag."""
    text: list[str] = []
    flags: list[str] = []
    for kind in REQUESTABLE:
        mine = [
            record
            for record in records
            if record["job"]["kind"] in ((kind, "kills") if kind == "regions" else (kind,))
        ]
        if not mine:
            continue
        lines, found = KINDS[kind].report(mine)
        counted = least_counted(mine)
        meta = sorted(
            {
                f"{record['commit'][:12]} on Python {record['python']}"
                + (f", Hypothesis {record['hypothesis']}" if record["hypothesis"] else "")
                for record in mine
            }
        )
        text += [f"## {kind}", "", f"{len(mine)} records; {'; '.join(meta)}."]
        if counted < KINDS[kind].rule:
            text.append(
                f"{counted} {'runs' if kind == 'fuzz' else 'streams'}, fewer than the rule's"
                f" {KINDS[kind].rule}: this measures, and does not meet the rule."
            )
        text += ["", *lines, ""]
        if found:
            text += ["Flags:", "", *[f"- {flag}" for flag in found], ""]
        flags += found
    return "\n".join(text), flags


def counted_problems(record: dict[str, Any]) -> list[str]:
    """Where a measured run of a self-test job counted nothing, or not what it counted before: every run
    its examples, and every feature the test declares counted."""
    job = record["job"]["id"]
    runs = record.get("runs", [])
    if not runs:
        return [f"{job}: no run was counted"]
    problems: list[str] = []
    for run in runs:
        if run.get("outcome", "passed") != "passed":
            problems.append(f"{job}: {run['node']} stream {run['stream']} ended {run['outcome']}")
        elif not run["examples"]:
            problems.append(f"{job}: {run['node']} stream {run['stream']} counted no examples")
    declared: dict[str, int] = {}
    for run in runs:
        for name in run["declared"]:
            declared[name] = declared.get(name, 0) + run["features"].get(name, 0)
    problems += [
        f"{job}: the declared feature `{name}` was never counted" for name, n in declared.items() if not n
    ]
    return problems


def drew_examples(record: dict[str, Any]) -> list[str]:
    """Where a self-test stream drew other than the examples the `ci` profile gives its property."""
    return [
        f"{record['job']['id']}: stream {run['stream']} drew {run['examples']} examples, not"
        f" {SELF_FLOORS_EXAMPLES}"
        for run in record.get("runs", [])
        if run["examples"] != SELF_FLOORS_EXAMPLES
    ]


def expectations(records: Sequence[dict[str, Any]], flags: Sequence[str]) -> list[str]:
    """Where a self-test job's answer is not the one it must give. A flag is a finding about the tree, not an
    answer: only these fail the self-test."""
    problems: list[str] = []
    for record in records:
        expect, job = record["job"]["expect"], record["job"]
        if expect == "recorded":
            runs = [run for run in record.get("runs", []) if run["stream"] == 0]
            if not runs or any(
                record["recorded"].get(run["node"]) is None or run["kill"] != record["recorded"][run["node"]]
                for run in runs
            ):
                problems.append(f"{job['id']}: stream 0 is not the recorded kill")
        elif expect == "counted":
            problems += counted_problems(record)
            first = {run["stream"]: run for run in record.get("runs", [])}.get(0)
            if first is None or first["features"] != SELF_FLOORS_STREAM_0:
                problems.append(f"{job['id']}: stream 0 did not count what it counted before")
            problems += drew_examples(record)
        elif expect == "ratio_one":
            if job["kind"] == "regions":
                problems += counted_problems(record) + drew_examples(record)
            if any("of the base's mean share" in flag or "alone" in flag for flag in flags):
                problems.append(f"{job['id']}: a tree against itself gave a share ratio other than 1")
        elif expect in ("finds", "no_finds") and record["found"] != (expect == "finds"):
            problems.append(f"{job['id']}: expected {'a find' if expect == 'finds' else 'no find'}")
    kills = [record for record in records if record["job"]["kind"] == "kills" and record["job"]["expect"]]
    for record in kills:
        if kills_moved(record)[1]:
            problems.append(f"{record['job']['id']}: a tree against itself moved a kill")
    if records and any(record["job"]["expect"] == "ratio_one" for record in records):
        sides = {record["job"]["side"] for record in records if record["job"]["expect"] == "ratio_one"}
        if sides != {"base", "head"}:
            problems.append("the regions self-test lacks a side")
    return problems


def counted_against(ids: Sequence[str], found: Sequence[dict[str, Any]]) -> list[str]:
    """The records counted against the matrix's jobs: one each, none missing, none of a job not asked for."""
    counted = Counter(record["job"]["id"] for record in found)
    problems = [
        f"job {name}: no record (its job failed before writing one, or was cancelled)"
        for name in ids
        if counted[name] == 0
    ]
    problems += [f"job {name}: {number} records" for name, number in sorted(counted.items()) if number > 1]
    problems += [f"a record of no requested job: {name}" for name in sorted(set(counted) - set(ids))]
    return problems


def summary(directory: Path, jobs: Sequence[Job], result: str, attempt: int) -> tuple[str, bool]:
    """The run's table, after counting each job's record: one each, every one finished."""
    found = records_in([directory])
    problems = counted_against([job.id for job in jobs], found)
    problems += [
        f"job {record['job']['id']}: {problem}" for record in found for problem in record.get("problems", [])
    ]
    text, flags = report(found)
    problems += expectations(found, flags) + cut_problems(found)
    if result != "success":
        problems.append(f"the measurement jobs ended in {result!r}")
    if attempt != 1:
        problems.append(f"attempt {attempt} of the run, which counts only a first: dispatch it anew")
    verdict = "every job's record, each once, finished" if not problems else f"{len(problems)} problems"
    head = [
        f"# Measurements: {verdict}",
        "",
        f"{len(found)} records of {len(jobs)} jobs; {len(flags)} flags.",
        "",
    ]
    if problems:
        head += ["## Problems", "", *[f"- {problem}" for problem in problems], ""]
    return "\n".join(head) + text, not problems


# --- the command --------------------------------------------------------------------------------------------


def write_outputs(values: Mapping[str, str]) -> None:
    lines = "".join(f"{name}={value}\n" for name, value in values.items())
    if target := os.environ.get("GITHUB_OUTPUT"):
        with Path(target).open("a", encoding="utf-8") as output:
            output.write(lines)
    else:
        print(lines, end="")


MATRIX_FILE = "matrix.json"  # beside the table: the ids of the matrix's jobs, for `fetch` to count against
WANTED = ("record-*", "measure-table-*")


def fetched(run: str, directory: Path, tries: int = 3) -> list[str]:
    """A run's record artifacts, and its tables (which hold the run's matrix), downloaded into `directory`:
    all at once, or where that fails one by one, each tried `tries` times; the names of those not had."""
    command = ["gh", "run", "download", run, "-R", REPO]
    patterns = [item for pattern in WANTED for item in ("-p", pattern)]
    if subprocess.run([*command, "-D", str(directory), *patterns], check=False).returncode == 0:
        return []
    listed = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{REPO}/actions/runs/{run}/artifacts",
            "--paginate",
            "--jq",
            ".artifacts[].name",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    names = sorted(name for name in listed.stdout.split() if name.startswith(("record-", "measure-table-")))
    if listed.returncode != 0 or not names:
        raise MeasureError([f"the artifacts of run {run} could not be listed: {listed.stderr[-300:]}"])
    return [
        name
        for name in names
        if not any(
            subprocess.run([*command, "-D", str(directory / name), "-n", name], check=False).returncode == 0
            for _ in range(tries)
        )
    ]


def local(kind: str, words: Sequence[str], count: int, base: str, out: Path, workers: int) -> int:
    """A kind's jobs run here one after another, then reported."""
    request = {
        "kind": kind,
        "selection": " ".join(words),
        "count": str(count),
        "per_job": "",
        "base": base,
        "python": ".".join(map(str, sys.version_info[:2])),
    }
    problems = selection_problems(kind, words, REPOSITORY)
    if problems:
        raise MeasureError(problems)
    records: list[dict[str, Any]] = []
    for job in matrix(request):
        print(f"measuring {job.id}: {job.nodes or job.control} ...", flush=True)
        records.append(run_job(job, out / job.id, workers))
    text, _ = report(records)
    print(text)
    print(f"records: {out}")
    merging = cut_problems(records)
    if merging:
        print("\nThis report is wrong:")
        print("\n".join(f"- {problem}" for problem in merging))
    return 1 if merging or any(record.get("problems") for record in records) else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").partition("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for kind in REQUESTABLE:
        each = commands.add_parser(kind, help=f"measure {kind} here")
        each.add_argument("selection", nargs="+")
        if KINDS[kind].rule:
            each.add_argument(
                "--streams" if kind != "fuzz" else "--runs", type=int, default=KINDS[kind].rule, dest="count"
            )
        each.add_argument("--workers", type=int, default=8)
        each.add_argument("--out", type=Path)
        if kind == "regions":
            each.add_argument("--base", required=True)
    commands.add_parser("request", help="check the dispatch's inputs and write them as outputs")
    commands.add_parser("matrix", help="the request's jobs, as the output `matrix`")
    job_parser = commands.add_parser("job", help="run the job `JOB` and write its record to DIRECTORY")
    job_parser.add_argument("directory", type=Path)
    job_parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    reporting = commands.add_parser("report", help="the records' table")
    reporting.add_argument("paths", nargs="+", type=Path)
    summing = commands.add_parser(
        "summary", help="count the records under DIRECTORY against MATRIX, then report"
    )
    summing.add_argument("directory", type=Path)
    summing.add_argument("output", type=Path)
    fetching = commands.add_parser("fetch", help="a CI run's records, downloaded and reported")
    fetching.add_argument("run")
    fetching.add_argument("--out", type=Path, help="the directory to download into (a new one by default)")
    arguments = parser.parse_args(argv)
    try:
        if arguments.command in REQUESTABLE:
            out = arguments.out or Path(tempfile.mkdtemp(prefix=f"measure-{arguments.command}-"))
            return local(
                arguments.command,
                arguments.selection,
                getattr(arguments, "count", 0),
                getattr(arguments, "base", ""),
                out,
                arguments.workers,
            )
        if arguments.command == "request":
            request = checked_request(os.environ, Path.cwd())
            write_outputs(request)
            print(f"The request, checked: {request}")
        elif arguments.command == "matrix":
            request = {
                name: os.environ.get(name.upper(), "")
                for name in ("kind", "selection", "count", "per_job", "base", "python")
            }
            jobs = matrix(request)
            write_outputs({"matrix": json.dumps([job.data() for job in jobs])})
            print(f"{len(jobs)} jobs")
        elif arguments.command == "job":
            job = job_from(os.environ.get("JOB", ""))
            record = run_job(job, arguments.directory, arguments.workers)
            print(
                json.dumps(
                    {key: value for key, value in record.items() if key not in ("runs", "measured", "report")}
                )
            )
            return 1 if record.get("problems") else 0
        elif arguments.command == "report":
            print(report(records_in(arguments.paths))[0])
        elif arguments.command == "summary":
            jobs = [job_from(json.dumps(each)) for each in json.loads(os.environ.get("MATRIX", "[]"))]
            text, ok = summary(
                arguments.directory,
                jobs,
                os.environ.get("RESULT", ""),
                int(os.environ.get("ATTEMPT", "0") or 0),
            )
            arguments.output.mkdir(parents=True, exist_ok=True)
            (arguments.output / "table.md").write_text(text + "\n", encoding="utf-8")
            (arguments.output / MATRIX_FILE).write_text(
                json.dumps([job.id for job in jobs]), encoding="utf-8"
            )
            if target := os.environ.get("GITHUB_STEP_SUMMARY"):
                with Path(target).open("a", encoding="utf-8") as markdown:
                    markdown.write(text + "\n")
            print(text)
            return 0 if ok else 1
        else:
            directory = arguments.out or Path(tempfile.mkdtemp(prefix="measure-fetch-"))
            directory.mkdir(parents=True, exist_ok=True)
            missing = fetched(arguments.run, directory)
            found = records_in([directory])
            print(report(found)[0])
            print(f"records: {directory}")
            matrices = sorted(directory.rglob(MATRIX_FILE))
            problems = [f"{len(missing)} artifacts not downloaded: {', '.join(missing)}"] if missing else []
            if matrices:
                problems += counted_against(json.loads(matrices[0].read_text(encoding="utf-8")), found)
            else:
                problems.append("the run kept no table, so its records are not counted against its matrix")
            problems += cut_problems(found)
            if problems:
                print("\nThis report is partial or wrong:")
                print("\n".join(f"- {problem}" for problem in problems))
                return 1
    except MeasureError as error:
        for problem in error.problems:
            print(f"::error title=Measure::{problem}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
