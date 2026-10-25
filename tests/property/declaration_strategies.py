# SPDX-License-Identifier: Apache-2.0
"""Strategies for HP41 and HP42 (the S7 design's 6.4): declarations over records that `declarations.md`
section 1 takes, and faults planted in them by name, each with the pointer it puts at fault.

A declaration is drawn from the text alone: section 1's members table and shape table, section 4.1's rows,
`provenance.md` section 6.2's facts, `uncertainty.md` section 4's distributions, `mixing_rules.md`'s rules and
`read_side_contract.md` section 6's `want` tokens, each cited where it is used. The registered fields,
conditions, facts, sections and labels, and the vocabulary's token lists, come from `core/vocabulary.py`,
which is generated from the specification. Nothing here reads `core/declarations.py`, whose `SHAPE`, `TOKENS`
and rules the properties check.

`declarations` draws a declaration the text takes, under claims of none of the suites item 12 names: one to
three models, each checked over one to three listed records of `stores.py`'s fixtures and reading one to four
fields, each with a requirement or none; acceptances of every kind section 4.1 lists that such a build can
check, located at a record where their kind needs a location, an accepted difference located or not;
`trainable` entries; `target` facts of every shape; and the optional members present or absent. Its numbers
are doubles, as every JSON number is read (`record_format.md` section 1 item 6), at physical scales.

A planter changes a copy of such a declaration and records each fault it plants (`Planted`): its name, the
pointer the refusal paragraph gives it (the member at fault, or the object that should hold a missing member),
and, for a missing member or none of a place's exclusive alternatives, which, so that the oracle can tell one
fault two rules name from two faults at one pointer. The property tests map a fault's name to the rules the
text gives it, and the rules to the refusals by the refusal paragraph's order: the oracle is theirs, the
planting this module's. A planter puts no other member at fault: where a change would reach a member that
rests on the one it changes (a waiver's `label` on its requirement, a `trainable` entry's record on
`checked_over.records`, a requirement's field on `reads`), it chooses a place where none rests, clears what
rests there first, or plants a fresh entry.
"""

import copy
import json
from collections.abc import Callable, Sequence
from typing import NamedTuple, cast

from hypothesis import strategies as st

from materica.core.jsonio import JsonValue
from materica.core.vocabulary import STATUS_TOKENS, VOCABULARY
from materica.shapes import Suite
from tests.property import records, stores
from tests.property.strategies import Size

Json = dict[str, JsonValue]

# The text's lists, each where the text gives it.

# `read_side_contract.md` section 6: the `want` tokens.
WANTS = ("value", "bounds", "components", "evidence", "reference_data", "fit", "coverage")
# Section 1, `precision`: "`binary32` or `binary64`".
PRECISIONS = ("binary32", "binary64")
# Section 1, `mixing`: "`identity`, a named rule, or `refuse`"; `mixing_rules.md`'s named rules.
MIXING_RULES = ("identity", "arithmetic", "harmonic", "wood", "refuse")
# Section 4.1, `extrapolation`: "`method` (`constant` or `consumer_law`)".
METHODS = ("constant", "consumer_law")
# Section 4.3 and `uncertainty.md` section 4: each token and its parameters.
DISTRIBUTIONS: dict[str, tuple[str, ...]] = {
    "normal": ("mean", "sd"),
    "lognormal": ("mean", "sd"),
    "uniform": ("lower", "upper"),
    "triangular": ("lower", "mode", "upper"),
    "student_t": ("location", "scale", "dof"),
    "beta": ("lower", "upper", "p", "q"),
}
# Section 4.3: "`space` is `identity` or `log`".
SPACES = ("identity", "log")
# Section 4.1, `overlay_scope`: "`accepts` (any of `consumer`, `model`, `configuration`)".
ACCEPTS = ("consumer", "model", "configuration")
# Item 11: "A requirement's `review` holds `reviewed`, the one token of schema 0.1.0".
REVIEW = "reviewed"
# The shape table's own members cell: a waiver's `code` is "a reason of `read_side_contract.md` section 4
# other than `condition_unknown_name`", and "a code names a condition where its reasons always carry one: the
# six `condition_*` codes, `outside_range`, `at_edge` and `range_unstated`".
NEVER_WAIVED = "condition_unknown_name"
WAIVER_CODES = tuple(code for code in VOCABULARY.reasons if code != NEVER_WAIVED)
CONDITION_CODES = (
    *(code for code in VOCABULARY.reasons if code.startswith("condition_")),
    "outside_range",
    "at_edge",
    "range_unstated",
)
WAIVED_CONDITION_CODES = tuple(code for code in CONDITION_CODES if code != NEVER_WAIVED)
OTHER_CODES = tuple(code for code in WAIVER_CODES if code not in CONDITION_CODES)
# Section 4.1's kinds; those a build that claims none of item 12's suites can check (a distribution is the
# sampling suite's); those whose row gives "`region`, `interval` or `record`".
KINDS = VOCABULARY.acceptance_kinds
CHECKED_KINDS = tuple(kind for kind in KINDS if kind != "distribution")
LOCATED_KINDS = ("waiver", "implied_condition", "extrapolation", "nominal", "distribution")
# Item 4: "an extrapolation, a nominal and a distribution also carry the `basis` of their number".
BASIS_KINDS = ("extrapolation", "nominal", "distribution")

FIELDS = tuple(sorted(VOCABULARY.fields))
LABELS = {name: spec.label for name, spec in VOCABULARY.fields.items() if spec.label is not None}
ANY_LABEL = VOCABULARY.token_lists["label"]
CONDITIONS = tuple(VOCABULARY.conditions)
NUMERIC = tuple(name for name, spec in VOCABULARY.conditions.items() if spec.shape == "numeric")
TOKEN_CONDITIONS = tuple(name for name, spec in VOCABULARY.conditions.items() if spec.shape == "token")
UNITS = {name: str(VOCABULARY.conditions[name].unit) for name in NUMERIC}
CONDITION_TOKENS = {name: VOCABULARY.conditions[name].tokens for name in TOKEN_CONDITIONS}
FACTS = tuple(VOCABULARY.facts)
FACTS_WITH_TOKENS = tuple(name for name, spec in VOCABULARY.facts.items() if spec.tokens)
SECTIONS = tuple(sorted(VOCABULARY.sections))
LEVELS = VOCABULARY.token_lists["level"]
REPRESENTS = VOCABULARY.token_lists["represents"]
FACT_BASES = VOCABULARY.token_lists["basis"]

# Each numeric condition's values at a physical scale, in its registered unit; a condition registered later
# draws from 0 to 1 until it has its own.
SCALES = {
    "temperature": (250.0, 400.0),
    "shear_rate": (0.1, 1.0e4),
    "magnetic_flux_density": (0.0, 2.0),
    "specimen_size": (1.0e-6, 0.1),
    "measurement_dimension": (1.0e-6, 0.1),
}

# `provenance.md` section 6.2, each fact's members but `basis`, by kind: a `token` of the fact's row, text,
# an NCBI Taxonomy integer, an UBERON identifier, a number, and the unit the row fixes. A target holds each in
# that shape, "its text members (`label`, `text`) optional" (section 1's shape table); `donor_age` holds
# `value` or `range`.
FACT_MEMBERS: dict[str, dict[str, str]] = {
    "species": {"ncbi_taxon": "integer", "label": "text"},
    "anatomical_site": {"uberon": "uberon", "label": "text"},
    "tissue_state": {"token": "token"},
    "disease_and_treatment_state": {"token": "token", "text": "text"},
    "preparation": {"text": "text"},
    "preservation": {"token": "token", "text": "text"},
    "post_mortem_interval": {"value": "number", "unit": "unit"},
    "donor_age": {"value": "number", "unit": "unit"},
    "mimics": {"text": "text"},
    "supply_form": {"token": "token"},
    "lot": {"text": "text"},
}

# The members the shape table names at each place (section 1; section 4.1 for each kind's own), which a
# slip or a member of no place avoids. A kind's members are its row's: `acceptance`, its location, `field` but
# where it names none, its own, `reason`, and `basis` for item 4's three kinds; an acceptance of no kind may
# hold any kind's.
_LOCATION = ("record", "region", "interval")
NAMED: dict[str, tuple[str, ...]] = {
    "declaration": ("consumer", "operating_conditions", "sampling", "models"),
    "consumer": ("name", "version"),
    "operating condition": ("value", "range", "unit"),
    "model entry": (
        "model",
        "model_configuration_hash",
        "region_conditions",
        "checked_over",
        "target",
        "reads",
        "consumer_parameters",
        "requirements",
        "families",
        "mixing",
        "combinations",
        "acceptances",
        "chains",
        "trainable",
        "precision",
        "engine",
    ),
    "model": ("name", "version"),
    "checked over": ("domain", "path", "records"),
    "material reference": ("id", "version", "content_hash"),
    "requirement": ("field", "want", "conditions", "label", "review", "represents", "population_level"),
    "requirement condition": ("tolerance", "accept", "reason", "consequence"),
    "tolerance": ("value", "unit"),
    "trainable entry": ("field", *_LOCATION),
    "mixing": ("fraction_sum_tolerance", "rules"),
    "chain": ("from", "event", "to", "state_mapping"),
    "chain end": ("family", "record"),
    "implied numeric": ("value", "range", "unit", "basis"),
    "implied token": ("token", "basis"),
    "status object": ("status", "reason"),
    "pick": ("acceptance", *_LOCATION, "field", "index", "reason"),
    "waiver": ("acceptance", *_LOCATION, "field", "code", "condition", "label", "reason"),
    "implied_condition": ("acceptance", *_LOCATION, "field", "fact", "token", "implies", "reason"),
    "accepted_difference": ("acceptance", *_LOCATION, "section", "fact", "value", "reason"),
    "extrapolation": ("acceptance", *_LOCATION, "field", "method", "law", "reason", "basis"),
    "nominal": ("acceptance", *_LOCATION, "field", "value", "params", "reason", "basis"),
    "distribution": (
        "acceptance",
        *_LOCATION,
        "field",
        "distribution",
        "distribution_parameters",
        "space",
        "reason",
        "basis",
    ),
    "overlay": ("acceptance", "field", "overlay", "reason"),
    "overlay_scope": ("acceptance", "overlay", "accepts", "reason"),
    **{f"fact {name}": tuple(members) for name, members in FACT_MEMBERS.items()},
}
NAMED["fact donor_age"] = (*NAMED["fact donor_age"], "range")
NAMED["acceptance"] = tuple(sorted({name for kind in KINDS for name in NAMED[kind]}))
for _fact in FACTS:
    # An accepted difference's `value`: the fact's shape, "its `basis` and text members optional", and
    # `inferred_from` where the fact's row leaves the basis open (`provenance.md` section 6.2's `mimics` row).
    _open = "basis" not in VOCABULARY.facts[_fact].fixed
    NAMED[f"difference {_fact}"] = (*NAMED[f"fact {_fact}"], "basis", *(("inferred_from",) if _open else ()))
EVERY_NAME = tuple(sorted({name for names in NAMED.values() for name in names}))

# What each place requires (section 1's Required column, 4.1's rows): the members whose absence alone is a
# fault, and the exclusive alternatives of which exactly one is held. A location, `reason` and `basis` are
# the rules' own (BC-037, items 3 and 4) and are left out here; a waiver's `condition` is required where its
# code names one.
REQUIRED: dict[str, tuple[str, ...]] = {
    "declaration": ("consumer", "operating_conditions", "models"),
    "consumer": ("name", "version"),
    "operating condition": ("unit",),
    "model entry": (
        "model",
        "model_configuration_hash",
        "checked_over",
        "target",
        "reads",
        "consumer_parameters",
        "families",
        "combinations",
        "chains",
    ),
    "model": ("name", "version"),
    "material reference": ("id", "version", "content_hash"),
    "requirement": ("field", "want"),
    "tolerance": ("value", "unit"),
    "trainable entry": ("field",),
    "mixing": ("fraction_sum_tolerance", "rules"),
    "chain": ("from", "event", "to", "state_mapping"),
    "chain end": ("family", "record"),
    "implied numeric": ("unit",),
    "implied token": ("token",),
    "pick": ("acceptance", "field", "index"),
    "waiver": ("acceptance", "field", "code"),
    "implied_condition": ("acceptance", "field", "fact", "token", "implies"),
    "accepted_difference": ("acceptance", "section", "fact", "value"),
    "extrapolation": ("acceptance", "field", "method", "law"),
    "nominal": ("acceptance", "field"),
    "distribution": ("acceptance", "field", "distribution", "distribution_parameters", "space"),
    "overlay": ("acceptance", "field", "overlay"),
    "overlay_scope": ("acceptance", "overlay", "accepts"),
    "fact species": ("ncbi_taxon",),
    "fact anatomical_site": ("uberon",),
    "fact tissue_state": ("token",),
    "fact disease_and_treatment_state": ("token",),
    "fact preservation": ("token",),
    "fact post_mortem_interval": ("value", "unit"),
    "fact donor_age": ("unit",),
    "fact supply_form": ("token",),
}
EXCLUSIVE: dict[str, tuple[str, ...]] = {
    "operating condition": ("value", "range"),
    "implied numeric": ("value", "range"),
    "fact donor_age": ("value", "range"),
    "difference donor_age": ("value", "range"),
    "requirement condition": ("tolerance", "accept"),
    "checked over": ("domain", "path", "records"),
    "trainable entry": _LOCATION,
    "nominal": ("value", "params"),
}

