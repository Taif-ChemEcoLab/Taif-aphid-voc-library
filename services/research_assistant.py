"""Deterministic, provenance-aware answers over the V1 evidence layer."""

from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd

from data.v1_loader import BIOLOGICAL_CONTEXTS, CONFIDENCE_LABELS, CONFIDENCE_ORDER, CONFIDENCE_SOURCE_RANGES, CURATED_CANDIDATE_STRUCTURES, PUBLISHED_FEATURES, UNRESOLVED_RECORDS
from services.feature_queries import feature_evidence


@dataclass(frozen=True)
class EvidenceAnswer:
    answer: str
    evidence_layer: str
    source: str
    caution: str
    records: pd.DataFrame


def _answer_for_feature(feature_id: str) -> EvidenceAnswer:
    packet = feature_evidence(feature_id)
    row = packet["feature"]
    annotation = row["published_annotation_display"] or "unknown"
    answer = (
        f"{row['bio_id']} is a published GC-MS feature at RT {row['published_rt_exact']}. "
        f"Its annotation is ‘{annotation}’. Identification confidence: {row['identification_confidence']}. "
        f"Original published notation: {row['published_confidence_notation']}. "
        f"It is recorded in {int(row['contexts_present'])} of 15 documented contexts."
    )
    return EvidenceAnswer(
        answer=answer,
        evidence_layer="published evidence + V1 descriptive join",
        source="Alotaibi et al. 2023, Supplementary Table S2",
        caution="The annotation/confidence is preserved as published; it is not upgraded to a confirmed peak structure.",
        records=packet["occurrences"][["context_id", "canonical_species", "host_plant_and_part"]].copy(),
    )


