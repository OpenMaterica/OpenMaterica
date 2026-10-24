# SPDX-License-Identifier: Apache-2.0
"""`SHAPE`, the table of places `core/declarations.py` checks a declaration against, is the table of the
declaration's shape as `declarations.md` section 1 gives it, and `declaration.json`'s members, required lists
and token lists are `SHAPE`'s: so the code, the schema and the text hold one list (the S7 design's 6.4).

-  Each place of the table, its members and what the Required column makes of each (required, optional,
  exactly one of several, or present as a rule beside the table says), each kind of acceptance's members as
  the table's acceptance rows and section 4.1's row give them, and each object a Holds cell gives.
-  Each place's definitions in the schema: their members, their required members, and, where a place is
  several definitions (one per exclusive alternative), the members each requires alone; each token list
  `TOKENS` writes out, a distribution's parameters, and the codes that name a condition.

Each check returns its problems; each has controls that change `SHAPE`, the text or the schema and find one.
"""

import copy
import json
import re
from collections.abc import Callable
from typing import cast

import pytest

from materica.core import declarations
from materica.core.declarations import (
    CONDITION_CODES,
    DISTRIBUTION_PARAMETERS,
    KINDS,
    SHAPE,
    TOKENS,
    Holds,
    List,
    Member,
    Required,
)
from materica.core.jsonio import JsonValue
from materica.core.vocabulary import VOCABULARY
from scripts.gen_vocabulary import codes
from tests.spec_sync.schemas import SCHEMA
from tests.spec_sync.test_declaration_schema import (
    HELD_OBJECTS,
    document,
    expected_kind,
    holds,
    kind_rows,
    shape_rows,
)
from tests.verdicts import Json

Shape = dict[str, tuple[Member, ...]]
FILES: dict[str, Json] = {
    path.relative_to(SCHEMA).as_posix(): json.loads(path.read_text(encoding="utf-8"))
    for path in SCHEMA.rglob("*.json")
}


# `SHAPE` against the text.

# The table's places; and the places of `SHAPE` that hold the objects its Holds cells give.
TABLE_PLACES = (
    *("declaration", "model entry", "requirement", "requirement condition", "trainable entry"),
    "material reference",
)
HELD_PLACES = {
    **{"consumer": "consumer", "sampling": "sampling", "model": "model", "mixing": "mixing"},
    **{"chains": "chain", "engine": "engine"},
}


def required_of(cell: str) -> str:
    """What a Required cell makes of its members: `yes`, `no`, `one` (exactly one), or `rule` (where a rule
    beside the table holds)."""
    if cell.startswith("yes"):
        return "yes"
    if cell == "exactly one":
        return "one"
    return "no" if cell.startswith("no") else "rule"


def members(shape: Shape, place: str) -> dict[str, str]:
    return {member.name: member.required for member in shape[place]}


def text_problems(text: str, shape: Shape) -> list[str]:
    """Where `shape` differs from the table: a place's members and their Required cells; a list the table asks
    one entry or more of; each kind of acceptance's members and its required ones; each object a Holds cell
    gives."""
    rows, kinds = shape_rows(text), kind_rows(text)
    problems: list[str] = []
    for place in TABLE_PLACES:
        given: dict[str, str] = {}
        for row in (row for row in rows if row["Place"] == place):
            first, _, located = row["Member"].partition(" and one of ")
            given |= dict.fromkeys(codes(first), required_of(row["Required"]))
            given |= dict.fromkeys(codes(located), "one")
            asks = "at least one" in row["Required"] or "at least one" in row["Holds"]
            for listed in (entry for entry in shape[place] if entry.name in codes(first)):
                if isinstance(listed.holds, List) and (listed.holds.least >= 1) != asks:
                    problems.append(f"the {place}'s {listed.name} asks {listed.holds.least} entries or more")
        if members(shape, place) != given:
            problems.append(f"the {place} is {members(shape, place)}, the text {given}")
    for kind in KINDS:
        named, needed = expected_kind(rows, kind, kinds)
        found = members(shape, kind)
        if set(found) != named:
            problems.append(f"{kind} names {sorted(found)}, the text {sorted(named)}")
        found_needed = sorted(name for name, held in found.items() if held == "yes")
        if set(found_needed) != needed:
            problems.append(f"{kind} requires {found_needed}, the text {sorted(needed)}")
    for (place, name), _ in HELD_OBJECTS.items():
        cell = holds(rows, place, name)
        given_object = cast(re.Match[str], re.match(r"`\{([^}]*)\}`", cell))[1]
        required = set(re.findall(r'"([a-z_]+)"', given_object))
        optional = set(re.findall(r"optionally `([a-z_]+)`", cell))
        held = members(shape, HELD_PLACES[name])
        if (
            set(held) != required | optional
            or {member for member, h in held.items() if h == "yes"} != required
        ):
            problems.append(
                f"the {place}'s {name} holds {held}, the text {sorted(required)} and {sorted(optional)}"
            )
    return problems


