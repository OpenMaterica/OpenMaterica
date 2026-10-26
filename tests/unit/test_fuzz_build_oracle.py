# SPDX-License-Identifier: Apache-2.0
"""`build_bytes.py`'s oracle (`tests/fuzz/build_oracle.py`), which the target, needing Atheris, cannot show
here: a JSON pointer read, resolved and written to as RFC 6901 says; each of the three relations quiet on the
check as it is and failing on a check broken for it; and, through the target's own `test_one_input` with
Atheris stubbed, every seed passing the target, with no fault seeded and with S7a-1's control fault, which
no seed shows, one change to a seed's pointer does, and the design's unnarrowed fault seven seeds show at
once."""

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
from materica.core import declarations
from materica.core.build import check_build
from materica.core.declarations import Finding, JsonObject
from materica.core.jsonio import JsonValue
from materica.core.record import RecordStore
from materica.core.report import BuildRefusal, BuildReport
from scripts.measure import CONTROLS
from tests.fuzz import build_oracle
from tests.fuzz.build_oracle import (
    KNOWN_DIVERGENCES,
    NOT_BUILT,
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

BUILD_CHECKS = Path(materica.__file__).parent / "data" / "conformance" / "build_checks"
# A declaration the check takes: BC-016's, one model over water with one waiver.
VALID: JsonValue = json.loads(
    (BUILD_CHECKS / "inputs" / "bc016_waiver_at_one_of_two_records.json").read_bytes()
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
    check_declaration(VALID, store(), refused(BuildRefusal("BC-048", "/models/0/model")))


def test_a_refusal_of_another_case_fails_the_relations() -> None:
    with pytest.raises(AssertionError, match="which no rule of the declaration's names"):
        check_declaration(VALID, store(), refused(BuildRefusal("BC-016", "")))


# The model's relation: the check's refusals held to the model's where it refuses with every rule placed.


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


def test_the_model_s_relation_holds_nothing_where_the_model_gives_no_verdict() -> None:
    """The model gives no verdict for a declaration that passes its own check, nor where it places some
    rule's refusals not: an engine model over a domain, which item 7 may refuse (S11)."""
    check_declaration(VALID, store(), refused(BuildRefusal("BC-048", "/models/0/model")))
    over_a_domain = placed(VALID, "/models/0/checked_over", {"domain": "lumen"})
    engine: JsonValue = {
        "crosswalk": {"id": "materica/crosswalk", "version": "1.0.0", "sha256": "f" * 64},
        "values": {},
    }
    over_a_domain = placed(over_a_domain, "/models/0/engine", engine)
    verdict = build_model.check_build(json.dumps(over_a_domain).encode(), BUILD)
    assert not isinstance(verdict, build_model.Refused) or verdict.unplaced, verdict
    check_declaration(over_a_domain, store(), refused(BuildRefusal("BC-048", "/models/0/engine")))


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


# Each known divergence: an example the check and the model refuse apart, which the relation lets through
# with the divergence listed and fails without it.

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
TWO_ALTERNATIVES = put(
    "bc048_trainable_field_not_read.json",
    ("/models/0/checked_over/path", "lumen"),
    ("/models/0/checked_over/records/0/version", {"x": 1.0}),
)
DIVERGENCES: dict[str, JsonValue] = {
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
}


def test_every_known_divergence_has_an_example() -> None:
    assert set(DIVERGENCES) == set(KNOWN_DIVERGENCES)


@pytest.mark.parametrize("name", sorted(DIVERGENCES))
def test_a_known_divergence_passes_the_relation_and_fails_it_unlisted(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    check_declaration(DIVERGENCES[name], store())
    others = {other: explains for other, explains in KNOWN_DIVERGENCES.items() if other != name}
    monkeypatch.setattr(build_oracle, "KNOWN_DIVERGENCES", others)
    with pytest.raises(AssertionError, match=r"^the implementation gives "):
        check_declaration(DIVERGENCES[name], store())


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
    assert re.search(CONTROLS["declarations"].found, f"AssertionError: {found.value}"), str(found.value)


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
