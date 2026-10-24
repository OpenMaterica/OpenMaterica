# SPDX-License-Identifier: Apache-2.0
"""A consumer's declaration, checked on its own before any record is read (`declarations.md` section 1).

`Declaration.from_json` reads the text by `record_format.md` section 1 item 6 (`jsonio`) and checks it by
hand, as `envelope.py` checks a record's envelope, against `SHAPE`: the table of the declaration's shape,
place by place, each object a Holds cell gives (a consumer, an operating condition, a target's fact) a place
of its own, and each kind of acceptance a place with its members as section 4.1's row gives them. Tests hold
`SHAPE` to the table as the text gives it and to `schema/0.1/declaration.json`
(`tests/spec_sync/test_declaration_shape.py`), so the code, the schema and the text hold one list.

Each rule is one function, which finds every fault it names:
- `_shape` (BC-048): a member not named at its place, a required member missing, none or two of exclusive
  alternatives, a value of another JSON type, a list shorter than its row asks, a value breaking its Holds;
- `_tokens` (BC-048): every token, unit and registered name against its list, read from the vocabulary;
- `_names` (BC-048): a name given twice; a requirement, `trainable` entry or combination naming a field its
  model does not read; a combination of one section; a `trainable` entry at a record not checked over;
- `_reasons` (BC-004, BC-005): a tolerance's, an accept list's and an acceptance's `reason`, and `basis`
  where the kind needs one; a `reason` or `basis` that is not a string of at least one character is BC-048's;
- `_locations` (BC-037): an acceptance whose kind needs a location and names none;
- `_labels` (BC-050): a waiver resting on a label its requirement does not name, reviewed;
- `_suites` (BC-040, BC-044, BC-043, BC-051): items 7 and 8 and the `population_level` rule, then item 12,
  member by member, against the build's claims.

Each fault is a `Finding`: its case, the pointer of the member at fault (of the object that should hold a
missing member), and, for a missing member or a place's exclusive alternatives, which. `_precedence` keeps one
refusal per fault, of the case first in the refusal paragraph's order, and merges those of one case and
pointer. A declaration that breaks no rule gives a `Declaration`.
"""

import dataclasses
import json
import re
from collections.abc import Callable, Collection, Iterator
from dataclasses import dataclass
from typing import Literal, TypeVar, cast, get_args

from materica import shapes
from materica.core import jsonio
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.reasons import Reason
from materica.core.report import BuildRefusal
from materica.core.slips import one_slip
from materica.core.vocabulary import STATUS_TOKENS, VOCABULARY
from materica.shapes import Suite, Want

JsonObject = dict[str, JsonValue]
_Name = TypeVar("_Name", str, MaterialRef)

# A declaration as JSON text, or as a value already read. A `str` is always text, as a JSON string is never a
# declaration.
DeclarationInput = str | bytes | bytearray | memoryview | JsonValue | shapes.Declaration

# The refusal paragraph's order: "the first of: items 3, 4, 7 and 8, the `population_level` rule and section
# 4.1's location rule [BC-004] [BC-005] [BC-040] [BC-044] [BC-043] [BC-037]; section 4.1 item 4 [BC-050];
# item 12 [BC-051]; this paragraph [BC-048]".
ORDER = ("BC-004", "BC-005", "BC-040", "BC-044", "BC-043", "BC-037", "BC-050", "BC-051", "BC-048")


# The table of the declaration's shape (section 1), place by place.


@dataclass(frozen=True)
class Value:
    """A value of one JSON type (`any`: of none in particular), and what its Holds cell states of it beyond
    its type and its tokens: a function giving what is wrong, or None."""

    type: Literal["string", "number", "any"]
    constraint: Callable[[JsonValue], str | None] | None = None


@dataclass(frozen=True)
class Object:
    """An object whose members are those `SHAPE` names at `place`."""

    place: str


@dataclass(frozen=True)
class List:
    """A list of at least `least` entries, each held as `items`."""

    items: "Holds"
    least: int = 0


@dataclass(frozen=True)
class Map:
    """An object keyed by names, each value held as `values`, or as its name's entry there; a name the entry
    lacks is no registered one, which `_tokens` refuses, and its value is not checked."""

    values: "Holds | dict[str, Holds]"


Holds = Value | Object | List | Map

# `yes`: required. `no`: optional. `one`: exactly one of the place's members so marked. `rule`: present or
# absent as a rule beside the table says (item 8's `sampling`, item 7's `engine`, a waiver's `condition`, an
# acceptance's location), which that rule's function judges and `_shape` does not.
Required = Literal["yes", "no", "one", "rule"]


@dataclass(frozen=True)
class Member:
    name: str
    required: Required
    holds: Holds


def _not_below_zero(value: JsonValue) -> str | None:
    return "below zero" if isinstance(value, float) and value < 0 else None


def _whole_not_below_zero(value: JsonValue) -> str | None:
    whole = isinstance(value, float) and value >= 0 and value.is_integer()
    return None if whole or not isinstance(value, float) else "not a whole number at least zero"


def _whole(value: JsonValue) -> str | None:
    return "not a whole number" if isinstance(value, float) and not value.is_integer() else None


def _range(value: JsonValue) -> str | None:
    if not (isinstance(value, list) and len(value) == 2 and all(isinstance(end, float) for end in value)):
        return "not a range [lo, hi] of two numbers"
    return "a range whose lo is above its hi" if cast(float, value[0]) > cast(float, value[1]) else None


def _one_character(value: JsonValue) -> str | None:
    return "the empty string" if value == "" else None


def _uberon(value: JsonValue) -> str | None:
    unmatched = isinstance(value, str) and not re.fullmatch(r"UBERON:[0-9]+", value)
    return "not an UBERON identifier" if unmatched else None


def _in_unit_interval(value: JsonValue) -> str | None:
    return "outside (0, 1]" if isinstance(value, float) and not 0 < value <= 1 else None


def _difference_value(value: JsonValue) -> str | None:
    return None if value == "any" or isinstance(value, dict) else 'neither a fact, a status object nor "any"'


def _level_or_status(value: JsonValue) -> str | None:
    return None if isinstance(value, str | dict) else "neither a level nor a status object"


_STRING = Value("string")
_NUMBER = Value("number")
_ANY = Value("any")
_TEXT = Value("string")  # a `reason` or `basis`: `_reasons` holds it to at least one character
_NAME = Value("string")  # a token or a registered name: `_tokens` holds it to its list
_RANGE = Value("any", _range)
_REFERENCE = Object("material reference")

