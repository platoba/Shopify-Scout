"""Tests for Shopify Scout analyzer module."""
import pytest
from app.analyzer import (
    analyze_prices, analyze_categories, analyze_tags,
    analyze_vendors, compute_store_score, full_analysis,
)

SAMPLE_PRODUCTS = [
    {
        "id": 1, "title": "Running Shoe A",
        "product_type": "Shoes", "vendor": "BrandA",
        "tags": ["running", "eco", "new"],
        "variants": [{"price": "99.00"}, {"price": "109.00"}],
        "created_at": "2025-12-01T00:00:00Z",
    },
    {
        "id": 2, "title": "Running Shoe B",
        "product_type": "Shoes", "vendor": "BrandA",
        "tags": ["running", "premium"],
        "variants": [{"price": "149.00"}],
        "created_at": "2025-11-15T00:00:00Z",
    },
    {
        "id": 3, "title": "T-Shirt",
        "product_type": "Apparel", "vendor": "BrandB",
        "tags": ["casual", "eco"],
        "variants": [{"price": "35.00"}],
        "created_at": "2025-10-01T00:00:00Z",
    },
    {
        "id": 4, "title": "Socks Pack",
        "product_type": "Accessories", "vendor": "BrandA",
        "tags": ["basics"],
        "variants": [{"price": "15.00"}],
        "created_at": "2025-09-01T00:00:00Z",
    },
]


class TestAnalyzePrices:
    def test_basic_stats(self):
        result = analyze_prices(SAMPLE_PRODUCTS)
        assert result["min"] == 15.0
        assert result["max"] == 149.0
        assert result["count"] == 5  # 2+1+1+1 variants
        assert 50 < result["avg"] < 100

    def test_empty_products(self):
        assert analyze_prices([]) == {}

    def test_zero_prices_excluded(self):
        products = [{"variants": [{"price": "0"}, {"price": "50.00"}]}]
        result = analyze_prices(products)
        assert result["count"] == 1
        assert result["min"] == 50.0


class TestAnalyzeCategories:
    def test_category_counts(self):
        result = analyze_categories(SAMPLE_PRODUCTS)
        assert result["Shoes"] == 2
        assert result["Apparel"] == 1
        assert result["Accessories"] == 1

    def test_empty(self):
        assert analyze_categories([]) == {}

    def test_missing_type(self):
        products = [{"product_type": None}, {"product_type": ""}]
        result = analyze_categories(products)
        assert result["Other"] == 2


class TestAnalyzeTags:
    def test_tag_frequency(self):
        result = analyze_tags(SAMPLE_PRODUCTS)
        assert result["running"] == 2
        assert result["eco"] == 2

    def test_empty(self):
        assert analyze_tags([]) == {}


class TestAnalyzeVendors:
    def test_vendor_counts(self):
        result = analyze_vendors(SAMPLE_PRODUCTS)
        assert result["BrandA"] == 3
        assert result["BrandB"] == 1


class TestComputeStoreScore:
    def test_medium_store(self):
        data = {"product_count": 50, "products": SAMPLE_PRODUCTS, "collections": []}
        result = compute_store_score(data)
        assert 1 <= result["score"] <= 10
        assert len(result["reasons"]) > 0

    def test_empty_store(self):
        data = {"product_count": 0, "products": [], "collections": []}
        result = compute_store_score(data)
        assert result["score"] < 5


class TestFullAnalysis:
    def test_returns_all_keys(self):
        data = {
            "domain": "test.com",
            "product_count": 4,
            "products": SAMPLE_PRODUCTS,
            "collections": [{"title": "All", "id": 1}],
        }
        result = full_analysis(data)
        assert "prices" in result
        assert "categories" in result
        assert "tags" in result
        assert "vendors" in result
        assert "trend" in result
        assert "score" in result
        assert result["domain"] == "test.com"
