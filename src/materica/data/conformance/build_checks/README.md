# Build-check cases (BC)

The cases of a consumer's build check, which checks a declaration against records
(`docs/specification/declarations.md`; `docs/specification/README.md`, "Suites and case numbers"). A
build-check case holds for an implementation that claims build checks with plain read. The suite holds, so
far, two kinds of case.

The declaration checked on its own, which the build refuses before any read (S7a-1's):
- a tolerance or accept list without its reason (BC-004);
- an acceptance without its reason, or without the basis its kind needs (BC-005);
- an acceptance with no location where its kind needs one (BC-037);
- a declaration that departs from its shape: not JSON or not an object, a member missing, of another type,
  unknown or one slip from a named one, a token its member does not take, a name given twice, a requirement or
  `trainable` entry against `reads` and `checked_over`, an empty `reason` (BC-048);
- a waiver resting on a label whose requirement does not name that label with `review: "reviewed"` (BC-050);
- what a build refuses because it does not claim the scene suite, USD read or the sampling suite, with the
  rules that come before it (BC-051).

A declaration over records that passes its own check, and what the build gives after reading (S7a-2's):
- the operating conditions declared once, a value or a range (BC-001), and the records `checked_over` lists,
  none other, one listed and absent from the store included (BC-002);
- a field read with no requirement, for which nothing is read (BC-003);
- a status no declaration changes (BC-006);
- `accepted`, `accepted_by` with the indexes of the acceptances used, the ones a read applied included, and
  `not_accepted` (BC-009); the verdict, every result not accepted listed, each model's results judged by its
  own acceptances (BC-010);
- a waiver's reach: its record (equal in `id`, `version` and `content_hash`), condition, code and field,
  whatever the reason's `alternative`, and one that names no label (BC-016);
- an implied condition that fills an unstated condition and no other (BC-017); an extrapolation under
  `outside_range` (BC-019); a nominal on an interval (BC-020);
- `label_mismatch` against the label stored on the value read (BC-027); each result naming its model and
  record (BC-028); waivers of reasons no row of section 4.2 lets a waiver cover (BC-038);
- the `review` requirement and `not_reviewed`, never on a result that holds no `provenance` (BC-049);
  acceptances no result used, per model (BC-053).

S7a-1 builds the declaration's own check, and with it the runner's `check_build` executor, and S7a-2 the
results (`tests/spec_sync/case_steps.json` maps each file to `S7a-1` or `S7a-2`); both have run every file
here since S7a-2. `CASES.md`
beside this file gives one row per case file: what the arm tests, the text that decides it, and what the build
gives. Start there.

## Reading a case

A build-check case names its records in `inputs.records` and its declaration in `inputs.declaration`, and its
`request` is `{"operation": "check_build"}` (`docs/specification/README.md`, "Case files"). In this suite:

- `expected.refusals` lists the declaration's refusals, each `{"item", "pointer"}`: the case id of the rule
  broken and a JSON pointer (RFC 6901) into the declaration, `""` being the declaration itself. They are
  compared as a set; `detail` is never compared.
- A refusal case (S7a-1's) names `refusals`, `results`, `watches` and `unused` in `compare.members`, and
  `expected` holds `refusals` alone: a declaration refused on its own gives no results, no watches and nothing
  unused (`declarations.md` section 2), so a build that refuses and still reads fails every file.
- Three refusal files compare one rule's refusals alone (`compare.rules_compared`), where the text fixes
  another rule's refusal of the same declaration less exactly than the rule the arm tests:
  `BC-050.requirement_names_another_label` (the waiver's label is also not one its field registers, a fault
  the token rule names too), and `BC-051.engine_over_records` and `BC-051.engine_over_domain` (item 7 refuses
  the engine model, at pointers the text does not fix; the arms test that its `engine` then gives no refusal
  under item 12, and that a domain it is checked over still does).
- A result case (S7a-2's) names `refusals`, `results` and `unused`, and expects no refusal. `results` are
  compared as a set keyed by `model`, `record` and `field`, so a result the file does not name fails it; each
  compares the members `compare.result_members` names (`status`, `reasons`, `value`, `assumption`, `accepted`,
  `accepted_by` and `not_accepted`; BC-049's `provenance` too, which holds the review; BC-003's every member
  of a read too, each expected absent), numbers exactly, `accepted_by` as a set of indexes and `not_accepted`
  as a multiset of reasons. `unused` is a set of `{"model", "acceptance"}`. These files do not compare
  `watches`: the build emits a watch for an accepted result, and watches are S7a-4's.
- Claims: BC-051's files state the claims their answer rests on: `{"scene_documents": false}`,
  `{"usd_read": false}`, both, or `{"sampling": false}`; `BC-020.want_mismatch_at_step_0_nominal_unused`
  states `{"fits_and_reference_data": false}`, its `want` being that suite's.

## The fixtures

Every record here is a conformance fixture (`record_format.md` section 7 item 1): illustrative, stating
nothing about any material.

- **The records** are the plain-read suite's inputs of the same names, byte for byte, but for two:
  - `water_fixture.json`, `conformance/water_fixture` 1.0.0: the viscosity, a constant of 0.000692 Pa.s at
    310.15 K, its shear rate unstated, its Newtonian label stored with no `label_basis`, its review
    `not_checked`. Other copies of that id and version, each with its own hash but two: its review completed
    (`water_review_reviewed.json`) or holding a `result` the reader does not know
    (`water_review_unknown_result.json`), both with water's hash, since a review lies outside it; its label
    absent (`water_label_missing.json`) or the linear label (`water_linear_label_on_viscosity.json`); two
    constant alternatives (`water_two_constant_alternatives.json`); an in vivo specimen with the temperature
    stated, unstated or `not_checked` (`water_in_vivo.json`, `water_in_vivo_temperature_unstated.json`,
    `water_in_vivo_temperature_not_checked.json`), its shear rate stated over 10 to 1000 1/s.
  - `glycerol_fixture.json`, `conformance/glycerol_fixture` 1.0.0, a density stated at 293.15 K;
    `grade_density_bounds_specification_limits.json`, `conformance/polymer_grade_fixture` 1.0.0, a density
    interval of [1150, 1250] kg/m3; `density_table.json` and `density_edge_table.json`, density tables over
    temperature, the second with a declared edge at 273 K; `composition_components_partial.json`, an elemental
    composition.
  - written for this suite: `plasma_fixture.json`, `conformance/plasma_fixture` 1.0.0, the water fixture's
    shape with its own id and name and a viscosity of 0.0012 Pa.s, so that two records of different ids leave
    the same condition unstated; and `glycerol_review_reviewed.json`, the glycerol fixture with its review
    completed as a writer records one (who, their ORCID, the date, their independence, the checklist) and
    glycerol's hash, since a review lies outside it, so that a reviewed value is `met`.
- **The declarations**, one per file, named after the case and variant (`bc048_json_array.json`). A refusal
  case's is one base declaration with the arm's fault planted. The base: the consumer `conformance_consumer`
  1.0.0; operating conditions of 310.15 K and 50 to 500 1/s; one model, `drag` 1.0.0, checked over the water
  record, with an empty `target`, reading the viscosity, with one requirement (a temperature tolerance of 1 K, a
  shear rate tolerance of 0 1/s and a `test_method` accept list, each with its reason) and one acceptance, a
  waiver of the unstated shear rate at the water record. An acceptance an arm adds is valid but for the fault
  planted: an `overlay` and an `overlay_scope` name an overlay no case supplies, and an `engine` pins a
  crosswalk no case passes. A result case's declaration is valid, with an empty `target` and no `combinations`
  or `trainable`, which S7a-3 and S7a-4 build: the viscosity read under the same operating conditions with a
  requirement naming the Newtonian label, a temperature tolerance of 1 K and a shear rate tolerance of 0 1/s,
  or a density or a composition read under its own; and the acceptances each arm needs, none a `pick` or an
  `overlay`, which S7c builds. A model that reads a table states `"precision": "binary64"` (`declarations.md`
  section 1 item 10); no rule these files test reads it.

## What the cases cannot show

- **Watches**, which S7a-4's files compare, and a consumer's run against them.
- **Specimen differences and combinations**, which S7a-3's files compare: every target here is empty.
- **A label-resting waiver's coverage** (BC-050's six arms of a waiver naming a trusted or untrusted label),
  ruled to come after 0.1.0.dev4; one arm here uses such a waiver only as its control.
- **One acceptance used by two results.** Over records an acceptance is located at one record and names one
  field, so only an accepted difference, with no location or covering a section, reaches two results: S7a-3's.
- **A review added after a pin.** A review lies outside the content hash (`declarations.md` section 1 item
  11), so a pinned record's review can change while the pin holds; a case supplies one copy of a record, and
  BC-049's files supply copies of the water and glycerol fixtures, each with its record's hash and its own
  review, one per file.
- **One refusal given twice.** Refusals are compared as a set, so a build that reports a refusal twice, where
  "Two faults with one case and one pointer are one refusal", passes every file. The build's property tests
  hold that rule.
- **Seven faults of the build, beyond the declarations here.** S7a-2's property tests (HP43 to HP46) are to
  hold these over drawn declarations: `unused` naming every acceptance after the first model; one set of used
  acceptances shared by every model; a model's reason covered by another model's acceptance; `not_reviewed`
  given to a result that holds no `provenance`; `not_reviewed` making the status `unknown` over a read's
  `not_met`; an acceptance located at a record by its `id` alone; and a waiver that covers no reason carrying
  an `alternative`. Six of them each fail the arm written for it here (`BC-053.unused_per_model` the first
  two, `BC-010.each_model_judged_by_its_own_acceptances`, `BC-049.absent_record_gives_no_not_reviewed`,
  `BC-016.waiver_at_another_copy_of_the_record` and `BC-016.waiver_covers_each_alternatives_reason`); the
  fifth fails no file, since no file requires a review of a `not_met` result that carries a value.
- **The claims' other side.** BC-051's files hold for a build that does not claim the suite each names; what a
  build claiming it gives comes with that suite's cases.
- **BC-040's refusals.** The engine arms compare BC-051's refusals alone; item 7's are BC-040's own cases.

## How they were made and checked

The cases were drafted with AI assistance (Claude, Anthropic) from the specification text alone, by passes
shown no implementation; the code that runs them did not exist. Each arm states the sentences its answer rests
on, checked against the text, and was then checked by:
- the case schema (`schema/0.1/case.json`), every file; the reference reader
  (`tests/conformance/reference_reader.py`), every input read alike, the one that is not JSON refused alike;
  every record's hash recomputed by two RFC 8785 implementations, and every pin of a record in a declaration;
  the two records written here validated against the writer schema;
- a build written from `declarations.md` sections 1, 2 and 4 alone, over a read written from the text alone
  (`read_side_contract.md`, with `provenance.md` section 2 item 6 and `record_format.md` sections 4.1 and 6
  where it rests on them), which agrees with every file under the claims it states; that read agrees with
  every one of the 165 plain-read case files over this suite's fixtures that it takes;
- a control per arm, the arm's declaration with the one thing it tests removed, or, for five result arms,
  the records it is read over changed (the review completed or not, the record supplied or not), which gives
  that build another answer; for the one arm whose point is a refusal not given (an `accepted_difference` with
  no location), a seeded fault of that build which the arm catches instead; 47 more arms also carry a seeded
  fault each catches. Two pairs of files share a declaration, its records and its answer, and differ in their
  controls, each testing its own rule on the same build: `BC-006.waived_unknown_stays_unknown` (its control
  drops the waiver: the status does not move) and `BC-028.one_model_one_record` (its control renames the
  model: the result names it), and `BC-010.all_accepted` (its control drops one model's waiver: the verdict
  follows every model) and `BC-028.two_models_over_one_record` (its control drops the second model: each
  result names its own);
- 82 seeded faults of that build, each of which some file catches: among them a waiver covering a reason
  section 4.2 does not list, or ignoring its condition, code, field or record, or a reason that carries an
  `alternative`; an acceptance located by `id` alone; an implied condition counted applied though it filled
  nothing; `accepted_by` without what the read applied; the status raised when accepted; a model's reason
  covered by another model's acceptance; `unused` not kept per model; the label checked against the result's
  labels, or on no stored value; `not_reviewed` not given, or given to a result with no `provenance`; every
  record of the store read; a field with no requirement read;
- a draft schema of the declaration, against which every declaration a result case expects to pass, and every
  control that passes its own check, is valid, and every refused declaration invalid, except those whose rule
  a schema cannot state (a name given twice by a member's value, a field against `reads`, a location against
  `checked_over`, the label rule, the build's claims), and the one that is not JSON.

The scripts that generated and checked these files are not part of the repository. The files are the source.
