# SPDX-License-Identifier: Apache-2.0
"""declaration.json and build_report.json against the specification, the vocabulary, case.json and the
build-check cases.

- The declaration's members at each place, their required lists and their tokens are those of
  `declarations.md` section 1's table of the declaration's shape, each acceptance kind's own members those of
  section 4.1's row, and its lists of names the vocabulary's (`schema/0.1/vocabulary/`).
- The report's field result holds `read_result.json`'s members as `case.json` gives them, and `case.json`'s
  build result and watch are the report's, member for member.
- Every build-check declaration whose case expects no refusal is valid against declaration.json; every one
  expected refused is invalid, where the case's refusal points, or is listed with the rule the schema does
  not state; and the schema is closed at every place those declarations reach.

Each check returns its problems, and its controls change a copy of the text or of a schema and find one.
"""

import copy
import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator

from materica.core import jsonio
from materica.core.jsonio import JsonValue
from materica.core.reasons import Reason
from scripts.gen_vocabulary import SPECIFICATION, cells, codes, listed, prose, table, without_asides
from tests.spec_sync.schemas import BASE, PACKAGE, SCHEMA, agreed, registry
from tests.verdicts import Json

DECLARATION: Json = json.loads((SCHEMA / "declaration.json").read_text(encoding="utf-8"))
REPORT: Json = json.loads((SCHEMA / "build_report.json").read_text(encoding="utf-8"))
CASE: Json = json.loads((SCHEMA / "case.json").read_text(encoding="utf-8"))
RESULT: Json = json.loads((SCHEMA / "read_result.json").read_text(encoding="utf-8"))
REQUEST: Json = json.loads((SCHEMA / "read_request.json").read_text(encoding="utf-8"))
VOCABULARY = SCHEMA / "vocabulary"


def document(name: str) -> str:
    return (SPECIFICATION / name).read_text(encoding="utf-8")


def vocabulary(name: str) -> Json:
    return cast(Json, json.loads((VOCABULARY / name).read_text(encoding="utf-8")))


def definitions(schema: Json) -> dict[str, Json]:
    return cast(dict[str, Json], schema["$defs"])


def properties(node: Json) -> dict[str, Json]:
    return cast(dict[str, Json], node.get("properties", {}))


def required(node: Json) -> list[str]:
    return cast(list[str], node.get("required", []))


def at(node: JsonValue, *path: str) -> Json:
    """The object at `path` below `node`."""
    for step in path:
        node = cast(Json, node)[step]
    return cast(Json, node)


# The table of the declaration's shape (`declarations.md` section 1).

HEADER = "| Place | Member | Required | Holds |"


def shape_rows(text: str) -> list[dict[str, str]]:
    """The rows of the table of the declaration's shape, each place written out where the cell leaves it to
    the row above."""
    lines = text.splitlines()
    start = lines.index(HEADER)
    rows: list[dict[str, str]] = []
    place = ""
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        found = dict(zip(("Place", "Member", "Required", "Holds"), cells(line), strict=True))
        place = found["Place"] or place
        rows.append({**found, "Place": place})
    return rows


# Each place of the table, and the definitions of declaration.json that hold its members.
KINDS = (
    "pick",
    "waiver",
    "implied_condition",
    "accepted_difference",
    "extrapolation",
    "nominal",
    "distribution",
    "overlay",
    "overlay_scope",
)
PLACES = {
    "declaration": ("",),
    "model entry": ("model_entry",),
    "requirement": ("requirement",),
    "requirement condition": ("tolerance_condition", "accept_condition"),
    "acceptance": KINDS,
    "trainable entry": ("trainable_entry",),
    "material reference": ("material_reference",),
}
OWN = "its kind's own members"


def definition(schema: Json, name: str) -> Json:
    """A definition of declaration.json by its name, the root for "", followed through a `$ref` to the read
    request's (a material reference)."""
    found = schema if not name else definitions(schema)[name]
    reference = found.get("$ref")
    if isinstance(reference, str) and reference.startswith("read_request.json#/$defs/"):
        return definitions(REQUEST)[reference.rpartition("/")[2]]
    return found


def kind_rows(text: str) -> dict[str, dict[str, str]]:
    """Section 4.1's rows, by kind."""
    return {row["`acceptance`"].strip("`"): row for row in table(text, "### 4.1 The list")}


# The code spans of an own-members cell that name no member of the acceptance: what an implied condition's
# `implies` may not hold ("a record condition's shapes without `basis` (one there is ignored), `plus_minus` or
# `set_or_measured`").
NOT_OWN = {"implied_condition": {"basis", "plus_minus", "set_or_measured"}}
MEMBER = re.compile(r"[a-z_]+")


def own_members(cell: str, kind: str) -> tuple[set[str], set[str]]:
    """A kind's own members in its row's cell, and those of them it requires: each clause's member is
    required, but one the clause gives `optionally`, one followed by `where` (required where that holds), and
    two written one `in place of` the other, of which it holds one."""
    named: set[str] = set()
    needed: set[str] = set()
    either: set[str] = set()
    for clause in without_asides(cell).split(";"):
        optional = clause.strip().startswith("optionally")
        for pair in re.findall(r"`([a-z_]+)` in place of `([a-z_]+)`", clause):
            either |= set(pair)
        for match in re.finditer(r"`([^`]+)`( where)?", clause):
            member = match[1]
            if not MEMBER.fullmatch(member) or member in NOT_OWN.get(kind, set()):
                continue
            named.add(member)
            if not (optional or match[2]):
                needed.add(member)
    return named, needed - either


def common(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row["Place"] == "acceptance" and row["Member"] != OWN]


def expected_kind(
    rows: list[dict[str, str]], kind: str, kinds: dict[str, dict[str, str]]
) -> tuple[set[str], set[str]]:
    """A kind's members and required members, by the table's acceptance rows and its section 4.1 row."""
    named, needed = own_members(kinds[kind]["Own members"], kind)
    location = kinds[kind]["Location"]
    for row in common(rows):
        members = set(codes(row["Member"]))
        held = row["Required"]
        if members == {"record", "region", "interval"}:
            if not location.startswith("none"):
                named |= members
            if location.startswith("`record`"):
                needed.add("record")
            continue
        if held.startswith("yes, but"):
            if kind not in codes(held):
                named |= members
                needed |= members
            continue
        listed = held.startswith("for ") and f"`{kind}`" in held
        # A member required of the kinds its cell lists, which "no other kind holds", is named on those alone
        # (`basis`, the maintainer's ruling of 2026-10-24).
        if held.startswith("for ") and "no other kind holds" in held and not listed:
            continue
        named |= members
        if held.startswith("yes") or listed:
            needed |= members
    return named, needed


def located(schema: Json, kind: str) -> bool:
    conjuncts = cast(list[Json], definitions(schema)[kind].get("allOf", []))
    return {"$ref": "#/$defs/location_rule"} in conjuncts


def shape_problems(text: str, schema: Json) -> list[str]:
    """Where declaration.json's places differ from the table's: a member named in one and not the other, a
    member required in one and not the other, a list the table asks one entry or more of that the schema does
    not, and a kind's location rule."""
    rows = shape_rows(text)
    kinds = kind_rows(text)
    problems: list[str] = []
    if unmapped := {row["Place"] for row in rows} - set(PLACES):
        problems.append(f"the table's places {sorted(unmapped)} have no definition here")
    for place, names in PLACES.items():
        at_place = [row for row in rows if row["Place"] == place]
        if place == "acceptance":
            for kind in names:
                named, needed = expected_kind(rows, kind, kinds)
                found = definition(schema, kind)
                if set(properties(found)) != named:
                    problems.append(f"{kind} names {sorted(properties(found))}, the text {sorted(named)}")
                if set(required(found)) != needed:
                    problems.append(f"{kind} requires {sorted(required(found))}, the text {sorted(needed)}")
                needs = kinds[kind]["Location"].startswith("`region`, `interval` or `record`")
                if located(schema, kind) != needs:
                    problems.append(f"{kind}'s location rule is {'missing' if needs else 'applied'}")
            continue
        named = {member for row in at_place for member in codes(row["Member"])}
        found_named = {member for name in names for member in properties(definition(schema, name))}
        if found_named != named:
            problems.append(f"the {place} names {sorted(found_named)}, the text {sorted(named)}")
        needed = {
            member
            for row in at_place
            if row["Required"].startswith("yes")
            for member in codes(row["Member"].partition(" and one of ")[0])
        }
        exactly_one = {
            member for row in at_place if row["Required"] == "exactly one" for member in codes(row["Member"])
        }
        if exactly_one:
            # One definition per member of the row, each requiring its own alone of them.
            alternatives = [set(required(definition(schema, name))) for name in names]
            found_needed = alternatives[0].intersection(*alternatives[1:])
            each = [held & exactly_one for held in alternatives]
            if any(len(own) != 1 for own in each) or set[str]().union(*each) != exactly_one:
                problems.append(f"a {place} does not require exactly one of {sorted(exactly_one)}")
        else:
            found_needed = {member for name in names for member in required(definition(schema, name))}
        if found_needed != needed:
            problems.append(f"the {place} requires {sorted(found_needed)}, the text {sorted(needed)}")
        for row in at_place:
            if "at least one" in row["Required"]:
                for member in codes(row["Member"]):
                    held = properties(definition(schema, names[0]))[member]
                    if held.get("minItems") != 1:
                        problems.append(f"the {place}'s {member} takes an empty list")
    return problems


# The members the table's Holds cells give as an object (`{"name", "version"}`, both required), and the
# definition that holds them; a model's name and version are the writer's `scope_model`.
HELD_OBJECTS = {
    ("declaration", "consumer"): "consumer",
    ("declaration", "sampling"): "sampling",
    ("model entry", "model"): "record.writer.json#/$defs/scope_model",
    ("model entry", "mixing"): "mixing",
    ("model entry", "chains"): "chain",
    ("model entry", "engine"): "engine",
}
WRITER: Json = json.loads((SCHEMA / "record.writer.json").read_text(encoding="utf-8"))


