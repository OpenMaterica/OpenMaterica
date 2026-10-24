# SPDX-License-Identifier: Apache-2.0
"""The reference model pinned to the conformance cases: it agrees with every case file of a read in the
repository, whatever step of the implementation runs it, or the case file is listed in `exceptions.py` under
its kind. The table evaluation and record-check suites are left out, being no reads (`cases.NOT_A_READ`).

The list is exact (the maintainer's ruling 3 on S2a-1's open points): a listed case file the model agrees with
is stale and fails, and so does a disagreement no kind lists. A case file on which the model gives no verdict
is a disagreement, never a pass. Where the model and a case disagree, the text decides: a fault of the model
is fixed; a case that contradicts the text is listed, with the quotes, and left for the maintainer, never
edited here (case files change through the case tools alone)."""

import re
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import pytest

from tests.conformance.runner import CaseFile
from tests.reference import build_model, read_model
from tests.reference.build_model import Refusal, Refused
from tests.reference.cases import (
    BUILD_CONFIGURATIONS,
    Outcome,
    agreeing,
    answer,
    build_case_files,
    build_differences,
    build_outcome,
    case_files,
    judged,
    outcome,
    read_case_files,
)
from tests.reference.exceptions import BUILD_EXCEPTIONS, EXCEPTIONS, Excepted
from tests.reference.strict_json import JsonObject, parse


@pytest.mark.parametrize("case_file", read_case_files(), ids=lambda case_file: case_file.path.name)
def test_the_model_agrees_with_the_case_file(case_file: CaseFile) -> None:
    problem = judged(case_file.path.name, outcome(case_file), EXCEPTIONS)
    assert problem is None, problem


# The operations that are no read: a table evaluation, a record check and a quote hash.
NO_READ = ("evaluate", "check", "quote_sha256", "check_build")


def left_out_problems(every: tuple[CaseFile, ...], read: tuple[CaseFile, ...]) -> list[str]:
    """Each case file left out of the reads that is a read, and each kept that is none: an evaluation, a
    record check, a quote hash or a build check."""
    kept = {case_file.path.name for case_file in read}
    return [
        f"{case_file.path.name}: {'kept' if case_file.path.name in kept else 'left out'}"
        for case_file in every
        if (case_file.path.name in kept) == (case_file.operation in NO_READ)
    ]


def test_the_files_left_out_are_exactly_those_that_are_no_read() -> None:
    assert left_out_problems(case_files(), read_case_files()) == []
    assert len(case_files()) - len(read_case_files()) >= 35 + 197 + 50


def test_a_read_left_out_or_an_evaluation_or_check_kept_fails() -> None:
    read = read_case_files()
    assert left_out_problems(case_files(), read[1:]) == [f"{read[0].path.name}: left out"]
    for operation in NO_READ:
        other = next(case_file for case_file in case_files() if case_file.operation == operation)
        assert left_out_problems(case_files(), (*read, other)) == [f"{other.path.name}: kept"]


def test_every_listed_case_file_is_a_read_and_every_kind_gives_its_reason() -> None:
    names = {case_file.path.name for case_file in read_case_files()}
    for kind, excepted in EXCEPTIONS.items():
        assert excepted.reason.strip(), kind
        assert excepted.case_files, kind
        assert excepted.case_files <= names, sorted(excepted.case_files - names)


def test_no_verdict_is_listed_by_the_detail_it_gives() -> None:
    assert all(
        excepted.detail is not None for excepted in EXCEPTIONS.values() if excepted.outcome == "no verdict"
    )


DIFFERING = Excepted("a reason", "differs", frozenset({"listed.json"}))
TABLES = Excepted("a reason", "no verdict", frozenset({"listed.json"}), detail="a table")


@pytest.mark.parametrize(
    ("name", "found", "exceptions", "problem"),
    [
        ("listed.json", Outcome("agrees"), {}, None),
        ("listed.json", Outcome("differs"), {"kind": DIFFERING}, None),
        ("listed.json", Outcome("agrees"), {"kind": DIFFERING}, "a stale entry"),
        ("unlisted.json", Outcome("differs", "status"), {"kind": DIFFERING}, "no kind lists it"),
        ("unlisted.json", Outcome("no verdict", "a table"), {}, "no kind lists it"),
        ("listed.json", Outcome("no verdict"), {"kind": DIFFERING}, "but no verdict"),
        ("listed.json", Outcome("differs"), {"one": DIFFERING, "two": DIFFERING}, "listed under 2 kinds"),
        ("listed.json", Outcome("no verdict", "a table"), {"kind": TABLES}, None),
        ("listed.json", Outcome("no verdict", "a pick"), {"kind": TABLES}, "for 'a table', but 'a pick'"),
        ("listed.json", Outcome("agrees"), {"kind": TABLES}, "a stale entry"),
    ],
)
def test_the_list_can_fail(
    name: str, found: Outcome, exceptions: Mapping[str, Excepted], problem: str | None
) -> None:
    given = judged(name, found, exceptions)
    assert given == problem if problem is None else given is not None and problem in given


