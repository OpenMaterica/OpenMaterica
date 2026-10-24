# SPDX-License-Identifier: Apache-2.0
"""The build check (`declarations.md`): a consumer's declaration checked against the records.

S7a-1 builds the declaration's own check (section 1). A declaration it refuses gives a report of its refusals
alone, and nothing is read for it. Any other declaration raises `NotImplementedError`, naming what the pieces
still to come read of it, so that no answer is given that a later piece would change (the S7 design's 1.3):
the reads, results and verdict (S7a-2), specimen differences and combinations (S7a-3), watches and trainable
fields (S7a-4), and picks and overlays (S7c).
"""

from collections.abc import Collection
from typing import NoReturn

from materica.core.declarations import CLAIMS, Declaration, DeclarationInput, parse_declaration
from materica.core.jsonio import JsonValue
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from materica.core.report import BuildReport
from materica.shapes import Suite

# The piece that reads each kind of acceptance, of those S7a-1 does not.
_READ_BY = {
    "pick": "S7c",
    "overlay": "S7c",
    "overlay_scope": "S7c",
    "accepted_difference": "S7a-3",
}


def check_build(
    declaration: DeclarationInput, store: RecordStore, *, claims: Collection[Suite] = CLAIMS
) -> BuildReport:
    """Check `declaration` against the records in `store`, as a build that claims `claims`.

    `declaration` is JSON text, a `str` or bytes-like, or a value, read as `read` reads a request. The claims
    are checked first: `ValueError` for claims no implementation makes (a suite not in the README's list, or
    claims without plain read or without the build checks), and `NotImplementedError` for a claim of the scene
    suite, USD read or the sampling suite. A declaration that departs from its shape, or breaks a rule of
    section 1, gives a report of its refusals alone, and nothing is read. Any other raises
    `NotImplementedError` in this version, naming each acceptance and the piece that reads it.
    """
    checked = Declaration.from_json(declaration, claims)
    if isinstance(checked, tuple):
        given: JsonValue | Reason = parse_declaration(declaration)
        return BuildReport(checked, given)
    _not_built(checked)


def _not_built(declaration: Declaration) -> NoReturn:
    """Raise for a declaration that passed its own check: each read, result and verdict is a later piece's."""
    named: dict[str, list[str]] = {}
    for model in declaration.models:
        for acceptance in model.acceptances:
            piece = _READ_BY.get(acceptance.kind, "S7a-2")
            named.setdefault(piece, []).append(
                f"the {acceptance.kind} /models/{model.index}/acceptances/{acceptance.index}"
            )
        for position, _ in enumerate(model.trainable):
            named.setdefault("S7a-4", []).append(
                f"the trainable entry /models/{model.index}/trainable/{position}"
            )
    listed = "; ".join(
        f"{piece} reads {', '.join(acceptances)}" for piece, acceptances in sorted(named.items())
    )
    raise NotImplementedError(
        "the declaration passed its own check, and this version builds nothing past it: S7a-2 reads the "
        "records and gives the results and the verdict, S7a-3 the specimen differences and combinations, "
        "S7a-4 the watches and trainable fields, and S7c applies picks and overlays"
        + (f" ({listed})" if listed else "")
    )
