"""Price tracking with SQLite persistence, alerts, and trend analysis.

Tracks price history for every product variant across monitored stores.
Supports: price drop/increase alerts, historical charts data, best-buy timing.
"""
import os
import json
import time
import sqlite3
import logging
import statistics
from datetime import datetime, timedelta
from typing import Optional

from app.config import MONITOR_DB

logger = logging.getLogger(__name__)

# Alert thresholds
PRICE_DROP_THRESHOLD = 0.10  # 10% drop triggers alert
PRICE_SPIKE_THRESHOLD = 0.20  # 20% increase triggers alert
HISTORY_RETENTION_DAYS = 90


def _get_db():
    """Get DB connection with price tracking tables."""
    os.makedirs(os.path.dirname(MONITOR_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(MONITOR_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            product_id TEXT NOT NULL,
            variant_id TEXT NOT NULL,
            title TEXT,
            price REAL NOT NULL,
            compare_at_price REAL,
            currency TEXT DEFAULT 'USD',
            recorded_at REAL NOT NULL,
            UNIQUE(domain, variant_id, recorded_at)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            product_id TEXT NOT NULL,
            variant_id TEXT NOT NULL,
            title TEXT,
            alert_type TEXT NOT NULL,
            old_price REAL NOT NULL,
            new_price REAL NOT NULL,
            change_pct REAL NOT NULL,
            created_at REAL NOT NULL,
            notified INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_domain_variant
        ON price_history(domain, variant_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_recorded
        ON price_history(recorded_at)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_notified
        ON price_alerts(notified)
    """)
    conn.commit()
    return conn


def record_prices(domain: str, products: list, currency: str = "USD") -> dict:
    """Record current prices for all variants. Returns change summary."""
    conn = _get_db()
    now = time.time()
    recorded = 0
    alerts = []

    try:
        for product in products:
            pid = str(product.get("id", ""))
            title = (product.get("title") or "")[:100]
            for variant in product.get("variants", []):
                vid = str(variant.get("id", ""))
                try:
                    price = float(variant.get("price", 0))
                except (ValueError, TypeError):
                    continue
                if price <= 0:
                    continue

                compare_at = None
                if variant.get("compare_at_price"):
                    try:
                        compare_at = float(variant["compare_at_price"])
                    except (ValueError, TypeError):
                        pass

                # Get last recorded price
                row = conn.execute(
                    """SELECT price FROM price_history
                       WHERE domain = ? AND variant_id = ?
                       ORDER BY recorded_at DESC LIMIT 1""",
                    (domain, vid),
                ).fetchone()

                last_price = row[0] if row else None

                # Record new price
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO price_history
                           (domain, product_id, variant_id, title, price,
                            compare_at_price, currency, recorded_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (domain, pid, vid, title, price, compare_at, currency, now),
                    )
                    recorded += 1
                except sqlite3.IntegrityError:
                    pass

                # Check for significant price changes
                if last_price and last_price > 0:
                    change_pct = (price - last_price) / last_price
                    alert = None
                    if change_pct <= -PRICE_DROP_THRESHOLD:
                        alert = _create_alert(
                            conn, domain, pid, vid, title,
                            "price_drop", last_price, price, change_pct, now
                        )
                    elif change_pct >= PRICE_SPIKE_THRESHOLD:
                        alert = _create_alert(
                            conn, domain, pid, vid, title,
                            "price_spike", last_price, price, change_pct, now
                        )
                    if alert:
                        alerts.append(alert)

        conn.commit()
    finally:
        conn.close()

    return {"recorded": recorded, "alerts": alerts}


def _create_alert(conn, domain, pid, vid, title, alert_type,
                  old_price, new_price, change_pct, now):
    """Create a price alert record."""
    conn.execute(
        """INSERT INTO price_alerts
           (domain, product_id, variant_id, title, alert_type,
            old_price, new_price, change_pct, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (domain, pid, vid, title, alert_type,
         old_price, new_price, change_pct, now),
    )
    return {
        "domain": domain,
        "product_id": pid,
        "variant_id": vid,
        "title": title,
        "type": alert_type,
        "old_price": old_price,
        "new_price": new_price,
        "change_pct": round(change_pct * 100, 1),
    }


def get_price_history(domain: str, variant_id: str,
                      days: int = 30) -> list[dict]:
    """Get price history for a specific variant."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT price, compare_at_price, currency, recorded_at, title
               FROM price_history
               WHERE domain = ? AND variant_id = ? AND recorded_at >= ?
               ORDER BY recorded_at ASC""",
            (domain, variant_id, cutoff),
        ).fetchall()
        return [
            {
                "price": r[0],
                "compare_at_price": r[1],
                "currency": r[2],
                "recorded_at": r[3],
                "date": datetime.fromtimestamp(r[3]).strftime("%Y-%m-%d %H:%M"),
                "title": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_price_summary(domain: str, days: int = 30) -> dict:
    """Get price summary statistics for a store."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT variant_id, title,
                      MIN(price) as min_price,
                      MAX(price) as max_price,
                      AVG(price) as avg_price,
                      COUNT(*) as data_points
               FROM price_history
               WHERE domain = ? AND recorded_at >= ?
               GROUP BY variant_id
               HAVING data_points > 1
               ORDER BY (MAX(price) - MIN(price)) / AVG(price) DESC
               LIMIT 20""",
            (domain, cutoff),
        ).fetchall()

        volatile = []
        for r in rows:
            spread = r[3] - r[2]
            volatility = (spread / r[4]) * 100 if r[4] > 0 else 0
            volatile.append({
                "variant_id": r[0],
                "title": r[1],
                "min_price": round(r[2], 2),
                "max_price": round(r[3], 2),
                "avg_price": round(r[4], 2),
                "data_points": r[5],
                "volatility_pct": round(volatility, 1),
            })

        # Overall stats
        overall = conn.execute(
            """SELECT COUNT(DISTINCT variant_id), AVG(price),
                      MIN(price), MAX(price)
               FROM price_history
               WHERE domain = ? AND recorded_at >= ?""",
            (domain, cutoff),
        ).fetchone()

        return {
            "domain": domain,
            "days": days,
            "tracked_variants": overall[0] or 0,
            "avg_price": round(overall[1] or 0, 2),
            "min_price": round(overall[2] or 0, 2),
            "max_price": round(overall[3] or 0, 2),
            "most_volatile": volatile,
        }
    finally:
        conn.close()


def get_pending_alerts(limit: int = 50) -> list[dict]:
    """Get unnotified price alerts."""
    conn = _get_db()
    try:
        rows = conn.execute(
            """SELECT id, domain, product_id, variant_id, title,
                      alert_type, old_price, new_price, change_pct, created_at
               FROM price_alerts
               WHERE notified = 0
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0], "domain": r[1], "product_id": r[2],
                "variant_id": r[3], "title": r[4], "type": r[5],
                "old_price": r[6], "new_price": r[7],
                "change_pct": round(r[8] * 100, 1),
                "created_at": datetime.fromtimestamp(r[9]).strftime("%Y-%m-%d %H:%M"),
            }
            for r in rows
        ]
    finally:
        conn.close()


def mark_alerts_notified(alert_ids: list[int]) -> int:
    """Mark alerts as notified."""
    if not alert_ids:
        return 0
    conn = _get_db()
    try:
        placeholders = ",".join("?" for _ in alert_ids)
        cur = conn.execute(
            f"UPDATE price_alerts SET notified = 1 WHERE id IN ({placeholders})",
            alert_ids,
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def detect_discount_patterns(domain: str, days: int = 60) -> list[dict]:
    """Detect products with recurring discount patterns (e.g., weekly sales)."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT variant_id, title, price, compare_at_price, recorded_at
               FROM price_history
               WHERE domain = ? AND recorded_at >= ?
                     AND compare_at_price IS NOT NULL
                     AND compare_at_price > price
               ORDER BY variant_id, recorded_at""",
            (domain, cutoff),
        ).fetchall()

        # Group by variant
        variants = {}
        for r in rows:
            vid = r[0]
            if vid not in variants:
                variants[vid] = {"title": r[1], "discounts": []}
            discount_pct = ((r[3] - r[2]) / r[3]) * 100
            variants[vid]["discounts"].append({
                "price": r[2],
                "compare_at": r[3],
                "discount_pct": round(discount_pct, 1),
                "date": datetime.fromtimestamp(r[4]).strftime("%Y-%m-%d"),
            })

        patterns = []
        for vid, data in variants.items():
            if len(data["discounts"]) >= 2:
                avg_discount = statistics.mean(
                    d["discount_pct"] for d in data["discounts"]
                )
                patterns.append({
                    "variant_id": vid,
                    "title": data["title"],
                    "discount_count": len(data["discounts"]),
                    "avg_discount_pct": round(avg_discount, 1),
                    "latest_discount": data["discounts"][-1],
                })

        return sorted(patterns, key=lambda x: -x["discount_count"])
    finally:
        conn.close()


def get_best_buy_timing(domain: str, variant_id: str,
                        days: int = 60) -> dict:
    """Analyze price history to suggest best time to buy."""
    history = get_price_history(domain, variant_id, days)
    if len(history) < 3:
        return {"recommendation": "insufficient_data", "data_points": len(history)}

    prices = [h["price"] for h in history]
    current = prices[-1]
    avg = statistics.mean(prices)
    low = min(prices)
    high = max(prices)
    stdev = statistics.stdev(prices) if len(prices) > 1 else 0

    # Determine recommendation
    if current <= low * 1.05:
        rec = "strong_buy"
        reason = f"Current ${current:.2f} is near all-time low ${low:.2f}"
    elif current <= avg - stdev:
        rec = "buy"
        reason = f"Current ${current:.2f} is below average ${avg:.2f}"
    elif current >= avg + stdev:
        rec = "wait"
        reason = f"Current ${current:.2f} is above average ${avg:.2f}, likely to drop"
    else:
        rec = "hold"
        reason = f"Current ${current:.2f} is near average ${avg:.2f}"

    # Trend detection (last 5 data points)
    recent = prices[-5:] if len(prices) >= 5 else prices
    if len(recent) >= 3:
        if all(recent[i] <= recent[i - 1] for i in range(1, len(recent))):
            trend = "falling"
        elif all(recent[i] >= recent[i - 1] for i in range(1, len(recent))):
            trend = "rising"
        else:
            trend = "stable"
    else:
        trend = "unknown"

    return {
        "recommendation": rec,
        "reason": reason,
        "current_price": current,
        "avg_price": round(avg, 2),
        "min_price": low,
        "max_price": high,
        "std_dev": round(stdev, 2),
        "trend": trend,
        "data_points": len(prices),
    }


def cleanup_old_records(days: int = HISTORY_RETENTION_DAYS) -> int:
    """Remove price history older than retention period."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        cur = conn.execute(
            "DELETE FROM price_history WHERE recorded_at < ?", (cutoff,)
        )
        conn.execute(
            "DELETE FROM price_alerts WHERE created_at < ?", (cutoff,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
