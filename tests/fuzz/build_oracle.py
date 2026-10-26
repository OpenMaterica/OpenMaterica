# SPDX-License-Identifier: Apache-2.0
"""What `build_bytes.py` holds `check_build` to (the S7 design's 6.4, "Fuzzing"), importable without Atheris
so that `tests/unit/test_fuzz_build_oracle.py` can show each relation failing: the JSON pointer of RFC 6901,
read and resolved, a member put in place at one, and the four relations a check of one declaration keeps.

- `check_build` raises nothing but a `NotImplementedError` of what this version does not build past the
  declaration's own check (`NOT_BUILT`: the S7 design's 4.1, and what the later pieces read);
- every refusal's pointer names a member of the declaration (a missing member's names the object that should
  hold it, which is one);
- every refusal's case is one of the refusal paragraph's (`declarations.md` section 1);
- where the build's reference model (`tests/reference/build_model.py`) gives a verdict, the check gives
  exactly its refusals, but where the two differ as a known divergence says (`KNOWN_DIVERGENCES`, empty now,
  each an open point when it is not): a declaration it refuses with every rule's refusals placed, and one it
  takes, which passes its own check (`TAKEN`), where the check refuses nothing. Where the model does not
  place some rule's refusals (`Refused.unplaced`, or a `NoVerdict` naming such a rule), the check is held to
  the first three alone.
"""

import copy
import json
from collections.abc import Callable, Mapping

from materica.core.build import check_build
from materica.core.jsonio import JsonValue
from materica.core.record import RecordStore
from materica.core.report import BuildReport
from tests.reference import build_model
from tests.reference.direct import BUILD
from tests.reference.read_model import NoVerdict

Check = Callable[[JsonValue, RecordStore], BuildReport]
Model = Callable[[bytes, frozenset[str]], build_model.Refused | NoVerdict]
Refusals = frozenset[tuple[str, str]]

# The cases a declaration's refusal may name: the refusal paragraph's.
CASES = frozenset({"BC-004", "BC-005", "BC-037", "BC-040", "BC-043", "BC-044", "BC-048", "BC-050", "BC-051"})

# What `check_build` raises `NotImplementedError` for past the declaration's own check, by the words each
# begins with, and the piece that builds it: the S7 design's 4.1 (a pick or an overlay, a checked record that
# is an overlay, `want: fit` on a fit record), and what a later piece reads (a `target` or `combinations` and
# a `trainable` entry, which the build raises for with the picks and overlays, and a label's trust).
NOT_BUILT: Mapping[str, str] = {
    "the declaration passed its own check, and this version reads none of its records while it holds what a "
    "later piece reads": "S7c, S7a-3 and S7a-4",
    "a read whose target is an overlay is not built yet": "S4c-1",
    "want: fit on a field holding a fit record is not read yet": "the fits and reference data suite",
    "the waiver /acceptances/": "S7a-2's label trust",
}

# The model's words for a declaration that passes its own check (`DeclarationCheck.verdict`): no fault found
# and none left unplaced, the build going on past the declaration, or to a pick or an overlay. The check must
# then refuse nothing, as a refusal there is one the model does not give.
TAKEN = frozenset({build_model.PAST_THE_DECLARATION, "a pick or an overlay acceptance (S7c)"})


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


def member_at(value: JsonValue, pointer: str) -> tuple[JsonValue] | None:
    """The member `pointer` names in `value`, its root included, alone in a tuple; None where it names
    none."""
    tokens = tokens_of(pointer)
    if tokens is None:
        return None
    for token in tokens:
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and (index := index_of(token, len(value))) is not None:
            value = value[index]
        else:
            return None
    return (value,)


def resolves(value: JsonValue, pointer: str) -> bool:
    """Whether `pointer` names a member of `value`, its root included."""
    return member_at(value, pointer) is not None


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


# The known divergences of the check from the model, each an open point: each, given the declaration and the
# refusals of each side, names those it explains of the refusals one side gives and the other does not, and
# the relation fails on any left unexplained. The mapping is empty: the thirteen the target's runs found are
# fixed on `main` (the model's, then the check's), and a divergence found since is listed here only with its
# open point, an `Explains` function named for it and an example in `tests/unit/test_fuzz_build_oracle.py`
# that passes with it listed and fails without it (`tests/fuzz/README.md`, "The relation to the model").

Refusal = tuple[str, str]
Explains = Callable[[JsonValue, Refusals, Refusals], set[Refusal]]

KNOWN_DIVERGENCES: Mapping[str, Explains] = {}


def check_declaration(
    declaration: JsonValue,
    store: RecordStore,
    check: Check = check_build,
    model: Model = build_model.check_build,
) -> None:
    """`check` of `declaration` over `store`, `check_build` by default (the target passes the one it imported
    to be instrumented), held to the four relations: the model's as `model` gives it, the build's reference
    model by default, of the JSON text `json.dumps` writes of `declaration` (which `check_build` reads too),
    under the claims of plain read and the build checks, which hold no suite item 12 names, as `check_build`'s
    own claims do not."""
    try:
        report = check(declaration, store)
    except NotImplementedError as error:
        if not str(error).startswith(tuple(NOT_BUILT)):
            raise AssertionError(f"NotImplementedError of no piece: {error}") from error
        found: Refusals = frozenset()
    else:
        for refusal in report.refusals:
            assert refusal.item in CASES, (
                f"a refusal of {refusal.item}, which no rule of the declaration's names"
            )
            assert resolves(declaration, refusal.pointer), (
                f"a refusal at {refusal.pointer!r}, which names no member"
            )
        found = frozenset((refusal.item, refusal.pointer) for refusal in report.refusals)
    verdict = model(json.dumps(declaration).encode(), BUILD)
    wanted: Refusals
    if isinstance(verdict, build_model.Refused) and not verdict.unplaced:
        wanted = frozenset((refusal.item, refusal.pointer) for refusal in verdict.refusals)
    elif isinstance(verdict, NoVerdict) and verdict.why in TAKEN:
        wanted = frozenset()
    else:
        return
    explained: set[Refusal] = set()
    for explains in KNOWN_DIVERGENCES.values():
        explained |= explains(declaration, found, wanted)
    check_alone, model_alone = found - wanted - explained, wanted - found - explained
    if check_alone or model_alone:
        raise AssertionError(
            f"the implementation gives {sorted(check_alone)}, the model {sorted(model_alone)}"
        )
