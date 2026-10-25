# SPDX-License-Identifier: Apache-2.0
"""Mutants of steps 9 and 10 (`core/fields.py`'s units, `core/conditions.py`, and `core/read.py` where it runs
them), each with one fault, and the property of `test_condition_properties.py` that must kill each one. As in
`test_value_field_mutants.py`, each must die within the examples the `ci` profile gives a property, at both
sizes, and records the examples its kill took as `examples_to_kill`.

A fault is injected where the core looks a name up when it runs: a module-level function or table of
`conditions`, `fields` or `read`, or `RecordField.specimen`.
"""

import copy
import dataclasses
from collections.abc import Callable, Collection, Mapping, Sequence
from fractions import Fraction
from typing import Any, NamedTuple

import pytest
from hypothesis import given
from hypothesis import strategies as st

from materica.core import conditions, fields, read
from materica.core.conditions import AxisEntry, ConditionsRead, ImpliedCondition
from materica.core.fields import RecordField
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.reasons import Reason
from materica.core.value_shapes import Found, JsonObject
from materica.core.vocabulary import VOCABULARY
from tests.property import test_condition_properties as properties
from tests.property.condition_strategies import (
    ENDING,
    FAULTS,
    ROWS,
    STEP_9_FAULTS,
    UNIT_PLACES,
    base_reads,
    faulty_reads,
    with_unknowns,
)
from tests.property.strategies import ORIGINAL, SMALL, Size
from tests.property.support import MUTANT_SEARCH, long_reprs_reported
from tests.property.test_mutants import setting
from tests.property.test_value_field_mutants import slipped_by, within_two_slips
from tests.unit import test_read


def drawn_rows(size: Size) -> st.SearchStrategy[Any]:
    return st.sampled_from(ROWS).flatmap(properties.numeric_cases)


def its_case(check: Callable[[Any], None]) -> Callable[[Any], None]:
    return lambda drawn: check(drawn.case)


def drawn_places(size: Size) -> st.SearchStrategy[Any]:
    return st.sampled_from(UNIT_PLACES).flatmap(lambda place: properties.other_units(place, size))


def second(check: Callable[[Any], None]) -> Callable[[tuple[str, Any]], None]:
    return lambda drawn: check(drawn[1])


def kind(drawn: tuple[str, Any]) -> set[str]:
    return {drawn[0]}


@st.composite
def table_cases_without_a_requirement(draw: st.DrawFn) -> tuple[str, properties.Case]:
    """A table case in which one condition the field's row requires is held nowhere: the record has none of
    it, and the request names none, so that only the row asks for it. `table_cases` names every required
    condition in the request, and leaves one so only where its `unchecked` kind removes the request's
    requirement of a condition and its `absent_but_required` kind then removes that condition from the record:
    a search drawn whole took 536 examples."""
    _, case = draw(properties.table_cases())
    name = draw(st.sampled_from(VOCABULARY.fields[properties.FIELD].requires))
    conditions = {held: value for held, value in case.conditions.items() if held != name}
    required = {asked: value for asked, value in case.required.items() if asked != name}
    return "absent_but_required", case._replace(conditions=conditions, required=required)


