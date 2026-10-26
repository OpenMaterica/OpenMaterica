# SPDX-License-Identifier: Apache-2.0
"""HP43 to HP46 (the S7 design's 6.5): the build's results, its own reasons and its verdict
(`declarations.md` sections 1, 2 and 4.2), over the draws of `build_strategies.py`, against an oracle written
here from the text.

- HP43, `judge` against section 4.2's table and the build's terms: for a result drawn directly, its reasons
  (with conditions and alternatives) and `assumption`, and acceptances drawn beside it, `accepted` holds
  exactly when every reason is covered, `accepted_by` is exactly the covering and the applied, `not_accepted`
  exactly the uncovered. In three parts drawn directly (`waivers`, `assumptions`, `never`), and one over whole
  builds (`indexes`), where "applied" is read from each result as the build's terms define it, and each
  model's unused acceptances are checked too.
- HP44, the results are the reads: each result's read equals the read of the request built here from the
  declaration by section 2 item 7, member for member; one result per model, listed record and field read, none
  for a record not listed; the build's reasons only ever add, and the status is the worst. Two parts,
  `requests` and `coverage`. On these draws, HP1's, HP2's and HP11's checks hold each result's read, where
  each applies (`read_checks`).
- HP45, the build's own reasons against the record as stored: `label_mismatch` exactly where the stored label
  of the value the result rests on differs or is absent, beside any other reason, and never where it rests on
  no stored value; `not_reviewed` exactly where `review` is required and the result's provenance holds no
  completed review; a waiver naming a label covers only where the stored label is that label and is trusted,
  and where this version cannot tell, the build raises. Three parts, `label`, `review` and `label_waiver`;
  the fourth, `label_trust`, waits for label trust, after 0.1.0.dev4 (maintainer, 2026-10-21).
- HP46, the refusal law and order: `refused` exactly when a refusal, or a result not accepted, exists;
  permuting models, listed records and acceptances (their indexes re-mapped) permutes the results, compared as
  a list, and changes no verdict. Its draws are refused by no declaration's check (`built`), so the law's arm
  of a refusal is held by the fuzz target's results relation, over every build-check case's report, refused
  ones among them (`tests/unit/test_fuzz_build_results.py`).

An implied condition's value is compared with a condition entry's bit for bit, as `read_side_contract.md`
section 1 compares two implied values ("the same numbers bit for bit"). Where the text leaves a choice, the
oracle takes the build's reading, each an open point until ruled: `records` holds each record step 1 of a read
found ("every record a read resolved", step 1 being "Resolve"); and where a waiver naming a label fits a
reason and every reason of the result fits an acceptance, whether the label is trusted could change the
verdict, which this version does not judge: the build raises `NotImplementedError` there, and nowhere else.
"""

import json
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from materica.core import acceptance as acceptance_module
from materica.core import build as build_module
from materica.core.hashing import content_hash
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult, read
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from materica.core.report import BuildReport, BuildResult
from materica.shapes import ReasonCode
from tests.property import build_strategies as strategies
from tests.property import result_strategies
from tests.property import test_result_properties as result_properties
from tests.property.build_strategies import Judged, World
from tests.property.strategies import SIZE, Size
from tests.property.support import feature, same

JsonObject = dict[str, JsonValue]
Key = tuple[str, str | None, int | None]


# Section 4.2's table, as this module reads it, row by row: the reasons, the kind that covers them, and the
# row's own condition (the code and the condition it names; the `assumption`).
@dataclass(frozen=True)
class Row:
    reasons: frozenset[str]
    kind: str
    names_code: bool = False
    names_condition: bool = False
    on_assumption: bool = False


ROWS = (
    # "`condition_unstated`, `condition_unchecked`, `condition_uncertain` | unknown | a `waiver` naming that
    # condition and code"
    Row(
        frozenset({"condition_unstated", "condition_unchecked", "condition_uncertain"}),
        "waiver",
        names_code=True,
        names_condition=True,
    ),
    # "`no_requirement`, `stated_without_origin`, `outside_check_points`, `fill_in_version_mismatch`,
    # `entries_withheld`, `not_reviewed` | unknown | a `waiver` naming that code"
    Row(
        frozenset(
            {
                "no_requirement",
                "stated_without_origin",
                "outside_check_points",
                "fill_in_version_mismatch",
                "entries_withheld",
                "not_reviewed",
            }
        ),
        "waiver",
        names_code=True,
    ),
    # "`no_pick` | unknown | a `pick` only"
    Row(frozenset({"no_pick"}), "pick"),
    # "`range_unstated`, `outside_coverage` | unknown | an `extrapolation` only"
    Row(frozenset({"range_unstated", "outside_coverage"}), "extrapolation"),
    # "`outside_range` | not_met | an `extrapolation`, only on a result whose `assumption` names it"
    Row(frozenset({"outside_range"}), "extrapolation", on_assumption=True),
    # "`want_mismatch`, for a value read from an interval, or a vector read from a parameter set with none |
    # not_met | a `nominal`, only on a result whose `assumption` names it"
    Row(frozenset({"want_mismatch"}), "nominal", on_assumption=True),
    # "`engine_mass_not_comparable` | unknown | a `waiver` naming that code"
    Row(frozenset({"engine_mass_not_comparable"}), "waiver", names_code=True),
)
# The rows of `overlay_scope_mismatch`, a specimen difference and a `trainable` field are not drawn: no
# declaration here holds an overlay, a `target` or `trainable` (`build_strategies.py`).

