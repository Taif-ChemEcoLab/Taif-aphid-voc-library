"""
GC-MS Data Ingestion Pipeline
================================
Converts the tidy GC-MS CSV (output of the Excel parser) into
the sample_data.py format used by the VOC·BIO Streamlit library.

Usage:
    python ingest_gcms_data.py

Input:
    gcms_tidy_data.csv  — the tidy CSV produced by the Excel parser

Output:
    data/sample_data.py — overwrites the sample data with real data

The script:
  1. Reads the tidy CSV
  2. Enriches each compound with chemical metadata (PubChem CID, SMILES,
     formula, MW, LogP, class) from the built-in lookup table
  3. Aggregates replicate samples → one representative record per
     compound × aphid species × host plant combination
  4. Builds VOCS, INSECTS, PLANTS, BIOASSAYS DataFrames
  5. Writes a new sample_data.py that the Streamlit app imports directly
"""

import pandas as pd
import numpy as np
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CSV_PATH     = os.path.join(SCRIPT_DIR, "gcms_tidy_data.csv")
OUTPUT_PATH  = os.path.join(SCRIPT_DIR, "sample_data.py")

# ── Chemical metadata lookup ──────────────────────────────────────────────────
# PubChem CIDs, SMILES, formula, MW, LogP, and chemical class for every
# identified compound in the GC-MS dataset.
COMPOUND_METADATA = {
    "2-methyl-4-heptanone": {
        "display_name": "2-Methyl-4-heptanone",
        "pubchem_cid":  12671,
        "formula":      "C8H16O",
        "mw":           128.21,
        "logp":         2.60,
        "class":        "Aliphatic Ketone",
        "smiles":       "CCCC(=O)CC(C)C",
        "inchikey":     "KQSSATDQUYCRGS-UHFFFAOYSA-N",
    },
    "4,5-dimethyl nonane": {
        "display_name": "4,5-Dimethyl Nonane",
        "pubchem_cid":  522685,
        "formula":      "C11H24",
        "mw":           156.31,
        "logp":         5.44,
        "class":        "Aliphatic Hydrocarbon",
        "smiles":       "CCCCC(C)C(C)CCC",
        "inchikey":     "BNIXVQGCZULYKV-UHFFFAOYSA-N",
    },
    "4-carene": {
        "display_name": "4-Carene",
        "pubchem_cid":  26049,
        "formula":      "C10H16",
        "mw":           136.23,
        "logp":         4.23,
        "class":        "Monoterpene",
        "smiles":       "CC1=CCC2(CC1)C2(C)C",
        "inchikey":     "WTFXTQVDAKGDEY-HTQZYQBOSA-N",
    },
    "6-methyl-hepta-2-none": {
        "display_name": "6-Methyl-5-hepten-2-one",
        "pubchem_cid":  12813,
        "formula":      "C8H14O",
        "mw":           126.20,
        "logp":         2.38,
        "class":        "Aliphatic Ketone",
        "smiles":       "CC(=O)CCC=C(C)C",
        "inchikey":     "MDWVSAYEQPLWMX-UHFFFAOYSA-N",
    },
    "azulene": {
        "display_name": "Azulene",
        "pubchem_cid":  9231,
        "formula":      "C10H8",
        "mw":           128.17,
        "logp":         3.22,
        "class":        "Sesquiterpene",
        "smiles":       "C1=CC2=CC=CC=CC2=C1",
        "inchikey":     "WMKGGZDBHBKIKF-UHFFFAOYSA-N",
    },
    "benzaldehyde": {
        "display_name": "Benzaldehyde",
        "pubchem_cid":  240,
        "formula":      "C7H6O",
        "mw":           106.12,
        "logp":         1.48,
        "class":        "Benzenoid Aldehyde",
        "smiles":       "O=Cc1ccccc1",
        "inchikey":     "HUMNYLRZRPPJDN-UHFFFAOYSA-N",
    },
    "beta farnesen": {
        "display_name": "(E)-β-Farnesene",
        "pubchem_cid":  5362469,
        "formula":      "C15H24",
        "mw":           204.35,
        "logp":         5.92,
        "class":        "Sesquiterpene",
        "smiles":       "CC(=C)CCC=C(C)CCC=C(C)C",
        "inchikey":     "OIIQMHCBKGZXAL-UHFFFAOYSA-N",
        "notes_extra":  "Aphid alarm pheromone; released on predator contact",
    },
    "carbolactam": {
        "display_name": "Caprolactam",
        "pubchem_cid":  1018,
        "formula":      "C6H11NO",
        "mw":           113.16,
        "logp":         0.07,
        "class":        "Lactam",
        "smiles":       "O=C1CCCCCN1",
        "inchikey":     "JBKVHLHDHHXQEQ-UHFFFAOYSA-N",
    },
    "caryophyllene": {
        "display_name": "(E)-β-Caryophyllene",
        "pubchem_cid":  5281515,
        "formula":      "C15H24",
        "mw":           204.35,
        "logp":         5.08,
        "class":        "Sesquiterpene",
        "smiles":       "C(/C=C/[C@@]1(C)CCC(=C)CC1)(=C)C",
        "inchikey":     "NPNUFJALOSREFX-MUBKMAFCSA-N",
        "notes_extra":  "Indirect defense compound; attracts parasitoid wasps",
    },
    "d-lemonene": {
        "display_name": "D-Limonene",
        "pubchem_cid":  440917,
        "formula":      "C10H16",
        "mw":           136.23,
        "logp":         4.23,
        "class":        "Monoterpene",
        "smiles":       "C[C@@H]1CCC(=CC1)C=C",
        "inchikey":     "XMGQYMWWDOXHJM-JTQLQIEISA-N",
    },
    "heptacosane": {
        "display_name": "Heptacosane",
        "pubchem_cid":  12685,
        "formula":      "C27H56",
        "mw":           380.74,
        "logp":         14.13,
        "class":        "Aliphatic Hydrocarbon",
        "smiles":       "CCCCCCCCCCCCCCCCCCCCCCCCCCC",
        "inchikey":     "LBSFBXFZGKUJAO-UHFFFAOYSA-N",
    },
    "hexatriacontane": {
        "display_name": "Hexatriacontane",
        "pubchem_cid":  12128,
        "formula":      "C36H74",
        "mw":           506.98,
        "logp":         18.93,
        "class":        "Aliphatic Hydrocarbon",
        "smiles":       "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        "inchikey":     "PKOZIOXBFOXKDO-UHFFFAOYSA-N",
    },
    "humulene": {
        "display_name": "α-Humulene",
        "pubchem_cid":  5281520,
        "formula":      "C15H24",
        "mw":           204.35,
        "logp":         4.92,
        "class":        "Sesquiterpene",
        "smiles":       "CC1=CCC(=CCC(CC1)=C)C",
        "inchikey":     "UMNKXPULIDJLSU-UHFFFAOYSA-N",
    },
    "methyl salicylate": {
        "display_name": "Methyl Salicylate",
        "pubchem_cid":  4133,
        "formula":      "C8H8O3",
        "mw":           152.15,
        "logp":         2.55,
        "class":        "Benzenoid",
        "smiles":       "COC(=O)c1ccccc1O",
        "inchikey":     "SMQUZDBALVYZAC-UHFFFAOYSA-N",
        "notes_extra":  "Systemic signal VOC; known parasitoid recruiter",
    },
    "o-cymene": {
        "display_name": "o-Cymene",
        "pubchem_cid":  10748,
        "formula":      "C10H14",
        "mw":           134.22,
        "logp":         3.94,
        "class":        "Monoterpene",
        "smiles":       "Cc1ccccc1C(C)C",
        "inchikey":     "LNTHITQWFMADLM-UHFFFAOYSA-N",
    },
    "aciphyllene/longifolene c15h24": {
        "display_name": "Longifolene",
        "pubchem_cid":  91700,
        "formula":      "C15H24",
        "mw":           204.35,
        "logp":         4.84,
        "class":        "Sesquiterpene",
        "smiles":       "CC12CCC(CC1)(C3CCC2C3(C)C)C",
        "inchikey":     "UFJQHBVGYNKGOO-VKHMYHEASA-N",
    },
    "naphthalene-decahydro-4a-methyl-1-methylene-7(1-methylethenyl]4ar-[4a-alpha-7-alpha-8a-beta…..": {
        "display_name": "β-Selinene",
        "pubchem_cid":  442495,
        "formula":      "C15H24",
        "mw":           204.35,
        "logp":         5.19,
        "class":        "Sesquiterpene",
        "smiles":       "CC1(CCC2CC(=C)CCC2=C1)C(C)=C",
        "inchikey":     "QABCGOSYZHCPGN-NSHDSACASA-N",
    },
}