def test_shape_is_the_texts_table() -> None:
    assert text_problems(document("declarations.md"), SHAPE) == []


def dropped(place: str, name: str) -> Shape:
    shape = dict(SHAPE)
    shape[place] = tuple(member for member in shape[place] if member.name != name)
    return shape


def requiring(place: str, name: str, required: Required) -> Shape:
    shape = dict(SHAPE)
    shape[place] = tuple(
        Member(member.name, required, member.holds) if member.name == name else member
        for member in shape[place]
    )
    return shape


def holding(place: str, name: str, holds: Holds) -> Shape:
    shape = dict(SHAPE)
    shape[place] = tuple(
        Member(member.name, member.required, holds) if member.name == name else member
        for member in shape[place]
    )
    return shape


@pytest.mark.parametrize(
    ("shape", "problem"),
    [
        (dropped("model entry", "chains"), "the model entry is"),
        (requiring("requirement", "label", "yes"), "the requirement is"),
        (requiring("declaration", "sampling", "no"), "the declaration is"),
        (requiring("requirement condition", "accept", "yes"), "the requirement condition is"),
        (requiring("trainable entry", "region", "no"), "the trainable entry is"),
        (dropped("waiver", "label"), "waiver names"),
        (requiring("extrapolation", "basis", "no"), "extrapolation requires"),
        (requiring("pick", "record", "rule"), "pick requires"),
        (dropped("engine", "region_values"), "the model entry's engine holds"),
        (requiring("consumer", "version", "no"), "the declaration's consumer holds"),
        (
            dict(SHAPE, waiver=(*SHAPE["waiver"], Member("basis", "no", declarations.Value("string")))),
            "waiver names",
        ),
        (
            holding("model entry", "reads", List(declarations.Value("string"))),
            "the model entry's reads asks",
        ),
    ],
)
def test_a_shape_that_drifts_from_the_text_is_found(shape: Shape, problem: str) -> None:
    assert any(found.startswith(problem) for found in text_problems(document("declarations.md"), shape))


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ("| | `consequence` | no |", "| | `consequence` | yes |", "the requirement condition is"),
        ("| | `chains` | yes, `[]` allowed |", "| | `chains` | no |", "the model entry is"),
        (
            "| | `reads` | yes, at least one |",
            "| | `reads` | yes, `[]` allowed |",
            "the model entry's reads asks",
        ),
        ("; no other kind holds it |", " |", "pick names"),
    ],
)
def test_a_text_that_drifts_from_the_shape_is_found(old: str, new: str, problem: str) -> None:
    text = document("declarations.md")
    assert text.count(old) == 1, old
    assert any(found.startswith(problem) for found in text_problems(text.replace(old, new), SHAPE))


# `SHAPE` against declaration.json.

# Each place's definitions, as (file, definition), the file's root for None: one per exclusive alternative.
DEFINITIONS: dict[str, tuple[tuple[str, str | None], ...]] = {
    "declaration": (("declaration.json", None),),
    "requirement condition": (
        ("declaration.json", "tolerance_condition"),
        ("declaration.json", "accept_condition"),
    ),
    "material reference": (("read_request.json", "material_ref"),),
    "operating condition": (
        ("read_request.json", "operating_value"),
        ("read_request.json", "operating_range"),
    ),
    "model": (("record.writer.json", "scope_model"),),
    "checked over": tuple(
        ("declaration.json", f"checked_over_{name}") for name in ("domain", "path", "records")
    ),
    "population level": (
        ("record.writer.json", "population_level"),
        ("declaration.json", "balanced_population_level"),
    ),
    "tolerance": (("read_request.json", "tolerance"),),
    "status object": (("record.writer.json", "status_object"),),
    **{
        place: (("declaration.json", place.replace(" ", "_")),)
        for place in (
            *("model entry", "requirement", "trainable entry", "consumer", "sampling", "independence entry"),
            *("mixing", "chain", "chain end", "engine", "crosswalk pin", "engine value"),
            *KINDS,
        )
    },
    **{f"fact {fact}": (("declaration.json", f"declared_{fact}"),) for fact in VOCABULARY.facts},
}