def held_problems(text: str, schema: Json) -> list[str]:
    """Where an object a Holds cell gives (its members, `"name"` each, and an `optionally` member after it)
    differs from its definition's members, or from its required members: all of them, unless the cell says
    which are optional."""
    rows = shape_rows(text)
    problems: list[str] = []
    for (place, member), name in HELD_OBJECTS.items():
        cell = holds(rows, place, member)
        shape = re.match(r"`\{([^}]*)\}`", cell)
        if shape is None:
            problems.append(f"the {place}'s {member} holds no object")
            continue
        given = set(re.findall(r'"([a-z_]+)"', shape[1]))
        optional = set(re.findall(r"optionally `([a-z_]+)`", cell))
        found = (
            definitions(WRITER)[name.rpartition("/")[2]]
            if name.startswith("record.writer")
            else definitions(schema)[name]
        )
        if set(properties(found)) != given | optional:
            text_gives = sorted(given | optional)
            problems.append(
                f"the {place}'s {member} holds {sorted(properties(found))}, the text {text_gives}"
            )
        if set(required(found)) != given:
            problems.append(
                f"the {place}'s {member} requires {sorted(required(found))}, the text {sorted(given)}"
            )
    return problems


def test_the_shape_table_is_the_declaration_schemas() -> None:
    assert shape_problems(document("declarations.md"), DECLARATION) == []
    assert held_problems(document("declarations.md"), DECLARATION) == []


def test_an_object_a_holds_cell_gives_that_drifts_is_found() -> None:
    schema = copy.deepcopy(DECLARATION)
    properties(definitions(schema)["sampling"]).pop("independence")
    required(definitions(schema)["engine"]).append("region_values")
    found = held_problems(document("declarations.md"), schema)
    assert any(problem.startswith("the declaration's sampling holds") for problem in found)
    assert any(problem.startswith("the model entry's engine requires") for problem in found)
    text = document("declarations.md").replace("| | `precision` |", "| place | `precision` |")
    assert any("have no definition here" in problem for problem in shape_problems(text, DECLARATION))


def _drop_member(schema: Json) -> None:
    properties(definitions(schema)["model_entry"]).pop("families")


def _add_member(schema: Json) -> None:
    properties(definitions(schema)["requirement"])["profile"] = {"type": "string"}


def _require_optional(schema: Json) -> None:
    required(definitions(schema)["model_entry"]).append("mixing")


def _optional_required(schema: Json) -> None:
    required(definitions(schema)["model_entry"]).remove("target")


def _basis_of_a_waiver(schema: Json) -> None:
    required(definitions(schema)["waiver"]).append("basis")


def _basis_named_on_a_waiver(schema: Json) -> None:
    properties(definitions(schema)["waiver"])["basis"] = {"$ref": "#/$defs/text"}


def _empty_reads(schema: Json) -> None:
    properties(definitions(schema)["model_entry"])["reads"].pop("minItems")


def _unlocated_nominal(schema: Json) -> None:
    definitions(schema)["nominal"]["allOf"] = [{"$ref": "#/$defs/value_or_params_rule"}]


def _field_of_an_accepted_difference(schema: Json) -> None:
    properties(definitions(schema)["accepted_difference"])["field"] = {"$ref": "#/$defs/registered_field"}


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (_drop_member, "the model entry names"),
        (_add_member, "the requirement names"),
        (_require_optional, "the model entry requires"),
        (_optional_required, "the model entry requires"),
        (_basis_of_a_waiver, "waiver requires"),
        (_basis_named_on_a_waiver, "waiver names"),
        (_empty_reads, "reads takes an empty list"),
        (_unlocated_nominal, "nominal's location rule is missing"),
        (_field_of_an_accepted_difference, "accepted_difference names"),
    ],
)
def test_a_schema_that_drifts_from_the_table_is_found(change: Callable[[Json], None], problem: str) -> None:
    schema = copy.deepcopy(DECLARATION)
    change(schema)
    assert any(problem in found for found in shape_problems(document("declarations.md"), schema))


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ("| | `precision` |", "| | `profile` | no | a token |\n| | `precision` |", "the model entry names"),
        ("| | `review` | no |", "| | `review` | yes |", "the requirement requires"),
        ("`code`, and `condition` where the code names one;", "`code`, and `condition`;", "waiver requires"),
    ],
)
def test_a_text_that_drifts_from_the_schema_is_found(old: str, new: str, problem: str) -> None:
    text = document("declarations.md")
    assert text.count(old) == 1
    assert any(problem in found for found in shape_problems(text.replace(old, new), DECLARATION))


# The tokens and names each member takes.


def reference(node: Json) -> str:
    return str(node.get("$ref", ""))


def enum(node: Json) -> list[str]:
    return cast(list[str], node.get("enum", [node["const"]] if "const" in node else []))


def holds(rows: list[dict[str, str]], place: str, member: str) -> str:
    """The Holds cell of the row naming `member` at `place`; the own members' row for an acceptance's."""
    found = [
        row["Holds"] for row in rows if row["Place"] == place and member in (codes(row["Member"]) or [OWN])
    ]
    return found[0]


def named_rules(text: str) -> list[str]:
    return [row["Rule"].strip("`") for row in table(text, "## 3. Named rules")]


def distribution_parameters(text: str) -> dict[str, list[str]]:
    """Each distribution token's parameters, `uncertainty.md` section 4: the code spans of its cell before the
    first colon or semicolon."""
    return {
        row["Token"].strip("`"): codes(re.split(r"[:;]", row["Parameters"])[0])
        for row in table(text, "## 4. Distribution tokens")
    }


def condition_codes(text: str, reasons: list[str]) -> list[str]:
    """The codes that name a condition (`declarations.md` section 1): "the six `condition_*` codes", the
    reasons the vocabulary gives that prefix, and the codes listed after them."""
    clause = prose(text).partition("a code names a condition where its reasons always carry one: ")[2]
    clause = clause.partition(";")[0]
    prefixed = [code for code in reasons if code.startswith("condition_")]
    if not clause.startswith("the six `condition_*` codes, ") or len(prefixed) != 6:
        return []
    return [*prefixed, *listed(clause, "the six `condition_*` codes, ", None)]


def token_problems(text: str, schema: Json) -> list[str]:
    """Where a member's tokens differ from those the text gives it: the table's Holds column, section 1's
    sentence on the codes that name a condition, `mixing_rules.md` section 3's rules and `uncertainty.md`
    section 4's parameters; or where a member does not take its list from the vocabulary or the read request
    that the tests of those files hold to the text."""
    rows = shape_rows(text)
    defs = definitions(schema)
    own = holds(rows, "acceptance", OWN)
    model = properties(defs["model_entry"])
    requirement = properties(defs["requirement"])
    reasons = list(at(vocabulary("reasons.json"), "reasons"))
    mixing = holds(rows, "model entry", "mixing")
    rule = at(defs["mixing"], "properties", "rules", "additionalProperties")
    waiver_rule = at(defs["waiver_condition_rule"], "if", "properties", "code")
    refused_code = cast(Json, properties(defs["waiver"])["code"].get("not", {}))
    found = {
        "precision": (enum(model["precision"]), codes(holds(rows, "model entry", "precision"))),
        "review": (enum(requirement["review"]), codes(without_asides(holds(rows, "requirement", "review")))),
        "space": (
            enum(properties(defs["distribution"])["space"]),
            listed(own, "and `space`, ", " (section 4.3)"),
        ),
        "accepts": (
            enum(at(defs["overlay_scope"], "properties", "accepts", "items")),
            listed(own, "at least one of ", ", none twice"),
        ),
        "mixing rules": (
            enum(rule),
            [
                *listed(mixing, "field to ", ", a rule"),
                *named_rules(document("mixing_rules.md")),
                *listed(mixing, "names, or ", None),
            ],
        ),
        "codes that name a condition": (enum(waiver_rule), condition_codes(text, reasons)),
        "the code no waiver takes, by the table": (
            enum(refused_code),
            listed(own, "a reason of `read_side_contract.md` section 4 other than ", ", which section 4.2"),
        ),
        "the code no waiver takes, by section 4.2": (
            enum(refused_code),
            listed(prose(text), "A waiver whose `code` is ", " is refused at build, at its `code`"),
        ),
        "kinds": (
            [enum(properties(defs[kind])["acceptance"])[0] for kind in KINDS],
            cast(list[str], vocabulary("acceptances.json")["kinds"]),
        ),
    }
    problems = [
        f"{member}: {mine} against {theirs}" for member, (mine, theirs) in found.items() if mine != theirs
    ]
    parameters = distribution_parameters(document("uncertainty.md"))
    for conjunct in cast(list[Json], defs["distribution_parameters_binding"]["allOf"]):
        token = at(conjunct, "if", "properties", "distribution")["const"]
        given = at(conjunct, "then", "properties", "distribution_parameters")
        if given["required"] != parameters.pop(str(token), None):
            problems.append(f"{token}'s parameters are not uncertainty.md's")
    problems += [f"{token}'s parameters are not bound" for token in parameters]
    taken = {
        "want": (requirement["want"], "read_request.json#/$defs/want"),
        "represents": (requirement["represents"], "vocabulary/statistics.json#/$defs/represents"),
        "a requirement's label": (requirement["label"], "vocabulary/fields.json#/$defs/label"),
        "a waiver's label": (properties(defs["waiver"])["label"], "vocabulary/fields.json#/$defs/label"),
        "code": (properties(defs["waiver"])["code"], "vocabulary/reasons.json#/$defs/reason_code"),
        "method": (
            properties(defs["extrapolation"])["method"],
            "vocabulary/acceptances.json#/$defs/extrapolation_method",
        ),
        "distribution": (
            properties(defs["distribution"])["distribution"],
            "vocabulary/statistics.json#/$defs/distribution",
        ),
    }
    problems += [
        f"{member} takes {reference(node)}"
        for member, (node, target) in taken.items()
        if reference(node) != target
    ]
    return problems


