# SPDX-License-Identifier: Apache-2.0
"""The build check (`declarations.md`): a consumer's declaration checked against the records.

S7a-1 builds the declaration's own check (section 1). A declaration it refuses gives a report of its refusals
alone, and nothing is read for it.

S7a-2a builds the reads over records (section 2), `_results`: for each model, each record its `checked_over`
lists, in the order listed, and each field in its `reads`, in that order, one result. A field with no
requirement is read for nothing (section 1 item 1). Any other is read through `read` by the build's own
request (`_request`, item 7), which is given the acceptances of the kinds a read takes, overlays aside, that
name the field and are located at the record (`_given`). The acceptances the read applied are mapped to their
indexes in the model's `acceptances`, each kept only where the result shows it as the build's terms say
(`_applied`). `_stored` gives the label and its basis as stored on the value a result rests on, for the
build's own reasons.

Before any read, a declaration holding what a later piece reads raises `NotImplementedError`, naming each,
so that no answer is given that the later piece would change (the S7 design's 1.3): a pick or an overlay,
which S7c applies; a non-empty `target` or `combinations`, whose specimen differences and combinations S7a-3
gives; and a non-empty `trainable`, which S7a-4 reads. Past the reads, the build's own reasons, the judgement,
the verdict and the report's results are S7a-2b's: `check_build` raises `NotImplementedError` naming it. A
read lets through the `NotImplementedError` it raises itself (a checked record that is an overlay, `want:
fit` on a field holding a fit record).
"""

import copy
from collections.abc import Collection, Sequence
from typing import NoReturn, cast

from materica import shapes
from materica.core.declarations import (
    CLAIMS,
    Acceptance,
    Declaration,
    DeclarationInput,
    ModelEntry,
    Requirement,
    parse_declaration,
)
from materica.core.fields import RecordField, find_field
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult, read
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from materica.core.report import BuildReport, BuildResult
from materica.core.resolve import ResolvedRecord, resolve_record
from materica.core.value_shapes import IMPLIED_BASIS, JsonObject, a_list, an_object
from materica.core.vocabulary import VOCABULARY
from materica.shapes import Suite

# The kinds of acceptance the build gives a read (section 2 item 7): of those a read takes ("A request's
# `acceptances` take only the kinds `pick`, `overlay`, `extrapolation`, `nominal`, `implied_condition` and
# `trainable`", `read_side_contract.md` section 1), overlays aside, which overlays a read is given being
# [not yet covered]; and the `trainable` acceptance is the one the build makes from a `trainable` entry
# (section 7), never a declaration's.
_GIVEN_KINDS = ("pick", "extrapolation", "nominal", "implied_condition")

# The kinds of acceptance a later piece applies, and that piece: the build raises for each before any read.
_APPLIED_LATER = {"pick": "S7c", "overlay": "S7c"}

# The members of a record condition's shapes an implied condition's value holds (section 4.1's row), its
# `basis` aside, which the declaration may give and nothing reads.
_IMPLIED_MEMBERS = ("value", "range", "unit", "token")

# A result as far as its read, beside what S7a-2b judges it with: the indexes, in the model's `acceptances`,
# of those the read applied (`_applied`), and the label and its basis as stored on the value the result rests
# on (`_stored`).
Reading = tuple[BuildResult, tuple[int, ...], JsonObject | None]


