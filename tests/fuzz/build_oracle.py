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
  exactly its refusals, but where the two differ as a known divergence says (`KNOWN_DIVERGENCES`, each an open
  point): a declaration it refuses with every rule's refusals placed, and one it takes, which passes its own
  check (`TAKEN`), where the check refuses nothing. Where the model does not place some rule's refusals
  (`Refused.unplaced`, or a `NoVerdict` naming such a rule), the check is held to the first three alone.
"""

import copy
import json
import re
from collections.abc import Callable, Mapping

from materica.core.build import check_build
from materica.core.jsonio import JsonValue
from materica.core.record import RecordStore
from materica.core.report import BuildReport
from materica.core.vocabulary import VOCABULARY
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
# the relation fails on any left unexplained.

Refusal = tuple[str, str]
Explains = Callable[[JsonValue, Refusals, Refusals], set[Refusal]]

MODEL = re.compile(r"/models/[0-9]+")
ACCEPTANCE = re.compile(r"/models/[0-9]+/acceptances/[0-9]+")
TRAINABLE = re.compile(r"/models/[0-9]+/trainable/[0-9]+")
REQUIREMENT = re.compile(r"/models/[0-9]+/requirements/[0-9]+")


def held(declaration: JsonValue, pointer: str) -> JsonValue:
    """The member `pointer` names, None where it names none (or names a `null`)."""
    found = member_at(declaration, pointer)
    return None if found is None else found[0]


def a_waiver(declaration: JsonValue, pointer: str) -> dict[str, JsonValue] | None:
    """The waiver `pointer` names, None where it names no acceptance whose kind is `waiver`."""
    found = held(declaration, pointer)
    return found if isinstance(found, dict) and found.get("acceptance") == "waiver" else None


def a_label_of_another_type(declaration: JsonValue, check: Refusals, model: Refusals) -> set[Refusal]:
    """A waiver's `label` of another JSON type than a string: the check refuses it by section 4.1 item 4
    first (BC-050) wherever the requirement for its field does not name that value reviewed, and the model
    by the shape table alone (BC-048), as any member of another type ("nothing inside it is checked"). The
    maintainer has ruled `null` the model's way (2026-10-25: `null` names no label, so item 4 does not judge
    it), which the check follows only beside a reviewed requirement naming no label; for the other types the
    ruling's reason holds and its words are silent."""
    return {
        refusal
        for item, at in check
        if item == "BC-050"
        and at.endswith("/label")
        and ACCEPTANCE.fullmatch(at.removesuffix("/label"))
        and a_waiver(declaration, at.removesuffix("/label")) is not None
        and not isinstance(held(declaration, at), str)
        and ("BC-048", at) in model
        for refusal in (("BC-050", at), ("BC-048", at))
    }


def a_condition_beside_a_code_at_fault(
    declaration: JsonValue, check: Refusals, model: Refusals
) -> set[Refusal]:
    """A waiver's `condition` beside a `code` missing or of another type: the model refuses the `condition`
    ("a waiver whose `code` is no reason names no condition"), where the check has the rule that judges the
    `condition` against the `code` stand aside, the `code` itself at fault (the refusal paragraph), as it
    does for a missing `condition` beside a refused `code`."""
    return {
        ("BC-048", at)
        for item, at in model
        if item == "BC-048"
        and at.endswith("/condition")
        and (waiver := a_waiver(declaration, at.removesuffix("/condition"))) is not None
        and not isinstance(waiver.get("code"), str)
    }


def a_condition_of_another_type(declaration: JsonValue, check: Refusals, model: Refusals) -> set[Refusal]:
    """A waiver's `condition` of another JSON type, where its `code` names one: the check refuses the
    `condition`, one fault one refusal, and the model refuses it and refuses the waiver too, as missing
    the `condition` its `code` needs."""
    return {
        ("BC-048", at)
        for item, at in model
        if item == "BC-048"
        and ACCEPTANCE.fullmatch(at)
        and (waiver := a_waiver(declaration, at)) is not None
        and "condition" in waiver
        and not isinstance(waiver["condition"], str)
    }


def well_formed_reference(value: JsonValue) -> bool:
    """A material reference of its row's shape: `id`, `version` and `content_hash`, strings, and nothing
    else."""
    return (
        isinstance(value, dict)
        and set(value) == {"id", "version", "content_hash"}
        and all(isinstance(member, str) for member in value.values())
    )


def listed(declaration: JsonValue, model: str) -> list[JsonValue]:
    """The records a model's `checked_over` lists, none where it lists none."""
    records = held(declaration, model + "/checked_over/records")
    return records if isinstance(records, list) else []