# The JSON type each member holds, by place (the Holds column): `string`, `number`, `object` (a place or a
# map), `list`. A member holding any value (an interval, a nominal's `params`, an implied condition's
# `basis`, an accepted difference's `value`) is left out, since no value is of another type.
TYPES: dict[str, dict[str, str]] = {
    "declaration": {"consumer": "object", "operating_conditions": "object", "models": "list"},
    "consumer": {"name": "string", "version": "string"},
    "operating condition": {"value": "number", "range": "list", "unit": "string"},
    "model entry": {
        "model": "object",
        "model_configuration_hash": "string",
        "checked_over": "object",
        "target": "object",
        "reads": "list",
        "consumer_parameters": "list",
        "requirements": "list",
        "families": "object",
        "mixing": "object",
        "combinations": "list",
        "acceptances": "list",
        "chains": "list",
        "trainable": "list",
        "precision": "string",
    },
    "model": {"name": "string", "version": "string"},
    "checked over": {"records": "list"},
    "material reference": {"id": "string", "version": "string", "content_hash": "string"},
    "requirement": {
        "field": "string",
        "want": "string",
        "conditions": "object",
        "label": "string",
        "review": "string",
    },
    "requirement condition": {
        "tolerance": "object",
        "accept": "list",
        "reason": "string",
        "consequence": "string",
    },
    "tolerance": {"value": "number", "unit": "string"},
    "trainable entry": {"field": "string", "record": "object"},
    "mixing": {"fraction_sum_tolerance": "number", "rules": "object"},
    "chain": {"from": "object", "event": "string", "to": "object", "state_mapping": "object"},
    "chain end": {"family": "string", "record": "object"},
    "implied numeric": {"value": "number", "range": "list", "unit": "string"},
    "implied token": {"token": "string"},
    "status object": {"status": "string", "reason": "string"},
    "pick": {
        "acceptance": "string",
        "record": "object",
        "field": "string",
        "index": "number",
        "reason": "string",
    },
    "waiver": {
        "acceptance": "string",
        "record": "object",
        "field": "string",
        "code": "string",
        "reason": "string",
    },
    "implied_condition": {
        "acceptance": "string",
        "record": "object",
        "field": "string",
        "fact": "string",
        "token": "string",
        "implies": "object",
        "reason": "string",
    },
    "accepted_difference": {
        "acceptance": "string",
        "section": "string",
        "fact": "string",
        "reason": "string",
    },
    "extrapolation": {
        "acceptance": "string",
        "record": "object",
        "field": "string",
        "method": "string",
        "law": "string",
        "reason": "string",
        "basis": "string",
    },
    "nominal": {
        "acceptance": "string",
        "record": "object",
        "field": "string",
        "value": "number",
        "reason": "string",
        "basis": "string",
    },
    "overlay": {"acceptance": "string", "field": "string", "overlay": "object", "reason": "string"},
    "overlay_scope": {"acceptance": "string", "overlay": "object", "accepts": "list", "reason": "string"},
    "fact species": {"ncbi_taxon": "number", "label": "string"},
    "fact anatomical_site": {"uberon": "string", "label": "string"},
    "fact tissue_state": {"token": "string"},
    "fact preservation": {"token": "string", "text": "string"},
    "fact post_mortem_interval": {"value": "number", "unit": "string"},
    "fact donor_age": {"value": "number", "range": "list", "unit": "string"},
    "fact supply_form": {"token": "string"},
}
for _fact in FACTS:
    # An accepted difference's `value` requires what its fact's shape requires, and holds `basis`, a token,
    # and `inferred_from`, a string, beside its members.
    REQUIRED[f"difference {_fact}"] = REQUIRED.get(f"fact {_fact}", ())
    TYPES[f"difference {_fact}"] = {
        **TYPES.get(f"fact {_fact}", {}),
        "basis": "string",
        "inferred_from": "string",
    }

# The claims drawn: plain read and the build checks, which every build claims (`check_build`), and of the
# other suites any but the three item 12 names, whose members a declaration drawn here holds only as planted.
QUIET_SUITES: tuple[Suite, ...] = (
    "hash",
    "fits_and_reference_data",
    "table_evaluation",
    "mixing",
    "family_evaluation",
    "record_checks",
    "engine_adapter",
)
SCENE: Suite = "scene_documents"
USD: Suite = "usd_read"
SAMPLING: Suite = "sampling"


class Planted(NamedTuple):
    """A fault planted: its name, which the property tests map to the rules the text gives it; the pointer the
    refusal paragraph gives it; for a missing member or none of a place's exclusive alternatives, which; and,
    for a fault whose rules turn on the rest of its model (item 7's) or of the declaration (item 8's, the
    `population_level` rule's, item 12's sparing), what the oracle reads of them."""

    fault: str
    pointer: str
    aspect: str | None = None
    facts: tuple[tuple[str, object], ...] = ()


class Drawn(NamedTuple):
    """A declaration the text takes, the same with faults planted (a value, or a text that is not JSON), the
    faults, the draw's first choice (`way`, a feature) and second (`kind`, by chance), and the claims. For
    HP42, `without` is the planted declaration without the member a build cannot check, `suite` the suite that
    checks that member, and `beside` the number of the faults, first among them, planted beside it."""

    valid: Json
    declaration: JsonValue | bytes
    planted: tuple[Planted, ...]
    way: str
    kind: str
    claims: frozenset[Suite]
    without: Json | None = None
    suite: Suite | None = None
    beside: int = 0


def pointer(*tokens: str | int) -> str:
    """A JSON pointer (RFC 6901): each token after a `/`, `~` written `~0` and `/` written `~1`."""
    return "".join("/" + str(token).replace("~", "~0").replace("/", "~1") for token in tokens)


def floats(low: float, high: float) -> st.SearchStrategy[float]:
    return st.floats(low, high, allow_nan=False, allow_infinity=False)


def whole(low: int, high: int) -> st.SearchStrategy[float]:
    """A whole number as JSON reads one, a double."""
    return st.integers(low, high).map(float)


def scale(condition: str) -> tuple[float, float]:
    return SCALES.get(condition, (0.0, 1.0))


def section_of(field: str) -> str:
    return field.partition(".")[0]


# Texts: a `reason` or `basis` is "a string of at least one character", which nothing else judges, so a
# space, a tab, a degree sign and a long one are drawn beside short text.
TEXTS = st.one_of(
    st.sampled_from((" ", "\t\n", "about 2 % per kelvin near 37 °C", "recalled", "x" * 120)),
    st.text(st.characters(codec="utf-8"), min_size=1, max_size=12),
)
NAMES = st.text(st.characters(codec="utf-8"), max_size=8)
VERSIONS = st.sampled_from(("0.3.0", "1.0.0", "2.1", ""))
HASHES = st.sampled_from((records.WELL_FORMED_HASH, "sha256:...", "sha256:" + "f" * 64))
# `stores.py`'s identities, each pinned by one of three hashes: nine references.
PINS = (records.WELL_FORMED_HASH, *stores.STALE)
REFERENCES: tuple[Json, ...] = tuple(
    {"id": identity, "version": version, "content_hash": pin}
    for identity, version in stores.IDENTITIES
    for pin in PINS
)
REFERENCE = st.sampled_from(REFERENCES).map(copy.deepcopy)
# Names of no member at any place, each more than one slip from every name the shape table gives, written with
# the characters a pointer escapes.
UNKNOWN_NAMES = (
    "an_unknown_member_of_this_place",
    "colour/depth~of the member",
    "~1~0 written as it stands",
    "x_unknown_member_x_unknown_member",
)
ANY_VALUES: tuple[JsonValue, ...] = ("x", 1.0, True, None, [], {"a": 1.0}, [1.0, "y"])
OTHER_TYPES: dict[str, tuple[JsonValue, ...]] = {
    "string": (1.0, True, None, ["x"], {"x": "y"}),
    "number": (True, "1.0", False, None, True, [1.0], {"value": 1.0}),
    "object": ("x", 1.0, True, None, [], [{"a": 1.0}]),
    "list": ("x", 1.0, False, None, {}, {"0": "x"}),
}


def other_type(kind: str) -> st.SearchStrategy[JsonValue]:
    """A value of a JSON type other than `kind`'s: a boolean among a number's, which is no number."""
    return st.sampled_from(OTHER_TYPES[kind]).map(copy.deepcopy)


def any_value() -> st.SearchStrategy[JsonValue]:
    return st.sampled_from(ANY_VALUES).map(copy.deepcopy)


# The pieces of a valid declaration.


@st.composite
def numeric_value(draw: st.DrawFn, condition: str, *, implied: bool = False) -> Json:
    """`{"value", "unit"}` or `{"range": [lo, hi], "unit"}` in the condition's registered unit, `lo` not above
    `hi` (equal in about one draw in eight); for an implied condition's value, a `basis` beside it in one draw
    in four, which section 4.1's row ignores."""
    low, high = scale(condition)
    held: Json
    if draw(st.booleans()):
        held = {"value": draw(floats(low, high))}
    else:
        first = draw(floats(low, high))
        second = first if draw(st.integers(0, 7)) == 0 else draw(floats(low, high))
        held = {"range": [min(first, second), max(first, second)]}
    held["unit"] = UNITS[condition]
    if implied and draw(st.integers(0, 3)) == 0:
        held["basis"] = draw(any_value())
    return held


@st.composite
def operating_conditions(draw: st.DrawFn) -> Json:
    names = draw(st.lists(st.sampled_from(NUMERIC), max_size=3, unique=True))
    return {name: draw(numeric_value(name)) for name in names}


@st.composite
def requirement_condition(draw: st.DrawFn, condition: str) -> Json:
    """A requirement condition (the shape table's row): a tolerance, not below zero (zero in about one draw in
    four), in the condition's unit, for a numeric condition; an accept list of the row's tokens for a token
    one; its `reason`; and a `consequence` or none."""
    held: Json
    if condition in NUMERIC:
        low, high = scale(condition)
        tolerance = draw(st.one_of(st.just(0.0), floats(0.0, (high - low) / 10)))
        held = {"tolerance": {"value": tolerance, "unit": UNITS[condition]}}
    else:
        tokens = CONDITION_TOKENS[condition]
        held = {"accept": list(draw(st.lists(st.sampled_from(tokens), min_size=1, max_size=3, unique=True)))}
    held["reason"] = draw(TEXTS)
    if draw(st.booleans()):
        held["consequence"] = draw(NAMES)
    return held


@st.composite
def requirement(draw: st.DrawFn, field: str, *, labelled: bool | None = None) -> Json:
    """A requirement for `field`: its `want`; conditions or none; the field's registered label or none, and
    `review` or none (`labelled` True gives both, False neither)."""
    held: Json = {"field": field, "want": draw(st.sampled_from(WANTS))}
    if draw(st.booleans()):
        names = draw(st.lists(st.sampled_from(CONDITIONS), max_size=2, unique=True))
        held["conditions"] = {name: draw(requirement_condition(name)) for name in names}
    if field in LABELS and (labelled or (labelled is None and draw(st.booleans()))):
        held["label"] = LABELS[field]
    if labelled or (labelled is None and draw(st.booleans())):
        held["review"] = REVIEW
    return held


@st.composite
def fact(draw: st.DrawFn, name: str, *, difference: bool = False) -> Json:
    """A fact in its shape of `provenance.md` section 6.2 without `basis`, its text members present or not;
    for an accepted difference's `value`, with a `basis` or none, and `inferred_from` or none where the row
    leaves the basis open."""
    held: Json = {}
    for member, kind in FACT_MEMBERS[name].items():
        if kind == "text":
            if draw(st.booleans()):
                held[member] = draw(NAMES)
        elif kind == "token":
            held[member] = draw(st.sampled_from(VOCABULARY.facts[name].tokens))
        elif kind == "integer":
            held[member] = draw(whole(1, 10**7))
        elif kind == "uberon":
            held[member] = "UBERON:" + draw(st.text("0123456789", min_size=1, max_size=7))
        elif kind == "number":
            held[member] = draw(floats(0.0, 3.0e9))
        else:
            held[member] = VOCABULARY.facts[name].fixed["unit"]
    if name == "donor_age" and draw(st.booleans()):
        first, second = draw(floats(0.0, 3.0e9)), draw(floats(0.0, 3.0e9))
        del held["value"]
        held["range"] = [min(first, second), max(first, second)]
    if difference:
        fixed = VOCABULARY.facts[name].fixed.get("basis")
        if draw(st.booleans()):
            held["basis"] = fixed if fixed is not None else draw(st.sampled_from(FACT_BASES))
        if fixed is None and draw(st.booleans()):
            held["inferred_from"] = draw(NAMES)
    return held


@st.composite
def status_object(draw: st.DrawFn) -> Json:
    """A status object (`provenance.md` section 1): `status`, and a `reason` or none."""
    held: Json = {"status": draw(st.sampled_from(STATUS_TOKENS))}
    if draw(st.booleans()):
        held["reason"] = draw(NAMES)
    return held


@st.composite
def implied_value(draw: st.DrawFn, condition: str) -> Json:
    """An implied condition's value (section 4.1's row): a numeric condition's `{"value", "unit"}` or
    `{"range", "unit"}`, a token condition's `{"token"}` of its row, a `basis` beside it in some draws."""
    if condition in NUMERIC:
        return draw(numeric_value(condition, implied=True))
    held: Json = {"token": draw(st.sampled_from(CONDITION_TOKENS[condition]))}
    if draw(st.integers(0, 3)) == 0:
        held["basis"] = draw(any_value())
    return held


