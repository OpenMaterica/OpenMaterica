# SPDX-License-Identifier: Apache-2.0
"""The conformance-case runner, by `docs/specification/README.md`, "Case files" to "Operations".

It finds every case file, runs those whose operation has an executor under every configuration of claims that
agrees with the case's suite and claims, compares each result with the case's expected answer, and folds a
case's variants into the case's outcome. Later steps add executors; the rest stays as it is.

The table evaluation cases are the exception: `materica` claims no table evaluation, so their executor runs
the test-only reference evaluator (`tests/reference/table_evaluator.py`), and a case it passes is verified
against that evaluator, never passed.
"""

import json
import math
import re
import struct
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from functools import cache
from pathlib import Path
from typing import Literal, TypedDict

import materica
from materica.core import hashing, jsonio
from materica.core.build import check_build
from materica.core.jsonio import JsonValue
from materica.core.read import read
from materica.core.reasons import Reason
from materica.io.plain import load_records
from materica.shapes import Suite
from tests.reference import table_evaluator
from tests.reference.table_evaluator import Evaluation, Scheme, Side, Table

CONFORMANCE = Path(materica.__file__).parent / "data" / "conformance"
# Each case file's implementation step, and the steps done (`tests/spec_sync/test_case_steps.py`).
CASE_STEPS = Path(__file__).resolve().parent.parent / "spec_sync" / "case_steps.json"

JsonObject = dict[str, JsonValue]


class CaseFileError(Exception):
    """A case file that breaks the rules for case files: a defect in the case, never a pass."""


class Outcome(Enum):
    PASSED = "passed"
    VERIFIED = "verified against the reference evaluator"
    FAILED = "failed"
    NOT_RUN = "not run: its suite or claims disagree with every configuration of claims"
    NOT_YET_RUNNABLE = "not yet runnable: no executor for its operation, or its step not done"


@dataclass(frozen=True, eq=False)
class CaseFile:
    path: Path
    case: str
    variant: str
    suite: str
    operation: str
    claims: dict[str, bool]
    inputs: JsonObject
    request: JsonValue
    expected: JsonObject
    members: tuple[str, ...]
    relative_tolerance: float | None
    exact: bool
    # A table evaluation case's tolerance per precision, `binary64` and `binary32` (README, "Case files"), in
    # place of `relative_tolerance`; its executor compares by the precision an evaluator claims.
    precision_tolerances: dict[str, float] | None = None
    # A record-check case's rules, by case id, whose findings and listing it compares (README, "Case files").
    rules: tuple[str, ...] = ()
    # A build-check case's members of each result compared (README, "Case files": `compare.result_members`).
    result_members: tuple[str, ...] = ()

    @classmethod
    def from_document(cls, path: Path, document: JsonValue) -> "CaseFile":
        document = _object(document, "the case file")
        case = _string(document.get("case"), "case")
        variant = _string(document.get("variant"), "variant")
        if not re.fullmatch(r"[a-z0-9_]+", variant) or path.name != f"{case}.{variant}.json":
            raise CaseFileError(f"{path.name}: the file is not named <case>.<variant>.json")
        # A request may itself be broken on purpose (PR-330 gives an array and a string): that is a read too.
        # A record-check case without a request runs the record checks (README, "Case files").
        request = document.get("request")
        operation = request.get("operation", "read") if isinstance(request, dict) else "read"
        if request is None and document.get("suite") == "record_checks":
            operation = "check"
        compare = _object(document.get("compare"), "compare")
        members = tuple(
            _string(member, "compare.members") for member in _list(compare.get("members"), "members")
        )
        expected = _object(document.get("expected"), "expected")
        if not set(expected) <= set(members):
            raise CaseFileError(f"{path.name}: expected holds members compare does not name")
        tolerance, precision_tolerances = _tolerances(compare.get("relative_tolerance"))
        exact = compare.get("exact", False)
        if not isinstance(exact, bool):
            raise CaseFileError(f"{path.name}: compare's exact is not true or false")
        if (tolerance is not None or precision_tolerances is not None) and exact:
            raise CaseFileError(f"{path.name}: compare gives both relative_tolerance and exact")
        rules = tuple(
            _string(rule, "compare.rules_compared")
            for rule in _list(compare.get("rules_compared", []), "rules_compared")
        )
        result_members = tuple(
            _string(member, "compare.result_members")
            for member in _list(compare.get("result_members", []), "result_members")
        )
        claims = _object(document.get("claims", {}), "claims")
        if not all(isinstance(claimed, bool) for claimed in claims.values()):
            raise CaseFileError(f"{path.name}: a claim is not true or false")
        return cls(
            path=path,
            case=case,
            variant=variant,
            suite=_string(document.get("suite"), "suite"),
            operation=_string(operation, "request.operation"),
            claims={suite: claimed is True for suite, claimed in claims.items()},
            inputs=_object(document.get("inputs"), "inputs"),
            request=request,
            expected=expected,
            members=members,
            relative_tolerance=tolerance,
            exact=exact,
            precision_tolerances=precision_tolerances,
            rules=rules,
            result_members=result_members,
        )

    def input_bytes(self, member: str) -> bytes:
        return (self.path.parent.parent / "inputs" / _string(self.inputs.get(member), member)).read_bytes()

    def input_paths(self, member: str) -> list[Path]:
        names = _list(self.inputs.get(member), member)
        return [self.path.parent.parent / "inputs" / _string(name, member) for name in names]


