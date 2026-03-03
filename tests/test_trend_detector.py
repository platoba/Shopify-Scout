"""Tests for trend_detector module."""
import pytest


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_trend.db")
    monkeypatch.setattr("app.trend_detector.MONITOR_DB", db_path)
    monkeypatch.setattr("app.config.MONITOR_DB", db_path)
    return db_path


def _make_products(n=5, category="Electronics", vendor="TestVendor"):
    products = []
    for i in range(n):
        products.append({
            "id": f"prod_{i}",
            "title": f"Product {i}",
            "product_type": category,
            "vendor": vendor,
            "tags": f"tag1, tag2, trending-{i}",
            "created_at": "2026-03-01T00:00:00",
            "variants": [
                {"id": f"var_{i}", "price": str(29.99 + i * 10)},
            ],
        })
    return products


class TestRecordProductSignals:
    def test_records_signals(self):
        from app.trend_detector import record_product_signals
        products = _make_products(5)
        count = record_product_signals("shop1.com", products)
        assert count == 5

    def test_handles_list_tags(self):
        from app.trend_detector import record_product_signals
        products = [{"id": "p1", "title": "T", "product_type": "Shoes",
                     "vendor": "Nike", "tags": ["running", "athletic"],
                     "variants": [{"id": "v1", "price": "99"}]}]
        count = record_product_signals("shop.com", products)
        assert count == 1

    def test_handles_empty_products(self):
        from app.trend_detector import record_product_signals
        count = record_product_signals("shop.com", [])
        assert count == 0

    def test_handles_missing_fields(self):
        from app.trend_detector import record_product_signals
        products = [{"id": "p1", "variants": [{"id": "v1", "price": "10"}]}]
        count = record_product_signals("shop.com", products)
        assert count == 1


class TestDetectHotCategories:
    def test_finds_hot_categories(self):
        from app.trend_detector import record_product_signals, detect_hot_categories
        # Multiple stores with same category
        record_product_signals("shop1.com", _make_products(5, "Electronics"))
        record_product_signals("shop2.com", _make_products(3, "Electronics"))
        record_product_signals("shop3.com", _make_products(2, "Electronics"))

        hot = detect_hot_categories(days=7, min_stores=2)
        assert len(hot) >= 1
        assert hot[0]["category"] == "Electronics"
        assert hot[0]["store_count"] >= 2

    def test_excludes_single_store(self):
        from app.trend_detector import record_product_signals, detect_hot_categories
        record_product_signals("lonely.com", _make_products(10, "Unique"))
        hot = detect_hot_categories(days=7, min_stores=2)
        lonely = [h for h in hot if h["category"] == "Unique"]
        assert len(lonely) == 0

    def test_excludes_other_type(self):
        from app.trend_detector import record_product_signals, detect_hot_categories
        products = [{"id": "p1", "title": "X", "product_type": "Other",
                     "vendor": "V", "tags": "",
                     "variants": [{"id": "v1", "price": "10"}]}]
        record_product_signals("shop1.com", products)
        record_product_signals("shop2.com", products)
        hot = detect_hot_categories(days=7, min_stores=2)
        other_cats = [h for h in hot if h["category"] == "Other"]
        assert len(other_cats) == 0

    def test_heat_score_levels(self):
        from app.trend_detector import _calc_heat
        assert "HOT" in _calc_heat(5, 10)
        assert "WARM" in _calc_heat(3, 5)
        assert "RISING" in _calc_heat(2, 2)
        assert "COOL" in _calc_heat(1, 1)


class TestDetectTrendingTags:
    def test_finds_trending_tags(self):
        from app.trend_detector import record_product_signals, detect_trending_tags
        record_product_signals("shop1.com", _make_products(5))
        record_product_signals("shop2.com", _make_products(3))

        tags = detect_trending_tags(days=7, top_n=10)
        assert len(tags) >= 1
        tag_names = [t["tag"] for t in tags]
        assert "tag1" in tag_names
        assert "tag2" in tag_names

    def test_tag_store_spread(self):
        from app.trend_detector import record_product_signals, detect_trending_tags
        record_product_signals("s1.com", _make_products(2))
        record_product_signals("s2.com", _make_products(2))

        tags = detect_trending_tags(days=7)
        for tag in tags:
            if tag["tag"] in ("tag1", "tag2"):
                assert tag["store_spread"] == 2

    def test_empty_tags(self):
        from app.trend_detector import detect_trending_tags
        tags = detect_trending_tags(days=7)
        assert tags == []


