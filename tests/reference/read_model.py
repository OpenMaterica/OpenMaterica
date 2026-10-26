# SPDX-License-Identifier: Apache-2.0
"""A test-only reference model of a read of one field of one record: what `read_side_contract.md` sections 1
to 3 give for a request and the sources supplied beside it, written from the specification's text alone, for
the conformance cases (`test_cases.py`), HP12 and the fuzz targets.

It never ships and imports nothing from `materica`, at any depth (`test_layering.py`). Its tables are the
text's, checked against the generated vocabulary (`test_tables.py`), and each rule cites the text it comes
from, as `file:line` and a short quote, which `test_citations.py` finds at that line.

**What it decides.** Steps 0 to 13 for the forms constant, table, interval, composition and evidence, a
table's value from the reference evaluator's `exact` mode (`table_evaluator.py`); implied conditions,
nominals and extrapolations, an extrapolation covering a table's `outside_range` at step 11 under `want:
value` with the value at the readable range's nearest end; step 7 over alternatives read with no pick and no
overlay (S4a): the shape of `alternatives`, each alternative read alone and set aside, kept or refusing the
field, a table alternative whose read gives a reason at step 11 or that an extrapolation covers among them
(S4d), and the outcome with its reasons and members; and the operations `list_records` and `content_hash`.

**What it does not.** Everything else gives `NoVerdict`, a distinct outcome a test counts and never reads as
a pass: a pick, an overlay, a `trainable` acceptance, a region target, and `want: fit` on a field holding a
fit record.

**Where the text is silent.** The model takes the maintainer's ruling where there is one, else the fail-closed
choice. Each such point is listed once in `OPEN_POINTS`, and named where it is applied ("Open point: <name>").

The model reads JSON as `strict_json.parse` does: every number a float. Its results are JSON values of that
kind, so that a case compares them as it compares an implementation's result read back from its text."""

import itertools
import json
import re
import struct
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Final, Literal, TypeAlias, TypeGuard

from tests.reference import table_evaluator
from tests.reference.strict_json import JsonObject, JsonValue, NotStrictJson, content_hash, parse

OPEN_POINTS: Final[Mapping[str, str]] = {
    "form_not_allowed_by_its_row": (
        "a composition whose basis the field's row does not allow is refused as a form the row does not "
        "allow is: with `form_not_registered` and the shared checks' reasons, its member, which the read "
        "neither uses nor returns, not checked (maintainer, 2026-10-15; the text says so of a form, not of "
        "a basis)"
    ),
    "alternatives_without_a_pick": (
        "over alternatives the model decides step 7 for a read with no pick and no overlay (S4a): the shape "
        "of `alternatives`, each alternative of a form it reads read alone by steps 8 to 13, set aside, "
        "kept or refusing the field, and the outcome, its reasons and members. A pick or an overlay in the "
        "request gives no verdict at step 0; a table alternative is read as a field, and one that steps 8 "
        "or 9 refuse refuses the field, one step 10 sets aside is set aside, one step 11 ends or an "
        "extrapolation covers is set aside, kept or refusing by the text's rows of step 7 (S4d), and one "
        "read to step 13 stays or refuses as any form's"
    ),
    "evidence_entry_provenance": (
        "an evidence entry's `provenance` is returned holding, below the provenance table's own members, "
        "those the writer schema defines at every depth, a member it does not define left out, since the "
        "text names them in part only"
    ),
}

Status: TypeAlias = Literal["met", "unknown", "not_met"]

# README.md:53 "A read gives `met`, `not_met` or `unknown`"
# read_side_contract.md:138 "The status is the worst of them: `not_met` over `unknown` over `met`"
STATUSES_BEST_FIRST: Final[tuple[Status, ...]] = ("met", "unknown", "not_met")

# The text's tables


@dataclass(frozen=True)
class StatusUnit:
    """A unit registered as a status object: README.md:46-47 "or `{"status": "not_applicable"}` for a field
    with no unit"."""

    status: str


@dataclass(frozen=True)
class FieldRow:
    unit: str | StatusUnit
    forms: tuple[str, ...]
    requires: tuple[str, ...]
    bases: tuple[str, ...] = ()  # the composition bases the row allows
    label: str | None = None
    label_not_on_axis: str | None = None  # the label goes on a table whose axis is not this condition


# record_format.md:161 "| Section.field | Unit | Forms | Requires | Label |"
FIELDS: Final[Mapping[str, FieldRow]] = {
    "bulk.density": FieldRow("kg/m3", ("constant", "table", "interval"), ("temperature", "density_kind")),
    # record_format.md:164 "composition (basis `mass_fraction`)"
    "bulk.elemental_composition": FieldRow("1", ("composition",), (), bases=("mass_fraction",)),
    # record_format.md:165 "`materica.fluid.newtonian.v1` on a constant, or on a table whose axis is not
    # `shear_rate`"
    "fluid.dynamic_viscosity": FieldRow(
        "Pa.s",
        ("constant", "table", "interval"),
        ("temperature", "shear_rate"),
        label="materica.fluid.newtonian.v1",
        label_not_on_axis="shear_rate",
    ),
    "magnetic.remanence": FieldRow(
        "T", ("constant", "interval"), ("temperature", "specimen_shape", "test_method")
    ),
    "magnetic.saturation_magnetisation": FieldRow(
        "A/m", ("constant", "interval"), ("temperature", "specimen_shape", "test_method")
    ),
    "magnetic.volume_susceptibility": FieldRow(
        "1",
        ("constant", "table", "interval"),
        ("temperature", "specimen_shape", "magnetic_flux_density"),
        label="materica.magnetic.linear.v1",
        label_not_on_axis="magnetic_flux_density",
    ),
    # record_format.md:169 "| `biocompatibility.evidence` |"
    "biocompatibility.evidence": FieldRow(StatusUnit("not_applicable"), ("evidence",), ()),
}
SECTIONS: Final = frozenset(name.partition(".")[0] for name in FIELDS)
FIELD_LABELS: Final[Mapping[str, str]] = {row.label: name for name, row in FIELDS.items() if row.label}


RequiredWith: TypeAlias = tuple[tuple[str, tuple[str, ...]], ...]  # another condition, and its tokens


@dataclass(frozen=True)
class ConditionRow:
    shape: Literal["numeric", "token"]
    unit: str | None = None
    tokens: tuple[str, ...] = ()
    required_with: RequiredWith = ()


# provenance.md:230 "| Name | Shape | Unit or tokens | Required with |"
CONDITIONS: Final[Mapping[str, ConditionRow]] = {
    "temperature": ConditionRow("numeric", unit="K"),
    "shear_rate": ConditionRow("numeric", unit="1/s"),
    "magnetic_flux_density": ConditionRow("numeric", unit="T"),
    "density_kind": ConditionRow("token", tokens=("apparent", "matrix")),
    "specimen_shape": ConditionRow(
        "token",
        tokens=("sphere", "cylinder", "prolate_spheroid", "oblate_spheroid", "slab", "film", "irregular"),
    ),
    "specimen_size": ConditionRow("numeric", unit="m"),
    "measurement_geometry": ConditionRow("token", tokens=("bulk", "tube", "gap")),
    # provenance.md:239 "`measurement_geometry`: `tube`, `gap`"
    "measurement_dimension": ConditionRow(
        "numeric", unit="m", required_with=(("measurement_geometry", ("tube", "gap")),)
    ),
    "test_method": ConditionRow(
        "token",
        tokens=(
            "rotational_rheometer",
            "capillary_viscometer",
            "vibrating_sample_magnetometer",
            "squid_magnetometer",
            "hysteresigraph",
            "pycnometer",
            "reference_formulation",
        ),
    ),
}


# record_format.md:401 "`axis` names the table's axis, a numeric condition"
AXES: Final = tuple(name for name, row in CONDITIONS.items() if row.shape == "numeric")


@dataclass(frozen=True)
class FactRow:
    members: Mapping[str, str]  # each member of the row's shape but `basis` and `inferred_from`, and its kind
    required: tuple[str, ...]
    tokens: tuple[str, ...] = ()
    unit: str | None = None  # the unit the row fixes
    basis: str | None = None  # the basis the row fixes


# provenance.md:289 "| Name | JSON shape |"
FACTS: Final[Mapping[str, FactRow]] = {
    "species": FactRow({"ncbi_taxon": "integer", "label": "text"}, ("ncbi_taxon", "label")),
    "anatomical_site": FactRow({"uberon": "text", "label": "text"}, ("uberon", "label")),
    "tissue_state": FactRow(
        {"token": "token"}, ("token",), ("in_vivo", "ex_vivo_fresh", "frozen_thawed", "fixed", "phantom")
    ),
    # provenance.md:294 "is present exactly when `token` is `diseased` or `treated`"
    "disease_and_treatment_state": FactRow(
        {"token": "token", "text": "text"}, ("token",), ("normal", "diseased", "treated")
    ),
    "preparation": FactRow({"text": "text"}, ("text",)),
    # provenance.md:296 "<text, required for other>"
    "preservation": FactRow(
        {"token": "token", "text": "text"},
        ("token",),
        ("none", "refrigerated", "frozen", "fixed_formalin", "other"),
    ),
    "post_mortem_interval": FactRow({"value": "number", "unit": "unit"}, ("value", "unit"), unit="s"),
    # provenance.md:298 "| `donor_age` | `{"value", "unit": "s", "basis"}`"
    "donor_age": FactRow({"value": "number", "range": "range", "unit": "unit"}, ("unit",), unit="s"),
    # provenance.md:299 "its `basis` is fixed to `stated`, so it takes no `inferred_from`"
    "mimics": FactRow({"text": "text"}, ("text",), basis="stated"),
    "supply_form": FactRow({"token": "token"}, ("token",), ("stock", "coupon", "finished_component")),
    "lot": FactRow({"text": "text"}, ("text",)),
}
DISEASE_NAMED_BY: Final = ("diseased", "treated")


@dataclass(frozen=True)
class ReasonRow:
    status: Status
    steps: tuple[int, ...] = ()
    procedures: tuple[str, ...] = ()  # for a code no step gives


# read_side_contract.md:380 "| Code | Status | Step | Meaning | Defined in |"
REASONS: Final[Mapping[str, ReasonRow]] = {
    "malformed": ReasonRow("not_met", (1, 2, 3, 6)),
    "other_version": ReasonRow("not_met", (2, 6)),
    "hash_mismatch": ReasonRow("not_met", (4, 6)),
    "pin_mismatch": ReasonRow("not_met", (1, 4, 6)),
    "unknown_type": ReasonRow("not_met", (5, 6)),
    "absent": ReasonRow("not_met", (1, 6, 7)),
    "no_pick": ReasonRow("unknown", (7,)),
    "pick_invalid": ReasonRow("not_met", (7,)),
    "form_not_registered": ReasonRow("not_met", (8,)),
    "form_invalid": ReasonRow("not_met", (7, 8)),
    "unknown_token": ReasonRow("not_met", (6, 8)),
    "withheld": ReasonRow("not_met", (6, 8)),
    "entries_withheld": ReasonRow("unknown", (8,)),
    "fill_in_version_mismatch": ReasonRow("unknown", (12,)),
    "unit_mismatch": ReasonRow("not_met", (9,)),
    "condition_unstated": ReasonRow("unknown", (10,)),
    "condition_unknown_name": ReasonRow("unknown", (10,)),
    "condition_unchecked": ReasonRow("unknown", (10,)),
    "condition_outside": ReasonRow("not_met", (10,)),
    "condition_not_accepted": ReasonRow("not_met", (10,)),
    "condition_uncertain": ReasonRow("unknown", (10,)),
    "outside_range": ReasonRow("not_met", (11,)),
    "at_edge": ReasonRow("not_met", (11,)),
    "range_unstated": ReasonRow("unknown", (11,)),
    "want_mismatch": ReasonRow("not_met", (0, 7, 11, 13)),
    "nominal_invalid": ReasonRow("not_met", (13,)),
    "stated_without_origin": ReasonRow("unknown", (12,)),
    "family_suite_absent": ReasonRow("not_met", (8,)),
    "points_unsupported": ReasonRow("not_met", (8,)),
    "overlay_base_mismatch": ReasonRow("not_met", (6,)),
    "overlay_scope_mismatch": ReasonRow("not_met", procedures=("build",)),
    "overlay_conflict": ReasonRow("not_met", (6,)),
    "request_incomplete": ReasonRow("not_met", (0, 10, 11)),
    "request_unit_mismatch": ReasonRow("not_met", (0,)),
    "owner_ambiguous": ReasonRow("not_met", procedures=("scene",)),
    "no_material": ReasonRow("not_met", procedures=("scene",)),
    "domain_undeclared": ReasonRow("not_met", procedures=("scene",)),
    "orientation_missing": ReasonRow("not_met", procedures=("scene",)),
    "geometry_unresolved": ReasonRow("not_met", procedures=("scene",)),
    "geometry_hash_mismatch": ReasonRow("not_met", procedures=("scene",)),
    "representation_unsupported": ReasonRow("not_met", procedures=("scene",)),
    "homogeneity_undeclared": ReasonRow("not_met", procedures=("scene",)),
    "outside_path": ReasonRow("not_met", procedures=("scene",)),
    "label_unmapped": ReasonRow("not_met", procedures=("scene",)),
    "anatomy_mismatch": ReasonRow("not_met", procedures=("scene",)),
    "unauthored_attribute": ReasonRow("not_met", procedures=("USD read",)),
    "stage_units_unauthored": ReasonRow("not_met", procedures=("USD read", "engine adapter")),
    "units_uncompensated": ReasonRow("not_met", procedures=("USD read",)),
    "binding_missing": ReasonRow("not_met", procedures=("USD read",)),
    "binding_refused": ReasonRow("not_met", procedures=("USD read",)),
    "payload_unloaded": ReasonRow("not_met", procedures=("USD read",)),
    "region_in_prototype": ReasonRow("not_met", procedures=("USD read",)),
    "time_sampled": ReasonRow("not_met", procedures=("USD read",)),
    "engine_crosswalk_invalid": ReasonRow("not_met", procedures=("engine adapter", "build")),
    "engine_value_invalid": ReasonRow("not_met", procedures=("engine adapter",)),
    "engine_attribute_unset": ReasonRow("not_met", procedures=("engine adapter",)),
    "engine_value_sourced": ReasonRow("not_met", procedures=("engine adapter",)),
    "engine_binding_overridden": ReasonRow("not_met", procedures=("engine adapter",)),
    "engine_region_instanced": ReasonRow("not_met", procedures=("engine adapter",)),
    "engine_material_missing": ReasonRow("not_met", procedures=("build",)),
    "engine_material_foreign": ReasonRow("not_met", procedures=("build",)),
    "engine_material_stale": ReasonRow("not_met", procedures=("build",)),
    "engine_density_overridden": ReasonRow("not_met", procedures=("build",)),
    "engine_mass_not_comparable": ReasonRow("unknown", procedures=("build",)),
    "path_arrays_mismatch": ReasonRow("not_met", procedures=("USD read",)),
    "no_requirement": ReasonRow("unknown", procedures=("build",)),
    "label_mismatch": ReasonRow("not_met", procedures=("build",)),
    "not_reviewed": ReasonRow("unknown", procedures=("build",)),
    "unknown_family": ReasonRow("not_met", procedures=("family evaluation",)),
    "parameters_mismatch": ReasonRow("not_met", procedures=("family evaluation",)),
    "check_point_failed": ReasonRow("not_met", procedures=("family evaluation",)),
    "inadmissible": ReasonRow("not_met", procedures=("family evaluation",)),
    "outside_check_points": ReasonRow("unknown", procedures=("family evaluation",)),
    "outside_coverage": ReasonRow("unknown", procedures=("family evaluation",)),
    "fractions_invalid": ReasonRow("not_met", procedures=("mixing",)),
    "mixing_refused": ReasonRow("not_met", procedures=("mixing",)),
}

# provenance.md:11 "The five tokens are `unstated`"
STATUS_TOKENS: Final = ("unstated", "not_checked", "none", "not_applicable", "withheld")
ANY_STATUS: Final = frozenset(STATUS_TOKENS)

# record_format.md:328 "one of `constant`, `table`, `power_law`, `interval`, `composition`, `parameter_set`"
FORMS: Final = (
    "constant", "table", "power_law", "interval", "composition", "parameter_set", "reference_data", "evidence"
)  # fmt: skip
# record_format.md:330 "`value` for a constant; otherwise the member named like the form"
FORM_MEMBERS: Final[Mapping[str, str]] = {form: "value" if form == "constant" else form for form in FORMS}
# record_format.md:469-470 "`reported_range`, `proxy_range` (a range taken from other tissues),
# `specification_limits`"
INTERVAL_BASES: Final = ("reported_range", "proxy_range", "specification_limits", "stated_bound")
# record_format.md:408 "`scheme` is `linear` or `loglog`"
TABLE_SCHEMES: Final = ("linear", "loglog")
# declarations.md:369 "`method` (`constant` or `consumer_law`)"
EXTRAPOLATION_METHODS: Final = ("constant", "consumer_law")
# record_format.md:482 "`basis` is `mass_fraction`, `volume_fraction` or `mole_fraction`"
COMPOSITION_BASES: Final = ("mass_fraction", "volume_fraction", "mole_fraction")
# record_format.md:486 "`sum_rule` is `sums_to_one` or `partial`"
SUM_RULES: Final = ("sums_to_one", "partial")
# record_format.md:498 "The element symbols are IUPAC's 118"
ELEMENTS: Final = tuple(
    "H He "
    "Li Be B C N O F Ne "
    "Na Mg Al Si P S Cl Ar "
    "K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
    "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe "
    "Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
    "Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
)
# record_format.md:482-483 "`component` is `element:<symbol>`"
COMPONENTS: Final = frozenset(f"element:{symbol}" for symbol in ELEMENTS)

# uncertainty.md:31 "`mean`, `median`, `single_measurement` or `stated`"
CENTRALS: Final = ("mean", "median", "single_measurement", "stated")
# uncertainty.md:34 "`normal` or `lognormal` where the source states one"
BLOCK_DISTRIBUTIONS: Final = ("normal", "lognormal")
# uncertainty.md:35 "`reported_sd`, `reported_se`, `reported_range`, `across_sources`, `digitising_error`"
BLOCK_BASES: Final = (
    "reported_sd", "reported_se", "reported_range", "across_sources", "digitising_error",
    "specification_limits",
)  # fmt: skip
# uncertainty.md:36 "`population` (variation between specimens or donors), `estimate`"
REPRESENTS: Final = ("population", "estimate", "measurement", "across_sources")
# uncertainty.md:37 "the levels are `donor`, `lot`, `specimen` and `test`"
LEVELS: Final = ("donor", "lot", "specimen", "test")
# uncertainty.md:39 "`repeatability`, `intermediate` or `reproducibility`"
PRECISION_CONDITIONS: Final = ("repeatability", "intermediate", "reproducibility")
# uncertainty.md:40 "`reported`, or `not_reported` where the source gives no spread"
DISPERSIONS: Final = ("reported", "not_reported")
# uncertainty.md:47 "`distribution` is `normal`, `student_t`"
UNCERTAINTY_DISTRIBUTIONS: Final = ("normal", "student_t")
# uncertainty.md:50 "`basis` is `reported_uncertainty` or `digitising_error`"
UNCERTAINTY_BASES: Final = ("reported_uncertainty", "digitising_error")
# uncertainty.md:51 "`represents` is `measurement`, `estimate`"
UNCERTAINTY_REPRESENTS: Final = ("measurement", "estimate")
# uncertainty.md:237 "| Token | Parameters |"
DISTRIBUTIONS: Final = ("normal", "lognormal", "uniform", "triangular", "student_t", "beta")