# An executor runs one case file's operation as a reader claiming the given suites.
Executor = Callable[[CaseFile, frozenset[Suite]], JsonObject]


@dataclass(frozen=True)
class CaseRun:
    case_file: CaseFile
    outcome: Outcome
    differences: tuple[str, ...] = ()
    claimed: tuple[frozenset[Suite], ...] = ()  # the configurations it ran under


def discover(root: Path = CONFORMANCE) -> list[CaseFile]:
    case_files: list[CaseFile] = []
    for path in sorted(root.glob("*/cases/*.json")):
        document = jsonio.parse(path.read_bytes())
        if isinstance(document, Reason):
            raise CaseFileError(f"{path.name}: {document.detail}")
        case_file = CaseFile.from_document(path, document)
        if path.parent.parent.name != case_file.suite:
            raise CaseFileError(f"{path.name}: suite {case_file.suite!r} is not its directory's")
        case_files.append(case_file)
    return case_files


def agreeing(case_file: CaseFile, configurations: Iterable[frozenset[Suite]]) -> list[frozenset[Suite]]:
    """The configurations that claim the case's suite and agree with every claim the case states."""
    return [
        claimed
        for claimed in configurations
        if case_file.suite in claimed
        and all((suite in claimed) == claims for suite, claims in case_file.claims.items())
    ]


def steps(case_file: CaseFile, case_steps: Path = CASE_STEPS) -> tuple[str, ...]:
    """The implementation steps whose code the case file needs: one, or several whose order is not fixed.

    A case file the map does not name needs none here, so a missing entry never hides a case; the map's own
    test finds it.
    """
    entry = _case_steps(case_steps)["case_files"].get(case_file.path.name, ())
    return (entry,) if isinstance(entry, str) else tuple(entry)


def step_done(case_file: CaseFile, case_steps: Path = CASE_STEPS) -> bool:
    done = _case_steps(case_steps)["done"]
    return all(step in done for step in steps(case_file, case_steps))


class _CaseSteps(TypedDict):
    done: list[str]
    case_files: dict[str, str | list[str]]


@cache
def _case_steps(path: Path) -> _CaseSteps:
    loaded: _CaseSteps = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def not_run_because(
    case_file: CaseFile, *, configurations: Iterable[frozenset[Suite]], executors: Mapping[str, Executor]
) -> Outcome | None:
    if case_file.operation not in executors or not step_done(case_file):
        return Outcome.NOT_YET_RUNNABLE
    if not agreeing(case_file, configurations):
        return Outcome.NOT_RUN
    return None


def run(
    case_file: CaseFile, *, configurations: Iterable[frozenset[Suite]], executors: Mapping[str, Executor]
) -> CaseRun:
    """The case file run under every configuration that agrees with it; it fails if any run fails."""
    configurations = tuple(configurations)
    not_run = not_run_because(case_file, configurations=configurations, executors=executors)
    if not_run is not None:
        return CaseRun(case_file, not_run)
    claimed = tuple(agreeing(case_file, configurations))
    differences = [
        f"claiming {', '.join(sorted(claims))}: {difference}"
        for claims in claimed
        for difference in _run_once(case_file, claims, executors[case_file.operation])
    ]
    outcome = Outcome.FAILED if differences else passing_outcome(case_file)
    return CaseRun(case_file, outcome, tuple(differences), claimed)


