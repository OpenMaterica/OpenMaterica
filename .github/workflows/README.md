# Workflows

`ci.yml` checks every change. Its opening comment says why it is shaped as it is; this table says what runs,
and `tests/unit/test_ci_workflows.py` holds its jobs and shards to `ci.yml`, with what each pytest command
selects; no job or step carries on after a failure (`continue-on-error`).
`pages.yml` deploys `site/` to openmaterica.org on a push to main that touches it.
`repeat.yml` runs one test many times, each run under a seed of its own, when dispatched by hand (below).
`mutants.yml` runs a branch's hand mutants, each against a pytest selection in a job of its own, and writes
one table of what became of each, when dispatched by hand (below).
`measure.yml` runs the measurements a property piece makes before review as a matrix of jobs, and writes one
table a kind, when dispatched by hand, or as its own self-test on a pull request that changes it (below).
`claims.yml` checks a pull request's description and commit messages against git on every push and every edit of
the description, and prints its figures as advice (below).

| Job | Runs | When |
|---|---|---|
| `gate` | the per-commit jobs' cap, `PER_COMMIT_MAX_PARALLEL` (below); the sign-off check (`scripts/check_signoff.py`) on a pull request, the confidentiality scan, and the known-anomalies registry's check (`scripts/check_anomalies.py`); decides which jobs run: on a pull request from the paths it touched, otherwise every job (no other job with `fuzz_only`) | always |
| `static` | ruff, mypy and pyright; `uv build` and the wheel check; the consumer snippet against the installed wheel, and its control | a pull request that changes code, which is any path the gate lists neither as documentation (`docs_paths` in its step) nor as the site's (`site_paths`: `site/`, `assets/`), and any Python file wherever it sits (`python_paths`), since ruff reads it; every merge to main; weekly; manual |
| `generated` | every generator of `scripts/` with `--check`: the vocabulary, the reader schema, the typed shapes, and the property README's kill counts with the margin guard (`gen_kill_counts.py`); on Python 3.11 | as `static` |
| `tests` | `uv run pytest -n auto`, property tests at the `dev` profile, but the mutant searches and the audit controls (`--property-controls none`), in two parts of about equal time side by side (`--partition 1/2` and `2/2`, `tests/partition.py`) that together hold every test once | as `static`; Python 3.11 to 3.15, in parallel, two jobs each; on 3.15 alone also the pre-review script's trace test (`MATERICA_TRACE_SELECTION=1`, which no other job sets, and which sits in one of the two parts) |
| `controls` | the mutant searches and the audit controls alone (`--property-controls only`), which run at the `ci` profile's examples whatever the profile, so cost about as much as a Python's other tests: on the supported range's ends, the oldest Python and the newest, which bracket the versions between, each in jobs beside that Python's `tests` jobs, so that none is the longest; in parts of about equal time side by side (`--partition`), four on 3.11, the slower interpreter, and two on 3.15, which together hold every one of them once | as `static`; Python 3.11 (four jobs) and 3.15 (two jobs) |
| `kill_points` | after a Python's `controls` jobs: each search's kill point, from the JUnit reports of all that Python's parts together, against `tests/property/kill_points.json` (`gen_kill_counts.py --against`, without `--partial`, so a search that ran in no part fails it); it first counts the reports, so that a part whose report is missing is named as that; a failed `controls` part skips it, so one Python's failing part hides the other's kill-point verdict, and `result` names the failed job | as `static`; Python 3.11 and 3.15 |
| `hypothesis` | the property tests and mutants at the `ci` profile, or `deep` weekly and on a manual run, in eleven jobs side by side (`json`, `records`, `writer`, `agreement_1of2`, `agreement_2of2`, `step8_mutants`, `conditions`, `relations_1of2`, `relations_2of2`, `alternatives_1of2`, `alternatives_2of2`): the eight shards of `SHARDS` in `tests/conftest.py`, the three longest of which, `agreement`, `relations` and `alternatives`, run in two parts of about equal time each (`--shard agreement_1of2`, `tests/partition.py`), the parts together holding every test of the shard once; each job with its own example database; on Python 3.15, a worker per vCPU | a pull request that changes any path but the documentation and those no part of the job reads (`hypothesis_free` in the gate's step), any test included; every merge to main; weekly; manual |
| `site` | the site staged exactly as `pages.yml` stages it (its step, word for word), which fails where a file it copies is missing; then `scripts/check_site.py` on the copy: every local link, image and icon of each page and of the web manifest resolves, every page keeps one content security policy, before anything it loads, that lets nothing load from elsewhere, nothing loads from elsewhere, and the README's images name files of the tree; on the runner's Python, seconds long | a pull request that changes any path but documentation alone, `site/` and `assets/` included, which run this job and no code job; every merge to main; weekly; manual |
| `commit` | each commit of a pull request but its head, checked out on its own: the site job's steps, ruff, mypy and pyright, `uv build` and the wheel check, every generator's `--check` (on Python 3.11, as `generated`) and `freeze_schema.py --check`, then `pytest --collect-only tests` and the specification-sync tests (`tests/spec_sync`), on Python 3.15; the whole suite runs on the head alone (maintainer, 2026-10-21; until then this job ran it on each commit too: "Jobs at once", below); at most `PER_COMMIT_MAX_PARALLEL` at once, 6 where it is unset (below); a commit whose tree passed the same checks earlier in the pull request (kept in the cache under its tree, `ci.yml`'s blob and the runner's image version) is not checked again | a pull request of two commits or more: each commit before the head that changes code, as the gate counts it for `static` |
| `site_commit` | each commit of a pull request but its head that changes the site alone (beside documentation or not), checked out on its own: the site job's steps, word for word; at most `PER_COMMIT_MAX_PARALLEL` at once, as `commit` | a pull request of two commits or more with such a commit before the head |
| `fuzz` | after `hypothesis`, from the union of the shards' example databases: the Atheris targets of `tests/fuzz/`, after a control with seeded faults, for `fuzz_seconds` each; then the property tests, to replay and shrink what was found; on Python 3.14 | weekly; manual, alone with `fuzz_only` |
| `result` | fails unless every job the gate asked for succeeded (a job skipped by its `if` reports success), and when any job failed or was cancelled: the one check the ruleset on main requires | always |

The `tests` jobs run the properties at `dev` on random draws, as a laptop does (since #38), so an audit can fail
a sound property by chance. Since 2026-10-18 `dev` holds each feature it judges to a floor that a correct run
falls below with a probability of at most 1e-6 by the audits' model, at the chance the floor assumes, as `ci`'s
floors are: at most about 3e-5 a run of the whole suite, and about 1.5e-4 for a pull request's five runs, one on
each Python (until 2026-10-21 the `commit` job ran the suite on each earlier commit too: 1.6e-3 for a pull
request of 50 such runs). Before 2026-10-18, about one of these runs in 25 failed by chance, so that a pull
request was almost never green. The `hypothesis` job at `ci`
also judges least shares, whose figure is known for some properties only, and the `controls` job, whose
searches and controls are derandomised, adds nothing. Such a failure names the seed that draws its run again,
and `repeat.yml` tells chance from a fault (`tests/property/README.md`, "Audits").

The `tests`, `controls` and `hypothesis` jobs run their tests in parts that run side by side, which
`tests/unit/test_ci_workflows.py` holds to a partition: it collects the tests each part of each matrix selects, on
this repository, and fails where a test is in none of a job's parts or in two (the test's own controls fail where a part
is left out of the matrix, a count is wrong, or a test is in two parts). A part is chosen with `--partition I/N`, or for
a Hypothesis shard `--shard NAME_IofN`: the tests the other options select, split by the seconds each took in a CI
run (`tests/partition_weights.json`, written from such a run's reports by `python -m tests.partition`), the heaviest
test left to the lightest part. The weights decide how even the parts are and never which tests run: a stale or
missing weight makes a part slower and loses no test. Their evenness shows in the durations reports (one per part,
so a part that runs well beyond the others is read there); the weights are measured seconds of one CI run, so they
age: a test added since weighs the default until a run lists it, and a long test renamed or moved loses its weight.

Maintaining the weights. Record them again when a part runs visibly longer than its siblings, or after long tests
are added, renamed or moved. Download the durations reports of one CI run on Python 3.15, the Python the weights
come from and the only one on which the pre-review script's trace test runs: for the `dev` table every part of the
`tests` job and of the `controls` job (`durations-tests-3.15-1of2`, `durations-controls-3.15-1of2`, ...); for the
`ci` table every part of the `hypothesis` job's shards from a run at the `ci` profile, not `deep`
(`durations-hypothesis-agreement_1of2`, ...). Then run `python -m tests.partition PROFILE SOURCE REPORT ...` with
the profile (`dev` or `ci`), a line saying which run the reports are from, and the reports' paths. A test file the
reports hold has its entries replaced and a file they do not hold keeps its own, so one job's reports leave the
other job's weights; give every part of the jobs that run a file, since the tests of a missing part lose their
weights. On Python 3.11 to 3.14 the trace test is skipped but still assigned its 3.15 weight, so a part there can
run up to about 9 percent over an even split: the weights are one Python's, not each Python's own.

Each pytest job but `commit`, which collects every test and runs the specification-sync tests, writes a JUnit
report, summarised on the run's page (`scripts/report_test_durations.py`: the tests in each band of wall time, the
slowest tests and files, and the total, wall time and CPU time, the tests' own and their child processes') and kept
90 days as the artifact `durations-<job>-<Python and part, or shard>`, whenever pytest ran.
pytest runs under `timeout --foreground --signal=INT`, three minutes before its job's timeout, so that a run out of
time is sent one SIGINT, stops, writes the report of the tests that finished (about 5 s later, after pytest-xdist
ends its workers) and fails, rather than be cancelled without one (`ci.yml` says why).
No duration fails a job.

Every action is pinned to a commit, uv to one version (`UV_VERSION`), and every job of every workflow to the runner
image `ubuntu-24.04` (`ci.yml` says why, above its jobs); `uv sync --locked` fails on a lock file out of date with
`pyproject.toml`.

## Repeat runs (`repeat.yml`)

Run by hand alone (`workflow_dispatch`), never on a push or a pull request: one pytest node, a test, a file or a
directory under `tests/`, run many times in parallel jobs, each run under a seed of its own, to measure how often
it fails (maintainer, 2026-10-17). `tests/README.md`, "Repeat runs on CI", says how to ask for one and how to read
its summary. Its inputs: the node; the profile, one of `tests/conftest.py`'s (`dev`, `ci`, `deep`; `ci` by
default); the jobs, 1 to 20, and the runs in each, 1 to 25; the first seed, 0 to 999999999; the Python, one of
the test matrix's; and extra pytest arguments, `--shard` and `--property-controls` alone.

