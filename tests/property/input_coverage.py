# SPDX-License-Identifier: Apache-2.0
"""Cuts of the draws the tests make, for `scripts/input_coverage.py`: a pytest plugin, loaded only with
`-p tests.property.input_coverage` (README, "Every draw is held").

Imported, it puts a wrapper in place of each strategy constructor of `hypothesis.strategies` and of `|`
between two strategies, before any test module imports one (`from hypothesis.strategies import x` binds at
import). With neither option below, a wrapper calls the constructor it replaced with the same arguments and
returns what that returns, so that every draw is the one drawn without the plugin
(`tests/unit/test_input_coverage.py` compares them).

A site is a call of a constructor written in a module under `tests/`, named by where it is written: the
module, the functions around the call (as Python's `__qualname__` names them), and the call's own text
(`ast.unparse`, cut at `LABEL_LENGTH`), with `#2`, `#3`... for a later call of the same text in the same
function. So a site keeps its name when lines around it move, and changes it when its own call changes.
Where the call runs in a plain function called from another, the site is named after the outermost of that
chain of calls written under `tests/`, the owner, and the call the owner makes into the chain (`owner > call >
place`): a helper's draw made for a composite strategy is that composite's draw, two calls of one helper are
two draws, and a cut changes each there alone.

- `--input-coverage-out DIR` runs the tests derandomized, with no example database, and records into `DIR`:
  from each process, what the calls at each site drew from (`sites-*.json`: the values, options, ends and
  sizes they had) and the calls of plain `random` in the modules under `tests/` it loaded; from the process
  that reports, every test that failed (`outcome.json`), and the first failure that holds a cut at once
  (`held`).
- `--input-coverage-cut CUT`, with `--input-coverage-out`, changes the draws of one site (`CUT`: a JSON
  object of its `site_id`, its `change`, one of `CHANGES`, and the value or option a `drop` names, `key`), and
  records in `effects-*.json` how many of that site's calls it changed (`applied`), did not touch
  (`unchanged`) or left as drawn because the change would have left nothing to draw (`empty`). The first
  failure that is not an invalid draw (`INVALID`) stops the run.
"""

import ast
import functools
import hashlib
import inspect
import json
import math
import os
import re
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import CodeType, FrameType
from typing import Any, cast

import pytest
from hypothesis import Phase, settings, strategies
from hypothesis.control import currently_in_test_context
from hypothesis.strategies import SearchStrategy

TESTS = Path(__file__).resolve().parents[1]
ROOT = TESTS.parent
UNDER_TESTS = str(TESTS) + os.sep

# The kinds of draw a cut changes, by constructor (`|` for `a | b`).
VALUES = ("sampled_from", "booleans")
OPTIONS = ("one_of", "|")
RANGES = ("integers", "floats")
SIZES = ("lists", "sets", "frozensets", "dictionaries")
ORDERS = ("permutations",)
CUTTABLE = frozenset((*VALUES, *OPTIONS, *RANGES, *SIZES, *ORDERS))
CHANGES = {
    "drop": (*VALUES, *OPTIONS),
    "pin_low": RANGES,
    "off_low": RANGES,
    "pin_high": RANGES,
    "off_high": RANGES,
    "least_size": SIZES,
    "off_least": SIZES,
    "greatest_size": SIZES,
    "off_greatest": SIZES,
    "identity_order": ORDERS,
}
# Constructors that draw nothing of their own: a constant, or what the strategies given them draw. A
# `fixed_dictionaries` draws whether each `optional` key is present, so one given any is listed uncut.
DRAW_NOTHING = frozenset({"just", "none", "nothing", "tuples", "data", "deferred", "shared", "runner"})
# Names of `hypothesis.strategies` that construct no strategy. Every other public name is a constructor; one
# neither cuttable nor drawing nothing (`text`, `builds`, `randoms`, `recursive`, `from_type`...) is recorded
# and listed, uncut.
NOT_CONSTRUCTORS = frozenset(
    {"composite", "register_type_strategy", "DataObject", "DrawFn", "SearchStrategy"}
)
# A test failing at one of these drew nothing valid under the cut: the cut is reported as that, never as held.
INVALID = re.compile(
    r"Unsatisfiable|FailedHealthCheck|InvalidArgument|rejected \d+% of its draws|the audits saw no draws"
)
AFTER_A_FAILURE = (Phase.shrink, Phase.explain)
LABEL_LENGTH = 72
KEY_LENGTH = 60

