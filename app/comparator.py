"""Multi-store comparison engine for competitive analysis."""
from datetime import datetime, timezone


def compare_stores(analyses: list[dict]) -> dict:
    """Compare multiple analyzed store data side by side.

    Args:
        analyses: List of full_analysis results from analyzer.

    Returns:
        Comparison dict with rankings, gaps, and recommendations.
    """
    if not analyses:
        return {"error": "No stores to compare", "stores": []}

    if len(analyses) == 1:
        summary = _store_summary(analyses[0])
        return {
            "stores": [summary],
            "ranking": _rank_stores([summary]),
            "comparison": {},
        }

    summaries = [_store_summary(a) for a in analyses]
    ranking = _rank_stores(summaries)
    price_comparison = _compare_prices(analyses)
    category_overlap = _compute_category_overlap(analyses)
    gap_analysis = _find_gaps(analyses)

    return {
        "stores": summaries,
        "ranking": ranking,
        "price_comparison": price_comparison,
        "category_overlap": category_overlap,
        "gap_analysis": gap_analysis,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _store_summary(analysis: dict) -> dict:
    """Extract key metrics from a store analysis."""
    prices = analysis.get("prices", {})
    score = analysis.get("score", {})
    categories = analysis.get("categories", {})
    vendors = analysis.get("vendors", {})

    return {
        "domain": analysis.get("domain", "unknown"),
        "product_count": analysis.get("product_count", 0),
        "price_min": prices.get("min", 0),
        "price_max": prices.get("max", 0),
        "price_avg": round(prices.get("avg", 0), 2),
        "price_median": round(prices.get("median", 0), 2),
        "category_count": len(categories),
        "vendor_count": len(vendors),
        "top_category": max(categories, key=categories.get) if categories else None,
        "store_score": score.get("score", 0),
        "score_reasons": score.get("reasons", []),
    }


def _rank_stores(summaries: list[dict]) -> list[dict]:
    """Rank stores by composite score."""
    scored = []
    for s in summaries:
        composite = 0
        # Product diversity (0-30)
        pc = min(s["product_count"] / 100, 1.0) * 15
        cc = min(s["category_count"] / 10, 1.0) * 15
        composite += pc + cc
        # Price positioning (0-20)
        if s["price_avg"] > 0:
            price_score = min(s["price_avg"] / 200, 1.0) * 20
            composite += price_score
        # Store score (0-50)
        composite += s["store_score"] * 5
        scored.append({
            "domain": s["domain"],
            "composite_score": round(composite, 1),
            "product_count": s["product_count"],
            "store_score": s["store_score"],
        })

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, s in enumerate(scored):
        s["rank"] = i + 1
    return scored


def _compare_prices(analyses: list[dict]) -> dict:
    """Compare pricing strategies across stores."""
    result = {
        "by_store": {},
        "cheapest": None,
        "most_expensive": None,
        "widest_range": None,
    }

    min_avg = float("inf")
    max_avg = 0
    widest = 0

    for a in analyses:
        domain = a.get("domain", "unknown")
        prices = a.get("prices", {})
        if not prices:
            continue

        avg = prices.get("avg", 0)
        p_min = prices.get("min", 0)
        p_max = prices.get("max", 0)
        p_range = p_max - p_min

        result["by_store"][domain] = {
            "min": p_min,
            "max": p_max,
            "avg": round(avg, 2),
            "median": round(prices.get("median", 0), 2),
            "range": round(p_range, 2),
        }

        if avg < min_avg and avg > 0:
            min_avg = avg
            result["cheapest"] = domain
        if avg > max_avg:
            max_avg = avg
            result["most_expensive"] = domain
        if p_range > widest:
            widest = p_range
            result["widest_range"] = domain

    return result


def _compute_category_overlap(analyses: list[dict]) -> dict:
    """Find shared and unique categories across stores."""
    store_cats = {}
    for a in analyses:
        domain = a.get("domain", "unknown")
        cats = set(a.get("categories", {}).keys())
        store_cats[domain] = cats

    domains = list(store_cats.keys())
    if len(domains) < 2:
        return {"shared": [], "unique_by_store": {}}

    all_cats = set()
    for cats in store_cats.values():
        all_cats.update(cats)

    shared = set.intersection(*store_cats.values()) if store_cats.values() else set()
    unique_by_store = {}
    for domain, cats in store_cats.items():
        others = set()
        for d, c in store_cats.items():
            if d != domain:
                others.update(c)
        unique_by_store[domain] = sorted(cats - others)

    return {
        "all_categories": sorted(all_cats),
        "shared": sorted(shared),
        "unique_by_store": unique_by_store,
        "overlap_ratio": round(len(shared) / len(all_cats), 2) if all_cats else 0,
    }


def _find_gaps(analyses: list[dict]) -> list[dict]:
    """Identify market gaps and opportunities from comparison."""
    gaps = []

    # Find categories that only 1 store has (low competition)
    cat_counts = {}
    for a in analyses:
        for cat in a.get("categories", {}):
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

    for cat, count in cat_counts.items():
        if count == 1 and cat != "Other":
            domain = next(
                a["domain"] for a in analyses if cat in a.get("categories", {})
            )
            gaps.append({
                "type": "unique_category",
                "category": cat,
                "store": domain,
                "insight": f"Only {domain} sells {cat} - potential niche opportunity",
            })

    # Find price gaps (large spread in average prices)
    avgs = [(a.get("domain"), a.get("prices", {}).get("avg", 0)) for a in analyses]
    avgs = [(d, p) for d, p in avgs if p > 0]
    if len(avgs) >= 2:
        avgs.sort(key=lambda x: x[1])
        spread = avgs[-1][1] - avgs[0][1]
        if spread > 50:
            gaps.append({
                "type": "price_gap",
                "low": {"store": avgs[0][0], "avg_price": round(avgs[0][1], 2)},
                "high": {"store": avgs[-1][0], "avg_price": round(avgs[-1][1], 2)},
                "spread": round(spread, 2),
                "insight": f"${spread:.0f} price gap between cheapest and most expensive",
            })

    # Find underserved vendor diversity
    for a in analyses:
        vendors = a.get("vendors", {})
        if len(vendors) == 1 and a.get("product_count", 0) > 10:
            gaps.append({
                "type": "single_vendor",
                "store": a["domain"],
                "vendor": list(vendors.keys())[0],
                "insight": f"{a['domain']} relies on a single vendor - supply risk",
            })

    return gaps


def format_comparison_text(comparison: dict) -> str:
    """Format comparison result as readable text for Telegram."""
    lines = ["🔍 **店铺对比报告**\n"]

    # Rankings
    ranking = comparison.get("ranking", [])
    if ranking:
        lines.append("📊 **综合排名**")
        for r in ranking:
            medal = ["🥇", "🥈", "🥉"][r["rank"] - 1] if r["rank"] <= 3 else f"#{r['rank']}"
            lines.append(
                f"  {medal} {r['domain']} — 综合分 {r['composite_score']}"
                f" (产品{r['product_count']}个, 店铺评分{r['store_score']})"
            )
        lines.append("")

    # Price comparison
    pc = comparison.get("price_comparison", {})
    if pc.get("by_store"):
        lines.append("💰 **价格对比**")
        for domain, prices in pc["by_store"].items():
            lines.append(
                f"  • {domain}: ${prices['min']:.0f}-${prices['max']:.0f}"
                f" (均价${prices['avg']:.0f})"
            )
        if pc.get("cheapest"):
            lines.append(f"  📉 最便宜: {pc['cheapest']}")
        if pc.get("most_expensive"):
            lines.append(f"  📈 最贵: {pc['most_expensive']}")
        lines.append("")

    # Category overlap
    co = comparison.get("category_overlap", {})
    if co.get("shared"):
        lines.append(f"🏷️ **品类重叠** (重叠率 {co['overlap_ratio']:.0%})")
        lines.append(f"  共有品类: {', '.join(co['shared'][:10])}")
        for domain, uniq in co.get("unique_by_store", {}).items():
            if uniq:
                lines.append(f"  {domain} 独有: {', '.join(uniq[:5])}")
        lines.append("")

    # Gap analysis
    gaps = comparison.get("gap_analysis", [])
    if gaps:
        lines.append("🎯 **市场机会**")
        for g in gaps[:5]:
            lines.append(f"  • {g['insight']}")

    return "\n".join(lines)