| Job | Runs | When |
|---|---|---|
| `request` | checks the inputs (`scripts/repeat_runs.py request`, on the runner's Python) and writes them, checked, as its outputs, which the jobs after it read in place of the inputs; then collects the node with the extra arguments, so that a test that does not exist or a value pytest does not list fails before any run starts; then checks the runs' cap, `REPEAT_MAX_PARALLEL` (below) | every dispatch |
| `runs` | each job its runs one after another, each under its own seed (`--hypothesis-seed`; job `j` of `r` runs from the first seed `s` takes the seeds `s + (j - 1) r` to `s + j r - 1`), `.hypothesis/` removed before each, as CI's test jobs run pytest; each run's record, with its failing examples, kept 90 days as the artifact `runs-<job>-<attempt>`, so that a job run again keeps its records beside its first attempt's; fails where any run failed or did not finish | after `request`, the jobs side by side, at most `REPEAT_MAX_PARALLEL` at once (`max-parallel`), 10 where it is unset (below), none cancelled by another's failure (`fail-fast: false`) |
| `summary` | sums every job's records on the run's page: the runs, the failures with their seeds and failing examples, and the failure rate with its exact one-sided 95 % upper bound (`scripts/repeat_runs.py summary`); fails where a run failed or did not finish, a seed has no record or two, a job of runs did not succeed, or the run is on an attempt but its first | after the runs, whatever their result, once the request was checked |

No input reaches a profile's example count, deadline or health checks: the profile is chosen from
`tests/conftest.py`'s own, each input reaches a step through its environment alone and is checked before any job
reads it, and no extra argument but the two listed is taken. A job of runs starts no run, and interrupts the one
running (`uv run timeout --foreground --signal=INT`, as `ci.yml`'s jobs do), three minutes before its timeout: 60 minutes at
`dev`, 120 at `ci`, 360 at `deep`. The workflow reads the repository alone (`contents: read`), reads no secret,
and restores the uv cache CI saved but saves none. A dispatch waits behind a running one of the same inputs on the
same ref, whose seeds it would repeat; one of other inputs runs beside it, and none is cancelled: GitHub
cancels a run pending in a concurrency group when another queues, unless the group sets `queue: max`, which
holds up to 100 pending in order (GitHub's "Control the concurrency of workflows and jobs", read
2026-10-18), and both hand-run workflows set it.
Each run draws what its seed draws on any machine. Until `tests/conftest.py`'s profiles stopped inheriting
Hypothesis's own `ci` profile, which `CI=true` loads on every runner and which sets `derandomize=True`, every run
drew the same examples whatever its seed (`tests/README.md`, "Repeat runs on CI").
`tests/unit/test_ci_workflows.py` holds it to each of these, running its steps as written.
When the node collects a test in a module whose searches are derandomized, a module `PROPERTY_CONTROLS`
selects (the mutant searches and the audit controls) or one whose code sets `derandomize` to anything but
off, fixes a seed (`@seed`), or runs `tests/property/support.py`'s `MUTANT_SEARCH` or `examples_to_kill`
by any name, the request job warns once, naming the modules (for the whole suite, which always holds some,
naming none), and does not refuse (#43's review, L7; #46's, L5); a module counts by any of its code,
whichever of its tests the node selects: every repeat of such a test draws the same examples whatever its seed, so a
repeat of it measures nothing a seed changes, but repeating it on a head and on its base is still a valid
comparison. The warning reads what pytest collected with the extra arguments, so `--property-controls none`
leaves the controls out of it. A module that runs another module's search through a function it imports
(`tests/property/test_validators_agree.py` runs the writer mutants' searches) is not found.

## Mutant tables (`mutants.yml`)

Run by hand alone (`workflow_dispatch`), never on a push or a pull request: a branch's hand mutants, each a
patch committed on it as `mutants/<name>.patch`, each run against a pytest selection in a job of its own,
beside a job of the commit as it is (the baseline), and one table of what became of each (maintainer,
2026-10-18), so that a reviewer's mutant runs, which took about five hours on the shared laptop for one
review, run side by side on CI. `tests/README.md`, "Mutant tables on CI", says how to ask for one and how
to read its table. Its inputs: the mutants, by name, or none for every patch in `mutants/`; the selection,
paths or nodes under `tests/` (`tests` by default, the whole suite); the profile (`dev` by default); the
Python; the seed every run draws under, or none for one drawn at random; and extra pytest arguments,
`--shard` and `--property-controls` alone.

| Job | Runs | When |
|---|---|---|
| `request` | checks the inputs and every patch they name (`scripts/mutant_runs.py request`, on the runner's Python) and writes them, checked, as its outputs, the matrix of jobs among them, which the jobs after it read in place of the inputs; then collects the selection with the extra arguments, so that a test that does not exist fails before any mutant's job starts; then checks the mutants' cap, `MUTANT_MAX_PARALLEL` (below) | every dispatch |
| `mutants` | one job for the baseline and one for each mutant: a clean checkout of the dispatched commit, the patch applied (`git apply`), every module of the package imported and each Python file the patch touches compiled, the selection collected, and then run as CI's test jobs run pytest, a worker per vCPU under `worksteal`, stopping at the first failure, under the request's seed and profile, interrupted three minutes before the job's timeout (60 minutes at `dev`, 120 at `ci`, 360 at `deep`), counted from the job's first step, so that a slow setup comes out of the run's time; its record kept 90 days as the artifact `record-<mutant>-<attempt>` (`record-_baseline-<attempt>` for the baseline); fails where it could not decide, and where the baseline did not pass | after `request`, the jobs side by side, at most `MUTANT_MAX_PARALLEL` at once (`max-parallel`), 10 where it is unset (below), none cancelled by another's failure (`fail-fast: false`) |
| `table` | one row for the baseline and one for each mutant, on the run's page and kept 90 days as the artifact `mutant-table-<attempt>` (`table.md`, `table.json`): killed, with the collected test that failed first; survived; broken, where the patch does not apply or the code does not import or collect, in one process or under pytest-xdist (a module or a worker in its report where a test should be), with why; or undecided, with why. Where the baseline did not pass, no mutant counts as killed. Fails unless the baseline passed and every mutant was killed, each with one record, every mutant's job succeeded, and the run is on its first attempt | after the mutants' jobs, whatever their result, once the request was checked |

A patch is a file of the dispatched commit, never text from the dispatch form, and the request job refuses,
before any mutant's job starts, a patch git does not read as a text patch in its own format (a `diff --git`
for each file, in git's order), one with binary data, one that renames or copies a file, in any form, or
makes a link or a submodule, and one that touches a path outside the checkout (from the root, through `..`,
or through a link), inside `.git`, under `.github/` or `mutants/` (ignoring case), one git ignores (the
environment uv installs, `.venv/`, and the example database, `.hypothesis/`), the runner itself
(`scripts/mutant_runs.py`), or what decides what uv installs or how it runs (`pyproject.toml`, `uv.lock`,
`uv.toml`, `.python-version`, `.python-versions`). A rename without rename lines is one: a `diff --git` line,
or its `---` and `+++` lines, naming another path than the file's, which git applies by deleting that path
while its own report lists the new one alone (#46's review, H1), so every path a patch names, old and new, is
checked. It refuses a patch that is
not a regular file committed at the dispatched commit, a name other than 1 to 64 letters, digits, `_` and
`-`, more than 200 mutants (a matrix holds 256 jobs), and a patch of more than 1 MiB or with a control
character but tab and line feed. A mutant's job checks its patch again before applying it, and runs the
script that records the verdict from a copy outside the checkout, made before the patch is applied
(`python3 -I`), so that nothing a patch writes reaches it, and every `uv run` after the patch neither syncs
nor locks (`--no-sync --frozen`), so that nothing a patch adds changes what is installed. These guard against
accidents, not a hostile patch: a patch's code runs in its job, which could forge its own record, so the
workflow relies on who may dispatch it (write access, which can push a workflow anyway), a token that reads
alone, no secret read and no cache saved. Each row gives the paths its patch touches, and a kill by a patch
that edits the tests or pytest's settings is marked, since the edit may have failed the test. Every run of a
dispatch draws under one seed, so
that a chance failure of the baseline's draws is a failure of each mutant's that leaves them alone, and a
mutant's run replays exactly. Under pytest-xdist, `-x` ends a run that failed as interrupted (exit 2, where
a run without xdist exits 1; checked 2026-10-18), so a run that stopped so counts as killed when its report
names the failed test. The workflow reads the repository alone (`contents: read`), reads no secret, restores
the uv cache CI saved and saves none, and never cancels another dispatch; a dispatch waits behind a running
one of the same inputs on the same ref, and others pending behind it wait in turn (`queue: max`, above). `tests/unit/test_ci_workflows.py` holds it to each of these, running
its steps as written on a throwaway repository, with a stub in place of pytest and with this Python's
pytest, end to end on mutants that are killed, survive and are broken.

## Measurements (`measure.yml`)

Dispatched by hand (`workflow_dispatch`): the measurements of `scripts/measure.py` (floors at the variance
measured, kill drift over streams, regions of a base against the head, a fuzz control's rate, the input
coverage's cuts) as a matrix of jobs, with the counts and judgement of a local run (maintainer, 2026-10-23);
`tests/README.md`, "Measurements on CI", says how to ask for one and how to read its table. Its inputs: the
kind, `floors`, `drift`, `regions`, `fuzz` or `cuts`; the selection, paths or nodes under `tests/property`, fuzz
controls by name, or for cuts `all` or selections of the input coverage's baseline, each as `NAME:whole` to
run the cuts its `!` patterns leave out too; the count, streams or runs (the rule's: 20, 40, 18 and 10; none for
cuts); the streams a job (none for cuts); the base, for regions; and the Python. A selection's cuts are split
into slices by its baseline's `timing` (its cuts, or those of a whole recording for `NAME:whole`, and its longest cut measured on CI), each slice's cuts planned
to fill half its job's 120 minutes at two at once, the rest left to the selection's recording and a slower
runner.

It also runs on a pull request that changes `measure.yml`, `scripts/measure.py`, `scripts/input_coverage.py` or
a file under `tests/`. There the request reads the pull request's base and head from the event and the files
it changes (`git diff BASE...HEAD`), and makes two sets of jobs. Where it changes the workflow, its script or
the input coverage's runner or plugin, the self-test (`SELF_TEST`), each kind on one small selection with the
answer it must give: stream 0 the recorded kill, a tree against itself every share's ratio 1 and every kill its
record, the fastest fuzz control finding its fault and finding nothing with none seeded, and the cuts of one
site of S3c's each with the baseline's result (GitHub dispatches a workflow only from the default branch's copy
of it, so a draft would otherwise never run its own). Where it changes a test a selection of the input coverage
runs (or `tests/conftest.py` or `tests/property/conftest.py`, the Hypothesis profiles, or its entry of the
baseline, against the base's), every cut of that selection; where it changes a module that the selection's tests
import, the cuts of the sites whose names hold that module (maintainer, 2026-10-24), in slices planned from the
cuts that scope holds, which the request job counts from the selection's recording (none where it holds none: a
notice names the module); each held to the baseline at the pull request's merge commit, a cut that disagrees
failing the report. The run is advisory (maintainer, 2026-10-25): no branch protection requires it, until it has
run cleanly on a few feature pull requests. A pull request that changes none of these makes no job but the
request. A newer push cancels a pull request's running measurement.

| Job | Runs | When |
|---|---|---|
| `request` | checks the inputs (`scripts/measure.py request`, on the runner's Python), or on a pull request its base and head, and writes them, checked, as its outputs; collects the selection at `ci` and makes the matrix, one job a test function and chunk of streams (for regions a job of each side, and one of every mutant search at the head), a fuzz control's run or a slice of a selection's cuts, and resolves the base to its commit (`measure.py matrix`), so that a selection holding nothing to measure, a base that is no commit or more jobs than a matrix holds fails before any job starts; on a pull request, the self-test and the cuts of what it changes (a scope's cuts counted from the recording), or no job; then checks the jobs' cap, `MEASURE_MAX_PARALLEL` (below) | every dispatch, and a pull request that changes the workflow, its scripts or the tests |
| `measure` | each job of the matrix: the job checked again, then run (`measure.py job`): a base exported with `git archive` into an environment of its own; pytest with the script as its plugin, a process per vCPU, each a share of the streams, the property's checks run and its audit's judgement left to the report; every mutant search at the head as `gen_kill_counts.py --measure` runs them; one run of a fuzz control as `ci.yml`'s control step runs it, on Python 3.14 with Atheris; or a slice of a selection's cuts, `scripts/input_coverage.py run` recording the selection then running the slice two cuts at once, no cut started once the rest of its time would not hold one and a half of its longest cut. Interrupted three minutes before its timeout (120 minutes, 30 for a fuzz run), counted from the job's start, by one SIGINT the script passes on to its processes, so that the record keeps what finished; its record kept 90 days as the artifact `record-<job>-<attempt>`; fails where its record holds a problem (for a cut job: the selection failing with no cut, a cut of its slice not run in its time) | after `request`, where it made a job, at most `MEASURE_MAX_PARALLEL` at once (`max-parallel`), 10 where it is unset (below), none cancelled by another's failure (`fail-fast: false`) |
| `report` | counts the records first (`measure.py summary`), one for each job of the matrix, naming a missing one as that, then merges them into one table a kind with its flags, on the run's page and kept 90 days as the artifact `measure-table-<attempt>` (`table.md`); fails where a record is missing or doubled, a record holds a problem, a job did not succeed, a self-test job gave another answer than its own, a selection's slices do not make one report (one missing or doubled, or one recording other cuts), a pull request's or the self-test's cuts disagree with the baseline, or the run is on an attempt but its first. A flag (a floor above 1e-6 at the variance measured and the least share, a kill near or past the guard, a share below 0.8 of the base's, a dispatched cut that disagrees with the baseline) is a finding the table reports, not a failure | after the jobs, whatever their result, once the request was checked and made a job |

No input reaches a profile's example count, deadline or health checks: every run is at `ci`, the profile of
`tests/conftest.py`, derandomised (the example database off, the shrink and explain phases dropped, and the
health checks `too_slow`, `filter_too_much`, `data_too_large` and `large_base_example` suppressed, as a
measured run needs), each stream salting the test's digest. Each input reaches a step through its
environment alone and is checked before any job reads it. The workflow reads the repository alone
(`contents: read`), reads no secret, restores the uv cache CI saved and saves none, and cancels no running
dispatch; a dispatch waits behind a running one of the same inputs on the same ref, while a pull request's
run gives way to the next push's. GitHub refuses `queue: max` beside a `cancel-in-progress` that is true, so this
workflow leaves the queue at GitHub's default, `single`: a dispatch pending behind a running one of the same inputs
on the same ref is replaced by a newer dispatch of those inputs (the group holds every input, so those are rare;
a dispatch that ran is never cancelled).
`tests/unit/test_ci_workflows.py` holds it to each of these (that no event's settings combine `queue: max` with
a `cancel-in-progress` that is true among them), and runs the request, a measurement and the report
as written on this repository, the report's failure cases among them.

## Claims (`claims.yml`)

On a pull request opened, reopened, pushed to or edited (`opened`, `reopened`, `synchronize` and `edited`;
maintainer, 2026-10-24): `scripts/check_claims.py check` on the pull request's description and its commit
messages, in one job, `claims`, on the whole history (`fetch-depth: 0`). A head, a base, a commit, or a count of
commits, files or lines that either states and git does not show fails the job. The figures (a number that
no recorded measurement holds, in the description or the CHANGELOG lines the branch adds) are advice, not a
failure, until measurement runs write the facts that would hold them (maintainer, 2026-10-23): the job passes
`--figures-advisory`, which prints each as `advisory figure finding:` and leaves the git facts to fail. The job
summary holds the output, and one notice counts the figures. An empty description passes, with a notice that
there is no claim to check (the commit messages are checked all the same). The ruled wording, the script's third
check, is not run: the rulings file is private and CI never reads it.

The same job runs the baseline guard of `tests/unit/test_check_claims.py`, which holds
`scripts/claims_baseline.json` to the CHANGELOG at its commit on `main`. The test jobs check out at depth 1,
where that commit is missing and the guard skips; this job has the history, and sets `CLAIMS_REQUIRE_HISTORY=1`,
under which the guard fails where the commit is missing, since a skip there would pass unseen. It runs after a
failed check too, so that one run shows both.

| Job | Runs | When |
|---|---|---|
| `claims` | the description, written from the event through the environment to a file (`printf '%s'`; no pull request's words reach a script's text); the check with the event's base and head, whose output is printed with workflow commands stopped; the baseline guard | a pull request opened, reopened, pushed to or edited |

It is a workflow of its own because `ci.yml` cancels a pull request's running workflow on each new event
(`cancel-in-progress`): an `edited` trigger there would cancel the whole run whenever the description changed,
and without it a description corrected after the push would never be checked again. Its concurrency is one group
for each pull request, and a new event cancels the run before it. Each event's payload holds the pull request as it
was when the event was made, its description and its head both, so when a push and an edit come close together
the later event's run reads the latest of each and is the run whose verdict stands; the earlier run reports as
cancelled, and checked a state that is no longer current. A manual re-run is the exception: GitHub re-runs a run
with its own event's payload, so it reads the description as it was then; to check a corrected description, edit
it or push.

Open point: the ruleset on `main` requires `ci.yml`'s `result` alone, so this check does not block a merge until
the maintainer adds `claims` to the ruleset as a required check. A pull request with a merge conflict has no merge
commit to check out, and runs neither workflow. `tests/unit/test_ci_workflows.py` holds the workflow to each of
these, and runs its steps as written on a throwaway repository, with the controls: a description that states the
head, the base and the count truly passes, and one that names a head the branch replaced, or a wrong count, fails.

## The whole suite on CI

A branch's whole suite runs on CI without a workflow of its own. A push to a pull request, a draft
included, runs it on the head at `dev` in `ci.yml`'s `tests` and `controls` jobs (every Python, and the
mutant searches and audit controls on the range's ends); each earlier commit gets the fast checks, the
collection of every test and the specification-sync tests in the `commit` job. A push to main and the weekly
run run every job. For a pushed branch with no pull request, dispatch
`repeat.yml` with `node=tests`, `jobs=1` and `runs=1`, at the profile and on the Python wanted: one run of
the whole suite under one seed. A manual run of `ci.yml` on a branch also runs the suite, with every job but
the per-commit ones, but its Hypothesis job runs at `deep`, beside the fuzz job, which takes hours. Each job
runs pytest with a worker per vCPU (`-n auto`), four on GitHub's standard Linux runner for a public
repository (GitHub's runner reference, read 2026-10-18): a job has its runner to itself, so the worker count
a laptop shared between agents needs chosen (`-n 8` or `-n 12`) has nothing to share there.

## Jobs at once (`PER_COMMIT_MAX_PARALLEL`, `REPEAT_MAX_PARALLEL`)

Since 2026-10-20 the repository is the only one of the OpenMaterica organisation, whose plan reads `team`
(`gh api orgs/OpenMaterica`), for which GitHub's limits reference gives 60 standard-runner jobs at once; before,
it shared its organisation's 60 with MIME's and MADDENING's work. A job beyond the limit waits for a runner. On
the runs measured since the move (2026-10-20 23:00 to 2026-10-21 04:00, UTC) GitHub ran at most 5 to 19 of this
repository's jobs at once, a number that rose over those hours, while others waited; why is not known. Three
repository variables cap how many of this repository's matrix jobs run at once (maintainer, 2026-10-17):

| Variable | Caps | Where it is unset |
|---|---|---|
| `PER_COMMIT_MAX_PARALLEL` | `ci.yml`'s `commit` job, and its `site_commit` job apart: each may run that many at once | 6 |
| `REPEAT_MAX_PARALLEL` | `repeat.yml`'s `runs`, for each dispatch | 10 |
| `MUTANT_MAX_PARALLEL` | `mutants.yml`'s `mutants`, for each dispatch | 10 |
| `MEASURE_MAX_PARALLEL` | `measure.yml`'s `measure`, for each dispatch | 10 |

Raise `PER_COMMIT_MAX_PARALLEL` so that a pull request's commits are checked sooner; lower it where the head's
jobs wait behind the per-commit ones. Where it is unset the cap is 6. A repository's variable can change
without a change to this file: read it with `gh variable list` (below) before relying on a figure here. The
figures below are written for a variable of V, and take V = 12, the value the maintainer set on 2026-10-20, as
the example.

Count the rest too. Once the gate has passed, a push to a pull request runs 30 jobs on its head at once:
`static`, `generated`, `tests` on five Pythons in two parts each (10), `controls` in six parts (four on 3.11,
two on 3.15), `hypothesis` in eleven jobs, and `site`; the two `kill_points` jobs start as the `controls` parts
end, so they raise no peak. Each job's set-up (checkout, uv with its cache, `uv sync`) took a median of 6 to 8 s,
and at most 11 s in nine jobs of ten, and a pytest job collects its tests in about 15 s more (CI runs of
2026-10-20 to 2026-10-21), so a part costs about half a minute of runner time beside its tests. On the runs of
2026-10-20 before the move, which started every job at once, a run without earlier commits took 7.2 to 11.2
minutes of wall time (median 9.1; seven pushes and three pull requests of one commit), about 130 job-minutes,
set by its longest job, and a pull request with earlier commits 23.8 to 25.0 (six runs), set by the per-commit
job, which then ran the whole suite: a median of 23.7 minutes a commit, 12 to 28 (24 jobs). The `commit` job's
other steps took a median of 45 s of it; with the collection and the specification-sync tests (56 to 144 s of
test time in the test jobs' reports, nine runs, every Python, which four workers share) it is about two minutes
a commit, an estimate to be read from the durations of the pull request that made the change.

| | The head alone | With `commit` jobs at V | At the cap's ceiling of 20 |
|---|---|---|---|
| Runners one push holds | 30 | 30 + V (42 at V = 12) for the two minutes or so of the `commit` jobs | 50 (70 with `site_commit` jobs, which run beside `commit`'s and are rare) |
| Left of 60 at once | 30 | 30 - V (18 at V = 12) | 10 (none, and 10 wait, with `site_commit` jobs) |
| Left of 20 at once | none, 10 wait | none, 10 + V wait (22 at V = 12) | none, 30 wait |

At a limit L of jobs at once, a run takes at least its job-minutes over L, whatever the caps: about 130 for the
head and about two more for each earlier commit, so 10 minutes for the head alone at L = 13. Where jobs wait,
GitHub starts them in an order of its own, not the workflow's, so the longest may start last.
`PER_COMMIT_MAX_PARALLEL` caps `commit` and `site_commit` each apart; each repeat dispatch runs its own
`REPEAT_MAX_PARALLEL` (20 at the ceiling) and each mutant dispatch its own `MUTANT_MAX_PARALLEL` (20 at the
ceiling, and nothing beside them: its request job ends before they start and its table job starts after them),
up to 201 jobs for 200 mutants and the baseline. One push at the ceiling with a `site_commit` job, one repeat
dispatch and one mutant dispatch together ask for 70 + 20 + 20 = 110, more than the 60: the rest wait for a
runner. Each further dispatch, of other inputs or on another ref, asks for its own 20 more.

Anyone with write access to the repository can set these variables, not its maintainers alone (GitHub's "Use
variables": write access suffices for a repository of an organisation), which is why the check bounds them. Set,
read or remove one with the GitHub CLI:

```sh
gh variable set PER_COMMIT_MAX_PARALLEL --body 12 -R OpenMaterica/OpenMaterica
gh variable list -R OpenMaterica/OpenMaterica
gh variable delete PER_COMMIT_MAX_PARALLEL -R OpenMaterica/OpenMaterica  # the default again
```

Each takes a whole number from 1 to 20, written plainly in ASCII digits. A step of the job the capped jobs need,
`gate` or `request`, reads the variable on every run (a push to main and the weekly run included) and fails on
anything else, with "the repository variable NAME is ..., not a whole number from 1 to 20": 0, a negative number,
more than 20, a fraction, `1e1`, a sign, a space or a leading zero, another script's digit, or text. The capped
jobs then never start, and the run fails. GitHub documents no bound on `max-parallel`, nor what it does with such
a value, so none reaches it. The step writes the value it took as an output of its job (the gate's
`per_commit_max_parallel`, each request job's `max_parallel`), and the capped jobs parse that output
(`fromJSON(needs.gate.outputs.per_commit_max_parallel)`) and never read the variable: a value changed after the
check does not reach a run already past it. "Re-run failed jobs" runs the capped jobs again on the output their
checker gave when it passed, as it runs the per-commit job again on the gate's list of commits (GitHub does not
document this; the per-commit matrix relies on it already); "Re-run all jobs" checks the variable again.
`tests/unit/test_ci_workflows.py` holds each capped job to that expression and each checker to that output, and
runs each check as written, under two locales, on values inside and outside the range. It also fails where a
workflow reads a repository variable anywhere but in a cap's check: a new cap is added to its `CAPS`, with a
check of its own.
