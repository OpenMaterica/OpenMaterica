# Declarations

Schema 0.1.0, draft. Conventions, suites and case numbers: `README.md`. Rationale: AD 3.5, 4.2, 4.11, 5.5
and 9.6.

A record holds facts. A consumer declares its choices. The build checks the declarations against the records,
by the read of `read_side_contract.md`, and records both in the material input sheet. This document defines
the declaration, the result of a check, what accepts which reason, the run-time watches and the sheet.

## 1. The declaration

A consumer writes one declaration per experiment: its operating conditions, declared once, and one entry per
model that reads material fields.

```json
{
  "consumer": {"name": "mime", "version": "0.3.0"},
  "operating_conditions": {
    "temperature": {"value": 310.15, "unit": "K"},
    "shear_rate": {"range": [50.0, 500.0], "unit": "1/s"}
  },
  "models": [{
    "model": {"name": "stokes_drag", "version": "0.3.0"},
    "model_configuration_hash": "sha256:...",
    "checked_over": {"domain": "lumen"},
    "target": {"species": {"ncbi_taxon": 9606}},
    "reads": ["fluid.dynamic_viscosity"],
    "consumer_parameters": ["fluid.mu"],
    "requirements": [{
      "field": "fluid.dynamic_viscosity", "want": "value", "label": "materica.fluid.newtonian.v1",
      "conditions": {
        "temperature": {"tolerance": {"value": 1.0, "unit": "K"},
                        "reason": "viscosity falls about 2 % per kelvin near 37 °C",
                        "consequence": "1 K moves drag by about 2 %"},
        "shear_rate": {"tolerance": {"value": 0.0, "unit": "1/s"},
                       "reason": "the Newtonian label must hold over the operating shear rates"}}}],
    "families": {},
    "mixing": {"fraction_sum_tolerance": 1e-9, "rules": {"fluid.dynamic_viscosity": "refuse"}},
    "combinations": [],
    "acceptances": [
      {"acceptance": "waiver", "region": "lumen", "field": "fluid.dynamic_viscosity",
       "condition": "shear_rate", "code": "condition_unstated",
       "reason": "water is Newtonian over the band (recalled); the source states no shear rate"},
      {"acceptance": "accepted_difference", "section": "fluid", "fact": "species",
       "value": {"status": "not_applicable"}, "reason": "water has no species"}],
    "chains": [],
    "trainable": []
  }]
}
```

