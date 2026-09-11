import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest import build_corpus, chunk_pdf_policy, chunk_underwriting_excel, split_text_into_chunks

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
POLICY_PATH = os.path.join(DATA_DIR, "policies", "rbc_term_life.pdf")
EXCEL_PATH = os.path.join(DATA_DIR, "underwriting_criteria.xlsx")


def test_split_text_into_chunks_respects_max_length():
    text = "\n".join(f"Paragraph {i} " + "word " * 30 for i in range(20))
    chunks = split_text_into_chunks(text, max_chars=200)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 200 + 50  # allow a little slack for the last paragraph merged in


def test_chunk_pdf_policy_produces_nonempty_chunks_with_metadata():
    chunks = chunk_pdf_policy(POLICY_PATH)

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["text"].strip() != ""
        assert chunk["metadata"]["doc_type"] == "policy"
        assert chunk["metadata"]["source_file"] == "rbc_term_life.pdf"
        assert chunk["metadata"]["page"] >= 1


def test_chunk_underwriting_excel_covers_all_sheets():
    chunks = chunk_underwriting_excel(EXCEL_PATH)
    sheets = {c["metadata"]["sheet"] for c in chunks}

    assert len(chunks) > 0
    assert {"Age", "BMI", "Health History", "Occupation Risk", "Lifestyle", "Risk Tiers"}.issubset(sheets)
    for chunk in chunks:
        assert chunk["metadata"]["doc_type"] == "underwriting_criteria"


def test_build_corpus_combines_policies_and_criteria():
    corpus = build_corpus()
    doc_types = {c["metadata"]["doc_type"] for c in corpus}

    assert doc_types == {"policy", "underwriting_criteria"}
    assert len(corpus) > 20
