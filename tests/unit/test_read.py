# SPDX-License-Identifier: Apache-2.0
"""Examples at the edges of the read up to step 5, which the cases and properties reach rarely or not at
all: versions longer than `int` reads, the forms a request may be given in, the misuses that raise, and the
steps not built yet, which raise rather than answer."""

import copy
import dataclasses
import importlib
import inspect
import json
import math
import struct
from collections.abc import Callable, Collection
from pathlib import Path
from types import ModuleType
from typing import Any, cast, get_type_hints

import pytest

import materica
from materica import shapes
from materica.core import evaluate, value_shapes
from materica.core import read as read_module
from materica.core.conditions import ConditionEntry
from materica.core.hashing import content_hash
from materica.core.identifiers import FAMILY_ID, RECORD_ID, MaterialRef, Version, parse_version
from materica.core.jsonio import JsonValue
from materica.core.read import Extrapolation, FieldRead, FormRange, ReadRequest, ReadResult, read
from materica.core.reasons import Reason, merged
from materica.core.record import RecordStore
from materica.core.status import worst
from materica.core.value_shapes import FORM_MEMBERS, a_list, an_object
from materica.core.vocabulary import VOCABULARY
from materica.shapes import ReasonCode, Suite
from tests.spec_sync.schemas import validator

WATER = (
    Path(materica.__file__).parent / "data" / "conformance" / "plain_read" / "inputs" / "water_fixture.json"
)
PIN = "sha256:c21a2c7f46e66bcfb5e74f18d2a08644468d5a92bafb4fa57a03651facf96e2d"
REQUEST: shapes.ReadRequest = {
    "target": {
        "record": {"id": "conformance/water_fixture", "version": "2.0.0", "content_hash": PIN},
        "field": "fluid.dynamic_viscosity",
    },
    "operating_conditions": {"temperature": {"value": 310.15, "unit": "K"}},
    "requirement": {"want": "value", "conditions": {"temperature": {"tolerance": {"value": 1, "unit": "K"}}}},
}
ABSENT = ReadResult("not_met", (Reason("absent"),))


def with_members(**members: JsonValue) -> dict[str, JsonValue]:
    """REQUEST as parsed JSON, with `members` set at its top."""
    value: dict[str, JsonValue] = json.loads(json.dumps(REQUEST))
    return value | members


def store() -> RecordStore:
    return materica.load_records([WATER])


def test_components_beyond_ints_digit_limit_order_by_length_then_digits() -> None:
    longer = parse_version("1" + "0" * 5000 + ".0.0")
    shorter = parse_version("9" * 4999 + ".0.0")
    assert longer is not None
    assert shorter is not None
    assert shorter < longer
    ten = parse_version("0.10.0")
    assert ten is not None
    assert ten == Version("0", "10", "0")
    assert ten > Version("0", "9", "0")


@pytest.mark.parametrize(
    "components", [("01", "0", "0"), ("1", "00", "0"), ("1", "0", ""), ("\u0661", "0", "0"), ("1", "0", "1 ")]
)
def test_a_version_is_built_only_from_components_without_leading_zeros(
    components: tuple[str, str, str],
) -> None:
    # Ordering by length, then digits, holds only without them.
    with pytest.raises(ValueError, match="version component"):
        Version(*components)


def test_a_version_compares_only_with_a_version() -> None:
    version = Version("1", "0", "0")
    assert version.__lt__("1.0.0") is NotImplemented  # the method itself, as total_ordering calls it
    assert version != "1.0.0"  # type: ignore[comparison-overlap]  # the misuse under test
    with pytest.raises(TypeError):
        _ = version < "2.0.0"


@pytest.mark.parametrize("text", ["0.1.0\n", "01.0.0", "1.0", "\u0661.0.0", "1.0.0-rc1", " 1.0.0"])
def test_a_version_off_the_pattern_is_none(text: str) -> None:
    assert parse_version(text) is None


def test_identifiers_match_in_full() -> None:
    assert RECORD_ID.fullmatch("conformance/water_fixture")
    assert not RECORD_ID.fullmatch("conformance/water_fixture\n")
    assert FAMILY_ID.fullmatch("materica.fluid.newtonian.v1")
    assert not FAMILY_ID.fullmatch("materica.v1")
    assert not FAMILY_ID.fullmatch("materica.fluid.v01")


def test_a_request_reads_the_same_as_text_as_a_value_and_as_a_shape() -> None:
    text = json.dumps(REQUEST)
    for given in (text, text.encode(), bytearray(text.encode()), memoryview(text.encode())):
        assert read(given, store()) == ABSENT, type(given)
    assert read(json.loads(text), store()) == ABSENT
    assert read(REQUEST, store()) == ABSENT


@pytest.mark.parametrize(
    "request_value",
    [
        pytest.param({**REQUEST, "x": {1, 2}}, id="a_set"),
        pytest.param({**REQUEST, "x": float("nan")}, id="nan"),
        pytest.param(b"\xef\xbb\xbf{}", id="a_byte_order_mark"),
        pytest.param("\ufeff{}", id="a_byte_order_mark_in_text"),
        pytest.param('{"x": "\ud800"}', id="a_lone_surrogate_in_text"),
        pytest.param(json.dumps("a string"), id="a_json_string"),
    ],
)
def test_a_request_that_is_not_json_is_incomplete(request_value: object) -> None:
    result = read(request_value, store())  # type: ignore[arg-type]  # a misuse a consumer may still make
    assert result.status == "not_met"
    assert [reason.code for reason in result.reasons] == ["request_incomplete"]


def test_unknown_claims_are_a_misuse() -> None:
    with pytest.raises(ValueError, match="not suites"):
        read(REQUEST, store(), claims={"plain_read", "hashes"})  # type: ignore[arg-type]  # the misuse


WITHOUT_PLAIN_READ: list[set[shapes.Suite]] = [
    set(),
    {"hash"},
    {"fits_and_reference_data"},
    {"scene_documents", "hash"},
]


@pytest.mark.parametrize("claims", WITHOUT_PLAIN_READ)
def test_claims_without_plain_read_are_a_misuse(claims: set[shapes.Suite]) -> None:
    with pytest.raises(ValueError, match="plain_read"):
        read(REQUEST, store(), claims=claims)
    with pytest.raises(ValueError, match="plain_read"):
        ReadRequest.from_json(REQUEST, claims)


def test_steps_not_built_yet_raise_rather_than_answer() -> None:
    region = with_members(target={"region": "lumen", "field": "fluid.dynamic_viscosity"})
    with pytest.raises(NotImplementedError):
        read(region, store())
    # Whatever else is wrong with it: scenes may add reasons of their own.
    faults: list[dict[str, JsonValue]] = [
        {"operating_conditions": {"temperature": {"value": 310.15, "unit": "Cel"}}},
        {"requirement": {"want": "fit"}},
        {"target": {"region": 1.0, "record": {}, "field": "x"}},
    ]
    for fault in faults:
        with pytest.raises(NotImplementedError):
            read(region | fault, store())
    with pytest.raises(NotImplementedError):
        read(with_members(acceptances=[{"acceptance": "pick", "index": 0.0}]), store())
    refused = read(with_members(acceptances={"acceptance": "pick"}), store())
    assert refused.reasons == (Reason("request_incomplete"),)


INPUTS = WATER.parent


def stored(
    record: dict[str, JsonValue], field: str = "fluid.dynamic_viscosity"
) -> tuple[JsonValue, RecordStore]:
    """REQUEST for `field` of `record`, pinned by its hash recomputed, and a store holding it."""
    record = {**record, "content_hash": content_hash(record)}
    records = RecordStore()
    records.add("record", json.dumps(record).encode())
    pin = {name: record[name] for name in ("id", "version", "content_hash")}
    return with_members(target={"record": pin, "field": field}), records


def water() -> dict[str, JsonValue]:
    value: dict[str, JsonValue] = json.loads(WATER.read_text(encoding="utf-8"))
    return value


def with_field(name: str, field: JsonValue) -> dict[str, JsonValue]:
    """The water record with `field`, in the section `name` names, as its only field."""
    record = water()
    section, _, field_name = name.partition(".")
    record["body"] = {"sections": {section: {"fields": {field_name: field}}}}
    return record


def water_field() -> dict[str, JsonValue]:
    found: JsonValue = water()
    for step in ("body", "sections", "fluid", "fields", "dynamic_viscosity"):
        assert isinstance(found, dict)
        found = found[step]
    assert isinstance(found, dict)
    return found


def viscosity_table(**table: JsonValue) -> dict[str, JsonValue]:
    """The water viscosity as a table over temperature, its axis condition `not_applicable`, with `table`'s
    members changed."""
    field = {**water_field(), "form": "table"}
    del field["value"]
    conditions = field["conditions"]
    assert isinstance(conditions, dict)
    field["conditions"] = {**conditions, "temperature": {"status": "not_applicable"}}
    field["table"] = {
        "axis": "temperature",
        "axis_unit": "K",
        "x": [300.0, 320.0],
        "y": [0.000853, 0.000577],
        "scheme": "linear",
        "edges": [],
        **table,
    }
    return field


def test_a_table_steps_8_to_13_pass_gives_its_value_and_one_steps_8_and_9_refuse_is_refused() -> None:
    """A table steps 8 and 9 pass is read on (`read_side_contract.md` section 3): at 310.15 K, between its two
    knots, it gives its value, interpolated, and the table it is read from, as stored; its axis entry is `met`
    and gives no reason (section 5, first row), so the water's unstated shear rate alone stands; and the
    Newtonian label on a temperature table is returned (step 12). One that steps 8 and 9 refuse gives every
    reason they find."""
    result = read(*stored(with_field("fluid.dynamic_viscosity", viscosity_table())))
    assert (result.status, result.reasons) == ("unknown", (Reason("condition_unstated", "shear_rate"),))
    assert result.value == evaluate.value([300.0, 320.0], [0.000853, 0.000577], "linear", 310.15)
    assert result.table == viscosity_table()["table"]
    assert result.labels == ("materica.fluid.newtonian.v1",)
    operating: shapes.OperatingCondition = {"value": 310.15, "unit": "K"}
    axis = ConditionEntry("temperature", "met", {"status": "not_applicable"}, operating)
    assert axis in (result.conditions or ())
    for refused, codes in (
        (
            {"unit": None, "table": viscosity_table(scheme="cubic")["table"]},
            {"form_invalid", "unknown_token"},
        ),
        ({"table": viscosity_table(axis_unit="Cel")["table"]}, {"unit_mismatch"}),
        ({"table": viscosity_table(points=[])["table"]}, {"points_unsupported"}),
        ({"conditions": water_field()["conditions"]}, {"form_invalid"}),
    ):
        result = read(*stored(with_field("fluid.dynamic_viscosity", {**viscosity_table(), **refused})))
        assert {reason.code for reason in result.reasons} == codes, refused


def test_a_tables_axis_unit_gives_unit_mismatch_with_its_axis() -> None:
    """`read_side_contract.md` section 2 item 2: `unit_mismatch` carries `condition` where it concerns an
    axis."""
    field = viscosity_table(axis_unit="Cel")
    assert read(*stored(with_field("fluid.dynamic_viscosity", field))).reasons == (
        Reason("unit_mismatch", "temperature"),
    )


EMPTY_X: list[dict[str, JsonValue]] = [
    {"x": [], "y": [], "edges": [310.0]},
    {"x": [], "y": [], "edges": [], "source_range": [290.0, 330.0]},
    {"x": [], "y": [], "edges": [310.0], "source_range": [290.0, 330.0]},
]


@pytest.mark.parametrize("table", EMPTY_X)
def test_an_empty_x_beside_edges_or_a_source_range_is_refused_and_never_raises(
    table: dict[str, JsonValue],
) -> None:
    """`record_format.md` section 6, table item 1: "`x` holds at least two distinct values", so the table is
    `form_invalid`, alone and as an alternative; `read_side_contract.md` section 2: "A read never stops with
    an error for anything a record or request contains" (the S3a review's H1: an edge's and `source_range`'s
    rules read `x`'s ends)."""
    alone = read(*stored(with_field("fluid.dynamic_viscosity", viscosity_table(**table))))
    assert (alone.status, alone.reasons) == ("not_met", (Reason("form_invalid"),))
    second = read(
        *stored(
            with_field("fluid.dynamic_viscosity", {"alternatives": [water_field(), viscosity_table(**table)]})
        )
    )
    assert second.status == "not_met"
    assert Reason("form_invalid", alternative=1) in second.reasons


@pytest.mark.parametrize(
    ("beside", "codes"),
    [
        ({}, {"withheld"}),
        ({"points": []}, {"withheld"}),
        ({"points": None}, {"withheld"}),
        ({"point": []}, {"form_invalid"}),
        ({"pointz": 1.0}, {"form_invalid"}),
        ({"x_unknown_member": 1.0}, {"withheld"}),
        ({"edges": []}, {"form_invalid"}),
    ],
)
def test_a_withheld_table_ignores_points_beside_its_status_and_refuses_a_slip_of_it(
    beside: dict[str, JsonValue], codes: set[str]
) -> None:
    """`provenance.md` section 1 item 5: a status object breaks its shape where it "also holds a member S
    defines", and "Elsewhere a member beside `status` and `reason` that S does not define is ignored". A
    table's shape does not define `points` (the writer schema refuses it, `record_format.md` section 6, table
    item 5), so `points` is ignored there, whatever it holds; a member one slip from it is refused, `points`
    being named at a table's place for section 10 item 5, and the broken status object gives no `withheld`."""
    field: dict[str, JsonValue] = {
        **viscosity_table(),
        "table": {"status": "withheld", **beside},
        "statistics": {"status": "withheld"},
    }
    result = read(*stored(with_field("fluid.dynamic_viscosity", field)))
    assert (result.status, {reason.code for reason in result.reasons}) == ("not_met", codes), beside


def test_a_registered_condition_on_the_evidence_field_is_refused_whatever_its_form() -> None:
    """`record_format.md` section 4.3 item 3 binds the field: a table on `biocompatibility.evidence` whose
    `conditions` hold its axis gives `form_invalid` beside `form_not_registered` (maintainer, 2026-10-19);
    with `conditions` `{}`, `form_not_registered` alone."""
    table: dict[str, JsonValue] = {**viscosity_table(), "unit": {"status": "not_applicable"}}
    del table["label"]
    name = "biocompatibility.evidence"
    with_its_axis: dict[str, JsonValue] = {
        **table,
        "conditions": {"temperature": {"status": "not_applicable"}},
    }
    assert {reason.code for reason in read(*stored(with_field(name, with_its_axis), name)).reasons} == {
        "form_not_registered",
        "form_invalid",
    }
    assert read(*stored(with_field(name, {**table, "conditions": {}}), name)).reasons == (
        Reason("form_not_registered"),
    )


@pytest.mark.parametrize(
    ("name", "form"),
    [
        ("bulk.density", "composition"),
        ("bulk.elemental_composition", "interval"),
        ("bulk.elemental_composition", "constant"),
        ("biocompatibility.evidence", "table"),
    ],
)
def test_a_form_its_row_does_not_allow_is_refused_with_every_shared_reason_and_not_its_member(
    name: str, form: str
) -> None:
    """The read neither uses nor returns the member of a form its row does not allow, so step 8 does not read
    it: a constant's `value` that is not a number adds nothing beside `form_not_registered`."""
    field = {**water_field(), "form": form, FORM_MEMBERS[form]: "not this form's member"}
    del field["label"]
    if name == "biocompatibility.evidence":
        # Its conditions hold no registered condition, whatever its form (`record_format.md` section 4.3).
        field["conditions"] = {}
    assert read(*stored(with_field(name, field), name)).reasons == (Reason("form_not_registered"),)
    refused = read(*stored(with_field(name, {**field, "unit": None}), name))
    assert {reason.code for reason in refused.reasons} == {"form_not_registered", "form_invalid"}


HYDROGEN: dict[str, JsonValue] = {"component": "element:H", "fraction": 0.102}
COMPOSITION: dict[str, JsonValue] = {
    "form": "composition",
    "unit": "1",
    "conditions": {},
    "statistics": water_field()["statistics"],
    "provenance": water_field()["provenance"],
}


@pytest.mark.parametrize(
    ("basis", "codes"),
    [
        ("mole_fraction", {"form_not_registered"}),
        ("volume_fraction", {"form_not_registered"}),
        ("mass_fraction", set[str]()),
        ("stated", {"form_invalid"}),
        ("bogus", {"unknown_token"}),
        (5.0, {"form_invalid"}),
    ],
)
def test_a_compositions_basis_is_checked_with_its_form_token(basis: JsonValue, codes: set[str]) -> None:
    """A basis of a composition's own list that the row does not allow is `form_not_registered`, as a form the
    row does not allow is (the S2 design's section 1.4, SQ43), beside every shared reason; any other basis is
    the composition's own member's to judge (`record_format.md` section 6, composition item 1)."""
    name = "bulk.elemental_composition"
    composition: dict[str, JsonValue] = {"basis": basis, "sum_rule": "partial", "components": [HYDROGEN]}
    field: dict[str, JsonValue] = {**COMPOSITION, "composition": composition}
    request, records = stored(with_field(name, field), name)
    assert isinstance(request, dict)
    request["requirement"] = {"want": "components"}
    # Past step 8, the read's one reason is step 10's for the temperature the request names and the field does
    # not state.
    found = {reason.code for reason in read(request, records).reasons} - {"condition_unstated"}
    assert found == codes
    statistics = {**COMPOSITION["statistics"], "n_specimens": -1.0}  # type: ignore[dict-item]
    request, records = stored(with_field(name, {**field, "statistics": statistics}), name)
    assert {reason.code for reason in read(request, records).reasons} == codes | {"form_invalid"}


STATED: dict[str, JsonValue] = {"basis": "stated"}
# Specimen facts that pass step 8 (None) or give these codes, each on the water field as its only fact.
FACTS: list[tuple[str, dict[str, JsonValue], tuple[str, ...] | None]] = [
    ("disease_and_treatment_state", {"token": "normal", **STATED}, None),
    ("disease_and_treatment_state", {"token": "diseased", "text": "fibrosis", **STATED}, None),
    ("disease_and_treatment_state", {"token": "treated", "text": "dialysis", **STATED}, None),
    ("disease_and_treatment_state", {"token": "normal", "text": "none", **STATED}, ("form_invalid",)),
    ("disease_and_treatment_state", {"token": "diseased", **STATED}, ("form_invalid",)),
    ("disease_and_treatment_state", {"token": "treated", **STATED}, ("form_invalid",)),
    ("disease_and_treatment_state", {"token": "remission", **STATED}, ("unknown_token",)),
    (
        "disease_and_treatment_state",
        {"token": "remission", "text": "since 2019", **STATED},
        ("unknown_token", "form_invalid"),
    ),
    ("post_mortem_interval", {"value": 60.0, "unit": "s", **STATED}, None),
    ("post_mortem_interval", {"value": 60.0, "unit": {"status": "unstated"}, **STATED}, ("unit_mismatch",)),
    ("post_mortem_interval", {"value": 1.0, "unit": "min", **STATED}, ("unit_mismatch",)),
    ("post_mortem_interval", {"value": 1.0, "unit": {"status": "approximate"}, **STATED}, ("unit_mismatch",)),
    ("post_mortem_interval", {"value": 1.0, "unit": 60.0, **STATED}, ("form_invalid",)),
    (
        "post_mortem_interval",
        {"value": 1.0, "unit": {"status": "unstated", "note": "x"}, **STATED},
        ("form_invalid",),
    ),
    ("donor_age", {"range": [1.0, 2.0], "unit": "a", **STATED}, ("unit_mismatch",)),
    ("donor_age", {"range": [1.0, 2.0], "unit": "s", **STATED}, None),
    ("mimics", {"text": "liver", **STATED}, None),
    ("mimics", {"text": "liver", "inferred_from": "Methods", **STATED}, None),
    ("mimics", {"text": "liver", "basis": "inferred", "inferred_from": "Methods"}, ("form_invalid",)),
    ("mimics", {"text": "liver", "basis": "guessed"}, ("unknown_token",)),
]


@pytest.mark.parametrize(("name", "fact", "codes"), FACTS)
def test_a_specimen_fact_takes_its_rows_shape_and_fixed_members(
    name: str, fact: dict[str, JsonValue], codes: tuple[str, ...] | None
) -> None:
    """A disease or treatment state's text is there exactly for `diseased` and `treated`; a basis its row
    fixes (`"basis": "stated"`) takes that token alone and leaves no `inferred_from` to name, so one there is
    ignored; and a fact's unit, which its row fixes too (`"unit": "s"`), is checked here only as a string or a
    status object, any token included, since step 9 alone compares it, and refuses another unit or any status
    object (maintainer, 2026-10-15)."""
    field: JsonValue = {**water_field(), "specimen": {name: fact}}
    if codes is None:
        assert past_step_9(read(*stored(with_field("fluid.dynamic_viscosity", field))))
    else:
        refused = read(*stored(with_field("fluid.dynamic_viscosity", field)))
        assert {reason.code for reason in refused.reasons} == set(codes)


