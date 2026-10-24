# SPDX-License-Identifier: Apache-2.0
"""Examples of the declaration's own check and `check_build` (`declarations.md` section 1), at what the
build-check files reach rarely: a pointer's escapes, the forms a declaration may be given in, the claims, the
precedence rule's corners, the report of a refused declaration, and what this version does not build, which
raises naming each acceptance."""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import materica
from materica.core.build import check_build
from materica.core.declarations import Declaration, DeclarationInput
from materica.core.jsonio import JsonValue
from materica.core.record import RecordStore
from materica.core.report import BuildRefusal
from materica.shapes import Suite
from tests.spec_sync.schemas import agreed

BUILD_CHECKS = Path(materica.__file__).parent / "data" / "conformance" / "build_checks"
Json = dict[str, JsonValue]
# A declaration the check takes: BC-016's, one model over water with one waiver (its arm's control).
VALID: Json = json.loads((BUILD_CHECKS / "inputs" / "bc016_waiver_at_one_of_two_records.json").read_bytes())


def store() -> RecordStore:
    return materica.load_records([BUILD_CHECKS / "inputs" / "water_fixture.json"])


def a_declaration(change: Callable[[Json], object] = lambda declaration: None) -> Json:
    declaration = copy.deepcopy(VALID)
    change(declaration)
    return declaration


def model(declaration: Json, index: int = 0) -> Json:
    return cast(list[Json], declaration["models"])[index]


def acceptances(declaration: Json) -> list[JsonValue]:
    return cast(list[JsonValue], model(declaration)["acceptances"])


WATER = cast(Json, acceptances(VALID)[0])["record"]
PICK: Json = {"acceptance": "pick", "record": WATER, "field": "fluid.dynamic_viscosity", "index": 0.0}
PICK["reason"] = "the stored alternative the model was calibrated against"


def conditions(declaration: Json) -> Json:
    return cast(Json, cast(list[Json], model(declaration)["requirements"])[0]["conditions"])


def condition(declaration: Json, name: str) -> Json:
    return cast(Json, conditions(declaration)[name])


def tolerance(declaration: Json) -> Json:
    return cast(Json, condition(declaration, "temperature")["tolerance"])


def operating(declaration: Json) -> Json:
    return cast(Json, cast(Json, declaration["operating_conditions"])["shear_rate"])


def refusals(declaration: DeclarationInput, claims: frozenset[Suite] | None = None) -> set[tuple[str, str]]:
    checked = (
        Declaration.from_json(declaration) if claims is None else Declaration.from_json(declaration, claims)
    )
    assert isinstance(checked, tuple), "the declaration was taken"
    return {(refusal.item, refusal.pointer) for refusal in checked}


def test_the_valid_declaration_is_taken_and_raises_past_its_check() -> None:
    assert isinstance(Declaration.from_json(VALID), Declaration)
    with pytest.raises(NotImplementedError, match="S7a-2 reads the records"):
        check_build(VALID, store())


# A pointer's reference tokens, escaped by RFC 6901: `~` as `~0`, then `/` as `~1`.


@pytest.mark.parametrize(
    ("name", "token"),
    [("a/b", "a~1b"), ("a~b", "a~0b"), ("~1", "~01"), ("/~", "~1~0"), ("~/", "~0~1"), ("", "")],
)
def test_a_refusals_pointer_escapes_each_name_it_passes(name: str, token: str) -> None:
    """A name the declaration's author chose, at three depths: an operating condition, a region's operating
    condition and a fact of the target, each unregistered."""

    def change(declaration: Json) -> None:
        cast(Json, declaration["operating_conditions"])[name] = {"value": 1.0, "unit": "K"}
        model(declaration)["target"] = {name: {}}
        model(declaration)["region_conditions"] = {name: {name: {"value": 1.0, "unit": "K"}}}

    assert refusals(a_declaration(change)) == {
        ("BC-048", f"/operating_conditions/{token}"),
        ("BC-048", f"/models/0/target/{token}"),
        ("BC-051", "/models/0/region_conditions"),
        ("BC-048", f"/models/0/region_conditions/{token}/{token}"),
    }