| Member | Contents |
|---|---|
| `consumer` | who declares: name and version |
| `operating_conditions` | per condition, `{"value", "unit"}` or `{"range": [lo, hi], "unit"}`, in the condition's registered unit, declared once for the experiment [BC-001] |
| `sampling` | for the experiment, where any requirement samples: `{"min_acceptance", "reason", "independence"}` (items 8 and 9) [BC-044] |
| `region_conditions` | per model, optional: region to operating conditions that override the experiment's there, such as a heated region [BC-001] |
| `model` | the model's name and version |
| `model_configuration_hash` | a hash of the model's whole configuration with every value read from records removed, by a procedure the consumer names in the sheet (for MIME, the graph's configuration minus the parameters the sheet derives from records) |
| `checked_over` | where requirements are checked: `{"domain": <name>}` (the regions of a scene domain, `geometry.md`), `{"path": <name>}` (every interval of a layered path, by the path's `name`) or `{"records": [<material references>]}` (records read with no scene) [BC-002] |
| `target` | the specimen facts the model stands for, each in the record's fact shape (`provenance.md` section 6.2) without `basis`; differences are computed against it (section 3) |
| `reads` | every field the model reads |
| `consumer_parameters` | every consumer parameter a record feeds; each needs a derivation in the sheet (section 9) |
| `requirements` | per field: `want` (`read_side_contract.md` section 6), required; `conditions`, per condition either `tolerance` (absolute, in the condition's unit) or `accept` (a token list), each with its `reason` and, where known, its `consequence`; optionally `label`, the label the model assumes; and `represents`, the spread its question needs where it samples (`uncertainty.md`); and, where `represents` is `population` and the field is sampled, `population_level`, which no other requirement holds: `{"level", "within"}` as in `uncertainty.md` section 1, or `{"level", "balanced_over": <level>}` for a balanced draw from an ensemble [BC-043]; and optionally `review`, `reviewed` where the model needs a value someone checked against its source (item 11) [BC-049] |
| `families` | for each parameter-set field, the family version the model's evaluator implements (`model_families.md`) |
| `mixing` | `fraction_sum_tolerance`, set by the model's precision, and per field the rule the model applies in a cell holding more than one material: `identity`, a named rule, or `refuse` (`mixing_rules.md`) |
| `combinations` | lists of fields of one material, from different sections, that the model combines into one quantity (section 3) |
| `acceptances` | every pick, waiver, implied condition, accepted difference, extrapolation, nominal, distribution and overlay (section 4) |
| `chains` | hand-overs at events, as pairs of family and record (section 6) |
| `trainable` | fields the model fits, each `{"field", <location>}`, its region, interval or record (section 7) |
| `precision` | per model, the floating-point precision it evaluates in, `binary32` or `binary64`, where the model evaluates tables or parameter sets [BC-047] |
| `engine` | for a model that is a physics engine: `crosswalk`, the pin of its engine crosswalk (`usd_binding.md` section 10.1), OpenMaterica's or one the consumer writes and passes to the build with the declaration; `values`, per crosswalk attribute with no OpenMaterica field, `{"value", "unit", "reason", "basis"}` in SI, with no `unit` for an attribute with no dimension; and optionally `region_values`, per region, values that override `values` there, as `region_conditions` does for conditions [BC-039] |

**The declaration's shape.** The build reads a declaration as JSON by `record_format.md` section 1 item 6 and
checks it on its own, before any record is read, against the table below. A member this document marks
optional, or gives only where a condition holds, may be absent. A member whose absence an accepted rule
already refuses or leaves uncovered may be absent; the table names the rule. Every other member is required;
where it holds a list or an object, an empty one is allowed and is the declaration (a `target` of `{}` names
no fact). A member that holds a token holds one of those listed for it, and a name a field or condition, one
the build's version registers. [BC-048]

| Place | Member | Required | Holds |
|---|---|---|---|
| declaration | `consumer` | yes | `{"name", "version"}`, both required |
| | `operating_conditions` | yes, `{}` allowed | registered condition to `{"value", "unit"}` or `{"range": [lo, hi], "unit"}`, for a numeric condition, in its registered unit, `lo` not above `hi` |
| | `sampling` | where a requirement samples (item 8) | `{"min_acceptance", "reason", "independence"}`, all required (items 8, 9) |
| | `models` | yes, at least one | model entries |
| model entry | `model` | yes | `{"name", "version"}`, both required; no two entries of one `name` |
| | `model_configuration_hash` | yes | a string |
| | `region_conditions` | no | region to operating conditions as above |
| | `checked_over` | yes | exactly one of `{"domain"}`, `{"path"}`, each a name, and `{"records"}`, at least one material reference, none twice |
| | `target` | yes, `{}` allowed | a fact of `provenance.md` section 6.2 to its shape there without `basis`, its text members (`label`, `text`) optional, since none is compared (section 3 item 1); never a status object |
| | `reads` | yes, at least one | registered fields, none twice |
| | `consumer_parameters` | yes, `[]` allowed | strings |
| | `requirements` | no: absent, every field read gives `no_requirement` (item 1) | requirements, at most one per field, each for a field in `reads` |
| | `families` | yes, `{}` allowed | parameter-set field to the family version (`model_families.md`) |
| | `mixing` | no: absent, no rule is declared, and a field with no declared rule is refused (`mixing_rules.md` section 1 item 3) | `{"fraction_sum_tolerance", "rules"}`, both required: a number not below zero; field to `identity`, a rule `mixing_rules.md` names, or `refuse` |
| | `combinations` | yes, `[]` allowed | lists of two or more fields in `reads`, from different sections |
| | `acceptances` | no: absent, nothing is covered (section 4.2) | acceptances (below) |
| | `chains` | yes, `[]` allowed | `{"from", "event", "to", "state_mapping"}`, all required (section 6) |
| | `trainable` | no: absent, no field is trainable, and every reason section 7 would report refuses | entries `{"field", <location>}` (section 7) |
| | `precision` | where the model evaluates tables or parameter sets (item 10) | `binary32` or `binary64` |
| | `engine` | for a physics engine (item 7) | `{"crosswalk", "values"}` and optionally `region_values` (`usd_binding.md` section 10.1) |
| requirement | `field`, `want` | yes | a field in `reads`; a token of `read_side_contract.md` section 6 |
| | `conditions` | no: absent, a condition the record holds gives `condition_unchecked` (`read_side_contract.md` section 5) | registered condition to a requirement condition |
| | `label` | no | a label registered for the field (`record_format.md` section 4.1) |
| | `review` | no | `reviewed` (item 11) |
| | `represents` | no: a requirement holding it samples (item 12) | a token of `uncertainty.md` section 1 |
| | `population_level` | where `represents` is `population`, and only there (the members table) | the object the members table gives |
| requirement condition | `tolerance` or `accept` | exactly one | `{"value", "unit"}`, not below zero, in the condition's unit, for a numeric condition; at least one token of the condition's row, for a token one |
| | `reason` | yes (item 3) | a string of at least one character |
| | `consequence` | no | a string |
| acceptance | `acceptance` | yes | a kind of section 4.1 |
| | `record`, `region`, `interval` | as its kind's row in section 4.1 says | a material reference; a region's name; an interval |
| | `field` | yes, but an `accepted_difference` names `section` and an `overlay_scope` neither | a registered field |
| | `reason` | yes (item 4) | a string of at least one character |
| | `basis` | for `extrapolation`, `nominal` and `distribution` (item 4); no other kind holds it | a string of at least one character |
| | its kind's own members | as section 4.1's row gives them: required; or, where the row gives a condition ("where the code names one"), required where it holds and refused where it does not; or optional where the row says "optionally" | a pick's `index`, a whole number not below zero; a waiver's `code`, a reason of `read_side_contract.md` section 4 other than `condition_unknown_name`, which section 4.2 never accepts (a code names a condition where its reasons always carry one: the six `condition_*` codes, `outside_range`, `at_edge` and `range_unstated`; a waiver whose `code` is no reason names no condition), and `label` as above; an implied condition's `fact` and `token`, of `provenance.md` section 6.2, and its `implies`, per registered condition as section 4.1's row gives it, in the condition's registered unit, `lo` not above `hi`, a `basis` there ignored; an extrapolation's `method`, `constant` or `consumer_law`, and its `law`, a string of at least one character; an accepted difference's `section`, a registered section, and `fact`, a fact of `provenance.md` section 6.2, its `value` that fact's shape (its `basis` and text members optional), a status object or `"any"`; a nominal's `value` or `params`, exactly one, `params` only for a field whose row allows the form `parameter_set` (`read_side_contract.md` section 1); a distribution's `distribution`, a token of `uncertainty.md` section 4, `distribution_parameters`, that token's parameters, named as there, and `space`, `identity` or `log` (section 4.3); an overlay's and an `overlay_scope`'s `overlay`, a material reference; an `overlay_scope`'s `accepts`, at least one of `consumer`, `model` and `configuration`, none twice |
| trainable entry | `field` and one of `record`, `region`, `interval` | yes | a field in `reads`, at a location the model is checked over |
| material reference | `id`, `version`, `content_hash` | yes | strings |

A declaration departs from its shape where:
- it is not valid JSON by that item, or is not an object;
- a required member is missing, or a member is of another JSON type, or empty where the table asks for one
  entry or more;
- it holds, at any depth, a member the table does not name at that place, a member one slip
  (`record_format.md` section 10) from a named one included, but for a `basis` inside an implied condition's
  `implies`, which section 4.1's row ignores;
- a token or a registered name is not one of those its member takes, a slip of one, another member's token and
  one in another case included;
- a name is given twice where the table allows it once: two models of one `name`, a record listed twice in one
  `checked_over`, a field twice in `reads`, two requirements for one field, two `trainable` entries for one
  field at one location;
- a requirement or a `trainable` entry names a field its model does not list in `reads`, or a `trainable`
  entry a location its model is not checked over (a `record` where it is checked over a domain or a path, a
  `region` or an `interval` where it is checked over `records`: section 2 item 2);
- a `reason` or `basis` is not a string of at least one character;
- a value breaks a constraint its row's Holds column states (a `range` whose `lo` is above its `hi`, a unit
  other than the registered one, a number below zero, an `index` with a fractional part, a combination of
  fewer than two fields or of fields of one section, two of a member's mutually exclusive alternatives, an
  empty `law`, a distribution's parameters other than its token's, a repeated `accepts` token).

The build refuses at build a declaration that departs from its shape, or that breaks a rule of items 3, 4, 7,
8, 12, the `population_level` rule, or section 4.1's location rule or item 4. Each refusal is `{"item",
"pointer", "detail"?}`: the case of the rule broken, a JSON pointer (RFC 6901) into the declaration, and
optionally `detail`, text for people that no case compares. The pointer names the member at fault; for a
missing member, the object that should hold it; of two of one name, the later entry of its list, whole (the
model entry, not its `model.name`; the requirement, not its `field`; the field in `reads` or the record in
`checked_over.records` itself); for a waiver naming a `label` that section 4.1 item 4 refuses, that waiver's
`label`; for a model item 7 refuses, its `engine`, one refusal per model, whichever of that item's rules it
breaks; for a text that is not valid JSON, or a declaration that is not an object, the empty pointer, and
nothing else is checked. The member at fault is the most specific one: for a value that breaks its row's
Holds, that member; for what item 12 refuses, the member that needs the suite (`checked_over`'s `domain` or
`path`, `region_conditions`, `sampling`, a requirement's `represents` or `population_level`, the model's
`engine`), or the acceptance or `trainable` entry itself. A member deeper down that holds another JSON type is
a member at fault like any other: the pointer names it, nothing inside it is checked, and the rest of the
declaration is. A rule that judges one member against another stands aside where the other is itself at
fault, so that one fault is one refusal: the `population_level` rule beside a `represents` that is no token, a
requirement's `field` against a `reads` at fault (an empty one too), and a waiver's missing `condition`
beside a `code` that is refused; an acceptance that names no known kind is refused at itself, and none of its
other members is judged. Standing aside has three exceptions.
A member is still held to what it must be whichever value
the other holds, namely its JSON type (a distribution parameter's value is a number; an accepted difference's
`value` is an object, a status object, judged as one, or `"any"`), a label that no registered field has, and
`params` where no registered field's row allows the form `parameter_set`. A rule the text states for a member at
fault still applies: a waiver whose `code` is no reason names no `condition`. And an entry that is no well-formed
name (a reference without string `id`, `version` and `content_hash`, a `field` that is no string) is
neither the same as nor different from another, and no rule compares it. An acceptance that names no known kind
keeps the rule above: none of its other members is judged. Three rules ask what the declaration holds, at
fault or not, and do not stand aside: a requirement samples where it holds `represents`, whatever `represents`
holds (item 8); a waiver's `label` is refused unless its requirement holds `review: "reviewed"` and names that
label, whatever else the requirement's `label` and `review` hold (section 4.1 item 4); and a `trainable`
entry's location is judged against the one alternative `checked_over` names, whatever that alternative holds
(a `domain` or a `path` that is no string is still a scene, and a `records` list, an empty one too, is still
the list a record must be in), and against none where `checked_over` names two alternatives or none, or its
`records` is no list.
A fault more than one rule names carries the case of
the first of: items 3, 4, 7 and 8, the `population_level` rule and section 4.1's location rule [BC-004] [BC-005]
[BC-040] [BC-044] [BC-043] [BC-037]; section 4.1 item 4 [BC-050]; item 12 [BC-051]; this paragraph
[BC-048]. Two faults with one case and one pointer are one refusal. The build reports every refusal it finds,
and reads nothing for a declaration it refuses. [BC-048]

1. Only a model that reads a field declares anything about it. A field in `reads` with no requirement gives
   `unknown` with the reason `no_requirement`; the build reads nothing for it, so its result holds `status`,
   `reasons` and the build's members alone. [BC-003]
2. A requirement belongs to the model that reads the field, never to the experiment as a whole. [not yet
   covered]
3. A tolerance or accept list MUST carry its reason; the build refuses one without (an empty `reason` breaks
   its row's Holds, BC-048). [BC-004]
4. Every acceptance MUST carry a `reason`; an extrapolation, a nominal and a distribution also carry the
   `basis` of their number. The build refuses one without (an empty `reason` or `basis` breaks its row's
   Holds, BC-048). [BC-005]
5. A requirement with a `label` gives `not_met` with the reason `label_mismatch` when the label stored on the
   value the result rests on differs or is absent (section 2 item 8). [BC-027]
6. A layered path read with `checked_over: {"path": ...}` is named by its `name` member (`geometry.md`), and
   its intervals by their 0-based index. [BC-036]
7. A model with `engine` reads the fields its crosswalk sources, with `want` `value`, and is checked over a
   domain that does not include the background; one checked over a path or records, over a domain that
   includes the background, or with another `want`, is refused at build. A declared engine value without
   `reason` and `basis`, or for an attribute the crosswalk sources from a field, is refused at build, and so
   is a pinned crosswalk that is not passed or does not validate (`engine_crosswalk_invalid`), and two engine
   models whose domains share a region (`usd_binding.md` section 10.1 item 10). Its per-field results (section
   2) gate what the adapter writes; its engine results (section 2 item 6), after the adapter has written, gate
   the build. [BC-039] [BC-040]
8. `sampling.min_acceptance` is a number in (0, 1]: the lowest joint acceptance the consumer accepts for the
   run, below which a sampler refuses (`uncertainty.md` section 3 rule 11), with its `reason`. A declaration
   in which a requirement samples, without it or with one outside (0, 1], is refused at build. [BC-044]
9. `sampling.independence` is a list of `{"fields": [<location and field>, ...], "reason", "basis"}`. Each
   entry declares that the fields listed are sampled as independent. Every pair of fields a run samples must
   fall within one entry; a pair outside every entry is refused at build. The entries are recorded in the
   sheet. [BC-046]
10. `precision` is recorded in the sheet, and a model that evaluates tables or parameter sets without it is
    refused at build. [BC-047]
11. A requirement's `review` holds `reviewed`, the one token of schema 0.1.0. A requirement holding it gives
    `unknown` with the reason `not_reviewed` on a result whose `provenance.review` (`read_side_contract.md`
    section 2) is not a completed review: one holding `result` `reviewed` (`provenance.md` section 2 item 6).
    A result that holds no `provenance` gets no such reason. A review lies outside the content hash, so the
    build reads the review the record holds when it runs (section 9 item 3): a review added after a record was
    pinned can let a refused build pass, and one removed can refuse an accepted build, the pin unchanged. Each
    result's `provenance` holds the review its answer rested on (section 2). [BC-049]
12. A build refuses at build what it cannot check: where it does not claim the scene suite, a model checked
    over a domain or a path, `region_conditions`, and an acceptance or `trainable` entry located at a region
    or an interval; where it does not claim USD read, a model with `engine`; where it does not claim the
    sampling suite, `sampling`, a requirement's `represents` or `population_level`, and a `distribution`
    acceptance. A requirement samples where it holds `represents`. Items 7 and 8 and the `population_level`
    rule (the members table) come first, member by member: where item 7 refuses a model with `engine`, its
    `engine` gives no refusal under this item, and where item 8 or that rule refuses the declaration over a
    requirement, that requirement gives none. [BC-051] [BC-040] [BC-043] [BC-044]

## 2. Results

The build reads every required field in every region, interval or record a model is checked over, by the read
of `read_side_contract.md`, and returns one result each: the read result (`read_side_contract.md` section 2)
with `model`, the location it was read for, `record`, `field`, `specimen_differences`, `accepted`,
`accepted_by`, `not_accepted` and, on a result at a location where its field is listed in `trainable`,
`trainable_by` added. A read applies an acceptance only at its own record or region (`read_side_contract.md`
section 1), and a read request names no interval, so the build reads an interval by its record and gives that
read the acceptances located at that interval as located at that record. [not yet covered]

```json
{"model": "stokes_drag", "region": "lumen", "field": "fluid.dynamic_viscosity",
 "record": {"id": "materica/MAT-0002", "version": "1.0.0", "content_hash": "sha256:..."},
 "status": "unknown", "reasons": [{"code": "condition_unstated", "condition": "shear_rate"}],
 "value": 0.000692, "unit": "Pa.s",
 "conditions": [{"name": "temperature", "status": "met",
                 "record": {"value": 310.15, "unit": "K", "basis": "stated"},
                 "operating": {"value": 310.15, "unit": "K"}},
                {"name": "shear_rate", "status": "unknown", "record": {"status": "unstated"},
                 "operating": {"range": [50.0, 500.0], "unit": "1/s"}}],
 "specimen_differences": [{"section": "fluid", "fact": "species",
                           "record": {"status": "not_applicable"}, "target": {"ncbi_taxon": 9606}}],
 "labels": ["materica.fluid.newtonian.v1"],
 "accepted": true, "accepted_by": [0, 1], "not_accepted": []}