# Each property that kills a mutant, by name: its examples at a size, its check, and the labels of an example
# (the kind it was drawn of, a unit's place and kind, a read's faults, the places of its additions), among
# which a mutant's `dies_at` must be.
KILLERS: dict[
    str,
    tuple[Callable[[Size], st.SearchStrategy[Any]], Callable[[Any], None], Callable[[Any], set[str]]],
] = {
    "HP7": (drawn_rows, its_case(properties.check_against_the_oracle), lambda drawn: {drawn.boundary}),
    "HP7 plus or minus": (
        lambda size: properties.plus_minus_cases(),
        its_case(properties.check_against_the_oracle),
        lambda drawn: {drawn.kind},
    ),
    "HP7 table": (lambda size: properties.table_cases(), second(properties.check_against_the_oracle), kind),
    "HP7 table, a requirement held nowhere": (
        lambda size: table_cases_without_a_requirement(),
        second(properties.check_against_the_oracle),
        kind,
    ),
    "HP7 implied": (
        lambda size: properties.implied_cases(),
        second(properties.check_against_the_oracle),
        kind,
    ),
    "HP9": (lambda size: properties.merge_cases(), second(properties.check_merge), kind),
    "HP8 registered": (properties.registered_units, properties.check_registered, kind),
    "HP8 other": (drawn_places, properties.check_refused, lambda drawn: {drawn.place, drawn.kind}),
    "HP3": (
        lambda size: faulty_reads(tuple(FAULTS), size),
        properties.check_one_fault,
        lambda faulty: set(faulty.faults),
    ),
    # A planned search of HP3: reads whose first fault is one of step 10's that end the read and keep its
    # `conditions`. A mutant that leaves step 10's entries empty also ends a read step 10 does not end, as two
    # disagreeing implied conditions do, which HP3 whole catches on its reads past step 10 first.
    "HP3, a refusal at step 10": (
        lambda size: faulty_reads(ENDING, size),
        properties.check_one_fault,
        lambda faulty: set(faulty.faults),
    ),
    "HP5": (with_unknowns, properties.check_ignored, lambda unknowns: set(unknowns.places)),
    "base": (base_reads, properties.check_base, lambda read_case: set()),
    # Two deterministic tables of `tests/unit/test_read.py`, which no property draws: an implied condition
    # located elsewhere, read end to end, and the implied conditions step 0 refuses.
    "located elsewhere": (
        lambda size: st.sampled_from(test_read.ELSEWHERE),
        test_read.check_located_elsewhere,
        lambda where: {where},
    ),
    "step 0": (
        lambda size: st.sampled_from(test_read.IMPLIED_AT_STEP_0),
        lambda row: test_read.check_refused_at_step_0(row[1], row[2]),
        lambda row: {row[0]},
    ),
}


class Mutant(NamedTuple):
    name: str
    killer: str  # a key of KILLERS
    inject: Callable[[pytest.MonkeyPatch], None]
    dies_at: tuple[str, ...] = ()  # labels, one of which the example that kills it must have; any where none


# Step 10's comparisons.

STATED_ENDS = conditions._stated_ends  # pyright: ignore[reportPrivateUsage]  # the functions the faults replace
OPERATING_ENDS = conditions._operating_ends  # pyright: ignore[reportPrivateUsage]
WITHIN = conditions._within  # pyright: ignore[reportPrivateUsage]
COMPARED = conditions._compared  # pyright: ignore[reportPrivateUsage]


def _floating_point_as_written(condition: JsonObject, operating: Any, tolerance: float, bound: float) -> bool:
    a, b = STATED_ENDS(condition)
    lo, hi = OPERATING_ENDS(operating)
    return a - (tolerance - bound) <= lo and hi <= b + (tolerance - bound)


def _value_row_difference_in_floating_point(
    condition: JsonObject, operating: Any, tolerance: float, bound: float
) -> bool:
    """Section 5's first row as written, `|r - v| <= t`, and its bound's `|r - v| + u <= t`, in floating
    point."""
    if "value" in condition and "value" in operating:
        r, _ = STATED_ENDS(condition)
        v, _ = OPERATING_ENDS(operating)
        return abs(r - v) + bound <= tolerance
    return WITHIN(condition, operating, tolerance, bound)


def _strict(condition: JsonObject, operating: Any, tolerance: float, bound: float) -> bool:
    a, b = (Fraction(end) for end in STATED_ENDS(condition))
    lo, hi = (Fraction(end) for end in OPERATING_ENDS(operating))
    slack = Fraction(tolerance) - Fraction(bound)
    return a - slack < lo and hi < b + slack


def _stated_range_as_its_low_end(condition: JsonObject) -> tuple[float, float]:
    a, _ = STATED_ENDS(condition)
    return a, a


def _operating_range_as_its_low_end(operating: Any) -> tuple[float, float]:
    lo, _ = OPERATING_ENDS(operating)
    return lo, lo


def _bound_moves_the_low_end_only(
    condition: JsonObject, operating: Any, tolerance: float, bound: float
) -> bool:
    a, b = (Fraction(end) for end in STATED_ENDS(condition))
    lo, hi = (Fraction(end) for end in OPERATING_ENDS(operating))
    t, u = Fraction(tolerance), Fraction(bound)
    return a + u - t <= lo and hi <= b + t


