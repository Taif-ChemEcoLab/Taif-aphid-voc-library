"""Typed V1 evidence graph generation without ecological-effect inference."""

from __future__ import annotations

import pandas as pd

from data.v1_loader import BIOLOGICAL_CONTEXTS, CHEMICAL_ENTITIES, CONFIDENCE_LABELS, FEATURE_CHEMICAL_MAPPING, PUBLISHED_FEATURES
from services.feature_queries import occurrence_catalog


ALLOWED_EDGE_TYPES = {"context_species", "context_host", "published_presence", "chemical_interpretation"}


def _node(node_id: str, label: str, node_type: str, evidence: str, detail: str = "") -> dict[str, str]:
    return {"node_id": node_id, "label": label, "node_type": node_type, "evidence_level": evidence, "detail": detail}


def evidence_network_tables(context_ids: tuple[str, ...] = (), confidences: tuple[str, ...] = ("*", "?", "??", "UK"), include_chemical_interpretations: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return typed nodes/edges. No behavioral or natural-enemy semantics exist."""
    contexts = BIOLOGICAL_CONTEXTS.copy()
    if context_ids:
        contexts = contexts[contexts["context_id"].isin(context_ids)]
    occurrences = occurrence_catalog()
    occurrences = occurrences[occurrences["context_id"].isin(contexts["context_id"])]
    occurrences = occurrences[occurrences["confidence_symbol"].isin(confidences)]
    features = PUBLISHED_FEATURES[PUBLISHED_FEATURES["feature_id"].isin(occurrences["feature_id"])].copy()
    nodes: dict[str, dict[str, str]] = {}
    edges: list[dict[str, str]] = []
    for row in contexts.to_dict("records"):
        context_node = f"context:{row['context_id']}"
        species_node = f"species:{row['canonical_species']}"
        host_node = f"host:{row['host_plant_and_part']}"
        nodes[context_node] = _node(context_node, row["context_id"], "context", "documentary_context", f"{row['canonical_species']} · {row['host_plant_and_part']}")
        nodes[species_node] = _node(species_node, row["canonical_species"], "species", row["provenance_status"], row["historical_species_label"])
        nodes[host_node] = _node(host_node, row["host_plant_and_part"], "host", row["provenance_status"])
        edges.append({"source": context_node, "target": species_node, "edge_type": "context_species", "evidence_level": "documentary_context", "source_record": row["evidence_source"], "published_confidence_notation": "", "identification_confidence": "Not applicable", "conflict_status": row["conflict_status"]})
        edges.append({"source": context_node, "target": host_node, "edge_type": "context_host", "evidence_level": "documentary_context", "source_record": row["evidence_source"], "published_confidence_notation": "", "identification_confidence": "Not applicable", "conflict_status": row["conflict_status"]})
    for row in occurrences.to_dict("records"):
        context_node = f"context:{row['context_id']}"
        feature_node = f"feature:{row['feature_id']}"
        nodes[feature_node] = _node(feature_node, row["bio_id"], "feature", row["evidence_level"], row["published_annotation_exact"])
        conflict = row.get("conflict_status_x", "") or row.get("conflict_status_y", "")
        edges.append({"source": context_node, "target": feature_node, "edge_type": "published_presence", "evidence_level": row["evidence_level"], "source_record": row["source_workbook_or_publication"], "published_confidence_notation": row["confidence_symbol"], "identification_confidence": CONFIDENCE_LABELS[row["confidence_symbol"]], "conflict_status": conflict})
    if include_chemical_interpretations:
        mapping = FEATURE_CHEMICAL_MAPPING[FEATURE_CHEMICAL_MAPPING["feature_id"].isin(features["feature_id"])]
        chemicals = CHEMICAL_ENTITIES.set_index("chemical_id", drop=False)
        feature_index = features.set_index("feature_id", drop=False)
        for row in mapping.to_dict("records"):
            chemical = chemicals.loc[row["chemical_id"]]
            feature = feature_index.loc[row["feature_id"]]
            feature_node = f"feature:{row['feature_id']}"
            chemical_node = f"chemical:{row['chemical_id']}"
            nodes[feature_node] = _node(feature_node, feature["bio_id"], "feature", feature["evidence_status"], feature["published_annotation_exact"])
            nodes[chemical_node] = _node(chemical_node, chemical["canonical_name"], "chemical_interpretation", chemical["identity_evidence_level"], chemical["experimental_peak_identity_status"])
            edges.append({"source": feature_node, "target": chemical_node, "edge_type": "chemical_interpretation", "evidence_level": row["evidence_level"], "source_record": row["evidence_source"], "published_confidence_notation": row["confidence_symbol"], "identification_confidence": CONFIDENCE_LABELS[row["confidence_symbol"]], "conflict_status": row["conflict_status"]})
    node_frame = pd.DataFrame(nodes.values(), columns=["node_id", "label", "node_type", "evidence_level", "detail"])
    edge_frame = pd.DataFrame(edges, columns=["source", "target", "edge_type", "evidence_level", "source_record", "published_confidence_notation", "identification_confidence", "conflict_status"])
    if not set(edge_frame["edge_type"]).issubset(ALLOWED_EDGE_TYPES):
        raise ValueError("Unsupported evidence edge type generated")
    return node_frame.reset_index(drop=True), edge_frame.reset_index(drop=True)


def network_contract() -> dict[str, object]:
    return {
        "allowed_edge_types": sorted(ALLOWED_EDGE_TYPES),
        "excluded_semantics": ["attraction", "repellency", "natural-enemy recruitment", "interaction strength", "receptor binding"],
        "interpretation": "Connectivity measures documentation coverage, not biological importance.",
    }
