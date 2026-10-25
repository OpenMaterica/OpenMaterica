# `materica.core`

The core (layer L2, AD 7.1): the code that reads and checks records. It uses Python's standard library only
(AD 7.2, CONTRIBUTING constraint 3), so it adds nothing to a consumer's dependencies; the shapes it types its
results with (`materica.shapes`, generated) use the standard library only too.

## The data paths

The content hash:

```
bytes ─▶ jsonio.parse ─▶ value ─▶ hashing.hashable_view ─▶ view ─▶ canonical.canonicalize ─▶ bytes ─▶ SHA-256
            │                       (hashing.content_hash runs these three, and writes "sha256:<hex>")
            └─▶ Reason("malformed")
```

A read, steps 0 to 13 of `read_side_contract.md` section 3:

```
request ─▶ read.ReadRequest.from_json ─▶ step 0, the request on its own ─▶ reasons, or a ReadRequest
                                          and its implied conditions and nominals
                                                                                │
sources ─▶ record.RecordStore.add ─▶ candidates by id and version,              ▼
           and the unreadable sources                      resolve.resolve_record
                                                           1 the candidate that states the pin
                                                           2 its schema version     ┐
                                                           3 envelope.py's checks   ├ kept on the Record
                                                           5 its type               ┘
                                                           4 the hash, with HS: recomputed on every read,
                                                             between steps 3 and 5
                                                                  │
                                                           fields.find_field
                                                           7 the field, or absent; a field holding
                                                             alternatives (fields.alternatives_problems,
                                                             read._read_alternatives) reads each by 8 to
                                                             13, then sets it aside, keeps it or refuses
                                                             the field, with no pick and no overlay (S4a)
                                                                  │
                                                           read.read_value_field, steps 8 to 13 of one
                                                           value field:
                                                           fields.form_problems
                                                           8 the form token against its row; the record's
                                                             structure, the section and the members every
                                                             form shares (value_shapes); the own member of
                                                             a constant, an interval, a composition or
                                                             evidence
                                                                  │
                                                           fields.unit_problems
                                                           9 every unit against the registered one, code
                                                             point for code point
                                                                  │
                                                           conditions.check_conditions
                                                          10 each condition against the request, exactly
                                                          11 a constant's range is its conditions; an
                                                             interval, a composition and evidence none
                                                          12 stated_without_origin; the field's label and
                                                             mixed_conditions
                                                          13 the form's own member by want, as stored,
                                                             or a nominal's value for an interval under
                                                             want value, or want_mismatch
                                                                  │
          read.ReadResult (status, reasons, labels, ◀─────────────┘   every reason found, and the members
          conditions once step 10 ran to its end, and                 section 2 gives, as stored and copied;
          value, unit, specimen, statistics and                       or NotImplementedError for an overlay,
          provenance, an assumption, or                               a pick, an extrapolation, the rest of
          alternative_values)                                         step 7 and a table's member
```

