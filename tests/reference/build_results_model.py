# SPDX-License-Identifier: Apache-2.0
"""A test-only reference model of what a build gives a declaration that passes its own check: the reads, the
results, the verdict and the report, written from the specification's text alone (`declarations.md` sections
1, 2 and 4.2, and the build's terms of section 2), for the build-check cases (`test_cases.py`) and HP43 to
HP46.

It never ships and imports nothing from `materica`, at any depth (`test_layering.py`). It takes the
declaration's own check from `build_model.py` and reads through the read model (`read_model.read`), never
through the implementation's read.

**What it decides.** For each model, each record its `checked_over` lists and each field it reads, in that
order: the request the build gives the read, the read, the build's own reasons (`no_requirement`,
`label_mismatch`, `not_reviewed`), the status law, the acceptances the read applied, the judgement by section
4.2's table, held here as the model's own data (`COVERAGE`), `accepted_by`, `not_accepted`, `unused`, the
verdict and the report.

**What it does not.** `NoVerdict`, never a pass, for each kind `UNDECIDED` names: a waiver resting on a label
that would cover a reason but for label trust, which comes after 0.1.0.dev4; a target naming a fact, or
`combinations` (S7a-3); a `trainable` entry (S7a-4); the report's watches (S7a-4); a pick, an overlay or a row
of section 4.2 that only they reach (S7c); the alternative a result rests on, where the result does not name
it and the alternatives are stored otherwise; and a read the read model gives no verdict on. The
declaration's own check, and its no verdict for a claimed suite or a pick or an overlay, are
`build_model.py`'s.

**Where the text is silent.** The model takes the maintainer's ruling where there is one, else the fail-closed
choice. Each such point is listed once in `OPEN_POINTS`, and named where it is applied ("Open point:
<name>")."""

import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Final

from tests.reference import build_model, read_model
from tests.reference.read_model import REASONS, NoVerdict, Status
from tests.reference.strict_json import JsonObject, JsonValue, parse

OPEN_POINTS: Final = {
    "two_implied_that_agree": (
        "an implied condition given to a read was applied where it applies to the field read (its specimen "
        "states its fact and token) and a condition entry shows its value with basis `implied`, so two that "
        "agree and both apply are both cited in `accepted_by` (the S7 design's choice); one whose fact and "
        "token the specimen does not state filled nothing, though its value equal the entry's, and is not "
        "(the fail-closed choice: unused, so that the consumer sees it did nothing)"
    ),
    "label_of_no_stored_value": (
        "a result that rests on no stored value is checked against no label, as the text says; a refusal "
        "before step 7 finds the field is told by the read itself: a read of the same request over no "
        "records that gives anything but `absent` was refused at step 0, and a reason given only before "
        "step 7, or `absent`, ends the read before the field is found"
    ),
    "alternative_a_result_rests_on": (
        "a result over alternatives rests on one alternative exactly where it holds `conditions`; the "
        "alternative is the one its reasons name, and where none names one the model decides only if every "
        "alternative stores the same label and specimen, else gives no verdict, since only step 7 says which "
        "one is left"
    ),
    "condition_unknown_name_never_covered": (
        "`condition_unknown_name` is covered by nothing (the maintainer's ruling of 2026-10-24, whose words "
        "land with S7a-1b's first commit, section 4.2's first row then naming three codes, pending until it "
        "is on `main`); `main`'s text lists it in the first row, but no waiver that passes the declaration's "
        "own check names the unregistered condition such a reason carries, so the two readings never differ"
    ),
}

# What the model gives no verdict on, by kind (`exceptions.RESULTS_NOT_DECIDED` gives each kind's reason).
UNDECIDED: Final = {
    "label_trust": "a waiver resting on a label, whose coverage rests on label trust (after 0.1.0.dev4)",
    "specimen_differences": "a target naming a fact, or combinations (S7a-3)",
    "trainable": "a trainable entry (S7a-4)",
    "watches": "the report's watches (S7a-4)",
    "picks_and_overlays": "a row of section 4.2 that a pick or an overlay alone reaches (S7c)",
    "alternative_unnamed": "the unnamed alternative a result rests on, among alternatives stored otherwise",
    "the_read": "the read",
}


