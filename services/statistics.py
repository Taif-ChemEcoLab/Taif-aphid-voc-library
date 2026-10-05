"""Descriptive statistics for the published V1 binary presence layer."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import squareform

from data.v1_loader import BIOLOGICAL_CONTEXTS, CONFIDENCE_LABELS, CONFIDENCE_ORDER, PUBLISHED_FEATURES
from services.feature_queries import feature_catalog, occurrence_catalog
from utils.sorting import bio_id_number


METHODS = [
    {"method_id": "confidence_counts", "name": "Identification-confidence composition", "input": "81 published Bio features", "observational_unit": "published GC-MS feature", "calculation": "Count by inherited published category", "interpretation": "Descriptive publication evidence", "status": "available_now"},
    {"method_id": "feature_prevalence", "name": "Feature prevalence", "input": "Binary feature-context presence", "observational_unit": "published GC-MS feature", "calculation": "contexts present / 15 documented contexts", "interpretation": "Documentation prevalence; not biological significance", "status": "available_now"},
    {"method_id": "presence_matrix", "name": "Feature-context matrix", "input": "352 published presence assertions", "observational_unit": "feature-context cell", "calculation": "1=reported present; 0=not listed present", "interpretation": "Published presence profile; not abundance", "status": "available_now"},
    {"method_id": "jaccard", "name": "Jaccard similarity", "input": "Binary context profiles", "observational_unit": "biological/sample context", "calculation": "intersection / union of present features", "interpretation": "Profile similarity; not replication or causality", "status": "available_now"},
    {"method_id": "hierarchical_clustering", "name": "Hierarchical clustering", "input": "Jaccard distance = 1 - similarity", "observational_unit": "biological/sample context", "calculation": "Average-linkage agglomerative clustering", "interpretation": "Exploratory ordering only", "status": "available_now"},
    {"method_id": "rt_distribution", "name": "Published RT distribution", "input": "Published RT decimal candidate", "observational_unit": "published GC-MS feature", "calculation": "Descriptive histogram by confidence", "interpretation": "Feature-location distribution; no chemical confirmation", "status": "available_now"},
    {"method_id": "pca_cap_bray", "name": "PCA/CAP/Bray-Curtis abundance analyses", "input": "Quantitative matrix not reconciled", "observational_unit": "unresolved", "calculation": "Not performed", "interpretation": "Requires additional reconstruction", "status": "not_authorized"},
    {"method_id": "inferential_tests", "name": "Inferential tests and multiple-testing correction", "input": "Independent replicate-level data unavailable", "observational_unit": "unresolved", "calculation": "Not performed", "interpretation": "No valid hypothesis tests available", "status": "not_authorized"},
]


@lru_cache(maxsize=1)
def _presence_matrix_cached() -> pd.DataFrame:
    observations = occurrence_catalog()[["feature_id", "context_id"]].drop_duplicates()
    observations["present"] = 1
    matrix = observations.pivot(index="feature_id", columns="context_id", values="present").fillna(0).astype(int)
    return matrix.reindex(index=PUBLISHED_FEATURES["feature_id"], columns=BIOLOGICAL_CONTEXTS["context_id"], fill_value=0)


def presence_matrix(feature_ids: list[str] | None = None, context_ids: list[str] | None = None, bio_ids: bool = True) -> pd.DataFrame:
    matrix = _presence_matrix_cached().copy()
    if feature_ids is not None:
        matrix = matrix.reindex(index=feature_ids)
    if context_ids is not None:
        matrix = matrix.reindex(columns=context_ids)
    if bio_ids:
        lookup = PUBLISHED_FEATURES.set_index("feature_id")["bio_id"]
        matrix.index = [lookup[value] for value in matrix.index]
        matrix.index.name = "bio_id"
    return matrix


def feature_prevalence() -> pd.DataFrame:
    data = feature_catalog()[["feature_id", "bio_id", "published_annotation_display", "confidence_symbol", "published_confidence_notation", "identification_confidence", "canonical_name", "has_interpretation", "contexts_present", "context_prevalence"]].copy()
    data["context_specific"] = data["contexts_present"] == 1
    data["_bio_number"] = data["bio_id"].map(bio_id_number)
    return data.sort_values(["contexts_present", "_bio_number"], ascending=[False, True], kind="stable").drop(columns="_bio_number").reset_index(drop=True)


def confidence_summary() -> pd.DataFrame:
    result = PUBLISHED_FEATURES["confidence_symbol"].value_counts().reindex(CONFIDENCE_ORDER, fill_value=0).rename_axis("published_confidence_notation").reset_index(name="features")
    result["proportion"] = result["features"] / len(PUBLISHED_FEATURES)
    result["identification_confidence"] = result["published_confidence_notation"].map(CONFIDENCE_LABELS)
    return result


def rt_distribution() -> pd.DataFrame:
    result = PUBLISHED_FEATURES[["feature_id", "bio_id", "published_rt_exact", "published_rt_decimal_candidate", "confidence_symbol", "published_confidence_notation", "identification_confidence", "published_annotation_display"]].copy()
    result["published_rt_numeric"] = pd.to_numeric(result["published_rt_decimal_candidate"], errors="coerce")
    return result


def jaccard_similarity(matrix: pd.DataFrame | None = None) -> pd.DataFrame:
    binary = presence_matrix(bio_ids=False) if matrix is None else matrix.copy()
    contexts = binary.columns.tolist()
    values = binary.T.to_numpy(dtype=bool)
    result = np.zeros((len(contexts), len(contexts)), dtype=float)
    for left in range(len(contexts)):
        for right in range(len(contexts)):
            union = np.logical_or(values[left], values[right]).sum()
            result[left, right] = np.logical_and(values[left], values[right]).sum() / union if union else 1.0
    return pd.DataFrame(result, index=contexts, columns=contexts)


def nearest_contexts(context_id: str, matrix: pd.DataFrame | None = None) -> pd.DataFrame:
    similarities = jaccard_similarity(matrix)
    if context_id not in similarities.index:
        raise KeyError(context_id)
    result = similarities.loc[context_id].drop(index=context_id).sort_values(ascending=False).rename("jaccard_similarity").reset_index().rename(columns={"index": "context_id"})
    return result


def clustered_context_order(matrix: pd.DataFrame | None = None) -> tuple[list[str], np.ndarray | None]:
    similarities = jaccard_similarity(matrix)
    if len(similarities) < 2:
        return similarities.index.tolist(), None
    distance = (1.0 - similarities).clip(0.0, 1.0)
    np.fill_diagonal(distance.values, 0.0)
    condensed = squareform(distance.values, checks=True)
    tree = linkage(condensed, method="average")
    return similarities.index[leaves_list(tree)].tolist(), tree


def methods_dictionary() -> pd.DataFrame:
    return pd.DataFrame(METHODS)


def statistics_contract() -> dict[str, object]:
    matrix = presence_matrix(bio_ids=False)
    return {
        "mode": "published_evidence",
        "row_grain": "published GC-MS feature",
        "matrix_dimensions": [int(matrix.shape[0]), int(matrix.shape[1])],
        "present_cells": int(matrix.to_numpy().sum()),
        "observational_units": "15 documentary biological/sample contexts",
        "excluded": ["PCA", "CAP recomputation", "Bray-Curtis abundance", "hypothesis tests", "p-values", "effect sizes", "multiple-testing correction"],
    }
