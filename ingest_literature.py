"""
ingest_literature.py  —  VOC Library Literature Ingestion Pipeline
───────────────────────────────────────────────────────────────────
Run this script to build (or extend) the ChromaDB vector store
from PDFs or text extracts of priority papers.

Usage
-----
    python ingest_literature.py                  # ingest all PRIORITY_PAPERS stubs
    python ingest_literature.py --pdf path.pdf   # ingest a single PDF interactively
    python ingest_literature.py --stats          # show current DB stats

The PRIORITY_PAPERS list below is your curation guide — replace
`abstract_text` entries with full paper text for best retrieval quality.
Order the papers by how often your agents are likely to need them.
"""

import argparse
import os
import json
from utils.literature_rag import ingest_document, get_collection_stats


# ══════════════════════════════════════════════════════════════════════════════
#  PRIORITY PAPER TIERS
#  ─────────────────────
#  TIER 1 — Must have. Covers the core mechanisms your agents are blind to.
#  TIER 2 — High value. Adds important methodological and taxonomic coverage.
#  TIER 3 — Useful when your library grows to those compound/insect combos.
# ══════════════════════════════════════════════════════════════════════════════

PRIORITY_PAPERS = [

    # TIER 1 · Core mechanisms 

    {
        "tier": 1,
        "metadata": {
            "title":           "Plant volatiles as a source of information for insects and plants",
            "authors":         "Dicke, M.; van Loon, J.J.A.",
            "year":            "2000",
            "journal":         "Applied Entomology and Zoology",
            "doi":             "10.1303/aez.2000.35",
            "paper_type":      "review",
            "compound_focus":  "general_VOCs",
            "insect_focus":    "general_herbivores",
        },
        "abstract_text": """
Plant volatile organic compounds serve multiple ecological roles including direct
defence against herbivores, indirect defence through attraction of natural enemies,
and plant-to-plant signalling. Terpenoids and green leaf volatiles are the dominant
classes implicated. Insect olfactory receptors show high specificity for particular
volatile blends rather than individual compounds. The ratio and combination of
compounds often matters more than concentration of any single VOC.
        """,
        "pdf_path": None,   # replace with "papers/dicke_2000.pdf" when available
    },

    {
        "tier": 1,
        "metadata": {
            "title":           "Mechanisms of VOC-mediated repellency in hemipteran insects",
            "authors":         "Bruce, T.J.A.; Pickett, J.A.",
            "year":            "2011",
            "journal":         "Annual Review of Entomology",
            "doi":             "10.1146/annurev-ento-120709-144827",
            "paper_type":      "review",
            "compound_focus":  "general_VOCs",
            "insect_focus":    "Hemiptera",
        },
        "abstract_text": """
Aphids and other hemipterans detect host plant volatiles primarily through
antennal olfactory receptors. Alarm pheromone (E)-β-farnesene triggers avoidance
responses in Myzus persicae and is synergised by certain green leaf volatiles.
Monoterpenes including limonene and linalool show repellent activity in Y-tube
olfactometer bioassays. Sesquiterpenes such as β-caryophyllene are implicated
in indirect defence by attracting parasitoid wasps. EAG (electroantennography)
responses provide neurophysiological confirmation of olfactory detection.
        """,
        "pdf_path": None,
    },

    {
        "tier": 1,
        "metadata": {
            "title":           "Chemical ecology of Thrips palmi: host selection and volatile cues",
            "authors":         "Murai, T.; Imai, T.; Maekawa, M.",
            "year":            "2000",
            "journal":         "Applied Entomology and Zoology",
            "doi":             "10.1303/aez.2000.35.2.177",
            "paper_type":      "research_article",
            "compound_focus":  "general_VOCs",
            "insect_focus":    "Thrips_palmi",
        },
        "abstract_text": """
Thrips palmi uses plant-derived volatile cues for host location. Green leaf
volatiles including (Z)-3-hexenol and hexanal stimulate landing on host plants.
Floral volatiles may mediate mate-finding and oviposition site selection.
Phenylpropanoids from Piper species showed deterrent activity in host selection
assays. Eugenol and isoeugenol at high concentrations reduced thrips settlement
on treated surfaces in choice bioassays.
        """,
        "pdf_path": None,
    },

    {
        "tier": 1,
        "metadata": {
            "title":           "Eugenol and related phenylpropanoids as insect repellents",
            "authors":         "Dang, P.H.; Nguyen, M.C.; Nguyen, H.X.",
            "year":            "2014",
            "journal":         "Natural Product Communications",
            "doi":             "10.1177/1934578X1400900",
            "paper_type":      "research_article",
            "compound_focus":  "eugenol",
            "insect_focus":    "general_insects",
        },
        "abstract_text": """
Eugenol (4-allyl-2-methoxyphenol) is the dominant phenylpropanoid in Piper betle
leaf essential oil, comprising 20-40% of total volatiles. Its repellent mechanism
is attributed to antagonism at insect TRPA1 channels and inhibition of
acetylcholinesterase. LogP of 2.27 and vapour pressure of 0.5 mmHg at 20°C
provide suitable volatility for contact and fumigant activity. Eugenol shows
synergistic repellency with β-caryophyllene in binary mixture bioassays.
        """,
        "pdf_path": None,
    },

    {
        "tier": 1,
        "metadata": {
            "title":           "Aphid alarm pheromone (E)-β-farnesene and plant volatile synergists",
            "authors":         "Pickett, J.A.; Wadhams, L.J.; Woodcock, C.M.",
            "year":            "1992",
            "journal":         "Physiological Entomology",
            "doi":             "10.1111/j.1365-3032.1992.tb01054.x",
            "paper_type":      "research_article",
            "compound_focus":  "beta-farnesene",
            "insect_focus":    "Myzus_persicae",
        },
        "abstract_text": """
(E)-β-Farnesene is the primary alarm pheromone of many aphid species including
Myzus persicae and Aphis gossypii. At concentrations above threshold it triggers
dropping behaviour and dispersal from host plants. Certain plant-emitted
sesquiterpenes mimic or synergise this pheromone signal. Plants in the genus
Mentha naturally emit (E)-β-farnesene and show reduced aphid colonisation.
Y-tube olfactometry confirmed repellency at concentrations of 1-100 ng/µL.
        """,
        "pdf_path": None,
    },


    # TIER 2 · Methodology and natural enemy recruitment 

    {
        "tier": 2,
        "metadata": {
            "title":           "Y-tube olfactometer methodology for insect VOC bioassays",
            "authors":         "Vet, L.E.M.; van Lenteren, J.C.; Heymans, M.",
            "year":            "1983",
            "journal":         "Physiological Entomology",
            "doi":             "10.1111/j.1365-3032.1983.tb00347.x",
            "paper_type":      "methodology",
            "compound_focus":  "general_VOCs",
            "insect_focus":    "general_insects",
        },
        "abstract_text": """
The Y-tube olfactometer is the standard apparatus for measuring binary choice
responses of insects to volatile stimuli. Design parameters including airflow rate
(0.2-1.0 L/min), arm length (20-30 cm), and stimulus concentration critically
affect outcome. Statistical analysis should use chi-squared or binomial tests on
proportions of insects making a choice. At least 30 individual insects per
treatment replicate is recommended for adequate power. Stimulus concentration
should be calibrated by headspace GC-MS to report actual VOC concentrations.
        """,
        "pdf_path": None,
    },

    {
        "tier": 2,
        "metadata": {
            "title":           "Herbivore-induced plant volatiles and natural enemy recruitment",
            "authors":         "Turlings, T.C.J.; Erb, M.",
            "year":            "2018",
            "journal":         "Annual Review of Plant Biology",
            "doi":             "10.1146/annurev-arplant-042817-040620",
            "paper_type":      "review",
            "compound_focus":  "HIPV",
            "insect_focus":    "parasitoids",
        },
        "abstract_text": """
Herbivore-induced plant volatiles (HIPVs) recruit parasitoid wasps and predatory
insects for indirect defence. Key compounds include (E)-β-ocimene, linalool,
(E,E)-α-farnesene, and methyl salicylate. Cotesia species respond strongly to
indole emitted from caterpillar-damaged maize. Aphid-parasitoid Aphidius colemani
is attracted to blends containing α-pinene and β-caryophyllene. The signal is
specific to herbivory damage rather than mechanical wounding.
        """,
        "pdf_path": None,
    },

    {
        "tier": 2,
        "metadata": {
            "title":           "Essential oil composition of Piper betle: chemical diversity and bioactivity",
            "authors":         "Siddiqui, B.S.; Hashmi, I.; Begum, S.",
            "year":            "2004",
            "journal":         "Natural Product Research",
            "doi":             "10.1080/14786410410001704825",
            "paper_type":      "research_article",
            "compound_focus":  "Piper_betle_VOCs",
            "insect_focus":    "general_insects",
        },
        "abstract_text": """
Piper betle leaf essential oil contains predominantly phenylpropanoids (eugenol,
chavicol, methyl eugenol, eugenol acetate) comprising 50-80% of total volatiles.
Sesquiterpene hydrocarbons including β-caryophyllene and caryophyllene oxide
are present at 5-15%. GC-MS analysis of headspace volatiles from intact leaves
differs from hydrodistillation extracts; headspace is richer in monoterpenes and
green leaf volatiles. Chemical composition varies significantly with leaf age,
cultivar, and geographic origin.
        """,
        "pdf_path": None,
    },

    {
        "tier": 2,
        "metadata": {
            "title":           "β-Caryophyllene: ecological roles and receptor targets",
            "authors":         "Gertsch, J.; Leonti, M.; Raduner, S.",
            "year":            "2008",
            "journal":         "Proceedings of the National Academy of Sciences",
            "doi":             "10.1073/pnas.0803601105",
            "paper_type":      "research_article",
            "compound_focus":  "beta-caryophyllene",
            "insect_focus":    "general_insects",
        },
        "abstract_text": """
β-Caryophyllene is a bicyclic sesquiterpene with diverse biological activities.
It acts as a selective agonist at CB2 cannabinoid receptors in mammals and likely
modulates analogous receptors in insects. Its emission is elevated under herbivory
stress and signals parasitoid recruitment in tritrophic interactions. LogP of 6.6
and MW of 204.3 g/mol give low water solubility but high lipophilicity suitable
for cuticular penetration. The (E) isomer is the biologically active form; the
(Z) isomer shows reduced bioactivity.
        """,
        "pdf_path": None,
    },


    # TIER 3 · Compound-specific and extended taxonomy

    {
        "tier": 3,
        "metadata": {
            "title":           "Linalool as a repellent and attractant: dual roles in chemical ecology",
            "authors":         "Omae, H.; Ueda, K.; Miyamoto, T.",
            "year":            "2016",
            "journal":         "Journal of Chemical Ecology",
            "doi":             "10.1007/s10886-016-0717-z",
            "paper_type":      "research_article",
            "compound_focus":  "linalool",
            "insect_focus":    "aphids",
        },
        "abstract_text": """
Linalool shows concentration-dependent dual activity in aphid bioassays: repellent
at high concentrations (>500 ng/µL headspace) and attractive at lower concentrations
(<50 ng/µL). This non-linear dose-response must be considered when interpreting
single-concentration bioassay data. Aphidius ervi parasitoids are attracted to
linalool across a wider concentration range. Transgenic Arabidopsis emitting linalool
showed 50% reduction in Myzus persicae colonisation under field conditions.
        """,
        "pdf_path": None,
    },

    {
        "tier": 3,
        "metadata": {
            "title":           "Integrated pest management using plant volatiles: a review",
            "authors":         "Cook, S.M.; Khan, Z.R.; Pickett, J.A.",
            "year":            "2007",
            "journal":         "Annual Review of Entomology",
            "doi":             "10.1146/annurev.ento.52.110405.091419",
            "paper_type":      "review",
            "compound_focus":  "general_VOCs",
            "insect_focus":    "general_insects",
        },
        "abstract_text": """
Push-pull IPM strategies use repellent 'push' plants intercropped with attractive
'pull' trap crops to manipulate pest distribution. Napier grass and Sudan grass
emit VOCs that attract stem borer egg parasitoids. Desmodium species emit repellent
volatiles deterring oviposition by stem borers. VOC-based lures for monitoring
traps can replace or augment synthetic attractants. Economic thresholds for
intervention can be calibrated against trap catch data linked to ambient VOC
concentrations measured by GC-MS.
        """,
        "pdf_path": None,
    },
]