# `read_side_contract.md` section 2's members table: an `assumption` is "the declaration it rests on, as
# `{"acceptance"}` with its kind's own members as the request gives them, `basis` aside"; section 4.1's
# rows give each kind's own members.
OWN_MEMBERS = {"nominal": ("value", "params"), "extrapolation": ("method", "law")}
# Section 2 item 7: "the acceptances of the kinds a read takes (`read_side_contract.md` section 1), overlays
# aside": a read takes `pick`, `overlay`, `extrapolation`, `nominal`, `implied_condition` and `trainable`, and
# the `trainable` acceptance is the one section 7 gives, never a declaration's.
GIVEN_KINDS = ("pick", "extrapolation", "nominal", "implied_condition")
# Section 2 item 8: the build's own reasons.
OWN_CODES = frozenset({"no_requirement", "label_mismatch", "not_reviewed"})
# Section 2 item 8: "A result that rests on no stored value (its record or field not found, a refusal before
# step 7 finds the field ...)". The refusals of `read_side_contract.md` section 3's steps 1 to 5 (Resolve,
# Version, Validate, Hash, Type), and `absent`, which steps 1 and 7 give for a record or a field not found.
# Step 0's refusals, which share codes with later steps', are not drawn where this is read (HP45).
BEFORE_THE_FIELD = frozenset(
    {"absent", "pin_mismatch", "other_version", "malformed", "hash_mismatch", "unknown_type"}
)
# `provenance.md` section 2 item 6: a completed review holds `result` `reviewed`.
REVIEWED = "reviewed"
STATUS_ORDER = ("met", "unknown", "not_met")
# Each reason's status, as `read_side_contract.md` section 4's table gives it.
STATUSES: dict[str, str] = {code: row["status"] for code, row in result_properties.REASONS.items()}


def key(reason: Reason) -> Key:
    """A reason as section 2 item 2 identifies it: its code, condition and alternative."""
    return (reason.code, reason.condition, reason.alternative)


def keys(reasons: Iterable[Reason]) -> Counter[Key]:
    return Counter(map(key, reasons))


def worst(reasons: Iterable[Reason]) -> str:
    """Section 2 item 8: the status, "the worst of them all"; `met` where a result holds no reason."""
    return max((STATUSES[reason.code] for reason in reasons), key=STATUS_ORDER.index, default="met")


# The build's terms (section 2).


def located(members: Mapping[str, JsonValue], record: Mapping[str, JsonValue]) -> bool:
    """The build's terms: "An acceptance is **located at** a result's location when it names the record read,
    equal in `id`, `version` and `content_hash`; one located at a region or an interval is located at no
    record, and an accepted difference with no location is located at every location its model is checked
    over"."""
    if "region" in members or "interval" in members:
        return False
    named = members.get("record")
    if not isinstance(named, dict):
        return members.get("acceptance") == "accepted_difference"
    return all(named.get(member) == record[member] for member in ("id", "version", "content_hash"))


def names(assumption: JsonValue, members: Mapping[str, JsonValue]) -> bool:
    """Whether a result's `assumption` names the acceptance `members`: is the declaration it rests on, its
    kind and its kind's own members as given, `basis` aside, numbers bit for bit."""
    kind = members.get("acceptance")
    if not isinstance(kind, str) or kind not in OWN_MEMBERS:
        return False
    declared: JsonObject = {"acceptance": kind}
    declared.update({name: members[name] for name in OWN_MEMBERS[kind] if name in members})
    return assumption is not None and same(declared, assumption)


Trusted = Callable[[Mapping[str, JsonValue]], bool]


def covers(
    members: Mapping[str, JsonValue],
    reason: Reason,
    assumption: JsonValue,
    record: Mapping[str, JsonValue],
    field: str,
    trusted: Trusted | None = None,
) -> bool:
    """The build's terms: "An acceptance **covers** a reason ... of a result when it names the result's field
    ..., is located at the result's location, and is of a kind section 4.2's row for that reason names, under
    that row's own condition (the code and condition named; the `assumption`), and, for a waiver naming a
    label, as section 4.1 item 4 says": "It covers its reason only on a result whose stored label ... is that
    label and is trusted", which `trusted` judges; a waiver naming a label covers nothing where none is given.
    Section 4.2: "A waiver covers a reason whatever its `alternative`"."""
    if members.get("field") != field or not located(members, record):
        return False
    kind = members.get("acceptance")
    if kind == "waiver" and "label" in members and (trusted is None or not trusted(members)):
        return False
    return any(
        reason.code in row.reasons
        and kind == row.kind
        and (not row.names_code or members.get("code") == reason.code)
        and (not row.names_condition or members.get("condition") == reason.condition)
        and (not row.on_assumption or names(assumption, members))
        for row in ROWS
    )


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    accepted_by: frozenset[int]
    not_accepted: Counter[Key]


