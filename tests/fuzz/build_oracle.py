# SPDX-License-Identifier: Apache-2.0
"""What `build_bytes.py` holds `check_build` to (the S7 design's 6.4, "Fuzzing"), importable without Atheris
so that `tests/unit/test_fuzz_build_oracle.py` can show each relation failing: the JSON pointer of RFC 6901,
read and resolved, a member put in place at one, and the three relations a check of one declaration keeps.

- `check_build` raises nothing but the `NotImplementedError` it gives a declaration that passed its own check
  (the S7 design's 4.1: what a later piece reads of it);
- every refusal's pointer names a member of the declaration (a missing member's names the object that should
  hold it, which is one);
- every refusal's case is one of the refusal paragraph's (`declarations.md` section 1).
"""

import copy
from collections.abc import Callable

from materica.core.build import check_build
from materica.core.jsonio import JsonValue
from materica.core.record import RecordStore
from materica.core.report import BuildReport

Check = Callable[[JsonValue, RecordStore], BuildReport]

# The cases a declaration's refusal may name: the refusal paragraph's.
CASES = frozenset({"BC-004", "BC-005", "BC-037", "BC-040", "BC-043", "BC-044", "BC-048", "BC-050", "BC-051"})
# How `check_build` words the `NotImplementedError` of a declaration that passed its own check.
NOT_BUILT = "the declaration passed its own check, and this version builds nothing past it"


def tokens_of(pointer: str) -> list[str] | None:
    """A JSON pointer's reference tokens, unescaped (RFC 6901: `~1` as `/`, then `~0` as `~`), or None where
    it is not one: not empty and not starting with `/`, or holding a `~` not followed by `0` or `1`."""
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        return None
    tokens = pointer[1:].split("/")
    for token in tokens:
        if "~" in token.replace("~0", "").replace("~1", ""):
            return None
    return [token.replace("~1", "/").replace("~0", "~") for token in tokens]


def index_of(token: str, length: int) -> int | None:
    """A reference token as an array index (RFC 6901: `0`, or ASCII digits not starting with `0`), below
    `length`."""
    if token == "0" or (token[:1] in "123456789" and token.isascii() and token.isdigit()):
        index = int(token)
        return index if index < length else None
    return None


def resolves(value: JsonValue, pointer: str) -> bool:
    """Whether `pointer` names a member of `value`, its root included."""
    tokens = tokens_of(pointer)
    if tokens is None:
        return False
    for token in tokens:
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and (index := index_of(token, len(value))) is not None:
            value = value[index]
        else:
            return False
    return True


def placed(value: JsonValue, pointer: str, member: JsonValue) -> JsonValue | None:
    """`value` with `member` at `pointer`, not empty: in place of the member it names, or as a new member of
    the object it ends in, or at the end of the list it ends in (`-`, or the list's length); None where it
    names no place."""
    tokens = tokens_of(pointer)
    if not tokens:
        return None
    root = copy.deepcopy(value)
    parent = root
    for token in tokens[:-1]:
        if isinstance(parent, dict) and token in parent:
            parent = parent[token]
        elif isinstance(parent, list) and (index := index_of(token, len(parent))) is not None:
            parent = parent[index]
        else:
            return None
    last = tokens[-1]
    if isinstance(parent, dict):
        parent[last] = member
    elif isinstance(parent, list) and last in ("-", str(len(parent))):
        parent.append(member)
    elif isinstance(parent, list) and (index := index_of(last, len(parent))) is not None:
        parent[index] = member
    else:
        return None
    return root


def check_declaration(declaration: JsonValue, store: RecordStore, check: Check = check_build) -> None:
    """`check` of `declaration` over `store`, `check_build` by default (the target passes the one it imported
    to be instrumented), held to the three relations."""
    try:
        report = check(declaration, store)
    except NotImplementedError as error:
        if not str(error).startswith(NOT_BUILT):
            raise AssertionError(f"NotImplementedError of no piece: {error}") from error
        return
    for refusal in report.refusals:
        assert refusal.item in CASES, f"a refusal of {refusal.item}, which no rule of the declaration's names"
        assert resolves(declaration, refusal.pointer), (
            f"a refusal at {refusal.pointer!r}, which names no member"
        )
