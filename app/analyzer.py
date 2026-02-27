"""Store data analysis: pricing, categories, trends, scoring."""
from typing import Optional
from datetime import datetime


def analyze_prices(products: list) -> dict:
    """Analyze price distribution across all product variants."""
    prices = []
    for p in products:
        for v in p.get("variants", []):
            try:
                price = float(v.get("price", 0))
                if price > 0:
                    prices.append(price)
            except (ValueError, TypeError):
                pass

    if not prices:
        return {}

    prices.sort()
    n = len(prices)
    return {
        "min": prices[0],
        "max": prices[-1],
        "avg": sum(prices) / n,
        "median": prices[n // 2],
        "count": n,
        "p25": prices[n // 4] if n >= 4 else prices[0],
        "p75": prices[3 * n // 4] if n >= 4 else prices[-1],
    }


def analyze_categories(products: list) -> dict:
    """Count products per product_type."""
    types = {}
    for p in products:
        pt = p.get("product_type", "Other") or "Other"
        types[pt] = types.get(pt, 0) + 1
    return dict(sorted(types.items(), key=lambda x: -x[1]))


def analyze_tags(products: list) -> dict:
    """Count tag frequency across all products."""
    tags = {}
    for p in products:
        for t in p.get("tags", []):
            if isinstance(t, str) and t.strip():
                tag = t.strip().lower()
                tags[tag] = tags.get(tag, 0) + 1
    return dict(sorted(tags.items(), key=lambda x: -x[1]))


def analyze_vendors(products: list) -> dict:
    """Count products per vendor."""
    vendors = {}
    for p in products:
        v = p.get("vendor", "Unknown") or "Unknown"
        vendors[v] = vendors.get(v, 0) + 1
    return dict(sorted(vendors.items(), key=lambda x: -x[1]))


def analyze_creation_trend(products: list) -> dict:
    """Analyze product creation dates to detect launch frequency."""
    dates = []
    for p in products:
        created = p.get("created_at", "")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                dates.append(dt)
            except (ValueError, TypeError):
                pass

    if not dates:
        return {}

    dates.sort(reverse=True)
    now = datetime.now(dates[0].tzinfo) if dates[0].tzinfo else datetime.now()

    last_7d = sum(1 for d in dates if (now - d).days <= 7)
    last_30d = sum(1 for d in dates if (now - d).days <= 30)
    last_90d = sum(1 for d in dates if (now - d).days <= 90)

    return {
        "newest": dates[0].isoformat(),
        "oldest": dates[-1].isoformat(),
        "last_7d": last_7d,
        "last_30d": last_30d,
        "last_90d": last_90d,
        "avg_per_month": round(len(dates) / max(1, (now - dates[-1]).days / 30), 1),
    }


def compute_store_score(store_data: dict) -> dict:
    """Compute a 1-10 competitiveness score for a store."""
    score = 5.0
    reasons = []

    pc = store_data.get("product_count", 0)
    if pc >= 200:
        score += 1.5
        reasons.append(f"大型店铺({pc}产品)")
    elif pc >= 50:
        score += 0.5
        reasons.append(f"中型店铺({pc}产品)")
    elif pc < 10:
        score -= 1
        reasons.append(f"产品过少({pc})")

    prices = analyze_prices(store_data.get("products", []))
    if prices:
        if prices["avg"] > 100:
            score += 0.5
            reasons.append(f"高客单价(${prices['avg']:.0f})")
        spread = prices["max"] - prices["min"]
        if spread > 200:
            score += 0.5
            reasons.append("价格带宽广")

    categories = analyze_categories(store_data.get("products", []))
    if len(categories) >= 5:
        score += 0.5
        reasons.append(f"品类丰富({len(categories)}类)")

    trend = analyze_creation_trend(store_data.get("products", []))
    if trend.get("last_30d", 0) >= 5:
        score += 1
        reasons.append(f"活跃上新(30天{trend['last_30d']}款)")
    elif trend.get("last_90d", 0) == 0:
        score -= 1
        reasons.append("90天无上新")

    collections = store_data.get("collections", [])
    if len(collections) >= 5:
        score += 0.5
        reasons.append(f"集合完善({len(collections)}个)")

    score = max(1, min(10, round(score, 1)))
    return {"score": score, "reasons": reasons}


def full_analysis(store_data: dict) -> dict:
    """Run all analyses on store data."""
    products = store_data.get("products", [])
    return {
        "domain": store_data.get("domain", ""),
        "product_count": store_data.get("product_count", 0),
        "prices": analyze_prices(products),
        "categories": analyze_categories(products),
        "tags": analyze_tags(products),
        "vendors": analyze_vendors(products),
        "trend": analyze_creation_trend(products),
        "collections": store_data.get("collections", []),
        "score": compute_store_score(store_data),
    }
