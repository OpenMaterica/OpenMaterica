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
from materica.core.identifiers import MaterialRef
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


def requirement(declaration: Json) -> Json:
    return cast(list[Json], model(declaration)["requirements"])[0]


def appended(acceptance: Json, **members: JsonValue) -> Callable[[Json], object]:
    return lambda declaration: acceptances(declaration).append(acceptance | members | {"reason": "a reason"})


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


def test_the_valid_declaration_is_taken_and_gives_its_results() -> None:
    """BC-016's declaration over water alone: no refusal, and its two records' results, the second's record
    absent from the store."""
    assert isinstance(Declaration.from_json(VALID), Declaration)
    report = check_build(VALID, store())
    assert report.refusals == ()
    assert [result.record.id for result in report.results] == [
        "conformance/water_fixture",
        "conformance/plasma_fixture",
    ]


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
    reports = [check_build(given, store()).to_json() for given in as_given(VALID)]
    assert reports == [reports[0]] * len(reports)
    assert reports[0]["refusals"] == []


def test_a_text_that_is_no_json_and_a_value_that_is_none_are_refused_at_the_empty_pointer() -> None:
    for given in ("{", b"\xff", "[1, 2]", "null", '"a string"', float("nan"), {1, 2}, '{"a": 1, "a": 2}'):
        assert refusals(cast(DeclarationInput, given)) == {("BC-048", "")}, given


def test_a_lone_surrogate_in_a_text_is_refused_not_raised() -> None:
    """A `str` holding a lone surrogate is no UTF-8 text: refused at the empty pointer, as `parse_declaration`
    says, rather than raised."""
    text = json.dumps(
        a_declaration(lambda d: cast(Json, acceptances(d)[0]).update(reason="\ud800")), ensure_ascii=False
    )
    assert refusals("\ud800") == refusals(text) == {("BC-048", "")}


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
    requirement(declaration)["represents"] = "measurement"


DISTRIBUTION: Json = {
    "acceptance": "distribution",
    "record": WATER,
    "field": "fluid.dynamic_viscosity",
    "distribution": "normal",
    "space": "identity",
    "distribution_parameters": {"mean": 0.000692, "sd": 0.00002},
    "basis": "a spread of about 3 %",
}


@pytest.mark.parametrize(
    ("suite", "change"),
    [
        ("scene_documents", domain),
        ("usd_read", engine),
        ("sampling", sampled_requirement),
        ("sampling", appended(DISTRIBUTION)),
    ],
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


def test_a_population_level_beside_a_represents_at_fault_is_not_judged_by_the_population_level_rule() -> None:
    """A `represents` that is no token is a member at fault, and the level beside it is not judged against it
    (no rule is judged against a member at fault): item 12 refuses the level as the sampling suite's, and the
    `population_level` rule, whose case comes first where it applies, gives no BC-043."""
    at = "/models/0/requirements/0"

    def sampled(represents: JsonValue) -> Json:
        def change(declaration: Json) -> None:
            declaration["sampling"] = {"min_acceptance": 0.5, "reason": "a reason", "independence": []}
            requirement(declaration)["represents"] = represents
            requirement(declaration)["population_level"] = {"level": "donor", "within": {"status": "none"}}

        return a_declaration(change)

    at_fault: list[JsonValue] = ["bogus", 5.0, ["population"]]
    for represents in at_fault:
        assert refusals(sampled(represents)) == {
            ("BC-051", "/sampling"),
            ("BC-051", f"{at}/represents"),
            ("BC-051", f"{at}/population_level"),
        }, represents
    # The control: beside a `represents` that is a token, the same level is BC-043's.
    assert ("BC-043", f"{at}/population_level") in refusals(sampled("estimate"))


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


# What a later piece reads raises before any read, naming each and the piece that reads it
# (`tests/unit/test_build.py` holds the rest).


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
        for index, kind in ((1, "pick"), (2, "overlay"), (3, "pick"), (5, "overlay"))
    )
    assert said.endswith(f"what a later piece reads: S7c reads {named}")


def test_the_raise_names_a_trainable_entry_and_its_piece_and_no_accepted_difference() -> None:
    """An accepted difference beside an empty `target` covers nothing (the S7 design's 1.3)."""
    difference: Json = {"acceptance": "accepted_difference", "section": "fluid", "fact": "species"}
    difference["value"] = {"status": "not_applicable"}

    def change(declaration: Json) -> None:
        appended(difference)(declaration)
        model(declaration)["trainable"] = [{"field": "fluid.dynamic_viscosity", "record": WATER}]

    with pytest.raises(NotImplementedError) as raised:
        check_build(a_declaration(change), store())
    assert str(raised.value).endswith(
        "what a later piece reads: S7a-4 reads the trainable entry /models/0/trainable/0"
    )


# A declaration that passes, typed member by member: S7a-2 and the pieces after it read each.


