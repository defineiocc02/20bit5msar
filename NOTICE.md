# Third-Party Notices

This repository is a research engineering archive. It contains third-party material
that is **not** covered by any license the project owner may add later.

## 1. MathWorks Simulink Agentic Toolkit (SATK)

- Location: `dependencies/toolkit/`
- Version: `2026.10.b` (see `dependencies/toolkit/VERSION`)
- Copyright: 2025–2026, The MathWorks, Inc. All rights reserved.
- License: bundled at `dependencies/toolkit/LICENSE.md` — a BSD-3-Clause variant whose
  third condition states that the software and all modifications/derivatives are
  licensed **solely for use in conjunction with MathWorks products and service offerings**.
- Upstream: <https://github.com/matlab/simulink-agentic-toolkit>
- Citation metadata: `dependencies/toolkit/CITATION.cff`

This toolkit is vendored because `SAR20.m` validates SATK functions (`model_read`,
`model_edit`, `library.settingsLookup`, …) before `apply`. It is a runtime dependency,
not project-owned code. Its own `LICENSE.md`, `CITATION.cff`, `README.md` and
`CONTRIBUTING.md` are preserved verbatim inside that directory.

## 2. Reference literature (PDFs)

- Location: `docs/PAPERS/` — 27 PDF files, ~59 MB
- Contents: IEEE / ISSCC / CICC conference and journal papers, vendor datasheets
  (Analog Devices, Texas Instruments), and US patent documents.
- Copyright remains with the respective authors, publishers and assignees.
- These files are included **for research citation and traceability only**, at the
  repository owner's explicit direction to keep the archive complete. They are not
  offered under any open license, and no sublicense is granted.
- A complete list with relative paths, original source paths and SHA-256 digests is
  in [`docs/PAPERS/INDEX.md`](docs/PAPERS/INDEX.md); machine-readable provenance is
  in [`docs/REFERENCE_INDEX.json`](docs/REFERENCE_INDEX.json).

> If you are a rights holder and want a document removed, please open an issue at
> <https://github.com/defineiocc02/20bit5msar/issues>. The removal is straightforward:
> the PDFs are not referenced by any executable path, only by the index and by prose
> in `docs/CAAZ_ADI.md` / `docs/ENGINEERING_ANALYSIS.md`.

## 3. Bundled Python environment

`dependencies/analysis_env/` is a locally generated Python virtual environment
(h5py / numpy / scipy / matplotlib) and is **excluded** from the repository by
`.gitignore`. It is reproducible from the environment's own requirements; no
third-party Python code is committed. To recreate:

```bash
python3 -m venv dependencies/analysis_env
dependencies/analysis_env/bin/pip install h5py numpy scipy matplotlib
```

## 4. Project code and documents

No open-source license has been declared for the project's own MATLAB source,
Simulink model, analysis scripts or documents. Until a `LICENSE` file is added,
do not assume permission for redistribution or commercial use.

Model parameters derived from published papers are explicitly labeled as
**engineering assumptions** in `config/adc_parameters.m` and
`config/normal_parameters.m`; they are not PDK data and not disclosed silicon values.

## 5. Status disclaimer

This repository is a behavioral modeling archive. It contains no fabricated
measurements, no power/area results, no PDK or signoff data, and does not claim
reproduction of any referenced paper. See
[`docs/ENGINEERING_ANALYSIS.md`](docs/ENGINEERING_ANALYSIS.md) for the evidence
hierarchy and the list of claims that must not be made.
