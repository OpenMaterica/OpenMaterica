# Changelog

All notable changes to OpenMaterica will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Additional sections per release: **Schema**, **Data**, **Verification**, **Security** and **Known Anomalies**.
The schema, each model family and each library material carry their own versions; see
`DOCUMENTATION_ARCHITECTURE.md` section 7. Once the material library has its own repository, its changes are
recorded in that repository's CHANGELOG. This file is the core's: `openmaterica-authoring` and
`openmaterica-families` keep changelogs of their own, in their directories, from their first releases, and
every family entry goes in `families/CHANGELOG.md`.

## [Unreleased]

### Added
- The build's own reasons, its verdict and its report (S7a-2b; `declarations.md` sections 2 and 4.2).
  `check_build` gives the report of a declaration that passes its own check. The build's own reasons join the
  read's (section 2 item 8): `no_requirement` for a field read with no requirement; `label_mismatch` where the
  requirement names a label and the label stored on the value the result rests on differs or is absent, and
  none where the result rests on no stored value; `not_reviewed` where the requirement holds `review` and the
  result's provenance holds no completed review, and none where it holds no provenance. A result's status is
  the worst of them all. `core/acceptance.py` judges each result by the build's terms: an acceptance covers a
  reason where it names the result's field, is located at its record (equal in `id`, `version` and
  `content_hash`) and is of the kind a row of section 4.2 listing the reason names, under that row's own
  condition, whatever the reason's `alternative`; `accepted_by` holds every acceptance that covered a reason
  and every one the read applied, `not_accepted` each reason nothing covers, and `unused` lists, per model,
  each of its acceptances none of its results used. `BuildResult` holds the joined reasons, the status and the
  verdict, with `value`, `end_value` under an extrapolation and `initial_value`, which S7a-4's trainable fields
  fill (the S7 design's 4.2); `BuildReport` holds the records a read resolved, the results and the acceptances unused, with
  `refused`, `result()` and `status_lines()`, the lines `materica status` will print, each reason nothing
  covers beside the "Covered by" cells of section 4.2 that list it. `ReadResult` records whether its read
  found the record its target pins at step 1, whether or not steps 2 to 5 then refused it, outside its JSON
  and equality (`resolved`), so that `records` names a record the build looked at and refused. Section 4.2's
  table is generated into
  `schema/0.1/vocabulary/coverage.json`, each "Covered by" cell read by a fixed table of the phrasings it uses,
  a phrasing the generator does not know stopping it; with the table in a file, `not_reviewed` dropped from it
  fails the vocabulary check, where it passed every check before (the S7 design's 9). The report omits
  `watches`, which S7a-4 emits, rather than holding an empty list, and `BuildReport.watches` raises until then;
  it omits `combinations` too, which S7a-3 adds with the combinations it builds, and has no such member until
  then. Where a waiver naming a label fits a reason of a result that label trust could still accept (every
  reason of the result fits some acceptance), the build raises `NotImplementedError`: whether that label is
  trusted is S7a-2's label trust, after 0.1.0.dev4; a result with a reason nothing fits is refused whatever the
  label is, and is reported as if the label were not trusted. The conformance runner compares a build's results and
  unused acceptances and runs S7a-2's 58 build-check files, which pass, also under a build claiming the fits and
  reference data suite (a third build configuration); 1296 of 1638 case files pass, 35 are verified against the
  reference evaluator and 307 are not yet runnable. 34 broken builds each fail an S7a-2 file by the difference
  named beside them, and `tests/spec_sync/test_build_reasons.py` holds each code of the procedure `build` to
  where it is constructed. No case file changes its expected answer.
- The build's reads over records (S7a-2a; `declarations.md` section 2). `check_build` reads a declaration that
  passes its own check: for each model, each record its `checked_over` lists, in the order listed, and each
  field in its `reads`, in that order, one result (`BuildResult`: the model, the record, the field and the
  read), and none for a record not listed; a field with no requirement is read for nothing (section 1 item 1).
  Each read is of the build's own request, item 7: the requirement's `want` and `conditions` alone, every
  declared operating condition, and the acceptances of the kinds a read takes, overlays aside, that name the
  field and are located at the record. The acceptances applied are mapped to their indexes in the model's
  `acceptances` by the build's terms, which define "applied" on the result alone: an acceptance given to the
  read is applied wherever the result shows it (an implied condition, a `conditions` entry with the value it
  supplies; a nominal or an extrapolation, the `assumption`), whether or not the read named it.
  The label and its basis stored on the value a result rests on are read from the record as stored, for the
  build's own reasons; `ReadResult` records which value that is outside its JSON and equality (`resting_on`),
  as it records `applied`. Past the reads, S7a-2b gives the build's own reasons, the judgement, the verdict
  and the report's results (above). Before any read it raises for a pick or an overlay (S7c), a non-empty `target` or `combinations` (S7a-3) and a non-empty
  `trainable` (S7a-4), and no longer for an `overlay_scope` or an accepted difference, which with no overlay
  applied and an empty `target` cover nothing (the S7 design's 1.3). No case file changes its expected answer;
  `BC-009.two_implied_conditions_of_one_value` is added, two implied conditions of one value, one whose token
  the specimen does not state, both applied.
- `materica.check_build(declaration, store, *, claims=...)`, the build check up to the declaration's own check
  (S7a-1b; `declarations.md` section 1). The declaration, JSON text or a value, is read by `record_format.md`
  section 1 item 6 and checked by hand against `SHAPE`, the table of its shape (`core/declarations.py`): every
  fault found, one refusal per fault by the precedence rule, each its case and a JSON pointer (BC-004, BC-005,
  BC-037, BC-040, BC-043, BC-044, BC-048, BC-050, BC-051). A spec-sync test holds `SHAPE` to the
  specification's table, its places, members and Required cells, the JSON type each Holds cell gives, the
  constraints the cells and item 8 state and the clauses' phrases, and to `declaration.json`'s members,
  required lists and tokens; not to the own members' types, the facts' shapes, the type of a member inside a
  `{...}` phrase, a `range`'s entries, two prose clauses on the population level, or the rules on names, which
  the unit examples and the build-check files hold where they hold them at all. A refused declaration gives a `BuildReport` of its refusals
  alone (`core/report.py`); one that passes raises `NotImplementedError`, naming each acceptance and the piece
  that reads it, until S7a-2 builds the reads and the verdict. Claims no implementation makes raise
  `ValueError`; a declaration holding a member that a claimed scene suite, USD read or sampling suite checks
  raises `NotImplementedError` (maintainer, 2026-10-24: the build fails closed there). The conformance runner
  gains the `check_build` executor, the build comparison (refusals as a set, under `rules_compared` where
  named) and the build's two configurations of claims, and runs S7a-1's 56 build-check files, which pass; its
  broken builds, seven the S7 design names and one for each of the three clauses of 2026-10-24 the
  declaration's check can show, each fail one.
- `.github/workflows/claims.yml`, the claims check on every pull request (approved by the maintainer on
  2026-10-24): on each push and each edit of the description, `check_claims.py` holds the description and the
  commit messages to git, and a head, base, commit or count that git does not show fails the job; the figures
  are printed as advice and fail nothing, until measurement runs write the facts that would hold them (the new
  `check_claims.py check --figures-advisory`, which reaches no git fact and no ruled wording; the rulings file is
  private and CI never reads it). A workflow of its own, since `ci.yml` cancels a running pull request's workflow
  on each new event, and one that did so on an `edited` trigger would lose the run whenever the description
  changed. The job also runs the baseline guard of `tests/unit/test_check_claims.py` on the whole history, with
  `CLAIMS_REQUIRE_HISTORY=1`, under which the guard fails where the baseline's commit is missing instead of
  skipping, as it does at the test jobs' depth. `scripts/check_claims.py` is among the gate's paths that run no
  Hypothesis job, with the new workflow.
- `scripts/check_claims.py`, a check of a branch's claims that a builder runs before asking for review
  (approved by the maintainer on 2026-10-23; CONTRIBUTING, "Before asking for review"). It holds a pull
  request's description and the branch's commit messages to git: a commit name names one commit on the branch
  or on `main` (unless its sentence names a pull request), the head and the base they name are the branch's,
  and a count of its commits, files changed or lines added and removed is git's. It holds each figure of the
  description and of the CHANGELOG lines the branch adds to a recorded fact (`record` writes one, with how it
  was measured and at which commit; one measured before the head holds only where the commits since change
  prose Markdown alone: the CHANGELOG, a README, the documentation, but not the specification or a file a test
  reads), unless the figure is marked an estimate or is of a kind that is no measurement. Given the
  maintainer's rulings file, which is private and named when it runs, it holds each specification sentence the
  branch adds that nearly matches a ruling to the ruling's words, and prints both; a wording the rulings file
  accepts for a ruling is printed apart instead. `scripts/claims_baseline.json` holds what the figure check
  finds in this file at its commit on `main`, 680 entries, each a figure by its words with its reason: 488
  measured and stated with no recorded measurement, and 192 that are no measurement; the check refuses an entry
  that is no figure there, and `baseline` writes the file. Prose claims, counts written in words and what a
  figure counts stay with the reviewer.

### Changed
- CI's fuzz control step prints each run's find time (the maintainer's ruling of 2026-10-23), so that CI's runs
  measure the rates the fuzz controls' bar is judged by, which the rates in `ci.yml` and `tests/fuzz/README.md`
  only estimate from local runs. For every control, one line a run, `fuzz-control <name> round=<r> run=<i>
  found=<yes|no> seconds=<s>`, and one line a control, `fuzz-control-summary <name> runs=<n> found=<k>
  seconds=<total> rate=<finds a second>`, printed before any check can end the step. A run's seconds are those
  between its log's creation and its last write, which for a run that found the fault is the time to the find
  (libFuzzer stops a run at its first crash). The step's runs, and its passing and failing, do not change.
  `tests/unit/test_ci_workflows.py` holds the lines' shape and counts for every control, with a control in which
  a step without them, or reading a find otherwise than the checks do, fails.

### Schema
- The vocabulary gains `coverage.json` (S7a-2b), generated by `scripts/gen_vocabulary.py` from `declarations.md`
  section 4.2's table of what covers which reason: per row, its codes, its status, its "Covered by" cell and the
  rule that cell states. No specification sentence changes; the build reads the file (Added, above).
- Six clauses of `declarations.md` (the maintainer's rulings of 2026-10-24 on S7a-1a's open points and on
  S7a-1b's review, as recommended; `docs/specification/changes.md`): `condition_unknown_name` is never
  accepted, its remedy the reader's upgrade, and a waiver whose `code` is `condition_unknown_name` is refused
  at its `code` (section 4.2), which `declaration.json` refuses; `basis` is a member of an extrapolation, a
  nominal and a distribution alone, and `declaration.json` names it on no other kind; a `population_level`
  beside a `represents` that is not `population`, or beside none, is refused by the `population_level` rule
  (BC-043), except where the build claims the sampling suite, where it fails closed, and `declaration.json`
  refuses it; a watch holds `unit` with an `interval` only (section 8 item
  1), and `build_report.json` refuses one beside `accept`; the report of a declaration refused on its own
  holds the declaration as given where its text is JSON, and its `consumer` where the declaration declares one
  (section 2), which `build_report.json` now requires unless the report's one refusal is BC-048 at the empty
  pointer, which it cannot tell from a text that is not JSON; and a model item 7 refuses gives one refusal, at
  its `engine` (section 1, the refusal paragraph). A default of the second review (2026-10-25), which the
  maintainer has yet to confirm, adds a seventh: a rule that judges one member against another stands aside
  where the other is itself at fault, so that one fault is one refusal (the same paragraph): a requirement is
  not judged against an empty `reads`, an acceptance with no known kind is refused at itself and none of its
  other members is judged, and an engine value without its `reason` or `basis` is item 7's fault alone, at the
  `engine`. Five build-check arms: `BC-048.waiver_of_an_unknown_condition_name` (a
  registered condition, refused at the `code`), `BC-048.basis_on_a_waiver`,
  `BC-051.population_level_beside_another_represents`, `BC-051.population_level_without_represents`, and
  `BC-048.want_of_another_json_type` (a member of another JSON type, refused at itself alone). No other case
  file changes.
- Three sentences of `declarations.md` (the maintainer's ruling of 2026-10-23, as recommended after
  S7-cases-2's review; `docs/specification/changes.md`): a code names a condition, for a waiver's `condition`,
  where its reasons always carry one, the six `condition_*` codes, `outside_range`, `at_edge` and
  `range_unstated` (BC-048); a build result keeps the read's members, including `value`, where the read
  returned one, so a `label_mismatch` the build adds to an `unknown` read leaves its value (BC-027); and the
  build's own read request holds the requirement's `want` and `conditions`, and the declared operating
  conditions (BC-009). No case file changes.
- The declaration's and the build report's schemas (S7a-1a), `schema/0.1/declaration.json` and
  `build_report.json`, written by hand. The declaration as the build checks it on its own: closed at every
  place, each place's members, required members and tokens those of `declarations.md` section 1's table of the
  declaration's shape, each kind's own members those of section 4.1's row, its lists of registered names held to
  the vocabulary, and, in its description, what the schema does not state and the build's own check does (a name
  given twice where the members beside it differ, a field or location set against another member, the case and
  pointer of a refusal), with the reason: a schema could state some of it only with one conjunct for each
  registered name, written again for each name the vocabulary adds, where the build's check states each once,
  and none can state two models of one name or two trainable entries for one field at one location, whose
  name and location no registry lists and no JSON Schema compares across the items of an array. An identical
  duplicate in `models`, `requirements` or `trainable` the schema refuses, by `uniqueItems`, which compares
  whole items. The report: its field results the read result's members with the build's, its combination
  results, refusals, watches and unused acceptances; `watches` is optional, so that a build that does not yet
  emit watches omits the member. The typed shapes gain `Declaration`, `BuildReport` and the shapes they
  hold; the declaration's requirement, requirement condition, overlay scope and distribution are
  `DeclaredRequirement`, `DeclaredRequirementCondition`, `DeclaredOverlayScope` and `DeclaredDistribution`, since
  the shorter names are the read request's, an overlay record's and a statistics token's, and no existing shape
  changes. `tests/spec_sync/test_declaration_schema.py` holds the schemas to the text, the vocabulary,
  `case.json` and every build-check case.
- The specification of declarations and the build check over records (S7-spec; the maintainer's rulings of
  2026-10-20 on the build order and of 2026-10-21 on the build check; `docs/specification/changes.md`).
  `declarations.md` gains:
  - the declaration checked on its own: one table of every member at its place, required or optional, with the
    tokens and registered names each takes and the constraints its values hold; a declaration that departs
    from it is refused at build before any read, each refusal its rule's case, a JSON pointer and optionally a
    `detail` no case compares (BC-048); and what a build refuses because it does not claim the scene suite,
    USD read or the sampling suite (BC-051);
  - a requirement's `review: "reviewed"`, and the build's reason `not_reviewed` (unknown), which a waiver
    covers, with the limit that a review lies outside the content hash (BC-049);
  - a waiver naming the `label` it rests on, refused unless the requirement for its field names that label and
    asks for review, and covering only where the label is trusted, stated by the source or on a reviewed value
    (BC-050);
  - the build's results over records; its terms (given, applied, located at, covers, trusted, used); the
    acceptances each read is given; its own reasons joining the read's; `not_accepted`; `unused` (BC-053); and
    its report (BC-010); a field read with no requirement is read for nothing (BC-003);
  - a `trainable` entry's shape, the `trainable` acceptance the build gives its read, and `trainable_by`
    (BC-029);
  - watches of accepted results only, an operating value outside joined in, a `declared` watch for a waived
    unstated numeric condition (BC-052), and a form-range watch cut at a declared edge (BC-031).

  `read_side_contract.md`: a request whose requirement holds `review` is refused (PR-330), and a request takes
  a `trainable` acceptance, two of which for one field are refused (PR-330), under which a read goes on past
  `condition_outside`, `condition_not_accepted` and `outside_range`, carrying the value and
  `initial_value_only`, and ends across or at a declared edge with no value (PR-339); the reason table gains
  `not_reviewed`, regenerated into `vocabulary/reasons.json` and the typed shapes' `ReasonCode`, and added to
  the reference model's table of reasons. The specification README: the case range BC-001 to BC-099; the value
  a result carries where a read goes on under a trainable acceptance; with the architecture draft (12.2, 15),
  the build order, declarations over records before record checks and scenes. **The read of a request
  changes**: a request whose requirement holds `review` is now refused at step 0, `request_incomplete`, as
  one holding `label` is and as section 1 says, since `review` belongs to a declaration's requirement, which a
  build checks (S7a-2) and a read never does; it read as without it, and could give `met` on a value its
  consumer asked to be reviewed. A member one slip from `review` in a requirement (`reviev`) is now refused,
  `request_incomplete`, as section 1 refuses a slip of every member it names there; it was ignored. The
  reference model refuses both, as the text does, where it read both as without them. A request holding a
  `trainable` acceptance now raises `NotImplementedError` (the maintainer's ruling, 2026-10-22), whatever else
  it holds, as one holding a pick or an overlay does, until S7a-4 builds the read under it; it was refused,
  `request_incomplete`, as a kind a read does not take. The model's citations of the edited documents move to
  their new lines, some re-quoted, each saying where the model lags the text, and `plain_read/CASES.md`'s
  PR-330 heading quotes the widened row.

  A label's basis, `label_basis` (`record_format.md` sections 4.1 and 5): an optional member of a value field,
  closed, in a condition's basis shape, in the writer schema, marked `x-materica-write-only`: no read checks
  its shape or returns it. The reader schema and the typed shapes (`LabelBasis`) are regenerated with it. A
  record check flags a label without one, or one that breaks its shape (RC-122). **The reader changes**:
  `label_basis` is named at a field's place, so a member one slip from it (`label_basi`) refuses the field
  (`form_invalid`, PR-030), and so does `label_basis` beside `alternatives` (`record_format.md` section 5),
  where the reader before ignored both. Four case files hold it, written through the case tools: three of
  PR-030 (`label_basi` beside the label refuses the field; `label_basis`, well formed or not, is neither
  checked nor returned in any member a case compares) and one of PR-044, whose row now names `label_basis`
  beside `alternatives`.
- The build-check case (S7-cases-1; the S7 design's section 5, its paragraph ruled to land with the first case
  files on 2026-10-21). The specification README's "Case files" gains it: a build-check case names its declaration
  in `inputs.declaration`, read by `record_format.md` section 1 item 6, asks for `{"operation": "check_build"}`,
  and compares the members of the build's report it names: the declaration's refusals as a set of case id and
  pointer (only those of the rules `compare.rules_compared` lists, where it lists any), the results, the watches
  and the acceptances unused. `case.json` gains the build arm: `inputs.declaration`, the build operation, the
  report's compared members (a build result being a read case's compared members with the build's own),
  `compare.result_members`, and `compare.rules_compared` in a build-check case too, with the branch that holds a
  build-check case to them; any other case asking for `check_build` or naming `result_members` is refused, and so
  is a case naming a declaration that is neither a build-check case nor an engine-adapter case, which the README
  gives one. The typed shapes are regenerated. `tests/spec_sync/name_overlaps.json` allows the four names the
  build's report gives a second meaning (`acceptance`, an unused acceptance's index; `fields`, a combination's
  list; `interval`, a watch's ends; `operation`, the build's own) and `field` beside `fields`, each with the
  sentence that keeps them apart.
- Three sentences of `declarations.md` section 1, ruled with S7-cases-1's review on 2026-10-23
  (`docs/specification/changes.md`). Item 12's precedence holds member by member: where item 7 refuses a model with
  `engine`, its `engine` gives no refusal under item 12 and a domain it is checked over still does, and where item
  8 or the `population_level` rule refuses the declaration over a requirement, that requirement gives none and a
  `sampling` beside it still does; BC-051's Cases row says "for that member". An empty `reason` or `basis` breaks
  its row's Holds and is BC-048's, items 3 and 4 refusing one that is absent. A refusal's pointer names the most
  specific member at fault: for a value that breaks its row's Holds, that member; for what item 12 refuses, the
  member that needs the suite, or the acceptance or `trainable` entry itself.
- Three clarifying sentences, ruled on 2026-10-23 (`docs/specification/changes.md`), each settling a reading the
  build check's case files would otherwise choose; no reader, schema or case file changes. `read_side_contract.md`
  section 2: an `alternative_values` entry whose alternative is kept outside its form's range, or is a table read
  over an operating range of its axis, holds its `unit`, `specimen`, `statistics` and `provenance` as
  `record_format.md` section 5 gives them, even where its read ended at step 11; and an alternative's index, an
  entry's and a reason's `alternative`, counts from 0, in stored order. `declarations.md` section 1: a waiver
  whose `code` is no reason names no condition, so such a waiver without `condition` is refused at its `code`
  alone (BC-048).
- A build-check case that compares results it expects names the members of each result it compares:
  `case.json` requires `compare.result_members` there. Before, such a case without it compared each result's
  `model`, location and `field` alone. A refusal case, which compares results and expects none, names none.

### Verification
- PR-330's arm of a member one slip from a requirement's `review` (`PR-330.near_typo_requirement_review`,
  S7a-2a), written through the case tools: refused at step 0, which S2a-2's step 0 runs, and passes. The S7
  design's notes ask for the slip among the arms of the read's refusal of `review`, which it has made since
  S7-spec; and `tests/spec_sync/unknown_member_positions.json` names `review` at a requirement's place, so the
  positions test plants a slip of it as of `label`. 1238 of 1638 case files pass, 35 are verified against the
  reference evaluator, and 365 are not yet runnable.
- The build's reference model of a declaration checked on its own (S7a-1m; the S7 design's 6.4, "The model"),
  `tests/reference/build_model.py`, written from `declarations.md` section 1 and section 4.1's location rule
  and item 4 by an agent that did not read the build's code, and importing nothing from `materica`: its shape
  table, the refusals of BC-004, BC-005, BC-037, BC-043, BC-044, BC-048, BC-050 and BC-051 by case and pointer,
  each fault carrying the case of the first rule that names it, and no verdict past the declaration or on what a
  claimed suite checks; item 7's BC-040 it places where the declaration decides it, one refusal a model at its
  `engine`, and names without placing where it does not. `tests/reference/test_cases.py` runs every
  build-check file through it under every configuration of build claims its claims allow: it agrees with each
  of S7a-1's 56 files, and hands S7a-2's 58, which pass it, to the results model below. 114 seeded faults, the
  hand mutants of the model's rules, 84 killed (50 by the files, 34 by its direct checks) and 30 listed as
  survivors for HP41 and HP42 to kill; its citations, its layering and its token lists
  against the vocabulary are held as the read model's are, and its shape table and token lists against the
  declaration's JSON Schema. One fault is one member at fault, a pick is located by its `record`, and a claimed
  suite gives no verdict (maintainer, 2026-10-24); `tests/reference/direct.py` holds those and the order of
  the cases, which no file pins. The model follows the maintainer's clauses of 2026-10-24 as S7a-1b's text on
  `main` words them (a waiver of `condition_unknown_name` refused at its `code`, `basis` on three kinds, a
  `population_level` only beside `population`, item 7 at `engine`), and the refusal paragraph's rule that a
  rule judging one member against another stands aside where the other is at fault.
- The build's reference model past the declaration (S7a-2m; the S7 design's 6.5, "The model"),
  `tests/reference/build_results_model.py`, written from `declarations.md` sections 1, 2 and 4.2 and the build's
  terms before S7a-2's code, by an agent that did not read the build's code, and importing nothing from
  `materica`: the request each read is given, the read through the read model, the build's own reasons
  (`no_requirement`, `label_mismatch`, `not_reviewed`), the status law, what a read applied, the judgement by
  section 4.2's table held as the model's own data, `accepted_by`, `not_accepted`, `unused`, the verdict and the
  report; no verdict for a waiver resting on a label where label trust decides it (after 0.1.0.dev4), for a
  target naming a fact, combinations, a `trainable` entry and the watches (S7a-3, S7a-4), and for the rows of
  section 4.2 a pick or an overlay alone reaches (S7c). `build_model.py` hands it a declaration that passes its
  own check. `tests/reference/test_cases.py` compares a build's results as the specification's README says: the
  models agree with every one of the 114 build-check files, S7a-2's 58 included, under every configuration of
  build claims each allows, and none is listed. Its table of section 4.2 is held to the table parsed from the
  text, since `main` has no `coverage.json` yet, and to `coverage.json` once the file exists (a build whose
  acceptance module exists without it fails); 45 direct checks hold what no file pins; 79 seeded faults, 76
  killed (47 by the files, 29 by the direct checks) and 3 listed as survivors; its citations and layering are
  held as the other models' are. Four open points, each listed once: three the model's readings of the text
  (one of them, an implied condition applied by the value an entry shows, where the text's two sentences on an
  implied condition differ), and one that gives no verdict where it cannot decide.
- The measurements a property piece makes before review run on CI as a matrix (maintainer, 2026-10-23), with
  the counts and judgement of a local run: `scripts/measure.py` (floors at the variance measured, at the mean and the least share, kill drift over
  streams, regions of a base against the head with every mutant search's kill, a fuzz control's rate), run alike
  here at a small scale and as the jobs of `.github/workflows/measure.yml`, dispatched by hand; each job keeps a
  record, and a summary counts them before it merges them into one table a kind. A pull request that changes the
  workflow or its script runs its self-test, each kind with the answer it must give. `pre_review.py --stage
  whole` runs every test of the tree but the property modules, which CI runs in its shards.
- S7a-2's build-check case files (S7-cases-2; the S7 design's section 5.4, its S7a-2 rows), written through the
  case tools from the text alone, by a pass shown no implementation: 57 files of a declaration over records that
  passes its own check, each expecting the build's results and the acceptances it leaves unused: BC-001 (3),
  BC-002 (3), BC-003 (2), BC-006 (3), BC-009 (5), BC-010 (4), BC-016 (7), BC-017 (4), BC-019 (4), BC-020 (4),
  BC-027 (3), BC-028 (2), BC-038 (4), BC-049 (6) and BC-053 (3). Of the design's 59, BC-050's six label-trust
  files are ruled to come after 0.1.0.dev4, and one arm of BC-053, an acceptance used by two results, is left out:
  over records an acceptance is located at one record and names one field, so it cannot arise before S7a-3. Six
  arms are added: five where a seeded fault of the build that no other file caught showed one was needed (an
  acceptance located by `id` alone, a waiver skipping a reason that carries an `alternative`, `not_reviewed` on a
  result with no `provenance`, a model's reason covered by another model's acceptance, `unused` not kept per
  model), and BC-049's reviewed value that is `met`. Each
  result is keyed by model, record and field and compares its status, reasons, value, `assumption`, `accepted`,
  `accepted_by` and `not_accepted` (BC-049's also its `provenance`, BC-003's also every member of a read, each
  absent); no file compares watches, which are S7a-4's. The records are fourteen plain-read inputs, byte for byte,
  and two new fixtures, `plasma_fixture.json` and `glycerol_review_reviewed.json`. Every file is S7a-2's and not
  yet runnable. With them, PR-330's arm
  of a requirement holding `review` (`PR-330.review_in_requirement`), refused at step 0, which S2a-2's step 0
  runs, and passes. A build written from the text alone, over a read written from it that agrees with the 165
  plain-read case files over these fixtures that it takes, agrees with every file; each arm's control, its
  declaration with the one thing it tests removed (for five, the records changed), gives that build another
  answer; each of 82 seeded faults of that build fails at least one file. `CASES.md`'s column of a build-check
  case writes its results and unused acceptances, and the runner's case file holds `compare.result_members`. 1181
  of 1631 case files pass, 35 are verified against the reference evaluator, and 415 are not yet runnable.
- S7a-1's build-check case files (S7-cases-1; the S7 design's section 5.4, its S7a-1 rows), written through the
  case tools from the text alone, by a pass shown no implementation: 51 files of a declaration checked on its own
  and refused at build, in a new suite, `build_checks/`, with its `CASES.md` and `README.md`: BC-004 (3), BC-005
  (8), BC-037 (6), BC-048 (22), BC-050 (2) and BC-051 (10), as the design plans. Each supplies the plain-read water
  fixture, byte for byte (one the glycerol fixture too), and one declaration, a base declaration with the arm's
  fault planted, and expects exactly its refusals, each its rule's case and a JSON pointer into the declaration,
  and no results, watches or unused acceptances. Three answers rest on the sentences ruled with them (**Schema**,
  above): an engine model checked over a domain gives the domain's BC-051 beside item 7's refusal, a population
  requirement without `population_level` beside `sampling` gives BC-043 and the `sampling`'s BC-051, and an empty
  `reason` gives BC-048 at the `reason`. Every file is S7a-1's and not yet runnable, since no executor runs
  `check_build` before S7a-1. A build of the declaration's check written from the text alone agrees with every
  file; each arm's control, its declaration with the one thing it tests removed, gives that build another answer,
  but for the one arm whose point is a refusal not given, which a seeded fault of that build catches instead, and
  five more arms also carry a seeded fault each catches; each of 41 seeded faults of that build fails at least one
  file. 1180 of 1573 case files pass, 35 are verified against the reference evaluator, and 358 are not yet
  runnable.
- A label's basis (**Schema**, above) comes with four case files, written through the case tools, which run
  and pass: `PR-030.near_typo_label_basi_beside_label`, `label_basi` beside the label, refused at step 8;
  `PR-030.label_basis_stated_not_returned` and `PR-030.label_basis_guessed_not_checked`, `label_basis` well
  formed and not, each `met`, every member a case compares as without it; and
  `PR-044.alternatives_beside_label_basis`, refused at step 7. A reader, or the reference model, that does not
  name `label_basis` at a field's place fails the first and the last and no other case file; no case file
  caught the model's before. A reader that checks its shape fails the third alone.
  `tests/spec_sync/test_t1.py` lists the slip's input under `slip`. Since a case compares only the members its
  `compare` names, `tests/reference/test_cases.py` also holds the reference model's whole result, over every
  case file of a read it gives a verdict on, to the members of `read_side_contract.md` section 2's table, read
  from the text: a model that returns `label_basis` beside them passes every case file and fails it. A change
  to `read_side_contract.md` now selects that test in `scripts/pre_review.py`.
- PR-339's arm across a declared edge, written through the case tools: `PR-339.across_edge_no_value`, the edge
  table narrowed to [275, 283], read at 272 K under a `trainable` acceptance, ends at step 11 with
  `outside_range` and no value, as `read_side_contract.md` section 2 item 3 now says; `declarations.md`
  section 4.2 covers a trainable field's `outside_range` only on a result that carries one (BC-029). It is
  S7a-4's, and not yet runnable; the map of steps (`tests/spec_sync/test_case_steps.py`) now knows the S7
  pieces, S7a-1 to S7a-5 and S7c. The reference model now gives no verdict on a request holding a `trainable`
  acceptance, as on a pick, where it refused one with `request_incomplete`, and lists the arm so; none of its
  129 seeded faults gives the arm another outcome. The implementation raises `NotImplementedError` on such a
  request (**Schema**, above), so HP12's agreement check, which fuzz target 5 also runs over every acceptance
  of the case files, finds that neither decides, as on a pick. 1180 of 1522 case files pass, and 307 are not
  yet runnable.
- `scripts/input_coverage.py` and its pytest plugin, `tests/property/input_coverage.py` (maintainer,
  2026-10-23): whether the tests hold every draw a strategy makes, which the property README's rule "every draw
  is held" asked and reviews had shown by hand. Each cut of a selection's draws (a value or option
  dropped, a range's end pinned or kept off, a collection held to or kept off its least or greatest size, a
  permutation held to the order given) runs the selection's tests as a pytest process of its own at `ci`,
  derandomized, until the first failure; `tests/property/input_coverage_baseline.json` lists every cut no
  test holds with its reason, and every draw the plugin cannot cut, and the check fails on one it does not
  list and on an entry whose cut is now held. A fixture with one test for each value a cut takes away holds
  each cut at that test. A strategy drawn by another strategy is its caller's draw (maintainer, 2026-10-24); a
  strategy built once, at module level or cached, is shared by its callers or named after the first.
  Two selections, run locally: S4d's table alternatives (93 cuts: 15 held, 72 gaps, 57 of them S4a's draws and
  the value-field draws S4a's and S2's helpers make for the other alternatives and the table set aside, 6
  equivalents, 5 of them empty) and S3c's extrapolation (213 cuts: 56 held, 127 gaps, 30 equivalents, 6 of them
  empty); the earlier pieces' table and value strategies drawn inside the two are left out of their selections
  by `!` patterns, for now and not yet run (S4d's: 61 places, 258 cuts, 10 uncut draws; S3c's: 20 places, 80
  cuts, 9 uncut draws, a floor of what a whole run makes), counted in the baseline, whose check fails when the counts change; the
  whole-repository run on the CI matrix runs them first and removes the patterns. None is fixed here. On the
  trees before S3c's fix round and at S4d's first round it reports not held the draws those rounds' reviews
  and builder found unheld by hand. The plugin loaded with no cut draws what is drawn without it, every
  choice compared (`tests/unit/test_input_coverage.py`, on a tree of every kind of draw it cuts).