def past_step_9(result: ReadResult) -> bool:
    """Whether steps 8 and 9 passed the read: step 10 then runs to its end, and gives `conditions`."""
    return result.conditions is not None


def test_a_read_whose_target_is_an_overlay_raises_rather_than_answer() -> None:
    overlay = json.loads((INPUTS / "water_overlay_fixture.json").read_text(encoding="utf-8"))
    with pytest.raises(NotImplementedError):
        read(*stored(overlay))


def test_a_request_keeps_only_the_members_its_shape_names() -> None:
    checked = ReadRequest.from_json(with_members(x_note=1.0, records=["a.json"]))
    assert isinstance(checked, ReadRequest)
    assert checked.target == MaterialRef("conformance/water_fixture", "2.0.0", PIN)
    expected = json.loads(json.dumps(REQUEST))
    expected["requirement"]["conditions"]["temperature"]["tolerance"]["value"] = 1.0
    assert checked.to_json() == expected


def with_member(place: tuple[str, ...], name: str, value: JsonValue = 1.0) -> dict[str, JsonValue]:
    """REQUEST as parsed JSON, with `name` set to `value` in the object at `place`."""
    request = with_members()
    parent: JsonValue = request
    for step in place:
        assert isinstance(parent, dict)
        parent = parent[step]
    assert isinstance(parent, dict)
    parent[name] = value
    return request


TEMPERATURE = ("requirement", "conditions", "temperature")
# A member one slip from one section 1 or `declarations.md` names at each place of a request, and the
# condition the place concerns.
SLIPS = [
    pytest.param((), "requirment", None, id="top"),
    pytest.param((), "record", None, id="top_records"),
    pytest.param((), "acceptance", None, id="top_acceptances"),
    pytest.param(("target",), "fields", None, id="target"),
    pytest.param(("target", "record"), "versions", None, id="target_record"),
    pytest.param(("requirement",), "wants", None, id="requirement"),
    pytest.param(("requirement",), "labels", None, id="requirement_refused_member"),
    pytest.param(("requirement",), "feild", None, id="requirement_declarations_field"),
    pytest.param(("operating_conditions", "temperature"), "units", "temperature", id="operating"),
    pytest.param(TEMPERATURE, "tolerances", "temperature", id="requirement_condition"),
    pytest.param(TEMPERATURE, "accepts", "temperature", id="requirement_condition_refused_member"),
    pytest.param(TEMPERATURE, "reasn", "temperature", id="requirement_condition_declarations_reason"),
    pytest.param(
        TEMPERATURE, "consequences", "temperature", id="requirement_condition_declarations_consequence"
    ),
    pytest.param((*TEMPERATURE, "tolerance"), "vaule", "temperature", id="tolerance"),
]


@pytest.mark.parametrize(("place", "name", "condition"), SLIPS)
def test_a_member_one_slip_from_a_named_one_is_refused_at_its_place(
    place: tuple[str, ...], name: str, condition: str | None
) -> None:
    refused = read(with_member(place, name), store())
    assert refused.reasons == (Reason("request_incomplete", condition),)


@pytest.mark.parametrize(("place", "name", "condition"), SLIPS)
def test_a_member_further_from_every_named_one_is_ignored(
    place: tuple[str, ...], name: str, condition: str | None
) -> None:
    assert read(with_member(place, f"x_{name}"), store()) == ABSENT


@pytest.mark.parametrize("field", ["fluid.surface_tension", "acoustic.sound_speed", "fluid.specimen"])
def test_a_field_the_vocabulary_does_not_register_is_refused(field: str) -> None:
    assert read(with_member(("target",), "field", field), store()).reasons == (Reason("request_incomplete"),)


@pytest.mark.parametrize("name", ["label", "represents", "population_level", "review"])
def test_a_requirement_holding_a_declarations_member_is_refused(name: str) -> None:
    assert read(with_member(("requirement",), name, "x"), store()).reasons == (Reason("request_incomplete"),)


@pytest.mark.parametrize(
    ("place", "name"), [(("requirement",), "field"), (TEMPERATURE, "reason"), (TEMPERATURE, "consequence")]
)
def test_a_declarations_member_a_read_never_checks_is_ignored(place: tuple[str, ...], name: str) -> None:
    """`declarations.md` section 1 names a requirement's `field`, and a requirement condition's `reason` and
    `consequence`: a read ignores each, and refuses a member one slip from one (above)."""
    assert read(with_member(place, name, "fluid.dynamic_viscosity"), store()) == ABSENT


def test_a_result_reads_back_from_its_json() -> None:
    result = ReadResult(
        "not_met", (Reason("request_incomplete", "temperature", "below zero"),), ("hash_not_checked",)
    )
    assert ReadResult.from_json(result.to_json()) == result
    written = json.loads(json.dumps(result.to_json()))
    assert written["reasons"] == [
        {"code": "request_incomplete", "condition": "temperature", "detail": "below zero"}
    ]


def test_a_reason_given_twice_is_merged_with_both_details() -> None:
    (reason,) = merged(
        [Reason("request_incomplete", "temperature", "a"), Reason("request_incomplete", "temperature", "b")]
    )
    assert reason.detail == "a; b"


def test_the_worst_status_wins_and_none_is_met() -> None:
    assert worst([]) == "met"
    assert worst(["met", "unknown"]) == "unknown"
    assert worst(["unknown", "not_met", "met"]) == "not_met"
    assert VOCABULARY.reasons["no_pick"].status == "unknown"
    assert VOCABULARY.sections == {"bulk", "fluid", "magnetic", "biocompatibility"}


def test_a_store_sets_documents_aside_and_keeps_unreadable_sources_apart() -> None:
    records = RecordStore()
    records.add("manifest", b'{"document_type": "scene", "id": "conformance/a", "version": "1.0.0"}')
    records.add(
        "record",
        b'{"document_type": "x", "record_type": "material", "id": "conformance/a", "version": "1.0.0"}',
    )
    records.add("array", b"[]")
    records.add("bytes", b"\xff")
    assert [record.source for record in records.get("conformance/a", "1.0.0")] == ["record"]
    assert [source for source, _ in records.unparsed()] == ["array", "bytes"]
    assert records.list_records() == []


def claims_parameters(modules: list[ModuleType]) -> dict[str, object]:
    """The annotation of every `claims` parameter of a function or method defined in `modules`."""
    found: dict[str, object] = {}
    for module in modules:
        for _, member in inspect.getmembers(module):
            candidates: list[object] = list(vars(member).values()) if inspect.isclass(member) else [member]
            for candidate in candidates:
                function: object = getattr(candidate, "__func__", candidate)  # a classmethod's function
                if (
                    inspect.isfunction(function)
                    and function.__module__ == module.__name__
                    and "claims" in inspect.signature(function).parameters
                ):
                    found[function.__qualname__] = get_type_hints(function)["claims"]
    return found


CORE = [
    importlib.import_module(f"materica.core.{path.stem}")
    for path in sorted((Path(materica.__file__).parent / "core").glob("*.py"))
]


def test_each_claims_parameter_of_the_core_is_typed_by_the_suites() -> None:
    """So that a misspelt suite name does not type-check (S2a-2's review, L7)."""
    found = claims_parameters(CORE)
    assert {"form_problems", "_form", "read", "ReadRequest.from_json", "resolve_record"} <= found.keys()
    assert {name for name, hint in found.items() if hint != Collection[Suite]} == set()


def test_a_claims_parameter_typed_otherwise_is_found() -> None:
    module = ModuleType("loose")

    def loose(claims: Collection[str]) -> None:
        pass

    loose.__module__ = module.__name__
    module.loose = loose  # type: ignore[attr-defined]
    assert claims_parameters([module]) == {
        "test_a_claims_parameter_typed_otherwise_is_found.<locals>.loose": Collection[str]
    }


def test_a_label_is_judged_on_the_form_the_field_holds_and_on_no_form_where_it_holds_none() -> None:
    """S2a-2's review, L8: the row names a label for a field and its form, so a label beside a form token the
    reader does not know is refused for that form, and one beside a missing form is not judged on a form."""
    field = water_field()
    missing = read(
        *stored(with_field("fluid.dynamic_viscosity", {k: v for k, v in field.items() if k != "form"}))
    )
    assert missing.reasons == (Reason("form_invalid"),)
    assert "label" not in str(missing.reasons[0].detail)
    unknown = read(*stored(with_field("fluid.dynamic_viscosity", {**field, "form": "spline"})))
    details = {reason.code: str(reason.detail) for reason in unknown.reasons}
    assert details.keys() == {"unknown_token", "form_invalid"}
    assert "'spline', a form the reader does not know" in details["form_invalid"]
    composition = read(*stored(with_field("fluid.dynamic_viscosity", {**field, "form": "composition"})))
    assert {reason.code for reason in composition.reasons} == {"form_not_registered", "form_invalid"}
    assert "a field of form composition" in str(composition.reasons)


UNCERTAINTY: dict[str, JsonValue] = {
    "value": 0.02,
    "coverage_factor": 2.0,
    "coverage_probability": {"status": "unstated"},
    "distribution": "normal",
    "dof": {"status": "not_applicable"},
    "basis": "reported_uncertainty",
    "represents": "measurement",
    "precision_conditions": "repeatability",
}


def with_block(**members: JsonValue) -> dict[str, JsonValue]:
    statistics = water_field()["statistics"]
    assert isinstance(statistics, dict)
    return {**water_field(), "statistics": {**statistics, **members}}


def with_condition(name: str, condition: JsonValue) -> dict[str, JsonValue]:
    conditions = water_field()["conditions"]
    assert isinstance(conditions, dict)
    return {**water_field(), "conditions": {**conditions, name: condition}}


def with_fact(name: str, fact: JsonValue) -> dict[str, JsonValue]:
    return {**water_field(), "specimen": {name: fact}}


def unlabelled(**members: JsonValue) -> dict[str, JsonValue]:
    return {**{name: value for name, value in water_field().items() if name != "label"}, **members}


# The eleven rules S2a-2's review found no test checking (finding M1), each with a field that breaks it and
# the codes step 8 gives, and some with a field that keeps it, which passes step 8 (None). The label on a
# table, which no read reaches before S3, is `test_a_label_on_a_table_follows_its_rows_axis`.
RULES: list[tuple[str, dict[str, JsonValue], frozenset[str] | None]] = [
    (
        "a population level's within holds none alone of the statuses",
        with_block(
            represents="population", population_level={"level": "specimen", "within": {"status": "unstated"}}
        ),
        frozenset({"form_invalid"}),
    ),
    (
        "... and none passes",
        with_block(
            represents="population", population_level={"level": "specimen", "within": {"status": "none"}}
        ),
        None,
    ),
    (
        "an uncertainty's precision_conditions takes its tokens alone",
        with_block(relative_uncertainty={**UNCERTAINTY, "precision_conditions": "lab_to_lab"}),
        frozenset({"unknown_token"}),
    ),
    ("... and repeatability passes", with_block(relative_uncertainty=UNCERTAINTY), None),
    (
        "a constant's statistics takes withheld, never not_applicable",
        {**water_field(), "statistics": {"status": "not_applicable"}},
        frozenset({"form_invalid"}),
    ),
    (
        "a condition's basis takes stated or inferred",
        with_condition("temperature", {"value": 310.15, "unit": "K", "basis": "guessed"}),
        frozenset({"unknown_token"}),
    ),
    (
        "a fact's basis is no block's",
        with_fact("lot", {"text": "B-17", "basis": "reported_sd"}),
        frozenset({"form_invalid"}),
    ),
    (
        "a condition's status object refuses the members of either shape",
        with_condition("temperature", {"status": "unstated", "token": "apparent"}),
        frozenset({"form_invalid"}),
    ),
    (
        "a fact's token knows the conditions' tokens",
        with_fact("tissue_state", {"token": "tube", "basis": "stated"}),
        frozenset({"form_invalid"}),
    ),
    (
        "a condition's token knows the facts' tokens",
        with_condition("density_kind", {"token": "stock", "basis": "stated"}),
        frozenset({"form_invalid"}),
    ),
    (
        "a token condition's unit is a string or a status object",
        with_condition("measurement_geometry", {"token": "tube", "unit": 5.0, "basis": "stated"}),
        frozenset({"form_invalid"}),
    ),
    (
        "... which step 9 refuses",
        with_condition("measurement_geometry", {"token": "tube", "unit": "m", "basis": "stated"}),
        frozenset({"unit_mismatch"}),
    ),
    (
        "a fact's unit takes any status token at step 8, which step 9 refuses",
        with_fact(
            "post_mortem_interval", {"value": 60.0, "unit": {"status": "approximate"}, "basis": "stated"}
        ),
        frozenset({"unit_mismatch"}),
    ),
    (
        "the row's label beside a form the reader does not know",
        {**water_field(), "form": "spline"},
        frozenset({"unknown_token", "form_invalid"}),
    ),
    ("a form the reader does not know, alone", unlabelled(form="spline"), frozenset({"unknown_token"})),
    (
        "beside a form the reader does not know, every form's own member is named",
        unlabelled(form="spline", intervals={}),
        frozenset({"unknown_token", "form_invalid"}),
    ),
]


@pytest.mark.parametrize(("rule", "field", "codes"), RULES, ids=[rule for rule, _, _ in RULES])
def test_each_rule_the_review_found_untested(
    rule: str, field: dict[str, JsonValue], codes: frozenset[str] | None
) -> None:
    if codes is None:
        assert past_step_9(read(*stored(with_field("fluid.dynamic_viscosity", field))))
    else:
        refused = read(*stored(with_field("fluid.dynamic_viscosity", field)))
        assert {reason.code for reason in refused.reasons} == codes


TEMPERATURE_STATED: dict[str, JsonValue] = {"value": 310.15, "unit": "K"}
# Places a record names `basis` at, each with the field holding a token there.
BASES: list[tuple[str, Callable[[str], dict[str, JsonValue]]]] = [
    ("a condition's", lambda basis: with_condition("temperature", {**TEMPERATURE_STATED, "basis": basis})),
    ("a fact's", lambda basis: with_fact("tissue_state", {"token": "in_vivo", "basis": basis})),
    ("a statistics block's", lambda basis: with_block(basis=basis)),
]


@pytest.mark.parametrize(("place", "field"), BASES, ids=[place for place, _ in BASES])
def test_a_records_basis_implied_is_a_token_the_reader_knows_that_no_row_allows(
    place: str, field: Callable[[str], dict[str, JsonValue]]
) -> None:
    """A result's condition entry gives the basis `implied` (`read_side_contract.md` section 2 item 6), so the
    reader knows it for a member named `basis`: in a record it is `form_invalid`, as one the reader knows
    for no `basis` is `unknown_token` (section 3, step 8). S2a-4's review, L4."""
    for basis, code in [("implied", "form_invalid"), ("x_unknown", "unknown_token")]:
        refused = read(*stored(with_field("fluid.dynamic_viscosity", field(basis))))
        assert [reason.code for reason in refused.reasons] == [code], basis


@pytest.mark.parametrize(("axis", "allowed"), [("shear_rate", False), ("temperature", True)])
def test_a_label_on_a_table_follows_its_rows_axis(axis: str, allowed: bool) -> None:
    """Step 8's shared check of a field, which a read reaches for a table only once S3 reads tables."""
    field: dict[str, JsonValue] = {**water_field(), "form": "table", "table": {"axis": axis}}
    found = value_shapes.field_problems(field, VOCABULARY.fields["fluid.dynamic_viscosity"], "table")
    assert [reason.code for reason in found] == ([] if allowed else ["form_invalid"])


def test_withheld_is_given_beside_a_shared_refusal() -> None:
    """Each step makes all its checks (`read_side_contract.md` section 2 item 2): a withheld value beside a
    broken unit gives both. HP3 meets the pair only on its rarer two-fault draws, so the review's mutant that
    drops `withheld` there survived it in one run of six."""
    withheld: dict[str, JsonValue] = {
        **water_field(),
        "value": {"status": "withheld"},
        "statistics": {"status": "withheld"},
    }
    alone = read(*stored(with_field("fluid.dynamic_viscosity", withheld)))
    assert {reason.code for reason in alone.reasons} == {"withheld"}
    both = read(*stored(with_field("fluid.dynamic_viscosity", {**withheld, "unit": None})))
    assert {reason.code for reason in both.reasons} == {"withheld", "form_invalid"}


# A status object holding a token the reader does not know, broken in each way `provenance.md` section 1 item
# 5 names, and by a slip (section 10): it is read for nothing else, so its token gives no `unknown_token`.
UNKNOWN_STATUS = "x_unknown"
BROKEN_STATUSES: list[tuple[str, dict[str, JsonValue]]] = [
    ("beside a member where S is a number", with_block(sd={"status": UNKNOWN_STATUS, "note": 1.0})),
    ("beside a member S defines", with_block(relative_uncertainty={"status": UNKNOWN_STATUS, "value": 1.0})),
    ("with a reason that is no string", with_block(sd={"status": UNKNOWN_STATUS, "reason": 1.0})),
    ("beside a slip of reason", with_block(relative_uncertainty={"status": UNKNOWN_STATUS, "reasons": "x"})),
    ("as a condition", with_condition("temperature", {"status": UNKNOWN_STATUS, "unit": "K"})),
    ("as a fact", with_fact("lot", {"status": UNKNOWN_STATUS, "text": "B-17"})),
]


@pytest.mark.parametrize(("place", "field"), BROKEN_STATUSES, ids=[place for place, _ in BROKEN_STATUSES])
def test_a_status_object_that_breaks_its_shape_gives_no_reason_for_its_token(
    place: str, field: dict[str, JsonValue]
) -> None:
    refused = read(*stored(with_field("fluid.dynamic_viscosity", field)))
    assert [reason.code for reason in refused.reasons] == ["form_invalid"]


def test_an_unknown_status_token_alone_is_unknown_token() -> None:
    """The control: the same token, in an object that keeps its shape, gives its own reason."""
    kept = with_block(relative_uncertainty={"status": UNKNOWN_STATUS, "reason": "not stated"})
    refused = read(*stored(with_field("fluid.dynamic_viscosity", kept)))
    assert [reason.code for reason in refused.reasons] == ["unknown_token"]


DERIVED: dict[str, JsonValue] = {
    "origin": "derived",
    "derivation": {
        "method": "arrhenius_mixing",
        "inputs": [
            {
                "record": {"id": "conformance/a", "version": "1.0.0", "content_hash": "sha256:" + "0" * 64},
                "field": "fluid.dynamic_viscosity",
            }
        ],
        "assumptions": [],
        "input_specimens": [
            {"input": 0.0, "specimen": {"post_mortem_interval": {"value": 60.0, "unit": "min", **STATED}}}
        ],
    },
}
KELVIN_SIGN = chr(0x212A)
# Units step 9 compares (`read_side_contract.md` section 3, step 9), each changed in the water field, and the
# reasons, `(code, condition)`, it then gives; none where the field passes step 9.
UNITS: list[tuple[str, dict[str, JsonValue], set[tuple[str, str | None]] | None]] = [
    ("the field's unit as registered", water_field(), None),
    ("the field's unit with a space", {**water_field(), "unit": "Pa s"}, {("unit_mismatch", None)}),
    ("the field's unit in capitals", {**water_field(), "unit": "PA.S"}, {("unit_mismatch", None)}),
    (
        "a status object where a string is registered",
        {**water_field(), "unit": {"status": "unstated"}},
        {("unit_mismatch", None)},
    ),
    (
        "a condition's unit in another code",
        with_condition("temperature", {"value": 37.0, "unit": "Cel", "basis": "stated"}),
        {("unit_mismatch", "temperature")},
    ),
    (
        "a condition's unit as the Kelvin sign",
        with_condition("temperature", {"value": 310.15, "unit": KELVIN_SIGN, "basis": "stated"}),
        {("unit_mismatch", "temperature")},
    ),
    (
        "a condition's unit as a status object",
        with_condition("temperature", {"value": 310.15, "unit": {"status": "unstated"}, "basis": "stated"}),
        {("unit_mismatch", "temperature")},
    ),
    (
        "a plus_minus entry's unit, once with its condition's",
        with_condition(
            "temperature",
            {
                "value": 310.15,
                "unit": "Cel",
                "plus_minus": [{"stated_as": "bound", "value": 0.5, "unit": "Cel"}],
                "basis": "stated",
            },
        ),
        {("unit_mismatch", "temperature")},
    ),
    (
        "a plus_minus entry's unit alone",
        with_condition(
            "temperature",
            {
                "value": 310.15,
                "unit": "K",
                "plus_minus": [{"stated_as": "sd", "value": 0.5, "unit": {"status": "unstated"}}],
                "basis": "stated",
            },
        ),
        {("unit_mismatch", "temperature")},
    ),
    (
        "a unit on a token condition",
        with_condition("measurement_geometry", {"token": "bulk", "unit": "1", "basis": "stated"}),
        {("unit_mismatch", "measurement_geometry")},
    ),
    (
        "the field's unit and a condition's: one reason each",
        {**with_condition("shear_rate", {"value": 1.0, "unit": "s-1", "basis": "stated"}), "unit": "Pa*s"},
        {("unit_mismatch", None), ("unit_mismatch", "shear_rate")},
    ),
    (
        "a condition the reader does not know, compared with nothing",
        with_condition("pressure", {"value": 1.0, "unit": "bar", "basis": "stated"}),
        None,
    ),
    (
        "a condition held as a status object",
        with_condition("temperature", {"status": "unstated", "reason": "no unit given either"}),
        None,
    ),
    (
        "a field's fact in minutes",
        with_fact("post_mortem_interval", {"value": 1.0, "unit": "min", **STATED}),
        {("unit_mismatch", None)},
    ),
    (
        "a field's fact in seconds",
        with_fact("donor_age", {"range": [1.0e9, 2.0e9], "unit": "s", **STATED}),
        None,
    ),
    ("a field's fact as a status object", with_fact("donor_age", {"status": "unstated"}), None),
    (
        "a derived value's input fact in minutes",
        {**water_field(), "provenance": DERIVED},
        {("unit_mismatch", None)},
    ),
    (
        "an input fact in minutes where the origin is not derived, which step 8 does not check",
        {**water_field(), "provenance": {**DERIVED, "origin": "measured_by_contributor"}},
        None,
    ),
]


