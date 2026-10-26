# Schema changes

Each schema version, what changed, and the conformance cases that came with it
(`DOCUMENTATION_ARCHITECTURE.md` section 7.2). Before 1.0.0 a reader reads only its own minor version
(`README.md`), so a minor version may change any shape; each change is listed here.

## 0.1.0 (draft, 2026-10-12)

The first version. It specifies records (the envelope, record types `material` and `overlay` with `interface`
reserved, the bulk, fluid, magnetic and biocompatibility sections, the eight form tokens, units, identifiers,
versions and the content hash), provenance, uncertainty, model families, fits and reference data, scene
documents, the USD binding, mixing rules, declarations and the read-side contract. Its cases are those listed
at the end of each document. Scene documents, layered paths, label crosswalks, the USD binding, the stage
check and the engine adapter are in 0.1.0; families, fits and reference data, and mixing are specified but
their suites are optional until the minor version that brings their first consumer (`README.md`). In USD a
region binds its material with the purpose `materica`; the `physics` purpose is left to engines, whose
materials an engine adapter writes from a declared engine model by an engine crosswalk, stamped with the reads
they came from, and which the stage check re-derives per shape (`usd_binding.md` sections 5, 9 and 10).
OpenMaterica ships one engine crosswalk, for `UsdPhysics`; a consumer writes the crosswalk for any other
engine it runs, drafted by a scaffold. Acoustic attenuation is registered in `/m`.

Settled before the first code (maintainer, 2026-10-13): a reader refuses as malformed exactly what RFC 8259's
grammar refuses and a listed set of further faults, follows I-JSON except that noncharacters are legal, and
reads every number as the nearest double, ties to even (`record_format.md` section 1 item 6; PR-002, PR-047);
`null` is read by where it is, and ignored inside a member the reader does not know (PR-049); records' and
other documents' schema versions match one pattern, and a missing or ill-formed `schema_version` is malformed
(`record_format.md` section 8; PR-048), as is a scene document's `scene_schema_version` (SC-002), while an
engine crosswalk with
an ill-formed or other `crosswalk_schema_version` is invalid (RC-140); the reader schema, in JSON Schema
2020-12, checks the envelope with the patterns of `id`, `version` and `content_hash`, and the body's structure
as far as the reader's version knows it, never a value field, form or section `specimen`, whose shape errors
refuse only the fields they affect, nor an unknown section or anything inside `extensions`
(`record_format.md` section 1 items 2
and 3; PR-008, PR-034, PR-045); an object with `document_type` and no `record_type` is not a record (PR-006);
a material reference resolves among the records supplied by hash, giving `malformed` where the record may be a
source that did not parse, one without a string `id` and `version`, or a candidate with an ill-formed
`content_hash`, or where two copies differ in their bytes (`read_side_contract.md` section 3, step 1; PR-328,
PR-329); the request has an exact shape and is checked on its own first, with structural, `want`,
condition-name, range and tolerance checks, and the two checks that need the form at step 11 (PR-330); a
`want` of a suite the reader does not claim gives `want_mismatch` at step 0 (PR-332); a reason appears once
per code and condition, with `condition` on a listed set of codes, and each step makes all its checks
(PR-331); with HS, a recomputed hash that differs gives `hash_mismatch` and one `pin_mismatch` (HS-010,
HS-011), and `hash_not_checked` labels only results that reach step 4; an overlay is resolved after the
target, and its base pin compared at step 6; the hash vectors widened (HS-003); case files gain claims,
variants (one file per arm, a case passing when a variant ran and none failed), exact comparison, a request
file for requests that break item 6, the `content_hash` operation and the `list_records` operation (always
`met`, listing only the good records), a `cases/` and `inputs/` layout, `labels` compared without
`hash_not_checked` unless a hash claim is stated, and reasons compared as a multiset of code and condition
(`README.md`, "Case files"); a request's unit is compared with the registered unit code point for code point,
after JSON escapes are decoded, on any operating condition or tolerance of a registered numeric condition
whose unit is a string, whatever else is wrong with the entry, and a request member the shape does not name at
that place is ignored (PR-320, PR-330); a reference with no candidate holding its hash gives `malformed`, not
`pin_mismatch`, when a supplied source is unreadable (PR-329); strings are hashed with no Unicode
normalisation (`record_format.md` section 9 item 2; HS-003); and the namespace `conformance` is reserved for
conformance fixtures, whose contents are illustrative: a record check flags one given from outside a
conformance tree, and a check of a whole library leaves conformance trees out (`record_format.md` section 7;
RC-121). Names, settled before any release (maintainer, 2026-10-14): the project is OpenMaterica; the
reserved namespace, the family namespace, the USD binding purpose and the attribute namespace are `materica`,
where drafts before that date used a working name; the schema class prefix is `Materica`; and the local ids in
`materica` are `MAT-NNNN` and `INT-NNNN` (`record_format.md` section 7; RC-012, RC-013). Settled with S1's
review (maintainer, 2026-10-14): a tolerance whose condition has no operating entry because
`operating_conditions` is not an object gives `request_incomplete` with that `condition`, beside the member's
own `request_incomplete` (`read_side_contract.md` section 1; PR-330); and the vocabulary files are published
with the schemas, under `schema/0.1/vocabulary/` (`provenance.md` section 6).