def test_each_member_takes_the_tokens_the_text_gives_it() -> None:
    assert token_problems(document("declarations.md"), DECLARATION) == []


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ("`binary32` or `binary64` |", "`binary64` |", "precision"),
        (
            ", `outside_range`, `at_edge` and `range_unstated`;",
            ", `outside_range` and `at_edge`;",
            "codes that name",
        ),
        ("section 4 other than `condition_unknown_name`", "section 4 other than `no_pick`", "by the table"),
        ("whose `code` is `condition_unknown_name` is", "whose `code` is `no_pick` is", "by section 4.2"),
        ("`identity` or `log` (section 4.3)", "`identity` (section 4.3)", "space"),
    ],
)
def test_a_token_the_schema_does_not_take_is_found(old: str, new: str, problem: str) -> None:
    text = document("declarations.md")
    assert text.count(old) == 1
    assert any(problem in found for found in token_problems(text.replace(old, new), DECLARATION))


def test_a_list_taken_from_elsewhere_is_found() -> None:
    schema = copy.deepcopy(DECLARATION)
    properties(definitions(schema)["requirement"])["want"] = {"enum": ["value"]}
    cast(list[Json], definitions(schema)["distribution_parameters_binding"]["allOf"]).pop()
    found = token_problems(document("declarations.md"), schema)
    assert "want takes " in found
    assert "beta's parameters are not bound" in found


def binding_names(node: Json, member: str) -> list[str]:
    """The name each conjunct of a binding's `allOf` tests its `member` for."""
    return [
        str(at(conjunct, "if", "properties", member)["const"]) for conjunct in cast(list[Json], node["allOf"])
    ]


def name_problems(schema: Json) -> list[str]:
    """Where a list of names declaration.json writes differs from the vocabulary's, and where a binding refers
    to another name's row."""
    defs = definitions(schema)
    fields = list(at(vocabulary("fields.json"), "fields"))
    sections = list(at(vocabulary("fields.json"), "$defs", "sections", "properties"))
    conditions = cast(dict[str, Json], vocabulary("conditions.json")["conditions"])
    numeric = [name for name, row in conditions.items() if row["shape"] == "numeric"]
    tokens = [name for name, row in conditions.items() if row["shape"] == "token"]
    facts = cast(dict[str, Json], vocabulary("specimen_facts.json")["facts"])
    with_tokens = [name for name, row in facts.items() if row["tokens"]]
    implied = properties(defs["implied_condition"])["fact"]
    rows = cast(dict[str, Json], at(vocabulary("fields.json"), "fields"))
    no_parameter_set = [
        name for name, row in rows.items() if "parameter_set" not in cast(list[str], row["forms"])
    ]
    found = {
        "registered fields": (enum(defs["registered_field"]), fields),
        "registered sections": (enum(defs["registered_section"]), sections),
        "registered conditions": (enum(defs["registered_condition"]), list(conditions)),
        "registered facts": (enum(defs["registered_fact"]), list(facts)),
        "fields whose rows allow no parameter set": (
            enum(at(defs["parameter_set_field_name"], "not")),
            no_parameter_set,
        ),
        "operating conditions": (list(properties(defs["operating_conditions"])), numeric),
        "implied conditions": (list(properties(defs["implies"])), list(conditions)),
        "implied tokens": (list(properties(defs["implied_token_binding"])), tokens),
        "target facts": (list(properties(defs["target"])), list(facts)),
        "facts with tokens": (enum(implied), with_tokens),
        "fact token binding": (binding_names(defs["fact_token_binding"], "fact"), with_tokens),
        "difference value binding": (binding_names(defs["difference_value_binding"], "fact"), list(facts)),
        "label binding": (binding_names(defs["label_binding"], "field"), fields),
        "requirement condition binding": (
            list(properties(defs["requirement_condition_binding"])),
            list(conditions),
        ),
    }
    problems = [
        f"{what}: {mine} against {theirs}" for what, (mine, theirs) in found.items() if mine != theirs
    ]
    for name, bound in properties(defs["requirement_condition_binding"]).items():
        kind = "tolerance" if name in numeric else "accept"
        target = (
            f"vocabulary/conditions.json#/$defs/units/properties/{name}/properties/unit"
            if kind == "tolerance"
            else f"vocabulary/conditions.json#/$defs/{name}_token"
        )
        inner = at(bound, "properties", kind)
        given = at(inner, "properties", "unit") if kind == "tolerance" else at(inner, "items")
        if required(bound) != [kind] or reference(given) != target:
            problems.append(f"{name}'s requirement condition is bound to another row")
    for conjunct in cast(list[Json], defs["label_binding"]["allOf"]):
        field = at(conjunct, "if", "properties", "field")["const"]
        label = at(conjunct, "then", "properties", "label")
        if reference(label) != f"vocabulary/fields.json#/$defs/{field}/properties/label":
            problems.append(f"{field}'s label is bound to another row")
    return problems


def test_the_lists_of_names_are_the_vocabularys() -> None:
    assert name_problems(DECLARATION) == []


def test_a_list_of_names_that_drifts_is_found() -> None:
    schema = copy.deepcopy(DECLARATION)
    cast(list[str], definitions(schema)["registered_field"]["enum"]).pop()
    properties(definitions(schema)["operating_conditions"]).pop("specimen_size")
    conjuncts = cast(list[Json], definitions(schema)["label_binding"]["allOf"])
    conjuncts[0] = copy.deepcopy(conjuncts[2]) | {"if": conjuncts[0]["if"]}
    found = name_problems(schema)
    assert any(problem.startswith("registered fields") for problem in found)
    assert any(problem.startswith("operating conditions") for problem in found)
    assert "bulk.density's label is bound to another row" in found


# The report against read_result.json and case.json.

# The report's members that no build-check case compares until the scene suite's variants of the cases: a
# result read for a region or an interval holds it beside `record` (`declarations.md` section 2 item 2), and a
# watch at a region holds it.
SCENE_MEMBERS = {"region", "interval"}
# Each of case.json's definitions a build-check case compares, and the report's it stands for.
TWINS = {
    "compared_specimen_difference": "specimen_difference",
    "compared_watch": "watch",
    "compared_unused": "unused_acceptance",
}


def from_the_result(schema: JsonValue) -> JsonValue:
    """A part of read_result.json with its own references written as a file beside it writes them."""
    if isinstance(schema, dict):
        return {
            key: f"read_result.json{value}"
            if key == "$ref" and isinstance(value, str) and value.startswith("#")
            else from_the_result(value)
            for key, value in schema.items()
        }
    if isinstance(schema, list):
        return [from_the_result(item) for item in schema]
    return schema


ANNOTATIONS = {"title", "description", "$comment"}


def normal(schema: JsonValue, file: Json, twins: dict[str, str]) -> JsonValue:
    """A part of a schema as it constrains: without its annotations, each reference to one of the file's own
    definitions written out, but a twin's, which is named by the report's name of it."""
    if isinstance(schema, list):
        return [normal(item, file, twins) for item in schema]
    if not isinstance(schema, dict):
        return schema
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        name = reference.removeprefix("#/$defs/")
        if name in twins:
            return {"twin": twins[name]}
        return normal(definitions(file)[name], file, twins)
    return {key: normal(value, file, twins) for key, value in schema.items() if key not in ANNOTATIONS}


def compared(case: Json, report: Json, case_name: str, report_names: tuple[str, ...]) -> list[str]:
    """Where case.json's definition and the report's differ, member for member: a member one names and the
    others do not, but the report's scene members, or a member shaped otherwise."""
    mine = {
        member: normal(schema, case, TWINS)
        for member, schema in properties(definitions(case)[case_name]).items()
    }
    theirs: dict[str, JsonValue] = {}
    problems: list[str] = []
    report_twins = {name: name for name in TWINS.values()}
    for name in report_names:
        for member, schema in properties(definitions(report)[name]).items():
            shape = normal(schema, report, report_twins)
            if theirs.setdefault(member, shape) != shape:
                problems.append(f"the report's results shape {member} two ways")
    if extra := set(theirs) - set(mine) - SCENE_MEMBERS:
        problems.append(f"the report's {'/'.join(report_names)} names {sorted(extra)}, case.json's does not")
    if missing := set(mine) - set(theirs):
        problems.append(f"case.json's {case_name} names {sorted(missing)}, the report's does not")
    problems += [
        f"{case_name}'s {member} is shaped otherwise"
        for member in sorted(set(mine) & set(theirs))
        if mine[member] != theirs[member]
    ]
    return problems


def report_problems(case: Json, report: Json, result: Json) -> list[str]:
    """Where the report's results, watches, specimen differences and unused acceptances drift from case.json's
    build result and its twins, or a field result's read members from read_result.json's."""
    field = properties(definitions(report)["field_result"])
    read = cast(dict[str, Json], from_the_result(result["properties"]))
    problems = (
        [] if list(field)[: len(read)] == list(read) else ["a field result's read members are not the read's"]
    )
    problems += [
        f"a field result's {name} is not the read's" for name in read if field.get(name) != read[name]
    ]
    problems += compared(case, report, "compared_build_result", ("field_result", "combination_result"))
    for case_name, report_name in TWINS.items():
        problems += compared(case, report, case_name, (report_name,))
    return problems


def test_case_jsons_build_result_and_watch_are_the_reports() -> None:
    assert report_problems(CASE, REPORT, RESULT) == []


