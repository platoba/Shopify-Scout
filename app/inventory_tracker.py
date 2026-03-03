"""Inventory tracking and sell-through rate analysis.

Tracks variant inventory levels to detect:
- Bestsellers (fast sell-through)
- Dead stock (no movement)
- Restocking patterns
- Out-of-stock frequency
"""
import os
import time
import sqlite3
import logging
from datetime import datetime
from typing import Optional

from app.config import MONITOR_DB

logger = logging.getLogger(__name__)


def _get_db():
    """Get DB connection with inventory tables."""
    os.makedirs(os.path.dirname(MONITOR_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(MONITOR_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            product_id TEXT NOT NULL,
            variant_id TEXT NOT NULL,
            title TEXT,
            sku TEXT,
            available INTEGER,
            inventory_policy TEXT,
            recorded_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            variant_id TEXT NOT NULL,
            title TEXT,
            event_type TEXT NOT NULL,
            old_qty INTEGER,
            new_qty INTEGER,
            delta INTEGER,
            recorded_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_inv_domain_variant
        ON inventory_snapshots(domain, variant_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_events_type
        ON stock_events(event_type, recorded_at)
    """)
    conn.commit()
    return conn


def record_inventory(domain: str, products: list) -> dict:
    """Record inventory levels for all variants. Returns events."""
    conn = _get_db()
    now = time.time()
    recorded = 0
    events = []

    try:
        for product in products:
            pid = str(product.get("id", ""))
            title = (product.get("title") or "")[:100]

            for variant in product.get("variants", []):
                vid = str(variant.get("id", ""))
                sku = (variant.get("sku") or "")[:50]

                # Determine availability
                available = _get_availability(variant)
                policy = variant.get("inventory_policy", "deny")

                # Get previous snapshot
                prev = conn.execute(
                    """SELECT available FROM inventory_snapshots
                       WHERE domain = ? AND variant_id = ?
                       ORDER BY recorded_at DESC LIMIT 1""",
                    (domain, vid),
                ).fetchone()

                # Record snapshot
                conn.execute(
                    """INSERT INTO inventory_snapshots
                       (domain, product_id, variant_id, title, sku,
                        available, inventory_policy, recorded_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (domain, pid, vid, title, sku, available, policy, now),
                )
                recorded += 1

                # Detect events
                if prev is not None:
                    old_qty = prev[0]
                    if old_qty is not None and available is not None:
                        delta = available - old_qty
                        event = _detect_event(
                            conn, domain, vid, title,
                            old_qty, available, delta, now
                        )
                        if event:
                            events.append(event)

        conn.commit()
    except Exception as e:
        logger.error(f"Failed to record inventory: {e}")
    finally:
        conn.close()

    return {"recorded": recorded, "events": events}


def _get_availability(variant: dict) -> Optional[int]:
    """Extract available quantity from variant data."""
    # Shopify products.json doesn't always expose inventory
    # Check inventory_quantity first, then available flag
    if "inventory_quantity" in variant:
        try:
            return int(variant["inventory_quantity"])
        except (ValueError, TypeError):
            pass
    # Use available flag as binary
    if "available" in variant:
        return 1 if variant["available"] else 0
    return None


def _detect_event(conn, domain, vid, title, old_qty, new_qty, delta, now):
    """Detect and record inventory events."""
    if delta == 0:
        return None

    if old_qty > 0 and new_qty <= 0:
        event_type = "stockout"
    elif old_qty <= 0 and new_qty > 0:
        event_type = "restock"
    elif delta > 0:
        event_type = "restock"
    elif delta < 0:
        event_type = "sold"
    else:
        return None

    conn.execute(
        """INSERT INTO stock_events
           (domain, variant_id, title, event_type,
            old_qty, new_qty, delta, recorded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (domain, vid, title, event_type, old_qty, new_qty, delta, now),
    )

    return {
        "domain": domain,
        "variant_id": vid,
        "title": title,
        "event": event_type,
        "old_qty": old_qty,
        "new_qty": new_qty,
        "delta": delta,
    }


def get_bestsellers(domain: str, days: int = 30,
                    top_n: int = 20) -> list[dict]:
    """Find bestsellers by total units sold."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT variant_id, title,
                      SUM(ABS(delta)) as total_sold,
                      COUNT(*) as sale_events,
                      MIN(recorded_at) as first_sale,
                      MAX(recorded_at) as last_sale
               FROM stock_events
               WHERE domain = ? AND event_type = 'sold'
                     AND recorded_at >= ?
               GROUP BY variant_id
               ORDER BY total_sold DESC
               LIMIT ?""",
            (domain, cutoff, top_n),
        ).fetchall()

        results = []
        for r in rows:
            days_active = max(1, (r[5] - r[4]) / 86400)
            results.append({
                "variant_id": r[0],
                "title": r[1],
                "total_sold": r[2],
                "sale_events": r[3],
                "daily_rate": round(r[2] / days_active, 1),
                "velocity": _velocity_label(r[2] / days_active),
            })
        return results
    finally:
        conn.close()


def _velocity_label(daily_rate: float) -> str:
    """Label sell velocity."""
    if daily_rate >= 10:
        return "🚀 VIRAL"
    elif daily_rate >= 5:
        return "🔥 HOT"
    elif daily_rate >= 2:
        return "📈 FAST"
    elif daily_rate >= 0.5:
        return "✅ STEADY"
    elif daily_rate >= 0.1:
        return "🐌 SLOW"
    else:
        return "💤 DEAD"


def get_dead_stock(domain: str, days: int = 30,
                   min_days_stale: int = 14) -> list[dict]:
    """Find variants with no sales activity for extended period."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    stale_cutoff = time.time() - (min_days_stale * 86400)
    try:
        # Get all tracked variants
        all_variants = conn.execute(
            """SELECT DISTINCT variant_id, title, available
               FROM inventory_snapshots
               WHERE domain = ? AND recorded_at >= ?
               ORDER BY recorded_at DESC""",
            (domain, cutoff),
        ).fetchall()

        # Get variants with recent sales
        active = set(row[0] for row in conn.execute(
            """SELECT DISTINCT variant_id FROM stock_events
               WHERE domain = ? AND event_type = 'sold'
                     AND recorded_at >= ?""",
            (domain, stale_cutoff),
        ).fetchall())

        dead = []
        seen = set()
        for r in all_variants:
            vid = r[0]
            if vid not in active and vid not in seen:
                seen.add(vid)
                # Get last sale date
                last_sale = conn.execute(
                    """SELECT MAX(recorded_at) FROM stock_events
                       WHERE domain = ? AND variant_id = ?
                             AND event_type = 'sold'""",
                    (domain, vid),
                ).fetchone()
                last_sale_date = (
                    datetime.fromtimestamp(last_sale[0]).strftime("%Y-%m-%d")
                    if last_sale and last_sale[0] else "never"
                )
                dead.append({
                    "variant_id": vid,
                    "title": r[1],
                    "current_stock": r[2],
                    "last_sale": last_sale_date,
                    "status": "💤 DEAD_STOCK",
                })

        return dead[:30]
    finally:
        conn.close()


def get_stockout_frequency(domain: str, days: int = 30) -> list[dict]:
    """Find variants that frequently go out of stock."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT variant_id, title,
                      COUNT(*) as stockout_count,
                      MIN(recorded_at) as first_event,
                      MAX(recorded_at) as last_event
               FROM stock_events
               WHERE domain = ? AND event_type = 'stockout'
                     AND recorded_at >= ?
               GROUP BY variant_id
               ORDER BY stockout_count DESC
               LIMIT 20""",
            (domain, cutoff),
        ).fetchall()

        return [
            {
                "variant_id": r[0],
                "title": r[1],
                "stockout_count": r[2],
                "frequency": f"~every {max(1, int((r[4]-r[3])/86400/max(1,r[2])))} days"
                if r[2] > 1 else "once",
                "signal": "high_demand" if r[2] >= 3 else "supply_issue",
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_restock_patterns(domain: str, days: int = 30) -> list[dict]:
    """Analyze restocking patterns."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT variant_id, title,
                      COUNT(*) as restock_count,
                      AVG(new_qty) as avg_restock_qty,
                      MAX(new_qty) as max_restock_qty
               FROM stock_events
               WHERE domain = ? AND event_type = 'restock'
                     AND recorded_at >= ?
               GROUP BY variant_id
               HAVING restock_count >= 2
               ORDER BY restock_count DESC
               LIMIT 20""",
            (domain, cutoff),
        ).fetchall()

        return [
            {
                "variant_id": r[0],
                "title": r[1],
                "restock_count": r[2],
                "avg_restock_qty": round(r[3] or 0),
                "max_restock_qty": r[4] or 0,
                "pattern": "regular" if r[2] >= 4 else "occasional",
            }
            for r in rows
        ]
    finally:
        conn.close()


def inventory_summary(domain: str, days: int = 30) -> dict:
    """Generate comprehensive inventory summary for a store."""
    bestsellers = get_bestsellers(domain, days, top_n=10)
    dead_stock = get_dead_stock(domain, days)
    stockouts = get_stockout_frequency(domain, days)

    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        stats = conn.execute(
            """SELECT COUNT(DISTINCT variant_id),
                      SUM(CASE WHEN event_type='sold' THEN ABS(delta) ELSE 0 END),
                      SUM(CASE WHEN event_type='stockout' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN event_type='restock' THEN 1 ELSE 0 END)
               FROM stock_events
               WHERE domain = ? AND recorded_at >= ?""",
            (domain, cutoff),
        ).fetchone()

        return {
            "domain": domain,
            "period_days": days,
            "tracked_variants": stats[0] or 0,
            "total_units_sold": stats[1] or 0,
            "stockout_events": stats[2] or 0,
            "restock_events": stats[3] or 0,
            "top_sellers": bestsellers,
            "dead_stock_count": len(dead_stock),
            "frequent_stockouts": stockouts[:5],
        }
    finally:
        conn.close()
