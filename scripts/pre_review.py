# SPDX-License-Identifier: Apache-2.0
"""Run the mechanical checks that apply to what a branch changed, before asking for review (CONTRIBUTING,
"Before asking for review").

    python scripts/pre_review.py [BASE] [--list] [--stage fast|tests|properties|whole] [--workers N]
                                 [--keep-going]

`BASE` is a ref, `origin/main` where none is given. The changed files are those from the merge base of `BASE`
and `HEAD` to the working tree, committed or not, with the files git does not track yet. From them it plans
the checks, prints each with the paths that selected it, and runs them in three stages: the fast checks
(sign-offs, confidential names, every generator's `--check`, for a change to code the linters and type
checkers, and where a README's kill points marker was added or removed the kill counts' unit tests, which hold
the markers to the recorded groups by name), the tests of what changed and of what imports it, and the
property shards at the `ci` profile that
hold a changed or affected property module, with, where one of them holds mutant searches or the recorded kill
points or their README changed, every mutant search's kill against the recorded one
(`scripts/gen_kill_counts.py --measure`, as CI's controls job checks its own run). A stage that fails stops
the run before the next, unless `--keep-going` is given: what the fast checks find is fixed before any test
runs. After the plan it prints reminders for what no test can check: a figure stated in a CHANGELOG line or a
commit message to recount, code changed beside a CHANGELOG that was not.

A fourth stage, `whole`, runs only when asked for (`--stage whole`): every test under `tests/` but those left
to CI by name (`LEFT_TO_CI`, each with why), its selection the tree's own, so that a new directory of tests
joins it with no edit. Run it once at the head, after the other stages pass and before handing back: a
builder's targeted tests miss a directory nothing they changed imports, which CI then fails on.

It adds to CI's checks and replaces none. It runs the checks that apply to the change, not every check; CI
runs them all, on every Python, and its result is the one that counts. A change it selects no check for is
printed as such: that is a gap in this script, or a change only an independent eye can judge.

What imports what is read from the import statements of the Python files, `from a import b` counting for
`a` and for `a.b`, and `import a.b.c` for `a` and `a.b` too, whose `__init__.py` it runs; a data file is
followed to the tests and modules that read it by the declared table `DATA_RULES`. A few tests read the whole
tree instead of importing what they check (`TREE_READERS`): a changed Python file selects them whether or not
anything imports it. A change it cannot map to a test with confidence (a Python file no test imports, a file
under `tests/` outside every group of tests, a conftest of a group it does not know) selects the whole of
`tests/unit`, and says so.
`tests/unit/test_pre_review.py` holds both tables against a trace of the files the tests open.
"""

import argparse
import ast
import fnmatch
import glob
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections import defaultdict, deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "origin/main"
STAGES = ("fast", "tests", "properties", "whole")
# The whole tree's stage runs when asked for alone (`--stage whole`): before review, at the head, as the last
# check (CONTRIBUTING, "Before asking for review").
DEFAULT_STAGES = STAGES[:-1]

# The whole-tree stage: every test under `tests/` but these, each left to CI by name, with why. Its selection
# is the tree's own (`pytest tests`), so a new directory of tests joins it with no edit here; it runs in parts
# (`--partition`, by the times CI's test jobs measured) one after another, each under the 15 minutes an
# agent's command may take (`WHOLE_PARTS`).
LEFT_TO_CI = {
    "tests/property": "the property modules: CI's hypothesis job runs their shards at `ci`, and its tests "
    "and controls jobs at `dev`; the properties stage runs the shards a change reaches",
}
WHOLE_PARTS = 1

# CI's own lists of the paths that are not code (`.github/workflows/ci.yml`, step "Changed paths"):
# `tests/unit/test_pre_review.py` holds these to the workflow's text.
DOCUMENTATION_PATHS = (
    r"CHANGELOG\.md|CLAUDE\.md|CONTRIBUTING\.md|SECURITY\.md|docs/regulatory/.+|docs/validation/.+"
    r"|\.github/ISSUE_TEMPLATE/.+|\.github/pull_request_template\.md"
)
SITE_PATHS = r"site/.+|assets/.+"
PYTHON_PATHS = r".*\.pyi?"

# The generators CI runs with `--check` in its generated-files job, in its own environment on Python 3.11,
# since the generator of the typed shapes does not run on 3.15.
GENERATORS = ("gen_vocabulary", "gen_reader_schema", "gen_shapes", "gen_kill_counts")
GENERATOR_PYTHON = "3.11"

# The kill counts: the recorded kill points and the README written from them, which a run of every mutant
# search holds to the code (`scripts/gen_kill_counts.py --measure`, as CI's controls job does with
# `--against`), and the modules whose searches record one.
KILL_COUNTS = r"tests/property/(kill_points\.json|README\.md)"
MUTANT_SEARCHES = "test_*mutants"

# A README's kill points marker, the comment line that names the group of the table under it:
# `scripts/gen_kill_counts.py`'s `MARKER`, which `tests/unit/test_pre_review.py` holds this to. The
# generator's `--check` holds each table to the group its marker names; the kill counts' unit tests also hold
# the markers to the groups the repository has, by name, and they run in the tests stage, which CI runs and a
# build may not. They take seconds, so a marker added or removed runs them with the fast checks.
KILL_POINTS_MARKER = re.compile(
    r"<!-- kill points of (?P<extent>every search|some searches) of (?P<group>\S+)"
    r" \(scripts/gen_kill_counts\.py\) -->"
)
KILL_COUNTS_TESTS = "tests/unit/test_gen_kill_counts.py"

PROFILE_VARIABLE = "MATERICA_HYPOTHESIS_PROFILE"
SPECIFICATION = r"docs/specification/.+|design/ARCHITECTURE_DRAFT\.md|DOCUMENTATION_ARCHITECTURE\.md"

# The citation test of the read model, when the model is in the tree: a reference with no quote, a drifted
# line and a quote cut short are what it catches. Absent, the rule selects nothing for it.
CITATION_TEST = "tests/reference/test_citations.py"


@dataclass(frozen=True)
class DataRule:
    """A kind of file that is no Python and what reads it: the tests that run on it alone, the paths whose
    tests run whole, and the Python modules that load it, whose importers' tests run too."""

    name: str
    pattern: str
    why: str
    tests: tuple[str, ...] = ()
    readers: tuple[str, ...] = ()


