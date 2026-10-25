# SPDX-License-Identifier: Apache-2.0
"""Seeded faults of the build's results model (`build_results_model.py`), each one rule of the text broken,
run against every build-check case file and, failing those, the results model's direct checks
(`results_direct.py`) by `test_seeded_faults.py`. A fault the cases or the direct checks kill is a rule they
pin; one that survives is a rule neither pins, listed with why, which HP43 to HP46 (S7a-2p) must kill. The S7
design's mutant lists for HP43 to HP46 (6.5's table) name rules the model must have; each it holds is seeded
here, under the name that list gives it where it gives one (R01 to R07: the faults of the case writer's
build).

Each fault replaces one or more of the model's module-level names, which the model looks up when it runs, and
keeps the model answering: a fault that makes it raise fails its check, never kills."""

import copy
import dataclasses
from collections.abc import Callable, Mapping, Sequence

from tests.reference import build_results_model as results
from tests.reference import read_model
from tests.reference.build_results_model import (
    GIVEN_KINDS,
    REFERENCE,
    ROW_OF,
    Made,
    Report,
    Row,
    Stored,
    entries,
    members,
)
from tests.reference.mutants import Mutant
from tests.reference.read_model import REASONS, Status
from tests.reference.strict_json import JsonObject, JsonValue

# The model's own functions, taken before any fault replaces them.
_applied_by = results.applied_by
_build_reasons = results.build_reasons
_covers = results.covers
_field_result = results.field_result
_filled = results.filled
_judge = results.judge
_located_at = results.located_at
_model_results = results.model_results
_read_of = results.read_of
_request_for = results.request_for
_status_of = results.status_of
_stored_value = results.stored_value
_unused_of = results.unused_of

BUILD_CODES = ("no_requirement", "label_mismatch", "not_reviewed")


def codes(reasons: Sequence[JsonValue]) -> list[str]:
    return [str(members(reason).get("code")) for reason in reasons]


# The request


def given_at_any_record(acceptances: Sequence[JsonValue], record: JsonObject, name: str) -> tuple[int, ...]:
    return tuple(
        index
        for index, acceptance in enumerate(acceptances)
        if members(acceptance).get("acceptance") in GIVEN_KINDS and members(acceptance).get("field") == name
    )


def given_for_any_field(acceptances: Sequence[JsonValue], record: JsonObject, name: str) -> tuple[int, ...]:
    return tuple(
        index
        for index, acceptance in enumerate(acceptances)
        if members(acceptance).get("acceptance") in GIVEN_KINDS and _located_at(members(acceptance), record)
    )


def given_of_every_kind(acceptances: Sequence[JsonValue], record: JsonObject, name: str) -> tuple[int, ...]:
    return tuple(
        index
        for index, acceptance in enumerate(acceptances)
        if members(acceptance).get("field") == name and _located_at(members(acceptance), record)
    )


def request_changed(
    change: Callable[[JsonObject, JsonObject, JsonObject], None],
) -> Callable[..., JsonObject]:
    def request_for(
        declaration: JsonObject,
        record: JsonObject,
        name: str,
        requirement: JsonObject,
        given: list[JsonValue],
    ) -> JsonObject:
        request = _request_for(declaration, record, name, requirement, given)
        change(request, declaration, requirement)
        return request

    return request_for


def requirement_whole(request: JsonObject, declaration: JsonObject, requirement: JsonObject) -> None:
    request["requirement"] = {name: held for name, held in requirement.items() if name != "field"}


def unnamed_operating_dropped(request: JsonObject, declaration: JsonObject, requirement: JsonObject) -> None:
    named = members(requirement.get("conditions"))
    held = members(declaration.get("operating_conditions"))
    request["operating_conditions"] = {name: entry for name, entry in held.items() if name in named}


def want_defaulted(request: JsonObject, declaration: JsonObject, requirement: JsonObject) -> None:
    request["requirement"] = {**members(request["requirement"]), "want": "value"}


# The build's own reasons, and the stored value


def label_from_the_result(
    read: JsonObject, record: JsonObject, name: str, sources: Sequence[bytes]
) -> Stored | None:
    found = _stored_value(read, record, name, sources)
    if found is None:
        return None
    value = {member: held for member, held in members(found.value).items() if member != "label"}
    labels = [label for label in entries(read.get("labels")) if label in read_model.FIELD_LABELS]
    if labels:
        value["label"] = labels[0]
    return Stored(value)


def section_of_field(record: JsonObject, name: str, sources: Sequence[bytes]) -> JsonObject:
    """The section of the pinned record that holds the field `name`, as stored, or none."""
    found = results.pinned(record, sources)
    value = found[0].value if found else None
    body = members(value).get("body") if isinstance(value, dict) else None
    return members(members(members(body).get("sections")).get(name.partition(".")[0]))


def stored_wherever(
    read: JsonObject, record: JsonObject, name: str, sources: Sequence[bytes]
) -> Stored | None:
    found = _stored_value(read, record, name, sources)
    return found if found is not None else Stored({})


def step_0_unread(request: JsonObject, claims: frozenset[str]) -> bool:
    return True


def field_holding_alternatives_stored(
    read: JsonObject, record: JsonObject, name: str, sources: Sequence[bytes]
) -> Stored | None:
    if any(members(reason).get("code") in results.BEFORE_THE_FIELD for reason in entries(read["reasons"])):
        return None
    found = results.pinned(record, sources)
    if not found:
        return None
    held = section_of_field(record, name, sources)
    return Stored(members(held.get("fields")).get(name.partition(".")[2]))


def section_stored(
    read: JsonObject, record: JsonObject, name: str, sources: Sequence[bytes]
) -> Stored | None:
    found = _stored_value(read, record, name, sources)
    if found is None:
        return None
    return Stored(section_of_field(record, name, sources))


def reasons_dropping(
    drops: Callable[[JsonObject, JsonObject, Stored | None], bool],
) -> Callable[..., list[JsonObject]]:
    def build_reasons(requirement: JsonObject, read: JsonObject, stored: Stored | None) -> list[JsonObject]:
        found = _build_reasons(requirement, read, stored)
        return [
            reason
            for reason in found
            if not (reason.get("code") == "label_mismatch" and drops(requirement, read, stored))
        ]

    return build_reasons


def any_label_matches(requirement: JsonObject, read: JsonObject, stored: Stored | None) -> bool:
    return stored is not None and stored.label is not None


