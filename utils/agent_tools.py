"""
Agent Tools — functions agents call to query the VOC library.
"""

import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.sample_data import VOCS, INSECTS, PLANTS, BIOASSAYS

try:
    from utils.chem_utils import (
        compute_descriptors, tanimoto_similarity,
        get_lipinski_verdict, RDKIT_AVAILABLE,
    )
except Exception:
    RDKIT_AVAILABLE = False


#  CHEMIST TOOLS 
def get_compound_profile(compound_name: str) -> str:
    mask = VOCS["name"].str.lower().str.contains(compound_name.lower(), na=False)
    hits = VOCS[mask]
    if hits.empty:
        return f"No compound matching '{compound_name}' found."
    results = []
    for _, row in hits.iterrows():
        results.append(
            f"Compound: {row['name']} (ID: {row['voc_id']})\n"
            f"  Formula: {row['formula']} | MW: {row['mw']} g/mol | LogP: {row['logp']}\n"
            f"  Class: {row['class']} | Emission source: {row['emission_source']}\n"
            f"  SMILES: {row['smiles']}\n"
            f"  PubChem CID: {row['pubchem_cid']}\n"
            f"  Associated insect: {row['insect']}\n"
            f"  Associated plant: {row['plant']}\n"
            f"  Bioactivity: {row['bioactivity']} (target: {row['target']})\n"
            f"  Concentration: {row['concentration_ppm']} ppm\n"
            f"  Notes: {row['notes']}"
        )
    return "\n\n".join(results)


def get_compounds_by_class(chemical_class: str) -> str:
    mask = VOCS["class"].str.lower().str.contains(chemical_class.lower(), na=False)
    hits = VOCS[mask]
    if hits.empty:
        return f"No compounds found in class '{chemical_class}'."
    lines = [f"Compounds in class '{chemical_class}':"]
    for _, row in hits.iterrows():
        lines.append(f"  • {row['name']} — {row['formula']}, LogP {row['logp']}, "
                     f"{row['bioactivity']} on {row['insect']}")
    return "\n".join(lines)


def get_rdkit_descriptors(compound_name: str) -> str:
    mask = VOCS["name"].str.lower().str.contains(compound_name.lower(), na=False)
    hits = VOCS[mask]
    if hits.empty:
        return f"Compound '{compound_name}' not found."
    row = hits.iloc[0]
    if not RDKIT_AVAILABLE:
        return (f"RDKit not installed. Stored values for {row['name']}: "
                f"MW={row['mw']}, LogP={row['logp']}")
    desc    = compute_descriptors(row["smiles"])
    verdict = get_lipinski_verdict(row["smiles"])
    if not desc:
        return f"Could not parse SMILES for {row['name']}."
    desc_str    = "\n".join(f"  {k}: {v}" for k, v in desc.items())
    verdict_str = "\n".join(f"  {k}: {v}" for k, v in verdict.items())
    return (f"RDKit Descriptors for {row['name']}:\n{desc_str}\n\n"
            f"Volatility Profile:\n{verdict_str}")


def find_similar_compounds(compound_name: str, threshold: float = 0.25) -> str:
    if not RDKIT_AVAILABLE:
        return "RDKit required for structural similarity search."
    mask = VOCS["name"].str.lower().str.contains(compound_name.lower(), na=False)
    hits = VOCS[mask]
    if hits.empty:
        return f"Compound '{compound_name}' not found."
    query_smiles = hits.iloc[0]["smiles"]
    query_name   = hits.iloc[0]["name"]
    results = []
    for _, row in VOCS.iterrows():
        if row["name"] == query_name: continue
        sim = tanimoto_similarity(query_smiles, row["smiles"])
        if sim >= threshold:
            results.append((sim, row))
    if not results:
        return f"No compounds with Tanimoto ≥ {threshold} found."
    results.sort(key=lambda x: x[0], reverse=True)
    lines = [f"Compounds similar to {query_name} (threshold ≥ {threshold}):"]
    for sim, row in results:
        lines.append(f"  • {row['name']} — Tanimoto: {sim:.3f} | "
                     f"Class: {row['class']} | Bioactivity annotation: {row['bioactivity']} on {row['insect']}")
    return "\n".join(lines)


# ENTOMOLOGIST TOOLS 

