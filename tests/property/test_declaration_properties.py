# SPDX-License-Identifier: Apache-2.0
"""HP41 and HP42 (the S7 design's 6.4): the declaration's own check (`declarations.md` section 1), over the
draws of `declaration_strategies.py`, against an oracle written here from the text.

- HP41, in seven parts: a declaration the text takes gives no refusal, its `reason` and `basis` strings judged
  by nothing but their length (a space, a tab or a long text among them); each fault planted in it gives
  exactly its `{item, pointer}`, under the precedence rule; and several give all of theirs, in any order. The
  parts: `reasons` (items 3 and 4, and the empty string), `locations` (section 4.1's location column and its
  rule), `shape` (a required member missing, a value its Holds column refuses, a member not named at its
  place, a slip of a named one, an empty list where one entry is asked), `tokens` (a token or a registered
  name outside its member's list), `names` (a name given twice, a field not read, a location not checked
  over, a label-resting waiver of item 4), `precedence` (a fault two rules name, a missing member's pointer,
  a text that is not JSON, a value that is not an object, two members missing from one object) and
  `every_fault` (two to five faults at once, across models).
- HP42: what a build cannot check (item 12), against items 7 and 8 and the `population_level` rule, which come
  first, member by member: a declaration with one scene, engine or sampling member planted is refused with
  the cases T4's order gives, one per fault at its pointer, and otherwise refused exactly as without it; and a
  build that claims the member's suite raises `NotImplementedError` for it (a claimed suite fails closed:
  maintainer, 2026-10-24).

The oracle: each planted fault's rules, by its name (`RULES`, each from its sentence); a fault more than one
rule names (one member at fault: maintainer, 2026-10-24) carries the case first in the refusal paragraph's
order (`ORDER`); two faults of one case and one pointer are one refusal; and a fault a rule judges against a
member itself at fault, or inside an acceptance that names no known kind, is not judged (`judged`).

HP1, HP2 and HP11's checks (`check_totality`, `check_status_law`, `check_claims`) are of a result's `read`:
S7a-1 gives none, a declaration being refused or raising `NotImplementedError` past its check, so none applies
here; they join with S7a-2's results.
"""

from collections.abc import Iterator, Mapping, Sequence
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from materica.core.declarations import Declaration
from materica.core.jsonio import JsonValue
from materica.shapes import Suite
from tests.property import declaration_strategies as strategies
from tests.property.declaration_strategies import FACTS, KINDS, Drawn, Planted, model_of
from tests.property.strategies import SIZE
from tests.property.support import feature

# The refusal paragraph: "A fault more than one rule names carries the case of the first of: items 3, 4, 7
# and 8, the `population_level` rule and section 4.1's location rule [BC-004] [BC-005] [BC-040] [BC-044]
# [BC-043] [BC-037]; section 4.1 item 4 [BC-050]; item 12 [BC-051]; this paragraph [BC-048]."
ORDER = ("BC-004", "BC-005", "BC-040", "BC-044", "BC-043", "BC-037", "BC-050", "BC-051", "BC-048")
SHAPE = frozenset({"BC-048"})

# Each planted fault's rules, by its name.
RULES: Mapping[str, frozenset[str]] = {
    # Item 3: "A tolerance or accept list MUST carry its reason"; and the `reason` row, "yes (item 3)".
    "condition_without_reason": frozenset({"BC-004", "BC-048"}),
    # Item 4: "Every acceptance MUST carry a `reason`; an extrapolation, a nominal and a distribution also
    # carry the `basis` of their number"; and the rows of `reason` and `basis`.
    "acceptance_without_reason": frozenset({"BC-005", "BC-048"}),
    "acceptance_without_basis": frozenset({"BC-005", "BC-048"}),
    # Items 3 and 4: "an empty `reason` breaks its row's Holds, BC-048"; `law`, "text of at least one
    # character" (section 4.1).
    "empty_text": SHAPE,
    # Section 4.1: "An acceptance whose kind needs a location and names none is refused. [BC-037]"; a pick's
    # location is its `record`, a member its row requires (maintainer, 2026-10-24).
    "unlocated": frozenset({"BC-037"}),
    "unlocated_pick": frozenset({"BC-037", "BC-048"}),
    # The paragraph's list of departures: a required member missing, a value breaking its row's Holds (another
    # JSON type among them), a member the table does not name at that place, a token or registered name not of
    # its member's list, a name given twice, a field not in `reads`, a location not checked over.
    "missing_member": SHAPE,
    "holds": SHAPE,
    "unknown_member": SHAPE,
    "token": SHAPE,
    "twice": SHAPE,
    "unread": SHAPE,
    "unlisted": SHAPE,
    # Section 4.1 item 4: a waiver naming a `label` is refused "unless the requirement for its field names
    # that `label` and holds `review: "reviewed"`" [BC-050], at its `label`; one of another field, or of
    # another type, breaks the label row's Holds too. A `label` of `null` names no label, so item 4 does not
    # judge it: a member of another JSON type, refused at itself by the shape table alone, `holds`
    # (maintainer, 2026-10-25).
    "label_unreviewed": frozenset({"BC-050"}),
    "waiver_label": frozenset({"BC-050", "BC-048"}),
    # "for a text that is not valid JSON, or a declaration that is not an object, the empty pointer".
    "not_json": SHAPE,
    "not_object": SHAPE,
    # Item 12: "where it does not claim the scene suite, a model checked over a domain or a path,
    # `region_conditions`, and an acceptance or `trainable` entry located at a region or an interval; ...
    # where it does not claim the sampling suite, ..., and a `distribution` acceptance".
    "scene_member": frozenset({"BC-051"}),
    "sampling_member": frozenset({"BC-051"}),
}


