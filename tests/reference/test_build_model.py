# SPDX-License-Identifier: Apache-2.0
"""The build's model held directly, on the rules no build-check case file pins (`direct.py`): that one fault
is one member at fault, that a pick is located by its record, that a suite the build claims gives no verdict
whatever else the declaration holds, and that the model orders the cases of a fault two rules name as the
specification does. The seeded faults of the model are run against these checks too
(`test_seeded_faults.py`), so that a fault only these tell apart is a kill."""

import json

import pytest

from tests.reference import build_model, direct
from tests.reference.read_model import NoVerdict


@pytest.mark.parametrize("check", direct.CHECKS, ids=lambda check: check.what)
def test_the_model_gives_each_declaration_the_answer_the_text_and_the_rulings_give(
    check: direct.Direct,
) -> None:
    assert direct.judged(check) is None


@pytest.mark.parametrize("what", direct.SUITE_MEMBERS)
def test_a_claimed_suite_gives_no_verdict_beside_another_fault_and_only_its_claim_does(what: str) -> None:
    suite, unclaimed, model, members = direct.SUITE_MEMBERS[what]
    text = json.dumps(direct.declaration({**model, **direct.OTHER_FAULT}, **members)).encode()
    claimed = build_model.check_build(text, suite)
    assert isinstance(claimed, NoVerdict), f"{what}: the suite claimed gives {claimed}"
    bare = build_model.check_build(text, direct.BUILD)
    assert isinstance(bare, build_model.Refused), f"{what}: the suite not claimed gives {bare}"
    assert {(one.item, one.pointer) for one in bare.refusals} == unclaimed | {direct.OTHER_REFUSAL}


def test_the_model_orders_the_cases_of_a_fault_two_rules_name_as_the_text_does() -> None:
    assert direct.order_problems() == []


def test_the_order_is_read_from_the_paragraph_that_gives_it() -> None:
    assert direct.specified_order() == (
        "BC-004", "BC-005", "BC-040", "BC-044", "BC-043", "BC-037", "BC-050", "BC-051", "BC-048",
    )  # fmt: skip


def test_a_waiver_label_both_rules_name_is_one_refusal_not_two() -> None:
    held = json.dumps(direct.labelled(direct.NEWTONIAN, direct.MAGNETIC)).encode()
    found = build_model.check_build(held, direct.BUILD)
    assert isinstance(found, build_model.Refused)
    assert len(found.refusals) == 1


@pytest.mark.parametrize(
    ("check", "problem"),
    [
        (
            direct.Direct("a", direct.declaration(), direct.BUILD, direct.refused(("BC-048", ""))),
            "no verdict",
        ),
        (direct.Direct("b", {}, direct.BUILD, None), "refused"),
        (direct.Direct("c", {}, direct.BUILD, direct.refused(("BC-004", ""))), "not [('BC-004', '')]"),
        (
            direct.Direct("d", {}, direct.BUILD, direct.refused(("BC-048", "/models"))),
            "not [('BC-048', '/models')]",
        ),
    ],
)
def test_a_direct_check_the_model_does_not_meet_is_found(check: direct.Direct, problem: str) -> None:
    """Control: each kind of disagreement (no verdict for a refusal, a refusal for no verdict, another case,
    another pointer) is reported."""
    found = direct.judged(check)
    assert found is not None
    assert problem in found


@pytest.mark.parametrize("place", range(len(build_model.ORDER) - 1))
def test_a_model_that_swaps_two_neighbouring_cases_of_its_order_is_found(
    place: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control: each reordering of two neighbouring cases is a disagreement with the text, as the five
    reorderings the review wrote are."""
    swapped = list(build_model.ORDER)
    swapped[place], swapped[place + 1] = swapped[place + 1], swapped[place]
    monkeypatch.setattr(build_model, "ORDER", tuple(swapped))
    assert direct.order_problems() != []
