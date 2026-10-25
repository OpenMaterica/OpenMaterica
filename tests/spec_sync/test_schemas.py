# SPDX-License-Identifier: Apache-2.0
"""The specification's member tables equal the schemas', and the schemas' token lists the specification's.

Structure is edited in the schemas and checked here against the tables, so that the specification keeps its
prose (CONTRIBUTING, "Changing the schema"). The tokens the vocabulary holds are generated instead, and CI
checks those files with `scripts/gen_vocabulary.py --check`.
"""

import copy
import json
import re
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest

from materica.core.jsonio import JsonValue
from materica.core.vocabulary import VOCABULARY
from scripts.freeze_schema import misplaced_ids
from scripts.gen_vocabulary import SPECIFICATION, codes, only_code, outside_parentheses, table
from tests.spec_sync.schemas import BASE, PACKAGE, RESULT_TWINS, SCHEMA, agreed, as_returned, validator
from tests.verdicts import Json

WRITER = json.loads((SCHEMA / "record.writer.json").read_text(encoding="utf-8"))
CASE = json.loads((SCHEMA / "case.json").read_text(encoding="utf-8"))
REQUEST = json.loads((SCHEMA / "read_request.json").read_text(encoding="utf-8"))
RESULT = json.loads((SCHEMA / "read_result.json").read_text(encoding="utf-8"))
PAGE_TEXT = json.loads((SCHEMA / "page_text.json").read_text(encoding="utf-8"))


def document(name: str) -> str:
    return (SPECIFICATION / name).read_text(encoding="utf-8")


def test_the_envelope_table_is_the_writer_schemas() -> None:
    rows = table(document("record_format.md"), "## 2. The envelope")
    assert [only_code(row["Member"]) for row in rows] == list(WRITER["properties"])
    assert [only_code(row["Member"]) for row in rows if row["Required"] == "yes"] == WRITER["required"]


def page_text_table_problems(schema: dict[str, JsonValue]) -> list[str]:
    """Where `page_text.md` section 1's member table differs from the page-text schema: the members in order,
    those required, and the members of a page, of an element entry and of `copy` that its contents name."""
    rows = table(document("page_text.md"), "## 1. Page-text documents")
    members = [name for row in rows for name in codes(row["Member"])]
    required = [name for row in rows if row["Required"] == "yes" for name in codes(row["Member"])]
    definitions = cast(dict[str, dict[str, JsonValue]], schema["$defs"])
    properties = cast(dict[str, dict[str, JsonValue]], schema["properties"])
    named = {codes(row["Member"])[0]: codes(row["Contents"])[0] for row in rows if codes(row["Contents"])}
    shapes = {
        "pages": definitions["page"],
        "text": definitions["element"],
        "copy": properties["copy"],
    }
    problems: list[str] = []
    if members != list(properties):
        problems.append(f"members {members}, the schema's {list(properties)}")
    if required != schema["required"]:
        problems.append(f"required {required}, the schema's {schema['required']}")
    for member, shape in shapes.items():
        listed = json.loads("[" + named[member].strip("{}") + "]")
        held = [name for name in cast(dict[str, JsonValue], shape["properties"]) if name != "cell_columns"]
        if listed != held or cast(list[str], shape["required"]) != listed:
            problems.append(f"{member}: the table names {listed}, the schema holds {held}")
    return problems


def test_the_page_text_table_is_the_page_text_schemas() -> None:
    assert page_text_table_problems(PAGE_TEXT) == []


def test_a_page_text_member_left_out_of_the_schema_is_found() -> None:
    schema = copy.deepcopy(PAGE_TEXT)
    del schema["$defs"]["page"]["properties"]["furniture"]
    schema["required"].remove("readings")
    assert len(page_text_table_problems(schema)) == 2


# The record-check suite's fixtures against the schemas a page-text document and a place are written to
# (`page_text.json`; `record.writer.json`'s `copy`, whose place a curation tool writes): for each shape those
# schemas state (the two kinds, a page's text, the copy hash's and an element path's patterns, a place's two
# members together, a span's two kinds), an instance taken and one refused.
FIXTURES = PACKAGE / "data" / "conformance" / "record_checks" / "inputs"
EVIDENCE = ("body", "sections", "bulk", "fields", "density", "provenance", "evidence")
DOCUMENTS_TAKEN = (
    "page_text_pdf.json",
    "page_text_xml.json",
    "page_text_xml_typography.json",
    "page_text_pdf_tab.json",
)
DOCUMENTS_REFUSED = (
    "page_text_pdf_members_of_both_kinds.json",
    "page_text_pdf_carriage_return.json",
    "page_text_pdf_copy_hash_bare.json",
    "page_text_xml_path_without_a_position.json",
)
PLACES_TAKEN = ("rc032_quote_at_its_place.json", "rc032_xml_quote_at_its_place.json")
PLACES_REFUSED = (
    "rc222_span_with_page_and_element.json",
    "rc222_boxes_beside_an_element.json",
    "rc222_page_text_without_spans.json",
    "rc031_copy_hash_bare.json",
)


