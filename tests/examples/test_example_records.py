# SPDX-License-Identifier: Apache-2.0
"""The example records (`examples/`). Each is a record the writer and reader schemas take, with its content
hash and the record checks that can be made from it alone; each number in it is its source's, as the sources
were read for these examples; the note that they are not yet fully human-reviewed stands wherever they are
documented; and a read of each gives, at this release, what that documentation says. Each check has a
control that must fail."""

import copy
import json
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest

from materica import content_hash, load_records, read
from materica.core import jsonio
from materica.core.envelope import envelope_problems
from materica.core.jsonio import JsonValue
from materica.core.read import ReadResult
from materica.core.reasons import Reason
from materica.core.record import RecordStore
from materica.core.value_shapes import JsonObject, a_list, an_object, label_allowed
from materica.core.vocabulary import VOCABULARY
from tests.spec_sync.schemas import validator

REPOSITORY = Path(__file__).resolve().parents[2]
RECORDS = REPOSITORY / "examples" / "records"
FILES = ("water.json", "ndfeb_n45.json", "human_plasma.json")
# Where the examples are documented, each of which must say they are not yet fully human-reviewed.
DOCUMENTED = (
    REPOSITORY / "README.md",
    REPOSITORY / "examples" / "README.md",
    REPOSITORY / "docs" / "user_guide" / "quickstart.md",
)
NOTE = ("not reviewed library data", "not yet fully human-reviewed", "may change in a later commit")
WRITER = validator("record.writer.json")
READER = validator("record.reader.json")

Path_ = tuple[str | int, ...]


def example(name: str) -> JsonObject:
    """The example record in `name`, as a reader parses it (`record_format.md` section 1 item 6)."""
    parsed = jsonio.parse((RECORDS / name).read_bytes())
    assert isinstance(parsed, dict), f"{name}: {parsed}"
    return parsed


def at(value: JsonValue, path: Path_) -> JsonValue:
    for step in path:
        value = a_list(value)[step] if isinstance(step, int) else an_object(value)[step]
    return value


def sections(record: JsonObject) -> JsonObject:
    return an_object(an_object(record["body"])["sections"])


def value_fields(record: JsonObject) -> Iterator[tuple[str, JsonObject]]:
    """Each value field of `record`, an alternative as one, with the name of the field it belongs to."""
    for section, holder in sections(record).items():
        for field, value in an_object(an_object(holder)["fields"]).items():
            held = an_object(value)
            for alternative in a_list(held["alternatives"]) if "alternatives" in held else [held]:
                yield f"{section}.{field}", an_object(alternative)


# ── Each example is a record ───────────────────────────────────────────────────────────────────────────


def record_problems(record: JsonObject) -> list[str]:
    """What the writer and reader schemas, the envelope checks and the content hash refuse in `record`, and
    the record checks it can be given alone that a reader of this release can make without `materica check`:
    its namespace (`example`), each field's required conditions (RC-006), its label (RC-122: the label its
    row names for its form and no other, and beside it a `label_basis`, whose shape the writer schema checks),
    and every review unset, as an example's is. A structure the reader schema refuses is walked no further.
    Left to `materica check`, and so not made here: RC-020, RC-037, RC-043, RC-045, RC-051, RC-052 and
    RC-058 (the plasma record breaks RC-058, open point 7 of the pull request).

    A malformed identifier or version (RC-012 to RC-014) is refused by the schemas and the envelope checks,
    which return first; a reserved namespace is not `example`, so the one namespace check refuses it too."""
    problems = [f"writer schema: {message}" for message in WRITER(record)]
    structure = [f"reader schema: {message}" for message in READER(record)]
    structure += [f"envelope: {problem}" for problem in envelope_problems(record)]
    if structure:
        return problems + structure
    if record["content_hash"] != (computed := content_hash(record)):
        problems.append(f"content_hash: stated {record['content_hash']}, computed {computed}")
    identifier = str(record["id"])
    if identifier.partition("/")[0] != "example":
        problems.append(f"id: {identifier!r} is not in the namespace example")
    for name, field in value_fields(record):
        spec = VOCABULARY.fields[name]
        conditions = an_object(field["conditions"])
        problems += [f"{name}: no {condition}" for condition in spec.requires if condition not in conditions]
        named = spec.label if label_allowed(spec, str(field["form"]), field) else None
        if field.get("label") != named:
            problems.append(f"{name}: label {field.get('label')!r}, not {named!r}")
        elif named is not None and "label_basis" not in field:
            problems.append(f"{name}: label {named!r} without label_basis")
        review = an_object(an_object(field["provenance"])["review"])
        if review.get("status") != "not_checked":
            problems.append(f"{name}: review {review}")
    return problems