class _Undecided(Exception):
    def __init__(self, kind: str, detail: str = "") -> None:
        why = UNDECIDED[kind] + (f": {detail}" if detail else "")
        super().__init__(why)
        self.why = why


@dataclass(frozen=True)
class Row:
    """A row of section 4.2's table: the reasons it lists, their status, and what covers them, under the row's
    own condition (declarations.md:293-294 "is of a kind section 4.2's row for that reason names, under that
    row's own condition (the code and condition named; the `assumption`)")."""

    reasons: tuple[str, ...]
    status: str
    kind: str
    names_code: bool = False
    names_condition: bool = False
    on_assumption: bool = False
    qualifier: str = ""  # the row's words beside its codes, which the model holds by `on_assumption`
    condition_reasons: bool = False  # every `condition_*` reason
    differences: bool = False  # a specimen difference
    undecided: str | None = None  # the kind of `UNDECIDED` the row's condition needs


# declarations.md:388-389 "This table is the only place that says which acceptance covers which reason (other
# documents cite it). A" and "reason not listed is never accepted"
COVERAGE: Final = (
    # declarations.md:393 "| a `waiver` naming that condition and code |"; Open point:
    # condition_unknown_name_never_covered.
    Row(("condition_unstated", "condition_unchecked", "condition_uncertain"), "unknown", "waiver",
        names_code=True, names_condition=True),
    # declarations.md:394 "`entries_withheld`, `not_reviewed` | unknown | a `waiver` naming that code |"
    Row(("no_requirement", "stated_without_origin", "outside_check_points", "fill_in_version_mismatch",
         "entries_withheld", "not_reviewed"), "unknown", "waiver", names_code=True),
    # declarations.md:395 "| `no_pick` | unknown | a `pick` only |"
    Row(("no_pick",), "unknown", "pick", undecided="picks_and_overlays"),
    # declarations.md:396 "| `range_unstated`, `outside_coverage` | unknown | an `extrapolation` only |"
    Row(("range_unstated", "outside_coverage"), "unknown", "extrapolation"),
    # declarations.md:397 "an `extrapolation`, only on a result whose `assumption` names it"
    Row(("outside_range",), "not_met", "extrapolation", on_assumption=True),
    # declarations.md:398 "a `nominal`, only on a result whose `assumption` names it"
    Row(("want_mismatch",), "not_met", "nominal", on_assumption=True,
        qualifier="for a value read from an interval, or a vector read from a parameter set with none"),
    # declarations.md:399 "| `engine_mass_not_comparable` | unknown | a `waiver` naming that code |"
    Row(("engine_mass_not_comparable",), "unknown", "waiver", names_code=True),
    # declarations.md:400 "an `overlay_scope` naming every member that differs"
    Row(("overlay_scope_mismatch",), "not_met", "overlay_scope", undecided="picks_and_overlays"),
    # declarations.md:401 "| a specimen difference | (not a status) | an `accepted_difference` |"
    Row((), "(not a status)", "accepted_difference", differences=True, undecided="specimen_differences"),
    # declarations.md:402 "on a field listed in `trainable` | any | its `trainable` entry (section 7), on a"
    Row(("outside_range", "range_unstated", "outside_coverage"), "any", "trainable",
        qualifier="on a field listed in `trainable`", condition_reasons=True, differences=True,
        undecided="trainable"),
)  # fmt: skip
# The row of each reason, the trainable entry's aside: a model with a `trainable` entry gives no verdict.
ROW_OF: Final = {code: row for row in COVERAGE if row.kind != "trainable" for code in row.reasons}

# read_side_contract.md:64-65 "take only the kinds `pick`, `overlay`, `extrapolation`, `nominal`," and
# "`implied_condition` and `trainable`"; declarations.md:302 "section 1), overlays aside (which overlays it
# gives a read is [not yet covered]), that name the read's field": a `trainable` acceptance is section 7's,
# made from a `trainable` entry, on which the model gives no verdict.
GIVEN_KINDS: Final = ("pick", "extrapolation", "nominal", "implied_condition")
REFERENCE: Final = ("id", "version", "content_hash")
# read_side_contract.md:380 "| Code | Status | Step | Meaning | Defined in |": the reasons given only before
# step 7, and `absent`, which at step 7 is the field not found: each ends a read before the field is found.
BEFORE_THE_FIELD: Final = (
    *(code for code, row in REASONS.items() if row.steps and max(row.steps) < 7),
    "absent",
)


