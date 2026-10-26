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
build claims checks beyond the declaration (the scene suite, USD read, the sampling suite). Item 7 it places
where the declaration alone decides it (an engine model over records or a path, with another `want`, with a
crosswalk no case passes, or a declared value without its `reason` or `basis`: BC-040 at the model's
`engine`); what it cannot decide, and the shapes of an interval location and of an engine's declared values,
are rules it does not place: a refused declaration names them in `unplaced`, and a case compares it only
where `compare.rules_compared` leaves them out.

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
    "exactly_one_of": (
        "where a place takes exactly one of two or three members and holds none, the fault is the object's, "
        "at its pointer, as a missing member's is; where it holds more than one, the fault is the object's "
        "own, one with any other rule's fault at the same pointer"
    ),
    "reads_at_fault": (
        "a `reads` at fault is the member itself, absent, of another JSON type or empty; an entry of it that "
        "is no field, or a field twice, leaves the rest judged against the fields it does list. Beside a "
        "`reads` at fault no field is judged against it: a combination's fields and a `trainable` entry's "
        "stand aside as a requirement's does, the paragraph's principle applied to the pairs it does not name"
    ),
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
    "interval_location": (
        "the text gives an interval location no shape: the model does not place the BC-048 of one, and a "
        "declaration holding one is refused where the scene suite is not claimed (item 12)"
    ),
    "item_7_beyond_the_declaration": (
        "item 7 is placed where the declaration alone decides it, one BC-040 a model at its `engine`: over "
        "records or a path, a requirement with a token of `want` other than `value`, a pinned crosswalk "
        "outside `materica/` (a build-check case passes none), and a declared value, in `values` or "
        "`region_values`, that is an object without its `reason` or without its `basis`. What the "
        "declaration does not decide is not placed: a model over a domain (whether it includes the "
        "background, shares a region with another, or has a crosswalk that validates), a crosswalk of "
        "`materica/`, and the rest of a declared value's shape, which its crosswalk's attribute gives. A "
        "fault inside `engine`, or at an engine model's requirement's `want` that is no token, which item 7 "
        "may name too, is not placed either"
    ),
    "claimed_suite_hides_refusals": (
        "a declaration holding a member a suite the build claims checks further gives no verdict, even where "
        "the model places a certain refusal beside it (a BC-004 beside a claimed domain, a "
        "`population_level` beside no `represents` or another one, a sampled requirement with no `sampling` "
        "block): the fail-closed choice, a decision (maintainer, 2026-10-24), at the cost that no case "
        "compares the refusals of a build that claims a suite"
    ),
    "token_operating_condition": (
        "a token condition in `operating_conditions` or `region_conditions` is refused at it: the text gives "
        "an operating condition for a numeric one alone"
    ),
    "families_values": (
        "a `families` value, the family version, is not judged: the text gives it no type and no list, and "
        "only the key, a parameter-set field, is checked"
    ),
    "waiver_label_beside_an_unregistered_field": (
        "a waiver's `label` beside a `field` that is not registered, or beside no `field`, is refused by "
        "item 4 (no requirement for a field of that name names it) as well as the field's own fault, or the "
        "missing `field`'s: two faults at two members"
    ),
    "implied_status_object_pointer": (
        "a status object as an implied condition's value is refused at the member that holds it, "
        "`implies/<condition>`, as a target fact's is at `/target/<fact>`: the text gives the refusal in the "
        "target's words and not the pointer, and the maintainer's ruling of 2026-10-24 on the target's is "
        "extended to it; nothing inside the object is checked"
    ),
}

# declarations.md:177-180 "A fault more than one rule names carries the case of the first of: items 3, 4, 7
# and 8, the" and "section 4.1 item 4 [BC-050]; item 12 [BC-051]; this paragraph [BC-048]". A fault is one
# member at fault (declarations.md:145-146 "The pointer names the member at fault"): a member two rules name
# (a waiver's `label` that item 4 and the token rule both refuse, a `domain` of another JSON type that item 12
# and the shape rule both name) is one fault carrying both, as the build-check suite's README says of the
# first ("a fault the token rule names too"), and one refusal, `refusals_of` keeping the first's case
# (maintainer, 2026-10-24). A missing member is the object's fault, apart from the object's own and from
# another missing member's: `Fault.apart` names which. A rule that judges one member against another does not
# judge it where the other is at fault (declarations.md:157-158 "A rule that judges one member against
# another stands aside where the other is itself at fault"): the rules that do so are marked "Stands aside".
# It stands aside with three exceptions (the maintainer's ruling of 2026-10-26). A
# member is still held to what it must be whichever value the other holds, namely its JSON type (a
# distribution parameter's value is a number; an accepted difference's `value` is an object, a status object,
# judged as one, or `"any"`), a label that no registered field has, and `params` where no registered field's
# row allows the form `parameter_set`. A rule the text states for a member at fault still applies: a waiver
# whose `code` is no reason names no `condition`. An entry that is no well-formed name (a reference without
# string `id`, `version` and `content_hash`, a `field` that is no string) is neither the same as nor different
# from another, and no rule compares it. An acceptance that names no known kind keeps the rule above: none of
# its other members is judged.
ORDER: Final = ("BC-004", "BC-005", "BC-040", "BC-044", "BC-043", "BC-037", "BC-050", "BC-051", "BC-048")
SHAPE: Final = "BC-048"
# What the model gives a declaration that passes its own check: the build's results model
# (`build_results_model.py`) takes the declaration on from there.
PAST_THE_DECLARATION: Final = "past the declaration (S7a-2 to S7a-4)"

