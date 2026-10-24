# The reference model

A test-only model of a read of one field of one record (`docs/specification/read_side_contract.md` sections 1
to 3), written from the specification's text alone, for the conformance cases, HP12 and the fuzz targets (the
S2 design's SQ49), as S3 keeps a test-only reference evaluator; and beside it the build's model of a
declaration checked on its own (`declarations.md` section 1, S7a-1), written from the text by an agent that
did not read the build's code ("The build's model", below). Neither ships, and neither imports anything from
`materica`, at any depth.

| File | What it holds |
|---|---|
| `strict_json.py` | strict JSON (`record_format.md` section 1 item 6), RFC 8785 and the content hash (section 9), from the standard library |
| `read_model.py` | the model: the text's tables, steps 0 to 13, the result, `list_records` and `content_hash`; its open points in `OPEN_POINTS` |
| `build_model.py` | the build's model of the declaration's own check: its shape table, written from the text, its refusals by case and pointer under the precedence rule, and `NoVerdict` past it; its open points in its own `OPEN_POINTS` |
| `cases.py` | every case file of a read run through the model, and every build-check file through the build's model, under every configuration of claims it allows, and compared |
| `exceptions.py` | the case files each model does not agree with, by kind, each kind with its reason: today, reads outside the read model's scope and build-check files past the declaration, on which each gives no verdict |
| `test_cases.py` | the read model agrees with every case file of a read, and the build's model with every build-check file, or the case file is listed under its kind |
| `test_tables.py` | each model's tables against the generated vocabulary, so that a drift of either fails |
| `test_citations.py` | each quote the models, and the table evaluator beside them, cite is at the line it cites; each open point is listed once and named where it is applied |
| `test_layering.py` | the models and the table evaluator reach no `materica` module, by the imports they write or in a fresh interpreter |
| `mutants.py`, `test_seeded_faults.py` | seeded faults of each model, each killed by a case file or listed as a survivor with its reason; not named `test_*mutants*`, since they are no Hypothesis search and run on every Python (`tests/conftest.py`, `PROPERTY_CONTROLS`) |

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
`consumer`. **What it does not.** A declaration that passes its own check gives `NoVerdict`: what the build
gives after reading is S7a-2's to S7a-4's, a pick or an overlay S7c's. So does a declaration holding a member a
suite the build claims checks further (the scene suite, USD read, the sampling suite). Three rules give
refusals it does not place: item 7's (BC-040), at pointers the text does not fix; an interval location's shape,
which the text does not give; and an engine's declared values, which its crosswalk shapes. A refused report
names them, and a case compares it only where `compare.rules_compared` leaves them out, as BC-051's two engine
files do; else it is no verdict, never a pass.

Where the text leaves a point open, the model takes the maintainer's ruling where there is one, else the
fail-closed choice, each listed once in its `OPEN_POINTS` and named where it is applied:

