"""Primary references and dataset-source explanation."""

import streamlit as st


DOI = "10.3390/insects14070589"
DOI_URL = f"https://doi.org/{DOI}"
FULL_CITATION = (
    "Alotaibi, N. J., Alsufyani, T., M’sakni, N. H., Almalki, M. A., "
    "Alghamdi, E. M., & Spiteller, D. (2023). Rapid Identification of Aphid "
    "Species by Headspace GC-MS and Discriminant Analysis. Insects, 14, 589."
)


def source_summary() -> None:
    st.markdown("#### Primary experimental source")
    st.write(FULL_CITATION)
    c1, c2, c3 = st.columns(3)
    c1.metric("Journal", "Insects")
    c2.metric("Year", "2023")
    c3.metric("DOI", DOI)
    st.link_button("Open the article by DOI", DOI_URL)


def render():
    st.markdown("<div class='section-head'>References / Data Sources</div>", unsafe_allow_html=True)
    source_summary()
    st.info(
        "The published GC-MS Bio-feature annotations and their identification-confidence "
        "categories originate from this study. Candidate molecular structures in VOC·BIO are "
        "a separate curated interpretation layer and do not upgrade the published peak identity."
    )
    st.markdown("#### Supplementary Information")
    st.write(
        "The Supplementary Information is retained as a distinct primary source in the project "
        "evidence package (`insects-2378901-supplementary.pdf`)."
    )
    sources = [
        {
            "Source": "Supplementary Table S1",
            "Use in VOC·BIO": "Biological and sample context",
            "What it supports": "Aphid species, host plant/part, accession, collection site, coordinates and collection date",
        },
        {
            "Source": "Supplementary Table S2",
            "Use in VOC·BIO": "Published Bio-feature evidence",
            "What it supports": "81 Bio IDs, printed RT, annotations, inherited identification-confidence categories and documentary context presence",
        },
    ]
    st.dataframe(sources, use_container_width=True, hide_index=True)
    st.caption("Feature-level source: Alotaibi et al. 2023, Supplementary Table S2.")
    st.caption("Context-level source: Alotaibi et al. 2023, Supplementary Table S1.")
    with st.expander("How confidence was defined in Supplementary Table S2"):
        st.markdown(
            "- **Authentic-standard supported**: selected key compounds were compared with authentic standards. Original published notation: `*`.\n"
            "- **Tentative identification, higher library match**: reported NIST reverse match 990–850. Original published notation: `?`.\n"
            "- **Tentative identification, lower library match**: reported NIST reverse match 800–700. Original published notation: `??`.\n"
            "- **Unknown feature**: reported reverse match below 700. Original published notation: `UK`."
        )