# provenance.md:92 "`measured_by_source`, `measured_by_contributor`, `fitted`, `derived`,
# `evaluated_from_formulation`"
ORIGINS: Final = (
    "measured_by_source", "measured_by_contributor", "fitted", "derived", "evaluated_from_formulation",
    "stated_without_origin",
)  # fmt: skip
# provenance.md:122-123 "whose `result` is a token the reader knows (`reviewed`)"
REVIEW_RESULTS: Final = ("reviewed",)
# provenance.md:211 "`stated`, or `inferred` with an `inferred_from` text"
CONDITION_BASES: Final = ("stated", "inferred")
# read_side_contract.md:484 "with basis `implied`"
IMPLIED_BASIS: Final = "implied"
# provenance.md:264-265 "`stated_as` is `bound`"
STATED_AS: Final = ("bound", "sd")
# provenance.md:272 "`set_or_measured` is `set_point`"
SET_OR_MEASURED: Final = ("set_point", "measured")

# read_side_contract.md:132 "the result's labels, from this list only: `user_extracted`"
RESULT_LABELS: Final = (
    "user_extracted", "no_independent_witness", "mean_of_specimen_fits", "mixed_conditions",
    "hash_not_checked", "initial_value_only",
)  # fmt: skip
# read_side_contract.md:528 "| `want` | constant, table, power law | interval | composition | evidence |"
WANTS: Final = ("value", "bounds", "components", "evidence", "reference_data", "fit", "coverage")
# read_side_contract.md:535-538 "the fits and reference data suite"
FITS_AND_REFERENCE_DATA_WANTS: Final = ("reference_data", "fit", "coverage")
# Each want's row, the forms it gives: read_side_contract.md:530-533 "| `value` | the number at the operating
# conditions" and "| `bounds` | `not_met` (`want_mismatch`) | `{"lower", "upper", "basis"}`, as stored"
GIVES: Final[Mapping[str, tuple[str, ...]]] = {
    "value": ("constant", "table", "power_law"),
    "bounds": ("interval",),
    "components": ("composition",),
    "evidence": ("evidence",),
    "reference_data": ("reference_data",),
}
# declarations.md:363 "| `acceptance` | Location | Own members | Effect |"
ACCEPTANCE_KINDS: Final = (
    "pick", "waiver", "implied_condition", "accepted_difference", "extrapolation", "nominal", "distribution",
    "overlay", "overlay_scope",
)  # fmt: skip
# read_side_contract.md:64-65 "take only the kinds `pick`, `overlay`, `extrapolation`, `nominal`,
# `implied_condition` and `trainable`": the model takes the first five, and gives no verdict on a request
# holding a `trainable` acceptance (`UNDECIDED_ACCEPTANCES`), which S7a-4 builds in the read.
READ_ACCEPTANCE_KINDS: Final = ("pick", "overlay", "extrapolation", "nominal", "implied_condition")
# declarations.md:359-361 "names the `field` it covers" and "its kind's own members; and carries `reason`"
ACCEPTANCE_NAMES: Final = ("acceptance", "field", "record", "region", "interval", "reason", "basis")
ACCEPTANCE_OWN_NAMES: Final[Mapping[str, tuple[str, ...]]] = {
    "pick": ("index",),
    "waiver": ("code", "condition"),
    "implied_condition": ("fact", "token", "implies"),
    "accepted_difference": ("section", "fact", "value"),
    "extrapolation": ("method", "law"),
    "nominal": ("value", "params"),
    "distribution": ("distribution", "space", "distribution_parameters"),
    "overlay": ("overlay",),
    "overlay_scope": ("overlay", "accepts"),
}

# read_side_contract.md:309-311 "a token the reader knows for a member of that name in a member whose row does
# not allow it (`form_invalid`), a token the reader knows for no member of that name (`unknown_token`)": every
# token the version gives a member of each name, wherever it sits.
KNOWN_TOKENS: Final[Mapping[str, frozenset[str]]] = {
    "form": frozenset(FORMS),
    "basis": frozenset(
        (
            *CONDITION_BASES,
            IMPLIED_BASIS,
            *INTERVAL_BASES,
            *COMPOSITION_BASES,
            *BLOCK_BASES,
            *UNCERTAINTY_BASES,
        )
    ),
    "central": frozenset(CENTRALS),
    "distribution": frozenset(DISTRIBUTIONS),
    "represents": frozenset(REPRESENTS),
    "dispersion": frozenset(DISPERSIONS),
    "precision_conditions": frozenset(PRECISION_CONDITIONS),
    "level": frozenset(LEVELS),
    "within": frozenset(LEVELS),
    "origin": frozenset(ORIGINS),
    "token": frozenset(
        {token for row in CONDITIONS.values() for token in row.tokens}
        | {token for row in FACTS.values() for token in row.tokens}
    ),
    "stated_as": frozenset(STATED_AS),
    "set_or_measured": frozenset(SET_OR_MEASURED),
    "sum_rule": frozenset(SUM_RULES),
    "component": COMPONENTS,
    "scheme": frozenset(TABLE_SCHEMES),
    "label": frozenset(FIELD_LABELS),
}

# The members each shape names at its place, for the slips of record_format.md:588-589 "one slip (below) from
# a member the shape names at that place" and the members a result returns, read_side_contract.md:165 "Every
# member a result returns from a record holds the members the reader's version defines".
# record_format.md:86 "| Member | Required | Contents |"
ENVELOPE_NAMES: Final = (
    "schema_version", "record_type", "id", "version", "name", "licence", "content_hash", "card", "body"
)  # fmt: skip
# record_format.md:16 "`licence` is an object whose `values` and `evidence` (both required) are strings"
LICENCE_NAMES: Final = ("values", "evidence")
# record_format.md:17-18 "`sections` (required) and `extensions` are objects"
MATERIAL_BODY_NAMES: Final = ("sections", "extensions")
# record_format.md:144-145 "A section holds `fields`" and "optionally `specimen`"
SECTION_NAMES: Final = ("specimen", "fields")
# record_format.md:326 "| Member | Required | Contents |"
VALUE_FIELD_NAMES: Final = (
    "form", "unit", *dict.fromkeys(FORM_MEMBERS.values()), "conditions", "specimen", "statistics",
    "provenance", "label", "label_basis", "fit",
)  # fmt: skip
# Both shapes are named at a field's place, so a slip of `alternatives` beside a value field's members is
# refused (the maintainer's ruling, 2026-10-19, as built): record_format.md:324 "A value field is an object
# with these members, or an `alternatives` object (below)."
FIELD_PLACE_NAMES: Final = (*VALUE_FIELD_NAMES, "alternatives")
# read_side_contract.md:335-336 "a table's `axis`, `axis_unit` (as a string or a status object), `x`, `y`,
# `scheme`, `edges` and `source_range`"
TABLE_MEMBERS: Final = ("axis", "axis_unit", "x", "y", "scheme", "edges", "source_range")
# record_format.md:437-438 "`points` counts as a member named at a table's place"
TABLE_RESERVED: Final = ("points",)
TABLE_NAMES: Final = (*TABLE_MEMBERS, *TABLE_RESERVED)
# record_format.md:404 "`edges` is required: a list of numbers"; record_format.md:427 "`source_range`, where
# present"
TABLE_REQUIRED: Final = ("axis", "axis_unit", "x", "y", "scheme", "edges")
# provenance.md:46-47 "for a condition, `value`," and "`range`, `token`, `unit`, `basis`, `inferred_from`"
CONDITION_NAMES: Final = (
    "value", "range", "token", "unit", "basis", "inferred_from", "plus_minus", "set_or_measured"
)  # fmt: skip
NUMERIC_CONDITION_ONLY: Final = ("value", "range", "plus_minus", "set_or_measured")
# provenance.md:263 "numeric condition: a non-empty list of"
PLUS_MINUS_NAMES: Final = ("stated_as", "value", "unit")
# uncertainty.md:29 "| Member | Contents |"
BLOCK_MEMBERS: Final = (
    "central", "n_specimens", "n_donors", "mean", "sd", "min", "max", "distribution", "basis", "represents",
    "dispersion", "relative_uncertainty", "expanded_uncertainty",
)  # fmt: skip
# uncertainty.md:58-59 "each present exactly where the `represents` beside it is `population`,
# `across_sources`"
CONDITIONAL_BLOCK_MEMBERS: Final[Mapping[str, str]] = {
    "population_level": "population",
    "n_sources": "across_sources",
    "precision_conditions": "measurement",
}
BLOCK_NAMES: Final = (*BLOCK_MEMBERS, *CONDITIONAL_BLOCK_MEMBERS)
# The status tokens of each of a block's members that holds a token: provenance.md:27 "| in a statistics
# block, `represents` | `unstated`, `not_applicable` |"
BLOCK_TOKEN_MEMBERS: Final[Mapping[str, tuple[tuple[str, ...], frozenset[str]]]] = {
    "central": (CENTRALS, frozenset({"not_applicable"})),
    "basis": (BLOCK_BASES, frozenset({"not_applicable"})),
    "distribution": (BLOCK_DISTRIBUTIONS, frozenset({"unstated"})),
    "represents": (REPRESENTS, frozenset({"unstated", "not_applicable"})),
    "precision_conditions": (PRECISION_CONDITIONS, frozenset({"unstated"})),
}
BLOCK_COUNTS: Final = ("n_specimens", "n_donors", "n_sources")
POPULATION_LEVEL_NAMES: Final = ("level", "within")
# uncertainty.md:41 "| `relative_uncertainty` |"
UNCERTAINTY_MEMBERS: Final = (
    "value", "coverage_factor", "coverage_probability", "distribution", "dof", "basis", "represents"
)  # fmt: skip
UNCERTAINTY_NAMES: Final = (*UNCERTAINTY_MEMBERS, "precision_conditions")
# provenance.md:90 "| Member | Required | Contents |"
PROVENANCE_NAMES: Final = (
    "origin", "source", "extraction", "evidence", "assistance", "review", "derivation", "formulation",
    "search", "import", "per_parameter", "recipe",
)  # fmt: skip
# provenance.md:93 "`key` in the source registry (section 8); `document`"
SOURCE_NAMES: Final = ("key", "document", "locator")
# The members a review names, as the example review holds them, with a status object's:
# provenance.md:97 "with who checked the value against the source, their ORCID, the date, whether they are
# independent of whoever or whatever extracted it, and the checklist items covered"
REVIEW_NAMES: Final = (
    "status", "reason", "result", "reviewer", "orcid", "date", "independent_of_extraction", "checklist"
)  # fmt: skip
# Those a reviewed review returns, a status object's aside: provenance.md:97 "or `{"result": "reviewed", ...}`
# with who checked the value against the source"
RESULT_REVIEW_NAMES: Final = tuple(name for name in REVIEW_NAMES if name not in ("status", "reason"))
# provenance.md:196-198 "holds `method`, the method's identifier, a string; `inputs`"
DERIVATION_NAMES: Final = ("method", "inputs", "assumptions", "input_specimens", "mixed_conditions")
INPUT_NAMES: Final = ("record", "field")
INPUT_SPECIMEN_NAMES: Final = ("input", "specimen")
REFERENCE_NAMES: Final = ("id", "version", "content_hash")
# record_format.md:466 "`lower` and `upper` are numbers"
INTERVAL_NAMES: Final = ("lower", "upper", "basis")
# record_format.md:492-493 "its basis, sum rule, stated sum where present, and components"
COMPOSITION_NAMES: Final = ("basis", "sum_rule", "stated_sum", "components")
COMPONENT_NAMES: Final = ("component", "fraction", "statistics")
# record_format.md:237-238 "Each entry holds `endpoint`, `standard`"
EVIDENCE_ENTRY_NAMES: Final = (
    "endpoint", "standard", "contact_category", "contact_duration", "material_form", "processing",
    "reported_result", "provenance",
)  # fmt: skip
STANDARD_NAMES: Final = ("designation", "year")

# read_side_contract.md:11 "| Member | Contents |", and the shape at read_side_contract.md:20-21 "Its shape,
# apart from `records`, which is supplied beside it, is exactly this"
REQUEST_NAMES: Final = ("records", "target", "operating_conditions", "requirement", "acceptances")
TARGET_NAMES: Final = ("field", "record", "region")
OPERATING_NAMES: Final = ("value", "range", "unit")
# read_side_contract.md:40-41 "a member one slip (`record_format.md` section 10) from a member this section or
# `declarations.md` names at that place": a requirement names `field` there (declarations.md:30
# "fluid.dynamic_viscosity", the example's) and each of its conditions a `reason` and a `consequence`
# (declarations.md:64 "each with its `reason` and, where known, its `consequence`"), which a read ignores and
# of which it refuses a slip: the text decides it, as S2a-4's review read it, the maintainer's approval
# (2026-10-18) and ruling (2026-10-19) on the former open point `names_a_declaration_gives_a_requirement`.
REQUIREMENT_NAMES: Final = (
    "want",
    "conditions",
    "label",
    "represents",
    "population_level",
    "review",
    "field",
)
REQUIREMENT_CONDITION_NAMES: Final = ("tolerance", "accept", "reason", "consequence")
TOLERANCE_NAMES: Final = ("value", "unit")
# read_side_contract.md:37 "its `requirement` holds `label`, `represents`, `population_level` or `review`"
DECLARATION_ONLY_REQUIREMENT_NAMES: Final = ("label", "represents", "population_level", "review")
IMPLIED_VALUE_NAMES: Final = (*CONDITION_NAMES, "status", "reason")

# read_side_contract.md:32 "its field does not match `^[a-z0-9_]+\.[a-z0-9_]+$` in full"
FIELD_PATTERN: Final = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+")
# record_format.md:541 "`^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`"
VERSION_PATTERN: Final = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
# record_format.md:523 "A namespace matches `[a-z0-9_]+`"; record_format.md:532 "the local id matching"
ID_PATTERN: Final = re.compile(r"[a-z0-9_]+/[A-Za-z0-9_.-]+")
# record_format.md:94 "`sha256:` and 64 lowercase hexadecimal digits"
HASH_PATTERN: Final = re.compile(r"sha256:[0-9a-f]{64}")
# README.md:66 "a reader reads only records of its own `MAJOR.MINOR`"
READER_MAJOR_MINOR: Final = ("0", "1")

# Reasons, results and what the model does not decide


@dataclass(frozen=True)
class Reason:
    code: str
    condition: str | None = None
    alternative: int | None = None


class Reasons:
    """The reasons a read has found, each once: read_side_contract.md:139-140 "A reason, identified by its
    `code`, its `condition` and its `alternative`, appears at most once in a result"."""

    def __init__(self, found: Iterable[Reason] = ()) -> None:
        self._found: dict[Reason, None] = dict.fromkeys(found)

    def add(self, code: str, condition: str | None = None) -> None:
        self._found[Reason(code, condition)] = None

    def extend(self, other: Iterable[Reason]) -> None:
        for reason in other:
            self._found[reason] = None

    def found_in(self, index: int) -> "Reasons":
        # read_side_contract.md:146-148 "A reason carries `alternative` exactly when it was found at steps 8
        # to 13 while reading one alternative"
        return Reasons(Reason(reason.code, reason.condition, index) for reason in self._found)

    def __iter__(self) -> Iterator[Reason]:
        return iter(self._found)

    def __bool__(self) -> bool:
        return bool(self._found)

    @property
    def status(self) -> Status:
        return worst(REASONS[reason.code].status for reason in self._found)

    def end_the_read(self) -> bool:
        # read_side_contract.md:186 "A step that gives `not_met` ends the read"
        return self.status == "not_met"

    def of_status(self, status: Status) -> "Reasons":
        return Reasons(reason for reason in self._found if REASONS[reason.code].status == status)

    def to_json(self) -> list[JsonValue]:
        # read_side_contract.md:124 "a list of `{"code", "condition"?, "alternative"?, "detail"?}`"
        found: list[JsonValue] = []
        for reason in self._found:
            given: JsonObject = {"code": reason.code}
            if reason.condition is not None:
                given["condition"] = reason.condition
            if reason.alternative is not None:
                # JSON numbers read as doubles (strict_json.parse), an index among them
                given["alternative"] = float(reason.alternative)
            found.append(given)
        return found


def worst(statuses: Iterable[Status]) -> Status:
    found = list(statuses)
    return max(found, key=STATUSES_BEST_FIRST.index) if found else "met"


@dataclass(frozen=True)
class NoVerdict:
    """A read the model does not decide, and why: never a pass, never a refusal."""

    why: str


class _Undecided(Exception):
    def __init__(self, why: str) -> None:
        super().__init__(why)
        self.why = why


# The acceptances the model does not apply, and the piece whose steps do.
UNDECIDED_ACCEPTANCES: Final[Mapping[str, str]] = {
    "pick": "a pick acceptance (S4)",
    "overlay": "an overlay acceptance (S4)",
    "trainable": "a trainable acceptance (S7a-4)",
}


# What every step's checks share


def number(value: JsonValue) -> TypeGuard[float]:
    return isinstance(value, float)


def whole(value: JsonValue) -> TypeGuard[float]:
    # record_format.md:73-74 "whether it is whole is a check of its value, made where the member is used"
    return isinstance(value, float) and value.is_integer()


def not_negative(value: JsonValue) -> TypeGuard[float]:
    return isinstance(value, float) and value >= 0


def ordered_pair(value: JsonValue) -> bool:
    if not (isinstance(value, list) and len(value) == 2):
        return False
    low, high = value
    return number(low) and number(high) and low <= high


def one_slip(name: str, other: str) -> bool:
    """record_format.md:601-602 "Two names are **one slip** apart when one becomes the other by inserting,
    deleting or substituting one character", an underscore included, counting code points, or by swapping two
    adjacent ones, or making one `_`-separated word plural or singular."""
    if name == other:
        return False
    if len(name) == len(other):
        differ = [index for index, (a, b) in enumerate(zip(name, other, strict=True)) if a != b]
        if len(differ) == 1:
            return True
        if (
            len(differ) == 2
            and differ[1] == differ[0] + 1
            and (name[differ[0]], name[differ[1]]) == (other[differ[1]], other[differ[0]])
        ):
            return True
    if abs(len(name) - len(other)) == 1:
        shorter, longer = sorted((name, other), key=len)
        if any(longer[:index] + longer[index + 1 :] == shorter for index in range(len(longer))):
            return True
    words, other_words = name.split("_"), other.split("_")
    if len(words) != len(other_words):
        return False
    differ = [index for index, (a, b) in enumerate(zip(words, other_words, strict=True)) if a != b]
    return len(differ) == 1 and _plural_of_either(words[differ[0]], other_words[differ[0]])