def get_insect_profile(insect_name: str) -> str:
    mask = (INSECTS["species"].str.lower().str.contains(insect_name.lower(), na=False) |
            INSECTS["common_name"].str.lower().str.contains(insect_name.lower(), na=False))
    hits = INSECTS[mask]
    if hits.empty:
        return f"Insect '{insect_name}' not found."
    lines = []
    for _, row in hits.iterrows():
        lines.append(
            f"Insect: {row['species']} ({row['common_name']})\n"
            f"  Order: {row['order']} | Family: {row['family']}\n"
            f"  Host range: {row['host_range']}\n"
            f"  Damage type: {row['damage_type']}\n"
            f"  Geographic range: {row['geographic_range']}"
        )
    return "\n\n".join(lines)


def get_bioassay_records(query: str) -> str:
    mask = (BIOASSAYS["voc_name"].str.lower().str.contains(query.lower(), na=False) |
            BIOASSAYS["insect"].str.lower().str.contains(query.lower(), na=False))
    hits = BIOASSAYS[mask]
    if hits.empty:
        return f"No bioassay records found for '{query}'."
    lines = [f"Bioassay records for '{query}':"]
    for _, row in hits.iterrows():
        lines.append(
            f"\n  [{row['assay_id']}] {row['voc_name']} × {row['insect']}\n"
            f"    Assay type: {row['assay_type']}\n"
            f"    Response: {row['response']} (target: {row['target']})\n"
            f"    Effect size: {row['effect_size']}% | p-value: {row['p_value']}\n"
            f"    Replicates: {row['n_replicates']} | Conc: {row['concentration_ppm']} ppm\n"
            f"    Reference: {row['reference']}"
        )
    return "\n".join(lines)


def get_vocs_for_insect(insect_name: str) -> str:
    mask = VOCS["insect"].str.lower().str.contains(insect_name.lower(), na=False)
    hits = VOCS[mask]
    if hits.empty:
        return f"No VOC records found for insect '{insect_name}'."
    lines = [f"VOCs associated with {insect_name}:"]
    for _, row in hits.iterrows():
        lines.append(f"  • {row['name']} ({row['class']}) — {row['bioactivity']}, "
                     f"target: {row['target']}, from {row['plant']}")
    return "\n".join(lines)


def get_natural_enemies(insect_name: str) -> str:
    mask = VOCS["insect"].str.lower().str.contains(insect_name.lower(), na=False)
    hits = VOCS[mask]
    if hits.empty:
        return f"No natural enemy data found for '{insect_name}'."
    lines = [f"Natural enemies associated with {insect_name}:"]
    for _, row in hits[["natural_enemy", "name", "bioactivity", "target"]].drop_duplicates().iterrows():
        lines.append(f"  • {row['natural_enemy']} — recruited via {row['name']} "
                     f"({row['bioactivity']}, target: {row['target']})")
    return "\n".join(lines)


def get_vocs_for_plant(plant_name: str) -> str:
    mask = VOCS["plant"].str.lower().str.contains(plant_name.lower(), na=False)
    hits = VOCS[mask]
    if hits.empty:
        return f"No VOC records found for plant '{plant_name}'."
    lines = [f"VOCs associated with {plant_name}:"]
    for _, row in hits.iterrows():
        lines.append(f"  • {row['name']} ({row['class']}) — {row['bioactivity']} "
                     f"on {row['insect']} | {row['concentration_ppm']} ppm")
    return "\n".join(lines)


#  COMPUTATIONAL TOOLS 

def get_library_statistics() -> str:
    total      = len(VOCS)
    attractants = (VOCS["bioactivity"] == "Attractant").sum()
    repellents  = (VOCS["bioactivity"] == "Repellent").sum()
    classes     = VOCS["class"].value_counts().to_dict()
    ins_counts  = VOCS["insect"].value_counts().to_dict()
    avg_effect  = BIOASSAYS["effect_size"].mean()
    return (
        f"VOC Library Statistics:\n"
        f"  Total VOC records: {total}\n"
        f"  Attractants: {attractants} | Repellents: {repellents}\n"
        f"  Chemical classes: {json.dumps(classes, indent=4)}\n"
        f"  Insects covered: {json.dumps(ins_counts, indent=4)}\n"
        f"  Host plants covered: {VOCS['plant'].nunique()}\n"
        f"  Average bioassay effect size: {avg_effect:.1f}%\n"
        f"  Total bioassay records: {len(BIOASSAYS)}"
    )