def answer_question(question: str) -> EvidenceAnswer:
    """Answer common evidence questions without generative inference."""
    lower = question.strip().lower()
    if any(token in lower for token in ("attract", "repel", "behavior", "bioassay", "effect")):
        return EvidenceAnswer(
            "V1 contains no publication-facing behavioral assay dataset. GC-MS feature presence cannot answer this question.",
            "unresolved / unavailable evidence",
            "Phase 5B quarantine record",
            "A behavioral claim requires genuine assay observations and an appropriate experimental design.",
            pd.DataFrame(),
        )
    match = re.search(r"\bbio\s*0*([1-9]|[1-7][0-9]|8[01])\b", lower)
    if match:
        bio_id = f"Bio{int(match.group(1))}"
        matched = PUBLISHED_FEATURES[PUBLISHED_FEATURES["bio_id"].str.casefold() == bio_id.casefold()]
        if not matched.empty:
            return _answer_for_feature(matched.iloc[0]["feature_id"])

    if "alhada" in lower:
        rows = BIOLOGICAL_CONTEXTS[BIOLOGICAL_CONTEXTS["conflict_status"].str.contains("conflict", case=False, na=False)]
        return EvidenceAnswer(
            "The Alhada rose assignment remains conflicted; V1 preserves competing historical and published labels without forcing a taxon merge.",
            "historical reconstruction + unresolved evidence",
            "V1 biological contexts and unresolved record V1-UNR-004",
            "A chain-of-custody or sample-level barcode join is still required.",
            rows[["context_id", "canonical_species", "historical_species_label", "conflict_notes"]].copy(),
        )
    if any(token in lower for token in ("76", "84", "63", "81", "transition", "lineage")):
        rows = UNRESOLVED_RECORDS[UNRESOLVED_RECORDS["category"] == "historical_transition"]
        return EvidenceAnswer(
            "The 76-sample × 84-feature precursor and published 63-observation × 81-Bio-variable layer are documented, but their exact transformation is only partially resolved.",
            "historical reconstruction + published evidence",
            "V1 unresolved record V1-UNR-001",
            "No exclusions, replicate means, feature removals, or renumbering are inferred.",
            rows.copy(),
        )
    if "weight" in lower or "mass" in lower:
        rows = UNRESOLVED_RECORDS[UNRESOLVED_RECORDS["category"].isin(["sample_mass", "normalization"])]
        return EvidenceAnswer(
            "Historical sample-associated mass values and mass-division formulas exist. Weight was not described as a published CAP analytical factor, and the exact weighed material remains unresolved.",
            "historical reconstruction",
            "V1 historical mass observations and unresolved records",
            "Represent mass as experimental/normalization metadata, not as a published covariate.",
            rows.copy(),
        )
    if "structure" in lower or "similar" in lower:
        structure_records = CURATED_CANDIDATE_STRUCTURES[["canonical_name", "source_bio_ids", "gcms_identification_confidence"]].copy()
        structure_records["published_confidence_notation"] = structure_records["gcms_identification_confidence"]
        structure_records["identification_confidence"] = structure_records["published_confidence_notation"].map(CONFIDENCE_LABELS)
        return EvidenceAnswer(
            f"{len(CURATED_CANDIDATE_STRUCTURES)} publication-annotation candidates have internally validated molecular structures. Their published GC-MS confidence remains unchanged; the two legacy manual-review structures remain separate.",
            "curated candidate-structure representation",
            "Supplementary Table S2 annotations, PubChem identifiers, and RDKit validation",
            "A candidate structure represents the named chemical interpretation; it does not independently confirm the experimental peak or ecological function.",
            structure_records[["canonical_name", "source_bio_ids", "identification_confidence", "published_confidence_notation"]],
        )
    if "confidence" in lower or "identif" in lower:
        summary = (
            PUBLISHED_FEATURES.groupby(["published_confidence_notation", "identification_confidence"], as_index=False)
            .size().rename(columns={"size": "features"})
        )
        summary["source_study_definition"] = summary["published_confidence_notation"].map(CONFIDENCE_SOURCE_RANGES)
        order = {value: index for index, value in enumerate(CONFIDENCE_ORDER)}
        summary = summary.sort_values("published_confidence_notation", key=lambda values: values.map(order)).reset_index(drop=True)
        return EvidenceAnswer(
            "Identification confidence of the 81 published GC-MS features: 11 Authentic-standard supported; "
            "32 Tentative identification, higher library match; 27 Tentative identification, lower library match; "
            "and 11 Unknown features. These categories were inherited from the published source dataset; they were "
            "not generated by VOC·BIO. The original published notation (*, ?, ?? and UK) is retained for provenance.",
            "published evidence",
            "Published Supplementary Table S2",
            "Tentative and unknown features are not confirmed chemical identities and must remain tentative or unknown in downstream views.",
            summary,
        )
    if "dock" in lower or "binding" in lower:
        rows = UNRESOLVED_RECORDS[UNRESOLVED_RECORDS["category"].str.contains("dock", case=False, na=False)]
        return EvidenceAnswer(
            "No validated new docking results are part of V1. Historical scores remain isolated exploratory output.",
            "unresolved / out-of-scope evidence",
            "V1 unresolved records and Phase 5C.1 docking audit",
            "Docking scores are computational predictions, not experimental binding affinities.",
            rows.copy(),
        )

    return EvidenceAnswer(
        f"V1 represents {len(PUBLISHED_FEATURES)} published GC-MS features across {len(BIOLOGICAL_CONTEXTS)} documented contexts. Ask about a Bio ID, confidence, Alhada, mass, processing lineage, structures, or docking for a source-scoped answer.",
        "published evidence + current curated representation",
        "V1 datasets",
        "The assistant does not infer missing experimental relationships.",
        pd.DataFrame(),
    )


def suggested_questions() -> tuple[str, ...]:
    return (
        "What is Bio1?",
        "What do the identification-confidence categories mean?",
        "Is the 76×84 to 63×81 transition resolved?",
        "What is unresolved about Alhada?",
        "How is aphid/sample weight represented?",
        "Which structures are available?",
        "Are behavioral effects available?",
        "Are docking results validated?",
    )