@pytest.mark.parametrize("name", FILES)
def test_each_example_is_a_record(name: str) -> None:
    assert record_problems(example(name)) == []


def rehashed(record: JsonObject) -> JsonObject:
    record["content_hash"] = content_hash(record)
    return record


def change(path: Path_, value: JsonValue) -> Callable[[JsonObject], None]:
    def changed(record: JsonObject) -> None:
        an_object(at(record, path[:-1]))[str(path[-1])] = value

    return changed


def drop(path: Path_) -> Callable[[JsonObject], None]:
    def dropped(record: JsonObject) -> None:
        del an_object(at(record, path[:-1]))[str(path[-1])]

    return dropped


DENSITY_0: Path_ = ("body", "sections", "bulk", "fields", "density", "alternatives", 0)
VISCOSITY_1: Path_ = ("body", "sections", "fluid", "fields", "dynamic_viscosity", "alternatives", 1)


def tabled(axis: str, unit: str) -> Callable[[JsonObject], None]:
    """The second viscosity alternative made a table along `axis`, its label kept: the row lets the label go
    on a table whose axis is not `shear_rate` and on no other (`record_format.md` section 4.1)."""

    def made(record: JsonObject) -> None:
        field = an_object(at(record, VISCOSITY_1))
        del field["value"]
        field["form"] = "table"
        field["table"] = {
            "axis": axis,
            "axis_unit": unit,
            "x": [300.0, 320.0],
            "y": [0.00085, 0.00058],
            "scheme": "linear",
            "edges": [],
        }
        an_object(field["conditions"])[axis] = {"status": "not_applicable"}

    return made


@pytest.mark.parametrize(
    ("fault", "rehash", "found"),
    [
        (change((*DENSITY_0, "statistics", "dispersion"), "maybe"), True, "writer schema"),
        (change(("body", "sections"), []), True, "reader schema"),
        (change((*DENSITY_0, "value"), 998.208), False, "content_hash"),
        (change(("id",), "materica/water"), True, "namespace example"),
        (change(("id",), "example/Water Space"), True, "envelope: id"),
        (change(("version",), "0.1"), True, "envelope: version"),
        (drop((*DENSITY_0, "conditions", "density_kind")), True, "bulk.density: no density_kind"),
        (drop((*VISCOSITY_1, "label")), True, "fluid.dynamic_viscosity: label None"),
        (
            change((*DENSITY_0, "label"), "materica.fluid.newtonian.v1"),
            True,
            "bulk.density: label 'materica.fluid.newtonian.v1', not None",
        ),
        (
            drop((*VISCOSITY_1, "label_basis")),
            True,
            "fluid.dynamic_viscosity: label 'materica.fluid.newtonian.v1' without label_basis",
        ),
        (
            tabled("shear_rate", "1/s"),
            True,
            "fluid.dynamic_viscosity: label 'materica.fluid.newtonian.v1', not None",
        ),
        (change((*VISCOSITY_1, "label_basis"), {"basis": "inferred"}), True, "writer schema"),
        (
            change((*VISCOSITY_1, "provenance", "review"), {"status": "not_checked_yet"}),
            True,
            "fluid.dynamic_viscosity: review",
        ),
    ],
    ids=[
        "writer",
        "reader",
        "hash",
        "namespace",
        "id",
        "version",
        "required-condition",
        "label",
        "label-not-named",
        "label-basis",
        "label-on-its-axis",
        "label-basis-shape",
        "review",
    ],
)
def test_the_record_check_can_fail(fault: Callable[[JsonObject], None], rehash: bool, found: str) -> None:
    record = copy.deepcopy(example("water.json"))
    fault(record)
    problems = record_problems(rehashed(record) if rehash else record)
    assert any(found in problem for problem in problems), problems


