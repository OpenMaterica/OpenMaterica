# SPDX-License-Identifier: Apache-2.0
"""The input-coverage checker's controls (`scripts/input_coverage.py`, `tests/property/input_coverage.py`): a
draw no test holds is reported not held, and held once a test holds it; the plugin loaded changes no draw; a
draw it cannot cut is listed uncut, never held; a cut that leaves nothing to draw, or no valid example, is
reported as that; and the baseline fails on a cut not held that it does not list and on one now held.

Each runs the checker on a tree of its own, written here, with a copy of the plugin: importing the plugin into
this process would put its wrappers in front of every later test's strategies."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import input_coverage
from scripts.input_coverage import cuts_of, problems, result_of

REPOSITORY = Path(__file__).resolve().parents[2]
PLUGIN = REPOSITORY / "tests" / "property" / "input_coverage.py"

HEADER = """
import random

from hypothesis import find, given, settings, strategies as st
from hypothesis.strategies import sampled_from

DERANDOMIZED = settings(derandomize=True, database=None, max_examples=40, deadline=None)
"""

# A composite of two draws, of which one test holds the value "a" alone.
HOLDS_A = (
    HEADER
    + """

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
)
HOLDS_B = """

def test_b_is_drawn():
    find(drawn(), lambda example: example == "b", settings=DERANDOMIZED)
"""

# Every kind of draw the plugin cuts, a constructor bound at import among them, and what it does not cut.
EVERYTHING = (
    HEADER
    + """

def helper(draw):
    return draw(st.sampled_from(["p", "q"]))


@st.composite
def everything(draw):
    return (
        draw(sampled_from(["a", "b", "c"])),
        draw(st.one_of(st.just(1), st.integers(2, 5))),
        draw(st.none() | st.booleans()),
        draw(st.floats(0.0, 1.0)),
        draw(st.floats(min_value=0.0, exclude_min=True, allow_infinity=False)),
        draw(st.integers(0, 1)),
        draw(st.lists(st.integers(0, 3), min_size=1, max_size=4)),
        draw(st.lists(st.booleans())),
        draw(st.sets(st.integers(0, 9), max_size=3)),
        draw(st.dictionaries(st.sampled_from("xy"), st.booleans(), max_size=2)),
        draw(st.permutations([1, 2, 3])),
        draw(st.tuples(st.just(0), st.integers(0, 1))),
        helper(draw),
        draw(st.text(max_size=3)),
        draw(st.randoms(use_true_random=False)).random(),
        random.Random(1).random(),
    )


@st.composite
def other(draw):
    return helper(draw)


@DERANDOMIZED
@given(everything(), other())
def test_everything(example, again):
    pass
"""
)

UNCUT = {
    "tests/test_everything.py::everything::st.text(max_size=3)": "text",
    "tests/test_everything.py::everything::st.randoms(use_true_random=False)": "randoms",
    "tests/test_everything.py::everything::random.Random(1)": "random",
}

# A value drawn alone (no cut can drop it and leave a draw), and a range a filter makes invalid at one end.
EMPTY_AND_INVALID = (
    HEADER
    + """

@st.composite
def drawn(draw):
    return draw(st.sampled_from(["only"])), draw(st.integers(0, 3).filter(lambda number: number > 0))


@DERANDOMIZED
@given(drawn())
def test_drawn(example):
    pass
"""
)


def tree(root: Path, modules: dict[str, str]) -> Path:
    (root / "tests" / "property").mkdir(parents=True)
    # The tree's own root for pytest, whatever lies above it.
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests" / "property" / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy(PLUGIN, root / "tests" / "property" / "input_coverage.py")
    for name, source in modules.items():
        (root / "tests" / name).write_text(source, encoding="utf-8")
    return root