```

1. `status` is one of three: `met`, `not_met` or `unknown`. It states a fact about the record against the
   requirement, and declarations never change it. [BC-006]
2. The result carries `model`, and the region, interval or record it was read for. [BC-028] Over records the
   location is the record read: the result holds `record` and neither `region` nor `interval`. Every result of
   a field holds the `field` read, and a combination's its `fields` (section 3 item 6). [BC-028]
3. `specimen_differences` lists, for each fact the target names, the record's fact where it differs from the
   target, as facts, never as a grade (section 3). [BC-008]
4. `accepted` is true when each reason and each specimen difference of the result is covered as the table in
   section 4.2 says, and `accepted_by` lists the 0-based indexes, in the model's `acceptances`, of every
   acceptance used, the ones the read itself applied (a pick, an overlay, an implied condition) included.
   [BC-009] `not_accepted` lists each reason and each specimen difference that nothing covers, empty exactly
   when `accepted` is true. [BC-009]
5. The build MUST refuse to build while any result is not accepted, and reports every such result, not only
   the first. [BC-010]

The build gives one report:
- `consumer`, as declared;
- `records`, every record a read resolved, as `{"id", "version", "content_hash"}`;
- `declaration`, as given;
- `refusals`, the declaration's own (section 1);
- `results`, every result of this section and of section 3 item 6, each field result with the `provenance` its
  read returned, which holds the review the result's answer rested on;
- `watches` (section 8);
- `unused` (item 9).

A declaration the build refuses on its own gives no results, no watches and nothing unused; its report holds the
declaration as given where the text is JSON, and its `consumer` where the declaration declares one. The report's
schema cannot tell a text that is not JSON from a declaration whose one refusal is BC-048 at the empty pointer,
and requires the declaration unless the report's one refusal is that. [not yet covered] The build refuses to
build while the report holds a refusal, as it does while a result is not accepted (item 5). The material input sheet (section 9) holds the
report's `consumer`, `records`, `declaration`, `results` and `watches` under those names, and adds its own;
`refusals` and `unused` are the report's alone. [BC-010]

6. **Engine results.** A model with `engine` is judged in order: the build reads its fields; the adapter
   writes where those results are accepted (`usd_binding.md` section 10); the stage check runs; and the build
   then gives one engine result per shape of the model's regions, `{"model", "region", "shape", "status",
   "reasons"}`. An engine result states a fact about the stage, not a record. Its status is `met` unless one
   of these applies:
   - `engine_material_missing` (not_met): no engine material, or only the physics scene's (`usd_binding.md`
     section 9 item 8);
   - `engine_material_foreign` (not_met): an engine material with no stamp, or stamped for another material,
     or stamped with the `stage` convention for other stage units (item 6);
   - `engine_material_stale` (not_met): a stamp that does not re-derive (item 7), or whose crosswalk pin, read
     requests, acceptances or declared values differ from those the current declaration gives for that
     region, so engine materials written at 293 K fail a declaration at 310 K;
   - `engine_density_overridden` (not_met): an authored, non-zero effective density from
     `UsdPhysics.MassAPI` that differs (item 5);
   - `engine_mass_not_comparable` (unknown): an authored, non-zero `physics:mass` on the shape or an
     ancestor (item 5).

   The build refuses while any engine result is not accepted (section 4.2). [BC-039] [BC-041]

**The build's terms.** An acceptance is **given** to a read when the build puts it in the read's request (item
7). A read **applied** an acceptance given to it where its result shows it: an implied condition that filled a
condition (a `conditions` entry whose `record` is the value the implied condition supplies, with basis
`implied`); a nominal or an extrapolation that the result's `assumption` names; a `trainable` acceptance, on a
result that carries `initial_value_only`. An implied condition, nominal, extrapolation or `trainable`
acceptance given and not so shown was not applied; when a pick or an overlay is applied is [not yet covered].
An acceptance is **located at** a result's location when it names the record read, equal in `id`, `version`
and `content_hash`; one located at a region or an interval is located at no record, and an accepted difference
with no location is located at every location its model is checked over. An acceptance **covers** a reason or
a specimen difference of a result when it names the result's field (an accepted difference, its section), is
located at the result's location, and is of a kind section 4.2's row for that reason names, under that row's
own condition (the code and condition named; the `assumption`), and, for a waiver naming a label, as section
4.1 item 4 says. A label is **trusted** on a result where the record stores it on the value the result rests
on (item 8) with a `label_basis` whose `basis` is `stated` (`record_format.md` section 4.1), or where the
result's review is a completed review (section 1 item 11). An acceptance is **used** where it covers a reason
or a specimen difference of a result, or a read applied it. [BC-009] [BC-053] [BC-050]

7. The build's own read request holds the requirement's `want` and `conditions`, and the declared operating
   conditions. The build gives each read the acceptances of the kinds a read takes (`read_side_contract.md`
   section 1), overlays aside (which overlays it gives a read is [not yet covered]), that name the read's field
   and are located at its location, and the `trainable` acceptance section 7 gives. It maps the ones the read
   applied to their indexes in the model's `acceptances` for `accepted_by`. [BC-009]
8. The build's own reasons (`no_requirement`, `label_mismatch`, `not_reviewed`) join the read's, and the
   result's status is the worst of them all. Every other member of the result is as the read returned it,
   including `value`, where the read returned one. The build checks a requirement's `label` against the label
   stored on the value the result rests on (the field, or the alternative read), whether or not the read
   reached step 12, so a label never hides behind another refusal. A result that rests on no stored value (its
   record or field not found, a refusal before step 7 finds the field, or no single alternative:
   `read_side_contract.md` section 3, step 7) is checked against none. [BC-027] [BC-049]
9. The build lists in `unused`, per model, each acceptance not used (the build's terms), as `{"model",
   "acceptance": <its index>}`, so a waiver for another field, record or code is seen. An unused acceptance
   refuses nothing. [BC-053]

## 3. Specimen differences

1. For each fact the target names, the build compares the record's fact (the section's merged with the
   field's) with the target's: a species by NCBI Taxonomy identifier; an anatomical site by UBERON identifier;
   a token fact by token; a numeric fact by value, the target's value (or every value of its range) lying
   within the record's value or range. Text members are never compared. [BC-011]
2. A fact the target names that the record holds as any status object, or does not hold at all, is a
   difference, listed with the record's status object, or with no `record` where the record does not hold the
   fact. [BC-012] A result that holds no `specimen` (`read_side_contract.md` section 2 item 6) lists no
   specimen differences. [BC-008]
3. Facts the target does not name are not compared. [not yet covered]
4. The build MAY add the ontology's relation where one exists (`relation`: `part_of`, `sibling`). [not yet
   covered]
5. A difference is listed per section, so one accepted difference for a section covers every field of it.
   [BC-013]
6. **Combinations.** A model that combines fields of one material from different sections into one quantity
   (an impedance from `bulk.density` and an acoustic sound speed) lists them in `combinations`. The build
   compares the specimen facts of those fields with each other, by the rules of item 1, and returns one result
   per combination: `{"model", location, "record", "fields": [...], "specimen_differences": [...],
   "accepted", "accepted_by", "not_accepted"}`, each difference accepted like a difference from the target,
   and `not_accepted` as section 2 item 4 gives it. Two fields may describe different specimens even when each
   matches the target (AD 4.2). [BC-014]

## 4. Acceptances

### 4.1 The list

One list, `acceptances`. Every entry has `acceptance`, one of the kinds below; names where it applies; names
the `field` it covers (an `accepted_difference` names its `section` in place of a field, section 3 item 5, and
an `overlay_scope` names none); holds its kind's own members; and carries `reason`.

| `acceptance` | Location | Own members | Effect |
|---|---|---|---|
| `pick` | `record` (pinned by hash): the target's, or an overlay the read applies to the field; a pick that also names a `region` or an `interval` is not applied in a plain read, both being its location too (`read_side_contract.md` section 1) | `index`, a whole number not below zero (0-based, into the stored `alternatives` of the field read) [PR-330] | the read uses that alternative, read like any field; if its conditions are not met, its own reasons stand [BC-015]; an index naming no stored alternative of the field read, or a pick located at the base of a field an applied overlay replaces, gives `pick_invalid`, which nothing accepts (`read_side_contract.md` section 3, step 7) [PR-304] |
| `waiver` | `region`, `interval` or `record` | `code`, and `condition` where the code names one; optionally `label`, the label the consumer's judgement rests on | covers one reason of one result (section 4.2) [BC-016]; one naming a `label` covers only where that label is trusted (item 4) [BC-050] |
| `implied_condition` | `region`, `interval` or `record` | `fact`, a specimen fact whose shape has a `token` member, and `token`, one of its tokens (`provenance.md` section 6.2); `implies`, per registered condition `{"value", "unit"}` or `{"range": [lo, hi], "unit"}` for a numeric one and `{"token"}`, with a token of its row, for a token one: a record condition's shapes without `basis` (one there is ignored), `plus_minus` or `set_or_measured`, and never a status object (`provenance.md` section 6.1) | supplies a value for a condition the record leaves unstated, on fields whose specimen states that fact and token; the value is checked like a stated one, with basis `implied` [BC-017] |
| `accepted_difference` | optional: absent, every location the model is checked over | `section`, `fact`, `value` (in the fact's shape, or `"any"`) | covers specimen differences in that section and fact whose record value equals `value` under section 3 item 1 [BC-018] |
| `extrapolation` | `region`, `interval` or `record` | `method` (`constant` or `consumer_law`), `law` (text of at least one character, which a reader does not judge), `basis` [PR-330] | where the read applies it (under `want: value`, never at or across a declared edge: `read_side_contract.md` section 5), the result carries the end value and the operating value; the consumer computes the extrapolated value by its method, and the sheet records it [BC-019] |
| `nominal` | `region`, `interval` or `record` | `value`, `basis`; for a parameter set, `params` in place of `value` | supplies a value for an interval, in the field's registered unit, or the parameter vector held for a parameter set (under any structure, for one-at-a-time variation, or where `params` is not applicable), with exactly the family's parameters and passing its admissibility; refused: a value outside the interval's bounds (in a read, `nominal_invalid`), a vector with a missing or extra parameter or outside an `interval` structure's box, and an inadmissible vector [BC-020] [BC-042] |
| `distribution` | `region`, `interval` or `record` | `distribution`, `space`, `distribution_parameters`, `basis` | sampling where the record gives no distribution (section 4.3) [BC-021] |
| `overlay` | none | `overlay` (identifier, version, hash) | applies that overlay (section 5) [BC-022] |
| `overlay_scope` | none | `overlay`, `accepts` (any of `consumer`, `model`, `configuration`) | covers `overlay_scope_mismatch` for that overlay, in the members named [BC-023] |

An acceptance whose kind needs a location and names none is refused. [BC-037]

1. An implied condition never overrides a stated condition: it fills only an unstated one, which is a
   condition the record holds as `{"status": "unstated"}` or does not hold, never one holding another status
   object. A room-temperature experiment that implies 310.15 K for in vivo values still fails a 1 K tolerance
   at 293 K. [BC-017]
2. An accepted difference with `value` `"any"` accepts every value of that fact in that section; one that
   names a value accepts only that value, so accepting water's `not_applicable` species for the fluid section
   does not accept porcine blood. [BC-018]
3. An evaluator that clamps a table at the ends of its readable range (`record_format.md` section 6, table
   item 3) is extrapolating by a constant: it needs an extrapolation of method `constant`, or its in-range
   flag MUST stop the run (`read_side_contract.md` section 7). [not yet covered] An evaluator returns no other
   value outside that range, so a `consumer_law` extrapolation is computed beside it, from the end value: the
   value a read under that extrapolation returns, at the readable range's nearest end, taken from inside the
   range (`read_side_contract.md` section 5), or the one the evaluator returns there, where it returns one
   (`read_side_contract.md` section 7 item 1). [PR-307] [TE-003]
4. Treating a value as its label's trivial model beyond what the record states (a Newtonian fluid at a shear
   rate the record leaves unstated) is the consumer's judgement, never the label's (`record_format.md`
   section 4.1). A waiver that names no label is the consumer's judgement alone: its `reason` states the
   judgement and what it rests on, which is its basis. A waiver that names a label is still the consumer's
   judgement, narrowed to values whose label is trusted, and so needs the label's value reviewed, through the
   requirement: the build refuses it at build unless the requirement for its field names that `label` and
   holds `review: "reviewed"` (section 1 item 11). It covers its reason only on a result whose stored label
   (section 2 item 8) is that label and is trusted (section 2): stated by the source, or on a value whose
   review is completed. So only a waiver of `not_reviewed` the consumer declares lets an unreviewed value
   build, and no waiver makes an inferred, unreviewed label cover anything. [BC-050] [BC-016]

### 4.2 What covers which reason

This table is the only place that says which acceptance covers which reason (other documents cite it). A
reason not listed is never accepted, `condition_unknown_name` among them: a condition name the reader does not
know is a typo or a version mismatch, which the reader's upgrade remedies, not a waiver. [BC-038] A waiver
whose `code` is `condition_unknown_name` is refused at build, at its `code` (section 1). [BC-048]

| Reason | Status | Covered by |
|---|---|---|
| `condition_unstated`, `condition_unchecked`, `condition_uncertain` | unknown | a `waiver` naming that condition and code |
| `no_requirement`, `stated_without_origin`, `outside_check_points`, `fill_in_version_mismatch`, `entries_withheld`, `not_reviewed` | unknown | a `waiver` naming that code |
| `no_pick` | unknown | a `pick` only |
| `range_unstated`, `outside_coverage` | unknown | an `extrapolation` only |
| `outside_range` | not_met | an `extrapolation`, only on a result whose `assumption` names it |
| `want_mismatch`, for a value read from an interval, or a vector read from a parameter set with none | not_met | a `nominal`, only on a result whose `assumption` names it |
| `engine_mass_not_comparable` | unknown | a `waiver` naming that code |
| `overlay_scope_mismatch` | not_met | an `overlay_scope` naming every member that differs |
| a specimen difference | (not a status) | an `accepted_difference` |
| a condition reason, `outside_range`, `range_unstated`, `outside_coverage` or a specimen difference, on a field listed in `trainable` | any | its `trainable` entry (section 7), on a result that carries a value |

A waiver covers a reason whatever its `alternative` (`read_side_contract.md` section 2 item 2). [BC-016]

### 4.3 A declared distribution

```json
{"acceptance": "distribution", "region": "tissue", "field": "bulk.density", "distribution": "normal",
 "space": "identity", "distribution_parameters": {"mean": 1050.0, "sd": 25.0},
 "basis": "midpoint and quarter-width of the proxy range 1000 to 1100 kg/m3",
 "reason": "the record gives an interval only"}
