# SPDX-License-Identifier: Apache-2.0
"""Faults seeded in the core, which show that the fuzz targets find a fault and that the replay shrinks it.

- In `jsonio.parse`, for the first two targets: an exception escapes when the bytes read as an array whose
  first item is an empty object. No seed input holds the shape, so a fuzzer has to build it.
- In the read, for the third: an exception escapes when two copies of the target state its pin and are
  identical byte for byte, which a read must take as one record (`read_side_contract.md` section 3, step 1),
  beside an unreadable source, by a reader without the hash suite: a conjunction of three draws, which a
  fuzzer has to explore to meet.
- In step 10, for the fourth: an exception escapes for a temperature above 311 K stated with a plus or minus,
  beside a shear rate stated as a range other than 10 to 1000 1/s. No seed holds two of the three (S2a-3,
  2026-10-16): 18 hold a plus or minus on a temperature, at 310.15 K or below, 17 of them beside a shear rate
  of 10 to 1000 1/s and one beside an unstated one; three state a shear rate's range otherwise, with no plus
  or minus on their temperature; none a temperature above 311 K. So the fuzzer has to change two numbers of
  one seed, keeping the field through steps 8 and 9 to reach step 10, each change new coverage. It replaced
  the step-8 fault of S2a-2's fix round (a constant above 1 measured above 311 K whose statistics block
  represents a population's spread), which no seed held two parts of either, when the target came to read
  steps 9 and 10.

- In a composition's own member, the S2 design's control (section 1.7), for the third target and the fourth:
  an exception escapes for a composition whose `components` is empty, which step 8 must refuse
  (`record_format.md` section 6, composition item 5). The fourth target's seeds hold one (PR-051's
  `no_component`), so it finds it at once; the third has to draw it.

- In step 7, S4a's control for the fourth target, whose oracle is the reference model (`read_side_contract.md`
  section 3, step 7): an alternative refused at step 9 for its unit alone is set aside, not refusing the
  field, where it is the third or a later stored alternative. Nothing raises: the read gives an answer, which
  only the model's tells wrong. Of the 56 seed fields that hold alternatives, two hold three or more, and none
  a unit other than the registered one past the second (2026-10-19), so the fuzzer has to change one.

- In step 8, S3a's control for the fourth target: a table over temperature whose first knot lies below 250
  is refused (`form_invalid`) where the text reads it, and the model with it, to the end. Nothing raises:
  only the model's answer tells it wrong. Of the 113 seed fields that hold a table over temperature, none
  starts below 250 (2026-10-20), so the fuzzer has to lower one's first knot, in a table no other fault makes
  `form_invalid`.

- In a table's value, S3b-2's control for the fourth target, which reads a table at the places table item 3
  tells apart, one double above each edge among them: an exception escapes for a read in the interval just
  above an edge where the value just above lies outside 0.6 to 1.6 times the value just below, either way. No
  seed holds one: of the 22 edges the seed tables hold twice in `x`, the ratios of the value above to the
  value below lie between 0.99 and 1.2 (2026-10-21), so the fuzzer has to change a value at an edge, as
  halving or doubling either one does, in a table that keeps its edge.

- In step 0, S3c's control for the fifth target, which parses its bytes as one acceptance of fixed reads of
  two tables: an extrapolation's `method` compared ignoring case, so that `Constant` or `consumer_LAW` is
  taken where step 0 must refuse it (`declarations.md` section 4.1: "`method` (`constant` or
  `consumer_law`)"). Nothing raises: the read goes on, and the target's oracle, which holds an extrapolation
  that breaks its shape to a refusal wherever it is located (`acceptance_oracle.check_shape_refused`), finds
  it, and the model's answer too. No seed holds such a method (2026-10-21), and every seed holding an
  extrapolation is one changed letter from one. The S3 design names a `law` that is a number taken under
  `constant`, which a seed holds (`PR-330.extrapolation_law_not_string`); under `consumer_law`, which no seed
  holds beside a number, it is two aligned changes away, and five local runs of 600 s found it in none
  (2026-10-21).

- In step 7, S4d's control for the fourth target, which reads a field's table alternatives at their places
  too (`field_oracle.alternative_places`): a table alternative read outside its readable range, at no edge and
  with no extrapolation that would cover it, refuses the field where the text sets it aside
  (`read_side_contract.md` section 3, step 7), where a value of its `y` lies below 900. Nothing raises: only
  the model's answer tells it wrong. Ungated, four seeds would show it at once, each a density table whose `y`
  is 916 to 1000 read just below its readable range beside a constant that stays there; no seed shows it gated
  (2026-10-22). One change does: a value of such a table's `y` lowered below 900 (a changed digit, an erased
  one, a minus sign), or, where a table whose `y` lies below 900 already (a viscosity's) is read outside its
  range beside alternatives all set aside, a change that makes another stay (a byte of its condition's name,
  which leaves the condition unstated). The control's local runs found it both ways.

- In the declaration's own check, S7a-1's control for `build_bytes.py` (the S7 design's 6.4): item 4 skips
  every acceptance after a model's second, so that a third acceptance without its `reason` or `basis` is
  refused only by the shape table, as a member missing (BC-048), where the text gives BC-005. Nothing raises,
  and the pointer and the case are ones the target allows: only the target's relation to the build's
  reference model tells it wrong. The design's fault skipped every acceptance after the first: seven of the
  113 seed declarations, BC-005's arms of a second acceptance without its `reason` or `basis`, show that one
  unchanged (2026-10-25), so the fuzzer would find it at once and show nothing; no seed holds a third
  acceptance without either.

Each of the first four raises its own message, and so does the seventh, so that CI can tell which fault a run
found; the fifth, the sixth, the ninth and the tenth are found by the oracle's assertion that the
implementation and the model disagree, and the eighth by the oracle's assertion that an extrapolation breaking
its shape is refused.

The first three targets seed the first two faults when `MATERICA_FUZZ_SEEDED_FAULT` is set, and pytest seeds
them when loaded as a plugin, `python -m pytest -p tests.fuzz.seeded_fault`. Only the fourth target seeds the
third, since the property targets draw conditions too and would find it before their own. Set to
`composition`, the variable seeds the composition's fault alone, in the third target and the fourth; set to
`alternatives`, step 7's alone, in the fourth; set to `tables`, step 8's table fault alone, in the fourth;
set to `table_edges`, the table value's alone, in the fourth; set to `extrapolation_method`, step 0's method
alone, in the fifth; set to `table_alternatives`, step 7's over a table alternative alone, in the fourth; set
to `declarations`, the declaration's check's alone, in `build_bytes.py`.
"""

