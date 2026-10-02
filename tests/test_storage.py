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

def test_session_isolated_retrieval():
    doc_a = {'id': 'a-1', 'session_id': 'sess-a', 'filename': 'a.png', 'original_name': 'a.png', 'ocr_text': 'doc a'}
    doc_b = {'id': 'b-1', 'session_id': 'sess-b', 'filename': 'b.png', 'original_name': 'b.png', 'ocr_text': 'doc b'}
    insert_document(doc_a)
    insert_document(doc_b)

    docs_a = get_all_documents('sess-a')
    docs_b = get_all_documents('sess-b')

    assert len(docs_a) == 1
    assert docs_a[0]['id'] == 'a-1'

    assert len(docs_b) == 1
    assert docs_b[0]['id'] == 'b-1'

def test_session_isolated_get_by_id():
    doc = {'id': 'iso-1', 'session_id': 'alice', 'filename': 'iso.png', 'original_name': 'iso.png', 'ocr_text': 'secret'}
    insert_document(doc)

    assert get_document('iso-1', 'alice') is not None
    assert get_document('iso-1', 'bob') is None

def test_session_isolated_delete():
    doc = {'id': 'del-iso-1', 'session_id': 'alice', 'filename': 'del.png', 'original_name': 'del.png', 'ocr_text': 'secret'}
    insert_document(doc)

    # Bob tries to delete Alice's doc
    deleted = delete_document('del-iso-1', 'bob')
    assert deleted is False
    assert get_document('del-iso-1', 'alice') is not None

    # Alice deletes her doc
    deleted = delete_document('del-iso-1', 'alice')
    assert deleted is True
    assert get_document('del-iso-1', 'alice') is None

def test_session_isolated_count():
    insert_document({'id': 'cnt-1', 'session_id': 'user-1', 'filename': '1.png', 'original_name': '1.png', 'ocr_text': '1'})
    insert_document({'id': 'cnt-2', 'session_id': 'user-1', 'filename': '2.png', 'original_name': '2.png', 'ocr_text': '2'})
    insert_document({'id': 'cnt-3', 'session_id': 'user-2', 'filename': '3.png', 'original_name': '3.png', 'ocr_text': '3'})

    assert get_document_count('user-1') == 2
    assert get_document_count('user-2') == 1
    assert get_document_count() == 3