def verdict(
    reasons: Sequence[Reason],
    assumption: JsonValue,
    record: Mapping[str, JsonValue],
    field: str,
    acceptances: Sequence[tuple[int, Mapping[str, JsonValue]]],
    applied: Iterable[int],
    trusted: Trusted | None = None,
) -> Verdict:
    """Section 2 item 4: "`accepted` is true when each reason ... of the result is covered as the table in
    section 4.2 says, and `accepted_by` lists the 0-based indexes, in the model's `acceptances`, of every
    acceptance used, the ones the read itself applied ... included"; "`not_accepted` lists each reason ...
    that nothing covers". The build's terms: "An acceptance is **used** where it covers a reason ... of a
    result, or a read applied it.\""""
    used = set(applied)
    uncovered: list[Reason] = []
    for reason in reasons:
        covering = {
            index
            for index, members in acceptances
            if covers(members, reason, assumption, record, field, trusted)
        }
        used |= covering
        if not covering:
            uncovered.append(reason)
    return Verdict(not uncovered, frozenset(used), keys(uncovered))


def supplied(value: Mapping[str, JsonValue]) -> JsonObject:
    """The condition an implied condition supplies for one condition: its value "a record condition's shapes
    without `basis` (one there is ignored)", checked "like a stated one, with basis `implied`" (section
    4.1)."""
    return {**{name: held for name, held in value.items() if name != "basis"}, "basis": "implied"}


def applied_by(
    result: Mapping[str, JsonValue] | None, given: Sequence[tuple[int, Mapping[str, JsonValue]]]
) -> set[int]:
    """The build's terms: "A read **applied** an acceptance given to it where its result shows it: an implied
    condition that filled a condition (a `conditions` entry whose `record` is the value the implied condition
    supplies, with basis `implied`); a nominal or an extrapolation that the result's `assumption` names"."""
    if result is None:
        return set()
    entries = result.get("conditions")
    filled = {
        str(entry["name"]): entry.get("record")
        for entry in (entries if isinstance(entries, list) else [])
        if isinstance(entry, dict)
    }
    found: set[int] = set()
    for index, members in given:
        kind = members.get("acceptance")
        if kind == "implied_condition":
            implies = members.get("implies")
            assert isinstance(implies, dict)
            if any(
                isinstance(value, dict) and same(supplied(value), filled.get(name))
                for name, value in implies.items()
            ):
                found.add(index)
        elif kind in OWN_MEMBERS and names(result.get("assumption"), members):
            found.add(index)
    return found


# Section 2 item 7: the build's own read request.


def given_to(
    model: Mapping[str, JsonValue], record: Mapping[str, JsonValue], field: str
) -> list[tuple[int, JsonObject]]:
    """Section 2 item 7: "The build gives each read the acceptances of the kinds a read takes ..., overlays
    aside ..., that name the read's field and are located at its location": each with its index in the
    model's `acceptances`."""
    return [
        (index, held)
        for index, held in enumerate(acceptances_of(model))
        if held.get("acceptance") in GIVEN_KINDS and held.get("field") == field and located(held, record)
    ]


def request_for(
    declared: Mapping[str, JsonValue],
    model: Mapping[str, JsonValue],
    record: Mapping[str, JsonValue],
    requirement: Mapping[str, JsonValue],
) -> JsonObject:
    """Section 2 item 7: "The build's own read request holds the requirement's `want` and `conditions`, and
    the declared operating conditions", and the acceptances given, in the model's order."""
    field = requirement["field"]
    assert isinstance(field, str)
    return cast(
        JsonObject,
        json.loads(
            json.dumps(
                {
                    "target": {"record": record, "field": field},
                    "operating_conditions": declared["operating_conditions"],
                    "requirement": {
                        "want": requirement["want"],
                        "conditions": requirement.get("conditions", {}),
                    },
                    "acceptances": [held for _, held in given_to(model, record, field)],
                }
            )
        ),
    )


def models_of(declared: Mapping[str, JsonValue]) -> list[JsonObject]:
    return cast(list[JsonObject], declared["models"])


def name_of(model: Mapping[str, JsonValue]) -> str:
    return str(cast(JsonObject, model["model"])["name"])


def listed_of(model: Mapping[str, JsonValue]) -> list[JsonObject]:
    return cast(list[JsonObject], cast(JsonObject, model["checked_over"])["records"])


def reads_of(model: Mapping[str, JsonValue]) -> list[str]:
    return cast(list[str], model["reads"])


def acceptances_of(model: Mapping[str, JsonValue]) -> list[JsonObject]:
    return cast(list[JsonObject], model.get("acceptances", []))


def requirement_of(model: Mapping[str, JsonValue], field: str) -> JsonObject | None:
    return next(
        (held for held in cast(list[JsonObject], model.get("requirements", [])) if held["field"] == field),
        None,
    )


def ref_of(record: Mapping[str, JsonValue] | MaterialRef) -> tuple[str, str, str]:
    if isinstance(record, MaterialRef):
        return (record.id, record.version, record.content_hash)
    return (str(record["id"]), str(record["version"]), str(record["content_hash"]))


def as_json(record: MaterialRef) -> JsonObject:
    return cast(JsonObject, record.to_json())


# Running the build.


def store_of(world: World) -> RecordStore:
    store = RecordStore()
    for number, data in enumerate(world.sources):
        store.add(f"source_{number}", data)
    return store


