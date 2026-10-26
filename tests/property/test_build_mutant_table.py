# SPDX-License-Identifier: Apache-2.0
"""HP43's to HP46's mutant table (`test_build_mutants.py`) read whole, in a module apart from its searches, so
that it runs on every Python (`--property-controls` in `tests/conftest.py`)."""

from materica.core import acceptance, build, report
from tests.property import build_strategies as strategies
from tests.property.test_build_mutants import KILLERS, MUTANTS

# What each part's examples draw as their way, which a mutant's `dies_at` names.
DRAWN = {
    **{f"HP43 {part}": ways for part, ways in strategies.HP43_PARTS.items()},
    "HP43 indexes": ("indexes",),
    **{f"HP44 {part}": ways for part, ways in strategies.HP44_PARTS.items()},
    **{f"HP45 {part}": ways for part, ways in strategies.HP45_PARTS.items()},
    "HP46": ("permutation",),
}
# Where each fault is injected: the modules a mutant's `function` names a member of.
MODULES = (acceptance, build, report.BuildReport)
OUTSIDE_THE_MODULES = {"VOCABULARY.reasons", "BuildReport.refused"}


def test_each_mutant_names_a_killer_the_ways_that_show_it_its_assertion_and_its_function() -> None:
    assert len({mutant.name for mutant in MUTANTS}) == len(MUTANTS)
    assert set(DRAWN) == set(KILLERS)
    assert all(mutant.killer in KILLERS for mutant in MUTANTS)
    assert all(mutant.dies_at and set(mutant.dies_at) <= set(DRAWN[mutant.killer]) for mutant in MUTANTS)
    # Each mutant's ways lie in one stratum of its killer's, whose test's draws search it.
    assert all(
        any(set(mutant.dies_at) <= set(ways) for ways in KILLERS[mutant.killer][1]) for mutant in MUTANTS
    )
    assert all(
        {way for ways in KILLERS[killer][1] for way in ways} == set(DRAWN[killer]) for killer in KILLERS
    )
    assert all(mutant.says.strip() and mutant.fault.strip() for mutant in MUTANTS)
    assert all(
        mutant.function in OUTSIDE_THE_MODULES or any(hasattr(module, mutant.function) for module in MODULES)
        for mutant in MUTANTS
    )


def test_every_part_kills_a_mutant() -> None:
    """HP43's four parts, HP44's two, HP45's three and HP46 each kill one at least: none is a check no fault
    fails."""
    assert {mutant.killer for mutant in MUTANTS} == set(KILLERS)


# The S7 design's mutants of HP43 to HP46 (its section 6.5), by the function it names, each by the row that
# stands for it here.
DESIGN: dict[str, dict[str, str]] = {
    "_covers": {
        "a waiver covering a `not_met` reason": "waiver_covers_not_met",
        "a waiver ignoring its `condition`": "waiver_ignores_its_condition",
        "a nominal covering `want_mismatch` with no `assumption`, or step 0's": (
            "nominal_covers_without_its_assumption"
        ),
        "an extrapolation covering `outside_range` with no `assumption`": (
            "extrapolation_covers_without_its_assumption"
        ),
        "`at_edge` covered by an extrapolation": "extrapolation_covers_at_an_edge",
        "`label_mismatch` or `no_pick` covered by a waiver naming it": "waiver_covers_label_mismatch",
        "a waiver covering no reason that carries an `alternative` (R07)": (
            "waiver_covers_no_reason_of_an_alternative"
        ),
    },
    "_located_at": {
        "by `id` alone (R06)": "located_by_id_alone",
        "a region taken at a record": "region_taken_at_a_record",
    },
    "judge": {
        "a waiver ignoring its `field`": "waiver_ignores_its_field",
        "`accepted_by` without the applied": "accepted_by_without_the_applied",
        "`accepted_by` with an acceptance that covered nothing": "accepted_by_with_what_covered_nothing",
        "`not_accepted` holding a covered reason": "not_accepted_holds_covered_reasons",
        "an implied condition that filled nothing counted applied": "unfilled_implied_condition_applied",
        "an extrapolation at an `at_edge` read counted applied": "extrapolation_at_an_edge_applied",
        "a model's reason covered by another model's acceptance (R02)": "judged_by_every_models_acceptances",
    },
    "unused": {
        "an applied acceptance listed": "unused_lists_the_applied",
        "each acceptance named after the first model (R01)": "unused_named_after_the_first_model",
        "one set of used acceptances shared by every model (R03)": "unused_shared_by_every_model",
    },
    "_request": {
        "an acceptance at another record given": "acceptance_at_another_record_given",
        "the requirement's `label` or `review` given (so `request_incomplete`)": (
            "requirement_label_and_review_given"
        ),
        "an operating condition the requirement does not name dropped (a table's axis)": (
            "unnamed_operating_condition_dropped"
        ),
        "`want` defaulted": "want_defaulted",
    },
    "check_build": {
        "results for every record in the store": "every_record_in_the_store_read",
        "a field with no requirement read": "field_with_no_requirement_read",
        "the status lowered when accepted": "status_lowered_when_accepted",
        "`not_reviewed` making the status `unknown` over a read's `not_met` (R05)": (
            "not_reviewed_status_unknown"
        ),
    },
    "_stored": {
        "read from the result's labels only (hidden behind a `not_met`)": "label_from_the_result_only",
        "the section's in place of the field's": "label_of_the_section",
    },
    "_build_reasons": {
        "`not_checked` with a `reason` taken as reviewed": "not_checked_with_a_reason_taken_as_reviewed",
        "`not_reviewed` as `not_met`": "not_reviewed_read_as_not_met",
        "added to a result with no provenance (R04)": "not_reviewed_given_without_provenance",
        "`label_mismatch` on an absent record": "label_mismatch_on_no_stored_value",
    },
    "HP46": {
        "`refused` read from the first model only": "refused_read_from_the_first_model_only",
        "acceptances matched by position after a permutation": "acceptances_matched_by_position",
        "results de-duplicated by field alone": "results_deduplicated_by_field",
    },
}
# The design's mutants of label trust, which waits until after 0.1.0.dev4 (maintainer, 2026-10-21): no row
# stands for them, and none is drawn.
WAITING = {
    "_trusted": (
        "an inferred basis trusted",
        "a stated basis not trusted",
        "`label_basis` read from the read result",
    ),
    "_label_rests": ("review not checked", "label presence not checked"),
}

