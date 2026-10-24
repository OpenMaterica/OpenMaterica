# SPDX-License-Identifier: Apache-2.0
"""`SHAPE`, the table of places `core/declarations.py` checks a declaration against, is the table of the
declaration's shape as `declarations.md` section 1 gives it, and `declaration.json`'s members, required lists
and token lists are `SHAPE`'s: so the code, the schema and the text hold one list (the S7 design's 6.4).

-  Each place of the table, its members and what the Required column makes of each (required, optional,
  exactly one of several, or present as a rule beside the table says), each kind of acceptance's members as
  the table's acceptance rows and section 4.1's row give them, and each object a Holds cell gives.
-  What each member holds: the JSON type its Holds cell's phrase gives (`HELD`); each constraint a cell or
  item 8 states (`CONSTRAINED`); the members the own members' cell names by a kind's possessive; and the
  clauses of 2026-10-24 the table states, `basis` on three kinds alone and `population_level` only beside
  `population`, the latter against what the check refuses.
-  Each place's definitions in the schema: their members, their required members, and, where a place is
  several definitions (one per exclusive alternative), the members each requires alone; each token list
  `TOKENS` writes out, a distribution's parameters, and the codes that name a condition.

Not held here: the own members' cell's types, and its constraints but a pick's `index` and an
extrapolation's `law`; the facts' shapes, which `provenance.md` section 6.2 gives (`_FACTS`); and the rules
on a name given twice, read or checked over, which no Holds phrase states: the unit examples and the
build-check files hold those.

Each check returns its problems; each has controls that change `SHAPE`, the text or the schema and find one.
"""

import copy
import json
import re
from collections.abc import Callable
from pathlib import Path
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
from scripts.gen_vocabulary import codes, prose, without_asides
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


# What each member holds, against its row's Holds cell: the JSON type its phrase gives, and each constraint a
# cell or an item states.

OWN = "its kind's own members"
# A Holds cell's phrase, at its start, and the JSON type it gives; a member whose Required cell allows `[]`
# holds a list of it.
HELD: tuple[tuple[str, str], ...] = (
    (r"lists of two or more fields", "list of list of string"),
    (r"model entries|requirements,|acceptances |entries `\{", "list of object"),
    (r"registered fields|strings|at least one token", "list of string"),
    (r"region to operating conditions", "map of map of object"),
    (r"registered condition to |a fact of .* to its shape", "map of object"),
    (r"parameter-set field to ", "map of string"),
    (r"`\{|exactly one of `\{|the object |a material reference", "object"),
    (r"a number", "number"),
    (
        r"a string|a registered field|a field in |a token of |a label |a kind of |a region's name"
        r"|`[a-z0-9]+`( or `[a-z0-9]+`)?( |$)",
        "string",
    ),
    (r"an interval", "any"),
)


def text_kind(cell: str, required: str) -> str | None:
    kind = next((kind for pattern, kind in HELD if re.match(pattern, cell)), None)
    if kind is not None and "`[]` allowed" in required and not kind.startswith("list"):
        return f"list of {kind}"
    return kind


def shape_kind(held: Holds) -> str:
    if isinstance(held, declarations.Value):
        return held.type
    if isinstance(held, declarations.Object):
        return "object"
    if isinstance(held, List):
        return f"list of {shape_kind(held.items)}"
    values = held.values if isinstance(held.values, dict) else {"": held.values}
    kinds = sorted({shape_kind(value) for value in values.values()})
    return f"map of {' or '.join(kinds)}"


def held_by(shape: Shape, place: str, name: str) -> Holds | None:
    return next((member.holds for member in shape[place] if member.name == name), None)


