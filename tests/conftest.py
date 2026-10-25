# SPDX-License-Identifier: Apache-2.0
"""Hypothesis profiles for every property test, chosen with `MATERICA_HYPOTHESIS_PROFILE`.

`dev` (the default) for a local run and the test matrix, `ci` for CI's Hypothesis job, and `deep` for its
weekly run. A property never sets its own example count, which would override the profile.
"""

import argparse
import os
import sys
import time
from collections import Counter
from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings
from hypothesis.database import DirectoryBasedExampleDatabase

from materica.shapes import Suite
from tests import harvested_constants, partition
from tests.conformance import runner

if sys.platform != "win32":
    import resource

# One example database at a fixed path, whatever the working directory, so that a local run and CI's cached
# copy are the same directory: an example that failed once is replayed first on the next run. `.hypothesis/`
# is git-ignored.
HYPOTHESIS_DATABASE = Path(__file__).resolve().parent.parent / ".hypothesis" / "examples"

# The maintainer's counts: rigour is fixed. `tests/unit/test_hypothesis_profiles.py` holds them, and the
# settings below, to their values, and its controls find these lines by their text.
EXAMPLES = {"dev": 200, "ci": 2_000, "deep": 20_000}

for profile, examples in EXAMPLES.items():
    settings.register_profile(
        profile,
        # Hypothesis's own defaults, not whatever profile is loaded: where `CI` is set, as on GitHub's
        # runners, that is Hypothesis's built-in `ci` profile, whose `derandomize=True` draws the same
        # examples on every run whatever `--hypothesis-seed` says. So no machine's environment changes a
        # setting (`tests/unit/test_hypothesis_profiles.py`).
        parent=settings.get_profile("default"),
        max_examples=examples,
        # Timing on a loaded runner is not a property of the code.
        deadline=None,
        # A CI failure can then be replayed on a machine without the database.
        print_blob=True,
        database=DirectoryBasedExampleDatabase(HYPOTHESIS_DATABASE),
        # Nor is a slow draw on a loaded runner; CI had this from Hypothesis's `ci` profile, and every machine
        # has it now.
        suppress_health_check=[HealthCheck.too_slow],
    )

PROFILE = os.environ.get("MATERICA_HYPOTHESIS_PROFILE", "dev")
if PROFILE not in EXAMPLES:
    raise RuntimeError(f"MATERICA_HYPOTHESIS_PROFILE={PROFILE!r}: expected one of {sorted(EXAMPLES)}")
settings.load_profile(PROFILE)

# Every derandomized run, the mutant searches and the audit controls among them, draws none of the constants
# Hypothesis harvests from the loaded modules, so that what it draws depends on the code alone
# (`harvested_constants.py`).
harvested_constants.pin()


