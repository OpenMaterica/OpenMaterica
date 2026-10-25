# SPDX-License-Identifier: Apache-2.0
"""Examples of the build's reads over records (`declarations.md` section 2, S7a-2a): the build's own read
request (item 7), one result per model, listed record and field, in order, the acceptances a read applied
mapped to the model's indexes and checked against the build's terms, the label stored on the value a result
rests on (item 8), and what this version raises before and after the reads (the S7 design's 1.3). Each test
plants what a wrong build would do, beside the answer the text gives, where one example can show it."""

import copy
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import materica
from materica import shapes
from materica.core import build
from materica.core.build import Reading, check_build
from materica.core.conditions import ConditionEntry
from materica.core.declarations import CLAIMS, Acceptance, Declaration
from materica.core.hashing import content_hash
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult, read
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from scripts.gen_vocabulary import SPECIFICATION

# The build's internals these examples hold to the text, bound once.
results_of = build._results  # pyright: ignore[reportPrivateUsage]
given_to = build._given  # pyright: ignore[reportPrivateUsage]
request_for = build._request  # pyright: ignore[reportPrivateUsage]
located_at = build._located_at  # pyright: ignore[reportPrivateUsage]
applied_of = build._applied  # pyright: ignore[reportPrivateUsage]
GIVEN_KINDS = build._GIVEN_KINDS  # pyright: ignore[reportPrivateUsage]

BUILD_CHECKS = Path(materica.__file__).parent / "data" / "conformance" / "build_checks"
INPUTS = BUILD_CHECKS / "inputs"
Json = dict[str, JsonValue]
NEWTONIAN = "materica.fluid.newtonian.v1"
VISCOSITY, DENSITY = "fluid.dynamic_viscosity", "bulk.density"


def case(name: str) -> tuple[Json, RecordStore]:
    """A build-check file's declaration, as a value to change, and a store of its records."""
    document = json.loads((BUILD_CHECKS / "cases" / f"{name}.json").read_text(encoding="utf-8"))
    declaration: Json = json.loads((INPUTS / document["inputs"]["declaration"]).read_text(encoding="utf-8"))
    return declaration, materica.load_records([INPUTS / name for name in document["inputs"]["records"]])


def model(declaration: Json, index: int = 0) -> Json:
    return cast(list[Json], declaration["models"])[index]


def requirement(declaration: Json) -> Json:
    return cast(list[Json], model(declaration)["requirements"])[0]


def acceptances(declaration: Json) -> list[Json]:
    return cast(list[Json], model(declaration)["acceptances"])


def checked(declaration: Json) -> Declaration:
    taken = Declaration.from_json(declaration)
    assert isinstance(taken, Declaration), taken
    return taken


def readings(declaration: Json, store: RecordStore) -> list[Reading]:
    return results_of(checked(declaration), store, CLAIMS)


def only_read(declaration: Json, store: RecordStore) -> ReadResult:
    ((result, _, _),) = readings(declaration, store)
    assert result.read is not None
    return result.read


def request_of(declaration: Json, index: int = 0) -> Json:
    """The build's own request for the first record and the requirement `index` of the first model."""
    taken = checked(declaration)
    entry = taken.models[0]
    record, needed = entry.records[0], entry.requirements[index]
    given = given_to(entry.acceptances, record, needed.field)
    return cast(Json, request_for(taken.operating_conditions, record, needed, given))


def codes(result: ReadResult) -> set[str]:
    return {reason.code for reason in result.reasons}


# The build's own request (section 2 item 7): "the requirement's `want` and `conditions`, and the declared
# operating conditions", and the acceptances "of the kinds a read takes, overlays aside, that name the read's
# field and are located at its location".


def test_the_request_holds_the_requirements_want_and_conditions_and_no_label_or_review() -> None:
    declaration, store = case("BC-017.fills_an_unstated_condition")
    requirement(declaration)["review"] = "reviewed"
    assert requirement(declaration)["label"] == NEWTONIAN
    request = request_of(declaration)
    assert request["requirement"] == {"want": "value", "conditions": requirement(declaration)["conditions"]}
    assert "request_incomplete" not in codes(only_read(declaration, store))
    # The control: the read refuses the request the build would make were it to copy either member.
    for name in ("label", "review"):
        copied = copy.deepcopy(request)
        cast(Json, copied["requirement"])[name] = requirement(declaration)[name]
        assert "request_incomplete" in codes(read(copied, store)), name


