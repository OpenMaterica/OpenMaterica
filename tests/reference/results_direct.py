# SPDX-License-Identifier: Apache-2.0
"""Direct checks of the build's results model (`build_results_model.py`): declarations written here, most
of them a build-check file's declaration with one thing changed, each read over the suite's fixtures and
given the answer the specification gives it, for what no build-check case file pins. They are the model's own
tests, not evidence on the build: a case file is the shared evidence (`test_build_results_model.py`).

The seeded faults of the results model (`results_mutants.py`) run against these after the case files, so
that a fault only a direct check tells apart is a kill, and a rule neither pins is a listed survivor."""

import copy
import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Final
from unittest import mock

from tests.reference import build_model, build_results_model, read_model
from tests.reference.read_model import NoVerdict
from tests.reference.strict_json import JsonObject, JsonValue, parse

INPUTS: Final = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "materica"
    / "data"
    / "conformance"
    / "build_checks"
    / "inputs"
)
BUILD: Final = frozenset({"plain_read", "build_checks"})
VISCOSITY: Final = "fluid.dynamic_viscosity"
DENSITY: Final = "bulk.density"
NEWTONIAN: Final = "materica.fluid.newtonian.v1"
WATER: Final = "water_fixture.json"
PLASMA: Final = "plasma_fixture.json"
GRADE: Final = "grade_density_bounds_specification_limits.json"
IN_VIVO_UNSTATED: Final = "water_in_vivo_temperature_unstated.json"
TWO_ALTERNATIVES: Final = "water_two_constant_alternatives.json"
LABEL_MISSING: Final = "water_label_missing.json"
DENSITY_TABLE: Final = "density_table.json"
LINEAR: Final = "water_linear_label_on_viscosity.json"


@cache
def input_bytes(name: str) -> bytes:
    return (INPUTS / name).read_bytes()


def declared(name: str) -> JsonObject:
    """A build-check file's declaration, as a new object to change."""
    value = parse(input_bytes(name))
    assert isinstance(value, dict)
    return copy.deepcopy(value)


def reference(name: str) -> JsonObject:
    """The material reference of a fixture, as a declaration pins it."""
    record = parse(input_bytes(name))
    assert isinstance(record, dict)
    return {member: record[member] for member in ("id", "version", "content_hash")}


def model(declaration: JsonObject, index: int = 0) -> JsonObject:
    models = declaration["models"]
    assert isinstance(models, list)
    entry = models[index]
    assert isinstance(entry, dict)
    return entry


def requirement(declaration: JsonObject) -> JsonObject:
    requirements = model(declaration)["requirements"]
    assert isinstance(requirements, list)
    entry = requirements[0]
    assert isinstance(entry, dict)
    return entry


def acceptances(declaration: JsonObject) -> list[JsonValue]:
    held = model(declaration)["acceptances"]
    assert isinstance(held, list)
    return held


def changed(name: str, change: Callable[[JsonObject], object]) -> JsonObject:
    declaration = declared(name)
    change(declaration)
    return declaration


@dataclass(frozen=True)
class Expected:
    """One result's members the check compares, by its model, the record read (its file) and its field."""

    model: str
    record: str
    field: str
    members: Mapping[str, JsonValue]


_READ: Final = read_model.read


def no_verdict_on_a_read_over_records(
    request: JsonObject, sources: Sequence[bytes], claims: frozenset[str]
) -> JsonObject | NoVerdict:
    """A stand-in read model that gives no verdict on a read over records: no build-check fixture reaches the
    read model's own no verdicts (it gives one for a fit record or a region), so the results model's path
    for a read it cannot decide is held by this stand-in."""
    return (
        NoVerdict("the stand-in read model's read over records")
        if sources
        else _READ(request, sources, claims)
    )


def no_verdict_on_a_read_over_none(
    request: JsonObject, sources: Sequence[bytes], claims: frozenset[str]
) -> JsonObject | NoVerdict:
    """A stand-in read model that gives no verdict on the read the results model makes of a request over no
    records, to tell whether step 0 passes."""
    return (
        _READ(request, sources, claims) if sources else NoVerdict("the stand-in read model's read over none")
    )


@dataclass(frozen=True)
class Direct:
    what: str
    declaration: JsonObject
    records: tuple[str, ...]
    results: tuple[Expected, ...] = ()
    unused: frozenset[tuple[str, int]] = frozenset()
    undecided: str | None = None  # the kind of `UNDECIDED` the model gives no verdict for
    refused: bool | None = None  # the verdict, where the check states it
    resolved: tuple[str, ...] | None = None  # the report's `records`, by file, where the check states them
    claims: frozenset[str] = field(default=BUILD)
    # A record of `records`, by file, changed in memory before it is read: the check keeps its reference.
    edited: Mapping[str, Callable[[JsonObject], object]] = field(
        default_factory=dict[str, Callable[[JsonObject], object]]
    )
    # Sources read beside the records, by file (the same pin supplied twice, with other bytes).
    beside: tuple[bytes, ...] = ()
    read: Callable[..., JsonObject | NoVerdict] | None = None  # a stand-in for the read model's read


