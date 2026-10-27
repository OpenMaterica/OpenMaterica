# SPDX-License-Identifier: Apache-2.0
"""`build_bytes.py`'s oracle (`tests/fuzz/build_oracle.py`), which the target, needing Atheris, cannot show
here: a JSON pointer read, resolved and written to as RFC 6901 says; each of the four relations quiet on the
check as it is and failing on a check broken for it, the model's where it refuses a declaration and where it
takes one; and, through the target's own `test_one_input` with
Atheris stubbed, every seed passing the target, with no fault seeded and with S7a-1's control fault, which
no seed shows, one change to a seed's pointer does, and the design's unnarrowed fault seven seeds show at
once; the declarations a first byte past the seeds' picks, each with a waiver of `condition_outside` planted,
passing it too; and the target holding every report to the results relations, each failing through it on a
build broken for it."""

import contextlib
import copy
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

import materica
from materica.core import acceptance, declarations
from materica.core.build import check_build
from materica.core.declarations import Finding, Holds, JsonObject
from materica.core.jsonio import JsonValue
from materica.core.record import RecordStore
from materica.core.report import BuildRefusal, BuildReport
from scripts.measure import CONTROLS, found_in
from tests.fuzz import build_oracle
from tests.fuzz.build_oracle import (
    KNOWN_DIVERGENCES,
    NOT_BUILT,
    TAKEN,
    check_declaration,
    index_of,
    member_at,
    placed,
    resolves,
    tokens_of,
)
from tests.fuzz.seeded_fault import faulty_reasons
from tests.reference import build_model
from tests.reference.direct import BUILD
from tests.reference.read_model import NoVerdict
from tests.unit.test_fuzz_build_results import first_model_alone, waiver_covers_condition_outside

BUILD_CHECKS = Path(materica.__file__).parent / "data" / "conformance" / "build_checks"
# A declaration the check takes: BC-016's, one model over water with one waiver.
VALID: JsonValue = json.loads(
    (BUILD_CHECKS / "inputs" / "bc016_waiver_at_one_of_two_records.json").read_bytes()
)


# An engine model over a domain, which item 7 may refuse (S11): the model places that rule's refusals not.
OVER_A_DOMAIN = placed(
    placed(VALID, "/models/0/checked_over", {"domain": "lumen"}),
    "/models/0/engine",
    {"crosswalk": {"id": "materica/crosswalk", "version": "1.0.0", "sha256": "f" * 64}, "values": {}},
)


def store() -> RecordStore:
    return materica.load_records([BUILD_CHECKS / "inputs" / "water_fixture.json"])


# RFC 6901.


@pytest.mark.parametrize(
    ("pointer", "tokens"),
    [("", []), ("/", [""]), ("/a~1b", ["a/b"]), ("/a~0b", ["a~b"]), ("/~01", ["~1"]), ("/a/0", ["a", "0"])],
)
def test_a_pointer_gives_its_reference_tokens_unescaped(pointer: str, tokens: list[str]) -> None:
    assert tokens_of(pointer) == tokens


@pytest.mark.parametrize("pointer", ["a", "/~", "/~2", "/a~", "a/b"])
def test_a_text_that_is_no_pointer_gives_none(pointer: str) -> None:
    assert tokens_of(pointer) is None


@pytest.mark.parametrize(
    ("token", "length", "index"),
    [
        ("0", 1, 0),
        ("1", 2, 1),
        ("2", 2, None),
        ("01", 3, None),
        ("-", 2, None),
        ("+1", 3, None),
        ("\u0661", 3, None),
    ],
)
def test_an_array_index_is_zero_or_ascii_digits_not_starting_with_zero(
    token: str, length: int, index: int | None
) -> None:
    assert index_of(token, length) == index


def test_a_pointer_resolves_to_a_member_or_the_root() -> None:
    value: JsonValue = {"a": [{"b/c": 1.0, "d~e": 2.0}], "": 3.0}
    assert resolves(value, "")
    assert resolves(value, "/a/0/b~1c")
    assert resolves(value, "/a/0/d~0e")
    assert resolves(value, "/")
    assert not resolves(value, "/a/1")
    assert not resolves(value, "/a/0/b/c")
    assert not resolves(value, "/a/-")
    assert not resolves(value, "a")


