"""Interactive typed evidence network over supported V1 relationships."""

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

from data.v1_loader import BIOLOGICAL_CONTEXTS, CONFIDENCE_LABELS
from services.evidence_network import evidence_network_tables, network_contract


NODE_COLORS = {"context": "#166534", "species": "#dc2626", "host": "#22c55e", "feature": "#64748b", "chemical_interpretation": "#7c3aed"}
EDGE_COLORS = {"context_species": "#ef4444", "context_host": "#22c55e", "published_presence": "#94a3b8", "chemical_interpretation": "#8b5cf6"}


def _figure(nodes, edges):
    graph = nx.Graph()
    for row in nodes.to_dict("records"):
        graph.add_node(row["node_id"], **row)
    for row in edges.to_dict("records"):
        graph.add_edge(row["source"], row["target"], **row)
    position = nx.spring_layout(graph, seed=42, k=1.5 / max(len(graph.nodes) ** 0.5, 1))
    traces = []
    for edge_type, color in EDGE_COLORS.items():
        x, y = [], []
        for left, right, detail in graph.edges(data=True):
            if detail.get("edge_type") != edge_type:
                continue
            x += [position[left][0], position[right][0], None]
            y += [position[left][1], position[right][1], None]
        if x:
            traces.append(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=1.2), hoverinfo="skip", name=edge_type.replace("_", " ")))
    for node_type, color in NODE_COLORS.items():
        selected = [node for node, detail in graph.nodes(data=True) if detail.get("node_type") == node_type]
        if not selected:
            continue
        traces.append(go.Scatter(x=[position[node][0] for node in selected], y=[position[node][1] for node in selected], mode="markers", marker=dict(color=color, size=[10 + min(graph.degree(node), 8) * 2 for node in selected], line=dict(color="white", width=1)), hovertext=[f"<b>{graph.nodes[node]['label']}</b><br>{node_type}<br>{graph.nodes[node]['detail']}<br>Evidence: {graph.nodes[node]['evidence_level']}<br>Documentation degree: {graph.degree(node)}" for node in selected], hoverinfo="text", name=node_type.replace("_", " ")))
    figure = go.Figure(traces)
    figure.update_layout(height=650, xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h", y=-0.05), plot_bgcolor="#f8faf9")
    return figure, graph


def render():
    st.markdown("<div class='section-head'>Feature-Context Evidence Network</div>", unsafe_allow_html=True)
    st.info("Edges encode published presence, documentary context, or chemical interpretation only. Connectivity measures documentation coverage, not ecological importance or causality.")
    labels = BIOLOGICAL_CONTEXTS.apply(lambda row: f"{row['canonical_species']} · {row['host_plant_and_part']}", axis=1)
    controls = st.columns([3, 2, 2])
    selection = controls[0].multiselect("Contexts", BIOLOGICAL_CONTEXTS["context_id"].tolist(), default=[BIOLOGICAL_CONTEXTS["context_id"].iloc[0]], format_func=lambda value: labels[BIOLOGICAL_CONTEXTS["context_id"] == value].iloc[0])
    confidence = controls[1].multiselect("Identification confidence", ["*", "?", "??", "UK"], default=["*", "?", "??", "UK"], format_func=lambda value: CONFIDENCE_LABELS[value])
    include_chemicals = controls[2].toggle("Chemical interpretations", value=True)
    if not selection:
        st.warning("Select at least one biological context.")
        return
    nodes, edges = evidence_network_tables(tuple(selection), tuple(confidence), include_chemicals)
    figure, graph = _figure(nodes, edges)
    metrics = st.columns(4)
    metrics[0].metric("Nodes", graph.number_of_nodes())
    metrics[1].metric("Evidence edges", graph.number_of_edges())
    metrics[2].metric("Published presence edges", int((edges["edge_type"] == "published_presence").sum()))
    metrics[3].metric("Connected components", nx.number_connected_components(graph))
    st.plotly_chart(figure, use_container_width=True)
    edge_tab, node_tab, method_tab = st.tabs(["Evidence edges", "Nodes", "Method"])
    with edge_tab:
        label_lookup = nodes.set_index("node_id")["label"]
        edge_display = edges.copy()
        edge_display["From"] = edge_display["source"].map(label_lookup)
        edge_display["To"] = edge_display["target"].map(label_lookup)
        edge_display["Relationship"] = edge_display["edge_type"].str.replace("_", " ").str.title()
        edge_display = edge_display.rename(columns={"identification_confidence": "Identification confidence", "published_confidence_notation": "Original published notation"})
        edge_display["Original published notation"] = edge_display["Original published notation"].replace("", "Not applicable")
        st.dataframe(edge_display[["From", "To", "Relationship", "Identification confidence", "Original published notation"]], use_container_width=True, hide_index=True, height=360)
        st.download_button("Download filtered edges", edges.to_csv(index=False), "v1_evidence_network_edges.csv", "text/csv")
    with node_tab:
        node_display = nodes[["label", "node_type", "detail", "evidence_level"]].copy()
        node_display.columns = ["Label", "Type", "Details", "Evidence level"]
        node_display = node_display.loc[:, node_display.astype(str).apply(lambda column: column.str.strip().ne("").mean() >= 0.5)]
        st.dataframe(node_display, use_container_width=True, hide_index=True, height=360)
    with method_tab:
        st.write("Network connectivity measures documentation coverage, not biological importance or causality.")
        with st.expander("Developer / network contract"):
            st.json(network_contract())
