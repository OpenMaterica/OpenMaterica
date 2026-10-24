# SPDX-License-Identifier: Apache-2.0
"""The reference model's tables, written from the specification's text, against the vocabulary the generator
writes from the same text (`schema/0.1/vocabulary/`), so that a drift of either fails here; and so the build
model's own token lists, those of its shape table that the vocabulary holds. The vocabulary is
read as a file, not through `materica`; the control drifts a copy of it one table at a time."""

import copy
import posixpath
from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.reference import build_model, read_model
from tests.reference.read_model import StatusUnit
from tests.reference.strict_json import JsonObject, JsonValue, parse

VOCABULARY = Path(__file__).resolve().parents[2] / "src" / "materica" / "schema" / "0.1" / "vocabulary"
Vocabulary = Mapping[str, JsonObject]


def vocabulary() -> dict[str, JsonObject]:
    loaded: dict[str, JsonObject] = {}
    for path in sorted(VOCABULARY.glob("*.json")):
        document = parse(path.read_bytes())
        assert isinstance(document, dict), path.name
        loaded[path.stem] = document
    return loaded


def tokens(vocabulary: Vocabulary, file: str, name: str) -> JsonValue:
    definitions = vocabulary[file]["$defs"]
    assert isinstance(definitions, dict)
    definition = definitions[name]
    assert isinstance(definition, dict)
    return definition["enum"]


def model_fields() -> JsonObject:
    fields: JsonObject = {}
    for name, row in read_model.FIELDS.items():
        unit: JsonValue = {"status": row.unit.status} if isinstance(row.unit, StatusUnit) else row.unit
        entry: JsonObject = {"unit": unit, "forms": list(row.forms), "requires": list(row.requires)}
        if row.bases:
            entry["bases"] = {"composition": list(row.bases)}
        if row.label is not None:
            entry["label"] = row.label
        if row.label_not_on_axis is not None:
            entry["label_not_on_axis"] = row.label_not_on_axis
        fields[name] = entry
    return fields


def model_conditions() -> JsonObject:
    conditions: JsonObject = {}
    for name, row in read_model.CONDITIONS.items():
        entry: JsonObject = {"shape": row.shape}
        if row.shape == "numeric":
            entry["unit"] = row.unit
        else:
            entry["tokens"] = list(row.tokens)
        entry["required_with"] = {other: list(given) for other, given in row.required_with}
        conditions[name] = entry
    return conditions


def model_facts() -> JsonObject:
    facts: JsonObject = {}
    for name, row in read_model.FACTS.items():
        entry: JsonObject = {"tokens": list(row.tokens)}
        if row.unit is not None:
            entry["unit"] = row.unit
        if row.basis is not None:
            entry["basis"] = row.basis
        facts[name] = entry
    return facts


def model_reasons() -> JsonObject:
    reasons: JsonObject = {}
    for code, row in read_model.REASONS.items():
        entry: JsonObject = {"status": row.status}
        if row.steps:
            entry["steps"] = [float(step) for step in row.steps]
        else:
            entry["procedures"] = list(row.procedures)
        reasons[code] = entry
    return reasons


# Each of the model's token lists, and where the vocabulary holds the same list.
TOKEN_LISTS: dict[str, tuple[tuple[str, ...], str, str]] = {
    "FORMS": (read_model.FORMS, "forms", "form"),
    "TABLE_SCHEMES": (read_model.TABLE_SCHEMES, "forms", "table_scheme"),
    "AXES": (read_model.AXES, "conditions", "axis"),
    "INTERVAL_BASES": (read_model.INTERVAL_BASES, "forms", "interval_basis"),
    "COMPOSITION_BASES": (read_model.COMPOSITION_BASES, "forms", "composition_basis"),
    "SUM_RULES": (read_model.SUM_RULES, "forms", "sum_rule"),
    "COMPONENTS": (tuple(f"element:{symbol}" for symbol in read_model.ELEMENTS), "forms", "component"),
    "CENTRALS": (read_model.CENTRALS, "statistics", "central"),
    "BLOCK_DISTRIBUTIONS": (read_model.BLOCK_DISTRIBUTIONS, "statistics", "statistics_distribution"),
    "BLOCK_BASES": (read_model.BLOCK_BASES, "statistics", "statistics_basis"),
    "REPRESENTS": (read_model.REPRESENTS, "statistics", "represents"),
    "LEVELS": (read_model.LEVELS, "statistics", "level"),
    "PRECISION_CONDITIONS": (read_model.PRECISION_CONDITIONS, "statistics", "precision_conditions"),
    "DISPERSIONS": (read_model.DISPERSIONS, "statistics", "dispersion"),
    "UNCERTAINTY_DISTRIBUTIONS": (
        read_model.UNCERTAINTY_DISTRIBUTIONS,
        "statistics",
        "uncertainty_distribution",
    ),
    "UNCERTAINTY_BASES": (read_model.UNCERTAINTY_BASES, "statistics", "uncertainty_basis"),
    "UNCERTAINTY_REPRESENTS": (read_model.UNCERTAINTY_REPRESENTS, "statistics", "uncertainty_represents"),
    "DISTRIBUTIONS": (read_model.DISTRIBUTIONS, "statistics", "distribution"),
    "ORIGINS": (read_model.ORIGINS, "provenance", "origin"),
    "REVIEW_RESULTS": (read_model.REVIEW_RESULTS, "provenance", "review_result"),
    "CONDITION_BASES": (read_model.CONDITION_BASES, "provenance", "basis"),
    "STATED_AS": (read_model.STATED_AS, "provenance", "stated_as"),
    "SET_OR_MEASURED": (read_model.SET_OR_MEASURED, "provenance", "set_or_measured"),
    "RESULT_LABELS": (read_model.RESULT_LABELS, "labels", "result_label"),
    "FIELD_LABELS": (tuple(read_model.FIELD_LABELS), "fields", "label"),
}


