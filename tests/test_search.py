import pytest
from search.ranker import rank, extract_snippet

DOCS = [
    {"id": "1", "ocr_text": "Payment received Rs 6500 on 15 March 2026 for services"},
    {"id": "2", "ocr_text": "Medicine Paracetamol 500mg daily"},
    {"id": "3", "ocr_text": "Invoice #INV-2026-0312 Grocery Mart Total Rs 2340"},
    {"id": "4", "ocr_text": "Payment for Rs 1500 only"}
]

def test_exact_match_ranks_first():
    results = rank("6500", DOCS)
    assert len(results) > 0
    assert results[0]['id'] == "1"

def test_partial_match_scores_above_zero():
    # "March" is in doc 1, not exactly the query but a part of it
    results = rank("March payment", DOCS)
    assert len(results) > 0
    assert any(r['id'] == "1" for r in results)
    assert all(r['score'] > 0 for r in results)

def test_no_match_scores_zero():
    # Unrelated doc filtered out
    results = rank("Xylophone", DOCS)
    assert len(results) == 0

def test_fuzzy_handles_ocr_noise():
    # "₹6500" vs "Rs 6500"
    results = rank("₹6500", DOCS)
    # Should still find doc 1 due to fuzzy matching on 6500 part
    assert len(results) > 0
    assert results[0]['id'] == "1"

def test_empty_corpus():
    results = rank("test", [])
    assert results == []

def test_snippet_contains_match():
    snippet_info = extract_snippet(DOCS[0]['ocr_text'], "6500")
    assert "6500" in snippet_info['text']

def test_snippet_highlight_ranges():
    snippet_info = extract_snippet(DOCS[0]['ocr_text'], "6500")
    ranges = snippet_info['highlight_ranges']
    assert len(ranges) >= 1
    start, end = ranges[0]
    # Check that the highlighted part is actually the match
    assert snippet_info['text'][start:end].lower() == "6500"

def test_ranking_order():
    # "Payment" is in doc 1 and doc 4. 
    # Let's search for "Payment 6500". Doc 1 should be higher than Doc 4.
    results = rank("Payment 6500", DOCS)
    assert len(results) >= 2
    
    # Extract scores
    scores = [r['score'] for r in results]
    
    # Check descending order
    assert scores == sorted(scores, reverse=True)
    
    # Check doc 1 is first
    assert results[0]['id'] == "1"
