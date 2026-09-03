"""Structural similarity explorer using Morgan fingerprints and Tanimoto scores."""

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.sample_data import VOCS
from utils.chem_utils import (
    RDKIT_AVAILABLE,
    get_structure_image_url,
    similarity_matrix,
    tanimoto_similarity,
)


def render():
    st.markdown(
        "<div class='section-head'>Structural Similarity Explorer</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class='info-box'>
        This tool compares VOC <b>chemical structures</b> using Morgan fingerprints
        (radius=2, 2048 bits) and the Tanimoto coefficient. It is intended for
        structure-based navigation only. A high score does <b>not</b> demonstrate
        similar odor, volatility, aphid response, receptor binding, or ecological function.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not RDKIT_AVAILABLE:
        st.error(
            "**RDKit is required for structural similarity calculations.**\n\n"
            "Add `rdkit` to your `requirements.txt` and redeploy."
        )
        return

    tab1, tab2 = st.tabs(["Structure Query", "Pairwise Structure Matrix"])

    with tab1:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            mode = st.radio(
                "Query by", ["Select from Library", "Enter SMILES"], horizontal=True
            )
        with col_b:
            threshold = st.slider(
                "Structural similarity threshold", 0.0, 1.0, 0.2, 0.05
            )

        query_smiles = None

        if mode == "Select from Library":
            selected = st.selectbox("Select query VOC", VOCS["name"].tolist())
            query_row = VOCS[VOCS["name"] == selected].iloc[0]
            query_smiles = query_row["smiles"]
        else:
            query_smiles = st.text_input(
                "Enter SMILES string",
                placeholder="e.g. CC1=CCC(CC1)C(C)=C",
            )

        st.caption(
            "Results are ranked by structural fingerprint similarity only. Treat "
            "bioactivity annotation, insect, and source fields as contextual evidence."
        )

        if query_smiles and st.button("Find structurally related VOCs", type="primary"):
            with st.spinner("Computing Morgan/Tanimoto structural similarities..."):
                results = []
                for _, row in VOCS.iterrows():
                    sim = tanimoto_similarity(query_smiles, row["smiles"])
                    results.append(
                        {
                            "VOC": row["name"],
                            "Class": row["class"],
                            "Formula": row["formula"],
                            "Bioactivity Annotation": row["bioactivity"],
                            "Insect": row["insect"],
                            "Structural Similarity": sim,
                            "SMILES": row["smiles"],
                            "CID": row.get("pubchem_cid", 0),
                        }
                    )

                results_df = pd.DataFrame(results)
                results_df = results_df[results_df["Structural Similarity"] >= threshold]
                results_df = results_df.sort_values("Structural Similarity", ascending=False)

            if results_df.empty:
                st.warning(
                    f"No VOCs found with structural similarity >= {threshold}"
                )
            else:
                st.success(
                    f"Found **{len(results_df)}** structurally related VOCs "
                    f"at threshold >= {threshold}"
                )

                fig = px.bar(
                    results_df,
                    x="Structural Similarity",
                    y="VOC",
                    color="Class",
                    orientation="h",
                    text="Structural Similarity",
                    hover_data=["Formula", "Bioactivity Annotation", "Insect"],
                )
                fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
                fig.add_vline(
                    x=0.4,
                    line_dash="dash",
                    line_color="#f59e0b",
                    annotation_text="Structural reference (0.4)",
                )
                fig.update_layout(
                    height=max(250, len(results_df) * 40),
                    margin=dict(t=10, b=10, l=10, r=60),
                    xaxis=dict(range=[0, 1.15]),
                    font=dict(family="Inter"),
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(
                    "Ranks library VOCs by Morgan/Tanimoto structural similarity; "
                    "high scores do not establish shared odor, bioactivity annotation, or docking evidence."
                )
                st.download_button(
                    "Download structural similarity results CSV",
                    data=results_df.to_csv(index=False),
                    file_name="structural_similarity_results.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

                st.markdown("**Top 4 Closest Structures**")
                st.caption(
                    "Closest by Morgan/Tanimoto structure fingerprints; not a "
                    "bioactivity annotation or docking evidence result."
                )
                top4 = results_df.head(4)
                cols = st.columns(min(4, len(top4)))
                for col, (_, row) in zip(cols, top4.iterrows()):
                    with col:
                        img_url = get_structure_image_url(
                            pubchem_cid=row["CID"],
                            smiles=row["SMILES"],
                            width=240,
                            height=160,
                        )
                        if img_url:
                            st.image(img_url, width=240)
                        st.markdown(
                            f"**{row['VOC']}**  \n"
                            f'<span style="color:#1a3a2a;font-weight:700">'
                            f'{row["Structural Similarity"]:.3f}</span>',
                            unsafe_allow_html=True,
                        )

                st.markdown("**Structural Match Results**")

                def color_bio(val):
                    if val == "Attractant":
                        return (
                            "background-color:#d1fae5;color:#065f46;font-weight:600"
                        )
                    if val == "Repellent":
                        return (
                            "background-color:#fee2e2;color:#991b1b;font-weight:600"
                        )
                    return ""

                display = results_df.drop(columns=["SMILES", "CID"]).copy()
                display["Structural Similarity"] = display["Structural Similarity"].apply(
                    lambda x: f"{x:.4f}"
                )
                st.dataframe(
                    display.style.map(color_bio, subset=["Bioactivity Annotation"]),
                    use_container_width=True,
                    hide_index=True,
                )

    with tab2:
        st.markdown("**Pairwise Structural Similarity Matrix - All VOCs**")
        st.caption(
            "Computed using Morgan fingerprints (radius=2, 2048 bits). This matrix "
            "shows chemical neighborhood only, not functional or behavioral similarity."
        )

        with st.spinner("Computing full structural similarity matrix..."):
            smiles_list = VOCS["smiles"].tolist()
            names = [
                (name[:22] + "..." if len(name) > 22 else name)
                for name in VOCS["name"].tolist()
            ]
            mat = similarity_matrix(smiles_list, names)

        fig_heat = px.imshow(
            mat,
            color_continuous_scale=["#f0fdf4", "#1a3a2a"],
            zmin=0,
            zmax=1,
            text_auto=".2f",
            aspect="auto",
            labels=dict(color="Tanimoto"),
        )
        fig_heat.update_layout(
            height=550,
            margin=dict(t=10, b=80, l=10, r=10),
            font=dict(family="Inter", size=9),
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-40,
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        st.caption(
            "Shows pairwise structural neighborhoods across the library; it is "
            "a navigation map, not evidence of shared biological function."
        )
        st.download_button(
            "Download pairwise structural similarity matrix CSV",
            data=mat.to_csv(index=True),
            file_name="pairwise_structural_similarity_matrix.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown(
            """
            **Interpretation guide**
            - **1.00** = identical fingerprint
            - **0.85+** = close structural analogs
            - **0.40-0.85** = structurally related region
            - **< 0.40** = structurally distinct by this fingerprint

            These bands are navigation aids, not evidence of shared bioactivity
            annotation, docking evidence, odor profile, volatility, or ecological role.
            """
        )
