# SPDX-License-Identifier: Apache-2.0
"""Parts of a pytest run: the tests it selects, split into parts that run side by side in jobs of their own.

CI runs the `tests` job in two parts, the `controls` job in four on Python 3.11 and two on 3.15, and four of
the Hypothesis job's shards (`agreement`, `relations`, `alternatives`, `build`) in two (`--shard
agreement_1of2`). Each part runs `--partition I/N`, the I-th of N parts of what the other selection options
leave. The parts of one selection are a partition: every selected test is in exactly one, whatever the
weights, because every part computes the same assignment of every selected test and keeps its own
(`parts_of`). `tests/unit/test_partition.py` holds that, with controls that fail where a test is in none or in
two, and `tests/unit/test_ci_workflows.py` holds it for the parts CI's matrices run, on the tests they really
collect.

The weights decide only how even the parts are, never which tests run. Each is the seconds a test took in a CI
run, in `partition_weights.json`, which `python -m tests.partition` writes from such a run's JUnit reports; a
test it does not list weighs `DEFAULT_SECONDS`. The assignment gives the heaviest test left to the lightest
part (longest processing time first), so a weight that is stale or missing makes parts uneven and loses no
test.

    python -m tests.partition PROFILE SOURCE REPORT ...    # record these reports' tests in PROFILE's table

`SOURCE` says where the reports are from (a CI run), and is kept beside the table under `sources`. A test file
the reports hold has its entries replaced by what they show, and a file they do not hold keeps its entries, so
that the reports of one job do not drop the weights of another's. Within a file the reports are taken as
complete: give every part of every job that runs it, or the tests of the missing parts lose their weights.

Maintaining the weights. A test that is not listed weighs `DEFAULT_SECONDS`, so a new test costs nothing
until a run lists it, and a renamed or moved long test silently weighs the default; the parts then drift
from even. Record again when a part of a CI run takes visibly longer than the others (the durations reports,
one per part: `durations-tests-3.15-1of2`, `durations-controls-3.15-1of2`,
`durations-hypothesis-agreement_1of2`), or after adding or moving long tests. Take the reports of one CI run
on one Python, 3.15, the one on which the trace test runs: for `dev`, all parts of the `tests` job and of
the `controls` job; for `ci`, all parts of the Hypothesis job's shards of a run at the `ci` profile (not
`deep`, which has ten times the examples).
"""

import heapq
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

WEIGHTS_FILE = Path(__file__).resolve().parent / "partition_weights.json"
# What a test the table does not list weighs, in seconds: about the mean of the tests it leaves out.
DEFAULT_SECONDS = 0.05
# A test is listed from this many seconds: the lighter ones are many and even, and weigh the default.
LISTED_FROM_SECONDS = 1.0
# The tables, by the profile a run loads: `deep` runs the properties at ten times `ci`'s examples, in the same
# proportions.
TABLE_OF_PROFILE = {"dev": "dev", "ci": "ci", "deep": "ci"}

PART = re.compile(r"(?P<index>[1-9][0-9]*)/(?P<count>[1-9][0-9]*)")
# A shard of the Hypothesis job in parts: `agreement_1of2`.
SHARD_PART = re.compile(r"(?P<name>[a-z0-9_]+?)_(?P<index>[1-9][0-9]*)of(?P<count>[1-9][0-9]*)")


def parse_part(text: str) -> tuple[int, int]:
    """`I/N` as (I, N), I from 1 to N."""
    found = PART.fullmatch(text)
    if found is None or int(found["index"]) > int(found["count"]):
        raise ValueError(f"{text!r} is not I/N with I from 1 to N")
    return int(found["index"]), int(found["count"])


def split_shard(text: str) -> tuple[str, tuple[int, int] | None]:
    """A shard's name and, where it is one part of the shard, which part: `agreement_1of2` is ("agreement",
    (1, 2)). `1of1` is no part; a name that ends so is not read as one."""
    found = SHARD_PART.fullmatch(text)
    if found is None or int(found["index"]) > int(found["count"]) or found["count"] == "1":
        return text, None
    return found["name"], (int(found["index"]), int(found["count"]))


