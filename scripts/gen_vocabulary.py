# SPDX-License-Identifier: Apache-2.0
"""Generate `src/materica/schema/0.1/vocabulary/*.json` from the tables and token lists of the specification.

    python scripts/gen_vocabulary.py            # write the files
    python scripts/gen_vocabulary.py --check    # fail if a file differs from what the specification gives

Tokens live in the specification and structure in the writer schemas (CONTRIBUTING, "Changing the schema"), so
each file holds tokens and none of the prose around them: a rule written in prose (when a field's label
applies) is code with its own cases. Most tokens sit in tables; the rest sit in lists in a table cell or a
sentence (`a`, `b` or `c`), each found after a quoted piece of text that must occur exactly once, up to the
quoted text that ends it. A cell or a list not of the form expected stops the script, and so does a name
listed twice in one table; every list of tokens is read in full or not at all: the specification is the
source, and a change to it must change a file or fail here, never drop a token. A parenthetical in a list is
prose and is read as none of its tokens; in a table cell of tokens, a code span inside one stops the script.
`coverage.json` is the one file of a rule: `declarations.md` section 4.2's table of what covers which reason,
each "Covered by" cell read by a fixed table of the phrasings it uses (`COVERED_BY`), a phrasing not in it
stopping the script.
"""

import json
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NamedTuple

REPOSITORY = Path(__file__).resolve().parents[1]
SPECIFICATION = REPOSITORY / "docs" / "specification"
VOCABULARY = REPOSITORY / "src" / "materica" / "schema" / "0.1" / "vocabulary"
# Where the files are published: each file's `$id` is this and its name (`tests/spec_sync/test_schemas.py`).
VOCABULARY_ID = "https://w3id.org/materica/schema/0.1/vocabulary/"

Row = dict[str, str]
Vocabulary = dict[str, object]
# A document of the specification by its file name, as text.
Documents = Callable[[str], str]

_CODE = re.compile(r"`([^`]+)`")
_TOKEN = re.compile(r"[a-z0-9_]+")
_CODE_LIST = re.compile(r"`[a-z0-9_]+`(?:, `[a-z0-9_]+`)*")
# Tokens joined as prose joins them: `a`, `b` or `c`; `a`, `b`, and `c`; `a`, or `b`.
_PROSE_LIST = re.compile(r"`[a-z0-9_]+`(?:(?:,| or|, or| and|, and) `[a-z0-9_]+`)*")
# A specimen fact's `token` member, as the JSON shape writes it: `"token": "a" | "b"`, up to the next member.
_TOKEN_MEMBER = re.compile(r'"token": ("[a-z0-9_]+"(?: \| "[a-z0-9_]+")*)(?=, |\})')
# Any member a specimen fact's JSON shape writes with a value, and a quoted value up to the next member.
_MEMBER_VALUE = re.compile(r'"([a-z_]+)": ')
_QUOTED = re.compile(r'"([^"]*)"(?=, |\})')
# An ontology identifier as a fact's shape writes it, `"UBERON:<digits>"`: capitals, a colon, then digits.
_IDENTIFIER = re.compile(r"([A-Z]+):<digits>")
_SYMBOLS = re.compile(r"`[A-Z][a-z]?`(?: `[A-Z][a-z]?`)*")
# A family identifier (`record_format.md` section 7 item 3), the form a label takes.
_LABEL = re.compile(r"[a-z0-9_]+(?:\.[a-z0-9_]+)+\.v[1-9][0-9]*")
# A field's Label cell: the label's code span, then ` on ` and the prose saying where it applies.
_LABEL_CELL = re.compile(r"`([^`]+)` on ([^`]*(?:`[^`]*`[^`]*)*)")
# Where a label applies, after ` on `: a constant, and perhaps a table whose axis is not a given condition.
_LABEL_ON = re.compile(r"a constant(?:, or on a table whose axis is not `([a-z0-9_]+)`)?")
# A numeric condition's cell: its unit's code span alone, or followed by a parenthetical or `: ` and prose.
_UNIT_CELL = re.compile(r"`([^`]+)`(?: \([^`()]*\)|: [^`]*)?")
# A field's name in section 4.1's table, `<section>.<field>`.
_QUALIFIED = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+")
# The procedures section 4's `Step` column names for a code no step of the read gives (its paragraph above).
PROCEDURES = ("scene", "USD read", "engine adapter", "build", "family evaluation", "mixing")
# The steps of `read_side_contract.md` section 3.
STEPS = range(14)


class TableError(ValueError):
    """A table, one of its cells, or a list of tokens, not of the form this script reads."""


def table(document: str, heading: str) -> list[Row]:
    """The first table below the line `heading`, a row per dict keyed by the column headers."""
    lines = document.splitlines()
    if heading not in lines:
        raise TableError(f"no heading {heading!r}")
    rows: list[list[str]] = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("|"):
            rows.append(cells(line))
        elif rows or line.startswith("#"):
            break
    if len(rows) < 3:
        raise TableError(f"no table with rows below {heading!r}")
    header, _, *body = rows
    if any(len(row) != len(header) for row in body):
        raise TableError(f"a row below {heading!r} has another number of cells than its header")
    return [dict(zip(header, row, strict=True)) for row in body]