def built(world: World, declared: JsonObject | None = None) -> BuildReport:
    """The build's report on the world's declaration, or `declared`. The build never raises on these draws,
    whose declarations the text takes and hold nothing a later piece reads; nor does it refuse them."""
    try:
        report = build_module.check_build(
            world.declaration if declared is None else declared, store_of(world), claims=world.claims
        )
    except Exception as error:
        raise AssertionError(f"the build raised {error!r}") from error
    assert report.refusals == (), f"refused a declaration the text takes: {report.refusals}"
    return report


def stored_records(world: World) -> dict[tuple[str, str, str], JsonObject]:
    """Each record of the store by the pin it states; a pin two sources state is not drawn."""
    found: dict[tuple[str, str, str], JsonObject] = {}
    for data in world.sources:
        record = cast(JsonObject, json.loads(data))
        found[ref_of(record)] = record
    return found


@dataclass(frozen=True)
class Expected:
    """A result the declaration asks for: its model, its record (the reference as listed), its field, and
    the read of the request built here, or None for a field with no requirement."""

    model: JsonObject
    record: JsonObject
    field: str
    requirement: JsonObject | None
    request: JsonObject | None
    read: ReadResult | None


def expected_results(world: World, declared: JsonObject | None = None) -> list[Expected]:
    """Section 2: "The build reads every required field in every ... record a model is checked over ..., and
    returns one result each"; section 1 item 1: "A field in `reads` with no requirement gives `unknown` with
    the reason `no_requirement`; the build reads nothing for it"."""
    declaration = world.declaration if declared is None else declared
    found: list[Expected] = []
    for model in models_of(declaration):
        for record in listed_of(model):
            for field in reads_of(model):
                required = requirement_of(model, field)
                if required is None:
                    found.append(Expected(model, record, field, None, None, None))
                    continue
                request = request_for(declaration, model, record, required)
                found.append(
                    Expected(
                        model,
                        record,
                        field,
                        required,
                        request,
                        read(request, store_of(world), claims=world.claims),
                    )
                )
    return found


def result_key(
    model: str, record: Mapping[str, JsonValue], field: str
) -> tuple[str, tuple[str, str, str], str]:
    return (model, ref_of(record), field)


def matched(report: BuildReport, expected: Sequence[Expected]) -> list[tuple[Expected, BuildResult]]:
    """Each result the declaration asks for beside the report's: exactly one each, and no other."""
    wanted = Counter(result_key(name_of(one.model), one.record, one.field) for one in expected)
    given = Counter(
        result_key(result.model, as_json(result.record), result.field) for result in report.results
    )
    assert given == wanted, (
        f"results {sorted(given.elements())}, the declaration's {sorted(wanted.elements())}"
    )
    by_key = {
        result_key(result.model, as_json(result.record), result.field): result for result in report.results
    }
    return [(one, by_key[result_key(name_of(one.model), one.record, one.field)]) for one in expected]


def own_reasons(result: BuildResult) -> Counter[Key]:
    """The reasons a result holds beside its read's, which section 2 item 8 says only join them."""
    added = keys(result.reasons)
    read_keys = keys(() if result.read is None else result.read.reasons)
    missing = read_keys - added
    assert not missing, f"the read's reasons {sorted(missing.elements())} left out of the result"
    return added - read_keys


# HP43.


def check_judged(drawn: Judged) -> None:
    """`judge`, against the oracle, on a result and acceptances drawn directly."""
    found = acceptance_module.judge(
        drawn.reasons, drawn.read, drawn.record, drawn.field, drawn.acceptances, drawn.applied
    )
    assumption = None if drawn.read is None else cast(JsonValue, drawn.read.assumption)
    wanted = verdict(
        drawn.reasons,
        assumption,
        as_json(drawn.record),
        drawn.field,
        [(acceptance.index, acceptance.members) for acceptance in drawn.acceptances],
        drawn.applied,
    )
    assert found.accepted == wanted.accepted, f"accepted {found.accepted}, the text's {wanted.accepted}"
    assert len(set(found.accepted_by)) == len(found.accepted_by), f"accepted_by twice: {found.accepted_by}"
    assert set(found.accepted_by) == wanted.accepted_by, (
        f"accepted_by {sorted(found.accepted_by)}, the text's {sorted(wanted.accepted_by)}"
    )
    assert keys(found.not_accepted) == wanted.not_accepted, (
        f"not_accepted {sorted(keys(found.not_accepted).elements())}, the text's"
        f" {sorted(wanted.not_accepted.elements())}"
    )