def without_plus_minus(condition: JsonObject) -> JsonObject:
    return {name: member for name, member in condition.items() if name != "plus_minus"}


def _plus_minus_ignored(name: str, condition: JsonObject, operating: Any, required: Any) -> Reason | None:
    return COMPARED(name, without_plus_minus(condition), operating, required)


def _plus_minus_makes_not_met(
    name: str, condition: JsonObject, operating: Any, required: Any
) -> Reason | None:
    found = COMPARED(name, condition, operating, required)
    if found is not None and found.code == "condition_uncertain":
        return Reason("condition_outside", name)
    return found


def _sd_ignored(name: str, condition: JsonObject, operating: Any, required: Any) -> Reason | None:
    entries = condition.get("plus_minus")
    if isinstance(entries, list):
        bound: list[JsonValue] = [
            entry for entry in entries if isinstance(entry, dict) and entry.get("stated_as") == "bound"
        ]
        condition = {**condition, "plus_minus": bound} if bound else without_plus_minus(condition)
    return COMPARED(name, condition, operating, required)


def _unchecked_read_as_met(name: str, condition: JsonObject, operating: Any, required: Any) -> Reason | None:
    return None if required is None else COMPARED(name, condition, operating, required)


def _not_accepted_read_as_unknown(
    name: str, condition: JsonObject, operating: Any, required: Any
) -> Reason | None:
    found = COMPARED(name, condition, operating, required)
    if found is not None and found.code == "condition_not_accepted":
        return Reason("condition_unchecked", name)
    return found


def _accepted_where(
    matches: Callable[[str, list[str]], bool],
) -> Callable[[str, JsonObject, Any, Any], Reason | None]:
    """`_compared`, a token checked against an accept list by `matches` rather than by its presence."""

    def compared(name: str, condition: JsonObject, operating: Any, required: Any) -> Reason | None:
        if required is None or "accept" not in required:
            return COMPARED(name, condition, operating, required)
        if matches(str(condition["token"]), [str(token) for token in required["accept"]]):
            return None
        return Reason("condition_not_accepted", name)

    return compared


def _case_folded_in(token: str, accept: list[str]) -> bool:
    return token.casefold() in [listed.casefold() for listed in accept]


def _by_its_first_three_characters(token: str, accept: list[str]) -> bool:
    return any(listed.startswith(token[:3]) for listed in accept)


# Step 10's other rows, the conditions checked and the entries.

ENTRY = conditions._entry  # pyright: ignore[reportPrivateUsage]
CHECKED = conditions._checked  # pyright: ignore[reportPrivateUsage]
KNOWN = conditions._known  # pyright: ignore[reportPrivateUsage]


def _unknown_name_read_as_unstated(
    name: str, held: JsonValue | None, operating: Any, required: Any, reasons: list[Reason]
) -> Any:
    if name in VOCABULARY.conditions:
        return ENTRY(name, held, operating, required, reasons)
    reasons.append(Reason("condition_unstated", name))
    return conditions.ConditionEntry(name, "unknown")


def _an_unknown_status_read_as_unstated(
    name: str, held: JsonValue | None, operating: Any, required: Any, reasons: list[Reason]
) -> Any:
    if name in VOCABULARY.conditions or not (isinstance(held, dict) and "status" in held):
        return ENTRY(name, held, operating, required, reasons)
    reasons.append(Reason("condition_unstated", name))
    return conditions.ConditionEntry(name, "unknown", KNOWN(held, ("status", "reason")), operating)


def _required_with_ignored(
    held: JsonObject, requires: Collection[str], required: Mapping[str, object]
) -> list[str]:
    return list(dict.fromkeys([*held, *requires, *required]))


def _row_requirements_ignored(
    held: JsonObject, requires: Collection[str], required: Mapping[str, object]
) -> list[str]:
    return CHECKED(held, (), required)


def _status_record_dropped(
    name: str, held: JsonValue | None, operating: Any, required: Any, reasons: list[Reason]
) -> Any:
    entry = ENTRY(name, held, operating, required, reasons)
    status_object = isinstance(held, dict) and "status" in held
    return dataclasses.replace(entry, record=None) if status_object else entry


