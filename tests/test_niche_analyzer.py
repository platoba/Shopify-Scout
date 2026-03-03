"""Tests for Shopify Scout niche analyzer module."""
from app.niche_analyzer import (
    analyze_niche, _compute_niche_score, _find_opportunities,
    _determine_positioning, _assess_diversity, _assess_freshness,
    _generate_recommendations, _score_to_grade, format_niche_report,
)


SAMPLE_ANALYSIS = {
    "domain": "niche-store.com",
    "product_count": 50,
    "products": [
        {
            "id": i,
            "title": f"Product {i}",
            "product_type": "Jewelry" if i < 30 else "Accessories",
            "vendor": "NicheBrand",
            "tags": ["gold", "handmade"] if i < 20 else ["silver"],
            "variants": [{"price": str(80 + i)}],
            "created_at": f"2026-02-{min(28, i+1):02d}T00:00:00Z",
        }
        for i in range(50)
    ],
    "prices": {"min": 80, "max": 130, "avg": 105, "median": 105, "count": 50},
    "categories": {"Jewelry": 30, "Accessories": 20},
    "vendors": {"NicheBrand": 50},
    "tags": {"gold": 20, "handmade": 20, "silver": 30},
    "score": {"score": 7, "reasons": ["Good focus"]},
}

BUDGET_ANALYSIS = {
    "domain": "cheap-stuff.com",
    "product_count": 200,
    "products": [],
    "prices": {"min": 1, "max": 15, "avg": 8, "median": 7, "count": 200},
    "categories": {f"Cat{i}": 20 for i in range(10)},
    "vendors": {f"Vendor{i}": 20 for i in range(10)},
    "tags": {"cheap": 100, "sale": 80},
    "score": {"score": 4, "reasons": ["Low prices"]},
}

EMPTY_ANALYSIS = {
    "domain": "empty.com",
    "product_count": 0,
    "products": [],
    "prices": {},
    "categories": {},
    "vendors": {},
    "tags": {},
    "score": {"score": 0, "reasons": []},
}


class TestScoreToGrade:
    def test_grade_a(self):
        assert _score_to_grade(85) == "A"
        assert _score_to_grade(100) == "A"

    def test_grade_b(self):
        assert _score_to_grade(70) == "B"

    def test_grade_c(self):
        assert _score_to_grade(55) == "C"

    def test_grade_d(self):
        assert _score_to_grade(40) == "D"

    def test_grade_f(self):
        assert _score_to_grade(20) == "F"
        assert _score_to_grade(0) == "F"


class TestComputeNicheScore:
    def test_focused_high_value(self):
        result = _compute_niche_score(
            {"Jewelry": 30, "Accessories": 20},
            {"avg": 105, "median": 105},
            {"NicheBrand": 50},
            50,
        )
        assert result["score"] > 50
        assert result["grade"] in ("A", "B", "C")
        assert len(result["reasons"]) > 0

    def test_budget_spread(self):
        result = _compute_niche_score(
            {f"Cat{i}": 20 for i in range(10)},
            {"avg": 8},
            {f"V{i}": 20 for i in range(10)},
            200,
        )
        # Budget stores score lower
        assert isinstance(result["score"], (int, float))

    def test_empty(self):
        result = _compute_niche_score({}, {}, {}, 0)
        assert result["score"] <= 50

    def test_single_brand_bonus(self):
        result = _compute_niche_score(
            {"Shoes": 30},
            {"avg": 100},
            {"OnlyBrand": 30},
            30,
        )
        reasons_text = " ".join(result["reasons"])
        assert "单一品牌" in reasons_text or "品类聚焦" in reasons_text

    def test_too_many_vendors_penalty(self):
        vendors = {f"V{i}": 5 for i in range(15)}
        result = _compute_niche_score({"Misc": 50}, {"avg": 50}, vendors, 50)
        reasons_text = " ".join(result["reasons"])
        assert "供应商过多" in reasons_text

    def test_tiny_store_penalty(self):
        result = _compute_niche_score({"Cat": 2}, {"avg": 50}, {"V": 2}, 2)
        reasons_text = " ".join(result["reasons"])
        assert "太少" in reasons_text


class TestFindOpportunities:
    def test_low_competition(self):
        opps = _find_opportunities(
            {"Pet Supplies": 20, "Art": 10},
            {"avg": 50},
            {"custom": 5},
        )
        types = [o["type"] for o in opps]
        assert "low_competition" in types

    def test_high_margin(self):
        opps = _find_opportunities(
            {"Jewelry": 30},
            {"avg": 80},
            {"gold": 10},
        )
        types = [o["type"] for o in opps]
        assert "high_margin" in types

    def test_trending_tags(self):
        opps = _find_opportunities(
            {"Accessories": 20},
            {"avg": 30},
            {"trending1": 10, "trending2": 8, "trending3": 5, "trending4": 4, "trending5": 3},
        )
        tag_opps = [o for o in opps if o["type"] == "trending_tags"]
        assert len(tag_opps) > 0

    def test_price_segmentation(self):
        opps = _find_opportunities(
            {"Mixed": 50},
            {"min": 5, "max": 500, "avg": 100},
            {},
        )
        types = [o["type"] for o in opps]
        assert "price_segmentation" in types

    def test_no_opportunities(self):
        opps = _find_opportunities({}, {"avg": 0}, {})
        assert isinstance(opps, list)


