"""Natural-sorted feature library with concise evidence drill-down."""

import streamlit as st

from data.v1_loader import CONFIDENCE_EXPLANATION, CONFIDENCE_LABELS
from services.feature_queries import feature_evidence, filter_features, filter_options
from utils.display import researcher_table


CONFIDENCE_ORDER = ["*", "?", "??", "UK"]


def _detail(feature_id: str) -> None:
    packet = feature_evidence(feature_id)
    row = packet["feature"]
    st.markdown(f"### {row['bio_id']} — {row['published_annotation_display']}")
    badges = st.columns(4)
    badges[0].metric("Retention time", row["published_rt_exact"])
    badges[1].metric("Identification confidence", CONFIDENCE_LABELS[row["confidence_symbol"]])
    badges[2].metric("Contexts present", int(row["contexts_present"]))
    badges[3].metric("Candidate structure", "Available" if row["has_structure"] else "Not available")
    st.caption(f"Original published notation: {row['published_confidence_notation']}")
    published, contexts, interpretation, technical = st.tabs(["Published evidence", "Contexts", "Chemical interpretation", "Technical provenance"])
    with published:
        st.write(row["confidence_interpretation"])
        st.caption("Source: Alotaibi et al. 2023, Supplementary Table S2")
    with contexts:
        table = researcher_table(
            packet["occurrences"],
            {"canonical_species": "Aphid species", "host_plant_and_part": "Host plant / part", "collection_locality": "Collection locality", "collection_environment": "Collection environment"},
            always_keep=("canonical_species", "host_plant_and_part"), minimum_supported_fraction=0.5,
        )
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.caption("Rows are documentary presence contexts, not independent biological replicates.")
    with interpretation:
        if packet["mapping"].empty:
            st.info("No chemical interpretation is assigned. This remains a valid published GC-MS feature.")
        elif packet["chemicals"].empty:
            st.info("The publication provides an annotation, but no chemical entity record is available.")
        else:
            chemical = packet["chemicals"].iloc[0]
            details = {
                "Candidate chemical": chemical["canonical_name"],
                "Candidate structure": "Available" if chemical["structure_available"] == "true" else "Not available",
                "Formula": chemical["formula"],
                "PubChem CID": chemical["pubchem_cid"],
                "Structure validation": chemical["chemical_structure_validation_status"],
                "GC-MS identity status": CONFIDENCE_LABELS[row["confidence_symbol"]],
            }
            shown = [{"Field": key, "Value": value} for key, value in details.items() if str(value).strip()]
            st.dataframe(shown, use_container_width=True, hide_index=True)
            st.warning("The candidate structure represents the named annotation; it is not independent confirmation of the GC-MS peak identity.")
    with technical:
        technical_fields = {
            "Historical annotation candidate": row["historical_annotation_candidate"],
            "Historical RT candidate": row["historical_rt_candidate"],
            "Mapping confidence": row["mapping_confidence"],
            "Conflict notes": row["conflict_notes"],
            "Annotation correction status": row["annotation_correction_status"],
            "Annotation correction evidence": row["annotation_correction_evidence"],
        }
        supported = [{"Field": key, "Value": value} for key, value in technical_fields.items() if str(value).strip()]
        if supported:
            st.dataframe(supported, use_container_width=True, hide_index=True)


def render():
    st.markdown("<div class='section-head'>Published GC-MS Feature Library</div>", unsafe_allow_html=True)
    st.info(CONFIDENCE_EXPLANATION)
    st.info("Bio features are the primary records. Candidate structures and contexts are linked evidence layers and do not replace published confidence.")
    options = filter_options()
    with st.expander("Search and filter", expanded=True):
        row1 = st.columns([2, 2, 2])
        query = row1[0].text_input("Search Bio ID or annotation", max_chars=120)
        confidence = row1[1].multiselect("Identification confidence", CONFIDENCE_ORDER, default=CONFIDENCE_ORDER, format_func=lambda value: CONFIDENCE_LABELS[value])
        min_contexts = row1[2].slider("Minimum documented contexts", 0, 15, 0)
        row2 = st.columns(4)
        species = row2[0].selectbox("Aphid species", ["All"] + options["species"])
        host = row2[1].selectbox("Host / plant part", ["All"] + options["hosts"])
        structure = row2[2].selectbox("Candidate structure", ["All", "Available", "Not available"])
        sort_by = row2[3].selectbox("Sort by", ["Bio ID", "Retention time", "Annotation", "Contexts present", "Confidence"])
        ascending = st.toggle("Ascending", value=True)
    data = filter_features(
        confidences=tuple(confidence), query=query, species=species, host=host, structure_status=structure,
        min_contexts=min_contexts, sort_by=sort_by, ascending=ascending,
    )
    st.caption(f"{len(data)} of 81 published features. Bio-ID ordering uses the numeric component.")
    if data.empty:
        st.warning("No features match the current filters.")
        return
    table_source = data.copy()
    table = researcher_table(
        table_source,
        {"bio_id": "Bio ID", "published_rt_exact": "Retention time", "published_annotation_display": "Published annotation", "identification_confidence": "Identification confidence", "published_confidence_notation": "Original published notation", "contexts_present": "Contexts present", "canonical_name": "Candidate chemical", "has_structure": "Curated structure"},
        always_keep=("bio_id", "published_rt_exact", "published_annotation_display", "identification_confidence", "published_confidence_notation", "contexts_present"),
    )
    st.dataframe(table, use_container_width=True, hide_index=True, height=500)
    st.download_button("Download filtered feature view", data.to_csv(index=False), "voc_bio_v1_published_features_filtered.csv", "text/csv", use_container_width=True)
    selected = st.selectbox(
        "Inspect feature evidence", data["feature_id"].tolist(),
        format_func=lambda value: f"{data.loc[data['feature_id'] == value, 'bio_id'].iloc[0]} · {data.loc[data['feature_id'] == value, 'published_annotation_display'].iloc[0]}",
    )
    _detail(selected)
