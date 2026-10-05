"""Researcher-facing context views with empty metadata suppressed."""

import plotly.express as px
import streamlit as st

from services.context_queries import context_feature_long, context_options, filter_contexts, mass_metadata, species_host_summary
from utils.display import researcher_table
from utils.sorting import sort_by_bio_id


def render():
    st.markdown("<div class='section-head'>Biological and Sample Contexts</div>", unsafe_allow_html=True)
    st.info("Contexts document sample, aphid, host, and collection information from Supplementary Table S1. Counts are not biological-replicate prevalence.")
    options = context_options()
    filters = st.columns([2, 2, 2, 3])
    species = filters[0].selectbox("Aphid species", ["All"] + options["species"])
    host = filters[1].selectbox("Host / plant part", ["All"] + options["hosts"])
    environment = filters[2].selectbox("Collection environment", ["All"] + options["environments"])
    query = filters[3].text_input("Search species, host, locality, or sample", max_chars=120)
    data = filter_contexts(species, host, environment, query)
    catalog, profiles, presence, mass = st.tabs(["Context catalog", "Species-host profiles", "Published feature presence", "Historical mass metadata"])
    with catalog:
        metrics = st.columns(4)
        metrics[0].metric("Documented contexts", len(data))
        metrics[1].metric("Aphid species", data["canonical_species"].nunique())
        metrics[2].metric("Host plants / parts", data["host_plant_and_part"].nunique())
        metrics[3].metric("Feature presence records", int(data["published_features_present"].sum()))
        display = researcher_table(
            data,
            {
                "common_sample_name": "Sample", "canonical_species": "Aphid species", "genbank_accession": "GenBank accession",
                "host_plant_and_part": "Host plant / part", "collection_locality": "Collection locality", "coordinates": "Coordinates",
                "collection_date": "Collection date", "collection_environment": "Collection environment",
                "published_features_present": "Published features present",
            },
            always_keep=("common_sample_name", "canonical_species", "host_plant_and_part", "published_features_present"),
            minimum_supported_fraction=0.5,
        )
        st.dataframe(display, use_container_width=True, hide_index=True, height=480)
        st.download_button("Download filtered contexts", data.to_csv(index=False), "voc_bio_v1_biological_contexts_filtered.csv", "text/csv")
        st.caption("Source: Alotaibi et al. 2023, Supplementary Table S1.")
        if data["conflict_status"].astype(str).str.contains("conflict", case=False, na=False).any():
            st.warning("A conflicted historical context assignment remains explicit and is not automatically merged.")
    with profiles:
        summary = species_host_summary()
        if species != "All":
            summary = summary[summary["canonical_species"] == species]
        if host != "All":
            summary = summary[summary["host_plant_and_part"] == host]
        left, right = st.columns(2)
        with left:
            counts = data.groupby("canonical_species", as_index=False).agg(Contexts=("context_id", "nunique"))
            st.plotly_chart(px.bar(counts, x="Contexts", y="canonical_species", orientation="h", title="Documented contexts by species", labels={"canonical_species": "Aphid species"}), use_container_width=True)
        with right:
            counts = data.groupby("host_plant_and_part", as_index=False).agg(Contexts=("context_id", "nunique"))
            st.plotly_chart(px.bar(counts, x="Contexts", y="host_plant_and_part", orientation="h", title="Documented contexts by host", labels={"host_plant_and_part": "Host / part"}), use_container_width=True)
        st.dataframe(summary.rename(columns={"canonical_species": "Aphid species", "host_plant_and_part": "Host plant / part", "contexts": "Contexts", "published_features": "Published features"}), use_container_width=True, hide_index=True)
    with presence:
        long = context_feature_long()
        long = long[long["context_id"].isin(data["context_id"])]
        long = sort_by_bio_id(long)
        display = researcher_table(
            long,
            {"canonical_species": "Aphid species", "host_plant_and_part": "Host plant / part", "bio_id": "Bio ID", "published_annotation_display": "Published annotation", "identification_confidence": "Identification confidence", "published_confidence_notation": "Original published notation"},
            always_keep=("canonical_species", "host_plant_and_part", "bio_id", "published_annotation_display", "identification_confidence", "published_confidence_notation"),
        )
        st.dataframe(display, use_container_width=True, hide_index=True, height=470)
        st.caption(f"{len(long)} documentary presence records in the current view. Absence from this table is not behavioral inactivity.")
    with mass:
        masses = mass_metadata()
        st.caption("Historical sample-associated mass metadata are not joined to the publication contexts. Exact weighed material and downstream propagation remain unresolved.")
        display = researcher_table(
            masses,
            {"sample_identifier": "Historical sample", "measured_mass_value": "Recorded mass", "mass_units": "Unit", "mass_original_token": "Source value", "weighed_material": "Weighed material"},
            always_keep=("sample_identifier", "measured_mass_value", "mass_units"), minimum_supported_fraction=0.5,
        )
        st.dataframe(display, use_container_width=True, hide_index=True, height=470)