def test_a_declaration_that_passes_is_typed_member_by_member() -> None:
    reads: list[JsonValue] = ["fluid.dynamic_viscosity", "bulk.density"]
    combined: list[JsonValue] = [reads]

    def change(declaration: Json) -> None:
        model(declaration).update(reads=reads, combinations=combined)
        model(declaration)["trainable"] = [{"field": reads[0], "record": WATER}]
        requirement(declaration).update(label="materica.fluid.newtonian.v1", review="reviewed")

    given = a_declaration(change)
    checked = Declaration.from_json(given)
    assert isinstance(checked, Declaration)
    entry, water = model(given), MaterialRef(**cast(dict[str, str], WATER))
    assert checked.consumer == given["consumer"]
    assert checked.operating_conditions == given["operating_conditions"]
    assert checked.given == given
    (typed,) = checked.models
    assert typed.index == 0
    assert (typed.name, typed.version) == ("drag", "1.0.0")
    assert typed.configuration_hash == entry["model_configuration_hash"]
    checked_over = cast(list[dict[str, str]], cast(Json, entry["checked_over"])["records"])
    assert typed.records == tuple(MaterialRef(**reference) for reference in checked_over)
    assert typed.target == entry["target"]
    assert typed.reads == tuple(reads)
    assert typed.combinations == (tuple(reads),)
    assert typed.trainable == ((reads[0], water),)
    assert typed.entry == entry
    (needed,) = typed.requirements
    assert (needed.field, needed.want) == (reads[0], "value")
    assert needed.conditions == requirement(given)["conditions"]
    assert (needed.label, needed.reviewed) == ("materica.fluid.newtonian.v1", True)
    (waiver,) = typed.acceptances
    assert (waiver.index, waiver.kind, waiver.location, waiver.field) == (0, "waiver", water, reads[0])
    assert waiver.members == acceptances(given)[0]


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
    # A code refused as a token is a member at fault, and the condition it would name is not judged against
    # it: one refusal, at the `code`, whether or not the waiver names a condition.
    assert refusals(waived("condition_unknown_name", None)) == {("BC-048", "/models/0/acceptances/0/code")}
    assert refusals(waived("condition_unknown_name", "temperature")) == {
        ("BC-048", "/models/0/acceptances/0/code")
    }
    assert refusals(waived("no_requirement", "temperature")) == {
        ("BC-048", "/models/0/acceptances/0/condition")
    }
    assert isinstance(Declaration.from_json(waived("no_requirement", None)), Declaration)
    assert isinstance(Declaration.from_json(waived("at_edge", "temperature")), Declaration)


def test_an_empty_reads_is_a_reads_at_fault_and_nothing_beside_it_is_refused_as_not_read() -> None:
    """BC-048 wants at least one entry in `reads`: that member is the fault, and a requirement, a combination
    and a `trainable` entry naming a field are not also judged against the list (the second review's default).
    The control: the same declaration beside a `reads` that is a list and lacks the fields."""
    fields: list[JsonValue] = ["fluid.dynamic_viscosity", "bulk.density"]

    def reading(reads: list[JsonValue]) -> Callable[[Json], object]:
        def change(declaration: Json) -> None:
            model(declaration).update(reads=reads, combinations=[fields])
            model(declaration)["trainable"] = [{"field": fields[0], "record": WATER}]

        return change

    assert isinstance(Declaration.from_json(a_declaration(reading(fields))), Declaration)
    assert refusals(a_declaration(reading([]))) == {("BC-048", "/models/0/reads")}
    # What does not depend on `reads` is still checked: a combined name that is no registered field.
    unregistered = a_declaration(
        lambda d: model(d).update(reads=[], combinations=[["fluid.dynamic_viscosity", "no.such_field"]])
    )
    assert refusals(unregistered) == {("BC-048", "/models/0/reads"), ("BC-048", "/models/0/combinations/0/1")}
    elsewhere = refusals(a_declaration(reading(["magnetic.remanence"])))
    assert elsewhere == {
        ("BC-048", "/models/0/requirements/0/field"),
        ("BC-048", "/models/0/combinations/0/0"),
        ("BC-048", "/models/0/combinations/0/1"),
        ("BC-048", "/models/0/trainable/0/field"),
    }


# An acceptance of no kind, or of one that is no kind, is refused at itself and none of its other members is
# judged (the second review's default): not an unknown member, a type, a token, a `reason` missing or a
# location, whichever kind the member would belong to.

FAULTY_MEMBERS: Json = {"field": "no.such_field", "index": 0.5, "value": "text", "foo": 1, "reason": ""}


@pytest.mark.parametrize(
    ("kind", "pointer"),
    [
        (None, "/models/0/acceptances/1"),
        ("no_such_kind", "/models/0/acceptances/1/acceptance"),
        ("Pick", "/models/0/acceptances/1/acceptance"),
        (3.0, "/models/0/acceptances/1/acceptance"),
        (["pick"], "/models/0/acceptances/1/acceptance"),
    ],
)
def test_an_acceptance_of_no_known_kind_is_refused_at_itself_alone(kind: JsonValue, pointer: str) -> None:
    given: Json = {} if kind is None else {"acceptance": kind}
    declaration = a_declaration(lambda d: acceptances(d).append(given | FAULTY_MEMBERS))
    assert refusals(declaration) == {("BC-048", pointer)}
    no_reason = a_declaration(lambda d: acceptances(d).append(given | {"value": 1.0}))
    assert refusals(no_reason) == {("BC-048", pointer)}