def absent_label_matches(requirement: JsonObject, read: JsonObject, stored: Stored | None) -> bool:
    return stored is not None and stored.label is None


def case_blind_label_matches(requirement: JsonObject, read: JsonObject, stored: Stored | None) -> bool:
    return stored is not None and str(stored.label).lower() == str(requirement["label"]).lower()


def before_the_field_without(code: str) -> tuple[str, ...]:
    return tuple(held for held in results.BEFORE_THE_FIELD if held != code)


def reasons_adding(adds: Callable[[JsonObject, JsonObject], bool]) -> Callable[..., list[JsonObject]]:
    def build_reasons(requirement: JsonObject, read: JsonObject, stored: Stored | None) -> list[JsonObject]:
        found = _build_reasons(requirement, read, stored)
        if adds(requirement, read) and {"code": "not_reviewed"} not in found:
            found.append({"code": "not_reviewed"})
        return found

    return build_reasons


def reviewed_without_provenance(requirement: JsonObject, read: JsonObject) -> bool:
    return "review" in requirement and "provenance" not in read


def unreviewed_unrequired(requirement: JsonObject, read: JsonObject) -> bool:
    return "provenance" in read and not results.completed(read["provenance"])


def reason_taken_as_review(provenance: JsonValue) -> bool:
    review = members(members(provenance).get("review"))
    return review.get("result") == "reviewed" or "reason" in review


def status_from(status: Callable[[list[str]], Status]) -> Callable[..., Status]:
    def status_of(reasons: Sequence[JsonValue]) -> Status:
        return status(codes(list(reasons)))

    return status_of


def worst_of(found: list[str]) -> Status:
    return read_model.worst(REASONS[code].status for code in found)


def worst_without_the_build(found: list[str]) -> Status:
    return worst_of([code for code in found if code not in BUILD_CODES])


def not_reviewed_unknown(found: list[str]) -> Status:
    return "unknown" if "not_reviewed" in found else worst_of(found)


def not_reviewed_not_met(found: list[str]) -> Status:
    return "not_met" if "not_reviewed" in found else worst_of(found)


def best_of(found: list[str]) -> Status:
    statuses: list[Status] = [REASONS[code].status for code in found]
    return min(statuses, key=read_model.STATUSES_BEST_FIRST.index) if statuses else "met"


def field_result_changed(
    change: Callable[[Made, JsonObject | None, JsonObject], Made],
) -> Callable[..., Made]:
    def field_result(
        declaration: JsonObject,
        model: JsonObject,
        record: JsonObject,
        name: str,
        requirement: JsonObject | None,
        sources: Sequence[bytes],
        claims: frozenset[str],
    ) -> Made:
        made = _field_result(declaration, model, record, name, requirement, sources, claims)
        return change(made, requirement, record)

    return field_result


def value_dropped_by_the_build(made: Made, requirement: JsonObject | None, record: JsonObject) -> Made:
    if "label_mismatch" not in codes(entries(made.result["reasons"])):
        return made
    return dataclasses.replace(
        made, result={name: held for name, held in made.result.items() if name != "value"}
    )


def every_listed_record_resolved(made: Made, requirement: JsonObject | None, record: JsonObject) -> Made:
    return made if requirement is None else dataclasses.replace(made, resolved=record)


def unread_record_resolved(made: Made, requirement: JsonObject | None, record: JsonObject) -> Made:
    return dataclasses.replace(made, resolved=record) if requirement is None else made


def unrequired_field_read(
    declaration: JsonObject,
    model: JsonObject,
    record: JsonObject,
    name: str,
    requirement: JsonObject | None,
    sources: Sequence[bytes],
    claims: frozenset[str],
) -> Made:
    wanted: JsonObject = {"field": name, "want": "value"}
    taken = requirement if requirement is not None else wanted
    return _field_result(declaration, model, record, name, taken, sources, claims)


# What the read applied


def given_applied(
    read: JsonObject, given: Sequence[int], acceptances: Sequence[JsonValue]
) -> tuple[int, ...]:
    return tuple(given)


def first_implied_only(
    read: JsonObject, given: Sequence[int], acceptances: Sequence[JsonValue]
) -> tuple[int, ...]:
    applied = _applied_by(read, given, acceptances)
    implied = [
        index for index in applied if members(acceptances[index]).get("acceptance") == "implied_condition"
    ]
    return tuple(index for index in applied if index not in implied[1:])


def indexed_among_the_given(
    read: JsonObject, given: Sequence[int], acceptances: Sequence[JsonValue]
) -> tuple[int, ...]:
    return tuple(list(given).index(index) for index in _applied_by(read, given, acceptances))


def implied_applied_where_the_specimen_states_it(
    declaration: JsonObject,
    model: JsonObject,
    record: JsonObject,
    name: str,
    requirement: JsonObject | None,
    sources: Sequence[bytes],
    claims: frozenset[str],
) -> Made:
    """An implied condition that filled a condition counted applied only where the field's specimen states its
    fact and token: a condition the text does not add."""
    made = _field_result(declaration, model, record, name, requirement, sources, claims)
    held = section_of_field(record, name, sources)
    value = members(members(held.get("fields")).get(name.partition(".")[2]))
    specimen = {**members(held.get("specimen")), **members(value.get("specimen"))}
    acceptances = entries(model.get("acceptances"))

    def stated(index: int) -> bool:
        implied = members(acceptances[index])
        if implied.get("acceptance") != "implied_condition":
            return True
        fact = members(specimen.get(str(implied.get("fact"))))
        return results.same(fact.get("token"), implied.get("token"))

    return dataclasses.replace(made, applied=tuple(index for index in made.applied if stated(index)))


def filled_by_the_first_entry_supplied(read: JsonObject, implied: JsonObject) -> bool:
    """An implied condition's value taken from its first `implies` entry, whatever the condition."""
    first: JsonValue = next(iter(members(implied.get("implies")).values()), None)
    return any(
        bool(members(first))
        and results.same(
            members(members(entry).get("record")),
            {**results.without_basis(members(first)), "basis": "implied"},
        )
        for entry in entries(read.get("conditions"))
    )


def filled_whatever_the_basis(read: JsonObject, implied: JsonObject) -> bool:
    return any(
        bool(supplied) and results.same(results.without_basis(held), results.without_basis(supplied))
        for entry in entries(read.get("conditions"))
        for held in [members(members(entry).get("record"))]
        for supplied in [members(members(implied.get("implies")).get(str(members(entry).get("name"))))]
    )