Settled for the read of values (maintainer, 2026-10-14). The read: a record's units are compared with the
registered unit code point for code point, a unit held as a status object by its token, at step 9 alone, step
8 checking only that a unit is a string or a status object (`record_format.md` section 4.2; PR-010, PR-037); a
request for a field the reader does not know is `request_incomplete` (PR-330); step 8 checks the members a
read uses or returns, the statistics block among them, a composition component's included, and lists the
values it checks: counts whole and not negative, ranges and bounds in order, a ± and a standard deviation not
below zero, and coverage factors, coverage probabilities and degrees of freedom in range (PR-051, PR-158);
`family_suite_absent` is given at step 8 (PR-036); `source` is required for origin `measured_by_source` and
checked for its `key` only, and `derivation` by the shapes `provenance.md` section 5 now gives; `review` never
refuses a read, and a review that is `null`, absent or not an object, holds both `status` and `result`, or
holds a status token other than `not_checked` or an unknown `result` token reads as `{"status":
"not_checked"}` (PR-109); `null` refuses a field only in a member step 8 checks (PR-049); `provenance.md`
section 1 lists every member that may hold a status object, with its tokens, and an object holding `status`
there is a status object, one that also holds a member of the shape it stands for, or any member but `reason`
where that shape is a number, a string or a token (which amends, for those positions only, the earlier ruling
that other members beside it are ignored), being a shape error, as is a token its row does not allow, each
refusing at read only in a member step 8 checks, and a key `status` in `conditions` or `specimen` naming a
condition or a fact (PR-110); a token the reader knows for a member of that name, in a member whose row does
not allow it, is `form_invalid`, and one it knows for no member of that name `unknown_token`, labels included
(PR-053, PR-154, PR-158); a result holds only the members the reader's version defines, in every member it
returns from a record, with its members present by the step the read reached and its condition entries
compared by name (PR-336, PR-337); a derived value's derivation, its assumptions included, is returned, with
the label `mixed_conditions` (PR-102); a label the row does not name for the field refuses it, and a missing
one is not refused at read (PR-035, PR-053; RC-122); alternatives may differ in form, and none is set aside
for its form, so a grade's specification limits beside a lot's constant give `no_pick` until a pick, while a
`want` that no remaining alternative's form can give is `want_mismatch`; under `no_pick`, `alternative_values`
holds one entry per remaining alternative, with its index, its value or its form's member as stored, and its
own conditions, specimen, statistics, provenance and labels, the result holding no conditions, specimen,
statistics or provenance of its own, and no nominal is applied (PR-013, PR-338). Conditions: every comparison
is exact on the numbers as read, so "exactly at the tolerance" holds for the doubles (PR-306, PR-335); a
numeric condition may carry `plus_minus`, a bound, a standard deviation, both, or one of unstated kind, and
`set_or_measured`, and a bound narrows a met condition while any other ± alone turns it into `unknown`
(`condition_uncertain`), never `not_met` (PR-108, PR-334); a run-time watch is narrowed by a stated bound, its
ends rounded inward, and a waived `condition_uncertain` gets the tolerance's interval (BC-030); a condition
another requires is checked like a required one, an implied token included (`provenance.md` section 6.1,
"Required with"; PR-311); `test_method` gains `hysteresigraph` and is required on remanence and saturation
magnetisation, `specimen_shape` staying required beside it (PR-305, PR-311, PR-315); a test method that probes
a length below the specimen's enters only with a condition stating that length. The forms: `want: bounds`
returns the interval's basis, and bounds are in order (PR-022, PR-050); `want: components` returns the
composition's basis and sum rule, its element symbols come from a table, and a repeated component, a fraction
outside [0, 1] or an empty list is refused (PR-023, PR-051); evidence entries are withheld one by one, each
whole, every member but provenance, or not at all, an entry withheld in part being refused, a partly withheld
list giving `unknown` (`entries_withheld`) and a wholly withheld one `withheld`, while an entry's members may
hold any other status object; an empty evidence list, an entry missing a member and a registered condition
under evidence are refused (PR-038, PR-052). Acceptances: a read takes only `pick`, `overlay`,
`extrapolation`, `nominal` and `implied_condition`, any other kind being `request_incomplete`; each is checked
at step 0 whatever field it names, that field registered, and applies only to its own; an implied condition
names a token fact and one of its tokens, and supplies values of a record condition's shapes without `basis`,
`plus_minus` or `set_or_measured`, and never a status object; two nominals naming one field, and two implied
conditions that apply and disagree, whether or not the record states that condition, are `request_incomplete`,
which ends the read even where they disagree in one alternative; an implied condition fills only an unstated
or absent condition, which is then checked, its unit checked like an operating condition's; a nominal inside
or on an interval's bounds supplies the value, one outside them gives `nominal_invalid`, and `assumption`
holds no `basis` (PR-302, PR-316, PR-318, PR-320, PR-330, PR-338). Statistics: each relative or expanded
uncertainty carries its own `represents`, `basis`, `distribution` (`normal` or `student_t`, by scale),
`coverage_factor` or `coverage_probability`, and `dof`, and `reported_uncertainty` leaves the block's `basis`;
`population_level`, `n_sources` and `precision_conditions` are present exactly where `represents` calls for
them; `student_t` and `beta` are registered distribution tokens; a record check lists, without failing, a
coverage factor and probability that disagree (`uncertainty.md` section 1; PR-153, PR-155, PR-156, PR-158,
RC-051, RC-162). Provenance and vocabulary: the specimen facts `supply_form` and `lot`, with one record per
grade or product and measurements on particular lots as alternatives naming their `lot`; a record fact holding
any status object differs from a target's fact (BC-012); `use` gains `used_in_selection`, never a witness
(RC-077); a database source names its release and entry (RC-200); the search record gains `weighting` and
`inputs` (RC-201); and schema 0.1.0 has no origin for a value predicted by a model. Specified, with suites
optional until their minor version (`README.md`): `params` per uncertainty structure, check points without a
vector, and the label `mean_of_specimen_fits` (PR-333, FE-014, RC-184); the space of a `multivariate_normal`
and `covariance_space` (RC-059, RC-083); named admissibility constraints (FE-013, RC-180 to RC-183); ensemble
levels and groups, with members that are fits to distinct units (RC-160, SA-016, SA-017); ensemble members and
interval corners listed, not flagged (RC-057, SA-019); nominal vectors (BC-042, SA-020); the sampling
contract, with the `transform_draws` operation and exact regions (SA-015, SA-018, SA-021 to SA-025); the
declaration's `sampling` (BC-044, BC-046), `population_level` (BC-043) and `precision` (BC-047); and the table
evaluation suite's tolerance per precision (TE-012). Record checks gain a listing that never fails
(`README.md`, "Case files"), and case ranges RC-160 to RC-179 (`uncertainty.md`), RC-180 to RC-199
(`model_families.md`) and RC-200 to RC-219 (`provenance.md`).

Settled after two checks of this text, one for names a slip could swap and one for reads that give `met` where
doubt remains. Names (maintainer, 2026-10-14): a population level's `unit` is `level` (`uncertainty.md`
sections 1 and 3, `declarations.md` section 1; PR-156, SA-016, BC-043), a `marginals` structure's `statistics`
is `parameter_statistics` (FE-042), the read result's `values` is `alternative_values` (PR-013), and a
digitised curve's or figure's `digitiser` is `digitisation` (FD-003, RC-029); an overlay scope's `consumer` is
compared with the declaring consumer's `name`, its version not compared, and a fill-in's scope names its user
there (BC-023); a chain's records are pinned material references (BC-026); `reported_sd` never stands beside
`represents: estimate` (RC-052); and where a member the reader does not know is ignored, one that is one slip
from a member named at its place (a character inserted, deleted or substituted, two adjacent ones swapped, a
plural or singular, an underscore added or removed) is refused, `form_invalid` in a record and
`request_incomplete` in a request, the names valid at one place being kept more than one slip apart
(`record_format.md` section 10; PR-005, PR-008, PR-030, PR-108, PR-109, PR-330). The read: an overlay whose
`purpose` is none of the four is `unknown_token`, and one of another purpose than `fill_in` that replaces a
withheld value is `withheld` (PR-042); `alternatives` is a list of at least one value field and stands alone
(PR-044); a fill-in whose document, or whose base's, does not state a string identifier and version gives
`fill_in_version_mismatch` (PR-107); an interval left beside other alternatives counts as a form `want: value`
can give where a nominal applies, so the read gives `no_pick` (PR-338); a requirement holding `label`,
`represents` or `population_level` is `request_incomplete` (PR-330); an acceptance applies only at the record
or region it names, never at an interval or with no location (PR-316); step 11's `request_incomplete` ends the
read as step 10's does (PR-308); a status object whose `status` or `reason` is not a string, and a `unit` on a
token condition, are refused (PR-110, PR-037); and what a pick naming no stored alternative gives is not yet
specified, but it is never another alternative. The build: a nominal covers `want_mismatch` only on a result
whose `assumption` names it (BC-020); a fact the target names that the record lacks is a difference (BC-012);
a `fit` or `scene_override` scope without a model or configuration hash differs (BC-023); and an interval's
acceptances reach the read of its record. `read_side_contract.md` section 4 names the step or procedure that
gives each reason.

