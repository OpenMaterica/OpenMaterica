# SPDX-License-Identifier: Apache-2.0
"""Each rule of the reference model, and of the reference evaluator of tables beside it, cites the
specification as `file:line` and a short quote; each quote is found at its line, so that a citation that
drifts from the text fails, and so does a `file:line` without a quote, which nothing could check. A quote
holds `"` only inside a code span, as the text's JSON stands, so that it ends at the first `"` outside one.
The same holds of every test module that cites the text as `file:line`: the seeded faults of the model hold
their citation in a string (the `rule` of a `Mutant`), the rest in a comment or a docstring, and a module
that cites the text and is not listed here fails the check that lists them.
A quote is at least `MIN_QUOTE` characters, so that it cannot sit at a neighbouring line by chance, and
begins on a cited line. It may end on a later one, so a range may be shifted by less than its width and
still hold its quote: a citation of lines 49 to 51 whose quote begins on 50 passes as 48 to 50 and as 50 to
52, and fails as 47 to 49 and as 51 to 53. The controls below show which shifts pass and which fail.
Requiring the quote to reach the last cited line too would close that; measured over the 550 citations the
check reads at this writing (the model's 408 and the four test modules' 142), it fails 90 of them, which are
not re-anchored, so the check keeps the weaker rule and says so here. At this writing 280 of the 289 ranges
among them pass shifted by one line in one direction or the other, and none of the 261 single lines does.
Each point the text leaves open is listed once in `OPEN_POINTS` and named
where the model applies it, and the two agree."""

import ast
import io
import re
import tokenize
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Final

import pytest

from tests.reference import build_model, build_results_model, read_model

REPOSITORY = Path(__file__).resolve().parents[2]
SPECIFICATION = REPOSITORY / "docs" / "specification"
MODEL_SOURCES = ("read_model.py", "strict_json.py", "build_model.py", "build_results_model.py")
EVALUATOR_SOURCE = REPOSITORY / "tests" / "reference" / "table_evaluator.py"
SOURCES = [*(REPOSITORY / "tests" / "reference" / name for name in MODEL_SOURCES), EVALUATOR_SOURCE]
# The test modules that cite the text, in the strings, comments and docstrings they hold it in.
TEST_SOURCES = [
    REPOSITORY / "tests" / path
    for path in (
        "reference/mutants.py",
        "reference/cases.py",
        "reference/results_direct.py",
        "reference/results_mutants.py",
        "reference/test_build_results_model.py",
        "property/test_model_mutants.py",
        "property/test_model_properties.py",
    )
]
# A quote shorter than this finds its place at almost any line.
MIN_QUOTE: Final = 20
# The seeded faults that break an implementation property with no line in the text, each with why no line
# states it: a row listed here cites nothing, and a row that cites nothing is listed here, names an open
# point, or fails the check.
NO_LINE_IN_THE_TEXT: Final[Mapping[str, str]] = {
    "results_share_the_record": (
        "the text says what a result holds (read_side_contract.md section 2 item 5), never that its members "
        "are objects of their own"
    ),
}
SEEDED_FAULTS_SOURCE = REPOSITORY / "tests" / "reference" / "mutants.py"
RESULTS_FAULTS_SOURCE = REPOSITORY / "tests" / "reference" / "results_mutants.py"
MUTANT_KILLS_SOURCE = REPOSITORY / "tests" / "property" / "test_model_mutants.py"
# The open points of the three models, the read's, the build's declaration check and its results, which share
# no name.
OPEN_POINTS: Final[Mapping[str, str]] = {
    **read_model.OPEN_POINTS,
    **build_model.OPEN_POINTS,
    **build_results_model.OPEN_POINTS,
}
# A quote's text: characters but `"` and a backtick, and code spans, which may hold `"`.
QUOTED = r'"((?:[^"`]|`[^`]*`)+)"'
REFERENCE = re.compile(r"(?P<file>[A-Za-z_]+\.md):(?P<start>\d+)(?:-(?P<end>\d+))?")
CITATION = re.compile(
    REFERENCE.pattern + r"\s+(?P<quotes>" + QUOTED + r"(?:\s*(?:and|or|,|;|\.\.\.)\s*" + QUOTED + r")*)"
)
QUOTE = re.compile(QUOTED)
OPEN_POINT = re.compile(r"Open point: (?P<name>[a-z0-9_]+)")
OPEN_POINT_NAMED = re.compile(r"OPEN_POINTS: ([a-z0-9_]+)")


