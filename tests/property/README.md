# Property tests

Hypothesis properties of the core, in nine groups, of the writer schema, in a tenth, and of the anomaly
check's reader (the last bullet).

- **JSON:** the JSON reader (`docs/specification/record_format.md` section 1 item 6), RFC 8785 (section 9 item
  2) and the content hash (section 9). `strategies.py` builds what they draw: JSON values, texts that write a
  value in many valid ways, and texts holding exactly one fault the specification lists. Trees are drawn
  top-down within a leaf budget, so no draw is thrown away. RFC 8785's property draws names across the
  surrogate range one name in three and negative zero one number in four, which its trees alone held in under
  5% of examples, too seldom for the feature audit at `ci` (below). With them, (9) the one-slip relation
  (`core/slips.py`, section 10), which the read and the name-overlap check share, against a neighbour generator
  written from section 10's list (`test_slip_properties.py`): two names are one slip apart exactly where the
  generator reaches one from the other, by a kind it reaches it by. The generator builds names from a name, as
  the relation compares two, and is the oracle neither shares (the S2a-1 review, verdict 19). Each kind is
  drawn alike, with two slips, unrelated names and two characters swapped far apart as near misses; and, in
  about one in four of the unrelated names and of the two slips not swapped far apart, a name with an empty
  word against the same with `s` or `es` in that word, which is no plural (`pairs_through_an_empty_word`, about
  0.16 of the examples; its floor: Mutants, "The regions held to a floor").
