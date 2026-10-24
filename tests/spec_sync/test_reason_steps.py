# SPDX-License-Identifier: Apache-2.0
"""Each reason code is given only at the steps the reason table names (`read_side_contract.md` section 4,
`Step`, generated into `vocabulary/reasons.json`).

Against the text: each code is named in the text of each step the table gives it (the step's item in section
3, with the passages that item hands its checks to, and step 6 giving an overlay the codes steps 1 to 5 give
the target, which the table must give at step 6 too), and no step's text names a code the table does not give
it there. A code no step gives is named in the document of each procedure the table gives it.

Against the code, for the steps built, statically and as run: every `Reason` a module of the core constructs,
by any name, is constructed in a function this module places at a step, with a code the table allows there;
and every reason a read of a case file returns was constructed at a step that may give it, under every claim
the case agrees with.
"""

import ast
import json
import re
import sys
from collections.abc import Callable, Collection, Iterator
from functools import cache
from pathlib import Path
from types import FrameType

import pytest

from materica.core import read as read_module
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult, read
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from materica.shapes import Suite, Want
from scripts.gen_vocabulary import PROCEDURES, SPECIFICATION
from tests.conformance import runner
from tests.conformance.runner import CONFIGURATIONS, CaseFile, agreeing
from tests.spec_sync.schemas import SCHEMA

Documents = Callable[[str], str]
# Each code, and the steps of section 3 that give it or the procedures that give one no step gives.
Table = dict[str, tuple[frozenset[int], frozenset[str]]]
CORE = Path(read_module.__file__).parent


def reason_table() -> Table:
    reasons = json.loads((SCHEMA / "vocabulary" / "reasons.json").read_text(encoding="utf-8"))["reasons"]
    return {
        code: (frozenset(int(step) for step in row.get("steps", [])), frozenset(row.get("procedures", [])))
        for code, row in reasons.items()
    }


TABLE = reason_table()


def document(name: str) -> str:
    return (SPECIFICATION / name).read_text(encoding="utf-8")


