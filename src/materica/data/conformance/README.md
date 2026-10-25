# Conformance cases

The conformance cases of the OpenMaterica specification (`docs/specification/`). The rules for reading a case
are in the specification's README ("Case files", "Variants", "Claims", "Operations"). They hold wherever this
file or the ones beside it differ. These files only help you find your way.

## What is here

| Directory | Suite | Specification | What its cases check |
|---|---|---|---|
| `plain_read/` | plain read | `read_side_contract.md`, `record_format.md`, `provenance.md`, `uncertainty.md` | a read of one field of one record: the request's own check; steps 1 to 5 of the read (resolve, version, validate, hash, type); steps 6 to 13, which read the value (field, form and tokens, units, conditions, origin, `want`); and `list_records` |
| `hash/` | hash (HS) | `record_format.md` section 9; `read_side_contract.md` steps 1 and 4 | the content hash, as an operation on any JSON value, and the reads of a reader that recomputes it |
| `table_evaluation/` | table evaluation (TE) | `read_side_contract.md` section 7; `record_format.md` section 6 | what a consumer's own evaluator of a table returns: the value, `in_range`, the derivative by side, and the refusal at or across an edge, at each precision |
| `record_checks/` | record checks (RC) | `page_text.md`; `provenance.md` section 4 | what a checker of records finds and lists: page-text documents, the place of a quote in a copy, the comparison of a quote with its place, the copy hash's form, and the `quote_sha256` vectors |
| `build_checks/` | build checks (BC) | `declarations.md` | what a build gives a consumer's declaration over records: so far, the declaration checked on its own and refused at build, each refusal its rule's case and a JSON pointer into the declaration; and, for a declaration that passes, the results over the records it lists, what accepts each, and the acceptances unused |

The tree grows with the implementation. The plain-read cases cover the read through step 13 for the forms
0.1.0's fields use: constant, table, interval, composition and evidence, and reads under an extrapolation.
Overlays, picks and the specification's other suites come later. The build-check cases so far are a declaration
checked on its own, which the build refuses before any read, and one over records that passes, with its
results, what accepts each and the acceptances unused. A case file may arrive before the code that runs it:
`tests/spec_sync/case_steps.json` names the implementation step each one needs, and until that step is done
the tests report the file as not yet runnable, never as passed.

Each suite directory holds:
- `cases/<case id>.<variant>.json`: one file per arm of a case (a "variant"). For example,
  `PR-320.operating_unit_kelvin_sign.json` is case PR-320 (a row in the specification), in the arm that
  writes `K` with U+212A KELVIN SIGN.
- `inputs/`: the files the cases supply, each once, whichever cases use it.
- `CASES.md`: one row per case file, grouped by case id under the specification's row for that case. It gives
  what the arm tests, the step at which the read ends, and the expected answer. Start there.
- `README.md`: the suite's fixtures and input families, and what its cases cannot show.

## Reading a case

```json
{"case": "PR-320", "variant": "operating_unit_kelvin_sign", "suite": "plain_read", "schema_version": "0.1.0",
 "inputs": {"records": ["water_fixture.json"]},
 "request": {"target": {"record": {"id": "conformance/water_fixture", "version": "1.0.0",
                                   "content_hash": "sha256:c21a…"},
                        "field": "fluid.dynamic_viscosity"},
             "operating_conditions": {"temperature": {"value": 310.15, "unit": "\u212a"}},
             "requirement": {"want": "value",
                             "conditions": {"temperature": {"tolerance": {"value": 1.0, "unit": "K"}}}}},
 "expected": {"status": "not_met",
              "reasons": [{"code": "request_unit_mismatch", "condition": "temperature"}]},
 "compare": {"members": ["status", "reasons", "value"]}}
```

The operating condition's unit is U+212A KELVIN SIGN, written here as an escape; the case file holds the
character itself. The tolerance's unit is the letter `K`. Units are compared code point for code point, so the
read is refused at step 0. Members:

| Member | Meaning |
|---|---|
| `inputs` | the files supplied, by name in the suite's `inputs/`: `records` (the sources a read resolves against), `value` (the one file a `content_hash` operation hashes), `request` (a request file, used only where the request itself must break the JSON rules) |
| `request` | the read request, or `{"operation": "content_hash"}` / `{"operation": "list_records"}` |
| `expected` | the members of the result the case compares |
| `compare.members` | which members are compared. One named here but left out of `expected` must be absent from the result, as `value` is above: a refused read carries no value. A member whose answer the specification leaves open is left out of both (`status` and `reasons` in a few `no_pick` arms) |
| `claims` | only on cases whose answer depends on which suites the reader claims (`{"hash": true}`) |