def test_an_acceptance_of_a_known_kind_has_its_members_judged_beside_the_same_faults() -> None:
    """The control: the faults of the cases above, under a kind, are each refused, so those could fail."""
    pick: Json = {"acceptance": "pick"}
    found = refusals(a_declaration(lambda d: acceptances(d).append(pick | FAULTY_MEMBERS)))
    assert {pointer for _, pointer in found} >= {
        f"/models/0/acceptances/1/{name}" for name in ("field", "index", "value", "foo", "reason")
    }


# Each constraint's boundary, a number's JSON type (`true` is none), a status object's members and a
# population level's `within`; then the rules on names, tokens and shapes the text states. Each row: a change
# and the refusals it gives, none where the declaration is taken.


def sampling(min_acceptance: JsonValue, represents: str | None = None) -> Callable[[Json], object]:
    def change(declaration: Json) -> None:
        declaration["sampling"] = {"min_acceptance": min_acceptance, "reason": "a reason", "independence": []}
        if represents is not None:
            requirement(declaration)["represents"] = represents

    return change


def no_block(declaration: Json) -> None:
    sampling(0.5, "measurement")(declaration)
    declaration["sampling"] = "a block"


def within(held: JsonValue) -> Callable[[Json], object]:
    def change(declaration: Json) -> None:
        sampling(0.5, "population")(declaration)
        requirement(declaration)["population_level"] = {"level": "donor", "within": held}

    return change


Refusals = set[tuple[str, str]]
AT = "/models/0/requirements/0"
BLOCK: Refusals = {("BC-051", "/sampling")}
LEVEL: Refusals = BLOCK | {("BC-051", f"{AT}/represents"), ("BC-051", f"{AT}/population_level")}
DIFFERENCE: Json = {"acceptance": "accepted_difference", "section": "fluid", "fact": "species"}
BOUNDARIES: list[tuple[Callable[[Json], object], Refusals]] = [
    # `min_acceptance` in (0, 1]: by its Holds where no requirement samples, by item 8 where one does.
    (sampling(1.0), BLOCK),
    (sampling(0.0), BLOCK | {("BC-048", "/sampling/min_acceptance")}),
    (sampling(1.0000001), BLOCK | {("BC-048", "/sampling/min_acceptance")}),
    (sampling(True), BLOCK | {("BC-048", "/sampling/min_acceptance")}),
    (sampling(0.0, "measurement"), BLOCK | {("BC-044", "/sampling/min_acceptance")}),
    (sampling("one half", "measurement"), BLOCK | {("BC-044", "/sampling/min_acceptance")}),
    (no_block, {("BC-044", "/sampling")}),
    # A number and a string of the JSON types their rows give.
    (lambda d: tolerance(d).update(value=True), {("BC-048", f"{AT}/conditions/temperature/tolerance/value")}),
    (
        lambda d: model(d).update(model_configuration_hash=1.0),
        {("BC-048", "/models/0/model_configuration_hash")},
    ),
    # An UBERON identifier holds its digits.
    (
        lambda d: model(d).update(target={"anatomical_site": {"uberon": "UBERON:"}}),
        {("BC-048", "/models/0/target/anatomical_site/uberon")},
    ),
    (lambda d: model(d).update(target={"anatomical_site": {"uberon": "UBERON:0000948"}}), set()),
    # A status object holds `status` and, beside it, `reason` at most.
    (appended(DIFFERENCE, value={"status": "not_applicable", "reason": "water has none"}), set()),
    # A population level's `within`: a level, or the status object `none`.
    (within({"status": "none"}), LEVEL),
    (within("lot"), LEVEL),
    (within({"status": "unstated"}), LEVEL | {("BC-048", f"{AT}/population_level/within/status")}),
    (within("lots"), LEVEL | {("BC-048", f"{AT}/population_level/within")}),
]


@pytest.mark.parametrize(("change", "expected"), BOUNDARIES)
def test_each_constraint_judges_its_boundary_and_each_type_its_own(
    change: Callable[[Json], object], expected: Refusals
) -> None:
    declaration = a_declaration(change)
    if not expected:
        assert isinstance(Declaration.from_json(declaration), Declaration)
    else:
        assert refusals(declaration) == expected


MAGNETIC: list[JsonValue] = ["magnetic.remanence", "magnetic.saturation_magnetisation"]
TRAINABLE: Json = {"field": "fluid.dynamic_viscosity", "record": WATER}
NO_FIELD: list[JsonValue] = [1.0]
IMPLIED: Json = {
    "acceptance": "implied_condition",
    "record": WATER,
    "field": "fluid.dynamic_viscosity",
    "fact": "tissue_state",
    "token": "in_vivo",
    "implies": {"temperature": {"value": 310.15, "unit": "C"}},
}
NOMINAL: Json = {
    "acceptance": "nominal",
    "record": WATER,
    "field": "fluid.dynamic_viscosity",
    "basis": "a basis",
}
SCOPE: Json = {"acceptance": "overlay_scope", "overlay": WATER, "accepts": ["consumer", "consumer"]}
ELSEWHERE: Json = {"id": "conformance/another_fixture", "version": "1.0.0", "content_hash": "sha256:0"}


def entries(**members: JsonValue) -> Callable[[Json], object]:
    return lambda declaration: model(declaration).update(members)