Position = tuple[int, int, int, int]
Strategy = SearchStrategy[Any]


def relative(filename: str) -> str:
    path = Path(filename).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


@functools.cache
def under_tests(filename: str) -> bool:
    return filename.startswith(UNDER_TESTS)


def shortened(text: str, length: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= length else text[: length - 1] + "…"


@dataclass(frozen=True)
class Place:
    """Where a call is written, the text of each option it writes out (`one_of`, `|`), if it does, and whether
    it calls a function of `random` or makes a `Random`."""

    name: str
    options: tuple[str, ...] | None
    random: bool = False


@functools.cache
def places(filename: str) -> dict[Position, Place]:
    """Each call and binary operation of a module, by its position."""
    tree = ast.parse(Path(filename).read_text(encoding="utf-8"))
    found: dict[Position, Place] = {}
    numbers: dict[tuple[str, str], int] = {}
    path = relative(filename)

    def visit(node: ast.AST, scope: str, in_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                inner = (
                    child.name
                    if scope == "<module>"
                    else f"{scope}.{'<locals>.' if in_function else ''}{child.name}"
                )
                visit(child, inner, not isinstance(child, ast.ClassDef))
                continue
            if isinstance(child, ast.Call | ast.BinOp) and child.end_lineno is not None:
                label = shortened(ast.unparse(child), LABEL_LENGTH)
                number = numbers[scope, label] = numbers.get((scope, label), 0) + 1
                name = f"{path}::{scope}::{label}" + (f"#{number}" if number > 1 else "")
                position = (child.lineno, child.end_lineno, child.col_offset, child.end_col_offset or 0)
                found[position] = Place(name, option_texts(child), calls_random(child))
            visit(child, scope, in_function)

    visit(tree, "<module>", False)
    return found


def calls_random(node: ast.Call | ast.BinOp) -> bool:
    if not isinstance(node, ast.Call):
        return False
    called = node.func
    if isinstance(called, ast.Attribute):
        return isinstance(called.value, ast.Name) and called.value.id == "random"
    return isinstance(called, ast.Name) and called.id == "Random"


def option_texts(node: ast.Call | ast.BinOp) -> tuple[str, ...] | None:
    if isinstance(node, ast.BinOp):
        return (ast.unparse(node.left), ast.unparse(node.right))
    if node.keywords or any(isinstance(argument, ast.Starred) for argument in node.args):
        return None
    written: list[ast.expr] = node.args
    if len(written) == 1 and isinstance(written[0], ast.List | ast.Tuple):
        written = written[0].elts
        if any(isinstance(element, ast.Starred) for element in written):
            return None
    return tuple(ast.unparse(option) for option in written)


@functools.cache
def place_at(code: CodeType, offset: int) -> Place:
    """The place of the call a frame running `code` is in, at byte `offset`."""
    line, end_line, column, end_column = list(code.co_positions())[offset // 2]
    found = None
    if line is not None and end_line is not None and column is not None and end_column is not None:
        found = places(code.co_filename).get((line, end_line, column, end_column))
    return found or Place(f"{relative(code.co_filename)}::{code.co_qualname}::line {line}", None)


def owner_of(frame: FrameType) -> FrameType:
    """The outermost frame of the chain of calls written under `tests/` that `frame` runs in."""
    while frame.f_back is not None and under_tests(frame.f_back.f_code.co_filename):
        frame = frame.f_back
    return frame


def site_name(place: Place, frame: FrameType) -> str:
    """The place's name where its owner wrote it, and otherwise the owner and the call it is in, which tells
    two calls of one helper from one owner apart."""
    owner_frame = owner_of(frame)
    owner = f"{relative(owner_frame.f_code.co_filename)}::{owner_frame.f_code.co_qualname}"
    if place.name.startswith(owner + "::"):
        return place.name
    call = place_at(owner_frame.f_code, owner_frame.f_lasti).name
    return f"{owner} > {call.removeprefix(owner + '::')} > {place.name}"


def key_of(value: object) -> str:
    """A value of `sampled_from` as a cut names it: its `repr` without a memory address, or a function's or
    class's qualified name; a long one cut short, with a digest of the whole."""
    if inspect.isfunction(value) or inspect.isclass(value) or inspect.ismethod(value):
        text = f"{getattr(value, '__module__', '')}.{getattr(value, '__qualname__', '')}"
    else:
        text = re.sub(r" at 0x[0-9a-fA-F]+", "", repr(value))
    if len(text) <= KEY_LENGTH:
        return text
    return f"{text[: KEY_LENGTH - 12]}…{hashlib.sha256(text.encode()).hexdigest()[:10]}"


def unique(keys: list[str]) -> list[str]:
    """Keys that name two values alike told apart by the values' places in the call."""
    counts = Counter(keys)
    return [f"{key} #{index}" if counts[key] > 1 else key for index, key in enumerate(keys)]


def option_keys(count: int, texts: tuple[str, ...] | None) -> list[str]:
    labels = (
        list(texts) if texts is not None and len(texts) == count else [f"#{index}" for index in range(count)]
    )
    return unique([shortened(label, KEY_LENGTH) for label in labels])


@dataclass
class Seen:
    """What the calls at one site drew from: `keys` counts the calls drawing each value or option beside
    others and `lone` those drawing it alone; `ends` the calls with each end of a range bounded and the range
    wider than a point, and those with an end unbounded (`no low`, `no high`); `sizes` the calls whose size
    can move off each end, and those of two sizes alone (`pair`)."""

    kind: str
    contexts: set[str] = field(default_factory=set[str])
    calls: int = 0
    keys: dict[str, int] = field(default_factory=dict[str, int])
    lone: dict[str, int] = field(default_factory=dict[str, int])
    ends: dict[str, int] = field(default_factory=dict[str, int])
    sizes: dict[str, int] = field(default_factory=dict[str, int])

    def json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "contexts": sorted(self.contexts),
            "calls": self.calls,
            "keys": self.keys,
            "lone": self.lone,
            "ends": self.ends,
            "sizes": self.sizes,
        }


def counted(table: dict[str, int], key: str) -> None:
    table[key] = table.get(key, 0) + 1


@dataclass
class Cut:
    site: str
    change: str
    key: str | None
    effects: dict[str, int] = field(default_factory=lambda: {"applied": 0, "unchanged": 0, "empty": 0})

    def reaches(self, place: Place) -> bool:
        return self.site == place.name or self.site.endswith(" > " + place.name)


@dataclass
class Call:
    """One call of a constructor: its arguments as given, and by name (`arguments`) where a cut reads them."""

    kind: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    arguments: dict[str, Any]
    options: tuple[str, ...] | None

    def keys(self) -> list[str]:
        if self.kind == "booleans":
            return ["True", "False"]
        if self.kind == "sampled_from":
            return unique([key_of(value) for value in self.arguments["elements"]])
        return option_keys(len(self.args), self.options)

    def ends(self) -> tuple[Any, Any]:
        """The least and the greatest value a range can draw, None where unbounded."""
        low, high = self.arguments.get("min_value"), self.arguments.get("max_value")
        if self.kind == "floats":
            if low is not None and self.arguments.get("exclude_min"):
                low = math.nextafter(low, math.inf)
            if high is not None and self.arguments.get("exclude_max"):
                high = math.nextafter(high, -math.inf)
        return low, high

    def sizes(self) -> tuple[int, int | None]:
        return self.arguments.get("min_size") or 0, self.arguments.get("max_size")


class State:
    out: Path | None = None
    cut: Cut | None = None
    seen: dict[str, Seen] = {}  # noqa: RUF012 (the one state of a process)
    reported: list[dict[str, object]] = []  # noqa: RUF012
    effects_written: dict[str, int] | None = None
    held = False
    config: pytest.Config | None = None
    session: pytest.Session | None = None


ORIGINALS: dict[str, Callable[..., Strategy]] = {}
SIGNATURES: dict[str, inspect.Signature] = {}


def record(site: str, call: Call) -> None:
    seen = State.seen.get(site)
    if seen is None:
        seen = State.seen[site] = Seen(call.kind)
    seen.calls += 1
    seen.contexts.add("draw" if currently_in_test_context() else "import")
    kind = call.kind
    if kind in VALUES or kind in OPTIONS:
        distinct = set(call.keys())
        for key in distinct:
            counted(seen.lone if len(distinct) == 1 else seen.keys, key)
    elif kind in RANGES:
        low, high = call.ends()
        if low is None and high is None:
            counted(seen.ends, "unbounded")
        elif low is None or high is None or low < high:
            for end, value in (("low", low), ("high", high)):
                counted(seen.ends, end if value is not None else f"no {end}")
            if kind == "integers" and low is not None and high is not None and high - low == 1:
                # Two values: keeping off one end is pinning to the other.
                counted(seen.ends, "pair")
    elif kind in SIZES:
        least, greatest = call.sizes()
        if greatest is None or least < greatest:
            counted(seen.sizes, "least")
            if greatest is not None:
                counted(seen.sizes, "greatest")
                if greatest - least == 1:
                    # Two sizes: keeping off one is holding to the other.
                    counted(seen.sizes, "pair")
    elif kind in ORDERS and len(list(call.arguments["values"])) > 1:
        counted(seen.keys, "order")


def cut_strategy(call: Call, cut: Cut, original: Callable[..., Strategy]) -> tuple[Strategy | None, str]:
    """The strategy the cut makes of this call, None where it makes none, and its effect."""
    just = ORIGINALS["just"]
    kind, change = call.kind, cut.change
    if change == "drop":
        if kind == "booleans":
            return just(cut.key != "True"), "applied"
        values = list(call.arguments["elements"]) if kind == "sampled_from" else list(call.args)
        kept = [value for value, key in zip(values, call.keys(), strict=True) if key != cut.key]
        if len(kept) == len(values):
            return None, "unchanged"
        if not kept:
            return None, "empty"
        if kind == "sampled_from":
            return original(kept), "applied"
        return (kept[0] if kind == "|" else original(*kept)), "applied"
    if kind in RANGES:
        low, high = call.ends()
        end = low if change.endswith("low") else high
        if end is None:
            return None, "unchanged"
        if change.startswith("pin"):
            return just(float(end) if kind == "floats" else end), "applied"
        if low is not None and high is not None and low >= high:
            return None, "empty"
        lower = change == "off_low"
        kept_off = dict(call.arguments)
        if kind == "integers":
            kept_off["min_value" if lower else "max_value"] = end + 1 if lower else end - 1
        else:
            kept_off["min_value" if lower else "max_value"] = end
            kept_off["exclude_min" if lower else "exclude_max"] = True
        return original(**kept_off), "applied"
    if kind in SIZES:
        least, greatest = call.sizes()
        lower = change in ("least_size", "off_least")
        size = least if lower else greatest
        if size is None:
            return None, "unchanged"
        moved_off = change.startswith("off")
        if greatest is not None and least >= greatest:
            return None, "empty" if moved_off else "unchanged"
        if moved_off:
            bound = {"min_size": least + 1} if lower else {"max_size": size - 1}
            return original(**{**call.arguments, **bound}), "applied"
        return original(**{**call.arguments, "min_size": size, "max_size": size}), "applied"
    values = list(call.arguments["values"])
    if len(values) < 2:
        return None, "unchanged"
    return just(values), "applied"


def constructed(kind: str, frame: FrameType, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Strategy:
    """What the wrapper of `kind` returns where the plugin records or cuts: the constructor's strategy,
    recorded, or the cut's."""
    original = ORIGINALS[kind]
    if not under_tests(frame.f_code.co_filename):
        return original(*args, **kwargs)
    if kind in OPTIONS and len(args) == 1 and not isinstance(args[0], SearchStrategy):
        args = tuple(args[0])
    place = place_at(frame.f_code, frame.f_lasti)
    cut = State.cut
    if cut is not None and not cut.reaches(place):
        return original(*args, **kwargs)
    site = site_name(place, frame)
    if kind not in CUTTABLE:
        if cut is None:
            record_uncut(site, kind)
        return original(*args, **kwargs)
    arguments = {} if kind in OPTIONS else dict(SIGNATURES[kind].bind(*args, **kwargs).arguments)
    call = Call(kind, args, kwargs, arguments, place.options)
    if cut is None:
        record(site, call)
        return original(*args, **kwargs)
    if site != cut.site or kind not in CHANGES[cut.change]:
        return original(*args, **kwargs)
    strategy, effect = cut_strategy(call, cut, original)
    cut.effects[effect] += 1
    return original(*args, **kwargs) if strategy is None else strategy


def record_uncut(site: str, kind: str) -> None:
    seen = State.seen.get(site)
    if seen is None:
        seen = State.seen[site] = Seen(kind)
    seen.calls += 1
    seen.contexts.add("draw" if currently_in_test_context() else "import")


def wrapped(name: str, original: Callable[..., Strategy]) -> Callable[..., Strategy]:
    @functools.wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Strategy:
        if State.out is None or name in DRAW_NOTHING:
            return original(*args, **kwargs)
        if name == "fixed_dictionaries" and not kwargs.get("optional"):
            return original(*args, **kwargs)
        return constructed(name, sys._getframe(1), args, kwargs)  # pyright: ignore[reportPrivateUsage]

    return wrapper


def install() -> None:
    for name in strategies.__all__:
        original: Callable[..., Strategy] = getattr(strategies, name)
        if name in NOT_CONSTRUCTORS or inspect.isclass(original) or not callable(original):
            continue
        ORIGINALS[name] = original
        if name in CUTTABLE:
            SIGNATURES[name] = inspect.signature(original)
        setattr(strategies, name, wrapped(name, original))
    union = SearchStrategy.__or__
    ORIGINALS["|"] = union

    def either(self: Strategy, other: Strategy) -> Strategy:
        if State.out is None:
            return union(self, other)
        return constructed("|", sys._getframe(1), (self, other), {})  # pyright: ignore[reportPrivateUsage]

    SearchStrategy.__or__ = either  # type: ignore[method-assign]


install()


def random_calls(module: object) -> list[str]:
    """The places a module under `tests/` calls a function of `random` or makes a `Random`."""
    filename = getattr(module, "__file__", None)
    if not isinstance(filename, str) or not filename.endswith(".py"):
        return []
    filename = str(Path(filename).resolve())
    if not under_tests(filename):
        return []
    return [place.name for place in places(filename).values() if place.random]


def worker() -> str:
    return os.environ.get("PYTEST_XDIST_WORKER", "main")


def process_name() -> str:
    return f"{worker()}-{os.getpid()}"


def worker_of(report: pytest.TestReport | pytest.CollectReport) -> str:
    """The worker that ran a report's test: xdist's controller names it on the report it receives."""
    node = getattr(report, "node", None)
    workerinput: object = getattr(node, "workerinput", None)
    if isinstance(workerinput, dict):
        name = cast(dict[str, object], workerinput).get("workerid")
        if isinstance(name, str):
            return name
    return worker()


def write(name: str, content: object) -> None:
    assert State.out is not None
    path = State.out / name
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(content, indent=1, sort_keys=True), encoding="utf-8")
    partial.replace(path)


def write_effects() -> None:
    cut = State.cut
    if cut is not None and cut.effects != State.effects_written:
        State.effects_written = dict(cut.effects)
        write(f"effects-{process_name()}.json", cut.effects)


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("input coverage", "cuts of the draws (tests/property/input_coverage.py)")
    group.addoption("--input-coverage-out", metavar="DIR", help="run derandomized, recording into DIR")
    group.addoption("--input-coverage-cut", metavar="CUT", help="the cut to apply, a JSON object")


def pytest_configure(config: pytest.Config) -> None:
    out = config.getoption("--input-coverage-out")
    text = config.getoption("--input-coverage-cut")
    if out is None:
        if text is not None:
            raise pytest.UsageError("--input-coverage-cut needs --input-coverage-out")
        return
    State.out = Path(out)
    State.out.mkdir(parents=True, exist_ok=True)
    if text is not None:
        given = json.loads(text)
        if given.get("change") not in CHANGES:
            raise pytest.UsageError(f"--input-coverage-cut: the change is one of {sorted(CHANGES)}")
        State.cut = Cut(given["site_id"], given["change"], given.get("key"))
    # The profile loaded, derandomized and with no example database, under its own name, which the tests read
    # (`strategies.SIZE`): a run with a cut draws what the run without it drew up to the cut, and stores
    # nothing a later run would replay. Under a cut, a failing example is neither shrunk nor explained: the
    # draws that find it are the same, and only a person reading it needs it small.
    loaded = settings()
    # Hypothesis leaves its settings' properties unannotated.
    kept = cast(Sequence[Phase], loaded.phases)  # pyright: ignore[reportUnknownMemberType]
    phases = [phase for phase in kept if State.cut is None or phase not in AFTER_A_FAILURE]
    profile = settings.get_current_profile_name()
    settings.register_profile(profile, parent=loaded, derandomize=True, database=None, phases=phases)
    settings.load_profile(profile)


def pytest_sessionstart(session: pytest.Session) -> None:
    State.session = session
    State.config = session.config


def reporting() -> bool:
    return State.out is not None and State.config is not None and not hasattr(State.config, "workerinput")


def failed(test: str, when: str, text: str, message: str, process: str) -> None:
    assert State.out is not None
    invalid = INVALID.search(text) is not None
    State.reported.append(
        {
            "test": test,
            "when": when,
            "message": shortened(message, 2000),
            "invalid": invalid,
            "process": process,
        }
    )
    write("outcome.json", {"finished": False, "failures": State.reported})
    if not invalid and not State.held:
        State.held = True
        (State.out / "held").write_text(test, encoding="utf-8")
        stop(f"input coverage: {test} failed")


def stop(reason: str) -> None:
    assert State.config is not None
    dsession = State.config.pluginmanager.getplugin("dsession")
    if dsession is not None:
        # xdist's controller stops starting tests once its `shouldstop` is set.
        setattr(dsession, "shouldstop", reason)  # noqa: B010
    elif State.session is not None:
        State.session.shouldstop = reason


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    # A worker writes its effects before it sends the report on: the run may be stopped once it is read.
    write_effects()
    if reporting() and report.failed:
        crash = getattr(report.longrepr, "reprcrash", None)
        message = getattr(crash, "message", None) or (report.longreprtext.strip().splitlines() or [""])[-1]
        failed(report.nodeid, report.when, report.longreprtext, message, worker_of(report))


@pytest.hookimpl(tryfirst=True)
def pytest_collectreport(report: pytest.CollectReport) -> None:
    if reporting() and report.failed:
        text = report.longreprtext
        failed(report.nodeid or "collection", "collect", text, text, worker_of(report))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if State.out is None:
        return
    write_effects()
    if State.cut is None:
        calls = sorted({call for module in list(sys.modules.values()) for call in random_calls(module)})
        sites = {site: seen.json() for site, seen in State.seen.items()}
        write(f"sites-{process_name()}.json", {"sites": sites, "random": calls})
    if reporting():
        write("outcome.json", {"finished": True, "exit": int(exitstatus), "failures": State.reported})
