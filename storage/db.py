import sqlite3
from flask import g
from config import Config
import os

def get_db():
    db = sqlite3.connect(
        Config.DATABASE_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    db.row_factory = sqlite3.Row
    return db

def init_db():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    db = get_db()
    with db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                ocr_text TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    db.close()

def insert_document(doc: dict) -> str:
    db = get_db()
    with db:
        db.execute(
            'INSERT INTO documents (id, filename, original_name, ocr_text) VALUES (?, ?, ?, ?)',
            (doc['id'], doc['filename'], doc['original_name'], doc.get('ocr_text', ''))
        )
    db.close()
    return doc['id']

def get_all_documents() -> list[dict]:
    db = get_db()
    cur = db.execute('SELECT * FROM documents ORDER BY uploaded_at DESC')
    docs = [dict(row) for row in cur.fetchall()]
    db.close()
    return docs

def get_document(doc_id: str) -> dict:
    db = get_db()
    cur = db.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
    row = cur.fetchone()
    db.close()
    return dict(row) if row else None

def delete_document(doc_id: str) -> None:
    db = get_db()
    with db:
        db.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
    db.close()

def get_document_count() -> int:
    db = get_db()
    cur = db.execute('SELECT COUNT(*) FROM documents')
    count = cur.fetchone()[0]
    db.close()
    return count
