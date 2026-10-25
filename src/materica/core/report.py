# SPDX-License-Identifier: Apache-2.0
"""The build's report (`declarations.md` section 2), and a refusal of the declaration on its own (section 1).

A declaration refused on its own gives a report of its refusals alone: no results, no watches and nothing
unused (S7a-1). One that passes gives the records a read resolved, one `BuildResult` per model, record listed
and field read, and the acceptances no result used (S7a-2): each result holds its read, the build's own
reasons joined to the read's, the worst status of them all, and the verdict, `accepted`, `accepted_by` and
`not_accepted`. The report leaves out what a later piece builds: `watches`, which S7a-4 emits, raises
`NotImplementedError` and is left out of the JSON rather than given empty (the S7 design's 1.3 and 9);
specimen differences and combinations, S7a-3's, are never given here, since a declaration that names a
`target` or `combinations` raises before any read (`core/build.py`). `status_lines` prints the report for
people, each reason nothing covers beside what would cover it, from section 4.2's table (`coverage.json`).
"""

import copy
import dataclasses
from dataclasses import dataclass
from typing import NoReturn, cast

from materica import shapes
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult
from materica.core.reasons import Reason
from materica.core.status import ReadStatus
from materica.core.value_shapes import JsonObject
from materica.core.vocabulary import VOCABULARY


@dataclass(frozen=True)
class BuildResult:
    """A result of the build over records (section 2): the model's name; the record read, which over records
    is the result's location (item 2); the field; the read's result as the read returned it, or None for a
    field the model reads with no requirement, for which the build reads nothing (section 1 item 1); the
    reasons, the read's with the build's own joined, and the status, the worst of them all (item 8); and the
    verdict (item 4): `accepted`, `accepted_by`, the indexes in the model's `acceptances` of every acceptance
    used for it, and `not_accepted`, each reason nothing covers. `specimen_differences` and `trainable_by`
    are S7a-3's and S7a-4's, empty and None here.

    `value` is the value to use as the field's; `end_value` and `initial_value` hold the read's value where it
    is not the value at the operating conditions (the S7 design's 4.2). `unit`, `labels`, `conditions`,
    `provenance` and `assumption` read the read's result."""

    model: str
    record: MaterialRef
    field: str
    read: ReadResult | None
    reasons: tuple[Reason, ...]
    status: ReadStatus
    accepted: bool
    accepted_by: tuple[int, ...]
    not_accepted: tuple[Reason, ...]
    specimen_differences: tuple[shapes.SpecimenDifference, ...] = dataclasses.field(default=(), kw_only=True)
    trainable_by: int | None = dataclasses.field(default=None, kw_only=True)

    @property
    def value(self) -> JsonValue:
        """The read's value, where the result is accepted, the field is not trainable and the value is the one
        at the operating conditions: the record's, or the consumer's declared nominal, which `assumption`
        names. None under an extrapolation (`end_value`), on a trainable field (`initial_value`), on a result
        not accepted, and where no value was read."""
        if self.trainable_by is not None or self._extrapolated:
            return None
        return self._accepted_value()

    @property
    def end_value(self) -> JsonValue:
        """Under an extrapolation the `assumption` names, on an accepted result: the read's value, the value
        at the readable range's nearest end. The extrapolated value is the consumer's to compute, by the
        method the `assumption` holds (`declarations.md` section 4.1). None otherwise."""
        return self._accepted_value() if self._extrapolated else None

    @property
    def initial_value(self) -> JsonValue:
        """On an accepted result of a trainable field: the record's value, which the consumer uses only as the
        initial value of its fit (section 7). None otherwise."""
        return self._accepted_value() if self.trainable_by is not None else None

    @property
    def unit(self) -> JsonValue:
        return None if self.read is None else copy.deepcopy(self.read.unit)

    @property
    def labels(self) -> tuple[str, ...]:
        return () if self.read is None else self.read.labels

    @property
    def conditions(self) -> list[shapes.ConditionEntry] | None:
        if self.read is None or self.read.conditions is None:
            return None
        return cast(list[shapes.ConditionEntry], [entry.to_json() for entry in self.read.conditions])

    @property
    def provenance(self) -> shapes.ResultProvenance | None:
        if self.read is None or self.read.provenance is None:
            return None
        return self.read.provenance.to_json()

    @property
    def assumption(self) -> shapes.Assumption | None:
        if self.read is None or self.read.assumption is None:
            return None
        return copy.deepcopy(self.read.assumption)

    @property
    def _extrapolated(self) -> bool:
        assumption = cast(JsonObject | None, self.assumption)
        return assumption is not None and assumption.get("acceptance") == "extrapolation"

    def _accepted_value(self) -> JsonValue:
        if not self.accepted or self.read is None:
            return None
        return copy.deepcopy(self.read.value)

    def to_json(self) -> shapes.BuildResultJson:
        """The result as `build_report.json` gives it: the read's members as the read returned them, none for
        a field read with no requirement; the build's reasons and status in place of the read's; and the
        build's members."""
        members: dict[str, object] = {
            "model": self.model,
            "record": self.record.to_json(),
            "field": self.field,
        }
        if self.read is not None:
            members.update(self.read.to_json())
        members["status"] = self.status
        members["reasons"] = [reason.to_json() for reason in self.reasons]
        members["specimen_differences"] = [copy.deepcopy(found) for found in self.specimen_differences]
        members["accepted"] = self.accepted
        members["accepted_by"] = list(self.accepted_by)
        if self.trainable_by is not None:
            members["trainable_by"] = self.trainable_by
        members["not_accepted"] = [reason.to_json() for reason in self.not_accepted]
        return cast(shapes.BuildResultJson, members)