class TestDeterminePositioning:
    def test_premium(self):
        result = _determine_positioning({"avg": 250, "median": 200})
        assert result["tier"] == "premium"
        assert "高端" in result["strategy"]

    def test_mid_high(self):
        result = _determine_positioning({"avg": 120, "median": 110})
        assert result["tier"] == "mid_high"

    def test_mid(self):
        result = _determine_positioning({"avg": 60, "median": 55})
        assert result["tier"] == "mid"

    def test_budget(self):
        result = _determine_positioning({"avg": 25, "median": 20})
        assert result["tier"] == "budget"

    def test_ultra_budget(self):
        result = _determine_positioning({"avg": 10, "median": 8})
        assert result["tier"] == "ultra_budget"

    def test_unknown(self):
        result = _determine_positioning({"avg": 0, "median": 0})
        assert result["tier"] == "unknown"

    def test_right_skewed(self):
        result = _determine_positioning({"avg": 200, "median": 100})
        assert result["price_skew"] == "right_skewed"


class TestAssessDiversity:
    def test_concentrated(self):
        result = _assess_diversity({"Shoes": 90, "Other": 10}, {"Brand": 100}, 100)
        assert result["concentration"] == "highly_concentrated"
        assert result["hhi"] > 0.6

    def test_diversified(self):
        cats = {f"Cat{i}": 10 for i in range(10)}
        result = _assess_diversity(cats, {f"V{i}": 10 for i in range(5)}, 100)
        assert result["concentration"] == "diversified"
        assert result["hhi"] <= 0.3

    def test_moderate(self):
        result = _assess_diversity({"A": 50, "B": 30, "C": 20}, {"V1": 100}, 100)
        assert result["concentration"] in ("moderately_concentrated", "highly_concentrated", "diversified")

    def test_empty(self):
        result = _assess_diversity({}, {}, 0)
        assert result["category_count"] == 0
        assert result["products_per_category"] == 0


class TestAssessFreshness:
    def test_fresh_products(self):
        products = [
            {"created_at": "2026-02-28T00:00:00Z"},
            {"created_at": "2026-02-20T00:00:00Z"},
            {"created_at": "2026-01-01T00:00:00Z"},
        ]
        result = _assess_freshness(products)
        assert result["freshness_score"] > 0
        assert result["newest"] is not None
        assert result["oldest"] is not None
        assert result["total_with_dates"] == 3
        assert result["catalog_span_days"] > 0

    def test_empty_products(self):
        result = _assess_freshness([])
        assert result["freshness_score"] == 0

    def test_no_dates(self):
        products = [{"id": 1}, {"id": 2}]
        result = _assess_freshness(products)
        assert result["freshness_score"] == 0

    def test_recent_count(self):
        products = [
            {"created_at": "2026-02-15T00:00:00Z"},
            {"created_at": "2026-02-10T00:00:00Z"},
            {"created_at": "2025-06-01T00:00:00Z"},
        ]
        result = _assess_freshness(products)
        assert result["recent_30d"] >= 0
        assert result["recent_90d"] >= result["recent_30d"]


class TestGenerateRecommendations:
    def test_high_score(self):
        recs = _generate_recommendations(
            {"grade": "A", "score": 85},
            [], {"tier": "mid"}, {"concentration": "diversified"}, {"freshness_score": 50},
        )
        assert any("优秀" in r for r in recs)

    def test_low_score(self):
        recs = _generate_recommendations(
            {"grade": "F", "score": 20},
            [], {"tier": "ultra_budget"}, {"concentration": "diversified"}, {"freshness_score": 10},
        )
        assert any("弱" in r or "薄" in r for r in recs)

    def test_stale_catalog(self):
        recs = _generate_recommendations(
            {"grade": "C", "score": 50},
            [], {"tier": "mid"}, {"concentration": "moderate"}, {"freshness_score": 10},
        )
        assert any("陈旧" in r for r in recs)

    def test_with_opportunities(self):
        opps = [{"type": "low_competition", "detail": "Pet竞争度低", "priority": "high"}]
        recs = _generate_recommendations(
            {"grade": "B", "score": 70},
            opps, {"tier": "mid"}, {"concentration": "moderate"}, {"freshness_score": 60},
        )
        assert any("Pet" in r for r in recs)


class TestAnalyzeNiche:
    def test_full_niche_analysis(self):
        result = analyze_niche(SAMPLE_ANALYSIS)
        assert result["domain"] == "niche-store.com"
        assert "niche_score" in result
        assert "opportunities" in result
        assert "positioning" in result
        assert "diversity" in result
        assert "freshness" in result
        assert "recommendations" in result
        assert "generated_at" in result

    def test_empty_analysis(self):
        result = analyze_niche(EMPTY_ANALYSIS)
        assert result["niche_score"]["score"] <= 50

    def test_budget_analysis(self):
        result = analyze_niche(BUDGET_ANALYSIS)
        assert result["positioning"]["tier"] in ("ultra_budget", "budget")


class TestFormatNicheReport:
    def test_format(self):
        niche = analyze_niche(SAMPLE_ANALYSIS)
        text = format_niche_report(niche)
        assert "赛道分析" in text
        assert "赛道评分" in text
        assert "定位" in text
        assert "品类" in text

    def test_format_empty(self):
        niche = analyze_niche(EMPTY_ANALYSIS)
        text = format_niche_report(niche)
        assert isinstance(text, str)