import dataclasses
import math
import os
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Protocol, TypeVar

import pytest

from materica.core import conditions, declarations, evaluate, fields, jsonio, read
from materica.core.conditions import AxisEntry, ConditionsRead, ImpliedCondition
from materica.core.fields import RecordField
from materica.core.identifiers import MaterialRef
from materica.core.jsonio import JsonValue
from materica.core.read import FieldRead, Standing
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from materica.core.resolve import Refused, ResolvedRecord, resolve_record
from materica.core.value_shapes import Found, JsonObject, invalid
from materica.core.vocabulary import VOCABULARY
from materica.shapes import OperatingCondition, RequirementCondition, Suite

COMPOSITION = "composition"
ALTERNATIVES = "alternatives"
TABLES = "tables"
TABLE_EDGES = "table_edges"
EXTRAPOLATION_METHOD = "extrapolation_method"
TABLE_ALTERNATIVES = "table_alternatives"
DECLARATIONS = "declarations"
NAMED = (
    COMPOSITION,
    ALTERNATIVES,
    TABLES,
    TABLE_EDGES,
    EXTRAPOLATION_METHOD,
    TABLE_ALTERNATIVES,
    DECLARATIONS,
)

_parse = jsonio.parse


def faulty_parse(data: bytes) -> JsonValue | Reason:
    value = _parse(data)
    if isinstance(value, list) and value and value[0] == {}:
        raise IndexError("the seeded fault in parse")
    return value


def faulty_resolve_record(
    ref: MaterialRef, store: RecordStore, claims: Collection[Suite]
) -> ResolvedRecord | Refused:
    pinned = [
        copy for copy in store.get(ref.id, ref.version) if copy.value.get("content_hash") == ref.content_hash
    ]
    identical = len(pinned) > 1 and all(copy.data == pinned[0].data for copy in pinned)
    if identical and store.unparsed() and "hash" not in claims:
        raise IndexError("the seeded fault in the read")
    return resolve_record(ref, store, claims)