- The input coverage's cuts run on CI as a kind of `.github/workflows/measure.yml`, `cuts` (maintainer,
  2026-10-23 and 2026-10-24): a dispatch names selections of the baseline, or `all`, each alone or as
  `NAME:whole`, without its `!` patterns, so that the cuts they leave out run too. The request job splits each
  selection's cuts into slices by the baseline's new `timing` (the cuts the selection makes, those of a whole
  recording where it is run `:whole`, and its longest cut, from the first dispatch on CI), each slice's cuts planned to fill half of its job's 120 minutes at two
  at once; each job records the selection and runs its slice, starting no cut it could not finish before its interrupt and reporting how many cuts its share
  held; the report merges the slices into the selection's report, refusing a slice missing, doubled or
  recording other cuts, naming a selection that held no cut ("0 in scope: nothing checked"), and holds it to
  the baseline, a disagreement a flag. `measure.py fetch RUN --out DIR` downloads
  the records and `input_coverage.py check NAME --records DIR` checks them. `scripts/input_coverage.py` gains
  what the jobs use: `--whole`, `--scope` and `--slice K/N` (a report that is a share of a selection's cuts,
  run and judged alone), `--records`, and a `--budget` counted from the command's start.
  On a pull request that changes a test a selection runs (or `tests/conftest.py` or `tests/property/conftest.py`,
  the Hypothesis profiles), or its entry of the baseline, the workflow runs every cut of that selection, and on
  one that changes a module the selection's tests import, the cuts of the sites whose names hold that module,
  in slices planned from the cuts that scope holds (counted from the selection's recording by the request
  job, none where it holds none), each held to the baseline, a disagreement failing the run's report job; a
  pull request that changes none of these makes no job but the request, and one that changes the workflow, its
  script or the input coverage's runner or plugin runs the self-test, now with the cuts of one site of S3c's
  beside the other kinds, which must be two. What the `!` patterns leave out is now counted by the place a
  draw is written: the owner of a strategy built once in a cached function is the first caller on a worker, so
  the sites it made, and with them the counts, varied with how the tests were split among the recording's
  workers (S3c's 151, 160 and 165 sites at 2, 4 and 8 workers), where the places and what is drawn at them do
  not (a count by the selection's own owner and the place varied too, 120, 128 and 132 sites). The count is a
  floor: another owner or another call of a place already drawn adds nothing, until the draw-time ownership
  restores a count by owner. The pull-request run is advisory (maintainer, 2026-10-25): it
  blocks no merge, until it has run cleanly on a few feature pull requests. `measure.yml` leaves the
  concurrency queue at GitHub's default, since `queue: max` beside a pull request's cancelling run is a
  workflow validation error (a pending dispatch of the same inputs on the same ref is replaced by a newer one).
  The draw-time ownership the maintainer ruled on 2026-10-24 follows as a piece of its own,
  before the whole-repository run.
- The build's reference model of a declaration is changed at the points where it and the declaration check
  read the specification apart (defaults of 2026-10-26, which the maintainer has yet to confirm; the check's side
  follows in its own pull request, which also moves the check's comparison of a `trainable` entry's record, now
  of the record whole, to the model's, by its reference). A rule that judges one member against another stands
  aside only as far as its verdict depends on the member at fault: what the judged member's own type, shape or
  registered names settle, whichever value the member at fault holds, is still judged. An entry that is no
  well-formed name (a reference without string `id`, `version` and `content_hash`, a `field` that is no string)
  is neither the same as nor different from another, and no rule compares it. The
  model now names a record by its reference (`id`, `version`, `content_hash`) in `checked_over.records`, in a
  `trainable` entry's location and in the check for a name given twice, and compares a `trainable` entry's
  record by it, a record that is no reference compared with none; judges `records` beside another alternative of
  `checked_over`; judges a label beside an unregistered field against every registered label; keeps the check of
  a distribution's parameter values beside a token that is none; reads a status object as an object whose only
  members are `status` and `reason`, in an accepted difference's `value` too; does not read a waiver's
  `condition` of another JSON type as also missing; names `region_conditions` and a `trainable` entry's `region`
  or `interval` for item 12 whatever JSON type it holds; refuses a combination only where its registered fields
  are all of one section; and gives an object holding two of the members it takes one of the object's own fault,
  so that a `trainable` entry at a record and a region is item 12's refusal alone at the entry. Three open
  points are retired on those defaults (`member_judged_beside_a_faulty_one`, `combination_sections`,
  `trainable_location_in_a_scene`) and `exactly_one_of` is restated. `tests/reference/direct.py` holds 66 new
  direct checks, 40 of which the model of `main` fails (counted by running them against it); the other 26 pin
  what the model of `main` already held (the cross-kind location rule of a `trainable` entry, the parts of a
  record's name, a name given twice with another between, a record listed twice beside another alternative of
  `checked_over`, a `nominal` holding neither `value` nor `params`) and arms on which the sides already agreed,
  and each fails on a hand mutant of the model that drops what it pins. Two seeded faults the new checks kill are
  no longer listed as survivors (`build_trainable_at_a_region_taken`, `build_trainable_twice_by_field`).

## [0.1.0.dev3] - 2026-10-22

A development pre-release. It holds S3: a field holding a table, read through every step (its checks at steps 8 and
9, its own axis beside the field's conditions at step 10, its form within its readable range and edges at step 11,
its origin and its `want` at steps 12 and 13), and the `extrapolation` acceptance, which under `want: value` gives a
table's end value outside its readable range, at no declared edge and across none; S4d: a table among a field's
alternatives, read with no pick and no overlay; the schema's table and extrapolation shapes and the result's shape
the maintainer ruled; a `CITATION.cff`; and the repository's move to the OpenMaterica organisation. Picks, overlays,
a read whose target is an overlay record, a region target and `want: fit` on a field holding a fit record raise
`NotImplementedError` until later steps. The schema 0.1 files may still change before 0.1.0. The entries below are
everything since 0.1.0.dev2.

### Added
- The read's steps 8 and 9 for a table (S3a; `record_format.md` section 6, table items 1, 2, 4 and 5;
  `read_side_contract.md` section 3, steps 8 and 9). Step 8 checks every member of a table: `axis`, a numeric
  condition the reader knows (another string, a token condition's name included, is `unknown_token`, and the
  axis condition is then not checked), held in the field's `conditions` as `not_applicable`; `axis_unit`, a
  string or a status object; `x`, at least two distinct values, never decreasing; `y`, one number for each;
  `scheme`, `linear` or `loglog` (another string `unknown_token`), a log-log table's numbers positive;
  `edges`, each strictly inside `x`'s range, in `x` exactly twice and consecutively, none listed twice, no
  other value of `x` repeated; `source_range`, two numbers in order sharing with `x`'s range a value that is
  no edge. Numbers are compared by value, so `-0` equals `0`, and `x` is indexed once, so that the edges are
  checked in time linear in the table's length. A table whose `x` is empty is refused (`form_invalid`) beside
  an edge or a `source_range` too, whose rules read `x`'s ends, and the read never raises there. A table
  holding `points`, whatever it holds, gives `points_unsupported`, and `null` there `form_invalid` too;
  `points` counts as a member named at a table's place, so a member one slip from it is refused, in a table
  and in a status object standing for one, while `points` itself beside such a status object is ignored, as a
  member the table's shape does not define (`provenance.md` section 1 item 5). Step 9 compares `axis_unit`
  with the axis condition's registered unit, code point for code point, its `unit_mismatch` carrying the axis.
  A table that steps 8 and 9 pass, alone or as an alternative, first, last or beside any other, still raises
  `NotImplementedError`: steps 10 to 13 are S3b-2's. The 72 case files mapped to S3a run and pass:
  1029 of 1508 case files pass and 35 are verified against the reference evaluator; 444 wait for S3b-2 (67),
  S3c (45), S4's later pieces (135) and the record checks, C2 (197).
- The evidence field's `conditions` hold no registered condition whatever the field's form (`record_format.md`
  section 4.3 item 3; the maintainer's ruling of 2026-10-19): a table on `biocompatibility.evidence` whose
  `conditions` hold its axis gives `form_invalid` beside `form_not_registered`
  (`PR-036.table_on_biocompatibility_evidence_holding_its_axis`, a new arm written through the case tools).
- Three more case arms, written through the case tools (S3a's review): a table whose `x` is empty beside an
  edge and a `source_range`, `form_invalid` where the read raised
  (`PR-322.x_empty_beside_an_edge_and_a_source_range`); a withheld table beside `points`, `withheld`
  (`PR-110.table_withheld_beside_points`); and one beside `point`, one slip from it, `form_invalid`
  (`PR-110.table_withheld_beside_a_slip_of_points`).
- A table's steps 10 to 13 (S3b-2; `record_format.md` section 6, table item 3; `read_side_contract.md` sections
  1, 2, 3 steps 10 to 13, 5 and 6). Step 10 gives the table's own axis an entry beside the field's conditions,
  `met` where the operating value lies in the readable range and on no edge, `not_met` otherwise (no operating
  value and an operating range included), with no reason of its own. Step 11 reads the readable range, `x`'s
  range narrowed by `source_range`, through `core/evaluate.py`: a read exactly at an edge gives `at_edge`
  wherever the edge lies, one outside the range `outside_range`, beside `at_edge` where the edge lies outside it,
  and it makes the request's two checks that need the form, no operating value of the axis (`request_incomplete`,
  a fault of the request) and an operating range of it (`want_mismatch` alone); each reason carries the axis, and
  each ends the read. Under `want: value` a read in the range gives the table's number at the operating value,
  and the result holds the table it is read from, as stored, in its new `table` member (**Schema**, below); under
  another `want` the table is the entry's value as stored and `want_mismatch` stands. Step 11 also reports
  whether an extrapolation could cover its `outside_range` (outside, at no edge and across none), for the
  extrapolations' piece to complete. A table alternative read in its range stays, and one set aside by its
  conditions never reaches step 11; one whose read gives a reason at step 11 raises `NotImplementedError` at step
  7, whose rules for it are S4d's, and the reference model gives no verdict there. The 68 case files mapped to
  S3b-2, and seven new arms written through the case tools (a value read from a table with its table, alone and
  as the one alternative left; no `table` beside `want_mismatch`, outside the range and under `no_pick`; a table
  stated without origin whose read step 11 ends, with `outside_range` alone, since step 12 never runs; and a
  table's unknown member left out of the `table` beside its value), run and pass: 1104 of 1515 case files pass and
  35 are verified against the reference evaluator; 376 wait for S3c (45), S4's later pieces (134) and the record
  checks, C2 (197).
- The `extrapolation` acceptance (S3c; `declarations.md` section 4.1; `read_side_contract.md` sections 1, 2, 3
  and 5). Step 0 checks an extrapolation whatever field or location it names: its `field` as a target's, its
  `method` one of `constant` and `consumer_law`, its `law` a string of at least one character, white space
  alone included, which the reader does not judge, a member one slip from a named one refused, its `reason` and
  `basis` ignored; two naming one field are `request_incomplete`, whatever else each holds. One naming the
  read's field at the read's record applies to it: under `want: value`, a table read outside its readable range,
  at no declared edge and with none between the read and the range's nearest end or on that end, goes on past
  step 11's `outside_range` to steps 12 and 13, its status `not_met` and its reasons kept, step 12's added; the
  result carries the value at the readable range's nearest end, taken from inside the range (at a `source_range`
  end inside an interval, interpolated there), with its unit, specimen, statistics, provenance and the table it is
  read from, and `assumption`, the extrapolation's `method` and `law` as the request gives them; `applied` holds
  its index. Under any other `want`, at or across an edge, inside the range, on a constant, or named for another
  field or location, it is checked and not applied. Step 11's report names the extrapolation that covers its
  `outside_range` beside `coverable`, for S4d's step 7, where a table alternative whose read gives a reason at
  step 11 still raises `NotImplementedError`, one an extrapolation covers included. The reference model applies
  an extrapolation as the read does, written from the text. The 45 case files mapped to S3c, and a new arm of
  the result's `table` under an extrapolation, written through the case tools
  (`PR-307.table_under_an_extrapolation`: the table returned as stored, its `source_range` included, beside the
  end value a `consumer_law` extrapolation starts from), run and pass: 1151 of 1517 case files pass (one more arm,
  of an implied value, under **Verification**) and 35 are verified against the reference evaluator; 331 wait for
  S4's later pieces (134) and the record checks, C2 (197).
- Step 7's rows for a table alternative whose read gives a reason at step 11 (S4d; `read_side_contract.md` section
  3, step 7; `record_format.md` section 5 items 2 to 5), for a field holding alternatives read with no pick and no
  overlay. One read outside its readable range, at no declared edge, is set aside, unless an extrapolation the
  request carries would cover it under `want: value`: then it stays, is read on through steps 12 and 13, and the
  extrapolation is applied only where it is the one left. One read at a declared edge refuses the field, wherever
  the edge lies, `outside_range` beside it or not. One whose read reaches step 11 with no operating value for its
  axis refuses the field, its `request_incomplete` carrying no `alternative`; one set aside at step 10 never reaches
  step 11. One read over an operating range of its axis stays, and counts as a form `want` cannot give. Under
  `no_pick` the entry of a table kept outside its range or read over a range holds its table as stored, with no end
  value, no `assumption` and no extrapolation applied, and the labels step 12 gives it even where its read ended at
  step 11. Step 7 raised `NotImplementedError` there until now. The reference model decides the same rows,
  written from the text by an agent that did not read the read's code. The 25 case files mapped to S4d run and
  pass (PR-013's six, PR-044's fifteen and PR-308's four; the S4 design's 26th,
  `PR-308.table_set_aside_never_reaches_step_11`, has run with S3b-2): 1176 of 1517 case files pass and 35 are
  verified against the reference evaluator; 306 wait for S4's later pieces (109) and the record checks, C2
  (197). No case file changes.
- `CITATION.cff`, so that GitHub's "Cite this repository" gives the software's citation: its title, author with
  ORCID, licence and repository. Its version and release date are added from 0.1.0, with the first archived
  release.

### Changed
- `scripts/pre_review.py` runs the kill counts' unit tests (`tests/unit/test_gen_kill_counts.py`) with its
  fast checks wherever a kill points marker of a README was added or removed, as well as in its tests stage:
  they hold the markers to the recorded groups by name, which the generator's `--check` does not, and a
  group the README gained and they did not name once failed on CI alone.
- CI's per-commit job checks that each earlier commit of a pull request builds, type-checks, generates and
  collects on its own, and no longer runs the whole suite on it, which the head's jobs run (maintainer,
  2026-10-21). Each commit but the head still gets the site job's steps, ruff, mypy and pyright, the wheel and
  its check and every generator's `--check`, and now `freeze_schema.py --check`, `pytest --collect-only tests`
  and the specification-sync tests (`tests/spec_sync`, 56 to 144 s of test time on CI, shared by four workers).
  The suite there took a median of 23.7 minutes a commit (12 to 28, 24 jobs of 2026-10-20 to 2026-10-21) and set
  the wall time of every pull request with earlier commits; in the pull-request runs since it began
  (2026-10-17), it found a commit that failed alone while the head passed five times, two of them by the checks
  the job keeps. `tests/unit/test_ci_workflows.py` holds the job to the collection of every test and the
  specification-sync tests and to nothing more, with controls (the whole-suite step put back, the collection
  removed or narrowed to a directory, the specification-sync tests removed, `freeze_schema.py --check`
  removed). The workflows and property READMEs say what each commit and the head now get and the chance of a
  `dev` audit failing a pull request (about 1.5e-4, from 1.6e-3); the workflows README also the measured
  set-up time of a job (6 to 8 s, where it estimated 1.5 minutes) and the organisation's runner limit since the
  move.
- The fuzz job's replay step skips every mutant search by a rule, `--ignore-glob='tests/property/test_*mutants.py'`,
  not by a list of modules: the list named the older mutant modules only, so the step collected 623 tests, 312 of
  them in mutant modules that are derandomised and keep nothing in the example database. It now collects 311. The
  mutant tables' checks (`test_*mutant_table.py`) draw under the profile's database and stay in the replay.
  `tests/unit/test_ci_workflows.py` collects with the step's own arguments and compares the files with the
  property modules that are mutant searches keeping no database; it fails with a mutant module's pattern removed
  and with a property module wrongly skipped. Locally the rule saves about 6 % of the step (434.7 to 410.6 s at
  8 workers): the replay's growth is mostly in the property modules and the mutant tables, not the mutant modules.
  The fuzz job's `timeout-minutes` is 120, from 65: its slowest run on CI took 59.5 minutes (the weekly run of
  2026-10-19, run 39234564233; the replay 16.8 minutes against 2.6 to 6.3 before), and the job is held to twice
  its slowest run as the Hypothesis job's shards are (`FUZZ_SLOWEST_ON_CI`, which fails below it). What the job
  runs is unchanged.
- The fuzz job's control step runs fuzz target 4 on the fault seeded in a table as well
  (`MATERICA_FUZZ_SEEDED_FAULT=tables`; the maintainer's ruling of 2026-10-21), in two runs of its own side by
  side after the step-10 fault's, each of up to 480 s: one and a half times the slowest of six local finds (16
  to 319 s), to the minute, as the step-10 fault's 900 s are of its slowest, 601 s. The step passes where either
  run reports a line of the model's assertion in which the implementation gives `form_invalid` and the model
  does not. `tests/unit/test_ci_workflows.py` runs the step as written, a stub standing for each fuzz run, and
  fails with the table's runs removed, with one run, with shorter runs, with the two one after the other, with
  the check removed and with the runs without the step's dictionary; the check fails where no run finds the
  fault and where the only finding is another disagreement. The job's timeout rises from 120 to 137 minutes: twice its slowest run on CI (59.5 minutes)
  and the 8.5 minutes the two runs add by estimate (`FUZZ_ADDED_SINCE`, until a run on CI measures them).