- **Records:** (4) the envelope checks agree with the generated reader schema (section 1 item 2); (5) versions
  order as their integers, for components hundreds of digits long, and a text is a version exactly when it
  matches section 8's pattern; (6) the laws of a read up to step 5 (`read_side_contract.md` sections 1 to 3):
  it never raises but where a step not built yet would decide it, or for claims without plain read, a misuse;
  a reason appears once per code and condition; the order of the sources, identical copies of them, and records
  of another identity (another id, or another version of the target's) change nothing; an unreadable source
  turns only `absent` or `pin_mismatch` into `malformed`; a request member the shape does not name changes
  nothing; and every listed record, read under its own hash, passes steps 1 to 3 and 5. `records.py` builds
  records and versions, `stores.py` stores and requests.

  The first law is checked against the specification only where the read refuses. Where the implementation's
  own `resolve_record` resolves the target, a `NotImplementedError` is allowed, so a resolution that wrongly
  succeeds is invisible to it; the case files and the other laws are the oracle there.
- **Writer schema:** (7) the writer schema (`record_format.md` section 1 item 2) takes every value field the
  specification allows, and refuses each field it forbids by one fault; and it takes every registered field in
  its place, a section's `fields` or an overlay's `replaces`, bound to its row of section 4.1, refusing one
  under a name its section does not register or holding a form, a unit, a label or a composition's basis its
  row does not give, or a specimen fact's unit other than the one its row fixes, a status object included
  (maintainer, 2026-10-15). `value_fields.py` builds the fields from the text alone, never from the schema or
  the bindings it applies: tokens and each field's row from the vocabulary (generated from the specification),
  a specimen fact's members from `provenance.md` section 6.2's JSON shapes, and the rest from the member tables
  and rules each builder cites. A fault is one change the text says breaks a field (a
  member missing, a bound crossed, a token of another member's list or of none, a status token its row does
  not allow, a rule across objects broken, a unit other than the registered one, a field under a name or
  holding what its row does not give), 183 of them in eleven families, the eleventh a table's shape (S3a: a
  member missing or of another type, an axis or a scheme the reader does not know, one knot, a log-log number
  not positive, an edge listed twice, a `source_range` not two numbers, a member the table does not define or
  its reserved `points`, an `axis_unit` other than its axis's, and the axis condition held otherwise than
  `not_applicable`), each drawn as often as another of its
  family on a field, or a body, planned so that its place exists; a family of more than 15 faults is drawn
  in parts of at most 15, each a property of its own, so that the feature audit at `ci` can judge each fault
  (below).
  The refusal is checked on one the schema takes, the same but for the fault, so that it is the fault's.
  And what the writer takes in a body, step 9 of a read passes (the relation its unit bindings exist for):
  a body the text allows passes step 9, and one with every condition and fact, its unit changed at one place
  step 9 compares (the field's, a numeric condition's, a `plus_minus` entry's, a token condition's, a fact's),
  is one the writer refuses, a table's `axis_unit` among the places since S3a.
- **Step 8:** (8) the laws of step 8 of a read (`read_side_contract.md` section 3), in the part step 8
  decides, the S2 design's HP3 and HP5: one fault of a catalogue written from the text gives exactly the codes
  its rule gives, and two faults in two parts of the record give both (each step makes all its checks);
  members the reader does not know, added where they may go, never change the outcome, two slips off a named
  member included. `value_field_strategies.py` builds a record holding one field that passes step 8, a
  constant as often as an interval and a composition together, or evidence, each member its row's shape or a
  status object its row allows, and anything at all in the members a read does not check; and the catalogue,
  by region of the record, each fault with the codes its rule gives: 21 regions since S2a-2's fix round,
  which wrote faults
  for each value step 8 checks, the derivation and `source` included, slips beside a named member or of an
  optional one, and the eleven rules its review found untested; and five of S2b-1's, an interval's, a
  composition's and a component's own members (`interval`, `interval_tokens`, `composition`,
  `composition_tokens`, `component`), whose cross-member rules no schema states (lower above upper, both
  bounds `none`, a component twice, a fraction outside 0 to 1, an empty list, `element:Xx`, a basis the row
  does not allow), with the near misses the text allows (bounds equal, `0` beside `-0`, one bound `none`,
  fractions 0, 1 and `-0`, a component's statistics withheld, a sum no read checks); and four of S2b-2's,
  evidence's (`evidence_list`, `evidence_report`, `evidence_provenance`, `evidence_field`), 36 faults: a list
  empty, a status object, an object or `null`, a report not an object, withheld in part or a withheld report
  holding a member, every report withheld (`withheld`), a member missing, `null`, of another type or a broken
  status object, a year with a fraction, a report's provenance broken as a field's would be, a registered
  condition, with the near misses the text allows (some reports withheld, `entries_withheld` beside a read
  that goes on, which HP3 reads as passing step 8; a member `unstated`; a member beside a standard's status;
  a provenance member a read does not check, or its review, broken; a condition of a name the reader does not
  know, step 10's; statistics beside, which evidence's row does not read). The field region's faults
  on the own member (`value_*`) act on the member of the field's form. A fault of the forms' regions is drawn on
  a field of its form; any other on a field of a form drawn first, evidence only for the shared regions it
  takes (`takes`). HP3 runs in four parts, a property each,
  the 21 regions taken in turn by the first two, S2b-1's five by the third, S2b-2's four by the fourth: each
  draws its first fault's
  region among its own, and the field's form, before the record, so that the feature audit at `ci` can judge
  each region and form (below); the mutant searches draw HP3 whole. A third law, the label's rule, holds a
  label on a table to the Label column, read by the test itself, through step 8's shared check, since no read
  reaches a table before S3. A read is made under the `want` that gives its field's form; one that passes
  step 8 is refused at step 9 or 10, or goes on to steps 11 to 13: either is the outcome "past step 8". HP5
  adds its members at every object of the record but a `conditions` map and a status object, a list's items
  among them (a component, a derivation's input, a report), and declares how often one lands in an interval's
  or a composition's own member, and in an evidence field's reports (`in_a_report`).
- **Steps 9 and 10:** (10) the laws of steps 9 and 10 (`read_side_contract.md` sections 3 and 5), the S2
  design's HP7, HP8 and HP9, and HP3 and HP5 for the part steps 9 and 10 decide
  (`test_condition_properties.py`). HP7: step 10 gives each condition the entry and reason of an oracle
  written from section 5 alone (`condition_oracle.py`, which imports nothing from `core/conditions.py`), on
  the exact rationals the doubles are: each numeric row at each boundary its exactness turns on (an operating
  end anywhere; at `fl(r + t)`; the double next to the exact bound `r + t`, inside it or outside, at ordinary
  magnitudes and among subnormals; a tolerance that is the rounded difference; PR-335's mixed magnitudes, a
  large stated value, a small operating one and a tolerance the double next to their exact difference, at or
  above it or below it; negative zero), each at the lower or the upper end of the stated span, a stated plus
  or minus of each kind, the table's other rows (an accept list holding, beside the row's tokens, a token
  capitalised, a prefix of one and another row's token; a name the reader does not know, held as a value or a
  status object) and the conditions checked, a condition the row requires held by neither the record nor the
  request in about one draw in seven (its floor: Mutants), and implied conditions that fill, never
  override, and disagree.
  Step 10's `met` and `unknown` entries are not returned before S2a-4, so HP7 calls `check_conditions` as the
  read does. HP9: a field's specimen is the section's facts, each overridden by the field's (a dict merge
  written in the test), and an implied condition applies exactly where that merge states its fact and token.
  HP8, end to end through the read: the registered unit passes however escapes write it in the record's text,
  at each place a unit sits (a field's, a condition's, either of two `plus_minus` entries', a fact's in the
  section, the field and a derived value's inputs); any other, equal under NFKC or case folding, or but for a
  space, another registered unit, any text or a status object, gives `unit_mismatch` with its condition, and
  so does any unit on a token condition. HP3: one fault of a catalogue of steps 9 and 10, written from the
  text, on a read every condition of which is stated and met, gives exactly the reasons its rule gives; in one
  draw in four, two faults of two parts of the read give step 9's alone, or two implied conditions that
  disagree alone, or every reason of step 10, its `conditions` returned where one ends the read. HP5: members
  the reader does not know, added to a condition, a `plus_minus` entry, a fact, the request's operating
  conditions, requirement and tolerances, and an implied condition, its record and its values, change nothing,
  the returned `conditions` included. `condition_strategies.py` draws each, its kind first, so that the
  feature audit holds each kind to its draw floor.

  HP7's oracle is a second reading of section 5's rows, written out row by row where the code folds them
  into one test, but not of everything: S2a-3's implementer wrote it after `core/conditions.py`, and it
  repeats three readings the text left open, each the implementer's default in the decision log (section
  "S2a-3 (branch feat/s2a-3)"): a value never agrees with the range `[v, v]` (the entry on two implied
  conditions that "supply different values", now written in section 1 with the fix round's default that `0`
  and `-0` differ); of two implied values that agree, one fills the condition, alike in any order since they
  agree bit for bit (the same entry); and `applied` lists every implied condition that fills, both of two that
  agree (the entry on the result's `applied`). S2a-4's reference model (`tests/reference/read_model.py`, on
  its branch), written from the text by another agent, is to check the three through HP12.

  HP7's boundary kinds reach these sides of their bound, measured over 3,000 derandomised draws a kind
  (2026-10-16, S2a-3's fix round): `one_ulp_inside`, `subnormal_inside` and `mixed_magnitudes_inside` are
  `met` in every draw, and their `_outside` twins `not_met` in every draw, by construction (a draw whose
  window holds no double outside it is built at its other bound, or within the stated span); the property
  asserts it of each example, so that each side is a drawn feature the audit holds to its floor. `anywhere`
  (`met` in 1,625), `at_the_tolerance` (2,747) and `rounded_difference` (2,523) reach both, by where they draw
  and by rounding, and `minus_zero` is `met` but where its edge at `fl(r + t)` rounds outside (2,998).
  Floating point as written disagrees with the exact test in `anywhere`, `at_the_tolerance`,
  `one_ulp_outside`, `rounded_difference` and `minus_zero` (34, 253, 306, 213 and 2 draws), and section 5's
  first row as written, `|r - v| <= t`, also in `mixed_magnitudes_outside` (1,127 of 3,000 value rows): the
  kinds those mutants die at. Which end of the stated span the boundary sits at, and a bound's window, are
  features declared by their chances.
- **The result:** (11) the laws of a read's result (`read_side_contract.md` section 2), the S2 design's HP1,
  HP2, HP6 and HP11 (`test_result_properties.py`), over reads that end at each step S2 builds, the kind drawn
  first (`result_strategies.py`): a record that passes steps 1 to 10, under each `want` of plain read; a
  fault of step 8's catalogue or of steps 9 and 10's; a read that ends before step 4, at step 5 or at step 7;
  alternatives the request meets, or whose list breaks its shape; and, S2b-2's, an interval's read under a
  nominal (`nominal`), five ways drawn first (inside its bounds, on one, the double next past one, under
  `want: bounds`, or where it does not apply: for another field, beside a region, with no location), and a
  nominal for another field before the one applied in half the draws of one that supplies the value. HP1: the
  read gives a result, raising
  `NotImplementedError` for a step not built yet alone, which only step 8's faults reach here; every code is
  the table's, each `(code, condition)` once, `condition` on every `condition_*` reason and on no reason of a
  code that never concerns one. HP2: the status is the worst of the reasons' statuses, which the oracle folds
  from the vocabulary itself, and the members are present as item 6 says (a value with its unit, specimen,
  statistics and provenance exactly where the status is not `not_met` and one value stands; the alternative
  values exactly under `no_pick`; `conditions` beside a value, never under `no_pick` or after a refusal
  before step 10); under a nominal, an oracle of its own (`declarations.md` section 4.1): inside or on the
  bounds, compared exactly, the nominal's value and `assumption` beside `want_mismatch` and `not_met`, and
  `applied` its index; one double outside, `nominal_invalid` in place of `want_mismatch`, no value and
  nothing applied; under `want: bounds` or located elsewhere, the read as without it. HP6: what a read
  returns of a met constant, interval, composition or evidence under the
  `want` that gives it (its form drawn first: a constant as often as two of the others), or of each
  alternative under
  `no_pick`, equals the stored member, an interval's `none` bound a status object, a composition's components
  and stated sum as stored, evidence's reports with their statuses and their provenance whole, the members the
  version defines at every depth (a report's provenance as the writer schema writes it, not as a result's
  `provenance` is cut), numbers bit for bit and status objects as status objects, holding the members
  the generated `TypedDict`s define (the oracle walks the shapes itself, never the reader's filter), each
  count and index an integer, the review as `provenance.md` section 2 item 6 reads it; and emptying what a
  result returns, its JSON or its members, changes neither a later JSON of it nor a later read of the same
  store. Its draws give the field a value of `-0` in one in four, each way a review reads in one in three,
  and a member the reader does not know in its statistics block, a fact or a condition in one in two, each
  declared by its chance; a second HP6 property holds a nominal's value, its kind and `applied` as the
  request writes them, a double bit for bit. HP11: without the hash suite, `hash_not_checked` marks exactly a
  read that reached
  step 4, which the draw knows, and the two reads differ by that label alone. Step 10's faults that leave the
  read to go on (`unchecked`, `unstated`, `unknown_name`, `uncertain`) are a kind of their own, beside a token
  the request does not accept in half its draws, so that a result holds reasons of both statuses; a read of
  every kind is, first, in about one draw in seven, this kind's whose one fault is `unchecked`, the kind's own
  draws giving `unchecked` half as often as each other fault (its floor: Mutants); step 8's
  kind draws two faults always in half its draws; and HP6 draws a constant's statistics held as the status
  object its row allows in one draw in four (fuzz target 4 found it returned as an empty block).
- **The reference model:** (12) the S2 design's HP12 (`test_model_properties.py`): the read agrees with the
  test-only reference model (`tests/reference/read_model.py`), given the same sources, request text and
  claims, compared as section 2 compares results (the status; the reasons as a set of their code, condition
  and alternative; the labels as a set; condition entries by name; alternative values in order; every other
  member bit for bit; counts and indexes as the integers rule 5 writes), or both "not yet" (a
  `NotImplementedError`, a no verdict). Five parts, each drawing its kinds first (`model_strategies.py`):
  values and alternatives (a constant, an interval, a composition or evidence, the form drawn first, met as
  drawn, at one of section 5's boundaries as HP7 draws them, or filled by an implied condition, beside another
  section's specimen in one draw in three, under its own `want` in half the draws of a form but a constant's;
  an interval in half its draws under a nominal of one of the result group's five ways, and evidence's unit in
  half its draws a status object with a reason; alternatives of one form met, broken, or refused by a request
  fault, each further one apart from the first beside its own member in one draw in four: its unit spelled
  otherwise, a specimen fact of its own, or a request fault of its own; intervals met in half their draws
  under `want: value` with a nominal located at the read); faults of steps 8 to 10, one or two, step 8's of
  every form it reads; the first two parts draw, after the kind and inside a kind that can hold it, in about
  one draw in seven of each kind of values and one in four of steps 9 and 10, the region each holds to a
  floor, a constant's read under `want: bounds` and a read of steps 9 and 10 whose one fault is `unchecked`
  (Mutants, "The regions held to a floor"); two faults of one of steps 0,
  8, 9 and 10 that give two reasons (the design's B5, a step that stops at its first fault); step 0's
  catalogue of 60 faults and near misses, and six texts that are no JSON, written from `read_side_contract.md`
  section 1 (S2b-2's eight: an acceptance not an object; a nominal's value not a number or missing, its field
  not registered, a slip, two for one field; and the near misses, one for another field, its `basis` and
  `params` anything), and reads that end before step 8; and the rules no case file pins (the model's
  survivors), each
  planted. The known divergences are listed by kind with their reasons and held exactly, failing on any other:
  one step not built that the model decides (an overlay as the target, S4's decision 8; evidence and the
  nominal, which S2b-2 reads, are no divergence any more), found by the implementation's own
  `NotImplementedError` and held to the draw and to what the model gives (a pick, an overlay or a `trainable`
  acceptance in a request, which the implementation raises at, the model gives no verdict on, so neither
  decides; a requirement holding `review` is refused by both, at step 0, as one holding `label` is); and the
  open points on which the two read the text differently, where the model must refuse as it fails closed, and
  the model given the implementation's reading must agree with it: none since the maintainer ruled the last,
  open point 1's record half (`members_of_the_other_kind`: a record condition holding a member of the other
  kind), fail closed (2026-10-19, `provenance.md` section 6.1 item 1), which the implementation now refuses.
  It is planted still, and so are open point 1's request half (an implied value holding a member of the other
  kind's shape; the token ruling, 2026-10-18) and a slip of a name a declaration gives a requirement
  (`names_a_declaration_gives_a_requirement`, which the text decides: S2a-4's review, approved 2026-10-18),
  and the two must agree on each. Can-fail controls of the check itself: `test_model_controls.py`, an open
  point's on open point 1's record half as the implementation read it before its ruling.
- **What a read must not look at:** (13) the S2 design's HP4 and HP10 (`test_invariance_properties.py`,
  `invariance_strategies.py`). HP4: a fault in another field, registered or not, or in another section's
  specimen never changes a read (the oracle, the read of the record without it); one in the read field's own
  section's specimen refuses it, `form_invalid` or `unknown_token` alone. Both read a constant, an interval, a
  composition or evidence, a constant as often as two of the others, and the audit holds each form to its
  chance.
  HP10: sources and request written
  again, members reordered and whitespace, escapes and number spellings drawn, give the original's result,
  compared as section 2 compares; sources identical byte for byte are written again alike, since two copies
  of a pin whose bytes differ are another read.
- **Information monotonicity:** (14) the maintainer's "more checks of the same kind" (2026-10-14): the
  fail-closed spike's relations S2's forms reach, each a property (`test_monotonicity_properties.py`), over a
  world on the spike's grids, half cooperative, and one change (`monotonicity_strategies.py`): N1r, N2, N3r,
  N4, N5r, N6, N8 (information lost never helps), P1 to P4 (added never hurts), S1 and S2 (must degrade) and
  S5 (section 5's rows on the exact values), restricted as the spike's limits say. N7r, P5 to P7, S3 and S4
  speak of tables, picks and alternatives set aside: S3's and S4's. Where a fault's trigger is rare on random
  worlds, a relation draws its way first, a world the read meets with the trigger built in; each relation
  holds, applied with a verdict on both sides and not vacuous, in a declared least share of its examples.
  N1r's and N3r's ways include the shapes their restrictions leave out, where the unrestricted twins N1 and N3
  must fail; and the worlds every relation draws are audited for the same shapes, by their chances: an
  implied condition that fills a condition of the field, and a numeric condition the read leaves unchecked;
  and for a world the read meets, which the cooperative half of the worlds is drawn for.
- **Tables:** (15) the table evaluator (`core/evaluate.py`; `record_format.md` section 6, table items 3 and 4;
  `read_side_contract.md` sections 5 and 7), the S3 design's HP17 to HP19, against an oracle written from the
  text (`test_evaluate_properties.py`). HP17: the evaluator agrees with it over drawn tables and operating
  values, never raising: where each value lies (at an edge, in the readable range, beyond an edge) exactly,
  and the number, the exact value rounded once, bit for bit. HP18: a read at a knot that is no edge, or beyond
  the readable range's end where that is one, gives the stored `y` bit for bit, `-0` included. HP19: the knots
  that bracket a read are the interval the text names and its value lies between their two `y`; and over
  monotone `y` with no edge, reads are monotone. `tables.py` draws tables step 8 accepts by choices made first
  (the scheme; the magnitude: ordinary, any double, doubles a few units apart, subnormal, or small multiples
  of the least subnormal, where a log-log table follows `y = c / x` at its knots, so that about 40 of its
  reads in a run at `ci` lie halfway between two doubles, where Hypothesis's draws alone reached about two;
  edges; signed zeros; and a `source_range` absent, narrower, within one interval, wider, across an end, or of
  one point), drawing only what the table needs, and reads each at every place table item 3 tells apart: each
  knot and edge, the readable range's ends and `source_range`'s, the double either side of each, both zeros, a
  value inside each interval with room, one beyond each end of the readable range, and the largest doubles.
  Each property first checks its table against the text's rules (`accepted`), a check that found two faults of
  the generator while it was written; its control is a table for each rule step 8 refuses. The oracle compares
  as fractions, finds a read's interval by scanning every pair of knots, and computes in another arrangement:
  a linear value exactly, and a log-log one in decimal at 100 digits, rounded at once where an error bound
  shows that rounding is the value's, and near a point halfway between two doubles deciding over prime factors
  whether the value is that point. It shares no code with the evaluator, which decides rational values over a
  basis found by gcds and bounds the rest by directed rounding; both use the standard library's `fractions`
  and `decimal`. Its own controls: it gives every number and refusal of the table evaluation cases, and the
  exact value at constructed ties, which it misses with its exact decision switched off. HP17 also holds, as
  explicit examples, six reads at log-log values halfway between two subnormals, which its own draws reach.
- **Step 7 over alternatives (S4a):** (16) the laws of step 7 for a field holding alternatives, read with no
  pick and no overlay (`read_side_contract.md` section 3, step 7; `record_format.md` section 5), HP27 to HP29
  (`test_alternatives_properties.py`). `alternatives_strategies.py` draws one of step 7's five outcomes first
  (a refusal, every alternative set aside, the one left, `want_mismatch` and `no_pick`), then a base read of a
  form, and one to five alternatives built to give it, each by a way drawn for its standing: staying as drawn,
  with an `unknown` reason of step 10 or 12, held in the field's other form, or, for evidence, its unit with
  another `reason`; set aside by a numeric condition one double off its operating value or a token the request
  does not accept, in either form where the field takes a constant and an interval, or, for evidence, which
  holds no registered condition, an implied temperature one double off; refusing by a unit, a form token the reader does not know, a missing provenance, or two implied
  conditions that disagree in it alone; in a stored order drawn, under a nominal in half the draws of a field
  that takes intervals under `want: value`. Each way's standing is the text's, so the drawn outcome is the
  draw's, which HP27 asserts of each example. HP27: the read agrees with an oracle written from the text
  that composes the reads of each alternative alone (the record holding it as the field, under the same
  request): each alternative's standing from the `not_met` codes of its own read, by the steps the reason
  table gives each, then the first outcome that applies, its reasons, each found reading one alternative
  carrying its index and a fault of the request none, and its members, an `alternative_values` entry's from
  the alternative read alone under the `want` its form gives, and the `unit` the first staying one's. The
  oracle uses the implementation's own read of a value field, so HP27 holds step 7's composition, not steps
  8 to 13, which the other groups and HP12 hold. HP28: reordering the stored alternatives moves only their
  indexes (the fail-closed spike's P6), and a field wrapped as its only alternative reads as the field, each
  reason found reading it carrying `alternative: 0`, every member the field's where it stays (P5). HP29: an
  alternative set aside, added at any stored index, changes the status never, and the reasons only by its own,
  reported only where the result is `not_met` and rests on no single alternative, and by the indexes past it
  (the spike's N7r, from the other side); two or more alternatives that stay never give `met` (S3). HP12
  draws the same alternatives among its own (`model_strategies.outcomes_of_step_7`), so that the reference
  model and the read meet step 7's outcomes: its audit holds those draws to their floor (`standing`), and
  HP27's audit each outcome among them.
- **The table form through steps 8 and 9 (S3a):** (17) the laws of a table's step 8 and step 9
  (`record_format.md` section 6, table items 1, 2, 4 and 5; `read_side_contract.md` section 3), the S3 design's
  HP13 to HP16 (`test_table_form_properties.py`), over reads of a table steps 8 and 9 pass, drawn by
  `tables.py` on a field whose row allows one, over an axis drawn among the numeric conditions, beside a full
  composition in the record (`table_form_strategies.py`). A table they pass goes on to steps 10 to 13 (S3b-2):
  its outcome is "past step 9", a read that gives no reason of a code step 8 or 9 gives. HP13, in four parts
  drawing their faults first among at most eight (the knots, the edges and a log-log table's signs, the tokens
  and the axis condition, `source_range` and `points`, an empty `x` among them): one fault of a catalogue written
  from the text gives exactly the reasons its rule gives, and a near miss the text allows (an edge at zero held
  as `-0` and `0`, an axis condition with its `reason`, a `source_range` of one point that is no edge) gives
  none, a read that raises being an outcome no rule gives; each base passes, checked after its fault, so that a
  reader that refuses some bases is reported at the fault wherever an example draws it; the fault changes nothing
  of the composition's read, which sits in the density's section; and the fault is its rule's alone: its read
  with what its rule judges undone passes steps 8 and 9 (`JUDGED`: the members put back as the base holds them,
  or removed where it holds none; on a table the fault changed first so that it could exist, without what the
  fault added; only the entry or the value the fault added taken away, where it adds one beside what it judges:
  a log-log table's non-positive values made positive, its scheme kept), so that a fault built to break another
  member too, which most often gives `form_invalid` as the fault does, fails there, or the reader refuses the
  undone table. The three faults that rewrite `x`, `y` and the edges wholesale can only be undone by putting those
  back, and HP13 has no power there against an extra break of them. HP14: a member added to a table more than one
  slip from every member named there, `points` included, changes nothing, and one slip from one, by each kind
  section 10 names, refuses (`form_invalid`). HP15: an `axis_unit` of each kind HP8 draws other than the
  registered one gives `unit_mismatch` with the axis as `condition`. HP16: the row's label on a table is refused
  exactly where its axis is the condition the Label cell names. Each property declares what it draws first as
  drawn, at most eight, so each is held to a draw floor of 50 or more at `ci`. The writer's table family (7),
  T1's table examples (`tests/spec_sync/test_t1.py`) and the reference model, which reads a table to the end as
  the read does (its case files, and the oracle of fuzz target 4; HP12's table part), hold the same rules from
  three other sides.
- **A table read to the end (S3b-2):** (18) the laws of a table's steps 10 to 13 (`record_format.md` section
  6, table items 3 and 4; `read_side_contract.md` section 1, section 3 steps 10 to 13, section 5's first row
  and "The form's range", section 6), the S3 design's HP20 to HP23 and its monotonicity property
  (`test_table_read_properties.py`), over reads of a table `tables.py` draws on a field whose row allows one,
  over an axis drawn among the numeric conditions, its other conditions left unchecked
  (`table_read_strategies.py`), each property drawing first the way its rule tells apart, at most five, so
  that each is held to its draw floor (110 to 245 at `ci`; over 20 runs of 2,000 a size, 40 for HP20 at `ci`,
  measured again with the fix round's draws, 2026-10-21, a way's count varied up to 11.7 times a binomial's, at
  which a correct run fails a floor with a probability of at most 4.8e-8, the audits' model giving 6.1e-7 at
  most; these are estimates, the variances measured over 20 runs bounding them within a factor of 1.9 (one-sided
  95 %), 1.5 over 40: at those bounds the worst is 1e-4, HP20 at `deep`, and HP20 at `ci` 4.4e-7). HP20, at and beside the edges: at an edge inside the readable range,
  `at_edge` with the axis, no value and the axis entry `not_met`; at one outside a narrowed range,
  `outside_range` beside it; one double below an edge reads the interval below and one above the interval
  above, each the value the reference evaluator's `exact` mode gives on that interval alone; beyond an edge
  outside the range or on its end, `outside_range` alone; and step 11's report (`read.form_range`) says no
  extrapolation could cover a read at an edge or beyond one. HP21, at and across the readable range's ends: inside and at an
  end, the axis entry `met` and the evaluator's value; one double outside, far outside, and outside a narrower
  `source_range`, `outside_range` and a report that an extrapolation could cover it; and, a relation, the read
  of a table without `source_range` is the read with one no narrower than `x`'s range and with a tolerance on
  the axis, `table` aside, over tables whose readable range is `x`'s, so that a read its way calls outside
  is outside the table without its `source_range` too. HP22: the table's block, as stored, at a knot and between two; a table holding
  `points`, `points_unsupported` and no block. HP23: no operating value for the axis gives
  `request_incomplete` with the axis, beside the result's `conditions`, and a range of it `want_mismatch`
  alone with the axis, inside the range, across an end, holding an edge or outside. The monotonicity property,
  over a read whose other conditions the request meets, its place drawn as the relation's is: adding a
  `source_range` of any kind `tables.py` draws, or a tolerance on the axis, never turns `unknown` or `not_met`
  into `met`, and a read inside the range is `met`, or `unknown` in the worlds whose field is stated
  without origin (22 to 28 % of them, measured), so that the relation is not vacuous on either half (over a field without alternatives, as
  the S3 design limits it).
  HP1, HP2 and HP11 draw a table read to the end too, in a test function of each beside its own, the family
  first, so that their own draws are as they were; and HP12 in a part of its own, a table among alternatives
  beside the four families. In some of these draws the table holds a member the reader does not know (36 to
  38 %, measured), and, but among alternatives, the field is stated without origin (31 to 34 % of all), whose
  step-12 reason a read step 11 refuses never reaches.
- **An extrapolation (S3c):** (19) the laws of a request's `extrapolation` (`declarations.md` section 4.1;
  `read_side_contract.md` sections 1, 2, 3 and 5), the S3 design's HP24 to HP26 and its monotonicity property
  over an extrapolation (`test_extrapolation_properties.py`, in the `conditions` shard), over HP20 and HP21's
  table reads with the request's acceptances drawn beside them (`extrapolation_strategies.py`): an
  extrapolation's method one of the vocabulary's tokens, its law any text of at least one character, its
  `basis` and `reason` any JSON value or absent. Each property draws first the way its rule tells apart, at most
  five, held to its draw floor (110 to 160 at `ci`; over 20 runs of 2,000 a size, 2026-10-21, a way's count
  varied up to 14.5 times a binomial's, at which a correct run fails a floor with a probability of at most
  4.1e-7, the audits' model giving 6.1e-7 at most; at the variances' one-sided 95 % bounds, 1.9 times those
  measured over 20 runs, the worst is 9.2e-5, HP26's refusals at `deep`'s size). HP24, where the extrapolation
  applies, one double or far outside the readable range, outside a narrower `source_range`, and outside it with
  the value stated without origin, the field holding the `label` its row names for a table over the axis, where
  it names one: adding it keeps the status `not_met` and the reasons the read without it gives, step 12's added
  (`stated_without_origin`), and the labels it gives, step 12's added (the field's `label`), and gives the
  value at the readable range's nearest end,
  the reference evaluator's `exact` value there, the members HP6's oracle gives beside a value, the table as
  stored and `assumption`, its method and law as the request gives them and no `basis`; `applied` names it.
  HP24 where one at the read does not apply, inside the readable range or at an end, at an edge inside or
  outside it, beyond one, and under another `want` of plain read's, `bounds`, `components` or `evidence`: the
  read is the read without it, member for member. HP25:
  one located at another field, record, region or interval, or nowhere, changes nothing; two that name one
  field are `request_incomplete` alone, both at the read, one with no location, or one at a region and one with
  none, in an order drawn, and two that name two fields are read as the one at the read alone, its index in
  `applied`. HP26: a method missing or not a token, a law missing, of another type or empty, each refused,
  located at the read or nowhere; a law of white space alone, `basis` and `reason` of any value and a member
  no document names each read as the extrapolation without them, a member one slip from a named one refused.
  The monotonicity property, over HP21's reads of a table the request can meet: adding an extrapolation at the
  read never turns `unknown` or `not_met` into `met`, and outside the range it applies, its value present, so
  that the relation is not vacuous; its worlds stated without origin are declared by their chance, 0.2 (over 20
  runs at `ci` a mean share of 0.264, the least 0.245; 0.255 and 0.2195 at `deep`'s size). Every draw of the
  strategy is held: each way by its floor, and each draw within one (the method `consumer_law`, a law outside
  ASCII, a `reason`, the order of two, a refused shape with no location, the `want` under which one does not
  apply, the field's `label`, and each kind of value of the lists HP26 draws from: the methods that are no
  token, the laws of white space, the laws that are no text, and a slip's name and the place of its
  character) by a mutant that shows there alone, so that a draw cut to one value leaves a mutant alive.
- **A table among alternatives at step 11 (S4d):** (20) step 7's rows for a table alternative whose read gives a
  reason at step 11 (`read_side_contract.md` section 3, step 7; `record_format.md` section 5 items 2 to 5), HP39 and
  HP40 (`test_table_alternatives_properties.py`, in the `alternatives` shard), over
  `table_alternatives_strategies.py`'s draws: S4a's alternatives, their outcome drawn first among its five and built
  as S4a builds them, over a field that takes a constant, an interval and a table, and beside them a table over a
  condition no other alternative states, stored at an index drawn, by a way drawn second: outside its readable range
  with no extrapolation, over an operating range of its axis, outside under an extrapolation at the read under
  `want: value` (its value stated without origin) and under `want: bounds`; at an edge inside the range, at one outside a
  narrowed range, with no operating value for its axis, and with none but set aside at step 10. Each part,
  `kept_or_set_aside` and `refuses`, draws its four ways, so that each test function draws its first choice among at
  most five, and holds each outcome and each way to the floor of a chance declared below its least share measured:
  0.11 and 0.14, floors of 35 and 60 at `ci`. Over 20 runs of 2,000 a size (2026-10-22), an outcome's count and a
  way's varied up to 13.7 times a binomial's, at which the draw floor of one in five failed a run with up to 1.2e-3;
  at these chances a correct run of a part fails with at most 2.3e-7 at the variance measured (1.6e-4 at its one-sided
  95 % bound). HP39: the read agrees with HP27's oracle, which composes the reads of each alternative alone, with step
  11's standings (a read alone at an edge refuses the field; outside the range, set aside, but where the read alone
  applies an extrapolation, kept; over a range, staying, a form `want` cannot give; `request_incomplete`, refusing,
  with no index), and, under `no_pick`, a kept or over-range table's entry its table as stored, its members and step
  12's labels as a read of it that reaches step 12 gives them; the extrapolation is among what the read applied
  exactly where the table it covers is the one left (`check_applied`, on the result's `applied`, outside its JSON);
  and the draw is what its outcome and way say, by the oracles (`check_drawn`). HP40: the table read inside its range,
  its readable range moved off the operating value by a narrower `source_range` and no edge met, gives the read of the
  field without it, indexes moved, where another stays, and `not_met` with every alternative's reasons, its
  `outside_range` among them, where none does; it never turns a `not_met` read `met`. HP40 draws by chance (no floor),
  over HP39's strategy. HP12 draws the same in a part of its own, the part first. Every draw S4d adds is held: the
  outcome and the ways by their floors, and within a way, the base form a named `want` needs, the others none in the
  form it gives under `want_mismatch`, the extrapolation, the operating range, the absent operating value and the
  token set aside at step 10 by `check_drawn`, the kept table's origin and its label by a mutant each that shows
  there alone, and its stored index by two, one showing where the table is not stored first and one where it is
  not stored last, so that a draw cut leaves one alive; the operating range's upper end, the double above the
  operating value or any double above it, by HP12's mutant `a_range_across_the_readable_end_outside`, which shows
  only where that end lies past the readable range's (HP12's tables below); HP40's three moves of the range by a
  test of each on a table written by hand (`off_the_value`); the others' own draws are S4a's, which S4a's
  properties hold.
- **The anomaly check's reader:** the YAML reader of `scripts/check_anomalies.py` and its specifier syntax
  against PyYAML's `safe_load` and `packaging` (`test_anomaly_reader_properties.py`, in the `agreement` shard).
  A document the reader reads is read as PyYAML reads it; one PyYAML refuses is refused; one inside the subset
  the reader names is read. Documents are drawn whole, with one or two choices outside the subset, with an edit
  to a valid one, and as single plain words, characters, escapes and boolean words; controls run each on a
  reader with one rule weakened. The reader is a gate script that installs nothing, so these are its only tests
  against a second implementation.

The record strategies draw each case the specification tells apart as often as another. An example of (4) is
a sweep: one record changed at each aspect the reader schema checks (removed, of another JSON type, or `null`),
one near miss in each pattern, one other record type, one place left unchecked, and one record changed at
random. Drawn one change at a time, the rarer boundaries came up in under 1% of examples, and a mutant's
search took up to 1,900 examples to meet them. An example of (6) is a store built for one of the cases step 1
tells apart (no copy of the target; one, or two identical or differing, that state the pin; none that does,
beside an ill-formed hash or not), with sources of other identities, unreadable ones and documents beside it,
and claims with plain read or, in one world in four, without it.

## Profiles and sizes

`tests/conftest.py` sets how many examples each property draws, from `MATERICA_HYPOTHESIS_PROFILE`, and
`strategies.SIZE` how large its trees are, from the same profile:

| Profile | Examples per property | Trees | Where it runs |
|---|---|---|---|
| `dev` | 200 | small: 10 scalars, 3 members, depth 5 | the default: locally, and on every Python in CI's test matrix |
| `ci` | 2,000 | small | CI's Hypothesis job, when the core, its schemas and vocabulary, these tests or their configuration change, and on every code change to main |
| `deep` | 20,000 | original: 30 scalars, 5 members, depth 6 | the same job, weekly and on a manual run |

The original size is the one the properties were first written with, or larger. Content is never narrowed:
text is full Unicode half the time and built from the characters the specification treats apart the other
half, and numbers cover every double. Shapes that small trees cannot reach are explicit examples, run under
every profile: nesting 64, 65 and 100,000 deep, objects and records with many members, and a record with every
section and null in each place the envelope checks leave alone. A record with a change planned in a sweep
varies in its structure, its unchecked places holding a few values of each JSON type; the record changed at
random, and every change into a place left unchecked, draw full trees.

Every profile takes Hypothesis's own defaults as its parent, so a machine's environment changes no setting
(`tests/unit/test_hypothesis_profiles.py`). CI therefore draws new examples on every run, as a local run does,
and a run given `--hypothesis-seed` draws there what it draws on any machine. Until #38 it did not: GitHub sets
`CI`, on which Hypothesis loads its built-in `ci` profile at import, and the profiles, registered without a
parent, inherited its `derandomize=True`, which Hypothesis applies before any seed. Every job that ran the
properties drew, for each, the same examples on every run of the same code: the test matrix and the per-commit
job at `dev`, the Hypothesis job at `ci`, and the one `deep` run before #38 (run 39002750375, by hand on
2026-10-17), with that run's fuzz job's replay at `ci`. Every profile also suppresses the `too_slow` health
check, as that built-in profile did on CI: a draw slowed by a loaded runner is not a fault of the code. The
mutant searches, the audits' tests and controls, and T1's variants are derandomised by their own settings, on
purpose.

Every profile keeps its examples in `.hypothesis/examples` at the repository root (git-ignored, cached by CI),
so an example that failed once, under `deep` or any other profile, is tried first on every later run; a
failure prints a blob that replays it anywhere.

## Shards

CI runs the groups in eight shards, the three longest of them, `agreement`, `relations` and `alternatives`, in two parts each
(`--shard agreement_1of2` and `--shard agreement_2of2`, and the same for `relations` and `alternatives`: the shard's tests split in
two parts of about equal time, `tests/partition.py`), so in eleven jobs side by side: `pytest tests/property --shard
json`, which also holds the tables group, `--shard records`, which holds the record and step-8 groups, `--shard writer`, `--shard agreement`, the
two validators' agreement (below), `--shard step8_mutants`, step 8's mutant searches, which keep no example
database and were most of the records shard's time, `--shard conditions`, steps 9 and 10's group and the
result's with their mutant searches, which take seconds and set no example database (112 s on four local
workers at `ci`, 2026-10-16; 155 s with the result's, 2026-10-17; 151 s beside the relations' shard,
2026-10-17), and since S3b-2 a table's steps 10 to 13's mutant searches too, whose properties are in `records`
(about three minutes of CPU at `ci` between them, locally, 2026-10-21), and since S3c an extrapolation's
properties with their mutant searches (`test_extrapolation_*.py`: 143 s of CPU at `ci` for the properties and 5
s for the 66 searches, locally, 2026-10-21, 8 s for the 114 of its fix round; here, not in `records`, which S3b-2's properties brought to 5.4
minutes of its 20 at `ci` on CI), and `--shard relations`, the reference
model's, isolation and byte form's, and monotonicity groups with their mutant searches, each example reading two records or a read twice (198 s on four local
workers at `ci`, 2026-10-17; `SHARDS` in `tests/conftest.py`), and `--shard alternatives`, S4a's step 7 over
alternatives with its mutant searches (122 s on eight local workers at `ci`, 342 s of test time, 2026-10-19;
`relations`, with HP12's draws of S4a's outcomes, took 163 s and 1,036 s after it, under the same lock).
S2b-1's intervals and compositions added 13%
to `conditions` and 7% to `relations`, each timed side by side with the tests before them (475 s against 420,
588 against 549, at loads of 15 to 25), and HP3's third part 51 s of one worker to records (172 s). S2b-2's
evidence and nominals: records 98 s, step8_mutants 65 s, conditions 265 s, relations 516 s, agreement
429 s,
on four local workers at `ci`, run one after another (2026-10-18, at loads of 8 to 11 from other work). Each
family of faults is a property of its own,
run in parallel. The agreement shard's drawn properties run python-jsonschema on every example, and are the
longest tests of any shard: on 4 workers locally (2026-10-17), the shard took 4.0 and 8.0 minutes at `ci`, its
longest property 1.9 and 4.7 (at loads of 4 to 7 and 15 to 17), and 112 minutes at `deep`, its longest
property 70 (load 18 to 30). `deep` has not yet run on CI, whose cores are 1.6 to 4 times slower: there it may
not fit in the 6 hours GitHub gives a job. Each module is in exactly one shard
(`tests/unit/test_source_files.py`), and each shard but step 8's mutant searches' keeps its own example
database in CI.

## The two validators

Every verdict the tests take from the package's JSON Schemas comes from jsonschema-rs (`tests/verdicts.py`),
alone or beside python-jsonschema's (`tests/spec_sync/schemas.py`). `validator` and `agreed`, for tests that
take few verdicts, run both libraries on every value and fail the test with a `Disagreement` where they
differ. `takes` and the writer properties' `Writer`, for loops, give jsonschema-rs's verdict alone;
python-jsonschema gives the messages a failure prints, and fails the test at once where it finds none. Both
read every resource at draft 2020-12. python-jsonschema takes 32 to 120 ms of CPU a field against the writer's
value field, a choice among eight forms, and 6 to 20 ms against the reader's; jsonschema-rs, 0.01 to 0.08 ms
(drawn fields at `ci`'s size and T1's fields, 2026-10-17, at loads of 13 to 22, which move CPU time too).

`test_validators_agree.py`, the `agreement` shard, holds the two to one verdict:
- on T1's inputs (`tests/spec_sync/test_t1.py`): each field against the writer schema and the reader `$defs`,
  by its form's definition and by `value_field`, its section's specimen against both, and the field against
  its row's binding. Every example at `deep`; at `dev` and `ci`, every tenth example of each group (the inputs
  that read one registered field, and the variants of one base by one change and origin), 730 of the 5,383
  (670 of 5,066 before S2b-1 added a full interval and composition to T1's bases),
  which holds each registered field, base, origin and change, alone and beside each origin (`share_misses`). A
  whole pass took 590 s and 760 s summed over 8 workers on a loaded machine (2026-10-16).
- on drawn fields, against the writer's and the reader's `value_field`; drawn bodies, against the writer's;
  drawn records changed near each boundary of the envelope (`records.sweeps()`), and every conformance input
  that parses, against the reader schema; and the base and faulty field of each fault family, against both
  value fields; as many as the profile gives.
- along each writer mutant's own search (`test_writer_mutants.py`), as its table runs it, up to the example at
  which the mutant's verdict first differs from the package's. There a difference of that mutant's reach, on
  either side, shows on every run. The drawn faults alone meet such a difference by chance: Hypothesis shows
  one draw in about eight examples, so 2,000 examples give each of the 166 faults one or two draws, and in the
  review of 2026-10-17, 12 of the 89 mutants changed no compared verdict in at least one of five samples.

It lists every place in the tests that takes jsonschema-rs's verdict alone, with the tests that compare that
schema or the reason it is left out, and checks that the list is exact by reading the tests' sources. Its
controls: writer mutants given to one side (M18 on T1's share, M55 on the drawn faults, each of the 12 along
its own search, and U1 to U3 along theirs, which draw bodies with a unit changed) and reader mutants given to
one side (on drawn faults and on drawn records), each found as the side given it taking what the other
refuses; a pattern ended in `$`, given to both, which python-jsonschema reads as matching before a final
newline and jsonschema-rs, as ECMA-262 does, not; the pairs the properties use, each of both libraries; and
T1's inputs, naming every definition T1 judges an example by. `tests/spec_sync/test_schemas.py` holds every
schema file to draft 2020-12 and every pattern to what both libraries read alike: anchored at both ends, by
`^` and `(?![\s\S])`, with no escape of a letter or digit, no `.` or `$` outside a class and no POSIX class.

## Mutants

`test_mutants.py` (JSON) and `test_record_mutants.py` (records) give the core one fault at a time and require
the property aimed at it to find the fault within the examples of the `ci` profile, at the small size and at
the original one. The faults include those the conformance runner's self-tests use, and faults that only some
sizes or contents could show: a nesting limit off by one, removal that stops at depth 2, sorting by one pass of
exchanges, a pattern searched where it must match in full, versions ordered as strings or as doubles, an
unreadable source ignored, the first of two differing copies read. Each test records the examples its kill
took as `examples_to_kill`, which `--junitxml` writes out. A fault that died only at the original size would
mean the small size misses it. Hypothesis warns where the repr of the example it reports runs past 30 kB,
which the warning filter makes an error: the searches of steps 8 to 10, and those that share the latter's,
ignore that warning alone, so that a kill at a long example (an evidence field at the original size) is
counted, not lost in its report.

A derandomized run draws none of the constants Hypothesis harvests from the loaded modules
(`tests/harvested_constants.py`), so a search's examples, and its count, depend on the code alone: the mutant,
the property's strategy and check, the version of Hypothesis, and the source of the `kill` helper that runs the
search (below), not which other modules the process imported or in what order. Until 2026-10-18 they did not: Hypothesis (6.169) takes a constant in about
one draw in twenty, half the time one it found in a loaded module outside `tests/`, and `derandomize=True`
fixes the seed, not those constants, so a module added for any reason could move kills in every shard or let a
mutant survive. #43's `scripts/check_anomalies.py`, collected through its unit tests, moved 13 of the 544
kills that `--property-controls only` measures, and `a_non_object_provenance_opens` survived 2,000 examples at
the original size; a module of 270 other constants loaded beside the suite moved 47, and each mutant module
collected alone, 62. With the constants pinned, none of the 544 moved in any of those runs, nor on Python 3.11
against 3.15 (measured 2026-10-18).

No kill count here is typed. `kill_points.json` records each search's kill point at the small and the original
size, and `scripts/gen_kill_counts.py` writes from it the last cell of each row of the tables under a comment
naming their group, and the sentence below. The file is recorded from a run of every search (`uv run python
scripts/gen_kill_counts.py --measure --record`, about 45 seconds of tests on 8 to 12 workers). A search's kill
does not depend on the profile or the Python (the 874 kills of 2026-10-19 were the same at `dev` and `ci`, and
on 3.11 and 3.15), so a local run records CI's.

What a kill does depend on, beyond the strategies and checks a search draws, the file records under `inputs`:
the Hypothesis version (`uv.lock`), and a digest of the source of each `kill` helper that runs a search (the
function `search` it defines, `@MUTANT_SEARCH`-decorated, which Hypothesis hashes into the seed, comments and
blank lines left out as it leaves them out) and of `MUTANT_SEARCH`. That source is the same text for every
mutant a helper searches, so editing it re-seeds all of them. The condition group's helper is also the
result, invariance, monotonicity and model groups' (366 of the 874 searches). Measured on a scratch copy
(2026-10-19): comment lines added beside the search and inside it moved no kill; renaming one local
(`first`) throughout the helper moved 247 of those 366 searches, and one (`two_nominals_for_one_field`, small
size) re-seeded to an example outside its "dies at" labels and failed its own assertion. `--check`,
`--against` and a failed `--measure` name the input that differs from the tree first, so that a re-seed never
shows as an unexplained wall of moved kills; the cure is to record again (`--measure --record`), and then to
read the margin guard's list, a re-seeded kill past the 500th being a new fact about its search. The digest is
of the text, so it also flags an edit to the search function that moves nothing, such as a comment after code
on a line.

Two checks hold the counts. `--check`, beside the other generators, fails where a count here differs from the
file, where an input differs from the tree's, where a recorded group has no table here (but the writer's and
the records', which have none), where a table of every search of its group lacks a recorded mutant's row, or
where a kill falls after the 500th example: the margin guard (maintainer, 2026-10-19), which names each such
search, to be planned as below. The guard bounds the pinned seed's kill, not the margin: a search that is early
at this seed and long over others is not seen by it (below). CI's `kill_points` job, which reads the reports of all
of a Python's `controls` parts, which together run every search on Python 3.11 and 3.15, holds the file to that
run (`--against`): it fails where a kill point differs, a search
it ran is not recorded, a recorded group is missing from its run (a test function renamed or deleted leaves
counts nothing runs; `--measure --record` drops it), a search passed without recording `examples_to_kill`
(which neither the file, the counts nor the guard would otherwise see), or a row of these tables names a search
it did not run. A pull request that adds or moves a mutant records again; a row of a mutant the file does not
hold yet passes `--check`, so that a stacked branch's older commits stand, and fails at the head against CI's
run.

<!-- kill points summary (scripts/gen_kill_counts.py) -->
`kill_points.json` records 1,306 searches, 653 mutants each at both sizes; the latest kill is at the 487th example (`upper_none_as_infinity`, original size).
<!-- end of kill points summary -->

Three searches were planned because their kill sat in a long tail. With the pin, a search's kill is fixed by
the code, but where the kill is late, a change that moves the seed (a Hypothesis upgrade, or any other change to
what Hypothesis hashes into a search's seed) can move it past the budget. Each of
the three was reseeded 24 times with the code unchanged (a pytest plugin salting `hypothesis.core.
function_digest`, salts `v1` to `v24`: the strategies and the code are the same, only the seed differs), drawn whole: `a_non_object_provenance_opens` took 872 examples at the original size
and 455 at the small (pinned), up to 1,875 and 1,311 over the salts, and survived 2,000 at the small size in
one salt; `empty_word_made_plural` 629, up to 945; `row_requirements_ignored` 536, up to 1,363, and survived
2,000 in one salt (both sizes). Each fault shows in a thin region of its property's examples (below), so each
is now searched in that region, in records the core passes (and the property's own reach into it is held to a
floor: "The regions held to a floor", below):

| Mutant | Where the fault shows | The planned search |
|---|---|---|
| `a_non_object_provenance_opens` | an edit of a leaf below a `review` or `copy` in a provenance whose value is an array, which the hash keeps (item 1 removes them inside a provenance object only): the hash's `edits` must draw such a provenance, an object inside it holding one of the names, and that leaf among the record's | The hash's record, a `held` member `{"provenance": [...]}` holding an object (in up to two further arrays) with `review` or `copy`, and an edit of a leaf below it |
| `empty_word_made_plural` | `x__y` against `x_s_y` (one character added) or `x_es_y` (two): (9)'s `pairs` must draw a name with an empty word, then the slip that puts `s` or `es` in exactly that word | a name of words with one empty, the same with `s` or `es` in it, in either order |
| `row_requirements_ignored` | a condition the field's row requires that the record does not hold and the request does not name: `table_cases` names every one in the request, so it needs the `unchecked` kind to remove one from the request and `absent_but_required` to remove the same from the record | HP7's table case with one required condition removed from the record and from the request |

Each is meant to draw only examples the core passes, and three controls check that, on fresh random draws of the
same strategy, not on the search's own derandomized 2,000: 200 at `dev` and 2,000 at `ci` and `deep`. The hash's
(`test_mutant_view.py`) runs at both sizes, small and original, in two arms: the strategy as the search draws it,
and the strategy with the tree below `review` or `copy` planned to hold a provenance object that removes a leaf,
alone or beside a kept one, which is the draw that tells a search that edits a removed leaf from the planned one.
The first draft of the hash's strategy, without the filter that picks a kept leaf, failed the core on 1 of 5,000
random examples at the small size and 6 of 5,000 at the original (the review's measurement), so the first arm
alone would catch it in a run of 2,000 (`ci`) with a probability of 33% at the small size and 91% at the original,
and in a run of 200 (`dev`) 4% and 21%; the second arm catches it at the first example of every run (the first
draw of its `one_of` is a tree with no kept leaf, and a random draw fails three times in four, so 200 draws miss
it with a probability below 1e-100; measured 40 runs of 200 in 40, at each size), and a third test runs the
strategy without the filter against the control and asserts that it fails, at both sizes. The slips' control (`test_mutant_view.py`, `pairs_through_an_empty_word`, which takes no
size) and the conditions' (`test_condition_mutant_table.py`, `table_cases_without_a_requirement`, no size either)
draw their one strategy. The three mutants, by the searches in `test_mutants.py` and `test_condition_mutants.py`,
fail on every one of the 2,000 examples of each search, at both sizes, at the assertion that names their fault:
`check_edit`'s "left the hash unchanged", `check_one_slip`'s first or second assertion, and
`check_against_the_oracle`'s reasons. Each search dies at its first example at both sizes, and in each of the
24 salts (measured 2026-10-18). That is by construction: Hypothesis draws the example of all zero choices
first, whatever the seed, and every planned example kills, so the kill point is 1 and a salt cannot move it. It
is not a margin. What it shows is the number of the planned examples that kill: 2,000 of 2,000 for each of the
three (the slip's first draw, `Pair('s', '')`, is the degenerate whole name `''` against `s`, not `x__y` against
`x_s_y`; 1,996 of its 2,000 contain an underscore).

**The regions held to a floor.** A planned search shows that a check kills its mutant; it does not show that the
property's own strategy still draws the region where the fault shows, so a change that stopped drawing it would
pass every test (PR #49's review, M1; maintainer, 2026-10-19). The property whose draws each planned search
stands in for records its region as a feature and holds it to a draw floor at `ci` (Audits, below), declared by
its chance; a control in `tests/unit/test_audit_controls.py` shows each audit failing, on that feature alone,
when the generator stops producing it; and a second control, beside each planned search's own
(`test_mutant_view.py`, `test_condition_mutant_table.py`, `test_result_mutant_table.py`,
`test_model_mutant_table.py`), shows that over the property's own draws (200 at `dev`, 2,000 at `ci` and
`deep`) an example shows the feature exactly where the mutant fails the property's check, so that the floor
counts the region where the fault shows, no wider and no narrower. The member the reader does not know that
HP12's values plant is held as HP6 holds it, by its chance and its audit control alone; its planned search
draws it always. That control removes the member as drawn, rather than rejecting each example that shows it:
the region of a constant under `bounds` plants it in every draw, and the rejection stopped that region too
(2026-10-21). Main drew six of these regions in under 0.03 of the examples, too seldom for a floor: one of
10 examples, the least `ci` judges, needs a chance of about 0.065 (`audits.draw_floor`). So each strategy draws
its region in a weighted branch, and each chance is declared below the least share measured (2026-10-20: 2,000
examples a run at `ci`, derandomised, each run its own stream, the checks skipped; 48 runs, HP1's and HP12's
96, HP7's 144; shares are measured, since Hypothesis draws the ends of a small range more often than their share):

| Planned search | Region (feature) | Property, and its branch | Main: mean share | Now: mean (least) | Chance | Floor | Falls below it, a run |
|---|---|---|---|---|---|---|---|
| `a_non_object_provenance_opens` | an edit below `review` or `copy` in a provenance that is an array (`edited_below_review_or_copy_in_a_non_object_provenance`) | the hash's edit property: in about three in ten of its edits outside every provenance object, the edit placed below such a name beside the record's own members (`placed_below_a_non_object_provenance`) | 0.003 | 0.257 (0.218) | 0.18 | 95 | 5e-14; 1e-38 |
| `empty_word_made_plural` | a name with an empty word against the same with `s` or `es` in it (`through_an_empty_word`) | (9): such a pair in about one in four of its unrelated names and its two slips not swapped far apart (`pairs_through_an_empty_word`) | 0.002 | 0.157 (0.116) | 0.1 | 30 | 6e-13; 2e-32 |
| `row_requirements_ignored` | a condition the row requires held by neither the record nor the request (`required_held_nowhere`) | HP7's table: such a condition removed after the kinds in about one draw in seven | 0.005 | 0.144 (0.104) | 0.1 | 30 | 2e-11; 7e-21 |
| `condition_unchecked_without_its_condition` (result) | a result holding `condition_unchecked` (`condition_unchecked`) | HP1: before the kind, in about one draw in seven, the planned search's read with no second fault (`unknown_at_step_10` whose one fault is `unchecked`), the kind's own draws giving `unchecked` half as often as each other fault | 0.024 | 0.154 (0.113) | 0.08 | 15 | 7e-16; 8e-18 |
| `condition_unchecked_without_its_condition` (HP12) | the same (`condition_unchecked`) | HP12's faults: inside the kind of steps 9 and 10, the one that reaches step 10, in about a quarter of its draws, the planned search's read with no second fault (`unchecked` the one fault of steps 9 and 10) | 0.026 | 0.132 (0.093; 0.0795 over 20 more runs) | 0.08 | 15 | 4e-13; 3e-19 (5e-11 at the 20's variance) |
| `bounds_given_by_a_constant` | a constant's read under `want: bounds` that reaches step 13, which refuses it (`constant_refused_bounds`) | HP12's values: inside each of its two kinds alike, in about one draw in seven, the planned search's read (a constant under `want: bounds`, as drawn or with an implied temperature) or alternatives of a constant met under `want: bounds`, each beside a member the reader does not know | 0.016 | 0.157 (0.116) | 0.09 | 20 | 5e-15; 6e-22 |
| `unknown_members_returned` | a member the reader does not know (`unknown_member`) | HP12's values, as drawn (`result_strategies.enriched`, half the draws of the field read) and in every draw of the region above | 0.244 | 0.354 (0.294) | 0.2 | 110 | 3e-23; 3e-42 |

The floor is the count of 2,000 examples below which a run fails. The last column is the probability that a
run falls below it, by `audits.py`'s model (a run counts 2,000 / `CLUSTER` = 250 draws, each shown in `SHOWN` =
5 examples: the probability that 250 draws at the mean share give fewer than a fifth of the floor), and at the
variance measured over the runs (3.4 to 7.2 times a binomial count's, 10.4 over the 20 more of HP12's faults:
the count taken as that many examples' clusters). What each floor bounds: a region no longer drawn, or drawn 5 to 21 times more thinly than now. Main's
strategies drew the hash's, the slips' and the table's regions below these floors, but HP1's, HP12's faults' and
HP12's constants under `bounds` above theirs: those floors catch a region that is no longer drawn, not one drawn
as thinly as on main, which no floor at 1e-6 could tell from the shares now. `deep` would catch most such slides:
it holds each chance at a third (0.027 to 0.03 over 20,000 examples), above main's 0.016 to 0.026.

Each branch draws its region in place of a draw the strategy would have made, so it narrows what the strategy
draws besides by the branch's share. HP1's draws its region before the kind, so that it takes from every kind
and fault alike, and from `unknown_at_step_10` most of that kind's draws of `unchecked`, not those of the
faults beside it; in one of its draws in 32 it draws instead a read whose first fault is `disagreeing`, which
gives `request_incomplete`, so that the branch takes none of that code's share. Over 96 runs each region of
HP1, HP2 and HP11 (their reads are HP1's) that the reviews measured kept 0.81 to 1.26 of main's mean share
(the fix rounds' tables, in the pull request). HP12's parts draw theirs after the kind, inside a kind that can
hold it, so that their kinds stay drawn alike, as their floors take them (0.495 to 0.505 over 96 runs): the
values part in each of its two kinds alike, the other regions the review measured keeping 0.84 to 0.99 of
main's share, and the faults part in its kind of steps 9 and 10, the one of its two that reaches step 10,
where the region takes about a quarter of the draws, so that each first fault of steps 9 and 10 keeps 0.66 to
0.82 of its share on main. The slips' branch takes from the unrelated names and the two slips not swapped far
apart, never from a one slip's draw: drawn first among all, it took a fifth of the substitutions' share and
moved the plural searches' kills. The table's draws after the kinds, whose labels are as drawn, removing one
condition from the case; the hash's takes the edits outside every provenance object alone and places its
region under a member no record holds, so that the edits inside a provenance object and every feature of the
record are as drawn. These changes reach the properties named and the searches that draw their strategies;
HP10, the byte form's property, draws HP12's builders but not its parts, and so draws as before. The hash's
records hold a provenance object in an array in half their draws, and a `card` or `content_hash` in their
provenance object in half, which lifts the six chances of its two properties that lay above their least
shares on main (`card_below_the_top` and `provenance_in_an_array` on both, least 0.386 to 0.426, and the edit
property's `edited_below_a_kept_special_name` and `edited_inside_a_provenance_object`, 0.3335 and 0.2945 against
0.36 and 0.33; `test_hashing_properties.py`). All six clear their chances now. Some declared chances still lie
above the least share measured over 96 runs, each far above its floor (at most 6e-8 a run at the variance
measured): HP1's kinds (0.07; least
0.030 to 0.045 now, 0.043 to 0.064 on main), and HP12's values' `form_interval` (0.14; 0.102 now, 0.136 on
main), `form_composition` (0.12; 0.107, 0.124), `form_evidence` (0.11; 0.107, 0.113) and `standing` (0.10;
0.093, 0.100). No weight lifts HP1's: a kind's count varies six to eight times as much as a binomial count, so
a least share of 0.07 over 48 runs needs a mean of about 0.11, and eleven such kinds exceed the whole. HP12's
four lay within 0.005 of their least shares on main, and the region takes about one draw in seven of each
kind; the constants hold the only slack, and those under `want: value` hold the `-0` region (kept at 0.87 of
main's), the others S4a's constant alternatives and the request faults, which other searches draw. A sixth,
HP12's faults' `condition_unchecked` (0.08), is at its least share: 0.093 over those 96 runs, but 0.0795 (159
of 2,000 examples) in the worst of 20 more on other streams (2026-10-21). Its floor, 15, lies far below that
least count, and a run falls below it with a probability of 5e-11 at the variance of those 20 runs (10.4 times
a binomial count's).

The other planned searches are held by a floor the property had, or by none of their own yet. HP2's five under a
nominal draw HP2's `nominal` kind whole, and since 2026-10-20 HP1's `reasons_not_merged` its step 8 and steps 9
and 10 kinds and `stated_without_origin_with_a_condition` the five it dies at, HP2's `conditions_beside_no_pick` and `unit_beside_alternative_values` its `alternatives`
kind and `no_statistics_beside_a_composition` its `met_own_member` kind's compositions (The result's mutants,
below), each kind held to its chance, not the narrower region where the fault shows;
steps 9 and 10's planned search draws HP3's faults that end the read at step 10, each of which HP3's step 10
property draws first and holds to its floor; HP5's members in a report are its `in_a_report` share; and HP3's
planned searches of step 8, and HP12's that draw step 8's faults among those named, draw faults HP3 holds by
region, the precedent of Step 8's mutants ("the region audit that HP3 draws it"), not by fault: 154 faults
cannot each be drawn often enough for a floor at `ci`. These have no floor of their own yet: HP12's planned
searches of values at a boundary, under a nominal, alternatives under a nominal, evidence's unit with a
reason, step 0's nominal faults, and S4a's (an interval under bounds, the outcomes of step 7 and three
narrower); HP27's planned searches (a request fault, under a nominal, evidence set aside first or under
`no_pick`); and (9)'s irregular plurals and plurals in `ies`, too thin for a floor even at `deep`: (9) draws a
pair through an irregular plural in 0.0043 of its examples and one through an `ies` plural in 0.0032 (means
over 24 runs of 2,000, each mutant injected beside the region, which it fails exactly; least 0.0020 and
0.0005), and by `audits.py`'s model a floor at `deep`'s 20,000 examples reaches 10 only at a chance of about
0.0067 (2026-10-21). Their draws were left as they are: lifting them is the maintainer's call. Four searches
planned on 2026-10-20, too thin for a floor at `ci`, are held at `deep` (below). A floor at `ci` needs about
0.065: a second branch in a strategy already drawing one would take its other draws below 0.8 of main's.

**Held at `deep`.** Four regions of the searches planned on 2026-10-20, 0.025 to 0.036 of their parts' draws,
are held to a floor at `deep` alone, whose 20,000 examples make one possible at 1e-6 (maintainer, 2026-10-21).
Each part records its region as a feature computed from the example and the read's result, declares it with
`deep_chances` (Audits, below) by a chance at or below its least share over 24 runs at `ci` (2026-10-21, 2,000
examples a run, derandomised, each run its own stream, the checks skipped), and has a control at `deep`'s
examples and rule in `test_model_deep_floor_controls.py`, which runs where `deep` runs (below); a second,
beside the planned searches' own (`test_model_mutant_table.py`), shows that over the part's own draws an
example shows the feature exactly where the mutant fails the agreement. No draw changed:

| Planned search | Region (feature) | Part | `ci`: mean (least), variance | `deep`'s size: mean (least) | Chance | Floor | Falls below it, a run |
|---|---|---|---|---|---|---|---|
| `plus_minus_units_unchecked` ("a plus or minus unit") | a read that plants a `plus_minus` entry's unit and whose result gives `unit_mismatch` on `temperature` (`plus_minus_unit_refused`) | HP12's faults | 0.0247 (0.0105), 3.8 | 0.0256 (0.0226), 4 runs of 20,000 | 0.01 | 25 | 2.4e-7; 3e-47 |
| `token_condition_unit_accepted` ("a token condition's unit") | the same of a token condition's unit, on `measurement_geometry` (`token_condition_unit_refused`) | HP12's faults | 0.0255 (0.0075), 6.1 | 0.0283 (0.0260), 4 runs of 20,000 | 0.007 | 10 | 4.4e-7; 3e-35 |
| `components_normalised` ("a composition under components") | a composition's components given, as the value or an alternative's, that state their sum or whose fractions dividing by their sum changes (`components_not_normalised`) | HP12's values | 0.0359 (0.0085), 7.3 | 0.0357 (0.014), 16 runs of 2,000 | 0.008 | 15 | 4.3e-7; 7e-35 |
| `request_faults_of_the_first_alternative_alone` ("request faults apart") | alternatives refused by `request_incomplete` reasons alone, on two conditions or more (`request_faults_of_two_alternatives`) | HP12's values | 0.0359 (0.0195), 8.7 | 0.0358 (0.019), 16 runs of 2,000 | 0.019 | 95 | 7.3e-7; 6e-22 |

The floor is the count of 20,000 examples below which a `deep` run fails. The last column is the probability
that a correct run falls below it by `audits.py`'s model (20,000 / `CLUSTER` = 2,500 draws, each shown in
`SHOWN` = 5 examples) at the declared chance, and at the means and variances measured (the count taken as that
many examples' clusters, scaled to 20,000 examples; the variance is the count's over a binomial count's). A
run of HP12's faults at `deep` took 11 to 13 minutes here; one of its values about 15, too long to measure, so
its share at `deep`'s size is from runs of 2,000. Each chance lies at or below the least of 2,000-example
runs, so each floor catches a region no longer drawn, or drawn 8 to 57 times more thinly than its mean at
`deep`; `deep`'s own least shares, by the examples' ratio, would hold chances 1.4 to 3.4 times higher.
Features read from the example alone counted more than the region where the mutant shows, over the same draws:
the fault planted (reads that end at `want_mismatch` before step 9 plant it too), the plant
`request_faults_apart`, and a composition under `want: components`.

A floor held at `deep` alone is judged only where `deep` runs, CI's scheduled and dispatched runs of the
Hypothesis job, so its control runs there too and in no pull request's job (2026-10-21; an open point for the
maintainer). Each control runs a property for 20,000 examples: 5 to 8 minutes here at the small size, about 35
to 40 minutes of CPU in all on CI, which a pull request's controls job would carry on each Python; at `deep`'s
size, 10.4 to 21.0 minutes each on CI (measured in dispatched run 39553647007, 2026-10-21, 67.1 minutes in all).
The controls are marked `deep_controls`, which every other profile deselects (`tests/conftest.py`), and sit in
the `relations` shard beside the properties they control (`test_model_deep_floor_controls.py`, whose audits
`conftest.py` leaves to the control); the shard's `deep` timeout is held to at least twice its measured runs,
which hold them (`.github/workflows/ci.yml`). `tests/unit/test_ci_workflows.py` fails where a scheduled or
dispatched run leaves one out or runs it twice, or a pull request's job runs one, and the module fails where a
feature held at `deep` alone has no control.

Every count in these tables is one seed's: the derandomised search's. Another seed takes
another count, often several times larger or smaller (PR #37's review measured 19 and 1,406 for a mutant
listed at 52 and 414), so a count says how a search went, not a mutant's margin to the 2,000 examples. That
margin is a seed sweep's, which the tables give where one was run: the examples a search took over many
random seeds, at both sizes.

CI's test matrix runs the mutant modules, `test_*mutants*`, on the supported range's ends alone
(`--property-controls` in `tests/conftest.py`), so a mutant module holds mutant searches only. The checks of
the mutants' own code, which run on every Python, are in modules of their own: `test_mutant_view.py` (the hash
mutants' view, without a fault, is the core's), `test_value_field_mutant_table.py`,
`test_writer_mutant_table.py`, `test_condition_mutant_table.py`, `test_result_mutant_table.py`,
`test_model_mutant_table.py` with HP12's controls in `test_model_controls.py` and the audit controls of its
floors held at `deep` alone in `test_model_deep_floor_controls.py` (run at `deep` alone),
`test_invariance_mutant_table.py` and `test_monotonicity_mutant_table.py`.

`test_mutants.py` also gives the one-slip relation twelve faults, each killed by (9) (its strategy has no size,
so both sizes take the same examples):

<!-- kill points of some searches of test_mutants.py::test_the_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Examples |
|---|---|---|
| `substitution_missed` | a character substituted missed | 23, 23 |
| `insertion_missed` | a character inserted or deleted missed | 1, 1 |
| `underscore_missed` | an underscore added or removed missed | 21, 21 |
| `swap_missed` | two adjacent characters swapped missed | 3, 3 |
| `plural_missed` | a word made plural or singular missed | 11, 11 |
| `underscore_read_as_a_character` | an underscore added is named a character added | 21, 21 |
| `two_characters_added_one_slip` | two characters added at the end are one slip | 13, 13 |
| `swap_of_any_two_characters` | two characters swapped far apart are one slip | 52, 52 |
| `ies_plural_missed` | a final `y` made `ies`, a plural section 10 lists, missed (planned) | 1, 1 |
| `es_plural_missed` | `es` added, a plural section 10 lists, missed | 93, 93 |
| `irregular_plurals_missed` | an irregular plural section 10 lists missed (planned) | 1, 1 |
| `empty_word_made_plural` | the empty string between two underscores is a word, `s` its plural (planned) | 1, 1 |

The last is the relation as it stood until the property found it: `x__y` and `x_s_y` are one character apart,
but `x__y` and `x_es_y` two, which it called one plural. `irregular_plurals_missed` and `ies_plural_missed` are
planned since 2026-10-20, on a name holding one of section 10's irregular singulars against the same with its
plural (`pairs_through_an_irregular_plural`), and on a name holding a word that ends in `y` against the same
with `ies` in its place (`pairs_through_an_ies_plural`), each of which the core passes (`test_mutant_view.py`).
Drawn with (9) whole, the first died past the 500th example on 46 of 400 streams on main and on 73 once (9)
drew a pair through an empty word (one-sided Fisher p = 0.005); the second on 88 and 80, about as on main, but
at the 700th on the recorded stream. (9) draws the regions in about one example in 230 and one in 310, too
seldom for a floor of their own even at `deep` ("The regions held to a floor", above); each dies at the 1st
example.

`test_writer_mutants.py` gives the writer schema one change at a time: the S2a-1 review's 29 mutants of its
value-field part and its two controls (M1 to M31, its numbering kept), one for each constraint written since
(M6b, M14b, M32 to M61), and nine that tighten it (T1 to T9); then the bindings it applies from the
vocabulary, each changed in the vocabulary file or no longer applied by the writer: a section's field names, a
field's forms, unit, label or composition basis, its alternatives, the replaced fields, a numeric condition's
unit and its `plus_minus` entries', a specimen fact's fixed unit (B1 to B14, with B5b), and the forms a row's
label goes on and a labelled table's axis (B15 and B16, PR #37's review), and six that tighten them (TB1 to
TB6; B15, B16 and TB6 each die at their first example at both sizes, 2026-10-17); and three of those bindings
removed again (U1 to U3: the specimen facts', a field's unit,
the conditions'), each killed by the relation to step 9 at a body with a unit changed where it held, searched
among those places (each at its first example, both sizes; measured 2026-10-16). Each names
the property that kills it and the assertion it must die at: a loosening mutant dies when the refusal property
of its family finds the schema taking one of the faults it names, its search drawn among those faults, which
the family's property draws as often as any other (the feature audit holds it to its draw floor); a
tightening one dies when the acceptance property finds it refusing a field the text allows, its search drawn
on fields of the form and with the parts in which it refuses one. Both sizes, as above. Two mutants of the
review die at a fault besides the one they were written for, both by the rule they break: M13, without
`plus_minus`'s `then`, also takes an unstated kind beside a stated one, and M48, with `withheld` among an
entry's other statuses, also takes a withheld entry without its recipe.

### Step 8's mutants

`test_value_field_mutants.py`. Each fault is injected where the core looks a name up when it runs, or in the
tables it builds, rebuilt under the fault. The first 25 (S2a-2's 24, and its fix round's
`fact_unit_judged_at_step_8`) were searched with their property whole; the 23 of them HP3 kills are now
planned too (below), and HP5's two are still searched whole. The other 22 are the fix round's: the eleven
rules S2a-2's review found no test checked (M1; the fact unit's is `fact_unit_judged_at_step_8`), and parts of
the text HP3 had no fault for or could not tell from a missing member (M2). One, `label_on_any_table`, dies to
the label's rule. The other 21 each name the faults they must die at, and their search is planned, as the
writer's are: HP3 draws its first fault among them, and the kill must hold one. Drawn with HP3 whole, 17 of
those 21 were measured: each died within its 2,000 examples at both sizes but `within_any_status` and
`label_beside_an_unknown_form_as_on_a_constant`, which died at the original size alone (884 and 845). HP3
whole meets one fault of 154 too seldom to kill each such mutant every time at `ci`, so the planned search is
what shows HP3 refuses each fault, and the region audit that HP3 draws it; each of the review's eleven rules
also has a deterministic read in `tests/unit/test_read.py`. The kill is the examples the derandomised search
took, at the small and the original size.

Two of the first 25, `missing_represents_accepted` and `named_state_text_unchecked`, have had planned searches
since 2026-10-16: searched with HP3 whole, each survived 2,000 examples at the small size once the suite held
`scripts/report_test_durations.py`, which its unit tests import, and died where their module ran alone. At
S2a-3's head, `named_state_text_unchecked` also survived 2,000 examples at the original size where its shard
ran alone, as CI runs it, and died where the whole suite ran: S2a-3's code added constants. Hypothesis (6.169)
draws, among its values, constants it finds in the project's modules the process has loaded, test modules
aside, so the examples a derandomised search meets changed with the code and with what else a process imported
(no longer: Mutants, above). Emptying that pool, the search killed it alone and after the unit tests alike
(measured 2026-10-16). Planned,
each dies at its first example at both sizes, alone, after the whole suite's collection, on Python 3.11 and
3.15. The other 21 that HP3 kills, which could each meet the same at any change, have been planned since S2a-3
came onto main (maintainer, 2026-10-16): each names the faults of HP3's catalogue that test the rule it
breaks, chosen from a search on each of the 154 faults alone against each mutant at both sizes (a fault that
killed it only beside a second fault was left out), and dies at its first example at both sizes, alone and
after the whole suite's collection, on Python 3.11 and 3.15 (measured 2026-10-17). Searched whole, they had
died after 3 to 1,297 examples. HP5's two, `unknown_members_refused` and `two_slips_refused`, are still
searched whole: HP5 draws no fault of the catalogue to name, and nearly every example it draws kills each, at
the second example at both sizes in each of those runs.

<!-- kill points of every search of test_value_field_mutants.py::test_the_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `unknown_tokens_ignored` | a token the reader knows for no member of its name is accepted | HP3 | the 20 faults of a token unknown to its member (`UNKNOWN_TOKENS`), S2b-1's seven among them | 1, 1 |
| `unknown_token_read_as_a_shape_fault` | such a token gives `form_invalid` | HP3 | those 20, `statistics_statuses.status_unknown` and `field.label_unknown` | 1, 1 |
| `status_tokens_unchecked` | a status object takes any status token | HP3 | `statistics_statuses.block_status_not_allowed`, `.status_not_allowed`, `.status_unknown`, `.within_status_not_allowed`, `field.value_status_not_allowed` | 1, 1 |
| `members_beside_a_status_ignored` | a status object beside a member of the shape it stands for is read as one | HP3 | `statistics_statuses.uncertainty_status_beside_a_member`, `condition_tokens.status_beside_a_token`, `.status_beside_unit`, `specimen_tokens.fact_status_beside_its_token` | 1, 1 |
| `missing_represents_accepted` | a statistics block without `represents` passes (the S2 design's HP3 mutant) | HP3 | `statistics_members.represents_missing` | 1, 1 |
| `null_read_as_absent` | `null` in an optional member reads as the member absent (HP3's) | HP3 | `condition_tokens.set_or_measured_null`, `provenance.source_null` | 1, 1 |
| `unknown_condition_names_checked` | a condition name the reader does not know is checked as a numeric condition (HP3's "read as known") | HP3 | `condition_tokens.name_unknown` | 1, 1 |
| `plus_minus_kinds_unchecked` | a `plus_minus` list is checked only as a list | HP3 | `conditions.plus_minus_empty`, `.plus_minus_negative`, `.plus_minus_two_bounds`, `.plus_minus_unit_not_a_string`, `.plus_minus_unstated_beside_sd` | 1, 1 |
| `range_order_unchecked` | a range's `lo` may lie above its `hi` | HP3 | `conditions.range_reversed`, `.range_reversed_on_shear_rate`, `specimen.fact_range_reversed` | 1, 1 |
| `counts_not_whole` | `n_specimens` takes any number | HP3 | `statistics_numbers.count_not_whole` | 1, 1 |
| `conditional_members_unchecked` | `population_level`, `n_sources` and `precision_conditions` may sit beside any `represents` | HP3 | `statistics_members.n_sources_elsewhere`, `.population_level_elsewhere`, `.population_level_missing`, `.precision_conditions_missing`, `uncertainty.uncertainty_precision_missing` | 1, 1 |
| `uncertainty_rules_unchecked` | an uncertainty's coverage, `dof` and precision rules go | HP3 | `uncertainty.dof_status_under_student_t`, `.dof_under_normal`, `.no_coverage_number`, `.uncertainty_precision_missing` | 1, 1 |
| `named_state_text_unchecked` | a disease or treatment state's text may sit beside any token, or be missing | HP3 | `specimen.fact_text_beside_normal`, `specimen.fact_treated_without_text` | 1, 1 |
| `fixed_basis_unchecked` | `mimics`'s basis takes either token, not the one its row fixes | HP3 | `specimen_tokens.fact_basis_not_its_rows` | 1, 1 |
| `fact_unit_judged_at_step_8` | a fact's unit is judged at step 8, `s` alone and a status object of the five tokens only, where step 9 alone compares it (a default for the maintainer, 2026-10-15) | HP3 | `specimen.fact_unit_not_its_rows`, `.fact_unit_status_any_token` | 1, 1 |
| `record_structure_unchecked` | a slip in the envelope, the body or a section is ignored | HP3 | `record.body_slip`, `.envelope_slip`, `.licence_slip`, `.section_name_slip` | 1, 1 |
| `section_specimen_unchecked` | a section's `specimen` is not checked | HP3 | `section_specimen.section_fact_name_slip`, `.section_fact_not_its_shape` | 1, 1 |
| `first_refusal_only` | step 8 gives its first reason only (the S2 design's HP12 mutant) | HP3 | `field_form.form_unknown_beside_a_slip`, one fault that gives two reasons | 1, 1 |
| `slip_by_substitution_missed` | the one-slip relation misses a character substituted | HP3 | `statistics_slips_beside.slip_beside_substituted`, `field_slips_optional.slip_substituted` | 1, 1 |
| `slip_by_insertion_missed` | it misses a character inserted or deleted | HP3 | `statistics_slips_beside.slip_beside_inserted`, `.slip_beside_deleted`, `field_slips_optional.slip_inserted`, `.slip_deleted` | 1, 1 |
| `slip_by_swap_missed` | it misses two adjacent characters swapped | HP3 | `statistics_slips_beside.slip_beside_swapped`, `conditions.plus_minus_slip`, `field_slips_optional.slip_swapped` | 1, 1 |
| `slip_by_plural_missed` | it misses a word made plural or singular | HP3 | `statistics_slips_beside.slip_beside_plural`, `field_slips_optional.slip_plural` | 1, 1 |
| `slip_by_underscore_missed` | it misses an underscore added or removed | HP3 | `statistics_slips_beside.slip_beside_underscore`, `field_slips_optional.slip_underscore` | 1, 1 |
| `unknown_members_refused` | every member a place does not name is refused | HP5 | any of its property | 2, 2 |
| `two_slips_refused` | names two characters off a named member are refused too | HP5 | any of its property | 2, 2 |
| `within_any_status` | a population level's `within` takes any status token, where `none` alone is allowed | HP3 | `statistics_statuses.within_status_not_allowed` | 1, 1 |
| `uncertainty_precision_any_string` | an uncertainty's `precision_conditions` takes any string | HP3 | `uncertainty_tokens.uncertainty_precision_unknown` | 1, 1 |
| `statistics_not_applicable_on_a_constant` | a constant's `statistics` takes `not_applicable`, which only reference data's takes | HP3 | `statistics_statuses.block_status_not_allowed` | 1, 1 |
| `basis_any_string` | a condition's and a fact's `basis` take any string | HP3 | `condition_tokens.basis_unknown`, `specimen_tokens.fact_basis_of_another_member` | 4, 6 |
| `condition_status_refuses_its_own_shapes_members_only` | a condition's status object refuses only its own shape's members, so `token` beside a numeric condition's passes | HP3 | `condition_tokens.status_beside_a_token` | 1, 1 |
| `token_known_within_its_kind` | a condition's `token` knows only the conditions' tokens and a fact's only the facts', so `tube` in `tissue_state` is `unknown_token` | HP3 | `condition_tokens.token_of_a_fact`, `specimen_tokens.fact_token_of_a_condition` | 1, 1 |
| `token_condition_unit_unchecked` | a token condition's `unit` takes anything | HP3 | `condition_tokens.token_condition_unit_not_a_string` | 1, 1 |
| `label_on_any_table` | a label goes on a table whatever its axis | the label's rule | its oracle, on a table on its row's axis | 3, 35 |
| `label_beside_an_unknown_form_as_on_a_constant` | a label beside a form the reader does not know is judged as on a constant | HP3 | `field_form.form_unknown_beside_the_label` | 7, 6 |
| `no_form_member_named_beside_an_unknown_form` | beside a form the reader does not know, no form's own member is named, so `intervals` is ignored | HP3 | `field_form.form_unknown_beside_a_slip` | 1, 1 |
| `statistics_block_slips_ignored` | a slip among a statistics block's members is ignored | HP3 | `statistics_slips_beside.*` | 1, 1 |
| `field_level_slips_ignored` | a slip among a field's members is ignored | HP3 | `field_slips_optional.*` | 1, 1 |
| `status_object_slips_ignored` | a slip inside a status object is ignored | HP3 | `statistics_statuses.status_slip` | 1, 1 |
| `derivation_unchecked` | a derived value's derivation is not checked | HP3 | `derivation.*` and `derivation_inputs.*` but `derivation_missing` | 1, 1 |
| `derivation_inputs_may_be_empty` | a derivation's `inputs` may be empty | HP3 | `derivation.inputs_empty`, its input specimens emptied with it, since an index past no input would refuse alone | 1, 1 |
| `block_mean_any` | a statistics block's `mean` takes any value | HP3 | `statistics_numbers.mean_not_a_number` | 1, 1 |
| `block_precision_any_string` | a statistics block's `precision_conditions` takes any string | HP3 | `statistics_tokens.precision_conditions_unknown` | 1, 1 |
| `neither_value_nor_range_allowed` | a numeric condition may hold neither `value` nor `range` | HP3 | `conditions.neither_value_nor_range` | 1, 1 |
| `n_sources_any_number` | `n_sources` takes any number | HP3 | `statistics_numbers.n_sources_not_whole`, `.n_sources_negative` | 1, 1 |
| `dof_of_zero_allowed` | an uncertainty's `dof` may be 0 | HP3 | `uncertainty.dof_zero` | 1, 1 |
| `coverage_probability_of_zero_allowed` | an uncertainty's `coverage_probability` may be 0 | HP3 | `uncertainty.coverage_probability_zero` | 1, 1 |
| `population_level_any_string` | a population level's `level` takes any string | HP3 | `statistics_tokens.level_unknown` | 1, 1 |
| `interval_order_unchecked` | an interval's bounds taken in either order | HP3 | `interval.lower_above_upper` | 1, 1 |
| `both_bounds_none_allowed` | an interval whose bounds are both `none` passes | HP3 | `interval.both_none` | 1, 1 |
| `equal_bounds_refused` | an interval's bounds must differ, a near miss refused | HP3 | `interval.bounds_equal` | 1, 1 |
| `minus_zero_below_zero` | `-0` compared as below `0`, so a lower bound `0` above an upper `-0` is refused | HP3 | `interval.zero_and_minus_zero` | 1, 1 |
| `bound_any_status` | a bound takes any status token, where `none` alone is allowed | HP3 | `interval.bound_status_not_allowed` | 1, 1 |
| `interval_basis_any_string` | an interval's `basis` takes any string | HP3 | `interval_tokens.basis_unknown` | 1, 1 |
| `composition_basis_any_string` | a composition's `basis` takes any string | HP3 | `composition_tokens.basis_unknown` | 1, 1 |
| `sum_rule_any_string` | `sum_rule` takes any string | HP3 | `composition_tokens.sum_rule_unknown` | 1, 1 |
| `composition_basis_off_its_row_read` | a basis of the composition's list that the row does not allow is left to the own member, which takes it | HP3 | `composition_tokens.basis_not_its_rows` | 1, 1 |
| `empty_components_allowed` | `components` may be empty | HP3 | `composition.components_empty` | 1, 1 |
| `component_twice_allowed` | a component named twice is read once | HP3 | `composition.component_repeated` | 1, 1 |
| `fraction_any_number` | a fraction takes any number | HP3 | `composition.fraction_above_one`, `.fraction_negative` | 1, 1 |
| `fraction_neither_zero_nor_one` | a fraction must lie strictly between 0 and 1, a near miss refused | HP3 | `composition.fractions_zero_and_one` | 1, 1 |
| `element_by_pattern` | a component checked by `element:[A-Z][a-z]?` alone (the S2 design's alternative to SQ43's table) | HP3 | `component.element_unknown` | 1, 1 |
| `component_statistics_unchecked` | a component's statistics block is not checked | HP3 | `component.statistics_count_not_whole`, `.statistics_central_unknown`, `.statistics_status_not_allowed`, `.statistics_represents_missing` | 1, 1 |
| `stated_sum_any` | `stated_sum` takes any value | HP3 | `composition.stated_sum_not_a_number` | 1, 1 |
| `sums_checked_at_read` | a `sums_to_one` composition that sums away from one with no stated sum is refused, a record check's flag read as a refusal | HP3 | `composition.sum_unflagged` | 1, 1 |
| `unknown_members_refused_in_an_own_member` | a member an interval, a composition or a component does not name is refused | HP5 | any of its property | 10, 22 |
| `any_bound_status_read_as_none` | a bound's status object of any token read as `none`, so that an unknown token beside a `none` gives `form_invalid` too | HP3 | `interval_tokens.bound_status_unknown` | 1, 1 |
| `a_repeat_found_only_beside_itself` | a component named twice found only where it follows itself | HP3 | `composition.component_repeated_apart` | 1, 1 |
| `every_report_withheld_read_as_some` | evidence whose every report is withheld gives `entries_withheld`, not `withheld` | HP3 | `evidence_list.every_report_withheld` | 1, 1 |
| `some_reports_withheld_read_as_every` | evidence some of whose reports are withheld gives `withheld` | HP3 | `evidence_list.one_more_report_withheld` | 1, 1 |
| `an_empty_list_taken` | evidence may be an empty list | HP3 | `evidence_list.list_empty` | 1, 1 |
| `a_status_list_read_as_withheld` | evidence held as a status object read as every report withheld | HP3 | `evidence_list.list_a_status` | 1, 1 |
| `a_report_withheld_in_part_taken` | a report withholding some of its members, or a withheld report holding a member beside its provenance, taken | HP3 | `evidence_list.report_withheld_in_part`, `.withheld_report_opened` | 1, 1 |
| `a_report_member_optional` | a report may lack a member | HP3 | `evidence_report.member_missing` | 1, 1 |
| `a_reports_provenance_unchecked` | a report's provenance is not checked | HP3 | `evidence_provenance.origin_unknown`, `.origin_missing`, `.source_key_not_a_string`, `.source_missing_for_its_origin`, `.derivation_missing`, `.not_an_object` | 1, 1 |
| `a_years_fraction_taken` | a standard's `year` takes any number | HP3 | `evidence_report.standard_year_not_whole` | 1, 1 |
| `a_registered_condition_taken_under_evidence` | a registered condition under evidence taken | HP3 | `evidence_field.registered_condition`, `.registered_condition_unstated` | 1, 1 |
| `unknown_members_refused_in_a_report` | a member a report, its standard or its provenance does not name is refused | HP5 (planned) | any of its property, its members added in a report | 1, 1 |

S2b-1's 18 test an interval's and a composition's own member: each rule HP3's five new regions hold a fault
for, the near misses among them (equal bounds, `0` beside `-0`, fractions 0 and 1, a sum no read checks), and
HP5's unknown member in an own member, searched whole. Each planned search died at its first example at both
sizes, in the shard and alone; the shard's kills of the others moved where S2b-1 changed what HP3 draws
(`basis_any_string` from 14 and 10, `label_beside_an_unknown_form_as_on_a_constant` from 2 and 2,
`label_on_any_table` at the original size from 59), measured in the `step8_mutants` shard at `ci` on four
local workers (2026-10-17). PR #37's review added two, each planned at a fault added for it: a bound's status
object of any token read as `none` (`interval_tokens.bound_status_unknown`, an unknown token beside `none`), and a
repeat found only beside the component it repeats (`composition.component_repeated_apart`, the first component
again after another, where HP3's `component_repeated` had met it only in some runs at `ci`). Each dies at its
first example at both sizes; no other count of the table moved (the shard again, the same day).

S2b-2's ten test evidence's own member, each rule HP3's fourth part holds a fault for, near misses among them
(every report withheld beside all but one, a withheld report holding a member besides its provenance, a year
of `1.5`), and HP5's unknown member in a report, its standard or its provenance. HP5's own draws add members
anywhere in a record of any form step 8 reads, and met this one's fault at 233 and 1,597 examples, too thin a
margin: its search is planned, members added in a valid evidence field's reports alone (`with_unknowns(...,
reports=True)`). Each died at its first example at both sizes (the `step8_mutants` shard at `ci` on four local
workers, 2026-10-18; with the pin at S2b-2's head, the same day). Of the others, only S2b-1's
`unknown_members_refused_in_an_own_member` moved (from 24 and 95, with the pin), since HP5 draws evidence too.

The S2 design's HP5 mutant, an unknown member returned, waits for the result's members (S2a-4), but in a
condition's entry, which steps 9 and 10's HP5 kills (`unknown_members_returned_in_an_entry`, below).

### Steps 9 and 10's mutants

`test_condition_mutants.py`, injected as step 8's are: a module-level function of `conditions`, `fields` or
`read`, or `RecordField.specimen`. Each names the property that kills it; the search draws that property's
examples, the parametrised ones (HP7's rows, HP8's places) drawn among their parameters, and where it names
the labels it must die at (the kind an example was drawn of, a unit's place and kind, a read's faults, the
places of its additions), the example that kills it must hold one. HP7's and HP9's examples hold no tree, so
both sizes take the same examples. Three rules no property draws are searched alike over the deterministic
tables of `tests/unit/test_read.py` that check them: an implied condition located elsewhere, read end to end
("located elsewhere"), and the implied conditions step 0 refuses ("step 0"). The kill is the examples the
derandomised search took, at the small and the original size.

Seven of these are the mutants of S2a-3's review that survived the whole suite (its M2), each a rule no test
checked: `implied_not_located`, `located_at_without_its_hash`, `accept_list_case_folded`,
`accept_list_by_prefix`, `unknown_name_status_read_as_unstated`, `only_the_first_plus_minus_unit` and
`implies_value_not_an_object_ignored`. The first two and the last die to the deterministic tables written for
them; the other four survived 2,000 examples at both sizes until HP7's token kinds drew accept lists holding
strings outside the row, its `unknown_name` kind a status object as often as a value, and HP8's `plus_minus`
place the unit in either entry of two.

One of HP3's searches is planned. `conditions_withheld_from_a_refusal` empties step 10's entries, which the
read takes for two implied conditions that disagree, so on a read step 10 does not end it ends the read there
too, with neither `value` nor `conditions`. HP3 drawn whole meets such a read first (an `unstated` one, at the
original size, once the harvested constants were pinned), and there the assertion that fails is HP3's for a
read past step 10, not the refusal's the mutant was written for. Its search ("HP3, a refusal at step 10")
draws HP3's first fault among step 10's four that end the read and keep its `conditions` (`ENDING`), and it
dies at an `outside` read at both sizes. As a control, where HP3 expected a refusal to hold no `conditions`,
the planned search let it survive 2,000 examples at both sizes, and HP3 whole still killed it, at reads past
step 10 (measured 2026-10-18).

<!-- kill points of every search of test_condition_mutants.py::test_the_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `floating_point_as_written` | section 5's tests computed in floating point | HP7 | `anywhere`, `at_the_tolerance`, `one_ulp_outside`, `rounded_difference`, `minus_zero` | 9, 9 |
| `value_row_difference_in_floating_point` | section 5's first row as written, `\|r - v\| <= t`, computed in floating point | HP7 | `anywhere`, `at_the_tolerance`, `one_ulp_outside`, `rounded_difference`, `mixed_magnitudes_outside` | 9, 9 |
| `strict_inequalities` | `<` for `<=` | HP7 | any of its examples | 1, 1 |
| `stated_range_as_its_low_end` | a stated range read as its `lo` | HP7 | any of its examples | 75, 75 |
| `operating_range_as_its_low_end` | an operating range read as its `lo` | HP7 | any of its examples | 26, 26 |
| `plus_minus_ignored` | a stated plus or minus ignored | HP7, plus or minus | `bound`, `sd`, `unstated`, `bound_beside_sd` | 3, 3 |
| `plus_minus_makes_not_met` | a stated plus or minus turns `met` into `not_met` | HP7, plus or minus | `bound`, `sd`, `unstated`, `bound_beside_sd` | 3, 3 |
| `sd_ignored` | an `sd` or unstated entry ignored where no bound sits | HP7, plus or minus | `sd`, `unstated` | 3, 3 |
| `bound_moves_the_low_end_only` | a bound narrows the window at its low end alone | HP7, plus or minus | `bound`, `bound_beside_sd` | 24, 24 |
| `unchecked_read_as_met` | a stated condition with no tolerance or accept list is `met` | HP7, table | any of its examples | 3, 3 |
| `not_accepted_read_as_unknown` | a token outside the accept list is `unknown` | HP7, table | any of its examples | 18, 18 |
| `accept_list_case_folded` | a token matched against an accept list after case folding | HP7, table | any of its examples | 114, 114 |
| `accept_list_by_prefix` | a token matched by an entry of the accept list that begins with its first three characters | HP7, table | any of its examples | 114, 114 |
| `unknown_name_status_read_as_unstated` | a name the reader does not know, held as a status object, read as `condition_unstated` | HP7, table | any of its examples | 5, 5 |
| `unknown_name_read_as_unstated` | a name the reader does not know is `condition_unstated` | HP7, table | any of its examples | 4, 4 |
| `required_with_ignored` | a condition another requires with its token is not checked | HP7, table | any of its examples | 3, 3 |
| `row_requirements_ignored` | the row's required conditions are not checked | HP7, table (planned) | any of its examples | 1, 1 |
| `status_object_not_returned` | an entry held as a status object returns no `record` | HP7, table | any of its examples | 1, 1 |
| `operating_returned_only_with_a_requirement` | `operating` returned only where a tolerance is given | HP7, table | any of its examples | 6, 6 |
| `implied_overrides_a_stated_value` | an implied condition fills a stated condition | HP7, implied | `never_over_a_stated_value`, `never_over_another_status` | 2, 2 |
| `implied_fills_any_status` | an implied condition fills any status object | HP7, implied | `never_over_another_status` | 21, 21 |
| `disagreement_ignored` | two implied conditions that disagree, the first wins | HP7, implied | `two_that_disagree`, `a_value_beside_a_range`, `minus_zero_beside_zero` | 8, 8 |
| `a_value_agrees_with_its_range` | a value agrees with the range `[v, v]` | HP7, implied | `a_value_beside_a_range` | 25, 25 |
| `minus_zero_agrees_with_zero` | implied values compared as numbers, `-0` agreeing with `0` (S2a-3's first reading, until its fix round's default) | HP7, implied | `minus_zero_beside_zero` | 8, 8 |
| `implied_applies_without_its_fact` | an implied condition applies whatever the specimen states | HP7, implied | `its_fact_not_stated` | 96, 96 |
| `applied_not_recorded` | `applied` holds no implied condition | HP7, implied | any of its examples | 1, 1 |
| `implied_not_located` | every implied condition applied, wherever it is located | located elsewhere | any of its rows | 1, 1 |
| `located_at_without_its_hash` | a location compared by `id` and `version`, without its `content_hash` | located elsewhere | `another_content_hash` | 3, 3 |
| `implies_value_not_an_object_ignored` | an implied value that is not an object dropped without a reason | step 0 | `a value that is not an object` | 16, 16 |
| `section_facts_win` | the section's fact overrides the field's (the S2 design's HP9 mutant) | HP9 | `the_field_another_token`, `the_field_a_status_object`, `the_section_a_status_object` | 7, 7 |
| `a_status_fact_overrides_nothing` | a field's fact held as a status object leaves the section's | HP9 | `the_field_a_status_object` | 22, 22 |
| `nfkc_before_comparing` | units compared after NFKC (the S2 design's HP8 mutant) | HP8, another unit | `compatibility_equal` | 1, 1 |
| `case_folded` | units compared after case folding (the S2 design's HP8 mutant) | HP8, another unit | `case_folded`, `compatibility_equal` | 2, 2 |
| `spaces_ignored` | spaces and zero-width spaces dropped from a unit | HP8, another unit | `spaced` | 11, 11 |
| `a_status_object_where_a_string_is_registered` | a status object takes a string's place | HP8, another unit | `status_object` | 35, 5 |
| `plus_minus_units_unchecked` | a `plus_minus` entry's unit not compared | HP8, another unit | `plus_minus` | 2, 2 |
| `only_the_first_plus_minus_unit` | only the first `plus_minus` entry's unit compared | HP8, another unit | `plus_minus` | 9, 87 |
| `token_condition_units_unchecked` | a `unit` on a token condition passes | HP8, another unit | `token_condition` | 179, 3 |
| `section_facts_unchecked` | the section's facts' units not compared | HP8, another unit | `section_fact` | 34, 6 |
| `input_facts_unchecked` | a derived value's input facts' units not compared | HP8, another unit | `input_fact` | 4, 52 |
| `condition_dropped_from_unit_mismatch` | a condition's `unit_mismatch` carries no condition | HP8, another unit | `condition`, `plus_minus`, `token_condition` | 2, 2 |
| `plus_minus_against_the_field_unit` | a `plus_minus` unit compared with the field's unit | HP8, the registered unit | any of its examples | 1, 1 |
| `facts_against_the_field_unit` | a fact's unit compared with the field's unit | HP8, the registered unit | any of its examples | 1, 1 |
| `step_10_after_a_refusal_at_step_9` | step 10 runs after step 9's `not_met` | HP3 | a fault of step 9 | 1, 1 |
| `first_unit_reason_only` | step 9 gives its first reason only | HP3 | a fault of step 9 | 1, 1 |
| `unknown_reasons_dropped_beside_not_met` | step 10's `unknown` reasons dropped beside a `not_met` | HP3 | `unchecked`, `unstated`, `unknown_name`, `uncertain` | 7, 6 |
| `conditions_withheld_from_a_refusal` | a read step 10 ends returns no `conditions` | HP3, a refusal at step 10 (planned) | `outside`, `range_outside`, `not_accepted`, `implied_outside` | 2, 2 |
| `disagreement_checks_the_others` | two implied conditions that disagree, and the conditions checked all the same | HP3 | `disagreeing` | 102, 9 |
| `unknown_members_returned_in_an_entry` | a condition's entry returns members the reader does not know | HP5 | `condition`, `plus_minus_entry` | 1, 1 |
| `two_slips_refused_in_a_request` | a request's names two characters off a named one refused | HP5 | any of its examples | 4, 4 |
| `unknown_request_members_refused` | every member a request's place does not name refused | HP5 | `operating`, `requirement_condition`, `tolerance`, `implied`, `implied_record`, `implied_value` | 4, 3 |

A mutant first written for HP5, step 0 keeping an implied value's unknown members, was dropped: no read can
tell it from the core, since step 10 returns a filled condition with the members the reader knows alone.

### The result's mutants

`test_result_mutants.py`, injected as steps 9 and 10's are: a module-level function or name of `read`,
`conditions` or `resolve`. Each names the property that kills it and the kinds or features (`-0`, an unknown
member, a review's way, a statistics status object) one of which the example that kills it must show. The kill
is the examples the derandomised search took, at the small and the original size. Phase A's `condition_unchecked_without_its_condition` died at 1,079 of
2,000 at the small size; since its fault's kind is drawn as one of its own (`unknown_at_step_10`), over twelve
random seeds a search it dies within 507, `reasons_not_merged` within 115 and `best_status` within 310 (they
took up to 1,459 and 1,587 over 24). On main on 2026-10-19 it died at the 10th and 20th examples, but over 24
seed salts (as for the three searches above) at up to the 546th at the small size and the 1,064th at the
original, after the 500th in 4 of the 48; so its search is planned, HP1 over its `unknown_at_step_10` kind with
the fault `unchecked` first ("HP1, an unchecked condition"). Of 2,000 examples of that strategy, at a
derandomised seed and at a random one, 1,657 and 1,640 kill it at the small size and 1,624 and 1,578 at the
original; the others draw a second fault, of step 9, which ends the read before step 10. It dies at the 2nd
example at both sizes, alone and in each of the 24 salts (measured 2026-10-19). Its "dies at" cell names the one
label every example of that strategy shows, so for this search it describes the draw, not a region found.
HP1 itself holds the region to a floor, a result holding `condition_unchecked`, since 2026-10-20 (Mutants, "The
regions held to a floor"). `reasons_not_merged` dies at a
fault of step 8 and at one of steps 9 and 10 alike, as the comment above it in `test_result_mutants.py` says,
and the two of a code the table does not hold die at a fault of step 8 too, as their comments say. S2b-1's six
die at an interval or a
composition (`form_interval`, `form_composition`), the S2 design's other HP6 mutant, an interval's `upper: none`
read as infinity, among them; HP2's `no_statistics_beside_a_composition` took 1,708 and 1,831 examples while
`met` reads drew their `want` among all of plain read's, and since they take their form's own in half the
draws, far fewer. That was still a thin margin: over 20 random seeds (1000 to 1019) its search took 13 to 749
examples at the small size and 49 to 1,115 at the original, and 1,406 on another (PR #37's review, L5). So HP1,
HP2 and HP11 draw a tenth kind, `met_own_member`, a met read of an interval or a composition under the `want`
its form gives: over the same seeds it dies within 4 to 314 at the small size (median 42) and 4 to 215 at the
original (median 26). HP1's two mutants of a code the table does not hold give it the status `not_met` too, so
that it reaches the result and dies at HP1's reason-table assertion, which each names, not at the read's own
look-up of the code (the review's L1). The tenth kind moved every HP1, HP2 and HP11 search.

S2b-2's eleven: five of HP2's under a nominal, three of HP6's on evidence, and three of HP6's second property,
on a nominal's value and assumption. HP1, HP2 and HP11 draw an eleventh kind, `nominal` (declared by a chance
of 0.07, as each kind is), so that HP2's nominal mutants die at a nominal's way within its share of the examples,
not inside `met`, where they died too late; HP2's oracle names `value`, `assumption`, `nominal_invalid` and
`applied` under a nominal itself. Even so the margin was thin: drawn among the eleven kinds, over twelve random
seeds (1000 to 1011) `a_nominal_applied_outside_its_bounds` took up to 1,414 examples and
`a_nominal_applied_wherever_it_is_located` survived 2,000 in two (its fault shows only at a nominal beside a
region or with no location, two fifteenths of a nominal's draws). So the five are planned searches, HP2 over
reads under a nominal alone (`drawn_reads(size, ("nominal",))`): over the same seeds each died within 158
examples at both sizes (the median 1 to 42). Evidence is a fourth form `met_own_member` and HP6 draw. HP1's
`a_code_outside_the_table` dies at a nominal located elsewhere too, an interval read under `value` as without
it, as its comment says. S3b-2's `no_table_beside_its_value` holds HP2's clause of the members that S3b-2
adds, `table` exactly beside a value read from a table, on HP2's table reads.

Since 2026-10-20 a read of every kind is, first, in about one draw in seven, HP1's planned search's read, which
step 10 gives `condition_unchecked` (Mutants, "The regions held to a floor"). That moved four searches past the
500th example more often than main's (each over 200 streams at each size, main against the branch, one-sided
Fisher p below 0.01): `reasons_not_merged` on 18 of 400 (3 on main), `conditions_beside_no_pick` and
`no_unit_beside_alternative_values` on 17 (3; since S3b-2 its row holds the ruled rule's fault,
`unit_beside_alternative_values`), and `no_statistics_beside_a_composition` on 28 (12); and
`stated_without_origin_with_a_condition`, on 3 (5), died at the 656th on the recorded stream. So they are
planned, as HP2's under a nominal are, on the kinds or the form they die at alone: HP1 over its step 8 and steps
9 and 10 kinds ("HP1 at steps 8 to 10"), HP1 over the five kinds `stated_without_origin_with_a_condition` dies
at ("HP1 over the kinds of a stated value"), HP2 over its `alternatives` kind ("HP2 among alternatives"), and
HP2 over `met_own_member`'s compositions ("HP2 over a composition under its own want"). Each kind is held to its chance, not the narrower region where the fault shows (a reason found
twice, a `no_pick` result: 0.04 and 0.03 of HP1's examples, too few for a floor of their own), and a composition
by `met_own_member`'s chance alone.

<!-- kill points of every search of test_result_mutants.py::test_the_result_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `condition_unchecked_without_its_condition` | `condition_unchecked` given without its condition (the S2 design's HP1 mutant) | HP1, an unchecked condition (planned) | `unknown_at_step_10` | 2, 2 |
| `stated_without_origin_with_a_condition` | `stated_without_origin` given a condition | HP1 over the kinds of a stated value (planned) | `met`, `met_own_member`, `nominal`, `step_9_or_10_fault`, `unknown_at_step_10` | 20, 5 |
| `a_code_outside_the_table` | step 13's refusal under a code the table does not hold, given `not_met`, at the reason table's assertion | HP1 | `met`, `step_8_fault`, `nominal_elsewhere` | 115, 260 |
| `reasons_not_merged` | a reason found twice given twice | HP1 at steps 8 to 10 (planned) | `step_8_fault`, `step_9_or_10_fault` | 18, 4 |
| `a_forms_mismatch_outside_the_table` | an interval's or a composition's `want_mismatch` under a code the table does not hold, given `not_met`, at the reason table's assertion | HP1 | `form_interval`, `form_composition`, `form_evidence`, `step_8_fault` | 115, 260 |
| `value_beside_condition_outside` | a read step 10 refuses goes on, and returns its value (the S2 design's HP2 mutant) | HP2 | `step_9_or_10_fault`, `unknown_at_step_10` | 49, 53 |
| `best_status` | the status the best of the reasons' | HP2 | any kind | 49, 53 |
| `conditions_beside_no_pick` | a `no_pick` result holds the first alternative's `conditions` | HP2 among alternatives (planned) | `alternatives` | 1, 1 |
| `unit_beside_alternative_values` | a `no_pick` result holds the first entry's `unit` beside its entries, as the interim rule gave it | HP2 among alternatives (planned) | `alternatives` | 1, 1 |
| `no_statistics_beside_a_composition` | a composition's spread read as its components' alone, so its field's statistics block is not returned | HP2 over a composition under its own want (planned) | `form_composition` | 1, 1 |
| `a_nominal_applied_outside_its_bounds` | a nominal supplies the value wherever it lies | HP2 (planned) | `nominal_outside` | 4, 9 |
| `nominal_invalid_as_want_mismatch` | a nominal outside the bounds gives `want_mismatch`, not `nominal_invalid` | HP2 (planned) | `nominal_outside` | 4, 9 |
| `a_nominal_applied_wherever_it_is_located` | a nominal applied wherever it names the read's field, whatever its location | HP2 (planned) | `nominal_elsewhere` | 27, 12 |
| `applied_names_a_nominal_that_supplied_nothing` | `applied` names a nominal that applies whether or not it supplied the value | HP2 (planned) | `nominal_outside`, `nominal_under_bounds` | 4, 3 |
| `a_nominals_value_dropped_under_not_met` | section 2 item 3 without its exception: no value under `not_met`, a nominal's included | HP2 (planned) | `nominal_inside`, `nominal_on_a_bound` | 1, 1 |
| `expanded_uncertainty_divided_by_its_k` | an expanded uncertainty returned divided by its coverage factor (the S2 design's) | HP6 | `met`, `alternatives` | 9, 11 |
| `results_share_the_record` | a member with nothing to leave out returned as the record's own object (the S2 design's) | HP6 | `met`, `alternatives` | 1, 1 |
| `json_shares_the_result` | a result's JSON shares its objects with the result | HP6 | `met`, `alternatives` | 1, 1 |
| `negative_zero_as_zero` | a value of `-0` returned as `0` | HP6 | `negative_zero` | 1, 1 |
| `upper_none_as_infinity` | an interval's `upper: none` returned as infinity (the S2 design's) | HP6 | `form_interval` | 5, 487 |
| `bounds_without_their_basis` | an interval's bounds returned without their basis | HP6 | `form_interval` | 4, 3 |
| `components_normalised` | a composition's fractions scaled to sum to one, its stated sum dropped | HP6 | `form_composition` | 11, 30 |
| `component_counts_as_doubles` | a component's statistics block's counts written as doubles | HP6 | `form_composition` | 10, 18 |
| `unknown_members_returned` | the members a returned object holds kept whole, those the reader does not know included | HP6 | `unknown_member`, `form_evidence` | 18, 8 |
| `review_as_it_holds` | a review returned as the record holds it, whatever it holds | HP6 | a review's way | 5, 6 |
| `counts_as_doubles` | a count or an index written as a double | HP6 | `met`, `alternatives` | 3, 4 |
| `statistics_status_object_emptied` | a constant's statistics read by the block's shape alone, so that its status object comes back empty (the fault fuzz target 4 found) | HP6 | `statistics_withheld` | 1, 1 |
| `a_reports_review_as_it_holds` | a report's review returned as the record holds it | HP6 | `form_evidence` | 18, 9 |
| `a_reports_provenance_cut_to_a_results` | a report's provenance returned cut to a result's `provenance` (origin and review) | HP6 | `form_evidence` | 18, 9 |
| `unknown_members_kept_in_a_report` | evidence's list copied as the record holds it, a member the reader does not know kept | HP6 | `form_evidence` | 18, 9 |
| `a_nominal_as_a_single` | a nominal's value rounded to single precision | HP6, nominal | `nominal` | 3, 10 |
| `an_assumption_without_its_kind` | the assumption without `acceptance: nominal` | HP6, nominal | `nominal` | 1, 1 |
| `applied_without_the_nominal` | `applied` without the nominal that supplied the value | HP6, nominal | `nominal` | 1, 1 |
| `no_table_beside_its_value` | a value read from a table returned without the table it is read from (S3b-2) | HP2 on a table | `table_at_an_edge`, `table_across_its_range`, `table_statistics` | 2, 2 |
| `labelled_before_step_4` | `hash_not_checked` on a read that ended before step 4 (the S2 design's HP11 mutant) | HP11 | `before_step_4` | 6, 44 |
| `labelled_beside_the_hash_suite` | `hash_not_checked` on a read under the hash suite | HP11 | any kind that reaches step 4 | 1, 1 |

### HP12's mutants

`test_model_mutants.py`. Of the implementation, injected as the other groups' are: a step that stops at its
first fault (the S2 design's HP12 mutant, killed on two faults of one step, B5), the design's mutants of HP1
to HP11 that a result can show, taken from their modules, the broken status object that reports its token,
the fault HP12 found, and open point 1's request half as the implementation read it before S2a-4's fix round.
Of the model, applied to `tests/reference/read_model.py` while the core stays as it is:
its faults no case file kills, and the ten one case file alone kills. Each dies within the `ci`
profile's examples at both sizes, at an example that shows one of the parts, ways, steps or planted rules it
names; a search marked "planned" draws step 8's faults among those named first, or the first part's constants
at a boundary, as HP3's planned searches do, where HP12's own draws meet the fault too seldom for a safe
margin (each measured over six to twelve random seeds). Two more are planned since 2026-10-19, each late over
24 seed salts: HP1's `condition_unchecked_without_its_condition`, drawn with the faults' part whole, died at
the 128th and 168th examples and over the salts at up to the 598th and 811th; it is searched among reads whose
fault of steps 9 and 10 is `unchecked` ("an unchecked condition"): of 2,000 of its examples, at two seeds as
above, 1,446 and 1,527 kill it at the small size and 1,570 and 1,562 at the original (the others draw a second
fault, of step 9, which ends the read there, or a `want` of a suite the claims leave out, which step 0
refuses). And `bounds_given_by_a_constant`, whose planned search drew `valued` whole, every form since S2b-1
and S2b-2 (a constant under `bounds` in one draw in 35), died at the 139th and 523rd and over the salts at up
to the 934th and 594th; it is searched among constants under `want: bounds`, as drawn or with an implied
temperature, every one of which kills it (2,000 of 2,000 at both sizes and both seeds). No example of the three
strategies failed on the core. They die at the 2nd and the 1st example, at both sizes and in each salt
(measured 2026-10-19). The "dies at" cells of these two name the label every example of their strategy
shows, so they describe the draws, not regions found. Since 2026-10-20 the first and second parts draw, inside their kinds, the regions they hold to floors, a
constant's read under `bounds` that reaches step 13 and a result holding `condition_unchecked`, and the first
holds the member the reader does not know to its chance (Mutants, "The regions held to a floor"). The draws of
the regions moved four of these parts' searches past the 500th example more often than main's: each searched
over 200 streams at each size, main against the branch, the model's fault `plus_minus_units_unchecked` on 27 of
400 (13 on main), `request_faults_of_the_first_alternative_alone` on 10 (2), and, under an earlier draft of the
branch, `components_normalised` at the 510th at the small size (2 of 400 as drawn now, none on main) and
`unknown_members_returned` at members no shape defines in evidence's reports rather than a planted one (so on 10
of 80 streams on main too). A fifth, `token_condition_unit_accepted`, went past it on 8 of 200 (3), not beyond
chance (one-sided Fisher p = 0.11), and is planned too, as the review named it. Each is planned on its region: the reads whose first fault of steps 9
and 10 is a `plus_minus` entry's unit ("a plus or minus unit") or a token condition's unit ("a token
condition's unit"); alternatives whose first raises a fault of the request and
each further one one of its own ("request faults apart"); a composition under `want: components`, as drawn or
with an implied temperature ("a composition under components"); and a read whose field holds a member the reader
does not know ("an unknown member"). Each draws only reads the implementation and the model agree on, as S4a's
planned searches must, and its region in every example (`test_model_mutant_table.py`). Of 2,000 examples of the `plus_minus` search, at a derandomised seed and at a random one, 1,888 and
1,832 kill `plus_minus_units_unchecked` at the small size and 1,886 and 1,837 at the original (the others draw
a second fault, of step 9, or a `want` step 0 refuses), all at a read showing its fault; of the composition's, 1,570
and 1,545 kill `components_normalised` at the small size and 1,505 and 1,578 at the original, all at a
composition (measured 2026-10-20). Each dies at the 1st example at both sizes, but `components_normalised`
at the 3rd and 5th. Since 2026-10-21 the first four regions, 0.025 to 0.036 of the parts' draws, are each
held to a floor at `deep` alone, and the unknown member has its floor at `ci` (Mutants, "The regions held to
a floor").
S2b-1's: three of HP3's planned on an own member, HP6's `upper: none`
as infinity and normalised components, and two faults of the model that case files kill, held here on the forms
S2b-1 reads.

`upper_none_as_infinity` is planned since S4a's move onto main (2026-10-20). S4a's alternatives joined the draws
of the first part, and drawn whole it died at the 503rd example at the small size (the 177th and the 29th
before, at the small and the original size), after the margin guard's 500th. It is searched among intervals
under `want: bounds` with no nominal, whose reads give the bounds, `upper: none` among them (an interval's
upper bound is none in one draw in four), and dies at the 7th and the 34th. That search and S4a's planned
searches (the table below) are each held to the agreement on the core as it is
(`test_a_planned_search_draws_only_reads_the_core_agrees_with_the_model_on`, for the first 500 examples and once
for 2,000 on 2026-10-20), so that a mutant they kill dies of its fault.

<!-- kill points of every search of test_model_mutants.py::test_the_implementations_mutant_is_killed_by_the_agreement (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Part | Dies at | Examples |
|---|---|---|---|---|
| `step_0_stops_at_its_first_fault` | step 0 gives its first reason only | two of one step | `step_0` | 1, 1 |
| `step_8_stops_at_its_first_fault` | step 8 gives its first reason only | two of one step | `step_8` | 2, 2 |
| `step_9_stops_at_its_first_fault` | step 9 gives its first reason only | two of one step | `step_9` | 8, 3 |
| `step_10_stops_at_its_first_fault` | step 10 gives its first reason only | two of one step | `step_10` | 4, 9 |
| `broken_status_object_reports_its_token` | a status object that breaks its shape gives its token's `unknown_token` too | unpinned | `broken_status_object` | 10, 45 |
| `declaration_names_ignored` | a slip of a requirement's `field`, or of its conditions' `reason` or `consequence`, ignored | unpinned | `names_a_declaration_gives_a_requirement` | 47, 38 |
| `implied_members_of_the_other_kind_ignored` | an implied value's member of the other kind's shape, and a slip of one, ignored | unpinned | `implied_member_of_the_other_kind` | 26, 51 |
| `condition_unchecked_without_its_condition` | HP1's (planned) | an unchecked condition | `unchecked` | 2, 2 |
| `value_beside_condition_outside` | HP2's | faults | step 10's ending faults | 266, 9 |
| `unknown_tokens_ignored` | HP3's: an unknown token ignored | faults | `step_8` | 4, 10 |
| `missing_represents_accepted` | HP3's (planned) | faults | `statistics_members.represents_missing` | 1, 1 |
| `null_read_as_absent` | HP3's (planned) | faults | `condition_tokens.set_or_measured_null`, `provenance.source_null` | 1, 1 |
| `unknown_condition_names_checked` | HP3's (planned) | faults | `condition_tokens.name_unknown` | 1, 1 |
| `interval_order_unchecked` | HP3's (planned) | faults | `interval.lower_above_upper` | 1, 1 |
| `component_twice_allowed` | HP3's (planned) | faults | `composition.component_repeated` | 1, 1 |
| `element_by_pattern` | HP3's (planned) | faults | `component.element_unknown` | 1, 1 |
| `specimen_facts_merged_across_sections` | HP4's | values | `another_section` | 38, 117 |
| `unknown_members_returned` | HP5's and HP6's: an unknown member returned | an unknown member (planned) | `unknown_member` | 1, 1 |
| `expanded_uncertainty_divided_by_its_k` | HP6's | values | `valued`, `alternatives` | 151, 104 |
| `upper_none_as_infinity` | HP6's | an interval under bounds (planned) | `form_interval` | 7, 34 |
| `components_normalised` | HP6's | a composition under components (planned) | `form_composition` | 3, 5 |
| `floating_point_as_written` | HP7's (planned) | values at a boundary | `at_a_boundary` | 20, 28 |
| `strict_inequalities` | HP7's | values | `valued`, `alternatives` | 1, 1 |
| `plus_minus_ignored` | HP7's (planned) | values at a boundary | `at_a_boundary` | 5, 28 |
| `plus_minus_makes_not_met` | HP7's (planned) | values at a boundary | `at_a_boundary` | 5, 28 |
| `nfkc_before_comparing` | HP8's | faults | `steps_9_and_10` | 2, 2 |
| `case_folded` | HP8's | faults | `steps_9_and_10` | 2, 2 |
| `section_facts_win` | HP9's | values | `valued`, `alternatives` | 179, 91 |
| `hash_over_members_as_written` | HP10's (B7) | values | `valued`, `alternatives` | 6, 5 |
| `labelled_before_step_4` | HP11's | early | `before_step_4`, `stores` | 2, 2 |
| `request_faults_of_the_first_alternative_alone` | step 7 gives the first faulted alternative's request faults alone | request faults apart (planned) | `request_faults_apart` | 1, 1 |
| `first_alternative_in_every_entry` | under `no_pick`, each entry the first alternative's read | values | `alternatives` | 2, 2 |
| `bounds_given_by_a_constant` | step 13 gives a constant's value under `want: bounds` | constants (planned) | `valued` | 1, 1 |
| `minus_zero_given_as_zero` | a constant's `-0` given as `0` | values | `negative_zero` | 1, 1 |
| `every_constant_not_built` | step 13 raises for a constant in S2b's words | values | `valued`, `alternatives` | 1, 1 |
| `text_that_is_no_json_raises` | step 0 raises on a text that is no JSON, where it must refuse | early | `not_json` | 1, 1 |
| `edge_read_from_the_interval_above` | at an edge inside the readable range, the value of the interval above, and no refusal (S3b-2) | tables at an edge | `at_an_edge_inside` | 1, 1 |
| `below_an_edge_from_the_degenerate_interval` | just below an edge, the edge's own two entries read as the interval, which divides by zero (S3b-2) | tables at an edge | `just_below_an_edge`, `just_above_an_edge` | 104, 25 |
| `at_edge_dropped_beside_outside_range` | at an edge outside the readable range, `outside_range` alone (S3b-2) | tables at an edge | `at_an_edge_outside` | 2, 2 |
| `range_checked_before_the_edge` | the range checked before the edge, so an edge outside it is `outside_range` alone and reported coverable (S3b-2) | tables at an edge | `at_an_edge_outside`, `across_an_edge` | 2, 2 |
| `ends_by_strict_inequality` | `<` for `<=` at the readable range's ends (S3b-2) | tables across their range | `at_an_end` | 2, 2 |
| `source_range_ignored` | the readable range `x`'s, whatever `source_range` holds (S3b-2) | tables across their range | the three ways outside | 7, 6 |
| `source_range_widening` | a `source_range` widening the readable range (S3b-2) | tables across their range | the three ways outside | 7, 6 |
| `the_tolerance_widens_the_range` | the readable range widened by the request's tolerance on the axis (S3b-2) | tables across their range | the three ways outside | 27, 9 |
| `outside_at_step_10` | the axis entry's `not_met` given `condition_outside` at step 10, which ends the read before step 11 (S3b-2) | tables across their range | the three ways outside | 6, 4 |
| `points_ignored` | a table holding `points` read as one without (S3b-2) | tables' statistics | `holding_points` | 25, 4 |
| `the_nearest_knots_block` | `points` read: the block of the knot nearest the read in place of the table's (S3b-2) | tables' statistics | `holding_points` | 25, 4 |
| `a_member_dropped_from_the_tables_block` | a table's statistics block returned without its first member (S3b-2's fix round) | tables' statistics | `at_a_knot`, `between_knots` | 1, 1 |
| `range_mismatch_without_its_axis` | a read over a range of the axis gives `want_mismatch` without the axis (S3b-2) | tables' requests | the four ranges | 2, 2 |
| `outside_range_beside_a_range_across_an_end` | `outside_range` beside `want_mismatch` for a range that leaves the readable range (S3b-2) | tables' requests | `range_across_an_end`, `range_outside` | 4, 4 |
| `monotone_the_tolerance_widens_the_range` | the tolerance's widening, searched by the monotonicity property (S3b-2) | tables across their range | the three ways outside | 27, 9 |
| `monotone_source_range_widening` | a `source_range`'s widening, searched by the monotonicity property (S3b-2) | tables across their range | the three ways outside | 7, 6 |
| `step_11_refusal_goes_on_to_step_12` | a read step 11 refused goes on to step 12, which adds `stated_without_origin` (S3b-2's review) | tables' requests | `stated_without_origin` | 3, 3 |
| `an_edge_sets_aside` | a table alternative read at an edge set aside (S4d) | tables among alternatives, `at_an_edge_inside` (planned) | `at_an_edge_inside` | 6, 3 |
| `an_edge_outside_the_range_sets_aside` | `outside_range` set aside beside `at_edge` (S4d) | tables among alternatives, `at_an_edge_outside` (planned) | `at_an_edge_outside` | 8, 3 |
| `set_aside_under_a_covering_extrapolation` | `outside_range` set aside where an extrapolation the request carries covers it (S4d) | tables among alternatives, `kept` (planned) | `kept` | 4, 3 |
| `kept_without_an_extrapolation` | `outside_range` kept with no extrapolation that covers it (S4d) | tables among alternatives, `outside` (planned) | `outside` | 4, 3 |
| `kept_under_any_want` | a table kept where the request carries an extrapolation its place could take, under any `want` (S4d) | tables among alternatives, `kept_under_bounds` (planned) | `kept_under_bounds` | 4, 3 |
| `kept_refuses` | a table an extrapolation covers refusing the field (S4d) | tables among alternatives, `kept` (planned) | `kept` | 4, 3 |
| `over_a_range_sets_aside` | a table read over an operating range of its axis set aside (S4d) | tables among alternatives, `over_an_operating_range` (planned) | `over_an_operating_range` | 4, 3 |
| `over_a_range_refuses` | a table read over an operating range of its axis refusing the field (S4d) | tables among alternatives, `over_an_operating_range` (planned) | `over_an_operating_range` | 4, 3 |
| `over_a_range_gives` | a table read over an operating range counted as a form `want` can give (S4d) | tables among alternatives, `over_an_operating_range` (planned) | `over_an_operating_range` | 10, 7 |
| `request_fault_at_step_11_sets_aside` | no operating value for a table's axis, at step 11, setting the table aside (S4d) | tables among alternatives, `no_operating_value` (planned) | `no_operating_value` | 6, 3 |
| `request_fault_at_step_11_tagged` | step 11's `request_incomplete` given the table's index (S4d) | tables among alternatives, `no_operating_value` (planned) | `no_operating_value` | 1, 1 |
| `set_aside_at_step_10_reaches_step_11` | a table set aside at step 10 refusing the field for its missing operating value (S4d) | tables among alternatives, `no_operating_value_set_aside` (planned) | `no_operating_value_set_aside` | 1, 1 |
| `kept_entry_its_read` | a kept table's `no_pick` entry its read under the extrapolation: the end value (S4d) | tables among alternatives, `kept` (planned) | `kept` | 4, 4 |
| `over_a_range_entry_without_step_12_labels` | an over-range table's `no_pick` entry with its read's labels, none (S4d) | tables among alternatives, `over_an_operating_range` (planned) | `over_an_operating_range` | 4, 3 |
| `entry_labels_of_the_first_alternative` | a kept or over-range table's entry with the first stored alternative's labels (S4d) | tables among alternatives, `over_an_operating_range` (planned) | `over_an_operating_range` | 66, 19 |
| `entry_labels_of_the_last_alternative` | a kept or over-range table's entry with the last stored alternative's labels (S4d) | tables among alternatives, `over_an_operating_range` (planned) | `over_an_operating_range` | 4, 3 |
| `kept_unknown_dropped_beside_two_or_more` | a kept table's `unknown` reasons dropped beside `no_pick` or `want_mismatch` (S4d) | tables among alternatives, `kept` (planned) | `kept` | 4, 4 |
| `outside_range_refuses` | `outside_range` refusing the field, as every other `not_met` does (S4d) | tables among alternatives, `outside` (planned) | `outside` | 6, 3 |
| `narrowed_alternative_kept` | the table moved off its range kept (S4d) | tables among alternatives, `outside` (planned) | `outside` | 4, 3 |
| `set_aside_by_its_range_beside_the_one_left` | the reasons of a table set aside by its range reported beside the one left (S4d) | tables among alternatives, `outside` (planned) | `outside` | 6, 3 |
| `a_range_across_the_readable_end_outside` | a range of a table alternative's axis past the readable range's end given `outside_range` beside its `want_mismatch` (S4d's review) | tables among alternatives, `over_an_operating_range` (planned) | `over_an_operating_range` | 3, 54 |

<!-- kill points of every search of test_model_mutants.py::test_the_models_seeded_mutant_is_killed_by_the_agreement (scripts/gen_kill_counts.py) -->
| Fault of the model | Part | Dies at | Examples |
|---|---|---|---|
| `plurals_not_slips` | unpinned | `plural_of_two_characters` | 199, 12 |
| `member_checked_off_its_row` | unpinned | `form_off_its_row` | 90, 66 |
| `composition_checked_beyond_its_basis` | unpinned | `composition_basis_off_its_row` | 110, 119 |
| `broken_status_object_reports_its_token` | unpinned | `broken_status_object` | 10, 45 |
| `members_of_the_other_kind_read` | unpinned, at the record condition's refusal or the implied value's | `members_of_the_other_kind`, `implied_member_of_the_other_kind` | 4, 11 |
| `members_of_the_other_kind_ignored` | unpinned, at the record condition's refusal or the implied value's | `members_of_the_other_kind`, `implied_member_of_the_other_kind` | 4, 11 |
| `slips_of_alternatives_ignored` | unpinned | `alternatives_slip_beside` | 1, 1 |
| `declaration_names_not_named_in_a_request` | unpinned | `names_a_declaration_gives_a_requirement` | 47, 38 |
| `population_level_checks_stop_at_a_missing_member` | unpinned | `checks_beside_a_broken_object` | 164, 84 |
| `dof_token_unchecked_under_student_t` | unpinned | `checks_beside_a_broken_object` | 137, 473 |
| `every_status_object_an_unstated_kind` | unpinned | `checks_beside_a_broken_object` | 185, 78 |
| `every_forms_member_named_at_a_field` | unpinned | `another_forms_member_slipped` | 2, 2 |
| `input_specimens_optional` | faults (planned) | `derivation.input_specimens_missing` | 1, 1 |
| `hash_not_checked_before_step_4` | early | `request`, `before_step_4`, `stores` | 1, 1 |
| `token_condition_unit_accepted` | faults (planned: a token condition's unit first) | `unit_token_condition` | 1, 1 |
| `plus_minus_units_unchecked` | faults (planned: a `plus_minus` unit first) | `unit_plus_minus` | 1, 1 |
| `implied_values_compared_by_value` | unpinned | `implied_zero_beside_minus_zero` | 18, 9 |
| `stated_without_origin_unreported` | values | `valued`, `alternatives` | 60, 106 |
| `ies_not_a_plural` | unpinned | `plural_of_two_characters` | 416, 147 |
| `review_of_both_shapes_read_as_its_status` | unpinned | `review_of_both_shapes` | 8, 3 |
| `reviewed_review_keeps_a_status_objects_members` | unpinned | `review_of_both_shapes` | 9, 4 |
| `donor_age_of_neither_accepted` | faults (planned) | `specimen.fact_neither_value_nor_range` | 1, 1 |
| `value_given_by_an_interval` | values | `form_interval` | 74, 38 |
| `bounds_given_by_a_constant` | values | `form_constant` | 9, 9 |
| `evidence_entry_provenance_unchecked` | faults (planned) | `evidence_provenance.*`, each of the six faults of a report's provenance | 1, 1 |
| `entry_withheld_in_part_read` | faults (planned) | `evidence_list.report_withheld_in_part`, `.withheld_report_opened` | 1, 1 |
| `unit_returned_without_its_reason` | evidence's unit with a reason (planned) | `unit_with_a_reason` | 52, 52 |
| `two_nominals_for_one_field` | early (planned: step 0's catalogue, the first fault a nominal's) | `two_nominals_for_one_field` | 52, 45 |
| `nominal_ignored_over_alternatives` | alternatives under a nominal (planned) | `nominal_over_alternatives` | 1, 1 |
| `nominal_applied_under_no_pick` | alternatives under a nominal (planned) | `nominal_over_alternatives` | 1, 1 |
| `nominal_outside_supplies_the_value` | values under a nominal (planned) | `nominal_outside` | 7, 35 |
| `request_fault_sets_aside` | a refusal by a fault of the request (planned) | `refused` | 3, 3 |
| `nominal_not_applied_to_the_one_left` | an interval under a nominal (planned) | `one_left` | 2, 2 |
| `unknown_reasons_dropped_beside_no_pick` | outcomes of step 7 (planned) | `want_mismatch`, `no_pick` | 7, 5 |
| `set_aside_reasons_beside_no_pick` | outcomes of step 7 (planned) | `want_mismatch`, `no_pick` | 58, 39 |
| `unit_of_the_first_stored_alternative` | evidence set aside first (planned) | `no_pick` | 52, 52 |
| `table_returned_whole` | tables' statistics (planned, S3b-2's review) | `unknown_member` | 5, 7 |
| `set_aside_alternative_reaches_step_11` | tables among alternatives, `no_operating_value_set_aside` (planned, S4d) | `no_operating_value_set_aside` | 1, 1 |
| `over_a_range_entry_unlabelled` | tables among alternatives, `over_an_operating_range` (planned, S4d) | `over_an_operating_range` | 4, 3 |
| `kept_for_an_extrapolation_under_any_want` | tables among alternatives, `kept_under_bounds` (planned, S4d) | `kept_under_bounds` | 1, 1 |

S4a's five are the faults of the model's step 7 that one case file alone kills, each searched over S4a's
alternatives alone (`model_strategies.outcomes_of_step_7`), three of them narrowed further, as HP27's planned
searches are: among all S4a's outcomes, `request_fault_sets_aside` took 311 and 211 examples,
`nominal_not_applied_to_the_one_left` 395 and 52, and `unit_of_the_first_stored_alternative` 1,116 and
survived 2,000 at the original size (2026-10-19, at `ci`); the table's counts are S4a's fix round's, once a
set-aside alternative's form was drawn too. HP12 draws S4a's alternatives in two of its
alternatives kind's six ways, the base field's form planted for the form's audit, so that the model and the
read meet step 7's outcomes. Its audit holds those draws, `standing`, to the floor of their chance, measured
(about one example in six by the draw; 0.119 to 0.178 over 12 runs of the draws at `ci`; declared 0.10), and
a control stops drawing them (`tests/unit/test_audit_controls.py`). The five outcomes among them are not
audited here: each is about one HP12 example in 30, whose floor at `ci` is 0, below what the audit judges;
HP27's audit holds each, drawn first by the same strategy.

S2b-2's seven are six of the eight the table listed as no read S2 built could show them (an evidence entry, at
which the core raised; a unit held as a status object, which only `biocompatibility.evidence` registers; a
nominal, for which no strategy drew one), and one of its own, a nominal outside the bounds that supplies the
value (`tests/reference/mutants.py`). HP12 draws evidence among its forms, its unit with a reason in half its
draws, an interval under a nominal in half its draws, and intervals over alternatives under one, and step 0's
catalogue holds eight faults of acceptances. Five searches are planned: a report's faults among step 8's
(drawn first among those named), the nominal's ways alone, alternatives under a nominal alone, step 0's
catalogue with a nominal's fault first, where `two_nominals_for_one_field` met its fault at 1,285 and 711
examples among all of step 0's 60, and evidence whose unit holds a reason, where
`unit_returned_without_its_reason` took up to 1,440 over twelve random seeds (1000 to 1011). Over those seeds
the planned searches of `two_nominals_for_one_field`, `nominal_outside_supplies_the_value` and
`unit_returned_without_its_reason` died within 123, 123 and 94 examples at both sizes, and HP4's
`every_field_checked_beside_evidence`, drawn whole, within 400.

S4d's part, tables among alternatives (`test_the_read_agrees_with_the_model_on_tables_among_alternatives`),
draws one of HP39's two parts first, each held to its floor, then, as HP39 draws them, the others' outcome and
the table's way by chance (`table_alternatives_strategies.py`). Each of S4d's mutants of step 7 but
`extrapolation_applied_under_no_pick`, whose fault shows in what the read applied alone, outside the result's
JSON (`APPLIED_ALONE`), is searched there as a planned search of the way where it shows, HP40's three at a
table outside its range; and so are the three of the model's twelve faults of step 7's rows for a table that
one case file alone kills. Each of these planned searches draws only reads the core and the model agree on
(`test_model_mutant_table.py`). One more mutant is HP12's alone (S4d's review): a read over a range of the
table's axis that runs past the readable range's end given `outside_range` beside its `want_mismatch`
(`a_range_across_the_readable_end_outside`), where section 1 gives "no other reason of that step". HP12 kills it
at the agreement with the model. HP39 fails on it only at the check of its draw (`check_drawn`: the table's read
alone then stands as set aside), not at an assertion of the read, which is no kill. It shows only where the
range's upper end lies past the readable range's, so it holds that draw: with the end cut to the double above
the operating value, which lies inside the range, it survives 2,000 examples at both sizes. Over 40 streams a
size it died at the 125th example at the latest.

Listed, with the reason no read shows it: `results_share_the_record` (a shared object never shows in JSON; HP6
holds the core to sharing nothing). `units_stored_differently_read_as_no_pick`, listed here until S4a, became
the text's reading with the maintainer's ruling on `unit` under `no_pick` (2026-10-19), and is replaced in
the model's table by `unit_of_the_last_remaining_alternative`, which two case files kill
(`tests/reference/README.md`). The design's other mutant not searched here: HP6's result sharing the stored
object (JSON again).

### HP4 and HP10's mutants

`test_invariance_mutants.py`, at the ways (HP4) and kinds (HP10) each names, and three of HP4's at the form
of the field their read holds, a constant, an interval, a composition or evidence.

<!-- kill points of every search of test_invariance_mutants.py::test_the_invariance_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `specimen_facts_merged_across_sections` | a field's specimen holds every section's facts (the S2 design's HP4 mutant) | HP4 | `another_section_specimen` | 14, 11 |
| `every_field_checked` | step 8 checks every field of the record | HP4 | `another_field` | 1, 1 |
| `every_section_specimen_checked` | step 8 checks every section's specimen | HP4 | `another_section_specimen` | 11, 10 |
| `every_field_checked_beside_an_interval` | step 8 checks every field of the record where it reads an interval (PR #37's review) | HP4 | `another_field`, at an interval | 28, 36 |
| `every_section_specimen_checked_beside_a_composition` | step 8 checks every section's specimen where it reads a composition (PR #37's review) | HP4 | `another_section_specimen`, at a composition | 46, 395 |
| `every_field_checked_beside_evidence` | step 8 checks every field of the record where it reads evidence (S2b-2) | HP4 | `another_field`, at evidence | 137, 5 |
| `section_specimen_unchecked` | the read field's own section's specimen not checked (HP3's) | HP4, refusal | `own_section_specimen` | 1, 1 |
| `hash_over_members_as_written` | the recomputed hash taken over the members in the order the source writes them (the S2 design's HP10 mutant, B7) | HP10 | any kind | 3, 5 |
| `integers_read_as_integers` | a number spelled without a fraction or exponent read as an integer | HP10 | any kind | 1, 1 |

### The monotonicity relations' mutants

`test_monotonicity_mutants.py`, each searched with the relation it names (the spike's mutants that S2's forms
reach, under its names where the core has them; with a world's trigger built in where the relation draws a way
first). Over twelve random seeds a search, each died within 927 examples, `floating_point_as_written` the
slowest.

<!-- kill points of every search of test_monotonicity_mutants.py::test_the_relations_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Relation | Examples |
|---|---|---|---|
| `row_requirements_ignored` | a condition the row requires, absent, not checked (the spike's `absent_required_skipped`) | N1r | 2, 2 |
| `required_with_ignored` | a condition another requires with its token not checked | N1r | 75, 11 |
| `requested_absent_skipped` | a condition the request names and the record lacks skipped | N1r | 6, 4 |
| `origin_default` | an absent origin read as `measured_by_contributor` | N2 | 9, 214 |
| `status_object_passes` | a condition held as a status object gives a met entry | N3r | 9, 4 |
| `status_in_any_member` | a status object in `origin` passes step 8 | N3r | 2, 2 |
| `plus_minus_widens` | a bound widens the tolerance instead of narrowing it | N4 | 2, 2 |
| `tolerance_inverted` | a value met where it lies outside the tolerance | N5r | 2, 2 |
| `missing_operating_met` | a tolerance with no operating condition passes step 0 and gives a met entry | N6 | 77, 59 |
| `implied_overrides_a_stated_value` | an implied condition overrides a stated one (`implied_overrides`) | N8 | 2, 2 |
| `tolerance_inverted_widened` | as `tolerance_inverted` | P1 | 2, 2 |
| `plus_minus_widens_removed` | as `plus_minus_widens` | P2 | 2, 2 |
| `accept_list_as_its_last_token` | an accept list read as its last token alone | P3 | 2, 2 |
| `operating_conditions_checked` | every condition the request operates checked, as one with no tolerance | P4 | 2, 2 |
| `sd_ignored` | an `sd` or unstated plus or minus ignored | S1 | 3, 5 |
| `status_object_read_as_met` | as `status_object_passes` | S2 | 1, 1 |
| `not_applicable_anywhere` | `not_applicable` read as met on any condition | S2 | 3, 12 |
| `floating_point_as_written` | section 5's comparisons in floating point (`float_compare`) | S5 | 200, 3 |
| `implied_fills_any_status` | an implied condition fills a condition held as any status object (step 10's) | N3r | 9, 73 |

The unrestricted twins, N1 (any condition removed) and N3 (any member made a status object), fail on the core
as they must, on N1r's and N3r's own draws, by one of the ways that hold their counterexamples
(`UNRESTRICTED_WAYS`):

<!-- kill points of every search of test_monotonicity_mutants.py::test_the_unrestricted_twins_mutant_is_killed_by_the_core (scripts/gen_kill_counts.py) -->
| Twin | The way that holds its counterexample | Examples |
|---|---|---|
| `N1` | an unchecked condition, or one an implied condition fills, removed from a world otherwise met | 17, 10 |
| `N3` | `unstated` where an implied condition fills it | 8, 6 |

A generator that lost
those ways fails these searches; worlds that lost the shapes fail the worlds' audit
(`test_the_worlds_hold_the_shapes_the_restrictions_are_for`).

### The table evaluator's mutants

`test_evaluate_mutants.py`. Each fault replaces one of `core/evaluate.py`'s module-level functions, which the
evaluator looks up when it runs, and each mutant names the assertions its kill may fail: an assertion's
message begins with its label, and the search fails where the first failure is another's. HP17 checks where
every operating value lies before any number, so that a fault of range or edge dies as one, not by the end
value it leads to. The first eight are the S3 design's (section 6.6). Of the other ten, six are broken
evaluators of the table evaluation suite's README made a reader's, the text's rules since the design among
them (no number beyond an edge, the readable range's end value); one raises where a read returns a refusal
(the code design's rule 1); two reach the assertions no design mutant does (`interval`, `monotone`); and one
is the evaluator before the S3b-1 review, whose log-log value, rounded from 50 digits, a halfway point may
leave one unit off. The kill is the examples the derandomised search took, at the small and the original size
(recorded by `scripts/gen_kill_counts.py`, below).

<!-- kill points of every search of test_evaluate_mutants.py::test_the_evaluator_mutant_is_killed_at_its_assertion (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `bracket_search_off_by_one_at_a_knot` | the bracket search one past a knot (`bisect_right`): a knot read through the interval above it, the last one past the end | HP17 | `raised`, `value` | 1, 1 |
| `loglog_interpolated_linearly` | a log-log table interpolated linearly | HP17 | `value` | 3, 10 |
| `log10_for_x_beside_ln_for_y` | the log-log slope taken with `log10` for `x` and `ln` for `y` | HP17 | `value` | 3, 22 |
| `formulas_in_doubles` | `read_side_contract.md` section 7 item 2's formulas in doubles, as written, a knot read through the interval below it (one unit off at upper knots; dividing by zero between adjacent doubles) | HP17 | `raised`, `value` | 2, 2 |
| `source_range_ignored` | the readable range is `[x[0], x[-1]]` | HP17 | `position` | 7, 6 |
| `source_range_widening` | a `source_range` wider than `x` widens the readable range | HP17 | `position` | 3, 6 |
| `knot_through_a_fraction` | a knot's `y` returned through a fraction, which loses `-0` | HP18 | `stored` | 5, 5 |
| `t_from_the_upper_knot` | `t` computed as `(x - x1) / (x1 - x0)` | HP19 | `between` | 5, 8 |
| `extrapolated_beyond_an_edge` | beyond an edge from the readable range, the end value | HP17 | `position` | 7, 6 |
| `range_judged_before_the_edge` | the readable range judged before the edge, so that an edge outside it reads as outside (the S3 design's HP20 mutant) | HP17 | `position` | 7, 6 |
| `edges_ignored` | no operating value lies at an edge | HP17 | `position` | 3, 5 |
| `end_value_at_the_ends_of_x` | outside the readable range, the value at `x[0]` or `x[-1]`, as NumPy's `interp` clamps | HP17 | `value` | 7, 6 |
| `refusal_raised` | at or beyond an edge, an exception in place of no number | HP17 | `raised` | 3, 5 |
| `ends_excluded` | the readable range's ends excluded (`<`) | HP17 | `position` | 1, 1 |
| `below_an_edge_from_the_interval_above` | just below an edge, the interval above it (a log-log value read through it can lie beyond every double, where its exact value raises) | HP17 | `raised`, `value` | 3, 29 |
| `between_knots_the_interval_above` | between two knots, the interval above them | HP19 | `interval` | 3, 6 |
| `interval_read_backwards` | `t` computed as `(x1 - x) / (x1 - x0)`: inside its interval's `y`, run the wrong way | HP19 monotone | `monotone` | 32, 9 |
| `loglog_not_exact_at_ties` | a log-log value in decimal at 50 digits, rounded once: one unit off at some values halfway between two doubles, which the least subnormals give | HP17 | `value` | 66, 96 |

### Step 7's mutants (S4a)

`test_alternatives_mutants.py`, each injected as the result's are, at a function of step 7 in `core/read.py`
(its standing, each of the three rules of what an outcome reports, the reading of one alternative) or around
`_read_alternatives`, and each dying at the outcome and the assertion it names. Five are planned searches,
HP27 over draws narrowed to where the fault shows, since HP27's own draws met it too seldom: drawn among all
five outcomes, `request_fault_sets_aside` took 628 and 565 examples, `nominal_dropped_over_alternatives` 656
and survived 2,000 at the small size, and `the_first_stored_unit` 1,990 and survived 2,000 at the original.
The fourth, `gives_reads_the_first_stored_form`, a review's hand mutant that survived every test, judges an
interval under a nominal by the first stored alternative's form: it shows only where a non-interval is stored
first and set aside and every alternative that stays is an interval, which the draws reach since a set-aside
alternative is held in either form; under a nominal alone it took 15 and 739, so it is searched with the
set-aside alternative stored first. The fifth, `the_last_staying_unit`, gives every entry the last staying
alternative's unit under `no_pick` (since S3b-2 each entry holds its own; before, the result held one): it
shows only where the alternatives that stay hold units that differ, which only evidence allows (a status
object with another `reason`). Drawn among all five outcomes and every form it died at the 86th and 355th
example (S4a's fix round), and, once a set-aside alternative's form was drawn, at the 495th and 732nd, the
second after the margin guard's 500th; it is searched among evidence under `no_pick`, where it died at the
52nd and 80th, and at the 52nd and 73rd once each entry held its own unit (S3b-2). Each planned search is also
held to HP27's check on the core as it is, which it must pass
(`test_a_planned_search_draws_only_reads_the_core_passes`, for the first 500 examples, the margin guard's
horizon, and once for 2,000 on 2026-10-20), so that a mutant it kills dies of its fault. Counts at both sizes,
one seed's, the derandomised search's, in the alternatives shard at `ci` (2026-10-19, S4a's fix round;
recorded again on the move onto main, 2026-10-20).

<!-- kill points of every search of test_alternatives_mutants.py::test_the_alternatives_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `refusal_sets_aside` | an alternative refused at step 8 or 9 set aside | HP27 | `refused` | 77, 6 |
| `cannot_give_sets_aside` | an alternative whose form `want` cannot give set aside | HP27 | every outcome but `all_set_aside` | 7, 3 |
| `request_fault_sets_aside` | an alternative a fault of the request ends set aside | HP27 (planned) | `refused` | 3, 3 |
| `set_aside_reasons_beside_the_one_left` | the set-aside alternatives' reasons reported beside the one left | HP27 | `one_left` | 97, 114 |
| `waiting_reasons_beside_two_or_more` | a staying alternative's `not_met` reasons reported beside `no_pick` or `want_mismatch` | HP27 | `want_mismatch`, `no_pick` | 19, 3 |
| `unknown_reasons_dropped_beside_two_or_more` | the staying alternatives' `unknown` reasons dropped there | HP27 | `want_mismatch`, `no_pick` | 20, 10 |
| `set_aside_reasons_dropped_where_refused` | the set-aside alternatives' reasons dropped from a refusal | HP27 | `refused`, `all_set_aside` | 2, 2 |
| `waiting_reasons_dropped_where_refused` | a staying alternative's waiting reasons dropped from a refusal | HP27 | `refused` | 77, 6 |
| `index_among_those_that_stay` | an index counted among the alternatives that stay | HP27 | `one_left`, `no_pick` | 118, 66 |
| `request_fault_tagged` | a fault of the request given the alternative's index | HP27 | `refused` | 79, 80 |
| `gives_reads_the_first_stored_form` | an interval under a nominal judged by the first stored alternative's form | HP27 (planned) | `no_pick` | 3, 12 |
| `nominal_dropped_over_alternatives` | a nominal ignored over alternatives | HP27 (planned) | `refused`, `one_left` | 2, 2 |
| `the_last_staying_unit` | under `no_pick`, every entry's unit the last staying alternative's | HP27 (planned) | `no_pick` | 52, 73 |
| `the_first_stored_unit` | under `no_pick`, every entry's unit the first stored alternative's, set aside or not | HP27 (planned) | `no_pick` | 52, 59 |
| `labels_kept_where_refused` | the alternatives' labels on a result that rests on none | HP27 | `refused`, `want_mismatch` | 269, 87 |
| `outcome_decided_in_reading_order` | the reading stops at the first alternative that refuses | HP28, order | `refused` | 92, 21 |
| `the_one_left_untagged` | the one left's reasons without their index | HP28, wrapping | any outcome | 6, 3 |
| `set_aside_refuses` | an alternative set aside refusing the field | HP29, set aside | every outcome but `all_set_aside` | 6, 3 |
| `the_first_staying_read` | with several alternatives left, the first is read (the spike's `first_alternative`) | HP29, two staying | `no_pick` | 2, 2 |

Seven of them are also broken implementations that an S4a case file catches
(`tests/conformance/test_runner_can_fail.py`), and the reference model's own step 7 has sixteen seeded faults
of its own, each killed by a case file (`tests/reference/README.md`).

Not drawn: an alternative that a fault of the request ends holding a reason of its own. Only step 8's
`entries_withheld` could stand there (evidence with some reports withheld, beside two implied conditions
that disagree in the same alternative), and the strategies remove withheld reports
(`result_strategies.without_withheld_reports`). So nothing here would see that alternative's own reasons
lose their index (a review's hand mutant did so and survived every test); the text gives the index
(`read_side_contract.md` section 2 item 2) and `_found_reading` tags every reason but the request's fault.

### The table form's mutants (S3a)

`test_table_form_mutants.py`, each injected at a function or a table of `core/fields.py` or
`core/value_shapes.py` that the table reader looks up when it runs (each rule of a table's step 8 is a
function of its own, `_abscissae`, `_one_y_for_each_x`, `_edges_once`, `_positive_where_log_log`, `_points`,
`_shares_a_value_no_edge`, `_axis_condition`, so that a fault replaces one), and each dying at a fault, kind or
way it names and at the assertion it names. Eighteen are the S3 design's mutants of HP13 to HP16
(section 6.5); `a_tables_fault_refuses_its_records_other_fields` is not, and HP13's read of the record's other
field sees it; nor is `ends_of_an_empty_x_read`, the code S3a's review found raising on a table whose `x` is
empty beside an edge or a `source_range` (its H1), which HP13's fault of that table kills, the raise read as
an outcome no rule gives. Counts at both sizes, one seed's, the derandomised search's, in the step8_mutants
shard at `ci` (2026-10-20, S3a and its review's fix round).

Three searches are planned (S3a's review, M4 and L3), each drawing alone the faults where its mutant shows,
from the part HP13 draws them in. Over 40 seeds a size, HP13's own draws first met
`zero_and_minus_zero_by_sign_bit` at the base on 15 of 80 streams: a base drawn with an edge at zero, held as
`-0` and `0`, is one that mutant itself refuses, and the check read the base first. Its search draws the two
faults of an edge at zero, on bases whose zeros are each held as `0` (`zeros_held_alike`, which reads the same
by table item 1); `x_strictly_increasing`, which refuses any base holding an edge, is searched on the near
miss alone, an edge at zero held as `-0` and `0`, whose read it refuses before its base is read, and now names
that fault and its assertion alone, where it admitted the base. Each of the two dies at the near miss whatever
the base, a fault HP13 draws first, held to its draw floor of 50 at `ci` with an audit control. And
`axis_condition_held_as_a_value_accepted` showed only where `axis_condition_held_otherwise` held the axis
condition as a value, one of the fault's three ways (one draw in 21, a draw floor of none: it died as late as
the 489th example); the fault now holds it as a value, a number or a range in the axis's registered unit, in
two of its four ways, a region HP13's tokens part records and declares by its chance, 0.07 (a floor of 10;
0.0876 of the examples on average over 18 runs at `ci`, 0.055 at least), with an audit control, and the search
draws that way alone (`axis_conditions_held_as_a_value`). `test_table_form_mutant_table.py` holds each planned
search to the core as it is for its first 500 examples at `ci` (200 at `dev`), at both sizes, so that a mutant
it kills dies of its fault. Over 40 seeds a size (2026-10-20, the search's settings with only the seed
changed), each died at the first or second example, at its fault and assertion; every other table form mutant
died at its own assertion too, none past the 267th example.

Controls hold HP13's last assertion, that a fault is its rule's alone (`test_table_form_controls.py`). Six
hand-made builders each give `form_invalid` as their fault does, so HP13's other assertions pass them: one of
`token_not_a_string` that also swaps `x`'s first two knots, of `source_range_reversed` that also shortens `y`, of
`y_longer` that also lists `x`'s first knot as an edge, of `edge_at_an_end` and of `repeated_x_no_edge` that
also shorten `y`, and of `log_log_not_positive` whose scheme is not a string. On each of the first 100
derandomised examples of its fault, at both sizes, each fails at that assertion, and the same builder without
its extra break passes. A control for each of the 28 faults that have an undo breaks, one at a time, every member
its rule does not judge (declared there, apart from `JUDGED`, so that an undo made broader fails against it) on
the faulty read, and holds that the undo leaves it broken; an undo of `edge_listed_twice` made broader by `x`,
`y`, the `source_range`, the scheme, the axis, its unit or `points`, or by all of `x`, `y` and the edges, is
shown failing it. They hold every example, so they are not mutant searches and record no kill; they keep no
example database.

<!-- kill points of every search of test_table_form_mutants.py::test_the_table_form_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `y_length_unchecked` | `y` of another length than `x` taken | HP13, knots | `y_longer`, `y_shorter` | 1, 1 |
| `x_strictly_increasing` | `x` required strictly increasing, which refuses every edge | HP13, edges (planned) | `zero_edge_both_signs` | 1, 1 |
| `edge_at_an_end_accepted` | an edge at `x[0]` or `x[-1]` taken | HP13, edges | `edge_at_an_end` | 1, 1 |
| `zero_accepted_in_log_log` | `>=` for `>`: a log-log table's zero taken | HP13, edges | `log_log_not_positive` | 6, 96 |
| `unknown_scheme_read_as_linear` | any string taken as a scheme | HP13, tokens | `scheme_unknown` | 1, 1 |
| `axis_condition_held_as_a_value_accepted` | the axis condition held as a value taken | HP13, tokens (planned) | `axis_condition_held_otherwise`, held as a value | 1, 1 |
| `zero_and_minus_zero_by_sign_bit` | `-0` and `0` compared by sign bit, in `x` and in `edges` | HP13, edges (planned) | `zero_edge_both_signs`, `edges_zero_and_minus_zero` | 2, 2 |
| `token_condition_axis_form_invalid` | a token condition's name as axis given `form_invalid` | HP13, tokens | `axis_token_condition` | 2, 2 |
| `source_range_unchecked` | `source_range` neither shaped nor held to `x` | HP13, `source_range` and `points` | a `source_range` fault | 1, 1 |
| `disjoint_source_range_accepted` | a `source_range` disjoint from `x`'s range taken | HP13, `source_range` and `points` | `source_range_disjoint` | 119, 4 |
| `points_ignored` | a table holding `points` read | HP13, `source_range` and `points` | `points`, `points_null` | 20, 39 |
| `source_range_meeting_x_only_at_an_edge_accepted` | a `source_range` meeting `x`'s range only at an edge taken | HP13, `source_range` and `points` | `source_range_only_at_an_edge` | 2, 2 |
| `points_form_invalid` | `form_invalid` in place of `points_unsupported` | HP13, `source_range` and `points` | `points`, `points_null` | 20, 39 |
| `ends_of_an_empty_x_read` | an edge's and `source_range`'s rules read `x[0]` and `x[-1]` of an empty `x`, and raise | HP13, `source_range` and `points` | `x_empty_beside_edges_or_a_source_range` | 6, 70 |
| `a_tables_fault_refuses_its_records_other_fields` | a table's fault refuses every field read from its record | HP13, knots | any, at the neighbour | 1, 1 |
| `edge_slip_ignored` | a member one slip from `edges` ignored | HP14 | a slip | 9, 27 |
| `point_slip_ignored` | `points` not named at a table's place, so a slip of it is ignored | HP14 | a slip | 7, 5 |
| `axis_unit_reason_without_its_condition` | a table's `unit_mismatch` without its axis | HP15 | any kind | 1, 1 |
| `axis_unit_compared_under_nfkc` | units compared after NFKC | HP15 | `compatibility_equal` | 1, 1 |
| `label_blind_to_the_axis` | the row's label taken on a table over any axis | HP16 | `on_its_rows_axis` | 1, 1 |

### A table's steps 10 to 13's mutants (S3b-2)

`test_table_read_mutants.py`, each injected at a function the read looks up when it runs (`read.form_range`, step
11; `read.axis_status`, the axis entry; `evaluate.readable_range`, `in_readable_range` and `interval`; the read's
`check_conditions`, step 10; `fields._points`; `read.read_value_field`), and each dying at a way it names and at
the assertion it names: the S3 design's mutants of HP20 to HP23 and of its monotonicity property (section 6.7),
the last two searched by that property too, the same faults as two of HP21's. Two die at a way beside the one the
design names, where the fault shows as well: the degenerate interval just above an edge whose interval above ends
at another edge, and the range checked first beyond an edge outside the range, reported coverable.
`monotone_source_range_widening` is a planned search of the monotonicity property, one double outside alone, a
way the property draws first and holds to its floor: over its four ways it died at the 327th example on one of 40
streams. `the_nearest_knots_block` injects `points_ignored` too, and no knot block shows without `points` read,
so it dies where that one does; `a_member_dropped_from_the_tables_block` (S3b-2's fix round) gives HP22's clause
of the block as stored at every read a mutant of its own. The review's hand mutant of step 11's report on an edge
on the readable range's end (`read_side_contract.md` section 5: "or on that end"), read as none between the read
and the range, is two rows, one for each end (S3b-2's second fix round), searched by HP20 across an edge alone,
the way that draws such an edge in half its draws (planned: over HP20's five ways they died after the 500th
example on 1 or 2 of 40 streams a size, the latest at the 934th; across an edge alone, at the 150th at the
latest). The report has a reader in a result only where an extrapolation meets such an edge (S3c, and S4d's
step 7), which HP12 draws nowhere, so HP12 cannot search those two (`REPORT_ALONE`). HP12's table part
searches each of the sixteen others as well (`test_model_mutants.py`, its rows below its own), each a planned search of the part's kind of the family whose property kills it (`TABLE_PARTS`), a kind the
part draws first and holds to its floor: searched over the whole part, a tolerance's widening died after the
margin guard's 500th example on some streams (the 664th and the 1,301st, in a first form of the mutant, of the 24
and 7 streams run a size) and `at_edge` dropped beside `outside_range` at the 628th of 40, and those of a
`source_range` died at an edge of another family as well. Three die at more of their kind's ways than their
property draws (`WHERE_THE_TABLE_PART_SHOWS`). Each of the part's four planned searches is held to the agreement
on the core as it is, as S4a's are (`test_a_planned_search_draws_only_reads_the_core_agrees_with_the_model_on`,
`PLANNED_BY_S3B2`). Its region is the kind, drawn first and held to its floor; each mutant shows at some of the
kind's ways, which its own property draws first and holds to a floor, and no control holds the kind to exactly
where each mutant shows (an open point). Over 40 streams a size (2026-10-21, again with the fix round's draws
and its mutant), every search here and in HP12's table part dies at a way and an assertion its row names, the
latest at the 183rd example (the 198th before); the second fix round's four searches (the two above, and HP12's
two of the review's kinds, below) over 40 more a size, the latest at the 150th. Counts at both
sizes, one seed's, the derandomised search's, in the conditions shard at `ci` (2026-10-21).

HP12's table part searches two more of the review's kinds (S3b-2's second fix round), each where its fault
shows, a region the part draws beside the way and plants (`table_read_strategies.table_reads`): a read step 11
refused that goes on to step 12, among tables' requests, every one of which step 11 refuses, dying where the
field is stated without origin (`step_11_refusal_goes_on_to_step_12`, of the core); and the model's
`table_returned_whole`, among tables' statistics, whose reads give a value and the table it is read from,
dying where the table holds a member the reader does not know. So a change that stopped drawing either region
fails these searches, as one that stopped drawing an edge on the readable range's end fails HP20's planned
search above. The monotonicity property holds its worlds stated without origin, whose read in the range is
`unknown`, by their chance (0.2: 0.2335 the least share over 40 runs at `ci`), with an audit control; it and
HP21's relation hold each way outside to a read outside the range of the table without its `source_range`.

<!-- kill points of every search of test_table_read_mutants.py::test_the_table_read_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `edge_read_from_the_interval_above` | at an edge inside the readable range, the value of the interval above, and no refusal | HP20 | `at_an_edge_inside` | 1, 1 |
| `below_an_edge_from_the_degenerate_interval` | just below an edge, the edge's own two entries read as the interval, which divides by zero | HP20 | `just_below_an_edge`, `just_above_an_edge` | 7, 7 |
| `at_edge_dropped_beside_outside_range` | at an edge outside the readable range, `outside_range` alone | HP20 | `at_an_edge_outside` | 2, 2 |
| `range_checked_before_the_edge` | the range checked before the edge, so an edge outside it is `outside_range` alone and reported coverable | HP20 | `at_an_edge_outside`, `across_an_edge` | 2, 2 |
| `an_edge_on_the_lower_end_not_across` | below the readable range, an edge on its lower end read as none between, so a read beyond it is reported coverable | HP20 (planned: across an edge) | `across_an_edge` | 3, 5 |
| `an_edge_on_the_upper_end_not_across` | above the readable range, an edge on its upper end read as none between, so a read beyond it is reported coverable | HP20 (planned: across an edge) | `across_an_edge` | 19, 9 |
| `ends_by_strict_inequality` | `<` for `<=` at the readable range's ends | HP21 | `at_an_end` | 2, 2 |
| `source_range_ignored` | the readable range `x`'s, whatever `source_range` holds | HP21 | the three ways outside | 6, 7 |
| `source_range_widening` | a `source_range` widening the readable range | HP21 | the three ways outside | 6, 7 |
| `the_tolerance_widens_the_range` | the readable range widened by the request's tolerance on the axis | HP21, the relation | `one_double_outside`, `far_outside` | 11, 5 |
| `outside_at_step_10` | the axis entry's `not_met` given `condition_outside` at step 10, which ends the read before step 11 | HP21 | the three ways outside | 6, 7 |
| `points_ignored` | a table holding `points` read as one without | HP22 | `holding_points` | 4, 4 |
| `the_nearest_knots_block` | `points` read: the block of the knot nearest the read in place of the table's | HP22 | `holding_points` | 4, 4 |
| `a_member_dropped_from_the_tables_block` | a table's statistics block returned without its first member, so not as stored at a read | HP22 | `at_a_knot`, `between_knots` | 1, 1 |
| `range_mismatch_without_its_axis` | a read over a range of the axis gives `want_mismatch` without the axis | HP23 | the four ranges | 2, 2 |
| `outside_range_beside_a_range_across_an_end` | `outside_range` beside `want_mismatch` for a range that leaves the readable range | HP23 | `range_across_an_end`, `range_outside` | 18, 5 |
| `monotone_the_tolerance_widens_the_range` | the tolerance's widening, searched by the monotonicity property | monotonicity | `one_double_outside`, `far_outside` | 4, 4 |
| `monotone_source_range_widening` | a `source_range`'s widening, searched by the monotonicity property | monotonicity (planned: one double outside) | `one_double_outside` | 55, 53 |

### An extrapolation's mutants (S3c)

`test_extrapolation_mutants.py`, each injected at a name the read looks up when it runs (`read.form_range`, step
11; `read.read_value_field`, steps 8 to 13; `read._extrapolation` and `read._acceptances`, step 0;
`read.Extrapolation.located_at`; `evaluate.beyond_an_edge`), and each dying at a way it names and at the
assertion it names: the S3 design's mutants of HP24 to HP26 and of its monotonicity property over an
extrapolation (sections 6.7 and 6.8; `test_extrapolation_mutant_table.py` holds each to the row that stands for
it), beside a few more the read's code invites: the end value read at the far end; an edge read on under an
extrapolation; an extrapolation applied inside the range, or across an edge; the field it names ignored; a law
of any type; the method unchecked; a slip ignored and an unknown member refused. And six that hold a draw of
`extrapolation_strategies.py` each, showing where that draw alone puts them, so that a change that stopped
drawing it fails here: the extrapolation's `reason` (`reason_in_the_assumption`), its method `consumer_law`
(`the_method_read_as_constant`), a law outside ASCII (`a_law_outside_ascii_refused`), a read at an end of the
readable range (`an_end_read_as_outside`), the extrapolation that applies drawn second
(`applied_at_the_first_index`), and a refused shape with no location (`shape_unchecked_off_a_record`); the
ways are held by their floors, and `basis` and the method `constant` by the design's own mutants. And 24 more,
each showing at one kind of value a draw within a way takes, so that a draw cut to one value leaves one of them
alive: the field's `label`, which HP24 draws where the value is stated without origin
(`labels_dropped_under_an_extrapolation`); the `want` under which one does not apply, `bounds` alone, and
`components` and `evidence`; and each kind of value of the lists HP26 draws from, its methods that are no
token (a capital, the fuzz control's own fault of a method compared ignoring case; a space added; a space for
the underscore; another word; the empty string; no string), its laws that are no text (each of JSON's five
other kinds, a number among them, the S3 design's control fault for fuzz target 5), its laws of white space
(ASCII's spaces, its tab and newline, white space outside ASCII), and a slip's name (the kind or the field, a
location, `basis` or `reason`, the kind's own) and the place of its character (before the name, inside it,
after it). Each is searched where its way alone is drawn (planned), but the label's. The design's "the end value
taken at `x[0]` where `source_range` narrows the range" shows at every way HP24 draws, since each draws tables
of every kind of `source_range`; its way of its own, outside a narrower `source_range`, is held by its floor.
S3b-2's two mutants of step 11's report on an edge on the readable range's end, which HP20 searches in the
report alone, are searched here in a result too: under an extrapolation a read beyond such an edge is given the
end value, which HP24 sees where it does not apply, across an edge alone (planned: the way that draws an edge
on the range's end in half its draws).

<!-- kill points of every search of test_extrapolation_mutants.py::test_the_extrapolation_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `status_met_under_an_extrapolation` | a read an extrapolation covers given `met`, its reasons dropped | HP24 | each way | 1, 1 |
| `status_unknown_under_an_extrapolation` | a read an extrapolation covers given `unknown`, `outside_range` replaced by an `unknown` code | HP24 | each way | 1, 1 |
| `extrapolated_linearly` | the value extrapolated by the slope of the interval at the range's nearest end, not the end value | HP24 | each way | 3, 3 |
| `the_far_ends_value` | the value at the readable range's far end | HP24 | each way | 3, 3 |
| `end_value_at_x_where_source_range_narrows` | the end value `y[0]` or `y[-1]` where `source_range` narrows the range | HP24 | each way | 3, 9 |
| `labels_dropped_under_an_extrapolation` | a read an extrapolation covers given its value and step 12's reasons, but not its labels | HP24 | `stated_without_origin` | 24, 19 |
| `steps_12_and_13_skipped` | a read an extrapolation covers given its value, but not step 12's reason | HP24 | `stated_without_origin` | 10, 6 |
| `basis_in_the_assumption` | the extrapolation's `basis` in `assumption` | HP24 | each way | 5, 9 |
| `reason_in_the_assumption` | the extrapolation's `reason` in `assumption`, where it holds one | HP24 | each way | 7, 3 |
| `the_method_read_as_constant` | `assumption` naming the method `constant`, whatever the request gives | HP24 | each way | 5, 9 |
| `a_law_outside_ascii_refused` | a `law` holding a character outside ASCII refused | HP24 | each way | 3, 3 |
| `applied_under_want_bounds` | an extrapolation applied under any `want` | HP24 where it does not apply | `under_another_want` | 8, 4 |
| `applied_at_an_edge_outside_the_readable_range` | at an edge outside the readable range, the extrapolation applied, the end value given | HP24 where it does not apply | `at_an_edge_outside` | 10, 24 |
| `an_edge_read_under_an_extrapolation` | at an edge inside the readable range, under an extrapolation, the value below the edge | HP24 where it does not apply | `at_an_edge_inside` | 2, 2 |
| `applied_across_an_edge` | beyond an edge outside the readable range or on its end, the extrapolation applied | HP24 where it does not apply | `across_an_edge` | 39, 8 |
| `an_end_read_as_outside` | a read at an end of the readable range read as outside it, so that an extrapolation covers it | HP24 where it does not apply | `inside_the_range` | 46, 56 |
| `applied_inside_the_range` | an extrapolation at the read applied to a read inside the range: `assumption` and `applied` | HP24 where it does not apply | `inside_the_range` | 1, 1 |
| `an_edge_on_the_lower_end_read_as_none_between` | below the readable range, an edge on its lower end read as none between, so a read beyond it is given the end value | HP24 (planned: across an edge) | `across_an_edge` | 3, 5 |
| `an_edge_on_the_upper_end_read_as_none_between` | above the readable range, the same of an edge on its upper end | HP24 (planned: across an edge) | `across_an_edge` | 11, 9 |
| `applied_under_want_bounds_alone` | an extrapolation applied under `want: bounds` alone | HP24 where it does not apply (planned: under another `want`) | `under_another_want` | 1, 1 |
| `applied_under_every_want_but_bounds` | an extrapolation applied under `want: components` and `want: evidence` | HP24 where it does not apply (planned: under another `want`) | `under_another_want` | 3, 3 |
| `the_location_ignored` | an extrapolation applied wherever it is located, or with no location | HP25 | `another_record`, `a_region`, `an_interval`, `no_location` | 2, 2 |
| `the_field_ignored` | an extrapolation at the read's record applied whatever field it names | HP25 | `another_field` | 1, 1 |
| `two_read_the_first_applied` | two extrapolations naming one field read, the first applied | HP25, two | the three ways of one field | 1, 1 |
| `two_read_the_second_applied` | two extrapolations naming one field read, the second applied | HP25, two | the three ways of one field | 1, 1 |
| `applied_at_the_first_index` | `applied` holding the first acceptance's index, whichever covered the read | HP25, two | `each_its_own_field` | 10, 3 |
| `law_optional_under_constant` | `law` optional under `method: constant` | HP26, refused | `law_missing` | 16, 27 |
| `an_empty_law_accepted` | an empty `law` accepted | HP26, refused | `law_empty` | 6, 5 |
| `a_law_of_any_type` | a `law` that is no string accepted | HP26, refused | `law_not_text` | 10, 7 |
| `the_method_unchecked` | `method` missing or not one of its tokens accepted | HP26, refused | `method_missing`, `method_unknown` | 1, 1 |
| `shape_unchecked_off_a_record` | an extrapolation with no record, or at a region or an interval, taken whatever its method and law | HP26, refused | each way | 5, 10 |
| `a_method_compared_ignoring_case` | a `method` compared ignoring case, kept as written (`Constant`): the fuzz control's fault | HP26, refused (planned: a method no token) | `method_unknown` | 1, 1 |
| `a_method_read_stripped` | a `method` read stripped of white space (`constant `) | HP26, refused (planned: a method no token) | `method_unknown` | 22, 11 |
| `a_space_in_a_method_read_as_an_underscore` | a space in a `method` read as an underscore (`consumer law`) | HP26, refused (planned: a method no token) | `method_unknown` | 3, 18 |
| `a_method_checked_by_its_pattern` | a `method` checked against a token's pattern, lower-case letters and underscores, not the tokens (`linear`, `clamp`) | HP26, refused (planned: a method no token) | `method_unknown` | 5, 43 |
| `an_empty_method_taken` | an empty `method` taken | HP26, refused (planned: a method no token) | `method_unknown` | 73, 7 |
| `a_method_of_another_type_taken` | a `method` that is no string taken (a number, `null`) | HP26, refused (planned: a method no token) | `method_unknown` | 16, 3 |
| `a_number_taken_as_a_law` | a `law` that is a number taken: the S3 design's control fault for fuzz target 5 | HP26, refused (planned: a law no text) | `law_not_text` | 9, 12 |
| `a_null_law_taken` | a `law` of `null` taken | HP26, refused (planned: a law no text) | `law_not_text` | 1, 1 |
| `a_boolean_law_taken` | a `law` that is a boolean taken | HP26, refused (planned: a law no text) | `law_not_text` | 3, 34 |
| `a_list_taken_as_a_law` | a `law` that is a list taken | HP26, refused (planned: a law no text) | `law_not_text` | 16, 5 |
| `an_object_taken_as_a_law` | a `law` that is an object taken | HP26, refused (planned: a law no text) | `law_not_text` | 7, 3 |
| `a_law_of_white_space_refused` | a `law` of white space refused, read stripped | HP26, read | `law_white_space` | 1, 1 |
| `basis_checked` | a `basis` that is no string refused | HP26, read | `law_white_space`, `basis_and_reason_any`, `an_unknown_member` | 2, 2 |
| `a_slip_ignored` | a member one slip from a named one ignored | HP26, read | `a_slip_of_a_member` | 17, 19 |
| `an_unknown_member_refused` | a member no document names refused | HP26, read | `an_unknown_member` | 6, 25 |
| `a_law_of_spaces_refused` | a `law` stripped of spaces alone, and refused where nothing is left (one space, three) | HP26, read (planned: a law of white space) | `law_white_space` | 1, 1 |
| `a_law_of_tabs_or_newlines_refused` | a `law` of white space holding a tab or a newline refused | HP26, read (planned: a law of white space) | `law_white_space` | 3, 42 |
| `a_law_of_white_space_outside_ascii_refused` | a `law` of white space outside ASCII refused (a no-break space, an ideographic space) | HP26, read (planned: a law of white space) | `law_white_space` | 11, 7 |
| `a_slip_of_the_kind_or_field_ignored` | a member one slip from `acceptance` or `field` ignored | HP26, read (planned: a slip) | `a_slip_of_a_member` | 1, 1 |
| `a_slip_of_a_location_ignored` | a member one slip from `record`, `region` or `interval` ignored | HP26, read (planned: a slip) | `a_slip_of_a_member` | 3, 9 |
| `a_slip_of_basis_or_reason_ignored` | a member one slip from `basis` or `reason`, which a read ignores, ignored too | HP26, read (planned: a slip) | `a_slip_of_a_member` | 7, 7 |
| `a_slip_of_method_or_law_ignored` | a member one slip from `method` or `law` ignored | HP26, read (planned: a slip) | `a_slip_of_a_member` | 5, 3 |
| `a_character_before_a_name_not_read_as_a_slip` | a named member with a character put before it ignored | HP26, read (planned: a slip) | `a_slip_of_a_member` | 1, 1 |
| `a_character_inside_a_name_not_read_as_a_slip` | a named member with a character put inside it ignored | HP26, read (planned: a slip) | `a_slip_of_a_member` | 3, 5 |
| `a_character_after_a_name_not_read_as_a_slip` | a named member with a character put after it ignored | HP26, read (planned: a slip) | `a_slip_of_a_member` | 5, 3 |
| `monotone_status_met` | under an extrapolation that covers the read, `met` | monotonicity | `one_double_outside`, `far_outside` | 4, 4 |

### Step 7 over a table alternative's reasons at step 11 (S4d)

`test_table_alternatives_mutants.py`, each injected at a function of step 7 in `core/read.py` (`_standing`,
`_standing_at_step_11`, `_set_aside_by_its_range`, `_gives`, `_entry`, `_found_reading`,
`_reported_beside_two_or_more`) or around `_read_alternatives`, and each dying at the table's way and at the
assertion it names: the S4 design's mutants of HP39 and HP40 (`test_table_alternatives_mutant_table.py` holds
each to the row that stands for it), beside five more the code invites: a kept table and an over-range table
each refusing the field, a table set aside at step 10 refusing the field for its missing operating value as if
it reached step 11, and a kept or over-range table's entry given the labels of the first stored alternative,
or of the last, as a loop's variable left over would hold, which hold the table's stored index: a table stored
first shows the one nowhere, and a table stored last the other. Of the design's, "kept under
`want: bounds`" is a step 7 that keeps a table where the request carries an extrapolation its place could
take, under any `want`, since step 7 reads the extrapolation that applies (`FormRange.extrapolation`), which no
`want` but `value` gives; "the extrapolation applied under `no_pick`" shows in what the read applied alone,
outside the result's JSON, which HP39 holds (`check_applied`); and HP40's three die at a table read inside its
range and moved off it. Every one is searched over its property's own draws: none needs a planned search.
HP12's part over tables among alternatives searches each but the one of `applied` too, at the way where it
shows (HP12's tables below).

<!-- kill points of every search of test_table_alternatives_mutants.py::test_the_table_alternatives_mutant_is_killed (scripts/gen_kill_counts.py) -->
| Mutant | Fault | Killed by | Dies at | Examples |
|---|---|---|---|---|
| `an_edge_sets_aside` | a table alternative read at an edge set aside | HP39, refuses | `at_an_edge_inside`, `at_an_edge_outside` | 10, 4 |
| `an_edge_outside_the_range_sets_aside` | `outside_range` set aside beside `at_edge` | HP39, refuses | `at_an_edge_outside` | 26, 38 |
| `set_aside_under_a_covering_extrapolation` | `outside_range` set aside where an extrapolation the request carries covers it | HP39, kept or set aside | `kept` | 99, 5 |
| `kept_without_an_extrapolation` | `outside_range` kept with no extrapolation that covers it | HP39, kept or set aside | `outside`, `kept_under_bounds` | 2, 2 |
| `kept_under_any_want` | a table kept where the request carries an extrapolation its place could take, under any `want` | HP39, kept or set aside | `kept_under_bounds` | 5, 10 |
| `kept_refuses` | a table an extrapolation covers refusing the field | HP39, kept or set aside | `kept` | 99, 5 |
| `over_a_range_sets_aside` | a table read over an operating range of its axis set aside | HP39, kept or set aside | `over_an_operating_range` | 6, 9 |
| `over_a_range_refuses` | a table read over an operating range of its axis refusing the field | HP39, kept or set aside | `over_an_operating_range` | 6, 9 |
| `over_a_range_gives` | a table read over an operating range counted as a form `want` can give | HP39, kept or set aside | `over_an_operating_range` | 11, 57 |
| `request_fault_at_step_11_sets_aside` | no operating value for a table's axis, at step 11, setting the table aside | HP39, refuses | `no_operating_value` | 11, 6 |
| `request_fault_at_step_11_tagged` | step 11's `request_incomplete` given the table's index | HP39, refuses | `no_operating_value` | 4, 6 |
| `set_aside_at_step_10_reaches_step_11` | a table set aside at step 10 refusing the field for its missing operating value | HP39, refuses | `no_operating_value_set_aside` | 19, 7 |
| `kept_entry_its_read` | a kept table's `no_pick` entry its read under the extrapolation: the end value | HP39, kept or set aside | `kept` | 99, 5 |
| `extrapolation_applied_under_no_pick` | a kept table's extrapolation among what a `no_pick` read applied | HP39, kept or set aside | `kept` | 99, 5 |
| `over_a_range_entry_without_step_12_labels` | an over-range table's `no_pick` entry with its read's labels, none | HP39, kept or set aside | `over_an_operating_range` | 6, 9 |
| `entry_labels_of_the_first_alternative` | a kept or over-range table's entry with the first stored alternative's labels | HP39, kept or set aside | `over_an_operating_range`, `kept` | 7, 5 |
| `entry_labels_of_the_last_alternative` | a kept or over-range table's entry with the last stored alternative's labels | HP39, kept or set aside | `over_an_operating_range`, `kept` | 6, 5 |
| `kept_unknown_dropped_beside_two_or_more` | a kept table's `unknown` reasons dropped beside `no_pick` or `want_mismatch` | HP39, kept or set aside | `kept` | 99, 5 |
| `outside_range_refuses` | `outside_range` refusing the field, as every other `not_met` does | HP40 | `inside` | 6, 8 |
| `narrowed_alternative_kept` | the table moved off its range kept | HP40 | `inside` | 2, 2 |
| `set_aside_by_its_range_beside_the_one_left` | the reasons of a table set aside by its range reported beside the one left | HP40 | `inside` | 64, 8 |

Two of them are also broken implementations that S4d's case files alone catch, `an_edge_sets_aside` and
`over_a_range_gives` (`tests/conformance/test_runner_can_fail.py`), and the reference model's step 7 has twelve
seeded faults of its step-11 rows, each killed by a case file (`tests/reference/README.md`).

## Audits

`conftest.py` runs every test here under the two audits of `audits.py`:

- **draw rejection**: a test that throws away more than 40% of its draws (by `assume` or `.filter`) fails,
  and so does a Hypothesis test whose draws the audit could not see;
- **features**: a property declares, with `@pytest.mark.features(name=least_share, ...)`, the least share of
  its examples that must show each feature the specification distinguishes, and records each example's
  features with `support.feature`. A share below its least fails, and so does a feature recorded but not
  declared. Each least share is about a third of the share measured at both sizes. At `ci` and `deep` a share
  is judged only where the run's examples make at least 20 expected at the least share: `ci` judges the shares
  of 1% or more, and `deep` every share declared (the least is 0.2%); `dev` holds a declared feature to a
  floor instead (below). A property that draws one of several features alike as its first choice, as a
  refusal property draws its fault, names them with `@pytest.mark.drawn(name, ...)` instead. At `ci` each is
  held to its draw floor: Hypothesis keeps an example's first choice through up to 8 examples (the example
  and the mutations it makes of it), so the floor counts 2,000 examples as 250 draws, each shown in 5
  examples (5.7 to 7.0 measured, by fault), and is the count a fault falls below with a probability of at
  most 1e-6. A floor below 10 cannot be judged, and fails: those features must be drawn among fewer. `deep`
  holds each to a third of its share, and `dev` to its draw floor where that is at least 10, judging no other
  (below). A property that knows the chance that one draw shows each feature declares it with
  `@pytest.mark.chances(name=chance, ...)`, as the writer schema's acceptance properties do with their shares
  measured at `ci`: at `ci` each is held to the draw floor of its chance, a floor below 10 failing (draw it
  more often, its family in parts); at `dev` to that floor where it
  is at least 10, judging no other; and at `deep` to a third of its chance. Hypothesis's clusters make a least
  share less safe than independent examples would: at the gate of 20 expected, a feature shown by whole
  clusters falls below its least share in about one run in a hundred (`audits.JUDGED_FROM`). So the json and
  records shards' properties declare by its chance each feature whose least share failed a run with a
  probability above 1e-6 at `ci` or 1e-3 at `dev` (the bound `dev` was held to then), computed from the
  clusters measured on each property (2026-10-15); RFC 8785's values and HP3's parts draw their features often
  enough to have a floor. HP5's `field`, `in_an_own_member` and `in_a_report`, which S2b-1's places in lists
  and own members and S2b-2's evidence made rarer, have no floor at their chances, so they keep least shares:
  0.02, 0.01 and 0.01, the last two the lowest `ci` judges, from 22 runs at `ci`, where they fail a run with
  1.4e-9, 5.0e-7 and 5.8e-13 by the module's cluster model at the variance measured (S2b-2's review,
  2026-10-18). Steps 9 and 10's properties draw each kind first among at most ten (a floor of 30 at `ci`), and
  declare it drawn;
  their HP3's two faults are declared by their chance, one in four, and HP7's end of the span and a bound's
  window by the least share measured. The result's properties draw their kind first among at most eleven;
  HP1, HP2 and HP11 declare each kind by a chance of 0.07, below one in eleven, since at its floor of 25 a
  kind's count, measured over 22 runs at `ci`, fell short with up to 2.8e-6 (at 0.07's floor of 10, 1.9e-7 at
  most: S2b-2's review, 2026-10-18); and HP6 declares its field's `-0`, its review's way, its statistics
  status object and its unknown member by their chances, and its second property a nominal's ways by theirs,
  `behind_another` at its least share measured. HP3's fourth part, evidence's, declares its regions by their
  chances, each at four fifths of its nominal chance, which four runs at `ci` measured above (2026-10-18);
  HP12 declares the read field's form by its chance measured over 22 runs at `ci`, since a tenth of its
  examples show none. Seven regions where a planned search's mutant shows are declared by their chances
  on the properties the searches stand in for, each with a control (Mutants, "The regions held to a floor");
  HP12's first two parts draw their region inside a kind, so that their kinds stay drawn alike. Four more,
  in the same two parts, are too thin for a floor at `ci`, where 2,000 examples give a floor of 10 only at a
  chance of about 0.065: each is declared with `@pytest.mark.deep_chances(name=chance, ...)`, held to the draw
  floor of its chance at `deep` alone, where 20,000 examples give one from about 0.007, a floor below 10
  failing, and judged at no other profile, where it counts as declared; each has a control at `deep`'s
  examples and rule.
  HP12's parts draw their kinds, steps or planted rules first (at most twelve), HP4 its
  ways and
  HP10 its kinds, each declared drawn, and HP4 the read field's form by its chance; each monotonicity relation declares the least share of its examples on
  which it held (applied, a verdict on both sides, not vacuous: a third of the share measured at both sizes),
  and those that draw a way first declare their ways drawn; S4a's HP27 to HP29 draw step 7's outcome first,
  each declared drawn; the monotonicity property over a table (S3b-2) draws its way first, declared drawn, and
  declares its worlds stated without origin by their chance. The table evaluator's properties declare every
  feature by its chance: the least share it showed in eight runs of 2,000 examples (seeds 1 to 4, at both sizes,
  2026-10-17, measured again after the S3b-1 review's strategy changes), rounded down. For each such
  property, five of steps 9 and 10's, two of the result's (HP1 by a kind, HP6 by a chance) and two of HP4's
  (a form by its chance, in each of its two properties), S2b-2's five (HP3's fourth part by a region,
  HP12, HP6 and HP4 by evidence's form, HP6's second property by a nominal's way and by `behind_another`),
  S4a's HP27 by `no_pick`, and S3b-2's monotonicity property over a table by its worlds stated without
  origin,
  `tests/unit/test_audit_controls.py` runs it at `ci`'s examples with a generator that stops producing one of
  those features: its audit fails, on that feature alone; each of the table evaluator's has a control, on a choice no other
  feature it declares depends on. Such a chance is a lower estimate of a share, held only to its floor, which
  lies far below it. One of the five runs a parametrised property, HP8's
  other units, on one parameter, its `plus_minus` place, held to the features that parameter's marks declare,
  as the audit holds each parameter to its own;
- **each profile's rule** (`audits.RULES`): `ci` holds the drawn features and those declared by their chances
  to their draw floors, and a declared feature to its least share; `deep` holds each feature to its least
  share, a third of its share or chance where it is drawn or declared by its chance, and each declared by
  `deep_chances` to its draw floor, which no other profile judges; and `dev` holds every
  feature to its draw floor where that is at least 10, judging no other (2026-10-18). There a declared feature
  counts as drawn with three times its least share, and is never held above its least share. So, at the chance
  its floor assumes, no feature `dev` judges fails a correct run with a probability above 1e-6 by the floors'
  model, as no floor at `ci` does; a feature whose measured share falls below the chance its floor assumes
  fails a correct run more often, and is fixed where it is declared (a lower least share or chance), not in
  the rule. With 200 examples the model counts 25 draws, and a floor reaches 10 only at
  a chance of one half or more: `dev` judges the features drawn among two, those declared by a chance of one
  half or more, and declared features of a least share of about 0.17 or more (35 features of the properties on
  main, 2026-10-18). The features it leaves are judged at `ci` and `deep`. Until 2026-10-18 `dev` held a
  declared feature to its least share where 20 were expected, and features drawn among three or fewer to a
  third of their share, with a bound of about 1e-3 a feature set before CI's per-commit job (#30) ran every
  property at `dev` once for each commit: three of about 75 `dev` jobs of pull requests #35 and #37 failed so
  by chance that day, each a feature drawn among three. `tests/unit/test_audits.py` holds those three runs'
  counts, pins what `ci` and `deep` judge of the features declared, drawn or declared by their chances (in
  runs of any size, with `interesting` and `invalid` draws), holds those declared by `deep_chances` to be
  judged at `deep` alone, and fails if a feature judged by a floor, at any profile and any declaration on a
  grid, fails a correct run with a probability above 1e-6 by the model.

An audit judges random draws, so a sound property fails it now and then by chance. By the floors' model, each
feature judged at `dev` fails a correct run with a probability of at most 1e-6, and a run of every property on
main at most about 1.3e-5 in all (3.2e-5 with the properties of pull requests #35 and #37). The model takes
the fewest draws a run can hold, and overstates: it gave the least shares `dev` judged until 2026-10-18 about
one failure a run of every property with #35's and #37's (0.36 on main), where CI's `dev` jobs failed about
one run in 25. Over seeds 1 to 100, run locally at `dev` on #37's head (every audited property then written),
the audited properties failed 2 runs of 100 by the rule `dev` had (features drawn among three, in 5.5% and
9.5% of the examples, against 11%), and none of the 8,900 audits failed by its rule now (2026-10-18). The
bound rests on the chance each floor assumes. Over those runs each declared feature of main that `dev` judges
showed 0.94 to 1.26 times the share its floor assumes, three times its least share; of the features declared
by their chances, measured at `ci`, `test_output_matches_rfc8785`'s `non_ascii_character` showed 0.57 at `dev`
against 0.66, which puts its floor's false failure at about 3e-5 by the model, as before 2026-10-18. At `ci`
each floor holds a feature to 1e-6 as well; the least shares of the properties whose clusters were measured,
the json and records shards' and the writer schema's acceptance properties, fail a run of them with a
probability of about 2e-6 (`audits.py`); the other least shares judged at `ci` have no figure. CI draws at
random since #38 ("Profiles and sizes"), so each of its `dev` runs is a sample of its own: by the model, a
pull request's five `dev` runs, one on each Python of the test matrix, fail by chance with a probability of at
most about 1.5e-4 (until 2026-10-21 the per-commit job ran one more for each earlier commit: 1.6e-3 for the 50
or so of a pull request); the controls job, derandomised, adds nothing (`.github/workflows/README.md`). An audit that
fails a run Hypothesis drew at random names the seed of that run and how to draw it again: the failing job's
own pytest command, at its profile and on its Python, with `-k <test> --hypothesis-seed=<seed>`, or with
`@seed(<seed>)` on the test. A run that collects less draws other examples under the same seed, since
Hypothesis also draws constants from the modules outside `tests/` that are loaded: on the whole suite, a
property's run replayed exactly under the job's command with `-k`, on one worker or four, and drew 25 of its
200 examples otherwise from its file alone (2026-10-17; `tests/unit/test_audit_replay.py` holds the message to
this). To tell chance from a fault, dispatch `repeat.yml` on the failing test at its profile (`tests/README.md`,
"Repeat runs on CI"): after a chance failure nearly every run passes, while a change that lowers a share fails
most runs. It cannot measure rates this small, since 200 runs without a failure bound the rate at 1.5%; it
tells a rare failure from a frequent one.

## Every draw is held

A strategy's draw is held where some test fails once it stops being drawn: a value no test needs can go, and
every test pass. The check below judges the draws a cut takes away (each value or option, a range's ends, a
collection's least and greatest size, the order given); a range's interior and a collection's middle sizes no
cut takes away, so it cannot judge those. The rule was shown by hand until 2026-10-23 (S3c's review found five draws inside its ways
that nothing held; S4d's builder cut 27 by hand, and the first round left two passing).
`scripts/input_coverage.py` shows it by cutting each draw in turn (maintainer, 2026-10-23):

    uv run --frozen python scripts/input_coverage.py run table_alternatives --report REPORT.json --parallel 4 --workers 2

A cut is one change to one site's draws: each value of `sampled_from` and `booleans`, and each option of
`one_of` and `|`, dropped in turn (values named alike, as two objects with no `repr` of their own, are told
apart by their places in the call); each bounded end of `integers` and `floats` pinned, and kept off; a list,
set or dictionary held to its least size and kept off it, and, where it has one, held to its greatest and
kept off it; a permutation held to the order given. A site is a call of a constructor written under `tests/`,
named by its module, the functions around it and its own text, so that it keeps its name when lines around it
move; a draw a helper makes inside a composite strategy is named after that composite and the call it makes
into the helper (`owner > call > place`), so that two calls of one helper are two sites, and cut there alone.
A composite drawn by another, while that one is itself being drawn, is likewise the caller's (`owner >
draw(...) > place`), so a selection whose patterns name its module takes the draws of the strategies its own
strategies build as they are drawn (maintainer, 2026-10-24); a test runs in no draw, so a strategy drawn in a
test under `find` or `data.draw` is named after the strategy, not the test, and one cut reaches every test that
draws it. The owner is where a strategy's constructor runs, not where the strategy is drawn, so a strategy
built once, as "Adding a property" asks, has no caller to be named after: built at module level it is the
module's (`<module>::...`), shared by every strategy that draws it, and built in a function that is cached it is
named after the first caller that built it in that process (`early > cached() > ...`); a cut of either is held
by a test of any of its callers, and masks the others'. A selection's cut of a draw that several callers share
therefore says only that some caller's test needs it. Attributing a draw to the strategy that draws it, at
the time it is drawn, is for the next piece of this tool, before the whole-repository run (its own review);
`tests/unit/test_input_coverage.py` holds both cases with this result. The plugin
(`input_coverage.py`, loaded only with `-p`) wraps the constructors; loaded with no cut, every draw is the one
drawn without it (`tests/unit/test_input_coverage.py` compares them). Each cut runs the selection's tests as a
pytest process of its own, at `ci`, derandomized and with no example database, until the first test fails:
`held` names that test and its message; `not held` none failed; `invalid` where only invalid draws failed (no
valid example, a health check, the draws' rejection audit); `empty` where it would have left a call nothing to
draw. What it cannot cut is listed by site for a person to read, never counted as held: `text`, `characters`,
`binary`, `randoms`, `builds`, `recursive`, `from_type` and the like, plain `random`, a range's unbounded
side, the optional keys of `fixed_dictionaries`, and a site of more than 24 values across its calls (meant for
a list computed from the draw, whose values differ at every call; the 24 is declared, and no site of the two
selections below that is cut has more than nine). A cut changes every draw after it, not one value alone (a list one value shorter is drawn by other
choices), so its run is a new derandomized sample: a `held` rests on one run, at a test whose message the
report keeps, and a `not held` says that no test needed the value in that run.

On CI the cuts run as `measure.yml`'s cut kind (maintainer, 2026-10-23 and 2026-10-24; `tests/README.md`,
"Measurements on CI"). A dispatch names selections of the baseline, or `all`, each as `NAME:whole` to run the
cuts its `!` patterns leave out too, and the request job splits each selection's cuts into slices of about
equal time by the baseline's `timing`: the cuts the selection makes and its longest cut measured (on two
workers a cut, four cuts at once, run locally), so that a slice's cuts fill at most half of its
job's 120 minutes at two at once, the rest left to the selection's recording and a slower runner. Each job
records the selection and runs its slice (`--slice K/N`); the report merges the slices into the selection's
report, each slice there once and every slice recording the same cuts, and holds it to the baseline, a
disagreement a flag. `measure.py fetch RUN --out DIR` downloads the records, and `input_coverage.py check NAME
--records DIR` holds them to the baseline here. The workflow's self-test holds the cuts of one site of S3c's
to the baseline.

"Drop each value" is finer than the hand rule's "cut the list to one value": two values of one kind, each
held by the kind's mutant, pass a drop each, where a cut to one value fails. The baseline calls such a pair
"equivalent" where no list or comparison in the code tells them apart, and "a gap" where one could: S3c's
slips are held by kind of name, but the read lists the names one by one (`read._EXTRAPOLATION_MEMBERS`), so a
list that lost one would pass. Of the hand rule's other reading, "a draw within a way" (the kept table's
origin, its label, a fallback list), a cut of a draw reaches nothing: those are edits of the strategy's code,
held by hand mutants of it (CONTRIBUTING, "The draws reach what the mutants need").

`input_coverage_baseline.json` names each selection: the tests it runs and the sites they are to hold
(`fnmatch` patterns, the last that matches a site deciding, and one beginning with `!` leaving out what it
matches), then every cut not held (or empty), with its result and a reason that begins "a gap: " or
"equivalent: " and goes on to say why (a result of `error`, `not applied` or `invalid` is no evidence about the
tests and cannot be listed), and every draw it cannot cut, with a person's note. The check fails on a cut not
held, or an uncut draw, that the baseline does not list, and on an entry whose cut is now held or no longer
made: an entry cannot outlive its gap, and nothing turns the check off. What the `!` patterns leave out of what
an earlier pattern took is recorded too, under `left_out`: its sites with a cut, its cuts and its uncut draws,
counted, and why it is left out; `list` and `check` print the counts, and `check` fails when they differ, so
that a new draw of a selection's own through a module it leaves out is not dropped unseen. Each test module
that imports a module whose sites a selection holds is named by the selection (whole or in part) or excused
with a reason under `excused` (`tests/unit/test_input_coverage.py` fails on one that is neither); a test that
draws the sites through another module is not found so. S4d's selection (`table_alternatives`) also runs HP12's part over tables among
alternatives, its searches and the planned searches of `test_model_mutant_table.py`; under the rule these hold
none of S4d's own sites (HP12's strategy draws S4d's composite inside its own, so those draws are HP12's, for an
HP12 selection to judge), and they add only to the time of a cut. Two selections are checked so far, run
locally on 2026-10-23 and 2026-10-24 (on two workers a cut, four cuts at once):

| Selection | Sites | Cuts | Held | Not held: gaps, equivalents | Empty | Uncut | A cut, nothing holding it | A cut held |
|---|---|---|---|---|---|---|---|---|
| `table_alternatives` (S4d) | 29 | 93 | 15 | 72, 6 | 5 | 5 | 284 to 342 s | 103 to 369 s |
| `extrapolation` (S3c) | 64 | 213 | 56 | 127, 30 | 6 | 19 | 77 to 147 s | 16 to 107 s |

Every cut of S4d's ran on 2026-10-24, after the owner rule; of S3c's, the 80 whose sites the rule left with
the same calls keep their results of 2026-10-23, and the other 127 ran on 2026-10-24. Under the rule, S4d's
own sites reach only the draws its own tests make, and the operating range's upper end above the double
above, held before at HP12's `a_range_across_the_readable_end_outside` through HP12's draws, is held by no
test in S4d's own draws, by either cut: S4d's review's finding stands there. S3c's `extrapolations` is one
site a caller: `basis` and `reason` are needed present only where `applied` draws it, the method `constant`
only where `refused_shapes` does, and `consumer_law` only where `applied` does. Both selections gain S3b-2's
table reads drawn inside them (S4d 10 cuts, S3c 99). The earlier pieces' table and value strategies that the
two draw inside them (`tables.py`, `value_field_strategies.py`, `strategies.py`, `records.py`,
`condition_strategies.py`) are left out by `!` patterns and not yet run, for now (maintainer, 2026-10-24): the
next piece of this tool, the whole-repository run on the CI matrix, runs them first and removes the patterns,
and each cut of them not held then gets its reason. The baseline counts them under `left_out`: S4d's
selection leaves out 61 sites, 258 cuts (257 runnable and one `empty`) and 10 uncut draws, S3c's 165 sites,
607 cuts and 70 uncut draws, about ten hours of one eight-core machine (an estimate from these runs' times).
Another piece's draws inside a strategy are not left out: they stay listed, and are judged now or with that
run. Of S4d's 72 gaps, 41 are S4a's ways, counts, tokens and `want` that S4d's composite draws for the
alternatives beside the table and for the table set aside at step 10, which no S4d test needs; 16 are the
interval ways and interval basis tokens that S4a's `changed` and S2's `another_value` draw from the value-field
piece for the alternatives beside the table (each ran, 2026-10-24, on two workers, 310 to 330 s, and none is
held); 10 are S3b-2's axis, field and side of an edge drawn for S4d's table; five are S4d's own (the table
never stored first, never stored last, and no operating range one double wide, nor, in S4d's own draws,
wider). HP12's draws of S4d's composite are an HP12 selection's, which the whole-repository run makes; until
then the operating range's upper end is held by no test in S4d's own draws. Running every property module
waits for CI's measurement matrix.

Two historical runs show the check finding what reviews found by hand, each on a past tree with this branch's
plugin and runner: before S3c's fix round (`a4c1b281`), every cut of the five draws S3c's review found unheld
(the methods that are no token, the laws of white space, the laws that are no text, a slip's name and its
place: 32 cuts) is not held; at S4d's first round (`cad00df0`), the table always stored last is not held, as
S4d's builder found by hand, and so is the operating range's upper end held to the double above, which
S4d's review found. Both are held at the head.

## Adding a property

Write the check as a function of the implementation and the example, and the property as a `test_...` function
that records its features and calls the check. Declare the features with their least shares, or their chances,
measured. Add a mutant that the property must kill, to the mutant file of its group, with its row in its
group's table, and the module to a shard; then record its kill (`uv run python scripts/gen_kill_counts.py
--measure --record`), which writes the row's count, and plan its search if the check names its kill after the
500th example. Never set `max_examples` on a property: the profile decides it. Build strategies so that they draw what
they need rather than filter it, take their size from `strategies.SIZE`, and build each strategy once rather
than in every draw: Hypothesis spends more building and checking a strategy than drawing from it.
