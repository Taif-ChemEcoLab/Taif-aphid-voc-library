"""Bioassay Results page. Fixed: applymap → map (Pandas 2.x)."""

import streamlit as st
import plotly.express as px
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.sample_data import BIOASSAYS


def render():
    st.markdown("<div class='section-head'>📊 Bioassay Results</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='info-box'>
    Bioassay results from olfactometer and wind-tunnel experiments. Effect size = % insects
    responding to the VOC. Lower p-values indicate stronger statistical evidence.
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        resp_filter  = st.selectbox("Response",   ["All"] + list(BIOASSAYS["response"].unique()))
    with col2:
        assay_filter = st.selectbox("Assay Type", ["All"] + list(BIOASSAYS["assay_type"].unique()))
    with col3:
        min_effect   = st.slider("Min Effect Size (%)", 0, 100, 0)

    df = BIOASSAYS.copy()
    if resp_filter  != "All": df = df[df["response"]   == resp_filter]
    if assay_filter != "All": df = df[df["assay_type"] == assay_filter]
    df = df[df["effect_size"] >= min_effect]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records",          len(df))
    c2.metric("Avg Effect Size",  f"{df['effect_size'].mean():.1f}%")
    c3.metric("Attractant Tests", int((df["response"] == "Attractant").sum()))
    c4.metric("Repellent Tests",  int((df["response"] == "Repellent").sum()))

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Effect Size by VOC**")
        fig1 = px.bar(
            df.sort_values("effect_size", ascending=True),
            x="effect_size", y="voc_name",
            color="response",
            color_discrete_map={"Attractant": "#22c55e", "Repellent": "#ef4444"},
            orientation="h", text="effect_size",
            hover_data=["assay_type", "n_replicates", "p_value"],
        )
        fig1.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig1.update_layout(
            height=380, margin=dict(t=10, b=10, l=10, r=50),
            xaxis_title="Effect Size (%)", yaxis_title="",
            legend=dict(orientation="h", y=-0.12),
            font=dict(family="Inter"), paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig1, use_container_width=True)
        st.caption(
            "Ranks curated assay effect sizes for displayed records; it does not "
            "standardize across assay designs or provide a validated field-performance prediction."
        )

    with col_b:
        st.markdown("**Effect Size vs Concentration**")
        fig2 = px.scatter(
            df, x="concentration_ppm", y="effect_size",
            color="response", size="n_replicates",
            hover_name="voc_name",
            hover_data=["insect", "assay_type", "p_value"],
            color_discrete_map={"Attractant": "#22c55e", "Repellent": "#ef4444"},
            labels={"concentration_ppm": "Concentration (ppm)", "effect_size": "Effect Size (%)"},
        )
        fig2.update_layout(
            height=380, margin=dict(t=10, b=10),
            legend=dict(orientation="h", y=-0.12),
            font=dict(family="Inter"), paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "Shows assay concentration against response magnitude; point patterns "
            "are descriptive and do not establish a dose-response model."
        )

    st.markdown("**Statistical Significance (−log₁₀ p-value)**")
    df_pv = df.copy()
    df_pv["neg_log_p"] = df_pv["p_value"].apply(lambda x: -math.log10(x) if x > 0 else 0)
    fig3 = px.bar(
        df_pv.sort_values("neg_log_p", ascending=False),
        x="voc_name", y="neg_log_p",
        color="response",
        color_discrete_map={"Attractant": "#22c55e", "Repellent": "#ef4444"},
        labels={"voc_name": "VOC", "neg_log_p": "-log₁₀(p)"},
    )
    fig3.add_hline(y=-math.log10(0.05), line_dash="dash",
                   line_color="#f59e0b", annotation_text="p=0.05")
    fig3.update_layout(
        height=300, margin=dict(t=10, b=80), xaxis_tickangle=-30,
        legend=dict(orientation="h", y=-0.35),
        font=dict(family="Inter"), paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption(
        "Displays statistical support as -log10(p) with a p=0.05 reference line; "
        "it does not measure biological effect size or independent replication."
    )

    st.markdown("**Full Bioassay Records**")
    def color_resp(val):
        if val == "Attractant": return "background-color:#d1fae5;color:#065f46;font-weight:600"
        elif val == "Repellent": return "background-color:#fee2e2;color:#991b1b;font-weight:600"
        return ""

    st.dataframe(
        df.style.map(color_resp, subset=["response"]),   # .map not .applymap
        use_container_width=True, hide_index=True, height=320,
    )
