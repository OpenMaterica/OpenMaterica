# SPDX-License-Identifier: Apache-2.0
"""`scripts/gen_kill_counts.py`: the README's kill counts are the recorded kill points, the recorded kill
points are a run's, and a kill after the 500th example fails the margin guard. Each check is shown failing."""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from scripts import gen_kill_counts
from scripts.gen_kill_counts import CountsError, KillPoints, Record
from tests.property import support

REAL_INPUTS = gen_kill_counts.inputs_of_tree
REAL_NO_TABLE = gen_kill_counts.NO_TABLE

GROUP = "test_x_mutants.py::test_the_mutant_is_killed"
OTHER = "test_y_mutants.py::test_the_other_is_killed"
SUMMARY = (
    "<!-- kill points summary (scripts/gen_kill_counts.py) -->\nwhatever was here\n"
    "<!-- end of kill points summary -->"
)


def readme(*rows: str, extent: str = "every search", group: str = GROUP) -> str:
    table = "\n".join(("| Mutant | Fault, with a `\\|` | Examples |", "|---|---|---|", *rows))
    marker = f"<!-- kill points of {extent} of {group} (scripts/gen_kill_counts.py) -->"
    return f"# Mutants\n\n{SUMMARY}\n\n{marker}\n{table}\n\nAfter.\n"


