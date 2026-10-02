import os
import pytest
import io
import shutil
from app import app
from config import Config
from storage import db

@pytest.fixture
def client():
    orig_db = Config.DATABASE_PATH
    orig_uploads = Config.UPLOAD_FOLDER
    
    # Setup test config
    app.config['TESTING'] = True
    app.config['DATABASE_PATH'] = 'instance/test_api_documents.db'
    app.config['UPLOAD_FOLDER'] = 'static/test_api_uploads'
    Config.DATABASE_PATH = app.config['DATABASE_PATH'] # Keep db module in sync
    Config.UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
    
    # Ensure dirs exist
    os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Reset DB
    if os.path.exists(app.config['DATABASE_PATH']):
        os.remove(app.config['DATABASE_PATH'])
    db.init_db()

    with app.test_client() as client:
        yield client

    # Teardown
    if os.path.exists(app.config['DATABASE_PATH']):
        os.remove(app.config['DATABASE_PATH'])
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    Config.DATABASE_PATH = orig_db
    Config.UPLOAD_FOLDER = orig_uploads
    app.config['DATABASE_PATH'] = orig_db
    app.config['UPLOAD_FOLDER'] = orig_uploads
    db.init_db()

def test_upload_valid_image(client):
    mock_img_path = os.path.join('mock_data', 'test_payment.png')
    if not os.path.exists(mock_img_path):
        pytest.skip(f"{mock_img_path} not found")
        
    with open(mock_img_path, 'rb') as f:
        data = {
            'files': (f, 'test_payment.png')
        }
        response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'uploaded' in json_data
    assert len(json_data['uploaded']) == 1
    
    img_id = json_data['uploaded'][0]['image_id']
    
    # Verify DB record exists
    assert db.get_document(img_id) is not None

def test_upload_invalid_type(client):
    data = {
        'files': (io.BytesIO(b"some text"), 'test.txt')
    }
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 200 # App logic returns 200 for partial failures
    json_data = response.get_json()
    assert len(json_data['errors']) == 1
    assert "invalid extension" in json_data['errors'][0]

def test_upload_too_large(client, monkeypatch):
    monkeypatch.setattr(Config, 'MAX_FILE_SIZE_MB', 0) # 0 MB max size
    
    data = {
        'files': (io.BytesIO(b"a" * 1024), 'large.png')
    }
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data['errors']) == 1
    assert "exceeds" in json_data['errors'][0]

def test_search_finds_match(client):
    mock_img_path = os.path.join('mock_data', 'test_payment.png')
    if not os.path.exists(mock_img_path):
        pytest.skip(f"{mock_img_path} not found")
        
    with open(mock_img_path, 'rb') as f:
        client.post('/api/upload', data={'files': (f, 'test_payment.png')})
        
    response = client.get('/api/search?q=6500')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data['results']) >= 1

def test_search_no_match(client):
    response = client.get('/api/search?q=nonsense')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data['results']) == 0
    assert "No documents matched" in json_data['message']

def test_search_empty_query(client):
    response = client.get('/api/search?q=')
    assert response.status_code == 400

def test_library_lists_all(client):
    mock_img_path = os.path.join('mock_data', 'test_payment.png')
    if not os.path.exists(mock_img_path):
        pytest.skip(f"{mock_img_path} not found")
        
    with open(mock_img_path, 'rb') as f:
        client.post('/api/upload', data={'files': (f, 'test_1.png')})
    with open(mock_img_path, 'rb') as f:
        # seek back to start if we were reusing f, but we opened it again so it's fine. 
        # Actually need a new read or a seek(0) in between, but reopening in open() is easier to get right:
        pass
    with open(mock_img_path, 'rb') as f:
        client.post('/api/upload', data={'files': (f, 'test_2.png')})
        
    response = client.get('/api/library')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data) == 2