def find_strongest_bioassay_evidence(bioactivity: str = None) -> str:
    df = BIOASSAYS.copy()
    if bioactivity:
        df = df[df["response"].str.lower() == bioactivity.lower()]
    if df.empty:
        return "No matching bioassay records."
    top   = df.sort_values(["effect_size", "p_value"], ascending=[False, True]).head(5)
    lines = ["Strongest bioassay evidence:"]
    for _, row in top.iterrows():
        lines.append(
            f"  • [{row['assay_id']}] {row['voc_name']} → {row['insect']}\n"
            f"    Effect: {row['effect_size']}% | p={row['p_value']} | "
            f"n={row['n_replicates']} | {row['assay_type']}\n"
            f"    Reference: {row['reference']}"
        )
    return "\n".join(lines)


def compare_compounds(compound_a: str, compound_b: str) -> str:
    def find_voc(name):
        mask = VOCS["name"].str.lower().str.contains(name.lower(), na=False)
        hits = VOCS[mask]
        return hits.iloc[0] if not hits.empty else None
    a = find_voc(compound_a)
    b = find_voc(compound_b)
    if a is None: return f"Compound '{compound_a}' not found."
    if b is None: return f"Compound '{compound_b}' not found."
    sim = (tanimoto_similarity(a["smiles"], b["smiles"])
           if RDKIT_AVAILABLE else "N/A (RDKit not installed)")
    return (
        f"Comparison: {a['name']} vs {b['name']}\n\n"
        f"{'Property':<28} {'Compound A':<28} {'Compound B'}\n"
        f"{'-'*80}\n"
        f"{'Name':<28} {a['name']:<28} {b['name']}\n"
        f"{'Formula':<28} {a['formula']:<28} {b['formula']}\n"
        f"{'MW (g/mol)':<28} {str(a['mw']):<28} {b['mw']}\n"
        f"{'LogP':<28} {str(a['logp']):<28} {b['logp']}\n"
        f"{'Chemical class':<28} {a['class']:<28} {b['class']}\n"
        f"{'Bioactivity annotation':<28} {a['bioactivity']:<28} {b['bioactivity']}\n"
        f"{'Target insect':<28} {a['insect']:<28} {b['insect']}\n"
        f"{'Host plant':<28} {a['plant']:<28} {b['plant']}\n"
        f"{'Conc. (ppm)':<28} {str(a['concentration_ppm']):<28} {b['concentration_ppm']}\n"
        f"\nTanimoto structural similarity: {sim}"
    )


def get_repellent_strategy(plant_name: str) -> str:
    plant_vocs = VOCS[VOCS["plant"].str.lower().str.contains(plant_name.lower(), na=False)]
    if plant_vocs.empty:
        return f"No data found for plant '{plant_name}'."
    repellents    = plant_vocs[plant_vocs["bioactivity"] == "Repellent"]
    attractants_ne = plant_vocs[(plant_vocs["bioactivity"] == "Attractant") &
                                 (plant_vocs["target"] == "Natural Enemy")]
    lines = [f"Natural Pest Management Strategy for {plant_name}:\n"]
    if not repellents.empty:
        lines.append("REPELLENT VOCs (direct pest deterrence):")
        for _, row in repellents.iterrows():
            lines.append(f"  • {row['name']} ({row['class']}) — repels {row['insect']} "
                         f"at {row['concentration_ppm']} ppm")
    if not attractants_ne.empty:
        lines.append("\nATTRACTANT VOCs (recruit natural enemies):")
        for _, row in attractants_ne.iterrows():
            lines.append(f"  • {row['name']} — attracts {row['natural_enemy']} "
                         f"against {row['insect']}")
    if repellents.empty and attractants_ne.empty:
        lines.append("No repellent or natural-enemy-attractant VOCs found.")
    return "\n".join(lines)


#  TOOL REGISTRY 

TOOL_REGISTRY = {
    "get_compound_profile":           get_compound_profile,
    "get_compounds_by_class":         get_compounds_by_class,
    "get_rdkit_descriptors":          get_rdkit_descriptors,
    "find_similar_compounds":         find_similar_compounds,
    "get_insect_profile":             get_insect_profile,
    "get_bioassay_records":           get_bioassay_records,
    "get_vocs_for_insect":            get_vocs_for_insect,
    "get_natural_enemies":            get_natural_enemies,
    "get_vocs_for_plant":             get_vocs_for_plant,
    "get_library_statistics":         get_library_statistics,
    "find_strongest_bioassay_evidence": find_strongest_bioassay_evidence,
    "compare_compounds":              compare_compounds,
    "get_repellent_strategy":         get_repellent_strategy,
}


