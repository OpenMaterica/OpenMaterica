# SPDX-License-Identifier: Apache-2.0
"""The relations the build's fuzz target holds a report of results to (the S7 design's 6.5, "Fuzzing"),
importable without Atheris so that `tests/unit/test_fuzz_build_results.py` can show each failing: two that
need no model, cheap enough to check on every input, and the build's results model where it decides.

- 4.2's own law: an accepted result holds no `not_met` reason that no assumption and no `trainable`
  acceptance covers (`declarations.md` section 4.2: the rows that cover a `not_met` reason are an
  extrapolation's and a nominal's, "only on a result whose `assumption` names it", the `trainable` entry's,
  "on a result that carries a value", and an `overlay_scope`'s, whose `overlay_scope_mismatch` this version
  never gives, an overlay being S7c's);
- the refusal law: the report is refused exactly where it holds a refusal or a result not accepted (section 2
  item 5 and the report's paragraph).

- the model: where the build's results model (`tests/reference/build_results_model.py`) decides and both it
  and the build take the declaration, each result's status, reasons, verdict, `accepted_by` and
  `not_accepted`, the acceptances unused and `refused` are the model's. The declaration's own refusals are
  left to the relation `build_oracle.check_declaration` holds them to, with its exemptions (a refusal of the
  model's not placed, a known divergence), which runs after these: compared here first, they would raise
  another line than that relation's, which `build_bytes.py`'s control `declarations` is found by.

`build_bytes.py` holds every report the build gives to these, the two cheap ones first; the design's control
for it (`_covers` letting a waiver naming `condition_outside` cover it) 4.2's own law and the model both see.
"""

import json
from collections.abc import Collection, Mapping, Sequence
from typing import cast

from materica.core.report import BuildReport, BuildResult
from materica.core.vocabulary import VOCABULARY
from materica.shapes import Suite
from tests.reference import build_model, build_results_model
from tests.reference.read_model import NoVerdict

# The `not_met` reasons a row of section 4.2 covers by an assumption, and the kind the assumption names.
ON_AN_ASSUMPTION = {"outside_range": "extrapolation", "want_mismatch": "nominal"}
# The trainable row's: "a condition reason, `outside_range`, `range_unstated`, `outside_coverage` ... on a
# field listed in `trainable`".
TRAINABLE = frozenset({"outside_range", "range_unstated", "outside_coverage"})


def covered_without_a_waiver(result: BuildResult, code: str) -> bool:
    """Whether a `not_met` reason of `code` can be covered on `result`: by the assumption its row names, or
    by the result's `trainable` acceptance."""
    assumption = result.assumption
    named = None if assumption is None else assumption.get("acceptance")
    if code in ON_AN_ASSUMPTION and named == ON_AN_ASSUMPTION[code]:
        return True
    trainable = code in TRAINABLE or code.startswith("condition_")
    return result.trainable_by is not None and trainable and result.read is not None


def check_results(report: BuildReport) -> None:
    """The report held to 4.2's own law and the refusal law."""
    for result in report.results:
        if not result.accepted:
            continue
        for reason in result.reasons:
            if VOCABULARY.reasons[reason.code].status == "not_met":
                assert covered_without_a_waiver(result, reason.code), (
                    f"{result.model} {result.record.id} {result.field} accepted with {reason.code}, which no "
                    "assumption or trainable acceptance covers"
                )
    refused = bool(report.refusals) or any(not result.accepted for result in report.results)
    assert report.refused == refused, (
        f"refused {report.refused}, where its refusals and results give {refused}"
    )


# The build's results model (`tests/reference/build_results_model.py`): a result by its model, record and
# field, and what the relation compares of it.
ResultKey = tuple[str, tuple[str, str, str], str]
Compared = tuple[object, ...]


def _reason_key(reason: Mapping[str, object]) -> tuple[object, ...]:
    alternative = reason.get("alternative")
    return (
        reason.get("code"),
        reason.get("condition"),
        None if alternative is None else int(cast(float, alternative)),
    )


def _compared(result: Mapping[str, object]) -> Compared:
    """What the relation compares of a result, as JSON: its status, its reasons as a multiset, the verdict,
    `accepted_by` as a set and `not_accepted` as a multiset."""
    reasons = cast(list[Mapping[str, object]], result["reasons"])
    not_accepted = cast(list[Mapping[str, object]], result["not_accepted"])
    return (
        result["status"],
        tuple(sorted(map(_reason_key, reasons), key=repr)),
        result["accepted"],
        tuple(sorted({int(index) for index in cast(list[float], result["accepted_by"])})),
        tuple(sorted(map(_reason_key, not_accepted), key=repr)),
    )


def _keyed(results: Sequence[Mapping[str, object]]) -> dict[ResultKey, Compared]:
    keyed: dict[ResultKey, Compared] = {}
    for result in results:
        record = cast(Mapping[str, str], result["record"])
        key = (
            str(result["model"]),
            (record["id"], record["version"], record["content_hash"]),
            str(result["field"]),
        )
        keyed[key] = _compared(result)
    return keyed


def check_against_the_model(
    declaration: bytes, sources: Sequence[bytes], claims: Collection[Suite], report: BuildReport
) -> None:
    """The report against the build's results model where the model decides (the S7 design's 6.5) and both
    it and the build take the declaration: each result's status, reasons, verdict, `accepted_by` and
    `not_accepted`, the unused acceptances and `refused`; nothing where the model gives no verdict, and
    nothing where either refuses the declaration, whose refusals `build_oracle.check_declaration` holds."""
    modelled = build_results_model.check_build(declaration, sources, frozenset(claims))
    if isinstance(modelled, NoVerdict | build_model.Refused) or report.refusals:
        return
    given = json.loads(json.dumps(report.to_json()))
    found_results = _keyed(given["results"])
    wanted_results = _keyed(modelled.results)
    assert found_results.keys() == wanted_results.keys(), (
        f"results {sorted(found_results)}, the model's {sorted(wanted_results)}"
    )
    for key, wanted_one in wanted_results.items():
        assert found_results[key] == wanted_one, f"{key}: {found_results[key]}, the model's {wanted_one}"
    found_unused = sorted((one["model"], int(one["acceptance"])) for one in given["unused"])
    wanted_unused = sorted(
        (str(one["model"]), int(cast(float, one["acceptance"]))) for one in modelled.unused
    )
    assert found_unused == wanted_unused, f"unused {found_unused}, the model's {wanted_unused}"
    assert report.refused == modelled.refused, f"refused {report.refused}, the model's {modelled.refused}"