NAMES: list[tuple[Callable[[Json], object], Refusals]] = [
    # A combination: two or more fields in `reads`, of different sections.
    (entries(combinations=[["fluid.dynamic_viscosity"]]), {("BC-048", "/models/0/combinations/0")}),
    # One entry, and it no field: fewer than two fields, whatever its sections; the entry refused at itself.
    (
        entries(combinations=[NO_FIELD]),
        {("BC-048", "/models/0/combinations/0"), ("BC-048", "/models/0/combinations/0/0")},
    ),
    (
        entries(reads=["fluid.dynamic_viscosity", *MAGNETIC], combinations=[MAGNETIC]),
        {("BC-048", "/models/0/combinations/0")},
    ),
    (
        entries(
            reads=["fluid.dynamic_viscosity", *MAGNETIC],
            combinations=[[MAGNETIC[0], "fluid.dynamic_viscosity"]],
        ),
        set(),
    ),
    # An implied condition's value in its condition's registered unit; a token condition's accept list of its
    # row's tokens.
    (appended(IMPLIED), {("BC-048", "/models/0/acceptances/1/implies/temperature/unit")}),
    (
        lambda d: conditions(d).update(test_method={"accept": ["a_rheometer"], "reason": "a reason"}),
        {("BC-048", f"{AT}/conditions/test_method/accept/0")},
    ),
    # A distribution's parameters its token's, none missing (and the sampling suite's member, item 12).
    (
        appended(DISTRIBUTION, distribution_parameters={"mean": 0.000692}),
        {
            ("BC-051", "/models/0/acceptances/1"),
            ("BC-048", "/models/0/acceptances/1/distribution_parameters"),
        },
    ),
    # An `overlay_scope`'s `accepts`, none twice; two `trainable` entries for one field at one location;
    # `params` only for a field whose row allows a parameter set, which no field of 0.1.0 does.
    (appended(SCOPE), {("BC-048", "/models/0/acceptances/1/accepts")}),
    (
        entries(trainable=[TRAINABLE, TRAINABLE]),
        {("BC-048", "/models/0/trainable/1")},
    ),
    (appended(NOMINAL, params={"a": 1.0}), {("BC-048", "/models/0/acceptances/1/params")}),
    # An accepted difference's value of its fact's shape.
    (
        appended(DIFFERENCE, value={"ncbi_taxon": "human"}),
        {("BC-048", "/models/0/acceptances/1/value/ncbi_taxon")},
    ),
    # A requirement for a field the build does not register: its `label` is not judged against it.
    (
        lambda d: requirement(d).update(field="fluid.viscosity", label="materica.fluid.newtonian.v1"),
        {("BC-048", f"{AT}/field")},
    ),
    # The registered fields a `mixing` rule and a `families` entry name, and a mixing rule's token: a valid
    # rule is taken, a field with no parameter set (every field of 0.1.0) is no family's.
    (
        entries(mixing={"fraction_sum_tolerance": 0.0, "rules": {"fluid.dynamic_viscosity": "identity"}}),
        set(),
    ),
    (
        entries(mixing={"fraction_sum_tolerance": 0.0, "rules": {"fluid.dynamic_viscosity": "bogus"}}),
        {("BC-048", "/models/0/mixing/rules/fluid.dynamic_viscosity")},
    ),
    (
        entries(families={"fluid.dynamic_viscosity": "a family"}),
        {("BC-048", "/models/0/families/fluid.dynamic_viscosity")},
    ),
    # Checked over a domain and records, two alternatives: no `trainable` record is judged against them.
    (
        entries(
            checked_over={"domain": "lumen", "records": [WATER]},
            trainable=[{"field": "fluid.dynamic_viscosity", "record": ELSEWHERE}],
        ),
        {("BC-048", "/models/0/checked_over"), ("BC-051", "/models/0/checked_over/domain")},
    ),
]


@pytest.mark.parametrize(("change", "expected"), NAMES)
def test_each_rule_on_names_tokens_and_shapes_the_text_states_holds(
    change: Callable[[Json], object], expected: Refusals
) -> None:
    declaration = a_declaration(change)
    if not expected:
        assert isinstance(Declaration.from_json(declaration), Declaration)
    else:
        assert refusals(declaration) == expected


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


def test_a_trainable_entry_at_a_record_and_a_region_is_one_refusal_of_item_12_and_a_region_over_records() -> (
    None
):
    """Item 12 refuses the entry once, whichever locations it names; its region, where the model is checked
    over records, is also a location the model is not checked over: BC-048 at the region."""
    entry: Json = {"field": "fluid.dynamic_viscosity", "record": WATER, "region": "lumen"}
    assert refusals(a_declaration(lambda d: model(d).update(trainable=[entry]))) == {
        ("BC-051", "/models/0/trainable/0"),
        ("BC-048", "/models/0/trainable/0/region"),
    }


# A member of another JSON type is refused at itself, and nothing inside it is checked (section 1): a member
# holding a token, one holding a list of tokens and one keyed by names, each given a container of no tokens.


