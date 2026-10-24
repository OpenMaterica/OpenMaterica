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
        draw(st.frozensets(st.integers(0, 9), min_size=1, max_size=3)),
        draw(st.dictionaries(st.sampled_from("xy"), st.booleans(), max_size=2)),
        draw(st.fixed_dictionaries({"a": st.just(1)}, optional={"b": st.just(2)})),
        draw(st.fixed_dictionaries({"c": st.just(3)})),
        draw(st.integers(2, 2)),
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

EVERY = "tests/test_everything.py::everything::"
UNCUT = {
    EVERY + "st.floats(min_value=0.0, exclude_min=True, allow_infinity=False)": "unbounded above",
    EVERY + "st.fixed_dictionaries({'a': st.just(1)}, optional={'b': st.just(2)})": "optional keys",
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


# Hypothesis's own defaults, whatever the machine's environment: where any variable of its table of CI
# variables is set (`CI`, `GITHUB_ACTIONS` on GitHub's runners...), Hypothesis loads its built-in `ci` profile
# (derandomized, no example database), which the controls must not rest on. The repository's conftest does
# the same for its profiles.
FIXTURE_CONFTEST = """
from hypothesis import settings

settings.register_profile("fixture", parent=settings.get_profile("default"))
settings.load_profile("fixture")
"""


def tree(root: Path, modules: dict[str, str]) -> Path:
    (root / "tests" / "property").mkdir(parents=True)
    # The tree's own root for pytest, whatever lies above it.
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (root / "tests" / "conftest.py").write_text(FIXTURE_CONFTEST, encoding="utf-8")
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


def pytest_in(root: Path, module: str, *options: str) -> tuple[Path, "subprocess.CompletedProcess[str]"]:
    """pytest run on one module of the tree, Hypothesis's storage (its example database among it) in a
    directory of its own, which it returns, with every test case observed there."""
    storage = root / f"storage-{len(list(root.glob('storage-*')))}"
    environment = {
        **os.environ,
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
    assert kinds >= {"frozensets", "dictionaries", "permutations", "text", "randoms", "fixed_dictionaries"}
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
        f"tests/test_everything.py::everything > helper(draw) > {helper}",
        f"tests/test_everything.py::other > helper(draw) > {helper}",
    } <= set(report["sites"])
    # A range of one value has no end to move, and a dictionary with no optional key draws nothing of its own.
    assert not [name for name in report["cuts"] if "st.integers(2, 2)" in name or "{'c'" in name]
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


def test_a_pattern_beginning_with_an_exclamation_mark_leaves_out_what_it_matches(tmp_path: Path) -> None:
    root = tree(tmp_path, {"test_everything.py": EVERYTHING})
    helper = "tests/test_everything.py::helper::st.sampled_from(['p', 'q'])"
    everything, other = (f"tests/test_everything.py::{owner} > helper(draw) > {helper}" for owner in OWNERS)
    _, report, _ = check(root, "list", "test_everything.py")
    # The control: both owners' draws of the helper are taken by the selection's pattern alone.
    assert {everything, other} <= set(report["sites"])
    sites = ["tests/test_everything.py::*", "!* > tests/test_everything.py::helper::*", "*::other > *"]
    _, narrowed, output = check(root, "list", "test_everything.py", {"sites": sites}, report="narrowed.json")
    assert other in narrowed["sites"], output
    assert everything not in narrowed["sites"]
    assert not [name for name in narrowed["cuts"] if name.startswith(everything)]
    assert set(narrowed["sites"]) == set(report["sites"]) - {everything}
    assert narrowed["uncut"] == report["uncut"]


OWNERS = ("everything", "other")


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
            seen("one_of", keys={f"#{n}": 1 for n in range(24)}),
            [("drop", key, False) for key in sorted(f"#{n}" for n in range(24))],
            None,
        ),
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
        (
            seen("floats", ends={"low": 1, "no high": 1}),
            [("pin_low", None, False), ("off_low", None, False)],
            "unbounded above",
        ),
        (
            seen("integers", ends={"high": 1, "no low": 1, "unbounded": 1}),
            [("pin_high", None, False), ("off_high", None, False)],
            "unbounded below and above",
        ),
        (seen("floats", ends={"unbounded": 1}), [], "unbounded"),
        (seen("integers"), [], None),
        (seen("lists", sizes={"least": 1}), [("least_size", None, False), ("off_least", None, False)], None),
        (
            seen("dictionaries", sizes={"least": 1, "greatest": 1}),
            [
                ("least_size", None, False),
                ("off_least", None, False),
                ("greatest_size", None, False),
                ("off_greatest", None, False),
            ],
            None,
        ),
        (
            seen("sets", sizes={"least": 2, "greatest": 2, "pair": 2}),
            [("least_size", None, False), ("greatest_size", None, False)],
            None,
        ),
        (seen("permutations", keys={"order": 1}), [("identity_order", None, False)], None),
        (seen("permutations"), [], None),
        (seen("builds"), [], "builds"),
        (seen("fixed_dictionaries"), [], "optional keys"),
    ],
)
def test_the_cuts_of_a_site(
    recorded: dict[str, Any], changes: list[tuple[str, str | None, bool]], uncut: str | None
) -> None:
    cuts, why = cuts_of("a site", recorded)
    assert [(cut["change"], cut["key"], cut.get("empty", False)) for cut in cuts] == changes
    assert why == uncut