def _plural_of_either(word: str, other: str) -> bool:
    # record_format.md:603-604 "`s` or `es` added at its end or taken off it, a final `y` exchanged with
    # `ies`, or `datum` with `data`, `index` with `indices` or `matrix` with `matrices`"
    irregular = {("datum", "data"), ("index", "indices"), ("matrix", "matrices")}
    for singular, plural in ((word, other), (other, word)):
        if not singular:
            continue  # an empty word, between two underscores, has no plural
        if plural in (singular + "s", singular + "es") or (singular, plural) in irregular:
            return True
        if singular.endswith("y") and plural == singular[:-1] + "ies":
            return True
    return False


def slipped(value: JsonObject, named: Iterable[str]) -> bool:
    """Whether `value` holds a member one slip from a member named at its place: record_format.md:588 "refuses
    a member it does not know, where items 1 and 4 would ignore or skip it, that is one slip"."""
    names = tuple(named)
    return any(member not in names and any(one_slip(member, name) for name in names) for member in value)


def known_token(value: JsonValue, member: str, allowed: Iterable[str], faults: Reasons) -> None:
    """A token in a member whose row allows `allowed`: read_side_contract.md:309-311 "a token the reader knows
    for a member of that name in a member whose row does not allow it (`form_invalid`), a token the reader
    knows for no member of that name (`unknown_token`)"."""
    if not isinstance(value, str):
        faults.add("form_invalid")
    elif value not in tuple(allowed):
        faults.add("form_invalid" if value in KNOWN_TOKENS[member] else "unknown_token")


@dataclass(frozen=True)
class StatusObject:
    token: str | None  # None where the object breaks its shape


def status_object(
    value: JsonValue,
    faults: Reasons,
    *,
    allowed: frozenset[str],
    shape: tuple[str, ...] = (),
    named: tuple[str, ...] = (),
    scalar: bool = False,
    unit: bool = False,
) -> StatusObject | None:
    """The status object `value` is, in a member that may hold one, or None: provenance.md:44 "In a member of
    this table, an object holding `status` is a status object".

    `shape` names the members S defines; `named`, other names the text names at S's place, whose slips are
    refused; `scalar` says that S is a number, a string or a token; a unit's token is compared at step 9
    alone.
    """
    # provenance.md:44 "In a member of this table, an object holding `status` is a status object."
    if not (isinstance(value, dict) and "status" in value):
        return None
    token, reason = value["status"], value.get("reason", "")
    if not (
        # provenance.md:45 "where its `status` or `reason` is not a string, or where it also holds a"
        isinstance(token, str)
        and isinstance(reason, str)
        and not any(name in value for name in shape)
        # provenance.md:47-48 "Where S is a number, a string or a token, and there only, it does so also where
        # it holds any member but `status` and `reason`."
        and not (scalar and any(name not in ("status", "reason") for name in value))
        and not slipped(value, ("status", "reason", *shape, *named))
    ):
        # provenance.md:51-53 "A status object that breaks its shape is read for nothing else, so its token
        # gives no reason of its own"
        faults.add("form_invalid")
        return StatusObject(None)
    if not unit:
        # provenance.md:50-51 "A status token its row does not allow refuses the field as `form_invalid`, and
        # one the reader does not know as `unknown_token`."
        if token not in STATUS_TOKENS:
            faults.add("unknown_token")
        elif token not in allowed:
            faults.add("form_invalid")
    return StatusObject(token)


def copied(value: JsonValue) -> JsonValue:
    """A deep copy: a result shares nothing with the record it was read from."""
    if isinstance(value, list):
        return [copied(item) for item in value]
    if isinstance(value, dict):
        return {name: copied(member) for name, member in value.items()}
    return value


def status_returned(value: JsonObject) -> JsonObject:
    # read_side_contract.md:166 "numbers as read, status objects as status objects"
    return {name: copied(value[name]) for name in ("status", "reason") if name in value}


# Step 0: the request on its own (read_side_contract.md section 1)


@dataclass(frozen=True)
class Reference:
    id: str
    version: str
    content_hash: str


@dataclass(frozen=True)
class ImpliedCondition:
    fact: str
    token: str
    # by condition, the value it supplies: its known members, without `basis`
    implies: Mapping[str, JsonObject]


@dataclass(frozen=True)
class Request:
    reference: Reference | None  # None for a region target
    field: str
    want: str
    operating: Mapping[str, JsonObject]
    tolerances: Mapping[str, float]
    accepts: Mapping[str, tuple[str, ...]]
    implied: tuple[ImpliedCondition, ...]  # those that apply to this read: its field, at its record
    nominal: float | None  # the nominal that applies to this read
    # the extrapolation that applies to this read: its own members as the request gives them, `basis` aside
    extrapolation: JsonObject | None = None


def reference_of(value: JsonValue) -> Reference | None:
    if not isinstance(value, dict):
        return None
    id_, version, hash_ = value.get("id"), value.get("version"), value.get("content_hash")
    if isinstance(id_, str) and isinstance(version, str) and isinstance(hash_, str):
        return Reference(id_, version, hash_)
    return None


def check_request(request: JsonValue, claims: frozenset[str], reasons: Reasons) -> Request | None:
    """Step 0. The request's reasons go into `reasons`; the request is returned where it passes."""

    def incomplete(condition: str | None = None) -> None:
        reasons.add("request_incomplete", condition)

    # read_side_contract.md:29 "it is not valid JSON by that item, or departs from that shape in any way"
    if not isinstance(request, dict):
        incomplete()
        return None
    # read_side_contract.md:40-42 "it holds, at any depth, a member one slip (`record_format.md` section 10)
    # from a member this section or `declarations.md` names at that place, refused ones included"
    if slipped(request, REQUEST_NAMES):
        incomplete()
    target = request.get("target")
    field_name = reference = None
    region = False
    if not isinstance(target, dict):
        incomplete()
    else:
        if slipped(target, TARGET_NAMES):
            incomplete()
        field_name = registered_field(target.get("field"))
        if field_name is None:
            incomplete()
        # read_side_contract.md:30 "a target with both or neither of record and region"
        if ("record" in target) == ("region" in target):
            incomplete()
        elif "record" in target:
            record = target["record"]
            if isinstance(record, dict) and slipped(record, REFERENCE_NAMES):
                incomplete()
            reference = reference_of(record)
            if reference is None:
                incomplete()
        elif isinstance(target["region"], str):
            region = True
        else:
            incomplete()
    operating = checked_operating(request, reasons)
    want, tolerances, accepts = checked_requirement(request, claims, reasons)
    implied, nominal, extrapolation = checked_acceptances(request, field_name, reference, reasons)
    if reasons.end_the_read() or field_name is None or want is None:
        return None
    if region:
        raise _Undecided("a region target is read through a scene (the scene suite)")
    return Request(
        reference, field_name, want, operating, tolerances, accepts, implied, nominal, extrapolation
    )


def registered_field(value: JsonValue) -> str | None:
    # read_side_contract.md:32-34 "its field does not match" and "its field is not registered"
    if isinstance(value, str) and FIELD_PATTERN.fullmatch(value) and value in FIELDS:
        return value
    return None


def checked_operating(request: JsonObject, reasons: Reasons) -> dict[str, JsonObject]:
    operating: dict[str, JsonObject] = {}
    given = request.get("operating_conditions", {})
    if not isinstance(given, dict):
        reasons.add("request_incomplete")
        return operating
    for name, entry in given.items():
        row = CONDITIONS.get(name)
        # read_side_contract.md:36 "it names a condition that is not registered"
        # read_side_contract.md:25 "and is given only for a numeric condition"
        if row is None or row.shape == "token" or not isinstance(entry, dict):
            reasons.add("request_incomplete", name)
            continue
        supplied = numeric_value(entry, row, name, OPERATING_NAMES, reasons)
        if supplied is not None:
            operating[name] = supplied
    return operating


def numeric_value(
    entry: JsonObject, row: ConditionRow, name: str, named: tuple[str, ...], reasons: Reasons
) -> JsonObject | None:
    """An operating condition, or the value an implied condition supplies, checked as
    read_side_contract.md:24-25 "exactly one of `{"value", "unit"}` and `{"range": [lo, hi], "unit"}`, with
    numbers and a string unit" and read_side_contract.md:44 "an operating range whose `lo` is greater than its
    `hi`" say, its unit as read_side_contract.md:52-53 "has a string `unit` other than the condition's
    registered unit" says; its known members where it is whole."""
    if slipped(entry, named):
        reasons.add("request_incomplete", name)
    unit = entry.get("unit")
    if request_unit_differs(unit, row):
        reasons.add("request_unit_mismatch", name)
    # read_side_contract.md:23-24 "an operating condition is exactly one of"
    has_value, has_range = "value" in entry, "range" in entry
    shaped = (
        has_value != has_range
        and (not has_value or number(entry["value"]))
        and (not has_range or two_numbers(entry["range"]))
        and isinstance(unit, str)
    )
    if not shaped:
        reasons.add("request_incomplete", name)
        return None
    # read_side_contract.md:43-44 "an operating range whose `lo` is greater than its `hi`"
    if has_range and not ordered_pair(entry["range"]):
        reasons.add("request_incomplete", name)
        return None
    return {member: copied(entry[member]) for member in OPERATING_NAMES if member in entry}


def request_unit_differs(unit: JsonValue, row: ConditionRow) -> bool:
    # read_side_contract.md:51-55 "where an operating condition or tolerance of a registered numeric condition
    # has a string `unit` other than the condition's registered unit, whatever else is wrong with that entry.
    # Units are compared as strings, after JSON escapes are decoded, code point for code point"
    return isinstance(unit, str) and unit != row.unit


def two_numbers(value: JsonValue) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(number(end) for end in value)


def checked_requirement(
    request: JsonObject, claims: frozenset[str], reasons: Reasons
) -> tuple[str | None, dict[str, float], dict[str, tuple[str, ...]]]:
    tolerances: dict[str, float] = {}
    accepts: dict[str, tuple[str, ...]] = {}
    requirement = request.get("requirement")
    if not isinstance(requirement, dict):
        reasons.add("request_incomplete")
        return None, tolerances, accepts
    if slipped(requirement, REQUIREMENT_NAMES) or any(
        name in requirement for name in DECLARATION_ONLY_REQUIREMENT_NAMES
    ):
        reasons.add("request_incomplete")
    want = requirement.get("want")
    # read_side_contract.md:35 "its `want` is not one of section 6's tokens"
    if not (isinstance(want, str) and want in WANTS):
        reasons.add("request_incomplete")
        want = None
    elif want in FITS_AND_REFERENCE_DATA_WANTS and "fits_and_reference_data" not in claims:
        # read_side_contract.md:49-51 "A request whose `want` belongs to a suite the reader does not claim is
        # refused at the same step, with the reason `want_mismatch`"
        reasons.add("want_mismatch")
    conditions = requirement.get("conditions", {})
    if not isinstance(conditions, dict):
        reasons.add("request_incomplete")
        return want, tolerances, accepts
    given_operating = request.get("operating_conditions", {})
    for name, entry in conditions.items():
        row = CONDITIONS.get(name)
        if row is None or not isinstance(entry, dict):
            reasons.add("request_incomplete", name)
            continue
        if slipped(entry, REQUIREMENT_CONDITION_NAMES):
            reasons.add("request_incomplete", name)
        if row.shape == "token":
            accept = entry.get("accept")
            # read_side_contract.md:30-31 "a `tolerance` for a token condition or an `accept` list for a
            # numeric one"
            if "tolerance" in entry:
                reasons.add("request_incomplete", name)
            if isinstance(accept, list) and all(isinstance(token, str) for token in accept):
                accepts[name] = tuple(token for token in accept if isinstance(token, str))
            else:
                reasons.add("request_incomplete", name)
            continue
        if "accept" in entry:
            reasons.add("request_incomplete", name)
        tolerance = entry.get("tolerance")
        if not isinstance(tolerance, dict):
            reasons.add("request_incomplete", name)
            continue
        if slipped(tolerance, TOLERANCE_NAMES):
            reasons.add("request_incomplete", name)
        value, unit = tolerance.get("value"), tolerance.get("unit")
        if request_unit_differs(unit, row):
            reasons.add("request_unit_mismatch", name)
        # read_side_contract.md:43 "a tolerance below zero (`-0` is not)"
        if isinstance(value, float) and value >= 0 and isinstance(unit, str):
            tolerances[name] = value
        else:
            reasons.add("request_incomplete", name)
        # read_side_contract.md:43 "it gives a tolerance for a condition with no operating condition"
        # read_side_contract.md:47-49 "A tolerance whose condition has no operating entry because
        # `operating_conditions` is not an object gives `request_incomplete` with that `condition`"
        if not (isinstance(given_operating, dict) and name in given_operating):
            reasons.add("request_incomplete", name)
    return want, tolerances, accepts


def checked_acceptances(
    request: JsonObject, field_name: str | None, reference: Reference | None, reasons: Reasons
) -> tuple[tuple[ImpliedCondition, ...], float | None, JsonObject | None]:
    """read_side_contract.md:68-69 "Each acceptance is checked here, whatever field or location it names":
    every acceptance checked; those of this read's field at its record returned."""
    given = request.get("acceptances", [])
    if not isinstance(given, list):
        reasons.add("request_incomplete")
        return (), None, None
    implied: list[ImpliedCondition] = []
    nominals: list[float] = []
    extrapolations: list[JsonObject] = []
    # read_side_contract.md:71-72 "So do two acceptances of one kind, `nominal`, `extrapolation`, `pick` or
    # `trainable`, that name one field": the fields each kind names, as written
    named: dict[str, list[str]] = {"nominal": [], "extrapolation": []}
    for acceptance in given:
        if not isinstance(acceptance, dict):
            reasons.add("request_incomplete")
            continue
        kind = acceptance.get("acceptance")
        if isinstance(kind, str) and kind in UNDECIDED_ACCEPTANCES:
            raise _Undecided(UNDECIDED_ACCEPTANCES[kind])
        # read_side_contract.md:70-71 "An acceptance of any other kind, or one that breaks its shape, gives
        # `request_incomplete`"
        if not isinstance(kind, str) or kind not in READ_ACCEPTANCE_KINDS:
            reasons.add("request_incomplete")
            continue
        if slipped(acceptance, (*ACCEPTANCE_NAMES, *ACCEPTANCE_OWN_NAMES[kind])):
            reasons.add("request_incomplete")
        location = acceptance.get("record")
        if isinstance(location, dict) and slipped(location, REFERENCE_NAMES):
            reasons.add("request_incomplete")
        # read_side_contract.md:69 "its `field` as the target's is (the pattern, and a registered field)"
        named_field = registered_field(acceptance.get("field"))
        if named_field is None:
            reasons.add("request_incomplete")
        applies = named_field is not None and named_field == field_name and at_the_read(acceptance, reference)
        if kind in named and isinstance(acceptance.get("field"), str):
            named[kind].append(str(acceptance["field"]))
        if kind == "extrapolation":
            method, law = acceptance.get("method"), acceptance.get("law")
            # declarations.md:369 "`method` (`constant` or `consumer_law`), `law` (text of at least one
            # character, which a reader does not judge)"
            if method not in EXTRAPOLATION_METHODS or not is_law(law):
                reasons.add("request_incomplete")
            elif applies:
                # read_side_contract.md:133 "with its kind's own members as the request gives them, `basis`
                # aside"
                extrapolations.append({"acceptance": "extrapolation", "method": method, "law": law})
        elif kind == "nominal":
            value = acceptance.get("value")
            # read_side_contract.md:77-79 "A nominal takes `params` in place of `value` only where the row of
            # the field it names allows the form `parameter_set`": no row the model's FIELDS hold allows one.
            if not isinstance(value, float):
                reasons.add("request_incomplete")
            elif applies:
                nominals.append(value)
        else:
            checked = checked_implied_condition(acceptance, reasons)
            if checked is not None and applies:
                implied.append(checked)
    # read_side_contract.md:71-73 "So do two acceptances of one kind, `nominal`, `extrapolation`, `pick` or
    # `trainable`, that name one field, whatever location or other members each holds": a pick or a
    # `trainable` acceptance gives no verdict above (S7a-4 builds the last), so nominals and extrapolations
    # are counted here.
    if any(len(fields) != len(set(fields)) for fields in named.values()):
        reasons.add("request_incomplete")
    return (
        tuple(implied),
        nominals[0] if nominals else None,
        extrapolations[0] if extrapolations else None,
    )


def is_law(value: JsonValue) -> TypeGuard[str]:
    """declarations.md:369 "`law` (text of at least one character, which a reader does not judge)": a string
    of one code point or more, white space alone included, since a reader does not judge what it says."""
    return isinstance(value, str) and len(value) >= 1


def at_the_read(acceptance: JsonObject, reference: Reference | None) -> bool:
    # read_side_contract.md:89-96 "only at the read's own location: its `record`, its `region` or both, each
    # the read's" ... "One naming another field, another record or region, an `interval`" ... "or no location
    # is checked and not applied"
    if "region" in acceptance or "interval" in acceptance or "record" not in acceptance:
        return False
    return reference is not None and reference_of(acceptance["record"]) == reference


def checked_implied_condition(acceptance: JsonObject, reasons: Reasons) -> ImpliedCondition | None:
    """An implied condition's shape, and its units: read_side_contract.md:80 "An implied condition breaks its
    shape" and declarations.md:367 "| `implied_condition` | `region`, `interval` or `record` |"."""
    whole_shape = True
    fact, token, implies = acceptance.get("fact"), acceptance.get("token"), acceptance.get("implies")
    # read_side_contract.md:80-81 "where its `fact` is not a specimen fact with tokens or its `token` is not
    # one of that fact's"
    row = FACTS.get(fact) if isinstance(fact, str) else None
    if row is None or not row.tokens:
        reasons.add("request_incomplete")
        whole_shape = False
    elif not (isinstance(token, str) and token in row.tokens):
        reasons.add("request_incomplete")
        whole_shape = False
    if not isinstance(implies, dict):
        reasons.add("request_incomplete")
        return None
    values: dict[str, JsonObject] = {}
    for name, value in implies.items():
        supplied = implied_value(name, value, reasons)
        if supplied is None:
            whole_shape = False
        else:
            values[name] = supplied
    if not whole_shape or not isinstance(fact, str) or not isinstance(token, str):
        return None
    return ImpliedCondition(fact, token, values)