def a_trainable_location_beside_a_fault(
    declaration: JsonValue, check: Refusals, model: Refusals
) -> set[Refusal]:
    """A `trainable` entry's `record` judged against `checked_over` beside a fault: the entry, or a member of
    it or of its record, at fault (its `field` among them), a listed record off its shape, or a model checked
    over a domain or a path. The model refuses the record as a location its model is not checked over (its
    open point `trainable_location_in_a_scene`: "nor does a record over a domain or a path"); the check judges
    it in none of these, the other member's fault the one refusal (the refusal paragraph: a rule that judges
    one member against another stands aside), and a location over a domain or a path the scene's, which item
    12 refuses the model for."""
    explained: set[Refusal] = set()
    for item, at in model - check:
        entry = at.removesuffix("/record")
        if item != "BC-048" or not at.endswith("/record") or not TRAINABLE.fullmatch(entry):
            continue
        owner = entry.rpartition("/trainable/")[0]
        checked_over = held(declaration, owner + "/checked_over")
        over_a_scene = isinstance(checked_over, dict) and ("domain" in checked_over or "path" in checked_over)
        beside = any(
            (other == entry or other.startswith(entry + "/")) and other != at for _, other in check | model
        )
        if over_a_scene or beside or not all(map(well_formed_reference, listed(declaration, owner))):
            explained.add((item, at))
    return explained


TWICE = re.compile(r"(/models/[0-9]+/(?:trainable|requirements|checked_over/records))/([0-9]+)")


def a_name_given_twice_beside_a_fault(
    declaration: JsonValue, check: Refusals, model: Refusals
) -> set[Refusal]:
    """A name given twice (a record listed twice, two `trainable` entries or two requirements for one field)
    where an entry of the list up to the later one holds a member at fault: the check tells two entries
    apart by their names where each holds them well formed, a member besides them aside, and judges none
    that does not; the model tells them apart as values, whole, and judges them whatever they hold."""
    explained: set[Refusal] = set()
    for item, at in check ^ model:
        found = TWICE.fullmatch(at)
        if item != "BC-048" or found is None:
            continue
        entries = [f"{found.group(1)}/{index}" for index in range(int(found.group(2)) + 1)]
        if any(other.startswith(entry + "/") for _, other in check | model for entry in entries):
            explained.add((item, at))
    return explained


def ancestors(pointer: str) -> list[str]:
    """`pointer` and each pointer above it, to the declaration's own members."""
    found: list[str] = []
    while pointer:
        found.append(pointer)
        pointer = pointer.rpartition("/")[0]
    return found


def a_status_object_off_its_shape(declaration: JsonValue, check: Refusals, model: Refusals) -> set[Refusal]:
    """An object holding `status` and another member than `reason`, or a `status` that is no string, and a
    requirement's `population_level.within` that is an object: the check refuses such an object at itself,
    as no status object, and judges it as the member's other shape, where the model judges it as a status
    object, member by member (its open point `implied_status_object_pointer` reads a status object at the
    member that holds it, elsewhere)."""

    def off_its_shape(pointer: str) -> bool:
        value = held(declaration, pointer)
        if not isinstance(value, dict):
            return False
        within = pointer.endswith("/population_level/within") and REQUIREMENT.fullmatch(
            pointer.removesuffix("/population_level/within")
        )
        status = "status" in value and (
            not set(value) <= {"status", "reason"} or not isinstance(value["status"], str)
        )
        return bool(within) or status

    return {(item, at) for item, at in check ^ model if any(map(off_its_shape, ancestors(at)))}


def a_label_beside_an_unregistered_field(
    declaration: JsonValue, check: Refusals, model: Refusals
) -> set[Refusal]:
    """A requirement's `label` beside a `field` that is not registered: the check judges it against every
    registered label; the model does not judge it beside a field at fault (its open point
    `member_judged_beside_a_faulty_one`, the refusal paragraph's rule that stands aside applied to a pair it
    does not name)."""
    explained: set[Refusal] = set()
    for item, at in check - model:
        owner = at.removesuffix("/label")
        if at.endswith("/label") and REQUIREMENT.fullmatch(owner):
            field = held(declaration, owner + "/field")
            if not (isinstance(field, str) and field in VOCABULARY.fields):
                explained.add((item, at))
    return explained


