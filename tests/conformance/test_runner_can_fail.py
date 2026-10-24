# SPDX-License-Identifier: Apache-2.0
"""Broken implementations, one fault each: every one must fail at least one real case, the named one included.

Faults inside a function are injected by replacing that function for the test, so that the rest of the
implementation stays the one under test.
"""

import copy
import hashlib
import math
import re
import unicodedata
from collections.abc import Callable, Collection, Iterable
from dataclasses import replace
from typing import NamedTuple

import pytest

from materica import shapes
from materica.core import (
    canonical,
    declarations,
    envelope,
    fields,
    hashing,
    jsonio,
    read,
    record,
    resolve,
    value_shapes,
)
from materica.core.fields import RecordField
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.reasons import Reason
from materica.core.record import Record, RecordStore
from materica.core.report import BuildRefusal
from materica.core.resolve import Refused, ResolvedRecord
from materica.core.slips import one_slip
from materica.core.vocabulary import VOCABULARY, ConditionSpec, RecordFieldSpec
from materica.shapes import Suite
from tests.conformance import runner
from tests.conformance.runner import (
    CONFIGURATIONS,
    EVALUATOR_CLAIMS,
    EXECUTORS,
    CaseFile,
    EvaluatorClaim,
    EvaluatorPrecision,
    Executor,
    JsonObject,
    Outcome,
    TableEvaluator,
)
from tests.property import test_alternatives_mutants as alternatives_mutants
from tests.property import test_table_alternatives_mutants as table_alternatives_mutants
from tests.property.support import Searched
from tests.reference import table_evaluator
from tests.reference.table_evaluator import REFUSED, Evaluation, Side, Table

CASE_FILES = {case_file.path.name: case_file for case_file in runner.discover()}

# A broken implementation: the executor of the operation its catcher runs, after any faults are injected.
Fault = Callable[[pytest.MonkeyPatch], Executor]


