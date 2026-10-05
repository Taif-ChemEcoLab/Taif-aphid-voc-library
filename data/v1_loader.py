"""Read-only loader for the provenance-aware VOC·BIO V1 data layer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils.sorting import sort_by_bio_id


V1_DIR = Path(__file__).resolve().parent / "v1"


def _read(name: str, required: tuple[str, ...]) -> pd.DataFrame:
    path = V1_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing V1 dataset: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{name} missing required fields: {sorted(missing)}")
    return frame


PUBLISHED_FEATURES = _read(
    "v1_published_features.csv",
    ("feature_id", "bio_id", "published_annotation_exact", "confidence_symbol"),
)
PUBLISHED_FEATURES = sort_by_bio_id(PUBLISHED_FEATURES)
CHEMICAL_ENTITIES = _read(
    "v1_chemical_entities.csv",
    ("chemical_id", "canonical_name", "structure_available", "publication_facing"),
)
BIOLOGICAL_CONTEXTS = _read(
    "v1_biological_contexts.csv",
    ("context_id", "canonical_species", "host_plant_and_part", "conflict_status"),
)
OBSERVATIONS = _read(
    "v1_observations.csv",
    ("observation_id", "observation_type", "feature_id", "context_id"),
)
FEATURE_CHEMICAL_MAPPING = _read(
    "v1_feature_chemical_mapping.csv",
    ("mapping_id", "feature_id", "chemical_id", "mapping_status"),
)
PROVENANCE = _read("v1_provenance.csv", ("provenance_id", "evidence_class", "relative_path"))
LEGACY_17 = _read("legacy_17_migration.csv", ("legacy_record_id", "legacy_name", "disposition"))
QUARANTINED_FIELDS = _read("quarantined_legacy_fields.csv", ("dataset", "field", "publication_gate"))
UNRESOLVED_RECORDS = _read("unresolved_v1_records.csv", ("record_id", "category", "status"))

PRESENCE_OBSERVATIONS = OBSERVATIONS[OBSERVATIONS["observation_type"] == "published_feature_presence"].copy()
MASS_OBSERVATIONS = OBSERVATIONS[OBSERVATIONS["observation_type"] == "historical_sample_mass"].copy()
STRUCTURED_CHEMICALS = CHEMICAL_ENTITIES[
    (CHEMICAL_ENTITIES["structure_available"] == "true")
    & CHEMICAL_ENTITIES["smiles"].str.strip().ne("")
].copy()
CURATED_CANDIDATE_STRUCTURES = STRUCTURED_CHEMICALS[
    STRUCTURED_CHEMICALS["publication_facing"] == "true"
].copy()
LEGACY_REVIEW_STRUCTURES = STRUCTURED_CHEMICALS[
    STRUCTURED_CHEMICALS["publication_facing"] != "true"
].copy()

CONFIDENCE_ORDER = ("*", "?", "??", "UK")
CONFIDENCE_LABELS = {
    "*": "Authentic-standard supported",
    "?": "Tentative identification, higher library match",
    "??": "Tentative identification, lower library match",
    "UK": "Unknown feature",
}
CONFIDENCE_SOURCE_RANGES = {
    "*": "Authentic-standard supported",
    "?": "Tentative library identification; reported NIST reverse match 990–850",
    "??": "Tentative library identification; reported NIST reverse match 800–700",
    "UK": "Unknown feature; reported reverse match <700",
}
CONFIDENCE_EXPLANATION = (
    "VOC·BIO preserves the identification-confidence categories reported in the published source dataset. "
    "The original notation was *, ?, ?? and UK. These categories distinguish authentic-standard-supported "
    "features from tentative library identifications and unknown features. They should not be interpreted as "
    "equivalent levels of confirmed chemical identity."
)

# Presentation-only derivatives. The immutable source column remains unchanged.
PUBLISHED_FEATURES["published_confidence_notation"] = PUBLISHED_FEATURES["confidence_symbol"]
PUBLISHED_FEATURES["identification_confidence"] = PUBLISHED_FEATURES["confidence_symbol"].map(CONFIDENCE_LABELS)


def feature_context_view() -> pd.DataFrame:
    """Published presence rows joined to feature and context metadata."""
    return (
        PRESENCE_OBSERVATIONS
        .merge(PUBLISHED_FEATURES, on="feature_id", how="left", validate="many_to_one")
        .merge(BIOLOGICAL_CONTEXTS, on="context_id", how="left", validate="many_to_one")
    )


def publication_feature_view() -> pd.DataFrame:
    """Feature table with optional candidate chemical interpretation; no structure inference."""
    mapping = FEATURE_CHEMICAL_MAPPING[["feature_id", "chemical_id", "mapping_status"]]
    chemicals = CHEMICAL_ENTITIES[[
        "chemical_id", "canonical_name", "structure_available", "structural_validation_status",
        "chemical_structure_validation_status", "structure_resolution_class",
        "gcms_identification_confidence", "pubchem_cid", "smiles", "inchi", "inchikey",
        "formula", "molecular_weight", "experimental_peak_identity_status",
    ]]
    return (
        PUBLISHED_FEATURES
        .merge(mapping, on="feature_id", how="left", validate="one_to_one")
        .merge(chemicals, on="chemical_id", how="left", validate="many_to_one")
        .fillna("")
    )
