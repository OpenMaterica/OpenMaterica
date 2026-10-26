# SPDX-License-Identifier: Apache-2.0
# Atheris installs on Python 3.12 to 3.14 only; elsewhere its stub in typings/ stands in for it.
# pyright: reportMissingModuleSource=false
"""Fuzz target `build_bytes.py` (the S7 design's 6.4, "Fuzzing"): raw bytes in place of one member of a
build-check case's declaration (`declarations.md` section 1), checked by `check_build`.

    python -m tests.fuzz.build_bytes --seed CORPUS     # copy the seed corpus into CORPUS
    python -m tests.fuzz.build_bytes --dict FILE       # write the dictionary of declarations
    python -m tests.fuzz.build_bytes CORPUS -dict=FILE [libFuzzer options]

The first byte picks a seed declaration, one of those the build-check suite's cases read; the bytes after it,
up to the first newline, are a JSON pointer (RFC 6901) to a member of it, or to one its object does not hold
yet, or to the end of one of its lists; the rest, read by `jsonio.parse`, stands in that member's place, and
`check_build` checks the declaration over the records the seed's case reads. The target fails when
`check_build` raises anything but a `NotImplementedError` of what this version does not build past the
declaration's own check, when a refusal's pointer names no member of the declaration, when a refusal names a
case outside the refusal paragraph's, or when the build's reference model (`tests/reference/build_model.py`)
refuses the declaration and the check's refusals differ from its own as no known divergence says: the
relations of `build_oracle.py`, which `tests/unit/test_fuzz_build_oracle.py` shows failing. The seeds are
every member of every seed declaration, each at its own pointer, and each whole declaration at the empty
pointer.
"""

import json
import sys
from collections.abc import Iterator
from pathlib import Path

import atheris

# Imported first, and inside this block, so that Atheris instruments the core for its coverage.
with atheris.instrument_imports(include=["materica"]):
    from materica.core import jsonio
    from materica.core.build import check_build
    from materica.core.record import RecordStore

from materica.core.jsonio import JsonValue
from materica.core.reasons import Reason
from materica.core.vocabulary import VOCABULARY
from tests.fuzz import seeded_fault
from tests.fuzz.build_oracle import check_declaration, placed

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


def store_of(names: tuple[str, ...]) -> RecordStore:
    store = RecordStore()
    for name in names:
        store.add(name, (BUILD_CHECKS / "inputs" / name).read_bytes())
    return store


SEEDS = seed_cases()
STORES = [store_of(names) for _, _, names in SEEDS]


def test_one_input(data: bytes) -> None:
    if not data:
        return
    seed = data[0] % len(SEEDS)
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
        check_declaration(member, STORES[seed], check_build)
        return
    declaration = placed(SEEDS[seed][1], pointer, member)
    if declaration is not None:
        check_declaration(declaration, STORES[seed], check_build)


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
    atheris.Setup(arguments, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main(sys.argv)
