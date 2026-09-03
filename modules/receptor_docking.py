"""Read-only receptor, ligand-evidence, and docking curation review."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CURATION_DIR = PROJECT_ROOT / "curation_drafts"


@st.cache_data(show_spinner=False)
def _load_csv(name: str) -> pd.DataFrame:
    path = CURATION_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def _status_bucket(status: str) -> str:
    value = str(status).lower()
    if value.startswith("resolved") or "verified" in value or "ready" in value:
        if "partial" in value or "needs" in value:
            return "Partial"
        return "Verified"
    if "partial" in value:
        return "Partial"
    if "indirect" in value or "emission_record" in value:
        return "Context"
    if value in ("", "tbd") or "needs" in value or "open" in value:
        return "Open"
    return "Context"


def _is_evidence_ready(status: str) -> bool:
    value = str(status).lower()
    return (
        "verified" in value
        or value.startswith("resolved")
        or "table_value_verified" in value
        or "figure_value_verified" in value
    ) and "needs" not in value


def _is_protein_ready(status: str) -> bool:
    value = str(status).lower()
    return (
        ("verified" in value or "ready" in value)
        and "partial" not in value
        and "needs" not in value
    )


def _style_status(val: str) -> str:
    bucket = _status_bucket(val)
    colors = {
        "Verified": "background-color:#d1fae5;color:#065f46;font-weight:600",
        "Partial": "background-color:#fef3c7;color:#92400e;font-weight:600",
        "Open": "background-color:#fee2e2;color:#991b1b;font-weight:600",
        "Context": "background-color:#e0f2fe;color:#075985;font-weight:600",
    }
    return colors.get(bucket, "")


def _with_protein_gate(evidence: pd.DataFrame, proteins: pd.DataFrame) -> pd.DataFrame:
    if evidence.empty:
        return evidence

    df = evidence.copy()
    df["status_bucket"] = df["validation_status"].map(_status_bucket)
    df["evidence_value_verified"] = df["validation_status"].map(_is_evidence_ready)

    if proteins.empty:
        df["protein_status"] = ""
        df["protein_ready"] = False
    else:
        protein_gate = proteins[["protein_id", "validation_status"]].rename(
            columns={"validation_status": "protein_status"}
        )
        df = df.merge(protein_gate, on="protein_id", how="left")
        df["protein_status"] = df["protein_status"].fillna("")
        df["protein_ready"] = df["protein_status"].map(_is_protein_ready)

    receptor_categories = {
        "direct_receptor",
        "protein_binding",
        "protein_binding_behavior",
        "protein_binding_structure",
        "parasitoid_protein_binding",
    }
    df["ready_for_confirmed_view"] = (
        df["evidence_category"].isin(receptor_categories)
        & df["evidence_value_verified"]
        & df["protein_ready"]
        & ~df["quantitative_value"].astype(str).str.upper().eq("TBD")
    )
    return df


def _metric_row(evidence: pd.DataFrame, proteins: pd.DataFrame, docking: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evidence Rows", len(evidence))
    c2.metric("Proteins", len(proteins))
    c3.metric("Docking Records", len(docking))
    c4.metric("Confirmed Subset", int(evidence["ready_for_confirmed_view"].sum()) if not evidence.empty else 0)


def _render_status_chart(evidence: pd.DataFrame) -> None:
    if evidence.empty:
        return
    chart_df = evidence["status_bucket"].value_counts().rename_axis("status").reset_index(name="count")
    fig = px.bar(
        chart_df,
        x="status",
        y="count",
        color="status",
        text="count",
        color_discrete_map={
            "Verified": "#22c55e",
            "Partial": "#f59e0b",
            "Open": "#ef4444",
            "Context": "#0ea5e9",
        },
    )
    fig.update_layout(
        height=260,
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False,
        xaxis_title="",
        yaxis_title="Rows",
        font=dict(family="Inter"),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Counts curation status buckets for receptor-ligand evidence; it reflects "
        "review readiness, not docking accuracy or biological validation."
    )


def _select_existing_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return df[[col for col in columns if col in df.columns]]


def render():
    st.markdown("<div class='section-head'>Receptor Docking & Evidence</div>", unsafe_allow_html=True)

    evidence = _load_csv("ligand_evidence.csv")
    proteins = _load_csv("olfactory_proteins.csv")
    ligands = _load_csv("voc_ligands.csv")
    organisms = _load_csv("organisms.csv")
    docking = _load_csv("docking_results.csv")

    if evidence.empty and proteins.empty and docking.empty:
        st.error("Receptor-ligand evidence data is not available in this deployment.")
        return

    evidence = _with_protein_gate(evidence, proteins)
    _metric_row(evidence, proteins, docking)

    st.markdown("<br>", unsafe_allow_html=True)
    _render_status_chart(evidence)

    tab_confirmed, tab_evidence, tab_proteins, tab_docking, tab_ligands = st.tabs(
        ["Confirmed Subset", "Evidence", "Proteins", "Docking", "Ligands"]
    )

    with tab_confirmed:
        confirmed = evidence[evidence["ready_for_confirmed_view"]].copy()
        cols = [
            "evidence_id",
            "ligand_id",
            "organism_id",
            "protein_id",
            "evidence_category",
            "assay_type",
            "quantitative_value",
            "units",
            "citation_key",
            "validation_status",
            "protein_status",
        ]
        st.dataframe(confirmed[cols], use_container_width=True, hide_index=True, height=360)
        st.download_button(
            "Download confirmed receptor evidence CSV",
            data=confirmed[cols].to_csv(index=False),
            file_name="confirmed_receptor_evidence.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tab_evidence:
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox(
                "Evidence Category",
                ["All"] + sorted(evidence["evidence_category"].dropna().unique().tolist()),
            )
        with col2:
            bucket = st.selectbox("Status", ["All", "Verified", "Partial", "Open", "Context"])
        with col3:
            confirmed_only = st.checkbox("Confirmed subset only", value=False)

        df = evidence.copy()
        if category != "All":
            df = df[df["evidence_category"] == category]
        if bucket != "All":
            df = df[df["status_bucket"] == bucket]
        if confirmed_only:
            df = df[df["ready_for_confirmed_view"]]

        cols = [
            "evidence_id",
            "ligand_id",
            "organism_id",
            "protein_id",
            "evidence_category",
            "assay_type",
            "result_summary",
            "quantitative_value",
            "units",
            "citation_key",
            "validation_status",
            "protein_status",
        ]
        st.dataframe(
            df[cols].style.map(_style_status, subset=["validation_status", "protein_status"]),
            use_container_width=True,
            hide_index=True,
            height=520,
        )
        st.download_button(
            "Download filtered docking evidence CSV",
            data=df[cols].to_csv(index=False),
            file_name="filtered_docking_evidence.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tab_proteins:
        cols = [
            "protein_id",
            "organism_id",
            "protein_family",
            "protein_name",
            "ortholog_group",
            "accession",
            "structure_status",
            "structure_id",
            "evidence_role",
            "validation_status",
            "notes",
        ]
        st.dataframe(
            proteins[cols].style.map(_style_status, subset=["validation_status"]),
            use_container_width=True,
            hide_index=True,
            height=520,
        )
        st.download_button(
            "Download olfactory proteins CSV",
            data=proteins[cols].to_csv(index=False),
            file_name="olfactory_proteins.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tab_docking:
        if docking.empty:
            st.info("No docking records loaded.")
        else:
            cols = [
                "docking_id",
                "ligand_id",
                "protein_id",
                "organism_id",
                "docking_source",
                "confidence",
                "receptor_structure",
                "ligand_structure",
                "docking_engine",
                "box_center_x",
                "box_center_y",
                "box_center_z",
                "box_size_x",
                "box_size_y",
                "box_size_z",
                "exhaustiveness",
                "best_affinity_kcal_mol",
                "estimated_ki_um",
                "top_contact_residues",
                "cavity_residues",
                "validation_status",
                "notes",
            ]
            st.dataframe(_select_existing_columns(docking, cols), use_container_width=True, hide_index=True, height=480)
            st.caption(
                "Lists curated receptor-ligand docking records and affinity estimates; "
                "these scores prioritize hypotheses and do not replace binding or behavioral assays."
            )
            docking_export = _select_existing_columns(docking, cols)
            st.download_button(
                "Download docking records CSV",
                data=docking_export.to_csv(index=False),
                file_name="docking_records.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with tab_ligands:
        if ligands.empty:
            st.info("No ligand curation records loaded.")
        else:
            st.dataframe(ligands, use_container_width=True, hide_index=True, height=480)
        if not organisms.empty:
            st.markdown("**Organisms**")
            st.dataframe(organisms, use_container_width=True, hide_index=True, height=260)