def parts_of(nodeids: Sequence[str], count: int, weights: Mapping[str, float]) -> list[int]:
    """The part, from 0, of each test: the heaviest test left goes to the lightest part. Ties go to the lower
    part, equal weights in the order of the node ids, so that the same tests always come out the same."""
    if count < 1:
        raise ValueError(f"{count} parts")
    order = sorted(
        range(len(nodeids)),
        key=lambda position: (-weights.get(nodeids[position], DEFAULT_SECONDS), nodeids[position], position),
    )
    loads = [(0.0, part) for part in range(count)]
    heapq.heapify(loads)
    assigned = [0] * len(nodeids)
    for position in order:
        load, part = heapq.heappop(loads)
        assigned[position] = part
        heapq.heappush(loads, (load + weights.get(nodeids[position], DEFAULT_SECONDS), part))
    return assigned


def in_part(nodeids: Sequence[str], part: tuple[int, int], weights: Mapping[str, float]) -> list[bool]:
    """Whether each test is in part I of N."""
    index, count = part
    return [assigned == index - 1 for assigned in parts_of(nodeids, count, weights)]


def weights_for(profile: str, file: Path = WEIGHTS_FILE) -> dict[str, float]:
    table: dict[str, float] = json.loads(file.read_text(encoding="utf-8"))[TABLE_OF_PROFILE[profile]]
    return table


# --- recording the weights from a run -----------------------------------------------------------------------


def node_id(classname: str, name: str, root: Path) -> str:
    """The node id of a JUnit test case: the longest prefix of its class name that is a file under `root` is
    the path, and what follows is the classes the test sits in."""
    parts = classname.split(".")
    for end in range(len(parts), 0, -1):
        path = "/".join(parts[:end]) + ".py"
        if (root / path).is_file():
            return "::".join([path, *parts[end:], name])
    raise ValueError(f"{classname}: no test file of this repository")


def files_in(reports: Iterable[Path], root: Path) -> set[str]:
    """The test files that have a test, skipped or not, in some report."""
    return {
        node_id(case.get("classname", ""), case.get("name", ""), root).split("::")[0]
        for report in reports
        for case in ElementTree.parse(report).iter("testcase")
    }


def seconds_in(reports: Iterable[Path], root: Path) -> dict[str, float]:
    """Each test that ran in some report (a skipped test took no time worth weighing), with the longest it
    took in any of them, from `LISTED_FROM_SECONDS` up, to a tenth of a second."""
    longest: dict[str, float] = {}
    for report in reports:
        for case in ElementTree.parse(report).iter("testcase"):
            if case.find("skipped") is not None:
                continue
            identifier = node_id(case.get("classname", ""), case.get("name", ""), root)
            longest[identifier] = max(longest.get(identifier, 0.0), float(case.get("time", "0")))
    return {
        identifier: round(taken, 1)
        for identifier, taken in sorted(longest.items())
        if taken >= LISTED_FROM_SECONDS
    }


def recorded(
    table: str, source: str, reports: Sequence[Path], file: Path = WEIGHTS_FILE, root: Path | None = None
) -> None:
    """Record the tests of the reports in one table of the weights file, and say where they are from: a test
    file the reports hold has its entries replaced, a file they do not hold keeps its own."""
    found: dict[str, Any] = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    base = root or file.parent.parent
    held = files_in(reports, base)
    kept = {
        identifier: taken
        for identifier, taken in found.get(table, {}).items()
        if identifier.split("::")[0] not in held
    }
    found[table] = dict(sorted({**kept, **seconds_in(reports, base)}.items()))
    sources = found.setdefault("sources", {})
    sources[table] = f"{sources[table]}; {source}" if kept and table in sources else source
    file.write_text(json.dumps(found, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[1] not in ("dev", "ci"):
        sys.exit(__doc__)
    recorded(sys.argv[1], sys.argv[2], [Path(argument) for argument in sys.argv[3:]])