def type_problems(text: str, shape: Shape) -> list[str]:
    """Where a member of a place of the table holds another JSON type in `shape` than its row's Holds cell
    gives (`HELD`): each part of a cell, split at its semicolons, for each member its row names in turn, or
    the whole cell for each; an acceptance's member at each kind naming it. Not the own members of an
    acceptance's kind, nor a trainable entry's location, whose cells give no type of theirs."""
    problems: list[str] = []
    for row in shape_rows(text):
        if row["Member"] == OWN:
            continue
        names = codes(row["Member"].partition(" and one of ")[0])
        parts = row["Holds"].split("; ")
        if len(parts) != len(names):
            # A cell of one plural noun for several members gives each one of it.
            parts = [re.sub(r"^strings\b", "a string", row["Holds"])] * len(names)
        for name, part in zip(names, parts, strict=True):
            expected = text_kind(part, row["Required"])
            if row["Place"] == "acceptance":
                places = [kind for kind in KINDS if name in members(shape, kind)]
            else:
                places = [row["Place"]]
            for place in places:
                held = held_by(shape, place, name)
                found = None if held is None else shape_kind(held)
                if found != expected:
                    problems.append(f"the {place}'s {name} holds {found}, the text {expected}")
    return problems


# Each constraint the text states: the row whose Holds cell states it (its place and member, OWN for an
# acceptance's own members) or None for an item's sentence; its phrase; and the member of `SHAPE` it holds, at
# each kind naming it for "acceptance", with the constraint that must be its (`TEXT`: a `reason`'s or a
# `basis`'s string of at least one character, which `_reasons` judges; `NEVER_STATUS`: each fact of a map,
# never a status object).
TEXT, NEVER_STATUS = vars(declarations)["_TEXT"], "never a status object"
CONSTRAINED: tuple[tuple[tuple[str, str] | None, str, str, str, object], ...] = (
    (
        ("declaration", "operating_conditions"),
        "`lo` not above `hi`",
        "operating condition",
        "range",
        "_range",
    ),
    (
        ("model entry", "mixing"),
        "a number not below zero",
        "mixing",
        "fraction_sum_tolerance",
        "_not_below_zero",
    ),
    (("model entry", "target"), "never a status object", "model entry", "target", NEVER_STATUS),
    (("requirement condition", "tolerance"), "not below zero", "tolerance", "value", "_not_below_zero"),
    (("requirement condition", "reason"), "at least one character", "requirement condition", "reason", TEXT),
    (("acceptance", "reason"), "at least one character", "acceptance", "reason", TEXT),
    (("acceptance", "basis"), "at least one character", "acceptance", "basis", TEXT),
    (
        ("acceptance", OWN),
        "a pick's `index`, a whole number not below zero",
        "pick",
        "index",
        "_whole_not_below_zero",
    ),
    (
        ("acceptance", OWN),
        "its `law`, a string of at least one character",
        "extrapolation",
        "law",
        "_one_character",
    ),
    (
        None,
        "`sampling.min_acceptance` is a number in (0, 1]",
        "sampling",
        "min_acceptance",
        "_in_unit_interval",
    ),
)


def constrained(held: Holds | None, constraint: object) -> bool:
    if constraint is TEXT:
        return held is TEXT
    if constraint == NEVER_STATUS:
        values = held.values if isinstance(held, declarations.Map) and isinstance(held.values, dict) else {}
        return bool(values) and all(
            isinstance(value, declarations.Object) and value.never_status for value in values.values()
        )
    function = vars(declarations)[cast(str, constraint)]
    return isinstance(held, declarations.Value | List) and held.constraint is function


def constraint_problems(text: str, shape: Shape) -> list[str]:
    """Where a constraint the text states (`CONSTRAINED`) is not in its cell or sentence, or not on its
    member in `shape`."""
    rows, problems = shape_rows(text), list[str]()
    for where, phrase, place, name, constraint in CONSTRAINED:
        said = prose(text) if where is None else holds(rows, *where)
        if phrase not in said:
            problems.append(f"{where or 'the text'} does not say {phrase!r}")
        places = (
            [kind for kind in KINDS if name in members(shape, kind)] if place == "acceptance" else [place]
        )
        problems += [
            f"the {at}'s {name} is not held to {phrase!r}"
            for at in places
            if not constrained(held_by(shape, at, name), constraint)
        ]
    return problems