def extrapolation_applied_under_any_assumption(
    read: JsonObject, given: Sequence[int], acceptances: Sequence[JsonValue]
) -> tuple[int, ...]:
    """A given extrapolation counted applied whenever the result rests on an `assumption`, a nominal's too."""
    applied = set(_applied_by(read, given, acceptances))
    if "assumption" in read:
        applied |= {
            index for index in given if members(acceptances[index]).get("acceptance") == "extrapolation"
        }
    return tuple(sorted(applied))


def numbers_equal(one: JsonValue, other: JsonValue) -> bool:
    """JSON compared by `==`, so that `0` and `-0` are one."""
    return one == other


def named_by_kind(assumption: JsonValue, acceptance: JsonObject) -> bool:
    return members(assumption).get("acceptance") == acceptance.get("acceptance")


# The judgement


def rows_changed(change: Callable[[dict[str, Row]], None]) -> dict[str, Row]:
    rows = dict(ROW_OF)
    change(rows)
    return rows


def waiver_of_any_code(rows: dict[str, Row]) -> None:
    for code in REASONS:
        rows.setdefault(code, Row((code,), REASONS[code].status, "waiver", names_code=True))


def conditions_unnamed(rows: dict[str, Row]) -> None:
    for code, row in rows.items():
        rows[code] = dataclasses.replace(row, names_condition=False)


def codes_unnamed(rows: dict[str, Row]) -> None:
    for code, row in rows.items():
        rows[code] = dataclasses.replace(row, names_code=False)


def assumption_unnamed(code: str) -> Callable[[dict[str, Row]], None]:
    def change(rows: dict[str, Row]) -> None:
        rows[code] = dataclasses.replace(rows[code], on_assumption=False)

    return change


def covered_like(code: str, other: str) -> Callable[[dict[str, Row]], None]:
    def change(rows: dict[str, Row]) -> None:
        rows[code] = rows[other]

    return change


def covers_changed(
    change: Callable[[JsonObject, JsonObject, JsonObject], JsonObject | None],
) -> Callable[..., bool]:
    def covers(acceptance: JsonObject, reason: JsonObject, result: JsonObject) -> bool:
        changed = change(acceptance, reason, result)
        return changed is not None and _covers(changed, reason, result)

    return covers


def field_taken(acceptance: JsonObject, reason: JsonObject, result: JsonObject) -> JsonObject | None:
    return {**acceptance, "field": result["field"]}


def location_taken(acceptance: JsonObject, reason: JsonObject, result: JsonObject) -> JsonObject | None:
    return {**acceptance, "record": result["record"]}


def alternatives_uncovered(
    acceptance: JsonObject, reason: JsonObject, result: JsonObject
) -> JsonObject | None:
    return None if "alternative" in reason else acceptance


def label_trusted(acceptance: JsonObject, reason: JsonObject, result: JsonObject) -> JsonObject | None:
    return {name: held for name, held in acceptance.items() if name != "label"}


def label_undecided_anywhere(
    acceptance: JsonObject, reason: JsonObject, result: JsonObject
) -> JsonObject | None:
    if "label" in acceptance:
        raise results._Undecided("label_trust")  # pyright: ignore[reportPrivateUsage]
    return acceptance


def located_by_id(acceptance: JsonObject, record: JsonObject) -> bool:
    if "region" in acceptance or "interval" in acceptance or "record" not in acceptance:
        return _located_at(acceptance, record)
    return members(acceptance["record"]).get("id") == record.get("id")


def located_by(*names: str) -> Callable[[JsonObject, JsonObject], bool]:
    """An acceptance located at a record by `names` alone, of `id`, `version` and `content_hash`."""

    def located_at(acceptance: JsonObject, record: JsonObject) -> bool:
        if "region" in acceptance or "interval" in acceptance or "record" not in acceptance:
            return _located_at(acceptance, record)
        named = members(acceptance["record"])
        return all(named.get(name) == record.get(name) for name in names)

    return located_at


def region_at_a_record(acceptance: JsonObject, record: JsonObject) -> bool:
    return _located_at(
        {name: held for name, held in acceptance.items() if name not in ("region", "interval")}, record
    )


def label_undecided_after(
    *tests: Callable[[JsonObject, JsonObject, JsonObject], bool],
) -> Callable[[JsonObject, JsonObject, JsonObject], JsonObject | None]:
    """A waiver naming a label given no verdict as soon as `tests` pass, before the tests that follow them."""

    def change(acceptance: JsonObject, reason: JsonObject, result: JsonObject) -> JsonObject | None:
        row = ROW_OF.get(str(reason.get("code")))
        located = _located_at(acceptance, members(result["record"]))
        passes = (
            row is not None
            and acceptance.get("acceptance") == row.kind
            and acceptance.get("field") == result["field"]
            and located
        )
        if "label" in acceptance and passes and all(test(acceptance, reason, result) for test in tests):
            raise results._Undecided("label_trust")  # pyright: ignore[reportPrivateUsage]
        return acceptance

    return change


def code_named(acceptance: JsonObject, reason: JsonObject, result: JsonObject) -> bool:
    return results.same(acceptance.get("code"), reason.get("code"))


def nothing_tested(acceptance: JsonObject, reason: JsonObject, result: JsonObject) -> bool:
    return True


def judged_changed(change: Callable[[JsonObject, Made, JsonObject], JsonObject]) -> Callable[..., JsonObject]:
    def judge(made: Made, model: JsonObject) -> JsonObject:
        return change(_judge(made, model), made, model)

    return judge


def everything_not_accepted(judged: JsonObject, made: Made, model: JsonObject) -> JsonObject:
    return {**judged, "not_accepted": list(entries(judged["reasons"]))}


def every_acceptance_of_the_field_cited(judged: JsonObject, made: Made, model: JsonObject) -> JsonObject:
    cited = {
        float(index)
        for index, acceptance in enumerate(entries(model.get("acceptances")))
        if members(acceptance).get("field") == judged["field"]
        and _located_at(members(acceptance), members(judged["record"]))
    }
    held = {index for index in entries(judged["accepted_by"]) if isinstance(index, float)}
    every: list[JsonValue] = [*sorted(cited | held)]
    return {**judged, "accepted_by": every}


def status_raised_when_accepted(judged: JsonObject, made: Made, model: JsonObject) -> JsonObject:
    return {**judged, "status": "met"} if judged["accepted"] is True else judged