def implied_value(name: str, value: JsonValue, reasons: Reasons) -> JsonObject | None:
    condition = CONDITIONS.get(name)
    # read_side_contract.md:86-87 "A value an implied condition supplies for a registered numeric condition is
    # checked as an operating condition is, its `unit` included", and an operating condition's unit
    # read_side_contract.md:51-53 "where an operating condition or tolerance of a registered numeric condition
    # has a string `unit` other than the condition's registered unit, whatever else is wrong with that entry":
    # whatever else the value breaks below
    if condition is not None and condition.shape == "numeric" and isinstance(value, dict):
        if request_unit_differs(value.get("unit"), condition):
            reasons.add("request_unit_mismatch", name)
    # read_side_contract.md:81-82 "where `implies` names a condition that is not registered, or gives one a
    # status object, `plus_minus`, `set_or_measured` or a token outside the condition's row"
    if condition is None or not isinstance(value, dict) or "status" in value:
        reasons.add("request_incomplete", name)
        return None
    if "plus_minus" in value or "set_or_measured" in value:
        reasons.add("request_incomplete", name)
        return None
    # read_side_contract.md:83-84 "It breaks its shape too (`request_incomplete`, with that `condition`) where
    # `implies` gives a numeric condition a `token`, or a token condition a `value`, `range` or `unit`" (the
    # maintainer's ruling, 2026-10-18), as the same members in a record do since the ruling of 2026-10-19
    # (`provenance.md` section 6.1 item 1, `holds_another_kind`).
    if condition.shape == "token":
        if slipped(value, IMPLIED_VALUE_NAMES) or holds_another_kind(value, ("value", "range", "unit")):
            reasons.add("request_incomplete", name)
            return None
        token = value.get("token")
        if not (isinstance(token, str) and token in condition.tokens):
            reasons.add("request_incomplete", name)
            return None
        return {"token": token}
    if holds_another_kind(value, ("token",)):
        reasons.add("request_incomplete", name)
        return None
    # read_side_contract.md:86-87 "A value an implied condition supplies for a registered numeric condition is
    # checked as an operating condition is, its `unit` included"
    return numeric_value(value, condition, name, IMPLIED_VALUE_NAMES, reasons)


# Steps 1 to 5: the record (read_side_contract.md section 3)


@dataclass(frozen=True)
class Source:
    value: JsonValue | NotStrictJson
    data: bytes


def sources_read(sources: Sequence[bytes]) -> list[Source]:
    # read_side_contract.md:201 "Every supplied source is read as JSON (`record_format.md` section 1 item 6)."
    found: list[Source] = []
    for data in sources:
        try:
            found.append(Source(parse(data), data))
        except NotStrictJson as fault:
            found.append(Source(fault, data))
    return found


def set_aside(value: JsonValue | NotStrictJson) -> bool:
    # read_side_contract.md:201-202 "An object with a `document_type` and no `record_type` is set aside"
    return isinstance(value, dict) and "document_type" in value and "record_type" not in value


def candidate(value: JsonValue | NotStrictJson) -> bool:
    # read_side_contract.md:205 "Every other object whose `id` and `version` are strings is a **candidate**"
    return (
        isinstance(value, dict)
        and not set_aside(value)
        and isinstance(value.get("id"), str)
        and isinstance(value.get("version"), str)
    )


def unreadable(value: JsonValue | NotStrictJson) -> bool:
    # read_side_contract.md:202-204 "A source that did not parse, or parsed to a value that is neither a
    # set-aside document nor an object with a string `id` and a string `version`, is **unreadable**."
    return not (set_aside(value) or candidate(value))


def resolve(
    reference: Reference,
    sources: Sequence[Source],
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
) -> JsonObject | None:
    """Steps 1 to 5: the record the reference names, or None with the reasons."""
    any_unreadable = any(unreadable(source.value) for source in sources)
    candidates = [
        (source.value, source.data)
        for source in sources
        if isinstance(source.value, dict)
        and candidate(source.value)
        and (source.value["id"], source.value["version"]) == (reference.id, reference.version)
    ]
    if not candidates:
        # read_side_contract.md:208-209 "the read gives `absent`, unless a supplied source is unreadable: then
        # it gives `malformed`"
        reasons.add("malformed" if any_unreadable else "absent")
        return None
    pinned = [
        (value, data) for value, data in candidates if value.get("content_hash") == reference.content_hash
    ]
    if not pinned:
        # read_side_contract.md:214-217 "the read gives `malformed` when a supplied source is unreadable, or
        # when one of the candidates" ... "has a `content_hash` that is absent, not a string, or not
        # `sha256:`"
        ill_formed = any(not well_formed_hash(value.get("content_hash")) for value, _ in candidates)
        reasons.add("malformed" if any_unreadable or ill_formed else "pin_mismatch")
        return None
    # read_side_contract.md:212-213 "With two or more whose bytes are all identical, it reads one; with two or
    # more whose bytes differ, the read gives `malformed`."
    if len({data for _, data in pinned}) > 1:
        reasons.add("malformed")
        return None
    record = pinned[0][0]
    if not version_and_structure_pass(record, reasons):
        return None
    # read_side_contract.md:224-228 "A reader that claims the HS suite also recomputes the hash" ... "A reader
    # that does not claim HS labels `hash_not_checked` every result that reaches this step"
    if "hash" in claims:
        if content_hash(record) != record["content_hash"]:
            reasons.add("hash_mismatch")
            reasons.add("pin_mismatch")
            return None
    else:
        labels.append("hash_not_checked")
    # read_side_contract.md:230-231 "Refuse a referenced record of a type the reader cannot read in its role
    # (`unknown_type`): a target's record that is not a `material`, however the target is named"
    if record["record_type"] != "material":
        reasons.add("unknown_type")
        return None
    return record


def well_formed_hash(value: JsonValue) -> bool:
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def version_and_structure_pass(record: JsonObject, reasons: Reasons) -> bool:
    # read_side_contract.md:219-221 "Read `schema_version`: absent, not a string, or not matching" ... "gives
    # `malformed`; another `MAJOR.MINOR` (before 1.0.0) gives `other_version`"
    schema_version = record.get("schema_version")
    match = VERSION_PATTERN.fullmatch(schema_version) if isinstance(schema_version, str) else None
    if match is None:
        reasons.add("malformed")
        return False
    if match.group(1, 2) != READER_MAJOR_MINOR:
        reasons.add("other_version")
        return False
    # read_side_contract.md:222 "**Validate** the envelope and the body's structure against the reader schema"
    if not reader_schema_accepts(record):
        reasons.add("malformed")
        return False
    return True


def reader_schema_accepts(record: JsonObject) -> bool:
    """The reader schema's checks of the envelope and the body's structure: record_format.md:14 "the **reader
    schema** is open. It checks the envelope"."""
    strings = ("schema_version", "record_type", "id", "version", "name", "content_hash")
    # record_format.md:14-15 "every member section 2 marks required is present and every member is of its JSON
    # type"
    if not all(isinstance(record.get(name), str) for name in strings):
        return False
    if "card" in record and not isinstance(record["card"], str):
        return False
    licence, body = record.get("licence"), record.get("body")
    if not (isinstance(licence, dict) and isinstance(body, dict)):
        return False
    if not all(isinstance(licence.get(name), str) for name in LICENCE_NAMES):
        return False
    # record_format.md:15-16 "`id`, `version` and `content_hash` match their patterns"
    id_, version, hash_ = record["id"], record["version"], record["content_hash"]
    if not (
        isinstance(id_, str)
        and ID_PATTERN.fullmatch(id_)
        and isinstance(version, str)
        and VERSION_PATTERN.fullmatch(version)
        and well_formed_hash(hash_)
    ):
        return False
    if record["record_type"] == "material":
        return material_body_accepted(body)
    if record["record_type"] == "overlay":
        return overlay_body_accepted(body)
    return True


def material_body_accepted(body: JsonObject) -> bool:
    # record_format.md:17-20 "in a material body, `sections` (required) and `extensions` are objects, and each
    # member of `sections` named as a section of that version is an object whose `fields` (required) is an
    # object"
    sections = body.get("sections")
    if not isinstance(sections, dict):
        return False
    if "extensions" in body and not isinstance(body["extensions"], dict):
        return False
    return all(
        isinstance(section, dict) and isinstance(section.get("fields"), dict)
        for name, section in sections.items()
        if name in SECTIONS
    )


def overlay_body_accepted(body: JsonObject) -> bool:
    # record_format.md:20-24 "in an overlay body (section 4.4), whose four members are all required"
    purpose, base, scope, replaces = (body.get(name) for name in ("purpose", "base", "scope", "replaces"))
    if not (isinstance(purpose, str) and reference_of(base) is not None and isinstance(replaces, dict)):
        return False
    if not (isinstance(scope, dict) and isinstance(scope.get("consumer"), str)):
        return False
    model = scope.get("model")
    if "model" in scope and not (
        isinstance(model, dict)
        and isinstance(model.get("name"), str)
        and isinstance(model.get("version"), str)
    ):
        return False
    return all(isinstance(scope[name], str) for name in ("model_configuration_hash", "run") if name in scope)


def list_records(sources: Sequence[bytes]) -> JsonObject:
    """The identity of each candidate that passes steps 2, 3 and 5 on its own: README.md:191-193 "the `{"id",
    "version"}` of exactly those sources that are candidates"."""
    listed: list[JsonValue] = []
    for source in sources_read(sources):
        value = source.value
        if not (isinstance(value, dict) and candidate(value)):
            continue
        if version_and_structure_pass(value, Reasons()) and value["record_type"] in ("material", "overlay"):
            entry: JsonValue = {"id": value["id"], "version": value["version"]}
            if entry not in listed:
                listed.append(entry)
    return {"status": "met", "reasons": [], "value": listed}


def hash_operation(data: bytes) -> JsonObject:
    """The content hash of any JSON value, `malformed` for bytes item 6 refuses: README.md:186-188 "gives the
    content hash of its value, whatever that value's JSON type" and "a file that breaks item 6 gives `not_met`
    and `malformed`, and no value"."""
    try:
        value = parse(data)
    except NotStrictJson:
        return {"status": "not_met", "reasons": [{"code": "malformed"}]}
    return {"status": "met", "reasons": [], "value": content_hash(value)}


# Slips in the envelope, the body and a section, which refuse every field read from them


def record_slips(record: JsonObject) -> bool:
    # record_format.md:591-592 "in the envelope or the body, the names in `sections` included, each field read
    # from that record"
    body, licence = record["body"], record["licence"]
    if not (isinstance(body, dict) and isinstance(licence, dict)):
        return False
    sections = body.get("sections")
    return (
        slipped(record, ENVELOPE_NAMES)
        or slipped(licence, LICENCE_NAMES)
        or slipped(body, MATERIAL_BODY_NAMES)
        or (isinstance(sections, dict) and slipped(sections, tuple(SECTIONS)))
    )


def section_slips(section: JsonObject, section_name: str) -> bool:
    # record_format.md:590-591 "in a section, its `specimen` and the names in its `fields` included, each
    # field read from that section"
    fields = section.get("fields")
    field_names = tuple(name.partition(".")[2] for name in FIELDS if name.partition(".")[0] == section_name)
    return slipped(section, SECTION_NAMES) or (isinstance(fields, dict) and slipped(fields, field_names))


# Step 8: form and tokens, read_side_contract.md:305 "8. **Form and tokens.**"


def check_value_field(
    field_value: JsonValue,
    section: JsonObject,
    field_name: str,
    claims: frozenset[str],
    *,
    record_fault: bool,
) -> tuple[Reasons, str | None]:
    """Step 8's reasons for one value field, and its form where the reader knows it."""
    faults = Reasons()
    if record_fault:
        faults.add("form_invalid")
    # read_side_contract.md:305-306 "a value field, form or section `specimen` that breaks its shape"
    if "specimen" in section:
        check_specimen(section["specimen"], faults)
    if not isinstance(field_value, dict):
        # read_side_contract.md:391 "a field that is not an object"
        faults.add("form_invalid")
        return faults, None
    row = FIELDS[field_name]
    form = field_value.get("form")
    known_form = form if isinstance(form, str) and form in FORMS else None
    if slipped(field_value, named_at_a_field(known_form)):
        faults.add("form_invalid")
    if "form" not in field_value:
        faults.add("form_invalid")
    else:
        known_token(form, "form", FORMS, faults)
    if known_form is not None:
        if known_form not in row.forms:
            # read_side_contract.md:305 "Refuse a form the field's row does not allow (`form_not_registered`)"
            # read_side_contract.md:313-315 "a form it does not allow is refused, `form_not_registered`, and
            # its member, which the read neither uses nor returns, is not checked"
            faults.add("form_not_registered")
        else:
            check_form_member(field_value, known_form, row, faults)
        # read_side_contract.md:344-345 "A parameter set read without the family evaluation suite is refused
        # here"
        if known_form == "parameter_set" and "family_evaluation" not in claims:
            faults.add("family_suite_absent")
    # read_side_contract.md:315 "`unit`, only as a string or a status object"
    if "unit" not in field_value:
        faults.add("form_invalid")
    else:
        check_unit(field_value["unit"], faults)
    check_conditions(field_value, faults)
    # record_format.md:260 "`conditions` holds no registered condition: one there is a shape error", of the
    # field `biocompatibility.evidence`, whatever its form (maintainer, 2026-10-19: a table there whose
    # `conditions` hold its axis gives `form_invalid` beside `form_not_registered`)
    conditions = field_value.get("conditions")
    if (
        "evidence" in row.forms
        and isinstance(conditions, dict)
        and any(name in CONDITIONS for name in conditions)
    ):
        faults.add("form_invalid")
    if "specimen" in field_value:
        check_specimen(field_value["specimen"], faults)
    # record_format.md:333 "| `statistics` | yes, except for `evidence` |"
    if known_form != "evidence":
        if "statistics" not in field_value:
            faults.add("form_invalid")
        else:
            # provenance.md:25 "`withheld`; on reference data, `not_applicable`"
            allowed = {"withheld", "not_applicable"} if known_form == "reference_data" else {"withheld"}
            check_block(field_value["statistics"], faults, allowed=frozenset(allowed))
    check_label(field_value, row, faults)
    if "provenance" not in field_value:
        faults.add("form_invalid")
    else:
        check_provenance(field_value["provenance"], faults)
    return faults, known_form


def named_at_a_field(form: str | None) -> tuple[str, ...]:
    """The members named at a value field's place: record_format.md:330 "| the form's member | yes | `value`
    for a constant; otherwise the member named like the form", the field's own form's member alone; beside a
    form the reader does not know, every form's member, which any of them might be (fail closed)."""
    if form is None:
        return FIELD_PLACE_NAMES
    others = set(FORM_MEMBERS.values()) - {FORM_MEMBERS[form]}
    return tuple(name for name in FIELD_PLACE_NAMES if name not in others)


def check_form_member(field_value: JsonObject, form: str, row: FieldRow, faults: Reasons) -> None:
    member = FORM_MEMBERS[form]
    if member not in field_value:
        faults.add("form_invalid")
        return
    value = field_value[member]
    if form == "table":
        check_table(value, field_value.get("conditions"), faults)
    elif form == "constant":
        # record_format.md:391 "**Constant.** `"value": <number>`"
        stated = status_object(value, faults, allowed=frozenset({"withheld"}), scalar=True)
        if stated is not None:
            withheld_value(stated, faults)
        elif not number(value):
            faults.add("form_invalid")
    elif form == "interval":
        check_interval(value, faults)
    elif form == "composition":
        check_composition(value, row, faults)
    elif form == "evidence":
        check_evidence(value, faults)


def check_table(value: JsonValue, conditions: JsonValue, faults: Reasons) -> None:
    """record_format.md section 6, table items 1, 2, 4 and 5: read_side_contract.md:335-336 "a table's `axis`,
    `axis_unit` (as a string or a status object), `x`, `y`, `scheme`, `edges` and `source_range`, and its axis
    condition"."""
    # provenance.md:24 "a form's member (`value` for a constant, otherwise the member named like the form)":
    # `withheld`. `points` is no member the table's shape defines: beside `status`, provenance.md:48-49
    # "Elsewhere a member beside `status` and `reason` that S does not define is ignored"; a member one slip
    # from it is refused, as it is named at a table's place.
    stated = status_object(
        value, faults, allowed=frozenset({"withheld"}), shape=TABLE_MEMBERS, named=TABLE_RESERVED
    )
    if stated is not None:
        withheld_value(stated, faults)
        return
    if not isinstance(value, dict):
        faults.add("form_invalid")
        return
    if slipped(value, TABLE_NAMES) or any(name not in value for name in TABLE_REQUIRED):
        faults.add("form_invalid")
    if "points" in value:
        # record_format.md:434-436 "A 0.1.0 reader refuses a table that holds `points`, whatever it holds
        # (`null` and `[]` included), with the reason `points_unsupported`"
        faults.add("points_unsupported")
        # record_format.md:436-437 "`null` there also gives `form_invalid` (section 1 item 5)"
        if value["points"] is None:
            faults.add("form_invalid")
    axis = value.get("axis")
    if "axis" in value and not isinstance(axis, str):
        # record_format.md:414-415 "An `axis` that is not a string breaks item 1."
        faults.add("form_invalid")
    elif isinstance(axis, str) and axis not in AXES:
        # record_format.md:411-413 "An `axis` that is a string naming no numeric condition the reader knows,
        # a token condition's name included, is a token the reader does not know for that member"
        faults.add("unknown_token")
    elif isinstance(axis, str) and isinstance(conditions, dict):
        # record_format.md:401-402 "the field's `conditions` holds that condition as `{"status":
        # "not_applicable"}`"
        held = conditions.get(axis)
        if not (isinstance(held, dict) and held.get("status") == "not_applicable"):
            faults.add("form_invalid")
    if "axis_unit" in value:
        # record_format.md:402 "`axis_unit` is a string or a status object"
        check_unit(value["axis_unit"], faults)
    if "scheme" in value:
        # record_format.md:409-411 "A `scheme` that is a string other than these two is a token the reader
        # does not know"
        known_token(value["scheme"], "scheme", TABLE_SCHEMES, faults)
    x, y, edges = (numbers_of(value.get(name)) for name in ("x", "y", "edges"))
    for name, found in (("x", x), ("y", y), ("edges", edges)):
        if name in value and found is None:
            faults.add("form_invalid")
    if table_breaks_item_1(x, y, edges):
        faults.add("form_invalid")
    # record_format.md:408 "A `loglog` table holds only positive `x` and `y`."
    if value.get("scheme") == "loglog" and any(number <= 0 for number in (*(x or []), *(y or []))):
        faults.add("form_invalid")
    if "source_range" in value and not source_range_holds(value["source_range"], x, edges):
        faults.add("form_invalid")


def numbers_of(value: JsonValue) -> list[float] | None:
    if isinstance(value, list) and all(number(item) for item in value):
        return [float(item) for item in value if number(item)]
    return None


