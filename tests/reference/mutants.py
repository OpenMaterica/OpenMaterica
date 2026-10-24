# SPDX-License-Identifier: Apache-2.0
"""Seeded faults of the reference model, each one rule of the text broken, run against every case file
(`test_seeded_faults.py`). A fault the cases kill is a rule they pin; one that survives is a rule no case
pins, which the properties of S2a-4's phase B must kill. The table, with what each one's search found, is
`README.md`'s.

Each fault replaces one to three of the model's module-level names, which the model looks up when it runs."""

import dataclasses
import math
from collections.abc import Generator, Iterable, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from fractions import Fraction
from unittest import mock

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
from tests.reference.strict_json import JsonObject, JsonValue, NotStrictJson


@dataclass(frozen=True)
class Mutant:
    fault: str
    rule: str  # where the text states the rule the fault breaks
    patches: Mapping[str, object]
    survives: str | None = None  # why no case file kills it, for one none does

    @contextmanager
    def applied(self) -> Generator[None, None, None]:
        with ExitStack() as stack:
            for name, replacement in self.patches.items():
                stack.enter_context(mock.patch.object(model, name, replacement))
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
        'declarations.md:365-367 "An implied condition never overrides a stated condition"',
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
        'declarations.md:357 "`law` (text of at least one character, which a reader does not judge)"',
        {"is_law": any_string_a_law},
    ),
    "white_space_law_refused": Mutant(
        "a `law` of white space refused",
        'declarations.md:357 "`law` (text of at least one character, which a reader does not judge)"',
        {"is_law": white_space_no_law},
    ),
    "extrapolation_method_unchecked": Mutant(
        "an extrapolation's `method` unchecked",
        'declarations.md:357 "`method` (`constant` or `consumer_law`)"',
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