@dataclass(frozen=True)
class Stored:
    """The value a result rests on, as stored (the field, or the alternative read), and its section."""

    value: JsonValue
    section: JsonObject

    @property
    def label(self) -> JsonValue:
        return members(self.value).get("label")

    @property
    def specimen(self) -> JsonObject:
        # read_side_contract.md:129 "the field's specimen facts, the section's merged with the field's";
        # record_format.md:145-146 "A field's own `specimen` overrides the section's, fact by fact."
        return {**members(self.section.get("specimen")), **members(members(self.value).get("specimen"))}


@dataclass(frozen=True)
class Made:
    """One result as the build makes it, before it is judged: the acceptances given to its read, and those
    the read applied, by index in its model's `acceptances`."""

    result: JsonObject
    given: tuple[int, ...] = ()
    applied: tuple[int, ...] = ()
    resolved: JsonObject | None = None  # the record the read resolved


@dataclass(frozen=True)
class Report:
    """The build's report (declarations.md:249 "The build gives one report:"): no refusal, each result judged,
    the acceptances unused, and the members the model does not decide, by kind."""

    consumer: JsonValue
    records: tuple[JsonObject, ...]
    declaration: JsonObject
    results: tuple[JsonObject, ...]
    unused: tuple[JsonObject, ...]
    undecided: dict[str, str] = field(default_factory=lambda: {"watches": UNDECIDED["watches"]})

    @property
    def refused(self) -> bool:
        # declarations.md:246 "The build MUST refuse to build while any result is not accepted, and reports
        # every such result, not only"
        return any(result["accepted"] is not True for result in self.results)

    def to_json(self) -> JsonObject:
        # declarations.md:249-251 "The build gives one report:" and "`records`, every record a read resolved,
        # as"; the watches are S7a-4's, and a build that does not emit them leaves them out
        return {
            "consumer": self.consumer,
            "records": list(self.records),
            "declaration": self.declaration,
            "refusals": [],
            "results": list(self.results),
            "unused": list(self.unused),
        }


def members(value: JsonValue) -> JsonObject:
    return value if isinstance(value, dict) else {}


def entries(value: JsonValue) -> list[JsonValue]:
    return value if isinstance(value, list) else []


def same(one: JsonValue, other: JsonValue) -> bool:
    """Equal JSON, numbers bit for bit (`record_format.md` section 1 item 6), so that `0` and `-0` differ."""
    if isinstance(one, float) and isinstance(other, float):
        return struct.pack(">d", one) == struct.pack(">d", other)
    if isinstance(one, list) and isinstance(other, list):
        return len(one) == len(other) and all(map(same, one, other))
    if isinstance(one, dict) and isinstance(other, dict):
        return one.keys() == other.keys() and all(same(one[name], other[name]) for name in one)
    return type(one) is type(other) and one == other


def check_build(
    text: bytes, sources: Sequence[bytes], claims: frozenset[str]
) -> Report | build_model.Refused | NoVerdict:
    """The build's answer, claiming `claims`, to a declaration given as the text a case supplies, over the
    records `sources` supplies."""
    own = build_model.check_build(text, claims)
    if not (isinstance(own, NoVerdict) and own.why == build_model.PAST_THE_DECLARATION):
        return own
    declaration = members(parse(text))
    try:
        return report(declaration, sources, claims)
    except _Undecided as undecided:
        return NoVerdict(undecided.why)