# The faults the reviews of S7a-2a, S7a-2b and S7a-2m showed no test of theirs catching, each by the row that
# stands for it here, or why none does.
REVIEWS: dict[str, str] = {
    "S7a-2a: the acceptances given cut to the first": "only_the_first_acceptance_given",
    "S7a-2a: the build's claims dropped from the read": "claims_dropped_from_the_read",
    "S7a-2a: the build's claims dropped from `_stored`": "stored_under_the_default_claims",
    "S7a-2a: an implied condition applied only where it fills every condition": (
        "implied_applied_where_every_condition_filled"
    ),
    "S7a-2a: an implied range not recognised": "implied_range_not_recognised",
    "S7a-2a: an implied token not recognised": "implied_token_not_recognised",
    "S7a-2a: under `want_mismatch` over two alternatives, resting on the first": (
        "rests_on_the_first_alternative_under_want_mismatch"
    ),
    "S7a-2a: an acceptance for another field of the section given": (
        "acceptance_of_another_field_of_the_section_given"
    ),
    "S7a-2b: an implied value compared by equality, so that -0 is 0": "implied_value_compared_by_equality",
    "S7a-2m: located ignoring the version": "located_ignoring_the_version",
    "S7a-2m: located ignoring the id": "located_ignoring_the_id",
    "S7a-2m: a refusal at steps 2 to 5 resting on the field": "refusal_at_steps_2_to_5_rests_on_the_field",
    "S7a-2m: an extrapolation counted applied under a nominal's assumption": (
        "extrapolation_applied_under_any_assumption"
    ),
    "S7a-2m: a labelled waiver of another code or condition left undecided": (
        "label_trust_raised_where_decided"
    ),
    # The review of this piece: rows of section 4.2 and an arm of section 2 item 8 that no draw reached. A
    # pick is drawn for `judge` alone: a build raises on one before any read, so the row's test over whole
    # builds waits for S7c.
    "S7a-2p: a pick covering nothing": "pick_covers_nothing",
    "S7a-2p: an extrapolation not covering `range_unstated`": "extrapolation_leaves_range_unstated",
    "S7a-2p: an extrapolation not covering `outside_coverage`": "extrapolation_leaves_outside_coverage",
    "S7a-2p: `label_mismatch` left out of a result whose read is `met`": (
        "label_mismatch_left_out_of_a_read_met"
    ),
}


def test_every_mutant_the_design_names_has_its_row() -> None:
    names = {mutant.name for mutant in MUTANTS}
    rows = [row for function in DESIGN.values() for row in function.values()]
    assert len(rows) == 36
    assert len(set(rows)) == len(rows)
    assert set(rows) <= names, sorted(set(rows) - names)
    assert sum(len(faults) for faults in WAITING.values()) == 5


def test_every_survivor_the_reviews_left_has_its_row() -> None:
    names = {mutant.name for mutant in MUTANTS}
    assert set(REVIEWS.values()) <= names, sorted(set(REVIEWS.values()) - names)
