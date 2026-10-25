# SPDX-License-Identifier: Apache-2.0
"""Step 10 of a read: the conditions (`read_side_contract.md` section 3, step 10, and section 5).

The conditions checked are those the record holds, those an implied condition the read applies fills, those
the field's row requires, those another condition requires with the token it holds, and those the request's
requirement names, each giving one entry of the result's `conditions`. A condition the record states is
compared with the request by section 5's table, every comparison made on the exact values of the doubles, as
rationals, so that no rounding of `r - v` passes a value outside its tolerance; a stated `plus_minus` can only
turn `met` into `unknown`.

A table's own axis, held as `not_applicable` (`record_format.md` section 6, table item 1), is section 5's
first row: its entry's status is the table's (`AxisEntry`), and step 10 gives no reason for it and does not
end the read on it; step 11 does both.

An implied condition (`declarations.md` section 4.1) applies where the request locates it at the read
(section 1) and the field's specimen, the section's facts merged with the field's, states its fact and token.
It fills a condition the record does not hold, or holds as `unstated`, as if the record stated it with the
basis `implied`. Two that apply and supply different values for one condition end the read here, with
`request_incomplete` for that condition, and then no condition is checked (ruling A). Values differ unless
they are of one shape and hold the same token or the same doubles bit for bit, so that which of two that agree
fills a condition never depends on their order.
"""

import copy
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeGuard, get_type_hints

from materica import shapes
from materica.core.fields import RecordField
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.reasons import Reason
from materica.core.status import ReadStatus
from materica.core.value_shapes import (
    IMPLIED_BASIS,
    JsonObject,
    a_list,
    an_object,
    is_status_object,
    status_row,
)
from materica.core.vocabulary import VOCABULARY


def located_at(named: str, location: JsonObject, field: str, record: MaterialRef) -> bool:
    """Whether an acceptance naming the field `named` at `location` applies to a read of `field` in `record`:
    it names that field, and that record as its one location, by `id`, `version` and `content_hash`
    (`read_side_contract.md` section 1)."""
    reference: JsonObject = {"id": record.id, "version": record.version, "content_hash": record.content_hash}
    return named == field and location == {"record": reference}


@dataclass(frozen=True)
class ImpliedCondition:
    """An implied condition of a request's `acceptances` that passed step 0: its index there; the field it
    names; where it is located, its `record`, `region` and `interval` as the request gives them, a record by
    the members a reference names; the specimen fact and token it rests on; and the value it implies for each
    condition, holding the members its shape names, a value or a range and a unit, or a token."""

    index: int
    field: str
    location: JsonObject
    fact: str
    token: str
    implies: dict[str, JsonObject]

    def located_at(self, field: str, record: MaterialRef) -> bool:
        return located_at(self.field, self.location, field, record)

    def to_json(self) -> JsonObject:
        return {
            "acceptance": "implied_condition",
            **copy.deepcopy(self.location),
            "field": self.field,
            "fact": self.fact,
            "token": self.token,
            "implies": {name: copy.deepcopy(value) for name, value in self.implies.items()},
        }


@dataclass(frozen=True)
class ConditionEntry:
    """An entry of a result's `conditions` (`read_side_contract.md` section 2 item 6): its `record` is the
    record's entry, holding the members the reader knows, as stored; its `operating`, the request's operating
    condition. Either is None where there is none."""

    name: str
    status: ReadStatus
    record: JsonObject | None = None
    operating: shapes.OperatingCondition | None = None

    @classmethod
    def from_json(cls, entry: JsonObject) -> "ConditionEntry":
        name, status, record = entry.get("name"), entry.get("status"), entry.get("record")
        if not (isinstance(name, str) and isinstance(status, str) and status in _STATUSES):
            raise ValueError(f"not a condition entry: {entry!r}")
        if record is not None and not isinstance(record, dict):
            raise ValueError(f"not a condition entry's record: {record!r}")
        operating = entry.get("operating")
        return cls(name, _STATUSES[status], record, None if operating is None else _operating(operating))

    def to_json(self) -> JsonObject:
        entry: JsonObject = {"name": self.name, "status": self.status}
        if self.record is not None:
            entry["record"] = copy.deepcopy(self.record)
        if self.operating is not None:
            entry["operating"] = operating_json(self.operating)
        return entry


