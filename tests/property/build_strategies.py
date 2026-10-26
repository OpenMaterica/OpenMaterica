# SPDX-License-Identifier: Apache-2.0
"""Strategies for HP43 to HP46 (the S7 design's 6.5): stores of records and declarations over them that
`declarations.md` section 1 takes, checked by `check_build`; and, for HP43, results and acceptances drawn
directly, judged by `judge`.

A record is a material of up to two sections, built here at physical scales from the build-check cases'
fixtures (a viscosity of 0.000692 Pa.s, a density of 1261 kg/m3, a grade's density limits, a density table
over temperature and one with a declared edge), each value holding what a draw asks of it: its label, its
review, its conditions stated or unstated, its specimen's tissue state, and alternatives. A whole build draws
its operating temperature first and states its records' values there, or 20 K away, so that a draw's reads
are met, refused or waiting about as often. Each record is pinned (its content hash computed), and a store
holds it or not. A declaration reads such records: one to three models, each checked over listed records and
reading one or two fields, each with a requirement or none; and acceptances of the kinds a build of this
version reads (waivers, implied conditions, nominals, extrapolations), each located at a record listed or
elsewhere: another record, another version or content hash of one, another field, or, in HP43's direct
draws, a region or an interval beside the record. No declaration here holds what a later piece reads (a
pick, an overlay, a `target` fact, `combinations` or `trainable`), for which `check_build` raises.

Each drawing part is split into strata of at most two of its ways (`STRATA`), each drawn by a test of its own
that draws its way first among them, alike, and builds the draw for it, recording the way so that the feature
audit holds it to its draw floor. The draws plant, record or compute nothing the oracles judge with: the
properties read what to expect from the declaration, the store and the text alone. Where a draw needs to
know a read's outcome to reach a way (a condition met, an alternative set aside), it builds values far from
the bounds that decide it.

The parts:
- HP43, `judge` drawn directly: `waivers` (one matching a reason, or differing from it in its code, its
  condition, its location or its field), `assumptions` (a nominal or an extrapolation that the result's
  `assumption` names or not, a reason other than the one an assumption covers, and a pick or an extrapolation
  beside a reason its row lists with no condition of its own), and `never` (a reason section 4.2 lists for no
  waiver, beside a waiver that names it, and `at_edge` beside an extrapolation); `indexes`, whole builds, each
  result's verdict and the unused acceptances judged by their indexes.
- HP44, `requests` (an operating value or range; an implied condition, a nominal or an extrapolation at the
  record or elsewhere) and `coverage` (a record listed or not, a field with a requirement or none, two models
  over one record, a listed record absent from the store).
- HP45, `label` (the stored label equal, different, absent, absent or equal under a refusal before step 12,
  no stored value, and absent under a read that is `met`), `review` (reviewed, not checked, an unknown result,
  a slip, no `review` required), and `label_waiver` (a waiver naming the requirement's label, on a value
  reviewed and labelled, unreviewed, unlabelled or of another label). HP45's `label_trust` part waits for
  label trust, after 0.1.0.dev4 (maintainer, 2026-10-21).
- HP46: builds of two or three models, permuted.
"""

import copy
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from hypothesis import strategies as st

from materica.core.declarations import Acceptance
from materica.core.hashing import content_hash
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult
from materica.core.reasons import Reason
from materica.core.vocabulary import VOCABULARY
from materica.shapes import ReasonCode, Suite
from tests.property.strategies import Size

JsonObject = dict[str, JsonValue]
Draw = st.DrawFn

VISCOSITY, DENSITY, COMPOSITION = "fluid.dynamic_viscosity", "bulk.density", "bulk.elemental_composition"
FIELDS = (VISCOSITY, DENSITY)
# The label the viscosity's row names (`record_format.md` section 4.1); one the reader knows that the row does
# not name for the field (`form_invalid`), and one it does not know (`unknown_token`): PR-053.
NEWTONIAN = "materica.fluid.newtonian.v1"
OTHER_LABELS = ("materica.magnetic.linear.v1", "acme.fluid.newtonian.v1")
BODY, ROOM, COLD, COLDER = 310.15, 293.15, 270.0, 260.0
VISCOSITY_VALUE, DENSITY_VALUE, NOMINAL_VALUE = 0.000692, 1261.0, 1180.0
# A viscosity's value, where a part draws one: a fluid's, from water's to a syrup's, in Pa.s.
VISCOSITIES = st.floats(min_value=0.0003, max_value=10.0)
IDS = ("property/build_a", "property/build_b", "property/build_c")
VERSION, OTHER_VERSION = "1.0.0", "1.0.1"
OTHER_HASH = "sha256:" + "f" * 64
MODELS = ("drag", "lift", "heat")
# The claims a build is drawn under: every build claims plain read and the build checks (README, "Suites and
# case numbers"), with the hash suite or without it.
WITH_HASH: frozenset[Suite] = frozenset({"plain_read", "hash", "build_checks"})
WITHOUT_HASH: frozenset[Suite] = frozenset({"plain_read", "build_checks"})
CLAIMS = st.sampled_from((WITH_HASH, WITHOUT_HASH))

# Section 4.2's rows, as data for the draws (the properties hold their own reading): the codes a waiver
# covers, those of them whose reasons carry a condition, and codes no row lists, by status.
WAIVED_WITH_A_CONDITION = ("condition_unstated", "condition_unchecked", "condition_uncertain")
WAIVED = (
    "no_requirement",
    "stated_without_origin",
    "outside_check_points",
    "fill_in_version_mismatch",
    "entries_withheld",
    "not_reviewed",
    "engine_mass_not_comparable",
)
LISTED = frozenset(
    {
        *WAIVED_WITH_A_CONDITION,
        *WAIVED,
        "no_pick",
        "range_unstated",
        "outside_coverage",
        "outside_range",
        "want_mismatch",
        "overlay_scope_mismatch",
    }
)
UNLISTED_NOT_MET = tuple(
    sorted(
        code
        for code, spec in VOCABULARY.reasons.items()
        if spec.status == "not_met" and code not in LISTED and code not in ("label_mismatch", "at_edge")
    )
)
UNLISTED_UNKNOWN = tuple(
    sorted(
        code
        for code, spec in VOCABULARY.reasons.items()
        if spec.status == "unknown" and code not in LISTED and code != "no_pick"
    )
)
# A code's condition, where its reasons always carry one (section 1's waiver row): the `condition_*` codes,
# `outside_range`, `at_edge` and `range_unstated`.
WITH_A_CONDITION = frozenset(
    {*(code for code in VOCABULARY.reasons if code.startswith("condition_")), "outside_range", "at_edge"}
    | {"range_unstated"}
)
CONDITIONS = ("temperature", "shear_rate", "density_kind", "measurement_geometry")


def stated(value: float, unit: str) -> JsonObject:
    return {"value": value, "unit": unit, "basis": "stated"}


UNSTATED: JsonObject = {"status": "unstated"}
APPARENT: JsonObject = {"token": "apparent", "basis": "stated"}
IN_VIVO: JsonObject = {"tissue_state": {"token": "in_vivo", "basis": "stated"}}
SHEAR_RATES: JsonObject = {"range": [50.0, 500.0], "unit": "1/s"}
# A shear rate a value states, over the operating range's and beyond it.
STATED_SHEAR_RATES: JsonObject = {"range": [10.0, 1000.0], "unit": "1/s", "basis": "stated"}

