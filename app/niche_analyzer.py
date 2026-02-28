"""Niche scoring and opportunity analysis for Shopify stores."""
import math
from typing import Optional
from datetime import datetime, timezone


# Market saturation benchmarks by category
CATEGORY_BENCHMARKS = {
    "Electronics": {"avg_price": 150, "competition": "high", "margin": "low"},
    "Clothing": {"avg_price": 50, "competition": "high", "margin": "medium"},
    "Shoes": {"avg_price": 100, "competition": "high", "margin": "medium"},
    "Accessories": {"avg_price": 30, "competition": "medium", "margin": "high"},
    "Jewelry": {"avg_price": 80, "competition": "medium", "margin": "very_high"},
    "Home & Garden": {"avg_price": 60, "competition": "medium", "margin": "medium"},
    "Beauty": {"avg_price": 35, "competition": "high", "margin": "high"},
    "Health": {"avg_price": 40, "competition": "medium", "margin": "high"},
    "Sports": {"avg_price": 70, "competition": "medium", "margin": "medium"},
    "Toys": {"avg_price": 25, "competition": "medium", "margin": "medium"},
    "Pet Supplies": {"avg_price": 30, "competition": "low", "margin": "high"},
    "Food & Drink": {"avg_price": 20, "competition": "medium", "margin": "medium"},
    "Books": {"avg_price": 15, "competition": "low", "margin": "low"},
    "Art": {"avg_price": 100, "competition": "low", "margin": "very_high"},
    "Crafts": {"avg_price": 25, "competition": "low", "margin": "high"},
    "Automotive": {"avg_price": 80, "competition": "low", "margin": "medium"},
    "Baby": {"avg_price": 35, "competition": "medium", "margin": "medium"},
    "Outdoor": {"avg_price": 90, "competition": "medium", "margin": "medium"},
}

MARGIN_SCORES = {"very_high": 10, "high": 8, "medium": 5, "low": 3}
COMPETITION_SCORES = {"low": 10, "medium": 6, "high": 3}