# A target's facts: each its shape in `provenance.md` section 6.2 without `basis`, its text members (`label`,
# `text`) optional (the `target` row). An accepted difference's `value` is the same with an optional `basis`,
# and `inferred_from` beside it where the fact's row leaves the basis open.
_FACTS: dict[str, tuple[Member, ...]] = {
    "species": (Member("ncbi_taxon", "yes", Value("number", _whole)), Member("label", "no", _STRING)),
    "anatomical_site": (Member("uberon", "yes", Value("string", _uberon)), Member("label", "no", _STRING)),
    "tissue_state": (Member("token", "yes", _NAME),),
    "disease_and_treatment_state": (Member("token", "yes", _NAME), Member("text", "no", _STRING)),
    "preparation": (Member("text", "no", _STRING),),
    "preservation": (Member("token", "yes", _NAME), Member("text", "no", _STRING)),
    "post_mortem_interval": (Member("value", "yes", _NUMBER), Member("unit", "yes", _NAME)),
    "donor_age": (
        Member("value", "one", _NUMBER),
        Member("range", "one", _RANGE),
        Member("unit", "yes", _NAME),
    ),
    "mimics": (Member("text", "no", _STRING),),
    "supply_form": (Member("token", "yes", _NAME),),
    "lot": (Member("text", "no", _STRING),),
}


def _difference(fact: str) -> tuple[Member, ...]:
    inferred = () if "basis" in VOCABULARY.facts[fact].fixed else (Member("inferred_from", "no", _STRING),)
    return (*_FACTS[fact], Member("basis", "no", _NAME), *inferred)


def _kind(
    *own: Member, location: Required | None = "rule", field: bool = True, basis: bool = False
) -> tuple[Member, ...]:
    """An acceptance kind's members: those the table's acceptance rows give every acceptance, `acceptance`,
    `reason`, the location as section 4.1's Location column gives the kind (`rule`: needed, `_locations`'
    judgement; `no`: optional; None: named in `own`, or none) and `field` but where the kind names none; and
    its own. `basis` is a member of an extrapolation, a nominal and a distribution alone (maintainer,
    2026-10-24)."""
    places = (("record", _REFERENCE), ("region", _STRING), ("interval", _ANY))
    located = () if location is None else tuple(Member(name, location, holds) for name, holds in places)
    return (
        Member("acceptance", "yes", _NAME),
        *located,
        *((Member("field", "yes", _NAME),) if field else ()),
        *own,
        Member("reason", "yes", _TEXT),
        *((Member("basis", "yes", _TEXT),) if basis else ()),
    )


_CONDITIONS = VOCABULARY.conditions
_NUMERIC = tuple(name for name, spec in _CONDITIONS.items() if spec.shape == "numeric")
_OPERATING = Map(dict.fromkeys(_NUMERIC, Object("operating condition")))
_IMPLIED: dict[str, Holds] = {
    name: Object("implied numeric" if spec.shape == "numeric" else "implied token")
    for name, spec in _CONDITIONS.items()
}

SHAPE: dict[str, tuple[Member, ...]] = {
    "declaration": (
        Member("consumer", "yes", Object("consumer")),
        Member("operating_conditions", "yes", _OPERATING),
        Member("sampling", "rule", Object("sampling")),
        Member("models", "yes", List(Object("model entry"), least=1)),
    ),
    "model entry": (
        Member("model", "yes", Object("model")),
        Member("model_configuration_hash", "yes", _STRING),
        Member("region_conditions", "no", Map(_OPERATING)),
        Member("checked_over", "yes", Object("checked over")),
        Member("target", "yes", Map({name: Object(f"fact {name}") for name in _FACTS})),
        Member("reads", "yes", List(_NAME, least=1)),
        Member("consumer_parameters", "yes", List(_STRING)),
        Member("requirements", "no", List(Object("requirement"))),
        Member("families", "yes", Map(_STRING)),
        Member("mixing", "no", Object("mixing")),
        Member("combinations", "yes", List(List(_NAME))),
        Member("acceptances", "no", List(Object("acceptance"))),
        Member("chains", "yes", List(Object("chain"))),
        Member("trainable", "no", List(Object("trainable entry"))),
        Member("precision", "rule", _NAME),
        Member("engine", "rule", Object("engine")),
    ),
    "requirement": (
        Member("field", "yes", _NAME),
        Member("want", "yes", _NAME),
        Member("conditions", "no", Map(dict.fromkeys(_CONDITIONS, Object("requirement condition")))),
        Member("label", "no", _NAME),
        Member("review", "no", _NAME),
        Member("represents", "no", _NAME),
        Member("population_level", "rule", Object("population level")),
    ),
    "requirement condition": (
        Member("tolerance", "one", Object("tolerance")),
        Member("accept", "one", List(_NAME, least=1)),
        Member("reason", "yes", _TEXT),
        Member("consequence", "no", _STRING),
    ),
    "trainable entry": (
        Member("field", "yes", _NAME),
        Member("record", "one", _REFERENCE),
        Member("region", "one", _STRING),
        Member("interval", "one", _ANY),
    ),
    "material reference": (
        Member("id", "yes", _STRING),
        Member("version", "yes", _STRING),
        Member("content_hash", "yes", _STRING),
    ),
    # The objects the Holds cells give.
    "consumer": (Member("name", "yes", _STRING), Member("version", "yes", _STRING)),
    "operating condition": (
        Member("value", "one", _NUMBER),
        Member("range", "one", _RANGE),
        Member("unit", "yes", _NAME),
    ),
    "sampling": (
        Member("min_acceptance", "yes", Value("number", _in_unit_interval)),
        Member("reason", "yes", _TEXT),
        Member("independence", "yes", List(Object("independence entry"))),
    ),
    "independence entry": (
        Member("fields", "yes", List(_ANY)),
        Member("reason", "yes", _TEXT),
        Member("basis", "yes", _TEXT),
    ),
    "model": (Member("name", "yes", _STRING), Member("version", "yes", _STRING)),
    "checked over": (
        Member("domain", "one", _STRING),
        Member("path", "one", _STRING),
        Member("records", "one", List(_REFERENCE, least=1)),
    ),
    "population level": (
        Member("level", "yes", _NAME),
        Member("within", "one", Value("any", _level_or_status)),
        Member("balanced_over", "one", _NAME),
    ),
    "tolerance": (Member("value", "yes", Value("number", _not_below_zero)), Member("unit", "yes", _NAME)),
    "mixing": (
        Member("fraction_sum_tolerance", "yes", Value("number", _not_below_zero)),
        Member("rules", "yes", Map(_NAME)),
    ),
    "chain": (
        Member("from", "yes", Object("chain end")),
        Member("event", "yes", _STRING),
        Member("to", "yes", Object("chain end")),
        Member("state_mapping", "yes", Map(_STRING)),
    ),
    "chain end": (Member("family", "yes", _STRING), Member("record", "yes", _REFERENCE)),
    "engine": (
        Member("crosswalk", "yes", Object("crosswalk pin")),
        Member("values", "yes", Map(Object("engine value"))),
        Member("region_values", "no", Map(Map(Object("engine value")))),
    ),
    "crosswalk pin": (
        Member("id", "yes", _STRING),
        Member("version", "yes", _STRING),
        Member("sha256", "yes", _STRING),
    ),
    "engine value": (
        Member("value", "yes", _NUMBER),
        Member("unit", "no", _STRING),
        Member("reason", "yes", _TEXT),
        Member("basis", "yes", _TEXT),
    ),
    # Each kind of acceptance (section 4.1), its members by `_kind`.
    "pick": _kind(
        Member("record", "yes", _REFERENCE),
        Member("region", "rule", _STRING),
        Member("interval", "rule", _ANY),
        Member("index", "yes", Value("number", _whole_not_below_zero)),
        location=None,
    ),
    "waiver": _kind(
        Member("code", "yes", _NAME), Member("condition", "rule", _NAME), Member("label", "no", _NAME)
    ),
    "implied_condition": _kind(
        Member("fact", "yes", _NAME), Member("token", "yes", _NAME), Member("implies", "yes", Map(_IMPLIED))
    ),
    "accepted_difference": _kind(
        Member("section", "yes", _NAME),
        Member("fact", "yes", _NAME),
        Member("value", "yes", Value("any", _difference_value)),
        location="no",
        field=False,
    ),
    "extrapolation": _kind(
        Member("method", "yes", _NAME), Member("law", "yes", Value("string", _one_character)), basis=True
    ),
    "nominal": _kind(Member("value", "one", _NUMBER), Member("params", "one", _ANY), basis=True),
    "distribution": _kind(
        Member("distribution", "yes", _NAME),
        Member("distribution_parameters", "yes", Map(_NUMBER)),
        Member("space", "yes", _NAME),
        basis=True,
    ),
    "overlay": _kind(Member("overlay", "yes", _REFERENCE), location=None),
    "overlay_scope": _kind(
        Member("overlay", "yes", _REFERENCE),
        Member("accepts", "yes", List(_NAME, least=1)),
        location=None,
        field=False,
    ),
    # An implied condition's value (section 4.1's row): a record condition's shape of that condition's kind,
    # without `plus_minus` or `set_or_measured`, never a status object; a `basis` there is ignored.
    "implied numeric": (
        Member("value", "one", _NUMBER),
        Member("range", "one", _RANGE),
        Member("unit", "yes", _NAME),
        Member("basis", "no", _ANY),
    ),
    "implied token": (Member("token", "yes", _NAME), Member("basis", "no", _ANY)),
    # An accepted difference's `value` as a status object (`provenance.md` section 1).
    "status object": (Member("status", "yes", _NAME), Member("reason", "no", _STRING)),
    **{f"fact {name}": members for name, members in _FACTS.items()},
    **{f"difference {name}": _difference(name) for name in _FACTS},
}