```

`distribution` takes a token of `uncertainty.md` section 4 (`normal`, `lognormal`, `uniform`, `triangular`,
`student_t`, `beta`), and `distribution_parameters` that token's parameters, named as there (a lognormal's
`mean` and `sd` are of the value itself, in the field's unit); `space` is `identity` or `log` (natural
logarithms); `basis` says why. A sampler draws from it as declared, and the sheet records it as the
consumer's assumption, never as the record's statistics (`uncertainty.md` section 3).
[BC-021]

## 5. Overlays

The reader applies a declared overlay and refuses a base mismatch or a conflict (`record_format.md` section
4.4). The build compares its scope.

1. A model applies an overlay only if an `overlay` acceptance names it by identifier, version and content
   hash. [BC-022]
2. For an overlay of purpose `fit` or `scene_override`, the build compares `scope.consumer` with the declaring
   consumer's `name`, `scope.model` (name and version) with the declaring model's, and
   `scope.model_configuration_hash` with the model's, each as strings, code point for code point; a scope
   names no consumer version, so none is compared, and one without `model` or `model_configuration_hash`
   differs. For an overlay of purpose `measurement`, it compares `scope.consumer` only. A difference gives
   `overlay_scope_mismatch` (section 4.2). A `fill_in` overlay's scope names the user in `scope.consumer`, and
   is not compared. [BC-023]
3. An applied overlay replaces whole fields of its base, and the sheet records it. [BC-025]

## 6. Chains of families

```json
"chains": [{"from": {"family": "acme.thermal.arrhenius_damage.v1",
                     "record": {"id": "acme/liver_native", "version": "1.0.0", "content_hash": "sha256:..."}},
            "event": "damage_complete",
            "to": {"family": "acme.thermal.arrhenius_damage.v1",
                   "record": {"id": "acme/liver_coagulated", "version": "1.0.0",
                              "content_hash": "sha256:..."}},
            "state_mapping": {"damage": "damage"}}]