STATISTICS: JsonObject = {
    "central": "stated",
    "n_specimens": {"status": "unstated"},
    "n_donors": {"status": "not_applicable"},
    "mean": {"status": "unstated"},
    "sd": {"status": "unstated"},
    "min": {"status": "unstated"},
    "max": {"status": "unstated"},
    "distribution": {"status": "unstated"},
    "basis": {"status": "not_applicable"},
    "represents": {"status": "unstated"},
    "dispersion": "not_reported",
    "relative_uncertainty": {"status": "none"},
    "expanded_uncertainty": {"status": "none"},
}
# A table's statistics: no central value, mean or extremes over its axis.
TABLE_STATISTICS: JsonObject = {
    **STATISTICS,
    **{name: {"status": "not_applicable"} for name in ("central", "mean", "min", "max")},
}

# A value's review (`provenance.md` section 2 item 6), by kind: a completed review; one not checked, with
# its reason or without; one whose `result` is no token of the list; and one holding a slip of `result`,
# which a read takes as not checked (PR-030).
REVIEWS: dict[str, JsonObject] = {
    "reviewed": {
        "result": "reviewed",
        "reviewer": "a property's reviewer",
        "date": "2026-10-15",
        "independent_of_extraction": True,
        "checklist": ["value", "unit"],
    },
    "not_checked": {"status": "not_checked", "reason": "a property's fixture"},
    "not_checked_bare": {"status": "not_checked"},
    "unknown_result": {"result": "approved", "reviewer": "a property's reviewer", "date": "2026-10-15"},
    "slip": {"reslt": "reviewed", "reviewer": "a property's reviewer", "date": "2026-10-15"},
}
NOT_REVIEWED = ("not_checked", "not_checked_bare", "unknown_result", "slip")


def provenance(review: JsonObject) -> JsonObject:
    return {
        "origin": "measured_by_contributor",
        "extraction": {"method": "own_measurement"},
        "assistance": {"status": "none"},
        "review": copy.deepcopy(review),
    }


# Values and records.


def viscosity(
    temperature: JsonObject,
    *,
    label: str | None = NEWTONIAN,
    review: str = "not_checked",
    shear_rate: JsonObject = UNSTATED,
    value: float = VISCOSITY_VALUE,
) -> JsonObject:
    """A constant viscosity, its temperature and shear rate as given."""
    field: JsonObject = {
        "form": "constant",
        "unit": "Pa.s",
        "value": value,
        "conditions": {"temperature": copy.deepcopy(temperature), "shear_rate": copy.deepcopy(shear_rate)},
        "statistics": copy.deepcopy(STATISTICS),
        "provenance": provenance(REVIEWS[review]),
    }
    if label is not None:
        field["label"] = label
    return field


# A density's forms: a constant at room temperature; a grade's specification limits; a table over
# temperature from 280 to 340 K; and one with a declared edge at 273 K, readable from 263 K.
DENSITY_FORMS = ("constant", "interval", "table", "edge_table")
TABLES: dict[str, JsonObject] = {
    "table": {
        "axis": "temperature",
        "axis_unit": "K",
        "x": [280.0, 300.0, 320.0, 340.0],
        "y": [1000.0, 996.0, 990.0, 986.0],
        "scheme": "linear",
        "edges": [],
    },
    "edge_table": {
        "axis": "temperature",
        "axis_unit": "K",
        "x": [263.0, 273.0, 273.0, 283.0],
        "y": [918.0, 916.0, 1000.0, 999.5],
        "scheme": "linear",
        "edges": [273.0],
    },
}


def density(
    form: str,
    *,
    temperature: JsonObject | None = None,
    kind: JsonObject = APPARENT,
    review: str = "not_checked",
) -> JsonObject:
    """A density of `form`, at room temperature where it is no table, whose temperature is its axis."""
    field: JsonObject = {"form": "table" if form == "edge_table" else form, "unit": "kg/m3"}
    tabled = form in TABLES
    if form == "constant":
        field["value"] = DENSITY_VALUE
    elif form == "interval":
        field["interval"] = {"lower": 1150.0, "upper": 1250.0, "basis": "specification_limits"}
        field["specimen"] = {"lot": {"status": "not_applicable"}}
    else:
        field["table"] = copy.deepcopy(TABLES[form])
    at_temperature: JsonObject = {"status": "not_applicable"} if tabled else stated(ROOM, "K")
    field["conditions"] = {
        "temperature": copy.deepcopy(at_temperature if temperature is None else temperature),
        "density_kind": copy.deepcopy(kind),
    }
    field["statistics"] = copy.deepcopy(TABLE_STATISTICS if tabled else STATISTICS)
    field["provenance"] = provenance(REVIEWS[review])
    return field


def section(fields: dict[str, JsonObject], *, in_vivo: bool = False) -> JsonObject:
    held: JsonObject = {"fields": dict(fields)}
    if in_vivo:
        held["specimen"] = copy.deepcopy(IN_VIVO)
    return held


def material(identity: str, sections: JsonObject) -> JsonObject:
    """A pinned material record of `sections`."""
    record: JsonObject = {
        "schema_version": "0.1.0",
        "record_type": "material",
        "id": identity,
        "version": VERSION,
        "name": "A material (property)",
        "licence": {"values": "CC0-1.0", "evidence": "excluded"},
        "content_hash": "sha256:" + "0" * 64,
        "body": {"sections": copy.deepcopy(sections)},
    }
    return repinned(record)


def repinned(record: JsonObject) -> JsonObject:
    return {**record, "content_hash": content_hash(record)}


def reference(record: JsonObject) -> JsonObject:
    return {member: record[member] for member in ("id", "version", "content_hash")}


def source(record: JsonObject) -> bytes:
    return json.dumps(record).encode()


def field_of(record: JsonObject, field: str) -> JsonObject | None:
    """The stored field `field` of `record`, or None."""
    body = record.get("body")
    sections = body.get("sections") if isinstance(body, dict) else None
    held = sections.get(field.partition(".")[0]) if isinstance(sections, dict) else None
    fields = held.get("fields") if isinstance(held, dict) else None
    found = fields.get(field.partition(".")[2]) if isinstance(fields, dict) else None
    return found if isinstance(found, dict) else None


# Declarations.


def tolerance(value: float, unit: str) -> JsonObject:
    return {"tolerance": {"value": value, "unit": unit}, "reason": "the model's sensitivity"}


ACCEPT_APPARENT: JsonObject = {"accept": ["apparent"], "reason": "the buoyancy acts on the whole specimen"}


def requirement(
    field: str,
    conditions: JsonObject,
    *,
    want: str = "value",
    label: str | None = None,
    review: bool = False,
) -> JsonObject:
    held: JsonObject = {"field": field, "want": want, "conditions": copy.deepcopy(conditions)}
    if label is not None:
        held["label"] = label
    if review:
        held["review"] = "reviewed"
    return held