def _operating_dropped(
    name: str, held: JsonValue | None, operating: Any, required: Any, reasons: list[Reason]
) -> Any:
    return ENTRY(name, held, None if required is None else operating, required, reasons)


def _every_member_known(value: JsonObject, members: Collection[str]) -> JsonObject:
    return copy.deepcopy(value)


# Implied conditions.

FILLED = conditions._filled  # pyright: ignore[reportPrivateUsage]
SAID = conditions.said
FILLABLE = conditions._fillable  # pyright: ignore[reportPrivateUsage]


def _implied_overrides_stated(
    stored: JsonObject, applying: Sequence[ImpliedCondition]
) -> tuple[JsonObject, tuple[int, ...]]:
    filled: JsonObject = {}
    for condition in applying:
        for name, value in condition.implies.items():
            filled.setdefault(name, {**value, "basis": "implied"})
    return filled, tuple(condition.index for condition in applying)


def _fills_any_status(entry: JsonValue | None) -> bool:
    return entry is None or (isinstance(entry, dict) and "status" in entry)


def _disagreement_ignored(applying: Sequence[ImpliedCondition]) -> tuple[Reason, ...]:
    return ()


def _a_value_says_a_range(implied: JsonObject) -> tuple[object, ...]:
    found = SAID(implied)
    return ("range", *found[1:]) if found and found[0] == "value" else found


def _numbers_as_rationals(implied: JsonObject) -> tuple[object, ...]:
    if "token" in implied:
        return ("token", implied["token"])
    lo, hi = STATED_ENDS(implied)
    return ("value" if "value" in implied else "range", Fraction(lo), Fraction(hi))


def _applies_without_its_fact(specimen: JsonObject, fact: str, token: str) -> bool:
    return True


def _applied_not_recorded(
    stored: JsonObject, applying: Sequence[ImpliedCondition]
) -> tuple[JsonObject, tuple[int, ...]]:
    return FILLED(stored, applying)[0], ()


def _located_anywhere(self: ImpliedCondition, field: str, record: MaterialRef) -> bool:
    return True


def _located_without_its_hash(self: ImpliedCondition, field: str, record: MaterialRef) -> bool:
    held = self.location.get("record")
    return (
        self.field == field
        and set(self.location) == {"record"}
        and isinstance(held, dict)
        and (held.get("id"), held.get("version")) == (record.id, record.version)
    )


IMPLIED_VALUE = read._implied_value  # pyright: ignore[reportPrivateUsage]


def _a_value_not_an_object_ignored(name: str, value: JsonValue, where: str, found: list[Reason]) -> Any:
    if name in VOCABULARY.conditions and not isinstance(value, dict):
        return None
    return IMPLIED_VALUE(name, value, where, found)


# The specimen merge.


def _section_wins(self: RecordField) -> JsonObject:
    value = self.value
    assert isinstance(value, dict)
    field_facts, section_facts = value.get("specimen", {}), self.section.get("specimen", {})
    assert isinstance(field_facts, dict)
    assert isinstance(section_facts, dict)
    return {**field_facts, **section_facts}


def _a_status_fact_overrides_nothing(self: RecordField) -> JsonObject:
    value = self.value
    assert isinstance(value, dict)
    field_facts, section_facts = value.get("specimen", {}), self.section.get("specimen", {})
    assert isinstance(field_facts, dict)
    assert isinstance(section_facts, dict)
    stated = {
        name: fact for name, fact in field_facts.items() if not (isinstance(fact, dict) and "status" in fact)
    }
    return {**section_facts, **stated}


# Step 9.

SAME_UNIT = fields.same_unit
SPECIMENS = fields._specimens  # pyright: ignore[reportPrivateUsage]
UNIT_PROBLEMS = fields.unit_problems


def _nfkc(stored: JsonValue, registered: JsonValue) -> bool:
    import unicodedata

    if isinstance(stored, str) and isinstance(registered, str):
        return unicodedata.normalize("NFKC", stored) == unicodedata.normalize("NFKC", registered)
    return SAME_UNIT(stored, registered)


def _case_folded(stored: JsonValue, registered: JsonValue) -> bool:
    if isinstance(stored, str) and isinstance(registered, str):
        return stored.casefold() == registered.casefold()
    return SAME_UNIT(stored, registered)