@st.composite
def acceptance(
    draw: st.DrawFn,
    kind: str,
    fields: Sequence[str],
    *,
    location: str | None = "record",
    labelled: Sequence[str] = (),
) -> Json:
    """An acceptance of `kind` its row allows (section 4.1, the shape table's own members cell), covering one
    of `fields` where its kind names a field, located at a record (`location` "record"), a region or an
    interval, or at none (None); a pick at its record wherever else it is located, but where `location` is
    None. A waiver covering one of `labelled` names that field's label in about half its draws."""
    held: Json = {"acceptance": kind}
    if location == "record" or (kind == "pick" and location is not None):
        held["record"] = draw(REFERENCE)
    if location == "region":
        held["region"] = draw(NAMES)
    elif location == "interval":
        held["interval"] = draw(st.one_of(whole(0, 3), NAMES))
    if kind not in ("accepted_difference", "overlay_scope"):
        held["field"] = draw(st.sampled_from(fields))
    if kind == "pick":
        held["index"] = draw(whole(0, 4))
    elif kind == "waiver":
        code = draw(st.sampled_from(WAIVED_CONDITION_CODES if draw(st.booleans()) else OTHER_CODES))
        held["code"] = code
        if code in CONDITION_CODES:
            held["condition"] = draw(st.sampled_from(CONDITIONS))
        if held["field"] in labelled and draw(st.booleans()):
            held["label"] = LABELS[str(held["field"])]
    elif kind == "implied_condition":
        name = draw(st.sampled_from(FACTS_WITH_TOKENS))
        held["fact"] = name
        held["token"] = draw(st.sampled_from(VOCABULARY.facts[name].tokens))
        implied = draw(st.lists(st.sampled_from(CONDITIONS), max_size=2, unique=True))
        held["implies"] = {condition: draw(implied_value(condition)) for condition in implied}
    elif kind == "accepted_difference":
        held["section"] = draw(st.sampled_from(SECTIONS))
        name = draw(st.sampled_from(FACTS))
        held["fact"] = name
        way = draw(st.integers(0, 3))
        held["value"] = (
            "any" if way == 0 else draw(status_object()) if way == 1 else draw(fact(name, difference=True))
        )
    elif kind == "extrapolation":
        held["method"] = draw(st.sampled_from(METHODS))
        held["law"] = draw(TEXTS)
    elif kind == "nominal":
        held["value"] = draw(floats(-1.0e3, 1.0e4))
    elif kind == "distribution":
        token = draw(st.sampled_from(sorted(DISTRIBUTIONS)))
        held["distribution"] = token
        held["distribution_parameters"] = {name: draw(floats(0.0, 1.0e3)) for name in DISTRIBUTIONS[token]}
        held["space"] = draw(st.sampled_from(SPACES))
    elif kind in ("overlay", "overlay_scope"):
        held["overlay"] = draw(REFERENCE)
        if kind == "overlay_scope":
            held["accepts"] = list(
                draw(st.lists(st.sampled_from(ACCEPTS), min_size=1, max_size=3, unique=True))
            )
    held["reason"] = draw(TEXTS)
    if kind in BASIS_KINDS:
        held["basis"] = draw(TEXTS)
    return held


@st.composite
def chain(draw: st.DrawFn) -> Json:
    """A chain (section 6): `from`, `event`, `to` and `state_mapping`, each end a family and a record."""

    def end() -> Json:
        return {"family": draw(NAMES), "record": draw(REFERENCE)}

    names = draw(st.lists(NAMES, max_size=2, unique=True))
    return {
        "from": end(),
        "event": draw(NAMES),
        "to": end(),
        "state_mapping": {name: draw(NAMES) for name in names},
    }


@st.composite
def combinations(draw: st.DrawFn, reads: Sequence[str], size: Size) -> list[JsonValue]:
    """Combinations of two or more fields in `reads`, each from a different section."""
    by_section: dict[str, list[str]] = {}
    for field in reads:
        by_section.setdefault(section_of(field), []).append(field)
    if len(by_section) < 2:
        return []
    found: list[JsonValue] = []
    for _ in range(draw(st.integers(0, 1 if size.members <= 3 else 2))):
        sections = draw(st.lists(st.sampled_from(sorted(by_section)), min_size=2, max_size=3, unique=True))
        found.append([draw(st.sampled_from(by_section[section])) for section in sections])
    return found


def located_or_not(kind: str) -> st.SearchStrategy[str | None]:
    """Where a valid acceptance of `kind` is located: at none for an overlay and an `overlay_scope` ("none");
    at a record or none for an accepted difference ("optional: absent, every location the model is checked
    over"); at a record for the others."""
    if kind in ("overlay", "overlay_scope"):
        return st.none()
    if kind == "accepted_difference":
        return st.sampled_from(("record", None))
    return st.just("record")


@st.composite
def model_entry(draw: st.DrawFn, name: str, size: Size) -> Json:
    """A model entry over records (section 1's rows), each optional member present or absent; two `trainable`
    entries of one field at two records among them, which the text allows ("no other entry names that field
    there", section 7)."""
    listed = list(draw(st.lists(st.sampled_from(REFERENCES), min_size=1, max_size=3, unique_by=json.dumps)))
    reads = list(draw(st.lists(st.sampled_from(FIELDS), min_size=1, max_size=4, unique=True)))
    target_facts = draw(st.lists(st.sampled_from(FACTS), max_size=min(4, size.members - 1), unique=True))
    entry: Json = {
        "model": {"name": name, "version": draw(VERSIONS)},
        "model_configuration_hash": draw(HASHES),
        "checked_over": {"records": cast(list[JsonValue], copy.deepcopy(listed))},
        "target": {fact_name: draw(fact(fact_name)) for fact_name in target_facts},
        "reads": cast(list[JsonValue], list(reads)),
        "consumer_parameters": cast(list[JsonValue], list(draw(st.lists(NAMES, max_size=2)))),
        "families": {},
        "combinations": draw(combinations(reads, size)),
        "chains": cast(list[JsonValue], [draw(chain()) for _ in range(draw(st.integers(0, 1)))]),
    }
    if draw(st.booleans()):
        required = draw(st.lists(st.sampled_from(reads), max_size=len(reads), unique=True))
        entry["requirements"] = [draw(requirement(field)) for field in required]
    labelled = [
        str(held["field"])
        for held in cast(list[Json], entry.get("requirements", []))
        if "label" in held and held.get("review") == REVIEW
    ]
    if draw(st.booleans()):
        kinds = draw(st.lists(st.sampled_from(CHECKED_KINDS), max_size=size.members))
        covered = reads + [field for field in FIELDS if field not in reads][:1]
        entry["acceptances"] = [
            draw(acceptance(kind, covered, location=draw(located_or_not(kind)), labelled=labelled))
            for kind in kinds
        ]
    if draw(st.booleans()):
        entry["mixing"] = {
            "fraction_sum_tolerance": draw(st.one_of(st.just(0.0), floats(0.0, 1.0e-3))),
            "rules": {
                field: draw(st.sampled_from(MIXING_RULES))
                for field in draw(st.lists(st.sampled_from(FIELDS), max_size=2, unique=True))
            },
        }
    if draw(st.booleans()):
        pairs = [(field, json.dumps(reference)) for field in reads for reference in listed]
        chosen = draw(st.lists(st.sampled_from(pairs), max_size=2, unique=True))
        entry["trainable"] = [
            {"field": field, "record": json.loads(reference)} for field, reference in chosen
        ]
    if draw(st.booleans()):
        entry["precision"] = draw(st.sampled_from(PRECISIONS))
    return entry


@st.composite
def claims(draw: st.DrawFn) -> frozenset[Suite]:
    others = draw(st.lists(st.sampled_from(QUIET_SUITES), max_size=3, unique=True))
    return frozenset({"plain_read", "build_checks", *others})


@st.composite
def declarations(draw: st.DrawFn, size: Size) -> Json:
    """A declaration the text takes, of one to three models of distinct names."""
    count = draw(st.integers(1, 3))
    names = draw(st.lists(NAMES, min_size=count, max_size=count, unique=True))
    return {
        "consumer": {"name": draw(NAMES), "version": draw(VERSIONS)},
        "operating_conditions": draw(operating_conditions()),
        "models": [draw(model_entry(name, size)) for name in names],
    }


# Planting.


class Planting:
    """A copy of a valid declaration being planted, the draw, and the faults planted in it so far; `replaced`,
    where a planter puts a text that is not JSON, or a value that is not an object, in the declaration's
    place, that text or value alone in a tuple."""

    def __init__(self, draw: st.DrawFn, valid: Json) -> None:
        self.draw = draw
        self.declaration: Json = copy.deepcopy(valid)
        self.planted: list[Planted] = []
        self.kinds: list[str] = []
        self.replaced: tuple[JsonValue | bytes] | None = None

    def plant(
        self, fault: str, at: str, aspect: str | None = None, facts: tuple[tuple[str, object], ...] = ()
    ) -> None:
        self.planted.append(Planted(fault, at, aspect, facts))

    @property
    def models(self) -> list[Json]:
        return cast(list[Json], self.declaration["models"])

    def model_index(self) -> int:
        return self.draw(st.integers(0, len(self.models) - 1))

    def choose(self, options: Sequence[str]) -> str:
        return self.draw(st.sampled_from(options))

    def index(self, count: int) -> int:
        return self.draw(st.integers(0, count - 1))


def entries(model: Json, member: str) -> list[JsonValue]:
    """`model[member]`, a list, made empty where the model holds none."""
    return cast(list[JsonValue], model.setdefault(member, []))


def requirements_of(model: Json) -> list[Json]:
    return cast(list[Json], model.get("requirements", []))


def acceptances_of(model: Json) -> list[Json]:
    return cast(list[Json], model.get("acceptances", []))


def reads_of(model: Json) -> list[str]:
    return cast(list[str], model["reads"])


def registered_reads(model: Json) -> list[str]:
    """The registered fields a model reads: those a planter covers or requires, never an entry of `reads`
    another planter put at fault."""
    return [field for field in reads_of(model) if field in FIELDS]


def records_of(model: Json) -> list[Json]:
    return cast(list[Json], cast(Json, model["checked_over"])["records"])


def labelled_waivers(model: Json, field: str) -> list[int]:
    """The positions of the waivers that name a `label` and cover `field`: each rests on its requirement."""
    return [
        position
        for position, held in enumerate(acceptances_of(model))
        if held.get("acceptance") == "waiver" and "label" in held and held.get("field") == field
    ]


def required_fields(model: Json) -> set[str]:
    return {str(held.get("field")) for held in requirements_of(model)}


def unrequired_reads(model: Json) -> list[str]:
    return [field for field in registered_reads(model) if field not in required_fields(model)]


def unread(model: Json) -> list[str]:
    """The registered fields a model neither reads nor requires anything of."""
    return [field for field in FIELDS if field not in reads_of(model) and field not in required_fields(model)]


def some_requirement(p: Planting, m: int, *, free: bool = False) -> tuple[int, Json]:
    """A requirement of model `m` for a field it reads, and its position: one it holds, or one appended for a
    field it reads and requires nothing of, a field appended to `reads` for it where there is none; with
    `free`, one whose field no labelled waiver rests on."""
    model = p.models[m]
    held = [
        (position, item)
        for position, item in enumerate(requirements_of(model))
        if item.get("field") in reads_of(model) and not (free and labelled_waivers(model, str(item["field"])))
    ]
    if held:
        return held[p.index(len(held))]
    fields = [field for field in unrequired_reads(model) if not labelled_waivers(model, field)]
    if not fields:
        fields = [p.choose(unread(model))]
        reads_of(model).append(fields[0])
    item = p.draw(requirement(p.choose(fields), labelled=False))
    listed = entries(model, "requirements")
    listed.append(item)
    return len(listed) - 1, item


def append_acceptance(p: Planting, m: int, kind: str, *, location: str | None = "record") -> tuple[str, Json]:
    """A valid acceptance of `kind` appended to model `m`, and its pointer: an overlay and an `overlay_scope`
    at no location whatever `location` says. A distribution, and an acceptance located at a region or an
    interval, are members item 12 refuses where the build claims neither the sampling suite nor the scene
    suite, planted as such."""
    model = p.models[m]
    if kind in ("overlay", "overlay_scope"):
        location = None
    held = p.draw(acceptance(kind, registered_reads(model), location=location))
    listed = entries(model, "acceptances")
    listed.append(held)
    at = pointer("models", m, "acceptances", len(listed) - 1)
    if kind == "distribution":
        p.plant("sampling_member", at)
    if location in ("region", "interval"):
        p.plant("scene_member", at)
    return at, held


def planted_under(p: Planting, at: str) -> bool:
    """Whether a fault is planted at `at` or inside the member it names."""
    return any(fault.pointer == at or fault.pointer.startswith(at + "/") for fault in p.planted)


def free_operating(p: Planting) -> list[str]:
    """The numeric conditions no planted fault holds in `operating_conditions`."""
    return [name for name in NUMERIC if not planted_under(p, pointer("operating_conditions", name))]


def condition_at(p: Planting, m: int, names: Sequence[str]) -> tuple[str, Json, Json]:
    """A requirement condition of one of `names` set on a requirement of model `m` (a condition there of that
    name replaced), its pointer, and the condition and requirement. A name already planted at is left
    alone."""
    j, held = some_requirement(p, m)
    conditions = cast(Json, held.setdefault("conditions", {}))
    here = pointer("models", m, "requirements", j, "conditions")

    def planted_at(name: str) -> bool:
        at = here + pointer(name)
        return any(fault.pointer == at or fault.pointer.startswith(at + "/") for fault in p.planted)

    free = [name for name in names if not planted_at(name)]
    name = p.choose(free or names)
    conditions[name] = p.draw(requirement_condition(name))
    return pointer("models", m, "requirements", j, "conditions", name), cast(Json, conditions[name]), held


# HP41's `reasons`: items 3 and 4, and the shape table's "a string of at least one character".


