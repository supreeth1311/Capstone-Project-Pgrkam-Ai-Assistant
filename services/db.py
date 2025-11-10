# services/db.py
import os, time
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text

DB_PATH = os.environ.get("DB_PATH", "sqlite:///pgrkam.db")
engine = create_engine(DB_PATH, future=True)

# ---------- helpers ----------
def _col_exists(con, table: str, col: str) -> bool:
    rows = list(con.execute(text(f"PRAGMA table_info({table})")))
    return any(r[1] == col for r in rows)

def _add_column_if_missing(con, table: str, col: str, decl: str):
    # NOTE: do NOT add UNIQUE here; create a unique index separately
    if not _col_exists(con, table, col):
        con.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {decl};"))

def _create_unique_index_if_missing(con, table: str, col: str, idx_name: str):
    con.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {table}({col});"))

# ---------- schema ----------
def init_db():
    with engine.begin() as con:
        # base tables
        con.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_key TEXT UNIQUE,           -- anon cookie or session key
          lang TEXT,
          district TEXT,
          prefs_json TEXT,
          created_at INTEGER
        );
        """))

        con.execute(text("""
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_key TEXT,
          role TEXT,
          content TEXT,
          intent TEXT,
          meta_json TEXT,
          ts INTEGER
        );
        """))

        con.execute(text("""
        CREATE TABLE IF NOT EXISTS uploads (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_key TEXT,
          filename TEXT,
          pages INT,
          ts INTEGER
        );
        """))

        con.execute(text("""
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_key TEXT,
          name TEXT,
          value REAL,
          payload TEXT,
          ts INTEGER
        );
        """))

        # ---- non-breaking migrations for auth fields ----
        # add columns (no unique constraint here)
        _add_column_if_missing(con, "users", "email", "TEXT")
        _add_column_if_missing(con, "users", "name", "TEXT")
        _add_column_if_missing(con, "users", "pass_hash", "TEXT")

        # add unique index on email (safe if duplicates don't exist)
        _create_unique_index_if_missing(con, "users", "email", "ux_users_email")
        # user_key already unique by table definition, but create index just in case
        _create_unique_index_if_missing(con, "users", "user_key", "ux_users_userkey")

# ---------- write ops ----------
def upsert_user(
    user_key: str,
    lang: str = "",
    district: str = "",
    prefs_json: str = ""
):
    """Legacy compatibility (original signature)."""
    now = int(time.time())
    with engine.begin() as con:
        con.execute(text("""
        INSERT INTO users(user_key,lang,district,prefs_json,created_at)
        VALUES (:uk,:lg,:ds,:pj,:ts)
        ON CONFLICT(user_key) DO UPDATE SET
          lang=excluded.lang,
          district=excluded.district,
          prefs_json=excluded.prefs_json;
        """), {"uk": user_key, "lg": lang, "ds": district, "pj": prefs_json, "ts": now})

def upsert_user_profile(
    user_key: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    pass_hash: Optional[str] = None,
    lang: str = "",
    district: str = "",
    prefs_json: str = ""
):
    """Auth-aware upsert (use this in app.py for login/registration)."""
    now = int(time.time())
    # Normalize empties to None
    email = email or None
    name = name or None
    pass_hash = pass_hash or None

    with engine.begin() as con:
        # Ensure a row exists for this user_key
        con.execute(text("""
        INSERT INTO users(user_key, created_at)
        VALUES (:uk, :ts)
        ON CONFLICT(user_key) DO NOTHING;
        """), {"uk": user_key, "ts": now})

        # Build dynamic update set
        sets = []
        params: Dict[str, Any] = {"uk": user_key, "lg": lang, "ds": district, "pj": prefs_json}
        if email is not None:
            sets.append("email=:em")
            params["em"] = email
        if name is not None:
            sets.append("name=:nm")
            params["nm"] = name
        if pass_hash is not None:
            sets.append("pass_hash=:ph")
            params["ph"] = pass_hash
        sets.append("lang=:lg")
        sets.append("district=:ds")
        sets.append("prefs_json=:pj")

        set_sql = ", ".join(sets)
        con.execute(text(f"UPDATE users SET {set_sql} WHERE user_key=:uk"), params)

def insert_message(user_key: str, role: str, content: str, intent: str = "", meta_json: str = ""):
    with engine.begin() as con:
        con.execute(text("""
        INSERT INTO messages(user_key,role,content,intent,meta_json,ts)
        VALUES (:uk,:r,:c,:i,:m,:ts)
        """), {"uk": user_key, "r": role, "c": content, "i": intent, "m": meta_json, "ts": int(time.time())})

def log_event(user_key: str, name: str, value: float = 0.0, payload: str = ""):
    with engine.begin() as con:
        con.execute(text("""
        INSERT INTO events(user_key,name,value,payload,ts)
        VALUES (:uk,:n,:v,:p,:ts)
        """), {"uk": user_key, "n": name, "v": value, "p": payload, "ts": int(time.time())})

# ---------- read ops ----------
def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with engine.begin() as con:
        row = con.execute(text("""
        SELECT id,user_key,email,name,pass_hash,lang,district,prefs_json,created_at
        FROM users WHERE email=:em
        """), {"em": email}).mappings().first()
        return dict(row) if row else None

def get_user_by_key(user_key: str) -> Optional[Dict[str, Any]]:
    with engine.begin() as con:
        row = con.execute(text("""
        SELECT id,user_key,email,name,pass_hash,lang,district,prefs_json,created_at
        FROM users WHERE user_key=:uk
        """), {"uk": user_key}).mappings().first()
        return dict(row) if row else None

def verify_login(email: str, pass_hash: str) -> Optional[Dict[str, Any]]:
    """Return user row if email+pass_hash match, else None."""
    with engine.begin() as con:
        row = con.execute(text("""
        SELECT id,user_key,email,name,pass_hash,lang,district,prefs_json,created_at
        FROM users WHERE email=:em AND pass_hash=:ph
        """), {"em": email, "ph": pass_hash}).mappings().first()
        return dict(row) if row else None
