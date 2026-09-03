"""
Cheminformatics utilities
==========================
Structure RENDERING  → PubChem REST API (works on any server, no display needed)
Descriptor calculation → RDKit (works headless, no drawing backend required)
Structural similarity search      → RDKit Morgan fingerprints (headless safe)

Why this approach:
  Streamlit Cloud is a headless Linux container. RDKit's 2D drawing functions
  (MolDraw2D, MolToImage) require a graphics/display backend (Cairo or Pillow
  with Agg). That backend is often missing on cloud hosts, so structure images
  silently fail. The PubChem image API requires nothing locally — it just returns
  a PNG over HTTPS given a compound CID or SMILES.
"""

import urllib.parse

# ── RDKit — imported only for descriptors & fingerprints, NOT for drawing ────
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors, AllChem, DataStructs
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


# ═══════════════════════════════════════════════════════
#  STRUCTURE IMAGE URLS  (PubChem REST API — cloud-safe)
# ═══════════════════════════════════════════════════════

def get_structure_image_url(pubchem_cid: int = None,
                            smiles: str = None,
                            width: int = 300,
                            height: int = 200) -> str:
    """
    Return a PubChem image URL for a compound.

    Priority:
      1. PubChem CID  → fastest, most reliable
      2. SMILES string → URL-encoded, slightly slower

    The URL returns a PNG directly — use in st.image() or an <img> tag.
    No local rendering, no display backend required.
    """
    if pubchem_cid and int(pubchem_cid) > 0:
        # CID-based image — most reliable
        return (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
            f"{int(pubchem_cid)}/PNG"
            f"?image_size={width}x{height}"
        )
    elif smiles:
        # SMILES-based image — fallback
        encoded = urllib.parse.quote(smiles, safe="")
        return (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/"
            f"{encoded}/PNG"
            f"?image_size={width}x{height}"
        )
    return ""


def get_structure_image_urls_batch(cids: list, width: int = 300, height: int = 200) -> list:
    """Return a list of PubChem image URLs for a list of CIDs."""
    return [get_structure_image_url(pubchem_cid=cid, width=width, height=height)
            for cid in cids]


# ═══════════════════════════════════════════════════════
#  MOLECULAR DESCRIPTORS  (RDKit — headless safe)
# ═══════════════════════════════════════════════════════

def mol_from_smiles(smiles: str):
    if not RDKIT_AVAILABLE:
        return None
    try:
        return Chem.MolFromSmiles(smiles)
    except Exception:
        return None


def compute_descriptors(smiles: str) -> dict:
    """
    Compute key molecular descriptors for a VOC.
    Returns empty dict if RDKit is unavailable or SMILES is invalid.
    """
    if not RDKIT_AVAILABLE:
        return {}
    mol = mol_from_smiles(smiles)
    if mol is None:
        return {}
    try:
        return {
            "Molecular Weight":         round(Descriptors.ExactMolWt(mol), 3),
            "LogP (Wildman-Crippen)":   round(Descriptors.MolLogP(mol), 3),
            "TPSA (Å²)":               round(Descriptors.TPSA(mol), 3),
            "H-Bond Donors":            rdMolDescriptors.CalcNumHBD(mol),
            "H-Bond Acceptors":         rdMolDescriptors.CalcNumHBA(mol),
            "Rotatable Bonds":          rdMolDescriptors.CalcNumRotatableBonds(mol),
            "Ring Count":               rdMolDescriptors.CalcNumRings(mol),
            "Aromatic Rings":           rdMolDescriptors.CalcNumAromaticRings(mol),
            "Heavy Atom Count":         mol.GetNumHeavyAtoms(),
            "Fraction Csp3":            round(rdMolDescriptors.CalcFractionCSP3(mol), 3),
        }
    except Exception:
        return {}


def get_lipinski_verdict(smiles: str) -> dict:
    """VOC volatility profile based on physicochemical rules."""
    if not RDKIT_AVAILABLE:
        return {}
    mol = mol_from_smiles(smiles)
    if mol is None:
        return {}
    try:
        mw   = Descriptors.ExactMolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd  = rdMolDescriptors.CalcNumHBD(mol)
        hba  = rdMolDescriptors.CalcNumHBA(mol)
        tpsa = Descriptors.TPSA(mol)
        rot  = rdMolDescriptors.CalcNumRotatableBonds(mol)

        volatile = mw < 300 and logp < 6 and tpsa < 80
        return {
            "MW < 300 (volatile)":       ("✅" if mw   < 300 else "❌") + f"  {mw:.1f} g/mol",
            "LogP < 6 (semi-volatile)":  ("✅" if logp <   6 else "❌") + f"  {logp:.2f}",
            "TPSA < 80 Å² (airborne)":  ("✅" if tpsa <  80 else "❌") + f"  {tpsa:.1f} Å²",
            "H-Bond Donors ≤ 1":         ("✅" if hbd  <=  1 else "❌") + f"  {hbd}",
            "H-Bond Acceptors ≤ 4":      ("✅" if hba  <=  4 else "❌") + f"  {hba}",
            "Rotatable Bonds ≤ 10":      ("✅" if rot  <= 10 else "❌") + f"  {rot}",
            "🧪 VOC Volatility Profile": "HIGH" if volatile else "MODERATE",
        }
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════
#  STRUCTURAL SIMILARITY SEARCH  (RDKit Morgan fingerprints — headless safe)
# ═══════════════════════════════════════════════════════

def tanimoto_similarity(smiles1: str, smiles2: str, radius: int = 2) -> float:
    """Tanimoto coefficient between two molecules via Morgan fingerprints."""
    if not RDKIT_AVAILABLE:
        return 0.0
    mol1 = mol_from_smiles(smiles1)
    mol2 = mol_from_smiles(smiles2)
    if mol1 is None or mol2 is None:
        return 0.0
    try:
        fp1 = AllChem.GetMorganFingerprintAsBitVect(mol1, radius, nBits=2048)
        fp2 = AllChem.GetMorganFingerprintAsBitVect(mol2, radius, nBits=2048)
        return round(DataStructs.TanimotoSimilarity(fp1, fp2), 4)
    except Exception:
        return 0.0


def similarity_matrix(smiles_list: list, names: list):
    """Pairwise Tanimoto structural similarity matrix as a DataFrame."""
    import pandas as pd
    n = len(smiles_list)
    matrix = [[tanimoto_similarity(smiles_list[i], smiles_list[j])
               for j in range(n)] for i in range(n)]
    return pd.DataFrame(matrix, index=names, columns=names)


# ── backwards-compat stubs (so old code that calls these won't crash) ─────────
def draw_molecule_svg(*args, **kwargs) -> str:
    return ""

def draw_molecule_png_b64(*args, **kwargs) -> str:
    return ""
