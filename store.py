"""Stockage SQLite local. Items du jour, items sauvegardés, sources éditables."""
import sqlite3
import json
import os
from datetime import datetime, timezone

DB = os.environ.get("BRIEFING_DB", "briefing.db")


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    c = _conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT UNIQUE,
        source_type TEXT, source_name TEXT,
        titre TEXT, resume TEXT, theme TEXT,
        importance INTEGER, url TEXT, thumbnail TEXT,
        published TEXT, collected_at TEXT, is_hero INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS saved (
        uid TEXT PRIMARY KEY, payload TEXT, saved_at TEXT
    );
    CREATE TABLE IF NOT EXISTS sources (
        key TEXT PRIMARY KEY, payload TEXT
    );
    """)
    c.commit(); c.close()


def replace_today(briefing: dict):
    """Remplace le briefing courant (on garde un seul briefing actif à la fois)."""
    c = _conn()
    c.execute("DELETE FROM items")
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    if briefing.get("hero"):
        rows.append((briefing["hero"], 1))
    for it in briefing.get("items", []):
        rows.append((it, 0))
    for it, is_hero in rows:
        uid = f'{it["source_type"]}:{it["url"]}'
        c.execute("""INSERT OR REPLACE INTO items
            (uid,source_type,source_name,titre,resume,theme,importance,url,thumbnail,published,collected_at,is_hero)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (uid, it["source_type"], it["source_name"], it.get("titre"), it.get("resume"),
             it.get("theme"), it.get("importance", 5), it.get("url"),
             it.get("thumbnail", ""), it.get("published", ""), now, is_hero))
    c.commit(); c.close()


def get_briefing() -> dict:
    c = _conn()
    rows = [dict(r) for r in c.execute("SELECT * FROM items ORDER BY is_hero DESC, importance DESC")]
    c.close()
    hero = next((r for r in rows if r["is_hero"]), None)
    items = [r for r in rows if not r["is_hero"]]
    return {"hero": hero, "items": items}


def save_item(payload: dict):
    c = _conn()
    c.execute("INSERT OR REPLACE INTO saved (uid,payload,saved_at) VALUES (?,?,?)",
              (payload["uid"], json.dumps(payload, ensure_ascii=False),
               datetime.now(timezone.utc).isoformat()))
    c.commit(); c.close()


def unsave_item(uid: str):
    c = _conn(); c.execute("DELETE FROM saved WHERE uid=?", (uid,)); c.commit(); c.close()


def get_saved() -> list:
    c = _conn()
    rows = [json.loads(r["payload"]) for r in c.execute("SELECT payload FROM saved ORDER BY saved_at DESC")]
    c.close(); return rows


def load_sources() -> dict:
    c = _conn()
    r = c.execute("SELECT payload FROM sources WHERE key='config'").fetchone()
    c.close()
    if r:
        return json.loads(r["payload"])
    with open("config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    save_sources(cfg)
    return cfg


def save_sources(cfg: dict):
    c = _conn()
    c.execute("INSERT OR REPLACE INTO sources (key,payload) VALUES ('config',?)",
              (json.dumps(cfg, ensure_ascii=False),))
    c.commit(); c.close()