def test_the_label_check_takes_a_table_on_another_axis() -> None:
    """The control `label-on-its-axis` beside its counterpart: a labelled table along temperature passes the
    label check, so a check that took the label on constants alone would fail here."""
    record = copy.deepcopy(example("water.json"))
    tabled("temperature", "K")(record)
    problems = record_problems(rehashed(record))
    assert not any(problem.startswith(("reader schema", "envelope")) for problem in problems), problems
    assert not any(problem.startswith("fluid.dynamic_viscosity: label") for problem in problems), problems


def test_the_label_check_reaches_a_field_without_alternatives() -> None:
    record = copy.deepcopy(example("human_plasma.json"))
    drop(("body", "sections", "fluid", "fields", "dynamic_viscosity", "label_basis"))(record)
    problems = record_problems(rehashed(record))
    assert "fluid.dynamic_viscosity: label 'materica.fluid.newtonian.v1' without label_basis" in problems, (
        problems
    )


# ── Each number is its source's ────────────────────────────────────────────────────────────────────────

CONVERSIONS: dict[str, Callable[[Decimal], Decimal]] = {
    "as stated": lambda number: number,
    "mPa·s to Pa·s": lambda number: number / 1000,
    "% to 1": lambda number: number / 100,
    "°C to K": lambda number: number + Decimal("273.15"),
    "years to s, the Julian year": lambda number: number * 31557600,
}


@dataclass(frozen=True)
class Stated:
    """A number as its source states it, the conversion that gives the stored number, and the source with the
    place in it. `path` runs from the record's `sections`."""

    file: str
    path: Path_
    stated: str
    conversion: str
    source: str


WATER_DENSITY = "IAPWS R6-95(2018), evaluated at {} K and 0.101325 MPa, liquid, to 6 significant digits"
WATER_VISCOSITY = "IAPWS R12-08, evaluated at {} K and 0.101325 MPa, liquid, to 6 significant digits"
R12_UNCERTAINTY = "IAPWS R12-08 section 2.5, p. 4: an expanded uncertainty with 'a coverage factor of two'"
N45 = (
    "supermagnete.de, 'Physical Magnet Data', grade N45, 'Residual magnetism Br', Tesla (T): '1.32-1.37'; "
    "the same on the data sheet of article W-01-N, p. 1 (accessed 2026-10-17)"
)
PLASMA = "Marcinkowska-Gapinska and Nawrocka-Bogusz 2013, doi:10.1155/2013/490410, {}"
PLASMA_TABLE = PLASMA.format("Table 1, 'Plasma viscosity', 'Before magnetic field (n = 25)': '1.33 ± 0.03*'")
DENSITY: Path_ = ("bulk", "fields", "density", "alternatives")
VISCOSITY: Path_ = ("fluid", "fields", "dynamic_viscosity", "alternatives")
REMANENCE: Path_ = ("magnetic", "fields", "remanence")
PLASMA_FIELD: Path_ = ("fluid", "fields", "dynamic_viscosity")
PLASMA_SPECIMEN: Path_ = ("fluid", "specimen")

