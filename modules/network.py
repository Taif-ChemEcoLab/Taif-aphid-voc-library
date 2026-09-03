"""Interaction Network – semiochemical knowledge graph."""

import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.sample_data import VOCS


def render():
    st.markdown("<div class='section-head'>🔗 Interaction Network</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='info-box'>
    Semiochemical knowledge graph connecting <b>VOCs → Insects → Host Plants → Natural Enemies</b>.
    Green edges = Attractant &nbsp;|&nbsp; Red edges = Repellent.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        bio_filter   = st.selectbox("Filter by Bioactivity Annotation", ["All", "Attractant", "Repellent"])
    with col2:
        show_enemies = st.checkbox("Show Natural Enemies", value=True)

    df = VOCS.copy()
    if bio_filter != "All":
        df = df[df["bioactivity"] == bio_filter]

    G = nx.Graph()
    for _, row in df.iterrows():
        voc    = row["name"];  insect = row["insect"]
        plant  = row["plant"]; enemy  = row["natural_enemy"]
        bio    = row["bioactivity"]
        G.add_node(voc,    type="VOC",    bioactivity=bio)
        G.add_node(insect, type="Insect")
        G.add_node(plant,  type="Plant")
        if show_enemies: G.add_node(enemy, type="Enemy")
        G.add_edge(voc, insect, relationship=bio)
        G.add_edge(insect, plant, relationship="hosts")
        if show_enemies:
            G.add_edge(voc, enemy,
                       relationship="recruits" if bio == "Attractant" else "signals")

    pos = nx.spring_layout(G, seed=42, k=2.5)
    type_colors = {"VOC": "#4a7c59", "Insect": "#ef4444",
                   "Plant": "#22c55e", "Enemy": "#f59e0b"}

    edge_traces = []
    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]; x1, y1 = pos[v]
        rel   = data.get("relationship", "")
        color = ("#22c55e" if rel in ("Attractant", "recruits")
                 else "#ef4444" if rel in ("Repellent", "signals")
                 else "#94a3b8")
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines", line=dict(width=1.8, color=color),
            hoverinfo="none", showlegend=False,
        ))

    node_traces = []
    for node_type, color in type_colors.items():
        nodes = [n for n, d in G.nodes(data=True) if d.get("type") == node_type]
        if not nodes: continue
        node_traces.append(go.Scatter(
            x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
            mode="markers+text",
            marker=dict(size=[12 + G.degree(n)*4 for n in nodes], color=color,
                        line=dict(width=1.5, color="white"), opacity=0.9),
            text=nodes, textposition="top center",
            textfont=dict(size=9, family="Inter", color="#1a3a2a"),
            hovertext=[f"<b>{n}</b><br>Type: {node_type}<br>Degree: {G.degree(n)}"
                       for n in nodes],
            hoverinfo="text", name=node_type, legendgroup=node_type,
        ))

    fig = go.Figure(data=edge_traces + node_traces)
    fig.update_layout(
        height=600, margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(orientation="h", y=-0.05, font=dict(family="Inter"),
                    bgcolor="rgba(255,255,255,0.8)"),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#f0fdf4", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter"),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Visualizes curated VOC-insect-plant-enemy links and node connectivity; "
        "it does not infer causality, interaction strength, or missing relationships."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Network Statistics**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nodes", G.number_of_nodes())
    c2.metric("Edges", G.number_of_edges())
    c3.metric("Avg Degree",
              f"{sum(d for _, d in G.degree()) / G.number_of_nodes():.2f}")
    c4.metric("Connected Components", nx.number_connected_components(G))

    st.markdown("**Top Hub Nodes**")
    top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:8]
    hub_data  = [{"Node": n, "Type": G.nodes[n].get("type", "—"),
                  "Degree": d, "Bioactivity": G.nodes[n].get("bioactivity", "—")}
                 for n, d in top_nodes]
    st.dataframe(pd.DataFrame(hub_data), use_container_width=True, hide_index=True)
