# SPDX-License-Identifier: Apache-2.0
"""Mutants of the declaration's own check (`core/declarations.py`), each with one fault, and the part of HP41
or HP42 (`test_declaration_properties.py`) that must kill it: the S7 design's mutants of HP41 and HP42 (its
section 6.4), and those the reviews of S7a-1b and S7a-1m left to these properties (the rules the build's
reference model's listed survivors and the review's hand mutants name). As in the other mutant modules, each
must die within the examples the `ci` profile gives a property, at both sizes, at an example of a way it
names, and at the assertion it names, and records the examples its kill took as `examples_to_kill`.

A fault is injected where the check looks a name up when it runs: a module-level function or table of
`declarations`, each rule's function (`_shape`, `_tokens`, `_names`, `_reasons`, `_locations`, `_labels`,
`_suites`), the precedence (`_precedence`), and the helpers they call (`_holds`, `_suite_members`, `_join`,
`TOKENS`, `_in_unit_interval`).
"""

import copy
import dataclasses
import re
from collections.abc import Callable, Collection
from typing import Any, NamedTuple, cast

import pytest
from hypothesis import strategies as st

from materica.core import declarations
from materica.core.declarations import Finding, Holds, JsonObject, Member
from materica.core.jsonio import JsonValue
from materica.core.report import BuildRefusal
from materica.core.slips import one_slip
from materica.core.vocabulary import VOCABULARY
from materica.shapes import Suite
from tests.property import declaration_strategies as strategies
from tests.property import test_declaration_properties as properties
from tests.property.declaration_strategies import Drawn
from tests.property.strategies import ORIGINAL, SMALL, Size
from tests.property.test_condition_mutants import kill

# Each property part that kills a mutant, by name: its examples at a size over a stratum of its ways, its
# strata (each a test of `test_declaration_properties.py`), and its check.
Examples = Callable[[Size, tuple[str, ...]], st.SearchStrategy[Drawn]]


def part_of(part: str) -> Examples:
    return lambda size, ways: strategies.hp41(part, size, ways)


KILLERS: dict[str, tuple[Examples, tuple[tuple[str, ...], ...], Callable[[Drawn], None]]] = {
    **{
        f"HP41 {part}": (part_of(part), strategies.STRATA[part], properties.check_declaration)
        for part in strategies.PARTS
    },
    "HP41 every_fault": (
        lambda size, _: strategies.every_fault(size),
        (("every_fault",),),
        properties.check_declaration,
    ),
    "HP42": (
        lambda size, ways: strategies.hp42(size, ways),
        strategies.HP42_STRATA,
        properties.check_unbuilt,
    ),
}


class Mutant(NamedTuple):
    name: str
    function: str  # the name in `declarations` the fault replaces
    killer: str  # a key of KILLERS
    inject: Callable[[pytest.MonkeyPatch], None]
    dies_at: tuple[str, ...]  # the ways, one of which the example that kills it must show
    says: str  # a pattern the message of the assertion that kills it must match: what the fault changes
    fault: str  # the fault, in words


def stratum(mutant: Mutant) -> tuple[str, ...]:
    """The stratum of its killer's ways holding every way the mutant names: the test whose draws kill it."""
    return next(ways for ways in KILLERS[mutant.killer][1] if set(mutant.dies_at) <= set(ways))


def replacing(name: str, value: object) -> Callable[[pytest.MonkeyPatch], None]:
    return lambda monkeypatch: monkeypatch.setattr(declarations, name, value)


# The functions and tables the faults wrap, taken before any replaces them.
SHAPE = declarations._shape  # pyright: ignore[reportPrivateUsage]
HOLDS = declarations._holds  # pyright: ignore[reportPrivateUsage]
TOKENS = declarations._tokens  # pyright: ignore[reportPrivateUsage]
NAMES = declarations._names  # pyright: ignore[reportPrivateUsage]
REASONS = declarations._reasons  # pyright: ignore[reportPrivateUsage]
LOCATIONS = declarations._locations  # pyright: ignore[reportPrivateUsage]
LABELS = declarations._labels  # pyright: ignore[reportPrivateUsage]
SUITES = declarations._suites  # pyright: ignore[reportPrivateUsage]
PRECEDENCE = declarations._precedence  # pyright: ignore[reportPrivateUsage]
SUITE_MEMBERS = declarations._suite_members  # pyright: ignore[reportPrivateUsage]
JOIN = declarations._join  # pyright: ignore[reportPrivateUsage]
PLACES = declarations._places  # pyright: ignore[reportPrivateUsage]
ENTRIES = declarations._entries  # pyright: ignore[reportPrivateUsage]
KIND_TOKENS = declarations._kind_tokens  # pyright: ignore[reportPrivateUsage]
NOT_BUILT = declarations._NOT_BUILT  # pyright: ignore[reportPrivateUsage]
TOKEN_LISTS = declarations.TOKENS
ORDER = declarations.ORDER


def at(declaration: JsonValue, pointer: str) -> JsonValue:
    """The value a JSON pointer (RFC 6901) names in `declaration`."""
    found = declaration
    for token in pointer.split("/")[1:]:
        name = token.replace("~1", "/").replace("~0", "~")
        found = found[int(name)] if isinstance(found, list) else cast(JsonObject, found)[name]
    return found


def kind_at(declaration: JsonObject, pointer: str) -> JsonValue:
    held = at(declaration, pointer)
    return held.get("acceptance") if isinstance(held, dict) else None


def dropping(
    function: Callable[..., list[Finding]], unwanted: Callable[[Finding, JsonObject], bool]
) -> Callable[..., list[Finding]]:
    """`function`, a rule, without the findings `unwanted` names (given each finding and the declaration)."""

    def faulty(declaration: JsonObject, *rest: Any) -> list[Finding]:
        return [finding for finding in function(declaration, *rest) if not unwanted(finding, declaration)]

    return faulty


def detail_says(*words: str) -> Callable[[Finding, JsonObject], bool]:
    return lambda finding, _: any(word in finding.detail for word in words)


def holds_dropping(*words: str, ending: str = "") -> Callable[[Holds, JsonValue, str], list[Finding]]:
    """`_holds` without the findings whose words hold one of `words`, at a pointer ending with `ending`."""

    def faulty(holds: Holds, value: JsonValue, pointer: str) -> list[Finding]:
        found = HOLDS(holds, value, pointer)
        return [
            finding
            for finding in found
            if not (any(word in finding.detail for word in words) and finding.pointer.endswith(ending))
        ]

    return faulty


def tokens_without(*places: tuple[str, str]) -> Callable[[pytest.MonkeyPatch], None]:
    lists = {key: tokens for key, tokens in TOKEN_LISTS.items() if key not in places}
    return replacing("TOKENS", lists)


class Folded(tuple[str, ...]):
    """A token list compared without case."""

    def __contains__(self, value: object) -> bool:
        return isinstance(value, str) and value.casefold() in {token.casefold() for token in self}


# `_reasons`.


def _accept_reason_unchecked(finding: Finding, declaration: JsonObject) -> bool:
    """Item 3 for a tolerance alone: an accept list without its reason left to the shape table."""
    held = at(declaration, finding.pointer)
    return finding.case == "BC-004" and isinstance(held, dict) and "tolerance" not in held


def _reason_checked_on_waivers_only(finding: Finding, declaration: JsonObject) -> bool:
    return (
        finding.case == "BC-005"
        and finding.aspect == "reason"
        and kind_at(declaration, finding.pointer) != "waiver"
    )