def drift(vocabulary: Vocabulary) -> list[str]:
    """Each table of the model that differs from the vocabulary's."""
    found = [
        f"{table}: the model has {model!r}, the vocabulary {given!r}"
        for table, model, given in [
            ("FIELDS", model_fields(), vocabulary["fields"]["fields"]),
            ("CONDITIONS", model_conditions(), vocabulary["conditions"]["conditions"]),
            ("FACTS", model_facts(), vocabulary["specimen_facts"]["facts"]),
            ("REASONS", model_reasons(), vocabulary["reasons"]["reasons"]),
            ("ACCEPTANCE_KINDS", list(read_model.ACCEPTANCE_KINDS), vocabulary["acceptances"]["kinds"]),
        ]
        if model != given
    ]
    found.extend(
        f"{table}: the model has {list(model)!r}, the vocabulary {tokens(vocabulary, file, name)!r}"
        for table, (model, file, name) in TOKEN_LISTS.items()
        if list(model) != tokens(vocabulary, file, name)
    )
    return found


def test_the_model_s_tables_are_the_vocabulary_s() -> None:
    assert drift(vocabulary()) == []


def drifted(path: tuple[str, ...], value: JsonValue) -> dict[str, JsonObject]:
    changed = copy.deepcopy(vocabulary())
    host: JsonValue = changed[path[0]]
    for step in path[1:-1]:
        assert isinstance(host, dict)
        host = host[step]
    assert isinstance(host, dict)
    host[path[-1]] = value
    return changed


@pytest.mark.parametrize(
    ("path", "value", "table"),
    [
        (("fields", "fields", "bulk.density", "unit"), "g/cm3", "FIELDS"),
        (("fields", "fields", "fluid.dynamic_viscosity", "label_not_on_axis"), "temperature", "FIELDS"),
        (("conditions", "conditions", "measurement_dimension", "required_with"), {}, "CONDITIONS"),
        (("specimen_facts", "facts", "mimics", "basis"), "inferred", "FACTS"),
        (("reasons", "reasons", "no_pick", "status"), "not_met", "REASONS"),
        (("acceptances", "kinds"), ["pick"], "ACCEPTANCE_KINDS"),
        (("statistics", "$defs", "represents", "enum"), ["population"], "REPRESENTS"),
        (("forms", "$defs", "component", "enum"), ["element:H"], "COMPONENTS"),
        (("forms", "$defs", "table_scheme", "enum"), ["linear"], "TABLE_SCHEMES"),
        (("labels", "$defs", "result_label", "enum"), [], "RESULT_LABELS"),
    ],
)
def test_a_drift_of_a_table_fails(path: tuple[str, ...], value: JsonValue, table: str) -> None:
    found = drift(drifted(path, value))
    assert [entry.partition(":")[0] for entry in found] == [table]