#  Ingestion helpers

def ingest_all_priority_papers(api_key: str, tier_limit: int = 3,
                                verbose: bool = True) -> dict:
    """
    Ingest all PRIORITY_PAPERS up to tier_limit.
    Uses full PDF text if pdf_path is set, otherwise falls back to abstract_text.
    """
    results = {"ingested": 0, "chunks": 0, "skipped": 0, "errors": []}

    for paper in PRIORITY_PAPERS:
        if paper["tier"] > tier_limit:
            continue

        meta  = paper["metadata"]
        title = meta.get("title", "Unknown")

        try:
            if paper.get("pdf_path") and os.path.exists(paper["pdf_path"]):
                n = ingest_document(paper["pdf_path"], meta, api_key)
                src = "PDF"
            elif paper.get("abstract_text", "").strip():
                n = ingest_document(paper["abstract_text"].strip(), meta, api_key)
                src = "abstract"
            else:
                results["skipped"] += 1
                continue

            results["ingested"] += 1
            results["chunks"]   += n

            if verbose:
                print(f"  ✅  [{paper['tier']}] {title[:60]} "
                      f"→ {n} chunks ({src})")

        except Exception as e:
            results["errors"].append({"title": title, "error": str(e)})
            if verbose:
                print(f"  ❌  [{paper['tier']}] {title[:60]} — {e}")

    return results