def a_code_of_another_type_with_no_condition(declaration: Json) -> None:
    """No `condition` beside the code: one beside a code that names none is refused whichever code it is."""
    waiver = cast(Json, acceptances(declaration)[0])
    waiver.update(code=["condition_unstate"])
    waiver.pop("condition")


OTHER_TYPES: list[tuple[Callable[[Json], object], str]] = [
    (lambda d: requirement(d).update(want={"status": "unstated"}), "/models/0/requirements/0/want"),
    (a_code_of_another_type_with_no_condition, "/models/0/acceptances/0/code"),
    (lambda d: model(d).update(reads={"status": "unstated"}), "/models/0/reads"),
    (
        lambda d: conditions(d).update(test_method={"accept": {"method": "a_method"}, "reason": "a reason"}),
        "/models/0/requirements/0/conditions/test_method/accept",
    ),
    (lambda d: model(d).update(target=["specie"]), "/models/0/target"),
    (lambda d: d.update(operating_conditions=["pressure"]), "/operating_conditions"),
    (
        lambda d: model(d).update(mixing={"fraction_sum_tolerance": 0.0, "rules": ["fluid.viscosity"]}),
        "/models/0/mixing/rules",
    ),
]


@pytest.mark.parametrize(("change", "pointer"), OTHER_TYPES)
def test_a_member_of_another_json_type_is_refused_at_itself_alone(
    change: Callable[[Json], object], pointer: str
) -> None:
    assert refusals(a_declaration(change)) == {("BC-048", pointer)}


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


# An engine value without its `reason` or `basis` is one fault, which item 7 and the shape's required members
# both name: BC-040 at the model's `engine` and none at the value (the refusal paragraph). A member of the
# value that item 7 does not judge (its `value`), and an empty `reason`, are refused at the value, BC-048's.

ENGINE = "/models/0/engine"
ENGINE_VALUES: list[tuple[Json, Json | None, Refusals]] = [
    ({"mu": {"value": 1.0, "reason": "r", "basis": "b"}}, None, {("BC-040", ENGINE)}),
    ({"mu": {"value": 1.0, "reason": "r"}}, None, {("BC-040", ENGINE)}),
    ({"mu": {"value": 1.0, "basis": "b"}}, None, {("BC-040", ENGINE)}),
    ({"mu": {"value": 1.0}}, None, {("BC-040", ENGINE)}),
    ({}, {"lumen": {"mu": {"value": 1.0, "reason": "r"}}}, {("BC-040", ENGINE)}),
    ({"mu": {"reason": "r", "basis": "b"}}, None, {("BC-040", ENGINE), ("BC-048", f"{ENGINE}/values/mu")}),
    (
        {"mu": {"value": 1.0, "reason": "", "basis": "b"}},
        None,
        {("BC-040", ENGINE), ("BC-048", f"{ENGINE}/values/mu/reason")},
    ),
]


@pytest.mark.parametrize(("values", "region_values", "expected"), ENGINE_VALUES)
def test_an_engine_value_without_reason_or_basis_is_item_7s_alone_at_the_engine(
    values: Json, region_values: Json | None, expected: Refusals
) -> None:
    def change(declaration: Json) -> None:
        engine(declaration)
        pinned = cast(Json, model(declaration)["engine"])
        pinned["values"] = values
        if region_values is not None:
            pinned["region_values"] = region_values

    assert refusals(a_declaration(change)) == expected


def test_item_7_finds_an_engine_values_missing_member_whatever_the_crosswalk() -> None:
    """With no crosswalk pinned and the model over a domain, item 7 has no other fault to find: BC-040 at the
    `engine` is then its finding of the value alone, in `values` and in `region_values`; without one, item 12
    refuses the engine (USD read not claimed), and the missing crosswalk is BC-048's."""

    def without_crosswalk(values: Json, region_values: Json) -> Json:
        def change(declaration: Json) -> None:
            model(declaration)["checked_over"] = {"domain": "lumen"}
            model(declaration)["engine"] = {"values": values, "region_values": region_values}

        return a_declaration(change)

    complete: Json = {"value": 1.0, "reason": "r", "basis": "b"}
    around = {("BC-048", ENGINE), ("BC-051", "/models/0/checked_over/domain")}
    assert refusals(without_crosswalk({"mu": complete}, {"lumen": {"mu": complete}})) == around | {
        ("BC-051", ENGINE)
    }
    assert refusals(without_crosswalk({"mu": {"value": 1.0, "reason": "r"}}, {})) == around | {
        ("BC-040", ENGINE)
    }
    assert refusals(without_crosswalk({}, {"lumen": {"mu": {"value": 1.0, "basis": "b"}}})) == around | {
        ("BC-040", ENGINE)
    }


# The check beside the build's reference model (the rulings of 2026-10-26): where the two read the text apart,
# and what the text now says. Each test holds a control, a declaration the same rule judges the other way, so
# that it can fail.

LABEL = "materica.fluid.newtonian.v1"
UNLISTED: Json = {"id": "conformance/unlisted", "version": "1.0.0", "content_hash": "sha256:" + "0" * 64}
WAIVER = "/models/0/acceptances/0"


def waiver_of(declaration: Json) -> Json:
    return cast(Json, acceptances(declaration)[0])


