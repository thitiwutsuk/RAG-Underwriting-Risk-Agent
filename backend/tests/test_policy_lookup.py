import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import search_policies


def test_search_policies_returns_hits_with_expected_shape():
    hits = search_policies("What is the waiting period for a critical illness claim?", k=3)

    assert len(hits) == 3
    for hit in hits:
        assert hit["text"].strip() != ""
        assert hit["source_file"]
        assert isinstance(hit["distance"], float)


def test_search_policies_finds_the_relevant_document():
    hits = search_policies("What is the waiting period for a critical illness claim?", k=3)
    top_sources = {hit["source_file"] for hit in hits}

    assert "rbc_critical_illness.pdf" in top_sources


def test_search_policies_respects_k():
    hits = search_policies("term life conversion privilege", k=1)
    assert len(hits) == 1
