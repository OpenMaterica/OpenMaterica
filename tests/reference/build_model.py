# SPDX-License-Identifier: Apache-2.0
"""A test-only reference model of a build's check of a declaration on its own: the refusals
`declarations.md` section 1 gives a declaration before any record is read, written from the specification's
text alone (section 1, its shape table and its precedence and pointer rules; section 4.1's location rule and
item 4), for the build-check cases (`test_cases.py`), HP41 and HP42.

It never ships and imports nothing from `materica`, at any depth (`test_layering.py`). Its shape table is
written here from the text; the registered names it checks against (fields, conditions, facts, reasons) are
the read model's tables, which `test_tables.py` holds to the generated vocabulary, as it holds this model's
own token lists.

**What it decides.** Every refusal of the declaration's own check, by case id and pointer: the departures from
its shape (BC-048), items 3 and 4 (BC-004, BC-005), item 8 (BC-044), the `population_level` rule (BC-043),
section 4.1's location rule (BC-037) and item 4 (BC-050), and item 12 (BC-051), each fault carrying the case
of the first rule that names it, and two of one case and pointer one refusal.

**What it does not.** `NoVerdict`, never a pass, for a declaration that passes its own check (what the build
gives after reading is S7a-2's to S7a-4's, a pick or an overlay S7c's), and for one holding what a suite the
build claims checks beyond the declaration (the scene suite, USD read, the sampling suite). Item 7's refusals
(BC-040) and the shapes of an interval location and of an engine's declared values are rules it does not
place: a refused declaration names them in `unplaced`, and a case compares it only where
`compare.rules_compared` leaves them out.

**Where the text is silent.** The model takes the maintainer's ruling where there is one, else the fail-closed
choice. Each such point is listed once in `OPEN_POINTS`, and named where it is applied ("Open point:
<name>")."""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Final, Literal, TypeAlias

from tests.reference.read_model import (
    ACCEPTANCE_KINDS,
    CONDITION_BASES,
    CONDITIONS,
    DISTRIBUTIONS,
    EXTRAPOLATION_METHODS,
    FACTS,
    FIELDS,
    LEVELS,
    REASONS,
    REPRESENTS,
    SECTIONS,
    STATUS_TOKENS,
    WANTS,
    NoVerdict,
    whole,
)
from tests.reference.strict_json import JsonObject, JsonValue, NotStrictJson, parse

OPEN_POINTS: Final[Mapping[str, str]] = {
    "what_one_fault_is": (
        "a fault is one departure of one member: a member missing that a rule and the shape rule both name "
        "(a `reason`, a location) is one fault, carrying the first rule's case; a member breaking two "
        "constraints (a waiver's `label` not registered for its field, and not named by its requirement) is "
        "two faults, each giving its refusal"
    ),
    "exactly_one_of": (
        "where a place takes exactly one of two or three members and holds none or more than one, the fault "
        "is the object's, at its pointer, as a missing member's is"
    ),
    "acceptance_of_an_unknown_kind": (
        "an acceptance whose `acceptance` is no kind of section 4.1 is refused at that member, and needs its "
        "`reason` as every acceptance does; its other members are not judged, since which ones it names "
        "depends on its kind"
    ),
    "member_judged_beside_a_faulty_one": (
        "a member whose allowed values depend on another member at fault is not judged: a label beside a "
        "field that is not registered, an implied condition's `token` or an accepted difference's `value` "
        "beside a fact that is none of section 6.2's, a distribution's parameters beside a token that is "
        "none of section 4's, a `trainable` entry's location beside a broken `checked_over`"
    ),
    "pick_located_at_a_region": (
        "a pick's location members are `record`, `region` and `interval`; one naming none of them is "
        "BC-037's, and one naming a region or an interval alone is located, which item 12 refuses where the "
        "build does not claim the scene suite"
    ),
    "combination_sections": "a combination's fields are from pairwise different sections",
    "chain_ends": (
        "a chain's `from` and `to` each hold `family`, a string, and `record`, a material reference, and its "
        "`state_mapping` maps names to strings"
    ),
    "independence_fields": (
        "each of an independence entry's `fields` is a registered field and one location, as a `trainable` "
        "entry names them"
    ),
    "accepted_difference_basis": (
        "an accepted difference's `value` may hold `basis`, `stated` or `inferred` (`stated` alone for "
        "`mimics`), and `inferred_from`, a string"
    ),
    "trainable_location_in_a_scene": (
        "whether a `trainable` entry's region or interval lies in the domain or path its model is checked "
        "over is the scene suite's: the model does not place that BC-048; over records a region or an "
        "interval never does, nor does a record over a domain or a path"
    ),
    "interval_location": (
        "the text gives an interval location no shape: the model does not place the BC-048 of one, and a "
        "declaration holding one is refused where the scene suite is not claimed (item 12)"
    ),
    "item_7_pointers": (
        "item 7 refuses an engine model at pointers the text does not fix: BC-040 is a rule the model does "
        "not place, certain over records or a path, and where the pinned crosswalk is outside `materica/` "
        "and none is passed (a build-check case passes none), else unknown; a fault inside `engine`, or at "
        "an engine model's requirement's `want`, which item 7 may name first, is not placed either"
    ),
    "basis_on_other_kinds": (
        "a `basis` on an acceptance of a kind other than extrapolation, nominal and distribution is a member "
        "not named there (BC-048): the maintainer's ruling of 2026-10-24, whose words land with S7a-1b's "
        'first commit, the shape table\'s `basis` row then reading "no other kind holds it"'
    ),
    "population_level_beside_another_represents": (
        "a `population_level` beside a `represents` that is not `population` is refused at it by the "
        "`population_level` rule (BC-043), and so is one beside no `represents`, so that item 12 refuses "
        "neither member of that requirement: the maintainer's ruling of 2026-10-24, whose words land with "
        'S7a-1b\'s first commit ("never beside another `represents`"), one beside none the fail-closed choice'
    ),
}

# declarations.md:155-157 "A fault more than one rule names carries the case of the first of: items 3, 4, 7
# and 8, the" and "section 4.1 item 4 [BC-050]; item 12 [BC-051]; this paragraph [BC-048]"
ORDER: Final = ("BC-004", "BC-005", "BC-040", "BC-044", "BC-043", "BC-037", "BC-050", "BC-051", "BC-048")
SHAPE: Final = "BC-048"