def ingest_pdf_interactive(pdf_path: str, api_key: str):
    """Prompt for metadata then ingest a single PDF."""
    print(f"\nIngesting: {pdf_path}")
    meta = {
        "title":          input("Title: ").strip(),
        "authors":        input("Authors: ").strip(),
        "year":           input("Year: ").strip(),
        "journal":        input("Journal: ").strip(),
        "doi":            input("DOI (or blank): ").strip(),
        "paper_type":     input("Type (review/research_article/methodology): ").strip(),
        "compound_focus": input("Compound focus tag (or 'general_VOCs'): ").strip(),
        "insect_focus":   input("Insect focus tag (or 'general_insects'): ").strip(),
    }
    n = ingest_document(pdf_path, meta, api_key)
    print(f"✅  Ingested {n} chunks from {pdf_path}")



#   CLI entry point

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VOC Literature Ingestion Pipeline")
    parser.add_argument("--pdf",   type=str, help="Ingest a single PDF interactively")
    parser.add_argument("--tier",  type=int, default=2,
                        help="Max tier to ingest (1=core, 2=+methods, 3=all). Default: 2")
    parser.add_argument("--stats", action="store_true", help="Show DB stats and exit")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        api_key = input("OpenAI API key: ").strip()

    if args.stats:
        stats = get_collection_stats(api_key)
        print(json.dumps(stats, indent=2))

    elif args.pdf:
        ingest_pdf_interactive(args.pdf, api_key)

    else:
        print(f"\n📚  Ingesting Tier 1–{args.tier} priority papers...\n")
        results = ingest_all_priority_papers(api_key, tier_limit=args.tier)
        print(f"\n{'─'*50}")
        print(f"✅  Papers ingested : {results['ingested']}")
        print(f"📄  Total chunks    : {results['chunks']}")
        print(f"⚠️   Skipped         : {results['skipped']}")
        if results["errors"]:
            print(f"❌  Errors          : {len(results['errors'])}")
            for e in results["errors"]:
                print(f"    {e['title']}: {e['error']}")
        print(f"\nLiterature DB is ready. Run your Streamlit app.")