def test_a_member_is_put_in_place_at_a_new_member_or_at_a_lists_end() -> None:
    value: JsonValue = {"a": [1.0, 2.0], "b": {"c": True}}
    assert placed(value, "/a/1", None) == {"a": [1.0, None], "b": {"c": True}}
    assert placed(value, "/a/2", None) == {"a": [1.0, 2.0, None], "b": {"c": True}}
    assert placed(value, "/a/-", None) == {"a": [1.0, 2.0, None], "b": {"c": True}}
    assert placed(value, "/b/d", 1.0) == {"a": [1.0, 2.0], "b": {"c": True, "d": 1.0}}
    assert placed(value, "/a/3", None) is None
    assert placed(value, "/x/y", None) is None
    assert placed(value, "", None) is None
    assert value == {"a": [1.0, 2.0], "b": {"c": True}}, "the seed itself left as it was"


# The relations: quiet on the check as it is; each failing on a check broken for it.


def refused(*refusals: BuildRefusal) -> Callable[[JsonValue, RecordStore], BuildReport]:
    return lambda declaration, _: BuildReport(refusals, declaration)


def raising(error: Exception) -> Callable[[JsonValue, RecordStore], BuildReport]:
    def check(declaration: JsonValue, records: RecordStore) -> BuildReport:
        raise error

    return check


def test_the_relations_are_quiet_on_the_check_as_it_is() -> None:
    check_declaration(VALID, store())
    without_reason = json.loads(json.dumps(VALID))
    del without_reason["models"][0]["acceptances"][0]["reason"]
    check_declaration(without_reason, store())
    check_declaration([VALID], store())


def test_a_raise_of_another_kind_escapes_the_relations() -> None:
    with pytest.raises(KeyError):
        check_declaration(VALID, store(), raising(KeyError("target")))


def test_a_not_implemented_error_of_no_piece_fails_the_relations() -> None:
    with pytest.raises(AssertionError, match="NotImplementedError of no piece"):
        check_declaration(VALID, store(), raising(NotImplementedError("a build claiming sampling")))


def test_a_refusal_at_no_member_fails_the_relations() -> None:
    with pytest.raises(AssertionError, match="which names no member"):
        check_declaration(VALID, store(), refused(BuildRefusal("BC-048", "/models/0/nothing")))
    check_declaration(OVER_A_DOMAIN, store(), refused(BuildRefusal("BC-048", "/models/0/model")))


def test_a_refusal_of_another_case_fails_the_relations() -> None:
    with pytest.raises(AssertionError, match="which no rule of the declaration's names"):
        check_declaration(VALID, store(), refused(BuildRefusal("BC-016", "")))


# The model's relation: the check's refusals held to the model's where it refuses with every rule placed, and
# to none where it takes the declaration.


def test_the_model_s_relation_fails_where_the_check_refuses_otherwise() -> None:
    at = "/models/0/acceptances/0"
    check_declaration(WITHOUT_REASON, store(), refused(BuildRefusal("BC-005", at)))
    with pytest.raises(
        AssertionError, match=re.escape(f"[('BC-048', '{at}')], the model [('BC-005', '{at}')]")
    ):
        check_declaration(WITHOUT_REASON, store(), refused(BuildRefusal("BC-048", at)))
    with pytest.raises(AssertionError, match=re.escape(f"gives [], the model [('BC-005', '{at}')]")):
        check_declaration(WITHOUT_REASON, store(), refused())
    with pytest.raises(AssertionError, match=re.escape(f"gives [], the model [('BC-005', '{at}')]")):
        check_declaration(WITHOUT_REASON, store(), raising(NotImplementedError(next(iter(NOT_BUILT)))))