def source_of(check: Direct, name: str) -> bytes:
    change = check.edited.get(name)
    if change is None:
        return input_bytes(name)
    record = parse(input_bytes(name))
    assert isinstance(record, dict)
    change(record)
    return json.dumps(record).encode()


def answer(check: Direct) -> build_results_model.Report | build_model.Refused | NoVerdict:
    sources = [*(source_of(check, name) for name in check.records), *check.beside]
    with ExitStack() as stack:
        if check.read is not None:
            stack.enter_context(mock.patch.object(read_model, "read", check.read))
        return build_results_model.check_build(json.dumps(check.declaration).encode(), sources, check.claims)


def reasons_of(value: JsonValue) -> Counter[str]:
    """Reasons as a multiset of their code, condition and alternative (`docs/specification/README.md`)."""
    held = value if isinstance(value, list) else []
    return Counter(
        json.dumps([entry.get("code"), entry.get("condition"), entry.get("alternative")])
        for entry in held
        if isinstance(entry, dict)
    )


def member_differs(name: str, wanted: JsonValue, found: JsonValue) -> bool:
    if name in ("reasons", "not_accepted"):
        return reasons_of(wanted) != reasons_of(found)
    if name == "accepted_by":
        return indexes(found) != indexes(wanted)
    return not build_results_model.same(wanted, found)


def indexes(value: JsonValue) -> frozenset[float] | None:
    """A list of indexes as a set, `0` and `0.0` alike; None for no list."""
    if not isinstance(value, list):
        return None
    return frozenset(float(index) for index in value if isinstance(index, int | float) and index is not True)


def judged(check: Direct) -> str | None:
    """What is wrong with the model's answer to `check`, or None."""
    given = answer(check)
    if check.undecided is not None:
        why = build_results_model.UNDECIDED[check.undecided]
        if isinstance(given, NoVerdict) and given.why.startswith(why):
            return None
        return f"{check.what}: {given!r}, not no verdict for {why!r}"
    if not isinstance(given, build_results_model.Report):
        return f"{check.what}: {given!r}, not a report"
    keyed = {
        (str(result["model"]), json.dumps(result["record"], sort_keys=True), str(result["field"])): result
        for result in given.results
    }
    expected = {
        (one.model, json.dumps(reference(one.record), sort_keys=True), one.field): one
        for one in check.results
    }
    problems = (
        [f"results {sorted(keyed)} given, {sorted(expected)} expected"]
        if keyed.keys() != expected.keys()
        else []
    )
    for key in sorted(keyed.keys() & expected.keys()):
        for name, wanted in expected[key].members.items():
            found = keyed[key].get(name)
            # an expected member of `None` must be absent: a result holds no JSON null
            absent_or_not = (name in keyed[key]) if wanted is None else (name not in keyed[key])
            if absent_or_not or (wanted is not None and member_differs(name, wanted, found)):
                problems.append(f"{key[0]} {key[2]} {name}: {found!r}, not {wanted!r}")
    unused = frozenset(
        (str(entry["model"]), int(index))
        for entry in given.unused
        if isinstance(index := entry["acceptance"], float)
    )
    if unused != check.unused:
        problems.append(f"unused {sorted(unused)}, not {sorted(check.unused)}")
    if check.refused is not None and given.refused != check.refused:
        problems.append(f"refused {given.refused}, not {check.refused}")
    if check.resolved is not None and list(given.records) != [reference(name) for name in check.resolved]:
        problems.append(f"records {list(given.records)}, not those of {check.resolved}")
    return f"{check.what}: {'; '.join(problems)}" if problems else None


def water_waiver_with_label(declaration: JsonObject) -> None:
    waiver = acceptances(declaration)[0]
    assert isinstance(waiver, dict)
    waiver["label"] = NEWTONIAN


def nominal_at_water(declaration: JsonObject) -> None:
    nominal = copy.deepcopy(acceptances(declaration)[0])
    assert isinstance(nominal, dict)
    nominal["record"] = reference(WATER)
    acceptances(declaration).append(nominal)


def nominal_for_another_field(declaration: JsonObject) -> None:
    nominal = copy.deepcopy(acceptances(declaration)[0])
    assert isinstance(nominal, dict)
    nominal["field"] = VISCOSITY
    acceptances(declaration).append(nominal)


def implied_condition_again(token: str) -> Callable[[JsonObject], None]:
    def change(declaration: JsonObject) -> None:
        implied = copy.deepcopy(acceptances(declaration)[0])
        assert isinstance(implied, dict)
        implied["token"] = token
        acceptances(declaration).append(implied)

    return change