Settled for the schema files (maintainer, 2026-10-14): until a schema version is released, its files under
`schema/<MAJOR.MINOR>/` may change; once released they never change, and a later minor version gets a
directory of its own; a reader validates against the schema files shipped with it and never fetches a schema
by its `$id` (`README.md`, "Versions and stability").

Settled with S2's conformance cases (maintainer, 2026-10-15), six points the cases raised: two implied
conditions that apply and disagree are checked first at step 10, and where they do, neither value fills the
condition, no condition is checked and the read ends, its result holding no `conditions` (PR-316);
`conditions` is present only once step 10 has run to its end, so not after a step-7 `want_mismatch` over
alternatives (PR-013); a review holding a known `result` is returned as found, as `provenance.md` section 2
item 6 already said, and `read_side_contract.md` section 2 now says so too (PR-109); a unit held as a status
object, the evidence field's included, is returned as stored, its `reason` with it (PR-010); an evidence entry
is returned with its `provenance` whole (PR-038); and which of an alternative's own reasons a `no_pick` result
reports is not yet specified.

A seventh point (maintainer, 2026-10-15): a review returned as found and an evidence entry's `provenance`
returned whole hold the members `read_side_contract.md` section 2 item 5 defines, so a member the reader does
not know is left out there too (PR-337).

Settled with S2a-1's review (maintainer, 2026-10-15): the specimen fact `disease_and_treatment_state` holds
`text`, naming the disease or the treatment, exactly when its `token` is `diseased` or `treated`, and none
under `normal`, which has nothing to name (`provenance.md` section 6.2; RC-039).

Proposed with S2a-2's review as a default and approved (maintainer, 2026-10-15): a specimen fact's `unit` is
compared at step 9, as every other unit is, with the unit its row fixes, wherever step 8 checks the fact, so
that another unit, or a status object with any token, gives `unit_mismatch`; step 8 checks only that it is a
string or a status object (`read_side_contract.md` section 3, step 9; PR-037). With it, the writer schema binds
such a unit to the one the row fixes, a status object refused, so that no record that step 9 refuses is
written: a fact whose unit the source does not give is written as a status object in place of the fact
(maintainer, 2026-10-15). Made explicit with the same review, and approved with it: `mimics`, whose row fixes
its `basis` to `stated`, takes no `inferred_from` (`provenance.md` section 6.2; RC-039).

Aligned with S2a-3's review (2026-10-16): step 8's list names a `derivation` for origin `derived` alone, as
`provenance.md` sections 2 and 5 already did; the reader schema's value-field `$defs` check it so, and leave a
derivation beside another origin unread, as a read does.

Proposed with S2a-3's review (maintainer, 2026-10-16): two values implied for one condition differ unless they
are of one shape, a value, a range or a token, and hold the same token or the same numbers bit for bit, so `0`
and `-0` differ, as a value and the range `[v, v]` already did (S2a-3's reading, which the review agreed
with); which of two that agree fills the condition then never depends on the order of the acceptances, and the
read fails closed where they differ (`read_side_contract.md` section 1).

Written with S2a-3's review (2026-10-16): `provenance.md` section 6.2 item 1 states the writer's rule for a
specimen fact's unit that the maintainer's ruling of 2026-10-15 set and the writer schema already applied: a
fact whose row fixes its unit holds that unit, and one whose unit the source does not give is written as a
status object in place of the fact (RC-039). Read alone, `record_format.md` section 4.2 (step 8 takes any
string or status object there) could have led a writer to `"min"`.

Names settled with the name-overlap check, before 0.1.0 (maintainer, 2026-10-15), so that a name keeps one
meaning wherever no safeguard keeps two apart: a scene cylinder's `axis` is `direction`, as a layered path's
is (`geometry.md` section 3.1; SC-006, RC-092); a family conversion's `from` and `to` are `from_measure` and
`to_measure` (RC-068), and an admissibility constraint's `kind` is `rule` (RC-180), in a family manifest
(`model_families.md` section 3); a declared model's `parameters` is `consumer_parameters` (`declarations.md`
sections 1 and 9; BC-034); a declared distribution's and a marginal's `parameters` are
`distribution_parameters` (`declarations.md` section 4.3, `uncertainty.md` section 2; BC-021, SA-007); a
witness datum's `reference_data` is `reference_data_name` (`model_families.md` section 6; FE-006); and a
`multivariate_normal`'s `space`, a space per parameter, is `parameter_spaces`, as is a fit's
`covariance_space.space` (`uncertainty.md` section 2, `fits_and_reference_data.md` section 2; RC-055, RC-059,
RC-083). A table's and a power law's `axis`, a chain's `from` and `to`, a family's `kind`, a family manifest's
`parameters`, the reference-data form's `reference_data`, a declared distribution's `space` and both meanings
of `ranges` keep their names.