def test_a_fault_seeded_in_the_model_disagrees(monkeypatch: pytest.MonkeyPatch) -> None:
    """The comparison sees a model that drops the field's label (`read_side_contract.md` step 12)."""
    (case_file,) = [found for found in case_files() if found.path.name == "PR-035.linear_label_returned.json"]
    assert outcome(case_file).kind == "agrees"

    def no_labels(field_value: JsonObject, provenance: JsonObject) -> list[str]:
        return []

    monkeypatch.setattr(read_model, "step_12_labels", no_labels)
    assert outcome(case_file).kind == "differs"


# A case compares only the members its `compare` names (README.md, "Case files"), so no case file sees a
# member a result holds outside `read_side_contract.md` section 2's table. The model's whole result is held to
# the table's names here, read from the text.
RESULT_SECTION = "## 2. The read result"
SPECIFICATION = Path(__file__).resolve().parents[2] / "docs" / "specification"


def result_members() -> frozenset[str]:
    """The member names of `read_side_contract.md` section 2's table, as the text writes them."""
    text = (SPECIFICATION / "read_side_contract.md").read_text(encoding="utf-8")
    lines = text[text.index(RESULT_SECTION) :].splitlines()
    start = next(number for number, line in enumerate(lines) if line.startswith("|"))
    end = next(number for number, line in enumerate(lines[start:], start) if not line.startswith("|"))
    rows = lines[start + 2 : end]  # the header and its rule aside
    names = [re.match(r"^\| `([a-z_]+)` \|", row) for row in rows]
    assert all(names), rows
    return frozenset(name[1] for name in names if name)


def members_outside_the_table() -> Iterator[str]:
    """Each read's result, under each configuration of claims its case file allows, that holds a member the
    result table does not name."""
    members = result_members()
    for case_file in read_case_files():
        if case_file.operation != "read":
            continue
        for claims in agreeing(case_file):
            given = answer(case_file, claims)
            if isinstance(given, read_model.NoVerdict):
                break
            outside = sorted(set(given) - members)
            if outside:
                yield f"{case_file.path.name}, claiming {sorted(claims)}: {outside}"


def test_the_models_results_hold_no_member_outside_the_result_table() -> None:
    assert {"status", "reasons", "value", "labels", "assumption"} <= result_members()
    assert list(members_outside_the_table()) == []