def check_verdicts(world: World, report: BuildReport) -> None:
    """Each result's verdict by its own model's acceptances, "applied" read from the result as the build's
    terms define it; and each model's unused acceptances (item 9)."""
    used: dict[str, set[int]] = {name_of(model): set() for model in models_of(world.declaration)}
    for one, result in matched(report, expected_results(world)):
        own = list(enumerate(acceptances_of(one.model)))
        read_json = None if result.read is None else cast(JsonObject, result.read.to_json())
        applied = applied_by(read_json, given_to(one.model, one.record, one.field))
        assumption = None if read_json is None else read_json.get("assumption")
        wanted = verdict(result.reasons, assumption, one.record, one.field, own, applied)
        where = f"{result.model} {result.record.id} {result.field}"
        assert result.accepted == wanted.accepted, (
            f"{where}: accepted {result.accepted}, the text's {wanted.accepted}"
        )
        assert len(set(result.accepted_by)) == len(result.accepted_by), f"{where}: accepted_by twice"
        assert set(result.accepted_by) == wanted.accepted_by, (
            f"{where}: accepted_by {sorted(result.accepted_by)}, the text's {sorted(wanted.accepted_by)}"
        )
        assert keys(result.not_accepted) == wanted.not_accepted, (
            f"{where}: not_accepted {sorted(keys(result.not_accepted).elements())}, the text's"
            f" {sorted(wanted.not_accepted.elements())}"
        )
        used[result.model] |= wanted.accepted_by
    # "The build lists in `unused`, per model, each acceptance not used (the build's terms)".
    unused = Counter((found.model, found.acceptance) for found in report.unused)
    wanted_unused = Counter(
        (name_of(model), index)
        for model in models_of(world.declaration)
        for index in range(len(acceptances_of(model)))
        if index not in used[name_of(model)]
    )
    assert unused == wanted_unused, f"unused {sorted(unused)}, the text's {sorted(wanted_unused)}"


def check_indexes(world: World) -> None:
    check_verdicts(world, built(world))


# HP44.


def check_reads(world: World) -> None:
    """Each result's read is the read of the request built from the declaration, member for member; the
    results are one per model, listed record and field read; the build's reasons only add to the read's, the
    status is the worst of them all, and every other member is the read's. HP1's, HP2's and HP11's checks hold
    each read."""
    report = built(world)
    stored = stored_records(world)
    for one, result in matched(report, expected_results(world)):
        where = f"{result.model} {result.record.id} {result.field}"
        if one.read is None:
            assert result.read is None, f"{where}: a field with no requirement read"
        else:
            assert result.read is not None, f"{where}: a field with a requirement not read"
            wanted = cast(JsonObject, one.read.to_json())
            found = cast(JsonObject, result.read.to_json())
            assert same(wanted, found), f"{where}: the read {found}, the request's {wanted}"
            written = cast(JsonObject, result.to_json())
            for name, value in wanted.items():
                if name not in ("status", "reasons"):
                    assert name in written, f"{where}: `{name}` left out"
                    assert same(value, written[name]), f"{where}: `{name}` not the read's"
            assert one.request is not None
            read_checks(world, one.request, stored.get(ref_of(one.record)), one.field, one.read)
        added = own_reasons(result)
        assert set(code for code, _, _ in added) <= OWN_CODES, f"{where}: added {sorted(added)}"
        assert result.status == worst(result.reasons), (
            f"{where}: status {result.status}, the worst of {[key(reason) for reason in result.reasons]}"
        )
    # Section 2: "`records`, every record a read resolved", the record step 1 of a read found; a read refused
    # at step 0 reached no step 1.
    found_records = [ref_of(record) for record in report.records]
    assert len(set(found_records)) == len(found_records), f"a record listed twice: {found_records}"
    wanted_records = {
        ref_of(one.record)
        for one in expected_results(world)
        if one.request is not None and not refused_at_step_0(one.request) and ref_of(one.record) in stored
    }
    assert set(found_records) == wanted_records, (
        f"records {found_records}, the reads' {sorted(wanted_records)}"
    )


# `read_side_contract.md` section 1: "So do two acceptances of one kind, `nominal`, `extrapolation`, `pick` or
# `trainable`, that name one field, whatever location or other members each holds" (`request_incomplete`).
ONE_A_FIELD = ("nominal", "extrapolation", "pick", "trainable")


def refused_at_step_0(request: Mapping[str, JsonValue]) -> bool:
    """Whether step 0 refuses `request`, on these draws, whose acceptances each have their shapes: two
    acceptances of one of `ONE_A_FIELD`'s kinds that name one field."""
    named = Counter(
        (held.get("acceptance"), held.get("field"))
        for held in cast(list[JsonObject], request.get("acceptances", []))
        if held.get("acceptance") in ONE_A_FIELD
    )
    return any(count > 1 for count in named.values())


def read_checks(
    world: World, request: JsonObject, record: JsonObject | None, field: str, found: ReadResult
) -> None:
    """HP1's, HP2's and HP11's checks of a read (`test_result_properties.py`), on the read of `request`:
    HP1's always; HP11's where no record of the store states a stale hash, which a read with the hash suite
    refuses and one without reads; HP2's where the record is stored, holds the field and the request gives no
    extrapolation, whose `assumption` HP2's check does not draw. HP2's check reads a nominal as applying to a
    read that passes steps 0 to 10, of its kind `met`, which a read refused by step 10 is not."""
    sources = world.sources
    refused_by_step_10 = refused_at_step_0(request) or any(
        STATUSES[reason.code] == "not_met" and max(result_properties.REASONS[reason.code]["steps"]) <= 10
        for reason in found.reasons
    )
    drawn = result_strategies.Drawn(
        "refused_by_step_10" if refused_by_step_10 else "met",
        sources,
        request,
        world.claims,
        record is not None and record.get("schema_version") == "0.1.0" and not refused_at_step_0(request),
        record if record is not None else {},
        field,
    )
    result_properties.check_totality(drawn)
    stale = any(
        content_hash(cast(JsonObject, json.loads(data))) != cast(JsonObject, json.loads(data))["content_hash"]
        for data in sources
    )
    if not stale:
        result_properties.check_claims(drawn)
    given = cast(list[JsonObject], request.get("acceptances", []))
    if (
        record is not None
        and "form" in (strategies.field_of(record, field) or {})
        and record.get("schema_version") == "0.1.0"
        and record.get("record_type") == "material"
        and not any(held.get("acceptance") == "extrapolation" for held in given)
    ):
        result_properties.check_status_law(drawn)