def table_breaks_item_1(x: list[float] | None, y: list[float] | None, edges: list[float] | None) -> bool:
    """record_format.md:403-404 "`x` holds at least two distinct values and is non-decreasing, and `y` holds
    one number for each entry of `x`"; record_format.md:405 "with no number twice; each edge lies strictly
    between `x[0]` and `x[-1]`"; record_format.md:406 "appears in `x` exactly twice, consecutively"; and
    record_format.md:407 "no other x value repeats. Numbers are compared by value, so `-0` equals `0`"."""
    if x is None:
        return False
    runs: list[tuple[float, int]] = []  # each run of equal consecutive values of `x`, and its length
    for value in x:
        if runs and runs[-1][0] == value:
            runs[-1] = (value, runs[-1][1] + 1)
        else:
            runs.append((value, 1))
    if len(runs) < 2 or any(later < earlier for (earlier, _), (later, _) in itertools.pairwise(runs)):
        return True
    if y is not None and len(y) != len(x):
        return True
    if edges is None:
        return False
    # A set holds a number once by value: `-0` and `0` are one item.
    if len(set(edges)) < len(edges):
        return True
    if not all(x[0] < edge < x[-1] for edge in edges):
        return True
    # In an `x` that never decreases, a value's entries are one run: twice consecutively is a run of two.
    lengths = dict(runs)
    if any(lengths.get(edge) != 2 for edge in edges):
        return True
    edged = set(edges)
    return any(length > 1 and value not in edged for value, length in runs)


def source_range_holds(source_range: JsonValue, x: list[float] | None, edges: list[float] | None) -> bool:
    """record_format.md:427-429 "two numbers in the table's `axis_unit`, the first not greater than the
    second, sharing with `[x[0], x[-1]]` at least one value that is no edge"."""
    if not ordered_pair(source_range):
        return False
    if x is None or edges is None or not x:
        # `x` or `edges` broken, or `x` empty (record_format.md:403 "`x` holds at least two distinct values"),
        # refuses the field already; there is no range to share with
        return True
    bounds = numbers_of(source_range)
    assert bounds is not None
    low, high = max(bounds[0], x[0]), min(bounds[1], x[-1])
    # An overlap of more than one value holds values that are no edge, the edges being finitely many.
    return low < high or (low == high and all(low != edge for edge in edges))


def withheld_value(stated: StatusObject, faults: Reasons) -> None:
    # provenance.md:339 "A reader refuses a withheld value, with the reason `withheld`."
    if stated.token == "withheld":
        faults.add("withheld")


def check_unit(unit: JsonValue, faults: Reasons) -> None:
    # record_format.md:230-232 "step 8 checks only that it is a string or a status object" ... "and one that
    # is neither is a shape error (`form_invalid`)"
    if isinstance(unit, str):
        return
    if status_object(unit, faults, allowed=ANY_STATUS, scalar=True, unit=True) is None:
        faults.add("form_invalid")


def check_conditions(field_value: JsonObject, faults: Reasons) -> None:
    # record_format.md:331 "| `conditions` | yes |"
    conditions = field_value.get("conditions")
    if not isinstance(conditions, dict):
        faults.add("form_invalid")
        return
    # read_side_contract.md:316-317 "each condition and specimen fact whose name the reader knows"
    for name, condition in conditions.items():
        if name in CONDITIONS:
            check_condition(name, condition, faults)


def check_condition(name: str, condition: JsonValue, faults: Reasons) -> None:
    row = CONDITIONS[name]
    # provenance.md:246 "either may instead hold a status object"
    if status_object(condition, faults, allowed=ANY_STATUS, shape=CONDITION_NAMES) is not None:
        return
    if not isinstance(condition, dict):
        faults.add("form_invalid")
        return
    if slipped(condition, CONDITION_NAMES):
        faults.add("form_invalid")
    if holds_another_kind(condition, ("token",) if row.shape == "numeric" else NUMERIC_CONDITION_ONLY):
        faults.add("form_invalid")
    if row.shape == "numeric":
        # provenance.md:242 "A numeric condition holds"
        check_value_or_range(condition, faults)
        if "unit" not in condition:
            faults.add("form_invalid")
        else:
            check_unit(condition["unit"], faults)
        if "plus_minus" in condition:
            check_plus_minus(condition["plus_minus"], faults)
        if "set_or_measured" in condition:
            known_token(condition["set_or_measured"], "set_or_measured", SET_OR_MEASURED, faults)
    else:
        # provenance.md:245 "a token condition holds"
        if "token" not in condition:
            faults.add("form_invalid")
        else:
            known_token(condition["token"], "token", row.tokens, faults)
        # provenance.md:245-246 "so a `unit` on one gives `unit_mismatch` at step 9"
        if "unit" in condition:
            check_unit(condition["unit"], faults)
    check_basis(condition, None, faults)


def holds_another_kind(value: JsonObject, members: tuple[str, ...]) -> bool:
    # In a record (the maintainer's ruling, 2026-10-19), as in an implied value (`implied_value`):
    # provenance.md:246-248 "A numeric condition holding `token`, or a token condition holding `value`,
    # `range`, `plus_minus` or `set_or_measured`, breaks its shape (`form_invalid`)"
    return any(member in value for member in members)


def check_value_or_range(value: JsonObject, faults: Reasons) -> None:
    # provenance.md:242 "`{"range": [lo, hi], "unit"}` with `lo <= hi`"; read_side_contract.md:326 "a
    # condition's or fact's `range`"
    if ("value" in value) == ("range" in value):
        faults.add("form_invalid")
    if "value" in value and not number(value["value"]):
        faults.add("form_invalid")
    if "range" in value and not ordered_pair(value["range"]):
        faults.add("form_invalid")


def check_basis(value: JsonObject, fixed: str | None, faults: Reasons) -> None:
    # provenance.md:210-211 "each shape except a status object carries a `basis`: `stated`, or `inferred` with
    # an `inferred_from` text"
    if "basis" not in value:
        faults.add("form_invalid")
        return
    known_token(value["basis"], "basis", CONDITION_BASES if fixed is None else (fixed,), faults)
    if fixed is None:
        if value["basis"] == "inferred" and "inferred_from" not in value:
            faults.add("form_invalid")
        if "inferred_from" in value and not isinstance(value["inferred_from"], str):
            faults.add("form_invalid")


def check_plus_minus(entries: JsonValue, faults: Reasons) -> None:
    # provenance.md:263 "numeric condition: a non-empty list of"
    if not isinstance(entries, list) or not entries:
        faults.add("form_invalid")
        return
    kinds: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            faults.add("form_invalid")
            continue
        if slipped(entry, PLUS_MINUS_NAMES) or any(name not in entry for name in PLUS_MINUS_NAMES):
            faults.add("form_invalid")
        if "stated_as" in entry:
            kind = entry["stated_as"]
            unstated = status_object(kind, faults, allowed=frozenset({"unstated"}), scalar=True)
            if unstated is not None:
                # provenance.md:265-266 "or `{"status": "unstated"}` (a ± whose kind the source does not
                # state)", so another token is no kind of the list's rules, refused by its own.
                if unstated.token == "unstated":
                    kinds.append("unstated")
            else:
                known_token(kind, "stated_as", STATED_AS, faults)
                if isinstance(kind, str):
                    kinds.append(kind)
        # provenance.md:266 "`value` is a number not below zero"
        if "value" in entry and not not_negative(entry["value"]):
            faults.add("form_invalid")
        if "unit" in entry:
            check_unit(entry["unit"], faults)
    # provenance.md:268-269 "The list holds at most one entry of each kind, and an entry of unstated kind
    # stands alone."
    if len(kinds) != len(set(kinds)) or ("unstated" in kinds and len(kinds) > 1):
        faults.add("form_invalid")


def fact_names(row: FactRow) -> tuple[str, ...]:
    return (*row.members, "basis") if row.basis is not None else (*row.members, "basis", "inferred_from")


def check_specimen(specimen: JsonValue, faults: Reasons) -> None:
    if not isinstance(specimen, dict):
        faults.add("form_invalid")
        return
    for name, fact in specimen.items():
        if name in FACTS:
            check_fact(name, fact, faults)
        elif any(one_slip(name, known) for known in FACTS):
            # record_format.md:591 "in a section, its `specimen`"
            faults.add("form_invalid")


def check_fact(name: str, fact: JsonValue, faults: Reasons) -> None:
    row = FACTS[name]
    names = fact_names(row)
    # provenance.md:303 "Every fact takes its row's shape or a status object"
    if status_object(fact, faults, allowed=ANY_STATUS, shape=names) is not None:
        return
    if not isinstance(fact, dict):
        faults.add("form_invalid")
        return
    if slipped(fact, names):
        faults.add("form_invalid")
    for member, kind in row.members.items():
        if member not in fact:
            if member in row.required:
                faults.add("form_invalid")
            continue
        value = fact[member]
        if kind == "token":
            known_token(value, "token", row.tokens, faults)
        elif kind == "unit":
            check_unit(value, faults)
        elif kind == "range":
            if not ordered_pair(value):
                faults.add("form_invalid")
        elif not {"text": isinstance(value, str), "number": number(value), "integer": whole(value)}[kind]:
            faults.add("form_invalid")
    if name == "donor_age" and ("value" in fact) == ("range" in fact):
        faults.add("form_invalid")
    if name == "disease_and_treatment_state" and ("text" in fact) != (fact.get("token") in DISEASE_NAMED_BY):
        faults.add("form_invalid")
    if name == "preservation" and fact.get("token") == "other" and "text" not in fact:
        faults.add("form_invalid")
    check_basis(fact, row.basis, faults)


def check_block(block: JsonValue, faults: Reasons, *, allowed: frozenset[str]) -> None:
    """A statistics block (uncertainty.md section 1), wherever it sits."""
    if status_object(block, faults, allowed=allowed, shape=BLOCK_NAMES) is not None:
        return
    if not isinstance(block, dict):
        faults.add("form_invalid")
        return
    if slipped(block, BLOCK_NAMES):
        faults.add("form_invalid")
    # uncertainty.md:57 "Every member is present, holding a number, a token, an object of its row's shape, or
    # a status object"
    for member in BLOCK_MEMBERS:
        if member not in block:
            faults.add("form_invalid")
        else:
            check_block_member(member, block[member], faults)
    represents = block.get("represents")
    for member, needs in CONDITIONAL_BLOCK_MEMBERS.items():
        # uncertainty.md:59-60 "One present elsewhere, or missing there, breaks the block's shape."
        if (member in block) != (represents == needs):
            faults.add("form_invalid")
        if member in block:
            check_block_member(member, block[member], faults)


def check_block_member(member: str, value: JsonValue, faults: Reasons) -> None:
    if member in BLOCK_TOKEN_MEMBERS:
        tokens, statuses = BLOCK_TOKEN_MEMBERS[member]
        if status_object(value, faults, allowed=statuses, scalar=True) is None:
            known_token(value, member, tokens, faults)
    elif member == "dispersion":
        known_token(value, "dispersion", DISPERSIONS, faults)
    elif member in ("relative_uncertainty", "expanded_uncertainty"):
        check_uncertainty(value, faults)
    elif member == "population_level":
        check_population_level(value, faults)
    elif status_object(value, faults, allowed=ANY_STATUS, scalar=True) is None:
        # read_side_contract.md:324 "counts (`n_specimens`, `n_donors`, `n_sources`" and "are whole and not
        # negative"; read_side_contract.md:327-328 "a statistics block's `sd`" and "an uncertainty's `value`
        # are not below zero"
        if member in BLOCK_COUNTS:
            acceptable = whole(value) and value >= 0
        elif member == "sd":
            acceptable = not_negative(value)
        else:
            acceptable = number(value)
        if not acceptable:
            faults.add("form_invalid")


def check_population_level(value: JsonValue, faults: Reasons) -> None:
    # uncertainty.md:37 "present exactly where `represents` is `population`"
    if (
        status_object(value, faults, allowed=frozenset({"unstated"}), shape=POPULATION_LEVEL_NAMES)
        is not None
    ):
        return
    if not isinstance(value, dict):
        faults.add("form_invalid")
        return
    if slipped(value, POPULATION_LEVEL_NAMES) or any(name not in value for name in POPULATION_LEVEL_NAMES):
        faults.add("form_invalid")
    # read_side_contract.md:138-139 "Each step makes all its checks before the read stops": a member present
    # is checked whatever else the object misses.
    if "level" in value:
        known_token(value["level"], "level", LEVELS, faults)
    # provenance.md:29 "in its `within`, `none`"
    if (
        "within" in value
        and status_object(value["within"], faults, allowed=frozenset({"none"}), scalar=True) is None
    ):
        known_token(value["within"], "within", LEVELS, faults)


def check_uncertainty(value: JsonValue, faults: Reasons) -> None:
    """A relative or expanded uncertainty: uncertainty.md:44 "In a relative or expanded uncertainty"."""
    if status_object(value, faults, allowed=ANY_STATUS, shape=UNCERTAINTY_NAMES) is not None:
        return
    if not isinstance(value, dict):
        faults.add("form_invalid")
        return
    if slipped(value, UNCERTAINTY_NAMES) or any(name not in value for name in UNCERTAINTY_MEMBERS):
        faults.add("form_invalid")
    # read_side_contract.md:327 "a `plus_minus` entry's `value`, a statistics block's `sd` and an
    # uncertainty's `value` are not below zero"
    if "value" in value and not not_negative(value["value"]):
        faults.add("form_invalid")
    coverage_is_a_number = False
    for member in ("coverage_factor", "coverage_probability"):
        if member in value and status_object(value[member], faults, allowed=ANY_STATUS, scalar=True) is None:
            given = value[member]
            # read_side_contract.md:328-329 "an uncertainty's `coverage_factor` and `dof` are above zero" and
            # "its `coverage_probability` is above zero and at most one"
            if not number(given) or given <= 0 or (member == "coverage_probability" and given > 1):
                faults.add("form_invalid")
            coverage_is_a_number = coverage_is_a_number or number(given)
    # read_side_contract.md:332-333 "an uncertainty has a numeric coverage factor or coverage probability"
    if not coverage_is_a_number:
        faults.add("form_invalid")
    distribution = value.get("distribution")
    if (
        "distribution" in value
        and status_object(distribution, faults, allowed=frozenset({"unstated"}), scalar=True) is None
    ):
        known_token(distribution, "distribution", UNCERTAINTY_DISTRIBUTIONS, faults)
    if "dof" in value:
        dof = value["dof"]
        # A status object there has its token checked under any distribution (read_side_contract.md:138-139
        # "Each step makes all its checks").
        held = status_object(dof, faults, allowed=ANY_STATUS, scalar=True)
        # read_side_contract.md:333-334 "its `dof` is a number exactly where its `distribution` is
        # `student_t`"
        if distribution == "student_t":
            if not (number(dof) and dof > 0):
                faults.add("form_invalid")
        elif held is None:
            faults.add("form_invalid")
    if "basis" in value:
        known_token(value["basis"], "basis", UNCERTAINTY_BASES, faults)
    represents = value.get("represents")
    if (
        "represents" in value
        and status_object(represents, faults, allowed=frozenset({"unstated"}), scalar=True) is None
    ):
        known_token(represents, "represents", UNCERTAINTY_REPRESENTS, faults)
    # uncertainty.md:41 "with `precision_conditions` where its `represents` is `measurement`"
    if ("precision_conditions" in value) != (represents == "measurement"):
        faults.add("form_invalid")
    if "precision_conditions" in value:
        given = value["precision_conditions"]
        if status_object(given, faults, allowed=frozenset({"unstated"}), scalar=True) is None:
            known_token(given, "precision_conditions", PRECISION_CONDITIONS, faults)


def check_label(field_value: JsonObject, row: FieldRow, faults: Reasons) -> None:
    # record_format.md:194-196 "A label the reader does not know refuses the field as a token it does not know
    # (`unknown_token`, section 10), and a label it knows that the row does not name for the field and its
    # form refuses it as `form_invalid`."
    if "label" not in field_value:
        return
    label = field_value["label"]
    if not isinstance(label, str):
        faults.add("form_invalid")
    elif label not in FIELD_LABELS:
        faults.add("unknown_token")
    elif not label_named(field_value, row, label):
        faults.add("form_invalid")


def label_named(field_value: JsonObject, row: FieldRow, label: str) -> bool:
    # record_format.md:165 "on a constant, or on a table whose axis is not `shear_rate`"
    form, table = field_value.get("form"), field_value.get("table")
    on_its_form = form == "constant" or (
        form == "table" and isinstance(table, dict) and table.get("axis") != row.label_not_on_axis
    )
    return label == row.label and on_its_form


def check_provenance(provenance: JsonValue, faults: Reasons) -> None:
    # read_side_contract.md:318-319 "and in `provenance` its `origin`, its `source` (present for origin
    # `measured_by_source`, and its `key` wherever present) and its `derivation` for origin `derived`"
    if not isinstance(provenance, dict):
        faults.add("form_invalid")
        return
    if slipped(provenance, PROVENANCE_NAMES):
        faults.add("form_invalid")
    origin = provenance.get("origin")
    if "origin" not in provenance:
        faults.add("form_invalid")
    else:
        known_token(origin, "origin", ORIGINS, faults)
    if origin == "measured_by_source" and "source" not in provenance:
        faults.add("form_invalid")
    if "source" in provenance:
        source = provenance["source"]
        # provenance.md:117 "wherever present, an object whose `key` is a string"
        if not (isinstance(source, dict) and isinstance(source.get("key"), str)):
            faults.add("form_invalid")
        elif slipped(source, SOURCE_NAMES):
            faults.add("form_invalid")
    # provenance.md:119 "`derivation` for origin `derived` (section 5)"
    if origin == "derived":
        if "derivation" not in provenance:
            faults.add("form_invalid")
        else:
            check_derivation(provenance["derivation"], faults)


def check_derivation(derivation: JsonValue, faults: Reasons) -> None:
    """provenance.md:196 "A derived value's `derivation` holds `method`" and provenance.md:201-202 "a list of
    `{"input": <index into inputs>, "specimen": {...}}`"."""
    if not isinstance(derivation, dict):
        faults.add("form_invalid")
        return
    if slipped(derivation, DERIVATION_NAMES):
        faults.add("form_invalid")
    if not isinstance(derivation.get("method"), str):
        faults.add("form_invalid")
    inputs = derivation.get("inputs")
    if not (isinstance(inputs, list) and inputs):
        faults.add("form_invalid")
    inputs = inputs if isinstance(inputs, list) else []
    for given in inputs:
        if not isinstance(given, dict):
            faults.add("form_invalid")
            continue
        record = given.get("record")
        if (
            slipped(given, INPUT_NAMES)
            or reference_of(record) is None
            or not isinstance(given.get("field"), str)
        ):
            faults.add("form_invalid")
        if isinstance(record, dict) and slipped(record, REFERENCE_NAMES):
            faults.add("form_invalid")
    assumptions = derivation.get("assumptions")
    if not (isinstance(assumptions, list) and all(isinstance(text, str) for text in assumptions)):
        faults.add("form_invalid")
    # provenance.md:201 "A derived value carries the specimen facts of each input in
    # `derivation.input_specimens`": required, as `mixed_conditions` is not (provenance.md:204 "where present,
    # the member is a boolean").
    check_input_specimens(derivation.get("input_specimens"), len(inputs), faults)
    if "mixed_conditions" in derivation and not isinstance(derivation["mixed_conditions"], bool):
        faults.add("form_invalid")