def analyze_niche(analysis: dict) -> dict:
    """Analyze the niche positioning and opportunity of a store.

    Args:
        analysis: Full analysis result from analyzer.full_analysis().

    Returns:
        Niche report with scores, opportunities, and recommendations.
    """
    categories = analysis.get("categories", {})
    prices = analysis.get("prices", {})
    tags = analysis.get("tags", {})
    vendors = analysis.get("vendors", {})
    product_count = analysis.get("product_count", 0)
    products = analysis.get("products", [])

    niche_score = _compute_niche_score(categories, prices, vendors, product_count)
    opportunities = _find_opportunities(categories, prices, tags)
    positioning = _determine_positioning(prices)
    diversity = _assess_diversity(categories, vendors, product_count)
    freshness = _assess_freshness(products)
    recommendations = _generate_recommendations(
        niche_score, opportunities, positioning, diversity, freshness
    )

    return {
        "domain": analysis.get("domain", "unknown"),
        "niche_score": niche_score,
        "opportunities": opportunities,
        "positioning": positioning,
        "diversity": diversity,
        "freshness": freshness,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _compute_niche_score(
    categories: dict, prices: dict, vendors: dict, product_count: int
) -> dict:
    """Compute a niche attractiveness score (0-100)."""
    score = 50  # baseline
    reasons = []

    # Category analysis
    if categories:
        top_cat = max(categories, key=categories.get)
        benchmark = CATEGORY_BENCHMARKS.get(top_cat, {})

        if benchmark:
            margin_s = MARGIN_SCORES.get(benchmark.get("margin", "medium"), 5)
            comp_s = COMPETITION_SCORES.get(benchmark.get("competition", "medium"), 6)
            score += margin_s + comp_s - 10
            reasons.append(
                f"主品类 {top_cat}: 利润率{benchmark.get('margin','?')}, "
                f"竞争{benchmark.get('competition','?')}"
            )

        # Niche focus bonus (fewer categories = more focused)
        if len(categories) <= 3:
            score += 10
            reasons.append("品类聚焦 (≤3个品类)")
        elif len(categories) >= 10:
            score -= 5
            reasons.append("品类分散 (≥10个品类)")

    # Price positioning
    avg_price = prices.get("avg", 0)
    if avg_price >= 100:
        score += 8
        reasons.append(f"高客单价 (均价${avg_price:.0f})")
    elif avg_price >= 50:
        score += 4
        reasons.append(f"中等客单价 (均价${avg_price:.0f})")
    elif avg_price > 0:
        reasons.append(f"低客单价 (均价${avg_price:.0f})")

    # Product count sweet spot
    if 20 <= product_count <= 200:
        score += 5
        reasons.append(f"产品数量适中 ({product_count})")
    elif product_count > 500:
        score -= 3
        reasons.append(f"产品数量过多 ({product_count})")
    elif product_count < 5:
        score -= 10
        reasons.append(f"产品数量太少 ({product_count})")

    # Vendor diversity
    if len(vendors) == 1 and product_count > 5:
        score += 5
        reasons.append("单一品牌/自有品牌 (利润可控)")
    elif len(vendors) > 10:
        score -= 3
        reasons.append(f"供应商过多 ({len(vendors)}家)")

    score = max(0, min(100, score))
    grade = _score_to_grade(score)

    return {"score": score, "grade": grade, "reasons": reasons}


def _score_to_grade(score: int) -> str:
    if score >= 80:
        return "A"
    elif score >= 65:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 35:
        return "D"
    return "F"


def _find_opportunities(categories: dict, prices: dict, tags: dict) -> list[dict]:
    """Identify specific niche opportunities."""
    opps = []

    # Low competition categories
    for cat in categories:
        benchmark = CATEGORY_BENCHMARKS.get(cat, {})
        if benchmark.get("competition") == "low":
            opps.append({
                "type": "low_competition",
                "category": cat,
                "detail": f"{cat} 竞争度低，可以深耕",
                "priority": "high",
            })

    # High margin categories
    for cat in categories:
        benchmark = CATEGORY_BENCHMARKS.get(cat, {})
        if benchmark.get("margin") in ("very_high", "high"):
            opps.append({
                "type": "high_margin",
                "category": cat,
                "detail": f"{cat} 利润率{benchmark['margin']}",
                "priority": "high",
            })

    # Trending tags (high frequency)
    sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
    trend_tags = [t for t, c in sorted_tags[:5] if c >= 3]
    if trend_tags:
        opps.append({
            "type": "trending_tags",
            "tags": trend_tags,
            "detail": f"热门标签: {', '.join(trend_tags)}",
            "priority": "medium",
        })

    # Price gap opportunity
    p_min = prices.get("min", 0)
    p_max = prices.get("max", 0)
    if p_max > 0 and p_min > 0 and p_max / p_min > 5:
        opps.append({
            "type": "price_segmentation",
            "detail": f"价格跨度大(${p_min:.0f}-${p_max:.0f})，可做产品线分层",
            "priority": "medium",
        })

    return opps


def _determine_positioning(prices: dict) -> dict:
    """Determine price positioning strategy."""
    avg = prices.get("avg", 0)
    median = prices.get("median", 0)

    if avg == 0:
        return {"strategy": "unknown", "tier": "unknown"}

    if avg >= 200:
        tier = "premium"
        strategy = "高端定位，注重品牌和体验"
    elif avg >= 100:
        tier = "mid_high"
        strategy = "中高端，品质驱动"
    elif avg >= 50:
        tier = "mid"
        strategy = "中端，性价比导向"
    elif avg >= 20:
        tier = "budget"
        strategy = "低价走量，薄利多销"
    else:
        tier = "ultra_budget"
        strategy = "超低价，极致性价比"

    skew = "balanced"
    if avg > 0 and median > 0:
        ratio = avg / median
        if ratio > 1.5:
            skew = "right_skewed"  # few expensive items
        elif ratio < 0.75:
            skew = "left_skewed"  # few cheap items

    return {
        "tier": tier,
        "strategy": strategy,
        "avg_price": round(avg, 2),
        "median_price": round(median, 2),
        "price_skew": skew,
    }


def _assess_diversity(
    categories: dict, vendors: dict, product_count: int
) -> dict:
    """Assess product and vendor diversity."""
    cat_count = len(categories)
    vendor_count = len(vendors)

    # Category concentration (Herfindahl Index)
    total_products = sum(categories.values()) if categories else 1
    hhi = sum((c / total_products) ** 2 for c in categories.values()) if categories else 1

    if hhi > 0.6:
        concentration = "highly_concentrated"
    elif hhi > 0.3:
        concentration = "moderately_concentrated"
    else:
        concentration = "diversified"

    return {
        "category_count": cat_count,
        "vendor_count": vendor_count,
        "product_count": product_count,
        "hhi": round(hhi, 3),
        "concentration": concentration,
        "products_per_category": round(product_count / cat_count, 1) if cat_count else 0,
    }


def _assess_freshness(products: list) -> dict:
    """Assess how fresh/recent the product catalog is."""
    if not products:
        return {"freshness_score": 0, "newest": None, "oldest": None}

    now = datetime.now(timezone.utc)
    dates = []
    for p in products:
        created = p.get("created_at")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                dates.append(dt)
            except (ValueError, TypeError):
                pass

    if not dates:
        return {"freshness_score": 0, "newest": None, "oldest": None}

    dates.sort()
    newest = dates[-1]
    oldest = dates[0]
    days_since_newest = (now - newest).days
    days_span = (newest - oldest).days

    # Freshness: 100 if newest product added today, decays
    freshness = max(0, 100 - days_since_newest * 2)

    # Count recent products (last 30 days)
    recent_30d = sum(1 for d in dates if (now - d).days <= 30)
    recent_90d = sum(1 for d in dates if (now - d).days <= 90)

    return {
        "freshness_score": freshness,
        "newest": newest.isoformat(),
        "oldest": oldest.isoformat(),
        "catalog_span_days": days_span,
        "days_since_newest": days_since_newest,
        "recent_30d": recent_30d,
        "recent_90d": recent_90d,
        "total_with_dates": len(dates),
    }


def _generate_recommendations(
    niche_score: dict,
    opportunities: list,
    positioning: dict,
    diversity: dict,
    freshness: dict,
) -> list[str]:
    """Generate actionable recommendations based on analysis."""
    recs = []

    # Score-based
    grade = niche_score.get("grade", "C")
    if grade in ("A", "B"):
        recs.append("✅ 赛道选择优秀，建议深度垂直化运营")
    elif grade in ("D", "F"):
        recs.append("⚠️ 赛道竞争力较弱，考虑调整品类或定位")

    # Positioning-based
    tier = positioning.get("tier", "")
    if tier == "ultra_budget":
        recs.append("💡 超低价策略利润薄，考虑提升产品附加值")
    elif tier == "premium":
        recs.append("💎 高端定位需要强品牌背书和内容营销")

    # Diversity-based
    conc = diversity.get("concentration", "")
    if conc == "highly_concentrated":
        recs.append("🎯 品类高度集中，适合专家型定位但需防范风险")
    elif conc == "diversified":
        recs.append("🔀 品类分散，考虑聚焦核心品类提升转化率")

    # Freshness-based
    fs = freshness.get("freshness_score", 0)
    if fs < 30:
        recs.append("🕐 产品目录陈旧，建议增加新品提升活力")
    elif fs > 80:
        recs.append("🆕 产品更新频繁，保持这个节奏")

    # Opportunity-based
    high_opps = [o for o in opportunities if o.get("priority") == "high"]
    if high_opps:
        for o in high_opps[:2]:
            recs.append(f"🎯 {o['detail']}")

    return recs


def format_niche_report(niche_data: dict) -> str:
    """Format niche analysis as readable text."""
    lines = [f"🎯 **{niche_data.get('domain', '')} 赛道分析**\n"]

    # Score
    ns = niche_data.get("niche_score", {})
    lines.append(
        f"📊 **赛道评分**: {ns.get('score', 0)}/100 "
        f"(等级 {ns.get('grade', '?')})"
    )
    for r in ns.get("reasons", []):
        lines.append(f"  • {r}")
    lines.append("")

    # Positioning
    pos = niche_data.get("positioning", {})
    if pos.get("strategy"):
        lines.append(f"💰 **定位**: {pos['strategy']}")
        lines.append(f"   价格层级: {pos.get('tier', '?')}")
    lines.append("")

    # Diversity
    div = niche_data.get("diversity", {})
    lines.append(
        f"📦 **品类**: {div.get('category_count', 0)}个品类, "
        f"{div.get('vendor_count', 0)}个供应商"
    )
    lines.append(f"   集中度: {div.get('concentration', '?')} (HHI={div.get('hhi', 0)})")
    lines.append("")

    # Freshness
    fr = niche_data.get("freshness", {})
    if fr.get("freshness_score") is not None:
        lines.append(f"🆕 **新鲜度**: {fr['freshness_score']}/100")
        if fr.get("recent_30d"):
            lines.append(f"   近30天新品: {fr['recent_30d']}个")
    lines.append("")

    # Recommendations
    recs = niche_data.get("recommendations", [])
    if recs:
        lines.append("💡 **建议**")
        for r in recs:
            lines.append(f"  {r}")

    return "\n".join(lines)