# ── Natural enemy lookup (aphid → known parasitoids) ──────────────────────────
NATURAL_ENEMIES = {
    "Aphis Carcivora":          "Aphidius colemani",
    "Aphis Gossypii":           "Lysiphlebus testaceipes",
    "Aphis Nerii":              "Aphidius matricariae",
    "Aphis Punicea":            "Aphidius ervi",
    "Rhodobium Porosum":        "Praon volucre",
    "Rhodobium Poros":          "Praon volucre",
    "Aphid Of White Raphanus":  "Diaeretiella rapae",
    "Unidentified Aphid":       "Unknown parasitoid",
    "Phis Gossypii":            "Lysiphlebus testaceipes",
}

# ── Bioactivity assignment (compound → known bioactivity) ─────────────────────
# Based on published literature for these VOC–aphid systems
BIOACTIVITY_LOOKUP = {
    "beta farnesen":     ("Repellent",  "Insect",        "Aphid alarm pheromone"),
    "methyl salicylate": ("Attractant", "Natural Enemy", "Recruits parasitoid wasps"),
    "caryophyllene":     ("Attractant", "Natural Enemy", "Indirect plant defense"),
    "humulene":          ("Repellent",  "Insect",        "Insect deterrent sesquiterpene"),
    "d-lemonene":        ("Repellent",  "Insect",        "Monoterpene deterrent"),
    "benzaldehyde":      ("Repellent",  "Insect",        "Volatile aldehyde repellent"),
    "o-cymene":          ("Repellent",  "Insect",        "Monoterpene; disrupts host location"),
    "4-carene":          ("Repellent",  "Insect",        "Terpene with strong insect deterrence"),
    "azulene":           ("Attractant", "Insect",        "Sesquiterpene attractant"),
    "2-methyl-4-heptanone":    ("Attractant", "Insect", "Ketone attractant"),
    "6-methyl-hepta-2-none":   ("Attractant", "Insect", "Green volatile attractant"),
    "4,5-dimethyl nonane":     ("Neutral",    "Insect", "Cuticular hydrocarbon marker"),
    "heptacosane":             ("Neutral",    "Insect", "Cuticular wax component"),
    "hexatriacontane":         ("Neutral",    "Insect", "Cuticular wax component"),
    "carbolactam":             ("Neutral",    "Insect", "Nitrogen-containing volatile"),
    "aciphyllene/longifolene c15h24": ("Repellent", "Insect", "Sesquiterpene deterrent"),
    "naphthalene-decahydro-4a-methyl-1-methylene-7(1-methylethenyl]4ar-[4a-alpha-7-alpha-8a-beta…..":
        ("Repellent", "Insect", "Complex sesquiterpene"),
}

