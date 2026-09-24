"""Manual spot-check: run sample queries against the ingested ChromaDB collection
and print the top matches so retrieval quality can be verified by eye.

Run: python scripts/spot_check_retrieval.py
"""

import os
import sys

import chromadb
from fastembed import TextEmbedding

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest import CHROMA_PERSIST_DIR, COLLECTION_NAME, EMBEDDING_MODEL_NAME

QUERIES = [
    "What is the waiting period before a critical illness claim is payable?",
    "What BMI range counts as Obese Class I and how many risk points does it add?",
    "Can a term life policy be converted to a whole life policy?",
    "What exclusions apply to accidental death and dismemberment coverage?",
    "What happens if someone in a hazardous occupation like an offshore oil rig worker applies for disability income insurance?",
]


def main():
    model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    for query in QUERIES:
        query_embedding = [vec.tolist() for vec in model.embed([query])]
        results = collection.query(query_embeddings=query_embedding, n_results=3)

        print("=" * 100)
        print(f"QUERY: {query}")
        print("-" * 100)
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            print(f"[distance={dist:.4f}] source={meta.get('source_file')} section/sheet={meta.get('section') or meta.get('sheet')}")
            print(f"  {doc[:300]}")
        print()


if __name__ == "__main__":
    main()
