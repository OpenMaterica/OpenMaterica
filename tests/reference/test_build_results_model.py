# SPDX-License-Identifier: Apache-2.0
"""The build's results model held on what no build-check case file pins (`results_direct.py`), and its table
of section 4.2, its own data, held to the specification's text: `main` has no `coverage.json` yet (the S7
design's generated table, which S7a-2's code brings), so the table is parsed from `declarations.md` here, each
row's "Covered by" read by a fixed table of the phrasings section 4.2 uses, so that a phrasing it does not
know fails. The seeded faults of the model run against the direct checks too (`test_seeded_faults.py`)."""

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest

from tests.reference import build_results_model, results_direct
from tests.reference.build_results_model import COVERAGE, UNDECIDED, Report
from tests.reference.exceptions import RESULTS_NOT_DECIDED
from tests.reference.read_model import REASONS
from tests.reference.strict_json import JsonObject

REPOSITORY: Final = Path(__file__).resolve().parents[2]
DECLARATIONS: Final = REPOSITORY / "docs" / "specification" / "declarations.md"
COVERAGE_JSON: Final = REPOSITORY / "src" / "materica" / "schema" / "0.1" / "vocabulary" / "coverage.json"

# Section 4.2's "Covered by" phrasings, each read as the kind, whether the code and the condition are named,
# and whether the row holds only on a result whose `assumption` names the acceptance.
PHRASINGS: Final = {
    "a `waiver` naming that condition and code": ("waiver", True, True, False),
    "a `waiver` naming that code": ("waiver", True, False, False),
    "a `pick` only": ("pick", False, False, False),
    "an `extrapolation` only": ("extrapolation", False, False, False),
    "an `extrapolation`, only on a result whose `assumption` names it": ("extrapolation", False, False, True),
    "a `nominal`, only on a result whose `assumption` names it": ("nominal", False, False, True),
    "an `overlay_scope` naming every member that differs": ("overlay_scope", False, False, False),
    "an `accepted_difference`": ("accepted_difference", False, False, False),
    "its `trainable` entry (section 7), on a result that carries a value": ("trainable", False, False, False),
}
# The maintainer's ruling of 2026-10-24, whose words #96 lands: `condition_unknown_name` leaves the first row.
# Once that text is on `main` the departure is empty.
RULED_OUT_OF_THE_FIRST_ROW: Final = ("condition_unknown_name",)


def table_rows(text: str) -> list[tuple[str, str, str]]:
    """Section 4.2's table, row by row: the reasons, the status and what covers them."""
    section = text[text.index("### 4.2 What covers which reason") : text.index("### 4.3")]
    rows = [
        line for line in section.splitlines() if line.startswith("| ") and not line.startswith("| Reason")
    ]
    cells = [tuple(cell.strip() for cell in row.strip("|").split(" | ")) for row in rows]
    return [(cell[0], cell[1], cell[2]) for cell in cells if len(cell) == 3]


def text_row(reasons: str, status: str, covered: str, ruled_out: tuple[str, ...] = ()) -> tuple[object, ...]:
    codes: list[str] = re.findall(r"`([a-z_]+)`", reasons)
    if covered not in PHRASINGS:
        raise ValueError(f"a phrasing the model does not read: {covered!r}")
    return (
        tuple(code for code in codes if code != "trainable" and code not in ruled_out),
        status,
        *PHRASINGS[covered],
        "a specimen difference" in reasons,
        "a condition reason" in reasons,
    )


def model_row(row: build_results_model.Row) -> tuple[object, ...]:
    return (
        row.reasons,
        row.status,
        row.kind,
        row.names_code,
        row.names_condition,
        row.on_assumption,
        row.differences,
        row.condition_reasons,
    )


def coverage_problems(text: str) -> list[str]:
    """Each difference between the model's table and section 4.2's, the ruling's departure aside."""
    rows = table_rows(text)
    try:
        parsed = [
            text_row(*row, ruled_out=RULED_OUT_OF_THE_FIRST_ROW if index == 0 else ())
            for index, row in enumerate(rows)
        ]
    except ValueError as error:
        return [str(error)]
    problems = [
        f"row {index}: the text's {text!r}, the model's {model!r}"
        for index, (text, model) in enumerate(zip(parsed, map(model_row, COVERAGE), strict=False))
        if text != model
    ]
    if len(parsed) != len(COVERAGE):
        problems.append(f"{len(parsed)} rows in the text, {len(COVERAGE)} in the model")
    problems += [
        f"row {index}: the qualifier {row.qualifier!r} is not the text's"
        for index, row in enumerate(COVERAGE)
        if row.qualifier and index < len(rows) and row.qualifier not in rows[index][0]
    ]
    return problems


def test_coverage_json_is_not_on_main_so_the_text_is_the_check() -> None:
    """When S7a-2's code lands `coverage.json`, the model's table is to be held to it too: this fails then."""
    assert not COVERAGE_JSON.exists()