def reviewed(named: bool) -> Callable[[Json], object]:
    def change(declaration: Json) -> None:
        requirement(declaration).update(review="reviewed")
        if not named:
            requirement(declaration).pop("label")

    return change


def unreviewed(named: bool) -> Callable[[Json], object]:
    def change(declaration: Json) -> None:
        if not named:
            requirement(declaration).pop("label")

    return change


def no_requirement(declaration: Json) -> None:
    model(declaration).pop("requirements")


# A waiver's `label` beside the requirement for its field: in each of the five situations.
LABEL_SITUATIONS: dict[str, tuple[Callable[[Json], object], bool]] = {
    "reviewed, naming no label": (reviewed(False), False),
    "unreviewed, naming no label": (unreviewed(False), False),
    "reviewed, naming the label": (reviewed(True), True),
    "unreviewed, naming the label": (unreviewed(True), False),
    "no requirement": (no_requirement, False),
}
NO_STRING: list[JsonValue] = [None, 1.0, True, ["x"], {}]


@pytest.mark.parametrize("label", NO_STRING, ids=["null", "number", "true", "list", "object"])
@pytest.mark.parametrize("situation", list(LABEL_SITUATIONS))
def test_a_waivers_label_that_is_no_string_names_no_label_and_is_bc_048_alone_in_every_situation(
    situation: str, label: JsonValue
) -> None:
    """The member of another type is refused at itself and BC-050 judges nothing against it, beside a
    requirement that names no label as beside one that does (maintainer, 2026-10-24)."""
    change, _ = LABEL_SITUATIONS[situation]

    def given(declaration: Json) -> None:
        waiver_of(declaration).update(label=label)
        change(declaration)

    assert refusals(a_declaration(given)) == {("BC-048", f"{WAIVER}/label")}


@pytest.mark.parametrize("situation", list(LABEL_SITUATIONS))
def test_a_waivers_label_that_is_a_string_is_still_judged_in_every_situation(situation: str) -> None:
    """The control of the test above: the same waiver with a label that is a string is BC-050's at the `label`
    wherever the requirement does not name it and hold `review: "reviewed"`, and is taken where it does."""
    change, taken = LABEL_SITUATIONS[situation]

    def given(declaration: Json) -> None:
        waiver_of(declaration).update(label=LABEL)
        change(declaration)

    declaration = a_declaration(given)
    if taken:
        assert isinstance(Declaration.from_json(declaration), Declaration)
    else:
        assert refusals(declaration) == {("BC-050", f"{WAIVER}/label")}


@pytest.mark.parametrize("code", [None, 1.0, ["condition_unstated"], {}, "not_a_reason"])
def test_a_condition_beside_a_code_that_names_none_is_refused_whichever_value_the_code_holds(
    code: JsonValue,
) -> None:
    """What a faulty member's own type settles whichever value it holds is still judged (section 1): the
    `condition` is refused at itself, and the `code` at fault is refused at itself."""
    declaration = a_declaration(lambda d: waiver_of(d).update(code=code))
    assert refusals(declaration) == {("BC-048", f"{WAIVER}/code"), ("BC-048", f"{WAIVER}/condition")}
    assert isinstance(Declaration.from_json(a_declaration()), Declaration)  # the control: a code naming one


def test_a_condition_beside_a_missing_code_is_refused_and_the_missing_code_too() -> None:
    declaration = a_declaration(lambda d: waiver_of(d).pop("code"))
    assert refusals(declaration) == {("BC-048", WAIVER), ("BC-048", f"{WAIVER}/condition")}


@pytest.mark.parametrize("code", [None, 1.0, ["condition_unstated"]])
def test_a_missing_condition_beside_a_code_that_is_no_string_is_not_judged(code: JsonValue) -> None:
    """The other half of the stand-aside, which depends on the code: a code at fault is not judged to need a
    condition, so the refusal is the `code`'s alone."""

    def given(declaration: Json) -> None:
        waiver_of(declaration).update(code=code)
        waiver_of(declaration).pop("condition")

    assert refusals(a_declaration(given)) == {("BC-048", f"{WAIVER}/code")}


def entry_at(**location: JsonValue) -> Json:
    return {"field": "fluid.dynamic_viscosity"} | location


@pytest.mark.parametrize("field", [1.0, None, ["x"]], ids=["number", "null", "list"])
def test_a_trainable_entrys_location_is_judged_beside_a_field_that_is_no_string(field: JsonValue) -> None:
    """The location rule judges the record against `checked_over`, not against the field."""
    at = "/models/0/trainable/0"
    entry: Json = {"field": field, "record": UNLISTED}
    declaration = a_declaration(lambda d: model(d).update(trainable=[entry]))
    assert refusals(declaration) == {("BC-048", f"{at}/field"), ("BC-048", f"{at}/record")}
    missing = a_declaration(lambda d: model(d).update(trainable=[{"record": UNLISTED}]))
    assert refusals(missing) == {("BC-048", at), ("BC-048", f"{at}/record")}
    # The control: a record the model is checked over is not refused, beside the same field at fault.
    listed = a_declaration(lambda d: model(d).update(trainable=[{"field": field, "record": WATER}]))
    assert refusals(listed) == {("BC-048", f"{at}/field")}