def a_report() -> Json:
    """A report as section 2 gives it, over BC-016's declaration: two results, one waived, no watches."""
    case = json.loads(
        (BUILD_CHECKS / "cases" / "BC-016.waiver_at_one_of_two_records.json").read_text("utf-8")
    )
    declaration = json.loads((BUILD_CHECKS / "inputs" / case["inputs"]["declaration"]).read_text("utf-8"))
    results = case["expected"]["results"]
    for result in results:
        result["specimen_differences"] = []
    return {
        "consumer": declaration["consumer"],
        "records": [result["record"] for result in results],
        "declaration": declaration,
        "refusals": [],
        "results": results,
        "unused": [],
    }


WATCH: Json = {
    "model": "drag",
    "record": {"id": "conformance/water_fixture", "version": "1.0.0", "content_hash": "sha256:0"},
    "field": "fluid.dynamic_viscosity",
    "condition": "temperature",
    "unit": "K",
    "source": "tolerance",
    "interval": [309.15, 311.15],
}


def _refused(report: Json) -> None:
    report["refusals"] = [{"item": "BC-048", "pointer": "/models/0/target"}]


def _refused_alone(report: Json) -> None:
    """A refused declaration's report: no results, nothing unused, its consumer and declaration as given."""
    _refused(report)
    report["results"] = []


def _refused_without(*members: str) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        _refused_alone(report)
        for member in members:
            del report[member]

    return change


def _refused_holding_a_consumer_it_does_not_declare(report: Json) -> None:
    _refused_alone(report)
    del cast(Json, report["declaration"])["consumer"]


def _refused_at_the_empty_pointer(declaration: JsonValue | None, *more: Json) -> Callable[[Json], None]:
    """A report of a declaration refused at the empty pointer, and of any refusals given beside it, holding
    the declaration given, and its consumer where it declares one; None for a text that is not JSON."""

    def change(report: Json) -> None:
        _refused_alone(report)
        report["refusals"] = [{"item": "BC-048", "pointer": ""}, *more]
        del report["consumer"], report["declaration"]
        if declaration is not None:
            report["declaration"] = declaration
            if isinstance(declaration, dict) and "consumer" in declaration:
                report["consumer"] = declaration["consumer"]

    return change


def _no_consumer(report: Json) -> None:
    del report["consumer"]


def _invalid_declaration(report: Json) -> None:
    del cast(Json, report["declaration"])["consumer"]


def _a_watch(report: Json) -> None:
    report["watches"] = [WATCH]


def _a_watch_with_both(report: Json) -> None:
    accept: JsonValue = ["pycnometer"]
    report["watches"] = [WATCH | {"accept": accept}]


def _a_watch_without_its_unit(report: Json) -> None:
    report["watches"] = [{name: held for name, held in WATCH.items() if name != "unit"}]


def _a_result_without_its_verdict(report: Json) -> None:
    del cast(list[Json], report["results"])[0]["accepted"]


def _a_combination(report: Json) -> None:
    result = cast(list[Json], report["results"])[0]
    kept = ("model", "record", "specimen_differences", "accepted", "accepted_by", "not_accepted")
    fields: JsonValue = ["bulk.density", "fluid.dynamic_viscosity"]
    report["results"] = [{name: result[name] for name in kept} | {"fields": fields}]


def _a_combination_with_a_status(report: Json) -> None:
    _a_combination(report)
    cast(list[Json], report["results"])[0]["status"] = "met"


def _a_pointer_that_is_not_one(report: Json) -> None:
    _refused_alone(report)
    cast(list[Json], report["refusals"])[0]["pointer"] = "models/0"


def _without(member: str) -> Callable[[Json], None]:
    """A report whose first result lacks the member."""

    def change(report: Json) -> None:
        del cast(list[Json], report["results"])[0][member]

    return change


def _a_combination_without(member: str) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        _a_combination(report)
        del cast(list[Json], report["results"])[0][member]

    return change


def _a_watch_changed(*removed: str, **given: JsonValue) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        watch = {name: held for name, held in WATCH.items() if name not in removed} | given
        report["watches"] = [watch]

    return change


def _an_unused_acceptance(**given: JsonValue) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        unused: Json = {"model": "drag", "acceptance": 0, **given}
        report["unused"] = [unused]

    return change


def _an_unused_acceptance_without_its_index(report: Json) -> None:
    report["unused"] = [{"model": "drag"}]


def _a_refused_report_with(member: str, held: JsonValue) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        _refused_alone(report)
        report[member] = held

    return change


def _a_refusal_changed(removed: str | None = None, **given: JsonValue) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        _refused_alone(report)
        refusal = cast(list[Json], report["refusals"])[0]
        report["refusals"] = [{name: held for name, held in refusal.items() if name != removed} | given]

    return change


def _a_report_without(member: str) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        del report[member]

    return change


def _records_that_are_no_references(report: Json) -> None:
    report["records"] = [{"id": "conformance/water_fixture"}]


def _unchanged(report: Json) -> None:
    pass


@pytest.mark.parametrize(
    ("change", "valid"),
    [
        (_unchanged, True),
        (_refused, False),
        (_refused_alone, True),
        (_refused_without("consumer", "declaration"), False),
        (_refused_without("consumer"), False),
        (_refused_without("declaration"), False),
        (_refused_holding_a_consumer_it_does_not_declare, False),
        (_refused_at_the_empty_pointer(None), True),
        (_refused_at_the_empty_pointer(None, {"item": "BC-048", "pointer": "/models"}), False),
        (_refused_at_the_empty_pointer(["a list"]), True),
        (_refused_at_the_empty_pointer({"models": []}), True),
        (
            _refused_at_the_empty_pointer(
                {"consumer": {"name": "a", "version": "1"}, "operating_conditions": {}}
            ),
            True,
        ),
        (_no_consumer, False),
        (_invalid_declaration, False),
        (_a_watch, True),
        (_a_watch_with_both, False),
        (_a_watch_without_its_unit, False),
        (_a_result_without_its_verdict, False),
        (_a_combination, True),
        (_a_combination_with_a_status, False),
        (_a_pointer_that_is_not_one, False),
        (_without("not_accepted"), False),
        (_without("model"), False),
        (_without("record"), False),
        (_without("specimen_differences"), False),
        (_a_combination_without("fields"), False),
        (_a_combination_without("record"), False),
        (_a_watch_changed("condition"), False),
        (_a_watch_changed("interval"), False),
        (_a_watch_changed("record"), False),
        (_a_watch_changed("record", region="lumen"), True),
        (_a_watch_changed("interval", "unit", accept=["pycnometer"]), True),
        (_a_watch_changed("interval", accept=["pycnometer"], unit="K"), False),
        (_a_watch_changed(source="declared"), True),
        (_a_watch_changed(source="measured"), False),
        (_a_refused_report_with("unused", [{"model": "drag", "acceptance": 0}]), False),
        (_a_refused_report_with("watches", [WATCH]), False),
        (_a_refused_report_with("watches", []), True),
        (_records_that_are_no_references, False),
        (_a_report_without("unused"), False),
        (_a_report_without("records"), False),
        (_a_report_without("results"), False),
        (_a_report_without("refusals"), False),
        (_an_unused_acceptance(), True),
        (_an_unused_acceptance(acceptance=-1), False),
        (_an_unused_acceptance_without_its_index, False),
        (_a_refusal_changed(item="bc-048"), False),
        (_a_refusal_changed(removed="pointer"), False),
        (_a_refusal_changed(removed="item"), False),
    ],
    ids=[
        "a_report",
        "refused_with_results",
        "refused_alone",
        "refused_without_its_consumer_and_declaration",
        "refused_without_its_consumer",
        "refused_without_its_declaration",
        "refused_holding_a_consumer_its_declaration_does_not_declare",
        "refused_as_a_text_that_is_not_json",
        "refused_at_the_empty_pointer_and_elsewhere_without_its_declaration",
        "refused_as_a_declaration_that_is_not_an_object",
        "refused_as_a_declaration_without_its_consumer",
        "refused_at_the_empty_pointer_holding_its_consumer",
        "no_consumer",
        "an_invalid_declaration_not_refused",
        "a_watch",
        "a_watch_with_an_interval_and_an_accept_list",
        "an_interval_watch_without_its_unit",
        "a_result_without_accepted",
        "a_combination",
        "a_combination_with_a_status",
        "a_pointer_that_is_not_one",
        "a_result_without_not_accepted",
        "a_result_without_its_model",
        "a_result_without_its_record",
        "a_result_without_specimen_differences",
        "a_combination_without_its_fields",
        "a_combination_without_its_record",
        "a_watch_without_its_condition",
        "a_watch_with_neither_interval_nor_accept",
        "a_watch_at_no_location",
        "a_watch_at_a_region",
        "an_accept_list_watch_without_a_unit",
        "an_accept_list_watch_with_a_unit",
        "a_watch_of_source_declared",
        "a_watch_of_a_source_that_is_none",
        "a_refused_report_listing_unused",
        "a_refused_report_holding_watches",
        "a_refused_report_holding_no_watches",
        "records_that_are_no_references",
        "a_report_without_unused",
        "a_report_without_records",
        "a_report_without_results",
        "a_report_without_refusals",
        "an_unused_acceptance",
        "an_unused_acceptance_of_index_minus_one",
        "an_unused_acceptance_without_its_index",
        "a_refusal_whose_item_is_no_case",
        "a_refusal_without_its_pointer",
        "a_refusal_without_its_item",
    ],
)
def test_the_report_schema_takes_a_report_and_refuses_what_section_2_does_not_give(
    change: Callable[[Json], None], valid: bool
) -> None:
    report = a_report()
    change(report)
    assert agreed("build_report.json")(report) is valid