Reasons are compared as a multiset of code and condition, so order does not matter and a repeated reason
fails. `labels` are compared as a set. `detail` is never compared.

A runner runs only the cases of the suites the implementation claims, and of those, only the variants whose
`claims` agree. A case passes when at least one of its variants ran and none failed.

## The fixtures are illustrative

Every record and document here is in the namespace `conformance`, which the specification reserves for
conformance fixtures (`record_format.md` section 7 item 1). Their values, provenance and sources are
illustrative. They are chosen to exercise a rule and state nothing about any material, whatever their tokens
say (`measured_by_contributor`, an `example.org` source). The water values are near textbook ones for
familiarity; they are not a measurement and were not checked as one. Never copy a fixture into a library. A
record check flags a `conformance` record given from outside a conformance tree, a directory `conformance`
whose parent is `data` (RC-121).

Each suite's inputs are self-contained. The hash suite's `water_fixture.json` is not the plain-read suite's,
although both are `conformance/water_fixture` 1.0.0; they differ in their bytes and their hash, and no case
supplies both. That is the specification's point about identifiers: a record is pinned by its hash, not by its
id and version alone.

## Inputs are byte-exact

Many inputs are broken on purpose: a byte-order mark, UTF-16 and UTF-32 text, ill-formed UTF-8, a repeated
member name, `NaN`, numbers that overflow, nesting 65 or 100000 deep, a CBOR, TOML or YAML copy of a record.
Some hold characters an editor may rewrite: U+212A, a decomposed `é`, noncharacters. `.gitattributes` marks
this tree `-text`, so git never converts it. Never reformat, re-save or "fix" an input. Case files themselves
are strict JSON (`record_format.md` section 1 item 6).

## How the cases were made and checked

The cases were drafted with AI assistance (Claude, Anthropic) from the specification text alone, by passes
that saw no implementation; none existed. The cases that end by step 5 were then checked by separate passes:
- every content hash computed by two independent RFC 8785 implementations (Python `rfc8785` 0.1.4, Node
  `canonicalize` 2.0.0) and recomputed by a third, written for the check;
- every expected answer compared with an independent reference model of the read procedure, written from the
  text;
- each suite run against deliberately faulty readers, one fault each, to show that every rule a case tests can
  fail. The few that cannot are named in each suite's README.

The cases that read values (steps 6 to 13) were written the same way, from the text alone, before any code
for those steps existed. Their content hashes and pins are checked by the two implementations above, and the
specification sentences each answer rests on were checked against the text. Two separate passes then checked
them: an independent reader written from the text, run under every configuration of claims each case allows,
and a scratch reader of the text run with about 300 seeded faults, one at a time. The first round found one
wrong answer (a fixture that kept a label its arm did not test), six points the text left open, which the
maintainer settled in the text, and 91 faults that no arm refused. After the arms added for them, and for a
seventh point their rerun raised, the independent reader agrees with every answer, and every fault but twelve
is refused by some case: nine that no input can tell from the text, two whose arms wait for answers the text
leaves open, and one the scratch reader never switched on. Every read compares every member of its result;
where the text leaves an answer open, no arm is written (the suite's `README.md` lists them).

The cases of tables and extrapolations (S3) were written the same way, from the text alone, before any code
for tables existed. Their content hashes, pins and quotes are checked as above; no independent pass has
checked their answers yet.

The record-check cases (C0) were written the same way, before any code that runs them; `record_checks/README.md`
says how their hashes and answers were checked, and what they cannot show.

The build-check cases (S7-cases-1 and S7-cases-2) were written the same way, from the text alone, before any
code that runs them, by a pass shown no implementation; `build_checks/README.md` says how their answers were
checked, and what they cannot show.

The scripts that first generated these files are not part of the repository. The files are the source.

## Changing a case

1. Edit the case file or the input. Never reformat an input you did not mean to change.
2. If you change a record, recompute its `content_hash` (`record_format.md` section 9), and every pin that
   names it: search the suite for the old hash.
3. Update the case's row in the suite's `CASES.md`.
4. Make sure the arm can fail: a reader with exactly the fault the arm targets must give a different answer.
5. If the case's answer changes because the specification changed, the change belongs in `changes.md` too.
