# SPDX-License-Identifier: Apache-2.0
"""The generators of `scripts/`: each reads its source as specified, refuses one it cannot read faithfully,
and fails `--check` when a generated file differs. CI runs each with `--check`."""

import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from scripts import gen_reader_schema, gen_shapes, gen_vocabulary
from scripts.gen_reader_schema import Json, SchemaError, reader_schema
from scripts.gen_vocabulary import TableError, cells, table
from tests.spec_sync.schemas import agreed


def test_a_table_is_read_by_its_headers_with_escaped_pipes() -> None:
    document = '## Words\n\n| Name | Shape |\n|---|---|\n| `a` | `{"t": "x" \\| "y"}` |\n\nAfter.\n'
    assert table(document, "## Words") == [{"Name": "`a`", "Shape": '`{"t": "x" | "y"}`'}]
    assert cells(r"| a | b \| c |") == ["a", "b | c"]


@pytest.mark.parametrize(
    ("document", "heading"),
    [
        pytest.param("## Words\n\nno table\n", "## Words", id="no_table"),
        pytest.param("## Words\n\n| A |\n|---|\n", "## Other", id="no_heading"),
        pytest.param("## Words\n\n| A | B |\n|---|---|\n| 1 |\n", "## Words", id="short_row"),
    ],
)
def test_a_table_that_cannot_be_read_is_refused(document: str, heading: str) -> None:
    with pytest.raises(TableError):
        table(document, heading)


def test_a_reason_row_with_an_unknown_status_is_refused() -> None:
    with pytest.raises(TableError):
        gen_vocabulary.reasons([{"Code": "`absent`", "Status": "maybe"}])


def test_a_numeric_condition_without_its_unit_first_is_refused() -> None:
    with pytest.raises(TableError):
        gen_vocabulary.conditions([{"Name": "`t`", "Shape": "numeric", "Unit or tokens": "kelvin, `K`"}])


def numeric(cell: str) -> gen_vocabulary.Row:
    return {"Name": "`t`", "Shape": "numeric", "Unit or tokens": cell, "Required with": "\u2014"}


@pytest.mark.parametrize(
    "cell", ["`K`", "`K` (the thermodynamic temperature)", "`K`: the specimen's temperature, not the bath's"]
)
def test_a_numeric_conditions_unit_is_read_beside_an_aside_or_prose(cell: str) -> None:
    assert gen_vocabulary.conditions([numeric(cell)])["conditions"] == {
        "t": {"shape": "numeric", "unit": "K", "required_with": {}}
    }