# CI's Hypothesis job runs the property modules in nine shards, `--shard json`, `--shard records`, `--shard
# writer`, `--shard agreement`, `--shard step8_mutants`, `--shard conditions`, `--shard relations`, `--shard
# alternatives` and `--shard build`, the three longest, `agreement`, `relations` and `alternatives`, each as
# two parts side by side (`--shard agreement_1of2`, `--shard agreement_2of2`: the shard's tests in two parts
# of about equal time, `tests/partition.py`); `tests/unit/test_source_files.py` checks that each module is in
# exactly one shard.
SHARDS = {
    "json": (
        "test_jsonio_properties",
        "test_canonical_properties",
        "test_hashing_properties",
        "test_slip_properties",
        "test_mutants",
        "test_mutant_view",
        "test_evaluate_properties",
        "test_evaluate_mutants",
    ),
    "records": (
        "test_envelope_properties",
        "test_version_properties",
        "test_read_properties",
        "test_record_mutants",
        "test_value_field_properties",
        "test_table_form_properties",
        # A table's steps 10 to 13 (S3b-2's HP20 to HP23), which read a table field end to end.
        "test_table_read_properties",
    ),
    "writer": ("test_writer_properties", "test_writer_mutants", "test_writer_mutant_table"),
    # The two JSON Schema libraries' agreement, whose drawn properties run python-jsonschema on every example
    # and were the writer shard's longest tests; and the anomaly check's YAML reader's agreement with PyYAML.
    "agreement": ("test_validators_agree", "test_anomaly_reader_properties"),
    # Step 8's mutant searches, the longest part of the records shard, and their table's check, a table's own
    # (S3a's HP13 to HP16) among them; they keep no example database.
    "step8_mutants": (
        "test_value_field_mutants",
        "test_value_field_mutant_table",
        "test_table_form_mutants",
        "test_table_form_mutant_table",
        # HP13's controls of a fault built to break another member too, derandomised, with no database.
        "test_table_form_controls",
    ),
    # Steps 9 and 10's properties and the result's (S2a-4: HP1, HP2, HP6 and HP11), which read records end to
    # end, their mutant searches, which take seconds and set no example database, so the shard's restored one
    # is harmless to them, and their tables' checks.
    "conditions": (
        "test_condition_properties",
        "test_condition_mutants",
        "test_condition_mutant_table",
        "test_result_properties",
        "test_result_mutants",
        "test_result_mutant_table",
        # The mutant searches of a table's steps 10 to 13 (S3b-2), which take seconds and set no example
        # database, and their table's check.
        "test_table_read_mutants",
        "test_table_read_mutant_table",
        # A request's extrapolation (S3c's HP24 to HP26 and its monotonicity property), which reads a table
        # field end to end, twice an example, its mutant searches and their table's check: here, not in
        # `records`, whose time at `ci` S3b-2's properties brought near a third of its timeout.
        "test_extrapolation_properties",
        "test_extrapolation_mutants",
        "test_extrapolation_mutant_table",
    ),
    # The read's relations (S2a-4's phase B): HP12, the agreement with the reference model, HP4 and HP10, and
    # the information-monotonicity relations, each example reading two records or a read twice, with their
    # mutant searches, which set no example database, their tables' checks, HP12's controls and the audit
    # controls of HP12's floors held at `deep` alone, which run at `deep` alone. A shard of
    # their own: beside steps 9 and 10's they took 198 s at `ci` on four local workers, and `conditions` 151
    # s (2026-10-17).
    "relations": (
        "test_model_properties",
        "test_model_mutants",
        "test_model_mutant_table",
        "test_model_controls",
        "test_model_deep_floor_controls",
        "test_invariance_properties",
        "test_invariance_mutants",
        "test_invariance_mutant_table",
        "test_monotonicity_properties",
        "test_monotonicity_mutants",
        "test_monotonicity_mutant_table",
    ),
    # S4a's step 7 over alternatives (HP27 to HP29), each example reading a field of alternatives and each
    # alternative alone, with their mutant searches and their table's check: a shard of their own, since
    # `relations` already took about a third of its timeout at `ci` on CI (7.4 minutes of 30, 2026-10-17).
    "alternatives": (
        "test_alternatives_properties",
        "test_alternatives_mutants",
        "test_alternatives_mutant_table",
        # S4d's step 7 over a table alternative whose read gives a reason at step 11 (HP39 and HP40), each
        # example reading a field of alternatives and each alternative alone, as S4a's do.
        "test_table_alternatives_properties",
        "test_table_alternatives_mutants",
        "test_table_alternatives_mutant_table",
    ),
    # S7a's build check (the S7 design's 6.1): S7a-1's declaration on its own (HP41 and HP42), and S7a-2's
    # results and verdict (HP43 to HP46), each with its mutant searches, which set no example database, and
    # their table's check. Each example of HP41 and HP42 checks a declaration twice, or three times (HP42),
    # and reads no record; each example of a whole build reads each of its results' records, and checks the
    # build again where it permutes it (HP46).
    "build": (
        "test_declaration_properties",
        "test_declaration_mutants",
        "test_declaration_mutant_table",
        "test_build_properties",
        "test_build_mutants",
        "test_build_mutant_table",
    ),
}