def cells(line: str) -> list[str]:
    """A table row's cells, with a pipe escaped inside one (`\\|`) unescaped."""
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def codes(cell: str) -> list[str]:
    return _CODE.findall(cell)


def only_code(cell: str) -> str:
    if not re.fullmatch(r"`[^`]+`", cell):
        raise TableError(f"expected one code span, got {cell!r}")
    return cell[1:-1]


def code_list(text: str, cell: str) -> list[str]:
    """The tokens of `text`, which must be code spans and nothing else: `a`, `b`."""
    if not _CODE_LIST.fullmatch(text):
        raise TableError(f"expected a list of code spans in {cell!r}")
    return codes(text)


def outside_parentheses(cell: str) -> str:
    """`cell` without its parentheticals, each of which must hold no code span: a token there would be
    dropped."""
    if any("`" in aside for aside in re.findall(r"\([^)]*\)", cell)):
        raise TableError(f"a code span inside a parenthetical in {cell!r}")
    return re.sub(r"\s*\([^)]*\)", "", cell)


def without_asides(text: str) -> str:
    """`text` without its parentheticals, nested ones included, and its case tags (`[PR-333]`). A
    parenthetical is prose: a code span inside one is no token of the list around it."""
    text = re.sub(r"\s*\[(?:[A-Z]{2}-\d{3}|not yet covered)\]", "", text)
    while True:
        shorter = re.sub(r"\s*\([^()]*\)", "", text)
        if shorter == text:
            return text
        text = shorter


def prose(document: str) -> str:
    """`document` with each run of whitespace one space, so that a sentence reads the same however wrapped."""
    return re.sub(r"\s+", " ", document)


def once(text: str, piece: str) -> int:
    """Where `piece` starts in `text`, which must hold it exactly once."""
    if text.count(piece) != 1:
        raise TableError(f"expected {piece!r} exactly once, found it {text.count(piece)} times")
    return text.index(piece)


def between(text: str, after: str | None, before: str | None) -> str:
    """The text between `after`, which must occur once, and the first `before` that follows it; from the
    start, or to the end, where either is None."""
    start = 0 if after is None else once(text, after) + len(after)
    end = len(text) if before is None else text.find(before, start)
    if end < 0:
        raise TableError(f"no {before!r} after {after!r}")
    return text[start:end]


def listed(text: str, after: str | None, before: str | None) -> list[str]:
    """The tokens of the list between `after` and `before` in `text` (`between`): code spans joined by
    commas, `or` and `and`, each perhaps followed by a parenthetical or a case tag, and nothing else."""
    found = without_asides(between(text, after, before)).strip()
    if not _PROSE_LIST.fullmatch(found):
        raise TableError(f"expected a list of tokens after {after!r}, got {found!r}")
    return codes(found)


def cell_of(rows: list[Row], member: str, column: str = "Contents") -> str:
    """The cell in `column` of the row whose first cell is the code span `member`."""
    found = [row[column] for row in rows if next(iter(row.values())) == f"`{member}`"]
    if len(found) != 1:
        raise TableError(f"expected one row for `{member}`, found {len(found)}")
    return found[0]


def enumeration(found: list[str]) -> dict[str, object]:
    if len(set(found)) != len(found):
        raise TableError(f"a token is listed twice in {found!r}")
    return {"enum": found}


def names(rows: list[Row], column: str) -> list[str]:
    """The code span of each row's `column`, a name each row gives once: a second row would replace the
    first's."""
    found = [only_code(row[column]) for row in rows]
    if repeated := sorted({name for name in found if found.count(name) > 1}):
        raise TableError(f"a name listed twice in the table: {repeated}")
    return found


def reasons(rows: list[Row]) -> Vocabulary:
    statuses: dict[str, object] = {}
    for code, row in zip(names(rows, "Code"), rows, strict=True):
        if row["Status"] not in ("met", "not_met", "unknown"):
            raise TableError(f"not a read status: {row['Status']!r}")
        statuses[code] = {"status": row["Status"], **given_by(row["Step"])}
    return {"$defs": {"reason_code": {"enum": list(statuses)}}, "reasons": statuses}


def given_by(cell: str) -> dict[str, object]:
    """The steps of section 3 that give a code, or the procedures that give one no step gives."""
    named = cell.split(", ")
    if all(re.fullmatch(r"0|[1-9][0-9]*", step) and int(step) in STEPS for step in named):
        return {"steps": [int(step) for step in named]}
    if all(procedure in PROCEDURES for procedure in named):
        return {"procedures": named}
    raise TableError(f"expected steps of section 3, or procedures, in {cell!r}")


class FieldRow(NamedTuple):
    """A row of `record_format.md` section 4.1, as read: its unit (a code, or a status object), its forms, the
    bases it allows a form, the conditions it requires, its label, if any, and the condition a table's axis
    must not be for the label to go on it, where the label goes on a table at all."""

    unit: str | dict[str, str]
    forms: list[str]
    bases: dict[str, list[str]]
    requires: list[str]
    label: str | None
    label_not_on_axis: str | None