# HP45.


def tolerated(
    alternative: Mapping[str, JsonValue],
    requirement: Mapping[str, JsonValue],
    operating: Mapping[str, JsonValue],
) -> bool:
    """Whether an alternative stays at step 7 ("alternatives whose conditions are not met are set aside",
    PR-044), on these draws, which state each alternative's numeric conditions as values far from their
    tolerances' ends, give the operating conditions as values, and hold in an alternative no label a read
    refuses ("any other `not_met` in an alternative" refuses the field): each condition the requirement
    holds a tolerance for, stated as a value beside an operating value, lies within it."""
    stated = cast(JsonObject, alternative.get("conditions", {}))
    for name, condition in cast(JsonObject, requirement.get("conditions", {})).items():
        allowed = cast(JsonObject, condition).get("tolerance")
        held, operated = stated.get(name), operating.get(name)
        if not (isinstance(allowed, dict) and isinstance(held, dict) and isinstance(operated, dict)):
            continue
        if "value" in held and "value" in operated:
            if abs(cast(float, held["value"]) - cast(float, operated["value"])) > cast(
                float, allowed["value"]
            ):
                return False
    return True


def resting_on(world: World, one: Expected, read_reasons: Sequence[Reason]) -> Mapping[str, JsonValue] | None:
    """Section 2 item 8: the stored value the result rests on, "the field, or the alternative read", as the
    store holds it; None where "the result rests on no stored value (its record or field not found, a refusal
    before step 7 finds the field, or no single alternative ...)"."""
    record = stored_records(world).get(ref_of(one.record))
    if record is None or any(reason.code in BEFORE_THE_FIELD for reason in read_reasons):
        return None
    value = strategies.field_of(record, one.field)
    if value is None:
        return None
    alternatives = value.get("alternatives")
    if not isinstance(alternatives, list):
        return value
    assert one.requirement is not None
    operating = cast(JsonObject, world.declaration["operating_conditions"])
    left = [
        cast(JsonObject, held)
        for held in alternatives
        if tolerated(cast(JsonObject, held), one.requirement, operating)
    ]
    return left[0] if len(left) == 1 else None


def wanted_own(world: World, one: Expected, found: ReadResult | None) -> Counter[str]:
    """Section 1 items 1, 5 and 11, and section 2 item 8: the build's own reasons for a result whose read is
    `found`: `no_requirement` for a field with no requirement; `label_mismatch` "when the label stored on the
    value the result rests on differs or is absent", none where it rests on none; and `not_reviewed` "on a
    result whose `provenance.review` ... is not a completed review: one holding `result` `reviewed`", none on
    "a result that holds no `provenance`"."""
    if one.requirement is None:
        return Counter({"no_requirement": 1})
    assert found is not None
    wanted: Counter[str] = Counter()
    label = one.requirement.get("label")
    if label is not None:
        value = resting_on(world, one, found.reasons)
        if value is not None and value.get("label") != label:
            wanted["label_mismatch"] += 1
    if one.requirement.get("review") == REVIEWED and found.provenance is not None:
        review = cast(JsonObject, found.provenance.to_json()).get("review")
        if not (isinstance(review, dict) and review.get("result") == REVIEWED):
            wanted["not_reviewed"] += 1
    return wanted


def check_own_reasons(world: World) -> None:
    """Exactly the build's own reasons the text gives, each without a condition or an alternative, beside the
    read's."""
    report = built(world)
    for one, result in matched(report, expected_results(world)):
        where = f"{result.model} {result.record.id} {result.field}"
        added = own_reasons(result)
        assert all(condition is None and alternative is None for _, condition, alternative in added), (
            f"{where}: own reasons {sorted(added)}"
        )
        found = Counter(code for code, _, _ in added.elements())
        wanted = wanted_own(world, one, result.read)
        assert found == wanted, (
            f"{where}: the build's own reasons {sorted(found.elements())}, the text's"
            f" {sorted(wanted.elements())}"
        )
        assert result.status == worst(result.reasons), f"{where}: status {result.status}"


def trusted_by_text(world: World, one: Expected, result: BuildResult) -> Trusted:
    """Section 4.1 item 4: a waiver naming a label "covers its reason only on a result whose stored label
    (section 2 item 8) is that label and is trusted (section 2)"; the build's terms: "A label is **trusted**
    on a result where the record stores it on the value the result rests on ... with a `label_basis` whose
    `basis` is `stated` ..., or where the result's review is a completed review"."""
    assert result.read is not None
    value = resting_on(world, one, result.read.reasons)
    provenance = (
        None if result.read.provenance is None else cast(JsonObject, result.read.provenance.to_json())
    )
    review = None if provenance is None else provenance.get("review")
    reviewed = isinstance(review, dict) and review.get("result") == REVIEWED

    def trusted(members: Mapping[str, JsonValue]) -> bool:
        if value is None or value.get("label") != members.get("label"):
            return False
        basis = value.get("label_basis")
        return reviewed or (isinstance(basis, dict) and basis.get("basis") == "stated")

    return trusted


