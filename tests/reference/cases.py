# SPDX-License-Identifier: Apache-2.0
"""Every conformance case file of a read, run through the reference model under every configuration of claims
the case allows, and compared with its expected answer as `docs/specification/README.md` ("Case files") says;
and every build-check case file, run through the build's own model (`build_model.py`) alike.

Case files and their inputs are read with the model's own strict JSON, so that nothing the model is given
passes through `materica`; the comparison is the conformance runner's, whose own tests show it fails on wrong
answers (`tests/conformance/test_comparator.py`)."""

import itertools
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Final, Literal

from tests.conformance.runner import CONFORMANCE, CaseFile, CaseFileError, compare
from tests.reference import build_model, read_model
from tests.reference.exceptions import BUILD_EXCEPTIONS, EXCEPTIONS, Excepted
from tests.reference.strict_json import JsonObject, JsonValue, NotStrictJson, parse

# The suites whose claim changes what a read gives (`read_side_contract.md` section 3: the hash at step 4, a
# parameter set at step 8, and the `want`s of step 0); every configuration claims plain read beside them.
SUITES: Final = ("hash", "fits_and_reference_data", "family_evaluation")
CONFIGURATIONS: Final = tuple(
    frozenset({"plain_read", *chosen})
    for size in range(len(SUITES) + 1)
    for chosen in itertools.combinations(SUITES, size)
)


@dataclass(frozen=True)
class Outcome:
    kind: Literal["agrees", "differs", "no verdict"]
    detail: str = ""


# The table evaluation suite is not a read. Each of its files asks an evaluator for a table's values at points
# (README.md:199 "A **table evaluation case** (`read_side_contract.md` section 7) names"), as a consumer's own
# evaluator does, outside the read; the model, a model of the read, has no
# answer to it, and those files are the table evaluator's to agree with. Nor are the record-check suite's
# files, record checks and `quote_sha256` operations, which are the record checks' to agree with, nor the
# build-check suite's, `check_build` operations, which the build's own model agrees with from S7a-1.
NOT_A_READ: Final = ("table_evaluation", "record_checks", "build_checks")

# The suites whose claim changes what a build gives, beside the build checks and plain read that every build
# configuration claims (README.md:269-270 "A case whose answer depends on a suite the build claims (the scene
# suite, say) says so in `claims`"): the scene suite, USD read and the sampling suite at the declaration
# (`declarations.md` section 1 item 12), the hash and the fits and reference data suite at the reads past it.
BUILD_SUITES: Final = ("hash", "fits_and_reference_data", "scene_documents", "usd_read", "sampling")
BUILD_CONFIGURATIONS: Final = tuple(
    frozenset({"plain_read", "build_checks", *chosen})
    for size in range(len(BUILD_SUITES) + 1)
    for chosen in itertools.combinations(BUILD_SUITES, size)
)


@cache
def case_files() -> tuple[CaseFile, ...]:
    return tuple(
        CaseFile.from_document(path, parse(path.read_bytes()))
        for path in sorted(CONFORMANCE.glob("*/cases/*.json"))
    )


@cache
def read_case_files() -> tuple[CaseFile, ...]:
    return tuple(case_file for case_file in case_files() if case_file.suite not in NOT_A_READ)


@cache
def build_case_files() -> tuple[CaseFile, ...]:
    return tuple(case_file for case_file in case_files() if case_file.suite == "build_checks")


@cache
def input_bytes(path: Path) -> bytes:
    return path.read_bytes()


def answer(case_file: CaseFile, claims: frozenset[str]) -> JsonObject | read_model.NoVerdict:
    """The model's answer to the case's operation: a read, `list_records` or `content_hash`."""
    if case_file.operation == "content_hash":
        return read_model.hash_operation(case_file.input_bytes("value"))
    sources = [input_bytes(path) for path in case_file.input_paths("records")]
    if case_file.operation == "list_records":
        return read_model.list_records(sources)
    request: JsonValue | NotStrictJson = case_file.request
    if "request" in case_file.inputs:
        try:
            request = parse(case_file.input_bytes("request"))
        except NotStrictJson as fault:
            request = fault
    return read_model.read(request, sources, claims)


def agreeing(
    case_file: CaseFile, configurations: tuple[frozenset[str], ...] = CONFIGURATIONS
) -> list[frozenset[str]]:
    """The configurations that claim the case's suite and agree with every claim it states (README.md,
    "Claims")."""
    return [
        claimed
        for claimed in configurations
        if case_file.suite in claimed
        and all((suite in claimed) == claim for suite, claim in case_file.claims.items())
    ]


def outcome(case_file: CaseFile) -> Outcome:
    """Whether the model agrees with the case file under every configuration of claims it allows.

    A raise of the model goes through, named with the case file and the claims: the model answers every case
    file, faulted or not, so a seeded fault that makes it raise has broken the model, which shows nothing of
    whether the case's expected answer tells that fault apart, and is never counted as a disagreement."""
    configurations = agreeing(case_file)
    if not configurations:
        return Outcome("differs", "no configuration of claims agrees with the case")
    for claims in configurations:
        try:
            given = answer(case_file, claims)
        except Exception as error:
            error.add_note(f"the model raised reading {case_file.path.name}, claiming {sorted(claims)}")
            raise
        if isinstance(given, read_model.NoVerdict):
            return Outcome("no verdict", given.why)
        differences = compare(case_file, given)
        if differences:
            return Outcome("differs", f"claiming {sorted(claims)}: {'; '.join(differences)}")
    return Outcome("agrees")


