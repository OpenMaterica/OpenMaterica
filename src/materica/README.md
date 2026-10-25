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
  refusals. A declaration that passes is read over its records (section 2), and `check_build` then raises
  `NotImplementedError` until S7a-2b judges the results and gives the report; before any read it raises for
  what a later piece reads (a pick or an overlay, a non-empty `target`, `combinations` or `trainable`).