def comments(source: str) -> list[str]:
    """The comments of `source`, each run of comment lines joined."""
    texts: list[str] = []
    run: list[str] = []
    last = 0
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        if run and token.start[0] != last + 1:
            texts.append(" ".join(run))
            run = []
        run.append(token.string.lstrip("#").strip())
        last = token.start[0]
    if run:
        texts.append(" ".join(run))
    return [" ".join(text.split()) for text in texts]


def prose(source: str) -> list[str]:
    """The comments of `source`, each run of comment lines joined, and its docstrings."""
    texts = comments(source)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
            docstring = ast.get_docstring(node)
            if docstring:
                texts.append(" ".join(docstring.split()))
    return texts


def strings(source: str) -> list[str]:
    """Every string literal of `source`, its adjacent literals joined: a docstring, and the `rule` a `Mutant`
    holds as an argument, which `prose` does not read."""
    return [
        " ".join(node.value.split())
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def held_in(source: str) -> list[str]:
    """What a test module holds citations in: its comments and every string, a `Mutant`'s `rule` too."""
    return [*comments(source), *strings(source)]


def specification_lines(file: str) -> list[str] | None:
    path = SPECIFICATION / file
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else None


def begins_before(quote: str, window: str, limit: int) -> bool:
    """Whether `quote` begins in `window` before `limit`: on a cited line, though it may run on past it. A
    range may therefore be shifted by less than its width and still hold its quote (the module docstring)."""
    position = window.find(quote)
    while position != -1:
        if position < limit:
            return True
        position = window.find(quote, position + 1)
    return False


def citation_problems(texts: Iterable[str]) -> list[str]:
    """Each citation whose file is not in the specification, or whose quote does not begin at its lines (it
    may run on to the line after the last one cited); and each `file:line` with no quote."""
    problems: list[str] = []
    for text in texts:
        quoted = {citation.start() for citation in CITATION.finditer(text)}
        problems.extend(
            f"{reference[0]}: no quote"
            for reference in REFERENCE.finditer(text)
            if reference.start() not in quoted
        )
        for citation in CITATION.finditer(text):
            file, start = citation["file"], int(citation["start"])
            end = int(citation["end"] or start)
            lines = specification_lines(file)
            if lines is None:
                problems.append(f"{citation[0]}: no file {file} in the specification")
                continue
            cited = " ".join(" ".join(lines[start - 1 : end]).split())
            window = " ".join(" ".join(lines[start - 1 : end + 1]).split())
            quotes = QUOTE.findall(citation["quotes"])
            problems.extend(
                f"{file}:{start}: {quote!r} is shorter than {MIN_QUOTE} characters"
                for quote in quotes
                if len(quote) < MIN_QUOTE
            )
            problems.extend(
                f"{file}:{start}: {quote!r} is not at lines {start} to {end}"
                for quote in quotes
                if not begins_before(quote, window, len(cited))
            )
    return problems


def seeded_fault_problems(
    rules: Mapping[str, str], open_points: Mapping[str, str], no_line: Mapping[str, str]
) -> list[str]:
    """Each seeded fault whose rule cites neither the text, nor an open point listed, nor stands in `no_line`;
    each open point a rule names and `open_points` does not list; each row of `no_line` that cites or names
    a point, or that `rules` does not hold."""
    problems = [
        f"{name}: listed as having no line in the text, and not a seeded fault"
        for name in no_line
        if name not in rules
    ]
    for name, rule in rules.items():
        point = OPEN_POINT_NAMED.search(rule)
        cites = REFERENCE.search(rule) is not None
        if name in no_line:
            if cites or point:
                problems.append(
                    f"{name}: listed as having no line in the text, and cites one or names a point"
                )
        elif not cites and not point:
            problems.append(f"{name}: cites neither the text nor an open point")
        if point and point[1] not in open_points:
            problems.append(f"{name}: names the open point {point[1]}, which is not listed")
    return problems


def open_point_problems(texts: Iterable[str], listed: Mapping[str, str]) -> list[str]:
    named = {match["name"] for text in texts for match in OPEN_POINT.finditer(text)}
    return [f"named but not listed: {name}" for name in sorted(named - set(listed))] + [
        f"listed but named nowhere: {name}" for name in sorted(set(listed) - named)
    ]


def model_prose() -> list[str]:
    return [text for path in SOURCES for text in prose(path.read_text(encoding="utf-8"))]


def test_every_quote_is_at_the_lines_it_cites() -> None:
    assert citation_problems(model_prose()) == []


def test_the_test_modules_that_cite_the_text_hold_to_the_same_rules() -> None:
    held = {path: held_in(path.read_text(encoding="utf-8")) for path in TEST_SOURCES}
    assert [problem for texts in held.values() for problem in citation_problems(texts)] == []
    cited = {path.name: sum(len(CITATION.findall(text)) for text in texts) for path, texts in held.items()}
    assert cited["mutants.py"] >= 120
    assert all(count >= 1 for count in cited.values()), cited


def test_every_test_module_that_cites_the_text_is_listed() -> None:
    """A module that cites the specification as `file:line` and is neither a source of the model nor listed
    in `TEST_SOURCES` has citations nothing reads. This module holds the examples that must fail."""
    files = {path.name for path in SPECIFICATION.iterdir() if path.suffix == ".md"}
    citing = {
        path
        for path in (REPOSITORY / "tests").rglob("*.py")
        if any(match["file"] in files for match in REFERENCE.finditer(path.read_text(encoding="utf-8")))
    }
    assert sorted(citing - {*SOURCES, *TEST_SOURCES, Path(__file__).resolve()}) == []


@pytest.mark.parametrize(
    ("source", "call", "least", "no_line"),
    [
        (SEEDED_FAULTS_SOURCE, "Mutant", 121, NO_LINE_IN_THE_TEXT),
        (RESULTS_FAULTS_SOURCE, "mutant", 50, {}),
    ],
    ids=["mutants", "results_mutants"],
)
def test_every_seeded_fault_cites_the_text_or_names_the_open_point_it_rests_on(
    source: Path, call: str, least: int, no_line: Mapping[str, str]
) -> None:
    """Each fault's `rule`, its second argument, in every table of faults of a module: `mutants.py` builds its
    faults by `Mutant(...)`, `results_mutants.py` by its `mutant(...)`."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    mutants = [
        node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == call
    ]
    rules = {
        str(key.value): str(mutant.args[1].value)
        for table in ast.walk(tree)
        if isinstance(table, ast.Dict)
        for key, mutant in zip(table.keys, table.values, strict=True)
        if isinstance(key, ast.Constant)
        and isinstance(mutant, ast.Call)
        and getattr(mutant.func, "id", "") == call
        and isinstance(mutant.args[1], ast.Constant)
    }
    assert len(rules) == len(mutants)
    assert len(rules) >= least
    assert seeded_fault_problems(rules, OPEN_POINTS, no_line) == []
    assert all(reason.strip() for reason in no_line.values())


@pytest.mark.parametrize(
    ("rules", "no_line", "problem"),
    [
        ({"a": 'read_side_contract.md:243 "Find the field (`absent`)"'}, {}, None),
        ({"a": "an open point (OPEN_POINTS: known)"}, {}, None),
        ({"a": "a rule the text states"}, {}, "a: cites neither the text nor an open point"),
        ({"a": "(OPEN_POINTS: unknown)"}, {}, "names the open point unknown, which is not listed"),
        ({"a": "an implementation property"}, {"a": "no line says it"}, None),
        (
            {"a": 'read_side_contract.md:243 "Find the field"'},
            {"a": "no line"},
            "a: listed as having no line",
        ),
        ({"a": "(OPEN_POINTS: known)"}, {"a": "no line"}, "a: listed as having no line"),
        (
            {"a": "a rule"},
            {"b": "no line"},
            "b: listed as having no line in the text, and not a seeded fault",
        ),
    ],
)
def test_a_seeded_fault_that_cites_nothing_is_found(
    rules: dict[str, str], no_line: dict[str, str], problem: str | None
) -> None:
    found = seeded_fault_problems(rules, {"known": "a choice"}, no_line)
    if problem is None:
        assert found == []
    else:
        assert len(found) >= 1
        assert any(problem in one for one in found)


def test_the_model_cites_the_text_for_its_rules() -> None:
    cited = [citation for text in model_prose() for citation in CITATION.finditer(text)]
    assert len(cited) > 150
    assert {citation["file"] for citation in cited} >= {
        "read_side_contract.md",
        "record_format.md",
        "provenance.md",
        "uncertainty.md",
        "declarations.md",
        "README.md",
    }


def test_every_open_point_is_listed_once_and_named_where_it_is_applied() -> None:
    assert open_point_problems(model_prose(), OPEN_POINTS) == []
    assert all(choice.strip() for choice in OPEN_POINTS.values())


def test_the_models_list_their_open_points_apart() -> None:
    """The read model's points, the build model's and the results model's share no name, so that one listed
    twice is seen, and each model names its own."""
    points = (read_model.OPEN_POINTS, build_model.OPEN_POINTS, build_results_model.OPEN_POINTS)
    assert sum(map(len, points)) == len(OPEN_POINTS)
    for name, listed in (("build_model.py", points[1]), ("build_results_model.py", points[2])):
        texts = prose((REPOSITORY / "tests" / "reference" / name).read_text(encoding="utf-8"))
        assert open_point_problems(texts, listed) == []


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ('read_side_contract.md:243 "Find the field (`absent`)"', None),
        ('read_side_contract.md:242-243 "Find the field (`absent`)"', None),
        ('read_side_contract.md:244 "Find the field (`absent`)"', "is not at lines 244 to 244"),
        ('read_side_contract.md:242 "Find the field (`absent`)"', "is not at lines 242 to 242"),
        ('read_side_contract.md:243 "Find the record of the field"', "is not at lines 243 to 243"),
        (
            'read_side_contract.md:243 "Find the field (`absent`)" and "a quote not there at all"',
            "'a quote not there at all'",
        ),
        ('read_side_contracts.md:222 "Find the field (`absent`)"', "no file read_side_contracts.md"),
        ('read_side_contract.md:243 "Find"', "'Find' is shorter than 20 characters"),
        ('read_side_contract.md:243 "the"', "'the' is shorter than 20 characters"),
        (
            'record_format.md:601 "Two names are **one slip** apart when one becomes the other by '
            'inserting,"',
            None,
        ),
        ("read_side_contract.md:243, where the field is found", "read_side_contract.md:243: no quote"),
        ('see read_side_contract.md:242-243 (step 7), "Find the field"', "read_side_contract.md:242-243: no"),
        (
            'provenance.md:265-266 "or `{"status": "unstated"}` (a ± whose kind the source does not state)"',
            None,
        ),
        (
            'provenance.md:265-266 "or `{"status": "unstated"}` (a ± whose kind the source does state)"',
            "is not at lines 265 to 266",
        ),
        ('provenance.md:97 "`{"status": "not_checked"}`, or" and "with who checked the value"', None),
        ('provenance.md:97 "`{"status": "not_checked"}`, or `{"result"" and "with who', "no quote"),
    ],
)
def test_a_citation_that_drifts_fails(text: str, problem: str | None) -> None:
    found = citation_problems([text])
    assert found == [] if problem is None else len(found) == 1 and problem in found[0]


@pytest.mark.parametrize(
    ("lines", "passes"),
    [
        pytest.param("49-51", True, id="as-cited"),
        pytest.param("50-52", True, id="range-shifted-one-later-passes"),
        pytest.param("48-50", True, id="range-shifted-one-earlier-passes"),
        pytest.param("50-51", True, id="range-narrowed-to-the-quote-passes"),
        pytest.param("51-53", False, id="range-shifted-two-later-fails"),
        pytest.param("47-49", False, id="range-shifted-two-earlier-fails"),
        pytest.param("50", True, id="the-quote's-own-line"),
        pytest.param("51", False, id="single-line-shifted-one-later-fails"),
        pytest.param("49", False, id="single-line-shifted-one-earlier-fails"),
    ],
)
def test_a_range_shifted_by_less_than_its_width_still_holds_a_quote_that_begins_in_it(
    lines: str, passes: bool
) -> None:
    """The quote begins on line 50 and ends on it. A single line shifted by one fails, as a range two lines
    wide shifted by two does; a range shifted by one passes, which is the limit the module's docstring states
    (a range may be shifted by less than its width)."""
    quote = '"whose `want` belongs to a suite the reader does not claim is refused at the same step"'
    found = citation_problems([f"read_side_contract.md:{lines} {quote}"])
    assert found == [] if passes else len(found) == 1 and "is not at lines" in found[0]


def test_an_open_point_named_and_listed_apart_fails() -> None:
    listed = {"known": "a choice", "unused": "another"}
    assert open_point_problems(["Open point: known.", "Open point: unknown."], listed) == [
        "named but not listed: unknown",
        "listed but named nowhere: unused",
    ]


def test_the_evaluator_is_held_to_the_same_citation_rules() -> None:
    texts = prose(EVALUATOR_SOURCE.read_text(encoding="utf-8"))
    assert sum(len(CITATION.findall(text)) for text in texts) >= 20
    assert citation_problems(texts) == []
    assert EVALUATOR_SOURCE in SOURCES


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        pytest.param(
            "read_side_contract.md:571 ", "read_side_contract.md:580 ", "is not at lines 580", id="line"
        ),
        pytest.param('"Linear interpolation within', '"Linear interpolation outside', "outside", id="quote"),
        pytest.param(
            "read_side_contract.md:571 ", "read_contract.md:557 ", "no file read_contract.md", id="file"
        ),
    ],
)
def test_a_citation_of_the_evaluator_that_drifts_fails(old: str, new: str, problem: str) -> None:
    """The evaluator's own source, with one of its citations drifted, fails the check that passes it."""
    source = EVALUATOR_SOURCE.read_text(encoding="utf-8")
    assert source.count(old) == 1
    assert citation_problems(prose(source)) == []
    found = citation_problems(prose(source.replace(old, new)))
    assert len(found) == 1
    assert problem in found[0]


@pytest.mark.parametrize(
    ("source", "old", "new", "problem"),
    [
        pytest.param(
            SEEDED_FAULTS_SOURCE,
            "read_side_contract.md:143 ",
            "read_side_contract.md:144 ",
            "lines 144 to 144",
            id="mutants-one-line-after",
        ),
        pytest.param(
            SEEDED_FAULTS_SOURCE,
            "read_side_contract.md:143 ",
            "read_side_contract.md:142 ",
            "lines 142 to 142",
            id="mutants-one-line-before",
        ),
        pytest.param(
            SEEDED_FAULTS_SOURCE,
            ' "A reason carries `condition` exactly when it concerns one condition"',
            "",
            "read_side_contract.md:143: no quote",
            id="mutants-no-quote",
        ),
        pytest.param(
            SEEDED_FAULTS_SOURCE,
            "A reason carries `condition` exactly when",
            "A reason carries `alternative` exactly when",
            "is not at lines 143 to 143",
            id="mutants-quote-changed",
        ),
        pytest.param(
            MUTANT_KILLS_SOURCE,
            "(provenance.md:51-53 ",
            "(provenance.md:52-54 ",
            "lines 52 to 54",
            id="properties",
        ),
    ],
)
def test_a_citation_of_a_seeded_fault_that_drifts_fails(
    source: Path, old: str, new: str, problem: str
) -> None:
    """The source of the seeded faults and the test of their kills, with one citation drifted, fail the check
    that passes them: a citation there is a string or a docstring, which `prose` alone does not read."""
    text = source.read_text(encoding="utf-8")
    assert text.count(old) == 1
    assert citation_problems(held_in(text)) == []
    found = citation_problems(held_in(text.replace(old, new)))
    assert len(found) == 1
    assert problem in found[0]