def judged(name: str, found: Outcome, exceptions: Mapping[str, Excepted]) -> str | None:
    """What is wrong with the model's outcome on a case file, given the list of exceptions, or None."""
    kinds = [kind for kind, excepted in exceptions.items() if name in excepted.case_files]
    if len(kinds) > 1:
        return f"{name} is listed under {len(kinds)} kinds: {kinds}"
    if found.kind == "agrees":
        return (
            f"{name} agrees with the model, but is listed under {kinds[0]!r}: a stale entry"
            if kinds
            else None
        )
    if not kinds:
        return f"{name}: the model {found.kind}, and no kind lists it: {found.detail}"
    excepted = exceptions[kinds[0]]
    if excepted.outcome != found.kind:
        return f"{name} is listed under {kinds[0]!r} as {excepted.outcome}, but {found.kind}"
    if excepted.detail is not None and excepted.detail != found.detail:
        return f"{name} is listed under {kinds[0]!r} for {excepted.detail!r}, but {found.detail!r}"
    return None


def build_answer(case_file: CaseFile, claims: frozenset[str]) -> build_model.Refused | read_model.NoVerdict:
    """The build model's answer to a build-check case: its declaration's own check (the records are read only
    past it)."""
    return build_model.check_build(case_file.input_bytes("declaration"), claims)


def refusal_key(refusal: JsonValue) -> tuple[str, str]:
    item = refusal.get("item") if isinstance(refusal, dict) else None
    pointer = refusal.get("pointer") if isinstance(refusal, dict) else None
    if not (isinstance(item, str) and isinstance(pointer, str)):
        raise CaseFileError(f"a refusal that is not an item and a pointer: {refusal!r}")
    return item, pointer


def build_differences(case_file: CaseFile, report: build_model.Refused) -> list[str] | read_model.NoVerdict:
    """How a refused declaration's report differs from the case's expected answer, or `NoVerdict` where the
    case compares the refusals of a rule the model does not place.

    README.md:259-261 "`refusals`, each `{"item": "<the rule's case id>", "pointer"}`, compared as a set" and
    "where `compare.rules_compared` lists case ids, only the refusals of those rules are compared"; and
    README.md:152-153 "A member `compare` names and `expected` omits must be absent from the result"."""
    rules = set(case_file.rules)
    unplaced = sorted(rule for rule in report.unplaced if not rules or rule in rules)
    if unplaced:
        return read_model.NoVerdict(
            "; ".join(
                f"the refusals of {rule}, which the model does not place: {report.unplaced[rule]}"
                for rule in unplaced
            )
        )
    given = report.to_json()
    differences: list[str] = []
    for member in case_file.members:
        if member != "refusals":
            if member in case_file.expected and member not in given:
                differences.append(f"{member}: missing")
            continue
        expected = case_file.expected.get(member)
        if not isinstance(expected, list):
            differences.append("refusals: must be absent")
            continue
        wanted = {key for key in map(refusal_key, expected) if not rules or key[0] in rules}
        found = {(one.item, one.pointer) for one in report.refusals if not rules or one.item in rules}
        if found != wanted:
            differences.append(
                f"refusals: missing {sorted(wanted - found)}, unexpected {sorted(found - wanted)}"
            )
    return differences


def build_outcome(case_file: CaseFile) -> Outcome:
    """Whether the build model agrees with a build-check case file under every configuration of claims it
    allows: a disagreement under any of them is one, and a no verdict under any, with none, is one. A raise
    goes through, named, as for a read (`outcome`)."""
    configurations = agreeing(case_file, BUILD_CONFIGURATIONS)
    if not configurations:
        return Outcome("differs", "no configuration of claims agrees with the case")
    undecided: list[str] = []
    for claims in configurations:
        try:
            given = build_answer(case_file, claims)
        except Exception as error:
            error.add_note(f"the build model raised reading {case_file.path.name}, claiming {sorted(claims)}")
            raise
        found = given if isinstance(given, read_model.NoVerdict) else build_differences(case_file, given)
        if isinstance(found, read_model.NoVerdict):
            undecided.append(found.why)
        elif found:
            return Outcome("differs", f"claiming {sorted(claims)}: {'; '.join(found)}")
    return Outcome("no verdict", undecided[0]) if undecided else Outcome("agrees")


def first_disagreement(
    judge: Callable[[CaseFile], Outcome] = outcome,
    exceptions: Mapping[str, Excepted] = EXCEPTIONS,
    files: Callable[[], tuple[CaseFile, ...]] = read_case_files,
) -> str | None:
    """The first case file of a read (or of `files`), in name order, whose outcome the list of exceptions does
    not give, or None."""
    for case_file in files():
        problem = judged(case_file.path.name, judge(case_file), exceptions)
        if problem is not None:
            return problem
    return None


def first_build_disagreement(judge: Callable[[CaseFile], Outcome] = build_outcome) -> str | None:
    """The first build-check case file, in name order, whose outcome `BUILD_EXCEPTIONS` does not give, or
    None."""
    return first_disagreement(judge, BUILD_EXCEPTIONS, build_case_files)