# The declaration's own token lists, beside the read model's tables
# declarations.md:192 "A requirement's `review` holds `reviewed`, the one token of schema 0.1.0"
REVIEWS: Final = ("reviewed",)
# declarations.md:102 "where the model evaluates tables or parameter sets (item 10) | `binary32` or
# `binary64`"
PRECISIONS: Final = ("binary32", "binary64")
# declarations.md:66 "per field the rule the model applies in a cell holding more than one material:
# `identity`, a named rule, or `refuse`"; mixing_rules.md:61-64 "| `arithmetic` | `p = sum_i phi_i * p_i` |"
MIXING_RULES: Final = ("identity", "arithmetic", "harmonic", "wood", "refuse")
# declarations.md:417 "`space` is `identity` or `log` (natural"
SPACES: Final = ("identity", "log")
# declarations.md:357 "`overlay`, `accepts` (any of `consumer`, `model`, `configuration`)"
ACCEPTS: Final = ("consumer", "model", "configuration")
# uncertainty.md:237 "| Token | Parameters |"
DISTRIBUTION_PARAMETERS: Final[Mapping[str, tuple[str, ...]]] = {
    "normal": ("mean", "sd"),
    "lognormal": ("mean", "sd"),
    "uniform": ("lower", "upper"),
    "triangular": ("lower", "mode", "upper"),
    "student_t": ("location", "scale", "dof"),
    "beta": ("lower", "upper", "p", "q"),
}
# declarations.md:118 "a code names a condition where its reasons always carry one: the six `condition_*`
# codes, `outside_range`, `at_edge` and `range_unstated`"
CODES_NAMING_A_CONDITION: Final = (
    *(code for code in REASONS if code.startswith("condition_")), "outside_range", "at_edge", "range_unstated"
)  # fmt: skip

# declarations.md:351 "`fact`, a specimen fact whose shape has a `token` member, and `token`, one of its
# tokens"
TOKEN_FACTS: Final = tuple(fact for fact, row in FACTS.items() if "token" in row.members)

# The shape table, from declarations.md:82 "| Place | Member | Required | Holds |". Each member has its JSON
# type (`object` for any, its value judged apart) and whether it is required: "yes"; "no", for a member the
# text marks optional or gives only where a condition holds (declarations.md:75-76 "A member this document
# marks optional, or gives only where a condition holds, may be absent"), whose rule is checked apart; "one",
# exactly one of the place's "one" members (Open point: exactly_one_of); or "located", at least one of an
# acceptance's location members, its absence BC-037's.
Required: TypeAlias = Literal["yes", "no", "one", "located"]
Place: TypeAlias = Mapping[str, tuple[type, Required]]
# declarations.md:120 "| material reference | `id`, `version`, `content_hash` | yes | strings |"
REFERENCE: Final[Place] = {"id": (str, "yes"), "version": (str, "yes"), "content_hash": (str, "yes")}
SHAPES: Final[Mapping[str, Place]] = {
    # declarations.md:84 "| declaration | `consumer` | yes | `{"name", "version"}`, both required |"
    "declaration": {
        "consumer": (dict, "yes"), "operating_conditions": (dict, "yes"), "sampling": (dict, "no"),
        "models": (list, "yes"),
    },
    "name and version": {"name": (str, "yes"), "version": (str, "yes")},
    # declarations.md:86 "`{"min_acceptance", "reason", "independence"}`, all required (items 8, 9)"
    "sampling": {"min_acceptance": (float, "yes"), "reason": (str, "yes"), "independence": (list, "yes")},
    # declarations.md:186 "`sampling.independence` is a list of"
    "independence entry": {"fields": (list, "yes"), "reason": (str, "yes"), "basis": (str, "yes")},
    # declarations.md:88 "| model entry | `model` | yes | `{"name", "version"}`, both required"
    "model entry": {
        "model": (dict, "yes"), "model_configuration_hash": (str, "yes"), "region_conditions": (dict, "no"),
        "checked_over": (dict, "yes"), "target": (dict, "yes"), "reads": (list, "yes"),
        "consumer_parameters": (list, "yes"), "requirements": (list, "no"), "families": (dict, "yes"),
        "mixing": (dict, "no"), "combinations": (list, "yes"), "acceptances": (list, "no"),
        "chains": (list, "yes"), "trainable": (list, "no"), "precision": (str, "no"), "engine": (dict, "no"),
    },
    # declarations.md:91 "exactly one of `{"domain"}`, `{"path"}`, each a name, and `{"records"}`"
    "checked_over": {"domain": (str, "one"), "path": (str, "one"), "records": (list, "one")},
    # declarations.md:85 "registered condition to `{"value", "unit"}` or `{"range": [lo, hi], "unit"}`"
    "operating condition": {"value": (float, "one"), "range": (list, "one"), "unit": (str, "yes")},
    # declarations.md:104 "| requirement | `field`, `want` | yes | a field in `reads`"
    "requirement": {
        "field": (str, "yes"), "want": (str, "yes"), "conditions": (dict, "no"), "label": (str, "no"),
        "review": (str, "no"), "represents": (str, "no"), "population_level": (dict, "no"),
    },
    # declarations.md:110 "| requirement condition | `tolerance` or `accept` | exactly one |"
    "requirement condition": {
        "tolerance": (dict, "one"), "accept": (list, "one"), "reason": (str, "yes"),
        "consequence": (str, "no"),
    },
    "tolerance": {"value": (float, "yes"), "unit": (str, "yes")},
    # declarations.md:64 "`{"level", "within"}` as in `uncertainty.md` section 1" and "`{"level",
    # "balanced_over": <level>}` for a balanced draw from an ensemble"
    "population_level": {"level": (str, "yes"), "within": (object, "one"), "balanced_over": (str, "one")},
    # provenance.md:8-9 "an object whose only members are `status` and, optionally, `reason` (a text)"
    "status object": {"status": (str, "yes"), "reason": (str, "no")},
    # declarations.md:97 "`{"fraction_sum_tolerance", "rules"}`, both required: a number not below zero"
    "mixing": {"fraction_sum_tolerance": (float, "yes"), "rules": (dict, "yes")},
    # declarations.md:100 "`{"from", "event", "to", "state_mapping"}`, all required (section 6)"
    "chain": {
        "from": (dict, "yes"), "event": (str, "yes"), "to": (dict, "yes"), "state_mapping": (dict, "yes"),
    },
    # Open point: chain_ends. declarations.md:450-451 "A chain names the event that ends the first family's
    # range and the family and record that take over"
    "chain end": {"family": (str, "yes"), "record": (dict, "yes")},
    # declarations.md:119 "| trainable entry | `field` and one of `record`, `region`, `interval` | yes |"
    "located field": {
        "field": (str, "yes"), "record": (dict, "one"), "region": (str, "one"), "interval": (object, "one"),
    },
    # declarations.md:103 "`{"crosswalk", "values"}` and optionally `region_values`"
    "engine": {"crosswalk": (dict, "yes"), "values": (dict, "yes"), "region_values": (dict, "no")},
    # usd_binding.md:364 "A crosswalk is pinned by `{"id", "version", "sha256"}`"
    "crosswalk pin": {"id": (str, "yes"), "version": (str, "yes"), "sha256": (str, "yes")},
}  # fmt: skip