KINDS: tuple[str, ...] = VOCABULARY.acceptance_kinds
# What an acceptance of no known kind may hold: the members some kind names, none of them required but its
# kind, since which of them it needs depends on that.
_ANY_KIND: dict[str, Member] = {
    member.name: Member(member.name, "yes" if member.name == "acceptance" else "rule", member.holds)
    for kind in KINDS
    for member in SHAPE[kind]
}
_LOCATED_KINDS = tuple(kind for kind in KINDS if any(member.name == "region" for member in SHAPE[kind]))
_NEEDS_LOCATION = ("pick", "waiver", "implied_condition", "extrapolation", "nominal", "distribution")
_NEEDS_BASIS = ("extrapolation", "nominal", "distribution")

# The tokens of the members whose lists are not the vocabulary's registered names (fields, conditions, facts,
# sections, labels and their rows' tokens, judged where they are read), by place and member.
TOKENS: dict[tuple[str, str], tuple[str, ...]] = {
    ("requirement", "want"): get_args(Want),
    ("requirement", "review"): ("reviewed",),
    ("requirement", "represents"): VOCABULARY.token_lists["represents"],
    ("population level", "level"): VOCABULARY.token_lists["level"],
    ("population level", "balanced_over"): VOCABULARY.token_lists["level"],
    ("model entry", "precision"): ("binary32", "binary64"),
    ("mixing", "rules"): ("identity", "arithmetic", "harmonic", "wood", "refuse"),
    ("waiver", "code"): tuple(VOCABULARY.reasons),
    ("extrapolation", "method"): VOCABULARY.token_lists["extrapolation_method"],
    ("distribution", "distribution"): VOCABULARY.token_lists["distribution"],
    ("distribution", "space"): ("identity", "log"),
    ("overlay_scope", "accepts"): ("consumer", "model", "configuration"),
    ("status object", "status"): STATUS_TOKENS,
}
# A declared distribution's parameters by its token, named as `uncertainty.md` section 4 names them.
DISTRIBUTION_PARAMETERS: dict[str, tuple[str, ...]] = {
    "normal": ("mean", "sd"),
    "lognormal": ("mean", "sd"),
    "uniform": ("lower", "upper"),
    "triangular": ("lower", "mode", "upper"),
    "student_t": ("location", "scale", "dof"),
    "beta": ("lower", "upper", "p", "q"),
}
# The codes that name a condition, for a waiver's `condition`: those whose reasons always carry one.
CONDITION_CODES = (
    *(code for code in VOCABULARY.reasons if code.startswith("condition_")),
    "outside_range",
    "at_edge",
    "range_unstated",
)


# A fault, and the refusals the build reports.


@dataclass(frozen=True)
class Finding:
    """A fault one rule finds: its case; the pointer of the member at fault, or of the object that should hold
    a missing member; its words; and `aspect`, the missing member, or the place's exclusive alternatives, at
    fault (None for the member at fault itself). A fault is its pointer and aspect, whichever rules name it.
    """

    case: str
    pointer: str
    detail: str = dataclasses.field(default="", compare=False)
    aspect: str | None = None


def _precedence(found: list[Finding]) -> tuple[BuildRefusal, ...]:
    """One refusal per fault, of the case first in `ORDER`, and those of one case and pointer merged into one,
    their words joined (section 1, the refusal paragraph)."""
    faults: dict[tuple[str, str | None], list[Finding]] = {}
    for finding in found:
        faults.setdefault((finding.pointer, finding.aspect), []).append(finding)
    kept: dict[tuple[str, str], list[str]] = {}
    for findings in faults.values():
        first = min(ORDER.index(finding.case) for finding in findings)
        for finding in (finding for finding in findings if ORDER.index(finding.case) == first):
            details = kept.setdefault((finding.case, finding.pointer), [])
            if finding.detail and finding.detail not in details:
                details.append(finding.detail)
    return tuple(BuildRefusal(case, at, "; ".join(details) or None) for (case, at), details in kept.items())