def check_build(
    declaration: DeclarationInput, store: RecordStore, *, claims: Collection[Suite] = CLAIMS
) -> BuildReport:
    """Check `declaration` against the records in `store`, as a build that claims `claims`.

    `declaration` is JSON text, a `str` or bytes-like, or a value, read as `read` reads a request. The claims
    are checked first: `ValueError` for claims no implementation makes (a suite not in the README's list, or
    claims without plain read or without the build checks). Where the build claims the scene suite, USD read
    or the sampling suite and the declaration holds a member that suite checks, it raises
    `NotImplementedError`, whatever else is wrong. A declaration that departs from its shape, or breaks a rule
    of section 1, gives a report of its refusals alone, and nothing is read. Any other raises
    `NotImplementedError` in this version: before any read, naming each pick, overlay, `target`,
    `combinations` and `trainable` entry and the piece that reads it; otherwise once its records are read,
    naming S7a-2b, which judges the results and gives the report.
    """
    checked = Declaration.from_json(declaration, claims)
    if isinstance(checked, tuple):
        given: JsonValue | Reason = parse_declaration(declaration)
        return BuildReport(checked, given)
    _not_built(checked)
    _not_judged(_results(checked, store, claims))


def _not_built(declaration: Declaration) -> None:
    """Raise, before any read, for a declaration holding what a later piece reads (the S7 design's 1.3). An
    `overlay_scope` and an accepted difference raise nothing: with no overlay applied and no specimen
    difference (an empty `target` names no fact), neither covers anything."""
    named: dict[str, list[str]] = {}
    for model in declaration.models:
        at = f"/models/{model.index}"
        for acceptance in model.acceptances:
            if (piece := _APPLIED_LATER.get(acceptance.kind)) is not None:
                named.setdefault(piece, []).append(
                    f"the {acceptance.kind} {at}/acceptances/{acceptance.index}"
                )
        if model.target:
            named.setdefault("S7a-3", []).append(f"the target {at}/target")
        if model.combinations:
            named.setdefault("S7a-3", []).append(f"the combinations {at}/combinations")
        for position, _ in enumerate(a_list(model.entry.get("trainable", []))):
            named.setdefault("S7a-4", []).append(f"the trainable entry {at}/trainable/{position}")
    if named:
        listed = "; ".join(f"{piece} reads {', '.join(items)}" for piece, items in sorted(named.items()))
        raise NotImplementedError(
            "the declaration passed its own check, and this version reads none of its records while it "
            f"holds what a later piece reads: {listed}"
        )


def _not_judged(results: Sequence[Reading]) -> NoReturn:
    raise NotImplementedError(
        f"the declaration passed its own check and its {len(results)} results were read; this version builds "
        "nothing past the reads: S7a-2b gives the build's own reasons, the judgement, the verdict and the "
        "report's results"
    )


def _results(declaration: Declaration, store: RecordStore, claims: Collection[Suite]) -> list[Reading]:
    """Section 2: one result per model, record listed in its `checked_over`, in the order listed, and field
    in its `reads`, in that order; none for a record not listed. A field with no requirement is read for
    nothing (section 1 item 1); any other gives the read of the build's own request (item 7)."""
    results: list[Reading] = []
    for model in declaration.models:
        for record in model.records:
            for field in model.reads:
                requirement = _requirement(model, field)
                if requirement is None:
                    results.append((BuildResult(model.name, record, field, None), (), None))
                    continue
                given = _given(model.acceptances, record, field)
                request = _request(declaration.operating_conditions, record, requirement, given)
                result = read(request, store, claims=claims)
                stored = _stored(store, record, field, result, claims)
                results.append(
                    (BuildResult(model.name, record, field, result), _applied(result, given), stored)
                )
    return results


def _requirement(model: ModelEntry, field: str) -> Requirement | None:
    """The model's requirement for `field`, of which there is at most one (section 1), or None."""
    return next((requirement for requirement in model.requirements if requirement.field == field), None)


def _given(acceptances: Sequence[Acceptance], record: MaterialRef, field: str) -> tuple[Acceptance, ...]:
    """Section 2 item 7: the acceptances, in the order the model lists them, of the kinds the build gives a
    read (`_GIVEN_KINDS`), that name the read's field and are located at its record."""
    return tuple(
        acceptance
        for acceptance in acceptances
        if acceptance.kind in _GIVEN_KINDS and acceptance.field == field and _located_at(acceptance, record)
    )


