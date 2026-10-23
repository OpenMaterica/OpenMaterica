# SPDX-License-Identifier: Apache-2.0
"""Whether the tests hold every draw: each cut of a selection's draws run as its own pytest process, and the
cuts no test holds compared with the baseline (`tests/property/README.md`, "Every draw is held").

A selection is a set of tests and the sites whose draws they are to hold: a name in the baseline
(`tests/property/input_coverage_baseline.json`), or `--tests` and `--sites` given here. The tests run with
the plugin `tests/property/input_coverage.py` (`-p`), at the profile given (`ci` unless `--profile`),
derandomized, with `PYTHONHASHSEED=0`, `-n WORKERS --dist worksteal`.

- `list` runs the selection once with no cut, recording the sites it reaches; that run must pass. It prints
  each site the `--sites` patterns match (`fnmatch` on its name) with its cuts, and each draw it cannot cut.
- `run` does the same, then runs each cut as its own process, `--parallel` at a time, stopping at the first
  test that fails (the plugin stops pytest; this script ends the process group at once), and records each
  cut's result in the report (`--report`, JSON, written after each cut): `held` (the first test that failed,
  and its message), `not held`, `invalid` (every failure an invalid draw: no valid example, a health check,
  the draws' rejection audit), `empty` (every call the cut reached would have had nothing left to draw),
  `not applied` (no call reached) or `error` (a failure with the cut applied nowhere, a time out, or no
  outcome). Given a report that holds results, it runs only the cuts without one, or of those only the ones
  `--only` patterns match; with `--budget SECONDS`, it starts no cut once that much time has gone. It exits 2
  while cuts are left.
- `check` compares a finished report with the baseline: it exits 1, naming each, on a cut not held that the
  baseline does not list with that result, a cut the baseline lists that is now held or no longer made, a
  draw it cannot cut that the baseline does not list, and a baseline entry for one no longer drawn. `run`
  ends with the same check once every cut has run.

The cuts of a site (`cuts_of`): each value of `sampled_from` and `booleans`, and each option of `one_of` and
`|`, dropped in turn; a range of `integers` or `floats` pinned to each bounded end and kept off it; a list,
set or dictionary held to its least size and to its greatest, where it has one; a permutation held to the
order given. A value only ever drawn alone at its calls makes a cut that is `empty` without a run. A site of
more than `MOST_VALUES` values or options is listed as uncut ("computed values"): a person checks it.
"""

import argparse
import fnmatch
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tests" / "property" / "input_coverage_baseline.json"
PLUGIN = "tests.property.input_coverage"
PROFILE_VARIABLE = "MATERICA_HYPOTHESIS_PROFILE"
MOST_VALUES = 24
RESULTS = ("held", "not held", "invalid", "empty", "not applied", "error")
# What a baseline entry's reason begins with: a gap a test should hold, or a cut no test can tell apart from
# the draw it cut.
REASONS = ("a gap: ", "equivalent: ")
DESCRIBED = {
    "pin_low": "pin to the low end",
    "off_low": "keep off the low end",
    "pin_high": "pin to the high end",
    "off_high": "keep off the high end",
    "least_size": "hold to the least size",
    "greatest_size": "hold to the greatest size",
    "identity_order": "hold to the order given",
}
Json = dict[str, Any]


def cut_name(site: str, change: str, key: str | None) -> str:
    return f"{site} :: " + (f"drop {key}" if change == "drop" else DESCRIBED[change])


def cuts_of(site: str, seen: Json) -> tuple[list[Json], str | None]:
    """The cuts of a site from what its calls drew from, or the reason it is uncut."""
    kind = seen["kind"]
    keys, lone, ends, sizes = seen["keys"], seen["lone"], seen["ends"], seen["sizes"]
    cuts: list[Json] = []
    if kind in ("sampled_from", "booleans", "one_of", "|"):
        values = sorted(set(keys) | set(lone))
        if len(values) > MOST_VALUES:
            return [], f"computed values: {len(values)} across its calls"
        for key in values:
            cuts.append({"site_id": site, "change": "drop", "key": key, "empty": key not in keys})
    elif kind in ("integers", "floats"):
        if not ends:
            return [], None
        if set(ends) == {"unbounded"}:
            return [], "unbounded"
        # Where every bounded call draws one of two integers, keeping off one end is pinning to the other.
        ways = (
            ("pin",) if ends.get("pair", 0) == ends.get("low", 0) == ends.get("high", 0) else ("pin", "off")
        )
        for end in ("low", "high"):
            if end in ends:
                cuts += [{"site_id": site, "change": f"{way}_{end}", "key": None} for way in ways]
    elif kind in ("lists", "sets", "frozensets", "dictionaries"):
        cuts += [
            {"site_id": site, "change": f"{end}_size", "key": None}
            for end in ("least", "greatest")
            if end in sizes
        ]
    elif kind == "permutations":
        if keys:
            cuts.append({"site_id": site, "change": "identity_order", "key": None})
    else:
        return [], kind
    for cut in cuts:
        cut["name"] = cut_name(site, cut["change"], cut["key"])
    return cuts, None