def _stripped(stored: JsonValue, registered: JsonValue) -> bool:
    if isinstance(stored, str) and isinstance(registered, str):
        return "".join(stored.split()).strip("​") == registered
    return SAME_UNIT(stored, registered)


def _a_status_object_for_a_string(stored: JsonValue, registered: JsonValue) -> bool:
    return (isinstance(stored, dict) and "status" in stored) or SAME_UNIT(stored, registered)


def _without(field: RecordField, change: Callable[[JsonObject], None]) -> Found:
    """`unit_problems` of `field` with its value changed by `change`, its section kept."""
    value = copy.deepcopy(field.value)
    assert isinstance(value, dict)
    change(value)
    return UNIT_PROBLEMS(RecordField(field.spec, value, field.section))


def entries_of(condition: JsonValue) -> list[JsonObject]:
    """A condition's `plus_minus` entries, where it holds any."""
    entries = condition.get("plus_minus") if isinstance(condition, dict) else None
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def _plus_minus_units_unchecked(field: RecordField) -> Found:
    def change(value: JsonObject) -> None:
        for condition in conditions_of(value).values():
            for entry in entries_of(condition):
                assert isinstance(condition, dict)
                entry["unit"] = condition.get("unit")

    return _without(field, change)


def _only_the_first_plus_minus_unit(field: RecordField) -> Found:
    def change(value: JsonObject) -> None:
        for condition in conditions_of(value).values():
            for entry in entries_of(condition)[1:]:
                assert isinstance(condition, dict)
                entry["unit"] = condition.get("unit")

    return _without(field, change)


def _token_condition_units_unchecked(field: RecordField) -> Found:
    def change(value: JsonObject) -> None:
        for condition in conditions_of(value).values():
            if isinstance(condition, dict) and "token" in condition:
                condition.pop("unit", None)

    return _without(field, change)


def _section_facts_unchecked(field: RecordField) -> list[tuple[str, JsonObject]]:
    return [found for found in SPECIMENS(field) if not found[0].startswith("body.sections.")]


def _input_facts_unchecked(field: RecordField) -> list[tuple[str, JsonObject]]:
    return [found for found in SPECIMENS(field) if "input_specimens" not in found[0]]


def _condition_dropped(detail: str, condition: str | None) -> Reason:
    return Reason("unit_mismatch", None, detail)


def _plus_minus_against_the_field_unit(field: RecordField) -> Found:
    def change(value: JsonObject) -> None:
        for name, condition in conditions_of(value).items():
            registered = VOCABULARY.conditions[name].unit if name in VOCABULARY.conditions else None
            for entry in entries_of(condition):
                entry["unit"] = registered if entry.get("unit") == field.spec.unit else "not the field's"

    return _without(field, change)


def _facts_against_the_field_unit(field: RecordField) -> list[tuple[str, JsonObject]]:
    found: list[tuple[str, JsonObject]] = []
    for where, specimen in SPECIMENS(field):
        changed = copy.deepcopy(specimen)
        for fact in changed.values():
            if isinstance(fact, dict) and "unit" in fact and "status" not in fact:
                fact["unit"] = "s" if fact["unit"] == field.spec.unit else "not the field's"
        found.append((where, changed))
    return found


def conditions_of(value: JsonObject) -> JsonObject:
    held = value["conditions"]
    assert isinstance(held, dict)
    return held


# The read's order of steps.

READ_UNIT_PROBLEMS = fields.unit_problems
READ_CHECK_CONDITIONS = conditions.check_conditions


def step_10_after_step_9(monkeypatch: pytest.MonkeyPatch) -> None:
    """The read goes on to step 10 after step 9's `not_met`, reporting both steps' reasons."""
    held: list[Reason] = []

    def units(field: RecordField) -> Found:
        held[:] = READ_UNIT_PROBLEMS(field)
        return []

    def checked(
        field: RecordField,
        operating: Any,
        required: Any,
        implied: Sequence[ImpliedCondition] = (),
        axis: AxisEntry | None = None,
    ) -> ConditionsRead:
        found = READ_CHECK_CONDITIONS(field, operating, required, implied, axis)
        return dataclasses.replace(found, reasons=(*held, *found.reasons))

    monkeypatch.setattr(read, "unit_problems", units)
    monkeypatch.setattr(read, "check_conditions", checked)