def _join(pointer: str, name: str | int) -> str:
    """`pointer` and one more reference token, escaped by RFC 6901 (`~` as `~0`, `/` as `~1`)."""
    return f"{pointer}/{str(name).replace('~', '~0').replace('/', '~1')}"


def _not_listed(value: str, allowed: Collection[str], what: str) -> str:
    near = next((name for name in sorted(allowed) if one_slip(value, name) is not None), None)
    return f"{value!r} is not {what}" + ("" if near is None else f", one slip from {near!r}")


# The walk: every object of the declaration, at its place.


@dataclass(frozen=True)
class Visit:
    """An object at a place of `SHAPE`, its pointer, and the name the nearest map keys it by (a condition, a
    fact, a region), if any."""

    place: str
    value: JsonObject
    pointer: str
    key: str | None


def _members_of(place: str) -> dict[str, Member]:
    return _ANY_KIND if place == "acceptance" else {member.name: member for member in SHAPE[place]}


def _places(declaration: JsonObject) -> Iterator[Visit]:
    """Each object of the declaration at its place, the declaration's first. An object is reached through a
    member its place names, holding the JSON type the member holds: never through an unknown member, nor one
    of another type, inside which nothing is checked (section 1)."""
    yield from _visit("declaration", declaration, "", None)


def _visit(place: str, value: JsonObject, pointer: str, key: str | None) -> Iterator[Visit]:
    if place == "acceptance" and value.get("acceptance") in KINDS:
        place = cast(str, value["acceptance"])
    yield Visit(place, value, pointer, key)
    members = _members_of(place)
    for name, held in value.items():
        if name in members:
            yield from _inside(members[name].holds, held, _join(pointer, name), key)
    difference, fact = value.get("value"), value.get("fact")
    if place == "accepted_difference" and isinstance(difference, dict):
        if _status_object(difference):
            yield from _visit("status object", difference, f"{pointer}/value", key)
        elif isinstance(fact, str) and fact in _FACTS:
            yield from _visit(f"difference {fact}", difference, f"{pointer}/value", fact)


def _inside(holds: Holds, value: JsonValue, pointer: str, key: str | None) -> Iterator[Visit]:
    if isinstance(holds, Object) and isinstance(value, dict):
        yield from _visit(holds.place, value, pointer, key)
    elif isinstance(holds, List) and isinstance(value, list):
        for index, item in enumerate(value):
            yield from _inside(holds.items, item, _join(pointer, index), key)
    elif isinstance(holds, Map) and isinstance(value, dict):
        for name, item in value.items():
            held = holds.values.get(name) if isinstance(holds.values, dict) else holds.values
            if held is not None:
                yield from _inside(held, item, _join(pointer, name), name)


def _status_object(value: JsonObject) -> bool:
    """An object holding `status`, and beside it `reason` at most (`provenance.md` section 1)."""
    return "status" in value and set(value) <= {"status", "reason"}


def _entries(value: JsonValue, member: str) -> Iterator[tuple[int, JsonObject]]:
    """The entries of `value[member]` that are objects, with their indexes: those a rule can judge."""
    entries = value.get(member) if isinstance(value, dict) else None
    if isinstance(entries, list):
        for index, entry in enumerate(entries):
            if isinstance(entry, dict):
                yield index, entry


# The rules.


def _shape(declaration: JsonObject) -> list[Finding]:
    """BC-048: at each place, a member it does not name, a member one slip from a named one included; a member
    it requires and lacks; none or two of its exclusive alternatives; and each member's value against what the
    member holds (`_holds`)."""
    found: list[Finding] = []
    for visit in _places(declaration):
        members, at = _members_of(visit.place), visit.pointer
        for name, held in visit.value.items():
            if name in members:
                found += _holds(members[name].holds, held, _join(at, name))
            else:
                found.append(Finding("BC-048", _join(at, name), _not_listed(name, members, "a member here")))
        for name, member in members.items():
            if member.required == "yes" and name not in visit.value:
                found.append(Finding("BC-048", at, f"{name!r} missing", name))
        alternatives = [name for name, member in members.items() if member.required == "one"]
        given = [name for name in alternatives if name in visit.value]
        if alternatives and len(given) != 1:
            found.append(Finding("BC-048", at, f"{len(given)} of {alternatives}", "|".join(alternatives)))
    return found


def _holds(holds: Holds, value: JsonValue, pointer: str) -> list[Finding]:
    """Where `value` is not what `holds` gives: its JSON type, its length, its constraint, and the same of
    each entry and map value that is no object (an object's members are its own visit's)."""
    if isinstance(holds, Value):
        if (holds.type == "string" and not isinstance(value, str)) or (
            holds.type == "number" and not isinstance(value, float)
        ):
            return [Finding("BC-048", pointer, f"not a {holds.type}")]
        problem = None if holds.constraint is None else holds.constraint(value)
        return [] if problem is None else [Finding("BC-048", pointer, problem)]
    if isinstance(holds, Object) or (isinstance(holds, Map) and not isinstance(value, dict)):
        return [] if isinstance(value, dict) else [Finding("BC-048", pointer, "not an object")]
    if isinstance(holds, List):
        if not isinstance(value, list):
            return [Finding("BC-048", pointer, "not a list")]
        found = [Finding("BC-048", pointer, f"fewer than {holds.least}")] if len(value) < holds.least else []
        for index, item in enumerate(value):
            found += _holds(holds.items, item, _join(pointer, index))
        return found
    entries: list[Finding] = []
    for name, item in cast(JsonObject, value).items():
        held = holds.values.get(name) if isinstance(holds.values, dict) else holds.values
        entries += [] if held is None else _holds(held, item, _join(pointer, name))
    return entries