# Declared, not derived: which Python reads which data. `test_pre_review.py` holds every path named here to
# exist, and every module that locates data by `resources.files` or `__file__` to be named in `readers` or to
# be listed there as reading none.
DATA_RULES = (
    DataRule(
        "the specification",
        SPECIFICATION,
        "its tables generate the vocabulary; its references, quotes and member tables are held to the code",
        tests=("tests/spec_sync", "tests/unit/test_generators.py", CITATION_TEST),
    ),
    DataRule(
        "the specification text the verdicts, the audits and the conditions read",
        r"docs/specification/(provenance|record_format|uncertainty)\.md",
        "the verdicts' tests and the audit controls quote it, the agreement and conditions shards read it "
        "when they are imported, and so do the property modules the fuzz oracles' tests import",
        tests=(
            "tests/unit/test_audit_controls.py",
            "tests/unit/test_verdicts.py",
            "tests/property/test_validators_agree.py",
            "tests/property/test_condition_mutant_table.py",
            "tests/unit/test_fuzz_oracle.py",
            "tests/unit/test_acceptance_oracle.py",
        ),
    ),
    DataRule(
        "the read result's table, to which the reference model's results are held",
        r"docs/specification/read_side_contract\.md",
        "the reference model's case test reads section 2's table, the members a read's result may hold",
        tests=("tests/reference/test_cases.py",),
    ),
    DataRule(
        "the declaration's text, from which the build model's order of refusals is read",
        r"docs/specification/declarations\.md",
        "the build model's order check reads the paragraph that lists the refusals in order, so a change to "
        "it runs the tests that import the helper that reads it; the results model's test reads section "
        "4.2's table",
        tests=("tests/reference/test_build_results_model.py",),
        readers=("tests/reference/direct.py",),
    ),
    DataRule(
        "a schema",
        r"src/materica/schema/.+",
        "the schemas and the vocabulary are read by the reader and held to the specification, and the frozen "
        "versions and the published index are built from the files",
        tests=(
            "tests/spec_sync",
            "tests/unit/test_shapes.py",
            "tests/unit/test_vocabulary.py",
            "tests/unit/test_freeze_schema.py",
            "tests/unit/test_schema_index.py",
        ),
        readers=(
            "src/materica/core/vocabulary.py",
            "tests/spec_sync/schemas.py",
            "tests/property/condition_oracle.py",
            "tests/verdicts.py",
            "tests/reference/read_model.py",
            "scripts/check_wheel.py",
            "scripts/freeze_schema.py",
            "scripts/gen_reader_schema.py",
            "scripts/gen_shapes.py",
            "scripts/schema_index.py",
        ),
    ),
    DataRule(
        "a conformance case",
        r"src/materica/data/conformance/.+",
        "the cases are run by the conformance runner and held to CASES.md and the step map, fuzz target 5's "
        "oracle reads two of the inputs, and the results model's direct checks read the build checks' inputs",
        tests=("tests/conformance", "tests/spec_sync"),
        readers=(
            "tests/conformance/runner.py",
            "scripts/check_wheel.py",
            "tests/fuzz/acceptance_oracle.py",
            "tests/reference/results_direct.py",
        ),
    ),
    DataRule(
        "the generated coverage table and the acceptance module that reads it",
        r"src/materica/schema/0\.1/vocabulary/coverage\.json|src/materica/core/acceptance\.py",
        "the results model's test holds its table of section 4.2 to `coverage.json` once the file exists, "
        "and fails where the acceptance module exists without it; `tests/reference` is no group of tests, "
        "so the test is named here",
        tests=("tests/reference/test_build_results_model.py",),
    ),
    DataRule(
        "a build-check input, which the results model's direct checks read",
        r"src/materica/data/conformance/build_checks/inputs/.+",
        "the results model's direct checks read the build-check declarations and fixtures by path, and the "
        "model's seeded faults run against them; `tests/reference` is no group of tests, so its readers' "
        "importers are named here",
        tests=("tests/reference/test_build_results_model.py", "tests/reference/test_seeded_faults.py"),
    ),
    DataRule(
        "a plain-read input the read tests load",
        r"src/materica/data/conformance/plain_read/inputs/water(_overlay)?_fixture\.json",
        "the read and conditions tests load the water fixtures directly",
        tests=("tests/unit/test_read.py", "tests/unit/test_conditions.py"),
    ),
    DataRule(
        "PR-316's case and its record, which the read tests load",
        r"src/materica/data/conformance/plain_read/(cases/PR-316\.implied_two_disagree_in_alternative"
        r"|inputs/water_alternatives_in_vivo_normal)\.json",
        "the read tests load PR-316's case file and its record directly, for step 7's arm of a request fault",
        tests=("tests/unit/test_read.py",),
    ),
    DataRule(
        "the evidence input the read tests load",
        r"src/materica/data/conformance/plain_read/inputs/evidence_fixture\.json",
        "the read tests load the evidence fixture directly, for step 8's and step 13's rows on evidence",
        tests=("tests/unit/test_read.py",),
    ),
    DataRule(
        "the build-check inputs the declaration tests load",
        r"src/materica/data/conformance/build_checks/inputs/"
        r"(bc016_waiver_at_one_of_two_records|water_fixture)\.json",
        "the declaration tests load BC-016's declaration and the water fixture directly, as a declaration "
        "the check takes and the records it is built over",
        tests=("tests/unit/test_declarations.py",),
    ),
    DataRule(
        "the build-check files, a plain-read record and the read-side contract, which the build tests load",
        r"src/materica/data/conformance/build_checks/(cases|inputs)/.+\.json"
        r"|src/materica/data/conformance/plain_read/inputs/density_overlay\.json"
        r"|docs/specification/read_side_contract\.md",
        "the build tests load build-check declarations and their records, an overlay record a read raises "
        "for, and section 1's list of the kinds of acceptance a read takes; the report's tests build "
        "build-check declarations over their records",
        tests=("tests/unit/test_build.py", "tests/unit/test_report.py"),
    ),
    DataRule(
        "an example record",
        r"examples/.+",
        "the example tests check each record against the schemas, its sources and what a read of it gives",
        tests=("tests/examples",),
    ),
    DataRule(
        "the README, which documents the example records",
        r"README\.md",
        "the example tests hold each page that documents the records to say they are not yet fully "
        "human-reviewed",
        tests=("tests/examples/test_example_records.py",),
    ),
    DataRule(
        "the quickstart",
        r"docs/user_guide/quickstart\.md",
        "it is run as a doctest, and it documents the example records, so it holds their note",
        tests=("tests/examples/test_quickstart.py", "tests/examples/test_example_records.py"),
    ),
    DataRule(
        "a spec-sync table",
        r"tests/spec_sync/.+\.json",
        "the tables are checked against the text and the schemas",
        tests=("tests/spec_sync",),
    ),
    DataRule(
        "the list of released schema versions",
        r"tests/spec_sync/released_schemas\.json",
        "the published index marks every version this list does not hold as a draft",
        tests=("tests/unit/test_schema_index.py",),
    ),
    DataRule(
        "a workflow",
        r"\.github/workflows/.+",
        "the workflows' jobs, guards and caps are held by tests",
        tests=("tests/unit/test_ci_workflows.py", "tests/unit/test_repeat_runs.py"),
    ),
    DataRule(
        "the ignore rules",
        r"\.gitignore",
        "the mutant request refuses a path git ignores, and its guard runs on the repository's own rules",
        tests=("tests/unit/test_ci_workflows.py",),
    ),
    DataRule(
        "the weights that split a run into parts",
        r"tests/partition_weights\.json",
        "the parts of a run are the tests' assignment by these seconds, which the partition's own tests "
        "read; the tests of CI's matrices run the real assignment",
        tests=("tests/unit/test_partition.py", "tests/unit/test_ci_workflows.py"),
        readers=("tests/partition.py",),
    ),
    DataRule(
        "the tests' README",
        r"tests/README\.md",
        "the mutant tables' recipe is run as the README writes it",
        tests=("tests/unit/test_mutant_runs.py",),
    ),
    DataRule(
        "the main workflow, which more tests read than hold it",
        r"\.github/workflows/ci\.yml",
        "the script's own lists of CI's paths, the Python versions, the source-file rules and the fuzz "
        "controls of the measurement tool are compared with its text",
        tests=(
            "tests/unit/test_pre_review.py",
            "tests/unit/test_python_versions.py",
            "tests/unit/test_source_files.py",
            "tests/unit/test_measure.py",
        ),
    ),
    DataRule(
        "the project's build",
        r"pyproject\.toml|uv\.lock",
        "the supported Pythons, the profiles and the lock file are held by tests",
        tests=(
            "tests/unit/test_python_versions.py",
            "tests/unit/test_hypothesis_profiles.py",
            "tests/unit/test_source_files.py",
            "tests/unit/test_ci_workflows.py",
            "tests/unit/test_gen_kill_counts.py",
        ),
    ),
    DataRule(
        "the recorded kill points, or the README written from them",
        KILL_COUNTS,
        "the kill counts' generator holds the README to the file, and its tests read both; a run of every "
        "mutant search holds the file to the code (planned with the property shards)",
        tests=("tests/unit/test_gen_kill_counts.py",),
        readers=("scripts/gen_kill_counts.py", "scripts/measure.py"),
    ),
    DataRule(
        "the claims check's baseline",
        r"scripts/claims_baseline\.json",
        "the claims check reads it, and its tests hold the committed file to its shape",
        tests=("tests/unit/test_check_claims.py",),
        readers=("scripts/check_claims.py",),
    ),
    DataRule(
        "the input coverage's baseline",
        r"tests/property/input_coverage_baseline\.json",
        "the checker reads its selections and compares a run with it, the measure workflow's cut kind splits "
        "them by its timing; their tests hold its form",
        tests=("tests/unit/test_input_coverage.py",),
        readers=("scripts/input_coverage.py", "scripts/measure.py"),
    ),
    DataRule(
        "the confidential digests and the hook that runs the scan",
        r"scripts/confidential_digests\.txt|scripts/pre-push",
        "the digests are read by the scan, whose tests run it on them, and its tests run the hook",
        tests=("tests/unit/test_check_confidential.py",),
    ),
)