@dataclass(frozen=True)
class UnusedAcceptance:
    """An acceptance no result of its model used (section 2 item 9): the model's name, and the acceptance's
    index in the model's `acceptances`."""

    model: str
    acceptance: int

    def to_json(self) -> shapes.UnusedAcceptance:
        return {"model": self.model, "acceptance": self.acceptance}


@dataclass(frozen=True)
class BuildRefusal:
    """A refusal of the declaration on its own: `item`, the case of the rule broken; `pointer`, a JSON pointer
    (RFC 6901) into the declaration, at the member at fault, or at the object that should hold a missing one;
    and `detail`, words for people that no case compares, so it takes no part in equality."""

    item: str
    pointer: str
    detail: str | None = dataclasses.field(default=None, compare=False)

    def to_json(self) -> shapes.BuildRefusalJson:
        if self.detail is None:
            return {"item": self.item, "pointer": self.pointer}
        return {"item": self.item, "pointer": self.pointer, "detail": self.detail}


@dataclass(frozen=True)
class BuildReport:
    """The build's report (section 2).

    `declaration` is the declaration as `jsonio.parse` read its text: the value given, or the reason
    `malformed` where the text is not JSON. The report holds the declaration where the text is JSON, and its
    `consumer` where the declaration declares one, whatever their shape. A declaration refused on its own
    gives its `refusals` and no records, results or unused acceptances; one that passes gives no refusal.
    """

    refusals: tuple[BuildRefusal, ...]
    declaration: JsonValue | Reason
    records: tuple[MaterialRef, ...] = ()
    results: tuple[BuildResult, ...] = ()
    unused: tuple[UnusedAcceptance, ...] = ()

    @property
    def consumer(self) -> JsonValue:
        """The declaration's `consumer`, as given, or None where it declares none."""
        given = self.declaration
        return copy.deepcopy(given.get("consumer")) if isinstance(given, dict) else None

    @property
    def refused(self) -> bool:
        """Whether the build refuses to build: while the report holds a refusal, or a result that is not
        accepted (section 2 item 5)."""
        return bool(self.refusals) or not all(result.accepted for result in self.results)

    @property
    def watches(self) -> NoReturn:
        """The run-time watches (section 8), which S7a-4 emits: until then this raises, and the JSON report
        leaves the member out rather than give it empty (the S7 design's 1.3)."""
        raise NotImplementedError("the build's watches (declarations.md section 8) are S7a-4's")

    def result(self, model: str, field: str, record: MaterialRef) -> BuildResult:
        """The result of `model` for `field` at `record`; `KeyError` where there is none."""
        for result in self.results:
            if (result.model, result.field, result.record) == (model, field, record):
                return result
        raise KeyError((model, field, record))

    def to_json(self) -> shapes.BuildReport:
        """The report as `build_report.json` gives it. Watches are left out, not given empty, until S7a-4
        builds them."""
        report: dict[str, object] = {}
        given = self.declaration
        if isinstance(given, dict) and "consumer" in given:
            report["consumer"] = copy.deepcopy(given["consumer"])
        report["records"] = [record.to_json() for record in self.records]
        if not isinstance(given, Reason):
            report["declaration"] = copy.deepcopy(given)
        report["refusals"] = [refusal.to_json() for refusal in self.refusals]
        report["results"] = [result.to_json() for result in self.results]
        report["unused"] = [unused.to_json() for unused in self.unused]
        return cast(shapes.BuildReport, report)

    def status_lines(self) -> tuple[str, ...]:
        """The report for people, as `materica status` prints it (the S7 design's 4.5): the verdict; each
        refusal; each result, `ok` where accepted, with what accepted it, or `x`, with each reason nothing
        covers beside what would cover it by section 4.2's table, read from `coverage.json`; and the
        acceptances unused. The format is the package's, not the specification's: no case compares it."""
        if self.refusals:
            counted = _counted(len(self.refusals), "refusal")
            return (
                f"build refused: the declaration's own check refused it, {counted}",
                *(
                    f"{_RESULT}{refusal.item}  {refusal.pointer or '(the declaration)'}"
                    for refusal in self.refusals
                ),
            )
        accepted = sum(result.accepted for result in self.results)
        counted = _counted(len(self.results), "result")
        if accepted == len(self.results):
            verdict = f"build accepted: {counted}, each accepted"
        else:
            verdict = f"build refused: {len(self.results) - accepted} of {counted} not accepted"
        lines = [f"{verdict}; the declaration's own check passed"]
        for result in self.results:
            lines += _result_lines(result, self._acceptances(result.model))
        unused = ", ".join(
            f"{found.model} #{found.acceptance} ({_described(self._acceptances(found.model)[index])})"
            for found in self.unused
            for index in (found.acceptance,)
        )
        lines.append(f"{_RESULT}unused: {unused or 'none'}")
        return tuple(lines)

    def _acceptances(self, model: str) -> list[JsonObject]:
        """The acceptances of the model named `model`, as declared."""
        models = cast(list[JsonObject], cast(JsonObject, self.declaration)["models"])
        entry = next(entry for entry in models if cast(JsonObject, entry["model"])["name"] == model)
        return cast(list[JsonObject], entry.get("acceptances", []))