def check_input_specimens(entries: JsonValue, inputs: int, faults: Reasons) -> None:
    # provenance.md:202-203 "each `input` a whole number below the length of `inputs` and each `specimen` a
    # map of specimen facts"
    if not isinstance(entries, list):
        faults.add("form_invalid")
        return
    for entry in entries:
        if not isinstance(entry, dict):
            faults.add("form_invalid")
            continue
        index = entry.get("input")
        if slipped(entry, INPUT_SPECIMEN_NAMES) or not (whole(index) and 0 <= index < inputs):
            faults.add("form_invalid")
        check_specimen(entry.get("specimen"), faults)


def check_interval(value: JsonValue, faults: Reasons) -> None:
    """record_format.md:466 "`lower` and `upper` are numbers, at most one holds `{"status": "none"}`"."""
    stated = status_object(value, faults, allowed=frozenset({"withheld"}), shape=INTERVAL_NAMES)
    if stated is not None:
        withheld_value(stated, faults)
        return
    if not isinstance(value, dict):
        faults.add("form_invalid")
        return
    if slipped(value, INTERVAL_NAMES):
        faults.add("form_invalid")
    nones = 0
    for side in ("lower", "upper"):
        if side not in value:
            faults.add("form_invalid")
            continue
        bound = status_object(value[side], faults, allowed=frozenset({"none"}), scalar=True)
        if bound is not None:
            nones += bound.token == "none"
        elif not number(value[side]):
            faults.add("form_invalid")
    lower, upper = value.get("lower"), value.get("upper")
    # record_format.md:466-467 "at most one holds `{"status": "none"}`" and "`lower <= upper` where both are
    # numbers"
    if nones == 2 or (number(lower) and number(upper) and lower > upper):
        faults.add("form_invalid")
    if "basis" not in value:
        faults.add("form_invalid")
    else:
        known_token(value["basis"], "basis", INTERVAL_BASES, faults)


def check_composition(value: JsonValue, row: FieldRow, faults: Reasons) -> None:
    """record_format.md:482 "`basis` is `mass_fraction`, `volume_fraction` or `mole_fraction`" and
    record_format.md:494-496 "`components` holds at least one component; no component appears twice"."""
    stated = status_object(value, faults, allowed=frozenset({"withheld"}), shape=COMPOSITION_NAMES)
    if stated is not None:
        withheld_value(stated, faults)
        return
    if not isinstance(value, dict):
        faults.add("form_invalid")
        return
    basis = value.get("basis")
    # record_format.md:214-215 "and so is a composition whose basis the row does not allow"
    if isinstance(basis, str) and basis in COMPOSITION_BASES and basis not in row.bases:
        # Open point: form_not_allowed_by_its_row.
        faults.add("form_not_registered")
        return
    if slipped(value, COMPOSITION_NAMES):
        faults.add("form_invalid")
    if "basis" not in value:
        faults.add("form_invalid")
    else:
        known_token(basis, "basis", COMPOSITION_BASES, faults)
    if "sum_rule" not in value:
        faults.add("form_invalid")
    else:
        known_token(value["sum_rule"], "sum_rule", SUM_RULES, faults)
    if "stated_sum" in value and not number(value["stated_sum"]):
        faults.add("form_invalid")
    components = value.get("components")
    # record_format.md:494-495 "`components` holds at least one component; no component appears twice; and
    # each `fraction` is a number from 0 to 1"
    if not (isinstance(components, list) and components):
        faults.add("form_invalid")
        return
    seen: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            faults.add("form_invalid")
            continue
        if slipped(component, COMPONENT_NAMES):
            faults.add("form_invalid")
        name, fraction = component.get("component"), component.get("fraction")
        if "component" not in component:
            faults.add("form_invalid")
        else:
            # record_format.md:483-484 "Another symbol, or a component of another kind, is a token the reader
            # does not know (`unknown_token`)."
            known_token(name, "component", COMPONENTS, faults)
            if isinstance(name, str):
                if name in seen:
                    faults.add("form_invalid")
                seen.add(name)
        if not (number(fraction) and 0 <= fraction <= 1):
            faults.add("form_invalid")
        # record_format.md:490-491 "a statistics block (`uncertainty.md` section 1), which a read checks as it
        # checks the field's"
        if "statistics" in component:
            check_block(component["statistics"], faults, allowed=frozenset({"withheld"}))


def check_evidence(value: JsonValue, faults: Reasons) -> None:
    """record_format.md:236 "`biocompatibility.evidence` is a value field of form `evidence`"."""
    # record_format.md:245-246 "The list holds at least one entry; an empty list is a shape error"
    if not (isinstance(value, list) and value):
        faults.add("form_invalid")
        return
    withheld_entries: list[bool] = []
    for entry in value:
        if not isinstance(entry, dict):
            faults.add("form_invalid")
            # An entry that is not an object withholds nothing, so not every entry is withheld.
            withheld_entries.append(False)
            continue
        if slipped(entry, EVIDENCE_ENTRY_NAMES):
            faults.add("form_invalid")
        withheld_members: list[bool] = []
        for member in EVIDENCE_ENTRY_NAMES[:-1]:
            if member not in entry:
                # record_format.md:246 "Every member of an entry is present"
                faults.add("form_invalid")
                continue
            given = entry[member]
            standard = member == "standard"
            stated = status_object(
                given,
                faults,
                allowed=ANY_STATUS,
                shape=STANDARD_NAMES if standard else (),
                scalar=not standard,
            )
            withheld_members.append(stated is not None and stated.token == "withheld")
            if stated is not None:
                continue
            if standard:
                check_standard(given, faults)
            elif not isinstance(given, str):
                faults.add("form_invalid")
        if "provenance" not in entry:
            faults.add("form_invalid")
        else:
            check_entry_provenance(entry["provenance"], faults)
        withheld_entries.append(withheld_whole(withheld_members, faults))
    # read_side_contract.md:345-346 "An evidence list whose every entry is withheld gives `withheld`; one with
    # some entries withheld, `unknown` (`entries_withheld`)."
    if withheld_entries and all(withheld_entries):
        faults.add("withheld")
    elif any(withheld_entries):
        faults.add("entries_withheld")


def check_entry_provenance(provenance: JsonValue, faults: Reasons) -> None:
    # record_format.md:255 "Step 8 checks an entry's `provenance` as a field's (`provenance.md` section 2 item
    # 6)"
    check_provenance(provenance, faults)


def withheld_whole(withheld_members: list[bool], faults: Reasons) -> bool:
    """Whether an entry, of which `withheld_members` says which members but `provenance` hold `withheld`, is
    withheld: record_format.md:249-250 "An entry is withheld whole, its provenance kept, or not at all"."""
    whole_entry = len(withheld_members) == len(EVIDENCE_ENTRY_NAMES) - 1 and all(withheld_members)
    if any(withheld_members) and not whole_entry:
        faults.add("form_invalid")
    return whole_entry


def check_standard(standard: JsonValue, faults: Reasons) -> None:
    # record_format.md:237-238 "Each entry holds `endpoint`, `standard`"
    if not isinstance(standard, dict) or any(name not in standard for name in STANDARD_NAMES):
        faults.add("form_invalid")
        return
    if slipped(standard, STANDARD_NAMES) or not isinstance(standard["designation"], str):
        faults.add("form_invalid")
    # read_side_contract.md:324-325 "an evidence entry's `standard.year` is whole"
    if not whole(standard["year"]):
        faults.add("form_invalid")


# Step 9: units, read_side_contract.md:348 "9. **Units.** Refuse a field unit, `axis_unit` or condition unit
# other than the registered one"


def same_unit(stored: JsonValue, registered: str | StatusUnit) -> bool:
    # record_format.md:226-229 "Units are compared as strings, after JSON escapes are decoded, code point for
    # code point" ... "A unit registered as a status object equals one holding the same `status` token"
    if isinstance(registered, StatusUnit):
        return isinstance(stored, dict) and stored.get("status") == registered.status
    return isinstance(stored, str) and stored == registered


def check_units(field_value: JsonObject, section: JsonObject, field_name: str) -> Reasons:
    reasons = Reasons()
    if not same_unit(field_value["unit"], FIELDS[field_name].unit):
        reasons.add("unit_mismatch")
    table = field_value.get(FORM_MEMBERS["table"]) if field_value["form"] == "table" else None
    if isinstance(table, dict) and "status" not in table:
        # read_side_contract.md:348 "Refuse a field unit, `axis_unit` or condition unit other than the
        # registered one"; read_side_contract.md:144-145 "`unit_mismatch` where they concern one condition (an
        # unregistered condition name included) or an axis"
        axis = str(table["axis"])
        unit = CONDITIONS[axis].unit
        assert unit is not None
        if not same_unit(table["axis_unit"], unit):
            reasons.add("unit_mismatch", axis)
    conditions = field_value["conditions"]
    assert isinstance(conditions, dict)
    for name, condition in conditions.items():
        row = CONDITIONS.get(name)
        if row is None or not isinstance(condition, dict) or "status" in condition:
            continue
        if row.shape == "token":
            # read_side_contract.md:349-350 "a `unit` on a token condition, which registers none"
            if "unit" in condition:
                reasons.add("unit_mismatch", name)
            continue
        assert row.unit is not None
        # read_side_contract.md:349 "a condition's `plus_minus` units included"
        units = [condition["unit"]]
        entries = condition.get("plus_minus", [])
        if isinstance(entries, list):
            units.extend(entry["unit"] for entry in entries if isinstance(entry, dict))
        if not all(same_unit(unit, row.unit) for unit in units):
            reasons.add("unit_mismatch", name)
    # read_side_contract.md:353-355 "A specimen fact's `unit`, wherever step 8 checks the fact, is compared in
    # the same way with the unit its row fixes"
    for specimen in checked_specimens(field_value, section):
        for name, fact in specimen.items():
            fixed = FACTS[name].unit if name in FACTS else None
            if fixed is None or not isinstance(fact, dict) or "status" in fact:
                continue
            if not same_unit(fact.get("unit"), fixed):
                reasons.add("unit_mismatch")
    return reasons


def checked_specimens(field_value: JsonObject, section: JsonObject) -> list[JsonObject]:
    """Every specimen step 8 checks for this field: the section's, the field's and a derivation's inputs'."""
    found = [
        specimen
        for specimen in (section.get("specimen"), field_value.get("specimen"))
        if isinstance(specimen, dict)
    ]
    provenance = field_value["provenance"]
    if isinstance(provenance, dict) and provenance.get("origin") == "derived":
        derivation = provenance.get("derivation")
        entries = derivation.get("input_specimens") if isinstance(derivation, dict) else None
        for entry in entries if isinstance(entries, list) else []:
            specimen = entry.get("specimen") if isinstance(entry, dict) else None
            if isinstance(specimen, dict):
                found.append(specimen)
    return found


# Step 10: conditions (read_side_contract.md section 5)


def merged_specimen(section: JsonObject, field_value: JsonObject) -> JsonObject:
    # record_format.md:145-146 "A field's own `specimen` overrides the section's, fact by fact."
    merged: JsonObject = {}
    for specimen in (section.get("specimen"), field_value.get("specimen")):
        if isinstance(specimen, dict):
            merged.update(specimen)
    return merged


def states(specimen: JsonObject, implied: ImpliedCondition) -> bool:
    # read_side_contract.md:357-358 "whose fact and token the field's specimen states"
    fact = specimen.get(implied.fact)
    return isinstance(fact, dict) and "status" not in fact and fact.get("token") == implied.token


def same_supplied_value(one: JsonObject, other: JsonObject) -> bool:
    """read_side_contract.md:110-112 "Two values differ unless they are of one shape, a value, a range or a
    token, and hold the same token or the same numbers bit for bit" ... "so `0` and `-0` differ, as a value
    and the range `[v, v]` do"."""
    return one.keys() == other.keys() and all(same_bits(one[member], other[member]) for member in one)


def same_bits(one: JsonValue, other: JsonValue) -> bool:
    if isinstance(one, float) and isinstance(other, float):
        return struct.pack(">d", one) == struct.pack(">d", other)
    if isinstance(one, list) and isinstance(other, list):
        return len(one) == len(other) and all(map(same_bits, one, other))
    return one == other


@dataclass
class ConditionsChecked:
    reasons: Reasons
    entries: list[JsonValue] | None  # None where two implied conditions disagree


def check_against_request(
    field_value: JsonObject, specimen: JsonObject, request: Request, axis: "TableAxis | None" = None
) -> ConditionsChecked:
    reasons = Reasons()
    held = field_value["conditions"]
    assert isinstance(held, dict)
    applying = [implied for implied in request.implied if states(specimen, implied)]
    supplied: dict[str, JsonObject] = {}
    disagreeing: list[str] = []
    for implied in applying:
        for name, value in implied.implies.items():
            if name in supplied and not same_supplied_value(supplied[name], value):
                disagreeing.append(name)
            supplied.setdefault(name, value)
    # read_side_contract.md:108-113 "two implied conditions that both apply to the field" ... "give
    # `request_incomplete` with that `condition`" ... "Step 10 makes this check first, and where it fails it
    # checks no condition"
    if disagreeing:
        for name in disagreeing:
            reasons.add("request_incomplete", name)
        return ConditionsChecked(reasons, None)
    # declarations.md:377-378 "it fills only an unstated one, which is a condition the record holds as"
    applied = {name: value for name, value in supplied.items() if unstated_or_absent(held.get(name))}
    entries: list[JsonValue] = [
        condition_entry(name, held, applied, request, reasons, axis)
        for name in conditions_checked(held, applied, request)
    ]
    return ConditionsChecked(reasons, entries)


def unstated_or_absent(condition: JsonValue) -> bool:
    return condition is None or (isinstance(condition, dict) and condition.get("status") == "unstated")


def conditions_checked(held: JsonObject, applied: Mapping[str, JsonObject], request: Request) -> list[str]:
    # read_side_contract.md:466-469 "The conditions checked are those the record holds; those an implied
    # condition the read applies fills" ... "those the field's row requires" ... "those another condition
    # requires with the token it holds" ... "and those the request's `requirement.conditions` names"
    names = dict.fromkeys((*held, *applied, *FIELDS[request.field].requires))
    for name, row in CONDITIONS.items():
        for other, tokens in row.required_with:
            if token_held(other, held, applied) in tokens:
                names[name] = None
    names.update(dict.fromkeys((*request.tolerances, *request.accepts)))
    return list(names)


def token_held(name: str, held: JsonObject, applied: Mapping[str, JsonObject]) -> JsonValue:
    if name in applied:
        return applied[name].get("token")
    condition = held.get(name)
    return condition.get("token") if isinstance(condition, dict) and "status" not in condition else None


def condition_entry(
    name: str,
    held: JsonObject,
    applied: Mapping[str, JsonObject],
    request: Request,
    reasons: Reasons,
    axis: "TableAxis | None" = None,
) -> JsonObject:
    """One entry of the result's `conditions`, its reason put in `reasons`: read_side_contract.md:173-174 "An
    entry's `record` is the record's entry, or the value an implied condition supplies with basis
    `implied`"."""
    entry: JsonObject = {"name": name}
    if name in request.operating:
        # read_side_contract.md:174-175 "its `operating` is the request's operating condition, omitted where
        # the request gives none"
        entry["operating"] = copied(request.operating[name])

    def give(status: Status, code: str | None = None, record: JsonObject | None = None) -> JsonObject:
        entry["status"] = status
        if record is not None:
            entry["record"] = record
        if code is not None:
            reasons.add(code, name)
        return entry

    # read_side_contract.md:477 "| a name the reader does not know | anything | `unknown`
    # (`condition_unknown_name`)"
    if name not in CONDITIONS:
        return give("unknown", "condition_unknown_name")
    if name in applied:
        # read_side_contract.md:484 "| a value implied by an acceptance (`declarations.md`) | as for a stated
        # value |"
        stated = applied[name]
        record = {**copied_object(stated), "basis": IMPLIED_BASIS}
    elif name not in held:
        # read_side_contract.md:476 "| any other status object, on any condition; or the condition is absent"
        return give("unknown", "condition_unstated")
    else:
        condition = held[name]
        assert isinstance(condition, dict)
        if axis is not None and name == axis.name and condition.get("status") == "not_applicable":
            # read_side_contract.md:475 "| `{"status": "not_applicable"}`, on the form's own axis | anything
            # |" ... "Step 10 gives no reason for it and does not end the read on it"
            return give(axis.status, record=status_returned(condition))
        if "status" in condition:
            return give("unknown", "condition_unstated", status_returned(condition))
        stated, record = condition, condition_returned(condition)
    if name in request.accepts:
        # read_side_contract.md:483 "| a token | an accept list | `met` when the token is in the list"
        if stated.get("token") in request.accepts[name]:
            return give("met", record=record)
        return give("not_met", "condition_not_accepted", record)
    if name not in request.tolerances:
        # read_side_contract.md:478 "| any stated value, range or token | no tolerance and no accept list for
        # it |"
        return give("unknown", "condition_unchecked", record)
    status = within_tolerance(stated, request.operating[name], request.tolerances[name])
    if status == "not_met":
        return give("not_met", "condition_outside", record)
    if status == "unknown":
        return give("unknown", "condition_uncertain", record)
    return give("met", record=record)


def ends(value: JsonObject) -> tuple[Fraction, Fraction]:
    """A stated or operating value as the range `[v, v]`, its ends exact."""
    given = value["value"] if "value" in value else value["range"]
    low, high = given if isinstance(given, list) else (given, given)
    assert number(low)
    assert number(high)
    return Fraction(low), Fraction(high)


def within_tolerance(stated: JsonObject, operating: JsonObject, tolerance: float) -> Status:
    """read_side_contract.md:479 "`met` when `abs(r - v) <= t`, else `not_met` (`condition_outside`)" to
    read_side_contract.md:482 "`met` when `a - t <= lo` and `hi <= b + t`", and a stated plus or minus as
    read_side_contract.md:499-500 "Where `plus_minus` holds a `bound` entry, it decides" says, on the exact
    values of the doubles: read_side_contract.md:488 "Every comparison in this table is made on the exact
    values of the numbers as read"."""
    low, high = ends(stated)
    operating_low, operating_high = ends(operating)
    t = Fraction(tolerance)
    # read_side_contract.md:480 "`met` when `r - t <= lo` and `hi <= r + t`", and its three other rows
    if not (low - t <= operating_low and operating_high <= high + t):
        return "not_met"
    entries = stated.get("plus_minus", [])
    entries = entries if isinstance(entries, list) else []
    bounds = [entry for entry in entries if isinstance(entry, dict) and entry.get("stated_as") == "bound"]
    if bounds:
        # read_side_contract.md:499-504 "Where `plus_minus` holds a `bound` entry, it decides" ... "both ends
        # move inward by u"
        bound = bounds[0]["value"]
        assert number(bound)
        u = Fraction(bound)
        return "met" if low + u - t <= operating_low and operating_high <= high - u + t else "unknown"
    # read_side_contract.md:505-506 "an `sd` entry, or one of unstated kind, with a value above zero makes the
    # entry `unknown`"
    values = [entry.get("value") for entry in entries if isinstance(entry, dict)]
    return "unknown" if any(number(value) and value > 0 for value in values) else "met"