def merged(out: Path) -> tuple[dict[str, Json], list[str]]:
    """The sites every process of a run recorded, their counts summed, and the calls of plain `random`."""
    sites: dict[str, Json] = {}
    randoms: set[str] = set()
    for path in sorted(out.glob("sites-*.json")):
        recorded = json.loads(path.read_text(encoding="utf-8"))
        randoms.update(recorded["random"])
        for site, seen in recorded["sites"].items():
            into = sites.setdefault(
                site,
                {
                    "kind": seen["kind"],
                    "contexts": [],
                    "calls": 0,
                    "keys": {},
                    "lone": {},
                    "ends": {},
                    "sizes": {},
                },
            )
            into["contexts"] = sorted(set(into["contexts"]) | set(seen["contexts"]))
            into["calls"] += seen["calls"]
            for table in ("keys", "lone", "ends", "sizes"):
                for key, count in seen[table].items():
                    into[table][key] = into[table].get(key, 0) + count
    return sites, sorted(randoms)


def pytest_command(tests: Sequence[str], out: Path, workers: int, cut: Json | None) -> list[str]:
    command = [sys.executable, "-m", "pytest", *tests, "-p", PLUGIN, "--input-coverage-out", str(out)]
    if cut is not None:
        command += [
            "--input-coverage-cut",
            json.dumps({key: cut[key] for key in ("site_id", "change", "key")}),
        ]
    command += ["-q", "--tb=short", "-p", "no:cacheprovider"]
    if workers > 0:
        command += ["-n", str(workers), "--dist", "worksteal"]
    return command