# The temperature supplied is 0 K, which the operating 310.15 K is outside of and nothing covers.
OUTSIDE_AT_ZERO: Final[Mapping[str, JsonValue]] = {
    "status": "not_met",
    "reasons": [{"code": "condition_outside", "condition": "temperature"}],
    "accepted": False,
    "not_accepted": [{"code": "condition_outside", "condition": "temperature"}],
}


def implied_conditions_of_one_value(first: float, second: float) -> Callable[[JsonObject], None]:
    """Two implied conditions, the second naming a token the specimen does not state, supplying the
    temperature `first` and `second`."""

    def change(declaration: JsonObject) -> None:
        implied = acceptances(declaration)[0]
        assert isinstance(implied, dict)
        implied["implies"] = {"temperature": {"value": first, "unit": "K"}}
        other = copy.deepcopy(implied)
        other["token"] = "ex_vivo_fresh"
        other["implies"] = {"temperature": {"value": second, "unit": "K"}}
        acceptances(declaration).append(other)

    return change


def one_alternative_left(declaration: JsonObject) -> None:
    # The second alternative states 310.65 K, outside a tolerance of 0.25 K at 310.15 K: set aside at step 10.
    conditions = requirement(declaration)["conditions"]
    assert isinstance(conditions, dict)
    del conditions["test_method"]
    temperature = conditions["temperature"]
    assert isinstance(temperature, dict)
    temperature["tolerance"] = {"value": 0.25, "unit": "K"}
    model(declaration)["acceptances"] = []


def one_alternative_left_with_no_label_required(declaration: JsonObject) -> None:
    one_alternative_left(declaration)
    del requirement(declaration)["label"]


def permuted(order: tuple[int, ...]) -> Callable[[JsonObject], None]:
    def change(declaration: JsonObject) -> None:
        held = acceptances(declaration)
        model(declaration)["acceptances"] = [held[index] for index in order]

    return change


def models_reversed(declaration: JsonObject) -> None:
    models = declaration["models"]
    assert isinstance(models, list)
    declaration["models"] = models[::-1]


def required(**members: JsonValue) -> Callable[[JsonObject], None]:
    def change(declaration: JsonObject) -> None:
        requirement(declaration).update(members)

    return change


def without_operating(name: str) -> Callable[[JsonObject], None]:
    def change(declaration: JsonObject) -> None:
        operating = declaration["operating_conditions"]
        assert isinstance(operating, dict)
        del operating[name]

    return change


def located_at(name: str) -> Callable[[JsonObject], None]:
    def change(declaration: JsonObject) -> None:
        acceptance = acceptances(declaration)[0]
        assert isinstance(acceptance, dict)
        acceptance["record"] = reference(name)

    return change


located_at_water: Final = located_at(WATER)


def labelled_at_plasma(declaration: JsonObject) -> None:
    water_waiver_with_label(declaration)
    located_at(PLASMA)(declaration)


def in_model(**members: JsonValue) -> Callable[[JsonObject], None]:
    def change(declaration: JsonObject) -> None:
        model(declaration).update(members)

    return change


def unstated(condition: str, alternative: int | None = None) -> JsonObject:
    reason: JsonObject = {"code": "condition_unstated", "condition": condition}
    if alternative is not None:
        reason["alternative"] = float(alternative)
    return reason


def record_with(**members: JsonValue) -> Callable[[JsonObject], None]:
    """A stored record with members set (a `schema_version` of another version, a `record_type` of none)."""

    def change(record: JsonObject) -> None:
        record.update(members)

    return change


def record_without(name: str) -> Callable[[JsonObject], None]:
    def change(record: JsonObject) -> None:
        del record[name]

    return change


def label_stored(label: str) -> Callable[[JsonObject], None]:
    def change(record: JsonObject) -> None:
        field_of(record)["label"] = label

    return change


def field_of(record: JsonObject) -> JsonObject:
    """The record's `fluid.dynamic_viscosity`, a field of the suite's fixtures."""
    members = build_results_model.members
    sections = members(members(record["body"]).get("sections"))
    held = members(members(members(sections.get("fluid")).get("fields")).get("dynamic_viscosity"))
    assert held
    return held


def first_alternative_unlabelled(record: JsonObject) -> None:
    first = build_results_model.entries(field_of(record)["alternatives"])[0]
    assert isinstance(first, dict)
    del first["label"]


def every_alternative_unlabelled(record: JsonObject) -> None:
    for alternative in build_results_model.entries(field_of(record)["alternatives"]):
        assert isinstance(alternative, dict)
        alternative.pop("label", None)


def waiver_at(code: str, **record: JsonValue) -> Callable[[JsonObject], None]:
    """The waiver of a build-check file, naming `code`, located at the record with members changed."""

    def change(declaration: JsonObject) -> None:
        waiver = acceptances(declaration)[0]
        assert isinstance(waiver, dict)
        waiver["code"] = code
        named = waiver["record"]
        assert isinstance(named, dict)
        named.update(record)

    return change