def fixture(name: str) -> JsonValue:
    return cast(JsonValue, json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def evidence_copy(name: str) -> JsonValue:
    found = fixture(name)
    for member in EVIDENCE:
        found = cast(dict[str, JsonValue], found)[member]
    return cast(dict[str, JsonValue], found)["copy"]


def misjudged_fixtures(page_text: Json, writer: Json) -> set[str]:
    """The fixtures judged otherwise than above, with `page_text` and `writer` in place of the package's
    files: a document by `page_text.json`, and a record's place by the writer's `copy`."""
    files = (page_text, writer)
    document_taken, copy_taken = (
        agreed("page_text.json", files),
        agreed("record.writer.json#/$defs/copy", files),
    )
    judged = [(name, document_taken(fixture(name)), True) for name in DOCUMENTS_TAKEN]
    judged += [(name, document_taken(fixture(name)), False) for name in DOCUMENTS_REFUSED]
    judged += [(name, copy_taken(evidence_copy(name)), True) for name in PLACES_TAKEN]
    judged += [(name, copy_taken(evidence_copy(name)), False) for name in PLACES_REFUSED]
    return {name for name, taken, should in judged if taken != should}


def test_the_fixtures_documents_and_places_are_judged_by_the_schemas() -> None:
    assert misjudged_fixtures(PAGE_TEXT, WRITER) == set()


def test_schemas_stating_less_or_more_misjudge_the_fixtures() -> None:
    """The control: each shape loosened, every refused fixture is taken; an element path's pattern tightened,
    the XML documents and the XML place are refused."""
    page_text, writer = copy.deepcopy(PAGE_TEXT), copy.deepcopy(WRITER)
    del page_text["anyOf"]
    del page_text["$defs"]["page"]["properties"]["text"]["pattern"]
    page_text["properties"]["copy"]["properties"]["sha256"] = {"type": "string"}
    del writer["$defs"]["element_path"]["pattern"]
    del writer["$defs"]["copy"]["dependentRequired"]
    writer["$defs"]["copy"]["properties"]["sha256"] = {"type": "string"}
    writer["$defs"]["copy"]["properties"]["spans"]["items"] = {"type": "object"}
    assert misjudged_fixtures(page_text, writer) == {*DOCUMENTS_REFUSED, *PLACES_REFUSED}
    tightened = copy.deepcopy(WRITER)
    tightened["$defs"]["element_path"]["pattern"] = "^/x"
    assert misjudged_fixtures(PAGE_TEXT, tightened) == {
        "page_text_xml.json",
        "page_text_xml_typography.json",
        "rc032_xml_quote_at_its_place.json",
    }


def test_the_request_table_is_the_request_schemas() -> None:
    rows = table(document("read_side_contract.md"), "## 1. The read request")
    members = [only_code(row["Member"]) for row in rows]
    # "Its shape, apart from `records`, which is supplied beside it" (section 1).
    assert members[0] == "records"
    assert members[1:] == list(REQUEST["properties"])


def test_the_result_table_is_the_result_schemas() -> None:
    rows = table(document("read_side_contract.md"), "## 2. The read result")
    assert [only_code(row["Member"]) for row in rows] == list(RESULT["properties"])


def _from_the_result(schema: JsonValue) -> JsonValue:
    """A part of read_result.json with its own references written from case.json, as case.json gives them."""
    if isinstance(schema, dict):
        return {
            key: f"read_result.json{value}"
            if key == "$ref" and isinstance(value, str) and value.startswith("#")
            else _from_the_result(value)
            for key, value in schema.items()
        }
    if isinstance(schema, list):
        return [_from_the_result(item) for item in schema]
    return schema


def test_a_cases_expected_members_are_the_results() -> None:
    """A case's `expected` holds the result's members it compares, each shaped as the result holds it, none
    required by itself (case.json requires `status` and `reasons` wherever `compare` names them)."""
    compared = CASE["$defs"]["compared_result"]
    assert compared["properties"] == _from_the_result(RESULT["properties"])
    assert "required" not in compared
    assert compared["additionalProperties"] is False


# The members a build gives a result beside the read's (`declarations.md` section 2, and section 3 item 6 for
# a combination's `fields`), as the case schema names them until the build's report has its own schema.
BUILD_MEMBERS = (
    "model",
    "record",
    "field",
    "fields",
    "specimen_differences",
    "accepted",
    "accepted_by",
    "trainable_by",
    "not_accepted",
)


def build_result_problems(case: Json) -> list[str]:
    """Where a build-check case's result drifts from a read case's: its read members are compared_result's,
    shaped alike, followed by the build's own; `compare.result_members` names exactly those members; and no
    member is required by itself, as a read case's are not."""
    defs = cast(dict[str, dict[str, JsonValue]], case["$defs"])
    built = cast(dict[str, JsonValue], defs["compared_build_result"]["properties"])
    read = cast(dict[str, JsonValue], defs["compared_result"]["properties"])
    problems: list[str] = []
    if list(built) != [*read, *BUILD_MEMBERS]:
        problems.append(f"a build result names {list(built)}")
    problems += [
        f"a build result's {name} is shaped otherwise" for name in read if built.get(name) != read[name]
    ]
    compare = cast(dict[str, dict[str, JsonValue]], defs["case_compare"]["properties"])
    named = cast(dict[str, list[str]], compare["result_members"]["items"])["enum"]
    if named != list(built):
        problems.append(f"result_members names {named}")
    if "required" in defs["compared_build_result"]:
        problems.append("a build result requires a member")
    return problems


def test_a_build_cases_result_is_a_read_cases_with_the_builds_members() -> None:
    assert build_result_problems(CASE) == []


def _properties(defs: Json, name: str) -> Json:
    return cast(Json, cast(Json, defs[name])["properties"])


def _drop_labels(defs: Json) -> None:
    _properties(defs, "compared_build_result").pop("labels")


def _reshape_value(defs: Json) -> None:
    _properties(defs, "compared_build_result")["value"] = {"type": "number"}


def _drop_a_result_member(defs: Json) -> None:
    items = cast(Json, cast(Json, _properties(defs, "case_compare")["result_members"])["items"])
    cast(list[JsonValue], items["enum"]).pop()


def _require_model(defs: Json) -> None:
    cast(Json, defs["compared_build_result"])["required"] = ["model"]


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (_drop_labels, "a build result names"),
        (_reshape_value, "a build result's value is shaped otherwise"),
        (_drop_a_result_member, "result_members names"),
        (_require_model, "requires a member"),
    ],
)
def test_a_build_result_that_drifts_is_found(change: Callable[[Json], None], problem: str) -> None:
    case = copy.deepcopy(CASE)
    change(case["$defs"])
    assert any(problem in found for found in build_result_problems(case))


