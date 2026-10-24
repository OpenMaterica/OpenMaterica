# SPDX-License-Identifier: Apache-2.0
"""The power of the case-agreement check: each seeded fault of the reference model (`mutants.py`) gives some
case file of a read an outcome the list of exceptions does not (a disagreement, a no verdict no kind lists, or
an agreement with a listed file), or is listed as a survivor with the reason no case does. A survivor
the cases come to kill, and a killed fault that comes to survive, both fail, so that the table in `README.md`
stays true. A fault that makes the model raise on a case file the check reads fails its check with the model's
traceback: a crash shows that the fault broke the model, not that a case's expected answer tells the fault
apart, so it is never counted as a kill. The check reads a fault's case files up to its first kill, so a raise
on a later one is not seen there; the faults that once raised are held on the files where they did.

The build model's faults (`BUILD_MUTANTS`) are held to the build-check case files the same way, against
`BUILD_EXCEPTIONS`, and failing those to the direct checks (`direct.py`)."""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn

import pytest

from tests.reference import build_model, direct
from tests.reference.cases import (
    build_case_files,
    build_outcome,
    case_files,
    first_build_disagreement,
    first_disagreement,
    outcome,
    read_case_files,
)
from tests.reference.mutants import BUILD_MUTANTS, MUTANTS, Mutant


def check(name: str, mutant: Mutant) -> None:
    """The cases kill the fault, or it is listed as a survivor."""
    with mutant.applied():
        found = first_disagreement()
    if mutant.survives is None:
        assert found is not None, f"{name} ({mutant.fault}) gives every case file its listed outcome"
    else:
        assert found is None, f"{name} is listed as a survivor ({mutant.survives}), but {found}"


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_the_cases_kill_the_fault_or_it_is_listed_as_a_survivor(name: str) -> None:
    check(name, MUTANTS[name])


# The check above stops at a fault's first killing file, so a raise on a later file is not seen. Seven faults
# once made the model raise, each found by measuring every fault over every case file of a read; each now
# answers there, and is held to its answer on the files where it raised: a disagreement where the file kills
# it, and an agreement where it takes no effect, a table alternative across an edge under an extrapolation
# among them, on which the model gave no verdict until S4d. The `condition_entry` wrappers of two, before they
# took the table axis, raised on every file they reached (353 and 330), the three table reads here among them.
# S3c's two raised in their first form (2026-10-21), each asking the reference evaluator for a value where it
# gives none in range: across an edge on the readable range's end, and at `x[0]` or `x[-1]` outside a
# narrower `source_range`. None of S4d's twelve raised, in its first form or since (2026-10-22).
TABLE_READS_THE_WRAPPERS_RAISED_ON = {
    "PR-016.linear_between_knots.json": "agrees",
    "PR-017.far_above.json": "agrees",
    "PR-018.at_edge.json": "agrees",
}
ONCE_RAISED = {
    "best_status": {"PR-301.unknown_beside_outside_range.json": "differs"},
    "null_read_as_absent": {"PR-049.source_range_null.json": "differs"},
    "alternatives_shape_unchecked": {"PR-044.alternatives_not_list.json": "differs"},
    "condition_shapes_unchecked": {
        "PR-049.condition_value_null.json": "differs",
        **TABLE_READS_THE_WRAPPERS_RAISED_ON,
    },
    "tolerance_without_an_operating_condition": {
        "PR-308.tolerance_with_other_operating_condition.json": "differs",
        "PR-308.tolerance_without_operating_conditions.json": "differs",
        **TABLE_READS_THE_WRAPPERS_RAISED_ON,
    },
    "extrapolation_across_an_edge": {
        "PR-307.across_edge_on_range_end.json": "agrees",
        "PR-307.across_edge_on_range_end_above.json": "agrees",
    },
    "extrapolation_end_of_x": {
        "PR-044.across_edge_under_extrapolation_set_aside.json": "agrees",
        "PR-307.above_narrowed_range.json": "differs",
        "PR-307.above_range_edge_inside.json": "differs",
        "PR-307.across_edge.json": "agrees",
        "PR-307.across_edge_above.json": "agrees",
        "PR-307.across_edge_on_range_end.json": "agrees",
        "PR-307.across_edge_on_range_end_above.json": "agrees",
        "PR-307.below_narrowed_range.json": "differs",
        "PR-307.below_range_edge_inside.json": "differs",
    },
}


@pytest.mark.parametrize(
    ("name", "file", "kind"),
    [(name, file, kind) for name, files in ONCE_RAISED.items() for file, kind in files.items()],
)
def test_a_fault_that_once_raised_answers_on_the_files_it_raised_on(name: str, file: str, kind: str) -> None:
    (case_file,) = [found for found in read_case_files() if found.path.name == file]
    with MUTANTS[name].applied():
        assert outcome(case_file).kind == kind


def test_the_table_holds_at_least_thirty_faults_and_says_why_each_survivor_survives() -> None:
    assert len(MUTANTS) >= 30
    assert all(mutant.survives is None or mutant.survives.strip() for mutant in MUTANTS.values())
    assert all(mutant.fault.strip() and mutant.rule.strip() for mutant in MUTANTS.values())


def test_a_fault_leaves_the_model_as_it_was_once_its_search_is_done() -> None:
    (case_file,) = [found for found in case_files() if found.path.name == "PR-035.linear_label_returned.json"]
    with MUTANTS["step_12_labels_dropped"].applied():
        assert outcome(case_file).kind == "differs"
    assert outcome(case_file).kind == "agrees"