@dataclass(frozen=True)
class TreeReader:
    """Tests that read Python files instead of importing them, a directory of them or a named one: an added,
    deleted or changed Python file that matches `pattern` can fail them, whatever imports it."""

    pattern: str
    why: str
    tests: tuple[str, ...]


# Declared, not derived: `test_pre_review.py` runs the tests under a trace of the files they open and the
# directories they list, and fails for a test that lists a directory of Python files, or opens a Python file
# it does not import, where the change of such a file does not select it.
TREE_READERS = (
    TreeReader(
        r"(src|tests|scripts)/.+\.py",
        "every Python file has its licence header and layer, and each property module is in one shard",
        ("tests/unit/test_source_files.py",),
    ),
    TreeReader(
        r"(src|tests|scripts)/.+\.py",
        "the pre-review script's own tests read the tree: the readers of data files are all declared",
        ("tests/unit/test_pre_review.py",),
    ),
    TreeReader(
        r"(src|tests|scripts)/.+\.py",
        "no test or script names a path the gate calls documentation, and no module the Hypothesis job runs "
        "imports one of the files the gate lists as free of Hypothesis",
        ("tests/unit/test_ci_workflows.py",),
    ),
    TreeReader(
        r"tests/property/.+\.py",
        "the kill counts' generator digests the source of the functions that seed the mutant searches, and "
        "holds the recorded kill points to them",
        ("tests/unit/test_gen_kill_counts.py",),
    ),
    TreeReader(
        r"src/materica/core/.+\.py",
        "each core module is imported, its `claims` parameter and its steps are checked, and where the build "
        "constructs its own reasons",
        (
            "tests/unit/test_read.py",
            "tests/spec_sync/test_reason_steps.py",
            "tests/spec_sync/test_build_reasons.py",
        ),
    ),
    TreeReader(
        r"tests/spec_sync/test_name_overlap_safeguards\.py",
        "the name-overlap allowlist names tests in it, and each must be there guarding its name",
        ("tests/spec_sync/test_name_overlaps.py",),
    ),
    TreeReader(
        r"tests/.+\.py",
        "the input coverage's tests copy the plugin into trees of their own and run it there, and read every "
        "test module under `tests/` for the strategy modules it imports",
        ("tests/unit/test_input_coverage.py",),
    ),
    TreeReader(
        r"tests/property/input_coverage\.py",
        "the measure workflow's cut kind's tests copy the plugin into trees of their own and run it there",
        ("tests/unit/test_measure_cuts.py",),
    ),
    TreeReader(
        r"tests/.+\.py",
        "the agreement shard compares the source of every test file with what it lists",
        ("tests/property/test_validators_agree.py",),
    ),
)