def result_shape_problems(result: dict[str, JsonValue], writer: dict[str, JsonValue]) -> list[str]:
    """Where the result's shapes repeat the writer's: a condition entry's `record` takes each shape the
    writer's `conditions` gives a condition, and a review returned as found names the writer review's
    members."""
    result_defs = cast(dict[str, dict[str, JsonValue]], result["$defs"])
    writer_defs = cast(dict[str, dict[str, JsonValue]], writer["$defs"])
    record = cast(dict[str, dict[str, list[dict[str, str]]]], result_defs["condition_entry"]["properties"])
    taken = {alternative["$ref"] for alternative in record["record"]["anyOf"]}
    conditions = cast(dict[str, dict[str, list[dict[str, str]]]], writer_defs["conditions"]["properties"])
    problems = [
        f"a condition entry's record does not take {name}'s shape {alternative['$ref']}"
        for name, given in conditions.items()
        for alternative in given["anyOf"]
        if f"record.writer.json{alternative['$ref']}" not in taken
    ]
    returned = cast(dict[str, JsonValue], result_defs["result_review"]["properties"])
    written = cast(dict[str, JsonValue], writer_defs["review"]["properties"])
    if list(returned) != list(written):
        problems.append(f"a review returned names {list(returned)}, the writer's {list(written)}")
    return problems


def test_the_results_shapes_take_the_writers() -> None:
    assert result_shape_problems(RESULT, WRITER) == []


def test_a_result_shape_left_behind_is_found() -> None:
    shapes = copy.deepcopy(RESULT)
    del shapes["$defs"]["condition_entry"]["properties"]["record"]["anyOf"][1]
    del shapes["$defs"]["result_review"]["properties"]["orcid"]
    assert result_shape_problems(shapes, WRITER) == [
        "a condition entry's record does not take density_kind's shape #/$defs/condition_density_kind",
        "a review returned names ['result', 'reviewer', 'date', 'independent_of_extraction', 'checklist'], "
        "the writer's ['result', 'reviewer', 'orcid', 'date', 'independent_of_extraction', 'checklist']",
    ]