def specimen_differences_left_out(judged: JsonObject, made: Made, model: JsonObject) -> JsonObject:
    return {name: held for name, held in judged.items() if name != "specimen_differences"}


def applied_uncited(made: Made, model: JsonObject) -> JsonObject:
    return _judge(dataclasses.replace(made, applied=()), model)


def build_reasons_unjudged(made: Made, model: JsonObject) -> JsonObject:
    reasons = entries(made.result["reasons"])
    read_only = [reason for reason in reasons if members(reason).get("code") not in BUILD_CODES]
    judged = _judge(dataclasses.replace(made, result={**made.result, "reasons": read_only}), model)
    return {**judged, "reasons": reasons}


def unused_listing_every_one(model: JsonObject, judged: Sequence[JsonObject]) -> list[JsonObject]:
    return _unused_of(model, [{**result, "accepted_by": []} for result in judged])


# The report


def report_from(
    judge_of: Callable[[Made, JsonObject, list[JsonObject]], JsonObject] | None = None,
    unused_of: Callable[[list[JsonObject], list[list[JsonObject]], list[list[Made]]], list[JsonObject]]
    | None = None,
    results_of: Callable[[list[JsonObject]], list[JsonObject]] | None = None,
    pieces_of: Callable[[list[JsonObject]], list[JsonObject]] | None = None,
) -> Callable[..., Report]:
    """The model's report, with one of its parts made otherwise: how a result is judged, given every model;
    what is unused, given every model's results; the results kept; or the models whose later pieces (a target
    naming a fact, combinations, a `trainable` entry) are looked for."""

    def report(declaration: JsonObject, sources: Sequence[bytes], claims: frozenset[str]) -> Report:
        models = [members(model) for model in entries(declaration.get("models"))]
        made: list[list[Made]] = []
        for model in pieces_of(models) if pieces_of else models:
            results.later_pieces(model)
        for model in models:
            made.append(results.model_results(declaration, model, sources, claims))
        judged = [
            [judge_of(one, model, models) if judge_of else results.judge(one, model) for one in ones]
            for model, ones in zip(models, made, strict=True)
        ]
        unused = (
            unused_of(models, judged, made)
            if unused_of
            else [
                entry
                for model, ones in zip(models, judged, strict=True)
                for entry in results.unused_of(model, ones)
            ]
        )
        kept = [result for ones in judged for result in ones]
        records = [one.resolved for ones in made for one in ones if one.resolved is not None]
        return Report(
            declaration.get("consumer"),
            tuple(results.distinct(records)),
            declaration,
            tuple(results_of(kept) if results_of else kept),
            tuple(unused),
        )

    return report


def judged_by_every_model(made: Made, model: JsonObject, models: list[JsonObject]) -> JsonObject:
    pooled = [acceptance for one in models for acceptance in entries(one.get("acceptances"))]
    return results.judge(made, {**model, "acceptances": pooled})


def unused_after_the_first(
    models: list[JsonObject], judged: list[list[JsonObject]], made: list[list[Made]]
) -> list[JsonObject]:
    first = members(models[0].get("model")).get("name") if models else None
    return [
        {**entry, "model": first}
        for model, ones in zip(models, judged, strict=True)
        for entry in results.unused_of(model, ones)
    ]


def unused_shared(
    models: list[JsonObject], judged: list[list[JsonObject]], made: list[list[Made]]
) -> list[JsonObject]:
    every = [result for ones in judged for result in ones]
    return [entry for model in models for entry in results.unused_of(model, every)]


def unused_without_the_applied(
    models: list[JsonObject], judged: list[list[JsonObject]], made: list[list[Made]]
) -> list[JsonObject]:
    return [
        entry
        for model, ones in zip(models, made, strict=True)
        for entry in results.unused_of(
            model, [results.judge(dataclasses.replace(one, applied=()), model) for one in ones]
        )
    ]


def one_result_a_field(kept: list[JsonObject]) -> list[JsonObject]:
    seen: dict[str, JsonObject] = {}
    for result in kept:
        seen.setdefault(str(result["field"]), result)
    return list(seen.values())


def every_record_of_the_store(
    declaration: JsonObject, model: JsonObject, sources: Sequence[bytes], claims: frozenset[str]
) -> list[Made]:
    stored: list[JsonValue] = [
        {name: source.value[name] for name in REFERENCE if name in source.value}
        for source in read_model.sources_read(sources)
        if isinstance(source.value, dict) and read_model.candidate(source.value)
    ]
    over: JsonObject = {"records": copy.deepcopy(stored)}
    listed: JsonObject = {**model, "checked_over": over}
    return _model_results(declaration, listed, sources, claims)


def later_pieces_decided(model: JsonObject) -> None:
    return None


def first_model_alone(models: list[JsonObject]) -> list[JsonObject]:
    return models[:1]


def alternative_unnamed_decided(
    chosen: Callable[[Sequence[JsonValue]], Stored | None],
) -> Callable[..., Stored | None]:
    """The unnamed alternative a result rests on decided by `chosen`, not given no verdict."""

    def stored_value(
        read: JsonObject, record: JsonObject, name: str, sources: Sequence[bytes]
    ) -> Stored | None:
        try:
            return _stored_value(read, record, name, sources)
        except results._Undecided as undecided:  # pyright: ignore[reportPrivateUsage]
            if undecided.why != results.UNDECIDED["alternative_unnamed"]:
                raise
            held = section_of_field(record, name, sources)
            field_value = members(members(held.get("fields")).get(name.partition(".")[2]))
            alternatives = entries(field_value.get("alternatives"))
            return chosen(alternatives)

    return stored_value


def first_alternative(alternatives: Sequence[JsonValue]) -> Stored | None:
    return Stored(alternatives[0])


def no_alternative(alternatives: Sequence[JsonValue]) -> Stored | None:
    return None


def read_undecided_as_no_reason(
    request: JsonObject, sources: Sequence[bytes], claims: frozenset[str]
) -> JsonObject:
    """A read the read model gives no verdict on taken as a read that gives no reason."""
    try:
        return _read_of(request, sources, claims)
    except results._Undecided:  # pyright: ignore[reportPrivateUsage]
        return {"status": "unknown", "reasons": []}


def step_0_read_undecided_as_passed(
    request: JsonObject, sources: Sequence[bytes], claims: frozenset[str]
) -> JsonObject:
    """The same read, over no records to tell step 0, taken as the `absent` that says step 0 passes."""
    try:
        return _read_of(request, sources, claims)
    except results._Undecided:  # pyright: ignore[reportPrivateUsage]
        if sources:
            raise
        return {"status": "unknown", "reasons": [{"code": "absent"}]}


