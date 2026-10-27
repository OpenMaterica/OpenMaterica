<h1 align="center"><img src="https://raw.githubusercontent.com/OpenMaterica/OpenMaterica/main/assets/images/logo.png" alt="OpenMaterica" width="70%"></h1>

[![CI](https://github.com/OpenMaterica/OpenMaterica/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/OpenMaterica/OpenMaterica/actions/workflows/ci.yml?query=branch%3Amain)
[![PyPI](https://img.shields.io/pypi/v/openmaterica?include_prereleases)](https://pypi.org/project/openmaterica/)
[![Code licence: Apache-2.0](https://img.shields.io/pypi/l/openmaterica?label=code%20licence)](https://github.com/OpenMaterica/OpenMaterica/blob/main/LICENSE)

**Material properties for biomedical simulation, each stored with the conditions it holds under, so a simulation
can check that a value applies before it uses it.**

Blood's viscosity at room temperature is not its viscosity at body temperature, and blood is thicker in slow flow
than in fast flow. A viscosity without its temperature and shear rate is a guess; OpenMaterica keeps them together.

> *OpenMaterica* is an open, fail-closed format for the physical properties of substances in and around the
> human body, and a Python reader for it. It is not a simulator: it computes no physics and ships no anatomy.
>
> A material value holds only under conditions: a viscosity at a temperature and a shear rate, a stiffness on a
> specimen of a given shape. Each record states those conditions with every value, with its source and its
> uncertainty, or that the source gave none. A simulation asks for a value at its own operating conditions, and
> the reader answers `met`, `not_met` or `unknown`, with its reasons. A condition the source did not state gives
> `unknown`, never `met`: a value that may not apply is never reported as one that does, and accepting it anyway
> is your declaration, not the reader's.
>
> It has two main integration targets. Records are plain JSON that any language can parse, each pinned by a
> SHA-256 hash of its content, and the Python package has no runtime dependencies. OpenUSD scenes, for
> simulators built on USD, get the same records through a binding the specification defines, optional and not
> yet in the Python package. None of it runs inside a simulation's loop: a simulation reads its values before
> it runs. OpenMaterica covers tissues and body fluids, the media and phantoms that stand in for them, agents
> introduced into them, and the materials of devices that enter or touch them. It aims to be one physical
> foundation for high-fidelity solvers (like [MIME](https://github.com/Microrobotics-Simulation-Framework/MIME))
> and real-time simulators (like [NVIDIA Isaac for Healthcare](https://github.com/isaac-for-healthcare)).

## Example uses

The curated library does not exist yet: the three records in [`examples/`](examples/) (water, NdFeB grade N45
and human blood plasma) show the format. These are the uses it is built for.

- **A microrobot swimming in a blood vessel** needs the viscosity of blood or plasma at body temperature and at
  the shear rates its own motion creates. A value measured outside those conditions reads `not_met`, naming the
  condition that failed. The example plasma record was measured at 37 °C between 10 and 100 s⁻¹, so a robot whose
  flow spans 3 to 1,300 s⁻¹ gets `not_met` on the shear rate, not a number that silently does not apply.
- **A magnetically steered device** needs its magnet's remanence. A magnet grade gives a range, not one number:
  the reader returns the bounds, or a nominal value you declare, carried with the assumption it rests on. If the
  source never stated the temperature the range holds at, the read says `unknown`, not `met`.
- **A bench test with a phantom** fills a model vessel with water or a glycerol mixture in place of blood. The
  phantom's properties come from a record of the phantom itself, at the bench's temperature; whether it stands in
  for blood is your declaration, never the library's claim.
- **A device design review** looks up a material's biocompatibility evidence: the test reports, the standards
  they followed and what they tested. It is information about the evidence, never a claim that the material is
  safe.

Imaging needs more. Schema 0.1 holds the bulk, fluid, magnetic and biocompatibility sections; the acoustic,
radiological, optical and thermal sections come later, and scenes and layered paths are specified but not yet in
the Python package.

- **Photoacoustic imaging through layered tissue** needs, for each layer from the skin to a target vessel,
  optical absorption and scattering at the laser's wavelength, how efficiently absorbed light becomes pressure
  (the Grüneisen parameter), and the speed and attenuation of sound at the transducer's frequency. Blood's
  absorption depends on the wavelength and on how oxygenated the blood is, the Grüneisen parameter changes
  markedly between room and body temperature, and attenuation depends on frequency. A layered path, an ordered
  list of materials and thicknesses, binds each layer to its record.
- **Ultrasound in a robotics simulator built on USD** needs each tissue's sound speed, density and attenuation at
  the probe's frequency, bound to the meshes of the scene. Tuning such as speckle stays with the simulator:
  OpenMaterica holds what describes the substance, not a simulator's settings.
- **C-arm fluoroscopy of a device in a vessel** needs each material's X-ray attenuation across the tube's energy
  spectrum: tissue and bone, blood carrying a contrast agent at its concentration, and the device's own
  materials. Attenuation depends strongly on photon energy and jumps at an element's absorption edge; iodine's
  and neodymium's both fall inside the diagnostic band, so a contrast agent and a magnet each need a spectrum, not
  one number. It is stored against photon energy, or derived from the elemental composition and density the bulk
  section already holds; each ray through the scene crosses its materials as a layered path, and the simulator
  integrates over its own spectrum.

## What it is, and what it is not

It is:

- **a specification of material records:** each value with its test conditions, the specimen it was measured on,
  its source and its uncertainty, or that the source gave none;
- **a reader that checks a record against a simulation's conditions:** it answers `met`, `not_met` or `unknown`,
  with the reasons, and a refusal is a result, not an error;
- **plain JSON:** JSON Schemas, a content hash per record, and conformance cases that an implementation in any
  language can run;
- **specified, not yet in the Python package:**
  - the OpenUSD binding, a main integration target beside plain JSON: records, overlays and layered paths
    expressed in USD scenes, optional, never required;
  - scene documents that bind materials to geometry, from a one-dimensional layered path to a USD scene;
  - the rest of the build check of every value a simulation declares, past the results over records (specimen
    differences, combinations, trainable fields and watches);
  - model parameter sets that name a versioned model family and carry check points, so that a solver that
    evaluates a model in the wrong convention fails loudly instead of silently.

It is not:

- **a solver, a mesher, a segmenter or a renderer:** it computes no physics;
- **a source of anatomy or patient data:** geometry is scene data;
- **a judge of whether a value applies to your use:** whether a record's specimen stands in for yours is your
  declaration;
- **a constitutive-model library to run in a simulation's loop:** the reference implementation the specification
  asks of each model family is there to define and verify it;
- **a database service, or yet a curated library:** the library does not exist yet, and the three records in
  [`examples/`](examples/) are examples;
- **a medical device, or a source of safety or biocompatibility claims** (see
  [Intended use and disclaimers](#intended-use-and-disclaimers)).

## Scope

OpenMaterica describes substances, never systems: not an apparatus or its calibration, not the quantities of
one object (its moment, inertia or mean density), not a drive, a procedure or a simulator's tuning. A value
belongs here if it is a substance's, measured on a test specimen whose shape and size are recorded; a value
of a made object as built (a device, an assembled robot) belongs to its consumer.
Geometry is scene data: OpenMaterica defines how geometry binds to materials and ships small test phantoms,
never anatomy. Other publishers can use the same machinery in their own namespaces, for data OpenMaterica does
not curate. The full statement is in [`docs/regulatory/intended_use.md`](docs/regulatory/intended_use.md).

## Status

Pre-release. Development pre-releases are on [PyPI](https://pypi.org/project/openmaterica/); this is `0.1.0.dev4`.
It holds strict JSON, the content hash, records, the read of a field holding a constant, an interval, a composition,
evidence or a table (with the `extrapolation` acceptance, which under `want: value` gives a table's end value
outside its readable range, at no declared edge and across none), or alternatives read with no pick (the one
alternative left, or no pick among those that stay), the schemas and vocabulary of 0.1, and the build check over
records: `materica.check_build` checks a declaration on its own, refusing each fault with its rule's case and a JSON
pointer, and reads the records it lists into results, each with its status, the reasons nothing covers and its
verdict by the declaration's acceptances. What later steps build, among it picks and overlays, the build's specimen
differences, combinations, trainable fields and watches, and the trust of a label, raises `NotImplementedError`
until then, and the schema 0.1 files may change until 0.1.0 is released. The curated material library does not
exist yet. The architecture concept is in [`design/ARCHITECTURE_DRAFT.md`](design/ARCHITECTURE_DRAFT.md).

## Install

```sh
pip install openmaterica==0.1.0.dev4
```

It needs Python 3.11 or later. To check where a release came from, verify its PyPI attestation (PEP 740), which
names the repository that built it. The repository moved to the OpenMaterica organisation after 0.1.0.dev2: name
`https://github.com/OpenMaterica/OpenMaterica` for every release from 0.1.0.dev3 on, and the former
`https://github.com/Microrobotics-Simulation-Framework/OpenMaterica` for 0.1.0.dev1 and 0.1.0.dev2, which were built
there:

```sh
uvx pypi-attestations verify pypi \
  --repository https://github.com/OpenMaterica/OpenMaterica \
  pypi:openmaterica-0.1.0.dev4-py3-none-any.whl
```

The command prints `OK` for a file built from the repository it names, and fails for any other repository.

## Intended use and disclaimers

> **OpenMaterica is research software.** It is not a medical device as defined by EU MDR (EU 2017/745) or US
> FDA regulations. It has no medical purpose and has not been CE-marked, cleared or approved by any regulatory
> body. When used as a component within regulated medical software, OpenMaterica is SOUP (Software of Unknown
> Provenance) under IEC 62304, and the device manufacturer is responsible for assessing its suitability.
>
> Material values in the OpenMaterica library are taken from cited sources, or are fits to cited data. They
> are not measurements of any particular patient, sample or device; each record states the specimen it was
> measured on, and whether that specimen stands in for yours is your declaration, not the library's.
> Biocompatibility fields are never a safety claim. See
> [`docs/regulatory/intended_use.md`](docs/regulatory/intended_use.md).

## Documentation

| Document | Description |
|---|---|
| [docs/user_guide/quickstart.md](docs/user_guide/quickstart.md) | Quickstart: write a record and read a value from it; this release reads constants, intervals, compositions, evidence and tables, a table's end value under an extrapolation, and alternatives with no pick, not yet picks or overlays |
| [examples/](examples/) | Three example records, cited (water, NdFeB grade N45, human blood plasma): examples, not reviewed library data, not yet fully human-reviewed, and they may change in a later commit |
| [design/ARCHITECTURE_DRAFT.md](design/ARCHITECTURE_DRAFT.md) | Architecture concept: components, data model, model families, geometry and USD binding, library and licensing, MIME and Isaac for Healthcare interfaces |
| [DOCUMENTATION_ARCHITECTURE.md](DOCUMENTATION_ARCHITECTURE.md) | How OpenMaterica is documented and verified, and its SOUP readiness |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Project constraints (including commit sign-off), code rules, identifiers, family and data rules, data attestation, takedown, anomaly lifecycle |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [docs/regulatory/](docs/regulatory/) | Intended use and regulatory boundary |
| [docs/validation/](docs/validation/) | Known anomalies registry |

## License

Code: Apache License 2.0. See [LICENSE](LICENSE). The curated material library will be released
separately, as static archived releases with a DOI, under CC0-1.0.