def fields(rows: list[Row]) -> Vocabulary:
    read: dict[str, FieldRow] = {}
    for name, row in zip(names(rows, "Section.field"), rows, strict=True):
        if not _QUALIFIED.fullmatch(name):
            raise TableError(f"expected <section>.<field>, got {name!r}")
        forms, bases = field_forms(row["Forms"])
        labelled = row["Label"] != "none"
        read[name] = FieldRow(
            field_unit(name, only_code(row["Unit"])),
            forms,
            bases,
            [] if row["Requires"] == "none" else code_list(row["Requires"], row["Requires"]),
            field_label(row["Label"]) if labelled else None,
            label_not_on_axis(row["Label"]) if labelled else None,
        )
    entries: dict[str, object] = {}
    for name, field in read.items():
        entry: dict[str, object] = {"unit": field.unit, "forms": field.forms, "requires": field.requires}
        if field.bases:
            entry["bases"] = field.bases
        if field.label is not None:
            entry["label"] = field.label
        if field.label_not_on_axis is not None:
            entry["label_not_on_axis"] = field.label_not_on_axis
        entries[name] = entry
    labels = list(dict.fromkeys(field.label for field in read.values() if field.label is not None))
    return {"$defs": {"label": {"enum": labels}, **field_bindings(read)}, "fields": entries}


def field_bindings(rows: dict[str, FieldRow]) -> dict[str, object]:
    """What the writer schema binds to the field names (maintainer, 2026-10-15): a material body's `sections`,
    each section's `fields` closed to the names its rows register, and an overlay's `replaces`, closed to
    `<section>.<field>`; each field, and each of its alternatives, bound to its row by `field_binding`."""
    sections: dict[str, list[str]] = {}
    for qualified in rows:
        section, _, name = qualified.partition(".")
        sections.setdefault(section, []).append(name)
    return {
        "sections": {
            "description": "Each section's fields: the names its rows register, each bound to its row.",
            "properties": {
                section: {
                    "properties": {
                        "fields": {
                            "propertyNames": enumeration(names),
                            "properties": {name: {"$ref": f"#/$defs/{section}.{name}"} for name in names},
                        }
                    }
                }
                for section, names in sections.items()
            },
        },
        "replaces": {
            "description": "The fields an overlay may replace, each bound to its row.",
            "propertyNames": enumeration(list(rows)),
            "properties": {qualified: {"$ref": f"#/$defs/{qualified}"} for qualified in rows},
        },
        **{qualified: field_binding(qualified, row) for qualified, row in rows.items()},
    }


def field_unit(name: str, code: str) -> str | dict[str, str]:
    """A field's unit: a code, or a status object holding its token alone (`{"status": "not_applicable"}`)."""
    if not code.startswith("{"):
        return code
    found = re.fullmatch(r'\{"status": "([a-z_]+)"\}', code)
    if found is None:
        raise TableError(f"expected a unit code or a status object for {name}, got {code!r}")
    return {"status": found[1]}


def field_binding(qualified: str, row: FieldRow) -> dict[str, object]:
    """A field's row as a schema of its members: the forms it takes, the bases it allows a composition, its
    unit (a code, or a status object holding the registered token, whatever its reason), and its label or
    none, on the forms its Label cell names, applied to the field and to each of its alternatives."""
    if isinstance(row.unit, str):
        unit: object = {"const": row.unit}
    else:
        token = {"const": row.unit["status"]}
        unit = {"type": "object", "required": ["status"], "properties": {"status": token}}
    if set(row.bases) - {"composition"}:
        raise TableError(f"a basis is a composition's only, not {sorted(set(row.bases) - {'composition'})}")
    binding: dict[str, object] = {
        "properties": {
            "form": enumeration(row.forms),
            "unit": unit,
            "label": False if row.label is None else {"const": row.label},
            **{form: {"properties": {"basis": enumeration(allowed)}} for form, allowed in row.bases.items()},
            "alternatives": {"items": {"$ref": f"#/$defs/{qualified}"}},
        }
    }
    if row.label is not None:
        binding["dependentSchemas"] = {"label": label_binding(qualified, row)}
    return binding


def label_binding(qualified: str, row: FieldRow) -> dict[str, object]:
    """Where a field holds its row's label, the forms its Label cell names it on: a constant, and a table
    whose axis is not the condition the cell names, where it names one (`record_format.md` section 4.1,
    "Labels"; a label the row does not name for the field and its form refuses it, so a writer cannot write
    one)."""
    forms = ["constant"] if row.label_not_on_axis is None else ["constant", "table"]
    if set(forms) - set(row.forms):
        raise TableError(f"{qualified}'s Label cell names its label on a form the row does not allow")
    binding: dict[str, object] = {"properties": {"form": enumeration(forms)}}
    if row.label_not_on_axis is not None:
        binding["if"] = {"required": ["form"], "properties": {"form": {"const": "table"}}}
        binding["then"] = {
            "properties": {"table": {"properties": {"axis": {"not": {"const": row.label_not_on_axis}}}}}
        }
    return binding


def field_label(cell: str) -> str:
    """The label a Label cell names: one code span, a family identifier, then ` on ` and prose saying where it
    applies, which is code (`record_format.md` section 4.1, "Labels") and names no second label."""
    found = _LABEL_CELL.fullmatch(cell)
    if found is None or not _LABEL.fullmatch(found[1]):
        raise TableError(f"expected a label's code span, then ' on ' and where it applies, in {cell!r}")
    if any(_LABEL.fullmatch(code) for code in codes(found[2])):
        raise TableError(f"a second label in {cell!r}")
    return found[1]