def _basis_checked_on_nominals_only(finding: Finding, declaration: JsonObject) -> bool:
    return (
        finding.case == "BC-005"
        and finding.aspect == "basis"
        and kind_at(declaration, finding.pointer) != "nominal"
    )


def _basis_required_of_a_waiver(declaration: JsonObject) -> list[Finding]:
    found = REASONS(declaration)
    for visit in PLACES(declaration):
        if visit.place == "waiver" and "basis" not in visit.value:
            found.append(Finding("BC-005", visit.pointer, "a waiver without its basis", "basis"))
    return found


def _blank_reason_refused(declaration: JsonObject) -> list[Finding]:
    """A `reason` or `basis` of white space alone refused, which the text takes ("a string of at least one
    character")."""
    found = REASONS(declaration)
    for visit in PLACES(declaration):
        for member in ("reason", "basis"):
            held = visit.value.get(member)
            if isinstance(held, str) and held and not held.strip():
                found.append(Finding("BC-048", f"{visit.pointer}/{member}", "white space alone"))
    return found


def _empty_condition_reason_as_item_3(declaration: JsonObject) -> list[Finding]:
    """An empty `reason` of a requirement condition refused by item 3, at the condition, where the text gives
    its row's Holds (BC-048, at the `reason`)."""
    found: list[Finding] = []
    for finding in REASONS(declaration):
        parent = finding.pointer.rpartition("/")[0]
        if finding.case == "BC-048" and finding.pointer.endswith("/reason") and "/conditions/" in parent:
            found.append(Finding("BC-004", parent, "an empty reason", "reason"))
        else:
            found.append(finding)
    return found


# `_locations`.


def _accepted_difference_location_required(declaration: JsonObject) -> list[Finding]:
    found = LOCATIONS(declaration)
    for visit in PLACES(declaration):
        if visit.place == "accepted_difference" and not {"record", "region", "interval"} & visit.value.keys():
            found.append(
                Finding("BC-037", visit.pointer, "an accepted difference naming no location", "location")
            )
    return found


# `_shape` and `_holds`.


def _plural_slip(finding: Finding, _: JsonObject) -> bool:
    """A member one slip from a named one by a plural or a singular, taken as that member."""
    named = re.search(r"'([^']*)' is not a member here, one slip from '([^']*)'", finding.detail)
    return named is not None and one_slip(named.group(1), named.group(2)) == "singular or plural"


def _difference_of_any_refused(declaration: JsonObject) -> list[Finding]:
    found = SHAPE(declaration)
    for visit in PLACES(declaration):
        if visit.place == "accepted_difference" and visit.value.get("value") == "any":
            found.append(Finding("BC-048", f"{visit.pointer}/value", '"any" refused'))
    return found


def _difference_judged_beside_its_fact_at_fault(declaration: JsonObject) -> list[Finding]:
    """An accepted difference's `value`, an object holding no `status`, refused as of no fact's shape where
    its `fact` is at fault, beside the `fact`'s own refusal."""
    found = SHAPE(declaration)
    for visit in PLACES(declaration):
        value, fact = visit.value.get("value"), visit.value.get("fact")
        if visit.place == "accepted_difference" and isinstance(value, dict) and "status" not in value:
            if fact not in VOCABULARY.facts:
                found.append(Finding("BC-048", f"{visit.pointer}/value", "of no fact's shape"))
    return found


def _boolean_taken(holds: Holds, value: JsonValue, pointer: str) -> list[Finding]:
    """A boolean taken wherever the table asks for a value of a type, a number among them."""
    return [] if isinstance(value, bool) else HOLDS(holds, value, pointer)


def _basis_of_another_kind(finding: Finding, _: JsonObject) -> bool:
    """A `basis` on an acceptance of a kind other than item 4's three taken, as if every kind named it."""
    return (
        "/acceptances/" in finding.pointer
        and finding.pointer.endswith("/basis")
        and "is not a member here" in finding.detail
    )


def _in_a_chain(finding: Finding, _: JsonObject) -> bool:
    return "/chains/" in finding.pointer


def _in_a_model_member(finding: Finding, _: JsonObject) -> bool:
    return re.fullmatch(r"/models/[0-9]+/model(/.*)?", finding.pointer) is not None


# An acceptance of no known kind judged by the members some kind names, each by the last kind that names it
# and none required but its kind: the check before the refusal paragraph had an acceptance that names no
# known kind refused at itself alone.
_EVERY_KIND = {
    member.name: Member(member.name, "yes" if member.name == "acceptance" else "rule", member.holds)
    for kind in declarations.KINDS
    for member in declarations.SHAPE[kind]
}


# `_names`.


def _fields_judged_against_an_empty_reads(declaration: JsonObject) -> list[Finding]:
    """A requirement's and a `trainable` entry's `field` judged against an empty `reads`, a `reads` itself at
    fault, where the refusal paragraph has that rule stand aside."""
    found = NAMES(declaration)
    for index, model in ENTRIES(declaration, "models"):
        if model.get("reads") != []:
            continue
        for member in ("requirements", "trainable"):
            for position, entry in ENTRIES(model, member):
                if isinstance(entry.get("field"), str):
                    at = f"/models/{index}/{member}/{position}/field"
                    found.append(Finding("BC-048", at, "not in an empty reads"))
    return found


def _trainable_twice_by_field(declaration: JsonObject) -> list[Finding]:
    """Two `trainable` entries for one field refused wherever each is located, where the text refuses two "for
    one field at one location"."""
    found = NAMES(declaration)
    for index, model in ENTRIES(declaration, "models"):
        fields: set[str] = set()
        for position, entry in ENTRIES(model, "trainable"):
            field = entry.get("field")
            if isinstance(field, str):
                if field in fields:
                    found.append(Finding("BC-048", f"/models/{index}/trainable/{position}", "a field twice"))
                fields.add(field)
    return found


# `_labels`.


def _label_waiver_taken_without_review(declaration: JsonObject) -> list[Finding]:
    """Item 4 holding a label-resting waiver to its requirement's `label` alone, not its `review`."""
    found: list[Finding] = []
    for index, model in ENTRIES(declaration, "models"):
        requirements: dict[str, JsonObject] = {}
        for _, requirement in ENTRIES(model, "requirements"):
            if isinstance(requirement.get("field"), str):
                requirements.setdefault(cast(str, requirement["field"]), requirement)
        for position, waiver in ENTRIES(model, "acceptances"):
            if waiver.get("acceptance") != "waiver" or "label" not in waiver:
                continue
            field = waiver.get("field")
            requirement = requirements.get(field, {}) if isinstance(field, str) else {}
            if requirement.get("label") != waiver["label"]:
                found.append(Finding("BC-050", f"/models/{index}/acceptances/{position}/label", "unreviewed"))
    return found


def _null_label_judged(declaration: JsonObject) -> list[Finding]:
    """Item 4 judging a waiver's `label` of `null` as one it names, beside a reviewed requirement naming no
    label, where `null` names none (maintainer, 2026-10-25): the check's reading beside any other
    requirement."""
    found = LABELS(declaration)
    for index, model in ENTRIES(declaration, "models"):
        for position, waiver in ENTRIES(model, "acceptances"):
            at = f"/models/{index}/acceptances/{position}/label"
            if waiver.get("acceptance") == "waiver" and "label" in waiver and waiver["label"] is None:
                if all(finding.pointer != at for finding in found):
                    found.append(Finding("BC-050", at, "a label of null judged"))
    return found