HELPER = "tests/property/test_x_mutants.py::kill"
INPUTS = {"hypothesis": "1.2.3", HELPER: "aaaaaaaaaaaa"}
SEEDED_BY: dict[str, str] = {}  # the tree's inputs, as a test sets them: it starts as INPUTS


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A README, a kill points file and inputs of their own, where the script looks for the repository's:
    the group `OTHER` has no table, and the installed Hypothesis is the recorded one."""
    monkeypatch.setattr(gen_kill_counts, "README", tmp_path / "README.md")
    monkeypatch.setattr(gen_kill_counts, "KILL_POINTS", tmp_path / "kill_points.json")
    monkeypatch.setattr(gen_kill_counts, "NO_TABLE", frozenset({OTHER}))
    SEEDED_BY.clear()
    SEEDED_BY.update(INPUTS)
    monkeypatch.setattr(gen_kill_counts, "inputs_of_tree", lambda: dict(SEEDED_BY))
    monkeypatch.setattr(gen_kill_counts, "installed_hypothesis", lambda: SEEDED_BY["hypothesis"])
    return tmp_path


def holding(tree: Path, recorded: KillPoints, text: str, inputs: dict[str, str] | None = None) -> None:
    record = Record(INPUTS if inputs is None else inputs, recorded)
    (tree / "kill_points.json").write_text(gen_kill_counts.dump(record), encoding="utf-8")
    (tree / "README.md").write_text(text, encoding="utf-8")


def report(tree: Path, *cases: tuple[str, str, int | None], name: str = "report.xml") -> Path:
    """A JUnit report as pytest writes it, one test case per (module, test id, kill); None, a case without
    `examples_to_kill`, as a test that failed; -1, one that passed without recording one."""
    written: list[str] = []
    for module, test_id, kill in cases:
        recorded = (
            ""
            if kill == -1
            else f'<properties><property name="examples_to_kill" value="{kill}" /></properties>'
            if kill is not None
            else "<failure>the mutant survived 2000 examples</failure>"
        )
        written.append(
            f'<testcase classname="tests.property.{module}" name="{test_id}">{recorded}</testcase>'
        )
    path = tree / name
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest">'
        + "".join(written)
        + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    return path


def both(module: str, function: str, mutant: str, small: int, original: int) -> list[tuple[str, str, int]]:
    return [
        (module, f"{function}[{mutant}-small]", small),
        (module, f"{function}[{mutant}-original]", original),
    ]


# --- the file -----------------------------------------------------------------------------------------------


def test_the_file_is_written_in_one_layout_and_read_back() -> None:
    recorded: KillPoints = {OTHER: {"b": (3, 1_500)}, GROUP: {"z": (2, 2), "a": (1, 10)}}
    record = Record({"hypothesis": "1.2.3", HELPER: "aaaaaaaaaaaa", "a": "b"}, recorded)
    text = gen_kill_counts.dump(record)
    assert text == textwrap.dedent(
        """\
        {
          "inputs": {
            "a": "b",
            "hypothesis": "1.2.3",
            "tests/property/test_x_mutants.py::kill": "aaaaaaaaaaaa"
          },
          "kills": {
            "test_x_mutants.py::test_the_mutant_is_killed": {
              "a": [1, 10],
              "z": [2, 2]
            },
            "test_y_mutants.py::test_the_other_is_killed": {
              "b": [3, 1500]
            }
          }
        }
        """
    )
    assert gen_kill_counts.load(text) == record


def file_of(inputs: str, kills: str) -> str:
    return f'{{"inputs": {inputs}, "kills": {kills}}}'


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        '{"test_x.py::test_y": {"a": [1, 1]}}',  # the old layout: no inputs
        file_of('{"hypothesis": "1"}', "[]"),
        file_of("{}", "{}"),  # no input at all: the file would record nothing it depends on
        file_of('{"hypothesis": 1}', "{}"),
        file_of('{"hypothesis": "1"}', '{"not a group": {"a": [1, 1]}}'),
        file_of('{"hypothesis": "1"}', '{"test_x.py::test_y": {}}'),
        file_of('{"hypothesis": "1"}', '{"test_x.py::test_y": {"a": [1]}}'),
        file_of('{"hypothesis": "1"}', '{"test_x.py::test_y": {"a": [0, 1]}}'),
        file_of('{"hypothesis": "1"}', '{"test_x.py::test_y": {"a": [1, true]}}'),
        file_of('{"hypothesis": "1"}', '{"test_x.py::test_y": {"a": [1, 2.0]}}'),
        file_of('{"hypothesis": "1"}', '{"test_x.py::test_y": {"a": "1, 1"}}'),
        "{",
    ],
)
def test_a_file_that_is_not_kill_points_is_refused(text: str) -> None:
    with pytest.raises(CountsError):
        gen_kill_counts.load(text)


# --- JUnit reports ------------------------------------------------------------------------------------------


def test_a_reports_kills_are_read_by_group_mutant_and_size(tree: Path) -> None:
    path = report(
        tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", 4, 9),
        ("test_x_mutants", "test_the_mutant_is_killed[b-small]", None),  # failed: no kill recorded
        ("test_x_mutants", "test_the_mutant_is_killed[odd-name-with-dashes-original]", 7),
    )
    assert gen_kill_counts.reported([path]) == gen_kill_counts.Report(
        {GROUP: {"a": {"small": 4, "original": 9}, "odd-name-with-dashes": {"original": 7}}}
    )


@pytest.mark.parametrize(
    ("module", "test_id"),
    [
        ("test_x_mutants", "test_the_mutant_is_killed[a]"),  # no size
        ("test_x_mutants", "test_the_mutant_is_killed"),
        ("unit.test_x", "test_the_mutant_is_killed[a-small]"),  # not a module of tests/property itself
    ],
)
def test_a_kill_that_is_no_search_at_a_size_is_refused(tree: Path, module: str, test_id: str) -> None:
    path = report(tree, (module, test_id, 3))
    with pytest.raises(CountsError):
        gen_kill_counts.reported([path])


def test_a_search_killed_at_two_examples_or_at_one_size_alone_is_refused(tree: Path) -> None:
    first = report(tree, ("test_x_mutants", "test_the_mutant_is_killed[a-small]", 3), name="one.xml")
    second = report(tree, ("test_x_mutants", "test_the_mutant_is_killed[a-small]", 4), name="two.xml")
    with pytest.raises(CountsError, match="two examples"):
        gen_kill_counts.reported([first, second])
    with pytest.raises(CountsError, match="original size"):
        gen_kill_counts.recorded_from(gen_kill_counts.reported([first]).kills)


# The kill points a partial report would drop: GROUP's `gone` and all of OTHER.
PARTLY_RECORDED: KillPoints = {GROUP: {"a": (1, 1), "gone": (5, 5)}, OTHER: {"b": (2, 2)}}


def of_group(mutant: str, small: int, original: int) -> list[tuple[str, str, int]]:
    return both("test_x_mutants", "test_the_mutant_is_killed", mutant, small, original)


def of_other(mutant: str, small: int, original: int) -> list[tuple[str, str, int]]:
    return both("test_y_mutants", "test_the_other_is_killed", mutant, small, original)


def test_recording_a_report_that_covers_every_recorded_group_replaces_them_and_adds_what_is_new(
    tree: Path,
) -> None:
    holding(
        tree, PARTLY_RECORDED, readme("| `a` | x | 0, 0 |", "| `gone` | y | 0, 0 |", "| `new` | z | 0, 0 |")
    )
    path = report(
        tree, *of_group("a", 6, 8), *of_group("gone", 7, 9), *of_group("new", 1, 3), *of_other("b", 4, 4)
    )
    assert gen_kill_counts.main(["--record", str(path)]) == 0
    assert gen_kill_counts.load(kept(tree)).kills == {
        GROUP: {"a": (6, 8), "gone": (7, 9), "new": (1, 3)},
        OTHER: {"b": (4, 4)},
    }
    assert "| `new` | z | 1, 3 |" in (tree / "README.md").read_text()


@pytest.mark.parametrize(
    ("cases", "lacked"),
    [
        (
            of_group("a", 6, 8),
            [
                f"{GROUP}: the reports hold no kill of 1 of its 2 recorded mutants: `gone`",
                f"{OTHER}: the reports hold no search of it",
            ],
        ),
        (
            [*of_group("a", 6, 8), *of_other("b", 4, 4)],
            [f"{GROUP}: the reports hold no kill of 1 of its 2 recorded mutants: `gone`"],
        ),
        (
            [*of_group("a", 6, 8), *of_group("gone", 7, 9)],
            [f"{OTHER}: the reports hold no search of it"],
        ),
    ],
    ids=["part-of-a-group-and-no-other", "part-of-a-group", "a-group-left-out"],
)
def test_recording_a_report_that_lacks_a_recorded_search_is_refused_naming_each_group_it_lacks(
    tree: Path, capsys: pytest.CaptureFixture[str], cases: list[tuple[str, str, int]], lacked: list[str]
) -> None:
    holding(tree, PARTLY_RECORDED, readme("| `a` | x | 1, 1 |", "| `gone` | y | 5, 5 |"))
    before = kept(tree), (tree / "README.md").read_text()
    assert gen_kill_counts.main(["--record", str(report(tree, *cases))]) == 2
    said = capsys.readouterr().err
    named = [line.strip() for line in said.splitlines()[1:]]
    assert named == lacked
    assert "do not cover every recorded group" in said
    assert "--measure --record" in said
    assert (kept(tree), (tree / "README.md").read_text()) == before  # nothing was written


def test_without_the_cover_check_a_report_of_part_of_a_group_drops_the_rest_of_its_kill_points(
    tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control of the refusal above: with the check gone, as before it, a report of `a` alone records,
    and the kill points of `gone`, which nothing about changed, are lost."""
    holding(tree, PARTLY_RECORDED, readme("| `a` | x | 1, 1 |"))

    def covering_all(kills: object, recorded: object, groups: object) -> list[str]:
        return []

    monkeypatch.setattr(gen_kill_counts, "uncovered", covering_all)
    path = report(tree, *of_group("a", 6, 8), *of_other("b", 2, 2))
    assert gen_kill_counts.main(["--record", str(path)]) == 0
    assert gen_kill_counts.load(kept(tree)).kills[GROUP] == {"a": (6, 8)}


