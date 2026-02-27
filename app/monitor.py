"""Store monitoring with SQLite persistence and change detection."""
import os
import json
import time
import sqlite3
import logging
from typing import Optional
from app.config import MONITOR_DB

logger = logging.getLogger(__name__)


def _ensure_db():
    """Create DB and tables if not exist."""
    os.makedirs(os.path.dirname(MONITOR_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(MONITOR_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watched_stores (
            domain TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            added_at REAL NOT NULL,
            last_check REAL DEFAULT 0,
            last_product_count INTEGER DEFAULT 0,
            last_snapshot TEXT DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS store_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            checked_at REAL NOT NULL,
            product_count INTEGER,
            avg_price REAL,
            new_products TEXT DEFAULT '[]',
            removed_products TEXT DEFAULT '[]'
        )
    """)
    conn.commit()
    return conn


def add_watch(domain: str, chat_id: int) -> bool:
    """Add a store to the watch list."""
    conn = _ensure_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO watched_stores (domain, chat_id, added_at) VALUES (?, ?, ?)",
            (domain, chat_id, time.time()),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to add watch: {e}")
        return False
    finally:
        conn.close()


def remove_watch(domain: str, chat_id: int) -> bool:
    """Remove a store from the watch list."""
    conn = _ensure_db()
    try:
        cur = conn.execute(
            "DELETE FROM watched_stores WHERE domain = ? AND chat_id = ?",
            (domain, chat_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to remove watch: {e}")
        return False
    finally:
        conn.close()


def list_watches(chat_id: int) -> list[dict]:
    """List all watched stores for a chat."""
    conn = _ensure_db()
    try:
        rows = conn.execute(
            "SELECT domain, added_at, last_check, last_product_count FROM watched_stores WHERE chat_id = ?",
            (chat_id,),
        ).fetchall()
        return [
            {"domain": r[0], "added_at": r[1], "last_check": r[2], "last_product_count": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def get_all_watches() -> list[dict]:
    """Get all watched stores across all chats."""
    conn = _ensure_db()
    try:
        rows = conn.execute(
            "SELECT domain, chat_id, last_check, last_product_count, last_snapshot FROM watched_stores"
        ).fetchall()
        return [
            {
                "domain": r[0], "chat_id": r[1], "last_check": r[2],
                "last_product_count": r[3], "last_snapshot": json.loads(r[4] or "{}"),
            }
            for r in rows
        ]
    finally:
        conn.close()


def save_snapshot(domain: str, product_count: int, avg_price: float,
                  new_products: list, removed_products: list, product_ids: dict):
    """Save a monitoring snapshot and update the watched store."""
    conn = _ensure_db()
    try:
        now = time.time()
        conn.execute(
            """INSERT INTO store_snapshots (domain, checked_at, product_count, avg_price, new_products, removed_products)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (domain, now, product_count, avg_price,
             json.dumps(new_products, ensure_ascii=False),
             json.dumps(removed_products, ensure_ascii=False)),
        )
        conn.execute(
            """UPDATE watched_stores SET last_check = ?, last_product_count = ?, last_snapshot = ?
               WHERE domain = ?""",
            (now, product_count, json.dumps(product_ids, ensure_ascii=False), domain),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")
    finally:
        conn.close()


def detect_changes(domain: str, current_products: list, last_snapshot: dict) -> dict:
    """Detect new and removed products compared to last snapshot."""
    current_ids = {str(p["id"]): p.get("title", "")[:60] for p in current_products}
    last_ids = last_snapshot if isinstance(last_snapshot, dict) else {}

    new_products = [
        {"id": pid, "title": title}
        for pid, title in current_ids.items()
        if pid not in last_ids
    ]
    removed_products = [
        {"id": pid, "title": title}
        for pid, title in last_ids.items()
        if pid not in current_ids
    ]

    return {
        "new": new_products,
        "removed": removed_products,
        "current_ids": current_ids,
        "changed": bool(new_products or removed_products),
    }