# An acceptance's place, by its kind: declarations.md:343-345 "names the `field` it covers (an
# `accepted_difference` names its `section` in place of a field" and declarations.md:347 "| `acceptance` |
# Location | Own members | Effect |", each kind's Location and Own members columns (Open point:
# pick_located_at_a_region).
LOCATIONS: Final[Place] = {
    "record": (dict, "located"),
    "region": (str, "located"),
    "interval": (object, "located"),
}
OPTIONAL_LOCATIONS: Final[Place] = {name: (kind, "no") for name, (kind, _) in LOCATIONS.items()}
KINDS: Final[Mapping[str, Place]] = {
    "pick": {**LOCATIONS, "index": (float, "yes")},
    "waiver": {**LOCATIONS, "code": (str, "yes"), "condition": (str, "no"), "label": (str, "no")},
    "implied_condition": {**LOCATIONS, "fact": (str, "yes"), "token": (str, "yes"), "implies": (dict, "yes")},
    "accepted_difference": {
        **OPTIONAL_LOCATIONS, "section": (str, "yes"), "fact": (str, "yes"), "value": (object, "yes"),
    },
    "extrapolation": {**LOCATIONS, "method": (str, "yes"), "law": (str, "yes")},
    "nominal": {**LOCATIONS, "value": (float, "one"), "params": (object, "one")},
    "distribution": {
        **LOCATIONS, "distribution": (str, "yes"), "space": (str, "yes"),
        "distribution_parameters": (dict, "yes"),
    },
    "overlay": {"overlay": (dict, "yes")},
    "overlay_scope": {"overlay": (dict, "yes"), "accepts": (list, "yes")},
}  # fmt: skip
assert tuple(KINDS) == ACCEPTANCE_KINDS
# declarations.md:115 "yes, but an `accepted_difference` names `section` and an `overlay_scope` neither"
NAMES_NO_FIELD: Final = ("accepted_difference", "overlay_scope")
# declarations.md:117 "| | `basis` | for `extrapolation`, `nominal` and `distribution` (item 4)"; a basis
# on another kind is a member not named there (Open point: basis_on_other_kinds).
NEEDS_BASIS: Final = ("extrapolation", "nominal", "distribution")


@dataclass(frozen=True, order=True)
class Refusal:
    item: str
    pointer: str


@dataclass(frozen=True)
class Refused:
    """A declaration the build refuses on its own: every refusal of the rules the model places, the rules
    whose refusals it does not place, each with why, and the declaration as given where its text is JSON."""

    refusals: frozenset[Refusal]
    unplaced: Mapping[str, str] = field(default_factory=dict[str, str])
    given: tuple[JsonValue, ...] = ()

    def to_json(self) -> JsonObject:
        # declarations.md:259 "A declaration the build refuses on its own gives no results, no watches and
        # nothing unused"; declarations.md:250-252 "`consumer`, as declared;" and "`declaration`, as given;"
        report: JsonObject = {
            "refusals": [{"item": one.item, "pointer": one.pointer} for one in sorted(self.refusals)]
        }
        for declaration in self.given:
            report["declaration"] = declaration
            if "consumer" in members(declaration):
                report["consumer"] = members(declaration)["consumer"]
        return report


@dataclass(frozen=True)
class Fault:
    pointer: str
    rules: tuple[str, ...]  # every rule that names it


def at(pointer: str, *tokens: str | int) -> str:
    """The JSON pointer one or more members deeper, each token escaped as RFC 6901 escapes it."""
    for token in tokens:
        pointer += "/" + str(token).replace("~", "~0").replace("/", "~1")
    return pointer


def first_rule(rules: Iterable[str]) -> str:
    return min(rules, key=ORDER.index)


def refusals_of(faults: Iterable[Fault]) -> frozenset[Refusal]:
    # declarations.md:157-158 "Two faults with one case and one pointer are one refusal"; Open point:
    # what_one_fault_is.
    return frozenset(Refusal(first_rule(fault.rules), fault.pointer) for fault in faults)


def check_build(text: bytes, claims: frozenset[str]) -> Refused | NoVerdict:
    """The build's check, claiming `claims`, of a declaration given as the text a case supplies."""
    # declarations.md:149-150 "for a text that is not valid JSON, or a declaration that is not an object, the
    # empty pointer, and nothing else is checked"
    try:
        declaration = parse(text)
    except NotStrictJson:
        return Refused(frozenset({Refusal(SHAPE, "")}))
    if not isinstance(declaration, dict):
        return Refused(frozenset({Refusal(SHAPE, "")}), given=(declaration,))
    check = DeclarationCheck(claims)
    check.declaration(declaration)
    found = check.verdict()
    return replace(found, given=(declaration,)) if isinstance(found, Refused) else found


def members(value: JsonValue) -> JsonObject:
    return value if isinstance(value, dict) else {}


def missing_at(pointer: str, name: str) -> str:
    # declarations.md:145-146 "for a missing member, the object that should hold it"
    return pointer


def empty(value: JsonValue) -> bool:
    # declarations.md:124-125 "or empty where the table asks for one entry or more"
    return value == []


def given_before(value: JsonValue, earlier: Iterable[JsonValue]) -> bool:
    # declarations.md:131 "a name is given twice where the table allows it once"; declarations.md:146 "of two
    # of one name, the later entry of its list, whole"
    return value in list(earlier)


def read_by(name: JsonValue, reads: list[str]) -> bool:
    # declarations.md:134 "a requirement or a `trainable` entry names a field its model does not list in
    # `reads`"
    return name in reads