def test_an_escape_left_out_is_seen() -> None:
    """The control: the pointer of a name holding `/`, written unescaped, names another member."""
    found = refusals(a_declaration(lambda d: cast(Json, d["operating_conditions"]).update({"a/b": {}})))
    assert ("BC-048", "/operating_conditions/a/b") not in found
    assert ("BC-048", "/operating_conditions/a~1b") in found


# A declaration as text, bytes or a value: read alike (`read` reads a request so).


def as_given(declaration: Json) -> list[DeclarationInput]:
    text = json.dumps(declaration)
    return [declaration, text, text.encode(), bytearray(text.encode()), memoryview(text.encode())]


def test_a_declaration_reads_alike_as_text_bytes_and_a_value() -> None:
    faulty = a_declaration(lambda d: cast(Json, acceptances(d)[0]).pop("reason"))
    for given in as_given(faulty):
        assert refusals(given) == {("BC-005", "/models/0/acceptances/0")}, type(given)
    for given in as_given(VALID):
        with pytest.raises(NotImplementedError):
            check_build(given, store())


def test_a_text_that_is_no_json_and_a_value_that_is_none_are_refused_at_the_empty_pointer() -> None:
    for given in ("{", b"\xff", "[1, 2]", "null", '"a string"', float("nan"), {1, 2}, '{"a": 1, "a": 2}'):
        assert refusals(cast(DeclarationInput, given)) == {("BC-048", "")}, given


# The claims, checked first.


@pytest.mark.parametrize(
    "claims", [{"plain_read", "build_checks", "spelling"}, {"hash", "build_checks"}, {"plain_read", "hash"}]
)
def test_claims_no_implementation_makes_raise_before_the_declaration_is_read(claims: set[str]) -> None:
    with pytest.raises(ValueError, match=r"every build claims|not suites"):
        check_build("{", store(), claims=cast(set[Suite], claims))


def domain(declaration: Json) -> None:
    model(declaration)["checked_over"] = {"domain": "lumen"}


def engine(declaration: Json) -> None:
    pin: Json = {"id": "a crosswalk", "version": "1", "sha256": "a hash"}
    model(declaration)["engine"] = {"crosswalk": pin, "values": {}}


def sampled_requirement(declaration: Json) -> None:
    cast(list[Json], model(declaration)["requirements"])[0]["represents"] = "measurement"


@pytest.mark.parametrize(
    ("suite", "change"),
    [("scene_documents", domain), ("usd_read", engine), ("sampling", sampled_requirement)],
)
def test_a_claimed_suite_this_version_does_not_build_fails_closed_where_the_declaration_holds_its_member(
    suite: Suite, change: Callable[[Json], None]
) -> None:
    """Item 12 does not refuse what a claimed suite checks, and this version cannot check it: it raises,
    whatever else is wrong (maintainer, 2026-10-24). A declaration holding no such member is judged as without
    the claim."""
    claims: frozenset[Suite] = frozenset({"plain_read", "build_checks", suite})

    def faulty_with(declaration: Json) -> None:
        change(declaration)
        declaration.pop("consumer")

    faulty = a_declaration(faulty_with)
    with pytest.raises(NotImplementedError, match=suite):
        check_build(faulty, store(), claims=claims)
    without = a_declaration(lambda d: d.pop("consumer"))
    assert refusals(without, claims) == refusals(without) == {("BC-048", "")}
    assert isinstance(Declaration.from_json(VALID, claims), Declaration)


def test_the_claims_a_build_makes_by_default_and_without_hash_judge_alike() -> None:
    faulty = a_declaration(lambda d: model(d).pop("target"))
    expected = {("BC-048", "/models/0")}
    assert refusals(faulty) == refusals(faulty, frozenset({"plain_read", "build_checks"})) == expected


