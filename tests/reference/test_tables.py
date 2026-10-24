# SPDX-License-Identifier: Apache-2.0
"""The reference model's tables, written from the specification's text, against the vocabulary the generator
writes from the same text (`schema/0.1/vocabulary/`), so that a drift of either fails here; and so the build
model's own token lists, those of its shape table that the vocabulary holds. The vocabulary is
read as a file, not through `materica`; the control drifts a copy of it one table at a time."""

import copy
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
