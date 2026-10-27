# Fuzzing

Six Atheris targets, which run coverage-guided fuzzing against the core. They live under `tests/` because
they are tests of the core, outside the package and its layers: they reuse the property tests' strategies,
profiles and example database, and are typed, linted and SPDX-checked with the other tests. pytest does not
collect them. Atheris ships no types, so `typings/atheris/` holds stubs for the part of it the targets use.

| Target | Drives | Fails when |
|---|---|---|
| `jsonio_bytes.py` | raw bytes into `jsonio.parse`, from a seed corpus of every conformance input and with `json.dict`, JSON's tokens and the escapes and bytes `record_format.md` section 1 item 6 turns on | `parse` raises; or it disagrees with the reference reader (`tests/conformance/reference_reader.py`), the standard library's json with hooks that refuse exactly the faults the item lists: a value it accepts differs, numbers bit for bit, or it refuses what the reference accepts, or the reverse |
| `properties.py` | the JSON properties of `tests/property/` (the reader, RFC 8785, the hash), through `fuzz_one_input`, in-process; the first byte picks the property | a property fails. The failure goes into the example database, and `pytest tests/property`, under the same `MATERICA_HYPOTHESIS_PROFILE`, replays it first and shrinks it |
| `record_properties.py` | the record properties of `tests/property/` (the envelope checks, versions, the read's laws, step 8's over a constant, an interval and a composition, steps 9 and 10's, and the S2 design's HP1, HP2, HP4, HP6, HP10, HP11 and HP12, the agreement with the reference model) in the same way: structure-aware, since their strategies build records, stores and requests from the bytes Atheris gives | as above |
| `read_field_bytes.py` | raw bytes into steps 7 to 13 of a read: the first byte picks a registered field, and the rest, read by `jsonio.parse`, stands in that field's place in a record valid otherwise, pinned by its recomputed hash, read at operating conditions with a tolerance or an accept list for each condition its row requires; seeded with every value field of every conformance input, with a dictionary of the member names and tokens a value field holds, a table's reserved `points` among them, that `--dict` writes from the schema and the vocabulary | a read raises anything but `NotImplementedError`; two reads differ; a result breaks HP1 or HP2 (a code of the table, of steps 7 to 13 only, each with its condition once and `condition` where section 2 item 2 puts it, the worst status, the members item 6 gives, `table` exactly beside a value read from a table: `field_oracle.check_table_member`); the read without the hash suite differs by more than the label `hash_not_checked`; the read under the `want` that gives the field's form (`value`, or `bounds` for an interval, `components` for a composition and `evidence` for evidence) and the reference model (`tests/reference/read_model.py`) disagree but as HP12 lists (`field_oracle.check_against_the_model`), which sees a refusal step 8 misses or gives wrongly, a condition holding a member of the other kind's shape among them (HP12's open point `members_of_the_other_kind`, which the target knew by its shape until the maintainer ruled it fail closed, 2026-10-19); step 8 lets through a constant, a table, an interval, a composition or evidence its row allows that the reader `$defs` refuse (`field_oracle.py`, T1's third relation); or steps 9 and 10 read such a field otherwise than their text: its units by code point, a table's `axis_unit` among them, and its conditions by HP7's oracle (`tests/property/condition_oracle.py`), a table that step 9 passes giving "not yet". A field holding alternatives is read by step 7 (S4a's rows, and S4d's for a table alternative whose read gives a reason at step 11), which the model decides too; `NotImplementedError`, "not yet", is a step not built, which no field the target writes reaches since S4d. A table is read to the end (S3b-2): its axis entry and step 11's reasons by the text (`field_oracle.table_steps_10_and_11`), and the table read again under `want: value` at the places table item 3 tells apart (`field_oracle.places`: its knots and edges, the readable range's ends, the double either side of each, a value beyond each end of `x`), each read held to the model, to steps 9 and 10 and to HP1 and HP2; a field holding table alternatives read again at their places too, as many in all as one table's (`field_oracle.alternative_places`, S4d), so that step 7 meets a table alternative read at an edge, outside its range and inside it beside the others |
| `read_acceptance_bytes.py` | raw bytes as the one entry of a request's `acceptances` (S3c, the S3 design's `read_acceptance_bytes`): `jsonio.parse` reads them, and the entry stands in fixed reads of two conformance tables (`acceptance_oracle.PLACES`): the density table below, inside and above its range and below it under `want: bounds`, and the edge table narrowed to [275, 283] K at its edge outside the range, beyond it and between it and the range; seeded with every acceptance of every conformance case's request, its extrapolations located at both tables among them, with a dictionary of an acceptance's names, the kinds, an extrapolation's methods, the registered fields and conditions and the two records' references, that `--dict` writes | a read raises anything but `NotImplementedError` (a pick or an overlay, which S4 reads, or a `trainable` acceptance, which S7a-4 reads); two reads differ; an extrapolation that breaks its shape is not refused with `request_incomplete`, wherever it is located (`acceptance_oracle.check_shape_refused`); a result breaks HP1 and HP2 as an acceptance leaves them, an extrapolation's result `not_met` with `outside_range`, the value with the members beside it and the table, and its `assumption` the entry's own `method` and `law`, the law text of at least one character (`acceptance_oracle.check_acceptance_laws`), or holds `table` other than beside its value; the status is better than the same read without the entry (`acceptance_oracle.check_no_better`); or the read and the reference model disagree but as HP12 lists (`field_oracle.check_against_the_model`) |
| `build_bytes.py` | raw bytes in place of one member of a build-check case's declaration (S7a-1, the S7 design's `build_bytes`): the first byte picks one of the 162 declarations the build-check cases read, or, past them, one of the four whose cases give a result `condition_outside` and hold no waiver naming it (BC-001's two, BC-017's and BC-027's), with such a waiver planted in that result's model (S7a-2, `PLANTED`; BC-038's holds one already), the byte read modulo the number of choices, the seeds' and the planted ones, so that a seed's first byte keeps its meaning, while a byte at or past the number of seeds picks another declaration than S7a-1's target did, and an input saved by that target replays otherwise here (no workflow keeps this target's corpus); the bytes up to the first newline are a JSON pointer to a member of it, to a member its object does not hold yet, or to the end of one of its lists; and the rest, read by `jsonio.parse`, stands in that member's place, `check_build` checking the declaration over the records that declaration's case reads. Seeded with every member of every such declaration at its pointer, roots included (10,927 inputs), with a dictionary of their names and strings, the kinds, the registered names and the vocabulary's tokens, that `--dict` writes | `check_build` raises anything but a `NotImplementedError` of what this version builds nothing past its check for (`NOT_BUILT`: the S7 design's 4.1, and what S7a-2's label trust, S7a-3 and S7a-4 read); a refusal's pointer names no member of the declaration (a missing member's names the object that should hold it); a refusal names a case outside the refusal paragraph's nine; the build's reference model (`tests/reference/build_model.py`) refuses the declaration, every rule's refusals placed, or takes it, passing its own check, and the check's refusals differ from its own (none, where it takes it) but as a known divergence says (`KNOWN_DIVERGENCES`, empty now, below): the relations of `build_oracle.py`, which `tests/unit/test_fuzz_build_oracle.py` shows failing; or the report the build gives breaks a results relation of `build_results_oracle.py` (S7a-2, below): an accepted result holds a `not_met` reason no assumption or `trainable` acceptance covers, `refused` is other than where a refusal or a result not accepted is, or, where the build's results model decides and neither it nor the build refuses the declaration, the report is other than the model's |

`build_results_oracle.py` holds the relations `build_bytes.py` holds every report the build gives to (the S7
design's 6.5), importable without Atheris: an accepted result holds no `not_met` reason that no assumption or
`trainable` acceptance covers (`declarations.md` section 4.2's own law); the report is refused exactly where a
refusal or a result not accepted is; and where the build's results model decides and neither it nor the build
refuses the declaration, the report is the model's. The target checks the first two, which need no model, then
the third, after `check_build` and before the relations to the declaration's model. The declaration's own
refusals are left to the relation to the build's reference model, which compares them with its exemptions (a
refusal of the model's not placed, a known divergence): compared by the third relation, which runs first, they
gave its line, and S7a-1's control, found by the reference model's line, was found by none.
`tests/unit/test_fuzz_build_results.py` shows them quiet on every build-check case's report, the first and the
third failing where `_covers` lets a waiver naming `condition_outside` cover it (the design's fault for the
target's control), the first where an accepted result holds that reason after one its assumption covers, the
second where `refused` reads the first model's results alone, and the third where a result or an unused
acceptance is left out, where one member of a result (its status, reasons, verdict, `accepted_by` or
`not_accepted`) differs alone, and where `refused` does; and `tests/unit/test_fuzz_build_oracle.py`, through the
target's own `test_one_input`, shows the target quiet on every seed and on every member of the four planted
declarations, and failing on each broken build: at the first relation on BC-038's seed and on the planted
BC-001 and BC-017 declarations, at the third alone on the planted BC-027 one, whose `label_mismatch` keeps its
result refused, and at the second on each seed whose report holds a result not accepted after a first model's
all accepted; and each control's fault, seeded, failing the target on the inputs that show it with a line read
as that control's find.

## Running

Atheris 3.1.0 installs on Linux x86_64 with Python 3.12 to 3.14 only; elsewhere the `fuzz` group installs
nothing.

```sh
uv sync --group fuzz
uv run python -m tests.fuzz.jsonio_bytes --seed corpus
uv run python -m tests.fuzz.jsonio_bytes corpus -dict=tests/fuzz/json.dict -max_len=4096 -max_total_time=300
MATERICA_HYPOTHESIS_PROFILE=ci uv run python -m tests.fuzz.properties -max_total_time=300
MATERICA_HYPOTHESIS_PROFILE=ci uv run python -m tests.fuzz.record_properties -max_total_time=300
uv run python -m tests.fuzz.read_field_bytes --seed fields && uv run python -m tests.fuzz.read_field_bytes --dict value_field.dict
uv run python -m tests.fuzz.read_field_bytes fields -dict=value_field.dict -max_total_time=300
uv run python -m tests.fuzz.read_acceptance_bytes --seed acceptances && uv run python -m tests.fuzz.read_acceptance_bytes --dict acceptance.dict
uv run python -m tests.fuzz.read_acceptance_bytes acceptances -dict=acceptance.dict -max_total_time=300
uv run python -m tests.fuzz.build_bytes --seed declarations && uv run python -m tests.fuzz.build_bytes --dict build.dict
uv run python -m tests.fuzz.build_bytes declarations -dict=build.dict -max_total_time=300
MATERICA_HYPOTHESIS_PROFILE=ci uv run pytest tests/property     # replays and shrinks what was found
mkdir smaller && uv run python -m tests.fuzz.jsonio_bytes -merge=1 smaller corpus   # what adds coverage
```

Run them from the repository root. libFuzzer writes new inputs into the corpus directory it is given, so it is
a copy, never `src/materica/data/conformance/`. To merge a corpus or minimise a crash, libFuzzer re-executes
its first argument; `jsonio_bytes.py` passes it `jsonio_bytes.sh`, which runs the module again with the same
interpreter. A replayed failure keeps the whitespace it was written with: the properties choose how a value
is written with a seeded `random.Random`, which shrinking cannot simplify, so only the value shrinks.

## Showing that it can fail

`seeded_fault.py` seeds three faults, each with its own message. One makes `parse` raise for an array whose
first item is an empty object, a shape no seed holds; another makes the read raise where two copies of the
target state its pin and are identical byte for byte, which a read must take as one record, beside an
unreadable source and without the hash suite: three draws that must meet. The third makes step 10 raise for a
temperature above 311 K stated with a plus or minus, beside a shear rate stated as a range other than 10 to
1000 1/s: no seed holds two of the three (18 hold a plus or minus on a temperature, at 310.15 K or below;
three state another range, with no plus or minus; none a temperature above 311 K), so the fuzzer has to change
two numbers of one seed, keeping the field through steps 8 and 9. Only the fourth target seeds it, since the
property targets draw conditions too, and it is instrumented by Atheris, as the core is, so that each part met
is new coverage. In ten local runs, six at a time, it was found after 84, 126, 147, 189, 216, 225, 236, 483,
531 and 601 s (Python 3.14, 2026-10-16), so the control runs the target twice side by side, each for up to 900
s, and passes where either finds it. The target's runs, the control's and the weekly one, pass
`-entropic_scale_per_exec_time=1`, which runs slow inputs less often and keeps every seed: one seed of 261 KB
costs about 52 times the others' mean an input, and without the flag the corpus fills with its derivatives
and a run slows as it goes (S2a-4's review B, M2). Four runs of 1,800 s each way, two at a time
(2026-10-17): with the flag 528 inputs a second, the fault found in two runs; without it 237, found in none. Rarer conjunctions tried first were missed: a temperature stated as a
range, with an `sd` entry, measured rather than set, in 600 s; one ending above 1000 1/s, in two runs of 600
s, since libFuzzer picks the number it changes after a random offset and an upper end two bytes after its
lower is seldom picked; one starting above 10 1/s, in one run of seven. The fault replaced, in S2a-3, the
step-8 fault of S2a-2's fix round (a constant above 1, measured above 311 K, whose statistics block represents
a population's spread, found after 22 to 279 s), once the target read steps 9 and 10; that one had replaced a
fault one digit from a seed that held two of its three parts. A refusal steps 8 to 10 miss is the oracles' to
see, which `tests/unit/test_fuzz_oracle.py` shows failing. With `MATERICA_FUZZ_SEEDED_FAULT=1`, the first two
targets must find the first, the third target the second and the fourth the third, and `python -m pytest -p
tests.fuzz.seeded_fault tests/property/...` must replay what the property targets saved and shrink it: the
read's properties, and HP12's and HP10's, which draw the stores the fault in the read lives in. With every HP
in the third target, it still found that fault after 6 to 15 s in eight local runs (Python 3.14, 2026-10-17),
each time by the read's own properties. CI's fuzz job does this first, against an empty example database,
before it fuzzes the core, and checks each step for the message of the fault it must find.

The S2 design's own control (its section 1.7) is a fourth fault, which S2b-1 put in real composition code: an
exception escapes for a composition whose `components` is empty, which step 8 must refuse.
`MATERICA_FUZZ_SEEDED_FAULT=composition` seeds it alone, in the third and the fourth target. The fourth finds
it at once, from PR-051's `no_component` among its seeds (1.7 s, Python 3.14, 2026-10-17; 1.5 s at S2b-2's
head, which reads evidence too, 2026-10-18). The third did not
find it, run as CI runs its control (180 s), nor in 600 s, nor in 600 s with inputs of up to 8,192 bytes from
the start (`-max_len=8192 -len_control=0`), nor in 600 s with the property strategies instrumented too, so
that each fault drawn is coverage, with inputs short or long. Random bytes given to HP3's third part alone
draw the fault in 17 of 3,000 inputs. The target's inputs are not random bytes: by default they grow from a
few bytes, where a record HP3 draws takes hundreds, a property among 35 takes their first byte, and each is a
mutation of one the fuzzer kept for new coverage. So CI's control keeps the three faults above, and the
composition's waits for a ruling on how target 3 should reach whole records (S2b-1's report).

S4a's control is a fault of another kind: one the read answers wrongly rather than raises at, so that only
the oracle can find it, here the reference model, which since S4a decides step 7 over alternatives with no
pick and no overlay as the read does. `MATERICA_FUZZ_SEEDED_FAULT=alternatives` seeds it alone, in the fourth
target: an alternative refused at step 9 for its unit alone is set aside where it is the third or a later
stored alternative (`seeded_fault.faulty_standing`). Of the 56 seed fields that hold alternatives, two hold
three or more, and none a unit other than the registered one past the second, so the fuzzer has to change
one; the target then fails at the model's assertion, "the implementation gives ..., the model ...".
`tests/unit/test_fuzz_oracle.py` shows the oracle failing on that shape. In two local runs side by side, as
CI's control runs the target, it was found after 6 and 80 s, each by one change to the third unit of the seed
that holds three density alternatives (`kg/m3` made `+g/m3` and `kg/m2`), each at the model's assertion
(Python 3.14, 2026-10-19). It is not in CI's control step: the control's runs and their length are the
maintainer's to set.

S3a's control is of S4a's kind, in step 8: a table over temperature whose first knot lies below 250 is refused
(`form_invalid`) where the text and the model read it past step 8 (`seeded_fault.faulty_points`).
`MATERICA_FUZZ_SEEDED_FAULT=tables` seeds it alone, in the fourth target. Of the seed fields that hold a
table over temperature (106 of 816 at S3a's head, read as JSON, 2026-10-20), none starts below 250 (the least
first knot is 250, and one table's `x` is empty, which item 1 refuses already), so the fuzzer has to lower
one's first knot, in a table no other fault makes `form_invalid`; the target then fails at the model's
assertion. In two local runs side by
side, as CI's control runs the target, it was found after 26 and 319 s, each by one change to a first knot of
280: a `-` inserted, in a table holding `points`, and the number halved, in a table stored as an alternative
(Python 3.14, 2026-10-20); four more found it after 16, 34, 57 and 250 s. Two faults tried first were missed
by two such runs of 600 s, about 1.2 million inputs each: a log-log table holding a `source_range`, which no
seed holds, since `linear` has to be overwritten whole or a `source_range` written in; and a `source_range`
reaching above 400, which 15 seed tables are one change from, its upper end two bytes after its lower, as
above. CI's control step runs it (maintainer, 2026-10-21) in two runs of its own side by side, each of up to
480 s, one and a half times the slowest of those six finds to the minute, as its runs of the step-10 fault
are of theirs, and passes where either finds it: a line of the model's assertion in which the implementation
gives `form_invalid` and the model does not.

S3b-2's control is of the first kind, an exception, in a table's value, which the fourth target reads at the
places table item 3 tells apart (`field_oracle.places`), one double above each edge among them: a read in the
interval just above an edge raises (`ArithmeticError`) where the value just above the edge lies outside 0.6 to
1.6 times the value just below, either way (`seeded_fault.faulty_value`). `MATERICA_FUZZ_SEEDED_FAULT=table_edges`
seeds it alone, in the fourth target. Of the 22 edges the seed tables hold twice in `x` (read as JSON,
2026-10-21), the ratio of the value above to the value below lies between 0.99 and 1.2, and the target reads
all 816 seeds with the fault seeded and finds nothing (`-runs=0`), so the fuzzer has to change a value at an
edge, as halving or doubling either one does, in a table that keeps its edge. A fault raising for every read
just above an edge, as the S3 design words it, every seed with an edge would hold, since the target reads there.
Its first narrowed form, a value below zero above the edge, was found in one of ten local runs of 600 s; its
second, one-sided (the value above below 0.6 of the value below), in two of ten, and in two more of 900 s after
764 and 752 s, about 5.9e-4 finds a second: it saw only half of the changes libFuzzer makes most to a number,
halving the value above or doubling the one below, and not doubling the value above or halving the one below.
Two-sided, in ten local runs, in pairs, each of up to 900 s with the arguments CI's control gives the target, it
was found in nine, after 65, 94, 174, 229, 246, 311, 311, 325 and 725 s, and missed once (Python 3.14, 2026-10-21;
each find a value at an edge doubled, halved or with digits inserted): a rate of 2.7e-3 finds a second.
CI's control step runs it in two pairs side by side, four runs of up to 900 s each, and passes where any of the
four reports the fault's message. At the rate measured, all four miss with about 1.1e-3 on a runner 1.4 times
slower than the laptop, and with about 7e-5 on one as fast, an estimate until CI's own runs measure the rate
there. A find in each run within 900 s on the runner's time is not met: one of the ten runs missed, and one found
it after 725 s, past the 643 s that 900 s are on a runner 1.4 times slower. The maintainer's ruling on the fuzz
controls gives them a job of their own, a runner for each pair; this control moves there when S4's piece builds
it.

S3c's control, for the fifth target, is of S4a's kind, in step 0: an extrapolation's `method` compared ignoring
case, so that `Constant` or `consumer_LAW` is taken where `declarations.md` section 4.1 allows `constant` or
`consumer_law` alone (`seeded_fault.faulty_extrapolation`). `MATERICA_FUZZ_SEEDED_FAULT=extrapolation_method`
seeds it alone, in the fifth target. Nothing raises: the read goes on, and the target's oracle, which holds an
extrapolation that breaks its shape to `request_incomplete` wherever it is located
(`acceptance_oracle.check_shape_refused`), finds it, as the model does. No seed holds such a method, and every
seed holding an extrapolation is one changed letter from one (2026-10-21). The S3 design names another fault, a
`law` that is a number taken under `constant`; a seed holds exactly that (PR-330's case of a law that is no
string), so the fuzzer would find it at once and show nothing. Under `consumer_law`, which no seed holds beside a
number, it is two aligned changes away, and five local runs of 600 s side by side, about 1.1 million inputs
each, found it in none. The method's fault, in ten local runs, five at a time side by side, each of
up to 600 s with the arguments CI's control gives the target, was found in all ten, after 7, 9, 25, 58, 84, 152,
154, 173, 174 and 482 s (Python 3.14, 2026-10-21; each find `constant` with one letter's case changed): a rate of
7.6e-3 finds a second. CI's control step runs it in four runs side by side, each of up to 480 s, the slowest find
to the minute, and passes where any of the four reports the oracle's message. At the rate measured, all four miss
with about 3e-5 on a runner 1.4 times slower than the laptop, an estimate until CI's own runs measure it. It moves
to the fuzz controls' own job when S4's piece builds it.

S4d's control, for the fourth target, is of S4a's kind, in step 7: a table alternative read outside its readable
range, at no edge and with no extrapolation that would cover it, refuses the field where the text sets it aside
(`seeded_fault.faulty_form_range`), where a value of the table's `y` lies below 900.
`MATERICA_FUZZ_SEEDED_FAULT=table_alternatives` seeds it alone, in the fourth target, which since S4d reads a
field's table alternatives at their places too (`field_oracle.alternative_places`). Nothing raises: the model's
assertion finds it. The S4 design's candidate, a log-log table alternative read outside its range refused, no seed
can show: of the 817 seeds, 57 hold alternatives, 23 of them 25 table alternatives, all linear, and the six read
outside their range at the target's 310.15 K each sit beside alternatives all set aside, where refusing the field
and setting the table aside give one answer (a `loglog` written into each of the six found nothing). Read at their
places, table alternatives show the fault ungated at once on four seeds, each a density table whose `y` is 916 to
1000, read just below its range beside a constant that stays there; gated, no seed shows it (817 of 817), and one
change does: a value of such a table's `y` lowered below 900, or, beside a viscosity table, whose `y` lies below
900 already, read outside its range at a place of its own, a byte of a constant's condition name, which leaves its
temperature unstated so that it stays (`tests/unit/test_fuzz_oracle.py` holds both, through the target's own
`test_one_input`). One dictionary operation reaches it by the second route alone: each of the dictionary's 279
entries, inserted at and written over every position of the 23 seeds holding table alternatives, shows it only on
`viscosity_alternatives_table_and_constant`, over its constant's `"temperature"` key, and none lowers a `y` below
900. In ten local runs, in pairs, each of up to 900 s with the arguments CI's control gives the target, it was
found in seven, after 125, 330, 447, 520, 628, 726 and 866 s, and missed three times (Python 3.14, 2026-10-22, at
1,000 to 1,710 inputs a second, two runs slowed by a test run beside them): a rate of 1.1e-3 finds a second, 0.80
a million inputs. The maintainer's ruling sets the fuzz controls a bar of two parts; this control fails the first
and meets the second at the rate measured. A find in each of ten runs within 900 s on the runner's time is not
met: three runs missed, and two found it after the 643 s that 900 s are on a runner 1.4 times slower (at 726 and
866 s). A weekly miss of at most 1e-3 is met at the rate measured, a point estimate: at it, four runs side by side
all miss with about 0.06 on a runner 1.4 times slower than the laptop, and twelve with about 2e-4; at its
one-sided 95 % lower bound, 5.2e-4 finds a second, twelve would all miss with about 0.018. So CI's control step
runs it in rounds of four side by side, each run of up to 900 s, another round only where no run of the round
before found it, three rounds at most (about 16 minutes on average, 45 at most), and passes where any run reports
a line of the model's assertion in which the implementation gives a table alternative's `outside_range` and the
model gives none. The rounds stay until the maintainer rules on them, as the table-value control above keeps its
four runs with the first part not met: accepted until the fuzz controls' own job exists, or replaced by a fault
that target 4 finds within 643 s in every run. The rate is an estimate until CI's own runs measure it; the control
moves to the fuzz controls' own job when S4's piece builds it.

S7a-1's control, for `build_bytes.py`, is of S4a's kind, in the declaration's own check: item 4 skips every
acceptance after a model's second (`seeded_fault.faulty_reasons`), so that a third acceptance without its
`reason` or `basis` is refused only as a member missing, BC-048, where the text gives BC-005.
`MATERICA_FUZZ_SEEDED_FAULT=declarations` seeds it alone, in `build_bytes.py`. Nothing raises, and its case
and pointer are ones the target allows, so only the target's relation to the build's reference model sees it,
as a line in which the model gives BC-005 at an acceptance after a model's second and the implementation does
not; the implementation's BC-048 there shows beside it only where the model gives none there, so the find asks
for the model's BC-005 alone, and a line with the model's BC-005 at acceptance 0 or 1, which the fault leaves
alone, is no find (`CONTROLS["declarations"]`'s `unless`, the control step's `declared_early`; a line holding
it at acceptance 0 or 1 and at a later one as well needs a second difference beside the fault, and reads as
none). The design's fault skipped every acceptance after a model's first: seven of the 162 seed declarations,
BC-005's arms of a second acceptance without its `reason` or `basis`, show that one unchanged, so the fuzzer
would find it at once and show nothing. No seed shows the narrowed one, and one change does: the seed that
holds such an acceptance at `/models/0/acceptances/1` written at `/models/0/acceptances/2`, one byte of its
pointer. Every seed passes the target's four relations, with no fault seeded and with this one (2026-10-26).
`measure.yml`'s fuzz kind ran it ten times with the fault seeded and ten with none (run 40263772231, Python
3.14): each run with the fault failed on it, after 28 to 63 s, four of them with the model's BC-005 alone, an
acceptance missing another member as well, which a find that also asked for the implementation's BC-048 read
as no find; each of the ten failing inputs passes the relations with no fault seeded. The ten with none found
nothing in 9,071 s. With the find as above but for its `unless` (run 40275055796), each of ten runs with the
fault found it, after 17 to 47 s, every line at acceptance 2 or 4, and each reads as a find with the `unless`
too; four of the ten with none ended on the thirteenth divergence (fixed on `main` since, below), after 215 to 882 s. The rate is
measured again with this find, and CI's control step runs it meanwhile in four runs side by side, each of up
to 900 s, the window of the bar the maintainer's ruling sets the fuzz controls, passing where any finds it;
their number and length are set from the rate measured. By the S7 design's budget rule the target joins the
`fuzz` job only where that job's slowest run on CI, and 5 minutes, come to 60 minutes at most; it took 126.7
(run 39743609131, 2026-10-22, which `ci.yml`'s comment on the job cites), so the target's own weekly fuzzing
runs in a row of its own beside the fuzz controls' job, which lands with the control's runs set from its rate.

S7a-2's control, for `build_bytes.py`, is the S7 design's fault in the build's verdict (its 6.5, `judge`):
`_covers` lets a waiver naming `condition_outside` and its condition cover it (`seeded_fault.faulty_covers`),
where `declarations.md` section 4.2 lets no waiver cover it. `MATERICA_FUZZ_SEEDED_FAULT=judge` seeds it alone,
in `build_bytes.py`. Nothing raises: the target's relation of section 4.2's own law finds a result accepted with
`condition_outside`, which no assumption covers and no correct build accepts (a `trainable` entry, which could,
the build does not read yet), and that line is the find (`CONTROLS["judge"]`, the control step's `judged`); the
results model's relation, checked after it, sees the fault too. Its seeds, by the design's scan: BC-038's
declaration, which holds such a waiver beside such a result, and the four other declarations whose cases give a
result `condition_outside`, each with the waiver planted where a first byte past the seeds picks it
(`build_bytes.PLANTED`). Under the fault, BC-038's seed and the planted BC-001 and BC-017 declarations fail at
that law, and the planted BC-027 one, whose `label_mismatch` keeps its result refused, at the results model's
relation alone, a line that is no find. The fault is the design's, unnarrowed: BC-038's seed shows it
unchanged, so a run finds it in its first pass over the seeds. Ten local runs, in pairs side by side with the
arguments CI's control step gives them, each found it after 1.0 to 1.5 s, the interpreter's start among them
(Python 3.14, 2026-10-27), and a run of 600 s with no fault seeded found nothing in 2,584,855 inputs (S7a-1's
smoke run before the results relations, 2,897,479). So the control shows the
target holding every report to the results relations and the find read as CI reads it, not the fuzzer reaching
a fault no seed holds, as S7a-1's narrowed fault does. A narrowed form exists: the same fault on a density
alone, which no seed shows and the planted BC-001 declarations do, one change of the first byte away; ten
local runs with the control step's arguments, in pairs side by side, each found it, after 60 to 739 s, a
median of 130 (2026-10-27). Run by the rule the other controls' runs follow, one and a half times the slowest
find, its two runs of 19 minutes would put the fuzz job's timeout past GitHub's 360 minutes, so it waits on
how its runs are set. CI's control step runs the design's form in two runs side by side, each of up to 60 s,
one and a half times the slowest find rounded up to the minute, and passes where either finds it.

The relation to the model holds the check to the model in both directions: where the model refuses a
declaration with every rule's refusals placed, the check gives its refusals, and where the model takes one
(`build_oracle.TAKEN`, its own words for a declaration that passes its check), the check refuses nothing. It
found, before any fuzzing, that the check and the model read a declaration apart in thirteen ways no build-check
case showed: by a sweep of every seed with each member replaced by a value of each JSON type, each string
edited, each member taken out, a member added and a list's entry repeated, and a random sweep of one to three
such changes; the thirteenth, by CI's fuzz runs with no fault seeded (run 40275055796, four of ten). They are
fixed on `main`: the model's in #103 (the thirteenth among them) and the check's in #104, the refusal paragraph
rewritten beside them, and `build_oracle.KNOWN_DIVERGENCES` is empty. `tests/unit/test_fuzz_build_oracle.py`
holds each one's example and shows the check and the model giving the same refusals on it, with nothing
listed: a waiver's `label` of another JSON type; a waiver's `condition` beside a `code` missing or of another
type; a waiver's `condition` of another type; a `trainable` entry's record beside a fault, or over a domain or
a path; a name given twice beside a fault of an entry; an object holding `status` off a status object's
shape, and a `within` that is an object; a requirement's `label` beside an unregistered field; the members
inside a member at fault; the members inside one of two exclusive alternatives; a distribution's parameters
beside a token at fault; a combination beside its fields at fault; a `region_conditions` of another type; a
nominal's `params` beside a `field` that names no registered field.

The mapping and its mechanism stay, for the next divergence the target finds: a divergence is listed in
`KNOWN_DIVERGENCES` only with its open point, a function that names, of the refusals one side gives and the
other does not, those it explains, and an example in `tests/unit/test_fuzz_build_oracle.py` that the relation
lets through with it listed and fails without it. These are the divergences found so far, not
all there are. With the thirteen fixed and the list empty, the sweeps find nothing, on the 158 seed declarations `main` then
held (none of 154,682 single changes, 149,976 pairs of changes to the members of one object, 29,619 added
members of another kind beside a second change, 935,733 random changes in two runs of 300 s, and none of 2,200
declarations HP41 and HP42 draw; 2026-10-26). With the fault seeded
the single-change sweep shows it on the same 13 changes.

## In CI

The `fuzz` job runs weekly and on a manual run only, on Python 3.14, after the Hypothesis job: the control
above, then each target for `fuzz_seconds` (300 by default, an input of the manual run), then `pytest
tests/property`, but the writer's properties, the validators' agreement and the mutant searches, to replay and
shrink what was found. It
starts from the union of the example databases the Hypothesis job's `json`, `records`, `conditions` and
`relations` shards just saved, or the latest each saved where that job did not run (a manual run with
`fuzz_only`), and saves the two jobs' finds together, for each shard. Target 1's corpus is cached from run to
run, seeded afresh each time, and merged into a fresh directory before it is saved, so that it keeps only the
inputs that add coverage. The job keeps the inputs that failed.

The control step prints each run's find time in the job's log, a `fuzz-control` line a run and a
`fuzz-control-summary` line a control, and the rates quoted above are local until CI's runs are collected.