def flowing(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def between(text: str, start: str, end: str) -> str:
    """The text from `start`, which must be there once, to the first `end` after it."""
    flat = flowing(text)
    assert flat.count(start) == 1, start
    first = flat.index(start)
    last = flat.index(end, first + len(start))
    return flat[first:last]


def steps(read_document: Documents) -> dict[int, str]:
    """Each step's item in section 3, by its number."""
    procedure = between(
        read_document("read_side_contract.md"), "## 3. The read procedure", "## 4. Reason codes"
    )
    items = list(re.finditer(r"(?:^| )(\d+)\. \*\*", procedure))
    return {
        int(item[1]): procedure[item.start() : following.start() if following else len(procedure)]
        for item, following in zip(items, [*items[1:], None], strict=True)
    }


# The passages a step's item hands its checks to: the document, the text a passage starts and ends with.
HANDED = {
    0: [("read_side_contract.md", "A request is read as JSON by", "Two checks need the form")],
    6: [("record_format.md", "2. `base` names one material", "## 5. Value fields")],
    10: [
        ("read_side_contract.md", "One check needs the field's specimen facts", "This fault, like step 11's"),
        ("read_side_contract.md", "## 5. How a condition is checked", "**The form's range.**"),
    ],
    11: [
        ("read_side_contract.md", "Two checks need the form", "One check needs the field's specimen facts"),
        ("read_side_contract.md", "**The form's range.**", "## 6. What a read returns"),
    ],
    13: [("read_side_contract.md", "## 6. What a read returns", "## 7. Evaluating a table")],
}
# Section 4: "step 6 giving an overlay the codes steps 1 to 5 give the target".
OVERLAY = "step 6 giving an overlay the codes steps 1 to 5 give the target"
TARGET_STEPS = frozenset(range(1, 6))
# Codes a step's text names without giving them, each with the sentence that names it.
MENTIONED = {
    (13, "no_pick"): "Under `no_pick` no nominal is applied, nor compared with the bounds",
}
PROCEDURE_DOCUMENTS = {
    "scene": ("geometry.md",),
    "USD read": ("usd_binding.md",),
    "engine adapter": ("usd_binding.md",),
    "build": ("declarations.md",),
    "family evaluation": ("model_families.md",),
    "mixing": ("mixing_rules.md",),
}


def named(text: str, table: Table) -> set[str]:
    return {code for code in re.findall(r"`([a-z_]+)`", text) if code in table}


def texts(read_document: Documents) -> dict[int, str]:
    """Each step's text: its item in section 3, and the passages the item hands its checks to."""
    return {
        step: item + "".join(between(read_document(name), *ends) for name, *ends in HANDED.get(step, []))
        for step, item in steps(read_document).items()
    }


def check_text(table: Table, read_document: Documents) -> None:
    text_of = texts(read_document)
    assert set(text_of) == set(range(14))
    assert OVERLAY in flowing(read_document("read_side_contract.md"))
    for (step, _), sentence in MENTIONED.items():
        assert sentence in text_of[step], sentence
    for step, text in text_of.items():
        own = named(text, table) - {code for (at, code) in MENTIONED if at == step}
        assert {code for code in own if step not in table[code][0]} == set(), f"step {step}"
    for code, (given, procedures) in table.items():
        overlays = bool(given & TARGET_STEPS)
        assert 6 in given or not overlays, f"{code}: step 6 gives an overlay what steps 1 to 5 give"
        for step in given:
            assert code in named(text_of[step], table) or (step == 6 and overlays), f"{code} at step {step}"
        for procedure in procedures:
            assert any(
                code in named(read_document(name), table) for name in PROCEDURE_DOCUMENTS[procedure]
            ), f"{code} by {procedure}"
        assert bool(given) != bool(procedures), code
    assert set(PROCEDURE_DOCUMENTS) == set(PROCEDURES)


def test_each_code_is_given_at_the_steps_the_table_names_and_no_other() -> None:
    check_text(TABLE, document)


# The functions of the core that construct a reason, by module and qualified name, and the step each belongs
# to; None for a function that is no step's: `jsonio.parse` gives the JSON reader's refusal, which `_parsed`
# passes to step 0, to report as `request_incomplete`, and `RecordStore.add` notes for an unreadable source,
# which step 1 reports; `merged` copies the reasons a step found, each code, condition and alternative once,
# and `tagged` copies those found reading one alternative, with its index. Step 8's checks of shape construct
# theirs in `value_shapes.invalid` and `unknown_token`. `parse_declaration` gives the reader's refusal of a
# declaration's text, which no read reports: the build refuses the declaration at the empty pointer.
STEP_OF: dict[tuple[str, str], int | None] = {
    ("jsonio.py", "parse"): None,
    ("declarations.py", "parse_declaration"): None,
    ("reasons.py", "merged"): None,
    ("reasons.py", "tagged"): None,
    ("read.py", "ReadRequest.from_json"): 0,
    ("read.py", "_parsed"): None,
    ("read.py", "_incomplete"): 0,
    ("read.py", "_slips"): 0,
    ("read.py", "_member"): 0,
    ("read.py", "_target"): 0,
    ("read.py", "_want"): 0,
    ("read.py", "_registered"): 0,
    ("read.py", "_unit"): 0,
    ("read.py", "_operating_condition"): 0,
    ("read.py", "_requirement_condition"): 0,
    ("read.py", "_numeric"): 0,
    ("read.py", "_implied_condition"): 0,
    ("read.py", "_implied_value"): 0,
    ("read.py", "_acceptances"): 0,
    ("read.py", "_nominal"): 0,
    ("read.py", "_extrapolation"): 0,
    ("read.py", "_acceptance_field"): 0,
    ("resolve.py", "_candidate"): 1,
    ("record.py", "Record.version_refusal"): 2,
    ("record.py", "Record.envelope_refusal"): 3,
    ("resolve.py", "resolve_record"): 4,
    ("record.py", "Record.type_refusal"): 5,
    ("record.py", "RecordStore.add"): None,
    ("fields.py", "find_field"): 7,
    ("fields.py", "alternatives_problems"): 7,
    ("read.py", "_read_alternatives"): 7,
    ("fields.py", "_form"): 8,
    ("fields.py", "_basis_allowed"): 8,
    ("fields.py", "_own_member"): 8,
    ("fields.py", "evidence"): 8,
    ("fields.py", "_points"): 8,
    ("fields.py", "_mismatch"): 9,
    ("conditions.py", "_entry"): 10,
    ("conditions.py", "_compared"): 10,
    ("conditions.py", "_disagreeing"): 10,
    ("read.py", "range_report"): 11,
    ("read.py", "_origin"): 12,
    ("read.py", "_by_want"): 13,
    ("read.py", "_nominal_read"): 13,
    ("value_shapes.py", "invalid"): 8,
    ("value_shapes.py", "unknown_token"): 8,
}
# Every module of the core, a new one included.
MODULES = tuple(sorted(path.name for path in CORE.glob("*.py")))


def callee(call: ast.Call) -> str | None:
    """The last name of what `call` calls: `Reason` for `Reason(...)` and `reasons.Reason(...)` alike."""
    if isinstance(call.func, ast.Name):
        return call.func.id
    return call.func.attr if isinstance(call.func, ast.Attribute) else None


def constructed(source: str) -> Iterator[tuple[str, str | None]]:
    """Each reason `source` constructs, as the qualified name of the function it is in and its code, None
    where the code is not written out: `Reason("code", ...)` or `Reason(code="code")`, by any name ending in
    `Reason`, or `_incomplete(...)`, which constructs `request_incomplete`."""

    def visit(node: ast.AST, owner: tuple[str, ...]) -> Iterator[tuple[str, str | None]]:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            owner = (*owner, node.name)
        if isinstance(node, ast.Call) and callee(node) == "Reason":
            given = [*node.args[:1], *(keyword.value for keyword in node.keywords if keyword.arg == "code")]
            code = given[0] if len(given) == 1 else None
            yield ".".join(owner), str(code.value) if isinstance(code, ast.Constant) else None
        elif isinstance(node, ast.Call) and callee(node) == "_incomplete":
            yield ".".join(owner), "request_incomplete"
        for child in ast.iter_child_nodes(node):
            yield from visit(child, owner)

    yield from visit(ast.parse(source), ())


def check_code(table: Table, sources: dict[str, str]) -> None:
    for module, source in sources.items():
        for function, code in constructed(source):
            assert (module, function) in STEP_OF, (
                f"{module}: {function} constructs {code} at no step this test knows"
            )
            step = STEP_OF[(module, function)]
            if code is None:
                assert step is None, f"{module}: {function} constructs a code not written out, at step {step}"
            else:
                assert step is None or step in table[code][0], (
                    f"{code} at step {step}, in {module}: {function}"
                )


def test_the_reads_code_constructs_each_code_at_a_step_that_gives_it() -> None:
    check_code(TABLE, {module: (CORE / module).read_text(encoding="utf-8") for module in MODULES})


def traced_read(
    request: JsonValue | bytes, store: RecordStore, claims: frozenset[Suite]
) -> tuple[ReadResult, list[tuple[str, int | None]]]:
    """A read, and the code and step of every reason constructed while it ran: the step `STEP_OF` gives the
    nearest function that constructed it, or -1 where it gives none."""
    target = Reason.__init__.__code__
    created: list[tuple[str, int | None]] = []

    def profile(frame: FrameType, event: str, _: object) -> None:
        if event != "call" or frame.f_code is not target:
            return
        caller = frame.f_back
        while caller is not None:
            key = (Path(caller.f_code.co_filename).name, caller.f_code.co_qualname)
            if key in STEP_OF:
                created.append((str(frame.f_locals["code"]), STEP_OF[key]))
                return
            caller = caller.f_back
        created.append((str(frame.f_locals["code"]), -1))

    sys.setprofile(profile)
    try:
        result = read(request, store, claims=claims)
    finally:
        sys.setprofile(None)
    return result, created


READS = [
    case_file
    for case_file in runner.discover()
    if case_file.operation == "read" and runner.step_done(case_file)
]


@cache
def traced(case_file: CaseFile) -> tuple[tuple[str, frozenset[int | None]], ...]:
    """For each reason a read of `case_file` returns, under each claim it agrees with, the steps at which a
    reason of its code was constructed during that read."""
    found: list[tuple[str, frozenset[int | None]]] = []
    for claims in agreeing(case_file, CONFIGURATIONS):
        store = RecordStore()
        for path in case_file.input_paths("records"):
            store.add(path.name, path.read_bytes())
        request: JsonValue | bytes = (
            case_file.input_bytes("request") if "request" in case_file.inputs else case_file.request
        )
        result, created = traced_read(request, store, claims)
        found += [
            (reason.code, frozenset(step for code, step in created if code == reason.code))
            for reason in result.reasons
        ]
    return tuple(found)


def check_traced(table: Table, case_file: CaseFile) -> None:
    for code, at in traced(case_file):
        assert -1 not in at, f"{code} constructed where no step is placed"
        assert at - {None}, f"{code} constructed at no step"
        assert at - {None} <= table[code][0], f"{code} constructed at {sorted(map(str, at))}"


@pytest.mark.parametrize("case_file", READS, ids=lambda case_file: case_file.path.name)
def test_each_reason_a_read_returns_was_constructed_at_a_step_that_gives_it(case_file: CaseFile) -> None:
    check_traced(TABLE, case_file)


# The codes the table gives at a step built in part, which the code of a step not built yet gives: at step 7,
# a pick's (S4); at step 11, a power law's unstated range (no 0.1.0 field takes a power law), a table's range
# and the request's two faults there being built (S3b-2); at step 12, a fill-in's (S4). No read of a case file
# returns one, so an entry left here once its code is built fails.
NOT_BUILT = {
    ("pick_invalid", 7),
    ("range_unstated", 11),
    ("fill_in_version_mismatch", 12),
}
BUILT = (0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13)
# The codes of a step built that no read of a case file of a step done returns yet. Once one does, the test
# fails, and the code leaves this set. Empty since S2b-2's case files. Step 7's `want_mismatch` left it in
# S2a-4's fix round: where no alternative left has a form `want` can give, it is PR-336's
# `want_mismatch_over_alternatives_no_hs`, which S2a-4's code runs (`case_steps.json`); S2b-1's alternatives
# of an interval and a constant under `want: components` (PR-013) return it too. Step 8's `entries_withheld`
# and step 13's `nominal_invalid` left it with S2b-2's case files (PR-052, PR-338).
NO_CASE_YET: set[tuple[str, int]] = set()


def test_the_reads_traced_reach_every_code_the_steps_built_give() -> None:
    """A tracer that saw nothing would find nothing: every code the table gives at a step built is returned,
    constructed at each of those steps, by some read of a case file."""
    seen = {(code, step) for case_file in READS for code, at in traced(case_file) for step in at}
    allowed = {(code, step) for code, (given, _) in TABLE.items() for step in given if step in BUILT}
    assert allowed - NOT_BUILT - NO_CASE_YET - seen == set()
    assert NOT_BUILT | NO_CASE_YET <= allowed
    assert NO_CASE_YET.isdisjoint(seen)
    assert NOT_BUILT.isdisjoint(seen)


def test_a_code_built_but_listed_as_not_built_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """The check above can fail on an entry left in `NOT_BUILT` once its code is built: step 11's
    `outside_range`, which S3b-2 built, listed again."""
    monkeypatch.setattr(sys.modules[__name__], "NOT_BUILT", NOT_BUILT | {("outside_range", 11)})
    with pytest.raises(AssertionError):
        test_the_reads_traced_reach_every_code_the_steps_built_give()


def without(table: Table, code: str, step: int) -> Table:
    given, procedures = table[code]
    return {**table, code: (given - {step}, procedures)}


def adding(table: Table, code: str, step: int) -> Table:
    given, procedures = table[code]
    return {**table, code: (given | {step}, procedures)}


def changed_document(name: str, old: str, new: str) -> Documents:
    """The documents, `name` with `old`, which must be there, replaced by `new`."""
    changed = document(name)
    assert old in changed, old
    changed = changed.replace(old, new, 1)
    return lambda other: changed if other == name else document(other)


@pytest.mark.parametrize(
    ("table", "read_document"),
    [
        pytest.param(without(TABLE, "absent", 7), document, id="a_step_the_table_lacks"),
        pytest.param(adding(TABLE, "withheld", 9), document, id="a_step_the_text_does_not_give"),
        pytest.param(adding(TABLE, "condition_outside", 5), document, id="a_step_with_no_handed_passage"),
        pytest.param(
            TABLE,
            changed_document(
                "read_side_contract.md",
                "(`unit_mismatch`), a condition's",
                "(`unit_mismatch`, `withheld`), a condition's",
            ),
            id="a_code_added_to_a_steps_item",
        ),
        pytest.param(
            {**TABLE, "label_mismatch": (frozenset[int](), frozenset({"scene"}))},
            document,
            id="a_procedure_not_naming_it",
        ),
        pytest.param(
            TABLE,
            changed_document(
                "read_side_contract.md",
                "Under `no_pick` no nominal is",
                "Under no pick no nominal is",
            ),
            id="a_mention_gone",
        ),
        *[
            pytest.param(without(TABLE, code, 6), document, id=f"{code}_not_given_an_overlay")
            for code in ("malformed", "other_version", "hash_mismatch", "pin_mismatch", "unknown_type")
        ],
        pytest.param(
            TABLE,
            changed_document(
                "read_side_contract.md",
                "| `bounds` | `not_met` (`want_mismatch`) |",
                "| `bounds` | `not_met` (`want_mismatch`, `unit_mismatch`) |",
            ),
            id="a_code_added_to_a_passage_handed_to_step_13",
        ),
        pytest.param(
            TABLE,
            changed_document(
                "read_side_contract.md",
                "`unknown` (`condition_unstated`) [PR-305] [PR-323]",
                "`unknown` (`condition_unstated`), or `withheld` [PR-305] [PR-323]",
            ),
            id="a_code_added_to_a_passage_handed_to_step_10",
        ),
    ],
)
def test_the_text_check_can_fail(table: Table, read_document: Documents) -> None:
    with pytest.raises(AssertionError):
        check_text(table, read_document)


SOURCES = {module: (CORE / module).read_text(encoding="utf-8") for module in MODULES}


@pytest.mark.parametrize(
    ("module", "old", "new"),
    [
        pytest.param(
            "resolve.py",
            'return Reason("absent", detail=',
            'return Reason("unknown_type", detail=',
            id="a_code_at_another_step",
        ),
        pytest.param(
            "read.py",
            '        return (Reason("request_incomplete", detail="the request is not an object"),)',
            '        return (Reason("absent"),)',
            id="absent_at_step_0",
        ),
        pytest.param("read.py", "def _member(", "def _members(", id="a_function_no_step_places"),
        pytest.param(
            "read.py",
            '        return (Reason("request_incomplete", detail="the request is not an object"),)',
            '        return (reasons.Reason("absent"),)',
            id="absent_at_step_0_through_the_module",
        ),
        pytest.param(
            "read.py",
            '        return (Reason("request_incomplete", detail="the request is not an object"),)',
            '        return (Reason(code="absent"),)',
            id="absent_at_step_0_by_keyword",
        ),
        pytest.param(
            "read.py",
            '        return (Reason("request_incomplete", detail="the request is not an object"),)',
            "        return (Reason(code),)",
            id="a_code_not_written_out_at_step_0",
        ),
        pytest.param(
            "jsonio.py",
            "def parse(data: bytes)",
            "def read_json(data: bytes)",
            id="a_function_no_step_places_in_another_module",
        ),
        pytest.param(
            "value_shapes.py",
            'return Reason("form_invalid", detail=detail)',
            'return Reason("absent", detail=detail)',
            id="absent_at_step_8",
        ),
    ],
)
def test_the_static_check_can_fail(module: str, old: str, new: str) -> None:
    assert old in SOURCES[module], old
    with pytest.raises(AssertionError):
        check_code(TABLE, {**SOURCES, module: SOURCES[module].replace(old, new, 1)})


def test_the_static_check_reads_a_module_the_core_gains() -> None:
    """A step's new module, which no list names, is read: its reason, in a function no step places, fails."""
    new_module = 'def outside() -> Reason:\n    return Reason("outside_range")\n'
    assert "not_yet_written.py" not in SOURCES
    with pytest.raises(AssertionError, match="at no step this test knows"):
        check_code(TABLE, {**SOURCES, "not_yet_written.py": new_module})
    assert set(MODULES) >= {
        *("read.py", "resolve.py", "record.py", "jsonio.py", "reasons.py"),
        *("fields.py", "value_shapes.py", "conditions.py"),
    }


def test_the_traced_check_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """A step-0 function that gives `absent` beside its own reason: a read of a case whose request it checks
    returns a reason step 0 may not give."""
    want = read_module._want  # pyright: ignore[reportPrivateUsage]  # the function the fault is seeded in

    def faulty(value: JsonValue, claims: Collection[Suite], found: list[Reason]) -> Want | None:
        found.append(Reason("absent"))
        return want(value, claims, found)

    monkeypatch.setattr(read_module, "_want", faulty)
    traced.cache_clear()
    case_file = next(case_file for case_file in READS if case_file.path.name == "PR-308.no_want.json")
    with pytest.raises(AssertionError):
        check_traced(TABLE, case_file)
    traced.cache_clear()
