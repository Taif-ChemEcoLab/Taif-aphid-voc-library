"""Dashboard – overview statistics. Fixed: applymap → map (Pandas 2.x)."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.sample_data import VOCS, INSECTS, PLANTS, BIOASSAYS


def render():
    st.markdown("""
    <div style='padding: 32px 0 24px 0'>
        <div class='hero-title'>VOC · BIO<br>Library</div>
        <div class='hero-subtitle'>
            Volatile Organic Compounds · Insect–Plant Interactions · Cheminformatics
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Stats cards ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class='info-box'>
        <b>Version 1 Scope:</b> This app is an evidence-navigation platform for
        exploring curated VOC, insect, plant, bioassay, docking evidence, and
        structural similarity records. It is not a validated prediction system. Docking
        evidence, structural similarity rankings, and assistant responses should be treated
        as hypothesis-generating evidence that requires experimental or
        literature validation before biological interpretation.
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Methods / Definitions", expanded=True):
        st.markdown(
            """
            - **VOC records:** Curated volatile organic compound entries linked to chemical identifiers, source plants, insects, and supporting observations in the bundled dataset.
            - **Bioactivity annotation:** A curated label, such as attractant or repellent, derived from the available literature, assay, or dataset context. It should be interpreted as an evidence annotation, not as a validated prediction.
            - **Structural similarity score:** A cheminformatics comparison based on molecular fingerprints, reported as a Tanimoto-style similarity score where higher values indicate more similar chemical structures.
            - **Docking affinity:** A receptor-ligand docking score or binding-energy estimate from curated docking records. It is hypothesis-generating and does not establish biological activity on its own.
            - **Evidence level / confidence:** A qualitative curation field summarizing the strength, source, or review status of supporting evidence when available.
            - **Local assistant behavior:** The assistant uses local, rule-based responses over the bundled VOC, bioassay, plant, insect, and docking data. It does not perform live web search or external model-based validation in this public Version 1 app.
            """
        )

    with st.expander("Citation / Data Provenance", expanded=True):
        st.markdown(
            """
            - **GC-MS and VOC dataset:** VOC occurrence records, chemical annotations, plant/insect context, concentration fields, and bioactivity annotations come from the bundled curated GC-MS and bioassay data tables used by this Version 1 app.
            - **Curated receptor-ligand evidence:** Receptor, ligand, organism, and evidence-status tables are loaded from the local curation files when available and should be interpreted as review records.
            - **Literature-derived docking entries:** Docking evidence records summarize literature- or curation-derived receptor-ligand docking metadata, affinity estimates, docking engine details, and validation status where available.
            - **PubChem structure rendering:** Two-dimensional molecule images and PubChem links are rendered from PubChem identifiers or SMILES-based PubChem services for visual inspection.
            - **RDKit calculations:** Molecular descriptors, volatility screens, Morgan fingerprints, Tanimoto structural similarity scores, and pairwise structural similarity matrices are computed locally with RDKit when RDKit is installed.
            - **Version 1 provenance note:** Exported CSV files reflect the filtered in-app tables at download time. They should be cited as curated Version 1 application outputs alongside the underlying literature, GC-MS, docking, PubChem, and RDKit sources.
            """
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    stats = [
        (c1, len(VOCS),                      "VOC Compounds"),
        (c2, len(INSECTS),                   "Insect Species"),
        (c3, len(PLANTS),                    "Host Plants"),
        (c4, len(BIOASSAYS),                 "Bioassay Records"),
        (c5, len(VOCS["class"].unique()),     "Chemical Classes"),
    ]
    for col, num, label in stats:
        with col:
            st.markdown(f"""
            <div class='stat-card'>
                <div class='stat-number'>{num}</div>
                <div class='stat-label'>{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1 charts ──────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(
            "<div class='section-head'>Bioactivity Annotation Distribution</div>",
            unsafe_allow_html=True,
        )
        bio_counts = VOCS["bioactivity"].value_counts().reset_index()
        bio_counts.columns = ["Bioactivity Annotation", "Count"]
        fig = px.pie(
            bio_counts, names="Bioactivity Annotation", values="Count",
            color="Bioactivity Annotation",
            color_discrete_map={"Attractant": "#22c55e", "Repellent": "#ef4444"},
            hole=0.55,
        )
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10), height=280,
            legend=dict(orientation="h", y=-0.05),
            font=dict(family="Inter"),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_traces(textinfo="percent+label", textfont_size=13)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Shows the balance of curated attractant and repellent annotations; "
            "it does not estimate efficacy or provide validated behavior predictions for untested VOCs."
        )

    with col_b:
        st.markdown(
            "<div class='section-head'>Chemical Classes</div>",
            unsafe_allow_html=True,
        )
        class_counts = VOCS["class"].value_counts().reset_index()
        class_counts.columns = ["Class", "Count"]
        fig2 = px.bar(
            class_counts, x="Count", y="Class", orientation="h",
            color="Count",
            color_continuous_scale=["#b7dfc9", "#1a3a2a"],
        )
        fig2.update_layout(
            margin=dict(t=10, b=10, l=10, r=10), height=280,
            coloraxis_showscale=False,
            yaxis_title="", xaxis_title="Number of VOCs",
            font=dict(family="Inter"),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "Summarizes chemical class coverage in the bundled records; it does "
            "not imply that larger classes have stronger biological evidence."
        )

    # ── Row 2 charts ──────────────────────────────────────────────────────────
    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown(
            "<div class='section-head'>LogP vs MW by Bioactivity Annotation</div>",
            unsafe_allow_html=True,
        )
        fig3 = px.scatter(
            VOCS, x="mw", y="logp",
            color="bioactivity",
            symbol="class",
            hover_name="name",
            hover_data={"insect": True, "plant": True},
            color_discrete_map={"Attractant": "#22c55e", "Repellent": "#ef4444"},
            labels={"mw": "Molecular Weight (g/mol)", "logp": "LogP", "bioactivity": "Bioactivity Annotation"},
        )
        fig3.update_traces(marker=dict(size=11, line=dict(width=1, color="white")))
        fig3.update_layout(
            margin=dict(t=10, b=10, l=10, r=10), height=280,
            legend=dict(orientation="h", y=-0.2),
            font=dict(family="Inter"),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.caption(
            "Maps molecular weight and LogP against curated bioactivity annotations; "
            "separation in this plot is descriptive, not a validated classifier."
        )

    with col_d:
        st.markdown(
            "<div class='section-head'>Emission Source Breakdown</div>",
            unsafe_allow_html=True,
        )
        src_counts = VOCS["emission_source"].value_counts().reset_index()
        src_counts.columns = ["Source", "Count"]
        fig4 = px.bar(
            src_counts, x="Source", y="Count",
            color="Source",
            color_discrete_sequence=["#4a7c59", "#a8d5b5"],
            text="Count",
        )
        fig4.update_layout(
            margin=dict(t=10, b=10, l=10, r=10), height=280,
            showlegend=False, xaxis_title="",
            font=dict(family="Inter"),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig4.update_traces(textposition="outside")
        st.plotly_chart(fig4, use_container_width=True)
        st.caption(
            "Counts source contexts recorded for VOC emissions; it does not rank "
            "source quality, emission rate, or ecological importance."
        )

    # ── Recent records ────────────────────────────────────────────────────────
    preview_rows = min(12, len(VOCS))
    st.markdown(
        "<div class='section-head'>VOC Record Preview</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Showing the first {preview_rows} curated VOC records from the bundled "
        f"library ({len(VOCS)} total records). Use the VOC Library page for the "
        "full searchable table."
    )
    display_cols = ["voc_id", "name", "class", "formula", "bioactivity", "insect", "plant"]
    styled = VOCS[display_cols].head(preview_rows).copy()

    def color_bio(val):
        if val == "Attractant":
            return "background-color:#d1fae5;color:#065f46;font-weight:600"
        elif val == "Repellent":
            return "background-color:#fee2e2;color:#991b1b;font-weight:600"
        return ""

    # .map() replaces deprecated .applymap() in pandas 2.x
    st.dataframe(
        styled.style.map(color_bio, subset=["bioactivity"]),
        use_container_width=True,
        height=430,
    )

    st.markdown("""
    <div class='footer'>
        VOC·BIO Library · Cheminformatics-Enhanced Insect–Plant Interaction Database<br>
        Powered by RDKit · Streamlit · Plotly · NetworkX
    </div>
    """, unsafe_allow_html=True)