# Modules that are no test and that locate files by `resources.files` or `__file__` without being one of
# `DATA_RULES`' readers, each with the reason a change to a data file need not follow it. (A test module is
# held by the trace in `test_pre_review.py`, which sees what it opens.)
LOCATES_NO_RULED_DATA = {
    "scripts/check_confidential.py": "reads the tracked files and the digests, whose rule runs its tests",
    "scripts/check_anomalies.py": "reads the anomaly registry and the package's version; the fast stage "
    "runs it on every change, as CI's gate does",
    "scripts/gen_vocabulary.py": "reads the specification's tables; the specification rule runs its tests",
    "tests/property/input_coverage.py": "names each site by its path under the tree it lies in, and reads "
    "the modules' source for the names; it opens no data file",
    "scripts/mutant_runs.py": "names its own copy for the mutant job's import check, and reads where each "
    "module it imports came from; it opens no data file",
    "scripts/pre_review.py": "reads the tree through git and `ast`; its own tests read it again and hold it",
    "tests/conftest.py": "locates the example database; a change to a conftest selects every test",
    "tests/fuzz/jsonio_bytes.py": "an Atheris target: CI's fuzz job runs it, this script cannot",
    "tests/fuzz/read_field_bytes.py": "an Atheris target: CI's fuzz job runs it, this script cannot",
    "tests/fuzz/read_acceptance_bytes.py": "an Atheris target: CI's fuzz job runs it, this script cannot",
    "tests/spec_sync/name_overlaps.py": "read by `tests/spec_sync`, which the schema rule runs whole",
    "tests/spec_sync/reason_sites.py": "read by `tests/spec_sync`, which the schema rule runs whole",
}

# The groups of tests under `tests/`, and the directory a conftest or package file of each applies to. A path
# under `tests/` outside every group selects the whole of `tests/unit`.
TEST_GROUPS = ("unit", "spec_sync", "conformance", "property", "examples")
# Code with no test, that a check of the static job holds instead: the consumer snippet is type-checked
# against the built wheel.
CHECKED_BY_THE_STATIC_JOB = r"tests/typing/.+"
WHOLE_UNIT_DIRECTORY = "tests/unit"


@dataclass
class Planned:
    stage: str
    command: tuple[str, ...]
    why: str
    because: list[str] = field(default_factory=list[str])
    env: dict[str, str] = field(default_factory=dict[str, str])
    # The files of the repository the command names: `test_pre_review.py` holds each to exist.
    paths: tuple[str, ...] = ()
    # A path that may be absent: its rule selects it only where it exists.
    optional: bool = False


def git(*arguments: str, root: Path = REPOSITORY, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *arguments], capture_output=True, text=True, check=check, cwd=root)


def git_paths(*arguments: str, root: Path = REPOSITORY) -> list[str]:
    """The NUL-separated paths git prints for `arguments`, as the file system names them."""
    done = subprocess.run(["git", *arguments], capture_output=True, check=True, cwd=root)
    return [os.fsdecode(path) for path in done.stdout.split(b"\0") if path]


def changed_files(base: str, root: Path = REPOSITORY) -> list[str]:
    """The files changed from the merge base of `base` and HEAD to the working tree, deleted ones included,
    with those not tracked yet, each path once, sorted. A rename counts as the old path gone and the new one
    added."""
    merge_base = git("merge-base", base, "HEAD", root=root).stdout.strip()
    tracked = git_paths("diff", "--no-renames", "--name-only", "-z", merge_base, root=root)
    untracked = git_paths("ls-files", "--others", "--exclude-standard", "-z", root=root)
    return sorted({*tracked, *untracked})


def changed_markers(changed: Sequence[str], base: str, root: Path = REPOSITORY) -> list[str]:
    """The changed READMEs in which a kill points marker was added or removed, from the merge base of `base`
    and HEAD to the working tree (a marker moved or edited is both); an untracked README by every line it
    holds, and one that is no regular file not opened."""
    readmes = [path for path in changed if Path(path).name == "README.md"]
    if not readmes:
        return []
    merge_base = git("merge-base", base, "HEAD", root=root).stdout.strip()
    untracked = set(git_paths("ls-files", "--others", "--exclude-standard", "-z", root=root))
    found: list[str] = []
    for path in readmes:
        if path in untracked:
            try:
                regular = stat.S_ISREG((root / path).stat().st_mode)
            except OSError:
                regular = False
            data = (root / path).read_bytes() if regular else b""
            lines = data.decode("utf-8", errors="replace").splitlines()
        else:
            diff = subprocess.run(
                ["git", "--literal-pathspecs", "diff", "--no-renames", "-U0", merge_base, "--", path],
                capture_output=True,
                check=True,
                cwd=root,
            ).stdout.decode("utf-8", errors="replace")
            lines = [line[1:] for line in diff.splitlines() if line[:1] in ("+", "-")]
        if any(KILL_POINTS_MARKER.fullmatch(line) for line in lines):
            found.append(path)
    return found


# How git writes a name on the line of `git diff --name-only`, which is what CI's gate reads: in double
# quotes, with these characters as a backslash and a letter, and any other control character, DEL and any
# byte of 0x80 or more as a backslash and three octal digits.
GIT_ESCAPES = {7: "a", 8: "b", 9: "t", 10: "n", 11: "v", 12: "f", 13: "r", 34: '"', 92: "\\"}


def git_quoted(path: str) -> str:
    """The path as `git diff --name-only` prints it, without `-z`: unchanged where it holds only printable
    ASCII other than `"` and `\\`, else in double quotes, escaped (`core.quotePath` at its default)."""
    data = os.fsencode(path)
    if all(0x20 <= byte < 0x7F and byte not in GIT_ESCAPES for byte in data):
        return path
    pieces = ['"']
    for byte in data:
        if byte in GIT_ESCAPES:
            pieces.append("\\" + GIT_ESCAPES[byte])
        elif 0x20 <= byte < 0x7F:
            pieces.append(chr(byte))
        else:
            pieces.append(f"\\{byte:03o}")
    return "".join(pieces) + '"'