def references(node: JsonValue) -> list[str]:
    if isinstance(node, list):
        return [found for item in node for found in references(item)]
    if not isinstance(node, dict):
        return []
    reference = node.get("$ref")
    own = [reference] if isinstance(reference, str) else []
    return own + [found for value in node.values() for found in references(value)]


def result_twin_problems(result: dict[str, JsonValue], writer: dict[str, JsonValue]) -> list[str]:
    """Each twin that is not its writer definition as a result returns it, and each place read_result.json
    refers to a writer definition that has a twin."""
    result_defs = cast(dict[str, JsonValue], result["$defs"])
    writer_defs = cast(dict[str, JsonValue], writer["$defs"])
    problems = [
        f"result_{name} is not the writer's {name} without the patterns a read does not check"
        for name in RESULT_TWINS
        if result_defs.get(f"result_{name}") != as_returned(writer_defs[name])
    ]
    twinned = {f"record.writer.json#/$defs/{name}" for name in RESULT_TWINS}
    return problems + [
        f"read_result.json refers to {reference}, which a result returns as its twin"
        for reference in references(result)
        if reference in twinned
    ]


def test_the_results_twins_are_the_writers_definitions_without_what_a_read_does_not_check() -> None:
    assert result_twin_problems(RESULT, WRITER) == []


def test_a_twin_that_drifts_from_the_writer_is_found() -> None:
    drifted = copy.deepcopy(RESULT)
    del drifted["$defs"]["result_specimen"]["properties"]["lot"]
    drifted["$defs"]["result_pinned_record"]["properties"]["id"] = {
        "$ref": "record.writer.json#/$defs/record_id"
    }
    drifted["$defs"]["alternative_value"]["properties"]["specimen"] = {
        "$ref": "record.writer.json#/$defs/specimen"
    }
    writer = copy.deepcopy(WRITER)
    writer["$defs"]["derivation"]["properties"]["method"] = {"type": "string", "minLength": 1}
    assert result_twin_problems(drifted, writer) == [
        "result_specimen is not the writer's specimen without the patterns a read does not check",
        "result_derivation is not the writer's derivation without the patterns a read does not check",
        "result_pinned_record is not the writer's pinned_record without the patterns a read does not check",
        "read_result.json refers to record.writer.json#/$defs/specimen, which a result returns as its twin",
    ]


# A test report a read returns: the writer's report, its provenance whole, checked as a field's and the
# members that check leaves unchecked as found (`record_format.md` section 4.3 item 2, the maintainer's ruling
# of 2026-10-19), so that a report whose `extraction` is a number, returned as stored, validates.
REPORTS = {
    "result_evidence_entry": "evidence_entry",
    "result_withheld_evidence_entry": "withheld_evidence_entry",
}
JSON_VALUE: JsonValue = {"$ref": "record.writer.json#/$defs/json_value"}


def _write_only(member: JsonValue) -> bool:
    return isinstance(member, dict) and "x-materica-write-only" in member


def as_a_report_returns(writer_defs: dict[str, dict[str, JsonValue]], name: str) -> dict[str, JsonValue]:
    """The writer's `name` as a read returns it in a test report: a reference to the writer's own written
    from read_result.json, the provenance and its source as a report returns them, each member the writer
    marks write-only any JSON value and required nowhere, and no rule across members a read does not check."""
    written = copy.deepcopy(writer_defs[name])
    written.pop("if", None)
    written.pop("then", None)
    written.pop("allOf", None)
    properties = cast(dict[str, JsonValue], written["properties"])
    for member, given in properties.items():
        if _write_only(given):
            properties[member] = JSON_VALUE
        elif member == "provenance":
            properties[member] = {"$ref": "#/$defs/result_entry_provenance"}
        elif member == "source":
            properties[member] = {"$ref": "#/$defs/result_entry_source"}
        else:
            properties[member] = json.loads(
                json.dumps(given).replace('"#/$defs/', '"record.writer.json#/$defs/')
            )
    written["required"] = [
        member for member in cast(list[str], written["required"]) if properties[member] != JSON_VALUE
    ]
    written.pop("description", None)
    return written