def _tokens(declaration: JsonObject) -> list[Finding]:
    """BC-048: every token, unit and registered name against its list, compared code point for code point, so
    a slip of one, another member's token and one in another case are refused: the fields, conditions, facts,
    sections and labels the build's version registers, each numeric condition's registered unit, and the
    tokens of each member's row."""
    found: list[Finding] = []

    def check(value: JsonValue, at: str, allowed: Collection[str], what: str) -> None:
        if isinstance(value, str) and value not in allowed:
            found.append(Finding("BC-048", at, _not_listed(value, allowed, what)))

    def each(value: JsonValue, at: str, allowed: Collection[str], what: str, *, keys: bool = False) -> None:
        """Each entry of a list, each value of an object, or with `keys` each name of an object."""
        if isinstance(value, list):
            for index, item in enumerate(value):
                check(item, _join(at, index), allowed, what)
        for name, item in _items(value):
            check(name if keys else item, _join(at, name), allowed, what)

    fields, facts, levels = VOCABULARY.fields, VOCABULARY.facts, VOCABULARY.token_lists["level"]
    for visit in _places(declaration):
        value, at, place, key = visit.value, visit.pointer, visit.place, visit.key
        for (where, member), allowed in TOKENS.items():
            if where == place and member in value:
                each(value[member], f"{at}/{member}", allowed, f"a {member} token")
                check(value[member], f"{at}/{member}", allowed, f"a {member} token")
        if place == "declaration":
            each(
                value.get("operating_conditions"),
                f"{at}/operating_conditions",
                _NUMERIC,
                "numeric",
                keys=True,
            )
        elif place == "model entry":
            each(value.get("reads"), f"{at}/reads", fields, "a registered field")
            for region, conditions in _items(value.get("region_conditions")):
                each(conditions, _join(f"{at}/region_conditions", region), _NUMERIC, "numeric", keys=True)
            for index, combined in enumerate(_list(value.get("combinations"))):
                each(combined, f"{at}/combinations/{index}", fields, "a registered field")
            sets = [name for name, spec in fields.items() if "parameter_set" in spec.forms]
            each(value.get("families"), f"{at}/families", sets, "a parameter-set field", keys=True)
            each(value.get("target"), f"{at}/target", facts, "a specimen fact", keys=True)
        elif place == "mixing":
            each(value.get("rules"), f"{at}/rules", fields, "a registered field", keys=True)
        elif place in ("requirement", "trainable entry", "acceptance") or place in KINDS:
            check(value.get("field"), f"{at}/field", fields, "a registered field")
        if place == "requirement":
            each(
                value.get("conditions"), f"{at}/conditions", _CONDITIONS, "a registered condition", keys=True
            )
            if "label" in value:
                check(value["label"], f"{at}/label", _labels_of(value.get("field")), "a label of its field")
        elif place == "requirement condition" and key in _CONDITIONS:
            spec, wrong = _CONDITIONS[key], "accept" if _CONDITIONS[key].shape == "numeric" else "tolerance"
            if wrong in value:
                found.append(Finding("BC-048", f"{at}/{wrong}", f"no {wrong} for {key}"))
            if spec.shape == "token":
                each(value.get("accept"), f"{at}/accept", spec.tokens, f"a token of {key}")
        elif place in ("tolerance", "operating condition", "implied numeric") and key in _NUMERIC:
            check(value.get("unit"), f"{at}/unit", (cast(str, _CONDITIONS[key].unit),), f"{key}'s unit")
        elif place == "implied token" and key in _CONDITIONS:
            check(value.get("token"), f"{at}/token", _CONDITIONS[key].tokens, f"a token of {key}")
        elif place == "population level":
            within = value.get("within")
            check(within, f"{at}/within", levels, "a level")
            if isinstance(within, dict) and not (_status_object(within) and within.get("status") == "none"):
                found.append(Finding("BC-048", f"{at}/within", "a status object other than none"))
        elif place == "acceptance" and "acceptance" in value:
            check(value["acceptance"], f"{at}/acceptance", KINDS, "a kind of acceptance")
        elif place in KINDS:
            found += _kind_tokens(place, value, at)
        elif place.startswith(("fact ", "difference ")):
            fact = facts[place.partition(" ")[2]]
            if fact.tokens:
                check(value.get("token"), f"{at}/token", fact.tokens, f"a token of {fact.name}")
            for member, fixed in fact.fixed.items():
                if member in _members_of(place):
                    check(value.get(member), f"{at}/{member}", (fixed,), f"{fact.name}'s {member}")
            if place.startswith("difference ") and "basis" not in fact.fixed:
                check(value.get("basis"), f"{at}/basis", VOCABULARY.token_lists["basis"], "a basis")
    return found


def _kind_tokens(kind: str, value: JsonObject, at: str) -> list[Finding]:
    """The registered names and conditional members of an acceptance of a known kind."""
    found: list[Finding] = []

    def check(member: str, allowed: Collection[str], what: str) -> None:
        held = value.get(member)
        if isinstance(held, str) and held not in allowed:
            found.append(Finding("BC-048", f"{at}/{member}", _not_listed(held, allowed, what)))

    if kind == "waiver":
        code = value.get("code")
        check("condition", _CONDITIONS, "a registered condition")
        if "label" in value:
            check("label", _labels_of(value.get("field")), "a label of its field")
        # A code names a condition where its reasons always carry one, and one that is no reason names none.
        if isinstance(code, str) and code in CONDITION_CODES and "condition" not in value:
            found.append(Finding("BC-048", at, f"a waiver of {code} names its condition", "condition"))
        elif isinstance(code, str) and code not in CONDITION_CODES and "condition" in value:
            found.append(Finding("BC-048", f"{at}/condition", f"{code!r} names no condition"))
    elif kind == "implied_condition":
        with_token = [name for name, spec in VOCABULARY.facts.items() if spec.tokens]
        check("fact", with_token, "a specimen fact with a token")
        fact = value.get("fact")
        if isinstance(fact, str) and fact in with_token:
            check("token", VOCABULARY.facts[fact].tokens, f"a token of {fact}")
        for name, _ in _items(value.get("implies")):
            if name not in _CONDITIONS:
                found.append(
                    Finding("BC-048", _join(f"{at}/implies", name), f"{name!r} is no registered condition")
                )
    elif kind == "accepted_difference":
        check("section", VOCABULARY.sections, "a registered section")
        check("fact", VOCABULARY.facts, "a specimen fact")
    elif kind == "nominal" and "params" in value:
        spec = (
            VOCABULARY.fields.get(cast(str, value["field"])) if isinstance(value.get("field"), str) else None
        )
        if spec is None or "parameter_set" not in spec.forms:
            found.append(Finding("BC-048", f"{at}/params", "params, for a field with no parameter set"))
    elif kind == "distribution":
        token, parameters = value.get("distribution"), value.get("distribution_parameters")
        if isinstance(token, str) and token in DISTRIBUTION_PARAMETERS and isinstance(parameters, dict):
            if sorted(parameters) != sorted(DISTRIBUTION_PARAMETERS[token]):
                named = ", ".join(DISTRIBUTION_PARAMETERS[token])
                found.append(Finding("BC-048", f"{at}/distribution_parameters", f"{token} takes {named}"))
    return found


def _labels_of(field: JsonValue) -> tuple[str, ...]:
    """The labels a field's requirement or waiver may name: the one its row registers (none, if it names
    none), or any registered label, for a field the build does not register, which is its own fault."""
    if isinstance(field, str) and field in VOCABULARY.fields:
        label = VOCABULARY.fields[field].label
        return () if label is None else (label,)
    return VOCABULARY.token_lists["label"]


