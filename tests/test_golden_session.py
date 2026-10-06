import pytest
from app import app
from storage import db

def test_golden_session_end_to_end():
    # 1. Fresh Incognito Client (no cookies, no prior session)
    incognito = app.test_client()

    # Client visits golden link: /?session_id=demo
    r_page = incognito.get('/?session_id=demo')
    assert r_page.status_code == 200

    # Library call on initial page load
    r_lib = incognito.get('/api/library', headers={'X-Session-ID': 'demo'})
    assert r_lib.status_code == 200
    docs = r_lib.get_json()
    assert len(docs) == 14, f"Expected 14 documents in golden session, found {len(docs)}"

    # 2. Test exact search '6500' -> scores >= 90% on mock_payment.png
    res_6500 = incognito.get('/api/search?q=6500', headers={'X-Session-ID': 'demo'}).get_json()
    assert 'results' in res_6500
    assert len(res_6500['results']) == 1
    top_6500 = res_6500['results'][0]
    assert top_6500['score'] >= 0.90
    assert '6,500' in top_6500['snippet'] or '6500' in top_6500['snippet']

    # 3. Test search 'Samrat' -> matches both mock_aadhaar and mock_payment
    res_samrat = incognito.get('/api/search?q=Samrat', headers={'X-Session-ID': 'demo'}).get_json()
    assert len(res_samrat['results']) == 2
    assert all(r['score'] >= 0.90 for r in res_samrat['results'])

    # 4. Test search 'Paracetamol' -> matches mock_medicine
    res_para = incognito.get('/api/search?q=Paracetamol', headers={'X-Session-ID': 'demo'}).get_json()
    assert len(res_para['results']) == 1
    assert res_para['results'][0]['score'] >= 0.90
    assert 'Paracetamol' in res_para['results'][0]['snippet']

    # 5. Test no-match query 'electricity bill' -> 0 results
    res_elec = incognito.get('/api/search?q=electricity+bill', headers={'X-Session-ID': 'demo'}).get_json()
    assert len(res_elec['results']) == 0
    assert "No documents matched" in res_elec.get('message', '')

    # 6. Test reopening later or from a different device/browser
    device_2 = app.test_client()
    r_dev2_page = device_2.get('/?session_id=demo')
    assert r_dev2_page.status_code == 200
    
    r_dev2_lib = device_2.get('/api/library', headers={'X-Session-ID': 'demo'})
    docs_dev2 = r_dev2_lib.get_json()
    assert len(docs_dev2) == 14

    res_dev2_search = device_2.get('/api/search?q=6500', headers={'X-Session-ID': 'demo'}).get_json()
    assert len(res_dev2_search['results']) == 1
    assert res_dev2_search['results'][0]['score'] >= 0.90