@dataclass(frozen=True)
class AxisEntry:
    """A table's axis and the status of its entry (section 5, first row): "the entry is `met` when the
    operating value lies in the form's range and on no declared edge ... and otherwise `not_met`, with no
    operating value or over an operating range included"."""

    name: str
    status: ReadStatus


@dataclass(frozen=True)
class ConditionsRead:
    """What step 10 found: its reasons; the entries of the result's `conditions`, or None where two implied
    conditions disagree and no condition is checked; and the indexes, in the request's `acceptances`, of the
    implied conditions that fill a condition."""

    reasons: tuple[Reason, ...]
    entries: tuple[ConditionEntry, ...] | None
    applied: tuple[int, ...] = ()


def check_conditions(
    field: RecordField,
    operating: Mapping[str, shapes.OperatingCondition],
    required: Mapping[str, shapes.RequirementCondition],
    implied: Sequence[ImpliedCondition] = (),
    axis: AxisEntry | None = None,
) -> ConditionsRead:
    """Step 10 for `field`, which passed steps 8 and 9, against the request's operating conditions and the
    conditions its requirement names (step 0 gives a tolerance only with an operating condition), with the
    implied conditions the request locates at the read; `axis`, a table's own axis entry."""
    specimen = field.specimen()
    applying = [condition for condition in implied if _states(specimen, condition.fact, condition.token)]
    disagreeing = _disagreeing(applying)
    if disagreeing:
        return ConditionsRead(disagreeing, None)
    stored = an_object(an_object(field.value)["conditions"])
    filled, applied = _filled(stored, applying)
    held = {**stored, **filled}
    reasons: list[Reason] = []
    entries = tuple(
        _axis_entry(axis, held[name], operating.get(name))
        if axis is not None and name == axis.name and _on_its_axis(held[name])
        else _entry(name, held.get(name), operating.get(name), required.get(name), reasons)
        for name in _checked(held, field.spec.requires, required)
    )
    return ConditionsRead(tuple(reasons), entries, applied)


def _states(specimen: JsonObject, fact: str, token: str) -> bool:
    stated = specimen.get(fact)
    return isinstance(stated, dict) and not is_status_object(stated) and stated.get("token") == token


def said(implied: JsonObject) -> tuple[object, ...]:
    """What an implied value says, to compare two: a token, or a value or a range, its numbers bit for bit."""
    if "token" in implied:
        return ("token", implied["token"])
    lo, hi = _stated_ends(implied)
    return ("value" if "value" in implied else "range", lo.hex(), hi.hex())


def _disagreeing(applying: Sequence[ImpliedCondition]) -> tuple[Reason, ...]:
    """`request_incomplete` for each condition to which two implied conditions that apply give different
    values (`read_side_contract.md` section 1)."""
    differing: dict[str, set[tuple[object, ...]]] = {}
    for condition in applying:
        for name, value in condition.implies.items():
            differing.setdefault(name, set()).add(said(value))
    return tuple(
        Reason("request_incomplete", name, f"two implied conditions that apply give {name} different values")
        for name, values in differing.items()
        if len(values) > 1
    )


def _fillable(entry: JsonValue | None) -> bool:
    """A condition the record does not hold, or holds as `unstated`: an implied condition fills it, never one
    holding another status object or a value (`declarations.md` section 4.1 item 1)."""
    return entry is None or (is_status_object(entry) and an_object(entry)["status"] == "unstated")


def _filled(stored: JsonObject, applying: Sequence[ImpliedCondition]) -> tuple[JsonObject, tuple[int, ...]]:
    """The conditions the implied conditions that apply fill, each as stated with the basis `implied`, and
    the indexes of those that fill one."""
    filled: JsonObject = {}
    applied: list[int] = []
    for condition in applying:
        for name, value in condition.implies.items():
            if _fillable(stored.get(name)):
                filled.setdefault(name, {**copy.deepcopy(value), "basis": IMPLIED_BASIS})
                applied.append(condition.index)
    return filled, tuple(dict.fromkeys(applied))