```

1. A chain names the event that ends the first family's range and the family and record that take over, with
   a mapping of state. Each `record` is a material reference, `{"id", "version", "content_hash"}`, pinned by
   its content hash as every record a consumer names is (`record_format.md` section 7 item 1). A family never
   names its successor (`model_families.md` section 5). [BC-026]
2. The build records each chain in the sheet. The run records each hand-over with its time. [not yet covered]

## 7. Trainable fields

1. A field listed in `trainable`, with its region, interval or record, is a parameter the consumer fits. An
   entry is `{"field", <location>}`, its location one of `record`, `region` and `interval`; it names a field
   in `reads` at a location the model is checked over, and no other entry names that field there (section 1).
   The build gives each read of that field there a `trainable` acceptance (`read_side_contract.md` section 1),
   and the result names the entry by its 0-based index in `trainable`, in `trainable_by`. A result whose read
   went on to step 12 under it carries the label `initial_value_only` (`read_side_contract.md` section 3, step
   12): the record's value is used only as the initial value. [BC-029] [PR-339]
2. For a trainable field, the reasons about conditions (`condition_outside` and `condition_not_accepted`
   included), the form's range (`outside_range`, `range_unstated` and `outside_coverage`, never `at_edge`) and
   specimen differences are reported, not refused, because the consumer will move the value. Every other
   `not_met` reason (a malformed record, a hash or pin mismatch, a unit mismatch, a withheld value, an
   overlay's base) still refuses, and so does a result that carries no value: an alternative is set aside as
   it would be without the acceptance, so a field all of whose alternatives are set aside refuses. [BC-029]
3. A fitted result is written back only as an overlay of purpose `fit` (`record_format.md` section 4.4).
   [not yet covered]

## 8. Run-time watches

1. The build emits watches for the results it accepts, and no others: one for every condition entry of an
   accepted result that a tolerance or accept list checked: `{"model", location, "field", "condition", "unit",
   "source": "tolerance"}` with either `interval` or `accept`, and `unit` with an `interval` only, a token
   condition having none. The interval is the set of values the condition may take while the entry stays met:
   `[r - t, r + t]` for a stated value `r`, `[a - t, b + t]` for a stated range; where the condition's
   `plus_minus` holds a bound u, which narrows the check (`read_side_contract.md` section 5),
   `[r - t + u, r + t - u]` and `[a - t + u, b + t - u]`. Each end is its exact value rounded inward to a
   double, so that every double inside the watch keeps the entry met. An accept-list entry's watch holds the
   accept list. A constant has no axis, but a run that heats it can still leave its tolerance. An entry a
   waiver accepted as `condition_uncertain` gets the interval of a record that states no ±, `[r - t, r + t]`
   or `[a - t, b + t]`, rounded inward too. [BC-030] Where the entry was accepted while `not_met` (a trainable
   field's `condition_outside`, section 7), its interval holds the operating condition the read was given as
   well: the smallest interval holding both. An accept list's watch is unchanged, a token condition having no
   operating condition (`read_side_contract.md` section 1). [BC-030]
2. For a table or power law, the build emits a watch with `source` `form_range`: the form's own range (for a
   table, its readable range, `record_format.md` section 6, table item 3), never widened by a tolerance.
   [BC-031] Where the result was accepted while `outside_range` (under an extrapolation, section 4.1, or on a
   trainable field), the watch holds the operating value as well: the smallest interval holding both. [BC-031]
   Where a declared edge lies inside the readable range, the watch holds only the part between the edges, or
   an edge and an end of the range, that holds the operating value; for an operating value outside the
   readable range, the part beside it, joined with it as above. Each end beside an edge is the double next to
   the edge on the operating value's side, since an evaluator refuses at the edge (`read_side_contract.md`
   section 7 item 7). [BC-031]
3. For a numeric condition whose entry a waiver accepted as `condition_unstated`, on an accepted result, the
   build emits a watch with `source` `declared`, holding as its interval the operating condition the read was
   given (`[v, v]` for a value, `[lo, hi]` for a range); where the read was given none, it emits none. The
   record says nothing there, so the run keeps to what the consumer declared. [BC-052]
4. The consumer checks its watches during the run, on the condition, not only on the value derived from it. A
   model-validity guard on the value itself MAY stay beside them. When a watch fires, the consumer marks the
   results from that point. [not yet covered]
5. The build notes, in the sheet, a declared operating condition that sits exactly on a table knot, because a
   derivative there depends on the evaluator's side (`read_side_contract.md` section 7). [BC-032]

## 9. The material input sheet

The sheet is one JSON document per build. [BC-033]

| Member | Contents |
|---|---|
| `consumer` | as declared, with, per model, the configuration hash and the name of the procedure that computed it |
| `records` | every record read: identifier, version, schema version and content hash |
| `declaration` | the declaration as given, acceptances included |
| `results` | every result of sections 2 and 3, each with its `provenance` (origin, review result, source key, tier where the source registry is available, assistance present or not, witness and fit-reproduction status for a parameter set) and its `labels` (`read_side_contract.md` section 2) |
| `derivations` | for every consumer parameter that a record fed: the base record and field, overlays applied, unit conversions, mixing rule and fractions, derivations, any extrapolated value the consumer computed, and the parameter it reached |
| `watches` | every watch of section 8 |
| `notes` | operating conditions on table knots; anything reported but not refused |

1. Every parameter in a model's `consumer_parameters` appears in `derivations`; one with no derivation is
   reported as unexplained. [BC-034]
2. A value read through a fill-in overlay shows its label (`user_extracted`) and its review result in the
   sheet, and a value stated without origin its reason (`stated_without_origin`), so a run on a user-typed
   value never looks like a run on a curated one. [BC-035]
3. A review is reported as found in the record. The content hash does not cover reviews (`record_format.md`
   section 9), so a pinned record does not pin its review. [not yet covered]
4. The sheet is stored in the run's provenance and, where the scene is a USD stage, on the stage
   (`usd_binding.md`). [not yet covered]

## Cases

| Case | Suite | Tests |
|---|---|---|
| BC-001 | build checks | requirements are checked against the declared operating conditions, per region where overridden |
| BC-002 | build checks | requirements are checked only over what `checked_over` names: a domain's regions, a path's intervals, or listed records |
| BC-003 | build checks | a field read with no requirement gives `unknown` (`no_requirement`) and holds `status`, `reasons` and the build's members alone, since nothing is read for it |
| BC-004 | build checks | a tolerance or accept list without a reason is refused |
| BC-005 | build checks | an acceptance without a reason, or a basis where its kind needs one, is refused |
| BC-006 | build checks | declarations never change a result's status |
| BC-008 | build checks | specimen differences are listed as facts |
| BC-009 | build checks | `accepted` follows section 4.2, with `accepted_by` indexes, in-read acceptances included, by the build's terms: a read is given the acceptances that name its field at its location, and applied only those its result shows; `not_accepted` lists what nothing covers, empty exactly when `accepted` is true |
| BC-010 | build checks | the build refuses while any result is not accepted, and lists them all, in one report; a declaration refused on its own gives no results, no watches and nothing unused |
| BC-011 | build checks | each fact shape is compared with the target as stated; text members never |
| BC-012 | build checks | a fact holding a status object (unstated, not applicable, withheld), or absent from the record, against a named target fact is a difference |
| BC-013 | build checks | one accepted difference for a section covers every field of it |
| BC-014 | build checks | a combination's fields with different specimens give one combination result needing acceptance |
| BC-015 | build checks | a pick by stored index selects that alternative, which is then read like any field |
| BC-016 | build checks | a waiver covers only its own location, condition and code, whatever the reason's `alternative`; one that names no label covers whatever the value's label and its basis |
| BC-017 | build checks | an implied condition fills only an unstated or absent condition, never one holding another status object, and is checked against the tolerance |
| BC-018 | build checks | an accepted difference covers only its value, or every value with `any` |
| BC-019 | build checks | an extrapolation covers `outside_range` only on a result whose `assumption` names it (under `want: value`, never at or across a declared edge), and `range_unstated` and `outside_coverage`; undeclared, they stand; a table read under `want: bounds` outside its range is refused, though an extrapolation names it |
| BC-020 | build checks | a nominal covers a value read from an interval; one outside the bounds is refused; it covers `want_mismatch` only on a result whose `assumption` names it, never step 0's or step 7's |
| BC-021 | build checks | a declared distribution is sampled as declared and recorded as the consumer's assumption |
| BC-022 | build checks | an overlay is applied only when an acceptance names it |
| BC-023 | build checks | an overlay scope difference gives `overlay_scope_mismatch`, accepted only in the members named; `scope.consumer` is compared with the consumer's `name`; a `fit` scope without `model` or `model_configuration_hash` differs |
| BC-025 | build checks | an applied overlay is recorded in the sheet (planned with R7) |
| BC-026 | build checks | a chain is recorded as pairs of family and record (planned with R7) |
| BC-027 | build checks | a required label that differs from the label stored on the value the result rests on, or is absent there, gives `label_mismatch`, beside any other reason, whether or not the read reached step 12; a result that rests on no stored value gives none |
| BC-028 | build checks | every result names its model, the field read, or for a combination its `fields`, and the region, interval or record it was read for: over records, the record and neither a region nor an interval |
| BC-029 | build checks | a trainable field's condition, range and specimen reasons are reported, not refused: the build gives its read a `trainable` acceptance, and the result carries the record's value with `initial_value_only` and names its entry in `trainable_by`; its other refusals stand, `at_edge` among them, and so does a result that carries no value |
| BC-030 | build checks | only accepted results are watched; a tolerance watch holds the interval, or the accept list, within which the entry stays met, narrowed by a stated bound, each end rounded inward; a waived `condition_uncertain` gets the tolerance's interval; an entry accepted while `not_met` gets the smallest interval holding its interval and the operating condition |
| BC-031 | build checks | a form-range watch holding the readable range is emitted for every table or power law of an accepted result, unwidened by a tolerance; joined with the operating value where the result was accepted while `outside_range`; cut at a declared edge inside the range to the part that holds the operating value |
| BC-032 | build checks | an operating condition on a table knot is noted (planned with R7) |
| BC-033 | build checks | the sheet holds every member of section 9 (planned with R7) |
| BC-034 | build checks | a parameter with no derivation is reported as unexplained (planned with R7) |
| BC-035 | build checks | a fill-in value shows its label and review result, an origin-less value its reason, in the sheet (planned with R7) |
| BC-036 | build checks | a layered path is named by its `name` and its intervals by 0-based index |
| BC-037 | build checks | an acceptance with no location where its kind needs one is refused |
| BC-038 | build checks | a reason not in section 4.2's table is never accepted |
| BC-039 | build checks | an engine model's engine results: `met` on the adapter's own output; `engine_material_missing` before it writes; `engine_material_foreign` for an Isaac-bound material; `engine_material_stale` when a declaration at 310 K meets materials written at 293 K; `engine_density_overridden` under a differing `MassAPI` density |
| BC-040 | build checks | refused at build: a declared engine value without reason or basis, or for an attribute sourced from a field; a pinned crosswalk not passed, or that does not validate; two engine models whose domains share a region; an engine model checked over a path, over records, or over a domain that includes the background; one whose requirement wants anything but `value` |
| BC-041 | build checks | an explicit mass gives `engine_mass_not_comparable`, which a waiver accepts and nothing else does |
| BC-042 | build checks | a nominal vector for `ensemble`, `marginals`, `independent` or `interval`: accepted when complete and admissible, and recorded; a missing parameter, an inadmissible vector, or one outside the box is refused; it covers `want_mismatch` on a set with no vector |
| BC-043 | build checks | a sampled population requirement without `population_level`, or a `population_level` in any other requirement, is refused at build |
| BC-044 | build checks | a declaration with a sampled requirement and no `sampling.min_acceptance`, or one outside (0, 1], is refused at build |
| BC-046 | build checks | a run that samples two fields outside every `sampling.independence` entry is refused at build; the entries are recorded |
| BC-047 | build checks | a model that evaluates tables or parameter sets without `precision` is refused at build; the precision is recorded |
| BC-048 | build checks | a declaration that departs from its shape is refused at build, before any read, each refusal its rule's case and a JSON pointer by the precedence and pointer rules: not JSON or not an object; a member missing, of another JSON type, empty where one entry or more is required, not named at its place or one slip from a named one, a `basis` inside an implied condition's `implies` aside; a token or registered name its member does not take; a name given twice; a requirement or `trainable` entry for a field not in `reads`, or a `trainable` entry at a location the model is not checked over; a value that breaks a constraint its row's Holds column states (a `range` whose `lo` is above its `hi`, a unit other than the registered one, a number below zero, an `index` with a fractional part, a combination of fewer than two fields or of fields of one section, two of a member's mutually exclusive alternatives, an empty `law`, a distribution's parameters other than its token's, a repeated `accepts` token); nothing is read for a refused declaration |
| BC-049 | build checks | a requirement holding `review: "reviewed"` gives `unknown` (`not_reviewed`) on a result whose review is not completed, which a waiver of that code covers; a completed review gives no such reason, nor does a result that holds no `provenance` |
| BC-050 | build checks | a waiver naming a `label` is refused at build unless the requirement for its field names that label and holds `review: "reviewed"`; it covers only a result whose stored label is that label and trusted, stated by the source or on a value whose review is completed |
| BC-051 | build checks | a build that does not claim the scene suite, USD read or the sampling suite refuses at build what needs it: a model checked over a domain or a path, `region_conditions`, an acceptance or `trainable` entry at a region or an interval; a model with `engine`; `sampling`, a requirement's `represents` or `population_level`, a `distribution` acceptance; where items 7 and 8 or the `population_level` rule refuse a member, their refusal alone for that member |
| BC-052 | build checks | a waived `condition_unstated` of a numeric condition, on an accepted result, gives a `declared` watch holding the operating condition the read was given, and none where it was given none |
| BC-053 | build checks | the build lists, per model, each acceptance no result used in `unused`: a waiver for another field, record or code, and an acceptance given to a read and not applied; an unused acceptance refuses nothing |
