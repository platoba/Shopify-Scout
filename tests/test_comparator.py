"""Tests for Shopify Scout comparator module."""
import pytest
from app.comparator import (
    compare_stores, _store_summary, _rank_stores,
    _compare_prices, _compute_category_overlap, _find_gaps,
    format_comparison_text,
)


STORE_A = {
    "domain": "store-a.com",
    "product_count": 50,
    "prices": {"min": 10, "max": 200, "avg": 75.5, "median": 60, "count": 50},
    "categories": {"Shoes": 30, "Apparel": 15, "Accessories": 5},
    "vendors": {"BrandA": 40, "BrandB": 10},
    "tags": {"running": 20, "eco": 10},
    "score": {"score": 7, "reasons": ["Good diversity"]},
}

STORE_B = {
    "domain": "store-b.com",
    "product_count": 30,
    "prices": {"min": 50, "max": 500, "avg": 180.0, "median": 150, "count": 30},
    "categories": {"Jewelry": 20, "Accessories": 10},
    "vendors": {"LuxBrand": 30},
    "tags": {"gold": 15, "silver": 10},
    "score": {"score": 8, "reasons": ["High value niche"]},
}

STORE_C = {
    "domain": "store-c.com",
    "product_count": 100,
    "prices": {"min": 5, "max": 50, "avg": 15.0, "median": 12, "count": 100},
    "categories": {"Toys": 50, "Crafts": 30, "Books": 20},
    "vendors": {"CheapVendor": 80, "Other": 20},
    "tags": {"kids": 40, "fun": 30},
    "score": {"score": 5, "reasons": ["Low price point"]},
}


class TestStoreSummary:
    def test_basic_summary(self):
        s = _store_summary(STORE_A)
        assert s["domain"] == "store-a.com"
        assert s["product_count"] == 50
        assert s["price_avg"] == 75.5
        assert s["category_count"] == 3
        assert s["vendor_count"] == 2
        assert s["top_category"] == "Shoes"
        assert s["store_score"] == 7

    def test_empty_categories(self):
        data = {**STORE_A, "categories": {}}
        s = _store_summary(data)
        assert s["category_count"] == 0
        assert s["top_category"] is None

    def test_empty_prices(self):
        data = {**STORE_A, "prices": {}}
        s = _store_summary(data)
        assert s["price_avg"] == 0
        assert s["price_min"] == 0


class TestRankStores:
    def test_ranking_order(self):
        summaries = [_store_summary(STORE_A), _store_summary(STORE_B)]
        ranked = _rank_stores(summaries)
        assert len(ranked) == 2
        assert ranked[0]["rank"] == 1
        assert ranked[1]["rank"] == 2
        # Store B has higher score
        assert ranked[0]["composite_score"] >= ranked[1]["composite_score"]

    def test_single_store(self):
        summaries = [_store_summary(STORE_A)]
        ranked = _rank_stores(summaries)
        assert len(ranked) == 1
        assert ranked[0]["rank"] == 1

    def test_three_stores(self):
        summaries = [_store_summary(s) for s in [STORE_A, STORE_B, STORE_C]]
        ranked = _rank_stores(summaries)
        assert len(ranked) == 3
        ranks = [r["rank"] for r in ranked]
        assert sorted(ranks) == [1, 2, 3]


class TestComparePrices:
    def test_basic_comparison(self):
        result = _compare_prices([STORE_A, STORE_B])
        assert "store-a.com" in result["by_store"]
        assert "store-b.com" in result["by_store"]
        assert result["cheapest"] == "store-a.com"
        assert result["most_expensive"] == "store-b.com"

    def test_widest_range(self):
        result = _compare_prices([STORE_A, STORE_B])
        assert result["widest_range"] is not None

    def test_empty_prices(self):
        empty = {**STORE_A, "prices": {}}
        result = _compare_prices([empty])
        assert result["cheapest"] is None

    def test_three_stores(self):
        result = _compare_prices([STORE_A, STORE_B, STORE_C])
        assert result["cheapest"] == "store-c.com"
        assert result["most_expensive"] == "store-b.com"


class TestCategoryOverlap:
    def test_partial_overlap(self):
        result = _compute_category_overlap([STORE_A, STORE_B])
        assert "Accessories" in result["shared"]
        assert "Shoes" in result["unique_by_store"]["store-a.com"]
        assert "Jewelry" in result["unique_by_store"]["store-b.com"]

    def test_no_overlap(self):
        no_overlap = {**STORE_B, "categories": {"Watches": 10}}
        result = _compute_category_overlap([STORE_A, no_overlap])
        assert result["shared"] == []
        assert result["overlap_ratio"] == 0

    def test_full_overlap(self):
        same_cats = {**STORE_B, "categories": STORE_A["categories"].copy()}
        result = _compute_category_overlap([STORE_A, same_cats])
        assert result["overlap_ratio"] == 1.0

    def test_single_store(self):
        result = _compute_category_overlap([STORE_A])
        assert result["shared"] == []

    def test_three_stores(self):
        result = _compute_category_overlap([STORE_A, STORE_B, STORE_C])
        assert isinstance(result["all_categories"], list)


class TestFindGaps:
    def test_unique_category_gap(self):
        gaps = _find_gaps([STORE_A, STORE_B])
        cat_gaps = [g for g in gaps if g["type"] == "unique_category"]
        categories = [g["category"] for g in cat_gaps]
        assert "Shoes" in categories or "Jewelry" in categories

    def test_price_gap(self):
        gaps = _find_gaps([STORE_A, STORE_B])
        price_gaps = [g for g in gaps if g["type"] == "price_gap"]
        assert len(price_gaps) > 0
        assert price_gaps[0]["spread"] > 50

    def test_single_vendor(self):
        single_vendor = {
            **STORE_B,
            "product_count": 20,
            "vendors": {"OnlyVendor": 20},
        }
        gaps = _find_gaps([STORE_A, single_vendor])
        vendor_gaps = [g for g in gaps if g["type"] == "single_vendor"]
        assert len(vendor_gaps) > 0

    def test_no_gaps(self):
        similar = {
            **STORE_A,
            "domain": "similar.com",
            "vendors": {"A": 10, "B": 10},
        }
        gaps = _find_gaps([STORE_A, similar])
        assert isinstance(gaps, list)


class TestCompareStores:
    def test_empty_input(self):
        result = compare_stores([])
        assert "error" in result

    def test_single_store(self):
        result = compare_stores([STORE_A])
        assert len(result["stores"]) == 1

    def test_two_stores(self):
        result = compare_stores([STORE_A, STORE_B])
        assert len(result["stores"]) == 2
        assert "ranking" in result
        assert "price_comparison" in result
        assert "category_overlap" in result
        assert "gap_analysis" in result
        assert "generated_at" in result

    def test_three_stores(self):
        result = compare_stores([STORE_A, STORE_B, STORE_C])
        assert len(result["stores"]) == 3
        assert len(result["ranking"]) == 3


class TestFormatComparisonText:
    def test_format_output(self):
        comparison = compare_stores([STORE_A, STORE_B])
        text = format_comparison_text(comparison)
        assert "店铺对比报告" in text
        assert "综合排名" in text
        assert "store-a.com" in text
        assert "store-b.com" in text

    def test_format_with_gaps(self):
        comparison = compare_stores([STORE_A, STORE_B, STORE_C])
        text = format_comparison_text(comparison)
        assert "市场机会" in text or "品类重叠" in text

    def test_format_empty(self):
        comparison = compare_stores([STORE_A])
        text = format_comparison_text(comparison)
        assert isinstance(text, str)