def test_a_result_holding_a_labels_basis_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Control: a model that returns a field's `label_basis` beside the table's members, which the case files'
    comparisons pass (they compare only the members `compare` names)."""
    (case_file,) = [
        found for found in case_files() if found.path.name == "PR-030.label_basis_stated_not_returned.json"
    ]
    returned = read_model.result

    def with_its_basis(
        reasons: read_model.Reasons, labels: Sequence[str], members: JsonObject | None = None
    ) -> JsonObject:
        result = returned(reasons, labels, members)
        result["label_basis"] = {"basis": "stated"}
        return result

    monkeypatch.setattr(read_model, "result", with_its_basis)
    assert outcome(case_file).kind == "agrees"
    found = next(members_outside_the_table(), None)
    assert found is not None
    assert found.endswith("['label_basis']")


# The build-check files, and the build's own model (`build_model.py`), which decides the declaration's own
# check.


@pytest.mark.parametrize("case_file", build_case_files(), ids=lambda case_file: case_file.path.name)
def test_the_build_model_agrees_with_the_build_case_file(case_file: CaseFile) -> None:
    problem = judged(case_file.path.name, build_outcome(case_file), BUILD_EXCEPTIONS)
    assert problem is None, problem


def test_the_build_files_are_exactly_those_whose_operation_is_check_build() -> None:
    names = {case_file.path.name for case_file in build_case_files()}
    assert names == {
        case_file.path.name for case_file in case_files() if case_file.operation == "check_build"
    }
    assert len(names) >= 108


def test_the_model_agrees_with_every_file_of_the_declaration_s_own_check() -> None:
    """S7a-1's files, the refusal cases, whose expected answer holds refusals and no results (the suite's
    README, "Reading a case"), each agree, none listed."""
    own = [case_file for case_file in build_case_files() if "results" not in case_file.expected]
    assert len(own) >= 51
    assert all("refusals" in case_file.expected for case_file in own)
    assert [case_file.path.name for case_file in own if build_outcome(case_file).kind != "agrees"] == []
    listed = {name for excepted in BUILD_EXCEPTIONS.values() for name in excepted.case_files}
    assert listed.isdisjoint(case_file.path.name for case_file in own)


def test_every_listed_build_file_is_a_build_file_and_every_kind_gives_its_reason() -> None:
    names = {case_file.path.name for case_file in build_case_files()}
    for kind, excepted in BUILD_EXCEPTIONS.items():
        assert excepted.reason.strip(), kind
        assert excepted.case_files, kind
        assert excepted.case_files <= names, sorted(excepted.case_files - names)
        assert excepted.outcome != "no verdict" or excepted.detail is not None, kind


def test_a_build_file_runs_under_every_configuration_its_claims_allow() -> None:
    """A file stating no claim runs under all 32 build configurations; one denying a suite, under the 16
    without it."""
    by_name = {case_file.path.name: case_file for case_file in build_case_files()}
    assert len(BUILD_CONFIGURATIONS) == 32
    assert len(agreeing(by_name["BC-004.tolerance_without_reason.json"], BUILD_CONFIGURATIONS)) == 32
    denied = agreeing(by_name["BC-051.checked_over_domain.json"], BUILD_CONFIGURATIONS)
    assert len(denied) == 16
    assert all("scene_documents" not in claims for claims in denied)


def build_file(name: str) -> CaseFile:
    (case_file,) = [found for found in build_case_files() if found.path.name == name]
    return case_file


TEMPERATURE = "/models/0/requirements/0/conditions/temperature"
LABEL = "/models/0/acceptances/0/label"


@pytest.mark.parametrize(
    ("name", "report", "problem"),
    [
        ("BC-004.tolerance_without_reason.json", Refused(frozenset({Refusal("BC-004", TEMPERATURE)})), None),
        (
            "BC-004.tolerance_without_reason.json",
            Refused(frozenset({Refusal("BC-048", TEMPERATURE)})),
            "missing",
        ),
        (
            "BC-004.tolerance_without_reason.json",
            Refused(frozenset({Refusal("BC-004", TEMPERATURE), Refusal("BC-048", TEMPERATURE)})),
            "unexpected [('BC-048'",
        ),
        (
            "BC-004.tolerance_without_reason.json",
            Refused(frozenset({Refusal("BC-004", "/models/0")})),
            "missing",
        ),
        ("BC-004.tolerance_without_reason.json", Refused(frozenset()), "missing"),
        (
            "BC-050.requirement_names_another_label.json",
            Refused(frozenset({Refusal("BC-050", LABEL), Refusal("BC-048", LABEL)})),
            None,
        ),
        (
            "BC-050.requirement_names_another_label.json",
            Refused(frozenset({Refusal("BC-048", LABEL)})),
            "missing",
        ),
        ("BC-051.engine_over_records.json", Refused(frozenset(), {"BC-040": "item 7's pointers"}), None),
        (
            "BC-051.engine_over_records.json",
            Refused(frozenset(), {"BC-051": "an engine's own"}),
            "no verdict",
        ),
        (
            "BC-004.tolerance_without_reason.json",
            Refused(frozenset(), {"BC-040": "item 7's pointers"}),
            "no verdict",
        ),
    ],
)
def test_the_build_comparison_can_fail(name: str, report: Refused, problem: str | None) -> None:
    """Refusals compared as a set, only those of the rules `compare.rules_compared` names where it names any,
    and a rule the model does not place compared no verdict, never a pass."""
    found = build_differences(build_file(name), report)
    if problem is None:
        assert found == []
    elif problem == "no verdict":
        assert isinstance(found, read_model.NoVerdict)
    else:
        assert isinstance(found, list)
        assert len(found) == 1
        assert problem in found[0]


def test_a_refused_report_compared_where_a_case_expects_results_differs() -> None:
    """A past-the-declaration file's expected `results`, compared against a refused report, is missing: a
    build that refuses and still passes as reading would not slip through."""
    case_file = build_file("BC-003.field_read_with_no_requirement.json")
    found = build_differences(case_file, Refused(frozenset()))
    assert isinstance(found, list)
    assert "results: missing" in found


def test_a_build_model_that_refuses_nothing_disagrees(monkeypatch: pytest.MonkeyPatch) -> None:
    """Control: a model whose check finds no fault gives no verdict on every refusal file, which no kind
    lists."""

    def no_fault(self: build_model.DeclarationCheck, pointer: str, *rules: str, apart: str = "") -> None:
        return None

    monkeypatch.setattr(build_model.DeclarationCheck, "fault", no_fault)
    outcome_found = build_outcome(build_file("BC-004.tolerance_without_reason.json"))
    assert outcome_found == Outcome("no verdict", "past the declaration (S7a-2 to S7a-4)")
    assert judged("BC-004.tolerance_without_reason.json", outcome_found, BUILD_EXCEPTIONS) is not None


def test_a_refused_report_holds_the_declaration_as_given_and_its_consumer() -> None:
    """Where the text is JSON, the refused report holds the declaration as given, and its `consumer` where it
    declares one (the maintainer's ruling of 2026-10-24); a text that is not JSON gives neither."""
    declared = build_file("BC-004.tolerance_without_reason.json").input_bytes("declaration")
    report = build_model.check_build(declared, frozenset({"plain_read", "build_checks"}))
    assert isinstance(report, Refused)
    given = report.to_json()
    assert given["declaration"] == parse(declared)
    assert given["consumer"] == {"name": "conformance_consumer", "version": "1.0.0"}
    array = build_model.check_build(b"[1.0]", frozenset({"plain_read", "build_checks"}))
    assert isinstance(array, Refused)
    assert array.to_json() == {"refusals": [{"item": "BC-048", "pointer": ""}], "declaration": [1.0]}
    broken = build_model.check_build(b'{"a": 1, "a": 2}', frozenset({"plain_read", "build_checks"}))
    assert isinstance(broken, Refused)
    assert broken.to_json() == {"refusals": [{"item": "BC-048", "pointer": ""}]}