def _first_unit_reason_only(field: RecordField) -> Found:
    return READ_UNIT_PROBLEMS(field)[:1]


def _unknown_reasons_dropped(
    field: RecordField,
    operating: Any,
    required: Any,
    implied: Sequence[ImpliedCondition] = (),
    axis: AxisEntry | None = None,
) -> ConditionsRead:
    found = READ_CHECK_CONDITIONS(field, operating, required, implied, axis)
    kept = tuple(reason for reason in found.reasons if VOCABULARY.reasons[reason.code].status == "not_met")
    return dataclasses.replace(found, reasons=kept)


def _conditions_withheld(
    field: RecordField,
    operating: Any,
    required: Any,
    implied: Sequence[ImpliedCondition] = (),
    axis: AxisEntry | None = None,
) -> ConditionsRead:
    return dataclasses.replace(READ_CHECK_CONDITIONS(field, operating, required, implied, axis), entries=None)


def _disagreement_checks_the_others(
    field: RecordField,
    operating: Any,
    required: Any,
    implied: Sequence[ImpliedCondition] = (),
    axis: AxisEntry | None = None,
) -> ConditionsRead:
    found = READ_CHECK_CONDITIONS(field, operating, required, implied, axis)
    if found.entries is not None:
        return found
    rest = READ_CHECK_CONDITIONS(field, operating, required, (), axis)
    return ConditionsRead(found.reasons + rest.reasons, rest.entries)


# What step 0 ignores of a request.

SLIPS = read._slips  # pyright: ignore[reportPrivateUsage]


def _unknown_request_members_refused(
    value: dict[str, JsonValue],
    named: Collection[str],
    where: str,
    found: list[Reason],
    condition: str | None = None,
) -> None:
    SLIPS(value, named, where, found, condition)
    found.extend(Reason("request_incomplete", condition) for member in value if member not in named)