def definition(file: str, name: str | None, files: dict[str, Json] = FILES) -> Json:
    found = files[file]
    return found if name is None else cast(Json, cast(Json, found["$defs"])[name])


def resolve(reference: str, file: str, files: dict[str, Json]) -> tuple[Json, str]:
    """The node a `$ref` names from `file`, and the file it is in."""
    target, _, path = reference.partition("#")
    target = (target.rpartition("/")[0] + "/" if "/" in file else "") + target if target else file
    node: JsonValue = files[target]
    for step in (step for step in path.split("/") if step):
        node = cast(Json, node)[step]
    return cast(Json, node), target


# An object a definition is: the members it names, and those it requires.
Branch = tuple[set[str], set[str]]


def branches(node: Json, file: str, files: dict[str, Json]) -> list[Branch]:
    """The objects a definition is, one per alternative of its `oneOf`, each with the members its `$ref` and
    its own `properties` give and the `required` of both."""
    named, needed = (
        set(cast(Json, node.get("properties", {}))),
        set(cast(list[str], node.get("required", []))),
    )
    if "$ref" in node:
        target, in_file = resolve(cast(str, node["$ref"]), file, files)
        found = branches(target, in_file, files)
    elif "oneOf" in node:
        alternatives = cast(list[Json], node["oneOf"])
        found = [branch for alternative in alternatives for branch in branches(alternative, file, files)]
    else:
        return [(named, needed)]
    return [(branch_named | named, branch_needed | needed) for branch_named, branch_needed in found]


def place_branches(place: str, files: dict[str, Json]) -> list[Branch]:
    if place.startswith("difference "):
        # An accepted difference's value of a fact: the binding's alternative that is the fact's shape.
        fact = place.partition(" ")[2]
        binding = cast(list[Json], definition("declaration.json", "difference_value_binding", files)["allOf"])
        for rule in binding:
            if cast(Json, cast(Json, rule["if"])["properties"])["fact"] == {"const": fact}:
                value = cast(Json, cast(Json, cast(Json, rule["then"])["properties"])["value"])
                return branches(cast(list[Json], value["anyOf"])[2], "declaration.json", files)
        raise AssertionError(f"no binding for {fact}")
    if place in ("implied numeric", "implied token"):
        return branches(
            definition("declaration.json", place.replace(" ", "_"), files), "declaration.json", files
        )
    found: list[Branch] = []
    for file, name in DEFINITIONS[place]:
        found += branches(definition(file, name, files), file, files)
    return found


def schema_problems(shape: Shape, files: dict[str, Json] = FILES) -> list[str]:
    """Where a place's definitions differ from `SHAPE`: the members they name together, the members all of
    them require, and, for a place of several, the members each requires alone, which `SHAPE` marks `one`."""
    problems: list[str] = []
    for place, held in shape.items():
        found = place_branches(place, files)
        named = set[str]().union(*(branch_named for branch_named, _ in found))
        every = set[str].intersection(*(branch_needed for _, branch_needed in found))
        if named != {member.name for member in held}:
            problems.append(
                f"the {place} names {sorted(named)} in the schema, {sorted(m.name for m in held)} here"
            )
        if every != {member.name for member in held if member.required == "yes"}:
            problems.append(f"the {place} requires {sorted(every)} in the schema")
        alone = set[str]().union(*(branch_needed for _, branch_needed in found)) - every
        if len(found) > 1 and alone != {member.name for member in held if member.required == "one"}:
            problems.append(f"the {place}'s alternatives require {sorted(alone)} in the schema")
    return problems


def test_declaration_json_names_and_requires_shapes_members() -> None:
    assert schema_problems(SHAPE) == []


def changed(file: str, name: str, change: Callable[[Json], object]) -> dict[str, Json]:
    files = copy.deepcopy(FILES)
    change(definition(file, name, files))
    return files