Settled with S3's design, tables and extrapolations (maintainer, 2026-10-15, as recommended; for `points`, the
refusal stays). Three points most of all: a 0.1.0 reader refuses a table that holds `points`; `source_range`
narrows the readable range; and no extrapolation crosses a declared edge. How a table alternative is set
aside, which the clauses below on PR-044 and PR-013 state, is settled by S4's decision 1 (maintainer,
2026-10-15), and written in S4's entry at the end of this file. A table's `y` holds one number per `x`,
`edges` is required, each edge lies strictly inside `[x[0], x[-1]]` and is listed once, and numbers, an
operating value's included, are compared by value; a table's axis condition holds `not_applicable`; an axis
the reader does not know, or a token condition's name, is `unknown_token`, and so is a `scheme` the reader
does not know, not `form_invalid` (PR-322, PR-032); step 8 checks every member of a table that the reader's
version defines, so a table returned as stored holds only checked members (PR-322), and checks a form's member
only where the field's row allows the form, so a form it does not allow, a composition basis included, gives
`form_not_registered` and no reason of its member (maintainer, 2026-10-15; PR-036); `source_range` never
extends the readable range and narrows it where it is narrower, for the read, an evaluator's `in_range` and
the form-range watch, and one that is not two ordered numbers sharing with `[x[0], x[-1]]` a value that is no
edge is `form_invalid` (PR-019, TE-003, BC-031); the axis entry is `met` exactly when the operating value lies
in the readable range off every edge, step 11, not step 10, gives its reason, and it never sets an alternative
aside (PR-312, PR-044); a table alternative left outside its readable range, at an edge or over a range of its
axis appears under `no_pick` with its table as stored, no extrapolation applied (PR-013); a read over a range
of the axis gives `want_mismatch` alone (PR-321); a read returns the table's statistics block, and does not
refuse a number in its `mean`, `min` or `max`, or a token in its `central` (PR-157); a power law read with its
range unstated has its axis entry `unknown` (PR-021); a trainable field's `at_edge` still refuses (BC-029); an
extrapolation covers `outside_range` only under `want: value`, after which the read goes on to steps 12 and
13, and the build counts it only on a result whose `assumption` names it, so that a table read under `want:
bounds` outside its range is refused (PR-307, BC-019); two extrapolations naming one field are
`request_incomplete`, as is an empty `law` (PR-330); a read exactly at an edge is refused wherever the edge
lies, outside the readable range included, `outside_range` standing beside `at_edge` there (PR-018); no
extrapolation is applied across a declared edge: where an edge lies between the operating value and the
readable range's nearest end, or on that end, the read gives `outside_range` and no value, and an evaluator
refuses as at the edge (PR-307, TE-010); a 0.1.0 reader refuses a table with a `points` member, whatever it
holds, with the new reason `points_unsupported` (PR-157); a status object that breaks its shape refuses its
field as `form_invalid` alone, its token giving no reason of its own, so one holding `withheld` beside a
table's members is no withheld value (PR-110); the record checks flag a table that breaks its structural
rules, `source_range`'s included (RC-008); the table evaluation cases take the `evaluate` operation, a
tolerance per precision, a refusal at an edge that returns no number, absent or NaN, and stops the run, and
the inside derivative at every end of the readable range, none where it is one point (TE-007, TE-010, TE-012),
and they fail an evaluator that reports a refusal where none is due and compare an expected zero derivative
exactly, either sign of zero passing (TE-002, TE-003); and outside the readable range an evaluator returns the
value at its nearest end, from inside, with a zero derivative, or no number, so clamping is a constant
extrapolation only at the readable range's ends (TE-003).

Per-knot statistics (maintainer, 2026-10-15, after a spike): deferred to 0.2, with the acoustic and
radiological sections that need them. The schema leaves them open. The text that does so is proposed and
awaits the maintainer's review. `points` is a reserved member name in a table. Its shape and its reading come
with its first consumer. A 0.1.0 writer writes none, and the closed writer schema refuses it (RC-003). A 0.1.0
reader refuses a table that holds `points`, as before (`points_unsupported`, PR-157). With no shape left to
break, that is the only reason, whatever `points` holds. `null` there also gives `form_invalid` (PR-049). For
the slip rule, `points` counts as a member named at a table's place, so `point` is still refused (PR-030). The
members named at one place, refused ones included, are kept more than one slip apart, and a later minor
version adds no member one slip from one of them (`record_format.md` section 10). A table's block applies to
every value the table gives. The text no longer says that a knot's own block replaces it (`record_format.md`
sections 5 and 6, `uncertainty.md` section 1 rule 2). Where the source's spread varies along the axis, a
writer SHOULD state the largest in the table's terms in the table's single block, and SHOULD say in the
record's `card` that it was derived so. The rule does not apply to a population spread on a `loglog` table,
which 0.1.0 cannot state relative to its value (`uncertainty.md` section 1 rule 2; maintainer, 2026-10-15).
From 1.0.0, an older reader ignores a member it does not know. So a later minor version adds a member that
changes how existing members are read only under a name reserved in advance, which every earlier reader of the
same major version refuses, or with a new token in an enumerated member such a reader checks (maintainer,
2026-10-15). The later version requires that name or token wherever the member appears. Any other such member
waits for a new major schema version, not a new record version (`record_format.md` section 10).

Settled for 1.0.0 (maintainer, 2026-10-15, as recommended). From 1.0.0, a re-issue that makes a field
unreadable to a reader of an earlier minor schema version changes the record's `version` major, even where no
value changes, as when a spread is re-stated under a reserved name (`record_format.md` section 8 item 3). A
power law's uncertainty structure sits beside its statistics block, as the `power_law` object's member
`uncertainty`, not in the block as `structure` (`uncertainty.md` sections 1 and 2). No 0.1.0 field takes a
power law, so no read changes. A structure changes how `a` and `b` are read, so the name `uncertainty` on a
power law is reserved before 1.0.0 (`DOCUMENTATION_ARCHITECTURE.md` section 7.2).

Settled for alternatives, picks, overlays and fill-ins (maintainer, 2026-10-15), S4's twelve decisions. An
independent check of the text (1 High, 10 Medium, 12 Low and 7 Info findings) led to its present wording. The
maintainer ruled on four points it raised, and approved the six defaults written after it (2026-10-15), each
marked below.

Without a pick, a reader reads each alternative alone, and the outcome does not depend on the order of
reading. Each alternative is set aside, stays, or refuses the field (PR-044). An alternative is set aside
where its conditions, the form's own axis entry aside, give `not_met`. It is also set aside where its read
lies outside its form's range, not exactly at a declared edge, and no extrapolation the request carries would
cover it. This holds for any form with a range, not for tables only (maintainer, 2026-10-15). These rules
settle the S3 entry's clauses on PR-044 and PR-013, replacing the one under which a table outside its readable
range or at an edge stayed. An alternative an extrapolation would cover stays, and is read on through steps 12
and 13. One whose form `want` cannot give stays too, a table read over an operating range of its axis included
(PR-013). Any other `not_met` in an alternative's read refuses the field. So does a table read exactly at a
declared edge, wherever the edge lies. So does a fault of the request: an alternative that reaches step 11
with no operating value for its axis refuses the field, rather than ending the read (maintainer, 2026-10-15;
PR-044, PR-308, PR-316).

