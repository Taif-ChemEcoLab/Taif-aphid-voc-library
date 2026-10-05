"""Researcher-facing Phase 5C.3 overview."""

import plotly.express as px
import streamlit as st

from data.v1_loader import CONFIDENCE_LABELS, CONFIDENCE_ORDER, CONFIDENCE_SOURCE_RANGES, CURATED_CANDIDATE_STRUCTURES, LEGACY_17, QUARANTINED_FIELDS, UNRESOLVED_RECORDS
from services.context_queries import filter_contexts
from services.feature_queries import catalog_contract, filter_features, filter_options
from utils.display import researcher_table
from utils.sorting import bio_id_number


COLORS = {"*": "#166534", "?": "#65a30d", "??": "#d97706", "UK": "#64748b"}
def render():
    st.markdown("<div class='hero-title'>VOC · BIO<br>Library</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Published GC-MS features · biological contexts · evidence provenance</div>", unsafe_allow_html=True)
    st.info(
        "Published occurrence, candidate chemical structure, biological context, and ecological evidence "
        "are separate evidence layers. A curated structure does not confirm a GC-MS peak identity."
    )
    options = filter_options()
    with st.expander("Filter the overview", expanded=False):
        c1, c2, c3 = st.columns(3)
        confidence = c1.multiselect(
            "Identification confidence", CONFIDENCE_ORDER, default=CONFIDENCE_ORDER,
            format_func=lambda value: CONFIDENCE_LABELS[value],
        )
        species = c2.selectbox("Aphid species", ["All"] + options["species"])
        host = c3.selectbox("Host / plant part", ["All"] + options["hosts"])
    features = filter_features(confidences=tuple(confidence), species=species, host=host)
    contexts = filter_contexts(species=species, host=host)
    curated_count = int(features["chemical_id"].isin(CURATED_CANDIDATE_STRUCTURES["chemical_id"]).sum())
    cols = st.columns(6)
    metrics = [
        (len(features), "Published features", "Unique Bio variables in the current view"),
        (len(contexts), "Documented contexts", "Sample and host contexts from Supplementary Table S1"),
        (int(features["contexts_present"].sum()), "Presence records", "Documentary feature-context presence cells"),
        (int(features["has_interpretation"].sum()), "Chemical interpretations", "Named annotations, including unresolved generic labels"),
        (curated_count, "Curated candidate structures", "Validated molecular representations; not confirmed compounds"),
        (int((features["confidence_symbol"] == "UK").sum()), "Unknown features", "Inherited published unknown-feature category"),
    ]
    for col, (value, label, help_text) in zip(cols, metrics):
        col.metric(label, value, help=help_text)

    overview, structures, context_tab, limitations = st.tabs(
        ["Published evidence", "Candidate structures", "Contexts", "Evidence notes"]
    )
    with overview:
        left, right = st.columns(2)
        with left:
            counts = features["confidence_symbol"].value_counts().reindex(CONFIDENCE_ORDER, fill_value=0).rename_axis("Original published notation").reset_index(name="Features")
            counts["Identification confidence"] = counts["Original published notation"].map(CONFIDENCE_LABELS)
            fig = px.bar(
                counts, x="Identification confidence", y="Features", color="Identification confidence", text="Features",
                color_discrete_map={CONFIDENCE_LABELS[key]: value for key, value in COLORS.items()},
                category_orders={"Identification confidence": [CONFIDENCE_LABELS[x] for x in CONFIDENCE_ORDER]},
                hover_data={"Original published notation": True},
                title=f"Identification confidence of the {len(features)} published GC-MS features in view",
            )
            fig.update_layout(showlegend=False, height=370, margin=dict(t=45, b=95, l=10, r=10), xaxis_tickangle=-18)
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("Published confidence definitions"):
                for symbol in CONFIDENCE_ORDER:
                    st.markdown(f"- **{CONFIDENCE_LABELS[symbol]}** — {CONFIDENCE_SOURCE_RANGES[symbol]}. Original published notation: `{symbol}`.")
        with right:
            widespread = features.copy()
            widespread["_bio_number"] = widespread["bio_id"].map(bio_id_number)
            widespread = widespread.sort_values(["contexts_present", "_bio_number"], ascending=[False, True], kind="stable").head(12)
            widespread["Feature"] = widespread["bio_id"] + " · " + widespread["published_annotation_display"]
            widespread["Identification confidence"] = widespread["confidence_symbol"].map(CONFIDENCE_LABELS)
            widespread = widespread.sort_values(["contexts_present", "_bio_number"], ascending=[True, False], kind="stable")
            fig = px.bar(
                widespread, x="contexts_present", y="Feature", orientation="h", color="Identification confidence",
                color_discrete_map={CONFIDENCE_LABELS[key]: value for key, value in COLORS.items()}, hover_data=["bio_id", "published_annotation_display"],
                title="Most widespread published features",
            )
            fig.update_layout(height=370, margin=dict(t=45, b=35, l=10, r=10), xaxis_title="Documented contexts present", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Contexts present means documentary feature-context presence, not biological replicate prevalence.")
        table_source = features.copy()
        table = researcher_table(
            table_source,
            {
                "bio_id": "Bio ID", "published_rt_exact": "Retention time", "published_annotation_display": "Published annotation",
                "identification_confidence": "Identification confidence", "published_confidence_notation": "Original published notation",
                "contexts_present": "Contexts present", "canonical_name": "Candidate chemical",
                "has_structure": "Curated structure",
            },
            always_keep=("bio_id", "published_rt_exact", "published_annotation_display", "identification_confidence", "published_confidence_notation", "contexts_present"),
        )
        st.dataframe(table, use_container_width=True, hide_index=True, height=340)
        st.download_button("Download filtered overview", features.to_csv(index=False), "voc_bio_v1_dashboard_features_filtered.csv", "text/csv")

    with structures:
        st.success(f"{len(CURATED_CANDIDATE_STRUCTURES)} publication-annotation candidates have validated molecular representations.")
        st.write(
            "These structures represent the chemicals named by the publication. Tentative peak identifications remain tentative. "
            "The two legacy manual-review structures are kept separately and are not counted here."
        )
        counts = features[features["has_structure"]]["confidence_symbol"].value_counts().reindex(["*", "?", "??"], fill_value=0)
        st.dataframe(
            [{"Identification confidence": CONFIDENCE_LABELS[symbol], "Curated candidate structures": int(counts[symbol])} for symbol in ["*", "?", "??"]],
            hide_index=True, use_container_width=True,
        )

    with context_tab:
        left, right = st.columns(2)
        with left:
            species_counts = contexts["canonical_species"].value_counts().rename_axis("Species").reset_index(name="Contexts")
            st.plotly_chart(px.bar(species_counts, x="Contexts", y="Species", orientation="h", title="Contexts by species"), use_container_width=True)
        with right:
            host_counts = contexts["host_plant_and_part"].value_counts().head(12).rename_axis("Host / part").reset_index(name="Contexts")
            st.plotly_chart(px.bar(host_counts, x="Contexts", y="Host / part", orientation="h", title="Contexts by host"), use_container_width=True)
        st.caption("Context counts describe documentary records; they are not biological-replicate counts.")

    with limitations:
        st.markdown("#### Interpretation-relevant limitations")
        st.markdown(
            "- Chemical annotations retain their published identification confidence.\n"
            "- Feature presence does not represent abundance, behavioral activity, or receptor binding.\n"
            "- Unresolved provenance is retained rather than inferred."
        )
        with st.expander("Historical reconstruction issues"):
            st.write("The historical 76-sample × 84-feature precursor to the published 63-observation × 81-feature layer remains only partly reconstructed.")
            st.dataframe(researcher_table(UNRESOLVED_RECORDS, {"category": "Issue type", "record": "Evidence gap", "status": "Status", "v1_handling": "Current handling"}, always_keep=("category", "record", "status"), minimum_supported_fraction=0.2), use_container_width=True, hide_index=True)
        with st.expander("Developer / dataset contract"):
            st.json(catalog_contract())
            st.dataframe(LEGACY_17[["legacy_name", "disposition"]], use_container_width=True, hide_index=True)
            st.dataframe(QUARANTINED_FIELDS[["dataset", "field", "publication_gate"]], use_container_width=True, hide_index=True)