- The fuzz job's control step runs fuzz target 4 on the fault seeded in a table's value too
  (`MATERICA_FUZZ_SEEDED_FAULT=table_edges`, S3b-2; the maintainer's ruling on the fuzz controls, 2026-10-21),
  in two pairs side by side, four runs of up to 900 s each, after the table's: the step passes where any of the
  four reports the fault's message. `tests/unit/test_ci_workflows.py` runs the step as written, a stub
  standing for each fuzz run, and fails with the four runs removed, with three, with shorter runs, with the
  four one after the other, with the check removed, and with the runs without the step's dictionary or with
  another, since the rate was measured with it; the check fails where no run finds the fault and where the
  only finding is another fault's. The job's timeout rises from 137 to 168 minutes: twice its slowest run
  on CI (59.5 minutes) and the 24 minutes the table's runs and these add by estimate (`FUZZ_ADDED_SINCE`). The
  ruling gives the fuzz controls a job of their own, a runner for each pair: this control moves there when S4's
  piece builds it.
- The fuzz job runs fuzz target 5 (S3c, **Verification**) weekly for `fuzz_seconds` as it runs the others, and
  its control step runs it on the fault seeded in an extrapolation's method
  (`MATERICA_FUZZ_SEEDED_FAULT=extrapolation_method`), in four runs side by side, each of up to 480 s, the
  slowest of ten local finds to the minute: at the rate measured, all four miss with about 3e-5 on a runner 1.4
  times slower than the laptop, an estimate. The step passes where any of the four reports the oracle's message
  that an extrapolation breaking its shape is not refused. `tests/unit/test_ci_workflows.py` runs the step as
  written, a stub standing for each fuzz run, and fails with the four runs removed, with three, with shorter
  runs, with the four one after the other, with the check removed, and with the runs without the step's
  dictionary or with another; the check fails where no run finds the fault and where the only finding is
  another. The job's timeout rises from 168 to 223 minutes: twice its slowest run on CI, 111.4 minutes, the job
  dispatched on S3c's draft (run 39596069518, 2026-10-21), which holds every step the job now runs and passed
  (control 51.1 minutes, the five targets 25.4, the replay 34.5). The run of 2026-10-19 that had set it took
  59.5; the 38 minutes estimated since for the table's and the table value's controls, this target and its
  control came to 34.0 measured, and the replay of the property tests, which no estimate counted, took 17.7
  minutes longer (`FUZZ_SLOWEST_ON_CI`; nothing is added since by estimate). The run shows the control passing
  on one runner, not its rate, which stays the estimate above. `scripts/pre_review.py` runs the two fuzz oracles' tests where the specification text
  their property imports read changes, as a trace of the files the tests open showed, and target 5's oracle's
  where a conformance file changes, since the oracle reads two inputs.
- The fuzz job's control step runs fuzz target 4 on the fault seeded in step 7 over a table alternative
  (`MATERICA_FUZZ_SEEDED_FAULT=table_alternatives`, S4d, **Verification**), after the method's: a round of four runs
  side by side, each of up to 900 s, and another where no run of a round found it, three rounds at most (about 16
  minutes on average, 45 at most). Of the two parts of the bar the maintainer's ruling sets the fuzz controls, it
  fails the first, a find in each of ten runs within 900 s on the runner's time: of its ten local runs, three missed
  and two found it after the 643 s that 900 s are on a runner 1.4 times slower. It meets the second, a weekly miss of
  at most 1e-3, at the rate measured locally, 1.1e-3 finds a second, a point estimate: all twelve runs miss with
  about 2e-4 on a runner 1.4 times slower than the laptop, where four alone would miss with about 0.06; at the
  rate's one-sided 95 % lower bound, 5.2e-4 finds a second, twelve would miss with about 0.018. The rounds stay
  until the maintainer rules on them; the rate is an estimate until CI's own runs measure it. The step passes where
  any run reports a line of the model's assertion in which the implementation gives a table alternative's
  `outside_range` and the model gives none. `tests/unit/test_ci_workflows.py` runs the step as written, a stub
  standing for each fuzz run, and fails with the runs removed, with three a round, with one round, with every round
  run though the first found it, with shorter runs, with the runs one after the other, with the check removed and
  with the runs without the step's dictionary; the check fails where no run finds the fault and where the only
  finding is another disagreement. The job's timeout rises from 223 to 314 minutes: twice its slowest run on CI,
  126.7 minutes (the run dispatched on S4d's draft, its control step running one round of this control, by its
  timing: the step's log does not say), and the 30 minutes of the two rounds that run did not run, 15 at most each
  (`FUZZ_ADDED_SINCE`). The 55 minutes S4d added by estimate came to 15.3 measured there (the control step 13.0, the
  replay 2.3). The control moves to the fuzz controls' own job when S4's piece builds it.
- The Hypothesis job's `alternatives` parts have a `deep` timeout of 110 minutes, from 90, by estimate (S4d): S4d's
  properties (HP39's two parts and HP40) take 175 and 110 s of the parts' test time at `ci` locally; ten times that
  at `deep`, on a runner 1.9 times slower than the laptop, shared by four workers, adds about 13.9 and 8.7 minutes
  to the parts' measured 38.7 and 32.2, and 110 is twice the slower, 52.6, and three, rounded up to a multiple of
  five. `tests/unit/test_ci_workflows.py` holds the interrupt at twice the estimate until a `deep` run measures it.
  At `ci` the parts take an estimated 5.3 and 4.2 minutes on CI (165 and 132 s locally; `main`'s take 121 and 114
  locally and 197 and 218 on CI, at most 1.9 times as long), under a third of their 20-minute timeout, so S4d's
  properties stay in the shard.
- The repository moved from `Microrobotics-Simulation-Framework/OpenMaterica` to `OpenMaterica/OpenMaterica`.
  GitHub redirects the old git and web URLs; the README, the site, the scripts, the unit test and the workflow
  documentation name the new place. MIME and MADDENING stay where they are. The README's attestation command says
  which repository to name for which release: the old one for 0.1.0.dev1 and 0.1.0.dev2, the new one from the next
  release on.
- The Hypothesis job's `alternatives` parts have a `deep` timeout of 90 minutes, from 45, set by estimate before
  the weekly `deep` run: at `ci` the parts took 196.8 and 218.0 s of pytest time (run 39404674681), ten times the
  examples is 33 and 36 minutes, and the timeout is twice the upper end, rounded up to the figure `records` has,
  until a `deep` run measures it. The job's `timeout-minutes` and the `JOB_MINUTES` its pytest step reads, which
  the interrupt is set from, change together; `tests/unit/test_ci_workflows.py` holds the interrupt at twice the
  estimate and fails where the clause is removed.
- Two of the maintainer's decisions recorded. The documentation plan's constraint 19, and its mirror in
  `CONTRIBUTING.md`, name a second tool that goes online (2026-10-20): source discovery and acquisition, like
  registry drafting a command a person runs with an explicit flag, which the MCP server never loads; the
  architecture draft's section 7.2 says the same. The architecture draft's section 12.2 places the curation
  tools (R15) in 0.1, as decided on 2026-10-15: quote attach-and-verify and the page text it reads by 0.1.0a1,
  the other tools by 0.1.0b1; its release table had them in 0.2.
- The quickstart and the examples' README no longer say a viscosity read stays `unknown` "until the
  consumer's declaration waives it". A waiver leaves the read `unknown` and covers the reason when the build checks
  it (`declarations.md` section 4.2); an implied condition that states the shear rate is what changes the read, to
  `met` where the request's tolerance for it holds (`read_side_contract.md` section 5). Wording only; no case, no
  schema and no behaviour changes.
- `scripts/gen_kill_counts.py --record` refuses reports that do not cover every recorded group, each of its
  recorded mutants at both sizes, and names each group they lack, and the mutants they lack of a group they
  hold. It replaced each group a report held, so a report of part of a group's searches dropped the kill
  points of the rest, and `--check` still passed (a README row of a mutant the file lacks passes it). Recording
  one group alone is kept, and made explicit: `--group GROUP` records the groups it names, which the reports
  must cover, and keeps the others (refused, as before, where the inputs changed). A mutant or a group that is
  gone is dropped by `--measure --record` alone, from a run of every search. `tests/unit/test_gen_kill_counts.py`
  holds the refusal for a report of part of a group, of a group left out and of both, and for a group `--group`
  names that the reports do not cover; its control, the check removed, records a report of part of a group and
  loses the kill points of the rest. `--measure --record` and `--against` are unchanged.
- `tests/unit/test_ci_workflows.py` holds that the parts of CI's test matrix that run with
  `MATERICA_TRACE_SELECTION=1` run the pre-review script's trace test once on every event. Its check counted
  the jobs that set the variable, each combination whole, so the variable on a part that does not hold the
  test (after a re-shard or a change of weights), the test moved to another job's selection, the pytest step
  skipped on an event, or the step's own setting clearing the job's, each left the test unrun and the check
  green. The new check reads the variable as the pytest step sees it (the step's setting, else the job's, else
  the workflow's), keeps the parts whose step runs on the event, and collects their selections for real (two
  collections, about 9 s locally), the trace tests being those of `tests/unit/test_pre_review.py` that take its `trace`
  fixture. On stand-in collections it fails, where the older check passes, with the variable moved to the
  other part, the test moved to the other part or to a Hypothesis shard, the test in both parts, the step
  skipped on pull requests, and the variable set by the job and cleared by the step. No job changes; the
  tests job's comment names the check.
- The Hypothesis job's `deep` timeouts are held to the times measured on CI, where estimates set several of
  them: each is at least twice the shard's slowest job measured at `deep`, with the interrupt's three minutes
  to spare, a shard run in parts taking its slowest part's time. The measurements are each job's time,
  started to completed, in two dispatched `deep` runs of 2026-10-21 (39540221119, main at 76907779;
  39553647007, at the tree main now holds, with the audit controls of the floors held at `deep` alone in
  `relations`) and the first `deep` run (39002750375, 2026-10-17). `records` goes from 90 to 105 minutes
  (slowest 50.8) and `json` from 45 to 55 (23.9), whose interrupts had fallen below twice their measured
  times. The others stay as they were, each above the rule: `agreement` 360 (slowest part 77.3), `relations`
  345 (65.2), `writer` 180 (67.4), `conditions` 180 (62.4), `alternatives` 90 (38.7), step 8's mutants 45
  (1.6). They are not lowered to the rule: the same code has run at least 2.7 times as long on one runner as
  on another (the writer shard at `ci`, 11 minutes and past 30), which three runs do not bound; lowering them
  is the maintainer's call. `tests/unit/test_ci_workflows.py` holds each interrupt at twice these times
  (`MEASURED_ON_CI`; the estimates it held for `relations` and `alternatives` are gone) and each timeout at
  most GitHub's 360, with controls under the rule for `records`, `relations`, `agreement`, `json` and the
  default, the `alternatives` clause removed, and `agreement` at 365. The job's comment and the property
  README give each figure as measured, with its run and date.
- The Hypothesis job's `records` shard has a `deep` timeout of 135 minutes, from 105. `main`'s dispatched
  `deep` run of 2026-10-21 (39578840767, at 0b9f6a5e) took 64.3 minutes for the job (09:41:51 to 10:46:07),
  pytest running the whole shard in 3,844 s, 99 passed and 1 failed, the failure a strategy that could not
  build its case (HP13's `source_range_disjoint`, **Verification**), not time: above the 50.8 minutes that set
  105, so that its interrupt, at 102, fell below twice it. 135 is twice 64.3 and three, rounded up to a
  multiple of five, as the rule sets each. Every other timeout is as it was. The job's comment gives the run
  beside the three before it, and `tests/unit/test_ci_workflows.py` holds the interrupt at twice 64.27
  minutes, its control now at 131.

### Schema
- `test_method` gains `reference_formulation` (maintainer, 2026-10-19): the test method of a value evaluated from
  a reference formulation or an equation of state, origin `evaluated_from_formulation` (`provenance.md`
  section 6.1 item 10), so that a consumer that names `test_method` in its requirement can accept such a value by
  its stated method, while, with no acceptance, the `test_method` entry of a value that states none is still
  `unknown` (`condition_unstated`). The vocabulary (`conditions.json`, whose list the writer schema binds a
  `test_method` token to) and the typed shapes are regenerated from the table, and the reference model's row
  lists the token. No read rule changes, so no conformance case does.
- `record_format.md` section 4.1 says, in two sentences (maintainer, 2026-10-19), that the Newtonian label on a
  value with no stated shear rate is no evidence at any shear rate: a label its row allows changes no member of a
  read's result but `labels`, so with no acceptance the value's `shear_rate` entry is `unknown`
  (`condition_unstated`) (PR-104, PR-053), and treating the fluid as Newtonian there is the consumer's own
  declaration, never the label's: an implied condition that supplies a shear rate (PR-316), or a declaration that
  covers the reason. No rule widens a label beyond its stated `shear_rate` condition.
- Page-text documents and the place of a quote in a copy (maintainer, 2026-10-20;
  `docs/specification/page_text.md`; `changes.md`). A checker, which reads only JSON, reads a copy's text from
  a page-text document: the text of one copy as one named extraction gave it, a PDF's visible text per page
  with its doubtful ranges (two readings compared glyph by glyph), reading-order jumps, furniture and raised
  and lowered text, or an XML file's text and elements with table cells' columns; it names its readings, is
  identified by its RFC 8785 hash and is never published. A quote's place in a copy (pages or element paths,
  character ranges counted in code points, the value's characters, and, for a PDF, user-space boxes for a
  viewer) sits in the evidence's `copy`, outside the content hash, with the hash of the page-text document it
  counts in; across a page break it leaves out only whitespace and furniture, and a stamped copy's place never
  ships. RC-032 compares a quote with that place alone, under every reading of its line-end hyphens, reads the
  value's numbers where the place marks the value, fails a value marked in an XML table cell outside the
  locator's column, and reports `not_checked`, never a pass, where the place is flagged, a PDF's readings are
  fewer than two, or the located text is doubtful, crosses a jump, or holds a code point unassigned or
  private-use in the checker's Unicode database. The normalisation of `quote_sha256`, which a `quote`'s
  comparison now shares, removes invisible format characters first and lists the 25 `White_Space` code points
  (`provenance.md` section 4 item 4). `copy.sha256` is written as `sha256:` and 64 lowercase hexadecimal
  digits. No reader change: a read never checks `copy`. The writer schema's `copy` takes the place and
  `sha256`'s form, and `schema/0.1/page_text.json` gives a page-text document's shape. The eleven plain-read
  fill-in inputs and `examples/records/human_plasma.json` write a copy's hash with the prefix; no content hash
  or pin moves. The record-check suite's first 197 case files come with it (RC-031, RC-032, RC-033's
  `quote_sha256` vectors, RC-220 to RC-226), waiting for the code that runs them, and the case-file format
  gains what they need (`docs/specification/README.md`, "Case files"; `case.json`): `inputs.page_texts`,
  `compare.rules_compared`, the comparison of a quote reported under RC-032, and the operation `quote_sha256`.
- The maintainer's rulings on S2b-2's review (2026-10-19; `docs/specification/changes.md`), on the reference
  model's open points:
  - `evidence_entry_provenance`: `record_format.md` section 4.3 item 2 now says that step 8 checks an evidence
    entry's `provenance` as a field's (`provenance.md` section 2 item 6), and returns the members that check
    leaves unchecked as found. The reader has read it so since S2b-2. Two PR-052 cases come with it: a
    report's provenance whose origin the reader does not know (`unknown_token`), and one whose `extraction`
    is a number (`met`, returned as stored). `read_result.json` returns a report as one now: its own
    definitions of a report, a withheld report, a report's provenance and its source take every member the
    writer marks write-only as any JSON value, required nowhere, and the rest as the writer's, a review as a
    result's and a derived value's derivation as a result's; `tests/spec_sync/test_schemas.py` holds each to
    the writer's. Until now the result typed a report as the writer's, so the second case's correct result
    did not validate. So the result schema no longer refuses a member the version does not define inside a
    member it takes as any JSON value (`extraction`, say): `read_side_contract.md` section 2 item 5 leaves
    such a member out, the reader does (a unit test holds it), and no case or schema holds another reader to
    it. With the maintainer's ruling of 2026-10-20 on the reviews inside a report's provenance, the sentence
    also says that each provenance those members hold, at any depth (one that `per_parameter` maps a
    parameter to), returns its `review` as every review is read; the reader has done so since S2b-2, and the
    reference model, which returned such a review as found, reads it so too. Two more PR-052 cases: such a
    review of a status token a review does not take, and one absent, each returned as `not_checked`.
  - `members_of_the_other_kind`, its record half: `provenance.md` section 6.1 item 1 now says that a numeric
    condition holding `token`, or a token condition holding `value`, `range`, `plus_minus` or
    `set_or_measured`, breaks its shape (`form_invalid`), whatever that member holds, and so does a member one
    slip from one (`record_format.md` section 10 item 5), as the request half's sentence says for an implied
    value. Step 8 ignored each until now, as a member the reader does not know, and its slips too; it refuses
    them (`value_shapes.OF_THE_OTHER_KIND`, and `based`'s `other_kind`), and a token condition's `unit` keeps
    step 9's rule. Six cases: under PR-045, a temperature holding `token`, and a density kind holding `value`,
    each with a value of its own kind's type, and a temperature holding `token` as a status object and a
    density kind holding `value` as `null`; under PR-030, a temperature holding `tokens`; under PR-301, a
    temperature holding `token` beside a basis the reader does not know, which gives `unknown_token` beside
    `form_invalid`, as step 8 makes all its checks. HP12 lists no open point since, and fuzz target 4 holds
    such a field to the model as any other.
  - `alternatives_named_at_a_field`: fail closed, as built and as the text decides it (`record_format.md`
    section 5 names `alternatives` at a field's place, and section 10 item 5 refuses a slip of a member named
    there); no text changes. One PR-030 case, `alternative` beside a constant (`form_invalid`), which kills
    the reference model's fault that ignores such a slip, a survivor of the cases until then.
  - `names_a_declaration_gives_a_requirement`: already decided (S2a-4's review, approved 2026-10-18): a slip of
    a requirement's `field`, or of a requirement condition's `reason` or `consequence`, is refused at step 0,
    as `read_side_contract.md` section 1 says of a slip of a member `declarations.md` names. The reference
    model, its seeded faults, HP12 and the READMEs cite the ruling; no text changes.
  - A nominal's `params` in place of its value: `read_side_contract.md` section 1 now says that a nominal
    takes `params` in place of `value` only where the row of the field it names allows the form
    `parameter_set`, so a nominal holding `params` and no `value`, for a field whose row allows none, breaks
    its shape (`request_incomplete`). Step 0 has required a `value` in every nominal since S2b-2, which is
    that reading while no row of this version allows a parameter set; the text did not say whether step 0
    consults the named field's row. A unit row (`params` alone), which the review's mutant fails, and one
    PR-330 case come with it.
- The writer schema's `table` (S3a), in place of the placeholder `table_field` held: `axis`, `axis_unit`, `x`,
  `y`, `scheme`, `edges` and `source_range`, none write-only, since a read checks every member of a table;
  `points` is not defined, so the closed writer refuses it (`record_format.md` section 6, table item 5). A
  log-log table's numbers are above zero, `edges` lists no number twice (`uniqueItems`, under which both
  validators the tests use take `-0` and `0` as equal), and the rules across members are step 8's, which T1
  lists with their reasons. The vocabulary gains `table_scheme` (`forms.json`, from table item 2), `axis`, the
  numeric conditions' names, and the binding `axes` (`conditions.json`), which the writer applies to a table
  field: each axis's registered unit in `axis_unit`, and the axis condition held as `not_applicable`. The
  reader schema and the typed shapes are generated again (`Table`, `TableScheme`, `Axis`); like every binding,
  `axes` is left out of both. `gen_reader_schema.py` copies `uniqueItems`. No specification text changed: the
  text, its cases and `changes.md`'s entry landed with S3-spec and S3-cases.
- The result's shape (the maintainer's rulings of 2026-10-19, landing with S3b-2;
  `docs/specification/changes.md`). Under `no_pick` each `alternative_values` entry holds its own alternative's
  `unit`, as stored, and the result holds no `unit` of its own (`read_side_contract.md` section 2: the `unit`
  and `alternative_values` rows, and item 6; `record_format.md` section 5 item 5 now lists each entry's own unit
  and labels beside its conditions, specimen, statistics and provenance). This replaces S4a's interim rule,
  under which the result held the first remaining alternative's unit and another alternative's `reason` was not
  returned. And a result whose value is read from a table holds that table as stored, in a new member `table`,
  present exactly when `value` is and is read from a table (the field's, the one alternative left or the one a
  pick names, under an extrapolation too), so that a consumer's own evaluator takes the table the read checked;
  PR-318's and PR-336's rows say so. `read_result.json`'s `alternative_value` requires `unit`, the result
  gains `table`, and `result_value` names the table's shape, which it took through the placeholder before;
  `case.json`'s compared result gains `table`; the typed shapes are generated again. The 31 case files whose
  expected answer held a result's `unit` beside `alternative_values` (17 of S4's later pieces, and 14 of
  S2a-4's, S2b's, S4a's and S3b-2's) are rewritten through the case tools, each entry's unit its stored
  alternative's, which was the result's unit in every one but S4a's three evidence arms (checked against each
  input), with their `CASES.md` rows and PR-013's row. The read and the reference model give each entry its
  unit; the model's two seeded faults of the unit, and the three mutants of the properties, now set every
  entry's unit to one alternative's.
- An extrapolation's shape (the maintainer's rulings of 2026-10-19, landing with S3c;
  `docs/specification/changes.md`). `read_request.json` gives a request's extrapolation its own definition,
  `method`, one of the two tokens `declarations.md` section 4.1 lists, which the vocabulary now generates
  (`acceptances.json`'s `extrapolation_method`), and `law`, a string of at least one character; a pick and an
  overlay keep their placeholder. A result's `assumption` under an extrapolation holds exactly `acceptance`,
  `method` and `law` in `read_result.json`. `method` so has a third meaning, allowed in the name-overlap list
  with its safeguard: each of its three places refuses the other two meanings' values. `declarations.md`
  section 4.1 item 3 says where a `consumer_law` extrapolation's end value comes from: the read's, at the
  readable range's nearest end, or the evaluator's where it returns one, which section 7 item 1 lets be absent
  outside the range. The typed shapes are generated again.

### Data
- `example/water` states the test method `reference_formulation` on each of its four values, all evaluated from
  the IAPWS formulations (maintainer, 2026-10-19). A condition changed, so its version is now `1.0.0`, a major
  change by `record_format.md` section 8 item 3, and its content hash
  `sha256:88851e6263f4dba3f41137f07a8a95dba13cb09bf36650a361bc11ff5bf22a07`; its label is unchanged, and it is
  still an example, not yet fully human-reviewed. A read of it now names the test method: the quickstart's
  request and the pinned reads in `tests/examples/` accept `reference_formulation`, and one that names none reads
  the stated method `unknown` (`condition_unchecked`), as `examples/README.md` now says. New tests read the water
  values refused by an accept list of measuring methods alone (`condition_not_accepted`), and the plasma,
  measured, `unknown` (`condition_unstated`) once its method is removed, by a request that also accepts
  `reference_formulation`, and `not_met` (`condition_not_accepted`) by one that accepts `reference_formulation`
  alone.

### Verification
- The maintainer's rulings on a report's provenance (2026-10-19 and 2026-10-20) come with four PR-052 case
  files, which run and pass: a report's provenance whose origin the reader does not know, and one whose
  `extraction` is a number; a review inside a provenance that a report's `per_parameter` maps a parameter to,
  of a status token a review does not take, and one absent. Four broken implementations show the runner fails
  on them: a report's provenance left unchecked, or checked in every member; such a nested review returned as
  found, or none returned where it holds none. Each fails under its broken implementation alone; the first
  kills the reference model's fault that leaves a report's provenance unchecked, a survivor of the cases until
  then, and the last two kill the model's new fault that returns such a review as found.
- The ruling on a record's condition holding the other kind's member (2026-10-19) comes with six case files
  (**Schema**, above), which run and pass. Six broken implementations, each an old or partial reading, fail
  none but these cases: no earlier case held the record half. The unknown-member positions R11 and R12 name
  the other kind's members, so a slip of each is injected in every host, and T1 lists the four PR-045 inputs
  and the PR-301 one under a new kind, `other_kind`, and the slip under `slip`.
- The ruling on a slip of `alternatives` at a field's place (2026-10-19) comes with one PR-030 case
  (**Schema**, above), which runs and passes. A broken implementation whose step 8 does not name
  `alternatives` at a field's place fails it, and no other case; T1 lists its input under `slip`.
- The ruling on a nominal's `params` (2026-10-19) comes with one PR-330 case (**Schema**, above), which runs
  and passes; a broken implementation taking `params` in place of a value fails it alone. 957 of 1504 case
  files pass.
- Four record-check arms name every sentence that decides them in `CASES.md`'s **Decided by** column. Three
  (`typography_quoted_as_printed`, `ligature_mapped_by_nfkc`, `format_character_removed`, of RC-032) named
  `page_text.md` 3.8 alone, where 3.6 and `provenance.md` 4.4 first find the match; they now name "3.6, 3.8 and
  `provenance.md` 4.4". `information_separator_not_a_space` named 3.6 alone, where `provenance.md` 4.4 (U+001C to
  U+001F "are not `White_Space`") decides; it now names "3.6 and `provenance.md` 4.4". No case file, input or
  expected answer changes: four rows of one table.
