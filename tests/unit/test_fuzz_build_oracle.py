# SPDX-License-Identifier: Apache-2.0
"""`build_bytes.py`'s oracle (`tests/fuzz/build_oracle.py`), which the target, needing Atheris, cannot show
here: a JSON pointer read, resolved and written to as RFC 6901 says; each of the three relations quiet on the
check as it is and failing on a check broken for it; and, through the target's own `test_one_input` with
Atheris stubbed, every seed passing the target, with no fault seeded and with S7a-1's control fault, which
no seed shows, one change to a seed's pointer does, and the design's unnarrowed fault seven seeds show at
once."""

import contextlib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

import materica
from materica.core import declarations
from materica.core.build import check_build
from materica.core.declarations import Finding, JsonObject
from materica.core.jsonio import JsonValue
from materica.core.record import RecordStore
from materica.core.report import BuildRefusal, BuildReport
from tests.fuzz.build_oracle import check_declaration, index_of, placed, resolves, tokens_of
from tests.fuzz.seeded_fault import faulty_reasons

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