# The mutant searches and the audit controls, which show that the properties and their feature audits can
# fail, by module. They run at the `ci` profile's examples whatever the profile. CI's test matrix runs them on
# the supported range's ends alone, in jobs of their own (`--property-controls only`), and everything else on
# every Python (`--property-controls none`); `tests/unit/test_ci_workflows.py` checks that together the jobs
# leave nothing out. A run without the option runs both. The audit controls of the floors held at `deep` alone
# (marked `deep_controls`) run only at `deep`: every other profile deselects them, whatever the options, since
# a floor held at `deep` alone is judged nowhere else and each control runs `deep`'s 20,000 examples
# (`tests/property/test_model_deep_floor_controls.py`, 2026-10-21).
PROPERTY_CONTROLS = ("test_*mutants*", "test_audit_controls*")


def is_property_control(module: Path) -> bool:
    return any(fnmatch(module.stem, pattern) for pattern in PROPERTY_CONTROLS)


def shard_name(text: str) -> str:
    """A shard of `SHARDS`, or one part of it: `agreement_1of2`."""
    name, _ = partition.split_shard(text)
    if name not in SHARDS:
        raise argparse.ArgumentTypeError(
            f"invalid choice: {text!r} (choose from {', '.join(sorted(SHARDS))})"
        )
    return text


