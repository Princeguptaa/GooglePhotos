import pytest
from app import app
from storage import db
from load_mock_data import seed_samples_for_session

@pytest.fixture(scope="module")
def client():
    # Setup demo session with loaded mock data
    db.clear_session_documents('test_acceptance_session')
    seed_samples_for_session('test_acceptance_session')
    with app.test_client() as client:
        yield client

def test_01_query_manoj(client):
    """TEST 1: Query 'Manoj' -> Documents containing Manoj should rank highly."""
    resp = client.get('/api/search?q=Manoj', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 2, "Expected at least 2 Manoj documents"
    # All returned top documents should contain Manoj
    for r in results[:2]:
        assert r['score'] >= 0.85, f"Expected strong match score, got {r['score']}"
        assert 'Manoj' in r['snippet'] or 'manoj' in r['snippet'].lower()

def test_02_query_manoj_payment(client):
    """TEST 2: Query 'Manoj payment' -> Document containing BOTH Manoj and payment-related content
    must rank above documents containing only Manoj or only payment."""
    resp = client.get('/api/search?q=Manoj+payment', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 1

    top_result = results[0]
    # Top result must contain BOTH Manoj and payment
    snippet_lower = top_result['snippet'].lower()
    assert 'manoj' in snippet_lower, "Top result must contain Manoj"
    assert ('payment' in snippet_lower or 'receipt' in snippet_lower or 'rs' in snippet_lower), "Top result must contain payment-related content"
    assert top_result['score'] >= 0.90, f"Expected >= 0.90 for dual-clue match, got {top_result['score']}"

    # Verify ranking: documents with only Manoj or only payment must rank strictly below top_result
    for r in results[1:]:
        assert top_result['score'] > r['score'], "Document with both Manoj and payment must rank strictly above single-clue matches"

def test_03_query_exact_amount_6500(client):
    """TEST 3: Query '6500' -> The document containing the exact 6500 amount should rank first or very highly.
    Do not match 6000, 5000, 1500, etc."""
    resp = client.get('/api/search?q=6500', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 1

    top_result = results[0]
    assert '6,500' in top_result['snippet'] or '6500' in top_result['snippet']
    assert top_result['score'] >= 0.90

    # Ensure documents with differing amounts (1500, 12899, 2340, 3200) are not falsely matched
    for r in results:
        assert '6,500' in r['snippet'] or '6500' in r['snippet']
        assert '1,500' not in r['snippet']

def test_04_query_6500_payment(client):
    """TEST 4: Query '6500 payment' -> The document containing BOTH 6500 and payment-related content
    should rank above generic payment documents."""
    resp = client.get('/api/search?q=6500+payment', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 1

    top_result = results[0]
    assert top_result['score'] >= 0.90
    assert ('6,500' in top_result['snippet'] or '6500' in top_result['snippet'])
    assert ('payment' in top_result['snippet'].lower() or 'receipt' in top_result['snippet'].lower())

    # If generic payment documents (e.g. 1500 payment) match partially, they must rank lower
    for r in results[1:]:
        assert top_result['score'] > r['score']

def test_05_query_prince_gupta(client):
    """TEST 5: Query 'Prince Gupta' -> Relevant documents containing Prince Gupta should rank highly."""
    resp = client.get('/api/search?q=Prince+Gupta', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 2, "Expected at least 2 Prince Gupta documents"

    for r in results[:2]:
        assert r['score'] >= 0.85
        assert 'Prince Gupta' in r['snippet']

def test_06_query_prince_gupta_aadhaar(client):
    """TEST 6: Query 'Prince Gupta Aadhaar' -> A document containing BOTH Prince Gupta and Aadhaar/UIDAI text
    must rank substantially higher than documents containing only Prince Gupta."""
    resp = client.get('/api/search?q=Prince+Gupta+Aadhaar', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 1

    top_result = results[0]
    snippet_lower = top_result['snippet'].lower()
    assert 'prince gupta' in snippet_lower
    assert ('aadhaar' in snippet_lower or 'uidai' in snippet_lower)
    assert top_result['score'] >= 0.90

    # Find result containing only Prince Gupta without Aadhaar (e.g. marksheet)
    single_clue_results = [r for r in results if 'marksheet' in r['snippet'].lower() or 'semester' in r['snippet'].lower()]
    if single_clue_results:
        marksheet_result = single_clue_results[0]
        # Multi-clue score must substantially outrank single-clue score
        assert top_result['score'] - marksheet_result['score'] >= 0.25, (
            f"Expected multi-clue score ({top_result['score']}) to substantially outrank single-clue ({marksheet_result['score']})"
        )

def test_07_query_aadhaar_no_filename_leakage(client):
    """TEST 7: Query 'Aadhaar' -> Only documents whose searchable content contains Aadhaar/Aadhar/UIDAI-related text
    should receive strong relevance. A filename alone must NOT make a result relevant."""
    resp = client.get('/api/search?q=Aadhaar', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 1

    for r in results:
        snippet_lower = r['snippet'].lower()
        # Must actually contain the text in OCR content
        assert ('aadhaar' in snippet_lower or 'aadhar' in snippet_lower or 'uidai' in snippet_lower), (
            f"Document {r['image_id']} returned without Aadhaar/UIDAI text in OCR snippet: {r['snippet']}"
        )

def test_08_query_paracetamol(client):
    """TEST 8: Query 'Paracetamol' -> The document containing Paracetamol should rank first/highly."""
    resp = client.get('/api/search?q=Paracetamol', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 1
    top_result = results[0]
    assert 'paracetamol' in top_result['snippet'].lower()
    assert top_result['score'] >= 0.90

def test_09_query_paracetamol_prescription(client):
    """TEST 9: Query 'Paracetamol prescription' -> The document containing both Paracetamol and
    prescription-related content should rank above generic prescriptions."""
    resp = client.get('/api/search?q=Paracetamol+prescription', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 1

    top_result = results[0]
    snippet_lower = top_result['snippet'].lower()
    assert 'paracetamol' in snippet_lower
    assert ('prescription' in snippet_lower or 'dr' in snippet_lower or 'mg' in snippet_lower)
    assert top_result['score'] >= 0.90

    # Generic prescription documents without Paracetamol must rank lower
    for r in results[1:]:
        assert top_result['score'] > r['score']

def test_10_query_invoice_september(client):
    """TEST 10: Query 'Invoice September' -> Documents matching both invoice-related content and September
    should receive a strong ranking boost."""
    resp = client.get('/api/search?q=Invoice+September', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    results = resp['results']
    assert len(results) >= 1

    top_result = results[0]
    snippet_lower = top_result['snippet'].lower()
    assert 'september' in snippet_lower, "Top result must match September"
    assert ('invoice' in snippet_lower or 'total' in snippet_lower or 'rs' in snippet_lower)
    assert top_result['score'] >= 0.90

    # Non-September invoices (March, January) must rank below the September invoice
    for r in results[1:]:
        assert top_result['score'] > r['score'], "September invoice must rank above other invoices"

def test_11_query_honest_no_results(client):
    """TEST 11: Query 'xyz123_not_a_real_term' -> Honest no-results response.
    Do not return unrelated documents."""
    resp = client.get('/api/search?q=xyz123_not_a_real_term', headers={'X-Session-ID': 'test_acceptance_session'}).get_json()
    assert 'results' in resp
    assert len(resp['results']) == 0
    assert "No documents matched" in resp.get('message', '')