def passing_outcome(case_file: CaseFile) -> Outcome:
    """What a case file that ran and failed nowhere counts as: verified, where its executor runs the reference
    evaluator, which only a table evaluation case's does; passed otherwise."""
    return Outcome.VERIFIED if case_file.operation == "evaluate" else Outcome.PASSED


def _run_once(case_file: CaseFile, claims: frozenset[Suite], executor: Executor) -> list[str]:
    try:
        result = executor(case_file, claims)
    except CaseFileError:
        raise
    except Exception as error:
        # An implementation that raises for a case's content fails it: no read raises (PR-300).
        return [f"raised {type(error).__name__}: {error}"]
    return compare(case_file, result)


def run_all(
    case_files: Iterable[CaseFile],
    *,
    configurations: Iterable[frozenset[Suite]],
    executors: Mapping[str, Executor],
) -> list[CaseRun]:
    configurations = tuple(configurations)
    return [run(case_file, configurations=configurations, executors=executors) for case_file in case_files]


def case_outcome(variants: Iterable[Outcome]) -> Outcome:
    """A case passes, or is verified, when at least one variant ran and none failed; with none run, it is not
    run."""
    outcomes = set(variants)
    if Outcome.FAILED in outcomes:
        return Outcome.FAILED
    if Outcome.PASSED in outcomes:
        return Outcome.PASSED
    if Outcome.VERIFIED in outcomes:
        return Outcome.VERIFIED
    if outcomes == {Outcome.NOT_YET_RUNNABLE}:
        return Outcome.NOT_YET_RUNNABLE
    return Outcome.NOT_RUN


def case_outcomes(runs: Iterable[CaseRun]) -> dict[str, Outcome]:
    variants: dict[str, list[Outcome]] = {}
    for case_run in runs:
        variants.setdefault(case_run.case_file.case, []).append(case_run.outcome)
    return {case: case_outcome(outcomes) for case, outcomes in variants.items()}


def compare(case_file: CaseFile, result: Mapping[str, JsonValue]) -> list[str]:
    """How `result` differs from the case's expected answer; no difference is a pass.

    Raises `CaseFileError` for a case that compares a number with neither `relative_tolerance` nor `exact`.
    """
    if case_file.operation == "evaluate":
        return _evaluation_runs_differ(case_file, result)
    if case_file.operation == "check_build":
        return _build_differs(case_file, result)
    differences: list[str] = []
    for member in case_file.members:
        if member == "labels":
            difference = _labels_differ(case_file, case_file.expected.get("labels"), result.get("labels"))
        elif member not in case_file.expected:
            difference = f"must be absent, got {result[member]!r}" if member in result else None
        elif member not in result:
            difference = "missing"
        elif member == "reasons":
            difference = _reasons_differ(case_file, case_file.expected[member], result[member])
        elif member == "value" and case_file.operation == "list_records":
            difference = _sets_differ(case_file.expected[member], result[member])
        elif member == "conditions":
            difference = _conditions_differ(case_file, case_file.expected[member], result[member])
        elif member == "alternative_values":
            difference = _alternative_values_differ(case_file, case_file.expected[member], result[member])
        else:
            difference = _values_differ(case_file, case_file.expected[member], result[member])
        if difference is not None:
            differences.append(f"{member}: {difference}")
    return differences


def _build_differs(case_file: CaseFile, report: Mapping[str, JsonValue]) -> list[str]:
    """How a build's report differs from a build-check case's expected answer (README, "Case files"):
    `refusals` as a set of their `item` and `pointer`, `detail` never, and only those of the rules
    `compare.rules_compared` names where it names any; and a member `compare` names and `expected` omits or
    gives empty must be absent or empty, as a refused declaration's `results`, `watches` and `unused` are (the
    S7 design's 5.1). Raises `CaseFileError` for a case that expects results, watches or unused acceptances,
    whose comparison arrives with S7a-2, the piece that gives them."""
    differences: list[str] = []
    for member in case_file.members:
        expected, got = case_file.expected.get(member, []), report.get(member, [])
        if member == "refusals":
            wanted, found = _refusal_set(case_file, expected), _refusal_set(case_file, got)
            if found != wanted:
                differences.append(
                    f"refusals: missing {sorted(wanted - found)}, unexpected {sorted(found - wanted)}"
                )
        elif expected != []:
            raise CaseFileError(f"{case_file.path.name}: comparing a build's {member} arrives with S7a-2")
        elif got != []:
            differences.append(f"{member}: must be absent or empty, got {got!r}")
    return differences