def _label_beside_an_unregistered_field_unjudged(declaration: JsonObject) -> list[Finding]:
    """Item 4 not judging a waiver's `label` beside a `field` that is not registered, left to the field's own
    fault."""
    return [
        finding
        for finding in LABELS(declaration)
        if at(declaration, finding.pointer.rpartition("/")[0] + "/field") in VOCABULARY.fields
    ]


# `_suites` and `_suite_members`.


def members_without(
    unwanted: Callable[[str, str], bool],
) -> Callable[[JsonObject], dict[str, list[tuple[str, str]]]]:
    """`_suite_members` without the members `unwanted` names (given each pointer and its words)."""

    def faulty(declaration: JsonObject) -> dict[str, list[tuple[str, str]]]:
        return {
            suite: [(pointer, words) for pointer, words in members if not unwanted(pointer, words)]
            for suite, members in SUITE_MEMBERS(declaration).items()
        }

    return faulty


def _interval_located_at_none(declaration: JsonObject) -> dict[str, list[tuple[str, str]]]:
    """An acceptance located at an interval and no region taken as located at none: item 12 reading a region
    alone as a scene's location."""

    def unwanted(pointer: str, words: str) -> bool:
        held = at(declaration, pointer)
        return (
            words.startswith("located at")
            and isinstance(held, dict)
            and "interval" in held
            and "region" not in held
        )

    return members_without(unwanted)(declaration)


def _engine_over_a_domain_refused_by_item_7(
    declaration: JsonObject, claims: Collection[Suite]
) -> list[Finding]:
    """Item 7 refusing an engine model over a domain, which it refuses only over a domain that includes the
    background (or with another `want`, or a pinned crosswalk not passed)."""
    found = SUITES(declaration, claims)
    for index, model in ENTRIES(declaration, "models"):
        checked_over = model.get("checked_over")
        if "engine" in model and isinstance(checked_over, dict) and "domain" in checked_over:
            found.append(Finding("BC-040", f"/models/{index}/engine", "an engine model over a domain"))
    return found


def _engine_taken(declaration: JsonObject, claims: Collection[Suite]) -> list[Finding]:
    return [finding for finding in SUITES(declaration, claims) if not finding.pointer.endswith("/engine")]


def _engine_over_records_left_to_item_12(declaration: JsonObject, claims: Collection[Suite]) -> list[Finding]:
    """Item 7 not refusing an engine model over a path or records, which item 12 then refuses."""
    return [
        finding
        for finding in SUITES(declaration, claims)
        if not (finding.case == "BC-040" and finding.detail.startswith("an engine model over a "))
    ]


def _item_12_beside_item_8(declaration: JsonObject, claims: Collection[Suite]) -> list[Finding]:
    """Item 12 refusing a sampled requirement's members where item 8 refuses the declaration over it."""
    found = SUITES(declaration, claims)
    if any(finding.case == "BC-044" for finding in found) and "sampling" not in claims:
        refused_at = {finding.pointer for finding in found}
        found += [
            Finding("BC-051", pointer, words)
            for pointer, words in SUITE_MEMBERS(declaration)["sampling"]
            if pointer.endswith(("/represents", "/population_level")) and pointer not in refused_at
        ]
    return found


def _population_level_beside_any_represents(
    declaration: JsonObject, claims: Collection[Suite]
) -> list[Finding]:
    """A `population_level` beside a `represents` that is not `population` taken by the `population_level`
    rule, item 12 refusing it where the sampling suite is not claimed."""
    found = [
        finding
        for finding in SUITES(declaration, claims)
        if not (finding.case == "BC-043" and finding.pointer.endswith("/population_level"))
    ]
    refused_at = {finding.pointer for finding in found}
    if "sampling" not in claims:
        found += [
            Finding("BC-051", pointer, words)
            for pointer, words in SUITE_MEMBERS(declaration)["sampling"]
            if pointer.endswith(("/population_level", "/represents")) and pointer not in refused_at
        ]
    return found


def _below_one(value: JsonValue) -> str | None:
    return "outside (0, 1)" if isinstance(value, float) and not 0 < value < 1 else None


def _zero_to_one(value: JsonValue) -> str | None:
    return "outside [0, 1]" if isinstance(value, float) and not 0 <= value <= 1 else None


# `_precedence`.


def _every_case_kept(found: list[Finding]) -> tuple[BuildRefusal, ...]:
    """No precedence: each rule's case kept at its pointer, those of one case and pointer merged."""
    kept: dict[tuple[str, str], None] = {}
    for finding in found:
        kept.setdefault((finding.case, finding.pointer), None)
    return tuple(BuildRefusal(case, pointer) for case, pointer in kept)


def _one_refusal_per_fault(found: list[Finding]) -> tuple[BuildRefusal, ...]:
    """The first case kept for each fault, but those of one case and pointer not merged."""
    faults: dict[tuple[str, str | None], list[Finding]] = {}
    for finding in found:
        faults.setdefault((finding.pointer, finding.aspect), []).append(finding)
    return tuple(
        BuildRefusal(min((finding.case for finding in findings), key=ORDER.index), pointer)
        for (pointer, _), findings in faults.items()
    )


def _missing_member_at_the_member(found: list[Finding]) -> tuple[BuildRefusal, ...]:
    return PRECEDENCE(
        [
            finding
            if finding.aspect is None
            else Finding(finding.case, JOIN(finding.pointer, finding.aspect))
            for finding in found
        ]
    )


def _not_json_at_the_root_member(found: list[Finding]) -> tuple[BuildRefusal, ...]:
    return PRECEDENCE(
        [
            Finding(finding.case, "/", finding.detail) if finding.detail.startswith("not JSON") else finding
            for finding in found
        ]
    )


def _first_fault_only(found: list[Finding]) -> tuple[BuildRefusal, ...]:
    return PRECEDENCE(found[:1])


def _model_index_off_by_one(pointer: str, name: str | int) -> str:
    return JOIN(pointer, name + 1 if pointer == "/models" and isinstance(name, int) else name)


# The rules S7a-1p's review found the draws reached none of, each in the reading its hand mutant gave it.


def _item_8_left_to_the_shape_table(words: str) -> Callable[[JsonObject, Collection[Suite]], list[Finding]]:
    """Item 8's refusal whose words begin with `words` given the shape table's case, BC-048, where item 8
    names it first (BC-044); the requirements it spares stay spared."""

    def faulty(declaration: JsonObject, claims: Collection[Suite]) -> list[Finding]:
        return [
            Finding("BC-048", finding.pointer, finding.detail, finding.aspect)
            if finding.case == "BC-044" and finding.detail.startswith(words)
            else finding
            for finding in SUITES(declaration, claims)
        ]

    return faulty


def _min_acceptance_of_another_type_taken(
    declaration: JsonObject, claims: Collection[Suite]
) -> list[Finding]:
    """Item 8 judging a `min_acceptance` of another JSON type as if it were one in (0, 1]: the shape table
    alone refuses it, and no requirement is spared."""
    block = declaration.get("sampling")
    if isinstance(block, dict) and not isinstance(block.get("min_acceptance", 0.5), float):
        declaration = {**declaration, "sampling": {**block, "min_acceptance": 0.5}}
    return SUITES(declaration, claims)