def report_problems(result: dict[str, JsonValue], writer: dict[str, JsonValue]) -> list[str]:
    """Each of a returned report's definitions that is not the writer's as a report returns it; the
    provenance also holds its review as a result's provenance does, required, and a derived value's
    derivation as a result's, required."""
    result_defs = cast(dict[str, dict[str, JsonValue]], result["$defs"])
    writer_defs = cast(dict[str, dict[str, JsonValue]], writer["$defs"])
    expected = {returned: as_a_report_returns(writer_defs, name) for returned, name in REPORTS.items()}
    expected["result_entry_source"] = as_a_report_returns(writer_defs, "source")
    provenance = as_a_report_returns(writer_defs, "provenance")
    cast(dict[str, JsonValue], provenance["properties"])["review"] = cast(
        dict[str, JsonValue], result_defs["result_provenance"]["properties"]
    )["review"]
    provenance["required"] = [*cast(list[str], provenance["required"]), "review"]
    provenance["allOf"] = [
        {
            "if": {"required": ["origin"], "properties": {"origin": {"const": "measured_by_source"}}},
            "then": {"required": ["source"]},
        },
        {
            "if": {"required": ["origin"], "properties": {"origin": {"const": "derived"}}},
            "then": {
                "required": ["derivation"],
                "properties": {"derivation": {"$ref": "#/$defs/result_derivation"}},
            },
        },
    ]
    expected["result_entry_provenance"] = provenance
    problems = [
        f"{returned} is not the writer's definition as a report returns it"
        for returned, shape in expected.items()
        if {key: value for key, value in result_defs.get(returned, {}).items() if key != "description"}
        != shape
    ]
    evidence = [
        branch
        for branch in cast(list[JsonValue], result_defs["result_value"]["anyOf"])
        if isinstance(branch, dict)
        and branch.get("type") == "array"
        and "listed_record" not in json.dumps(branch)
    ]
    reports = {"anyOf": [{"$ref": f"#/$defs/{returned}"} for returned in REPORTS]}
    if evidence != [{"type": "array", "items": reports}]:
        problems.append("a result's evidence is not a list of reports as a report returns them")
    return problems


def test_a_report_returned_is_the_writers_with_its_unchecked_members_as_found() -> None:
    assert report_problems(RESULT, WRITER) == []
    takes = validator("read_result.json")
    report: dict[str, JsonValue] = {
        "endpoint": "cytotoxicity",
        "standard": {"designation": "ISO 10993-5", "year": 2009.0},
        **dict.fromkeys(("contact_category", "contact_duration", "material_form", "processing"), "text"),
        "reported_result": "text",
        "provenance": {
            "origin": "measured_by_contributor",
            "extraction": 5.0,
            "review": {"status": "not_checked"},
        },
    }
    result: dict[str, JsonValue] = {"status": "met", "reasons": [], "value": [report], "labels": []}
    assert takes(result) == []
    for broken in ({"origin": "estimated"}, {"x_unknown_member": 1.0}, {"review": 5.0}):
        provenance = {**cast(dict[str, JsonValue], report["provenance"]), **broken}
        assert takes({**result, "value": [{**report, "provenance": provenance}]}) != [], broken


def test_a_report_shape_that_drifts_from_the_writer_is_found() -> None:
    drifted = copy.deepcopy(RESULT)
    drifted["$defs"]["result_entry_provenance"]["properties"]["extraction"] = {
        "$ref": "record.writer.json#/$defs/extraction"
    }
    del drifted["$defs"]["result_withheld_evidence_entry"]["properties"]["processing"]
    drifted["$defs"]["result_value"]["anyOf"][3] = {
        "type": "array",
        "items": {"anyOf": [{"$ref": "record.writer.json#/$defs/evidence_entry"}]},
    }
    writer = copy.deepcopy(WRITER)
    writer["$defs"]["source"]["properties"]["page"] = {"type": "string"}
    assert report_problems(drifted, writer) == [
        "result_withheld_evidence_entry is not the writer's definition as a report returns it",
        "result_entry_source is not the writer's definition as a report returns it",
        "result_entry_provenance is not the writer's definition as a report returns it",
        "a result's evidence is not a list of reports as a report returns them",
    ]


def test_the_result_takes_an_alternatives_index_only_from_zero() -> None:
    """An index among the stored alternatives, in an entry of `alternative_values` or a reason, is a whole
    number from 0 (`read_side_contract.md` section 2): the result schema refuses `-1` and takes 0 (S2a-4's
    review, L3's M42)."""
    refused = validator("read_result.json")
    entry: dict[str, JsonValue] = {
        "alternative": 0,
        "value": 1.0,
        "unit": "Pa.s",
        "conditions": [],
        "specimen": {},
        "provenance": {"origin": "measured_by_contributor", "review": {"status": "not_checked"}},
        "labels": [],
    }
    reason: dict[str, JsonValue] = {"code": "no_pick", "alternative": 0}

    def result(index: int) -> dict[str, JsonValue]:
        return {
            "status": "unknown",
            "reasons": [{**reason, "alternative": index}],
            "alternative_values": [{**entry, "alternative": index}],
            "labels": [],
        }

    assert refused(result(0)) == []
    assert refused({**result(0), "alternative_values": [{**entry, "alternative": -1}]}) != []
    assert refused({**result(0), "reasons": [{**reason, "alternative": -1}]}) != []