def printable(text: str) -> str:
    """The text with each control, format, surrogate or unassigned character written as an escape, so that a
    name in a diff cannot rewrite the terminal it is printed on."""
    return "".join(
        character
        if unicodedata.category(character) not in {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"}
        else f"\\x{ord(character):02x}"
        if ord(character) < 0x100
        else f"\\u{ord(character):04x}"
        if ord(character) < 0x10000
        else f"\\U{ord(character):08x}"
        for character in text
    )


def shell_quote(argument: str) -> str:
    """The argument as a shell reads it back: single-quoted where it needs quoting, and in `$'...'` where it
    holds a character `printable` would write as an escape, so that a command printed here can be pasted."""
    if printable(argument) == argument:
        return shlex.quote(argument)
    pieces: list[str] = []
    for character in argument:
        if character in {"\\", "'"}:
            pieces.append("\\" + character)
        elif printable(character) == character:
            pieces.append(character)
        else:
            pieces.append(printable(character))
    return "$'" + "".join(pieces) + "'"


def is_code(changed: Sequence[str]) -> bool:
    """CI's rule: a change is code unless it has paths, none a Python file, and each is documentation or the
    site's (the gate's `code`). The gate reads the names as `git diff --name-only` prints them, so a name that
    git quotes is matched in its quotes."""
    if not changed:
        return True
    lines = [git_quoted(path) for path in changed]
    if any(re.fullmatch(PYTHON_PATHS, line) for line in lines):
        return True
    return any(not re.fullmatch(f"{DOCUMENTATION_PATHS}|{SITE_PATHS}", line) for line in lines)


def matches(pattern: str, path: str) -> bool:
    """Whether the whole path fits the pattern, a newline in a name included."""
    return re.fullmatch(pattern, path, re.DOTALL) is not None


def module_name(path: str) -> str | None:
    """The dotted name a Python file is imported by, from the repository's root or `src/`."""
    if not path.endswith((".py", ".pyi")):
        return None
    parts = Path(path).with_suffix("").parts
    if parts[0] == "src":
        parts = parts[1:]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def imported_names(path: str, source: str) -> set[str]:
    """Each name the file imports: `import a.b` gives `a.b`, and `from a import b, c` gives `a`, `a.b` and
    `a.c`, so that a name that is a module and one that is not are both met. Relative imports are resolved
    against the file's package."""
    name = module_name(path)
    package = name.split(".") if name else []
    if name and Path(path).stem != "__init__":
        package = package[:-1]
    found: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - node.level + 1]
                origin = ".".join([*base, *([node.module] if node.module else [])])
            else:
                origin = node.module or ""
            if not origin:
                continue
            found.add(origin)
            found.update(f"{origin}.{alias.name}" for alias in node.names if alias.name != "*")
    return found


class Tree:
    """The repository's Python files and what they import, read once. A file that is no regular file (a link
    to a device, say) is not opened, and one that is not UTF-8 is read with replacements; each is listed in
    `notes`, and `unreadable` holds the paths whose imports may therefore be missed."""

    def __init__(self, root: Path = REPOSITORY) -> None:
        self.root = root
        self.files: dict[str, str] = {}
        self.notes: list[str] = []
        self.unreadable: set[str] = set()
        for top in ("src", "tests", "scripts"):
            for file in sorted((root / top).rglob("*.py")):
                if "__pycache__" in file.parts:
                    continue
                path = file.relative_to(root).as_posix()
                try:
                    regular = stat.S_ISREG(file.stat().st_mode)
                except OSError:
                    regular = False
                if not regular:
                    self.notes.append(f"{path} is not a regular file: not read")
                    self.unreadable.add(path)
                    continue
                data = file.read_bytes()
                try:
                    self.files[path] = data.decode("utf-8")
                except UnicodeDecodeError:
                    self.files[path] = data.decode("utf-8", errors="replace")
                    self.notes.append(
                        f"{path} is not valid UTF-8: read with replacements, its imports may be missed"
                    )
                    self.unreadable.add(path)
        self.importers: dict[str, set[str]] = defaultdict(set)
        for path, source in self.files.items():
            for name in imported_names(path, source):
                # Importing `a.b.c` runs `a/__init__.py` and `a/b/__init__.py` first, so the file is an
                # importer of each parent package as well.
                parts = name.split(".")
                for end in range(1, len(parts) + 1):
                    self.importers[".".join(parts[:end])].add(path)
        self._shards: dict[str, tuple[str, ...]] | None = None

    def exists(self, path: str) -> bool:
        return (self.root / path).exists()

    def shards(self) -> dict[str, tuple[str, ...]]:
        """`SHARDS` of `tests/conftest.py`, read without importing it."""
        if self._shards is None:
            tree = ast.parse(self.files["tests/conftest.py"])
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "SHARDS" for target in node.targets
                ):
                    self._shards = {key: tuple(value) for key, value in ast.literal_eval(node.value).items()}
                    break
            else:
                raise ValueError("tests/conftest.py has no SHARDS")
        return self._shards

    def shard_of(self, path: str) -> str | None:
        stem = Path(path).stem
        if Path(path).parent.as_posix() != "tests/property":
            return None
        return next((name for name, modules in self.shards().items() if stem in modules), None)

    def affected(self, paths: Iterable[str]) -> set[str]:
        """The Python files among `paths`, and every file that imports one of them, directly or through
        others. A deleted file is followed by the name it had."""
        reached: set[str] = set()
        queue = deque(path for path in paths if module_name(path))
        while queue:
            path = queue.popleft()
            if path in reached:
                continue
            reached.add(path)
            name = module_name(path)
            if name:
                queue.extend(self.importers.get(name, ()))
        return reached


def is_test_module(path: str) -> bool:
    parts = Path(path).parts
    return (
        parts[0] == "tests"
        and len(parts) > 1
        and parts[1] in TEST_GROUPS
        and Path(path).name.startswith("test_")
        and path.endswith(".py")
    )


def pytest_command(paths: Sequence[str], workers: int, *extra: str) -> tuple[str, ...]:
    return (
        "uv",
        "run",
        "--locked",
        "pytest",
        *paths,
        *extra,
        "-n",
        str(workers),
        "--dist",
        "worksteal",
        "-q",
        "--tb=short",
    )


class Plan:
    """The checks selected for a change, each once, with the paths that selected it."""

    def __init__(self) -> None:
        self._planned: dict[tuple[str, tuple[str, ...]], Planned] = {}

    def add(self, planned: Planned, because: str | None = None) -> None:
        key = (planned.stage, planned.command)
        held = self._planned.setdefault(key, planned)
        if because is not None and because not in held.because:
            held.because.append(because)

    def checks(self) -> list[Planned]:
        order = {stage: number for number, stage in enumerate(STAGES)}
        return sorted(self._planned.values(), key=lambda planned: order[planned.stage])


def generator_environment() -> dict[str, str]:
    """The environment of CI's Python 3.11 check of the generators, kept beside the project's own so that
    neither is rebuilt for the other."""
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return {"UV_PROJECT_ENVIRONMENT": str(cache / "openmaterica" / f"python-{GENERATOR_PYTHON}")}


STATIC_COMMANDS = (
    ("uv", "run", "--locked", "ruff", "check"),
    ("uv", "run", "--locked", "ruff", "format", "--check"),
    ("uv", "run", "--locked", "mypy"),
    ("uv", "run", "--locked", "pyright"),
)
# The rest of CI's static job, run by this script itself (`wheel_check`): its commands are not a list of argv
# the shell does not have to expand, since they name the wheel the build made.
WHEEL_COMMAND = ("python3", "scripts/pre_review.py", "--wheel-check")