@pytest.mark.parametrize(
    ("files", "problem"),
    [
        (
            changed("declaration.json", "waiver", lambda d: cast(Json, d["properties"]).pop("label")),
            "the waiver names",
        ),
        (
            changed(
                "declaration.json", "model_entry", lambda d: cast(list[str], d["required"]).remove("chains")
            ),
            "the model entry requires",
        ),
        (
            changed(
                "declaration.json",
                "accept_condition",
                lambda d: cast(list[str], d["required"]).remove("accept"),
            ),
            "the requirement condition's alternatives",
        ),
        (
            changed(
                "declaration.json",
                "pick",
                lambda d: cast(Json, d["properties"]).update(basis={"type": "string"}),
            ),
            "the pick names",
        ),
        (
            changed("declaration.json", "declared_species", lambda d: d.update(required=[])),
            "the fact species requires",
        ),
    ],
)
def test_a_schema_that_drifts_from_the_shape_is_found(files: dict[str, Json], problem: str) -> None:
    assert any(found.startswith(problem) for found in schema_problems(SHAPE, files))


def listed_tokens(node: Json) -> list[str]:
    return cast(list[str], node["enum"]) if "enum" in node else [cast(str, node["const"])]


def tokens_of(node: Json, file: str, files: dict[str, Json] = FILES) -> list[str]:
    """The tokens a member's schema takes: its `enum` or `const`, through a `$ref`, its items' or map's, less
    those its `not` refuses (a waiver's `code`)."""
    refused = listed_tokens(cast(Json, node["not"])) if isinstance(node.get("not"), dict) else []
    if "$ref" in node:
        target, in_file = resolve(cast(str, node["$ref"]), file, files)
        taken = tokens_of(target, in_file, files)
    elif isinstance(node.get("items"), dict) or isinstance(node.get("additionalProperties"), dict):
        key = "items" if isinstance(node.get("items"), dict) else "additionalProperties"
        taken = tokens_of(cast(Json, node[key]), file, files)
    else:
        taken = listed_tokens(node)
    return [token for token in taken if token not in refused]


TOKEN_DEFINITIONS = {
    "requirement": ("declaration.json", "requirement"),
    "population level": ("declaration.json", "balanced_population_level"),
    "model entry": ("declaration.json", "model_entry"),
    "mixing": ("declaration.json", "mixing"),
    "status object": ("record.writer.json", "status_object"),
    **{kind: ("declaration.json", kind) for kind in KINDS},
}


def token_problems(
    tokens: dict[tuple[str, str], tuple[str, ...]], files: dict[str, Json] = FILES
) -> list[str]:
    """Where a token list `TOKENS` writes out, a distribution's parameters or the codes that name a condition
    differ from the schema's."""
    problems: list[str] = []
    for (place, member), allowed in tokens.items():
        file, name = TOKEN_DEFINITIONS[place]
        node = cast(Json, cast(Json, definition(file, name, files)["properties"])[member])
        if sorted(tokens_of(node, file, files)) != sorted(allowed):
            problems.append(f"the {place}'s {member} takes {tokens_of(node, file, files)} in the schema")
    for rule in cast(
        list[Json], definition("declaration.json", "distribution_parameters_binding", files)["allOf"]
    ):
        token = cast(Json, cast(Json, cast(Json, rule["if"])["properties"])["distribution"])["const"]
        given = cast(Json, cast(Json, cast(Json, rule["then"])["properties"])["distribution_parameters"])[
            "required"
        ]
        if DISTRIBUTION_PARAMETERS[cast(str, token)] != tuple(cast(list[str], given)):
            problems.append(f"{token}'s parameters are {given} in the schema")
    naming = cast(
        Json, cast(Json, definition("declaration.json", "waiver_condition_rule", files)["if"])["properties"]
    )
    if sorted(tokens_of(cast(Json, naming["code"]), "declaration.json", files)) != sorted(CONDITION_CODES):
        problems.append("the codes that name a condition differ in the schema")
    return problems


def test_declaration_json_takes_shapes_tokens() -> None:
    assert token_problems(TOKENS) == []


def test_a_token_list_that_drifts_is_found() -> None:
    assert token_problems(TOKENS | {("distribution", "space"): ("identity",)}) == [
        "the distribution's space takes ['identity', 'log'] in the schema"
    ]
    # A waiver's code: the schema's `not` beside the reasons it takes from the vocabulary.
    codes_taken = changed(
        "declaration.json", "waiver", lambda d: cast(Json, cast(Json, d["properties"])["code"]).pop("not")
    )
    assert [problem.partition(" takes ")[0] for problem in token_problems(TOKENS, codes_taken)] == [
        "the waiver's code"
    ]
    files = changed(
        "declaration.json",
        "waiver_condition_rule",
        lambda d: d.update({"if": {"properties": {"code": {"enum": ["at_edge"]}}}}),
    )
    assert token_problems(TOKENS, files) == ["the codes that name a condition differ in the schema"]
