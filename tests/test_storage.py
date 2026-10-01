import pytest
from storage.db import init_db, insert_document, get_all_documents, get_document, delete_document, get_document_count
from config import Config

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    # Override database path to use a temporary file for tests
    Config.DATABASE_PATH = str(tmp_path / "test.db")
    init_db()
    yield

def test_insert_and_retrieve():
    doc = {'id': 'test-1', 'filename': 'f.png', 'original_name': 'my.png', 'ocr_text': 'hello world'}
    insert_document(doc)
    docs = get_all_documents()
    assert len(docs) == 1
    assert docs[0]['id'] == 'test-1'
    assert docs[0]['filename'] == 'f.png'
    assert docs[0]['original_name'] == 'my.png'
    assert docs[0]['ocr_text'] == 'hello world'

def test_get_by_id():
    doc = {'id': 'test-2', 'filename': 'g.png', 'original_name': 'test.png', 'ocr_text': 'some text'}
    insert_document(doc)
    retrieved = get_document('test-2')
    assert retrieved is not None
    assert retrieved['id'] == 'test-2'
    assert retrieved['ocr_text'] == 'some text'

def test_get_missing_id():
    assert get_document('nonexistent') is None

def test_delete():
    doc = {'id': 'test-3', 'filename': 'h.png', 'original_name': 'del.png', 'ocr_text': 'delete me'}
    insert_document(doc)
    assert len(get_all_documents()) == 1
    delete_document('test-3')
    assert len(get_all_documents()) == 0

def test_count():
    docs = [
        {'id': 'c-1', 'filename': '1.png', 'original_name': '1.png', 'ocr_text': 'a'},
        {'id': 'c-2', 'filename': '2.png', 'original_name': '2.png', 'ocr_text': 'b'},
        {'id': 'c-3', 'filename': '3.png', 'original_name': '3.png', 'ocr_text': 'c'}
    ]
    for d in docs:
        insert_document(d)
    assert get_document_count() == 3