def broken_model(kind: type[Exception]) -> Mutant:
    """A fault that breaks the model rather than a rule of the text: `status_object`, which nearly every read
    reaches, replaced by a function raising `kind`."""

    def raising(*args: object, **kwargs: object) -> NoReturn:
        raise kind("the model broken, not a rule of the text")

    return Mutant("the model raises wherever it reads a status object", "none", {"status_object": raising})


# The control: `TypeError`, and the `KeyError` and `AssertionError` that seeded faults once made the model
# raise. A check that counted the raise as a kill, of every kind or of one, would pass on it.
@pytest.mark.parametrize("kind", [TypeError, KeyError, AssertionError])
def test_a_fault_that_makes_the_model_raise_fails_its_check_and_leaves_the_model_as_it_was(
    kind: type[Exception],
) -> None:
    with pytest.raises(kind, match="the model broken") as raised:
        check("broken_model", broken_model(kind))
    notes = getattr(raised.value, "__notes__", [])
    assert any(note.startswith("the model raised reading PR-") for note in notes), notes
    (case_file,) = [found for found in case_files() if found.path.name == "PR-035.linear_label_returned.json"]
    assert outcome(case_file).kind == "agrees"


def build_check(name: str, mutant: Mutant) -> None:
    """The build-check cases, or failing those the direct checks, kill the build model's fault, or it is
    listed as a survivor."""
    with mutant.applied():
        found = first_build_disagreement() or next(iter(direct.problems()), None)
    if mutant.survives is None:
        assert found is not None, f"{name} ({mutant.fault}) gives every build-check file its listed outcome"
    else:
        assert found is None, f"{name} is listed as a survivor ({mutant.survives}), but {found}"


@pytest.mark.parametrize("name", sorted(BUILD_MUTANTS))
def test_the_build_cases_kill_the_fault_or_it_is_listed_as_a_survivor(name: str) -> None:
    build_check(name, BUILD_MUTANTS[name])


def test_the_build_table_holds_its_faults_apart_and_says_why_each_survivor_survives() -> None:
    assert len(BUILD_MUTANTS) >= 100
    assert MUTANTS.keys().isdisjoint(BUILD_MUTANTS)
    assert all(mutant.module is build_model for mutant in BUILD_MUTANTS.values())
    assert all(mutant.survives is None or mutant.survives.strip() for mutant in BUILD_MUTANTS.values())
    assert all(mutant.fault.strip() and mutant.rule.strip() for mutant in BUILD_MUTANTS.values())


def test_a_build_fault_leaves_the_model_as_it_was_once_its_search_is_done() -> None:
    (case_file,) = [
        found for found in build_case_files() if found.path.name == "BC-004.tolerance_without_reason.json"
    ]
    with BUILD_MUTANTS["build_item_3_unchecked"].applied():
        assert build_outcome(case_file).kind == "differs"
    assert build_outcome(case_file).kind == "agrees"


def broken_build_model(kind: type[Exception]) -> Mutant:
    """A fault that breaks the build model rather than a rule of the text: its token check, which every
    declaration reaches, replaced by a function raising `kind`."""

    def raising(*args: object, **kwargs: object) -> NoReturn:
        raise kind("the build model broken, not a rule of the text")

    return Mutant(
        "the build model raises at every token",
        "none",
        {"DeclarationCheck.token": raising},
        module=build_model,
    )


@pytest.mark.parametrize("kind", [TypeError, KeyError, AssertionError])
def test_a_build_fault_that_makes_the_model_raise_fails_its_check(kind: type[Exception]) -> None:
    """Control: a search that counted the raise as a kill would pass on it."""
    with pytest.raises(kind, match="the build model broken") as raised:
        build_check("broken_build_model", broken_build_model(kind))
    notes = getattr(raised.value, "__notes__", [])
    assert any(note.startswith("the build model raised reading BC-") for note in notes), notes


README = Path(__file__).with_name("README.md")
README_ROW = re.compile(r"^\| `(build_\w+)` \|.*\| (killed|survives) \|\s*$", re.MULTILINE)


def readme_problems(text: str, mutants: Mapping[str, Mutant]) -> list[str]:
    """Each build fault the README's table does not list, lists without a fault, or lists with the wrong
    outcome: it says only whether the cases (or the direct checks) kill a fault, and the table here is the
    one source of why a survivor survives."""
    rows = dict(README_ROW.findall(text))
    return [
        *(f"{name}: no row" for name in mutants if name not in rows),
        *(f"{name}: a row, and no fault" for name in rows if name not in mutants),
        *(
            f"{name}: the row says {rows[name]}, the table {'survives' if mutant.survives else 'killed'}"
            for name, mutant in mutants.items()
            if name in rows and (rows[name] == "survives") != (mutant.survives is not None)
        ),
    ]


def test_the_readme_lists_each_build_fault_and_whether_it_survives() -> None:
    assert readme_problems(README.read_text(encoding="utf-8"), BUILD_MUTANTS) == []


def test_a_readme_table_that_drifts_from_the_faults_fails() -> None:
    """Control: a row dropped, a row for no fault and a row with the other outcome are each found."""
    killed = next(name for name, mutant in BUILD_MUTANTS.items() if mutant.survives is None)
    text = README.read_text(encoding="utf-8")
    row = next(match for match in README_ROW.finditer(text) if match[1] == killed)
    assert readme_problems(text.replace(row[0], ""), BUILD_MUTANTS) == [f"{killed}: no row"]
    assert readme_problems(text + "| `build_no_such_fault` | a fault | killed |\n", BUILD_MUTANTS) == [
        "build_no_such_fault: a row, and no fault"
    ]
    flipped = text.replace(row[0], row[0].replace("| killed |", "| survives |"))
    assert readme_problems(flipped, BUILD_MUTANTS) == [f"{killed}: the row says survives, the table killed"]