@pytest.mark.parametrize(
    "cell",
    [
        pytest.param("`K` or `Cel`", id="a_second_unit"),
        pytest.param("`K`, `Cel`", id="a_list_of_units"),
        pytest.param("`K` (or `Cel`)", id="a_unit_in_the_aside"),
        pytest.param("`K`: or `Cel` where the source gives it", id="a_unit_in_the_prose"),
    ],
)
def test_a_numeric_conditions_cell_naming_a_second_unit_is_refused(cell: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.conditions([numeric(cell)])


def test_a_code_span_in_a_token_cells_parenthetical_is_refused() -> None:
    """Its token would be dropped with the parenthetical; an aside of plain prose is not."""
    row = {"Name": "`k`", "Shape": "token", "Required with": "\u2014"}
    plain = "`apparent` (the whole specimen, pores included), `matrix`"
    assert gen_vocabulary.conditions([{**row, "Unit or tokens": plain}])["conditions"] == {
        "k": {"shape": "token", "tokens": ["apparent", "matrix"], "required_with": {}}
    }
    with pytest.raises(TableError):
        gen_vocabulary.conditions(
            [{**row, "Unit or tokens": "`apparent` (pores included; also `bulk_apparent`), `matrix`"}]
        )


LABEL = "`materica.fluid.newtonian.v1` on a constant, or on a table whose axis is not `shear_rate`"


def test_a_label_cell_gives_its_one_label() -> None:
    assert gen_vocabulary.field_label(LABEL) == "materica.fluid.newtonian.v1"


def test_a_label_cell_says_where_the_label_goes() -> None:
    assert gen_vocabulary.label_not_on_axis(LABEL) == "shear_rate"
    assert gen_vocabulary.label_not_on_axis("`materica.fluid.newtonian.v1` on a constant") is None


@pytest.mark.parametrize(
    "where",
    [
        pytest.param("an interval", id="another_form"),
        pytest.param("a constant, or on a table whose axis is `shear_rate`", id="the_axis_it_takes"),
        pytest.param("a constant, or on a table whose axis is not shear_rate", id="an_axis_unquoted"),
        pytest.param("a constant, or on a table", id="any_table"),
        pytest.param("a constant or a table whose axis is not `shear_rate`", id="other_words"),
        pytest.param(
            "a constant, or on a table whose axis is not `shear_rate` or `temperature`", id="two_axes"
        ),
    ],
)
def test_a_label_cell_saying_otherwise_where_the_label_goes_is_refused(where: str) -> None:
    """S2a-2's review, M3: where a label goes was a hand-written copy of the cell's prose; it is now read from
    the cell, so that an unexpected cell stops the generator rather than a read."""
    with pytest.raises(TableError):
        gen_vocabulary.label_not_on_axis(f"`materica.fluid.newtonian.v1` on {where}")


@pytest.mark.parametrize(
    "cell",
    [
        pytest.param(
            "`materica.fluid.newtonian.v1` or `materica.fluid.power_law.v1` on a constant", id="two_labels"
        ),
        pytest.param(
            "`materica.fluid.newtonian.v1` on a constant, or `materica.fluid.power_law.v1` on a table",
            id="a_second_label_in_the_prose",
        ),
        pytest.param("`Materica Fluid (Newtonian)` on a constant", id="no_family_identifier"),
        pytest.param("`materica.fluid.newtonian.v01` on a constant", id="a_version_with_a_leading_zero"),
        pytest.param("`materica.fluid.newtonian.v1`", id="no_prose"),
        pytest.param("the label `materica.fluid.newtonian.v1` on a constant", id="label_not_first"),
    ],
)
def test_a_label_cell_of_another_form_is_refused(cell: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.field_label(cell)


@pytest.mark.parametrize(
    ("reader", "column"),
    [
        (gen_vocabulary.reasons, "Code"),
        (gen_vocabulary.fields, "Section.field"),
        (gen_vocabulary.conditions, "Name"),
        (gen_vocabulary.specimen_facts, "Name"),
        (gen_vocabulary.acceptances, "`acceptance`"),
    ],
)
def test_a_name_listed_twice_in_a_table_is_refused(
    reader: Callable[[list[gen_vocabulary.Row]], gen_vocabulary.Vocabulary], column: str
) -> None:
    """A second row would replace the first, its status, steps or shape lost: `names` refuses it before any
    other cell is read."""
    with pytest.raises(TableError, match="listed twice"):
        reader([{column: "`a`"}, {column: "`b`"}, {column: "`a`"}])


def extrapolation_row(own: str) -> list[gen_vocabulary.Row]:
    return [
        {"`acceptance`": "`nominal`", "Own members": "`value`"},
        {"`acceptance`": "`extrapolation`", "Own members": own},
    ]


def test_an_extrapolations_methods_are_its_rows_list() -> None:
    """`declarations.md` section 4.1: "`method` (`constant` or `consumer_law`)", read in full."""
    found = gen_vocabulary.acceptances(
        extrapolation_row("`method` (`constant` or `consumer_law`), `law` (text)")
    )
    assert found == {
        "kinds": ["nominal", "extrapolation"],
        "$defs": {"extrapolation_method": {"enum": ["constant", "consumer_law"]}},
    }


@pytest.mark.parametrize(
    "own",
    [
        pytest.param("`method` (`constant` or a law of one's own), `law`", id="prose_in_the_list"),
        pytest.param("`method`, `law`", id="no_list"),
        pytest.param("`method` (`constant` or `constant`), `law`", id="a_token_twice"),
    ],
)
def test_an_extrapolations_methods_are_read_in_full_or_refused(own: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.acceptances(extrapolation_row(own))


TISSUE_STATE = (
    '`{"token": "in_vivo" \\| "ex_vivo_fresh" \\| "frozen_thawed" \\| "fixed" \\| "phantom", "basis"}`'
)


@pytest.mark.parametrize(
    "cell",
    [
        pytest.param('{"token":"normal" | "diseased" | "treated", "basis"}', id="no_space_after_the_colon"),
        pytest.param('{"token": "normal" | "dis-eased", "basis"}', id="a_hyphen"),
        pytest.param('{"token": "normal" | treated, "basis"}', id="an_unquoted_token"),
        pytest.param('{"token": "normal" or "treated", "basis"}', id="another_separator"),
    ],
)
def test_a_specimen_facts_tokens_are_read_in_full_or_refused(cell: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.specimen_facts([{"Name": "`state`", "JSON shape": f"`{cell}`"}])


@pytest.mark.parametrize(
    ("shape", "fixed"),
    [
        ('{"value", "unit": "s", "basis"}', {"unit": "s"}),
        ('{"value", "unit": "s", "basis"} or {"range": [lo, hi], "unit": "s", "basis"}', {"unit": "s"}),
        ('{"text": <text>, "basis": "stated"}', {"basis": "stated"}),
        ('{"uberon": "UBERON:<digits>", "label": <text>, "basis"}', {}),
        ('{"token": "none" | "other", "text": <text, required for other>, "basis"}', {}),
    ],
)
def test_the_members_a_facts_shape_fixes_are_read_with_their_value(shape: str, fixed: dict[str, str]) -> None:
    assert gen_vocabulary.fixed_members(shape) == fixed


@pytest.mark.parametrize(
    "shape",
    [
        pytest.param('{"value", "unit": "s" | "min", "basis"}', id="a_list_outside_token"),
        pytest.param('{"value", "unit": s, "basis"}', id="an_unquoted_value"),
        pytest.param('{"value", "unit": "s or min", "basis"}', id="a_value_with_a_space"),
        pytest.param('{"value", "unit": "s"} or {"range": [lo, hi], "unit": "min"}', id="two_values"),
    ],
)
def test_a_value_a_facts_shape_writes_otherwise_is_refused(shape: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.specimen_facts([{"Name": "`fact`", "JSON shape": f"`{shape}`"}])


def test_a_facts_fixed_unit_changed_in_the_text_changes_the_vocabulary(tmp_path: Path) -> None:
    """The review's probe: a unit no file held, so that changing it in the text changed nothing."""
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    document = specification / "provenance.md"
    old = '| `post_mortem_interval` | `{"value", "unit": "s", "basis"}` |'
    text = document.read_text(encoding="utf-8")
    assert old in text
    document.write_text(text.replace(old, old.replace('"s"', '"min"')), encoding="utf-8")
    facts = json.loads(gen_vocabulary.generate(specification)["specimen_facts.json"])
    assert facts["facts"]["post_mortem_interval"]["unit"] == "min"
    assert facts["$defs"]["post_mortem_interval_unit"] == {"enum": ["min"]}
    assert facts["$defs"]["units"]["properties"]["post_mortem_interval"] == {
        "properties": {"unit": {"$ref": "#/$defs/post_mortem_interval_unit"}}
    }


@pytest.mark.parametrize(
    ("reader", "row"),
    [
        (
            gen_vocabulary.conditions,
            {"Name": "`g`", "Shape": "token", "Unit or tokens": "`bulk`, tube, `gap`"},
        ),
        (gen_vocabulary.conditions, {"Name": "`g`", "Shape": "token", "Unit or tokens": "`bulk`; `gap`"}),
        (
            gen_vocabulary.fields,
            {
                "Section.field": "`bulk.density`",
                "Unit": "`kg/m3`",
                "Forms": "constant",
                "Requires": "`temperature`, density_kind",
                "Label": "none",
            },
        ),
        (
            gen_vocabulary.fields,
            {
                "Section.field": "`bulk.density`",
                "Unit": "`kg/m3`",
                "Forms": "constant",
                "Requires": "none",
                "Label": "the label `materica.fluid.newtonian.v1`",
            },
        ),
    ],
    ids=["unquoted_token", "another_separator", "unquoted_requirement", "label_not_first"],
)
def test_a_list_of_tokens_with_anything_else_in_it_is_refused(
    reader: Callable[[list[gen_vocabulary.Row]], gen_vocabulary.Vocabulary], row: gen_vocabulary.Row
) -> None:
    with pytest.raises(TableError):
        reader([row])


def test_a_token_table_change_is_read_in_full_or_stops_the_generator(tmp_path: Path) -> None:
    """The review's two examples: a token with a digit is read with the others, never in their place; a cell
    written without the space after the colon stops the generator rather than give no tokens."""
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    document = specification / "provenance.md"
    text = document.read_text(encoding="utf-8")
    assert TISSUE_STATE in text
    document.write_text(text.replace("ex_vivo_fresh", "ex_vivo_2h"), encoding="utf-8")
    facts = json.loads(gen_vocabulary.generate(specification)["specimen_facts.json"])["facts"]
    assert facts["tissue_state"]["tokens"] == ["in_vivo", "ex_vivo_2h", "frozen_thawed", "fixed", "phantom"]
    document.write_text(text.replace('{"token": "normal"', '{"token":"normal"'), encoding="utf-8")
    with pytest.raises(TableError):
        gen_vocabulary.generate(specification)


def copy_tree(tmp_path: Path, source: Path) -> Path:
    target = tmp_path / source.name
    shutil.copytree(source, target)
    return target


def test_the_vocabulary_check_fails_when_a_table_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    monkeypatch.setattr(gen_vocabulary, "SPECIFICATION", specification)
    assert gen_vocabulary.main(["--check"]) == 0
    document = specification / "read_side_contract.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace("| `absent` | not_met |", "| `absent` | unknown |")
    )
    assert gen_vocabulary.main(["--check"]) == 1
    assert "reasons.json differs" in capsys.readouterr().err


def test_the_vocabulary_check_fails_on_a_file_no_table_gives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vocabulary = copy_tree(tmp_path, gen_vocabulary.VOCABULARY)
    monkeypatch.setattr(gen_vocabulary, "VOCABULARY", vocabulary)
    (vocabulary / "stray.json").write_text("{}\n")
    assert gen_vocabulary.main(["--check"]) == 1


def coverage_rows(specification: Path = gen_vocabulary.SPECIFICATION) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = json.loads(gen_vocabulary.generate(specification)["coverage.json"])[
        "coverage"
    ]
    return rows


def test_each_row_of_what_covers_which_reason_is_read_as_its_rule() -> None:
    """`declarations.md` section 4.2, row by row: the codes, the cell as written and the rule it states. "A
    condition reason" is read as each `condition_*` code but `condition_unknown_name`, which the paragraph
    above the table says is never accepted; the nominal's qualifier adds nothing to its row's own condition,
    and the trainable one limits its row to a field listed in `trainable`."""
    rows = coverage_rows()
    assert [(row["kind"], row["reasons"]) for row in rows][:3] == [
        ("waiver", ["condition_unstated", "condition_unchecked", "condition_uncertain"]),
        (
            "waiver",
            [
                "no_requirement",
                "stated_without_origin",
                "outside_check_points",
                "fill_in_version_mismatch",
                "entries_withheld",
                "not_reviewed",
            ],
        ),
        ("pick", ["no_pick"]),
    ]
    flags = {name: False for name in gen_vocabulary.COVERAGE_FLAGS}
    assert rows[0] == {
        "reasons": ["condition_unstated", "condition_unchecked", "condition_uncertain"],
        "specimen_difference": False,
        "status": "unknown",
        "covered_by": "a `waiver` naming that condition and code",
        "kind": "waiver",
        **flags,
        "names_code": True,
        "names_condition": True,
    }
    nominal = next(row for row in rows if row["kind"] == "nominal")
    assert (nominal["reasons"], nominal["on_assumption"], nominal["trainable"]) == (
        ["want_mismatch"],
        True,
        False,
    )
    trainable = rows[-1]
    assert trainable["kind"] == "trainable"
    assert (trainable["trainable"], trainable["carries_value"], trainable["specimen_difference"]) == (
        True,
        True,
        True,
    )
    assert trainable["status"] == "any"
    assert trainable["reasons"] == [
        "condition_unstated",
        "condition_unchecked",
        "condition_outside",
        "condition_not_accepted",
        "condition_uncertain",
        "outside_range",
        "range_unstated",
        "outside_coverage",
    ]
    assert not any("condition_unknown_name" in cast(list[str], row["reasons"]) for row in rows)


def test_the_vocabulary_check_fails_where_not_reviewed_is_dropped_from_what_covers_which_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The S7 design's 9: the S7 specification review's surviving hand mutant, `not_reviewed` dropped from
    section 4.2's table, passed every check while no file held the table. Now the check fails, and the file it
    would write covers `not_reviewed` by nothing."""
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    monkeypatch.setattr(gen_vocabulary, "SPECIFICATION", specification)
    assert gen_vocabulary.main(["--check"]) == 0
    document = specification / "declarations.md"
    text = document.read_text(encoding="utf-8")
    kept = "`entries_withheld`, `not_reviewed` | unknown | a `waiver` naming that code |"
    assert kept in text
    document.write_text(
        text.replace(kept, "`entries_withheld` | unknown | a `waiver` naming that code |"), encoding="utf-8"
    )
    assert gen_vocabulary.main(["--check"]) == 1
    assert (
        capsys.readouterr().err
        == "coverage.json differs from the specification: run scripts/gen_vocabulary.py\n"
    )
    assert not any("not_reviewed" in cast(list[str], row["reasons"]) for row in coverage_rows(specification))


@pytest.mark.parametrize(
    ("cell", "given"),
    [
        ("1, 2, 3, 6", {"steps": [1, 2, 3, 6]}),
        ("0", {"steps": [0]}),
        ("USD read, engine adapter", {"procedures": ["USD read", "engine adapter"]}),
    ],
)
def test_a_reasons_step_is_read_as_steps_or_procedures(cell: str, given: dict[str, object]) -> None:
    assert gen_vocabulary.given_by(cell) == given


@pytest.mark.parametrize("cell", ["14", "07", "1, build", "the build", "1,2", "step 3"])
def test_a_reasons_step_of_another_form_is_refused(cell: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.given_by(cell)


def test_a_fields_forms_are_read_with_the_bases_its_row_allows() -> None:
    assert gen_vocabulary.field_forms("constant, table, interval") == (["constant", "table", "interval"], {})
    assert gen_vocabulary.field_forms("composition (basis `mass_fraction`)") == (
        ["composition"],
        {"composition": ["mass_fraction"]},
    )
    assert gen_vocabulary.field_forms("evidence (section 4.3)") == (["evidence"], {})


@pytest.mark.parametrize(
    "cell",
    [
        "composition (basis mass_fraction)",
        "composition (bases `mass_fraction`)",
        "composition (`mass_fraction` only)",
        "constant; table",
        "Constant",
    ],
)
def test_a_forms_cell_of_another_form_is_refused(cell: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.field_forms(cell)


GEOMETRY = {"measurement_geometry": ["bulk", "tube", "gap"]}


def test_required_with_is_read_as_a_token_condition_and_its_tokens() -> None:
    assert gen_vocabulary.required_with("\u2014", GEOMETRY) == {}
    assert gen_vocabulary.required_with("`measurement_geometry`: `tube`, `gap`", GEOMETRY) == {
        "measurement_geometry": ["tube", "gap"]
    }


@pytest.mark.parametrize(
    "cell",
    [
        pytest.param("`measurement_geometry`: `pipe`", id="a_token_not_the_conditions"),
        pytest.param("`temperature`: `tube`", id="not_a_token_condition"),
        pytest.param("measurement_geometry: `tube`", id="an_unquoted_condition"),
        pytest.param("`measurement_geometry`: tube", id="an_unquoted_token"),
        pytest.param("", id="empty"),
    ],
)
def test_required_with_of_another_form_is_refused(cell: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.required_with(cell, GEOMETRY)


def test_a_list_in_prose_is_read_between_its_anchors() -> None:
    text = "the levels are `donor`, `lot` (a batch, `x`) [PR-156], `specimen` and `test` (rule 10)"
    assert gen_vocabulary.listed(text, "the levels are ", " (rule 10)") == [
        "donor",
        "lot",
        "specimen",
        "test",
    ]
    assert gen_vocabulary.listed("`a`, or `b` where it applies", None, " where") == ["a", "b"]


@pytest.mark.parametrize(
    ("text", "after", "before"),
    [
        pytest.param("are `a`, b or `c`.", "are ", ".", id="an_unquoted_token"),
        pytest.param("are `a`; `b`.", "are ", ".", id="another_separator"),
        pytest.param("are `a` and `B`.", "are ", ".", id="a_capital"),
        pytest.param("are `a`. are `b`.", "are ", ".", id="an_anchor_twice"),
        pytest.param("is `a`.", "are ", ".", id="no_anchor"),
        pytest.param("are `a`", "are ", ".", id="no_end"),
        pytest.param("are .", "are ", ".", id="no_token"),
    ],
)
def test_a_list_in_prose_of_another_form_is_refused(text: str, after: str, before: str) -> None:
    with pytest.raises(TableError):
        gen_vocabulary.listed(text, after, before)


def test_a_token_listed_twice_is_refused() -> None:
    with pytest.raises(TableError):
        gen_vocabulary.enumeration(["mean", "median", "mean"])


@pytest.mark.parametrize(
    ("document", "old", "new"),
    [
        pytest.param(
            "uncertainty.md", "`median`, `single_measurement`", "median, `single_measurement`", id="central"
        ),
        pytest.param("uncertainty.md", "the levels are `donor`", "the levels: `donor`", id="level_anchor"),
        pytest.param(
            "uncertainty.md",
            "- `basis` is `reported_uncertainty`",
            "- `basis`: `reported_uncertainty`",
            id="uncertainty",
        ),
        pytest.param("provenance.md", "`set_point` (the value", "set_point (the value", id="set_or_measured"),
        pytest.param(
            "provenance.md",
            "`measurement_geometry`: `tube`, `gap`",
            "`measurement_geometry`: `pipe`",
            id="required_with",
        ),
        pytest.param(
            "record_format.md",
            "`mole_fraction`. `component`",
            "mole fraction. `component`",
            id="composition_basis",
        ),
        pytest.param("record_format.md", "| 1 | `H` `He` |", "| 1 | `H` |", id="element_count"),
        pytest.param(
            "record_format.md",
            "`component` is `element:<symbol>`",
            "`component` is `<symbol>`",
            id="component_form",
        ),
        pytest.param(
            "read_side_contract.md", "| `at_edge` | not_met | 11 |", "| `at_edge` | not_met | 14 |", id="step"
        ),
        pytest.param(
            "declarations.md",
            "| unknown | a `waiver` naming that code |",
            "| unknown | a `waiver` that names that code |",
            id="a_phrasing_of_what_covers_not_known",
        ),
        pytest.param(
            "declarations.md",
            "| a specimen difference | (not a status) |",
            "| a difference of specimens | (not a status) |",
            id="a_reason_phrase_not_known",
        ),
        pytest.param(
            "declarations.md",
            "| `no_pick` | unknown | a `pick` only |",
            "| `no_pick`, `no_picks` | unknown | a `pick` only |",
            id="a_code_no_reason_has",
        ),
        pytest.param(
            "declarations.md",
            "| `range_unstated`, `outside_coverage` | unknown | an `extrapolation` only |",
            "| `range_unstated`, for a value read from an interval, or a vector read from a parameter set "
            "with none | unknown | an `extrapolation` only |",
            id="a_qualifier_its_rule_does_not_hold",
        ),
        pytest.param(
            "declarations.md",
            "| `range_unstated`, `outside_coverage` | unknown |",
            "| `range_unstated`, `outside_coverage`, `outside_range` | unknown |",
            id="a_code_of_another_status",
        ),
        pytest.param(
            "declarations.md",
            "| `condition_unstated`, `condition_unchecked`, `condition_uncertain` | unknown |",
            "| `condition_unstated`, `condition_unchecked`, `condition_uncertain`, "
            "`condition_unknown_name` | unknown |",
            id="a_reason_never_accepted_listed",
        ),
        pytest.param(
            "declarations.md",
            "never accepted, `condition_unknown_name` among them",
            "never accepted, condition_unknown_name among them",
            id="never_accepted_not_a_code",
        ),
        pytest.param(
            "declarations.md",
            "| a specimen difference | (not a status) |",
            "| a specimen difference | unknown |",
            id="a_specimen_difference_given_a_status",
        ),
        pytest.param("read_side_contract.md", "from this list only: ", "from this list: ", id="labels"),
        pytest.param(
            "record_format.md",
            "| `materica.fluid.newtonian.v1` on a constant,",
            "| `materica.fluid.newtonian.v1` or `materica.fluid.power_law.v1` on a constant,",
            id="a_second_label",
        ),
        pytest.param(
            "record_format.md",
            "| `materica.fluid.newtonian.v1` on a constant,",
            "| `Materica Fluid (Newtonian)` on a constant,",
            id="a_label_that_is_no_family_identifier",
        ),
        pytest.param(
            "record_format.md",
            "on a constant, or on a table whose axis is not `shear_rate`",
            "on a constant, or on an interval",
            id="where_a_label_goes",
        ),
        pytest.param(
            "provenance.md",
            "| `temperature` | numeric | `K` |",
            "| `temperature` | numeric | `K` or `Cel` |",
            id="a_second_unit",
        ),
        pytest.param(
            "provenance.md",
            "`apparent` (the whole specimen, pores included)",
            "`apparent` (the whole specimen, pores included; also `bulk_apparent`)",
            id="a_token_in_a_parenthetical",
        ),
        pytest.param(
            "read_side_contract.md",
            "| `no_pick` | unknown | 7 |",
            "| `absent` | not_met | 9 | a second row | this document 3 |\n| `no_pick` | unknown | 7 |",
            id="a_reason_listed_twice",
        ),
        pytest.param(
            "provenance.md",
            "| `shear_rate` | numeric | `1/s` | \u2014 |",
            "| `shear_rate` | numeric | `1/s` | \u2014 |\n| `temperature` | numeric | `Cel` | \u2014 |",
            id="a_condition_listed_twice",
        ),
    ],
)
def test_a_list_the_specification_rewords_stops_the_generator(
    tmp_path: Path, document: str, old: str, new: str
) -> None:
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    path = specification / document
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    with pytest.raises(TableError):
        gen_vocabulary.generate(specification)


def test_a_labels_axis_changed_in_the_text_changes_the_vocabulary(tmp_path: Path) -> None:
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    path = specification / "record_format.md"
    text = path.read_text(encoding="utf-8")
    old = "whose axis is not `shear_rate`"
    assert old in text
    path.write_text(text.replace(old, "whose axis is not `temperature`", 1), encoding="utf-8")
    fields = json.loads(gen_vocabulary.generate(specification)["fields.json"])["fields"]
    assert fields["fluid.dynamic_viscosity"]["label_not_on_axis"] == "temperature"
    assert fields["magnetic.volume_susceptibility"]["label_not_on_axis"] == "magnetic_flux_density"
    assert "label_not_on_axis" not in fields["bulk.density"]


@pytest.mark.parametrize(
    ("document", "old", "new", "file", "definition", "tokens"),
    [
        pytest.param(
            "uncertainty.md",
            "`reproducibility`, or",
            "`reproducibility`, `field_repeatability`, or",
            "statistics.json",
            "precision_conditions",
            ["repeatability", "intermediate", "reproducibility", "field_repeatability"],
            id="statistics",
        ),
        pytest.param(
            "record_format.md",
            "`stated_bound`. [RC-009]",
            "`stated_bound` or `tolerance_band`. [RC-009]",
            "forms.json",
            "interval_basis",
            ["reported_range", "proxy_range", "specification_limits", "stated_bound", "tolerance_band"],
            id="forms",
        ),
    ],
)
def test_a_token_added_to_a_list_in_prose_is_read_with_the_others(
    tmp_path: Path, document: str, old: str, new: str, file: str, definition: str, tokens: list[str]
) -> None:
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    path = specification / document
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    assert json.loads(gen_vocabulary.generate(specification)[file])["$defs"][definition]["enum"] == tokens


WRITER: dict[str, Json] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.org/writer.json",
    "title": "Record",
    "type": "object",
    "properties": {
        "id": {"$ref": "#/$defs/id"},
        "kind": {"enum": ["a", "b"]},
        "nested": {
            "type": "object",
            "properties": {"id": {"$ref": "#/$defs/id"}},
            "additionalProperties": False,
        },
        "field": {"$ref": "#/$defs/value_field"},
    },
    "additionalProperties": False,
    "$defs": {
        "id": {"type": "string", "pattern": "^[a-z]+(?![\\s\\S])"},
        "value_field": {
            "type": "object",
            "allOf": [{"$ref": "#/$defs/common"}],
            "required": ["value", "basis", "note"],
            "properties": {
                "value": {"type": "number"},
                "basis": {"$ref": "vocabulary/tokens.json#/$defs/basis"},
                "note": {"x-materica-write-only": True, "$ref": "#/$defs/note"},
            },
            "if": {"required": ["value"], "properties": {"value": {"const": 0}}},
            "then": {"required": ["note"]},
            "unevaluatedProperties": False,
        },
        "common": {
            "type": "object",
            "properties": {"unit": {"type": "string", "pattern": "^[a-z]+(?![\\s\\S])"}},
        },
        "note": {"type": "object", "properties": {"text": {"type": "string"}}},
        "specimen": {
            "type": "object",
            "properties": {"fact": {"$ref": "#/$defs/id"}},
            "additionalProperties": False,
        },
        "unused": {"type": "string"},
    },
}
VOCABULARY: dict[str, Json] = {
    "tokens.json": {"$defs": {"basis": {"enum": ["stated", "inferred"]}, "count": {"type": "integer"}}}
}


def test_the_reader_schema_opens_the_writers_where_a_reader_is_open() -> None:
    reader = reader_schema(WRITER, VOCABULARY)
    assert reader["properties"] == {
        "id": {"type": "string", "pattern": "^[a-z]+(?![\\s\\S])"},
        "kind": {"type": "string"},
        "nested": {"type": "object", "properties": {"id": {"type": "string"}}},
        "field": True,
    }
    assert "additionalProperties" not in reader


def test_the_reader_schemas_defs_hold_the_shapes_a_read_checks_without_its_write_only_members() -> None:
    """The value field and the specimen, with what they refer to and nothing else; the member marked
    write-only accepts anything and is required nowhere, the condition that required it gone with it."""
    assert reader_schema(WRITER, VOCABULARY)["$defs"] == {
        "id": {"type": "string"},
        "value_field": {
            "type": "object",
            "allOf": [{"$ref": "#/$defs/common"}],
            "required": ["value", "basis"],
            "properties": {"value": {"type": "number"}, "basis": {"type": "string"}, "note": True},
        },
        "common": {"type": "object", "properties": {"unit": {"type": "string"}}},
        "specimen": {"type": "object", "properties": {"fact": {"$ref": "#/$defs/id"}}},
    }


def changed(place: str, value: Json) -> dict[str, Json]:
    """WRITER with the subschema at `place`, a path of names through it, replaced by `value`, or removed where
    `value` is None."""
    writer: dict[str, Json] = json.loads(json.dumps(WRITER))
    *path, last = place.split("/")
    node = writer
    for name in path:
        inner = node[name]
        assert isinstance(inner, dict)
        node = inner
    if value is None:
        del node[last]
    else:
        node[last] = value
    return writer


# Marks of a member checked at read only under a condition, each of a form the generator does not take.
MALFORMED_MARKS: list[tuple[str, Json]] = [
    ("empty", {"unless": {}}),
    ("a_number", {"unless": {"basis": 1}}),
    ("a_list", {"unless": [{"basis": "stated"}]}),
    ("beside_another_member", {"unless": {"basis": "stated"}, "also": True}),
    ("another_keyword", {"when": {"basis": "stated"}}),
    ("on_no_member", {"unless": {"nowhere": "stated"}}),
]


@pytest.mark.parametrize(
    ("place", "value"),
    [
        pytest.param(
            "properties/id", {"type": "string", "pattern": "^[a-z]+$"}, id="pattern_ending_with_dollar"
        ),
        pytest.param(
            "properties/id", {"type": "string", "pattern": "[a-z]+(?![\\s\\S])"}, id="pattern_without_caret"
        ),
        pytest.param("properties/kind", {"enum": ["a", 1]}, id="enumeration_of_a_number"),
        pytest.param("properties/kind", {"$ref": "#/$defs/nowhere"}, id="reference_to_nothing"),
        pytest.param(
            "properties/kind", {"$ref": "#/$defs/id", "minLength": 1}, id="reference_beside_a_keyword"
        ),
        pytest.param("properties/kind", {"$ref": "other.json#/$defs/id"}, id="reference_to_another_file"),
        pytest.param(
            "$defs/value_field/properties/basis",
            {"$ref": "vocabulary/tokens.json#/$defs/count"},
            id="vocabulary_reference_to_no_enumeration",
        ),
        pytest.param(
            "$defs/value_field/properties/basis",
            {"$ref": "vocabulary/other.json#/$defs/basis"},
            id="vocabulary_reference_to_no_file",
        ),
        pytest.param(
            "$defs/value_field/not",
            {"properties": {"basis": {"enum": ["stated"]}}},
            id="enumeration_under_not",
        ),
        pytest.param(
            "$defs/value_field/properties/note",
            {"x-materica-write-only": False, "$ref": "#/$defs/note"},
            id="write_only_false",
        ),
        pytest.param(
            "$defs/value_field/properties/note",
            {"x-materica-write-only": None, "$ref": "#/$defs/note"},
            id="write_only_null",
        ),
        *(
            pytest.param(
                "$defs/value_field/properties/note",
                {"x-materica-write-only": mark, "$ref": "#/$defs/note"},
                id=f"write_only_unless_{name}",
            )
            for name, mark in MALFORMED_MARKS
        ),
        pytest.param(
            "$defs/value_field/properties/value",
            {"x-materica-write-only": {"unless": {"note": "stated"}}, "type": "number"},
            id="write_only_unless_on_a_member_not_checked",
        ),
        pytest.param("$defs/common/x-materica-write-only", True, id="write_only_outside_properties"),
        pytest.param("$defs/specimen", None, id="no_specimen"),
    ],
)
def test_a_writer_schema_the_script_cannot_open_is_refused(place: str, value: Json) -> None:
    with pytest.raises(SchemaError):
        reader_schema(changed(place, value), VOCABULARY)


def changes(*places: tuple[str, Json]) -> dict[str, Json]:
    """WRITER with the subschema at each place, a path of names through it, set to its value."""
    writer: dict[str, Json] = json.loads(json.dumps(WRITER))
    for place, value in places:
        *path, last = place.split("/")
        node = writer
        for name in path:
            inner = node[name]
            assert isinstance(inner, dict)
            node = inner
        node[last] = value
    return writer


@pytest.mark.parametrize(
    "places",
    [
        pytest.param(
            [("$defs/value_field/if", {"properties": {"basis": {"enum": ["stated"]}}})],
            id="an_enumeration_under_if",
        ),
        pytest.param(
            [
                (
                    "$defs/value_field/if",
                    {"properties": {"basis": {"$ref": "vocabulary/tokens.json#/$defs/basis"}}},
                )
            ],
            id="a_vocabulary_list_under_if",
        ),
        pytest.param(
            [
                ("$defs/kinds", {"enum": ["stated"]}),
                ("$defs/value_field/if", {"properties": {"basis": {"$ref": "#/$defs/kinds"}}}),
            ],
            id="a_definitions_enumeration_under_if",
        ),
        pytest.param(
            [
                ("$defs/value_field/not", {"properties": {"basis": {"$ref": "#/$defs/kinds"}}}),
                ("$defs/kinds", {"enum": ["a"]}),
            ],
            id="a_definitions_enumeration_under_not",
        ),
        pytest.param(
            [("$defs/value_field/if", {"properties": {"unit": {"pattern": "^[a-z]+(?![\\s\\S])"}}})],
            id="a_pattern_under_if",
        ),
        pytest.param(
            [("$defs/value_field/if", {"properties": {"unit": {"$ref": "#/$defs/id"}}})],
            id="a_definitions_pattern_under_if",
        ),
        pytest.param(
            [
                (
                    "$defs/value_field/not",
                    {"properties": {"note": {"type": "object", "additionalProperties": False}}},
                )
            ],
            id="a_closed_object_under_not",
        ),
        pytest.param(
            [("$defs/value_field/if", {"properties": {"field": {"$ref": "#/$defs/specimen"}}})],
            id="a_shape_never_applied_under_if",
        ),
        pytest.param(
            [("$defs/value_field/patternProperties", {"^x_": {"$ref": "#/$defs/note"}})],
            id="patternProperties",
        ),
        pytest.param(
            [
                (
                    "$defs/value_field/dependentSchemas",
                    {"value": {"properties": {"basis": {"enum": ["stated"]}}}},
                )
            ],
            id="dependentSchemas",
        ),
        pytest.param([("$defs/value_field/dependentRequired", {"value": ["basis"]})], id="dependentRequired"),
        pytest.param([("$defs/common/minLength", 1)], id="minLength"),
        pytest.param(
            [
                (
                    "$defs/value_field/if",
                    {
                        "properties": {
                            "value": {
                                "properties": {
                                    "kind": {"type": "string"},
                                    "detail": {"x-materica-write-only": {"unless": {"kind": "a"}}},
                                }
                            }
                        }
                    },
                )
            ],
            id="a_member_checked_under_a_condition_under_if",
        ),
    ],
)
def test_what_opening_would_turn_around_or_copy_unopened_is_refused(places: list[tuple[str, Json]]) -> None:
    """The review's probes: a `$ref` under `if` that reaches an enumeration was opened, turning the condition
    around, and a keyword the script does not open was copied, closed lists and `$ref`s with it. Each `if`
    here has a `then` requiring a member a read checks, so that the reader keeps the condition."""
    with pytest.raises(SchemaError):
        reader_schema(changes(*places, ("$defs/value_field/then", {"required": ["basis"]})), VOCABULARY)


# A member of the value field that refers to a definition with a member a read does not check.
PART: tuple[tuple[str, Json], ...] = (
    ("$defs/value_field/properties/part", {"$ref": "#/$defs/part"}),
    (
        "$defs/part",
        {
            "type": "object",
            "properties": {
                "secret": {"x-materica-write-only": True, "type": "string"},
                "open": {"type": "string"},
            },
        },
    ),
)
WHEN_ZERO: Json = {"required": ["value"], "properties": {"value": {"const": 0}}}
COMMON: Json = {"$ref": "#/$defs/common"}


def reader_value_field(*places: tuple[str, Json]) -> dict[str, Json]:
    definitions = reader_schema(changes(*PART, *places), VOCABULARY)["$defs"]
    assert isinstance(definitions, dict)
    value_field = definitions["value_field"]
    assert isinstance(value_field, dict)
    return value_field


@pytest.mark.parametrize(
    "places",
    [
        pytest.param(
            [
                (
                    "$defs/value_field/if",
                    {"properties": {"part": {"properties": {"secret": {"const": "x"}}}}},
                ),
                ("$defs/value_field/then", {"required": ["basis"]}),
            ],
            id="an_if_testing_an_unchecked_member",
        ),
        pytest.param(
            [
                ("$defs/value_field/if", WHEN_ZERO),
                ("$defs/value_field/then", {"properties": {"part": {"required": ["secret"]}}}),
            ],
            id="a_then_requiring_only_an_unchecked_member",
        ),
        pytest.param(
            [("$defs/value_field/allOf", [COMMON, {"properties": {"part": {"required": ["secret"]}}}])],
            id="a_conjunct_requiring_only_an_unchecked_member",
        ),
    ],
)
def test_a_rule_a_read_cannot_apply_is_left_out_of_the_reader(places: list[tuple[str, Json]]) -> None:
    """A read does not check a member marked write-only, however deep, so it applies no rule that tests one or
    reaches only such members (provenance.md section 2 item 6: the record checks')."""
    value_field = reader_value_field(*places)
    assert "if" not in value_field
    assert value_field["allOf"] == [{"$ref": "#/$defs/common"}]


@pytest.mark.parametrize(
    "places",
    [
        pytest.param(
            [
                ("$defs/value_field/if", WHEN_ZERO),
                ("$defs/value_field/then", {"properties": {"part": {"required": ["secret", "open"]}}}),
            ],
            id="a_then",
        ),
        pytest.param(
            [
                (
                    "$defs/value_field/allOf",
                    [COMMON, {"properties": {"part": {"required": ["secret", "open"]}}}],
                )
            ],
            id="a_conjunct",
        ),
    ],
)
def test_a_rule_reaching_checked_and_unchecked_members_is_refused(places: list[tuple[str, Json]]) -> None:
    """Keeping it would apply the unchecked part, and leaving it out would drop the checked one."""
    with pytest.raises(SchemaError, match="reaches members a read checks and others"):
        reader_value_field(*places)


def test_a_rule_reaching_a_checked_member_through_a_definition_is_kept() -> None:
    """The control: `open` is checked, so the condition stands in the reader."""
    then: Json = {"properties": {"part": {"required": ["open"]}}}
    value_field = reader_value_field(("$defs/value_field/if", WHEN_ZERO), ("$defs/value_field/then", then))
    assert (value_field["if"], value_field["then"]) == (WHEN_ZERO, then)


def test_a_condition_on_a_constant_is_kept_as_written() -> None:
    """`const` is not opened, so a condition testing one keeps its meaning in the reader."""
    condition: Json = {"required": ["value"], "properties": {"value": {"const": 1}}}
    writer = changes(("$defs/value_field/if", condition), ("$defs/value_field/then", {"required": ["basis"]}))
    definitions = reader_schema(writer, VOCABULARY)["$defs"]
    assert isinstance(definitions, dict)
    value_field = definitions["value_field"]
    assert isinstance(value_field, dict)
    assert (value_field["if"], value_field["then"]) == (condition, {"required": ["basis"]})


# A member of the value field a read checks only where its `basis` is `stated`, as a read checks a
# `derivation` for origin `derived` alone (provenance.md section 2 item 6).
STATED: Json = {"required": ["basis"], "properties": {"basis": {"const": "stated"}}}
DETAIL: tuple[tuple[str, Json], ...] = (
    (
        "$defs/value_field/properties/detail",
        {"x-materica-write-only": {"unless": {"basis": "stated"}}, "$ref": "#/$defs/detail"},
    ),
    ("$defs/detail", {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}}),
)
DETAIL_WHERE_STATED: Json = {"if": STATED, "then": {"properties": {"detail": {"$ref": "#/$defs/detail"}}}}


def reader_takes(writer: dict[str, Json], field: Json) -> bool:
    """Whether the value field of the reader `$defs` `writer` gives takes `field`."""
    reader = {"$defs": reader_schema(writer, VOCABULARY)["$defs"], "$ref": "#/$defs/value_field"}
    return agreed(reader)(field)


def test_a_member_a_read_checks_under_a_condition_is_checked_there_alone() -> None:
    """Its shape stands in a conjunct under the condition; elsewhere it accepts anything, as a member marked
    write-only does."""
    value_field = reader_value_field(*DETAIL)
    assert value_field["properties"] == {
        "value": {"type": "number"},
        "basis": {"type": "string"},
        "note": True,
        "part": {"$ref": "#/$defs/part"},
        "detail": True,
    }
    assert value_field["allOf"] == [COMMON, DETAIL_WHERE_STATED]
    writer = changes(*DETAIL)
    broken: dict[str, Json] = {"value": 1, "basis": "inferred", "detail": {"text": 1}}
    assert reader_takes(writer, broken)
    assert not reader_takes(writer, {**broken, "basis": "stated"})
    assert reader_takes(writer, {**broken, "basis": "stated", "detail": {"text": "a"}})


def test_a_member_a_read_checks_under_a_condition_is_required_there_alone() -> None:
    value_field = reader_value_field(*DETAIL, ("$defs/value_field/required", ["value", "basis", "detail"]))
    assert value_field["required"] == ["value", "basis"]
    conjunct: Json = {
        "if": STATED,
        "then": {"properties": {"detail": {"$ref": "#/$defs/detail"}}, "required": ["detail"]},
    }
    assert value_field["allOf"] == [COMMON, conjunct]


def test_a_rule_under_exactly_its_condition_takes_it_as_checked() -> None:
    """The control for the next test: the condition stands in the reader, as `derived`'s requiring a
    derivation does."""
    value_field = reader_value_field(
        *DETAIL, ("$defs/value_field/if", STATED), ("$defs/value_field/then", {"required": ["detail"]})
    )
    assert (value_field["if"], value_field["then"]) == (STATED, {"required": ["detail"]})


@pytest.mark.parametrize(
    "places",
    [
        pytest.param(
            [("$defs/value_field/if", WHEN_ZERO), ("$defs/value_field/then", {"required": ["detail"]})],
            id="a_then_of_another_condition",
        ),
        pytest.param(
            [("$defs/value_field/if", STATED), ("$defs/value_field/else", {"required": ["detail"]})],
            id="the_else_of_its_own_condition",
        ),
        pytest.param(
            [("$defs/value_field/allOf", [COMMON, {"required": ["detail"]}])],
            id="a_conjunct",
        ),
        pytest.param(
            [
                ("$defs/value_field/if", {"properties": {"detail": {"required": ["text"]}}}),
                ("$defs/value_field/then", {"required": ["basis"]}),
            ],
            id="an_if_testing_it",
        ),
    ],
)
def test_a_rule_outside_its_condition_takes_it_as_unchecked(places: list[tuple[str, Json]]) -> None:
    value_field = reader_value_field(*DETAIL, *places)
    assert not {"if", "then", "else"} & set(value_field)
    assert value_field["allOf"] == [COMMON, DETAIL_WHERE_STATED]


@pytest.mark.parametrize(
    "places",
    [
        pytest.param(
            [
                ("$defs/value_field/if", WHEN_ZERO),
                ("$defs/value_field/then", {"required": ["detail", "value"]}),
            ],
            id="a_then",
        ),
        pytest.param(
            [("$defs/value_field/allOf", [COMMON, {"required": ["detail", "value"]}])],
            id="a_conjunct",
        ),
    ],
)
def test_a_rule_outside_its_condition_reaching_it_and_a_checked_member_is_refused(
    places: list[tuple[str, Json]],
) -> None:
    with pytest.raises(SchemaError, match="reaches members a read checks and others"):
        reader_value_field(*DETAIL, *places)


def test_the_reader_schema_check_fails_when_it_differs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = tmp_path / "record.reader.json"
    reader.write_text(gen_reader_schema.generate(), encoding="utf-8")
    monkeypatch.setattr(gen_reader_schema, "READER", reader)
    assert gen_reader_schema.main(["--check"]) == 0
    reader.write_text(
        reader.read_text(encoding="utf-8").replace('"pattern"', '"pattern "', 1), encoding="utf-8"
    )
    assert gen_reader_schema.main(["--check"]) == 1


def test_only_the_shapes_of_a_result_are_read_only() -> None:
    module = (
        '"""Shapes."""\n\nfrom typing import TypedDict\n\n\nclass Reason(TypedDict):\n    code: str\n\n\n'
        "class ReadRequest(TypedDict):\n    field: str\n"
    )
    stub = gen_shapes.read_only(module)
    assert "from typing_extensions import ReadOnly\nfrom typing import TypedDict" in stub
    assert "    code: ReadOnly[str]" in stub
    assert "    field: str" in stub


def test_a_functional_typed_dict_goes_last_with_its_references_to_itself_quoted() -> None:
    """A shape with a member named by a Python keyword is written as a call, whose members are evaluated on
    import: every name it uses must be defined above it."""
    module = (
        "\n\nShape = TypedDict('Shape', {\n    'import': Part,\n    'more': dict[str, Shape],})\n"
        "\n\nclass Part(TypedDict):\n    text: str\n"
    )
    moved = gen_shapes.functional_last(module)
    assert moved.index("class Part") < moved.index("Shape = TypedDict('Shape'")
    assert "'more': dict[str, 'Shape']" in moved
    assert "'import': Part" in moved


def test_a_long_docstring_line_is_wrapped_and_code_is_not() -> None:
    long = "word " * 30
    text = gen_shapes.wrapped(f'class A:\n    """\n    {long}\n    """\n\n    member: "{long}"\n')
    assert all(len(line) <= 110 for line in text.splitlines() if not line.startswith("    member"))
    assert f'    member: "{long}"' in text


DENSITY = "| `bulk.density` | `kg/m3` | constant, table, interval | `temperature`, `density_kind` | none |"
REMANENCE = (
    "| `magnetic.remanence` | `T` | constant, interval "
    "| `temperature`, `specimen_shape`, `test_method` | none |"
)
VISCOSITY_LABEL = (
    "| `materica.fluid.newtonian.v1` on a constant, or on a table whose axis is not `shear_rate` |"
)
SPECIMEN_SIZE = "| `specimen_size` | numeric | `m`: the specimen's characteristic dimension"
BULK_FIELDS = ("sections", "properties", "bulk", "properties", "fields", "propertyNames", "enum")
MAGNETIC_FIELDS = ("sections", "properties", "magnetic", "properties", "fields", "propertyNames", "enum")


def condition_unit(unit: str) -> dict[str, Json]:
    return {
        "properties": {
            "unit": {"const": unit},
            "plus_minus": {"items": {"properties": {"unit": {"const": unit}}}},
        }
    }


@pytest.mark.parametrize(
    ("document", "old", "new", "file", "expected"),
    [
        pytest.param(
            "record_format.md",
            DENSITY,
            DENSITY + "\n| `bulk.porosity` | `1` | constant | `temperature` | none |",
            "fields.json",
            {
                BULK_FIELDS: ["density", "porosity", "elemental_composition"],
                ("replaces", "properties", "bulk.porosity"): {"$ref": "#/$defs/bulk.porosity"},
                ("bulk.porosity",): {
                    "properties": {
                        "form": {"enum": ["constant"]},
                        "unit": {"const": "1"},
                        "label": False,
                        "alternatives": {"items": {"$ref": "#/$defs/bulk.porosity"}},
                    }
                },
            },
            id="a_field_row_added",
        ),
        pytest.param(
            "record_format.md",
            REMANENCE + "\n",
            "",
            "fields.json",
            {
                MAGNETIC_FIELDS: ["saturation_magnetisation", "volume_susceptibility"],
                ("replaces", "properties", "magnetic.remanence"): None,
                ("magnetic.remanence",): None,
            },
            id="a_field_row_removed",
        ),
        pytest.param(
            "record_format.md",
            "| `kg/m3` | constant, table, interval |",
            "| `kg/m3` | constant, table, interval, power_law |",
            "fields.json",
            {
                ("bulk.density", "properties", "form"): {
                    "enum": ["constant", "table", "interval", "power_law"]
                }
            },
            id="a_form_added",
        ),
        pytest.param(
            "record_format.md",
            "| `kg/m3` | constant, table, interval |",
            "| `kg/m3` | constant, interval |",
            "fields.json",
            {("bulk.density", "properties", "form"): {"enum": ["constant", "interval"]}},
            id="a_form_removed",
        ),
        pytest.param(
            "record_format.md",
            "| `bulk.density` | `kg/m3` |",
            "| `bulk.density` | `g/cm3` |",
            "fields.json",
            {("bulk.density", "properties", "unit"): {"const": "g/cm3"}},
            id="a_unit_changed",
        ),
        pytest.param(
            "record_format.md",
            REMANENCE,
            REMANENCE.removesuffix(" none |") + " `materica.magnetic.remanent.v1` on a constant |",
            "fields.json",
            {("magnetic.remanence", "properties", "label"): {"const": "materica.magnetic.remanent.v1"}},
            id="a_label_added",
        ),
        pytest.param(
            "record_format.md",
            VISCOSITY_LABEL,
            "| none |",
            "fields.json",
            {("fluid.dynamic_viscosity", "properties", "label"): False},
            id="a_label_removed",
        ),
        pytest.param(
            "record_format.md",
            "composition (basis `mass_fraction`)",
            "composition (basis `mass_fraction`, `mole_fraction`)",
            "fields.json",
            {
                ("bulk.elemental_composition", "properties", "composition"): {
                    "properties": {"basis": {"enum": ["mass_fraction", "mole_fraction"]}}
                }
            },
            id="a_basis_added",
        ),
        pytest.param(
            "provenance.md",
            "| `temperature` | numeric | `K` | — |",
            "| `temperature` | numeric | `K` | — |\n| `pressure` | numeric | `Pa` | — |",
            "conditions.json",
            {("units", "properties", "pressure"): condition_unit("Pa")},
            id="a_numeric_condition_added",
        ),
        pytest.param(
            "provenance.md",
            "| `shear_rate` | numeric | `1/s` | \u2014 |\n",
            "",
            "conditions.json",
            {("units", "properties", "shear_rate"): None},
            id="a_numeric_condition_removed",
        ),
        pytest.param(
            "provenance.md",
            SPECIMEN_SIZE,
            "| `specimen_size` | token | `small`, `large`",
            "conditions.json",
            {("units", "properties", "specimen_size"): None},
            id="a_condition_no_longer_numeric",
        ),
        pytest.param(
            "provenance.md",
            "| `temperature` | numeric | `K` |",
            "| `temperature` | numeric | `Cel` |",
            "conditions.json",
            {("units", "properties", "temperature"): condition_unit("Cel")},
            id="a_condition_unit_changed",
        ),
        pytest.param(
            "provenance.md",
            '`{"value", "unit": "s", "basis"}` or `{"range": [lo, hi], "unit": "s", "basis"}`',
            '`{"value", "unit": "a", "basis"}` or `{"range": [lo, hi], "unit": "a", "basis"}`',
            "specimen_facts.json",
            {
                ("units", "properties", "donor_age"): {
                    "properties": {"unit": {"$ref": "#/$defs/donor_age_unit"}}
                },
                ("donor_age_unit",): {"enum": ["a"]},
            },
            id="a_facts_unit_changed",
        ),
        pytest.param(
            "provenance.md",
            '`{"value", "unit": "s", "basis"}` |',
            '`{"value", "unit": <text>, "basis"}` |',
            "specimen_facts.json",
            {("units", "properties", "post_mortem_interval"): None, ("post_mortem_interval_unit",): None},
            id="a_facts_unit_no_longer_fixed",
        ),
    ],
)
def test_a_row_changed_in_the_text_changes_the_binding_the_writer_applies(
    tmp_path: Path, document: str, old: str, new: str, file: str, expected: dict[tuple[str, ...], Json]
) -> None:
    """Each list a binding holds (a section's field names, the replaced fields, a field's forms, unit, label
    and bases, a numeric condition's unit, a specimen fact's fixed unit) comes from its row: a row added,
    removed or changed in a copy of the text changes it, and the writer schema, which applies the binding by
    reference, follows."""
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    path = specification / document
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    definitions = json.loads(gen_vocabulary.generate(specification)[file])["$defs"]
    for place, value in expected.items():
        node = definitions
        for name in place[:-1]:
            node = node[name]
        assert node.get(place[-1]) == value, place


@pytest.mark.parametrize(
    ("row", "problem"),
    [
        pytest.param({"Section.field": "`density`"}, "<section>.<field>", id="a_name_with_no_section"),
        pytest.param(
            {"Section.field": "`bulk.density.kind`"}, "<section>.<field>", id="a_name_of_three_parts"
        ),
        pytest.param(
            {"Forms": "interval (basis `stated_bound`)"}, "a composition's only", id="a_basis_elsewhere"
        ),
        pytest.param({"Unit": '`{"value": 1}`'}, "a unit code or a status object", id="a_unit_of_no_form"),
    ],
)
def test_a_field_row_the_binding_cannot_state_is_refused(row: dict[str, str], problem: str) -> None:
    base = {"Section.field": "`bulk.density`", "Unit": "`kg/m3`", "Forms": "constant", "Requires": "none"}
    with pytest.raises(TableError, match=re.escape(problem)):
        gen_vocabulary.fields([{**base, "Label": "none", **row}])


BINDING: Json = {"$ref": "vocabulary/tokens.json#/$defs/bound"}
BOUND: dict[str, Json] = {
    "tokens.json": {
        "$defs": {
            "basis": {"enum": ["stated", "inferred"]},
            "count": {"type": "integer"},
            "bound": {"properties": {"value": {"const": 1}}, "propertyNames": {"enum": ["value"]}},
        }
    }
}


def test_a_binding_of_the_vocabulary_is_left_out_of_the_reader() -> None:
    """A binding binds a field's members to its row, which a read checks in its own steps: the reader schema
    leaves the conjunct out, at its root and in its `$defs`, and the rest of the `allOf` stands."""
    writer = changes(
        ("$defs/value_field/allOf", [COMMON, BINDING]),
        ("properties/nested/allOf", [BINDING]),
    )
    reader = reader_schema(writer, BOUND)
    assert reader == reader_schema(changes(("$defs/value_field/allOf", [COMMON])), BOUND)


@pytest.mark.parametrize(
    "places",
    [
        pytest.param([("properties/kind", BINDING)], id="as_a_members_value"),
        pytest.param([("$defs/value_field/properties/basis", BINDING)], id="as_a_value_in_the_defs"),
        pytest.param(
            [
                ("$defs/value_field/if", {"allOf": [BINDING]}),
                ("$defs/value_field/then", {"required": ["basis"]}),
            ],
            id="under_if",
        ),
    ],
)
def test_a_binding_applied_other_than_as_a_conjunct_is_refused(places: list[tuple[str, Json]]) -> None:
    with pytest.raises(SchemaError):
        reader_schema(changes(*places), BOUND)


def test_the_shapes_leave_the_bindings_out() -> None:
    """A TypedDict cannot narrow a member by the name it sits under: the conjunct goes, the other conjuncts
    and the vocabulary's token lists stay."""
    schema: Json = {"allOf": [{"$ref": "#/$defs/common"}, BINDING], "type": "integer"}
    assert gen_shapes.as_read(schema) == {"allOf": [{"$ref": "#/$defs/common"}], "type": "number"}
    assert gen_shapes.as_read({"allOf": [BINDING]}) == {}
    assert gen_shapes.without_bindings(BOUND["tokens.json"]) == VOCABULARY["tokens.json"]


UBERON = '"uberon": "UBERON:<digits>"'


@pytest.mark.parametrize(
    ("shape", "patterns"),
    [
        ('{"uberon": "UBERON:<digits>", "label": <text>, "basis"}', {"uberon": "^UBERON:[0-9]+(?![\\s\\S])"}),
        ('{"fma": "FMA:<digits>", "basis"}', {"fma": "^FMA:[0-9]+(?![\\s\\S])"}),
        ('{"value", "unit": "s", "basis"}', {}),
    ],
)
def test_an_identifier_a_facts_shape_writes_is_read_as_its_pattern(
    shape: str, patterns: dict[str, str]
) -> None:
    """The writer's pattern of an identifier comes from the form the text writes (maintainer, 2026-10-15)."""
    assert gen_vocabulary.identifier_patterns(shape) == patterns


@pytest.mark.parametrize(
    "written",
    [
        pytest.param('"UBERON_<digits>"', id="another_separator"),
        pytest.param('"UBERON:<number>"', id="another_placeholder"),
        pytest.param('"uberon:<digits>"', id="a_prefix_in_lower_case"),
        pytest.param('"UBERON:<digits>.<digits>"', id="more_after_the_digits"),
        pytest.param('"<digits>"', id="no_prefix"),
    ],
)
def test_an_identifier_of_another_form_stops_the_generator(written: str) -> None:
    """A form the generator would read as another pattern, or drop, stops it."""
    shape = f'`{{"uberon": {written}, "label": <text>, "basis"}}`'
    with pytest.raises(TableError, match="<PREFIX>:<digits>"):
        gen_vocabulary.specimen_facts([{"Name": "`anatomical_site`", "JSON shape": shape}])


@pytest.mark.parametrize(
    ("new", "pattern"),
    [
        pytest.param('"uberon": "FMA:<digits>"', "^FMA:[0-9]+(?![\\s\\S])", id="another_prefix_read"),
        pytest.param('"uberon": "UBERON-<digits>"', None, id="another_form_refused"),
    ],
)
def test_the_identifier_the_text_writes_is_the_pattern_the_writer_takes(
    tmp_path: Path, new: str, pattern: str | None
) -> None:
    """On a copy of the text: a prefix changed changes the pattern in the vocabulary, which the writer
    schema refers to; a form changed in shape stops the generator."""
    specification = copy_tree(tmp_path, gen_vocabulary.SPECIFICATION)
    document = specification / "provenance.md"
    text = document.read_text(encoding="utf-8")
    assert text.count(UBERON) == 1
    document.write_text(text.replace(UBERON, new), encoding="utf-8")
    if pattern is None:
        with pytest.raises(TableError):
            gen_vocabulary.generate(specification)
        return
    facts = json.loads(gen_vocabulary.generate(specification)["specimen_facts.json"])
    assert facts["$defs"]["anatomical_site_uberon"] == {"type": "string", "pattern": pattern}


PATTERNED: dict[str, Json] = {
    "tokens.json": {
        "$defs": {
            "basis": {"enum": ["stated", "inferred"]},
            "identifier": {"type": "string", "pattern": "^ID:[0-9]+(?![\\s\\S])"},
            "unanchored": {"type": "string", "pattern": "ID:[0-9]+"},
        }
    }
}


def test_an_identifiers_pattern_is_any_string_in_the_reader() -> None:
    """Step 8 does not check an identifier's pattern (a record check's, maintainer 2026-10-15): the reader's
    `$defs` take any string there, as they took the writer's pattern written in place."""
    writer = changes(
        ("$defs/value_field/properties/basis", {"$ref": "vocabulary/tokens.json#/$defs/identifier"})
    )
    definitions = reader_schema(writer, PATTERNED)["$defs"]
    assert isinstance(definitions, dict)
    value_field = definitions["value_field"]
    assert isinstance(value_field, dict)
    assert value_field["properties"] == {
        "value": {"type": "number"},
        "basis": {"type": "string"},
        "note": True,
    }
    unanchored = changes(
        ("$defs/value_field/properties/basis", {"$ref": "vocabulary/tokens.json#/$defs/unanchored"})
    )
    with pytest.raises(SchemaError):
        reader_schema(unanchored, PATTERNED)