The result is the first outcome that applies, a refusal first (PR-044). A refused field, or one whose
alternatives are all set aside, reports every alternative's reasons, the `not_met` ones that wait in an
alternative that stays included (maintainer, 2026-10-15). Beside `no_pick` or `want_mismatch`, each remaining
alternative's `unknown` reasons stand, and its `not_met` reasons wait for a pick (maintainer, 2026-10-15;
PR-013). This settles the S2 entry's open point on an alternative's own reasons beside `no_pick`. Where every
alternative that stays is a table read over an operating range, the read gives `want_mismatch`, not `no_pick`
(PR-013). A result that rests on no single alternative holds no value, `assumption` or `conditions` (PR-336).
`alternatives` is a non-empty list of objects, none holding `alternatives` of its own (maintainer, 2026-10-15;
PR-044). A reason gains the member `alternative`, the stored index of the alternative it was found reading. A
reason is identified by code, condition and alternative, and cases compare the three (`README.md`, "Case
files"; PR-331).

A pick reads only its alternative. A pick past the last stored alternative, or on a field holding no
alternatives, gives the new reason `pick_invalid`, which nothing accepts (PR-304). This settles the S2 entry's
open point on a pick naming no stored alternative. A pick may be located at an overlay the read applies, and
then names one of that overlay's alternatives. One located at the base of a field an applied overlay replaces
gives `pick_invalid` (maintainer, 2026-10-15; PR-304). A pick's index is a whole number not below zero, `1.0`
being 1 and `-0` being 0. Two picks naming one field are `request_incomplete`, as two nominals are, whatever
their location (PR-330).

Every overlay an acceptance names for the read's field must apply; the build's selection of overlays by base
`id` comes with the build. An overlay that does not replace the read's field is refused (`absent`), and the
checks on `replaces` cover every key (PR-042, PR-046). One overlay named twice for one field is
`request_incomplete` (PR-041, PR-330). Two overlays named for the field read that both replace it conflict
(PR-041). A base differs in `id`, `version` or `content_hash`, compared as strings, an ill-formed base hash
included (PR-039). A record of a known type in the wrong role is refused as `unknown_type`: a target that is
not a `material`, however it is named, and an overlay acceptance naming a record that is not an `overlay`
(PR-007). A field an overlay replaces is refused by the base's envelope and body faults, not by the base's
section or the replaced field (PR-011). A fill-in over a base field holding alternatives gives
`fill_in_version_mismatch`. A fill-in's own alternatives are compared one by one, each mismatch with its index
(PR-107). A withheld value of the base, in any alternative, refuses an overlay that is not a fill-in, whether
or not its marker breaks its shape (maintainer, 2026-10-15; PR-042). An acceptance located at an `interval` is
not applied in a plain read even where it also names the read's `record`, and a pick is no exception: its
`region` and `interval` are its location, never members ignored (maintainer, 2026-10-15; PR-304, PR-307,
PR-316, PR-338). Only a pick may be located at an applied overlay: an extrapolation, a nominal or an implied
condition located there is not applied, and one located at the target's record applies to a field an overlay
replaces (maintainer, 2026-10-15; PR-307). A `no_pick` entry carries the labels step 12 gives its alternative
even where that alternative's read ended at step 11, so a table read over an operating range of its axis keeps
`user_extracted` and the field's `label` (maintainer, 2026-10-15; PR-013).

Settled with S3-te's review of the table evaluation suite. The `binary32` tolerances are capped per broken
evaluator (maintainer, 2026-10-17): each broken evaluator the suite's verification names misses at least one
of the files that should catch it by ten times that file's `binary32` tolerance (`README.md`, "Case files").
The TE suite's README lists each broken evaluator beside the files that should catch it. A broken evaluator
need not miss every file by that much: NumPy's `interp` outside the readable range misses TE-003 `narrowed` by
less (the TE suite's README). Outside a table's readable range, an evaluator's value and its derivative are
each judged alone (maintainer, 2026-10-17): each is the expected number, or absent or NaN. So a NaN value
beside a zero derivative passes (`read_side_contract.md` section 7 item 1). `in_range` is still compared there
(`read_side_contract.md` section 7 item 7; TE-002, TE-003). This settles the S3 entry's "or no number".

The cap on a file's `binary32` tolerance holds under each precision and side a broken evaluator claims
(maintainer, 2026-10-19): those words follow "by ten times that file's `binary32` tolerance" in `README.md`,
"Case files". The suite's README and the reference evaluator's tests already read the cap so, and it changes no
figure: for each of the 24 broken evaluators the best file is the same under each claim. The clause that a
difference no tolerance passes (in `in_range`, say, or a refusal) counts as beyond the cap, which the ruling of
2026-10-17 did not say, is ratified as written, and the 13 of the 35 table evaluation files named beside no
broken evaluator have no cap.

Settled with S2a-4's review (maintainer, 2026-10-18): an implied condition breaks its shape
(`request_incomplete`, with that `condition`) where `implies` gives a numeric condition a `token`, or a token
condition a `value`, `range` or `unit`, whatever that member holds, each being a member of the other kind of
condition's shape (`read_side_contract.md` section 1; PR-330). The text refused the first already, as a token
outside a numeric condition's row, and the second only through the shapes `declarations.md` section 4.1 names,
so S2a-3's reader ignored a `unit` beside a token; one sentence now says both, and the reader refuses both.

An interim rule, with S4a, step 7 over alternatives read with no pick and no overlay (maintainer, 2026-10-19):
under `no_pick`, the result's `unit` is the first remaining alternative's, in stored order, where the remaining
alternatives store it differently, and another alternative's `reason` is not returned (`read_side_contract.md`
section 2; PR-013). The maintainer has ruled that the rule holds until S3b-2, which replaces it with each
remaining alternative's `unit` in its `alternative_values` entry. Only a unit registered as a status object can
differ there, since step 9 compares it by its `status` token alone, and in 0.1.0 only
`biocompatibility.evidence` registers one. Stored order is fixed once a record is released (`record_format.md`
section 5), so the unit does not depend on the order of reading. An `alternative_values` entry still holds no
`unit` of its own.

Settled with a consumer's first reads of formulation values (maintainer, 2026-10-19): `test_method` gains
`reference_formulation`, the test method of a value evaluated from a reference formulation or an equation of
state (origin `evaluated_from_formulation`, `provenance.md` section 6.1 item 10). A consumer that names
`test_method` in its requirement accepts such a value by listing the token, while, with no acceptance, the
`test_method` entry of a value that states none is still `unknown` (`condition_unstated`), whatever its origin
(`read_side_contract.md` section 5). No read rule changes: the token is one more in the condition's list.
Clarified with it (maintainer, 2026-10-19): the Newtonian label on a value with no stated shear rate is no
evidence at any shear rate. A label its row allows changes no member of a read's result but `labels`, so with
no acceptance the value's `shear_rate` entry is `unknown` (`condition_unstated`), and treating the fluid as
Newtonian there is the consumer's own declaration, never the label's: an implied condition that supplies a
shear rate, or a declaration that covers the reason (`record_format.md` section 4.1; PR-104, PR-053, PR-316).
A label claims only over the stated `shear_rate` condition, as that section already said, and no rule widens
it.

Decided with the curation tools' first piece (maintainer, 2026-10-20): page-text documents and the place of a
quote in a copy (`page_text.md`). A checker reads only JSON, so it reads a copy's text from a page-text
document: the text of one copy as one named extraction gave it, identified by its RFC 8785 hash and never
published (RC-220, RC-221). A PDF's form holds each page's visible text with the ranges the extraction does
not vouch for (where two readings, compared glyph by glyph, disagree), the line feeds where reading order
jumps, the page's furniture, and its raised and lowered text; it names its readings, and one naming fewer than
two passes no quote. An XML file's form holds its string value and every element by its path, with a table
cell's columns where the extraction knows them. A quote's place in a copy, its spans and the hash of the
page-text document they count in, sits in `copy`, outside the content hash, since it holds for one copy and
one extraction, not for the document version; the locator is unchanged. Across a page break a place leaves out
only `White_Space` and furniture, a span may mark the value's characters, and a stamped copy's place never
ships (RC-222, RC-034). RC-032 compares a quote with its place in that page-text document alone, under every
reading of its line-end hyphens (a hyphen after a letter, never in XML), reads the value's numbers where the
place marks the value, fails a value marked in an XML table cell outside the locator's column, and reports
`not_checked` where the place is flagged, the readings are too few, or the located text is doubtful, crosses a
jump, or holds a code point unassigned or private-use in the checker's Unicode database (RC-032, RC-223 to
RC-226). A pass says that the quote is in the copy's text as the named extraction gave it; whether that text
is the copy's is not checked. The normalisation of `quote_sha256` gains a first step, removing invisible
format characters, and lists the 25 `White_Space` code points, which are not those of Python's `str.isspace`;
RC-032 compares a `quote` by the same normalised form (`provenance.md` section 4 item 4; RC-033).
`copy.sha256` is written as `sha256:` and 64 lowercase hexadecimal digits (RC-031). A page-text document's
schema version follows the version rule (`record_format.md` section 8), and its JSON the strict rules
(`record_format.md` section 1). No reader change: a read never checks `copy`. The writer schema's `copy` takes
the place, `page_text` and `spans`, present together or not at all, and `sha256`'s form; `page_text.json`
gives a page-text document's shape, its rules across members being RC-220's. The conformance inputs and the
example record that wrote a copy's hash as bare digits now write the prefix: eleven plain-read fill-ins and
`examples/records/human_plasma.json`. `copy` is outside the content hash, so no hash or pin moves. Two inputs
of the hash suite keep their bare digits: they are hash vectors, which the writer schema does not judge. The
record-check cases come with it, 197 case files of RC-031, RC-032, RC-033's `quote_sha256` vectors and RC-220
to RC-226, waiting for the curation track's quote attach-and-verify, whose core half runs them with the record
checks. The case-file format gains what they need (`README.md`, "Case files"): a record-check case's page-text
documents, `inputs.page_texts`; `compare.rules_compared`, the rules whose items a case compares; the
comparison of a quote with its place reported under RC-032 at the quote's evidence, a failure as a finding and
`not_checked` as a listing; and the operation `quote_sha256`, which gives a text's quote hash. `case.json`
takes them.