def test_every_declared_operating_condition_is_given_a_tables_axis_the_requirement_does_not_name() -> None:
    """BC-019's table over temperature, read at 270 K under an extrapolation: its requirement names
    `density_kind` alone, and the temperature it is read at is the experiment's."""
    declaration, store = case("BC-019.outside_range_under_an_extrapolation")
    assert set(cast(Json, requirement(declaration)["conditions"])) == {"density_kind"}
    request = request_of(declaration)
    assert request["operating_conditions"] == declaration["operating_conditions"]
    result = only_read(declaration, store)
    assert result.value is not None, result.reasons
    assert result.assumption is not None
    # The control: without the temperature, the table has no operating value for its axis.
    dropped = {**request, "operating_conditions": {}}
    assert codes(read(dropped, store)) == {"request_incomplete"}


@pytest.mark.parametrize("want", ["value", "bounds"])
def test_the_requirements_want_is_given_as_declared(want: str) -> None:
    """BC-020's interval read with its nominal: `value` takes the nominal's value beside `want_mismatch`,
    `bounds` the interval's bounds, as stored."""
    declaration, store = case("BC-020.nominal_inside_the_bounds")
    requirement(declaration)["want"] = want
    assert cast(Json, request_of(declaration)["requirement"])["want"] == want
    result = only_read(declaration, store)
    if want == "value":
        assert (result.value, result.assumption) == (1180.0, {"acceptance": "nominal", "value": 1180.0})
        assert codes(result) == {"want_mismatch"}
    else:
        assert isinstance(result.value, dict)
        assert result.assumption is None
        assert "want_mismatch" not in codes(result)


ANOTHER_PIN = "sha256:" + "0" * 64
ELSEWHERE: list[tuple[str, Callable[[Json], object]]] = [
    ("another_version", lambda nominal: cast(Json, nominal["record"]).update(version="1.0.1")),
    ("another_content_hash", lambda nominal: cast(Json, nominal["record"]).update(content_hash=ANOTHER_PIN)),
    ("another_id", lambda nominal: cast(Json, nominal["record"]).update(id="conformance/water_fixture")),
    ("another_field", lambda nominal: nominal.update(field="fluid.dynamic_viscosity")),
]


@pytest.mark.parametrize("change", [change for _, change in ELSEWHERE], ids=[name for name, _ in ELSEWHERE])
def test_an_acceptance_at_another_record_or_for_another_field_is_not_given(
    change: Callable[[Json], object],
) -> None:
    declaration, store = case("BC-020.nominal_inside_the_bounds")
    at_the_read = only_read(declaration, store)
    assert at_the_read.assumption is not None
    change(acceptances(declaration)[0])
    assert request_of(declaration)["acceptances"] == []
    elsewhere = only_read(declaration, store)
    assert (elsewhere.value, elsewhere.assumption, codes(elsewhere)) == (None, None, {"want_mismatch"})


def test_an_acceptance_of_a_kind_a_read_does_not_take_is_not_given() -> None:
    """BC-016's waiver at the read's record and field: a read takes no waiver (`read_side_contract.md`
    section 1), which would refuse the request."""
    declaration, _ = case("BC-016.waiver_at_one_of_two_records")
    (waiver,) = acceptances(declaration)
    assert waiver["acceptance"] == "waiver"
    assert (
        waiver["record"]
        == cast(list[JsonValue], cast(Json, model(declaration)["checked_over"])["records"])[0]
    )
    assert request_of(declaration)["acceptances"] == []


def test_the_kinds_given_are_those_a_read_takes_overlays_and_trainable_aside() -> None:
    """`_GIVEN_KINDS` against `read_side_contract.md` section 1's sentence, read from the text."""
    text = " ".join((SPECIFICATION / "read_side_contract.md").read_text(encoding="utf-8").split())
    found = re.search(r"A request's `acceptances` take only the kinds ((?:`\w+`(?:, | and )?)+)", text)
    assert found is not None
    taken = re.findall(r"`(\w+)`", found.group(1))
    assert taken == ["pick", "overlay", "extrapolation", "nominal", "implied_condition", "trainable"]
    assert set(GIVEN_KINDS) == set(taken) - {"overlay", "trainable"}


def located(**members: JsonValue) -> Acceptance:
    water = MaterialRef("conformance/water_fixture", "1.0.0", ANOTHER_PIN)
    given: Json = {
        "acceptance": "nominal",
        "record": cast(Json, water.to_json()),
        "field": DENSITY,
        **members,
    }
    return Acceptance(0, "nominal", water, DENSITY, given)