_check_conditions = conditions.check_conditions


def faulty_check_conditions(
    field: RecordField,
    operating: Mapping[str, OperatingCondition],
    required: Mapping[str, RequirementCondition],
    implied: Sequence[ImpliedCondition] = (),
    axis: AxisEntry | None = None,
) -> ConditionsRead:
    value = field.value if isinstance(field.value, dict) else {}
    held = value.get("conditions")
    held = held if isinstance(held, dict) else {}
    temperature, shear_rate = held.get("temperature"), held.get("shear_rate")
    if isinstance(temperature, dict) and isinstance(shear_rate, dict):
        entries = temperature.get("plus_minus")
        if isinstance(entries, list) and entries:
            kelvin = temperature.get("value")
            if isinstance(kelvin, float) and kelvin > 311.0:
                ends = shear_rate.get("range")
                if isinstance(ends, list) and len(ends) == 2 and ends != [10.0, 1000.0]:
                    raise IndexError("the seeded fault in step 10")
    return _check_conditions(field, operating, required, implied, axis)


_components = fields.components


def faulty_components(value: JsonValue, where: str, found: Found) -> None:
    if value == []:
        raise IndexError("the seeded fault in a composition")
    _components(value, where, found)


_standing = read._standing  # pyright: ignore[reportPrivateUsage]


def faulty_standing(found: FieldRead) -> Standing:
    standing = _standing(found)
    refused_for_its_unit = {
        reason.code for reason in found.reasons if VOCABULARY.reasons[reason.code].status == "not_met"
    } == {"unit_mismatch"}
    third_or_later = found.alternative is not None and found.alternative >= 2
    return "set_aside" if standing == "refuses" and refused_for_its_unit and third_or_later else standing


_points = fields._points  # pyright: ignore[reportPrivateUsage]


def faulty_points(entry: JsonObject, where: str, found: Found) -> None:
    _points(entry, where, found)
    x = fields._numbers(entry.get("x"))  # pyright: ignore[reportPrivateUsage]
    if entry.get("axis") == "temperature" and x and x[0] < 250.0:
        found.append(invalid(f"{where}: the seeded fault in a table"))


_value = evaluate.value

# The band of the table value's fault: the ratio of the value just above an edge to the value just below that
# no read raises for, its ends included. Two-sided, so that halving or doubling either value leaves it, as
# libFuzzer's changes to a number most often do; a one-sided band (below 0.6 alone) saw half of them.
LEAST_RATIO, MOST_RATIO = 0.6, 1.6


def faulty_value(x: Sequence[float], y: Sequence[float], scheme: evaluate.Scheme, at: float) -> float:
    below, above = evaluate.interval(x, at)
    if 0 < below < above and x[below] == x[below - 1]:
        ratio = y[below] / y[below - 1] if y[below - 1] != 0 else math.inf
        if not LEAST_RATIO <= ratio <= MOST_RATIO:
            raise ArithmeticError("the seeded fault in a table's value")
    return _value(x, y, scheme, at)


_extrapolation = read._extrapolation  # pyright: ignore[reportPrivateUsage]


def faulty_extrapolation(
    index: int, entry: dict[str, JsonValue], found: list[Reason]
) -> read.Extrapolation | None:
    method = entry.get("method")
    if isinstance(method, str) and method.lower() in read._EXTRAPOLATION_METHODS:  # pyright: ignore[reportPrivateUsage]
        taken = _extrapolation(index, {**entry, "method": method.lower()}, found)
        return None if taken is None else dataclasses.replace(taken, method=method)  # type: ignore[arg-type]
    return _extrapolation(index, entry, found)


_form_range = read.form_range


# The values of `y` below which the table alternatives' fault shows: four seeds' tables hold 916 to 1000.
LEAST_VALUE = 900.0


def faulty_form_range(table: JsonObject, request: read.ReadRequest) -> read.FormRange:
    """A table read outside its readable range, at no edge and with no extrapolation covering it, a value of
    its `y` below `LEAST_VALUE`, reported without `outside_range` standing alone, which step 7 alone reads: a
    table alternative then refuses the field where it is set aside; a field read alone is read as before."""
    found = _form_range(table, request)
    values = table.get("y")
    low = isinstance(values, list) and any(isinstance(y, float) and y < LEAST_VALUE for y in values)
    if low and found.outside_alone and found.extrapolation is None:
        return dataclasses.replace(found, outside_alone=False)
    return found