def test_the_sections_are_the_field_tables() -> None:
    assert set(WRITER["$defs"]["sections"]["properties"]) == VOCABULARY.sections


def test_the_record_types_are_the_type_tables() -> None:
    rows = table(document("record_format.md"), "## 3. Record types")
    assert {only_code(row["`record_type`"]) for row in rows} == set(WRITER["$defs"]["record_type"]["enum"])


def test_the_wants_are_section_6s() -> None:
    text = document("read_side_contract.md")
    section = text[text.index("## 6. What a read returns") : text.index("## 7. ")]
    rows = table(text, "## 6. What a read returns: `want`")
    wants = {only_code(row["`want`"]) for row in rows} | set(re.findall(r"`want: ([a-z_]+)`", section))
    assert wants == set(REQUEST["$defs"]["want"]["enum"])


def test_the_suites_are_the_readmes() -> None:
    sentence = re.search(r"`suite` is one of (.*?)\.", document("README.md"), re.DOTALL)
    assert sentence is not None
    assert codes(sentence[1]) == CASE["$defs"]["suite"]["enum"]


def test_the_operations_are_the_readmes() -> None:
    """Every operation the README names is the case schema's: an operation's, or a build-check case's."""
    named = re.findall(r'\{"operation": "([a-z][a-z0-9_]*)"', document("README.md"))
    operations = CASE["$defs"]["case_operation"]["properties"]["operation"]["enum"]
    build = CASE["$defs"]["build_operation"]["properties"]["operation"]["const"]
    assert sorted(named) == sorted([*operations, build])


def item(document_name: str, start: str) -> str:
    """The text of the numbered item of `document_name` that begins with `start`, up to the next item."""
    found = re.search(rf"^{re.escape(start)}(.*?)(?=^\d+\. |^#|\Z)", document(document_name), re.M | re.S)
    assert found is not None, start
    return found[1]


def test_the_overlay_purposes_are_section_4_4s() -> None:
    purposes = item("record_format.md", "1. `purpose` is ")
    assert (
        codes(outside_parentheses(purposes))
        == WRITER["$defs"]["overlay_body"]["properties"]["purpose"]["enum"]
    )


def test_the_status_tokens_are_provenances() -> None:
    tokens = codes(outside_parentheses(item("provenance.md", "2. The five tokens are ")))
    assert len(tokens) == 5
    assert tokens == WRITER["$defs"]["status_object"]["properties"]["status"]["enum"]


def test_the_read_statuses_are_the_result_tables() -> None:
    (row,) = [
        row
        for row in table(document("read_side_contract.md"), "## 2. The read result")
        if row["Member"] == "`status`"
    ]
    statuses = codes(row["Contents"].partition(". ")[0])
    assert statuses == RESULT["$defs"]["read_status"]["enum"]