def build_drift(vocabulary: Vocabulary) -> list[str]:
    """Each token list of the build model's shape table that differs from the vocabulary's: the acceptance
    kinds, a requirement's `review`, a distribution's tokens, the facts an implied condition may name, and the
    reason codes that name a condition. Its registered names (fields, conditions, facts, reasons, labels,
    `represents` and levels) are the read model's tables, held above."""
    reasons = vocabulary["reasons"]["reasons"]
    facts = vocabulary["specimen_facts"]["facts"]
    assert isinstance(reasons, dict)
    assert isinstance(facts, dict)
    condition_codes = [code for code in reasons if code.startswith("condition_")]
    pairs: list[tuple[str, JsonValue, JsonValue]] = [
        ("KINDS", list(build_model.KINDS), vocabulary["acceptances"]["kinds"]),
        ("REVIEWS", list(build_model.REVIEWS), tokens(vocabulary, "provenance", "review_result")),
        (
            "DISTRIBUTION_PARAMETERS",
            list(build_model.DISTRIBUTION_PARAMETERS),
            tokens(vocabulary, "statistics", "distribution"),
        ),
        (
            "TOKEN_FACTS",
            list(build_model.TOKEN_FACTS),
            [name for name, row in facts.items() if isinstance(row, dict) and row.get("tokens")],
        ),
        (
            "CODES_NAMING_A_CONDITION",
            list(build_model.CODES_NAMING_A_CONDITION),
            [
                *condition_codes,
                *(code for code in ("outside_range", "at_edge", "range_unstated") if code in reasons),
            ],
        ),
    ]
    return [
        f"{table}: the model has {model!r}, the vocabulary {given!r}"
        for table, model, given in pairs
        if model != given
    ]


def test_the_build_model_s_token_lists_are_the_vocabulary_s() -> None:
    assert build_drift(vocabulary()) == []


@pytest.mark.parametrize(
    ("path", "value", "table"),
    [
        (("acceptances", "kinds"), ["pick", "waiver"], "KINDS"),
        (("provenance", "$defs", "review_result", "enum"), ["reviewed", "checked"], "REVIEWS"),
        (("statistics", "$defs", "distribution", "enum"), ["normal"], "DISTRIBUTION_PARAMETERS"),
        (("specimen_facts", "facts", "lot", "tokens"), ["one"], "TOKEN_FACTS"),
        (("reasons", "reasons", "at_edge"), None, "CODES_NAMING_A_CONDITION"),
    ],
)
def test_a_drift_of_a_build_token_list_fails(path: tuple[str, ...], value: JsonValue, table: str) -> None:
    changed = drifted(path, value)
    if value is None:
        host = changed[path[0]][path[1]]
        assert isinstance(host, dict)
        del host[path[2]]
    found = build_drift(changed)
    assert [entry.partition(":")[0] for entry in found] == [table]


# The build model's shape table (`build_model.SHAPES` and the places of the acceptance kinds), against the
# declaration's JSON Schema, which is data written from the specification's table of the declaration's shape
# (`src/materica/schema/0.1/declaration.json`, read as a file, not through `materica`): per place, the
# members it names, the ones it requires and their JSON types; and the token lists the table adds. A place
# the schema states as a `oneOf` (`checked_over`, a requirement condition, an operating condition, a
# population level) is the union of its alternatives' members, required where every alternative requires.
SCHEMA = Path(__file__).resolve().parents[2] / "src" / "materica" / "schema" / "0.1"
DECLARATION = "declaration.json#/$defs/"
READ = "read_request.json#/$defs/"
WRITE = "record.writer.json#/$defs/"
PLACES: dict[str, tuple[str, ...]] = {
    "declaration": ("declaration.json#",),
    "name and version": (DECLARATION + "consumer", WRITE + "scope_model"),
    "sampling": (DECLARATION + "sampling",),
    "independence entry": (DECLARATION + "independence_entry",),
    "model entry": (DECLARATION + "model_entry",),
    "checked_over": tuple(DECLARATION + f"checked_over_{name}" for name in ("domain", "path", "records")),
    "operating condition": (READ + "operating_value", READ + "operating_range"),
    "requirement": (DECLARATION + "requirement",),
    "requirement condition": (DECLARATION + "tolerance_condition", DECLARATION + "accept_condition"),
    "tolerance": (READ + "tolerance",),
    "population_level": (WRITE + "population_level", DECLARATION + "balanced_population_level"),
    "status object": (WRITE + "status_object",),
    "mixing": (DECLARATION + "mixing",),
    "chain": (DECLARATION + "chain",),
    "chain end": (DECLARATION + "chain_end",),
    "located field": (DECLARATION + "trainable_entry",),
    "engine": (DECLARATION + "engine",),
    "crosswalk pin": (DECLARATION + "crosswalk_pin",),
    "reference": (READ + "material_ref",),
    **{kind: (DECLARATION + kind,) for kind in build_model.KINDS},
}
# What the schema names that the model does not, with why: the schema was written from the specification's
# table before the maintainer's ruling of 2026-10-24 that no kind but an extrapolation, a nominal and a
# distribution holds a `basis` (OPEN_POINTS: basis_on_other_kinds), whose words land with the next piece.
SCHEMA_ONLY: dict[str, frozenset[str]] = {
    kind: frozenset({"basis"}) for kind in build_model.KINDS if kind not in build_model.NEEDS_BASIS
}
JSON_TYPES: dict[type, str] = {str: "string", float: "number", list: "array", dict: "object"}
ALSO_ALLOWED: dict[str, str] = {"string": "string", "number": "integer", "array": "array", "object": "object"}
Schema = dict[str, JsonObject]


