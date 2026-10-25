# SPDX-License-Identifier: Apache-2.0
"""The build's own reasons, where they are constructed and that a file of a piece done returns each (the S7
design's 6.5).

Each code `read_side_contract.md` section 4 gives at the procedure `build` (generated into
`vocabulary/reasons.json`) is either built, constructed in `core/build.py` by `_build_reasons` and in no other
function of the core, and returned in a result of some build-check file of a piece done; or listed in
`NOT_BUILT_BUILD` with the piece that builds it, constructed nowhere in the core and returned by no such file.
A code built and still listed, or listed and built, fails. The control removes one code's construction from
the source, and the check fails.
"""

from collections import Counter

from materica.core import build
from materica.core.jsonio import JsonValue
from tests.conformance import runner
from tests.conformance.runner import CONFIGURATIONS, EXECUTORS, agreeing
from tests.spec_sync.reason_sites import CORE, constructed, reason_table

# The codes the procedure `build` gives that this version does not build, and the piece that does.
NOT_BUILT_BUILD = {
    "overlay_scope_mismatch": "S7c",
    "engine_crosswalk_invalid": "S11",
    "engine_material_missing": "S11",
    "engine_material_foreign": "S11",
    "engine_material_stale": "S11",
    "engine_density_overridden": "S11",
    "engine_mass_not_comparable": "S11",
}
# Where the build constructs its own reasons.
SITE = ("build.py", "_build_reasons")
BUILD_CODES = {code for code, (_, procedures) in reason_table().items() if "build" in procedures}


def construction_problems(sources: dict[str, str]) -> list[str]:
    """Each code the procedure `build` gives that `sources`, the core's modules by name, construct elsewhere
    than at `SITE`, or that is built and not constructed there, or listed and constructed anywhere."""
    sites = Counter(
        (module, function, code)
        for module, source in sources.items()
        for function, code in constructed(source)
    )
    problems: list[str] = []
    for code in sorted(BUILD_CODES):
        at = {(module, function) for module, function, found in sites if found == code}
        if code in NOT_BUILT_BUILD:
            problems += [
                f"{code}, listed as {NOT_BUILT_BUILD[code]}'s, constructed in {module}: {function}"
                for module, function in sorted(at)
            ]
        elif at != {SITE}:
            problems.append(f"{code} constructed at {sorted(at)}, not at {SITE} alone")
    return problems


def core_sources() -> dict[str, str]:
    """Every module of the core, a new one included, listed when a test runs."""
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(CORE.glob("*.py"))}


def test_each_build_code_is_built_or_listed_with_its_piece() -> None:
    """The procedure's codes, as the table gives them: every one but those listed is built here."""
    assert set(NOT_BUILT_BUILD) <= BUILD_CODES
    assert BUILD_CODES - set(NOT_BUILT_BUILD) == {"no_requirement", "label_mismatch", "not_reviewed"}


def test_each_code_built_is_constructed_in_build_reasons_and_no_listed_one_anywhere() -> None:
    assert construction_problems(core_sources()) == []


def test_a_codes_construction_removed_fails() -> None:
    """The control: `label_mismatch` constructed as another code, so `_build_reasons` no longer builds it."""
    sources = core_sources()
    written = '"label_mismatch",'
    assert sources["build.py"].count(written) == 1
    sources["build.py"] = sources["build.py"].replace(written, '"not_reviewed",')
    assert construction_problems(sources) == [
        f"label_mismatch constructed at [], not at {SITE} alone",
    ]


def codes(result: JsonValue) -> set[str]:
    assert isinstance(result, dict)
    reasons = result["reasons"]
    assert isinstance(reasons, list)
    return {str(reason["code"]) for reason in reasons if isinstance(reason, dict)}


def test_each_code_built_is_returned_by_a_build_check_file_of_a_piece_done() -> None:
    returned: set[str] = set()
    for case_file in runner.discover():
        if case_file.operation != "check_build" or not runner.step_done(case_file):
            continue
        for claims in agreeing(case_file, CONFIGURATIONS):
            results = EXECUTORS["check_build"](case_file, claims)["results"]
            assert isinstance(results, list)
            returned |= {code for result in results for code in codes(result)}
    built = BUILD_CODES - set(NOT_BUILT_BUILD)
    assert built <= returned
    assert not returned & set(NOT_BUILT_BUILD)
    assert build._build_reasons.__name__ == SITE[1]  # pyright: ignore[reportPrivateUsage]