def _token(entry: JsonValue | None) -> JsonValue:
    return entry.get("token") if isinstance(entry, dict) and not is_status_object(entry) else None


def _checked(held: JsonObject, requires: Collection[str], required: Mapping[str, object]) -> list[str]:
    """The names of the conditions checked, each once: those the record holds; those the row requires; those
    another condition requires with the token it holds (`provenance.md` section 6.1 item 9); and those the
    request's requirement names."""
    with_tokens = [
        spec.name
        for spec in VOCABULARY.conditions.values()
        for other, tokens in spec.required_with.items()
        if _token(held.get(other)) in tokens
    ]
    return list(dict.fromkeys([*held, *requires, *with_tokens, *required]))


def _on_its_axis(entry: JsonValue) -> bool:
    """A condition held as `{"status": "not_applicable"}`, which on a table's own axis is section 5's first
    row (step 8 refused any other entry there)."""
    return is_status_object(entry) and an_object(entry)["status"] == "not_applicable"


def _axis_entry(
    axis: AxisEntry, held: JsonValue, operating: shapes.OperatingCondition | None
) -> ConditionEntry:
    """A table's own axis entry: its status the table's, and no reason, since "Step 10 gives no reason for it
    and does not end the read on it: the form checks it, at step 11, which gives the reason" (section 5, first
    row); a tolerance on the axis plays no part, as "the tolerance never widens a table" (section 5)."""
    return ConditionEntry(axis.name, axis.status, _as_read(axis.name, an_object(held)), operating)


def _entry(
    name: str,
    held: JsonValue | None,
    operating: shapes.OperatingCondition | None,
    required: shapes.RequirementCondition | None,
    reasons: list[Reason],
) -> ConditionEntry:
    """The entry of the condition `name` by section 5's table, its reason, if any, appended to `reasons`."""
    if name not in VOCABULARY.conditions:
        reasons.append(
            Reason("condition_unknown_name", name, f"{name} is a condition the reader does not know")
        )
        return ConditionEntry(name, "unknown")
    record = None if held is None else _as_read(name, an_object(held))
    if held is None or is_status_object(held):
        reasons.append(Reason("condition_unstated", name, f"the source does not state {name}"))
        return ConditionEntry(name, "unknown", record, operating)
    found = _compared(name, an_object(held), operating, required)
    if found is None:
        return ConditionEntry(name, "met", record, operating)
    reasons.append(found)
    return ConditionEntry(name, VOCABULARY.reasons[found.code].status, record, operating)


def _compared(
    name: str,
    condition: JsonObject,
    operating: shapes.OperatingCondition | None,
    required: shapes.RequirementCondition | None,
) -> Reason | None:
    """The reason a stated condition is not `met` against the request, or None where it is."""
    if required is None:
        return Reason("condition_unchecked", name, f"the request gives {name} no tolerance or accept list")
    if _accepts(required):
        if condition["token"] in required["accept"]:
            return None
        return Reason("condition_not_accepted", name, f"{name}'s token is not in the accept list")
    if operating is None or not _tolerates(required):
        raise ValueError("step 0 lets through no tolerance without its operating condition")
    tolerance = required["tolerance"]["value"]
    if not _within(condition, operating, tolerance, 0.0):
        return Reason("condition_outside", name, f"{name} is outside the tolerance")
    stated = [an_object(entry) for entry in a_list(condition.get("plus_minus", []))]
    bounds = [_number(entry["value"]) for entry in stated if entry["stated_as"] == "bound"]
    if bounds:
        assured = _within(condition, operating, tolerance, bounds[0])
    else:
        assured = not any(_number(entry["value"]) > 0 for entry in stated)
    if assured:
        return None
    return Reason(
        "condition_uncertain", name, f"{name}'s stated plus or minus leaves the tolerance unassured"
    )