def _names(declaration: JsonObject) -> list[Finding]:
    """BC-048: a name given twice where the table allows it once, at the later entry, whole: two models of one
    `name`, a record listed twice in one `checked_over`, a field twice in `reads`, two requirements for one
    field, two `trainable` entries for one field at one location; an `accepts` token twice; a requirement, a
    `trainable` entry or a combination naming a field its model does not list in `reads`; a combination of
    fewer than two fields, or of fields of one section; a `trainable` entry at a record its model is not
    checked over. Where a model is checked over a domain or a path, which needs the scene, a `trainable`
    entry's location is not judged here, nor one at a region or an interval: item 12 refuses each."""
    found: list[Finding] = []
    models: set[str] = set()
    for index, model in _entries(declaration, "models"):
        at, name = f"/models/{index}", model.get("model")
        if isinstance(name, dict) and isinstance(name.get("name"), str):
            found += _twice(cast(str, name["name"]), models, at, "a second model of this name")
        records = _checked_records(model)
        seen: set[MaterialRef] = set()
        for position, reference in enumerate(records or []):
            if reference is not None:
                found += _twice(reference, seen, f"{at}/checked_over/records/{position}", "listed twice")
        read: set[str] | None = None if not isinstance(model.get("reads"), list) else set()
        for position, field in enumerate(_list(model.get("reads"))):
            if isinstance(field, str) and read is not None:
                found += _twice(field, read, f"{at}/reads/{position}", "read twice")
        required: set[str] = set()
        for position, requirement in _entries(model, "requirements"):
            here, field = f"{at}/requirements/{position}", requirement.get("field")
            if isinstance(field, str):
                found += _twice(field, required, here, "a second requirement for this field")
                found += _unread(field, read, f"{here}/field")
        for position, combined in enumerate(_list(model.get("combinations"))):
            here, fields = (
                f"{at}/combinations/{position}",
                [field for field in _list(combined) if isinstance(field, str)],
            )
            sections = {field.partition(".")[0] for field in fields}
            if isinstance(combined, list) and (
                len(combined) < 2 or (len(fields) == len(combined) and len(sections) < 2)
            ):
                found.append(Finding("BC-048", here, "not two or more fields of different sections"))
            for number, field in enumerate(_list(combined)):
                if isinstance(field, str):
                    found += _unread(field, read, f"{here}/{number}")
        trainable: set[str] = set()
        for position, entry in _entries(model, "trainable"):
            here, field = f"{at}/trainable/{position}", entry.get("field")
            locations = [name for name in ("record", "region", "interval") if name in entry]
            if not isinstance(field, str):
                continue
            found += _unread(field, read, f"{here}/field")
            if len(locations) == 1:
                location = json.dumps([field, locations[0], entry[locations[0]]], sort_keys=True)
                found += _twice(location, trainable, here, "a second trainable entry for this field there")
            reference = _reference(entry.get("record")) if locations == ["record"] else None
            if reference is not None and records is not None and reference not in records:
                found.append(Finding("BC-048", f"{here}/record", "a record its model is not checked over"))
        for position, acceptance in _entries(model, "acceptances"):
            accepts = [token for token in _list(acceptance.get("accepts")) if isinstance(token, str)]
            if acceptance.get("acceptance") == "overlay_scope" and len(set(accepts)) < len(accepts):
                found.append(Finding("BC-048", f"{at}/acceptances/{position}/accepts", "a token twice"))
    return found


def _twice(name: _Name, seen: set[_Name], at: str, detail: str) -> list[Finding]:
    """A finding at `at` where `name` is already in `seen`, which it then joins."""
    given = name in seen
    seen.add(name)
    return [Finding("BC-048", at, detail)] if given else []


def _unread(field: str, read: set[str] | None, at: str) -> list[Finding]:
    return (
        [Finding("BC-048", at, f"{field} is not in reads")] if read is not None and field not in read else []
    )


def _reasons(declaration: JsonObject) -> list[Finding]:
    """BC-004: a tolerance or accept list without `reason` (item 3). BC-005: an acceptance without `reason`,
    and an extrapolation, a nominal or a distribution without `basis` (item 4). A `reason` or `basis` that is
    not a string of at least one character, wherever it is, breaks its row's Holds: BC-048's, at that member.
    """
    found: list[Finding] = []
    for visit in _places(declaration):
        value, at, place = visit.value, visit.pointer, visit.place
        if place == "requirement condition" and "reason" not in value:
            found.append(Finding("BC-004", at, "a tolerance or accept list without its reason", "reason"))
        if (place in KINDS or place == "acceptance") and "reason" not in value:
            found.append(Finding("BC-005", at, "an acceptance without its reason", "reason"))
        if place in _NEEDS_BASIS and "basis" not in value:
            found.append(Finding("BC-005", at, f"an {place} without its basis", "basis"))
        for member in ("reason", "basis"):
            named, held = _members_of(place).get(member), value.get(member)
            if (
                named is not None
                and named.holds is _TEXT
                and member in value
                and not (isinstance(held, str) and held)
            ):
                found.append(Finding("BC-048", f"{at}/{member}", "not a string of at least one character"))
    return found


def _locations(declaration: JsonObject) -> list[Finding]:
    """BC-037: an acceptance whose kind needs a location and names none (section 4.1); a pick's is its
    record."""
    found: list[Finding] = []
    for visit in _places(declaration):
        if visit.place == "pick" and "record" not in visit.value:
            found.append(Finding("BC-037", visit.pointer, "a pick naming no record", "record"))
        elif visit.place in _NEEDS_LOCATION and not {"record", "region", "interval"} & visit.value.keys():
            found.append(Finding("BC-037", visit.pointer, f"a {visit.place} naming no location", "location"))
    return found


def _labels(declaration: JsonObject) -> list[Finding]:
    """BC-050: a waiver naming a `label`, unless the requirement for its field names that label and holds
    `review: "reviewed"` (section 4.1 item 4), at the waiver's `label`."""
    found: list[Finding] = []
    for index, model in _entries(declaration, "models"):
        requirements: dict[str, JsonObject] = {}
        for _, requirement in _entries(model, "requirements"):
            if isinstance(requirement.get("field"), str):
                requirements.setdefault(cast(str, requirement["field"]), requirement)
        for position, waiver in _entries(model, "acceptances"):
            if waiver.get("acceptance") != "waiver" or "label" not in waiver:
                continue
            field = waiver.get("field")
            requirement = requirements.get(field, {}) if isinstance(field, str) else {}
            if requirement.get("label") != waiver["label"] or requirement.get("review") != "reviewed":
                detail = "a waiver resting on a label its requirement does not name, reviewed"
                found.append(Finding("BC-050", f"/models/{index}/acceptances/{position}/label", detail))
    return found