def _refusal_set(case_file: CaseFile, refusals: JsonValue) -> set[tuple[str, str]]:
    """Each refusal's `item` and `pointer`, of the rules compared; a report's refusal lacking either is kept
    as the refusal it is, so that it differs from every expected one."""
    found: set[tuple[str, str]] = set()
    for refusal in refusals if isinstance(refusals, list) else [refusals]:
        item, pointer = (
            refusal.get(name) if isinstance(refusal, dict) else None for name in ("item", "pointer")
        )
        if not (isinstance(item, str) and isinstance(pointer, str)):
            found.add(("not a refusal", json.dumps(refusal, sort_keys=True)))
        elif not case_file.rules or item in case_file.rules:
            found.add((item, pointer))
    return found


def _labels_differ(case_file: CaseFile, expected_labels: JsonValue, labels: JsonValue) -> str | None:
    expected = _label_set(expected_labels)
    if labels is not None and not (
        isinstance(labels, list) and all(isinstance(label, str) for label in labels)
    ):
        return f"not a list of labels: {labels!r}"
    actual = _label_set(labels)
    if "hash" not in case_file.claims:
        expected.discard("hash_not_checked")
        actual.discard("hash_not_checked")
    return None if actual == expected else f"expected {sorted(expected)}, got {sorted(actual)}"


def _label_set(labels: JsonValue) -> set[str]:
    return {label for label in labels if isinstance(label, str)} if isinstance(labels, list) else set()


def _reasons_differ(case_file: CaseFile, expected: JsonValue, actual: JsonValue) -> str | None:
    wanted = Counter(_reason_key(case_file, reason) for reason in _list(expected, "expected.reasons"))
    if not isinstance(actual, list):
        return f"not a list: {actual!r}"
    try:
        found = Counter(_reason_key(case_file, reason) for reason in actual)
    except CaseFileError as error:
        return str(error)
    if found == wanted:
        return None
    missing = sorted((wanted - found).elements(), key=repr)
    unexpected = sorted((found - wanted).elements(), key=repr)
    return f"missing {missing}, unexpected {unexpected}"


def _reason_key(case_file: CaseFile, reason: JsonValue) -> tuple[str, str | None, str | None]:
    """A reason's identity: its code, its condition and its alternative (README, "Case files")."""
    reason = _object(reason, "a reason")
    condition = reason.get("condition")
    code = _string(reason.get("code"), "a reason's code")
    return (
        code,
        None if condition is None else _string(condition, "a reason's condition"),
        _alternative_key(case_file, reason["alternative"]) if "alternative" in reason else None,
    )


def _alternative_key(case_file: CaseFile, index: JsonValue) -> str:
    """An index is a number, compared exactly: bit for bit under `exact`, so `-0` is not `0`, and by value
    under a relative tolerance, which never applies to an index. A bool is never one."""
    if not isinstance(index, float):
        raise CaseFileError(f"a reason's alternative is not a number: {index!r}")
    if case_file.exact:
        return repr(index)
    if case_file.relative_tolerance is None:
        raise CaseFileError(
            f"{case_file.path.name} compares a reason's alternative with neither relative_tolerance nor exact"
        )
    return repr(index + 0.0)


def _conditions_differ(case_file: CaseFile, expected: JsonValue, actual: JsonValue) -> str | None:
    """Condition entries as a set keyed by `name`: each name once, in no set order."""
    wanted: dict[str, JsonValue] = {}
    for entry in _list(expected, "expected conditions"):
        name = _string(_object(entry, "an expected condition entry").get("name"), "a condition entry's name")
        if name in wanted:
            raise CaseFileError(f"{case_file.path.name} expects the condition {name!r} twice")
        wanted[name] = entry
    if not isinstance(actual, list):
        return f"not a list: {actual!r}"
    found: dict[str, JsonValue] = {}
    for entry in actual:
        key = entry.get("name") if isinstance(entry, dict) else None
        if not isinstance(key, str):
            return f"an entry without a string name: {entry!r}"
        if key in found:
            return f"{key!r} twice"
        found[key] = entry
    missing, unexpected = sorted(wanted.keys() - found.keys()), sorted(found.keys() - wanted.keys())
    if missing or unexpected:
        return f"missing {missing}, unexpected {unexpected}"
    differing = ((name, _values_differ(case_file, wanted[name], found[name])) for name in sorted(wanted))
    return next((f"{name}: {difference}" for name, difference in differing if difference is not None), None)


