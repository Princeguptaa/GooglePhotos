import urllib.request
import json

BASE = 'http://127.0.0.1:5000'

def test_live_session():
    # 1. Fresh incognito GET /?session_id=demo
    req = urllib.request.Request(f'{BASE}/?session_id=demo')
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
        assert resp.status == 200
        assert 'name="session-id" content="demo"' in html
        print('1. Live HTML: Status 200 returned with <meta name="session-id" content="demo">.')

    # 2. Fresh client loads library (simulating app.js on page load)
    req = urllib.request.Request(f'{BASE}/api/library', headers={'X-Session-ID': 'demo'})
    with urllib.request.urlopen(req) as resp:
        docs = json.loads(resp.read().decode('utf-8'))
        print(f'2. Initial Library Load: {len(docs)} documents returned immediately without user action.')
        assert len(docs) == 14, f'Expected 14 documents, got {len(docs)}'
        for d in docs:
            print(f'   - {d["original_name"]} (ID: {d["id"][:8]}...)')

    # 3. Search '6500'
    req = urllib.request.Request(f'{BASE}/api/search?q=6500', headers={'X-Session-ID': 'demo'})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f'3. Search "6500": {len(res["results"])} match(es)')
        assert len(res['results']) == 1
        top = res['results'][0]
        print(f'   - Top doc ID: {top["image_id"][:8]}... | Score: {top["score"]*100:.1f}% | Snippet: {top["snippet"]}')
        assert top['score'] >= 0.90

    # 4. Search 'Samrat'
    req = urllib.request.Request(f'{BASE}/api/search?q=Samrat', headers={'X-Session-ID': 'demo'})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f'4. Search "Samrat": {len(res["results"])} match(es)')
        assert len(res['results']) == 2
        for r in res['results']:
            print(f'   - Doc ID: {r["image_id"][:8]}... | Score: {r["score"]*100:.1f}% | Snippet: {r["snippet"]}')

    # 5. Search 'Paracetamol'
    req = urllib.request.Request(f'{BASE}/api/search?q=Paracetamol', headers={'X-Session-ID': 'demo'})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f'5. Search "Paracetamol": {len(res["results"])} match(es)')
        assert len(res['results']) == 1
        r = res['results'][0]
        print(f'   - Doc ID: {r["image_id"][:8]}... | Score: {r["score"]*100:.1f}% | Snippet: {r["snippet"]}')

    # 6. Search 'watermelon'
    req = urllib.request.Request(f'{BASE}/api/search?q=watermelon', headers={'X-Session-ID': 'demo'})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f'6. Search "watermelon": {len(res["results"])} match(es)')
        assert len(res['results']) == 0

    # 7. Device 2 / Reopened link persistence
    req = urllib.request.Request(f'{BASE}/api/library', headers={'X-Session-ID': 'demo'})
    with urllib.request.urlopen(req) as resp:
        docs2 = json.loads(resp.read().decode('utf-8'))
        print(f'7. Reopen/Device 2 Persistence: {len(docs2)} documents verified intact.')
        assert len(docs2) == 14

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_live_session()
