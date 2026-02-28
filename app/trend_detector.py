"""Trend detection across monitored Shopify stores.

Identifies trending products, hot/cold categories, and cross-store patterns.
"""
import time
import sqlite3
import logging
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

from app.config import MONITOR_DB

logger = logging.getLogger(__name__)


def _get_db():
    """Get DB connection with trend tables."""
    import os
    os.makedirs(os.path.dirname(MONITOR_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(MONITOR_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS product_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            product_id TEXT NOT NULL,
            title TEXT,
            product_type TEXT,
            vendor TEXT,
            price REAL,
            variant_count INTEGER DEFAULT 1,
            tags TEXT DEFAULT '[]',
            created_at_store TEXT,
            recorded_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trend_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_type TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_domain
        ON product_signals(domain, recorded_at)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_type
        ON product_signals(product_type)
    """)
    conn.commit()
    return conn


def record_product_signals(domain: str, products: list) -> int:
    """Record product data points for trend analysis."""
    conn = _get_db()
    now = time.time()
    count = 0
    try:
        for p in products:
            pid = str(p.get("id", ""))
            tags = p.get("tags", "")
            if isinstance(tags, list):
                tags_list = tags
            else:
                tags_list = [t.strip() for t in str(tags).split(",") if t.strip()]

            conn.execute(
                """INSERT INTO product_signals
                   (domain, product_id, title, product_type, vendor,
                    price, variant_count, tags, created_at_store, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    domain, pid,
                    (p.get("title") or "")[:100],
                    p.get("product_type") or "Other",
                    (p.get("vendor") or "")[:80],
                    _avg_price(p),
                    len(p.get("variants", [])),
                    ",".join(tags_list[:20]),
                    p.get("created_at", ""),
                    now,
                ),
            )
            count += 1
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to record signals: {e}")
    finally:
        conn.close()
    return count


def _avg_price(product: dict) -> float:
    """Get average variant price."""
    prices = []
    for v in product.get("variants", []):
        try:
            p = float(v.get("price", 0))
            if p > 0:
                prices.append(p)
        except (ValueError, TypeError):
            pass
    return statistics.mean(prices) if prices else 0.0


def detect_hot_categories(days: int = 14, min_stores: int = 2) -> list[dict]:
    """Find product types appearing across multiple stores recently."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT product_type,
                      COUNT(DISTINCT domain) as store_count,
                      COUNT(DISTINCT product_id) as product_count,
                      AVG(price) as avg_price,
                      MIN(price) as min_price,
                      MAX(price) as max_price
               FROM product_signals
               WHERE recorded_at >= ? AND product_type != 'Other'
               GROUP BY product_type
               HAVING store_count >= ?
               ORDER BY product_count DESC
               LIMIT 30""",
            (cutoff, min_stores),
        ).fetchall()

        return [
            {
                "category": r[0],
                "store_count": r[1],
                "product_count": r[2],
                "avg_price": round(r[3], 2),
                "price_range": f"${r[4]:.0f}-${r[5]:.0f}",
                "heat_score": _calc_heat(r[1], r[2]),
            }
            for r in rows
        ]
    finally:
        conn.close()


def _calc_heat(store_count: int, product_count: int) -> str:
    """Calculate heat level from store spread and product count."""
    score = store_count * 3 + product_count
    if score >= 20:
        return "🔥🔥🔥 HOT"
    elif score >= 10:
        return "🔥🔥 WARM"
    elif score >= 5:
        return "🔥 RISING"
    else:
        return "❄️ COOL"


def detect_trending_tags(days: int = 14, top_n: int = 20) -> list[dict]:
    """Find most common tags across stores."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT tags, domain FROM product_signals
               WHERE recorded_at >= ? AND tags != ''""",
            (cutoff,),
        ).fetchall()

        tag_counter = Counter()
        tag_stores = defaultdict(set)
        for r in rows:
            for tag in r[0].split(","):
                tag = tag.strip().lower()
                if tag and len(tag) > 1:
                    tag_counter[tag] += 1
                    tag_stores[tag].add(r[1])

        results = []
        for tag, count in tag_counter.most_common(top_n):
            results.append({
                "tag": tag,
                "count": count,
                "store_spread": len(tag_stores[tag]),
                "stores": sorted(tag_stores[tag])[:5],
            })
        return results
    finally:
        conn.close()