def _population_level_judged_beside_a_represents_at_fault(
    declaration: JsonObject, claims: Collection[Suite]
) -> list[Finding]:
    """The `population_level` rule judging a level beside a `represents` that is no token, as beside any
    other `represents`, where the refusal paragraph has it stand aside."""
    tokens = TOKEN_LISTS["requirement", "represents"]
    judged = copy.deepcopy(declaration)
    for _, model in ENTRIES(judged, "models"):
        for _, requirement in ENTRIES(model, "requirements"):
            if (
                "population_level" in requirement
                and requirement.get("represents", "population") not in tokens
            ):
                requirement["represents"] = "measurement"
    return SUITES(judged, claims)


def _waiver_condition_judged_beside_a_refused_code(kind: str, value: JsonObject, at: str) -> list[Finding]:
    """A waiver's missing `condition` refused beside a `code` that names one and is itself refused (the
    never-waived `condition_unknown_name`), where the refusal paragraph has that rule stand aside."""
    found = KIND_TOKENS(kind, value, at)
    code = value.get("code")
    if (
        kind == "waiver"
        and isinstance(code, str)
        and code in declarations.CONDITION_CODES
        and code not in TOKEN_LISTS["waiver", "code"]
        and "condition" not in value
    ):
        found.append(Finding("BC-048", at, f"a waiver of {code} names its condition", "condition"))
    return found


def _params_beside_an_unregistered_field_taken(kind: str, value: JsonObject, at: str) -> list[Finding]:
    """A nominal's `params` taken beside a `field` that names no registered field, as if that field's row
    allowed the form `parameter_set`."""
    field = value.get("field")
    registered = isinstance(field, str) and field in VOCABULARY.fields
    return [
        finding
        for finding in KIND_TOKENS(kind, value, at)
        if not (kind == "nominal" and finding.pointer == f"{at}/params" and not registered)
    ]


def _fail_closed_on_any_claimed_suite(declaration: JsonObject, claims: Collection[Suite]) -> None:
    """A build claiming a suite this version does not build failing closed whatever the declaration holds, a
    declaration holding no member of it among them."""
    for suite, words in NOT_BUILT.items():
        if suite in claims:
            raise NotImplementedError(f"a build claiming {suite}: {words}")


def _combination_field_unread(finding: Finding, _: JsonObject) -> bool:
    return re.fullmatch(
        r"/models/[0-9]+/combinations/[0-9]+/[0-9]+", finding.pointer
    ) is not None and finding.detail.endswith("is not in reads")


def _region_condition_name(finding: Finding, _: JsonObject) -> bool:
    return "/region_conditions/" in finding.pointer and "is not numeric" in finding.detail


def _trainable_field_name(finding: Finding, _: JsonObject) -> bool:
    return re.fullmatch(r"/models/[0-9]+/trainable/[0-9]+/field", finding.pointer) is not None


def _condition_unjudged_beside_a_code_that(
    states: Callable[[JsonObject], bool],
) -> Callable[[str, JsonObject, str], list[Finding]]:
    """`_kind_tokens` without a waiver's "names no condition" finding at its `condition`, where its `code` is
    in the state `states` names: the check standing aside from the rule the text states for a member at fault
    (the refusal paragraph's second exception, "a waiver whose `code` is no reason names no `condition`")."""

    def faulty(kind: str, value: JsonObject, at: str) -> list[Finding]:
        found = KIND_TOKENS(kind, value, at)
        if kind == "waiver" and states(value):
            return [finding for finding in found if finding.pointer != f"{at}/condition"]
        return found

    return faulty


def _code_missing(waiver: JsonObject) -> bool:
    """No `code`, and no member one slip from it: it was taken out."""
    return "code" not in waiver and not any(one_slip(name, "code") is not None for name in waiver)


def _code_slipped(waiver: JsonObject) -> bool:
    return "code" not in waiver and any(one_slip(name, "code") is not None for name in waiver)


def _code_retyped(waiver: JsonObject) -> bool:
    return "code" in waiver and not isinstance(waiver["code"], str)


def _trainable_record_beside_a_scene(finding: Finding, _: JsonObject) -> bool:
    return re.fullmatch(r"/models/[0-9]+/trainable/[0-9]+/record", finding.pointer) is not None and (
        "where the model is checked over" in finding.detail
    )


def _within_of_another_status_at_the_object(
    tokens: Callable[..., list[Finding]],
) -> Callable[..., list[Finding]]:
    """A `within` of a status other than `none` refused at the object, not at its `status`."""

    def faulty(declaration: JsonObject, *rest: Any) -> list[Finding]:
        return [
            dataclasses.replace(finding, pointer=finding.pointer.removesuffix("/status"))
            if "the one status of a within" in finding.detail
            else finding
            for finding in tokens(declaration, *rest)
        ]

    return faulty


def _label_of_another_type_judged_by_item_4(declaration: JsonObject) -> list[Finding]:
    """Item 4 judging a waiver's `label` that is no string, `null` aside (maintainer, 2026-10-25), as one it
    names: BC-050 at it, in front of the shape table's BC-048."""
    found = LABELS(declaration)
    models = declaration.get("models")
    for index, model in enumerate(models if isinstance(models, list) else []):
        acceptances = model.get("acceptances") if isinstance(model, dict) else None
        for position, held in enumerate(acceptances if isinstance(acceptances, list) else []):
            if (
                isinstance(held, dict)
                and held.get("acceptance") == "waiver"
                and "label" in held
                and held["label"] is not None
                and not isinstance(held["label"], str)
            ):
                at = f"/models/{index}/acceptances/{position}/label"
                found.append(Finding("BC-050", at, "a label of another type judged"))
    return found


def _combination_sections_judged_beside_an_unregistered_entry(
    declaration: JsonObject,
) -> list[Finding]:
    """The sections rule judging a combination whose entries are not all registered fields, the entry that
    is none counting as a section of its own name's first word, where the text has it stand aside."""
    found = NAMES(declaration)
    models = declaration.get("models")
    for index, model in enumerate(models if isinstance(models, list) else []):
        combinations = model.get("combinations") if isinstance(model, dict) else None
        for position, combined in enumerate(combinations if isinstance(combinations, list) else []):
            if not isinstance(combined, list) or len(combined) < 2:
                continue
            fields = [field for field in combined if isinstance(field, str)]
            if len(fields) == len(combined) and len({field.partition(".")[0] for field in fields}) < 2:
                found.append(
                    Finding("BC-048", f"/models/{index}/combinations/{position}", "of one section", None)
                )
    return found


# The ways of a stratum a mutant names whole: the token sweep's two ways of no slip, and the two ways where
# an acceptance names no location.
SWEPT = ("outside_list", "other_members_token")
UNLOCATED = ("unlocated", "accepted_difference_unlocated")
# The stratum whose faulty declaration no rule but the parse judges, so that a mutant of a rule that refuses
# what the text takes dies at the valid declaration alone, never at a fault planted beside such a value.
NOT_PARSED = ("not_json", "not_object")
EVERY = ("every_fault",)
REFUSALS = "^(refusals|taken|refused)"
VALID = "^a valid declaration refused"