# The precedence rule's corners (the refusal paragraph).


def test_a_missing_member_is_refused_at_the_object_that_should_hold_it_once_however_many_are_missing() -> (
    None
):
    def change(declaration: Json) -> None:
        for name in ("target", "reads", "chains"):
            model(declaration).pop(name)

    checked = Declaration.from_json(a_declaration(change))
    assert isinstance(checked, tuple)
    assert [(refusal.item, refusal.pointer) for refusal in checked] == [("BC-048", "/models/0")]


def test_two_cases_at_one_pointer_are_two_refusals_where_their_faults_differ() -> None:
    """A declaration missing `consumer` (BC-048 at the declaration) whose requirement samples with no
    `sampling` (BC-044 at the declaration): two faults, each its own case, at one pointer."""

    def change(declaration: Json) -> None:
        declaration.pop("consumer")
        cast(list[Json], model(declaration)["requirements"])[0]["represents"] = "measurement"

    assert refusals(a_declaration(change)) == {("BC-048", ""), ("BC-044", "")}


def test_a_fault_two_rules_name_carries_the_first_case() -> None:
    """An extrapolation with neither a location nor a basis: BC-005 for its basis and BC-037 for its location,
    and neither as BC-048's missing member; a reason of another type is BC-048's alone, at the reason."""
    extrapolation: Json = {
        "acceptance": "extrapolation",
        "field": "fluid.dynamic_viscosity",
        "method": "constant",
    }
    extrapolation |= {"law": "the end value", "reason": 1.0}
    found = refusals(a_declaration(lambda d: acceptances(d).append(extrapolation)))
    assert found == {
        ("BC-005", "/models/0/acceptances/1"),
        ("BC-037", "/models/0/acceptances/1"),
        ("BC-048", "/models/0/acceptances/1/reason"),
    }


def test_details_are_words_no_comparison_reads() -> None:
    assert BuildRefusal("BC-048", "", "one") == BuildRefusal("BC-048", "", "another")
    assert dict(BuildRefusal("BC-048", "", "one").to_json()) == {
        "item": "BC-048",
        "pointer": "",
        "detail": "one",
    }
    assert dict(BuildRefusal("BC-048", "").to_json()) == {"item": "BC-048", "pointer": ""}


# The rulings of 2026-10-24, each beside the change it turns on.


WAIVERS: list[tuple[Callable[[Json], object], set[str]]] = [
    # A waiver whose code is `condition_unknown_name` is refused at its code, whatever condition it names; one
    # the build does not register is a second member at fault.
    (lambda waiver: waiver.update(code="condition_unknown_name", condition="temperature"), {"/code"}),
    (
        lambda waiver: waiver.update(code="condition_unknown_name", condition="pressure"),
        {"/code", "/condition"},
    ),
    (lambda waiver: waiver.update(code="condition_unstated", condition="temperature"), set()),
    # `basis` on an extrapolation, a nominal and a distribution alone.
    (lambda waiver: waiver.update(basis="the consumer's judgement"), {"/basis"}),
]


@pytest.mark.parametrize(("change", "expected"), WAIVERS)
def test_a_waiver_under_the_rulings(change: Callable[[Json], object], expected: set[str]) -> None:
    declaration = a_declaration(lambda d: change(cast(Json, acceptances(d)[0])))
    if not expected:
        assert isinstance(Declaration.from_json(declaration), Declaration)
    else:
        assert refusals(declaration) == {("BC-048", f"/models/0/acceptances/0{at}") for at in expected}


