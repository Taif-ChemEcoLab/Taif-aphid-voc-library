"""Concise feature evidence with forensic details kept secondary."""

import streamlit as st

from data.v1_loader import CONFIDENCE_EXPLANATION, CONFIDENCE_LABELS, QUARANTINED_FIELDS, UNRESOLVED_RECORDS
from services.feature_queries import feature_catalog, feature_evidence
from utils.display import researcher_table


def render():
    st.markdown("<div class='section-head'>Evidence Explorer</div>", unsafe_allow_html=True)
    st.info(CONFIDENCE_EXPLANATION)
    st.caption("Trace a Bio feature through published context and candidate chemical interpretation. Detection is not evidence of behavioral or receptor activity.")
    catalog = feature_catalog()
    selected = st.selectbox(
        "Published feature", catalog["feature_id"].tolist(),
        format_func=lambda value: f"{catalog.loc[catalog['feature_id'] == value, 'bio_id'].iloc[0]} · {catalog.loc[catalog['feature_id'] == value, 'published_annotation_display'].iloc[0]}",
    )
    packet = feature_evidence(selected)
    feature = packet["feature"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bio ID", feature["bio_id"])
    m2.metric("Retention time", feature["published_rt_exact"])
    m3.metric("Identification confidence", CONFIDENCE_LABELS[feature["confidence_symbol"]], help=f"Original published notation: {feature['published_confidence_notation']}")
    m4.metric("Contexts present", int(feature["contexts_present"]))
    published, contexts, interpretation, limitations, technical = st.tabs(["Published evidence", "Contexts", "Candidate structure", "Interpretation limits", "Technical provenance"])
    with published:
        st.subheader(feature["published_annotation_display"])
        st.markdown(f"**Identification confidence:** {feature['identification_confidence']}")
        st.markdown(f"**Original published notation:** {feature['published_confidence_notation']}")
        st.write(feature["confidence_interpretation"])
        st.caption("Source: Alotaibi et al. 2023, Supplementary Table S2.")
    with contexts:
        table = researcher_table(packet["occurrences"], {"common_sample_name": "Sample", "canonical_species": "Aphid species", "host_plant_and_part": "Host plant / part", "collection_locality": "Locality"}, always_keep=("canonical_species", "host_plant_and_part"), minimum_supported_fraction=0.5)
        st.dataframe(table, use_container_width=True, hide_index=True)
    with interpretation:
        if packet["chemicals"].empty:
            st.info("No chemical interpretation record is assigned.")
        else:
            chemical = packet["chemicals"].iloc[0]
            values = [
                ("Candidate chemical", chemical["canonical_name"]),
                ("Structure available", "Yes" if chemical["structure_available"] == "true" else "No"),
                ("Formula", chemical["formula"]),
                ("Molecular weight", chemical["molecular_weight"]),
                ("PubChem CID", chemical["pubchem_cid"]),
                ("Structure validation", chemical["chemical_structure_validation_status"]),
            ]
            st.dataframe([{"Field": key, "Value": value} for key, value in values if str(value).strip()], use_container_width=True, hide_index=True)
            st.warning("A candidate molecular structure does not independently confirm the GC-MS feature and does not change its published confidence.")
    with limitations:
        st.markdown("- Feature presence is documentary, not quantitative abundance.\n- No behavioral assay evidence is present.\n- No receptor-binding conclusion is supported.\n- Unresolved mappings remain unresolved.")
    with technical:
        technical_values = {
            "Historical annotation candidate": feature["historical_annotation_candidate"],
            "Historical RT candidate": feature["historical_rt_candidate"],
            "Mapping confidence": feature["mapping_confidence"],
            "Conflict notes": feature["conflict_notes"],
            "Annotation correction": feature["annotation_correction_status"],
            "Correction evidence": feature["annotation_correction_evidence"],
        }
        rows = [{"Field": key, "Value": value} for key, value in technical_values.items() if str(value).strip()]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        with st.expander("Open unresolved evidence register"):
            st.dataframe(UNRESOLVED_RECORDS, use_container_width=True, hide_index=True)
        with st.expander("Open quarantined field register"):
            st.dataframe(QUARANTINED_FIELDS, use_container_width=True, hide_index=True)