def test_the_model_s_relation_holds_nothing_where_the_model_places_a_rule_s_refusals_not() -> None:
    """An engine model over a domain, which item 7 may refuse (S11): the model gives no verdict on it."""
    verdict = build_model.check_build(json.dumps(OVER_A_DOMAIN).encode(), BUILD)
    assert not isinstance(verdict, build_model.Refused) or verdict.unplaced, verdict
    assert not isinstance(verdict, NoVerdict) or verdict.why not in TAKEN, verdict
    check_declaration(OVER_A_DOMAIN, store(), refused(BuildRefusal("BC-048", "/models/0/engine")))


def test_the_model_s_words_for_a_declaration_it_takes_are_taken() -> None:
    """`TAKEN` holds the model's own words for a declaration that passes its check, past it and a pick's or
    an overlay's (S7c), so that the relation below does not fall quiet should the words change."""
    said = set[str]()
    for taken in (VALID, PICK_TAKEN):
        verdict = build_model.check_build(json.dumps(taken).encode(), BUILD)
        assert isinstance(verdict, NoVerdict), verdict
        said.add(verdict.why)
    assert said == set(TAKEN)


def adding(refusal: BuildRefusal) -> Callable[[JsonValue, RecordStore], BuildReport]:
    """`check_build` with `refusal` added to what it gives: a declaration it takes, refused with it alone."""

    def check(declaration: JsonValue, records: RecordStore) -> BuildReport:
        try:
            report = check_build(declaration, records)
        except NotImplementedError:
            return BuildReport((refusal,), declaration)
        return BuildReport((*report.refusals, refusal), declaration)

    return check


HOLDS = declarations._holds  # pyright: ignore[reportPrivateUsage]


def zero_tolerance_refused(holds: Holds, value: JsonValue, pointer: str) -> list[Finding]:
    """`_holds` refusing a tolerance of zero, which the text takes: its fault is "a number below zero"."""
    found = HOLDS(holds, value, pointer)
    if pointer.endswith("/tolerance/value") and value == 0.0:
        found.append(Finding("BC-048", pointer, "zero"))
    return found