def run_pytest(
    command: list[str], out: Path, profile: str, timeout: float, root: Path
) -> tuple[Json | None, float]:
    """Runs pytest in its own process group, ending it once a failure that holds the cut is recorded, and
    returns the run's outcome and its time."""
    # String hashing fixed, so that every process iterates a set of strings alike: a value's name, its `repr`,
    # is then the same in the run that records it and in the run that cuts it.
    environment = {**os.environ, PROFILE_VARIABLE: profile, "PYTHONHASHSEED": "0"}
    started = time.monotonic()
    with (out / "pytest.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command, cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        RUNNING.add(process)
        while process.poll() is None:
            if (out / "held").exists() or time.monotonic() - started > timeout:
                end_group(process)
                break
            time.sleep(0.5)
        RUNNING.discard(process)
    seconds = time.monotonic() - started
    outcome = out / "outcome.json"
    return (json.loads(outcome.read_text(encoding="utf-8")) if outcome.exists() else None), seconds


# The pytest processes running, each in a process group of its own, which a signal to this script would
# otherwise leave running: `ended` ends them first.
RUNNING: set["subprocess.Popen[bytes]"] = set()


def ended(number: int, _: object) -> None:
    for process in list(RUNNING):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    raise SystemExit(128 + number)


def end_group(process: "subprocess.Popen[bytes]") -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    except ProcessLookupError:
        process.wait()


def effects_of(out: Path) -> dict[str, int]:
    effects = {"applied": 0, "unchanged": 0, "empty": 0}
    for path in out.glob("effects-*.json"):
        for key, count in json.loads(path.read_text(encoding="utf-8")).items():
            effects[key] += count
    return effects


def result_of(outcome: Json | None, effects: dict[str, int], timed_out: bool) -> Json:
    """A cut's result from its run's outcome and the effects its processes recorded."""
    failures: list[Json] = [] if outcome is None else outcome["failures"]
    holding = [failure for failure in failures if not failure["invalid"]]
    if holding:
        first = holding[0]
        if effects["applied"] == 0:
            return {
                "result": "error",
                "test": first["test"],
                "message": "failed, though the cut changed no call: " + first["message"],
            }
        return {"result": "held", "test": first["test"], "message": first["message"]}
    if outcome is None or not outcome.get("finished") or timed_out:
        return {"result": "error", "message": "timed out" if timed_out else "the run ended with no outcome"}
    if failures:
        return {"result": "invalid", "test": failures[0]["test"], "message": failures[0]["message"]}
    if effects["applied"] == 0:
        return {"result": "empty" if effects["empty"] else "not applied"}
    return {"result": "not held"}


def recorded(args: argparse.Namespace, selection: Json, report: Json) -> bool:
    """The run with no cut, recorded into the report: False where it failed."""
    with tempfile.TemporaryDirectory(prefix="input-coverage-") as directory:
        out = Path(directory)
        command = pytest_command(selection["tests"], out, args.workers, None)
        outcome, seconds = run_pytest(command, out, args.profile, args.timeout, args.root)
        if outcome is None or outcome["failures"] or outcome.get("exit") != 0:
            print((out / "pytest.log").read_text(encoding="utf-8")[-4000:])
            print("input coverage: the selection fails with no cut; nothing to compare a cut with")
            return False
        sites, randoms = merged(out)
    report["record_seconds"] = round(seconds, 1)
    report["sites"], report["uncut"], report["cuts"] = {}, {}, {}
    for site, seen in sorted(sites.items()):
        if not any(fnmatch.fnmatchcase(site, pattern) for pattern in selection["sites"]):
            continue
        cuts, uncut = cuts_of(site, seen)
        if uncut is not None:
            report["uncut"][site] = uncut
        if cuts:
            report["sites"][site] = {
                "kind": seen["kind"],
                "calls": seen["calls"],
                "contexts": seen["contexts"],
            }
        for cut in cuts:
            report["cuts"][cut.pop("name")] = cut
    for call in randoms:
        if any(fnmatch.fnmatchcase(call, pattern) for pattern in selection["sites"]):
            report["uncut"][call] = "random"
    made: dict[str, Json] = report["cuts"]
    for cut in made.values():
        if cut.pop("empty", False):
            cut.update(result="empty", seconds=0.0)
    return True


def run_cut(args: argparse.Namespace, selection: Json, cut: Json) -> Json:
    """One cut's run, in a process of its own, and its result."""
    with tempfile.TemporaryDirectory(prefix="input-coverage-") as directory:
        out = Path(directory)
        command = pytest_command(selection["tests"], out, args.workers, cut)
        outcome, seconds = run_pytest(command, out, args.profile, args.timeout, args.root)
        effects = effects_of(out)
    return {
        **result_of(outcome, effects, seconds > args.timeout),
        "seconds": round(seconds, 1),
        "effects": effects,
    }


def run_cuts(args: argparse.Namespace, selection: Json, report: Json, path: Path) -> int:
    """Each cut not yet run, `--parallel` at a time, the report written after each; 2 where the budget ran
    out first."""
    started = time.monotonic()
    patterns = args.only or ["*"]
    waiting = [
        name
        for name, cut in report["cuts"].items()
        if "result" not in cut and any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)
    ]
    running: dict[Future[Json], str] = {}
    with ThreadPoolExecutor(args.parallel) as pool:
        while waiting or running:
            spent = args.budget is not None and time.monotonic() - started > args.budget
            while waiting and len(running) < args.parallel and not spent:
                name = waiting.pop(0)
                running[pool.submit(run_cut, args, selection, report["cuts"][name])] = name
            if not running:
                break
            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in done:
                name = running.pop(future)
                cut = report["cuts"][name]
                cut.update(future.result())
                print(f"{cut['result']:>11}  {cut['seconds']:6.1f} s  {name}", flush=True)
                write(path, report)
    left = sum("result" not in cut for cut in report["cuts"].values())
    if left:
        print(f"input coverage: {left} cuts left, by the budget or `--only`; run again to go on")
        return 2
    return 0


