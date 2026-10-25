# SPDX-License-Identifier: Apache-2.0
"""HP41's and HP42's mutant table (`test_declaration_mutants.py`) read whole, in a module apart from its
searches, so that it runs on every Python (`--property-controls` in `tests/conftest.py`)."""

from materica.core import declarations
from tests.property import declaration_strategies as strategies
from tests.property.test_declaration_mutants import KILLERS, MUTANTS, stratum

# What each part's examples draw as their way, which a mutant's `dies_at` names, in the part's strata.
DRAWN = {
    **{f"HP41 {part}": tuple(ways) for part, ways in strategies.PARTS.items()},
    "HP41 every_fault": ("every_fault",),
    "HP42": strategies.HP42_WAYS,
}


def test_each_part_draws_its_ways_in_strata_of_at_most_two() -> None:
    """Every way of a part in one stratum, and none of more than two ways (the floors at the variance
    measured)."""
    for killer, (_, strata, _) in KILLERS.items():
        ways = [way for ways in strata for way in ways]
        assert sorted(ways) == sorted(DRAWN[killer]), killer
        assert all(1 <= len(ways) <= 2 for ways in strata), killer


def test_each_mutant_names_a_killer_the_ways_that_show_it_its_assertion_and_its_function() -> None:
    assert len({mutant.name for mutant in MUTANTS}) == len(MUTANTS)
    assert set(DRAWN) == set(KILLERS)
    assert all(mutant.killer in KILLERS for mutant in MUTANTS)
    for mutant in MUTANTS:
        within = [ways for ways in KILLERS[mutant.killer][1] if set(mutant.dies_at) <= set(ways)]
        assert mutant.dies_at, mutant.name
        assert len(within) == 1, f"{mutant.name}: the ways it names lie in no one stratum"
    assert all(mutant.says.strip() and mutant.fault.strip() for mutant in MUTANTS)
    assert all(hasattr(declarations, mutant.function) for mutant in MUTANTS)


def test_every_stratum_kills_a_mutant() -> None:
    """Each stratum of HP41's seven parts and of HP42, a test of its own, kills one at least: none is a check
    no fault fails."""
    strata = {(killer, ways) for killer, (_, all_strata, _) in KILLERS.items() for ways in all_strata}
    assert {(mutant.killer, stratum(mutant)) for mutant in MUTANTS} == strata


# The S7 design's mutants of HP41 and HP42 (its section 6.4), by the function it names, each by the row that
# stands for it here.
DESIGN: dict[str, dict[str, str]] = {
    "_reasons": {
        "an empty string taken": "empty_reason_taken",
        "an accept list's reason not checked": "accept_reason_unchecked",
        "an acceptance's reason checked only on waivers": "reason_checked_on_waivers_only",
        "`basis` checked on nominals but not extrapolations": "basis_checked_on_nominals_only",
        "`basis` required of a waiver": "basis_required_of_a_waiver",
    },
    "_locations": {
        "`implied_condition` not checked": "implied_condition_location_unchecked",
        "an `accepted_difference` without location refused": "accepted_difference_location_required",
    },
    "_shape": {
        "an unknown member ignored": "unknown_member_ignored",
        "a plural slip missed": "plural_slip_missed",
        "a required member's absence taken (`target`)": "target_absence_taken",
        "an empty `checked_over.records` taken": "empty_records_taken",
    },
    "_tokens": {
        "`review` unchecked": "review_unchecked",
        "a slip of a token taken": "token_slip_taken",
        "tokens compared without case": "tokens_compared_without_case",
        "`want` left to the read": "want_left_to_the_read",
    },
    "_names": {
        "two models of one name taken": "two_models_of_one_name_taken",
        "a requirement for a field not read taken": "requirement_for_a_field_not_read_taken",
        "two requirements for one field taken": "two_requirements_for_one_field_taken",
        "a field twice in `reads` taken": "field_twice_in_reads_taken",
        "a `trainable` entry for a field not read taken": "trainable_for_a_field_not_read_taken",
        "one at an unlisted record taken": "trainable_at_an_unlisted_record_taken",
    },
    "_labels": {
        "a label-resting waiver taken without the requirement's `review`": (
            "label_waiver_taken_without_review"
        ),
    },
    "_precedence": {
        "BC-048 beside BC-005 for a missing reason": "bc048_beside_bc005",
        "a missing member's pointer at the member, not its parent": "missing_member_at_the_member",
        "two missing members of one object given twice": "two_missing_members_given_twice",
        'invalid JSON\'s pointer not `""`': "not_json_pointer_not_empty",
    },
    "the search": {
        "stops at the first fault": "first_fault_only",
        "a pointer's model index off by one": "model_index_off_by_one",
    },
    "_suites": {
        "`region_conditions` taken": "region_conditions_taken",
        "`checked_over.path` taken": "path_taken",
        "`engine` taken": "engine_taken",
        "a `distribution` acceptance taken": "distribution_taken",
        "a requirement's `represents` taken": "represents_taken",
        "BC-051 for an engine model over records in place of BC-040": "engine_over_records_left_to_item_12",
        "BC-051 beside BC-044 for `represents` with no `sampling`": "item_12_beside_item_8",
    },
}


def test_every_mutant_the_design_names_has_its_row() -> None:
    names = {mutant.name for mutant in MUTANTS}
    rows = [row for function in DESIGN.values() for row in function.values()]
    assert len(rows) == 35
    assert set(rows) <= names, sorted(set(rows) - names)