def item_7(facts: Mapping[str, object]) -> frozenset[str]:
    """Item 7 refuses a model with `engine` "checked over a path or records, ..., or with another `want`", "a
    declared engine value without `reason` and `basis`", and "a pinned crosswalk that is not passed", which
    every pinned crosswalk is to this version's build; at its `engine`, one refusal per model "whichever of
    that item's rules it breaks" (the refusal paragraph), and none at the value, though the shape table names
    its `reason` and `basis` too (`changes.md`, S7a-1b's second review). Item 12 names its `engine` too, where
    USD read is not claimed."""
    wants = cast(tuple[str, ...], facts["wants"])
    refused = (
        facts["over"] in ("path", "records")
        or facts["crosswalk"]
        or facts["unexplained"]
        or any(want != "value" for want in wants)
    )
    return frozenset({"BC-040", "BC-051"}) if refused else frozenset({"BC-051"})


def sampling(facts: Mapping[str, object]) -> Iterator[tuple[str, str | None, frozenset[str]]]:
    """Item 8: "A declaration in which a requirement samples, without [`sampling.min_acceptance`] or with one
    outside (0, 1], is refused at build"; "A requirement samples where it holds `represents`". The
    `population_level` rule: present "where `represents` is `population`, and only there". Item 12, "where it
    does not claim the sampling suite, `sampling`, a requirement's `represents` or `population_level`, and a
    `distribution` acceptance", except that "where item 8 or that rule refuses the declaration over a
    requirement, that requirement gives none"."""
    block = facts["block"]
    requirements = cast(tuple[tuple[str, str | None, bool], ...], facts["requirements"])
    distributions = cast(tuple[str, ...], facts["distributions"])
    sampled = [at for at, represents, _ in requirements if represents is not None]
    if sampled and block == "absent":
        # The member missing: the declaration should hold `sampling`.
        yield "", "sampling", frozenset({"BC-044", "BC-048"})
    if block == "outside":
        # `min_acceptance`, "a number in (0, 1]", breaks its row's Holds, and item 8's rule where one samples.
        yield "/sampling/min_acceptance", None, frozenset({"BC-044", "BC-048"} if sampled else {"BC-048"})
    if block != "absent":
        yield "/sampling", None, frozenset({"BC-051"})
    spared = set(sampled) if sampled and block in ("absent", "outside") else set[str]()
    for at, represents, level in requirements:
        if represents == "population" and not level:
            yield at, "population_level", frozenset({"BC-043", "BC-048"})
            spared.add(at)
        elif level and represents != "population":
            yield at + "/population_level", None, frozenset({"BC-043", "BC-051"})
            spared.add(at)
    for at, represents, level in requirements:
        if at not in spared:
            yield from (
                (at + "/" + name, None, frozenset({"BC-051"})) for name in ("represents",) if represents
            )
            yield from ((at + "/population_level", None, frozenset({"BC-051"})) for _ in range(int(level)))
    for at in distributions:
        yield at, None, frozenset({"BC-051"})


def faults_of(planted: Sequence[Planted]) -> Iterator[tuple[str, str | None, frozenset[str]]]:
    """Each fault: its pointer, the missing member or alternatives it is (None for the member at fault
    itself), and the rules that name it."""
    for fault in planted:
        facts = dict(fault.facts)
        if fault.fault == "engine":
            yield fault.pointer, None, item_7(facts)
        elif fault.fault == "sampling":
            yield from sampling(facts)
        else:
            yield fault.pointer, fault.aspect, RULES[fault.fault]