def part_of_selection(text: str) -> str:
    try:
        partition.parse_part(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None
    return text


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--shard",
        type=shard_name,
        help="run only the property modules of this shard, or of part IofN of it: agreement_1of2",
    )
    parser.addoption(
        "--property-controls",
        choices=["only", "none"],
        help="run only the mutant searches and the audit controls, or none of them",
    )
    parser.addoption(
        "--partition",
        type=part_of_selection,
        metavar="I/N",
        help="of the tests the other options select, run only part I of N, parts of about equal time that "
        "together hold every one of them once (tests/partition.py)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    shard = config.getoption("--shard")
    controls = config.getoption("--property-controls")
    split = config.getoption("--partition")
    name, shard_part = partition.split_shard(shard) if shard else (None, None)
    if split is not None and shard_part is not None:
        raise pytest.UsageError(f"--partition {split} with --shard {shard}, which is a part already")

    def kept(item: pytest.Item) -> bool:
        in_shard = name is None or item.path.stem in SHARDS[name]
        deep_alone = PROFILE == "deep" or item.get_closest_marker("deep_controls") is None
        return (
            in_shard
            and deep_alone
            and (controls is None or is_property_control(item.path) == (controls == "only"))
        )

    selected = [item for item in items if kept(item)]
    if part := shard_part or (partition.parse_part(split) if split else None):
        weights = partition.weights_for(PROFILE)
        chosen = partition.in_part([item.nodeid for item in selected], part, weights)
        selected = [item for item, wanted in zip(selected, chosen, strict=True) if wanted]
    run = {id(item) for item in selected}
    config.hook.pytest_deselected(items=[item for item in items if id(item) not in run])
    items[:] = selected


# Each test's CPU time, written beside the wall time in the JUnit XML that CI's durations report reads
# (`scripts/report_test_durations.py`). The xdist workers share a runner's cores, so a test's wall time partly
# measures the others; its CPU time much less. `cpu_seconds` is the CPU time of the test's own process, its
# xdist worker, and `children_cpu_seconds` that of the processes it started and waited for, which the first
# leaves out: a test that runs pytest or git in a subprocess spends its time there. Both span setup, call and
# teardown.
CPU_AT_SETUP = pytest.StashKey[tuple[float, float | None]]()


def children_cpu() -> float | None:
    """The CPU time of the processes this one started that have ended and been waited for; None where Python
    cannot tell (Windows)."""
    if sys.platform == "win32":
        return None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    item.stash[CPU_AT_SETUP] = (time.process_time(), children_cpu())


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> None:
    # What `record_property` does, at the last moment it can: the XML takes a test's properties from its
    # teardown report, which is made after the teardown and copies them when made.
    if call.when == "teardown" and CPU_AT_SETUP in item.stash:
        own, children = item.stash[CPU_AT_SETUP]
        item.user_properties.append(("cpu_seconds", f"{time.process_time() - own:.3f}"))
        children_now = children_cpu()
        if children is not None and children_now is not None:
            item.user_properties.append(("children_cpu_seconds", f"{children_now - children:.3f}"))


# Room on CPython's frame stack for every test on Python 3.11 and 3.12. CPython keeps the frames of running
# calls in 16 KiB chunks and, before 3.13, unmaps a chunk as soon as the call that opened it returns, so a
# call repeated across a chunk's edge maps, faults in and unmaps a chunk at every call (CPython gh-142183,
# fixed in 3.13 and 3.14 by a backport of March 2026 and in 3.15; 3.11 and 3.12 take security fixes only).
# Hypothesis's draws do that: one audit control made 1.52 million `mmap` calls on 3.11 and 264 on 3.13
# (2026-10-20, one local core). So each test runs inside `in_a_large_frame`, whose frame of `FRAME_SLOTS`
# never-set locals gets a 1 MiB chunk of its own (`push_chunk`, CPython's `Python/pystate.c`), and the test's
# frames run in the other half and meet no edge. It changes where frames are kept, not what they compute; a
# test runs two frames deeper. From 3.13 on the spare chunk makes the frame useless, so it is not applied.
# tests/unit/test_frame_room.py holds each case.
FRAME_SLOTS = 65_536
FRAME_CHUNKS_ARE_UNMAPPED = sys.version_info < (3, 13)


def large_frame_function(slots: int) -> Callable[[Callable[[], object]], object]:
    """A function that returns `call()` from a frame with `slots` local variables besides `call`."""
    names = " = ".join(f"_{index}" for index in range(slots))
    source = f"def in_a_large_frame(call):\n    if call is None:\n        {names} = None\n    return call()\n"
    namespace: dict[str, Callable[[Callable[[], object]], object]] = {}
    exec(compile(source, "<in_a_large_frame>", "exec"), namespace)
    return namespace["in_a_large_frame"]


in_a_large_frame = large_frame_function(FRAME_SLOTS)


def pytest_itemcollected(item: pytest.Item) -> None:
    if not FRAME_CHUNKS_ARE_UNMAPPED:
        return
    runtest = item.runtest

    def runtest_in_a_large_frame() -> None:
        in_a_large_frame(runtest)

    # An attribute of the item, which pytest's `pytest_runtest_call` calls as `item.runtest()`.
    item.runtest = runtest_in_a_large_frame  # type: ignore[method-assign]


# Here rather than in `conformance/`, so that it runs where pytest-xdist's controller, which collects nothing,
# writes the summary.
def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """After a run of the conformance tests, which case files ran and which did not, and why."""
    reports = [report for key in ("passed", "failed") for report in terminalreporter.stats.get(key, [])]
    if not any(str(getattr(report, "nodeid", "")).startswith("tests/conformance/") for report in reports):
        return
    runs = runner.run_all(runner.discover(), configurations=runner.CONFIGURATIONS, executors=runner.EXECUTORS)
    outcomes = Counter(case_run.outcome for case_run in runs)
    terminalreporter.section("conformance cases")
    claims = "; ".join(_configuration(claimed) for claimed in runner.CONFIGURATIONS)
    terminalreporter.write_line(
        f"{len(runs)} case files, each under every one of these claims it agrees with: {claims}"
    )
    for outcome in runner.Outcome:
        line = f"  {outcomes[outcome]:4d} {outcome.value}"
        operations = Counter(case_run.case_file.operation for case_run in runs if case_run.outcome is outcome)
        if operations:
            line += " (" + ", ".join(f"{name} {count}" for name, count in sorted(operations.items())) + ")"
        terminalreporter.write_line(line)
        if outcome is runner.Outcome.NOT_YET_RUNNABLE and outcomes[outcome]:
            steps = Counter(
                "+".join(runner.steps(case_run.case_file)) or "no executor"
                for case_run in runs
                if case_run.outcome is outcome
            )
            terminalreporter.write_line(
                "       by step: " + ", ".join(f"{step} {count}" for step, count in sorted(steps.items()))
            )


def _configuration(claimed: frozenset[Suite]) -> str:
    suites = ", ".join(sorted(claimed))
    if claimed != runner.REFERENCE_EVALUATOR:
        return suites
    return f"{suites} (the reference evaluator: {', '.join(map(str, runner.EVALUATOR_CLAIMS))})"