# A result's line, indented under the verdict; a reason's below it, indented further.
_RESULT, _BELOW = "  ", "        "


def _result_lines(result: BuildResult, acceptances: list[JsonObject]) -> list[str]:
    where = f"{result.model}  {result.record.id} {result.record.version}  {result.field}  {result.status}"
    if not result.accepted:
        return [
            f"{_RESULT}x   {where}",
            *(f"{_BELOW}{_covered_by(reason)}" for reason in result.not_accepted),
        ]
    used = ", ".join(f"#{index} ({_described(acceptances[index])})" for index in result.accepted_by)
    # A value accepted under a waiver of `not_reviewed` is "accepted unreviewed" (the S7 design's 4.4).
    accepted = (
        "accepted unreviewed"
        if any(reason.code == "not_reviewed" for reason in result.reasons)
        else "accepted"
    )
    line = f"{_RESULT}ok  {where}" + (f", {accepted} by {used}" if used else "")
    if result.end_value is not None:
        line += (
            f": end value {_shown(result.end_value)} {_shown(result.unit)}, at the readable range's nearest "
            "end; the value at the operating conditions is yours to compute"
        )
    return [line]


def _covered_by(reason: Reason) -> str:
    """A reason nothing covers, beside what would cover it by the rows of section 4.2 that list it, or that
    nothing would, for a reason no row lists."""
    rows = [row for row in VOCABULARY.coverage if reason.code in row.reasons]
    if not rows:
        return f"{_named(reason)}: nothing covers it (declarations.md 4.2)"
    covering = "; or ".join(row.covered_by.replace("`", "") for row in rows)
    return f"{_named(reason)}: covered by {covering} (declarations.md 4.2), and nothing declared covers it"


def _named(reason: Reason) -> str:
    named = reason.code if reason.condition is None else f"{reason.code}({reason.condition})"
    return named if reason.alternative is None else f"{named} in alternative {reason.alternative}"


def _described(acceptance: JsonObject) -> str:
    """An acceptance by its kind and the members that say what it accepts."""
    kind = str(acceptance["acceptance"])
    if kind == "waiver":
        code = str(acceptance["code"])
        return (
            f"waiver: {code}({acceptance['condition']})" if "condition" in acceptance else f"waiver: {code}"
        )
    if kind == "nominal":
        return f"nominal {_shown(acceptance.get('value', acceptance.get('params')))}"
    if kind == "extrapolation":
        return f"extrapolation, method {acceptance['method']}"
    if kind == "implied_condition":
        return f"implied condition: {acceptance['fact']} {acceptance['token']}"
    return kind.replace("_", " ")


def _shown(value: JsonValue) -> str:
    return repr(value) if isinstance(value, float) else str(value)


def _counted(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