def kindless_and_unread(declaration: JsonValue | bytes) -> tuple[list[str], set[int]]:
    """The acceptances of `declaration` that name no known kind (their `acceptance` missing, or no kind of
    section 4.1), by pointer, and the models whose `reads` is at fault (missing, no list, or empty), by
    index."""
    kindless: list[str] = []
    unread: set[int] = set()
    models = declaration.get("models") if isinstance(declaration, dict) else None
    for m, model in enumerate(models if isinstance(models, list) else []):
        if not isinstance(model, dict):
            continue
        reads = model.get("reads")
        if not (isinstance(reads, list) and reads):
            unread.add(m)
        listed = model.get("acceptances")
        for k, held in enumerate(listed if isinstance(listed, list) else []):
            if isinstance(held, dict) and held.get("acceptance") not in KINDS:
                kindless.append(f"/models/{m}/acceptances/{k}")
    return kindless, unread


def unshaped(declaration: JsonValue | bytes) -> list[str]:
    """The `value`s of the accepted differences of `declaration` that no fact's shape judges, by pointer: an
    object holding no `status` beside a `fact` at fault (missing, no string, or no fact of `provenance.md`
    section 6.2)."""
    found: list[str] = []
    models = declaration.get("models") if isinstance(declaration, dict) else None
    for m, model in enumerate(models if isinstance(models, list) else []):
        listed = model.get("acceptances") if isinstance(model, dict) else None
        for k, held in enumerate(listed if isinstance(listed, list) else []):
            if not (isinstance(held, dict) and held.get("acceptance") == "accepted_difference"):
                continue
            value, fact = held.get("value"), held.get("fact")
            if isinstance(value, dict) and "status" not in value and fact not in FACTS:
                found.append(f"/models/{m}/acceptances/{k}/value")
    return found


def judged(planted: Sequence[Planted], declaration: JsonValue | bytes) -> list[Planted]:
    """The planted faults the refusal paragraph judges: "A rule that judges one member against another stands
    aside where the other is itself at fault, so that one fault is one refusal: ... a requirement's `field`
    against a `reads` at fault (an empty one too) ...; an acceptance that names no known kind is refused at
    itself, and none of its other members is judged." A field not read is judged against `reads` alike for a
    requirement and a `trainable` entry (the members table: "each for a field in `reads`", "a field in
    `reads`"). An acceptance of no kind keeps the fault of its kind alone: its `acceptance` missing, at it, or
    no kind, at that member. An accepted difference's `value` is judged against its `fact` ("its `value` that
    fact's shape", the members table): beside a `fact` at fault no shape asks a member of it or names one, so
    nothing inside it is judged (the paragraph a ruling, applied to the pairs it does not name: maintainer,
    2026-10-25)."""
    kindless, unread = kindless_and_unread(declaration)
    shapeless = unshaped(declaration)

    def kept(fault: Planted) -> bool:
        for at in kindless:
            if (fault.pointer == at and fault.aspect == "acceptance") or fault.pointer == at + "/acceptance":
                return True
            if fault.pointer == at or fault.pointer.startswith(at + "/"):
                return False
        if any(fault.pointer == at or fault.pointer.startswith(at + "/") for at in shapeless):
            return False
        return not (fault.fault == "unread" and model_of(fault.pointer) in unread)

    return [fault for fault in planted if kept(fault)]


def expected(planted: Sequence[Planted], declaration: JsonValue | bytes) -> set[tuple[str, str]]:
    """The refusals the text gives the planted faults it judges in `declaration`: one fault per member at
    fault, of the case first in `ORDER` of the rules that name it; two of one case and one pointer, one
    refusal."""
    named: dict[tuple[str, str | None], set[str]] = {}
    for at, aspect, rules in faults_of(judged(planted, declaration)):
        named.setdefault((at, aspect), set()).update(rules)
    return {(min(rules, key=ORDER.index), at) for (at, _), rules in named.items()}


def refusals_of(declaration: JsonValue | bytes, claims: frozenset[Suite]) -> list[tuple[str, str]] | None:
    """The check's refusals, in its order, or None where it takes the declaration. The check never raises for
    a declaration drawn here, under claims of no suite item 12 names: one it takes, it gives whole."""
    try:
        checked = Declaration.from_json(declaration, claims)
    except Exception as error:
        raise AssertionError(f"the check raised {error!r}") from error
    return (
        None if isinstance(checked, Declaration) else [(refusal.item, refusal.pointer) for refusal in checked]
    )