Settled with S2b-2's review (maintainer, 2026-10-19): step 8 checks an evidence entry's `provenance` as it
checks a field's (`provenance.md` section 2 item 6: its `origin`; its `source`, present for
`measured_by_source` and an object with a string `key` wherever present; its `derivation` for `derived`; its
`review` read as every review is), and returns it whole, the members that check leaves unchecked as found
(`record_format.md` section 4.3 item 2; PR-052). The text returned the provenance whole but did not say which
of its members a read checks; S2b-2's reader checked them as a field's, and one sentence now says so. So a
report's provenance whose origin the reader does not know refuses the field (`unknown_token`), and one whose
`extraction` is a number is returned as stored. With the maintainer's ruling of 2026-10-20 on the reviews
inside it, the sentence also says that each provenance those members hold, at any depth (one that
`per_parameter` maps a parameter to, say), returns its `review` as `provenance.md` section 2 item 6 reads
every review: one of a status token a review does not take, or absent, is returned as
`{"status": "not_checked"}` (PR-052). S2b-2's reader read every review so; the text said so of the
provenance's own review alone.

Settled with S2b-2's review (maintainer, 2026-10-19): a record's numeric condition holding `token`, or token
condition holding `value`, `range`, `plus_minus` or `set_or_measured`, breaks its shape (`form_invalid`),
whatever that member holds, each being a member of the other kind of condition's shape, and so does a member
one slip from one (`provenance.md` section 6.1 item 1; PR-045, PR-030, PR-301). This is the record half of the
request side's sentence of 2026-10-18 (`read_side_contract.md` section 1), less a `unit` on a token condition,
which keeps step 9's `unit_mismatch`. The text gave each kind its shape but did not say whether the other
kind's member is one the reader knows at that place; S2a-2's reader ignored it as unknown, and the reader
refuses it now.

Settled with S2b-2's review (maintainer, 2026-10-19): a member one slip from `alternatives` beside a value
field's members, `alternative` beside a constant's say, refuses the field (`form_invalid`), as a slip of any
member named at a field's place does: `record_format.md` section 5 names both shapes at that place, a value
field's members and an `alternatives` object, and `record_format.md` section 10 item 5 refuses a slip of a
member named there (PR-030). The text decides it, and the reader has read it so since S2a-2; no sentence
changes.

Confirmed with S2b-2's review (maintainer, 2026-10-19), decided with S2a-4's review (approved 2026-10-18): a
member one slip from a requirement's `field`, or from a requirement condition's `reason` or `consequence`,
refuses the request (`request_incomplete`), as `read_side_contract.md` section 1 refuses a member one slip
from one `declarations.md` names at that place, refused ones included (PR-330). `declarations.md` names
`field` in a requirement and `reason` and `consequence` in each of its conditions, and a read ignores the
three, so a misspelt one is refused, not ignored. The text decides it; no sentence changes.

Settled with S2b-2's review (maintainer, 2026-10-19): step 0 judges a nominal by the row of the field it
names. A nominal takes `params` in place of `value` only where that row allows the form `parameter_set`, so
one holding `params` and no `value`, for a field whose row allows none, breaks its shape
(`request_incomplete`; `read_side_contract.md` section 1; PR-330). `declarations.md` section 4.1 gives
`params` "for a parameter set" without saying whether step 0 reads the field's row to know it; S2b-2's reader
required a `value` in every nominal, which is that reading while no 0.1.0 row allows a parameter set, and one
sentence now says so.

Settled for the result's shape, with S3b-2 (maintainer, 2026-10-19): under `no_pick` each `alternative_values`
entry holds its own alternative's `unit`, as stored, and the result holds no `unit` of its own
(`read_side_contract.md` section 2; PR-013). This replaces the interim rule of S4a above, under which the
result held the first remaining alternative's unit and another alternative's `reason` was not returned: now no
alternative's `reason` is lost, and `unit` is present exactly when `value` is. With it, a result whose value
is read from a table holds that table as stored, in a member `table` of the same meaning as a value field's,
present exactly when `value` is and is read from a table: the field's, the one alternative left or the one a
pick names, under an extrapolation too (`read_side_contract.md` section 2; PR-318, PR-336). A consumer that
evaluates the table in its own code (`read_side_contract.md` section 7) so takes the table the read checked,
through the overlays, the pick and the alternatives set aside that the read applied, with the readable range's
two ends, where before it would have read the record's JSON again on its own. `record_format.md` section 5
item 5 now lists each `no_pick` entry's own `unit` and `labels` beside its conditions, specimen, statistics and
provenance, as `read_side_contract.md` section 2 gives them.