def test_an_acceptance_at_a_region_or_an_interval_beside_the_record_is_located_at_no_record() -> None:
    """The build's terms: "one located at a region or an interval is located at no record". The build
    refuses either location without the scene suite (item 12), so a declaration cannot plant it here."""
    at_the_record = located()
    assert at_the_record.location is not None
    assert located_at(at_the_record, at_the_record.location)
    for beside in (located(region="lumen"), located(interval=0)):
        assert not located_at(beside, at_the_record.location)


# One result per model, listed record and field, in that order, and none for a record not listed (section
# 2; BC-002, BC-028). A field with no requirement is read for nothing (section 1 item 1).

WATER: Json = {
    "id": "conformance/water_fixture",
    "version": "1.0.0",
    "content_hash": "sha256:c21a2c7f46e66bcfb5e74f18d2a08644468d5a92bafb4fa57a03651facf96e2d",
}
GLYCEROL: Json = {
    "id": "conformance/glycerol_fixture",
    "version": "1.0.0",
    "content_hash": "sha256:53c34b5a18568f0ad10a1bf0be0ecef258a7f26048cf37c0fe8077c39af12b43",
}


def a_model(name: str, records: list[JsonValue], reads: list[JsonValue], required: list[str]) -> Json:
    return {
        "model": {"name": name, "version": "1.0.0"},
        "model_configuration_hash": "sha256:" + "1" * 64,
        "checked_over": {"records": records},
        "target": {},
        "reads": reads,
        "consumer_parameters": [],
        "requirements": [{"field": field, "want": "value"} for field in required],
        "families": {},
        "combinations": [],
        "acceptances": [],
        "chains": [],
    }


def two_models() -> Json:
    return {
        "consumer": {"name": "conformance_consumer", "version": "1.0.0"},
        "operating_conditions": {"temperature": {"value": 293.15, "unit": "K"}},
        "models": [
            a_model("drag", [GLYCEROL, WATER], [VISCOSITY, DENSITY], [VISCOSITY]),
            a_model("buoyancy", [WATER], [DENSITY], [DENSITY]),
        ],
    }


def test_one_result_per_model_listed_record_and_field_in_order_and_none_for_a_record_not_listed() -> None:
    store = materica.load_records([INPUTS / name for name in ("water_fixture.json", "glycerol_fixture.json")])
    store.add("density_table.json", (INPUTS / "density_table.json").read_bytes())
    found = [
        (result.model, result.record.to_json(), result.field)
        for result, _, _ in readings(two_models(), store)
    ]
    assert found == [
        ("drag", GLYCEROL, VISCOSITY),
        ("drag", GLYCEROL, DENSITY),
        ("drag", WATER, VISCOSITY),
        ("drag", WATER, DENSITY),
        ("buoyancy", WATER, DENSITY),
    ]


def test_a_field_with_no_requirement_is_read_for_nothing_and_every_other_is_read() -> None:
    store = materica.load_records([INPUTS / name for name in ("water_fixture.json", "glycerol_fixture.json")])
    found = {
        (result.model, result.record.id, result.field): result
        for result, _, _ in readings(two_models(), store)
    }
    assert {key for key, result in found.items() if result.read is None} == {
        ("drag", "conformance/glycerol_fixture", DENSITY),
        ("drag", "conformance/water_fixture", DENSITY),
    }
    water = found[("drag", "conformance/water_fixture", VISCOSITY)].read
    assert water is not None
    assert water.value == 0.000692
    glycerol = found[("drag", "conformance/glycerol_fixture", VISCOSITY)].read
    assert glycerol is not None
    assert codes(glycerol) == {"absent"}


def test_a_listed_record_absent_from_the_store_still_gives_its_result() -> None:
    declaration, store = case("BC-002.listed_record_absent_from_the_store")
    listed = cast(list[JsonValue], cast(Json, model(declaration)["checked_over"])["records"])
    assert [result.record.to_json() for result, _, _ in readings(declaration, store)] == listed
    assert any(
        result.read is not None and codes(result.read) == {"absent"}
        for result, _, _ in readings(declaration, store)
    )


# The acceptances a read applied, mapped to their indexes in the model's `acceptances` (item 7) and checked
# against the build's terms: "an implied condition that filled a condition (a `conditions` entry whose
# `record` is the value the implied condition supplies, with basis `implied`); a nominal or an extrapolation
# that the result's `assumption` names".