| Open point | The model's choice |
|---|---|
| `what_one_fault_is` | a member missing that a rule and the shape rule both name is one fault, carrying the first rule's case; a member breaking two constraints is two faults, each refused (a waiver's `label` registered for another field and not named by its requirement gives BC-050 and BC-048 at that `label`) |
| `exactly_one_of` | a place holding none, or more than one, of the members it takes exactly one of is at fault at its own pointer, as for a missing member |
| `acceptance_of_an_unknown_kind` | its `acceptance` refused, its `reason` required as every acceptance's, its other members not judged |
| `member_judged_beside_a_faulty_one` | a member whose allowed values depend on another member at fault (a label beside an unregistered field, an implied condition's `token` beside an unknown fact, ...) not judged |
| `pick_located_at_a_region` | a pick's location members are `record`, `region` and `interval`; one naming a region or an interval alone is located |
| `combination_sections` | a combination's fields are from pairwise different sections |
| `chain_ends` | a chain's `from` and `to` hold `family`, a string, and `record`, a material reference; `state_mapping` maps names to strings |
| `independence_fields` | an independence entry's `fields` each name a registered field and one location, as a `trainable` entry does |
| `accepted_difference_basis` | an accepted difference's `value` may hold `basis` (`stated` or `inferred`) and `inferred_from` |
| `trainable_location_in_a_scene` | whether a region or an interval lies in its model's domain or path is the scene suite's (unplaced); over records neither does, nor does a record over a domain or a path |
| `interval_location` | an interval location's shape unplaced; refused by item 12 where the scene suite is not claimed |
| `item_7_pointers` | BC-040 unplaced: certain over records or a path, or with a crosswalk outside `materica/` that no case passes, else unknown; a fault inside `engine`, or at an engine model's requirement's `want`, unplaced too |
| `basis_on_other_kinds` | a `basis` on another kind of acceptance refused as a member not named there (BC-048) |
| `population_level_beside_another_represents` | a `population_level` beside another `represents`, or beside none, refused at it by the `population_level` rule (BC-043), item 12 then refusing neither member of that requirement |

The maintainer's five clauses of 2026-10-24 land with S7a-1b's first commit (`25d8625b` on its branch), after
this branch's base. The model follows their landed words: a `basis` on another kind is refused ("no other kind
holds it", that commit's line 117), a `population_level` beside another `represents` is the `population_level`
rule's (its lines 64 and 109, and BC-043's row), a waiver of `condition_unknown_name` is refused at build by no
rule (it leaves section 4.2's first row: S7a-2's coverage, not the declaration's shape), a watch's `unit` is
S7a-4's, and a refused report holds the declaration and its `consumer` (its lines 259 to 261). The last two
open points become citations once that commit is on `main`; it also moves the lines of `declarations.md` after
its report paragraph by two, and those after section 4.2's opening by three, and the model's citations of
section 4 with them.

**Agreement with the cases.** `test_cases.py` runs every build-check file, 108 (51 of S7a-1's and 57 of
S7a-2's), under each of the 32 build configurations (build checks and plain read, beside any of the hash, the
fits and reference data suite, the scene suite, USD read and the sampling suite) that its claims allow: 3,272
runs. The model agrees with every one of S7a-1's 51 files (1,464 runs), none listed, and gives no verdict on
S7a-2's 57, each listed under `past_the_declaration`. It disagrees with none (measured 2026-10-24 on this
branch, at `main`'s `8c423d9b`).

**The mutant table.** `BUILD_MUTANTS` gives the build's model one fault per rule, each run against every
build-check file by `test_seeded_faults.py` as the read model's are, against `BUILD_EXCEPTIONS`; a fault that
makes the model raise fails its check (its control: the token check replaced by a function raising
`TypeError`, `KeyError` or `AssertionError`). 64 faults: 46 killed, 18 survive, each survivor a rule no case
pins, which HP41 and HP42 (S7a-1p) must kill. Measured over every build-check file, 2026-10-24: none makes the
model raise, and 22 die to one file alone. A fault that over-refuses dies to S7a-2's files too, each of which
then gives a refusal its listing does not.

| Mutant | Fault | Case files that kill it |
|---|---|---|
| `build_array_checked_as_its_first_entry` | a JSON array checked as its first entry | 1, `BC-048.json_array` |
| `build_refused_text_pointed_at_a_member` | a text not JSON, or not an object, refused at `/` | 3 |
| `build_unknown_member_ignored` | a member not named at its place ignored | 2 |
| `build_required_member_taken_missing` | a required member missing taken | 13 |
| `build_missing_member_pointed_at_itself` | a missing member's refusal at the member, not its parent | 13 |
| `build_member_of_another_type_taken` | a member of another JSON type taken | 1, `BC-048.member_of_another_type` |
| `build_empty_list_taken` | an empty list where one entry or more is asked taken | 1, `BC-048.empty_checked_over_records` |
| `build_exactly_one_unchecked` | none or two of a place's mutually exclusive members taken | survives: no case holds none or two |
| `build_target_basis_taken` | a target fact holding `basis` taken | 1, `BC-048.target_fact_holding_basis` |
| `build_tokens_compared_without_case` | a token compared without case | 1, `BC-048.review_in_another_case` |
| `build_token_slips_taken` | a token one slip from its member's taken | 3 |
| `build_unregistered_condition_taken` | an unregistered operating condition taken | 1, `BC-048.operating_condition_not_registered` |
| `build_review_unchecked` | a requirement's `review` of any string taken | 2 |
| `build_want_unchecked` | a requirement's `want` left to the read | 1, `BC-048.want_slip_values` |
| `build_extrapolation_method_unchecked` | an extrapolation's `method` unchecked | 1, `BC-048.extrapolation_method_linear` |
| `build_waiver_code_unchecked` | a waiver's `code` of any string taken | 1, `BC-048.waiver_code_not_a_reason` |
| `build_mixing_rule_unchecked` | a mixing rule of any string taken | survives: no case declares `mixing` |
| `build_unregistered_label_taken` | a label registered for another field taken | survives: the one such waiver's file compares BC-050 alone |
| `build_families_unchecked` | a `families` entry for a field with no parameter set taken | survives: every `families` is empty |
| `build_names_given_twice_taken` | a name given twice taken | 4 |
| `build_unread_field_taken` | a requirement or `trainable` entry for a field not read taken | 2 |
| `build_trainable_location_unchecked` | a `trainable` entry at a location not checked over taken | 1, `BC-048.trainable_record_not_checked_over` |
| `build_empty_reason_taken` | an empty `reason`, `basis` or `law` taken | 1, `BC-048.empty_reason` |
| `build_unit_unchecked` | a unit other than the registered one taken | survives: no case gives one |
| `build_range_order_unchecked` | a `range` upside down taken | survives: no case gives one |
| `build_negative_number_taken` | a tolerance or `fraction_sum_tolerance` below zero taken | survives: no case gives one |
| `build_fractional_index_taken` | a pick's fractional `index` taken | survives: every pick's index is whole |
| `build_combination_unchecked` | a combination unchecked | survives: every `combinations` is empty |
| `build_distribution_parameters_unchecked` | a distribution's parameters other than its token's taken | survives: the one distribution's are its token's |
| `build_repeated_accepts_taken` | a repeated `accepts` token taken | survives: the one `overlay_scope` accepts one member |
| `build_params_taken` | a nominal's `params` for a field with no parameter set taken | survives: every nominal holds `value` |
| `build_chains_unchecked` | a chain unchecked | survives: every `chains` is empty |
| `build_item_3_unchecked` | a tolerance or accept list without `reason` refused as BC-048 | 3 |
| `build_item_3_on_tolerances_alone` | an accept list without `reason` refused as BC-048 | 2 |
| `build_item_4_unchecked` | an acceptance without `reason` or `basis` refused as BC-048 | 8 |
| `build_basis_unrequired` | an extrapolation, nominal or distribution taken without `basis` | 17 |
| `build_basis_unrequired_of_an_extrapolation` | `basis` required of a nominal and a distribution alone | 8 |
| `build_basis_required_of_every_kind` | `basis` required of every acceptance | 82 |
| `build_location_rule_unchecked` | an acceptance needing a location taken without one | 6 |
| `build_accepted_difference_needs_a_location` | an accepted difference refused without a location | 2 |
| `build_implied_condition_located_optionally` | an implied condition taken without a location | 1, `BC-037.implied_condition_without_location` |
| `build_waiver_condition_unrequired` | a waiver's `condition` refused for every code | 74 |
| `build_unknown_code_names_a_condition` | a waiver whose `code` is no reason refused without a `condition` | 1, `BC-048.waiver_code_not_a_reason` |
| `build_label_rule_unchecked` | a label-resting waiver taken whatever its requirement names | 2 |
| `build_label_rule_without_review` | a label-resting waiver taken without its requirement's `review` | 1, `BC-050.requirement_without_review` |
| `build_label_refusal_at_the_waiver` | BC-050's refusal at the waiver, not at its `label` | 2 |
| `build_item_8_unchecked` | a requirement that samples taken without `min_acceptance` | 1, `BC-051.represents_without_sampling` |
| `build_population_level_rule_unchecked` | a population `represents` taken without `population_level` | 1, `BC-051.population_without_level_beside_sampling` |
| `build_scene_members_taken` | a domain, a path or `region_conditions` taken without the scene suite | 4 |
| `build_sampling_members_taken` | a sampling member taken without the sampling suite | 4 |
| `build_distribution_taken` | a distribution acceptance taken without the sampling suite | 1, `BC-051.distribution_acceptance` |
| `build_represents_taken` | a `represents` taken without the sampling suite | 1, `BC-051.represents_beside_sampling` |
| `build_claimed_suite_lacking` | a member a claimed suite checks refused as unclaimed | survives: each BC-051 file denies the suite it needs |
| `build_item_12_before_item_8` | a requirement item 8 refuses over refused by item 12 too | 1, `BC-051.represents_without_sampling` |
| `build_item_12_before_the_population_level_rule` | a requirement the `population_level` rule refuses refused by item 12 too | 1, `BC-051.population_without_level_beside_sampling` |
| `build_engine_refused_beside_item_7` | an engine model item 7 refuses refused at its `engine` too | 2 |
| `build_engine_withholds_every_member` | item 7's refusal withholding item 12's refusal of the model's domain | 1, `BC-051.engine_over_domain` |
| `build_item_7_refusal_dropped` | an engine model over records taken | 1, `BC-051.engine_over_records` |
| `build_item_7_pointers_placed` | a fault inside an engine model's `engine` or `want` placed | survives: no case holds one |
| `build_precedence_reversed` | a fault two rules name carrying the last rule's case | 17 |
| `build_every_rule_reported` | a fault two rules name refused under both | 17 |
| `build_condition_unknown_name_refused` | a waiver of `condition_unknown_name` refused at its `code` | survives: no case on this branch holds one |
| `build_basis_on_any_kind` | a `basis` on another kind of acceptance taken | survives: no case on this branch holds one |
| `build_population_level_beside_any_represents` | a `population_level` beside another `represents` taken | survives: no case on this branch holds one |

The last three are the 2026-10-24 clauses' rules: S7a-1b's first commit adds a case file for each
(`BC-048.waiver_of_an_unknown_condition_name`, `BC-048.basis_on_a_waiver`,
`BC-051.population_level_beside_another_represents`), which come to this model when that commit is on `main`.
The cases cannot show one refusal given twice: refusals are compared as a set, and the model's are a set.

## Running

```sh
uv run pytest tests/reference -n 6
```

The whole directory runs in about a minute on eight workers (57 s, 2026-10-22; 61 s with the build's model,
2026-10-24), the mutant searches most of it: a survivor's search reads every case file under every
configuration it allows, about 6 s alone.