# The clauses of 2026-10-24 that the table states: `basis` on three kinds alone, and `population_level` only
# beside the `represents` it names.

VALID: Json = json.loads(
    (
        Path(declarations.__file__).parents[1]
        / "data/conformance/build_checks/inputs"
        / "bc016_waiver_at_one_of_two_records.json"
    ).read_bytes()
)


def the_check_refuses_a_level(represents: str | None) -> bool:
    """Whether the declaration's check refuses a `population_level` beside `represents` (None: beside none),
    BC-043 at that member."""
    declaration = copy.deepcopy(VALID)
    requirement = cast(list[Json], cast(list[Json], declaration["models"])[0]["requirements"])[0]
    requirement["population_level"] = {"level": "donor", "within": {"status": "none"}}
    if represents is not None:
        requirement["represents"] = represents
        declaration["sampling"] = {"min_acceptance": 0.5, "reason": "a reason", "independence": []}
    checked = declarations.Declaration.from_json(declaration)
    at = "/models/0/requirements/0/population_level"
    return isinstance(checked, tuple) and ("BC-043", at) in {
        (refusal.item, refusal.pointer) for refusal in checked
    }


def clause_problems(text: str, shape: Shape, refuses_a_level: Callable[[str | None], bool]) -> list[str]:
    """Where the kinds the `basis` row lists, which "no other kind holds", are not those `shape` names `basis`
    on and requires it of; and where the `population_level` row's "where `represents` is `<token>`, and only
    there" differs from what `refuses_a_level` gives beside each `represents` and beside none."""
    rows, problems = shape_rows(text), list[str]()
    basis = next(row for row in rows if row["Place"] == "acceptance" and row["Member"] == "`basis`")
    listed = set(codes(basis["Required"].partition(" (item 4)")[0]))
    named = {kind for kind in KINDS if "basis" in members(shape, kind)}
    needed = {kind for kind in KINDS if members(shape, kind).get("basis") == "yes"}
    if needed != listed or ("no other kind holds it" in basis["Required"] and named != listed):
        problems.append(
            f"basis is named on {sorted(named)} and required of {sorted(needed)}, the text {sorted(listed)}"
        )
    level = next(row for row in rows if row["Member"] == "`population_level`")
    stated = re.match(r"where `represents` is `([a-z_]+)`(, and only there)?", level["Required"])
    token, only = (stated[1], stated[2] is not None) if stated else ("", False)
    for represents in (*VOCABULARY.token_lists["represents"], None):
        if refuses_a_level(represents) != (only and represents != token):
            problems.append(
                f"a population_level beside {represents or 'no represents'}: the text and the check differ"
            )
    return problems


# The members the own members' cell names a kind's by its possessive ("a pick's `index`", "its `law`").
POSSESSIVE = re.compile(r"\ban? ([`a-z_ ]+?)'s (?:and an? ([`a-z_ ]+?)'s )?`([a-z_]+)`|\bits `([a-z_]+)`")


def own_member_problems(text: str, shape: Shape) -> list[str]:
    """Where the own members' cell names, by a kind's possessive or `its`, a member that kind does not hold in
    `shape`."""
    cell = without_asides(holds(shape_rows(text), "acceptance", OWN))
    problems: list[str] = []
    for clause in cell.split("; "):
        kinds: list[str] = []
        for found in POSSESSIVE.finditer(clause):
            if found[3]:
                kinds = [kind.strip("`").replace(" ", "_") for kind in (found[1], found[2]) if kind]
            name = found[3] or found[4]
            problems += [
                f"the own members' cell names {kind}'s {name}"
                for kind in kinds
                if kind not in KINDS or name not in members(shape, kind)
            ]
    return problems