# The numbers of the example records, as their sources give them: the water's evaluated, the others' read from
# the documents named, as they were read for these examples on 2026-10-17 and 2026-10-18 and accepted by the
# maintainer pending a detailed check.
STATED = (
    Stated("water.json", (*DENSITY, 0, "value"), "998.207", "as stated", WATER_DENSITY.format(293.15)),
    Stated(
        "water.json", (*DENSITY, 0, "conditions", "temperature", "value"), "293.15", "as stated", "the state"
    ),
    Stated("water.json", (*DENSITY, 1, "value"), "993.330", "as stated", WATER_DENSITY.format(310.15)),
    Stated(
        "water.json", (*DENSITY, 1, "conditions", "temperature", "value"), "310.15", "as stated", "the state"
    ),
    Stated("water.json", (*VISCOSITY, 0, "value"), "0.00100160", "as stated", WATER_VISCOSITY.format(293.15)),
    Stated(
        "water.json",
        (*VISCOSITY, 0, "conditions", "temperature", "value"),
        "293.15",
        "as stated",
        "the state",
    ),
    Stated(
        "water.json",
        (*VISCOSITY, 0, "statistics", "relative_uncertainty", "value"),
        "0.17",
        "% to 1",
        "IAPWS R12-08 section 2.5, p. 4: 'the stated uncertainty of 0.17 % at 293.15 K'",
    ),
    Stated(
        "water.json",
        (*VISCOSITY, 0, "statistics", "relative_uncertainty", "coverage_factor"),
        "2",
        "as stated",
        R12_UNCERTAINTY,
    ),
    Stated(
        "water.json", (*VISCOSITY, 1, "value"), "0.000691304", "as stated", WATER_VISCOSITY.format(310.15)
    ),
    Stated(
        "water.json",
        (*VISCOSITY, 1, "conditions", "temperature", "value"),
        "310.15",
        "as stated",
        "the state",
    ),
    Stated(
        "water.json",
        (*VISCOSITY, 1, "statistics", "relative_uncertainty", "value"),
        "1",
        "% to 1",
        "IAPWS R12-08 Fig. 1, p. 4, read from the graphic: '1%' over 273.15 K to about 573 K",
    ),
    Stated(
        "water.json",
        (*VISCOSITY, 1, "statistics", "relative_uncertainty", "coverage_factor"),
        "2",
        "as stated",
        R12_UNCERTAINTY,
    ),
    Stated(
        "water.json",
        (*DENSITY, 0, "provenance", "formulation", "inputs", "pressure", "value"),
        "0.101325",
        "as stated",
        "the state, in MPa",
    ),
    Stated("ndfeb_n45.json", (*REMANENCE, "interval", "lower"), "1.32", "as stated", N45),
    Stated("ndfeb_n45.json", (*REMANENCE, "interval", "upper"), "1.37", "as stated", N45),
    Stated("human_plasma.json", (*PLASMA_FIELD, "value"), "1.33", "mPa·s to Pa·s", PLASMA_TABLE),
    Stated("human_plasma.json", (*PLASMA_FIELD, "statistics", "mean"), "1.33", "mPa·s to Pa·s", PLASMA_TABLE),
    Stated(
        "human_plasma.json",
        (*PLASMA_FIELD, "statistics", "n_specimens"),
        "25",
        "as stated",
        PLASMA.format("Table 1, 'Before magnetic field (n = 25)'"),
    ),
    Stated(
        "human_plasma.json",
        (*PLASMA_FIELD, "statistics", "n_donors"),
        "25",
        "as stated",
        PLASMA.format("section 2: 'a group of 25 healthy nonsmoking patients'"),
    ),
    Stated(
        "human_plasma.json",
        (*PLASMA_FIELD, "conditions", "temperature", "value"),
        "37",
        "°C to K",
        PLASMA.format("section 2: 'at the temperature of 37°C'"),
    ),
    *(
        Stated(
            "human_plasma.json",
            (*PLASMA_FIELD, "conditions", "shear_rate", "range", index),
            stated,
            "as stated",
            PLASMA.format("section 2: a regression over shear rates 'in the range of' 10 to 100 per second"),
        )
        for index, stated in enumerate(("10", "100"))
    ),
    *(
        Stated(
            "human_plasma.json",
            (*PLASMA_SPECIMEN, "donor_age", "range", index),
            stated,
            "years to s, the Julian year",
            PLASMA.format("section 2: 'aged 21 to 51'"),
        )
        for index, stated in enumerate(("21", "51"))
    ),
    Stated(
        "human_plasma.json",
        (*PLASMA_SPECIMEN, "species", "ncbi_taxon"),
        "9606",
        "as stated",
        "NCBI Taxonomy: Homo sapiens, the paper's 'healthy persons'",
    ),
)