EFFECTS = {
    "gw0": {"applied": 3, "unchanged": 1, "empty": 0},
    "gw1": {"applied": 0, "unchanged": 2, "empty": 0},
}
FAILED = {"test": "t", "message": "AssertionError: no", "invalid": False, "process": "gw0"}
ELSEWHERE = {**FAILED, "process": "gw1"}
INVALID = {"test": "u", "message": "Unsatisfiable", "invalid": True, "process": "gw0"}
NONE_APPLIED = {"gw0": {"applied": 0, "unchanged": 4, "empty": 0}}


@pytest.mark.parametrize(
    ("outcome", "effects", "timed_out", "result"),
    [
        ({"finished": False, "failures": [INVALID, FAILED]}, EFFECTS, False, "held"),
        ({"finished": True, "failures": [FAILED]}, NONE_APPLIED, False, "error"),
        # A failure in a worker that never applied the cut is not the cut's.
        ({"finished": False, "failures": [ELSEWHERE]}, EFFECTS, False, "error"),
        ({"finished": True, "failures": []}, EFFECTS, False, "not held"),
        ({"finished": True, "failures": [INVALID]}, EFFECTS, False, "invalid"),
        (
            {"finished": True, "failures": []},
            {"gw0": {"applied": 0, "unchanged": 4, "empty": 2}},
            False,
            "empty",
        ),
        ({"finished": True, "failures": []}, NONE_APPLIED, False, "not applied"),
        ({"finished": True, "failures": []}, EFFECTS, True, "error"),
        (None, EFFECTS, False, "error"),
    ],
)
def test_a_cuts_result(
    outcome: dict[str, Any] | None, effects: dict[str, dict[str, int]], timed_out: bool, result: str
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
        (
            a_report(a="held", b="not held"),
            {**AGREED, "uncut": {"u": " "}},
            ["an uncut site needs a person's note: u"],
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
        assert set(selection) == {"tests", "sites", "excused", "cuts", "uncut"}, name
        assert selection["tests"], name
        assert selection["sites"], name
        for test in [*selection["tests"], *selection["excused"]]:
            assert (REPOSITORY / test.partition("::")[0]).is_file(), test
        for test, note in selection["excused"].items():
            assert note.strip(), test
        for cut, entry in selection["cuts"].items():
            assert entry["result"] in input_coverage.RESULTS[1:], cut
            assert entry["reason"].startswith(input_coverage.REASONS), cut
        for site, note in selection["uncut"].items():
            assert note.strip(), site


# Each value a cut takes away is needed by one test alone, so that each cut is held at the test that needs
# what it removes: a cut that removes another value, or none, fails elsewhere or nowhere.
KILLS = (
    HEADER
    + """
import math

FIND = settings(derandomize=True, database=None, max_examples=200, deadline=None)
NEAR_ZERO = math.nextafter(0.0, math.inf)
NEAR_ONE = math.nextafter(1.0, -math.inf)


class Way:
    def __init__(self, number):
        self.number = number


# Two values whose names, without an address, are alike.
WAYS = [Way(1), Way(2), "plain"]


@st.composite
def number(draw):
    return draw(st.integers(0, 3))


@st.composite
def truth(draw):
    return draw(st.booleans())


@st.composite
def order(draw):
    return draw(st.permutations([1, 2, 3]))


@st.composite
def items(draw):
    return draw(st.lists(st.just("a"), max_size=3))


@st.composite
def fraction(draw):
    return draw(st.floats(0.0, 1.0, exclude_min=True, exclude_max=True))


@st.composite
def way(draw):
    return draw(st.sampled_from(WAYS))


def flag(draw):
    return draw(st.sampled_from(["on", "off"]))


@st.composite
def left(draw):
    return flag(draw)


@st.composite
def right(draw):
    return flag(draw)


@st.composite
def pair(draw):
    return flag(draw), flag(draw)


@st.composite
def level(draw):
    return draw(st.sampled_from(["up", "down"]))


@st.composite
def low(draw):
    return draw(level())


@st.composite
def high(draw):
    return draw(level())


@st.composite
def side(draw):
    return draw(st.sampled_from(["east", "west"]))


@DERANDOMIZED
@given(number(), truth(), order(), items(), fraction(), way(), left(), right(), pair(), low(), high())
def test_drawn(a, b, c, d, e, f, g, h, i, j, k):
    pass


def test_number_zero():
    find(number(), lambda example: example == 0, settings=FIND)


def test_number_three():
    find(number(), lambda example: example == 3, settings=FIND)


def test_truth_true():
    find(truth(), lambda example: example is True, settings=FIND)


def test_truth_false():
    find(truth(), lambda example: example is False, settings=FIND)


def test_another_order():
    find(order(), lambda example: example != [1, 2, 3], settings=FIND)


def test_no_items():
    find(items(), lambda example: len(example) == 0, settings=FIND)


def test_three_items():
    find(items(), lambda example: len(example) == 3, settings=FIND)


def test_fraction_near_zero():
    find(fraction(), lambda example: example == NEAR_ZERO, settings=FIND)


def test_fraction_near_one():
    find(fraction(), lambda example: example == NEAR_ONE, settings=FIND)


def test_way_two():
    find(way(), lambda example: isinstance(example, Way) and example.number == 2, settings=FIND)


def test_right_off():
    find(right(), lambda example: example == "off", settings=FIND)


def test_second_off():
    find(pair(), lambda example: example[1] == "off", settings=FIND)


def test_high_down():
    find(high(), lambda example: example == "down", settings=FIND)


@DERANDOMIZED
@given(st.data())
def test_side_east(data):
    assert "east" in [data.draw(side()) for _ in range(20)]


def test_side_west():
    find(side(), lambda example: example == "west", settings=FIND)
"""
)
FLAG = "tests/test_kills.py::flag::st.sampled_from(['on', 'off'])"
LEVEL = "tests/test_kills.py::level::st.sampled_from(['up', 'down'])"
FRACTION = "fraction::st.floats(0.0, 1.0, exclude_min=True, exclude_max=True)"
# Each cut, after `tests/test_kills.py::`, and the test that holds it (None: no test does).
KILLED_AT = {
    "number::st.integers(0, 3) :: pin to the low end": "test_number_three",
    "number::st.integers(0, 3) :: keep off the low end": "test_number_zero",
    "number::st.integers(0, 3) :: pin to the high end": "test_number_zero",
    "number::st.integers(0, 3) :: keep off the high end": "test_number_three",
    "truth::st.booleans() :: drop True": "test_truth_true",
    "truth::st.booleans() :: drop False": "test_truth_false",
    "order::st.permutations([1, 2, 3]) :: hold to the order given": "test_another_order",
    "items::st.lists(st.just('a'), max_size=3) :: hold to the least size": "test_three_items",
    "items::st.lists(st.just('a'), max_size=3) :: keep off the least size": "test_no_items",
    "items::st.lists(st.just('a'), max_size=3) :: hold to the greatest size": "test_no_items",
    "items::st.lists(st.just('a'), max_size=3) :: keep off the greatest size": "test_three_items",
    # The excluded ends' neighbours are the range's ends.
    f"{FRACTION} :: pin to the low end": "test_fraction_near_one",
    f"{FRACTION} :: keep off the low end": "test_fraction_near_zero",
    f"{FRACTION} :: pin to the high end": "test_fraction_near_zero",
    f"{FRACTION} :: keep off the high end": "test_fraction_near_one",
    # Two values named alike are told apart by their places, and cut one at a time.
    "way::st.sampled_from(WAYS) :: drop <tests.test_kills.Way object> #0": None,
    "way::st.sampled_from(WAYS) :: drop <tests.test_kills.Way object> #1": "test_way_two",
    "way::st.sampled_from(WAYS) :: drop 'plain'": None,
    # One helper's draw, cut for one owner alone, and for one of two calls from one owner alone.
    f"left > flag(draw) > {FLAG} :: drop 'on'": None,
    f"left > flag(draw) > {FLAG} :: drop 'off'": None,
    f"right > flag(draw) > {FLAG} :: drop 'on'": None,
    f"right > flag(draw) > {FLAG} :: drop 'off'": "test_right_off",
    f"pair > flag(draw) > {FLAG} :: drop 'on'": None,
    f"pair > flag(draw) > {FLAG} :: drop 'off'": None,
    f"pair > flag(draw)#2 > {FLAG} :: drop 'on'": None,
    f"pair > flag(draw)#2 > {FLAG} :: drop 'off'": "test_second_off",
    # One composite drawn by two others, cut for one drawer alone.
    f"low > draw(level()) > {LEVEL} :: drop 'up'": None,
    f"low > draw(level()) > {LEVEL} :: drop 'down'": None,
    f"high > draw(level()) > {LEVEL} :: drop 'up'": None,
    f"high > draw(level()) > {LEVEL} :: drop 'down'": "test_high_down",
    # A composite drawn in two tests, under `data.draw` and under `find`, which run in no draw: one site,
    # named after the composite, whose cuts reach both tests.
    "side::st.sampled_from(['east', 'west']) :: drop 'east'": "test_side_east",
    "side::st.sampled_from(['east', 'west']) :: drop 'west'": "test_side_west",
}


def test_each_cut_takes_away_what_it_names_and_is_held_by_the_test_that_needs_that(tmp_path: Path) -> None:
    root = tree(tmp_path, {"test_kills.py": KILLS})
    _, report, output = check(root, "run", "test_kills.py")
    found = {
        name.removeprefix("tests/test_kills.py::"): (
            cut["result"],
            cut.get("test", "").removeprefix("tests/test_kills.py::") or None,
        )
        for name, cut in report["cuts"].items()
    }
    expected = {
        name: ("not held", None) if test is None else ("held", test) for name, test in KILLED_AT.items()
    }
    assert found == expected, output


FAILS_WITH_NO_CUT = (
    HEADER
    + """

@st.composite
def drawn(draw):
    return draw(st.sampled_from(["a", "b"]))


@DERANDOMIZED
@given(drawn())
def test_drawn(example):
    pass


def test_always_fails():
    assert False, "fails with no cut"
"""
)


@pytest.mark.parametrize("command", ["list", "run"])
def test_a_selection_that_fails_with_no_cut_is_refused_and_its_failure_printed(
    tmp_path: Path, command: str
) -> None:
    root = tree(tmp_path, {"test_fails.py": FAILS_WITH_NO_CUT})
    with pytest.raises(FileNotFoundError):
        check(root, command, "test_fails.py")
    completed = subprocess.run(
        [
            *(sys.executable, str(REPOSITORY / "scripts" / "input_coverage.py"), command, "fixture"),
            *("--baseline", str(root / "baseline.json"), "--root", str(root), "--workers", "0"),
            *("--report", str(root / "again.json"), "--timeout", "120"),
        ],
        capture_output=True,
        text=True,
        cwd=root,
        timeout=600,
        check=False,
    )
    assert completed.returncode == 1, completed.stdout
    assert "the selection fails with no cut" in completed.stdout
    assert "failed: tests/test_fails.py::test_always_fails (call): AssertionError: fails with no cut" in (
        completed.stdout
    )
    assert not (root / "again.json").exists()


def test_a_report_of_another_selection_or_profile_is_refused(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    given = {"name": None, "tests": ["tests/a.py"], "sites": ["*"]}
    report.write_text(json.dumps({"selection": given, "profile": "dev"}), encoding="utf-8")
    arguments = ["check", "--tests", "tests/a.py", "--sites", "*", "--report", str(report)]
    with pytest.raises(SystemExit, match="another selection or profile"):
        input_coverage.main(arguments)
    with pytest.raises(SystemExit, match="another selection or profile"):
        input_coverage.main(["check", "--tests", "tests/a.py", "--sites", "tests/*", "--report", str(report)])


def test_every_test_module_importing_a_selections_strategies_is_named_or_excused() -> None:
    baseline = json.loads(input_coverage.BASELINE.read_text(encoding="utf-8"))
    for name, selection in baseline.items():
        assert input_coverage.importers_not_listed(REPOSITORY, selection) == [], name


def test_a_module_importing_the_strategies_that_a_selection_does_not_list_is_found(tmp_path: Path) -> None:
    (tmp_path / "tests" / "property").mkdir(parents=True)
    modules = {
        "drawn_strategies.py": "import hypothesis\n",
        "test_named.py": "from tests.property.drawn_strategies import WAYS\n",
        "test_by_module.py": "from tests.property import drawn_strategies\n",
        "test_relative.py": "from .drawn_strategies import WAYS\n",
        "test_dotted.py": "import tests.property.drawn_strategies as drawn\n",
        "test_unrelated.py": "from tests.property import other_strategies\n",
    }
    for module, source in modules.items():
        (tmp_path / "tests" / "property" / module).write_text(source, encoding="utf-8")
    selection = {
        "tests": ["tests/property/test_named.py::test_one"],
        "sites": ["tests/property/drawn_strategies.py::*"],
    }
    assert input_coverage.importers_not_listed(tmp_path, selection) == [
        "tests/property/test_by_module.py",
        "tests/property/test_dotted.py",
        "tests/property/test_relative.py",
    ]
    excused = dict.fromkeys(
        (f"tests/property/test_{name}.py" for name in ("by_module", "dotted", "relative")), "draws nothing"
    )
    assert input_coverage.importers_not_listed(tmp_path, {**selection, "excused": excused}) == []
