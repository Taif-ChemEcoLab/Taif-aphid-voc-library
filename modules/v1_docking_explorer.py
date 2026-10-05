"""Researcher-facing explorer for frozen Phase 5D VOC–OBP docking evidence."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from data.v1_loader import CONFIDENCE_LABELS
from services import frozen_docking as fd
from utils.chem_utils import get_structure_image_url


VIEWS = [
    "Overview", "Receptor × VOC matrix", "VOC explorer", "Receptor comparison",
    "Seed variability", "Pose explorer", "Docking validation", "Methods & provenance",
]
COLORS = {"Tier A": "#18794e", "Tier B": "#d97706"}


def _bio_number(value: str) -> int:
    return int(str(value).replace("Bio", ""))


def _ligand_label(row: pd.Series, include_tier: bool = True) -> str:
    tier = f" · {row['evidence_tier']}" if include_tier else ""
    return f"{row['bio_id']} · {row['canonical_candidate']}{tier}"


def _metric_row(items):
    # Limit each row to three metrics so values remain legible on narrow layouts.
    for start in range(0, len(items), 3):
        chunk = items[start:start + 3]
        columns = st.columns(len(chunk))
        for column, (label, value) in zip(columns, chunk):
            column.metric(label, value)


def _go_to(page: str, **state):
    st.session_state.update(state)
    st.session_state["main_navigation"] = page
    st.rerun()


def _overview():
    st.markdown("### Exploratory molecular docking")
    overview_metrics = [
        ("Experimental aphid OBPs", "2"), ("VOC candidates", "20"),
        ("VOC–OBP combinations", "40"), ("Independent runs", "200"), ("Retained poses", "2,000"),
    ]
    st.markdown(
        "<div class='docking-metric-grid'>" + "".join(
            f"<div class='docking-metric'><div>{label}</div><strong>{value}</strong></div>" for label, value in overview_metrics
        ) + "</div>", unsafe_allow_html=True,
    )
    st.caption(
        "The workflow was evaluated using independent experimental OBP–ligand complexes before "
        "application to this aphid OBP/VOC panel. Docking scores are computational predictions, "
        "not experimental binding affinities or measures of behavioral activity."
    )
    st.markdown("#### Production proteins")
    receptor_cards = [
        ("MvicOBP3", "Megoura viciae", "4Z39", "1.30 Å", "8.284, 6.721, 22.849", "27.811 × 29.469 × 22.853 Å"),
        ("NribOBP3", "Nasonovia ribisnigri", "4Z45", "2.02 Å", "21.128, −20.253, 1.603", "22.254 × 27.693 × 26.435 Å"),
    ]
    card_html = "<div class='receptor-card-grid'>"
    for name, species, pdb, resolution, center, size in receptor_cards:
        card_html += (
            f"<div class='receptor-card'><h4>{name}</h4><i>{species}</i>"
            f"<p><b>PDB:</b> {pdb} · <b>Method:</b> X-ray diffraction · <b>Resolution:</b> {resolution}</p>"
            f"<p><b>Search box:</b> center ({center}); dimensions {size}</p>"
            "<div class='pass-chip'>Production preparation: PASS</div></div>"
        )
    st.markdown(card_html + "</div>", unsafe_allow_html=True)
    st.markdown("#### Descriptive panel observations")
    c1, c2 = st.columns(2)
    with c1:
        st.info("**Bio59 · β-selinene** had the most negative median docking score in this computational panel for both OBPs.")
    with c2:
        st.info("**Bio42 · caprolactam** had the least negative median docking score in this computational panel for both OBPs.")
    st.caption("These observations are docking-score descriptions, not biological ligand rankings.")


def _matrix():
    st.markdown("### Receptor × VOC matrix")
    pairs = fd.pair_results().sort_values("bio_id", key=lambda s: s.map(_bio_number))
    pairs = pairs.assign(
        identification_confidence=pairs["gcms_confidence"].map(CONFIDENCE_LABELS),
        published_confidence_notation=pairs["gcms_confidence"],
    )
    labels = pairs[["bio_id", "ligand_name"]].drop_duplicates().sort_values("bio_id", key=lambda s: s.map(_bio_number))
    labels["display"] = labels["bio_id"] + " · " + labels["ligand_name"]
    order = labels["bio_id"].tolist()
    display = labels.set_index("bio_id")["display"].to_dict()
    z = pairs.pivot(index="receptor_name", columns="bio_id", values="median_rank1_score").reindex(index=["MvicOBP3", "NribOBP3"], columns=order)
    custom_columns = ["identification_confidence", "published_confidence_notation", "evidence_tier", "mean_rank1_score", "rank1_score_sd", "rank1_score_range", "final_classification"]
    custom = []
    for receptor in z.index:
        indexed = pairs[pairs["receptor_name"] == receptor].set_index("bio_id").reindex(order)
        custom.append(indexed[custom_columns].to_numpy())
    show_ids = st.toggle("Show Bio IDs in column labels", value=True)
    x_labels = [display[bio] if show_ids else display[bio].split(" · ", 1)[1] for bio in order]
    fig = go.Figure(go.Heatmap(
        z=z.to_numpy(), x=x_labels, y=z.index.tolist(), customdata=custom,
        colorscale="Viridis_r", colorbar_title="kcal/mol",
        hovertemplate=(
            "<b>%{x}</b><br>OBP: %{y}<br>Identification confidence: %{customdata[0]}"
            "<br>Original published notation: %{customdata[1]}<br>Evidence: %{customdata[2]}<br>Median: %{z:.3f} kcal/mol"
            "<br>Mean: %{customdata[3]:.3f}<br>SD: %{customdata[4]:.3f}"
            "<br>Range: %{customdata[5]:.3f}<br>Stability: %{customdata[6]}<extra></extra>"
        ),
    ))
    fig.update_layout(height=460, margin=dict(l=10, r=20, t=45, b=155), xaxis_tickangle=-55,
                      title="Median rank-1 Vina docking score across five independent seeds")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("More negative values are lower Vina docking scores. They are not experimental affinity measurements.")


def _selected_bio(ligands: pd.DataFrame) -> str:
    options = ligands["bio_id"].tolist()
    requested = st.query_params.get("bio") or st.session_state.get("docking_bio", "Bio39")
    index = options.index(requested) if requested in options else 0
    return st.selectbox(
        "VOC candidate", options, index=index, key="docking_ligand_select",
        format_func=lambda bio: _ligand_label(ligands.loc[ligands["bio_id"] == bio].iloc[0]),
    )


def _voc_explorer():
    st.markdown("### VOC docking explorer")
    ligands = fd.ligand_metadata()
    bio_id = _selected_bio(ligands)
    st.session_state["docking_bio"] = bio_id
    ligand = ligands.loc[ligands["bio_id"] == bio_id].iloc[0]
    identity, docking = st.columns([1, 1.5])
    with identity:
        st.markdown("#### GC-MS identification evidence")
        image = get_structure_image_url(ligand.get("pubchem_cid"), ligand.get("smiles"), width=420, height=300)
        if image:
            st.image(image, use_column_width=True, caption=f"Candidate structure · {ligand['canonical_candidate']}")
        st.write(f"**{bio_id} · {ligand['canonical_candidate']}**")
        st.write(f"Published annotation: {ligand['published_annotation']}")
        st.write(f"Identification confidence: **{CONFIDENCE_LABELS[ligand['confidence']]}**")
        st.caption(f"Original published notation: {ligand['confidence']} · Evidence tier: {ligand['evidence_tier']}")
        st.write(f"Formula: {ligand['formula']} · Molecular weight: {ligand['molecular_weight']} g/mol")
        st.write(f"PubChem CID: {ligand['pubchem_cid']} · Class: {ligand.get('chemical_class', 'Not frozen')}")
        st.code(str(ligand["smiles"]), language=None)
        contexts = str(ligand.get("biological_contexts", "")).split(";")
        with st.expander("Published biological contexts"):
            for context in contexts:
                if context.strip():
                    st.write("• " + context.strip())
        if st.button("View chemical evidence", key="to_chemical"):
            _go_to("Chemical Structure Explorer", chemical_bio=bio_id)
    with docking:
        st.markdown("#### Docking prediction evidence")
        pair_rows = fd.pair_results().query("bio_id == @bio_id")
        seeds = fd.rank1_results().query("bio_id == @bio_id")
        for receptor in ["MvicOBP3", "NribOBP3"]:
            pair = pair_rows.loc[pair_rows["receptor_name"] == receptor].iloc[0]
            receptor_seeds = seeds.loc[seeds["receptor_name"] == receptor].sort_values("seed")
            st.markdown(f"**{receptor}**")
            _metric_row([
                ("Median", f"{pair['median_rank1_score']:.3f} kcal/mol"),
                ("Mean", f"{pair['mean_rank1_score']:.3f}"),
                ("SD", f"{pair['rank1_score_sd']:.3f}"),
                ("Range", f"{pair['rank1_score_range']:.3f}"),
            ])
            st.caption(f"Five rank-1 scores: {', '.join(f'{x:.3f}' for x in receptor_seeds['vina_score'])} · {pair['final_classification']}")
        representative = fd.representative_complexes().query("bio_id == @bio_id")
        st.write(f"Representative frozen pose available: **{'Yes' if not representative.empty else 'No'}**")
        st.caption("GC-MS confidence is unchanged by the docking result.")
    if bio_id in {"Bio17", "Bio4", "Bio21"}:
        st.info(fd.STEREO_CAVEAT)


def _comparison():
    st.markdown("### Aphid OBP docking-profile comparison")
    data = fd.table("comparison").copy()
    data["label"] = data["bio_id"] + " · " + data["canonical_candidate"]
    data["highlight"] = data["bio_id"].map(lambda value: "Bio39 contrast" if value == "Bio39" else "Other VOC")
    fig = px.scatter(data, x="MvicOBP3", y="NribOBP3", color="highlight", hover_name="label",
                     color_discrete_map={"Bio39 contrast": "#c2410c", "Other VOC": "#277da1"},
                     labels={"MvicOBP3": "MvicOBP3 median Vina score (kcal/mol)", "NribOBP3": "NribOBP3 median Vina score (kcal/mol)"})
    low = min(data["MvicOBP3"].min(), data["NribOBP3"].min()) - .15
    high = max(data["MvicOBP3"].max(), data["NribOBP3"].max()) + .15
    fig.add_shape(type="line", x0=low, y0=low, x1=high, y1=high, line=dict(color="#777", dash="dash"))
    fig.update_layout(height=560, legend_title_text="", xaxis_range=[low, high], yaxis_range=[low, high])
    st.plotly_chart(fig, use_container_width=True)
    _metric_row([("Pearson r", "0.9600100221"), ("VOC candidates", "20"), ("Excluded", "0")])
    st.write("The two aphid OBPs showed broadly similar predicted docking-score profiles across the 20-VOC panel.")
    st.info("**Bio39 · methyl salicylate** was the largest descriptive contrast: Mvic − Nrib = **+0.525 kcal/mol**; the NribOBP3 score was more negative.")
    st.caption("This is a computational docking contrast and does not demonstrate experimental OBP preference.")


def _variability():
    st.markdown("### Five-seed variability")
    pairs = fd.pair_results()
    controls = st.columns(3)
    receptor = controls[0].selectbox("Aphid OBP", ["MvicOBP3", "NribOBP3"], key="var_receptor")
    tier = controls[1].selectbox("Evidence tier", ["All", "Tier A", "Tier B"], key="var_tier")
    stability = controls[2].selectbox("Post hoc classification", ["All", "STABLE", "VARIABLE"], key="var_stability")
    selected = pairs[pairs["receptor_name"] == receptor]
    if tier != "All":
        selected = selected[selected["evidence_tier"] == tier]
    if stability != "All":
        selected = selected[selected["final_classification"] == stability]
    allowed = selected["bio_id"].tolist()
    bio_id = st.selectbox("VOC", allowed, format_func=lambda bio: selected.loc[selected["bio_id"] == bio, "ligand_name"].iloc[0] + f" · {bio}")
    row = selected[selected["bio_id"] == bio_id].iloc[0]
    seed_rows = fd.rank1_results().query("receptor_name == @receptor and bio_id == @bio_id").sort_values("seed")
    seed_rows = seed_rows.assign(seed_label=seed_rows["seed"].map(lambda value: str(int(value))))
    fig = px.bar(seed_rows, x="seed_label", y="vina_score", text="vina_score",
                 labels={"seed_label": "Independent seed", "vina_score": "Rank-1 Vina docking score (kcal/mol)"},
                 color_discrete_sequence=["#2a9d8f"])
    fig.add_hline(y=row["median_rank1_score"], line_dash="dash", annotation_text="Pair median")
    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=seed_rows["seed_label"].tolist())
    fig.update_layout(height=440)
    st.plotly_chart(fig, use_container_width=True)
    _metric_row([("Median", f"{row['median_rank1_score']:.3f}"), ("SD", f"{row['rank1_score_sd']:.3f}"),
                 ("Range", f"{row['rank1_score_range']:.3f}"), ("Classification", row["final_classification"])])
    if row["final_classification"] == "VARIABLE":
        st.info(f"Flagged by the uniform post hoc rule: {row['criterion']}")
    st.caption("Seeds are independent computational docking runs, not biological replicates. No biological p-values are calculated.")
    st.markdown("#### Post hoc descriptive docking reproducibility")
    st.write("**37 stable · 3 variable**")
    st.write("Variable pairs: MvicOBP3–Bio42; NribOBP3–Bio49; NribOBP3–Bio56.")
    st.caption("This rule was applied uniformly after production docking; it was not a prospectively frozen Phase 5D.2 validation criterion.")


def _pose_viewer(receptor_path: Path, pose_text: str):
    try:
        import py3Dmol
        receptor_text = receptor_path.read_text(encoding="utf-8", errors="replace")
        receptor_format = "pdbqt" if receptor_path.suffix.lower() == ".pdbqt" else "pdb"
        viewer = py3Dmol.view(width=900, height=520)
        viewer.addModel(receptor_text, receptor_format)
        viewer.setStyle({"model": 0}, {"cartoon": {"color": "#9ecae1", "opacity": 0.75}})
        viewer.addModel(pose_text, "pdbqt")
        viewer.setStyle({"model": 1}, {"stick": {"colorscheme": "greenCarbon", "radius": 0.22}, "sphere": {"scale": 0.25}})
        viewer.zoomTo({"model": 1})
        components.html(viewer._make_html(), height=540, scrolling=False)
    except Exception as exc:
        st.warning(f"Interactive molecular viewer unavailable ({exc}). The frozen pose metadata remain available below.")


def _pose_explorer():
    st.markdown("### Representative predicted pose explorer")
    reps = fd.representative_complexes().copy()
    reps["display"] = reps["receptor_name"] + " · " + reps["bio_id"] + " · " + reps["ligand_name"]
    receptor = st.selectbox("Aphid OBP", ["MvicOBP3", "NribOBP3"], key="pose_receptor")
    subset = reps[reps["receptor_name"] == receptor]
    selected = st.selectbox("Frozen representative complex", subset.index.tolist(),
                            format_func=lambda idx: subset.loc[idx, "display"])
    row = subset.loc[selected]
    pose_text = fd.filtered_pose_text(str(row["representative_pose_path"]), str(row["bio_id"]))
    receptor_path = fd.prepared_receptor_path(str(row["PDB_ID"]))
    st.caption("Blue cartoon: prepared experimental receptor structure · green sticks: predicted ligand pose")
    _pose_viewer(receptor_path, pose_text)
    _metric_row([("Seed", int(row["representative_seed"])), ("Pose rank", int(row["representative_pose_rank"])),
                 ("Vina score", f"{row['representative_score']:.3f} kcal/mol")])
    st.write(f"**Selection rationale:** {row['selection_reason']}")
    interactions = fd.table("interactions").query("PDB_ID == @row.PDB_ID and bio_id == @row.bio_id and seed == @row.representative_seed")
    if interactions.empty:
        st.info("No corrected representative interaction rows are frozen for this complex.")
    else:
        shown = interactions[["residue", "receptor_atom", "ligand_atom", "minimum_strict_heavy_atom_distance_A", "interaction_types", "caveat"]].copy()
        shown.columns = ["Residue", "Receptor atom", "Ligand atom", "Heavy-atom distance (Å)", "Geometric screen", "Interpretive caveat"]
        st.dataframe(shown, hide_index=True, use_container_width=True)
    if row["bio_id"] == "Bio38":
        st.caption("Bio38 display and geometry exclude Meeko G0 ring-closure dummy atoms; CG0 remains a real carbon atom.")


def _validation():
    st.markdown("### Docking validation")
    st.write("The three systems are shown separately because the development control and held-out systems have different evidentiary roles.")
    cards = st.columns(3)
    content = [
        ("1DQE · bombykol", "Development control", "0/5", "1/5", "Minimum observed RMSD", "1.7936 Å"),
        ("2WC6 · bombykol", "Held-out", "1/5", "5/5", "Median best-of-10 RMSD", "1.3438 Å"),
        ("3N7H · DEET", "Held-out", "5/5", "5/5", "Median rank-1 RMSD", "0.6453 Å"),
    ]
    for card, values in zip(cards, content):
        title, role, rank1, best10, rmsd_label, rmsd = values
        with card:
            st.markdown(f"#### {title}")
            st.caption(role)
            st.metric("Rank-1 recovery", rank1)
            st.metric("Best-of-10 recovery", best10)
            st.metric(rmsd_label, rmsd)
    st.info("The protocol showed reproducible near-native pose sampling in both held-out systems, while rank-1 performance differed between systems.")
    st.caption("This supports exploratory pose generation, not experimental affinity prediction. The 1DQE development system was not a successful validation system.")
    with st.expander("Frozen validation table"):
        st.dataframe(fd.validation_results(), hide_index=True, use_container_width=True)


def _methods():
    st.markdown("### Methods & provenance")
    protocol = fd.protocol()
    _metric_row([("Vina", "1.2.7"), ("Exhaustiveness", "32"), ("Requested modes", "20"),
                 ("Energy range", "4 kcal/mol"), ("Runs / poses", "200 / 2,000")])
    st.write("**Seeds:** 42, 2026, 104729, 271828, 314159")
    st.write("**Protocol:** phase5d2_protocol_v1.0")
    st.code("0a80027f93fd7450d942ab98ce9fba1a70c743996d13e18887fd45725fd9fc19", language=None)
    with st.expander("Preparation and pocket definition"):
        st.write(
            "Ligands were independently embedded with ETKDGv3, optimized under the frozen workflow, "
            "charged and atom-typed using validated Meeko preparation. Receptors were cleaned, "
            "hydrogenated at the documented pH assumption, assigned Gasteiger charges, and converted "
            "to genuine AutoDock-compatible PDBQT files. Search boxes were prospectively derived from "
            "documented OBP3 surface-groove residues with a 5 Å margin; they were not tuned to production scores."
        )
    with st.expander("4Z45 preparation caveat"):
        st.write(
            "Generated terminal OXT geometry at ASP118 required a technical correction during preparation. "
            "Residues 119–121 were unresolved in the experimental structure and were not modeled; they lie "
            "outside the defined docking pocket. Receptor identity, search box, and Vina parameters were unchanged."
        )
    with st.expander("Molecular-size diagnostic"):
        st.write("MvicOBP3: Spearman ρ = **−0.4907374871**, n = **20**, using ligand heavy-atom count.")
        st.caption("This moderate association may reflect size-related scoring bias. Scores were not corrected, and the relationship is not biological evidence.")
    with st.expander("Primary structural and method records"):
        st.markdown(
            "[PDB 4Z39](https://www.rcsb.org/structure/4Z39) · "
            "[PDB 4Z45](https://www.rcsb.org/structure/4Z45) · "
            "[PDB 1DQE](https://www.rcsb.org/structure/1DQE) · "
            "[PDB 2WC6](https://www.rcsb.org/structure/2WC6) · "
            "[PDB 3N7H](https://www.rcsb.org/structure/3N7H) · "
            "[AutoDock Vina documentation](https://autodock-vina.readthedocs.io/)"
        )
    st.markdown("#### Frozen scientific downloads")
    st.info(
        "These exact frozen source tables retain their original confidence fields. In those files, `*` means "
        "Authentic-standard supported; `?` means Tentative identification, higher library match; `??` means "
        "Tentative identification, lower library match; and `UK` means Unknown feature. The files are served "
        "unchanged to preserve the Phase 5D scientific freeze."
    )
    columns = st.columns(2)
    for index, (label, key) in enumerate(fd.DISPLAY_DOWNLOADS.items()):
        path = fd.SOURCES[key]
        columns[index % 2].download_button(
            label, data=fd.source_bytes(key), file_name=path.name, mime="text/csv", key=f"download_{key}",
            help="Exact bytes from the frozen authoritative source table.",
        )
    st.caption("Downloads are served directly from frozen authoritative files; headline values are not independently recomputed for display.")


def render():
    st.markdown("""
    <style>
    .docking-metric-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:.8rem; margin:.5rem 0 1rem; }
    .docking-metric { border:1px solid #d9e6de; border-radius:9px; padding:.75rem .9rem; background:#f7fbf8; }
    .docking-metric div { color:#4b6355; font-size:.78rem; min-height:2.2em; }
    .docking-metric strong { display:block; color:#173d2a; font-size:1.85rem; font-weight:500; margin-top:.15rem; }
    .receptor-card-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:1rem; margin-bottom:1.2rem; }
    .receptor-card { border:1px solid #d9e6de; border-radius:10px; padding:1rem; background:white; }
    .receptor-card h4 { margin:0 0 .25rem; }
    .receptor-card p { line-height:1.55; }
    .pass-chip { color:#166534; background:#e8f7ed; border-radius:7px; padding:.55rem .7rem; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div class='section-head'>Multi-Receptor Docking Explorer</div>", unsafe_allow_html=True)
    try:
        fd.assert_scientific_contract()
    except Exception as exc:
        st.error(f"Frozen docking evidence failed its application consistency gate: {exc}")
        st.stop()
    st.caption("Validated exploratory VOC–OBP docking evidence · Phase 5D scientific freeze")
    slug_views = {view.lower().replace(" ", "-").replace("×", "x").replace("&", "and"): view for view in VIEWS}
    requested = slug_views.get(st.query_params.get("docking", ""), st.session_state.get("docking_view", "Overview"))
    view = st.selectbox("Docking view", VIEWS, index=VIEWS.index(requested) if requested in VIEWS else 0, key="docking_view_selector")
    st.session_state["docking_view"] = view
    renderers = {
        "Overview": _overview,
        "Receptor × VOC matrix": _matrix,
        "VOC explorer": _voc_explorer,
        "Receptor comparison": _comparison,
        "Seed variability": _variability,
        "Pose explorer": _pose_explorer,
        "Docking validation": _validation,
        "Methods & provenance": _methods,
    }
    renderers[view]()
    st.markdown("---")
    st.caption(
        "Exploratory molecular docking only. Results do not establish affinity, Kd, Ki, activation, inhibition, "
        "attraction, repellency, ecological function, pest-control efficacy, or chemical identity."
    )