def test_a_group_named_with_group_is_recorded_alone_and_the_others_kept(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holding(tree, PARTLY_RECORDED, readme("| `a` | x | 1, 1 |", "| `gone` | y | 5, 5 |"))
    path = report(tree, *of_group("a", 6, 8), *of_group("gone", 7, 9), *of_other("b", 4, 4))
    assert gen_kill_counts.main(["--record", str(path), "--group", GROUP]) == 0
    assert gen_kill_counts.load(kept(tree)).kills == {
        GROUP: {"a": (6, 8), "gone": (7, 9)},
        OTHER: {"b": (2, 2)},
    }
    assert f"left {OTHER} as recorded" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("cases", "lacked"),
    [
        (
            [*of_group("a", 6, 8), *of_other("b", 4, 4)],
            f"{GROUP}: the reports hold no kill of 1 of its 2 recorded mutants: `gone`",
        ),
        (of_other("b", 4, 4), f"{GROUP}: the reports hold no search of it"),
    ],
    ids=["part-of-the-group", "none-of-it"],
)
def test_a_group_named_with_group_that_the_reports_do_not_cover_is_refused(
    tree: Path, capsys: pytest.CaptureFixture[str], cases: list[tuple[str, str, int]], lacked: str
) -> None:
    holding(tree, PARTLY_RECORDED, readme("| `a` | x | 1, 1 |", "| `gone` | y | 5, 5 |"))
    before = kept(tree)
    assert gen_kill_counts.main(["--record", str(report(tree, *cases)), "--group", GROUP]) == 2
    said = capsys.readouterr().err
    assert "do not cover the groups --group names" in said
    assert [line.strip() for line in said.splitlines()[1:]] == [lacked]
    assert kept(tree) == before


# --- the README ---------------------------------------------------------------------------------------------


def test_the_counts_and_the_summary_are_written_and_the_rest_left_as_it_was(tree: Path) -> None:
    holding(
        tree,
        {GROUP: {"a": (1, 234), "b": (3, 4)}},
        readme("| `a` | x \\| y | 9, 9 |", "| `b` | z | anything |"),
    )
    assert gen_kill_counts.main([]) == 0
    written = (tree / "README.md").read_text()
    assert "| `a` | x \\| y | 1, 234 |" in written
    assert "| `b` | z | 3, 4 |" in written
    assert (
        "`kill_points.json` records 4 searches, 2 mutants each at both sizes; the latest kill is at the"
        " 234th example (`a`, original size)." in written
    )
    assert "whatever was here" not in written
    assert written.endswith("\n\nAfter.\n")
    assert gen_kill_counts.main(["--check"]) == 0


def test_a_count_is_written_with_its_thousands_separated() -> None:
    text, problems = gen_kill_counts.rendered(readme("| `a` | x | 0, 0 |"), {GROUP: {"a": (1, 1_234)}})
    assert problems == []
    assert "| `a` | x | 1, 1,234 |" in text
    assert "at the 1,234th example" in text


