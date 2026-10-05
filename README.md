# VOC·BIO Library V1.0

VOC·BIO is a provenance-aware Streamlit application for exploring published aphid headspace GC-MS Bio features, their biological/sample contexts, candidate chemical interpretations, defensible molecular structures, and frozen exploratory odorant-binding-protein docking results.

The public application reads curated and frozen assets. It does not reconstruct the source study, prepare molecules, or run docking.

## Scientific evidence model

VOC·BIO keeps three evidence levels distinct:

1. **81 published GC-MS Bio features** across **15 biological/sample contexts**.
2. **70 named candidate chemical interpretations** linked through explicit mappings.
3. **55 defensible molecular structures** eligible for molecular descriptors and structural-similarity analysis.

Unresolved records remain unresolved. A candidate name or structure does not upgrade the published GC-MS feature to a confirmed chemical identity.

### Identification confidence

The application preserves the categories reported in the published source dataset:

- **11 Authentic-standard supported**
- **32 Tentative identification, higher library match**
- **27 Tentative identification, lower library match**
- **11 Unknown features**

Original notation (`*`, `?`, `??`, `UK`) is retained as secondary provenance. Descriptive labels are primary throughout the interface. The categories were inherited from the source study and should not be interpreted as equivalent levels of confirmed identity.

## Application capabilities

- Overview of published evidence, contexts, and candidate structures.
- Searchable published-feature and evidence explorers.
- Biological/sample context views and descriptive published-feature statistics.
- Molecular descriptors for records with defensible structures only.
- Tanimoto structural-similarity exploration for valid structures only.
- Feature–context evidence network.
- Frozen multi-receptor docking explorer with score, variability, validation, provenance, and representative-pose views.
- Deterministic Research Team Assistant that answers from curated V1 records and labels its evidence scope.

Structural similarity is chemical-structure comparison, not evidence of bioactivity, attraction, repellency, receptor activation, or ecological function. The Research Team Assistant does not call an external language model; no OpenAI API or credential is required.

## Frozen exploratory OBP docking

The docking layer contains:

- **MvicOBP3**, PDB **4Z39**
- **NribOBP3**, PDB **4Z45**
- **20 VOC candidates**
- **40 receptor–ligand pairs**
- **5 predefined seeds per pair**
- **200 completed docking runs**
- **2,000 retained poses**

Docking scores are exploratory computational predictions only. They are not measured binding affinities, Ki values, receptor activation measurements, attraction/repellency evidence, ecological-function assignments, or pest-control efficacy.

The public runtime does not require AutoDock Vina, PDBFixer, OpenMM, Meeko, or Open Babel.

## Installation and startup

Python 3.10 is used for the documented validation environment.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m streamlit run app.py
```

On macOS/Linux, activate or invoke the virtual environment using the platform-appropriate `bin/` path. The Streamlit entry point is `app.py`.

## Repository structure

```text
data/v1/          Curated V1 evidence tables and explicit mappings
data/docking/     Frozen docking tables and protocol used by the app
docking_v1/       Two display receptors and six representative poses
modules/          Streamlit page implementations
services/         Read-only evidence, chemistry, and docking services
utils/            Display, sorting, and bounded cheminformatics helpers
checksums/        Runtime scientific-asset hashes and relocation record
tests/            Scientific-contract and route/integration checks
scripts/          Checksum and repository verification utilities
```

Required scientific files are loaded through repository-relative paths and validated for expected schemas and identifiers. Missing files produce explicit errors; demonstration data are not substituted.

## Reproducibility and verification

```bash
python tests/test_deployment_integrity.py
python tests/test_phase5d4.py
python scripts/generate_checksums.py --check
```

The public package contains the curated runtime subset. Primary publications, Supplementary Information, historical workbooks, complete preparation records, and full scientific archives remain separate controlled evidence. See `REPRODUCIBILITY.md` and `data/v1/v1_provenance.csv`.

## Citation

Software citation metadata are provided in `CITATION.cff`:

- Taghreed Alsufyani
- Taufia Hussain
- Noura J. Alotaibi

### Primary source publication

Alotaibi, N. J., Alsufyani, T., M’sakni, N. H., Almalki, M. A., Alghamdi, E. M., & Spiteller, D. (2023). “Rapid Identification of Aphid Species by Headspace GC-MS and Discriminant Analysis.” *Insects*, 14, 589. https://doi.org/10.3390/insects14070589

## Licensing

Original VOC·BIO application code is licensed under the MIT License. Scientific data and third-party content are not covered by that software license. See `LICENSE` and `DATA_LICENSE.md` for scope and attribution.

## Authors

- Taghreed Alsufyani
- Taufia Hussain
- Noura J. Alotaibi
