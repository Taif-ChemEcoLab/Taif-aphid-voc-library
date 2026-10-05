"""Structural similarity across validated publication-annotation candidates."""

import plotly.express as px
import streamlit as st

from data.v1_loader import CONFIDENCE_LABELS
from services.chemistry import chemistry_contract, similarity_search, structural_similarity_matrix, structured_chemicals
from utils.chem_utils import MAX_SMILES_LENGTH, get_structure_image_url, mol_from_smiles


def render():
    st.markdown("<div class='section-head'>Structural Similarity Explorer</div>", unsafe_allow_html=True)
    st.warning(
        "Structural similarity compares candidate molecular structures and does not establish shared biological activity or confirm GC-MS identity."
    )
    all_chemicals = structured_chemicals()
    filters = st.columns([2, 2])
    confidence = filters[0].multiselect(
        "Published confidence", ["*", "?", "??"], default=["*", "?", "??"],
        format_func=lambda value: CONFIDENCE_LABELS[value], key="similarity_confidence",
    )
    statuses = ["All"] + all_chemicals["identity_status_label"].drop_duplicates().tolist()
    identification_status = filters[1].selectbox("Identification status", statuses, key="similarity_status")
    chemicals = structured_chemicals(tuple(confidence), identification_status)
    if chemicals.empty:
        st.warning("No validated candidate structures match the selected filters.")
        return
    st.caption(f"{len(chemicals)} validated candidate structures included.")
    query_tab, matrix_tab = st.tabs(["Nearest structures", "Pairwise matrix"])
    with query_tab:
        controls = st.columns([2, 2, 1])
        source = controls[0].radio("Query source", ["Curated candidate", "Custom SMILES"], horizontal=True)
        threshold = controls[2].slider("Minimum Tanimoto", 0.0, 1.0, 0.0, 0.05)
        if source == "Curated candidate":
            selected = controls[1].selectbox(
                "Structure", chemicals["chemical_id"].tolist(),
                format_func=lambda value: f"{chemicals.loc[chemicals['chemical_id'] == value, 'bio_id'].iloc[0]} · {chemicals.loc[chemicals['chemical_id'] == value, 'canonical_name'].iloc[0]}",
            )
            query = chemicals.loc[chemicals["chemical_id"] == selected, "smiles"].iloc[0]
        else:
            query = controls[1].text_input("Custom SMILES", max_chars=MAX_SMILES_LENGTH)
        if st.button("Calculate structural similarity", type="primary"):
            if not query or mol_from_smiles(query) is None:
                st.error("Enter a valid SMILES within the 512-character bound.")
            else:
                result = similarity_search(query, threshold, tuple(confidence), identification_status)
                if result.empty:
                    st.info("No validated candidate structures meet the selected threshold.")
                else:
                    result["Feature and candidate"] = result["bio_id"] + " · " + result["canonical_name"]
                    fig = px.bar(
                        result.sort_values("tanimoto_similarity"), x="tanimoto_similarity", y="Feature and candidate",
                        orientation="h", text="tanimoto_similarity", color="identification_confidence",
                        hover_data=["formula", "published_confidence_notation"], title="Morgan-fingerprint similarity",
                        labels={"identification_confidence": "Identification confidence", "published_confidence_notation": "Original published notation"},
                    )
                    fig.update_layout(height=max(360, 28 * len(result)), xaxis=dict(range=[0, 1.05], title="Tanimoto coefficient"), yaxis_title="")
                    st.plotly_chart(fig, use_container_width=True)
                    for column, (_, candidate) in zip(st.columns(min(4, len(result))), result.head(4).iterrows()):
                        with column:
                            with st.container(border=True):
                                url = get_structure_image_url(candidate["pubchem_cid"], candidate["smiles"], 260, 180)
                                if url:
                                    st.image(url, use_column_width=True)
                                st.markdown(f"**{candidate['bio_id']} · {candidate['canonical_name']}**")
                                st.metric("Tanimoto", f"{candidate['tanimoto_similarity']:.3f}")
                                st.caption(candidate["identity_status_label"])
                    display = result[["bio_id", "canonical_name", "formula", "pubchem_cid", "identification_confidence", "published_confidence_notation", "tanimoto_similarity"]].copy()
                    display.columns = ["Bio ID", "Candidate chemical", "Formula", "PubChem CID", "Identification confidence", "Original published notation", "Tanimoto similarity"]
                    st.dataframe(display, use_container_width=True, hide_index=True)
                    st.download_button("Download similarity results", result.to_csv(index=False), "voc_bio_v1_structural_similarity_results.csv", "text/csv")
    with matrix_tab:
        matrix = structural_similarity_matrix(tuple(confidence), identification_status)
        fig = px.imshow(matrix, zmin=0, zmax=1, color_continuous_scale="Greens", aspect="auto", labels={"color": "Tanimoto"}, title="Pairwise candidate-structure similarity")
        fig.update_layout(height=max(500, min(1000, 19 * len(matrix))), margin=dict(t=55, b=120, l=100, r=30))
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("Download similarity matrix", matrix.to_csv(index=True), "voc_bio_v1_structural_similarity_matrix.csv", "text/csv")
    with st.expander("Technical method and evidence boundary"):
        st.json(chemistry_contract())
