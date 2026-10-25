# SPDX-License-Identifier: Apache-2.0
"""The relations the build's fuzz target holds a report of results to (the S7 design's 6.5, "Fuzzing"),
importable without Atheris so that `tests/unit/test_fuzz_build_results.py` can show each failing: two that
need no model, cheap enough to check on every input.

- 4.2's own law: an accepted result holds no `not_met` reason that no assumption and no `trainable`
  acceptance covers (`declarations.md` section 4.2: the rows that cover a `not_met` reason are an
  extrapolation's and a nominal's, "only on a result whose `assumption` names it", the `trainable` entry's,
  "on a result that carries a value", and an `overlay_scope`'s, whose `overlay_scope_mismatch` this version
  never gives, an overlay being S7c's);
- the refusal law: the report is refused exactly where it holds a refusal or a result not accepted (section 2
  item 5 and the report's paragraph).

The third relation the design names, the build model's verdict where it decides, waits for the results model
(#98); and the target that calls these, `build_bytes.py`, with its control (`_covers` letting a waiver naming
`condition_outside` cover it, which 4.2's own law sees), arrives with S7a-1's (#100).
"""

from materica.core.report import BuildReport, BuildResult
from materica.core.vocabulary import VOCABULARY

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
