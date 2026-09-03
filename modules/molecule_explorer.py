"""Molecule Explorer – full cheminformatics profile with PubChem structure image."""

import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.sample_data import VOCS
from utils.chem_utils import (
    get_structure_image_url,
    compute_descriptors,
    get_lipinski_verdict,
    RDKIT_AVAILABLE,
)


def render():
    st.markdown("<div class='section-head'>🔬 Molecule Explorer</div>", unsafe_allow_html=True)

    voc_names = VOCS["name"].tolist()
    selected  = st.selectbox("Select a VOC compound", voc_names)
    voc       = VOCS[VOCS["name"] == selected].iloc[0]

    bio_color = "#d1fae5" if voc["bioactivity"] == "Attractant" else "#fee2e2"
    bio_text  = "#065f46" if voc["bioactivity"] == "Attractant" else "#991b1b"

    st.markdown("<br>", unsafe_allow_html=True)
    col_img, col_info = st.columns([1, 2])

    with col_img:
        # ── Structure image from PubChem (cloud-safe) ─────────────────────────
        img_url = get_structure_image_url(
            pubchem_cid=voc.get("pubchem_cid"),
            smiles=voc.get("smiles"),
            width=360, height=260,
        )
        if img_url:
            st.image(
                img_url,
                caption=f"{voc['name']} — PubChem CID {voc['pubchem_cid']}",
                use_container_width=True,
            )
        else:
            st.info("Structure image unavailable")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**SMILES String**")
        st.markdown(
            f'<div class="smiles-box">{voc["smiles"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**InChIKey:** `{voc['inchikey']}`")
        st.markdown(
            f"**PubChem CID:** "
            f"[{voc['pubchem_cid']}]"
            f"(https://pubchem.ncbi.nlm.nih.gov/compound/{voc['pubchem_cid']})"
        )

    with col_info:
        st.markdown(f"## {voc['name']}")
        st.markdown(
            f'<span style="background:{bio_color};color:{bio_text};padding:4px 14px;'
            f'border-radius:20px;font-size:0.85rem;font-weight:700">'
            f'{voc["bioactivity"]}</span>'
            f'&nbsp;'
            f'<span style="background:#ede9fe;color:#4c1d95;padding:4px 14px;'
            f'border-radius:20px;font-size:0.85rem;font-weight:600">'
            f'{voc["class"]}</span>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Formula",       voc["formula"])
        c2.metric("MW (g/mol)",    voc["mw"])
        c3.metric("LogP",          voc["logp"])

        c4, c5, c6 = st.columns(3)
        c4.metric("Emission",      voc["emission_source"])
        c5.metric("Concentration", f"{voc['concentration_ppm']} ppm")
        c6.metric("Target",        voc["target"])

        st.markdown("---")
        st.markdown("**🦟 Associated Insect**")
        st.markdown(f"*{voc['insect']}*")
        st.markdown("**🌿 Host Plant**")
        st.markdown(f"*{voc['plant']}*")
        st.markdown("**🐝 Natural Enemy**")
        st.markdown(f"*{voc['natural_enemy']}*")
        st.markdown("**📝 Notes**")
        st.markdown(f"_{voc['notes']}_")

    # ── Computed Descriptors ──────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-head'>Computed Molecular Descriptors</div>",
        unsafe_allow_html=True,
    )

    if RDKIT_AVAILABLE:
        desc    = compute_descriptors(voc["smiles"])
        verdict = get_lipinski_verdict(voc["smiles"])

        col_desc, col_verdict = st.columns(2)

        with col_desc:
            st.markdown("**RDKit Descriptor Values**")
            if desc:
                d1, d2 = st.columns(2)
                items = list(desc.items())
                mid   = len(items) // 2
                for k, v in items[:mid]:
                    d1.metric(k, v)
                for k, v in items[mid:]:
                    d2.metric(k, v)
            else:
                st.warning("Could not parse SMILES for descriptor calculation.")

        with col_verdict:
            st.markdown("**VOC Volatility Profile**")
            if verdict:
                for rule, result in verdict.items():
                    if "VOC Volatility" in rule:
                        level = result
                        color = "#22c55e" if level == "HIGH" else "#f59e0b"
                        st.markdown(
                            f'<div style="background:{color};color:white;font-weight:700;'
                            f'font-size:1.1rem;padding:10px 16px;border-radius:8px;'
                            f'margin-bottom:12px">Volatility: {level}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"- **{rule}:** {result}")
            else:
                st.warning("Could not parse SMILES for volatility assessment.")

        # ── Radar chart ───────────────────────────────────────────────────────
        if desc:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Descriptor Radar Chart**")
            norms = {
                "MW":       (desc.get("Molecular Weight", 0), 500),
                "LogP":     (desc.get("LogP (Wildman-Crippen)", 0) + 2, 10),
                "TPSA":     (desc.get("TPSA (Å²)", 0), 150),
                "HBD":      (desc.get("H-Bond Donors", 0), 5),
                "HBA":      (desc.get("H-Bond Acceptors", 0), 10),
                "RotBonds": (desc.get("Rotatable Bonds", 0), 15),
                "Rings":    (desc.get("Ring Count", 0), 5),
                "Csp3":     (desc.get("Fraction Csp3", 0), 1),
            }
            cats = list(norms.keys())
            vals = [min(v / mx, 1.0) for v, mx in norms.values()]
            vals += [vals[0]]
            cats += [cats[0]]

            fig = go.Figure(go.Scatterpolar(
                r=vals, theta=cats, fill="toself",
                fillcolor="rgba(74,124,89,0.25)",
                line=dict(color="#1a3a2a", width=2),
                name=voc["name"],
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1]),
                           bgcolor="#f0fdf4"),
                showlegend=False, height=340,
                margin=dict(t=30, b=30),
                font=dict(family="Inter"),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        # RDKit not available — show stored values only
        st.info(
            "RDKit descriptors are not available in this environment. "
            "Showing stored database values only."
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("MW (g/mol)", voc["mw"])
        c2.metric("LogP",       voc["logp"])
        c3.metric("Formula",    voc["formula"])