Settled with S3c, the extrapolation (maintainer, 2026-10-19, as recommended): a `consumer_law` extrapolation is
computed from the end value a read under that extrapolation returns, at the readable range's nearest end, taken
from inside it, or from the one an evaluator returns there, where it returns one (`declarations.md` section 4.1
item 3; PR-307, TE-003). Before, item 3 named the evaluator's alone, which `read_side_contract.md` section 7
item 1 lets be absent or NaN outside the range, so a consumer whose evaluator returns none had no end value to
start from. A request's extrapolation now has its shape in `read_request.json`, as `declarations.md` section
4.1 gives it (`method`, one of its two tokens; `law`, text of at least one character), and a result's
`assumption` under it holds exactly `acceptance`, `method` and `law` in `read_result.json` (PR-330, PR-307).

Settled with the build check's design (maintainer, 2026-10-20 on the order; 2026-10-21, as recommended):
declarations over records come before scenes, and their scene arms after them. A declaration is checked on its
own before any read, against a table of its members, each required or optional: a missing or unknown member, a
slip, a token a member does not take, a name given twice, a requirement or trainable entry for a field not
read, or an empty reason or basis refuses it, each refusal naming its rule's case and a JSON pointer (BC-048).
A build refuses what it cannot check: scene declarations without the scene suite, engine models without USD
read, and sampling without the sampling suite, an accepted refusal standing first where one applies (BC-051).
The build gives one report, with `not_accepted` on each result and the acceptances no result used (BC-009,
BC-053), and defines what a read applied. A field with no requirement is read for nothing (BC-003). A
requirement may ask for a reviewed value, `review: "reviewed"`, and a value not reviewed gives `unknown` with
`not_reviewed`, which a waiver covers (BC-049). A request's requirement holding `review` is refused (PR-330).
A label records its basis in `label_basis`, whose shape no read checks and which no read returns; a waiver
that names a label needs a requirement that names the label and asks for review, and covers only where the
label is stated or the value reviewed (BC-050). The writer schema names `label_basis` at a field's place,
optional and closed; the reader names it too, and checks only its name: a member one slip from it
(`label_basi`) now refuses the field (`form_invalid`, PR-030), and so does `label_basis` beside `alternatives`
(`record_format.md` section 5), where the reader before ignored both. A read takes a `trainable` acceptance,
which the build makes from the declaration's `trainable` entries, and goes on past the condition and range
reasons with the value as the initial value, and ends with no value at or across a declared edge; the result
names its entry (PR-339, BC-029). Only accepted results are watched; a result accepted while not met watches
with its operating value; a waived unstated condition gets a `declared` watch (BC-030, BC-052), and a
form-range watch stops at a declared edge (BC-031). The build-check case shape is added, and
`declarations.md`'s case range is BC-001 to BC-099.

Settled with S7-cases-1's review (maintainer, 2026-10-23, as recommended): three sentences of
`declarations.md` section 1, each a reading the build check's first case files had to choose. Item 12's
precedence is per member: where item 7 refuses a model with `engine`, its `engine` gives no refusal under item
12 and its other members still do, and where item 8 or the `population_level` rule refuses the declaration
over a requirement, that requirement gives none and a `sampling` beside it still does. So a model with
`engine` checked over a domain, by a build that claims neither the scene suite nor USD read and is passed no
crosswalk, gives BC-040 and the domain's BC-051, and a population requirement without `population_level`
beside a valid `sampling` gives BC-043 and the `sampling`'s BC-051. Before, the sentence did not say whether
item 7 spared a model's `engine` or the whole model, and BC-051's Cases row gave the rules that come first
"their refusal alone" over the whole declaration; the row now says "for that member" (BC-051). Items 3 and 4's
"without" means absent: an empty `reason` or `basis` breaks its row's Holds and is BC-048's alone, at that
member; before, items 3 and 4 could be read as naming it too, which by the precedence would have given it
BC-004 or BC-005 (BC-048). And the pointer names the most specific member at fault: for a value that breaks
its row's Holds, that member, such as a requirement's `field` not in `reads` or a `trainable` entry's `record`
its model is not checked over; for what item 12 refuses, the member that needs the suite, or the acceptance or
`trainable` entry itself, such as a `distribution` acceptance (BC-048, BC-051).

Settled after S7-cases-1 (maintainer, 2026-10-23, as recommended): three sentences, each a reading the build
check's case files would otherwise have had to choose. In `read_side_contract.md` section 2, an
`alternative_values` entry whose alternative is kept outside its form's range, or is a table read over an
operating range of its axis, holds its `unit`, `specimen`, `statistics` and `provenance` as
`record_format.md` section 5 gives them, even where its read ended at step 11; before, the row gave the
entry's other members "for a read of that alternative alone", and such a read, ending `not_met` at step 11
with no value, holds none of the four, while `record_format.md` lists each entry with them (PR-013). And an
alternative's index, an entry's and a reason's `alternative`, counts from 0 in stored order; before, the row
said only "its index among the stored alternatives", where a pick's `index` is 0-based by `declarations.md`
section 4.1 (PR-013, PR-331). In `declarations.md` section 1, a waiver whose `code` is no reason names no
condition, so a `condition` beside it is refused, not required, and such a waiver without one gives one
refusal, at its `code`; before, a `code` one slip from a condition reason could be read as still naming the
condition, which would have added a refusal at the waiver for its missing `condition` (BC-048).

Settled with S7-cases-2's review (maintainer, 2026-10-23, as recommended): which codes name a condition, for a
waiver's `condition` (`declarations.md` section 1, an acceptance's own members). A code names a condition where
its reasons always carry one: the six `condition_*` codes, `outside_range`, `at_edge` and `range_unstated`
(`read_side_contract.md` section 2 item 2). A waiver of one of them needs its `condition`, and a waiver of any
other code is refused if it holds one, `unit_mismatch`, `request_incomplete`, `request_unit_mismatch` and
`want_mismatch` among them, whose reasons carry a condition only where they concern one. Before, "where the code
names one" did not say which codes, and could be read as the `condition_*` codes alone, or as every code whose
reasons can carry a condition (BC-048).

Settled with the same review (maintainer, 2026-10-23, as recommended): a build result keeps every member the
read returned, including `value`, where the read returned one (`declarations.md` section 2 item 8). So where
the build's own `label_mismatch` makes the result of an `unknown` read `not_met`, the result still carries the
read's value. Before, `read_side_contract.md` section 2 item 3, which gives a `not_met` result no value, could be
read as applying to the build's result as well as to the read's (BC-027).

Settled with the same review (maintainer, 2026-10-23, as recommended): the build's own read request holds the
requirement's `want` and `conditions`, and the declared operating conditions (`declarations.md` section 2 item
7). Before, item 7 said only which acceptances a read is given; a build that copied the whole requirement into
its request would have had every read of a requirement holding `label` or `review` refused, since
`read_side_contract.md` section 1 refuses a request whose requirement holds either (BC-009).