# The declaration's own token lists, beside the read model's tables
# declarations.md:214 "A requirement's `review` holds `reviewed`, the one token of schema 0.1.0"
REVIEWS: Final = ("reviewed",)
# declarations.md:102 "where the model evaluates tables or parameter sets (item 10) | `binary32` or
# `binary64`"
PRECISIONS: Final = ("binary32", "binary64")
# declarations.md:66 "per field the rule the model applies in a cell holding more than one material:
# `identity`, a named rule, or `refuse`"; mixing_rules.md:61-64 "| `arithmetic` | `p = sum_i phi_i * p_i` |"
MIXING_RULES: Final = ("identity", "arithmetic", "harmonic", "wood", "refuse")
# declarations.md:444 "`space` is `identity` or `log` (natural"
SPACES: Final = ("identity", "log")
# declarations.md:382 "`overlay`, `accepts` (any of `consumer`, `model`, `configuration`)"
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
# declarations.md:118 "a reason of `read_side_contract.md` section 4 other than `condition_unknown_name`,
# which section 4.2 never accepts"
NEVER_WAIVED: Final = ("condition_unknown_name",)

# declarations.md:376 "`fact`, a specimen fact whose shape has a `token` member, and `token`, one of its
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
    # declarations.md:208 "`sampling.independence` is a list of"
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
    # Open point: chain_ends. declarations.md:477-478 "A chain names the event that ends the first family's
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