def label_not_on_axis(cell: str) -> str | None:
    """Where a Label cell's label goes, after ` on `: "a constant", giving None, or "a constant, or on a table
    whose axis is not `<condition>`", giving the condition. Any other prose stops the script, since a reader
    reads where a label goes from what this gives (`record_format.md` section 4.1, "Labels")."""
    found = _LABEL_CELL.fullmatch(cell)
    where = _LABEL_ON.fullmatch(found[2]) if found is not None else None
    if where is None:
        raise TableError(
            f"expected ' on a constant', or ' on a constant, or on a table whose axis is not `<condition>`', "
            f"in {cell!r}"
        )
    return where[1]


def field_forms(cell: str) -> tuple[list[str], dict[str, list[str]]]:
    """A field's forms, and for a form the row restricts, the bases it allows: `composition (basis `a`)`. A
    reference to the section that defines a form (`evidence (section 4.3)`) is prose."""
    forms: list[str] = []
    bases: dict[str, list[str]] = {}
    for item in re.split(r", (?![^()]*\))", re.sub(r" \(section [0-9.]+\)", "", cell)):
        form = re.fullmatch(r"([a-z0-9_]+)(?: \(basis (`[a-z0-9_]+`(?:, `[a-z0-9_]+`)*)\))?", item)
        if form is None:
            raise TableError(f"expected forms, each perhaps with its bases, in {cell!r}")
        forms.append(form[1])
        if form[2] is not None:
            bases[form[1]] = codes(form[2])
    return forms, bases


def conditions(rows: list[Row]) -> Vocabulary:
    entries: dict[str, dict[str, object]] = {}
    token_conditions: dict[str, list[str]] = {}
    for name, row in zip(names(rows, "Name"), rows, strict=True):
        cell = row["Unit or tokens"]
        if row["Shape"] == "numeric":
            unit = _UNIT_CELL.fullmatch(cell)
            if unit is None:
                raise TableError(
                    f"expected a unit's code span, then nothing, an aside or ': ' and prose: {cell!r}"
                )
            entries[name] = {"shape": "numeric", "unit": unit[1]}
        elif row["Shape"] == "token":
            token_conditions[name] = code_list(outside_parentheses(cell), cell)
            entries[name] = {"shape": "token", "tokens": token_conditions[name]}
        else:
            raise TableError(f"not a condition's shape: {row['Shape']!r}")
    for row in rows:
        entries[only_code(row["Name"])]["required_with"] = required_with(
            row["Required with"], token_conditions
        )
    # Each token condition's tokens again as an enumeration, which the writer schema binds its `token` to.
    tokens = {f"{name}_token": enumeration(found) for name, found in token_conditions.items()}
    # The numeric conditions' names: the tokens a table's `axis` takes (`record_format.md` section 6, table
    # item 1, "a numeric condition").
    axis = enumeration([name for name, entry in entries.items() if entry["shape"] == "numeric"])
    return {
        "$defs": {**tokens, "axis": axis, "units": condition_units(entries), "axes": table_axes(entries)},
        "conditions": entries,
    }


def condition_units(entries: dict[str, dict[str, object]]) -> dict[str, object]:
    """What the writer schema binds to the condition names (maintainer, 2026-10-15): each numeric condition's
    `unit`, and the `unit` of each entry of its `plus_minus`, which item 6 compares with the same unit, hold
    its registered unit."""
    units = {name: {"const": entry["unit"]} for name, entry in entries.items() if entry["shape"] == "numeric"}
    return {
        "description": "Each numeric condition's registered unit, in its unit and its plus_minus entries'.",
        "properties": {
            name: {"properties": {"unit": unit, "plus_minus": {"items": {"properties": {"unit": unit}}}}}
            for name, unit in units.items()
        },
    }


def table_axes(entries: dict[str, dict[str, object]]) -> dict[str, object]:
    """What the writer schema binds to a table's axis (`record_format.md` section 6, table item 1): for each
    numeric condition, a table whose `axis` names it holds that condition's registered unit in `axis_unit`,
    and its field's `conditions` hold the condition as `{"status": "not_applicable"}`."""
    numeric = {name: entry["unit"] for name, entry in entries.items() if entry["shape"] == "numeric"}

    def naming(name: str) -> dict[str, object]:
        return {
            "required": ["table"],
            "properties": {"table": {"required": ["axis"], "properties": {"axis": {"const": name}}}},
        }

    not_applicable = {
        "type": "object",
        "required": ["status"],
        "properties": {"status": {"const": "not_applicable"}},
    }
    return {
        "description": "A table's axis: its axis_unit holds that numeric condition's registered unit, and "
        "the field's conditions hold the condition as not_applicable.",
        "properties": {
            "table": {
                "allOf": [
                    {
                        "if": {"required": ["axis"], "properties": {"axis": {"const": name}}},
                        "then": {"properties": {"axis_unit": {"const": unit}}},
                    }
                    for name, unit in numeric.items()
                ]
            }
        },
        "allOf": [
            {
                "if": naming(name),
                "then": {
                    "required": ["conditions"],
                    "properties": {"conditions": {"required": [name], "properties": {name: not_applicable}}},
                },
            }
            for name in numeric
        ],
    }


