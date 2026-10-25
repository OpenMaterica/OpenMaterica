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
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Final

from tests.reference import build_model, build_results_model
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


def answer(check: Direct) -> build_results_model.Report | build_model.Refused | NoVerdict:
    sources = [input_bytes(name) for name in check.records]
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


def one_alternative_left(declaration: JsonObject) -> None:
    # The second alternative states 310.65 K, outside a tolerance of 0.25 K at 310.15 K: set aside at step 10.
    conditions = requirement(declaration)["conditions"]
    assert isinstance(conditions, dict)
    del conditions["test_method"]
    temperature = conditions["temperature"]
    assert isinstance(temperature, dict)
    temperature["tolerance"] = {"value": 0.25, "unit": "K"}
    model(declaration)["acceptances"] = []


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


SHEAR_RATE: Final = unstated("shear_rate")
WANT_MISMATCH: Final[JsonObject] = {"code": "want_mismatch"}
NOT_REVIEWED: Final[JsonObject] = {"code": "not_reviewed"}
NOMINAL: Final[JsonObject] = {"acceptance": "nominal", "value": 1180.0}

CHECKS: Final = (
    # declarations.md:305-306 "join the read's, and the" and "result's status is the worst of them all": a
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
    # declarations.md:302-303 "that name the read's field" and "and are located at its location": a nominal
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
    # declarations.md:302 "that name the read's field": a nominal for another field, of the same value, is
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
    # Open point: two_implied_that_agree. Two implied conditions that both apply and agree both filled the
    # condition; one whose token the specimen does not state filled nothing.
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
        "an implied condition of the same value whose token the specimen does not state is not applied",
        changed("bc017_fills_an_unstated_condition.json", implied_condition_again("ex_vivo_fresh")),
        (IN_VIVO_UNSTATED,),
        (
            Expected("drag", IN_VIVO_UNSTATED, VISCOSITY, {
                "status": "met", "reasons": [], "accepted": True, "accepted_by": [0],
            }),
        ),
        frozenset({("drag", 1)}),
    ),
    # declarations.md:309-310 "A result that rests on no stored value (its" and "a refusal before step 7 finds
    # the field": no `label_mismatch`, though the record's field holds no label. Open point:
    # label_of_no_stored_value.
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
    # declarations.md:308 "stored on the value the result rests on (the field, or the alternative read)": the
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
    # declarations.md:195 "A result that holds no `provenance` gets no such reason": none under `no_pick`.
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
    # declarations.md:246 "The build MUST refuse to build while any result is not accepted", whichever model
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
    ),
    # declarations.md:242 "lists the 0-based indexes, in the model's `acceptances`, of every": permuted, they
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
    # declarations.md:251 "`records`, every record a read resolved, as": none for a read that resolves none,
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
    # declarations.md:381 "It covers its reason only on a result whose stored label": trust comes after
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
    # declarations.md:397 "an `extrapolation`, only on a result whose `assumption` names it": one at another
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
    # S7a-3's and S7a-4's: a target naming a fact, combinations, a `trainable` entry.
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
)  # fmt: skip


def problems() -> list[str]:
    """Every direct check the model fails."""
    return [problem for check in CHECKS if (problem := judged(check)) is not None]
