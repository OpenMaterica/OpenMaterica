# SPDX-License-Identifier: Apache-2.0
"""The case files of a read the reference model does not agree with, grouped by kind, each kind with its
reason: the exact list `test_cases.py` holds the model to (the maintainer's ruling 3 on S2a-1's open points).
Every kind is a read outside the model's scope, on which it gives no verdict, never a pass; each kind names
the detail of that outcome, so that a file the model gives no verdict on for another reason fails.

`BUILD_EXCEPTIONS` is the same list for the build-check case files and the build's own model
(`build_model.py`), which decides the declaration's own check alone."""

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


BUILD_EXCEPTIONS: Final[Mapping[str, Excepted]] = {
    "past_the_declaration": Excepted(
        (
            "A declaration that passes its own check is read, and what the build gives then (results, the "
            "verdict, `unused`, specimen differences, watches) is S7a-2's to S7a-4's; the model decides the "
            "declaration's own check alone, and gives no verdict past it."
        ),
        "no verdict",
        frozenset(
            {
                "BC-001.condition_outside_at_another_temperature.json",
                "BC-001.declared_range_against_a_stated_value.json",
                "BC-001.met_at_the_declared_temperature.json",
                "BC-002.both_records_listed.json",
                "BC-002.listed_record_absent_from_the_store.json",
                "BC-002.one_of_two_records_listed.json",
                "BC-003.field_read_with_no_requirement.json",
                "BC-003.field_read_with_no_requirement_waived.json",
                "BC-006.every_kind_s7a_2_reads.json",
                "BC-006.nominal_not_met_stays_not_met.json",
                "BC-006.waived_unknown_stays_unknown.json",
                "BC-009.extrapolation_applied.json",
                "BC-009.implied_condition_applied.json",
                "BC-009.nominal_applied.json",
                "BC-009.one_waiver_index.json",
                "BC-009.two_acceptances_indexes.json",
                "BC-010.all_accepted.json",
                "BC-010.each_model_judged_by_its_own_acceptances.json",
                "BC-010.one_accepted_one_not_in_one_model.json",
                "BC-010.two_models_each_not_accepted.json",
                "BC-016.label_free_judgement_waiver.json",
                "BC-016.waiver_at_another_copy_of_the_record.json",
                "BC-016.waiver_at_one_of_two_records.json",
                "BC-016.waiver_covers_each_alternatives_reason.json",
                "BC-016.waiver_for_another_code.json",
                "BC-016.waiver_for_another_condition.json",
                "BC-016.waiver_for_another_field.json",
                "BC-017.fills_an_unstated_condition.json",
                "BC-017.implied_value_outside_the_tolerance.json",
                "BC-017.not_checked_condition_not_filled.json",
                "BC-017.stated_condition_not_filled.json",
                "BC-019.at_an_edge_extrapolation_unused.json",
                "BC-019.outside_range_under_an_extrapolation.json",
                "BC-019.outside_range_without_an_extrapolation.json",
                "BC-019.want_bounds_refused_though_an_extrapolation_names_it.json",
                "BC-020.nominal_inside_the_bounds.json",
                "BC-020.nominal_outside_the_bounds.json",
                "BC-020.want_mismatch_at_step_0_nominal_unused.json",
                "BC-020.want_mismatch_its_assumption_does_not_name.json",
                "BC-027.label_mismatch_beside_condition_outside.json",
                "BC-027.required_label_absent.json",
                "BC-027.stored_label_differs.json",
                "BC-028.one_model_one_record.json",
                "BC-028.two_models_over_one_record.json",
                "BC-038.waiver_of_condition_outside.json",
                "BC-038.waiver_of_form_invalid.json",
                "BC-038.waiver_of_label_mismatch.json",
                "BC-038.waiver_of_no_pick.json",
                "BC-049.absent_record_gives_no_not_reviewed.json",
                "BC-049.not_checked_gives_not_reviewed.json",
                "BC-049.not_reviewed_waived.json",
                "BC-049.reviewed_value.json",
                "BC-049.reviewed_value_met.json",
                "BC-049.unknown_review_result_read_as_not_checked.json",
                "BC-053.implied_condition_given_not_applied.json",
                "BC-053.unused_per_model.json",
                "BC-053.waiver_at_another_record.json",
            }
        ),
        detail="past the declaration (S7a-2 to S7a-4)",
    ),
}