def required_with(cell: str, token_conditions: dict[str, list[str]]) -> dict[str, list[str]]:
    """The conditions and tokens with which a condition is required (`provenance.md` section 6.1 item 9):
    a dash (U+2014), or `other`: `a`, `b`, each `other` a token condition of the table and each token one of
    its own."""
    if cell == "\u2014":
        return {}
    found: dict[str, list[str]] = {}
    for part in cell.split("; "):
        named = re.fullmatch(r"`([a-z0-9_]+)`: (.+)", part)
        if named is None:
            raise TableError(f"expected `condition`: `token`, ... in {cell!r}")
        listed_tokens = code_list(named[2], cell)
        if not set(listed_tokens) <= set(token_conditions.get(named[1], [])):
            raise TableError(f"not a token condition of the table and its tokens: {part!r}")
        found[named[1]] = listed_tokens
    return found


def specimen_facts(rows: list[Row]) -> Vocabulary:
    """Each fact's tokens, those its `token` member takes, and the one value of each member its shape fixes
    (`"unit": "s"`), each again as an enumeration in `$defs`; in `$defs` the pattern of each identifier its
    shape writes (`"UBERON:<digits>"`, maintainer 2026-10-15), which the writer schema takes from here; and
    the binding of each fixed unit (`fact_units`). Its other members are structure, the writer schema's."""
    entries: dict[str, object] = {}
    definitions: dict[str, object] = {}
    units: list[str] = []
    for name, row in zip(names(rows, "Name"), rows, strict=True):
        shape = row["JSON shape"]
        found: list[str] = []
        for named in re.finditer(r'"token"', shape):
            member = _TOKEN_MEMBER.match(shape, named.start())
            if member is None:
                raise TableError(f'expected "token": "a" | "b" in {shape!r}')
            found += re.findall(r'"([a-z0-9_]+)"', member[1])
        fixed = fixed_members(shape)
        entries[name] = {"tokens": found, **fixed}
        if found:
            definitions[f"{name}_token"] = enumeration(found)
        for member_name, value in fixed.items():
            definitions[f"{name}_{member_name}"] = enumeration([value])
        for member_name, pattern in identifier_patterns(shape).items():
            definitions[f"{name}_{member_name}"] = {"type": "string", "pattern": pattern}
        if "unit" in fixed:
            units.append(name)
    return {"$defs": {**definitions, "units": fact_units(units)}, "facts": entries}


def fact_units(units: Sequence[str]) -> dict[str, object]:
    """What the writer schema binds to the fact names (maintainer, 2026-10-15): the `unit` of each fact whose
    row fixes one holds that unit, its enumeration here, so that no record that step 9 refuses is written, a
    status object there included. A fact whose unit the source does not give is written as a status object in
    its place."""
    return {
        "description": "Each specimen fact's unit, where its row fixes one.",
        "properties": {name: {"properties": {"unit": {"$ref": f"#/$defs/{name}_unit"}}} for name in units},
    }


def fixed_members(shape: str) -> dict[str, str]:
    """The members other than `token` that a fact's shape writes with one quoted value, each taking that value
    alone. A placeholder (`<text>`) or a range (`[lo, hi]`) is structure, the writer schema's, and an
    identifier (`"UBERON:<digits>"`) is `identifier_patterns`'; any other value, a list of values or a quoted
    placeholder of another form among them, stops the script."""
    fixed: dict[str, str] = {}
    for member in _MEMBER_VALUE.finditer(shape):
        if member[1] == "token" or shape.startswith(("<", "["), member.end()):
            continue
        value = _QUOTED.match(shape, member.end())
        if value is None or not re.fullmatch(r'[^\s"<>|]+|[^"]*<[a-z]+>[^"]*', value[1]):
            raise TableError(
                f"expected a quoted value, a placeholder or a range for {member[1]!r} in {shape!r}"
            )
        if "<" in value[1]:
            if not _IDENTIFIER.fullmatch(value[1]):
                raise TableError(
                    f"expected an identifier written <PREFIX>:<digits> for {member[1]!r} in {shape!r}"
                )
            continue
        if fixed.setdefault(member[1], value[1]) != value[1]:
            raise TableError(f"two values for {member[1]!r} in {shape!r}")
    return fixed


def identifier_patterns(shape: str) -> dict[str, str]:
    """Each member a fact's shape writes as an identifier, `"UBERON:<digits>"`, and the pattern of that form:
    its prefix and a colon, one digit or more, and nothing after (a validator's `$` would allow a final
    newline). `fixed_members` refuses a quoted placeholder of any other form."""
    found: dict[str, str] = {}
    for member in _MEMBER_VALUE.finditer(shape):
        value = _QUOTED.match(shape, member.end())
        if value is not None and (identifier := _IDENTIFIER.fullmatch(value[1])):
            found[member[1]] = f"^{identifier[1]}:[0-9]+(?![\\s\\S])"
    return found


def acceptances(rows: list[Row]) -> Vocabulary:
    """`declarations.md` section 4.1: the kinds of acceptance, and an extrapolation's methods, which its row's
    own members name: "`method` (`constant` or `consumer_law`)"."""
    kinds = names(rows, "`acceptance`")
    own = cell_of(rows, "extrapolation", "Own members")
    return {"kinds": kinds, "$defs": {"extrapolation_method": enumeration(listed(own, "`method` (", ")"))}}