def model(
    name: str,
    records: Sequence[JsonObject],
    reads: Sequence[str],
    requirements: Sequence[JsonObject],
    acceptances: Sequence[JsonObject],
) -> JsonObject:
    return {
        "model": {"name": name, "version": "1.0.0"},
        "model_configuration_hash": "sha256:" + "4" * 64,
        "checked_over": {"records": [reference(record) for record in records]},
        "target": {},
        "reads": list(reads),
        "consumer_parameters": [],
        "requirements": [copy.deepcopy(held) for held in requirements],
        "families": {},
        "combinations": [],
        "acceptances": [copy.deepcopy(held) for held in acceptances],
        "chains": [],
    }


def declaration(operating: JsonObject, models: Sequence[JsonObject]) -> JsonObject:
    return {
        "consumer": {"name": "a_property", "version": "1.0.0"},
        "operating_conditions": copy.deepcopy(operating),
        "models": list(models),
    }


def operating_at(temperature: float | list[float]) -> JsonObject:
    held: JsonObject = (
        {"range": list(temperature), "unit": "K"}
        if isinstance(temperature, list)
        else {"value": temperature, "unit": "K"}
    )
    return {"temperature": held, "shear_rate": copy.deepcopy(SHEAR_RATES)}


def located(at: JsonObject | None, **members: JsonValue) -> JsonObject:
    return {**({} if at is None else {"record": copy.deepcopy(at)}), **members}


def waiver(
    at: JsonObject | None, field: str, code: str, condition: str | None = None, **more: JsonValue
) -> JsonObject:
    held = located(at, acceptance="waiver", field=field, code=code)
    if condition is not None:
        held["condition"] = condition
    return {**held, **more, "reason": "the consumer's judgement"}


def implied(at: JsonObject, field: str, implies: JsonObject, token: str = "in_vivo") -> JsonObject:
    return {
        **located(at, acceptance="implied_condition", field=field),
        "fact": "tissue_state",
        "token": token,
        "implies": copy.deepcopy(implies),
        "reason": "a value measured in vivo was measured at body temperature",
    }


def nominal(at: JsonObject, field: str, value: float = NOMINAL_VALUE) -> JsonObject:
    return {
        **located(at, acceptance="nominal", field=field),
        "value": value,
        "basis": "a value within the stated limits",
        "reason": "the model needs one number",
    }


def pick(at: JsonObject, field: str) -> JsonObject:
    return {
        **located(at, acceptance="pick", field=field),
        "index": 0,
        "reason": "the first alternative is the one the model was fitted on",
    }


def extrapolation(at: JsonObject, field: str, method: str = "constant") -> JsonObject:
    return {
        **located(at, acceptance="extrapolation", field=field),
        "method": method,
        "law": "the value at the readable range's nearest end, held constant",
        "basis": "the density varies little below the tabulated range",
        "reason": "the operating temperature lies below the tabulated range",
    }


# Where an acceptance that is not at the record read is: another record, the record's id at another version,
# or its id and version at another content hash.
ELSEWHERE = ("id", "version", "content_hash")


def elsewhere(at: JsonObject, how: str) -> JsonObject:
    moved = copy.deepcopy(at)
    if how == "id":
        moved["id"] = next(identity for identity in IDS if identity != at["id"])
    elif how == "version":
        moved["version"] = OTHER_VERSION
    else:
        moved["content_hash"] = OTHER_HASH
    return moved


# What a draw is.


@dataclass(frozen=True)
class World:
    """A build drawn whole: the store's sources, the claims, and the declaration, as `check_build` takes
    them; the part and the way the draw showed."""

    part: str
    way: str
    sources: tuple[bytes, ...]
    claims: frozenset[Suite]
    declaration: JsonObject


@dataclass(frozen=True)
class Judged:
    """A result and acceptances drawn directly for `judge`: the result's reasons, its read (the `assumption`
    the verdict reads), its record and field, the model's acceptances as the declaration's check gives them,
    and the indexes of those the read applied."""

    way: str
    reasons: tuple[Reason, ...]
    read: ReadResult | None
    record: MaterialRef
    field: str
    acceptances: tuple[Acceptance, ...]
    applied: tuple[int, ...]


# HP43's direct draws.

HP43_PARTS: dict[str, tuple[str, ...]] = {
    "waivers": ("matching", "code_differs", "condition_differs", "location_differs", "field_differs"),
    "assumptions": (
        "nominal_named",
        "nominal_not_named",
        "extrapolation_named",
        "extrapolation_not_named",
        "other_reason",
        "pick",
        "extrapolation_unconditioned",
    ),
    "never": ("unlisted_not_met", "no_pick", "label_mismatch", "unlisted_code", "at_edge"),
}
# Where a waiver located elsewhere is: one member of the record's reference changed, or a region or an
# interval named beside the record (section 4.1's location rule asks for one at least).
WAIVER_ELSEWHERE = (*ELSEWHERE, "region", "interval")
JUDGED_RECORD = MaterialRef(IDS[0], VERSION, "sha256:" + "1" * 64)


def acceptances_of(given: Sequence[JsonObject]) -> tuple[Acceptance, ...]:
    """The acceptances as the declaration's check gives them: each one's index, kind, the record it names
    (its location over records), its field and its members as given."""
    found: list[Acceptance] = []
    for index, held in enumerate(given):
        at = held.get("record")
        location = (
            MaterialRef(str(at["id"]), str(at["version"]), str(at["content_hash"]))
            if isinstance(at, dict)
            else None
        )
        field = held.get("field")
        kind = held["acceptance"]
        assert isinstance(kind, str)
        found.append(Acceptance(index, kind, location, field if isinstance(field, str) else None, held))
    return tuple(found)


def condition_for(draw: Draw, code: str) -> str | None:
    return draw(st.sampled_from(CONDITIONS)) if code in WITH_A_CONDITION else None


@st.composite
def a_reason(draw: Draw, codes: Sequence[str]) -> Reason:
    code = draw(st.sampled_from(codes))
    return Reason(
        cast(ReasonCode, code),
        condition_for(draw, code),
        alternative=draw(st.sampled_from((None, None, 0, 1))),
    )


def other_field(field: str) -> str:
    return DENSITY if field == VISCOSITY else VISCOSITY


def a_read(reasons: Sequence[Reason], assumption: JsonObject | None) -> ReadResult:
    """A read's result holding `reasons` and, where given, the `assumption` the read's value rests on."""
    statuses = [VOCABULARY.reasons[reason.code].status for reason in reasons]
    status = "not_met" if "not_met" in statuses else "unknown" if statuses else "met"
    return ReadResult(status, tuple(reasons), assumption=assumption)  # type: ignore[arg-type]  # a JSON object


def assumed(acceptance: JsonObject) -> JsonObject:
    """The `assumption` a read gives where its value rests on `acceptance`: its kind and its kind's own
    members as the request gave them, `basis` aside (`read_side_contract.md` section 2's members table)."""
    own = ("value", "params") if acceptance["acceptance"] == "nominal" else ("method", "law")
    return {
        "acceptance": acceptance["acceptance"],
        **{name: copy.deepcopy(acceptance[name]) for name in own if name in acceptance},
    }


