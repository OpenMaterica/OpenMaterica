# Contributing to OpenMaterica

OpenMaterica is at the design stage. These rules apply from the first code commit; the reasons for them are in
[`DOCUMENTATION_ARCHITECTURE.md`](DOCUMENTATION_ARCHITECTURE.md), section 15. The material library will
live in a repository of its own; until it exists, its rules are kept here.

## Constraints

1. **Sign off every commit.** Use `git commit -s`. The sign-off certifies the
   [Developer Certificate of Origin](https://developercertificate.org/): you wrote the change, or have the
   right to submit it under Apache-2.0. A pull request with an unsigned commit is not merged. The design
   commits made before the first code are exempt.
2. **Apache-2.0 for code.** Every code contribution is licensed Apache-2.0. Do not add a runtime dependency
   under a copyleft licence.
3. **No simulator or ML-framework dependency at runtime.** Not MIME, MADDENING, JAX, PyTorch, Warp or Isaac.
   The core depends on Python's standard library only. `jsonschema`, USD and numpy are optional extras
   (`openmaterica[check]`, `openmaterica[usd]`, `openmaterica[sample]`), and code must work with whatever USD
   build is installed, including the one Isaac Sim ships. An MCP library comes only with `openmaterica[mcp]`:
   no distribution's base install brings one, and no sibling imports one.
4. **Keep the read side implementable without OpenMaterica code**, with a JSON parser or with USD; verifying a
   content hash also needs an RFC 8785 serialiser and SHA-256. Compute on the write side and store the
   result. Readers only read numbers, interpolate tables, evaluate power laws, apply the mixing rules their
   consumer declared, and evaluate model families with their own implementations after verifying check
   points.
5. **SI units in stored values.** Convert in importers and adapters, never in the stored data. Store
   attenuation as an amplitude coefficient in nepers per metre (UCUM `/m`); convert a source's decibels or
   intensity coefficient on import, and record the source's unit and basis. Store parameter sets only in their
   family's convention; conversion to a solver's convention belongs in an adapter or exporter, with vectors.
6. **No value without provenance** (see "Adding or changing a library material").
7. **The specification is normative.** A change to it needs conformance cases in the same pull request.
8. **Do not hand-edit generated files.** USD layers, material cards and the index are generated from the
   plain records.
9. **No claims beyond the data.** Library values are taken from cited sources, or are fits to cited data,
   labelled by origin. Biocompatibility fields record test evidence, never a safety claim or a device's
   status. Do not describe a value as validated for a patient, or as suited to any use.
10. **Never delete an anomaly entry.** Resolve it.
11. **No network access and no code execution from data**, at import or when reading files.
12. **Keep the anomaly registry in MADDENING's schema.** Do not add fields. CI checks it with
    `scripts/check_anomalies.py`, which stands in for MADDENING's validator, whose packaged command reads
    each component name as a Python name; nothing in the package imports MADDENING. The registry's version field is
    `materica_version`, which MADDENING's validator accepts from MADDENING 0.4.0, and it is the package's
    version (`DOCUMENTATION_ARCHITECTURE.md` section 8.1).
13. **Fail closed.** Readers refuse an unknown family or version, a failed check point, a request to
    sample an undeclared uncertainty structure, an attribute that was not authored, an unknown token in an
    enumerated field, a referenced record of an unknown type, interpolation across an edge, and a value
    outside its range unless the consumer declared an extrapolation with its basis. Never add a fallback that
    guesses.
14. **Check points and a convention witness on every shipped model parameter set.** Check points are computed
    by the family's reference implementation; never type them in. A reference-only set ships none (they would
    publish its parameters); a user's fill-in, an overlay in the user's own namespace, is checked against
    the witness instead. The witness is a response the
    source itself reports, independent of how the parameters were obtained (for a fit, a held-out datum);
    without one, a parameter set is not admitted to the curated library.
15. **Family versions are frozen.** Any change to a released definition or its vectors is a new version.
16. **Ship nothing non-redistributable.** A value from a source whose redistribution status is not
    permitted, or is unknown, is reference-only. Every pull request that adds data carries the data
    attestation.
17. **Data and code licences are separate.** Curated library records are under CC0-1.0, stated on each
    record. A quote kept as evidence is the source's text and is not relicensed.
18. **Shipped USD layers are self-contained**: no composition arcs and no asset paths.
19. **Static releases.** No feature may require a hosted service, and nothing is fetched from the network
    unless the user asks. No tool the MCP server loads may make a network request. Two tools go online, each a
    command a person runs with an explicit flag, which the MCP server never loads: registry drafting, and
    source discovery and acquisition.
20. **No model on the read side.** No language model in a reader, in `materica check`, in a release build
    or in any consumer's build. OpenMaterica calls no model and holds no keys.