| Module | Implements |
|---|---|
| `reasons.py` | a reason as `read_side_contract.md` section 2 shapes it, each code, condition and alternative once, the index of the alternative it was found reading where it was; codes from the table in section 4 |
| `status.py` | the three statuses of a read, and the worst of several (section 2) |
| `jsonio.py` | `record_format.md` section 1 item 6, strict JSON; `JsonValue`, the type of what it reads |
| `canonical.py` | `record_format.md` section 9 item 2: RFC 8785, with no Unicode normalisation |
| `hashing.py` | `record_format.md` section 9 items 1 and 2: what the hash leaves out, and the hash |
| `identifiers.py` | `record_format.md` sections 7 and 8: identifiers and versions, matched in full; material references |
| `slips.py` | `record_format.md` section 10: names one slip apart, by which a reader refuses a member it does not know that is one slip from a member named at its place |
| `vocabulary.py` | the tokens of the specification's tables, read from `schema/0.1/vocabulary/`, and `declarations.md` section 4.2's table of what covers which reason, row by row (`CoverageRow`, from `coverage.json`) |
| `envelope.py` | the reader schema's checks by hand (`record_format.md` section 1 item 2) |
| `value_shapes.py` | step 8's checks of what every form of a value field shares, by hand: a slip in the record's structure, a section's specimen, and a field's unit, conditions, specimen facts, statistics block, provenance members, label and status objects (`read_side_contract.md` section 3, step 8; `provenance.md`; `uncertainty.md` sections 1 and 4) |
| `fields.py` | a value field: step 7 finds it and checks the shape of the alternatives it may hold, step 8 checks its form token against its row (a composition's basis included), its shared members, and the own member of a form its row allows (a constant's, an interval's, a composition's and evidence's so far; a table the row allows raises `NotImplementedError`), and step 9 compares its units with the registered ones; its specimen facts, the section's merged with the field's |
| `record.py` | the records a read resolves among, and the checks that depend on one record alone (steps 2, 3 and 5) |
| `resolve.py` | steps 1 to 5: a material reference to the record it pins, or the reasons it is refused |
| `conditions.py` | step 10: the conditions checked, each against the request by section 5's table, on the exact values of the doubles, with a stated `plus_minus`, and the implied conditions the read applies (`declarations.md` section 4.1); a result's condition entries |
| `read.py` | the request's own check (step 0), its implied conditions, nominals and extrapolations included, an acceptance of a kind a read does not take refused; the read of a value field, steps 8 to 13 (`read_value_field`), an extrapolation applied at step 11 to a table read outside its readable range (S3c) and a nominal at step 13, and of alternatives at step 7 with no pick and no overlay (S4a), a table alternative set aside, kept or refusing the field by its reasons at step 11 (S4d), each reason found reading one carrying its index; the result (`ReadResult`, `FieldRead`, `ProvenanceSummary`), its members as stored by the generated shapes, each count and index an integer, the acceptances it applied (`applied`), the stored value it rests on (`resting_on`) and whether it resolved its record (`resolved`), each outside its JSON; picks and overlays are not built yet |
| `evaluate.py` | a table at an operating value of its axis (`record_format.md` section 6, table items 3 and 4; `read_side_contract.md` section 5): its readable range, its edges, the knots that bracket the value, and the table's number there, the exact value rounded once to the nearest double, ties to even (a log-log one under the one assumption `loglog` states); step 11 uses it, in `read.range_report` (its reasons and report) and `read.form_range` (the table's number, at the operating value or, under an extrapolation, at the readable range's nearest end) |
| `declarations.py` | `declarations.md` section 1: a consumer's declaration checked on its own, by hand, against `SHAPE`, the table of its shape place by place (held to the text and to `schema/0.1/declaration.json` by `tests/spec_sync/test_declaration_shape.py`); each rule one function naming its cases (the shape, tokens and names, BC-048; reasons, BC-004 and BC-005; locations, BC-037; labels, BC-050; items 7, 8, 12 and the `population_level` rule, BC-040, BC-044, BC-043 and BC-051), every fault found, one refusal per fault by the precedence rule; a declaration that passes, typed (`Declaration`, `ModelEntry`, `Requirement`, `Acceptance`) |
| `report.py` | the build's report (section 2) and a refusal of the declaration (`BuildRefusal`): a refused declaration's report, its refusals alone, its declaration and consumer as given; a passing one's, the records a read resolved, the results (`BuildResult`: the model, the record, the field, the read, the joined reasons, the worst status and the verdict, with `value`, `end_value` and `initial_value`) and the acceptances unused (`UnusedAcceptance`); `refused`, `result()`, the JSON (`watches` left out until S7a-4, its property raising) and `status_lines()`, each reason nothing covers beside what would cover it by section 4.2's table |
| `acceptance.py` | the build's verdict by its terms (section 2): `COVERAGE`, section 4.2's table; `located_at`; what covers a reason (`_covers`, by the rows listing it, whatever its `alternative`); `judge` (`accepted`, `accepted_by` with what the read applied, `not_accepted`); `unused`, per model; a waiver naming a label raises where it would cover, until S7a-2's label trust |
| `build.py` | `check_build`: the claims, the declaration's own check, a report of its refusals; before any read, `NotImplementedError` naming what a later piece reads (a pick or an overlay, S7c; a non-empty `target` or `combinations`, S7a-3; `trainable`, S7a-4); the results over records (section 2), each of the build's own request (item 7) with the acceptances it gives the read, those the read applied mapped to the model's indexes and checked against the build's terms; the build's own reasons (`no_requirement`, `label_mismatch` against the label stored on the value a result rests on, `not_reviewed`), the worst status, the verdict and the report |

The conformance cases HS-001 to HS-003 check the hash end to end; the plain-read cases, HS-010 and HS-011 the
read, through step 13 for a constant, an interval, a composition and evidence (`tests/conformance/`). The table evaluation cases, which OpenMaterica claims none of, check
`evaluate.py`'s numbers and refusals by a unit test (`tests/unit/test_evaluate.py`).

## Invariants

- **Results, never exceptions, for content.** `parse` gives a value or `malformed` for any bytes, running out
  of stack or memory included, and a read gives a result for any request and any records. An exception means
  a misuse of the Python API (`canonicalize` given a value `parse` would never give; claims no reader makes, a
  suite that does not exist or claims without plain read) or a step not built yet: a read whose answer a later
  step would decide raises `NotImplementedError` rather than give one, whatever else is wrong with the request
  (`tests/property/test_read_properties.py`, `tests/unit/test_read.py`). The build is alike: a declaration
  gives a report of its refusals or of its results, and raises only where a piece not built yet would change
  its answer (`tests/unit/test_declarations.py`, `tests/unit/test_build.py`).
- **A request is JSON text or a value.** Text is a `str` or bytes-like (`bytes`, `bytearray`, `memoryview`),
  read like a record's bytes; a `str` is always text, as a JSON string is never a request. Any other value is
  read as the JSON text `json.dumps` writes of it.
- **Every number is a float.** An integer reads as the nearest double; `JsonValue` has no `int`, and
  `canonicalize` refuses one. A request given as a Python value is read through JSON text, so its integers too.
  (The reader's properties compare types exactly; `tests/unit/test_canonical.py`.)
- **Stored JSON is never mutated, and never shared.** `hashable_view` builds new containers and leaves its
  argument as it was (`tests/unit/test_hashing.py`); a `Record` keeps the value its bytes parse to as it is;
  what a result returns from a record is a copy, and so is each result's JSON (HP6,
  `tests/property/test_result_properties.py`).
- **Identifiers match in full**, by `re.fullmatch` with character classes written out
  (`tests/property/test_version_properties.py`).
- **Step 8's shapes, by hand and in the schemas.** `value_shapes.py` and `fields.py` agree with the writer
  schema's value-field `$defs` and the generated reader `$defs`, but for listed exceptions of the kinds no JSON
  Schema states (T1, `tests/spec_sync/test_t1.py`); a member's status tokens are read from the generated
  shapes, never written out again.
- **One envelope check, in two forms.** `envelope.py` and `schema/0.1/record.reader.json` accept and refuse
  the same records (`tests/spec_sync/test_envelope.py`, `tests/property/test_envelope_properties.py`).
- **Standard library only**, with `materica.shapes`, itself standard library only, and, for type checkers
  only, `typing_extensions`; relative imports are checked like absolute ones (`tests/unit/test_source_files.py`).