def plant_condition_without_reason(p: Planting, numeric: bool) -> None:
    """Item 3: a tolerance (numeric) or an accept list (token) without its `reason`."""
    at, condition, _ = condition_at(p, p.model_index(), NUMERIC if numeric else TOKEN_CONDITIONS)
    del condition["reason"]
    p.kinds.append(at.rpartition("/")[2])
    p.plant("condition_without_reason", at, "reason")


def plant_acceptance_without_reason(p: Planting) -> None:
    """Item 4: an acceptance, of a kind by chance, without its `reason`."""
    kind = p.choose(KINDS)
    p.kinds.append(kind)
    at, held = append_acceptance(p, p.model_index(), kind)
    del held["reason"]
    p.plant("acceptance_without_reason", at, "reason")


def plant_basis_missing(p: Planting) -> None:
    """Item 4: an extrapolation, a nominal or a distribution without its `basis`."""
    kind = p.choose(BASIS_KINDS)
    p.kinds.append(kind)
    at, held = append_acceptance(p, p.model_index(), kind)
    del held["basis"]
    p.plant("acceptance_without_basis", at, "basis")


def plant_empty_text(p: Planting) -> None:
    """The shape table's "a string of at least one character": an empty `reason` (a requirement condition's,
    or an acceptance's of a kind by chance), `basis` or extrapolation `law`, refused at that member."""
    place = p.choose(("condition reason", "acceptance reason", "basis", "law"))
    p.kinds.append(place)
    m = p.model_index()
    if place == "condition reason":
        at, condition, _ = condition_at(p, m, CONDITIONS)
        condition["reason"] = ""
        p.plant("empty_text", at + "/reason")
        return
    kind = {"acceptance reason": p.choose(KINDS), "basis": p.choose(BASIS_KINDS), "law": "extrapolation"}[
        place
    ]
    member = {"acceptance reason": "reason", "basis": "basis", "law": "law"}[place]
    at, held = append_acceptance(p, m, kind)
    held[member] = ""
    p.plant("empty_text", f"{at}/{member}")


REASONS: dict[str, Callable[[Planting], None]] = {
    "tolerance_reason": lambda p: plant_condition_without_reason(p, numeric=True),
    "accept_reason": lambda p: plant_condition_without_reason(p, numeric=False),
    "acceptance_reason": plant_acceptance_without_reason,
    "basis": plant_basis_missing,
    "empty_text": plant_empty_text,
}


# `locations`: section 4.1's location column and its rule.


def plant_unlocated(p: Planting) -> None:
    """Section 4.1: "An acceptance whose kind needs a location and names none is refused": an acceptance of
    each kind that needs one, each kind in about half the draws and one at least; a pick's location is its
    record, so one naming a region or an interval and no record is unlocated too (maintainer, 2026-10-24)."""
    kinds = ("pick", *LOCATED_KINDS)
    for kind in [kind for kind in kinds if p.draw(st.booleans())] or [p.choose(kinds)]:
        at, held = append_acceptance(p, p.model_index(), kind, location=None)
        if kind == "pick":
            named = p.choose(("nothing", "region", "interval"))
            if named != "nothing":
                held[named] = "lumen" if named == "region" else 0.0
            p.kinds.append(f"pick naming {named}")
            p.plant("unlocated_pick", at, "record")
        else:
            p.kinds.append(kind)
            p.plant("unlocated", at, "location")


def plant_needs_none(p: Planting, kinds: Sequence[str]) -> None:
    """A near miss the text takes: an accepted difference ("optional: absent, every location the model is
    checked over"), an overlay or an `overlay_scope` ("none") naming no location."""
    kind = p.choose(kinds)
    p.kinds.append(kind)
    append_acceptance(p, p.model_index(), kind, location=None)


def plant_located(p: Planting) -> None:
    """A kind that needs a location naming one, its kind by chance: at a record, which the text takes, or at a
    region or an interval, which item 12 refuses where the scene suite is not claimed; a pick at its record
    and a region or an interval beside it, "both being its location too"."""
    kind = p.choose(("pick", "accepted_difference", *LOCATED_KINDS))
    where = p.choose(("record", "region", "interval"))
    p.kinds.append(f"{kind} at a {where}")
    append_acceptance(p, p.model_index(), kind, location=where)


LOCATIONS: dict[str, Callable[[Planting], None]] = {
    "unlocated": plant_unlocated,
    "accepted_difference_unlocated": lambda p: plant_needs_none(p, ("accepted_difference",)),
    "overlay_unlocated": lambda p: plant_needs_none(p, ("overlay", "overlay_scope")),
    "located": plant_located,
}


# `shape`: section 1's list of departures, at any depth.


class Site(NamedTuple):
    """An object of the declaration at its place, and its pointer."""

    place: str
    pointer: str
    value: Json


def sites(declaration: Json) -> list[Site]:
    """Every object of a declaration drawn here at its place: the declaration, its consumer and operating
    conditions, each model entry and what it holds. A model's listed records are left out, since a
    `trainable` entry rests on them, and so is a model entry or a list that is no longer of its type."""
    found = [Site("declaration", "", declaration)]
    if isinstance(declaration.get("consumer"), dict):
        found.append(Site("consumer", "/consumer", cast(Json, declaration["consumer"])))
    for name, held in cast(Json, declaration.get("operating_conditions", {})).items():
        if isinstance(held, dict) and name in NUMERIC:
            found.append(Site("operating condition", pointer("operating_conditions", name), held))
    models = declaration.get("models")
    for m, model in enumerate(models if isinstance(models, list) else []):
        if isinstance(model, dict):
            found += model_sites(m, model)
    return found


def model_sites(m: int, model: Json) -> list[Site]:
    at = pointer("models", m)
    found = [Site("model entry", at, model)]
    for member, place in (("model", "model"), ("checked_over", "checked over"), ("mixing", "mixing")):
        if isinstance(model.get(member), dict):
            found.append(Site(place, f"{at}/{member}", cast(Json, model[member])))
    for name, held in cast(Json, model.get("target", {})).items():
        if isinstance(held, dict) and f"fact {name}" in NAMED:
            found.append(Site(f"fact {name}", pointer("models", m, "target", name), held))
    for j, held in enumerate(requirements_of(model)):
        here = pointer("models", m, "requirements", j)
        found.append(Site("requirement", here, held))
        for name, condition in cast(Json, held.get("conditions", {})).items():
            if name not in CONDITIONS:
                continue
            inside = here + pointer("conditions", name)
            found.append(Site("requirement condition", inside, cast(Json, condition)))
            if isinstance(cast(Json, condition).get("tolerance"), dict):
                found.append(
                    Site("tolerance", inside + "/tolerance", cast(Json, cast(Json, condition)["tolerance"]))
                )
    for k, held in enumerate(acceptances_of(model)):
        found += acceptance_sites(pointer("models", m, "acceptances", k), held)
    for k, held in enumerate(cast(list[Json], model.get("trainable", []))):
        found.append(Site("trainable entry", pointer("models", m, "trainable", k), held))
    for k, held in enumerate(cast(list[Json], model.get("chains", []))):
        here = pointer("models", m, "chains", k)
        found.append(Site("chain", here, held))
        for end in ("from", "to"):
            found.append(Site("chain end", f"{here}/{end}", cast(Json, held[end])))
            found.append(
                Site(
                    "material reference", f"{here}/{end}/record", cast(Json, cast(Json, held[end])["record"])
                )
            )
    return found


def acceptance_sites(at: str, held: Json) -> list[Site]:
    kind = held.get("acceptance")
    place = kind if isinstance(kind, str) and kind in KINDS else "acceptance"
    found = [Site(place, at, held)]
    for name in ("record", "overlay"):
        if isinstance(held.get(name), dict):
            found.append(Site("material reference", f"{at}/{name}", cast(Json, held[name])))
    if place == "implied_condition":
        for name, value in cast(Json, held.get("implies", {})).items():
            if isinstance(value, dict) and "status" not in value and name in CONDITIONS:
                implied = "implied numeric" if name in NUMERIC else "implied token"
                found.append(Site(implied, at + pointer("implies", name), value))
    difference, its_fact = held.get("value"), held.get("fact")
    if place == "accepted_difference" and isinstance(difference, dict):
        if "status" in difference:
            found.append(Site("status object", f"{at}/value", difference))
        elif isinstance(its_fact, str) and its_fact in FACTS:
            found.append(Site(f"difference {its_fact}", f"{at}/value", difference))
    return found


def changeable(declaration: Json) -> list[Site]:
    """The sites a member is added to or taken out of: every one but a status object, which a member added or
    taken out would make an object of another place."""
    return [site for site in sites(declaration) if site.place != "status object"]


def model_of(at: str) -> int | None:
    parts = at.split("/")
    return int(parts[2]) if len(parts) > 2 and parts[1] == "models" else None


def rests_on(p: Planting, site: Site, member: str) -> bool:
    """Whether another member rests on `member` of `site`: a labelled waiver on its requirement's `field`,
    `label` or `review`, or on its model's `requirements`; a waiver's `label` on its own `field`."""
    m = model_of(site.pointer)
    model = p.models[m] if m is not None else {}
    if site.place == "requirement" and member in ("field", "label", "review"):
        return bool(labelled_waivers(model, str(site.value.get("field"))))
    if site.place == "model entry" and member == "requirements":
        return any(labelled_waivers(model, field) for field in FIELDS)
    return site.place == "waiver" and member in ("field", "label") and "label" in site.value


def removed(p: Planting, site: Site, member: str) -> None:
    """`member` taken out of `site`, and the faults that leaves: a required member missing; none of a place's
    exclusive alternatives; an acceptance's or a requirement condition's `reason` (items 4 and 3); a `basis`
    (item 4); an acceptance's location (BC-037); a waiver's `condition` where its code names one. An optional
    member taken out leaves none."""
    value, place, at = site.value, site.place, site.pointer
    del value[member]
    alternatives = EXCLUSIVE.get(place, ())
    if member in alternatives:
        if not any(name in value for name in alternatives):
            p.plant("missing_member", at, "|".join(alternatives))
    elif member == "reason" and place == "requirement condition":
        p.plant("condition_without_reason", at, "reason")
    elif member == "reason" and place in KINDS:
        p.plant("acceptance_without_reason", at, "reason")
    elif member == "basis" and place in BASIS_KINDS:
        p.plant("acceptance_without_basis", at, "basis")
    elif member == "record" and place == "pick":
        p.plant("unlocated_pick", at, "record")
    elif member in _LOCATION and place in LOCATED_KINDS:
        if not any(name in value for name in _LOCATION):
            p.plant("unlocated", at, "location")
    elif member == "condition" and place == "waiver":
        if value.get("code") in CONDITION_CODES:
            p.plant("missing_member", at, "condition")
    elif member in REQUIRED.get(place, ()):
        p.plant("missing_member", at, member)


def removable(p: Planting, site: Site, *, texts: bool) -> list[str]:
    """The members of `site` the shape part takes out: those whose absence is a fault of the shape table, and
    with `texts` also `reason`, `basis`, a waiver's `condition` and a location, whose absence is a rule's;
    none another member rests on."""
    wanted = {*REQUIRED.get(site.place, ()), *EXCLUSIVE.get(site.place, ())}
    if site.place == "waiver" and site.value.get("code") in CONDITION_CODES:
        # "`condition` where the code names one": required there.
        wanted.add("condition")
    if texts:
        wanted |= {"reason", "basis", "condition", *_LOCATION}
    return [member for member in site.value if member in wanted and not rests_on(p, site, member)]


def plant_missing(p: Planting) -> None:
    """A required member missing, which by chance from the shape table, or none of a place's exclusive
    alternatives, refused at the object that should hold it; `target` in about one draw in six (the design's
    mutant "a required member's absence taken (`target`)")."""
    if p.draw(st.integers(0, 5)) == 0:
        m = p.model_index()
        p.kinds.append("model entry: target")
        removed(p, Site("model entry", pointer("models", m), p.models[m]), "target")
        return
    candidates = [site for site in changeable(p.declaration) if removable(p, site, texts=False)]
    site = candidates[p.index(len(candidates))]
    members = removable(p, site, texts=False)
    member = members[p.index(len(members))]
    p.kinds.append(f"{site.place}: {member}")
    removed(p, site, member)


def plant_other_type(p: Planting) -> None:
    """A member of another JSON type than its row's, the type it holds by chance and a boolean among a
    number's others, refused at it and nothing inside it checked; in one draw in five an entry of another type
    appended to a list whose entries something rests on (`reads`, `checked_over.records`) or none
    (`consumer_parameters`)."""
    if p.draw(st.integers(0, 4)) == 0:
        name = p.choose(("reads", "records", "consumer_parameters"))
        m = p.model_index()
        model = p.models[m]
        listed = cast(list[JsonValue], records_of(model) if name == "records" else model[name])
        listed.append(p.draw(other_type("object" if name == "records" else "string")))
        p.kinds.append(f"an entry of {name}")
        path = ("checked_over", "records") if name == "records" else (name,)
        p.plant("holds", pointer("models", m, *path, len(listed) - 1))
        return
    candidates = [
        (site, member)
        for site in sites(p.declaration)
        for member in site.value
        if member in TYPES.get(site.place, {}) and not rests_on(p, site, member)
    ]
    # The type a member holds first, then a member of that type, so that a number, which few members hold,
    # is drawn as often as a string.
    kinds = [
        kind
        for kind in ("number", "string", "object", "list")
        if any(TYPES[site.place][member] == kind for site, member in candidates)
    ]
    kind = p.choose(kinds)
    of_kind = [(site, member) for site, member in candidates if TYPES[site.place][member] == kind]
    site, member = of_kind[p.index(len(of_kind))]
    p.kinds.append(f"{site.place}: {member}")
    site.value[member] = p.draw(other_type(kind))
    p.plant("holds", site.pointer + pointer(member))