def check(
    root: Path, command: str, module: str, baseline: dict[str, Any] | None = None, report: str = "report.json"
) -> tuple[int, dict[str, Any], str]:
    """The checker run on `module`'s draws over its tests, a process a cut: its exit, report and output."""
    (root / "baseline.json").write_text(
        json.dumps(
            {"fixture": {"tests": [f"tests/{module}"], "sites": [f"tests/{module}::*"], **(baseline or {})}}
        ),
        encoding="utf-8",
    )
    arguments = [command, "fixture", "--baseline", str(root / "baseline.json"), "--root", str(root)]
    arguments += ["--workers", "0", "--parallel", "4", "--report", str(root / report), "--timeout", "120"]
    completed = subprocess.run(
        [sys.executable, str(REPOSITORY / "scripts" / "input_coverage.py"), *arguments],
        capture_output=True,
        text=True,
        cwd=root,
        env=fixture_environment(),
        timeout=600,
        check=False,
    )
    return completed.returncode, json.loads((root / report).read_text(encoding="utf-8")), completed.stdout


def results(report: dict[str, Any]) -> dict[str, str]:
    return {name.rpartition(" :: ")[2]: cut["result"] for name, cut in report["cuts"].items()}


def test_a_draw_no_test_holds_is_reported_not_held_and_held_once_a_test_holds_it(tmp_path: Path) -> None:
    root = tree(tmp_path, {"test_holds.py": HOLDS_A})
    status, report, output = check(root, "run", "test_holds.py")
    assert results(report) == {"drop 'a'": "held", "drop 'b'": "not held"}
    cut = report["cuts"]["tests/test_holds.py::drawn::st.sampled_from(['a', 'b']) :: drop 'a'"]
    assert cut["test"] == "tests/test_holds.py::test_a_is_drawn", cut
    assert status == 1
    assert (
        "not held, and not in the baseline: "
        "tests/test_holds.py::drawn::st.sampled_from(['a', 'b']) :: drop 'b'" in output
    )
    (root / "tests" / "test_holds.py").write_text(HOLDS_A + HOLDS_B, encoding="utf-8")
    status, report, output = check(root, "run", "test_holds.py", report="again.json")
    assert results(report) == {"drop 'a'": "held", "drop 'b'": "held"}, output
    assert status == 0, output


def fixture_environment() -> dict[str, str]:
    """This process's environment without `CI`: a fixture tree has no conftest, and where `CI` is set
    Hypothesis loads its own `ci` profile there (derandomized, no example database), which the controls
    must not rest on."""
    return {name: value for name, value in os.environ.items() if name != "CI"}


def pytest_in(root: Path, module: str, *options: str) -> tuple[Path, "subprocess.CompletedProcess[str]"]:
    """pytest run on one module of the tree, Hypothesis's storage (its example database among it) in a
    directory of its own, which it returns, with every test case observed there."""
    storage = root / f"storage-{len(list(root.glob('storage-*')))}"
    environment = {
        **fixture_environment(),
        "HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY": "1",
        "HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_NOCOVER": "1",
        "HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_CHOICES": "1",
        "HYPOTHESIS_STORAGE_DIRECTORY": str(storage),
    }
    command = [sys.executable, "-m", "pytest", f"tests/{module}", "-q", "-p", "no:cacheprovider", *options]
    completed = subprocess.run(
        command, capture_output=True, text=True, cwd=root, env=environment, timeout=300, check=False
    )
    return storage, completed