@st.composite
def judged(draw: Draw, part: str, size: Size, ways: Sequence[str]) -> Judged:
    """A result and acceptances for `judge`, its way drawn first among the part's."""
    way = draw(st.sampled_from(tuple(ways)))
    field = draw(st.sampled_from(FIELDS))
    at = cast(JsonObject, JUDGED_RECORD.to_json())
    reasons: list[Reason] = []
    given: list[JsonObject] = []
    assumption: JsonObject | None = None
    if part == "waivers":
        codes = WAIVED_WITH_A_CONDITION if way == "condition_differs" else (*WAIVED_WITH_A_CONDITION, *WAIVED)
        reason = draw(a_reason(codes))
        reasons.append(reason)
        code, condition, field_named = str(reason.code), reason.condition, field
        if way == "code_differs":
            code = draw(
                st.sampled_from([other for other in (*WAIVED_WITH_A_CONDITION, *WAIVED) if other != code])
            )
            condition = condition_for(draw, code)
        elif way == "condition_differs":
            condition = draw(st.sampled_from([other for other in CONDITIONS if other != reason.condition]))
        elif way == "field_differs":
            field_named = other_field(field)
        given.append(_waiver_at(draw, way, at, field_named, code, condition))
    elif part == "assumptions":
        given, reasons, assumption = draw(_assumed(way, at, field))
    else:
        given, reasons, assumption = draw(_never(way, at, field))
    planted = len(reasons)
    reasons += draw(st.lists(a_reason((*WAIVED_WITH_A_CONDITION, *WAIVED, *UNLISTED_NOT_MET)), max_size=2))
    if len(reasons) > planted:
        # Waivers of some of the other reasons, never of the one the way plants.
        others = st.sampled_from(range(planted, len(reasons)))
        for extra in draw(st.lists(others, max_size=size.members - 2)):
            held = reasons[extra]
            given.append(waiver(at, field, held.code, held.condition))
    order = draw(st.permutations(range(len(given))))
    acceptances = acceptances_of([given[index] for index in order])
    # The read applied a nominal or an extrapolation exactly where its result's `assumption` names it.
    applied = tuple(
        acceptance.index
        for acceptance in acceptances
        if acceptance.kind in ("nominal", "extrapolation") and assumed(acceptance.members) == assumption
    )
    unique = list(dict.fromkeys(reasons))
    return Judged(way, tuple(unique), a_read(unique, assumption), JUDGED_RECORD, field, acceptances, applied)


def _waiver_at(
    draw: Draw, way: str, at: JsonObject, field: str, code: str, condition: str | None
) -> JsonObject:
    if way != "location_differs":
        return waiver(at, field, code, condition)
    how = draw(st.sampled_from(WAIVER_ELSEWHERE))
    if how == "region":
        return waiver(at, field, code, condition, region="lumen")
    if how == "interval":
        return waiver(at, field, code, condition, interval={"path": "wall", "index": 0.0})
    return waiver(elsewhere(at, how), field, code, condition)


@st.composite
def _assumed(
    draw: Draw, way: str, at: JsonObject, field: str
) -> tuple[list[JsonObject], list[Reason], JsonObject | None]:
    """A nominal or an extrapolation at the result, whose kind's reason the result holds, and the
    `assumption` the way gives: naming it, naming another (its value or law changed, or another kind), or
    none. Or a pick beside `no_pick`, or an extrapolation beside `range_unstated` or `outside_coverage`: the
    rows that need no condition of their acceptance, under no `assumption`. A pick is drawn here alone, for
    `judge`; a build raises on one before any read until S7c."""
    if way == "pick":
        return [pick(at, field)], [Reason("no_pick")], None
    if way == "extrapolation_unconditioned":
        unconditioned = draw(st.sampled_from(("range_unstated", "outside_coverage")))
        reason = (
            Reason("range_unstated", "temperature")
            if unconditioned == "range_unstated"
            else Reason("outside_coverage")
        )
        return [extrapolation(at, field)], [reason], None
    by_nominal = way.startswith("nominal") or (way == "other_reason" and draw(st.booleans()))
    held = (
        nominal(at, field, draw(st.sampled_from((NOMINAL_VALUE, 1200.0))))
        if by_nominal
        else extrapolation(at, field, draw(st.sampled_from(("constant", "consumer_law"))))
    )
    named = assumed(held)
    if way.endswith("_named") and not way.endswith("not_named"):
        reason = Reason("want_mismatch") if by_nominal else Reason("outside_range", "temperature")
        return [held], [reason], named
    if way.endswith("not_named"):
        reason = Reason("want_mismatch") if by_nominal else Reason("outside_range", "temperature")
        other = draw(st.sampled_from(("none", "changed", "other_kind")))
        if other == "none":
            return [held], [reason], None
        if other == "changed":
            changed = dict(named, **({"value": 1210.0} if by_nominal else {"law": "another law"}))
            return [held], [reason], changed
        return [held], [reason], assumed(extrapolation(at, field) if by_nominal else nominal(at, field))
    # The assumption names the acceptance, and the reason is one its row does not list.
    reason = draw(
        st.sampled_from(
            (
                Reason("outside_range", "temperature"),
                Reason("condition_unstated", "shear_rate"),
                Reason("at_edge", "temperature"),
            )
            if by_nominal
            else (
                Reason("want_mismatch"),
                Reason("condition_unstated", "shear_rate"),
                Reason("nominal_invalid"),
            )
        )
    )
    return [held], [reason], named


@st.composite
def _never(
    draw: Draw, way: str, at: JsonObject, field: str
) -> tuple[list[JsonObject], list[Reason], JsonObject | None]:
    """A reason section 4.2 never lets a waiver cover, beside a waiver naming it at the result; and `at_edge`
    beside an extrapolation at the result."""
    if way == "at_edge":
        # A read never applies an extrapolation at an edge (`read_side_contract.md` section 5).
        return [extrapolation(at, field)], [Reason("at_edge", "temperature")], None
    if way == "unlisted_not_met":
        code = draw(st.sampled_from(UNLISTED_NOT_MET))
    elif way == "unlisted_code":
        code = draw(st.sampled_from(UNLISTED_UNKNOWN))
    else:
        code = way
    reason = Reason(
        cast(ReasonCode, code), condition_for(draw, code), alternative=draw(st.sampled_from((None, 0)))
    )
    return [waiver(at, field, code, reason.condition)], [reason], None


# Whole builds: records, then a declaration over them.

# What a record's value is drawn as, each a way a read ends, at the build's operating temperature or the
# middle of its range: a viscosity stated there, or 20 K away (`condition_outside`), in vivo with its
# temperature unstated (an implied condition fills it), or two alternatives there and 0.5 K away; a density
# as a constant or an interval stated there, a table or a table with an edge, or in vivo with its temperature
# and kind unstated. In vivo values are half the viscosities and a third of the densities, and intervals a
# third of the densities: HP43's `indexes` kills its rarest mutants only there (an implied value of the other
# sign of zero, an implied token, an extrapolation beside a nominal that applied), and CI's first drift run
# killed two of them past the margin guard. Here and below, a choice's first value, which a search draws
# about twice as often as each other in its first examples (a probe of Hypothesis 6.169), is the one those
# kills need: in vivo, the pair or the token, the other sign of zero, an extrapolation beside a nominal, an
# acceptance kept at its record, a requirement present, and no waiver of another code beside them.
VISCOSITY_KINDS = ("in_vivo", "met", "outside", "in_vivo", "alternatives", "in_vivo")
DENSITY_KINDS = (
    "in_vivo",
    "interval",
    "constant",
    "table",
    "edge_table",
    "interval",
    "in_vivo",
    "interval",
    "in_vivo",
)
# An in vivo value whose record states one of the two conditions an implied condition supplies (its shear
# rate, or its density's kind), a third of the in vivo values.
IN_VIVO_STATED = "in_vivo_stated"
# A nominal inside the grade's limits, which supplies an interval's value, or outside them
# (`nominal_invalid`).
NOMINALS = (NOMINAL_VALUE, NOMINAL_VALUE, 1300.0, NOMINAL_VALUE)