def plant_range_upside_down(p: Planting) -> None:
    """ "a `range` whose `lo` is above its `hi`": an operating condition's or an implied condition's."""
    free = free_operating(p)
    name = p.choose(free or NUMERIC)
    low, high = scale(name)
    upside_down: Json = {"range": [high, low if low < high else high - 1.0], "unit": UNITS[name]}
    if len(free) > 0 and p.draw(st.booleans()):
        cast(Json, p.declaration["operating_conditions"])[name] = upside_down
        p.kinds.append("an operating condition's range")
        p.plant("holds", pointer("operating_conditions", name, "range"))
        return
    at, held = append_acceptance(p, p.model_index(), "implied_condition")
    cast(Json, held["implies"])[name] = upside_down
    p.kinds.append("an implied condition's range")
    p.plant("holds", at + pointer("implies", name, "range"))


def plant_below_zero(p: Planting) -> None:
    """ "a number below zero": a tolerance's value, or a `fraction_sum_tolerance`."""
    m = p.model_index()
    below = -p.draw(st.sampled_from((5.0e-324, 0.5, 2.0)))
    if p.draw(st.booleans()):
        at, condition, _ = condition_at(p, m, NUMERIC)
        cast(Json, condition["tolerance"])["value"] = below
        p.kinds.append("a tolerance")
        p.plant("holds", at + "/tolerance/value")
        return
    p.models[m]["mixing"] = {"fraction_sum_tolerance": below, "rules": {}}
    p.kinds.append("a fraction_sum_tolerance")
    p.plant("holds", pointer("models", m, "mixing", "fraction_sum_tolerance"))


def plant_index_off(p: Planting) -> None:
    """A pick's `index`, "a whole number not below zero", with a fractional part or below zero."""
    at, held = append_acceptance(p, p.model_index(), "pick")
    held["index"] = p.draw(st.sampled_from((0.5, 1.25, 2.0000000000000004, -1.0)))
    p.kinds.append("an index")
    p.plant("holds", at + "/index")


def plant_combination(p: Planting) -> None:
    """ "a combination of fewer than two fields or of fields of one section", each in `reads`."""
    m = p.model_index()
    model = p.models[m]
    reads = reads_of(model)
    if p.draw(st.booleans()):
        combined: list[JsonValue] = [p.choose(registered_reads(model))]
        p.kinds.append("a combination of one field")
    else:
        sections = [
            section for section in SECTIONS if sum(section_of(field) == section for field in FIELDS) > 1
        ]
        section = p.choose(sections)
        pair = [field for field in FIELDS if section_of(field) == section][:2]
        reads += [field for field in pair if field not in reads]
        combined = list(pair)
        p.kinds.append("a combination of one section")
    listed = cast(list[JsonValue], model["combinations"])
    listed.append(combined)
    p.plant("holds", pointer("models", m, "combinations", len(listed) - 1))


def plant_two_alternatives(p: Planting) -> None:
    """ "two of a member's mutually exclusive alternatives": an operating condition holding `value` and
    `range`; a requirement condition holding a tolerance and an accept list, refused at the condition and at
    the alternative its kind does not take (maintainer, 2026-10-24); a nominal's `value` beside `params`,
    which no field registered here takes (no row allows `parameter_set`), refused at the nominal and at
    `params`."""
    m = p.model_index()
    ways = ("operating condition", "requirement condition", "nominal")
    way = p.choose(ways if free_operating(p) else ways[1:])
    p.kinds.append(way)
    if way == "operating condition":
        name = p.choose(free_operating(p))
        low, _ = scale(name)
        operating = cast(Json, p.declaration["operating_conditions"])
        operating[name] = {"value": low, "range": [low, low], "unit": UNITS[name]}
        p.plant("holds", pointer("operating_conditions", name))
    elif way == "requirement condition":
        at, condition, _ = condition_at(p, m, CONDITIONS)
        name = at.rpartition("/")[2]
        if name in NUMERIC:
            condition["accept"] = ["x"]
            wrong = "accept"
        else:
            condition["tolerance"] = {"value": 1.0, "unit": "K"}
            wrong = "tolerance"
        p.plant("holds", at)
        p.plant("holds", f"{at}/{wrong}")
    else:
        at, held = append_acceptance(p, m, "nominal")
        held["params"] = {"a": 1.0}
        p.plant("holds", at)
        p.plant("holds", at + "/params")


def plant_identifier(p: Planting) -> None:
    """A target's `species` or `anatomical_site` off its row (`provenance.md` section 6.2): an NCBI Taxonomy
    identifier with a fractional part (`<integer>`), an UBERON identifier not `UBERON:<digits>`."""
    m = p.model_index()
    target = cast(Json, p.models[m]["target"])
    taxon = not planted_under(p, pointer("models", m, "target", "species"))
    if taxon and (
        planted_under(p, pointer("models", m, "target", "anatomical_site")) or p.draw(st.booleans())
    ):
        target["species"] = {"ncbi_taxon": p.draw(st.sampled_from((9606.5, 0.25)))}
        p.kinds.append("ncbi_taxon")
        p.plant("holds", pointer("models", m, "target", "species", "ncbi_taxon"))
    else:
        target["anatomical_site"] = {
            "uberon": p.choose(("UBERON:", "uberon:0002048", "UBERON:12a", "UBERON:1 "))
        }
        p.kinds.append("uberon")
        p.plant("holds", pointer("models", m, "target", "anatomical_site", "uberon"))


def plant_status_object(p: Planting) -> None:
    """A status object where none is taken, refused at the member and nothing inside it checked (maintainer,
    2026-10-24): a target's fact ("never a status object") or an implied condition's value ("never a status
    object")."""
    m = p.model_index()
    status = p.draw(status_object())
    facts = [name for name in FACTS if not planted_under(p, pointer("models", m, "target", name))]
    if len(facts) > 0 and p.draw(st.booleans()):
        name = p.choose(facts)
        cast(Json, p.models[m]["target"])[name] = status
        p.kinds.append("a target's fact")
        p.plant("holds", pointer("models", m, "target", name))
    else:
        at, held = append_acceptance(p, m, "implied_condition")
        name = p.choose(CONDITIONS)
        cast(Json, held["implies"])[name] = status
        p.kinds.append("an implied condition's value")
        p.plant("holds", at + pointer("implies", name))


def plant_waiver_condition(p: Planting) -> None:
    """A waiver's `condition` against its code: missing where the code names one (two draws in three), held
    where it names none."""
    at, held = append_acceptance(p, p.model_index(), "waiver")
    if p.draw(st.integers(0, 2)) > 0:
        held["code"] = p.choose(WAIVED_CONDITION_CODES)
        held.pop("condition", None)
        p.kinds.append("a condition code without its condition")
        p.plant("missing_member", at, "condition")
    else:
        held["code"] = p.choose(OTHER_CODES)
        held["condition"] = p.choose(CONDITIONS)
        p.kinds.append("a condition beside a code that names none")
        p.plant("holds", at + "/condition")


def plant_params(p: Planting) -> None:
    """A nominal's `params`, "only for a field whose row allows the form `parameter_set`", which no field
    registered here allows."""
    at, held = append_acceptance(p, p.model_index(), "nominal")
    del held["value"]
    held["params"] = {"a": 1.0}
    p.kinds.append("params")
    p.plant("holds", at + "/params")


def plant_distribution_parameters(p: Planting) -> None:
    """ "a distribution's parameters other than its token's": another token's, one missing or one more."""
    at, held = append_acceptance(p, p.model_index(), "distribution")
    token = str(held["distribution"])
    others = [name for name in sorted(DISTRIBUTIONS) if DISTRIBUTIONS[name] != DISTRIBUTIONS[token]]
    way = p.choose(("another token's", "one missing", "one more"))
    named = {
        "another token's": DISTRIBUTIONS[p.choose(others)],
        "one missing": DISTRIBUTIONS[token][:-1],
        "one more": (*DISTRIBUTIONS[token], "shift"),
    }[way]
    held["distribution_parameters"] = {name: 1.0 for name in named}
    p.kinds.append(f"distribution parameters, {way}")
    p.plant("holds", at + "/distribution_parameters")


CONSTRAINTS: dict[str, Callable[[Planting], None]] = {
    "waiver_condition": plant_waiver_condition,
    "status_object": plant_status_object,
    "two_alternatives": plant_two_alternatives,
    "index": plant_index_off,
    "combination": plant_combination,
    "range": plant_range_upside_down,
    "below_zero": plant_below_zero,
    "identifier": plant_identifier,
    "params": plant_params,
    "distribution_parameters": plant_distribution_parameters,
}


def plant_breaks_holds(p: Planting) -> None:
    """A value its row's Holds column refuses, refused at that member: another JSON type (in one draw in
    three); or constraints the column states (section 1's list of departures), each in about half the draws
    and one at least, at places apart, so that each constraint's check is met in about one draw of the part in
    eight."""
    if p.draw(st.integers(0, 2)) == 0:
        plant_other_type(p)
        return
    chosen = [name for name in CONSTRAINTS if p.draw(st.booleans())] or [p.choose(tuple(CONSTRAINTS))]
    for name in chosen:
        CONSTRAINTS[name](p)


# The depths a member is added at, each a group of places: the declaration's own, a model entry's, a
# requirement's, an acceptance's and a target's or `trainable` entry's.
DEPTHS: dict[str, tuple[str, ...]] = {
    "declaration": ("declaration", "consumer", "operating condition"),
    "model": ("model entry", "model", "checked over", "mixing", "chain", "chain end"),
    "requirement": ("requirement", "requirement condition", "tolerance"),
    "acceptance": (*KINDS, "acceptance", "material reference", "implied numeric", "implied token"),
    "entry": (
        "trainable entry",
        *(f"fact {name}" for name in FACTS),
        *(f"difference {name}" for name in FACTS),
    ),
}


def plant_unknown(p: Planting) -> None:
    """Members the shape table does not name at their places, one at each depth (an acceptance appended
    where the declaration holds none), each depth in about half the draws and one at least: a name of no
    place, or one another place names; at an acceptance, in two draws in three one of a kind, a member another
    kind names, a `basis` on a kind item 4 does not give one in half those draws."""
    depths = tuple(DEPTHS)
    for depth in [depth for depth in depths if p.draw(st.booleans())] or [p.choose(depths)]:
        every = [site for site in changeable(p.declaration) if site.place in DEPTHS[depth]]
        kinds = [site for site in every if site.place in KINDS]
        if depth == "acceptance" and (not kinds or p.draw(st.integers(0, 2)) > 0):
            if not kinds:
                at, held = append_acceptance(p, p.model_index(), p.choose(CHECKED_KINDS))
                kinds = [Site(str(held["acceptance"]), at, held)]
            every = kinds
        if every:
            add_unknown(p, every[p.index(len(every))])
    if not any(fault.fault == "unknown_member" for fault in p.planted):
        at, held = append_acceptance(p, p.model_index(), p.choose(CHECKED_KINDS))
        add_unknown(p, Site(str(held["acceptance"]), at, held))


def add_unknown(p: Planting, site: Site) -> None:
    """A member `site`'s place does not name, added to it."""
    others = NAMED["acceptance"] if site.place in KINDS else EVERY_NAME
    elsewhere = [
        name
        for name in others
        if name not in NAMED.get(site.place, ()) and name not in site.value and name != "status"
    ]
    if p.draw(st.booleans()):
        name = p.choose(UNKNOWN_NAMES)
    elif "basis" in elsewhere and p.draw(st.booleans()):
        name = "basis"
    else:
        name = p.choose(elsewhere)
    if name in site.value:
        name = next(unknown for unknown in UNKNOWN_NAMES if unknown not in site.value)
    site.value[name] = p.draw(any_value())
    p.kinds.append(f"{site.place}: {'of another place' if name in elsewhere else 'of none'}")
    p.plant("unknown_member", site.pointer + pointer(name))


# `record_format.md` section 10: one slip, by kind.
SLIP_KINDS = ("plural", "singular", "inserted", "deleted", "substituted", "swapped", "underscore")
_IRREGULAR = {"datum": "data", "index": "indices", "matrix": "matrices"}


def slip_of(name: str, kind: str) -> str:
    """`name` one slip away, by `kind`: its last `_`-separated word made plural (`s`, or `es` after an `s` or
    an `x`, a final `y` as `ies`, an irregular plural) or singular (a final `s` taken off, or one added), a
    character inserted, deleted or substituted, two adjacent characters swapped, an underscore inserted."""
    words = name.split("_")
    last = words[-1]
    if kind == "plural":
        if last in _IRREGULAR:
            plural = _IRREGULAR[last]
        elif last.endswith("y"):
            plural = last[:-1] + "ies"
        else:
            plural = last + ("es" if last.endswith(("s", "x")) else "s")
        return "_".join([*words[:-1], plural])
    if kind == "singular":
        return name[:-1] if name.endswith("s") else name + "s"
    if kind == "inserted":
        return name[:1] + "q" + name[1:]
    if kind == "deleted":
        return name[1:] if len(name) > 2 else name + "q"
    if kind == "substituted":
        return name[:-1] + ("z" if name[-1] != "z" else "y")
    if kind == "swapped":
        return name[1] + name[0] + name[2:] if len(name) > 1 and name[0] != name[1] else name + "q"
    return name[:1] + "_" + name[1:]


def plant_slip(p: Planting) -> None:
    """A member one slip from a named one (section 10) in place of it, the kind of slip by chance: the slip is
    a member not named at its place, refused at it, and the member it stands for is missing, where its absence
    is a fault."""
    candidates = [
        (site, member) for site in changeable(p.declaration) for member in removable(p, site, texts=True)
    ]
    site, member = candidates[p.index(len(candidates))]
    kind = p.choose(SLIP_KINDS)
    slipped = slip_of(member, kind)
    if slipped in NAMED.get(site.place, ()) or slipped in site.value:
        slipped = member + "q"
    p.kinds.append(f"{kind}: {member} as {slipped}")
    value = site.value[member]
    removed(p, site, member)
    site.value[slipped] = value
    p.plant("unknown_member", site.pointer + pointer(slipped))