def key_arguments(key_file: str | None, root: Path = REPOSITORY) -> tuple[str, ...]:
    """The scan's `--key-file`: the one given, or the clone's `openmaterica.scanKeyFile` (CONTRIBUTING,
    "Confidentiality"); without either the scan reads `CONFIDENTIAL_SCAN_KEY`, or checks the paths alone."""
    if key_file is None:
        configured = git("config", "--get", "openmaterica.scanKeyFile", root=root, check=False).stdout.strip()
        key_file = os.path.expanduser(configured) if configured else None
    return ("--key-file", key_file) if key_file else ()


def plan_checks(
    changed: Sequence[str],
    tree: Tree,
    base: str = DEFAULT_BASE,
    workers: int = 12,
    key_file: str | None = None,
    markers: Sequence[str] = (),
) -> tuple[list[Planned], list[str]]:
    """The checks that apply to `changed`, and the changed paths no rule selects a check for; `markers` are
    the changed READMEs whose kill points markers changed (`changed_markers`)."""
    plan = Plan()
    covered: set[str] = set()

    # Every change. The lock file first: every `uv run` below is `--locked`, so a lock file out of date with
    # `pyproject.toml` is refused, not rewritten behind the builder, and says so before anything else runs.
    plan.add(
        Planned(
            "fast",
            ("uv", "lock", "--check"),
            "the lock file is out of date with pyproject.toml; CI installs with `uv sync --locked`",
        ),
        "every change",
    )
    plan.add(
        Planned(
            "fast",
            ("python3", "scripts/check_signoff.py", base, "HEAD"),
            "every commit is signed off by its author (constraint 1); CI's gate runs it",
            paths=("scripts/check_signoff.py",),
        ),
        "every change",
    )
    plan.add(
        Planned(
            "fast",
            (
                "python3",
                "scripts/check_confidential.py",
                "--messages",
                f"{base}..HEAD",
                *key_arguments(key_file, tree.root),
            ),
            "no tracked file or commit message names a private project or path; CI's gate runs it",
            paths=("scripts/check_confidential.py",),
        ),
        "every change",
    )
    plan.add(
        Planned(
            "fast",
            ("python3", "scripts/check_anomalies.py"),
            "the known-anomalies registry keeps MADDENING's record schema and the package's version; CI's "
            "gate runs it",
            paths=("scripts/check_anomalies.py",),
        ),
        "every change",
    )
    environment = generator_environment()
    plan.add(
        Planned(
            "fast",
            ("uv", "sync", "--locked", "--python", GENERATOR_PYTHON),
            f"the environment of the generators' check on Python {GENERATOR_PYTHON}, as CI makes it",
            env=environment,
        ),
        "every change",
    )
    for generator in GENERATORS:
        plan.add(
            Planned(
                "fast",
                (
                    "uv",
                    "run",
                    "--locked",
                    "--python",
                    GENERATOR_PYTHON,
                    "python",
                    f"scripts/{generator}.py",
                    "--check",
                ),
                "a generated file or a specification table that differs from its source fails CI",
                env=environment,
                paths=(f"scripts/{generator}.py",),
            ),
            "every change",
        )
    plan.add(
        Planned(
            "fast",
            ("python3", "scripts/freeze_schema.py", "--check"),
            "a released schema version's file added, removed or changed (the tests job runs the same check)",
            paths=("scripts/freeze_schema.py",),
        ),
        "every change",
    )
    for path in markers:
        plan.add(
            Planned(
                "fast",
                ("uv", "run", "--locked", "pytest", KILL_COUNTS_TESTS, "-q", "--tb=short"),
                "the kill counts' tests hold the README's markers to the recorded groups by name, which the "
                "generator's `--check` does not; CI runs them in its tests stage, and they take seconds",
                paths=(KILL_COUNTS_TESTS,),
            ),
            f"{path} (a kill points marker added or removed)",
        )

    # A change to code.
    if is_code(changed):
        for command in STATIC_COMMANDS:
            plan.add(
                Planned("fast", command, "CI's static job runs it on every change to code"),
                "a change to code",
            )
        plan.add(
            Planned(
                "fast",
                WHEEL_COMMAND,
                "CI's static job builds the wheel, checks what it ships, and type-checks the consumer "
                "snippet against it (its two controls stay on CI)",
                paths=("scripts/pre_review.py",),
            ),
            "a change to code",
        )

    # The tests of what changed and of what imports it; a property module is run in its shard, whole.
    file_tests: dict[str, list[str]] = defaultdict(list)
    shard_causes: dict[str, list[str]] = defaultdict(list)

    def cause_of(path: str, reason: str | None) -> str:
        return path if reason is None else f"{path} ({reason})"

    def route(test: str, path: str, reason: str | None = None) -> None:
        covered.add(path)
        shard = tree.shard_of(test)
        if shard is None:
            file_tests[test].append(cause_of(path, reason))
        else:
            shard_causes[shard].append(cause_of(path, reason))

    def route_importers(root: str, path: str) -> int:
        """The tests that import `root`, directly or through others, each routed; how many."""
        found = [a for a in sorted(tree.affected([root])) if is_test_module(a) and tree.exists(a)]
        for affected in found:
            route(affected, path)
        return len(found)

    def route_declared(test: str, path: str) -> None:
        """A test a table names, and the tests that import it, whose collection runs its module-level code."""
        if tree.exists(test):
            route(test, path)
            if module_name(test) is not None:
                route_importers(test, path)

    def route_whole_unit(path: str, reason: str) -> None:
        if tree.exists(WHOLE_UNIT_DIRECTORY):
            route(WHOLE_UNIT_DIRECTORY, path, f"{reason}: the whole of {WHOLE_UNIT_DIRECTORY}")

    def route_every_shard(path: str) -> None:
        covered.add(path)
        for shard in tree.shards():
            shard_causes[shard].append(path)

    for path in changed:
        parts = Path(path).parts
        scoped = parts[0] == "tests" and Path(path).name in {"conftest.py", "__init__.py"}
        if matches(CHECKED_BY_THE_STATIC_JOB, path):
            covered.add(path)
        if module_name(path) is not None:
            imported = route_importers(path, path)
            if path in tree.unreadable:
                route_whole_unit(
                    path, "it cannot be read as Python source here, so what imports it is not known"
                )
            elif not (imported or scoped or is_test_module(path) or matches(CHECKED_BY_THE_STATIC_JOB, path)):
                route_whole_unit(path, "no test imports it")
            for tree_reader in TREE_READERS:
                if matches(tree_reader.pattern, path):
                    for test in tree_reader.tests:
                        route_declared(test, path)
        elif parts[0] == "tests" and not matches(CHECKED_BY_THE_STATIC_JOB, path):
            group = parts[1] if len(parts) > 2 else None
            if group not in TEST_GROUPS:
                route_whole_unit(path, "it is under tests/ and in no group of tests")
        if scoped:
            # A conftest, or a package file, applies to every test under its directory.
            directory = Path(path).parent.as_posix()
            group = parts[1] if len(parts) > 2 else None
            if group is None:
                route_every_shard(path)
                for other in tree.files:
                    if is_test_module(other) and tree.shard_of(other) is None:
                        route(other, path)
            elif group == "property":
                route_every_shard(path)
            elif group in TEST_GROUPS:
                route(directory, path)
            else:
                route_whole_unit(path, f"a {Path(path).name} of a directory that is no group of tests")

    # Data files, and the modules that read them.
    for path in changed:
        for rule in DATA_RULES:
            if not matches(rule.pattern, path):
                continue
            for test in rule.tests:
                route_declared(test, path)
            for reader in rule.readers:
                route_importers(reader, path)

    if file_tests:
        names = sorted(file_tests)
        # A path under a directory another names runs with it.
        directories = [name for name in names if (tree.root / name).is_dir()]
        kept = [
            name
            for name in names
            if not any(name != directory and name.startswith(f"{directory}/") for directory in directories)
        ]
        planned = Planned(
            "tests",
            pytest_command(kept, workers),
            "the tests of what changed, of what imports it and of what reads it, at the default profile",
            paths=tuple(kept),
        )
        for name in names:
            for cause in dict.fromkeys(file_tests[name]):
                plan.add(planned, cause)
    for shard in sorted(shard_causes):
        planned = Planned(
            "properties",
            pytest_command(["tests/property"], workers, "--shard", shard),
            f"shard {shard} holds a property module that changed or imports what changed: its properties, "
            "feature audits and mutant searches, at the `ci` profile",
            env={PROFILE_VARIABLE: "ci"},
            paths=("tests/property",),
        )
        for cause in dict.fromkeys(shard_causes[shard]):
            plan.add(planned, cause)

    # Every mutant search's kill point against the recorded one, wherever a shard that holds mutant searches
    # runs, or the file or the README changed.
    searching = [
        cause
        for shard in sorted(shard_causes)
        if any(fnmatch.fnmatch(module, MUTANT_SEARCHES) for module in tree.shards()[shard])
        for cause in shard_causes[shard]
    ]
    searching += [path for path in changed if matches(KILL_COUNTS, path)]
    if searching:
        planned = Planned(
            "properties",
            (
                "uv",
                "run",
                "--locked",
                "python",
                "scripts/gen_kill_counts.py",
                "--measure",
                "--workers",
                str(workers),
            ),
            "every mutant search's kill point is the one tests/property/kill_points.json records, and every "
            "row of the README's tables names a search that ran; CI's controls job checks its own run so",
            env={PROFILE_VARIABLE: "ci"},
            paths=("scripts/gen_kill_counts.py",),
        )
        for cause in dict.fromkeys(searching):
            plan.add(planned, cause)

    for planned in whole_tree(tree.root, workers):
        plan.add(planned, "every change")
    return plan.checks(), [path for path in changed if path not in covered]


