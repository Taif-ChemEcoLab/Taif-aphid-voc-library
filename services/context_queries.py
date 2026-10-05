"""Biological-context queries and publication presence summaries."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from data.v1_loader import BIOLOGICAL_CONTEXTS, MASS_OBSERVATIONS
from services.feature_queries import occurrence_catalog


@lru_cache(maxsize=1)
def _context_summary_cached() -> pd.DataFrame:
    counts = occurrence_catalog().groupby("context_id", as_index=False)["feature_id"].nunique().rename(columns={"feature_id": "published_features_present"})
    return BIOLOGICAL_CONTEXTS.merge(counts, on="context_id", how="left", validate="one_to_one").fillna({"published_features_present": 0})


def context_summary() -> pd.DataFrame:
    result = _context_summary_cached().copy()
    result["published_features_present"] = result["published_features_present"].astype(int)
    return result


def filter_contexts(species: str = "All", host: str = "All", environment: str = "All", query: str = "") -> pd.DataFrame:
    result = context_summary()
    if species != "All":
        result = result[result["canonical_species"] == species]
    if host != "All":
        result = result[result["host_plant_and_part"] == host]
    if environment != "All":
        result = result[result["collection_environment"] == environment]
    if query.strip():
        token = query.strip()
        mask = pd.Series(False, index=result.index)
        for column in ("context_id", "common_sample_name", "canonical_species", "historical_species_label", "host_plant_and_part", "collection_locality"):
            mask |= result[column].str.contains(token, case=False, regex=False, na=False)
        result = result[mask]
    return result.reset_index(drop=True)


def context_options() -> dict[str, list[str]]:
    data = context_summary()
    return {
        "species": sorted(value for value in data["canonical_species"].unique() if value),
        "hosts": sorted(value for value in data["host_plant_and_part"].unique() if value),
        "environments": sorted(value for value in data["collection_environment"].unique() if value),
    }


def mass_metadata() -> pd.DataFrame:
    """Historical mass rows; no context join is inferred."""
    return MASS_OBSERVATIONS.copy()


def species_host_summary() -> pd.DataFrame:
    """One row per documented species-host combination with context/feature counts."""
    contexts = context_summary()
    occurrences = occurrence_catalog()[["context_id", "feature_id"]]
    joined = contexts.merge(occurrences, on="context_id", how="left", validate="one_to_many")
    return (
        joined.groupby(["canonical_species", "host_plant_and_part"], as_index=False)
        .agg(contexts=("context_id", "nunique"), published_features=("feature_id", "nunique"))
        .sort_values(["canonical_species", "host_plant_and_part"])
        .reset_index(drop=True)
    )


def context_feature_long() -> pd.DataFrame:
    """Published presence joined to context descriptors, one row per present cell."""
    return occurrence_catalog().copy()