def fits_but_for_trust(world: World) -> bool:
    """Whether label trust could change a result's verdict: a waiver naming a label fits a reason (covers it,
    were its label trusted), and every reason fits some acceptance. This version raises there and nowhere
    else, the build's reading of where label trust decides (an open point until ruled)."""
    for one in expected_results(world):
        if one.read is None:
            continue
        added = wanted_own(world, one, one.read).elements()
        reasons = [*one.read.reasons, *(Reason(cast(ReasonCode, code)) for code in added)]
        assumption = cast(JsonObject, one.read.to_json()).get("assumption")
        own = acceptances_of(one.model)
        fits = [
            [
                held
                for held in own
                if covers(held, reason, assumption, one.record, one.field, trusted=lambda _: True)
            ]
            for reason in reasons
        ]
        if all(fits) and any("label" in held for found in fits for held in found):
            return True
    return False


def check_label_waiver(world: World) -> None:
    """Where label trust could change the verdict, the build raises, naming label trust; elsewhere each
    result's verdict, a waiver naming a label covering only where its label is stored and trusted."""
    if fits_but_for_trust(world):
        raised = ""
        try:
            report = build_module.check_build(world.declaration, store_of(world), claims=world.claims)
        except NotImplementedError as error:
            raised = str(error)
        except Exception as error:
            raise AssertionError(f"the build raised {error!r}") from error
        else:
            shown = [(result.accepted, result.accepted_by) for result in report.results]
            raise AssertionError(f"decided where label trust could change the verdict: {shown}")
        assert "label" in raised, f"raised for another reason: {raised}"
        return
    report = built(world)
    for one, result in matched(report, expected_results(world)):
        assert result.read is not None
        own = list(enumerate(acceptances_of(one.model)))
        read_json = cast(JsonObject, result.read.to_json())
        applied = applied_by(read_json, given_to(one.model, one.record, one.field))
        wanted = verdict(
            result.reasons,
            read_json.get("assumption"),
            one.record,
            one.field,
            own,
            applied,
            trusted_by_text(world, one, result),
        )
        assert result.accepted == wanted.accepted, f"accepted {result.accepted}, the text's {wanted.accepted}"
        assert set(result.accepted_by) == wanted.accepted_by, (
            f"accepted_by {sorted(result.accepted_by)}, the text's {sorted(wanted.accepted_by)}"
        )
        assert keys(result.not_accepted) == wanted.not_accepted, "not_accepted"


# HP46.


def check_refused(report: BuildReport) -> None:
    """Section 2 item 5 and the report's paragraph: the build refuses while the report holds a refusal, or a
    result that is not accepted. On HP46's draws the report holds no refusal (`built` asserts it), so the arm
    of a refusal is the fuzz relation's (`tests/fuzz/build_results_oracle.py`), which holds it on every
    build-check case's report, refused ones among them."""
    wanted = bool(report.refusals) or any(not result.accepted for result in report.results)
    assert report.refused == wanted, f"refused {report.refused}, the text's {wanted}"


@dataclass(frozen=True)
class Permutation:
    models: tuple[int, ...]
    records: tuple[tuple[int, ...], ...]  # per model, in the original order
    acceptances: tuple[tuple[int, ...], ...]  # per model: the new position of each original index


def permute(declared: JsonObject, permutation: Permutation) -> JsonObject:
    """The declaration with its models, each model's listed records and each model's acceptances reordered."""
    models = models_of(declared)
    reordered: list[JsonObject] = []
    for index in permutation.models:
        model = json.loads(json.dumps(models[index]))
        listed = listed_of(model)
        model["checked_over"] = {"records": [listed[at] for at in permutation.records[index]]}
        held = acceptances_of(model)
        placed: list[JsonValue] = [None] * len(held)
        for old, new in enumerate(permutation.acceptances[index]):
            placed[new] = held[old]
        model["acceptances"] = placed
        reordered.append(model)
    return {**declared, "models": cast(JsonValue, reordered)}


@st.composite
def permutations(draw: st.DrawFn, declared: JsonObject) -> Permutation:
    models = models_of(declared)
    return Permutation(
        tuple(draw(st.permutations(range(len(models))))),
        tuple(tuple(draw(st.permutations(range(len(listed_of(model)))))) for model in models),
        tuple(tuple(draw(st.permutations(range(len(acceptances_of(model)))))) for model in models),
    )


Moved = Mapping[str, Sequence[int]]


def verdicts(report: BuildReport, moved: Moved | None = None) -> list[tuple[object, ...]]:
    """Each result's verdict, in the report's order, its acceptances' indexes mapped by `moved` (per model:
    the new index of each old one)."""

    def at(model: str, index: int) -> int:
        return index if moved is None else moved[model][index]

    return [
        (
            result.model,
            ref_of(result.record),
            result.field,
            result.status,
            tuple(sorted(keys(result.reasons).items())),
            result.accepted,
            tuple(sorted(at(result.model, index) for index in result.accepted_by)),
            tuple(sorted(keys(result.not_accepted).items())),
        )
        for result in report.results
    ]


def unused_acceptances(report: BuildReport, moved: Moved | None = None) -> Counter[tuple[str, int]]:
    """Each model's unused acceptances, mapped by `moved`: a multiset, the text giving no order within a
    model."""
    return Counter(
        (unused.model, unused.acceptance if moved is None else moved[unused.model][unused.acceptance])
        for unused in report.unused
    )