def test_the_model_s_relation_fails_where_the_check_refuses_a_declaration_the_model_takes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A refusal where the model takes the declaration is one too many: a check adding one to its own answer,
    and the check with `_holds` refusing a tolerance of zero, which BC-016's declaration holds. The relation
    is quiet on the check as it is, which takes that declaration."""
    check_declaration(VALID, store())
    with pytest.raises(AssertionError, match=re.escape("gives [('BC-048', '/consumer')], the model []")):
        check_declaration(VALID, store(), adding(BuildRefusal("BC-048", "/consumer")))
    at = "/models/0/requirements/0/conditions/shear_rate/tolerance/value"
    monkeypatch.setattr(declarations, "_holds", zero_tolerance_refused)
    with pytest.raises(AssertionError, match=re.escape(f"gives [('BC-048', '{at}')], the model []")):
        check_declaration(VALID, store())


@pytest.mark.parametrize(
    "message",
    [
        "the declaration passed its own check, and this version reads none of its records while it holds "
        "what a later piece reads: S7a-3 reads the target /models/0/target",
        "a read whose target is an overlay is not built yet",
        "want: fit on a field holding a fit record is not read yet",
        "the waiver /acceptances/0 names the label 'x', and would cover a reason only where that label is "
        "trusted",
    ],
)
def test_a_not_implemented_error_of_a_piece_to_come_passes_the_relations(message: str) -> None:
    check_declaration(VALID, store(), raising(NotImplementedError(message)))


def test_a_declaration_holding_what_a_later_piece_reads_passes_the_relations() -> None:
    with_a_target = placed(VALID, "/models/0/target/tissue_state", {"token": "ex_vivo_fresh"})
    with pytest.raises(NotImplementedError, match="S7a-3"):
        check_build(with_a_target, store())
    check_declaration(with_a_target, store())


# The thirteen divergences the target's runs found, fixed on `main` (the model's, then the check's), each as
# the example that showed it: the check and the model now give the same refusals on it, with no divergence
# listed (`KNOWN_DIVERGENCES` is empty).

INPUTS = BUILD_CHECKS / "inputs"


def loaded(name: str) -> JsonValue:
    return cast(JsonValue, json.loads((INPUTS / name).read_bytes()))


def taken_out(value: JsonValue, pointer: str, name: str) -> JsonValue:
    copied = copy.deepcopy(value)
    found = member_at(copied, pointer)
    assert found is not None
    assert isinstance(found[0], dict)
    del found[0][name]
    return copied


def put(name: str, *changes: tuple[str, JsonValue]) -> JsonValue:
    value = loaded(name)
    for pointer, member in changes:
        value = placed(value, pointer, member)
    return value


WITHOUT_REASON = taken_out(VALID, "/models/0/acceptances/0", "reason")
# A pick the model takes, BC-005's pick with its `reason`: past its check, the build's picks are S7c's.
PICK_TAKEN = put("bc005_pick_without_reason.json", ("/models/0/acceptances/1/reason", "r"))
TWO_ALTERNATIVES = put(
    "bc048_trainable_field_not_read.json",
    ("/models/0/checked_over/path", "lumen"),
    ("/models/0/checked_over/records/0/version", {"x": 1.0}),
)
WITNESSES: dict[str, JsonValue] = {
    "waiver_label_of_another_type": put(
        "bc050_requirement_without_review.json", ("/models/0/acceptances/0/label", 1.0)
    ),
    "waiver_condition_beside_a_code_at_fault": taken_out(
        loaded("bc002_both_records_listed.json"), "/models/0/acceptances/0", "code"
    ),
    "waiver_condition_of_another_type": put(
        "bc002_both_records_listed.json", ("/models/0/acceptances/0/condition", None)
    ),
    "trainable_location_beside_a_fault": put(
        "bc048_trainable_field_not_read.json", ("/models/0/trainable/0/record/id", None)
    ),
    "name_given_twice_beside_a_fault": put(
        "bc048_record_listed_twice.json", ("/models/0/checked_over/records/0/x", 1.0)
    ),
    "status_object_off_its_shape": put(
        "bc005_accepted_difference_without_reason.json", ("/models/0/acceptances/1/value/x", 1.0)
    ),
    "label_beside_an_unregistered_field": put(
        "bc050_requirement_without_review.json",
        ("/models/0/requirements/0/field", "K"),
        ("/models/0/requirements/0/label", "x"),
    ),
    "inside_a_member_at_fault": put(
        "bc004_tolerance_without_reason.json",
        ("/models/0/requirements/0/conditions/test_method/tolerance", {"value": "x", "unit": 1.0}),
    ),
    "inside_one_of_two_alternatives": TWO_ALTERNATIVES,
    "parameters_beside_a_distribution_at_fault": put(
        "bc051_distribution_acceptance.json",
        ("/models/0/acceptances/1/distribution", "drag"),
        ("/models/0/acceptances/1/distribution_parameters/stock", ""),
    ),
    "combination_beside_its_fields_at_fault": put(
        "bc048_trainable_field_not_read.json", ("/models/0/combinations", [["", ""]])
    ),
    "region_conditions_of_another_type": put(
        "bc051_region_conditions.json", ("/models/0/region_conditions", None)
    ),
    # The thirteenth, from CI's fuzz run 40275055796: a nominal acceptance's `params` beside a `field` that
    # names no registered field (the input that crashed four runs of ten with no fault seeded).
    "params_beside_an_unregistered_field": put(
        "bc006_every_kind_s7a_2_reads.json",
        (
            "/models/0/acceptances/3",
            {
                "acceptance": "nominal",
                "params": {
                    "id": "conformance/water_fixture",
                    "version": "1.0.0",
                    "content_hash": "sha512:c2",
                },
                "field": "fluid.dyna",
                "reason": "the model needs onbration",
            },
        ),
    ),
}


def test_no_divergence_is_listed() -> None:
    assert KNOWN_DIVERGENCES == {}


@pytest.mark.parametrize("name", sorted(WITNESSES))
def test_the_check_and_the_model_give_the_same_refusals_on_a_divergence_found_once(name: str) -> None:
    """The witness is refused, with every rule's refusals placed by the model (so that the equality below
    compares something), and the relation holds with nothing listed."""
    declaration = WITNESSES[name]
    verdict = build_model.check_build(json.dumps(declaration).encode(), BUILD)
    assert isinstance(verdict, build_model.Refused)
    assert not verdict.unplaced
    wanted = {(refusal.item, refusal.pointer) for refusal in verdict.refusals}
    assert wanted
    assert {(one.item, one.pointer) for one in check_build(declaration, store()).refusals} == wanted
    check_declaration(declaration, store())


def test_a_divergence_listed_is_let_through_and_fails_the_relation_unlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mechanism an empty list keeps: a check that refuses a declaration the model takes fails the
    relation, and passes it where an `Explains` function names that refusal."""
    refusal = BuildRefusal("BC-048", "/models/0/model")
    with pytest.raises(AssertionError, match=r"^the implementation gives "):
        check_declaration(VALID, store(), refused(refusal))
    listed: dict[str, build_oracle.Explains] = {"listed": lambda _, found, wanted: set(found)}
    monkeypatch.setattr(build_oracle, "KNOWN_DIVERGENCES", listed)
    check_declaration(VALID, store(), refused(refusal))