def schema() -> Schema:
    paths = [SCHEMA / name for name in ("declaration.json", "read_request.json", "record.writer.json")]
    paths.extend(sorted((SCHEMA / "vocabulary").glob("*.json")))
    files: Schema = {}
    for path in paths:
        document = parse(path.read_bytes())
        assert isinstance(document, dict), path.name
        files[path.relative_to(SCHEMA).as_posix()] = document
    return files


def resolve(files: Schema, ref: str, here: str) -> tuple[JsonObject, str]:
    """The schema node `ref` names, and the file it is in: a file and a JSON pointer, either alone."""
    name, _, pointer = ref.partition("#")
    file = posixpath.normpath(posixpath.join(posixpath.dirname(here), name)) if name else here
    node: JsonValue = files[file]
    for step in [part for part in pointer.split("/") if part]:
        assert isinstance(node, dict), ref
        node = node[step.replace("~1", "/").replace("~0", "~")]
    assert isinstance(node, dict), ref
    return node, file


def json_type(files: Schema, node: JsonObject, here: str) -> str | None:
    """The JSON type a node states, following its references, or None where it states none (a `oneOf`)."""
    while True:
        stated = node.get("type")
        if isinstance(stated, str):
            return stated
        enum = node.get("enum")
        constant = enum[0] if isinstance(enum, list) and enum else node.get("const")
        if isinstance(constant, str):
            return "string"
        ref = node.get("$ref")
        if not isinstance(ref, str):
            return None
        node, here = resolve(files, ref, here)


def schema_place(files: Schema, refs: tuple[str, ...]) -> tuple[dict[str, str | None], frozenset[str]]:
    """The members the schema names at a place with their JSON types, and those every alternative requires."""
    members: dict[str, str | None] = {}
    required: frozenset[str] | None = None
    for ref in refs:
        node, here = resolve(files, ref, "declaration.json")
        properties = node.get("properties", {})
        assert isinstance(properties, dict), ref
        for name, held in properties.items():
            assert isinstance(held, dict), ref
            members[name] = json_type(files, held, here)
        every = node.get("required", [])
        assert isinstance(every, list), ref
        needed = frozenset(str(name) for name in every)
        required = needed if required is None else required & needed
    return members, required or frozenset()


def model_place(name: str) -> build_model.Place:
    if name in build_model.KINDS:
        return build_model.acceptance_place(name)
    return {"reference": build_model.REFERENCE, **build_model.SHAPES}[name]


def asked_of(place: build_model.Place) -> frozenset[str]:
    """The members a place requires: those it marks required, and its one location member where it has one."""
    located = [member for member, (_, how) in place.items() if how == "located"]
    return frozenset(
        [member for member, (_, how) in place.items() if how == "yes"]
        + (located if len(located) == 1 else [])
    )


def shape_drift(files: Schema) -> list[str]:
    """Each place at which the build model's shape table differs from the schema's."""
    found: list[str] = []
    for name in PLACES:
        place = model_place(name)
        members, required = schema_place(files, PLACES[name])
        schema_only = SCHEMA_ONLY.get(name, frozenset())
        only_schema, only_model = frozenset(members) - set(place) - schema_only, set(place) - set(members)
        if only_schema or only_model or not schema_only <= members.keys():
            found.append(
                f"{name}: members: the model alone {sorted(only_model)}, "
                f"the schema alone {sorted(only_schema)}"
            )
        if asked_of(place) != required:
            found.append(
                f"{name}: required: the model {sorted(asked_of(place))}, the schema {sorted(required)}"
            )
        for member, (kind, _) in place.items():
            stated, expected = members.get(member), JSON_TYPES.get(kind)
            if (
                stated is not None
                and expected is not None
                and stated not in (expected, ALSO_ALLOWED[expected])
            ):
                found.append(f"{name}.{member}: type: the model {expected}, the schema {stated}")
    return found


