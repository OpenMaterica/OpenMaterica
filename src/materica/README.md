# `materica`

The Python package. It implements the reader side of the OpenMaterica specification (`docs/specification/`).
The specification is normative: where this code and it differ, the code is wrong.

## Layers

The package is built in layers (AD 7.1), and a module imports only from its own layer or a lower one.

| Layer | Directory | What it holds |
|---|---|---|
| L0, schemas | `schema/`, `shapes.py` | the JSON Schemas (`schema/README.md`), and the JSON shapes as TypedDicts generated from them |
| L1, data | `data/`, `schema/0.1/vocabulary/` | the specification's conformance cases and the inputs they supply (`data/conformance/`, with their own `README.md`), and its vocabulary, published with the schemas |
| L2, core | `core/` | strict JSON, the canonical form and the content hash; identifiers, the envelope checks and the read up to step 5; Python's standard library only (`core/README.md`) |
| L4, readers | `io/` | files into the core's types (`io/README.md`) |

The authoring tools (L3), the sampling helpers (`sample/`, L5) and the command line (`tools/`, L6) arrive in
later steps. `tests/unit/test_source_files.py` walks every module's imports: a module imports only its own
layer or a lower one; `core/` imports only the standard library, itself and `shapes.py`, which imports only the
standard library; and nothing imports `materica_authoring`.

## What holds across the package

- No run-time dependency (AD 7.2): the built wheel declares none (`scripts/check_wheel.py`).
- It is typed (PEP 561) and ships `py.typed`. `mypy --strict` and pyright in strict mode pass over it, and a
  consumer's code type-checks against the installed wheel (`tests/typing/`). `shapes.pyi`, which type checkers
  read in place of `shapes.py`, marks what a read returns read-only (PEP 705).
- Everything under `data/` and `schema/` ships in the wheel byte for byte, since the conformance inputs are
  byte-exact and the reader loads the vocabulary (`scripts/check_wheel.py`).
- Generated files are never edited by hand. `scripts/` regenerates them and CI fails on any difference: the
  vocabulary from the specification's tables, the reader schema and the shapes from the writer schemas
  (CONTRIBUTING, "Changing the schema").
- `__init__.py` holds the public API built so far: `check_build`, `content_hash`, `load_records` and `read`.
  `check_build` checks a consumer's declaration on its own (`declarations.md` section 1) and reports its
  refusals. A declaration that passes is read over its records and judged (section 2): its `BuildReport`
  holds the records a read resolved, one `BuildResult` per model, record listed and field read (the read,
  the build's own reasons joined to it, the worst status, `accepted`, `accepted_by` and `not_accepted`, and
  `value`, or under an extrapolation `end_value`), the acceptances unused, `refused` and `status_lines()`,
  the lines `materica status` will print. `check_build` raises `NotImplementedError` where a later piece
  would change its answer: before any read, for a pick or an overlay (S7c), a non-empty `target` or
  `combinations` (S7a-3) or a non-empty `trainable` (S7a-4); and where a waiver naming a label fits a reason
  of a result that label trust could still accept, which S7a-2's label trust judges after 0.1.0.dev4.
  `BuildReport.watches` raises until S7a-4, and the JSON report leaves `watches` out rather than give it empty;
  `BuildReport.combinations` is added with S7a-3, which builds the combinations, and the report has no such
  member until then.
