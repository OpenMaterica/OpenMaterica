# SPDX-License-Identifier: Apache-2.0
"""The build's results model held on what no build-check case file pins (`results_direct.py`), and its table
of section 4.2, its own data, held to the specification's text: `main` has no `coverage.json` yet (the S7
design's generated table, which S7a-2b brings), so the table is parsed from `declarations.md` here, each
row's "Covered by" read by a fixed table of the phrasings section 4.2 uses, so that a phrasing it does not
know fails; and held to `coverage.json` once it exists. The seeded faults of the model run against the
direct checks too (`test_seeded_faults.py`)."""

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
from tests.reference.strict_json import JsonObject, JsonValue, parse

REPOSITORY: Final = Path(__file__).resolve().parents[2]
DECLARATIONS: Final = REPOSITORY / "docs" / "specification" / "declarations.md"
COVERAGE_JSON: Final = REPOSITORY / "src" / "materica" / "schema" / "0.1" / "vocabulary" / "coverage.json"
ACCEPTANCE_MODULE: Final = REPOSITORY / "src" / "materica" / "core" / "acceptance.py"

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


def table_rows(text: str) -> list[tuple[str, str, str]]:
    """Section 4.2's table, row by row: the reasons, the status and what covers them."""
    section = text[text.index("### 4.2 What covers which reason") : text.index("### 4.3")]
    rows = [
        line for line in section.splitlines() if line.startswith("| ") and not line.startswith("| Reason")
    ]
    cells = [tuple(cell.strip() for cell in row.strip("|").split(" | ")) for row in rows]
    return [(cell[0], cell[1], cell[2]) for cell in cells if len(cell) == 3]


def text_row(reasons: str, status: str, covered: str) -> tuple[object, ...]:
    codes: list[str] = re.findall(r"`([a-z_]+)`", reasons)
    if covered not in PHRASINGS:
        raise ValueError(f"a phrasing the model does not read: {covered!r}")
    return (
        tuple(code for code in codes if code != "trainable"),
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


def coverage_problems(text: str, table: tuple[build_results_model.Row, ...] = COVERAGE) -> list[str]:
    """Each difference between the model's table and section 4.2's."""
    rows = table_rows(text)
    try:
        parsed = [text_row(*row) for row in rows]
    except ValueError as error:
        return [str(error)]
    problems = [
        f"row {index}: the text's {text!r}, the model's {model!r}"
        for index, (text, model) in enumerate(zip(parsed, map(model_row, table), strict=False))
        if text != model
    ]
    if len(parsed) != len(table):
        problems.append(f"{len(parsed)} rows in the text, {len(table)} in the model")
    problems += [
        f"row {index}: the qualifier {row.qualifier!r} is not the text's"
        for index, row in enumerate(table)
        if row.qualifier and index < len(rows) and row.qualifier not in rows[index][0]
    ]
    return problems


def strings_of(value: JsonValue) -> set[str]:
    """Every string a JSON document holds, as a key or a value."""
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return {
            *value,
            *(s for held in value.values() for s in strings_of(held)),
        }
    if isinstance(value, list):
        return {s for held in value for s in strings_of(held)}
    return set()


def coverage_json_problems(coverage_json: Path, acceptance: Path) -> list[str]:
    """What is wrong with `coverage.json` beside the model's table. Where the file is absent, `main`'s state,
    the text is the check, and the build's acceptance module may not exist: that module reads the file, so
    it fails, not skips, without it. Where the file exists, it names every reason the model's table lists.
    The file's shape is S7a-2b's: its generator and its row-by-row comparison with the model's table
    replace the names check."""
    if not coverage_json.exists():
        return [f"{acceptance.name} exists, and {coverage_json.name} does not"] if acceptance.exists() else []
    held = strings_of(parse(coverage_json.read_bytes()))
    return [
        f"{coverage_json.name} names no `{code}`, which the model's table lists"
        for code in sorted({code for row in COVERAGE for code in row.reasons})
        if code not in held
    ]


def test_coverage_json_is_held_to_the_model_s_table_where_it_exists() -> None:
    """Not a skip: with no `coverage.json` on the tree the text is the check, and the build's acceptance
    module may not be there; with the file, its reasons are the model's."""
    assert coverage_json_problems(COVERAGE_JSON, ACCEPTANCE_MODULE) == []


def test_coverage_json_controls(tmp_path: Path) -> None:
    """Controls: an acceptance module without the file fails; a file that misses the first, the last or
    several reasons fails, naming each; a file that names them all, nested as a generator may write them,
    as list values or as dict keys, passes."""
    module, table = tmp_path / "acceptance.py", tmp_path / "coverage.json"
    assert coverage_json_problems(table, module) == []
    module.write_text("", encoding="utf-8")
    assert coverage_json_problems(table, module) == ["acceptance.py exists, and coverage.json does not"]
    codes = sorted({code for row in COVERAGE for code in row.reasons})
    assert len(codes) > 4

    def names_no(*missing: str) -> list[str]:
        return [f"coverage.json names no `{code}`, which the model's table lists" for code in missing]

    for missing in ((codes[0],), (codes[-1],), (codes[0], codes[2], codes[-1])):
        held = [code for code in codes if code not in missing]
        table.write_text(json.dumps({"rows": [{"reasons": held}]}), encoding="utf-8")
        assert coverage_json_problems(table, module) == names_no(*missing)
        table.write_text(json.dumps({"rows": [{code: "unknown" for code in held}]}), encoding="utf-8")
        assert coverage_json_problems(table, module) == names_no(*missing)
    for named in ({"rows": [{"reasons": codes}]}, {"rows": [{code: "unknown" for code in codes}]}):
        table.write_text(json.dumps(named), encoding="utf-8")
        assert coverage_json_problems(table, module) == []


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


def test_a_model_row_that_lists_a_code_the_text_does_not_is_found() -> None:
    """Control: the model's first row listing `condition_unknown_name` again, which section 4.2 never
    accepts (`declarations.md` names it as the one code that is never accepted), is found."""
    text = DECLARATIONS.read_text(encoding="utf-8")
    first = COVERAGE[0]
    listing = replace(first, reasons=(first.reasons[0], "condition_unknown_name", *first.reasons[1:]))
    found = coverage_problems(text, table=(listing, *COVERAGE[1:]))
    assert any(problem.startswith("row 0:") for problem in found), found


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
    """declarations.md:251 "The build MUST refuse to build while any result is not accepted, and reports every
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