@dataclass(frozen=True)
class Drawn:
    """A record as drawn: its record, as pinned, and the kind of each of its fields (`IN_VIVO_STATED` for
    an in vivo value that states one of the two conditions)."""

    record: JsonObject
    kinds: dict[str, str]


def a_viscosity(
    kind: str, at: float, label: str | None, review: str, *, shear_stated: bool = False
) -> JsonObject:
    """A viscosity of `kind` about the temperature `at`; in vivo, its shear rate stated over 10 to 1000 1/s
    where asked, so that of two conditions an implied condition supplies, it fills one."""
    if kind == "alternatives":
        return {
            "alternatives": [
                viscosity(stated(at, "K"), label=label, review=review),
                viscosity(stated(at + 0.5, "K"), label=label, review=review, value=0.000695),
            ]
        }
    if kind == "in_vivo":
        shear: JsonObject = STATED_SHEAR_RATES if shear_stated else UNSTATED
        return viscosity(UNSTATED, label=label, review=review, shear_rate=shear)
    return viscosity(stated(at if kind == "met" else at + 20.0, "K"), label=label, review=review)


def a_density(kind: str, at: float, review: str, *, kind_stated: bool = False) -> JsonObject:
    """A density of `kind` about the temperature `at`; in vivo, its kind stated where asked, so that of two
    conditions an implied condition supplies, it fills one."""
    if kind == "in_vivo":
        return density(
            "constant", temperature=UNSTATED, kind=APPARENT if kind_stated else UNSTATED, review=review
        )
    if kind in TABLES:
        return density(kind, review=review)
    return density(kind, temperature=stated(at, "K"), review=review)


@st.composite
def a_record(
    draw: Draw, identity: str, fields: Sequence[str], at: float, kinds: dict[str, str] | None = None
) -> Drawn:
    """A record of `identity` holding `fields` about the temperature `at`, each of a kind drawn, or given in
    `kinds`."""
    chosen: dict[str, str] = {}
    sections: JsonObject = {}
    for field in fields:
        review = draw(st.sampled_from(("not_checked", "reviewed")))
        if field == VISCOSITY:
            kind = (kinds or {}).get(field) or draw(st.sampled_from(VISCOSITY_KINDS))
            label = draw(st.sampled_from((NEWTONIAN, NEWTONIAN, None)))
            stated = kind == "in_vivo" and draw(st.integers(0, 2)) == 2
            held = a_viscosity(kind, at, label, review, shear_stated=stated)
            sections["fluid"] = section({"dynamic_viscosity": held}, in_vivo=kind == "in_vivo")
        else:
            kind = (kinds or {}).get(field) or draw(st.sampled_from(DENSITY_KINDS))
            stated = kind == "in_vivo" and draw(st.integers(0, 2)) == 2
            held = a_density(kind, at, review, kind_stated=stated)
            sections["bulk"] = section({"density": held}, in_vivo=kind == "in_vivo")
        chosen[field] = IN_VIVO_STATED if stated else kind
    return Drawn(material(identity, sections), chosen)


def conditions_for(draw: Draw, field: str, kind: str) -> JsonObject:
    """A requirement's conditions for `field`: a temperature tolerance, but over a table, whose axis it is,
    where it is named in about half the draws; a shear rate's in about a third; the density's kind."""
    if field == VISCOSITY:
        held: JsonObject = {"temperature": tolerance(draw(st.sampled_from((1.0, 1.0, 0.25))), "K")}
        if draw(st.integers(0, 2)) == 0:
            held["shear_rate"] = tolerance(0.0, "1/s")
        return held
    held = {"density_kind": copy.deepcopy(ACCEPT_APPARENT)}
    if kind not in TABLES or draw(st.booleans()):
        held["temperature"] = tolerance(1.0, "K")
    return held


@st.composite
def a_requirement(draw: Draw, field: str, kind: str) -> JsonObject:
    label = NEWTONIAN if field == VISCOSITY and draw(st.integers(0, 2)) == 0 else None
    return requirement(
        field,
        conditions_for(draw, field, kind),
        want=draw(st.sampled_from(("value", "value", "value", "bounds"))),
        label=label,
        review=draw(st.integers(0, 3)) == 0,
    )


# The implied conditions an in vivo value is given: its temperature implied as a value or a range, two
# conditions implied by one acceptance, and for a viscosity a pair of one value, one of whose tokens the
# specimen does not state, their numbers equal or of the other sign of zero, a shear rate at rest, and for a
# density its kind implied as a token. Where the record states one of the two conditions (`IN_VIVO_STATED`),
# the two-condition acceptance is drawn in half the draws, since only there does it fill one condition of
# two; where it states neither, the pair or the token in two of five, since only there do they fill one.
IMPLIED_KINDS = {
    VISCOSITY: ("pair", "value", "range", "two_conditions", "pair"),
    DENSITY: ("token", "value", "range", "two_conditions", "token"),
}
STATED_IMPLIED_KINDS = {
    VISCOSITY: ("two_conditions", "value", "two_conditions", "range", "two_conditions", "pair"),
    DENSITY: ("two_conditions", "value", "two_conditions", "range", "two_conditions", "token"),
}


def implies_for(field: str, how: str, at: float) -> JsonObject:
    temperature: JsonObject = {"value": at, "unit": "K"}
    if how == "range":
        return {"temperature": {"range": [at - 0.5, at + 0.5], "unit": "K"}}
    if how == "token" and field == DENSITY:
        return {"density_kind": {"token": "apparent"}}
    if how == "two_conditions":
        second: JsonObject = (
            {"shear_rate": {"value": 100.0, "unit": "1/s"}}
            if field == VISCOSITY
            else {"density_kind": {"token": "apparent"}}
        )
        return {"temperature": temperature, **second}
    return {"temperature": temperature}


@st.composite
def implied_acceptances(
    draw: Draw, record: JsonObject, field: str, at: float, *, stated: bool = False
) -> list[JsonObject]:
    how = draw(st.sampled_from((STATED_IMPLIED_KINDS if stated else IMPLIED_KINDS)[field]))
    if how != "pair":
        return [implied(record, field, implies_for(field, how, at))]
    zero = draw(st.sampled_from((0.0, -0.0)))
    other = draw(st.sampled_from((-zero, zero)))
    pair = [
        implied(record, field, {"shear_rate": {"value": zero, "unit": "1/s"}}),
        implied(record, field, {"shear_rate": {"value": other, "unit": "1/s"}}, token="phantom"),
    ]
    return pair if draw(st.booleans()) else pair[::-1]


