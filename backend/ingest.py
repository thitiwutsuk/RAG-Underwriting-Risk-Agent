"""Parse mock Excel data and real specimen policy PDFs, chunk them, and embed into ChromaDB.

Pipeline: parse (pandas/openpyxl for underwriting criteria, pypdf for policy PDFs)
-> chunk -> embed (local BAAI/bge-m3 via sentence-transformers, no API cost)
-> store in a persistent ChromaDB collection.

The policy documents in data/policies/ are real specimen/sample policies
publicly published by insurers (RBC Insurance) for consumer reference. See
data/README.md for sources and usage notes -- this repository is private and
these files are kept out of any public redistribution.

Run: python ingest.py
"""

import glob
import os

import chromadb
import pandas as pd
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

POLICY_DIR = "data/policies"
EXCEL_PATH = "data/underwriting_criteria.xlsx"
CHROMA_PERSIST_DIR = "chroma_db"
COLLECTION_NAME = "underwriting_knowledge_base"
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
MAX_CHUNK_CHARS = 1200

# Human-readable product names for each real specimen PDF, used in citations.
POLICY_TITLES = {
    "rbc_term_life.pdf": "RBC Your Term Life Insurance (Specimen Policy)",
    "t100-policy.pdf": "RBC Term 100 Permanent Life Insurance (Specimen Policy)",
    "your-term-rider.pdf": "RBC Your Term Life Insurance - Riders",
    "rbc-ul-policy.pdf": "RBC Universal Life Insurance (Specimen Policy)",
    "rbc-ul-policy-bonus.pdf": "RBC Universal Life Insurance with Bonus Interest (Specimen Policy)",
    "ul-rider-package.pdf": "RBC Universal Life Insurance - Rider Package",
    "rbc_critical_illness.pdf": "RBC Critical Illness Insurance Plan (Sample Policy)",
    "rbc_disability_income.pdf": "RBC Disability Income Protection (Specimen Policy)",
}


def split_text_into_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Greedily group paragraphs into chunks no longer than max_chars."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current} {para}".strip() if current else para
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = para
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks


def chunk_pdf_policy(path: str) -> list[dict]:
    """Extract text page by page from a real specimen policy PDF and chunk it."""
    filename = os.path.basename(path)
    title = POLICY_TITLES.get(filename, filename)
    reader = PdfReader(path)

    chunks = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for piece in split_text_into_chunks(text):
            chunks.append(
                {
                    "text": f"{title} (page {page_number}): {piece}",
                    "metadata": {
                        "doc_type": "policy",
                        "source_file": filename,
                        "policy_title": title,
                        "page": page_number,
                    },
                }
            )

    return chunks


def chunk_underwriting_excel(path: str) -> list[dict]:
    """Turn each row of each underwriting criteria sheet into a natural-language chunk."""
    sheets = pd.read_excel(path, sheet_name=None)
    chunks = []

    for sheet_name, df in sheets.items():
        for _, row in df.iterrows():
            text = f"Underwriting criteria ({sheet_name}): " + "; ".join(
                f"{col}={row[col]}" for col in df.columns
            )
            chunks.append(
                {
                    "text": text,
                    "metadata": {
                        "doc_type": "underwriting_criteria",
                        "source_file": os.path.basename(path),
                        "sheet": sheet_name,
                    },
                }
            )

    return chunks


def build_corpus() -> list[dict]:
    corpus: list[dict] = []
    for policy_path in sorted(glob.glob(os.path.join(POLICY_DIR, "*.pdf"))):
        corpus.extend(chunk_pdf_policy(policy_path))
    corpus.extend(chunk_underwriting_excel(EXCEL_PATH))
    return corpus


def main():
    corpus = build_corpus()
    print(f"Built {len(corpus)} chunks from {POLICY_DIR} and {EXCEL_PATH}")

    print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}' (first run downloads it locally)...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    texts = [c["text"] for c in corpus]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
    collection = client.create_collection(COLLECTION_NAME)

    collection.add(
        ids=[f"chunk-{i}" for i in range(len(corpus))],
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=[c["metadata"] for c in corpus],
    )

    print(f"Stored {collection.count()} chunks in ChromaDB collection '{COLLECTION_NAME}' at ./{CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    main()