@pytest.mark.parametrize(("units", "field", "reasons"), UNITS, ids=[units for units, _, _ in UNITS])
def test_step_9_compares_each_unit_with_the_one_registered_for_it(
    units: str, field: dict[str, JsonValue], reasons: set[tuple[str, str | None]] | None
) -> None:
    """Code point for code point, a status object never equal to a string, each reason once with its
    condition; a field that passes goes on to step 10."""
    if reasons is None:
        assert past_step_9(read(*stored(with_field("fluid.dynamic_viscosity", field))))
        return
    result = read(*stored(with_field("fluid.dynamic_viscosity", field)))
    assert result.status == "not_met"
    assert {(reason.code, reason.condition) for reason in result.reasons} == reasons
    assert len(result.reasons) == len(reasons)


@pytest.mark.parametrize(
    ("fact", "reasons"),
    [
        ({"value": 60.0, "unit": "s", **STATED}, None),
        ({"value": 60.0, "unit": {"status": "not_applicable"}, **STATED}, {("unit_mismatch", None)}),
    ],
)
def test_step_9_compares_a_section_facts_unit_for_every_field_of_the_section(
    fact: dict[str, JsonValue], reasons: set[tuple[str, str | None]] | None
) -> None:
    record = water()
    section: dict[str, JsonValue] = {
        "specimen": {"post_mortem_interval": fact},
        "fields": {"dynamic_viscosity": water_field()},
    }
    record["body"] = {"sections": {"fluid": section}}
    if reasons is None:
        assert past_step_9(read(*stored(record)))
        return
    assert {(reason.code, reason.condition) for reason in read(*stored(record)).reasons} == reasons


def test_what_a_step_before_found_is_taken_as_found_and_anything_else_raises() -> None:
    """`value_shapes.an_object` and `a_list`, the pair steps 8 to 10 share: a defect of the core raises."""
    found: JsonValue = {"a": [1.0]}
    assert value_shapes.an_object(found) is found
    assert value_shapes.a_list(found["a"]) is found["a"]
    with pytest.raises(TypeError):
        value_shapes.an_object(found["a"])
    with pytest.raises(TypeError):
        value_shapes.a_list(found)


def test_a_field_unit_registered_as_a_status_object_takes_its_token_whatever_its_reason() -> None:
    """`biocompatibility.evidence`'s unit is `{"status": "not_applicable"}` (`record_format.md` section 4.2):
    step 9's comparison, apart from evidence's own member, which S2b-2 reads."""
    from materica.core.fields import same_unit

    registered = VOCABULARY.fields["biocompatibility.evidence"].unit
    assert same_unit({"status": "not_applicable", "reason": "a list of reports"}, registered)
    assert not same_unit({"status": "unstated"}, registered)
    assert not same_unit({"status": "bogus"}, registered)
    assert not same_unit("not_applicable", registered)
    assert same_unit("Pa.s", "Pa.s")
    assert not same_unit("Pa.s" + chr(0x200B), "Pa.s")
    assert not same_unit({"status": "unstated"}, "Pa.s")


IMPLIED: dict[str, JsonValue] = {
    "acceptance": "implied_condition",
    "record": {"id": "conformance/water_fixture", "version": "2.0.0", "content_hash": PIN},
    "field": "fluid.dynamic_viscosity",
    "fact": "tissue_state",
    "token": "in_vivo",
    "implies": {"temperature": {"value": 310.15, "unit": "K"}, "density_kind": {"token": "matrix"}},
    "reason": "body temperature in vivo",
}


def implied_with(**members: JsonValue) -> JsonValue:
    """REQUEST with one implied condition, `members` changed in it, None removing one."""
    acceptance: dict[str, JsonValue] = {
        name: value for name, value in {**IMPLIED, **members}.items() if value is not None
    }
    return with_members(acceptances=[acceptance])


# Implied conditions at step 0 (`read_side_contract.md` section 1), beyond the PR-330 arms: what is refused,
# with the condition it concerns, and what is ignored.
IMPLIED_AT_STEP_0: list[tuple[str, JsonValue, set[tuple[str, str | None]]]] = [
    ("implies not an object", implied_with(implies=[]), {("request_incomplete", None)}),
    (
        "a value that is not an object",
        implied_with(implies={"temperature": 310.15, "density_kind": {"token": "matrix"}}),
        {("request_incomplete", "temperature")},
    ),
    ("no implies", implied_with(implies=None), {("request_incomplete", None)}),
    ("no fact", implied_with(fact=None), {("request_incomplete", None)}),
    ("a field off the pattern", implied_with(field="viscosity"), {("request_incomplete", None)}),
    ("a slip beside its members", implied_with(facts="tissue_state"), {("request_incomplete", None)}),
    ("a slip of the basis a read ignores", implied_with(bases="x"), {("request_incomplete", None)}),
    (
        "a numeric value without its unit",
        implied_with(implies={"temperature": {"value": 310.15}}),
        {("request_incomplete", "temperature")},
    ),
    (
        "a numeric value in another unit",
        implied_with(implies={"shear_rate": {"value": 1.0, "unit": "s-1"}}),
        {("request_unit_mismatch", "shear_rate")},
    ),
    (
        "a token for a numeric condition",
        implied_with(implies={"temperature": {"token": "matrix"}}),
        {("request_incomplete", "temperature")},
    ),
    (
        "a value for a token condition",
        implied_with(implies={"density_kind": {"value": 1.0, "unit": "1"}}),
        {("request_incomplete", "density_kind")},
    ),
    (
        "a status object for a token condition",
        implied_with(implies={"density_kind": {"status": "unstated"}}),
        {("request_incomplete", "density_kind")},
    ),
    (
        "a token beside a numeric value, outside its row",
        implied_with(implies={"temperature": {"value": 310.15, "unit": "K", "token": "matrix"}}),
        {("request_incomplete", "temperature")},
    ),
    (
        "a slip of a token beside a numeric value",
        implied_with(implies={"temperature": {"value": 310.15, "unit": "K", "tokens": "matrix"}}),
        {("request_incomplete", "temperature")},
    ),
    (
        "a unit beside a token",
        implied_with(implies={"density_kind": {"token": "matrix", "unit": "K"}}),
        {("request_incomplete", "density_kind")},
    ),
    (
        "a range beside a token",
        implied_with(implies={"density_kind": {"token": "matrix", "range": [1.0, 2.0]}}),
        {("request_incomplete", "density_kind")},
    ),
    (
        "a slip of a value beside a token",
        implied_with(implies={"density_kind": {"token": "matrix", "valeu": 1.0}}),
        {("request_incomplete", "density_kind")},
    ),
    (
        "a slip of a status object's reason in a value",
        implied_with(implies={"temperature": {"value": 310.15, "unit": "K", "reasons": "x"}}),
        {("request_incomplete", "temperature")},
    ),
    (
        "two faults in two conditions",
        implied_with(implies={"temperature": {"range": [2.0, 1.0], "unit": "K"}, "pressure": {}}),
        {("request_incomplete", "temperature"), ("request_incomplete", "pressure")},
    ),
]


@pytest.mark.parametrize(
    ("fault", "request_value", "reasons"), IMPLIED_AT_STEP_0, ids=[fault for fault, _, _ in IMPLIED_AT_STEP_0]
)
def test_an_implied_condition_that_breaks_its_shape_is_refused_at_step_0(
    fault: str, request_value: JsonValue, reasons: set[tuple[str, str | None]]
) -> None:
    check_refused_at_step_0(request_value, reasons)


def check_refused_at_step_0(request_value: JsonValue, reasons: set[tuple[str, str | None]]) -> None:
    refused = read(request_value, store())
    assert refused.status == "not_met"
    assert {(reason.code, reason.condition) for reason in refused.reasons} == reasons


@pytest.mark.parametrize(
    "request_value",
    [
        pytest.param(implied_with(), id="as_given"),
        pytest.param(implied_with(basis="a datasheet", x_note=1.0), id="its_basis_and_an_unknown_member"),
        pytest.param(
            implied_with(implies={"temperature": {"value": 310.15, "unit": "K", "basis": "stated"}}),
            id="a_basis_in_a_value",
        ),
        pytest.param(
            implied_with(implies={"temperature": {"value": 310.15, "unit": "K", "reason": "x"}}),
            id="a_reason_in_a_value",
        ),
        pytest.param(
            implied_with(implies={"density_kind": {"token": "matrix", "inferred_from": "x"}}),
            id="an_inferred_from_beside_a_token",
        ),
        pytest.param(implied_with(record=None, region="lumen"), id="at_a_region"),
        pytest.param(implied_with(record="a reference of no shape"), id="at_no_reference"),
        pytest.param(implied_with(implies={}), id="implying_nothing"),
        pytest.param(implied_with(reason=None), id="without_its_reason"),
    ],
)
def test_an_implied_condition_that_keeps_its_shape_passes_step_0(request_value: JsonValue) -> None:
    """The record is version 2.0.0, which the store does not hold: the read goes on to step 1."""
    assert read(request_value, store()) == ABSENT


# Acceptances a read does not take (`read_side_contract.md` section 1: "An acceptance of any other kind ...
# gives `request_incomplete`"; PR-310's GAPS G11 arm, S2a-3's review I4), and those S3 and S4 apply.
NOT_TAKEN: list[JsonValue] = [
    {"acceptance": "waiver", "field": "fluid.dynamic_viscosity", "code": "condition_unstated"},
    {"acceptance": "accepted_difference", "section": "fluid", "fact": "species", "value": "any"},
    {"acceptance": "distribution", "field": "fluid.dynamic_viscosity", "distribution": "normal"},
    {"acceptance": "overlay_scope", "overlay": {}, "accepts": ["model"]},
    {"acceptance": "implied"},
    {"acceptance": 1.0},
    # A kind that is an object or a list, which fuzz target 5 found raising (S3c).
    {"acceptance": {"id": "conformance/fixture"}, "field": "fluid.dynamic_viscosity"},
    {"acceptance": ["nominal"], "field": "fluid.dynamic_viscosity"},
    {"field": "fluid.dynamic_viscosity"},
    1.0,
    None,
    [],
]
APPLIED_LATER: list[JsonValue] = [
    {"acceptance": "pick", "index": 0.0},
    {"acceptance": "overlay", "overlay": {}},
]


@pytest.mark.parametrize("acceptance", NOT_TAKEN)
def test_an_acceptance_of_a_kind_a_read_does_not_take_is_refused(acceptance: JsonValue) -> None:
    """Exactly `request_incomplete`, alone and beside an implied condition the request takes."""
    alone: list[JsonValue] = [acceptance]
    beside: list[JsonValue] = [IMPLIED, acceptance]
    for acceptances in (alone, beside):
        refused = read(with_members(acceptances=acceptances), store())
        assert (refused.status, refused.reasons) == ("not_met", (Reason("request_incomplete"),)), acceptances


@pytest.mark.parametrize("acceptance", APPLIED_LATER)
def test_a_pick_and_an_overlay_raise_whatever_else_the_request_holds(acceptance: JsonValue) -> None:
    """S4 applies them, and each could change the answer: beside a refusal, beside another kind."""
    for acceptances in ([acceptance], [*NOT_TAKEN, acceptance]):
        with pytest.raises(NotImplementedError):
            read(with_members(acceptances=acceptances), store())
        with pytest.raises(NotImplementedError):
            read(with_members(acceptances=acceptances, target=None), store())


# A `trainable` acceptance (section 1), the one a build makes from a declaration's `trainable` entry, which
# S7a-4 applies: the request raises until then, as for a pick (the maintainer's ruling, 2026-10-22).
TRAINABLES: list[JsonValue] = [
    {
        "acceptance": "trainable",
        "record": {"id": "conformance/water_fixture", "version": "2.0.0", "content_hash": PIN},
        "field": "fluid.dynamic_viscosity",
    },
    {"acceptance": "trainable"},
]


@pytest.mark.parametrize("acceptance", TRAINABLES)
def test_a_trainable_acceptance_raises_whatever_else_the_request_holds(acceptance: JsonValue) -> None:
    """Alone, beside refusals, beside a kind a read applies, and with no target."""
    ways: list[list[JsonValue]] = [[acceptance], [*NOT_TAKEN, acceptance], [IMPLIED, acceptance]]
    for acceptances in ways:
        with pytest.raises(NotImplementedError):
            read(with_members(acceptances=acceptances), store())
        with pytest.raises(NotImplementedError):
            read(with_members(acceptances=acceptances, target=None), store())


def with_review(
    review: JsonValue, acceptances: list[JsonValue] | None = None, **members: JsonValue
) -> dict[str, JsonValue]:
    """REQUEST as parsed JSON, its requirement holding `review` and `members`, and `acceptances` if given."""
    request = with_members() if acceptances is None else with_members(acceptances=acceptances)
    requirement = request["requirement"]
    assert isinstance(requirement, dict)
    requirement.update(review=review, **members)
    return request


@pytest.mark.parametrize("review", ["reviewed", "checked", None])
def test_a_requirement_holding_review_is_refused_exactly_as_label_is(review: JsonValue) -> None:
    """Section 1 refuses at step 0 a request whose requirement holds `label`, `represents`,
    `population_level` or `review`: a declaration's requirement, which a build checks (`not_reviewed`) and a
    read never does. A read refuses `review` with `request_incomplete`, as it refuses `label`, and raises
    nothing: alone, beside the other refusals (a slip of `review` and of `want`, an acceptance of no kind),
    beside a kind a read applies, and with no target."""
    ways: list[list[JsonValue] | None] = [None, [*NOT_TAKEN], [IMPLIED]]
    for acceptances in ways:
        request = with_review(review, acceptances)
        as_label = with_review(review, acceptances)
        requirement = as_label["requirement"]
        assert isinstance(requirement, dict)
        del requirement["review"]
        requirement["label"] = "materica.fluid.newtonian.v1"
        for given, alike in (
            (request, as_label),
            ({**request, "target": None}, {**as_label, "target": None}),
        ):
            refused, label_refused = read(given, store()), read(alike, store())
            assert (
                (refused.status, [r.code for r in refused.reasons])
                == (
                    label_refused.status,
                    [r.code for r in label_refused.reasons],
                )
                == ("not_met", ["request_incomplete"])
            ), acceptances
        beside = read(with_review(review, acceptances, wants="value", reviev="reviewed"), store())
        assert (beside.status, [r.code for r in beside.reasons]) == ("not_met", ["request_incomplete"])


@pytest.mark.parametrize("slip", ["reviev", "reviews", "reveiw", "rview", "re_view", "Review"])
def test_a_member_one_slip_from_review_in_a_requirement_is_refused(slip: str) -> None:
    """Section 1: a request is refused where "it holds, at any depth, a member one slip (`record_format.md`
    section 10) from a member this section or `declarations.md` names at that place, refused ones included",
    and section 1 names a requirement's `review`: a slip of it is refused, never read as without it."""
    refused = read(with_member(("requirement",), slip, "reviewed"), store())
    assert (refused.status, refused.reasons) == ("not_met", (Reason("request_incomplete"),)), slip
    assert read(with_member(("requirement",), f"x_{slip}", "reviewed"), store()) == ABSENT


def test_a_request_keeps_its_implied_conditions_with_the_members_their_shape_names() -> None:
    checked = ReadRequest.from_json(implied_with(x_note=1.0, basis="a datasheet"))
    assert isinstance(checked, ReadRequest)
    (implied,) = checked.implied
    assert implied.index == 0
    assert checked.to_json().get("acceptances") == [
        {
            "acceptance": "implied_condition",
            "record": IMPLIED["record"],
            "field": "fluid.dynamic_viscosity",
            "fact": "tissue_state",
            "token": "in_vivo",
            "implies": {"temperature": {"value": 310.15, "unit": "K"}, "density_kind": {"token": "matrix"}},
        }
    ]


def test_a_read_returns_the_implied_conditions_it_applied_outside_its_json() -> None:
    """A field in vivo with no temperature, read at 330 K: the implied 310.15 K fills it and is outside."""
    conditions: dict[str, JsonValue] = {"shear_rate": {"status": "unstated"}}
    field: dict[str, JsonValue] = {
        **water_field(),
        "conditions": conditions,
        "specimen": {"tissue_state": {"token": "in_vivo", **STATED}},
    }
    request, records = stored(with_field("fluid.dynamic_viscosity", field))
    assert isinstance(request, dict)
    target = request["target"]
    assert isinstance(target, dict)
    acceptance: dict[str, JsonValue] = {**IMPLIED, "record": target["record"]}
    request["acceptances"] = [acceptance]
    request["operating_conditions"] = {"temperature": {"value": 330.0, "unit": "K"}}
    result = read(request, records)
    assert set(result.reasons) == {
        Reason("condition_outside", "temperature"),
        Reason("condition_unstated", "shear_rate"),
        Reason("condition_unchecked", "density_kind"),
    }
    assert result.applied == (0,)
    assert "applied" not in result.to_json()
    assert ReadResult.from_json(result.to_json()) == result


# An implied condition located elsewhere (`read_side_contract.md` section 1): one naming another field,
# another record (another version or content hash), a region beside the record, an interval or no location
# is checked and not applied. Each implies a shear rate the record leaves unstated, beside a temperature
# outside its tolerance, which ends the read at step 10 so that its entries are returned: applied, the shear
# rate would be `condition_unchecked`, the request giving it no tolerance.
ELSEWHERE = (
    "another_field",
    "another_version",
    "another_content_hash",
    "a_region_beside_the_record",
    "an_interval",
    "no_location",
)
AT_THE_READ = "at_the_read"


def implying_a_shear_rate(where: str) -> tuple[JsonValue, RecordStore]:
    """A request at 330 K for a water field in vivo, its implied condition `AT_THE_READ` or at a location
    `ELSEWHERE`."""
    assert where in (AT_THE_READ, *ELSEWHERE)
    field: dict[str, JsonValue] = {
        **water_field(),
        "specimen": {"tissue_state": {"token": "in_vivo", **STATED}},
    }
    request, records = stored(with_field("fluid.dynamic_viscosity", field))
    assert isinstance(request, dict)
    target = request["target"]
    assert isinstance(target, dict)
    pin = target["record"]
    assert isinstance(pin, dict)
    acceptance: dict[str, JsonValue] = {
        **IMPLIED,
        "record": dict(pin),
        "implies": {"shear_rate": {"value": 100.0, "unit": "1/s"}},
    }
    if where == "another_field":
        acceptance["field"] = "bulk.density"
    elif where == "another_version":
        acceptance["record"] = {**pin, "version": "9.0.0"}
    elif where == "another_content_hash":
        acceptance["record"] = {**pin, "content_hash": "sha256:" + "f" * 64}
    elif where == "a_region_beside_the_record":
        acceptance["region"] = "lumen"
    elif where == "an_interval":
        del acceptance["record"]
        acceptance["interval"] = 0.0
    elif where == "no_location":
        del acceptance["record"]
    request["acceptances"] = [acceptance]
    request["operating_conditions"] = {"temperature": {"value": 330.0, "unit": "K"}}
    return request, records


def check_located_elsewhere(where: str) -> None:
    result = read(*implying_a_shear_rate(where))
    assert set(result.reasons) == {
        Reason("condition_outside", "temperature"),
        Reason("condition_unstated", "shear_rate"),
    }, where
    assert result.conditions is not None
    assert {entry.name: (entry.status, entry.record) for entry in result.conditions} == {
        "temperature": ("not_met", {"value": 310.15, "unit": "K", **STATED}),
        "shear_rate": ("unknown", {"status": "unstated"}),
    }, where
    assert result.applied == (), where


@pytest.mark.parametrize("where", ELSEWHERE)
def test_an_implied_condition_located_elsewhere_leaves_its_condition_unstated(where: str) -> None:
    check_located_elsewhere(where)


