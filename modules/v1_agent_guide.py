"""Research Team Assistant backed exclusively by provenance-aware V1 services."""

import streamlit as st

from services.research_assistant import answer_question, suggested_questions
from utils.display import researcher_table


def render():
    st.markdown("<div class='section-head'>Research Team Assistant</div>", unsafe_allow_html=True)
    st.info(
        "This local assistant retrieves curated V1 evidence and labels its evidence layer. "
        "It does not generate missing relationships or promote tentative identities."
    )
    mode = st.radio("Input", ["Guided question", "Ask in your own words"], horizontal=True)
    if mode == "Guided question":
        question = st.selectbox("Question", suggested_questions())
    else:
        question = st.text_input(
            "Evidence question",
            placeholder="Try: Which contexts contain Bio12?",
            max_chars=300,
        )

    if not question.strip():
        st.caption("Enter a question to retrieve a source-scoped answer.")
        return

    result = answer_question(question)
    st.subheader("Evidence-scoped answer")
    st.write(result.answer)
    c1, c2 = st.columns(2)
    c1.markdown(f"**Evidence layer:** {result.evidence_layer}")
    c2.markdown(f"**Source:** {result.source}")
    st.warning(result.caution)
    if not result.records.empty:
        with st.expander(f"Supporting records ({len(result.records)})", expanded=True):
            records = researcher_table(
                result.records,
                {
                    "canonical_species": "Aphid species",
                    "host_plant_and_part": "Host plant / part",
                    "canonical_name": "Candidate chemical",
                    "source_bio_ids": "Source Bio feature",
                    "gcms_identification_confidence": "Identification confidence",
                    "identification_confidence": "Identification confidence",
                    "published_confidence_notation": "Original published notation",
                    "source_study_definition": "Source-study definition",
                    "category": "Issue type",
                    "record": "Evidence gap",
                    "status": "Status",
                },
                minimum_supported_fraction=0.5,
            )
            if not records.empty:
                st.dataframe(records, use_container_width=True, hide_index=True)

    with st.expander("Assistant evidence policy"):
        st.markdown(
            "- Published evidence is quoted/described without silent canonical rewriting.\n"
            "- Historical reconstruction is labeled separately from publication evidence.\n"
            "- Chemical interpretation does not establish an experimentally verified peak identity.\n"
            "- Unresolved evidence remains unresolved.\n"
            "- GC-MS presence is never translated into behavioral or receptor-binding activity."
        )
