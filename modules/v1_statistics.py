"""Interactive descriptive statistics for published V1 presence evidence."""

import plotly.express as px
import streamlit as st

from data.v1_loader import CONFIDENCE_LABELS, CONFIDENCE_ORDER, CONFIDENCE_SOURCE_RANGES
from services.context_queries import context_options, filter_contexts
from services.feature_queries import feature_catalog
from services.statistics import clustered_context_order, confidence_summary, feature_prevalence, jaccard_similarity, methods_dictionary, nearest_contexts, presence_matrix, rt_distribution, statistics_contract


COLORS = {"*": "#166534", "?": "#65a30d", "??": "#d97706", "UK": "#64748b"}


def render():
    st.markdown("<div class='section-head'>Published Feature Statistics</div>", unsafe_allow_html=True)
    st.info("All analyses on this page are descriptive or exploratory summaries of published feature presence across 15 documented contexts. The 352 present cells are not independent biological replicates.")
    overview, prevalence_tab, matrix_tab, similarity_tab, rt_tab, methods_tab = st.tabs(["Overview", "Feature prevalence", "81 × 15 matrix", "Jaccard and clustering", "Retention time", "Methods and limits"])
    prevalence = feature_prevalence()
    confidence = confidence_summary()
    with overview:
        metrics = st.columns(5)
        metrics[0].metric("Published features", 81)
        metrics[1].metric("Contexts", 15)
        metrics[2].metric("Present cells", 352)
        metrics[3].metric("With interpretation", int(prevalence["has_interpretation"].sum()))
        metrics[4].metric("Context-specific", int(prevalence["context_specific"].sum()), help="Reported present in exactly one documented context")
        left, right = st.columns(2)
        with left:
            figure = px.bar(confidence, x="identification_confidence", y="features", color="identification_confidence", text="features", color_discrete_map={CONFIDENCE_LABELS[key]: value for key, value in COLORS.items()}, hover_data=["published_confidence_notation", "proportion"], title="Identification confidence of the 81 published GC-MS features", category_orders={"identification_confidence": [CONFIDENCE_LABELS[value] for value in CONFIDENCE_ORDER]}, labels={"identification_confidence": "Identification confidence", "published_confidence_notation": "Original published notation"})
            figure.update_layout(showlegend=False, xaxis_title="", yaxis_title="Features", margin=dict(b=100), xaxis_tickangle=-18)
            st.plotly_chart(figure, use_container_width=True)
        with right:
            composition = confidence.copy()
            st.plotly_chart(px.pie(composition, values="features", names="identification_confidence", color="identification_confidence", color_discrete_map={CONFIDENCE_LABELS[key]: value for key, value in COLORS.items()}, hover_data=["published_confidence_notation"], hole=0.45, title="Feature composition"), use_container_width=True)
        confidence_display = confidence[["identification_confidence", "published_confidence_notation", "features", "proportion"]].copy()
        confidence_display.columns = ["Identification confidence", "Original published notation", "Features", "Proportion"]
        st.dataframe(confidence_display, use_container_width=True, hide_index=True)
        with st.expander("Published confidence definitions"):
            for symbol in CONFIDENCE_ORDER:
                st.markdown(f"- **{CONFIDENCE_LABELS[symbol]}** — {CONFIDENCE_SOURCE_RANGES[symbol]}. Original published notation: `{symbol}`.")
    with prevalence_tab:
        filters = st.columns([2, 3, 2])
        selected_confidence = filters[0].multiselect("Identification confidence", CONFIDENCE_ORDER, default=CONFIDENCE_ORDER, format_func=lambda value: CONFIDENCE_LABELS[value], key="prevalence_confidence")
        query = filters[1].text_input("Feature or annotation", max_chars=120, key="prevalence_query")
        scope = filters[2].selectbox("Scope", ["All", "Context-specific only", "Widespread (≥ 8 contexts)"], key="prevalence_scope")
        data = prevalence[prevalence["confidence_symbol"].isin(selected_confidence)]
        if query:
            data = data[data["bio_id"].str.contains(query, case=False, regex=False) | data["published_annotation_display"].str.contains(query, case=False, regex=False)]
        if scope == "Context-specific only":
            data = data[data["contexts_present"] == 1]
        elif scope.startswith("Widespread"):
            data = data[data["contexts_present"] >= 8]
        chart_data = data.head(30).sort_values(["contexts_present", "bio_id"], kind="stable")
        chart_data["Feature"] = chart_data["bio_id"] + " · " + chart_data["published_annotation_display"]
        st.plotly_chart(px.bar(chart_data, x="contexts_present", y="Feature", orientation="h", color="identification_confidence", color_discrete_map={CONFIDENCE_LABELS[key]: value for key, value in COLORS.items()}, hover_data=["published_annotation_display", "published_confidence_notation", "context_prevalence"], title="Documented contexts containing each feature", labels={"identification_confidence": "Identification confidence", "published_confidence_notation": "Original published notation"}), use_container_width=True)
        display = data[["bio_id", "published_annotation_display", "identification_confidence", "published_confidence_notation", "contexts_present", "context_prevalence"]].copy()
        display.columns = ["Bio ID", "Published annotation", "Identification confidence", "Original published notation", "Contexts present", "context_prevalence"]
        st.dataframe(display, use_container_width=True, hide_index=True, column_config={"context_prevalence": st.column_config.ProgressColumn("Proportion of 15 contexts", min_value=0, max_value=1, format="%.0f%%")})
        st.caption("Prevalence describes reported distribution across documentary contexts; it is not biological significance.")
    with matrix_tab:
        options = context_options()
        controls = st.columns(5)
        species = controls[0].selectbox("Species", ["All"] + options["species"], key="matrix_species")
        host = controls[1].selectbox("Host / part", ["All"] + options["hosts"], key="matrix_host")
        selected_confidence = controls[2].multiselect("Identification confidence", CONFIDENCE_ORDER, default=CONFIDENCE_ORDER, format_func=lambda value: CONFIDENCE_LABELS[value], key="matrix_confidence")
        interpretation = controls[3].selectbox("Interpretation", ["All", "Available", "Not available"], key="matrix_interpretation")
        feature_query = controls[4].text_input("Feature search", max_chars=80, key="matrix_feature")
        contexts = filter_contexts(species, host)
        features = feature_catalog()
        features = features[features["confidence_symbol"].isin(selected_confidence)]
        if interpretation == "Available":
            features = features[features["has_interpretation"]]
        elif interpretation == "Not available":
            features = features[~features["has_interpretation"]]
        if feature_query:
            features = features[features["bio_id"].str.contains(feature_query, case=False, regex=False) | features["published_annotation_display"].str.contains(feature_query, case=False, regex=False)]
        matrix = presence_matrix(features["feature_id"].tolist(), contexts["context_id"].tolist())
        if matrix.empty or matrix.shape[1] == 0:
            st.warning("No matrix cells match the current filters.")
        else:
            height = min(max(430, 18 * len(matrix)), 1400)
            figure = px.imshow(matrix, zmin=0, zmax=1, color_continuous_scale=[[0, "#f8fafc"], [1, "#166534"]], aspect="auto", labels={"x": "Biological context", "y": "Bio feature", "color": "Present"}, title=f"Published presence matrix · {matrix.shape[0]} features × {matrix.shape[1]} contexts")
            figure.update_layout(height=height, margin=dict(t=55, b=100, l=70, r=20), xaxis_tickangle=-45)
            st.plotly_chart(figure, use_container_width=True)
            st.download_button("Download filtered binary matrix", matrix.to_csv(index=True), "v1_feature_context_matrix.csv", "text/csv")
            st.caption("1 = Table S2 reported the feature present in that context. 0 = not listed present; it is not a quantitative zero or behavioral absence.")
    with similarity_tab:
        options = context_options()
        controls = st.columns(2)
        species = controls[0].selectbox("Species subset", ["All"] + options["species"], key="jaccard_species")
        host = controls[1].selectbox("Host subset", ["All"] + options["hosts"], key="jaccard_host")
        contexts = filter_contexts(species, host)
        binary = presence_matrix(context_ids=contexts["context_id"].tolist(), bio_ids=False)
        similarities = jaccard_similarity(binary)
        if len(similarities) < 2:
            st.info("Select at least two contexts for pairwise similarity and clustering.")
        else:
            order, _ = clustered_context_order(binary)
            ordered = similarities.loc[order, order]
            st.plotly_chart(px.imshow(ordered, zmin=0, zmax=1, color_continuous_scale="Viridis", text_auto=".2f", aspect="auto", labels={"color": "Jaccard"}, title="Jaccard similarity · average-linkage cluster order"), use_container_width=True)
            selected = st.selectbox("Nearest contexts for", similarities.index.tolist())
            st.dataframe(nearest_contexts(selected, binary), use_container_width=True, hide_index=True)
            st.caption("Jaccard = shared present features / union of present features. Average linkage clusters 1 − Jaccard distance. Contexts are observational profile units, not replicate groups.")
    with rt_tab:
        rt = rt_distribution()
        selected_confidence = st.multiselect("Identification confidence", CONFIDENCE_ORDER, default=CONFIDENCE_ORDER, format_func=lambda value: CONFIDENCE_LABELS[value], key="rt_confidence")
        rt = rt[rt["confidence_symbol"].isin(selected_confidence)]
        st.plotly_chart(px.histogram(rt, x="published_rt_numeric", color="identification_confidence", color_discrete_map={CONFIDENCE_LABELS[key]: value for key, value in COLORS.items()}, nbins=20, marginal="rug", hover_data=["bio_id", "published_annotation_display", "published_confidence_notation"], title="Published retention-time distribution", labels={"published_rt_numeric": "Published RT (decimal candidate)", "identification_confidence": "Identification confidence", "published_confidence_notation": "Original published notation"}), use_container_width=True)
        rt_display = rt[["bio_id", "published_annotation_display", "published_rt_numeric", "identification_confidence", "published_confidence_notation"]].copy()
        rt_display.columns = ["Bio ID", "Published annotation", "Retention time", "Identification confidence", "Original published notation"]
        st.dataframe(rt_display, use_container_width=True, hide_index=True)
        st.caption("RT values reproduce the publication-facing feature layer. RT overlap does not establish shared chemical identity.")
    with methods_tab:
        methods = methods_dictionary().copy()
        methods["status"] = methods["status"].astype(str).str.replace("_", " ").str.capitalize()
        methods = methods.rename(columns={"method": "Method", "status": "Availability", "interpretation": "Interpretation", "reason": "Evidence note"})
        shown = [column for column in ["Method", "Availability", "Interpretation", "Evidence note"] if column in methods]
        st.dataframe(methods[shown], use_container_width=True, hide_index=True)
        st.warning("PCA, CAP recomputation, Bray–Curtis abundance analysis, inferential tests, p-values, effect sizes and multiple-testing correction are not active because the quantitative/replicate layer is not reconciled.")
        with st.expander("Developer / dataset contract"):
            st.json(statistics_contract())