def whole_tree(root: Path, workers: int, parts: int = WHOLE_PARTS) -> list[Planned]:
    """Every test of the tree but those `LEFT_TO_CI`, in `parts` runs one after another."""
    ignored = tuple(f"--ignore={path}" for path in LEFT_TO_CI)
    held = sorted(
        path.relative_to(root).as_posix()
        for path in (root / "tests").iterdir()
        if path.is_dir()
        and path.name != "__pycache__"
        and path.relative_to(root).as_posix() not in LEFT_TO_CI
    )
    split = [("--partition", f"{part}/{parts}") for part in range(1, parts + 1)] if parts > 1 else [()]
    left = "; ".join(f"{path}, {why}" for path, why in LEFT_TO_CI.items())
    why = f"every test of the tree but those left to CI ({left}): {', '.join(held)}"
    return [
        Planned(
            "whole", pytest_command(("tests",), workers, *ignored, *part), why, paths=("tests", *LEFT_TO_CI)
        )
        for part in split
    ]


# A figure a message states as a count of something a recount can show: "69,617 test cases", "24 hand
# mutants", "1723 passed", "3 shards". A decimal ("1.5 runs") is read whole, never from its fraction.
FIGURE = re.compile(
    r"(?<![\d.,])\d[\d,]*(?:\.\d+)?\s+(?:[A-Za-z-]+\s+)?"
    r"(?:test cases|test case|cases|case files|files|tests|mutants|examples|runs|properties|shards|passed)\b"
)


def stated_figures(text: str) -> list[str]:
    """Each count in `text` of a kind a recount can show, once, in order."""
    return list(dict.fromkeys(match.group(0) for match in FIGURE.finditer(text)))


def reminders(changed: Sequence[str], stated: Sequence[str]) -> list[str]:
    """What no check here can decide, from the paths changed and the figures stated in the CHANGELOG lines and
    commit messages the branch adds."""
    found: list[str] = []
    if is_code(changed) and "CHANGELOG.md" not in changed:
        found.append(
            "code changed and the CHANGELOG did not: does the change need an entry under Unreleased?"
        )
    if stated:
        found.append(
            "recount each figure the CHANGELOG lines and commit messages state, by what counts that thing "
            "(`pytest --collect-only -q` counts tests, not examples, case files or trace lines): "
            + "; ".join(f'"{figure}"' for figure in stated)
        )
    return found


def describe(planned: Planned) -> str:
    """The command as a shell reads it, quoted, with the environment it sets."""
    environment = " ".join(f"{name}={shell_quote(value)}" for name, value in planned.env.items())
    command = " ".join(shell_quote(argument) for argument in planned.command)
    return f"{environment + ' ' if environment else ''}{command}"


def print_plan(
    checks: Sequence[Planned],
    uncovered: Sequence[str],
    files: Sequence[str],
    to_decide: Sequence[str] = (),
    notes: Sequence[str] = (),
) -> None:
    print(f"{len(files)} changed file(s); {len(checks)} check(s) selected")
    for stage in STAGES:
        staged = [planned for planned in checks if planned.stage == stage]
        if not staged:
            continue
        print(f"\n[{stage}]" + ("" if stage in DEFAULT_STAGES else f" (runs only with --stage {stage})"))
        for planned in staged:
            print(f"  {describe(planned)}")
            print(f"      why: {planned.why}")
            if planned.because:
                shown = ", ".join(printable(cause) for cause in planned.because[:4])
                more = len(planned.because) - 4
                print(f"      selected by: {shown}{f' and {more} more' if more > 0 else ''}")
    if uncovered:
        print("\nno check is selected for these (CI may check them; the self-review list applies):")
        for path in uncovered:
            print(f"  {printable(path)}")
    if notes:
        print("\nnot read as Python:")
        for note in notes:
            print(f"  {printable(note)}")
    if to_decide:
        print("\nfor you to decide (no check can):")
        for reminder in to_decide:
            print(f"  - {reminder}")


