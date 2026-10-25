# SPDX-License-Identifier: Apache-2.0
"""The reason table and the reasons the core's source constructs, for `test_reason_steps.py` and
`test_build_reasons.py`. Importing it lists no directory, so that a trace of what each test lists names the
test that does (`tests/unit/test_pre_review.py`)."""

import ast
import json
from collections.abc import Iterator
from pathlib import Path

from materica.core import read as read_module
from tests.spec_sync.schemas import SCHEMA

# Each code, and the steps of section 3 that give it or the procedures that give one no step gives.
Table = dict[str, tuple[frozenset[int], frozenset[str]]]
CORE = Path(read_module.__file__).parent


def reason_table() -> Table:
    reasons = json.loads((SCHEMA / "vocabulary" / "reasons.json").read_text(encoding="utf-8"))["reasons"]
    return {
        code: (frozenset(int(step) for step in row.get("steps", [])), frozenset(row.get("procedures", [])))
        for code, row in reasons.items()
    }


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
