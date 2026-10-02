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
                    id            TEXT PRIMARY KEY,
                    session_id    TEXT NOT NULL DEFAULT 'default',
                    filename      TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    ocr_text      TEXT NOT NULL,
                    uploaded_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Check for schema migration if table was created previously without session_id
            cursor = conn.execute("PRAGMA table_info(documents)")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'session_id' not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default'")
                
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id, uploaded_at DESC)')

            conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
                USING fts5(ocr_text, content='documents', content_rowid='rowid')
            ''')

def insert_document(doc: dict) -> str:
    session_id = doc.get('session_id', 'default')
    with closing(get_connection()) as conn:
        with conn:
            conn.execute('''
                INSERT INTO documents (id, session_id, filename, original_name, ocr_text)
                VALUES (?, ?, ?, ?, ?)
            ''', (doc['id'], session_id, doc['filename'], doc['original_name'], doc['ocr_text']))
    return doc['id']

def get_all_documents(session_id: str | None = None) -> list[dict]:
    with closing(get_connection()) as conn:
        if session_id is not None:
            rows = conn.execute(
                'SELECT * FROM documents WHERE session_id = ? ORDER BY uploaded_at DESC', 
                (session_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM documents ORDER BY uploaded_at DESC'
            ).fetchall()
        return [dict(row) for row in rows]

def get_document(doc_id: str, session_id: str | None = None) -> dict | None:
    with closing(get_connection()) as conn:
        if session_id is not None:
            row = conn.execute(
                'SELECT * FROM documents WHERE id = ? AND session_id = ?', 
                (doc_id, session_id)
            ).fetchone()
        else:
            row = conn.execute(
                'SELECT * FROM documents WHERE id = ?', 
                (doc_id,)
            ).fetchone()
        return dict(row) if row else None

def delete_document(doc_id: str, session_id: str | None = None) -> bool:
    with closing(get_connection()) as conn:
        with conn:
            if session_id is not None:
                cursor = conn.execute(
                    'DELETE FROM documents WHERE id = ? AND session_id = ?', 
                    (doc_id, session_id)
                )
            else:
                cursor = conn.execute(
                    'DELETE FROM documents WHERE id = ?', 
                    (doc_id,)
                )
            return cursor.rowcount > 0

def get_document_count(session_id: str | None = None) -> int:
    try:
        with closing(get_connection()) as conn:
            if session_id is not None:
                row = conn.execute(
                    'SELECT COUNT(*) FROM documents WHERE session_id = ?', 
                    (session_id,)
                ).fetchone()
            else:
                row = conn.execute('SELECT COUNT(*) FROM documents').fetchone()
            return row[0] if row else 0
    except sqlite3.OperationalError:
        init_db()
        with closing(get_connection()) as conn:
            if session_id is not None:
                row = conn.execute(
                    'SELECT COUNT(*) FROM documents WHERE session_id = ?', 
                    (session_id,)
                ).fetchone()
            else:
                row = conn.execute('SELECT COUNT(*) FROM documents').fetchone()
            return row[0] if row else 0