Runner = Callable[[Planned, Path], int]


def run_check(planned: Planned, root: Path) -> int:
    environment = {**os.environ, **planned.env}
    return subprocess.run(planned.command, cwd=root, env=environment, check=False).returncode


CONSUMER_SNIPPET = "tests/typing/consumer_snippet.py"
StepRunner = Callable[[Sequence[str], Path], int]


def run_step(command: Sequence[str], directory: Path) -> int:
    print(f"$ {' '.join(shell_quote(argument) for argument in command)}", flush=True)
    return subprocess.run(command, cwd=directory, check=False).returncode


def wheel_check(root: Path = REPOSITORY, run: StepRunner = run_step) -> int:
    """The part of CI's static job after the type checkers, in a temporary directory: build the wheel, check
    what it ships, install it into a virtual environment of its own, and type-check the consumer snippet
    against it with mypy and pyright, from a directory the project's configuration does not reach. The exit
    status is that of the first step that failed. The job's two controls on the snippet check stay on CI."""
    with tempfile.TemporaryDirectory(prefix="pre-review-wheel-") as scratch_name:
        scratch = Path(scratch_name)
        distribution, consumer, snippet = scratch / "dist", scratch / "consumer", scratch / "snippet"
        python = str(consumer / "bin" / "python")
        status = run(("uv", "build", "--out-dir", str(distribution)), root)
        if status != 0:
            return status
        wheels = sorted(glob.glob(str(distribution / "*.whl")))
        if not wheels:
            print("uv build made no wheel", file=sys.stderr)
            return 1
        snippet.mkdir()
        shutil.copy(root / CONSUMER_SNIPPET, snippet)
        steps: tuple[tuple[tuple[str, ...], Path], ...] = (
            (("uv", "run", "--locked", "python", "scripts/check_wheel.py", *wheels), root),
            (("uv", "venv", str(consumer)), root),
            (("uv", "pip", "install", "--python", python, *wheels), root),
            (
                (
                    *("uv", "run", "--locked", "--project", str(root)),
                    *("mypy", "--strict", "--python-executable", python, "consumer_snippet.py"),
                ),
                snippet,
            ),
            (
                (
                    *("uv", "run", "--locked", "--project", str(root)),
                    *("pyright", "--pythonpath", python, "consumer_snippet.py"),
                ),
                snippet,
            ),
        )
        for command, directory in steps:
            status = run(command, directory)
            if status != 0:
                return status
    return 0


def execute(
    checks: Sequence[Planned],
    stages: Sequence[str],
    keep_going: bool,
    root: Path = REPOSITORY,
    runner: Runner = run_check,
) -> tuple[int, list[str]]:
    """Run the checks of `stages` in order; the exit status (1 where any failed) and one summary line each.
    A stage after one that failed is not run, unless `keep_going`."""
    summary: list[str] = []
    failed = False
    for stage in STAGES:
        if stage not in stages:
            summary.append(f"[{stage}] not asked for")
            continue
        staged = [planned for planned in checks if planned.stage == stage]
        if failed and not keep_going:
            summary.extend(f"  not run (an earlier stage failed): {describe(planned)}" for planned in staged)
            continue
        for planned in staged:
            print(f"\n$ {describe(planned)}", flush=True)
            started = time.monotonic()
            status = runner(planned, root)
            seconds = time.monotonic() - started
            failed = failed or status != 0
            summary.append(f"  {'ok    ' if status == 0 else 'FAILED'} {seconds:6.1f} s  {describe(planned)}")
    return (1 if failed else 0), summary


def added_figures(base: str, root: Path = REPOSITORY) -> list[str]:
    """The figures in the CHANGELOG lines the branch adds and in its commit messages."""
    merge_base = git("merge-base", base, "HEAD", root=root).stdout.strip()
    changelog = git("diff", "--no-renames", "-U0", merge_base, "--", "CHANGELOG.md", root=root).stdout
    added = "\n".join(
        line[1:] for line in changelog.splitlines() if line.startswith("+") and not line.startswith("+++")
    )
    messages = git("log", "--format=%B", f"{merge_base}..HEAD", root=root).stdout
    return stated_figures(f"{added}\n{messages}")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the mechanical checks that apply to a branch's changes."
    )
    parser.add_argument(
        "base", nargs="?", default=DEFAULT_BASE, help=f"the ref the branch is based on ({DEFAULT_BASE})"
    )
    parser.add_argument(
        "--list", action="store_true", help="print the checks and what selected them; run none"
    )
    parser.add_argument("--stage", action="append", choices=STAGES, help="run this stage alone (repeatable)")
    parser.add_argument(
        "--workers", type=int, default=min(12, os.cpu_count() or 1), help="pytest-xdist workers"
    )
    parser.add_argument("--keep-going", action="store_true", help="run a stage after one that failed")
    parser.add_argument("--key-file", help="the confidential-names key, else openmaterica.scanKeyFile")
    parser.add_argument("--wheel-check", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args(arguments)
    if options.wheel_check:
        return wheel_check()
    try:
        files = changed_files(options.base)
    except subprocess.CalledProcessError as error:
        print(f"cannot find the changes from {options.base}: {error.stderr.strip()}", file=sys.stderr)
        return 2
    tree = Tree()
    checks, uncovered = plan_checks(
        files,
        tree,
        options.base,
        options.workers,
        options.key_file,
        markers=changed_markers(files, options.base),
    )
    print_plan(checks, uncovered, files, reminders(files, added_figures(options.base)), tree.notes)
    if options.list:
        return 0
    status, summary = execute(checks, options.stage or DEFAULT_STAGES, options.keep_going)
    print("\nsummary")
    print("\n".join(summary))
    skipped = [stage for stage in STAGES if stage not in (options.stage or DEFAULT_STAGES)]
    if skipped:
        print(f"stages not run: {', '.join(skipped)}")
    print("pre-review checks failed" if status else "the pre-review checks that ran passed; CI runs the rest")
    return status


if __name__ == "__main__":
    sys.exit(main())