def inside_a_member_at_fault(declaration: JsonValue, check: Refusals, model: Refusals) -> set[Refusal]:
    """Refusals the check gives inside an object or a list both refuse at itself, inside which the model
    refuses nothing: the model checks nothing inside a member the table does not name at its place ("nothing
    inside it is checked", read of every member at fault), where the check judges such a member by the shape
    it has where the table names it."""
    refused = {at for item, at in check & model if item == "BC-048"}
    explained: set[Refusal] = set()
    for item, at in check - model:
        for above in ancestors(at)[1:]:
            if above in refused and isinstance(held(declaration, above), dict | list):
                if not any(other.startswith(above + "/") for _, other in model):
                    explained.add((item, at))
    return explained


COMBINATION = re.compile(r"/models/[0-9]+/combinations/[0-9]+")


def a_combination_beside_its_fields_at_fault(
    declaration: JsonValue, check: Refusals, model: Refusals
) -> set[Refusal]:
    """A combination judged as a whole (fewer than two fields, fields of one section, a field twice) beside an
    entry of it at fault: the check judges it on the entries it holds; the model has the rule stand aside, its
    entries at fault (the refusal paragraph's rule that stands aside, read of a pair it does not name)."""
    return {
        (item, at)
        for item, at in check - model
        if COMBINATION.fullmatch(at) and any(other.startswith(at + "/") for _, other in check | model)
    }


# The places that take exactly one of two or three members (section 1's table).
EXCLUSIVE = (frozenset({"records", "domain", "path"}), frozenset({"value", "params"}))


def inside_one_of_two_alternatives(declaration: JsonValue, check: Refusals, model: Refusals) -> set[Refusal]:
    """Refusals the check gives inside an alternative of an object holding two of its mutually exclusive
    alternatives (a `checked_over` holding `records` and a `path`): both refuse the object, and the model
    judges neither alternative's inside (its open point `exactly_one_of`: the fault is the object's), where
    the check judges each."""
    explained: set[Refusal] = set()
    for item, at in check - model:
        for above in ancestors(at)[1:]:
            value = held(declaration, above)
            two = isinstance(value, dict) and any(len(set(value) & names) > 1 for names in EXCLUSIVE)
            if two and ("BC-048", above) in check & model:
                explained.add((item, at))
    return explained


def parameters_beside_a_distribution_at_fault(
    declaration: JsonValue, check: Refusals, model: Refusals
) -> set[Refusal]:
    """A distribution's `distribution_parameters` beside a `distribution` that is no token of
    `uncertainty.md` section 4: the check judges the parameters' members; the model does not, beside a token
    at fault (its open point `member_judged_beside_a_faulty_one`)."""
    explained: set[Refusal] = set()
    for item, at in check - model:
        owner, found, _ = at.partition("/distribution_parameters")
        if found and ACCEPTANCE.fullmatch(owner) and ("BC-048", owner + "/distribution") in check & model:
            explained.add((item, at))
    return explained


def region_conditions_of_another_type(
    declaration: JsonValue, check: Refusals, model: Refusals
) -> set[Refusal]:
    """A model's `region_conditions` of another JSON type than an object: the check refuses it by item 12
    first (BC-051), which names the member, and the model by the shape table alone (BC-048), though its own
    note on the refusal order has item 12 and the shape table both name a `domain` of another type."""
    return {
        refusal
        for item, at in check
        if item == "BC-051"
        and at.endswith("/region_conditions")
        and MODEL.fullmatch(at.removesuffix("/region_conditions"))
        and not isinstance(held(declaration, at), dict)
        and ("BC-048", at) in model
        for refusal in (("BC-051", at), ("BC-048", at))
    }


KNOWN_DIVERGENCES: Mapping[str, Explains] = {
    "waiver_label_of_another_type": a_label_of_another_type,
    "waiver_condition_beside_a_code_at_fault": a_condition_beside_a_code_at_fault,
    "waiver_condition_of_another_type": a_condition_of_another_type,
    "trainable_location_beside_a_fault": a_trainable_location_beside_a_fault,
    "name_given_twice_beside_a_fault": a_name_given_twice_beside_a_fault,
    "status_object_off_its_shape": a_status_object_off_its_shape,
    "label_beside_an_unregistered_field": a_label_beside_an_unregistered_field,
    "inside_a_member_at_fault": inside_a_member_at_fault,
    "inside_one_of_two_alternatives": inside_one_of_two_alternatives,
    "parameters_beside_a_distribution_at_fault": parameters_beside_a_distribution_at_fault,
    "combination_beside_its_fields_at_fault": a_combination_beside_its_fields_at_fault,
    "region_conditions_of_another_type": region_conditions_of_another_type,
}


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