@pytest.mark.parametrize(
    ("check", "name", "old", "new"),
    [
        (test_the_overlay_purposes_are_section_4_4s, "record_format.md", "`measurement` (", "`measured` ("),
        (
            test_the_status_tokens_are_provenances,
            "provenance.md",
            "`not_checked` (a check",
            "`unchecked` (a check",
        ),
        (
            test_the_read_statuses_are_the_result_tables,
            "read_side_contract.md",
            "| `met`, `not_met` or `unknown`.",
            "| `met`, `partly_met`, `not_met` or `unknown`.",
        ),
        (
            test_the_operations_are_the_readmes,
            "README.md",
            '`{"operation": "transform_draws", "normals"',
            '`{"operation": "map_draws", "normals"',
        ),
    ],
    ids=["purpose", "status_object", "read_status", "operation"],
)
def test_the_token_checks_can_fail(
    check: Callable[[], None], name: str, old: str, new: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = document(name)
    assert old in original
    changed = original.replace(old, new)
    unchanged = document

    def changed_document(other: str) -> str:
        return changed if other == name else unchanged(other)

    monkeypatch.setattr(sys.modules[__name__], "document", changed_document)
    with pytest.raises(AssertionError):
        check()


def test_every_schema_files_id_is_where_it_is_published() -> None:
    assert sorted(path.name for path in SCHEMA.rglob("*.json"))
    assert misplaced_ids(SCHEMA, BASE) == []


def test_the_id_check_can_fail(tmp_path: Path) -> None:
    base = "https://example.org/schema/0.1/"
    (tmp_path / "vocabulary").mkdir()
    (tmp_path / "right.json").write_text(json.dumps({"$id": base + "right.json"}), encoding="utf-8")
    (tmp_path / "vocabulary" / "moved.json").write_text(
        json.dumps({"$id": base + "moved.json"}), encoding="utf-8"
    )
    (tmp_path / "none.json").write_text("{}", encoding="utf-8")
    assert misplaced_ids(tmp_path, base) == ["none.json: None", f"vocabulary/moved.json: {base}moved.json"]


# What both libraries read alike (`tests/verdicts.py`, `tests/property/test_validators_agree.py`).
# jsonschema-rs reads a resource's `$schema` unless told the draft, and applies `dependencies`, a keyword
# draft 2020-12 dropped, even at 2020-12; python-jsonschema reads every file at 2020-12. So every file
# declares 2020-12 or nothing, and uses no keyword outside 2020-12's but the package's own `x-materica-*`
# and, at a vocabulary file's root, its table.
DRAFT = "https://json-schema.org/draft/2020-12/schema"
# Keywords whose value is a schema, a map of schemas by name, or a list of schemas.
IN_PLACE = {
    "items",
    "additionalProperties",
    "unevaluatedProperties",
    "unevaluatedItems",
    "not",
    "if",
    "then",
    "else",
    "contains",
    "propertyNames",
    "contentSchema",
}
BY_NAME = {"properties", "patternProperties", "$defs", "dependentSchemas"}
LISTED = {"allOf", "anyOf", "oneOf", "prefixItems"}
KEYWORDS = (
    IN_PLACE
    | BY_NAME
    | LISTED
    | {"$schema", "$id", "$ref", "$anchor", "$dynamicRef", "$dynamicAnchor", "$vocabulary", "$comment"}
    | {"type", "enum", "const", "multipleOf", "maximum", "exclusiveMaximum", "minimum", "exclusiveMinimum"}
    | {"maxLength", "minLength", "pattern", "maxItems", "minItems", "uniqueItems", "maxContains"}
    | {"minContains", "maxProperties", "minProperties", "required", "dependentRequired"}
    | {"title", "description", "default", "deprecated", "readOnly", "writeOnly", "examples"}
    | {"format", "contentEncoding", "contentMediaType"}
)
VOCABULARY_TABLES = {
    "vocabulary/acceptances.json": "kinds",
    "vocabulary/conditions.json": "conditions",
    "vocabulary/coverage.json": "coverage",
    "vocabulary/fields.json": "fields",
    "vocabulary/reasons.json": "reasons",
    "vocabulary/specimen_facts.json": "facts",
}


def schema_files(root: Path = SCHEMA) -> dict[str, dict[str, object]]:
    return {
        path.relative_to(root).as_posix(): json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(root.rglob("*.json"))
    }


def subschemas(schema: object, where: str = "") -> Iterator[tuple[str, dict[str, object]]]:
    """Each schema object in `schema`, with its JSON pointer: those its keywords hold, at any depth."""
    if not isinstance(schema, dict):
        return
    found = cast(dict[str, object], schema)
    yield where, found
    for keyword, value in found.items():
        if keyword in IN_PLACE:
            yield from subschemas(value, f"{where}/{keyword}")
        elif keyword in BY_NAME and isinstance(value, dict):
            for name, held in cast(dict[str, object], value).items():
                yield from subschemas(held, f"{where}/{keyword}/{name}")
        elif keyword in LISTED and isinstance(value, list):
            for index, held in enumerate(cast(list[object], value)):
                yield from subschemas(held, f"{where}/{keyword}/{index}")


def draft_problems(files: dict[str, dict[str, object]]) -> list[str]:
    """Each file that declares another draft than 2020-12, and each keyword outside 2020-12's."""
    problems = [
        f"{name} declares {file['$schema']}"
        for name, file in files.items()
        if file.get("$schema", DRAFT) != DRAFT
    ]
    for name, file in files.items():
        for where, schema in subschemas(file):
            own = {VOCABULARY_TABLES[name]} if where == "" and name in VOCABULARY_TABLES else set[str]()
            problems += [
                f"{name}#{where}: {keyword}"
                for keyword in schema
                if keyword not in KEYWORDS | own and not keyword.startswith("x-materica-")
            ]
    return problems


def test_every_schema_file_is_read_at_2020_12() -> None:
    assert draft_problems(schema_files()) == []


@pytest.mark.parametrize(
    ("path", "value", "problem"),
    [
        (
            ("$schema",),
            "http://json-schema.org/draft-07/schema#",
            "case.json declares http://json-schema.org/",
        ),
        (("dependencies",), {"case": ["inputs"]}, "case.json#: dependencies"),
        (("properties", "case", "definitions"), {}, "case.json#/properties/case: definitions"),
    ],
    ids=["draft-07", "dependencies", "nested"],
)
def test_the_draft_check_can_fail(path: tuple[str, ...], value: object, problem: str) -> None:
    files = schema_files()
    changed = files["case.json"]
    for step in path[:-1]:
        changed = cast(dict[str, object], changed[step])
    changed[path[-1]] = value
    assert any(found.startswith(problem) for found in draft_problems(files)), draft_problems(files)


# Every pattern starts with `^` and ends with `(?![\s\S])`, which both libraries read alike, as matching in
# full; a validator's `$` also matches before a final newline in python-jsonschema and not in jsonschema-rs.
# Between, no escape of a letter or digit (`\d`, `\w` and `\s` are ASCII in one library and Unicode in the
# other, and differently inside a lookaround), no `.` outside a class, no `$` and no POSIX class
# (`[[:alpha:]]` is a class in jsonschema-rs and a set of characters in python-jsonschema).
END = "(?![\\s\\S])"


def pattern_problems(pattern: str) -> list[str]:
    problems = [] if pattern.startswith("^") else ["no `^` at its start"]
    problems += [] if pattern.endswith(END) else [f"no `{END}` at its end"]
    body = pattern.removeprefix("^").removesuffix(END)
    in_class, index = False, 0
    while index < len(body):
        character = body[index]
        if character == "\\":
            escaped = body[index + 1 : index + 2]
            if escaped.isalnum():
                problems.append(f"the escape `\\{escaped}`")
            index += 2
            continue
        if body.startswith("[[:", index) or (in_class and body.startswith("[:", index)):
            problems.append("a POSIX class")
        if character == "[" and not in_class:
            in_class = True
        elif character == "]" and in_class:
            in_class = False
        elif character in ".$" and not in_class:
            problems.append(f"`{character}` outside a class")
        index += 1
    return problems


def patterns(files: dict[str, dict[str, object]]) -> Iterator[tuple[str, str]]:
    """Each pattern in `files`, a `pattern`'s or a `patternProperties` name, with where it is."""
    for name, file in files.items():
        for where, schema in subschemas(file):
            if isinstance(schema.get("pattern"), str):
                yield f"{name}#{where}/pattern", cast(str, schema["pattern"])
            for held in cast(dict[str, object], schema.get("patternProperties", {})):
                yield f"{name}#{where}/patternProperties", held


def test_every_pattern_reads_alike_in_both_libraries() -> None:
    found = dict(patterns(schema_files()))
    assert len(found) >= 13
    assert {
        where: pattern_problems(pattern) for where, pattern in found.items() if pattern_problems(pattern)
    } == {}


@pytest.mark.parametrize(
    ("pattern", "problem"),
    [
        ("^[0-9]+$", f"no `{END}` at its end"),
        ("[0-9]+(?![\\s\\S])", "no `^` at its start"),
        ("^\\d+(?![\\s\\S])", "the escape `\\d`"),
        ("^a\\wb(?![\\s\\S])", "the escape `\\w`"),
        ("^a\\sb(?![\\s\\S])", "the escape `\\s`"),
        ("^a.b(?![\\s\\S])", "`.` outside a class"),
        ("^a$b(?![\\s\\S])", "`$` outside a class"),
        ("^[[:alpha:]]+(?![\\s\\S])", "a POSIX class"),
    ],
)
def test_the_pattern_check_can_fail(pattern: str, problem: str) -> None:
    assert problem in pattern_problems(pattern)


def test_the_pattern_check_reads_every_file() -> None:
    """The control for the files: a pattern of `case.json` and one of `read_request.json`, changed, are
    found."""
    files = schema_files()
    case_properties = cast(dict[str, dict[str, object]], files["case.json"]["properties"])
    case_properties["case"]["pattern"] = "^[A-Z]{2}-\\d{3}(?![\\s\\S])"
    request_definitions = cast(dict[str, dict[str, object]], files["read_request.json"]["$defs"])
    request_definitions["field_name"]["pattern"] = "^[a-z0-9_]+.[a-z0-9_]+(?![\\s\\S])"
    found = {where for where, pattern in patterns(files) if pattern_problems(pattern)}
    assert found == {"case.json#/properties/case/pattern", "read_request.json#/$defs/field_name/pattern"}