def labelled_waiver(**members: JsonValue) -> Callable[[JsonObject], None]:
    def change(declaration: JsonObject) -> None:
        water_waiver_with_label(declaration)
        waiver = acceptances(declaration)[0]
        assert isinstance(waiver, dict)
        waiver.update(members)

    return change


def extrapolation_at_the_nominal(declaration: JsonObject) -> None:
    """An extrapolation for the field the nominal is for, at its record: given to the read, which applies the
    nominal."""
    nominal = acceptances(declaration)[0]
    assert isinstance(nominal, dict)
    acceptances(declaration).append(
        {
            "acceptance": "extrapolation",
            "record": nominal["record"],
            "field": nominal["field"],
            "method": "constant",
            "law": "the value at the readable range's nearest end, held constant",
            "basis": "the density varies little below the tabulated range over the operating band",
            "reason": "the operating temperature lies below the tabulated range",
        }
    )


def implied_for_two_conditions(declaration: JsonObject) -> None:
    """The implied condition supplies the shear rate beside the temperature, the temperature second."""
    implied = acceptances(declaration)[0]
    assert isinstance(implied, dict)
    implied["implies"] = {
        "shear_rate": {"range": [50.0, 500.0], "unit": "1/s"},
        "temperature": {"value": 310.15, "unit": "K"},
    }


def in_second_model(**members: JsonValue) -> Callable[[JsonObject], None]:
    def change(declaration: JsonObject) -> None:
        model(declaration, 1).update(members)

    return change


def same_pin_other_bytes(name: str) -> bytes:
    """A second source for the pin of a fixture: the record with another name, so another bytes."""
    record = parse(input_bytes(name))
    assert isinstance(record, dict)
    record["name"] = "another name for the same pin"
    return json.dumps(record).encode()


SHEAR_RATE: Final = unstated("shear_rate")
UNKNOWN_TOKEN: Final[JsonObject] = {"code": "unknown_token"}
LABEL_MISMATCH: Final[JsonObject] = {"code": "label_mismatch"}
WANT_MISMATCH: Final[JsonObject] = {"code": "want_mismatch"}
NOT_REVIEWED: Final[JsonObject] = {"code": "not_reviewed"}
NOMINAL: Final[JsonObject] = {"acceptance": "nominal", "value": 1180.0}


def refused_at_a_step_before_the_field(code: str, change: Callable[[JsonObject], object]) -> Direct:
    """A record found by its pin, whose stored label differs from the one required, refused by `code` at a
    step from 2 to 5 (the stored record edited in memory): the result rests on no stored value, and
    the record was resolved (Open point: record_a_read_resolved)."""
    reason: JsonObject = {"code": code}
    return Direct(
        f"no label_mismatch past a record refused as {code}",
        declared("bc027_stored_label_differs.json"),
        (LINEAR,),
        (
            Expected(
                "drag",
                LINEAR,
                VISCOSITY,
                {
                    "reasons": [reason],
                    "accepted": False,
                    "accepted_by": [],
                    "not_accepted": [reason],
                },
            ),
        ),
        resolved=(LINEAR,),
        edited={LINEAR: change},
    )


def waiver_located_at_another(what: str, **record: JsonValue) -> Direct:
    """A waiver that would cover the water record's `condition_unstated`, located at another `id` or
    `version` of it: it covers nothing, and is unused."""
    return Direct(
        what,
        changed("bc016_waiver_for_another_code.json", waiver_at("condition_unstated", **record)),
        (WATER,),
        (
            Expected(
                "drag",
                WATER,
                VISCOSITY,
                {
                    "reasons": [SHEAR_RATE],
                    "accepted": False,
                    "accepted_by": [],
                    "not_accepted": [SHEAR_RATE],
                },
            ),
        ),
        frozenset({("drag", 0)}),
    )


def labelled_waiver_that_would_not_cover(what: str, **waiver: JsonValue) -> Direct:
    """A waiver resting on a label, of a code or a condition that would not cover the reason: decided and
    unused."""
    return Direct(
        what,
        changed("bc049_reviewed_value.json", labelled_waiver(**waiver)),
        ("water_review_reviewed.json",),
        (
            Expected(
                "drag",
                "water_review_reviewed.json",
                VISCOSITY,
                {
                    "reasons": [SHEAR_RATE],
                    "accepted": False,
                    "accepted_by": [],
                    "not_accepted": [SHEAR_RATE],
                },
            ),
        ),
        frozenset({("drag", 0)}),
    )