def test_an_implied_condition_at_the_reads_own_location_fills_its_condition() -> None:
    """The control: the same implied condition, located at the read, is applied."""
    result = read(*implying_a_shear_rate(AT_THE_READ))
    assert set(result.reasons) == {
        Reason("condition_outside", "temperature"),
        Reason("condition_unchecked", "shear_rate"),
    }
    assert result.applied == (0,)
    with pytest.raises(AssertionError):
        check_located_elsewhere(AT_THE_READ)


# Steps 11 to 13 for a constant, and the result (`read_side_contract.md` sections 2, 3 and 6).

SHEAR_RATE: dict[str, JsonValue] = {"range": [10.0, 1000.0], "unit": "1/s", **STATED}
MET_REQUEST: dict[str, JsonValue] = {
    "operating_conditions": {
        "temperature": {"value": 310.15, "unit": "K"},
        "shear_rate": {"value": 100.0, "unit": "1/s"},
    },
    "requirement": {
        "want": "value",
        "conditions": {
            "temperature": {"tolerance": {"value": 1.0, "unit": "K"}},
            "shear_rate": {"tolerance": {"value": 0.0, "unit": "1/s"}},
        },
    },
}


def met_field(**members: JsonValue) -> dict[str, JsonValue]:
    """The water constant, its every condition stated and met by `MET_REQUEST`, with `members` set."""
    field = water_field()
    conditions = field["conditions"]
    assert isinstance(conditions, dict)
    conditions["shear_rate"] = dict(SHEAR_RATE)
    return field | members


def read_met(
    field: JsonValue, *, want: str = "value", claims: Collection[Suite] = ("plain_read", "hash")
) -> ReadResult:
    request, records = stored(with_field("fluid.dynamic_viscosity", field))
    assert isinstance(request, dict)
    request.update(copy.deepcopy(MET_REQUEST))
    requirement = request["requirement"]
    assert isinstance(requirement, dict)
    requirement["want"] = want
    return read(request, records, claims=claims)


def test_a_met_constant_returns_its_value_and_the_members_beside_it() -> None:
    result = read_met(met_field())
    assert (result.status, result.reasons) == ("met", ())
    written = json.loads(json.dumps(result.to_json()))
    assert list(written) == [
        "status", "reasons", "value", "unit", "conditions", "specimen", "statistics", "provenance", "labels"
    ]  # fmt: skip
    assert written["value"] == 0.000692
    assert written["unit"] == "Pa.s"
    assert written["specimen"] == {}
    assert written["provenance"] == {
        "origin": "measured_by_contributor",
        "review": {
            "status": "not_checked",
            "reason": "conformance fixture: illustrative values, not a measurement",
        },
    }
    assert written["labels"] == ["materica.fluid.newtonian.v1"]


# A label's basis (`record_format.md` section 4.1): "A reader checks only its name: for slips, as it checks
# every member named at its place (section 10 item 5), and beside `alternatives` (section 5). It neither
# checks its shape nor returns it, so no read depends on it." [PR-030]
LABEL_BASES = [
    pytest.param({"basis": "stated"}, id="stated"),
    pytest.param({"basis": "inferred", "inferred_from": "a curator's reading of the source"}, id="inferred"),
    pytest.param({"basis": "guessed", "x_note": 1.0}, id="breaking_its_shape"),
    pytest.param(5.0, id="not_an_object"),
]


@pytest.mark.parametrize("basis", LABEL_BASES)
def test_a_labels_basis_is_neither_checked_nor_returned(basis: JsonValue) -> None:
    without = json.loads(json.dumps(read_met(met_field()).to_json()))
    result = read_met(met_field(label_basis=basis))
    assert (result.status, result.reasons) == ("met", ())
    assert json.loads(json.dumps(result.to_json())) == without


@pytest.mark.parametrize("slip", ["label_basi", "label_bases", "labelbasis", "label_basiss", "lable_basis"])
def test_a_member_one_slip_from_a_labels_basis_refuses_the_field(slip: str) -> None:
    """`record_format.md` section 10 item 5: a member one slip from one named at a field's place refuses the
    field, `label_basis` among them (section 5)."""
    basis: JsonValue = {"basis": "stated"}
    result = read_met(met_field(**{slip: basis}))
    assert (result.status, [reason.code for reason in result.reasons]) == ("not_met", ["form_invalid"]), slip


def test_a_labels_basis_beside_alternatives_refuses_the_field() -> None:
    """`record_format.md` section 5: the object holding `alternatives` holds no member of a value field, and
    `label_basis` is one."""
    assert read_met({"alternatives": [met_field()]}).status == "met"
    result = read_met({"alternatives": [met_field()], "label_basis": {"basis": "stated"}})
    assert (result.status, [reason.code for reason in result.reasons]) == ("not_met", ["form_invalid"])


@pytest.mark.parametrize("held", [{"status": "withheld"}, {"status": "withheld", "reason": "licensed"}])
def test_a_statistics_block_held_as_a_status_object_is_returned_as_one(held: dict[str, JsonValue]) -> None:
    """`provenance.md` section 1 item 4: a reader returns a status as a status, here the one a constant's
    statistics row allows. Fuzz target 4 found it returned as an empty block, against the reference model."""
    written = json.loads(json.dumps(read_met(met_field(statistics=held)).to_json()))
    assert written["statistics"] == held


RESULT_SCHEMA = validator("read_result.json")
NOT_CHECKED: JsonValue = {"status": "not_checked"}
# A review a status object stands for, and what a read returns of it (`provenance.md` section 2 item 6): as
# found where it keeps its shape (section 1 item 5), else `not_checked`, since a review never refuses.
NOT_CHECKED_REVIEWS = [
    pytest.param(
        {"status": "not_checked", "reason": "r"}, {"status": "not_checked", "reason": "r"}, id="as_found"
    ),
    pytest.param(
        {"status": "not_checked", "reason": "r", "x_note": 1.0},
        {"status": "not_checked", "reason": "r"},
        id="an_unknown_member_left_out",
    ),
    pytest.param({"status": "not_checked", "reason": 5.0}, NOT_CHECKED, id="a_reason_not_a_string"),
    pytest.param({"status": "not_checked", "reason": None}, NOT_CHECKED, id="a_reason_null"),
    pytest.param(
        {"status": "not_checked", "reason": "r", "result": "reviewed"}, NOT_CHECKED, id="beside_a_result"
    ),
    pytest.param(
        {"status": "not_checked", "reason": "r", "reviewer": "a"}, NOT_CHECKED, id="beside_a_reviewer"
    ),
]


@pytest.mark.parametrize(("review", "returned"), NOT_CHECKED_REVIEWS)
def test_a_not_checked_review_is_returned_as_found_only_where_it_keeps_its_shape(
    review: JsonValue, returned: JsonValue
) -> None:
    """S2a-4's review, L5 (a `reason` that is no string was returned as found, and the result then failed
    `read_result.json`) and L3's M25 (a `reason` kept beside a `result`)."""
    field = met_field()
    field["provenance"] = {**an_object(field["provenance"]), "review": review}
    written = json.loads(json.dumps(read_met(field).to_json()))
    assert written["provenance"]["review"] == returned
    assert RESULT_SCHEMA(written) == []


DERIVED_OFF_PATTERN: dict[str, JsonValue] = {
    "origin": "derived",
    "review": {"status": "not_checked"},
    "derivation": {
        "method": "a conversion",
        "inputs": [
            {
                "record": {"id": "Not An Id", "version": "1.0", "content_hash": "sha256:x"},
                "field": "fluid.density",
            }
        ],
        "assumptions": [],
        "input_specimens": [{"input": 0.0, "specimen": {}}],
    },
}
SITE: dict[str, JsonValue] = {"uberon": "UBERON:liver", "label": "liver", "basis": "stated"}


def test_a_result_of_a_record_the_writer_refuses_validates_where_the_read_takes_it() -> None:
    """S2a-4's review, L1: step 8 checks an anatomical site's `uberon` and a derivation input's pinned record
    as strings alone (RC-039; `provenance.md` section 5), so a read takes both off their writer patterns, and
    `read_result.json` takes the result. It keeps the writer's closed structure: a member no shape defines,
    which a result never holds, inside a returned fact or input is refused."""
    field = met_field(specimen={"anatomical_site": SITE}, provenance=DERIVED_OFF_PATTERN)
    written = json.loads(json.dumps(read_met(field).to_json()))
    assert written["specimen"] == {"anatomical_site": SITE}
    assert written["provenance"]["derivation"]["inputs"][0]["record"]["id"] == "Not An Id"
    assert RESULT_SCHEMA(written) == []
    unknown = copy.deepcopy(written)
    unknown["specimen"]["anatomical_site"]["x_note"] = 1.0
    assert RESULT_SCHEMA(unknown) != []
    unknown = copy.deepcopy(written)
    unknown["provenance"]["derivation"]["inputs"][0]["record"]["x_note"] = 1.0
    assert RESULT_SCHEMA(unknown) != []


def test_a_want_the_constant_cannot_give_keeps_the_conditions_and_labels_but_returns_no_value() -> None:
    for want in ("bounds", "components", "evidence"):
        result = read_met(met_field(), want=want)
        assert (result.status, result.reasons) == ("not_met", (Reason("want_mismatch"),)), want
        written = json.loads(json.dumps(result.to_json()))
        assert set(written) == {"status", "reasons", "conditions", "labels"}, want
        assert "materica.fluid.newtonian.v1" in written["labels"], want


def test_the_suite_s_wants_on_a_constant_give_want_mismatch_but_fit_on_a_fitted_one_waits() -> None:
    """`read_side_contract.md` section 6: reference data on any other form, and a fit or a coverage on a field
    without one, give `want_mismatch`; reading a fitted field's fit record is the suite's, not built yet."""
    claims: tuple[Suite, ...] = ("plain_read", "hash", "fits_and_reference_data")
    for want in ("reference_data", "fit", "coverage"):
        result = read_met(met_field(), want=want, claims=claims)
        assert result.reasons == (Reason("want_mismatch"),), want
    with pytest.raises(NotImplementedError):
        read_met(met_field(fit={"model": "a fit record"}), want="fit", claims=claims)
    assert read_met(met_field(fit={"model": "a fit record"}), claims=claims).value == 0.000692


def test_a_result_writes_numbers_as_stored_and_each_count_and_index_as_an_integer() -> None:
    """`-0` stays `-0` (PR-047), never RFC 8785's form; a statistics block's counts and a derivation's input
    indexes are integers (the code design's rule 5)."""
    field = met_field(value=-0.0)
    statistics = field["statistics"]
    assert isinstance(statistics, dict)
    statistics["n_specimens"] = 3.0
    statistics["n_donors"] = -0.0
    field["provenance"] = DERIVED_INPUTS
    text = json.dumps(read_met(field).to_json())
    written = json.loads(text)
    assert '"value": -0.0' in text
    assert written["statistics"]["n_specimens"] == 3
    assert type(written["statistics"]["n_specimens"]) is int
    assert type(written["statistics"]["n_donors"]) is int
    inputs = written["provenance"]["derivation"]["input_specimens"]
    assert [entry["input"] for entry in inputs] == [0, 1]
    assert all(type(entry["input"]) is int for entry in inputs)


def test_a_result_shares_nothing_with_the_record_or_with_its_own_json() -> None:
    """The code design's rule 6: a member returned is a deep copy, and so is each result's JSON."""
    result = read_met(met_field())
    first = cast(dict[str, Any], result.to_json())
    first["statistics"]["central"] = "changed"
    first["provenance"]["review"]["status"] = "changed"
    again = cast(dict[str, Any], result.to_json())
    assert again["statistics"]["central"] == "stated"
    assert again["provenance"]["review"]["status"] == "not_checked"
    assert read_met(met_field()).to_json() == result.to_json()
    assert ReadResult.from_json(result.to_json()) == result


def test_a_derivation_returned_shares_nothing_with_the_stored_record() -> None:
    """Rule 6 through the Python API: a consumer that changes the derivation a result holds, the field's or
    an alternative's, changes no later read of the same store (S2a-4's review, L3's M51)."""
    alternatives: list[JsonValue] = [met_field(provenance=DERIVED_INPUTS)] * 2
    fields: list[JsonValue] = [met_field(provenance=DERIVED_INPUTS), {"alternatives": alternatives}]
    for field in fields:
        request, records = stored(with_field("fluid.dynamic_viscosity", field))
        assert isinstance(request, dict)
        request.update(copy.deepcopy(MET_REQUEST))
        first = read(request, records)
        reads = first.alternative_values or (first,)
        for each in reads:
            assert each.provenance is not None
            assert each.provenance.derivation is not None
            each.provenance.derivation["method"] = "changed"
            an_object(a_list(each.provenance.derivation["inputs"])[0])["field"] = "changed"
        later = read(request, records)
        for each in later.alternative_values or (later,):
            assert each.provenance is not None
            assert each.provenance.derivation == DERIVED_INPUTS["derivation"]


def test_a_review_returned_as_found_shares_nothing_with_the_stored_record() -> None:
    """Rule 6 for a member no shape types: a review never refuses, so a reviewed review is returned as found
    whatever its members hold, an object or a list of them included; a consumer that changes one through the
    Python API changes no later read of the same store (S2a-4's fix round: hand mutant M45, which the
    review's run saw killed by a monotonicity property, survived the whole suite here)."""
    review: dict[str, JsonValue] = {
        "result": "reviewed",
        "reviewer": {"name": "a"},
        "checklist": [{"item": "b"}],
    }
    field = met_field()
    field["provenance"] = {**an_object(field["provenance"]), "review": review}
    request, records = stored(with_field("fluid.dynamic_viscosity", field))
    assert isinstance(request, dict)
    request.update(copy.deepcopy(MET_REQUEST))
    first = read(request, records)
    assert first.provenance is not None
    assert first.provenance.review == review
    an_object(first.provenance.review["reviewer"])["name"] = "changed"
    an_object(a_list(first.provenance.review["checklist"])[0])["item"] = "changed"
    later = read(request, records)
    assert later.provenance is not None
    assert later.provenance.review == review


def test_only_a_derived_value_returns_its_derivation_and_its_mixed_conditions_label() -> None:
    """`provenance.md` section 2 item 6 checks `derivation` for origin `derived` alone, and SQ45 labels a
    derived value whose inputs' conditions differ: a derivation beside another origin is a member the read
    does not check, neither returned nor labelled (S2a-4's review, L3's M04 and M21)."""
    derivation = {**an_object(DERIVED_INPUTS["derivation"]), "mixed_conditions": True}
    for origin in ("derived", "measured_by_contributor"):
        provenance: dict[str, JsonValue] = {
            **an_object(met_field()["provenance"]),
            "origin": origin,
            "derivation": derivation,
        }
        written = json.loads(json.dumps(read_met(met_field(provenance=provenance)).to_json()))
        derived = origin == "derived"
        assert ("derivation" in written["provenance"]) is derived, origin
        assert ("mixed_conditions" in written["labels"]) is derived, origin


def test_a_derivation_inputs_reference_holding_status_returns_its_three_members() -> None:
    """A member named `status` where no status object stands is one the reader does not know (`provenance.md`
    section 1 item 5), left out of the reference returned (S2a-4's review, L3's M29)."""
    derivation = copy.deepcopy(an_object(DERIVED_INPUTS["derivation"]))
    reference = an_object(an_object(a_list(derivation["inputs"])[0])["record"])
    pin = dict(reference)
    reference["status"] = "not_checked"
    provenance: dict[str, JsonValue] = {**DERIVED_INPUTS, "derivation": derivation}
    written = json.loads(json.dumps(read_met(met_field(provenance=provenance)).to_json()))
    assert written["provenance"]["derivation"]["inputs"][0]["record"] == pin


def met_interval(**interval: JsonValue) -> dict[str, JsonValue]:
    """The water field as an interval met by `MET_REQUEST`, holding `interval`, and no label, which only a
    constant or a table may carry."""
    field = met_field(form="interval", interval=interval)
    del field["value"], field["label"]
    return field


def met_composition(**composition: JsonValue) -> dict[str, JsonValue]:
    """A composition read as `fluid.dynamic_viscosity` is, but for its row: `bulk.elemental_composition`."""
    return {**COMPOSITION, "conditions": met_field()["conditions"], "composition": composition}


def read_composition(
    field: JsonValue,
    *,
    want: str = "components",
    claims: Collection[Suite] = ("plain_read", "hash"),
    acceptances: Collection[dict[str, JsonValue]] = (),
) -> ReadResult:
    """`field` as `bulk.elemental_composition`, read under `want`, with `acceptances`, each located at the
    target's record."""
    name = "bulk.elemental_composition"
    request, records = stored(with_field(name, field), name)
    assert isinstance(request, dict)
    request.update(copy.deepcopy(MET_REQUEST))
    requirement = request["requirement"]
    assert isinstance(requirement, dict)
    requirement["want"] = want
    if acceptances:
        pin = cast(dict[str, JsonValue], request["target"])["record"]
        request["acceptances"] = [{**acceptance, "record": pin} for acceptance in acceptances]
    return read(request, records, claims=claims)


def test_an_interval_returns_its_bounds_with_their_basis_as_stored_and_a_none_as_a_status() -> None:
    """`read_side_contract.md` section 6: `want: bounds` gives `{"lower", "upper", "basis"}`, as stored
    [PR-022]; section 2 item 5: numbers as read, status objects as status objects, a member the reader does
    not know left out."""
    stored_interval: dict[str, JsonValue] = {
        "lower": -0.0,
        "upper": {"status": "none"},
        "basis": "stated_bound",
    }
    result = read_met(met_interval(**stored_interval, x_unknown_member=1.0), want="bounds")
    assert (result.status, result.reasons) == ("met", ())
    text = json.dumps(result.to_json())
    assert json.loads(text)["value"] == stored_interval
    assert '"lower": -0.0' in text
    for want in ("value", "components", "evidence"):
        refused = read_met(met_interval(**stored_interval), want=want)
        assert (refused.status, refused.reasons, refused.value) == (
            "not_met",
            (Reason("want_mismatch"),),
            None,
        )


def test_a_composition_is_returned_as_stored_never_normalised_its_component_counts_as_integers() -> None:
    """`record_format.md` section 6, composition items 2 to 4: the basis, the sum rule, a stated sum and the
    components as stored, nothing normalised [PR-023], a component's statistics returned with it [PR-051];
    the code design's rule 5: a count is written as an integer, wherever its block sits."""
    statistics = {**cast(dict[str, JsonValue], COMPOSITION["statistics"]), "n_specimens": 3.0}
    oxygen: dict[str, JsonValue] = {"component": "element:O", "fraction": 0.723, "statistics": statistics}
    composition: dict[str, JsonValue] = {
        "basis": "mass_fraction",
        "sum_rule": "sums_to_one",
        "stated_sum": 0.825,
        "components": [HYDROGEN, {**oxygen, "x_unknown_member": 1.0}],
    }
    result = read_composition(met_composition(**composition))
    assert (result.status, result.reasons) == ("met", ())
    written = json.loads(json.dumps(result.to_json()))
    assert written["value"] == {**composition, "components": [HYDROGEN, {**oxygen, "statistics": statistics}]}
    assert type(written["value"]["components"][1]["statistics"]["n_specimens"]) is int
    for want in ("value", "bounds", "evidence"):
        refused = read_composition(met_composition(**composition), want=want)
        assert (refused.status, refused.reasons, refused.value) == (
            "not_met",
            (Reason("want_mismatch"),),
            None,
        )


BOUND_ORDER: list[tuple[dict[str, JsonValue], ReasonCode | None]] = [
    ({"lower": 2.0, "upper": 1.0}, "form_invalid"),
    ({"lower": {"status": "none"}, "upper": {"status": "none"}}, "form_invalid"),
    ({"lower": "0.4", "upper": 1.0}, "form_invalid"),
    ({"lower": {"status": "unstated"}, "upper": 1.0}, "form_invalid"),
    ({"lower": 1.0, "upper": 1.0}, None),
    ({"lower": 0.0, "upper": -0.0}, None),
    ({"lower": {"status": "none"}, "upper": 1.0}, None),
    ({"lower": 1.0e308, "upper": {"status": "none"}}, None),
    # A status token the reader does not know is never read as one it knows, here `none` (`record_format.md`
    # section 10 item 3), so beside a `none` it gives `unknown_token` alone (PR #37's review, H12).
    ({"lower": {"status": "unbounded"}, "upper": {"status": "none"}}, "unknown_token"),
    ({"lower": {"status": "none"}, "upper": {"status": "unbounded"}}, "unknown_token"),
]


@pytest.mark.parametrize(("bounds", "code"), BOUND_ORDER)
def test_an_intervals_bounds_are_numbers_at_most_one_none_and_in_order(
    bounds: dict[str, JsonValue], code: ReasonCode | None
) -> None:
    """`record_format.md` section 6, interval item 1 [PR-050]; numbers compare by value, so `-0` equals
    `0`."""
    result = read_met(met_interval(**bounds, basis="reported_range"), want="bounds")
    assert result.reasons == ((Reason(code),) if code else ()), bounds