MUTANTS = [
    # `_reasons` (the design's five; the review's blank text).
    Mutant(
        "empty_reason_taken",
        "_reasons",
        "HP41 reasons",
        replacing("_reasons", dropping(REASONS, lambda finding, _: finding.case == "BC-048")),
        ("empty_text",),
        REFUSALS,
        "an empty `reason` or `basis` taken",
    ),
    Mutant(
        "accept_reason_unchecked",
        "_reasons",
        "HP41 reasons",
        replacing("_reasons", dropping(REASONS, _accept_reason_unchecked)),
        ("accept_reason",),
        "^refusals",
        "an accept list's `reason` not checked by item 3",
    ),
    Mutant(
        "reason_checked_on_waivers_only",
        "_reasons",
        "HP41 reasons",
        replacing("_reasons", dropping(REASONS, _reason_checked_on_waivers_only)),
        ("acceptance_reason",),
        "^refusals",
        "an acceptance's `reason` checked by item 4 only on waivers",
    ),
    Mutant(
        "basis_checked_on_nominals_only",
        "_reasons",
        "HP41 reasons",
        replacing("_reasons", dropping(REASONS, _basis_checked_on_nominals_only)),
        ("basis",),
        "^refusals",
        "`basis` checked by item 4 on nominals but not extrapolations",
    ),
    Mutant(
        "basis_required_of_a_waiver",
        "_reasons",
        "HP41 precedence",
        replacing("_reasons", _basis_required_of_a_waiver),
        NOT_PARSED,
        VALID,
        "`basis` required of a waiver",
    ),
    Mutant(
        "empty_condition_reason_as_item_3",
        "_reasons",
        "HP41 reasons",
        replacing("_reasons", _empty_condition_reason_as_item_3),
        ("empty_text",),
        "^refusals",
        "an empty `reason` of a requirement condition refused by item 3, not by its row's Holds",
    ),
    Mutant(
        "blank_reason_refused",
        "_reasons",
        "HP41 precedence",
        replacing("_reasons", _blank_reason_refused),
        NOT_PARSED,
        VALID,
        "a `reason` or `basis` of white space alone refused",
    ),
    # `_locations` (the design's two).
    Mutant(
        "implied_condition_location_unchecked",
        "_locations",
        "HP41 locations",
        replacing(
            "_locations",
            dropping(
                LOCATIONS,
                lambda finding, declaration: kind_at(declaration, finding.pointer) == "implied_condition",
            ),
        ),
        ("unlocated",),
        REFUSALS,
        "an `implied_condition` naming no location taken",
    ),
    Mutant(
        "accepted_difference_location_required",
        "_locations",
        "HP41 locations",
        replacing("_locations", _accepted_difference_location_required),
        UNLOCATED,
        f"{VALID}|^refused",
        "an `accepted_difference` naming no location refused",
    ),
    # `_shape` and `_holds` (the design's four; the reviews' Holds rules).
    Mutant(
        "unknown_member_ignored",
        "_shape",
        "HP41 shape",
        replacing("_shape", dropping(SHAPE, detail_says("is not a member here"))),
        ("unknown", "slip"),
        REFUSALS,
        "a member the table does not name ignored",
    ),
    Mutant(
        "plural_slip_missed",
        "_shape",
        "HP41 shape",
        replacing("_shape", dropping(SHAPE, _plural_slip)),
        ("slip",),
        "^refusals",
        "a member one plural slip from a named one ignored",
    ),
    Mutant(
        "target_absence_taken",
        "_shape",
        "HP41 shape",
        replacing("_shape", dropping(SHAPE, lambda finding, _: finding.aspect == "target")),
        ("missing",),
        REFUSALS,
        "a model entry without `target` taken",
    ),
    Mutant(
        "empty_records_taken",
        "_holds",
        "HP41 shape",
        replacing("_holds", holds_dropping("fewer than", ending="/checked_over/records")),
        ("empty_list",),
        REFUSALS,
        "an empty `checked_over.records` taken",
    ),
    Mutant(
        "empty_reads_taken",
        "_holds",
        "HP41 shape",
        replacing("_holds", holds_dropping("fewer than", ending="/reads")),
        ("empty_list",),
        REFUSALS,
        "an empty `reads` taken",
    ),
    Mutant(
        "empty_accepts_taken",
        "_holds",
        "HP41 shape",
        replacing("_holds", holds_dropping("fewer than", ending="/accepts")),
        ("empty_list",),
        REFUSALS,
        "an `overlay_scope` accepting nothing taken",
    ),
    Mutant(
        "empty_reads_judged",
        "_names",
        "HP41 shape",
        replacing("_names", _fields_judged_against_an_empty_reads),
        ("empty_list",),
        "^refusals",
        "a requirement's or a `trainable` entry's `field` judged against an empty `reads`",
    ),
    Mutant(
        "exactly_one_unchecked",
        "_shape",
        "HP41 shape",
        replacing("_shape", dropping(SHAPE, detail_says("two or more of"))),
        ("breaks_holds",),
        REFUSALS,
        "two of a place's exclusive alternatives taken",
    ),
    Mutant(
        "consumer_shape_unchecked",
        "_shape",
        "HP41 shape",
        replacing("_shape", dropping(SHAPE, lambda finding, _: finding.pointer.startswith("/consumer"))),
        ("unknown", "slip"),
        REFUSALS,
        "a `consumer` missing a member, holding another or of another type, taken",
    ),
    Mutant(
        "range_order_unchecked",
        "_holds",
        "HP41 shape",
        replacing("_holds", holds_dropping("lo is above its hi")),
        ("breaks_holds",),
        REFUSALS,
        "a `range` whose `lo` is above its `hi` taken",
    ),
    Mutant(
        "number_below_zero_taken",
        "_holds",
        "HP41 shape",
        replacing("_holds", holds_dropping("below zero")),
        ("breaks_holds",),
        REFUSALS,
        "a tolerance or a `fraction_sum_tolerance` below zero taken",
    ),
    Mutant(
        "index_not_whole_taken",
        "_holds",
        "HP41 shape",
        replacing("_holds", holds_dropping("not a whole number at least zero")),
        ("breaks_holds",),
        REFUSALS,
        "a pick's `index` with a fractional part, or below zero, taken",
    ),
    Mutant(
        "status_object_taken",
        "_holds",
        "HP41 shape",
        replacing("_holds", holds_dropping("a status object, where none is taken")),
        ("breaks_holds",),
        REFUSALS,
        "a status object as a target's fact or an implied condition's value taken",
    ),
    Mutant(
        "params_taken",
        "_tokens",
        "HP41 shape",
        replacing("_tokens", dropping(TOKENS, detail_says("params, for a field with no parameter set"))),
        ("breaks_holds",),
        REFUSALS,
        "a nominal's `params` for a field whose row allows no parameter set taken",
    ),
    Mutant(
        "distribution_parameters_unchecked",
        "_tokens",
        "HP41 shape",
        replacing(
            "_tokens",
            dropping(TOKENS, lambda finding, _: finding.pointer.endswith("/distribution_parameters")),
        ),
        ("breaks_holds",),
        REFUSALS,
        "a distribution's parameters other than its token's taken",
    ),
    Mutant(
        "basis_on_any_kind_taken",
        "_shape",
        "HP41 shape",
        replacing("_shape", dropping(SHAPE, _basis_of_another_kind)),
        ("unknown", "slip"),
        REFUSALS,
        "a `basis` on a waiver, an implied condition, an accepted difference, a pick or an overlay taken",
    ),
    Mutant(
        "chains_unchecked",
        "_shape",
        "HP41 shape",
        replacing("_shape", dropping(SHAPE, _in_a_chain)),
        ("unknown", "slip"),
        REFUSALS,
        "a chain's members unchecked",
    ),
    Mutant(
        "model_name_and_version_unchecked",
        "_shape",
        "HP41 shape",
        replacing("_shape", dropping(SHAPE, _in_a_model_member)),
        ("unknown", "slip"),
        REFUSALS,
        "a `model` missing `name` or `version`, holding another member or of another type, taken",
    ),
    Mutant(
        "boolean_taken_as_a_number",
        "_holds",
        "HP41 shape",
        replacing("_holds", _boolean_taken),
        ("not_a_number",),
        REFUSALS,
        "a boolean taken where the table asks for another type",
    ),
    Mutant(
        "difference_of_any_refused",
        "_shape",
        "HP41 locations",
        replacing("_shape", _difference_of_any_refused),
        UNLOCATED,
        f"{VALID}|^refused",
        'an accepted difference of value `"any"` refused',
    ),
    Mutant(
        "difference_judged_beside_its_fact_at_fault",
        "_shape",
        "HP41 tokens",
        replacing("_shape", _difference_judged_beside_its_fact_at_fault),
        SWEPT,
        REFUSALS,
        "an accepted difference's `value` judged beside its `fact` at fault",
    ),
    # `_tokens` (the design's four; the reviews' token lists).
    Mutant(
        "review_unchecked",
        "TOKENS",
        "HP41 tokens",
        tokens_without(("requirement", "review")),
        SWEPT,
        REFUSALS,
        "a requirement's `review` holding any string taken",
    ),
    Mutant(
        "token_slip_taken",
        "_tokens",
        "HP41 tokens",
        replacing("_tokens", dropping(TOKENS, detail_says(", one slip from"))),
        ("slip_of_token", "misspelt_name"),
        REFUSALS,
        "a token one slip from one its member takes taken",
    ),
    Mutant(
        "tokens_compared_without_case",
        "TOKENS",
        "HP41 tokens",
        replacing("TOKENS", {key: Folded(tokens) for key, tokens in TOKEN_LISTS.items()}),
        ("other_case",),
        REFUSALS,
        "a member's tokens compared without case",
    ),
    Mutant(
        "want_left_to_the_read",
        "TOKENS",
        "HP41 tokens",
        tokens_without(("requirement", "want")),
        SWEPT,
        REFUSALS,
        "a requirement's `want` left to the read",
    ),
    Mutant(
        "mixing_rule_unchecked",
        "TOKENS",
        "HP41 tokens",
        tokens_without(("mixing", "rules")),
        SWEPT,
        REFUSALS,
        "a mixing rule holding any string taken",
    ),
    Mutant(
        "precision_unchecked",
        "TOKENS",
        "HP41 tokens",
        tokens_without(("model entry", "precision")),
        SWEPT,
        REFUSALS,
        "a `precision` holding any string taken",
    ),
    Mutant(
        "never_waived_code_taken",
        "TOKENS",
        "HP41 tokens",
        replacing("TOKENS", {**TOKEN_LISTS, ("waiver", "code"): tuple(VOCABULARY.reasons)}),
        SWEPT,
        REFUSALS,
        "a waiver of `condition_unknown_name` taken",
    ),
    Mutant(
        "families_unchecked",
        "_tokens",
        "HP41 tokens",
        replacing("_tokens", dropping(TOKENS, detail_says("a parameter-set field"))),
        SWEPT,
        REFUSALS,
        "a `families` entry for a field whose row allows no parameter set taken",
    ),
    Mutant(
        "space_unchecked",
        "TOKENS",
        "HP41 tokens",
        tokens_without(("distribution", "space")),
        SWEPT,
        REFUSALS,
        "a distribution's `space` holding any string taken",
    ),
    Mutant(
        "unit_unchecked",
        "_tokens",
        "HP41 tokens",
        replacing("_tokens", dropping(TOKENS, detail_says("'s unit"))),
        SWEPT,
        REFUSALS,
        "a unit other than its condition's or its fact's taken",
    ),
    Mutant(
        "waiver_condition_token_unchecked",
        "_tokens",
        "HP41 tokens",
        replacing(
            "_tokens",
            dropping(
                TOKENS,
                lambda finding, _: (
                    finding.pointer.endswith("/condition") and "a registered condition" in finding.detail
                ),
            ),
        ),
        SWEPT,
        REFUSALS,
        "a waiver's `condition` holding any string taken",
    ),
    Mutant(
        "waiver_condition_missing_taken",
        "_tokens",
        "HP41 shape",
        replacing("_tokens", dropping(TOKENS, detail_says("names its condition"))),
        ("missing",),
        REFUSALS,
        "a waiver whose code names a condition taken without its `condition`",
    ),
    Mutant(
        "kindless_acceptance_judged",
        "_ANY_KIND",
        "HP41 shape",
        replacing("_ANY_KIND", _EVERY_KIND),
        ("missing",),
        "^refusals",
        "an acceptance of no known kind judged by the members other kinds name",
    ),
    # `_names` and `_labels` (the design's seven; the reviews' combinations, `accepts` and `trainable`).
    Mutant(
        "two_models_of_one_name_taken",
        "_names",
        "HP41 names",
        replacing("_names", dropping(NAMES, detail_says("a second model of this name"))),
        ("twice",),
        REFUSALS,
        "two models of one `name` taken",
    ),
    Mutant(
        "requirement_for_a_field_not_read_taken",
        "_names",
        "HP41 names",
        replacing(
            "_names",
            dropping(
                NAMES,
                lambda finding, _: (
                    "/requirements/" in finding.pointer and "is not in reads" in finding.detail
                ),
            ),
        ),
        ("requirement_unread",),
        REFUSALS,
        "a requirement for a field not in `reads` taken",
    ),
    Mutant(
        "two_requirements_for_one_field_taken",
        "_names",
        "HP41 names",
        replacing("_names", dropping(NAMES, detail_says("a second requirement for this field"))),
        ("twice",),
        REFUSALS,
        "two requirements for one field taken",
    ),
    Mutant(
        "field_twice_in_reads_taken",
        "_names",
        "HP41 names",
        replacing("_names", dropping(NAMES, detail_says("read twice"))),
        ("twice",),
        REFUSALS,
        "a field twice in `reads` taken",
    ),
    Mutant(
        "trainable_for_a_field_not_read_taken",
        "_names",
        "HP41 names",
        replacing(
            "_names",
            dropping(
                NAMES,
                lambda finding, _: "/trainable/" in finding.pointer and "is not in reads" in finding.detail,
            ),
        ),
        ("trainable_unread",),
        REFUSALS,
        "a `trainable` entry for a field not in `reads` taken",
    ),
    Mutant(
        "trainable_at_an_unlisted_record_taken",
        "_names",
        "HP41 names",
        replacing("_names", dropping(NAMES, detail_says("a record its model is not checked over"))),
        ("trainable_unlisted",),
        REFUSALS,
        "a `trainable` entry at a record its model is not checked over taken",
    ),
    Mutant(
        "trainable_twice_by_field",
        "_names",
        "HP41 precedence",
        replacing("_names", _trainable_twice_by_field),
        NOT_PARSED,
        VALID,
        "two `trainable` entries for one field at two locations refused",
    ),
    Mutant(
        "combination_unchecked",
        "_names",
        "HP41 shape",
        replacing("_names", dropping(NAMES, detail_says("not two or more fields of different sections"))),
        ("breaks_holds",),
        REFUSALS,
        "a combination of one field, or of fields of one section, taken",
    ),
    Mutant(
        "repeated_accepts_taken",
        "_names",
        "HP41 names",
        replacing("_names", dropping(NAMES, detail_says("a token twice"))),
        ("twice",),
        REFUSALS,
        "an `accepts` token given twice taken",
    ),
    Mutant(
        "label_beside_an_unregistered_field_unjudged",
        "_labels",
        "HP41 names",
        replacing("_labels", _label_beside_an_unregistered_field_unjudged),
        ("label_unreviewed",),
        "^refusals",
        "a waiver's `label` beside a `field` that is not registered left to the field's own fault",
    ),
    Mutant(
        "label_waiver_taken_without_review",
        "_labels",
        "HP41 names",
        replacing("_labels", _label_waiver_taken_without_review),
        ("label_unreviewed",),
        REFUSALS,
        "a label-resting waiver taken without its requirement's `review`",
    ),
    Mutant(
        "null_label_judged",
        "_labels",
        "HP41 names",
        replacing("_labels", _null_label_judged),
        ("label_unreviewed",),
        REFUSALS,
        "a waiver's `label` of `null` judged by item 4 beside a reviewed requirement naming no label",
    ),
    # `_precedence` and the search (the design's six).
    Mutant(
        "bc048_beside_bc005",
        "_precedence",
        "HP41 precedence",
        replacing("_precedence", _every_case_kept),
        ("two_rules",),
        "^refusals",
        "BC-048 given beside BC-005 for one missing `reason`",
    ),
    Mutant(
        "missing_member_at_the_member",
        "_precedence",
        "HP41 precedence",
        replacing("_precedence", _missing_member_at_the_member),
        ("two_rules", "missing_member"),
        "^refusals",
        "a missing member's pointer at the member, not at its parent",
    ),
    Mutant(
        "two_missing_members_given_twice",
        "_precedence",
        "HP41 precedence",
        replacing("_precedence", _one_refusal_per_fault),
        ("two_missing",),
        "^a refusal given twice",
        "two members missing from one object given as two refusals",
    ),
    Mutant(
        "not_json_pointer_not_empty",
        "_precedence",
        "HP41 precedence",
        replacing("_precedence", _not_json_at_the_root_member),
        ("not_json",),
        "^refusals",
        'a text that is not JSON refused at "/", not at ""',
    ),
    Mutant(
        "first_fault_only",
        "_precedence",
        "HP41 every_fault",
        replacing("_precedence", _first_fault_only),
        EVERY,
        "^refusals",
        "the search stopping at the first fault",
    ),
    Mutant(
        "model_index_off_by_one",
        "_join",
        "HP41 every_fault",
        replacing("_join", _model_index_off_by_one),
        EVERY,
        "^refusals",
        "a pointer's model index off by one",
    ),
    # `_suites` (the design's seven; the reviews' sampling rules).
    Mutant(
        "region_conditions_taken",
        "_suite_members",
        "HP42",
        replacing(
            "_suite_members", members_without(lambda pointer, _: pointer.endswith("/region_conditions"))
        ),
        ("region_conditions",),
        REFUSALS,
        "`region_conditions` taken without the scene suite",
    ),
    Mutant(
        "path_taken",
        "_suite_members",
        "HP42",
        replacing(
            "_suite_members", members_without(lambda pointer, _: pointer.endswith("/checked_over/path"))
        ),
        ("path",),
        REFUSALS,
        "a model checked over a path taken without the scene suite",
    ),
    Mutant(
        "interval_location_taken",
        "_suite_members",
        "HP41 locations",
        replacing("_suite_members", _interval_located_at_none),
        ("located",),
        "^(refusals|refused|taken)",
        "an acceptance located at an interval taken without the scene suite",
    ),
    Mutant(
        "engine_over_a_domain_refused_by_item_7",
        "_suites",
        "HP42",
        replacing("_suites", _engine_over_a_domain_refused_by_item_7),
        ("engine",),
        REFUSALS,
        "an engine model over a domain refused by item 7 as one over records is",
    ),
    Mutant(
        "sampling_independence_unrequired",
        "_shape",
        "HP42",
        replacing("_shape", dropping(SHAPE, lambda finding, _: finding.aspect == "independence")),
        ("sampling",),
        REFUSALS,
        "a `sampling` block without `independence` taken",
    ),
    Mutant(
        "engine_taken",
        "_suites",
        "HP42",
        replacing("_suites", _engine_taken),
        ("engine",),
        REFUSALS,
        "a model with `engine` taken",
    ),
    Mutant(
        "distribution_taken",
        "_suite_members",
        "HP42",
        replacing("_suite_members", members_without(lambda _, words: words == "a distribution")),
        ("sampling",),
        REFUSALS,
        "a `distribution` acceptance taken without the sampling suite",
    ),
    Mutant(
        "represents_taken",
        "_suite_members",
        "HP42",
        replacing("_suite_members", members_without(lambda pointer, _: pointer.endswith("/represents"))),
        ("sampling",),
        f"{REFUSALS}|^a build claiming sampling did not fail closed",
        "a requirement's `represents` taken without the sampling suite",
    ),
    Mutant(
        "engine_over_records_left_to_item_12",
        "_suites",
        "HP42",
        replacing("_suites", _engine_over_records_left_to_item_12),
        ("engine",),
        REFUSALS,
        "BC-051 for an engine model over records in place of BC-040",
    ),
    Mutant(
        "engine_value_refused_at_the_value",
        "_ITEM_7_MEMBERS",
        "HP42",
        replacing("_ITEM_7_MEMBERS", frozenset[tuple[str, str]]()),
        ("engine",),
        "^refusals",
        "an engine value without `reason` or `basis` refused at the value beside the model's `engine`",
    ),
    Mutant(
        "item_12_beside_item_8",
        "_suites",
        "HP42",
        replacing("_suites", _item_12_beside_item_8),
        ("sampling",),
        REFUSALS,
        "BC-051 beside BC-044 for a `represents` with no `sampling`",
    ),
    Mutant(
        "population_level_beside_any_represents",
        "_suites",
        "HP42",
        replacing("_suites", _population_level_beside_any_represents),
        ("sampling",),
        REFUSALS,
        "a `population_level` beside another `represents`, or none, left to item 12",
    ),
    Mutant(
        "min_acceptance_one_refused",
        "_in_unit_interval",
        "HP42",
        replacing("_in_unit_interval", _below_one),
        ("sampling",),
        REFUSALS,
        "a `min_acceptance` of 1 refused by item 8",
    ),
    Mutant(
        "min_acceptance_zero_taken",
        "_in_unit_interval",
        "HP42",
        replacing("_in_unit_interval", _zero_to_one),
        ("sampling",),
        REFUSALS,
        "a `min_acceptance` of 0 taken by item 8",
    ),
    # The rules S7a-1p's review found no draw reached (the refusal paragraph's first and third rules that
    # stand aside, item 8's arms, item 12's last members, the scene's, a claimed suite, names inside a
    # member), each now drawn.
    Mutant(
        "min_acceptance_missing_left_to_the_shape_table",
        "_suites",
        "HP42",
        replacing(
            "_suites", _item_8_left_to_the_shape_table("a requirement samples, with no min_acceptance")
        ),
        ("sampling",),
        REFUSALS,
        "a `sampling` without `min_acceptance`, beside a requirement that samples, refused by the shape "
        "table alone (BC-048), not item 8",
    ),
    Mutant(
        "sampling_of_another_type_left_to_the_shape_table",
        "_suites",
        "HP42",
        replacing(
            "_suites", _item_8_left_to_the_shape_table("a requirement samples, and sampling is no object")
        ),
        ("sampling",),
        REFUSALS,
        "a `sampling` of another JSON type, beside a requirement that samples, refused by the shape table "
        "alone (BC-048), not item 8",
    ),
    Mutant(
        "min_acceptance_of_another_type_left_to_the_shape_table",
        "_suites",
        "HP42",
        replacing("_suites", _min_acceptance_of_another_type_taken),
        ("sampling",),
        REFUSALS,
        "a `min_acceptance` of another JSON type, a boolean among them, beside a requirement that samples, "
        "refused by the shape table alone, not item 8",
    ),
    Mutant(
        "population_level_judged_beside_a_represents_at_fault",
        "_suites",
        "HP42",
        replacing("_suites", _population_level_judged_beside_a_represents_at_fault),
        ("sampling",),
        REFUSALS,
        "the `population_level` rule judging a level beside a `represents` that is no token",
    ),
    Mutant(
        "within_of_any_status_taken",
        "_tokens",
        "HP42",
        replacing("_tokens", dropping(TOKENS, detail_says("the one status of a within"))),
        ("sampling",),
        REFUSALS,
        "a `population_level`'s `within` of a status other than `none` taken",
    ),
    Mutant(
        "item_12_after_the_shape_table",
        "ORDER",
        "HP42",
        replacing("ORDER", (*ORDER[:-2], ORDER[-1], ORDER[-2])),
        ("sampling",),
        REFUSALS,
        "a member both item 12 and the shape table name carrying the shape table's case, BC-048",
    ),
    Mutant(
        "engine_over_a_path_left_to_item_12",
        "_suites",
        "HP42",
        replacing("_suites", dropping(SUITES, detail_says("an engine model over a path"))),
        ("engine",),
        REFUSALS,
        "item 7 not refusing an engine model checked over a path",
    ),
    Mutant(
        "region_condition_names_unchecked",
        "_tokens",
        "HP42",
        replacing("_tokens", dropping(TOKENS, _region_condition_name)),
        ("region_conditions",),
        REFUSALS,
        "a condition's name in `region_conditions` that is no numeric condition taken",
    ),
    Mutant(
        "trainable_location_taken_without_the_scene_suite",
        "_suite_members",
        "HP42",
        replacing("_suite_members", members_without(lambda pointer, _: "/trainable/" in pointer)),
        ("domain", "path"),
        REFUSALS,
        "a `trainable` entry at a region or an interval taken without the scene suite",
    ),
    Mutant(
        "fail_closed_on_any_claimed_suite",
        "_fail_closed",
        "HP42",
        replacing("_fail_closed", _fail_closed_on_any_claimed_suite),
        ("domain", "path"),
        "^the check raised NotImplementedError",
        "a build claiming the scene suite, USD read or the sampling suite failing closed for a declaration "
        "that holds no member of it",
    ),
    Mutant(
        "waiver_condition_judged_beside_a_refused_code",
        "_kind_tokens",
        "HP41 tokens",
        replacing("_kind_tokens", _waiver_condition_judged_beside_a_refused_code),
        SWEPT,
        "^refusals",
        "a waiver's missing `condition` refused beside its never-waived `code`",
    ),
    Mutant(
        "combination_field_unread_taken",
        "_names",
        "HP41 shape",
        replacing("_names", dropping(NAMES, _combination_field_unread)),
        ("breaks_holds",),
        REFUSALS,
        "a combination naming a registered field its model does not list in `reads` taken",
    ),
    Mutant(
        "params_beside_an_unregistered_field_taken",
        "_kind_tokens",
        "HP41 shape",
        replacing("_kind_tokens", _params_beside_an_unregistered_field_taken),
        ("breaks_holds",),
        REFUSALS,
        "a nominal's `params` beside a `field` that names no registered field taken",
    ),
    Mutant(
        "trainable_field_name_unchecked",
        "_tokens",
        "HP41 shape",
        replacing("_tokens", dropping(TOKENS, _trainable_field_name)),
        ("empty_list",),
        REFUSALS,
        "a `trainable` entry's `field` that names no registered field taken beside a `reads` at fault",
    ),
    Mutant(
        "condition_beside_a_missing_code_unjudged",
        "_kind_tokens",
        "HP41 shape",
        replacing("_kind_tokens", _condition_unjudged_beside_a_code_that(_code_missing)),
        ("missing",),
        REFUSALS,
        "a waiver's `condition` left unjudged beside a `code` taken out",
    ),
    Mutant(
        "condition_beside_a_retyped_code_unjudged",
        "_kind_tokens",
        "HP41 shape",
        replacing("_kind_tokens", _condition_unjudged_beside_a_code_that(_code_retyped)),
        ("breaks_holds",),
        REFUSALS,
        "a waiver's `condition` left unjudged beside a `code` of another JSON type",
    ),
    Mutant(
        "condition_beside_a_slipped_code_unjudged",
        "_kind_tokens",
        "HP41 shape",
        replacing("_kind_tokens", _condition_unjudged_beside_a_code_that(_code_slipped)),
        ("slip",),
        REFUSALS,
        "a waiver's `condition` left unjudged beside a `code` written as a slip of its name",
    ),
    Mutant(
        "trainable_record_beside_a_scene_taken",
        "_names",
        "HP42",
        replacing("_names", dropping(NAMES, _trainable_record_beside_a_scene)),
        ("domain", "path"),
        REFUSALS,
        "a `trainable` entry at a record taken where its model is checked over a domain or a path",
    ),
    Mutant(
        "within_of_another_status_refused_at_the_object",
        "_tokens",
        "HP42",
        replacing("_tokens", _within_of_another_status_at_the_object(TOKENS)),
        ("sampling",),
        REFUSALS,
        "a `within` of a status other than `none` refused at the object, not at its `status`",
    ),
    Mutant(
        "label_of_another_type_judged_by_item_4",
        "_labels",
        "HP41 precedence",
        replacing("_labels", _label_of_another_type_judged_by_item_4),
        ("two_rules",),
        REFUSALS,
        "a waiver's `label` of another JSON type judged by item 4, BC-050 in front of the shape table's "
        "BC-048",
    ),
    Mutant(
        "combination_sections_judged_beside_an_unregistered_entry",
        "_names",
        "HP41 tokens",
        replacing("_names", _combination_sections_judged_beside_an_unregistered_entry),
        ("slip_of_token", "misspelt_name"),
        REFUSALS,
        "a combination judged for its sections beside an entry that names no registered field",
    ),
]


@pytest.mark.parametrize("size", [pytest.param(SMALL, id="small"), pytest.param(ORIGINAL, id="original")])
@pytest.mark.parametrize("mutant", MUTANTS, ids=[mutant.name for mutant in MUTANTS])
def test_the_declaration_mutant_is_killed(
    mutant: Mutant,
    size: Size,
    monkeypatch: pytest.MonkeyPatch,
    record_property: Callable[[str, object], None],
) -> None:
    """At an example of one of the ways it names, and at the assertion it names."""
    mutant.inject(monkeypatch)
    examples, _, check = KILLERS[mutant.killer]
    said: list[str] = []

    def checked(example: Drawn) -> None:
        try:
            check(example)
        except AssertionError as error:
            said.append(str(error))
            raise

    tried, example = kill(examples(size, stratum(mutant)), checked)
    record_property("examples_to_kill", tried)
    assert cast(Drawn, example).way in mutant.dies_at, cast(Drawn, example).way
    assert re.search(mutant.says, said[0]), said[0]