def problems(report: Json, entry: Json) -> list[str]:
    """Where a finished report and the selection's baseline disagree."""
    found: list[str] = []
    listed: dict[str, Json] = entry.get("cuts", {})
    for name, cut in report["cuts"].items():
        result = cut.get("result")
        if result is None:
            found.append(f"not run: {name}")
        elif result == "held":
            if name in listed:
                found.append(f"now held, so the baseline drops it: {name} ({cut['test']})")
        elif name not in listed:
            found.append(f"{result}, and not in the baseline: {name}")
        elif listed[name]["result"] != result:
            found.append(f"{result}, the baseline says {listed[name]['result']}: {name}")
    for name, cut in listed.items():
        if name not in report["cuts"]:
            found.append(f"in the baseline, no longer cut: {name}")
        if not cut.get("reason", "").startswith(REASONS) or cut.get("result") not in RESULTS[1:]:
            found.append(f"a baseline entry needs a result not held and a reason beginning {REASONS}: {name}")
    uncut: dict[str, str] = entry.get("uncut", {})
    for site, why in report["uncut"].items():
        if site not in uncut:
            found.append(f"uncut ({why}), and not in the baseline: {site}")
    for site, note in uncut.items():
        if site not in report["uncut"]:
            found.append(f"in the baseline as uncut, no longer drawn uncut: {site}")
        if not note.strip():
            found.append(f"an uncut site needs a person's note: {site}")
    return found


def write(path: Path, report: Json) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    partial.replace(path)


def selection_of(args: argparse.Namespace) -> tuple[Json, Json]:
    """The selection's tests and site patterns, and its baseline entry (empty for one given here)."""
    source = Path(args.baseline)
    baseline = cast(Json, json.loads(source.read_text(encoding="utf-8"))) if source.exists() else {}
    if args.name is not None:
        if args.name not in baseline:
            raise SystemExit(
                f"input coverage: no selection {args.name!r} in {args.baseline}: {sorted(baseline)}"
            )
        entry = baseline[args.name]
        return {"name": args.name, "tests": entry["tests"], "sites": entry["sites"]}, entry
    if not args.tests or not args.sites:
        raise SystemExit("input coverage: name a selection of the baseline, or give --tests and --sites")
    return {"name": None, "tests": args.tests, "sites": args.sites}, {}


def summary(report: Json) -> str:
    counts: dict[str, int] = {}
    for cut in report["cuts"].values():
        counts[cut.get("result", "not run")] = counts.get(cut.get("result", "not run"), 0) + 1
    return (
        f"{len(report['sites'])} sites, {len(report['cuts'])} cuts ("
        + ", ".join(f"{result} {count}" for result, count in sorted(counts.items()))
        + f"), {len(report['uncut'])} uncut"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    parser.add_argument("command", choices=("list", "run", "check"))
    parser.add_argument("name", nargs="?", help="a selection of the baseline")
    parser.add_argument("--tests", nargs="+", help="the pytest arguments that select the tests")
    parser.add_argument("--sites", nargs="+", help="fnmatch patterns of the sites to cut")
    parser.add_argument("--baseline", default=str(BASELINE))
    parser.add_argument("--report", help="the report, JSON: read where it exists, and written")
    parser.add_argument("--profile", default="ci")
    parser.add_argument("--workers", type=int, default=8, help="pytest-xdist workers a run")
    parser.add_argument("--parallel", type=int, default=1, help="cuts run at once")
    parser.add_argument("--budget", type=float, help="seconds after which no cut is started")
    parser.add_argument("--only", nargs="+", help="run only the cuts whose names these patterns match")
    parser.add_argument("--timeout", type=float, default=1800.0, help="seconds a run may take")
    parser.add_argument("--root", type=Path, default=ROOT, help="the tree whose tests run")
    args = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, ended)
    signal.signal(signal.SIGINT, ended)
    selection, entry = selection_of(args)
    path = Path(args.report) if args.report else None
    report: Json = {}
    if path is not None and path.exists():
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("selection") != selection or report.get("profile") != args.profile:
            raise SystemExit(f"input coverage: {path} is a report of another selection or profile")
    if args.command == "check":
        if not report:
            raise SystemExit("input coverage: check needs a --report")
    elif "sites" not in report:
        report = {"selection": selection, "profile": args.profile, "root": str(args.root)}
        if not recorded(args, selection, report):
            return 1
        if path is not None:
            write(path, report)
    if args.command == "list":
        for site in report["sites"]:
            print(site)
            for name in (name for name, cut in report["cuts"].items() if cut["site_id"] == site):
                print(f"    {name.rpartition(' :: ')[2]}")
        for site, why in report["uncut"].items():
            print(f"uncut ({why}): {site}")
        print(summary(report))
        return 0
    if args.command == "run":
        if path is None:
            raise SystemExit("input coverage: run needs a --report to write")
        left = run_cuts(args, selection, report, path)
        if left:
            return left
    found = problems(report, entry)
    for problem in found:
        print(problem)
    print(summary(report))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