def test_a_count_edited_by_hand_fails_the_check(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |"))
    assert gen_kill_counts.main([]) == 0
    assert gen_kill_counts.main(["--check"]) == 0
    text = (tree / "README.md").read_text()
    (tree / "README.md").write_text(text.replace("| 1, 2 |", "| 1, 3 |"))
    assert gen_kill_counts.main(["--check"]) == 1
    assert "differ from kill_points.json" in capsys.readouterr().err


def test_a_file_out_of_its_layout_fails_the_check(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |"))
    assert gen_kill_counts.main([]) == 0
    (tree / "kill_points.json").write_text(
        '{"inputs": {"hypothesis": "1.2.3", "'
        + HELPER
        + '": "aaaaaaaaaaaa"}, "kills": {"test_x_mutants.py::test_the_mutant_is_killed": {"a": [1, 2]}}}\n'
    )
    assert gen_kill_counts.main(["--check"]) == 1
    assert "not in this script's layout" in capsys.readouterr().err


def test_a_table_of_every_search_without_a_recorded_mutants_row_fails(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    recorded: KillPoints = {GROUP: {"a": (1, 2), "b": (1, 1)}}
    holding(tree, recorded, readme("| `a` | x | 1, 2 |"))
    assert gen_kill_counts.main([]) == 1
    assert "`b` is recorded but has no row" in capsys.readouterr().err
    # control: a table of some searches may leave one out
    holding(tree, recorded, readme("| `a` | x | 1, 2 |", extent="some searches"))
    assert gen_kill_counts.main([]) == 0
    assert gen_kill_counts.main(["--check"]) == 0


def test_two_rows_of_one_mutant_or_a_table_of_a_group_not_recorded_fail(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |", "| `a` | y | 1, 2 |"))
    assert gen_kill_counts.main(["--check"]) == 1
    assert "`a` has two rows" in capsys.readouterr().err
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |", group=OTHER))
    assert gen_kill_counts.main(["--check"]) == 1
    assert "does not hold" in capsys.readouterr().err


def test_a_row_of_a_mutant_not_yet_recorded_passes_the_check_and_fails_against_the_run(tree: Path) -> None:
    """A stacked branch's older commits carry rows for mutants the file does not hold yet; the head is held to
    the run of every search, which ran the mutant and so finds it unrecorded."""
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |", "| `new` | y | 7, 7 |"))
    assert gen_kill_counts.main([]) == 0
    assert gen_kill_counts.main(["--check"]) == 0
    assert "| `new` | y | 7, 7 |" in (tree / "README.md").read_text()
    run = report(
        tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", 1, 2),
        *both("test_x_mutants", "test_the_mutant_is_killed", "new", 7, 7),
    )
    assert gen_kill_counts.main(["--against", str(run)]) == 1


@pytest.mark.parametrize(
    "text",
    [
        "<!-- kill points of all searches of test_x.py::test_y (scripts/gen_kill_counts.py) -->\n| a |\n",
        "<!-- kill points of every search of test_x.py::test_y (scripts/gen_kill_counts.py) -->\n\n| a |\n",
        "<!-- kill points of every search of test_x.py::test_y (scripts/gen_kill_counts.py) -->\n"
        "| M | E |\n|---|---|\n| `a`, `b` | 1, 1 |\n",
        "<!-- kill points of every search of test_x.py::test_y (scripts/gen_kill_counts.py) -->\n"
        "| M | E |\n|---|---|\n| a | 1, 1 |\n",
    ],
    ids=["an extent it does not know", "no table under it", "two mutants in a row", "no mutant in a row"],
)
def test_a_table_the_script_cannot_read_is_refused(text: str) -> None:
    with pytest.raises(CountsError):
        gen_kill_counts.tables(text.split("\n"))


@pytest.mark.parametrize("summary", ["", SUMMARY + "\n" + SUMMARY], ids=["none", "two"])
def test_a_readme_without_one_summary_is_refused(tree: Path, summary: str) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |").replace(SUMMARY, summary))
    assert gen_kill_counts.main(["--check"]) == 2


@pytest.mark.parametrize(
    ("number", "written"),
    [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (112, "112th"),
        (523, "523rd"),
        (1_001, "1,001st"),
    ],
)
def test_ordinals(number: int, written: str) -> None:
    assert gen_kill_counts.ordinal(number) == written


def test_the_summary_names_every_search_at_the_latest_kill() -> None:
    assert gen_kill_counts.summary({GROUP: {"b": (9, 3), "a": (2, 9)}, OTHER: {"c": (1, 1)}}).endswith(
        "the latest kill is at the 9th example (`a`, original size; `b`, small size)."
    )


# --- the margin guard ---------------------------------------------------------------------------------------


def test_the_margin_is_the_maintainers_500() -> None:
    assert gen_kill_counts.MARGIN == 500


@pytest.mark.parametrize(("small", "original"), [(501, 1), (1, 501), (2_000, 2_000)])
def test_a_kill_after_the_500th_example_fails_the_check_naming_it(
    tree: Path, capsys: pytest.CaptureFixture[str], small: int, original: int
) -> None:
    holding(
        tree,
        {GROUP: {"late": (small, original), "early": (1, 1)}},
        readme("| `late` | x | 0 |", "| `early` | y | 0 |"),
    )
    assert gen_kill_counts.main([]) == 0
    assert gen_kill_counts.main(["--check"]) == 1
    said = capsys.readouterr().err
    for size, kill in (("small", small), ("original", original)):
        named = (
            f"`late` dies at the {gen_kill_counts.ordinal(kill)} example at the {size} size, after the 500th"
        )
        assert (named in said) == (kill > 500)
    assert "`early`" not in said


def test_a_kill_at_the_500th_example_passes_the_guard(tree: Path) -> None:
    """The control of the guard's boundary: the 500th example is within the margin."""
    holding(tree, {GROUP: {"late": (500, 500)}}, readme("| `late` | x | 0 |"))
    assert gen_kill_counts.main([]) == 0
    assert gen_kill_counts.main(["--check"]) == 0


# --- against a run ------------------------------------------------------------------------------------------


def run_of_every_search(tree: Path, **changed: int) -> Path:
    small = changed.get("small", 1)
    return report(
        tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", small, 2),
        *both("test_x_mutants", "test_the_mutant_is_killed", "b", 3, 4),
        *both("test_y_mutants", "test_the_other_is_killed", "c", 5, 6),
    )


@pytest.fixture
def recorded_tree(tree: Path) -> Path:
    holding(
        tree,
        {GROUP: {"a": (1, 2), "b": (3, 4)}, OTHER: {"c": (5, 6)}},
        readme("| `a` | x | 1, 2 |", "| `b` | y | 3, 4 |"),
    )
    assert gen_kill_counts.main([]) == 0
    return tree


def test_a_run_that_gives_the_recorded_kills_passes(recorded_tree: Path) -> None:
    assert gen_kill_counts.main(["--against", str(run_of_every_search(recorded_tree))]) == 0


def test_a_kill_that_moved_fails_against_the_run_naming_it(
    recorded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert gen_kill_counts.main(["--against", str(run_of_every_search(recorded_tree, small=9))]) == 1
    said = capsys.readouterr().err
    assert "`a` at the small size: killed at 9, recorded 1" in said
    assert "--measure --record" in said


def test_a_recorded_search_the_run_holds_no_kill_of_fails(
    recorded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = report(
        recorded_tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", 1, 2),
        ("test_x_mutants", "test_the_mutant_is_killed[b-small]", None),
        ("test_x_mutants", "test_the_mutant_is_killed[b-original]", None),
    )
    assert gen_kill_counts.main(["--against", str(run)]) == 1
    said = capsys.readouterr().err
    assert "`b` is recorded, but the reports hold no kill of it" in said
    assert "names `b`, which did not run" in said


def test_a_recorded_search_the_run_killed_at_one_size_alone_fails(
    recorded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = report(
        recorded_tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", 1, 2),
        ("test_x_mutants", "test_the_mutant_is_killed[b-small]", 3),
        ("test_x_mutants", "test_the_mutant_is_killed[b-original]", None),
    )
    assert gen_kill_counts.main(["--against", str(run)]) == 1
    assert (
        "`b` is recorded, but the reports hold no kill of it at the original size" in capsys.readouterr().err
    )


def test_a_search_the_run_holds_and_the_file_does_not_fails(
    recorded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = report(
        recorded_tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", 1, 2),
        *both("test_x_mutants", "test_the_mutant_is_killed", "b", 3, 4),
        *both("test_z_mutants", "test_the_new_one_is_killed", "d", 1, 1),
    )
    assert gen_kill_counts.main(["--against", str(run)]) == 1
    assert "`d` ran, killed at" in capsys.readouterr().err


# --- measuring ----------------------------------------------------------------------------------------------


def test_measuring_runs_every_search_and_records_or_checks_its_report(
    recorded_tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    given: dict[str, int] = {}

    def measured(workers: int, directory: Path) -> Path:
        given["workers"] = workers
        return run_of_every_search(directory, small=7)

    monkeypatch.setattr(gen_kill_counts, "measured", measured)
    assert gen_kill_counts.main(["--measure", "--workers", "3"]) == 1
    assert given == {"workers": 3}
    assert gen_kill_counts.main(["--measure", "--record"]) == 0
    assert "| `a` | x | 7, 2 |" in (recorded_tree / "README.md").read_text()
    assert gen_kill_counts.main(["--measure"]) == 0

    def failing(workers: int, directory: Path) -> None:
        return None

    monkeypatch.setattr(gen_kill_counts, "measured", failing)
    assert gen_kill_counts.main(["--measure"]) == 1  # a search failed: nothing is known of its kill
    assert "other inputs" not in capsys.readouterr().err
    SEEDED_BY[HELPER] = "bbbbbbbbbbbb"  # a failed search beside an edited helper: the edit is named
    assert gen_kill_counts.main(["--measure"]) == 1
    said = capsys.readouterr().err
    assert "re-seeded to an example that fails its own check" in said
    assert f"{HELPER} changed" in said


def test_the_search_run_is_every_mutant_search_with_a_junit_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[list[str]] = []

    class Done:
        returncode = 0

    def run(command: list[str], **keywords: object) -> Done:
        ran.append(command)
        return Done()

    monkeypatch.setattr(subprocess, "run", run)
    assert gen_kill_counts.measured(5, tmp_path) == tmp_path / "kill_points.xml"
    [command] = ran
    assert command[1:] == [
        "-m",
        "pytest",
        "tests/property",
        "--property-controls",
        "only",
        "-n",
        "5",
        "--dist",
        "worksteal",
        "-q",
        "--tb=short",
        f"--junitxml={tmp_path / 'kill_points.xml'}",
    ]


@pytest.mark.parametrize(
    "arguments",
    [
        ["--record"],
        ["--measure", "--check"],
        ["--measure", "--against", "x.xml"],
        ["--measure", "--record", "x.xml"],
        ["--group", GROUP],
        ["--check", "--group", GROUP],
        ["--against", "x.xml", "--group", GROUP],
        ["--measure", "--record", "--group", GROUP],
        ["--record", "x.xml", "--group", "test_x_mutants.py"],
    ],
)
def test_a_mode_the_script_does_not_take_is_refused(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as refused:
        gen_kill_counts.main(arguments)
    assert refused.value.code == 2


# --- the repository's own -----------------------------------------------------------------------------------


def test_the_repositorys_readme_holds_the_recorded_counts_and_a_count_changed_fails(
    tree: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check on the repository's own files, copied: it reads every table, and one count changed by hand
    fails it (CI runs the check itself in its generated-files job)."""
    monkeypatch.setattr(gen_kill_counts, "inputs_of_tree", REAL_INPUTS)
    monkeypatch.setattr(gen_kill_counts, "NO_TABLE", REAL_NO_TABLE)
    shutil.copy(gen_kill_counts.REPOSITORY / "tests" / "property" / "README.md", tree / "README.md")
    shutil.copy(
        gen_kill_counts.REPOSITORY / "tests" / "property" / "kill_points.json", tree / "kill_points.json"
    )
    assert gen_kill_counts.main(["--check"]) == 0
    lines = (tree / "README.md").read_text().split("\n")
    tables = gen_kill_counts.tables(lines)
    assert sum(table.every for table in tables) >= 8
    row = tables[0].rows[0]
    lines[row.line] = lines[row.line].rsplit("|", 2)[0] + "| 2,000, 2,000 |"
    (tree / "README.md").write_text("\n".join(lines))
    assert gen_kill_counts.main(["--check"]) == 1
    assert "differ from kill_points.json" in capsys.readouterr().err


# --- what the kill points depend on -------------------------------------------------------------------------


def kept(tree: Path) -> str:
    return (tree / "kill_points.json").read_text(encoding="utf-8")


def test_a_hypothesis_upgrade_fails_the_check_and_against_naming_the_cause(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |"))
    assert gen_kill_counts.main([]) == 0
    assert gen_kill_counts.main(["--check"]) == 0  # control: the same inputs pass
    SEEDED_BY["hypothesis"] = "9.9.9"
    assert gen_kill_counts.main(["--check"]) == 1
    said = capsys.readouterr().err
    assert "Hypothesis changed (recorded 1.2.3, uv.lock 9.9.9)" in said
    assert "--measure --record" in said
    run = report(tree, *both("test_x_mutants", "test_the_mutant_is_killed", "a", 1, 2))
    assert gen_kill_counts.main(["--against", str(run), "--partial"]) == 1
    assert "Hypothesis changed" in capsys.readouterr().err


def test_an_installed_hypothesis_other_than_the_recorded_fails_against(
    tree: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |"))
    run = report(tree, *both("test_x_mutants", "test_the_mutant_is_killed", "a", 1, 2))
    assert gen_kill_counts.main(["--against", str(run), "--partial"]) == 0
    monkeypatch.setattr(gen_kill_counts, "installed_hypothesis", lambda: "7.7.7")
    assert gen_kill_counts.main(["--against", str(run), "--partial"]) == 1
    assert "Hypothesis 7.7.7 is installed, and the kill points were recorded with 1.2.3" in (
        capsys.readouterr().err
    )
    monkeypatch.setattr(gen_kill_counts, "installed_hypothesis", lambda: None)  # not installed: no claim
    assert gen_kill_counts.main(["--against", str(run), "--partial"]) == 0


def test_an_edited_kill_helper_fails_naming_it_and_a_moved_kill_leads_with_the_cause(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |"))
    SEEDED_BY[HELPER] = "bbbbbbbbbbbb"
    assert gen_kill_counts.main(["--check"]) == 1
    said = capsys.readouterr().err
    assert f"{HELPER} changed: Hypothesis seeds each search from the source of this function" in said
    run = report(tree, *both("test_x_mutants", "test_the_mutant_is_killed", "a", 40, 2))
    assert gen_kill_counts.main(["--against", str(run), "--partial"]) == 1
    said = capsys.readouterr().err
    assert said.index(f"{HELPER} changed") < said.index("killed at 40, recorded 1")


@pytest.mark.parametrize("change", ["added", "removed"])
def test_a_kill_helper_added_or_removed_fails_the_check(
    tree: Path, capsys: pytest.CaptureFixture[str], change: str
) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |"))
    if change == "added":
        SEEDED_BY["tests/property/test_new_mutants.py::kill"] = "cccccccccccc"
    else:
        del SEEDED_BY[HELPER]
    assert gen_kill_counts.main(["--check"]) == 1
    said = capsys.readouterr().err
    assert ("is not a recorded input" if change == "added" else "no longer in the tree") in said


def test_a_late_kill_beside_changed_inputs_is_told_to_record_first(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holding(tree, {GROUP: {"late": (900, 1)}}, readme("| `late` | x | 900, 1 |"))
    assert gen_kill_counts.main(["--check"]) == 1
    assert "plan its search" in capsys.readouterr().err
    SEEDED_BY[HELPER] = "bbbbbbbbbbbb"
    assert gen_kill_counts.main(["--check"]) == 1
    assert "if it is still late after recording again, plan its search" in capsys.readouterr().err


def test_recording_part_of_the_searches_where_the_inputs_changed_is_refused(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}, OTHER: {"b": (2, 2)}}, readme("| `a` | x | 1, 2 |"))
    SEEDED_BY[HELPER] = "bbbbbbbbbbbb"
    before = kept(tree)
    part = report(tree, *both("test_x_mutants", "test_the_mutant_is_killed", "a", 6, 8))
    assert gen_kill_counts.main(["--record", str(part), "--group", GROUP]) == 2
    assert "inputs changed, so every kill may have moved, and --group records 1 of the 2" in (
        capsys.readouterr().err
    )
    assert kept(tree) == before  # nothing was written
    both_groups = report(
        tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", 6, 8),
        *both("test_y_mutants", "test_the_other_is_killed", "b", 2, 2),
    )
    assert gen_kill_counts.main(["--record", str(both_groups)]) == 0
    assert gen_kill_counts.load(kept(tree)).inputs[HELPER] == "bbbbbbbbbbbb"
    assert gen_kill_counts.main(["--check"]) == 0


def test_recording_part_of_the_searches_keeps_the_inputs_it_was_recorded_with(tree: Path) -> None:
    """The control of the refusal above: with the inputs unchanged, a part may be recorded, by naming it."""
    holding(tree, {GROUP: {"a": (1, 2)}, OTHER: {"b": (2, 2)}}, readme("| `a` | x | 1, 2 |"))
    part = report(tree, *both("test_x_mutants", "test_the_mutant_is_killed", "a", 6, 8))
    assert gen_kill_counts.main(["--record", str(part), "--group", GROUP]) == 0
    assert gen_kill_counts.load(kept(tree)).kills[OTHER] == {"b": (2, 2)}


def test_measuring_and_recording_writes_the_inputs_and_drops_a_group_the_run_lacks(
    tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    holding(
        tree,
        {
            GROUP: {"a": (1, 2), "b": (3, 4)},
            OTHER: {"c": (5, 6)},
            "test_gone_mutants.py::test_g": {"d": (7, 8)},
        },
        readme("| `a` | x | 1, 2 |", "| `b` | y | 3, 4 |"),
    )

    def measured(workers: int, directory: Path) -> Path:
        return run_of_every_search(directory)

    monkeypatch.setattr(gen_kill_counts, "measured", measured)
    SEEDED_BY[HELPER] = "bbbbbbbbbbbb"
    assert gen_kill_counts.main(["--measure"]) == 1  # the stale inputs and the group the run lacks
    said = capsys.readouterr().err
    assert f"{HELPER} changed" in said
    assert "test_gone_mutants.py::test_g: recorded, but the run holds no search of it" in said
    assert gen_kill_counts.main(["--measure", "--record"]) == 0
    record = gen_kill_counts.load(kept(tree))
    assert "dropped test_gone_mutants.py::test_g" in capsys.readouterr().err
    assert set(record.kills) == {GROUP, OTHER}
    assert record.inputs == SEEDED_BY
    assert gen_kill_counts.main(["--measure"]) == 0


# --- a run of every search ----------------------------------------------------------------------------------


def test_a_recorded_group_the_run_lacks_fails_against_unless_the_report_is_partial(
    recorded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A test function renamed or deleted leaves counts nothing runs: its group is missing from the run."""
    run = report(
        recorded_tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", 1, 2),
        *both("test_x_mutants", "test_the_mutant_is_killed", "b", 3, 4),
    )
    assert gen_kill_counts.main(["--against", str(run)]) == 1
    assert f"{OTHER}: recorded, but the run holds no search of it" in capsys.readouterr().err
    assert gen_kill_counts.main(["--against", str(run), "--partial"]) == 0
    renamed = report(
        recorded_tree,
        *both("test_x_mutants", "test_the_renamed_is_killed", "a", 1, 2),
        *both("test_x_mutants", "test_the_renamed_is_killed", "b", 3, 4),
        *both("test_y_mutants", "test_the_other_is_killed", "c", 5, 6),
    )
    assert gen_kill_counts.main(["--against", str(renamed)]) == 1
    said = capsys.readouterr().err
    assert f"{GROUP}: recorded, but the run holds no search of it" in said
    assert "test_the_renamed_is_killed" in said  # and the new group is not recorded


def test_a_partial_report_is_for_against_alone() -> None:
    with pytest.raises(SystemExit) as refused:
        gen_kill_counts.main(["--partial"])
    assert refused.value.code == 2


def test_a_search_that_passed_without_recording_its_kill_fails_against_and_cannot_be_recorded(
    recorded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = report(
        recorded_tree,
        *both("test_x_mutants", "test_the_mutant_is_killed", "a", 1, 2),
        *both("test_x_mutants", "test_the_mutant_is_killed", "b", 3, 4),
        *both("test_y_mutants", "test_the_other_is_killed", "c", 5, 6),
        ("test_x_mutants", "test_the_mutant_is_killed[forgot-small]", -1),
        ("test_x_mutants", "test_the_mutant_is_killed[forgot-original]", -1),
    )
    assert gen_kill_counts.main(["--against", str(run)]) == 1
    said = capsys.readouterr().err
    assert "test_x_mutants.py::test_the_mutant_is_killed[forgot-small] passed without recording" in said
    assert gen_kill_counts.main(["--record", str(run)]) == 2
    assert "passed without recording examples_to_kill" in capsys.readouterr().err
    # controls: a test that is no mutant search, a failed search and a skipped one are not silent
    other = report(
        recorded_tree,
        ("test_x_audit", "test_the_mutant_is_killed[forgot-small]", -1),  # not a mutant module
        ("test_x_mutants", "test_the_mutant_is_killed[a]", -1),  # no size: no search
        ("test_x_mutants", "test_the_mutant_is_killed[b-small]", None),  # failed
    )
    assert gen_kill_counts.reported([other]).silent == ()


# --- the README's tables ------------------------------------------------------------------------------------


def test_a_recorded_group_whose_marker_was_deleted_fails_the_check(
    tree: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    holding(tree, {GROUP: {"a": (1, 2)}}, readme("| `a` | x | 1, 2 |"))
    assert gen_kill_counts.main([]) == 0
    assert gen_kill_counts.main(["--check"]) == 0
    text = (
        (tree / "README.md")
        .read_text()
        .replace(f"<!-- kill points of every search of {GROUP} (scripts/gen_kill_counts.py) -->\n", "")
    )
    (tree / "README.md").write_text(text)
    assert gen_kill_counts.main(["--check"]) == 1
    assert f"{GROUP}: recorded, and the README holds no kill points comment" in capsys.readouterr().err
    # control: a group listed as having no table needs none
    holding(tree, {GROUP: {"a": (1, 2)}}, text)
    monkeypatch.setattr(gen_kill_counts, "NO_TABLE", frozenset({GROUP}))
    assert gen_kill_counts.main([]) == 0
    assert gen_kill_counts.main(["--check"]) == 0


def test_the_planned_searches_controls_run_the_examples_the_margin_guard_allows() -> None:
    assert support.MARGIN == gen_kill_counts.MARGIN


def test_the_readme_holds_a_table_for_exactly_the_recorded_groups_but_two() -> None:
    """By name, so that a marker deleted or moved to another group's table fails here too."""
    text = (gen_kill_counts.REPOSITORY / "tests" / "property" / "README.md").read_text(encoding="utf-8")
    marked = sorted(
        (found["extent"], found["group"])
        for found in map(gen_kill_counts.MARKER.fullmatch, text.split("\n"))
        if found
    )
    assert marked == sorted(
        [
            ("some searches", "test_mutants.py::test_the_mutant_is_killed"),
            ("every search", "test_value_field_mutants.py::test_the_mutant_is_killed"),
            ("every search", "test_condition_mutants.py::test_the_mutant_is_killed"),
            ("every search", "test_result_mutants.py::test_the_result_mutant_is_killed"),
            (
                "every search",
                "test_evaluate_mutants.py::test_the_evaluator_mutant_is_killed_at_its_assertion",
            ),
            (
                "every search",
                "test_model_mutants.py::test_the_implementations_mutant_is_killed_by_the_agreement",
            ),
            (
                "every search",
                "test_model_mutants.py::test_the_models_seeded_mutant_is_killed_by_the_agreement",
            ),
            ("every search", "test_alternatives_mutants.py::test_the_alternatives_mutant_is_killed"),
            ("every search", "test_table_form_mutants.py::test_the_table_form_mutant_is_killed"),
            ("every search", "test_table_read_mutants.py::test_the_table_read_mutant_is_killed"),
            ("every search", "test_extrapolation_mutants.py::test_the_extrapolation_mutant_is_killed"),
            (
                "every search",
                "test_table_alternatives_mutants.py::test_the_table_alternatives_mutant_is_killed",
            ),
            ("every search", "test_declaration_mutants.py::test_the_declaration_mutant_is_killed"),
            ("every search", "test_invariance_mutants.py::test_the_invariance_mutant_is_killed"),
            ("every search", "test_monotonicity_mutants.py::test_the_relations_mutant_is_killed"),
            (
                "every search",
                "test_monotonicity_mutants.py::test_the_unrestricted_twins_mutant_is_killed_by_the_core",
            ),
        ]
    )
    recorded = gen_kill_counts.load(
        (gen_kill_counts.REPOSITORY / "tests" / "property" / "kill_points.json").read_text(encoding="utf-8")
    ).kills
    assert {group for _, group in marked} | gen_kill_counts.NO_TABLE == set(recorded)
    assert not {group for _, group in marked} & gen_kill_counts.NO_TABLE


# --- the seeding sources ------------------------------------------------------------------------------------

HELPER_SOURCE = '''
from hypothesis import given, settings

MUTANT_SEARCH = settings(max_examples=2000, derandomize=True)


def kill(examples, check):
    """The examples searched."""
    tried = 0

    @MUTANT_SEARCH
    @given(examples)
    def search(example):
        # a comment
        nonlocal tried
        tried += 1
        check(example)

    return search
'''


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository of its own: one test module with a kill helper, and a lock."""
    (tmp_path / "tests" / "property").mkdir(parents=True)
    (tmp_path / "tests" / "property" / "test_x_mutants.py").write_text(HELPER_SOURCE, encoding="utf-8")
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "pytest"\nversion = "1.0"\n\n'
        '[[package]]\nname = "hypothesis"\nversion = "6.7.8"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(gen_kill_counts, "REPOSITORY", tmp_path)
    monkeypatch.setattr(gen_kill_counts, "PROPERTY_TESTS", tmp_path / "tests" / "property")
    monkeypatch.setattr(gen_kill_counts, "LOCK", tmp_path / "uv.lock")
    return tmp_path


def seeding(repository: Path, source: str = HELPER_SOURCE) -> dict[str, str]:
    (repository / "tests" / "property" / "test_x_mutants.py").write_text(source, encoding="utf-8")
    return REAL_INPUTS()


def test_the_inputs_are_the_locked_hypothesis_and_the_digest_of_each_seeding_source(repository: Path) -> None:
    inputs = seeding(repository)
    assert inputs["hypothesis"] == "6.7.8"
    assert set(inputs) == {
        "hypothesis",
        "tests/property/test_x_mutants.py::kill",
        "tests/property/test_x_mutants.py::MUTANT_SEARCH",
    }
    assert all(len(value) == 12 for name, value in inputs.items() if name != "hypothesis")


@pytest.mark.parametrize(
    ("edit", "moves"),
    [
        ("example", True),  # a local renamed: the measured case, 37 of 51 kills of a size moved
        ("        tried += 1", True),
        ("max_examples=2000", True),  # the settings every search is seeded and bounded by
        ("    # a comment", False),
    ],
    ids=["a renamed parameter", "a statement", "the search settings", "a comment line"],
)
def test_an_edit_to_a_seeding_source_moves_its_digest_unless_it_is_only_a_comment(
    repository: Path, edit: str, moves: bool
) -> None:
    before = seeding(repository)
    if edit == "max_examples=2000":
        edited = HELPER_SOURCE.replace(edit, "max_examples=2001")
    elif edit == "    # a comment":
        edited = HELPER_SOURCE.replace(
            "        # a comment", "        # another comment\n\n        # and a third"
        )
    elif edit == "example":
        edited = HELPER_SOURCE.replace("(example)", "(sample)").replace("check(example)", "check(sample)")
    else:
        edited = HELPER_SOURCE.replace(edit, "        tried += 2")
    after = seeding(repository, edited)
    assert (after != before) is moves
    if edit == "max_examples=2000":
        assert (
            after["tests/property/test_x_mutants.py::kill"]
            == before["tests/property/test_x_mutants.py::kill"]
        )
    assert gen_kill_counts.stale(before, after) != [] if moves else gen_kill_counts.stale(before, after) == []


def test_an_edit_outside_the_search_function_moves_no_digest(repository: Path) -> None:
    """The digest is of what Hypothesis hashes (the search function), not the helper around it."""
    before = seeding(repository)
    after = seeding(
        repository, HELPER_SOURCE.replace('"""The examples searched."""', '"""Another summary."""')
    )
    assert after == before


def test_a_second_helper_is_found_and_two_of_one_name_are_refused(repository: Path) -> None:
    second = HELPER_SOURCE.replace("def kill(", "def search_all(")
    inputs = seeding(
        repository,
        HELPER_SOURCE + second.split("MUTANT_SEARCH = settings(max_examples=2000, derandomize=True)")[1],
    )
    assert "tests/property/test_x_mutants.py::search_all" in inputs
    twice = HELPER_SOURCE + HELPER_SOURCE.split("derandomize=True)")[1]
    with pytest.raises(CountsError, match="two definitions"):
        seeding(repository, twice)


def test_the_locked_hypothesis_is_read_from_the_lock(repository: Path) -> None:
    assert gen_kill_counts.locked_hypothesis() == "6.7.8"
    (repository / "uv.lock").write_text('[[package]]\nname = "pytest"\nversion = "1.0"\n', encoding="utf-8")
    with pytest.raises(CountsError, match="no one Hypothesis"):
        gen_kill_counts.locked_hypothesis()


def test_the_repositorys_seeding_sources_are_every_search_decorator_it_holds() -> None:
    """An independent count: each `@MUTANT_SEARCH` line of tests/property is a kill helper recorded as an
    input, beside the settings and the Hypothesis version."""
    decorated = sorted(
        path.name
        for path in (gen_kill_counts.REPOSITORY / "tests" / "property").glob("*.py")
        for line in path.read_text(encoding="utf-8").split("\n")
        if line.strip() == "@MUTANT_SEARCH"
    )
    inputs = REAL_INPUTS()
    helpers = sorted(
        name.split("::")[0].rsplit("/", 1)[1]
        for name in inputs
        if name.endswith(("kill", "examples_to_kill"))
    )
    assert helpers == decorated
    assert len(decorated) == 5
    assert set(inputs) - {name for name in inputs if name.endswith(("kill", "examples_to_kill"))} == {
        "hypothesis",
        "tests/property/support.py::MUTANT_SEARCH",
    }