class DeclarationCheck:
    def __init__(self, claims: frozenset[str]) -> None:
        self.claims = claims
        self.faults: list[Fault] = []
        self.unplaced: dict[str, str] = {}
        self.refused_unplaced = False  # an unplaced rule certainly refuses the declaration
        self.item_7_scopes: list[str] = []  # the pointers at which item 7 may name a fault first
        self.beyond: str | None = None
        self.picks_or_overlays = False
        self.sampling_members: list[tuple[str, JsonObject]] = []  # requirements holding either member

    def fault(self, pointer: str, *rules: str) -> None:
        self.faults.append(Fault(pointer, rules or (SHAPE,)))

    def unplace(self, rule: str, why: str, refuses: bool = False) -> None:
        self.unplaced.setdefault(rule, why)
        self.refused_unplaced = self.refused_unplaced or refuses

    def lacks(self, suite: str, why: str) -> bool:
        """Whether the build lacks a suite a member needs (declarations.md:199 "A build refuses at build what
        it cannot check"); where it claims it, that suite's checks are beyond the model."""
        if suite in self.claims:
            self.beyond = self.beyond or why
            return False
        return True

    def verdict(self) -> Refused | NoVerdict:
        if self.beyond is not None:
            return NoVerdict(self.beyond)
        placed: list[Fault] = []
        for one in self.faults:
            if any(
                one.pointer == scope or one.pointer.startswith(scope + "/") for scope in self.item_7_scopes
            ):
                # Open point: item_7_pointers.
                self.unplace(first_rule(one.rules), "a fault item 7 may name first (S11)")
            else:
                placed.append(one)
        if placed or self.refused_unplaced:
            return Refused(refusals_of(placed), dict(self.unplaced))
        if self.unplaced:
            return NoVerdict("; ".join(f"{rule}, {why}" for rule, why in sorted(self.unplaced.items())))
        if self.picks_or_overlays:
            return NoVerdict("a pick or an overlay acceptance (S7c)")
        return NoVerdict("past the declaration (S7a-2 to S7a-4)")

    def shaped(
        self,
        value: JsonValue,
        pointer: str,
        place: Place,
        missing: Mapping[str, tuple[str, ...]] | None = None,
        mistyped: Mapping[str, tuple[str, ...]] | None = None,
    ) -> JsonObject | None:
        """The members of an object shaped as `place` that hold their JSON type, with the object's own faults:
        declarations.md:124-126 "a required member is missing, or a member is of another JSON type, or empty
        where" and "it holds, at any depth, a member the table does not name at that place". `missing` and
        `mistyped` name the rules besides the shape rule's that name a member's absence or type."""
        if not isinstance(value, dict):
            self.fault(pointer)
            return None
        typed: JsonObject = {}
        for name, held in value.items():
            if name not in place:
                self.fault(at(pointer, name))
            elif place[name][0] is object or isinstance(held, place[name][0]):
                typed[name] = held
            else:
                # declarations.md:153-154 "A member deeper down that holds another JSON type is a member at
                # fault like any other: the pointer names it, nothing inside it is checked"
                self.fault(at(pointer, name), *(mistyped or {}).get(name, (SHAPE,)))
        for name, (_, required) in place.items():
            if required == "yes" and name not in value:
                self.fault(missing_at(pointer, name), *(missing or {}).get(name, (SHAPE,)))
        alternatives = [name for name, (_, required) in place.items() if required == "one"]
        if alternatives and sum(name in value for name in alternatives) != 1:
            self.fault(pointer)  # Open point: exactly_one_of.
        locations = [name for name, (_, required) in place.items() if required == "located"]
        if locations and not any(name in value for name in locations):
            # declarations.md:359 "An acceptance whose kind needs a location and names none is refused"
            self.fault(pointer, "BC-037", SHAPE)
        return typed

    def token(self, value: JsonValue, pointer: str, tokens: Collection[str]) -> bool:
        # declarations.md:129-130 "a token or a registered name is not one of those its member takes, a slip
        # of one, another member's token and one in another case included"
        if isinstance(value, str) and value in tokens:
            return True
        self.fault(pointer)
        return False

    def texts(self, typed: JsonObject, pointer: str, *names: str) -> None:
        # declarations.md:136 "a `reason` or `basis` is not a string of at least one character";
        # declarations.md:139-140 "two of a member's mutually exclusive alternatives, an
        # empty `law`"
        for name in names:
            if typed.get(name) == "":
                self.fault(at(pointer, name))

    def entries(self, typed: JsonObject, name: str, pointer: str) -> list[tuple[str, JsonValue]]:
        held = typed.get(name)
        return (
            [(at(pointer, name, index), entry) for index, entry in enumerate(held)]
            if isinstance(held, list)
            else []
        )

    def declaration(self, declaration: JsonObject) -> None:
        # The models first: item 8 asks whether a requirement samples, `sampling`'s own type included.
        if empty(declaration.get("models")):
            self.fault("/models")  # declarations.md:87 "| | `models` | yes, at least one | model entries |"
        names: list[str] = []
        for pointer, entry in self.entries(declaration, "models", ""):
            self.model_entry(entry, pointer)
            name = members(members(entry).get("model")).get("name")
            if isinstance(name, str):
                if given_before(name, names):
                    # declarations.md:146-147 "of two of one name, the later entry of its list, whole (the
                    # model entry, not its `model.name`"
                    self.fault(pointer)
                names.append(name)
        item_8 = {"sampling": self.item_8()}
        typed = self.shaped(declaration, "", SHAPES["declaration"], mistyped=item_8) or {}
        if "consumer" in typed:
            self.shaped(typed["consumer"], "/consumer", SHAPES["name and version"])
        if isinstance(conditions := typed.get("operating_conditions"), dict):
            self.operating_conditions(conditions, "/operating_conditions")
        self.sampling(declaration)

    def item_8(self) -> tuple[str, ...]:
        """The rules that name a fault of `sampling.min_acceptance`: declarations.md:183-185
        "`sampling.min_acceptance` is a number in (0, 1]" and "A declaration in which a requirement samples,
        without it or with one outside (0, 1], is refused at build"; its row's Holds alone where none does."""
        sampled = any("represents" in requirement for _, requirement in self.sampling_members)
        return ("BC-044", SHAPE) if sampled else (SHAPE,)

    def operating_conditions(self, conditions: JsonObject, pointer: str, implied: bool = False) -> None:
        # declarations.md:85 "for a numeric condition, in its registered unit, `lo` not above `hi`"
        for name, condition in conditions.items():
            row = CONDITIONS.get(name)
            if row is None or (row.shape == "token" and not implied):
                self.fault(at(pointer, name))
            elif row.shape == "token":
                # declarations.md:351 "and `{"token"}`, with a token of its row, for a token one: a record
                # condition's shapes without `basis` (one there is ignored)"
                place: Place = {"token": (str, "yes"), "basis": (object, "no")}
                if (typed := self.shaped(condition, at(pointer, name), place)) and "token" in typed:
                    self.token(typed["token"], at(pointer, name, "token"), row.tokens)
            else:
                place = {**SHAPES["operating condition"], **({"basis": (object, "no")} if implied else {})}
                if (typed := self.shaped(condition, at(pointer, name), place)) is not None:
                    self.numeric(typed, at(pointer, name), row.unit)

    def numeric(self, typed: JsonObject, pointer: str, unit: str | None) -> None:
        if "unit" in typed and typed["unit"] != unit:
            self.fault(at(pointer, "unit"))  # declarations.md:137-138 "a unit other than the registered one"
        ends = typed.get("range")
        if isinstance(ends, list):
            for index, end in enumerate(ends):
                if not isinstance(end, float):
                    self.fault(at(pointer, "range", index))
            low, high = [*ends, 0.0, 0.0][:2]
            if len(ends) != 2 or (isinstance(low, float) and isinstance(high, float) and low > high):
                # declarations.md:137 "a `range` whose `lo` is above its `hi`"
                self.fault(at(pointer, "range"))

    def model_entry(self, entry: JsonValue, pointer: str) -> None:
        typed = self.shaped(entry, pointer, SHAPES["model entry"])
        if typed is None:
            return
        if "model" in typed:
            self.shaped(typed["model"], at(pointer, "model"), SHAPES["name and version"])
        over = self.checked_over(typed, at(pointer, "checked_over"))
        reads = self.reads(typed, pointer)
        for fact, value in members(typed.get("target")).items():
            self.fact(fact, value, at(pointer, "target", fact), basis_allowed=False)
        for at_index, parameter in self.entries(typed, "consumer_parameters", pointer):
            if not isinstance(parameter, str):
                # declarations.md:94 "| | `consumer_parameters` | yes, `[]` allowed | strings |"
                self.fault(at_index)
        for name in members(typed.get("families")):
            # declarations.md:96 "| | `families` | yes, `{}` allowed | parameter-set field to the family
            # version"
            if name not in FIELDS or "parameter_set" not in FIELDS[name].forms:
                self.fault(at(pointer, "families", name))
        if "mixing" in typed:
            self.mixing(typed["mixing"], at(pointer, "mixing"))
        for at_index, combination in self.entries(typed, "combinations", pointer):
            self.combination(combination, at_index, reads)
        for at_index, chain in self.entries(typed, "chains", pointer):
            self.chain(chain, at_index)
        if "precision" in typed:
            self.token(typed["precision"], at(pointer, "precision"), PRECISIONS)
        if isinstance(region_conditions := typed.get("region_conditions"), dict):
            # declarations.md:199-200 "where it does not claim the scene suite, a model checked over a domain
            # or a path, `region_conditions`"
            if self.lacks("scene_documents", "region_conditions under the scene suite (S7b)"):
                self.fault(at(pointer, "region_conditions"), "BC-051")
            for region, conditions in region_conditions.items():
                if isinstance(conditions, dict):
                    self.operating_conditions(conditions, at(pointer, "region_conditions", region))
                else:
                    self.fault(at(pointer, "region_conditions", region))
        engine_model = isinstance(entry, dict) and "engine" in entry
        requirements = self.requirements(typed, pointer, reads, engine_model)
        for at_index, acceptance in self.entries(typed, "acceptances", pointer):
            self.acceptance(acceptance, at_index, requirements)
        for at_index, located in self.entries(typed, "trainable", pointer):
            self.trainable(located, at_index, reads, over)
        self.trainable_twice(typed, pointer)
        if engine_model:
            self.engine(entry if isinstance(entry, dict) else {}, typed, pointer)

    def checked_over(self, typed: JsonObject, pointer: str) -> list[JsonValue] | Literal["scene"] | None:
        """The records a model is checked over, "scene" for a domain or a path, or None where `checked_over`
        is broken (Open point: member_judged_beside_a_faulty_one)."""
        if "checked_over" not in typed:
            return None
        value = typed["checked_over"]
        held = self.shaped(value, pointer, SHAPES["checked_over"])
        for name in ("domain", "path"):
            if name in members(value) and self.lacks(
                "scene_documents", "a model checked over a domain or a path under the scene suite (S7b)"
            ):
                self.fault(at(pointer, name), "BC-051")
        if held is None or len(members(value).keys() & {"domain", "path", "records"}) != 1:
            return None
        records = held.get("records")
        if not isinstance(records, list):
            return "scene" if "records" not in members(value) else None
        if empty(records):
            # declarations.md:91 "at least one material reference, none twice"
            self.fault(at(pointer, "records"))
        for index, record in enumerate(records):
            self.shaped(record, at(pointer, "records", index), REFERENCE)
            if given_before(record, records[:index]):
                # declarations.md:147-148 "the field in `reads` or the record in `checked_over.records`
                # itself"
                self.fault(at(pointer, "records", index))
        return records

    def reads(self, typed: JsonObject, pointer: str) -> list[str]:
        if empty(typed.get("reads")):
            # declarations.md:93 "| yes, at least one | registered fields, none twice |"
            self.fault(at(pointer, "reads"))
        listed: list[str] = []
        for at_index, name in self.entries(typed, "reads", pointer):
            if self.token(name, at_index, FIELDS) and isinstance(name, str):
                if given_before(name, listed):
                    self.fault(at_index)
                listed.append(name)
        return listed

    def fact(self, name: str, value: JsonValue, pointer: str, basis_allowed: bool) -> None:
        """A fact of provenance.md section 6.2: declarations.md:92 "a fact of `provenance.md` section 6.2 to
        its shape there without `basis`, its text members (`label`, `text`) optional"."""
        row = FACTS.get(name)
        if row is None:
            self.fault(pointer)
            return
        kinds = {"integer": float, "number": float, "range": list}
        place: dict[str, tuple[type, Required]] = {
            member: (kinds.get(kind, str), "no" if member in ("label", "text") else "yes")
            for member, kind in row.members.items()
        }
        if name == "donor_age":
            place.update(value=(float, "one"), range=(list, "one"))
        if basis_allowed:
            # Open point: accepted_difference_basis.
            place.update(basis=(str, "no"), inferred_from=(str, "no"))
        typed = self.shaped(value, pointer, place)  # declarations.md:92 "never a status object"
        for member, held in (typed or {}).items():
            kind = row.members.get(member)
            if kind == "token":
                self.token(held, at(pointer, member), row.tokens)
            elif kind == "unit":
                self.token(held, at(pointer, member), (row.unit or "",))
            elif member == "basis":
                self.token(held, at(pointer, member), (row.basis,) if row.basis else CONDITION_BASES)
            elif (kind == "integer" and not whole(held)) or (member == "uberon" and not uberon(held)):
                self.fault(at(pointer, member))
        if typed and "range" in typed:
            self.numeric({"range": typed["range"]}, pointer, None)

    def mixing(self, value: JsonValue, pointer: str) -> None:
        typed = self.shaped(value, pointer, SHAPES["mixing"])
        tolerance = (typed or {}).get("fraction_sum_tolerance")
        if isinstance(tolerance, float) and tolerance < 0:
            # declarations.md:138 "other than the registered one, a number below zero"
            self.fault(at(pointer, "fraction_sum_tolerance"))
        for name, rule in members((typed or {}).get("rules")).items():
            # declarations.md:97 "field to `identity`, a rule `mixing_rules.md` names, or `refuse`"
            if self.token(name, at(pointer, "rules", name), FIELDS):
                self.token(rule, at(pointer, "rules", name), MIXING_RULES)

    def combination(self, combination: JsonValue, pointer: str, reads: list[str]) -> None:
        # declarations.md:98 "lists of two or more fields in `reads`, from different sections"; Open point:
        # combination_sections.
        if not isinstance(combination, list):
            self.fault(pointer)
            return
        sections = [
            name.partition(".")[0] for name in combination if isinstance(name, str) and name in FIELDS
        ]
        if len(combination) < 2 or len(set(sections)) < len(sections):
            self.fault(pointer)
        for index, name in enumerate(combination):
            if self.token(name, at(pointer, index), FIELDS) and not read_by(name, reads):
                self.fault(at(pointer, index))

    def chain(self, chain: JsonValue, pointer: str) -> None:
        typed = self.shaped(chain, pointer, SHAPES["chain"]) or {}
        for end in ("from", "to"):
            if end in typed and (held := self.shaped(typed[end], at(pointer, end), SHAPES["chain end"])):
                if "record" in held:
                    self.shaped(held["record"], at(pointer, end, "record"), REFERENCE)
        for name, mapped in members(typed.get("state_mapping")).items():
            if not isinstance(mapped, str):
                self.fault(at(pointer, "state_mapping", name))  # Open point: chain_ends.

    def requirements(
        self, typed: JsonObject, pointer: str, reads: list[str], engine_model: bool
    ) -> dict[str, JsonObject]:
        """Each requirement checked, and the first requirement for each field."""
        first: dict[str, JsonObject] = {}
        for at_index, value in self.entries(typed, "requirements", pointer):
            requirement = self.shaped(value, at_index, SHAPES["requirement"])
            if requirement is None:
                continue
            name = requirement.get("field")
            registered = "field" in requirement and self.token(name, at(at_index, "field"), FIELDS)
            if registered and not read_by(name, reads):
                # declarations.md:134 "a requirement or a `trainable` entry names a field its model does not
                # list in `reads`"
                self.fault(at(at_index, "field"))
            if isinstance(name, str):
                if given_before(name, first):
                    self.fault(at_index)  # declarations.md:147 "the requirement, not its `field`"
                first.setdefault(name, requirement)
            if "want" in requirement:
                self.token(requirement["want"], at(at_index, "want"), WANTS)
                if engine_model:
                    self.item_7_scopes.append(at(at_index, "want"))  # Open point: item_7_pointers.
            if "label" in requirement and registered:
                # declarations.md:106 "| | `label` | no | a label registered for the field"; Open point:
                # member_judged_beside_a_faulty_one.
                self.token(requirement["label"], at(at_index, "label"), label_of(str(name)))
            if "review" in requirement:
                self.token(requirement["review"], at(at_index, "review"), REVIEWS)
            for condition, entry in members(requirement.get("conditions")).items():
                self.requirement_condition(condition, entry, at(at_index, "conditions", condition))
            self.population_level(members(value), requirement, at_index)
        return first

    def requirement_condition(self, name: str, entry: JsonValue, pointer: str) -> None:
        row = CONDITIONS.get(name)
        if row is None:
            self.fault(pointer)  # declarations.md:105 "registered condition to a requirement condition"
            return
        # declarations.md:166 "A tolerance or accept list MUST carry its reason; the build refuses one
        # without"
        given = bool(members(entry).keys() & {"tolerance", "accept"})
        reason = {"reason": ("BC-004", SHAPE)} if given else None
        typed = self.shaped(entry, pointer, SHAPES["requirement condition"], reason) or {}
        self.texts(typed, pointer, "reason")
        # declarations.md:110 "`{"value", "unit"}`, not below zero, in the condition's unit, for a numeric
        # condition; at least one token of the condition's row, for a token one"
        if "tolerance" in typed and row.shape == "token":
            self.fault(at(pointer, "tolerance"))
        elif "tolerance" in typed:
            tolerance = self.shaped(typed["tolerance"], at(pointer, "tolerance"), SHAPES["tolerance"]) or {}
            if isinstance(number := tolerance.get("value"), float) and number < 0:
                self.fault(at(pointer, "tolerance", "value"))
            self.numeric(
                {"unit": tolerance["unit"]} if "unit" in tolerance else {}, at(pointer, "tolerance"), row.unit
            )
        accept = typed.get("accept")
        if isinstance(accept, list) and (row.shape == "numeric" or empty(accept)):
            self.fault(at(pointer, "accept"))
        elif isinstance(accept, list):
            for index, token in enumerate(accept):
                self.token(token, at(pointer, "accept", index), row.tokens)

    def population_level(self, value: JsonObject, requirement: JsonObject, pointer: str) -> None:
        represents = value.get("represents")
        if "represents" in requirement:
            self.token(represents, at(pointer, "represents"), REPRESENTS)
        if "represents" in value or "population_level" in value:
            self.sampling_members.append((pointer, value))
        if represents == "population" and "population_level" not in value:
            # declarations.md:64 "and, where `represents` is `population` and the field is sampled,
            # `population_level`"
            self.fault(pointer, "BC-043")
        elif "population_level" in value and represents != "population":
            # Open point: population_level_beside_another_represents.
            self.fault(at(pointer, "population_level"), "BC-043")
        level = requirement.get("population_level")
        if level is None:
            return
        typed = self.shaped(level, at(pointer, "population_level"), SHAPES["population_level"]) or {}
        for name in ("level", "balanced_over"):
            if name in typed:
                self.token(typed[name], at(pointer, "population_level", name), LEVELS)
        within = typed.get("within")
        if isinstance(within, dict):
            # uncertainty.md:37 "`{"level": <level>, "within": <level> or {"status": "none"}}`"
            status = self.shaped(within, at(pointer, "population_level", "within"), SHAPES["status object"])
            if status and "status" in status:
                self.token(status["status"], at(pointer, "population_level", "within", "status"), ("none",))
        elif "within" in typed:
            self.token(within, at(pointer, "population_level", "within"), LEVELS)

    def acceptance(self, value: JsonValue, pointer: str, requirements: Mapping[str, JsonObject]) -> None:
        kind = members(value).get("acceptance")
        # declarations.md:168 "Every acceptance MUST carry a `reason`; an extrapolation, a nominal and a
        # distribution also carry the"
        rules = {"reason": ("BC-005", SHAPE), "basis": ("BC-005", SHAPE)}
        if not isinstance(kind, str) or kind not in KINDS:
            # Open point: acceptance_of_an_unknown_kind.
            place: dict[str, tuple[type, Required]] = {name: (object, "no") for name in members(value)}
            place.update(acceptance=(str, "yes"), reason=(str, "yes"))
            typed = self.shaped(value, pointer, place, rules) or {}
            if "acceptance" in typed:
                self.token(typed["acceptance"], at(pointer, "acceptance"), KINDS)
            self.texts(typed, pointer, "reason")
            return
        place = {"acceptance": (str, "yes"), "reason": (str, "yes"), **KINDS[kind]}
        if kind not in NAMES_NO_FIELD:
            place["field"] = (str, "yes")
        if kind in NEEDS_BASIS:
            place["basis"] = (str, "yes")
        typed = self.shaped(value, pointer, place, rules) or {}
        self.texts(typed, pointer, "reason", "basis", "law")
        name = typed.get("field")
        field_name = name if "field" in typed and self.token(name, at(pointer, "field"), FIELDS) else None
        if "record" in typed:
            self.shaped(typed["record"], at(pointer, "record"), REFERENCE)
        if "interval" in typed:
            self.unplace(SHAPE, "an interval location's shape (S7b)")  # Open point: interval_location.
        if (members(value).keys() & {"region", "interval"}) and "region" in place:
            # declarations.md:200-201 "an acceptance or `trainable` entry located at a region or an interval"
            if self.lacks(
                "scene_documents", "an acceptance at a region or an interval under the scene suite (S7b)"
            ):
                self.fault(pointer, "BC-051")
        # declarations.md:201-203 "where it does not claim the sampling suite, `sampling`, a requirement's
        # `represents` or `population_level`, and a `distribution` acceptance"
        if kind == "distribution" and self.lacks(
            "sampling", "a distribution acceptance under the sampling suite"
        ):
            self.fault(pointer, "BC-051")
        self.picks_or_overlays = self.picks_or_overlays or kind in ("pick", "overlay")
        self.own_members(kind, typed, pointer, str(field_name) if field_name else None, requirements)

    def own_members(
        self,
        kind: str,
        typed: JsonObject,
        pointer: str,
        name: str | None,
        requirements: Mapping[str, JsonObject],
    ) -> None:
        # declarations.md:118 "a pick's `index`, a whole number not below zero; a waiver's `code`, a reason
        # of"
        index = typed.get("index")
        if kind == "pick" and "index" in typed and not (whole(index) and index >= 0):
            self.fault(at(pointer, "index"))
        elif kind == "waiver":
            self.waiver(typed, pointer, name, requirements)
        elif kind == "implied_condition":
            fact = typed.get("fact")
            if "fact" in typed and self.token(fact, at(pointer, "fact"), TOKEN_FACTS) and "token" in typed:
                self.token(typed["token"], at(pointer, "token"), FACTS[str(fact)].tokens)
            if isinstance(implies := typed.get("implies"), dict):
                # declarations.md:127-128 "but for a `basis` inside an implied condition's `implies`, which
                # section 4.1's row ignores"
                self.operating_conditions(implies, at(pointer, "implies"), implied=True)
        elif kind == "accepted_difference":
            self.accepted_difference(typed, pointer)
        elif kind == "extrapolation" and "method" in typed:
            self.token(typed["method"], at(pointer, "method"), EXTRAPOLATION_METHODS)
        elif kind == "nominal" and "params" in typed and name and "parameter_set" not in FIELDS[name].forms:
            # declarations.md:118 "`params` only for a field whose row allows"
            self.fault(at(pointer, "params"))
        elif kind == "distribution":
            self.distribution(typed, pointer)
        elif kind in ("overlay", "overlay_scope"):
            if "overlay" in typed:
                self.shaped(typed["overlay"], at(pointer, "overlay"), REFERENCE)
            accepts = typed.get("accepts")
            strings = (
                [token for token in accepts if isinstance(token, str)] if isinstance(accepts, list) else []
            )
            if isinstance(accepts, list) and (empty(accepts) or len(set(strings)) < len(strings)):
                self.fault(at(pointer, "accepts"))  # declarations.md:140 "a repeated `accepts` token"
            for index, token in enumerate(accepts if isinstance(accepts, list) else []):
                self.token(token, at(pointer, "accepts", index), ACCEPTS)

    def waiver(
        self, typed: JsonObject, pointer: str, name: str | None, requirements: Mapping[str, JsonObject]
    ) -> None:
        code = typed.get("code")
        known = "code" in typed and self.token(code, at(pointer, "code"), REASONS)
        # declarations.md:118 "a waiver whose `code` is no reason names no condition"
        names_one = known and code in CODES_NAMING_A_CONDITION
        if names_one and "condition" not in typed:
            self.fault(pointer)
        elif "condition" in typed and not names_one:
            self.fault(at(pointer, "condition"))
        elif "condition" in typed:
            self.token(typed["condition"], at(pointer, "condition"), CONDITIONS)
        if "label" not in typed:
            return
        if name is not None:
            # Open point: member_judged_beside_a_faulty_one.
            self.token(typed["label"], at(pointer, "label"), label_of(name))
        # declarations.md:380-381 "the build refuses it at build unless the requirement for its field names
        # that `label` and holds `review: "reviewed"`"; declarations.md:148-149 "for a waiver naming a `label`
        # that section 4.1 item 4 refuses, that waiver's `label`"
        held = typed.get("field")
        requirement = requirements.get(held, {}) if isinstance(held, str) else {}
        if requirement.get("label") != typed["label"] or requirement.get("review") != "reviewed":
            self.fault(at(pointer, "label"), "BC-050")

    def accepted_difference(self, typed: JsonObject, pointer: str) -> None:
        if "section" in typed:
            self.token(typed["section"], at(pointer, "section"), sorted(SECTIONS))
        fact = typed.get("fact")
        known = "fact" in typed and self.token(fact, at(pointer, "fact"), FACTS)
        # declarations.md:118 "its `value` that fact's shape (its `basis` and text members optional), a status
        # object or `"any"`"
        value = typed.get("value")
        if "value" not in typed or value == "any":
            return
        if isinstance(value, dict) and "status" in value:
            status = self.shaped(value, at(pointer, "value"), SHAPES["status object"])
            if status and "status" in status:
                self.token(status["status"], at(pointer, "value", "status"), STATUS_TOKENS)
        elif not isinstance(value, dict):
            self.fault(at(pointer, "value"))
        elif known:
            self.fact(str(fact), value, at(pointer, "value"), basis_allowed=True)

    def distribution(self, typed: JsonObject, pointer: str) -> None:
        if "space" in typed:
            self.token(typed["space"], at(pointer, "space"), SPACES)
        token = typed.get("distribution")
        if not ("distribution" in typed and self.token(token, at(pointer, "distribution"), DISTRIBUTIONS)):
            return  # Open point: member_judged_beside_a_faulty_one.
        parameters = typed.get("distribution_parameters")
        if not isinstance(parameters, dict):
            return
        if sorted(parameters) != sorted(DISTRIBUTION_PARAMETERS[str(token)]):
            # declarations.md:140 "a distribution's parameters other than its token's"
            self.fault(at(pointer, "distribution_parameters"))
        for parameter, number in parameters.items():
            if not isinstance(number, float):
                self.fault(at(pointer, "distribution_parameters", parameter))

    def located_field(self, value: JsonValue, pointer: str) -> JsonObject | None:
        located = self.shaped(value, pointer, SHAPES["located field"])
        if located is None:
            return None
        if "field" in located and not self.token(located["field"], at(pointer, "field"), FIELDS):
            del located["field"]
        if "record" in located:
            self.shaped(located["record"], at(pointer, "record"), REFERENCE)
        if "interval" in located:
            self.unplace(SHAPE, "an interval location's shape (S7b)")  # Open point: interval_location.
        return located

    def trainable(
        self,
        value: JsonValue,
        pointer: str,
        reads: list[str],
        over: list[JsonValue] | Literal["scene"] | None,
    ) -> None:
        entry = self.located_field(value, pointer)
        if entry is None:
            return
        if "field" in entry and not read_by(entry["field"], reads):
            # declarations.md:134 "names a field its model does not list in `reads`"
            self.fault(at(pointer, "field"))
        for where in sorted(entry.keys() & {"record", "region", "interval"}):
            # declarations.md:134-135 "or a `trainable` entry a location its model is not checked over"
            if over == "scene" and where != "record":
                self.unplace(SHAPE, "whether a region or interval lies where its model is checked over (S7b)")
            elif over is not None and (over == "scene" or where != "record" or entry[where] not in over):
                self.fault(at(pointer, where))  # Open point: trainable_location_in_a_scene.
            if where != "record" and self.lacks(
                "scene_documents", "a trainable entry at a region or an interval under the scene suite (S7b)"
            ):
                # declarations.md:200 "an acceptance or `trainable` entry located"
                self.fault(pointer, "BC-051")

    def trainable_twice(self, typed: JsonObject, pointer: str) -> None:
        # declarations.md:132-133 "two `trainable` entries for one field at one location"
        seen: list[JsonObject] = []
        for at_index, value in self.entries(typed, "trainable", pointer):
            held = members(value)
            locations = held.keys() & {"record", "region", "interval"}
            if "field" in held and len(locations) == 1:
                key = {name: held[name] for name in ("field", *locations)}
                if given_before(key, seen):
                    self.fault(at_index)
                seen.append(key)

    def engine(self, entry: JsonObject, typed: JsonObject, pointer: str) -> None:
        engine = self.shaped(entry["engine"], at(pointer, "engine"), SHAPES["engine"]) or {}
        pin = (
            self.shaped(engine["crosswalk"], at(pointer, "engine", "crosswalk"), SHAPES["crosswalk pin"])
            if ("crosswalk" in engine)
            else None
        )
        if engine.get("values") or engine.get("region_values"):
            self.unplace(
                SHAPE, "a declared engine value's shape, which its crosswalk's attribute gives (S11)"
            )
        # declarations.md:200-201 "where it does not claim USD read, a model with `engine`"
        if not self.lacks("usd_read", "an engine model under USD read (S11)"):
            return
        self.item_7_scopes.append(at(pointer, "engine"))  # Open point: item_7_pointers.
        # declarations.md:176-177 "one checked over a path or records, over a domain that includes the
        # background, or with another `want`, is refused at build"; usd_binding.md:384-385 "the build resolves
        # each pin against the crosswalks passed to it and OpenMaterica's own"
        identifier = (pin or {}).get("id")
        over_records_or_a_path = bool(members(typed.get("checked_over")).keys() & {"records", "path"})
        not_passed = isinstance(identifier, str) and not identifier.startswith("materica/")
        if over_records_or_a_path or not_passed:
            # declarations.md:204-205 "where item 7 refuses a model with `engine`, its `engine` gives no
            # refusal under this item"
            self.unplace(
                "BC-040", "item 7's refusal of an engine model, at pointers the text does not fix (S11)", True
            )
        else:
            self.unplace("BC-040", "whether item 7 refuses an engine model over a domain (S11)")
            self.unplace("BC-051", "an engine model's own, unless item 7 refuses the model (S11)")

    def sampling(self, declaration: JsonObject) -> None:
        item_8 = self.item_8()
        sampled = "BC-044" in item_8
        value = declaration.get("sampling")
        if "sampling" not in declaration and sampled:
            self.fault("", "BC-044")
        if isinstance(value, dict):
            item = {"min_acceptance": item_8}
            typed = self.shaped(value, "/sampling", SHAPES["sampling"], item, item) or {}
            self.texts(typed, "/sampling", "reason")
            minimum = typed.get("min_acceptance")
            if isinstance(minimum, float) and not 0 < minimum <= 1:
                self.fault("/sampling/min_acceptance", *item_8)
            for at_index, entry in self.entries(typed, "independence", "/sampling"):
                independence = self.shaped(entry, at_index, SHAPES["independence entry"]) or {}
                self.texts(independence, at_index, "reason", "basis")
                for field_pointer, located in self.entries(independence, "fields", at_index):
                    self.located_field(located, field_pointer)  # Open point: independence_fields.
        if "sampling" in declaration and self.lacks("sampling", "sampling under the sampling suite"):
            # declarations.md:151-152 "`sampling`, a requirement's `represents` or `population_level`"
            self.fault("/sampling", "BC-051")
        minimum = members(value).get("min_acceptance")
        item_8_refuses = sampled and not (isinstance(minimum, float) and 0 < minimum <= 1)
        for pointer, requirement in self.sampling_members:
            # declarations.md:205-206 "where item 8 or that rule refuses the declaration over a requirement,
            # that requirement gives none"
            if (item_8_refuses and "represents" in requirement) or (
                (requirement.get("represents") == "population") != ("population_level" in requirement)
            ):
                continue
            for name in ("represents", "population_level"):
                if name in requirement and self.lacks(
                    "sampling", "a requirement that samples under the sampling suite"
                ):
                    self.fault(at(pointer, name), "BC-051")


def label_of(name: str) -> tuple[str, ...]:
    # record_format.md:161 "| Section.field | Unit | Forms | Requires | Label |"
    label = FIELDS[name].label
    return (label,) if label else ()


def uberon(value: JsonValue) -> bool:
    # provenance.md:292 "`{"uberon": "UBERON:<digits>", "label": <text>, "basis"}`"
    digits = value[len("UBERON:") :] if isinstance(value, str) and value.startswith("UBERON:") else ""
    return digits.isascii() and digits.isdigit()