def plant_empty_list(p: Planting) -> None:
    """An empty list where the table asks for one entry or more: `models` alone, in one draw in four; or of
    `reads`, `checked_over.records`, an `overlay_scope`'s `accepts` and a token condition's accept list, each
    in about half the draws and one at least. Before `reads` or the records are emptied, what rests on them in
    that model goes: its requirements, `trainable` entries, combinations and its waivers' labels (`reads`),
    its `trainable` entries (the records); and no accept list is set in a model whose `reads` is emptied,
    since its requirement would need a field read."""
    if p.draw(st.integers(0, 3)) == 0:
        p.kinds.append("models")
        p.declaration["models"] = []
        p.plant("holds", "/models")
        return
    lists = ("reads", "records", "accepts", "accept")
    emptied: set[int] = set()
    for which in [which for which in lists if p.draw(st.booleans())] or [p.choose(lists)]:
        m = p.model_index()
        model = p.models[m]
        if which == "reads":
            model.pop("requirements", None)
            model.pop("trainable", None)
            model["combinations"] = []
            for held in acceptances_of(model):
                if held.get("acceptance") == "waiver":
                    held.pop("label", None)
            model["reads"] = []
            emptied.add(m)
            p.plant("holds", pointer("models", m, "reads"))
        elif which == "records":
            model.pop("trainable", None)
            cast(Json, model["checked_over"])["records"] = []
            p.plant("holds", pointer("models", m, "checked_over", "records"))
        elif which == "accepts":
            at, held = append_acceptance(p, m, "overlay_scope")
            held["accepts"] = []
            p.plant("holds", at + "/accepts")
        else:
            others = [index for index in range(len(p.models)) if index not in emptied]
            if not others:
                continue
            at, condition, _ = condition_at(p, others[p.index(len(others))], TOKEN_CONDITIONS)
            condition["accept"] = []
            p.plant("holds", at + "/accept")
        p.kinds.append(which)


SHAPE: dict[str, Callable[[Planting], None]] = {
    "missing": plant_missing,
    "breaks_holds": plant_breaks_holds,
    "unknown": plant_unknown,
    "slip": plant_slip,
    "empty_list": plant_empty_list,
}


# `tokens`: each member that holds a token or a registered name, at a place nothing rests on, with the list it
# takes there; a way gives a token outside that list, which the place's writer writes.

# Every token of every list the text gives a member, and the registered names: another member's token is one
# of these that the member's own list lacks.
EVERY_TOKEN = tuple(
    sorted(
        {
            *WANTS,
            *PRECISIONS,
            *MIXING_RULES,
            *METHODS,
            *SPACES,
            *ACCEPTS,
            REVIEW,
            *STATUS_TOKENS,
            *FACT_BASES,
            *SECTIONS,
            *KINDS,
            *LEVELS,
            *REPRESENTS,
            *UNITS.values(),
            *(token for tokens in CONDITION_TOKENS.values() for token in tokens),
            *(token for name in FACTS_WITH_TOKENS for token in VOCABULARY.facts[name].tokens),
            *FIELDS,
            *CONDITIONS,
            *FACTS,
            *ANY_LABEL,
            *DISTRIBUTIONS,
        }
    )
)
# Tokens of no list: an unknown word, the empty string, a token's words run together, a symbol.
NO_LIST = ("not_a_token_of_any_list", "", "valueOf", "?")

Bad = Callable[[tuple[str, ...]], str]


def outside_list(p: Planting) -> Bad:
    return lambda allowed: p.choose([token for token in NO_LIST if token not in allowed])


def slip_of_token(p: Planting) -> Bad:
    def bad(allowed: tuple[str, ...]) -> str:
        base = p.choose(allowed) if allowed else p.choose(EVERY_TOKEN)
        slipped = slip_of(base, p.choose(SLIP_KINDS))
        return slipped if slipped not in allowed and slipped else base + "q"

    return bad


def other_members_token(p: Planting) -> Bad:
    return lambda allowed: p.choose([token for token in EVERY_TOKEN if token not in allowed])


def other_case(p: Planting) -> Bad:
    def bad(allowed: tuple[str, ...]) -> str:
        base = p.choose(allowed) if allowed else p.choose(ANY_LABEL)
        for changed in (base.upper(), base.capitalize(), base.swapcase()):
            if changed not in allowed and changed != base:
                return changed
        return base.upper() + "Q"

    return bad


def write_requirement_member(member: str, allowed: tuple[str, ...]) -> Callable[[Planting, Bad], str]:
    """A requirement's `want` or `review`, on a requirement no labelled waiver rests on."""

    def write(p: Planting, bad: Bad) -> str:
        m = p.model_index()
        j, held = some_requirement(p, m, free=True)
        held[member] = bad(allowed)
        return pointer("models", m, "requirements", j, member)

    return write


def write_requirement_label(p: Planting, bad: Bad) -> str:
    """A requirement's `label`, against "a label registered for the field", on one no labelled waiver rests
    on."""
    m = p.model_index()
    j, held = some_requirement(p, m, free=True)
    field = str(held["field"])
    held["label"] = bad((LABELS[field],) if field in LABELS else ())
    return pointer("models", m, "requirements", j, "label")


# Section 1's `families`, "for each parameter-set field": those whose row allows the form `parameter_set`.
PARAMETER_SETS = tuple(name for name, spec in VOCABULARY.fields.items() if "parameter_set" in spec.forms)


def write_family(p: Planting, bad: Bad) -> str:
    """A name in `families`, which holds parameter-set fields alone: another field's name among them."""
    m = p.model_index()
    token = bad(PARAMETER_SETS)
    p.models[m]["families"] = {token: "1.0.0"}
    return pointer("models", m, "families", token)


def write_precision(p: Planting, bad: Bad) -> str:
    m = p.model_index()
    p.models[m]["precision"] = bad(PRECISIONS)
    return pointer("models", m, "precision")


def write_mixing_rule(p: Planting, bad: Bad) -> str:
    m = p.model_index()
    field = p.choose(FIELDS)
    p.models[m]["mixing"] = {"fraction_sum_tolerance": 0.0, "rules": {field: bad(MIXING_RULES)}}
    return pointer("models", m, "mixing", "rules", field)


def fresh(kind: str) -> Callable[[Planting], tuple[str, Json]]:
    return lambda p: append_acceptance(p, p.model_index(), kind)


def write_waiver_code(p: Planting, bad: Bad) -> str:
    """A waiver's `code`, on a waiver with no `condition`: a code that is no reason names no condition."""
    at, held = fresh("waiver")(p)
    held.pop("condition", None)
    held["code"] = bad(WAIVER_CODES)
    if held["code"] in CONDITION_CODES:
        # A token of no list could be a reason the clause names: then it needs its condition.
        held["condition"] = p.choose(CONDITIONS)
    return at + "/code"


def write_never_waived(p: Planting, bad: Bad) -> str:
    """Section 4.2: "A waiver whose `code` is `condition_unknown_name` is refused at build, at its `code`",
    beside a condition, which the code names (the shape table's own members cell)."""
    at, held = fresh("waiver")(p)
    held["code"] = NEVER_WAIVED
    held["condition"] = p.choose(CONDITIONS)
    return at + "/code"


def write_waiver_condition(p: Planting, bad: Bad) -> str:
    at, held = fresh("waiver")(p)
    held["code"] = p.choose(WAIVED_CONDITION_CODES)
    held["condition"] = bad(CONDITIONS)
    return at + "/condition"


def write_member_of(kind: str, member: str, allowed: tuple[str, ...]) -> Callable[[Planting, Bad], str]:
    def write(p: Planting, bad: Bad) -> str:
        at, held = fresh(kind)(p)
        held[member] = bad(allowed)
        return f"{at}/{member}"

    return write


def write_accepts(p: Planting, bad: Bad) -> str:
    at, held = fresh("overlay_scope")(p)
    held["accepts"] = [bad(ACCEPTS)]
    return at + "/accepts/0"


def write_status(p: Planting, bad: Bad) -> str:
    at, held = fresh("accepted_difference")(p)
    held["value"] = {"status": bad(STATUS_TOKENS)}
    return at + "/value/status"


def write_difference_basis(p: Planting, bad: Bad) -> str:
    """An accepted difference's `value`'s `basis`, `stated` or `inferred`, of a fact whose row leaves it
    open."""
    at, held = fresh("accepted_difference")(p)
    name = p.choose(tuple(name for name in FACTS if "basis" not in VOCABULARY.facts[name].fixed))
    held["fact"] = name
    held["value"] = {**p.draw(fact(name)), "basis": bad(FACT_BASES)}
    return at + "/value/basis"


def write_fact_token(p: Planting, bad: Bad) -> str:
    """An implied condition's `token`, of its `fact`'s tokens."""
    at, held = fresh("implied_condition")(p)
    held["token"] = bad(VOCABULARY.facts[str(held["fact"])].tokens)
    return at + "/token"


def write_implied_token(p: Planting, bad: Bad) -> str:
    """An implied token condition's `token`, of its row's tokens."""
    at, held = fresh("implied_condition")(p)
    name = p.choose(TOKEN_CONDITIONS)
    held["implies"] = {name: {"token": bad(CONDITION_TOKENS[name])}}
    return at + pointer("implies", name, "token")


def write_unit(p: Planting, bad: Bad) -> str:
    """A unit, against the one registered for its condition or fixed by its fact's row: an operating
    condition's, a tolerance's, an implied condition's, a target's `post_mortem_interval`'s."""
    m = p.model_index()
    name = p.choose(NUMERIC)
    place = p.choose(("operating condition", "tolerance", "implied", "fact"))
    if place == "operating condition":
        cast(Json, p.declaration["operating_conditions"])[name] = {
            "value": scale(name)[0],
            "unit": bad((UNITS[name],)),
        }
        return pointer("operating_conditions", name, "unit")
    if place == "tolerance":
        at, condition, _ = condition_at(p, m, (name,))
        cast(Json, condition["tolerance"])["unit"] = bad((UNITS[name],))
        return at + "/tolerance/unit"
    if place == "implied":
        at, held = append_acceptance(p, m, "implied_condition")
        held["implies"] = {name: {"value": scale(name)[0], "unit": bad((UNITS[name],))}}
        return at + pointer("implies", name, "unit")
    unit = VOCABULARY.facts["post_mortem_interval"].fixed["unit"]
    cast(Json, p.models[m]["target"])["post_mortem_interval"] = {"value": 3600.0, "unit": bad((unit,))}
    return pointer("models", m, "target", "post_mortem_interval", "unit")


def write_target_token(p: Planting, bad: Bad) -> str:
    m = p.model_index()
    name = p.choose(FACTS_WITH_TOKENS)
    cast(Json, p.models[m]["target"])[name] = {"token": bad(VOCABULARY.facts[name].tokens)}
    return pointer("models", m, "target", name, "token")


def write_accept_token(p: Planting, bad: Bad) -> str:
    """An entry of a token condition's accept list, beside the row's tokens."""
    at, condition, _ = condition_at(p, p.model_index(), TOKEN_CONDITIONS)
    tokens = CONDITION_TOKENS[at.rpartition("/")[2]]
    accept = cast(list[JsonValue], condition["accept"])
    accept.append(bad(tokens))
    return f"{at}/accept/{len(accept) - 1}"


# The registered names, each at a place where nothing rests on it.


def write_reads_entry(p: Planting, bad: Bad) -> str:
    """An entry appended to `reads`."""
    m = p.model_index()
    reads = reads_of(p.models[m])
    reads.append(bad(FIELDS))
    return pointer("models", m, "reads", len(reads) - 1)


def write_acceptance_field(p: Planting, bad: Bad) -> str:
    at, held = fresh(p.choose(("pick", "extrapolation", "nominal", "overlay")))(p)
    held["field"] = bad(FIELDS)
    return at + "/field"


def write_trainable_field(p: Planting, bad: Bad) -> str:
    """A `trainable` entry's `field`, at a record its model is checked over: a field not registered is not in
    `reads` either, one member at fault."""
    m = p.model_index()
    model = p.models[m]
    listed = entries(model, "trainable")
    listed.append({"field": bad(FIELDS), "record": copy.deepcopy(records_of(model)[0])})
    return pointer("models", m, "trainable", len(listed) - 1, "field")


def write_requirement_field(p: Planting, bad: Bad) -> str:
    """A requirement's `field`, on a requirement appended for it: a field not registered is not in `reads`
    either, one member at fault."""
    m = p.model_index()
    held = p.draw(requirement(FIELDS[0], labelled=False))
    held["field"] = bad(FIELDS)
    listed = entries(p.models[m], "requirements")
    listed.append(held)
    return pointer("models", m, "requirements", len(listed) - 1, "field")


def write_combination_entry(p: Planting, bad: Bad) -> str:
    """A combination of the name and a field of `reads` of a section other than the name's, so that its
    sections stay different (such a field appended to `reads` where none is read); a field not registered is
    not in `reads` either, one member at fault."""
    m = p.model_index()
    model = p.models[m]
    token = bad(FIELDS)
    reads = reads_of(model)
    others = [field for field in registered_reads(model) if section_of(field) != section_of(token)]
    if not others:
        others = [next(field for field in FIELDS if section_of(field) != section_of(token))]
        reads.append(others[0])
    listed = cast(list[JsonValue], model["combinations"])
    listed.append([token, p.choose(others)])
    return pointer("models", m, "combinations", len(listed) - 1, 0)


