# SPDX-License-Identifier: Apache-2.0
"""The controls of the feature audits of the json and records shards' properties that declare features by
their chances (`@pytest.mark.chances`), of the conditions shard's, steps 9 and 10's and the result's, which
declare them by their chances or draw them alike (`@pytest.mark.drawn`), of HP12's and HP4's form of the field
read (S2b-1, and PR #37's review), of S2b-2's evidence and nominal, of the relations shard's audit of the
monotonicity relations' worlds, by their chances, of S4a's outcome of step 7, drawn first, of HP12's draws of
S4a's alternatives, by their chance, of the regions where a planned search's mutant shows, each held on the
property whose own draws the search stands in for, by their chances, of S3a's HP13 to HP16, each drawing its
fault, kind or way first, among them the regions of HP13's planned searches, and of S3b-2's HP20 to HP23,
HP21's relation, the monotonicity property over a table, HP12's table part and HP1, HP2 and HP11's table
reads, each drawing its way or kind first, and the monotonicity property's worlds stated without origin, by
their chance, of S3c's HP24 to HP26 and the monotonicity property over an extrapolation, each drawing its way
first, and that property's worlds stated without origin, by their chance, of S4d's HP39, the others' outcome
drawn first and the table's way by its chance, and HP12's part over tables among alternatives, its part drawn
first, and of S7a-1's HP41 and HP42, each part drawing its way first: run at the `ci` profile's examples with
a generator that stops producing one of them, each property fails its audit, on that feature alone; a
parametrised property, on one of its parameters, by the marks that parameter carries. The controls of the
floors held at `deep` alone, which run where `deep` runs, are in
`tests/property/test_model_deep_floor_controls.py` and use the run defined here. Outside `tests/property/`,
whose audits would fail these runs too."""

import sys
from collections.abc import Callable
from typing import NamedTuple

import pytest
from hypothesis import HealthCheck, reject, settings
from hypothesis import strategies as st

from materica.core.jsonio import JsonValue
from tests.conftest import EXAMPLES
from tests.property import audits, result_strategies
from tests.property import test_alternatives_properties as alternatives_properties
from tests.property import test_canonical_properties as canonical_properties
from tests.property import test_condition_properties as condition_properties
from tests.property import test_declaration_properties as declaration_properties
from tests.property import test_evaluate_properties as evaluate_properties
from tests.property import test_extrapolation_properties as extrapolation_properties
from tests.property import test_hashing_properties as hashing_properties
from tests.property import test_invariance_properties as invariance_properties
from tests.property import test_jsonio_properties as jsonio_properties
from tests.property import test_model_properties as model_properties
from tests.property import test_monotonicity_properties as monotonicity_properties
from tests.property import test_read_properties as read_properties
from tests.property import test_result_properties as result_properties
from tests.property import test_slip_properties as slip_properties
from tests.property import test_table_alternatives_properties as table_alternatives_properties
from tests.property import test_table_form_properties as table_form_properties
from tests.property import test_table_read_properties as table_read_properties
from tests.property import test_value_field_properties as value_field_properties
from tests.property import test_version_properties as version_properties
from tests.property.result_strategies import JsonObject


class Control(NamedTuple):
    test: Callable[..., None]  # the property, as pytest runs it
    never: str  # the feature its generator stops producing
    # The checks of the property's law it skips: the audit counts the features, which the checks do not
    # change, and skipping them saves most of the run.
    skipped: tuple[str, ...]
    parameters: tuple[tuple[str, object], ...] = ()  # of a parametrised property, the one it runs with
    # How the generator stops producing the feature, where rejecting each example that shows it would stop
    # another feature's draws too; by default, that rejection.
    stops: Callable[[pytest.MonkeyPatch], None] | None = None


def strip_unknown_members(value: JsonValue) -> None:
    if isinstance(value, dict):
        value.pop("x_unknown_member", None)
        for member in value.values():
            strip_unknown_members(member)
    elif isinstance(value, list):
        for item in value:
            strip_unknown_members(item)