def test_each_member_holds_what_its_row_gives() -> None:
    text = document("declarations.md")
    assert type_problems(text, SHAPE) == []
    assert constraint_problems(text, SHAPE) == []
    assert clause_problems(text, SHAPE, the_check_refuses_a_level) == []
    assert own_member_problems(text, SHAPE) == []


FACTS_AS_STATUS = declarations.Map({name: declarations.Object(f"fact {name}") for name in VOCABULARY.facts})


@pytest.mark.parametrize(
    ("shape", "problem"),
    [
        (
            holding("model entry", "model_configuration_hash", declarations.Value("number")),
            "the model entry's model_configuration_hash holds number",
        ),
        (
            holding("model entry", "reads", List(declarations.Value("number"), least=1)),
            "the model entry's reads holds list of number",
        ),
        (holding("tolerance", "value", declarations.Value("number")), "the tolerance's value is not held"),
        (
            holding("sampling", "min_acceptance", declarations.Value("number")),
            "the sampling's min_acceptance is not held",
        ),
        (holding("pick", "index", declarations.Value("number")), "the pick's index is not held"),
        (
            holding("extrapolation", "law", declarations.Value("string")),
            "the extrapolation's law is not held",
        ),
        (holding("model entry", "target", FACTS_AS_STATUS), "the model entry's target is not held"),
        (holding("waiver", "reason", declarations.Value("string")), "the waiver's reason is not held"),
        (dropped("distribution", "basis"), "basis is named on"),
        (dropped("waiver", "code"), "the own members' cell names waiver's code"),
    ],
)
def test_a_held_type_or_constraint_that_drifts_from_the_text_is_found(shape: Shape, problem: str) -> None:
    text = document("declarations.md")
    found = [
        *type_problems(text, shape),
        *constraint_problems(text, shape),
        *clause_problems(text, shape, the_check_refuses_a_level),
        *own_member_problems(text, shape),
    ]
    assert any(problem in line for line in found), found


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        (
            "| | `model_configuration_hash` | yes | a string |",
            "| | `model_configuration_hash` | yes | a number |",
            "holds string, the text number",
        ),
        (
            "| registered fields, none twice |",
            "| names, none twice |",
            "reads holds list of string, the text None",
        ),
        (
            '`{"value", "unit"}`, not below zero, in the condition\'s unit',
            '`{"value", "unit"}`, in the condition\'s unit',
            "does not say 'not below zero'",
        ),
        (
            "a pick's `index`, a whole number not below zero",
            "a pick's `index`, a whole number",
            "does not say \"a pick's `index`",
        ),
        (
            "where `represents` is `population`, and only there (the members table)",
            "where `represents` is `population` (the members table)",
            "a population_level beside measurement",
        ),
        (
            "| for `extrapolation`, `nominal` and `distribution` (item 4)",
            "| for `extrapolation` and `nominal` (item 4)",
            "basis is named on",
        ),
        (
            "a waiver's `code`, a reason",
            "a waiver's `codes`, a reason",
            "the own members' cell names waiver's codes",
        ),
    ],
)
def test_a_held_type_or_constraint_the_text_drifts_from_is_found(old: str, new: str, problem: str) -> None:
    text = document("declarations.md")
    assert text.count(old) == 1, old
    text = text.replace(old, new)
    found = [
        *type_problems(text, SHAPE),
        *constraint_problems(text, SHAPE),
        *clause_problems(text, SHAPE, the_check_refuses_a_level),
        *own_member_problems(text, SHAPE),
    ]
    assert any(problem in line for line in found), found


def test_a_check_that_takes_a_level_beside_another_represents_is_found() -> None:
    def beside_none_alone(represents: str | None) -> bool:
        return represents is None

    found = clause_problems(document("declarations.md"), SHAPE, beside_none_alone)
    assert found
    assert all(line.startswith("a population_level beside") for line in found)


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