def _suites(declaration: JsonObject, claims: Collection[Suite]) -> list[Finding]:
    """Items 7 and 8 and the `population_level` rule, then item 12, member by member (section 1).

    - BC-040, item 7: a model with `engine` checked over a path or records; one whose requirement wants
      anything but `value`; a declared engine value without `reason` or `basis`; a pinned crosswalk not
      passed, as every crosswalk is to this version's build, which takes none.
    - BC-044, item 8: a requirement samples (holds `represents`), and `sampling.min_acceptance` is missing or
      not a number in (0, 1].
    - BC-043, the `population_level` rule: `represents` `population` without `population_level`, and a
      `population_level` beside another `represents` (maintainer, 2026-10-24).
    - BC-051, item 12: what a suite the build does not claim checks, at the member that needs it, or at the
      acceptance or `trainable` entry itself; but no model's `engine` that item 7 refuses, and no member of a
      requirement over which item 8 or the `population_level` rule refuses the declaration.
    """
    found: list[Finding] = []
    item7: set[int] = set()
    for index, model in _entries(declaration, "models"):
        if "engine" not in model:
            continue
        at, before = f"/models/{index}", len(found)
        for name in ("path", "records"):
            if name in _object(model.get("checked_over")):
                found.append(Finding("BC-040", f"{at}/checked_over/{name}", f"an engine model over a {name}"))
        for position, requirement in _entries(model, "requirements"):
            want = requirement.get("want")
            if isinstance(want, str) and want != "value":
                found.append(
                    Finding("BC-040", f"{at}/requirements/{position}/want", "an engine reads values")
                )
        engine = _object(model.get("engine"))
        if "crosswalk" in engine:
            found.append(
                Finding("BC-040", f"{at}/engine/crosswalk", "a pinned crosswalk not passed to the build")
            )
        for here, value in _engine_values(engine, f"{at}/engine"):
            for member in ("reason", "basis"):
                if member not in value:
                    found.append(Finding("BC-040", here, f"an engine value without its {member}", member))
        if len(found) > before:
            item7.add(index)
    sampled = [
        (f"/models/{index}/requirements/{position}", requirement)
        for index, model in _entries(declaration, "models")
        for position, requirement in _entries(model, "requirements")
        if "represents" in requirement
    ]
    block, item8 = declaration.get("sampling"), len(found)
    if sampled and "sampling" not in declaration:
        found.append(Finding("BC-044", "", "a requirement samples, and no sampling is declared", "sampling"))
    elif sampled and not isinstance(block, dict):
        found.append(Finding("BC-044", "/sampling", "a requirement samples, and sampling is no object"))
    elif sampled and "min_acceptance" not in cast(JsonObject, block):
        found.append(
            Finding("BC-044", "/sampling", "a requirement samples, with no min_acceptance", "min_acceptance")
        )
    elif sampled and _in_unit_interval(cast(JsonObject, block)["min_acceptance"]) is not None:
        found.append(Finding("BC-044", "/sampling/min_acceptance", "a min_acceptance outside (0, 1]"))
    elif sampled and not isinstance(cast(JsonObject, block)["min_acceptance"], float):
        found.append(Finding("BC-044", "/sampling/min_acceptance", "a min_acceptance that is no number"))
    spared: set[str] = {at for at, _ in sampled} if len(found) > item8 else set()
    for at, requirement in sampled:
        represents = requirement["represents"]
        if represents == "population" and "population_level" not in requirement:
            found.append(
                Finding("BC-043", at, "a population requirement without its level", "population_level")
            )
            spared.add(at)
        elif represents in TOKENS["requirement", "represents"] and "population_level" in requirement:
            if represents != "population":
                found.append(
                    Finding("BC-043", f"{at}/population_level", f"a population level beside {represents}")
                )
                spared.add(at)
    if "scene_documents" not in claims:
        found += _scene_members(declaration)
    for index, model in _entries(declaration, "models"):
        if "usd_read" not in claims and "engine" in model and index not in item7:
            found.append(Finding("BC-051", f"/models/{index}/engine", "an engine model, without USD read"))
    if "sampling" in claims:
        return found
    if "sampling" in declaration:
        found.append(Finding("BC-051", "/sampling", "sampling, without the sampling suite"))
    for index, model in _entries(declaration, "models"):
        for position, requirement in _entries(model, "requirements"):
            at = f"/models/{index}/requirements/{position}"
            for member in ("represents", "population_level"):
                if member in requirement and at not in spared:
                    found.append(Finding("BC-051", f"{at}/{member}", f"{member}, without the sampling suite"))
        for position, acceptance in _entries(model, "acceptances"):
            if acceptance.get("acceptance") == "distribution":
                at = f"/models/{index}/acceptances/{position}"
                found.append(Finding("BC-051", at, "a distribution, without the sampling suite"))
    return found


def _scene_members(declaration: JsonObject) -> list[Finding]:
    """Item 12's scene part: a model checked over a domain or a path, `region_conditions`, and an acceptance
    or `trainable` entry located at a region or an interval."""
    found: list[Finding] = []
    for index, model in _entries(declaration, "models"):
        at = f"/models/{index}"
        for name in ("domain", "path"):
            if name in _object(model.get("checked_over")):
                found.append(
                    Finding("BC-051", f"{at}/checked_over/{name}", f"a {name}, without the scene suite")
                )
        if "region_conditions" in model:
            found.append(
                Finding("BC-051", f"{at}/region_conditions", "region conditions, without the scene suite")
            )
        for member in ("acceptances", "trainable"):
            for position, entry in _entries(model, member):
                located = member == "trainable" or entry.get("acceptance") in _LOCATED_KINDS
                if located and {"region", "interval"} & entry.keys():
                    detail = "located at a region or an interval, without the scene suite"
                    found.append(Finding("BC-051", f"{at}/{member}/{position}", detail))
    return found


def _engine_values(engine: JsonObject, at: str) -> Iterator[tuple[str, JsonObject]]:
    for name, value in _items(engine.get("values")):
        if isinstance(value, dict):
            yield _join(f"{at}/values", name), value
    for region, values in _items(engine.get("region_values")):
        for name, value in _items(values):
            if isinstance(value, dict):
                yield _join(_join(f"{at}/region_values", region), name), value


def _object(value: JsonValue) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _list(value: JsonValue) -> list[JsonValue]:
    return value if isinstance(value, list) else []


def _items(value: JsonValue) -> Iterator[tuple[str, JsonValue]]:
    yield from _object(value).items()