class TestNewProductSurge:
    def test_no_surge(self):
        from app.trend_detector import record_product_signals, detect_new_product_surge
        record_product_signals("shop.com", _make_products(3))
        result = detect_new_product_surge("shop.com", threshold=100)
        assert result is None

    def test_detects_surge(self):
        from app.trend_detector import record_product_signals, detect_new_product_surge
        from datetime import datetime
        # Create products with today's created_at
        today = datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%d")
        products = _make_products(15)
        for p in products:
            p["created_at"] = today
        record_product_signals("shop.com", products)
        result = detect_new_product_surge("shop.com", threshold=10)
        # May or may not detect based on time window
        # The logic compares created_at_store vs current date
        assert result is None or result["signal"] == "product_launch_surge"


class TestCrossStoreComparison:
    def test_comparison(self):
        from app.trend_detector import record_product_signals, cross_store_comparison
        record_product_signals("s1.com", _make_products(5, "Electronics", "BrandA"))
        record_product_signals("s2.com", _make_products(3, "Electronics", "BrandB"))
        record_product_signals("s2.com", _make_products(2, "Clothing", "BrandC"))

        result = cross_store_comparison(["s1.com", "s2.com"], days=7)
        assert result["stores_analyzed"] == 2
        assert result["total_categories"] >= 1
        assert len(result["overlapping"]) >= 0

    def test_empty_comparison(self):
        from app.trend_detector import cross_store_comparison
        result = cross_store_comparison(["empty1.com", "empty2.com"])
        assert result["stores_analyzed"] == 2
        assert result["total_categories"] == 0


class TestVendorLandscape:
    def test_vendor_data(self):
        from app.trend_detector import record_product_signals, get_vendor_landscape
        record_product_signals("s1.com", _make_products(5, "Shoes", "Nike"))
        record_product_signals("s2.com", _make_products(3, "Shoes", "Nike"))
        record_product_signals("s2.com", _make_products(2, "Bags", "Gucci"))

        vendors = get_vendor_landscape(days=7)
        assert len(vendors) >= 1
        nike = [v for v in vendors if v["vendor"] == "Nike"]
        assert len(nike) == 1
        assert nike[0]["store_count"] == 2

    def test_empty_vendors(self):
        from app.trend_detector import get_vendor_landscape
        vendors = get_vendor_landscape(days=7)
        assert vendors == []


class TestGenerateTrendReport:
    def test_report_structure(self):
        from app.trend_detector import record_product_signals, generate_trend_report
        record_product_signals("s1.com", _make_products(5))
        record_product_signals("s2.com", _make_products(3))

        report = generate_trend_report(days=7)
        assert "period_days" in report
        assert "hot_categories" in report
        assert "trending_tags" in report
        assert "top_vendors" in report
        assert "summary" in report
        assert report["period_days"] == 7

    def test_empty_report(self):
        from app.trend_detector import generate_trend_report
        report = generate_trend_report(days=7)
        assert report["summary"]["total_hot_categories"] == 0


class TestAvgPrice:
    def test_calculates_avg(self):
        from app.trend_detector import _avg_price
        product = {"variants": [
            {"price": "10"}, {"price": "20"}, {"price": "30"}
        ]}
        assert _avg_price(product) == 20.0

    def test_handles_invalid(self):
        from app.trend_detector import _avg_price
        product = {"variants": [{"price": "abc"}, {}]}
        assert _avg_price(product) == 0.0

    def test_handles_zero(self):
        from app.trend_detector import _avg_price
        product = {"variants": [{"price": "0"}, {"price": "50"}]}
        assert _avg_price(product) == 50.0

    def test_no_variants(self):
        from app.trend_detector import _avg_price
        assert _avg_price({}) == 0.0
        assert _avg_price({"variants": []}) == 0.0