def test_a_population_level_is_refused_but_beside_population() -> None:
    """Beside another `represents` or none, at the `population_level`, before item 12; under a claim of the
    sampling suite, which checks it, the build fails closed."""

    def sampled(represents: str | None) -> Json:
        def change(declaration: Json) -> None:
            requirement = cast(list[Json], model(declaration)["requirements"])[0]
            requirement["population_level"] = {"level": "donor", "within": {"status": "none"}}
            if represents is not None:
                declaration["sampling"] = {"min_acceptance": 0.5, "reason": "a reason", "independence": []}
                requirement["represents"] = represents

        return a_declaration(change)

    at = "/models/0/requirements/0"
    assert refusals(sampled("estimate")) == {("BC-043", f"{at}/population_level"), ("BC-051", "/sampling")}
    assert refusals(sampled(None)) == {("BC-043", f"{at}/population_level")}
    assert refusals(sampled("population")) == {
        ("BC-051", "/sampling"),
        ("BC-051", f"{at}/represents"),
        ("BC-051", f"{at}/population_level"),
    }
    with pytest.raises(NotImplementedError, match="sampling"):
        Declaration.from_json(sampled(None), frozenset({"plain_read", "build_checks", "sampling"}))


# The report of a declaration refused on its own (section 2): its consumer and declaration as given, where it
# can hold them.


@pytest.mark.parametrize(
    ("given", "members"),
    [
        (b"{", {"records", "refusals", "results", "unused"}),
        (b"[]", {"records", "declaration", "refusals", "results", "unused"}),
        (b'{"models": []}', {"records", "declaration", "refusals", "results", "unused"}),
        (
            b'{"consumer": 1, "models": []}',
            {"consumer", "records", "declaration", "refusals", "results", "unused"},
        ),
    ],
)
def test_a_refused_report_holds_what_was_given_and_the_report_schema_takes_it(
    given: bytes, members: set[str]
) -> None:
    report = check_build(given, store())
    written = report.to_json()
    assert report.refused
    assert set(written) == members
    assert (written["results"], written["unused"], written["records"]) == ([], [], [])
    if "declaration" in written:
        assert written["declaration"] == json.loads(given)
    assert agreed("build_report.json")(cast(JsonValue, written))


def test_a_report_is_a_copy() -> None:
    report = check_build(b'{"consumer": {"name": "a"}}', store())
    cast(Json, report.to_json().get("consumer"))["name"] = "b"
    assert report.to_json().get("consumer") == {"name": "a"}


# What this version does not build raises, naming each acceptance and the piece that reads it.


def test_the_raise_names_each_pick_and_overlay_and_the_piece_that_applies_them() -> None:
    pick: Json = {"acceptance": "pick", "record": WATER, "field": "fluid.dynamic_viscosity", "index": 0}
    overlay: Json = {"acceptance": "overlay", "field": "fluid.dynamic_viscosity", "overlay": WATER}
    scope: Json = {"acceptance": "overlay_scope", "overlay": WATER, "accepts": ["consumer"]}
    entries = [pick, overlay, pick, scope, overlay]
    declaration = a_declaration(
        lambda d: acceptances(d).extend(entry | {"reason": "a reason"} for entry in entries)
    )
    with pytest.raises(NotImplementedError) as raised:
        check_build(declaration, store())
    said = str(raised.value)
    named = ", ".join(
        f"the {kind} /models/0/acceptances/{index}"
        for index, kind in ((1, "pick"), (2, "overlay"), (3, "pick"), (4, "overlay_scope"), (5, "overlay"))
    )
    assert f"S7c reads {named})" in said
    assert "(S7a-2 reads the waiver /models/0/acceptances/0; " in said


# The Holds constraints and the exclusive alternatives, which no build-check file plants.