def _reference(value: JsonValue) -> MaterialRef | None:
    id_, version, pin = (_object(value).get(name) for name in ("id", "version", "content_hash"))
    if isinstance(id_, str) and isinstance(version, str) and isinstance(pin, str):
        return MaterialRef(id_, version, pin)
    return None


def _checked_records(model: JsonObject) -> list[MaterialRef | None] | None:
    """The records a model is checked over, where `checked_over` names records alone: each reference, None for
    an entry that is not one."""
    checked_over = _object(model.get("checked_over"))
    records = checked_over.get("records")
    if "domain" in checked_over or "path" in checked_over or not isinstance(records, list):
        return None
    return [_reference(reference) for reference in records]


# The claims, the text, and the declaration that passed.

CLAIMS: frozenset[Suite] = frozenset({"plain_read", "hash", "build_checks"})
"""The suites a build claims unless told otherwise: plain read, the hash suite and the build checks."""

SUITES: frozenset[str] = frozenset(get_args(Suite))
# The suites item 12 refuses without, which this version does not build: a claim of one raises.
_NOT_BUILT = {
    "scene_documents": "S7b builds the scene suite's build checks",
    "usd_read": "S11 builds an engine model's build checks",
    "sampling": "the sampling suite's build checks come with its minor version",
}


def check_claims(claims: Collection[Suite]) -> frozenset[Suite]:
    """The claims, as a set. `ValueError` for claims no implementation makes: a suite not in the README's
    list, or claims without plain read or without the build checks, which every build claims.
    `NotImplementedError` for a claim of the scene suite, USD read or the sampling suite, which this version
    does not build."""
    claimed = frozenset(claims)
    if not claimed <= SUITES:
        raise ValueError(f"not suites: {sorted(claimed - SUITES)}")
    for suite in ("plain_read", "build_checks"):
        if suite not in claimed:
            raise ValueError(f"every build claims {suite}")
    for suite, piece in _NOT_BUILT.items():
        if suite in claimed:
            raise NotImplementedError(f"a build claiming {suite}: {piece}")
    return claimed


def parse_declaration(declaration: DeclarationInput) -> JsonValue | Reason:
    """The declaration's value, read by `record_format.md` section 1 item 6, or the reason `malformed`. Text
    is a `str` or bytes-like; any other value is read as the JSON text `json.dumps` writes of it."""
    if isinstance(declaration, str):
        # A lone surrogate stays in the bytes as invalid UTF-8, which the reader refuses, rather than raise.
        return jsonio.parse(declaration.encode("utf-8", "surrogatepass"))
    if isinstance(declaration, bytes | bytearray | memoryview):
        return jsonio.parse(bytes(declaration))
    try:
        return jsonio.parse(json.dumps(declaration, allow_nan=False).encode())
    except (TypeError, ValueError, RecursionError) as error:
        return Reason("malformed", detail=str(error))


@dataclass(frozen=True)
class Requirement:
    """A requirement that passed the check: its field and `want`; its conditions as given, which the build's
    own read request holds (section 2 item 7); and the label and review the build checks."""

    field: str
    want: Want
    conditions: JsonObject
    label: str | None
    reviewed: bool


@dataclass(frozen=True)
class Acceptance:
    """An acceptance that passed the check: its index in its model's `acceptances`, its kind, its location
    over records (None where it names none), the field it covers (None for an accepted difference and an
    `overlay_scope`), and its members as given."""

    index: int
    kind: str
    location: MaterialRef | None
    field: str | None
    members: JsonObject


@dataclass(frozen=True)
class ModelEntry:
    """A model entry that passed the check, over records, and the entry as given."""

    index: int
    name: str
    version: str
    configuration_hash: str
    records: tuple[MaterialRef, ...]
    target: JsonObject
    reads: tuple[str, ...]
    requirements: tuple[Requirement, ...]
    combinations: tuple[tuple[str, ...], ...]
    acceptances: tuple[Acceptance, ...]
    trainable: tuple[tuple[str, MaterialRef], ...]
    entry: JsonObject


@dataclass(frozen=True)
class Declaration:
    """A declaration that passed its own check (section 1), and the declaration as given."""

    consumer: shapes.Consumer
    operating_conditions: shapes.OperatingConditions
    models: tuple[ModelEntry, ...]
    given: JsonObject

    @classmethod
    def from_json(
        cls, declaration: DeclarationInput, claims: Collection[Suite] = CLAIMS
    ) -> "Declaration | tuple[BuildRefusal, ...]":
        """The declaration, or every refusal of it, one per fault (section 1). The claims are checked first
        (`check_claims`). A text that is not JSON, or a declaration that is not an object, is refused at the
        empty pointer, and nothing else is checked."""
        claimed = check_claims(claims)
        value = parse_declaration(declaration)
        if isinstance(value, Reason):
            return _precedence([Finding("BC-048", "", f"not JSON: {value.detail}")])
        if not isinstance(value, dict):
            return _precedence([Finding("BC-048", "", "the declaration is not an object")])
        found = [
            *_shape(value),
            *_tokens(value),
            *_names(value),
            *_reasons(value),
            *_locations(value),
            *_labels(value),
            *_suites(value, claimed),
        ]
        if found:
            return _precedence(found)
        given = cast(shapes.Declaration, value)
        models = tuple(_model(index, entry) for index, entry in _entries(value, "models"))
        return cls(given["consumer"], given["operating_conditions"], models, value)


def _model(index: int, entry: JsonObject) -> ModelEntry:
    """A model entry that broke no rule: every member has the shape `SHAPE` gives it."""
    model = cast(shapes.ModelEntry, entry)
    requirements = tuple(
        Requirement(
            requirement["field"],
            requirement["want"],
            cast(JsonObject, requirement.get("conditions", {})),
            requirement.get("label"),
            requirement.get("review") == "reviewed",
        )
        for requirement in model.get("requirements", [])
    )
    acceptances = tuple(
        Acceptance(
            position,
            cast(str, acceptance["acceptance"]),
            _reference(acceptance.get("record")),
            cast("str | None", acceptance.get("field")),
            acceptance,
        )
        for position, acceptance in _entries(entry, "acceptances")
    )
    trainable = tuple(
        (cast(str, item["field"]), reference)
        for _, item in _entries(entry, "trainable")
        if (reference := _reference(item.get("record"))) is not None
    )
    return ModelEntry(
        index,
        model["model"]["name"],
        model["model"]["version"],
        model["model_configuration_hash"],
        tuple(reference for reference in _checked_records(entry) or [] if reference is not None),
        cast(JsonObject, model["target"]),
        tuple(model["reads"]),
        requirements,
        tuple(tuple(combined) for combined in model["combinations"]),
        acceptances,
        trainable,
        entry,
    )