# `declarations.md` section 4.2's "Covered by" column: each phrasing the table uses, and the rule it states. A
# phrasing not listed here stops the generator, so that a row is never read loosely (the S7 design's 6.5).
# `kind` is the kind of acceptance that covers; each flag is false unless given: `names_code`, the
# acceptance's `code` is the reason's; `names_condition`, its `condition` is the reason's; `on_assumption`,
# only on a result whose `assumption` names the acceptance; `names_differing_members`, an `overlay_scope`
# naming every member that differs; `carries_value`, only on a result that carries a value.
COVERED_BY: dict[str, dict[str, object]] = {
    "a `waiver` naming that condition and code": {
        "kind": "waiver",
        "names_code": True,
        "names_condition": True,
    },
    "a `waiver` naming that code": {"kind": "waiver", "names_code": True},
    "a `pick` only": {"kind": "pick"},
    "an `extrapolation` only": {"kind": "extrapolation"},
    "an `extrapolation`, only on a result whose `assumption` names it": {
        "kind": "extrapolation",
        "on_assumption": True,
    },
    "a `nominal`, only on a result whose `assumption` names it": {"kind": "nominal", "on_assumption": True},
    "an `overlay_scope` naming every member that differs": {
        "kind": "overlay_scope",
        "names_differing_members": True,
    },
    "an `accepted_difference`": {"kind": "accepted_difference"},
    "its `trainable` entry (section 7), on a result that carries a value": {
        "kind": "trainable",
        "carries_value": True,
    },
}
# Every flag a coverage row holds: the rule's, and `trainable`, that the row covers on a field listed in
# `trainable` alone, which its Reason column states.
COVERAGE_FLAGS = (
    "names_code",
    "names_condition",
    "on_assumption",
    "names_differing_members",
    "carries_value",
    "trainable",
)
# The Reason column's phrases beside code spans, joined as prose joins a list.
SPECIMEN_DIFFERENCE, CONDITION_REASON = "a specimen difference", "a condition reason"
# The qualifiers a Reason cell may end with, each with what its row's rule must already hold, and what the
# qualifier adds. A nominal's `assumption` names it only where it supplied the value, which it does only for a
# value read from an interval or a vector read from a parameter set with none (`read_side_contract.md`
# section 6), so that qualifier adds nothing to its row's own condition, which it requires.
REASON_QUALIFIERS: dict[str, tuple[dict[str, object], dict[str, object]]] = {
    ", for a value read from an interval, or a vector read from a parameter set with none": (
        {"on_assumption": True},
        {},
    ),
    ", on a field listed in `trainable`": ({"kind": "trainable"}, {"trainable": True}),
}
# The Status column: a read status, or the two cells of the rows that are not a reason's.
STATUS_CELLS: dict[str, str | None] = {
    "unknown": "unknown",
    "not_met": "not_met",
    "(not a status)": None,
    "any": "any",
}
# A list in the Reason column: items joined by commas, `or` and `and`.
_REASON_ITEMS = re.compile(r", or |, and |, | or | and ")


def coverage(read: Documents) -> Vocabulary:
    """`declarations.md` section 4.2: per row, the reasons it covers and the rule of what covers them. "A
    condition reason" is each of section 4's `condition_*` codes (the six `condition_*` codes, section 1) but
    those the paragraph above the table says are never accepted ("`condition_unknown_name` among them"), which
    no row may list."""
    document = read("declarations.md")
    reason_rows = table(read("read_side_contract.md"), "## 4. Reason codes")
    statuses = {
        code: row["Status"] for code, row in zip(names(reason_rows, "Code"), reason_rows, strict=True)
    }
    kinds = names(table(document, "### 4.1 The list"), "`acceptance`")
    never = listed(prose(document), "A reason not listed is never accepted, ", " among them")
    condition_reasons = [code for code in statuses if code.startswith("condition_") and code not in never]
    rows: list[object] = []
    for row in table(document, "### 4.2 What covers which reason"):
        rule = covering(row["Covered by"], kinds)
        reasons, specimen_difference = covered_reasons(row["Reason"], rule, statuses, condition_reasons)
        if listed_never := sorted(set(reasons) & set(never)):
            raise TableError(f"a row lists a reason the table never accepts: {listed_never}")
        rows.append(
            {
                "reasons": reasons,
                "specimen_difference": specimen_difference,
                "status": row_status(row["Status"], reasons, specimen_difference, statuses),
                "covered_by": row["Covered by"],
                **rule,
            }
        )
    return {"coverage": rows}


def covering(cell: str, kinds: list[str]) -> dict[str, object]:
    """The rule a "Covered by" cell states, by `COVERED_BY`: its kind, of section 4.1 or the `trainable`
    acceptance section 7 gives, and every flag."""
    if cell not in COVERED_BY:
        raise TableError(f"a phrasing of what covers a reason this script does not know: {cell!r}")
    rule = {"kind": "", **dict.fromkeys(COVERAGE_FLAGS, False), **COVERED_BY[cell]}
    if rule["kind"] not in (*kinds, "trainable"):
        raise TableError(f"{cell!r} names no kind of acceptance")
    return rule


