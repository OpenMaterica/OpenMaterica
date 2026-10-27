# SPDX-License-Identifier: Apache-2.0
# Atheris installs on Python 3.12 to 3.14 only; elsewhere its stub in typings/ stands in for it.
# pyright: reportMissingModuleSource=false
"""Fuzz target `build_bytes.py` (the S7 design's 6.4 and 6.5, "Fuzzing"): raw bytes in place of one member of
a build-check case's declaration (`declarations.md` section 1), checked by `check_build`, and the report it
gives held to the build's results relations.

    python -m tests.fuzz.build_bytes --seed CORPUS     # copy the seed corpus into CORPUS
    python -m tests.fuzz.build_bytes --dict FILE       # write the dictionary of declarations
    python -m tests.fuzz.build_bytes CORPUS -dict=FILE [libFuzzer options]

The first byte picks a seed declaration, one of those the build-check suite's cases read, or, past them, one
of those whose cases give a result `condition_outside`, with a waiver naming it and its condition planted in
that result's model where none is (`PLANTED`: the S7 design's 6.5, the seeds of the control `judge`); the
bytes after it, up to the first newline, are a JSON pointer (RFC 6901) to a member of it, or to one its object
does not hold yet, or to the end of one of its lists; the rest, read by `jsonio.parse`, stands in that
member's place, and `check_build` checks the declaration over the records the seed's case reads. The target
fails when `check_build` raises anything but a `NotImplementedError` of what this version does not build past
the declaration's own check, when a refusal's pointer names no member of the declaration, when a refusal names
a case outside the refusal paragraph's, or when the build's reference model (`tests/reference/build_model.py`)
refuses the declaration and the check's refusals differ from its own as no known divergence says: the
relations of `build_oracle.py`, which `tests/unit/test_fuzz_build_oracle.py` shows failing; and when the
report the build gives breaks a results relation of `build_results_oracle.py` (section 4.2's own law, the
refusal law, or the build's results model where it decides), which `tests/unit/test_fuzz_build_results.py`
shows failing. The seeds are every member of every seed declaration, each at its own pointer, and each whole
declaration at the empty pointer; a planted declaration is a change of the first byte away from its seeds.
"""

import copy
import json
import sys
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import atheris

# Imported first, and inside this block, so that Atheris instruments the core for its coverage.
with atheris.instrument_imports(include=["materica"]):
    from materica.core import jsonio
    from materica.core.build import check_build
    from materica.core.record import RecordStore

from materica.core.declarations import CLAIMS
from materica.core.jsonio import JsonValue
from materica.core.reasons import Reason
from materica.core.report import BuildReport
from materica.core.vocabulary import VOCABULARY
from tests.fuzz import seeded_fault
from tests.fuzz.build_oracle import check_declaration, placed
from tests.fuzz.build_results_oracle import check_against_the_model, check_results

BUILD_CHECKS = Path(jsonio.__file__).parents[1] / "data" / "conformance" / "build_checks"


def seed_cases() -> list[tuple[str, JsonValue, tuple[str, ...]]]:
    """Each declaration the build-check cases read, once, in the order of their files, with the records of the
    first case that reads it: its name, its value, and the records' names."""
    found: dict[str, tuple[str, JsonValue, tuple[str, ...]]] = {}
    for path in sorted((BUILD_CHECKS / "cases").glob("*.json")):
        inputs = json.loads(path.read_text(encoding="utf-8"))["inputs"]
        name = inputs["declaration"]
        if name not in found:
            value: JsonValue = json.loads((BUILD_CHECKS / "inputs" / name).read_text(encoding="utf-8"))
            found[name] = (name, value, tuple(inputs.get("records", ())))
    return list(found.values())


def sources_of(names: tuple[str, ...]) -> tuple[bytes, ...]:
    return tuple((BUILD_CHECKS / "inputs" / name).read_bytes() for name in names)


def store_of(names: tuple[str, ...]) -> RecordStore:
    store = RecordStore()
    for name, data in zip(names, sources_of(names), strict=True):
        store.add(name, data)
    return store


SEEDS = seed_cases()
STORES = [store_of(names) for _, _, names in SEEDS]
SOURCES = [sources_of(names) for _, _, names in SEEDS]

# A result read `condition_outside`: its model's name, its record's reference (id, version, hash), its field
# and the condition.
Outside = tuple[str, tuple[str, str, str], str, str]
PLANTED_REASON = "planted by build_bytes.py: a waiver naming condition_outside, which 4.2 lets cover nothing"