def without_unknown_members(monkeypatch: pytest.MonkeyPatch) -> None:
    """HP12's values with no member the reader does not know: each field `result_strategies.enriched` draws
    loses the member it planted, and the draws are otherwise the same. Its region of a constant under
    `want: bounds` plants the member in every draw (`model_strategies.REGIONS`), so rejecting each example
    that shows the member stops that region too. A derandomised run draws by the property's source, so an edit
    of the property draws another stream: after one (2026-10-21) the run held the region in 4 of 2,000
    examples, below its floor of 20, where main's had held it above."""
    drawn = result_strategies.enriched

    @st.composite
    def enriched(draw: st.DrawFn, field: JsonObject, *, unknown_member: bool = False) -> tuple[str, ...]:
        shown: tuple[str, ...] = draw(drawn(field, unknown_member=unknown_member))
        strip_unknown_members(field)
        return tuple(name for name in shown if name != "unknown_member")

    monkeypatch.setattr(result_strategies, "enriched", enriched)


CONTROLS = [
    Control(jsonio_properties.test_written_values_read_back, "three_deep", ("check_reads_back",)),
    Control(canonical_properties.test_output_matches_rfc8785, "negative_zero", ("check_matches_rfc8785",)),
    Control(
        hashing_properties.test_editing_any_leaf_the_hash_covers_changes_it,
        "edited_inside_a_provenance_object",
        ("check_edit",),
    ),
    Control(
        hashing_properties.test_the_hash_ignores_what_it_leaves_out,
        "card_below_the_top",
        ("check_invariance",),
    ),
    Control(version_properties.test_versions_order_as_their_integers, "decided_by_major", ("check_order",)),
    # The read's outcome is a feature, so the first law's check runs; the others' laws read again, skipped.
    Control(read_properties.test_a_read_never_raises_and_gives_each_reason_once, "malformed", ()),
    Control(
        read_properties.test_the_order_and_identical_copies_of_the_sources_change_nothing,
        "malformed",
        ("check_order_and_copies",),
    ),
    Control(
        read_properties.test_a_record_of_another_identity_changes_nothing,
        "malformed",
        ("check_other_identity",),
    ),
    Control(
        read_properties.test_an_unreadable_source_turns_only_absent_or_pin_mismatch_into_malformed,
        "malformed",
        ("check_unreadable",),
    ),
    Control(
        read_properties.test_a_request_member_the_shape_does_not_name_changes_nothing,
        "malformed",
        ("check_unnamed",),
    ),
    Control(
        value_field_properties.test_members_the_reader_does_not_know_change_nothing,
        "faulty_base",
        ("check_ignored",),
    ),
    Control(
        value_field_properties.test_one_fault_gives_its_refusal_and_no_other_part_1,
        "region_derivation",
        ("check_one_fault",),
    ),
    Control(
        value_field_properties.test_one_fault_gives_its_refusal_and_no_other_part_2,
        "region_derivation_inputs",
        ("check_one_fault",),
    ),
    Control(
        value_field_properties.test_one_fault_gives_its_refusal_and_no_other_part_2,
        "form_composition",
        ("check_one_fault",),
    ),
    Control(
        value_field_properties.test_one_fault_gives_its_refusal_and_no_other_part_3,
        "region_component",
        ("check_one_fault",),
    ),
    Control(
        value_field_properties.test_one_fault_gives_its_refusal_and_no_other_part_4,
        "region_evidence_report",
        ("check_one_fault",),
    ),
    Control(
        condition_properties.test_each_row_of_the_table_and_the_conditions_it_checks,
        "required_with_its_token",
        ("check_against_the_oracle",),
    ),
    Control(
        condition_properties.test_the_registered_unit_passes_step_9_however_escapes_write_it,
        "input_fact",
        ("check_registered",),
    ),
    Control(
        condition_properties.test_one_fault_of_step_10_gives_its_reason_beside_the_others,
        "two_faults",
        ("check_one_fault",),
    ),
    Control(
        condition_properties.test_members_the_reader_does_not_know_change_nothing_steps_9_and_10_read,
        "implied_value",
        ("check_ignored",),
    ),
    Control(
        condition_properties.test_any_other_unit_gives_unit_mismatch_with_its_condition,
        "status_object",
        ("check_refused",),
        (("place", "plus_minus"),),
    ),
    Control(
        result_properties.test_a_read_gives_a_result_whose_reasons_are_the_tables,
        "alternatives_broken",
        ("check_totality",),
    ),
    Control(
        result_properties.test_what_a_read_returns_is_as_stored_and_shares_nothing,
        "negative_zero",
        ("check_returned_as_stored",),
    ),
    *(
        Control(monotonicity_properties.test_the_worlds_hold_the_shapes_the_restrictions_are_for, shape, ())
        for shape in monotonicity_properties.WORLD_SHAPES
    ),
    Control(
        result_properties.test_what_a_read_returns_is_as_stored_and_shares_nothing,
        "form_interval",
        ("check_returned_as_stored",),
    ),
    Control(
        model_properties.test_the_read_agrees_with_the_model_on_values_and_alternatives,
        "form_composition",
        ("check_outcome",),
    ),
    Control(
        model_properties.test_the_read_agrees_with_the_model_on_values_and_alternatives,
        "form_evidence",
        ("check_outcome",),
    ),
    Control(
        result_properties.test_what_a_read_returns_is_as_stored_and_shares_nothing,
        "form_evidence",
        ("check_returned_as_stored",),
    ),
    Control(
        result_properties.test_a_nominal_supplies_its_value_and_the_assumption_it_rests_on,
        "nominal_on_a_bound",
        ("check_nominal_supplied",),
    ),
    Control(
        result_properties.test_a_nominal_supplies_its_value_and_the_assumption_it_rests_on,
        "behind_another",
        ("check_nominal_supplied",),
    ),
    Control(
        invariance_properties.test_a_fault_in_another_field_or_section_never_changes_the_read,
        "form_interval",
        ("check_isolated",),
    ),
    Control(
        invariance_properties.test_a_fault_in_the_read_fields_section_specimen_refuses_it,
        "form_composition",
        ("check_refused",),
    ),
    Control(
        invariance_properties.test_a_fault_in_another_field_or_section_never_changes_the_read,
        "form_evidence",
        ("check_isolated",),
    ),
    # The regions where a planned search's mutant shows, each held to its floor on the property whose own
    # draws the planned search stands in for (`tests/property/README.md`, "Mutants").
    Control(
        hashing_properties.test_editing_any_leaf_the_hash_covers_changes_it,
        "edited_below_review_or_copy_in_a_non_object_provenance",
        ("check_edit",),
    ),
    Control(
        slip_properties.test_one_slip_is_what_the_neighbour_generator_reaches,
        "through_an_empty_word",
        ("check_one_slip",),
    ),
    Control(
        condition_properties.test_each_row_of_the_table_and_the_conditions_it_checks,
        "required_held_nowhere",
        ("check_against_the_oracle",),
    ),
    Control(
        result_properties.test_a_read_gives_a_result_whose_reasons_are_the_tables,
        "condition_unchecked",
        ("check_totality",),
    ),
    Control(
        model_properties.test_the_read_agrees_with_the_model_on_faults_of_steps_8_to_10,
        "condition_unchecked",
        ("check_outcome",),
    ),
    Control(
        model_properties.test_the_read_agrees_with_the_model_on_values_and_alternatives,
        "constant_refused_bounds",
        ("check_outcome",),
    ),
    Control(
        model_properties.test_the_read_agrees_with_the_model_on_values_and_alternatives,
        "unknown_member",
        ("check_outcome",),
        stops=without_unknown_members,
    ),
    # The table evaluator's: each stops one choice that no other feature it declares depends on.
    Control(
        evaluate_properties.test_hp17_the_evaluator_agrees_with_the_oracle, "one_point", ("check_agreement",)
    ),
    Control(evaluate_properties.test_hp18_a_read_at_a_knot_gives_its_y_as_stored, "loglog", ("check_knots",)),
    Control(
        evaluate_properties.test_hp19_a_read_lies_between_the_y_of_the_knots_that_bracket_it,
        "loglog",
        ("check_bracketing",),
    ),
    Control(
        evaluate_properties.test_hp19_reads_over_monotone_knots_are_monotone,
        "non_increasing",
        ("check_monotone",),
    ),
    # S4a's: step 7's outcome over alternatives, drawn first among the five; and HP12's draws of them.
    Control(
        alternatives_properties.test_the_outcome_over_alternatives_is_the_texts,
        "no_pick",
        ("check_drawn_outcome", "check_outcome"),
    ),
    Control(
        model_properties.test_the_read_agrees_with_the_model_on_values_and_alternatives,
        "standing",
        ("check_outcome",),
    ),
    # S3a's: HP13's four parts, each its faults drawn first; HP14's kinds, HP15's and HP16's.
    *(
        Control(
            table_form_properties.test_one_table_fault_gives_the_reasons_its_rule_gives,
            never,
            ("check_one_fault",),
            (("part", part),),
        )
        for part, never in (
            ("knots", "y_longer"),
            ("edges", "edge_at_an_end"),
            ("tokens", "scheme_unknown"),
            ("source_range_and_points", "points"),
            # The regions of the planned searches of the S3a review's fix round: the edge at zero held as `-0`
            # and `0`, a fault drawn first (`x_strictly_increasing`, and `zero_and_minus_zero_by_sign_bit`,
            # which dies there, the check reading the fault before its base), and the axis condition held as
            # a value, a way of one fault declared by its chance; and the fault the review's H1 added.
            ("edges", "zero_edge_both_signs"),
            ("tokens", "axis_condition_held_as_a_value"),
            ("source_range_and_points", "x_empty_beside_edges_or_a_source_range"),
        )
    ),
    Control(
        table_form_properties.test_a_member_one_slip_from_a_tables_refuses_and_any_other_is_ignored,
        "far",
        ("check_added",),
    ),
    Control(
        table_form_properties.test_any_other_axis_unit_gives_unit_mismatch_with_the_axis,
        "status_object",
        ("check_other_axis_unit",),
    ),
    Control(
        table_form_properties.test_a_rows_label_is_refused_exactly_on_a_table_over_its_axis,
        "on_another_axis",
        ("check_label",),
    ),
    # S3b-2's: HP20 to HP23, HP21's relation and the monotonicity property, each its way drawn first, and the
    # monotonicity property's worlds stated without origin, by their chance; HP12's table part and HP1, HP2
    # and HP11's table reads, each its kind drawn first.
    Control(
        table_read_properties.test_a_read_at_an_edge_is_refused_and_beside_one_reads_its_own_side,
        "across_an_edge",
        ("check_edge",),
    ),
    Control(
        table_read_properties.test_the_readable_range_holds_its_ends_and_nothing_beyond,
        "outside_a_narrower_source_range",
        ("check_range",),
    ),
    Control(
        table_read_properties.test_a_source_range_no_narrower_than_x_and_a_tolerance_on_the_axis_change_nothing,
        "far_outside",
        ("check_no_wider_and_tolerance",),
    ),
    Control(
        table_read_properties.test_a_tables_block_stands_at_every_read_and_points_are_refused,
        "holding_points",
        ("check_statistics",),
    ),
    Control(
        table_read_properties.test_step_11s_request_checks_give_their_reason_with_the_axis,
        "range_holding_an_edge",
        ("check_request",),
    ),
    Control(
        table_read_properties.test_a_source_range_or_a_tolerance_on_the_axis_never_turns_a_read_met,
        "one_double_outside",
        ("check_monotone",),
    ),
    Control(
        table_read_properties.test_a_source_range_or_a_tolerance_on_the_axis_never_turns_a_read_met,
        "stated_without_origin",
        ("check_monotone",),
    ),
    Control(
        model_properties.test_the_read_agrees_with_the_model_on_tables,
        "table_among_alternatives",
        ("check_agreement",),
    ),
    Control(
        result_properties.test_a_table_read_gives_a_result_whose_reasons_are_the_tables,
        "table_request",
        ("check_totality",),
    ),
    Control(
        result_properties.test_on_a_table_the_status_is_the_worst_reason_and_the_members_are_item_6s,
        "table_statistics",
        ("check_status_law",),
    ),
    Control(
        result_properties.test_without_the_hash_suite_the_label_marks_a_table_read,
        "table_at_an_edge",
        ("check_claims",),
    ),
    # S3c's: HP24 to HP26 and the monotonicity property over an extrapolation, each its way drawn first, and
    # the monotonicity property's worlds stated without origin, by their chance.
    Control(
        extrapolation_properties.test_an_extrapolation_that_applies_adds_the_end_value_and_what_rests_on_it,
        "outside_a_narrower_source_range",
        ("check_applied",),
    ),
    Control(
        extrapolation_properties.test_an_extrapolation_changes_no_read_in_the_range_at_or_across_an_edge_or_under_another_want,
        "at_an_edge_outside",
        ("check_not_applied",),
    ),
    Control(
        extrapolation_properties.test_an_extrapolation_located_elsewhere_is_checked_and_never_applied,
        "an_interval",
        ("check_elsewhere",),
    ),
    Control(
        extrapolation_properties.test_two_extrapolations_naming_one_field_are_refused_wherever_located,
        "each_its_own_field",
        ("check_two",),
    ),
    Control(
        extrapolation_properties.test_an_extrapolation_whose_method_or_law_breaks_its_shape_is_refused,
        "law_empty",
        ("check_refused_shape",),
    ),
    Control(
        extrapolation_properties.test_an_extrapolations_ignored_members_and_white_space_law_are_read_and_a_slip_refused,
        "law_white_space",
        ("check_read_shape",),
    ),
    Control(
        extrapolation_properties.test_an_extrapolation_never_turns_a_read_met,
        "far_outside",
        ("check_monotone",),
    ),
    Control(
        extrapolation_properties.test_an_extrapolation_never_turns_a_read_met,
        "stated_without_origin",
        ("check_monotone",),
    ),
    # S4d's: HP39's two parts, each the others' outcome drawn first among S4a's five and the table's way by
    # its chance; and HP12's part over tables among alternatives, its part drawn first.
    Control(
        table_alternatives_properties.test_a_table_alternative_kept_or_set_aside_by_its_range_is_read_as_the_text_says,
        "no_pick",
        ("check_table_alternative",),
    ),
    Control(
        table_alternatives_properties.test_a_table_alternative_kept_or_set_aside_by_its_range_is_read_as_the_text_says,
        "kept",
        ("check_table_alternative",),
    ),
    Control(
        table_alternatives_properties.test_a_table_alternative_at_an_edge_or_with_no_operating_value_is_read_as_the_text_says,
        "all_set_aside",
        ("check_table_alternative",),
    ),
    Control(
        table_alternatives_properties.test_a_table_alternative_at_an_edge_or_with_no_operating_value_is_read_as_the_text_says,
        "no_operating_value_set_aside",
        ("check_table_alternative",),
    ),
    Control(
        model_properties.test_the_read_agrees_with_the_model_on_tables_among_alternatives,
        "refuses",
        ("check_agreement",),
    ),
    # S7a-1's: HP41's six drawing parts and HP42, each drawing its way first among the two of a stratum (a
    # stratum of one draws none; `every_fault` draws none), a control of one stratum a part.
    Control(
        declaration_properties.test_a_reason_or_a_basis_missing_or_empty_is_refused_by_items_3_and_4,
        "basis",
        ("check_declaration",),
        (("ways", ("acceptance_reason", "basis")),),
    ),
    Control(
        declaration_properties.test_an_acceptance_whose_kind_needs_a_location_and_names_none_is_refused,
        "accepted_difference_unlocated",
        ("check_declaration",),
        (("ways", ("unlocated", "accepted_difference_unlocated")),),
    ),
    Control(
        declaration_properties.test_a_declaration_off_its_shape_is_refused_at_the_member_at_fault,
        "slip",
        ("check_declaration",),
        (("ways", ("unknown", "slip")),),
    ),
    Control(
        declaration_properties.test_a_token_or_a_registered_name_off_its_members_list_is_refused,
        "misspelt_name",
        ("check_declaration",),
        (("ways", ("slip_of_token", "misspelt_name")),),
    ),
    Control(
        declaration_properties.test_a_name_given_twice_a_field_not_read_and_an_unreviewed_label_are_refused,
        "trainable_unlisted",
        ("check_declaration",),
        (("ways", ("twice", "trainable_unlisted")),),
    ),
    Control(
        declaration_properties.test_a_fault_carries_the_first_case_of_the_rules_that_name_it_once,
        "not_json",
        ("check_declaration",),
        (("ways", ("not_json", "not_object")),),
    ),
    Control(
        declaration_properties.test_what_a_build_cannot_check_is_refused_after_items_7_and_8_and_fails_closed_where_claimed,
        "engine",
        ("check_unbuilt",),
        (("ways", ("region_conditions", "engine")),),
    ),
]