# An acceptance's place, by its kind: declarations.md:368-370 "names the `field` it covers (an
# `accepted_difference` names its `section` in place of a field" and declarations.md:372 "| `acceptance` |
# Location | Own members | Effect |", each kind's Location and Own members columns. A pick is located by its
# `record` alone, a `region` or an `interval` being named beside it: declarations.md:374 "`record` (pinned by
# hash): the target's, or an overlay the read applies to the field" and "a pick that also names a `region` or
# an `interval` is not applied in a plain read" (maintainer, 2026-10-24).
LOCATIONS: Final[Place] = {
    "record": (dict, "located"),
    "region": (str, "located"),
    "interval": (object, "located"),
}
OPTIONAL_LOCATIONS: Final[Place] = {name: (kind, "no") for name, (kind, _) in LOCATIONS.items()}
KINDS: Final[Mapping[str, Place]] = {
    "pick": {**OPTIONAL_LOCATIONS, "record": (dict, "located"), "index": (float, "yes")},
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
# declarations.md:117 "| | `basis` | for `extrapolation`, `nominal` and `distribution` (item 4); no other kind
# holds it": a `basis` on another kind is a member the table does not name there.
NEEDS_BASIS: Final = ("extrapolation", "nominal", "distribution")


def acceptance_place(kind: str) -> Place:
    """The members of an acceptance of `kind`: those every acceptance holds, its kind's own, and its `field`
    and `basis` where the kind takes them."""
    place: dict[str, tuple[type, Required]] = {
        "acceptance": (str, "yes"), "reason": (str, "yes"), **KINDS[kind],
    }  # fmt: skip
    if kind not in NAMES_NO_FIELD:
        place["field"] = (str, "yes")
    if kind in NEEDS_BASIS:
        place["basis"] = (str, "yes")
    return place


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
        # declarations.md:281 "A declaration the build refuses on its own gives no results, no watches and
        # nothing unused; its report holds the declaration as given where the text is JSON, and its `consumer`
        # where the declaration declares one"
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
    apart: str = ""  # the missing member (or "one of", "a location") an object's fault is about, else ""


def at(pointer: str, *tokens: str | int) -> str:
    """The JSON pointer one or more members deeper, each token escaped as RFC 6901 escapes it."""
    for token in tokens:
        pointer += "/" + str(token).replace("~", "~0").replace("/", "~1")
    return pointer


def first_rule(rules: Iterable[str]) -> str:
    return min(rules, key=ORDER.index)


def refusals_of(faults: Iterable[Fault]) -> frozenset[Refusal]:
    """One refusal for each member at fault, with the case of the first rule that names it (the comment at
    `ORDER`). The rule is held where the faults are gathered, not at the rule that finds one: every rule
    that names a member adds its fault, and none refuses it twice."""
    naming: dict[tuple[str, str], list[str]] = {}
    for fault in faults:
        naming.setdefault((fault.pointer, fault.apart), []).extend(fault.rules)
    return frozenset(Refusal(first_rule(rules), pointer) for (pointer, _), rules in naming.items())


def check_build(text: bytes, claims: frozenset[str]) -> Refused | NoVerdict:
    """The build's check, claiming `claims`, of a declaration given as the text a case supplies."""
    # declarations.md:150-152 "for a text that is not valid JSON, or a declaration that is not an object, the
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


def is_status_object(value: JsonValue) -> bool:
    # provenance.md:8-9 "an object whose only members are `status` and, optionally, `reason` (a text)"
    return isinstance(value, dict) and "status" in value and value.keys() <= {"status", "reason"}


def in_unit_interval(number: float) -> bool:
    # declarations.md:205 "`sampling.min_acceptance` is a number in (0, 1]"
    return 0 < number <= 1


def missing_at(pointer: str, name: str) -> str:
    # declarations.md:146-147 "for a missing member, the object that should hold it"
    return pointer


def empty(value: JsonValue) -> bool:
    # declarations.md:124-125 "or empty where the table asks for one entry or more"
    return value == []


def given_before(value: object, earlier: Iterable[object]) -> bool:
    # declarations.md:131 "a name is given twice where the table allows it once"; declarations.md:147 "of two
    # of one name, the later entry of its list, whole"
    return value in list(earlier)


def reference_of(value: JsonValue) -> tuple[str, str, str] | None:
    """A material reference's name, its `id`, `version` and `content_hash`, or None where the value is no
    well-formed reference and names nothing (the comment at `ORDER`). What else it holds is not its name."""
    # declarations.md:120 "| material reference | `id`, `version`, `content_hash` | yes | strings |"
    if not isinstance(value, dict):
        return None
    identifier, version, content_hash = (value.get(member) for member in ("id", "version", "content_hash"))
    if isinstance(identifier, str) and isinstance(version, str) and isinstance(content_hash, str):
        return identifier, version, content_hash
    return None


def read_by(name: JsonValue, reads: list[str] | None) -> bool:
    # declarations.md:134 "a requirement or a `trainable` entry names a field its model does not list in
    # `reads`". Stands aside where `reads` is at fault: declarations.md:158-159 "a requirement's `field`
    # against a `reads` at fault (an empty one too)" (Open point: reads_at_fault).
    return reads is None or name in reads


class DeclarationCheck:
    def __init__(self, claims: frozenset[str]) -> None:
        self.claims = claims
        self.faults: list[Fault] = []
        self.unplaced: dict[str, str] = {}
        self.item_7_scopes: list[str] = []  # the pointers at which item 7 may name a fault first
        self.item_7_refused: list[str] = []  # the `engine` pointers of the models item 7 certainly refuses
        self.other_want = (
            False  # the model being checked has a requirement with a token of `want` but `value`
        )
        self.beyond: str | None = None
        self.picks_or_overlays = False
        self.sampling_members: list[tuple[str, JsonObject]] = []  # requirements holding either member
        self.rule_refused: list[str] = []  # the requirements the `population_level` rule refuses

    def fault(self, pointer: str, *rules: str, apart: str = "") -> None:
        self.faults.append(Fault(pointer, rules or (SHAPE,), apart))

    def unplace(self, rule: str, why: str) -> None:
        self.unplaced.setdefault(rule, why)

    def lacks(self, suite: str, why: str) -> bool:
        """Whether the build lacks a suite a member needs (declarations.md:221 "A build refuses at build what
        it cannot check"); where it claims it, that suite's checks are beyond the model."""
        if suite in self.claims:
            self.beyond = self.beyond or why
            return False
        return True

    def item_7_may_name(self, fault: Fault) -> bool:
        """Whether item 7 may name `fault` first: it lies inside an `engine`, or at a `want` of an engine
        model's requirement, or is the `engine` member's own fault (its type, or a member it lacks) where item
        7 does not certainly refuse the model. Where it does, the refusal at `engine` is item 7's, and a fault
        of the member itself is the same refusal."""
        for scope in self.item_7_scopes:
            if fault.pointer.startswith(scope + "/"):
                return True
            if fault.pointer == scope and not (scope in self.item_7_refused and not fault.apart):
                return True
        return False

    def verdict(self) -> Refused | NoVerdict:
        if self.beyond is not None:
            return NoVerdict(self.beyond)  # Open point: claimed_suite_hides_refusals.
        placed: list[Fault] = []
        for one in self.faults:
            if self.item_7_may_name(one):
                # Open point: item_7_beyond_the_declaration.
                self.unplace(first_rule(one.rules), "a fault item 7 may name first (S11)")
            else:
                placed.append(one)
        if placed:
            return Refused(refusals_of(placed), dict(self.unplaced))
        if self.unplaced:
            return NoVerdict("; ".join(f"{rule}, {why}" for rule, why in sorted(self.unplaced.items())))
        if self.picks_or_overlays:
            return NoVerdict("a pick or an overlay acceptance (S7c)")
        return NoVerdict(PAST_THE_DECLARATION)

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
                # declarations.md:155-156 "A member deeper down that holds another JSON type is a member at
                # fault like any other: the pointer names it, nothing inside it is checked"
                self.fault(at(pointer, name), *(mistyped or {}).get(name, (SHAPE,)))
        for name, (_, required) in place.items():
            if required == "yes" and name not in value:
                self.fault(missing_at(pointer, name), *(missing or {}).get(name, (SHAPE,)), apart=name)
        alternatives = [name for name, (_, required) in place.items() if required == "one"]
        if alternatives:
            # Open point: exactly_one_of. None is a missing member's fault, apart from the object's own; two
            # or more are the object's own fault, one with any other rule's fault there (declarations.md:146
            # "The pointer names the member at fault").
            held = sum(name in value for name in alternatives)
            if held == 0:
                self.fault(pointer, apart="one of")
            elif held > 1:
                self.fault(pointer)
        locations = [name for name, (_, required) in place.items() if required == "located"]
        if locations and not any(name in value for name in locations):
            # declarations.md:384 "An acceptance whose kind needs a location and names none is refused"
            self.fault(pointer, "BC-037", SHAPE, apart="a location")
        return typed

    def token(self, value: JsonValue, pointer: str, tokens: Collection[str]) -> bool:
        # declarations.md:129-130 "a token or a registered name is not one of those its member takes, a slip
        # of one, another member's token and one in another case included"
        if isinstance(value, str) and value in tokens:
            return True
        self.fault(pointer)
        return False

    def texts(self, typed: JsonObject, pointer: str, *names: str) -> None:
        # declarations.md:137 "a `reason` or `basis` is not a string of at least one character";
        # declarations.md:140-141 "two of a member's mutually exclusive alternatives, an
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
                    # declarations.md:147-148 "of two of one name, the later entry of its list, whole (the
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
        """The rules that name a fault of `sampling.min_acceptance`: declarations.md:205-207
        "`sampling.min_acceptance` is a number in (0, 1]" and "A declaration in which a requirement samples,
        without it or with one outside (0, 1], is refused at build"; its row's Holds alone where none does."""
        sampled = any("represents" in requirement for _, requirement in self.sampling_members)
        return ("BC-044", SHAPE) if sampled else (SHAPE,)

    def operating_conditions(self, conditions: JsonObject, pointer: str, implied: bool = False) -> None:
        # declarations.md:85 "for a numeric condition, in its registered unit, `lo` not above `hi`"
        for name, condition in conditions.items():
            row = CONDITIONS.get(name)
            if (
                row is None
                or (row.shape == "token" and not implied)
                or (implied and is_status_object(condition))
            ):
                # declarations.md:376 "never a status object": an implied condition holding one is the fault,
                # as a target fact is. Open point: token_operating_condition. Open point:
                # implied_status_object_pointer.
                self.fault(at(pointer, name))
            elif row.shape == "token":
                # declarations.md:376 "and `{"token"}`, with a token of its row, for a token one: a record
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
            self.fault(at(pointer, "unit"))  # declarations.md:138-139 "a unit other than the registered one"
        ends = typed.get("range")
        if isinstance(ends, list):
            for index, end in enumerate(ends):
                if not isinstance(end, float):
                    self.fault(at(pointer, "range", index))
            low, high = [*ends, 0.0, 0.0][:2]
            if len(ends) != 2 or (isinstance(low, float) and isinstance(high, float) and low > high):
                # declarations.md:138 "a `range` whose `lo` is above its `hi`"; one of other than two ends is
                # not declarations.md:85 "`{"range": [lo, hi], "unit"}`"
                self.fault(at(pointer, "range"))

    def model_entry(self, entry: JsonValue, pointer: str) -> None:
        typed = self.shaped(entry, pointer, SHAPES["model entry"])
        if typed is None:
            return
        self.other_want = False
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
            # version"; Open point: families_values.
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
        # declarations.md:221-222 "where it does not claim the scene suite, a model checked over a domain
        # or a path, `region_conditions`": the member that needs the suite, whatever JSON type it holds.
        if "region_conditions" in members(entry) and self.lacks(
            "scene_documents", "region_conditions under the scene suite (S7b)"
        ):
            self.fault(at(pointer, "region_conditions"), "BC-051")
        if isinstance(region_conditions := typed.get("region_conditions"), dict):
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
        is broken (the comment at `ORDER`)."""
        if "checked_over" not in typed:
            return None
        value = typed["checked_over"]
        held = self.shaped(value, pointer, SHAPES["checked_over"])
        for name in ("domain", "path"):
            if name in members(value) and self.lacks(
                "scene_documents", "a model checked over a domain or a path under the scene suite (S7b)"
            ):
                self.fault(at(pointer, name), "BC-051")
        if held is None:
            return None
        one = len(members(value).keys() & {"domain", "path", "records"}) == 1
        records = held.get("records")
        if not isinstance(records, list):
            return "scene" if one and "records" not in members(value) else None
        if empty(records):
            # declarations.md:91 "at least one material reference, none twice"
            self.fault(at(pointer, "records"))
        names: list[tuple[str, str, str] | None] = []
        for index, record in enumerate(records):
            self.shaped(record, at(pointer, "records", index), REFERENCE)
            named = reference_of(record)
            if one and named is not None and given_before(named, names):
                # declarations.md:148-149 "the field in `reads` or the record in `checked_over.records`
                # itself". A record is named by its reference. Beside another alternative neither side judges
                # a record twice.
                self.fault(at(pointer, "records", index))
            names.append(named)
        return records if one else None

    def reads(self, typed: JsonObject, pointer: str) -> list[str] | None:
        """The fields a model lists in `reads`, or None where the member is at fault: absent, of another JSON
        type, or empty (Open point: reads_at_fault)."""
        if empty(typed.get("reads")):
            # declarations.md:93 "| yes, at least one | registered fields, none twice |"
            self.fault(at(pointer, "reads"))
        if not isinstance(typed.get("reads"), list) or empty(typed.get("reads")):
            return None
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
        if row is None or (not basis_allowed and is_status_object(value)):
            # declarations.md:92 "never a status object": the member is the fault, and nothing inside it is
            # checked (the comment at `ORDER`).
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
        typed = self.shaped(value, pointer, place)
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
            # declarations.md:139 "other than the registered one, a number below zero"
            self.fault(at(pointer, "fraction_sum_tolerance"))
        for name, rule in members((typed or {}).get("rules")).items():
            # declarations.md:97 "field to `identity`, a rule `mixing_rules.md` names, or `refuse`"
            if self.token(name, at(pointer, "rules", name), FIELDS):
                self.token(rule, at(pointer, "rules", name), MIXING_RULES)

    def combination(self, combination: JsonValue, pointer: str, reads: list[str] | None) -> None:
        # declarations.md:98 "lists of two or more fields in `reads`, from different sections"; refused where
        # the Holds list refuses, declarations.md:140 "fewer than two fields or of fields of one section". The
        # count judges the list alone. The sections rule judges the entries against each other, so it stands
        # aside wherever an entry is no registered field: it refuses only where every entry is a registered
        # field and all are of one section (the maintainer's ruling of 2026-10-26).
        if not isinstance(combination, list):
            self.fault(pointer)
            return
        sections = [
            name.partition(".")[0] for name in combination if isinstance(name, str) and name in FIELDS
        ]
        every_entry_registered = len(sections) == len(combination)
        if len(combination) < 2 or (every_entry_registered and len(set(sections)) == 1):
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
        self, typed: JsonObject, pointer: str, reads: list[str] | None, engine_model: bool
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
                    self.fault(at_index)  # declarations.md:148 "the requirement, not its `field`"
                first.setdefault(name, requirement)
            if "want" in requirement:
                wants = self.token(requirement["want"], at(at_index, "want"), WANTS)
                if engine_model:
                    # declarations.md:197 "reads the fields its crosswalk sources, with `want` `value`" and
                    # declarations.md:199 "or with another `want`, is refused at build": a token of `want`
                    # other than `value`; a `want` that is no token is a fault item 7 may name too. Open
                    # point: item_7_beyond_the_declaration.
                    self.other_want = self.other_want or (wants and requirement["want"] != "value")
                    self.item_7_scopes.append(at(at_index, "want"))
            if "label" in requirement:
                # declarations.md:106 "| | `label` | no | a label registered for the field". Beside a field
                # that is not registered it is judged against every registered label, which refuses one no
                # field has (the comment at `ORDER`).
                self.token(
                    requirement["label"], at(at_index, "label"), label_of(str(name) if registered else None)
                )
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
        # declarations.md:188 "A tolerance or accept list MUST carry its reason; the build refuses one
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
            self.fault(pointer, "BC-043", apart="population_level")
            self.rule_refused.append(pointer)
        elif "population_level" in value and represents != "population":
            # declarations.md:109 "where `represents` is `population`, and only there": beside another token
            # or beside none. Stands aside beside a `represents` that is no token (declarations.md:158
            # "the `population_level` rule beside a `represents` that is no token").
            if "represents" not in value or (isinstance(represents, str) and represents in REPRESENTS):
                self.fault(at(pointer, "population_level"), "BC-043")
                self.rule_refused.append(pointer)
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
        # declarations.md:160-161 "an acceptance that names no known kind is refused at itself, and none of
        # its other members is judged": at the acceptance where the `acceptance` member is missing, at the
        # member where it is no kind.
        kind = members(value).get("acceptance")
        if not isinstance(value, dict):
            self.fault(pointer)
            return
        if "acceptance" not in value:
            self.fault(pointer, apart="acceptance")
            return
        if not isinstance(kind, str) or kind not in KINDS:
            self.fault(at(pointer, "acceptance"))
            return
        # declarations.md:190 "Every acceptance MUST carry a `reason`; an extrapolation, a nominal and a
        # distribution also carry the"
        rules = {"reason": ("BC-005", SHAPE), "basis": ("BC-005", SHAPE)}
        place = acceptance_place(kind)
        typed = self.shaped(value, pointer, place, rules) or {}
        self.texts(typed, pointer, "reason", "basis", "law")
        name = typed.get("field")
        field_name = name if "field" in typed and self.token(name, at(pointer, "field"), FIELDS) else None
        if "record" in typed:
            self.shaped(typed["record"], at(pointer, "record"), REFERENCE)
        if "interval" in typed:
            self.unplace(SHAPE, "an interval location's shape (S7b)")  # Open point: interval_location.
        locations = {name for name, (_, required) in place.items() if required == "located"}
        unlocated = bool(locations) and not locations & members(value).keys()
        if (members(value).keys() & {"region", "interval"}) and "region" in place and not unlocated:
            # declarations.md:222-223 "an acceptance or `trainable` entry located at a region or an interval";
            # a pick naming a region and no `record` is unlocated, BC-037's alone.
            if self.lacks(
                "scene_documents", "an acceptance at a region or an interval under the scene suite (S7b)"
            ):
                self.fault(pointer, "BC-051")
        # declarations.md:223-225 "where it does not claim the sampling suite, `sampling`, a requirement's
        # `represents` or `population_level`, and a `distribution` acceptance"
        if kind == "distribution" and self.lacks(
            "sampling", "a distribution acceptance under the sampling suite"
        ):
            self.fault(pointer, "BC-051")
        self.picks_or_overlays = self.picks_or_overlays or kind in ("pick", "overlay")
        self.own_members(kind, typed, pointer, str(field_name) if field_name else None, requirements, value)

    def own_members(
        self,
        kind: str,
        typed: JsonObject,
        pointer: str,
        name: str | None,
        requirements: Mapping[str, JsonObject],
        given: JsonObject,
    ) -> None:
        # declarations.md:118 "a pick's `index`, a whole number not below zero; a waiver's `code`, a reason
        # of"
        index = typed.get("index")
        if kind == "pick" and "index" in typed and not (whole(index) and index >= 0):
            self.fault(at(pointer, "index"))
        elif kind == "waiver":
            self.waiver(typed, pointer, name, requirements, given)
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
        elif kind == "nominal" and "params" in typed and not takes_parameter_set(name):
            # declarations.md:118 "`params` only for a field whose row allows"; read_side_contract.md:77-79 "a
            # nominal holding `params` and no `value`, for a field whose row allows none, breaks its shape".
            # Whenever the entry's `field` names no registered field (not registered, missing or no string) it
            # is judged against every registered row (the comment at `ORDER`).
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
                self.fault(at(pointer, "accepts"))  # declarations.md:141 "a repeated `accepts` token"
            for index, token in enumerate(accepts if isinstance(accepts, list) else []):
                self.token(token, at(pointer, "accepts", index), ACCEPTS)

    def waiver(
        self,
        typed: JsonObject,
        pointer: str,
        name: str | None,
        requirements: Mapping[str, JsonObject],
        given: JsonObject,
    ) -> None:
        code = typed.get("code")
        known = "code" in typed and self.token(code, at(pointer, "code"), REASONS)
        refused = known and code in NEVER_WAIVED
        if refused:
            # declarations.md:118 "other than `condition_unknown_name`, which section 4.2 never accepts"
            self.fault(at(pointer, "code"))
        # declarations.md:118 "a waiver whose `code` is no reason names no condition"
        names_one = known and code in CODES_NAMING_A_CONDITION
        # A `condition` of another JSON type is present, and the member at fault, not a missing one.
        if names_one and "condition" not in given:
            # Stands aside beside a `code` that is refused (declarations.md:159-160 "a waiver's missing
            # `condition` beside a `code` that is refused").
            if not refused:
                self.fault(pointer, apart="condition")
        elif "condition" in given and not names_one:
            self.fault(at(pointer, "condition"))
        elif "condition" in typed:
            self.token(typed["condition"], at(pointer, "condition"), CONDITIONS)
        if "label" not in typed:
            return
        label = typed["label"]
        # A label that is none of the field's is the token rule's fault; beside a field that is not
        # registered, one no field has (the comment at `ORDER`).
        registered = label in label_of(name)
        # declarations.md:405-406 "the build refuses it at build unless the requirement for its field names
        # that `label` and holds `review: "reviewed"`"; declarations.md:149-150 "for a waiver naming a `label`
        # that section 4.1 item 4 refuses, that waiver's `label`". Item 4 and the token rule name one member,
        # which `refusals_of` refuses once (the comment at `ORDER`). Open point:
        # waiver_label_beside_an_unregistered_field.
        held = typed.get("field")
        requirement = requirements.get(held, {}) if isinstance(held, str) else {}
        if requirement.get("label") != label or requirement.get("review") != "reviewed":
            self.fault(at(pointer, "label"), "BC-050")
        if not registered:
            self.fault(at(pointer, "label"))

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
        if is_status_object(value):
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
        known = "distribution" in typed and self.token(token, at(pointer, "distribution"), DISTRIBUTIONS)
        parameters = typed.get("distribution_parameters")
        if not isinstance(parameters, dict):
            return
        if known and sorted(parameters) != sorted(DISTRIBUTION_PARAMETERS[str(token)]):
            # declarations.md:141 "a distribution's parameters other than its token's". Beside a token that
            # is none, the names stand aside, each value's type is still judged (the comment at `ORDER`).
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
        reads: list[str] | None,
        over: list[JsonValue] | Literal["scene"] | None,
    ) -> None:
        entry = self.located_field(value, pointer)
        if entry is None:
            return
        if "field" in entry and not read_by(entry["field"], reads):
            # declarations.md:134 "names a field its model does not list in `reads`"
            self.fault(at(pointer, "field"))
        for where in sorted(entry.keys() & {"record", "region", "interval"}):
            # declarations.md:134-135 "or a `trainable` entry a location its model is not checked over". Over
            # records the location is the record read (declarations.md:258 "Over records the location is the
            # record read"), so a region or an interval is not a location, nor is a record over a domain or a
            # path (the maintainer's ruling of 2026-10-26); whether a region or an interval lies in the domain
            # or the path is the scene suite's.
            if over == "scene" and where != "record":
                self.unplace(SHAPE, "whether a region or interval lies where its model is checked over (S7b)")
            elif over is not None and (over == "scene" or where != "record" or unlisted(entry[where], over)):
                self.fault(at(pointer, where))
        if members(value).keys() & {"region", "interval"} and self.lacks(
            "scene_documents", "a trainable entry at a region or an interval under the scene suite (S7b)"
        ):
            # declarations.md:222 "an acceptance or `trainable` entry located": the entry at a region or an
            # interval of whatever type, as an acceptance is.
            self.fault(pointer, "BC-051")

    def trainable_twice(self, typed: JsonObject, pointer: str) -> None:
        # declarations.md:132-133 "two `trainable` entries for one field at one location"
        # A name is the field and the location: a record's reference, a region's name or an interval as
        # given. An entry whose field is no string, or whose location is no well-formed name, has none.
        seen: list[tuple[str, str, object]] = []
        for at_index, value in self.entries(typed, "trainable", pointer):
            held = members(value)
            locations = held.keys() & {"record", "region", "interval"}
            if isinstance(held.get("field"), str) and len(locations) == 1:
                (where,) = locations
                location = reference_of(held[where]) if where == "record" else held[where]
                if location is None or (where == "region" and not isinstance(location, str)):
                    continue
                key = (str(held["field"]), where, location)
                if given_before(key, seen):
                    self.fault(at_index)
                seen.append(key)

    def engine(self, entry: JsonObject, typed: JsonObject, pointer: str) -> None:
        where = at(pointer, "engine")
        engine = self.shaped(entry["engine"], where, SHAPES["engine"]) or {}
        pin = (
            self.shaped(engine["crosswalk"], at(where, "crosswalk"), SHAPES["crosswalk pin"])
            if ("crosswalk" in engine)
            else None
        )
        declared = [
            value
            for values in (engine.get("values"), *members(engine.get("region_values")).values())
            for value in members(values).values()
        ]
        if declared:
            self.unplace(
                SHAPE, "a declared engine value's shape, which its crosswalk's attribute gives (S11)"
            )
        # declarations.md:222-223 "where it does not claim USD read, a model with `engine`"
        if not self.lacks("usd_read", "an engine model under USD read (S11)"):
            return
        self.item_7_scopes.append(where)  # Open point: item_7_beyond_the_declaration.
        # declarations.md:198-199 "one checked over a path or records, over a domain that includes the
        # background, or with another `want`, is refused at build"; usd_binding.md:384-385 "the build resolves
        # each pin against the crosswalks passed to it and OpenMaterica's own"
        identifier = (pin or {}).get("id")
        over_records_or_a_path = bool(members(typed.get("checked_over")).keys() & {"records", "path"})
        not_passed = isinstance(identifier, str) and not identifier.startswith("materica/")
        # declarations.md:199-200 "A declared engine value without `reason` and `basis`"
        without_a_member = any(
            isinstance(value, dict) and not {"reason", "basis"} <= value.keys() for value in declared
        )
        if over_records_or_a_path or not_passed or self.other_want or without_a_member:
            # declarations.md:150-151 "for a model item 7 refuses, its `engine`, one refusal per model,
            # whichever of that item's rules it breaks"
            self.fault(where, "BC-040")
            self.item_7_refused.append(where)
        else:
            # declarations.md:226-227 "where item 7 refuses a model with `engine`, its `engine` gives no
            # refusal under this item": what that is, is not decided here.
            self.unplace("BC-040", "whether item 7 refuses an engine model (S11)")
            self.unplace("BC-051", "an engine model's own, unless item 7 refuses the model (S11)")

    def sampling(self, declaration: JsonObject) -> None:
        item_8 = self.item_8()
        sampled = "BC-044" in item_8
        value = declaration.get("sampling")
        if "sampling" not in declaration and sampled:
            # Under a claimed sampling suite the requirement that samples gives no verdict below, and with it
            # this refusal (Open point: claimed_suite_hides_refusals).
            self.fault("", "BC-044", apart="sampling")
        if isinstance(value, dict):
            item = {"min_acceptance": item_8}
            typed = self.shaped(value, "/sampling", SHAPES["sampling"], item, item) or {}
            self.texts(typed, "/sampling", "reason")
            minimum = typed.get("min_acceptance")
            if isinstance(minimum, float) and not in_unit_interval(minimum):
                self.fault("/sampling/min_acceptance", *item_8)
            for at_index, entry in self.entries(typed, "independence", "/sampling"):
                independence = self.shaped(entry, at_index, SHAPES["independence entry"]) or {}
                self.texts(independence, at_index, "reason", "basis")
                for field_pointer, located in self.entries(independence, "fields", at_index):
                    self.located_field(located, field_pointer)  # Open point: independence_fields.
        if "sampling" in declaration and self.lacks("sampling", "sampling under the sampling suite"):
            # declarations.md:153-154 "`sampling`, a requirement's `represents` or `population_level`"
            self.fault("/sampling", "BC-051")
        minimum = members(value).get("min_acceptance")
        item_8_refuses = sampled and not (isinstance(minimum, float) and in_unit_interval(minimum))
        for pointer, requirement in self.sampling_members:
            # declarations.md:227-228 "where item 8 or that rule refuses the declaration over a requirement,
            # that requirement gives none"
            spared = (item_8_refuses and "represents" in requirement) or pointer in self.rule_refused
            for name in ("represents", "population_level"):
                if name in requirement and self.lacks(
                    "sampling", "a requirement that samples under the sampling suite"
                ):
                    if not spared:
                        self.fault(at(pointer, name), "BC-051")


def label_of(name: str | None) -> tuple[str, ...]:
    """The labels registered for a field, or for every field where there is no registered one."""
    # record_format.md:161 "| Section.field | Unit | Forms | Requires | Label |"
    if name is None:
        return tuple(sorted({row.label for row in FIELDS.values() if row.label}))
    label = FIELDS[name].label
    return (label,) if label else ()


def takes_parameter_set(name: str | None) -> bool:
    """Whether a nominal may hold `params` for the field: the row of a registered field allows the form
    `parameter_set`, and beside a field that is not registered, the row of some registered field does."""
    # read_side_contract.md:77-78 "only where the row of the field it names allows the form `parameter_set`"
    rows = [FIELDS[name]] if name else list(FIELDS.values())
    return any("parameter_set" in row.forms for row in rows)


def unlisted(record: JsonValue, records: Iterable[JsonValue]) -> bool:
    """Whether a `trainable` entry's record is none of those a model is checked over, by reference. A record
    that is no well-formed reference names no record, so it is not compared with the listed ones (the comment
    at `ORDER`)."""
    name = reference_of(record)
    return name is not None and name not in {reference_of(held) for held in records}


def uberon(value: JsonValue) -> bool:
    # provenance.md:292 "`{"uberon": "UBERON:<digits>", "label": <text>, "basis"}`"
    digits = value[len("UBERON:") :] if isinstance(value, str) and value.startswith("UBERON:") else ""
    return digits.isascii() and digits.isdigit()