def observed(root: Path, *options: str, module: str = "test_everything.py") -> list[tuple[Any, ...]]:
    """Every test case the module's tests drew, as Hypothesis's observability reports them: the test, its
    status, its arguments and the choices drawn."""
    storage, completed = pytest_in(root, module, *options)
    assert completed.returncode == 0, completed.stdout[-3000:]
    cases: list[tuple[Any, ...]] = []
    for path in sorted((storage / "observed").glob("*_testcases.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            case = json.loads(line)
            choices = json.dumps(case["metadata"]["choice_nodes"], sort_keys=True)
            cases.append((case["property"], case["status"], case["representation"], choices))
    assert cases
    return cases


def test_the_plugin_loaded_with_no_cut_changes_no_draw(tmp_path: Path) -> None:
    root = tree(tmp_path, {"test_everything.py": EVERYTHING})
    without = observed(root)
    plugin = ("-p", "tests.property.input_coverage")
    assert observed(root, *plugin) == without
    assert observed(root, *plugin, "--input-coverage-out", str(root / "recorded")) == without
    recorded = json.loads(next((root / "recorded").glob("sites-*.json")).read_text(encoding="utf-8"))["sites"]
    kinds = {seen["kind"] for seen in recorded.values()}
    assert kinds >= {"sampled_from", "one_of", "|", "booleans", "integers", "floats", "lists", "sets"}
    assert kinds >= {"dictionaries", "permutations", "text", "randoms"}
    site = "tests/test_everything.py::everything::sampled_from(['a', 'b', 'c'])"
    assert site in recorded
    elsewhere = json.dumps({"site_id": site, "change": "drop", "key": "'z'"})
    cut = ("--input-coverage-out", str(root / "elsewhere"), "--input-coverage-cut", elsewhere)
    assert observed(root, *plugin, *cut) == without
    # The control: the same comparison fails where a cut applies.
    applied = json.dumps({"site_id": site, "change": "drop", "key": "'a'"})
    cut = ("--input-coverage-out", str(root / "applied"), "--input-coverage-cut", applied)
    assert observed(root, *plugin, *cut) != without


# A property under Hypothesis's own settings, drawn at random, and one that fails, whose example the
# database keeps.
AT_RANDOM = (
    HEADER
    + """

@given(st.integers(0, 10**9))
def test_at_random(number):
    pass
"""
)
FAILS = (
    HEADER
    + """

@given(st.integers(0, 10**9))
def test_fails(number):
    assert number < 10
"""
)


def test_a_recording_run_is_derandomized_and_keeps_no_example(tmp_path: Path) -> None:
    root = tree(tmp_path, {"test_at_random.py": AT_RANDOM, "test_fails.py": FAILS})
    # The controls: without the plugin, two runs draw apart, and a failing example is kept.
    assert observed(root, module="test_at_random.py") != observed(root, module="test_at_random.py")
    storage, completed = pytest_in(root, "test_fails.py")
    assert completed.returncode == pytest.ExitCode.TESTS_FAILED, completed.stdout[-3000:]
    assert (storage / "examples").is_dir()
    recording = ("-p", "tests.property.input_coverage", "--input-coverage-out", str(root / "recorded"))
    first = observed(root, *recording, module="test_at_random.py")
    assert observed(root, *recording, module="test_at_random.py") == first
    storage, completed = pytest_in(root, "test_fails.py", *recording)
    # The plugin stops a run at its first failure: pytest's status for a run interrupted.
    assert completed.returncode == pytest.ExitCode.INTERRUPTED, completed.stdout[-3000:]
    assert not (storage / "examples").exists()


def test_every_cut_made_is_applied_and_a_draw_it_cannot_cut_is_listed_uncut_never_held(
    tmp_path: Path,
) -> None:
    root = tree(tmp_path, {"test_everything.py": EVERYTHING})
    status, report, output = check(root, "run", "test_everything.py")
    assert report["uncut"] == UNCUT
    for name, cut in report["cuts"].items():
        assert cut["result"] == "not held", (name, cut)
        assert cut["effects"]["applied"] > 0, (name, cut)
    changes = {cut["change"] for cut in report["cuts"].values()}
    assert changes == {"drop", *input_coverage.DESCRIBED}
    helper = "tests/test_everything.py::helper::st.sampled_from(['p', 'q'])"
    assert {
        f"tests/test_everything.py::everything > {helper}",
        f"tests/test_everything.py::other > {helper}",
    } <= set(report["sites"])
    # Two integers: keeping off an end is pinning to the other, so pins alone.
    pair = "tests/test_everything.py::everything::st.integers(0, 1)"
    assert sorted(name for name in report["cuts"] if name.startswith(pair + " ::")) == [
        f"{pair} :: pin to the high end",
        f"{pair} :: pin to the low end",
    ]
    assert status == 1
    for site, why in UNCUT.items():
        assert f"uncut ({why}), and not in the baseline: {site}" in output
    listed = {
        "cuts": {
            name: {"result": "not held", "reason": "equivalent: no test reads it"} for name in report["cuts"]
        },
        "uncut": dict.fromkeys(UNCUT, "no test reads it"),
    }
    status, _, output = check(root, "check", "test_everything.py", listed)
    assert status == 0, output


def test_a_cut_that_leaves_nothing_to_draw_or_no_valid_example_is_reported_as_that(tmp_path: Path) -> None:
    root = tree(tmp_path, {"test_empty.py": EMPTY_AND_INVALID})
    status, report, output = check(root, "run", "test_empty.py")
    found = results(report)
    assert found["drop 'only'"] == "empty"
    assert found["pin to the low end"] == "invalid"
    assert "held" not in found.values()
    assert status == 1
    assert "empty, and not in the baseline" in output
    assert "invalid, and not in the baseline" in output


def test_a_site_keeps_its_name_when_lines_around_it_move(tmp_path: Path) -> None:
    first = tree(tmp_path / "first", {"test_holds.py": HOLDS_A})
    _, report, _ = check(first, "list", "test_holds.py")
    moved = HOLDS_A.replace(
        "@st.composite", "LINES = [\n    1,\n    2,\n]\n\n\ndef unrelated():\n    pass\n\n\n@st.composite"
    )
    second = tree(tmp_path / "second", {"test_holds.py": moved})
    _, again, _ = check(second, "list", "test_holds.py")
    assert (
        set(again["cuts"])
        == set(report["cuts"])
        == {
            "tests/test_holds.py::drawn::st.sampled_from(['a', 'b']) :: drop 'a'",
            "tests/test_holds.py::drawn::st.sampled_from(['a', 'b']) :: drop 'b'",
        }
    )


def seen(kind: str, **tables: dict[str, int]) -> dict[str, Any]:
    return {
        "kind": kind,
        "contexts": ["draw"],
        "calls": 1,
        **{t: tables.get(t, {}) for t in ("keys", "lone", "ends", "sizes")},
    }


@pytest.mark.parametrize(
    ("recorded", "changes", "uncut"),
    [
        (
            seen("sampled_from", keys={"'a'": 2, "'b'": 1}, lone={"'c'": 3}),
            [("drop", "'a'", False), ("drop", "'b'", False), ("drop", "'c'", True)],
            None,
        ),
        (
            seen("booleans", keys={"True": 1, "False": 1}),
            [("drop", "False", False), ("drop", "True", False)],
            None,
        ),
        (seen("one_of", keys={f"#{n}": 1 for n in range(25)}), [], "computed values: 25 across its calls"),
        (
            seen("integers", ends={"low": 2, "high": 2, "pair": 2}),
            [("pin_low", None, False), ("pin_high", None, False)],
            None,
        ),
        (
            seen("integers", ends={"low": 2, "high": 2, "pair": 1}),
            [
                ("pin_low", None, False),
                ("off_low", None, False),
                ("pin_high", None, False),
                ("off_high", None, False),
            ],
            None,
        ),
        (seen("floats", ends={"low": 1}), [("pin_low", None, False), ("off_low", None, False)], None),
        (seen("floats", ends={"unbounded": 1}), [], "unbounded"),
        (seen("integers"), [], None),
        (seen("lists", sizes={"least": 1}), [("least_size", None, False)], None),
        (
            seen("dictionaries", sizes={"least": 1, "greatest": 1}),
            [("least_size", None, False), ("greatest_size", None, False)],
            None,
        ),
        (seen("permutations", keys={"order": 1}), [("identity_order", None, False)], None),
        (seen("permutations"), [], None),
        (seen("builds"), [], "builds"),
    ],
)
def test_the_cuts_of_a_site(
    recorded: dict[str, Any], changes: list[tuple[str, str | None, bool]], uncut: str | None
) -> None:
    cuts, why = cuts_of("a site", recorded)
    assert [(cut["change"], cut["key"], cut.get("empty", False)) for cut in cuts] == changes
    assert why == uncut


EFFECTS = {"applied": 3, "unchanged": 1, "empty": 0}
FAILED = {"test": "t", "message": "AssertionError: no", "invalid": False}
INVALID = {"test": "u", "message": "Unsatisfiable", "invalid": True}


@pytest.mark.parametrize(
    ("outcome", "effects", "timed_out", "result"),
    [
        ({"finished": False, "failures": [INVALID, FAILED]}, EFFECTS, False, "held"),
        ({"finished": True, "failures": [FAILED]}, {**EFFECTS, "applied": 0}, False, "error"),
        ({"finished": True, "failures": []}, EFFECTS, False, "not held"),
        ({"finished": True, "failures": [INVALID]}, EFFECTS, False, "invalid"),
        ({"finished": True, "failures": []}, {"applied": 0, "unchanged": 4, "empty": 2}, False, "empty"),
        (
            {"finished": True, "failures": []},
            {"applied": 0, "unchanged": 4, "empty": 0},
            False,
            "not applied",
        ),
        ({"finished": True, "failures": []}, EFFECTS, True, "error"),
        (None, EFFECTS, False, "error"),
    ],
)
def test_a_cuts_result(
    outcome: dict[str, Any] | None, effects: dict[str, int], timed_out: bool, result: str
) -> None:
    assert result_of(outcome, effects, timed_out)["result"] == result


def a_report(**cuts: str) -> dict[str, Any]:
    named = {f"s :: {name}": {"site_id": "s", "result": result, "test": "t"} for name, result in cuts.items()}
    return {"sites": {"s": {}}, "cuts": named, "uncut": {"u": "text"}}


AGREED = {
    "cuts": {"s :: b": {"result": "not held", "reason": "a gap: nothing reads it"}},
    "uncut": {"u": "checked: a name no test reads"},
}


@pytest.mark.parametrize(
    ("report", "baseline", "found"),
    [
        (a_report(a="held", b="not held"), AGREED, []),
        (a_report(a="not held", b="not held"), AGREED, ["not held, and not in the baseline: s :: a"]),
        (a_report(a="held", b="held"), AGREED, ["now held, so the baseline drops it: s :: b (t)"]),
        (a_report(a="held", b="invalid"), AGREED, ["invalid, the baseline says not held: s :: b"]),
        (a_report(a="held"), AGREED, ["in the baseline, no longer cut: s :: b"]),
        (
            a_report(a="held", b="not held"),
            {**AGREED, "cuts": {"s :: b": {"result": "not held", "reason": "nothing reads it"}}},
            [
                "a baseline entry needs a result not held and a reason beginning "
                "('a gap: ', 'equivalent: '): s :: b"
            ],
        ),
        (
            a_report(a="held", b="not held"),
            {**AGREED, "uncut": {}},
            ["uncut (text), and not in the baseline: u"],
        ),
        (
            {**a_report(a="held", b="not held"), "uncut": {}},
            AGREED,
            ["in the baseline as uncut, no longer drawn uncut: u"],
        ),
        (
            {**a_report(a="held", b="not held"), "cuts": {"s :: b": {"site_id": "s"}}},
            AGREED,
            ["not run: s :: b"],
        ),
    ],
)
def test_the_baseline_lists_every_cut_not_held_and_only_shrinks(
    report: dict[str, Any], baseline: dict[str, Any], found: list[str]
) -> None:
    assert problems(report, baseline) == found


def test_the_baseline_names_tests_that_exist_and_gives_each_entry_its_reason() -> None:
    baseline = json.loads(input_coverage.BASELINE.read_text(encoding="utf-8"))
    assert baseline
    for name, selection in baseline.items():
        assert set(selection) == {"tests", "sites", "cuts", "uncut"}, name
        assert selection["tests"], name
        assert selection["sites"], name
        for test in selection["tests"]:
            assert (REPOSITORY / test.partition("::")[0]).is_file(), test
        for cut, entry in selection["cuts"].items():
            assert entry["result"] in input_coverage.RESULTS[1:], cut
            assert entry["reason"].startswith(input_coverage.REASONS), cut
        for site, note in selection["uncut"].items():
            assert note.strip(), site