def check_valid(drawn: Drawn) -> None:
    """A declaration the text takes gives no refusal."""
    found = refusals_of(drawn.valid, drawn.claims)
    assert found is None, f"a valid declaration refused: {found}"


def check_refusals(drawn: Drawn) -> None:
    """The planted faults give exactly the oracle's refusals, each once."""
    wanted = expected(drawn.planted, drawn.declaration)
    found = refusals_of(drawn.declaration, drawn.claims)
    if not wanted:
        assert found is None, f"refused {found}, where the text refuses nothing"
        return
    assert found is not None, f"taken, where the text refuses {sorted(wanted)}"
    assert len(found) == len(set(found)), f"a refusal given twice: {found}"
    assert set(found) == wanted, f"refusals {sorted(set(found))}, the text's {sorted(wanted)}"


def check_declaration(drawn: Drawn) -> None:
    check_valid(drawn)
    check_refusals(drawn)


def check_unbuilt(drawn: Drawn) -> None:
    """HP42: the member's refusals beside the others', and the others as without it; and a build claiming the
    member's suite fails closed."""
    check_valid(drawn)
    check_refusals(drawn)
    suite = drawn.suite
    assert drawn.without is not None
    assert suite is not None
    without = set(refusals_of(drawn.without, drawn.claims) or ())
    member = expected(drawn.planted[drawn.beside :], drawn.declaration)
    found = set(refusals_of(drawn.declaration, drawn.claims) or ())
    assert found == without | member, (
        f"refused otherwise than without the member: {sorted(found)}, without it {sorted(without)} and the"
        f" member's {sorted(member)}"
    )
    claimed: frozenset[Suite] = drawn.claims.union((suite,))
    try:
        checked = Declaration.from_json(drawn.declaration, claimed)
    except NotImplementedError:
        return
    shown = (
        "taken" if isinstance(checked, Declaration) else sorted((one.item, one.pointer) for one in checked)
    )
    raise AssertionError(f"a build claiming {suite} did not fail closed: {shown}")


# Each part's strata (`strategies.STRATA`), each a test of its own drawing its way first among them.
STRATA = {
    part: [pytest.param(stratum, id="-".join(stratum), marks=pytest.mark.drawn(*stratum)) for stratum in ways]
    for part, ways in (*strategies.STRATA.items(), ("HP42", strategies.HP42_STRATA))
}


@pytest.mark.parametrize("ways", STRATA["reasons"])
@given(data=st.data())
def test_a_reason_or_a_basis_missing_or_empty_is_refused_by_items_3_and_4(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.hp41("reasons", SIZE, ways))
    feature(drawn.way)
    check_declaration(drawn)


@pytest.mark.parametrize("ways", STRATA["locations"])
@given(data=st.data())
def test_an_acceptance_whose_kind_needs_a_location_and_names_none_is_refused(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.hp41("locations", SIZE, ways))
    feature(drawn.way)
    check_declaration(drawn)


@pytest.mark.parametrize("ways", STRATA["shape"])
@given(data=st.data())
def test_a_declaration_off_its_shape_is_refused_at_the_member_at_fault(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.hp41("shape", SIZE, ways))
    feature(drawn.way)
    check_declaration(drawn)


@pytest.mark.parametrize("ways", STRATA["tokens"])
@given(data=st.data())
def test_a_token_or_a_registered_name_off_its_members_list_is_refused(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.hp41("tokens", SIZE, ways))
    feature(drawn.way)
    check_declaration(drawn)


@pytest.mark.parametrize("ways", STRATA["names"])
@given(data=st.data())
def test_a_name_given_twice_a_field_not_read_and_an_unreviewed_label_are_refused(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.hp41("names", SIZE, ways))
    feature(drawn.way)
    check_declaration(drawn)


@pytest.mark.parametrize("ways", STRATA["precedence"])
@given(data=st.data())
def test_a_fault_carries_the_first_case_of_the_rules_that_name_it_once(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.hp41("precedence", SIZE, ways))
    feature(drawn.way)
    check_declaration(drawn)


@given(strategies.every_fault(SIZE))
def test_every_fault_of_a_declaration_is_refused_at_once(drawn: Drawn) -> None:
    check_declaration(drawn)


@pytest.mark.parametrize("ways", STRATA["HP42"])
@given(data=st.data())
def test_what_a_build_cannot_check_is_refused_after_items_7_and_8_and_fails_closed_where_claimed(
    ways: tuple[str, ...], data: st.DataObject
) -> None:
    drawn = data.draw(strategies.hp42(SIZE, ways))
    feature(drawn.way)
    check_unbuilt(drawn)