def token_drift(files: Schema) -> list[str]:
    """Each token list of the build model's shape table, beyond those the vocabulary holds, that differs from
    the schema's."""
    defs = files["declaration.json"]["$defs"]
    assert isinstance(defs, dict)

    def enum(*path: str) -> JsonValue:
        node: JsonValue = defs
        for step in path:
            assert isinstance(node, dict), path
            node = node[step]
        return node

    pairs: list[tuple[str, tuple[str, ...], JsonValue]] = [
        (
            "MIXING_RULES",
            build_model.MIXING_RULES,
            enum("mixing", "properties", "rules", "additionalProperties", "enum"),
        ),
        ("SPACES", build_model.SPACES, enum("distribution", "properties", "space", "enum")),
        ("ACCEPTS", build_model.ACCEPTS, enum("overlay_scope", "properties", "accepts", "items", "enum")),
        ("PRECISIONS", build_model.PRECISIONS, enum("model_entry", "properties", "precision", "enum")),
    ]
    return [
        f"{table}: the model has {list(model)!r}, the schema {given!r}"
        for table, model, given in pairs
        if list(model) != given
    ]


def test_the_build_model_s_shape_table_and_token_lists_are_the_declaration_schema_s() -> None:
    files = schema()
    assert shape_drift(files) == []
    assert token_drift(files) == []


def test_every_place_of_the_shape_table_is_compared_with_the_schema() -> None:
    assert set(PLACES) == {*build_model.SHAPES, "reference", *build_model.KINDS}


def test_the_members_only_the_schema_names_are_the_basis_of_the_kinds_that_take_none() -> None:
    assert SCHEMA_ONLY.keys() == set(build_model.KINDS) - set(build_model.NEEDS_BASIS)
    for kind in SCHEMA_ONLY:
        assert "basis" not in build_model.acceptance_place(kind)
        assert "basis" in schema_place(schema(), PLACES[kind])[0]


DELETE: JsonValue = "delete the member"


def drifted_schema(file: str, path: tuple[str, ...], value: JsonValue) -> Schema:
    changed = copy.deepcopy(schema())
    host: JsonValue = changed[file]
    for step in path[:-1]:
        assert isinstance(host, dict)
        host = host[step]
    assert isinstance(host, dict)
    if value == DELETE:
        del host[path[-1]]
    else:
        host[path[-1]] = value
    return changed


@pytest.mark.parametrize(
    ("file", "path", "value", "found"),
    [
        (
            "declaration.json",
            ("$defs", "pick", "required"),
            ["acceptance", "field", "index", "reason"],
            "pick: required",
        ),
        ("declaration.json", ("$defs", "pick", "properties", "extra"), {"type": "string"}, "pick: members"),
        ("declaration.json", ("$defs", "pick", "properties", "basis"), DELETE, "pick: members"),
        (
            "declaration.json",
            ("$defs", "sampling", "properties", "independence", "type"),
            "object",
            "sampling.independence: type",
        ),
        ("declaration.json", ("$defs", "engine", "properties", "region_values"), DELETE, "engine: members"),
        ("declaration.json", ("$defs", "model_entry", "required"), ["model"], "model entry: required"),
        ("declaration.json", ("properties", "sampling"), DELETE, "declaration: members"),
        (
            "declaration.json",
            ("$defs", "tolerance_condition", "required"),
            ["tolerance"],
            "requirement condition: required",
        ),
        (
            "declaration.json",
            ("$defs", "checked_over_domain", "properties", "domain"),
            DELETE,
            "checked_over: members",
        ),
        (
            "read_request.json",
            ("$defs", "operating_value", "required"),
            ["value"],
            "operating condition: required",
        ),
        (
            "read_request.json",
            ("$defs", "material_ref", "properties", "id"),
            {"type": "number"},
            "reference.id: type",
        ),
        (
            "record.writer.json",
            ("$defs", "status_object", "properties", "reason"),
            DELETE,
            "status object: members",
        ),
        (
            "declaration.json",
            ("$defs", "mixing", "properties", "rules", "additionalProperties", "enum"),
            ["identity"],
            "MIXING_RULES",
        ),
        (
            "declaration.json",
            ("$defs", "distribution", "properties", "space", "enum"),
            ["identity"],
            "SPACES",
        ),
        (
            "declaration.json",
            ("$defs", "overlay_scope", "properties", "accepts", "items", "enum"),
            ["consumer"],
            "ACCEPTS",
        ),
        (
            "declaration.json",
            ("$defs", "model_entry", "properties", "precision", "enum"),
            ["binary32"],
            "PRECISIONS",
        ),
    ],
)
def test_a_drift_of_the_schema_from_the_shape_table_fails(
    file: str, path: tuple[str, ...], value: JsonValue, found: str
) -> None:
    files = drifted_schema(file, path, value)
    assert any(entry.startswith(found) for entry in [*shape_drift(files), *token_drift(files)])