@st.composite
def acceptances_for(draw: Draw, drawn: Drawn, field: str, record: JsonObject, at: float) -> list[JsonObject]:
    """Acceptances a model may declare for `field` at `record`, by the field's kind: a waiver of a reason its
    read gives, an implied condition, a nominal and in most draws an extrapolation beside it, or an
    extrapolation, where the kind meets one, in about two thirds of those draws one alike for the section's
    other field beside the first (the one a read of the kind applies), and in about a quarter of the draws a
    waiver of another code."""
    kind = drawn.kinds.get(field)
    found: list[JsonObject] = []
    if field == VISCOSITY and draw(st.integers(0, 3)):
        found.append(waiver(record, field, "condition_unstated", "shear_rate"))
    if kind in ("in_vivo", IN_VIVO_STATED):
        found += draw(implied_acceptances(record, field, at, stated=kind == IN_VIVO_STATED))
    elif kind == "interval":
        found.append(nominal(record, field, draw(st.sampled_from(NOMINALS))))
        if draw(st.integers(0, 3)) < 3:
            found.append(extrapolation(record, field))
    elif kind in TABLES:
        found.append(extrapolation(record, field, draw(st.sampled_from(("constant", "consumer_law")))))
    elif kind == "outside" and draw(st.booleans()):
        found.append(waiver(record, field, "condition_outside", "temperature"))
    if field == DENSITY and kind in ("interval", *TABLES) and draw(st.integers(0, 2)) < 2:
        found.append({**found[0], "field": COMPOSITION})
    if draw(st.integers(0, 3)) == 3:
        found.append(waiver(record, field, draw(st.sampled_from(WAIVED)), None))
    return found


@st.composite
def placed(draw: Draw, held: JsonObject, listed: Sequence[JsonObject]) -> JsonObject:
    """`held` where it was drawn in most draws; else at another record listed, or elsewhere."""
    at = held.get("record")
    if not isinstance(at, dict) or draw(st.integers(0, 4)) < 4:
        return held
    others = [reference(record) for record in listed if reference(record) != at]
    how = draw(st.sampled_from(("listed", *ELSEWHERE) if others else ELSEWHERE))
    moved = draw(st.sampled_from(others)) if how == "listed" else elsewhere(at, how)
    return {**held, "record": moved}


@st.composite
def a_model(
    draw: Draw,
    name: str,
    drawn: Sequence[Drawn],
    size: Size,
    at: float,
    *,
    reads: Sequence[str] | None = None,
) -> JsonObject:
    """A model over a non-empty selection of `drawn`, in an order drawn, reading one or both fields, each with
    a requirement in most draws, and declaring acceptances for its records and fields."""
    chosen = draw(st.lists(st.sampled_from(range(len(drawn))), min_size=1, max_size=len(drawn), unique=True))
    listed = [drawn[index] for index in chosen]
    fields = list(reads) if reads is not None else draw(st.permutations(FIELDS))[: draw(st.integers(1, 2))]
    requirements: list[JsonObject] = []
    for field in fields:
        if draw(st.integers(0, 5)) < 5:
            requirements.append(draw(a_requirement(field, listed[0].kinds.get(field, "constant"))))
    acceptances: list[JsonObject] = []
    for one in listed:
        for field in fields:
            for held in draw(acceptances_for(one, field, reference(one.record), at)):
                acceptances.append(draw(placed(held, [other.record for other in listed])))
    acceptances = acceptances[: size.members + 2]
    order = draw(st.permutations(range(len(acceptances))))
    return model(
        name,
        [one.record for one in listed],
        fields,
        requirements,
        [acceptances[index] for index in order],
    )


# The operating temperatures a build is drawn at: body and room temperature, below a table's readable range,
# below an edged table's (outside it beyond no edge), at its edge, and a range about body temperature.
TEMPERATURES: tuple[float | list[float], ...] = (
    BODY,
    BODY,
    ROOM,
    COLD,
    COLDER,
    273.0,
    [BODY - 1.0, BODY + 1.0],
)


def middle(temperature: float | list[float]) -> float:
    return (temperature[0] + temperature[1]) / 2 if isinstance(temperature, list) else temperature


@st.composite
def builds(draw: Draw, size: Size, part: str, models: tuple[int, int] = (1, 3)) -> World:
    """A build of one to three records, each holding one field or both, and `models` models over them. It
    draws no way first: its way is its part's name."""
    temperature = draw(st.sampled_from(TEMPERATURES))
    at = middle(temperature)
    count = draw(st.integers(1, min(3, size.members)))
    drawn = [draw(a_record(IDS[index], draw(_fields()), at)) for index in range(count)]
    names = MODELS[: draw(st.integers(*models))]
    declared = [draw(a_model(name, drawn, size, at)) for name in names]
    sources = [source(one.record) for one in drawn]
    return World(
        part,
        part,
        tuple(draw(st.permutations(sources))),
        draw(CLAIMS),
        declaration(operating_at(temperature), declared),
    )


def _fields() -> st.SearchStrategy[list[str]]:
    return st.sampled_from(([VISCOSITY], [DENSITY], [VISCOSITY, DENSITY]))


def indexes(size: Size) -> st.SearchStrategy[World]:
    """HP43's `indexes`: whole builds, no way drawn first."""
    return builds(size, "indexes")


# HP44.

HP44_PARTS: dict[str, tuple[str, ...]] = {
    "requests": ("operating_value", "operating_range", "implied", "nominal", "extrapolation"),
    "coverage": ("unlisted_record", "no_requirement", "two_models", "absent_record"),
}
# Where an acceptance a read could take is put: at the record read, elsewhere, or both, each a third of the
# draws; elsewhere is also another field, of the record's section or of another.
GIVEN_ELSEWHERE = (*ELSEWHERE, "field")


@st.composite
def given_somewhere(draw: Draw, held: JsonObject, field: str) -> list[JsonObject]:
    """`held` at the record read, elsewhere, or both."""
    where = draw(st.sampled_from(("record", "elsewhere", "both")))
    if where == "record":
        return [held]
    how = draw(st.sampled_from(GIVEN_ELSEWHERE))
    moved: JsonObject
    if how == "field":
        moved = {**held, "field": COMPOSITION if field == DENSITY else DENSITY}
    else:
        at = held["record"]
        assert isinstance(at, dict)
        moved = {**held, "record": elsewhere(at, how)}
    return [moved] if where == "elsewhere" else [held, moved]


