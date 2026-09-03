"""Local research assistant for the public/offline version of the VOC library."""

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.sample_data import BIOASSAYS, INSECTS, PLANTS, VOCS


CURATION_DIR = Path(__file__).resolve().parents[3] / "curation_drafts"

QUESTION_BANK = {
    "library_scope": "What does this VOC library contain?",
    "top_vocs": "Which VOCs have the strongest quantitative signal?",
    "bioactivity": "Which VOCs are annotated as attractants or repellents?",
    "volatile": "Which compounds look most VOC-like by molecular properties?",
    "plants_insects": "Which plants and insects are represented?",
    "natural_enemies": "Which natural enemies are linked to the VOC records?",
    "similarity": "How should I interpret the Structural Similarity Explorer?",
    "docking": "What does the receptor docking evidence mean in this version?",
}


def _fmt_list(values, limit=8):
    clean = [str(v) for v in values if pd.notna(v) and str(v).strip()]
    if not clean:
        return "not reported"
    shown = clean[:limit]
    suffix = f"; plus {len(clean) - limit} more" if len(clean) > limit else ""
    return ", ".join(shown) + suffix


def _top_unique(frame, value_col, group_cols, limit=8):
    cols = group_cols + [value_col]
    data = frame[cols].dropna(subset=[value_col]).copy()
    if data.empty:
        return data
    data = data.sort_values(value_col, ascending=False)
    return data.drop_duplicates(group_cols).head(limit)


def _response_library_scope():
    voc_count = VOCS["name"].nunique()
    record_count = len(VOCS)
    plant_count = VOCS["plant"].nunique()
    insect_count = VOCS["insect"].nunique()
    class_count = VOCS["class"].nunique()
    assay_count = len(BIOASSAYS)

    top_classes = VOCS["class"].value_counts().head(6)
    class_lines = "\n".join(f"- {name}: {count} records" for name, count in top_classes.items())

    return (
        f"The library contains {record_count} VOC occurrence records representing "
        f"{voc_count} unique VOC names, {class_count} chemical classes, "
        f"{plant_count} plant entries, {insect_count} insect entries, and "
        f"{assay_count} linked bioassay/quantification records.\n\n"
        "Most represented chemical classes:\n"
        f"{class_lines}\n\n"
        "Use this page as a guided index over the internal dataset. It does not call "
        "an external language model or web service."
    )


def _response_top_vocs():
    top = _top_unique(
        BIOASSAYS,
        "effect_size",
        ["voc_name", "insect", "response", "concentration_ppm", "n_replicates"],
        limit=10,
    )
    if top.empty:
        return "No quantitative effect-size records are available in the bundled dataset."

    lines = []
    for _, row in top.iterrows():
        lines.append(
            f"- {row['voc_name']} against {row['insect']}: "
            f"{row['response']}, effect size {row['effect_size']:.2f}, "
            f"{row['concentration_ppm']:.2f} ppm, n={int(row['n_replicates'])}"
        )

    return (
        "The strongest quantitative signals in this version are ranked by the "
        "internal `effect_size` field, which is derived from the bundled GC-MS/"
        "bioassay table rather than a validated prediction.\n\n"
        + "\n".join(lines)
        + "\n\nInterpret these as prioritization signals for review, not as final "
        "validated efficacy rankings."
    )


def _response_bioactivity():
    counts = VOCS.groupby(["bioactivity", "class"]).size().reset_index(name="records")
    counts = counts.sort_values(["bioactivity", "records"], ascending=[True, False])

    sections = []
    for bioactivity, part in counts.groupby("bioactivity"):
        top_classes = ", ".join(
            f"{row['class']} ({row['records']})" for _, row in part.head(5).iterrows()
        )
        examples = VOCS[VOCS["bioactivity"] == bioactivity]["name"].drop_duplicates().head(8)
        sections.append(
            f"**{bioactivity}**\n"
            f"- Main classes: {top_classes}\n"
            f"- Example VOCs: {_fmt_list(examples)}"
        )

    return (
        "Bioactivity annotations in this version are dataset annotations and should be "
        "read together with insect, plant, concentration, and replicate context.\n\n"
        + "\n\n".join(sections)
    )