_reasons = declarations._reasons  # pyright: ignore[reportPrivateUsage]


def faulty_reasons(declaration: JsonObject) -> list[declarations.Finding]:
    """S7a-1's control: item 4 skips every acceptance after a model's second (`declarations.md` section 1:
    "Every acceptance MUST carry a `reason`"), so a later acceptance without its `reason` or `basis` is left
    to the shape table's missing member."""

    def after_the_second(pointer: str) -> bool:
        parts = pointer.split("/")
        return len(parts) == 5 and parts[3] == "acceptances" and parts[4] not in ("0", "1")

    return [
        finding
        for finding in _reasons(declaration)
        if not (finding.case == "BC-005" and after_the_second(finding.pointer))
    ]


def seed() -> None:
    jsonio.parse = faulty_parse
    read.resolve_record = faulty_resolve_record  # type: ignore[attr-defined]  # read's own name for it, not exported


def seed_if_asked() -> None:
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") not in (None, "", *NAMED):
        seed()


_Function = TypeVar("_Function", bound=Callable[..., object])


class Instrument(Protocol):
    def __call__(self, function: _Function, /) -> _Function: ...


def seed_step_10_if_asked(instrument: Instrument) -> None:
    """The fourth target's fault, which only it seeds, since the property targets draw fields too.
    `instrument` is Atheris's, so that each part of the conjunction the fuzzer meets is new coverage and each
    comparison a hint, as in a real fault of the core."""
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") not in (None, "", *NAMED):
        read.check_conditions = instrument(faulty_check_conditions)  # type: ignore[attr-defined]  # read's own name


def seed_composition_if_asked(instrument: Instrument) -> None:
    """The S2 design's control, which the third target and the fourth seed where the variable asks for it
    by name, instrumented as the fourth's own fault is."""
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") == COMPOSITION:
        fields.components = instrument(faulty_components)


def seed_alternatives_if_asked(instrument: Instrument) -> None:
    """S4a's control, which the fourth target seeds where the variable asks for it by name, instrumented as
    its other faults are."""
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") == ALTERNATIVES:
        # Its parameter is named otherwise than `read._standing`'s, whose name is the module's here.
        read._standing = instrument(faulty_standing)  # type: ignore[assignment]  # pyright: ignore[reportPrivateUsage]


def seed_tables_if_asked(instrument: Instrument) -> None:
    """S3a's control, which the fourth target seeds where the variable asks for it by name, instrumented as
    its other faults are."""
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") == TABLES:
        fields._points = instrument(faulty_points)  # pyright: ignore[reportPrivateUsage]


def seed_table_edges_if_asked(instrument: Instrument) -> None:
    """S3b-2's control, which the fourth target seeds where the variable asks for it by name, instrumented as
    its other faults are."""
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") == TABLE_EDGES:
        evaluate.value = instrument(faulty_value)


def seed_extrapolation_method_if_asked(instrument: Instrument) -> None:
    """S3c's control, which the fifth target seeds where the variable asks for it by name, instrumented as the
    fourth's faults are."""
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") == EXTRAPOLATION_METHOD:
        read._extrapolation = instrument(faulty_extrapolation)  # pyright: ignore[reportPrivateUsage]


def seed_table_alternatives_if_asked(instrument: Instrument) -> None:
    """S4d's control, which the fourth target seeds where the variable asks for it by name, instrumented as
    its other faults are."""
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") == TABLE_ALTERNATIVES:
        read.form_range = instrument(faulty_form_range)


def seed_declarations_if_asked(instrument: Instrument) -> None:
    """S7a-1's control, which `build_bytes.py` seeds where the variable asks for it by name, instrumented as
    the other targets' faults are."""
    if os.environ.get("MATERICA_FUZZ_SEEDED_FAULT") == DECLARATIONS:
        declarations._reasons = instrument(faulty_reasons)  # pyright: ignore[reportPrivateUsage]


def pytest_configure(config: pytest.Config) -> None:
    seed()
