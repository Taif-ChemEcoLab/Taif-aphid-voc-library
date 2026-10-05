# Reproducibility and archive boundaries

## Public runtime package

The repository contains only the curated V1 tables and frozen docking assets required to render the application. It performs no molecular preparation or production docking and does not rebuild the upstream scientific evidence layers.

- `data/v1/` contains the published-feature, context, mapping, chemical, unresolved-record, quarantine, and provenance tables.
- `data/docking/` contains byte-preserved frozen docking tables and protocol records consumed by the public interface.
- `docking_v1/` contains the two receptor display files and six selected representative poses needed by the pose viewer.
- `checksums/docking_asset_relocation.csv` records the source-to-public path mapping and original hashes for relocated docking files.
- `checksums/runtime_scientific_assets.sha256` verifies the cleaned runtime scientific subset.

## Verification

Use Python 3.10 with the declared deployment requirements:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pip check
.venv/Scripts/python tests/test_deployment_integrity.py
.venv/Scripts/python tests/test_phase5d4.py
.venv/Scripts/python scripts/generate_checksums.py --check
```

Do not change expected values to silence a regression. Investigate any count, schema, stable-ID, byte-hash, or scientific-contract mismatch.

## Controlled scientific archive

The complete evidence and reproducibility archive is intentionally separate from the public Streamlit runtime. It should retain the primary article and Supplementary Information, historical workbooks, collaborator clarifications, complete audit manifests, molecular-preparation records, full receptor/ligand preparations, run logs, all poses, validation systems, and environment records. `data/v1/v1_provenance.csv` records expected evidence roles and source hashes.

The authoritative protected Phase 5 hashes remain properties of that controlled archive. Public path consolidation does not alter those source files; byte identity for the relocated runtime subset is recorded separately. Scientific corrections should be versioned, documented, tested, and reviewed independently from presentation or dependency maintenance.