def report(declaration: JsonObject, sources: Sequence[bytes], claims: frozenset[str]) -> Report:
    results: list[JsonObject] = []
    unused: list[JsonObject] = []
    records: list[JsonObject] = []
    for model in entries(declaration.get("models")):
        later_pieces(members(model))
        made = model_results(declaration, members(model), sources, claims)
        judged = [judge(one, members(model)) for one in made]
        results.extend(judged)
        unused.extend(unused_of(members(model), judged))
        records.extend(one.resolved for one in made if one.resolved is not None)
    return Report(
        declaration.get("consumer"), tuple(distinct(records)), declaration, tuple(results), tuple(unused)
    )


def later_pieces(model: JsonObject) -> None:
    # declarations.md:318 "For each fact the target names, the build compares the record's fact"; a target
    # of `{}` names none (declarations.md:78-79 "a `target` of `{}` names no fact"), so a result lists no
    # specimen difference
    if members(model.get("target")) or entries(model.get("combinations")):
        raise _Undecided("specimen_differences")
    # declarations.md:461-462 "The build gives each read of that field there a `trainable` acceptance"
    if entries(model.get("trainable")):
        raise _Undecided("trainable")


def model_results(
    declaration: JsonObject, model: JsonObject, sources: Sequence[bytes], claims: frozenset[str]
) -> list[Made]:
    """One result per record listed and field read, in that order: declarations.md:210 "The build reads every
    required field in every region, interval or record a model is checked over"."""
    requirements = {
        str(members(requirement).get("field")): members(requirement)
        for requirement in entries(model.get("requirements"))
    }
    return [
        field_result(
            declaration, model, members(record), str(name), requirements.get(str(name)), sources, claims
        )
        for record in entries(members(model.get("checked_over")).get("records"))
        for name in entries(model.get("reads"))
    ]


def field_result(
    declaration: JsonObject,
    model: JsonObject,
    record: JsonObject,
    name: str,
    requirement: JsonObject | None,
    sources: Sequence[bytes],
    claims: frozenset[str],
) -> Made:
    # declarations.md:212 "with `model`, the location it was read for, `record`, `field`,
    # `specimen_differences`, `accepted`,"; declarations.md:236-237 "Over records the location is the record
    # read: the result holds" and "`record` and neither `region` nor `interval`"
    location: JsonObject = {"model": members(model.get("model")).get("name"), "record": record, "field": name}
    if requirement is None:
        # declarations.md:161-163 "A field in `reads` with no requirement gives" ... "the build reads nothing
        # for it, so its result holds `status`," and "`reasons` and the build's members alone"
        return Made({"status": "unknown", "reasons": [{"code": "no_requirement"}], **location})
    acceptances = entries(model.get("acceptances"))
    given = given_to(acceptances, record, name)
    request = request_for(declaration, record, name, requirement, [acceptances[index] for index in given])
    read = read_model.read(request, sources, claims)
    if isinstance(read, NoVerdict):
        raise _Undecided("the_read", read.why)
    passed_step_0 = step_0_passes(request, claims)
    # The stored value is looked for only where a label is required or an implied condition is given: the
    # alternative a result rests on is not always known (Open point: alternative_a_result_rests_on).
    looked_for = "label" in requirement or any(
        members(acceptances[index]).get("acceptance") == "implied_condition" for index in given
    )
    stored = stored_value(read, record, name, sources) if passed_step_0 and looked_for else None
    reasons: list[JsonValue] = [*entries(read["reasons"]), *build_reasons(requirement, read, stored)]
    # declarations.md:305-307 "The build's own reasons (`no_requirement`, `label_mismatch`, `not_reviewed`)
    # join the read's, and the" ... "result's status is the worst of them all. Every other member of the
    # result is as the read returned it," and "including `value`, where the read returned one"
    result: JsonObject = {**read, "status": status_of(reasons), "reasons": reasons, **location}
    applied = applied_by(read, given, acceptances, stored)
    resolved = record if passed_step_0 and resolved_by_step_1(record, sources) else None
    return Made(result, given, applied, resolved)


def given_to(acceptances: Sequence[JsonValue], record: JsonObject, name: str) -> tuple[int, ...]:
    """declarations.md:301-303 "The build gives each read the acceptances of the kinds a read takes" ... "that
    name the read's field" and "and are located at its location"."""
    return tuple(
        index
        for index, acceptance in enumerate(acceptances)
        if members(acceptance).get("acceptance") in GIVEN_KINDS
        and members(acceptance).get("field") == name
        and located_at(members(acceptance), record)
    )


