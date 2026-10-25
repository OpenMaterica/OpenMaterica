# SPDX-License-Identifier: Apache-2.0
"""The build's report (`declarations.md` section 2), and a refusal of the declaration on its own (section 1).

S7a-1 gives a report only for a declaration refused on its own: its refusals, no results, no watches and
nothing unused. `check_build` raises `NotImplementedError` for any other (`core/build.py`), so the members a
report of an accepted declaration adds (the records read, the results, the acceptances unused) come with the
pieces that build them. S7a-2a builds a result as far as its read (`BuildResult`); S7a-2b judges it and gives
the report that holds it.
"""

import copy
from dataclasses import dataclass, field
from typing import cast

from materica import shapes
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult
from materica.core.reasons import Reason


@dataclass(frozen=True)
class BuildResult:
    """A result of the build over records (section 2), as far as its read: the model's name; the record read,
    which over records is the result's location (item 2); the field; and the read's result as the read
    returned it, or None for a field the model reads with no requirement, for which the build reads nothing
    (section 1 item 1). S7a-2b adds the build's own reasons, the status and the judgement."""

    model: str
    record: MaterialRef
    field: str
    read: ReadResult | None


@dataclass(frozen=True)
class BuildRefusal:
    """A refusal of the declaration on its own: `item`, the case of the rule broken; `pointer`, a JSON pointer
    (RFC 6901) into the declaration, at the member at fault, or at the object that should hold a missing one;
    and `detail`, words for people that no case compares, so it takes no part in equality."""

    item: str
    pointer: str
    detail: str | None = field(default=None, compare=False)

    def to_json(self) -> shapes.BuildRefusalJson:
        if self.detail is None:
            return {"item": self.item, "pointer": self.pointer}
        return {"item": self.item, "pointer": self.pointer, "detail": self.detail}


@dataclass(frozen=True)
class BuildReport:
    """The report of a declaration the build refused on its own (section 2).

    `declaration` is the declaration as `jsonio.parse` read its text: the value given, or the reason
    `malformed` where the text is not JSON. The report holds the declaration where the text is JSON, and its
    `consumer` where the declaration declares one, whatever their shape (section 2).
    """

    refusals: tuple[BuildRefusal, ...]
    declaration: JsonValue | Reason

    @property
    def refused(self) -> bool:
        """Whether the build refuses to build: while the report holds a refusal (section 2)."""
        return bool(self.refusals)

    def to_json(self) -> shapes.BuildReport:
        """The report as `build_report.json` gives it. A refused declaration gives no results, no watches and
        nothing unused (section 2); watches are left out, not given empty, until S7a-4 builds them."""
        report: dict[str, object] = {}
        given = self.declaration
        if isinstance(given, dict) and "consumer" in given:
            report["consumer"] = copy.deepcopy(given["consumer"])
        report["records"] = []
        if not isinstance(given, Reason):
            report["declaration"] = copy.deepcopy(given)
        report["refusals"] = [refusal.to_json() for refusal in self.refusals]
        report["results"] = []
        report["unused"] = []
        return cast(shapes.BuildReport, report)
