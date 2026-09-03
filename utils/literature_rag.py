"""
literature_rag.py  —  VOC Library Literature RAG Module
────────────────────────────────────────────────────────
Provides a ChromaDB-backed vector store for scientific literature,
and a search_literature() tool that slots directly into each agent's
tool-calling loop in multi_agent.py.

Usage
-----
1.  Ingest PDFs / text chunks once:
        from utils.literature_rag import ingest_document
        ingest_document("path/to/paper.pdf", metadata={...})

2.  The search_literature tool is registered in AGENT_TOOLS (below)
    and called automatically by GPT-4o during run_agent().

Dependencies
------------
    pip install chromadb openai pypdf2 tiktoken
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

#  Configuration 

CHROMA_DIR      = os.getenv("CHROMA_DIR", "./voc_literature_db")
COLLECTION_NAME = "voc_literature"
CHUNK_SIZE      = 400          # tokens per chunk (≈ 300 words)
CHUNK_OVERLAP   = 60           # token overlap between chunks
TOP_K_DEFAULT   = 5            # chunks returned per search


#  Vector store initialisation 

def _get_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY not set.")
    return key


def _get_collection(api_key: Optional[str] = None):
    """Return (or create) the ChromaDB collection with OpenAI embeddings."""
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key or _get_openai_key(),
        model_name="text-embedding-3-small",
    )
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


#  Text chunking 

def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Naive word-boundary chunker.
    Replace with tiktoken-based chunker for production use.
    """
    words  = text.split()
    chunks = []
    start  = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 50]


def _doc_id(source: str, chunk_idx: int) -> str:
    h = hashlib.md5(source.encode()).hexdigest()[:8]
    return f"{h}_chunk{chunk_idx:04d}"


#  Ingestion API 

def ingest_text(text: str, metadata: dict, api_key: Optional[str] = None) -> int:
    """
    Chunk plain text and add to the vector store.

    Parameters
    ----------
    text     : full document text
    metadata : dict with keys like:
               title, authors, year, journal, doi,
               compound_focus, insect_focus, paper_type
    api_key  : OpenAI key (falls back to env var)

    Returns
    -------
    Number of chunks ingested.
    """
    collection = _get_collection(api_key)
    chunks     = _chunk_text(text)
    source     = metadata.get("doi") or metadata.get("title") or "unknown"

    ids  = [_doc_id(source, i) for i in range(len(chunks))]
    metas = [
        {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
        for i in range(len(chunks))
    ]

    # ChromaDB upsert — safe to re-run
    collection.upsert(documents=chunks, ids=ids, metadatas=metas)
    return len(chunks)


def ingest_pdf(pdf_path: str, metadata: dict, api_key: Optional[str] = None) -> int:
    """Extract text from a PDF then call ingest_text."""
    try:
        import PyPDF2
    except ImportError:
        raise ImportError("pip install pypdf2")

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(pdf_path)

    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)

    full_text = "\n".join(text_parts)
    metadata.setdefault("source_file", path.name)
    return ingest_text(full_text, metadata, api_key)


def ingest_document(path_or_text: str, metadata: dict,
                    api_key: Optional[str] = None) -> int:
    """
    Unified ingestion entry point.
    Pass a file path (PDF) or raw text string.
    """
    if Path(path_or_text).exists() and path_or_text.endswith(".pdf"):
        return ingest_pdf(path_or_text, metadata, api_key)
    return ingest_text(path_or_text, metadata, api_key)


#  Search API 

def search_literature(
    query: str,
    top_k: int = TOP_K_DEFAULT,
    filter_compound: Optional[str] = None,
    filter_insect: Optional[str]   = None,
    api_key: Optional[str]         = None,
) -> str:
    """
    Search the literature vector store.
    Returns a JSON string consumed by GPT-4o as a tool result.

    Parameters
    ----------
    query            : natural language search query
    top_k            : number of chunks to return
    filter_compound  : restrict to chunks mentioning this compound
    filter_insect    : restrict to chunks mentioning this insect
    api_key          : OpenAI key
    """
    collection = _get_collection(api_key)

    where = {}
    if filter_compound:
        where["compound_focus"] = {"$eq": filter_compound}
    if filter_insect:
        where["insect_focus"] = {"$eq": filter_insect}

    kwargs = dict(query_texts=[query], n_results=top_k)
    if where:
        kwargs["where"] = where

    try:
        results = collection.query(**kwargs)
    except Exception as e:
        return json.dumps({"error": str(e), "chunks": []})

    chunks_out = []
    for i, (doc, meta, dist) in enumerate(
        zip(results["documents"][0],
            results["metadatas"][0],
            results["distances"][0])
    ):
        chunks_out.append({
            "rank":        i + 1,
            "relevance":   round(1 - dist, 3),   # cosine similarity
            "title":       meta.get("title",   "Unknown"),
            "authors":     meta.get("authors", "Unknown"),
            "year":        meta.get("year",    "Unknown"),
            "journal":     meta.get("journal", "Unknown"),
            "doi":         meta.get("doi",     ""),
            "paper_type":  meta.get("paper_type", ""),
            "excerpt":     doc[:600],
        })

    return json.dumps({
        "query":      query,
        "n_returned": len(chunks_out),
        "chunks":     chunks_out,
    }, indent=2)


def get_collection_stats(api_key: Optional[str] = None) -> dict:
    """Return basic stats about the literature collection."""
    collection = _get_collection(api_key)
    count = collection.count()
    return {"total_chunks": count, "collection": COLLECTION_NAME,
            "db_path": CHROMA_DIR}


#  OpenAI tool schema (used in AGENT_TOOLS lists) 

SEARCH_LITERATURE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_literature",
        "description": (
            "Search the VOC Library scientific literature knowledge base. "
            "Use this when you need mechanistic explanations, mode-of-action detail, "
            "methodology context, or cross-study evidence that is not in the structured "
            "compound/bioassay database. Returns ranked excerpts with citation metadata."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Natural language search query, e.g. "
                        "'β-caryophyllene repellent mechanism thrips' or "
                        "'GC-MS headspace sampling betel vine volatiles'"
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of chunks to return (default 5, max 10).",
                    "default": 5,
                },
                "filter_compound": {
                    "type": "string",
                    "description": "Optional: restrict results to a specific compound focus tag.",
                },
                "filter_insect": {
                    "type": "string",
                    "description": "Optional: restrict results to a specific insect focus tag.",
                },
            },
            "required": ["query"],
        },
    },
}
