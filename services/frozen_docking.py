"""Read-only access to the frozen Phase 5D docking evidence.

The application consumes authoritative files verbatim. It never docks, adjusts
scores, or infers experimental affinity from these computational predictions.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DOCKING_DIR = ROOT / "data" / "docking"
SOURCES = {
    "rank1": DOCKING_DIR / "docking_runs_rank1.csv",
    "poses": DOCKING_DIR / "docking_poses.csv",
    "pairs": DOCKING_DIR / "docking_pairs.csv",
    "comparison": DOCKING_DIR / "receptor_comparison.csv",
    "validation": DOCKING_DIR / "validation_summary.csv",
    "interactions": DOCKING_DIR / "representative_interactions.csv",
    "stability": DOCKING_DIR / "stability_classifications.csv",
    "ligands": DOCKING_DIR / "ligand_validation.csv",
    "panel": DOCKING_DIR / "production_voc_panel.csv",
    "receptors": DOCKING_DIR / "receptor_validation.csv",
    "representatives": DOCKING_DIR / "representative_complexes.csv",
    "protocol": DOCKING_DIR / "docking_protocol.json",
}
DISPLAY_DOWNLOADS = {
    "Receptor–VOC pair summary": "pairs",
    "Seed-level rank-1 results": "rank1",
    "Pose-level results": "poses",
    "Receptor comparison": "comparison",
    "Stability classification": "stability",
    "Representative interactions": "interactions",
    "Validation summary": "validation",
}
STEREO_CAVEAT = (
    "The source annotation does not establish stereochemistry. The docked 3D "
    "coordinates represent one computational realization of the constitutionally "
    "matched candidate and should not be interpreted as experimental "
    "stereochemical assignment."
)


def _read_csv(key: str) -> pd.DataFrame:
    path = SOURCES[key]
    if not path.is_file():
        raise FileNotFoundError(f"Frozen docking source is unavailable: {path.name}")
    return pd.read_csv(path)


@lru_cache(maxsize=None)
def _cached_table(key: str) -> pd.DataFrame:
    return _read_csv(key)


def table(key: str) -> pd.DataFrame:
    return _cached_table(key).copy()


def pair_results() -> pd.DataFrame:
    pairs = table("pairs")
    stability = table("stability")[[
        "PDB_ID", "bio_id", "final_classification", "criterion", "rule_status",
        "mean_contact_residue_jaccard", "major_pose_cluster_size", "pose_cluster_count",
    ]]
    return pairs.merge(stability, on=["PDB_ID", "bio_id"], how="left", validate="one_to_one")


def ligand_metadata() -> pd.DataFrame:
    panel = table("panel")
    prepared = table("ligands")
    keep = [
        "bio_id", "candidate_chemical_name", "canonical_smiles", "stereochemistry",
        "rotatable_bonds", "heavy_atoms", "preparation_status", "validation_status",
    ]
    merged = panel.merge(prepared[keep], on="bio_id", how="left", validate="one_to_one")
    order = merged["bio_id"].str.extract(r"(\d+)")[0].astype(int)
    return merged.assign(_order=order).sort_values("_order").drop(columns="_order")


def rank1_results() -> pd.DataFrame:
    return table("rank1")


def pose_results() -> pd.DataFrame:
    return table("poses")


def representative_complexes() -> pd.DataFrame:
    return table("representatives")


def validation_results() -> pd.DataFrame:
    return table("validation")


def receptor_results() -> pd.DataFrame:
    return table("receptors")


def protocol() -> dict:
    return json.loads(SOURCES["protocol"].read_text(encoding="utf-8"))


def source_bytes(key: str) -> bytes:
    """Return exact authoritative bytes for an unmodified download."""
    return SOURCES[key].read_bytes()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scientific_contract() -> dict[str, object]:
    pairs = pair_results()
    rank1 = rank1_results()
    poses = pose_results()
    ligands = ligand_metadata()
    comparison = table("comparison")
    stability = table("stability")
    grouped = pairs.groupby("receptor_name")["median_rank1_score"]
    mvic = pairs[pairs["receptor_name"] == "MvicOBP3"]
    nrib = pairs[pairs["receptor_name"] == "NribOBP3"]
    diffs = comparison.set_index("bio_id")["absolute_difference"]
    variable = stability[stability["final_classification"] == "VARIABLE"]
    variable_ids = set(variable["receptor_name"] + "–" + variable["bio_id"])
    checks = {
        "20 production ligands": ligands["bio_id"].nunique() == 20,
        "2 production OBPs": pairs["receptor_name"].nunique() == 2,
        "40 receptor–VOC pairs": len(pairs) == 40,
        "200 rank-1 runs": len(rank1) == 200 and rank1["docking_run_id"].nunique() == 200,
        "2,000 retained poses": len(poses) == 2000,
        "five seeds per pair": bool((rank1.groupby(["receptor_name", "bio_id"])["seed"].nunique() == 5).all()),
        "Tier A/B/C = 11/9/0": (
            int((ligands["evidence_tier"] == "Tier A").sum()) == 11
            and int((ligands["evidence_tier"] == "Tier B").sum()) == 9
            and int((ligands["evidence_tier"] == "Tier C").sum()) == 0
        ),
        "Mvic headline median": np.isclose(float(grouped.median()["MvicOBP3"]), -4.712, atol=1e-12),
        "Nrib headline median": np.isclose(float(grouped.median()["NribOBP3"]), -4.7895, atol=1e-12),
        "Bio59 most negative for both": (
            mvic.loc[mvic["median_rank1_score"].idxmin(), "bio_id"] == "Bio59"
            and nrib.loc[nrib["median_rank1_score"].idxmin(), "bio_id"] == "Bio59"
        ),
        "Bio42 least negative for both": (
            mvic.loc[mvic["median_rank1_score"].idxmax(), "bio_id"] == "Bio42"
            and nrib.loc[nrib["median_rank1_score"].idxmax(), "bio_id"] == "Bio42"
        ),
        "Bio39 largest receptor contrast": diffs.idxmax() == "Bio39" and np.isclose(float(diffs.max()), 0.525, atol=1e-12),
        "37 stable / 3 variable": (
            int((stability["final_classification"] == "STABLE").sum()) == 37
            and int((stability["final_classification"] == "VARIABLE").sum()) == 3
        ),
        "correct variable pairs": variable_ids == {"MvicOBP3–Bio42", "NribOBP3–Bio49", "NribOBP3–Bio56"},
    }
    return {"ok": all(checks.values()), "checks": checks}


def assert_scientific_contract() -> None:
    result = scientific_contract()
    failed = [name for name, passed in result["checks"].items() if not passed]
    if failed:
        raise RuntimeError("Frozen docking evidence failed consistency checks: " + "; ".join(failed))


def prepared_receptor_path(pdb_id: str) -> Path:
    receptors = receptor_results()
    row = receptors.loc[receptors["PDB_ID"] == pdb_id].iloc[0]
    pdbqt = ROOT / str(row["prepared_pdbqt"])
    heavy = pdbqt.with_name(pdbqt.name.replace("_prepared.pdbqt", "_heavy.pdb"))
    return heavy if heavy.exists() else pdbqt


def filtered_pose_text(relative_path: str, bio_id: str) -> str:
    """Read a frozen pose for display, excluding Bio38 Meeko G0 dummy atoms."""
    lines = (ROOT / relative_path).read_text(encoding="utf-8", errors="replace").splitlines()
    if bio_id == "Bio38":
        lines = [line for line in lines if not (
            line.startswith(("ATOM", "HETATM")) and line[12:16].strip() == "G0"
        )]
    return "\n".join(lines) + "\n"