def test_the_model_s_table_is_section_4_2_s() -> None:
    assert coverage_problems(DECLARATIONS.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        pytest.param(
            "`not_reviewed` | unknown | a `waiver` naming that code |",
            "`not_reviewed` | unknown | a `waiver` naming the code |",
            "a phrasing",
            id="phrasing",
        ),
        pytest.param(
            "`entries_withheld`, `not_reviewed` |", "`entries_withheld` |", "row 1", id="not-reviewed-dropped"
        ),
        pytest.param("| `no_pick` | unknown |", "| `no_pick` | not_met |", "row 2", id="status"),
        pytest.param(
            "| a `nominal`, only on a result whose `assumption` names it |",
            "| a `nominal` only |",
            "a phrasing",
            id="assumption-dropped",
        ),
        pytest.param(
            "| `engine_mass_not_comparable` | unknown | a `waiver` naming that code |\n",
            "| `engine_mass_not_comparable` | unknown | a `waiver` naming that code |\n"
            "| `at_edge` | not_met | an `extrapolation` only |\n",
            "rows in the text",
            id="row-added",
        ),
        pytest.param(
            "or a vector read from a parameter set with none", "or a vector", "qualifier", id="qualifier"
        ),
    ],
)
def test_a_table_that_drifts_from_the_model_s_fails(old: str, new: str, problem: str) -> None:
    """Controls: a row's phrasing rewritten, `not_reviewed` dropped from its row (the S7-spec review's
    surviving hand mutant, which passed every check until the table was held), a status changed, a row's
    condition dropped, a row added and a qualifier cut are each found."""
    text = DECLARATIONS.read_text(encoding="utf-8")
    assert text.count(old) == 1
    found = coverage_problems(text.replace(old, new))
    assert found
    assert any(problem in one for one in found), found


def test_each_row_s_status_is_its_reasons_status() -> None:
    """A row's status column states the status the read side's table gives each reason it lists."""
    for row in COVERAGE:
        if row.status in ("unknown", "not_met"):
            assert {REASONS[code].status for code in row.reasons} == {row.status}, row


def test_the_kinds_the_model_does_not_decide_each_have_a_reason() -> None:
    assert RESULTS_NOT_DECIDED.keys() == UNDECIDED.keys()
    assert all(reason.strip() for reason in RESULTS_NOT_DECIDED.values())


@pytest.mark.parametrize("check", results_direct.CHECKS, ids=lambda check: check.what)
def test_the_model_gives_each_declaration_the_answer_the_text_gives(check: results_direct.Direct) -> None:
    assert results_direct.judged(check) is None


FIRST: Final = results_direct.CHECKS[0]


@pytest.mark.parametrize(
    ("check", "problem"),
    [
        pytest.param(
            replace(
                FIRST,
                results=(
                    results_direct.Expected(
                        "drag", results_direct.GRADE, "bulk.density", {"status": "unknown"}
                    ),
                ),
            ),
            "status",
            id="a-member",
        ),
        pytest.param(
            replace(
                FIRST,
                results=(
                    results_direct.Expected("drag", results_direct.GRADE, "bulk.density", {"value": None}),
                ),
            ),
            "value",
            id="an-absent-member",
        ),
        pytest.param(replace(FIRST, results=()), "results", id="a-result"),
        pytest.param(replace(FIRST, unused=frozenset({("drag", 0)})), "unused", id="unused"),
        pytest.param(replace(FIRST, refused=False), "refused", id="the-verdict"),
        pytest.param(replace(FIRST, resolved=()), "records", id="records"),
        pytest.param(replace(FIRST, undecided="label_trust"), "not no verdict", id="a-no-verdict"),
    ],
)
def test_a_direct_check_the_model_does_not_meet_is_found(check: results_direct.Direct, problem: str) -> None:
    """Control: each kind of disagreement a direct check can find is reported."""
    found = results_direct.judged(check)
    assert found is not None
    assert problem in found


def test_the_verdict_is_a_result_not_accepted() -> None:
    """declarations.md:246 "The build MUST refuse to build while any result is not accepted, and reports every
    such result, not only": the verdict of a report, by its results."""
    accepted: JsonObject = {"model": "a", "accepted": True}
    refused: JsonObject = {"model": "b", "accepted": False}
    assert not Report({}, (), {}, (accepted, accepted), ()).refused
    assert Report({}, (), {}, (accepted, refused), ()).refused
    assert Report({}, (), {}, (refused, accepted), ()).refused
    assert not Report({}, (), {}, (), ()).refused


def test_a_report_leaves_the_watches_out_and_says_so() -> None:
    report = Report({}, (), {}, (), ())
    assert "watches" not in report.to_json()
    assert report.undecided == {"watches": UNDECIDED["watches"]}
    assert json.dumps(report.to_json())