21. **Quotes and human review.** Every value in the curated library that was extracted from text or a
    table carries its quote (or, if the legal review rules that quotes may not ship, the quote's hash, the
    text staying with the curator), locator, document identity and copy hash, whoever or whatever extracted
    it. A
    value a model helped draft also carries an assistance record. No value enters a release without a human
    review record.
22. **A model never decides** a tier, a redistribution status, a unit conversion, a check point, a witness
    or a fit result.
23. **Records hold facts; consumers declare choices.** No record, card, check or default says where, in what
    state or in which regime a model applies, which stand-in is acceptable, which mixing rule to use beyond
    the identities, or which of competing values wins.
24. **Nothing stands in for a value without saying so.** No fallback values on physical attributes; no
    nominal, distribution or extrapolation the source does not give, unless a consumer declares it with its
    basis and the run records it as the consumer's; an unstated condition is unknown, never met; every
    spread says what it represents.
25. **A check is reported for what it can show.** A witness is independent of how the parameters were
    obtained, or the record says "no independent witness". Check points are not presented as evidence about
    a value. An attestation by an interested party says that it is one.
26. **The core never runs inside a consumer's computation**: its simulation step, compiled program or
    gradient path. Consumers write their own code for anything they read, interpolate, mix or evaluate
    there, and verify it against conformance data, golden vectors and check points. The core may run at a
    consumer's build or setup (the reader, the requirement checks, the material input sheet, label-volume
    fractions, the reference sampler), and is SOUP in a product that does so. Do not add core code meant to
    run in a consumer's step, loop or gradient.
27. **Every record has a record type.** OpenMaterica defines `material`, `interface` and `overlay`. A reader
    skips a type it does not know when listing records, and refuses it when a record of that type is
    referenced. OpenMaterica curates only material and interface records. A type of your own lives in your
    namespace; its envelope and value machinery are checked, never its body, and the first such type is
    specified only after a consumer has prototyped one.

## Code

<!-- REUSE-IgnoreStart -->
- Every source file starts with an SPDX licence header (`# SPDX-License-Identifier: Apache-2.0`); JSON data
  files are covered by the repository's licence.
  <!-- REUSE-IgnoreEnd -->
- The package is typed and ships `py.typed`. `mypy --strict` and pyright both pass over `src/materica`. No
  public function returns an object from `pxr`, and every `pxr` call in `materica` goes through
  `io/usd/_pxr.py`.
- `pyproject.toml` states the licence as an SPDX expression with its licence files (PEP 639) and keeps
  development tools in `[dependency-groups]` (PEP 735); releases are published with attestations (PEP 740).
- These rules are `DOCUMENTATION_ARCHITECTURE.md` section 15, constraints 28 to 30.
- Supported Python versions: 3.11 and later, and every Python that is not at end of life and that a named
  consumer or engine needs in-process. CI runs each one.

## Development

