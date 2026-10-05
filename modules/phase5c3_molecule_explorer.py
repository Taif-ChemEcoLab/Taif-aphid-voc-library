"""Publication-annotation candidate structure explorer."""

import plotly.graph_objects as go
import streamlit as st

from data.v1_loader import CONFIDENCE_LABELS
from services.chemistry import descriptor_profile, legacy_review_structures, structured_chemicals
from utils.chem_utils import get_structure_image_url


def render():
    st.markdown("<div class='section-head'>Chemical Structure Explorer</div>", unsafe_allow_html=True)
    st.info(
        "The molecular structure represents the chemical named by the published annotation. "
        "For tentative GC-MS identifications, the structure does not constitute independent confirmation of peak identity."
    )
    all_chemicals = structured_chemicals()
    controls = st.columns([2, 2])
    selected_confidence = controls[0].multiselect(
        "Published confidence", ["*", "?", "??"], default=["*", "?", "??"],
        format_func=lambda value: CONFIDENCE_LABELS[value],
    )
    statuses = ["All"] + all_chemicals["identity_status_label"].drop_duplicates().tolist()
    identification_status = controls[1].selectbox("Identification status", statuses)
    chemicals = structured_chemicals(tuple(selected_confidence), identification_status)
    if chemicals.empty:
        st.warning("No curated candidate structures match the selected filters.")
        return
    st.caption(f"{len(chemicals)} curated publication-annotation candidate structures in this view.")
    chemical_options = chemicals["chemical_id"].tolist()
    requested_bio = st.session_state.get("chemical_bio")
    matching = chemicals.index[chemicals["bio_id"] == requested_bio].tolist() if requested_bio else []
    default_index = chemical_options.index(chemicals.loc[matching[0], "chemical_id"]) if matching else 0
    selected = st.selectbox(
        "Candidate chemical representation", chemical_options, index=default_index,
        format_func=lambda value: (
            f"{chemicals.loc[chemicals['chemical_id'] == value, 'bio_id'].iloc[0]} · "
            f"{chemicals.loc[chemicals['chemical_id'] == value, 'canonical_name'].iloc[0]}"
        ),
    )
    row = chemicals[chemicals["chemical_id"] == selected].iloc[0]
    structure, properties, provenance, legacy = st.tabs(["Structure", "Computed properties", "Identity and provenance", "Legacy manual review"])
    with structure:
        col1, col2 = st.columns([1, 2])
        with col1:
            url = get_structure_image_url(row["pubchem_cid"] or None, row["smiles"] or None, width=420, height=300)
            if url:
                st.image(url, use_column_width=True, caption=f"2D representation · {row['canonical_name']}")
        with col2:
            st.markdown(f"### {row['canonical_name']}")
            st.markdown(f"**Source Bio feature:** {row['bio_id']}")
            st.markdown(f"**Published annotation:** {row['published_annotation_exact']}")
            st.markdown(f"**Identity status:** {row['identity_status_label']}")
            metrics = st.columns(3)
            metrics[0].metric("Formula", row["formula"])
            metrics[1].metric("Molecular weight", row["molecular_weight"])
            metrics[2].metric("PubChem CID", row["pubchem_cid"])
            st.markdown("**SMILES**")
            st.code(row["smiles"], language=None)
            st.markdown("**InChIKey**")
            st.code(row["inchikey"], language=None)
            st.link_button("Open PubChem record", f"https://pubchem.ncbi.nlm.nih.gov/compound/{row['pubchem_cid']}")
            docking_panel = {
                "Bio4", "Bio8", "Bio9", "Bio13", "Bio17", "Bio20", "Bio21", "Bio22", "Bio31", "Bio36",
                "Bio38", "Bio39", "Bio42", "Bio47", "Bio49", "Bio51", "Bio53", "Bio55", "Bio56", "Bio59",
            }
            if row["bio_id"] in docking_panel and st.button("View docking evidence", key="chemical_to_docking"):
                st.session_state["docking_bio"] = row["bio_id"]
                st.session_state["docking_view"] = "VOC explorer"
                st.session_state["route_override"] = "Docking Predictions"
                st.rerun()
    with properties:
        values = descriptor_profile(selected)
        st.dataframe({"Descriptor": list(values), "Computed value": list(values.values())}, hide_index=True, use_container_width=True)
        axes = ["Molecular Weight", "LogP (Wildman-Crippen)", "TPSA (Å²)", "H-Bond Acceptors", "Rotatable Bonds"]
        ceilings = [700.0, 12.0, 140.0, 10.0, 25.0]
        normalized = [min(max(float(values.get(axis, 0)) / ceiling, 0), 1) for axis, ceiling in zip(axes, ceilings)]
        fig = go.Figure(go.Scatterpolar(r=normalized + normalized[:1], theta=axes + axes[:1], fill="toself", line_color="#166534"))
        fig.update_layout(title="Normalized descriptor profile", polar=dict(radialaxis=dict(range=[0, 1], visible=True)), height=390, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("This descriptor profile is chemical navigation, not an activity, volatility, or identity prediction.")
    with provenance:
        fields = [
            ("Identifier source", row["identifier_source"]),
            ("Retrieval / verification", row["identifier_verification_method"]),
            ("Chemical structure validation", row["chemical_structure_validation_status"]),
            ("GC-MS identification confidence", row["identity_status_label"]),
            ("Experimental identification status", row["published_identification_status"]),
        ]
        st.dataframe([{"Field": key, "Value": value} for key, value in fields if str(value).strip()], hide_index=True, use_container_width=True)
        st.caption(f"Original published notation: {row['published_confidence_notation']}")
        st.warning("A valid structure does not upgrade a tentative identification—whether higher or lower library match—and is not proof that the experimental feature is this chemical.")
    with legacy:
        legacy_rows = legacy_review_structures()
        st.write("These two structures predate the publication-annotation layer. They remain separately labeled and are not mapped to Bio features.")
        st.dataframe(legacy_rows[["canonical_name", "formula", "molecular_weight", "pubchem_cid", "structural_validation_status", "experimental_peak_identity_status"]], use_container_width=True, hide_index=True)
