# SPDX-License-Identifier: Apache-2.0
"""Direct checks of the build's model: declarations written here, each with the answer the specification gives
it, for the rules no build-check case file pins. They are the model's own tests, not evidence on the build: a
case file is the shared evidence, and a direct check holds the model to the maintainer's rulings and to the
text where no file does (`test_build_model.py`).

The seeded faults of the model (`mutants.py`) are run against these as well as against the case files, so
that a fault only a direct check tells apart is a kill, and a rule neither pins is a listed survivor."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from tests.reference import build_model
from tests.reference.read_model import NoVerdict
from tests.reference.strict_json import JsonObject, JsonValue

SPECIFICATION: Final = Path(__file__).resolve().parents[2] / "docs" / "specification"
RECORD: Final[JsonObject] = {
    "id": "conformance/water_fixture",
    "version": "1.0.0",
    "content_hash": "sha256:c21a2c7f46e66bcfb5e74f18d2a08644468d5a92bafb4fa57a03651facf96e2d",
}
VISCOSITY: Final = "fluid.dynamic_viscosity"
NEWTONIAN: Final = "materica.fluid.newtonian.v1"  # a label registered for the viscosity
MAGNETIC: Final = "materica.magnetic.linear.v1"  # a label registered for another field
REASON: Final = "the consumer's own reason, a string of at least one character"
CONFIGURATION_HASH: Final = "sha256:46df0c2b3082576d2848959f99adb425293d93f6ebcc0b73552c124b3c2106d3"
BUILD: Final = frozenset({"plain_read", "build_checks"})
SCENE: Final = BUILD | {"scene_documents"}
SAMPLING: Final = BUILD | {"sampling"}
USD: Final = BUILD | {"usd_read"}
EVERY_SUITE: Final = BUILD | {"hash", "fits_and_reference_data", "scene_documents", "usd_read", "sampling"}
MODEL: Final = "/models/0"
OTHER_FAULT: Final[JsonObject] = {"consumer_parameters": [1.0]}  # a number where the table asks for strings
OTHER_REFUSAL: Final = ("BC-048", f"{MODEL}/consumer_parameters/0")
Refusals = frozenset[tuple[str, str]]


def refused(*refusals: tuple[str, str]) -> Refusals:
    return frozenset(refusals)


def requirement(**members: JsonValue) -> JsonObject:
    return {
        "field": VISCOSITY,
        "want": "value",
        "conditions": {"temperature": {"tolerance": {"value": 1.0, "unit": "K"}, "reason": REASON}},
        **members,
    }


def entry(**members: JsonValue) -> JsonObject:
    """A model entry that passes its own check, with `members` replacing or adding to it."""
    return {
        "model": {"name": "drag", "version": "1.0.0"},
        "model_configuration_hash": CONFIGURATION_HASH,
        "checked_over": {"records": [RECORD]},
        "target": {},
        "reads": [VISCOSITY],
        "consumer_parameters": ["drag.viscosity"],
        "requirements": [requirement()],
        "families": {},
        "combinations": [],
        "chains": [],
        **members,
    }


def declaration(model: JsonObject | None = None, **members: JsonValue) -> JsonObject:
    """A declaration that passes its own check, with `members` replacing or adding to it."""
    return {
        "consumer": {"name": "conformance_consumer", "version": "1.0.0"},
        "operating_conditions": {"temperature": {"value": 310.15, "unit": "K"}},
        "models": [model or entry()],
        **members,
    }


def acceptance(kind: str, **members: JsonValue) -> JsonObject:
    return {"acceptance": kind, "record": RECORD, "field": VISCOSITY, "reason": REASON, **members}


def waiver(**members: JsonValue) -> JsonObject:
    return acceptance("waiver", code="condition_unstated", condition="shear_rate", **members)


def pick(**members: JsonValue) -> JsonObject:
    return acceptance("pick", index=0.0, **members)


def unlocated(kind: JsonObject, **location: JsonValue) -> JsonObject:
    """`kind` without its `record`, at the `location`."""
    return {name: held for name, held in kind.items() if name != "record"} | location


def unlocated_pick(**location: JsonValue) -> JsonObject:
    return unlocated(pick(), **location)


@dataclass(frozen=True)
class Direct:
    what: str
    declaration: JsonObject
    claims: frozenset[str]
    refusals: Refusals | None  # None: no verdict


def beside_another_fault(
    what: str, suite: frozenset[str], unclaimed: Refusals, model: JsonObject, **members: JsonValue
) -> list[Direct]:
    """A declaration holding a member the suite checks and `OTHER_FAULT`: its refusals where the build does
    not claim the suite (the control: the claim is what changes the answer), no verdict where it does."""
    held = declaration({**model, **OTHER_FAULT}, **members)
    return [
        Direct(
            f"{what}, its suite not claimed, beside another fault", held, BUILD, unclaimed | {OTHER_REFUSAL}
        ),
        Direct(f"{what}, its suite claimed, beside another fault", held, suite, None),
    ]


def labelled(requirement_label: str, waiver_label: str) -> JsonObject:
    return declaration(
        entry(
            requirements=[requirement(label=requirement_label, review="reviewed")],
            acceptances=[waiver(label=waiver_label)],
        )
    )


IMPLIED: Final[JsonObject] = acceptance(
    "implied_condition",
    fact="tissue_state",
    token="phantom",
    implies={"temperature": {"value": 300.0, "unit": "K"}},
)
DISTRIBUTION: Final[JsonObject] = acceptance(
    "distribution",
    distribution="normal",
    space="identity",
    distribution_parameters={"mean": 1.0, "sd": 0.1},
    basis="the consumer's own basis",
)
ENGINE: Final[JsonObject] = {
    "crosswalk": {"id": "materica/rigid_body", "version": "1.0.0", "sha256": "0" * 64},
    "values": {},
}
SAMPLING_BLOCK: Final[JsonObject] = {"min_acceptance": 0.5, "reason": REASON, "independence": []}
ACCEPTANCE: Final = f"{MODEL}/acceptances/0"
# A member each suite checks: the suite, its refusals where the build does not claim it, the model entry that
# holds it and the declaration's members beside it.
SUITE_MEMBERS: Final[dict[str, tuple[frozenset[str], Refusals, JsonObject, dict[str, JsonValue]]]] = {
    "a model checked over a domain": (
        SCENE,
        refused(("BC-051", f"{MODEL}/checked_over/domain")),
        entry(checked_over={"domain": "lumen"}),
        {},
    ),
    "a distribution acceptance": (
        SAMPLING,
        refused(("BC-051", ACCEPTANCE)),
        entry(acceptances=[DISTRIBUTION]),
        {},
    ),
    "a model with an engine": (USD, refused(), entry(engine=ENGINE), {}),
    "a sampling block": (SAMPLING, refused(("BC-051", "/sampling")), entry(), {"sampling": SAMPLING_BLOCK}),
}


# A member another JSON type holds and item 12 names: one fault two rules name, so the shape rule's refusal
# and item 12's are one, with item 12's case where the suite is not claimed (the order puts it first) and no
# verdict where it is (maintainer, 2026-10-24).
DOMAIN: Final = f"{MODEL}/checked_over/domain"
PATH: Final = f"{MODEL}/checked_over/path"
MISTYPED_GATING_MEMBERS: Final[tuple[tuple[str, frozenset[str], JsonObject, str], ...]] = (
    (
        "a model checked over a domain that is a number",
        SCENE,
        declaration(entry(checked_over={"domain": 5.0})),
        DOMAIN,
    ),
    (
        "a model checked over a domain that is an object",
        SCENE,
        declaration(entry(checked_over={"domain": {}})),
        DOMAIN,
    ),
    (
        "a model checked over a path that is a number",
        SCENE,
        declaration(entry(checked_over={"path": 5.0})),
        PATH,
    ),
    ("a sampling that is a number", SAMPLING, declaration(sampling=5.0), "/sampling"),
)


CHECKS: Final[tuple[Direct, ...]] = (
    Direct("the declaration the checks start from", declaration(), BUILD, None),
    # One fault is one member at fault (maintainer, 2026-10-24): a waiver's label that item 4 and the token
    # rule both refuse is one refusal, BC-050's; the token rule's alone where item 4 does not refuse it.
    Direct(
        "a waiver's label registered for another field, not named by its requirement",
        labelled(NEWTONIAN, MAGNETIC),
        BUILD,
        refused(("BC-050", f"{ACCEPTANCE}/label")),
    ),
    Direct(
        "a waiver's label registered for another field, its requirement naming it",
        labelled(MAGNETIC, MAGNETIC),
        BUILD,
        refused(("BC-048", f"{MODEL}/requirements/0/label"), ("BC-048", f"{ACCEPTANCE}/label")),
    ),
    Direct(
        "a waiver's label registered for its field, its requirement naming it",
        labelled(NEWTONIAN, NEWTONIAN),
        BUILD,
        None,
    ),
    Direct(
        "a status object as a target fact",
        declaration(entry(target={"species": {"status": "unstated"}})),
        BUILD,
        refused(("BC-048", f"{MODEL}/target/species")),
    ),
    Direct(
        "a status object as an implied condition's value",
        declaration(entry(acceptances=[{**IMPLIED, "implies": {"temperature": {"status": "unstated"}}}])),
        BUILD,
        refused(("BC-048", f"{ACCEPTANCE}/implies/temperature")),
    ),
    Direct("an implied condition holding a value", declaration(entry(acceptances=[IMPLIED])), BUILD, None),
    # A pick is located by its record, whatever the build claims (maintainer, 2026-10-24).
    *(
        Direct(
            f"a pick naming a region and no record, claiming {label}",
            declaration(entry(acceptances=[unlocated_pick(region="lumen")])),
            claims,
            refused(("BC-037", ACCEPTANCE)),
        )
        for label, claims in (("no suite", BUILD), ("the scene suite", SCENE), ("every suite", EVERY_SUITE))
    ),
    Direct(
        "a pick naming an interval and no record, claiming the scene suite",
        declaration(entry(acceptances=[unlocated_pick(interval={"path": "a", "index": 0.0})])),
        SCENE,
        refused(("BC-037", ACCEPTANCE)),
    ),
    Direct("a pick naming a record", declaration(entry(acceptances=[pick()])), BUILD, None),
    Direct(
        "a pick naming a record and a region, the scene suite not claimed",
        declaration(entry(acceptances=[pick(region="lumen")])),
        BUILD,
        refused(("BC-051", ACCEPTANCE)),
    ),
    Direct(
        "a pick naming a record and a region, the scene suite claimed",
        declaration(entry(acceptances=[pick(region="lumen")])),
        SCENE,
        None,
    ),
    # An acceptance of any kind at a region is item 12's, as a pick's is (the scene suite not claimed, BC-051;
    # claimed, no verdict).
    *(
        Direct(f"{what}, {label}", declaration(entry(acceptances=[held])), claims, refusals)
        for what, held in (
            ("a waiver at a region and no record", unlocated(waiver(), region="lumen")),
            ("a waiver at a record and a region", waiver(region="lumen")),
        )
        for label, claims, refusals in (
            ("the scene suite not claimed", BUILD, refused(("BC-051", ACCEPTANCE))),
            ("the scene suite claimed", SCENE, None),
        )
    ),
    # A member two rules name is one fault; a member missing is the object's, apart from the object's own and
    # from another missing member's.
    *(
        check
        for what, suite, held, pointer in MISTYPED_GATING_MEMBERS
        for check in (
            Direct(f"{what}, its suite not claimed", held, BUILD, refused(("BC-051", pointer))),
            Direct(f"{what}, its suite claimed", held, suite, None),
        )
    ),
    Direct(
        "a waiver lacking its reason and its code",
        declaration(
            entry(
                acceptances=[
                    {
                        name: held
                        for name, held in waiver().items()
                        if name not in ("reason", "code", "condition")
                    }
                ]
            )
        ),
        BUILD,
        refused(("BC-005", ACCEPTANCE), ("BC-048", ACCEPTANCE)),
    ),
    # A status object is an object whose only members are `status` and, optionally, `reason`
    # (provenance.md section 6.1): one refusal at the member that holds it. Anything else is judged as the
    # member it is.
    *(
        Direct(
            what, declaration(held), BUILD, refused(*(("BC-048", f"{pointer}{inside}") for inside in found))
        )
        for what, held, pointer, found in (
            (
                "a status object with a reason as a target fact",
                entry(target={"species": {"status": "unstated", "reason": REASON}}),
                f"{MODEL}/target/species",
                ("",),
            ),
            (
                "a status object beside another member as a target fact",
                entry(target={"species": {"status": "unstated", "unit": "K"}}),
                f"{MODEL}/target/species",
                ("", "/status", "/unit"),
            ),
            (
                "a reason alone as a target fact",
                entry(target={"species": {"reason": REASON}}),
                f"{MODEL}/target/species",
                ("", "/reason"),
            ),
            (
                "an empty object as a target fact",
                entry(target={"species": {}}),
                f"{MODEL}/target/species",
                ("",),
            ),
            (
                "a status object with a reason as an implied condition's value",
                entry(
                    acceptances=[
                        {**IMPLIED, "implies": {"temperature": {"status": "unstated", "reason": REASON}}}
                    ]
                ),
                f"{ACCEPTANCE}/implies/temperature",
                ("",),
            ),
            (
                "a status object beside another member as an implied condition's value",
                entry(
                    acceptances=[{**IMPLIED, "implies": {"temperature": {"status": "unstated", "unit": "K"}}}]
                ),
                f"{ACCEPTANCE}/implies/temperature",
                ("", "/status"),
            ),
        )
    ),
    # A suite the build claims checks its members further: no verdict, never the refusals of the rest.
    *(
        check
        for what, (suite, unclaimed, model, members) in SUITE_MEMBERS.items()
        for check in beside_another_fault(what, suite, unclaimed, model, **members)
    ),
)


def judged(check: Direct) -> str | None:
    """What is wrong with the model's answer to `check`, or None."""
    given = build_model.check_build(json.dumps(check.declaration).encode(), check.claims)
    if isinstance(given, NoVerdict):
        return (
            None
            if check.refusals is None
            else f"{check.what}: no verdict ({given.why}), not {sorted(check.refusals)}"
        )
    found = frozenset((one.item, one.pointer) for one in given.refusals)
    if check.refusals is None:
        return f"{check.what}: refused {sorted(found)}, not no verdict"
    return (
        None
        if found == check.refusals
        else f"{check.what}: refused {sorted(found)}, not {sorted(check.refusals)}"
    )


def specified_order() -> tuple[str, ...]:
    """The cases in the order the paragraph of declarations.md that gives the refusal lists them: the first
    that names a fault is the fault's case."""
    text = " ".join((SPECIFICATION / "declarations.md").read_text(encoding="utf-8").split())
    start = text.index("A fault more than one rule names carries the case of the first of")
    return tuple(re.findall(r"\[(BC-\d{3})\]", text[start : text.index("Two faults with one case", start)]))


def order_problems() -> list[str]:
    """The model's order is the specification's, and a fault two rules name carries the earlier's case."""
    order = specified_order()
    problems = [] if build_model.ORDER == order else [f"the order is {build_model.ORDER}, the text's {order}"]
    for place, earlier in enumerate(order):
        for later in order[place + 1 :]:
            fault = build_model.Fault("/x", (later, earlier))
            if build_model.refusals_of([fault]) != frozenset({build_model.Refusal(earlier, "/x")}):
                problems.append(f"a fault {later} and {earlier} name does not carry {earlier}'s case")
    return problems


def problems() -> list[str]:
    """Every direct check the model fails."""
    found = [problem for check in CHECKS if (problem := judged(check)) is not None]
    return [*found, *order_problems()]