def _alternative_values_differ(case_file: CaseFile, expected: JsonValue, actual: JsonValue) -> str | None:
    """Entries in stored order, member by member, each entry's `labels` and `conditions` as the result's."""
    entries = _list(expected, "expected alternative_values")
    if not isinstance(actual, list) or len(actual) != len(entries):
        return f"expected {len(entries)} entries, got {actual!r}"
    for index, (expected_entry, found) in enumerate(zip(entries, actual, strict=True)):
        wanted = _object(expected_entry, "an expected alternative_values entry")
        if not isinstance(found, dict):
            return f"entry {index} is not an object: {found!r}"
        for name in sorted(wanted.keys() | found.keys()):
            if name == "labels":
                difference = _labels_differ(case_file, wanted.get(name), found.get(name))
            elif name not in found:
                difference = "missing"
            elif name not in wanted:
                difference = f"must be absent, got {found[name]!r}"
            elif name == "conditions":
                difference = _conditions_differ(case_file, wanted[name], found[name])
            else:
                difference = _values_differ(case_file, wanted[name], found[name])
            if difference is not None:
                return f"entry {index}, {name}: {difference}"
    return None


def _sets_differ(expected: JsonValue, actual: JsonValue) -> str | None:
    if not isinstance(actual, list):
        return f"not a list: {actual!r}"
    # A listing holds strings, so its entries compare exactly.
    wanted = {json.dumps(entry, sort_keys=True) for entry in _list(expected, "expected.value")}
    found = {json.dumps(entry, sort_keys=True) for entry in actual}
    if found == wanted:
        return None
    return f"missing {sorted(wanted - found)}, unexpected {sorted(found - wanted)}"


def _values_differ(case_file: CaseFile, expected: JsonValue, actual: JsonValue) -> str | None:
    mismatch = f"expected {expected!r}, got {actual!r}"
    if isinstance(expected, float):
        if not isinstance(actual, float):
            return mismatch
        return None if _numbers_agree(case_file, expected, actual) else mismatch
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return mismatch
        differing = (_values_differ(case_file, e, a) for e, a in zip(expected, actual, strict=True))
        return next((difference for difference in differing if difference is not None), None)
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            return mismatch
        differing = (_values_differ(case_file, expected[name], actual[name]) for name in expected)
        return next((difference for difference in differing if difference is not None), None)
    # None, a bool or a string: bool must not meet a number that equals it.
    return None if type(actual) is type(expected) and actual == expected else mismatch


def _numbers_agree(case_file: CaseFile, expected: float, actual: float) -> bool:
    if case_file.exact:
        return struct.pack(">d", expected) == struct.pack(">d", actual)
    if case_file.relative_tolerance is None:
        raise CaseFileError(
            f"{case_file.path.name} compares a number with neither relative_tolerance nor exact"
        )
    if expected == 0:
        return abs(actual) <= case_file.relative_tolerance
    return abs(actual - expected) <= case_file.relative_tolerance * abs(expected)


def _tolerances(value: JsonValue) -> tuple[float | None, dict[str, float] | None]:
    """One relative tolerance, or a tolerance per precision, `{"binary64", "binary32"}` (a table evaluation
    case's: README, "Case files")."""
    if value is None or (isinstance(value, float) and value >= 0):
        return value, None
    if isinstance(value, dict) and set(value) == {"binary64", "binary32"}:
        per_precision = {
            precision: tolerance
            for precision, tolerance in value.items()
            if isinstance(tolerance, float) and tolerance >= 0
        }
        if len(per_precision) == 2:
            return None, per_precision
    raise CaseFileError(f"relative_tolerance is not a number at least 0, nor one per precision: {value!r}")


def _object(value: JsonValue, what: str) -> JsonObject:
    if not isinstance(value, dict):
        raise CaseFileError(f"{what} is not an object")
    return value