@dataclass(frozen=True)
class InWords:
    """What a source states that schema 0.1.0 has no member for, in the words a record keeps it in."""

    file: str
    path: Path_
    phrase: str
    source: str


IN_WORDS = (
    InWords(
        "human_plasma.json",
        (*PLASMA_FIELD, "statistics", "sd", "reason"),
        "'1.33 ± 0.03' mPa·s",
        PLASMA_TABLE,
    ),
    InWords(
        "human_plasma.json",
        (*PLASMA_FIELD, "statistics", "represents", "reason"),
        "± 0.03 mPa·s",
        PLASMA_TABLE,
    ),
    InWords(
        "ndfeb_n45.json",
        (*REMANENCE, "conditions", "temperature", "reason"),
        "'apply at room temperature'",
        "supermagnete.de, 'Physical Magnet Data': 'are reference points and apply at room temperature'",
    ),
    *(
        InWords(
            "water.json",
            (*DENSITY, index, "statistics", "relative_uncertainty", "reason"),
            "a tolerance of 0.0001 %",
            "IAPWS R6-95(2018) section 6, p. 6, and Fig. 1, p. 16",
        )
        for index in (0, 1)
    ),
)


def numbers(value: JsonValue, path: Path_ = ()) -> Iterator[tuple[Path_, float]]:
    """Each number in `value` outside a provenance object, with its path."""
    if isinstance(value, dict):
        for name, member in value.items():
            if name != "provenance":
                yield from numbers(member, (*path, name))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from numbers(item, (*path, index))
    elif isinstance(value, float):
        yield path, value


def source_problems(
    records: Mapping[str, JsonObject], stated: Sequence[Stated], in_words: Sequence[InWords]
) -> list[str]:
    """Each number of `stated` a record does not hold as its conversion gives it, each phrase of `in_words` it
    does not hold, and each number of a record outside its provenance that `stated` gives no source for."""
    problems: list[str] = []
    for row in stated:
        expected = float(CONVERSIONS[row.conversion](Decimal(row.stated)))
        try:
            found = at(sections(records[row.file]), row.path)
        except (KeyError, IndexError, TypeError):
            problems.append(f"{row.file} {row.path}: absent, where {row.source} gives {row.stated}")
            continue
        if found != expected or not isinstance(found, float):
            problems.append(f"{row.file} {row.path}: {found!r}, where {row.source} gives {row.stated}")
    for words in in_words:
        try:
            text = at(sections(records[words.file]), words.path)
        except (KeyError, IndexError, TypeError):
            text = None
        if not isinstance(text, str) or words.phrase not in text:
            problems.append(f"{words.file} {words.path}: {text!r} does not say {words.phrase!r}")
    sourced = {(row.file, row.path) for row in stated}
    for file, record in records.items():
        problems += [
            f"{file} {path}: {number!r}, with no source given"
            for path, number in numbers(sections(record))
            if (file, path) not in sourced
        ]
    return problems


def examples() -> dict[str, JsonObject]:
    return {name: example(name) for name in FILES}


def test_each_number_is_its_sources() -> None:
    assert source_problems(examples(), STATED, IN_WORDS) == []


def in_sections(path: Path_) -> Path_:
    return ("body", "sections", *path)


@pytest.mark.parametrize(
    ("file", "fault", "found"),
    [
        (
            "water.json",
            change(in_sections((*DENSITY, 0, "value")), 998.208),
            "998.208, where IAPWS R6-95(2018)",
        ),
        (
            "ndfeb_n45.json",
            change(in_sections((*REMANENCE, "interval", "upper")), 1.38),
            "1.38, where supermag",
        ),
        (
            "human_plasma.json",
            change(in_sections((*PLASMA_FIELD, "value")), 1.33),
            "1.33, where Marcinkowska",
        ),
        (
            "human_plasma.json",
            change(in_sections((*PLASMA_FIELD, "statistics", "min")), 0.0012),
            "'min'): 0.0012, with no source given",
        ),
        (
            "human_plasma.json",
            change(in_sections((*PLASMA_FIELD, "statistics", "sd")), {"status": "unstated"}),
            "does not say \"'1.33 ± 0.03' mPa·s\"",
        ),
        (
            "human_plasma.json",
            drop(in_sections((*PLASMA_SPECIMEN, "donor_age"))),
            "'donor_age', 'range', 0): absent",
        ),
    ],
    ids=["water", "n45", "plasma-unit", "unsourced", "in-words", "absent"],
)
def test_the_source_check_can_fail(file: str, fault: Callable[[JsonObject], None], found: str) -> None:
    records = examples()
    fault(records[file])
    problems = source_problems(records, STATED, IN_WORDS)
    assert any(found in problem for problem in problems), problems