def execute_tool(tool_name: str, arguments: dict) -> str:
    func = TOOL_REGISTRY.get(tool_name)
    if func is None:
        return f"Unknown tool: {tool_name}"
    try:
        return func(**arguments)
    except Exception as e:
        return f"Tool error ({tool_name}): {str(e)}"


#  OPENAI TOOL SCHEMAS 

CHEMIST_TOOLS = [
    {"type": "function", "function": {"name": "get_compound_profile",   "description": "Retrieve full chemical profile of a VOC by name. Returns formula, SMILES, LogP, MW, class, bioactivity annotation, notes.", "parameters": {"type": "object", "properties": {"compound_name": {"type": "string"}}, "required": ["compound_name"]}}},
    {"type": "function", "function": {"name": "get_compounds_by_class", "description": "List all VOC compounds in a chemical class (Monoterpene, Sesquiterpene, Green Leaf Volatile, Benzenoid, Phenylpropanoid, etc.).", "parameters": {"type": "object", "properties": {"chemical_class": {"type": "string"}}, "required": ["chemical_class"]}}},
    {"type": "function", "function": {"name": "get_rdkit_descriptors",  "description": "Compute RDKit molecular descriptors: MW, LogP, TPSA, H-bond donors/acceptors, rotatable bonds, volatility profile.", "parameters": {"type": "object", "properties": {"compound_name": {"type": "string"}}, "required": ["compound_name"]}}},
    {"type": "function", "function": {"name": "find_similar_compounds", "description": "Find structurally similar compounds using Tanimoto/Morgan fingerprints.", "parameters": {"type": "object", "properties": {"compound_name": {"type": "string"}, "threshold": {"type": "number", "description": "Minimum Tanimoto (0–1), default 0.25"}}, "required": ["compound_name"]}}},
]

ENTOMOLOGIST_TOOLS = [
    {"type": "function", "function": {"name": "get_insect_profile",   "description": "Retrieve biological profile: order, family, host range, damage type, geographic range.", "parameters": {"type": "object", "properties": {"insect_name": {"type": "string"}}, "required": ["insect_name"]}}},
    {"type": "function", "function": {"name": "get_bioassay_records", "description": "Retrieve bioassay records for a compound or insect. Returns effect size, p-value, assay type, reference.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_vocs_for_insect",  "description": "List all VOC compounds associated with an insect and their attractant/repellent activity.", "parameters": {"type": "object", "properties": {"insect_name": {"type": "string"}}, "required": ["insect_name"]}}},
    {"type": "function", "function": {"name": "get_natural_enemies",  "description": "List natural enemies (parasitoids, predators) and the VOCs that recruit them.", "parameters": {"type": "object", "properties": {"insect_name": {"type": "string"}}, "required": ["insect_name"]}}},
    {"type": "function", "function": {"name": "get_vocs_for_plant",   "description": "List all VOCs associated with a host plant and their known bioactivities.", "parameters": {"type": "object", "properties": {"plant_name": {"type": "string"}}, "required": ["plant_name"]}}},
]

COMPUTATIONAL_TOOLS = [
    {"type": "function", "function": {"name": "get_library_statistics",           "description": "Summary statistics: total compounds, classes, bioactivity annotation split, insect coverage.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "find_strongest_bioassay_evidence", "description": "VOC–insect pairs with strongest evidence (highest effect size, lowest p-value).", "parameters": {"type": "object", "properties": {"bioactivity": {"type": "string", "description": "Filter by 'Attractant' or 'Repellent' (optional)"}}}}},
    {"type": "function", "function": {"name": "compare_compounds",                "description": "Side-by-side comparison: MW, LogP, class, bioactivity annotation, target, Tanimoto structural similarity.", "parameters": {"type": "object", "properties": {"compound_a": {"type": "string"}, "compound_b": {"type": "string"}}, "required": ["compound_a", "compound_b"]}}},
    {"type": "function", "function": {"name": "get_repellent_strategy",           "description": "Natural pest management strategy for a host plant using repellent VOCs and natural enemy recruiters.", "parameters": {"type": "object", "properties": {"plant_name": {"type": "string"}}, "required": ["plant_name"]}}},
]