def _within(
    condition: JsonObject, operating: shapes.OperatingCondition, tolerance: float, bound: float
) -> bool:
    """Whether every value within `bound` of the stated value or range lies within `tolerance` of the
    operating value or range, exactly. A value `r` is the range `[r, r]`, and so is an operating value, so
    that section 5's four rows, and its `plus_minus` rule, are one test: `a + u - t <= lo` and
    `hi <= b - u + t`."""
    a, b = (Fraction(end) for end in _stated_ends(condition))
    lo, hi = (Fraction(end) for end in _operating_ends(operating))
    slack = Fraction(tolerance) - Fraction(bound)
    return a - slack <= lo and hi <= b + slack


def _stated_ends(condition: JsonObject) -> tuple[float, float]:
    if "value" in condition:
        return _number(condition["value"]), _number(condition["value"])
    return _pair(condition["range"])


def _operating_ends(operating: shapes.OperatingCondition) -> tuple[float, float]:
    if _is_value(operating):
        return operating["value"], operating["value"]
    if _is_range(operating):
        return operating["range"]
    raise TypeError("step 0 lets through no operating condition but a value or a range")


# Which of their shapes a requirement's condition and an operating condition hold, step 0 having checked them.


def _accepts(required: shapes.RequirementCondition) -> TypeGuard[shapes.AcceptRequirement]:
    return "accept" in required


def _tolerates(required: shapes.RequirementCondition) -> TypeGuard[shapes.ToleranceRequirement]:
    return "tolerance" in required


def _is_value(operating: shapes.OperatingCondition) -> TypeGuard[shapes.OperatingValue]:
    return "value" in operating


def _is_range(operating: shapes.OperatingCondition) -> TypeGuard[shapes.OperatingRange]:
    return "range" in operating


# What a result returns of a record's condition: the members the reader's version defines, as stored
# (`read_side_contract.md` section 2 item 5), as the writer schema's shapes give them.
_STATUS_MEMBERS = tuple(get_type_hints(shapes.StatusObject))
_PLUS_MINUS_MEMBERS = tuple(get_type_hints(shapes.PlusMinusEntry))
_STATUSES: dict[str, ReadStatus] = {"met": "met", "not_met": "not_met", "unknown": "unknown"}


def _as_read(name: str, condition: JsonObject) -> JsonObject:
    if is_status_object(condition):
        return _known(condition, _STATUS_MEMBERS)
    found = _known(condition, status_row(shapes.Conditions, name)[1])
    if "plus_minus" in found:
        found["plus_minus"] = [_plus_minus_entry(an_object(entry)) for entry in a_list(found["plus_minus"])]
    return found


def _plus_minus_entry(entry: JsonObject) -> JsonValue:
    found = _known(entry, _PLUS_MINUS_MEMBERS)
    if is_status_object(found["stated_as"]):
        found["stated_as"] = _known(an_object(found["stated_as"]), _STATUS_MEMBERS)
    return found


def _known(value: JsonObject, members: Collection[str]) -> JsonObject:
    return {name: copy.deepcopy(member) for name, member in value.items() if name in members}


def _operating(value: JsonValue) -> shapes.OperatingCondition:
    entry = an_object(value)
    unit = entry["unit"]
    if not isinstance(unit, str):
        raise ValueError(f"not an operating condition: {entry!r}")
    if "value" in entry:
        return {"value": _number(entry["value"]), "unit": unit}
    return {"range": _pair(entry["range"]), "unit": unit}


def operating_json(operating: shapes.OperatingCondition) -> JsonObject:
    """An operating condition as JSON: a value, or a range as a list, and the unit."""
    if _is_value(operating):
        return {"value": operating["value"], "unit": operating["unit"]}
    lo, hi = _operating_ends(operating)
    return {"range": [lo, hi], "unit": operating["unit"]}


def _number(value: object) -> float:
    if not isinstance(value, float):
        raise TypeError(f"step 8 lets through no {type(value).__name__} here")
    return value


def _pair(value: object) -> tuple[float, float]:
    match value:
        case [float() as lo, float() as hi]:
            return lo, hi
        case _:
            raise TypeError(f"steps 0 and 8 let through no {type(value).__name__} here")