@st.composite
def requests(draw: Draw, size: Size, ways: Sequence[str]) -> World:
    """HP44's `requests`: one model reading one record's field, by the way drawn, beside acceptances the
    build gives the read or not."""
    way = draw(st.sampled_from(tuple(ways)))
    if way == "operating_range":
        temperature: float | list[float] = draw(
            st.sampled_from(([BODY - 1.0, BODY + 1.0], [ROOM - 0.5, ROOM + 0.5]))
        )
    else:
        temperature = draw(st.sampled_from((BODY, ROOM)))
    if way in ("operating_value", "operating_range"):
        field = draw(st.sampled_from(FIELDS))
        kind = draw(st.sampled_from(("met", "outside"))) if field == VISCOSITY else "constant"
    else:
        field = VISCOSITY if way == "implied" and draw(st.booleans()) else DENSITY
        kind = {"implied": "in_vivo", "nominal": "interval"}.get(way) or draw(
            st.sampled_from(("table", "edge_table"))
        )
    if way == "extrapolation":
        temperature = COLD if kind == "table" else draw(st.sampled_from((COLDER, 273.0)))
    at = middle(temperature)
    one = draw(a_record(IDS[0], [field], at, {field: kind}))
    record = reference(one.record)
    given: list[JsonObject] = []
    if way == "implied":
        for held in draw(implied_acceptances(record, field, at, stated=one.kinds[field] == IN_VIVO_STATED)):
            given += draw(given_somewhere(held, field))
        if draw(st.integers(0, 2)):
            # Beside them, one the specimen does not state the token of, which no read applies.
            given.append(implied(record, field, implies_for(field, "value", at), token="phantom"))
    elif way == "nominal":
        given = draw(given_somewhere(nominal(record, field), field))
    elif way == "extrapolation":
        given = draw(given_somewhere(extrapolation(record, field), field))
    if field == VISCOSITY and draw(st.booleans()):
        given.append(waiver(record, field, "condition_unstated", "shear_rate"))
    if draw(st.integers(0, 3)) == 0:
        given.append(waiver(record, field, draw(st.sampled_from(WAIVED))))
    given = [given[index] for index in draw(st.permutations(range(len(given))))]
    required = draw(a_requirement(field, kind))
    declared = model(MODELS[0], [one.record], [field], [required], given)
    return World(
        "requests",
        way,
        (source(one.record),),
        draw(CLAIMS),
        declaration(operating_at(temperature), [declared]),
    )


@st.composite
def coverage(draw: Draw, size: Size, ways: Sequence[str]) -> World:
    """HP44's `coverage`: which results a build gives, by the way drawn."""
    way = draw(st.sampled_from(tuple(ways)))
    temperature = draw(st.sampled_from(TEMPERATURES))
    at = middle(temperature)
    count = 3 if way == "unlisted_record" else draw(st.integers(1, 3))
    drawn = [draw(a_record(IDS[index], draw(_fields()), at)) for index in range(count)]
    stored = list(drawn)
    if way == "absent_record":
        stored.remove(draw(st.sampled_from(drawn)))
    names = MODELS[: 2 if way == "two_models" else draw(st.integers(1, 2))]
    declared: list[JsonObject] = []
    for name in names:
        listing = drawn[:1] if way == "two_models" else drawn
        if way == "unlisted_record":
            listing = drawn[: draw(st.integers(1, 2))]
        reads = list(FIELDS) if way == "no_requirement" else None
        held = draw(a_model(name, listing, size, at, reads=reads))
        if way == "no_requirement" and draw(st.booleans()):
            held["requirements"] = cast(list[JsonValue], held["requirements"])[:1]
        declared.append(held)
    if way == "absent_record":
        absent = next(reference(one.record) for one in drawn if one not in stored)
        for held in declared:
            listed = cast(list[JsonValue], cast(JsonObject, held["checked_over"])["records"])
            if absent not in listed:
                listed.append(absent)
    sources = [source(one.record) for one in stored]
    return World(
        "coverage",
        way,
        tuple(sources),
        draw(CLAIMS),
        declaration(operating_at(temperature), declared),
    )


# HP45.

HP45_PARTS: dict[str, tuple[str, ...]] = {
    "label": ("equal", "differs", "absent", "early_refusal", "no_stored_value", "absent_met"),
    "review": ("reviewed", "not_checked", "unknown_result", "slip", "not_required"),
    "label_waiver": ("reviewed_and_labelled", "unreviewed", "unlabelled", "another_label"),
}
# Where a result rests on no stored value (section 2 item 8): the record not in the store, the field not in
# it, the record refused at step 2 or 5, and no single alternative (both stay, under `want: value` or
# `bounds`, or both are set aside).
NO_STORED_VALUE = ("record_absent", "field_absent", "other_version", "unknown_type", "no_single_alternative")


@st.composite
def labels(draw: Draw, size: Size, ways: Sequence[str]) -> World:
    """HP45's `label`: a viscosity whose requirement names the Newtonian label, stored as the way says, read
    beside a section that holds an unknown `label` member in some draws (which a read ignores), under claims
    with the hash suite or without it, where a record's stated hash may be stale. Under `absent_met` the value
    states its shear rate and the requirement names it, so that the read is `met` and `label_mismatch` is the
    result's one reason; the other ways leave the shear rate unstated, and their reads end `unknown` or
    `not_met`."""
    way = draw(st.sampled_from(tuple(ways)))
    claims = draw(CLAIMS)
    stored_label: str | None = {"equal": NEWTONIAN, "absent": None, "absent_met": None}.get(way, NEWTONIAN)
    if way == "differs":
        stored_label = draw(st.sampled_from(OTHER_LABELS))
    elif way == "early_refusal":
        stored_label = draw(st.sampled_from((NEWTONIAN, None)))
    tolerated = 1.0
    operating: float = BODY
    value = draw(VISCOSITIES)
    met = way == "absent_met"
    shear = STATED_SHEAR_RATES if met else UNSTATED
    held: JsonObject = viscosity(stated(BODY, "K"), label=stored_label, value=value, shear_rate=shear)
    if way == "early_refusal":
        held = viscosity(stated(ROOM, "K"), label=stored_label, value=value)
    alternatives = way in ("equal", "absent") and draw(st.integers(0, 3)) == 0
    if alternatives:
        # The one left at step 7 holds the label the way gives; the other, set aside, the row's or none. No
        # alternative holds a label a read refuses, which would refuse the field (PR-044, PR-053).
        aside = viscosity(stated(BODY + 5.0, "K"), label=draw(st.sampled_from((NEWTONIAN, None))))
        kept = viscosity(stated(BODY, "K"), label=stored_label, value=value)
        held = {"alternatives": [kept, aside] if draw(st.booleans()) else [aside, kept]}
    want = "value"
    how = draw(st.sampled_from(NO_STORED_VALUE)) if way == "no_stored_value" else None
    if how == "no_single_alternative":
        both = draw(st.sampled_from(("stay", "stay_bounds", "stay_bounds", "set_aside")))
        values: list[JsonValue] = [
            viscosity(stated(temperature, "K"), label=draw(st.sampled_from((NEWTONIAN, None))))
            for temperature in (BODY, BODY + 0.5)
        ]
        held = {"alternatives": values}
        want = "bounds" if both == "stay_bounds" else "value"
        operating = ROOM if both == "set_aside" else BODY
    sections: JsonObject = {"fluid": section({"dynamic_viscosity": held})}
    if how == "field_absent":
        sections = {"bulk": section({"density": density("constant")})}
    beside = draw(st.sampled_from((None, None, NEWTONIAN, OTHER_LABELS[0])))
    if beside is not None:
        cast(JsonObject, sections["fluid" if "fluid" in sections else "bulk"])["label"] = beside
    record = material(IDS[0], sections)
    if how == "other_version":
        record = repinned({**record, "schema_version": "0.2.0"})
    elif how == "unknown_type":
        record = repinned({**record, "record_type": "acme:thing"})
    pinned = reference(record)
    if claims == WITHOUT_HASH and how is None and draw(st.integers(0, 3)) == 0:
        # A record edited after it was pinned: a read without the hash suite takes it.
        record = {**record, "name": "A material (property), edited"}
    sources = () if how == "record_absent" else (source(record),)
    required = requirement(
        VISCOSITY,
        {"temperature": tolerance(tolerated, "K"), **({"shear_rate": tolerance(0.0, "1/s")} if met else {})},
        want=want,
        label=NEWTONIAN,
        review=draw(st.booleans()),
    )
    acceptances = (
        [waiver(pinned, VISCOSITY, "condition_unstated", "shear_rate")] if draw(st.booleans()) else []
    )
    declared = model(MODELS[0], [record], [VISCOSITY], [required], acceptances)
    declared["checked_over"] = {"records": [pinned]}
    return World("label", way, sources, claims, declaration(operating_at(operating), [declared]))