MUTANTS = [
    Mutant(
        "floating_point_as_written",
        "HP7",
        setting(conditions, "_within", _floating_point_as_written),
        ("anywhere", "at_the_tolerance", "one_ulp_outside", "rounded_difference", "minus_zero"),
    ),
    Mutant(
        "value_row_difference_in_floating_point",
        "HP7",
        setting(conditions, "_within", _value_row_difference_in_floating_point),
        ("anywhere", "at_the_tolerance", "one_ulp_outside", "rounded_difference", "mixed_magnitudes_outside"),
    ),
    Mutant("strict_inequalities", "HP7", setting(conditions, "_within", _strict)),
    Mutant(
        "stated_range_as_its_low_end",
        "HP7",
        setting(conditions, "_stated_ends", _stated_range_as_its_low_end),
    ),
    Mutant(
        "operating_range_as_its_low_end",
        "HP7",
        setting(conditions, "_operating_ends", _operating_range_as_its_low_end),
    ),
    Mutant(
        "plus_minus_ignored",
        "HP7 plus or minus",
        setting(conditions, "_compared", _plus_minus_ignored),
        ("bound", "sd", "unstated", "bound_beside_sd"),
    ),
    Mutant(
        "plus_minus_makes_not_met",
        "HP7 plus or minus",
        setting(conditions, "_compared", _plus_minus_makes_not_met),
        ("bound", "sd", "unstated", "bound_beside_sd"),
    ),
    Mutant(
        "sd_ignored", "HP7 plus or minus", setting(conditions, "_compared", _sd_ignored), ("sd", "unstated")
    ),
    Mutant(
        "bound_moves_the_low_end_only",
        "HP7 plus or minus",
        setting(conditions, "_within", _bound_moves_the_low_end_only),
        ("bound", "bound_beside_sd"),
    ),
    Mutant("unchecked_read_as_met", "HP7 table", setting(conditions, "_compared", _unchecked_read_as_met)),
    Mutant(
        "not_accepted_read_as_unknown",
        "HP7 table",
        setting(conditions, "_compared", _not_accepted_read_as_unknown),
    ),
    Mutant(
        "unknown_name_read_as_unstated",
        "HP7 table",
        setting(conditions, "_entry", _unknown_name_read_as_unstated),
    ),
    Mutant(
        "accept_list_case_folded",
        "HP7 table",
        setting(conditions, "_compared", _accepted_where(_case_folded_in)),
    ),
    Mutant(
        "accept_list_by_prefix",
        "HP7 table",
        setting(conditions, "_compared", _accepted_where(_by_its_first_three_characters)),
    ),
    Mutant(
        "unknown_name_status_read_as_unstated",
        "HP7 table",
        setting(conditions, "_entry", _an_unknown_status_read_as_unstated),
    ),
    Mutant("required_with_ignored", "HP7 table", setting(conditions, "_checked", _required_with_ignored)),
    Mutant(
        "row_requirements_ignored",
        "HP7 table, a requirement held nowhere",
        setting(conditions, "_checked", _row_requirements_ignored),
    ),
    Mutant("status_object_not_returned", "HP7 table", setting(conditions, "_entry", _status_record_dropped)),
    Mutant(
        "operating_returned_only_with_a_requirement",
        "HP7 table",
        setting(conditions, "_entry", _operating_dropped),
    ),
    Mutant(
        "implied_overrides_a_stated_value",
        "HP7 implied",
        setting(conditions, "_filled", _implied_overrides_stated),
        ("never_over_a_stated_value", "never_over_another_status"),
    ),
    Mutant(
        "implied_fills_any_status",
        "HP7 implied",
        setting(conditions, "_fillable", _fills_any_status),
        ("never_over_another_status",),
    ),
    Mutant(
        "disagreement_ignored",
        "HP7 implied",
        setting(conditions, "_disagreeing", _disagreement_ignored),
        ("two_that_disagree", "a_value_beside_a_range", "minus_zero_beside_zero"),
    ),
    Mutant(
        "a_value_agrees_with_its_range",
        "HP7 implied",
        setting(conditions, "said", _a_value_says_a_range),
        ("a_value_beside_a_range",),
    ),
    Mutant(
        "minus_zero_agrees_with_zero",
        "HP7 implied",
        setting(conditions, "said", _numbers_as_rationals),
        ("minus_zero_beside_zero",),
    ),
    Mutant(
        "implied_applies_without_its_fact",
        "HP7 implied",
        setting(conditions, "_states", _applies_without_its_fact),
        ("its_fact_not_stated",),
    ),
    Mutant("applied_not_recorded", "HP7 implied", setting(conditions, "_filled", _applied_not_recorded)),
    Mutant(
        "implied_not_located", "located elsewhere", setting(ImpliedCondition, "located_at", _located_anywhere)
    ),
    Mutant(
        "located_at_without_its_hash",
        "located elsewhere",
        setting(ImpliedCondition, "located_at", _located_without_its_hash),
        ("another_content_hash",),
    ),
    Mutant(
        "implies_value_not_an_object_ignored",
        "step 0",
        setting(read, "_implied_value", _a_value_not_an_object_ignored),
        ("a value that is not an object",),
    ),
    Mutant(
        "section_facts_win",
        "HP9",
        setting(RecordField, "specimen", _section_wins),
        ("the_field_another_token", "the_field_a_status_object", "the_section_a_status_object"),
    ),
    Mutant(
        "a_status_fact_overrides_nothing",
        "HP9",
        setting(RecordField, "specimen", _a_status_fact_overrides_nothing),
        ("the_field_a_status_object",),
    ),
    Mutant(
        "nfkc_before_comparing", "HP8 other", setting(fields, "same_unit", _nfkc), ("compatibility_equal",)
    ),
    Mutant(
        "case_folded",
        "HP8 other",
        setting(fields, "same_unit", _case_folded),
        ("case_folded", "compatibility_equal"),
    ),
    Mutant("spaces_ignored", "HP8 other", setting(fields, "same_unit", _stripped), ("spaced",)),
    Mutant(
        "a_status_object_where_a_string_is_registered",
        "HP8 other",
        setting(fields, "same_unit", _a_status_object_for_a_string),
        ("status_object",),
    ),
    Mutant(
        "plus_minus_units_unchecked",
        "HP8 other",
        setting(read, "unit_problems", _plus_minus_units_unchecked),
        ("plus_minus",),
    ),
    Mutant(
        "only_the_first_plus_minus_unit",
        "HP8 other",
        setting(read, "unit_problems", _only_the_first_plus_minus_unit),
        ("plus_minus",),
    ),
    Mutant(
        "token_condition_units_unchecked",
        "HP8 other",
        setting(read, "unit_problems", _token_condition_units_unchecked),
        ("token_condition",),
    ),
    Mutant(
        "section_facts_unchecked",
        "HP8 other",
        setting(fields, "_specimens", _section_facts_unchecked),
        ("section_fact",),
    ),
    Mutant(
        "input_facts_unchecked",
        "HP8 other",
        setting(fields, "_specimens", _input_facts_unchecked),
        ("input_fact",),
    ),
    Mutant(
        "condition_dropped_from_unit_mismatch",
        "HP8 other",
        setting(fields, "_mismatch", _condition_dropped),
        ("condition", "plus_minus", "token_condition"),
    ),
    Mutant(
        "plus_minus_against_the_field_unit",
        "HP8 registered",
        setting(read, "unit_problems", _plus_minus_against_the_field_unit),
    ),
    Mutant(
        "facts_against_the_field_unit",
        "HP8 registered",
        setting(fields, "_specimens", _facts_against_the_field_unit),
    ),
    Mutant("step_10_after_a_refusal_at_step_9", "HP3", step_10_after_step_9, tuple(STEP_9_FAULTS)),
    Mutant(
        "first_unit_reason_only",
        "HP3",
        setting(read, "unit_problems", _first_unit_reason_only),
        tuple(STEP_9_FAULTS),
    ),
    Mutant(
        "unknown_reasons_dropped_beside_not_met",
        "HP3",
        setting(read, "check_conditions", _unknown_reasons_dropped),
        ("unchecked", "unstated", "unknown_name", "uncertain"),
    ),
    Mutant(
        "conditions_withheld_from_a_refusal",
        "HP3, a refusal at step 10",
        setting(read, "check_conditions", _conditions_withheld),
        ENDING,
    ),
    Mutant(
        "disagreement_checks_the_others",
        "HP3",
        setting(read, "check_conditions", _disagreement_checks_the_others),
        ("disagreeing",),
    ),
    Mutant(
        "unknown_members_returned_in_an_entry",
        "HP5",
        setting(conditions, "_known", _every_member_known),
        ("condition", "plus_minus_entry"),
    ),
    Mutant("two_slips_refused_in_a_request", "HP5", setting(read, "slipped", slipped_by(within_two_slips))),
    Mutant(
        "unknown_request_members_refused",
        "HP5",
        setting(read, "_slips", _unknown_request_members_refused),
        ("operating", "requirement_condition", "tolerance", "implied", "implied_record", "implied_value"),
    ),
]