HOLDS: list[tuple[Callable[[Json], object], str | None]] = [
    (
        lambda d: tolerance(d).update(value=-1.0),
        "/models/0/requirements/0/conditions/temperature/tolerance/value",
    ),
    (lambda d: tolerance(d).update(value=-0.0), None),
    (lambda d: operating(d).update(range=[500.0, 50.0]), "/operating_conditions/shear_rate/range"),
    (lambda d: operating(d).update(range=[50.0]), "/operating_conditions/shear_rate/range"),
    (lambda d: operating(d).update(range=[50.0, 50.0, 500.0]), "/operating_conditions/shear_rate/range"),
    (lambda d: operating(d).update(range=[50.0, 50.0]), None),
    # An entry of another type is a member deeper down, refused at itself.
    (lambda d: operating(d).update(range=[50.0, "500"]), "/operating_conditions/shear_rate/range/1"),
    (lambda d: operating(d).update(range=[True, 500.0]), "/operating_conditions/shear_rate/range/0"),
    (
        lambda d: model(d).update(mixing={"fraction_sum_tolerance": -1e-9, "rules": {}}),
        "/models/0/mixing/fraction_sum_tolerance",
    ),
    (lambda d: acceptances(d).append(PICK | {"index": 0.5}), "/models/0/acceptances/1/index"),
    (lambda d: acceptances(d).append(PICK | {"index": -1.0}), "/models/0/acceptances/1/index"),
    (lambda d: acceptances(d).append(PICK | {"index": 3.0}), None),
    (
        lambda d: model(d).update(target={"species": {"ncbi_taxon": 9606.5}}),
        "/models/0/target/species/ncbi_taxon",
    ),
    (
        lambda d: model(d).update(target={"anatomical_site": {"uberon": "UBERON:12a"}}),
        "/models/0/target/anatomical_site/uberon",
    ),
    (
        lambda d: condition(d, "shear_rate").pop("tolerance"),
        "/models/0/requirements/0/conditions/shear_rate",
    ),
    (lambda d: operating(d).update(value=1.0), "/operating_conditions/shear_rate"),
]


@pytest.mark.parametrize(("change", "pointer"), HOLDS)
def test_a_value_breaking_its_holds_and_two_or_none_of_its_alternatives_are_refused(
    change: Callable[[Json], object], pointer: str | None
) -> None:
    declaration = a_declaration(change)
    if pointer is None:
        assert isinstance(Declaration.from_json(declaration), Declaration)
    else:
        assert refusals(declaration) == {("BC-048", pointer)}


def test_a_waiver_names_its_condition_exactly_where_its_code_names_one() -> None:
    def waived(code: str, condition: str | None) -> Json:
        def change(declaration: Json) -> None:
            waiver = cast(Json, acceptances(declaration)[0])
            waiver.pop("condition")
            waiver["code"] = code
            if condition is not None:
                waiver["condition"] = condition

        return a_declaration(change)

    assert refusals(waived("condition_unstated", None)) == {("BC-048", "/models/0/acceptances/0")}
    assert refusals(waived("no_requirement", "temperature")) == {
        ("BC-048", "/models/0/acceptances/0/condition")
    }
    assert isinstance(Declaration.from_json(waived("no_requirement", None)), Declaration)
    assert isinstance(Declaration.from_json(waived("at_edge", "temperature")), Declaration)


# One fault is one member at fault (maintainer, 2026-10-24): a member two rules name gives one refusal, of the
# first rule's case; a status object where none is taken is refused at the member, nothing inside it checked.


def test_a_requirement_condition_holding_both_alternatives_is_two_members_at_fault() -> None:
    """The condition, for its two exclusive alternatives, and the one of them its kind does not take
    (maintainer, 2026-10-24)."""
    at = "/models/0/requirements/0/conditions"
    numeric = a_declaration(lambda d: condition(d, "temperature").update(accept=["apparent"]))
    assert refusals(numeric) == {("BC-048", f"{at}/temperature"), ("BC-048", f"{at}/temperature/accept")}
    both: Json = {"accept": ["rotational_rheometer"], "tolerance": {"value": 1.0, "unit": "K"}}
    token = a_declaration(lambda d: conditions(d).update(test_method=both | {"reason": "a reason"}))
    assert refusals(token) == {("BC-048", f"{at}/test_method"), ("BC-048", f"{at}/test_method/tolerance")}

    def accept_alone(declaration: Json) -> None:
        condition(declaration, "temperature").update(accept=["apparent"])
        condition(declaration, "temperature").pop("tolerance")

    assert refusals(a_declaration(accept_alone)) == {("BC-048", f"{at}/temperature/accept")}