WAIVER: Json = {
    "acceptance": "waiver",
    "field": VISCOSITY,
    "condition": "shear_rate",
    "code": "condition_unstated",
    "reason": "a waiver the read is not given",
}


def test_an_applied_acceptance_is_mapped_to_its_index_in_the_models_acceptances() -> None:
    """BC-017's implied condition, after two waivers: the read is given it alone, first in its request."""
    declaration, store = case("BC-017.fills_an_unstated_condition")
    implied = acceptances(declaration)[0]
    acceptances(declaration)[:0] = [{**WAIVER, "record": implied["record"]}] * 2
    assert request_of(declaration)["acceptances"] == [implied]
    ((result, applied, _),) = readings(declaration, store)
    assert result.read is not None
    assert result.read.applied == (0,)
    assert applied == (2,)


def an_acceptance(kind: str, index: int = 3, **members: JsonValue) -> Acceptance:
    return Acceptance(index, kind, None, VISCOSITY, {"acceptance": kind, "field": VISCOSITY, **members})


IMPLIES_310: Json = {"temperature": {"value": 310.15, "unit": "K", "basis": "stated"}}
IMPLIED = an_acceptance("implied_condition", fact="tissue_state", token="in_vivo", implies=IMPLIES_310)
NOMINAL = an_acceptance("nominal", value=0.0007)
EXTRAPOLATION = an_acceptance("extrapolation", method="constant", law="held constant")


def with_temperature(record: Json, *, applied: tuple[int, ...] = (0,)) -> ReadResult:
    return ReadResult("met", (), (), (ConditionEntry("temperature", "met", record),), applied)


@pytest.mark.parametrize(
    ("result", "applied"),
    [
        pytest.param(with_temperature({"value": 310.15, "unit": "K", "basis": "implied"}), (3,), id="filled"),
        pytest.param(with_temperature({"value": 310.15, "unit": "K", "basis": "stated"}), (), id="stated"),
        pytest.param(
            with_temperature({"value": 309.15, "unit": "K", "basis": "implied"}), (), id="another_value"
        ),
        pytest.param(
            ReadResult("not_met", (Reason("condition_outside", "temperature"),), applied=(0,)), (), id="none"
        ),
        pytest.param(
            with_temperature({"value": 310.15, "unit": "K", "basis": "implied"}, applied=()),
            (),
            id="not_applied",
        ),
    ],
)
def test_an_implied_condition_counts_applied_only_where_its_value_filled_an_entry(
    result: ReadResult, applied: tuple[int, ...]
) -> None:
    assert applied_of(result, (IMPLIED,)) == applied


def test_two_implied_conditions_that_agree_each_count_applied_where_the_read_says_it_filled() -> None:
    """The second, of the same value, counts only where the read names it: the read alone knows which
    applied (its fact and token stated by the field's specimen)."""
    other = an_acceptance("implied_condition", 5, fact="tissue_state", token="in_vitro", implies=IMPLIES_310)
    filled: Json = {"value": 310.15, "unit": "K", "basis": "implied"}
    assert applied_of(with_temperature(filled, applied=(0, 1)), (IMPLIED, other)) == (3, 5)
    assert applied_of(with_temperature(filled, applied=(0,)), (IMPLIED, other)) == (3,)


@pytest.mark.parametrize(
    ("given", "assumption", "applied"),
    [
        pytest.param(NOMINAL, {"acceptance": "nominal", "value": 0.0007}, (3,), id="nominal_named"),
        pytest.param(NOMINAL, None, (), id="nominal_no_assumption"),
        pytest.param(NOMINAL, {"acceptance": "nominal", "value": 0.0008}, (), id="nominal_another_value"),
        pytest.param(
            EXTRAPOLATION,
            {"acceptance": "extrapolation", "method": "constant", "law": "held constant"},
            (3,),
            id="extrapolation_named",
        ),
        pytest.param(
            EXTRAPOLATION,
            {"acceptance": "extrapolation", "method": "constant", "law": "another law"},
            (),
            id="extrapolation_another_law",
        ),
        pytest.param(
            NOMINAL,
            {"acceptance": "extrapolation", "method": "constant", "law": "held constant"},
            (),
            id="nominal_under_an_extrapolation",
        ),
    ],
)
def test_a_nominal_or_an_extrapolation_counts_applied_only_where_the_assumption_names_it(
    given: Acceptance, assumption: Json | None, applied: tuple[int, ...]
) -> None:
    result = ReadResult(
        "not_met",
        (Reason("want_mismatch"),),
        applied=(0,),
        value=0.0007,
        assumption=cast("shapes.Assumption | None", assumption),
    )
    assert applied_of(result, (given,)) == applied