def kill(examples: st.SearchStrategy[Any], check: Callable[[Any], None]) -> tuple[int, Any]:
    """The examples searched until `check` first fails, and that example; an AssertionError where it never
    does."""
    tried = 0
    first: list[tuple[int, Any]] = []

    @MUTANT_SEARCH
    @given(examples)
    def search(example: Any) -> None:
        nonlocal tried
        tried += 1
        try:
            check(example)
        except AssertionError:
            first.append((tried, example))
            raise

    try:
        with long_reprs_reported():
            search()
    except AssertionError:
        return first[0]
    raise AssertionError(f"the mutant survived {tried} examples")


@pytest.mark.parametrize("size", [pytest.param(SMALL, id="small"), pytest.param(ORIGINAL, id="original")])
@pytest.mark.parametrize("mutant", MUTANTS, ids=[mutant.name for mutant in MUTANTS])
def test_the_mutant_is_killed(
    mutant: Mutant,
    size: Size,
    monkeypatch: pytest.MonkeyPatch,
    record_property: Callable[[str, object], None],
) -> None:
    """At an example of one of the labels it names, where it names some."""
    mutant.inject(monkeypatch)
    examples, check, labels = KILLERS[mutant.killer]
    tried, example = kill(examples(size), check)
    record_property("examples_to_kill", tried)
    assert not mutant.dies_at or labels(example) & set(mutant.dies_at), labels(example)