Settled with S7a-1a's open points (maintainer, 2026-10-24, as recommended): `condition_unknown_name` is never
accepted, and a waiver whose `code` is `condition_unknown_name` is refused at build, at its `code`
(`declarations.md` sections 4.2 and 1). A condition name the reader does not know is a typo or a version
mismatch, which the reader's upgrade remedies, not a waiver. Before, `declarations.md` section 4.2's first row
listed it among the reasons a waiver naming that condition and code covers, but such a waiver names its
condition, which takes only a name the build's version registers (`declarations.md` section 1), so no
declaration could name the one the reader did not know, and one naming a registered condition was taken and
covered nothing (BC-038, BC-048).

Settled with the same open points (maintainer, 2026-10-24, as recommended): `basis` is a member of an
extrapolation, a nominal and a distribution alone (`declarations.md` section 1, the table of the declaration's
shape). Every other kind of acceptance holding one departs from its shape, as a member the table does not name
there; a `basis` inside an implied condition's `implies` is still ignored. Before, the table named `basis` at
the acceptance's place, required "for `extrapolation`, `nominal` and `distribution`", which could be read as
naming it on every kind, and the declaration's schema took it on all nine (BC-048).

Settled with the same open points (maintainer, 2026-10-24, as recommended): a requirement holding
`population_level` beside a `represents` that is not `population`, or beside none, is refused at build, by the
`population_level` rule (`declarations.md` section 1, the members table and the table of the declaration's
shape), at its `population_level`, in every build this version makes, except where the build claims the
sampling suite, where it fails closed (a claimed suite this version does not build raises, even where a refusal
is certain; maintainer, 2026-10-24). Before, that rule refused only a population requirement without one, and a
build claiming the sampling suite took a `population_level` beside another `represents` or beside none
(BC-043).

Settled with the same open points (maintainer, 2026-10-24, as recommended): a watch holds `unit` with an
`interval` only, a token condition having none (`declarations.md` section 8 item 1). Before, the item listed
`unit` among every watch's members, where an accept-list watch's condition has no unit, and the report's
schema, which required `unit` with an `interval`, took one beside `accept` too; it now refuses it there
(BC-030).

Settled with the same open points (maintainer, 2026-10-24, as recommended): the report of a declaration
refused on its own holds the declaration as given where its text is JSON, and its `consumer` where the
declaration declares one (`declarations.md` section 2). Before, `declarations.md` section 2 listed both among
the report's members with no word on a text that is not JSON, of which neither can be given, and the report's
schema let a refused report omit both. The schema now requires the declaration unless the report's one refusal
is BC-048 at the empty pointer, which it cannot tell from a text that is not JSON, as `declarations.md` section 2
says.

Settled with S7a-1b's review (maintainer, 2026-10-24, as recommended): a model that item 7 refuses gives one
refusal, at its `engine`, whichever of the item's rules it breaks (`declarations.md` section 1, the refusal
paragraph). Before, the paragraph's most specific member would have placed an engine value without its `basis`
at that value and another `want` at the requirement's `want`, so one engine model could give several refusals
(BC-040).

Settled with S7a-1b's second review (2026-10-25, a default the maintainer confirmed that day): a rule that
judges one member against another stands aside where the other is itself at fault, so that one fault is one
member at fault (`declarations.md` section 1, the refusal paragraph). A `population_level` beside a `represents`
that is no token is not refused by the `population_level` rule, a requirement for a field is not judged against
a `reads` at fault (an empty `reads` is one: BC-048 wants an entry), and a waiver of `condition_unknown_name`
naming no `condition` is refused once, at its `code`, not again at the waiver for the `condition` that a
refused code is not judged to need; an acceptance with no kind, or one that is no kind, is refused at itself
(at the acceptance where the `acceptance` member is missing, at the member where it is no kind) and none of its
other members is judged, which depend on the kind; the rest of the declaration is still checked for its own
faults. An engine value without its `reason` or `basis` is likewise one
fault, which item 7 and the shape's required members both name: one refusal, BC-040 at the model's `engine`,
and none at the value. Before, the paragraph did not say, and a second implementation could read each of these
cases as a second refusal (BC-005, BC-040, BC-043, BC-048).

The maintainer's ruling of 2026-10-26, taken after a comparison of the declaration
check with the build's reference model: a rule that judges one member against another stands aside where the
other is itself at fault, with three exceptions (`declarations.md` section 1, the refusal paragraph). A member is
still held to what it must be whichever value the other holds: its JSON type (a distribution parameter's value
is a number; an accepted difference's `value` is an object, a status object judged as one, or `"any"`), a label
that no registered field has, and `params` where no registered field's row allows the form `parameter_set`. A
rule the text states for a member at fault still applies: a waiver whose `code` is no reason names no
`condition`. And an entry that is no well-formed name (a reference without string `id`, `version` and
`content_hash`, a `field` that is no string) is neither the same as nor different from another, and no rule
compares it, so it is never given twice and a `trainable` entry's record is compared with the listed ones by
reference. An acceptance that names no known kind keeps the rule above: none of its other members is judged.
One reading follows that no earlier text stated: a combination is refused for its sections only where every
entry is a registered field and all are of one section, so two fields of one section beside a third entry that
is no registered field are refused at that entry alone (the sections rule judges the entries against each
other). Before, the paragraph gave three examples of standing aside and did not say where the principle stops,
so two implementations could stop it at different places (BC-048).

A second ruling of 2026-10-26, taken with the same comparison: a
`trainable` entry at a `record` where its model is checked over a domain or a path, and one at a `region` or
an `interval` where it is checked over `records`, is at a location its model is not checked over
(`declarations.md` section 1, the shape's departures, and `declarations.md` section 2 item 2): BC-048 at the
location, beside item 12's refusal at the entry where the build does not claim the scene suite. Before, the
text did not say which location kinds a model checked over `records` or over a scene can have (BC-048).

A third ruling of 2026-10-26, on three readings the declaration check and the build's reference model already
shared: the refusal paragraph (`declarations.md` section 1) now says which rules do not stand aside where the
member they judge against is at fault. A requirement samples where it holds `represents`, whatever `represents`
holds (item 8), so a `represents` that is no token beside no `sampling` is refused for the missing `sampling`
(BC-044) and for the `represents` (BC-048). A waiver's `label` is refused unless its requirement holds
`review: "reviewed"` and names that label, whatever else the requirement's `label` and `review` hold (`declarations.md`
section 4.1 item 4), so a `review` that is no token beside a waiver's `label` is refused at the `review` (BC-048) and at
the `label` (BC-050). A `trainable` entry's location is judged against the one alternative `checked_over` names,
whatever that alternative holds: a `domain` or a `path` that is no string is still a scene, and a `records` list,
an empty one too, is still the list a record must be in; where `checked_over` names two alternatives or none,
or its `records` is no list, the location is judged against none. The paragraph's "That has three exceptions"
now reads "Standing aside has three exceptions", as the "That" could be read as the acceptance clause before it.
Before, the paragraph read literally would have had each of the three stand aside (BC-044, BC-050, BC-048).