def located_at(acceptance: JsonObject, record: JsonObject) -> bool:
    """declarations.md:289-291 "is **located at** a result's location when it names the record read, equal in
    `id`, `version`" and "and `content_hash`; one located at a region or an interval is located at no
    record, and an accepted difference" ... "with no location is located at every location its model is
    checked over"."""
    if "region" in acceptance or "interval" in acceptance:
        return False
    if "record" not in acceptance:
        return acceptance.get("acceptance") == "accepted_difference"
    named = members(acceptance["record"])
    return all(name in named and named[name] == record.get(name) for name in REFERENCE)


def request_for(
    declaration: JsonObject,
    record: JsonObject,
    name: str,
    requirement: JsonObject,
    given: list[JsonValue],
) -> JsonObject:
    """declarations.md:300-301 "The build's own read request holds the requirement's `want` and `conditions`,
    and the declared operating" and "conditions. The build gives each read the acceptances", with the target
    the read is for (read_side_contract.md:14 "`{"record": {"id", "version", "content_hash"}, "field":
    "<section>.<field>"}`") and the acceptances given it; its records are supplied beside it."""
    return {
        "target": {"record": record, "field": name},
        "operating_conditions": declaration.get("operating_conditions", {}),
        "requirement": {
            member: requirement[member] for member in ("want", "conditions") if member in requirement
        },
        "acceptances": given,
    }


def step_0_passes(request: JsonObject, claims: frozenset[str]) -> bool:
    """Whether the request passes step 0, which the read makes before any record is read
    (read_side_contract.md:19-20 "and checked on its own before any record is" and "read (section 3, step
    0)"): a read of it over no records goes on to step 1, which finds no candidate and gives `absent`
    (read_side_contract.md:208-209 "the read gives `absent`, unless a supplied" and "source is unreadable").
    Open point: label_of_no_stored_value."""
    over_none = read_model.read(request, (), claims)
    if isinstance(over_none, NoVerdict):
        raise _Undecided("the_read", over_none.why)
    return same(over_none["reasons"], [{"code": "absent"}])


def pinned(record: JsonObject, sources: Sequence[bytes]) -> list[read_model.Source]:
    """The sources step 1 takes for the record: read_side_contract.md:210-211 "Among the candidates of the
    reference's `id` and `version`, the reader takes those whose stated" and "`content_hash` equals the
    reference's"."""
    return [
        source
        for source in read_model.sources_read(sources)
        if isinstance(source.value, dict)
        and read_model.candidate(source.value)
        and all(source.value.get(name) == record.get(name) for name in REFERENCE)
    ]


def resolved_by_step_1(record: JsonObject, sources: Sequence[bytes]) -> bool:
    # read_side_contract.md:211-213 "With one, the read goes on, whatever else was supplied" and "With two or
    # more whose bytes are all identical, it reads one; with two or more whose bytes differ, the read gives
    # `malformed`"
    found = pinned(record, sources)
    return bool(found) and len({source.data for source in found}) == 1