def permuted_order(
    results: Sequence[tuple[object, ...]], declared: JsonObject, permutation: Permutation
) -> list[tuple[object, ...]]:
    """The design's "permutes the results": `results` of `declared`'s build reordered as the permutation
    reorders the models and each model's listed records, the order within one record of a model (its fields)
    kept."""
    models = [name_of(model) for model in models_of(declared)]

    def placed(one: tuple[object, ...]) -> tuple[int, int]:
        model = models.index(cast(str, one[0]))
        listed = [ref_of(record) for record in listed_of(models_of(declared)[model])]
        record = listed.index(cast(tuple[str, str, str], one[1]))
        return (permutation.models.index(model), permutation.records[model].index(record))

    return sorted(results, key=placed)


def check_permuted(world: World, permutation: Permutation) -> None:
    report = built(world)
    check_refused(report)
    permuted = built(world, permute(world.declaration, permutation))
    check_refused(permuted)
    moved = {
        name_of(model): permutation.acceptances[index]
        for index, model in enumerate(models_of(world.declaration))
    }
    wanted = permuted_order(verdicts(report, moved), world.declaration, permutation)
    assert verdicts(permuted) == wanted, (
        f"permuted, the verdicts {verdicts(permuted)}; before, permuted, {wanted}"
    )
    assert unused_acceptances(permuted) == unused_acceptances(report, moved), (
        f"permuted, the unused acceptances {sorted(unused_acceptances(permuted))}; before,"
        f" {sorted(unused_acceptances(report, moved))}"
    )
    assert permuted.refused == report.refused, "refused changed by a permutation"


@dataclass(frozen=True)
class Permuted:
    world: World
    permutation: Permutation

    @property
    def way(self) -> str:
        return self.world.way


@st.composite
def permuted_worlds(draw: st.DrawFn, size: Size) -> Permuted:
    world = draw(strategies.permuted_builds(size))
    return Permuted(world, draw(permutations(world.declaration)))


def check_permutation(drawn: Permuted) -> None:
    check_permuted(drawn.world, drawn.permutation)


# The test functions. Each drawing part is a test parametrized by its strata (`strategies.STRATA`), each
# drawing its way first among the stratum's, alike; HP43's `indexes` and HP46 draw no way.
STRATA = {
    part: [
        pytest.param(stratum, id="-".join(stratum), marks=pytest.mark.drawn(*stratum)) for stratum in strata
    ]
    for part, strata in strategies.STRATA.items()
}


@pytest.mark.parametrize("ways", STRATA["waivers"])
@given(data=st.data())
def test_a_waiver_covers_a_reason_exactly_where_it_names_its_code_condition_record_and_field(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.judged("waivers", SIZE, ways))
    feature(drawn.way)
    check_judged(drawn)


@pytest.mark.parametrize("ways", STRATA["assumptions"])
@given(data=st.data())
def test_a_nominal_or_extrapolation_covers_its_reason_exactly_where_the_assumption_names_it(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.judged("assumptions", SIZE, ways))
    feature(drawn.way)
    check_judged(drawn)


@pytest.mark.parametrize("ways", STRATA["never"])
@given(data=st.data())
def test_a_reason_no_row_lists_for_an_acceptance_is_never_covered_by_it(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.judged("never", SIZE, ways))
    feature(drawn.way)
    check_judged(drawn)


@given(strategies.indexes(SIZE))
def test_each_results_verdict_and_the_unused_acceptances_are_the_texts_by_index(world: World) -> None:
    check_indexes(world)


@pytest.mark.parametrize("ways", STRATA["requests"])
@given(data=st.data())
def test_each_results_read_is_the_read_of_the_request_the_declaration_gives(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    world = data.draw(strategies.requests(SIZE, ways))
    feature(world.way)
    check_reads(world)


@pytest.mark.parametrize("ways", STRATA["coverage"])
@given(data=st.data())
def test_the_results_are_one_per_model_listed_record_and_field_read(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    world = data.draw(strategies.coverage(SIZE, ways))
    feature(world.way)
    check_reads(world)


@pytest.mark.parametrize("ways", STRATA["label"])
@given(data=st.data())
def test_label_mismatch_is_given_exactly_where_the_stored_label_differs_or_is_absent(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    world = data.draw(strategies.labels(SIZE, ways))
    feature(world.way)
    check_own_reasons(world)


@pytest.mark.parametrize("ways", STRATA["review"])
@given(data=st.data())
def test_not_reviewed_is_given_exactly_where_review_is_required_and_not_completed(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    world = data.draw(strategies.reviews(SIZE, ways))
    feature(world.way)
    check_own_reasons(world)


@pytest.mark.parametrize("ways", STRATA["label_waiver"])
@given(data=st.data())
def test_a_waiver_naming_a_label_covers_only_where_the_label_is_stored_and_trusted(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    world = data.draw(strategies.label_waivers(SIZE, ways))
    feature(world.way)
    check_label_waiver(world)


@given(permuted_worlds(SIZE))
def test_the_build_refuses_exactly_where_a_result_is_not_accepted_whatever_the_order(drawn: Permuted) -> None:
    check_permutation(drawn)