def _located_at(acceptance: Acceptance, record: MaterialRef) -> bool:
    """The build's terms (section 2): an acceptance is located at a result's record when it names that
    record, equal in `id`, `version` and `content_hash`; one located at a region or an interval is located at
    no record."""
    return acceptance.location == record and not {"region", "interval"} & acceptance.members.keys()


def _request(
    operating_conditions: shapes.OperatingConditions,
    record: MaterialRef,
    requirement: Requirement,
    given: Sequence[Acceptance],
) -> shapes.ReadRequest:
    """Section 2 item 7: the build's own read request for the requirement's field at `record`. It holds the
    requirement's `want` and `conditions`, and no other member of the requirement (a read refuses its `label`
    and `review`); the declared operating conditions, each of them, whether or not the requirement names it;
    and the acceptances `given`, each as declared, in that order."""
    return {
        "target": {"record": record.to_json(), "field": requirement.field},
        "operating_conditions": cast(
            dict[str, shapes.OperatingCondition], copy.deepcopy(dict(operating_conditions))
        ),
        "requirement": {
            "want": requirement.want,
            "conditions": cast(dict[str, shapes.RequirementCondition], copy.deepcopy(requirement.conditions)),
        },
        "acceptances": [cast(shapes.Acceptance, copy.deepcopy(acceptance.members)) for acceptance in given],
    }


def _applied(result: ReadResult, given: Sequence[Acceptance]) -> tuple[int, ...]:
    """The indexes, in the model's `acceptances`, of the acceptances given to the read that it applied: those
    the result's `applied` names (by their indexes in the request's `acceptances`, which are `given`'s), each
    kept only where the result shows it, as the build's terms say (section 2)."""
    return tuple(sorted({given[index].index for index in result.applied if _shown(given[index], result)}))


def _shown(acceptance: Acceptance, result: ReadResult) -> bool:
    """The build's terms (section 2): a read applied an implied condition that filled a condition (a
    `conditions` entry whose `record` is the value the implied condition supplies, with basis `implied`), and
    a nominal or an extrapolation that the result's `assumption` names. No other kind given to a read in this
    version is shown applied: a pick raises before any read (S7c)."""
    if acceptance.kind == "implied_condition":
        filled = {entry.name: entry.record for entry in result.conditions or ()}
        implies = an_object(acceptance.members["implies"])
        return any(filled.get(name) == _supplied(an_object(value)) for name, value in implies.items())
    if acceptance.kind in ("nominal", "extrapolation"):
        assumption = cast(JsonObject | None, result.assumption)
        return assumption is not None and all(
            acceptance.members.get(name) == value for name, value in assumption.items()
        )
    return False


def _supplied(implied: JsonObject) -> JsonObject:
    """The condition an implied condition's value fills, as the record would state it with the basis
    `implied` (section 4.1's row)."""
    return {
        **{name: implied[name] for name in _IMPLIED_MEMBERS if name in implied},
        "basis": IMPLIED_BASIS,
    }


def _stored(
    store: RecordStore, record: MaterialRef, field: str, result: ReadResult, claims: Collection[Suite]
) -> JsonObject | None:
    """The `label` and `label_basis`, each where stored, on the value the result rests on (section 2 item 8):
    the field, or the alternative read (`ReadResult.resting_on`), read from the record as stored in `store`,
    never from the result, whose labels a read that ends before step 12 leaves out; None where the result
    rests on no stored value."""
    if result.resting_on is None:
        return None
    resolved = resolve_record(record, store, claims)
    assert isinstance(resolved, ResolvedRecord), "a result resting on a stored value resolved its record"
    found = find_field(resolved.record.value, VOCABULARY.fields[field])
    assert isinstance(found, RecordField), "a result resting on a stored value found its field"
    value = found.value
    for index in result.resting_on:
        value = a_list(an_object(value)["alternatives"])[index]
    held = value if isinstance(value, dict) else {}
    return {name: copy.deepcopy(held[name]) for name in ("label", "label_basis") if name in held}