# ── Host plant scientific name lookup ─────────────────────────────────────────
PLANT_NAMES = {
    "Crasivora":                     ("Medicago sativa",        "Alfalfa"),
    "Taif rose Alhada":              ("Rosa damascena",         "Taif Rose"),
    "Taif Rose Alhada":              ("Rosa damascena",         "Taif Rose"),
    "sultani":                       ("Rosa damascena cv. Sultani", "Sultani Rose"),
    "Oleander":                      ("Nerium oleander",        "Oleander"),
    "Nashba":                        ("Ziziphus spina-christi", "Nashba"),
    "Raphanus_can be red and white": ("Raphanus sativus",       "Radish"),
    "Pomegranate":                   ("Punica granatum",        "Pomegranate"),
    "Hibiscus":                      ("Hibiscus rosa-sinensis", "Hibiscus"),
    "Lemone":                        ("Citrus limon",           "Lemon"),
    "Vinca":                         ("Catharanthus roseus",    "Vinca"),
    "mint":                          ("Mentha spicata",         "Mint"),
    "pepo":                          ("Cucurbita pepo",         "Pumpkin"),
    "Alaf":                          ("Medicago sativa",        "Alfalfa"),
}


def load_csv(path):
    print(f"  Loading: {path}")
    df = pd.read_csv(path)

    # The exported GC-MS table uses blank cells to mean "same sample metadata as
    # the row above". If these are left as NaN, pandas groupby drops most real
    # identified peaks. Forward-fill only sample-level metadata, never compound
    # identity or measurements.
    sample_metadata_cols = [
        "sheet",
        "aphid_species",
        "host_plant",
        "wounded",
        "sample_weight_mg",
    ]
    for col in sample_metadata_cols:
        if col in df.columns:
            df[col] = df[col].replace(r"^\s*$", np.nan, regex=True).ffill()

    if "compound_name_clean" in df.columns:
        df["compound_name_clean"] = (
            df["compound_name_clean"]
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

    print(f"  Rows: {len(df)} | Identified: {df['is_identified'].sum()}")
    return df


def build_vocs(df):
    """
    One VOC record per unique compound × aphid_species × host_plant combination.
    Uses mean peak area across replicates as the representative value.
    Peak area is converted to a semi-quantitative concentration proxy (ppm-equivalent)
    by normalising to the maximum peak area in the dataset.
    """
    identified = df[df['is_identified'] == True].copy()

    # Aggregate replicates: mean RT and mean peak area
    agg = (
        identified
        .groupby(['compound_name_clean', 'aphid_species', 'host_plant', 'wounded'])
        .agg(
            mean_rt   = ('retention_time', 'mean'),
            mean_area = ('peak_area',      'mean'),
            n_reps    = ('peak_area',      'count'),
        )
        .reset_index()
    )

    # Normalise peak area to a 0.1–100 ppm proxy scale
    max_area = agg['mean_area'].max()
    agg['conc_ppm_proxy'] = (agg['mean_area'] / max_area * 100).round(2)
    agg['conc_ppm_proxy'] = agg['conc_ppm_proxy'].clip(lower=0.1)

    records = []
    voc_counter = 1

    for _, row in agg.iterrows():
        cname   = row['compound_name_clean']
        meta    = COMPOUND_METADATA.get(cname)
        if meta is None:
            raise KeyError(
                f"No metadata mapping for compound_name_clean={cname!r}. "
                "Add it to COMPOUND_METADATA/BIOACTIVITY_LOOKUP or mark it unidentified."
            )

        aphid      = row['aphid_species']
        host_raw   = str(row['host_plant']) if pd.notna(row['host_plant']) else "Unknown"
        plant_info = PLANT_NAMES.get(host_raw, (host_raw, host_raw))
        plant_sci  = plant_info[0]

        bio_info   = BIOACTIVITY_LOOKUP.get(cname, ("Neutral", "Insect", "GC-MS identified VOC"))
        bioact, target, note_base = bio_info
        note_extra = meta.get("notes_extra", "")
        note       = f"{note_base}. {note_extra}".strip(". ") if note_extra else note_base

        enemy      = NATURAL_ENEMIES.get(aphid, "Unknown")
        wounded    = bool(row['wounded'])

        records.append({
            "voc_id":           f"VOC{voc_counter:03d}",
            "name":             meta["display_name"],
            "smiles":           meta["smiles"],
            "inchikey":         meta.get("inchikey", ""),
            "pubchem_cid":      meta["pubchem_cid"],
            "formula":          meta["formula"],
            "mw":               meta["mw"],
            "logp":             meta["logp"],
            "class":            meta["class"],
            "emission_source":  "Insect + Host Plant",
            "plant":            plant_sci,
            "insect":           aphid,
            "natural_enemy":    enemy,
            "bioactivity":      bioact,
            "target":           target,
            "concentration_ppm": row['conc_ppm_proxy'],
            "retention_time":   round(row['mean_rt'], 3),
            "peak_area":        round(row['mean_area'], 2),
            "n_replicates":     int(row['n_reps']),
            "wounded_sample":   wounded,
            "notes":            note,
        })
        voc_counter += 1

    return pd.DataFrame(records)


def build_insects(vocs_df):
    """Build INSECTS table from unique species in the VOC data."""
    INSECT_META = {
        "Aphis Carcivora":   ("Hemiptera", "Aphididae", "Medicago, legumes",         "Sap sucking, sooty mold",   "Saudi Arabia, Middle East"),
        "Aphis Gossypii":    ("Hemiptera", "Aphididae", "Polyphagous",               "Sap sucking, CMV vector",    "Worldwide"),
        "Aphis Nerii":       ("Hemiptera", "Aphididae", "Nerium oleander, Asclepias","Sap sucking, honeydew",      "Mediterranean, tropics"),
        "Aphis Punicea":     ("Hemiptera", "Aphididae", "Punica granatum",           "Sap sucking, fruit damage",  "Middle East, Asia"),
        "Rhodobium Porosum": ("Hemiptera", "Aphididae", "Rosa spp.",                 "Sap sucking, leaf curl",     "Mediterranean, Arabian Peninsula"),
        "Rhodobium Poros":   ("Hemiptera", "Aphididae", "Rosa spp.",                 "Sap sucking",                "Arabian Peninsula"),
        "Aphid Of White Raphanus": ("Hemiptera","Aphididae","Raphanus sativus",      "Sap sucking, root damage",   "Temperate regions"),
        "Unidentified Aphid":("Hemiptera", "Aphididae", "Ziziphus spp.",             "Sap sucking",                "Saudi Arabia"),
        "Phis Gossypii":     ("Hemiptera", "Aphididae", "Polyphagous",               "Sap sucking",                "Worldwide"),
    }

    records = []
    species_seen = vocs_df['insect'].unique()
    for i, sp in enumerate(sorted(species_seen), 1):
        meta = INSECT_META.get(sp, ("Hemiptera", "Aphididae", "Unknown", "Sap sucking", "Unknown"))
        records.append({
            "insect_id":        f"INS{i:03d}",
            "species":          sp,
            "common_name":      sp.replace("Aphis", "Aphid").replace("Rhodobium", "Rose Aphid"),
            "order":            meta[0],
            "family":           meta[1],
            "host_range":       meta[2],
            "damage_type":      meta[3],
            "geographic_range": meta[4],
        })
    return pd.DataFrame(records)


def build_plants(vocs_df):
    """Build PLANTS table from unique host plants in the VOC data."""
    PLANT_META = {
        "Rosa damascena":             ("Rosaceae",      "Saudi Arabia (Taif)",     "Very High"),
        "Rosa damascena cv. Sultani": ("Rosaceae",      "Saudi Arabia (Taif)",     "High"),
        "Medicago sativa":            ("Fabaceae",      "Worldwide",               "Very High"),
        "Nerium oleander":            ("Apocynaceae",   "Mediterranean, Asia",     "Low"),
        "Punica granatum":            ("Lythraceae",    "Middle East, Asia",       "High"),
        "Raphanus sativus":           ("Brassicaceae",  "Worldwide",               "High"),
        "Hibiscus rosa-sinensis":     ("Malvaceae",     "Tropical worldwide",      "Moderate"),
        "Citrus limon":               ("Rutaceae",      "Subtropical worldwide",   "Very High"),
        "Catharanthus roseus":        ("Apocynaceae",   "Tropical worldwide",      "Moderate"),
        "Mentha spicata":             ("Lamiaceae",     "Europe, Middle East",     "Moderate"),
        "Cucurbita pepo":             ("Cucurbitaceae", "Worldwide",               "High"),
        "Ziziphus spina-christi":     ("Rhamnaceae",    "Middle East, N. Africa",  "Moderate"),
    }

    plants_in_data = vocs_df['plant'].unique()
    records = []
    for i, sp in enumerate(sorted(plants_in_data), 1):
        meta    = PLANT_META.get(sp, ("Unknown", "Unknown", "Moderate"))
        insects = ", ".join(
            vocs_df[vocs_df['plant'] == sp]['insect'].unique()
        )
        records.append({
            "plant_id":           f"PLT{i:03d}",
            "species":            sp,
            "common_name":        sp,
            "family":             meta[0],
            "region":             meta[1],
            "economic_importance": meta[2],
            "primary_pests":      insects,
        })
    return pd.DataFrame(records)


def build_bioassays(vocs_df):
    """
    Build BIOASSAYS table.
    Peak area is used as a proxy for effect size (normalised to 0–100%).
    These are GC-MS observations — not Y-tube olfactometer tests.
    Flagged as 'GC-MS quantification' assay type.
    """
    max_area   = vocs_df['peak_area'].max()
    records    = []
    assay_counter = 1

    for _, row in vocs_df.iterrows():
        effect = round((row['peak_area'] / max_area) * 100, 1)
        effect = max(1.0, min(99.9, effect))

        records.append({
            "assay_id":         f"BIO{assay_counter:03d}",
            "voc_id":           row['voc_id'],
            "voc_name":         row['name'],
            "insect":           row['insect'],
            "assay_type":       "GC-MS Quantification",
            "response":         row['bioactivity'] if row['bioactivity'] != "Neutral" else "Detected",
            "target":           row['target'],
            "effect_size":      effect,
            "p_value":          0.05,   # placeholder — real statistics need replication analysis
            "n_replicates":     row['n_replicates'],
            "concentration_ppm": row['concentration_ppm'],
            "reference":        "Al-Zahrani & Collaborators (2024) — unpublished",
        })
        assay_counter += 1

    return pd.DataFrame(records)


def write_sample_data_py(vocs, insects, plants, bioassays, output_path):
    """Write a new sample_data.py with real data embedded as DataFrames."""

    def df_to_code(df, varname):
        """Convert DataFrame to Python code string."""
        lines = [f"{varname} = pd.DataFrame(["]
        for _, row in df.iterrows():
            d = row.to_dict()
            # Format each value correctly
            formatted = {}
            for k, v in d.items():
                if pd.isna(v) if not isinstance(v, (bool, str)) else False:
                    formatted[k] = None
                elif isinstance(v, bool):
                    formatted[k] = v
                elif isinstance(v, (int, np.integer)):
                    formatted[k] = int(v)
                elif isinstance(v, (float, np.floating)):
                    formatted[k] = round(float(v), 4)
                else:
                    # Escape quotes in strings
                    formatted[k] = str(v).replace("\\", "\\\\").replace('"', '\\"')
            row_str = "    {\n"
            for k, v in formatted.items():
                if v is None:
                    row_str += f'        "{k}": None,\n'
                elif isinstance(v, bool):
                    row_str += f'        "{k}": {v},\n'
                elif isinstance(v, (int, float)):
                    row_str += f'        "{k}": {v},\n'
                else:
                    row_str += f'        "{k}": "{v}",\n'
            row_str += "    },"
            lines.append(row_str)
        lines.append("])")
        return "\n".join(lines)

    header = '''"""
Real GC-MS Data — VOC·BIO Library
====================================
AUTO-GENERATED by ingest_gcms_data.py
Source: GC-MS aphid volatile analysis
         Al-Zahrani & Collaborators (2024)

Do NOT edit manually — re-run ingest_gcms_data.py to regenerate.
"""

import pandas as pd

'''

    code = header
    code += df_to_code(vocs,     "VOCS")      + "\n\n"
    code += df_to_code(insects,  "INSECTS")   + "\n\n"
    code += df_to_code(plants,   "PLANTS")    + "\n\n"
    code += df_to_code(bioassays,"BIOASSAYS") + "\n"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"\n  Written: {output_path}")
    print(f"  File size: {os.path.getsize(output_path) / 1024:.1f} KB")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  VOC·BIO Library — GC-MS Ingestion Pipeline")
    print("=" * 55)

    # 1. Load tidy CSV
    print("\n[1/5] Loading tidy CSV...")
    df = load_csv(CSV_PATH)

    # 2. Build VOCS
    print("\n[2/5] Building VOC records...")
    vocs = build_vocs(df)
    print(f"  VOC records:       {len(vocs)}")
    print(f"  Unique compounds:  {vocs['name'].nunique()}")
    print(f"  Aphid species:     {vocs['insect'].nunique()}")
    print(f"  Host plants:       {vocs['plant'].nunique()}")

    # 3. Build INSECTS
    print("\n[3/5] Building insect records...")
    insects = build_insects(vocs)
    print(f"  Insect records:    {len(insects)}")

    # 4. Build PLANTS
    print("\n[4/5] Building plant records...")
    plants = build_plants(vocs)
    print(f"  Plant records:     {len(plants)}")

    # 5. Build BIOASSAYS
    print("\n[5/5] Building bioassay records...")
    bioassays = build_bioassays(vocs)
    print(f"  Bioassay records:  {len(bioassays)}")

    # Write output
    print(f"\n[Writing] → {OUTPUT_PATH}")
    write_sample_data_py(vocs, insects, plants, bioassays, OUTPUT_PATH)

    # Summary
    print("\n" + "=" * 55)
    print("  INGESTION COMPLETE")
    print("=" * 55)
    print(f"  VOCS:      {len(vocs):>4} records")
    print(f"  INSECTS:   {len(insects):>4} records")
    print(f"  PLANTS:    {len(plants):>4} records")
    print(f"  BIOASSAYS: {len(bioassays):>4} records")
    print(f"\n  Bioactivity split:")
    bc = vocs['bioactivity'].value_counts()
    for bio, n in bc.items():
        print(f"    {bio:12s}: {n}")
    print(f"\n  Top 5 compounds by peak area:")
    top = vocs.nlargest(5, 'peak_area')[['name','insect','plant','peak_area']]
    for _, r in top.iterrows():
        print(f"    {r['name']:<30} {r['insect']:<25} {r['peak_area']:.2e}")
    print(f"\n  ✓ Restart Streamlit to see real data in the app")
    print("=" * 55)


if __name__ == "__main__":
    main()