def covered_reasons(
    cell: str, rule: dict[str, object], statuses: dict[str, str], condition_reasons: list[str]
) -> tuple[list[str], bool]:
    """A Reason cell's codes, "a condition reason" read as those codes, and whether it names a specimen
    difference. A qualifier it ends with must agree with the row's rule (`REASON_QUALIFIERS`), and sets the
    flags it adds in `rule`."""
    for qualifier, (required, added) in REASON_QUALIFIERS.items():
        if cell.endswith(qualifier):
            if any(rule[name] != value for name, value in required.items()):
                raise TableError(f"{cell!r} qualifies a row whose rule does not hold {required}")
            rule.update(added)
            cell = cell.removesuffix(qualifier)
            break
    reasons: list[str] = []
    specimen_difference = False
    for item in _REASON_ITEMS.split(cell):
        if item == SPECIMEN_DIFFERENCE:
            specimen_difference = True
        elif item == CONDITION_REASON:
            reasons += condition_reasons
        elif re.fullmatch(r"`[a-z0-9_]+`", item) and item[1:-1] in statuses:
            reasons.append(item[1:-1])
        else:
            raise TableError(f"neither a reason code nor a phrase this script knows: {item!r} in {cell!r}")
    if len(set(reasons)) != len(reasons):
        raise TableError(f"a reason listed twice in {cell!r}")
    return reasons, specimen_difference


def row_status(
    cell: str, reasons: list[str], specimen_difference: bool, statuses: dict[str, str]
) -> str | None:
    """A row's Status cell, which for a read status is each of its codes' status in `read_side_contract.md`
    section 4, and is not a status exactly where the row lists a specimen difference alone."""
    if cell not in STATUS_CELLS:
        raise TableError(f"not a status this script knows: {cell!r}")
    status = STATUS_CELLS[cell]
    if (status is None) != (specimen_difference and not reasons):
        raise TableError(f"{cell!r} beside the reasons {reasons}")
    if status in ("unknown", "not_met") and (
        differing := [code for code in reasons if statuses[code] != status]
    ):
        raise TableError(f"a row of status {status} lists codes of another status: {differing}")
    return status


def forms(read: Documents) -> Vocabulary:
    """`record_format.md` sections 5 and 6: the form tokens, a table's schemes, an interval's and a
    composition's tokens, and the components, `element:<symbol>` for each symbol of the element table."""
    document = read("record_format.md")
    text = prose(document)
    members = table(document, "## 5. Value fields")
    table_form = between(text, "**Table.**", "**Power law.**")
    interval = between(text, "**Interval.**", "**Composition.**")
    composition = between(text, "**Composition.**", "**Model parameter set.**")
    once(composition, "`component` is `element:<symbol>`")
    heading = re.search(r"^The element symbols are IUPAC's (\d+) .*:$", document, re.M)
    if heading is None:
        raise TableError("no line introducing the element table")
    symbols: list[str] = []
    for period in table(document, heading[0]):
        if not _SYMBOLS.fullmatch(period["Symbols"]):
            raise TableError(f"expected element symbols in {period['Symbols']!r}")
        symbols += codes(period["Symbols"])
    if len(symbols) != int(heading[1]):
        raise TableError(f"the element table holds {len(symbols)} symbols, not the {heading[1]} it states")
    return {
        "$defs": {
            "form": enumeration(listed(cell_of(members, "form"), "one of ", None)),
            "table_scheme": enumeration(listed(table_form, "2. `scheme` is ", ".")),
            "interval_basis": enumeration(listed(interval, "2. `basis` is ", ".")),
            "composition_basis": enumeration(listed(composition, "1. `basis` is ", ". `component`")),
            "sum_rule": enumeration(listed(composition, "2. `sum_rule` is ", ". Where")),
            "component": enumeration([f"element:{symbol}" for symbol in symbols]),
        }
    }


def statistics(read: Documents) -> Vocabulary:
    """`uncertainty.md` sections 1 and 4: the statistics block's tokens, an uncertainty's, and the
    distribution tokens a record or a declaration may name."""
    document = read("uncertainty.md")
    members = table(document, "## 1. The statistics block")
    uncertainty = between(prose(document), "In a relative or expanded uncertainty:", "Every uncertainty")
    return {
        "$defs": {
            "central": enumeration(listed(cell_of(members, "central"), "a constant's `value` is: ", ";")),
            "statistics_distribution": enumeration(
                listed(cell_of(members, "distribution"), "the block gives: ", " where the source states one")
            ),
            "statistics_basis": enumeration(listed(cell_of(members, "basis"), "spread comes from: ", ";")),
            "represents": enumeration(listed(cell_of(members, "represents"), "spread describes: ", ";")),
            "level": enumeration(
                listed(cell_of(members, "population_level"), "the levels are ", " (rule 10)")
            ),
            "precision_conditions": enumeration(
                listed(cell_of(members, "precision_conditions"), "is `measurement`: ", ", or `{")
            ),
            "dispersion": enumeration(
                listed(cell_of(members, "dispersion"), None, " where the source gives")
            ),
            "uncertainty_distribution": enumeration(listed(uncertainty, "- `distribution` is ", " or `{")),
            "uncertainty_basis": enumeration(listed(uncertainty, "- `basis` is ", ";")),
            "uncertainty_represents": enumeration(listed(uncertainty, "- `represents` is ", " or `{")),
            "distribution": enumeration(
                [only_code(token["Token"]) for token in table(document, "## 4. Distribution tokens")]
            ),
        }
    }