def _list(value: JsonValue, what: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise CaseFileError(f"{what} is not a list")
    return value


def _string(value: JsonValue, what: str) -> str:
    if not isinstance(value, str):
        raise CaseFileError(f"{what} is not a string")
    return value


def reason_json(reason: Reason) -> JsonObject:
    shape: JsonObject = {"code": reason.code}
    if reason.condition is not None:
        shape["condition"] = reason.condition
    if reason.detail is not None:
        shape["detail"] = reason.detail
    return shape


def content_hash_executor(
    parse: Callable[[bytes], JsonValue | Reason] = jsonio.parse,
    digest: Callable[[JsonValue], str] = hashing.content_hash,
) -> Executor:
    """The `content_hash` operation (README, "Operations"), from the given parser and hash."""

    def execute(case_file: CaseFile, claims: frozenset[Suite]) -> JsonObject:
        value = parse(case_file.input_bytes("value"))
        if isinstance(value, Reason):
            return {"status": "not_met", "reasons": [reason_json(value)]}
        return {"status": "met", "reasons": [], "value": digest(value)}

    return execute


def read_executor() -> Executor:
    """A read of the case's request, or of the file `inputs.request` names, among `inputs.records`. The result
    goes through JSON text, as a consumer would receive it."""

    def execute(case_file: CaseFile, claims: frozenset[Suite]) -> JsonObject:
        store = load_records(case_file.input_paths("records"))
        request = case_file.input_bytes("request") if "request" in case_file.inputs else case_file.request
        written = jsonio.parse(json.dumps(read(request, store, claims=claims).to_json()).encode())
        assert not isinstance(written, Reason), written
        return _object(written, "the result")

    return execute


def check_build_executor() -> Executor:
    """A build of the declaration the file `inputs.declaration` names over the records `inputs.records` names,
    its bytes given as they are, so that a declaration that is not JSON can be. The report goes through JSON
    text, as a consumer would receive it."""

    def execute(case_file: CaseFile, claims: frozenset[Suite]) -> JsonObject:
        store = load_records(case_file.input_paths("records"))
        report = check_build(case_file.input_bytes("declaration"), store, claims=claims)
        written = jsonio.parse(json.dumps(report.to_json()).encode())
        assert not isinstance(written, Reason), written
        return _object(written, "the report")

    return execute


def list_records_executor() -> Executor:
    """The `list_records` operation (README, "Operations"): always `met`, listing the good records."""

    def execute(case_file: CaseFile, claims: frozenset[Suite]) -> JsonObject:
        listed = {
            (record.id, record.version)
            for record in load_records(case_file.input_paths("records")).list_records()
        }
        return {
            "status": "met",
            "reasons": [],
            "value": [{"id": id_, "version": version} for id_, version in sorted(listed)],
        }

    return execute


# Table evaluation (README, "Case files"; `read_side_contract.md` section 7).

# The precisions an evaluator may claim (`read_side_contract.md` section 7's lead).
EvaluatorPrecision = Literal["binary64", "binary32"]


@dataclass(frozen=True)
class EvaluatorClaim:
    """What a runner is given beside the suites for an evaluator: the precision it runs in, and the side whose
    derivative it returns at an interior knot (README, "Case files")."""

    precision: EvaluatorPrecision
    side: Side

    def __str__(self) -> str:
        return f"{self.precision} {self.side}"


# The reference evaluator's four configurations: each precision, declaring each side (S3Q15).
EVALUATOR_CLAIMS: tuple[EvaluatorClaim, ...] = (
    EvaluatorClaim("binary64", "left"),
    EvaluatorClaim("binary64", "right"),
    EvaluatorClaim("binary32", "left"),
    EvaluatorClaim("binary32", "right"),
)

# An evaluator: a table at one axis value, in a precision, declaring a side.
TableEvaluator = Callable[[Table, float, EvaluatorPrecision, Side], Evaluation]


class Refusal(Exception):
    """A refusal an evaluator raises in place of reporting it: `read_side_contract.md` section 7 item 7, "a
    raised refusal counts as reported". The `evaluate` executor adapts it to the refusal reported, at that
    axis value; any other exception fails the case, as an executor that raises does."""


def evaluate_executor(
    evaluator: TableEvaluator = table_evaluator.evaluate,
    claims: Sequence[EvaluatorClaim] = EVALUATOR_CLAIMS,
) -> Executor:
    """The `evaluate` operation (README, "Case files"): `evaluator` at each of the case's axis values, in
    order, once under each precision and side it claims. Its result holds one run per claim, each with its
    evaluations, which `compare` takes in turn."""

    def execute(case_file: CaseFile, suites: frozenset[Suite]) -> JsonObject:
        table, points = _evaluate_request(case_file)
        runs: list[JsonValue] = []
        for claim in claims:
            evaluations: list[JsonValue] = [
                _evaluation_json(_reported(evaluator, table, at, claim)) for at in points
            ]
            runs.append({"precision": claim.precision, "side": claim.side, "evaluations": evaluations})
        return {"runs": runs}

    return execute


def _reported(evaluator: TableEvaluator, table: Table, at: float, claim: EvaluatorClaim) -> Evaluation:
    """The evaluation at `at`, a raised `Refusal` adapted to the refusal reported, with no number (the TE
    suite's README: "Both count as reported; a runner adapts each")."""
    try:
        return evaluator(table, at, claim.precision, claim.side)
    except Refusal:
        return Evaluation(refused=True)


def _evaluate_request(case_file: CaseFile) -> tuple[Table, list[float]]:
    """The table and the axis values of a table evaluation case. A table the reference evaluator refuses
    (`table_evaluator.structural_fault`) is a defect in the case."""
    request = _object(case_file.request, "request")
    table = _object(request.get("table"), "request.table")
    points = _numbers(request.get("at"), "request.at")
    source_range = table.get("source_range")
    try:
        return Table(
            x=tuple(_numbers(table.get("x"), "table.x")),
            y=tuple(_numbers(table.get("y"), "table.y")),
            scheme=_scheme(table.get("scheme")),
            edges=tuple(_numbers(table.get("edges"), "table.edges")),
            source_range=None if source_range is None else _pair(source_range, "table.source_range"),
        ), points
    except ValueError as error:
        raise CaseFileError(f"{case_file.path.name}: {error}") from error


def _scheme(value: JsonValue) -> Scheme:
    match value:
        case "linear" | "loglog":
            return value
        case _:
            raise CaseFileError(f"a table whose scheme is {value!r}")


def _evaluation_json(evaluation: Evaluation) -> JsonObject:
    """An evaluation as the comparison reads it: `refused` always; `in_range`, `value` and `derivative` where
    the evaluator returned them."""
    entry: JsonObject = {"refused": evaluation.refused}
    if evaluation.in_range is not None:
        entry["in_range"] = evaluation.in_range
    for name, number in (("value", evaluation.value), ("derivative", evaluation.derivative)):
        if number is not None:
            entry[name] = float(number)
    return entry


def _evaluation_runs_differ(case_file: CaseFile, result: Mapping[str, JsonValue]) -> list[str]:
    """How each run of a table evaluation case, one per precision and side the evaluator claims, differs from
    the case's evaluations, entry by entry in order, at the tolerance of the run's precision."""
    tolerances = case_file.precision_tolerances
    if tolerances is None:
        raise CaseFileError(
            f"{case_file.path.name}: a table evaluation case without a tolerance per precision"
        )
    points = _numbers(_object(case_file.request, "request").get("at"), "request.at")
    expected = [
        _object(entry, "an expected evaluation")
        for entry in _list(case_file.expected.get("evaluations"), "expected.evaluations")
    ]
    if len(expected) != len(points):
        raise CaseFileError(f"{case_file.path.name}: not one expected evaluation per axis value")
    runs = result.get("runs")
    if not isinstance(runs, list) or not runs:
        # An evaluator that claims the suite claims a precision and a side (read_side_contract.md section 7
        # item 8), so a result with no run is no pass.
        return ["evaluations: no run under any precision and side"]
    differences: list[str] = []
    for run in runs:
        if not isinstance(run, dict):
            differences.append(f"evaluations: a run that is not an object: {run!r}")
            continue
        precision, side, found = run.get("precision"), run.get("side"), run.get("evaluations")
        if not (isinstance(precision, str) and precision in tolerances and side in ("left", "right")):
            differences.append(f"evaluations: a run under no precision and side: {run!r}")
            continue
        if not isinstance(found, list) or len(found) != len(expected):
            differences.append(f"{precision} {side}: expected {len(expected)} evaluations, got {found!r}")
            continue
        for at, wanted, got in zip(points, expected, found, strict=True):
            difference = _evaluation_differs(wanted, got, tolerances[precision], str(side))
            if difference is not None:
                differences.append(f"{precision} {side}: at {at!r}: {difference}")
    return differences


def _evaluation_differs(wanted: JsonObject, got: JsonValue, tolerance: float, side: str) -> str | None:
    """How one evaluation differs from its expected entry, which is compared only by the members it holds and
    whether a refusal is reported (README, "Case files")."""
    if not isinstance(got, dict):
        return f"not an object: {got!r}"
    refused = got.get("refused")
    if not isinstance(refused, bool):
        return f"the refusal is not reported as true or false: {refused!r}"
    if wanted.get("refused") is True:
        # A refused entry "passes only where the evaluator reports the refusal and each number it returns
        # there is absent or NaN, never finite and never infinite". A JSON `null` is no number returned, and
        # reads as absent here as in every other entry.
        if not refused:
            return "expected the refusal, got none"
        beside = [
            f"{name} {got[name]!r}"
            for name in ("value", "derivative")
            if got.get(name) is not None and not _nan(got[name])
        ]
        return f"a number beside the refusal: {', '.join(beside)}" if beside else None
    # Any other entry passes "only where the evaluator reports no refusal".
    if refused:
        return "refused where no refusal is due"
    in_range = wanted.get("in_range")
    if not isinstance(in_range, bool):
        raise CaseFileError(f"an expected evaluation that is neither refused nor in_range: {wanted!r}")
    if got.get("in_range") is not in_range:
        return f"in_range: expected {in_range!r}, got {got.get('in_range')!r}"
    for name in ("value", "derivative"):
        # Outside the readable range, "each number passes where it is the expected one, or absent or NaN".
        difference = _evaluated_number_differs(
            name, wanted.get(name), got.get(name), tolerance, side, absent_passes=not in_range
        )
        if difference is not None:
            return f"{name}: {difference}"
    return None


def _evaluated_number_differs(
    name: str, expected: JsonValue, found: JsonValue, tolerance: float, side: str, *, absent_passes: bool
) -> str | None:
    """How a returned value or derivative, `None` where absent, differs from the expected one (README, "Case
    files")."""
    if expected == "none":
        # "A `"none"` passes only where the evaluator returns that number absent or NaN."
        return None if found is None or _nan(found) else f"expected none, got {found!r}"
    if isinstance(expected, dict):
        # "`{"left", "right"}` ..., of which the side the evaluator declares is compared"
        expected = expected.get(side)
    if not isinstance(expected, float):
        raise CaseFileError(f"an expected {name} that is not a number, none or one per side: {expected!r}")
    if found is None or _nan(found):
        return None if absent_passes else f"expected {expected!r}, got {'none' if found is None else 'NaN'}"
    if not isinstance(found, float):
        return f"expected {expected!r}, got {found!r}"
    if name == "derivative" and expected == 0.0:
        # "an expected derivative of `0` passes only where it is zero, of either sign"
        agree = found == 0.0
    elif expected == 0.0:
        # "the tolerance being absolute where an expected value is zero"
        agree = abs(found) <= tolerance
    else:
        agree = abs(found - expected) <= tolerance * abs(expected)
    return None if agree else f"expected {expected!r}, got {found!r}"


def _nan(value: JsonValue) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _numbers(value: JsonValue, what: str) -> list[float]:
    numbers = _list(value, what)
    if not all(isinstance(number, float) for number in numbers):
        raise CaseFileError(f"{what} holds something other than numbers")
    return [number for number in numbers if isinstance(number, float)]


def _pair(value: JsonValue, what: str) -> tuple[float, float]:
    numbers = _numbers(value, what)
    if len(numbers) != 2:
        raise CaseFileError(f"{what} is not two numbers")
    return numbers[0], numbers[1]


# The claims the case files run under, each under every one that agrees with it: plain read and HS, as by
# default; plain read alone, a reader without HS; and with the fits and reference data suite too, whose
# `want`s step 0 then accepts. Under it a read gives the same as without it, but that step 13 gives
# `want_mismatch` for each of the suite's `want`s, which no constant can give, and raises for `fit` on a
# field holding a fit record, which the suite reads: so claiming it gives no answer a step not built could
# change.
# Then a build's: the build checks with plain read and HS, as a build claims by default
# (`materica.core.declarations.CLAIMS`), and with plain read alone. A build claims neither the scene suite,
# USD read nor the sampling suite yet, so a build-check case that states those claims false runs under both.
# Last, the reference evaluator's: the table evaluation suite alone, which `materica` does not claim, at each
# precision and side (`EVALUATOR_CLAIMS`).
REFERENCE_EVALUATOR: frozenset[Suite] = frozenset({"table_evaluation"})
CONFIGURATIONS: tuple[frozenset[Suite], ...] = (
    frozenset({"plain_read", "hash"}),
    frozenset({"plain_read"}),
    frozenset({"plain_read", "hash", "fits_and_reference_data"}),
    frozenset({"plain_read", "hash", "build_checks"}),
    frozenset({"plain_read", "build_checks"}),
    REFERENCE_EVALUATOR,
)
EXECUTORS: dict[str, Executor] = {
    "content_hash": content_hash_executor(),
    "read": read_executor(),
    "list_records": list_records_executor(),
    "check_build": check_build_executor(),
    "evaluate": evaluate_executor(),
}
