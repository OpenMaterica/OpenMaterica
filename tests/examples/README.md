# Example records and the quickstart

| Test | Checks |
|---|---|
| `test_example_records.py` | each record in `examples/records/`: the writer and reader schemas take it (both JSON Schema libraries, `spec_sync/schemas.py`), the envelope checks and its content hash, and the record checks it can be given alone (its identifier in the namespace `example`, each field's required conditions, its label by RC-122 (the label its row names for its form and no other, with a `label_basis` beside it, whose shape the writer schema checks), every review `not_checked`); each number in it, outside its provenance, against a table of its source's number, the conversion and the place in the source, and the statements schema 0.1.0 keeps only in words; the note that the examples are not yet fully human-reviewed, in `README.md`, `examples/README.md`, the quickstart and each record's `card`; and what a read of each gives at this release, as those documents say: `met` for the plasma, for the water, the one alternative left where the other is set aside (`met` for the density, `unknown` with `condition_unstated` naming that alternative for the viscosity, whose shear rate is unstated) and `no_pick` where both alternatives meet, each viscosity alternative's `condition_unstated` beside it, each water request accepting the test method the values state (`reference_formulation`), which a request naming none leaves `condition_unchecked` and one accepting only measuring methods refuses (`condition_not_accepted`), the plasma, measured, `met` with its method and `unknown` (`condition_unstated`) with it removed, by a request that also accepts `reference_formulation`, and `not_met` (`condition_not_accepted`) by one that accepts `reference_formulation` alone, and for N45's interval `unknown` with its bounds under `want: bounds` and `not_met` (`want_mismatch`) under `want: value` |
| `test_quickstart.py` | `docs/user_guide/quickstart.md`, its `pycon` blocks run in order as one doctest beside a copy of the water example, every example run (none skipped) and every output compared |

The record, source and note checks have controls that must fail: a record given a token the writer refuses, a
structure the reader refuses, a value changed without its hash, a reserved namespace, a malformed identifier
or version, a required condition, a label or a review dropped, a label on a field whose row names none, a
label's basis dropped (on a water alternative, and on the plasma's field, which holds no alternatives) and a
label's basis that breaks its shape; a number changed in each record, a number with
no source, a statement in words dropped, a sourced member removed; each document with its note's lines
removed; and the quickstart with one shown output changed, four times, and with a line of it skipped. The read
outcomes are pinned as exact values, with no control of their own in the suite, so a pin is as sharp as its
assertion: the water pins compare the status, every reason with its `alternative`, and the value or each
alternative's value.

Limits. The record check makes the record checks a reader of this release can make alone (identifier and
version, required conditions, the label and its basis, every review `not_checked`) and leaves RC-020, RC-037, RC-043,
RC-045, RC-051, RC-052 and RC-058 to `materica check`; the plasma record breaks RC-058 (the pull request's
open point 7). The note check holds each document to carry the note's three phrases and cannot see a
sentence elsewhere that contradicts them.

S4a (2026-10-19) updated the water pins, `examples/README.md` and the quickstart, once the one alternative
left was read; the test method `reference_formulation` (2026-10-20) updated them again, once the water values
stated it. When S4b lands (picks), no pin here fails, since no pinned request carries a pick; the prose that
says picks are not read yet goes stale instead and is updated by hand. When S3 lands (tables,
extrapolation), no pin here fails, because no example holds a table and no pinned request carries an
extrapolation; the prose that says tables are not read yet goes stale instead, in the quickstart's opening
note and its "not read yet" list, in `examples/README.md` and in the README's documentation table, and is
updated by hand.