def read_outside() -> dict[str, set[Outside]]:
    """Each declaration the build-check cases read, with the results its cases expect read
    `condition_outside`: the cases' own answers, not the build's."""
    found: dict[str, set[Outside]] = {}
    for path in sorted((BUILD_CHECKS / "cases").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        for result in case["expected"].get("results", []):
            record = result["record"]
            for reason in result["reasons"]:
                if reason["code"] == "condition_outside":
                    reference = (record["id"], record["version"], record["content_hash"])
                    read = (result["model"], reference, result["field"], reason["condition"])
                    found.setdefault(case["inputs"]["declaration"], set()).add(read)
    return found


def acceptances_of(models: JsonValue, name: str) -> list[JsonValue]:
    """The acceptances of the one model of a seed declaration's `models` named `name`."""
    assert isinstance(models, list)
    found = [
        model["acceptances"]
        for model in models
        if isinstance(model, dict) and isinstance(model["model"], dict) and model["model"]["name"] == name
    ]
    [acceptances] = found
    assert isinstance(acceptances, list), name
    return acceptances


def planted(value: JsonValue, reads: set[Outside]) -> JsonValue | None:
    """`value` with a waiver naming `condition_outside` and its condition, at the result's record and field,
    at the end of the acceptances of each result's model that holds no such waiver; None where every one
    does."""
    declaration = copy.deepcopy(value)
    assert isinstance(declaration, dict)
    added = False
    for name, (identifier, version, content_hash), field, condition in sorted(reads):
        acceptances = acceptances_of(declaration["models"], name)
        waiver: dict[str, JsonValue] = {
            "acceptance": "waiver",
            "record": {"id": identifier, "version": version, "content_hash": content_hash},
            "field": field,
            "condition": condition,
            "code": "condition_outside",
        }
        if any(isinstance(entry, dict) and waiver.items() <= entry.items() for entry in acceptances):
            continue
        acceptances.append({**waiver, "reason": PLANTED_REASON})
        added = True
    return declaration if added else None


OUTSIDE = read_outside()
# The declarations a choice of the first byte past the seeds' picks, each with its seed's records.
PLANTED = [
    (index, found)
    for index, (name, value, _) in enumerate(SEEDS)
    if name in OUTSIDE and (found := planted(value, OUTSIDE[name])) is not None
]
CHOICES: list[tuple[JsonValue, RecordStore, tuple[bytes, ...]]] = [
    *zip((value for _, value, _ in SEEDS), STORES, SOURCES, strict=True),
    *((found, STORES[index], SOURCES[index]) for index, found in PLANTED),
]


def with_results(sources: Sequence[bytes]) -> Callable[[JsonValue, RecordStore], BuildReport]:
    """`check_build`, the report it gives held to the results relations: section 4.2's own law and the refusal
    law, then the build's results model, of the JSON text `json.dumps` writes, over the records' bytes
    `sources`, under the default claims the build reads with."""

    def check(declaration: JsonValue, store: RecordStore) -> BuildReport:
        report = check_build(declaration, store)
        check_results(report)
        check_against_the_model(json.dumps(declaration).encode(), sources, CLAIMS, report)
        return report

    return check


def test_one_input(data: bytes) -> None:
    if not data:
        return
    value, store, sources = CHOICES[data[0] % len(CHOICES)]
    head, newline, text = data[1:].partition(b"\n")
    if not newline:
        return
    try:
        pointer = head.decode("utf-8")
    except UnicodeDecodeError:
        return
    member = jsonio.parse(text)
    if isinstance(member, Reason):
        return
    if pointer == "":
        check_declaration(member, store, with_results(sources))
        return
    declaration = placed(value, pointer, member)
    if declaration is not None:
        check_declaration(declaration, store, with_results(sources))


# The seeds, and the dictionary.


def members(value: JsonValue, pointer: str = "") -> Iterator[tuple[str, JsonValue]]:
    """Each member of `value` at every depth, its root first, with its pointer."""
    yield pointer, value
    if isinstance(value, dict):
        for name, item in value.items():
            yield from members(item, f"{pointer}/{name.replace('~', '~0').replace('/', '~1')}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from members(item, f"{pointer}/{index}")


def seeds() -> Iterator[tuple[str, bytes]]:
    """Every member of every seed declaration, at its pointer, its root among them."""
    for number, (name, value, _) in enumerate(SEEDS):
        for position, (pointer, member) in enumerate(members(value)):
            data = bytes([number]) + pointer.encode() + b"\n" + json.dumps(member).encode()
            yield f"{Path(name).stem}-{position}", data


def seed_corpus(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in seeds():
        (directory / name).write_bytes(data)


def dictionary() -> Iterator[str]:
    """JSON's structure; every member name and string of the seed declarations; the kinds of acceptance, the
    registered fields, conditions, facts, sections, labels and reasons, and the vocabulary's token lists."""
    yield from ('"{"', '"}"', '"["', '"]"', '":"', '","', '"null"', '"true"', '"false"', '"-0"', '"1e308"')
    names: set[str] = {
        *VOCABULARY.acceptance_kinds,
        *VOCABULARY.fields,
        *VOCABULARY.conditions,
        *VOCABULARY.facts,
        *VOCABULARY.sections,
        *VOCABULARY.reasons,
        *(token for tokens in VOCABULARY.token_lists.values() for token in tokens),
    }
    for _, value, _ in SEEDS:
        for pointer, member in members(value):
            names.update(token for token in pointer.split("/")[1:] if not token.isdigit())
            if isinstance(member, str):
                names.add(member)
    for name in sorted(names):
        yield json.dumps(json.dumps(name))


def main(arguments: list[str]) -> None:
    if arguments[1:2] == ["--seed"]:
        seed_corpus(Path(arguments[2]))
        return
    if arguments[1:2] == ["--dict"]:
        Path(arguments[2]).write_text("\n".join(dictionary()) + "\n", encoding="utf-8")
        return
    seeded_fault.seed_declarations_if_asked(atheris.instrument_func)
    seeded_fault.seed_judge_if_asked(atheris.instrument_func)
    atheris.Setup(arguments, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main(sys.argv)