def test_a_trainable_entry_with_no_name_is_never_given_twice() -> None:
    """R1 (an entry that is no well-formed name is neither the same as nor different from another), for the
    two members of an entry's name: the field and the reference."""
    first, second = "/models/0/trainable/0", "/models/0/trainable/1"
    no_field: list[JsonValue] = [{"field": 1.0, "record": WATER}, {"field": 1.0, "record": WATER}]
    assert refusals(a_declaration(lambda d: model(d).update(trainable=no_field))) == {
        ("BC-048", f"{first}/field"),
        ("BC-048", f"{second}/field"),
    }
    no_reference: Json = cast(Json, WATER) | {"id": None}
    unnamed: list[JsonValue] = [entry_at(record=no_reference), entry_at(record=no_reference)]
    assert refusals(a_declaration(lambda d: model(d).update(trainable=unnamed))) == {
        ("BC-048", f"{first}/record/id"),
        ("BC-048", f"{second}/record/id"),
    }
    no_region: list[JsonValue] = [entry_at(region=1.0), entry_at(region=1.0)]
    assert refusals(a_declaration(lambda d: model(d).update(trainable=no_region))) == {
        ("BC-048", f"{first}/region"),
        ("BC-048", f"{second}/region"),
        ("BC-051", first),
        ("BC-051", second),
    }
    # The control: two entries that are well-formed names and the same are given twice, at the later.
    same: list[JsonValue] = [entry_at(record=WATER), entry_at(record=WATER)]
    assert refusals(a_declaration(lambda d: model(d).update(trainable=same))) == {("BC-048", second)}


def test_a_trainable_entrys_record_is_compared_by_its_reference() -> None:
    """Two entries naming one field at one reference are given twice, though one copy of the record holds a
    member the table does not name (refused at itself, nothing else inside it)."""
    stray = cast(Json, WATER) | {"stray": 1.0}
    entries: list[JsonValue] = [entry_at(record=WATER), entry_at(record=stray)]
    assert refusals(a_declaration(lambda d: model(d).update(trainable=entries))) == {
        ("BC-048", "/models/0/trainable/1"),
        ("BC-048", "/models/0/trainable/1/record/stray"),
    }
    # A record the model is checked over, named with a member the table does not name, is checked over.
    assert refusals(a_declaration(lambda d: model(d).update(trainable=[entry_at(record=stray)]))) == {
        ("BC-048", "/models/0/trainable/0/record/stray")
    }


CHECKED_OVER = "/models/0/checked_over"
TRAINABLE_0 = "/models/0/trainable/0"
INTERVAL: JsonValue = [0.0, 1.0]


@pytest.mark.parametrize("scene", [{"domain": "lumen"}, {"path": "vessel"}], ids=["domain", "path"])
def test_a_trainable_entry_at_a_record_is_at_a_location_a_model_over_a_scene_is_not_checked_over(
    scene: Json,
) -> None:
    """A record is the location over records (`declarations.md` section 2 item 2); over a scene it is a
    location the model is not checked over: BC-048 at the record, beside item 12's refusal of the scene."""
    (name,) = scene
    declaration = a_declaration(
        lambda d: model(d).update(checked_over=scene, trainable=[entry_at(record=WATER)])
    )
    assert refusals(declaration) == {
        ("BC-051", f"{CHECKED_OVER}/{name}"),
        ("BC-048", f"{TRAINABLE_0}/record"),
    }
    # The control: the same entry over records that list it is taken, and the scene alone is item 12's.
    assert isinstance(
        Declaration.from_json(a_declaration(lambda d: model(d).update(trainable=[entry_at(record=WATER)]))),
        Declaration,
    )
    assert refusals(a_declaration(lambda d: model(d).update(checked_over=scene))) == {
        ("BC-051", f"{CHECKED_OVER}/{name}")
    }


@pytest.mark.parametrize(("name", "held"), [("region", "lumen"), ("interval", INTERVAL)])
def test_a_trainable_entry_at_a_region_or_an_interval_is_at_a_location_a_model_over_records_has_not(
    name: str, held: JsonValue
) -> None:
    """Over records the location is the record read, neither a region nor an interval: BC-048 at the location,
    beside item 12's refusal of the entry. The control: over a scene the same entry is item 12's alone (the
    scene suite owns which regions and intervals the model is checked over)."""
    declaration = a_declaration(lambda d: model(d).update(trainable=[entry_at(**{name: held})]))
    assert refusals(declaration) == {("BC-051", TRAINABLE_0), ("BC-048", f"{TRAINABLE_0}/{name}")}
    over_a_scene = a_declaration(
        lambda d: model(d).update(checked_over={"domain": "lumen"}, trainable=[entry_at(**{name: held})])
    )
    assert refusals(over_a_scene) == {("BC-051", f"{CHECKED_OVER}/domain"), ("BC-051", TRAINABLE_0)}