# The target, through its own `test_one_input`.


def _instrumenting_nothing(**_: object) -> contextlib.AbstractContextManager[None]:
    return contextlib.nullcontext()


def _as_it_is(function: Callable[..., object]) -> Callable[..., object]:
    return function


@pytest.fixture
def target(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """`build_bytes.py`, imported with Atheris stubbed: the core it reads is not instrumented here."""
    atheris = ModuleType("atheris")
    atheris.__dict__.update(instrument_imports=_instrumenting_nothing, instrument_func=_as_it_is)
    monkeypatch.setitem(sys.modules, "atheris", atheris)
    import tests.fuzz.build_bytes as module

    return module


Seed = tuple[str, JsonValue, tuple[str, ...]]


def seeds_of(target: ModuleType) -> list[tuple[Seed, RecordStore]]:
    """The target's seed declarations, each with its name and records' names, beside its store."""
    seeds: list[Seed] = target.SEEDS
    stores: list[RecordStore] = target.STORES
    return list(zip(seeds, stores, strict=True))


def seed_refusals(target: ModuleType) -> list[object]:
    """Each seed declaration's refusals as `check_build` gives them, or "not built" past its check."""
    found: list[object] = []
    for (_, value, _), records in seeds_of(target):
        try:
            found.append(sorted((one.item, one.pointer) for one in check_build(value, records).refusals))
        except NotImplementedError:
            found.append("not built")
    return found


def test_every_seed_passes_the_target_with_no_fault_and_with_the_control_fault(
    target: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    seeds: list[tuple[str, bytes]] = list(target.seeds())
    assert len(seeds_of(target)) == len(
        {
            json.loads(path.read_text())["inputs"]["declaration"]
            for path in (BUILD_CHECKS / "cases").glob("*.json")
        }
    )
    assert len(seeds) > 7_000
    for _, data in seeds:
        target.test_one_input(data)
    monkeypatch.setattr(declarations, "_reasons", faulty_reasons)
    for _, data in seeds:
        target.test_one_input(data)


def test_the_readme_counts_the_target_s_seeds(target: ModuleType) -> None:
    """`tests/fuzz/README.md`'s counts of the seed declarations and inputs, which a new build-check case
    changes."""
    text = (Path(__file__).parents[1] / "fuzz" / "README.md").read_text(encoding="utf-8")
    declarations, inputs = len(seeds_of(target)), sum(1 for _ in target.seeds())
    assert f"one of the {declarations} declarations the build-check cases read" in text
    assert f"seven of the {declarations} seed declarations" in text
    assert f"roots included ({inputs:,} inputs)" in text


def test_no_seed_shows_the_control_fault_and_one_change_of_a_pointer_does(
    target: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control's premise: no seed declaration is refused otherwise with the fault seeded; and BC-005's
    seeds of a second acceptance without its `reason` or `basis`, that acceptance written a third time at the
    next place, one byte of a seed's pointer, are."""
    plain = seed_refusals(target)
    with monkeypatch.context() as patch:
        patch.setattr(declarations, "_reasons", faulty_reasons)
        assert seed_refusals(target) == plain
    shown = 0
    for (name, value, _), records in seeds_of(target):
        models = value.get("models") if isinstance(value, dict) else None
        model = models[0] if isinstance(models, list) and models else None
        acceptances = model.get("acceptances") if isinstance(model, dict) else None
        if not name.startswith("bc005_") or not isinstance(acceptances, list) or len(acceptances) < 2:
            continue
        changed = placed(value, "/models/0/acceptances/2", acceptances[1])
        before = sorted((one.item, one.pointer) for one in check_build(changed, records).refusals)
        with monkeypatch.context() as patch:
            patch.setattr(declarations, "_reasons", faulty_reasons)
            after = sorted((one.item, one.pointer) for one in check_build(changed, records).refusals)
        assert ("BC-005", "/models/0/acceptances/2") in before, name
        assert ("BC-048", "/models/0/acceptances/2") in after, name
        shown += 1
    assert shown == 7


def test_the_control_s_fault_fails_the_model_s_relation_with_the_line_ci_reads_as_its_find(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BC-005's seed of a second acceptance without its `reason`, that acceptance written a third time: the
    relation passes it, and fails it with S7a-1's control fault seeded, with a line that `ci.yml`'s control
    step and `scripts/measure.py`'s fuzz kind read as the control's find (`CONTROLS["declarations"]`)."""
    seed = loaded("bc005_accepted_difference_without_reason.json")
    acceptances = member_at(seed, "/models/0/acceptances")
    assert acceptances is not None
    assert isinstance(acceptances[0], list)
    changed = placed(seed, "/models/0/acceptances/2", acceptances[0][1])
    check_declaration(changed, store())
    monkeypatch.setattr(declarations, "_reasons", faulty_reasons)
    with pytest.raises(AssertionError) as found:
        check_declaration(changed, store())
    assert found_in(f"AssertionError: {found.value}", CONTROLS["declarations"]), str(found.value)


def test_the_control_s_fault_beside_another_missing_member_is_its_find_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same third acceptance without its `section` too: the check's BC-048 there, for the `section` and
    for the `reason` the fault leaves to the shape table, is the model's as well, for the `section`, so the
    line shows the model's BC-005 alone, as four of the ten runs of `measure.yml`'s fuzz kind found the fault
    (run 40263772231); it is the control's find too."""
    seed = loaded("bc005_accepted_difference_without_reason.json")
    acceptances = member_at(seed, "/models/0/acceptances")
    assert acceptances is not None
    assert isinstance(acceptances[0], list)
    third = acceptances[0][1]
    assert isinstance(third, dict)
    without_section = {name: held for name, held in third.items() if name != "section"}
    changed = placed(seed, "/models/0/acceptances/2", without_section)
    check_declaration(changed, store())
    monkeypatch.setattr(declarations, "_reasons", faulty_reasons)
    alone = "the implementation gives [], the model [('BC-005', '/models/0/acceptances/2')]"
    with pytest.raises(AssertionError, match=re.escape(alone)) as found:
        check_declaration(changed, store())
    assert found_in(f"AssertionError: {found.value}", CONTROLS["declarations"]), str(found.value)


def test_seven_seeds_show_the_design_s_fault_unnarrowed(
    target: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Why the control's fault is narrowed: item 4 skipping every acceptance after a model's first, as the S7
    design words it, changes the refusals of seven seed declarations unchanged by the fuzzer."""
    original = declarations._reasons  # pyright: ignore[reportPrivateUsage]

    def later(pointer: str) -> bool:
        parts = pointer.split("/")
        return len(parts) == 5 and parts[3] == "acceptances" and parts[4] != "0"

    def after_the_first(declaration: JsonObject) -> list[Finding]:
        return [
            finding
            for finding in original(declaration)
            if not (finding.case == "BC-005" and later(finding.pointer))
        ]

    plain = seed_refusals(target)
    monkeypatch.setattr(declarations, "_reasons", after_the_first)
    assert sum(before != after for before, after in zip(plain, seed_refusals(target), strict=True)) == 7


# The results relations, through the target (S7a-2, the S7 design's 6.5).

OUTSIDE_READ = (
    "bc001_condition_outside_at_another_temperature.json",
    "bc001_declared_range_against_a_stated_value.json",
    "bc017_implied_value_outside_the_tolerance.json",
    "bc027_label_mismatch_beside_condition_outside.json",
)
WAIVED_ALREADY = "bc038_waiver_of_condition_outside.json"
LAW = "accepted with condition_outside, which no assumption or trainable acceptance covers"


def target_input(choice: int, pointer: str, member: JsonValue) -> bytes:
    return bytes([choice]) + pointer.encode() + b"\n" + json.dumps(member).encode()


def kept(choice: int, value: JsonValue) -> bytes:
    """The input that picks `choice` and puts its declaration's own `consumer` back in place: the
    declaration unchanged, a planted waiver kept."""
    assert isinstance(value, dict)
    return target_input(choice, "/consumer", value["consumer"])


def test_a_first_byte_past_the_seeds_picks_a_declaration_read_outside_with_a_waiver_of_it_planted(
    target: ModuleType,
) -> None:
    """The control `judge`'s seeds (the S7 design's 6.5): every declaration whose cases give a result
    `condition_outside`, BC-038's holding a waiver naming it already and each other one, picked by a first
    byte past the seeds', with one planted; every member of each at its pointer passes the target, with no
    fault seeded, the planted waiver covering nothing."""
    names = [name for name, _, _ in target.SEEDS]
    assert sorted(target.OUTSIDE) == sorted((*OUTSIDE_READ, WAIVED_ALREADY))
    assert [names[index] for index, _ in target.PLANTED] == list(OUTSIDE_READ)
    assert len(target.CHOICES) == len(names) + len(OUTSIDE_READ) <= 256
    for choice in range(len(names), len(target.CHOICES)):
        value: JsonValue = target.CHOICES[choice][0]
        assert value != target.SEEDS[target.PLANTED[choice - len(names)][0]][1]
        target.test_one_input(kept(choice, value))
        for pointer, member in target.members(value):
            target.test_one_input(target_input(choice, pointer, member))


def test_4_2s_own_law_fails_through_the_target_where_a_waiver_covers_condition_outside(
    target: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_covers` letting a waiver naming `condition_outside` cover it (the design's fault for the control
    `judge`): BC-038's seed fails the target at 4.2's own law, unchanged, and so does each planted choice
    whose result holds no other reason a waiver cannot cover; BC-027's, whose `label_mismatch` keeps its
    result refused, fails at the results model's relation alone, the verdict's `accepted_by` and
    `not_accepted`."""
    names = [name for name, _, _ in target.SEEDS]
    monkeypatch.setattr(acceptance, "_covers", waiver_covers_condition_outside)
    seed = names.index(WAIVED_ALREADY)
    with pytest.raises(AssertionError, match=LAW):
        target.test_one_input(kept(seed, target.SEEDS[seed][1]))
    for offset, (index, value) in enumerate(target.PLANTED):
        modelled = names[index].startswith("bc027_")
        wanted = (
            r"^\('drag', .*\): \('not_met', .*, False, .*\), the model's \('not_met', " if modelled else LAW
        )
        with pytest.raises(AssertionError, match=wanted):
            target.test_one_input(kept(len(names) + offset, value))


def test_the_refusal_law_fails_through_the_target_where_refused_reads_the_first_model_alone(
    target: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`refused` read from the first model's results alone: each seed declaration whose report holds a result
    not accepted after a first model's all accepted fails the target at the refusal law, and there are such
    seeds."""
    monkeypatch.setattr(BuildReport, "refused", property(first_model_alone))
    caught: list[str] = []
    for choice, (_, value, _) in enumerate(target.SEEDS):
        try:
            target.test_one_input(target_input(choice, "", value))
        except AssertionError as error:
            caught.append(str(error))
    assert caught
    assert all(message == "refused False, where its refusals and results give True" for message in caught)