# The label and its basis as stored on the value a result rests on (item 8): "the field, or the alternative
# read", "whether or not the read reached step 12", and none "where the result rests on no stored value".


def test_the_label_is_read_from_the_record_as_stored_behind_a_refusal_before_step_12() -> None:
    """The water viscosity read at 330 K: step 10 ends the read, so the result holds no label, and the label
    stored on the field is the one the build checks."""
    declaration = two_models()
    declaration["operating_conditions"] = {"temperature": {"value": 330.0, "unit": "K"}}
    model(declaration)["requirements"] = [
        {
            "field": VISCOSITY,
            "want": "value",
            "conditions": {"temperature": {"tolerance": {"value": 1.0, "unit": "K"}, "reason": "r"}},
        }
    ]
    store = materica.load_records([INPUTS / "water_fixture.json", INPUTS / "glycerol_fixture.json"])
    found = {
        (result.record.id, result.field): (result, stored)
        for result, _, stored in readings(declaration, store)
    }
    result, stored = found[("conformance/water_fixture", VISCOSITY)]
    assert result.read is not None
    assert codes(result.read) == {"condition_outside", "condition_unstated"}
    assert result.read.labels == ()
    assert stored == {"label": NEWTONIAN}


def test_a_result_resting_on_no_stored_value_has_no_stored_label() -> None:
    """A listed record absent (BC-002), and a `want` of a suite the build does not claim, refused at step 0
    before the field is found, though the water viscosity stores its label."""
    declaration, store = case("BC-002.listed_record_absent_from_the_store")
    assert any(stored is None for _, _, stored in readings(declaration, store))
    declaration = two_models()
    model(declaration).update(checked_over={"records": [WATER]}, reads=[VISCOSITY])
    model(declaration)["requirements"] = [{"field": VISCOSITY, "want": "fit"}]
    del cast(list[Json], declaration["models"])[1]
    ((result, _, stored),) = readings(declaration, materica.load_records([INPUTS / "water_fixture.json"]))
    assert result.read is not None
    assert codes(result.read) == {"want_mismatch"}
    assert stored is None


def stored_water(field: JsonValue) -> tuple[Json, RecordStore]:
    """A water record holding `field` as its viscosity, pinned by its hash recomputed, a declaration over it
    with BC-016's requirement, and a store holding the record."""
    record: Json = json.loads((INPUTS / "water_fixture.json").read_text(encoding="utf-8"))
    cast(Json, cast(Json, cast(Json, record["body"])["sections"])["fluid"])["fields"] = {
        "dynamic_viscosity": field
    }
    record["content_hash"] = content_hash(record)
    store = RecordStore()
    store.add("water.json", json.dumps(record).encode())
    declaration, _ = case("BC-016.waiver_at_one_of_two_records")
    reference: Json = {name: record[name] for name in ("id", "version", "content_hash")}
    model(declaration)["checked_over"] = {"records": [reference]}
    model(declaration)["acceptances"] = []
    return declaration, store


def water_field(**members: JsonValue) -> Json:
    record: Json = json.loads((INPUTS / "water_fixture.json").read_text(encoding="utf-8"))
    field = cast(Json, cast(Json, cast(Json, cast(Json, record["body"])["sections"])["fluid"])["fields"])
    viscosity = cast(Json, field["dynamic_viscosity"])
    viscosity.pop("label")
    return viscosity | members


LABELLED: Json = {"label": NEWTONIAN, "label_basis": {"basis": "stated"}}


@pytest.mark.parametrize("left", [0, 1])
def test_the_label_is_the_one_alternative_lefts_and_never_the_fields(left: int) -> None:
    at_300_k = water_field(
        conditions={
            "temperature": {"value": 300.0, "unit": "K", "basis": "stated"},
            "shear_rate": {"status": "unstated"},
        }
    )
    alternatives: list[JsonValue] = [at_300_k, at_300_k]
    alternatives[left] = water_field(**LABELLED)
    declaration, store = stored_water({"alternatives": alternatives})
    ((result, _, stored),) = readings(declaration, store)
    assert result.read is not None
    assert result.read.resting_on == (left,), result.read.reasons
    assert stored == LABELLED


def test_a_field_with_no_label_stores_none_and_its_basis_is_given_where_stored() -> None:
    for field, label in ((water_field(), {}), (water_field(**LABELLED), LABELLED)):
        declaration, store = stored_water(field)
        ((_, _, stored),) = readings(declaration, store)
        assert stored == label