def write_mixing_key(p: Planting, bad: Bad) -> str:
    m = p.model_index()
    token = bad(FIELDS)
    p.models[m]["mixing"] = {"fraction_sum_tolerance": 0.0, "rules": {token: "refuse"}}
    return pointer("models", m, "mixing", "rules", token)


def write_operating_key(p: Planting, bad: Bad) -> str:
    """A name in `operating_conditions`, "registered condition to ... for a numeric condition"."""
    token = bad(NUMERIC)
    cast(Json, p.declaration["operating_conditions"])[token] = {"value": 300.0, "unit": "K"}
    return pointer("operating_conditions", token)


def write_condition_key(p: Planting, bad: Bad) -> str:
    m = p.model_index()
    j, held = some_requirement(p, m)
    token = bad(CONDITIONS)
    cast(Json, held.setdefault("conditions", {}))[token] = {
        "tolerance": {"value": 1.0, "unit": "K"},
        "reason": "r",
    }
    return pointer("models", m, "requirements", j, "conditions", token)


def write_implies_key(p: Planting, bad: Bad) -> str:
    at, held = fresh("implied_condition")(p)
    token = bad(CONDITIONS)
    held["implies"] = {token: {"value": 300.0, "unit": "K"}}
    return at + pointer("implies", token)


def write_target_key(p: Planting, bad: Bad) -> str:
    m = p.model_index()
    token = bad(FACTS)
    cast(Json, p.models[m]["target"])[token] = {}
    return pointer("models", m, "target", token)


def write_implied_fact(p: Planting, bad: Bad) -> str:
    """An implied condition's `fact`, "a specimen fact whose shape has a `token` member": its `token` is not
    judged beside a fact at fault."""
    at, held = fresh("implied_condition")(p)
    held["fact"] = bad(FACTS_WITH_TOKENS)
    return at + "/fact"


def write_difference_fact(p: Planting, bad: Bad) -> str:
    """An accepted difference's `fact`, beside a `value` of `"any"`, which no fact's shape judges."""
    at, held = fresh("accepted_difference")(p)
    held["fact"] = bad(FACTS)
    held["value"] = "any"
    return at + "/fact"


# The sweep: each member a token of its own list, and each registered name; the members a misspelt name is
# drawn at, fields and conditions.
TOKEN_WRITERS: dict[str, Callable[[Planting, Bad], str]] = {
    "want": write_requirement_member("want", WANTS),
    "review": write_requirement_member("review", (REVIEW,)),
    "unit": write_unit,
    "mixing rule": write_mixing_rule,
    "precision": write_precision,
    "waiver condition": write_waiver_condition,
    "never waived code": write_never_waived,
    "family": write_family,
    "space": write_member_of("distribution", "space", SPACES),
    "distribution": write_member_of("distribution", "distribution", tuple(DISTRIBUTIONS)),
    "label": write_requirement_label,
    "waiver code": write_waiver_code,
    "method": write_member_of("extrapolation", "method", METHODS),
    "accepts": write_accepts,
    "status": write_status,
    "difference basis": write_difference_basis,
    "section": write_member_of("accepted_difference", "section", SECTIONS),
    "kind": write_member_of("waiver", "acceptance", KINDS),
    "fact token": write_fact_token,
    "implied token": write_implied_token,
    "target token": write_target_token,
    "accept": write_accept_token,
    "reads": write_reads_entry,
    "operating condition": write_operating_key,
    "target fact": write_target_key,
    "implied fact": write_implied_fact,
    "difference fact": write_difference_fact,
}
FIELD_WRITERS: dict[str, Callable[[Planting, Bad], str]] = {
    "reads": write_reads_entry,
    "acceptance field": write_acceptance_field,
    "trainable field": write_trainable_field,
    "requirement field": write_requirement_field,
    "combination": write_combination_entry,
    "mixing key": write_mixing_key,
}
CONDITION_WRITERS: dict[str, Callable[[Planting, Bad], str]] = {
    "operating condition": write_operating_key,
    "requirement condition": write_condition_key,
    "implies": write_implies_key,
    "waiver condition": write_waiver_condition,
}


def plant_token(p: Planting, way: Callable[[Planting], Bad]) -> None:
    """Tokens outside their members' lists, the members by chance among the sweep's, each in about half the
    draws and one at least, so that each member's check is met in about one draw of the way in two."""
    chosen = [member for member in TOKEN_WRITERS if p.draw(st.booleans())] or [p.choose(tuple(TOKEN_WRITERS))]
    for member in chosen:
        p.kinds.append(member)
        p.plant("token", TOKEN_WRITERS[member](p, way(p)))


def plant_misspelt_name(p: Planting) -> None:
    """A registered name misspelt, a field or a condition by chance, at a place of its kind by chance: one
    slip from a registered name, and no registered name itself."""
    writers, names = (FIELD_WRITERS, FIELDS) if p.draw(st.booleans()) else (CONDITION_WRITERS, CONDITIONS)
    member = p.choose(sorted(writers))
    p.kinds.append(member)

    def misspelt(allowed: tuple[str, ...]) -> str:
        slipped = slip_of(p.choose(names), p.choose(SLIP_KINDS))
        return slipped if slipped not in allowed else slipped + "q"

    p.plant("token", writers[member](p, misspelt))


TOKENS: dict[str, Callable[[Planting], None]] = {
    "outside_list": lambda p: plant_token(p, outside_list),
    "slip_of_token": lambda p: plant_token(p, slip_of_token),
    "other_members_token": lambda p: plant_token(p, other_members_token),
    "other_case": lambda p: plant_token(p, other_case),
    "misspelt_name": plant_misspelt_name,
}


# `names`: names given twice, fields not read, a location not checked over, a label-resting waiver (item 4).


def plant_twice(p: Planting) -> None:
    """ "a name is given twice where the table allows it once", which list by chance, refused at the later
    entry, whole: two models of one `name`, a record listed twice in one `checked_over`, a field twice in
    `reads`, two requirements for one field, two `trainable` entries for one field at one location, and an
    `accepts` token twice (refused at the list, a value breaking its row's Holds)."""
    which = p.choose(("requirements", "models", "reads", "records", "trainable", "accepts"))
    p.kinds.append(which)
    if which == "models":
        if len(p.models) > 1:
            later = 1 + p.index(len(p.models) - 1)
            earlier = p.index(later)
            name = cast(Json, p.models[earlier]["model"])["name"]
            cast(Json, p.models[later]["model"])["name"] = name
        else:
            p.models.append(copy.deepcopy(p.models[0]))
            later = 1
        p.plant("twice", pointer("models", later))
        return
    m = p.model_index()
    model = p.models[m]
    if which in ("records", "reads"):
        listed = cast(list[JsonValue], records_of(model) if which == "records" else reads_of(model))
        listed.append(copy.deepcopy(listed[p.index(len(listed))]))
        path = ("checked_over", "records") if which == "records" else ("reads",)
        p.plant("twice", pointer("models", m, *path, len(listed) - 1))
    elif which == "requirements":
        _, held = some_requirement(p, m)
        second = p.draw(requirement(str(held["field"]), labelled=False))
        listed = entries(model, "requirements")
        listed.append(second)
        p.plant("twice", pointer("models", m, "requirements", len(listed) - 1))
    elif which == "trainable":
        listed = entries(model, "trainable")
        valid = [
            held
            for held in cast(list[Json], listed)
            if held.get("field") in reads_of(model) and held.get("record") in records_of(model)
        ]
        if not valid:
            # No entry is valid, so none names this field at this record.
            record: JsonValue = copy.deepcopy(p.draw(st.sampled_from(records_of(model))))
            valid = [{"field": p.choose(registered_reads(model)), "record": record}]
            listed.append(cast(JsonValue, copy.deepcopy(valid[0])))
        listed.append(cast(JsonValue, copy.deepcopy(valid[p.index(len(valid))])))
        p.plant("twice", pointer("models", m, "trainable", len(listed) - 1))
    else:
        at, held = append_acceptance(p, m, "overlay_scope")
        token = p.choose(ACCEPTS)
        held["accepts"] = [token, *(p.choose(ACCEPTS) for _ in range(p.index(2))), token]
        if len(set(cast(list[str], held["accepts"]))) == len(cast(list[str], held["accepts"])):
            held["accepts"] = [token, token]
        p.plant("holds", at + "/accepts")


def plant_requirement_unread(p: Planting) -> None:
    """ "a requirement ... names a field its model does not list in `reads`", refused at its `field`."""
    m = p.model_index()
    model = p.models[m]
    field = p.choose(unread(model))
    listed = entries(model, "requirements")
    listed.append(p.draw(requirement(field)))
    p.kinds.append(field)
    p.plant("unread", pointer("models", m, "requirements", len(listed) - 1, "field"))


def plant_trainable_unread(p: Planting) -> None:
    """ "a `trainable` entry names a field its model does not list in `reads`", at a listed record."""
    m = p.model_index()
    model = p.models[m]
    field = p.choose([field for field in FIELDS if field not in reads_of(model)])
    listed = entries(model, "trainable")
    taken = [(held.get("field"), held.get("record")) for held in cast(list[Json], listed)]
    records_free = [record for record in records_of(model) if (field, record) not in taken]
    if not records_free:
        records_free = records_of(model)
    listed.append({"field": field, "record": copy.deepcopy(records_free[p.index(len(records_free))])})
    p.kinds.append(field)
    p.plant("unread", pointer("models", m, "trainable", len(listed) - 1, "field"))


def plant_trainable_unlisted(p: Planting) -> None:
    """ "a `trainable` entry a location its model is not checked over": a field it reads at a record it does
    not list."""
    m = p.model_index()
    model = p.models[m]
    record = p.draw(
        st.sampled_from([reference for reference in REFERENCES if reference not in records_of(model)])
    )
    listed = entries(model, "trainable")
    listed.append({"field": p.choose(registered_reads(model)), "record": copy.deepcopy(record)})
    p.plant("unlisted", pointer("models", m, "trainable", len(listed) - 1, "record"))


def plant_label_unreviewed(p: Planting) -> None:
    """Section 4.1 item 4: a waiver naming a `label`, refused "unless the requirement for its field names that
    `label` and holds `review: "reviewed"`", at its `label`: the requirement lacking `review`, the label,
    both, or absent, or the waiver's field none registered (a slip of a labelled one), by chance. A labelled
    waiver that rested on the requirement before is refused so too."""
    m = p.model_index()
    model = p.models[m]
    field = p.choose(sorted(LABELS))
    reads = reads_of(model)
    if field not in reads:
        reads.append(field)
    lacking = p.choose(("review", "label", "both", "requirement", "a registered field"))
    p.kinds.append(lacking)
    if lacking == "a registered field":
        # A waiver whose `field` no field registered here is: no requirement names it, so item 4 refuses its
        # `label` beside the field's own fault, two members at fault.
        at, held = append_acceptance(p, m, "waiver")
        held["field"], held["label"] = field + "s", LABELS[field]
        p.plant("token", at + "/field")
        p.plant("label_unreviewed", at + "/label")
        return
    listed = entries(model, "requirements")
    position = next((j for j, held in enumerate(requirements_of(model)) if held.get("field") == field), None)
    if lacking == "requirement":
        if position is not None:
            del listed[position]
    else:
        if position is None:
            listed.append(p.draw(requirement(field, labelled=True)))
            position = len(listed) - 1
        held = cast(Json, listed[position])
        held["label"], held["review"] = LABELS[field], REVIEW
        for member in {"review": ("review",), "label": ("label",), "both": ("label", "review")}[lacking]:
            del held[member]
    for k in labelled_waivers(model, field):
        p.plant("label_unreviewed", pointer("models", m, "acceptances", k, "label"))
    at, held = append_acceptance(p, m, "waiver")
    held["field"], held["label"] = field, LABELS[field]
    p.plant("label_unreviewed", at + "/label")


NAMES_PART: dict[str, Callable[[Planting], None]] = {
    "twice": plant_twice,
    "requirement_unread": plant_requirement_unread,
    "trainable_unread": plant_trainable_unread,
    "trainable_unlisted": plant_trainable_unlisted,
    "label_unreviewed": plant_label_unreviewed,
}


# `precedence`: the refusal paragraph's order, its pointers and its merging.


def plant_two_rules(p: Planting) -> None:
    """A fault two rules name, which pair by chance: an acceptance without its `reason` or `basis` (item 4 and
    the shape table), a tolerance or accept list without its `reason` (item 3 and the table), a pick naming no
    record (the location rule and the table), a waiver's `label` registered for another field or of another
    type (item 4 and the table)."""
    pair = p.choose(("item 4", "item 3", "location", "label"))
    p.kinds.append(pair)
    m = p.model_index()
    if pair == "item 4":
        if p.draw(st.booleans()):
            plant_acceptance_without_reason(p)
        else:
            plant_basis_missing(p)
    elif pair == "item 3":
        plant_condition_without_reason(p, numeric=p.draw(st.booleans()))
    elif pair == "location":
        at, held = append_acceptance(p, m, "pick")
        del held["record"]
        p.plant("unlocated_pick", at, "record")
    else:
        at, held = append_acceptance(p, m, "waiver")
        field = p.choose(sorted(LABELS))
        held["field"] = field
        held["label"] = p.draw(
            st.one_of(
                st.sampled_from([label for label in ANY_LABEL if label != LABELS[field]]),
                other_type("string"),
            )
        )
        p.plant("waiver_label", at + "/label")