def test_get_image_valid(client):
    mock_img_path = os.path.join('mock_data', 'test_payment.png')
    if not os.path.exists(mock_img_path):
        pytest.skip(f"{mock_img_path} not found")
        
    with open(mock_img_path, 'rb') as f:
        upload_resp = client.post('/api/upload', data={'files': (f, 'test.png')})
        img_id = upload_resp.get_json()['uploaded'][0]['image_id']
        
    response = client.get(f'/api/images/{img_id}')
    assert response.status_code == 200
    assert response.content_type in ['image/png', 'image/jpeg', 'application/octet-stream']

def test_get_image_invalid(client):
    response = client.get('/api/images/nonexistent')
    assert response.status_code == 404

def test_get_ocr_text(client):
    mock_img_path = os.path.join('mock_data', 'test_payment.png')
    if not os.path.exists(mock_img_path):
        pytest.skip(f"{mock_img_path} not found")
        
    with open(mock_img_path, 'rb') as f:
        upload_resp = client.post('/api/upload', data={'files': (f, 'test.png')})
        img_id = upload_resp.get_json()['uploaded'][0]['image_id']
        
    response = client.get(f'/api/images/{img_id}/ocr')
    assert response.status_code == 200
    assert 'ocr_text' in response.get_json()

def test_delete_removes(client):
    mock_img_path = os.path.join('mock_data', 'test_payment.png')
    if not os.path.exists(mock_img_path):
        pytest.skip(f"{mock_img_path} not found")
        
    with open(mock_img_path, 'rb') as f:
        upload_resp = client.post('/api/upload', data={'files': (f, 'test.png')})
        img_id = upload_resp.get_json()['uploaded'][0]['image_id']
        
    response = client.delete(f'/api/images/{img_id}')
    assert response.status_code == 200
    
    lib_resp = client.get('/api/library')
    assert len(lib_resp.get_json()) == 0

def test_session_isolation_library_and_search(client):
    mock_img_path = os.path.join('mock_data', 'test_payment.png')
    if not os.path.exists(mock_img_path):
        pytest.skip(f"{mock_img_path} not found")

    # Client A uploads with session header user-a
    with open(mock_img_path, 'rb') as f:
        resp_a = client.post(
            '/api/upload', 
            data={'files': (f, 'payment_a.png')}, 
            headers={'X-Session-ID': 'user-a'}
        )
    assert resp_a.status_code == 200
    doc_a_id = resp_a.get_json()['uploaded'][0]['image_id']

    # Client B uploads with session header user-b
    with open(mock_img_path, 'rb') as f:
        resp_b = client.post(
            '/api/upload', 
            data={'files': (f, 'payment_b.png')}, 
            headers={'X-Session-ID': 'user-b'}
        )
    assert resp_b.status_code == 200
    doc_b_id = resp_b.get_json()['uploaded'][0]['image_id']

    # User A's library contains only doc A
    lib_a = client.get('/api/library', headers={'X-Session-ID': 'user-a'}).get_json()
    assert len(lib_a) == 1
    assert lib_a[0]['id'] == doc_a_id

    # User B's library contains only doc B
    lib_b = client.get('/api/library', headers={'X-Session-ID': 'user-b'}).get_json()
    assert len(lib_b) == 1
    assert lib_b[0]['id'] == doc_b_id

    # Cross-session access blocked
    res_b_view = client.get(f'/api/images/{doc_a_id}', headers={'X-Session-ID': 'user-b'})
    assert res_b_view.status_code == 404

    res_b_ocr = client.get(f'/api/images/{doc_a_id}/ocr', headers={'X-Session-ID': 'user-b'})
    assert res_b_ocr.status_code == 404

    res_b_del = client.delete(f'/api/images/{doc_a_id}', headers={'X-Session-ID': 'user-b'})
    assert res_b_del.status_code == 404

    # User A can still access their doc
    res_a_view = client.get(f'/api/images/{doc_a_id}', headers={'X-Session-ID': 'user-a'})
    assert res_a_view.status_code == 200

def test_load_samples_endpoint(client):
    response = client.post('/api/load-samples', headers={'X-Session-ID': 'sample-user'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'loaded' in data
    assert data['loaded'] >= 1

    lib = client.get('/api/library', headers={'X-Session-ID': 'sample-user'}).get_json()
    assert len(lib) == data['loaded']

