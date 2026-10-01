import sqlite3
import os
from contextlib import closing
from config import Config

def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    with closing(get_connection()) as conn:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id          TEXT PRIMARY KEY,
                    filename    TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    ocr_text    TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
                USING fts5(ocr_text, content='documents', content_rowid='rowid')
            ''')

def insert_document(doc: dict) -> str:
    with closing(get_connection()) as conn:
        with conn:
            conn.execute('''
                INSERT INTO documents (id, filename, original_name, ocr_text)
                VALUES (?, ?, ?, ?)
            ''', (doc['id'], doc['filename'], doc['original_name'], doc['ocr_text']))
    return doc['id']

def get_all_documents() -> list[dict]:
    with closing(get_connection()) as conn:
        rows = conn.execute('SELECT * FROM documents ORDER BY uploaded_at DESC').fetchall()
        return [dict(row) for row in rows]

def get_document(doc_id: str) -> dict | None:
    with closing(get_connection()) as conn:
        row = conn.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
        return dict(row) if row else None

def delete_document(doc_id: str) -> None:
    with closing(get_connection()) as conn:
        with conn:
            conn.execute('DELETE FROM documents WHERE id = ?', (doc_id,))

def get_document_count() -> int:
    with closing(get_connection()) as conn:
        row = conn.execute('SELECT COUNT(*) FROM documents').fetchone()
        return row[0]