COMPONENTS: list[tuple[JsonValue, ReasonCode | None]] = [
    ([], "form_invalid"),
    ({"component": "element:H", "fraction": 0.1}, "form_invalid"),
    ([HYDROGEN, {**HYDROGEN, "fraction": 0.2}], "form_invalid"),
    # A repeat is found wherever it stands, not only next to its first (PR #37's review, H19).
    ([HYDROGEN, {"component": "element:O", "fraction": 0.7}, {**HYDROGEN, "fraction": 0.2}], "form_invalid"),
    ([{**HYDROGEN, "fraction": -0.01}], "form_invalid"),
    ([{**HYDROGEN, "fraction": 1.01}], "form_invalid"),
    ([{**HYDROGEN, "fraction": "0.1"}], "form_invalid"),
    ([{"component": "element:H"}], "form_invalid"),
    ([{**HYDROGEN, "statistics": {"central": "stated"}}], "form_invalid"),
    ([{**HYDROGEN, "component": "element:Xx"}], "unknown_token"),
    ([{**HYDROGEN, "component": "water"}], "unknown_token"),
    ([{**HYDROGEN, "component": "element:h"}], "unknown_token"),
    ([{**HYDROGEN, "fraction": 0.0}, {"component": "element:O", "fraction": 1.0}], None),
    ([{**HYDROGEN, "fraction": -0.0}], None),
    ([{**HYDROGEN, "statistics": {"status": "withheld"}}], None),
]


@pytest.mark.parametrize(("components", "code"), COMPONENTS)
def test_a_compositions_components_are_a_non_empty_list_each_once_a_known_element_a_fraction_in_0_1(
    components: JsonValue, code: ReasonCode | None
) -> None:
    """`record_format.md` section 6, composition items 1, 3 and 5 [PR-051]."""
    composition: dict[str, JsonValue] = {
        "basis": "mass_fraction",
        "sum_rule": "partial",
        "components": components,
    }
    result = read_composition(met_composition(**composition))
    assert result.reasons == ((Reason(code),) if code else ()), components


# Each form step 8 reads: how a field of it is read, and the `want` that gives its own member.
READERS: dict[str, tuple[Callable[..., ReadResult], str]] = {
    "constant": (read_met, "value"),
    "interval": (read_met, "bounds"),
    "composition": (read_composition, "components"),
}
MEMBERS: dict[str, JsonValue] = {
    "constant": 0.000692,
    "interval": {"lower": 0.0006, "upper": 0.0008, "basis": "reported_range"},
    "composition": {"basis": "mass_fraction", "sum_rule": "partial", "components": [HYDROGEN]},
}


def own_field(form: str, own: JsonValue) -> dict[str, JsonValue]:
    """A field of `form` met by `MET_REQUEST`, its own member `own`."""
    if form == "constant":
        return met_field(value=own)
    if form == "interval":
        field = met_interval()
        field["interval"] = own
        return field
    return {**met_composition(), "composition": own}


@pytest.mark.parametrize(
    ("form", "marker"),
    [
        ("constant", {"status": "withheld", "x_unknown_member": 1.0}),
        ("interval", {"status": "withheld", "lower": 0.0006}),
        ("composition", {"status": "withheld", "components": [HYDROGEN]}),
    ],
)
def test_a_withheld_marker_that_breaks_its_shape_refuses_its_field_as_form_invalid_alone(
    form: str, marker: dict[str, JsonValue]
) -> None:
    """`provenance.md` section 1 item 5: "A status object that breaks its shape is read for nothing else, so
    its token gives no reason of its own": a constant's beside any member but `reason`, where S is a number,
    an interval's or a composition's beside a member S defines (PR #37's review, H32)."""
    reader, want = READERS[form]
    result = reader(own_field(form, marker), want=want)
    assert (result.status, result.reasons) == ("not_met", (Reason("form_invalid"),)), form


@pytest.mark.parametrize("form", ["constant", "interval", "composition"])
def test_want_fit_on_a_fitted_field_of_each_form_waits_for_the_fits_suite(form: str) -> None:
    """`read_side_contract.md` section 6: `want: fit` returns a fitted field's `fit` record, which the fits
    and reference data suite reads, not built yet; on a field without one it gives `want_mismatch` (PR #37's
    review, H42)."""
    claims: tuple[Suite, ...] = ("plain_read", "hash", "fits_and_reference_data")
    reader, _ = READERS[form]
    field = own_field(form, MEMBERS[form])
    assert reader(field, want="fit", claims=claims).reasons == (Reason("want_mismatch"),)
    with pytest.raises(NotImplementedError):
        reader({**field, "fit": {"model": "a fit record"}}, want="fit", claims=claims)


# Each own-member place, and a member there one slip from a member the field's own shape names, which the
# member's shape does not (`record_format.md` section 10 items 1 and 5: a slip refuses only "from a member the
# shape names at that place").
SLIPS_NAMED_ELSEWHERE: list[tuple[str, str, str]] = [
    ("interval", "interval", "values"),
    ("interval", "interval", "forms"),
    ("composition", "composition", "units"),
    ("composition", "component", "values"),
    ("composition", "component", "forms"),
]


@pytest.mark.parametrize(("form", "place", "slip"), SLIPS_NAMED_ELSEWHERE)
def test_a_slip_of_a_member_named_at_another_place_is_ignored_in_an_own_member(
    form: str, place: str, slip: str
) -> None:
    """Ignored, and left out of the value returned (PR #37's review, H10)."""
    reader, want = READERS[form]
    own = cast(dict[str, JsonValue], copy.deepcopy(MEMBERS[form]))
    holder = own if place == form else cast(dict[str, JsonValue], cast(list[JsonValue], own["components"])[0])
    holder[slip] = 1.0
    result = reader(own_field(form, own), want=want)
    assert (result.status, result.reasons, result.value) == ("met", (), MEMBERS[form]), (place, slip)


# Evidence (`record_format.md` section 4.3; SQ44).


EVIDENCE_FIXTURE = WATER.with_name("evidence_fixture.json")
EVIDENCE_PROVENANCE: dict[str, JsonValue] = {
    "origin": "measured_by_contributor",
    "extraction": {"method": "own_measurement"},
    "assistance": {"status": "none"},
    "review": {"status": "not_checked"},
}
REPORT: dict[str, JsonValue] = {
    "endpoint": "cytotoxicity",
    "standard": {"designation": "ISO 10993-5", "year": 2009.0},
    "contact_category": "the source's words",
    "contact_duration": "the source's words",
    "material_form": "the source's words",
    "processing": "the source's words",
    "reported_result": "the source's words",
    "provenance": EVIDENCE_PROVENANCE,
}
WITHHELD_REPORT: dict[str, JsonValue] = {
    **{name: {"status": "withheld"} for name in REPORT if name != "provenance"},
    "provenance": {**EVIDENCE_PROVENANCE, "recipe": {"steps": "Table 3, row 2"}},
}


def read_evidence(
    evidence: JsonValue,
    *,
    want: str = "evidence",
    members: dict[str, JsonValue] | None = None,
    acceptances: Collection[dict[str, JsonValue]] = (),
) -> ReadResult:
    """The evidence fixture's field, holding `evidence` and `members`, read under `want`, with `acceptances`,
    each located at the evidence record."""
    name = "biocompatibility.evidence"
    record: dict[str, JsonValue] = json.loads(EVIDENCE_FIXTURE.read_text(encoding="utf-8"))
    field = cast(dict[str, Any], record)["body"]["sections"]["biocompatibility"]["fields"]["evidence"]
    field.update({"evidence": evidence, **(members or {})})
    request, records = stored(record, name)
    assert isinstance(request, dict)
    request["requirement"] = {"want": want}
    del request["operating_conditions"]
    if acceptances:
        pin = cast(dict[str, JsonValue], request["target"])["record"]
        request["acceptances"] = [{**acceptance, "record": pin} for acceptance in acceptances]
    return read(request, records)


def test_evidence_returns_its_reports_as_stored_each_provenance_whole_and_no_statistics() -> None:
    """`record_format.md` section 4.3 item 2: "A reader returns an entry with its statuses and its
    `provenance` whole, holding the members `read_side_contract.md` section 2 item 5 defines": a member the
    reader does not know left out at every depth, and the review as `provenance.md` section 2 item 6 reads
    every review [PR-038] [PR-337]; section 2 item 6: evidence has no statistics."""
    source: dict[str, JsonValue] = {
        "key": "smith2019",
        "document": {"identifier": "doi:10.1000/xyz123", "version": "version_of_record"},
    }
    provenance: dict[str, JsonValue] = {
        **EVIDENCE_PROVENANCE,
        "origin": "measured_by_source",
        "source": source,
    }
    report: dict[str, JsonValue] = {
        **REPORT,
        "contact_duration": {"status": "unstated", "reason": "not in the report"},
        "provenance": provenance,
    }
    unknown: dict[str, JsonValue] = {"x_unknown_member": 1.0}
    document: dict[str, JsonValue] = {**cast(dict[str, JsonValue], source["document"]), **unknown}
    stored_source: dict[str, JsonValue] = {**source, "document": document}
    stored_provenance: dict[str, JsonValue] = {
        **provenance,
        **unknown,
        "source": stored_source,
        "review": {"status": "unstated"},
    }
    standard: dict[str, JsonValue] = {**cast(dict[str, JsonValue], REPORT["standard"]), **unknown}
    stored_report: dict[str, JsonValue] = {
        **report,
        **unknown,
        "standard": standard,
        "provenance": stored_provenance,
    }
    result = read_evidence([stored_report, WITHHELD_REPORT], members={"statistics": {"central": "stated"}})
    assert (result.status, result.reasons) == ("unknown", (Reason("entries_withheld"),))
    written = json.loads(json.dumps(result.to_json()))
    reviewed: dict[str, JsonValue] = {
        **report,
        "provenance": {**provenance, "review": {"status": "not_checked"}},
    }
    assert written["value"] == [reviewed, WITHHELD_REPORT]
    assert "statistics" not in written
    cast(list[Any], result.value)[0]["endpoint"] = "changed"
    assert read_evidence([stored_report, WITHHELD_REPORT]).to_json() == written
    for want in ("value", "bounds", "components"):
        refused = read_evidence([REPORT], want=want)
        assert (refused.status, refused.reasons, refused.value) == (
            "not_met",
            (Reason("want_mismatch"),),
            None,
        )


def test_a_reports_placeholder_comes_back_whole_and_a_named_member_by_its_shape() -> None:
    """A provenance member whose members the version does not name yet, a placeholder (`assistance`: the
    tool, model and provider as reported), holds any member, so it comes back whole; one whose members it
    names (`extraction`) holds those alone (`read_side_contract.md` section 2 item 5)."""
    assistance: dict[str, JsonValue] = {"tool": "a reader", "settings": {"temperature": 0.0}}
    extraction: dict[str, JsonValue] = {
        "method": "table",
        "text_extraction": "a tool",
        "x_unknown_member": 1.0,
    }
    report = report_with(
        provenance={**EVIDENCE_PROVENANCE, "assistance": assistance, "extraction": extraction}
    )
    written = json.loads(json.dumps(read_evidence([report]).to_json()))
    provenance = written["value"][0]["provenance"]
    assert provenance["assistance"] == assistance
    assert provenance["extraction"] == {"method": "table", "text_extraction": "a tool"}


def test_a_reports_provenance_reads_its_review_and_its_per_parameter_provenances_as_every_provenance() -> (
    None
):
    """`provenance.md` section 2 item 6: "Every other review reads as `{"status": "not_checked"}`: one that
    is `null`, absent or not an object, ..."; `read_side_contract.md` section 2 item 5: "A member the reader
    does not know is left out", at every depth, in each provenance `per_parameter` maps a name to (S2b-2's
    review, L1: M65 and M31)."""
    without_review = {name: member for name, member in EVIDENCE_PROVENANCE.items() if name != "review"}
    per_parameter: dict[str, JsonValue] = {
        "a": {**EVIDENCE_PROVENANCE, "x_unknown_member": 1.0, "review": {"status": "bogus"}}
    }
    result = read_evidence(
        [
            report_with(provenance=without_review),
            report_with(provenance={**EVIDENCE_PROVENANCE, "per_parameter": per_parameter}),
        ]
    )
    assert (result.status, result.reasons) == ("met", ())
    first, second = (report["provenance"] for report in json.loads(json.dumps(result.to_json()))["value"])
    assert first == {**without_review, "review": {"status": "not_checked"}}
    assert second["per_parameter"] == {"a": {**EVIDENCE_PROVENANCE, "review": {"status": "not_checked"}}}


def report_with(**members: JsonValue) -> dict[str, JsonValue]:
    return {**REPORT, **members}


EVIDENCE_LISTS: list[tuple[JsonValue, set[ReasonCode]]] = [
    ([REPORT], set()),
    ([], {"form_invalid"}),
    # `provenance.md` section 1 item 5: the form's member, "except `evidence`, which never holds one".
    ({"status": "withheld"}, {"form_invalid"}),
    ([WITHHELD_REPORT], {"withheld"}),
    ([WITHHELD_REPORT, WITHHELD_REPORT], {"withheld"}),
    ([REPORT, WITHHELD_REPORT], {"entries_withheld"}),
    # An entry that is not an object is not withheld, so not every entry is.
    ([1.0, WITHHELD_REPORT], {"form_invalid", "entries_withheld"}),
    # A withheld entry whose provenance breaks its shape is withheld still, its fault beside.
    ([{**WITHHELD_REPORT, "provenance": {"origin": 1.0}}], {"form_invalid", "withheld"}),
    # Withheld in part: "An entry is withheld whole, its provenance kept, or not at all".
    ([report_with(endpoint={"status": "withheld"})], {"form_invalid"}),
    (
        [{**WITHHELD_REPORT, "endpoint": "cytotoxicity"}, WITHHELD_REPORT],
        {"form_invalid", "entries_withheld"},
    ),
    # A marker that breaks its shape is read for nothing else, so it withholds nothing.
    ([{**WITHHELD_REPORT, "endpoint": {"status": "withheld", "x": 1.0}}], {"form_invalid"}),
    # "Every member of an entry is present": one missing a member, its others withheld, is not withheld whole,
    # so it gives no `withheld` of its own (S2b-2's review, L1: M15).
    ([{name: member for name, member in WITHHELD_REPORT.items() if name != "processing"}], {"form_invalid"}),
    # Any other status stands in a report's member, `unstated` for a duration the source does not give.
    ([report_with(contact_duration={"status": "unstated"})], set()),
    ([report_with(standard={"status": "not_applicable", "x_unknown_member": 1.0})], set()),
    ([report_with(standard={"status": "unstated", "year": 2009.0})], {"form_invalid"}),
    ([report_with(endpoint={"status": "unstated", "x_unknown_member": 1.0})], {"form_invalid"}),
    ([report_with(endpoint={"status": "untold"})], {"unknown_token"}),
    ([report_with(endpoint=5.0)], {"form_invalid"}),
    ([report_with(standard={"designation": "ISO 10993-5", "year": 2009.5})], {"form_invalid"}),
    ([report_with(standard={"designation": "ISO 10993-5"})], {"form_invalid"}),
    ([report_with(standard={"designation": "ISO 10993-5", "year": 2009.0, "yaer": 1.0})], {"form_invalid"}),
    ([report_with(endpiont="cytotoxicity")], {"form_invalid"}),
    ([{name: member for name, member in REPORT.items() if name != "processing"}], {"form_invalid"}),
    ([{name: member for name, member in REPORT.items() if name != "provenance"}], {"form_invalid"}),
    ([report_with(provenance={**EVIDENCE_PROVENANCE, "origin": "remembered"})], {"unknown_token"}),
    ([report_with(provenance={**EVIDENCE_PROVENANCE, "origin": "measured_by_source"})], {"form_invalid"}),
]


@pytest.mark.parametrize(("evidence", "codes"), EVIDENCE_LISTS)
def test_an_evidence_list_holds_one_report_or_more_each_withheld_whole_or_not_at_all(
    evidence: JsonValue, codes: set[ReasonCode]
) -> None:
    """`record_format.md` section 4.3 items 1 and 2, `read_side_contract.md` section 3 step 8: every entry
    withheld gives `withheld`, some `entries_withheld` [PR-052]; an entry's members by `provenance.md` section
    1 item 5's row, "any; `withheld` only in every one of them at once"; an entry's provenance checked as a
    field's is (`record_format.md` section 4.3 item 2, the maintainer's ruling of 2026-10-19)."""
    result = read_evidence(evidence)
    assert {reason.code for reason in result.reasons} == codes, evidence


EVIDENCE_MEMBERS: list[tuple[dict[str, JsonValue], str, set[ReasonCode]]] = [
    ({"conditions": {"temperature": {"status": "unstated"}}}, "not_met", {"form_invalid"}),
    ({"conditions": {"humidity": {"value": 0.5}}}, "unknown", {"condition_unknown_name"}),
    ({"conditions": []}, "not_met", {"form_invalid"}),
    ({"unit": "1"}, "not_met", {"unit_mismatch"}),
    ({"unit": {"status": "not_applicable", "reason": "a list of reports"}}, "met", set()),
    ({"statistics": {"status": "withheld"}}, "met", set()),
]


@pytest.mark.parametrize(("members", "status", "codes"), EVIDENCE_MEMBERS)
def test_evidence_takes_no_registered_condition_and_its_unit_is_a_status_object(
    members: dict[str, JsonValue], status: str, codes: set[ReasonCode]
) -> None:
    """`record_format.md` section 4.3 item 3: a registered condition is a shape error, a name the reader does
    not know gives `unknown` [PR-052]; section 4.1: the unit `{"status": "not_applicable"}` [PR-010]; a
    statistics block beside evidence, which has none, is a member a read neither checks nor returns."""
    result = read_evidence([REPORT], members=members)
    assert (result.status, {reason.code for reason in result.reasons}) == (status, codes), members


# Nominals (`declarations.md` section 4.1; `read_side_contract.md` sections 1, 2 and 6; SQ47).


PINNED_AT_THE_READ = "the read's record"  # stands, in a nominal below, for the target's record and its pin


def read_accepting(
    field: JsonValue, acceptances: list[dict[str, JsonValue]], *, want: str = "value"
) -> ReadResult:
    """`field` read as `read_met` reads it, with `acceptances`, each located at the target's record where its
    `record` is `PINNED_AT_THE_READ`."""
    request, records = stored(with_field("fluid.dynamic_viscosity", field))
    assert isinstance(request, dict)
    request.update(copy.deepcopy(MET_REQUEST))
    cast(dict[str, JsonValue], request["requirement"])["want"] = want
    pin = cast(dict[str, JsonValue], request["target"])["record"]
    request["acceptances"] = [
        {**acceptance, "record": pin} if acceptance.get("record") == PINNED_AT_THE_READ else acceptance
        for acceptance in acceptances
    ]
    return read(request, records)


def nominal(value: JsonValue = 0.0007, **members: JsonValue) -> dict[str, JsonValue]:
    """A nominal for the water field at the read's record, `members` changed in it, None removing one."""
    acceptance: dict[str, JsonValue] = {
        "acceptance": "nominal",
        "record": PINNED_AT_THE_READ,
        "field": "fluid.dynamic_viscosity",
        "value": value,
        "basis": "the midpoint of the limits",
        "reason": "a fixture's",
        **members,
    }
    return {name: member for name, member in acceptance.items() if member is not None}


NONE: dict[str, JsonValue] = {"status": "none"}
NOMINALS: list[tuple[dict[str, JsonValue], float, ReasonCode]] = [
    ({"lower": 0.0006, "upper": 0.0008}, 0.0007, "want_mismatch"),
    ({"lower": 0.0006, "upper": 0.0008}, 0.0006, "want_mismatch"),
    ({"lower": 0.0006, "upper": 0.0008}, 0.0008, "want_mismatch"),
    ({"lower": 0.0006, "upper": 0.0008}, math.nextafter(0.0008, 1.0), "nominal_invalid"),
    ({"lower": 0.0006, "upper": 0.0008}, math.nextafter(0.0006, 0.0), "nominal_invalid"),
    ({"lower": 0.0006, "upper": NONE}, 1.0e300, "want_mismatch"),
    ({"lower": 0.0006, "upper": NONE}, 0.0005, "nominal_invalid"),
    ({"lower": NONE, "upper": 0.0008}, -1.0, "want_mismatch"),
    ({"lower": NONE, "upper": 0.0008}, 0.0009, "nominal_invalid"),
    # Compared by value, as every number is: `-0` lies on the bound 0.
    ({"lower": 0.0, "upper": 0.0008}, -0.0, "want_mismatch"),
]