def _response_volatile():
    data = VOCS[["name", "class", "mw", "logp", "plant", "insect"]].dropna(
        subset=["mw", "logp"]
    )
    data = data[(data["mw"] < 180) & (data["logp"] <= 4.5)].copy()
    data = data.sort_values(["mw", "logp"]).drop_duplicates(["name"]).head(10)

    if data.empty:
        return "No records match the simple VOC-like molecular-property filter."

    lines = []
    for _, row in data.iterrows():
        lines.append(
            f"- {row['name']} ({row['class']}): MW {row['mw']:.2f}, "
            f"LogP {row['logp']:.2f}; observed with {row['insect']} / {row['plant']}"
        )

    return (
        "A conservative VOC-like screen uses low molecular weight and moderate "
        "hydrophobicity. Here I filtered for MW < 180 and LogP <= 4.5.\n\n"
        + "\n".join(lines)
        + "\n\nThis is a physicochemical screen only. Actual volatility depends on "
        "vapor pressure, matrix, temperature, and sampling method."
    )


def _response_plants_insects():
    plant_examples = PLANTS["species"].drop_duplicates().head(10)
    insect_examples = INSECTS["species"].drop_duplicates().head(10)

    top_pairs = (
        VOCS.groupby(["plant", "insect"])
        .size()
        .reset_index(name="voc_records")
        .sort_values("voc_records", ascending=False)
        .head(8)
    )
    pair_lines = "\n".join(
        f"- {row['plant']} / {row['insect']}: {row['voc_records']} VOC records"
        for _, row in top_pairs.iterrows()
    )

    return (
        f"The library includes {PLANTS['species'].nunique()} plant records and "
        f"{INSECTS['species'].nunique()} insect records.\n\n"
        f"Example plants: {_fmt_list(plant_examples, limit=10)}\n\n"
        f"Example insects: {_fmt_list(insect_examples, limit=10)}\n\n"
        "Most represented plant-insect combinations:\n"
        f"{pair_lines}"
    )


def _response_natural_enemies():
    enemies = VOCS["natural_enemy"].dropna()
    counts = enemies.value_counts().head(10)
    if counts.empty:
        return "No natural enemy annotations are available in the bundled VOC records."

    lines = "\n".join(f"- {name}: {count} VOC records" for name, count in counts.items())
    return (
        "Natural enemy fields are linked annotations from the bundled records. They "
        "help identify ecological context but do not prove recruitment by a VOC.\n\n"
        "Most frequent natural enemy annotations:\n"
        f"{lines}"
    )


def _response_similarity():
    return (
        "The Structural Similarity Explorer compares chemical fingerprints only. "
        "It is useful for finding related VOC structures, analogs, and chemical "
        "neighborhoods in the library.\n\n"
        "It should not be interpreted as evidence that two VOCs share the same "
        "odor, volatility, aphid behavior, natural enemy response, receptor binding, "
        "or ecological function. Those claims need bioassay, literature, or docking "
        "evidence."
    )


def _response_docking():
    docking_file = CURATION_DIR / "docking_results.csv"
    if not docking_file.exists():
        return (
            "The receptor docking page is available, but receptor-ligand curation "
            "files were not found in this deployment."
        )

    docking = pd.read_csv(docking_file)
    n_results = len(docking)
    receptor_col = "receptor_id" if "receptor_id" in docking else "protein_id"
    receptors = docking[receptor_col].nunique() if receptor_col in docking else 0
    ligands = docking["ligand_id"].nunique() if "ligand_id" in docking else 0

    energy_col = (
        "binding_energy_kcal_mol"
        if "binding_energy_kcal_mol" in docking.columns
        else "best_affinity_kcal_mol"
    )
    top_line = ""
    if energy_col in docking.columns:
        top = docking.sort_values(energy_col).head(5)
        lines = []
        for _, row in top.iterrows():
            ligand = row.get("ligand_id", "ligand")
            receptor = row.get(receptor_col, "receptor")
            energy = row.get(energy_col)
            lines.append(f"- {ligand} vs {receptor}: {energy:.2f} kcal/mol")
        top_line = "\n\nLowest reported docking energies:\n" + "\n".join(lines)

    return (
        f"The local docking evidence table contains {n_results} receptor-ligand "
        f"records covering {ligands} ligand IDs and {receptors} receptor IDs."
        f"{top_line}\n\nDocking should be treated as hypothesis-generating evidence. "
        "It can prioritize receptor-ligand pairs for review, but it does not replace "
        "binding assays, electrophysiology, or behavioral validation."
    )


