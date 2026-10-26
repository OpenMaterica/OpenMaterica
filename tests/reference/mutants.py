# SPDX-License-Identifier: Apache-2.0
"""Seeded faults of the reference model, each one rule of the text broken, run against every case file
(`test_seeded_faults.py`). A fault the cases kill is a rule they pin; one that survives is a rule no case
pins, which the properties of S2a-4's phase B must kill. The table, with what each one's search found, is
`README.md`'s.

Each fault replaces one to three of the model's module-level names, which the model looks up when it runs.
The build model's faults (`BUILD_MUTANTS`, run against every build-check case file) replace its names alike,
a dotted name reaching a method of its `DeclarationCheck`."""

import dataclasses
import math
import re
from collections.abc import Callable, Collection, Generator, Iterable, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from fractions import Fraction
from types import ModuleType
from typing import TypeVar
from unittest import mock

from tests.reference import build_model as build
from tests.reference import read_model as model
from tests.reference.read_model import (
    ConditionRow,
    FieldRead,
    FieldRow,
    ImpliedCondition,
    Reason,
    Reasons,
    Reference,
    Request,
    Source,
    Status,
    StatusObject,
)
from tests.reference.strict_json import JsonObject, JsonValue, NotStrictJson, parse


@dataclass(frozen=True)
class Mutant:
    fault: str
    rule: str  # where the text states the rule the fault breaks
    patches: Mapping[str, object]
    survives: str | None = None  # why no case file kills it, for one none does
    module: ModuleType = model  # the model whose names the patches replace

    @contextmanager
    def applied(self) -> Generator[None, None, None]:
        with ExitStack() as stack:
            for name, replacement in self.patches.items():
                *path, attribute = name.split(".")
                host: object = self.module
                for part in path:
                    host = getattr(host, part)
                stack.enter_context(mock.patch.object(host, attribute, replacement))
            yield


# The model's own functions, taken before any fault replaces them.
_check_value_field = model.check_value_field
_checked_acceptances = model.checked_acceptances
_checked_requirement = model.checked_requirement
_check_composition = model.check_composition
_check_fact = model.check_fact
_check_input_specimens = model.check_input_specimens
_check_population_level = model.check_population_level
_check_plus_minus = model.check_plus_minus
_check_uncertainty = model.check_uncertainty
_check_label = model.check_label
_check_provenance = model.check_provenance
_check_units = model.check_units
_condition_entry = model.condition_entry
_conditions_checked = model.conditions_checked
_fate_of = model.fate_of
_reasons_beside_two_or_more = model.reasons_beside_two_or_more
_reasons_where_refused = model.reasons_where_refused
_read_alternatives = model.read_alternatives
_read_decided = model.read_decided
_read_value_field = model.read_value_field
_resolve = model.resolve
_review_read = model.review_read
_same_unit = model.same_unit
_plural_of_either = model._plural_of_either  # pyright: ignore[reportPrivateUsage]
_shape_by_want = model.shape_by_want
_sources_read = model.sources_read
_status_object = model.status_object
_unit_returned = model.unit_returned
_within_tolerance = model.within_tolerance
_table_axis = model.table_axis
_read_the_table = model.read_the_table
_extrapolation_covers = model.extrapolation_covers
_at_the_read = model.at_the_read
_readable_range = model.readable_range
_form_member_returned = model.form_member_returned
_form_want_gives = model.form_want_gives


class EveryString:
    def __contains__(self, item: object) -> bool:
        return isinstance(item, str)


class EveryPair:
    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = None  # type: ignore[assignment]


def no_request_unit_compared(unit: JsonValue, row: ConditionRow) -> bool:
    return False


def operating_for_every_tolerance(
    request: JsonObject, claims: frozenset[str], reasons: Reasons
) -> tuple[str | None, dict[str, float], dict[str, tuple[str, ...]]]:
    requirement = request.get("requirement")
    conditions = requirement.get("conditions") if isinstance(requirement, dict) else None
    operating = request.get("operating_conditions", {})
    if isinstance(conditions, dict) and isinstance(operating, dict):
        given: JsonObject = {name: {} for name in conditions}
        request = {**request, "operating_conditions": {**given, **operating}}
    return _checked_requirement(request, claims, reasons)


def unchecked_without_an_operating_condition(
    name: str,
    held: JsonObject,
    applied: Mapping[str, JsonObject],
    request: Request,
    reasons: Reasons,
    axis: model.TableAxis | None = None,
) -> JsonObject:
    """The entry of a condition whose tolerance has no operating condition, a request the fault above lets
    through, read as one given no tolerance: there is nothing to compare it with, and the request holds no
    operating condition of that name to index."""
    if name in request.tolerances and name not in request.operating:
        tolerances = {other: value for other, value in request.tolerances.items() if other != name}
        request = dataclasses.replace(request, tolerances=tolerances)
    return _condition_entry(name, held, applied, request, reasons, axis)


def negative_zero_tolerance_refused(
    request: JsonObject, claims: frozenset[str], reasons: Reasons
) -> tuple[str | None, dict[str, float], dict[str, tuple[str, ...]]]:
    checked = _checked_requirement(request, claims, reasons)
    requirement = request.get("requirement")
    conditions = requirement.get("conditions") if isinstance(requirement, dict) else None
    if not isinstance(conditions, dict):
        return checked
    for name, entry in conditions.items():
        tolerance = entry.get("tolerance") if isinstance(entry, dict) else None
        value = tolerance.get("value") if isinstance(tolerance, dict) else None
        if isinstance(value, float) and value == 0.0 and math.copysign(1.0, value) < 0:
            reasons.add("request_incomplete", name)
    return checked


def no_slip(value: JsonObject, named: Iterable[str]) -> bool:
    return False


def no_plural(word: str, other: str) -> bool:
    return False


def no_record_slip(record: JsonObject) -> bool:
    return False


def no_section_slip(section: JsonObject, section_name: str) -> bool:
    return False


def anywhere(acceptance: JsonObject, reference: Reference | None) -> bool:
    return True


def first_nominal_of_each_field(
    request: JsonObject, field_name: str | None, reference: Reference | None, reasons: Reasons
) -> tuple[tuple[ImpliedCondition, ...], float | None, JsonObject | None]:
    given = request.get("acceptances")
    if isinstance(given, list):
        kept: list[JsonValue] = []
        named: set[str] = set()
        for acceptance in given:
            field_name_given = acceptance.get("field") if isinstance(acceptance, dict) else None
            if isinstance(acceptance, dict) and acceptance.get("acceptance") == "nominal":
                if isinstance(field_name_given, str) and field_name_given in named:
                    continue
                if isinstance(field_name_given, str):
                    named.add(field_name_given)
            kept.append(acceptance)
        request = {**request, "acceptances": kept}
    return _checked_acceptances(request, field_name, reference, reasons)


def any_field_on_the_pattern(value: JsonValue) -> str | None:
    return value if isinstance(value, str) and model.FIELD_PATTERN.fullmatch(value) else None


def never_unreadable(value: JsonValue | NotStrictJson) -> bool:
    return False


def first_copy_of_each_record(sources: Sequence[bytes]) -> list[Source]:
    kept: list[Source] = []
    seen: set[str] = set()
    for source in _sources_read(sources):
        value = source.value
        if isinstance(value, dict):
            identity = repr([value.get("id"), value.get("version"), value.get("content_hash")])
            if identity in seen:
                continue
            seen.add(identity)
        kept.append(source)
    return kept


def labelled_before_step_4(
    request: JsonValue | NotStrictJson, sources: Sequence[bytes], claims: frozenset[str]
) -> JsonObject:
    answer = _read_decided(request, sources, claims)
    labels = answer["labels"]
    if "hash" not in claims and isinstance(labels, list) and "hash_not_checked" not in labels:
        answer["labels"] = [*labels, "hash_not_checked"]
    return answer


def hash_never_recomputed(
    reference: Reference,
    sources: Sequence[Source],
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
) -> JsonObject | None:
    if "hash" in claims:
        return _resolve(reference, sources, claims - {"hash"}, reasons, [])
    return _resolve(reference, sources, claims, reasons, labels)


def never_broken(field_value: JsonObject) -> bool:
    return False


def alternatives_of_any_shape(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    """Step 7 over an `alternatives` whose shape the fault leaves unchecked: one that is not a list read as a
    list of its one entry."""
    alternatives = field_value["alternatives"]
    if not isinstance(alternatives, list):
        field_value = {**field_value, "alternatives": [alternatives]}
    return _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )


def want_mismatch_beside_no_pick(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    alternatives = field_value["alternatives"]
    given = model.GIVES.get(request.want, ())
    found = answer["reasons"]
    if "alternative_values" in answer and isinstance(alternatives, list) and isinstance(found, list):
        if any(isinstance(one, dict) and one.get("form") not in given for one in alternatives):
            answer["reasons"] = [*found, {"code": "want_mismatch"}]
            answer["status"] = "not_met"
    return answer


def conditions_kept_under_no_pick(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    entries = answer.get("alternative_values")
    if isinstance(entries, list) and isinstance(entries[0], dict):
        answer["conditions"] = entries[0]["conditions"]
    return answer


def alternatives_counted_from_one(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    entries = answer.get("alternative_values")
    for entry in entries if isinstance(entries, list) else []:
        index = entry.get("alternative") if isinstance(entry, dict) else None
        if isinstance(entry, dict) and isinstance(index, float):
            entry["alternative"] = index + 1
    return answer


def labels_raised_from_alternatives(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    entries, found = answer.get("alternative_values"), answer["labels"]
    if isinstance(entries, list) and isinstance(entries[0], dict) and isinstance(found, list):
        raised = entries[0]["labels"]
        answer["labels"] = [*found, *(raised if isinstance(raised, list) else [])]
    return answer


def nominal_ignored_over_alternatives(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    without = dataclasses.replace(request, nominal=None)
    return _read_alternatives(
        field_value, section, without, claims, reasons, labels, record_fault=record_fault
    )


def nominal_applied_to_every_alternative(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    applied = nominal if nominal is not None else request.nominal
    read = _read_value_field(
        field_value, section, request, claims, record_fault=record_fault, nominal=applied
    )
    # an interval's alone: a table an extrapolation covers holds an `assumption` too (S4d)
    if read.form == "interval" and "assumption" in read.members:
        read.stored = read.members["value"]
    return read


def alternatives_read(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
) -> list[FieldRead]:
    """Each alternative of a field whose `alternatives` keeps its shape read alone, as step 7 reads it."""
    alternatives = field_value["alternatives"]
    if model.alternatives_broken(field_value) or not isinstance(alternatives, list):
        return []
    return [
        _read_value_field(
            alternative, section, request, claims, record_fault=record_fault, nominal=request.nominal
        )
        for alternative in alternatives
    ]


def reasons_in(answer: JsonObject) -> Reasons:
    found: list[Reason] = []
    listed = answer["reasons"]
    for reason in listed if isinstance(listed, list) else []:
        assert isinstance(reason, dict)
        code, condition, index = reason["code"], reason.get("condition"), reason.get("alternative")
        assert isinstance(code, str)
        found.append(
            Reason(
                code,
                condition if isinstance(condition, str) else None,
                int(index) if isinstance(index, float) else None,
            )
        )
    return Reasons(found)


def with_reasons(answer: JsonObject, reasons: Reasons) -> JsonObject:
    answer["reasons"], answer["status"] = reasons.to_json(), reasons.status
    return answer


def rests_on_one_alternative(answer: JsonObject) -> bool:
    # read_side_contract.md:172 "a result that rests on no single alternative": of step 7's outcomes, only the
    # one left holds `conditions`
    return "conditions" in answer


def refused_alternative_set_aside(read: FieldRead) -> model.Fate:
    # at steps 8 and 9 alone: step 11's `at_edge` refuses by a rule of its own (S4d)
    fate = _fate_of(read)
    return "set_aside" if fate == "refuses" and read.ended_at in (8, 9) and not read.by_request else fate


def set_aside_alternative_refuses(read: FieldRead) -> model.Fate:
    # at step 10 alone: step 11's `outside_range` sets aside by a rule of its own (S4d)
    fate = _fate_of(read)
    return "refuses" if fate == "set_aside" and read.ended_at == 10 else fate


def request_fault_sets_aside(read: FieldRead) -> model.Fate:
    return "set_aside" if read.by_request else _fate_of(read)


def want_mismatch_sets_aside(read: FieldRead) -> model.Fate:
    fate = _fate_of(read)
    return "set_aside" if fate == "stays" and read.by_want.status == "not_met" else fate


def set_aside_reasons_dropped_where_refused(reads: Sequence[FieldRead]) -> Reasons:
    fates = [model.fate_of(one) for one in reads]
    if "refuses" not in fates:
        return _reasons_where_refused(reads)
    return Reasons(
        reason
        for index, one in enumerate(reads)
        if fates[index] != "set_aside"
        for reason in model.reasons_of_alternative(one, index)
    )


def waiting_reasons_dropped_where_refused(reads: Sequence[FieldRead]) -> Reasons:
    return Reasons(
        reason
        for index, one in enumerate(reads)
        for reason in model.reasons_of_alternative(one, index)
        if model.fate_of(one) != "stays" or model.REASONS[reason.code].status != "not_met"
    )


def labels_kept_where_refused(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    reads = alternatives_read(field_value, section, request, claims, record_fault=record_fault)
    fates = [model.fate_of(one) for one in reads]
    found = answer["labels"]
    if reads and ("refuses" in fates or "stays" not in fates) and isinstance(found, list):
        answer["labels"] = [*found, *(label for one in reads for label in one.labels)]
    return answer


def set_aside_reasons_beside_the_one_left(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    if not rests_on_one_alternative(answer):
        return answer
    reads = alternatives_read(field_value, section, request, claims, record_fault=record_fault)
    found = reasons_in(answer)
    found.extend(
        reason
        for index, one in enumerate(reads)
        if model.fate_of(one) == "set_aside"
        for reason in model.reasons_of_alternative(one, index)
    )
    return with_reasons(answer, found)


def one_left_reasons_without_their_alternative(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    if not rests_on_one_alternative(answer):
        return answer
    return with_reasons(answer, Reasons(Reason(found.code, found.condition) for found in reasons_in(answer)))


def nominal_not_applied_to_the_one_left(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    """The one left read as an interval under `want: value` with no nominal: `want_mismatch`, and no value."""
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    # a nominal's alone: the one left an extrapolation covers holds an `assumption` too (S4d)
    assumption = answer.get("assumption")
    if isinstance(assumption, dict) and assumption.get("acceptance") == "nominal":
        for name in ("value", "assumption", "unit", "specimen", "statistics", "provenance"):
            answer.pop(name, None)
    return answer


def not_met_reasons_beside_two_or_more(reads: Sequence[FieldRead], staying: Sequence[int]) -> Reasons:
    return Reasons(
        reason for index in staying for reason in model.reasons_of_alternative(reads[index], index)
    )


def unknown_reasons_dropped_beside_two_or_more(reads: Sequence[FieldRead], staying: Sequence[int]) -> Reasons:
    return Reasons()


def set_aside_reasons_beside_two_or_more(reads: Sequence[FieldRead], staying: Sequence[int]) -> Reasons:
    found = _reasons_beside_two_or_more(reads, staying)
    found.extend(
        reason
        for index, one in enumerate(reads)
        if model.fate_of(one) == "set_aside"
        for reason in model.reasons_of_alternative(one, index)
    )
    return found


def request_fault_given_an_alternative(read: FieldRead, index: int) -> Reasons:
    return Reasons(
        (*read.own.found_in(index), *read.by_request.found_in(index), *read.by_want.found_in(index))
    )


def index_among_those_that_stay(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    reads = alternatives_read(field_value, section, request, claims, record_fault=record_fault)
    staying = [index for index, one in enumerate(reads) if model.fate_of(one) == "stays"]
    rank = {float(index): float(position) for position, index in enumerate(staying)}
    for listed in (answer["reasons"], answer.get("alternative_values", [])):
        for item in listed if isinstance(listed, list) else []:
            index = item.get("alternative") if isinstance(item, dict) else None
            if isinstance(item, dict) and isinstance(index, float) and index in rank:
                item["alternative"] = rank[index]
    return answer


def unit_of_the_first_stored_alternative(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    alternatives = field_value["alternatives"]
    entries = answer.get("alternative_values")
    if isinstance(entries, list) and isinstance(alternatives, list):
        first = alternatives[0]
        assert isinstance(first, dict)
        for entry in entries:
            assert isinstance(entry, dict)
            entry["unit"] = model.unit_returned(first["unit"])
    return answer


def every_unknown_token_a_shape_fault(
    value: JsonValue, member: str, allowed: Iterable[str], faults: Reasons
) -> None:
    if not isinstance(value, str) or value not in tuple(allowed):
        faults.add("form_invalid")


def status_tokens_unchecked(
    value: JsonValue,
    faults: Reasons,
    *,
    allowed: frozenset[str],
    shape: tuple[str, ...] = (),
    named: tuple[str, ...] = (),
    scalar: bool = False,
    unit: bool = False,
) -> StatusObject | None:
    return _status_object(value, faults, allowed=allowed, shape=shape, named=named, scalar=scalar, unit=True)


def member_checked_off_its_row(
    field_value: JsonValue,
    section: JsonObject,
    field_name: str,
    claims: frozenset[str],
    *,
    record_fault: bool,
) -> tuple[Reasons, str | None]:
    faults, form = _check_value_field(field_value, section, field_name, claims, record_fault=record_fault)
    row = model.FIELDS[field_name]
    if isinstance(field_value, dict) and form in ("constant", "interval", "composition", "evidence"):
        if form not in row.forms:
            allowing = dataclasses.replace(row, forms=(*row.forms, form), bases=model.COMPOSITION_BASES)
            model.check_form_member(field_value, form, allowing, faults)
    return faults, form


def composition_checked_beyond_its_basis(value: JsonValue, row: FieldRow, faults: Reasons) -> None:
    _check_composition(value, row, faults)
    if isinstance(value, dict) and value.get("basis") in model.COMPOSITION_BASES:
        _check_composition(value, dataclasses.replace(row, bases=model.COMPOSITION_BASES), faults)


def family_suite_ignored(
    field_value: JsonValue,
    section: JsonObject,
    field_name: str,
    claims: frozenset[str],
    *,
    record_fault: bool,
) -> tuple[Reasons, str | None]:
    faults, form = _check_value_field(field_value, section, field_name, claims, record_fault=record_fault)
    return Reasons(reason for reason in faults if reason.code != "family_suite_absent"), form


def withheld_in_part(withheld_members: list[bool], faults: Reasons) -> bool:
    return len(withheld_members) == len(model.EVIDENCE_ENTRY_NAMES) - 1 and all(withheld_members)


def missing_label_refused(field_value: JsonObject, row: FieldRow, faults: Reasons) -> None:
    _check_label(field_value, row, faults)
    if "label" not in field_value:
        faults.add("form_invalid")


def unreadable_review_refused(provenance: JsonValue, faults: Reasons) -> None:
    _check_provenance(provenance, faults)
    if isinstance(provenance, dict):
        read = _review_read(provenance)
        if read == {"status": "not_checked"} and provenance.get("review") != read:
            faults.add("form_invalid")


def without_nulls(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return {name: without_nulls(member) for name, member in value.items() if member is not None}
    if isinstance(value, list):
        return [without_nulls(item) for item in value]
    return value


def nulls_read_as_absent(
    field_value: JsonValue,
    section: JsonObject,
    field_name: str,
    claims: frozenset[str],
    *,
    record_fault: bool,
) -> tuple[Reasons, str | None]:
    section_without = without_nulls(section)
    assert isinstance(section_without, dict)
    return _check_value_field(
        without_nulls(field_value), section_without, field_name, claims, record_fault=record_fault
    )


def field_read_without_nulls(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    """Steps 8 to 13 of a field whose `null` members the fault above reads as absent, read so at every step:
    a table's `source_range: null`, which step 8 then passes as absent, is absent at steps 10 and 11 too, so
    that the faulted model answers where it would index the `null`."""
    return _read_value_field(
        without_nulls(field_value), section, request, claims, record_fault=record_fault, nominal=nominal
    )


def section_specimen_unchecked(
    field_value: JsonValue,
    section: JsonObject,
    field_name: str,
    claims: frozenset[str],
    *,
    record_fault: bool,
) -> tuple[Reasons, str | None]:
    without = {name: member for name, member in section.items() if name != "specimen"}
    return _check_value_field(field_value, without, field_name, claims, record_fault=record_fault)


def block_unchecked(block: JsonValue, faults: Reasons, *, allowed: frozenset[str]) -> None:
    return None


def unchecked(value: JsonValue, faults: Reasons) -> None:
    return None


def population_level_checks_stop_at_a_missing_member(value: JsonValue, faults: Reasons) -> None:
    if isinstance(value, dict) and not all(name in value for name in model.POPULATION_LEVEL_NAMES):
        if model.status_object(value, faults, allowed=frozenset({"unstated"})) is None:
            faults.add("form_invalid")
        return
    _check_population_level(value, faults)


def dof_token_unchecked_under_student_t(value: JsonValue, faults: Reasons) -> None:
    dof = value.get("dof") if isinstance(value, dict) else None
    if isinstance(value, dict) and value.get("distribution") == "student_t" and isinstance(dof, dict):
        _check_uncertainty({**value, "dof": -1.0}, faults)
        return
    _check_uncertainty(value, faults)


def every_status_object_an_unstated_kind(entries: JsonValue, faults: Reasons) -> None:
    unstated: JsonValue = {"status": "unstated"}
    read_as: JsonValue = entries
    if isinstance(entries, list):
        each: list[JsonValue] = [
            {**entry, "stated_as": unstated}
            if isinstance(entry, dict) and isinstance(entry.get("stated_as"), dict)
            else entry
            for entry in entries
        ]
        read_as = each
    _check_plus_minus(read_as, faults)
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("stated_as"), dict):
            model.status_object(entry["stated_as"], faults, allowed=frozenset({"unstated"}), scalar=True)


def every_forms_member_named(form: str | None) -> tuple[str, ...]:
    return model.FIELD_PLACE_NAMES


def input_specimens_optional(entries: JsonValue, inputs: int, faults: Reasons) -> None:
    if entries is not None:
        _check_input_specimens(entries, inputs, faults)


def condition_unchecked(name: str, condition: JsonValue, faults: Reasons) -> None:
    return None


# Steps 9 and 10 index what step 8 holds a condition to. A condition the fault above leaves unchecked that
# they cannot index is read by them as one the record does not hold, so that the faulted model answers.


def unit_unreadable(name: str, condition: JsonValue) -> bool:
    """A numeric condition, not a status object, without the `unit` step 9 compares, or holding a `plus_minus`
    entry without one."""
    row = model.CONDITIONS.get(name)
    if row is None or row.shape != "numeric" or not isinstance(condition, dict) or "status" in condition:
        return False
    entries = condition.get("plus_minus", [])
    return "unit" not in condition or (
        isinstance(entries, list)
        and any(isinstance(entry, dict) and "unit" not in entry for entry in entries)
    )


def units_of_readable_conditions(field_value: JsonObject, section: JsonObject, field_name: str) -> Reasons:
    conditions = field_value["conditions"]
    assert isinstance(conditions, dict)
    readable = {
        name: condition for name, condition in conditions.items() if not unit_unreadable(name, condition)
    }
    return _check_units({**field_value, "conditions": readable}, section, field_name)


def comparable(condition: JsonObject) -> bool:
    """A stated value step 10 can compare with a tolerance: a `value` that is a number, or else a `range` of
    two numbers, and, where it holds a `bound` entry, the first one's `value` a number."""
    given = condition["value"] if "value" in condition else condition.get("range")
    ends = given if isinstance(given, list) else [given, given]
    entries = condition.get("plus_minus", [])
    bounds = [
        entry
        for entry in (entries if isinstance(entries, list) else [])
        if isinstance(entry, dict) and entry.get("stated_as") == "bound"
    ]
    return (
        len(ends) == 2
        and all(model.number(end) for end in ends)
        and (not bounds or model.number(bounds[0].get("value")))
    )


def entry_of_a_readable_condition(
    name: str,
    held: JsonObject,
    applied: Mapping[str, JsonObject],
    request: Request,
    reasons: Reasons,
    axis: model.TableAxis | None = None,
) -> JsonObject:
    condition = held.get(name)
    if name in held and (
        not isinstance(condition, dict)
        or ("status" not in condition and name in request.tolerances and not comparable(condition))
    ):
        held = {other: value for other, value in held.items() if other != name}
    return _condition_entry(name, held, applied, request, reasons, axis)


def case_folded(stored: JsonValue, registered: str | model.StatusUnit) -> bool:
    if isinstance(stored, str) and isinstance(registered, str):
        return stored.casefold() == registered.casefold()
    return _same_unit(stored, registered)


def broken_status_reports_its_token(
    value: JsonValue,
    faults: Reasons,
    *,
    allowed: frozenset[str],
    shape: tuple[str, ...] = (),
    named: tuple[str, ...] = (),
    scalar: bool = False,
    unit: bool = False,
) -> StatusObject | None:
    found = _status_object(value, faults, allowed=allowed, shape=shape, named=named, scalar=scalar, unit=unit)
    token = value.get("status") if isinstance(value, dict) else None
    if found is not None and found.token is None and not unit and isinstance(token, str):
        if token not in model.STATUS_TOKENS:
            faults.add("unknown_token")
    return found


def holds_no_other_kind(value: JsonObject, members: tuple[str, ...]) -> bool:
    return False


def entry_without_the_other_kind(
    name: str,
    held: JsonObject,
    applied: Mapping[str, JsonObject],
    request: Request,
    reasons: Reasons,
    axis: model.TableAxis | None = None,
) -> JsonObject:
    """A condition entry whose `record` leaves out the members of the other kind's shape, as members the
    reader does not know at that place."""
    entry = _condition_entry(name, held, applied, request, reasons, axis)
    record = entry.get("record")
    if isinstance(record, dict) and name in model.CONDITIONS and "status" not in record:
        other = ("token",) if model.CONDITIONS[name].shape == "numeric" else model.NUMERIC_CONDITION_ONLY
        entry["record"] = {member: value for member, value in record.items() if member not in other}
    return entry


def entry_provenance_unchecked(provenance: JsonValue, faults: Reasons) -> None:
    return None


def nested_reviews_as_found(provenance: JsonObject) -> JsonObject:
    returned = model.written_returned(provenance, [{"$ref": "#/$defs/provenance"}])
    assert isinstance(returned, dict)
    return {**returned, "review": model.review_read(provenance)}


def no_specimen_checked(field_value: JsonObject, section: JsonObject) -> list[JsonObject]:
    return []


def token_condition_units_accepted(field_value: JsonObject, section: JsonObject, field_name: str) -> Reasons:
    return Reasons(
        reason
        for reason in _check_units(field_value, section, field_name)
        if reason.condition is None or model.CONDITIONS[reason.condition].shape != "token"
    )


def plus_minus_units_unchecked(field_value: JsonObject, section: JsonObject, field_name: str) -> Reasons:
    conditions = field_value["conditions"]
    if isinstance(conditions, dict):
        stripped: JsonObject = {
            name: {member: given for member, given in condition.items() if member != "plus_minus"}
            if isinstance(condition, dict)
            else condition
            for name, condition in conditions.items()
        }
        field_value = {**field_value, "conditions": stripped}
    return _check_units(field_value, section, field_name)


def float_ends(value: JsonObject) -> tuple[float, float]:
    given = value["value"] if "value" in value else value["range"]
    low, high = given if isinstance(given, list) else (given, given)
    assert isinstance(low, float)
    assert isinstance(high, float)
    return low, high


def in_floating_point(stated: JsonObject, operating: JsonObject, tolerance: float) -> Status:
    low, high = float_ends(stated)
    operating_low, operating_high = float_ends(operating)
    if not (low - tolerance <= operating_low and operating_high <= high + tolerance):
        return "not_met"
    entries = stated.get("plus_minus", [])
    bounds = (
        [entry["value"] for entry in entries if isinstance(entry, dict) and entry.get("stated_as") == "bound"]
        if isinstance(entries, list)
        else []
    )
    if bounds and isinstance(bounds[0], float):
        u = bounds[0]
        return (
            "met"
            if low + u - tolerance <= operating_low and operating_high <= high - u + tolerance
            else "unknown"
        )
    return _within_tolerance(stated, operating, tolerance)


def strict_inequalities(stated: JsonObject, operating: JsonObject, tolerance: float) -> Status:
    low, high = model.ends(stated)
    operating_low, operating_high = model.ends(operating)
    t = Fraction(tolerance)
    if not (low - t < operating_low and operating_high < high + t):
        return "not_met"
    return _within_tolerance(stated, operating, tolerance)


def plus_minus_ignored(stated: JsonObject, operating: JsonObject, tolerance: float) -> Status:
    without = {name: given for name, given in stated.items() if name != "plus_minus"}
    return _within_tolerance(without, operating, tolerance)


def unchecked_read_as_met(
    name: str,
    held: JsonObject,
    applied: Mapping[str, JsonObject],
    request: Request,
    reasons: Reasons,
    axis: model.TableAxis | None = None,
) -> JsonObject:
    found = Reasons()
    entry = _condition_entry(name, held, applied, request, found, axis)
    if Reason("condition_unchecked", name) in set(found):
        entry["status"] = "met"
    else:
        reasons.extend(found)
    return entry


def operating_omitted(
    name: str,
    held: JsonObject,
    applied: Mapping[str, JsonObject],
    request: Request,
    reasons: Reasons,
    axis: model.TableAxis | None = None,
) -> JsonObject:
    entry = _condition_entry(name, held, applied, request, reasons, axis)
    entry.pop("operating", None)
    return entry


def fills_anything(condition: JsonValue) -> bool:
    return True


def compared_by_value(one: JsonObject, other: JsonObject) -> bool:
    return one.keys() == other.keys() and all(one[member] == other[member] for member in one)


def always_the_same(one: JsonObject, other: JsonObject) -> bool:
    return True


def registered_names_only(held: JsonObject, applied: Mapping[str, JsonObject], request: Request) -> list[str]:
    return [name for name in _conditions_checked(held, applied, request) if name in model.CONDITIONS]


def origin_unreported(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    read = _read_value_field(
        field_value, section, request, claims, record_fault=record_fault, nominal=nominal
    )
    read.own = Reasons(reason for reason in read.own if reason.code != "stated_without_origin")
    return read


def no_labels(field_value: JsonObject, provenance: JsonObject) -> list[str]:
    return []


def nominal_outside_supplies_the_value(
    read: FieldRead, field_value: JsonObject, request: Request, nominal: float | None, point: float | None
) -> None:
    _shape_by_want(read, field_value, request, nominal, point)
    if nominal is not None and Reason("nominal_invalid") in set(read.by_want):
        read.by_want = Reasons([Reason("want_mismatch")])
        read.members["value"] = nominal
        read.members["assumption"] = {"acceptance": "nominal", "value": nominal}


def best(statuses: Iterable[Status]) -> Status:
    found = list(statuses)
    return min(found, key=model.STATUSES_BEST_FIRST.index) if found else "met"


def table_read_ended_where_it_has_no_value(
    read: FieldRead, table: JsonObject, request: Request
) -> float | None:
    """Step 11 of a table under the fault above, which reads on past a `not_met` reason beside a better one:
    a read at an edge or outside the readable range, where the table has no value, ends at step 11 all the
    same, with the reasons step 11 gives, so that the faulted model answers where it would evaluate the table
    there; every other read as the model reads it."""
    axis = table["axis"]
    assert isinstance(axis, str)
    operating = request.operating.get(axis)
    point = operating.get("value") if operating is not None else None
    if not model.number(point) or (not model.at_an_edge(table, point) and model.inside(table, point)):
        return _read_the_table(read, table, request)
    if model.at_an_edge(table, point):
        read.own.add("at_edge", axis)
    if not model.inside(table, point):
        read.own.add("outside_range", axis)
    read.ended_at = 11
    return None


def value_whatever_the_status(status: Status, members: JsonObject) -> bool:
    return "value" in members


def members_read_past_a_refusal(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    """A field step 10 refuses read on to step 13 all the same, its reasons kept."""
    read = _read_value_field(
        field_value, section, request, claims, record_fault=record_fault, nominal=nominal
    )
    if read.conditions is not None and not read.members:
        unchecked = dataclasses.replace(request, tolerances={}, accepts={})
        read_on = _read_value_field(
            field_value, section, unchecked, claims, record_fault=record_fault, nominal=nominal
        )
        read.members, read.labels = read_on.members, read_on.labels
    return read


def every_member(value: JsonObject, names: Iterable[str]) -> JsonObject:
    return model.copied_object(value)


def review_result_alone(provenance: JsonObject) -> JsonObject:
    read = _review_read(provenance)
    return {"result": read["result"]} if "result" in read else read


def reviewed_with_a_status_objects_members(provenance: JsonObject) -> JsonObject:
    review = provenance.get("review")
    read = _review_read(provenance)
    if isinstance(review, dict) and "result" in read:
        return model.known_members(review, model.REVIEW_NAMES)
    return read


def both_shapes_read_as_the_status_object(provenance: JsonObject) -> JsonObject:
    review = provenance.get("review")
    if (
        isinstance(review, dict)
        and review.get("status") == "not_checked"
        and "result" in review
        and not model.slipped(review, model.REVIEW_NAMES)
    ):
        return model.status_returned(review)
    return _review_read(provenance)


def ies_not_a_plural(word: str, other: str) -> bool:
    ies = any(
        singular.endswith("y") and plural == singular[:-1] + "ies"
        for singular, plural in ((word, other), (other, word))
    )
    return not ies and _plural_of_either(word, other)


def donor_age_of_neither_accepted(name: str, fact: JsonValue, faults: Reasons) -> None:
    if name == "donor_age" and isinstance(fact, dict) and not {"status", "value", "range"} & fact.keys():
        fact = {**fact, "value": 0.0}
    _check_fact(name, fact, faults)


def unit_of_the_last_remaining_alternative(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    """Step 7 over alternatives, every `no_pick` entry's `unit` taken from the last remaining alternative, not
    each from its own."""
    returned = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    entries = returned.get("alternative_values")
    if isinstance(entries, list) and entries:
        alternatives = field_value["alternatives"]
        assert isinstance(alternatives, list)
        last = entries[-1]
        assert isinstance(last, dict)
        assert isinstance(last["alternative"], float)
        stored = alternatives[int(last["alternative"])]
        assert isinstance(stored, dict)
        for entry in entries:
            assert isinstance(entry, dict)
            entry["unit"] = model.unit_returned(stored["unit"])
    return returned


def registered_unit(unit: JsonValue) -> JsonValue:
    if isinstance(unit, dict):
        return {name: given for name, given in unit.items() if name == "status"}
    return _unit_returned(unit)


def field_facts_alone(section: JsonObject, field_value: JsonObject) -> JsonObject:
    specimen = field_value.get("specimen")
    return dict(specimen) if isinstance(specimen, dict) else {}


def shared(value: JsonValue) -> JsonValue:
    return value


NO_REQUIRED_WITH = {
    name: dataclasses.replace(row, required_with=()) for name, row in model.CONDITIONS.items()
}

# S3b-2's faults of a table's steps 10 to 13, each breaking one rule of the model's.


def edge_unseen_by_the_axis_entry(field_value: JsonObject, request: Request) -> model.TableAxis:
    """The axis entry `met` at an edge inside the readable range, as if the edge were none."""
    found = _table_axis(field_value, request)
    table = field_value["table"]
    assert isinstance(table, dict)
    operating = request.operating.get(found.name)
    point = operating.get("value") if operating is not None else None
    if model.number(point) and model.inside(table, point) and model.at_an_edge(table, point):
        return model.TableAxis(found.name, "met")
    return found


def outside_range_dropped_at_an_edge(read: FieldRead, table: JsonObject, request: Request) -> float | None:
    """At an edge outside the readable range, `at_edge` alone."""
    point = _read_the_table(read, table, request)
    codes = {reason.code for reason in read.own}
    if {"at_edge", "outside_range"} <= codes:
        read.own = Reasons(reason for reason in read.own if reason.code != "outside_range")
    return point


def without_source_range(table: JsonObject) -> JsonObject:
    return {name: member for name, member in table.items() if name != "source_range"}


def source_range_never_narrows_the_read(read: FieldRead, table: JsonObject, request: Request) -> float | None:
    """The table read at step 11 as if it held no `source_range`."""
    return _read_the_table(read, without_source_range(table), request)


def source_range_never_narrows_the_axis(field_value: JsonObject, request: Request) -> model.TableAxis:
    table = field_value["table"]
    assert isinstance(table, dict)
    return _table_axis({**field_value, "table": without_source_range(table)}, request)


def outside_range_beside_a_range(read: FieldRead, table: JsonObject, request: Request) -> float | None:
    """Over an operating range of the axis that leaves the readable range, `outside_range` beside
    `want_mismatch`."""
    point = _read_the_table(read, table, request)
    axis = table["axis"]
    assert isinstance(axis, str)
    operating = request.operating.get(axis)
    given = operating.get("range") if operating is not None else None
    if isinstance(given, list) and len(given) == 2 and model.number(given[0]) and model.number(given[1]):
        low, high = _readable_range(table)
        if given[0] < low or given[1] > high:
            read.own.add("outside_range", axis)
    return point


def step_11_reasons_without_the_axis(read: FieldRead, table: JsonObject, request: Request) -> float | None:
    point = _read_the_table(read, table, request)
    read.own = Reasons(
        Reason(reason.code) if reason.code in ("outside_range", "at_edge", "want_mismatch") else reason
        for reason in read.own
    )
    read.by_request = Reasons(Reason(reason.code) for reason in read.by_request)
    return point


def table_returned_whole(form: str, member: JsonValue) -> JsonValue:
    """A table returned with every member it holds, those the reader does not know among them."""
    return model.copied(member) if form == "table" else _form_member_returned(form, member)


def table_member_dropped(
    read: FieldRead, field_value: JsonObject, request: Request, nominal: float | None, point: float | None
) -> None:
    """A value read from a table returned without the table it is read from."""
    _shape_by_want(read, field_value, request, nominal, point)
    read.members.pop("table", None)


# S3c's: an extrapolation, at step 0 and at step 11.


def extrapolation_under_any_want(table: JsonObject, point: float, request: Request) -> bool:
    """An extrapolation applied under any `want`, as under `want: value`."""
    return _extrapolation_covers(table, point, dataclasses.replace(request, want="value"))


def extrapolation_at_an_edge(table: JsonObject, point: float, request: Request) -> bool:
    """An extrapolation applied at an edge outside the readable range, the edge's refusal not deciding."""
    if request.want == "value" and request.extrapolation is not None and model.at_an_edge(table, point):
        return not model.inside(table, point)
    return _extrapolation_covers(table, point, request)


def extrapolation_across_an_edge(table: JsonObject, point: float, request: Request) -> bool:
    """An extrapolation applied across an edge strictly between the read and the readable range's nearest
    end, an edge on that end alone looked at (where the table has no one-sided value to give, so the fault
    answers there as the text does)."""
    if request.want != "value" or request.extrapolation is None or model.at_an_edge(table, point):
        return False
    return not model.at_an_edge(table, model.nearest_end(table, point))


def end_value_of_x(read: FieldRead, table: JsonObject, request: Request) -> float | None:
    """Under an extrapolation, the end value `y[0]` or `y[-1]`, where `source_range` narrows the range or
    not: the value at `x`'s end, not the readable range's."""
    point = _read_the_table(read, table, request)
    if read.covered is None:
        return point
    axis = table["axis"]
    assert isinstance(axis, str)
    operating = request.operating[axis].get("value")
    assert model.number(operating)
    y = model.table_numbers(table, "y")
    return y[0] if operating < model.readable_range(table)[0] else y[-1]


def the_far_end(table: JsonObject, point: float) -> float:
    """The end value taken at the readable range's far end."""
    low, high = model.readable_range(table)
    return high if point < low else low


def extrapolated_read_ends_at_step_11(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    """A read an extrapolation covers given step 13's value but not step 12's reasons and labels."""
    read = _read_value_field(
        field_value, section, request, claims, record_fault=record_fault, nominal=nominal
    )
    if read.covered is not None:
        read.own = Reasons(reason for reason in read.own if reason.code != "stated_without_origin")
        read.labels = []
    return read


def extrapolation_located_anywhere(acceptance: JsonObject, reference: Reference | None) -> bool:
    """An extrapolation applied wherever it is located, or with no location."""
    return acceptance.get("acceptance") == "extrapolation" or _at_the_read(acceptance, reference)


def first_extrapolation_of_each_field(
    request: JsonObject, field_name: str | None, reference: Reference | None, reasons: Reasons
) -> tuple[tuple[ImpliedCondition, ...], float | None, JsonObject | None]:
    """Two extrapolations naming one field read as the first, the second dropped, not refused."""
    given = request.get("acceptances")
    if isinstance(given, list):
        kept: list[JsonValue] = []
        named: set[str] = set()
        for acceptance in given:
            field_name_given = acceptance.get("field") if isinstance(acceptance, dict) else None
            if isinstance(acceptance, dict) and acceptance.get("acceptance") == "extrapolation":
                if isinstance(field_name_given, str) and field_name_given in named:
                    continue
                if isinstance(field_name_given, str):
                    named.add(field_name_given)
            kept.append(acceptance)
        request = {**request, "acceptances": kept}
    return _checked_acceptances(request, field_name, reference, reasons)


def any_string_a_law(value: JsonValue) -> bool:
    """An empty `law` accepted."""
    return isinstance(value, str)


def white_space_no_law(value: JsonValue) -> bool:
    """A `law` of white space refused, read stripped."""
    return isinstance(value, str) and len(value.strip()) >= 1


class EveryMethod:
    """Every value a method: an extrapolation's `method` unchecked."""

    def __contains__(self, value: object) -> bool:
        return True


def assumption_with_its_basis(
    request: JsonObject, field_name: str | None, reference: Reference | None, reasons: Reasons
) -> tuple[tuple[ImpliedCondition, ...], float | None, JsonObject | None]:
    """An extrapolation's `assumption` holding its `basis` too."""
    implied, nominal, extrapolation = _checked_acceptances(request, field_name, reference, reasons)
    given = request.get("acceptances")
    if extrapolation is not None and isinstance(given, list):
        for acceptance in given:
            if isinstance(acceptance, dict) and acceptance.get("acceptance") == "extrapolation":
                if "basis" in acceptance:
                    extrapolation = {**extrapolation, "basis": acceptance["basis"]}
                break
    return implied, nominal, extrapolation


def covered_outside_range_dropped(read: FieldRead, table: JsonObject, request: Request) -> float | None:
    """A read an extrapolation covers without its `outside_range`, so `met` or `unknown`."""
    point = _read_the_table(read, table, request)
    if read.covered is not None:
        read.own = Reasons(reason for reason in read.own if reason.code != "outside_range")
    return point


# S4d's: step 7's rows for a table alternative whose read gives a reason at step 11, or that an extrapolation
# covers.


def step_11_codes(read: FieldRead) -> set[str]:
    """The codes of the reasons of a read that step 11 ended, none for another read."""
    return {reason.code for reason in read.own} if read.ended_at == 11 else set()


def outside_alone(read: FieldRead) -> bool:
    codes = step_11_codes(read)
    return "outside_range" in codes and "at_edge" not in codes


def outside_range_kept(read: FieldRead) -> model.Fate:
    """An alternative outside its form's range, off every edge, kept with no extrapolation to cover it."""
    return "stays" if outside_alone(read) else _fate_of(read)


def outside_range_read_for_an_entry(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    """Beside the fault above, a read step 11 ends outside the range given what an entry holds from its field,
    as a kept alternative's is, so that the faulted model answers under `no_pick`."""
    read = _read_value_field(
        field_value, section, request, claims, record_fault=record_fault, nominal=nominal
    )
    if outside_alone(read) and isinstance(field_value, dict):
        model.returned_from_the_field(read, field_value, model.merged_specimen(section, field_value))
    return read


def covered_set_aside(read: FieldRead) -> model.Fate:
    """An alternative an extrapolation the request carries covers set aside, as one outside its range is."""
    return "set_aside" if read.covered is not None else _fate_of(read)


def edge_inside_the_range_sets_aside(read: FieldRead) -> model.Fate:
    """An alternative read exactly at an edge inside its readable range set aside, not refusing the field."""
    codes = step_11_codes(read)
    return "set_aside" if "at_edge" in codes and "outside_range" not in codes else _fate_of(read)


def edge_outside_the_range_sets_aside(read: FieldRead) -> model.Fate:
    """An alternative read exactly at an edge outside its readable range, `outside_range` beside `at_edge`,
    set aside, as one outside the range is."""
    return "set_aside" if {"at_edge", "outside_range"} <= step_11_codes(read) else _fate_of(read)


def set_aside_read_on_to_step_11(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    """A table whose conditions give `not_met` at step 10 read on to step 11 all the same, where the request
    gives no operating value for its axis: `request_incomplete`, which refuses the field."""
    read = _read_value_field(
        field_value, section, request, claims, record_fault=record_fault, nominal=nominal
    )
    if read.ended_at == 10 and not read.by_request and read.form == "table" and isinstance(field_value, dict):
        table = field_value["table"]
        assert isinstance(table, dict)
        axis = table["axis"]
        assert isinstance(axis, str)
        if axis not in request.operating:
            read.by_request.add("request_incomplete", axis)
    return read


def over_a_range_set_aside(read: FieldRead) -> model.Fate:
    """A table read over an operating range of its axis set aside, not kept."""
    return "set_aside" if read.over_a_range else _fate_of(read)


def over_a_range_given_by_want(read: FieldRead, request: Request) -> bool:
    """A table read over an operating range of its axis counted as a form `want` gives, as a table is."""
    if read.over_a_range:
        return read.form in model.GIVES.get(request.want, ())
    return _form_want_gives(read, request)


def over_a_range_entry_unlabelled(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    """A table read over an operating range of its axis given no labels for its entry, as its read, which
    step 11 ends, gives none."""
    read = _read_value_field(
        field_value, section, request, claims, record_fault=record_fault, nominal=nominal
    )
    if read.over_a_range:
        read.entry_labels = []
    return read


def over_a_range_entry_bare(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    """A table read over an operating range of its axis returning no member for its entry beside the table:
    no `unit`, `specimen`, `statistics` or `provenance`, as its read, which step 11 ends, returns none."""
    read = _read_value_field(
        field_value, section, request, claims, record_fault=record_fault, nominal=nominal
    )
    if read.over_a_range:
        read.members = {}
    return read


def kept_entries_extrapolated(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    """Under `no_pick`, the entry of an alternative an extrapolation covers holding the end value and the
    `assumption`: the extrapolation applied, though that alternative is not the one left."""
    answer = _read_alternatives(
        field_value, section, request, claims, reasons, labels, record_fault=record_fault
    )
    entries = answer.get("alternative_values")
    if isinstance(entries, list):
        reads = alternatives_read(field_value, section, request, claims, record_fault=record_fault)
        for entry in entries:
            assert isinstance(entry, dict)
            index = entry["alternative"]
            assert isinstance(index, float)
            one = reads[int(index)]
            if one.covered is not None:
                entry["value"], entry["assumption"] = one.members["value"], one.covered
    return answer


def kept_reads_ending_at_step_11(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    """Step 7 reading an alternative an extrapolation covers no further than step 11: no reason or label of
    step 12, and no value of step 13."""

    def read_to_step_11(
        field_value: JsonValue,
        section: JsonObject,
        request: Request,
        claims: frozenset[str],
        *,
        record_fault: bool,
        nominal: float | None,
    ) -> FieldRead:
        read = _read_value_field(
            field_value, section, request, claims, record_fault=record_fault, nominal=nominal
        )
        if read.covered is not None:
            read.own = Reasons(reason for reason in read.own if reason.code != "stated_without_origin")
            read.labels = []
            read.members = {
                name: member
                for name, member in read.members.items()
                if name not in ("value", "table", "assumption")
            }
        return read

    with mock.patch.object(model, "read_value_field", read_to_step_11):
        return _read_alternatives(
            field_value, section, request, claims, reasons, labels, record_fault=record_fault
        )


def kept_under_any_want(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    """Step 7 keeping an alternative outside its range that the request's extrapolation would cover under
    `want: value`, whatever the `want`: an extrapolation that would cover it were it applied."""

    def covers_as_under_value(table: JsonObject, point: float, given: Request) -> bool:
        return _extrapolation_covers(table, point, dataclasses.replace(given, want="value"))

    with mock.patch.object(model, "extrapolation_covers", covers_as_under_value):
        return _read_alternatives(
            field_value, section, request, claims, reasons, labels, record_fault=record_fault
        )


MUTANTS: Mapping[str, Mutant] = {
    # Step 0
    "want_outside_section_6": Mutant(
        "a `want` that is none of section 6's tokens is read",
        'read_side_contract.md:35 "its `want` is not one of section 6"',
        {"WANTS": EveryString()},
    ),
    "fits_wants_without_their_suite": Mutant(
        "`fit`, `coverage` and `reference_data` read by a reader without their suite",
        'read_side_contract.md:49-51 "whose `want` belongs to a suite the reader does not claim is '
        'refused at the same step"',
        {"FITS_AND_REFERENCE_DATA_WANTS": ()},
    ),
    "tolerance_without_an_operating_condition": Mutant(
        "a tolerance with no operating condition accepted",
        'read_side_contract.md:43 "it gives a tolerance for a condition with no operating condition"',
        {
            "checked_requirement": operating_for_every_tolerance,
            "condition_entry": unchecked_without_an_operating_condition,
        },
    ),
    "request_units_not_compared": Mutant(
        "an operating condition's, a tolerance's or an implied value's unit not compared",
        'read_side_contract.md:51-55 "where an operating condition or tolerance of a registered numeric '
        'condition has a string `unit`"',
        {"request_unit_differs": no_request_unit_compared},
    ),
    "negative_zero_tolerance_refused": Mutant(
        "a tolerance of `-0` read as below zero",
        'read_side_contract.md:43 "a tolerance below zero (`-0` is not)"',
        {"checked_requirement": negative_zero_tolerance_refused},
    ),
    "declaration_members_in_a_requirement_read": Mutant(
        "a requirement holding `label`, `represents`, `population_level` or `review` read",
        'read_side_contract.md:37-39 "its `requirement` holds `label`, `represents`"',
        {"DECLARATION_ONLY_REQUIREMENT_NAMES": ()},
    ),
    "acceptances_applied_anywhere": Mutant(
        "an acceptance applied at another record, a region, an interval or no location",
        'read_side_contract.md:89-96 "only at the read\'s own location"',
        {"at_the_read": anywhere},
    ),
    "two_nominals_for_one_field": Mutant(
        "two nominals naming one field read as the first",
        'read_side_contract.md:71-72 "So do two acceptances of one kind, `nominal`, `extrapolation`, `pick` '
        'or `trainable`, that name one field"',
        {"checked_acceptances": first_nominal_of_each_field},
    ),
    "unregistered_field_requested": Mutant(
        "a field the reader's version does not register read, and found absent",
        'read_side_contract.md:33-34 "its field is not registered"',
        {"registered_field": any_field_on_the_pattern},
    ),
    # The slip rule, in a request and a record
    "every_slip_ignored": Mutant(
        "a member one slip from a named one ignored, in a request and in a record",
        'record_format.md:588-593 "refuses a member it does not know, where items 1 and 4 would ignore or '
        'skip it, that is one slip (below)", read_side_contract.md:40-41 "a member one slip '
        "(`record_format.md` section 10) from a member this section or `declarations.md` names at that "
        'place"',
        {"slipped": no_slip},
    ),
    "plurals_not_slips": Mutant(
        "a word made plural or singular not one slip",
        'record_format.md:602-604 "making one of its `_`-separated words plural or singular"',
        {"_plural_of_either": no_plural},
        survives="each plural slip in the cases adds an `s` (`fluids`), and so is one character inserted",
    ),
    "envelope_body_and_section_slips_ignored": Mutant(
        "a slip in the envelope, the body or a section refuses no field",
        'record_format.md:590-592 "in the envelope or the body, the names in `sections` included, each '
        'field read from that record"',
        {"record_slips": no_record_slip, "section_slips": no_section_slip},
    ),
    # Steps 1 to 5
    "unreadable_sources_ignored": Mutant(
        "an unreadable source never turns `absent` or `pin_mismatch` into `malformed`",
        'read_side_contract.md:208-217 "unless a supplied source is unreadable: then it gives `malformed`"',
        {"unreadable": never_unreadable},
    ),
    "first_of_differing_copies_read": Mutant(
        "of two copies with the pin whose bytes differ, the first read",
        'read_side_contract.md:212-213 "with two or more whose bytes differ, the read gives `malformed`"',
        {"sources_read": first_copy_of_each_record},
    ),
    "hash_not_checked_before_step_4": Mutant(
        "`hash_not_checked` on a result that ends before step 4",
        'read_side_contract.md:227-228 "a result that ends before it carries no such label"',
        {"read_decided": labelled_before_step_4},
    ),
    "hash_never_recomputed": Mutant(
        "a reader claiming HS never recomputes the hash",
        'read_side_contract.md:224-226 "also recomputes the hash"',
        {"resolve": hash_never_recomputed},
    ),
    "other_minor_versions_read": Mutant(
        "a record of another `MAJOR.MINOR` read",
        'read_side_contract.md:220-221 "another `MAJOR.MINOR` (before 1.0.0) gives `other_version`"',
        {"READER_MAJOR_MINOR": EveryPair()},
    ),
    # Step 7
    "alternatives_shape_unchecked": Mutant(
        "an `alternatives` that is empty, not a list or beside a value field's members read",
        'record_format.md:342-346 "`alternatives` is a non-empty list"',
        {"alternatives_broken": never_broken, "read_alternatives": alternatives_of_any_shape},
    ),
    "want_mismatch_beside_no_pick": Mutant(
        "`want_mismatch` reported under `no_pick` for an alternative whose form `want` cannot give",
        'read_side_contract.md:299-300 "under `no_pick` no `want_mismatch` is reported"',
        {"read_alternatives": want_mismatch_beside_no_pick},
    ),
    "conditions_kept_under_no_pick": Mutant(
        "a `no_pick` result holding `conditions` of its own",
        'read_side_contract.md:179-180 "Under `no_pick` the result holds none of `unit`, `conditions`, '
        '`specimen`, `statistics` and `provenance`"',
        {"read_alternatives": conditions_kept_under_no_pick},
    ),
    "alternatives_counted_from_one": Mutant(
        "an `alternative_values` entry's index counted from one",
        'read_side_contract.md:126 "`alternative` is its index among the stored alternatives of the field '
        'read" and "counts from 0, in stored order"',
        {"read_alternatives": alternatives_counted_from_one},
    ),
    "labels_raised_from_an_alternative": Mutant(
        "an alternative's labels on the `no_pick` result's own",
        "read_side_contract.md:132 \"each alternative's other labels sitting, under `no_pick`, in its "
        '`alternative_values` entry"',
        {"read_alternatives": labels_raised_from_alternatives},
    ),
    "nominal_ignored_over_alternatives": Mutant(
        "an interval beside other alternatives not counted as a form `want: value` gives under a nominal",
        'read_side_contract.md:292-293 "An interval counts as one `want: value` can give where a nominal '
        'the request carries applies"',
        {"read_alternatives": nominal_ignored_over_alternatives},
    ),
    "nominal_applied_under_no_pick": Mutant(
        "a nominal applied to an interval alternative under `no_pick`",
        'read_side_contract.md:545-546 "Under `no_pick` no nominal is applied"',
        {"read_value_field": nominal_applied_to_every_alternative},
    ),
    # Step 7 with no pick (S4a)
    "refused_alternative_set_aside": Mutant(
        "an alternative refused at step 8 or 9 set aside, not refusing the field",
        'read_side_contract.md:274 "Every other `not_met` in an alternative"',
        {"fate_of": refused_alternative_set_aside},
    ),
    "set_aside_alternative_refuses": Mutant(
        "an alternative whose conditions give `not_met` at step 10 refusing the field, not set aside",
        'read_side_contract.md:262-263 "An alternative is set aside where its conditions"',
        {"fate_of": set_aside_alternative_refuses},
    ),
    "request_fault_sets_aside": Mutant(
        "an alternative whose read a fault of the request ends set aside, not refusing the field",
        'read_side_contract.md:276-277 "fault of the request (section 1): an alternative whose read '
        'reaches step 11 with no operating value for"',
        {"fate_of": request_fault_sets_aside},
    ),
    "want_mismatch_sets_aside": Mutant(
        "an alternative whose form `want` cannot give set aside, not kept",
        'read_side_contract.md:268-271 "whose form `want` cannot give"',
        {"fate_of": want_mismatch_sets_aside},
    ),
    "set_aside_reasons_dropped_where_refused": Mutant(
        "the set-aside alternatives' reasons dropped where another refuses the field",
        'read_side_contract.md:286-287 "where an alternative refuses the field, or every alternative is '
        'set aside, `not_met`"',
        {"reasons_where_refused": set_aside_reasons_dropped_where_refused},
    ),
    "waiting_reasons_dropped_where_refused": Mutant(
        "the `not_met` reasons of an alternative that stays dropped where the field is refused",
        'read_side_contract.md:281-283 "These wait: they are reported once a pick names that alternative"',
        {"reasons_where_refused": waiting_reasons_dropped_where_refused},
    ),
    "labels_kept_where_refused": Mutant(
        "the alternatives' labels on the result where the field is refused or every alternative set aside",
        'read_side_contract.md:302-304 "holds no `value`, `assumption` or `conditions`"',
        {"read_alternatives": labels_kept_where_refused},
    ),
    "set_aside_reasons_beside_the_one_left": Mutant(
        "the set-aside alternatives' reasons reported beside the one left",
        'read_side_contract.md:288-289 "not reported, since they would refuse a sound value"',
        {"read_alternatives": set_aside_reasons_beside_the_one_left},
    ),
    "one_left_reasons_without_their_alternative": Mutant(
        "the one left's reasons without their `alternative`",
        'read_side_contract.md:147-148 "This holds for a picked alternative and for the one left"',
        {"read_alternatives": one_left_reasons_without_their_alternative},
    ),
    "nominal_not_applied_to_the_one_left": Mutant(
        "a nominal not applied to the interval left, which gives no value",
        'read_side_contract.md:288 "where one alternative stays", '
        "read_side_contract.md:544 \"A nominal applies only under `want: value`, inside or on the interval's "
        'bounds"',
        {"read_alternatives": nominal_not_applied_to_the_one_left},
    ),
    "not_met_reasons_beside_no_pick": Mutant(
        "the `not_met` reasons of the alternatives that stay reported beside `no_pick` or `want_mismatch`",
        'read_side_contract.md:299-300 "`not_met` reasons wait"',
        {"reasons_beside_two_or_more": not_met_reasons_beside_two_or_more},
    ),
    "unknown_reasons_dropped_beside_no_pick": Mutant(
        "the `unknown` reasons of the alternatives that stay dropped beside `no_pick` or `want_mismatch`",
        'read_side_contract.md:299 "`unknown` reasons stand beside `want_mismatch` or `no_pick`"',
        {"reasons_beside_two_or_more": unknown_reasons_dropped_beside_two_or_more},
    ),
    "set_aside_reasons_beside_no_pick": Mutant(
        "the set-aside alternatives' reasons reported beside `no_pick` or `want_mismatch`",
        'read_side_contract.md:300-301 "are not reported there"',
        {"reasons_beside_two_or_more": set_aside_reasons_beside_two_or_more},
    ),
    "request_fault_given_an_alternative": Mutant(
        "a fault of the request found reading one alternative given that `alternative`",
        'read_side_contract.md:150 "A fault of the request carries none, even one found in an alternative '
        '(section 1)"',
        {"reasons_of_alternative": request_fault_given_an_alternative},
    ),
    "index_among_those_that_stay": Mutant(
        "an alternative's index counted among the alternatives that stay, in its reasons and its entry",
        'read_side_contract.md:149-150 "index among the stored alternatives of the field read"',
        {"read_alternatives": index_among_those_that_stay},
    ),
    "unit_of_the_first_stored_alternative": Mutant(
        "under `no_pick`, every entry's `unit` the first stored alternative's, set aside or not",
        'read_side_contract.md:127 "Under `no_pick` the result holds none: each `alternative_values` '
        'entry holds its own"',
        {"read_alternatives": unit_of_the_first_stored_alternative},
    ),
    # Step 8
    "unknown_tokens_read_as_shape_faults": Mutant(
        "a token the reader knows for no member of that name gives `form_invalid`",
        'read_side_contract.md:309-311 "a token the reader knows for no member of that name '
        '(`unknown_token`)"',
        {"known_token": every_unknown_token_a_shape_fault},
    ),
    "status_tokens_unchecked": Mutant(
        "a status object takes any token, in any member",
        'provenance.md:50-51 "A status token its row does not allow refuses the field as `form_invalid`"',
        {"status_object": status_tokens_unchecked},
    ),
    "member_checked_off_its_row": Mutant(
        "the member of a form the row does not allow checked as on a row allowing it",
        'read_side_contract.md:313-315 "does not allow is refused, `form_not_registered`"',
        {"check_value_field": member_checked_off_its_row},
    ),
    "composition_checked_beyond_its_basis": Mutant(
        "a composition whose basis the row does not allow checked further",
        "maintainer, 2026-10-15 (OPEN_POINTS: form_not_allowed_by_its_row)",
        {"check_composition": composition_checked_beyond_its_basis},
        survives="each composition whose basis its row does not allow is otherwise well formed in the cases",
    ),
    "family_suite_ignored": Mutant(
        "a parameter set read without the family evaluation suite not `family_suite_absent`",
        'read_side_contract.md:344-345 "read without the family evaluation suite is refused here '
        '(`family_suite_absent`)"',
        {"check_value_field": family_suite_ignored},
    ),
    "entry_withheld_in_part_read": Mutant(
        "an evidence entry withheld in some members but not every one read",
        'record_format.md:249-251 "one holding `withheld` in some of those members and not in every one '
        'breaks its shape (`form_invalid`)"',
        {"withheld_whole": withheld_in_part},
    ),
    "missing_label_refused": Mutant(
        "a field without its row's label refused",
        'record_format.md:197-198 "missing label is not refused at read"',
        {"check_label": missing_label_refused},
    ),
    "unreadable_review_refuses": Mutant(
        "a review the reader cannot read refuses the field",
        'provenance.md:120-126 "`review` never refuses the field"',
        {"check_provenance": unreadable_review_refused},
    ),
    "null_read_as_absent": Mutant(
        "`null` in a member step 8 checks read as the member absent",
        'record_format.md:47-50 "where `null` stands in a member step 8 checks"',
        {"check_value_field": nulls_read_as_absent, "read_value_field": field_read_without_nulls},
    ),
    "statistics_unchecked": Mutant(
        "a statistics block not checked",
        'read_side_contract.md:317 "the statistics block and its uncertainties"',
        {"check_block": block_unchecked},
    ),
    "uncertainties_unchecked": Mutant(
        "a relative or expanded uncertainty not checked",
        'uncertainty.md:44-51 "In a relative or expanded uncertainty:"',
        {"check_uncertainty": unchecked},
    ),
    "derivation_unchecked": Mutant(
        "a derived value's derivation not checked",
        'provenance.md:201-205 "A derived value carries the '
        "specimen facts of each input in "
        '`derivation.input_specimens`"',
        {"check_derivation": unchecked},
    ),
    "population_level_checks_stop_at_a_missing_member": Mutant(
        "a population level missing a member has its `level` and `within` left unchecked",
        'read_side_contract.md:138-139 "Each step makes all its checks before the read stops", '
        'uncertainty.md:37 "present exactly where `represents` is `population`"',
        {"check_population_level": population_level_checks_stop_at_a_missing_member},
        survives="no case holds a population level missing a member beside a token of its own",
    ),
    "dof_token_unchecked_under_student_t": Mutant(
        "a `dof` held as a status object under a Student's t distribution has its token left unchecked",
        'read_side_contract.md:138-139 "Each step makes all its checks before the read stops", '
        'provenance.md:50-51 "and one the reader does not know as `unknown_token`" and uncertainty.md:48-49 '
        '"a number where `distribution` is `student_t`"',
        {"check_uncertainty": dof_token_unchecked_under_student_t},
        survives="no case holds a `dof` status object of an unknown token under a Student's t distribution",
    ),
    "every_status_object_an_unstated_kind": Mutant(
        "a `plus_minus` entry whose `stated_as` holds any status object counted as of unstated kind",
        'provenance.md:265-266 "or `{"status": "unstated"}` (a ± whose kind the source does not state)"',
        {"check_plus_minus": every_status_object_an_unstated_kind},
        survives="no case holds a `stated_as` of another status token beside an entry of a stated kind",
    ),
    "every_forms_member_named_at_a_field": Mutant(
        "every form's member named at a field's place, so that a slip of another form's refuses a constant",
        'record_format.md:330 "`value` for a constant; otherwise the member named like the form"',
        {"named_at_a_field": every_forms_member_named},
        survives="no case holds a slip of another form's member beside a form the reader knows",
    ),
    "input_specimens_optional": Mutant(
        "a derivation without `input_specimens` read",
        'provenance.md:201 "carries the specimen facts of each input in `derivation.input_specimens`"',
        {"check_input_specimens": input_specimens_optional},
        survives="every derivation in the cases holds `input_specimens`",
    ),
    "section_specimen_unchecked": Mutant(
        "a section's `specimen` not checked for a field read from it",
        'read_side_contract.md:305-306 "form or section `specimen` that breaks its shape"',
        {"check_value_field": section_specimen_unchecked},
    ),
    "condition_shapes_unchecked": Mutant(
        "a condition of a name the reader knows not checked",
        'read_side_contract.md:316-317 "each condition and specimen fact whose name the reader knows"',
        {
            "check_condition": condition_unchecked,
            "check_units": units_of_readable_conditions,
            "condition_entry": entry_of_a_readable_condition,
        },
    ),
    "broken_status_object_reports_its_token": Mutant(
        "a status object that breaks its shape gives its token's `unknown_token` beside `form_invalid`",
        'provenance.md:51-53 "A status object that breaks its shape is read for nothing else, so its '
        'token gives no reason of its own"',
        {"status_object": broken_status_reports_its_token},
    ),
    # The points the text left open (`OPEN_POINTS` until the maintainer ruled each). The first two break the
    # implied half too, which the maintainer's token ruling settled (2026-10-18), and the record half, ruled
    # with `provenance.md` section 6.1 item 1 (2026-10-19): the cases of both rulings kill both.
    "members_of_the_other_kind_read": Mutant(
        "a numeric condition holding `token`, or a token condition holding `value`, read",
        'provenance.md:246-249 "A numeric condition holding `token`, or a token condition holding '
        '`value`, `range`, `plus_minus` or `set_or_measured`, breaks its shape (`form_invalid`)", in a '
        "record (the maintainer's ruling, 2026-10-19); read_side_contract.md:83-84 \"where `implies` "
        'gives a numeric condition a `token`, or a token condition a `value`, `range` or `unit`", implied',
        {"holds_another_kind": holds_no_other_kind},
    ),
    "members_of_the_other_kind_ignored": Mutant(
        "a numeric condition's `token`, or a token condition's `value`, ignored as a member the reader does "
        "not know: not refused, and not returned",
        'provenance.md:246-249 "A numeric condition holding `token`, or a token condition holding '
        '`value`, `range`, `plus_minus` or `set_or_measured`, breaks its shape (`form_invalid`)", in a '
        "record (the maintainer's ruling, 2026-10-19); read_side_contract.md:83-84 \"where `implies` "
        'gives a numeric condition a `token`, or a token condition a `value`, `range` or `unit`", implied',
        {"holds_another_kind": holds_no_other_kind, "condition_entry": entry_without_the_other_kind},
    ),
    "slips_of_alternatives_ignored": Mutant(
        "a member one slip from `alternatives` beside a value field's members ignored",
        'record_format.md:324 "A value field is an object with these members, or an `alternatives` object '
        '(below)" (the maintainer\'s ruling, 2026-10-19), record_format.md:588 "refuses a member it does not '
        'know, where items 1 and 4 would ignore or skip it, that is one slip (below)"',
        {"FIELD_PLACE_NAMES": model.VALUE_FIELD_NAMES},
    ),
    "evidence_entry_provenance_unchecked": Mutant(
        "an evidence entry's `provenance` not checked",
        'record_format.md:255 "Step 8 checks an entry" (the maintainer\'s ruling, 2026-10-19)',
        {"check_entry_provenance": entry_provenance_unchecked},
    ),
    "nested_reviews_returned_as_found": Mutant(
        "a review inside a provenance an evidence entry's `per_parameter` maps a parameter to returned as "
        "found, and none where that provenance holds none",
        'record_format.md:256-258 "at any depth (one that `per_parameter` maps a parameter to, say), '
        "returns its `review` as that item reads every review\" (the maintainer's ruling, 2026-10-20)",
        {"entry_provenance_returned": nested_reviews_as_found},
    ),
    # Not an open point since the fix round: the text names the three (S2a-4's review, approved by the
    # maintainer on 2026-10-18 and confirmed on 2026-10-19), and no case holds a slip of one.
    "declaration_names_not_named_in_a_request": Mutant(
        "a slip of a requirement's `field`, or of its conditions' `reason` or `consequence`, ignored",
        'read_side_contract.md:40-41 "a member one slip (`record_format.md` section 10) from a member '
        'this section or", declarations.md:64 "per field: `want` (`read_side_contract.md` section 6), '
        'required" and "each with its `reason` and, where known, its `consequence`" (the text names them in '
        "a requirement)",
        {
            "REQUIREMENT_NAMES": model.REQUIREMENT_NAMES[:-1],
            "REQUIREMENT_CONDITION_NAMES": model.REQUIREMENT_CONDITION_NAMES[:2],
        },
        survives="no case holds a slip of `field`, `reason` or `consequence` in a requirement",
    ),
    # Step 9
    "units_compared_after_case_folding": Mutant(
        "a record's units compared after case folding",
        'record_format.md:226-228 "Units are compared as '
        "strings, after JSON escapes are decoded, code "
        'point for code point"',
        {"same_unit": case_folded},
    ),
    "fact_units_unchecked": Mutant(
        "a specimen fact's unit not compared with the one its row fixes",
        'read_side_contract.md:353-356 "is compared in the same way with the unit its row fixes"',
        {"checked_specimens": no_specimen_checked},
    ),
    "token_condition_unit_accepted": Mutant(
        "a `unit` on a token condition passes step 9",
        'read_side_contract.md:349-350 "a `unit` on a token condition, which registers none"',
        {"check_units": token_condition_units_accepted},
    ),
    "plus_minus_units_unchecked": Mutant(
        "a `plus_minus` entry's unit not compared",
        'read_side_contract.md:349 "`plus_minus` units included"',
        {"check_units": plus_minus_units_unchecked},
    ),
    # Step 10
    "floating_point_as_written": Mutant(
        "section 5's tests computed in floating point as written",
        'read_side_contract.md:488-491 "Computed in floating point as written, it could pass a value just '
        'outside the tolerance"',
        {"within_tolerance": in_floating_point},
    ),
    "strict_inequalities": Mutant(
        "`<` for `<=` in section 5's table",
        'read_side_contract.md:479-482 "`met` when `abs(r - v) <= t`, else `not_met` (`condition_outside`)"',
        {"within_tolerance": strict_inequalities},
    ),
    "plus_minus_ignored": Mutant(
        "a stated plus or minus ignored",
        'read_side_contract.md:496-507 "For a numeric condition holding `plus_minus`"',
        {"within_tolerance": plus_minus_ignored},
    ),
    "unchecked_read_as_met": Mutant(
        "a stated condition the request gives no tolerance or accept list for read as `met`",
        'read_side_contract.md:478 "no tolerance and no accept list for it"',
        {"condition_entry": unchecked_read_as_met},
    ),
    "operating_omitted_from_entries": Mutant(
        "a condition entry without the request's operating condition",
        'read_side_contract.md:174-175 "its `operating` is the request"',
        {"condition_entry": operating_omitted},
    ),
    "implied_fills_any_condition": Mutant(
        "an implied condition fills a stated condition, or one held as another status object",
        'declarations.md:386-388 "An implied condition never overrides a stated condition"',
        {"unstated_or_absent": fills_anything},
    ),
    "disagreeing_implied_conditions_read": Mutant(
        "two implied conditions that disagree read as the first",
        'read_side_contract.md:108-113 "two implied conditions that both apply to the field"',
        {"same_supplied_value": always_the_same},
    ),
    "implied_values_compared_by_value": Mutant(
        "two implied values compared as numbers, so that `0` and `-0` agree",
        'read_side_contract.md:110-112 "hold the same token or the same numbers bit for bit"',
        {"same_supplied_value": compared_by_value},
    ),
    "required_with_ignored": Mutant(
        "a condition another condition requires with its token not checked",
        'read_side_contract.md:468 "condition requires with the token it holds"',
        {"CONDITIONS": NO_REQUIRED_WITH},
    ),
    "unknown_condition_names_ignored": Mutant(
        "a condition name the reader does not know gives no entry and no reason",
        'read_side_contract.md:477 "a name the reader does not know"',
        {"conditions_checked": registered_names_only},
    ),
    # Step 12
    "stated_without_origin_unreported": Mutant(
        "a value stated without origin not `unknown`",
        'read_side_contract.md:363 "Give `unknown` for a value stated without origin '
        '(`stated_without_origin`)"',
        {"read_value_field": origin_unreported},
    ),
    "step_12_labels_dropped": Mutant(
        "the field's label and `mixed_conditions` not added",
        'read_side_contract.md:364-365 "add the labels of section 2"',
        {"step_12_labels": no_labels},
    ),
    # Step 13
    "bounds_given_by_a_constant": Mutant(
        "`want: bounds` gives a constant's value",
        'read_side_contract.md:531 "`bounds` | `not_met` (`want_mismatch`)"',
        {"GIVES": {**model.GIVES, "bounds": ("interval", "constant")}},
    ),
    "value_given_by_an_interval": Mutant(
        "`want: value` gives an interval's bounds without a nominal",
        'read_side_contract.md:530 "a declared nominal inside or on the bounds supplies `value` and '
        '`assumption`"',
        {"GIVES": {**model.GIVES, "value": (*model.GIVES["value"], "interval")}},
    ),
    "nominal_outside_supplies_the_value": Mutant(
        "a nominal outside an interval's bounds supplies the value",
        'read_side_contract.md:530 "and one outside them gives `nominal_invalid` in place of '
        '`want_mismatch`"',
        {"shape_by_want": nominal_outside_supplies_the_value},
    ),
    # The status law and the result's members
    "best_status": Mutant(
        "the status the best of the reasons, not the worst",
        'read_side_contract.md:138 "The status is the worst of them: `not_met` over `unknown` over `met`"',
        {"worst": best, "read_the_table": table_read_ended_where_it_has_no_value},
    ),
    "value_beside_not_met": Mutant(
        "a value returned beside `not_met` without an assumption, as beside `condition_outside`",
        'read_side_contract.md:125 "present unless `not_met` with neither an assumption"',
        {"read_value_field": members_read_past_a_refusal, "value_returned": value_whatever_the_status},
    ),
    "unknown_members_returned": Mutant(
        "a member the reader does not know returned",
        'read_side_contract.md:168-169 "A member the reader does not know is left out"',
        {"known_members": every_member},
    ),
    "review_returned_as_its_result": Mutant(
        "a known review returned as its `result` alone",
        'provenance.md:120-123 "A reader returns it as found in two cases only"',
        {"review_read": review_result_alone},
    ),
    "unit_returned_without_its_reason": Mutant(
        "a unit held as a status object returned without its `reason`",
        'read_side_contract.md:127 "a unit held as a status object keeps its `reason`"',
        {"unit_returned": registered_unit},
    ),
    "section_facts_not_merged": Mutant(
        "the result's `specimen` the field's facts alone",
        'read_side_contract.md:129 "specimen facts, the section"',
        {"merged_specimen": field_facts_alone},
    ),
    "results_share_the_record": Mutant(
        "a result shares its members with the record read",
        "an implementation property: no line of the text says a result's members are separate objects "
        "(listed in `NO_LINE_IN_THE_TEXT`, tests/reference/test_citations.py)",
        {"copied": shared},
        survives="a case compares a result's JSON, in which no object is shared",
    ),
    # Rules S2a-4's review pinned (half B, L4; half A, L6)
    "ies_not_a_plural": Mutant(
        "a final `y` exchanged with `ies` not one slip",
        'record_format.md:603-604 "a final `y` exchanged with `ies`"',
        {"_plural_of_either": ies_not_a_plural},
        survives="no case holds a slip of a final `y` made `ies`",
    ),
    "donor_age_of_neither_accepted": Mutant(
        "a `donor_age` holding neither `value` nor `range` accepted",
        'provenance.md:298 "`{"value", "unit": "s", "basis"}` or `{"range": [lo, hi], "unit": "s", '
        '"basis"}`"',
        {"check_fact": donor_age_of_neither_accepted},
        survives="no case holds a `donor_age` with neither `value` nor `range`",
    ),
    "review_of_both_shapes_read_as_its_status": Mutant(
        "a review holding both `status` and `result` read as its status object",
        'provenance.md:124 "one holding both `status` and `result`"',
        {"review_read": both_shapes_read_as_the_status_object},
        survives="no case holds a review holding both `status` and `result`",
    ),
    "reviewed_review_keeps_a_status_objects_members": Mutant(
        "a reviewed review returned with a status object's members, its `reason` among them",
        'provenance.md:120 "A reader returns it as found in two cases only", provenance.md:122-123 "or an '
        'object holding no `status` whose `result` is a token the reader knows (`reviewed`)"',
        {"review_read": reviewed_with_a_status_objects_members},
        survives="no case holds a reviewed review beside a `reason`",
    ),
    # The maintainer's ruling of 2026-10-19 on `unit` under `no_pick`: it replaces
    # `units_stored_differently_read_as_no_pick`, the reading the text now takes.
    "unit_of_the_last_remaining_alternative": Mutant(
        "under `no_pick`, every entry's `unit` the last remaining alternative's",
        'read_side_contract.md:127 "Under `no_pick` the result holds none: each `alternative_values` '
        'entry holds its own"',
        {"read_alternatives": unit_of_the_last_remaining_alternative},
    ),
    # S3b-2's: a table's steps 10 to 13, measured 2026-10-21 at S3b-2's head.
    "edge_unseen_by_the_axis_entry": Mutant(
        "the axis entry `met` at an edge inside the readable range",
        "read_side_contract.md:475 \"the entry is `met` when the operating value lies in the form's range "
        'and on no declared edge"',
        {"table_axis": edge_unseen_by_the_axis_entry},
    ),
    "outside_range_dropped_at_an_edge": Mutant(
        "at an edge outside the readable range, `at_edge` alone",
        'record_format.md:420-421 "`outside_range` stands beside `at_edge`"',
        {"read_the_table": outside_range_dropped_at_an_edge},
    ),
    "source_range_never_narrows": Mutant(
        "the readable range `x`'s, whatever `source_range` holds",
        'record_format.md:416-417 "or `source_range[0]` where that is greater"',
        {
            "read_the_table": source_range_never_narrows_the_read,
            "table_axis": source_range_never_narrows_the_axis,
        },
    ),
    "outside_range_beside_a_range": Mutant(
        "over an operating range of the axis that leaves the readable range, `outside_range` beside "
        "`want_mismatch`",
        'read_side_contract.md:104-106 "an operating range of its axis gives `want_mismatch`"',
        {"read_the_table": outside_range_beside_a_range},
    ),
    "step_11_reasons_without_the_axis": Mutant(
        "step 11's reasons without the axis as their `condition`",
        'read_side_contract.md:143 "A reason carries `condition` exactly when it concerns one condition"',
        {"read_the_table": step_11_reasons_without_the_axis},
    ),
    "table_returned_whole": Mutant(
        "a table returned as stored with the members the reader does not know",
        'read_side_contract.md:168 "A member the reader does not know is left out"',
        {"form_member_returned": table_returned_whole},
    ),
    "table_member_dropped": Mutant(
        "a value read from a table returned without the table it is read from",
        'read_side_contract.md:134 "where the value is read from a table: that table as stored"',
        {"shape_by_want": table_member_dropped},
    ),
    # S3c's: an extrapolation, measured 2026-10-21 at S3c's head.
    "extrapolation_under_any_want": Mutant(
        "an extrapolation applied under any `want`",
        'read_side_contract.md:519 "Under any other `want` an extrapolation is not applied"',
        {"extrapolation_covers": extrapolation_under_any_want},
    ),
    "extrapolation_at_an_edge": Mutant(
        "an extrapolation applied at an edge outside the readable range",
        'read_side_contract.md:519-521 "`outside_range` beside it where it lies outside"',
        {"extrapolation_covers": extrapolation_at_an_edge},
    ),
    "extrapolation_across_an_edge": Mutant(
        "an extrapolation applied across an edge strictly between the read and the readable range's nearest "
        "end",
        'read_side_contract.md:522-524 "Nor is an extrapolation applied across a declared edge"',
        {"extrapolation_covers": extrapolation_across_an_edge},
    ),
    "extrapolation_end_of_x": Mutant(
        "the end value `y[0]` or `y[-1]` where `source_range` narrows the range",
        'read_side_contract.md:517 "the result carries the value at the range" and record_format.md:416-417 '
        '"or `source_range[0]` where that is greater, to `x[-1]`, or `source_range[1]` where that is '
        'smaller"',
        {"read_the_table": end_value_of_x},
    ),
    "extrapolation_far_end": Mutant(
        "the end value taken at the readable range's far end",
        'read_side_contract.md:517 "taken from inside the range"',
        {"nearest_end": the_far_end},
    ),
    "extrapolated_read_ends_at_step_11": Mutant(
        "a read an extrapolation covers given no step-12 reason or label",
        'read_side_contract.md:186-188 "after which the read goes on to steps 12 and 13"',
        {"read_value_field": extrapolated_read_ends_at_step_11},
    ),
    "extrapolation_located_anywhere": Mutant(
        "an extrapolation applied wherever it is located",
        'read_side_contract.md:93-96 "an extrapolation, a nominal or an implied condition located at an '
        'overlay is not applied"',
        {"at_the_read": extrapolation_located_anywhere},
    ),
    "two_extrapolations_read_as_the_first": Mutant(
        "two extrapolations naming one field read as the first",
        'read_side_contract.md:71-72 "So do two acceptances of one kind, `nominal`, `extrapolation`, `pick` '
        'or `trainable`, that name one field"',
        {"checked_acceptances": first_extrapolation_of_each_field},
    ),
    "empty_law_accepted": Mutant(
        "an empty `law` accepted",
        'declarations.md:378 "`law` (text of at least one character, which a reader does not judge)"',
        {"is_law": any_string_a_law},
    ),
    "white_space_law_refused": Mutant(
        "a `law` of white space refused",
        'declarations.md:378 "`law` (text of at least one character, which a reader does not judge)"',
        {"is_law": white_space_no_law},
    ),
    "extrapolation_method_unchecked": Mutant(
        "an extrapolation's `method` unchecked",
        'declarations.md:378 "`method` (`constant` or `consumer_law`)"',
        {"EXTRAPOLATION_METHODS": EveryMethod()},
    ),
    "assumption_with_its_basis": Mutant(
        "an extrapolation's `assumption` holding its `basis`",
        'read_side_contract.md:133 "as the request gives them, `basis` aside"',
        {"checked_acceptances": assumption_with_its_basis},
    ),
    "covered_outside_range_dropped": Mutant(
        "a read an extrapolation covers without its `outside_range`",
        'read_side_contract.md:516 "the result stays `not_met`, its reasons kept"',
        {"read_the_table": covered_outside_range_dropped},
    ),
    # S4d's: step 7's rows for a table alternative at step 11, measured 2026-10-22.
    "outside_range_kept_without_an_extrapolation": Mutant(
        "an alternative outside its form's range, off every edge, kept with no extrapolation to cover it",
        'read_side_contract.md:264-265 "An alternative is set aside where its read lies outside its form"',
        {"fate_of": outside_range_kept, "read_value_field": outside_range_read_for_an_entry},
    ),
    "covered_alternative_set_aside": Mutant(
        "an alternative an extrapolation the request carries would cover set aside, not kept",
        'read_side_contract.md:268-269 "one that an extrapolation the request carries would cover"',
        {"fate_of": covered_set_aside},
    ),
    "edge_inside_the_range_sets_aside": Mutant(
        "a table alternative read exactly at an edge inside its readable range set aside, not refusing",
        'read_side_contract.md:275-276 "A table alternative read exactly at a declared edge refuses the '
        'field"',
        {"fate_of": edge_inside_the_range_sets_aside},
    ),
    "edge_outside_the_range_sets_aside": Mutant(
        "a table alternative read exactly at an edge outside its readable range, `outside_range` beside "
        "`at_edge`, set aside, not refusing",
        'record_format.md:366-368 "A table alternative read exactly at a declared edge (`at_edge`) '
        'refuses the field"',
        {"fate_of": edge_outside_the_range_sets_aside},
    ),
    "set_aside_alternative_reaches_step_11": Mutant(
        "a table alternative set aside at step 10 read on to step 11, its missing operating value refusing "
        "the field",
        'read_side_contract.md:278-279 "one set aside at step 10 never reaches step 11 and refuses nothing"',
        {"read_value_field": set_aside_read_on_to_step_11},
    ),
    "over_a_range_set_aside": Mutant(
        "a table alternative read over an operating range of its axis set aside, not kept",
        'read_side_contract.md:268-271 "table read over an operating range of its axis, say"',
        {"fate_of": over_a_range_set_aside},
    ),
    "over_a_range_counted_as_a_form_want_gives": Mutant(
        "a table read over an operating range of its axis counted as a form `want` gives",
        'read_side_contract.md:291 "A table read over an operating range of its axis counts as a form '
        '`want` cannot give"',
        {"form_want_gives": over_a_range_given_by_want},
    ),
    "over_a_range_entry_unlabelled": Mutant(
        "the `no_pick` entry of a table read over an operating range of its axis without step 12's labels",
        'read_side_contract.md:126 "except that its `labels` are those step 12 gives that alternative even '
        'where its read ended at step 11, as a table read over an operating range of its axis does"',
        {"read_value_field": over_a_range_entry_unlabelled},
    ),
    "over_a_range_entry_bare": Mutant(
        "the `no_pick` entry of a table read over an operating range of its axis without its unit, "
        "specimen, statistics and provenance",
        'record_format.md:378-380 "with its own unit, conditions, specimen, statistics, provenance and '
        'labels"',
        {"read_value_field": over_a_range_entry_bare},
    ),
    "extrapolation_applied_under_no_pick": Mutant(
        "under `no_pick`, the entry of an alternative an extrapolation covers holding the end value and "
        "`assumption`",
        'read_side_contract.md:294-295 "with no nominal or extrapolation applied"',
        {"read_alternatives": kept_entries_extrapolated},
    ),
    "kept_alternative_read_no_further": Mutant(
        "an alternative kept for an extrapolation not read on through steps 12 and 13",
        'read_side_contract.md:271-272 "An alternative kept for an extrapolation is read on through steps '
        '12 and 13"',
        {"read_alternatives": kept_reads_ending_at_step_11},
    ),
    "kept_for_an_extrapolation_under_any_want": Mutant(
        "an alternative outside its range kept for an extrapolation that would cover it under `want: "
        "value`, whatever the `want`",
        'record_format.md:359-360 "unless an extrapolation the request carries would cover it"',
        {"read_alternatives": kept_under_any_want},
    ),
}


# The build model's faults: the hand mutants of the model's rules (`build_model.py`), each run against
# every build-check case file (`test_seeded_faults.py`). The model's own functions, taken first.
Check = build.DeclarationCheck
_build_shaped = Check.shaped
_build_token = Check.token
_build_operating_conditions = Check.operating_conditions
_build_numeric = Check.numeric
_build_population_level = Check.population_level
_build_acceptance = Check.acceptance
_build_own_members = Check.own_members
_build_waiver = Check.waiver
_build_trainable = Check.trainable
_build_requirements = Check.requirements
_build_combination = Check.combination
_build_engine = Check.engine
_build_model_entry = Check.model_entry
_build_sampling = Check.sampling
_build_lacks = Check.lacks
_build_fact = Check.fact
_build_distribution = Check.distribution
_build_check = build.check_build
_build_reads = Check.reads
_build_texts = Check.texts
_build_unplace = Check.unplace
_build_verdict = Check.verdict
_build_trainable_twice = Check.trainable_twice
_build_requirement_condition = Check.requirement_condition
_build_parse = parse
Rules = Mapping[str, tuple[str, ...]] | None


def first_of_an_array(text: bytes) -> JsonValue:
    value = _build_parse(text)
    return value[0] if isinstance(value, list) and value else value


def refused_text_at_a_member(text: bytes, claims: frozenset[str]) -> build.Refused | model.NoVerdict:
    given = _build_check(text, claims)
    if isinstance(given, build.Refused):
        return build.Refused(
            frozenset(build.Refusal(one.item, one.pointer or "/") for one in given.refusals), given.unplaced
        )
    return given


def reshaped(
    change: Callable[[JsonValue, str, build.Place, Rules], tuple[JsonValue, build.Place, Rules]],
) -> Callable[..., JsonObject | None]:
    """`shaped` with its value, place or rules changed first."""

    def shaped(
        self: build.DeclarationCheck,
        value: JsonValue,
        pointer: str,
        place: build.Place,
        missing: Rules = None,
        mistyped: Rules = None,
    ) -> JsonObject | None:
        value, place, missing = change(value, pointer, place, missing)
        return _build_shaped(self, value, pointer, place, missing, mistyped)

    return shaped


def unknown_members_dropped(
    value: JsonValue, pointer: str, place: build.Place, missing: Rules
) -> tuple[JsonValue, build.Place, Rules]:
    known = (
        {name: held for name, held in value.items() if name in place} if isinstance(value, dict) else value
    )
    return known, place, missing


def requirement_relaxed(
    required: str, to: build.Required
) -> Callable[[JsonValue, str, build.Place, Rules], tuple[JsonValue, build.Place, Rules]]:
    def relax(
        value: JsonValue, pointer: str, place: build.Place, missing: Rules
    ) -> tuple[JsonValue, build.Place, Rules]:
        return (
            value,
            {name: (kind, to if held == required else held) for name, (kind, held) in place.items()},
            missing,
        )

    return relax


def any_type(
    value: JsonValue, pointer: str, place: build.Place, missing: Rules
) -> tuple[JsonValue, build.Place, Rules]:
    return value, {name: (object, held) for name, (_, held) in place.items()}, missing


def rule_dropped(
    rule: str, only_where: str | None = None
) -> Callable[[JsonValue, str, build.Place, Rules], tuple[JsonValue, build.Place, Rules]]:
    """The rule taken out of those naming a missing member, everywhere or where the object holds
    `only_where`."""

    def drop(
        value: JsonValue, pointer: str, place: build.Place, missing: Rules
    ) -> tuple[JsonValue, build.Place, Rules]:
        if missing is None or (only_where is not None and only_where not in build.members(value)):
            return value, place, missing
        return (
            value,
            place,
            {name: tuple(one for one in rules if one != rule) for name, rules in missing.items()},
        )

    return drop


def negatives_read_as_positive(
    value: JsonValue, pointer: str, place: build.Place, missing: Rules
) -> tuple[JsonValue, build.Place, Rules]:
    if place in (build.SHAPES["tolerance"], build.SHAPES["mixing"]) and isinstance(value, dict):
        value = {name: abs(held) if isinstance(held, float) else held for name, held in value.items()}
    return value, place, missing


def families_dropped(
    value: JsonValue, pointer: str, place: build.Place, missing: Rules
) -> tuple[JsonValue, build.Place, Rules]:
    if place == build.SHAPES["model entry"] and isinstance(value, dict) and "families" in value:
        value = {**value, "families": {}}
    return value, place, missing


def tokens_without_case(
    self: build.DeclarationCheck, value: JsonValue, pointer: str, tokens: Collection[str]
) -> bool:
    if isinstance(value, str) and value.lower() in {token.lower() for token in tokens}:
        return True
    return _build_token(self, value, pointer, tokens)


def token_slips_taken(
    self: build.DeclarationCheck, value: JsonValue, pointer: str, tokens: Collection[str]
) -> bool:
    if isinstance(value, str) and any(model.one_slip(value, token) for token in tokens):
        return True
    return _build_token(self, value, pointer, tokens)


def unregistered_conditions_dropped(
    self: build.DeclarationCheck, conditions: JsonObject, pointer: str, implied: bool = False
) -> None:
    registered = {name: held for name, held in conditions.items() if name in model.CONDITIONS}
    _build_operating_conditions(self, registered, pointer, implied)


def never(*given: object) -> bool:
    return False


def always(*given: object) -> bool:
    return True


def nothing(*given: object) -> None:
    return None


def last_rule(rules: Iterable[str]) -> str:
    return max(rules, key=build.ORDER.index)


def every_rule(faults: Iterable[build.Fault]) -> frozenset[build.Refusal]:
    return frozenset(build.Refusal(rule, fault.pointer) for fault in faults for rule in fault.rules)


def trainable_anywhere(
    self: build.DeclarationCheck, value: JsonValue, pointer: str, reads: list[str], over: object
) -> None:
    _build_trainable(self, value, pointer, reads, None)


Result = TypeVar("Result")


def faults_dropped(
    method: Callable[..., Result], keep: Callable[[build.DeclarationCheck, build.Fault], bool]
) -> Callable[..., Result]:
    """`method` with the faults it finds that `keep` refuses taken back."""

    def dropped(self: build.DeclarationCheck, *given: object) -> Result:
        before = len(self.faults)
        result = method(self, *given)
        self.faults[before:] = [fault for fault in self.faults[before:] if keep(self, fault)]
        return result

    return dropped


def not_at(pattern: str) -> Callable[[build.DeclarationCheck, build.Fault], bool]:
    """A fault kept unless its pointer matches `pattern`."""
    expression = re.compile(pattern)
    return lambda self, fault: expression.search(fault.pointer) is None


def shaped_unfaulted(
    select: Callable[[str, build.Place], bool],
) -> Callable[..., JsonObject | None]:
    """`shaped` giving no fault for the place `select` names: its members are still typed."""

    def shaped(
        self: build.DeclarationCheck,
        value: JsonValue,
        pointer: str,
        place: build.Place,
        missing: Rules = None,
        mistyped: Rules = None,
    ) -> JsonObject | None:
        before = len(self.faults)
        result = _build_shaped(self, value, pointer, place, missing, mistyped)
        if select(pointer, place):
            del self.faults[before:]
        return result

    return shaped


def label_refusal_at_the_waiver(
    self: build.DeclarationCheck,
    typed: JsonObject,
    pointer: str,
    name: str | None,
    requirements: Mapping[str, JsonObject],
    given: JsonObject,
) -> None:
    before = len(self.faults)
    _build_waiver(self, typed, pointer, name, requirements, given)
    self.faults[before:] = [
        build.Fault(pointer, fault.rules) if "BC-050" in fault.rules else fault
        for fault in self.faults[before:]
    ]


def label_rule_without_review(
    self: build.DeclarationCheck,
    typed: JsonObject,
    pointer: str,
    name: str | None,
    requirements: Mapping[str, JsonObject],
    given: JsonObject,
) -> None:
    reviewed = {field: {**requirement, "review": "reviewed"} for field, requirement in requirements.items()}
    _build_waiver(self, typed, pointer, name, reviewed, given)


def unknown_code_names_a_condition(
    self: build.DeclarationCheck,
    typed: JsonObject,
    pointer: str,
    name: str | None,
    requirements: Mapping[str, JsonObject],
    given: JsonObject,
) -> None:
    _build_waiver(self, typed, pointer, name, requirements, given)
    if typed.get("code") not in model.REASONS and "condition" not in typed:
        self.fault(pointer)


def condition_unknown_name_taken(
    self: build.DeclarationCheck,
    typed: JsonObject,
    pointer: str,
    name: str | None,
    requirements: Mapping[str, JsonObject],
    given: JsonObject,
) -> None:
    before = len(self.faults)
    _build_waiver(self, typed, pointer, name, requirements, given)
    if typed.get("code") == "condition_unknown_name":
        self.faults[before:] = [
            fault for fault in self.faults[before:] if fault.pointer != build.at(pointer, "code")
        ]


def condition_missing_beside_a_refused_code(
    self: build.DeclarationCheck,
    typed: JsonObject,
    pointer: str,
    name: str | None,
    requirements: Mapping[str, JsonObject],
    given: JsonObject,
) -> None:
    _build_waiver(self, typed, pointer, name, requirements, given)
    if typed.get("code") == "condition_unknown_name" and "condition" not in typed:
        self.fault(pointer, apart="condition")


def judged_beside_a_reads_at_fault(method: Callable[..., Result]) -> Callable[..., Result]:
    """`method` (a requirement's, a combination's or a `trainable` entry's check, whose third argument is the
    model's `reads`) with a `reads` at fault taken as a `reads` that lists nothing."""

    def judged(
        self: build.DeclarationCheck, first: object, pointer: str, reads: list[str] | None, *rest: object
    ) -> Result:
        return method(self, first, pointer, [] if reads is None else reads, *rest)

    return judged


def acceptance_of_no_kind_judged(
    self: build.DeclarationCheck, value: JsonValue, pointer: str, requirements: Mapping[str, JsonObject]
) -> None:
    _build_acceptance(self, value, pointer, requirements)
    held = build.members(value)
    kind = held.get("acceptance")
    if (
        "acceptance" in held
        and (not isinstance(kind, str) or kind not in build.KINDS)
        and "reason" not in held
    ):
        self.fault(pointer, "BC-005", build.SHAPE, apart="reason")


def population_level_beside_a_non_token(
    self: build.DeclarationCheck, value: JsonObject, requirement: JsonObject, pointer: str
) -> None:
    _build_population_level(self, value, requirement, pointer)
    represents = value.get("represents")
    if (
        "population_level" in value
        and "represents" in value
        and not (isinstance(represents, str) and represents in model.REPRESENTS)
    ):
        self.fault(build.at(pointer, "population_level"), "BC-043")
        self.rule_refused.append(pointer)


def refusals_under_a_claimed_sampling_suite(
    rule: str,
) -> Callable[[build.DeclarationCheck, JsonObject], None]:
    """`sampling` giving a claimed suite's declaration the refusals the model places, not no verdict, where
    `rule` refuses a requirement (`BC-043`) or a requirement that samples has no `sampling` block
    (`BC-044`)."""

    def sampling(self: build.DeclarationCheck, declaration: JsonObject) -> None:
        _build_sampling(self, declaration)
        refuses = (
            bool(self.rule_refused)
            if rule == "BC-043"
            else "sampling" not in declaration and "BC-044" in self.item_8()
        )
        if "sampling" in self.claims and refuses:
            self.beyond = None

    return sampling


def item_12_beside_another_represents(self: build.DeclarationCheck, declaration: JsonObject) -> None:
    _build_sampling(self, declaration)
    for pointer, requirement in self.sampling_members:
        beside_another = "population_level" in requirement and requirement.get("represents") != "population"
        if beside_another and "sampling" not in self.claims:
            for name in ("represents", "population_level"):
                if name in requirement:
                    self.fault(build.at(pointer, name), "BC-051")


def lacks_but(suite: str) -> Callable[[build.DeclarationCheck, str, str], bool]:
    def lacks(self: build.DeclarationCheck, claimed: str, why: str) -> bool:
        return False if claimed == suite else _build_lacks(self, claimed, why)

    return lacks


def every_suite_lacking(self: build.DeclarationCheck, suite: str, why: str) -> bool:
    return True


def item_7_refusal_dropped(
    self: build.DeclarationCheck, entry: JsonObject, typed: JsonObject, pointer: str
) -> None:
    before = len(self.faults)
    _build_engine(self, entry, typed, pointer)
    self.faults[before:] = [fault for fault in self.faults[before:] if "BC-040" not in fault.rules]
    self.item_7_refused.clear()


def item_7_without(rule: str) -> Callable[..., None]:
    """`engine` with one of item 7's certain rules not read: `values` (a declared value without `reason` or
    `basis`) or `want` (a requirement with a token of `want` other than `value`)."""

    def engine(self: build.DeclarationCheck, entry: JsonObject, typed: JsonObject, pointer: str) -> None:
        held = entry.get("engine")
        if rule == "want":
            self.other_want = False
        if rule == "values" and isinstance(held, dict):
            entry = {**entry, "engine": {**held, "values": {}, "region_values": {}}}
        _build_engine(self, entry, typed, pointer)

    return engine


def item_7_refusal_per_rule(
    self: build.DeclarationCheck, entry: JsonObject, typed: JsonObject, pointer: str
) -> None:
    """Item 7's refusal of a model with a declared value that lacks a member given at the value, not at the
    model's `engine`."""
    _build_engine(self, entry, typed, pointer)
    held = entry.get("engine")
    values = build.members(build.members(held).get("values")) if isinstance(held, dict) else {}
    for attribute, value in values.items():
        if isinstance(value, dict) and not {"reason", "basis"} <= value.keys():
            self.fault(build.at(pointer, "engine", "values", attribute), "BC-040")


def item_7_pointers_placed(
    self: build.DeclarationCheck, entry: JsonObject, typed: JsonObject, pointer: str
) -> None:
    _build_engine(self, entry, typed, pointer)
    self.item_7_scopes.clear()


def engine_withholds_every_member(self: build.DeclarationCheck, entry: JsonValue, pointer: str) -> None:
    before = len(self.faults)
    _build_model_entry(self, entry, pointer)
    if "engine" in build.members(entry):
        self.faults[before:] = [fault for fault in self.faults[before:] if "BC-051" not in fault.rules]


def item_12_before(rule: str) -> Callable[[build.DeclarationCheck, JsonObject], None]:
    """`sampling` with a requirement that item 8 (`BC-044`) or the `population_level` rule (`BC-043`) refuses
    over still refused at its `represents` by item 12."""

    def sampling(self: build.DeclarationCheck, declaration: JsonObject) -> None:
        _build_sampling(self, declaration)
        minimum = build.members(declaration.get("sampling")).get("min_acceptance")
        for pointer, requirement in self.sampling_members:
            if rule == "BC-044":
                refused = "represents" in requirement and not (
                    isinstance(minimum, float) and 0 < minimum <= 1
                )
            else:
                refused = (
                    requirement.get("represents") == "population" and "population_level" not in requirement
                )
            if refused and "sampling" not in self.claims:
                self.fault(build.at(pointer, "represents"), "BC-051")

    return sampling


def item_8_unchecked(self: build.DeclarationCheck) -> tuple[str, ...]:
    return (build.SHAPE,)


def target_basis_taken(
    self: build.DeclarationCheck, name: str, value: JsonValue, pointer: str, basis_allowed: bool
) -> None:
    _build_fact(self, name, value, pointer, True)


def unit_unchecked(self: build.DeclarationCheck, typed: JsonObject, pointer: str, unit: str | None) -> None:
    _build_numeric(self, {name: held for name, held in typed.items() if name != "unit"}, pointer, unit)


def range_sorted(self: build.DeclarationCheck, typed: JsonObject, pointer: str, unit: str | None) -> None:
    ends = typed.get("range")
    if isinstance(ends, list) and all(isinstance(end, float) for end in ends):
        ordered: list[JsonValue] = [*sorted(end for end in ends if isinstance(end, float))]
        typed = {**typed, "range": ordered}
    _build_numeric(self, typed, pointer, unit)


def own_members_eased(kind: str, ease: Callable[[JsonObject], JsonObject]) -> Callable[..., None]:
    def own_members(
        self: build.DeclarationCheck,
        kind_given: str,
        typed: JsonObject,
        pointer: str,
        name: str | None,
        requirements: Mapping[str, JsonObject],
        given: JsonObject,
    ) -> None:
        _build_own_members(
            self, kind_given, ease(typed) if kind_given == kind else typed, pointer, name, requirements, given
        )

    return own_members


def index_rounded(typed: JsonObject) -> JsonObject:
    index = typed.get("index")
    return {**typed, "index": float(round(index))} if isinstance(index, float) else typed


def accepts_deduplicated(typed: JsonObject) -> JsonObject:
    accepts = typed.get("accepts")
    return (
        {**typed, "accepts": list(dict.fromkeys(accepts))}
        if isinstance(accepts, list) and all(isinstance(token, str) for token in accepts)
        else typed
    )


def params_dropped(typed: JsonObject) -> JsonObject:
    return {name: held for name, held in typed.items() if name != "params"}


def parameters_as_the_token_s(self: build.DeclarationCheck, typed: JsonObject, pointer: str) -> None:
    token = typed.get("distribution")
    parameters = build.DISTRIBUTION_PARAMETERS.get(token) if isinstance(token, str) else None
    if parameters is not None and "distribution_parameters" in typed:
        typed = {**typed, "distribution_parameters": dict.fromkeys(parameters, 0.0)}
    _build_distribution(self, typed, pointer)


def every_label(name: str) -> tuple[str, ...]:
    return tuple(model.FIELD_LABELS)


def no_bc_050(self: build.DeclarationCheck, fault: build.Fault) -> bool:
    return "BC-050" not in fault.rules


def no_bc_043(self: build.DeclarationCheck, fault: build.Fault) -> bool:
    return "BC-043" not in fault.rules


def no_level_beside_another_represents(self: build.DeclarationCheck, fault: build.Fault) -> bool:
    return not ("BC-043" in fault.rules and fault.pointer.endswith("/population_level"))


def no_bc_051_at_a_distribution(self: build.DeclarationCheck, fault: build.Fault) -> bool:
    return "BC-051" not in fault.rules or not fault.pointer.rsplit("/", 2)[-2] == "acceptances"


def no_bc_051_at_represents(self: build.DeclarationCheck, fault: build.Fault) -> bool:
    return "BC-051" not in fault.rules or not fault.pointer.endswith("/represents")


def refused_apiece(faults: Iterable[build.Fault]) -> frozenset[build.Refusal]:
    """Each fault refused with its own first case: two faults at one member, one from each rule that names
    it, give two refusals."""
    return frozenset(build.Refusal(build.first_rule(fault.rules), fault.pointer) for fault in faults)


def missing_members_merged(faults: Iterable[build.Fault]) -> frozenset[build.Refusal]:
    """One refusal for each pointer, a missing member's fault merged with the object's and with another
    missing member's."""
    naming: dict[str, list[str]] = {}
    for fault in faults:
        naming.setdefault(fault.pointer, []).extend(fault.rules)
    return frozenset(build.Refusal(build.first_rule(rules), pointer) for pointer, rules in naming.items())


def waiver_dropping(
    drop: Callable[[build.Fault, str, str | None], bool],
) -> Callable[..., None]:
    """`waiver` with the faults `drop` names (given the fault, its pointer and its field) taken back."""

    def waiver(
        self: build.DeclarationCheck,
        typed: JsonObject,
        pointer: str,
        name: str | None,
        requirements: Mapping[str, JsonObject],
        given: JsonObject,
    ) -> None:
        before = len(self.faults)
        _build_waiver(self, typed, pointer, name, requirements, given)
        self.faults[before:] = [fault for fault in self.faults[before:] if not drop(fault, pointer, name)]

    return waiver


def target_status_object_taken(
    self: build.DeclarationCheck, name: str, value: JsonValue, pointer: str, basis_allowed: bool
) -> None:
    if basis_allowed or not build.is_status_object(value):
        _build_fact(self, name, value, pointer, basis_allowed)


def unlocated_pick_refused_by_item_12(
    self: build.DeclarationCheck, value: JsonValue, pointer: str, requirements: Mapping[str, JsonObject]
) -> None:
    _build_acceptance(self, value, pointer, requirements)
    held = build.members(value)
    unlocated = held.get("acceptance") == "pick" and "record" not in held
    if unlocated and held.keys() & {"region", "interval"} and self.lacks("scene_documents", "a pick"):
        self.fault(pointer, "BC-051")


def status_object_without_a_reason(value: JsonValue) -> bool:
    """A status object that holds the `status` member alone: the `reason` it may hold not allowed."""
    return isinstance(value, dict) and value.keys() == {"status"}


def status_object_without_a_status(value: JsonValue) -> bool:
    """An object holding no member but `status` and `reason`, `status` among them or not."""
    return isinstance(value, dict) and value.keys() <= {"status", "reason"}


def target_status_object_with_a_reason_taken(
    self: build.DeclarationCheck, name: str, value: JsonValue, pointer: str, basis_allowed: bool
) -> None:
    if basis_allowed or not (build.is_status_object(value) and "reason" in build.members(value)):
        _build_fact(self, name, value, pointer, basis_allowed)


def acceptance_at_taken(location: str) -> Callable[..., None]:
    """`acceptance` without item 12's refusal of one at `location`, a distribution's own kept."""

    def acceptance(
        self: build.DeclarationCheck, value: JsonValue, pointer: str, requirements: Mapping[str, JsonObject]
    ) -> None:
        before = len(self.faults)
        _build_acceptance(self, value, pointer, requirements)
        held = build.members(value)
        if location in held and held.get("acceptance") != "distribution":
            self.faults[before:] = [fault for fault in self.faults[before:] if "BC-051" not in fault.rules]

    return acceptance


def no_bc_051(self: build.DeclarationCheck, fault: build.Fault) -> bool:
    return "BC-051" not in fault.rules


def claimed_suite_unrecorded(self: build.DeclarationCheck, suite: str, why: str) -> bool:
    return suite not in self.claims


def claimed_suite_gives_the_refusals(self: build.DeclarationCheck) -> build.Refused | model.NoVerdict:
    self.beyond = None
    return _build_verdict(self)


def in_open_interval(number: float) -> bool:
    return 0 < number < 1


def in_interval_from_zero(number: float) -> bool:
    return 0 <= number <= 1


def difference_value_any_refused(typed: JsonObject) -> JsonObject:
    return {**typed, "value": 0.0} if typed.get("value") == "any" else typed


def condition_registered(typed: JsonObject) -> JsonObject:
    return {**typed, "condition": next(iter(model.CONDITIONS))} if "condition" in typed else typed


def accepts_filled(typed: JsonObject) -> JsonObject:
    return {**typed, "accepts": ["consumer"]} if typed.get("accepts") == [] else typed


ONE_RECORD: JsonObject = {"id": "a", "version": "1", "content_hash": "sha256:0"}


def trainable_twice_by_field(self: build.DeclarationCheck, typed: JsonObject, pointer: str) -> None:
    entries = typed.get("trainable")
    if isinstance(entries, list):
        by_field: list[JsonValue] = [
            {"field": entry["field"], "record": ONE_RECORD}
            if isinstance(entry, dict) and "field" in entry
            else entry
            for entry in entries
        ]
        typed = {**typed, "trainable": by_field}
    _build_trainable_twice(self, typed, pointer)


def engine_over_a_domain_refused(
    self: build.DeclarationCheck, entry: JsonObject, typed: JsonObject, pointer: str
) -> None:
    _build_engine(self, entry, typed, pointer)
    if "BC-040" in self.unplaced:
        self.fault(build.at(pointer, "engine"), "BC-040")
        self.item_7_refused.append(build.at(pointer, "engine"))


def interval_location_placed(self: build.DeclarationCheck, rule: str, why: str) -> None:
    if "interval location" not in why:
        _build_unplace(self, rule, why)


def population_level_beside_none_as_shape(
    self: build.DeclarationCheck, value: JsonObject, requirement: JsonObject, pointer: str
) -> None:
    before = len(self.faults)
    _build_population_level(self, value, requirement, pointer)
    if "represents" not in value:
        self.faults[before:] = [
            build.Fault(fault.pointer, (build.SHAPE,))
            if "BC-043" in fault.rules and fault.pointer.endswith("/population_level")
            else fault
            for fault in self.faults[before:]
        ]


def population_level_shape_unchecked(
    self: build.DeclarationCheck, value: JsonObject, requirement: JsonObject, pointer: str
) -> None:
    _build_population_level(
        self, value, {name: held for name, held in requirement.items() if name != "population_level"}, pointer
    )


def texts_refusing_blanks(self: build.DeclarationCheck, typed: JsonObject, pointer: str, *names: str) -> None:
    for name in names:
        held = typed.get(name)
        if isinstance(held, str) and not held.strip():
            self.fault(build.at(pointer, name))


def empty_condition_reason_as_item_3(
    self: build.DeclarationCheck, name: str, entry: JsonValue, pointer: str
) -> None:
    before = len(self.faults)
    _build_requirement_condition(self, name, entry, pointer)
    if build.members(entry).get("reason") == "":
        self.faults[before:] = [
            build.Fault(fault.pointer, ("BC-004", *fault.rules))
            if fault.pointer.endswith("/reason")
            else fault
            for fault in self.faults[before:]
        ]


def is_the_consumer(pointer: str, place: build.Place) -> bool:
    return pointer == "/consumer" and place is build.SHAPES["name and version"]


def is_a_model_name(pointer: str, place: build.Place) -> bool:
    return pointer.endswith("/model") and place is build.SHAPES["name and version"]


def is_an_independence_entry(pointer: str, place: build.Place) -> bool:
    return place is build.SHAPES["independence entry"]


EVERY_STRING = EveryString()
BUILD_MUTANTS: Mapping[str, Mutant] = {
    # Not JSON, or not an object
    "build_array_checked_as_its_first_entry": Mutant(
        "a declaration that is a JSON array checked as its first entry",
        'declarations.md:150-152 "for a text that is not valid JSON, or a declaration that is not an object, '
        'the empty pointer, and nothing else is checked"',
        {"parse": first_of_an_array},
        module=build,
    ),
    "build_refused_text_pointed_at_a_member": Mutant(
        "a text that is not valid JSON, or not an object, refused at `/`, not at the empty pointer",
        'declarations.md:150-152 "for a text that is not valid JSON, or a declaration that is not an object, '
        'the empty pointer"',
        {"check_build": refused_text_at_a_member},
        module=build,
    ),
    # The shape
    "build_unknown_member_ignored": Mutant(
        "a member the table does not name at its place ignored",
        'declarations.md:126 "it holds, at any depth, a member the table does not name at that place"',
        {"DeclarationCheck.shaped": reshaped(unknown_members_dropped)},
        module=build,
    ),
    "build_required_member_taken_missing": Mutant(
        "a required member missing taken",
        'declarations.md:124 "a required member is missing, or a member is of another JSON type"',
        {"DeclarationCheck.shaped": reshaped(requirement_relaxed("yes", "no"))},
        module=build,
    ),
    "build_missing_member_pointed_at_itself": Mutant(
        "a missing member's refusal pointed at the member, not at the object that should hold it",
        'declarations.md:146-147 "for a missing member, the object that should hold it"',
        {"missing_at": build.at},
        module=build,
    ),
    "build_member_of_another_type_taken": Mutant(
        "a member of another JSON type taken",
        'declarations.md:155-156 "A member deeper down that holds another JSON type is a member at fault '
        "like "
        'any other"',
        {"DeclarationCheck.shaped": reshaped(any_type)},
        module=build,
    ),
    "build_empty_list_taken": Mutant(
        "an empty list where the table asks for one entry or more taken",
        'declarations.md:124-125 "or empty where the table asks for one entry or more"',
        {"empty": never},
        module=build,
    ),
    "build_exactly_one_unchecked": Mutant(
        "a place that takes exactly one of its alternatives holding none or two taken",
        'declarations.md:140 "two of a member\'s mutually exclusive alternatives"',
        {"DeclarationCheck.shaped": reshaped(requirement_relaxed("one", "no"))},
        module=build,
    ),
    "build_target_basis_taken": Mutant(
        "a target fact holding `basis` taken",
        'declarations.md:92 "a fact of `provenance.md` section 6.2 to its shape there without `basis`"',
        {"DeclarationCheck.fact": target_basis_taken},
        module=build,
    ),
    # Tokens and registered names
    "build_tokens_compared_without_case": Mutant(
        "a token compared without case",
        'declarations.md:129-130 "a token or a registered name is not one of those its member takes, a slip '
        "of one, another member's token and one in another case included\"",
        {"DeclarationCheck.token": tokens_without_case},
        module=build,
    ),
    "build_token_slips_taken": Mutant(
        "a token one slip from one its member takes taken",
        'declarations.md:129-130 "a token or a registered name is not one of those its member takes, a slip '
        'of one"',
        {"DeclarationCheck.token": token_slips_taken},
        module=build,
    ),
    "build_unregistered_condition_taken": Mutant(
        "an operating condition the build's version does not register taken",
        'declarations.md:85 "registered condition to `{"value", "unit"}` or `{"range": [lo, hi], "unit"}`"',
        {"DeclarationCheck.operating_conditions": unregistered_conditions_dropped},
        module=build,
    ),
    "build_review_unchecked": Mutant(
        "a requirement's `review` holding any string taken",
        'declarations.md:214 "A requirement\'s `review` holds `reviewed`, the one token of schema 0.1.0"',
        {"REVIEWS": EVERY_STRING},
        module=build,
    ),
    "build_want_unchecked": Mutant(
        "a requirement's `want` left to the read",
        'declarations.md:104 "a token of `read_side_contract.md` section 6"',
        {"WANTS": EVERY_STRING},
        module=build,
    ),
    "build_extrapolation_method_unchecked": Mutant(
        "an extrapolation's `method` unchecked",
        'declarations.md:118 "an extrapolation\'s `method`, `constant` or `consumer_law`"',
        {"EXTRAPOLATION_METHODS": EVERY_STRING},
        module=build,
    ),
    "build_waiver_code_unchecked": Mutant(
        "a waiver's `code` holding any string taken",
        'declarations.md:118 "a waiver\'s `code`, a reason of `read_side_contract.md` section 4"',
        {"REASONS": EVERY_STRING},
        module=build,
    ),
    "build_mixing_rule_unchecked": Mutant(
        "a mixing rule holding any string taken",
        'declarations.md:97 "field to `identity`, a rule `mixing_rules.md` names, or `refuse`"',
        {"MIXING_RULES": EVERY_STRING},
        "no case declares `mixing`",
        module=build,
    ),
    "build_unregistered_label_taken": Mutant(
        "a label registered for another field taken",
        'declarations.md:106 "a label registered for the field"',
        {"label_of": every_label},
        module=build,
    ),
    "build_families_unchecked": Mutant(
        "a `families` entry for a field whose row allows no parameter set taken",
        'declarations.md:96 "parameter-set field to the family version"',
        {"DeclarationCheck.shaped": reshaped(families_dropped)},
        "every case's `families` is empty",
        module=build,
    ),
    # Names twice, and a field or location dangling
    "build_names_given_twice_taken": Mutant(
        "a name given twice where the table allows it once taken",
        'declarations.md:131 "a name is given twice where the table allows it once"',
        {"given_before": never},
        module=build,
    ),
    "build_unread_field_taken": Mutant(
        "a requirement or a `trainable` entry for a field not in `reads` taken",
        'declarations.md:134 "a requirement or a `trainable` entry names a field its model does not list in '
        '`reads`"',
        {"read_by": always},
        module=build,
    ),
    "build_trainable_location_unchecked": Mutant(
        "a `trainable` entry at a location its model is not checked over taken",
        'declarations.md:134-135 "or a `trainable` entry a location its model is not checked over"',
        {"DeclarationCheck.trainable": trainable_anywhere},
        module=build,
    ),
    # Holds
    "build_empty_reason_taken": Mutant(
        "an empty `reason`, `basis` or `law` taken",
        'declarations.md:137 "a `reason` or `basis` is not a string of at least one character"',
        {"DeclarationCheck.texts": nothing},
        module=build,
    ),
    "build_unit_unchecked": Mutant(
        "a unit other than the registered one taken",
        'declarations.md:138-139 "a unit other than the registered one"',
        {"DeclarationCheck.numeric": unit_unchecked},
        "no case gives a unit other than its condition's",
        module=build,
    ),
    "build_range_order_unchecked": Mutant(
        "a `range` whose `lo` is above its `hi` taken",
        'declarations.md:138 "a `range` whose `lo` is above its `hi`"',
        {"DeclarationCheck.numeric": range_sorted},
        "no case gives a range upside down",
        module=build,
    ),
    "build_negative_number_taken": Mutant(
        "a tolerance or a `fraction_sum_tolerance` below zero taken",
        'declarations.md:139 "other than the registered one, a number below zero"',
        {"DeclarationCheck.shaped": reshaped(negatives_read_as_positive)},
        "no case gives a number below zero",
        module=build,
    ),
    "build_fractional_index_taken": Mutant(
        "a pick's `index` with a fractional part taken",
        'declarations.md:139 "an `index` with a fractional part"',
        {"DeclarationCheck.own_members": own_members_eased("pick", index_rounded)},
        "every pick in the cases has a whole index",
        module=build,
    ),
    "build_combination_unchecked": Mutant(
        "a combination of fewer than two fields, of one section or of fields not read taken",
        'declarations.md:98 "lists of two or more fields in `reads`, from different sections"',
        {"DeclarationCheck.combination": nothing},
        module=build,
    ),
    "build_distribution_parameters_unchecked": Mutant(
        "a distribution's parameters other than its token's taken",
        "declarations.md:141 \"a distribution's parameters other than its token's\"",
        {"DeclarationCheck.distribution": parameters_as_the_token_s},
        "the one distribution in the cases holds its token's parameters",
        module=build,
    ),
    "build_repeated_accepts_taken": Mutant(
        "a repeated `accepts` token taken",
        'declarations.md:141 "a repeated `accepts` token"',
        {"DeclarationCheck.own_members": own_members_eased("overlay_scope", accepts_deduplicated)},
        "the one `overlay_scope` in the cases accepts one member",
        module=build,
    ),
    "build_params_taken": Mutant(
        "a nominal's `params` for a field whose row allows no parameter set taken",
        'declarations.md:118 "`params` only for a field whose row allows the form `parameter_set`"',
        {"DeclarationCheck.own_members": own_members_eased("nominal", params_dropped)},
        module=build,
    ),
    "build_chains_unchecked": Mutant(
        "a chain's members unchecked",
        'declarations.md:100 "`{"from", "event", "to", "state_mapping"}`, all required (section 6)"',
        {"DeclarationCheck.chain": nothing},
        "every case's `chains` is empty",
        module=build,
    ),
    # Items 3 and 4, the location rule and section 4.1 item 4
    "build_item_3_unchecked": Mutant(
        "a tolerance or an accept list without its `reason` refused as a missing member alone (BC-048)",
        'declarations.md:188 "A tolerance or accept list MUST carry its reason; the build refuses one '
        'without"',
        {"DeclarationCheck.shaped": reshaped(rule_dropped("BC-004"))},
        module=build,
    ),
    "build_item_3_on_tolerances_alone": Mutant(
        "an accept list without its `reason` refused as a missing member alone (BC-048)",
        'declarations.md:188 "A tolerance or accept list MUST carry its reason"',
        {"DeclarationCheck.shaped": reshaped(rule_dropped("BC-004", "accept"))},
        module=build,
    ),
    "build_item_4_unchecked": Mutant(
        "an acceptance without its `reason` or `basis` refused as a missing member alone (BC-048)",
        'declarations.md:190 "Every acceptance MUST carry a `reason`"',
        {"DeclarationCheck.shaped": reshaped(rule_dropped("BC-005"))},
        module=build,
    ),
    "build_basis_unrequired": Mutant(
        "an extrapolation, a nominal and a distribution taken without `basis`",
        'declarations.md:190-191 "an extrapolation, a nominal and a distribution also carry the `basis` of '
        'their number"',
        {"NEEDS_BASIS": ()},
        module=build,
    ),
    "build_basis_unrequired_of_an_extrapolation": Mutant(
        "`basis` required of a nominal and a distribution, but not of an extrapolation",
        'declarations.md:117 "| | `basis` | for `extrapolation`, `nominal` and `distribution` (item 4)"',
        {"NEEDS_BASIS": ("nominal", "distribution")},
        module=build,
    ),
    "build_basis_required_of_every_kind": Mutant(
        "`basis` required of every acceptance, a waiver's included",
        'declarations.md:117 "| | `basis` | for `extrapolation`, `nominal` and `distribution` (item 4)"',
        {"NEEDS_BASIS": tuple(build.KINDS)},
        module=build,
    ),
    "build_location_rule_unchecked": Mutant(
        "an acceptance whose kind needs a location taken without one",
        'declarations.md:384 "An acceptance whose kind needs a location and names none is refused"',
        {"DeclarationCheck.shaped": reshaped(requirement_relaxed("located", "no"))},
        module=build,
    ),
    "build_accepted_difference_needs_a_location": Mutant(
        "an accepted difference refused without a location",
        'declarations.md:377 "| `accepted_difference` | optional: absent, every location the model is '
        "checked "
        'over |"',
        {
            "KINDS": {
                **build.KINDS,
                "accepted_difference": {**build.KINDS["accepted_difference"], **build.LOCATIONS},
            }
        },
        module=build,
    ),
    "build_implied_condition_located_optionally": Mutant(
        "an implied condition taken without a location",
        'declarations.md:376 "| `implied_condition` | `region`, `interval` or `record` |"',
        {
            "KINDS": {
                **build.KINDS,
                "implied_condition": {**build.KINDS["implied_condition"], **build.OPTIONAL_LOCATIONS},
            }
        },
        module=build,
    ),
    "build_waiver_condition_unrequired": Mutant(
        "a waiver's `condition` refused for every code",
        'declarations.md:118 "a code names a condition where its reasons always carry one: the six '
        '`condition_*` codes"',
        {"CODES_NAMING_A_CONDITION": ()},
        module=build,
    ),
    "build_unknown_code_names_a_condition": Mutant(
        "a waiver whose `code` is no reason refused without a `condition`",
        'declarations.md:118 "a waiver whose `code` is no reason names no condition"',
        {"DeclarationCheck.waiver": unknown_code_names_a_condition},
        module=build,
    ),
    "build_label_rule_unchecked": Mutant(
        "a waiver naming a label taken whatever its requirement names",
        'declarations.md:405-406 "the build refuses it at build unless the requirement for its field names '
        'that `label` and holds `review: "reviewed"`"',
        {"DeclarationCheck.waiver": faults_dropped(_build_waiver, no_bc_050)},
        module=build,
    ),
    "build_label_rule_without_review": Mutant(
        "a waiver naming a label taken where its requirement names the label without `review`",
        'declarations.md:405-406 "names that `label` and holds `review: "reviewed"`"',
        {"DeclarationCheck.waiver": label_rule_without_review},
        module=build,
    ),
    "build_label_refusal_at_the_waiver": Mutant(
        "BC-050's refusal pointed at the waiver, not at its `label`",
        'declarations.md:149-150 "for a waiver naming a `label` that section 4.1 item 4 refuses, that '
        "waiver's `label`\"",
        {"DeclarationCheck.waiver": label_refusal_at_the_waiver},
        module=build,
    ),
    # Items 7, 8 and 12, and the population_level rule
    "build_item_8_unchecked": Mutant(
        "a requirement that samples taken without `sampling.min_acceptance`",
        'declarations.md:206-207 "A declaration in which a requirement samples, without it or with one '
        "outside "
        '(0, 1], is refused at build"',
        {"DeclarationCheck.item_8": item_8_unchecked},
        module=build,
    ),
    "build_population_level_rule_unchecked": Mutant(
        "a population `represents` taken without `population_level`",
        'declarations.md:64 "where `represents` is `population` and the field is sampled, '
        '`population_level`"',
        {"DeclarationCheck.population_level": faults_dropped(_build_population_level, no_bc_043)},
        module=build,
    ),
    "build_scene_members_taken": Mutant(
        "a member the scene suite checks taken without it, which the arms for a domain, a path and "
        "`region_conditions` kill; the legs at a region or an interval are pinned by no case "
        "(`build_acceptance_at_a_region_taken`, `build_trainable_at_a_region_taken`)",
        'declarations.md:221-222 "where it does not claim the scene suite, a model checked over a domain or '
        'a path, `region_conditions`"',
        {"DeclarationCheck.lacks": lacks_but("scene_documents")},
        module=build,
    ),
    "build_sampling_members_taken": Mutant(
        "`sampling`, `represents`, `population_level` or a distribution taken without the sampling suite",
        "declarations.md:223-225 \"where it does not claim the sampling suite, `sampling`, a requirement's "
        '`represents` or `population_level`, and a `distribution`"',
        {"DeclarationCheck.lacks": lacks_but("sampling")},
        module=build,
    ),
    "build_distribution_taken": Mutant(
        "a distribution acceptance taken without the sampling suite",
        'declarations.md:224-225 "`represents` or `population_level`, and a `distribution` acceptance"',
        {"DeclarationCheck.acceptance": faults_dropped(_build_acceptance, no_bc_051_at_a_distribution)},
        module=build,
    ),
    "build_represents_taken": Mutant(
        "a requirement's `represents` taken without the sampling suite",
        "declarations.md:224 \"sampling suite, `sampling`, a requirement's `represents` or "
        '`population_level`"',
        {"DeclarationCheck.sampling": faults_dropped(_build_sampling, no_bc_051_at_represents)},
        module=build,
    ),
    "build_claimed_suite_lacking": Mutant(
        "a member a claimed suite checks refused as if the build did not claim it",
        'declarations.md:221 "A build refuses at build what it cannot check"',
        {"DeclarationCheck.lacks": every_suite_lacking},
        module=build,
    ),
    "build_item_12_before_item_8": Mutant(
        "a requirement item 8 refuses the declaration over refused at its `represents` by item 12 too",
        'declarations.md:227-228 "where item 8 or that rule refuses the declaration over a requirement, that '
        'requirement gives none"',
        {"DeclarationCheck.sampling": item_12_before("BC-044")},
        module=build,
    ),
    "build_item_12_before_the_population_level_rule": Mutant(
        "a requirement the `population_level` rule refuses refused at its `represents` by item 12 too",
        'declarations.md:227-228 "where item 8 or that rule refuses the declaration over a requirement, that '
        'requirement gives none"',
        {"DeclarationCheck.sampling": item_12_before("BC-043")},
        module=build,
    ),
    "build_engine_withholds_every_member": Mutant(
        "an engine model item 7 refuses giving no refusal under item 12 for any member, its domain's "
        "included",
        'declarations.md:226 "come first, member by member"',
        {"DeclarationCheck.model_entry": engine_withholds_every_member},
        module=build,
    ),
    "build_item_7_refusal_dropped": Mutant(
        "an engine model checked over records taken",
        'declarations.md:198-199 "one checked over a path or records, over a domain that includes the '
        'background, or with another `want`, is refused at build"',
        {"DeclarationCheck.engine": item_7_refusal_dropped},
        module=build,
    ),
    "build_item_7_pointers_placed": Mutant(
        "a fault inside an engine model's `engine`, or at its requirement's `want`, placed as its own rule's",
        "item 7 may name such a fault first (OPEN_POINTS: item_7_beyond_the_declaration)",
        {"DeclarationCheck.engine": item_7_pointers_placed},
        module=build,
    ),
    "build_item_7_values_unread": Mutant(
        "a declared engine value without its `reason` or `basis` not read as item 7's refusal of the model",
        'declarations.md:199-200 "A declared engine value without `reason` and `basis`"',
        {"DeclarationCheck.engine": item_7_without("values")},
        module=build,
    ),
    "build_item_7_want_unread": Mutant(
        "a requirement with a token of `want` other than `value` not read as item 7's refusal of the model",
        'declarations.md:199 "or with another `want`, is refused at build"',
        {"DeclarationCheck.engine": item_7_without("want")},
        module=build,
    ),
    "build_item_7_refusal_at_the_value": Mutant(
        "item 7's refusal of a declared engine value without its `reason` or `basis` given at the value, "
        "beside the model's",
        'declarations.md:150-151 "for a model item 7 refuses, its `engine`, one refusal per model, '
        "whichever of that item's rules it breaks\"",
        {"DeclarationCheck.engine": item_7_refusal_per_rule},
        module=build,
    ),
    # Precedence
    "build_precedence_reversed": Mutant(
        "a fault two rules name carrying the last rule's case, not the first's",
        'declarations.md:177-180 "A fault more than one rule names carries the case of the first of: '
        "items 3, "
        '4, 7 and 8, the"',
        {"first_rule": last_rule},
        module=build,
    ),
    "build_every_rule_reported": Mutant(
        "a fault two rules name refused under both",
        'declarations.md:177 "A fault more than one rule names carries the case of the first of"',
        {"refusals_of": every_rule},
        module=build,
    ),
    # The rulings of 2026-10-24, whose words land with S7a-1b's first commit
    "build_condition_unknown_name_taken": Mutant(
        "a waiver of `condition_unknown_name` taken, though section 4.2 never accepts it",
        'declarations.md:118 "other than `condition_unknown_name`, which section 4.2 never accepts"',
        {"DeclarationCheck.waiver": condition_unknown_name_taken},
        module=build,
    ),
    "build_condition_missing_beside_a_refused_code": Mutant(
        "a waiver of `condition_unknown_name` naming no `condition` refused for the `condition` too",
        'declarations.md:159-160 "a waiver\'s missing `condition` beside a `code` that is refused"',
        {"DeclarationCheck.waiver": condition_missing_beside_a_refused_code},
        module=build,
    ),
    "build_basis_on_any_kind": Mutant(
        "a `basis` on a waiver, an implied condition, an accepted difference, a pick or an overlay taken",
        'declarations.md:117 "(item 4); no other kind holds it"',
        {"KINDS": {kind: {**place, "basis": (str, "no")} for kind, place in build.KINDS.items()}},
        module=build,
    ),
    "build_population_level_beside_any_represents": Mutant(
        "a `population_level` beside a `represents` that is not `population` taken, and refused by item 12 "
        "where the build does not claim the sampling suite",
        'declarations.md:109 "where `represents` is `population`, and only there"',
        {
            "DeclarationCheck.population_level": faults_dropped(
                _build_population_level, no_level_beside_another_represents
            ),
            "DeclarationCheck.sampling": item_12_beside_another_represents,
        },
        module=build,
    ),
    # The rulings of 2026-10-24 on the review: one fault is one member at fault, and a pick is located by its
    # record
    "build_member_faults_refused_apiece": Mutant(
        "two faults at one member, one from each rule that names it (a waiver's `label` that item 4 and the "
        "token rule both refuse, a `domain` of another JSON type that item 12 and the shape rule both name), "
        "given a refusal each",
        'declarations.md:177-180 "A fault more than one rule names carries the case of the first of: items '
        '3, 4, 7 and 8, the"',
        {"refusals_of": refused_apiece},
        module=build,
    ),
    "build_missing_members_merged": Mutant(
        "the faults at one pointer merged whatever they are about, so that two members missing from one "
        "object, or one missing and the object's own, give one refusal",
        'declarations.md:180 "Two faults with one case and one pointer are one refusal"',
        {"refusals_of": missing_members_merged},
        module=build,
    ),
    "build_status_object_checked_inside": Mutant(
        "a status object as a target fact or an implied condition's value checked as an ordinary member, "
        "refused at the member and again inside it",
        'declarations.md:92 "never a status object"',
        {"is_status_object": never},
        module=build,
    ),
    "build_target_status_object_taken": Mutant(
        "a status object as a target fact taken",
        'declarations.md:92 "never a status object"',
        {"DeclarationCheck.fact": target_status_object_taken},
        module=build,
    ),
    "build_status_object_without_a_reason": Mutant(
        "a status object holding a `reason` judged an ordinary member: the `reason` it may hold not allowed",
        'provenance.md:8-9 "an object whose only members are `status` and, optionally, `reason` (a text)"',
        {"is_status_object": status_object_without_a_reason},
        module=build,
    ),
    "build_status_object_needing_no_status": Mutant(
        "an object holding a `reason` and no `status` taken for a status object",
        'provenance.md:8-9 "an object whose only members are `status` and, optionally, `reason` (a text)"',
        {"is_status_object": status_object_without_a_status},
        module=build,
    ),
    "build_target_status_object_with_a_reason_taken": Mutant(
        "a status object holding a `reason` as a target fact taken",
        'declarations.md:92 "never a status object"',
        {"DeclarationCheck.fact": target_status_object_with_a_reason_taken},
        module=build,
    ),
    "build_pick_located_at_a_region": Mutant(
        "a pick naming a region or an interval and no record taken as located",
        'declarations.md:374 "a pick that also names a `region` or an `interval` is not applied in a plain '
        'read"',
        {"KINDS": {**build.KINDS, "pick": {**build.LOCATIONS, "index": (float, "yes")}}},
        module=build,
    ),
    "build_unlocated_pick_refused_by_item_12": Mutant(
        "a pick naming a region and no record refused by item 12 beside the location rule, or taken as "
        "beyond "
        "the model where the build claims the scene suite",
        'declarations.md:222-223 "an acceptance or `trainable` entry located at a region or an interval"',
        {"DeclarationCheck.acceptance": unlocated_pick_refused_by_item_12},
        module=build,
    ),
    "build_order_048_before_050": Mutant(
        "a fault two rules name carrying the shape rule's case before item 4's and item 12's",
        'declarations.md:177-180 "A fault more than one rule names carries the case of the first of: items '
        '3, 4, 7 and 8, the"',
        {"ORDER": ("BC-004", "BC-005", "BC-040", "BC-044", "BC-043", "BC-037", "BC-048", "BC-050", "BC-051")},
        module=build,
    ),
    "build_order_005_before_004": Mutant(
        "a fault two rules name carrying item 4's case before item 3's",
        'declarations.md:177-180 "A fault more than one rule names carries the case of the first of: items '
        '3, 4, 7 and 8, the"',
        {"ORDER": ("BC-005", "BC-004", "BC-040", "BC-044", "BC-043", "BC-037", "BC-050", "BC-051", "BC-048")},
        module=build,
    ),
    # Item 12's two legs at a region or an interval, and the claimed suite
    "build_acceptance_at_a_region_taken": Mutant(
        "an acceptance at a region taken without the scene suite",
        'declarations.md:222-223 "an acceptance or `trainable` entry located at a region or an interval"',
        {"DeclarationCheck.acceptance": acceptance_at_taken("region")},
        module=build,
    ),
    "build_acceptance_at_an_interval_taken": Mutant(
        "an acceptance at an interval taken without the scene suite",
        'declarations.md:222-223 "an acceptance or `trainable` entry located at a region or an interval"',
        {"DeclarationCheck.acceptance": acceptance_at_taken("interval")},
        "no case holds an acceptance at an interval, whatever the suite",
        module=build,
    ),
    "build_trainable_at_a_region_taken": Mutant(
        "a `trainable` entry at a region or an interval taken without the scene suite",
        'declarations.md:222-223 "an acceptance or `trainable` entry located at a region or an interval"',
        {"DeclarationCheck.trainable": faults_dropped(_build_trainable, no_bc_051)},
        module=build,
    ),
    "build_claimed_suite_beyond_unrecorded": Mutant(
        "a member a claimed suite checks taken as if nothing were beyond the model, so that the "
        "declaration's "
        "other refusals stand",
        'declarations.md:221 "A build refuses at build what it cannot check"',
        {"DeclarationCheck.lacks": claimed_suite_unrecorded},
        module=build,
    ),
    "build_claimed_suite_gives_the_refusals": Mutant(
        "a declaration holding a member a claimed suite checks given the refusals of the model's own rules, "
        "not no verdict",
        'declarations.md:221 "A build refuses at build what it cannot check"',
        {"DeclarationCheck.verdict": claimed_suite_gives_the_refusals},
        module=build,
    ),
    # The rules the review found no fault for
    "build_min_acceptance_one_refused": Mutant(
        "a `min_acceptance` of 1 refused",
        'declarations.md:205 "`sampling.min_acceptance` is a number in (0, 1]"',
        {"in_unit_interval": in_open_interval},
        "no case gives a `min_acceptance` of 1",
        module=build,
    ),
    "build_min_acceptance_zero_taken": Mutant(
        "a `min_acceptance` of 0 taken",
        'declarations.md:205 "`sampling.min_acceptance` is a number in (0, 1]"',
        {"in_unit_interval": in_interval_from_zero},
        "no case gives a `min_acceptance` of 0",
        module=build,
    ),
    "build_any_difference_refused": Mutant(
        'an accepted difference of value `"any"` refused',
        'declarations.md:118 "a status object or `"any"`"',
        {
            "DeclarationCheck.own_members": own_members_eased(
                "accepted_difference", difference_value_any_refused
            )
        },
        'no case holds an accepted difference of value `"any"`',
        module=build,
    ),
    "build_trainable_twice_by_field": Mutant(
        "two `trainable` entries for one field at two locations refused",
        'declarations.md:132-133 "two `trainable` entries for one field at one location"',
        {"DeclarationCheck.trainable_twice": trainable_twice_by_field},
        module=build,
    ),
    "build_engine_over_a_domain_refused": Mutant(
        "an engine model over a domain refused by item 7 as certainly as one over records",
        "item 7 refuses an engine model over a domain that includes the background, or shares a region with "
        "another's, which the declaration does not tell (OPEN_POINTS: item_7_beyond_the_declaration)",
        {"DeclarationCheck.engine": engine_over_a_domain_refused},
        module=build,
    ),
    "build_interval_location_placed": Mutant(
        "an interval location's shape placed, its BC-048 given as for any member",
        "the text gives an interval location no shape (OPEN_POINTS: interval_location)",
        {"DeclarationCheck.unplace": interval_location_placed},
        "no case holds an interval location",
        module=build,
    ),
    "build_waiver_condition_token_unchecked": Mutant(
        "a waiver's `condition` holding any string taken",
        'declarations.md:129-130 "a token or a registered name is not one of those its member takes"',
        {"DeclarationCheck.own_members": own_members_eased("waiver", condition_registered)},
        "no case gives a waiver a `condition` that is no registered one",
        module=build,
    ),
    "build_population_level_beside_none_refused_as_shape": Mutant(
        "a `population_level` beside no `represents` refused as BC-048, not BC-043",
        'declarations.md:109 "where `represents` is `population`, and only there"',
        {"DeclarationCheck.population_level": population_level_beside_none_as_shape},
        module=build,
    ),
    "build_independence_entry_shape_unchecked": Mutant(
        "an independence entry's members, required and named, unchecked",
        'declarations.md:208-209 "`sampling.independence` is a list of `{"fields": [<location and field>, '
        '...], "reason", "basis"}`"',
        {"DeclarationCheck.shaped": shaped_unfaulted(is_an_independence_entry)},
        "no case holds an independence entry",
        module=build,
    ),
    "build_independence_entry_texts_unchecked": Mutant(
        "an independence entry's empty `reason` or `basis` taken",
        'declarations.md:137 "a `reason` or `basis` is not a string of at least one character"',
        {
            "DeclarationCheck.sampling": faults_dropped(
                _build_sampling, not_at(r"^/sampling/independence/\d+/")
            )
        },
        "no case holds an independence entry",
        module=build,
    ),
    "build_sampling_independence_unrequired": Mutant(
        "a `sampling` block without `independence` taken",
        'declarations.md:86 "`{"min_acceptance", "reason", "independence"}`, all required (items 8, 9)"',
        {"SHAPES": {**build.SHAPES, "sampling": {**build.SHAPES["sampling"], "independence": (list, "no")}}},
        "no case holds a `sampling` block without `independence`",
        module=build,
    ),
    "build_space_unchecked": Mutant(
        "a distribution's `space` holding any string taken",
        'declarations.md:444 "`space` is `identity` or `log` (natural"',
        {"SPACES": EVERY_STRING},
        "the one distribution in the cases holds a `space` of the text's",
        module=build,
    ),
    "build_empty_reads_taken": Mutant(
        "an empty `reads` taken",
        'declarations.md:93 "yes, at least one | registered fields, none twice"',
        {"DeclarationCheck.reads": faults_dropped(_build_reads, not_at(r"/reads$"))},
        module=build,
    ),
    # The rulings of 2026-10-24 and of 2026-10-25: a rule stands aside where the member it judges
    # against is at fault
    "build_requirement_judged_beside_a_reads_at_fault": Mutant(
        "a requirement's `field` judged against a `reads` at fault as against one that lists nothing",
        'declarations.md:159 "requirement\'s `field` against a `reads` at fault (an empty one too)"',
        {"DeclarationCheck.requirements": judged_beside_a_reads_at_fault(_build_requirements)},
        module=build,
    ),
    "build_combination_judged_beside_a_reads_at_fault": Mutant(
        "a combination's fields judged against a `reads` at fault as against one that lists nothing",
        'declarations.md:157-158 "A rule that judges one member against another stands aside where the '
        'other is itself at fault" (OPEN_POINTS: reads_at_fault)',
        {"DeclarationCheck.combination": judged_beside_a_reads_at_fault(_build_combination)},
        module=build,
    ),
    "build_trainable_judged_beside_a_reads_at_fault": Mutant(
        "a `trainable` entry's field judged against a `reads` at fault as against one that lists nothing",
        'declarations.md:157-158 "A rule that judges one member against another stands aside where the '
        'other is itself at fault" (OPEN_POINTS: reads_at_fault)',
        {"DeclarationCheck.trainable": judged_beside_a_reads_at_fault(_build_trainable)},
        module=build,
    ),
    "build_population_level_rule_beside_a_non_token": Mutant(
        "the `population_level` rule refusing a `population_level` beside a `represents` that is no token",
        'declarations.md:158 "the `population_level` rule beside a `represents` that is no token"',
        {"DeclarationCheck.population_level": population_level_beside_a_non_token},
        module=build,
    ),
    "build_acceptance_of_no_kind_judged": Mutant(
        "an acceptance of no known kind refused for its missing `reason` too",
        'declarations.md:160-161 "an acceptance that names no known kind is refused at itself, and none of '
        'its other members is judged"',
        {"DeclarationCheck.acceptance": acceptance_of_no_kind_judged},
        module=build,
    ),
    # Under a claimed suite the build fails closed
    "build_population_level_rule_refused_under_a_claim": Mutant(
        "a requirement the `population_level` rule refuses given that refusal where the build claims the "
        "sampling suite",
        "declarations.md:223-225 \"where it does not claim the sampling suite, `sampling`, a requirement's "
        '`represents` or `population_level`, and a `distribution`" (OPEN_POINTS: '
        "claimed_suite_hides_refusals)",
        {"DeclarationCheck.sampling": refusals_under_a_claimed_sampling_suite("BC-043")},
        module=build,
    ),
    "build_missing_sampling_block_refused_under_a_claim": Mutant(
        "a requirement that samples with no `sampling` block given item 8's refusal where the build claims "
        "the sampling suite",
        "declarations.md:223-225 \"where it does not claim the sampling suite, `sampling`, a requirement's "
        '`represents` or `population_level`, and a `distribution`" (OPEN_POINTS: '
        "claimed_suite_hides_refusals)",
        {"DeclarationCheck.sampling": refusals_under_a_claimed_sampling_suite("BC-044")},
        module=build,
    ),
    "build_consumer_shape_unchecked": Mutant(
        'a `consumer` missing a member of `{"name", "version"}`, or holding another, taken',
        'declarations.md:84 "| declaration | `consumer` | yes | `{"name", "version"}`, both required |"',
        {"DeclarationCheck.shaped": shaped_unfaulted(is_the_consumer)},
        "no case holds a `consumer` of another shape",
        module=build,
    ),
    "build_model_name_and_version_unchecked": Mutant(
        'a `model` missing a member of `{"name", "version"}`, or holding another, taken',
        'declarations.md:88 "| model entry | `model` | yes | `{"name", "version"}`, both required"',
        {"DeclarationCheck.shaped": shaped_unfaulted(is_a_model_name)},
        "no case holds a `model` of another shape",
        module=build,
    ),
    "build_waiver_condition_missing_taken": Mutant(
        "a waiver whose `code` names a condition taken without its `condition`",
        'declarations.md:118 "required where it holds and refused where it does not"',
        {"DeclarationCheck.waiver": waiver_dropping(lambda fault, pointer, name: fault.pointer == pointer)},
        module=build,
    ),
    "build_empty_accepts_taken": Mutant(
        "an `overlay_scope` accepting nothing taken",
        'declarations.md:118 "at least one of `consumer`, `model` and `configuration`, none twice"',
        {"DeclarationCheck.own_members": own_members_eased("overlay_scope", accepts_filled)},
        "the one `overlay_scope` in the cases accepts one member",
        module=build,
    ),
    "build_blank_reason_refused": Mutant(
        "a `reason` or `basis` of whitespace alone refused",
        'declarations.md:137 "a `reason` or `basis` is not a string of at least one character"',
        {"DeclarationCheck.texts": texts_refusing_blanks},
        "no case holds a `reason` of whitespace alone",
        module=build,
    ),
    "build_empty_condition_reason_is_item_3": Mutant(
        "an empty `reason` on a requirement condition refused as item 3, BC-004, not as BC-048",
        'declarations.md:188-189 "(an empty `reason` breaks its row\'s Holds, BC-048)"',
        {"DeclarationCheck.requirement_condition": empty_condition_reason_as_item_3},
        "no case holds a requirement condition with an empty `reason`",
        module=build,
    ),
    "build_population_level_shape_unchecked": Mutant(
        "a requirement's `population_level` of another shape taken",
        'declarations.md:64 "`{"level", "within"}` as in `uncertainty.md` section 1"',
        {"DeclarationCheck.population_level": population_level_shape_unchecked},
        module=build,
    ),
    "build_represents_token_unchecked": Mutant(
        "a requirement's `represents` holding any string taken",
        'declarations.md:108 "a token of `uncertainty.md` section 1"',
        {"REPRESENTS": EVERY_STRING},
        module=build,
    ),
    "build_waiver_label_beside_an_unregistered_field_not_judged": Mutant(
        "a waiver's `label` beside a `field` that is not registered not refused by item 4",
        "OPEN_POINTS: waiver_label_beside_an_unregistered_field",
        {
            "DeclarationCheck.waiver": waiver_dropping(
                lambda fault, pointer, name: name is None and "BC-050" in fault.rules
            )
        },
        "no case holds a waiver's `label` beside an unregistered `field`",
        module=build,
    ),
    "build_precision_unchecked": Mutant(
        "a `precision` holding any string taken",
        'declarations.md:102 "where the model evaluates tables or parameter sets (item 10) | `binary32` or '
        '`binary64`"',
        {"PRECISIONS": EVERY_STRING},
        "every `precision` in the cases is a token of the text's",
        module=build,
    ),
    "build_consumer_parameters_unchecked": Mutant(
        "a `consumer_parameters` entry that is no string taken",
        'declarations.md:94 "| | `consumer_parameters` | yes, `[]` allowed | strings |"',
        {
            "DeclarationCheck.model_entry": faults_dropped(
                _build_model_entry, not_at(r"/consumer_parameters/\d+$")
            )
        },
        module=build,
    ),
}