@pytest.mark.parametrize(("bounds", "given", "code"), NOMINALS)
def test_a_nominal_inside_or_on_an_intervals_bounds_supplies_the_value_and_one_outside_is_refused(
    bounds: dict[str, JsonValue], given: float, code: ReasonCode
) -> None:
    """Section 6: under `want: value`, "a declared nominal inside or on the bounds supplies `value` and
    `assumption`, and one outside them gives `nominal_invalid` in place of `want_mismatch`, with no value",
    compared exactly, on the bounded side of a one-sided interval [PR-338]; section 2 item 3: the status stays
    `not_met` [PR-302]; `applied` holds the nominal's index where it supplied the value."""
    result = read_accepting(met_interval(**bounds, basis="specification_limits"), [IMPLIED, nominal(given)])
    assert (result.status, result.reasons) == ("not_met", (Reason(code),))
    written = json.loads(json.dumps(result.to_json()))
    if code == "want_mismatch":
        assert result.applied == (1,)
        assert struct.pack(">d", written["value"]) == struct.pack(">d", given)
        assert written["assumption"] == {"acceptance": "nominal", "value": given}
        assert {"unit", "conditions", "specimen", "statistics", "provenance"} <= written.keys()
        assert ReadResult.from_json(result.to_json()) == result
    else:
        assert result.applied == ()
        assert {"value", "assumption", "unit", "statistics"}.isdisjoint(written)


def test_a_nominal_is_unused_under_bounds_and_on_a_form_that_gives_its_value() -> None:
    """Section 6: "under `want: bounds` it is not applied", and `applied` leaves it out; a constant gives its
    own value, an interval read under `want: components` `want_mismatch` alone."""
    interval = met_interval(lower=0.0006, upper=0.0008, basis="specification_limits")
    bounds = read_accepting(interval, [nominal(0.0009)], want="bounds")
    assert (bounds.status, bounds.reasons, bounds.applied, bounds.assumption) == ("met", (), (), None)
    constant = read_accepting(met_field(), [nominal(0.0009)])
    assert (constant.status, constant.value, constant.applied, constant.assumption) == (
        "met",
        0.000692,
        (),
        None,
    )
    components = read_accepting(interval, [nominal()], want="components")
    assert (components.reasons, components.value, components.assumption) == (
        (Reason("want_mismatch"),),
        None,
        None,
    )


def test_a_nominal_supplies_no_value_for_a_composition_or_evidence() -> None:
    """`declarations.md` section 4.1: a nominal "supplies a value for an interval"; section 6's table gives
    it in the interval's column alone, and `not_met` (`want_mismatch`) for a composition and for evidence
    under `want: value`, with no value (S2b-2's review, L1: M35)."""
    composition = read_composition(
        met_composition(**cast(dict[str, JsonValue], MEMBERS["composition"])),
        want="value",
        acceptances=[nominal(0.5, field="bulk.elemental_composition")],
    )
    evidence = read_evidence(
        [REPORT], want="value", acceptances=[nominal(1.0, field="biocompatibility.evidence")]
    )
    unused = ("not_met", (Reason("want_mismatch"),), None, None, ())
    assert [
        (result.status, result.reasons, result.value, result.assumption, result.applied)
        for result in (composition, evidence)
    ] == [unused, unused]


NOMINALS_ELSEWHERE: list[dict[str, JsonValue]] = [
    nominal(field="bulk.density"),
    nominal(record=None),
    nominal(record=None, region="lumen"),
    nominal(interval="skin"),
    nominal(region="lumen"),
    nominal(record={"id": "conformance/water_fixture", "version": "2.0.0", "content_hash": PIN}),
    nominal(record={"id": "conformance/water_fixture"}),
    nominal(record=1.0),
]


@pytest.mark.parametrize("elsewhere", NOMINALS_ELSEWHERE)
def test_a_nominal_naming_another_field_or_located_elsewhere_is_checked_and_not_applied(
    elsewhere: dict[str, JsonValue],
) -> None:
    """Section 1: "One naming another field, another record or region, an `interval` ... or no location is
    checked and not applied" [PR-338]; a location's shape is not checked, only compared."""
    result = read_accepting(
        met_interval(lower=0.0006, upper=0.0008, basis="specification_limits"), [elsewhere]
    )
    assert (result.status, result.reasons, result.value, result.applied) == (
        "not_met",
        (Reason("want_mismatch"),),
        None,
        (),
    )


NOMINAL_SHAPES: list[tuple[list[dict[str, JsonValue]], str]] = [
    ([nominal(value=None)], "refused"),
    ([nominal(value="0.0007")], "refused"),
    ([nominal(value=True)], "refused"),
    ([nominal(field="bulk.porosity")], "refused"),
    ([nominal(field="viscosity")], "refused"),
    ([nominal(field=None)], "refused"),
    ([nominal(vaule=0.0007)], "refused"),
    ([nominal(feild="fluid.dynamic_viscosity")], "refused"),
    ([nominal(record={"id": "x", "versoin": "1.0.0"})], "refused"),
    # "So do two acceptances of one kind, `nominal`, ... that name one field, whatever location or other
    # members each holds."
    ([nominal(), nominal(record=None, region="lumen", value="broken")], "refused"),
    ([nominal(), nominal(field="bulk.density")], "read"),
    # Its `reason` and `basis` are ignored; `params`, a parameter set's in place of a value, and a member no
    # document names, too.
    ([nominal(basis=1.0, reason=None, params={"a": 1.0}, x_unknown_member=1.0)], "read"),
    # "A nominal takes `params` in place of `value` only where the row of the field it names allows the form
    # `parameter_set`" (the maintainer's ruling of 2026-10-19, S2b-2's review M56): the water field's row
    # allows none, so `params` alone breaks its shape.
    ([nominal(value=None, params={"a": 1.0})], "refused"),
]


@pytest.mark.parametrize(("acceptances", "outcome"), NOMINAL_SHAPES)
def test_a_nominals_shape_is_checked_at_step_0_whatever_it_names(
    acceptances: list[dict[str, JsonValue]], outcome: str
) -> None:
    """Section 1: "Each acceptance is checked here, whatever field or location it names: its `field` as the
    target's is (the pattern, and a registered field), and its kind's own members, have their shapes; its
    `reason` and `basis` are ignored" [PR-330]."""
    result = read_accepting(
        met_interval(lower=0.0006, upper=0.0008, basis="specification_limits"), acceptances
    )
    if outcome == "refused":
        assert (result.status, result.reasons) == ("not_met", (Reason("request_incomplete"),)), acceptances
    else:
        assert result.reasons == (Reason("want_mismatch"),), acceptances
        assert result.value == 0.0007


WATER_PIN: dict[str, JsonValue] = {"id": "conformance/water_fixture", "version": "2.0.0", "content_hash": PIN}


def test_a_request_keeps_its_nominals_with_the_members_their_shape_names() -> None:
    request = with_members(acceptances=[nominal(record=WATER_PIN, params=[1.0]), IMPLIED])
    checked = ReadRequest.from_json(request)
    assert isinstance(checked, ReadRequest)
    (given,) = checked.nominals
    assert (given.index, checked.nominal()) == (0, given)
    acceptances = cast(list[JsonValue], checked.to_json().get("acceptances"))
    assert acceptances[0] == {
        "acceptance": "nominal",
        "record": WATER_PIN,
        "field": "fluid.dynamic_viscosity",
        "value": 0.0007,
    }
    assert ReadRequest.from_json(checked.to_json()) == checked


# An extrapolation (S3c; `declarations.md` section 4.1; `read_side_contract.md` sections 1, 2 and 5): checked
# at step 0 whatever it names, and applied at step 11 to a table read outside its readable range under `want:
# value`, at no declared edge and across none, where it names the read's field at the read's record.


def extrapolation(**members: JsonValue) -> dict[str, JsonValue]:
    """An extrapolation for the water field at the read's record, `members` changed in it, None removing
    one."""
    acceptance: dict[str, JsonValue] = {
        "acceptance": "extrapolation",
        "record": PINNED_AT_THE_READ,
        "field": "fluid.dynamic_viscosity",
        "method": "constant",
        "law": "the end value held",
        "basis": "the source's last point",
        "reason": "a fixture's",
        **members,
    }
    return {name: member for name, member in acceptance.items() if member is not None}


def read_at(
    at: float,
    acceptances: list[dict[str, JsonValue]],
    *,
    field: JsonValue = None,
    want: str = "value",
) -> ReadResult:
    """`field`, the viscosity table `met_table` gives by default, read as `read_accepting` reads it, at `at`
    K."""
    request, records = stored(with_field("fluid.dynamic_viscosity", field or met_table()))
    assert isinstance(request, dict)
    request.update(copy.deepcopy(MET_REQUEST))
    cast(dict[str, JsonValue], request["requirement"])["want"] = want
    cast(dict[str, JsonValue], request["operating_conditions"])["temperature"] = {"value": at, "unit": "K"}
    pin = cast(dict[str, JsonValue], request["target"])["record"]
    request["acceptances"] = [
        {**acceptance, "record": pin} if acceptance.get("record") == PINNED_AT_THE_READ else acceptance
        for acceptance in acceptances
    ]
    return read(request, records)


def axis_status(result: ReadResult) -> str:
    (entry,) = [entry for entry in result.conditions or () if entry.name == "temperature"]
    return entry.status


OUTSIDE = Reason("outside_range", "temperature")


@pytest.mark.parametrize(("at", "end"), [(290.0, 0.000853), (330.0, 0.000577), (-1e300, 0.000853)])
@pytest.mark.parametrize("method", ["constant", "consumer_law"])
def test_an_extrapolation_covers_outside_range_with_the_end_value_and_its_assumption(
    at: float, end: float, method: str
) -> None:
    """Section 5: "the result stays `not_met`, its reasons kept; the read goes on to steps 12 and 13, which
    add theirs; and the result carries the value at the range's nearest end, taken from inside the range, and
    `assumption`, the operating value being the axis entry's `operating`" [PR-307]; section 2: `assumption`
    is "`{"acceptance"}` with its kind's own members as the request gives them, `basis` aside", and the table
    the value is read from is returned "under an extrapolation too"; `applied` holds its index."""
    result = read_at(at, [nominal(), extrapolation(method=method)])
    assert (result.status, result.reasons, result.value) == ("not_met", (OUTSIDE,), end)
    assert result.assumption == {"acceptance": "extrapolation", "method": method, "law": "the end value held"}
    assert (result.table, result.applied) == (met_table()["table"], (1,))
    assert axis_status(result) == "not_met"
    assert result.labels == ("materica.fluid.newtonian.v1",)
    assert json.loads(json.dumps(result.to_json()))["assumption"] == result.assumption


def test_an_extrapolation_takes_the_end_of_a_narrower_source_range_from_inside_it() -> None:
    """Section 5: "the value at the range's nearest end, taken from inside the range": at a `source_range` end
    inside an interval, the table's value interpolated there, never `x[0]`'s."""
    field = met_table(source_range=[305.0, 315.0])
    result = read_at(301.0, [extrapolation()], field=field)
    assert (result.status, result.reasons) == ("not_met", (OUTSIDE,))
    assert result.value == evaluate.value([300.0, 320.0], [0.000853, 0.000577], "linear", 305.0)


def test_steps_12_and_13_run_under_an_extrapolation() -> None:
    """Section 3: "except step 11's `outside_range` under an extrapolation that applies (section 5), after
    which the read goes on to steps 12 and 13": a value stated without origin gives its reason, beside
    `outside_range`, and the field's label stands."""
    field = met_table()
    cast(dict[str, JsonValue], field["provenance"])["origin"] = "stated_without_origin"
    result = read_at(330.0, [extrapolation()], field=field)
    assert result.reasons == (OUTSIDE, Reason("stated_without_origin"))
    assert (result.status, result.value, result.labels) == (
        "not_met",
        0.000577,
        ("materica.fluid.newtonian.v1",),
    )


EDGED: dict[str, JsonValue] = {
    "x": [300.0, 310.0, 310.0, 320.0],
    "y": [9e-4, 8e-4, 7e-4, 6e-4],
    "edges": [310.0],
}
NOT_APPLIED: dict[str, tuple[float, dict[str, JsonValue], str, tuple[Reason, ...]]] = {
    "inside the range": (310.15, {}, "value", ()),
    "under want bounds": (330.0, {}, "bounds", (OUTSIDE,)),
    "at an edge inside the range": (310.0, EDGED, "value", (Reason("at_edge", "temperature"),)),
    "at an edge outside the range": (
        310.0,
        {**EDGED, "source_range": [311.0, 320.0]},
        "value",
        (Reason("at_edge", "temperature"), OUTSIDE),
    ),
    "across an edge outside the range": (
        305.0,
        {**EDGED, "source_range": [312.0, 320.0]},
        "value",
        (OUTSIDE,),
    ),
    "across an edge on the range's end": (
        305.0,
        {**EDGED, "source_range": [310.0, 320.0]},
        "value",
        (OUTSIDE,),
    ),
}


@pytest.mark.parametrize("situation", NOT_APPLIED)
def test_an_extrapolation_is_not_applied_in_the_range_under_another_want_or_at_or_across_an_edge(
    situation: str,
) -> None:
    """Section 5: "Under any other `want` an extrapolation is not applied, nor at a declared edge" ... "Nor is
    an extrapolation applied across a declared edge: where an edge lies between the operating value and the
    readable range's nearest end, or on that end, `outside_range` stands and the result carries no value"."""
    at, table, want, reasons = NOT_APPLIED[situation]
    result = read_at(at, [extrapolation()], field=met_table(**table), want=want)
    assert (result.reasons, result.applied, result.assumption) == (reasons, (), None)
    if reasons:
        assert (result.status, result.value, result.table) == ("not_met", None, None)
    else:
        assert result.status == "met"


EXTRAPOLATIONS_ELSEWHERE: list[dict[str, JsonValue]] = [
    extrapolation(field="bulk.density"),
    extrapolation(record=None),
    extrapolation(record=None, region="lumen"),
    extrapolation(interval="skin"),
    extrapolation(region="lumen"),
    extrapolation(record={"id": "conformance/water_fixture", "version": "2.0.0", "content_hash": PIN}),
    extrapolation(record=1.0),
]


@pytest.mark.parametrize("elsewhere", EXTRAPOLATIONS_ELSEWHERE)
def test_an_extrapolation_naming_another_field_or_located_elsewhere_is_checked_and_not_applied(
    elsewhere: dict[str, JsonValue],
) -> None:
    """Section 1: "One naming another field, another record or region, an `interval` ... or no location is
    checked and not applied" [PR-307]."""
    result = read_at(330.0, [elsewhere])
    assert (result.status, result.reasons, result.value, result.applied) == ("not_met", (OUTSIDE,), None, ())


EXTRAPOLATION_SHAPES: list[tuple[list[dict[str, JsonValue]], str]] = [
    ([extrapolation(method=None)], "refused"),
    ([extrapolation(method="linear")], "refused"),
    ([extrapolation(method="Constant")], "refused"),
    ([extrapolation(method=1.0)], "refused"),
    ([extrapolation(law=None)], "refused"),
    ([extrapolation(law=1.0)], "refused"),
    ([extrapolation(law=["the end value"])], "refused"),
    # `law`: "text of at least one character, which a reader does not judge" (`declarations.md` section 4.1).
    ([extrapolation(law="")], "refused"),
    ([extrapolation(law=" ")], "read"),
    ([extrapolation(law="\u00e9")], "read"),
    ([extrapolation(laws="the end value held")], "refused"),
    ([extrapolation(methd="constant")], "refused"),
    ([extrapolation(field="bulk.porosity")], "refused"),
    ([extrapolation(field=None)], "refused"),
    ([extrapolation(record={"id": "x", "versoin": "1.0.0"})], "refused"),
    # "So do two acceptances of one kind, `nominal`, `extrapolation`, `pick` or `trainable`, that name one
    # field, whatever location or other members each holds."
    ([extrapolation(), extrapolation(record=None, law="")], "refused"),
    ([extrapolation(), extrapolation(record=None)], "refused"),
    ([extrapolation(), extrapolation(field="bulk.density")], "read"),
    ([extrapolation(), nominal()], "read"),
    # Its `reason` and `basis` are ignored, and so is a member no document names.
    ([extrapolation(basis=None, reason=1.0, x_unknown_member=1.0)], "read"),
]


@pytest.mark.parametrize(("acceptances", "outcome"), EXTRAPOLATION_SHAPES)
def test_an_extrapolations_shape_is_checked_at_step_0_whatever_it_names(
    acceptances: list[dict[str, JsonValue]], outcome: str
) -> None:
    """Section 1: "Each acceptance is checked here, whatever field or location it names: its `field` as the
    target's is (the pattern, and a registered field), and its kind's own members, have their shapes"
    [PR-330]."""
    result = read_at(330.0, acceptances)
    if outcome == "refused":
        assert (result.status, result.reasons) == ("not_met", (Reason("request_incomplete"),)), acceptances
    else:
        assert (result.reasons, result.value) == ((OUTSIDE,), 0.000577), acceptances


def test_a_request_keeps_its_extrapolations_with_the_members_their_shape_names() -> None:
    request = with_members(acceptances=[IMPLIED, extrapolation(record=WATER_PIN, x_note=1.0)])
    checked = ReadRequest.from_json(request)
    assert isinstance(checked, ReadRequest)
    (given,) = checked.extrapolations
    assert (given.index, checked.extrapolation()) == (1, given)
    acceptances = cast(list[JsonValue], checked.to_json().get("acceptances"))
    assert acceptances[1] == {
        "acceptance": "extrapolation",
        "record": WATER_PIN,
        "field": "fluid.dynamic_viscosity",
        "method": "constant",
        "law": "the end value held",
    }
    assert ReadRequest.from_json(checked.to_json()) == checked


# A table among alternatives: step 7 reads every alternative before it decides the outcome. A table read
# inside its readable range is read as any form is (S3b-2), and one whose read gives a reason at step 11 is
# set aside, kept or refuses the field by step 7's rows for step 11 (S4d).
BESIDE_A_TABLE: dict[str, Callable[[], dict[str, JsonValue]]] = {
    "constant": lambda: met_field(),
    "interval": lambda: met_interval(lower=0.0006, upper=0.0008, basis="specification_limits"),
    "broken constant": lambda: met_field(value="not a number"),
}
TABLE_AMONG_OTHERS: list[tuple[str, ...]] = [
    ("table",),
    *((other, "table") for other in BESIDE_A_TABLE),
    *(("table", other) for other in BESIDE_A_TABLE),
]