RESPONSE_BUILDERS = {
    "library_scope": _response_library_scope,
    "top_vocs": _response_top_vocs,
    "bioactivity": _response_bioactivity,
    "volatile": _response_volatile,
    "plants_insects": _response_plants_insects,
    "natural_enemies": _response_natural_enemies,
    "similarity": _response_similarity,
    "docking": _response_docking,
}


def _keyword_route(text):
    text = text.lower()
    routes = [
        ("docking", ["dock", "receptor", "binding"]),
        ("similarity", ["similar", "fingerprint", "tanimoto", "structural"]),
        ("natural_enemies", ["enemy", "enemies", "parasitoid", "predator"]),
        ("plants_insects", ["plant", "insect", "aphid", "host"]),
        ("volatile", ["volatile", "logp", "molecular", "mw"]),
        ("bioactivity", ["repellent", "attractant", "bioactivity", "response"]),
        ("top_vocs", ["strong", "top", "effect", "evidence", "signal"]),
    ]
    for key, words in routes:
        if any(word in text for word in words):
            return key
    return "library_scope"


def _answer_question(question_key):
    return RESPONSE_BUILDERS[question_key]()


def render():
    st.markdown(
        "<div class='section-head'>Ask the Research Team</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class='info-box'>
        This public version uses a local, rule-based research assistant. It answers
        curated questions from the internal VOC, bioassay, plant, insect, and docking
        tables. No API key is required and no question is sent to an external service.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("VOC records", f"{len(VOCS):,}")
    col_b.metric("Bioassay records", f"{len(BIOASSAYS):,}")
    col_c.metric("Unique insects", f"{VOCS['insect'].nunique():,}")

    if "local_team_history" not in st.session_state:
        st.session_state.local_team_history = []

    st.markdown("**Choose a guided question**")
    selected_label = st.selectbox(
        "Guided question",
        list(QUESTION_BANK.values()),
        label_visibility="collapsed",
    )
    selected_key = next(
        key for key, label in QUESTION_BANK.items() if label == selected_label
    )

    custom_question = st.text_input(
        "Optional keyword question",
        placeholder=(
            "Example: summarize natural enemies, docking evidence, volatile compounds..."
        ),
    )

    col_submit, col_clear = st.columns([3, 1])
    with col_submit:
        ask = st.button("Ask local research assistant", type="primary", use_container_width=True)
    with col_clear:
        clear = st.button("Clear", use_container_width=True)

    if clear:
        st.session_state.local_team_history = []
        st.rerun()

    if ask:
        if custom_question.strip():
            question = custom_question.strip()
            answer_key = _keyword_route(question)
        else:
            question = QUESTION_BANK[selected_key]
            answer_key = selected_key

        st.session_state.local_team_history.append(
            {
                "question": question,
                "answer": _answer_question(answer_key),
                "source": "Internal bundled dataset",
            }
        )
        st.rerun()

    for turn in reversed(st.session_state.local_team_history):
        st.markdown(
            f"""
            <div style='background:#1a3a2a;color:#d1fae5;border-radius:8px;
                        padding:12px 16px;margin-top:18px'>
                <b>Question</b><br>{turn["question"]}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(turn["answer"])
        st.caption(f"Source: {turn['source']}. Deterministic local summary; no API call.")
