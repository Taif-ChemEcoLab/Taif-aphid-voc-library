"""Insect–Plant Database page. Fixed: applymap → map (Pandas 2.x)."""

import streamlit as st
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.sample_data import INSECTS, PLANTS, VOCS


def render():
    st.markdown("<div class='section-head'>🌱 Insect–Plant Database</div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["🦟 Insect Species", "🌿 Host Plants", "🔀 Interaction Matrix"])

    with tab1:
        order_filter = st.selectbox("Filter by Order", ["All"] + list(INSECTS["order"].unique()))
        df_ins = INSECTS if order_filter == "All" else INSECTS[INSECTS["order"] == order_filter]
        st.dataframe(df_ins, use_container_width=True, hide_index=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Insects by Family**")
        fig = px.bar(
            INSECTS["family"].value_counts().reset_index(),
            x="family", y="count", color="family",
            color_discrete_sequence=px.colors.qualitative.G10,
        )
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Count",
                          height=240, margin=dict(t=10, b=10),
                          font=dict(family="Inter"), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        family_filter = st.selectbox("Filter by Family", ["All"] + list(PLANTS["family"].unique()))
        df_plt = PLANTS if family_filter == "All" else PLANTS[PLANTS["family"] == family_filter]
        st.dataframe(df_plt, use_container_width=True, hide_index=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Plants by Economic Importance**")
        imp_counts = PLANTS["economic_importance"].value_counts().reset_index()
        imp_counts.columns = ["Importance", "Count"]
        order_map = {"Very High": 4, "High": 3, "Moderate": 2, "Low": 1}
        imp_counts["order"] = imp_counts["Importance"].map(order_map)
        imp_counts = imp_counts.sort_values("order")
        fig2 = px.bar(
            imp_counts, x="Importance", y="Count", color="Importance",
            color_discrete_map={"Very High": "#1a3a2a", "High": "#4a7c59",
                                 "Moderate": "#a8d5b5", "Low": "#d1fae5"},
            text="Count",
        )
        fig2.update_layout(showlegend=False, xaxis_title="", height=240,
                           margin=dict(t=10, b=10), font=dict(family="Inter"),
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.markdown("""
        <div class='info-box'>
        Matrix shows how many VOC records exist for each insect–plant combination.
        Darker cells = more VOC data available.
        </div>
        """, unsafe_allow_html=True)
        matrix = (VOCS.groupby(["insect", "plant"]).size()
                      .reset_index(name="voc_count"))
        pivot = matrix.pivot(index="insect", columns="plant",
                              values="voc_count").fillna(0)
        fig3 = px.imshow(
            pivot, color_continuous_scale=["#f0fdf4", "#1a3a2a"],
            aspect="auto", text_auto=True,
            labels=dict(x="Host Plant", y="Insect Species", color="# VOCs"),
        )
        fig3.update_layout(height=420, margin=dict(t=30, b=80, l=10, r=10),
                           font=dict(family="Inter", size=11),
                           paper_bgcolor="rgba(0,0,0,0)", xaxis_tickangle=-35)
        st.plotly_chart(fig3, use_container_width=True)
        st.caption(
            "Counts curated VOC records for each insect-plant pairing; darker "
            "cells indicate data density, not interaction strength or validation."
        )

        st.markdown("**VOC associations per insect**")
        ins_voc = VOCS.groupby("insect").agg(
            voc_count=("voc_id", "count"),
            attractants=("bioactivity", lambda x: (x == "Attractant").sum()),
            repellents=("bioactivity",  lambda x: (x == "Repellent").sum()),
        ).reset_index()
        st.dataframe(ins_voc, use_container_width=True, hide_index=True)