The project uses [uv](https://docs.astral.sh/uv/). `uv.lock` pins the development tools, and CI installs them
with `uv sync --locked`, so a lock file out of date with `pyproject.toml` fails it.

```sh
uv sync                                  # .venv with the package, editable, and the dev group
uv run pytest -n 12 --dist worksteal     # every test; the summary counts the conformance cases
uv run ruff check && uv run ruff format --check
uv run mypy && uv run pyright
```

Twelve workers suit a machine of 8 performance cores and 24 threads, as the maintainer's; use `-n 8` when
another heavy job shares it. Always `--dist worksteal`: xdist's default hands a worker a file's tests together,
so a file's slow tests wait on one worker (`tests/README.md`, "Running").

Every commit must build, type-check, generate and collect on its own. On a pull request CI checks each commit
but the head by itself, on Python 3.15: the fast checks above, the wheel, every generator's `--check`,
`freeze_schema.py --check`, `pytest --collect-only tests` and the specification-sync tests (`tests/spec_sync`).
The full suite runs on the head alone, on every Python and at the `ci` profile (maintainer, 2026-10-21;
`.github/workflows/README.md`, the `commit` job). So while working, run the tests of what you touched and of what
it feeds, and leave the rest of the stack to CI.

Property tests take their depth from `MATERICA_HYPOTHESIS_PROFILE`: `dev` (the default), `ci` or `deep`
(`tests/README.md`). Fuzzing needs Linux x86_64 and Python 3.12 to 3.14: `uv sync --group fuzz`, then
`tests/fuzz/README.md`. Without uv, `pip install --group dev -e .` (pip 25.1 or later) installs the same
tools, unpinned.

## Before asking for review

A review should spend its time on what only an independent reader finds. Eight of this repository's reviews, read
for this section, kept finding the same things first, and a builder can check most of them mechanically. These checks add
to the review and to CI and lower no bar. `scripts/pre_review.py [BASE]` (`origin/main` where none is given)
finds the files you changed, from the merge base to your working tree, runs the checks below that apply to them
and prints each with the paths that selected it; `--list` prints the plan alone. Its fast stage comes first:
fix what it finds before any test runs. It runs the checks that apply, not every check; CI runs them all, on
every Python, and its result is the one that counts. Every `uv run` it plans is `--locked`, and `uv lock
--check` comes first: a lock file out of date with `pyproject.toml` is refused, never rewritten behind you. A
change it cannot map to a test (a Python file no test imports, a file under `tests/` in no group of tests)
selects the whole of `tests/unit`, and the plan says why. It does not run the site job (the site staged as Pages
stages it, and its links and images checked), the fuzz job, or the two controls of the wheel check. Its last
stage, `--stage whole`, which runs only when asked for, runs every test of the tree but the property modules
(`LEFT_TO_CI`, each with why; CI's shards run them): run it once, at your head, after the other stages pass and
before you hand back, so that a directory no targeted check reached (`tests/reference`, say) runs too. The
measurements a property piece makes (floors, kill drift, regions, a fuzz control's rate) run on CI as a matrix
(`tests/README.md`, "Measurements on CI").

| What it catches | Check |
|---|---|
| a commit without your sign-off; a private name or path in a file or a message | `python3 scripts/check_signoff.py BASE HEAD`; `python3 scripts/check_confidential.py --messages BASE..HEAD` |
| a generated file edited by hand, or a source changed without regenerating; a kill count of `tests/property/README.md` that is not the recorded one, or a kill after the 500th example; a released schema file changed | each of `scripts/gen_vocabulary.py`, `gen_reader_schema.py`, `gen_shapes.py` and `gen_kill_counts.py` with `--check`, on Python 3.11, which `uv run --python 3.11 python scripts/gen_shapes.py --check` does (`uv run python scripts/gen_shapes.py --check` fails on the project's 3.15: the shapes' generator does not run there); `pre_review.py` runs all four on 3.11 in an environment of its own, so the project's `.venv` is not rebuilt; `python3 scripts/freeze_schema.py --check` |
| a kill points marker of `tests/property/README.md` for a group the kill counts' tests do not name, or one they name gone | `uv run pytest tests/unit/test_gen_kill_counts.py`; `pre_review.py` runs it with its fast checks where a marker was added or removed |
| lint, format, types | `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pyright` |
| a wheel that lacks a file it ships, or that a consumer's type check refuses (`py.typed`, the stubs, the package data) | `uv build`, then `uv run python scripts/check_wheel.py dist/*.whl` and the consumer snippet's `mypy --strict` and `pyright` against the installed wheel, as the static job's steps do; `python3 scripts/pre_review.py --wheel-check` runs them in a temporary directory |
| a reference to a section, item or title that is not there; a quote of the specification changed or lost; a case tag or table row with no counterpart | `uv run pytest tests/spec_sync/test_references.py tests/spec_sync/test_value_fields.py tests/spec_sync/test_unknown_member_positions.py` |
| a name reused at a place, or one slip from another | `uv run pytest tests/spec_sync/test_name_overlaps.py tests/spec_sync/test_name_overlap_safeguards.py` |
| a feature audit that fails by chance, or that does not fail when its feature stops being drawn | `MATERICA_HYPOTHESIS_PROFILE=ci uv run pytest tests/property --shard NAME -n 12 --dist worksteal` for your module's shard (`SHARDS` in `tests/conftest.py`), and `uv run pytest tests/unit/test_audit_controls.py tests/unit/test_audits.py` |
| a mutant a property no longer kills, or a mutant table that no longer matches its module | the same shard run, which holds the group's mutant searches and `test_*mutant_table.py` |
| a kill point that moved, a mutant search not recorded, or a README row naming a search that does not run | `uv run python scripts/gen_kill_counts.py --measure`, which runs every mutant search (about 45 seconds on 12 workers) and checks its kills against `tests/property/kill_points.json`; `--measure --record` records them and writes the README's counts. An edit to a `kill` helper (the function that runs a mutant search), or a Hypothesis upgrade, re-seeds hundreds of searches at once; the check names it, and `--measure --record` is the cure |
| a table of `pre_review.py` (the tests that read the whole tree, the data files tests open) that a test you wrote or changed now opens or lists and the table misses | `MATERICA_TRACE_SELECTION=1 uv run --locked pytest tests/unit/test_pre_review.py -k trace`: the trace test runs the whole suite once, about a minute of wall time and three of CPU, so it is skipped unless that variable is `1`; CI sets it in one job, the `tests` job on Python 3.15, and `pre_review.py` does not set it |
| a head, base or commit count in the description or a commit message that git does not show; a figure in the description or the CHANGELOG lines added that no recorded measurement holds; a specification sentence that words a ruling otherwise | `python3 scripts/check_claims.py check origin/main --description FILE --rulings FILE`, after `check_claims.py record` for each figure measured (`scripts/README.md`); run elsewhere than the builder's worktree, at the gate, it takes the builder's facts file with `--facts`; `pre_review.py` does not run it, since it needs the description. CI runs it too, in `claims.yml`, on every push to a pull request and every edit of its description: a git fact that git does not show fails that check, a figure with no recorded fact is printed as advice, and the rulings are not read, so the builder's run with `--rulings` stays theirs |
| a script, a workflow or the build broken | the script's own test in `tests/unit` (`test_<script>.py`; `test_generators.py` for the three generators, `test_check_confidential.py` for `pre-push`); `tests/unit/test_ci_workflows.py` |

The rest only you can decide. Read your change once as the reviewer will:

- **A mutant dies where it names.** Run each and read the assertion it fails at. A guard that fires first (`the
  read raised`, a totality check) means the check the mutant is for never ran.
- **The code you changed has a hand mutant that dies.** Break each arm of what you changed by hand (a comparison, a
  default, a branch, a status, a refusal), one at a time, and see a test fail at an assertion made for that arm; a
  mutant that survives is a test missing. Where `tests/README.md` describes mutant tables on CI, ask for them
  to run there, not on your machine.
- **A guard or control can fail.** Break what it guards, one fault at a time, and see it fail; then try the faults
  it was not written for: a neighbouring spelling, another locale, a newline in a value, a `continue-on-error`.
- **The draws reach what the mutants need.** Take a variety out of a strategy and see whether a mutant then
  survives. A rule pinned in most runs by chance is not pinned. `scripts/input_coverage.py run NAME` takes
  out each, one at a time, for a selection of `tests/property/input_coverage_baseline.json`, and fails on a
  cut no test notices that the baseline does not list (`tests/property/README.md`, "Every draw is held").
- **A number declared is a number measured.** A least share, a chance, a timeout and a rate each rest on runs
  you can name, at the profile and on the machine they apply to. Three local runs do not show 1e-6, and a local
  rate is not CI's: ask for the repeat workflow (`tests/README.md`).
- **A claim says what the tests show.** In the pull request, the CHANGELOG and each commit message, say what is
  bounded and what is estimated. `check_claims.py` holds the git facts and the figures it can read to git and to
  the facts recorded; a prose claim, a count written in words and what a figure counts are yours to check. Recount every figure by what counts that thing: a test is not a case file, nor a
  Hypothesis example, nor a line of a trace. Where you write "neither X nor Y", name the control that could have
  shown one.
- **A citation says it.** The line is right, the quote is whole (a check may stop at an inner `"`), and the
  section cited holds it in the commit that cites it. Check a `file:line` reference by opening the line.
- **The code agrees with the text, arm by arm.** For each refusal the text lists (a slip, a member of the other
  kind, a token known for another place), the code gives the status and code the text names.
- **A fact is written once.** Search for the words, names and numbers you changed in comments, READMEs, workflow
  headers and this file, and refer to the one place that states each.
- **A mutant's README row is current.** The row of each mutant you changed names the assertion it dies at; its
  kill count is written by `scripts/gen_kill_counts.py` from the recorded kill points, never by hand.
- **Each commit stands alone.** No call lands before the function it calls: each commit builds, type-checks,
  generates and collects on its own, which CI's per-commit job checks; the full suite runs on the head.

## Confidentiality

This repository is public. It never names the maintainer's private projects, and never carries a private path:
an absolute home directory, a session scratchpad, Claude Code's temporary directory, or the private planning
directory beside the repository, which only `CLAUDE.md` names. `scripts/check_confidential.py` checks every
tracked file, and CI also checks the message of every commit a pull request or a push brings, and a pull
request's branch name.

The names cannot be listed here, and plain hashes of them would not hide them, since hashing a word list
recovers short words. So `scripts/confidential_digests.txt` holds their HMAC-SHA256 under a secret key, 64
hexadecimal digits, which CI reads from the repository secret `CONFIDENTIAL_SCAN_KEY`. Without the key, as on a
fork, the paths are checked and the names are not, with a warning. A key the digests were not made with is
refused. A finding gives its file and line, and a term's first letter and length, never the term.

A text file is read as UTF-8, a byte that is not read as a replacement, which keeps every ASCII word of a text
in any ASCII-compatible encoding. A binary file, or a text in UTF-16 or UTF-32, is read by its printable runs
of four ASCII characters or more, as bytes and as UTF-16 and UTF-32 of either byte order (an image's text
chunks, a PDF's plain metadata); its findings say `(binary)`, and their line is the run's number. What the
scan does not read: a run shorter than four characters, and whatever a file holds compressed, such as a PNG's
compressed text chunks, a PDF's streams or an archive's members. Before committing such a file, strip its
metadata, or look at it decompressed.

- **Run it**, from the repository's root, with the key in a file or in `CONFIDENTIAL_SCAN_KEY`:
  ```sh
  python3 scripts/check_confidential.py --key-file /path/to/confidential_scan.key --messages origin/main..HEAD
  ```
  Without a key, it checks the paths only.
- **Add a term** (this needs the key): add it to the private list of terms, one a line, and write the digests
  again from the whole list. A term is found as a word, a pair of adjacent words or a hyphenated run, whatever
  the case and separators: `a-b` finds `A B`, `a_b` and `a-b`.
  ```sh
  python3 scripts/check_confidential.py --key-file /path/to/confidential_scan.key --digest \
    < /path/to/confidential_terms.txt > scripts/confidential_digests.txt
  ```
- **A new key** (`python3 -c "import secrets; print(secrets.token_hex(32))"`) needs the digests written again,
  and the secret set again: `gh secret set CONFIDENTIAL_SCAN_KEY < /path/to/confidential_scan.key`.
- **As a pre-push hook**, which checks what each push would publish, before it does: the name of each branch
  or tag it writes, every file content and annotated tag the remote lacks (by what the remote advertises at
  that moment), a file a later commit removes included, and every commit message it brings, refusing the push
  on a finding. Deleting a ref is never refused. CI's scan runs only once a push is public. Install it once a
  clone (hooks live in the common git directory, so every worktree shares it), and either name the key file,
  if you hold the key (a leading `~` is expanded), or say that this clone has none, as an outside
  contributor's: then the hook checks the paths alone, with a warning. With neither, or with the key in
  neither the configuration nor `CONFIDENTIAL_SCAN_KEY`, it refuses every push and says how to set one:
  ```sh
  cp scripts/pre-push "$(git rev-parse --git-path hooks/pre-push)"
  git config openmaterica.scanKeyFile /path/to/confidential_scan.key    # if you hold the key
  git config openmaterica.scanWithoutKey true                           # if you do not
  ```
  It runs the scan of the checkout you push from, so a branch based on a `main` from before the hook needs a
  rebase first. Agents push only through it.
- **As a pre-commit hook**, which checks the tracked files of the working tree before each commit (CI checks
  the messages):
  ```sh
  key=/path/to/confidential_scan.key; hook="$(git rev-parse --git-path hooks/pre-commit)"; printf '#!/bin/sh\nexec python3 scripts/check_confidential.py --key-file %s\n' "$key" > "$hook" && chmod +x "$hook"
  ```

## Identifier prefixes

| Category | Format | Example |
|---|---|---|
| Anomalies | `OMAT-ANO-XXX` | `OMAT-ANO-001` |
| Verification items | `OMAT-VER-XXX` | `OMAT-VER-001` |
| Records | `<namespace>/<local id>`; in the curated library `materica/MAT-XXXX` for materials and `materica/INT-XXXX` for interfaces. A namespace uses the characters `[a-z0-9_]` and is unique only once registered | `materica/MAT-0001` |
| Record types | `material`, `interface` and `overlay` (OpenMaterica's); `<namespace>:<type>` for another namespace's, once a consumer has prototyped one | `mime:emns_calibration` (planned) |
| Methods | `OMAT-MTH-XXX` | `OMAT-MTH-001` |
| Model families | `<namespace>.<section>.<name>.v<N>` | `materica.mechanical.ogden_incompressible.v1` |

The prefix `OMAT` is distinct from `MADD` (MADDENING), `MIME` and `MBOT` (MICROROBOTICA).

## Commit messages

Prefixes as in MADDENING and MIME, plus three:

| Prefix | Meaning |
|---|---|
| `feat:` | new feature |
| `fix:` | bug fix |
| `refactor:` | restructuring, no behaviour change |
| `docs:` | documentation only |
| `test:` | tests |
| `perf:` | performance |
| `verify:` | verification evidence |
| `break:` | breaking change |
| `deprecate:` | deprecation notice |
| `security:` | security-relevant change |
| `schema:` | a change to the specification, the record schema or the USD schema |
| `family:` | a new family version, or a deprecation |
| `data:` | a change to the material library |

## Changing the schema

One pull request carries all of: the specification text in `docs/specification/`, the conformance cases, the
writer JSON Schemas and USD schema files, the generated files (the reader schemas and typed shapes from the
writer schemas, the vocabulary from the specification's tables), the reader change, an entry in
`docs/specification/changes.md`, and a CHANGELOG entry under **Schema**. Edit structure in the writer schemas
and tokens in the specification's tables, then regenerate; CI fails if a generated file or a specification
member table differs from its source. The version rules are in `DOCUMENTATION_ARCHITECTURE.md` section 7.

A released schema version's files never change: a change is a new minor version in a new directory beside it
(maintainer, 2026-10-14). CI fails where a file of a released version is added, removed or changed
(`tests/spec_sync/test_released_schemas.py`). Until its release, a version's files may change, and the
version's index page on the site says so ("Draft until 0.1.0"; it leaves the page when the release freezes the
version). Once 0.1.0 is released, the next line's schemas are written in `src/materica/schema/0.2-dev/`, with
`$id`s under `https://w3id.org/materica/schema/0.2-dev/`; the 0.2.0 release renames the directory to `0.2/`,
rewrites the `$id`s, moves the files the generators write into it and points the paths wired to `0.1` (the
generators, `tests/spec_sync/schemas.py`) at the new line, then freezes it (`src/materica/schema/README.md`,
"Released versions"). That is the documented path; whether the address is instead redirected by a pull request
to `perma-id/w3id.org` is decided at that release.

## Adding a model family

A family is admitted with all of the following, in one pull request:

- a `definition.md` following `DOCUMENTATION_ARCHITECTURE.md` section 5.2: its kind (`static`, or
  `evolution` with its state variables, initial state and any events), stated per loading control, with
  every rate marked as an input or a test condition; its input and output measures, with conversion vectors
  between them; equations, with the domain of each term; parameters with units, admissibility, references,
  and the known conventions elsewhere;
- golden test vectors as data files, including edge cases and admissibility cases, with their precision;
  vectors on both sides of every switch in the equations; consistency vectors for any constant continuity
  fixes (for an evolution family: input histories, with tolerances, and analytic cases that pin the
  integrator);
- a reference implementation in plain numpy, written for clarity, that reproduces the vectors. It lives
  with the family in `families/` and ships in `openmaterica-families`, never in the core;
- a **named consumer**: who needs the family, and for what.

An event says only that the family's range of states ends, and under which condition. Never name the model
that takes over: the consumer declares that chain, as pairs of family and record, and the build records it.
State the family's coverage in measures that do not depend on the loading mode (principal stretches or
invariants, and rate). A witness that works only through a model of a test (a puncture force through a model
of the puncture) counts for admission only if that model is itself a family with vectors.

The identifier is namespaced and versioned. Publishing under `materica.` is for families this project
maintains, and a family enters it only when an in-scope record uses it; until then it lives in its consumer's
namespace. Anyone may publish families in their own namespace with the same checks, and needs no admission
from this project; the library's CI runs no code of yours, so your family's check points are reported there as
"not checked (third-party family)". A released version never changes: a correction is a new version, and the
old one is deprecated with a pointer to it. A family with no consumer for two releases is deprecated. Record
the change under **Families** in `families/CHANGELOG.md`.

**A consumer that cannot be named.** A family under `materica.` may be admitted for a consumer that cannot
be named publicly, on three conditions. The maintainer attests that the consumer exists and says nothing
else about it. Where the maintainer also owns that consumer, the attestation certifies itself, and the
admission record says so in those words. And the family reproduces a published dataset end to end (its
witness and a fit), so that every claim in its record can be checked without the consumer: that
reproduction is the check that carries weight. The attestation is renewed each release, or the
two-release deprecation applies. A family that only a private project needs is better published in that
project's own namespace, which needs no admission.

## Adding or changing a library material

**First, the scope.** OpenMaterica describes substances in and around the human body: tissues and body fluids,
the media and phantoms that stand in for them, agents introduced into them, and the materials of devices
that enter or touch them. It does not describe systems: an apparatus or its calibration, the quantities of
one object (its moment, inertia or mean density), a drive, a procedure, or a simulator's tuning. Before
adding a value, ask what it was measured on. A value of a substance, or of a mixture given by its
composition, measured on a test specimen whose shape and size you record as conditions, is in. A value of a
made object as built (a device, a product, an assembled robot) belongs to its consumer. A value that depends
on the specimen's shape (a magnetic value measured on a sphere) is in, with the shape as a condition. An
apparatus's materials (a coil's copper) go in your own namespace as material records. A friction
coefficient is a pair property (an interface record) only if the source states the surface conditions and
the test method; one measured with a single tool is reference data. Data about a system can still use the
same machinery in your own namespace, as a record type of your own, once one has been prototyped
(`DOCUMENTATION_ARCHITECTURE.md` section 3.1).

Every value needs (the full standard is `DOCUMENTATION_ARCHITECTURE.md` section 5.3):

- its **origin**: measured by the source, measured by you, fitted, derived, evaluated from a reference
  formulation (with the derivation as evidence), or stated without an origin;
- a **source** as a key in the source registry, with a locator for the version of the document you read
  (table, figure, page or equation); for a table, quote the column header and give its index;
- the **extraction** method: table, text, digitised figure (with the tool, the axis calibration and an
  estimate of digitising error), supplementary dataset (with its licence), own measurement, derivation or
  fit;
- the **quote** for every value extracted from text or a table: verbatim, with any conditions and exponents
  it states, the document's identifier and version, and the SHA-256 of your copy. Record which text
  extraction of the document matched. Never commit a copy stamped with personal data. If the legal review
  rules that quotes may not ship, the record carries the SHA-256 of the normalised quote instead, and you
  keep the text;
- the **conditions** of the test as the source states them, from the conditions vocabulary (temperature,
  frequency, rate, loading mode, test method, measurement geometry, propagation direction for speeds in
  anisotropic tissue; categorical ones included), each with its basis (stated, or inferred from a figure),
  and any the source does not state recorded as unstated; the specimen's shape and size as conditions for
  magnetic values; the
  test method and specimen geometry for failure values; the kind of density (apparent, or of the tissue
  itself);
- for a table or a power law, the **range** it covers, and the range the source says it holds over where that
  differs; for a table, its **interpolation scheme** and **edges**; for a power law, the basis of its
  exponent. A 0.1.0 record holds no evidence per point (`points` is reserved until 0.2). So keep each row's
  own spread, and where in the source it was found, in your draft. Where that spread varies along the axis,
  state the largest in the table's block, in the table's terms, and say so in the record's card (specification
  `uncertainty.md` section 1 rule 2). On a log-log table whose spread is a population spread, 0.1.0 cannot
  state it in those terms: hold the table back until 0.2. Attenuation is stored as an amplitude coefficient in
  nepers per metre (UCUM `/m`), with a solid's shear attenuation beside its longitudinal one; record the unit
  the source used and whether it reported an amplitude or an intensity coefficient;
- a **composition** with its components, basis (mass, volume or mole), sum rule, and the sum the source
  states, kept as a fact even when it is not 100 %;
- **statistics** for a scalar: specimens and donors, mean, standard deviation, minimum, maximum, basis, and
  what the spread represents (a population, an estimate, measurement error or spread across sources); a
  relative or expanded uncertainty with its coverage factor where that is what the source gives; the basis
  "specification limits" for a datasheet's minimum and maximum; at least a range with its basis;
  `dispersion: not_reported` if the source gives none; an interval with its basis if that is all that is
  known, one-sided if only one bound is. For a parameter set, an **uncertainty structure** (`ensemble`,
  `multivariate_normal`, `independent` with a justification, `marginals` where the source gives statistics
  per parameter and no dependence, `interval` or `none`) and what it represents;
- for a parameter set, **check points** baked by the family's reference implementation, spanning the fit's
  coverage and the family's branch points (none for a reference-only set: they would publish its
  parameters), and an **independent witness**: a response the source reports
  that was not used to obtain the parameters, with the fit it is independent of and a tolerance taken from
  the fit's residual and the stated state's precision (never the spread between specimens), or the flag "no
  independent witness". A set that is a mean of per-specimen fits is witnessed against per-specimen data.
  For a fit, the **fit record** (reference data, procedure, coverage, residual; or "exactly determined").
  Provenance may be given per parameter. A constant that names its trivial family (a Newtonian viscosity) is
  a scalar for these rules, not a parameter set;
- **specimen facts**, per section or field, describing the thing tested: species and anatomical site as
  ontology identifiers (NCBI Taxonomy, UBERON), tissue state from the short list (in vivo, ex vivo fresh,
  frozen and thawed, fixed, phantom), disease and treatment state, preparation, preservation, donor age,
  shape; a fact the source does
  not state recorded as unstated; for a phantom or a substitute, what its maker says it mimics. Do not write
  what the data is a proxy for: that depends on each consumer's target;
- density and elemental composition in the **bulk** section, once, never repeated in another section;
- for biocompatibility, the **test evidence** only: endpoint, standard and part, contact category and
  duration tested, material form and processing; never a status;
- an explicit **status** ("not checked", "none") wherever a check or field has no result; never leave it
  empty;
- a **review record**: who checked the value against the source, when, and their ORCID, and whether the
  reviewer is independent of whoever, or whatever, extracted it. Agreement with another database is not a
  review.

The **tier** (shipped, reference-only or private) is not written per value: it is computed from the
source's redistribution status in the registry. What a person sets is that status, and the record's review
status. Records are JSON.

Every material also needs the prose its card shows (architecture draft section 6.6): why it was curated and
for which consumer, what was measured and what was not, and who maintains it. Do not write that it suits a
use. Write it in the record; the card is generated.

Rules for data:

- Extract from primary literature. Never copy a secondary database in bulk.
- Do not enter numbers found in code or datasheets with nothing behind them as library values. They stay in
  their consumer as declared values until a source replaces them. A citation found beside a number in code
  is a lead, not provenance: follow it to the source and take the value from there.
- In the source registry, record for each copy you hold its retrieval route, its version identity and the
  licence it came under.
- Keep every alternative you find where sources disagree; do not pick one. The consumer picks. How hard to
  search for alternatives depends on how sensitive a consumer's result is to the choice.
- Check the source's redistribution status in the source registry before shipping a value. If there is no
  entry, add one; if the status is not permitted or unknown, the value is reference-only: publish the
  provenance, the locator and an extraction recipe, not the value.
- Fits you make yourself from published curves are your own work and can usually be shipped even when the
  curves stay reference-only. Say so in the fit record.
- Own measurements published under an open licence are welcome and are the cleanest data the library can
  hold.

Run `python -m materica check` before opening a pull request; CI runs it too.

You do not need the curated library to publish records. Keep them in your own repository under your own
namespace and run the same `materica check`. The template repository sets that up. To list your namespace,
open a pull request adding one line to the library's `publishers.yaml` (architecture draft section 6.7).

A change is recorded under **Data** in the library's CHANGELOG with a new record version. A value that
faithfully transcribes a source later found wrong is a data update, not an anomaly; consumers that pin the old
version learn of it from the advisory index (architecture draft section 5.6).

### Model-assisted extraction

You may draft values with a language model through the curation tools (architecture draft section 8), using
your own agent and key. The tools are library functions with a command line; the MCP server only exposes them
to an agent, except registry drafting and source discovery and acquisition, which go online and stay commands
you run yourself. Then:

- record the assistance: tool, model and provider as reported, the procedure's `OMAT-MTH-` entry and
  version, and the date;
- keep the evidence for every value, as for any value: the verbatim quote, its locator, the document's
  identity and version, and the SHA-256 of your copy. Do not publish quotes for reference-only values; a
  quote contains the value;
- a record a model drafted stays reference-only until you set its review status;
- ask the agent to flag contradictions inside a source, swapped values, implausible spreads and
  mislabelled specimen states; the review checklist asks for these. Before review, run a pass told to
  refute the draft, and read what it finds;
- let deterministic tools convert units, bake check points and run fits. Never accept a model's number for
  any of them;
- for a parameter set, attach its independent witness and run the convention checker; the model's guess at
  the family is only a proposal;
- set redistribution statuses and review statuses yourself; the tier is computed from them;
- review every value at its locator on the rendered page, not only the quote, and record the checklist;
- before relying on a model, run the procedure against the gold set and look at its per-field errors.

The MCP tools can only write drafts. Opening and merging the pull request are yours.

### Data attestation

Every pull request that adds or changes library data includes this statement, ticked, in the pull-request
template:

> I attest that each value in this pull request was extracted from the cited source by the method recorded
> for it, or comes from a measurement or fit I describe; that every value extracted from text or a table
> carries its verbatim quote and locator, or the quote's hash if the legal review has ruled that quotes may
> not ship; that every value a language model helped draft is recorded as such and was checked by a named
> reviewer against the source at its locator; that nothing was copied in bulk from a secondary database;
> that each value's tier matches its source's redistribution status in the source registry; and that I have
> the right to contribute the shipped values under CC0-1.0. Quotes kept as evidence remain the source's
> text.

### Takedown

A rights holder who objects to a shipped value or reference dataset can write to
**nick@microrobotica.org**. The request is acknowledged within 5 business days. While it is assessed, the
affected values are moved to reference-only in the next library patch release, and the change is recorded
under **Data** in the library's CHANGELOG. A takedown is not an anomaly: the values are not wrong.

## Anomaly lifecycle

Adopted from MADDENING unchanged (its `CONTRIBUTING.md` and `DOCUMENTATION_ARCHITECTURE.md` section 9.7).

1. **Discovery.** Open an issue with the anomaly template (`.github/ISSUE_TEMPLATE/anomaly.yml`). Fill in
   severity, safety relevance and its rationale, affected components, affected versions and any workaround.
   Apply `anomaly:critical`, `anomaly:major` or `anomaly:minor`, and `safety-relevant` where it applies.
2. **Formalisation.** Add an entry to `docs/validation/known_anomalies.yaml` by hand. This is a deliberate
   review step and is never automated.
3. **Verification.** When resolved, set the status and version, and cite the test that shows the fix.

Severity follows MADDENING's definitions; `DOCUMENTATION_ARCHITECTURE.md` section 8.2 applies them to data
and families. **A silent wrong result is never `minor`.** A library value that differs from its source is a
silent wrong result; so is a reference implementation that differs from its family definition.

Name affected components without adding fields: `schema:<API name>`, `reader:<function>`,
`method:<OMAT-MTH id>`, `model:<family identifier>`, `data:<MAT or INT id>`.

Every defect a release carried gets an entry. Every `critical` or `major` defect found during a development
cycle gets one, even if no release carried it.

## Release gate

As MADDENING's: a `safety-relevant`, `critical` or `major` anomaly closed in a release must be in the
registry before that release is tagged; a `minor` one within two release cycles.

A release that releases a schema version (schema 0.1 at the 0.1.0 release; a development pre-release releases
none) freezes it in the release's pull request, before the tag:

```sh
python3 scripts/freeze_schema.py 0.1       # adds 0.1 to tests/spec_sync/released_schemas.json
python3 scripts/freeze_schema.py --check   # fails where a released version differs from it
```

It refuses a version whose `$id`s are not their paths, and never rewrites a version already listed. Commit the
manifest with the release; from then on CI fails where a file of that version changes, and the version's page on
the site loses its "draft until" note when Pages next deploys. The release's pull request carries the manifest and
merges just before the tag, so the note leaves the site then and not at the tag: that is intended, since from the
merge the files are frozen.