def plant_not_json(p: Planting) -> None:
    """A text that is not JSON by `record_format.md` section 1 item 6, the declaration's own text with one of
    the item's faults: cut short, a trailing comma, a byte-order mark, a name repeated, `NaN`, an unpaired
    surrogate escape, a byte that is not UTF-8, a number that rounds to an infinity, nesting deeper than 64.
    Refused at the empty pointer, and nothing else checked."""
    text = json.dumps(p.declaration).encode()
    fault = p.choose(("cut", "comma", "bom", "repeated", "nan", "surrogate", "utf8", "infinity", "deep"))
    p.kinds.append(fault)
    inserted = {
        "repeated": b'"consumer": 1, ',
        "nan": b'"x": NaN, ',
        "surrogate": b'"x": "\\ud800", ',
        "utf8": b'"\xff": 1, ',
        "infinity": b'"x": 1e400, ',
        "deep": b'"x": ' + b"[" * 65 + b"]" * 65 + b", ",
    }
    if fault == "cut":
        p.replaced = (text[:-1],)
    elif fault == "comma":
        p.replaced = (text[:-1] + b", }",)
    elif fault == "bom":
        p.replaced = (b"\xef\xbb\xbf" + text,)
    else:
        p.replaced = (b"{" + inserted[fault] + text[1:],)
    p.plant("not_json", "")


def plant_not_object(p: Planting) -> None:
    """A declaration that is not an object: refused at the empty pointer, and nothing else checked."""
    options: tuple[JsonValue, ...] = ([copy.deepcopy(p.declaration)], "a declaration", 1.0, None, True)
    value: JsonValue = p.draw(st.sampled_from(options))
    p.kinds.append(type(value).__name__)
    p.replaced = (json.dumps(value).encode() if p.draw(st.booleans()) else value,)
    p.plant("not_object", "")


def plant_two_missing(p: Planting) -> None:
    """Two members missing from one object: one refusal, at the object (the refusal paragraph: "Two faults
    with one case and one pointer are one refusal")."""

    def two_or_more(site: Site) -> list[str]:
        # `acceptance` aside: an acceptance without it is of no kind, which changes what else it requires.
        required = REQUIRED.get(site.place, ())
        return [
            member
            for member in removable(p, site, texts=False)
            if member in required and member != "acceptance"
        ]

    candidates = [site for site in changeable(p.declaration) if len(two_or_more(site)) > 1]
    site = candidates[p.index(len(candidates))]
    members = two_or_more(site)
    first = p.index(len(members))
    second = (first + 1 + p.index(len(members) - 1)) % len(members)
    p.kinds.append(site.place)
    for member in (members[first], members[second]):
        removed(p, site, member)


PRECEDENCE: dict[str, Callable[[Planting], None]] = {
    "two_rules": plant_two_rules,
    "missing_member": plant_missing,
    "not_json": plant_not_json,
    "not_object": plant_not_object,
    "two_missing": plant_two_missing,
}

PARTS: dict[str, dict[str, Callable[[Planting], None]]] = {
    "reasons": REASONS,
    "locations": LOCATIONS,
    "shape": SHAPE,
    "tokens": TOKENS,
    "names": NAMES_PART,
    "precedence": PRECEDENCE,
}


@st.composite
def hp41(draw: st.DrawFn, part: str, size: Size) -> Drawn:
    """A declaration the text takes, and the same with one fault of `part`'s ways planted (two, where the way
    is two missing members, or where a slip leaves its member missing), the way drawn first, alike."""
    ways = PARTS[part]
    way = draw(st.sampled_from(tuple(ways)))
    valid = draw(declarations(size))
    chosen = draw(claims())
    p = Planting(draw, valid)
    ways[way](p)
    planted = p.declaration if p.replaced is None else p.replaced[0]
    return Drawn(valid, planted, tuple(p.planted), way, "; ".join(p.kinds), chosen)


def local_token(writer: Callable[[Planting, Bad], str]) -> Callable[[Planting], None]:
    """A token of no list, written by `writer` at a fresh place."""
    return lambda p: p.plant("token", writer(p, outside_list(p)))


# `every_fault`: several faults at once, each a planter that appends a fresh entry or adds a member and so
# leaves every other fault where it is.
LOCAL: dict[str, Callable[[Planting], None]] = {
    "tolerance_reason": REASONS["tolerance_reason"],
    "accept_reason": REASONS["accept_reason"],
    "acceptance_reason": plant_acceptance_without_reason,
    "basis": plant_basis_missing,
    "empty_text": plant_empty_text,
    "unlocated": plant_unlocated,
    "located": plant_located,
    "unknown": plant_unknown,
    "requirement_unread": plant_requirement_unread,
    "trainable_unread": plant_trainable_unread,
    "trainable_unlisted": plant_trainable_unlisted,
    "reads_twice": lambda p: plant_twice_of(p, "reads"),
    "records_twice": lambda p: plant_twice_of(p, "records"),
    "accepts_twice": lambda p: plant_twice_of(p, "accepts"),
    **{
        f"token {member}": local_token(writer)
        for member, writer in TOKEN_WRITERS.items()
        if member not in ("want", "review", "label", "precision", "mixing rule", "unit", "target token")
    },
}


def plant_twice_of(p: Planting, which: str) -> None:
    """A field twice in `reads`, a record twice in `checked_over.records`, a token twice in `accepts`, each of
    those its model reads or lists as drawn."""
    m = p.model_index()
    model = p.models[m]
    if which == "accepts":
        at, held = append_acceptance(p, m, "overlay_scope")
        token = p.choose(ACCEPTS)
        held["accepts"] = [token, token]
        p.plant("holds", at + "/accepts")
        return
    listed = cast(list[JsonValue], records_of(model) if which == "records" else reads_of(model))
    kept = [item for item in listed if which == "records" or item in FIELDS]
    listed.append(copy.deepcopy(kept[p.index(len(kept))]))
    path = ("checked_over", "records") if which == "records" else ("reads",)
    p.plant("twice", pointer("models", m, *path, len(listed) - 1))


@st.composite
def every_fault(draw: st.DrawFn, size: Size) -> Drawn:
    """A declaration the text takes, and the same with two to five faults planted across its models, each a
    local planter's by chance."""
    valid = draw(declarations(size))
    chosen = draw(claims())
    p = Planting(draw, valid)
    names = draw(st.lists(st.sampled_from(sorted(LOCAL)), min_size=2, max_size=5))
    for name in names:
        LOCAL[name](p)
    return Drawn(valid, p.declaration, tuple(p.planted), "every_fault", "; ".join(names), chosen)


# HP42: what a build cannot check (item 12), beside faults of HP41's local planters.

HP42_WAYS = ("domain", "path", "region_conditions", "engine", "sampling")
# The local planters HP42 draws beside its member: none a `trainable` entry's record or a listed record twice,
# which a domain or a path in place of the records would take away.
BESIDE = tuple(name for name in sorted(LOCAL) if name not in ("trainable_unlisted", "records_twice"))


def plant_checked_over(p: Planting, m: int, member: str) -> None:
    """`checked_over` a domain or a path in place of records (item 12: the scene suite's), refused at it; a
    member beside the records stays."""
    checked_over = cast(Json, p.models[m]["checked_over"])
    del checked_over["records"]
    checked_over[member] = p.draw(st.sampled_from(("lumen", "wall", "path_1")))
    p.plant("scene_member", pointer("models", m, "checked_over", member))


def plant_region_conditions(p: Planting, m: int) -> None:
    regions = p.draw(
        st.lists(st.sampled_from(("lumen", "wall", "heated")), min_size=1, max_size=2, unique=True)
    )
    p.models[m]["region_conditions"] = {region: p.draw(operating_conditions()) for region in regions}
    p.plant("scene_member", pointer("models", m, "region_conditions"))


@st.composite
def engine(draw: st.DrawFn) -> Json:
    """An engine (section 1's row): `crosswalk`, the pin of its crosswalk; `values`, per attribute
    `{"value", "unit", "reason", "basis"}` with no `unit` for one with no dimension; `region_values` or
    none."""

    def value() -> Json:
        held: Json = {"value": draw(floats(0.0, 1.0e4)), "reason": draw(TEXTS), "basis": draw(TEXTS)}
        if draw(st.booleans()):
            held["unit"] = draw(st.sampled_from(("kg/m3", "Pa", "1")))
        return held

    attributes = draw(
        st.lists(st.sampled_from(("density", "friction", "restitution")), max_size=2, unique=True)
    )
    held: Json = {
        "crosswalk": {"id": "materica/crosswalk", "version": "1.0.0", "sha256": "f" * 64},
        "values": {name: value() for name in attributes},
    }
    if draw(st.booleans()):
        held["region_values"] = {"lumen": {name: value() for name in attributes[:1]}}
    return held


def plant_engine(p: Planting, m: int) -> None:
    """A model with `engine`, over its records or over a domain (by chance), its crosswalk pinned in three
    draws in four. The oracle reads item 7 from what it is over, its crosswalk (pinned, and never passed to
    this version's build) and its requirements' `want`s; a missing crosswalk is the shape table's fault, the
    draw where item 7 alone tells an engine model over records from one over a domain."""
    model = p.models[m]
    over = p.choose(("records", "domain"))
    if over == "domain":
        plant_checked_over(p, m, "domain")
    held = p.draw(engine())
    pinned = p.draw(st.integers(0, 3)) > 0
    if not pinned:
        del held["crosswalk"]
        p.plant("missing_member", pointer("models", m, "engine"), "crosswalk")
    model["engine"] = held
    wants = tuple(str(item["want"]) for item in requirements_of(model) if isinstance(item.get("want"), str))
    p.kinds.append(f"over {over}{'' if pinned else ', no crosswalk'}")
    p.plant(
        "engine",
        pointer("models", m, "engine"),
        None,
        (("over", over), ("crosswalk", pinned), ("wants", wants)),
    )


@st.composite
def population_level(draw: st.DrawFn) -> Json:
    """`{"level", "within"}` (a level, or the status object of `none`), or `{"level", "balanced_over"}`."""
    level = draw(st.sampled_from(LEVELS))
    if draw(st.booleans()):
        within: JsonValue = draw(st.sampled_from(LEVELS)) if draw(st.booleans()) else {"status": "none"}
        return {"level": level, "within": within}
    return {"level": level, "balanced_over": draw(st.sampled_from(LEVELS))}


def plant_sampling(p: Planting, m: int) -> None:
    """A sampling member, which by chance: a requirement's `represents`, of `population` with its level or
    without, or another; a `population_level` beside another `represents` or none; `sampling` alone; a
    `distribution` acceptance. Beside it, `sampling` with a `min_acceptance` outside (0, 1] (0 among them),
    missing `independence` (in two draws in three) or `reason`, valid (`min_acceptance` 1 among them), or
    absent, by chance. The oracle reads items 8 and 12 and the `population_level` rule from what is
    planted."""
    which = p.choose(("represents", "population", "no_level", "level_beside", "sampling", "distribution"))
    block = p.choose(
        ("outside", "incomplete", "valid")
        if which == "sampling"
        else ("outside", "incomplete", "valid", "absent")
    )
    p.kinds.append(f"{which}, sampling {block}")
    requirements: list[tuple[str, str | None, bool]] = []
    distributions: list[str] = []
    if which in ("represents", "population", "no_level", "level_beside"):
        j, held = some_requirement(p, m)
        represents: str | None = {
            "represents": p.choose([token for token in REPRESENTS if token != "population"]),
            "population": "population",
            "no_level": "population",
            "level_beside": p.choose([*(token for token in REPRESENTS if token != "population"), "none"]),
        }[which]
        if represents == "none":
            represents = None
        else:
            held["represents"] = represents
        level = which in ("population", "level_beside")
        if level:
            held["population_level"] = p.draw(population_level())
        requirements.append((pointer("models", m, "requirements", j), represents, level))
    elif which == "distribution":
        at, _ = append_acceptance(p, m, "distribution")
        p.planted = [fault for fault in p.planted if fault.pointer != at]
        distributions.append(at)
    if block != "absent":
        bounds = (1.0, 0.95, 5.0e-324) if block != "outside" else (0.0, -0.5, 1.0000000000000002, 2.0)
        least = p.draw(st.sampled_from(bounds))
        sampling: Json = {"min_acceptance": least, "reason": p.draw(TEXTS), "independence": []}
        if block == "incomplete":
            missing = p.choose(("independence", "independence", "reason"))
            del sampling[missing]
            p.plant("missing_member", "/sampling", missing)
        p.declaration["sampling"] = sampling
    p.plant(
        "sampling",
        "",
        None,
        (("block", block), ("requirements", tuple(requirements)), ("distributions", tuple(distributions))),
    )


HP42_SUITES: dict[str, Suite] = {
    "domain": SCENE,
    "path": SCENE,
    "region_conditions": SCENE,
    "engine": USD,
    "sampling": SAMPLING,
}


@st.composite
def hp42(draw: st.DrawFn, size: Size) -> Drawn:
    """A declaration the text takes; beside it, none to two faults of HP41's local planters; and the same with
    one member a build that claims neither the scene suite, USD read nor the sampling suite cannot check
    planted, which way drawn first, alike."""
    way = draw(st.sampled_from(HP42_WAYS))
    valid = draw(declarations(size))
    chosen = draw(claims())
    p = Planting(draw, valid)
    for name in draw(st.lists(st.sampled_from(BESIDE), max_size=2)):
        LOCAL[name](p)
    without, beside = copy.deepcopy(p.declaration), len(p.planted)
    m = p.model_index()
    if way in ("domain", "path"):
        plant_checked_over(p, m, way)
    elif way == "region_conditions":
        plant_region_conditions(p, m)
    elif way == "engine":
        plant_engine(p, m)
    else:
        plant_sampling(p, m)
    return Drawn(
        valid,
        p.declaration,
        tuple(p.planted),
        way,
        "; ".join(p.kinds),
        chosen,
        without,
        HP42_SUITES[way],
        beside,
    )
