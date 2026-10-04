import sqlite3
from config.settings import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_connection()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, full_name TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER PRIMARY KEY, data_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, filename TEXT, document_type TEXT, path TEXT, extracted_text TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY AUTOINCREMENT, external_id TEXT, title TEXT, organization TEXT, opportunity_type TEXT, country TEXT, city TEXT, description TEXT, requirements_json TEXT, deadline TEXT, funding TEXT, tuition TEXT, application_url TEXT, source_url TEXT, source_name TEXT, verification_status TEXT DEFAULT 'UNVERIFIED', last_verified TEXT, metadata_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, opportunity_key TEXT, title TEXT, organization TEXT, status TEXT DEFAULT 'Saved', deadline TEXT, next_action TEXT, notes TEXT DEFAULT '', updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    ''')
    user_cols = {row['name'] for row in conn.execute('PRAGMA table_info(users)').fetchall()}
    if 'full_name' not in user_cols:
        conn.execute('ALTER TABLE users ADD COLUMN full_name TEXT')
    conn.execute("INSERT OR IGNORE INTO users(id,email,full_name) VALUES(1,'local@opportune.ai','Local User')")
    conn.commit()
    conn.close()


def save_profile(user_id, data_json):
    conn = get_connection()
    conn.execute('''INSERT INTO profiles(user_id,data_json,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET data_json=excluded.data_json,updated_at=CURRENT_TIMESTAMP''', (user_id, data_json))
    conn.commit(); conn.close()


def load_profile(user_id):
    conn = get_connection(); row = conn.execute('SELECT data_json FROM profiles WHERE user_id=?', (user_id,)).fetchone(); conn.close()
    return row['data_json'] if row else '{}'


def save_document(user_id, filename, document_type, path, extracted_text):
    conn = get_connection()
    existing = conn.execute('SELECT id FROM documents WHERE user_id=? AND filename=? AND document_type=? ORDER BY id DESC LIMIT 1', (user_id, filename, document_type)).fetchone()
    if existing:
        conn.execute('UPDATE documents SET path=?, extracted_text=?, created_at=CURRENT_TIMESTAMP WHERE id=?', (path, extracted_text, existing['id']))
    else:
        conn.execute('INSERT INTO documents(user_id,filename,document_type,path,extracted_text) VALUES(?,?,?,?,?)', (user_id,filename,document_type,path,extracted_text))
    conn.commit(); conn.close()


def list_documents(user_id):
    conn = get_connection(); rows = conn.execute('SELECT * FROM documents WHERE user_id=? ORDER BY created_at DESC,id DESC', (user_id,)).fetchall(); conn.close(); return rows


def delete_document(document_id, user_id):
    conn = get_connection()
    row = conn.execute('SELECT path FROM documents WHERE id=? AND user_id=?', (document_id, user_id)).fetchone()
    if not row:
        conn.close(); return False
    conn.execute('DELETE FROM documents WHERE id=? AND user_id=?', (document_id, user_id))
    conn.commit(); conn.close()
    return row['path']


def save_application(user_id, data):
    conn = get_connection(); conn.execute('''INSERT INTO applications(user_id,opportunity_key,title,organization,status,deadline,next_action,notes) VALUES(?,?,?,?,?,?,?,?)''', (user_id,data.get('opportunity_key'),data.get('title'),data.get('organization'),data.get('status','Saved'),data.get('deadline'),data.get('next_action'),data.get('notes',''))); conn.commit(); conn.close()


def list_applications(user_id):
    conn = get_connection(); rows = conn.execute('SELECT * FROM applications WHERE user_id=? ORDER BY updated_at DESC', (user_id,)).fetchall(); conn.close(); return rows


def update_application_status(app_id, status):
    conn = get_connection(); conn.execute('UPDATE applications SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?', (status,app_id)); conn.commit(); conn.close()


def delete_application(app_id, user_id=1):
    conn=get_connection()
    row=conn.execute('SELECT id FROM applications WHERE id=? AND user_id=?',(int(app_id),int(user_id))).fetchone()
    if not row:
        conn.close(); return False
    conn.execute('DELETE FROM applications WHERE id=? AND user_id=?',(int(app_id),int(user_id)))
    conn.commit(); conn.close(); return True


def create_guest_user(token: str) -> int:
    """A private per-visitor user row (used on shared deployments)."""
    conn = get_connection()
    cur = conn.execute("INSERT INTO users(email,full_name) VALUES(?,?)", (f"guest-{token}@opportune.local", "Guest"))
    conn.commit(); uid = cur.lastrowid; conn.close()
    return int(uid)


def purge_old_guests(days: int = 2) -> int:
    """Delete guest users (and their profile, documents, applications, uploaded files) older than `days`."""
    from pathlib import Path
    conn = get_connection()
    rows = conn.execute("SELECT id FROM users WHERE email LIKE 'guest-%' AND created_at < datetime('now', ?)", (f"-{int(days)} days",)).fetchall()
    ids = [r["id"] for r in rows]
    for uid in ids:
        for doc in conn.execute("SELECT path FROM documents WHERE user_id=?", (uid,)).fetchall():
            try:
                Path(doc["path"] or "").unlink(missing_ok=True)
            except Exception:
                pass
        for table in ("documents", "applications", "profiles"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit(); conn.close()
    return len(ids)