# How the read of a value under review ends: met or unknown with a value; `not_met` with a value, under a
# nominal it applies or an extrapolation; or `not_met` with none, its temperature outside the tolerance.
REVIEW_READS = ("valued", "not_met_valued", "not_met")


@st.composite
def reviews(draw: Draw, size: Size, ways: Sequence[str]) -> World:
    """HP45's `review`: a value whose review is as the way says, read under a requirement holding `review` or
    not, its read ending as drawn."""
    way = draw(st.sampled_from(tuple(ways)))
    review = draw(st.sampled_from(tuple(REVIEWS))) if way == "not_required" else way
    if way == "not_checked":
        review = draw(st.sampled_from(("not_checked", "not_checked_bare")))
    ends = draw(st.sampled_from(REVIEW_READS))
    temperature: float = BODY
    if ends == "not_met_valued":
        kind = draw(st.sampled_from(("interval", "table")))
        field = DENSITY
        held = density(kind, review=review)
        temperature = ROOM if kind == "interval" else COLD
    else:
        field = draw(st.sampled_from(FIELDS))
        kind = "constant"
        held = (
            viscosity(stated(BODY, "K"), review=review, value=draw(VISCOSITIES))
            if field == VISCOSITY
            else density("constant", review=review)
        )
        temperature = ROOM if field == DENSITY else BODY
        if ends == "not_met":
            temperature = COLD if field == DENSITY else ROOM
    name = "fluid" if field == VISCOSITY else "bulk"
    record = material(IDS[0], {name: section({field.partition(".")[2]: held})})
    at = reference(record)
    acceptances: list[JsonObject] = []
    if kind == "interval":
        acceptances.append(nominal(at, field))
    elif kind == "table":
        acceptances.append(extrapolation(at, field))
    if draw(st.booleans()):
        acceptances.append(waiver(at, field, "not_reviewed"))
    required = requirement(field, conditions_for(draw, field, kind), review=way != "not_required")
    declared = model(MODELS[0], [record], [field], [required], acceptances)
    return World(
        "review", way, (source(record),), draw(CLAIMS), declaration(operating_at(temperature), [declared])
    )


@st.composite
def label_waivers(draw: Draw, size: Size, ways: Sequence[str]) -> World:
    """HP45's `label_waiver`: a waiver of the viscosity's unstated shear rate naming the Newtonian label,
    under a requirement naming that label and `review` (section 4.1 item 4), on a value as the way says;
    beside, in half the draws, a waiver of `not_reviewed`. No value here states its label's basis: whether a
    label is trusted by its basis is `label_trust`'s, after 0.1.0.dev4."""
    way = draw(st.sampled_from(tuple(ways)))
    stored_label: str | None = NEWTONIAN
    review = "reviewed" if way == "reviewed_and_labelled" else draw(st.sampled_from(NOT_REVIEWED))
    if way == "unlabelled":
        stored_label = None
    elif way == "another_label":
        stored_label = draw(st.sampled_from(OTHER_LABELS))
    if way in ("unlabelled", "another_label"):
        review = draw(st.sampled_from(tuple(REVIEWS)))
    held = viscosity(stated(BODY, "K"), label=stored_label, review=review, value=draw(VISCOSITIES))
    record = material(IDS[0], {"fluid": section({"dynamic_viscosity": held})})
    at = reference(record)
    acceptances = [waiver(at, VISCOSITY, "condition_unstated", "shear_rate", label=NEWTONIAN)]
    if draw(st.booleans()):
        acceptances.append(waiver(at, VISCOSITY, "not_reviewed"))
    order = draw(st.permutations(range(len(acceptances))))
    required = requirement(VISCOSITY, {"temperature": tolerance(1.0, "K")}, label=NEWTONIAN, review=True)
    declared = model(MODELS[0], [record], [VISCOSITY], [required], [acceptances[index] for index in order])
    return World(
        "label_waiver", way, (source(record),), draw(CLAIMS), declaration(operating_at(BODY), [declared])
    )


# HP46.


def permuted_builds(size: Size) -> st.SearchStrategy[World]:
    """HP46: builds of two or three models; the property permutes them."""
    return builds(size, "permutation", models=(2, 3))


# Each drawing part's ways in strata of at most two, each drawn by a test of its own (the S7 design's 6.1: a
# test function split so that each draws among fewer ways), as S7a-1's HP41 and HP42 were split once CI
# measured their counts: drawn among four or five alike, a way's count varied over 20 streams 6.6 times a
# binomial count's on average, and a way drawn among five fell below its floor at the variance measured in
# about one measurement in five (a simulation), among two in about one in 500.
# HP44's `requests` draws `implied` and `nominal` apart. Drawn alike, `nominal` completed 0.30 of the examples
# and `implied` 0.70 (a mean over 20 streams, CI's floors on the draft's head before this split; locally the
# same, 0.30 over 2,000 and 0.29 over 6,000 examples, with the two ways in either order), so its least share
# fell to a false failure of 3.2e-02 above the 1e-06 the rule allows; `nominal` and `extrapolation` drawn
# alike completed 0.50 each. The cause of `implied` taking more is not established; the measured fix is the
# split, which `extrapolation` shows already runs its 2,000 examples alone.
STRATA: dict[str, tuple[tuple[str, ...], ...]] = {
    "waivers": (("matching", "code_differs"), ("condition_differs", "location_differs"), ("field_differs",)),
    "assumptions": (
        ("nominal_named", "nominal_not_named"),
        ("extrapolation_named", "extrapolation_not_named"),
        ("other_reason",),
        ("pick", "extrapolation_unconditioned"),
    ),
    "never": (("unlisted_not_met", "no_pick"), ("label_mismatch", "unlisted_code"), ("at_edge",)),
    "requests": (("operating_value", "operating_range"), ("implied",), ("nominal",), ("extrapolation",)),
    "coverage": (("unlisted_record", "no_requirement"), ("two_models", "absent_record")),
    "label": (("equal", "differs"), ("absent", "early_refusal"), ("no_stored_value",), ("absent_met",)),
    "review": (("reviewed", "not_checked"), ("unknown_result", "slip"), ("not_required",)),
    "label_waiver": (("reviewed_and_labelled", "unreviewed"), ("unlabelled", "another_label")),
}
PARTS: dict[str, tuple[str, ...]] = {**HP43_PARTS, **HP44_PARTS, **HP45_PARTS}
