# SPDX-License-Identifier: Apache-2.0
"""The pre-review script selects the checks a change calls for, and no others, and every check it can select
exists. Each rule has a change that must select its check and one that must not."""

import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts import gen_kill_counts, pre_review
from scripts.pre_review import (
    DATA_RULES,
    GENERATORS,
    LOCATES_NO_RULED_DATA,
    Planned,
    Tree,
    plan_checks,
)
from tests.unit import open_trace
from tests.unit.throwaway_git import throwaway_repository

REPOSITORY = Path(__file__).resolve().parents[2]
CI = (REPOSITORY / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
TREE = Tree(REPOSITORY)
KEY = "KEY"


def plan(*changed: str, tree: Tree = TREE) -> tuple[list[Planned], list[str]]:
    return plan_checks(changed, tree, base="BASE", workers=3, key_file=KEY)


def commands(checks: list[Planned], stage: str | None = None) -> list[str]:
    return [" ".join(check.command) for check in checks if stage is None or check.stage == stage]


def run_paths(checks: list[Planned]) -> set[str]:
    """The paths the planned pytest commands of the tests stage name."""
    return {path for check in checks if check.stage == "tests" for path in check.paths}


def shards(checks: list[Planned]) -> set[str]:
    return {
        check.command[check.command.index("--shard") + 1]
        for check in checks
        if check.stage == "properties" and "--shard" in check.command
    }


# --- what CI runs: the script holds its lists to the workflow's -------------------------------------------


def ci_assignment(name: str) -> str:
    match = re.search(rf"^\s*{name}='([^']*)'$", CI, re.MULTILINE)
    assert match, name
    return match.group(1)


def test_the_documentation_site_and_python_paths_are_the_workflows() -> None:
    assert ci_assignment("docs_paths") == pre_review.DOCUMENTATION_PATHS
    assert ci_assignment("site_paths") == pre_review.SITE_PATHS
    assert ci_assignment("python_paths") == pre_review.PYTHON_PATHS


def test_the_generators_are_the_ones_the_workflow_checks_on_python_3_11() -> None:
    assert set(re.findall(r"scripts/(gen_\w+)\.py --check", CI)) == set(GENERATORS)
    assert f'python-version: "{pre_review.GENERATOR_PYTHON}"' in CI
    assert f"--python {pre_review.GENERATOR_PYTHON}" in CI


# The static job's four steps before the wheel's, as the workflow gives them and with `--locked` as the script
# runs them: written out here, since a table read from the script would drop a step without a test noticing.
STATIC_STEPS = (
    ("uv", "run", "--locked", "ruff", "check"),
    ("uv", "run", "--locked", "ruff", "format", "--check"),
    ("uv", "run", "--locked", "mypy"),
    ("uv", "run", "--locked", "pyright"),
)


def test_the_script_runs_the_static_jobs_four_steps_and_no_other() -> None:
    assert pre_review.STATIC_COMMANDS == STATIC_STEPS
    assert set(commands(plan("src/materica/core/read.py")[0], "fast")) >= {" ".join(c) for c in STATIC_STEPS}


@pytest.mark.parametrize("command", STATIC_STEPS)
def test_each_static_check_is_a_step_of_the_workflows_static_job(command: tuple[str, ...]) -> None:
    # CI syncs the environment with `uv sync --locked` first; the script, which has none, locks each `uv run`.
    in_ci = " ".join(argument for argument in command if argument != "--locked")
    assert f"- run: {in_ci}" in CI
    checks, _ = plan("src/materica/core/read.py")
    assert " ".join(command) in commands(checks, "fast")


def test_the_confidential_sign_off_and_anomaly_checks_are_the_gates_commands() -> None:
    assert 'python3 scripts/check_signoff.py "$BASE" "$HEAD"' in CI
    assert "python3 scripts/check_confidential.py" in CI
    assert "--messages" in CI
    assert "python3 scripts/check_anomalies.py" in CI


# --- the rules, each with a change that selects its check and one that does not ----------------------------


@pytest.mark.parametrize(
    "path", ["CHANGELOG.md", "site/other.html", "src/materica/core/read.py", "scripts/x.sh"]
)
def test_every_change_runs_the_sign_off_scan_anomaly_generators_and_freeze_checks(path: str) -> None:
    fast = commands(plan(path)[0], "fast")
    assert "python3 scripts/check_signoff.py BASE HEAD" in fast
    assert f"python3 scripts/check_confidential.py --messages BASE..HEAD --key-file {KEY}" in fast
    assert "python3 scripts/check_anomalies.py" in fast
    assert "python3 scripts/freeze_schema.py --check" in fast
    for generator in GENERATORS:
        assert any(command.endswith(f"scripts/{generator}.py --check") for command in fast)


def test_the_generators_run_in_their_own_python_3_11_environment_not_the_projects() -> None:
    checks, _ = plan("CHANGELOG.md")
    generated = [check for check in checks if "--check" in check.command and "--python" in check.command]
    synced = [check for check in checks if check.command[:2] == ("uv", "sync")]
    assert len(generated) == len(GENERATORS)
    assert len(synced) == 1
    assert {check.env["UV_PROJECT_ENVIRONMENT"] for check in [*generated, *synced]} == {
        pre_review.generator_environment()["UV_PROJECT_ENVIRONMENT"]
    }
    assert pre_review.generator_environment()["UV_PROJECT_ENVIRONMENT"].endswith("python-3.11")
    assert not any(
        "UV_PROJECT_ENVIRONMENT" in check.env for check in checks if check not in generated + synced
    )


@pytest.mark.parametrize(
    "path", ["src/materica/core/read.py", "README.md", "tests/unit/test_read.py", "typings/x.pyi"]
)
def test_a_change_to_code_runs_the_linters_and_type_checkers(path: str) -> None:
    fast = commands(plan(path)[0], "fast")
    assert {" ".join(command) for command in STATIC_STEPS} <= set(fast)


@pytest.mark.parametrize(
    "path",
    [
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "docs/validation/other.yaml",
        "site/other.html",
        "assets/logo.svg",
    ],
)
def test_a_change_to_documentation_or_the_site_alone_runs_none_of_them(path: str) -> None:
    fast = commands(plan(path)[0], "fast")
    assert not {" ".join(command) for command in STATIC_STEPS} & set(fast)
    assert not {" ".join(pre_review.WHEEL_COMMAND)} & set(fast)


def test_a_change_with_no_path_is_code_as_the_gate_reads_it() -> None:
    assert pre_review.is_code([])
    assert not pre_review.is_code(["CHANGELOG.md", "site/other.html"])
    assert pre_review.is_code(["CHANGELOG.md", "site/other.html", "scripts/x.py"])
    assert pre_review.is_code(["docs/regulatory/helper.py"])  # a Python file is code wherever it sits
    assert not pre_review.is_code(["docs/regulatory/other.md"])


@pytest.mark.parametrize("path", ["CHANGELOG.md", "pyproject.toml", "uv.lock", "src/materica/core/read.py"])
def test_the_lock_file_is_checked_first_whatever_changed(path: str) -> None:
    assert commands(plan(path)[0], "fast")[0] == "uv lock --check"


def test_a_property_module_runs_its_shard_at_ci_and_the_audit_controls_that_import_it() -> None:
    checks, _ = plan("tests/property/test_value_field_properties.py")
    assert "records" in shards(checks)
    assert "tests/unit/test_audit_controls.py" in run_paths(checks)
    assert all(
        check.env == {"MATERICA_HYPOTHESIS_PROFILE": "ci"} for check in checks if check.stage == "properties"
    )
    assert "writer" not in shards(checks)  # control: a shard that holds none of the module's importers


def test_a_mutant_module_and_its_table_run_with_their_shard() -> None:
    assert "writer" in shards(plan("tests/property/test_writer_mutants.py")[0])
    assert "writer" in shards(plan("tests/property/test_writer_mutant_table.py")[0])
    assert "step8_mutants" in shards(plan("tests/property/test_value_field_mutant_table.py")[0])
    assert "step8_mutants" not in shards(plan("tests/property/test_writer_mutant_table.py")[0])


MEASURE = "uv run --locked python scripts/gen_kill_counts.py --measure --workers 3"


@pytest.mark.parametrize(
    "path",
    [
        "tests/property/test_result_mutants.py",
        "tests/property/model_strategies.py",
        "src/materica/core/read.py",
        "tests/property/kill_points.json",
        "tests/property/README.md",
    ],
)
def test_a_change_that_can_move_a_kill_or_a_count_measures_every_search_against_the_file(path: str) -> None:
    checks, uncovered = plan(path)
    assert MEASURE in commands(checks, "properties")
    assert uncovered == []


@pytest.mark.parametrize(
    "path", ["tests/property/test_validators_agree.py", "scripts/check_signoff.py", "CHANGELOG.md"]
)
def test_a_change_that_cannot_move_a_kill_does_not_measure(path: str) -> None:
    """The controls: a shard that holds no mutant search (the agreement), a script, documentation."""
    assert MEASURE not in commands(plan(path)[0])


def test_the_kill_counts_file_and_readme_run_the_generators_tests_and_check() -> None:
    for path in ("tests/property/kill_points.json", "tests/property/README.md"):
        checks, _ = plan(path)
        assert "tests/unit/test_gen_kill_counts.py" in run_paths(checks)
        assert any(
            command.endswith("scripts/gen_kill_counts.py --check") for command in commands(checks, "fast")
        )


KILL_COUNTS_TESTS = "uv run --locked pytest tests/unit/test_gen_kill_counts.py -q --tb=short"


def test_a_kill_points_marker_added_or_removed_runs_the_kill_counts_tests_with_the_fast_checks() -> None:
    """The tests stage runs them for any change of the README; a marker runs them before it, so that a group
    the README gains and the tests do not name fails where a build runs its fast checks (it once failed on CI
    alone)."""
    readme = "tests/property/README.md"
    marked, _ = plan_checks([readme], TREE, base="BASE", workers=3, key_file=KEY, markers=[readme])
    (planned,) = [check for check in marked if " ".join(check.command) == KILL_COUNTS_TESTS]
    assert planned.stage == "fast"
    assert planned.because == [f"{readme} (a kill points marker added or removed)"]
    # control: the README changed elsewhere than a marker leaves them to the tests stage
    unmarked, _ = plan(readme)
    assert KILL_COUNTS_TESTS not in commands(unmarked, "fast")
    assert "tests/unit/test_gen_kill_counts.py" in run_paths(unmarked)


def test_the_kill_points_marker_is_the_generators() -> None:
    assert pre_review.KILL_POINTS_MARKER.pattern == gen_kill_counts.MARKER.pattern


def test_a_property_helper_runs_the_shards_of_the_modules_that_import_it() -> None:
    checks, _ = plan("tests/property/audits.py")
    assert "tests/unit/test_audits.py" in run_paths(checks)
    assert "tests/unit/test_audit_controls.py" in run_paths(checks)
    assert {"json", "records"} <= shards(checks)


def test_a_core_module_runs_the_property_shards_and_the_unit_test_of_what_imports_it() -> None:
    checks, _ = plan("src/materica/core/hashing.py")
    assert "json" in shards(checks)
    assert "tests/unit/test_hashing.py" in run_paths(checks)
    assert "tests/unit/test_check_signoff.py" not in run_paths(
        checks
    )  # control: nothing there imports hashing


def test_a_core_module_the_quickstart_runs_selects_the_quickstarts_test() -> None:
    """The quickstart's doctest imports the package at run time, which the import graph cannot see, so its
    test imports the same names at module level: without that, a change to the read leaves the page's test
    out of the selection and a wrong output shown on the page fails only in CI."""
    for module in ("read", "hashing"):
        assert "tests/examples/test_quickstart.py" in run_paths(plan(f"src/materica/core/{module}.py")[0])
    assert "tests/examples/test_quickstart.py" not in run_paths(
        plan("scripts/check_signoff.py")[0]
    )  # control: a script nothing there imports


def test_a_conftest_applies_to_every_shard_and_the_top_one_to_every_test() -> None:
    assert shards(plan("tests/property/conftest.py")[0]) == set(TREE.shards())
    assert "tests/unit/test_read.py" not in run_paths(plan("tests/property/conftest.py")[0])
    assert "tests/unit/test_read.py" in run_paths(plan("tests/conftest.py")[0])


def test_a_script_runs_its_own_unit_test_and_no_shard_beyond_the_agreement_one() -> None:
    checks, _ = plan("scripts/check_signoff.py")
    assert "tests/unit/test_check_signoff.py" in run_paths(checks)
    assert shards(checks) == set()  # the agreement shard reads the tests' sources, not the scripts'
    assert "tests/unit/test_check_signoff.py" not in run_paths(plan("scripts/check_site.py")[0])  # control


def test_a_specification_file_runs_the_spec_sync_tests_and_the_generators_tests() -> None:
    for path in (
        "docs/specification/overview.md",
        "DOCUMENTATION_ARCHITECTURE.md",
        "design/ARCHITECTURE_DRAFT.md",
    ):
        checks, uncovered = plan(path)
        assert {"tests/spec_sync", "tests/unit/test_generators.py"} <= run_paths(checks)
        assert uncovered == []
        assert shards(checks) == set()
    assert run_paths(plan("docs/regulatory/other.md")[0]) == set()  # control: not a specification file


def test_a_schema_file_runs_the_spec_sync_tests_and_the_shards_of_what_reads_it() -> None:
    checks, _ = plan("src/materica/schema/0.1/record.writer.json")
    assert {"tests/spec_sync", "tests/unit/test_shapes.py"} <= run_paths(checks)
    assert {"writer", "agreement"} <= shards(checks)
    assert run_paths(plan("src/materica/data/conformance/plain_read/CASES.md")[0]).isdisjoint(
        {"tests/unit/test_shapes.py"}
    )


def test_a_conformance_case_runs_the_conformance_and_spec_sync_tests() -> None:
    checks, _ = plan("src/materica/data/conformance/plain_read/CASES.md")
    assert {"tests/conformance", "tests/spec_sync"} <= run_paths(checks)


def test_a_spec_sync_table_runs_the_spec_sync_tests_alone() -> None:
    checks, _ = plan("tests/spec_sync/name_overlaps.json")
    assert run_paths(checks) == {"tests/spec_sync"}
    assert shards(checks) == set()


def test_a_workflow_runs_the_workflow_tests_and_a_site_file_does_not() -> None:
    assert "tests/unit/test_ci_workflows.py" in run_paths(plan(".github/workflows/repeat.yml")[0])
    assert run_paths(plan("site/other.html")[0]) == set()


def test_the_build_files_run_the_tests_that_hold_the_pythons_and_the_profiles() -> None:
    assert {"tests/unit/test_python_versions.py", "tests/unit/test_hypothesis_profiles.py"} <= run_paths(
        plan("pyproject.toml")[0]
    )


def test_a_directory_named_runs_the_tests_under_it_once() -> None:
    checks, _ = plan("docs/specification/provenance.md", "tests/spec_sync/test_t1.py")
    (command,) = [check.command for check in checks if check.stage == "tests"]
    assert "tests/spec_sync" in command
    assert "tests/spec_sync/test_t1.py" not in command


def test_a_change_selects_each_check_once_with_every_path_that_selected_it() -> None:
    checks, _ = plan("docs/specification/provenance.md", "docs/specification/uncertainty.md")
    (run,) = [check for check in checks if check.stage == "tests"]
    assert run.because == ["docs/specification/provenance.md", "docs/specification/uncertainty.md"]
    keys = [(check.stage, check.command) for check in checks]
    assert len(keys) == len(set(keys))


def test_a_change_no_rule_selects_a_check_for_is_listed() -> None:
    assert plan("CHANGELOG.md")[1] == ["CHANGELOG.md"]
    assert plan("tests/conformance/README.md")[1] == ["tests/conformance/README.md"]
    assert plan("site/other.html", "scripts/check_signoff.py")[1] == ["site/other.html"]  # control: covered


def test_the_stages_run_in_order() -> None:
    checks, _ = plan("src/materica/core/hashing.py", "docs/specification/provenance.md")
    stages = [check.stage for check in checks]
    assert stages == sorted(stages, key=pre_review.STAGES.index)
    assert set(stages) == set(pre_review.STAGES)


# --- what reads the whole tree, and what the script cannot map --------------------------------------------


def selects(checks: list[Planned], test: str, tree: Tree = TREE) -> bool:
    """Whether the planned checks run the test file: by its path, by a directory above it, or by its shard."""
    if tree.shard_of(test) is not None:
        return tree.shard_of(test) in shards(checks)
    return any(test == path or test.startswith(f"{path}/") for path in run_paths(checks))


@pytest.fixture
def no_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Switch off the whole-directory fallback, so that the declared readers are not satisfied by it."""
    monkeypatch.setattr(pre_review, "WHOLE_UNIT_DIRECTORY", "tests/nowhere")


READERS_OF_THE_CORE = (
    "tests/unit/test_source_files.py",
    "tests/unit/test_read.py",
    "tests/spec_sync/test_reason_steps.py",
    "tests/spec_sync/test_build_reasons.py",
    "tests/unit/test_pre_review.py",
)


@pytest.mark.usefixtures("no_fallback")
def test_a_new_core_module_selects_the_tests_that_list_every_core_module() -> None:
    checks, uncovered = plan("src/materica/core/zz_new.py")
    assert all(selects(checks, test) for test in READERS_OF_THE_CORE)
    assert uncovered == []
    # control: a module beside the core is listed by the source-file tests, not by the two of the core
    beside, _ = plan("src/materica/zz_new.py")
    assert selects(beside, "tests/unit/test_source_files.py")
    assert not selects(beside, "tests/unit/test_read.py")
    assert not selects(beside, "tests/spec_sync/test_reason_steps.py")
    assert not selects(beside, "tests/spec_sync/test_build_reasons.py")


@pytest.mark.usefixtures("no_fallback")
def test_a_script_selects_the_workflow_tests_that_forbid_it_to_name_a_documentation_path() -> None:
    assert selects(plan("scripts/check_signoff.py")[0], "tests/unit/test_ci_workflows.py")
    assert selects(plan("tests/unit/test_zz_new.py")[0], "tests/unit/test_ci_workflows.py")
    # control: a Python file outside the three directories it reads
    assert not selects(plan("docs/regulatory/zz_new.py")[0], "tests/unit/test_ci_workflows.py")


@pytest.mark.usefixtures("no_fallback")
def test_a_property_module_outside_every_shard_selects_the_tests_that_list_the_shards() -> None:
    checks, uncovered = plan("tests/property/test_zz_new.py")
    assert selects(checks, "tests/unit/test_source_files.py")
    assert uncovered == []
    assert "writer" not in shards(checks)  # control: it is in no shard, so no shard but the readers' is run


@pytest.mark.usefixtures("no_fallback")
def test_a_new_test_that_calls_the_verdicts_selects_the_agreement_shard_that_compares_every_test() -> None:
    assert "agreement" in shards(plan("tests/unit/test_zz_verdict.py")[0])
    assert "agreement" not in shards(plan("scripts/check_signoff.py")[0])  # control: it reads the tests only


def test_a_python_file_no_test_imports_selects_the_whole_unit_directory_and_says_why() -> None:
    for path in (
        "scripts/zz_new.py",
        "tests/fuzz/zz_new.py",
        "src/materica/zz_new.py",
        "docs/regulatory/zz.py",
    ):
        checks, uncovered = plan(path)
        (run,) = [check for check in checks if check.stage == "tests"]
        assert "tests/unit" in run.paths
        assert uncovered == []
        assert any(cause.startswith(path) and "no test imports it" in cause for cause in run.because)
    # controls: what a test imports, a test, and the snippet the static job type-checks
    for path in (
        "scripts/check_signoff.py",
        "src/materica/core/hashing.py",
        "tests/unit/test_read.py",
        "tests/typing/consumer_snippet.py",
    ):
        checks, _ = plan(path)
        assert "tests/unit" not in run_paths(checks), path


def test_a_file_under_tests_outside_every_group_selects_the_whole_unit_directory_and_says_why() -> None:
    for path in ("tests/README.md", "tests/fuzz/README.md", "tests/fuzz/json.dict"):
        checks, uncovered = plan(path)
        (run,) = [check for check in checks if check.stage == "tests"]
        assert "tests/unit" in run.paths
        assert uncovered == []
        assert any("in no group of tests" in cause for cause in run.because)
    # controls: a file in a group of tests that no rule reads is listed; the snippet's is the static job's
    checks, uncovered = plan("tests/conformance/README.md")
    assert uncovered == ["tests/conformance/README.md"]
    assert "tests/unit" not in run_paths(checks)
    checks, uncovered = plan("tests/typing/zz_other.md")
    assert "tests/unit" not in run_paths(checks)
    assert uncovered == []


@pytest.mark.parametrize(
    ("path", "selected", "not_selected"),
    [
        ("tests/unit/conftest.py", "tests/unit", "tests/spec_sync"),
        ("tests/spec_sync/conftest.py", "tests/spec_sync", "tests/unit"),
        ("tests/conformance/conftest.py", "tests/conformance", "tests/unit"),
        ("tests/unit/__init__.py", "tests/unit", "tests/spec_sync"),
        ("tests/examples/__init__.py", "tests/examples", "tests/unit"),
    ],
)
def test_a_conftest_or_package_file_of_a_group_of_tests_selects_that_directorys_tests(
    path: str, selected: str, not_selected: str
) -> None:
    checks, uncovered = plan(path)
    assert selected in run_paths(checks)
    assert not_selected not in run_paths(checks)
    assert shards(checks) != set(TREE.shards())  # control: a conftest of one group was every shard
    assert uncovered == []
    (run,) = [check for check in checks if check.stage == "tests"]
    assert not any("no test imports it" in cause for cause in run.because)


def test_a_conftest_of_a_directory_that_is_no_group_selects_the_whole_unit_directory() -> None:
    checks, _ = plan("tests/fuzz/conftest.py")
    assert "tests/unit" in run_paths(checks)


# Each pair is a file that a test opens (the trace below finds them) and the tests it must select.
PROVENANCE_READERS = (
    "tests/unit/test_audit_controls.py",
    "tests/unit/test_verdicts.py",
    "tests/property/test_validators_agree.py",
    "tests/property/test_condition_mutant_table.py",
)
PLAIN_READ = "src/materica/data/conformance/plain_read/inputs"
SCHEMA_READERS = ("tests/unit/test_freeze_schema.py", "tests/unit/test_schema_index.py")


@pytest.mark.parametrize(
    ("path", "tests"),
    [
        *(
            (f"docs/specification/{name}.md", PROVENANCE_READERS)
            for name in ("provenance", "record_format", "uncertainty")
        ),
        ("docs/specification/read_side_contract.md", ("tests/reference/test_cases.py",)),
        ("docs/specification/declarations.md", ("tests/reference/test_build_results_model.py",)),
        (
            "src/materica/schema/0.1/vocabulary/coverage.json",
            ("tests/reference/test_build_results_model.py",),
        ),
        ("src/materica/core/acceptance.py", ("tests/reference/test_build_results_model.py",)),
        (
            "src/materica/data/conformance/build_checks/inputs/water_fixture.json",
            ("tests/reference/test_build_results_model.py", "tests/reference/test_seeded_faults.py"),
        ),
        (f"{PLAIN_READ}/water_fixture.json", ("tests/unit/test_read.py", "tests/unit/test_conditions.py")),
        (
            f"{PLAIN_READ}/water_overlay_fixture.json",
            ("tests/unit/test_read.py", "tests/unit/test_conditions.py"),
        ),
        ("src/materica/schema/0.1/README.md", SCHEMA_READERS),
        ("src/materica/schema/0.1/record.writer.json", SCHEMA_READERS),
        ("tests/spec_sync/released_schemas.json", ("tests/unit/test_schema_index.py",)),
        ("examples/records/water.json", ("tests/examples/test_example_records.py",)),
        ("examples/README.md", ("tests/examples/test_example_records.py",)),
        ("README.md", ("tests/examples/test_example_records.py",)),
        (
            "docs/user_guide/quickstart.md",
            ("tests/examples/test_quickstart.py", "tests/examples/test_example_records.py"),
        ),
        ("scripts/pre-push", ("tests/unit/test_check_confidential.py",)),
        ("tests/property/kill_points.json", ("tests/unit/test_gen_kill_counts.py",)),
        ("tests/property/README.md", ("tests/unit/test_gen_kill_counts.py",)),
        (
            ".github/workflows/ci.yml",
            (
                "tests/unit/test_pre_review.py",
                "tests/unit/test_python_versions.py",
                "tests/unit/test_source_files.py",
                "tests/unit/test_ci_workflows.py",
            ),
        ),
    ],
)
def test_a_data_file_selects_each_test_that_opens_it(path: str, tests: tuple[str, ...]) -> None:
    checks, uncovered = plan(path)
    assert uncovered == []
    assert [test for test in tests if not selects(checks, test)] == []


def test_a_data_file_no_test_opens_does_not_select_those_tests() -> None:
    # controls: a specification file the tests do not open, a conformance case, another workflow, a table
    other = plan("docs/specification/changes.md")[0]
    assert not any(selects(other, test) for test in PROVENANCE_READERS)
    case = plan("src/materica/data/conformance/plain_read/CASES.md")[0]
    assert not any(selects(case, test) for test in (*SCHEMA_READERS, "tests/unit/test_read.py"))
    workflow = plan(".github/workflows/repeat.yml")[0]
    assert not selects(workflow, "tests/unit/test_python_versions.py")
    assert not selects(workflow, "tests/unit/test_pre_review.py")
    assert not selects(plan("tests/spec_sync/name_overlaps.json")[0], "tests/unit/test_schema_index.py")


# --- hostile names and files ------------------------------------------------------------------------------

NAMES = [
    "tests/unit/test_$(touch pwned2).py",
    "tests/unit/test_semi;touch pwned.py",
    "tests/unit/test_--collect-only.py",
    "tests/unit/test_a b.py",
    "tests/unit/test_new\nline.py",
    "tests/unit/test_\x1b[31mred.py",
    "tests/unit/test_it's.py",
    "tests/unit/test_é.py",
]


@pytest.mark.parametrize("name", NAMES)
def test_a_printed_argument_pastes_back_as_the_same_argument_and_runs_nothing(
    name: str, tmp_path: Path
) -> None:
    quoted = pre_review.shell_quote(name)
    done = subprocess.run(
        ["bash", "-c", f"printf %s {quoted}"], capture_output=True, check=True, cwd=tmp_path
    )
    assert done.stdout == name.encode()
    assert list(tmp_path.iterdir()) == []


def test_the_same_names_joined_without_quoting_would_run_a_command(tmp_path: Path) -> None:
    # control: the printed command of the first version, `" ".join(command)`, executes the name's `$(...)`
    subprocess.run(["bash", "-c", f"printf %s {NAMES[0]}"], capture_output=True, check=True, cwd=tmp_path)
    assert [path.name for path in tmp_path.iterdir()] == ["pwned2"]


@pytest.mark.parametrize("name", NAMES)
def test_a_name_is_printed_with_no_control_character_in_it(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    def printed(text: str) -> str:
        checks = [Planned("tests", ("uv", "run", "pytest", text), "why", because=[text])]
        pre_review.print_plan(checks, [text], [text], notes=[text])
        return capsys.readouterr().out

    out, plain = printed(name), printed("tests/unit/test_plain.py")
    assert {character for character in out if unicodedata.category(character) == "Cc"} <= {"\n"}
    assert out.count("\n") == plain.count("\n")  # a newline in a name does not add a line


@pytest.mark.parametrize("name", NAMES)
def test_a_hostile_test_name_reaches_pytest_as_one_argument_and_nothing_runs(
    name: str, tmp_path: Path
) -> None:
    tree = small_tree(tmp_path)
    (tmp_path / name).write_text("from pkg import a\n", encoding="utf-8")
    tree = Tree(tmp_path)
    checks, _ = plan(name, tree=tree)
    (run,) = [check for check in checks if check.stage == "tests"]
    assert name in run.command
    assert run.command.count(name) == 1
    assert not any(name.startswith("pwned") for _, _, names in os.walk(tmp_path) for name in names)


def test_a_file_that_is_no_regular_file_is_not_opened_and_one_that_is_not_utf_8_is_reported(
    tmp_path: Path,
) -> None:
    small_tree(tmp_path)
    assert Tree(tmp_path).notes == []  # control: a tree of ordinary files has no note
    (tmp_path / "src/pkg/zero.py").symlink_to("/dev/zero")
    (tmp_path / "src/pkg/latin.py").write_bytes(b"x = '\xe9'\n")
    (tmp_path / "src/pkg/gone.py").symlink_to(tmp_path / "nowhere")
    tree = Tree(tmp_path)  # a read of /dev/zero would not return
    assert not {"src/pkg/zero.py", "src/pkg/gone.py"} & set(tree.files)
    assert "src/pkg/latin.py" in tree.files
    assert sorted(tree.notes) == [
        "src/pkg/gone.py is not a regular file: not read",
        "src/pkg/latin.py is not valid UTF-8: read with replacements, its imports may be missed",
        "src/pkg/zero.py is not a regular file: not read",
    ]
    for path in ("src/pkg/zero.py", "src/pkg/latin.py"):
        checks, uncovered = plan(path, tree=tree)
        (run,) = [check for check in checks if check.stage == "tests"]
        assert "tests/unit" in run.paths
        assert uncovered == []
        assert any(cause.startswith(path) for cause in run.because)


def test_the_script_names_a_file_it_cannot_read_instead_of_failing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    small_tree(tmp_path)
    (tmp_path / "src/pkg/latin.py").write_bytes(b"x = '\xe9'\n")
    tree = Tree(tmp_path)
    checks, uncovered = plan("src/pkg/latin.py", tree=tree)
    pre_review.print_plan(checks, uncovered, ["src/pkg/latin.py"], notes=tree.notes)
    assert "src/pkg/latin.py is not valid UTF-8" in capsys.readouterr().out


def test_a_file_that_is_not_utf_8_sends_its_change_to_the_whole_unit_directory_though_a_test_imports_it(
    tmp_path: Path,
) -> None:
    small_tree(tmp_path)
    (tmp_path / "src/pkg/latin.py").write_bytes(b"x = '\xe9'\n")
    (tmp_path / "tests/unit/test_latin.py").write_text("from pkg import latin\n", encoding="utf-8")
    checks, _ = plan("src/pkg/latin.py", tree=Tree(tmp_path))
    (run,) = [check for check in checks if check.stage == "tests"]
    assert "tests/unit" in run.paths  # what it imports, and so what imports it, is not known
    assert any("cannot be read as Python source" in cause for cause in run.because)
    # control: the same file in UTF-8, imported by the same test, selects that test alone
    (tmp_path / "src/pkg/latin.py").write_text("x = 1\n", encoding="utf-8")
    checks, _ = plan("src/pkg/latin.py", tree=Tree(tmp_path))
    assert run_paths(checks) == {"tests/unit/test_latin.py"}


def test_a_test_a_table_names_selects_the_tests_that_import_it_as_their_collection_runs_its_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    small_tree(tmp_path)
    (tmp_path / "tests/unit/test_reads.py").write_text("X = 1\n", encoding="utf-8")
    (tmp_path / "tests/unit/test_imports_it.py").write_text(
        "from tests.unit.test_reads import X\n", encoding="utf-8"
    )
    (tmp_path / "tests/unit/test_alone.py").write_text("Y = 2\n", encoding="utf-8")
    table = (pre_review.TreeReader(r"src/pkg/c\.py", "reads it", ("tests/unit/test_reads.py",)),)
    monkeypatch.setattr(pre_review, "TREE_READERS", table)
    checks, _ = plan("src/pkg/c.py", tree=Tree(tmp_path))
    assert {"tests/unit/test_reads.py", "tests/unit/test_imports_it.py"} <= run_paths(checks)
    assert "tests/unit/test_alone.py" not in run_paths(checks)  # control


# --- the names as the gate reads them -----------------------------------------------------------------------


def ci_says_code(lines: str) -> bool:
    """CI's `code` for the names `git diff --name-only` printed, by the gate's own `grep` lines."""
    script = (
        'if [ -n "$changed" ] && ! grep -qxE "$python_paths" <<< "$changed" '
        '&& ! grep -qvxE "$docs_paths|$site_paths" <<< "$changed"; then echo false; else echo true; fi'
    )
    environment = {
        "changed": lines.rstrip("\n"),
        **{name: ci_assignment(name) for name in ("python_paths", "docs_paths", "site_paths")},
    }
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=environment, check=True)
    return done.stdout.strip() == "true"


GATE_CASES = [
    ["CHANGELOG.md"],
    ["docs/regulatory/plain.md", "site/page.html"],
    ["docs/regulatory/é.md"],
    ["docs/regulatory/tab\there.md"],
    ['docs/regulatory/quote".md'],
    ["docs/regulatory/back\\slash.md"],
    ["site/é.html", "CHANGELOG.md"],
    ["docs/regulatory/helper.py"],
    ["docs/regulatory/é.py"],
    ["CONTRIBUTING.md", "scripts/x.sh"],
]


@pytest.mark.parametrize("names", GATE_CASES, ids=lambda names: "+".join(names))
def test_a_change_is_code_as_the_gate_reads_the_names_git_prints(names: list[str], repository: Path) -> None:
    commit("base", "--allow-empty")
    for name in names:
        (repository / name).parent.mkdir(parents=True, exist_ok=True)
        (repository / name).write_text("x")
    subprocess.run(["git", "add", "-A"], check=True)
    listed = subprocess.run(
        ["git", "diff", "--cached", "--no-renames", "--name-only"], capture_output=True, text=True, check=True
    ).stdout
    assert pre_review.is_code(names) == ci_says_code(listed)
    assert {pre_review.git_quoted(name) for name in names} == set(listed.splitlines())


def test_a_documentation_file_with_an_accent_in_its_name_is_code_to_the_gate_and_so_to_the_script() -> None:
    assert re.fullmatch(
        f"{pre_review.DOCUMENTATION_PATHS}", "docs/regulatory/é.md"
    )  # control: read raw, it is docs
    assert pre_review.is_code(["docs/regulatory/é.md"])
    assert not pre_review.is_code(
        ["docs/regulatory/e.md"]
    )  # control: the same name in ASCII is documentation


# --- the import graph --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "source", "names"),
    [
        ("tests/a.py", "import x.y\nimport z as w", {"x.y", "z"}),
        ("tests/a.py", "from x import y, z", {"x", "x.y", "x.z"}),
        ("tests/a.py", "from x import *", {"x"}),
        ("tests/property/a.py", "from . import b", {"tests.property", "tests.property.b"}),
        ("tests/property/a.py", "from .b import c", {"tests.property.b", "tests.property.b.c"}),
        ("tests/property/a.py", "from ..unit import d", {"tests.unit", "tests.unit.d"}),
        ("src/materica/core/__init__.py", "from . import jsonio", {"materica.core", "materica.core.jsonio"}),
        ("tests/a.py", "def f(:", set[str]()),
    ],
)
def test_imported_names(path: str, source: str, names: set[str]) -> None:
    assert pre_review.imported_names(path, source) == names


@pytest.mark.parametrize(
    ("path", "name"),
    [
        ("src/materica/core/read.py", "materica.core.read"),
        ("src/materica/core/__init__.py", "materica.core"),
        ("src/materica/shapes.pyi", "materica.shapes"),
        ("tests/property/strategies.py", "tests.property.strategies"),
        ("scripts/pre_review.py", "scripts.pre_review"),
        ("README.md", None),
    ],
)
def test_module_names(path: str, name: str | None) -> None:
    assert pre_review.module_name(path) == name


def small_tree(tmp_path: Path) -> Tree:
    files = {
        "src/pkg/__init__.py": "",
        "src/pkg/a.py": "",
        "src/pkg/b.py": "from pkg import a",
        "src/pkg/c.py": "",
        "tests/conftest.py": 'SHARDS = {"one": ("test_p",), "two": ("test_q",)}\n',
        "tests/unit/test_b.py": "from pkg import b",
        "tests/unit/test_c.py": "from pkg import c",
        "tests/property/test_p.py": "from pkg import b",
        "tests/property/test_q.py": "from pkg import c",
        "tests/spec_sync/test_s.py": "",
        "docs/specification/x.md": "",
    }
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    return Tree(tmp_path)


def test_a_change_reaches_what_imports_it_through_others_and_not_what_does_not(tmp_path: Path) -> None:
    tree = small_tree(tmp_path)
    checks, _ = plan("src/pkg/a.py", tree=tree)
    assert run_paths(checks) == {"tests/unit/test_b.py"}  # through b
    assert shards(checks) == {"one"}  # control: two imports only c


def test_importing_a_module_reaches_the_package_files_it_runs_and_not_their_siblings(tmp_path: Path) -> None:
    for name, text in {
        "src/pkg/__init__.py": "",
        "src/pkg/sub/__init__.py": "",
        "src/pkg/sub/deep.py": "",
        "src/pkg/sub/other.py": "",
        "src/pkg/top.py": "",
        "tests/conftest.py": "SHARDS = {}\n",
        "tests/unit/test_deep.py": "import pkg.sub.deep",
        "tests/unit/test_top.py": "from pkg import top",
    }.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    tree = Tree(tmp_path)
    assert tree.importers["pkg.sub"] == {"tests/unit/test_deep.py"}  # `pkg.sub.deep` runs pkg/sub/__init__.py
    assert run_paths(plan("src/pkg/sub/__init__.py", tree=tree)[0]) == {"tests/unit/test_deep.py"}
    assert run_paths(plan("src/pkg/__init__.py", tree=tree)[0]) == {
        "tests/unit/test_deep.py",
        "tests/unit/test_top.py",
    }
    # control: a module beside the package file is run only by what imports it, which nothing here does
    assert tree.importers["pkg.sub.other"] == set()
    assert "tests/unit/test_top.py" not in run_paths(plan("src/pkg/sub/__init__.py", tree=tree)[0])


@pytest.mark.parametrize(
    ("package_file", "test", "imports_only"),
    [
        ("src/materica/__init__.py", "tests/unit/test_slips.py", "materica.core.slips"),
        ("scripts/__init__.py", "tests/unit/test_schema_index.py", "scripts.freeze_schema"),
        ("tests/fuzz/__init__.py", "tests/unit/test_fuzz_oracle.py", "tests.fuzz.field_oracle"),
    ],
)
@pytest.mark.usefixtures("no_fallback")  # the whole-directory fallback would select the test without the rule
def test_a_package_file_selects_a_test_that_imports_only_a_module_under_it(
    package_file: str, test: str, imports_only: str
) -> None:
    names = pre_review.imported_names(test, TREE.files[test])
    assert imports_only in names  # control: the test names the module, never the package itself
    package = pre_review.module_name(package_file)
    assert package is not None
    assert package not in names
    assert selects(plan(package_file)[0], test)
    assert all(test not in reader.tests for reader in pre_review.TREE_READERS)  # no declared reader


def test_a_deleted_module_still_reaches_what_imported_it(tmp_path: Path) -> None:
    tree = small_tree(tmp_path)
    (tmp_path / "src/pkg/a.py").unlink()
    assert run_paths(plan("src/pkg/a.py", tree=tree)[0]) == {"tests/unit/test_b.py"}


def test_a_deleted_test_is_not_run(tmp_path: Path) -> None:
    tree = small_tree(tmp_path)
    (tmp_path / "tests/unit/test_b.py").unlink()
    assert run_paths(plan("tests/unit/test_b.py", tree=tree)[0]) == set()


def test_the_citation_test_runs_for_a_specification_file_where_it_exists_and_only_there(
    tmp_path: Path,
) -> None:
    tree = small_tree(tmp_path)
    assert pre_review.CITATION_TEST not in run_paths(plan("docs/specification/x.md", tree=tree)[0])
    (tmp_path / "tests/reference").mkdir()
    (tmp_path / pre_review.CITATION_TEST).write_text("", encoding="utf-8")
    assert pre_review.CITATION_TEST in run_paths(plan("docs/specification/x.md", tree=Tree(tmp_path))[0])
    # control: a change that is no specification file does not select it
    assert pre_review.CITATION_TEST not in run_paths(plan("src/pkg/c.py", tree=Tree(tmp_path))[0])


# --- every check it can run exists -----------------------------------------------------------------------


def everything_changed() -> list[str]:
    """A change that matches every rule: one file of each kind of path the rules name."""
    return [
        "src/materica/core/read.py",
        "tests/conftest.py",
        "tests/property/conftest.py",
        *(f"tests/property/{module}.py" for modules in TREE.shards().values() for module in modules),
        "scripts/check_signoff.py",
        "pyproject.toml",
        "docs/specification/provenance.md",
        "src/materica/schema/0.1/record.writer.json",
        "src/materica/data/conformance/plain_read/CASES.md",
        "tests/spec_sync/name_overlaps.json",
        ".github/workflows/ci.yml",
        "scripts/confidential_digests.txt",
    ]


def test_every_path_a_check_names_exists() -> None:
    checks, uncovered = plan(*everything_changed())
    assert uncovered == []
    for check in checks:
        for path in check.paths:
            assert (REPOSITORY / path).exists(), f"{path} in: {' '.join(check.command)}"
    assert {check.stage for check in checks} == set(pre_review.STAGES)


def test_every_path_a_data_rule_names_exists_but_the_optional_citation_test() -> None:
    for rule in DATA_RULES:
        for path in (*rule.tests, *rule.readers):
            if path != pre_review.CITATION_TEST:
                assert (REPOSITORY / path).exists(), f"{path} in the rule for {rule.name}"
        assert re.compile(rule.pattern)


def test_every_shard_a_check_names_is_one_of_the_conftests() -> None:
    checks, _ = plan(*everything_changed())
    assert shards(checks) == set(TREE.shards())


@pytest.mark.parametrize("shard", sorted(Tree(REPOSITORY).shards()))
def test_pytest_collects_each_shard_the_checks_name(shard: str) -> None:
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/property",
            "--shard",
            shard,
            "--collect-only",
            "-q",
            "-p",
            "no:xdist",
        ],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout[-500:] + done.stderr[-500:]
    assert re.search(r"\b\d+ tests? collected\b", done.stdout)


def test_every_helper_that_finds_a_data_file_by_its_own_location_is_a_reader_or_listed_why_not() -> None:
    readers = {reader for rule in DATA_RULES for reader in rule.readers}
    found = {
        path
        for path, source in TREE.files.items()
        if not Path(path).name.startswith("test_")
        if "resources.files" in source or "__file__" in source
    }
    assert found - readers - set(LOCATES_NO_RULED_DATA) == set()
    assert set(LOCATES_NO_RULED_DATA) <= found, "an entry for a module that no longer locates files"
    assert readers <= set(TREE.files), "a reader that does not exist"


# --- the changes, read from git ---------------------------------------------------------------------------


def commit(message: str, *options: str) -> None:
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.org",
            "commit",
            "-q",
            *options,
            "-m",
            message,
        ],
        check=True,
    )


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return throwaway_repository(tmp_path, monkeypatch)


def test_the_changes_are_committed_staged_unstaged_untracked_deleted_and_renamed_files(
    repository: Path,
) -> None:
    for name in ("kept", "edited", "staged", "deleted", "moved", "untouched"):
        (repository / name).write_text(name)
    commit("base")
    subprocess.run(["git", "checkout", "-q", "-b", "branch"], check=True)
    (repository / "edited").write_text("changed")
    commit("on the branch")
    (repository / "staged").write_text("changed")
    subprocess.run(["git", "add", "staged"], check=True)
    (repository / "kept").write_text("changed, not staged")
    (repository / "deleted").unlink()
    (repository / "moved").rename(repository / "moved_to")
    (repository / "new").write_text("untracked")
    assert pre_review.changed_files("main", repository) == [
        "deleted",
        "edited",
        "kept",
        "moved",
        "moved_to",
        "new",
        "staged",
    ]


def test_the_changes_are_from_the_merge_base_not_from_the_base_tip(repository: Path) -> None:
    (repository / "a").write_text("a")
    commit("base")
    subprocess.run(["git", "checkout", "-q", "-b", "branch"], check=True)
    (repository / "mine").write_text("mine")
    commit("mine")
    subprocess.run(["git", "checkout", "-q", "main"], check=True)
    (repository / "theirs").write_text("theirs")
    commit("theirs, since the branch was cut")
    subprocess.run(["git", "checkout", "-q", "branch"], check=True)
    assert pre_review.changed_files("main", repository) == ["mine"]


def test_a_file_moved_with_git_mv_and_committed_gives_both_paths(repository: Path) -> None:
    # A rename git pairs is only one it reports from a commit or the index; without `--no-renames` the old
    # path is lost, and with it the importers of a moved module.
    (repository / "core").mkdir()
    (repository / "core" / "hashing.py").write_text("x = 1\n" * 20)
    commit("base")
    subprocess.run(["git", "checkout", "-q", "-b", "branch"], check=True)
    subprocess.run(["git", "mv", "core/hashing.py", "core/digest.py"], check=True)
    commit("moved")
    assert pre_review.changed_files("main", repository) == ["core/digest.py", "core/hashing.py"]
    (repository / "core" / "again.py").write_text("x = 1\n" * 20)
    subprocess.run(
        ["git", "mv", "core/digest.py", "core/other.py"], check=True
    )  # and one staged, not committed
    assert pre_review.changed_files("main", repository) == [
        "core/again.py",
        "core/hashing.py",
        "core/other.py",
    ]


def test_a_path_with_a_newline_in_it_is_one_path(repository: Path) -> None:
    (repository / "kept").write_text("kept")
    commit("base")
    subprocess.run(["git", "checkout", "-q", "-b", "branch"], check=True)
    (repository / "two\nlines.py").write_text("x")
    (repository / "kept").write_text("changed")
    commit("a name with a newline")
    (repository / "tab\there.py").write_text("x")  # untracked
    assert pre_review.changed_files("main", repository) == ["kept", "tab\there.py", "two\nlines.py"]


MARKER_LINE = "<!-- kill points of every search of test_x_mutants.py::test_x (scripts/gen_kill_counts.py) -->"
OTHER_MARKER = "<!-- kill points of some searches of test_y.py::test_y (scripts/gen_kill_counts.py) -->"


def test_the_readmes_whose_kill_points_markers_changed_are_found(repository: Path) -> None:
    readme = repository / "tests" / "property" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text(f"# Mutants\n\n{MARKER_LINE}\n| a | 1 |\n")
    (repository / "notes.md").write_text("notes\n")
    commit("base")
    subprocess.run(["git", "checkout", "-q", "-b", "branch"], check=True)

    def found() -> list[str]:
        return pre_review.changed_markers(pre_review.changed_files("main", repository), "main", repository)

    readme.write_text(f"# Mutants\n\n{MARKER_LINE}\n| a | 2 |\n")
    commit("a count changed, the marker kept")
    assert found() == []
    (repository / "notes.md").write_text(f"notes\n{OTHER_MARKER}\n")  # a marker outside any README
    assert found() == []
    readme.write_text(f"# Mutants\n\n{MARKER_LINE}\n| a | 2 |\n\n{OTHER_MARKER}\n| b | 3 |\n")
    commit("a group added")
    assert found() == ["tests/property/README.md"]
    readme.write_text("# Mutants\n\n| a | 2 |\n")  # unstaged: both markers gone
    assert found() == ["tests/property/README.md"]
    subprocess.run(["git", "checkout", "-q", "-f", "-b", "other", "main"], check=True)
    (repository / "guide").mkdir()
    (repository / "guide" / "README.md").write_text(f"{OTHER_MARKER}\n")  # untracked
    (repository / "tests" / "README.md").write_text("no marker\n")  # untracked
    assert found() == ["guide/README.md"]


def test_an_unknown_base_is_refused() -> None:
    assert pre_review.main(["no-such-ref-anywhere", "--list"]) == 2


def test_the_scan_key_is_the_one_given_else_the_clones_setting_else_none(repository: Path) -> None:
    assert pre_review.key_arguments(None, repository) == ()
    assert pre_review.key_arguments("given", repository) == ("--key-file", "given")
    subprocess.run(["git", "config", "openmaterica.scanKeyFile", "~/a.key"], check=True)
    assert pre_review.key_arguments(None, repository) == ("--key-file", str(Path("~/a.key").expanduser()))
    assert pre_review.key_arguments("given", repository) == ("--key-file", "given")


# --- running -----------------------------------------------------------------------------------------------


def checks_of_every_stage() -> list[Planned]:
    return [
        Planned("fast", ("fast-1",), "why"),
        Planned("fast", ("fast-2",), "why"),
        Planned("tests", ("tests-1",), "why"),
        Planned("properties", ("properties-1",), "why"),
    ]


def test_the_stages_run_in_order_and_a_failure_stops_the_next() -> None:
    ran: list[str] = []

    def runner(planned: Planned, root: Path) -> int:
        ran.append(planned.command[0])
        return 1 if planned.command[0] == "fast-2" else 0

    status, summary = pre_review.execute(checks_of_every_stage(), pre_review.STAGES, False, runner=runner)
    assert status == 1
    assert ran == ["fast-1", "fast-2"]
    assert [line for line in summary if "not run" in line] == [
        "  not run (an earlier stage failed): tests-1",
        "  not run (an earlier stage failed): properties-1",
    ]
    assert "FAILED" in "\n".join(summary)


def test_keep_going_runs_the_stages_after_a_failure() -> None:
    ran: list[str] = []

    def runner(planned: Planned, root: Path) -> int:
        ran.append(planned.command[0])
        return 1 if planned.command[0] == "fast-1" else 0

    status, _ = pre_review.execute(checks_of_every_stage(), pre_review.STAGES, True, runner=runner)
    assert status == 1
    assert ran == ["fast-1", "fast-2", "tests-1", "properties-1"]


def test_a_run_where_every_check_passes_exits_zero_and_a_stage_not_asked_for_is_said() -> None:
    ran: list[str] = []

    def runner(planned: Planned, root: Path) -> int:
        ran.append(planned.command[0])
        return 0

    status, summary = pre_review.execute(checks_of_every_stage(), ["fast", "tests"], False, runner=runner)
    assert status == 0
    assert ran == ["fast-1", "fast-2", "tests-1"]
    assert "[properties] not asked for" in summary


def test_the_environment_of_a_check_reaches_its_process(tmp_path: Path) -> None:
    out = tmp_path / "seen"
    code = f"import os; open({str(out)!r}, 'w').write(os.environ['PRE_REVIEW_X'])"
    planned = Planned("fast", (sys.executable, "-c", code), "why", env={"PRE_REVIEW_X": "seen"})
    assert pre_review.run_check(planned, tmp_path) == 0
    assert out.read_text() == "seen"
    assert (
        pre_review.run_check(Planned("fast", (sys.executable, "-c", "raise SystemExit(3)"), "why"), tmp_path)
        == 3
    )


def test_the_command_lists_its_plan_without_running_it(capsys: pytest.CaptureFixture[str]) -> None:
    assert pre_review.main(["HEAD", "--list"]) == 0
    printed = capsys.readouterr().out
    assert "check(s) selected" in printed
    assert "[fast]" in printed
    assert "selected by" in printed


def test_the_command_plans_for_the_readmes_whose_markers_git_shows_changed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def changed_markers(changed: Sequence[str], base: str) -> list[str]:
        return ["tests/property/README.md"]

    monkeypatch.setattr(pre_review, "changed_markers", changed_markers)
    assert pre_review.main(["HEAD", "--list"]) == 0
    assert "tests/property/README.md (a kill points marker added or removed)" in capsys.readouterr().out


def test_the_script_runs_as_a_command() -> None:
    done = subprocess.run(
        [sys.executable, "scripts/pre_review.py", "HEAD", "--list"],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert "[fast]" in done.stdout


def test_every_uv_run_and_sync_the_script_plans_is_locked() -> None:
    checks, _ = plan(*everything_changed())
    runs = [check.command for check in checks if check.command[:2] == ("uv", "run")]
    assert len(runs) >= 4 + len(GENERATORS) + 1  # the static checks, the generators and the pytest commands
    assert all(command[2] == "--locked" for command in runs), [c for c in runs if c[2] != "--locked"]
    assert all("--locked" in check.command for check in checks if check.command[:2] == ("uv", "sync"))
    assert pre_review.pytest_command(["tests/unit"], 3)[:3] == ("uv", "run", "--locked")


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv, which CI's test job installs")
def test_a_lock_file_that_is_out_of_date_is_refused_and_left_as_it_was(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    # The project asks for no more than the Python that runs this test, and goes stale by its version, not by
    # its Python requirement: raising `requires-python` past the running interpreter made every uv call after
    # it fail with "incompatible with the project's Python requirement" on Python 3.11 (CI, 2026-10-18), exit
    # 2, whether or not the lock was stale. That also let the two refusals below pass for the wrong reason.
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    pyproject.write_text(
        f'[project]\nname = "p"\nversion = "0"\nrequires-python = ">={python}"\n', encoding="utf-8"
    )
    # An explicit environment: nothing uv reads from the one that runs the test (UV_LOCKED, UV_FROZEN,
    # UV_NO_SYNC, UV_PROJECT_ENVIRONMENT, a cache or index setting, an active VIRTUAL_ENV) reaches the
    # throwaway project.
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("UV_") and name not in {"VIRTUAL_ENV", "CONDA_PREFIX"}
    }
    environment |= {
        "UV_PROJECT_ENVIRONMENT": str(tmp_path / "venv"),
        "UV_PYTHON": sys.executable,
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_OFFLINE": "1",
        "UV_NO_CONFIG": "1",
    }

    def uv(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["uv", *arguments], cwd=project, env=environment, capture_output=True, text=True, check=False
        )

    def succeeds(*arguments: str) -> None:
        done = uv(*arguments)
        assert done.returncode == 0, f"uv {' '.join(arguments)} exited {done.returncode}: {done.stderr}"

    def refuses_a_stale_lock(*arguments: str) -> None:
        done = uv(*arguments)
        assert done.returncode != 0, f"uv {' '.join(arguments)} accepted a stale lock file: {done.stderr}"
        # for the lock file's staleness, not for another reason (an interpreter the project does not allow)
        assert "needs to be updated" in done.stderr, (
            f"uv {' '.join(arguments)} exited {done.returncode}: {done.stderr}"
        )

    succeeds("lock")
    lock = (project / "uv.lock").read_bytes()
    succeeds("lock", "--check")  # control: a lock file that is current passes
    succeeds("run", "--locked", "python", "-c", "pass")
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('version = "0"', 'version = "1"'), encoding="utf-8"
    )
    refuses_a_stale_lock("lock", "--check")
    refuses_a_stale_lock("run", "--locked", "python", "-c", "pass")
    assert (project / "uv.lock").read_bytes() == lock
    # control: without `--locked` uv rewrites the lock file, and `uv lock --check` passes after it, as the
    # script's first version left the builder's tree
    succeeds("run", "python", "-c", "pass")
    assert (project / "uv.lock").read_bytes() != lock
    succeeds("lock", "--check")


@pytest.mark.parametrize(
    "path",
    [
        "pyproject.toml",
        "src/materica/shapes.pyi",
        "src/materica/py.typed",
        "tests/typing/consumer_snippet.py",
        "src/materica/data/conformance/plain_read/CASES.md",
    ],
)
def test_a_change_to_what_the_wheel_ships_or_the_snippet_checks_runs_the_wheel_check(path: str) -> None:
    assert " ".join(pre_review.WHEEL_COMMAND) in commands(plan(path)[0], "fast")


def test_the_wheel_check_is_what_the_workflows_static_job_does_after_the_type_checkers() -> None:
    for text in (
        "- run: uv build",
        "scripts/check_wheel.py dist/*.whl",
        "uv venv ",
        "uv pip install --python ",
        "tests/typing/consumer_snippet.py",
        "mypy --strict --python-executable ",
        "pyright --pythonpath ",
    ):
        assert text in CI, text


class Steps:
    """A stand-in for the commands of the wheel check: records each, builds a wheel for `uv build`."""

    def __init__(self, fail_at: str | None = None, builds: bool = True) -> None:
        self.calls: list[tuple[tuple[str, ...], Path, bool]] = []
        self.fail_at = fail_at
        self.builds = builds

    def __call__(self, command: Sequence[str], directory: Path) -> int:
        self.calls.append((tuple(command), directory, (directory / "consumer_snippet.py").exists()))
        if command[:2] == ("uv", "build") and self.builds:
            Path(command[3]).mkdir(parents=True)
            (Path(command[3]) / "p-0-py3-none-any.whl").write_bytes(b"")
        return 3 if self.fail_at and self.fail_at in command else 0


def test_the_wheel_check_builds_checks_installs_and_type_checks_the_snippet_apart_from_the_project() -> None:
    steps = Steps()
    assert pre_review.wheel_check(REPOSITORY, steps) == 0
    assert [command[:2] for command, _, _ in steps.calls] == [
        ("uv", "build"),
        ("uv", "run"),
        ("uv", "venv"),
        ("uv", "pip"),
        ("uv", "run"),
        ("uv", "run"),
    ]
    _, check, _, install, mypy, pyright = steps.calls
    wheel = check[0][-1]
    assert wheel.endswith(".whl")
    assert wheel in install[0]
    assert check[0][3:5] == ("python", "scripts/check_wheel.py")
    assert check[1] == REPOSITORY
    for step in (mypy, pyright):
        assert step[1] != REPOSITORY  # run where the project's configuration does not reach
        assert step[2]  # with the snippet beside it
        assert step[0][-1] == "consumer_snippet.py"
        assert "--project" in step[0]
    assert "mypy" in mypy[0]
    assert "--strict" in mypy[0]
    assert "pyright" in pyright[0]


@pytest.mark.parametrize("failing", ["scripts/check_wheel.py", "mypy", "pyright"])
def test_a_wheel_check_step_that_fails_stops_the_rest_and_gives_its_status(failing: str) -> None:
    steps = Steps(fail_at=failing)
    assert pre_review.wheel_check(REPOSITORY, steps) == 3
    assert failing in steps.calls[-1][0]  # it is the last step run
    assert len(steps.calls) == {"scripts/check_wheel.py": 2, "mypy": 5, "pyright": 6}[failing]


def test_a_build_that_makes_no_wheel_fails_the_wheel_check() -> None:
    steps = Steps(builds=False)
    assert pre_review.wheel_check(REPOSITORY, steps) == 1
    assert len(steps.calls) == 1


def test_the_chosen_pytest_command_has_the_workers_and_the_work_stealing_distribution() -> None:
    command = pre_review.pytest_command(["tests/unit"], 7, "--shard", "json")
    assert command[command.index("-n") + 1] == "7"
    assert command[command.index("--dist") + 1] == "worksteal"
    assert command[command.index("--shard") + 1] == "json"


def test_the_checks_come_in_the_order_of_the_stages_whatever_the_order_they_were_planned_in() -> None:
    plan_of_checks = pre_review.Plan()
    for stage in ("properties", "tests", "fast"):
        plan_of_checks.add(Planned(stage, (stage,), "why"))
    assert [check.stage for check in plan_of_checks.checks()] == ["fast", "tests", "properties"]


def test_is_test_module_names_the_four_groups_of_tests_and_no_other_file() -> None:
    for group in ("unit", "spec_sync", "conformance", "property"):
        assert pre_review.is_test_module(f"tests/{group}/test_x.py")
    for path in ("tests/fuzz/test_x.py", "tests/unit/helper.py", "scripts/test_x.py", "tests/unit/test_x.md"):
        assert not pre_review.is_test_module(path)


def test_a_module_of_the_same_name_outside_the_property_directory_is_in_no_shard(tmp_path: Path) -> None:
    tree = small_tree(tmp_path)
    assert tree.shard_of("tests/property/test_p.py") == "one"
    assert tree.shard_of("tests/unit/test_p.py") is None
    assert tree.shard_of("tests/property/sub/test_p.py") is None


@pytest.mark.parametrize(
    ("status", "said"), [(1, "pre-review checks failed"), (0, "pre-review checks that ran passed")]
)
def test_the_command_ends_with_the_status_of_the_checks_it_ran(
    status: int, said: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:

    def executed(*arguments: object, **keywords: object) -> tuple[int, list[str]]:
        return status, ["  summary line"]

    monkeypatch.setattr(pre_review, "execute", executed)
    assert pre_review.main(["HEAD", "--stage", "fast"]) == status
    assert said in capsys.readouterr().out


def test_listing_the_plan_runs_none_of_it(monkeypatch: pytest.MonkeyPatch) -> None:
    def never(*arguments: object, **keywords: object) -> tuple[int, list[str]]:
        raise AssertionError("--list ran the checks")

    monkeypatch.setattr(pre_review, "execute", never)
    assert pre_review.main(["HEAD", "--list"]) == 0


# --- what no check can decide ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "figures"),
    [
        ("69,617 test cases over 101,231 cases", ["69,617 test cases", "101,231 cases"]),
        ("each of the 1266 case files, 1266 case files again", ["1266 case files"]),
        ("38 mutants and 2,000 examples in 12 tests", ["38 mutants", "2,000 examples", "12 tests"]),
        ("a section 3 item 12 of 4 steps, version 1.2", []),
        ("24 hand mutants, then 45 hand mutants", ["24 hand mutants", "45 hand mutants"]),
        ("1723 passed in 3 shards", ["1723 passed", "3 shards"]),
        ("a mean of 1.5 runs and 2,000 examples", ["1.5 runs", "2,000 examples"]),
    ],
)
def test_stated_figures(text: str, figures: list[str]) -> None:
    assert pre_review.stated_figures(text) == figures


def test_a_mutant_module_changed_beside_a_readme_that_was_not_is_no_reminder() -> None:
    # The reviews showed a README row that is wrong, never a missing co-change: CONTRIBUTING asks for the row.
    reminders = pre_review.reminders(["tests/property/test_writer_mutants.py"], [])
    assert not any("mutant" in text for text in reminders)
    assert any("CHANGELOG" in text for text in reminders)  # control: the reminders are still built


def test_reminders_name_code_changed_beside_a_changelog_that_was_not() -> None:
    assert any("CHANGELOG" in text for text in pre_review.reminders(["src/materica/core/read.py"], []))
    assert not any(
        "CHANGELOG" in text
        for text in pre_review.reminders(["src/materica/core/read.py", "CHANGELOG.md"], [])
    )
    assert not any("CHANGELOG" in text for text in pre_review.reminders(["CONTRIBUTING.md"], []))


def test_reminders_list_the_figures_stated_and_none_where_none_is() -> None:
    (reminder,) = [
        text for text in pre_review.reminders(["CHANGELOG.md"], ["1266 case files"]) if "recount" in text
    ]
    assert '"1266 case files"' in reminder
    assert not any("recount" in text for text in pre_review.reminders(["CHANGELOG.md"], []))


def test_the_figures_added_are_those_of_the_changelog_lines_and_commit_messages_of_the_branch(
    repository: Path,
) -> None:
    (repository / "CHANGELOG.md").write_text("- an old line of 5 tests\n")
    commit("base with 7 mutants")
    subprocess.run(["git", "checkout", "-q", "-b", "branch"], check=True)
    (repository / "CHANGELOG.md").write_text("- an old line of 5 tests\n- a new line of 1,266 case files\n")
    commit("the branch, 9 examples")
    assert pre_review.added_figures("main", repository) == ["1,266 case files", "9 examples"]


# --- the declared tables, held against what the tests open --------------------------------------------------

TRACE_OUT = "OPEN_TRACE_OUT"
# The trace runs the whole suite once, about a minute of wall time and three of CPU, so it runs where this is
# `1`: in ci.yml's `tests` job on Python 3.15 alone (test_ci_workflows.py holds that), and where asked.
TRACE_SELECTION = "MATERICA_TRACE_SELECTION"


@pytest.fixture(scope="module")
def trace(tmp_path_factory: pytest.TempPathFactory) -> list[tuple[str, str, str]]:
    """Every file the tests open and every directory they list, by test file: the suite is run under
    `tests/unit/open_trace.py`, which keeps the first test of each test function and imports, without running,
    the property modules. It sees what the test process opens, not what a subprocess of it does.

    The run gets an empty bytecode cache of its own (`PYTHONPYCACHEPREFIX`). With a warm cache the import
    system reads a module's `.pyc`, under `__pycache__` and ignored, and never opens its source, so a
    package's `__init__.py` was named or not by whatever an earlier run had left. Every import now reads its
    source, and the trace is the same on a laptop, on CI and in a clean checkout."""
    if TRACE_OUT in os.environ:
        pytest.skip("this is the traced run itself")
    if os.environ.get(TRACE_SELECTION) != "1":
        pytest.skip(
            f"the trace test is skipped unless {TRACE_SELECTION}=1: CI's `tests` job on Python 3.15 sets it, "
            f"and a builder runs it with `{TRACE_SELECTION}=1 uv run --locked pytest "
            "tests/unit/test_pre_review.py -k trace`"
        )
    out = tmp_path_factory.mktemp("trace") / "opens.jsonl"
    cold_cache = tmp_path_factory.mktemp("cold_bytecode_cache")
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            open_trace.__name__,
            *("tests/unit", "tests/spec_sync", "tests/conformance", "tests/property", "tests/examples"),
            *("-n", "4", "--dist", "worksteal", "-q", "--tb=no", "-p", "no:cacheprovider"),
        ],
        cwd=REPOSITORY,
        env={
            **os.environ,
            "OPEN_TRACE_ROOT": str(REPOSITORY),
            TRACE_OUT: str(out),
            "PYTHONPYCACHEPREFIX": str(cold_cache),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.exists(), run.stdout[-800:] + run.stderr[-800:]
    found = [
        (kind, test, path) for kind, test, path in (json.loads(line) for line in out.read_text().splitlines())
    ]
    # control: the trace sees what it is for, or an empty one would pass every test below
    assert ("opened", "tests/unit/test_read.py", f"{PLAIN_READ}/water_fixture.json") in found
    assert ("listed", "tests/unit/test_source_files.py", "tests/property") in found
    # control: the run read each package's source, as a cold cache makes the import system do. With the
    # repository's own warm `__pycache__` it would have read the `.pyc`, which the trace ignores. It names the
    # test that imported the package first on its worker, whichever of the fuzz oracles' tests that is
    assert any(("opened", test, "tests/fuzz/__init__.py") in found for test in FUZZ_ORACLE_TESTS)
    # control: the run held every group of tests, since a group left out of the run opens nothing and so
    # would pass every test below without being seen
    for group in pre_review.TEST_GROUPS:
        assert any(test.startswith(f"tests/{group}/") for _, test, _ in found), group
    return found


def tracked() -> set[str]:
    done = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, check=True, cwd=REPOSITORY
    )
    return {path for path in done.stdout.split("\0") if path}


def is_a_test_module(path: str) -> bool:
    return path.startswith("tests/") and Path(path).name.startswith("test_") and path.endswith(".py")


# A file that a test opens and that does not select it when it changes, each with its reason. None today.
OPENED_AND_NOT_SELECTING: dict[tuple[str, str], str] = {}


def lists_python(trace: list[tuple[str, str, str]]) -> set[tuple[str, str]]:
    """The (directory, test file) pairs where a test lists a directory that holds a tracked Python file."""
    with_python = {str(Path(path).parent) for path in tracked() if path.endswith(".py")}
    return {
        (directory, test)
        for kind, test, directory in trace
        if kind == "listed" and directory in with_python and is_a_test_module(test)
    }


# The tests of the fuzz targets' oracles, the only tests that import the fuzz package.
FUZZ_ORACLE_TESTS = ("tests/unit/test_fuzz_oracle.py", "tests/unit/test_acceptance_oracle.py")


def test_the_declared_readers_hold_against_a_trace_of_the_files_the_tests_open(
    trace: list[tuple[str, str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One test, since each worker that ran one of several would make the trace again."""
    files = tracked()
    with monkeypatch.context() as unmapped:
        unmapped.setattr(pre_review, "WHOLE_UNIT_DIRECTORY", "tests/nowhere")  # the tables must hold alone
        opened = sorted(
            {
                (path, test)
                for kind, test, path in trace
                if kind == "opened" and path in files and path != test and is_a_test_module(test)
            }
        )
        planned: dict[str, list[Planned]] = {}
        missed = [
            (path, test)
            for path, test in opened
            if (path, test) not in OPENED_AND_NOT_SELECTING
            and not selects(planned.setdefault(path, plan(path)[0]), test)
        ]
        assert not missed, (
            f"{len(missed)} files whose change does not select a test that opens them: {missed[:12]}"
        )
        assert set(OPENED_AND_NOT_SELECTING) <= set(opened), "an exemption for a file that no test opens"

        listed = sorted(lists_python(trace))
        assert listed, "no test lists a directory of Python files"
        absent = [(d, test) for d, test in listed if not selects(plan(f"{d}/zz_new.py")[0], test)]
        assert not absent, f"a new Python file does not select a test that lists its directory: {absent}"

        # control: the trace names the fuzz package's file for an oracle's test, and no declared reader lists
        # either test, so the import graph alone selects it (the cold run once named this pair)
        assert any(("tests/fuzz/__init__.py", test) in opened for test in FUZZ_ORACLE_TESTS)
        assert all(
            test not in reader.tests for reader in pre_review.TREE_READERS for test in FUZZ_ORACLE_TESTS
        )

        # control: with the table of whole-tree readers emptied, the same check names the readers it held
        unmapped.setattr(pre_review, "TREE_READERS", ())
        absent_without = {test for d, test in listed if not selects(plan(f"{d}/zz_new.py")[0], test)}
        assert {
            "tests/unit/test_source_files.py",
            "tests/unit/test_ci_workflows.py",
            "tests/spec_sync/test_reason_steps.py",
            "tests/spec_sync/test_build_reasons.py",
            "tests/unit/test_pre_review.py",
        } <= absent_without
        # test_read lists the core when it is first imported, which test_conditions may do first and be named
        assert absent_without & {"tests/unit/test_read.py", "tests/unit/test_conditions.py"}


# --- the whole tree's stage ------------------------------------------------------------------------------


def whole_problems(checks: Sequence[Planned]) -> list[str]:
    """Where the whole-tree stage leaves out a test that `LEFT_TO_CI` does not name with a reason, or runs a
    selection other than the tree's own: `tests`, one `--ignore` for each path left to CI, and nothing else
    that narrows it."""
    whole = [check for check in checks if check.stage == "whole"]
    problems = [] if whole else ["no whole-tree check"]
    narrowing = ("--ignore", "--deselect", "-k", "-m", "--shard", "--property-controls", "--ignore-glob")
    for check in whole:
        words = list(check.command)
        start = words.index("pytest") + 1
        if words[start] != "tests":
            problems.append(f"the whole stage runs {words[start]!r}, not the tree's tests")
        ignored = [word.partition("=")[2] for word in words if word.startswith("--ignore=")]
        problems += [
            f"{path} left out with no reason" for path in ignored if not pre_review.LEFT_TO_CI.get(path)
        ]
        problems += [
            f"{path} listed but not left out" for path in pre_review.LEFT_TO_CI if path not in ignored
        ]
        problems += [
            f"the whole stage narrows by {word}"
            for word in words
            if word.split("=")[0] in narrowing and not word.startswith("--ignore=")
        ]
    return problems


def test_the_whole_tree_stage_runs_every_test_but_those_left_to_ci_each_with_its_reason() -> None:
    checks, _ = plan("CHANGELOG.md")
    assert whole_problems(checks) == []
    (whole,) = [check for check in checks if check.stage == "whole"]
    assert "tests/reference" in whole.why
    assert "tests/property:" not in whole.why.partition("): ")[2]
    left = [check for check in checks if check.stage != "whole"]
    assert whole_problems(left) == ["no whole-tree check"]


@pytest.mark.parametrize(
    ("extra", "problem"),
    [
        ("--ignore=tests/reference", "tests/reference left out with no reason"),
        ("--deselect=tests/unit/test_read.py", "narrows by --deselect"),
        ("-k", "narrows by -k"),
    ],
)
def test_the_whole_tree_check_fails_where_a_test_is_left_out_unlisted(extra: str, problem: str) -> None:
    checks, _ = plan("CHANGELOG.md")
    changed = [
        Planned(check.stage, (*check.command, extra), check.why) if check.stage == "whole" else check
        for check in checks
    ]
    assert problem in "; ".join(whole_problems(changed))


def test_a_new_directory_of_tests_joins_the_whole_tree_stage_with_no_edit(tmp_path: Path) -> None:
    for directory in ("unit", "property", "newly_added"):
        (tmp_path / "tests" / directory).mkdir(parents=True)
    (whole,) = pre_review.whole_tree(tmp_path, 8)
    assert whole.why.endswith("): tests/newly_added, tests/unit")
    assert whole_problems([whole]) == []


def test_the_whole_tree_stage_runs_in_parts_one_after_another_when_asked() -> None:
    parts = pre_review.whole_tree(REPOSITORY, 8, parts=3)
    assert [check.command[check.command.index("--partition") + 1] for check in parts] == ["1/3", "2/3", "3/3"]
    assert whole_problems(parts) == []


def test_the_whole_tree_stage_runs_only_when_asked_for() -> None:
    assert pre_review.DEFAULT_STAGES == ("fast", "tests", "properties")
    ran: list[str] = []

    def runner(planned: Planned, root: Path) -> int:
        ran.append(planned.stage)
        return 0

    checks = [*checks_of_every_stage(), Planned("whole", ("whole-1",), "why")]
    _, summary = pre_review.execute(checks, pre_review.DEFAULT_STAGES, False, runner=runner)
    assert "whole" not in ran
    assert "[whole] not asked for" in summary
    pre_review.execute(checks, ["whole"], False, runner=runner)
    assert ran[-1] == "whole"