def keeps_card(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def digest(value: JsonValue) -> str:
        view = hashing.hashable_view(value)
        if isinstance(value, dict) and isinstance(view, dict) and "card" in value:
            view["card"] = value["card"]
        return "sha256:" + hashlib.sha256(canonical.canonicalize(view)).hexdigest()

    return runner.content_hash_executor(digest=digest)


def removes_review_outside_provenance(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return runner.content_hash_executor(digest=lambda value: hashing.content_hash(_without(value, "review")))


def orders_names_by_code_point(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def code_points(name: str) -> str:
        return name

    monkeypatch.setattr(canonical, "_utf16_units", code_points)
    return runner.content_hash_executor()


def orders_names_by_utf8_bytes(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def utf8_bytes(name: str) -> bytes:
        return name.encode("utf-8")

    monkeypatch.setattr(canonical, "_utf16_units", utf8_bytes)
    return runner.content_hash_executor()


def normalises_strings_to_nfc(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return runner.content_hash_executor(digest=lambda value: hashing.content_hash(_nfc(value)))


def formats_numbers_with_repr(monkeypatch: pytest.MonkeyPatch) -> Executor:
    monkeypatch.setattr(canonical, "_number", repr)
    return runner.content_hash_executor()


def accepts_repeated_names(monkeypatch: pytest.MonkeyPatch) -> Executor:
    monkeypatch.setattr(jsonio, "_object", dict)
    return runner.content_hash_executor()


def counts_scalars_in_depth(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def parse(data: bytes) -> JsonValue | Reason:
        value = jsonio.parse(data)
        if not isinstance(value, Reason) and _depth_counting_scalars(value) > jsonio.MAX_DEPTH:
            return Reason("malformed")
        return value

    return runner.content_hash_executor(parse=parse)


def answers_a_constant(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def execute(case_file: runner.CaseFile, claims: frozenset[Suite]) -> JsonObject:
        return {"status": "met", "reasons": [], "value": "sha256:" + "0" * 64}

    return execute


# Reads and listings with one fault: the core's own code, with one function replaced.


def ignores_unreadable_sources(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def no_unreadable_source(self: RecordStore) -> list[tuple[str, Reason]]:
        return []

    monkeypatch.setattr(RecordStore, "unparsed", no_unreadable_source)
    return EXECUTORS["read"]


def counts_documents_as_unreadable(monkeypatch: pytest.MonkeyPatch) -> Executor:
    add = RecordStore.add

    def add_document_as_unreadable(self: RecordStore, source: str, data: bytes) -> None:
        value = jsonio.parse(data)
        if isinstance(value, dict) and "document_type" in value and "record_type" not in value:
            data = b"[]"  # parses to no record, so the source is unreadable
        add(self, source, data)

    monkeypatch.setattr(RecordStore, "add", add_document_as_unreadable)
    return EXECUTORS["read"]


def reads_the_first_of_copies_that_differ(monkeypatch: pytest.MonkeyPatch) -> Executor:
    candidate = resolve._candidate  # pyright: ignore[reportPrivateUsage]  # the function the fault replaces

    def first_pinned(ref: MaterialRef, store: RecordStore) -> Record | Reason:
        pinned = [
            copy
            for copy in store.get(ref.id, ref.version)
            if copy.value.get("content_hash") == ref.content_hash
        ]
        return pinned[0] if pinned else candidate(ref, store)

    monkeypatch.setattr(resolve, "_candidate", first_pinned)
    return EXECUTORS["read"]


def searches_the_id_pattern(monkeypatch: pytest.MonkeyPatch) -> Executor:
    patterns = envelope._PATTERNS  # pyright: ignore[reportPrivateUsage]  # the table the fault changes
    monkeypatch.setitem(patterns, "id", Searched(patterns["id"]))  # pyright: ignore[reportArgumentType]  # a duck-typed pattern
    return EXECUTORS["read"]


def refuses_another_patch(monkeypatch: pytest.MonkeyPatch) -> Executor:
    refusal = vars(Record)["version_refusal"].func  # the cached_property's own function

    def same_patch_only(self: Record) -> Reason | None:
        found = refusal(self)
        return Reason("other_version") if found is None and self.value["schema_version"] != "0.1.0" else found

    monkeypatch.setattr(Record, "version_refusal", property(same_patch_only))
    return EXECUTORS["list_records"]


def lists_interfaces(monkeypatch: pytest.MonkeyPatch) -> Executor:
    monkeypatch.setattr(record, "READABLE_TYPES", ("material", "overlay", "interface"))
    return EXECUTORS["list_records"]


def lists_broken_envelopes(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def no_refusal(self: Record) -> Reason | None:
        return None

    monkeypatch.setattr(Record, "envelope_refusal", property(no_refusal))
    return EXECUTORS["list_records"]


def hash_not_recomputed(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def stated_hash(value: JsonValue) -> str:
        assert isinstance(value, dict)
        return str(value["content_hash"])

    monkeypatch.setattr(resolve, "content_hash", stated_hash)
    return EXECUTORS["read"]


def checks_the_type_before_the_hash(monkeypatch: pytest.MonkeyPatch) -> Executor:
    resolve_record = resolve.resolve_record

    def type_first(
        ref: MaterialRef, store: RecordStore, claims: Collection[Suite]
    ) -> ResolvedRecord | Refused:
        resolved = resolve_record(ref, store, ())
        if isinstance(resolved, Refused) and resolved.reasons[0].code == "unknown_type":
            return Refused(resolved.reasons)
        return resolve_record(ref, store, claims)

    monkeypatch.setattr(read, "resolve_record", type_first)
    return EXECUTORS["read"]


def labels_every_result_without_the_hash_suite(monkeypatch: pytest.MonkeyPatch) -> Executor:
    resolve_record = resolve.resolve_record

    def labelled(ref: MaterialRef, store: RecordStore, claims: Collection[Suite]) -> ResolvedRecord | Refused:
        resolved = resolve_record(ref, store, claims)
        if isinstance(resolved, Refused) and "hash" not in claims:
            return Refused(resolved.reasons, ("hash_not_checked",))
        return resolved

    monkeypatch.setattr(read, "resolve_record", labelled)
    return EXECUTORS["read"]


def normalises_units(monkeypatch: pytest.MonkeyPatch) -> Executor:
    unit = read._unit  # pyright: ignore[reportPrivateUsage]  # the function the fault replaces

    def normalised(
        spec: ConditionSpec, entry: dict[str, JsonValue], where: str, found: list[Reason]
    ) -> str | None:
        written = entry.get("unit")
        if isinstance(written, str):
            entry = {**entry, "unit": unicodedata.normalize("NFKC", written)}
        return unit(spec, entry, where, found)

    monkeypatch.setattr(read, "_unit", normalised)
    return EXECUTORS["read"]


def refuses_unnamed_members(monkeypatch: pytest.MonkeyPatch) -> Executor:
    target = read._target  # pyright: ignore[reportPrivateUsage]  # the function the fault replaces

    def strict(value: JsonValue, found: list[Reason]) -> tuple[MaterialRef, str] | None:
        if isinstance(value, dict) and set(value) - {"record", "field"}:
            found.append(Reason("request_incomplete", detail="a member the shape does not name"))
        return target(value, found)

    monkeypatch.setattr(read, "_target", strict)
    return EXECUTORS["read"]


def repeats_reasons(monkeypatch: pytest.MonkeyPatch) -> Executor:
    monkeypatch.setattr(read, "merged", tuple)
    return EXECUTORS["read"]


def ignores_the_suite_of_a_want(monkeypatch: pytest.MonkeyPatch) -> Executor:
    monkeypatch.setattr(read, "_WANT_SUITES", {})
    return EXECUTORS["read"]


def refuses_a_tolerance_of_minus_zero(monkeypatch: pytest.MonkeyPatch) -> Executor:
    condition = read._requirement_condition  # pyright: ignore[reportPrivateUsage]  # the function the fault replaces

    def signed(name: str, entry: JsonValue, operated: bool, found: list[Reason]) -> object:
        tolerance = entry.get("tolerance") if isinstance(entry, dict) else None
        value = tolerance.get("value") if isinstance(tolerance, dict) else None
        if isinstance(value, float) and math.copysign(1.0, value) < 0:
            found.append(Reason("request_incomplete", name, "below zero"))
        return condition(name, entry, operated, found)

    monkeypatch.setattr(read, "_requirement_condition", signed)
    return EXECUTORS["read"]


# Step 8 with one fault: a check of `value_shapes` or `fields` left out, loosened or stopped early.


def ignores_slips(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def none_slipped(members: Iterable[str], named: Collection[str]) -> list[tuple[str, str]]:
        return []

    monkeypatch.setattr(value_shapes, "slipped", none_slipped)
    return EXECUTORS["read"]


def ignores_members_beside_a_status(monkeypatch: pytest.MonkeyPatch) -> Executor:
    status_object = value_shapes.status_object

    def only_status_and_reason(
        value: dict[str, JsonValue],
        where: str,
        tokens: Collection[str] | None,
        defines: Collection[str],
        found: list[Reason],
    ) -> None:
        kept = {name: member for name, member in value.items() if name in ("status", "reason")}
        status_object(kept, where, tokens, defines, found)

    monkeypatch.setattr(value_shapes, "status_object", only_status_and_reason)
    return EXECUTORS["read"]


def knows_no_token_of_another_member(monkeypatch: pytest.MonkeyPatch) -> Executor:
    monkeypatch.setattr(value_shapes, "KNOWN", {member: frozenset[str]() for member in value_shapes.KNOWN})
    return EXECUTORS["read"]


def _ignoring_the_other_kind(
    monkeypatch: pytest.MonkeyPatch, shapes_of: Collection[str], *, exact: bool, slips: bool
) -> Executor:
    """A read that ignores, in a condition of a shape among `shapes_of`, the members of the other kind's
    shape (`exact`) or a slip of one (`slips`), as S2a-2's step 8 did before the maintainer's ruling of
    2026-10-19 (`provenance.md` section 6.1 item 1)."""
    conditions = value_shapes.conditions
    shaped = {name for name, spec in VOCABULARY.conditions.items() if spec.shape in shapes_of}

    def ignored(name: str, held: str) -> bool:
        other = value_shapes.OF_THE_OTHER_KIND[VOCABULARY.conditions[name].shape]
        return (exact and held in other) or (
            slips and held not in other and any(one_slip(held, member) for member in other)
        )

    def ignoring(value: JsonValue, where: str, found: list[Reason]) -> None:
        if isinstance(value, dict):
            value = {
                name: {held: member for held, member in entry.items() if not ignored(name, held)}
                if isinstance(entry, dict) and name in shaped
                else entry
                for name, entry in value.items()
            }
        conditions(value, where, found)

    monkeypatch.setattr(value_shapes, "conditions", ignoring)
    return EXECUTORS["read"]


def ignores_a_numeric_conditions_token(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return _ignoring_the_other_kind(monkeypatch, ("numeric",), exact=True, slips=True)


def ignores_a_token_conditions_numeric_members(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return _ignoring_the_other_kind(monkeypatch, ("token",), exact=True, slips=True)


def ignores_a_slip_of_the_other_kinds_member(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return _ignoring_the_other_kind(monkeypatch, ("numeric", "token"), exact=False, slips=True)


def _each_condition(
    monkeypatch: pytest.MonkeyPatch,
    checked: Callable[[value_shapes.Check, Collection[str]], value_shapes.Check],
) -> Executor:
    """A read whose step 8 checks each condition it knows through `checked`, given the condition's own check
    and the members of the other kind of condition's shape."""
    monkeypatch.setattr(
        value_shapes,
        "CONDITIONS",
        {
            name: checked(check, value_shapes.OF_THE_OTHER_KIND[VOCABULARY.conditions[name].shape])
            for name, check in value_shapes.CONDITIONS.items()
        },
    )
    return EXECUTORS["read"]


def _ignoring_the_other_kind_holding(
    monkeypatch: pytest.MonkeyPatch, holding: Callable[[JsonValue], bool]
) -> Executor:
    """A read that refuses a member of the other kind of condition's shape only where it holds a value
    `holding` does not take, against "whatever that member holds" (`provenance.md` section 6.1 item 1)."""

    def ignoring(check: value_shapes.Check, other: Collection[str]) -> value_shapes.Check:
        def checked(value: JsonValue, where: str, found: value_shapes.Found) -> None:
            if isinstance(value, dict):
                value = {name: held for name, held in value.items() if not (name in other and holding(held))}
            check(value, where, found)

        return checked

    return _each_condition(monkeypatch, ignoring)


def ignores_the_other_kinds_member_holding_an_object(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return _ignoring_the_other_kind_holding(monkeypatch, lambda held: isinstance(held, dict))


def ignores_the_other_kinds_member_holding_null(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return _ignoring_the_other_kind_holding(monkeypatch, lambda held: held is None)


def reads_nothing_else_beside_the_other_kind(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """A condition holding a member of the other kind of condition's shape refused for that alone, as a status
    object that breaks its shape is (`provenance.md` section 1), where step 8 makes all its checks
    (`read_side_contract.md` section 2 item 2) and the sentence that refuses the member makes no exception."""

    def refusing(check: value_shapes.Check, other: Collection[str]) -> value_shapes.Check:
        def checked(value: JsonValue, where: str, found: value_shapes.Found) -> None:
            held = [name for name in other if isinstance(value, dict) and name in value]
            if not held:
                check(value, where, found)
            found.extend(
                value_shapes.invalid(
                    f"{where} holds {name!r}, a member of the other kind of condition's shape"
                )
                for name in held
            )

        return checked

    return _each_condition(monkeypatch, refusing)


def names_no_alternatives_at_a_field(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """`alternatives` not named at a field's place beside the value field's members, so a slip of it there is
    ignored (`record_format.md` section 5, and the maintainer's ruling of 2026-10-19)."""
    slips = value_shapes.slips

    def without_alternatives(
        value: dict[str, JsonValue], named: Collection[str], where: str, found: list[Reason]
    ) -> None:
        slips(value, [name for name in named if name != "alternatives"], where, found)

    monkeypatch.setattr(value_shapes, "slips", without_alternatives)
    return EXECUTORS["read"]


def leaves_the_section_unchecked(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def nothing(name: str, section: dict[str, JsonValue]) -> list[Reason]:
        return []

    monkeypatch.setattr(fields, "section_problems", nothing)
    return EXECUTORS["read"]


def allows_every_form(monkeypatch: pytest.MonkeyPatch) -> Executor:
    form = fields._form  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def unregistered_too(
        field: dict[str, JsonValue], spec: RecordFieldSpec, claims: Collection[Suite], found: list[Reason]
    ) -> tuple[str | None, bool]:
        own: list[Reason] = []
        found_form, _ = form(field, spec, claims, own)
        found += [reason for reason in own if reason.code != "form_not_registered"]
        return found_form, found_form is not None

    monkeypatch.setattr(fields, "_form", unregistered_too)
    return EXECUTORS["read"]


def reads_null_as_absent(monkeypatch: pytest.MonkeyPatch) -> Executor:
    members = value_shapes.members

    def without_nulls(
        value: JsonValue,
        where: str,
        found: list[Reason],
        required: value_shapes.Members,
        optional: value_shapes.Members | None = None,
        *,
        named: Collection[str] = (),
    ) -> dict[str, JsonValue] | None:
        if isinstance(value, dict):
            value = {name: member for name, member in value.items() if member is not None}
        return members(value, where, found, required, optional, named=named)

    monkeypatch.setattr(value_shapes, "members", without_nulls)
    return EXECUTORS["read"]


def reads_a_withheld_value(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def no_member_check(field: dict[str, JsonValue], name: str, form: str, found: list[Reason]) -> None:
        pass

    monkeypatch.setattr(fields, "_own_member", no_member_check)
    return EXECUTORS["read"]


def stops_at_the_first_refusal(monkeypatch: pytest.MonkeyPatch) -> Executor:
    form_problems = fields.form_problems

    def first(
        field: RecordField, record_value: dict[str, JsonValue], claims: Collection[Suite]
    ) -> list[Reason]:
        return form_problems(field, record_value, claims)[:1]

    monkeypatch.setattr(read, "form_problems", first)
    return EXECUTORS["read"]


def returns_bounds_without_their_basis(monkeypatch: pytest.MonkeyPatch) -> Executor:
    counted_member = read._counted_member  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def bare(member: JsonValue) -> JsonValue:
        returned = counted_member(member)
        if isinstance(returned, dict) and "lower" in returned:
            return {name: bound for name, bound in returned.items() if name != "basis"}
        return returned

    monkeypatch.setattr(read, "_counted_member", bare)
    return EXECUTORS["read"]


def reads_an_upper_none_as_the_largest_double(monkeypatch: pytest.MonkeyPatch) -> Executor:
    counted_member = read._counted_member  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def unbounded(member: JsonValue) -> JsonValue:
        returned = counted_member(member)
        if isinstance(returned, dict) and returned.get("upper") == {"status": "none"}:
            return {**returned, "upper": 1.7976931348623157e308}
        return returned

    monkeypatch.setattr(read, "_counted_member", unbounded)
    return EXECUTORS["read"]


def normalises_components(monkeypatch: pytest.MonkeyPatch) -> Executor:
    counted_member = read._counted_member  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def normalised(member: JsonValue) -> JsonValue:
        returned = counted_member(member)
        if not (isinstance(returned, dict) and isinstance(stored := returned.get("components"), list)):
            return returned
        components = [component for component in stored if isinstance(component, dict)]
        total = math.fsum(float(str(component["fraction"])) for component in components)
        for component in components:
            component["fraction"] = float(str(component["fraction"])) / total
        return {name: kept for name, kept in returned.items() if name != "stated_sum"}

    monkeypatch.setattr(read, "_counted_member", normalised)
    return EXECUTORS["read"]


def takes_bounds_out_of_order(monkeypatch: pytest.MonkeyPatch) -> Executor:
    interval = fields.OWN_MEMBERS["interval"]

    def ordered_first(value: JsonValue, where: str, found: list[Reason]) -> None:
        if isinstance(value, dict) and isinstance(value.get("lower"), float):
            lower, upper = value["lower"], value.get("upper")
            if isinstance(lower, float) and isinstance(upper, float) and lower > upper:
                value = {**value, "lower": upper, "upper": lower}
        interval(value, where, found)

    monkeypatch.setitem(fields.OWN_MEMBERS, "interval", ordered_first)
    return EXECUTORS["read"]


def takes_a_component_twice(monkeypatch: pytest.MonkeyPatch) -> Executor:
    composition = fields.OWN_MEMBERS["composition"]

    def each_once(value: JsonValue, where: str, found: list[Reason]) -> None:
        if isinstance(value, dict) and isinstance(stored := value.get("components"), list):
            kept = {
                str(component.get("component")): component
                for component in stored
                if isinstance(component, dict)
            }
            value = {**value, "components": list(kept.values())}
        composition(value, where, found)

    monkeypatch.setitem(fields.OWN_MEMBERS, "composition", each_once)
    return EXECUTORS["read"]


def reads_every_report_withheld_as_some(monkeypatch: pytest.MonkeyPatch) -> Executor:
    evidence = fields.OWN_MEMBERS["evidence"]

    def some(value: JsonValue, where: str, found: list[Reason]) -> None:
        evidence(value, where, found)
        found[:] = [Reason("entries_withheld") if reason.code == "withheld" else reason for reason in found]

    monkeypatch.setitem(fields.OWN_MEMBERS, "evidence", some)
    return EXECUTORS["read"]


def withholds_a_list_for_one_report(monkeypatch: pytest.MonkeyPatch) -> Executor:
    evidence = fields.OWN_MEMBERS["evidence"]

    def whole(value: JsonValue, where: str, found: list[Reason]) -> None:
        evidence(value, where, found)
        found[:] = [Reason("withheld") if reason.code == "entries_withheld" else reason for reason in found]

    monkeypatch.setitem(fields.OWN_MEMBERS, "evidence", whole)
    return EXECUTORS["read"]


def takes_a_report_withheld_in_part(monkeypatch: pytest.MonkeyPatch) -> Executor:
    evidence_entry = fields.evidence_entry

    def in_part(value: JsonValue, where: str, found: list[Reason]) -> bool:
        own: list[Reason] = []
        withheld = evidence_entry(value, where, own)
        found += [reason for reason in own if "withholding" not in (reason.detail or "")]
        return withheld

    monkeypatch.setattr(fields, "evidence_entry", in_part)
    return EXECUTORS["read"]


def takes_a_registered_condition_under_evidence(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def none(conditions: JsonValue, where: str, found: list[Reason]) -> None:
        pass

    monkeypatch.setattr(fields, "_no_registered_condition", none)
    return EXECUTORS["read"]


def cuts_a_reports_provenance_to_a_results(monkeypatch: pytest.MonkeyPatch) -> Executor:
    returned = read._returned  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def cut(value: JsonValue, shape: object) -> JsonValue:
        found = returned(value, shape)
        if shape is shapes.Provenance and isinstance(found, dict):
            return {name: member for name, member in found.items() if name in ("origin", "review")}
        return found

    monkeypatch.setattr(read, "_returned", cut)
    return EXECUTORS["read"]


def _per_parameter_returned(
    monkeypatch: pytest.MonkeyPatch, changed: Callable[[JsonObject, JsonObject], None]
) -> Executor:
    """A read whose provenance returned whole hands each provenance its `per_parameter` maps a parameter to,
    as returned and as stored, to `changed`."""
    returned = read._returned  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def per_parameter(value: JsonValue, shape: object) -> JsonValue:
        found = returned(value, shape)
        if shape is shapes.Provenance and isinstance(value, dict) and isinstance(found, dict):
            stored, mapped = value.get("per_parameter"), found.get("per_parameter")
            if isinstance(stored, dict) and isinstance(mapped, dict):
                for name, held in stored.items():
                    nested = mapped.get(name)
                    if isinstance(held, dict) and isinstance(nested, dict):
                        changed(nested, held)
        return found

    monkeypatch.setattr(read, "_returned", per_parameter)
    return EXECUTORS["read"]


def returns_a_nested_review_as_found(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """A review inside a provenance `per_parameter` maps a parameter to returned as stored, against
    `record_format.md` section 4.3 item 2 (the maintainer's ruling of 2026-10-20)."""

    def as_found(nested: JsonObject, stored: JsonObject) -> None:
        if "review" in stored:
            nested["review"] = copy.deepcopy(stored["review"])

    return _per_parameter_returned(monkeypatch, as_found)


def returns_no_nested_review_where_none_is_held(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """A provenance `per_parameter` maps a parameter to, holding no review, returned with none, against
    `record_format.md` section 4.3 item 2 (the maintainer's ruling of 2026-10-20)."""

    def none_held(nested: JsonObject, stored: JsonObject) -> None:
        if "review" not in stored:
            nested.pop("review", None)

    return _per_parameter_returned(monkeypatch, none_held)


def leaves_a_reports_provenance_unchecked(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def unchecked(value: JsonValue, where: str, found: list[Reason]) -> None:
        pass

    monkeypatch.setattr(fields, "provenance", unchecked)
    return EXECUTORS["read"]


def checks_every_member_of_a_reports_provenance(monkeypatch: pytest.MonkeyPatch) -> Executor:
    checked = value_shapes.provenance  # the check `fields` imports, which the fault wraps

    def every_member(value: JsonValue, where: str, found: list[Reason]) -> None:
        checked(value, where, found)
        if isinstance(value, dict) and not isinstance(value.get("extraction", {}), dict):
            found.append(value_shapes.invalid(f"{where}.extraction is not an object"))

    monkeypatch.setattr(fields, "provenance", every_member)
    return EXECUTORS["read"]


def applies_a_nominal_outside_its_bounds(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def anywhere(
        interval: JsonObject, name: str, nominal: read.Nominal
    ) -> tuple[Reason, read.Nominal | None]:
        return Reason("want_mismatch"), nominal

    monkeypatch.setattr(read, "_nominal_read", anywhere)
    return EXECUTORS["read"]


def drops_a_nominals_value_under_not_met(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def unless_not_met(status: str, found: read.FieldRead) -> bool:
        return found.value is not None and status != "not_met"

    monkeypatch.setattr(read, "_value_returned", unless_not_met)
    return EXECUTORS["read"]


def applies_a_nominal_wherever_it_is_located(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def by_field(named: str, location: JsonObject, field: str, target: MaterialRef) -> bool:
        return named == field

    monkeypatch.setattr(read, "located_at", by_field)
    return EXECUTORS["read"]


def takes_two_nominals_for_one_field(monkeypatch: pytest.MonkeyPatch) -> Executor:
    acceptances = read._acceptances  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def one_each(entries: list[JsonValue], found: list[Reason]) -> object:
        own: list[Reason] = []
        checked = acceptances(entries, own)
        found += [reason for reason in own if "two nominals" not in (reason.detail or "")]
        return checked

    monkeypatch.setattr(read, "_acceptances", one_each)
    return EXECUTORS["read"]


def takes_params_in_place_of_a_value(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """A nominal holding `params` and no `value` passes step 0, whatever row its field has, and is never
    applied: reading B of S2b-2's review, M56, which the maintainer ruled out (2026-10-19)."""
    nominal = read._nominal  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def without_a_value(index: int, entry: dict[str, JsonValue], found: list[Reason]) -> object:
        if "params" in entry and "value" not in entry:
            return None
        return nominal(index, entry, found)

    monkeypatch.setattr(read, "_nominal", without_a_value)
    return EXECUTORS["read"]


def ignores_a_waiver(monkeypatch: pytest.MonkeyPatch) -> Executor:
    acceptances = read._acceptances  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def without_waivers(entries: list[JsonValue], found: list[Reason]) -> object:
        kept: list[JsonValue] = [
            entry
            for entry in entries
            if not (isinstance(entry, dict) and entry.get("acceptance") == "waiver")
        ]
        return acceptances(kept, found)

    monkeypatch.setattr(read, "_acceptances", without_waivers)
    return EXECUTORS["read"]


def compares_a_nominal_under_no_pick(monkeypatch: pytest.MonkeyPatch) -> Executor:
    read_alternatives = read._read_alternatives  # pyright: ignore[reportPrivateUsage]  # the function the fault wraps

    def compared(
        field: RecordField,
        record_value: JsonObject,
        request: read.ReadRequest,
        claims: Collection[Suite],
        labels: tuple[str, ...],
        nominal: read.Nominal | None,
    ) -> read.ReadResult:
        result = read_alternatives(field, record_value, request, claims, labels, nominal)
        bounds = [entry.member for entry in result.alternative_values or () if isinstance(entry.member, dict)]
        if nominal is None or not any(
            read._nominal_read(bound, field.spec.name, nominal)[1] is None  # pyright: ignore[reportPrivateUsage]
            for bound in bounds
            if "lower" in bound
        ):
            return result
        return read.ReadResult("not_met", (*result.reasons, Reason("nominal_invalid")), result.labels)

    monkeypatch.setattr(read, "_read_alternatives", compared)
    return EXECUTORS["read"]


# S4a's step 7 (`read_side_contract.md` section 3, step 7), each fault one of S4a's mutants.


def sets_a_refusal_aside(monkeypatch: pytest.MonkeyPatch) -> Executor:
    replaced = alternatives_mutants._refusal_sets_aside  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_standing", replaced)
    return EXECUTORS["read"]


def reports_the_set_aside_beside_the_one_left(monkeypatch: pytest.MonkeyPatch) -> Executor:
    replaced = alternatives_mutants._set_aside_beside_the_one_left  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_read_alternatives", replaced)
    return EXECUTORS["read"]


def leaves_the_one_left_untagged(monkeypatch: pytest.MonkeyPatch) -> Executor:
    replaced = alternatives_mutants._the_one_left_untagged  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_reported_of_the_one_left", replaced)
    return EXECUTORS["read"]


def tags_a_request_fault(monkeypatch: pytest.MonkeyPatch) -> Executor:
    replaced = alternatives_mutants._request_fault_tagged  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_found_reading", replaced)
    return EXECUTORS["read"]


def drops_the_waiting_reasons_where_refused(monkeypatch: pytest.MonkeyPatch) -> Executor:
    replaced = alternatives_mutants._waiting_dropped_where_refused  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_reported_where_refused", replaced)
    return EXECUTORS["read"]


def counts_an_index_among_those_that_stay(monkeypatch: pytest.MonkeyPatch) -> Executor:
    replaced = alternatives_mutants._index_among_those_that_stay  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_read_alternatives", replaced)
    return EXECUTORS["read"]


def takes_the_first_stored_unit(monkeypatch: pytest.MonkeyPatch) -> Executor:
    replaced = alternatives_mutants._the_first_stored_unit  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_read_alternatives", replaced)
    return EXECUTORS["read"]


# S4d's step 7 over a table alternative's reasons at step 11, the S4 cases plan's two broken readers, each
# fault one of S4d's mutants.


def sets_an_edge_aside(monkeypatch: pytest.MonkeyPatch) -> Executor:
    replaced = table_alternatives_mutants._an_edge_sets_aside  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_standing_at_step_11", replaced)
    return EXECUTORS["read"]


def counts_a_read_over_a_range_as_giving(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """`no_pick` where two or more stay and none has a form `want` can give, a table read over an operating
    range of its axis counted as one."""
    replaced = table_alternatives_mutants._over_a_range_gives  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(read, "_gives", replaced)
    return EXECUTORS["read"]


# Builds with one fault: the declaration's own check, with one rule's findings changed (S7a-1). Each fails an
# S7a-1 file.

Rule = Callable[..., list[declarations.Finding]]


def _filtered(
    monkeypatch: pytest.MonkeyPatch, rule: str, drop: Callable[[declarations.Finding, JsonObject], bool]
) -> Executor:
    """The build with the findings of `rule` that `drop` names left out."""
    original: Rule = vars(declarations)[rule]

    def filtered(declaration: JsonObject, *rest: object) -> list[declarations.Finding]:
        return [finding for finding in original(declaration, *rest) if not drop(finding, declaration)]

    monkeypatch.setattr(declarations, rule, filtered)
    return runner.check_build_executor()


def _refusals_changed(
    monkeypatch: pytest.MonkeyPatch, change: Callable[[tuple[BuildRefusal, ...]], tuple[BuildRefusal, ...]]
) -> Executor:
    original: Callable[[list[declarations.Finding]], tuple[BuildRefusal, ...]] = vars(declarations)[
        "_precedence"
    ]

    def precedence(found: list[declarations.Finding]) -> tuple[BuildRefusal, ...]:
        return change(original(found))

    monkeypatch.setattr(declarations, "_precedence", precedence)
    return runner.check_build_executor()


def reason_unchecked(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def no_reasons(declaration: JsonObject) -> list[declarations.Finding]:
        return []

    monkeypatch.setattr(declarations, "_reasons", no_reasons)
    return runner.check_build_executor()


def first_fault_only(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return _refusals_changed(monkeypatch, lambda refusals: refusals[:1])


def unknown_member_ignored(monkeypatch: pytest.MonkeyPatch) -> Executor:
    places: Callable[[JsonObject], Iterable[declarations.Visit]] = vars(declarations)["_places"]
    members_of: Callable[[str], dict[str, declarations.Member]] = vars(declarations)["_members_of"]

    def unknown(finding: declarations.Finding, declaration: JsonObject) -> bool:
        return any(
            finding.pointer == f"{visit.pointer}/{name}"
            for visit in places(declaration)
            for name in visit.value
            if name not in members_of(visit.place)
        )

    return _filtered(monkeypatch, "_shape", unknown)


def scene_accepted(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """A model checked over a domain read as one checked over no records: its domain taken."""
    return _filtered(
        monkeypatch, "_suites", lambda finding, _: finding.pointer.endswith("/checked_over/domain")
    )


def pointer_off_by_one(monkeypatch: pytest.MonkeyPatch) -> Executor:
    def moved(refusal: BuildRefusal) -> BuildRefusal:
        pointer = re.sub(r"^/models/(\d+)", lambda found: f"/models/{int(found[1]) + 1}", refusal.pointer)
        return replace(refusal, pointer=pointer)

    return _refusals_changed(monkeypatch, lambda refusals: tuple(map(moved, refusals)))


def review_token_unchecked(monkeypatch: pytest.MonkeyPatch) -> Executor:
    return _filtered(monkeypatch, "_tokens", lambda finding, _: finding.pointer.endswith("/review"))


def duplicate_requirement_taken(monkeypatch: pytest.MonkeyPatch) -> Executor:
    entry = re.compile(r"/models/\d+/requirements/\d+")
    return _filtered(monkeypatch, "_names", lambda finding, _: entry.fullmatch(finding.pointer) is not None)


def waives_an_unknown_condition_name(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """A waiver whose `code` is `condition_unknown_name` taken, the clause of 2026-10-24 off: that code among
    those a waiver takes."""
    monkeypatch.setitem(declarations.TOKENS, ("waiver", "code"), tuple(VOCABULARY.reasons))
    return runner.check_build_executor()


def takes_basis_on_every_kind(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """`basis` named on a waiver, as the shape table could be read before the ruling of 2026-10-24."""
    basis = next(member for member in declarations.SHAPE["extrapolation"] if member.name == "basis")
    monkeypatch.setitem(declarations.SHAPE, "waiver", (*declarations.SHAPE["waiver"], basis))
    return runner.check_build_executor()


def takes_a_population_level_beside_another_represents(monkeypatch: pytest.MonkeyPatch) -> Executor:
    """The `population_level` rule as it read before the ruling of 2026-10-24: its absence refused beside
    `population`, and its presence beside another `represents` taken."""
    return _filtered(
        monkeypatch, "_suites", lambda finding, _: finding.case == "BC-043" and finding.aspect is None
    )


def _without(value: JsonValue, removed: str) -> JsonValue:
    if isinstance(value, list):
        return [_without(item, removed) for item in value]
    if isinstance(value, dict):
        return {name: _without(member, removed) for name, member in value.items() if name != removed}
    return value


def _nfc(value: JsonValue) -> JsonValue:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc(item) for item in value]
    if isinstance(value, dict):
        return {unicodedata.normalize("NFC", name): _nfc(member) for name, member in value.items()}
    return value


def _depth_counting_scalars(value: JsonValue) -> int:
    if isinstance(value, list):
        return 1 + max((_depth_counting_scalars(item) for item in value), default=0)
    if isinstance(value, dict):
        return 1 + max((_depth_counting_scalars(member) for member in value.values()), default=0)
    return 1


# S7a-1's broken builds, each against the S7a-1 file that catches it (the S7 design's 6.4, and one for each
# rule of the clauses of 2026-10-24).
BUILD_FAULTS: list[tuple[Fault, str]] = [
    (reason_unchecked, "BC-005.waiver_without_reason.json"),
    (first_fault_only, "BC-004.two_models_both_listed.json"),
    (unknown_member_ignored, "BC-048.slip_acceptance_for_acceptances.json"),
    (scene_accepted, "BC-051.checked_over_domain.json"),
    (pointer_off_by_one, "BC-005.waiver_without_reason.json"),
    (review_token_unchecked, "BC-048.review_not_a_token.json"),
    (duplicate_requirement_taken, "BC-048.two_requirements_for_one_field.json"),
    (waives_an_unknown_condition_name, "BC-048.waiver_of_an_unknown_condition_name.json"),
    (takes_basis_on_every_kind, "BC-048.basis_on_a_waiver.json"),
    (
        takes_a_population_level_beside_another_represents,
        "BC-051.population_level_beside_another_represents.json",
    ),
]
FAULTS: list[tuple[Fault, str]] = [
    (keeps_card, "HS-001.top_level_removed.json"),
    (removes_review_outside_provenance, "HS-001.outside_kept.json"),
    (orders_names_by_code_point, "HS-003.utf16_order_raw.json"),
    (orders_names_by_utf8_bytes, "HS-003.utf16_order_raw.json"),
    (normalises_strings_to_nfc, "HS-003.nfc_decomposed.json"),
    (formats_numbers_with_repr, "HS-003.number_1_0.json"),
    (accepts_repeated_names, "HS-003.malformed_duplicate_name.json"),
    (counts_scalars_in_depth, "HS-003.depth_64_scalar.json"),
    (answers_a_constant, "HS-003.malformed_bom.json"),
    (ignores_unreadable_sources, "PR-328.unparsed_source_malformed.json"),
    (counts_documents_as_unreadable, "PR-328.scene_manifest_absent.json"),
    (reads_the_first_of_copies_that_differ, "PR-329.two_with_hash_card_differs.json"),
    (searches_the_id_pattern, "PR-002.local_id_trailing_newline.json"),
    (refuses_another_patch, "PR-048.patch_0_1_7_listed.json"),
    (lists_interfaces, "PR-006.interface_skipped.json"),
    (lists_broken_envelopes, "PR-004.overlay_missing_name_not_listed.json"),
    (hash_not_recomputed, "HS-010.value_edited.json"),
    (checks_the_type_before_the_hash, "HS-010.type_edited.json"),
    (labels_every_result_without_the_hash_suite, "PR-327.pin_no_hs.json"),
    (normalises_units, "PR-320.operating_unit_kelvin_sign.json"),
    (refuses_unnamed_members, "PR-330.unknown_member_in_target.json"),
    (repeats_reasons, "PR-331.request_incomplete_once_per_condition.json"),
    (ignores_the_suite_of_a_want, "PR-332.fit_without_fd.json"),
    (refuses_a_tolerance_of_minus_zero, "PR-330.tolerance_negative_zero_accepted.json"),
    (ignores_slips, "PR-005.near_typo_crad.json"),
    (ignores_members_beside_a_status, "PR-110.sd_status_beside_other_member.json"),
    (knows_no_token_of_another_member, "PR-045.condition_token_of_another_row.json"),
    (ignores_a_numeric_conditions_token, "PR-045.numeric_condition_holding_token.json"),
    (ignores_a_token_conditions_numeric_members, "PR-045.token_condition_holding_value.json"),
    (ignores_a_slip_of_the_other_kinds_member, "PR-030.near_typo_token_on_numeric_condition.json"),
    (ignores_the_other_kinds_member_holding_an_object, "PR-045.numeric_condition_holding_token_status.json"),
    (ignores_the_other_kinds_member_holding_null, "PR-045.token_condition_holding_value_null.json"),
    (reads_nothing_else_beside_the_other_kind, "PR-301.other_kind_beside_unknown_basis.json"),
    (names_no_alternatives_at_a_field, "PR-030.near_typo_alternative_beside_constant.json"),
    (leaves_the_section_unchecked, "PR-045.section_specimen_fault_refuses_section.json"),
    (allows_every_form, "PR-036.power_law_on_bulk_density.json"),
    (reads_null_as_absent, "PR-049.field_specimen_null.json"),
    (reads_a_withheld_value, "PR-105.withheld_value.json"),
    (stops_at_the_first_refusal, "PR-301.two_refusals_step_8.json"),
    (returns_bounds_without_their_basis, "PR-022.bounds_reported_range.json"),
    (reads_an_upper_none_as_the_largest_double, "PR-022.bounds_one_sided_upper_none.json"),
    (normalises_components, "PR-023.components_stated_sum.json"),
    (takes_bounds_out_of_order, "PR-050.lower_above_upper.json"),
    (takes_a_component_twice, "PR-051.repeated_component.json"),
    (reads_every_report_withheld_as_some, "PR-052.every_entry_withheld.json"),
    (withholds_a_list_for_one_report, "PR-052.some_entries_withheld.json"),
    (takes_a_report_withheld_in_part, "PR-052.entry_partly_withheld.json"),
    (takes_a_registered_condition_under_evidence, "PR-052.registered_condition_in_conditions.json"),
    (cuts_a_reports_provenance_to_a_results, "PR-038.evidence_list.json"),
    (leaves_a_reports_provenance_unchecked, "PR-052.entry_provenance_origin_unknown.json"),
    (checks_every_member_of_a_reports_provenance, "PR-052.entry_provenance_extraction_number.json"),
    (returns_a_nested_review_as_found, "PR-052.entry_provenance_per_parameter_review_unknown.json"),
    (returns_no_nested_review_where_none_is_held, "PR-052.entry_provenance_per_parameter_review_absent.json"),
    (applies_a_nominal_outside_its_bounds, "PR-338.nominal_outside.json"),
    (drops_a_nominals_value_under_not_met, "PR-302.nominal_value_under_not_met.json"),
    (applies_a_nominal_wherever_it_is_located, "PR-338.nominal_other_record.json"),
    (takes_two_nominals_for_one_field, "PR-330.two_nominals_one_field.json"),
    (takes_params_in_place_of_a_value, "PR-330.nominal_params_in_place_of_value.json"),
    (ignores_a_waiver, "PR-310.waiver_refused.json"),
    (compares_a_nominal_under_no_pick, "PR-338.no_pick_nominal_outside_not_reported.json"),
    (sets_a_refusal_aside, "PR-044.refused_reports_waiting_want_mismatch.json"),
    (reports_the_set_aside_beside_the_one_left, "PR-044.one_left_after_set_aside.json"),
    (leaves_the_one_left_untagged, "PR-044.one_left_after_set_aside.json"),
    (tags_a_request_fault, "PR-316.implied_two_disagree_in_alternative_beside_reasons.json"),
    (drops_the_waiting_reasons_where_refused, "PR-044.refused_reports_waiting_want_mismatch.json"),
    (counts_an_index_among_those_that_stay, "PR-013.index_past_set_aside_and_unknown_reasons.json"),
    (takes_the_first_stored_unit, "PR-013.evidence_unit_of_the_first_that_stays.json"),
    (sets_an_edge_aside, "PR-044.at_edge_under_extrapolation_refuses.json"),
    (counts_a_read_over_a_range_as_giving, "PR-013.two_tables_over_operating_range_want_mismatch.json"),
    *BUILD_FAULTS,
]
# S4d's broken readers fail S4d's case files alone: each pins a rule no earlier piece's case file reads.
S4D_FAULTS = (sets_an_edge_aside, counts_a_read_over_a_range_as_giving)


# Broken evaluators of a table, one fault each: the S3 design's section 6.4, and those the suite's README
# names besides. Each is the reference evaluator with its answer changed or one of its functions replaced,
# and claims every precision and side unless it says otherwise.
EvaluatorFault = Callable[[pytest.MonkeyPatch], TableEvaluator]


def reference(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
    return table_evaluator.evaluate(table, at, precision, side)


def only_clamps(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """`in_range` always true, with the end value outside the range."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        return found if found.refused else replace(found, in_range=True)

    return evaluate


def takes_in_range_strictly(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """`in_range` by `<` at the ends: at an end of the readable range, false, with the end value and 0."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        if found.in_range and at in table_evaluator.readable_range(table):
            return Evaluation(refused=False, in_range=False, value=found.value, derivative=0.0)
        return found

    return evaluate


def ignores_a_narrower_source_range(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """The readable range from `x` alone."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        return reference(replace(table, source_range=None), at, precision, side)

    return evaluate


def returns_the_side_it_did_not_declare(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        return reference(table, at, precision, "left" if side == "right" else "right")

    return evaluate


def gives_the_outside_derivative_at_an_end(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """At an end of the readable range, the derivative from outside it: zero."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        if found.in_range and at in table_evaluator.readable_range(table):
            return replace(found, derivative=0.0)
        return found

    return evaluate


def read_from_above(table: Table, edge: float, precision: EvaluatorPrecision) -> Evaluation:
    """The evaluation at `edge` from the interval above it: the table without the edge's lower knot, which
    then declares no edge there, read with the right-hand derivative."""
    lower = table.x.index(edge)
    above = replace(
        table,
        x=table.x[:lower] + table.x[lower + 1 :],
        y=table.y[:lower] + table.y[lower + 1 :],
        edges=tuple(other for other in table.edges if other != edge),
    )
    return reference(above, edge, precision, "right")


def reads_an_edge_from_the_interval_above(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        return (
            read_from_above(table, at, precision)
            if at in table.edges
            else reference(table, at, precision, side)
        )

    return evaluate


def refuses_an_edge_beside_the_interval_above(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """At an edge, the refusal reported, and the value and derivative of the interval above returned."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        if at not in table.edges:
            return found
        above = read_from_above(table, at, precision)
        return replace(found, value=above.value, derivative=above.derivative)

    return evaluate


def refuses_an_edge_beside_infinity(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """At an edge, the refusal reported, and +inf returned for the value and the derivative."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        return replace(found, value=math.inf, derivative=math.inf) if at in table.edges else found

    return evaluate


def end_value_outside(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
    """Outside the readable range, `in_range` false, with the value at its nearest end and 0, refusing
    nothing."""
    low, high = table_evaluator.readable_range(table)
    end = reference(table, low if at < low else high, precision, side)
    return Evaluation(refused=False, in_range=False, value=end.value, derivative=0.0)


def checks_the_range_before_the_edge(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """At an edge outside the readable range, `in_range` false and no refusal."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        low, high = table_evaluator.readable_range(table)
        if at in table.edges and not low <= at <= high:
            return end_value_outside(table, at, precision, side)
        return reference(table, at, precision, side)

    return evaluate


def extrapolates_across_an_edge(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """Outside the readable range, the end value, though an edge lies between the point and the end, or on
    it."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        low, high = table_evaluator.readable_range(table)
        if at in table.edges or low <= at <= high:
            return reference(table, at, precision, side)
        return end_value_outside(table, at, precision, side)

    return evaluate


def refuses_outside_the_range(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """A refusal where none is due: outside the readable range, off every edge."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        return REFUSED if found.in_range is False else found

    return evaluate


def reads_outside_the_range_as_numpy_interp(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """Outside the readable range, the table's own value there, held at `x[0]` and `x[-1]`, with 0."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        if found.in_range is not False:
            return found
        held = min(max(at, table.x[0]), table.x[-1])
        own = reference(replace(table, source_range=None), held, precision, side)
        return replace(found, value=own.value)

    return evaluate


def extrapolates_linearly(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """Outside the readable range, the line through the end with the inside derivative there."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        if found.in_range is not False:
            return found
        low, high = table_evaluator.readable_range(table)
        nearest = low if at < low else high
        end = reference(table, nearest, precision, side)
        slope = float(end.derivative or 0.0)
        return replace(found, value=float(end.value or 0.0) + (at - nearest) * slope, derivative=slope)

    return evaluate


def takes_the_declared_side_at_a_knot_ending_the_range(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """At an end of the readable range on an interior knot of `x`, the declared side's derivative."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        low, high = table_evaluator.readable_range(table)
        if found.in_range and low < high and at in (low, high) and at in table.x[1:-1]:
            declared = reference(replace(table, source_range=None), at, precision, side)
            return replace(found, derivative=declared.derivative)
        return found

    return evaluate


def returns_a_derivative_where_the_range_is_one_point(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """Where the readable range is one point, the derivative the table would give there without
    `source_range`."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        low, high = table_evaluator.readable_range(table)
        if found.in_range and low == high:
            unnarrowed = reference(replace(table, source_range=None), at, precision, side)
            return replace(found, derivative=unnarrowed.derivative)
        return found

    return evaluate


def reads_below_an_edge_from_the_interval_above(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    interval = table_evaluator._interval  # pyright: ignore[reportPrivateUsage]  # the function the fault replaces

    def past_the_edge(x: tuple[float, ...], point: float, side: Side) -> int:
        found = interval(x, point, side)
        below_an_edge = found + 2 < len(x) and x[found + 1] == x[found + 2] and point < x[found + 1]
        return found + 2 if below_an_edge else found

    monkeypatch.setattr(table_evaluator, "_interval", past_the_edge)
    return table_evaluator.evaluate


def interpolates_log_log_linearly(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        return reference(replace(table, scheme="linear"), at, precision, side)

    return evaluate


def interpolates_linear_in_log_space(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        return reference(replace(table, scheme="loglog"), at, precision, side)

    return evaluate


def takes_the_linear_slope_as_the_log_log_derivative(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    linear_slope = table_evaluator._linear_slope  # pyright: ignore[reportPrivateUsage]  # the replacement
    monkeypatch.setattr(table_evaluator, "_loglog_slope", linear_slope)
    return table_evaluator.evaluate


def rounds_binary32_results_to_bfloat16(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """Each operation's result in `binary32` rounded on to bfloat16's 8 bits; it claims `binary32` only."""
    binary32 = table_evaluator._binary32_result  # pyright: ignore[reportPrivateUsage]  # the function the fault replaces

    def bfloat16(value: float) -> float:
        if not math.isfinite(value):
            return binary32(value)
        mantissa, exponent = math.frexp(value)
        return binary32(math.ldexp(round(mantissa * 256) / 256, exponent))

    monkeypatch.setattr(table_evaluator, "_binary32_result", bfloat16)
    return table_evaluator.evaluate


def takes_a_wider_source_range_as_the_readable_range(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """Where `source_range` reaches beyond `x`, `in_range` true out to its ends, with the end value and 0:
    `source_range` extending the readable range, which it never does (record_format.md section 6 table item
    4)."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        source_range = table.source_range
        if found.in_range is False and source_range is not None and source_range[0] <= at <= source_range[1]:
            return replace(found, in_range=True)
        return found

    return evaluate


def scales_the_log_log_derivative_at_the_lower_knot(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """The log-log derivative's `y / x` taken at the interval's lower knot, not at the point."""
    loglog_slope = table_evaluator._loglog_slope  # pyright: ignore[reportPrivateUsage]  # the function the fault replaces

    def at_the_lower_knot(
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        point: float,
        value: float,
        arithmetic: table_evaluator._Arithmetic[float],  # pyright: ignore[reportPrivateUsage]
    ) -> float:
        return loglog_slope(x0, x1, y0, y1, x0, y0, arithmetic)

    monkeypatch.setattr(table_evaluator, "_loglog_slope", at_the_lower_knot)
    return table_evaluator.evaluate


def raises_its_refusals(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
    """The reference evaluator, raising each refusal in place of reporting it, which the text allows
    (read_side_contract.md section 7 item 7, "a raised refusal counts as reported")."""
    found = reference(table, at, precision, side)
    if found.refused:
        raise runner.Refusal(f"at {at!r}")
    return found


def raises_another_exception_at_a_refusal(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """At a refusal, `ValueError` raised, which is no refusal: the runner adapts `Refusal` alone."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        if found.refused:
            raise ValueError(f"at {at!r}")
        return found

    return evaluate


def raises_a_refusal_outside_the_range(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """A raised refusal where none is due: outside the readable range, off every edge."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        if found.in_range is False:
            raise runner.Refusal(f"at {at!r}")
        return found

    return evaluate


BINARY32_CLAIMS = tuple(claim for claim in EVALUATOR_CLAIMS if claim.precision == "binary32")

# The differences a broken evaluator may be caught by, as the runner words them.
IN_RANGE = "in_range: expected"
VALUE = "value: expected"
DERIVATIVE = "derivative: expected"
NO_DERIVATIVE = "derivative: expected none"
NO_REFUSAL = "expected the refusal, got none"
NUMBER_BESIDE_THE_REFUSAL = "a number beside the refusal"
REFUSAL_NOT_DUE = "refused where no refusal is due"


class Caught(NamedTuple):
    """A broken evaluator, a TE file that must catch it, and the difference it must fail by there, under each
    precision and side it claims."""

    fault: EvaluatorFault
    catcher: str
    by: str
    claims: tuple[EvaluatorClaim, ...] = EVALUATOR_CLAIMS


EVALUATOR_FAULTS: list[Caught] = [
    # Section 6.4's table, each fault with every case file the table names for it.
    Caught(only_clamps, "TE-002.linear.json", IN_RANGE),
    Caught(only_clamps, "TE-003.just_outside_linear.json", IN_RANGE),
    Caught(takes_in_range_strictly, "TE-002.linear.json", IN_RANGE),
    Caught(ignores_a_narrower_source_range, "TE-003.narrowed.json", IN_RANGE),
    Caught(ignores_a_narrower_source_range, "TE-002.source_range_narrow.json", IN_RANGE),
    Caught(returns_the_side_it_did_not_declare, "TE-006.close_sides.json", DERIVATIVE),
    Caught(returns_the_side_it_did_not_declare, "TE-006.far_sides.json", DERIVATIVE),
    Caught(gives_the_outside_derivative_at_an_end, "TE-007.linear_ends.json", DERIVATIVE),
    Caught(reads_an_edge_from_the_interval_above, "TE-010.linear_edge.json", NO_REFUSAL),
    Caught(refuses_an_edge_beside_the_interval_above, "TE-010.linear_edge.json", NUMBER_BESIDE_THE_REFUSAL),
    Caught(refuses_an_edge_beside_infinity, "TE-010.linear_edge.json", NUMBER_BESIDE_THE_REFUSAL),
    Caught(checks_the_range_before_the_edge, "TE-010.edge_outside_readable_range.json", NO_REFUSAL),
    Caught(
        takes_the_declared_side_at_a_knot_ending_the_range, "TE-007.readable_range_knot_ends.json", DERIVATIVE
    ),
    Caught(reads_below_an_edge_from_the_interval_above, "TE-011.linear_sides.json", VALUE),
    Caught(interpolates_log_log_linearly, "TE-004.loglog_values.json", VALUE),
    Caught(interpolates_log_log_linearly, "TE-008.loglog_interior.json", VALUE),
    Caught(interpolates_linear_in_log_space, "TE-004.linear_values.json", VALUE),
    Caught(takes_the_linear_slope_as_the_log_log_derivative, "TE-008.loglog_interior.json", DERIVATIVE),
    Caught(rounds_binary32_results_to_bfloat16, "TE-012.decimal_knots_linear.json", VALUE, BINARY32_CLAIMS),
    Caught(rounds_binary32_results_to_bfloat16, "TE-012.decimal_knots_loglog.json", VALUE, BINARY32_CLAIMS),
    # The text's further faults, which the suite's README names (read_side_contract.md section 7 items 1, 4
    # and 7), each with a case file that catches it.
    Caught(checks_the_range_before_the_edge, "TE-010.edge_outside_readable_range_above.json", NO_REFUSAL),
    Caught(extrapolates_across_an_edge, "TE-010.edge_outside_readable_range.json", NO_REFUSAL),
    Caught(extrapolates_across_an_edge, "TE-010.edge_outside_readable_range_above.json", NO_REFUSAL),
    Caught(extrapolates_across_an_edge, "TE-010.edge_on_readable_range_end.json", NO_REFUSAL),
    Caught(extrapolates_across_an_edge, "TE-010.edge_on_readable_range_end_above.json", NO_REFUSAL),
    Caught(
        returns_a_derivative_where_the_range_is_one_point, "TE-007.one_point_range_end.json", NO_DERIVATIVE
    ),
    Caught(
        returns_a_derivative_where_the_range_is_one_point, "TE-007.one_point_range_inside.json", NO_DERIVATIVE
    ),
    Caught(refuses_outside_the_range, "TE-003.just_outside_linear.json", REFUSAL_NOT_DUE),
    Caught(reads_outside_the_range_as_numpy_interp, "TE-002.source_range_narrow.json", VALUE),
    Caught(extrapolates_linearly, "TE-002.linear.json", VALUE),
    # Two more the text supports: record_format.md section 6 table item 4 ("It never extends the readable
    # range") and read_side_contract.md section 7 item 5 (`y / x` at the point).
    Caught(takes_a_wider_source_range_as_the_readable_range, "TE-002.source_range_wide.json", IN_RANGE),
    Caught(scales_the_log_log_derivative_at_the_lower_knot, "TE-008.loglog_interior.json", DERIVATIVE),
    # Raised refusals: the runner adapts `Refusal` alone, and only where a refusal is due.
    Caught(raises_another_exception_at_a_refusal, "TE-010.linear_edge.json", "raised ValueError"),
    Caught(raises_a_refusal_outside_the_range, "TE-003.just_outside_linear.json", REFUSAL_NOT_DUE),
]

# A difference the runner gives where an executor raised: no caught fault, unless raising is the fault.
RAISED = re.compile(r"claiming [^:]*: raised ")


def why_not_caught(
    evaluator: TableEvaluator, catcher: CaseFile, claim: EvaluatorClaim, by: str
) -> str | None:
    """Why `evaluator`, claiming `claim`, does not fail the case file `catcher` by a difference `by`, or None
    where it does."""
    executors = {**EXECUTORS, "evaluate": runner.evaluate_executor(evaluator, (claim,))}
    run = runner.run(catcher, configurations=CONFIGURATIONS, executors=executors)
    if run.outcome is not Outcome.FAILED:
        return f"{claim}: {run.outcome.value}"
    raised = [difference for difference in run.differences if RAISED.match(difference)]
    if raised and not by.startswith("raised"):
        return f"{claim}: caught by raising: {raised[0]}"
    if not any(by in difference for difference in run.differences):
        return f"{claim}: no difference {by!r}: {run.differences[0]}"
    return None


def failed_cases(operation: str, executor: Executor) -> set[str]:
    runs = runner.run_all(
        CASE_FILES.values(), configurations=CONFIGURATIONS, executors={**EXECUTORS, operation: executor}
    )
    return {case_run.case_file.path.name for case_run in runs if case_run.outcome is Outcome.FAILED}


@pytest.mark.parametrize(("fault", "catcher"), FAULTS, ids=[fault.__name__ for fault, _ in FAULTS])
def test_a_broken_implementation_fails_a_real_case(
    fault: Fault, catcher: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_file = CASE_FILES[catcher]
    executors = {**EXECUTORS, case_file.operation: fault(monkeypatch)}
    assert runner.run(case_file, configurations=CONFIGURATIONS, executors=executors).outcome is Outcome.FAILED


@pytest.mark.parametrize("fault", S4D_FAULTS, ids=[fault.__name__ for fault in S4D_FAULTS])
def test_s4ds_broken_readers_fail_s4ds_case_files_alone(
    fault: Fault, monkeypatch: pytest.MonkeyPatch
) -> None:
    s4d = {name for name, case_file in CASE_FILES.items() if runner.steps(case_file) == ("S4d",)}
    failed = failed_cases("read", fault(monkeypatch))
    assert failed, fault.__name__
    assert failed <= s4d, sorted(failed - s4d)


@pytest.mark.parametrize(
    ("fault", "catcher"), BUILD_FAULTS, ids=[fault.__name__ for fault, _ in BUILD_FAULTS]
)
def test_each_broken_build_is_caught_by_an_s7a_1_file(fault: Fault, catcher: str) -> None:
    assert runner.steps(CASE_FILES[catcher]) == ("S7a-1",)


@pytest.mark.parametrize("operation", sorted(EXECUTORS))
def test_the_implementation_itself_fails_none(operation: str) -> None:
    assert failed_cases(operation, EXECUTORS[operation]) == set()


def test_an_evaluator_that_raises_its_refusals_fails_no_te_file() -> None:
    raised: list[float] = []

    def counted(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        try:
            return raises_its_refusals(table, at, precision, side)
        except runner.Refusal:
            raised.append(at)
            raise

    assert failed_cases("evaluate", runner.evaluate_executor(counted)) == set()
    # It raised in place of every refusal the TE files hold, under each of the four configurations.
    assert len(raised) == 4 * sum(map(refusals_expected, CASE_FILES.values())) > 0


def refusals_expected(case_file: CaseFile) -> int:
    evaluations = case_file.expected.get("evaluations", [])
    assert isinstance(evaluations, list)
    return sum(1 for entry in evaluations if isinstance(entry, dict) and entry.get("refused") is True)


@pytest.mark.parametrize(
    "caught",
    EVALUATOR_FAULTS,
    ids=[f"{caught.fault.__name__}-{caught.catcher.removesuffix('.json')}" for caught in EVALUATOR_FAULTS],
)
def test_a_broken_evaluator_fails_its_case_by_its_own_difference_under_every_claim_it_makes(
    caught: Caught, monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluator = caught.fault(monkeypatch)
    catcher = CASE_FILES[caught.catcher]
    problems = [why_not_caught(evaluator, catcher, claim, caught.by) for claim in caught.claims]
    assert problems == [None] * len(caught.claims)


def raises_in_its_interpolation(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """A fault that fails a case only by raising: an interpolation that raises `TypeError`."""

    def interpolate(*arguments: object) -> float:
        raise TypeError("a fault in the evaluator's own code")

    monkeypatch.setattr(table_evaluator, "_interpolate", interpolate)
    return table_evaluator.evaluate


def test_a_fault_counts_as_caught_only_by_the_difference_named_beside_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claim, catcher = EVALUATOR_CLAIMS[0], CASE_FILES["TE-002.linear.json"]
    assert why_not_caught(reference, catcher, claim, IN_RANGE) == f"{claim}: {Outcome.VERIFIED.value}"
    clamping = only_clamps(monkeypatch)
    assert why_not_caught(clamping, catcher, claim, IN_RANGE) is None
    # Controls: the same fault named beside a difference it does not give, and a fault that only raises.
    assert "no difference 'value: expected'" in str(why_not_caught(clamping, catcher, claim, VALUE))
    raising = raises_in_its_interpolation(monkeypatch)
    assert "caught by raising: " in str(why_not_caught(raising, catcher, claim, IN_RANGE))


def with_ten_times_the_binary32_tolerance(case_file: CaseFile) -> CaseFile:
    """`case_file`, compared in either precision at ten times its `binary32` tolerance."""
    tolerances = case_file.precision_tolerances
    assert tolerances is not None
    return replace(case_file, precision_tolerances=dict.fromkeys(tolerances, 10 * tolerances["binary32"]))


FAULTY_EVALUATORS = list(dict.fromkeys(caught.fault for caught in EVALUATOR_FAULTS))


@pytest.mark.parametrize("fault", FAULTY_EVALUATORS, ids=[fault.__name__ for fault in FAULTY_EVALUATORS])
def test_each_broken_evaluator_misses_one_of_its_files_by_ten_times_its_binary32_tolerance(
    fault: EvaluatorFault, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The specification README's cap on a file's `binary32` tolerance, restated per broken evaluator
    (maintainer, 2026-10-17): of the TE files named beside a broken evaluator, at least one still catches it,
    by the difference named beside it, with that file's `binary32` tolerance ten times as wide, under each
    precision and side it claims.

    This is the stronger reading of the cap (maintainer, 2026-10-19). The specification counts a miss by the
    relative difference at the compared number where the broken evaluator differs most, or by a difference no
    tolerance passes; this test requires the difference named beside the file, which is at most that. A
    linear table read as log-log misses TE-004 `linear_values` by 176 times in its value, the difference named
    beside it, and by 35,586 times by the text's count, in its derivative (the TE README, "The broken
    evaluators")."""
    rows = [caught for caught in EVALUATOR_FAULTS if caught.fault is fault]
    evaluator = fault(monkeypatch)
    for claim in rows[0].claims:
        problems = [
            why_not_caught(
                evaluator, with_ten_times_the_binary32_tolerance(CASE_FILES[row.catcher]), claim, row.by
            )
            for row in rows
        ]
        assert None in problems, problems


def nudges_each_value_by_a_millionth(monkeypatch: pytest.MonkeyPatch) -> TableEvaluator:
    """Each value inside the readable range a millionth too large: under ten times any TE file's `binary32`
    tolerance, the least of which is 3e-7."""

    def evaluate(table: Table, at: float, precision: EvaluatorPrecision, side: Side) -> Evaluation:
        found = reference(table, at, precision, side)
        if found.in_range and found.value is not None:
            return replace(found, value=float(found.value) * (1 + 1e-6))
        return found

    return evaluate


def test_the_cap_fails_a_broken_evaluator_that_misses_every_file_by_less(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nudging = nudges_each_value_by_a_millionth(monkeypatch)
    claim = EVALUATOR_CLAIMS[0]
    files = [case_file for case_file in CASE_FILES.values() if case_file.operation == "evaluate"]
    # Caught at the files' own tolerances, but by no file at ten times its binary32 one.
    assert any(why_not_caught(nudging, case_file, claim, VALUE) is None for case_file in files)
    widened = [with_ten_times_the_binary32_tolerance(case_file) for case_file in files]
    assert all(why_not_caught(nudging, case_file, claim, VALUE) is not None for case_file in widened)