CHECKS: Final = (
    # declarations.md:318-319 "join the read's, and the" and "result's status is the worst of them all": a
    # `not_reviewed` (unknown) never lowers a read's `not_met`, and the value stays (R05).
    Direct(
        "not_reviewed beside a read's not_met that carries a value",
        changed("bc020_nominal_inside_the_bounds.json", required(review="reviewed")),
        (GRADE,),
        (
            Expected("drag", GRADE, DENSITY, {
                "status": "not_met", "reasons": [WANT_MISMATCH, NOT_REVIEWED], "value": 1180.0,
                "assumption": NOMINAL, "accepted": False, "accepted_by": [0], "not_accepted": [NOT_REVIEWED],
            }),
        ),
        refused=True,
    ),
    # declarations.md:315-316 "that name the read's field" and "and are located at its location": a nominal
    # at another record given too would make two nominals for one field, `request_incomplete`.
    Direct(
        "a nominal at another record is not given",
        changed("bc020_nominal_inside_the_bounds.json", nominal_at_water),
        (GRADE,),
        (
            Expected("drag", GRADE, DENSITY, {
                "status": "not_met", "reasons": [WANT_MISMATCH], "value": 1180.0, "assumption": NOMINAL,
                "accepted": True, "accepted_by": [0], "not_accepted": [],
            }),
        ),
        frozenset({("drag", 1)}),
        refused=False,
    ),
    # declarations.md:315 "that name the read's field": a nominal for another field, of the same value, is
    # neither given nor applied, and is unused.
    Direct(
        "a nominal for another field is not given",
        changed("bc020_nominal_inside_the_bounds.json", nominal_for_another_field),
        (GRADE,),
        (
            Expected("drag", GRADE, DENSITY, {
                "status": "not_met", "reasons": [WANT_MISMATCH], "value": 1180.0, "accepted": True,
                "accepted_by": [0], "not_accepted": [], "specimen_differences": [],
            }),
        ),
        frozenset({("drag", 1)}),
    ),
    # declarations.md:297-299 "an implied condition that filled a" ... "condition (a `conditions` entry whose
    # `record` is the value the implied condition supplies, with basis": each implied condition whose value an
    # entry shows with basis `implied` filled it, whether or not the specimen states its fact and token (the
    # sentence states no condition on the specimen, the row for supplying does, declarations.md:364 "on
    # fields whose specimen states that fact and token": Open point: implied_applied_by_the_value_shown), so
    # two supplying one value are both applied.
    Direct(
        "two implied conditions that agree are both applied",
        changed("bc017_fills_an_unstated_condition.json", implied_condition_again("in_vivo")),
        (IN_VIVO_UNSTATED,),
        (
            Expected("drag", IN_VIVO_UNSTATED, VISCOSITY, {
                "status": "met", "reasons": [], "value": 0.000692, "accepted": True, "accepted_by": [0, 1],
            }),
        ),
    ),
    Direct(
        "an implied condition of the same value whose token the specimen does not state is applied too",
        changed("bc017_fills_an_unstated_condition.json", implied_condition_again("ex_vivo_fresh")),
        (IN_VIVO_UNSTATED,),
        (
            Expected("drag", IN_VIVO_UNSTATED, VISCOSITY, {
                "status": "met", "reasons": [], "accepted": True, "accepted_by": [0, 1],
            }),
        ),
    ),
    # read_side_contract.md:110-112 "Two values differ unless they are of one shape, a value, a range or a
    # token, and hold the same token or the same numbers bit for bit": an implied value is compared as two
    # values are, so `0` and `-0` differ and the entry the first supplied is not the value the second
    # supplies; changes.md:204-206 "are of one shape, a value, a range or a token, and hold the same token or
    # the same numbers bit for bit". The first case is the control: equal zeros agree.
    Direct(
        "two implied conditions supplying 0 and 0 are both applied",
        changed("bc017_fills_an_unstated_condition.json", implied_conditions_of_one_value(0.0, 0.0)),
        (IN_VIVO_UNSTATED,),
        (
            Expected("drag", IN_VIVO_UNSTATED, VISCOSITY, {**OUTSIDE_AT_ZERO, "accepted_by": [0, 1]}),
        ),
    ),
    Direct(
        "an implied condition supplying -0 where the entry holds 0 is not applied",
        changed("bc017_fills_an_unstated_condition.json", implied_conditions_of_one_value(0.0, -0.0)),
        (IN_VIVO_UNSTATED,),
        (
            Expected("drag", IN_VIVO_UNSTATED, VISCOSITY, {**OUTSIDE_AT_ZERO, "accepted_by": [0]}),
        ),
        frozenset({("drag", 1)}),
    ),
    Direct(
        "an implied condition supplying 0 where the entry holds -0 is not applied",
        changed("bc017_fills_an_unstated_condition.json", implied_conditions_of_one_value(-0.0, 0.0)),
        (IN_VIVO_UNSTATED,),
        (
            Expected("drag", IN_VIVO_UNSTATED, VISCOSITY, {**OUTSIDE_AT_ZERO, "accepted_by": [0]}),
        ),
        frozenset({("drag", 1)}),
    ),
    # declarations.md:298-299 "a `conditions` entry whose `record` is the value the implied condition
    # supplies": the entry of the condition by its name, whichever the implied condition names first.
    Direct(
        "an implied condition naming two conditions fills the one it supplies the value of",
        changed("bc017_fills_an_unstated_condition.json", implied_for_two_conditions),
        (IN_VIVO_UNSTATED,),
        (
            Expected("drag", IN_VIVO_UNSTATED, VISCOSITY, {
                "status": "met", "reasons": [], "accepted": True, "accepted_by": [0],
            }),
        ),
    ),
    # declarations.md:322-323 "A result that rests on no stored value (its" and "a refusal before step 7 finds
    # the field": no `label_mismatch`, though the record's field holds no label. Open point:
    # label_of_no_stored_value. A read refused at step 0 resolves no record.
    Direct(
        "no label_mismatch past step 0's want_mismatch",
        changed("bc027_required_label_absent.json", required(want="reference_data")),
        (LABEL_MISSING,),
        (
            Expected("drag", LABEL_MISSING, VISCOSITY, {
                "status": "not_met", "reasons": [WANT_MISMATCH], "value": None, "accepted": False,
                "accepted_by": [], "not_accepted": [WANT_MISMATCH],
            }),
        ),
        frozenset({("drag", 0)}),
        resolved=(),
    ),
    Direct(
        "no label_mismatch past step 0's request_incomplete",
        changed("bc027_required_label_absent.json", without_operating("shear_rate")),
        (LABEL_MISSING,),
        (
            Expected("drag", LABEL_MISSING, VISCOSITY, {
                "status": "not_met", "reasons": [{"code": "request_incomplete", "condition": "shear_rate"}],
                "accepted": False, "accepted_by": [],
            }),
        ),
        frozenset({("drag", 0)}),
    ),
    # The same, past a refusal at steps 2 to 5, by each reason that step gives before the field is found.
    refused_at_a_step_before_the_field("other_version", record_with(schema_version="0.9.0")),
    refused_at_a_step_before_the_field("malformed", record_without("licence")),
    refused_at_a_step_before_the_field("unknown_type", record_with(record_type="gadget")),
    # declarations.md:321 "stored on the value the result rests on (the field, or the alternative read)": the
    # one left (its alternatives each store the Newtonian label: Open point: alternative_a_result_rests_on);
    # the field holding them stores none.
    Direct(
        "the one alternative left is checked against its own label",
        changed("bc016_waiver_covers_each_alternatives_reason.json", one_alternative_left),
        (TWO_ALTERNATIVES,),
        (
            Expected("drag", TWO_ALTERNATIVES, VISCOSITY, {
                "status": "met", "reasons": [], "value": 0.000692, "accepted": True, "accepted_by": [],
            }),
        ),
    ),
    # read_side_contract.md:302-303 "alternative left or picked": the one left names no reason, and the
    # alternatives store different labels (the first none), so the label to check is step 7's to say.
    Direct(
        "the one alternative left, unnamed among alternatives storing different labels",
        changed("bc016_waiver_covers_each_alternatives_reason.json", one_alternative_left),
        (TWO_ALTERNATIVES,),
        undecided="alternative_unnamed",
        edited={TWO_ALTERNATIVES: first_alternative_unlabelled},
    ),
    # declarations.md:181-182 "A requirement with a `label` gives": a requirement with none checks none, so
    # the one left decides, though it is unnamed among alternatives storing different labels (the first none).
    Direct(
        "no label required, the one alternative left unnamed among alternatives storing different labels",
        changed(
            "bc016_waiver_covers_each_alternatives_reason.json", one_alternative_left_with_no_label_required
        ),
        (TWO_ALTERNATIVES,),
        (
            Expected("drag", TWO_ALTERNATIVES, VISCOSITY, {
                "status": "met", "reasons": [], "value": 0.000692, "accepted": True, "accepted_by": [],
            }),
        ),
        edited={TWO_ALTERNATIVES: first_alternative_unlabelled},
    ),
    # declarations.md:181-182 "when the label stored on the" and "value the result rests on differs or is
    # absent": every alternative stores none, so whichever is left, the label is absent.
    Direct(
        "a label required, every alternative unlabelled, the one left unnamed",
        changed("bc016_waiver_covers_each_alternatives_reason.json", one_alternative_left),
        (TWO_ALTERNATIVES,),
        (
            Expected("drag", TWO_ALTERNATIVES, VISCOSITY, {
                "status": "not_met", "reasons": [LABEL_MISMATCH], "value": 0.000692, "accepted": False,
                "accepted_by": [], "not_accepted": [LABEL_MISMATCH],
            }),
        ),
        edited={TWO_ALTERNATIVES: every_alternative_unlabelled},
    ),
    # declarations.md:205 "A result that holds no `provenance` gets no such reason": none under `no_pick`.
    Direct(
        "no not_reviewed under no_pick, which holds no provenance",
        changed("bc016_waiver_covers_each_alternatives_reason.json", required(review="reviewed")),
        (TWO_ALTERNATIVES,),
        (
            Expected("drag", TWO_ALTERNATIVES, VISCOSITY, {
                "status": "unknown",
                "reasons": [{"code": "no_pick"}, unstated("test_method", 0), unstated("test_method", 1)],
                "accepted": False, "accepted_by": [0], "not_accepted": [{"code": "no_pick"}],
            }),
        ),
    ),
    # declarations.md:256 "The build MUST refuse to build while any result is not accepted", whichever model
    # holds it.
    Direct(
        "the verdict follows the last model too",
        declared("bc010_each_model_judged_by_its_own_acceptances.json"),
        (WATER,),
        (
            Expected("drag", WATER, VISCOSITY, {"accepted": True, "accepted_by": [0]}),
            Expected("lift", WATER, VISCOSITY, {"accepted": False, "accepted_by": []}),
        ),
        refused=True,
    ),
    Direct(
        "the verdict follows the first model too",
        changed("bc010_each_model_judged_by_its_own_acceptances.json", models_reversed),
        (WATER,),
        (
            Expected("drag", WATER, VISCOSITY, {"accepted": True, "accepted_by": [0]}),
            Expected("lift", WATER, VISCOSITY, {"accepted": False, "accepted_by": []}),
        ),
        refused=True,
    ),
    Direct(
        "every result accepted is no refusal",
        declared("bc010_all_accepted.json"),
        (WATER,),
        (
            Expected("drag", WATER, VISCOSITY, {"accepted": True}),
            Expected("lift", WATER, VISCOSITY, {"accepted": True}),
        ),
        refused=False,
        resolved=(WATER,),
    ),
    # declarations.md:252 "lists the 0-based indexes, in the model's `acceptances`, of every": permuted, they
    # follow.
    Direct(
        "acceptances permuted, their indexes follow",
        changed("bc009_two_acceptances_indexes.json", permuted((2, 0, 1))),
        (WATER,),
        (
            Expected("drag", WATER, VISCOSITY, {
                "reasons": [SHEAR_RATE, unstated("test_method")], "accepted": True, "accepted_by": [0, 1],
            }),
        ),
        frozenset({("drag", 2)}),
    ),
    Direct(
        "models permuted, each keeps its unused",
        changed("bc053_unused_per_model.json", models_reversed),
        (WATER,),
        (
            Expected("drag", WATER, VISCOSITY, {"accepted": True, "accepted_by": [0]}),
            Expected("lift", WATER, VISCOSITY, {"accepted": False, "accepted_by": []}),
        ),
        frozenset({("lift", 0)}),
    ),
    # declarations.md:261 "`records`, every record a read resolved, as": none for a read that resolves none,
    # and none where nothing is read.
    Direct(
        "the records two reads resolved",
        declared("bc002_both_records_listed.json"),
        (WATER, PLASMA),
        (
            Expected("drag", WATER, VISCOSITY, {"accepted": True}),
            Expected("drag", PLASMA, VISCOSITY, {"accepted": True}),
        ),
        resolved=(WATER, PLASMA),
    ),
    Direct(
        "no record a read did not resolve",
        declared("bc002_listed_record_absent_from_the_store.json"),
        (WATER,),
        (Expected("drag", PLASMA, VISCOSITY, {"reasons": [{"code": "absent"}]}),),
        resolved=(),
    ),
    Direct(
        "no record where nothing is read",
        declared("bc003_field_read_with_no_requirement.json"),
        (WATER,),
        (Expected("drag", WATER, VISCOSITY, {"reasons": [{"code": "no_requirement"}], "value": None}),),
        resolved=(),
    ),
    # A pin that no source holds (a hash that differs), and a pin held by two sources of different bytes
    # (`malformed`), resolve no record (Open point: record_a_read_resolved).
    Direct(
        "no record a pin matches by id and version alone",
        declared("bc027_stored_label_differs.json"),
        (WATER,),
        (Expected("drag", LINEAR, VISCOSITY, {"reasons": [{"code": "pin_mismatch"}]}),),
        resolved=(),
    ),
    Direct(
        "no record where two sources of different bytes hold the pin",
        changed("bc016_waiver_for_another_code.json", waiver_at("condition_unstated")),
        (WATER,),
        (Expected("drag", WATER, VISCOSITY, {"reasons": [{"code": "malformed"}]}),),
        frozenset({("drag", 0)}),
        resolved=(),
        beside=(same_pin_other_bytes(WATER),),
    ),
    # declarations.md:394 "It covers its reason only on a result whose stored label": trust comes after
    # 0.1.0.dev4; a waiver resting on a label that would cover nothing else is decided.
    Direct(
        "a waiver resting on a label that would cover its reason",
        changed("bc049_reviewed_value.json", water_waiver_with_label),
        ("water_review_reviewed.json",),
        undecided="label_trust",
    ),
    Direct(
        "a waiver resting on a label at another record",
        changed("bc049_reviewed_value.json", labelled_at_plasma),
        ("water_review_reviewed.json",),
        (
            Expected("drag", "water_review_reviewed.json", VISCOSITY, {
                "reasons": [SHEAR_RATE], "accepted": False, "accepted_by": [], "not_accepted": [SHEAR_RATE],
            }),
        ),
        frozenset({("drag", 0)}),
    ),
    labelled_waiver_that_would_not_cover(
        "a waiver resting on a label, of another code than the reason's", code="condition_unchecked"
    ),
    labelled_waiver_that_would_not_cover(
        "a waiver resting on a label, of another condition than the reason's", condition="temperature"
    ),
    # declarations.md:302-303 "equal in `id`, `version` and `content_hash`": a waiver that would cover,
    # located at the record's other `version`, or at another `id`, covers nothing.
    waiver_located_at_another("a waiver located at another version of the record", version="9.9.9"),
    waiver_located_at_another("a waiver located at another id", id="conformance/another_record"),
    # declarations.md:412 "an `extrapolation`, only on a result whose `assumption` names it": one at another
    # record is not given, nor does it cover.
    Direct(
        "an extrapolation at another record",
        changed("bc019_outside_range_under_an_extrapolation.json", located_at_water),
        (DENSITY_TABLE,),
        (
            Expected("drag", DENSITY_TABLE, DENSITY, {
                "status": "not_met", "reasons": [{"code": "outside_range", "condition": "temperature"}],
                "value": None, "assumption": None, "accepted": False, "accepted_by": [],
            }),
        ),
        frozenset({("drag", 0)}),
    ),
    # declarations.md:181-182 "differs or is absent": a label is a token, compared as written.
    Direct(
        "a stored label that differs from the one required in case alone",
        changed("bc016_waiver_for_another_code.json", waiver_at("condition_unstated")),
        (WATER,),
        (
            Expected("drag", WATER, VISCOSITY, {
                "reasons": [UNKNOWN_TOKEN, LABEL_MISMATCH], "accepted": False, "accepted_by": [],
                "not_accepted": [UNKNOWN_TOKEN, LABEL_MISMATCH],
            }),
        ),
        frozenset({("drag", 0)}),
        edited={WATER: label_stored("Materica.Fluid.Newtonian.v1")},
    ),
    # read_side_contract.md:133 "the declaration it rests on": a nominal the read applied, and an
    # extrapolation given beside it, which the result's `assumption` does not name, is not applied.
    Direct(
        "an extrapolation given beside a nominal the read applied is not applied",
        changed("bc020_nominal_inside_the_bounds.json", extrapolation_at_the_nominal),
        (GRADE,),
        (
            Expected("drag", GRADE, DENSITY, {
                "status": "not_met", "reasons": [WANT_MISMATCH], "value": 1180.0, "assumption": NOMINAL,
                "accepted": True, "accepted_by": [0], "not_accepted": [],
            }),
        ),
        frozenset({("drag", 1)}),
    ),
    # A read the read model gives no verdict on gives none: no build-check fixture reaches the read model's
    # own no verdicts, so a stand-in read model gives them (`no_verdict_on_a_read_over_records`).
    Direct(
        "a read the read model gives no verdict on",
        declared("bc028_one_model_one_record.json"),
        (WATER,),
        undecided="the_read",
        read=no_verdict_on_a_read_over_records,
    ),
    Direct(
        "a read of the request over no records, to tell step 0, that the read model gives no verdict on",
        declared("bc028_one_model_one_record.json"),
        (WATER,),
        undecided="the_read",
        read=no_verdict_on_a_read_over_none,
    ),
    # S7a-3's and S7a-4's, in the second model too: a target naming a fact, combinations, a `trainable` entry.
    Direct(
        "a target naming a fact",
        changed("bc028_one_model_one_record.json", in_model(target={"species": {"ncbi_taxon": 9606.0}})),
        (WATER,),
        undecided="specimen_differences",
    ),
    Direct(
        "combinations",
        changed("bc028_one_model_one_record.json", in_model(
            reads=[VISCOSITY, DENSITY], combinations=[[VISCOSITY, DENSITY]])),
        (WATER,),
        undecided="specimen_differences",
    ),
    Direct(
        "a trainable entry",
        changed("bc028_one_model_one_record.json", in_model(
            trainable=[{"field": VISCOSITY, "record": reference(WATER)}])),
        (WATER,),
        undecided="trainable",
    ),
    Direct(
        "a target naming a fact in the second model",
        changed("bc010_each_model_judged_by_its_own_acceptances.json", in_second_model(
            target={"species": {"ncbi_taxon": 9606.0}})),
        (WATER,),
        undecided="specimen_differences",
    ),
    Direct(
        "a trainable entry in the second model",
        changed("bc010_each_model_judged_by_its_own_acceptances.json", in_second_model(
            trainable=[{"field": VISCOSITY, "record": reference(WATER)}])),
        (WATER,),
        undecided="trainable",
    ),
)  # fmt: skip


def problems() -> list[str]:
    """Every direct check the model fails."""
    return [problem for check in CHECKS if (problem := judged(check)) is not None]