# What a read returns from a record: the members the reader knows, each as stored,
# read_side_contract.md:168-169 "A member the reader does not know is left out"


def copied_object(value: JsonObject) -> JsonObject:
    return {name: copied(member) for name, member in value.items()}


def known_members(value: JsonObject, names: Iterable[str]) -> JsonObject:
    return {name: copied(value[name]) for name in names if name in value}


def unit_returned(unit: JsonValue) -> JsonValue:
    # read_side_contract.md:127 "the field's unit, as stored: a unit held as a status object keeps its
    # `reason`"
    return status_returned(unit) if isinstance(unit, dict) else copied(unit)


def condition_returned(condition: JsonObject) -> JsonObject:
    if "status" in condition:
        return status_returned(condition)
    returned = known_members(condition, CONDITION_NAMES)
    if "unit" in returned:
        returned["unit"] = unit_returned(condition["unit"])
    entries = condition.get("plus_minus")
    if isinstance(entries, list):
        returned["plus_minus"] = [plus_minus_returned(entry) for entry in entries if isinstance(entry, dict)]
    return returned


def plus_minus_returned(entry: JsonObject) -> JsonValue:
    returned = known_members(entry, PLUS_MINUS_NAMES)
    for member in ("stated_as", "unit"):
        if isinstance(entry.get(member), dict):
            returned[member] = unit_returned(entry[member])
    return returned


def specimen_returned(specimen: JsonObject) -> JsonObject:
    # read_side_contract.md:129 "the field's specimen facts, the section's merged with the field's"
    return {name: fact_returned(name, fact) for name, fact in specimen.items() if name in FACTS}


def fact_returned(name: str, fact: JsonValue) -> JsonValue:
    if not isinstance(fact, dict):
        return copied(fact)
    if "status" in fact:
        return status_returned(fact)
    returned = known_members(fact, fact_names(FACTS[name]))
    if isinstance(fact.get("unit"), dict):
        returned["unit"] = unit_returned(fact["unit"])
    return returned


def block_returned(block: JsonValue) -> JsonValue:
    # read_side_contract.md:130 "| `statistics` | as stored |"
    if not isinstance(block, dict):
        return copied(block)
    if "status" in block:
        return status_returned(block)
    returned: JsonObject = {}
    for name in BLOCK_NAMES:
        if name not in block:
            continue
        member = block[name]
        if name in ("relative_uncertainty", "expanded_uncertainty"):
            returned[name] = uncertainty_returned(member)
        elif name == "population_level" and isinstance(member, dict) and "status" not in member:
            returned[name] = {
                level: status_returned(given) if isinstance(given, dict) else copied(given)
                for level, given in known_members(member, POPULATION_LEVEL_NAMES).items()
            }
        else:
            returned[name] = status_returned(member) if isinstance(member, dict) else copied(member)
    return returned


def uncertainty_returned(uncertainty: JsonValue) -> JsonValue:
    if not isinstance(uncertainty, dict):
        return copied(uncertainty)
    if "status" in uncertainty:
        return status_returned(uncertainty)
    return {
        name: status_returned(given) if isinstance(given, dict) else copied(given)
        for name, given in known_members(uncertainty, UNCERTAINTY_NAMES).items()
    }


def review_read(provenance: JsonObject) -> JsonObject:
    """A review as found, in two cases only, and otherwise as a status object holding `not_checked`:
    provenance.md:120 "A reader returns it as found in two cases only"."""
    review = provenance.get("review")
    not_checked: JsonObject = {"status": "not_checked"}
    if (
        not isinstance(review, dict)
        or slipped(review, REVIEW_NAMES)
        or ("status" in review and "result" in review)
    ):
        return not_checked
    if "status" in review:
        # provenance.md:45-46 "where its `status` or `reason` is not a string, or where it also holds a
        # member S defines"; provenance.md:51-52 "A status object that breaks its shape is read for nothing
        # else"
        broken = not isinstance(review.get("reason", ""), str) or any(
            name in review for name in REVIEW_NAMES[2:]
        )
        return status_returned(review) if review["status"] == "not_checked" and not broken else not_checked
    if review.get("result") in REVIEW_RESULTS:
        return known_members(review, RESULT_REVIEW_NAMES)
    return not_checked


def provenance_returned(provenance: JsonObject) -> JsonObject:
    # read_side_contract.md:131 "| `provenance` | `{"origin", "review", "source", "derivation"}`"
    returned: JsonObject = {"origin": copied(provenance["origin"]), "review": review_read(provenance)}
    source = provenance.get("source")
    if isinstance(source, dict) and isinstance(source.get("key"), str):
        returned["source"] = copied(source["key"])
    derivation = provenance.get("derivation")
    if provenance["origin"] == "derived" and isinstance(derivation, dict):
        returned["derivation"] = derivation_returned(derivation)
    return returned


def derivation_returned(derivation: JsonObject) -> JsonObject:
    # read_side_contract.md:131 "and for origin `derived` the `derivation`'s `method`, `inputs`,
    # `assumptions`, `input_specimens` and `mixed_conditions`"
    returned = known_members(derivation, DERIVATION_NAMES)
    inputs = derivation.get("inputs")
    if isinstance(inputs, list):
        returned["inputs"] = [input_returned(given) for given in inputs if isinstance(given, dict)]
    entries = derivation.get("input_specimens")
    if isinstance(entries, list):
        returned["input_specimens"] = [
            input_specimen_returned(entry) for entry in entries if isinstance(entry, dict)
        ]
    return returned


def input_returned(given: JsonObject) -> JsonValue:
    returned = known_members(given, INPUT_NAMES)
    record = given.get("record")
    if isinstance(record, dict):
        returned["record"] = known_members(record, REFERENCE_NAMES)
    return returned


def input_specimen_returned(entry: JsonObject) -> JsonValue:
    returned = known_members(entry, INPUT_SPECIMEN_NAMES)
    specimen = entry.get("specimen")
    if isinstance(specimen, dict):
        returned["specimen"] = specimen_returned(specimen)
    return returned


def form_member_returned(form: str, member: JsonValue) -> JsonValue:
    """A form's member as stored: a number, or the known members of an interval, a composition or a list of
    evidence."""
    if form == "interval" and isinstance(member, dict):
        # read_side_contract.md:531 "| `bounds` | `not_met` (`want_mismatch`)"
        return {
            side: status_returned(given) if isinstance(given, dict) else copied(given)
            for side, given in known_members(member, INTERVAL_NAMES).items()
        }
    if form == "composition" and isinstance(member, dict):
        # record_format.md:492-493 "its basis, sum rule, stated sum where present, and components"
        returned = known_members(member, COMPOSITION_NAMES)
        components = member.get("components")
        if isinstance(components, list):
            returned["components"] = [
                component_returned(given) for given in components if isinstance(given, dict)
            ]
        return returned
    if form == "evidence" and isinstance(member, list):
        return [evidence_entry_returned(entry) for entry in member if isinstance(entry, dict)]
    if form == "table" and isinstance(member, dict):
        # read_side_contract.md:166-167 "(statistics, bounds, components, a table)"; read_side_contract.md:168
        # "A member the reader does not know is left out"
        return known_members(member, TABLE_MEMBERS)
    return copied(member)


def component_returned(component: JsonObject) -> JsonValue:
    returned = known_members(component, COMPONENT_NAMES)
    if "statistics" in component:
        returned["statistics"] = block_returned(component["statistics"])
    return returned


# record_format.md:252-254 "A reader returns an entry with its statuses and its `provenance` whole" ...
# "section 2 item 5 defines": read_side_contract.md:165 "Every member a result returns from a record holds
# the members the reader's version defines", at every depth. Below the provenance table's own members the
# text names their members in part only (an extraction's by its methods' rows, a locator's in provenance.md
# section 2 item 2), so the model reads them where the version publishes them, its writer schema
# (record_format.md:10-11 "JSON Schema 2020-12, published with the" ... "specification in `schema/`"): each
# definition's named members, or, for an object it names none of, a map whose values it gives.
WRITER: Final[JsonObject] = json.loads(
    (
        Path(__file__).resolve().parents[2] / "src" / "materica" / "schema" / "0.1" / "record.writer.json"
    ).read_text(encoding="utf-8")
)


def definitions(node: JsonValue) -> list[JsonObject]:
    """The definitions `node` stands for: through a local reference, and each choice of `anyOf` or `oneOf`."""
    if not isinstance(node, dict):
        return []
    reference = node.get("$ref")
    if isinstance(reference, str):
        if not reference.startswith("#/$defs/"):
            return []
        defined = WRITER["$defs"]
        assert isinstance(defined, dict)
        return definitions(defined[reference.removeprefix("#/$defs/")])
    choices = node.get("anyOf", node.get("oneOf"))
    if isinstance(choices, list):
        return [found for choice in choices for found in definitions(choice)]
    return [node]


def named_members(definition: JsonObject) -> dict[str, JsonValue]:
    """A definition's members by name, those of each definition its `allOf` refers to included."""
    found: dict[str, JsonValue] = {}
    conjuncts = definition.get("allOf")
    for conjunct in conjuncts if isinstance(conjuncts, list) else []:
        for part in definitions(conjunct):
            found.update(named_members(part))
    properties = definition.get("properties")
    found.update(properties if isinstance(properties, dict) else {})
    return found


def written_returned(value: JsonValue, nodes: Sequence[JsonValue]) -> JsonValue:
    """`value`, where one of `nodes` defines it, holding at every depth the members the definitions name: an
    object holding `status`, the status object's (`status`, `reason`) where a choice is one; and a member no
    definition names anything of, whole."""
    choices = [found for node in nodes for found in definitions(node)]
    if isinstance(value, list):
        items = [choice["items"] for choice in choices if "items" in choice]
        return [written_returned(item, items[:1]) if items else copied(item) for item in value]
    if not isinstance(value, dict):
        return copied(value)
    objects = [choice for choice in choices if named_members(choice)]
    chosen = [
        choice
        for choice in objects
        if (set(named_members(choice)) <= {"status", "reason"}) == ("status" in value)
    ]
    maps = [choice.get("additionalProperties") for choice in choices if not named_members(choice)]
    maps = [held for held in maps if isinstance(held, dict)]
    if not chosen and maps:
        return {name: written_returned(member, maps[:1]) for name, member in value.items()}
    members: dict[str, list[JsonValue]] = {}
    for choice in chosen or objects:
        for name, node in named_members(choice).items():
            members.setdefault(name, []).append(node)
    if not members:
        return copied(value)
    return {
        name: written_returned(member, members[name]) for name, member in value.items() if name in members
    }


def entry_provenance_returned(provenance: JsonObject) -> JsonObject:
    """An evidence entry's `provenance`, or one it holds at any depth, returned whole: its members as found,
    each provenance among them returning its review as every review is read."""
    # Open point: evidence_entry_provenance. record_format.md:253-254 "holding the members
    # `read_side_contract.md` section 2 item 5 defines"
    returned = written_returned(provenance, [{"$ref": "#/$defs/provenance"}])
    assert isinstance(returned, dict)
    # record_format.md:256-258 "except that each provenance they hold, at any depth (one that `per_parameter`
    # maps a parameter to, say), returns its `review` as that item reads every review"
    per_parameter = provenance.get("per_parameter")
    if isinstance(per_parameter, dict):
        mapped = returned["per_parameter"]
        assert isinstance(mapped, dict)
        returned["per_parameter"] = {
            name: entry_provenance_returned(held) if isinstance(held, dict) else mapped[name]
            for name, held in per_parameter.items()
        }
    # provenance.md:120 "A reader returns it as found in two cases only"
    return {**returned, "review": review_read(provenance)}


def evidence_entry_returned(entry: JsonObject) -> JsonValue:
    returned: JsonObject = {}
    for name in EVIDENCE_ENTRY_NAMES:
        if name not in entry:
            continue
        given = entry[name]
        if name == "provenance" and isinstance(given, dict):
            returned[name] = entry_provenance_returned(given)
        elif isinstance(given, dict) and "status" in given:
            returned[name] = status_returned(given)
        elif name == "standard" and isinstance(given, dict):
            returned[name] = known_members(given, STANDARD_NAMES)
        else:
            returned[name] = copied(given)
    return returned


# A table's steps 10 and 11


@dataclass(frozen=True)
class TableAxis:
    """A table's axis and the status of its entry in `conditions` (step 10)."""

    name: str
    status: Status


def table_numbers(table: JsonObject, name: str) -> list[float]:
    found = numbers_of(table.get(name))
    assert found is not None, f"step 8 passed a table whose {name} is not a list of numbers"
    return found


def readable_range(table: JsonObject) -> tuple[float, float]:
    """record_format.md:416-417 "from `x[0]`, or `source_range[0]` where that is greater, to `x[-1]`, or
    `source_range[1]` where that is smaller, inclusive"."""
    x = table_numbers(table, "x")
    low, high = x[0], x[-1]
    if "source_range" in table:
        bounds = table_numbers(table, "source_range")
        low, high = max(low, bounds[0]), min(high, bounds[1])
    return low, high


def at_an_edge(table: JsonObject, point: float) -> bool:
    """record_format.md:417-419 "An operating value is compared with these ends and with the edges by value
    and exactly" ... "so `-0` lies at an end or an edge at `0`": as Python compares two doubles."""
    return any(edge == point for edge in table_numbers(table, "edges"))


def inside(table: JsonObject, point: float) -> bool:
    low, high = readable_range(table)
    return low <= point <= high


def table_axis(field_value: JsonObject, request: Request) -> TableAxis:
    """The table's axis entry: read_side_contract.md:475 "the entry is `met` when the operating value lies in
    the form's range and on no declared edge" ... "and otherwise `not_met`, with no operating value or over an
    operating range included"."""
    table = field_value["table"]
    assert isinstance(table, dict)
    name = table["axis"]
    assert isinstance(name, str)
    operating = request.operating.get(name)
    point = operating.get("value") if operating is not None else None
    met = number(point) and inside(table, point) and not at_an_edge(table, point)
    return TableAxis(name, "met" if met else "not_met")


def read_the_table(read: "FieldRead", table: JsonObject, request: Request) -> float | None:
    """Step 11 of a table (read_side_contract.md:359-360 "Evaluate the form at the operating conditions,
    within its range"): its reasons put in `read`, which ends there where one is `not_met`; the value at the
    operating value where the read goes on. Each reason carries the axis, read_side_contract.md:143 "A reason
    carries `condition` exactly when it concerns one condition or a form's axis"."""
    axis = table["axis"]
    assert isinstance(axis, str)
    operating = request.operating.get(axis)
    if operating is None:
        # read_side_contract.md:103-104 "a table or power law read with no operating value for its axis is
        # refused with `request_incomplete`"; read_side_contract.md:115 "This fault, like step 11's
        # `request_incomplete`, is the request's"
        read.by_request.add("request_incomplete", axis)
        read.ended_at = 11
        return None
    if "range" in operating:
        # read_side_contract.md:104-106 "and one read over an operating range of its axis gives
        # `want_mismatch`" ... "and no other reason of that step, since no point is read"
        read.own.add("want_mismatch", axis)
        read.ended_at = 11
        read.over_a_range = True
        return None
    point = operating["value"]
    assert number(point)
    # record_format.md:419 "A read exactly at an edge is refused (the value is two-sided), wherever the edge
    # lies"; read_side_contract.md:359-360 "`at_edge` for a table read exactly at an edge"
    if at_an_edge(table, point):
        read.own.add("at_edge", axis)
    # read_side_contract.md:512-514 "A **table** is read at the operating value of its axis, which must lie
    # within its readable range" ... "the tolerance never widens a table" ... "Outside the range, the result
    # is `not_met` (`outside_range`)"; record_format.md:420-421 "Where the edge lies outside the readable
    # range" ... "`outside_range` stands beside `at_edge`"
    if not inside(table, point):
        read.own.add("outside_range", axis)
    if read.own.end_the_read():
        if not extrapolation_covers(table, point, request):
            # read_side_contract.md:186 "A step that gives `not_met` ends the read, with the reasons found so
            # far"
            read.ended_at = 11
            return None
        # read_side_contract.md:186-188 "except step 11's `outside_range` under an extrapolation that applies
        # (section 5), after which the read goes on to steps 12 and 13"; read_side_contract.md:516-517 "the
        # result stays `not_met`, its reasons kept" ... "and the result carries the value at the range's
        # nearest end, taken from inside the range"
        read.covered = request.extrapolation
        point = nearest_end(table, point)
    # record_format.md:423-426 "the interval used is the one whose two knots bracket the read, strictly where
    # an edge is concerned" ... "a knot outside `source_range` is used where it brackets a read inside the
    # readable range": the reference evaluator's exact value, rounded once to a double, a knot's `-0` kept
    scheme = table["scheme"]
    assert scheme in TABLE_SCHEMES
    bounds = table_numbers(table, "source_range") if "source_range" in table else None
    evaluated = table_evaluator.evaluate(
        table_evaluator.Table(
            x=tuple(table_numbers(table, "x")),
            y=tuple(table_numbers(table, "y")),
            scheme="linear" if scheme == "linear" else "loglog",
            edges=tuple(table_numbers(table, "edges")),
            source_range=None if bounds is None else (bounds[0], bounds[1]),
        ),
        point,
        "exact",
    )
    assert evaluated.in_range, evaluated
    assert evaluated.value is not None, evaluated
    return float(evaluated.value)


def extrapolation_covers(table: JsonObject, point: float, request: Request) -> bool:
    """Whether the request's extrapolation covers a read outside the readable range:
    read_side_contract.md:515 "Under `want: value`, a declared extrapolation that applies to the read (section
    1) covers it"; read_side_contract.md:519-520 "Under any other `want` an extrapolation is not applied, nor
    at a declared edge"; read_side_contract.md:522-523 "Nor is an extrapolation applied across a declared
    edge: where an edge lies between the operating value and the readable range's nearest end, or on that
    end"."""
    if request.want != "value" or request.extrapolation is None or at_an_edge(table, point):
        return False
    end = nearest_end(table, point)
    return not any(min(point, end) <= edge <= max(point, end) for edge in table_numbers(table, "edges"))


def nearest_end(table: JsonObject, point: float) -> float:
    """The end of the readable range nearest `point`, which lies outside it: read_side_contract.md:517 "the
    value at the range's nearest end, taken from inside the range"."""
    low, high = readable_range(table)
    return low if point < low else high


# Steps 8 to 13 of one value field