def detect_new_product_surge(domain: str, days: int = 7,
                              threshold: int = 10) -> Optional[dict]:
    """Detect if a store has added many new products recently (launch signal)."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        # Products with recent store-side created_at
        rows = conn.execute(
            """SELECT COUNT(DISTINCT product_id), GROUP_CONCAT(DISTINCT product_type)
               FROM product_signals
               WHERE domain = ? AND recorded_at >= ?
                     AND created_at_store >= ?""",
            (domain, cutoff, datetime.now(tz=timezone.utc).replace(
                hour=0, minute=0).isoformat()[:10]),
        ).fetchone()

        new_count = rows[0] or 0
        if new_count >= threshold:
            return {
                "domain": domain,
                "new_products": new_count,
                "categories": (rows[1] or "").split(",")[:5],
                "signal": "product_launch_surge",
                "days": days,
            }
        return None
    finally:
        conn.close()


def cross_store_comparison(domains: list[str], days: int = 30) -> dict:
    """Compare category overlap and pricing across stores."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        store_data = {}
        for domain in domains[:10]:
            rows = conn.execute(
                """SELECT product_type,
                          COUNT(DISTINCT product_id) as cnt,
                          AVG(price) as avg_p
                   FROM product_signals
                   WHERE domain = ? AND recorded_at >= ?
                         AND product_type != 'Other'
                   GROUP BY product_type
                   ORDER BY cnt DESC""",
                (domain, cutoff),
            ).fetchall()
            store_data[domain] = {
                r[0]: {"count": r[1], "avg_price": round(r[2], 2)}
                for r in rows
            }

        # Find overlapping categories
        all_cats = set()
        for data in store_data.values():
            all_cats.update(data.keys())

        overlap = []
        for cat in all_cats:
            stores_with = {
                d: data[cat] for d, data in store_data.items() if cat in data
            }
            if len(stores_with) >= 2:
                prices = [v["avg_price"] for v in stores_with.values()]
                overlap.append({
                    "category": cat,
                    "store_count": len(stores_with),
                    "avg_price_range": f"${min(prices):.0f}-${max(prices):.0f}",
                    "price_spread_pct": round(
                        ((max(prices) - min(prices)) / min(prices)) * 100, 1
                    ) if min(prices) > 0 else 0,
                    "stores": {d: v for d, v in stores_with.items()},
                })

        overlap.sort(key=lambda x: -x["store_count"])

        # Find unique categories (only in one store)
        unique = []
        for cat in all_cats:
            stores_with = [d for d, data in store_data.items() if cat in data]
            if len(stores_with) == 1:
                d = stores_with[0]
                unique.append({
                    "category": cat,
                    "store": d,
                    "count": store_data[d][cat]["count"],
                    "avg_price": store_data[d][cat]["avg_price"],
                })

        return {
            "stores_analyzed": len(store_data),
            "total_categories": len(all_cats),
            "overlapping": overlap[:15],
            "unique_niches": sorted(unique, key=lambda x: -x["count"])[:10],
        }
    finally:
        conn.close()


def get_vendor_landscape(days: int = 30) -> list[dict]:
    """Map vendor distribution across all tracked stores."""
    conn = _get_db()
    cutoff = time.time() - (days * 86400)
    try:
        rows = conn.execute(
            """SELECT vendor,
                      COUNT(DISTINCT domain) as store_count,
                      COUNT(DISTINCT product_id) as product_count,
                      AVG(price) as avg_price,
                      GROUP_CONCAT(DISTINCT product_type) as categories
               FROM product_signals
               WHERE recorded_at >= ? AND vendor != ''
               GROUP BY vendor
               ORDER BY product_count DESC
               LIMIT 30""",
            (cutoff,),
        ).fetchall()

        return [
            {
                "vendor": r[0],
                "store_count": r[1],
                "product_count": r[2],
                "avg_price": round(r[3], 2),
                "categories": (r[4] or "").split(",")[:5],
            }
            for r in rows
        ]
    finally:
        conn.close()


def generate_trend_report(days: int = 14) -> dict:
    """Generate a comprehensive trend report."""
    hot_cats = detect_hot_categories(days)
    top_tags = detect_trending_tags(days, top_n=15)
    vendors = get_vendor_landscape(days)

    return {
        "period_days": days,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "hot_categories": hot_cats[:10],
        "trending_tags": top_tags,
        "top_vendors": vendors[:10],
        "summary": {
            "total_hot_categories": len(hot_cats),
            "total_trending_tags": len(top_tags),
            "total_vendors": len(vendors),
        },
    }