@pytest.mark.parametrize(
    ("held", "inside"),
    [({}, set[str]()), ({"status": "unstated"}, {"/status"}), ({"reason": "r"}, set[str]())],
)
def test_a_requirement_condition_holding_neither_alternative_is_bc_048s_alone(
    held: Json, inside: set[str]
) -> None:
    """Item 3 names a tolerance or an accept list: a condition holding neither lacks its alternative, and its
    `reason` too, as BC-048's members missing, at the condition."""
    at = "/models/0/requirements/0/conditions/temperature"

    assert refusals(a_declaration(lambda d: conditions(d).update(temperature=held))) == {
        ("BC-048", at),
        *(("BC-048", f"{at}{member}") for member in inside),
    }


def test_a_status_object_where_none_is_taken_is_one_refusal_at_the_member() -> None:
    target = a_declaration(lambda d: model(d).update(target={"species": {"status": "unstated"}}))
    assert refusals(target) == {("BC-048", "/models/0/target/species")}
    implied: Json = {"acceptance": "implied_condition", "record": WATER, "field": "fluid.dynamic_viscosity"}
    implied |= {
        "fact": "tissue_state",
        "token": "in_vivo",
        "implies": {"temperature": {"status": "unstated"}},
    }
    implying = a_declaration(lambda d: acceptances(d).append(implied | {"reason": "a reason"}))
    assert refusals(implying) == {("BC-048", "/models/0/acceptances/1/implies/temperature")}


def test_a_waivers_label_another_fields_and_its_requirements_none_is_one_refusal_of_bc_050() -> None:
    label = a_declaration(lambda d: cast(Json, acceptances(d)[0]).update(label="materica.magnetic.linear.v1"))
    assert refusals(label) == {("BC-050", "/models/0/acceptances/0/label")}


def test_a_trainable_entry_at_a_record_and_a_region_is_one_refusal_of_item_12() -> None:
    entry: Json = {"field": "fluid.dynamic_viscosity", "record": WATER, "region": "lumen"}
    assert refusals(a_declaration(lambda d: model(d).update(trainable=[entry]))) == {
        ("BC-051", "/models/0/trainable/0")
    }


# A pick's location is its record (maintainer, 2026-10-24).


@pytest.mark.parametrize("claims", [frozenset({"plain_read", "build_checks"}), None])
def test_a_pick_naming_a_region_and_no_record_is_unlocated_whatever_the_build_claims(
    claims: frozenset[Suite] | None,
) -> None:
    pick: Json = {"acceptance": "pick", "region": "lumen", "field": "fluid.dynamic_viscosity", "index": 0}
    declaration = a_declaration(lambda d: acceptances(d).append(pick | {"reason": "a reason"}))
    expected = {("BC-037", "/models/0/acceptances/1")}
    assert refusals(declaration, frozenset({"plain_read", "build_checks", "scene_documents"})) == expected
    assert refusals(declaration, claims) == expected


def test_a_pick_at_its_record_and_a_region_is_item_12s() -> None:
    declaration = a_declaration(lambda d: acceptances(d).append(PICK | {"region": "lumen"}))
    assert refusals(declaration) == {("BC-051", "/models/0/acceptances/1")}


# Item 7 in this version: every engine model's pinned crosswalk is one not passed; one refusal per model, at
# its `engine` (the refusal paragraph; maintainer, 2026-10-24).


def test_an_engine_model_is_refused_by_item_7_at_its_engine_once() -> None:
    def over_records_wanting_bounds(declaration: Json) -> None:
        engine(declaration)
        cast(list[Json], model(declaration)["requirements"])[0]["want"] = "bounds"

    assert refusals(a_declaration(over_records_wanting_bounds)) == {("BC-040", "/models/0/engine")}