- The properties that the planned mutant searches stand in for are held to the regions where those mutants show
  (maintainer, 2026-10-19). A planned search shows that a check kills its mutant, not that the property's own
  strategy still draws the region, so a change that stopped drawing it passed every test (PR #49's review, M1).
  Six regions, of the three searches planned for a long tail and of the two planned with the generated counts (one
  of them in two groups), were drawn by their properties in under 0.03 of the examples, too seldom for a draw
  floor at `ci`. Each property now draws its region in a weighted branch, records it as a feature computed from
  the example or from the read's result, and declares it by its chance, below the least share measured over 48 to
  144 runs at `ci` (0.08 to 0.18, where the means are 0.132 to 0.257; HP12's faults' is at its least, below): a
  run is held to a floor of 15 to 95 examples of 2,000, which a correct run falls below with a probability of
  7e-16 to 2e-11 by the audits' model (250 draws each shown in 5 examples) and of 1e-38 to 8e-18 at the variance
  measured. HP1 draws the planned search's read before the kind, in about one draw in seven, so that the branch
  takes from every kind and fault alike, and from `unknown_at_step_10` most of that kind's draws of `unchecked`: a
  result holding `condition_unchecked`. HP12's faults and values draw their region inside a kind that can hold it,
  so that their kinds stay drawn alike: the same result in about a quarter of the draws of steps 9 and 10, and a
  constant's read under `want: bounds` that reaches step 13 in about one draw in seven of each kind of values. The
  one-slip relation draws a name with an empty word against the same with `s` or `es` in it in about one in four
  of its unrelated names and two slips not swapped far apart, never a one slip's draw; HP7's table removes a
  condition the row requires from record and request after the kinds in about one draw in seven; and the hash's
  edit property places an edit below `review` or `copy` in a provenance that is an array beside the record's own
  members in about three in ten of its edits outside every provenance object. HP12's values hold the member the
  reader does not know to a chance of 0.2, as HP6 does (`unknown_members_returned`), and plant it in each draw of
  their region. A floor catches a region no longer drawn; HP1's and HP12's lie below the thin shares main drew,
  which no floor at 1e-6 could tell apart, though `deep`, holding each chance at a third, would catch most such
  slides. A control for each (`tests/unit/test_audit_controls.py`) shows the audit failing on that feature alone
  when the generator stops producing it, and a second shows, over the property's own draws, that an example shows
  the feature exactly where the mutant fails the property's check. Over 96 runs, main against the branch, every
  other region of HP1, HP2 and HP11 that the reviews of this change measured kept 0.81 to 1.26 of main's mean
  share (HP1's branch draws, in one of its draws in 32, a read that gives `request_incomplete`, so that the branch
  takes none of that code's share), HP12's values' 0.84 to 0.99 and the one-slip relation's 0.88 to 1.01; each
  first fault of HP12's steps 9 and 10, the kind that holds the region, kept 0.66 to 0.82. The hash's records hold
  a provenance object in an array in half their draws and a `card` or `content_hash` in their provenance object in
  half, which lifts six of its chances, below their least shares on main, above them; HP1's kinds (0.07) and four
  of HP12's values' (`form_interval`, `form_composition`, `form_evidence` and `standing`) still lie above their
  least shares, and HP12's faults' `condition_unchecked` (0.08) is at its least (0.093 over 96 runs, 0.0795 over
  20 more), each far above its floor (`tests/property/README.md`, "The regions held to a floor"). Kill points past
  the 500th example on more of 400 streams than main's (one-sided Fisher p below 0.05) are planned, on the region
  where each mutant shows: `reasons_not_merged` (HP1 over its step 8 and steps 9 and 10 kinds),
  `stated_without_origin_with_a_condition` (HP1 over the five kinds it dies at), `conditions_beside_no_pick` and
  `no_unit_beside_alternative_values` (HP2 over its alternatives), `no_statistics_beside_a_composition` (HP2 over
  compositions under their own `want`), `request_faults_of_the_first_alternative_alone` (alternatives with request
  faults apart), `irregular_plurals_missed` and `ies_plural_missed` (a name with an irregular singular, or a word
  in `y`, against its plural) and the model's `plus_minus_units_unchecked` (a `plus_minus` unit first), with
  `token_condition_unit_accepted` (a token condition's unit first; 8 of 200 streams against 3, which the review
  named), `components_normalised` (a composition under `want: components`) and `unknown_members_returned` (a
  member the reader does not know, where its HP12 row names `unknown_member` alone again). The first five draw
  kinds their properties hold to their chances, and `unknown_members_returned` a region with a floor of its own
  (HP12's values, `unknown_member`, chance 0.2, floor 110); the others have no floor of their own at `ci`,
  their regions being 0.004 to 0.04 of their properties' draws (four have one at `deep`, below). No
  example count, size, fault, mutant or check changed. The new draws and searches moved the kill points of 43 of
  the 479 mutants; the latest kill is still the 487th (`tests/property/kill_points.json`).
- The S3 design's HP13 to HP16 for a table's steps 8 and 9 (`tests/property/test_table_form_*.py`, the
  properties in the `records` shard, their mutant searches in `step8_mutants`), over tables `tables.py` draws
  on a field whose row allows one, over a numeric axis drawn, beside a composition in the record: HP13, in
  four parts, one fault of a catalogue written from the text (31, three of them near misses) gives exactly the
  reasons its rule gives, the base passes, and the read of the record's other field is unchanged; HP14, a
  member one slip from one a table names refuses, any other is ignored; HP15, an `axis_unit` other than the
  registered one, of each kind HP8 draws, gives `unit_mismatch` with the axis; HP16, the row's label refused
  exactly on a table over the axis its Label cell names. Each draws its fault, kind or way first, at most
  eight, held to its draw floor (at `ci`, 50 to 440, each failing a correct run with a probability of at most
  1e-6 by the audits' model), and each has an audit control, three more for the regions below. Twenty
  mutants, the design's eighteen, one that lets a table's fault refuse its record's other fields and one that
  reads an empty `x`'s ends, each die at the assertion and the fault they name (`scripts/gen_kill_counts.py`
  records them). Three searches are planned, each drawing alone the faults where its mutant shows: an edge at
  zero held as `-0` and `0`, on bases whose zeros are held as `0` or on any base, and the axis condition held
  as a value, which one fault now draws in two of its four ways, a region declared by its chance (a floor of
  10 at `ci`); over 40 seeds a size each dies at the first or second example, at its own assertion.
- HP13's fault `source_range_disjoint` is built for every `x` step 8 accepts. Where no finite double lies
  beyond either end of `x`, which then holds the least double and the largest, it lowered the last knot by one
  double first, and refused to build the case (an assertion in the strategy) where the knot before it was that
  double: `main`'s dispatched `deep` run of 2026-10-21 (39578840767) drew such an `x`, twelve adjacent doubles
  from the least, `0` and the two largest. It now lowers the run at `x`'s top, the last knot and each before
  it that is the knot after it (an edge's two entries) or the double below it, each by one double, an edge
  among them in `edges` too, each value of `y` kept at its knot. The knot before the run lies below where the
  run's lowest knot goes, so step 8 accepts the table as before and the `source_range` past `x`'s range,
  here the largest double alone, is its one refusal. Five cases pin it: `x` the least and the two largest
  doubles, its mirror, both ends beside knots, an edge beside the largest, and the deep run's `x`. Each holds
  HP13's check, the `source_range` past `x`'s range, `y` unchanged and the table without the `source_range`
  past steps 8 and 9; the old fault fails four of them, and the mirror, whose run lies at the bottom, passes
  under both. The last check is the one that holds the fault's meaning: with the edges left where they were,
  or the last knot alone lowered, HP13's own check still passes, as a broken `x` gives `form_invalid` too.
  The fault draws nothing, so no example's draws, kill point or feature share moved. The other faults of HP13
  that take a double beside an end, and S3b-2's table reads, take one only where it is finite (where `x` has
  no room, past a guard of the largest doubles, or among the places kept finite), and need no change: in a
  local run on tables whose `x` reaches the largest doubles, every fault of HP13 and every way of S3b-2's six
  properties passes.
- The writer schema's table: a family of twelve faults of its shape, each refused, and fifteen mutants of its
  constraints and bindings (M62 to M69, B17 to B19, T10, T11, TB7 and U4), each killed; the writer's step-9
  relation holds a table's `axis_unit`. T1 judges step 8 on tables, its inputs and one-fault variants of a
  full table and of one drawn on each row that allows one, with five kinds of exception for the rules no
  schema states; the unknown-member positions read a table's members and status objects; the reference model
  reads a table through step 9 and agrees with every case file it decides.
- Fuzz target 4 holds a table to the reference model, to T1's third relation and to step 9's units, its
  `axis_unit` among them. Its control, `MATERICA_FUZZ_SEEDED_FAULT=tables`, refuses a table over temperature
  whose first knot lies below 250, which no seed holds: six local runs found it, after 16 to 319 s. CI's
  control step runs it (**Changed**, above).
- No seeded fault of the reference model makes it raise. Three did, and the seeded-fault check counted each
  raise as a kill (measured over all 97 faults and every case file of a read):
  `tolerance_without_an_operating_condition` on two of its three files, by indexing an operating condition
  the request lacks, and `alternatives_shape_unchecked` and `condition_shapes_unchecked` on one file each.
  Each now answers where it takes effect and still breaks its rule: a condition whose tolerance has no
  operating condition is read as one given no tolerance, an `alternatives` that is not a list as a list of
  its one entry, and a condition left unchecked that steps 9 and 10 cannot index as one the record does not
  hold. Over 225 shapes where the three take effect, each read under two configurations of claims, the faults
  as they were raised on 107 reads and now raise on none. Every fault is killed by the same case files as
  before, from the same first file, each by an answer.
- The seeded-fault check fails on a fault that makes the reference model raise on a case file it reads (a
  fault's files in name order, up to its first kill), with the model's traceback and a note naming the case
  file and the claims, where it counted the raise as a kill: a raise shows that the fault broke the model, not
  that a case's expected answer tells it apart (`tests/reference/cases.py`).
  The model's agreement with the cases, which runs through the same comparison, errors the same way where the
  model raises. A control fault, `status_object` replaced by a function raising `TypeError`, `KeyError` or
  `AssertionError`, fails the check in each; with a raise of every kind counted as before, the check passes
  on each and the control's three tests fail, and with a raise of one kind counted, that kind's test alone
  fails. A case on which the implementation raises still fails that case in the conformance runner, as
  before.
- Four of the planned searches' regions that the region floors (above) left with no floor of their own are
  held to a floor at `deep` (maintainer, 2026-10-21): in HP12's faults, a read that plants a `plus_minus`
  entry's unit, or a token condition's, and whose result gives `unit_mismatch` on its condition
  (`plus_minus_units_unchecked`, `token_condition_unit_accepted`); in HP12's values, a composition's
  components given that a normalising read would change, and alternatives refused by faults of the request
  alone on two conditions or more (`components_normalised`, `request_faults_of_the_first_alternative_alone`).
  Each is 0.025 to 0.036 of its part's draws, too thin for a floor at `ci` that a correct run fails at most
  1e-6 (one needs a chance of about 0.065). A new marker, `deep_chances`, declares a feature by its chance and
  holds it to its draw floor at `deep` alone, a floor below 10 failing; `ci` and `dev` count it as declared
  and judge it nowhere (`audits.RULES`, `deep_floors`), and `tests/unit/test_audits.py` holds that, with a
  grid of chances none of which fails a correct `deep` run above 1e-6 by the audits' model. Each feature is
  computed from the example and the read's result, and a control beside the planned searches' own shows that
  over the part's draws an example shows it exactly where the mutant fails the agreement. Each is declared by
  a chance at or below its least share over 24 derandomised runs at `ci` (0.01, 0.007, 0.008 and 0.019; means
  0.025 to 0.036), whose floor at `deep` is 25, 10, 15 and 95 examples of 20,000: a correct run falls below it
  with a probability of at most 7.3e-7 by the audits' model at the chance (2,500 draws each shown in 5
  examples), and of at most 6e-22 at the means and variances measured. A control for each
  (`tests/property/test_model_deep_floor_controls.py`) runs its property for `deep`'s 20,000 examples with the
  region stopped and fails `deep`'s audit on that feature alone. The controls run where `deep` runs, in the
  Hypothesis job's scheduled and dispatched runs of the `relations` shard, and in no pull request's job:
  marked `deep_controls`, they are deselected at every other profile (`tests/conftest.py`), and
  `tests/unit/test_ci_workflows.py` fails where a `deep` run leaves one out or a pull request's job runs one.
  They add an estimated 84 minutes of CPU to the shard's `deep` run, at most 29 of wall, so its `deep` timeout
  goes from 300 to 345 minutes, twice its estimate, as the timeouts are set. (9)'s irregular plurals and
  plurals in `ies` keep no floor: (9) draws them in 0.0043 and 0.0032 of its examples, and by the audits'
  model a floor at `deep` needs a chance of about 0.0067 (`tests/property/README.md`, "The regions held to a
  floor"). The audit control of HP12's values' `unknown_member` removes the member as drawn instead of
  rejecting each example that shows it: the region of a constant under `want: bounds` plants the member in
  every draw, so the rejection stopped that region too, and whether the control passed rested on the
  derandomised stream: main's code drew the region above its floor of 20, this change's 4 of 2,000 examples.
  No example count, size, draw, fault, mutant or check changed.
- The reference model reads a table to the end as the read does, written from the text (S3b-2): its axis entry,
  step 11's readable range and edges, evaluated by the reference evaluator's `exact` mode, the request's two
  checks there, and the result's `table`. It agrees with every case file it decides, and gives no verdict on step
  7 over a table alternative whose read gives a reason at step 11 (15 files of S4's later pieces, listed). Seven
  seeded faults break its rules (the axis entry at an edge, `outside_range` beside `at_edge`, `source_range`'s
  narrowing, `want_mismatch` alone over a range, the axis on step 11's reasons, a table's unknown members, the
  `table` member), each killed by a disagreement, `table_returned_whole` by the two arms holding a table's
  unknown member and `table_member_dropped` by the three where `table` is present; S3b-2's case files move the
  counts of sixteen other faults, and its fix round's two arms six, every row measured again. Two older faults
  made the model raise in its table code, found by measuring every fault over every case file of a read, which
  the seeded-fault check, stopping at a fault's first killing file, does not do: each answers there, still
  breaking its rule (`best_status` ends a read at step 11 where the table has no value, `null_read_as_absent`
  reads the field without its `null` members at every step), killed by the same files, each by an answer. A
  test holds the five faults that once raised (these two, the three above, and the two `condition_entry`
  wrappers as they were before they took the table axis) to their answers on the case files where they raised.
  The fuzz oracle of target 4 holds a table's axis entry and step 11's reasons to the text
  (`field_oracle.table_steps_10_and_11`).
- The S3 design's HP20 to HP23 and its monotonicity property for a table's steps 10 to 13
  (`tests/property/test_table_read_*.py`; the properties in the `records` shard, their mutant searches in
  `conditions`), over tables `tables.py` draws on a field whose row allows one, over a numeric axis: HP20, at and
  beside the edges, an edge refused wherever it lies, `outside_range` beside it outside the readable range, one
  double either side of an edge reading its own side's interval as the reference evaluator's `exact` mode does,
  and no extrapolation reported able to cover a read at or beyond an edge, an edge on the readable range's end
  among them; HP21, at and across the readable range's ends, with a relation (a `source_range` no narrower than
  `x`'s range and a tolerance on the axis change nothing), drawn over tables whose readable range is `x`'s, so
  that a read its way puts outside is outside without the `source_range` too, which it asserts; HP22, the
  statistics block at every read and `points` refused; HP23, step 11's two request checks, each with the axis;
  and the monotonicity property, a `source_range` or a tolerance on the axis never turning a read `met`, drawn
  as the relation is, over a read that is `met` inside the range, `unknown` where the field is stated without
  origin, and `not_met` outside it, each asserted. Each draws its way first among at most five, held to its
  draw floor (110 to 245 at `ci`), each failing a correct run with a probability of at most 1e-6 by the audits'
  model and at most 4.8e-8 at the variance measured over 20 runs of 2,000 a size (40 for HP20 at `ci`), an
  estimate, and each has an audit control; the monotonicity property holds its worlds stated without origin by
  their chance (0.2, below the least share of 40 runs at `ci`, 0.2335; a floor of 110), with an audit control.
  Eighteen mutants (the design's, two of the monotonicity property, a table's block not as stored, and an edge on
  the readable range's end read as none between the read and the range, on each end, searched by HP20 across an
  edge alone) die at the way and assertion they name, at both sizes, and HP12's table part kills each that a
  result shows, sixteen, as planned searches of its kinds, and two more: a read step 11 refused that goes on to
  step 12, where the field is stated without origin, and the model's `table_returned_whole`, where the table
  holds a member the reader does not know, each a region the part draws and plants; over 40 streams a size, the
  latest at the 183rd example. HP1, HP2, HP11 and HP12 draw a table read to the end in a test function
  or part of their own, some holding a member the reader does not know or stated without origin, their own draws
  unchanged: with the harvested constants held out, their draws on `main` and here are the same, example for
  example. HP2's law of the members gains `table`, with a mutant of its own.
- Fuzz target 4 reads a table to the end (S3b-2): beside the drawn request it reads each table again under `want:
  value` at the places table item 3 tells apart (its knots and edges, the readable range's ends and
  `source_range`'s, the double either side of each, a value beyond each end of `x`; twelve at most), each read
  held to the reference model, to steps 9 to 11 and to HP1 and HP2, `table` exactly beside a value read from a
  table among them. Its control, `MATERICA_FUZZ_SEEDED_FAULT=table_edges`, raises for a read just above an edge
  where the value above lies outside 0.6 to 1.6 times the value below, either way, which no seed holds. In ten
  local runs, in pairs, each of up to 900 s with the control step's arguments, it was found in nine, after 65 to
  725 s, and missed once: a rate of 2.7e-3 finds a second, so that the control step's four runs all miss with
  about 1.1e-3 on a runner 1.4 times slower than the laptop, an estimate. Not every run finds it within 900 s
  of the runner's time (one missed, one found it after 725 s, past 643). CI's control step runs it (**Changed**,
  above).
- The S3 design's HP24 to HP26 and its monotonicity property over an extrapolation
  (`tests/property/test_extrapolation_*.py`, in the `conditions` shard): where one applies, adding it keeps the
  read `not_met` with its reasons, adds step 12's reasons and labels (the field's `label`, drawn where the value
  is stated without origin), and gives the end value from inside the readable range, the members beside a value,
  the table and its `assumption`, `basis` aside; where one at the read does not apply (inside the range, at or
  across an edge, under `want: bounds`, `components` or `evidence`), and where one is located elsewhere, it
  changes nothing; two naming one field are refused wherever located; step 0 refuses a method or a law that breaks
  its shape and reads white space, `basis`, `reason` and an unknown member; and adding one never turns a read
  `met`. Each property draws its way first among at most five, held to its draw floor (110 to 160 at `ci`): over
  20 runs of 2,000 a size, a correct run fails a floor with at most 4.1e-7 at the variance measured, 9.2e-5 at its
  one-sided 95 % bound. 57 mutants die at the way and the assertion each names, at both sizes; over 40 streams a
  size, the latest at the 215th example. Beside the design's, 30 each hold a draw of the strategy, showing at it
  alone, so that a draw cut to one value leaves one alive: among them the field's label, each `want` under which
  one does not apply, and each kind of value of the lists HP26 draws from (its methods that are no token, a
  capital among them, the fuzz control's own fault; its laws that are no text, a number among them, the S3
  design's own; its laws of white space; and a slip's name and the place of its character). S3b-2's two mutants of
  step 11's report on an edge on the readable range's end, which had no reader in a result, are searched in one
  too, across an edge.
- The reference model compares an implied value's unit for a numeric condition whatever else breaks the value
  (`read_side_contract.md` section 1: "checked as an operating condition is, its `unit` included", and an
  operating condition's unit "whatever else is wrong with that entry"). It stopped at a `token` beside the
  value, where the read gives `request_unit_mismatch` beside `request_incomplete`; fuzz target 5 (below) found
  the two answering differently. A new arm, written through the case tools, pins it
  (`PR-320.implied_value_holding_a_token_in_another_unit`, run by S2a-4's code), and fails the model as it was.
- Fuzz target 5, `tests/fuzz/read_acceptance_bytes.py` (S3c): raw bytes, parsed, as the one acceptance of seven
  fixed reads of two conformance tables, below, inside and above the density table's range and below it under
  `want: bounds`, and at the edge table's declared edge outside its narrowed range, beyond it and between it and
  the range, each read twice. It fails where a read raises anything but `NotImplementedError`, where two reads
  differ, where an extrapolation that breaks its shape is not refused wherever it is located
  (`read_side_contract.md` section 1), where a result breaks HP1 and HP2 as an acceptance leaves them or an
  extrapolation's result breaks section 5 (`not_met` with `outside_range`, the members beside the value, the
  table, and the entry's own `method` and `law` in `assumption`), where an acceptance makes a status better than
  the same read without it, and where the read and the reference model disagree but as HP12 lists. Its seeds are
  every acceptance of every conformance case's request (217), with a dictionary that `--dict` writes. Its
  oracles live apart (`tests/fuzz/acceptance_oracle.py`), and `tests/unit/test_acceptance_oracle.py` shows each
  failing and quiet on the core at every place under every seed. On the correct core it found two things: step 0
  raising `TypeError` for an acceptance whose kind is an object or a list (S3c's own, fixed here), and the
  model's implied value (above). Its control, `MATERICA_FUZZ_SEEDED_FAULT=extrapolation_method`, compares an
  extrapolation's `method` ignoring case, one changed letter from every seed extrapolation, none of which holds
  it: ten local runs, each of up to 600 s, found it in all ten, after 7 to 482 s, a rate of 7.6e-3 finds a
  second. The S3 design's own fault, a number taken as a `constant`'s `law`, a seed holds, and under
  `consumer_law` five runs of 600 s found it in none; HP26's mutants `a_law_of_any_type` and
  `a_number_taken_as_a_law` hold it, and `a_method_compared_ignoring_case` the control's. CI's control
  step runs the method's (**Changed**, above).
- HP39 and HP40 (S4d; `tests/property/test_table_alternatives_*.py`, in the `alternatives` shard), over a field
  holding S4a's alternatives beside a table over a condition no other alternative states
  (`table_alternatives_strategies.py`, built from S4a's strategies, which stay as they were): the others' outcome
  drawn first among S4a's five, then the table's way among the four of a part, outside its readable range, over an
  operating range of its axis, and outside under an extrapolation under `want: value` and under `want: bounds`; or
  at an edge inside the range, at one outside a narrowed range, with no operating value for its axis, and with none
  but set aside at step 10. HP39: the read is HP27's oracle, which composes the reads of each alternative alone,
  with step 11's standings, every member compared; a kept or over-range table's `no_pick` entry holds its table as
  stored and step 12's labels; the extrapolation is among what the read applied exactly where the table it covers is
  the one left; and each draw is what its outcome and way say. HP40: moving the table's readable range off the
  operating value gives the read without it, its indexes moved, or `not_met` with every alternative's reasons, and
  never turns a refusal `met`. Each outcome and way is held to the floor of a chance below its least share measured,
  0.11 and 0.14 (floors of 35 and 60 at `ci`): over 20 runs of 2,000 a size an outcome's count and a way's varied up
  to 13.7 times a binomial's, at which the draw floor of one in five failed a run of the first part with 1.2e-3 at
  `ci`; at these chances a correct run fails with at most 2.3e-7 at the variance measured, 1.6e-4 at its one-sided
  95 % bound. 21 mutants of step 7 die at the way and assertion each names, at both sizes: the design's sixteen and
  five the code invites (a kept and an over-range table each refusing the field, a table set aside at step 10
  refusing it, a kept or over-range entry labelled as the first stored alternative, or as the last); over 40 streams
  a size, the latest at the 321st example; kill points recorded, at most 99. Each of the 28 ways to cut one of the
  strategy's draws to a single value fails a test (a floor, the check of the draw, a mutant left alive, or the test
  of HP40's three moves of the range), and with no cut all pass; the table's stored index is held at both ends, by a
  mutant of the entry's labels each, and the operating range's upper end by a mutant of HP12's alone, a range past
  the readable range's end given `outside_range`, which the agreement kills. HP12 gains a part over the same draws,
  its two parts drawn first and held to their floors, which searches 20 of the mutants (the one of what the read
  applied shows outside the result's JSON), that one of its own and three of the reference model's new faults, each a
  planned search of the way where it shows. HP1, HP2, HP11 and HP12's own draws are unchanged: over 18 derandomised
  runs of 2,000 examples, each its own stream, each of their fourteen test functions draws and counts the same of
  each of its 102 features on `main` and here, and every earlier search's kill point stands as recorded. HP27's
  oracle takes the standing and entry rules as arguments, its own by default, so that HP39 composes it rather than
  copies it.
- The reference model's step 7 decides a table alternative whose read gives a reason at step 11, from the text
  (`read_side_contract.md` section 3, step 7; `record_format.md` section 5), by an agent that did not read the
  read's code: 1,285 read case files, 1,178 agreeing and 107 with no verdict (overlays 71, picks 36), none
  disagreeing. Twelve new seeded faults of those rows, each killed by a case file; every fault over every case file
  at the head: 129, 116 killed, 13 surviving, none raising. Four older step-7 faults narrowed back to their own rule
  once these files had a verdict, and `PR-044.across_edge_under_extrapolation_set_aside`, which one of them raised
  on, now agrees (`ONCE_RAISED`).
- Two broken implementations that S4d's case files alone catch (`tests/conformance/test_runner_can_fail.py`): an
  edge setting a table alternative aside, which fails four of them, and a table read over a range counted as a form
  `want` can give, which fails two. `tests/spec_sync/test_unknown_member_positions.py` gates a condition name step
  10 checks on whether step 10 ran, on the field or on its alternative alone, since step 7 now refuses a wrapped
  table host with no operating value for the request's fault.
- Fuzz target 4 reads a field's table alternatives at their places as well (`field_oracle.alternative_places`, S4d):
  each table alternative's places, as many in all as one table's, read under `want: value` and held to the model,
  steps 9 and 10 and HP1 and HP2, so that step 7 meets a table alternative read at an edge, outside its range and
  inside it beside the others; all 817 seeds pass on the correct core. Its control,
  `MATERICA_FUZZ_SEEDED_FAULT=table_alternatives`, refuses the field where a table alternative read outside its
  range at no edge and with no covering extrapolation is set aside, where a value of the table's `y` lies below 900:
  no seed shows it, and one change does (a density table's value lowered below 900, or a byte of a constant's
  condition name beside a viscosity table, each held in `tests/unit/test_fuzz_oracle.py`). The design's candidate, a
  log-log table alternative refused, no seed can show: every seed's table alternative read outside its range at the
  target's 310.15 K sits beside alternatives all set aside, where refusing and setting aside give one answer. In ten
  local runs, in pairs, each of up to 900 s with the control step's arguments, it was found in seven, after 125 to
  866 s, and missed three times: a rate of 1.1e-3 finds a second, 0.80 a million inputs. CI's control step runs it
  (**Changed**, above). `seeded_fault.py`'s count of which faults raise is corrected (the seventh raises; the sixth
  is the model's).
- Every citation of the specification in the tests is held to a quote found at its line, as the reference
  model's are. The seeded faults' table (`tests/reference/mutants.py`) cited the text as `file:line` in 128 of its
  129 `rule` strings (the 129th names an open point), 131 `file:line` references and a bare `:64`, and one comment
  more, with no quote; `test_model_mutants.py` and `test_model_properties.py` held one each, and `cases.py` one
  whose quote never closed. Nothing read them, so a shifted citation passed. Each now holds a quote (136 citations
  in the four files when first read); `tests/reference/test_citations.py` reads their comments and their string
  literals, a `Mutant`'s `rule` being a string that `prose` never saw, and fails a citation with no quote, a quote
  not found where it begins, a quote of fewer than 20 characters, a seeded fault that cites neither the text nor a
  listed open point nor stands in `NO_LINE_IN_THE_TEXT`, and a test module that cites the text and is not listed.
  Limit: a quote must begin on a cited line and may end on a later one, so a range may be shifted by less than its
  width and still pass (a single line shifted by one, or a range shifted by its width, fails). Measured at this
  head, 280 of the 289 ranges among the 550 citations read (the model's 408 and the four test modules' 142) pass
  shifted by one line in one direction or the other, and none of the 261 single lines does. Requiring the quote
  to reach the last cited line too would fail 90 of the 550, and is not done. Two citations moved to the line that says the rule: the `no_pick` result's
  `conditions` (`read_side_contract.md:169-170` to 171-172) and a comment's (169-171 to 164). A `dof` held as a
  status object under a Student's t distribution keeps `read_side_contract.md:134-135`, the rule that every check
  is made, and cites `provenance.md:50-51`, the token check, and `uncertainty.md:48-49`, the shape. A seeded fault
  that no line of the text states is named, not cited: `alternatives_counted_from_one` names the open point
  `alternative_index_base` (no line says an alternative's index starts at zero; the model reads it from zero), and
  `results_share_the_record` stands in `NO_LINE_IN_THE_TEXT` (an implementation property). Weak anchors were
  strengthened or given a second citation (a nominal, a population level, a reviewed review, the end value, a
  `no_pick` entry's labels, the slip rules and a requirement's names), and 15 quotes shorter than 20 characters
  were lengthened. Its controls: in `mutants.py` a rule's citation shifted one line later and one line earlier,
  its quote removed and its quote changed, and in `test_model_mutants.py` a shifted citation; the old check reads
  neither file, and handed `mutants.py` finds none of the four. Also: a quote of `"the"` fails, a range shifted
  by one passes where the quote still begins in it and a range shifted by two fails, and a row that cites
  nothing, names an unlisted point or is listed without cause fails. The check also closes a gap: a quote may run
  on to the line after the last one cited, but must now begin on a cited line, where before one beginning on the
  next line passed; 2 of the model's 408 citations began there (`record_format.md:580` to 581, and 243-244 to
  243-245). `tests/reference/README.md` holds `file:line` references in prose, unquoted and not read.
- HP13 tells a fault built wrongly from one built right. It held that a fault gives the reasons its rule gives
  and that its base passes; most of its faults give `form_invalid`, and so does one built to break `x`, `y`, the
  edges or the scheme as well, which it passed. It now also holds, on every example, that each fault is its
  rule's alone: its read with what its rule judges undone passes steps 8 and 9 (`table_form_strategies.JUDGED`).
  Of the 31 faults, 20 are undone by putting back the members their rule judges as the base holds them, or
  removing them where it holds none (the three that draw the member they break, by any one of those members);
  five, which change another member first so that they can exist, on the table so changed, without the entry or
  the member they added; three by taking away only what they added or wrote (`edge_at_an_end` and
  `repeated_x_no_edge` the entry of `x` and `y`, `log_log_not_positive` the non-positive values made positive,
  its scheme kept); and the three near misses by nothing, their own reads passing. Six controls
  (`tests/property/test_table_form_controls.py`), hand-made builders of `token_not_a_string`,
  `source_range_reversed`, `y_longer`, `edge_at_an_end`, `repeated_x_no_edge` and `log_log_not_positive` that
  also break `x`, `y`, the edges or the scheme, fail at that assertion on each of their first 100 derandomised
  examples at both sizes, the other assertions passing them, and pass without the extra break; without that
  assertion, each passes HP13. The last three passed HP13 until the undos of `edge_at_an_end`,
  `repeated_x_no_edge` and `log_log_not_positive` were made exact: they had put back `x`, `y` and the edges, `x`
  and `y`, and read the table as linear, which mended those breaks too. A seventh control breaks, one at a time,
  each member a fault's rule does not judge, on the faulty read of each of the 28 faults that have an undo, and
  holds that its undo leaves it broken, so that an undo made broader than its rule fails for any fault; it is
  shown failing for `edge_listed_twice` undone by putting `x`, `y` and the edges back, and for each member alone.
  Three faults rewrite `x`, `y` and the edges wholesale (`x_one_value`, `x_without_two_distinct_values`,
  `x_empty_beside_edges_or_a_source_range`), so putting those back is the only undo they can have, and HP13 has
  no power there against an extra break of them.
  The check found a helper building faults wrongly: `an_edge`, which makes a knot an edge for three faults, kept
  a base's `source_range` of that knot alone, which then shared no value that is no edge with `x`'s range (table
  item 4), so that `edge_repeated_thrice` and `edge_listed_twice` broke that rule too. Review found three more
  builders with the same second break by other means, `edge_at_an_end`, `edge_not_repeated` and `edge_not_in_x`,
  which the check cannot see, because their undo takes the edge away. All five now remove a `source_range` that
  meets `x`'s range at the edge's point alone (of that point, or ending there from outside `x`'s range), and nine
  pins hold it, each failing with the removal taken out. No draw is added: over seeds 1 to 4, both sizes and all
  four parts (64,000 examples) every base and every fault drawn is the same as on `main`, and 150 faulty reads
  differ, each only by that range removed (`edge_at_an_end` 41 of 1,809 draws, `edge_not_repeated` 58 of 2,296,
  `edge_repeated_thrice` 28, `edge_listed_twice` 10, `edge_not_in_x` 13 of 2,432). No kill point moved
  (`gen_kill_counts.py --measure`); `edges_zero_and_minus_zero` is undone with its zeros held as `0`, which table
  item 1 reads the same, so that a reader comparing `-0` and `0` by sign bit is still reported at the near miss.
  The check still cannot see a second break of a rule the fault's own member breaks, which putting that member
  back mends too. An independent oracle of table items 1, 2 and 4 written from the text, run over one
  derandomised stream of 2,000 a part and size, found a faulty read breaking a second rule in:
  `x_without_two_distinct_values` 460 of 460 (no other `x` value repeats),
  `x_empty_beside_edges_or_a_source_range` 405 of 586 (the edges' rule) and `x_decreasing` 295 of 414 (the
  range's rule in 199, the edges' in 145 and 95); `edge_not_in_x` 13 of 500 (its edge beyond an end, where no two
  knots have room), and, before the removal above, `edge_at_an_end` 9 of 475, `edge_not_repeated` 10 of 525 and
  `edge_not_in_x` 7 more (none after). Those that cannot be built alone are inherent:
  `x_without_two_distinct_values`, `x_empty_beside_edges_or_a_source_range`, the reversed `x_decreasing` beside
  edges or a range (in a separate stream, 200 of its 228 reversed draws) and `edge_not_in_x` where no two knots
  have room. The swapped `x_decreasing` (117 of its 301 swapped draws in that stream) is avoidable, by choosing a
  pair away from the edges and the range's ends, which changes its draws, and is not closed. Holding every faulty
  read to break no rule but its own and its inherent ones would take such an oracle in HP13 (about 50 lines); it
  is not built.

## [0.1.0.dev2] - 2026-10-20

A development pre-release. It holds S2: the read of a field holding a constant, an interval, a composition or
evidence, with its conditions, the acceptances a read takes (nominals and implied conditions) and the reasons of
its result; S4a: a field holding alternatives, read with no pick and no overlay (the one alternative left, those
set aside, or no pick among those that stay); the core's table evaluator, not yet called by the read; three
example records with a quickstart; and a README and site that say first what OpenMaterica is for. Tables,
extrapolation, picks and overlays raise `NotImplementedError` until later steps. The schema 0.1 files may still
change before 0.1.0. The entries below are everything since 0.1.0.dev1.

### Added
- A builders' check before a pull request is reviewed (maintainer, 2026-10-18), so that routine findings are
  caught before the independent review and the review spends its time on what only an independent reader finds.
  `scripts/pre_review.py [BASE]` finds the files a branch changed, from the merge base to the working tree, and
  runs the checks that apply to them, printing each with the paths that selected it: the sign-off and
  confidential scans and every generator's `--check` for any change; the linters and type checkers for a change
  to code; the tests that import a changed Python file, directly or through others, with a property module run
  as its whole shard at the `ci` profile, and the few tests that read the whole tree instead of importing it; the
  tests that hold or open a changed specification, schema, conformance case, spec-sync table, workflow or build
  file. A change it cannot map to a test selects the whole of `tests/unit`, and the plan says why. A change to
  code also builds the wheel, checks it and type-checks the consumer snippet against it, as CI's static job
  does. Every `uv run` is `--locked` and `uv lock --check` comes first. A name in a diff is printed escaped, a
  command quoted, and a file that cannot be read as Python is named, not a traceback. A stage that fails stops
  the run before the next. It ends with reminders for what no check decides: code changed beside a
  CHANGELOG that was not, and each count the branch states. `CONTRIBUTING.md` has a section, "Before asking for
  review", with each check's command and a short list for the points a builder judges. The script runs the
  checks that apply, not all of CI's, and replaces none; no check was removed and no threshold changed.
- The schema URL scheme (maintainer, 2026-10-18). The site's index page of a schema version that
  `tests/spec_sync/released_schemas.json` does not list opens with a note, "Draft until 0.1.0": its files may
  change until the release, and the release freezes them, which removes the note (`scripts/schema_index.py`);
  the Pages workflow now also runs when the manifest changes, and a test holds its `paths` to the staging's
  inputs. The note leaves the site when the release's pull request, which carries the manifest, merges just
  before the tag. The next line's development schemas will live in a `0.2-dev/` directory, renamed `0.2/`
  (with its `$id`s, its generated files and the paths wired to `0.1`) and frozen at its release; a redirect of
  the address instead is decided at that release. The staging refuses a tree that holds both `0.2-dev/` and
  `0.2/`. The rule is in `DOCUMENTATION_ARCHITECTURE.md` section 7.1, `CONTRIBUTING.md` and
  `src/materica/schema/README.md`. No `0.2-dev/` exists yet, and no `$id` changed.
- The project's artwork in `assets/`: the logo (`images/logo.png`, and `images/logo-full.png` at full size),
  the favicon and app icons (`images/favicon/`), and an animation of the logo for talks and posts
  (`video/logo-animation.mp4`). The logo heads the README and the site; the site serves the logo and favicons
  from its root, and its content security policy allows images and the web manifest from the site itself, and
  still nothing from elsewhere.
- The table evaluator, `core/evaluate.py` (S3b-1), which the read's step 11 is to use; nothing calls it yet. It
  gives a table's readable range, `x` narrowed by `source_range` (`record_format.md` section 6, table items 3
  and 4); whether an operating value lies at a declared edge, wherever the edge lies, or beyond one from the
  range; the knots that bracket it, strictly beside an edge; and the number a read gives there: inside the
  range, the table's value, and outside it, the value at the range's nearest end, taken from inside
  (`read_side_contract.md` section 5), or none at or beyond an edge. Numbers are compared exactly. A value is
  the exact value of the text's formula rounded once to the nearest double, ties to even: a linear one is
  computed in fractions; a log-log one in fractions where its exponent and itself are rational, and otherwise
  bounded in decimal, from 50 digits to 1,600, until both bounds round to the same double. That rests on one
  unproven assumption, the four exponentials conjecture, and past 1,600 digits the code returns its best
  rounding (`loglog`'s docstring). A knot's `y` is returned as stored, `-0` included (the S3 design's S3Q16).
  So it never raises and gives the same double everywhere. It computes no derivative.
- The read's steps 7 and 8 (S2a-2; `read_side_contract.md` section 3). Step 7 finds the target field, and
  gives `absent` where the record holds none; a field holding alternatives raises `NotImplementedError`, since
  alternatives are read at step 7, with S2a-4 (`no_pick`) and S4. Step 8 refuses a form the field's row does
  not allow, a composition's basis included (`form_not_registered`); a value field, form or section
  `specimen` that breaks its shape, a member one slip from one named at its place (in the field, or in the
  envelope, the body or a section, which refuses every field read from it), or a token the reader knows in a
  member whose row does not allow it (`form_invalid`); a token it knows for no member of that name
  (`unknown_token`); and a withheld value (`withheld`), each check made and every reason given. Beyond shapes
  it checks counts, ranges in order, signs and bounds, a statistics block's conditional members, an
  uncertainty's rules, and each status object's place and token (`provenance.md` section 1 item 5); one that
  breaks its shape, a member one slip from one it names included, is read for nothing else, so its token
  gives no reason of its own (`form_invalid` alone, never `unknown_token` beside it: S2a-4's HP12). A form
  the row allows whose own member waits for S2b-2 or S3 (evidence, a table) raises `NotImplementedError`
  whatever its other members hold, since its own member could add a reason: so an evidence entry's
  withholding waits for S2b-2 (an interval's and a composition's own members are read since S2b-1, and
  evidence's since S2b-2, below). A
  form the row does
  not allow is refused with every shared reason, its own member, which a read neither uses nor returns, unread
  (`core/fields.py`, `core/value_shapes.py`). Step 8 reads the status tokens each member allows from the
  generated shapes; a specimen fact's unit as it reads every unit, a string or a status object, step 9 alone
  comparing it; `mimics`'s fixed basis and a disease or treatment state's text as the maintainer's rulings
  settle them; and where a field's label goes from its row (`vocabulary/fields.json`).
- Step 0 refuses, as `request_incomplete`, a request member one slip from one the request's shape names, or
  one `declarations.md` names there (a requirement's `field`, a requirement condition's `reason` and
  `consequence`, each ignored itself: S2a-4's review), a field the vocabulary does not register, and a
  requirement holding a declaration's members.
- The read's steps 9 and 10 (S2a-3; `read_side_contract.md` sections 3 and 5). Step 9 compares each unit a
  field states with the one registered for it, code point for code point, and a unit registered as a status
  object by its token alone: the field's, a known numeric condition's and its `plus_minus` entries', with that
  condition, a `unit` on a token condition, which registers none, and a specimen fact's, against the unit its
  row fixes, wherever step 8 checks the fact (`unit_mismatch`; `core/fields.py`). Step 10 checks the
  conditions the record holds, those the row requires, those another condition requires with its token and
  those the request names, each by section 5's table, every comparison on the exact values of the doubles
  (`fractions.Fraction`), a stated `plus_minus` turning `met` into `unknown` alone (`condition_uncertain`),
  and gives the result's `conditions` once it has run to its end (`core/conditions.py`). A read step 10 does
  not end goes on to steps 11 to 13, which S2a-4 builds (below).
- Implied conditions (`declarations.md` section 4.1): step 0 checks each request's `implied_condition`,
  whatever field or location it names, its units as an operating condition's (`request_unit_mismatch`), and
  keeps only the members its shape names; a value holding a member of the other kind of condition's shape
  breaks its shape (a `token` for a numeric condition, a `value`, `range` or `unit` for a token one:
  S2a-4's review, and the maintainer's ruling of 2026-10-18), and so does a member one slip from one; step 10
  applies one located at the read whose fact and token the field's specimen states, the section's facts merged
  with the field's (`RecordField.specimen`), filling a condition the record leaves unstated or does not hold,
  with the basis `implied`, a token a record's `basis` never holds (`form_invalid`, not `unknown_token`:
  S2a-4's review); two that disagree end the read there with `request_incomplete` for that condition and no
  `conditions`, values differing unless of one shape and holding the same token or the same numbers bit for
  bit (`0` and `-0` differ, as do a value and `[v, v]`). A result's `applied`, outside its JSON and its
  equality, holds the indexes of the implied conditions that filled a condition. A request with any other
  acceptance still raises `NotImplementedError`.
- The read's steps 11 to 13 for a constant, and its result (S2a-4; `read_side_contract.md` sections 2, 3 and
  6). Step 11 adds nothing to a constant's conditions; step 12 gives `stated_without_origin` (`unknown`) and
  the field's label and `mixed_conditions` for a derived value whose inputs' conditions differ; step 13 gives
  a constant's value under `want: value` and `want_mismatch` under any other `want` (`want: fit` on a field
  holding a fit record raises `NotImplementedError` until the fits and reference data suite). The result
  (`ReadResult`, with `FieldRead` and `ProvenanceSummary`) holds the members section 2 gives, each present as
  its item 6 says: the value with its unit, specimen facts, statistics block and provenance (the origin, the
  review as found or `not_checked`, a status object that breaks its shape among the latter (S2a-4's review),
  the source's key, a derived value's derivation with its `assumptions`), each the members the reader's
  version defines, read from the generated shapes, as stored and copied (the code design's rule 6), a
  statistics block held as the status object its row allows returned as one. `to_json` writes numbers as
  stored, `-0` included, and each count and index as an integer (rule 5). S2b-1 reads intervals and
  compositions, and S2b-2 evidence and the nominal (below).
- Step 7 over a field holding alternatives, as far as S4's decision 12 lets S2 go (`core/read.py`,
  `fields.alternatives_problems`): a list that breaks its shape is `form_invalid`, a member one slip from
  `alternatives` or a value field's beside it included; a fault of the request inside one alternative refuses
  the field where no alternative has a reason of its own; and two or more alternatives none of which has a
  reason of its own give `want_mismatch` where none has a form `want` can give, else `no_pick`, each in
  `alternative_values` by its stored index. S4a reads every other outcome with no pick and no overlay
  (below).
- Step 7 over a field holding alternatives, read with no pick and no overlay (S4a; `read_side_contract.md`
  section 3, step 7, `record_format.md` section 5; built ahead of S3's code, maintainer, 2026-10-19). Each
  alternative is read alone, as a field, by steps 8 to 13, the request's nominal applied at step 13 where it
  applies to the read. One whose conditions give `not_met` at step 10 is set aside; one refused at step 8 or
  9, or by a fault of the request, refuses the field; any other stays, a `not_met` of step 13
  (`want_mismatch`, `nominal_invalid`) waiting. The result is the first outcome that applies: where one
  refuses, or every one is set aside, `not_met` with every alternative's reasons, those that wait included;
  where one stays, its read, the nominal applied; where two or more stay and none has a form `want` can give,
  `not_met` (`want_mismatch`); otherwise `unknown` (`no_pick`), each one that stays in `alternative_values` by
  its stored index, and the first one's `unit`. Beside `want_mismatch` and `no_pick` each staying
  alternative's `unknown` reasons stand and its `not_met` ones wait; a set-aside one's are not reported. A
  reason found reading one alternative carries its index as `alternative` (`Reason.alternative`, written as an
  integer; a reason's identity is its code, condition and alternative), a fault of the request none
  (`reasons.tagged`). A result that rests on no single alternative holds no value, `conditions` or
  `assumption`, a `unit` only beside `alternative_values`, and at most the label `hash_not_checked`. The 21 S4
  arms that hold no pick, no overlay, no extrapolation and no table alternative run, with S4a's three `unit`
  arms, the third written with this step: three evidence alternatives, the first set aside by an implied
  condition, so that the `unit` is the first remaining one's, not the first stored; a table alternative still
  raises at step 8 until S3, and a pick or an overlay at step 0 until S4b and S4c. The reference model reads
  the same step from the text, written without the implementation's, and agrees with every case file it
  decides.
- The read's steps 8 and 13 for an interval and a composition (S2b-1; `record_format.md` section 6,
  `read_side_contract.md` section 6). Step 8 reads an interval's `lower` and `upper`, each a number or
  `{"status": "none"}`, at most one of them `none` and `lower` not above `upper`, numbers compared by value,
  and its `basis`; and a composition's `basis`, `sum_rule`, a `stated_sum` that is a number, and `components`:
  at least one, none twice, each `element:<symbol>` of IUPAC's 118 (any other symbol or kind of component is
  `unknown_token`) with a `fraction` from 0 to 1, and its own statistics block, where it has one, checked as a
  field's. Each rule broken is `form_invalid`; a withheld own member gives `withheld`; a composition's basis
  the row does not allow stays `form_not_registered`, its member unread (`core/fields.py`). Step 13 returns the
  form's own member under the `want` that gives it, `bounds` or `components`, as stored and never normalised:
  a `none` bound as a status object, never infinity, the stated sum where present, a component's statistics
  with its counts as integers; any other `want` is `want_mismatch` (`core/read.py`).
- The read's steps 8 and 13 for evidence (S2b-2; `record_format.md` section 4.3, `read_side_contract.md`
  sections 3 and 6). Step 8 reads evidence's own member: a non-empty list of test reports, never a status
  object; each report holding every member, its text members a string or a status object of any token, its
  `standard` a designation and a whole year, its provenance checked as a field's (origin, source,
  derivation); each report withheld whole, its provenance kept, or not at all (`form_invalid`). Every report
  withheld gives `withheld`; some, `entries_withheld` (`unknown`), the read going on. A registered condition
  under evidence is `form_invalid` where the row allows the form; a name the reader does not know gives
  `condition_unknown_name` at step 10 (`core/fields.py`). Step 13 returns the list under `want: evidence`,
  each report with its statuses and its provenance whole, the members the version defines at every depth,
  its review read as `provenance.md` section 2 item 6 reads every review; a result of evidence holds no
  statistics. A placeholder beside a status object in what a result returns (a provenance's `assistance`)
  comes back whole (`core/read.py`).
- The nominal (S2b-2; `declarations.md` section 4.1, `read_side_contract.md` sections 1, 2 and 6). Step 0
  checks every nominal's shape, whatever field or location it names: its `field` as a target's and its
  `value` a number, its `reason` and `basis` ignored, `params` named and ignored; two nominals naming one field
  are `request_incomplete` whatever else each holds. Step 13 applies the one located at the read's field and
  record alone to an interval under `want: value`: inside or on its bounds, compared exactly, it supplies the
  value and the `assumption` (`{"acceptance": "nominal", "value"}`) beside `want_mismatch`, which the
  `not_met` result carries; outside them it gives `nominal_invalid` in place of `want_mismatch`, and no value;
  under `want: bounds` it is unused. `ReadResult.applied` holds its index where it supplied the value. Under
  `no_pick` no nominal is applied, nor compared with the bounds, but one that applies lets an interval count
  as a form `want: value` can give, so two intervals give `no_pick` (`read.Nominal`,
  `conditions.located_at`); since S4a it applies to the one alternative left.
- Step 0 refuses an acceptance that is not an object, or of a kind a read does not take, a `waiver` among
  them, with `request_incomplete` alone (PR-310's GAPS G11 arm; S2a-3's review, I4). A pick, an overlay or an
  extrapolation still raises `NotImplementedError`, whatever else the request holds, until S3 and S4.
- `materica.core.slips`: the one-slip relation of `record_format.md` section 10, which the read and the
  name-overlap check share. A word made plural or singular must be a word: the empty string between two
  underscores is none.
- `Vocabulary.token_lists`, every token list of the vocabulary by its name, a fact's fixed members, a
  field's bases and where its label goes, and `STATUS_TOKENS`, the status tokens from the generated shapes
  (`core/vocabulary.py`). Every `claims` parameter of the core is typed by the suites, so that a misspelt
  suite name does not type-check.
- A quickstart (`docs/user_guide/quickstart.md`): it writes a record holding one of the water example's
  values, reads it to a `met` result, shows a refusal with its reasons, and reads the example's two density
  alternatives, to the one left at one temperature and to `no_pick` where both are met (S4a). It says plainly
  that this release reads constants, intervals, compositions and evidence, and alternatives with no pick, and
  not yet tables or picks (S3 and S4), and a test runs its code and compares every output it shows
  (`tests/examples/`). The README's documentation table links it and the examples.

### Changed
- CI's longest jobs run in parts of about equal time side by side (maintainer, 2026-10-20), so that a push waits
  for the longest part and not the longest job; what is checked is the same tests, profiles, example counts
  and Pythons. The `controls` job (the mutant searches and the audit controls) runs in four parts on Python 3.11
  and two on 3.15, the `tests` job in two parts on each Python, and the Hypothesis job's three longest shards,
  `agreement`, `relations` and `alternatives`, in two parts each, so 30 jobs on a push's head where there were 18. A new
  pytest option, `--partition I/N`, and for a Hypothesis shard `--shard NAME_IofN`, choose the I-th of N parts
  of the tests the other options select (`tests/partition.py`): the heaviest test left goes to the lightest
  part, by the seconds each long test took in a CI run (`tests/partition_weights.json`); a stale weight makes a
  part slower and loses no test. `tests/unit/test_ci_workflows.py` collects the tests of every part of every
  matrix and fails where a test is in none or in two, with a control for each; `tests/unit/test_partition.py`
  holds the assignment to a partition on random selections. The kill points of the mutant searches are checked
  in a `kill_points` job per Python that reads the reports of all that Python's `controls` parts together (no
  `--partial`), after counting them. The example databases of `agreement`, `relations` and `alternatives` start afresh
  under their parts' names.
- `CLAUDE.md` states the proportionality rule (maintainer, 2026-10-17) beside the review budget it was decided
  with: a finding that matters only where real data is very unlikely to reach gets a stated limit, not new
  machinery, and becomes a known anomaly if real data is found to reach it; reviews mark each finding by whether
  it can change a value or a refusal a consumer sees on data a real record could hold.
- The README and the site say first what OpenMaterica is for, in one line: material properties for biomedical
  simulation, each stored with the conditions it holds under, so a simulation can check that a value applies
  before it uses it. Both now give example uses (blood or plasma viscosity for a microrobot, a magnet grade's
  remanence, a phantom standing in for blood, biocompatibility evidence; and, for the sections after schema 0.1,
  photoacoustic imaging through layered tissue, ultrasound in a simulator built on USD and C-arm fluoroscopy of a
  device in a vessel), a list of what it is and is not (not a simulator: it computes no physics and ships no anatomy), and plain
  JSON and OpenUSD as its two main integration targets. What the specification defines but the Python package does not yet implement (the
  OpenUSD binding, scene documents, the build check, model parameter sets with check points) is labelled so,
  and the site's paragraph on materiomics leaves the front page (the architecture concept holds it).
- The pre-review script's trace test (`tests/unit/test_pre_review.py`, run where `MATERICA_TRACE_SELECTION=1`)
  no longer depends on the Python bytecode cache. With a warm `__pycache__` the import system reads a module's
  `.pyc`, which the trace ignores, and never opens its source; with a cold one it opens the source, so the test
  failed on a clean checkout, naming `tests/fuzz/__init__.py` and `tests/unit/test_fuzz_oracle.py`, and passed
  on CI, where the workers had compiled every module first. The traced run now gets an empty cache of its own
  (`PYTHONPYCACHEPREFIX`), so every import reads its source in the same way every time, and the trace's setup
  asserts it saw that source. The pair it named was a gap in the import graph, which did not take a module to
  import its parents: importing `tests.fuzz.field_oracle` runs `tests/fuzz/__init__.py`, yet only a test naming
  the package selected a change to that file. The pre-review script's graph now counts `import a.b.c` as an
  import of `a` and `a.b` too, so a change to a package's `__init__.py` selects the tests that import a module
  under it (`src/materica/__init__.py` now selects `tests/unit/test_slips.py`, and `scripts/__init__.py` the
  tests that import only `scripts.<module>`), and the hand-declared `TREE_READERS` row for
  `tests/fuzz/__init__.py` is no longer needed.
- `scripts/mutant_runs.py` refuses a patch that creates a regular file named like a directory `.gitignore`
  names with a trailing slash: `.pytest_cache`, `.hypothesis`, and any other such name (`build`, `dist`,
  `.tox`, `.mypy_cache`). `git check-ignore --no-index` matches a pattern such as `.pytest_cache/` to a
  directory only, so the request took the file (`touched ['.pytest_cache']`), and the mutant ran undecided
  with a reason the table did not name (pytest: "Not a directory", exit 1, no failure named); it could not
  give a kill (#46's re-check, H2). The request now asks git about each path as itself and as `path/`, which
  closes the whole class rather than the two names, and no file tracked in the repository is matched either
  way. `tests/unit/test_ci_workflows.py` adds both names to the refused patches, with a control that takes
  the second question out and takes the patch; the patch creating `src/materica/third.py` stays taken.
- The README's code-licence badge reads PyPI's licence metadata (`img.shields.io/pypi/l/openmaterica`) where it
  read GitHub's licence detection (`img.shields.io/github/license/...`). Shields.io draws the second through a
  pool of GitHub API tokens and, on 2026-10-17, drew an error, which GitHub's image proxy then kept for four
  hours; the first makes no GitHub request. Both name Apache-2.0; no licence file or declaration changed.
- The sibling distributions and the MCP server (maintainer, 2026-10-16), with the maintainer's rulings of
  2026-10-17 on their open points, written into the architecture draft (the decisions, sections 3.1, 3.2, 7.1,
  7.2, 8, 12.1, 13, 14 and 15) and the documentation plan (the components, sections 2, 3.5, 5.1, 7.1, 7.4, 10,
  12, 14, 15 and the appendices), with `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md` and this file's preamble.
  One repository holds every Python distribution, a uv workspace with tag-prefixed releases, and
  OpenMaterica's own families stay in it, in the import package `materica_families`. There is no
  `openmaterica-mcp`: the core's `[mcp]` extra brings the one server, part of the core's assessed wheel and
  never run at a consumer's build. It speaks over stdio only and loads tools by entry point from a closed list
  (the core and its two siblings), and no tool it loads makes a network request; a listed sibling that is
  missing or mismatched is skipped with a logged reason, and no sibling imports an MCP library. A sibling's
  MAJOR.MINOR is the core's it is built for, and it depends on that core minor alone, after 1.0 as before; a
  core minor is a release train; the core's `[authoring]` and `[families]` extras pin the matching minor with
  a range, and `[all]` brings both; a sibling refuses a core of another MAJOR.MINOR, and `python -m materica
  versions` checks them; an explainer release, first `openmaterica-families` 0.1.0, stands in for a sibling at
  each core minor before its first. Family entries go in `families/CHANGELOG.md`. Text only: none of it is
  built yet.
- The documentation plan (sections 1, 6.5, 8.1 and 15, and Appendix B) and `CONTRIBUTING.md` (constraint 12)
  say what checks the known-anomalies registry: `scripts/check_anomalies.py`, which stands in for MADDENING's
  validator, whose packaged command reads each component name as a Python name; MADDENING's validator accepts
  `materica_version` from MADDENING 0.4.0. They had said that CI checked the registry with MADDENING's
  validator, which no job did, and that the validator refused `materica_version`. Appendix B dates the items
  changed after its status date.
- `CLAUDE.md` states the maintainer's review budget (maintainer, 2026-10-17) where it said that the maintainer
  reviews every line of code in detail: the specification text and `changes.md`, the public API and the
  schemas, the rulings, and each pull request's description and open points are reviewed closely; the rest is
  sampled (tests, case files, generated files, and the source code that is neither the public API nor a
  schema), and the independent review and CI are the line-level check. A step's end with the maintainer's
  review is now a review of what the budget lists. `CONTRIBUTING.md` and the documentation plan made no such
  claim. The pull request template gains an Open points heading.
- The specification README's cap on a file's `binary32` tolerance in the table evaluation suite holds under each
  precision and side a broken evaluator claims (maintainer, 2026-10-19; `docs/specification/changes.md`): "under
  each precision and side it claims" now follows "by ten times that file's `binary32` tolerance" in "Case files".
  The suite's README and the reference evaluator's tests already read the cap so, and no figure changes: for each
  of the 24 broken evaluators the best file is the same under each claim. The clause that a difference no
  tolerance passes counts as beyond the cap is ratified as written, and the 13 files named beside no broken
  evaluator keep no cap.
- On Python 3.11 and 3.12, every test runs inside a function with a large frame (`in_a_large_frame`,
  `tests/conftest.py`), which removes about half of 3.11's extra time on the mutant searches and the audit
  controls, and all of 3.12's. CPython 3.11 and 3.12 keep the frames of running calls in chunks of 16 KiB and
  unmap a chunk as soon as the call that opened it returns, so a call repeated across a chunk's edge maps and
  unmaps a chunk at every call (CPython gh-142183: 3.13 and 3.14, by a backport of March 2026, and 3.15 keep a
  spare chunk, so from 3.13 on the large frame is not applied; 3.11 and 3.12 take security fixes only).
  Hypothesis's draws do that: the controls job's tests (`--property-controls only`) made 70.8 million minor page
  faults on 3.11 and spent 205 s of CPU in the kernel, against 1.4 million and 4.8 s on 3.15. The large frame is
  given a chunk of its own, 1 MiB, and the test's frames run in the half it leaves, meeting no edge. On 8 local
  workers, one to a performance core (2026-10-20; local figures, CI's share is measured on the pull request's
  run), the CPU time of those tests went from 1,896 s to 1,632 s on 3.11 and, on part of them (the result's
  mutant searches and the audit controls), 3.12 went from 1,400 s to 1,145 s, level with 3.13's 1,157 s; 3.11's
  excess over 3.15 went from 1.33x to 1.15x. Every kill point, outcome and feature-audit count was the same with
  it and without, on 3.11 and on 3.15 (`scripts/gen_kill_counts.py --against` on each run, and the counts given
  to each of the 949 tests' audits compared). The rest of 3.11's excess is its interpreter, spread over
  Hypothesis's own functions. On CI 3.11 took about 1.9 times 3.15's time; how much of that this removes there is
  known only once CI has run it. Explain-phase tracing, which runs under `sys.settrace` before 3.12, was the
  cause first suspected and is not one: in the result's mutant searches and the audit controls it traced none of
  about 114,000 test cases, and forcing it off left their time within its run-to-run spread.
  `tests/unit/test_frame_room.py` holds every test on 3.11 and 3.12 to the large frame and shows the chunk edge it
  removes, and on 3.13 and later asserts that no test runs in it.

### Schema
- `read_request.json`'s acceptances, a JSON object each until now, take the shapes of the kinds a read takes
  (S2b-2; `read_side_contract.md` section 1, `declarations.md` section 4.1): the members every acceptance
  holds (its `field`, its location, `record`, `region` or `interval`, and its `reason` and `basis`, the last
  three any JSON, since a read checks no location's shape and ignores the other two), a nominal's `value`
  (and `params`), and an implied condition's `fact`, `token` and `implies`. A pick's, an overlay's and an
  extrapolation's own members are written with the steps that apply them (S3, S4): an extrapolation's
  `method` would be a third meaning of the name, which the name-overlap allowlist holds at two.
- `read_result.json`'s members, placeholders until now, typed from the writer schema's `$defs` and the
  vocabulary (S2a-4): the value by `want` (a number, an interval, a composition, a list of test reports, a
  form's member as stored, and the operations' content hash and listing), `alternative_values` and each entry,
  the unit, the condition entry (`name`, `status`, `record`, `operating`: the record's entry, its status
  object or an implied value with basis `implied`), the specimen, the statistics block, the provenance a read
  returns (its review as found, other members as the record holds them), the labels and a nominal's
  `assumption` (an extrapolation's members wait for S3). `case.json`'s compared result takes the same shapes,
  and every case file's expected answer validates against them; `tests/spec_sync/test_schemas.py` holds the
  condition entry's record to every condition shape and the returned review to the writer's members. The
  specimen and a derivation are `result_` twins of the writer's definitions, closed alike but without the
  patterns of members a read checks only as strings (an anatomical site's UBERON identifier, a derivation
  input's pinned record), so that a correct result of a record the writer refuses validates (S2a-4's review);
  `test_schemas.py` holds each twin to the writer's, and every result the implementation gives a case file it
  runs validates. Two names take a meaning more, allowed with their reasons and safeguards
  (`tests/spec_sync/name_overlaps.json`): `basis` (`implied`, in a result alone) and `source` (a result
  returns the key alone).
- The value fields of schema 0.1's writer schema, so far open placeholders (S2a-1): a value field of each of
  the eight forms, or alternatives; the constant, interval, composition and evidence forms in full; conditions
  with `plus_minus` and `set_or_measured`, each token condition bound to its own row's tokens; the specimen
  facts with `supply_form` and `lot`, a fact's fixed unit `s`, `mimics`'s stated basis and the UBERON
  identifier's pattern taken from the text, and a disease or treatment state's `text` present exactly for
  `diseased` and `treated`; the statistics block and its uncertainties, the provenance object and `label`; a
  status object in exactly the members `provenance.md` section 1 item 5 lists, a placeholder beside one taking
  no other; and the rules across objects of `provenance.md` sections 2, 3 and 7 (an extraction's derivation,
  formulation or fit record, a pooled statistic's search, a withheld value's or evidence entry's recipe). The
  table, power-law, parameter-set and reference-data forms' own members, the fit record, and the provenance
  members whose own members the text does not yet name stay placeholders; the schema's description names each
  such place. Members a read does not check carry `x-materica-write-only` (`record.writer.json`).
- The writer binds each name to its row (maintainer, 2026-10-15): each section's `fields` is closed to the
  names `record_format.md` section 4.1 registers for it, and an overlay's `replaces` to the registered fields;
  each field, and each of its alternatives, takes only its row's forms, the bases its row allows a
  composition, its registered unit and its row's label or none; a numeric condition's `unit`, and its
  `plus_minus` entries', hold its registered unit. The vocabulary generates the bindings from the rows, and
  the writer applies each by `allOf`, holding no list of its own; the reader schema and the typed shapes leave
  them out.
- The reader schema holds a value field's and a section specimen's shapes in `$defs`, as step 8 checks them,
  applied from nowhere, without the rules a read cannot apply (one testing, or requiring only, a member it
  does not check); the typed shapes gain a TypedDict per form and per shape, every number typed `float` as the
  reader gives it (`materica.shapes`).
- The vocabulary gains every token S2 reads, generated from the specification: the reason table's steps, the
  bases a field's row allows a form, the conditions another condition requires, the element symbols, each
  token condition's tokens and each specimen fact's fixed values as enumerations, and the form, interval,
  composition, statistics, uncertainty, provenance and result-label tokens, four of them in new files
  (`forms.json`, `statistics.json`, `provenance.json`, `labels.json`); the pattern of an identifier a fact's
  row writes (`"UBERON:<digits>"`); and the bindings of the rows (`fields.json`'s `sections`, `replaces` and
  one per field, `conditions.json`'s `units`). The generator reads every code span of a cell or stops, and
  stops on a name listed twice in a table, an identifier of another form, and a row a binding cannot state.
- `provenance.md` section 6.2: a disease or treatment state's `text` names the disease or the treatment and is
  present exactly when its token is `diseased` or `treated` (maintainer, 2026-10-15). Three plain-read inputs
  that held a text beside `normal` lose it, rehashed, and the PR-316 case files that pin them are repinned.
- Two defaults from S2a-2's review, approved (maintainer, 2026-10-15; `docs/specification/changes.md`): step
  9 of a read compares a specimen fact's `unit` with the unit its row fixes, wherever step 8 checks the fact,
  so that another unit, or a status object with any token, gives `unit_mismatch`, and step 8 checks it only as
  a string or a status object (`read_side_contract.md` section 3, step 9; three PR-037 arms, for S2a-3); and
  `mimics`, whose row fixes its basis to `stated`, takes no `inferred_from` (`provenance.md` section 6.2).
- The writer binds a row's label to the forms its Label cell names (`record_format.md` section 4.1; PR #37's
  review): where a field holds its row's label, its form is a constant, or a table where the cell names one,
  and that table's `axis` is not the cell's condition, so that the writer no longer takes a viscosity interval
  carrying the Newtonian label, which every reader refuses. `gen_vocabulary.py` writes it from the Label cell
  into each labelled field's binding (`fields.json`), and stops on a cell naming a form its row does not
  allow.
- The writer binds a specimen fact's unit to the one its row fixes (`"s"`), a status object there refused, as
  a numeric condition's unit is bound, so that no record step 9 refuses is written; a fact whose unit the
  source does not give is written as a status object (maintainer, 2026-10-15). The vocabulary generates the
  binding from the rows (`specimen_facts.json`'s `units`, each referring to its row's unit), and the writer's
  `specimen` applies it by `allOf`, a fact's own `unit` being a unit as anywhere else; the reader schema and
  the typed shapes leave the binding out. Every other unit the writer takes was already bound to
  its registered unit wherever the row fixes one (a field's, a condition's, a `plus_minus` entry's, none on a
  token condition); a table's `axis_unit` waits for S3, which writes the table's shape.
- A default from S2a-3's review, kept (maintainer, 2026-10-16; `docs/specification/changes.md`): two values
  implied for one condition differ unless they are of one shape and hold the same token or the same numbers
  bit for bit, so `0` and `-0` differ, as a value and `[v, v]` do, and which of two that agree fills it never
  depends on the order of the acceptances (`read_side_contract.md` section 1).
- The maintainer's ruling on S2a-4's review (2026-10-18; `docs/specification/changes.md`):
  `read_side_contract.md` section 1 now says that an implied condition breaks its shape (`request_incomplete`,
  with that condition) where `implies` gives a numeric condition a `token`, or a token condition a `value`,
  `range` or `unit`, whatever that member holds. The reader has refused both since S2a-4's review; the second
  rested on the shapes `declarations.md` section 4.1 names, and reversed S2a-3's reading of a `unit` beside a
  token, which step 0 ignored. One PR-330 case for each direction comes with it.
- The maintainer's ruling on `unit` under `no_pick` (2026-10-19; `docs/specification/changes.md`):
  `read_side_contract.md` section 2's `unit` row now says that under `no_pick` the result's `unit` is the
  first remaining alternative's, in stored order, so that where the remaining alternatives store `unit`
  differently, which only a unit registered as a status object allows, another alternative's `reason` is not
  returned. The reader and the reference model take the first; the reader raised `NotImplementedError` there
  until now. Two PR-013 cases come with it, run with S4a: two evidence alternatives whose units hold different
  `reason`s, or the second's alone a `reason`. The model's seeded fault that read it so until now
  (`units_stored_differently_read_as_no_pick`) is replaced by one that takes the last remaining alternative's
  unit, which both cases kill.
  The rule is interim: the maintainer has ruled that it holds until S3b-2, which replaces it with each remaining
  alternative's `unit` in its `alternative_values` entry.
- `provenance.md` section 6.2 item 1 states the writer's rule for a specimen fact's unit (maintainer,
  2026-10-15): a fact whose row fixes its unit holds that unit, and one whose unit the source does not give is
  written as a status object in place of the fact.
- `fields.json` gives, for a field whose Label cell lets its label go on a table, the condition the table's
  axis must not be (`label_not_on_axis`); the generator reads the cell's prose in its two forms, and any other
  stops it.
- `PR-032.interval_basis_unknown`'s input holds a statistics block of a valid basis, so that the arm tests the
  interval's basis alone; its pin follows.
- Members that held a name with a second meaning, and no safeguard to keep the two apart, are renamed before
  0.1.0 (maintainer, 2026-10-15; `docs/specification/changes.md`): a scene cylinder's `axis` to `direction`;
  a family conversion's `from` and `to` to `from_measure` and `to_measure`; an admissibility constraint's
  `kind` to `rule`; a declared model's `parameters` to `consumer_parameters`, and a declared distribution's
  and a marginal's to `distribution_parameters`; a witness datum's `reference_data` to
  `reference_data_name`; and a multivariate normal's per-parameter `space`, with a fit's
  `covariance_space.space`, to `parameter_spaces`. No schema held any of them yet; the one case file that
  did, a declared distribution in a request (PR-330), follows.
- `case.json` takes the `transform_draws` operation of a sampling case, its draws' shape not yet specified.
- `scripts/gen_reader_schema.py` takes a member marked `x-materica-write-only` with `{"unless": {<member>:
  <token>, ...}}` in place of `true`: one a read checks only where each named member of its object, one a read
  checks, holds that token. The reader `$defs` keep its shape, and whether its object requires it, in a
  conjunct under that condition, and elsewhere treat it as write-only: a rule in the `then` of exactly that
  condition takes it as checked, any other rule as unchecked. A mark of another form stops the generator.
- The reader `$defs` check a provenance object's `derivation` for origin `derived` alone, as `provenance.md`
  section 2 item 6 and step 8 do. They applied its shape wherever a `derivation` stood, so a reader validating
  a field with them refused one the text reads: a constant of origin `measured_by_contributor`, say, whose
  derivation, there because its extraction's method is `derivation`, holds no `inputs` (found by S2a-3's fuzz
  target 4 and its review). The writer marks `derivation` write-only `unless` its origin is `derived`, and
  still holds it to its shape wherever it stands (`provenance.md` sections 3 and 5, RC-035); the typed shapes
  are unchanged. The value-field check holds the marks of this form to the text, and the unknown-member positions
  walk into such a member, as before.

### Data
- Three example records in `examples/records/`, in the namespace `example`, each cited: `example/water`
  (density and dynamic viscosity at 293.15 K and 310.15 K and 0.101325 MPa, evaluated from IAPWS R6-95(2018)
  and R12-08), `example/ndfeb_n45` (the remanence of sintered NdFeB grade N45, 1.32 to 1.37 T, a vendor's
  grade limits) and `example/human_plasma` (dynamic viscosity at 37 °C, 1.33 mPa·s, from
  Marcinkowska-Gapinska and Nawrocka-Bogusz 2013, with the specimen facts the paper states). They are
  examples, not reviewed library data: not yet fully human-reviewed, and they may change in a later commit
  (maintainer, 2026-10-17 and 2026-10-18). They stay in the repository and are not in the wheel
  (`examples/README.md`). Tests hold each to the schemas, its hash and the record checks a reader of this
  release can make without `materica check` (identifier and version, required conditions, the label, every
  review `not_checked`; RC-058 is not among them), each number to its source's, the note to every place the
  examples are documented, and each read to what those documents say this release gives
  (`tests/examples/`).

### Verification
- The table evaluator against every table evaluation case: each number and `in_range` at 1e-12 relative, and
  each refusal, a broken evaluator failing each, and the edges of the text by example; and log-log values
  halfway between two doubles, rounded to even (`y = x^2` and `y = x^3` in the normal range and among
  subnormals, `y = x^2` over [1, 3], `y = 3 x^(3/2)` and `y = 1 / x` among the least subnormals), with a
  control in which the exact decision is switched off, and the bounds of the other values holding the exact
  value where it is known (`tests/unit/test_evaluate.py`).
- The S3 design's HP17 to HP19 for the table evaluator, against an oracle written from the text, exact in
  fractions, and for a log-log value in decimal at 100 digits under an error bound, deciding over prime
  factors whether a value near a halfway point is that point, over drawn tables of every magnitude,
  subnormals and `-0` included, the least subnormals following `y = c / x` so that reads fall halfway between
  two doubles, a `source_range` within one interval among them, and operating values at every place table
  item 3 tells apart: agreement bit for bit, knots as stored, bracketing and monotonicity, each with its
  feature audit and an audit control, and eighteen mutants, each killed at the assertion it names
  (`tests/property/test_evaluate_*.py`, in the `json` shard). The oracle's own controls are the table
  evaluation cases and the ties; the generator's self-check has a table for each rule step 8 refuses.
- Checks that the value-field shapes match the specification's member tables, status table and examples, that
  the members marked write-only are those step 8 does not check, that each token condition and fact binds its
  row's list and a fact's identifier the pattern of its row's form, that a member a row gives as present
  exactly with some tokens is so in the writer, that each rule across objects refuses a field without its
  member, that each binding of the rows is applied where it belongs and holds what the rows give, a row added
  to the text being taken by the unchanged writer, and that the writer's description names exactly the places
  it leaves open (`tests/spec_sync/test_value_fields.py`).
- A check that the names valid at one place, the members an `allOf` joins included, stay more than one slip
  apart and that no name has two meanings, over the schemas, the vocabulary and the specification, with an
  allowlist of the overlaps judged intended, each with its reason and a safeguard, a quote that must stay in
  its document or a test that refuses each meaning at the others' places, or with none, the reason and the
  maintainer's flag: approved with none possible; approved with the safeguard deferred to the shapes that give
  the name a place, and due, failing the check, once a schema gives it one (`ranges`); or pending while a
  rename is proposed, failing once the maintainer has answered, as the maintainer has for the eight proposed
  with S2a-1 (`tests/spec_sync/test_name_overlaps.py`, `test_name_overlap_safeguards.py`).
- A check that each reason code is given only at the steps the reason table names, against the text (a step's
  item and the passages it hands its checks to, and step 6 for an overlay what steps 1 to 5 give), and against
  the code of steps 0 to 5 in every module of the core, statically and traced through every read case file
  (`tests/spec_sync/test_reason_steps.py`).
- Hypothesis properties of the writer schema: it takes every value field the specification allows and every
  registered field in its place, and refuses each of 167 faults the text names, in ten families, built from
  the text and the vocabulary's rows, never from the schema or its bindings; 92 mutants of the schema and of
  the bindings it applies, the S2a-1 review's 31 among them, each killed at the assertion it names
  (`tests/property/test_writer_properties.py`, `test_writer_mutants.py`), in a third CI shard, `writer`.
- The feature audit holds a feature drawn alike as each example's first choice, as a refusal property draws
  its fault, to a floor its draw gives at the `ci` profile: Hypothesis shows one draw in up to eight examples,
  so the floor counts one draw in every eight examples, each draw shown in five, and is the count the feature
  falls below with a probability of at most 1e-6, and never below 10. A family of more than 15 faults is
  drawn in parts, a property each. Each fault is drawn by `st.sampled_from`, no longer by a drawn seed, which
  drew some faults up to 1.27 times as often as others (`tests/property/audits.py`).
- The writer schema's acceptance properties declare each feature by the chance that a draw shows it, its share
  measured at `ci` (`@pytest.mark.chances`): at `ci` each is held to the draw floor of its chance, at `dev` to
  that floor where it is at least 10, and at `deep` to a third of its chance. Their least shares assumed
  independent examples, which Hypothesis's clusters are not: from the measured clusters, they failed a run
  with a probability of about 1.5e-6 at `ci` and 1e-3 at `dev`, against about 3e-10 and 7e-7 now. The
  audit's comment no longer says 1e-9: a least share at its gate fails about one run in a hundred
  (`tests/property/audits.py`).
- The json and records shards' properties declare by its chance, measured at `ci`, each feature whose least
  share failed a correct run with a probability above 1e-6 at `ci` or 1e-3 at `dev`, computed from the
  clusters measured on each property: 44 features of 13 properties. Their least shares failed a run of the two
  shards with a probability of about 7e-3 at `ci` (negative zero in RFC 8785's values, about one run in 450,
  and 14 of HP3's regions, one in 200) and 2e-2 at `dev` (`long` in the versions' order failed 16 of 2,000
  runs), against about 2e-6 and 5e-4 now, from the least shares kept. RFC 8785's property draws names across
  the surrogate range and negative zero more often, and HP3 runs in two parts, a property each, its first
  fault's region drawn among the part's before the record, so that each feature has a floor at `ci`; the
  mutant searches draw as before. For each such property a control runs it at `ci`'s examples with a
  generator that stops producing one feature: its audit fails on that feature alone
  (`tests/unit/test_audit_controls.py`).
- A check that each member the schemas declare whole admits the float the reader gives
  (`tests/unit/test_shapes.py`).
- The tests of the repository scripts make their throwaway git repositories with every `GIT_` variable
  removed. Git exports `GIT_DIR` to the commands it runs, `git rebase --exec` among them, so the suite run
  that way re-initialised the outer repository, setting `core.bare` in its shared config, and committed onto
  its HEAD (`tests/unit/throwaway_git.py`, `test_throwaway_git.py`).
- The throwaway git repositories run no automatic maintenance. From git 2.54 (CI's runners carry 2.55), the
  maintenance a commit starts repacks in the background once about 256 objects are loose, and its
  `prune-packed` removes each emptied directory of `.git/objects`. The two gate tests that make 260 commits
  meet it (at git 2.55, the site commits' loop in 40 of 40 runs, the empty commits' in 7 of 40), and they
  failed twice in at most about 1,050 CI jobs of the whole suite, when that removal fell between git making a
  directory for the test's next object and writing the object there: "unable to create temporary file: No such
  file or directory". With 3 ms held at that point in the tests' own git commands, at git 2.55, the two tests
  failed 7 of 80 runs, each with one of CI's two messages, and passed 80 of 80 with this change; in a copy of
  their loop, a repack forced after every commit failed 24 of 24 runs in the background and none of 24 run
  before the commit returned. A test reads a commit's trace for the start of maintenance, with a control that
  finds it once the setting is unset (`tests/unit/throwaway_git.py`, `test_throwaway_git.py`).
- T1 (S2a-2): step 8 against the writer schema, with each field's binding to its row, and the generated reader
  `$defs`, on every value field of the conformance inputs and on one-fault variants of five full fields and of
  one field of each row and form, drawn by the writer's strategies: what the writer accepts step 8 accepts,
  what step 8 refuses as `form_invalid` the reader refuses, and the converse. Where a form's own member waits
  for S2b or S3, step 8's verdict is the case files' expected reasons, so for those fields T1 holds the data,
  not step 8. The exceptions are grouped by kind, each kind with its reason, a mark its refusals must show,
  and the case files whose read field breaks the relation (12 for the first, 48 for the second), computed
  from the generated files as the test runs, an unlisted, stale or misplaced one failing it; the shortcut of
  validating a field against its form's definition is checked on every example; and the token lists step 8
  knows by member name are held to the writer's (`tests/spec_sync/test_t1.py`).
- Hypothesis properties of step 8, the S2 design's HP3 and HP5: one fault of a 154-fault catalogue in 21
  regions written from the text (the derivation, `source` and each value step 8 checks among them, and slips
  that a reader ignoring slips cannot pass) gives exactly the codes its rule gives, two faults in two parts
  give both, and members the reader does not know never change the outcome; a third law holds a label on a
  table to the Label column; 47 mutants of step 8 each killed at both sizes, 21 of them at the faults they
  name, the eleven rules S2a-2's review found untested among them
  (`tests/property/test_value_field_properties.py` in the records shard, `test_value_field_mutants.py` in a
  fourth CI shard, `step8_mutants`).
- Step 8's oracles read status objects from `provenance.md` section 1's table, never from step 8's own status
  rows, which a check compares with it (`tests/spec_sync/status_rows.py`, `test_status_rows.py`).
- A property of the one-slip relation against a neighbour generator written from section 10, the oracle the
  read and the name-overlap check do not share, with 12 mutants (`tests/property/test_slip_properties.py`).
- A table of every position in a material record and a read request where a member the reader does not know
  is ignored or refused, held to the text, the schemas (every object a read reaches, and every member of one
  that may hold a status object, has a row, or a deferred row naming the piece that will read it), the hosts'
  objects and the read (`tests/spec_sync/unknown_member_positions.json`, `test_unknown_member_positions.py`).
- A fourth fuzz target, raw bytes into step 8, with a fault seeded for CI's control behind two changes to one
  seed, no seed holding two of its three parts, and an oracle that sees a refusal step 8 misses, T1's third
  relation, shown failing in the suite (`tests/fuzz/read_field_bytes.py`, `field_oracle.py`). CI's fuzz job
  gives that control 600 s, and no longer replays the mutant tables.
- 24 case files that end at step 0 or 8 on checks S2a-2 builds are run at S2a-2, two of them since its fix
  round in place of two whose field is a form its row allows; 579 case files pass, and 298 wait for a later
  step (`tests/spec_sync/case_steps.json`).
- S2a-3's 58 case files run and pass: 637 of 1260 case files pass, 623 wait for later steps.
- S2a-4's 166 case files run and pass: 803 of 1260 case files pass, 457 wait for later steps. Two of them are
  arms S4's decision 12 gives S2a-4, mapped to S4 until S2a-4's review (`PR-044.entry_holds_alternatives`,
  `PR-336.want_mismatch_over_alternatives_no_hs`). Two more end at step 0, one for each direction of the
  maintainer's token ruling (`PR-330.implied_token_for_numeric_condition`,
  `PR-330.implied_unit_for_token_condition`); they kill the reference model's two faults that read open point
  1's record half as the implementation does, by the implied half each breaks too. The reason-step check gives
  steps 11 to 13 their codes and loses its sets of codes no case returned: step 10's `unknown` codes, and step
  7's `want_mismatch`, each now returned.
- S2b-1's 54 case files run and pass: 857 of 1279 case files pass, 422 wait for later steps. Five broken
  implementations show the runner fails on them: bounds without their basis, an upper `none` read as the
  largest double, components normalised, bounds out of order and a component taken twice. PR-013's interval
  beside a constant under `want: components` returns step 7's `want_mismatch` too. 19 of the 54 came with
  PR #37's review, each killing a fault of the read that every other case let through: an interval's
  `stated_bound` and `proxy_range`, which a statistics block's `basis` does not hold, and a block's
  `reported_sd` in an interval; an interval's `basis`, a composition's `basis` or `sum_rule` and a component's
  `fraction` missing; a withheld interval and composition, one beside an unknown member, one beside a bound; a
  component's statistics withheld; a sum rule and a component of another member's tokens; a broken form its
  row does not allow; a component repeated after another; an unknown status token in a bound; and a slip of
  the field's `value` inside an interval.
- S4a's 24 case files run and pass: 945 of 1295 case files pass, 350 wait for S3 and S4's later pieces. 21
  were written with S4's text; three, the arms of `unit` under `no_pick`, come with S4a. Seven broken
  implementations of step 7 show the runner fails on them: a refusal set aside; the set-aside alternatives'
  reasons beside the one left; the one left's reasons without their index; a fault of the request given an
  index; the waiting reasons dropped from a refusal; an index counted among the alternatives that stay; and
  the first stored alternative's unit under `no_pick`. The reference model agrees with all 24, and its step 7
  has 16 seeded faults, each killed by a case file. The unknown-member positions read every position at a
  field's place inside an alternative too, and an alternative's own position gets its verdict (R77).
- S4a's properties (`tests/property/test_alternatives_properties.py`, a shard of their own, `alternatives`),
  over draws that take one of step 7's five outcomes first and build the alternatives that give it, each by a
  way drawn for its standing (`alternatives_strategies.py`): HP27, the read against an oracle written from
  step 7's text that composes the reads of each alternative alone, the drawn outcome asserted to be the
  oracle's; HP28, reordering the stored alternatives moves only their indexes and a field wrapped as its only
  alternative reads as the field (the fail-closed spike's P6 and P5); HP29, an alternative set aside, added at
  any stored index, changes no status, and two that stay never give `met` (N7r and S3). 19 mutants of step 7,
  each killed within the `ci` profile's examples at both sizes at the assertion it names, five by searches
  planned where their fault shows (`test_alternatives_mutants.py`); an audit control stops drawing `no_pick`.
  HP12 draws the same alternatives, its audit holds those draws to their floor, which a second control stops,
  and a planned search of them kills the five model faults one case file alone kills. HP1's and fuzz target
  4's reason identity take the `alternative`. The kill points join the generated counts
  (`tests/property/kill_points.json`), and two searches the margin guard named are planned: the mutant
  `the_last_staying_unit` (the 495th and 732nd example drawn whole, the 52nd and 80th among evidence under
  `no_pick`), and HP12's `upper_none_as_infinity`, which S4a's draws moved from the 177th and 29th to the
  503rd and 93rd (the 7th and 34th among intervals under `want: bounds`). Each planned search of both groups
  is held to its check on the core as it is, which it must pass.
- Fuzz target 4's oracle, the reference model, decides step 7 over alternatives with no pick and no overlay;
  `MATERICA_FUZZ_SEEDED_FAULT=alternatives` seeds a control in step 7 that answers wrongly rather than raises,
  which only the oracle finds and no seed holds. Fuzz target 3 drives HP27 to HP29.
- S2b-2's 64 case files run and pass: 921 of 1292 case files pass, 371 wait for S3 and S4. Eleven broken
  implementations show the runner fails on them: every report withheld read as some, and some as every; a
  report withheld in part taken; a registered condition under evidence taken; a report's provenance cut to a
  result's; a nominal applied outside its bounds, or wherever it is located; a nominal's value dropped from a
  `not_met` result; two nominals for one field taken; a waiver ignored; and a nominal compared with the bounds
  under `no_pick`. The reason-step check finds `entries_withheld` and `nominal_invalid` returned. 13 of the 64
  came with S2b-2's review, each killing a fault of the read that every other case let through: a list whose
  first report is withheld; a report's member holding `none` or `not_checked`, or a status token the reader
  does not know; `standard` as a status object beside a member its shape does not define, and a `standard`
  without its `designation`; a registered condition held as a status object under evidence; a withheld report
  whose marker holds a member beside its status; a slip of `provenance` in a report; a report's review of an
  unknown status; and a nominal on an interval's lower bound, inside one with no lower bound, and under
  `want: components`.
- Evidence and the nominal in the checks of steps 0 and 8 (S2b-2): T1 holds step 8 itself on evidence, its
  bases gaining a full evidence field and one every report of which is withheld; the unknown-member position
  D03 has its verdicts, R60 to R76 (an evidence field, a report and its standard, a report's provenance
  mirroring the field's), and D06 is narrowed to a pick, an overlay and an extrapolation, a nominal read at
  Q15 and Q16; a nominal's and an implied condition's members, in `read_request.json` and in the read, are
  held to the text; the reference model counts a report that is not an object as not withheld, and reads a
  report's provenance at every depth.
- The properties over evidence and the nominal (S2b-2). Step 8's: HP3's catalogue gains four regions of
  evidence, 36 faults with their near misses, in a fourth part; HP5 adds its members in evidence's reports,
  `in_a_report` declared. The result's: HP1, HP2 and HP11 draw an interval's read under a nominal as a kind of
  its own, five ways (inside its bounds, on one, one double outside, under `want: bounds`, located
  elsewhere), HP2 holding `value`, `assumption`, `nominal_invalid` and `applied` to an oracle of its own;
  HP6 holds evidence as stored and, in a property of its own, a nominal's value and assumption; HP4, HP6 and
  HP12 draw evidence, as often as an interval; HP12 draws nominals in its values, over alternatives and in
  step 0's catalogue (eight faults and near misses). Ten mutants of step 8 and one of HP5, eleven of the
  result's, one of HP4's, and seven faults of the model for HP12, which no read could show before, each
  killed at both sizes; five audit controls. HP12 lists no divergence for evidence or an acceptance any
  more. Fuzz target 4 reads evidence, holding it to the reader `$defs`, steps 9 and 10's oracle and the
  model; its "not yet" forms are a table and alternatives beyond decision 12.
- Intervals and compositions in the checks of step 8 (S2b-1): T1 holds step 8 itself on both, its bases
  gaining a full interval and composition (`tests/property/full_fields.py`'s `full_forms`), and the 21
  conformance examples of evidence alone keep their case files' verdict; the writer strategies give a row's
  label only where section 4.1's Label column puts it, a constant or a table off the cell's axis, which T1's
  drawn intervals had broken once step 8 read them, and the binding family two faults that put it elsewhere,
  on an interval and on a table on the cell's axis, which the writer now refuses (below); and the
  unknown-member positions D01 and D02 have their verdicts, R45 to R59, each read in a host of its form (a
  position may name the `form` it applies to).
- The properties over intervals and compositions (S2b-1). Step 8's: a field of each form drawn, a constant as
  often as the other two together; HP3's catalogue gains five regions of an own member, 48 faults among them
  the cross-member rules no schema states and their near misses, in a third part with its regions and forms
  declared by their chances, measured over 48 runs at `ci`; HP5 adds its members inside lists and own
  members, its least shares lowered where 48 runs showed them failing a `ci` run more often than 1e-6. The
  result's HP1, HP2 and HP6, HP4 and HP12 draw each form, HP6 holding an interval's bounds and a composition
  as stored, and HP1, HP2 and HP11 a met read of an interval or a composition under its own `want` as a kind
  of its own; HP4's audit holds it to the forms; HP12's known divergence for a form not built yet shrinks to
  evidence. 19 mutants of step 8 planned at their faults and one of HP5, six of the result's (the S2 design's
  `upper: none` read as infinity among them), two of HP4's, five of the implementation and two of the model
  for HP12, each killed at both sizes, HP1's at the reason table's assertion, and six audit controls for the
  new features. Fuzz target 4 holds an interval and a composition to the reader `$defs`, steps 9 and 10's
  oracle and the model, under the `want` its form gives; target 3 takes HP3's third part; and
  `MATERICA_FUZZ_SEEDED_FAULT=composition` seeds the S2 design's control, a composition whose `components`
  is empty, which target 4 finds at once and target 3 has not (`tests/fuzz/README.md`).
- The result's properties (`tests/property/test_result_properties.py`, in the `conditions` shard): HP1,
  totality and the reason table; HP2, the status law and the members item 6 gives; HP6, what a read returns
  as stored, by the generated shapes, sharing nothing; and HP11, the hash suite's label exactly where a read
  reached step 4. They draw reads that end at each step S2 builds, the kind first, and HP6's draws a `-0`
  value, each way a review reads and an unknown member, each by its chance. 17 mutants, each killed at both
  sizes within the `ci` profile's examples (`test_result_mutants.py`); two audit controls. Fuzz target 4
  holds every result to HP1 and HP2 (`field_oracle.check_result_laws`, shown failing on each law broken).
- HP12, the read agrees with the test-only reference model (`tests/property/test_model_properties.py`, in a
  `relations` shard of its own): given the same sources, request text and claims, the two results are equal
  as section 2 compares results, or both refuse to decide; five parts draw reads across every step S2 builds,
  two faults of one step among them (the design's B5), a catalogue of 52 faults of step 0, and the rules no
  case file pins. Its known divergences are listed by kind with their reasons and held exactly: three steps
  the implementation has not built that the model decides (an overlay as the target, a form S2b reads, an
  acceptance other than an implied condition), and one open point's record half (a condition holding a member
  of the other kind's shape) the implementation reads otherwise than the model's fail-closed choice, for the
  maintainer. 23 mutants of the implementation (a step that stops at
  its first fault at steps 0, 8, 9 and 10, and the design's mutants of HP1 to HP11 a result shows) and 18 of
  the model (its survivors of the cases and the faults one case file alone kills), each killed at both sizes;
  7 of the model's listed with the reason no read S2 builds shows them; controls of the check itself.
- HP4, a fault in another field or section's specimen never changes a read, and one in its own section's
  refuses it; HP10, a read's sources and request written in another byte form give its result
  (`test_invariance_properties.py`): six mutants, the design's two among them.
- Information monotonicity, the fail-closed spike's relations S2's forms reach (N1r, N2, N3r, N4, N5r, N6,
  N8, P1 to P4, S1, S2, S5), each a property restricted as the spike's limits say, on worlds drawn on the
  spike's grids, the rare triggers of its faults built in as drawn ways, each relation holding in a declared
  least share (`test_monotonicity_properties.py`): 18 mutants, the spike's that S2's forms reach and new ones,
  and the unrestricted twins N1 and N3 shown failing on the core.
- Fuzz target 4 holds each read under `want: value` to the reference model, as HP12 does, which sees a
  refusal step 8 gives wrongly (S2a-2's review, L3); it found a statistics status object returned as an empty
  block (fixed) and four readings of the model the text does not take (fixed, each seeded). The record target
  drives HP1, HP2, HP4, HP6, HP10, HP11 and HP12, and the control's replay runs HP12's and HP10's modules too.
- The result's draws reach step 10's `unknown` reasons and two reasons a read more often: the HP1 mutant that
  drops `condition_unchecked`'s condition, which took 1,079 examples, dies within 507 over twelve seeds.
- Steps 9 and 10's properties (`tests/property/test_condition_properties.py`), in a shard of their own: HP7,
  each condition against an oracle written from section 5 alone, on exact rationals, at each boundary its
  exactness turns on, with a plus or minus of each kind, the table's other rows and implied conditions; HP8,
  units by code point, end to end, however escapes write the registered one and refusing one equal under NFKC
  or case folding; HP9, the specimen merge; and HP3 and HP5 for the part steps 9 and 10 decide. 51 mutants,
  each killed within the `ci` profile's examples at both sizes (`test_condition_mutants.py`), 33 of them at
  the labels they name; five feature-audit controls, drawn features among them, one on a parameter of a
  parametrised property.
- Deterministic checks of each unit place, each row of section 5, the exact arms of PR-306 and PR-335 with a
  control that floating point gets them wrong, and implied conditions at steps 0 and 10
  (`tests/unit/test_read.py`, `tests/unit/test_conditions.py`).
- Fuzz target 4 reads at operating conditions and holds steps 9 and 10 to their text, its units by code point
  and its conditions by HP7's oracle. Its seeded fault moved to step 10, behind two changes to one seed, no
  seed holding two of its three parts; found after 84 to 601 s in ten local runs, so CI's control runs the
  target twice side by side for up to 900 s each. The record fuzz target drives the new properties. The
  unknown-member positions table gives an implied condition's members their verdicts (D06's first piece), and
  the reason-step check traces steps 9 and 10.
- With S2a-3's review (0 High, 2 Medium, 6 Low, 5 Info): the seven mutants that survived the whole suite each
  die now, in the mutant table. An implied condition located elsewhere (another field, version or content
  hash, a region beside the record, an interval, none) is read end to end and leaves its condition
  `condition_unstated`, and an implied value that is not an object is refused at step 0 (`tests/unit/`); HP7's
  token kinds draw accept lists holding strings outside the row, its unknown names a status object as often as
  a value, and HP8 a `plus_minus` unit in either entry of two. HP7's boundary kinds reach both sides of their
  bound, each one-sided kind built on its side and asserted there, the mixed kind as PR-335's pattern, with
  the end of the span and a bound's window as features; a mutant computing section 5's first row in floating
  point dies at it. A property holds that what the writer takes in a body, step 9 passes, with three writer
  mutants as its controls; a spec-sync test holds an implied condition's members, in the positions table and
  in the read, to the text, and the deferred row of the other acceptances names their kinds alone. HP7's
  oracle is said to repeat three of its implementer's readings. Steps 9 and 10's mutant searches join the
  `conditions` shard, whose `ci` timeout is 30 minutes.
- Each new check is shown failing on seeded faults.
- T1 sets each provenance object's `origin` to each other token of its row, in each base alone and beside each
  change inside the object, so that its relations see a member a read checks under one origin beside the
  others: 2,995 variants more, 4,657 in all. Its control: the reader `$defs` of b8a597d, which checked a
  derivation beside every origin, break relation 3 on a derived value's derivation varied with another
  origin, and on none of its variants that keep `derived` (`tests/spec_sync/test_t1.py`).
- CI fails closed. A merge to main runs every job and is never cancelled; the gate lists the paths that are
  documentation only and counts every other as code, both paths of a file moved included; and the one required
  check fails unless every job the gate asked for succeeded, so that a job skipped by mistake no longer
  passes. Every job runs on the image `ubuntu-24.04`, and every step under bash with `-eo pipefail`. Each
  pytest job writes a JUnit report, summarised on the run's page and kept 90 days
  (`scripts/report_test_durations.py`), whenever pytest ran; pytest runs under `timeout --foreground
  --signal=INT`, three minutes before its job's timeout, so that a job out of time is sent one SIGINT, stops,
  writes the report of the tests that finished and fails, rather than be cancelled without one; each test records its CPU time beside its wall
  time, its own and that of the processes it started. The mutant searches and the audit controls run on Python 3.11 and 3.15, the supported
  range's ends, in jobs of their own (`--property-controls`), and every other test on all five Pythons.
  `tests/unit/test_ci_workflows.py` holds the workflows to their comments: the image, the gate's step, each
  job's condition and the result, that no test or script names a path the gate calls documentation, what each
  pytest command selects, that the controls' modules hold mutant searches and audit controls only, no
  `continue-on-error`, `PYTEST_ADDOPTS` or `PYTEST_PLUGINS`, no pytest setting in `pyproject.toml` that
  chooses tests, and the workflows README's jobs and shards; each check with a control in which it must fail.
- Each of step 8's mutants that HP3 kills is searched among its own faults: `missing_represents_accepted` and
  `named_state_text_unchecked` first, whose kills, searched whole, changed with the constants Hypothesis draws
  from the modules a process has loaded, then the other 21 searched whole, which could meet the same at any
  change (maintainer, 2026-10-16). Each dies at its first example at both sizes, alone and after the whole
  suite's collection, on Python 3.11 and 3.15; HP5's two are still searched whole
  (`tests/property/README.md`).
- Every verdict the tests take from the package's JSON Schemas comes from jsonschema-rs, a development
  dependency only (0.58.4; `tests/verdicts.py`), where it was python-jsonschema's alone. Tests that take few
  verdicts take both libraries' and fail with a `Disagreement` where they differ; loops take jsonschema-rs's
  alone, python-jsonschema giving the messages a failure prints and failing the test at once where it finds
  none (`tests/spec_sync/schemas.py`). Both read every schema at draft 2020-12, and
  `tests/spec_sync/test_schemas.py` holds every schema file to that draft and every pattern to what both read
  alike. `tests/property/test_validators_agree.py`, a Hypothesis shard of its own (`agreement`), holds the two
  to one verdict: on T1's inputs, every example at `deep` and at `dev` and `ci` every tenth of each kind,
  which holds each origin, change and base; on drawn fields, bodies, records and each fault family's faults,
  by the writer and the reader; and along each writer mutant's own search, up to the example where its verdict
  first differs from the package's. It lists, and checks exactly, every place that takes jsonschema-rs's
  verdict alone, with what compares it or why nothing does. Its controls give writer and reader mutants to one
  side, each of the 12 writer mutants the drawn faults had missed among them, and a pattern ended in `$` to
  both, and hold the pairs the properties use to both libraries. Every mutant still dies, at the same example
  as before wherever the same modules are collected; the agreement module brings
  `scripts/gen_reader_schema.py` into every shard, and Hypothesis draws constants from it, so in CI's shards
  20 of 430 kills move (`tests/property/README.md`, Mutants). The switch cut the CPU time of the whole suite
  on 8 workers from 2,617 s to 1,620 s, and of the writer shard at `ci` on 4 from 2,956 s to 1,477 s; T1's
  tests ran about 25 times faster; on CI the writer shard's tests went from 649 s to 338 s
  (`tests/README.md`).
- The Hypothesis job's gate fails closed, as the gate of the other jobs does: it lists, beside the
  documentation, the paths no part of that job reads, and every other path runs the job, any test and the
  conformance runner included, which every shard loads and which the old list of code had missed.
  `tests/unit/test_ci_workflows.py` checks that no listed path is a module the property tests load or import,
  however late, nor a path such a module names, nor one the job's steps, its build or its workflow read.
- `tests/unit/test_ci_workflows.py` also holds each pytest command to its interrupt, three minutes before its
  job's timeout for every event and matrix combination, the fuzz job's excepted with its reason, and `--foreground`
  at every one of them, in `ci.yml` and in `repeat.yml`: without it `timeout` signalled pytest's whole process
  group as well as pytest, and a second SIGINT in pytest-xdist's controller could end the run in an internal error
  (`RuntimeError: release unlocked lock`) and cost the durations summary (the interrupted-run test failed in 8 of
  200 runs on Python 3.15 on CI). With one SIGINT the controller's teardown ends the workers, so the report is
  written about 5 s after the limit. The durations
  report counts the tests the interrupt stopped, which pytest-xdist writes with a time alone, and leaves them
  out (`scripts/report_test_durations.py`); a test runs pytest under the same interrupt and reads its report.
  The records shard's `deep` timeout is 90 minutes, from 45, after it took 31 on the first `deep` run on CI;
  a guard holds each shard's interrupt at twice its slowest run measured there.
- Every commit of a pull request but its head is checked on its own (the `commit` job): checked out as it is,
  on Python 3.15, ruff, mypy and pyright, the wheel's build and check, every generator's `--check` and the
  whole suite at `dev`, at most six at once. The gate lists the commits, but those that change documentation
  alone, so a pull request of one commit runs none; a Python file counts as code wherever it sits, for the
  commits and for the pull request, since ruff reads every one; a tree that passed the same checks earlier in the pull
  request is not checked again, its pass kept in the cache under the tree, the workflow's blob and the
  runner's image version. The one required check requires the job
  whenever the gate lists a commit. `tests/unit/test_ci_workflows.py` runs the gate's step on stacks of
  commits (in order, documentation alone, an empty commit, code a later commit undoes, a force-push, more
  commits than a matrix holds) and holds the job to its checks, its order and its key, each with a control.
- A pre-push hook, `scripts/pre-push`, which refuses a push that would publish a private name or path:
  `scripts/check_confidential.py --pre-push` reads git's pre-push input and checks what the push publishes,
  the name of each ref it writes, every file content and annotated tag the remote lacks by what it advertises
  then (`git ls-remote`, not the remote-tracking refs, which a branch deleted on the server leaves behind), at
  each path it has in the commits pushed, a content git names with no path included, and every commit's
  message, so that a file a later commit removes is checked too. A path or message that is not UTF-8 is read
  and shown escaped. It checks the names with the key file `git config openmaterica.scanKeyFile` names (a
  `~` expanded) or `CONFIDENTIAL_SCAN_KEY`; without a key it refuses the push, unless the clone says it has
  none (`git config openmaterica.scanWithoutKey true`), and then checks the paths alone. CONTRIBUTING says
  how to install it. Tested through `git push` in a throwaway repository with a bare remote. CI's scan also
  checks a pull request's branch name (`--ref-name`). Both scans read a binary file, or text in UTF-16 or
  UTF-32, by its printable runs of four ASCII characters or more, where they skipped any content holding a
  NUL byte; what a file holds compressed is still not read (CONTRIBUTING).
- A change to `site/` or `assets/` alone no longer runs the test suite, the mutant searches or the Hypothesis
  shards, none of which reads them, but a seconds-long `site` job (the gate's `site_paths`, neither code nor
  documentation; a Python file there is code). It stages the site with the Pages workflow's own step, copied
  word for word, which fails where a file it copies is missing, then runs `scripts/check_site.py` on the copy:
  every local link, image and icon, the web manifest's included, resolves; every page keeps one content
  security policy, in its head as a browser reads it and before anything it loads, that gives no directive
  twice and allows only `'none'`, `'self'`, `'unsafe-inline'`, hashes, nonces and `data:`, and nothing loads
  from elsewhere, an SVG image, a `background` or a stylesheet of the copy included, whose local addresses
  resolve too; no page has a `<base>`; the copy holds no symbolic link or hidden path, which the Pages
  artifact would publish dereferenced or leave out; and the README's images, inline, as HTML or by a
  reference, name files of the tree. It runs on every change but one to documentation alone, and the one
  required check requires it then. Each commit before a pull request's head gets the same steps: in the
  per-commit job, or, for a commit that changes the site alone, in a `site_commit` job.
  `tests/unit/test_ci_workflows.py` holds the job's staging step to Pages', shows that leaving out any file
  the step copies fails it, runs the site jobs' steps as written on a broken README and a page that loads from
  elsewhere, holds pages.yml's job to deploying what the site job checks, and checks that no test or script
  names a path of the site but those the site job runs and a few listed with their reasons, beside #23's check
  for documentation.
- A workflow that runs one test, file or directory many times on CI, each run under a seed of its own, to
  measure how often it fails (`repeat.yml`, dispatched by hand alone; `tests/README.md`, "Repeat runs on CI"):
  up to 20 jobs of up to 25 runs each, ten side by side at most, at one of the repository's own profiles, so
  that the same examples run in minutes rather than the laptop's hours. A request job checks every input and
  collects the node before any run starts (`scripts/repeat_runs.py`): the node a path under `tests/` that
  exists, the counts within their bounds, and no extra argument but `--shard` and `--property-controls`, so
  that nothing reaches a profile's example count, deadline or health checks. Each run's record keeps its seed,
  its outcome and each failing example Hypothesis reported; a summary gives the runs, the failing seeds with
  their examples and the failure rate with its one-sided 95 % upper bound, and fails the run where any run
  failed or did not finish. Each attempt of a job keeps its records under a name of its own, and the summary
  fails on any attempt of the run but the first, so that a job run again cannot replace a failure. It reads the
  repository alone, reads no secret, saves no cache, interrupts a job's last run three minutes before its
  timeout as CI's jobs do, and never cancels another dispatch. `tests/unit/test_ci_workflows.py` holds it to
  each of these, running its steps as written with a stub in place of pytest, each check with controls in which
  it fails.
- CI's Hypothesis runs drew fixed examples until this change. From the first CI run, with the profiles'
  introduction in S1a (cd3d444, 2026-10-14), and so in the runs behind 0.1.0.dev1, every job that ran the
  Hypothesis tests on GitHub drew the same examples on every run of the same code, whatever
  `--hypothesis-seed` said: the test matrix and the per-commit job at `dev`, the Hypothesis job at `ci`, and
  the one `deep` run before this change (by hand, 2026-10-17), with that run's fuzz job's replay at `ci`.
  GitHub sets `CI`, on which Hypothesis loads its built-in `ci` profile at import, and the repository's
  profiles, registered without a parent, inherited its `derandomize=True`, which Hypothesis applies before any
  seed, and its suppressed `too_slow` health check. The profiles now take Hypothesis's own defaults as their
  parent and suppress `too_slow` themselves, so the one change on CI is that every run draws new examples,
  those a laptop draws under the same seed; on a laptop, the one change is that `too_slow` is suppressed.
  `tests/unit/test_hypothesis_profiles.py` checks, in fresh processes with and without a runner's variables,
  that a runner changes no setting of any profile, imported or as a property runs them after pytest's hooks;
  that none is derandomised; that each keeps the settings the maintainer fixed (its example count, no deadline,
  `too_slow` alone suppressed, the blob, the repository's example database and every phase); and that on a
  runner two seeds draw different examples and one seed those it draws elsewhere. Its controls, the
  registration as it was, `derandomize` put back, each fixed setting changed and a deadline set in a hook on a
  runner alone, each fail it. Each `dev` run on CI is now a sample of its own, so an audit fails a sound
  property by chance about once in 2,000 runs of the suite, which makes a push red about once in 400 from the
  test matrix (`tests/property/README.md`, "Audits"). An audit's failure therefore names the seed Hypothesis
  drew its run under and the command that draws it again (`tests/unit/test_audit_replay.py`).
- The feature audit holds `dev` to the false failure `ci`'s floors keep: by the floors' model, at the chance
  each floor assumes, no feature it judges fails a correct run with a probability above 1e-6; a feature whose
  measured share falls below that chance fails more often, and is fixed where it is declared. `dev` now holds
  every feature to its draw floor where that is at least 10, judging no other: a drawn feature at one over
  their number, one declared by its chance at that chance, and a declared feature at three times its least
  share, never above its least share (`audits.RULES`, `floor_shortfalls`). It held declared features, and
  features drawn among three or fewer, to their least shares where 20 were expected, a bound of about 1e-3 a
  feature set before the per-commit job (#30) ran the suite at `dev` once for each commit: on 2026-10-18 three
  of about 75 `dev` jobs of #35 and #37 failed by chance (`unknown_field` in 10.5% and `another_field` in
  11.0% of an invariance property's examples, `drawn` in 9.5% of a monotonicity property's, each below 11%),
  so that a pull request was almost never green. By the model, the old rule failed a run of every property
  with a probability of about 0.36 on main (about 1 with #35's and #37's properties), the new at most 1.3e-5
  (3.2e-5); run locally at seeds 1 to 100 on #37's head, the audited properties failed 2 runs of 100 by the
  old rule (features drawn among three again) and none of their 8,900 audits by the new. Over those runs, each
  declared feature of main that `dev` judges showed 0.94 to 1.26 times the share its floor assumes;
  `non_ascii_character`, declared by its chance measured at `ci` (0.66), showed 0.57 at `dev`, about 3e-5 by
  the model, as before. `dev` stops judging 12 features of main's properties (25 with #35's and #37's), least
  shares of 0.10 to 0.16 and features drawn among three, each still judged at `ci` and `deep`. `ci` and
  `deep` judge exactly as before: `tests/unit/test_audits.py` pins what they judge of every declaration on a
  grid, in runs of sizes that are not multiples of eight and with `interesting` and `invalid` draws,
  computed from the rule before this change, with controls in which another rule or floors at another
  false failure judge otherwise. It fails if a feature judged by a floor, at any profile and any declaration
  on the grid, fails a correct run with a probability above 1e-6 by the model, with controls (the least shares
  `dev` judged by; floors at 1e-3), and holds the three CI runs' counts, replayed under their jobs' commands
  and seeds, which fail by the old rule and pass by the new. The README's "about once in 2,000" for `dev` is
  gone (`tests/property/README.md`, "Audits"; `.github/workflows/README.md`), and it no longer says that `ci`
  judges every share (it judges those of 1% or more) or gives one figure for a run at `ci`, whose least shares
  have figures for the json and records shards' and the writer schema's acceptance properties alone.
- Three test helpers that rebuilt the same thing on every call build it once, and no draw or verdict changes:
  `tests/spec_sync/test_cases_md.py` reads each suite's `CASES.md` once, not once for each of its 1258 case
  files, and types the result read-only, since every caller shares it, and keeps its argument typed;
  `tests/unit/test_ci_workflows.py` parses each workflow once, handing each caller a deep copy of its own, and
  each module's source once; and `tests/property/strategies.py` builds `json_values`'s strategy once for each
  set of arguments, keyed so that arguments `==` does not tell apart (0.0 and -0.0, `True` and 1) never share
  one, and `every_double`'s three strategies once; `tests/unit/test_strategy_key.py` holds that key's cases,
  with a control under a key by `==`. Measured on a loaded 16-core machine, each change's tests run at the
  same time as the same tests without it: `test_cases_md.py` took 0.9 to 1.3 s of CPU where it took 62 to 69
  s; `test_ci_workflows.py` 0.22 to 0.27 of its own CPU, the bash and git it runs unchanged; the `json` shard
  0.72 to 0.79 of its CPU at `dev` and 0.69 at `ci`, and the `writer` shard 0.78 to 0.82 at `dev`, against
  1.29 and 0.95 for two unchanged runs paired; the `agreement` shard (0.98 and 1.12, against 1.16 unchanged)
  and the audit controls (0.98) changed by no more than that noise. Under a fixed seed, every Hypothesis test
  case of the property suite and the tests that draw from its strategies (37,786), of the audit controls
  (53,688) and of the `json` shard at `ci` (42,964) drew the same choices and arguments, with the same status,
  as before, and every test gave the same verdict; a change that swaps the two branches of `every_double`'s
  `one_of` changes the draws of 37 of the `json` shard's 100 traced tests and the verdict of one.
- How many jobs run at once is set by repository variables (maintainer, 2026-10-17): `PER_COMMIT_MAX_PARALLEL`
  caps the `commit` and `site_commit` jobs (6 where it is unset, the cap before) and `REPEAT_MAX_PARALLEL` the
  repeat workflow's runs (10 where it is unset), so that the organisation's 60 runners, shared with MIME and
  MADDENING, can be given to OpenMaterica while it works alone and taken back when they work beside it. A step
  of the job the capped jobs need, the gate or the request job, checks the variable, or its default, on every
  run and fails where it is not a whole number from 1 to 20, so that no value GitHub does not document for
  `max-parallel` reaches them, and writes the value it took as that job's output, which the capped jobs parse
  (`fromJSON(needs.gate.outputs.per_commit_max_parallel)`): they never read the variable, so a value changed
  after the check does not reach them. `.github/workflows/README.md`, "Jobs at once", says when to raise or
  lower each and how. `tests/unit/test_ci_workflows.py` holds each capped job to that expression, each
  checker to that output and every repository variable a workflow reads to a cap's check, and runs each check
  as written, under two locales, on values inside and outside the range, each with controls in which it fails;
  its evaluator of GitHub's expressions reads `fromJSON`, and it reads a step's outputs as the runner does.
- Every derandomized Hypothesis run, the mutant searches and the audit controls among them, draws none of the
  constants Hypothesis harvests from the loaded modules (`tests/harvested_constants.py`, installed by
  `tests/conftest.py`), so what it draws, and so a mutant's kill count, depends on the code alone. Hypothesis
  6.169 takes a constant in about one draw in twenty, half the time one it found in a loaded module outside
  `tests/`, and `derandomize=True` fixes the seed, not those constants: #43's `scripts/check_anomalies.py`,
  collected through its unit tests, moved 13 of the 544 kills that `--property-controls only` measures and let
  `a_non_object_provenance_opens` survive 2,000 examples, which turned that pull request red (its review, H1).
  Hypothesis has no setting or environment variable for it, so the pin replaces
  `providers._get_local_constants` and empties `providers.CONSTANTS_CACHE`, both private, for a run whose
  settings are derandomized; `tests/unit/test_harvested_constants.py` fails if they go or stop having effect,
  with controls in which the draws do change. Every other run keeps the pool. With the pin, none of the 544
  kills moved with #43's module collected, with a module of 270 other constants loaded, with each mutant
  module collected alone, or on Python 3.11 against 3.15, where without it the second moved 47 and the third
  62; every mutant still dies within its 2,000 examples at both sizes, the latest at the 872nd, and
  `tests/property/README.md`'s counts are measured again.
- Hand mutants run on CI (maintainer, 2026-10-18), so that a reviewer's runs of the suite against dozens of
  mutants, about five hours on the shared laptop for one review, run side by side (`mutants.yml`, dispatched
  by hand alone; `tests/README.md`, "Mutant tables on CI"). A reviewer commits each mutant on a branch of its
  own as `mutants/<name>.patch` and dispatches the workflow with a pytest selection: each mutant runs in a job
  of its own, its patch applied to a clean checkout of the dispatched commit, beside a job of the commit as it
  is (the baseline), and a last job writes one table, on the run's page and as an artifact: killed, with the
  collected test that failed first; survived; broken, where the patch does not apply or the code does not
  import or collect, in one process or under pytest-xdist; or undecided. Each row gives the paths its patch
  touches, and a kill by a patch that edits the tests or pytest's settings is marked. Where the baseline did not pass, no mutant counts as killed, and the run passes only
  when every mutant was killed. Patches are files of the dispatched commit, never text from the dispatch form,
  and the request refuses, before any mutant runs, one git does not read as a text patch in its own format,
  one with binary data, a rename in any form (with rename lines or without, as a `diff --git`, `---` or `+++`
  line naming another path, which git applies though its report does not show it), a copy, a link or a
  submodule, and one that touches a path outside the checkout, inside `.git`, under `.github/` or `mutants/`,
  one git ignores (`.venv/`, `.hypothesis/`), the runner itself (`scripts/mutant_runs.py`), or what decides
  what uv installs or how it runs (`pyproject.toml`, `uv.lock`, `uv.toml`, `.python-version`); once the patch
  is applied, uv neither syncs nor locks. A mutant's job runs the code that records its verdict from a copy
  outside the checkout, made before the patch is applied; the record holds facts, and one function makes the verdict from
  them, so that a mutant whose patch did not apply or whose code did not import is broken whatever else its
  record holds. The runs of a dispatch share one seed, given or drawn and shown, so that a mutant's run
  replays exactly. At most `MUTANT_MAX_PARALLEL` mutants run at once, a repository variable checked as the
  other caps are (10 where it is unset, 20 at most). `tests/unit/test_ci_workflows.py` runs its steps as
  written on a throwaway repository, each refusal with the rule taken out of the script as its control, and
  end to end with this Python's pytest on mutants that are killed, survive and are broken. The whole suite of
  a branch already runs on CI, through a draft pull request or `repeat.yml` with `node=tests`;
  `.github/workflows/README.md`, "The whole suite on CI", says how.
- `repeat.yml` warns once, and runs the request all the same, where the node collects a test in a module
  whose searches are derandomized: one `PROPERTY_CONTROLS` selects, or one whose code sets `derandomize` to
  anything but off, fixes a seed (`@seed`), or runs `MUTANT_SEARCH` or `examples_to_kill` by any name (#43's
  review, L7). The reading is by module, which the warning says; for the whole suite, which always holds
  such modules, it is one sentence naming none. Every repeat of such a test draws the same examples whatever its
  seed, but repeating it on a head and on its base is still a valid comparison. The warning reads what pytest
  collected with the extra arguments; `tests/unit/test_ci_workflows.py` runs the step on nodes that must and
  must not be warned on, with controls that drop the warning, turn it into a refusal, or read the node in
  place of the collection. Both hand-run workflows set `queue: max` on their concurrency group, since GitHub
  otherwise cancels a dispatch pending in it when another queues, so that none is cancelled as their
  comments say (#46's review, L2).
- Three mutant searches whose kill sat in a long tail are planned, so that a change that moves a search's seed
  (a Hypothesis upgrade, or any other change to what Hypothesis hashes into it) cannot push them past their
  2,000 examples. With the pin their kills were fixed, but late: `a_non_object_provenance_opens` at the 872nd
  example (original size; 455 at the small), `empty_word_made_plural` at the 629th and `row_requirements_ignored`
  at the 536th. Reseeded 24 times with the code unchanged, drawn whole, they took up to 1,875, 945 and 1,363
  examples, and two of the three survived 2,000 in some salt. Each now draws the region where its fault shows,
  in records and names the core passes (an edit below a `review` or `copy` in a provenance whose value is an
  array; a name with an empty word and the same with `s` or `es` in it; a table case with a required condition
  held nowhere), checks the same assertion, and dies at its first example at both sizes and in all 24 salts. The
  properties are unchanged; a control checks that each planned search's examples pass on the core (the hash's
  at both sizes, with a second arm that plans the draws that tell the search from one that edits a removed
  leaf, and a test that the control fails that search). No budget, size, fault or mutant was changed; the other
  538 kill points did not move, and the latest of the 544 is now the 276th (`tests/property/README.md`).
  `examples_to_kill` no longer counts an error raised by the strategy itself as a kill (a kill at the 0th
  example); no kill point moved.
- The known-anomalies registry is checked in CI, in the gate on every run, whatever the change touches, by
  `scripts/check_anomalies.py`. It stands in for MADDENING's validator, which accepts `materica_version` from
  MADDENING 0.4.0 but whose packaged command reads each `affected_components` entry as an importable Python
  name, which this registry's component names are not (its library function can skip that read, and the
  command cannot; installing it needs Python 3.12 or later). It checks MADDENING's record schema with this registry's prefix, version
  field and component names: the top-level fields and no other, `materica_version` the package's version and
  `generated_date` a date; in each entry MADDENING's required fields and no other, `OMAT-ANO-` and three
  digits, each identifier once, the severity (`DOCUMENTATION_ARCHITECTURE.md` section 8.2), safety relevance
  and resolution status among their values, `affected_versions` a PEP 440 version specifier set or `none`, and
  each component `schema:`, `reader:`, `method:`, `model:` or `data:` and a name. It runs on the standard
  library alone, so it reads the registry's YAML as a subset, as PyYAML reads it, and refuses the rest at its
  line, an unquoted number or date and a key given twice among it, and refuses, not fails with a traceback, a
  registry or `pyproject.toml` that is missing, not UTF-8 or nested too deep, or a version that is not a string
  or is dynamic. `tests/unit/test_check_anomalies.py` fails a copy of a passing registry with each of its listed
  faults, one at a time, naming the rule (each required field missing, each top-level field missing, and a
  registry the reader refuses among them), holds the specifier syntax to `packaging`'s on listed strings, and
  holds the reader to PyYAML on fixed witness documents; `tests/property/test_anomaly_reader_properties.py`
  holds the reader to PyYAML's `safe_load` and the specifier syntax to `packaging`'s on drawn documents and
  sets, in the Hypothesis job (an estimate by sampling, with controls in which a weakened reader is found, not
  a proof of equality); one difference is known, a key of more than 1024 characters, which PyYAML refuses.
  The check runs where no installed package is importable, and `tests/unit/test_ci_workflows.py` runs the
  gate's step as GitHub runs it, which passes a registry at the package's version and fails one a version
  behind.
- A test-only reference model of the read, written from the specification's text and importing nothing from
  `materica`, for HP12 and the fuzz targets (S2a-4, phase 0; the S2 design's SQ49): steps 0 to 13 for
  constants, intervals, compositions and evidence, implied conditions and nominals, `list_records`,
  `content_hash`, and alternatives as far as S4's decision 12 lets S2 go; anything else, a table, a pick, an
  overlay or an extrapolation among them, gives no verdict, which a test never reads as a pass. Each rule
  cites the text, a quote at its line, and each point the text leaves open is listed with the ruling or the
  fail-closed choice taken. Of the 1,223 case files of a read, it agrees with 894 under every configuration
  of claims each allows (6,776 runs) and gives no verdict on 329, each listed by kind in an exact list of
  exceptions (tables, overlays, extrapolations, picks, and alternatives with reasons of their own); it
  disagrees with none. The table evaluation suite's 35 files, which ask for no read, are left out, and a test
  holds those left out to the files whose operation is `evaluate`. Its tables are held to the generated
  vocabulary; 75 faults seeded in it are each killed by a case file or listed as a survivor, a rule no case
  pins, 15 of them, each killed by HP12 or listed with the reason no read S2 builds shows it; and a layering
  check, with a control, shows it reaches no `materica` module (`tests/reference/`). Phase B fixed five of its
  readings the text does not take, each found by HP12 or by fuzz target 4 held to it, each seeded since.
- One more mutant search is planned (maintainer, 2026-10-19): HP12's `bounds_given_by_a_constant`. With the pin it
  died at the 139th and 523rd examples (small, original); reseeded 24 times with the code unchanged, drawn whole,
  it took up to 934 and 594 examples, after the 500th in five of its 48 searches. Its planned search, constants
  alone, had drawn `valued` whole since S2b-1 and S2b-2 made it draw every form, so that a constant under
  `want: bounds` came up in one draw in 35. It now draws constants under `want: bounds`, as drawn or with an
  implied temperature. Of 2,000 examples, at both sizes, at a derandomised seed and at a random one, all kill, and
  none fails on the core; it dies at the 1st example at both sizes and in all 24 salts. The properties, budgets,
  sizes, catalogues and the mutant tables' members are unchanged, and no other kill point moved
  (`tests/property/README.md`).
- One more mutant search is planned (maintainer, 2026-10-19): HP1's `condition_unchecked_without_its_condition`,
  in the result's group and in HP12's. With the pin it died at the 10th and 20th, and the 128th and 168th
  examples (small, original); reseeded 24 times with the code unchanged, drawn whole, it took up to 1,064 and
  811 examples, after the 500th in four of its 48 searches in each group. Each search now draws the region where
  its fault shows: HP1's `unknown_at_step_10` kind with the fault `unchecked`, and HP12's reads with that fault of
  step 10 (`result_strategies.unknown_at_step_10` and `model_strategies.step_9_or_10_faults` take the faults to
  draw first, their default unchanged). Of 2,000 examples of each, at both sizes, at a derandomised seed and at a
  random one, 1,446 to 1,657 kill (the others draw a second fault, of step 9, which ends the read before step 10,
  or a `want` of a suite the claims leave out, which step 0 refuses), and none fails on the core; each dies at the
  2nd example at both sizes and in all 24 salts. The two cells that name where it dies now name what the search
  draws, not a measurement. The properties, budgets, sizes, catalogues and the mutant tables' members are
  unchanged, and no other kill point moved (`tests/property/README.md`).
- The property README's kill counts are generated, and a kill after the 500th example fails a check (maintainer,
  2026-10-18 and 2026-10-19), so that stacked pull requests stop conflicting on them and none goes stale, as 27 of
  its 265 rows of counts had;
  its summary named the 276th example as the latest kill of 544, where 874 searches ran and the latest was the
  523rd. `tests/property/kill_points.json` records every mutant search's kill point at both sizes, one group per
  test function and one line per mutant, and what they depend on (the Hypothesis version, and a digest of the
  source of each helper that runs a derandomised search, since Hypothesis seeds a search from it and editing it
  moves hundreds of kills at once), written by `scripts/gen_kill_counts.py` from the JUnit reports pytest
  writes (`examples_to_kill`) and never by hand; the script writes from it the last cell of each row of the tables
  under a comment naming their group, and the summary. `--check`, beside the other generators in CI's
  generated-files job, the per-commit job and `scripts/pre_review.py`, fails where a count differs, where an input
  differs from the tree's (naming it), where a recorded group has no table, where a table of every search of its
  group lacks a recorded mutant's row, or where a kill falls after the 500th example: the margin guard, which
  names each such search (a recorded kill at the 501st fails it, at the 500th passes); the guard bounds the pinned
  seed's kill, not the margin over other seeds. CI's controls job holds the file to its own run of every search on
  Python 3.11 and 3.15 (`--against` its JUnit report): a kill that moved, a search not recorded, a recorded one
  with no kill, a recorded group missing from the run, a search that passed without recording its kill, and a
  README row naming a search that did not run each fail it; `pre_review.py` runs the same check (`--measure`) wherever it runs a shard that
  holds mutant searches. A search's kill does not depend on the profile or the Python (the 874 were the same at
  `dev` and `ci` and on 3.11 and 3.15), so a local run records CI's: `--measure --record` runs every search and
  records it. The one-slip relation's table gives one row a mutant, and the unrestricted twins' kills a table.
  The table evaluator's 18 mutant searches (`test_evaluate_mutants.py`) are recorded with the rest, their README
  table under a comment naming its group: the recorded counts equal the ones typed there, and the latest kill is
  the 96th example (`loglog_not_exact_at_ties`, original size), so none needs a plan.
- The table evaluation cases run (S3-te; `read_side_contract.md` section 7). OpenMaterica's own code claims no
  table evaluation, so a test-only reference evaluator, written from the specification's text and importing
  only the standard library (`tests/reference/table_evaluator.py`), stands in for a consumer's: the runner's
  `evaluate` executor runs every TE file under its four configurations, `binary64` and `binary32`, each
  declaring the left and the right side, and compares each by the specification's README ("Case files"). All
  35 files are reported on their own line, verified against the reference evaluator, never as passed. The
  evaluator also has an `exact` mode, for later pieces' properties: exact for a linear table, and for a
  log-log one wherever the value is rational, every point halfway between two doubles included; elsewhere
  worked at more digits until two precisions in a row round to the same double. At a knot it returns the
  knot's `y` as stored, so a `-0` there stays negative zero, as in the other two precisions. A log-log
  derivative beyond the largest double is returned exactly, as a linear one is, and never raises.
  Two limits are stated, not removed (S3Q29, maintainer, 2026-10-19): exact mode rests on Schanuel's conjecture,
  and in `binary32` the evaluator raises on a log-log table with a number that rounds to zero there, which no TE
  file holds (the evaluator's docstring; the TE suite's README, "What the cases cannot show").
- Broken evaluators, one fault each, in `tests/conformance/test_runner_can_fail.py`: the fifteen of the S3
  design's section 6.4, five more the TE suite's README names, and two more the text supports (a
  `source_range` that widens the readable range, and a log-log derivative scaled at the lower knot), each
  failing its named TE file under every precision and side it claims, by the difference named beside it and
  never by raising. Each still fails one of its named files with that file's `binary32` tolerance ten times
  as wide: the cap on a file's tolerance, restated per broken evaluator (maintainer, 2026-10-17).
  A test holds the list the tests run to the table in the TE suite's README, "The broken evaluators": the same
  faults, each beside the same files and the same difference, with controls in which a row, a file or a
  difference is changed (`tests/spec_sync/test_broken_evaluators.py`).
- The `evaluate` executor adapts a raised refusal, as the TE suite's README says a runner does: an evaluator
  that raises `Refusal` in place of reporting a refusal fails no TE file. It adapts no other exception, and a
  raised refusal where none is due fails.

### Known Anomalies
- The registry's `materica_version` is the package's version (`0.1.0.dev2` at this release); it still read
  `0.1.0.dev0` after 0.1.0.dev1 was released, and its header still said no version had been. No entries yet.

## [0.1.0.dev1] - 2026-10-14

A development pre-release, published to rehearse the release workflow and to hold the name on PyPI. It holds
S1: strict JSON, RFC 8785 and the content hash; records, their store and the read up to step 5; and the
schemas and vocabulary of 0.1, whose files may still change before 0.1.0. The entries below are everything
up to this release.

### Added
- Architecture concept (`design/ARCHITECTURE_DRAFT.md`).
- Documentation architecture plan (`DOCUMENTATION_ARCHITECTURE.md`), contribution rules (`CONTRIBUTING.md`),
  security policy (`SECURITY.md`), intended use statement (`docs/regulatory/intended_use.md`), an empty
  anomaly registry (`docs/validation/known_anomalies.yaml`) and its issue template.
- Design revision: plain records as a complete form with OpenUSD as the primary binding; five value forms;
  versioned model families with golden test vectors, reference implementations and check points in
  records; declared uncertainty structures; per-field proxies; a source registry, three record tiers and a
  separate data licence; the core, family packages and library as separate components; the dielectric
  section; layered paths. Constraints 13 to 17 and the pull-request template with the data attestation.
- Distribution design: namespaced material identifiers; material cards in place of data sheets; static,
  archived releases with federation through an index and no hosted service; self-contained shipped USD
  layers; record checks as a core command (`python -m materica check`). Constraints 18 and 19.
- Model-assisted curation design: an MCP tooling layer (bring-your-own-key, deterministic tools, quotes,
  human review, fail-closed release, a gold set); convention witnesses for parameter sets; evidence,
  assistance and search-record provenance fields. Constraints 20 to 22; constraint 14 extended.
- Phasing for MIME 0.3.0: three feature sets, each feature tied to what it serves; MIME spikes before MIME
  work starts.
- Revision against two new principles (records hold facts, consumers declare choices; carry what the
  evidence supports): consumer declarations with three-valued checks; domains; specimen facts in place of
  proxy flags; named mixing rules picked by the consumer; no schema fallbacks; tables with schemes, ranges
  and edges; spreads that say what they represent, `not_reported` and interval-only values; independent
  witnesses; fits written back only as scoped overlays; a family `kind` for evolution families;
  failure properties under mechanics; biocompatibility as test evidence; an advisory index; rewritten
  spike controls. Constraints 23 to 25; constraints 6, 9, 13 and 14 revised.
- Simplification pass: sections specified when a consumer needs them (fluid, mechanical with failure,
  acoustic, radiological, magnetic, biocompatibility first; optical, thermal and dielectric later), with
  three rules that make adding one a minor schema change; a publishers file and a template repository
  from the first library release, with MIME as the first other publisher; prototypes before the package;
  the advisory index and Hugging Face items as notes for later.
- Evolution families in the core from the start: state and history (viscoelastic and rate-dependent
  models), with optional events defined independently of any solver.
- Decisions after the prototypes (2026-10-12): the scope is substances in and around the human body, never
  systems, with five rules (a transfer test, pairs, geometry as scene data, behaviour, entry); every record
  has a record type, `material` and `interface` being OpenMaterica's, so other namespaces can use the
  machinery for data that is not a material; the curated library under CC0-1.0; reference implementations live
  with their families, shipped as `openmaterica-families`; consumers write their own readers, mixing rules and
  evaluators, verified against conformance data; quotes for every value extracted from text or a table in
  the curated library; curation tools before the first library release; a `bulk` section for density and
  elemental composition; the layered path's USD form as a typed prim, needed by MIME 0.3.0; an anisotropic
  linear elastic family for bone; conditions separated from specimen facts, with a starting vocabulary;
  new conformance cases (derivatives at table knots and ends, in-range reports, mixing at the cell, record
  types, the stage's units, physics bindings). Constraints 26 and 27; constraints 14, 17 and 21 revised.
- Fixes after an independent review of that revision (2026-10-12): the transfer test replaced by a line
  between test specimens (in, with their shape and size as conditions) and made objects as built (out); the
  typed value beside each field's JSON string in USD deleted, and no `UsdPhysics.MaterialAPI` on shipped
  layers; an `overlay` record type, overlays as prims of their own applied only when declared, scoped by a
  hash of the consumer's model configuration; unknown record types skipped when listing and refused when
  referenced, with namespaced types specified only after a consumer prototypes one; a plain scene manifest;
  the layered path's USD form with an index per interval, since USD drops repeated relationship targets;
  `interval` and `composition` value forms; attenuation stored as an amplitude coefficient, with shear
  attenuation for solids; declared extrapolation as a consumer declaration; an unknown token refuses its
  field and an unknown condition gives "unknown"; run-time watches on every declared condition; a
  `marginals` uncertainty structure; quotes required by the curated library's policy and checked where
  present, with a hash fallback if the legal review rules quotes may not ship, and evidence excluded from
  the CC0 grant; the content hash over the whole record minus an exclusion list, with test vectors;
  "a consumer's computation" defined as its step, compiled program and gradient path, the core running at
  build, and the write-side tooling split into `openmaterica-authoring`; the first library release defined as
  the first archived release with a DOI; conformance suites; disease and treatment state as specimen
  facts; records in JSON only. The stiffness tensor for bone moved to stretch. Constraints 4, 5, 13, 14, 21,
  24, 26 and 27 revised.
- After an ecosystem survey of NVIDIA's schemas and the wider ecosystem, and its review: the USD binding,
  layered paths, label crosswalks and scene documents move into OpenMaterica 0.1, with no cut line; a region
  binds its material with the purpose `materica`, and `physics` is left to engines; an engine is declared as a
  model, written by an engine adapter from pinned engine crosswalks and checked per shape by `materica check
  --stage`; readers detect schemas by name, traverse instances, and refuse unloaded payloads, point-instancer
  prototypes and time samples; acoustic attenuation is registered as `/m`; label crosswalks read by name.
- OpenMaterica ships one engine crosswalk, for OpenUSD's `UsdPhysics`; a consumer writes and pins the
  crosswalk for any other engine it runs, drafted by a scaffold from the engine's schema file and compared
  with the schema file it pins by hash. The stamp on an engine material carries the APIs applied, each
  attribute's type and dimension and the unit convention, so the stage check re-derives values without the
  crosswalk and checks the stamp against its units.
- Names settled (maintainer, 2026-10-13): conformance suites, engine crosswalks and label crosswalks replace
  conformance profiles, engine maps and label mappings; identifiers renamed to match
  (`engine_crosswalk_invalid`, `family_suite_absent`, `--crosswalk`, `"suite"` in case files).
- Decisions before the first code (maintainer, 2026-10-13): the core depends on Python's standard library
  only, with `[check]`, `[usd]` and `[sample]` extras; engine results in `openmaterica[usd]`; scene documents
  built before declarations; the writer JSON Schemas the single source of structure, with typed shapes
  generated from them; the package typed (`py.typed`); a Python 3.11 floor under a standing rule; record
  checks that need a registry, a copy or the history moved to the library's tooling; SPDX headers on source
  files.
- The first code: the package (`pyproject.toml` with uv's build backend, `uv.lock`, `py.typed`, no run-time
  dependency, the licence as an SPDX expression); strict JSON reading (`materica.core.jsonio`), RFC 8785
  serialisation (`materica.core.canonical`) and the content hash (`materica.core.hashing`, exported as
  `materica.content_hash`); CI, with a sign-off check on every commit of a pull request.
- The read up to step 5: identifiers and versions matched in full, versions ordered by their components'
  lengths and digits (`materica.core.identifiers`); the vocabulary of schema 0.1, generated from the
  specification's tables (`schema/0.1/vocabulary/`, `materica.core.vocabulary`); the reader schema's checks by hand
  (`materica.core.envelope`); the record store, and steps 1 to 5 of a read (`materica.core.record`,
  `materica.core.resolve`); the request's own check and the read, which raises `NotImplementedError` where a
  step not built yet would decide it (`materica.core.read`); plain records from files (`materica.io.plain`).
  `materica.read` and `materica.load_records` join `materica.content_hash` as the public API.
- The JSON shapes of records, read requests and results, and case files, as TypedDicts generated from the
  schemas (`materica.shapes`); a read's results are read-only to a type checker (PEP 705, in `shapes.pyi`).
- Generators, which CI runs with `--check` in a job of its own: the vocabulary from the specification's tables,
  the reader schema and the typed shapes from the writer schemas (`scripts/gen_*.py`).

### Changed
- Names settled before the first release (maintainer, 2026-10-14): the project is OpenMaterica, replacing the
  working name the drafts used until then, since removed from the public files. The distribution is
  `openmaterica` and the package `materica`. The record namespace, family identifiers, USD binding purpose,
  attribute namespace and command are `materica`, and the USD schema classes take the prefix `Materica`.
  Library records are `materica/MAT-NNNN` and `materica/INT-NNNN`, and the registry prefixes are `OMAT-ANO-`,
  `OMAT-VER-` and `OMAT-MTH-`.

### Schema
- Schema 0.1.0 (draft), settled before the first code: what a reader refuses as malformed JSON, numbers read
  as doubles, `null` read by where it is, one schema-version pattern, the reader schema's scope, how a
  material reference resolves among the records supplied, the request checked first, reason multiplicity,
  case-file claims, variants, exact comparison and operations, and the namespace `conformance` reserved for
  conformance fixtures (`docs/specification/changes.md`).
- The JSON Schemas of 0.1, each `$id` its path under `https://w3id.org/materica/schema/0.1/`: the writer
  schema's envelope and body structure, edited by hand (`record.writer.json`); the reader schema, generated
  from it (`record.reader.json`); the read request and result (`read_request.json`, `read_result.json`); the
  schema of case files (`case.json`); and the vocabulary, generated from the specification's tables
  (`vocabulary/`). The specification's member tables are checked against them.

### Families
### Data
### Verification
- The conformance-case runner. Of the 416 case files, the 51 `content_hash` cases (HS-001 to HS-003) run and
  pass; the 365 reads and listings are reported as not yet runnable, never as passed. Nine broken
  implementations, one fault each, each fail a real case.
- Property tests of the JSON reader, the RFC 8785 serialisation and the content hash, under a draw-rejection
  audit and a feature audit; 32 mutants of the core, each killed by its property within the `ci` profile's
  examples at both tree sizes; Hypothesis profiles `dev`, `ci` and `deep`, the last at the original sizes.
- Atheris fuzzing, weekly: raw bytes into the JSON reader, checked against a reference reader built from the
  standard library; and the Hypothesis properties driven by Atheris, whose findings the property tests replay
  and shrink. Each run first shows that both find a fault seeded in the reader.
- All 417 case files run and pass, each under every configuration of claims it holds for: with the hash suite
  (409), without it (347), and with the fits and reference data suite (408). PR-330 gains an arm: a tolerance
  beside `operating_conditions` that is not an object (`read_side_contract.md` section 1). Fifteen more broken
  implementations, of the read and the listing, each fail a real case. Every case file reads alike through the
  reader under test and a reference reader that shares no code with it, and is valid against `case.json`.
- Checks that what is written twice agrees: the specification's member tables and the schemas, and the token
  lists the schemas write by hand; the envelope checks and the reader schema on every conformance input; each
  `CASES.md` and its case files; and the map of case files to the steps that run them (`tests/spec_sync/`).
  Each module's imports, relative ones included, against the layers, and the shapes' against the standard
  library.
- Property tests of the envelope checks against the reader schema, of versions, and of the laws of a read up to
  step 5; 35 more mutants, each killed within the `ci` profile's examples at both sizes. CI runs the property
  tests in two shards side by side. A third Atheris target drives these properties, and first shows that it
  finds a fault seeded in the read.

### Security
### Known Anomalies
- Registry created, with no entries.
