# The reference model

A test-only model of a read of one field of one record (`docs/specification/read_side_contract.md` sections 1
to 3), written from the specification's text alone, for the conformance cases, HP12 and the fuzz targets (the
S2 design's SQ49), as S3 keeps a test-only reference evaluator; and beside it the build's model of a
declaration checked on its own (`declarations.md` section 1, S7a-1) and of what the build gives past it, the
reads, the results, the verdict and the report (sections 2 and 4.2, S7a-2), each written from the text by an
agent that did not read the build's code ("The build's model" and "The build's results model", below). None
ships, and none imports anything from `materica`, at any depth.

| File | What it holds |
|---|---|
| `strict_json.py` | strict JSON (`record_format.md` section 1 item 6), RFC 8785 and the content hash (section 9), from the standard library |
| `read_model.py` | the model: the text's tables, steps 0 to 13, the result, `list_records` and `content_hash`; its open points in `OPEN_POINTS` |
| `build_model.py` | the build's model of the declaration's own check: its shape table, written from the text, its refusals by case and pointer under the precedence rule, and, past it, the declaration handed to the results model; its open points in its own `OPEN_POINTS` |
| `build_results_model.py` | the build's model past the declaration: the request each read is given, the read through the read model, the build's own reasons, what the read applied, the judgement by section 4.2's table held as its own data, `unused`, the verdict and the report, and `NoVerdict` for what it does not decide; its open points in its own `OPEN_POINTS` |
| `cases.py` | every case file of a read run through the model, and every build-check file through the build's models, under every configuration of claims it allows, and compared, a build's results as the specification's README compares them |
| `exceptions.py` | the case files each model does not agree with, by kind, each kind with its reason: today, reads outside the read model's scope, on which it gives no verdict, and no build-check file; and what the results model does not decide, by kind, each with its reason |
| `test_cases.py` | the read model agrees with every case file of a read, and the build's models with every build-check file, or the case file is listed under its kind |
| `direct.py`, `test_build_model.py` | the build model held on what no build-check file pins: declarations written there, each with the answer the text and the maintainer's rulings give (one fault is one member at fault, a pick is located by its record, a claimed suite gives no verdict, the order of the cases) |
| `results_direct.py`, `test_build_results_model.py` | the results model held on what no build-check file pins: build-check declarations with one thing changed, each read over the suite's fixtures with the answer the text gives; and its table of section 4.2 against the table parsed from `declarations.md`, since `main` has no `coverage.json` yet |
| `test_tables.py` | each model's tables against the generated vocabulary, and the build model's shape table and token lists against the declaration's JSON Schema, so that a drift of either fails |
| `test_citations.py` | each quote the models, and the table evaluator beside them, cite is at the line it cites; each open point is listed once and named where it is applied |
| `test_layering.py` | the models and the table evaluator reach no `materica` module, by the imports they write or in a fresh interpreter |
| `mutants.py`, `results_mutants.py`, `test_seeded_faults.py` | seeded faults of each model, each killed by a case file (or, for the build's models, a direct check) or listed as a survivor with its reason; not named `test_*mutants*`, since they are no Hypothesis search and run on every Python (`tests/conftest.py`, `PROPERTY_CONTROLS`) |

## What it decides

Steps 0 to 13 for the forms constant, table, interval, composition and evidence, a table's value from the
reference evaluator's `exact` mode; implied conditions, nominals and extrapolations, an extrapolation covering
a table's `outside_range` at step 11 under `want: value` with the value at the readable range's nearest end
(S3c, written from the text: `read_side_contract.md` sections 1, 2 and 5, `declarations.md` section 4.1); the
operations `list_records` and `content_hash`; and step 7 over alternatives read with no pick and no overlay
(S4a): the shape of `alternatives`, each alternative read alone and set aside, kept or refusing the
field, and the outcome with its reasons, each found reading one alternative carrying its index, and its
members. S4a's step 7 was written from the text by an agent that did not read the implementation's. So were
step 7's rows for a table alternative whose read gives a reason at step 11, or that an extrapolation covers
(S4d, `read_side_contract.md` section 3, step 7; `record_format.md` section 5 items 2 to 5): one outside its
readable range, off every edge, is set aside where no extrapolation the request carries would cover it, and
kept where one would, read on through steps 12 and 13, the extrapolation applied only where it is the one
left (under `no_pick` its entry holds the table as stored, with no end value and no `assumption`); one read
exactly at an edge refuses the field wherever the edge lies, `outside_range` beside `at_edge` or not; one
read with no operating value for its axis refuses the field with `request_incomplete`, which carries no
`alternative`, while one set aside at step 10 never reaches step 11; and one read over an operating range of
its axis stays, counts as a form `want` cannot give, and under `no_pick` its entry holds the table as stored,
beside its unit, conditions, specimen, statistics and provenance, with the labels step 12 gives it.

Anything else gives `NoVerdict`, an outcome of its own, which a test counts and never reads as a pass: a pick
or an overlay (S4), a `trainable` acceptance (S7a-4), a region target (the scene suite), and `want: fit` on a
field holding a fit record (the fits and reference data suite).

Each rule cites the text as `file:line` and a short quote. Where the text leaves a point open, the model takes
the maintainer's ruling where there is one, else the fail-closed choice, each listed once in `OPEN_POINTS` and
named where it is applied:

| Open point | The model's choice |
|---|---|
| `form_not_allowed_by_its_row` | a composition whose basis the row does not allow is refused as a form the row does not allow is: `form_not_registered` and the shared checks' reasons, its member not checked (maintainer, 2026-10-15; the text says so of a form) |
| `alternatives_without_a_pick` | step 7 for a read with no pick and no overlay (S4a), a pick or an overlay giving no verdict at step 0; since S4d a table alternative whose read gives a reason at step 11, or that an extrapolation covers, is set aside, kept or refuses the field by the text's rows of step 7, and the point `table_alternatives_at_step_11`, under which it gave no verdict wherever it stood among the others, is gone |
| `evidence_entry_provenance` | an entry's `provenance` is returned whole, holding the members the version defines at every depth, read from the writer schema below the provenance table's own, since the text names them in part only |

The model was first written to check the expected answers of S2's case files on 2026-10-15, as an independent
reader of the text, and brought to the text of this branch here. Two rulings it took then, a form the row does
not allow left unchecked and a status object breaking its shape giving `form_invalid` alone, are the text's
since S3 (`read_side_contract.md` section 3, step 8; `provenance.md` section 1), and so is the shape of
`alternatives` (`record_format.md` section 5): the model cites them there. So are the maintainer's rulings of
2026-10-19 and 2026-10-20 on three points the model once listed: an evidence entry's `provenance` is checked as
a field's, every review it holds at any depth read as every review is (`record_format.md` section 4.3 item 2);
a record's condition holding a member of the other kind of condition's shape breaks it (`provenance.md`
section 6.1 item 1); and a slip of `alternatives` at a field's place is refused (`record_format.md` sections 5
and 10, as built).

## Agreement with the cases

`test_cases.py` runs every case file of a read in the repository, 1,290 on the S7 specification's branch
(1,203 reads, 25 listings and 11 reads of the hash suite, and 51 content hashes), whichever step of the
implementation runs it, under each of the 8 configurations of claims (plain read, with or without the hash,
the fits and reference data, and the family evaluation suites) that agrees with the case's suite and claims.
Each is compared as the specification's README says ("Case files"), by the conformance runner's comparison.
The table evaluation suite's 35 files are left out, and so are the record checks' and the build checks', and a
test holds the files left out to exactly those whose operation is `evaluate`, `check`, `quote_sha256` or
`check_build`: a table's values at points, as a consumer's own evaluator asks for them, a record's checks, a
quote's hash and a declaration's build are no read. The build's own model runs the build checks' files
("The build's model", below).

The model agrees with 1,182 files, under every configuration each allows (9,080 runs), and gives no verdict on
108, each listed in `exceptions.py` under the kind its outcome names: an overlay (71), a pick (36) and a
`trainable` acceptance (1). It disagrees with none (measured on the S7 specification's branch, 2026-10-22: of
its five case files, the four of `label_basis` agree, and PR-339's, read under a `trainable` acceptance, which
S7a-4 builds, is listed under the kind `trainable`; on S4d's branch, 2026-10-22: the 24 files the kind of a
table alternative whose read gives a reason at step 11 listed, one an extrapolation covers included, each
gained a verdict, the case's under every configuration it allows: none gives an answer the text decides
against, and the kind is gone; at S3c's head, which reads an extrapolation, 2026-10-21: of the 55 files the
kind of an extrapolation listed, the 45 S3c runs gained a verdict, as did S3c's arm of `table` under an
extrapolation, the nine of a table alternative under one moved to S4d's kind, and the one holding a pick to
the picks'; at S3b-2's head, of the 83 files of a table that steps 8 and 9 pass, listed at S3a's head, 68
gained a verdict and 15 moved to the new kind, and S3b-2 added seven). Until S4a it also gave no verdict on 21
files of alternatives with reasons of their own, with which it now agrees, as with S4a's three cases of `unit`
under `no_pick`. A case file the model disagrees with, or gives no verdict on, fails unless a kind lists it,
for the detail that kind names; a listed one it agrees with fails as stale.

## The mutant table