# What this version raises (the S7 design's 1.3): before any read, for a pick or an overlay (S7c), a
# non-empty `target` or `combinations` (S7a-3) and a non-empty `trainable` (S7a-4); past the reads, for what
# S7a-2b builds.


def no_read(request: object, store: object, *, claims: object) -> ReadResult:
    raise AssertionError("a read was made")


PICK: Json = {
    "acceptance": "pick",
    "field": VISCOSITY,
    "index": 0,
    "reason": "the alternative calibrated against",
}
OVERLAY: Json = {
    "acceptance": "overlay",
    "field": VISCOSITY,
    "overlay": WATER,
    "reason": "a dataset's overlay",
}
LATER: list[tuple[str, Callable[[Json], object], str]] = [
    (
        "pick",
        lambda d: acceptances(d).append({**PICK, "record": WATER}),
        "S7c reads the pick /models/0/acceptances/1",
    ),
    ("overlay", lambda d: acceptances(d).append(OVERLAY), "S7c reads the overlay /models/0/acceptances/1"),
    (
        "target",
        lambda d: model(d).update(target={"species": {"ncbi_taxon": 9606}}),
        "S7a-3 reads the target /models/0/target",
    ),
    (
        "combinations",
        lambda d: model(d).update(reads=[VISCOSITY, DENSITY], combinations=[[VISCOSITY, DENSITY]]),
        "S7a-3 reads the combinations /models/0/combinations",
    ),
    (
        "trainable",
        lambda d: model(d).update(trainable=[{"field": VISCOSITY, "record": WATER}]),
        "S7a-4 reads the trainable entry /models/0/trainable/0",
    ),
]


@pytest.mark.parametrize(
    ("change", "named"), [(change, named) for _, change, named in LATER], ids=[name for name, _, _ in LATER]
)
def test_what_a_later_piece_reads_raises_before_any_read(
    change: Callable[[Json], object], named: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    declaration, store = case("BC-016.waiver_at_one_of_two_records")
    change(declaration)
    checked(declaration)
    monkeypatch.setattr(build, "read", no_read)
    with pytest.raises(NotImplementedError) as raised:
        check_build(declaration, store)
    assert named in str(raised.value)


SCOPE: Json = {"acceptance": "overlay_scope", "overlay": WATER, "accepts": ["consumer"], "reason": "scoped"}
DIFFERENCE: Json = {
    "acceptance": "accepted_difference",
    "section": "fluid",
    "fact": "species",
    "value": {"status": "not_applicable"},
    "reason": "water has no species",
}


@pytest.mark.parametrize("acceptance", [SCOPE, DIFFERENCE], ids=["overlay_scope", "accepted_difference"])
def test_an_overlay_scope_and_an_accepted_difference_raise_only_past_the_reads(acceptance: Json) -> None:
    """With no overlay applied and an empty `target`, neither covers anything: S7a-2b lists each unused."""
    declaration, store = case("BC-016.waiver_at_one_of_two_records")
    acceptances(declaration).append(acceptance)
    made: list[object] = []

    def counted(request: object, store: RecordStore, *, claims: object) -> ReadResult:
        made.append(request)
        return read(cast(Json, request), store)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(build, "read", counted)
        with pytest.raises(NotImplementedError, match="S7a-2b") as raised:
            check_build(declaration, store)
    assert len(made) == len(cast(list[JsonValue], cast(Json, model(declaration)["checked_over"])["records"]))
    assert "S7c" not in str(raised.value)
    assert "S7a-3" not in str(raised.value)


def test_a_reads_own_raise_is_let_through() -> None:
    """A checked record that is an overlay, which the read raises for until S4c-1's role check (1.3)."""
    overlay = (
        Path(materica.__file__).parent
        / "data"
        / "conformance"
        / "plain_read"
        / "inputs"
        / "density_overlay.json"
    )
    record = json.loads(overlay.read_text(encoding="utf-8"))
    declaration = two_models()
    del cast(list[Json], declaration["models"])[1]
    reference: Json = {name: record[name] for name in ("id", "version", "content_hash")}
    model(declaration).update(
        checked_over={"records": [reference]},
        reads=[DENSITY],
        requirements=[{"field": DENSITY, "want": "value"}],
    )
    with pytest.raises(NotImplementedError, match="overlay is not built yet"):
        check_build(declaration, materica.load_records([overlay]))
