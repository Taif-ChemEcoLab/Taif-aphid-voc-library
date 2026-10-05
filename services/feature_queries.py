"""Feature-first V1 query service with explicit row-grain preservation."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from data.v1_loader import (
    BIOLOGICAL_CONTEXTS,
    CHEMICAL_ENTITIES,
    FEATURE_CHEMICAL_MAPPING,
    PUBLISHED_FEATURES,
    feature_context_view,
    publication_feature_view,
)
from utils.sorting import sort_by_bio_id


def _truth(value: object) -> bool:
    return str(value).strip().lower() == "true"


@lru_cache(maxsize=1)
def _feature_catalog_cached() -> pd.DataFrame:
    catalog = publication_feature_view().copy()
    occurrences = feature_context_view()
    prevalence = (
        occurrences.groupby("feature_id", as_index=False)["context_id"]
        .nunique()
        .rename(columns={"context_id": "contexts_present"})
    )
    catalog = catalog.merge(prevalence, on="feature_id", how="left", validate="one_to_one")
    catalog["contexts_present"] = catalog["contexts_present"].fillna(0).astype(int)
    catalog["context_prevalence"] = catalog["contexts_present"] / len(BIOLOGICAL_CONTEXTS)
    catalog["has_interpretation"] = catalog["chemical_id"].astype(str).str.strip().ne("")
    catalog["has_structure"] = catalog["structure_available"].map(_truth)
    catalog["published_rt_numeric"] = pd.to_numeric(
        catalog["published_rt_decimal_candidate"], errors="coerce"
    )
    return sort_by_bio_id(catalog)


def feature_catalog() -> pd.DataFrame:
    """One row per immutable published feature with derived descriptive fields."""
    return _feature_catalog_cached().copy()


@lru_cache(maxsize=1)
def _occurrences_cached() -> pd.DataFrame:
    return feature_context_view().copy()


def occurrence_catalog() -> pd.DataFrame:
    """One row per published feature-context presence assertion."""
    return _occurrences_cached().copy()


def filter_features(
    *,
    confidences: tuple[str, ...] = (),
    query: str = "",
    species: str = "All",
    host: str = "All",
    environment: str = "All",
    mapping_status: str = "All",
    structure_status: str = "All",
    min_contexts: int = 0,
    sort_by: str = "Bio ID",
    ascending: bool = True,
) -> pd.DataFrame:
    """Filter at context grain, then return unique feature rows."""
    result = feature_catalog()
    occurrences = occurrence_catalog()
    context_filter_used = species != "All" or host != "All" or environment != "All"
    if species != "All":
        occurrences = occurrences[occurrences["canonical_species"] == species]
    if host != "All":
        occurrences = occurrences[occurrences["host_plant_and_part"] == host]
    if environment != "All":
        occurrences = occurrences[occurrences["collection_environment"] == environment]
    if context_filter_used:
        result = result[result["feature_id"].isin(occurrences["feature_id"].unique())]
    if confidences:
        result = result[result["confidence_symbol"].isin(confidences)]
    if query.strip():
        token = query.strip()
        fields = (
            result["bio_id"].str.contains(token, case=False, regex=False, na=False)
            | result["published_annotation_exact"].str.contains(token, case=False, regex=False, na=False)
            | result["historical_annotation_candidate"].str.contains(token, case=False, regex=False, na=False)
            | result["canonical_name"].str.contains(token, case=False, regex=False, na=False)
        )
        result = result[fields]
    if mapping_status != "All":
        result = result[result["mapping_status"] == mapping_status]
    if structure_status == "Available":
        result = result[result["has_structure"]]
    elif structure_status == "Not available":
        result = result[~result["has_structure"]]
    result = result[result["contexts_present"] >= int(min_contexts)]
    sort_columns = {
        "Bio ID": "bio_id",
        "Retention time": "published_rt_numeric",
        "Annotation": "published_annotation_exact",
        "Contexts present": "contexts_present",
        "Confidence": "confidence_symbol",
    }
    sort_column = sort_columns.get(sort_by, "bio_id")
    if sort_column == "bio_id":
        return sort_by_bio_id(result, "bio_id", ascending=ascending)
    return result.sort_values(sort_column, ascending=ascending, na_position="last", kind="stable").reset_index(drop=True)


def feature_evidence(feature_id: str) -> dict[str, pd.DataFrame | pd.Series]:
    """Return a feature row and its documented presence/interpretation evidence."""
    rows = feature_catalog().query("feature_id == @feature_id")
    if rows.empty:
        raise KeyError(feature_id)
    occurrences = occurrence_catalog().query("feature_id == @feature_id").copy()
    mapping = FEATURE_CHEMICAL_MAPPING.query("feature_id == @feature_id").copy()
    chemicals = CHEMICAL_ENTITIES[CHEMICAL_ENTITIES["chemical_id"].isin(mapping["chemical_id"])].copy()
    return {"feature": rows.iloc[0], "occurrences": occurrences, "mapping": mapping, "chemicals": chemicals}


def filter_options() -> dict[str, list[str]]:
    occurrences = occurrence_catalog()
    catalog = feature_catalog()
    return {
        "species": sorted(value for value in occurrences["canonical_species"].unique() if value),
        "hosts": sorted(value for value in occurrences["host_plant_and_part"].unique() if value),
        "environments": sorted(value for value in occurrences["collection_environment"].unique() if value),
        "mapping_status": sorted(value for value in catalog["mapping_status"].unique() if value),
    }


def catalog_contract() -> dict[str, object]:
    return {
        "row_grain": "one published GC-MS feature",
        "source": "published Supplementary Table S2 with V1 interpretation/context joins",
        "feature_count": len(PUBLISHED_FEATURES),
        "context_count": len(BIOLOGICAL_CONTEXTS),
        "interpretation_count": int(feature_catalog()["has_interpretation"].sum()),
        "warnings": [
            "A chemical interpretation is not automatically a confirmed chemical identity.",
            "Feature-context presence is not abundance, behavior, or receptor binding.",
        ],
    }