def refused_by_the_first_model(self: Report) -> bool:
    first = self.results[0]["model"] if self.results else None
    return any(result["accepted"] is not True for result in self.results if result["model"] == first)


def never_refused(self: Report) -> bool:
    return False


def mutant(fault: str, rule: str, patches: Mapping[str, object], survives: str | None = None) -> Mutant:
    return Mutant(fault, rule, patches, survives, module=results)


RESULTS_MUTANTS: Mapping[str, Mutant] = {
    # The request (HP44 `_request`)
    "results_acceptance_at_another_record_given": mutant(
        "an acceptance a read takes given to the read of another record",
        'declarations.md:302-303 "that name the read\'s field" and "and are located at its location"',
        {"given_to": given_at_any_record},
    ),
    "results_acceptance_of_another_field_given": mutant(
        "an acceptance a read takes given to the read of another field",
        'declarations.md:302 "section 1), overlays aside (which overlays it gives a read is [not yet '
        "covered]), that name the read's field\"",
        {"given_to": given_for_any_field},
    ),
    "results_waivers_given": mutant(
        "an acceptance of a kind a read does not take (a waiver) given to the read",
        'declarations.md:301 "The build gives each read the acceptances of the kinds a read takes"',
        {"given_to": given_of_every_kind},
    ),
    "results_requirement_label_given": mutant(
        "the requirement given whole, its `label` and `review` with it (so `request_incomplete`)",
        "declarations.md:300 \"The build's own read request holds the requirement's `want` and "
        '`conditions`"',
        {"request_for": request_changed(requirement_whole)},
    ),
    "results_unnamed_operating_condition_dropped": mutant(
        "an operating condition the requirement does not name left out of the request (a table's axis)",
        'declarations.md:300-301 "and the declared operating" and "conditions. The build gives each read '
        'the acceptances"',
        {"request_for": request_changed(unnamed_operating_dropped)},
    ),
    "results_want_defaulted": mutant(
        "the request's `want` defaulted to `value`",
        "declarations.md:300 \"The build's own read request holds the requirement's `want` and "
        '`conditions`"',
        {"request_for": request_changed(want_defaulted)},
    ),
    # The build's own reasons, and the stored value (HP45 `_stored`, `_build_reasons`)
    "results_label_read_from_the_result": mutant(
        "the label stored read from the result's labels, which a refusal before step 12 hides",
        'declarations.md:308-309 "whether or not the read" and "reached step 12, so a label never hides '
        'behind another refusal"',
        {"stored_value": label_from_the_result},
    ),
    "results_label_checked_on_no_stored_value": mutant(
        "a result that rests on no stored value (its record or field not found, or no single alternative) "
        "checked against a value holding no label",
        'declarations.md:309-310 "A result that rests on no stored value (its" and "record or field not '
        'found, a refusal before step 7 finds the field, or no single alternative:"',
        {"stored_value": stored_wherever},
    ),
    "results_label_checked_past_step_0": mutant(
        "a read refused at step 0 checked against the field's label",
        "OPEN_POINTS: label_of_no_stored_value",
        {"step_0_passes": step_0_unread},
    ),
    "results_label_of_the_field_holding_alternatives": mutant(
        "the label checked against the field holding the alternatives, not the alternative read",
        'declarations.md:308 "stored on the value the result rests on (the field, or the alternative '
        'read), whether or not the read"',
        {"stored_value": field_holding_alternatives_stored},
    ),
    "results_label_of_the_section": mutant(
        "the label read from the section holding the field, not the field's",
        'declarations.md:308 "stored on the value the result rests on (the field, or the alternative '
        'read), whether or not the read"',
        {"stored_value": section_stored},
    ),
    "results_any_stored_label_matches": mutant(
        "a stored label that differs taken as the one required",
        'declarations.md:171-172 "when the label stored on the" and "value the result rests on differs or '
        'is absent"',
        {"build_reasons": reasons_dropping(any_label_matches)},
    ),
    "results_label_compared_without_case": mutant(
        "a stored label that differs from the one required in case alone taken as the one required",
        'declarations.md:171-172 "when the label stored on the" and "value the result rests on differs or '
        'is absent"',
        {"build_reasons": reasons_dropping(case_blind_label_matches)},
    ),
    "results_absent_label_matches": mutant(
        "a label absent from the value the result rests on taken as the one required",
        'declarations.md:171-172 "when the label stored on the" and "value the result rests on differs or '
        'is absent"',
        {"build_reasons": reasons_dropping(absent_label_matches)},
    ),
    "results_not_checked_with_a_reason_reviewed": mutant(
        "a review `not_checked` with a `reason` taken as completed",
        'declarations.md:194 "section 2) is not a completed review: one holding `result` `reviewed`"',
        {"completed": reason_taken_as_review},
    ),
    "results_not_reviewed_without_provenance": mutant(
        "`not_reviewed` given to a result that holds no `provenance` (R04)",
        'declarations.md:195 "A result that holds no `provenance` gets no such reason."',
        {"build_reasons": reasons_adding(reviewed_without_provenance)},
    ),
    "results_not_reviewed_unrequired": mutant(
        "`not_reviewed` given where the requirement holds no `review`",
        'declarations.md:192-193 "A requirement holding it gives" and "`unknown` with the reason '
        '`not_reviewed`"',
        {"build_reasons": reasons_adding(unreviewed_unrequired)},
    ),
    "results_not_reviewed_as_not_met": mutant(
        "`not_reviewed` making the status `not_met`",
        'declarations.md:192-193 "A requirement holding it gives" and "`unknown` with the reason '
        '`not_reviewed`"',
        {"status_of": status_from(not_reviewed_not_met)},
    ),
    "results_build_reasons_leave_the_status": mutant(
        "the build's own reasons leaving the read's status",
        'declarations.md:305-306 "join the read\'s, and the" and "result\'s status is the worst of them all"',
        {"status_of": status_from(worst_without_the_build)},
    ),
    "results_not_reviewed_lowers_not_met": mutant(
        "`not_reviewed` making the status `unknown` over a read's `not_met` (R05)",
        'declarations.md:305-306 "join the read\'s, and the" and "result\'s status is the worst of them all"',
        {"status_of": status_from(not_reviewed_unknown)},
    ),
    "results_best_status": mutant(
        "the status the best of the reasons",
        'declarations.md:305-306 "join the read\'s, and the" and "result\'s status is the worst of them all"',
        {"status_of": status_from(best_of)},
    ),
    "results_value_dropped_by_the_build": mutant(
        "the read's `value` dropped where the build's `label_mismatch` makes the result `not_met`",
        'declarations.md:306-307 "Every other member of the result is as the read returned it," and '
        '"including `value`, where the read returned one"',
        {"field_result": field_result_changed(value_dropped_by_the_build)},
    ),
    "results_unrequired_field_read": mutant(
        "a field in `reads` with no requirement read as if wanted as a value",
        'declarations.md:162 "the build reads nothing for it, so its result holds `status`,"',
        {"field_result": unrequired_field_read},
    ),
    # What the read applied (HP43 `judge`)
    "results_given_counted_applied": mutant(
        "every acceptance given counted applied (an implied condition that filled nothing, an "
        "extrapolation at an `at_edge` read)",
        'declarations.md:287-288 "An implied condition, nominal, extrapolation or `trainable`" and '
        '"acceptance given and not so shown was not applied"',
        {"applied_by": given_applied},
    ),
    "results_implied_applied_only_where_the_specimen_states_it": mutant(
        "an implied condition that filled a condition counted applied only where the field's specimen states "
        "its fact and token",
        'declarations.md:285-286 "condition (a `conditions` entry whose `record` is the value the implied '
        'condition supplies, with basis"',
        {"field_result": implied_applied_where_the_specimen_states_it},
    ),
    "results_implied_value_of_the_first_entry_supplied": mutant(
        "an implied condition's value taken from its first `implies` entry, whatever the condition an entry "
        "names",
        'declarations.md:285-286 "condition (a `conditions` entry whose `record` is the value the implied '
        'condition supplies, with basis"',
        {"filled": filled_by_the_first_entry_supplied},
    ),
    "results_numbers_compared_by_equality": mutant(
        "JSON compared by `==`, so that an implied condition supplying `-0` fills a condition showing `0`",
        'record_format.md:70-72 "Every number is the IEEE 754 double nearest it, ties to even, integers '
        'included:" and "`1e-400` as `0` and `-1e-400` as `-0`), as JavaScript reads them."',
        {"same": numbers_equal},
        "the text reads `-0` as a double of its own but states no equality for the value an implied "
        "condition supplies, so no direct check pins the model's bit-for-bit comparison against `==`; only "
        "an implied condition supplying `-0` beside the entry the read made from one supplying `0` "
        "separates them, and which the text means is S7a-2p's to settle with the maintainer",
    ),
    "results_extrapolation_applied_under_any_assumption": mutant(
        "a given extrapolation counted applied whenever the result rests on an `assumption`, a nominal's too",
        'read_side_contract.md:133 "the declaration it rests on, as `{"acceptance"}` with its kind\'s own '
        'members as the request gives them"',
        {"applied_by": extrapolation_applied_under_any_assumption},
    ),
    "results_implied_filled_whatever_the_basis": mutant(
        "an implied condition counted applied where an entry holds its value with a basis other than "
        "`implied`",
        'declarations.md:285-286 "condition (a `conditions` entry whose `record` is the value the implied '
        'condition supplies, with basis"',
        {"filled": filled_whatever_the_basis},
    ),
    "results_first_implied_only": mutant(
        "of two implied conditions that agree, the first alone counted applied",
        'declarations.md:285-286 "condition (a `conditions` entry whose `record` is the value the implied '
        'condition supplies, with basis"',
        {"applied_by": first_implied_only},
    ),
    "results_applied_indexed_among_the_given": mutant(
        "an applied acceptance indexed among those given, not in the model's `acceptances`",
        'declarations.md:303-304 "It maps the ones the read" and "applied to their indexes in the '
        "model's `acceptances` for `accepted_by`\"",
        {"applied_by": indexed_among_the_given},
    ),
    "results_assumption_named_by_kind": mutant(
        "an `assumption` taken to name every acceptance of its kind",
        'read_side_contract.md:133 "the declaration it rests on, as `{"acceptance"}` with its kind\'s '
        'own members as the request gives them"',
        {"names": named_by_kind},
        "a read applies one nominal or extrapolation, the one given for its field at its record, two of "
        "one kind being `request_incomplete`, and an acceptance of the kind elsewhere is neither given nor "
        "located at the result: which one an `assumption` names never differs",
    ),
    "results_applied_uncited": mutant(
        "`accepted_by` without the acceptances the read applied",
        'declarations.md:243 "acceptance used, the ones the read itself applied (a pick, an overlay, an '
        'implied condition) included."',
        {"judge": applied_uncited},
    ),
    # Covers (HP43 `_covers`, `_located_at`)
    "results_waiver_covers_not_met": mutant(
        "a waiver covering a reason no row of section 4.2 lists for it (`condition_outside`, `form_invalid`)",
        'declarations.md:388-389 "This table is the only place that says which acceptance covers which '
        'reason (other documents cite it). A" and "reason not listed is never accepted"',
        {"ROW_OF": rows_changed(waiver_of_any_code)},
    ),
    "results_waiver_condition_ignored": mutant(
        "a waiver covering a condition reason whatever condition it names",
        'declarations.md:393 "| a `waiver` naming that condition and code |"',
        {"ROW_OF": rows_changed(conditions_unnamed)},
    ),
    "results_waiver_code_ignored": mutant(
        "a waiver covering a reason of its row whatever code it names",
        'declarations.md:393 "| a `waiver` naming that condition and code |"',
        {"ROW_OF": rows_changed(codes_unnamed)},
    ),
    "results_waiver_field_ignored": mutant(
        "an acceptance covering a reason of a result whatever field it names",
        'declarations.md:291-292 "An acceptance **covers** a reason or" and "a specimen difference of a '
        "result when it names the result's field\"",
        {"covers": covers_changed(field_taken)},
    ),
    "results_location_ignored": mutant(
        "an acceptance covering a reason of a result whatever record it names",
        "declarations.md:293 \"located at the result's location, and is of a kind section 4.2's row for "
        'that reason names"',
        {"covers": covers_changed(location_taken)},
    ),
    "results_located_by_id_alone": mutant(
        "an acceptance located at a record by its `id` alone (R06)",
        'declarations.md:289-290 "when it names the record read, equal in `id`, `version`" and "and '
        '`content_hash`; one located at a region or an interval is located at no record"',
        {"located_at": located_by_id},
    ),
    "results_located_ignoring_the_version": mutant(
        "an acceptance located at a record by its `id` and `content_hash`, its `version` ignored",
        'declarations.md:289-290 "when it names the record read, equal in `id`, `version`" and "and '
        '`content_hash`; one located at a region or an interval is located at no record"',
        {"located_at": located_by("id", "content_hash")},
    ),
    "results_located_ignoring_the_id": mutant(
        "an acceptance located at a record by its `version` and `content_hash`, its `id` ignored",
        'declarations.md:289-290 "when it names the record read, equal in `id`, `version`" and "and '
        '`content_hash`; one located at a region or an interval is located at no record"',
        {"located_at": located_by("version", "content_hash")},
    ),
    "results_region_located_at_a_record": mutant(
        "an acceptance naming a region or an interval beside the record located at that record",
        'declarations.md:290 "one located at a region or an interval is located at no record"',
        {"located_at": region_at_a_record},
        "a declaration that passes its own check names no region or interval unless the build claims the "
        "scene suite, under which the model gives no verdict",
    ),
    "results_alternative_reasons_uncovered": mutant(
        "a waiver covering no reason that carries an `alternative` (R07)",
        'declarations.md:404 "A waiver covers a reason whatever its `alternative`"',
        {"covers": covers_changed(alternatives_uncovered)},
    ),
    "results_nominal_covers_without_assumption": mutant(
        "a nominal covering `want_mismatch` where the result's `assumption` does not name it, step 0's "
        "among them",
        'declarations.md:398 "a `nominal`, only on a result whose `assumption` names it"',
        {"ROW_OF": rows_changed(assumption_unnamed("want_mismatch"))},
    ),
    "results_extrapolation_covers_without_assumption": mutant(
        "an extrapolation covering `outside_range` where the result's `assumption` does not name it",
        'declarations.md:397 "an `extrapolation`, only on a result whose `assumption` names it"',
        {"ROW_OF": rows_changed(assumption_unnamed("outside_range"))},
    ),
    "results_extrapolation_covers_at_edge": mutant(
        "an extrapolation covering `at_edge`",
        'declarations.md:388-389 "This table is the only place that says which acceptance covers which '
        'reason (other documents cite it). A" and "reason not listed is never accepted"',
        {"ROW_OF": rows_changed(covered_like("at_edge", "range_unstated"))},
    ),
    "results_waiver_covers_label_mismatch": mutant(
        "a waiver naming `label_mismatch` covering it",
        'declarations.md:388-389 "This table is the only place that says which acceptance covers which '
        'reason (other documents cite it). A" and "reason not listed is never accepted"',
        {"ROW_OF": rows_changed(covered_like("label_mismatch", "not_reviewed"))},
    ),
    "results_waiver_covers_no_pick": mutant(
        "a waiver naming `no_pick` covering it",
        'declarations.md:395 "| `no_pick` | unknown | a `pick` only |"',
        {"ROW_OF": rows_changed(covered_like("no_pick", "not_reviewed"))},
    ),
    "results_condition_unknown_name_waivable": mutant(
        "a waiver naming `condition_unknown_name` and its condition covering it",
        "OPEN_POINTS: condition_unknown_name_never_covered",
        {"ROW_OF": rows_changed(covered_like("condition_unknown_name", "condition_unstated"))},
        "the condition a `condition_unknown_name` carries is one the reader's version does not register, "
        "and a waiver naming it is refused at the declaration's own check (declarations.md:79 \"and a name "
        'a field or condition, one"), so no declaration read holds one',
    ),
    "results_label_resting_waiver_trusted": mutant(
        "a waiver naming a label covering as one naming none, whatever the label's trust",
        'declarations.md:381 "It covers its reason only on a result whose stored label"',
        {"covers": covers_changed(label_trusted)},
    ),
    "results_label_resting_waiver_undecided_anywhere": mutant(
        "a waiver naming a label given no verdict though it covers nothing by the other tests",
        'declarations.md:291-293 "An acceptance **covers** a reason or" ... "located at the result\'s '
        "location, and is of a kind section 4.2's row for that reason names\"",
        {"covers": covers_changed(label_undecided_anywhere)},
    ),
    "results_label_resting_waiver_undecided_before_its_code": mutant(
        "a waiver naming a label given no verdict before its code is tested against the reason's",
        'declarations.md:291-293 "An acceptance **covers** a reason or" ... "located at the result\'s '
        "location, and is of a kind section 4.2's row for that reason names\"",
        {"covers": covers_changed(label_undecided_after(nothing_tested))},
    ),
    "results_label_resting_waiver_undecided_before_its_condition": mutant(
        "a waiver naming a label given no verdict before its condition is tested against the reason's",
        'declarations.md:291-293 "An acceptance **covers** a reason or" ... "located at the result\'s '
        "location, and is of a kind section 4.2's row for that reason names\"",
        {"covers": covers_changed(label_undecided_after(code_named))},
    ),
    # The judgement and `unused` (HP43 `judge`, `unused`)
    "results_another_model_s_acceptances": mutant(
        "a model's reason covered by another model's acceptance (R02)",
        'declarations.md:242 "section 4.2 says, and `accepted_by` lists the 0-based indexes, in the '
        "model's `acceptances`, of every\"",
        {"report": report_from(judge_of=judged_by_every_model)},
    ),
    "results_covered_reasons_not_accepted": mutant(
        "`not_accepted` holding a covered reason",
        'declarations.md:244 "`not_accepted` lists each reason and each specimen difference that nothing '
        'covers, empty exactly"',
        {"judge": judged_changed(everything_not_accepted)},
    ),
    "results_acceptance_covering_nothing_cited": mutant(
        "`accepted_by` holding an acceptance of the result's field at its location that covered nothing",
        'declarations.md:297-298 "An acceptance is **used** where it covers a reason" and "or a specimen '
        'difference of a result, or a read applied it."',
        {"judge": judged_changed(every_acceptance_of_the_field_cited)},
    ),
    "results_build_reasons_unjudged": mutant(
        "the build's own reasons left out of the judgement, so a `label_mismatch` refuses nothing",
        'declarations.md:241 "`accepted` is true when each reason and each specimen difference of the '
        'result is covered as the table in"',
        {"judge": build_reasons_unjudged},
    ),
    "results_status_raised_when_accepted": mutant(
        "an accepted result's status made `met`",
        'declarations.md:234-235 "It states a fact about the record against the" and "requirement, and '
        'declarations never change it"',
        {"judge": judged_changed(status_raised_when_accepted)},
    ),
    "results_specimen_differences_left_out": mutant(
        "a result without `specimen_differences`",
        'declarations.md:212 "with `model`, the location it was read for, `record`, `field`, '
        '`specimen_differences`, `accepted`,"',
        {"judge": judged_changed(specimen_differences_left_out)},
    ),
    "results_unused_lists_the_applied": mutant(
        "an acceptance the read applied, and that covered nothing, listed in `unused`",
        'declarations.md:297-298 "An acceptance is **used** where it covers a reason" and "or a specimen '
        'difference of a result, or a read applied it."',
        {"report": report_from(unused_of=unused_without_the_applied)},
    ),
    "results_unused_named_after_the_first_model": mutant(
        "each acceptance unused named after the first model (R01)",
        'declarations.md:312 "The build lists in `unused`, per model, each acceptance not used (the '
        "build's terms)\"",
        {"report": report_from(unused_of=unused_after_the_first)},
    ),
    "results_unused_shared_by_the_models": mutant(
        "one set of used acceptances shared by every model (R03)",
        'declarations.md:312 "The build lists in `unused`, per model, each acceptance not used (the '
        "build's terms)\"",
        {"report": report_from(unused_of=unused_shared)},
    ),
    "results_used_listed_unused": mutant(
        "every acceptance listed in `unused`, used or not",
        'declarations.md:312 "The build lists in `unused`, per model, each acceptance not used (the '
        "build's terms)\"",
        {"unused_of": unused_listing_every_one},
    ),
    # The results and the verdict (HP44 `check_build`, HP46)
    "results_every_record_of_the_store_read": mutant(
        "every record in the store read, listed or not",
        'declarations.md:210 "The build reads every required field in every region, interval or record a '
        'model is checked over"',
        {"model_results": every_record_of_the_store},
    ),
    "results_one_result_a_field": mutant(
        "the results de-duplicated by field alone",
        'declarations.md:210-211 "The build reads every required field in every region, interval or record '
        'a model is checked over" and "and returns one result each"',
        {"report": report_from(results_of=one_result_a_field)},
    ),
    "results_refused_by_the_first_model": mutant(
        "the verdict read from the first model's results alone",
        'declarations.md:246 "The build MUST refuse to build while any result is not accepted, and reports '
        'every such result, not only"',
        {"Report.refused": property(refused_by_the_first_model)},
    ),
    "results_never_refused": mutant(
        "no refusal while a result is not accepted",
        'declarations.md:246 "The build MUST refuse to build while any result is not accepted, and reports '
        'every such result, not only"',
        {"Report.refused": property(never_refused)},
    ),
    "results_unresolved_record_listed": mutant(
        "a record listed in `records` though its read resolved none",
        'declarations.md:251 "`records`, every record a read resolved, as `{"id", "version", '
        '"content_hash"}`"',
        {"field_result": field_result_changed(every_listed_record_resolved)},
    ),
    "results_unread_record_listed": mutant(
        "a record listed in `records` though nothing was read for it (a field with no requirement)",
        'declarations.md:251 "`records`, every record a read resolved, as `{"id", "version", '
        '"content_hash"}`"',
        {"field_result": field_result_changed(unread_record_resolved)},
    ),
    "results_later_pieces_decided": mutant(
        "a target naming a fact, combinations or a `trainable` entry decided as if absent",
        'declarations.md:318 "For each fact the target names, the build compares the record\'s fact"',
        {"later_pieces": later_pieces_decided},
    ),
    "results_found_before_the_field_by_absent_alone": mutant(
        "a read refused at steps 1 to 6 for a reason other than `absent` taken to have found the field",
        "OPEN_POINTS: label_of_no_stored_value",
        {"BEFORE_THE_FIELD": ("absent",)},
    ),
    "results_other_version_taken_to_find_the_field": mutant(
        "a record refused as `other_version` taken to have found the field, its label checked",
        'declarations.md:309-310 "A result that rests on no stored value (its" and "record or field not '
        'found, a refusal before step 7 finds the field, or no single alternative:"',
        {"BEFORE_THE_FIELD": before_the_field_without("other_version")},
    ),
    "results_malformed_taken_to_find_the_field": mutant(
        "a record refused as `malformed` taken to have found the field, its label checked",
        'declarations.md:309-310 "A result that rests on no stored value (its" and "record or field not '
        'found, a refusal before step 7 finds the field, or no single alternative:"',
        {"BEFORE_THE_FIELD": before_the_field_without("malformed")},
    ),
    "results_unknown_type_taken_to_find_the_field": mutant(
        "a record refused as `unknown_type` taken to have found the field, its label checked",
        'declarations.md:309-310 "A result that rests on no stored value (its" and "record or field not '
        'found, a refusal before step 7 finds the field, or no single alternative:"',
        {"BEFORE_THE_FIELD": before_the_field_without("unknown_type")},
    ),
    "results_later_pieces_of_the_first_model_alone": mutant(
        "a target naming a fact, combinations or a `trainable` entry looked for in the first model alone",
        'declarations.md:318 "For each fact the target names, the build compares the record\'s fact"',
        {"report": report_from(pieces_of=first_model_alone)},
    ),
    "results_unnamed_alternative_decided_as_none": mutant(
        "the alternative a result rests on, where none is named among labels that differ, taken to be none",
        "OPEN_POINTS: alternative_a_result_rests_on",
        {"stored_value": alternative_unnamed_decided(no_alternative)},
    ),
    "results_unnamed_alternative_decided_as_the_first": mutant(
        "the alternative a result rests on, where none is named among labels that differ, taken to be the "
        "first",
        "OPEN_POINTS: alternative_a_result_rests_on",
        {"stored_value": alternative_unnamed_decided(first_alternative)},
    ),
    "results_read_without_a_verdict_decided": mutant(
        "a read the read model gives no verdict on taken as a read that gives no reason",
        'declarations.md:306-307 "Every other member of the result is as the read returned it," and '
        '"including `value`, where the read returned one"',
        {"read_of": read_undecided_as_no_reason},
    ),
    "results_step_0_read_without_a_verdict_decided": mutant(
        "the read over no records, to tell step 0, that the read model gives no verdict on taken as passing",
        "OPEN_POINTS: label_of_no_stored_value",
        {"read_of": step_0_read_undecided_as_passed},
    ),
}