def skipped(*_: object) -> None:
    pass


def marks_of(control: Control) -> list[pytest.Mark]:
    """The property's marks, and those of the parameter set it runs with, as pytest gives them to its item."""
    marks: list[pytest.Mark] = getattr(control.test, "pytestmark", [])
    found = [mark for mark in marks if mark.name != "parametrize"]
    for mark in marks:
        if mark.name == "parametrize":
            names = [name.strip() for name in str(mark.args[0]).split(",")]
            for parameter_set in mark.args[1]:
                if tuple(zip(names, parameter_set.values, strict=True)) == control.parameters:
                    found += [decorator.mark for decorator in parameter_set.marks]
    return found


def marker_kwargs(control: Control, name: str) -> dict[str, float]:
    return {
        key: value for mark in marks_of(control) if mark.name == name for key, value in mark.kwargs.items()
    }


def marker_args(control: Control, name: str) -> tuple[str, ...]:
    return tuple(arg for mark in marks_of(control) if mark.name == name for arg in mark.args)


def control_id(control: Control) -> str:
    parameters = "".join(f"[{value}]" for _, value in control.parameters)
    return f"{control.test.__name__}{parameters}-{control.never}"


def run_without(control: Control, monkeypatch: pytest.MonkeyPatch, examples: int) -> audits.Counts:
    """The counts of a derandomised run of `examples` examples of the property, its generator stopped from
    producing the control's feature and the checks it skips skipped."""
    module = sys.modules[control.test.__module__]
    record: Callable[..., None] = module.feature

    def feature(name: str, shown: bool = True) -> None:
        if shown and name == control.never:
            reject()
        record(name, shown)

    # The property's own strategy, its example rejected wherever it would show the feature: a generator that
    # stops producing it, drawing the rest as before.
    if control.stops is None:
        monkeypatch.setattr(module, "feature", feature)
    else:
        control.stops(monkeypatch)
    for check in control.skipped:
        monkeypatch.setattr(module, check, skipped)
    # Derandomised, so that the run is the same each time. Hypothesis keeps a test's settings on it from when
    # `@given` wraps it; this sets them for this test alone.
    monkeypatch.setattr(
        control.test,
        "_hypothesis_internal_use_settings",
        settings(
            vars(control.test)["_hypothesis_internal_use_settings"],
            max_examples=examples,
            derandomize=True,
            database=None,
            suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
        ),
    )
    with audits.counting() as counts:
        control.test(**dict(control.parameters))
    return counts


@pytest.mark.parametrize("control", CONTROLS, ids=[control_id(control) for control in CONTROLS])
def test_a_generator_that_stops_producing_a_feature_fails_the_audit_at_ci(
    control: Control, monkeypatch: pytest.MonkeyPatch
) -> None:
    chances = marker_kwargs(control, "chances")
    drawn = marker_args(control, "drawn")
    assert control.never in chances or control.never in drawn
    counts = run_without(control, monkeypatch, EXAMPLES["ci"])
    problems = audits.feature_shortfalls(
        counts,
        marker_kwargs(control, "features"),
        drawn,
        chances=chances,
        deep_chances=marker_kwargs(control, "deep_chances"),
        **audits.RULES["ci"],
    )
    chance = chances[control.never] if control.never in chances else 1 / len(drawn)
    floor = audits.draw_floor(EXAMPLES["ci"], chance)
    assert floor >= audits.LEAST_DRAWS
    assert problems == [
        f"feature {control.never!r} in 0 of {EXAMPLES['ci']} examples, below its floor of {floor}"
    ]