@dataclass
class FieldRead:
    """One value field read alone: its reasons, and what a result returns from it."""

    own: Reasons = field(default_factory=Reasons)  # steps 8 to 12
    by_want: Reasons = field(default_factory=Reasons)  # step 13
    by_request: Reasons = field(default_factory=Reasons)  # step 10's `request_incomplete`, the request's
    ended_at: int | None = None  # the step whose `not_met` ended the read, None where it reached step 13
    covered: JsonObject | None = None  # the assumption of an extrapolation that covered step 11's reason
    over_a_range: bool = False  # a table read over an operating range of its axis, which step 11 ends
    form: str | None = None
    conditions: list[JsonValue] | None = None
    labels: list[str] = field(default_factory=list[str])  # the result's, once step 12 has run
    # what a result returns from the field: `unit`, `specimen`, `provenance`, `statistics` and `value` or
    # none, and `table` beside a value read from a table
    members: JsonObject = field(default_factory=dict[str, JsonValue])
    stored: JsonValue = None  # the form's member as stored, for an `alternative_values` entry
    entry_labels: list[str] = field(default_factory=list[str])  # step 12's, for an `alternative_values` entry

    @property
    def reasons(self) -> Reasons:
        return Reasons((*self.own, *self.by_request, *self.by_want))


def read_value_field(
    field_value: JsonValue,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    *,
    record_fault: bool,
    nominal: float | None,
) -> FieldRead:
    read = FieldRead()
    faults, read.form = check_value_field(
        field_value, section, request.field, claims, record_fault=record_fault
    )
    read.own.extend(faults)
    if read.own.end_the_read() or not isinstance(field_value, dict) or read.form is None:
        read.ended_at = 8
        return read
    read.own.extend(check_units(field_value, section, request.field))
    if read.own.end_the_read():
        read.ended_at = 9
        return read
    specimen = merged_specimen(section, field_value)
    axis = table_axis(field_value, request) if read.form == "table" else None
    checked = check_against_request(field_value, specimen, request, axis)
    if checked.entries is None:
        # read_side_contract.md:114-115 "This fault, like step 11's `request_incomplete`, is the request's"
        read.by_request.extend(checked.reasons)
        read.ended_at = 10
        return read
    read.own.extend(checked.reasons)
    # read_side_contract.md:170-171 "`conditions` is present once step 10 has run to its end, and only then"
    read.conditions = checked.entries
    if read.own.end_the_read():
        read.ended_at = 10
        return read
    # read_side_contract.md:511-512 "A **constant's** range is its conditions: once they are met, it is read;
    # step 11 adds nothing."
    point = None
    if read.form == "table":
        table = field_value["table"]
        assert isinstance(table, dict)
        point = read_the_table(read, table, request)
        if read.over_a_range:
            # read_side_contract.md:126 "or is a table read over an operating range of its axis, the entry
            # holds its form's member as stored instead" ... "except that its `labels` are those step 12
            # gives that alternative even where its read ended at step 11, as a table read over an operating
            # range of its axis does": what an entry holds, though the read ends here
            returned_from_the_field(read, field_value, specimen)
        if read.ended_at is not None:
            return read
    provenance = field_value["provenance"]
    assert isinstance(provenance, dict)
    # read_side_contract.md:363 "Give `unknown` for a value stated without origin (`stated_without_origin`)"
    if provenance["origin"] == "stated_without_origin":
        read.own.add("stated_without_origin")
    returned_from_the_field(read, field_value, specimen)
    read.labels = list(read.entry_labels)
    shape_by_want(read, field_value, request, nominal, point)
    return read


def returned_from_the_field(read: FieldRead, field_value: JsonObject, specimen: JsonObject) -> None:
    """What a result, or an `alternative_values` entry, returns from the field beside its value: its form's
    member as stored, `unit`, `specimen`, `provenance` and `statistics`, and the labels step 12 gives it."""
    assert read.form is not None
    provenance = field_value["provenance"]
    assert isinstance(provenance, dict)
    read.entry_labels = step_12_labels(field_value, provenance)
    read.stored = form_member_returned(read.form, field_value[FORM_MEMBERS[read.form]])
    read.members = {
        "unit": unit_returned(field_value["unit"]),
        "specimen": specimen_returned(specimen),
        "provenance": provenance_returned(provenance),
    }
    if read.form != "evidence":
        # uncertainty.md:61-62 "A block on a table or a power law applies to every value the form gives"
        read.members["statistics"] = block_returned(field_value["statistics"])


def step_12_labels(field_value: JsonObject, provenance: JsonObject) -> list[str]:
    # read_side_contract.md:364-365 "add the labels of section 2"
    labels: list[str] = []
    if isinstance(field_value.get("label"), str):
        labels.append(str(field_value["label"]))
    derivation = provenance.get("derivation")
    # read_side_contract.md:132 "`mixed_conditions` (a derived value whose inputs' conditions differ)"
    if (
        provenance["origin"] == "derived"
        and isinstance(derivation, dict)
        and derivation.get("mixed_conditions") is True
    ):
        labels.append("mixed_conditions")
    return labels


def shape_by_want(
    read: FieldRead, field_value: JsonObject, request: Request, nominal: float | None, point: float | None
) -> None:
    """Step 13 (read_side_contract.md section 6), `point` a table's value at the operating value."""
    assert read.form is not None
    if request.want == "fit" and "fit" in field_value:
        raise _Undecided("`want: fit` on a field holding a fit record (the fits and reference data suite)")
    if read.form == "table" and request.want == "value":
        # read_side_contract.md:530 "| `value` | the number at the operating conditions";
        # read_side_contract.md:134 "where the value is read from a table: that table as stored (item 5)"
        read.members["value"] = point
        read.members["table"] = read.stored
        if read.covered is not None:
            # read_side_contract.md:517 "taken from inside the range, and `assumption`";
            # read_side_contract.md:133 "the declaration it rests on"
            read.members["assumption"] = read.covered
        return
    if read.form in GIVES.get(request.want, ()):
        read.members["value"] = read.stored
        return
    if read.form == "interval" and request.want == "value" and nominal is not None:
        member = field_value["interval"]
        assert isinstance(member, dict)
        lower, upper = member["lower"], member["upper"]
        # read_side_contract.md:544-545 "A nominal applies only under `want: value`, inside or on the
        # interval's bounds, compared exactly, on the bounded side of a one-sided interval"
        inside = (not isinstance(lower, float) or Fraction(lower) <= Fraction(nominal)) and (
            not isinstance(upper, float) or Fraction(nominal) <= Fraction(upper)
        )
        if inside:
            # read_side_contract.md:530 "a declared nominal inside or on the bounds supplies `value` and
            # `assumption`"
            read.by_want.add("want_mismatch")
            read.members["value"] = nominal
            # read_side_contract.md:133 "the declaration it rests on"
            read.members["assumption"] = {"acceptance": "nominal", "value": nominal}
        else:
            # read_side_contract.md:530 "and one outside them gives `nominal_invalid` in place of
            # `want_mismatch`"
            read.by_want.add("nominal_invalid")
        return
    read.by_want.add("want_mismatch")


# Step 7, and the read


def read(
    request: JsonValue | NotStrictJson, sources: Sequence[bytes], claims: Iterable[str]
) -> JsonObject | NoVerdict:
    """The result of a read of `request` among `sources` by a reader that claims `claims`, or no verdict."""
    claimed = frozenset(claims)
    if "plain_read" not in claimed:
        raise ValueError("a reader claims plain read (README.md, Suites and case numbers)")
    try:
        return read_decided(request, sources, claimed)
    except _Undecided as undecided:
        return NoVerdict(undecided.why)


def read_decided(
    request: JsonValue | NotStrictJson, sources: Sequence[bytes], claims: frozenset[str]
) -> JsonObject:
    reasons = Reasons()
    labels: list[str] = []
    if isinstance(request, NotStrictJson):
        # read_side_contract.md:19 "A request is read as JSON by `record_format.md` section 1 item 6"
        reasons.add("request_incomplete")
        return result(reasons, labels)
    checked = check_request(request, claims, reasons)
    if checked is None or checked.reference is None:
        return result(reasons, labels)
    record = resolve(checked.reference, sources_read(sources), claims, reasons, labels)
    if record is None:
        return result(reasons, labels)
    # Step 6 applies the overlays the acceptances name, and `check_request` leaves none undecided.
    body = record["body"]
    assert isinstance(body, dict)
    sections = body["sections"]
    assert isinstance(sections, dict)
    section_name, _, field_key = checked.field.partition(".")
    section = sections.get(section_name)
    # read_side_contract.md:243 "Find the field (`absent`)"
    if not isinstance(section, dict):
        reasons.add("absent")
        return result(reasons, labels)
    fields = section["fields"]
    assert isinstance(fields, dict)
    if field_key not in fields:
        reasons.add("absent")
        return result(reasons, labels)
    field_value = fields[field_key]
    record_fault = record_slips(record) or section_slips(section, section_name)
    if isinstance(field_value, dict) and "alternatives" in field_value:
        return read_alternatives(
            field_value, section, checked, claims, reasons, labels, record_fault=record_fault
        )
    read_field = read_value_field(
        field_value, section, checked, claims, record_fault=record_fault, nominal=checked.nominal
    )
    reasons.extend(read_field.reasons)
    return field_result(reasons, labels, read_field)


def field_result(reasons: Reasons, labels: Sequence[str], read_field: FieldRead) -> JsonObject:
    """The result of one value field's read, a field's or the one alternative left, its reasons in
    `reasons`."""
    returned: JsonObject = {}
    if read_field.conditions is not None:
        returned["conditions"] = read_field.conditions
    if value_returned(reasons.status, read_field.members):
        returned.update(read_field.members)
    return result(reasons, [*labels, *read_field.labels], returned)


def value_returned(status: Status, members: JsonObject) -> bool:
    # read_side_contract.md:125 "| `value` | present unless `not_met` with neither an assumption": the model
    # gives no verdict under a `trainable` acceptance (S7a-4 builds it), so an assumption alone keeps the
    # value here.
    # read_side_contract.md:176-177 "`unit`, `specimen` (an empty object where no fact is stated) and
    # `provenance` are present exactly when `value` is"
    return "value" in members and (status != "not_met" or "assumption" in members)


def result(reasons: Reasons, labels: Sequence[str], members: JsonObject | None = None) -> JsonObject:
    # read_side_contract.md:170 "`reasons` and `labels` are always present, `labels` perhaps empty"
    returned: JsonObject = {
        "status": reasons.status,
        "reasons": reasons.to_json(),
        "labels": list(dict.fromkeys(labels)),
    }
    returned.update(members or {})
    return returned


def alternatives_broken(field_value: JsonObject) -> bool:
    # record_format.md:342-346 "`alternatives` is a non-empty list. Each entry is an object, and none holds
    # `alternatives` of its own. The object holding `alternatives` holds no member of a value field." ...
    # "an empty list, one that is not a list, an entry that is not an object or that holds `alternatives`, or
    # `alternatives` beside `form`, a form's member or another member of the table above"
    alternatives = field_value["alternatives"]
    return (
        not isinstance(alternatives, list)
        or not alternatives
        or any(name in field_value for name in VALUE_FIELD_NAMES)
        or slipped(field_value, FIELD_PLACE_NAMES)
        or any(
            not isinstance(alternative, dict) or "alternatives" in alternative for alternative in alternatives
        )
    )


def read_alternatives(
    field_value: JsonObject,
    section: JsonObject,
    request: Request,
    claims: frozenset[str],
    reasons: Reasons,
    labels: list[str],
    *,
    record_fault: bool,
) -> JsonObject:
    """Step 7 over alternatives with no pick (Open point: alternatives_without_a_pick)."""
    # read_side_contract.md:244-245 "A field whose `alternatives` breaks its shape is refused (`form_invalid`"
    if alternatives_broken(field_value):
        reasons.add("form_invalid")
        return result(reasons, labels)
    alternatives = field_value["alternatives"]
    assert isinstance(alternatives, list)
    # read_side_contract.md:259-260 "each alternative is read alone, as a field, by steps 8 to 13, and its
    # read ends where a field's would"; read_side_contract.md:281 "a nominal's outside an interval's bounds
    # among them": the nominal is compared in each read, and applied only to the one left (below)
    reads = [
        read_value_field(
            alternative, section, request, claims, record_fault=record_fault, nominal=request.nominal
        )
        for alternative in alternatives
    ]
    # read_side_contract.md:260-261 "The outcome is decided once every alternative is read"
    fates = [fate_of(one) for one in reads]
    # read_side_contract.md:126 "counts from 0, in stored order"
    staying = [index for index, fate in enumerate(fates) if fate == "stays"]
    if "refuses" in fates or not staying:
        # read_side_contract.md:286 "where an alternative refuses the field, or every alternative is set
        # aside"
        reasons.extend(reasons_where_refused(reads))
        # read_side_contract.md:303-304 "and its `labels` holds at most `hash_not_checked`"
        return result(reasons, labels)
    if len(staying) == 1:
        # read_side_contract.md:288-289 "where one alternative stays, that alternative's read, `want`
        # included; the set-aside ones' reasons are not reported"
        (left,) = staying
        reasons.extend(reasons_of_alternative(reads[left], left))
        return field_result(reasons, labels, reads[left])
    reasons.extend(reasons_beside_two_or_more(reads, staying))
    can_give = [index for index in staying if form_want_gives(reads[index], request)]
    if not can_give:
        # read_side_contract.md:290-291 "where two or more stay and none has a form `want` can give,
        # `not_met`, with `want_mismatch`, since no pick could help"
        reasons.add("want_mismatch")
        return result(reasons, labels)
    # read_side_contract.md:294 "otherwise `unknown`, with `no_pick`"
    reasons.add("no_pick")
    entries: list[JsonValue] = []
    # read_side_contract.md:294-295 "each alternative that stays appears in `alternative_values` as section 2
    # says, with no nominal or extrapolation applied"
    for index in staying:
        one = reads[index]
        assert one.conditions is not None
        entry: JsonObject = {
            "alternative": float(index),
            "value": entry_value(one, request),
            "conditions": one.conditions,
        }
        # read_side_contract.md:127 "each `alternative_values` entry holds its own alternative's unit, as
        # stored"
        entry.update(
            {
                name: one.members[name]
                for name in ("unit", "specimen", "statistics", "provenance")
                if name in one.members
            }
        )
        # read_side_contract.md:126 "except that its `labels` are those step 12 gives that alternative even
        # where its read ended at step 11"
        entry["labels"] = list(one.entry_labels)
        entries.append(entry)
    # read_side_contract.md:178-179 "Under `no_pick` the result holds none of `unit`, `conditions`,
    # `specimen`, `statistics` and `provenance`"
    return result(reasons, labels, {"alternative_values": entries})


def form_want_gives(read: FieldRead, request: Request) -> bool:
    """Whether an alternative that stays has a form `want` can give, where two or more stay."""
    # read_side_contract.md:291 "A table read over an operating range of its axis counts as a form `want`
    # cannot give."
    if read.over_a_range:
        return False
    # read_side_contract.md:292-293 "An interval counts as one `want: value` can give where a nominal the
    # request carries applies to the read"
    return read.form in GIVES.get(request.want, ()) or (
        read.form == "interval" and request.want == "value" and request.nominal is not None
    )


def entry_value(read: FieldRead, request: Request) -> JsonValue:
    """An `alternative_values` entry's `value`: read_side_contract.md:126 "`value` is its value as `want`
    shapes it. Where `want` cannot give its form, or where the alternative is kept outside its form's range
    or is a table read over an operating range of its axis, the entry holds its form's member as stored
    instead, with no nominal or extrapolation applied"; read_side_contract.md:272-273 "The extrapolation is
    applied only where that alternative is the one left": a table's number where `want` gives the form and
    the table is read at a point inside its readable range, otherwise the member as stored."""
    outside = any(reason.code == "outside_range" for reason in read.own)
    if read.form in GIVES.get(request.want, ()) and not outside and not read.over_a_range:
        return read.members["value"]
    return read.stored


Fate: TypeAlias = Literal["set_aside", "stays", "refuses"]


def fate_of(read: FieldRead) -> Fate:
    """What step 7 does with one alternative read with no pick: read_side_contract.md:261 "Each alternative is
    set aside, stays, or refuses the field"."""
    # read_side_contract.md:276-279 "So does a fault of the request (section 1): an alternative whose read
    # reaches step 11 with no operating value for its form's axis refuses the field": step 10's two implied
    # conditions that disagree, and step 11's `request_incomplete` for the axis
    if read.by_request:
        return "refuses"
    # read_side_contract.md:262-263 "An alternative is set aside where its conditions, the form's own axis
    # entry aside (section 5), give `not_met` at step 10"; read_side_contract.md:278-279 "while one set aside
    # at step 10 never reaches step 11 and refuses nothing"
    if read.ended_at == 10:
        return "set_aside"
    # read_side_contract.md:268-271 "Nothing else sets an alternative aside. These stay" ... "and one whose
    # form `want` cannot give" ... "or a table read over an operating range of its axis, say"
    if read.over_a_range:
        return "stays"
    if read.ended_at == 11:
        codes = {reason.code for reason in read.own}
        # read_side_contract.md:264-265 "An alternative is set aside where its read lies outside its form's
        # range at step 11, not exactly at a declared edge, and no extrapolation the request carries would
        # cover it": one that an extrapolation covers reads on (below), so `outside_range` ended this read
        if "outside_range" in codes and "at_edge" not in codes:
            return "set_aside"
        # read_side_contract.md:275-276 "A table alternative read exactly at a declared edge refuses the
        # field, wherever the edge lies, outside the readable range included"; record_format.md:367-368
        # "refuses the field, wherever the edge lies, even where `outside_range` stands beside it"
        return "refuses"
    # read_side_contract.md:274 "Every other `not_met` in an alternative's read refuses the field"
    if read.ended_at is not None:
        return "refuses"
    # read_side_contract.md:268-271 "These stay: one whose read gives no `not_met`; one that an extrapolation
    # the request carries would cover" ... "and one whose form `want` cannot give": a read that reaches step
    # 13 gives a `not_met` there alone, `want_mismatch`, or `nominal_invalid` (read_side_contract.md:281 "a
    # nominal's outside an interval's bounds among them"), or the `outside_range` an extrapolation covers,
    # after which the read goes on (read_side_contract.md:271-272 "An alternative kept for an extrapolation is
    # read on through steps 12 and 13, as a field is")
    return "stays"


def reasons_of_alternative(read: FieldRead, index: int) -> Reasons:
    """The reasons the read of the alternative at `index` reports, where step 7 reports them."""
    # read_side_contract.md:301-302 "Every reason found reading one alternative carries its `alternative`; a
    # fault of the request carries none"
    return Reasons((*read.own.found_in(index), *read.by_request, *read.by_want.found_in(index)))


def reasons_where_refused(reads: Sequence[FieldRead]) -> Reasons:
    # read_side_contract.md:286-287 "`not_met`, with every alternative's reasons, those that wait included"
    # read_side_contract.md:126 "counts from 0, in stored order"
    return Reasons(reason for index, one in enumerate(reads) for reason in reasons_of_alternative(one, index))


def reasons_beside_two_or_more(reads: Sequence[FieldRead], staying: Sequence[int]) -> Reasons:
    # read_side_contract.md:299-301 "each one's `unknown` reasons stand beside `want_mismatch` or `no_pick`,
    # and its `not_met` reasons wait" ... "A set-aside alternative's reasons are not reported there"
    return Reasons(
        reason
        for index in staying
        for reason in reasons_of_alternative(reads[index], index).of_status("unknown")
    )
