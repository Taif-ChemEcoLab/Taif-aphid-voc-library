# Taif Aphid VOC Library

Public Streamlit deployment package for the VOC-BIO library.

## Streamlit Cloud

Use these settings when creating the app:

- Repository: `Taif-ChemEcoLab/Taif-aphid-voc-library`
- Branch: `main`
- Main file path: `app.py`
- Python dependencies: installed from `requirements.txt`

No `.env` file is required for the public app. The bundled assistant page is local
and rule-based; it does not call OpenAI or any external language-model API.

## Included Files

- `app.py`: Streamlit entry point.
- `modules/`: Streamlit page modules used by the sidebar.
- `utils/chem_utils.py`: PubChem image URLs plus optional RDKit descriptors and similarity helpers.
- `data/sample_data.py`: public, schema-compatible demonstration dataset.
- `requirements.txt`: packages needed by Streamlit Cloud.

## Excluded Files

The deploy package intentionally excludes:

- `.env` and API keys.
- `__pycache__` and compiled Python files.
- raw GC-MS CSV/XLSX files.
- ingestion scripts used to generate private datasets.
- OpenAI/RAG development utilities.
- private receptor/docking curation drafts.

The public demo dataset preserves the application schema but does not publish raw
peak-area exports, replicate-level source files, unpublished curation tables, or
credentials.

## Local Run

```bash
pip install -r requirements.txt
streamlit run app.py
```