# ── The note stands wherever the examples are documented ──────────────────────────────────────────────


def plain(text: str) -> str:
    """Markdown or prose as words: each line's blockquote marker dropped, each run of white space one
    space."""
    return " ".join(re.sub(r"(?m)^[ \t]*>[ \t]?", "", text).split())


def missing_note(text: str) -> list[str]:
    """The phrases of the note `text` lacks, compared without regard to case."""
    words = plain(text).casefold()
    return [phrase for phrase in NOTE if phrase not in words]


@pytest.mark.parametrize("path", DOCUMENTED, ids=lambda path: path.relative_to(REPOSITORY).as_posix())
def test_the_documentation_says_the_examples_are_not_yet_fully_reviewed(path: Path) -> None:
    assert missing_note(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("name", FILES)
def test_each_example_says_so_in_its_card(name: str) -> None:
    assert missing_note(str(example(name)["card"])) == []


@pytest.mark.parametrize("path", DOCUMENTED, ids=lambda path: path.relative_to(REPOSITORY).as_posix())
def test_the_note_check_fails_where_the_note_is_removed(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    without = "\n".join(line for line in text.splitlines() if "human-reviewed" not in line)
    assert without != text
    assert "not yet fully human-reviewed" in missing_note(without)


# ── What a read of each example gives at this release ─────────────────────────────────────────────────


def request(
    record: JsonObject, field: str, operating: JsonObject, conditions: JsonObject, want: str = "value"
) -> JsonObject:
    pin: JsonObject = {name: record[name] for name in ("id", "version", "content_hash")}
    return {
        "target": {"record": pin, "field": field},
        "operating_conditions": operating,
        "requirement": {"want": want, "conditions": conditions},
    }


def kelvin(value: float, tolerance: float) -> tuple[JsonObject, JsonObject]:
    return {"value": value, "unit": "K"}, {"tolerance": {"value": tolerance, "unit": "K"}}


STORE = load_records(sorted(RECORDS.glob("*.json")))
# Each water value is evaluated from a formulation and states so (`provenance.md` section 6.1 item 10), so a
# request for one accepts that method; one that names none leaves it `condition_unchecked`.
FORMULATION: JsonObject = {"test_method": {"accept": ["reference_formulation"]}}


def test_the_plasma_example_reads_met() -> None:
    record = example("human_plasma.json")
    operating, tolerance = kelvin(310.15, 0.5)
    result = read(
        request(
            record,
            "fluid.dynamic_viscosity",
            {"temperature": operating, "shear_rate": {"range": [10.0, 100.0], "unit": "1/s"}},
            {
                "temperature": tolerance,
                "shear_rate": {"tolerance": {"value": 0.0, "unit": "1/s"}},
                "test_method": {"accept": ["rotational_rheometer"]},
            },
        ),
        STORE,
    )
    assert (result.status, result.reasons, result.value) == ("met", (), 0.00133)
    assert result.labels == ("materica.fluid.newtonian.v1",)


def test_the_water_example_gives_no_pick_where_both_alternatives_meet() -> None:
    operating, tolerance = kelvin(300.0, 20.0)
    result = read(
        request(
            example("water.json"),
            "bulk.density",
            {"temperature": operating},
            {"temperature": tolerance, "density_kind": {"accept": ["apparent"]}, **FORMULATION},
        ),
        STORE,
    )
    assert (result.status, [reason.code for reason in result.reasons]) == ("unknown", ["no_pick"])
    assert [alternative.value for alternative in result.alternative_values or ()] == [998.207, 993.33]


@pytest.mark.parametrize(("temperature", "value"), [(293.15, 998.207), (310.15, 993.33)])
def test_the_water_density_at_one_temperature_is_the_one_alternative_left(
    temperature: float, value: float
) -> None:
    """The other temperature is outside the tolerance, so its alternative is set aside and the one left is
    read (`read_side_contract.md` section 3, step 7): `met`, its value, and no reason of the set-aside one."""
    operating, tolerance = kelvin(temperature, 0.5)
    result = read(
        request(
            example("water.json"),
            "bulk.density",
            {"temperature": operating},
            {"temperature": tolerance, "density_kind": {"accept": ["apparent"]}, **FORMULATION},
        ),
        STORE,
    )
    assert (result.status, result.reasons, result.value) == ("met", (), value)
    assert result.alternative_values is None


@pytest.mark.parametrize(("temperature", "left", "value"), [(293.15, 0, 0.0010016), (310.15, 1, 0.000691304)])
def test_the_water_viscosity_at_one_temperature_is_the_one_left_its_shear_rate_unstated(
    temperature: float, left: int, value: float
) -> None:
    """Each viscosity alternative states no shear rate, which its row requires: the one left is read,
    `unknown` (`condition_unstated`, carrying its index), for a consumer's declaration to waive."""
    operating, tolerance = kelvin(temperature, 0.5)
    result = read(
        request(
            example("water.json"),
            "fluid.dynamic_viscosity",
            {"temperature": operating},
            {"temperature": tolerance, **FORMULATION},
        ),
        STORE,
    )
    assert (result.status, result.reasons, result.value) == (
        "unknown",
        (Reason("condition_unstated", "shear_rate", alternative=left),),
        value,
    )


def test_the_water_viscosity_where_both_alternatives_meet_gives_no_pick() -> None:
    """Where both alternatives stay, each one's `unknown` reasons stand beside `no_pick`
    (`read_side_contract.md` section 3, step 7)."""
    operating, tolerance = kelvin(300.0, 20.0)
    result = read(
        request(
            example("water.json"),
            "fluid.dynamic_viscosity",
            {"temperature": operating},
            {"temperature": tolerance, **FORMULATION},
        ),
        STORE,
    )
    assert (result.status, set(result.reasons)) == (
        "unknown",
        {
            Reason("no_pick"),
            Reason("condition_unstated", "shear_rate", alternative=0),
            Reason("condition_unstated", "shear_rate", alternative=1),
        },
    )
    assert [alternative.value for alternative in result.alternative_values or ()] == [0.0010016, 0.000691304]


def test_a_water_read_that_names_no_test_method_leaves_the_stated_one_unchecked() -> None:
    """The density states its test method, so a request that names none reads it `unknown`
    (`condition_unchecked`, `read_side_contract.md` section 5), the value carried."""
    operating, tolerance = kelvin(293.15, 0.5)
    result = read(
        request(
            example("water.json"),
            "bulk.density",
            {"temperature": operating},
            {"temperature": tolerance, "density_kind": {"accept": ["apparent"]}},
        ),
        STORE,
    )
    assert (result.status, result.reasons, result.value) == (
        "unknown",
        (Reason("condition_unchecked", "test_method", alternative=0),),
        998.207,
    )


@pytest.mark.parametrize(
    ("field", "own"),
    [
        ("bulk.density", {"density_kind": {"accept": ["apparent"]}}),
        ("fluid.dynamic_viscosity", {}),
    ],
)
def test_the_water_values_are_accepted_by_their_stated_method_and_by_no_measured_one(
    field: str, own: JsonObject
) -> None:
    """A consumer that accepts only measuring methods refuses each alternative (`condition_not_accepted`),
    and one that accepts `reference_formulation` meets the method (`provenance.md` section 6.1 item 10)."""
    operating, tolerance = kelvin(293.15, 0.5)
    measured: JsonObject = {
        "test_method": {"accept": ["rotational_rheometer", "capillary_viscometer", "pycnometer"]}
    }
    results = {
        accepted: read(
            request(
                example("water.json"),
                field,
                {"temperature": operating},
                {"temperature": tolerance, **own, **by},
            ),
            STORE,
        )
        for accepted, by in (("formulation", FORMULATION), ("measured", measured))
    }
    entries = {entry.name: entry.status for entry in results["formulation"].conditions or ()}
    assert entries["test_method"] == "met"
    refused = results["measured"]
    assert (refused.status, refused.value) == ("not_met", None)
    assert {reason for reason in refused.reasons if reason.condition == "test_method"} == {
        Reason("condition_not_accepted", "test_method", alternative=0),
        Reason("condition_not_accepted", "test_method", alternative=1),
    }


def test_an_accept_list_holding_reference_formulation_accepts_no_other_method_and_no_absent_one() -> None:
    """The plasma's viscosity, measured, is met where its test method is accepted, and reads `unknown`
    (`condition_unstated`) once its method is removed, whatever methods the request accepts: an accept list
    holding `reference_formulation` accepts no value that states no method. One holding that token alone
    refuses the plasma's stated method (`condition_not_accepted`, `read_side_contract.md` section 5)."""
    operating, tolerance = kelvin(310.15, 0.5)
    both: JsonObject = {"test_method": {"accept": ["rotational_rheometer", "reference_formulation"]}}
    formulation_alone: JsonObject = {"test_method": {"accept": ["reference_formulation"]}}
    plasma = example("human_plasma.json")
    without = copy.deepcopy(plasma)
    drop(("body", "sections", "fluid", "fields", "dynamic_viscosity", "conditions", "test_method"))(without)
    rehashed(without)
    statuses: list[tuple[str, tuple[Reason, ...]]] = []
    for record, accepted in ((plasma, both), (without, both), (plasma, formulation_alone)):
        store = RecordStore()
        store.add("plasma.json", json.dumps(record).encode("utf-8"))
        result = read(
            request(
                record,
                "fluid.dynamic_viscosity",
                {"temperature": operating, "shear_rate": {"range": [10.0, 100.0], "unit": "1/s"}},
                {
                    "temperature": tolerance,
                    "shear_rate": {"tolerance": {"value": 0.0, "unit": "1/s"}},
                    **accepted,
                },
            ),
            store,
        )
        statuses.append((result.status, result.reasons))
    assert statuses == [
        ("met", ()),
        ("unknown", (Reason("condition_unstated", "test_method"),)),
        ("not_met", (Reason("condition_not_accepted", "test_method"),)),
    ]


N45_UNKNOWN_REASONS = [
    ("condition_unstated", "temperature"),
    ("condition_unstated", "specimen_shape"),
    ("condition_unstated", "test_method"),
    ("stated_without_origin", None),
]


def n45(want: str) -> ReadResult:
    return read(request(example("ndfeb_n45.json"), "magnetic.remanence", {}, {}, want), STORE)


def test_the_n45_example_gives_its_bounds_as_unknown() -> None:
    """An interval is read since S2b-1: `want: bounds` returns the limits as stored (PR-022). The status is
    `unknown` for the three conditions the vendor leaves unstated and for the origin (section 2 item 4)."""
    result = n45("bounds")
    assert result.status == "unknown"
    assert [(reason.code, reason.condition) for reason in result.reasons] == N45_UNKNOWN_REASONS
    assert result.value == {"lower": 1.32, "upper": 1.37, "basis": "specification_limits"}
    assert result.unit == "T"


def test_the_n45_example_gives_no_value_as_not_met() -> None:
    """`want: value` on an interval is `want_mismatch` (PR-338); with no nominal declared the result holds no
    value, and the `unknown` reasons found before step 13 stand beside it (section 2 item 2)."""
    result = n45("value")
    assert result.status == "not_met"
    assert [(reason.code, reason.condition) for reason in result.reasons] == [
        *N45_UNKNOWN_REASONS,
        ("want_mismatch", None),
    ]
    assert result.value is None
    assert result.assumption is None