def stored_value(read: JsonObject, record: JsonObject, name: str, sources: Sequence[bytes]) -> Stored | None:
    """The value a result rests on, as stored, or None where it rests on none: declarations.md:308 "stored on
    the value the result rests on (the field, or the alternative read), whether or not the read" and
    declarations.md:309-310 "A result that rests on no stored value (its" and "record or field not found, a
    refusal before step 7 finds the field, or no single alternative:". The read passed step 0 (its caller
    asks). Open point: label_of_no_stored_value."""
    if any(members(reason).get("code") in BEFORE_THE_FIELD for reason in entries(read["reasons"])):
        return None
    found = pinned(record, sources)
    if not found:
        return None
    section, _, key = name.partition(".")
    value = found[0].value
    body = members(value).get("body") if isinstance(value, dict) else None
    held = members(members(members(body).get("sections")).get(section))
    field_value = members(held.get("fields")).get(key)
    if "alternatives" not in members(field_value):
        return Stored(field_value, held)
    # read_side_contract.md:302-303 "A result that rests on no single alternative, every outcome but one" and
    # "alternative left or picked, holds no `value`, `assumption` or `conditions`"
    if "conditions" not in read:
        return None
    alternatives = entries(members(field_value)["alternatives"])
    # read_side_contract.md:301 "Every reason found reading one alternative carries its `alternative`"
    named = {
        index
        for reason in entries(read["reasons"])
        if isinstance(index := members(reason).get("alternative"), float)
    }
    if len(named) == 1:
        (index,) = named
        if index.is_integer() and 0 <= index < len(alternatives):
            return Stored(alternatives[int(index)], held)
    # Open point: alternative_a_result_rests_on.
    stored = [Stored(alternative, held) for alternative in alternatives]
    if not named and all(
        same(one.label, stored[0].label) and one.specimen == stored[0].specimen for one in stored
    ):
        return stored[0]
    raise _Undecided("alternative_unnamed")


def build_reasons(requirement: JsonObject, read: JsonObject, stored: Stored | None) -> list[JsonObject]:
    """The build's own reasons on a field read under a requirement."""
    reasons: list[JsonObject] = []
    # declarations.md:171-172 "A requirement with a `label` gives `not_met` with the reason `label_mismatch`
    # when the label stored on the" and "value the result rests on differs or is absent"
    if "label" in requirement and stored is not None and not same(stored.label, requirement["label"]):
        reasons.append({"code": "label_mismatch"})
    # declarations.md:192-195 "A requirement holding it gives" ... "`unknown` with the reason `not_reviewed`
    # on a result whose `provenance.review`" ... "is not a completed review: one holding `result` `reviewed`"
    # and "A result that holds no `provenance` gets no such reason."
    if "review" in requirement and "provenance" in read and not completed(read["provenance"]):
        reasons.append({"code": "not_reviewed"})
    return reasons


def completed(provenance: JsonValue) -> bool:
    review = members(provenance).get("review")
    return isinstance(review, dict) and same(review.get("result"), "reviewed")


def status_of(reasons: Iterable[JsonValue]) -> Status:
    # read_side_contract.md:138 "The status is the worst of them: `not_met` over `unknown` over `met`"
    return read_model.worst(REASONS[str(members(reason).get("code"))].status for reason in reasons)


def applied_by(
    read: JsonObject, given: Sequence[int], acceptances: Sequence[JsonValue], stored: Stored | None
) -> tuple[int, ...]:
    """The acceptances given to the read that it applied: declarations.md:284-286 "A read **applied** an
    acceptance given to it where its result shows it: an implied condition that filled a" ... "a nominal or an
    extrapolation that the result's `assumption` names"; declarations.md:287-288 "An implied condition,
    nominal, extrapolation or `trainable` acceptance given and not so shown was not applied"."""
    applied: list[int] = []
    for index in given:
        acceptance = members(acceptances[index])
        kind = acceptance.get("acceptance")
        if (kind == "implied_condition" and filled(read, acceptance, stored)) or (
            kind in ("nominal", "extrapolation") and names(read.get("assumption"), acceptance)
        ):
            applied.append(index)
    return tuple(applied)


def filled(read: JsonObject, implied: JsonObject, stored: Stored | None) -> bool:
    """declarations.md:285-286 "condition (a `conditions` entry whose `record` is the value the implied
    condition supplies, with basis", by an implied condition that applies to the field read:
    declarations.md:351 "supplies a value for a condition the record leaves unstated, on fields whose specimen
    states that fact and token". Open point: two_implied_that_agree."""
    fact = members((stored.specimen if stored is not None else {}).get(str(implied.get("fact"))))
    if "status" in fact or not same(fact.get("token"), implied.get("token")):
        return False
    for entry in entries(read.get("conditions")):
        held = members(members(entry).get("record"))
        supplied = members(members(implied.get("implies")).get(str(members(entry).get("name"))))
        if supplied and same(held, {**without_basis(supplied), "basis": "implied"}):
            return True
    return False