@pytest.mark.parametrize(
    "checked_over",
    [{"domain": "lumen", "records": [WATER]}, {}, {"records": "water"}],
    ids=["two alternatives", "none", "another type"],
)
def test_a_model_checked_over_nothing_in_particular_has_no_location_kind_to_judge(checked_over: Json) -> None:
    """`checked_over` holding two alternatives, none, or a member of another type is a member at fault, and a
    `trainable` entry's location kind is not judged against it (the control: the tests above, where the model
    is checked over a scene, refuse the same record)."""
    declaration = a_declaration(
        lambda d: model(d).update(checked_over=checked_over, trainable=[entry_at(record=WATER)])
    )
    found = refusals(declaration)
    assert ("BC-048", f"{TRAINABLE_0}/record") not in found
    assert any(pointer.startswith(CHECKED_OVER) for _, pointer in found)


WITHIN = f"{AT}/population_level/within"
WITHIN_OBJECTS: list[tuple[JsonValue, Refusals]] = [
    ({"status": "none", "x": 1.0}, {("BC-048", f"{WITHIN}/x")}),
    ({"status": "none", "reason": 1.0}, {("BC-048", f"{WITHIN}/reason")}),
    ({"status": None}, {("BC-048", f"{WITHIN}/status")}),
    ({"status": "other"}, {("BC-048", f"{WITHIN}/status")}),
    ({"status": "unstated"}, {("BC-048", f"{WITHIN}/status")}),
    ({"x": 1.0}, {("BC-048", WITHIN), ("BC-048", f"{WITHIN}/x")}),
    ({}, {("BC-048", WITHIN)}),
    ({"status": "none", "reason": "no level below"}, set()),
    ({"status": "none"}, set()),
]


@pytest.mark.parametrize(("held", "expected"), WITHIN_OBJECTS)
def test_a_within_object_is_a_status_object_whose_one_status_is_none(
    held: JsonValue, expected: Refusals
) -> None:
    """`within` is a level or `{"status": "none"}` (`uncertainty.md` section 1), and a status object is an
    object whose only members are `status` and, optionally, a `reason` that is a text (`provenance.md` section
    1): a member of it that is none of these is refused at itself, as an accepted difference's value is."""
    assert refusals(a_declaration(within(held))) == LEVEL | expected


def test_the_member_of_a_condition_that_its_kind_does_not_take_is_refused_with_nothing_inside_it() -> None:
    """`tolerance` is for a numeric condition and `accept` for a token one (the table's Holds): for the other
    kind it is a member the table does not name here, refused at itself with nothing inside it checked."""
    at = f"{AT}/conditions"
    slab: Json = {"value": -1.0, "unit": "m", "slab": 1.0}
    token = a_declaration(
        lambda d: conditions(d).update(test_method={"tolerance": slab, "reason": "a reason"})
    )
    assert refusals(token) == {("BC-048", f"{at}/test_method/tolerance")}
    numeric = a_declaration(lambda d: condition(d, "temperature").update(accept=[1.0]))
    assert refusals(numeric) == {("BC-048", f"{at}/temperature"), ("BC-048", f"{at}/temperature/accept")}
    # The controls: inside the member the kind does take, the same faults are found.
    inside = a_declaration(
        lambda d: conditions(d).update(
            test_method={"accept": [1.0], "reason": "a reason"},
            temperature={"tolerance": slab, "reason": "a reason"},
        )
    )
    assert refusals(inside) == {
        ("BC-048", f"{at}/test_method/accept/0"),
        ("BC-048", f"{at}/temperature/tolerance/value"),
        ("BC-048", f"{at}/temperature/tolerance/slab"),
        ("BC-048", f"{at}/temperature/tolerance/unit"),
    }


COMBINABLE: list[JsonValue] = [
    "fluid.dynamic_viscosity",
    "bulk.density",
    "magnetic.remanence",
    "magnetic.saturation_magnetisation",
]
COMBINATIONS: list[tuple[list[JsonValue], Refusals]] = [
    # Two registered fields of one section are refused whatever else the list holds.
    (["magnetic.remanence", "magnetic.saturation_magnetisation"], {("BC-048", "/models/0/combinations/0")}),
    (
        ["magnetic.remanence", "magnetic.saturation_magnetisation", 1.0],
        {("BC-048", "/models/0/combinations/0"), ("BC-048", "/models/0/combinations/0/2")},
    ),
    (
        ["magnetic.remanence", "magnetic.saturation_magnetisation", "no.such_field"],
        {("BC-048", "/models/0/combinations/0"), ("BC-048", "/models/0/combinations/0/2")},
    ),
    # An entry that is no registered field has no section: one registered field is not a combination of one.
    (["magnetic.remanence", "magnetic.no_such_field"], {("BC-048", "/models/0/combinations/0/1")}),
    (["bulk.density", 1.0], {("BC-048", "/models/0/combinations/0/1")}),
    # A combination is refused only where all its registered fields are of one section.
    (["bulk.density", "magnetic.remanence", "magnetic.saturation_magnetisation"], set()),
    (["magnetic.remanence", "bulk.density"], set()),
]


@pytest.mark.parametrize(("combined", "expected"), COMBINATIONS)
def test_a_combination_of_registered_fields_of_one_section_is_refused_beside_an_entry_at_fault(
    combined: list[JsonValue], expected: Refusals
) -> None:
    declaration = a_declaration(lambda d: model(d).update(reads=COMBINABLE, combinations=[combined]))
    if not expected:
        assert isinstance(Declaration.from_json(declaration), Declaration)
    else:
        assert refusals(declaration) == expected
