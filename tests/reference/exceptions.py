# SPDX-License-Identifier: Apache-2.0
"""The case files of a read the reference model does not agree with, grouped by kind, each kind with its
reason: the exact list `test_cases.py` holds the model to (the maintainer's ruling 3 on S2a-1's open points).
Every kind is a read outside the model's scope, on which it gives no verdict, never a pass; each kind names
the detail of that outcome, so that a file the model gives no verdict on for another reason fails.

`BUILD_EXCEPTIONS` is the same list for the build-check case files and the build's models: `build_model.py`,
the declaration's own check, and `build_results_model.py` past it. `RESULTS_NOT_DECIDED` gives, by kind, what
the results model does not decide, each with its reason."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal


@dataclass(frozen=True)
class Excepted:
    reason: str
    outcome: Literal["differs", "no verdict"]
    case_files: frozenset[str]
    detail: str | None = None  # the outcome's detail every listed file gives, where the kind names one


EXCEPTIONS: Final[Mapping[str, Excepted]] = {
    "picks": Excepted(
        ("A pick is checked and applied at step 7 (S4); the model reads alternatives with no pick alone."),
        "no verdict",
        frozenset(
            {
                "PR-044.entry_not_object_with_pick.json",
                "PR-304.pick_absent_field.json",
                "PR-304.pick_alternative_not_met.json",
                "PR-304.pick_at_interval_not_applied.json",
                "PR-304.pick_at_record_and_interval_not_applied.json",
                "PR-304.pick_at_record_and_region_not_applied.json",
                "PR-304.pick_at_unnamed_overlay_not_applied.json",
                "PR-304.pick_broken_alternatives.json",
                "PR-304.pick_counts_set_aside.json",
                "PR-304.pick_fault_in_other_refuses_nothing.json",
                "PR-304.pick_index_1e0.json",
                "PR-304.pick_index_huge.json",
                "PR-304.pick_index_minus_zero.json",
                "PR-304.pick_index_one_point_zero.json",
                "PR-304.pick_interval_nominal_applied.json",
                "PR-304.pick_kept_table_extrapolation_applied.json",
                "PR-304.pick_no_location_not_applied.json",
                "PR-304.pick_on_field_without_alternatives.json",
                "PR-304.pick_other_field_not_applied.json",
                "PR-304.pick_other_hash_not_applied.json",
                "PR-304.pick_other_record_not_applied.json",
                "PR-304.pick_past_last.json",
                "PR-304.pick_reads_named.json",
                "PR-330.overlay_acceptance_other_field_without_overlay.json",
                "PR-330.pick_field_not_registered.json",
                "PR-330.pick_index_fractional.json",
                "PR-330.pick_index_missing.json",
                "PR-330.pick_index_negative.json",
                "PR-330.pick_index_not_number.json",
                "PR-330.pick_near_typo_indices.json",
                "PR-330.pick_other_field_index_fractional.json",
                "PR-330.two_picks_one_field.json",
                "PR-330.two_picks_one_field_same_index.json",
                "PR-330.two_picks_one_field_two_records.json",
                "PR-330.two_picks_other_field.json",
                "PR-330.two_picks_two_fields_read.json",
            }
        ),
        detail="a pick acceptance (S4)",
    ),
    "overlays": Excepted(
        ("An overlay is resolved and applied at step 6 (S4); the model applies none."),
        "no verdict",
        frozenset(
            {
                "PR-002.overlay_base_without_content_hash.json",
                "PR-007.overlay_acceptance_names_interface.json",
                "PR-007.overlay_acceptance_names_material.json",
                "PR-011.base_body_slip_fluids.json",
                "PR-011.base_envelope_slip_crad.json",
                "PR-011.base_field_fault_not_refused.json",
                "PR-011.base_section_member_slip_not_refused.json",
                "PR-011.base_section_specimen_slip_not_refused.json",
                "PR-011.fit_overlay_read.json",
                "PR-011.overlay_body_slip_replace.json",
                "PR-011.overlay_envelope_slip_crad.json",
                "PR-011.overlay_field_shape_refused.json",
                "PR-011.overlay_other_field_shape_not_checked.json",
                "PR-011.replaces_whole_field.json",
                "PR-012.overlay_named_for_other_field.json",
                "PR-012.overlay_named_for_other_field_not_resolved.json",
                "PR-039.base_content_hash_uppercase.json",
                "PR-039.base_other_content_hash.json",
                "PR-039.base_other_id.json",
                "PR-039.base_stale_version.json",
                "PR-041.one_overlay_named_twice.json",
                "PR-041.other_field_overlay_no_conflict.json",
                "PR-041.same_id_and_version_other_hash_conflict.json",
                "PR-041.same_overlay_two_fields.json",
                "PR-041.two_overlays_conflict.json",
                "PR-042.broken_marker_in_value_only.json",
                "PR-042.broken_withheld_marker.json",
                "PR-042.fit_over_withheld.json",
                "PR-042.measurement_over_withheld.json",
                "PR-042.purpose_fil_in.json",
                "PR-042.purpose_fil_in_not_replacing_read_field.json",
                "PR-042.purpose_fil_in_over_withheld.json",
                "PR-042.withheld_evidence_entry.json",
                "PR-042.withheld_field_not_replaced.json",
                "PR-042.withheld_in_one_alternative.json",
                "PR-042.withheld_marker_in_statistics_only.json",
                "PR-042.withheld_other_key.json",
                "PR-042.withheld_value_beside_unknown_form.json",
                "PR-046.does_not_replace_read_field.json",
                "PR-046.one_of_two_does_not_replace.json",
                "PR-046.other_key_base_lacks.json",
                "PR-046.other_key_field_lacked_in_held_section.json",
                "PR-106.fill_in_read.json",
                "PR-107.base_holds_alternatives.json",
                "PR-107.base_version_not_string.json",
                "PR-107.base_without_document.json",
                "PR-107.both_hold_alternatives.json",
                "PR-107.fill_in_alternative_picked.json",
                "PR-107.fill_in_alternatives_one_mismatch.json",
                "PR-107.fill_in_identifier_not_string.json",
                "PR-107.fill_in_other_identifier.json",
                "PR-107.fill_in_other_version.json",
                "PR-107.fill_in_version_not_string.json",
                "PR-107.fill_in_without_document.json",
                "PR-304.overlay_alternatives_no_pick.json",
                "PR-304.pick_at_base_of_overlaid_field.json",
                "PR-304.pick_at_overlay.json",
                "PR-304.pick_at_overlay_named_for_other_field.json",
                "PR-304.pick_at_overlay_past_last.json",
                "PR-304.pick_at_overlay_single_value.json",
                "PR-307.at_base_of_overlaid_field.json",
                "PR-307.at_overlay_not_applied.json",
                "PR-310.overlay_absent.json",
                "PR-310.overlay_hash_mismatch.json",
                "PR-310.overlay_hash_mismatch_no_hs.json",
                "PR-310.overlay_other_version.json",
                "PR-310.overlay_pin_mismatch.json",
                "PR-310.overlay_unreadable_source.json",
                "PR-310.two_overlays_two_faults.json",
                "PR-330.overlay_acceptance_without_overlay.json",
                "PR-330.overlay_reference_without_content_hash.json",
            }
        ),
        detail="an overlay acceptance (S4)",
    ),
    "trainable": Excepted(
        (
            "A read goes on under a `trainable` acceptance, the one a build makes, past the reasons "
            "`read_side_contract.md` section 3's stop rule names (S7a-4); the model applies none."
        ),
        "no verdict",
        frozenset({"PR-339.across_edge_no_value.json"}),
        detail="a trainable acceptance (S7a-4)",
    ),
}


# The build-check files the build's models (`build_model.py`, and past the declaration
# `build_results_model.py`) do not agree with, by kind: none today. Until S7a-2m the build model gave no
# verdict past the declaration, and S7a-2's 57 files were listed here under the kind
# `past_the_declaration`; each now agrees.
BUILD_EXCEPTIONS: Final[Mapping[str, Excepted]] = {}

# What the build's results model does not decide, by the kind its `UNDECIDED` names, each with its reason:
# a declaration that reaches one gives no verdict, never a pass, and a file it gives one on is listed above
# under that kind, with the detail the model gives.
RESULTS_NOT_DECIDED: Final[Mapping[str, str]] = {
    "label_trust": (
        "A waiver naming a label covers its reason only on a result whose stored label is that label and is "
        "trusted (`declarations.md` section 4.1 item 4). Label trust comes right after 0.1.0.dev4 "
        "(maintainer, 2026-10-21: dev4 is S7a-1 and S7a-2 without label trust), so a waiver resting on a "
        "label that would otherwise cover a reason gives no verdict, counted, never a pass; BC-050's six "
        "arms of it wait for it."
    ),
    "specimen_differences": (
        "Specimen differences and combinations are S7a-3's (the S7 design, 1.3): a model whose target names "
        "a fact, or that lists combinations, gives no verdict. A target of `{}` names none, and a result "
        "lists no difference."
    ),
    "trainable": (
        "A `trainable` entry gives each read of its field there a `trainable` acceptance, under which the "
        "read goes on past its reasons (`declarations.md` section 7): S7a-4's, and the read model gives no "
        "verdict on the acceptance either."
    ),
    "watches": (
        "The watches are S7a-4's (`declarations.md` section 8); the report leaves them out, as a build that "
        "does not emit them does, and a case that compares them gets no verdict where every member the model "
        "decides agrees. S7a-2's files compare none; S7a-1's, which do, expect a refusal."
    ),
    "picks_and_overlays": (
        "When a pick or an overlay is applied is not yet covered (the build's terms), and the rows of "
        "section 4.2 that a pick or an overlay alone reaches (`no_pick`, `overlay_scope_mismatch`) are "
        "S7c's; a declaration holding a pick or an overlay gives no verdict at the declaration already."
    ),
    "alternative_unnamed": (
        "Which alternative is the one left is step 7's: where a result rests on one alternative, names none "
        "in its reasons, and the alternatives store different labels, the model cannot say which label to "
        "check (its open point `alternative_a_result_rests_on`)."
    ),
    "the_read": "A read the read model gives no verdict on, for the reason it gives.",
}
