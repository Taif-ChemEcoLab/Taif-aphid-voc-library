"""Candidate-structure cheminformatics with GC-MS confidence kept separate."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from data.v1_loader import (
    CONFIDENCE_LABELS,
    CURATED_CANDIDATE_STRUCTURES,
    FEATURE_CHEMICAL_MAPPING,
    LEGACY_REVIEW_STRUCTURES,
    PUBLISHED_FEATURES,
)
from utils.chem_utils import compute_descriptors, mol_from_smiles, similarity_matrix, tanimoto_similarity
from utils.sorting import sort_by_bio_id


@lru_cache(maxsize=1)
def _curated_cached() -> pd.DataFrame:
    links = FEATURE_CHEMICAL_MAPPING[["feature_id", "chemical_id", "confidence_symbol", "mapping_status"]]
    features = PUBLISHED_FEATURES[[
        "feature_id", "bio_id", "published_annotation_exact", "published_annotation_display",
        "published_identification_status",
    ]]
    result = (
        CURATED_CANDIDATE_STRUCTURES
        .merge(links, on="chemical_id", how="left", validate="one_to_one", suffixes=("", "_mapping"))
        .merge(features, on="feature_id", how="left", validate="one_to_one")
    )
    result["published_confidence_notation"] = result["confidence_symbol"]
    result["identification_confidence"] = result["confidence_symbol"].map(CONFIDENCE_LABELS)
    result["identity_status_label"] = result["identification_confidence"]
    return sort_by_bio_id(result)


def structured_chemicals(
    confidences: tuple[str, ...] = (), identification_status: str = "All"
) -> pd.DataFrame:
    """Return validated publication-annotation candidate structures only."""
    result = _curated_cached().copy()
    if confidences:
        result = result[result["confidence_symbol"].isin(confidences)]
    if identification_status != "All":
        result = result[result["identity_status_label"] == identification_status]
    return sort_by_bio_id(result)


def legacy_review_structures() -> pd.DataFrame:
    """Return the two isolated legacy records; never feature-map them implicitly."""
    return LEGACY_REVIEW_STRUCTURES.copy()


@lru_cache(maxsize=128)
def descriptor_profile(chemical_id: str) -> dict[str, float | int]:
    rows = CURATED_CANDIDATE_STRUCTURES[CURATED_CANDIDATE_STRUCTURES["chemical_id"] == chemical_id]
    if rows.empty:
        raise KeyError(chemical_id)
    return compute_descriptors(rows.iloc[0]["smiles"])


def similarity_search(
    query_smiles: str,
    threshold: float = 0.0,
    confidences: tuple[str, ...] = (),
    identification_status: str = "All",
) -> pd.DataFrame:
    """Rank validated candidate structures while retaining identification status."""
    if mol_from_smiles(query_smiles) is None:
        raise ValueError("Invalid or out-of-bounds SMILES")
    chemicals = structured_chemicals(confidences, identification_status)
    columns = [
        "chemical_id", "bio_id", "canonical_name", "formula", "smiles", "pubchem_cid",
        "chemical_structure_validation_status", "confidence_symbol", "published_confidence_notation",
        "identification_confidence", "identity_status_label",
        "published_identification_status",
    ]
    result = chemicals[columns].copy()
    result["tanimoto_similarity"] = result["smiles"].map(lambda value: tanimoto_similarity(query_smiles, value))
    return result[result["tanimoto_similarity"] >= float(threshold)].sort_values(
        ["tanimoto_similarity", "bio_id"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)


def structural_similarity_matrix(
    confidences: tuple[str, ...] = (), identification_status: str = "All"
) -> pd.DataFrame:
    chemicals = structured_chemicals(confidences, identification_status)
    labels = (chemicals["bio_id"] + " · " + chemicals["canonical_name"]).tolist()
    return similarity_matrix(chemicals["smiles"].tolist(), labels)


def chemistry_contract() -> dict[str, object]:
    return {
        "candidate_structure_count": len(CURATED_CANDIDATE_STRUCTURES),
        "legacy_review_structure_count": len(LEGACY_REVIEW_STRUCTURES),
        "fingerprint": "Morgan radius 2, 2048 bits",
        "similarity": "Tanimoto coefficient",
        "identity_boundary": "A valid candidate structure does not confirm or upgrade a GC-MS peak identification.",
    }