def provenance(read: Documents) -> Vocabulary:
    """`provenance.md`: the origins, a review's result, the extraction methods, the locator types, a search's
    inputs, a condition's or fact's basis, and a condition's `plus_minus` and `set_or_measured` tokens."""
    document = read("provenance.md")
    text = prose(document)
    members = table(document, "## 2. The provenance object")
    methods = table(document, "## 3. Extraction")
    return {
        "$defs": {
            "origin": enumeration(listed(cell_of(members, "origin"), None, None)),
            "review_result": enumeration(listed(text, "whose `result` is a token the reader knows (", ")")),
            "extraction_method": enumeration(
                [method for row in methods for method in code_list(row["Method"], row["Method"])]
            ),
            "locator_type": enumeration(listed(text, "A `locator` names its `type` (", ")")),
            "search_inputs": enumeration(listed(cell_of(members, "search"), "and `inputs`: ", None)),
            "basis": enumeration(listed(text, "a status object carries a `basis`: ", " with an")),
            "stated_as": enumeration(listed(text, "`stated_as` is ", " or `{")),
            "set_or_measured": enumeration(listed(text, "`set_or_measured` is ", ";")),
        }
    }


def labels(read: Documents) -> Vocabulary:
    """`read_side_contract.md` section 2: the labels a result may hold beside the field's own."""
    members = table(read("read_side_contract.md"), "## 2. The read result")
    found = listed(cell_of(members, "labels"), "from this list only: ", ", and the field's `label`")
    return {"$defs": {"result_label": enumeration(found)}}


def from_table(
    document: str, heading: str, read_rows: Callable[[list[Row]], Vocabulary]
) -> Callable[[Documents], Vocabulary]:
    return lambda read: read_rows(table(read(document), heading))


# Each file, where in the specification its tokens are, and how they are read.
SOURCES: dict[str, tuple[str, Callable[[Documents], Vocabulary]]] = {
    "reasons.json": (
        "read_side_contract.md, 4. Reason codes",
        from_table("read_side_contract.md", "## 4. Reason codes", reasons),
    ),
    "fields.json": (
        "record_format.md, 4.1 Sections and fields of schema 0.1.0",
        from_table("record_format.md", "### 4.1 Sections and fields of schema 0.1.0", fields),
    ),
    "conditions.json": (
        "provenance.md, 6.1 Conditions of schema 0.1.0",
        from_table("provenance.md", "### 6.1 Conditions of schema 0.1.0", conditions),
    ),
    "specimen_facts.json": (
        "provenance.md, 6.2 Specimen facts of schema 0.1.0",
        from_table("provenance.md", "### 6.2 Specimen facts of schema 0.1.0", specimen_facts),
    ),
    "acceptances.json": (
        "declarations.md, 4.1 The list",
        from_table("declarations.md", "### 4.1 The list", acceptances),
    ),
    "forms.json": ("record_format.md, 5. Value fields and 6. The value forms", forms),
    "statistics.json": ("uncertainty.md, 1. The statistics block and 4. Distribution tokens", statistics),
    "provenance.json": (
        "provenance.md, 2. The provenance object, 3. Extraction and 6. Conditions",
        provenance,
    ),
    "labels.json": ("read_side_contract.md, 2. The read result", labels),
    "coverage.json": (
        "declarations.md, 4.2 What covers which reason, with read_side_contract.md, 4. Reason codes",
        coverage,
    ),
}


def generate(specification: Path = SPECIFICATION) -> dict[str, str]:
    """Each vocabulary file's name and text."""

    def read(document: str) -> str:
        return (specification / document).read_text(encoding="utf-8")

    files: dict[str, str] = {}
    for name, (source, tokens_of) in SOURCES.items():
        contents = {
            "$id": VOCABULARY_ID + name,
            "$comment": f"Generated by scripts/gen_vocabulary.py from docs/specification/{source}. "
            "Edit the specification.",
            **tokens_of(read),
        }
        files[name] = json.dumps(contents, indent=2, ensure_ascii=False) + "\n"
    return files


def main(arguments: Sequence[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    if list(arguments) not in ([], ["--check"]):
        print("usage: python scripts/gen_vocabulary.py [--check]", file=sys.stderr)
        return 2
    files = generate(SPECIFICATION)
    if arguments:
        differing = sorted(
            name
            for name, text in files.items()
            if not (VOCABULARY / name).is_file() or (VOCABULARY / name).read_text(encoding="utf-8") != text
        )
        stray = sorted({path.name for path in VOCABULARY.glob("*.json")} - files.keys())
        for name in differing:
            print(
                f"{name} differs from the specification: run scripts/gen_vocabulary.py",
                file=sys.stderr,
            )
        for name in stray:
            print(f"{name} comes from no table", file=sys.stderr)
        return 1 if differing or stray else 0
    VOCABULARY.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (VOCABULARY / name).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