def without_basis(value: JsonObject) -> JsonObject:
    # declarations.md:351 "a record condition's shapes without `basis` (one there is ignored)"
    return {name: held for name, held in value.items() if name != "basis"}


def names(assumption: JsonValue, acceptance: JsonObject) -> bool:
    """Whether a result's `assumption` names the acceptance: read_side_contract.md:133 "the declaration it
    rests on, as `{"acceptance"}` with its kind's own members as the request gives them, `basis` aside"."""
    kind = str(acceptance.get("acceptance"))
    own = {
        name: acceptance[name] for name in read_model.ACCEPTANCE_OWN_NAMES.get(kind, ()) if name in acceptance
    }
    return same(assumption, {"acceptance": kind, **own})


def covers(acceptance: JsonObject, reason: JsonObject, result: JsonObject) -> bool:
    """declarations.md:291-295 "An acceptance **covers** a reason or" ... "a specimen difference of a result
    when it names the result's field" ... "located at the result's location, and is of a kind section 4.2's
    row for that reason names" ... "own condition (the code and condition named; the `assumption`), and, for a
    waiver naming a label, as section" and "4.1 item 4 says. A label is **trusted** on a result";
    declarations.md:404 "A waiver covers a reason whatever its `alternative`"."""
    code = reason.get("code")
    row = ROW_OF.get(str(code))
    if row is None or acceptance.get("acceptance") != row.kind:
        return False
    if acceptance.get("field") != result["field"] or not located_at(acceptance, members(result["record"])):
        return False
    if row.names_code and not same(acceptance.get("code"), code):
        return False
    if row.names_condition and not same(acceptance.get("condition"), reason.get("condition")):
        return False
    if row.on_assumption and not names(result.get("assumption"), acceptance):
        return False
    if row.undecided is not None:
        raise _Undecided(row.undecided)
    if "label" in acceptance:
        # declarations.md:381 "It covers its reason only on a result whose stored label"
        raise _Undecided("label_trust")
    return True


def judge(made: Made, model: JsonObject) -> JsonObject:
    """The result judged: declarations.md:241-244 "`accepted` is true when each reason and each specimen
    difference of the result is covered as the table in" ... "section 4.2 says, and `accepted_by` lists the
    0-based indexes, in the model's `acceptances`, of every" ... "acceptance used, the ones the read itself
    applied (a pick, an overlay, an implied condition) included." and "`not_accepted` lists each reason and
    each specimen difference that nothing covers, empty exactly"."""
    acceptances = entries(model.get("acceptances"))
    used = set(made.applied)
    uncovered: list[JsonValue] = []
    for reason in entries(made.result["reasons"]):
        covering = {
            index
            for index, acceptance in enumerate(acceptances)
            if covers(members(acceptance), members(reason), made.result)
        }
        used |= covering
        if not covering:
            uncovered.append(reason)
    # declarations.md:324-325 "A result that holds no `specimen`" ... "lists no specimen differences", and a
    # target naming no fact gives none (`later_pieces`)
    return {
        **made.result,
        "specimen_differences": [],
        "accepted": not uncovered,
        "accepted_by": [float(index) for index in sorted(used)],
        "not_accepted": uncovered,
    }


def unused_of(model: JsonObject, judged: Sequence[JsonObject]) -> list[JsonObject]:
    """declarations.md:312 "The build lists in `unused`, per model, each acceptance not used (the build's
    terms)"; declarations.md:297-298 "An acceptance is **used** where it covers a reason or a
    specimen difference of a result, or a read applied it": the indexes `accepted_by` lists, per result."""
    used = {
        index for result in judged for index in entries(result["accepted_by"]) if isinstance(index, float)
    }
    name = members(model.get("model")).get("name")
    return [
        {"model": name, "acceptance": float(index)}
        for index in range(len(entries(model.get("acceptances"))))
        if float(index) not in used
    ]


def distinct(records: Iterable[JsonObject]) -> list[JsonObject]:
    # declarations.md:251 "`records`, every record a read resolved, as `{"id", "version", "content_hash"}`"
    found: list[JsonObject] = []
    for record in records:
        if not any(same(record, earlier) for earlier in found):
            found.append(record)
    return found