def alternatives_of(names: tuple[str, ...], table: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The water field as alternatives, `table` where `names` says "table", each other a fresh copy."""
    return {"alternatives": [table if name == "table" else BESIDE_A_TABLE[name]() for name in names]}


def met_table(**table: JsonValue) -> dict[str, JsonValue]:
    """The viscosity table, its shear rate stated and met by `MET_REQUEST` as `met_field`'s is."""
    field = viscosity_table(**table)
    cast(dict[str, JsonValue], field["conditions"])["shear_rate"] = dict(SHEAR_RATE)
    return field


# Each pair's outcome by step 7's rules (`read_side_contract.md` section 3, step 7), the table read at 310.15
# K inside its range: under `want: value` a table and a constant give their form, an interval does not; under
# `want: bounds` only the interval does; under `components` and `evidence` none; a broken constant refuses.
GIVES_UNDER: dict[str, set[str]] = {
    "value": {"table", "constant"},
    "bounds": {"interval"},
    "components": set(),
    "evidence": set(),
}


@pytest.mark.parametrize("want", ["value", "bounds", "components", "evidence"])
@pytest.mark.parametrize("names", TABLE_AMONG_OTHERS, ids=" and ".join)
def test_a_table_alternative_read_inside_its_range_is_read_as_any_alternative(
    names: tuple[str, ...], want: str
) -> None:
    """Section 3, step 7, a table alternative met inside its readable range, first or last beside each other
    form: a broken constant refuses the field; the one alternative left is read as the field; two that stay
    give `no_pick` where one has a form `want` can give, its entry the table's number under `want: value`
    (section 2, the `alternative_values` row), and `want_mismatch` where none has. The table and its axis
    never set anything aside (section 5, first row: "Its status never sets an alternative aside")."""
    result = read_accepting(alternatives_of(names, met_table()), [], want=want)
    table_alone = read_met(met_table(), want=want)
    if "broken constant" in names:
        assert result.status == "not_met"
        broken = names.index("broken constant")
        assert Reason("form_invalid", alternative=broken) in result.reasons
    elif names == ("table",):
        assert (result.status, result.value, result.table) == (
            table_alone.status,
            table_alone.value,
            table_alone.table,
        )
        assert result.reasons == tuple(
            dataclasses.replace(reason, alternative=0) for reason in table_alone.reasons
        )
    elif GIVES_UNDER[want] & set(names):
        assert (result.status, result.reasons) == ("unknown", (Reason("no_pick"),))
        entries = {entry.alternative: entry for entry in result.alternative_values or ()}
        at = names.index("table")
        expected = table_alone.value if want == "value" else viscosity_table()["table"]
        assert json.loads(json.dumps(entries[at].entry_json()))["value"] == expected
        assert result.table is None
    else:
        assert (result.status, result.reasons) == ("not_met", (Reason("want_mismatch"),))


STEP_11_REASONS: dict[str, tuple[dict[str, JsonValue], dict[str, JsonValue]]] = {
    "outside its range": ({}, {"temperature": {"value": 330.0, "unit": "K"}}),
    "at an edge": (
        {"x": [300.0, 310.15, 310.15, 320.0], "y": [1e-3, 8e-4, 7e-4, 6e-4], "edges": [310.15]},
        {},
    ),
    "at an edge outside a narrower source_range": (
        {
            "x": [300.0, 310.15, 310.15, 320.0],
            "y": [1e-3, 8e-4, 7e-4, 6e-4],
            "edges": [310.15],
            "source_range": [312.0, 320.0],
        },
        {},
    ),
    "outside a narrower source_range": ({"source_range": [300.0, 305.0]}, {}),
    "over an operating range": ({}, {"temperature": {"range": [309.15, 311.15], "unit": "K"}}),
    "with no operating value": ({}, {"temperature": None}),
}
SET_ASIDE = ("outside its range", "outside a narrower source_range")
REFUSING = ("at an edge", "at an edge outside a narrower source_range", "with no operating value")


def read_in(
    situation: str, field: JsonValue, *, want: str = "value", acceptances: Collection[JsonValue] = ()
) -> ReadResult:
    """`field` read as `read_accepting` reads it, the table and the request changed as `situation` says
    (`STEP_11_REASONS`), with `acceptances` located at the target's record."""
    return read(*request_in(situation, field, want=want, acceptances=acceptances))


def request_in(
    situation: str, field: JsonValue, *, want: str = "value", acceptances: Collection[JsonValue] = ()
) -> tuple[JsonValue, RecordStore]:
    """`read_in`'s request, and the store it reads."""
    _, operating = STEP_11_REASONS[situation]
    request, records = stored(with_field("fluid.dynamic_viscosity", field))
    assert isinstance(request, dict)
    request.update(copy.deepcopy(MET_REQUEST))
    requirement = cast(dict[str, JsonValue], request["requirement"])
    requirement["want"] = want
    given = cast(dict[str, JsonValue], request["operating_conditions"])
    for name, value in operating.items():
        if value is None:
            del given[name]
            del cast(dict[str, JsonValue], requirement["conditions"])[name]
        else:
            given[name] = value
    pin = cast(dict[str, JsonValue], request["target"])["record"]
    request["acceptances"] = [
        {**cast(dict[str, JsonValue], acceptance), "record": pin} for acceptance in acceptances
    ]
    return request, records


def table_in(situation: str) -> dict[str, JsonValue]:
    return met_table(**STEP_11_REASONS[situation][0])


def each_read_alone(situation: str, names: tuple[str, ...], want: str) -> tuple[Reason, ...]:
    """Every alternative's reasons, as each one's read alone as a field gives them, each carrying its index
    but `request_incomplete`, the request's fault (section 2 item 2)."""
    found: list[Reason] = []
    for index, name in enumerate(names):
        alone = table_in(situation) if name == "table" else BESIDE_A_TABLE[name]()
        for reason in read_in(situation, alone, want=want).reasons:
            mine = reason.code != "request_incomplete"
            found.append(dataclasses.replace(reason, alternative=index if mine else None))
    return merged(found)


@pytest.mark.parametrize("want", ["value", "bounds"])
@pytest.mark.parametrize("names", TABLE_AMONG_OTHERS, ids=" and ".join)
@pytest.mark.parametrize("situation", SET_ASIDE)
def test_a_table_alternative_outside_its_readable_range_is_set_aside(
    situation: str, names: tuple[str, ...], want: str
) -> None:
    """Section 3, step 7: "An alternative is set aside where its read lies outside its form's range at step
    11, not exactly at a declared edge, and no extrapolation the request carries would cover it" [PR-044]:
    beside another, the result is what the other alone gives as the one left, its reasons carrying its index,
    "the set-aside ones' reasons ... not reported"; alone, or beside one that is set aside too or refuses the
    field, `not_met` "with every alternative's reasons" (`outside_range` with the axis among them), no
    value."""
    result = read_in(situation, alternatives_of(names, table_in(situation)), want=want)
    at = names.index("table")
    others = [(index, name) for index, name in enumerate(names) if name != "table"]
    every = each_read_alone(situation, names, want)
    assert Reason("outside_range", "temperature", alternative=at) in every
    if not others:
        assert (result.status, result.reasons, result.value, result.conditions) == (
            "not_met",
            every,
            None,
            None,
        )
        return
    ((index, name),) = others
    other = read_in(situation, {"alternatives": [BESIDE_A_TABLE[name]()]}, want=want)
    if other.status == "not_met" and other.conditions is None:
        # The other refuses the field or is set aside too.
        assert (result.status, result.reasons, result.value) == ("not_met", every, None)
    else:
        assert dataclasses.replace(result, reasons=()) == dataclasses.replace(other, reasons=())
        assert result.reasons == tuple(
            dataclasses.replace(reason, alternative=index) for reason in other.reasons
        )


@pytest.mark.parametrize("extrapolated", [False, True])
@pytest.mark.parametrize("want", ["value", "bounds"])
@pytest.mark.parametrize("names", TABLE_AMONG_OTHERS, ids=" and ".join)
@pytest.mark.parametrize("situation", REFUSING)
def test_a_table_alternative_at_an_edge_or_with_no_operating_value_refuses_the_field(
    situation: str, names: tuple[str, ...], want: str, extrapolated: bool
) -> None:
    """Section 3, step 7: "A table alternative read exactly at a declared edge refuses the field, wherever the
    edge lies, outside the readable range included. So does a fault of the request (section 1): an
    alternative whose read reaches step 11 with no operating value for its form's axis refuses the field"
    [PR-044] [PR-308], whatever stands beside it and whatever extrapolation the request carries, none
    applying at an edge (section 5): `not_met` "with every alternative's reasons, those that wait included",
    each with its index but `request_incomplete`, which carries none (section 2 item 2), and no value."""
    acceptances = [extrapolation()] if extrapolated else []
    result = read_in(
        situation, alternatives_of(names, table_in(situation)), want=want, acceptances=acceptances
    )
    at = names.index("table")
    every = each_read_alone(situation, names, want)
    assert (result.status, result.reasons, result.value, result.conditions) == ("not_met", every, None, None)
    refusing = {
        "at an edge": [Reason("at_edge", "temperature", alternative=at)],
        "at an edge outside a narrower source_range": [
            Reason("at_edge", "temperature", alternative=at),
            Reason("outside_range", "temperature", alternative=at),
        ],
        "with no operating value": [Reason("request_incomplete", "temperature")],
    }[situation]
    assert set(refusing) <= set(result.reasons)
    assert all(reason.alternative is None for reason in result.reasons if reason.code == "request_incomplete")


def test_a_table_alternative_set_aside_at_step_10_never_reaches_step_11() -> None:
    """Section 3, step 7: "one set aside at step 10 never reaches step 11 and refuses nothing" [PR-308]: a
    table whose shear rate lies outside the request's, read with no operating value for its axis, beside a
    met constant, which is the one left (its temperature unchecked)."""
    table = table_in("with no operating value")
    cast(dict[str, JsonValue], table["conditions"])["shear_rate"] = {"value": 5.0, "unit": "1/s", **STATED}
    result = read_in("with no operating value", {"alternatives": [table, met_field()]})
    assert (result.status, result.value) == ("unknown", 0.000692)
    assert result.reasons == (Reason("condition_unchecked", "temperature", alternative=1),)


OVER_A_RANGE = "over an operating range"


@pytest.mark.parametrize("want", ["value", "bounds"])
def test_a_table_alternative_read_over_an_operating_range_alone_is_its_read_with_no_labels(want: str) -> None:
    """Section 3, step 7: "where one alternative stays, that alternative's read, `want` included": the table's
    read over a range of its axis ends at step 11 with `want_mismatch` and the axis (section 1), with its
    conditions and no value; and, its read ended before step 12, none of step 12's labels."""
    result = read_in(OVER_A_RANGE, {"alternatives": [table_in(OVER_A_RANGE)]}, want=want)
    assert (result.status, result.reasons) == (
        "not_met",
        (Reason("want_mismatch", "temperature", alternative=0),),
    )
    assert (result.value, result.labels, result.alternative_values) == (None, (), None)
    assert result.conditions is not None


# Under `no_pick` the table read over a range stays beside the other, whose form `want` gives; where it does
# not, `want_mismatch`, the table counting as a form `want` cannot give.
OVER_A_RANGE_BESIDE: dict[tuple[str, str], str] = {
    ("constant", "value"): "no_pick",
    ("constant", "bounds"): "want_mismatch",
    ("interval", "value"): "want_mismatch",
    ("interval", "bounds"): "no_pick",
}


@pytest.mark.parametrize(("other", "want"), OVER_A_RANGE_BESIDE)
@pytest.mark.parametrize("first", [True, False])
def test_a_table_alternative_read_over_an_operating_range_stays_as_a_form_want_cannot_give(
    other: str, want: str, first: bool
) -> None:
    """Section 3, step 7: "These stay: ... one whose form `want` cannot give (... or a table read over an
    operating range of its axis, say)"; "A table read over an operating range of its axis counts as a form
    `want` cannot give" [PR-013]. Under `no_pick` its entry holds "its form's member as stored instead", the
    other members as a read of it alone gives them, and "its `labels` are those step 12 gives that
    alternative even where its read ended at step 11, as a table read over an operating range of its axis
    does" (section 2): the field's label."""
    names = ("table", other) if first else (other, "table")
    result = read_in(OVER_A_RANGE, alternatives_of(names, table_in(OVER_A_RANGE)), want=want)
    if OVER_A_RANGE_BESIDE[(other, want)] == "want_mismatch":
        assert (result.status, result.reasons, result.alternative_values) == (
            "not_met",
            (Reason("want_mismatch"),),
            None,
        )
        return
    assert (result.status, result.reasons, result.value) == ("unknown", (Reason("no_pick"),), None)
    entries = {entry.alternative: entry for entry in result.alternative_values or ()}
    entry = json.loads(json.dumps(entries[names.index("table")].entry_json()))
    stored_table = table_in(OVER_A_RANGE)
    assert entry["value"] == stored_table["table"]
    assert entry["labels"] == [stored_table["label"]]
    assert (entry["unit"], entry["provenance"]["origin"]) == (stored_table["unit"], "measured_by_contributor")
    assert "statistics" in entry
    assert entry["specimen"] == {}
    assert [axis["status"] for axis in entry["conditions"] if axis["name"] == "temperature"] == ["not_met"]


@pytest.mark.parametrize("first", [True, False])
def test_a_table_alternative_an_extrapolation_would_cover_stays_with_no_extrapolation_applied(
    first: bool,
) -> None:
    """Section 3, step 7: "These stay: ... one that an extrapolation the request carries would cover, since a
    pick would let the extrapolation apply" [PR-013], beside a met constant: `no_pick`, the table's entry
    "its form's member as stored instead, with no nominal or extrapolation applied" (section 2), so neither
    the end value, nor an `assumption`, nor the extrapolation among what was applied; its `outside_range`
    waits."""
    names = ("table", "constant") if first else ("constant", "table")
    result = read_in(
        "outside a narrower source_range",
        alternatives_of(names, table_in("outside a narrower source_range")),
        acceptances=[extrapolation()],
    )
    assert (result.status, result.reasons, result.applied, result.assumption) == (
        "unknown",
        (Reason("no_pick"),),
        (),
        None,
    )
    (entry,) = [
        entry for entry in result.alternative_values or () if entry.alternative == names.index("table")
    ]
    assert (entry.value, entry.assumption, entry.applied, entry.table) == (entry.member, None, (), None)
    assert (
        json.loads(json.dumps(entry.entry_json()))["value"]
        == table_in("outside a narrower source_range")["table"]
    )


# The `no_pick` entries that hold a table as stored (section 2, the `alternative_values` row), by the
# acceptances each is read under: a table read over an operating range of its axis, and one kept outside its
# readable range for an extrapolation the request carries.
TABLE_ENTRIES_AS_STORED: dict[str, list[JsonValue]] = {
    OVER_A_RANGE: [],
    "outside a narrower source_range": [extrapolation()],
}


@pytest.mark.parametrize("member", ["value", "member"])
@pytest.mark.parametrize("situation", TABLE_ENTRIES_AS_STORED)
def test_a_table_entry_held_as_stored_shares_nothing_with_the_stored_record(
    situation: str, member: str
) -> None:
    """Rule 6 through the Python API, as for a derivation (above), for step 7's entry of a table held as
    stored (S4d's review): beside a met constant under `no_pick`, a consumer that changes the table the
    entry holds, its `value` or its `member`, changes no later read of the same store."""
    field = alternatives_of(("table", "constant"), table_in(situation))
    request, records = request_in(situation, field, acceptances=TABLE_ENTRIES_AS_STORED[situation])
    first = read(request, records)
    before = json.loads(json.dumps(first.to_json()))
    assert (first.status, first.reasons) == ("unknown", (Reason("no_pick"),))
    (entry,) = [entry for entry in first.alternative_values or () if entry.alternative == 0]
    table = an_object(getattr(entry, member))
    a_list(table["x"]).append(999.0)
    table["scheme"] = "changed"
    later = read(request, records)
    assert json.loads(json.dumps(later.to_json())) == before


def test_a_kept_tables_entry_drops_the_extrapolation_alone_from_what_it_applied() -> None:
    """Section 2, the `alternative_values` row: a kept table's entry holds its member "with no nominal or
    extrapolation applied", which takes the extrapolation's index (1) from what its read applied and leaves
    the implied condition's (0), as a staying constant's entry keeps it: both alternatives in vivo, the
    implied condition filling the density kind neither states (S4d's review). Neither is in the JSON."""
    field = alternatives_of(("table", "constant"), table_in("outside a narrower source_range"))
    for alternative in a_list(field["alternatives"]):
        an_object(alternative)["specimen"] = {"tissue_state": {"token": "in_vivo", **STATED}}
    implied: JsonValue = {**IMPLIED, "implies": {"density_kind": {"token": "matrix"}}}
    result = read_in("outside a narrower source_range", field, acceptances=[implied, extrapolation()])
    assert (result.status, result.applied) == ("unknown", ())
    assert Reason("no_pick") in result.reasons
    entries = {entry.alternative: entry for entry in result.alternative_values or ()}
    assert (entries[0].applied, entries[0].assumption, entries[1].applied) == ((0,), None, (0,))


def test_a_table_alternative_an_extrapolation_covers_is_read_with_it_as_the_one_left() -> None:
    """Section 3, step 7: "An alternative kept for an extrapolation is read on through steps 12 and 13, as a
    field is (above). The extrapolation is applied only where that alternative is the one left" [PR-044]:
    beside a constant set aside for its temperature, the result is the table's read under the extrapolation,
    `not_met` with `outside_range` carrying its index, the end value, the table and `assumption`, and the
    extrapolation among what was applied."""
    field: dict[str, JsonValue] = {"alternatives": [met_field(), table_in("outside its range")]}
    result = read_in("outside its range", field, acceptances=[extrapolation()])
    alone = read_in("outside its range", table_in("outside its range"), acceptances=[extrapolation()])
    assert result.reasons == (Reason("outside_range", "temperature", alternative=1),)
    assert (result.status, result.value, result.assumption, result.applied) == (
        "not_met",
        alone.value,
        alone.assumption,
        (0,),
    )
    assert (result.value, result.table) == (0.000577, viscosity_table()["table"])


def test_a_table_alternative_outside_its_range_is_set_aside_where_no_extrapolation_would_cover_it() -> None:
    """Section 3, step 7 sets aside one that "no extrapolation the request carries would cover", and section
    5 applies one "Under `want: value`" alone: under `want: bounds` the table is set aside and the constant,
    the one left, gives `want_mismatch`, with an extrapolation as without one."""
    situation = "outside a narrower source_range"
    field = alternatives_of(("table", "constant"), table_in(situation))
    covered = read_in(situation, field, want="bounds", acceptances=[extrapolation()])
    assert covered == read_in(situation, field, want="bounds")
    assert (covered.status, covered.reasons) == ("not_met", (Reason("want_mismatch", alternative=1),))


def test_a_kept_tables_unknown_reasons_stand_beside_no_pick_and_its_not_met_ones_wait() -> None:
    """Section 3, step 7: "Where two or more stay, each one's `unknown` reasons stand beside `want_mismatch`
    or `no_pick`, and its `not_met` reasons wait" [PR-013]: a kept table stated without origin gives step
    12's `stated_without_origin` beside `no_pick`, its `outside_range` not."""
    table = table_in("outside a narrower source_range")
    cast(dict[str, JsonValue], table["provenance"])["origin"] = "stated_without_origin"
    field: dict[str, JsonValue] = {"alternatives": [table, met_field()]}
    result = read_in("outside a narrower source_range", field, acceptances=[extrapolation()])
    assert (result.status, result.reasons) == (
        "unknown",
        (Reason("no_pick"), Reason("stated_without_origin", alternative=0)),
    )


def test_a_kept_tables_waiting_reasons_are_reported_once_another_refuses_the_field() -> None:
    """Section 3, step 7: "These wait: they are reported ... once the field is refused" [PR-044]: a kept
    table's `outside_range` beside a broken constant's `form_invalid`."""
    situation = "outside a narrower source_range"
    field = alternatives_of(("table", "broken constant"), table_in(situation))
    result = read_in(situation, field, acceptances=[extrapolation()])
    assert (result.status, set(result.reasons)) == (
        "not_met",
        {Reason("outside_range", "temperature", alternative=0), Reason("form_invalid", alternative=1)},
    )


def form_range_read(**report: object) -> FieldRead:
    """A table alternative's read with step 11's report `report` (`FormRange`), nothing else of it read."""
    return FieldRead((), form_range=FormRange(**cast(dict[str, Any], report)), alternative=0)


REPORTS: list[tuple[dict[str, object], bool]] = [
    ({"outside_alone": True}, True),
    ({"outside_alone": True, "coverable": True}, True),
    ({"outside_alone": True, "coverable": True, "extrapolation": "covering"}, False),
    ({"outside_alone": False}, False),
    ({"over_a_range": True}, False),
    ({"request_fault": True}, False),
]


@pytest.mark.parametrize(("report", "set_aside"), REPORTS)
def test_set_aside_by_its_range_takes_outside_range_alone_with_no_extrapolation_covering_it(
    report: dict[str, object], set_aside: bool
) -> None:
    """`_set_aside_by_its_range`: "outside its form's range at step 11, not exactly at a declared edge, and no
    extrapolation the request carries would cover it" (section 3, step 7): `outside_range` without `at_edge`
    (`outside_alone`, which an edge beside it, `outside_alone` false, takes away), and no extrapolation that
    covers it, one that could (`coverable`) but that the request does not carry included; never a read over
    an operating range or with no operating value, nor one step 11 did not reach."""
    if report.get("extrapolation") == "covering":
        covering = Extrapolation(0, "fluid.dynamic_viscosity", {}, "constant", "the end value held")
        report = {**report, "extrapolation": covering}
    set_aside_by_its_range = read_module._set_aside_by_its_range  # pyright: ignore[reportPrivateUsage]
    assert set_aside_by_its_range(form_range_read(**report)) is set_aside
    assert set_aside_by_its_range(FieldRead((), alternative=0)) is False


@pytest.mark.parametrize(
    "names", [("table",), ("interval", "table"), ("table", "interval")], ids=" and ".join
)
def test_a_table_alternative_beside_an_interval_under_a_nominal(names: tuple[str, ...]) -> None:
    """Section 3, step 7: "An interval counts as one `want: value` can give where a nominal the request
    carries applies to the read", and the table gives its number: two that stay give `no_pick`, with no
    nominal applied (section 6); the table alone is read as the field, the nominal applying to nothing."""
    result = read_accepting(alternatives_of(names, met_table()), [nominal()])
    if names == ("table",):
        assert (result.status, result.applied, result.assumption) == ("met", (), None)
        assert result.value == read_met(met_table()).value
    else:
        assert (result.status, result.reasons, result.applied) == ("unknown", (Reason("no_pick"),), ())


@pytest.mark.parametrize(
    "names", [names for names in TABLE_AMONG_OTHERS if "broken constant" not in names], ids=" and ".join
)
def test_a_table_alternative_step_8_refuses_refuses_the_field(names: tuple[str, ...]) -> None:
    """`read_side_contract.md` section 3, step 7: an alternative that steps 8 to 13 refuse refuses the field,
    its reasons carrying its index: here a table whose `x` decreases (table item 1). An interval beside it
    under `want: value`, with no nominal, adds its own `want_mismatch`."""
    result = read_accepting(alternatives_of(names, viscosity_table(x=[320.0, 300.0])), [])
    at = names.index("table")
    assert result.status == "not_met"
    assert [reason for reason in result.reasons if reason.alternative == at] == [
        Reason("form_invalid", alternative=at)
    ]


DERIVED_INPUTS: dict[str, JsonValue] = {
    "origin": "derived",
    "review": {"status": "not_checked"},
    "derivation": {
        "method": "a mixing rule",
        "inputs": [
            {
                "record": {"id": "example/MAT-1", "version": "1.0.0", "content_hash": "sha256:" + "1" * 64},
                "field": "fluid.dynamic_viscosity",
            },
            {
                "record": {"id": "example/MAT-2", "version": "1.0.0", "content_hash": "sha256:" + "2" * 64},
                "field": "fluid.dynamic_viscosity",
            },
        ],
        "assumptions": ["ideal mixing"],
        "input_specimens": [{"input": 0.0, "specimen": {}}, {"input": 1.0, "specimen": {}}],
    },
}


# Step 7 over alternatives, with no pick and no overlay (`read_side_contract.md` section 3, step 7).


def test_two_alternatives_with_no_reason_of_their_own_give_no_pick_each_in_alternative_values() -> None:
    result = read_met({"alternatives": [met_field(), met_field(value=0.0007)]})
    assert (result.status, result.reasons) == ("unknown", (Reason("no_pick"),))
    written = json.loads(json.dumps(result.to_json()))
    assert set(written) == {"status", "reasons", "alternative_values", "labels"}
    assert [
        (entry["alternative"], entry["value"], entry["unit"]) for entry in written["alternative_values"]
    ] == [
        (0, 0.000692, "Pa.s"),
        (1, 0.0007, "Pa.s"),
    ]
    assert all(type(entry["alternative"]) is int for entry in written["alternative_values"])
    assert written["labels"] == []


def test_an_unknown_member_inside_an_alternative_is_ignored() -> None:
    """`record_format.md` section 10 item 1, inside an alternative (the unknown-member position R77)."""
    plain = read_met({"alternatives": [met_field(), met_field()]})
    unknown = read_met({"alternatives": [met_field(x_unknown_member=1.0), met_field()]})
    assert unknown == plain


def test_no_alternative_whose_form_want_can_give_is_want_mismatch_at_step_7() -> None:
    result = read_met({"alternatives": [met_field(), met_field()]}, want="bounds")
    assert (result.status, result.reasons, result.conditions) == ("not_met", (Reason("want_mismatch"),), None)
    assert set(json.loads(json.dumps(result.to_json()))) == {"status", "reasons", "labels"}


def test_two_intervals_under_a_nominal_give_no_pick_with_no_nominal_applied() -> None:
    """Section 3 step 7: "An interval counts as one `want: value` can give where a nominal the request carries
    applies to the read"; section 6: "Under `no_pick` no nominal is applied, nor compared with the bounds, so
    none gives `nominal_invalid`" [PR-338]. A nominal located elsewhere applies to no read."""
    inside = met_interval(lower=0.0006, upper=0.0008, basis="specification_limits")
    below = met_interval(lower=0.0001, upper=0.0002, basis="specification_limits")
    field: dict[str, JsonValue] = {"alternatives": [inside, below]}
    result = read_accepting(field, [nominal()])
    assert (result.status, result.reasons, result.applied, result.assumption) == (
        "unknown",
        (Reason("no_pick"),),
        (),
        None,
    )
    written = json.loads(json.dumps(result.to_json()))
    assert [entry["value"] for entry in written["alternative_values"]] == [
        {"lower": 0.0006, "upper": 0.0008, "basis": "specification_limits"},
        {"lower": 0.0001, "upper": 0.0002, "basis": "specification_limits"},
    ]
    elsewhere = read_accepting(field, [nominal(record=None)])
    assert (elsewhere.status, elsewhere.reasons) == ("not_met", (Reason("want_mismatch"),))


def test_two_intervals_under_a_nominal_give_want_mismatch_under_components() -> None:
    """Section 3 step 7: "where two or more stay and none has a form `want` can give, `not_met`, with
    `want_mismatch`"; "An interval counts as one `want: value` can give where a nominal the request carries
    applies to the read", so under `want: components` neither interval counts, nominal or none [PR-338] (the
    hand mutant M47, which survived the rerun of S2b-2's review's mutants at `dev` and at `ci`)."""
    inside = met_interval(lower=0.0006, upper=0.0008, basis="specification_limits")
    below = met_interval(lower=0.0001, upper=0.0002, basis="specification_limits")
    result = read_accepting({"alternatives": [inside, below]}, [nominal()], want="components")
    assert (result.status, result.reasons, result.conditions, result.applied) == (
        "not_met",
        (Reason("want_mismatch"),),
        None,
        (),
    )


@pytest.mark.parametrize(
    "units",
    [
        [{"status": "not_applicable", "reason": "one"}, {"status": "not_applicable", "reason": "two"}],
        [{"status": "not_applicable"}, {"status": "not_applicable", "reason": "two"}],
        [{"status": "not_applicable", "reason": "one"}, {"status": "not_applicable"}],
    ],
)
def test_under_no_pick_each_entry_holds_its_own_alternatives_unit(units: list[JsonValue]) -> None:
    """Section 2, the `unit` row: "Under `no_pick` the result holds none: each `alternative_values` entry
    holds its own alternative's unit, as stored", so that alternatives whose units are stored differently
    "each keep their own" (the maintainer's ruling of 2026-10-19, replacing the interim rule) [PR-013]."""
    record: dict[str, Any] = json.loads(EVIDENCE_FIXTURE.read_text(encoding="utf-8"))
    fields = record["body"]["sections"]["biocompatibility"]["fields"]
    alternatives = [{**fields["evidence"], "evidence": [REPORT], "unit": unit} for unit in units]
    fields["evidence"] = {"alternatives": alternatives}
    request, records = stored(record, "biocompatibility.evidence")
    assert isinstance(request, dict)
    request["requirement"] = {"want": "evidence"}
    del request["operating_conditions"]
    result = read(request, records)
    assert (result.status, result.reasons) == ("unknown", (Reason("no_pick"),))
    assert result.unit is None
    written = json.loads(json.dumps(result.to_json()))
    assert "unit" not in written
    assert [entry["unit"] for entry in written["alternative_values"]] == units


def test_the_one_alternative_left_is_read_as_the_field_its_reasons_carrying_its_index() -> None:
    """Section 3 step 7: "where one alternative stays, that alternative's read, `want` included"; section 2
    item 2: a reason found reading it carries its `alternative` [PR-044]."""
    alone = read_met(met_field())
    left = read_met({"alternatives": [met_field()]})
    assert left == alone
    unknown = read_met({"alternatives": [water_field()]})
    assert (unknown.status, unknown.reasons) == (
        "unknown",
        (Reason("condition_unstated", "shear_rate", alternative=0),),
    )
    assert unknown.value == 0.000692
    (written,) = json.loads(json.dumps(unknown.to_json()))["reasons"]
    assert (written["code"], written["condition"], written["alternative"]) == (
        "condition_unstated",
        "shear_rate",
        0,
    )
    assert type(written["alternative"]) is int


def test_an_alternatives_own_unknown_reason_stands_beside_no_pick() -> None:
    """Section 3 step 7: "each one's `unknown` reasons stand beside `want_mismatch` or `no_pick`" [PR-013]."""
    result = read_met({"alternatives": [met_field(), water_field()]})
    assert (result.status, set(result.reasons)) == (
        "unknown",
        {Reason("no_pick"), Reason("condition_unstated", "shear_rate", alternative=1)},
    )
    assert [entry.alternative for entry in result.alternative_values or ()] == [0, 1]


def test_an_alternatives_own_unknown_reason_stands_beside_want_mismatch() -> None:
    """Section 3 step 7: "each one's `unknown` reasons stand beside `want_mismatch` or `no_pick`", under a
    `want` neither constant gives (a review's hand mutant that kept S2's `want_mismatch` alone) [PR-013]."""
    result = read_met({"alternatives": [met_field(), water_field()]}, want="bounds")
    assert (result.status, set(result.reasons), result.conditions) == (
        "not_met",
        {Reason("want_mismatch"), Reason("condition_unstated", "shear_rate", alternative=1)},
        None,
    )


def set_aside_lot() -> dict[str, JsonValue]:
    """The water constant stated at 400 K, which the read at 310.15 K sets aside at step 10, as a lot's value
    beside a grade's intervals (`provenance.md` section 6.2 item 5)."""
    lot = met_field()
    cast(dict[str, JsonValue], lot["conditions"])["temperature"] = {"value": 400.0, "unit": "K", **STATED}
    return lot


def test_each_interval_that_stays_counts_by_its_own_form_beside_a_constant_set_aside_first() -> None:
    """Section 3 step 7: "An interval counts as one `want: value` can give where a nominal the request carries
    applies to the read", each alternative that stays by its own form: a constant stored first and set aside
    takes nothing from the two intervals after it (a review's hand mutant that read the first stored
    alternative's form) [PR-338]."""
    inside = met_interval(lower=0.0006, upper=0.0008, basis="specification_limits")
    below = met_interval(lower=0.0001, upper=0.0002, basis="specification_limits")
    result = read_accepting({"alternatives": [set_aside_lot(), inside, below]}, [nominal()])
    assert (result.status, result.reasons, result.applied) == ("unknown", (Reason("no_pick"),), ())
    assert [entry.alternative for entry in result.alternative_values or ()] == [1, 2]


def test_two_intervals_count_under_a_nominal_outside_both() -> None:
    """Section 3 step 7: an interval counts "where a nominal the request carries applies to the read", and a
    nominal applies where it is located (section 1), whether or not it falls inside the bounds; section 6:
    "Under `no_pick` no nominal is applied, nor compared with the bounds, so none gives `nominal_invalid`"
    (a review's hand mutant that counted an interval only where the nominal supplied a value) [PR-338]."""
    below = met_interval(lower=0.0001, upper=0.0002, basis="specification_limits")
    above = met_interval(lower=0.0009, upper=0.001, basis="specification_limits")
    result = read_accepting({"alternatives": [below, above]}, [nominal()])
    assert (result.status, result.reasons, result.applied) == ("unknown", (Reason("no_pick"),), ())
    assert [entry.alternative for entry in result.alternative_values or ()] == [0, 1]


def test_the_one_alternative_left_keeps_what_its_read_applied() -> None:
    """Section 3 step 7: "where one alternative stays, that alternative's read", what it applied included
    (`ReadResult.applied`, outside the JSON): the nominal that supplied an interval's value [PR-338], and the
    implied condition that filled the alternative's temperature (`declarations.md` section 4.1), each by its
    index among the acceptances (a review's hand mutant that dropped them)."""
    inside = met_interval(lower=0.0006, upper=0.0008, basis="specification_limits")
    supplied = read_accepting({"alternatives": [set_aside_lot(), inside]}, [IMPLIED, nominal()])
    assert (supplied.status, supplied.reasons, supplied.value, supplied.applied) == (
        "not_met",
        (Reason("want_mismatch", alternative=1),),
        0.0007,
        (1,),
    )
    filled: dict[str, JsonValue] = {
        **met_field(),
        "conditions": {"shear_rate": dict(SHEAR_RATE)},
        "specimen": {"tissue_state": {"token": "in_vivo", **STATED}},
    }
    implied = {**IMPLIED, "record": PINNED_AT_THE_READ}
    result = read_accepting({"alternatives": [set_aside_lot(), filled]}, [nominal(), implied])
    assert (result.status, result.value, result.applied) == ("unknown", 0.000692, (1,))
    assert set(result.reasons) == {Reason("condition_unchecked", "density_kind", alternative=1)}


@pytest.mark.parametrize(
    ("field", "refusals"),
    [
        (
            {"alternatives": [met_field(), met_field(unit="mPa.s")]},
            {Reason("unit_mismatch", alternative=1)},
        ),
        (
            {
                "alternatives": [
                    met_field(unit={"status": "unstated", "reason": "one"}),
                    met_field(unit={"status": "unstated", "reason": "two"}),
                ]
            },
            {Reason("unit_mismatch", alternative=0), Reason("unit_mismatch", alternative=1)},
        ),
    ],
)
def test_an_alternatives_own_refusal_refuses_the_field(field: JsonValue, refusals: set[Reason]) -> None:
    """Section 3 step 7: "Every other `not_met` in an alternative's read refuses the field: ... a unit other
    than the registered one", and the result holds no value, `unit` or `conditions` [PR-044]."""
    result = read_met(field)
    assert (result.status, set(result.reasons), result.conditions) == ("not_met", refusals, None)
    assert set(json.loads(json.dumps(result.to_json()))) == {"status", "reasons", "labels"}


PR_316_CASE = INPUTS.parent / "cases" / "PR-316.implied_two_disagree_in_alternative.json"
PR_316_RECORD = INPUTS / "water_alternatives_in_vivo_normal.json"


def disagreeing_in_one_alternative(other: dict[str, JsonValue]) -> tuple[JsonValue, RecordStore]:
    """PR-316's two implied conditions that disagree, which apply in the one alternative whose specimen states
    their facts (a fault of the request there), with `other` set in the provenance of the alternative they do
    not apply in."""
    record: dict[str, Any] = json.loads(PR_316_RECORD.read_text(encoding="utf-8"))
    alternatives = record["body"]["sections"]["fluid"]["fields"]["dynamic_viscosity"]["alternatives"]
    assert [bool(alternative.get("specimen")) for alternative in alternatives] == [True, False]
    alternatives[1]["provenance"].update(other)
    request, records = stored(record)
    case = json.loads(PR_316_CASE.read_text(encoding="utf-8"))
    assert isinstance(request, dict)
    pin = cast(dict[str, Any], request["target"])["record"]
    request.update({name: case["request"][name] for name in ("operating_conditions", "requirement")})
    request["acceptances"] = [{**acceptance, "record": pin} for acceptance in case["request"]["acceptances"]]
    return request, records


def test_a_request_fault_inside_one_alternative_refuses_the_field_where_no_other_has_a_reason() -> None:
    """PR-316's arm, as its case file gives it: the fault carries no `alternative` (section 2 item 2)."""
    refused = read(*disagreeing_in_one_alternative({}))
    assert (refused.status, refused.reasons) == ("not_met", (Reason("request_incomplete", "temperature"),))


def test_a_request_fault_inside_one_alternative_reports_anothers_own_reason_beside_it() -> None:
    """Section 3 step 7: a fault of the request in one alternative refuses the field "with every
    alternative's reasons"; it carries no `alternative`, while the other's `stated_without_origin` carries its
    own (section 2 item 2) [PR-316] (S2a-4's review, L3's M09, which this read raised for until S4a)."""
    refused = read(*disagreeing_in_one_alternative({"origin": "stated_without_origin"}))
    assert (refused.status, set(refused.reasons)) == (
        "not_met",
        {Reason("request_incomplete", "temperature"), Reason("stated_without_origin", alternative=1)},
    )


@pytest.mark.parametrize(
    "field",
    [
        {"alternatives": [met_field(), {"alternatives": [met_field()]}]},
        {"alternatives": [met_field(), 1.0]},
        {"alternatives": [met_field(), met_field()], "alternative": []},
        {"alternatives": [met_field(), met_field()], "label": "materica.fluid.newtonian.v1"},
    ],
)
def test_alternatives_that_break_their_shape_are_refused_at_step_7(field: dict[str, JsonValue]) -> None:
    result = read_met(field)
    assert (result.status, result.reasons, result.conditions) == ("not_met", (Reason("form_invalid"),), None)


# The stored value a result rests on (`declarations.md` section 2 item 8), which a build checks a
# requirement's `label` against: kept outside the result's JSON and equality, as `applied` is.


def outside_at_300_k() -> dict[str, JsonValue]:
    """The met water constant stated at 300 K: outside the temperature's tolerance, so step 10 sets it aside
    as an alternative."""
    field = met_field()
    field["conditions"] = {
        **an_object(field["conditions"]),
        "temperature": {"value": 300.0, "unit": "K", **STATED},
    }
    return field


def test_a_result_rests_on_the_field_it_read_whether_or_not_its_read_reached_step_12() -> None:
    met = read_met(met_field())
    assert (met.status, met.resting_on) == ("met", ())
    for refused in (read_met(met_field(unit="Pa")), read_met(outside_at_300_k())):
        assert (refused.status, refused.resting_on) == ("not_met", ()), refused.reasons
    assert "resting_on" not in met.to_json()
    assert ReadResult.from_json(met.to_json()) == met


@pytest.mark.parametrize("left", [0, 1])
def test_a_result_rests_on_the_one_alternative_left_which_no_member_of_its_json_names(left: int) -> None:
    alternatives: list[JsonValue] = [outside_at_300_k(), outside_at_300_k()]
    alternatives[left] = met_field()
    result = read_met({"alternatives": alternatives})
    assert (result.status, result.reasons, result.resting_on) == ("met", (), (left,))
    assert result == read_met({"alternatives": alternatives[::-1]})


@pytest.mark.parametrize(
    "reading",
    [
        pytest.param(lambda: read(REQUEST, store()), id="record_absent"),
        pytest.param(lambda: read(*stored(water(), "bulk.density")), id="field_absent"),
        pytest.param(
            lambda: read(with_members(requirement={"want": "value", "review": "reviewed"}), store()),
            id="refused_at_step_0",
        ),
        pytest.param(lambda: read_met({"alternatives": [met_field(), met_field()]}), id="no_pick"),
        pytest.param(
            lambda: read_met({"alternatives": [met_field(), 1.0]}), id="alternatives_refused_at_step_7"
        ),
        pytest.param(
            lambda: read_met({"alternatives": [met_field(unit="Pa"), met_field()]}),
            id="an_alternative_refuses",
        ),
        pytest.param(
            lambda: read_met({"alternatives": [outside_at_300_k(), outside_at_300_k()]}),
            id="every_one_set_aside",
        ),
        pytest.param(
            lambda: read_met({"alternatives": [met_field(), met_field()]}, want="bounds"),
            id="want_mismatch_over_two_alternatives",
        ),
    ],
)
def test_a_result_resting_on_no_single_stored_value_rests_on_none(reading: Callable[[], ReadResult]) -> None:
    result = reading()
    assert result.status != "met"
    assert result.resting_on is None, result.reasons


# Whether step 1 of the read (`Resolve`) found the record its target pins, whether or not steps 2 to 5 then
# refused it, which a build lists among the records a read resolved (`declarations.md` section 2): kept
# outside the result's JSON and equality, as `applied` is.


def test_a_read_past_step_5_resolved_its_record_whatever_it_found_there() -> None:
    met = read_met(met_field())
    assert met.resolved
    assert read(*stored(water(), "bulk.density")).resolved
    assert read_met({"alternatives": [met_field(), met_field()]}).resolved
    assert "resolved" not in met.to_json()
    assert ReadResult.from_json(met.to_json()) == met


def tampered(**changes: JsonValue) -> tuple[JsonValue, RecordStore]:
    """A request for the water record's viscosity, pinned by the hash the record states, and a store holding
    the record with `changes`, which leave that hash as stated: step 1 finds it, and a later step may refuse
    it."""
    record = water()
    records = RecordStore()
    records.add("record", json.dumps(record | changes).encode())
    pin = {name: record[name] for name in ("id", "version", "content_hash")}
    return with_members(target={"record": pin, "field": "fluid.dynamic_viscosity"}), records


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        pytest.param({"schema_version": "9.9.9"}, "other_version", id="step_2_other_version"),
        pytest.param({"licence": 5}, "malformed", id="step_3_licence_of_no_shape"),
        pytest.param(
            {"licence": {"values": "NOPE", "evidence": "excluded"}}, "hash_mismatch", id="bad_licence_value"
        ),
        pytest.param({"name": "edited after it was hashed"}, "hash_mismatch", id="step_4_stale_hash"),
        pytest.param({"record_type": "fit"}, "hash_mismatch", id="step_5_type_over_a_stale_hash"),
    ],
)
def test_a_read_refused_at_steps_2_to_5_resolved_the_record_step_1_found(
    changes: dict[str, JsonValue], code: str
) -> None:
    """The result refuses the record, and has it: the record a reader most needs to see named."""
    result = read(*tampered(**changes))
    assert result.status == "not_met"
    assert result.reasons[0].code == code, result.reasons
    assert result.resolved


def test_a_record_of_an_unreadable_type_is_resolved_when_the_hash_is_not_checked() -> None:
    request, records = tampered(record_type="fit")
    result = read(request, records, claims=["plain_read"])
    assert [reason.code for reason in result.reasons] == ["unknown_type"]
    assert result.labels == ("hash_not_checked",)
    assert result.resolved


@pytest.mark.parametrize(
    "reading",
    [
        pytest.param(lambda: read(REQUEST, RecordStore()), id="record_absent"),
        pytest.param(lambda: read(*tampered(content_hash="sha256:" + "0" * 64)), id="no_copy_states_the_pin"),
        pytest.param(
            lambda: read(with_members(requirement={"want": "value", "review": "reviewed"}), store()),
            id="refused_at_step_0",
        ),
    ],
)
def test_a_read_that_found_no_record_resolved_none(reading: Callable[[], ReadResult]) -> None:
    result = reading()
    assert result.status == "not_met"
    assert not result.resolved, result.reasons