def _reshape_a_read_member(case: Json, report: Json, result: Json) -> None:
    properties(result)["value"] = {"type": "number"}


def _drop_a_watch_member(case: Json, report: Json, result: Json) -> None:
    properties(definitions(report)["watch"]).pop("unit")


def _a_case_member_the_report_lacks(case: Json, report: Json, result: Json) -> None:
    properties(definitions(case)["compared_build_result"])["score"] = {"type": "number"}


def _reshape_a_difference(case: Json, report: Json, result: Json) -> None:
    properties(definitions(report)["specimen_difference"])["section"] = {"enum": ["bulk"]}


def _a_report_member_the_case_lacks(case: Json, report: Json, result: Json) -> None:
    properties(definitions(report)["combination_result"])["status"] = {"type": "string"}


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (_reshape_a_read_member, "a field result's value is not the read's"),
        (_drop_a_watch_member, "case.json's compared_watch names ['unit']"),
        (_a_case_member_the_report_lacks, "case.json's compared_build_result names ['score']"),
        (_reshape_a_difference, "compared_specimen_difference's section is shaped otherwise"),
        (_a_report_member_the_case_lacks, "the report's results shape status two ways"),
    ],
)
def test_a_report_that_drifts_from_the_cases_is_found(
    change: Callable[[Json, Json, Json], None], problem: str
) -> None:
    case, report, result = copy.deepcopy(CASE), copy.deepcopy(REPORT), copy.deepcopy(RESULT)
    change(case, report, result)
    assert any(found.startswith(problem) for found in report_problems(case, report, result))


# The report's required members, by section 2, section 3 item 6, section 8 item 1 and section 1's refusals.

# The members the report requires only when it holds no refusal (`refusal_rule`), and the one a build that
# does not yet emit watches omits (section 2 lists it; S7a-4 makes it required).
REQUIRED_WITHOUT_A_REFUSAL = {"consumer", "declaration"}
OMITTED_WITHOUT_WATCHES = {"watches"}
BRACED = re.compile(r"\{([^{}]*)\}")
BRACED_MEMBER = re.compile(r'(?:(?<=\{)|(?<=, ))"(\w+)"(\?)?')


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def braced(text: str, anchor: str) -> list[tuple[str, bool]]:
    """The members of the first object written in braces after `anchor`, each with whether it is required (not
    followed by `?`). A member's value, `"source": "tolerance"`, is no member."""
    after = flat(text).partition(anchor)[2]
    assert after, anchor
    found = BRACED.search(after)
    assert found, anchor
    return [(member[1], not member[2]) for member in BRACED_MEMBER.finditer(found[0])]


def required_braced(text: str, anchor: str) -> set[str]:
    return {name for name, needed in braced(text, anchor) if needed}


def section_8(text: str) -> str:
    return text[text.index("## 8. Run-time watches") :]


def report_required_problems(text: str, report: Json, result: Json) -> list[str]:
    """Where the report's members and required lists differ from the text's: the seven members of the report
    (section 2), the members a field result adds to the read result's, a combination result's (section 3
    item 6), a watch's (section 8 item 1), an unused acceptance's (section 2 item 9) and a refusal's
    (section 1)."""
    problems: list[str] = []

    def agree(place: str, schema: set[str], text_gives: set[str]) -> None:
        if schema != text_gives:
            problems.append(f"{place} requires {sorted(schema)}, the text {sorted(text_gives)}")

    definition_of = definitions(report)
    paragraph = flat(text).partition("The build gives one report:")[2].partition("A declaration the build")[0]
    members = set(re.findall(r"- `([a-z_]+)`", paragraph))
    agree("the report's members", set(properties(report)), members)
    agree(
        "the report",
        set(required(report)),
        members - REQUIRED_WITHOUT_A_REFUSAL - OMITTED_WITHOUT_WATCHES,
    )
    without_a_refusal = at(definition_of["refusal_rule"], "else")
    agree("a report without a refusal", set(required(without_a_refusal)), REQUIRED_WITHOUT_A_REFUSAL)

    added = flat(text).partition("The build reads every required field")[2].partition(" and, on a result")[0]
    agree(
        "a field result",
        set(required(definition_of["field_result"])),
        set(required(result)) | set(re.findall(r"`([a-z_]+)`", added.partition("with")[2])),
    )
    agree(
        "a combination result",
        set(required(definition_of["combination_result"])),
        required_braced(text, "returns one result per combination:"),
    )
    agree(
        "a watch",
        set(required(definition_of["watch"])) | set(required(at(definition_of["watch_rule"], "then"))),
        required_braced(section_8(text), "1. The build emits watches"),
    )
    agree(
        "an unused acceptance",
        set(required(definition_of["unused_acceptance"])),
        required_braced(text, "9. The build lists in `unused`"),
    )
    agree(
        "a refusal", set(required(definition_of["build_refusal"])), required_braced(text, "Each refusal is")
    )
    return problems


def test_the_reports_required_members_are_those_of_the_text() -> None:
    assert report_required_problems(document("declarations.md"), REPORT, RESULT) == []


def _no_longer_required(place: str, member: str) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        required(definitions(report)[place]).remove(member)

    return change


def _newly_required(place: str, member: str) -> Callable[[Json], None]:
    def change(report: Json) -> None:
        required(definitions(report)[place]).append(member)

    return change


def _report_no_longer_requiring_unused(report: Json) -> None:
    required(report).remove("unused")


def _report_requiring_watches(report: Json) -> None:
    required(report).append("watches")


def _report_without_watches(report: Json) -> None:
    del properties(report)["watches"]


def _a_refusal_rule_without_the_consumer(report: Json) -> None:
    required(at(definitions(report)["refusal_rule"], "else")).remove("consumer")


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (_no_longer_required("field_result", "not_accepted"), "a field result requires"),
        (_no_longer_required("field_result", "specimen_differences"), "a field result requires"),
        (_newly_required("field_result", "trainable_by"), "a field result requires"),
        (_newly_required("field_result", "region"), "a field result requires"),
        (_no_longer_required("combination_result", "fields"), "a combination result requires"),
        (_newly_required("combination_result", "region"), "a combination result requires"),
        (_no_longer_required("watch", "condition"), "a watch requires"),
        (_newly_required("watch", "record"), "a watch requires"),
        (_no_longer_required("unused_acceptance", "acceptance"), "an unused acceptance requires"),
        (_no_longer_required("build_refusal", "pointer"), "a refusal requires"),
        (_newly_required("build_refusal", "detail"), "a refusal requires"),
        (_report_no_longer_requiring_unused, "the report requires"),
        (_report_requiring_watches, "the report requires"),
        (_report_without_watches, "the report's members"),
        (_a_refusal_rule_without_the_consumer, "a report without a refusal requires"),
    ],
)
def test_a_required_list_that_drifts_from_the_text_is_found(
    change: Callable[[Json], None], problem: str
) -> None:
    report = copy.deepcopy(REPORT)
    change(report)
    assert any(
        found.startswith(problem)
        for found in report_required_problems(document("declarations.md"), report, RESULT)
    )


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ("- `unused` (item 9).", "- `unused_items` (item 9).", "the report's members"),
        ("`not_accepted` and, on a result", "and, on a result", "a field result requires"),
        (
            '"accepted_by", "not_accepted"}`, each difference',
            '"accepted_by"}`, each difference',
            "a combination result",
        ),
        ('"unit",\n   "source": "tolerance"}', '"source": "tolerance"}', "a watch requires"),
        ('"acceptance": <its index>}', '"index": <its index>}', "an unused acceptance requires"),
        ('"pointer", "detail"?}', '"pointer", "detail"}', "a refusal requires"),
    ],
)
def test_a_text_that_drifts_from_the_required_lists_is_found(old: str, new: str, problem: str) -> None:
    text = document("declarations.md")
    assert text.count(old) == 1, old
    assert any(
        found.startswith(problem)
        for found in report_required_problems(text.replace(old, new), REPORT, RESULT)
    )


# The build-check cases against declaration.json.

BUILD_CHECKS = PACKAGE / "data" / "conformance" / "build_checks"
# Each file whose case expects the declaration refused and which declaration.json takes, with the rule that
# refuses it, which the schema does not state: a name given twice where the members beside it differ, a field
# or location set against another member, a rule beside the table of the shape, a build's claims. A schema
# could state some of these (two requirements for one field, a field not in `reads`, a combination of one
# section), but only with one conjunct for each registered name, written again for each name the vocabulary
# adds, where the build's check states each once. None can state two models of one name or two trainable
# entries for one field at one location: a model's name and an entry's location are values no registry lists,
# and no JSON Schema compares a free value across the items of an array. An identical duplicate it refuses,
# by `uniqueItems`, which compares whole items.
SCHEMA_DOES_NOT_STATE = {
    "BC-048.duplicate_member_not_json": "not JSON by record_format.md section 1 item 6: a member given twice",
    "BC-048.requirement_for_field_not_read": "a requirement for a field its model does not list in reads",
    "BC-048.trainable_field_not_read": "a trainable entry for a field its model does not list in reads",
    "BC-048.trainable_record_not_checked_over": "a trainable entry at a location its model is not checked"
    " over",
    "BC-048.two_models_of_one_name": "two models of one name",
    "BC-048.two_requirements_for_one_field": "two requirements for one field",
    "BC-050.requirement_without_review": "section 4.1 item 4: a waiver naming a label needs its requirement's"
    " review",
    "BC-051.checked_over_domain": "section 1 item 12: a domain, without the scene suite",
    "BC-051.checked_over_path": "section 1 item 12: a path, without the scene suite",
    "BC-051.distribution_acceptance": "section 1 item 12: a distribution, without the sampling suite",
    "BC-051.engine_over_domain": "section 1 item 12: a domain and engine, without the scene suite or USD"
    " read",
    "BC-051.region_conditions": "section 1 item 12: region_conditions, without the scene suite",
    "BC-051.represents_beside_sampling": "section 1 item 12: represents and sampling, without the sampling"
    " suite",
    "BC-051.sampling_block": "section 1 item 12: sampling, without the sampling suite",
}