`test_seeded_faults.py` gives the model one fault at a time and requires a case file to give an outcome the
list of exceptions does not (a disagreement, a no verdict no kind lists, or an agreement with a listed file),
or the fault to be listed as a survivor with its reason: each survivor is a rule no case pins, which the
properties of S2a-4's phase B must kill. The search stops at the first such case file; the count is of all of
them, measured 2026-10-17 on `main` at `6c9ab9f`, but `member_checked_off_its_row`'s, which PR #37's review's
cases kill (the same day). 75 faults: 61 killed, 14 survive; S2a-4's review added five survivors, each a rule
no case pins (below the table), so 80 faults: 61 killed, 19 survive. The two cases of the maintainer's token
ruling (2026-10-18) kill two of the survivors, so 63 killed, 17 survive. S4a replaced the fifth survivor
S2a-4's review added, `units_stored_differently_read_as_no_pick`, which the maintainer's ruling on `unit`
under `no_pick` (2026-10-19) made the text's reading, by `unit_of_the_last_remaining_alternative`, which that
ruling's cases kill, and added 16 faults of its step 7, each killed, measured 2026-10-19 at S4a's head: 96
faults, 80 killed, 16 survive. The maintainer's rulings of 2026-10-19 and 2026-10-20 bring cases that kill two
more, `evidence_entry_provenance_unchecked` and `slips_of_alternatives_ignored`, and a fault their cases kill,
`nested_reviews_returned_as_found`, so 97 faults: 83 killed, 14 survive. The rows these rulings change are
measured with them, and so are those their cases move that were current before them,
`condition_shapes_unchecked`, `every_slip_ignored` and `null_read_as_absent`; the others are as stamped. S3a's
case files kill one more, `broken_status_object_reports_its_token`
(`PR-110.table_unknown_status_beside_members` alone): 84 killed, 13 survive. S3b-2 adds seven faults of a
table's steps 10 to 13, each killed (below the table), and its case files, which read a table to the end, five
arms of the result's `table` among them, move the rows of sixteen others, measured with them at its head
(2026-10-21): 104 faults, 91 killed, 13 survive. Its fix round's two arms (a table whose read step 11 ends,
stated without origin, and a table's unknown member left out beside its value) move six rows; every row was
measured again with them (2026-10-21), and fifteen others differed from what the case files now give, each now
as measured. S3c adds thirteen faults of an extrapolation, at step 0 and at step 11, each killed (below the
table), and its 46 case files, to which the model now gives a verdict, its arm of `table` under an
extrapolation among them, move fifteen rows; every fault was measured over every case file of a read at S3c's
head (2026-10-21), and none made the model raise: 117 faults, 104 killed, 13 survive. Two of its faults raised
in their first form, each on reads it reached past its first kill: one applying an extrapolation across an
edge on the readable range's end, and one taking the end value at `x[0]`, outside a narrower `source_range`,
where the reference evaluator gives no value; each answers there now, still breaking its rule (an edge on the
end is still looked at; the end value is `y[0]` or `y[-1]` as stored). S3c's fuzz target 5 found the model
reading an implied value for a numeric condition that holds a `token` beside a unit other than the registered
one as `request_incomplete` alone, where the text gives `request_unit_mismatch` beside it, its unit "checked
as an operating condition is", "whatever else is wrong with that entry" (`read_side_contract.md:51-53,
:82-83`): the model is corrected, and an arm pins it (`PR-320.implied_value_holding_a_token_in_another_unit`),
which moves three rows; every fault was measured again with it, none raising. S4d adds twelve faults of step
7's rows for a table alternative at step 11, each killed (below the table), and its 24 case files, to which
the model now gives a verdict, move 32 rows; every fault was measured over every case file of a read on
S4d's branch (2026-10-22), and none made the model raise, in its first form or since: 129 faults, 116 killed,
13 survive. Four older faults of step 7 took effect beyond their rule once those files had a verdict, and
each is narrowed to it, so that its row counts its own rule's kills: `refused_alternative_set_aside` sets
aside an alternative refused at steps 8 and 9 alone, not one `at_edge` refuses, and
`set_aside_alternative_refuses` refuses one set aside at step 10 alone, not one outside the range;
`nominal_applied_under_no_pick` takes an interval's nominal alone, and `nominal_not_applied_to_the_one_left`
drops a nominal's value alone, not an extrapolation's, whose `assumption` each had read as a nominal's. The
four cases of a label's basis (2026-10-21) kill no survivor; the four rows they move, each current before
them, are measured with them (2026-10-22): `alternatives_shape_unchecked`, `every_slip_ignored`,
`operating_omitted_from_entries` and `step_12_labels_dropped`.

A fault that makes the model raise on a case file its search reads fails the search, with the model's
traceback and a note naming the file and the claims (`cases.py`, `outcome`): a raise shows that the fault broke
the model, not that a case's expected answer tells the fault apart, so it is never a kill. The search reads
the case files in name order and stops at a fault's first kill, so a raise on a later file is not seen there:
each raise below was found by measuring every fault over every case file of a read, which the search does not
do, and each fault that raised is held to its answer on the files where it did
(`test_a_fault_that_once_raised_answers_on_the_files_it_raised_on`). Its control, `status_object` replaced
by a function raising `TypeError`, `KeyError` or `AssertionError`, fails the check in each, where counting a
raise of that kind as a kill would pass it. Until 2026-10-21 the search counted a raise as a kill. Measured
that day over all 97 faults and every case file of a read, on `main` at `76907779`, three faults made the
model raise and no other did: `tolerance_without_an_operating_condition` raised `KeyError` on two of its three
files, its first (`PR-308.tolerance_with_other_operating_condition`) and
`PR-308.tolerance_without_operating_conditions`, by indexing the operating condition the request lacks;
`alternatives_shape_unchecked` raised on `PR-044.alternatives_not_list`, one of its five, and
`condition_shapes_unchecked` on `PR-049.condition_value_null`, one of its 25, each after its first file. Each
now answers wherever it takes effect and still breaks its rule: the first reads a condition whose tolerance
has no operating condition as one given no tolerance; the second reads an `alternatives` that is not a list as
a list of its one entry; the third has steps 9 and 10 read a condition it leaves unchecked that they cannot
index as one the record does not hold. Measured again with the three fixed, no fault raises on any case file,
and every fault is killed by the same files as before, from the same first file, each by an answer. Of the
three, the search reached a raise of `tolerance_without_an_operating_condition` alone, on its first file.

| Mutant | Fault | Case files that kill it |
|---|---|---|
| `want_outside_section_6` | a `want` that is none of section 6's tokens is read | 2 |
| `fits_wants_without_their_suite` | `fit`, `coverage` and `reference_data` read by a reader without their suite | 6 |
| `tolerance_without_an_operating_condition` | a tolerance with no operating condition accepted | 3 |
| `request_units_not_compared` | an operating condition's, a tolerance's or an implied value's unit not compared | 30 |
| `negative_zero_tolerance_refused` | a tolerance of `-0` read as below zero | 2 |
| `declaration_members_in_a_requirement_read` | a requirement holding `label`, `represents`, `population_level` or `review` read | 3 |
| `acceptances_applied_anywhere` | an acceptance applied at another record, a region, an interval or no location | 18 |
| `two_nominals_for_one_field` | two nominals naming one field read as the first | 1, `PR-330.two_nominals_one_field` alone |
| `unregistered_field_requested` | a field the reader's version does not register read, and found absent | 6 |
| `every_slip_ignored` | a member one slip from a named one ignored, in a request and in a record | 49 |
| `plurals_not_slips` | a word made plural or singular not one slip | survives: each plural slip in the cases adds an `s` (`fluids`), and so is one character inserted |
| `envelope_body_and_section_slips_ignored` | a slip in the envelope, the body or a section refuses no field | 6 |
| `unreadable_sources_ignored` | an unreadable source never turns `absent` or `pin_mismatch` into `malformed` | 49 |
| `first_of_differing_copies_read` | of two copies with the pin whose bytes differ, the first read | 2 |
| `hash_not_checked_before_step_4` | `hash_not_checked` on a result that ends before step 4 | 1, `PR-327.pin_no_hs` alone |
| `hash_never_recomputed` | a reader claiming HS never recomputes the hash | 8 |
| `other_minor_versions_read` | a record of another `MAJOR.MINOR` read | 15 |
| `alternatives_shape_unchecked` | an `alternatives` that is empty, not a list or beside a value field's members read | 6 |
| `want_mismatch_beside_no_pick` | `want_mismatch` reported under `no_pick` for an alternative whose form `want` cannot give | 7 |
| `conditions_kept_under_no_pick` | a `no_pick` result holding `conditions` of its own | 20 |
| `alternatives_counted_from_one` | an `alternative_values` entry's index counted from one | 20 |
| `labels_raised_from_an_alternative` | an alternative's labels on the `no_pick` result's own | 3 |
| `nominal_ignored_over_alternatives` | an interval beside other alternatives not counted as a form `want: value` gives under a nominal | 3 |
| `nominal_applied_under_no_pick` | a nominal applied to an interval alternative under `no_pick` | 1, `PR-338.no_pick_two_intervals_nominal` alone |
| `unknown_tokens_read_as_shape_faults` | a token the reader knows for no member of that name gives `form_invalid` | 32 |
| `status_tokens_unchecked` | a status object takes any token, in any member | 5 |
| `member_checked_off_its_row` | the member of a form the row does not allow checked as on a row allowing it | 2, `PR-036.broken_composition_on_density` and `PR-036.broken_interval_on_elemental_composition` |
| `composition_checked_beyond_its_basis` | a composition whose basis the row does not allow checked further | survives: each composition whose basis its row does not allow is otherwise well formed in the cases |
| `family_suite_ignored` | a parameter set read without the family evaluation suite not `family_suite_absent` | 8 |
| `entry_withheld_in_part_read` | an evidence entry withheld in some members but not every one read | 1, `PR-052.entry_partly_withheld` alone |
| `missing_label_refused` | a field without its row's label refused | 284 |
| `unreadable_review_refuses` | a review the reader cannot read refuses the field | 9 |
| `null_read_as_absent` | `null` in a member step 8 checks read as the member absent | 10 |
| `statistics_unchecked` | a statistics block not checked | 47 |
| `uncertainties_unchecked` | a relative or expanded uncertainty not checked | 14 |
| `derivation_unchecked` | a derived value's derivation not checked | 14 |
| `input_specimens_optional` | a derivation without `input_specimens` read | survives: every derivation in the cases holds `input_specimens` |
| `population_level_checks_stop_at_a_missing_member` | a population level missing a member has its `level` and `within` left unchecked | survives: no case holds a population level missing a member beside a token of its own |
| `dof_token_unchecked_under_student_t` | a `dof` held as a status object under a Student's t distribution has its token left unchecked | survives: no case holds such a `dof` of an unknown token |
| `every_forms_member_named_at_a_field` | every form's member named at a field's place, so that a slip of another form's refuses a constant | survives: no case holds a slip of another form's member beside a form the reader knows |
| `every_status_object_an_unstated_kind` | a `plus_minus` entry whose `stated_as` holds any status object counted as of unstated kind | survives: no case holds a `stated_as` of another status token beside an entry of a stated kind |
| `section_specimen_unchecked` | a section's `specimen` not checked for a field read from it | 3 |
| `condition_shapes_unchecked` | a condition of a name the reader knows not checked | 25 |
| `broken_status_object_reports_its_token` | a status object that breaks its shape gives its token's `unknown_token` beside `form_invalid` | 1, `PR-110.table_unknown_status_beside_members` alone (since S3a) |
| `members_of_the_other_kind_read` | a numeric condition holding `token`, or a token condition holding `value`, read | 8: `PR-330.implied_token_for_numeric_condition`, `PR-330.implied_unit_for_token_condition` and `PR-320.implied_value_holding_a_token_in_another_unit`, the implied half, which the token ruling settled; `PR-045.numeric_condition_holding_token`, `PR-045.numeric_condition_holding_token_status`, `PR-045.token_condition_holding_value`, `PR-045.token_condition_holding_value_null` and `PR-301.other_kind_beside_unknown_basis`, the record half, ruled on 2026-10-19 |
| `members_of_the_other_kind_ignored` | a numeric condition's `token`, or a token condition's `value`, ignored as a member the reader does not know: not refused, and not returned | 8, the same eight, the implied half's three and the record half's five |
| `slips_of_alternatives_ignored` | a member one slip from `alternatives` beside a value field's members ignored | 1, `PR-030.near_typo_alternative_beside_constant` alone, the case of the maintainer's ruling (2026-10-19) |
| `evidence_entry_provenance_unchecked` | an evidence entry's `provenance` not checked | 1, `PR-052.entry_provenance_origin_unknown` alone, the case of the maintainer's ruling (2026-10-19) |
| `nested_reviews_returned_as_found` | a review inside a provenance an evidence entry's `per_parameter` maps a parameter to returned as found, and none where that provenance holds none | 2, `PR-052.entry_provenance_per_parameter_review_unknown` and `PR-052.entry_provenance_per_parameter_review_absent`, the cases of the maintainer's ruling (2026-10-20) |
| `declaration_names_not_named_in_a_request` | a slip of a requirement's `field`, or of its conditions' `reason` or `consequence`, ignored | survives: no case holds a slip of `field`, `reason` or `consequence` in a requirement |
| `units_compared_after_case_folding` | a record's units compared after case folding | 3 |
| `fact_units_unchecked` | a specimen fact's unit not compared with the one its row fixes | 3 |
| `token_condition_unit_accepted` | a `unit` on a token condition passes step 9 | 1, `PR-037.unit_on_token_condition` alone |
| `plus_minus_units_unchecked` | a `plus_minus` entry's unit not compared | 1, `PR-037.plus_minus_unit` alone |
| `floating_point_as_written` | section 5's tests computed in floating point as written | 3 |
| `strict_inequalities` | `<` for `<=` in section 5's table | 12 |
| `plus_minus_ignored` | a stated plus or minus ignored | 15 |
| `unchecked_read_as_met` | a stated condition the request gives no tolerance or accept list for read as `met` | 7 |
| `operating_omitted_from_entries` | a condition entry without the request's operating condition | 337 |
| `implied_fills_any_condition` | an implied condition fills a stated condition, or one held as another status object | 2 |
| `disagreeing_implied_conditions_read` | two implied conditions that disagree read as the first | 8 |
| `implied_values_compared_by_value` | two implied values compared as numbers, so that `0` and `-0` agree | 1, `PR-316.implied_zero_beside_minus_zero` alone |
| `required_with_ignored` | a condition another condition requires with its token not checked | 4 |
| `unknown_condition_names_ignored` | a condition name the reader does not know gives no entry and no reason | 6 |
| `stated_without_origin_unreported` | a value stated without origin not `unknown` | 3, `PR-013.kept_table_step12_reason_beside_no_pick`, `PR-307.steps_12_and_13_run` and `PR-309.stated_without_origin` |
| `step_12_labels_dropped` | the field's label and `mixed_conditions` not added | 161 |
| `bounds_given_by_a_constant` | `want: bounds` gives a constant's value | 4 |
| `value_given_by_an_interval` | `want: value` gives an interval's bounds without a nominal | 22 |
| `nominal_outside_supplies_the_value` | a nominal outside an interval's bounds supplies the value | 3 |
| `best_status` | the status the best of the reasons, not the worst | 28 |
| `value_beside_not_met` | a value returned beside `not_met` without an assumption, as beside `condition_outside` | 22 |
| `unknown_members_returned` | a member the reader does not know returned | 15 |
| `review_returned_as_its_result` | a known review returned as its `result` alone | 2 |
| `unit_returned_without_its_reason` | a unit held as a status object returned without its `reason` | 4 |
| `section_facts_not_merged` | the result's `specimen` the field's facts alone | 26 |
| `results_share_the_record` | a result shares its members with the record read | survives: a case compares a result's JSON, in which no object is shared |
| `ies_not_a_plural` | a final `y` exchanged with `ies` not one slip | survives: no case holds a slip of a final `y` made `ies` |
| `donor_age_of_neither_accepted` | a `donor_age` holding neither `value` nor `range` accepted | survives: no case holds one |
| `review_of_both_shapes_read_as_its_status` | a review holding both `status` and `result` read as its status object | survives: no case holds one |
| `reviewed_review_keeps_a_status_objects_members` | a reviewed review returned with a status object's members, its `reason` among them | survives: no case holds one |
| `unit_of_the_last_remaining_alternative` | under `no_pick`, every entry's `unit` the last remaining alternative's | 3, the three `PR-013.evidence_unit*` arms |
| `refused_alternative_set_aside` | an alternative refused at step 8 or 9 set aside, not refusing the field | 11 |
| `set_aside_alternative_refuses` | an alternative whose conditions give `not_met` at step 10 refusing the field, not set aside | 11 |
| `request_fault_sets_aside` | an alternative whose read a fault of the request ends set aside, not refusing the field | 3 |
| `want_mismatch_sets_aside` | an alternative whose form `want` cannot give set aside, not kept | 13 |
| `set_aside_reasons_dropped_where_refused` | the set-aside alternatives' reasons dropped where another refuses the field | 5 |
| `waiting_reasons_dropped_where_refused` | the `not_met` reasons of an alternative that stays dropped where the field is refused | 3, `PR-044.refused_reports_waiting_nominal_invalid`, `PR-044.refused_reports_waiting_outside_range` and `PR-044.refused_reports_waiting_want_mismatch` |
| `labels_kept_where_refused` | the alternatives' labels on the result where the field is refused or every alternative set aside | 2, `PR-316.implied_two_disagree_in_alternative` and `PR-336.refused_over_alternatives_no_hs` |
| `set_aside_reasons_beside_the_one_left` | the set-aside alternatives' reasons reported beside the one left | 13 |
| `one_left_reasons_without_their_alternative` | the one left's reasons without their `alternative` | 7 |
| `nominal_not_applied_to_the_one_left` | a nominal not applied to the interval left, which gives no value | 1, `PR-338.one_left_interval_nominal_applied` alone |
| `not_met_reasons_beside_no_pick` | the `not_met` reasons of the alternatives that stay reported beside `no_pick` or `want_mismatch` | 17 |
| `unknown_reasons_dropped_beside_no_pick` | the `unknown` reasons of the alternatives that stay dropped beside `no_pick` or `want_mismatch` | 4, `PR-013.evidence_unit_of_the_first_that_stays`, `PR-013.index_past_set_aside_and_unknown_reasons`, `PR-013.kept_table_step12_reason_beside_no_pick` and `PR-013.want_mismatch_unknown_reasons_stand` |
| `set_aside_reasons_beside_no_pick` | the set-aside alternatives' reasons reported beside `no_pick` or `want_mismatch` | 2, `PR-013.evidence_unit_of_the_first_that_stays` and `PR-013.index_past_set_aside_and_unknown_reasons` |
| `request_fault_given_an_alternative` | a fault of the request found reading one alternative given that `alternative` | 6, PR-316's two arms in an alternative and PR-308's four with no operating value for a table alternative's axis |
| `index_among_those_that_stay` | an alternative's index counted among the alternatives that stay, in its reasons and its entry | 5 |
| `unit_of_the_first_stored_alternative` | under `no_pick`, every entry's `unit` the first stored alternative's, set aside or not | 3, the three `PR-013.evidence_unit*` arms |
| `edge_unseen_by_the_axis_entry` | the axis entry `met` at an edge inside the readable range | 7 |
| `outside_range_dropped_at_an_edge` | at an edge outside the readable range, `at_edge` alone | 6, PR-018's and PR-307's arms at an edge outside the readable range, below it and above it, and PR-044's two at an edge outside a narrowed readable range |
| `source_range_never_narrows` | the readable range `x`'s, whatever `source_range` holds | 23 |
| `outside_range_beside_a_range` | over an operating range of the axis that leaves the readable range, `outside_range` beside `want_mismatch` | 3, `PR-321.range_outside`, `PR-321.range_outside_under_extrapolation` and `PR-321.range_straddling_end` |
| `step_11_reasons_without_the_axis` | step 11's reasons without the axis as their `condition` | 72 |
| `table_returned_whole` | a table returned as stored with the members the reader does not know | 2, `PR-337.unknown_member_in_table_as_stored` and `PR-337.unknown_member_left_out_of_the_table_beside_its_value` |
| `table_member_dropped` | a value read from a table returned without the table it is read from | 4 |
| `extrapolation_under_any_want` | an extrapolation applied under any `want` | 4, PR-307's arms under `want: bounds`, `components` and `evidence`, and `PR-044.outside_under_extrapolation_want_bounds_set_aside` |
| `extrapolation_at_an_edge` | an extrapolation applied at an edge outside the readable range | 3, `PR-044.edge_outside_narrowed_range_under_extrapolation_refuses`, `PR-307.at_edge_outside_readable_range` and `PR-307.at_edge_outside_readable_range_above` |
| `extrapolation_across_an_edge` | an extrapolation applied across an edge strictly between the read and the readable range's nearest end | 3, `PR-044.across_edge_under_extrapolation_set_aside`, `PR-307.across_edge` and `PR-307.across_edge_above` |
| `extrapolation_end_of_x` | the end value `y[0]` or `y[-1]` where `source_range` narrows the range | 7 |
| `extrapolation_far_end` | the end value taken at the readable range's far end | 15 |
| `extrapolated_read_ends_at_step_11` | a read an extrapolation covers given no step-12 reason or label | 2, `PR-013.kept_table_step12_reason_beside_no_pick` and `PR-307.steps_12_and_13_run` |
| `extrapolation_located_anywhere` | an extrapolation applied wherever it is located | 5 |
| `two_extrapolations_read_as_the_first` | two extrapolations naming one field read as the first | 2, `PR-330.two_extrapolations_one_field` and `PR-330.two_extrapolations_one_field_one_without_location` |
| `empty_law_accepted` | an empty `law` accepted | 3, PR-330's three arms of an empty `law` |
| `white_space_law_refused` | a `law` of white space refused | 1, `PR-330.extrapolation_law_white_space_read` alone |
| `extrapolation_method_unchecked` | an extrapolation's `method` unchecked | 2, `PR-330.extrapolation_method_missing` and `PR-330.extrapolation_method_unknown` |
| `assumption_with_its_basis` | an extrapolation's `assumption` holding its `basis` | 14 |
| `covered_outside_range_dropped` | a read an extrapolation covers without its `outside_range` | 19 |
| `outside_range_kept_without_an_extrapolation` | an alternative outside its form's range, off every edge, kept with no extrapolation to cover it | 5 |
| `covered_alternative_set_aside` | an alternative an extrapolation the request carries would cover set aside, not kept | 4 |
| `edge_inside_the_range_sets_aside` | a table alternative read exactly at an edge inside its readable range set aside, not refusing | 2, `PR-044.at_edge_under_extrapolation_refuses` and `PR-044.table_at_edge_not_set_aside` |
| `edge_outside_the_range_sets_aside` | a table alternative read exactly at an edge outside its readable range, `outside_range` beside `at_edge`, set aside | 2, `PR-044.edge_outside_narrowed_range_refuses` and `PR-044.edge_outside_narrowed_range_under_extrapolation_refuses` |
| `set_aside_alternative_reaches_step_11` | a table alternative set aside at step 10 read on to step 11, its missing operating value refusing the field | 1, `PR-308.table_set_aside_never_reaches_step_11` alone |
| `over_a_range_set_aside` | a table alternative read over an operating range of its axis set aside, not kept | 5 |
| `over_a_range_counted_as_a_form_want_gives` | a table read over an operating range of its axis counted as a form `want` gives | 2, `PR-013.two_tables_over_operating_range_want_mismatch` and `PR-013.want_mismatch_unknown_reasons_stand` |
| `over_a_range_entry_unlabelled` | the `no_pick` entry of a table read over an operating range of its axis without step 12's labels | 1, `PR-013.table_over_operating_range_keeps_labels` alone |
| `over_a_range_entry_bare` | the `no_pick` entry of a table read over an operating range of its axis without its unit, specimen, statistics and provenance | 2, `PR-013.table_over_operating_range_as_stored` and `PR-013.table_over_operating_range_keeps_labels` |
| `extrapolation_applied_under_no_pick` | under `no_pick`, the entry of an alternative an extrapolation covers holding the end value and `assumption` | 3, `PR-013.kept_table_step12_reason_beside_no_pick`, `PR-013.table_outside_under_extrapolation` and `PR-044.beside_edge_under_extrapolation_kept` |
| `kept_alternative_read_no_further` | an alternative kept for an extrapolation not read on through steps 12 and 13 | 2, `PR-013.kept_table_step12_reason_beside_no_pick` and `PR-044.outside_under_extrapolation_one_left` |
| `kept_for_an_extrapolation_under_any_want` | an alternative outside its range kept for an extrapolation that would cover it under `want: value`, whatever the `want` | 1, `PR-044.outside_under_extrapolation_want_bounds_set_aside` alone |

Ten faults die to one case file alone; a change to that file would let each live, so the properties of phase
B should kill them as well. Of the eight survivors, three were the open points (`members_of_the_other_kind_read`,
`slips_of_alternatives_ignored`, `evidence_entry_provenance_unchecked`), which no case pinned while the text left
them open (the maintainer's rulings brought cases that kill all three: the token ruling's and the record
half's, `PR-030.near_typo_alternative_beside_constant` and `PR-052.entry_provenance_origin_unknown`); one is a
rule of the text that no case pins either, since S2a-4's fix round
(`declaration_names_not_named_in_a_request`: `read_side_contract.md:40-41` and `declarations.md:30` and `:64` name
a requirement's `field` and its conditions' `reason` and `consequence`, and a read refuses a slip of one: the
former open point `names_a_declaration_gives_a_requirement`, decided by the text as S2a-4's review read it,
approved by the maintainer on 2026-10-18 and confirmed on 2026-10-19); one is
the rule that a status object breaking its shape gives no reason of its own
(`broken_status_object_reports_its_token`), a ruling the text took up with S3, whose example is a table's,
which survived until S3a let the model read a table through step 9; one is the rule that a composition whose
basis its row does not allow is checked no further (`composition_checked_beyond_its_basis`), which only S3's cases show, again for tables;
one needs a plural of two characters or more (`plurals_not_slips`); and one cannot show through JSON at all
(`results_share_the_record`, HP6's). The same rule for a form the row does not allow
(`member_checked_off_its_row`) survived until PR #37's review added two cases that kill it, a composition with
no component on `bulk.density` and an interval upside down on `bulk.elemental_composition`, each
`form_not_registered` alone. The ninth, `input_specimens_optional`, is the model's own
reading until S2a-4's phase B, whose agreement property (HP12) found that the text requires the list
(`provenance.md` section 5 item 3, "A derived value carries the specimen facts of each input"); the model was
fixed, and the fault seeded. The tenth, `members_of_the_other_kind_ignored`, was the implementation's
reading of that open point's record half (S2a-4's phase B), which HP12 listed as a known divergence, held
exactly by this fault, until the maintainer ruled it fail closed (2026-10-19) and the implementation came to
refuse it; HP12 lists no divergence of it since. It and `members_of_the_other_kind_read` also ignore the
implied half, since the model reads both halves by one function, and so the two cases of the maintainer's
token ruling kill both, as the two of the record half's ruling do; neither is a survivor since. The last four are the model's readings until fuzz
target 4, held to the model, found them on its first minutes: a population level whose `within` is missing
or slipped had its `level` token left unchecked, so did a `dof` status object under a Student's t
distribution, against `read_side_contract.md` section 2 item 2, "Each step makes all its checks before the
read stops"; and a `stated_as` of any status token counted as of unstated kind, where `provenance.md` section
6.1 item 6 names `{"status": "unstated"}`; and every form's member named at a constant's place, so that a
slip of `table` refused it, where `record_format.md` section 5 names "the form's member", `value` for a
constant (step 8 names every form's member only beside a form the reader does not know). Each was fixed and
seeded.

S2a-4's review pinned the five it added: the first four are rules no case or HP12 draw held, the fourth the
model's own reading until then (a reviewed review's `reason` was returned, which `provenance.md` section 2
item 6 does not name for a reviewed review), fixed and seeded; the fifth was a step S4 owns, which no read S2
built reached, and S4a replaced it (above).

S4a's sixteen break each rule of step 7 the model decides for a read with no pick and no overlay: an
alternative's standing (set aside, staying or refusing the field), the reasons each outcome reports and
withholds, each reason's `alternative`, the nominal on the one left, the labels of a result that rests on no
single alternative, the entries' indexes and the `unit` under `no_pick`. Four die to one case file alone:
`request_fault_sets_aside`, `nominal_not_applied_to_the_one_left`, `unknown_reasons_dropped_beside_no_pick` and
`set_aside_reasons_beside_no_pick`. A fifth, `unit_of_the_first_stored_alternative`, died to the case S4a wrote
for it alone, three evidence alternatives the first of which an implied condition sets aside: only a unit
registered as a status object can be stored differently, which only evidence's is, and evidence holds no
registered condition of its own, so an implied condition is the one way to set an evidence alternative aside.
Since S3b-2 (the maintainer's ruling of 2026-10-19 on the result's shape) each entry holds its own
alternative's unit, and both `unit` faults set every entry's unit to one alternative's, so each dies to the
three evidence arms, whose entries' units differ.
Since S3b-2, `request_fault_sets_aside` dies to four more, PR-308's table alternatives read with no
operating value for the axis, a fault of the request that refuses the field. While those gave no verdict, any
verdict there killed it; since S4d gives them one, it dies to two of them, those beside a constant that
stays, and to `PR-316.implied_two_disagree_in_alternative`. It lets the other two through: where no other
alternative stays, the fault sets every alternative aside, and that result reports what the refusal does.

S3b-2's seven break each rule of a table's steps 10 to 13 the model decides: the axis entry `not_met` at an edge
(`read_side_contract.md:475`), `outside_range` beside `at_edge` at an edge outside the readable range
(`record_format.md:420-421`), the readable range narrowed by `source_range` (`record_format.md:416-417`),
`want_mismatch` alone over an operating range of the axis (`read_side_contract.md:104-106`), step 11's reasons
each with the axis (`read_side_contract.md:143`), a table returned with only the members the reader knows
(`read_side_contract.md:168`), and the result's `table` (`read_side_contract.md:134`). Each kill is a
disagreement, none a raise of the model (checked). `table_returned_whole` dies to the two arms that hold a
table's unknown member, and `table_member_dropped` to the three where `table` is present. Two older faults made
the model raise in its table code, each on one case file (`best_status` on `PR-301.unknown_beside_outside_range`,
whose `outside_range` then ended no read, so that the evaluator was asked outside the range;
`null_read_as_absent` on `PR-049.source_range_null`, whose `source_range: null` step 8 then read as absent and
step 11 as present), the class of S3a's open point 8. Both raises were found by measuring every fault over
every case file of a read, which the search does not do: it stops at each fault's first kill, before the raise
(`best_status` at `PR-013.index_past_set_aside_and_unknown_reasons`, `null_read_as_absent` at
`PR-045.token_condition_holding_value_null`), with the fault as it was and as it is. Each answers there now
(S3b-2's fix round), still breaking its rule: under `best_status` a read at an edge or outside the readable
range, where the table has no value, ends at step 11 all the same (`table_read_ended_where_it_has_no_value`),
and under `null_read_as_absent` every step reads the field without its `null` members, as step 8 does
(`field_read_without_nulls`). Each is killed by the same case files as before (6 and 10), each by an answer,
and is held to its answer on the file where it raised, as are the three above and the two `condition_entry`
wrappers of `tolerance_without_an_operating_condition` and `condition_shapes_unchecked`, which, before they
took the table axis S3b-2's model passes, raised on every file they reached (330 and 353 files), and which
are held on three table reads among them.

S4d's twelve break each rule of step 7 for a table alternative whose read gives a reason at step 11, or that
an extrapolation covers: an alternative outside its range, off every edge, set aside unless an extrapolation
the request carries would cover it (`read_side_contract.md:264-265`), and kept where one would
(`read_side_contract.md:268-269`), as `want: value` alone lets it (`record_format.md:359-360`), read on through
steps 12 and 13 (`read_side_contract.md:271-272`), with no extrapolation applied under `no_pick`
(`read_side_contract.md:294-295`); one at an edge refusing the field inside the readable range and outside it
(`read_side_contract.md:275-276`, `record_format.md:366-368`); one set aside at step 10 never reaching step 11
(`read_side_contract.md:278-279`); and one over an operating range of its axis kept
(`read_side_contract.md:268-271`), counted as a form `want` cannot give (`read_side_contract.md:291`), its
`no_pick` entry holding step 12's labels (`read_side_contract.md:126`) and its own unit, conditions, specimen,
statistics and provenance (`record_format.md:378-380`). The two rows of the request's fault at step 11, that it
refuses the field and that its reason carries no `alternative`, are S4a's `request_fault_sets_aside` and
`request_fault_given_an_alternative`, which read every fault of the request, step 10's and step 11's alike;
the second dies to PR-308's four arms since. Each kill is a disagreement, none a raise of the model (measured
over every case file, 2026-10-22). Three die to one case file alone (`set_aside_alternative_reaches_step_11`,
`over_a_range_entry_unlabelled` and `kept_for_an_extrapolation_under_any_want`), and
`extrapolated_read_ends_at_step_11` no longer does, now dying to the arm of a kept table's step-12 reason
beside `no_pick` as well: fifteen faults die to one case file alone. HP12 does not search S4d's three yet; its
table of the model's faults is `tests/property/test_model_mutants.py`'s.

The agreement property HP12 (`tests/property/test_model_properties.py`) kills 13 of the 14 survivors, the two
the token ruling's cases kill, and `member_checked_off_its_row`, which it searched as a survivor before two
cases came to kill it, every one of the 17 faults one case file alone kills (S4a's five among them, and
`evidence_entry_provenance_unchecked` and `slips_of_alternatives_ignored`, survivors HP12 searched until the
cases of their rulings came), and
`nominal_outside_supplies_the_value`, which two kill, each with the model given the fault and the core as it
is (`tests/property/test_model_mutants.py`); S2b-2, which reads evidence and nominals, brought the six that
waited for it. The other one is listed there with the reason no read shows it: a shared object never shows
in JSON.

## The build's model

`build_model.py` models a build's check of a declaration on its own (S7a-1), the refusals `declarations.md`
section 1 gives before any record is read: the declaration's shape (its table, the departures, the refusal,
pointer and precedence paragraph), items 3, 4, 7, 8 and 12, the `population_level` rule, and section 4.1's
location rule and item 4. It was written from the specification's text, with the build-check case files read
as data, by an agent that never read the build's code, as each piece's part of the build's model is (the S7
design's 6.1); the two meet at the case files and at HP41's and HP42's properties. Its shape table is written
from the text's; the names the build's version registers (fields, conditions, facts, reasons, labels, the
`represents` tokens, levels and distributions) are the read model's tables, and the token lists the shape table
adds (the acceptance kinds, a requirement's `review`, the distributions, the facts an implied condition names,
the codes that name a condition) are held to the vocabulary (`test_tables.py`).

**What it decides.** Every refusal of the declaration's own check, by case id and pointer, each fault carrying
the case of the first rule that names it (BC-004, BC-005, BC-040, BC-044, BC-043, BC-037, BC-050, BC-051 and
BC-048, in that order), two faults of one case and pointer one refusal; and the report of a refused
declaration, which holds its refusals and, where the text is JSON, the declaration as given and its
`consumer`. A fault is one member at fault (maintainer, 2026-10-24; `declarations.md:156-163`, and the suite's
README, "a fault the token rule names too"): a member two rules name is one fault holding both, so a waiver's
`label` that item 4 and the token rule both refuse gives BC-050 alone, a `domain`, `path` or `sampling` of
another JSON type, which item 12 and the shape rule both name, gives BC-051 alone where the suite is not
claimed (and no verdict where it is), and a status object as a target fact, or as an implied condition's
value, gives one refusal at the member, nothing inside it checked. The rule is held where the faults are
gathered (`refusals_of`: one refusal for each member at fault, the first case by the text's order); a member
missing from an object is that object's fault, apart from the object's own and from another missing member's,
which the text gives their own cases. A pick is
located by its `record`, a `region` or an `interval` being named beside it: one naming either and no `record`
is refused as unlocated (BC-037), whatever the build claims (maintainer, 2026-10-24; the pick row,
`declarations.md:357`, and `declaration.json`, which requires it).

**What it does not.** A declaration that passes its own check it takes no further: its no verdict there,
`PAST_THE_DECLARATION`, hands the declaration to the results model ("The build's results model", below), and
a pick or an overlay gives no verdict (S7c's). So does a declaration holding a member a suite the
build claims checks further (the scene suite, USD read, the sampling suite), whatever else it holds: the
refusals the model places beside such a member are not reported (the fail-closed choice, maintainer,
2026-10-24, at the cost that a certain refusal under a claimed suite goes uncompared: one of a
`population_level` beside no `represents` or another one, and one of a sampled requirement with no `sampling`
block, are among those). Three rules give refusals it does not place wholly: item 7's (BC-040), which it
places where the declaration decides it (a model over records or a path, a crosswalk no case passes, a
requirement wanting a token other than `value`, a declared engine value without its `reason` or `basis`: one
refusal a model, at its `engine`) and leaves unplaced where it does not (a model over a domain); an interval
location's shape, which the text does not give; and an engine's declared values, which its crosswalk shapes. A
refused report names what is unplaced, and a case compares it only where `compare.rules_compared` leaves it
out, as BC-051's two engine files do; else it is no verdict, never a pass.

Where the text leaves a point open, the model takes the maintainer's ruling where there is one, else the
fail-closed choice, each listed once in its `OPEN_POINTS` and named where it is applied:

| Open point | The model's choice |
|---|---|
| `exactly_one_of` | a place holding none, or more than one, of the members it takes exactly one of is at fault at its own pointer, as for a missing member |
| `member_judged_beside_a_faulty_one` | the refusal paragraph's three pairs apart, a member whose allowed values depend on another member at fault (a label beside an unregistered field, an implied condition's `token` beside an unknown fact, ...) is not judged |
| `reads_at_fault` | a `reads` at fault is the member itself; beside it no field is judged against it (a requirement's, as the text says; a combination's and a `trainable` entry's, by the same reading) |
| `combination_sections` | a combination's fields are from pairwise different sections |
| `chain_ends` | a chain's `from` and `to` hold `family`, a string, and `record`, a material reference; `state_mapping` maps names to strings |
| `independence_fields` | an independence entry's `fields` each name a registered field and one location, as a `trainable` entry does |
| `accepted_difference_basis` | an accepted difference's `value` may hold `basis` (`stated` or `inferred`) and `inferred_from` |
| `trainable_location_in_a_scene` | whether a region or an interval lies in its model's domain or path is the scene suite's (unplaced); over records neither does, nor does a record over a domain or a path |
| `interval_location` | an interval location's shape unplaced; refused by item 12 where the scene suite is not claimed |
| `claimed_suite_hides_refusals` | a declaration holding a member a claimed suite checks gives no verdict, even where a certain refusal stands beside it, a `population_level` beside no `represents` or another one and a sampled requirement with no `sampling` block among them (a decision, maintainer, 2026-10-24) |
| `item_7_beyond_the_declaration` | item 7 placed where the declaration decides it, one BC-040 a model at its `engine`; unplaced for an engine model over a domain, a crosswalk of `materica/` and the rest of a declared value's shape; a fault inside `engine`, or at a `want` that is no token, unplaced too |
| `token_operating_condition` | a token condition in `operating_conditions` or `region_conditions` is refused at it |
| `families_values` | a `families` value, the family version, is not judged: only the key, a parameter-set field, is |
| `waiver_label_beside_an_unregistered_field` | a waiver's `label` beside a `field` that is not registered, or beside no `field`, is refused by item 4 as well as the field's own fault, or the missing `field`'s: two faults at two members |
| `implied_status_object_pointer` | a status object as an implied condition's value is refused at the member that holds it, `implies/<condition>`, as a target fact's is at `/target/<fact>`: `declarations.md:359` gives the refusal in the target's words and not the pointer, and the ruling of 2026-10-24 on the target's is extended to it |

S7a-1b's clauses (maintainer, 2026-10-24) are on `main`, and the model cites them: a `basis` on a kind but an
extrapolation, a nominal and a distribution is a member the table does not name (`declarations.md:117`), a
`population_level` is held only beside a `represents` of `population`, beside none it too (`declarations.md:109`
and BC-043's row), a waiver of `condition_unknown_name` is refused at its `code` (`declarations.md:118`, BC-048),
a watch's `unit` is S7a-4's, and a refused report holds the declaration and its `consumer`
(`declarations.md:264`). The refusal paragraph's rule that a rule judging one member against another stands
aside where the other is at fault (`declarations.md:156-160`) is applied to the `population_level` rule beside a
`represents` that is no token, a requirement's `field` against a `reads` at fault (an empty one too), a waiver's
missing `condition` beside a refused `code`, and an acceptance of no known kind, refused at itself with none of
its other members judged. Item 7's refusals are one a model, at its `engine`. The rule's text names three
pairs; the model's reading of the others (a combination's fields and a `trainable` entry's beside a `reads` at
fault) is the open point `reads_at_fault`. Main session's overnight answers that bear on the model, logged for
the maintainer: an engine value without `reason` or `basis` is one refusal, BC-040 at `engine`; under a claim of
the sampling suite the build fails closed, where clause 3 would otherwise refuse; a sampled requirement with no
`sampling` block under that claim gives no verdict, not BC-044.

**Agreement with the cases.** `test_cases.py` runs every build-check file, 113 (56 of S7a-1's and 57 of
S7a-2's), under each of the 32 build configurations (build checks and plain read, beside any of the hash, the
fits and reference data suite, the scene suite, USD read and the sampling suite) that its claims allow: XXRUNS
runs. The model agrees with every one of S7a-1's 56 files (1,592 runs), none listed; S7a-2's 58, which pass
their own check, it hands to the results model, which agrees with each (XXRUNS2 runs, "The build's results
model", below). They disagree with none (measured 2026-10-25 on this branch, at `main`'s `60642b3c`). Until
then this model gave no verdict on S7a-2's files, each listed under `past_the_declaration`. No file separates the
configurations but by a label no file compares: each of the 114 gives one answer under all those its claims
allow, but for `hash_not_checked`, which the results of XXHNC of S7a-2's files hold where the hash is not claimed
(measured 2026-10-25), so the XXRUNS runs repeat 114 answers. The sweep is design for HP41's declarations,
which hold a member a suite checks; it is no evidence on these files. What a claimed
suite gives, no verdict whatever else the declaration holds, is held by the direct checks (`direct.py`), not
by a file.

**The direct checks.** `direct.py` holds declarations written there, each with the answer the text or the
maintainer's rulings give, for what no file pins: a waiver's `label` that item 4 and the token rule both
refuse is one refusal (BC-050), as is a status object as a target fact or an implied condition's value; a pick
naming a region or an interval and no `record` is BC-037 under every claim, and one naming a record and a
region is item 12's; a domain, a distribution, an engine and a sampling block, each with its suite claimed and
one other fault, give no verdict, and refuse without the claim (the control); and the model's order of the
cases is the order of the paragraph of `declarations.md` that gives it, read from the text (the model builds a
fault two rules name only as the shape rule beside one other, BC-004, BC-005, BC-044, BC-037 or BC-050; a
reordering of a pair without the shape rule changes no answer it gives, and only that check kills it). They
are the model's own tests, not shared evidence: the seeded faults run against them after the case files, so
that a fault only they tell apart is a kill.

**The mutant table.** `BUILD_MUTANTS` gives the build's model 114 faults, the hand mutants of the model's rules
(a rule none of them names has no fault, and the table is no proof that every rule has one). Each is run against every build-check file by `test_seeded_faults.py` as the read model's are,
against `BUILD_EXCEPTIONS`, and failing those against the direct checks; a fault that makes the model raise
fails its check (its control: the token check replaced by a function raising `TypeError`, `KeyError` or
`AssertionError`). 84 are killed, 50 by a case file and 34 by a direct check alone, and 30 survive: for each
survivor no case file does kill it, and `mutants.py` says why beside it. They are what HP41 and HP42 (S7a-1p)
must kill. Measured over every build-check file, 2026-10-25: none makes the model raise, and 25 die to one
case file alone. Item 7's fault (`build_item_7_pointers_placed`, a fault inside an engine model's `engine`
placed as its own rule's) is killed now that BC-040 is placed, by a direct check, since no case file holds one;
the four survivors the clauses left are killed (`build_basis_on_any_kind` by `BC-048.basis_on_a_waiver`,
`build_condition_unknown_name_taken` by `BC-048.waiver_of_an_unknown_condition_name`,
`build_population_level_beside_any_represents` by `BC-051.population_level_beside_another_represents` and
`BC-051.population_level_without_represents`, and `build_population_level_beside_none_refused_as_shape` by the
latter), and four older ones are killed by the new direct checks (`build_combination_unchecked`,
`build_waiver_condition_missing_taken`, `build_represents_token_unchecked`, `build_engine_over_a_domain_refused`). A fault that over-refuses dies to S7a-2's files too, each of which then gives a refusal its
listing does not. The table says only whether a fault is killed or survives; a test holds it to `mutants.py`.

| Mutant | Fault | Outcome |
|---|---|---|
| `build_array_checked_as_its_first_entry` | a JSON array checked as its first entry | killed |
| `build_refused_text_pointed_at_a_member` | a text not JSON, or not an object, refused at `/` | killed |
| `build_unknown_member_ignored` | a member not named at its place ignored | killed |
| `build_required_member_taken_missing` | a required member missing taken | killed |
| `build_missing_member_pointed_at_itself` | a missing member's refusal at the member, not its parent | killed |
| `build_member_of_another_type_taken` | a member of another JSON type taken | killed |
| `build_empty_list_taken` | an empty list where one entry or more is asked taken | killed |
| `build_exactly_one_unchecked` | none or two of a place's mutually exclusive members taken | killed |
| `build_target_basis_taken` | a target fact holding `basis` taken | killed |
| `build_tokens_compared_without_case` | a token compared without case | killed |
| `build_token_slips_taken` | a token one slip from its member's taken | killed |
| `build_unregistered_condition_taken` | an unregistered operating condition taken | killed |
| `build_review_unchecked` | a requirement's `review` of any string taken | killed |
| `build_want_unchecked` | a requirement's `want` left to the read | killed |
| `build_extrapolation_method_unchecked` | an extrapolation's `method` unchecked | killed |
| `build_waiver_code_unchecked` | a waiver's `code` of any string taken | killed |
| `build_mixing_rule_unchecked` | a mixing rule of any string taken | survives |
| `build_unregistered_label_taken` | a label registered for another field taken | killed |
| `build_families_unchecked` | a `families` entry for a field with no parameter set taken | survives |
| `build_names_given_twice_taken` | a name given twice taken | killed |
| `build_unread_field_taken` | a requirement or `trainable` entry for a field not read taken | killed |
| `build_trainable_location_unchecked` | a `trainable` entry at a location not checked over taken | killed |
| `build_empty_reason_taken` | an empty `reason`, `basis` or `law` taken | killed |
| `build_unit_unchecked` | a unit other than the registered one taken | survives |
| `build_range_order_unchecked` | a `range` upside down taken | survives |
| `build_negative_number_taken` | a tolerance or `fraction_sum_tolerance` below zero taken | survives |
| `build_fractional_index_taken` | a pick's fractional `index` taken | survives |
| `build_combination_unchecked` | a combination unchecked | killed |
| `build_distribution_parameters_unchecked` | a distribution's parameters other than its token's taken | survives |
| `build_repeated_accepts_taken` | a repeated `accepts` token taken | survives |
| `build_params_taken` | a nominal's `params` for a field with no parameter set taken | survives |
| `build_chains_unchecked` | a chain unchecked | survives |
| `build_item_3_unchecked` | a tolerance or accept list without `reason` refused as BC-048 | killed |
| `build_item_3_on_tolerances_alone` | an accept list without `reason` refused as BC-048 | killed |
| `build_item_4_unchecked` | an acceptance without `reason` or `basis` refused as BC-048 | killed |
| `build_basis_unrequired` | an extrapolation, nominal or distribution taken without `basis` | killed |
| `build_basis_unrequired_of_an_extrapolation` | `basis` required of a nominal and a distribution alone | killed |
| `build_basis_required_of_every_kind` | `basis` required of every acceptance | killed |
| `build_location_rule_unchecked` | an acceptance needing a location taken without one | killed |
| `build_accepted_difference_needs_a_location` | an accepted difference refused without a location | killed |
| `build_implied_condition_located_optionally` | an implied condition taken without a location | killed |
| `build_waiver_condition_unrequired` | a waiver's `condition` refused for every code | killed |
| `build_unknown_code_names_a_condition` | a waiver whose `code` is no reason refused without a `condition` | killed |
| `build_label_rule_unchecked` | a label-resting waiver taken whatever its requirement names | killed |
| `build_label_rule_without_review` | a label-resting waiver taken without its requirement's `review` | killed |
| `build_label_refusal_at_the_waiver` | BC-050's refusal at the waiver, not at its `label` | killed |
| `build_item_8_unchecked` | a requirement that samples taken without `min_acceptance` | killed |
| `build_population_level_rule_unchecked` | a population `represents` taken without `population_level` | killed |
| `build_scene_members_taken` | a domain, a path or `region_conditions` taken without the scene suite | killed |
| `build_sampling_members_taken` | a sampling member taken without the sampling suite | killed |
| `build_distribution_taken` | a distribution acceptance taken without the sampling suite | killed |
| `build_represents_taken` | a `represents` taken without the sampling suite | killed |
| `build_claimed_suite_lacking` | a member a claimed suite checks refused as unclaimed | killed |
| `build_item_12_before_item_8` | a requirement item 8 refuses over refused by item 12 too | killed |
| `build_item_12_before_the_population_level_rule` | a requirement the `population_level` rule refuses refused by item 12 too | killed |
| `build_engine_withholds_every_member` | item 7's refusal withholding item 12's refusal of the model's domain | killed |
| `build_item_7_refusal_dropped` | an engine model over records taken | killed |
| `build_item_7_pointers_placed` | a fault inside an engine model's `engine` or `want` placed | killed |
| `build_item_7_values_unread` | a declared engine value without its `reason` or `basis` not read as item 7's refusal of the model | killed |
| `build_item_7_want_unread` | a requirement with a token of `want` other than `value` not read as item 7's refusal of the model | killed |
| `build_item_7_refusal_at_the_value` | item 7's refusal of a declared engine value without its `reason` or `basis` given at the value, beside the model's | killed |
| `build_precedence_reversed` | a fault two rules name carrying the last rule's case | killed |
| `build_every_rule_reported` | a fault two rules name refused under both | killed |
| `build_condition_unknown_name_taken` | a waiver of `condition_unknown_name` taken, though section 4.2 never accepts it | killed |
| `build_condition_missing_beside_a_refused_code` | a waiver of `condition_unknown_name` naming no `condition` refused for the `condition` too | killed |
| `build_basis_on_any_kind` | a `basis` on another kind of acceptance taken | killed |
| `build_population_level_beside_any_represents` | a `population_level` beside another `represents` taken | killed |
| `build_member_faults_refused_apiece` | two faults at one member, one from each rule that names it (a waiver's `label` that item 4 and the token rule both refuse, a `domain` of another JSON type that item 12 and the shape rule both name), given a refusal each | killed |
| `build_missing_members_merged` | the faults at one pointer merged whatever they are about, so that two members missing from one object, or one missing and the object's own, give one refusal | killed |
| `build_status_object_checked_inside` | a status object as a target fact or an implied condition's value checked as an ordinary member, refused at the member and again inside it | killed |
| `build_target_status_object_taken` | a status object as a target fact taken | killed |
| `build_status_object_without_a_reason` | a status object holding a `reason` judged an ordinary member | killed |
| `build_status_object_needing_no_status` | an object holding a `reason` and no `status` taken for a status object | killed |
| `build_target_status_object_with_a_reason_taken` | a status object holding a `reason` as a target fact taken | killed |
| `build_pick_located_at_a_region` | a pick naming a region or an interval and no record taken as located | killed |
| `build_unlocated_pick_refused_by_item_12` | a pick naming a region and no record refused by item 12 beside the location rule, or taken as beyond the model where the build claims the scene suite | killed |
| `build_order_048_before_050` | a fault two rules name carrying the shape rule's case before item 4's and item 12's | killed |
| `build_order_005_before_004` | a fault two rules name carrying item 4's case before item 3's | killed |
| `build_acceptance_at_a_region_taken` | an acceptance at a region taken without the scene suite; both legs pinned by direct checks, a pick naming a record and a region and a waiver at a region (with a record and without), each refused unclaimed and no verdict claimed | killed |
| `build_acceptance_at_an_interval_taken` | an acceptance at an interval taken without the scene suite | survives |
| `build_trainable_at_a_region_taken` | a `trainable` entry at a region or an interval taken without the scene suite | survives |
| `build_claimed_suite_beyond_unrecorded` | a member a claimed suite checks taken as if nothing were beyond the model, so that the declaration's other refusals stand | killed |
| `build_claimed_suite_gives_the_refusals` | a declaration holding a member a claimed suite checks given the refusals of the model's own rules, not no verdict | killed |
| `build_min_acceptance_one_refused` | a `min_acceptance` of 1 refused | survives |
| `build_min_acceptance_zero_taken` | a `min_acceptance` of 0 taken | survives |
| `build_any_difference_refused` | an accepted difference of value `"any"` refused | survives |
| `build_trainable_twice_by_field` | two `trainable` entries for one field at two locations refused | survives |
| `build_engine_over_a_domain_refused` | an engine model over a domain refused by item 7 as certainly as one over records | killed |
| `build_interval_location_placed` | an interval location's shape placed, its BC-048 given as for any member | survives |
| `build_waiver_condition_token_unchecked` | a waiver's `condition` holding any string taken | survives |
| `build_population_level_beside_none_refused_as_shape` | a `population_level` beside no `represents` refused as BC-048, not BC-043 | killed |
| `build_independence_entry_shape_unchecked` | an independence entry's members, required and named, unchecked | survives |
| `build_independence_entry_texts_unchecked` | an independence entry's empty `reason` or `basis` taken | survives |
| `build_sampling_independence_unrequired` | a `sampling` block without `independence` taken | survives |
| `build_space_unchecked` | a distribution's `space` holding any string taken | survives |
| `build_empty_reads_taken` | an empty `reads` taken | killed |
| `build_requirement_judged_beside_a_reads_at_fault` | a requirement's `field` judged against a `reads` at fault as against one that lists nothing | killed |
| `build_combination_judged_beside_a_reads_at_fault` | a combination's fields judged against a `reads` at fault as against one that lists nothing | killed |
| `build_trainable_judged_beside_a_reads_at_fault` | a `trainable` entry's field judged against a `reads` at fault as against one that lists nothing | killed |
| `build_population_level_rule_beside_a_non_token` | the `population_level` rule refusing a `population_level` beside a `represents` that is no token | killed |
| `build_acceptance_of_no_kind_judged` | an acceptance of no known kind refused for its missing `reason` too | killed |
| `build_population_level_rule_refused_under_a_claim` | a requirement the `population_level` rule refuses given that refusal where the build claims the sampling suite | killed |
| `build_missing_sampling_block_refused_under_a_claim` | a requirement that samples with no `sampling` block given item 8's refusal where the build claims the sampling suite | killed |
| `build_consumer_shape_unchecked` | a `consumer` missing a member of `{"name", "version"}`, or holding another, taken | survives |
| `build_model_name_and_version_unchecked` | a `model` missing a member of `{"name", "version"}`, or holding another, taken | survives |
| `build_waiver_condition_missing_taken` | a waiver whose `code` names a condition taken without its `condition` | killed |
| `build_empty_accepts_taken` | an `overlay_scope` accepting nothing taken | survives |
| `build_blank_reason_refused` | a `reason` or `basis` of whitespace alone refused | survives |
| `build_empty_condition_reason_is_item_3` | an empty `reason` on a requirement condition refused as item 3, BC-004, not as BC-048 | survives |
| `build_population_level_shape_unchecked` | a requirement's `population_level` of another shape taken | survives |
| `build_represents_token_unchecked` | a requirement's `represents` holding any string taken | killed |
| `build_waiver_label_beside_an_unregistered_field_not_judged` | a waiver's `label` beside a `field` that is not registered not refused by item 4 | survives |
| `build_precision_unchecked` | a `precision` holding any string taken | survives |
| `build_consumer_parameters_unchecked` | a `consumer_parameters` entry that is no string taken | killed |

The cases cannot show one refusal given twice: refusals are compared as a set, and the model's are a set.

## The build's results model

`build_results_model.py` models what a build gives a declaration that passes its own check (S7a-2): the reads,
the results, the verdict and the report of `declarations.md` sections 2 and 4.2, with the build's terms
(given, applied, located at, covers, used). It was written from the specification's text, with the build-check
case files read as data, before S7a-2's code existed and by an agent that never read the build's code; the two
meet at the case files and at HP43 to HP46's properties (S7a-2p). It takes the declaration's own check from
`build_model.py`, whose no verdict `PAST_THE_DECLARATION` hands the declaration on, and reads through the read
model (`read_model.read`), never through the implementation's read.

**What it decides.** Per model, per record its `checked_over` lists and per field it reads, in that order:
- the request the build gives the read (item 7, with the maintainer's clause of 2026-10-23): the target, the
  declared operating conditions whole, the requirement's `want` and `conditions` alone, and the acceptances of
  the kinds a read takes, overlays aside, that name the field and are located at the record;
- the read, and no read for a field with no requirement, whose result holds `status`, `reasons` and the
  build's members alone (`no_requirement`);
- the build's own reasons (item 8): `label_mismatch` against the label stored on the value the result rests
  on, the field or the alternative read, whether or not the read reached step 12, and none where it rests on
  no stored value; `not_reviewed` where the requirement holds `review` and the result's `provenance` holds no
  completed review, and none where it holds no `provenance`;
- the status, the worst of the read's reasons and the build's, every other member as the read returned it,
  `value` included;
- the acceptances the read applied (the build's terms): an implied condition whose value a condition entry
  shows with basis `implied`, so that two supplying one value are both applied, a nominal or an extrapolation
  the result's `assumption` names;
- the judgement by section 4.2's table, held as the model's own data (`COVERAGE`): `accepted`, `accepted_by`
  (the acceptances that covered a reason and those the read applied, by index in the model's `acceptances`)
  and `not_accepted`; `specimen_differences`, empty, a target of `{}` naming no fact;
- `unused`, per model; the verdict (`Report.refused`: a result not accepted); and the report's `consumer`,
  `records` (each record a read resolved: Open point `record_a_read_resolved`), `declaration`, `refusals` (none), `results` and `unused`.

**What it does not.** `NoVerdict`, never a pass, for each kind its `UNDECIDED` names, each given its reason in
`exceptions.RESULTS_NOT_DECIDED`: a waiver naming a label that would cover a reason by every other test, whose
coverage rests on label trust, which comes after 0.1.0.dev4 (maintainer, 2026-10-21: dev4 is S7a-1 and S7a-2
without label trust); a target naming a fact, or `combinations` (S7a-3); a `trainable` entry (S7a-4); the
report's watches, which it leaves out as a build that does not emit them does, so that a case comparing them
gets no verdict where every member the model decides agrees (S7a-4); a row of section 4.2 that a pick or an
overlay alone reaches (S7c); the alternative a result rests on, where the result names none and the
alternatives store different labels; and a read the read model gives no verdict on. A pick, an overlay or a member a claimed suite checks gives no verdict at the
declaration already (`build_model.py`).

**Section 4.2's table.** `main` has no `coverage.json` yet (the S7 design's generated table, which S7a-2b
brings), so `test_build_results_model.py` parses the table from `declarations.md` and holds the model's
rows to it, each row's "Covered by" read by a fixed table of the phrasings it uses, so that a new phrasing
fails; its controls rewrite a phrasing, drop `not_reviewed` from its row (the S7-spec review's surviving hand
mutant), change a status, drop a row's condition, add a row and cut a qualifier, and each is found. When
`coverage.json` exists, a test holds it to the model's table: the file names every reason the table lists (the
least that can be said before the generated file's shape is known; S7a-2b's generator and row-by-row
comparison replace it), and a build whose acceptance module exists without the file fails, never skips. One
departure is allowed: `condition_unknown_name` leaves the first row, by the maintainer's ruling of 2026-10-24,
whose words #96 lands; it is unobservable, since no waiver that passes the declaration's own check names the
unregistered condition such a reason carries. The allowance filters the text's first row only while the text
still lists the code there: once #96's words are on `main` the check fails, saying to delete
`RULED_OUT_OF_THE_FIRST_ROW`, and a control shows that without the allowance today's text differs from the
model's row, so that the code put back in the model's row is never hidden by it.

Where the text leaves a point open, the model takes the maintainer's ruling where there is one, else the
reading it states, and gives `NoVerdict` where it cannot decide, each point listed once in its `OPEN_POINTS` and
named where it is applied:

| Open point | The model's choice |
|---|---|
| `label_of_no_stored_value` | a result resting on no stored value is checked against no label; a refusal at step 0 is told by a read of the same request over no records, which gives `absent` exactly where step 0 passes, and one at steps 1 to 6 by a reason only those steps give, or `absent` |
| `alternative_a_result_rests_on` | a result over alternatives rests on one exactly where it holds `conditions`; the alternative its reasons name, or, where none names one, any where every alternative stores the same label, else no verdict |
| `condition_unknown_name_never_covered` | covered by nothing (the maintainer's ruling of 2026-10-24; `main`'s first row lists it until #96's words land) |
| `record_a_read_resolved` | a record a read resolved is the one step 1 found, pinned by `id`, `version` and `content_hash` among the sources (one, or several of identical bytes) on a read that passed step 0, whether or not steps 2 to 5 then refuse it; the text says "resolved" and names no step |

**Agreement with the cases.** With the declaration's own check, the build's models agree with every one of the
108 build-check files under each of the build configurations its claims allow (3,272 runs), none listed:
S7a-1's 51 (1,464 runs) and S7a-2's 57 (1,808 runs), and disagree with none (measured 2026-10-25 on this
branch). `BUILD_EXCEPTIONS` is empty; until this piece it listed S7a-2's 57 under `past_the_declaration`. The
comparison is the specification's README's for a build-check case (`cases.py`): results as a set keyed by
model, location and field, both ways, each result's members as a read result's are, `accepted_by` as a set,
`not_accepted` as a multiset, and `unused` as a set; its controls (`test_cases.py`) find a result missing,
given twice or of another model, and an `accepted`, `accepted_by`, `not_accepted`, `value`, `reasons` or
`unused` that differs.

**The direct checks.** `results_direct.py` holds 40 declarations, most a build-check file's with one thing
changed (a stored record changed in memory where the check needs it, a second source beside it, or a stand-in
for the read model's read), read over the suite's fixtures, each with the answer the text gives, for what no
file pins: R05 (`not_reviewed` beside a read's `not_met` that carries a value), a nominal at another record or
for another field neither given nor applied, an extrapolation given beside the nominal a read applied, two
implied conditions that agree, one whose token the specimen does not state (applied too: the text adds no
condition on the specimen) and one naming two conditions, no `label_mismatch` past step 0's `want_mismatch`
or `request_incomplete` or past a record refused at steps 2 to 5 (`other_version`, `malformed`,
`unknown_type`), a label that differs in case alone, the one alternative left checked against its own label,
and, among labels that differ, left unnamed (no verdict), no `not_reviewed` under `no_pick`, the verdict over
two models in either order, acceptances and models permuted, the report's `records` (a record listed once for
two models, none for a read refused at step 0, a pin no source holds or two sources of different bytes hold,
and the record refused at steps 2 to 5, listed), a waiver resting on a label (no verdict where it would cover,
decided where its record, code or condition differ), a waiver located at another `id` or `version` of the
record, an extrapolation at another record, the read model's no verdict on either read the model makes (by a
stand-in, since no build-check fixture reaches the read model's own), and the later pieces' no verdicts, in
the first model and in the second.

**The mutant table.** `RESULTS_MUTANTS` (`results_mutants.py`) gives the results model 79 faults, one or more
per rule, among them each of the S7 design's HP43 to HP46 lists (6.5's table) the model holds, under R01 to
R07 the faults of the case writer's build. The label-trust faults of those lists (`_trusted`, `_label_rests`)
wait for label trust. Each runs against every build-check file and, failing those, the direct checks; a fault
that makes the model raise fails its check (its control: the judgement replaced by a function raising). 75 are
killed, 45 by a case file and 30 by a direct check alone (R05 among them, which no case file catches), and 4
survive, each with why beside it in `results_mutants.py`: three are faults no declaration that passes its own
check can show, and one (`results_numbers_compared_by_equality`) is a comparison of a signed zero that the
text does not settle, for S7a-2p and the maintainer. Measured over every build-check file, 2026-10-25: none
makes the model raise, and 11 die to one case file alone. The table says only whether a fault is killed or
survives; a test holds it to `results_mutants.py`.

| Mutant | Fault | Outcome |
|---|---|---|
| `results_acceptance_at_another_record_given` | an acceptance a read takes given to the read of another record | killed |
| `results_acceptance_of_another_field_given` | an acceptance a read takes given to the read of another field | killed |
| `results_waivers_given` | an acceptance of a kind a read does not take (a waiver) given to the read | killed |
| `results_requirement_label_given` | the requirement given whole, its `label` and `review` with it (so `request_incomplete`) | killed |
| `results_unnamed_operating_condition_dropped` | an operating condition the requirement does not name left out of the request (a table's axis) | killed |
| `results_want_defaulted` | the request's `want` defaulted to `value` | killed |
| `results_label_read_from_the_result` | the label stored read from the result's labels, which a refusal before step 12 hides | killed |
| `results_label_checked_on_no_stored_value` | a result that rests on no stored value (its record or field not found, or no single alternative) checked against a value holding no label | killed |
| `results_label_checked_past_step_0` | a read refused at step 0 checked against the field's label | killed |
| `results_label_of_the_field_holding_alternatives` | the label checked against the field holding the alternatives, not the alternative read | killed |
| `results_label_of_the_section` | the label read from the section holding the field, not the field's | killed |
| `results_any_stored_label_matches` | a stored label that differs taken as the one required | killed |
| `results_label_compared_without_case` | a stored label that differs from the one required in case alone taken as the one required | killed |
| `results_absent_label_matches` | a label absent from the value the result rests on taken as the one required | killed |
| `results_not_checked_with_a_reason_reviewed` | a review `not_checked` with a `reason` taken as completed | killed |
| `results_not_reviewed_without_provenance` | `not_reviewed` given to a result that holds no `provenance` (R04) | killed |
| `results_not_reviewed_unrequired` | `not_reviewed` given where the requirement holds no `review` | killed |
| `results_not_reviewed_as_not_met` | `not_reviewed` making the status `not_met` | killed |
| `results_build_reasons_leave_the_status` | the build's own reasons leaving the read's status | killed |
| `results_not_reviewed_lowers_not_met` | `not_reviewed` making the status `unknown` over a read's `not_met` (R05) | killed |
| `results_best_status` | the status the best of the reasons | killed |
| `results_value_dropped_by_the_build` | the read's `value` dropped where the build's `label_mismatch` makes the result `not_met` | killed |
| `results_unrequired_field_read` | a field in `reads` with no requirement read as if wanted as a value | killed |
| `results_given_counted_applied` | every acceptance given counted applied (an implied condition that filled nothing, an extrapolation at an `at_edge` read) | killed |
| `results_implied_applied_only_where_the_specimen_states_it` | an implied condition that filled a condition counted applied only where the field's specimen states its fact and token | killed |
| `results_implied_value_of_the_first_entry_supplied` | an implied condition's value taken from its first `implies` entry, whatever the condition an entry names | killed |
| `results_numbers_compared_by_equality` | JSON compared by `==`, so that an implied condition supplying `-0` fills a condition showing `0` | survives |
| `results_extrapolation_applied_under_any_assumption` | a given extrapolation counted applied whenever the result rests on an `assumption`, a nominal's too | killed |
| `results_implied_filled_whatever_the_basis` | an implied condition counted applied where an entry holds its value with a basis other than `implied` | killed |
| `results_first_implied_only` | of two implied conditions that agree, the first alone counted applied | killed |
| `results_applied_indexed_among_the_given` | an applied acceptance indexed among those given, not in the model's `acceptances` | killed |
| `results_assumption_named_by_kind` | an `assumption` taken to name every acceptance of its kind | survives |
| `results_applied_uncited` | `accepted_by` without the acceptances the read applied | killed |
| `results_waiver_covers_not_met` | a waiver covering a reason no row of section 4.2 lists for it (`condition_outside`, `form_invalid`) | killed |
| `results_waiver_condition_ignored` | a waiver covering a condition reason whatever condition it names | killed |
| `results_waiver_code_ignored` | a waiver covering a reason of its row whatever code it names | killed |
| `results_waiver_field_ignored` | an acceptance covering a reason of a result whatever field it names | killed |
| `results_location_ignored` | an acceptance covering a reason of a result whatever record it names | killed |
| `results_located_by_id_alone` | an acceptance located at a record by its `id` alone (R06) | killed |
| `results_located_ignoring_the_version` | an acceptance located at a record by its `id` and `content_hash`, its `version` ignored | killed |
| `results_located_ignoring_the_id` | an acceptance located at a record by its `version` and `content_hash`, its `id` ignored | killed |
| `results_region_located_at_a_record` | an acceptance naming a region or an interval beside the record located at that record | survives |
| `results_alternative_reasons_uncovered` | a waiver covering no reason that carries an `alternative` (R07) | killed |
| `results_nominal_covers_without_assumption` | a nominal covering `want_mismatch` where the result's `assumption` does not name it, step 0's among them | killed |
| `results_extrapolation_covers_without_assumption` | an extrapolation covering `outside_range` where the result's `assumption` does not name it | killed |
| `results_extrapolation_covers_at_edge` | an extrapolation covering `at_edge` | killed |
| `results_waiver_covers_label_mismatch` | a waiver naming `label_mismatch` covering it | killed |
| `results_waiver_covers_no_pick` | a waiver naming `no_pick` covering it | killed |
| `results_condition_unknown_name_waivable` | a waiver naming `condition_unknown_name` and its condition covering it | survives |
| `results_label_resting_waiver_trusted` | a waiver naming a label covering as one naming none, whatever the label's trust | killed |
| `results_label_resting_waiver_undecided_anywhere` | a waiver naming a label given no verdict though it covers nothing by the other tests | killed |
| `results_label_resting_waiver_undecided_before_its_code` | a waiver naming a label given no verdict before its code is tested against the reason's | killed |
| `results_label_resting_waiver_undecided_before_its_condition` | a waiver naming a label given no verdict before its condition is tested against the reason's | killed |
| `results_another_model_s_acceptances` | a model's reason covered by another model's acceptance (R02) | killed |
| `results_covered_reasons_not_accepted` | `not_accepted` holding a covered reason | killed |
| `results_acceptance_covering_nothing_cited` | `accepted_by` holding an acceptance of the result's field at its location that covered nothing | killed |
| `results_build_reasons_unjudged` | the build's own reasons left out of the judgement, so a `label_mismatch` refuses nothing | killed |
| `results_status_raised_when_accepted` | an accepted result's status made `met` | killed |
| `results_specimen_differences_left_out` | a result without `specimen_differences` | killed |
| `results_unused_lists_the_applied` | an acceptance the read applied, and that covered nothing, listed in `unused` | killed |
| `results_unused_named_after_the_first_model` | each acceptance unused named after the first model (R01) | killed |
| `results_unused_shared_by_the_models` | one set of used acceptances shared by every model (R03) | killed |
| `results_used_listed_unused` | every acceptance listed in `unused`, used or not | killed |
| `results_every_record_of_the_store_read` | every record in the store read, listed or not | killed |
| `results_one_result_a_field` | the results de-duplicated by field alone | killed |
| `results_refused_by_the_first_model` | the verdict read from the first model's results alone | killed |
| `results_never_refused` | no refusal while a result is not accepted | killed |
| `results_unresolved_record_listed` | a record listed in `records` though its read resolved none | killed |
| `results_unread_record_listed` | a record listed in `records` though nothing was read for it (a field with no requirement) | killed |
| `results_later_pieces_decided` | a target naming a fact, combinations or a `trainable` entry decided as if absent | killed |
| `results_found_before_the_field_by_absent_alone` | a read refused at steps 1 to 6 for a reason other than `absent` taken to have found the field | killed |
| `results_other_version_taken_to_find_the_field` | a record refused as `other_version` taken to have found the field, its label checked | killed |
| `results_malformed_taken_to_find_the_field` | a record refused as `malformed` taken to have found the field, its label checked | killed |
| `results_unknown_type_taken_to_find_the_field` | a record refused as `unknown_type` taken to have found the field, its label checked | killed |
| `results_later_pieces_of_the_first_model_alone` | a target naming a fact, combinations or a `trainable` entry looked for in the first model alone | killed |
| `results_unnamed_alternative_decided_as_none` | the alternative a result rests on, where none is named among labels that differ, taken to be none | killed |
| `results_unnamed_alternative_decided_as_the_first` | the alternative a result rests on, where none is named among labels that differ, taken to be the first | killed |
| `results_read_without_a_verdict_decided` | a read the read model gives no verdict on taken as a read that gives no reason | killed |
| `results_step_0_read_without_a_verdict_decided` | the read over no records, to tell step 0, that the read model gives no verdict on taken as passing | killed |

## Running

```sh
uv run pytest tests/reference -n 6
```

The whole directory runs in about a minute and a half on eight workers (57 s, 2026-10-22; 61 s with the
build's model, 2026-10-24; 64 s with its direct checks and 100 faults, 69 s with 104, 2026-10-24; 66 s with 114,
2026-10-25; XXTIME with the results model, its direct checks and 63 faults, with S7a-2's files read past the
declaration, on a machine shared with other sessions, 2026-10-25), the mutant searches most of it: a survivor's
search reads every case file under every configuration it allows, about 6 s alone.