Case = tuple[str, JsonValue | Reason, list[str]]


def build_cases(root: Path = BUILD_CHECKS) -> Iterator[Case]:
    """Each build-check case's name, its declaration as the build reads it (`jsonio.parse`, which gives a
    reason for a text that is not JSON), and the pointers of the refusals it expects."""
    for path in sorted((root / "cases").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        text = (root / "inputs" / case["inputs"]["declaration"]).read_bytes()
        pointers = [str(refusal["pointer"]) for refusal in case["expected"].get("refusals", [])]
        yield path.stem, jsonio.parse(text), pointers


def error_paths(value: JsonValue) -> set[str]:
    """Where python-jsonschema finds declaration.json's errors in a value, as JSON pointers."""
    checker = Draft202012Validator({"$ref": BASE + "declaration.json"}, registry=registry())
    # types-jsonschema types its second overload's instance as unknown.
    found = checker.iter_errors(value)  # pyright: ignore[reportUnknownMemberType]
    return {"".join(f"/{step}" for step in error.absolute_path) for error in found}


def case_problems(cases: list[Case], not_stated: dict[str, str]) -> list[str]:
    """Where a build-check case and declaration.json disagree: a declaration expected to pass that the
    schema refuses; one expected refused that it takes and the table does not list, or that it refuses
    nowhere at or above a pointer the case expects; and a listed file that is not one of those."""
    takes = agreed("declaration.json")
    problems: list[str] = []
    listed_now: set[str] = set()
    for name, value, pointers in cases:
        if isinstance(value, Reason):
            listed_now.add(name)
            continue
        valid = takes(value)
        if not pointers:
            if not valid:
                problems.append(f"{name}: expected to pass, refused")
        elif valid:
            listed_now.add(name)
        elif not any(pointer.startswith(path) for path in error_paths(value) for pointer in pointers):
            problems.append(f"{name}: refused, but nowhere at or above {pointers}")
    problems += [
        f"{name}: refused by the schema, or not a file, but listed" for name in set(not_stated) - listed_now
    ]
    problems += [f"{name}: taken by the schema and not listed" for name in listed_now - set(not_stated)]
    return problems


CASES = list(build_cases())


def test_every_build_check_declaration_is_judged_as_its_case_expects() -> None:
    assert case_problems(CASES, SCHEMA_DOES_NOT_STATE) == []


def test_a_listing_that_drifts_from_the_cases_is_found() -> None:
    stale = SCHEMA_DOES_NOT_STATE | {"BC-048.json_array": "a JSON array"}
    missing = {
        name: rule
        for name, rule in SCHEMA_DOES_NOT_STATE.items()
        if name != "BC-050.requirement_without_review"
    }
    assert "BC-048.json_array: refused by the schema, or not a file, but listed" in case_problems(
        CASES, stale
    )
    assert "BC-050.requirement_without_review: taken by the schema and not listed" in case_problems(
        CASES, missing
    )


def test_a_schema_that_judges_otherwise_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """The control: declaration.json with a model entry's required list cut to `model` takes the files whose
    declarations lack target or reads, and the check lists them."""
    schema = copy.deepcopy(DECLARATION)
    definitions(schema)["model_entry"]["required"] = ["model"]
    taken_by = agreed

    def mutant(reference: str) -> Callable[[JsonValue], bool]:
        return taken_by(BASE + reference, (schema,))

    monkeypatch.setattr(f"{__name__}.agreed", mutant)
    found = case_problems(CASES, SCHEMA_DOES_NOT_STATE)
    assert "BC-048.target_missing: taken by the schema and not listed" in found


def test_a_schema_that_refuses_what_its_case_expects_taken_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """The control: declaration.json with `mixing` required refuses the files that expect no refusal and
    hold none, and the check lists them as expected to pass and refused."""
    schema = copy.deepcopy(DECLARATION)
    required(definitions(schema)["model_entry"]).append("mixing")
    taken_by = agreed

    def mutant(reference: str) -> Callable[[JsonValue], bool]:
        return taken_by(BASE + reference, (schema,))

    monkeypatch.setattr(f"{__name__}.agreed", mutant)
    found = case_problems(CASES, SCHEMA_DOES_NOT_STATE)
    assert "BC-016.waiver_at_one_of_two_records: expected to pass, refused" in found


def test_a_refusal_at_another_place_than_the_cases_is_found() -> None:
    """The control: a file the schema refuses at its acceptance 0, whose case is made to expect the refusal
    at acceptance 1, is refused nowhere at or above where the case points."""
    name = "BC-005.waiver_without_reason"
    pointer = "/models/0/acceptances/1"
    assert [pointers for found, _, pointers in CASES if found == name] == [["/models/0/acceptances/0"]]
    moved = [(found, value, [pointer] if found == name else pointers) for found, value, pointers in CASES]
    assert f"{name}: refused, but nowhere at or above ['{pointer}']" in case_problems(
        moved, SCHEMA_DOES_NOT_STATE
    )


# Closure: every place a valid declaration reaches refuses a member the table does not name.

# The maps whose keys are the consumer's own names: a member added there is a key, not an unknown member.
FREE_MAPS = {"region_conditions", "state_mapping", "values", "region_values"}


def objects(value: JsonValue, pointer: str = "", key: str = "") -> Iterator[str]:
    """The pointer of each object in a declaration but the free maps."""
    if isinstance(value, dict):
        if key not in FREE_MAPS:
            yield pointer
        for name, held in value.items():
            yield from objects(held, f"{pointer}/{name}", name)
    elif isinstance(value, list):
        for index, held in enumerate(value):
            yield from objects(held, f"{pointer}/{index}", key)


UNKNOWN = "unknown_member"


def with_member(value: JsonValue, pointer: str, shaped: bool) -> JsonValue:
    """The declaration with a member the table does not name added at `pointer`: a string, or, where the
    object holds a member, a copy of its first member's value, which is well shaped where that member is (a
    string is refused wherever a type is checked, not wherever the place is closed)."""
    changed = copy.deepcopy(value)
    node = changed
    for step in filter(None, pointer.split("/")):
        node = node[int(step)] if isinstance(node, list) else cast(dict[str, JsonValue], node)[step]
    members = cast(dict[str, JsonValue], node)
    members[UNKNOWN] = copy.deepcopy(next(iter(members.values()))) if shaped and members else "a member"
    return changed


def open_places(schema_reference: str, files: tuple[Json, ...] = ()) -> list[str]:
    """Each place of a valid build-check declaration that takes a member the table does not name, as a string
    and as a copy of a sibling's value."""
    takes = agreed(schema_reference, files)
    found: list[str] = []
    for name, value in valid_declarations():
        for pointer in objects(value):
            found += [
                f"{name}{pointer}" for shaped in (False, True) if takes(with_member(value, pointer, shaped))
            ]
    return sorted(set(found))


def test_every_place_a_declaration_reaches_is_closed() -> None:
    assert open_places("declaration.json") == []


def test_an_open_place_is_found() -> None:
    schema = copy.deepcopy(DECLARATION)
    definitions(schema)["requirement"].pop("additionalProperties")
    found = open_places(BASE + "declaration.json", (schema,))
    assert found
    assert all(re.search(r"/models/\d+/requirements/\d+$", place) for place in found)


def test_a_place_that_checks_its_values_but_not_its_members_is_found() -> None:
    """`implies` refuses a string it is given as a member by the type of its values (the read request's), and
    a well-shaped value, a copy of the condition beside it, only by being closed. The control opens it."""
    schema = copy.deepcopy(DECLARATION)
    definitions(schema)["implies"].pop("additionalProperties")
    found = open_places(BASE + "declaration.json", (schema,))
    assert found
    assert all(place.endswith("/implies") for place in found)
    takes = agreed("declaration.json", (schema,))
    shaped = [
        (value, pointer)
        for _, value in valid_declarations()
        for pointer in objects(value)
        if pointer.endswith("/implies")
    ]
    assert shaped
    assert not any(takes(with_member(value, pointer, shaped=False)) for value, pointer in shaped)


def visited() -> tuple[set[str], set[str]]:
    """The kinds of place and the acceptance kinds of the valid declarations the closure check visits."""
    places: set[str] = set()
    kinds: set[str] = set()
    for _, value in valid_declarations():
        for pointer in objects(value):
            places.add(re.sub(r"/\d+", "/N", pointer))
            node = copy.deepcopy(cast(JsonValue, value))
            for step in filter(None, pointer.split("/")):
                node = node[int(step)] if isinstance(node, list) else cast(dict[str, JsonValue], node)[step]
            kind = cast(Json, node).get("acceptance")
            if isinstance(kind, str):
                kinds.add(kind)
    return places, kinds


# The places the closure check must reach, one for each place of the table of the shape.
REACHED = {
    "",
    "/consumer",
    "/models/N",
    "/models/N/model",
    "/models/N/checked_over",
    "/models/N/checked_over/records/N",
    "/models/N/requirements/N",
    "/models/N/requirements/N/conditions/temperature",
    "/models/N/acceptances/N",
    "/models/N/trainable/N",
    "/models/N/mixing",
    "/models/N/engine",
    "/models/N/engine/crosswalk",
    "/models/N/region_conditions/lumen",
    "/sampling",
    "/sampling/independence/N",
}


def test_the_closure_check_reaches_every_place_of_the_table() -> None:
    places, kinds = visited()
    assert REACHED <= places
    assert kinds == set(KINDS)


def test_a_closure_check_that_skips_a_place_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """The control: with the acceptances taken for a free map, no acceptance object is visited and the check
    above says so."""
    monkeypatch.setattr(f"{__name__}.FREE_MAPS", FREE_MAPS | {"acceptances"})
    places, kinds = visited()
    assert not REACHED <= places
    assert kinds != set(KINDS)


# Each rule and binding of declaration.json, applied where it belongs: a declaration with one fault it refuses
# is refused, and one beside it that it takes is taken.

WATER: JsonValue = {"id": "conformance/water_fixture", "version": "1.0.0", "content_hash": "sha256:0"}


def a_declaration() -> Json:
    """BC-016's declaration, valid: one model over two records, a requirement with a label and two
    tolerances, and a waiver."""
    case = json.loads(
        (BUILD_CHECKS / "cases" / "BC-016.waiver_at_one_of_two_records.json").read_text("utf-8")
    )
    return cast(
        Json, json.loads((BUILD_CHECKS / "inputs" / case["inputs"]["declaration"]).read_text("utf-8"))
    )


def model(declaration: Json) -> Json:
    return cast(list[Json], declaration["models"])[0]


def requirement(declaration: Json) -> Json:
    return cast(list[Json], model(declaration)["requirements"])[0]


def conditions(declaration: Json) -> Json:
    return at(requirement(declaration), "conditions")


def with_acceptance(acceptance: Json) -> Callable[[Json], None]:
    def change(declaration: Json) -> None:
        cast(list[JsonValue], model(declaration)["acceptances"]).append(acceptance)

    return change


def at_water(members: Json) -> Json:
    return {"record": WATER, "field": "fluid.dynamic_viscosity", "reason": "a reason"} | members


def sampled(represents: str, level: bool) -> Callable[[Json], None]:
    def change(declaration: Json) -> None:
        declaration["sampling"] = {"min_acceptance": 0.9, "reason": "a reason", "independence": []}
        requirement(declaration)["represents"] = represents
        if level:
            requirement(declaration)["population_level"] = {"level": "donor", "within": {"status": "none"}}

    return change


def implied(fact: str, token: str, implies: Json) -> Callable[[Json], None]:
    members: Json = {"acceptance": "implied_condition", "fact": fact, "token": token, "implies": implies}
    return with_acceptance(at_water(members))


def difference(fact: str, value: JsonValue) -> Callable[[Json], None]:
    members: Json = {"acceptance": "accepted_difference", "section": "fluid", "fact": fact, "value": value}
    return with_acceptance(members | {"reason": "a reason"})


def distribution(parameters: Json) -> Callable[[Json], None]:
    members: Json = {
        "acceptance": "distribution",
        "distribution": "normal",
        "space": "identity",
        "distribution_parameters": parameters,
        "basis": "a basis",
    }
    return with_acceptance(at_water(members))


def nominal(members: Json) -> Callable[[Json], None]:
    kind: Json = {"acceptance": "nominal", "basis": "a basis"}
    return with_acceptance(at_water(kind | members))


def waiver(members: Json) -> Callable[[Json], None]:
    kind: Json = {"acceptance": "waiver"}
    return with_acceptance(at_water(kind | members))


def requirement_label(label: str) -> Callable[[Json], None]:
    return lambda declaration: requirement(declaration).update(label=label)


def tolerance_unit(unit: str) -> Callable[[Json], None]:
    return lambda declaration: at(conditions(declaration), "temperature", "tolerance").update(unit=unit)


def accepted(tokens: JsonValue) -> Callable[[Json], None]:
    return lambda declaration: conditions(declaration).update(
        test_method={"accept": tokens, "reason": "a reason"}
    )


def temperature_as_accept_list(declaration: Json) -> None:
    conditions(declaration)["temperature"] = {"accept": ["apparent"], "reason": "a reason"}


def operating_unit(declaration: Json) -> None:
    at(declaration, "operating_conditions", "temperature")["unit"] = "Cel"


def target(fact: Json) -> Callable[[Json], None]:
    return lambda declaration: model(declaration).update(target=fact)


def families(declaration: Json) -> None:
    model(declaration)["families"] = {"fluid.dynamic_viscosity": "materica.fluid.cross.v1"}


def at_other_location(location: Json) -> Callable[[Json], None]:
    """A waiver that names the location given in place of a record."""
    members: Json = {"acceptance": "waiver", "field": "fluid.dynamic_viscosity", "code": "no_requirement"}
    return with_acceptance(members | location | {"reason": "a reason"})


def a_pick(members: Json) -> Callable[[Json], None]:
    kind: Json = {"acceptance": "pick", "index": 0}
    return with_acceptance(at_water(kind | members))


def an_overlay_scope(accepts: JsonValue) -> Callable[[Json], None]:
    scope: Json = {"acceptance": "overlay_scope", "overlay": WATER, "accepts": accepts, "reason": "a reason"}
    return with_acceptance(scope)


def trainable(*entries: Json) -> Callable[[Json], None]:
    return lambda declaration: model(declaration).update(trainable=list(entries))


def population_level(level: Json) -> Callable[[Json], None]:
    def change(declaration: Json) -> None:
        sampled("population", level=False)(declaration)
        requirement(declaration)["population_level"] = level

    return change


def independence(entry: Json) -> Callable[[Json], None]:
    def change(declaration: Json) -> None:
        sampled("estimate", level=False)(declaration)
        cast(Json, declaration["sampling"])["independence"] = [entry]

    return change


def engine_value(value: Json) -> Callable[[Json], None]:
    pin: Json = {"id": "a crosswalk", "version": "1", "sha256": "a hash"}
    return lambda declaration: model(declaration).update(engine={"crosswalk": pin, "values": {"a": value}})


def mixing(tolerance: float) -> Callable[[Json], None]:
    return lambda declaration: model(declaration).update(
        mixing={"fraction_sum_tolerance": tolerance, "rules": {}}
    )


def region_conditions(conditions: Json) -> Callable[[Json], None]:
    return lambda declaration: model(declaration).update(region_conditions={"lumen": conditions})


def twice(place: str) -> Callable[[Json], None]:
    """The first entry of a list, given again unchanged: a model, a requirement or a trainable entry."""

    def change(declaration: Json) -> None:
        if place == "models":
            cast(list[Json], declaration["models"]).append(copy.deepcopy(model(declaration)))
        else:
            entries = cast(
                list[Json], model(declaration).setdefault(place, [{"field": "bulk.density", "record": WATER}])
            )
            entries.append(copy.deepcopy(entries[0]))

    return change


def requirement_again(**given: JsonValue) -> Callable[[Json], None]:
    """A second requirement for the field of the first, which differs from it by the members given."""

    def change(declaration: Json) -> None:
        cast(list[Json], model(declaration)["requirements"]).append(requirement(declaration) | given)

    return change


def a_sampling_acceptance_of_zero(declaration: Json) -> None:
    sampled("estimate", level=False)(declaration)
    cast(Json, declaration["sampling"])["min_acceptance"] = 0


PROBES: list[tuple[str, Callable[[Json], None], bool]] = [
    ("the_requirement_labels_its_field", requirement_label("materica.fluid.newtonian.v1"), True),
    ("another_fields_label", requirement_label("materica.magnetic.linear.v1"), False),
    ("a_tolerance_in_another_unit", tolerance_unit("Cel"), False),
    ("a_numeric_condition_given_an_accept_list", temperature_as_accept_list, False),
    ("an_accept_list_of_the_rows_tokens", accepted(["pycnometer"]), True),
    ("an_accept_list_with_a_slip", accepted(["pycnometr"]), False),
    ("an_empty_accept_list", accepted([]), False),
    ("an_operating_condition_in_another_unit", operating_unit, False),
    ("a_population_with_its_level", sampled("population", level=True), True),
    ("a_population_without_its_level", sampled("population", level=False), False),
    ("an_estimate_beside_sampling", sampled("estimate", level=False), True),
    ("an_estimate_without_sampling", lambda d: requirement(d).update(represents="estimate"), False),
    (
        "a_waiver_naming_its_codes_condition",
        waiver({"code": "outside_range", "condition": "temperature"}),
        True,
    ),
    ("a_waiver_without_its_codes_condition", waiver({"code": "range_unstated"}), False),
    (
        "a_waiver_naming_a_condition_its_code_does_not",
        waiver({"code": "unit_mismatch", "condition": "temperature"}),
        False,
    ),
    (
        "a_waiver_with_no_location",
        with_acceptance(
            {
                "acceptance": "waiver",
                "field": "fluid.dynamic_viscosity",
                "code": "no_requirement",
                "reason": "a reason",
            }
        ),
        False,
    ),
    (
        "an_implied_token_of_its_fact",
        implied("tissue_state", "in_vivo", {"temperature": {"value": 310.15, "unit": "K"}}),
        True,
    ),
    ("an_implied_token_of_another_fact", implied("tissue_state", "normal", {}), False),
    (
        "an_implied_token_condition_off_its_row",
        implied("tissue_state", "in_vivo", {"density_kind": {"token": "bulk"}}),
        False,
    ),
    (
        "an_implied_value_in_another_unit",
        implied("tissue_state", "in_vivo", {"temperature": {"value": 37.0, "unit": "Cel"}}),
        False,
    ),
    ("a_differences_value_in_its_facts_shape", difference("species", {"ncbi_taxon": 9606}), True),
    (
        "a_differences_value_in_another_facts_shape",
        difference("species", {"uberon": "UBERON:0000178"}),
        False,
    ),
    (
        "a_mimics_value_inferred",
        difference("mimics", {"text": "blood", "basis": "inferred", "inferred_from": "a"}),
        False,
    ),
    ("a_normals_parameters", distribution({"mean": 1.0, "sd": 0.1}), True),
    ("a_normal_with_a_uniforms_parameters", distribution({"lower": 0.0, "upper": 1.0}), False),
    ("a_nominal_value", nominal({"value": 0.001}), True),
    ("a_nominal_value_and_params", nominal({"value": 0.001, "params": {"mu": 1.0}}), False),
    ("a_nominal_params_for_a_field_with_no_parameter_set", nominal({"params": {"mu": 1.0}}), False),
    ("a_family_for_a_field_with_no_parameter_set", families, False),
    ("a_target_age_in_seconds", target({"donor_age": {"range": [1.0e8, 2.0e9], "unit": "s"}}), True),
    ("a_target_age_in_years", target({"donor_age": {"range": [3.0, 60.0], "unit": "a"}}), False),
    (
        "a_target_age_holding_value_and_range",
        target({"donor_age": {"value": 1.0, "range": [1.0, 2.0], "unit": "s"}}),
        False,
    ),
    # The constraints the table's Holds cells give as keywords, and the rules beside them.
    ("a_waiver_at_a_region", at_other_location({"region": "lumen"}), True),
    ("a_waiver_at_an_interval", at_other_location({"interval": [1.0, 2.0]}), True),
    ("a_pick_at_a_record_and_a_region", a_pick({"region": "lumen"}), True),
    ("a_pick_index_of_one", a_pick({"index": 1}), True),
    # `basis` is a member of an extrapolation, a nominal and a distribution alone (the maintainer's ruling of
    # 2026-10-24): every other kind holding one is refused.
    ("a_pick_with_a_basis", a_pick({"basis": "a basis"}), False),
    (
        "an_implied_condition_with_a_basis_of_its_own",
        lambda d: with_acceptance(
            at_water(
                {
                    "acceptance": "implied_condition",
                    "fact": "tissue_state",
                    "token": "in_vivo",
                    "implies": {},
                    "basis": "a basis",
                }
            )
        )(d),
        False,
    ),
    ("a_waiver_with_a_basis", waiver({"code": "no_requirement", "basis": "a basis"}), False),
    (
        "an_accepted_difference_with_a_basis",
        with_acceptance(
            {
                "acceptance": "accepted_difference",
                "section": "fluid",
                "fact": "species",
                "value": "any",
                "reason": "a reason",
                "basis": "a basis",
            }
        ),
        False,
    ),
    (
        "an_overlay_with_a_basis",
        with_acceptance(
            {
                "acceptance": "overlay",
                "field": "fluid.dynamic_viscosity",
                "overlay": WATER,
                "reason": "a reason",
                "basis": "a basis",
            }
        ),
        False,
    ),
    (
        "an_overlay_scope_with_a_basis",
        with_acceptance(
            {
                "acceptance": "overlay_scope",
                "overlay": WATER,
                "accepts": ["model"],
                "reason": "a reason",
                "basis": "a basis",
            }
        ),
        False,
    ),
    ("a_nominal_with_its_basis", nominal({"value": 0.001}), True),
    ("two_identical_models", twice("models"), False),
    ("two_identical_requirements", twice("requirements"), False),
    ("two_identical_trainable_entries", twice("trainable"), False),
    # A name given twice where the members differ is the build's, not the schema's (the description's list).
    ("two_requirements_for_one_field_that_differ", requirement_again(want="bounds"), True),
    ("a_pick_index_of_minus_one", a_pick({"index": -1}), False),
    ("a_pick_index_with_a_fraction", a_pick({"index": 1.5}), False),
    (
        "an_overlay",
        with_acceptance(
            {
                "acceptance": "overlay",
                "field": "fluid.dynamic_viscosity",
                "overlay": WATER,
                "reason": "a reason",
            }
        ),
        True,
    ),
    ("an_overlay_scope_accepting_two_tokens", an_overlay_scope(["model", "consumer"]), True),
    ("an_overlay_scope_accepting_a_token_twice", an_overlay_scope(["model", "model"]), False),
    ("an_overlay_scope_accepting_nothing", an_overlay_scope([]), False),
    (
        "a_trainable_entry_at_a_record",
        trainable({"field": "fluid.dynamic_viscosity", "record": WATER}),
        True,
    ),
    (
        "a_trainable_entry_at_a_record_and_a_region",
        trainable({"field": "fluid.dynamic_viscosity", "record": WATER, "region": "lumen"}),
        False,
    ),
    ("a_trainable_entry_at_no_location", trainable({"field": "fluid.dynamic_viscosity"}), False),
    ("a_sampling_acceptance_of_zero", a_sampling_acceptance_of_zero, False),
    (
        "an_independence_entry_with_its_basis",
        independence({"fields": ["fluid.dynamic_viscosity"], "reason": "a reason", "basis": "a basis"}),
        True,
    ),
    (
        "an_independence_entry_without_its_basis",
        independence({"fields": ["fluid.dynamic_viscosity"], "reason": "a reason"}),
        False,
    ),
    ("a_mixing_tolerance_of_zero", mixing(0.0), True),
    ("a_negative_mixing_tolerance", mixing(-1.0e-9), False),
    (
        "a_combination_of_two_fields",
        lambda d: model(d).update(combinations=[["bulk.density", "fluid.dynamic_viscosity"]]),
        True,
    ),
    ("a_combination_of_one_field", lambda d: model(d).update(combinations=[["bulk.density"]]), False),
    (
        "an_engine_value_with_its_basis",
        engine_value({"value": 1.0, "reason": "a reason", "basis": "a basis"}),
        True,
    ),
    ("an_engine_value_without_its_basis", engine_value({"value": 1.0, "reason": "a reason"}), False),
    (
        "an_implied_condition_with_a_basis",
        implied(
            "tissue_state", "in_vivo", {"temperature": {"value": 310.15, "unit": "K", "basis": "stated"}}
        ),
        True,
    ),
    (
        "an_implied_condition_naming_an_unregistered_condition",
        implied("tissue_state", "in_vivo", {"pressure": {"value": 1.0, "unit": "Pa"}}),
        False,
    ),
    (
        "a_waiver_naming_an_unregistered_condition",
        waiver({"code": "outside_range", "condition": "pressure"}),
        False,
    ),
    # A waiver whose code is `condition_unknown_name` is refused, whatever condition it names (maintainer,
    # 2026-10-24).
    (
        "a_waiver_of_an_unknown_conditions_name_naming_it",
        waiver({"code": "condition_unknown_name", "condition": "pressure"}),
        False,
    ),
    (
        "a_waiver_of_an_unknown_conditions_name_naming_a_registered_one",
        waiver({"code": "condition_unknown_name", "condition": "temperature"}),
        False,
    ),
    (
        "a_waiver_of_an_unstated_condition_naming_a_registered_one",
        waiver({"code": "condition_unstated", "condition": "temperature"}),
        True,
    ),
    ("a_target_species_by_its_taxon", target({"species": {"ncbi_taxon": 9606}}), True),
    ("a_target_species_with_a_fractional_taxon", target({"species": {"ncbi_taxon": 9606.5}}), False),
    ("a_target_species_as_a_status_object", target({"species": {"status": "unstated"}}), False),
    (
        "a_target_disease_state_by_its_token",
        target({"disease_and_treatment_state": {"token": "normal"}}),
        True,
    ),
    (
        "a_target_disease_state_holding_a_basis",
        target({"disease_and_treatment_state": {"token": "normal", "basis": "stated"}}),
        False,
    ),
    (
        "a_balanced_population_level",
        population_level({"level": "donor", "balanced_over": "lot"}),
        True,
    ),
    ("a_population_level_beside_another_represents", sampled("measurement", level=True), False),
    (
        "a_population_level_beside_no_represents",
        lambda declaration: requirement(declaration).update(
            population_level={"level": "donor", "within": {"status": "none"}}
        ),
        False,
    ),
    ("a_population_level_beside_population", sampled("population", level=True), True),
    (
        "a_balanced_population_level_with_a_slip",
        population_level({"level": "donor", "balanced_over": "lots"}),
        False,
    ),
    (
        "a_region_with_its_operating_conditions",
        region_conditions({"temperature": {"value": 310.15, "unit": "K"}}),
        True,
    ),
    (
        "a_region_with_an_unregistered_operating_condition",
        region_conditions({"pressure": {"value": 1.0, "unit": "Pa"}}),
        False,
    ),
]


@pytest.mark.parametrize(
    ("change", "valid"), [probe[1:] for probe in PROBES], ids=[probe[0] for probe in PROBES]
)
def test_each_rule_and_binding_judges_its_own_fault(change: Callable[[Json], None], valid: bool) -> None:
    declaration = a_declaration()
    assert agreed("declaration.json")(declaration)
    change(declaration)
    assert agreed("declaration.json")(declaration) is valid


def printed_example() -> Json:
    """The declaration printed at the head of section 1."""
    text = document("declarations.md")
    start = text.index("## 1. The declaration")
    block = text[start:].partition("```json\n")[2].partition("\n```")[0]
    return cast(Json, json.loads(block))


def test_section_1s_printed_example_is_taken_and_a_fault_in_it_is_not() -> None:
    """The text's own example is a declaration. The controls: it holds a waiver located at a region, the
    location rule's second arm, and the schema refuses it with a member one slip off a named one."""
    example = printed_example()
    assert agreed("declaration.json")(example)
    assert any("region" in found for found in cast(list[Json], model(example)["acceptances"]))
    model(example)["model_configuration_hsh"] = "a slip"
    assert not agreed("declaration.json")(example)


def valid_declarations() -> list[tuple[str, Json]]:
    """The declarations the closure check adds a member to: the build-check cases that expect no refusal, and
    each probe the schema takes, which reaches places those cases do not (a trainable entry, an engine)."""
    found = [(name, value) for name, value, pointers in CASES if not pointers and isinstance(value, dict)]
    for name, change, valid in PROBES:
        if valid:
            declaration = a_declaration()
            change(declaration)
            found.append((name, declaration))
    return found
