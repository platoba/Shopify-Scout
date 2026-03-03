"""Tests for Shopify Scout exporter module."""
import os
import json
from app.exporter import (
    export_json, export_csv, export_html, export_report,
    export_comparison_csv, _build_price_ranges,
)


SAMPLE_ANALYSIS = {
    "domain": "test-store.com",
    "product_count": 4,
    "products": [
        {
            "id": 1, "title": "Shoe A",
            "product_type": "Shoes", "vendor": "BrandA",
            "tags": ["running", "eco"],
            "variants": [{"price": "99.00"}, {"price": "109.00"}],
            "created_at": "2025-12-01T00:00:00Z",
        },
        {
            "id": 2, "title": "Shirt B",
            "product_type": "Apparel", "vendor": "BrandB",
            "tags": ["casual"],
            "variants": [{"price": "35.00"}],
            "created_at": "2025-11-01T00:00:00Z",
        },
        {
            "id": 3, "title": "Hat C",
            "product_type": "Accessories", "vendor": "BrandA",
            "tags": ["basics"],
            "variants": [{"price": "15.00"}],
            "created_at": "2025-10-01T00:00:00Z",
        },
        {
            "id": 4, "title": "Watch D",
            "product_type": "Jewelry", "vendor": "LuxBrand",
            "tags": ["gold", "premium"],
            "variants": [{"price": "299.00"}],
            "created_at": "2025-09-01T00:00:00Z",
        },
    ],
    "prices": {"min": 15, "max": 299, "avg": 111.4, "median": 99, "count": 5, "p25": 35, "p75": 109},
    "categories": {"Shoes": 1, "Apparel": 1, "Accessories": 1, "Jewelry": 1},
    "vendors": {"BrandA": 2, "BrandB": 1, "LuxBrand": 1},
    "tags": {"running": 1, "eco": 1, "casual": 1, "basics": 1, "gold": 1, "premium": 1},
    "score": {"score": 6, "reasons": ["Good diversity", "Mixed pricing"]},
    "trend": {"new_30d": 0, "new_90d": 1},
}


class TestExportJSON:
    def test_basic_export(self):
        result = export_json(SAMPLE_ANALYSIS)
        parsed = json.loads(result)
        assert parsed["domain"] == "test-store.com"
        assert parsed["product_count"] == 4

    def test_export_to_file(self, tmp_path):
        filepath = str(tmp_path / "test.json")
        export_json(SAMPLE_ANALYSIS, filepath)
        assert os.path.exists(filepath)
        with open(filepath) as f:
            parsed = json.load(f)
        assert parsed["domain"] == "test-store.com"

    def test_unicode_handling(self):
        data = {"name": "测试店铺", "tags": ["中文标签"]}
        result = export_json(data)
        assert "测试店铺" in result

    def test_empty_data(self):
        result = export_json({})
        assert result == "{}"

    def test_creates_directory(self, tmp_path):
        filepath = str(tmp_path / "sub" / "dir" / "test.json")
        export_json({"a": 1}, filepath)
        assert os.path.exists(filepath)


class TestExportCSV:
    def test_basic_export(self):
        result = export_csv(SAMPLE_ANALYSIS)
        lines = result.strip().split("\n")
        assert len(lines) == 5  # header + 4 products
        assert "id,title" in lines[0]

    def test_export_to_file(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        export_csv(SAMPLE_ANALYSIS, filepath)
        assert os.path.exists(filepath)

    def test_price_extraction(self):
        result = export_csv(SAMPLE_ANALYSIS)
        lines = result.strip().split("\n")
        # Shoe A has 2 variants: 99 and 109
        assert "99.0" in lines[1]

    def test_empty_products(self):
        result = export_csv({"products": []})
        assert result == ""

    def test_no_products_key(self):
        result = export_csv({})
        assert result == ""

    def test_zero_price_excluded(self):
        data = {
            "products": [
                {
                    "id": 1, "title": "Test",
                    "product_type": "", "vendor": "",
                    "tags": [],
                    "variants": [{"price": "0"}, {"price": "50.00"}],
                    "created_at": "",
                }
            ]
        }
        result = export_csv(data)
        assert "50.0" in result

    def test_tags_formatting(self):
        data = {
            "products": [
                {
                    "id": 1, "title": "Test",
                    "product_type": "", "vendor": "",
                    "tags": ["tag1", "tag2", "tag3"],
                    "variants": [{"price": "10.00"}],
                    "created_at": "",
                }
            ]
        }
        result = export_csv(data)
        assert "tag1" in result


class TestExportHTML:
    def test_basic_export(self):
        result = export_html(SAMPLE_ANALYSIS)
        assert "<!DOCTYPE html>" in result
        assert "test-store.com" in result
        assert "Shopify Scout" in result

    def test_contains_price_info(self):
        html = export_html(SAMPLE_ANALYSIS)
        assert "$15.00" in html or "15" in html
        assert "$299.00" in html or "299" in html

    def test_contains_categories(self):
        html = export_html(SAMPLE_ANALYSIS)
        assert "Shoes" in html
        assert "Jewelry" in html

    def test_contains_vendors(self):
        html = export_html(SAMPLE_ANALYSIS)
        assert "BrandA" in html

    def test_contains_tags(self):
        html = export_html(SAMPLE_ANALYSIS)
        assert "running" in html

    def test_export_to_file(self, tmp_path):
        filepath = str(tmp_path / "report.html")
        export_html(SAMPLE_ANALYSIS, filepath)
        assert os.path.exists(filepath)
        with open(filepath) as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content

    def test_empty_analysis(self):
        result = export_html({
            "domain": "empty.com", "product_count": 0,
            "products": [], "prices": {}, "categories": {},
            "vendors": {}, "tags": {}, "score": {}, "trend": {},
        })
        assert "empty.com" in result

    def test_score_display(self):
        html = export_html(SAMPLE_ANALYSIS)
        assert "6" in html  # score

    def test_responsive_meta(self):
        html = export_html(SAMPLE_ANALYSIS)
        assert "viewport" in html


class TestBuildPriceRanges:
    def test_basic_ranges(self):
        products = SAMPLE_ANALYSIS["products"]
        ranges = _build_price_ranges(products)
        assert isinstance(ranges, dict)
        total = sum(ranges.values())
        assert total == 5  # 5 total variants with price > 0

    def test_empty(self):
        assert _build_price_ranges([]) == {}

    def test_all_ranges(self):
        products = [
            {"variants": [{"price": "5"}]},     # $0-10
            {"variants": [{"price": "20"}]},     # $10-25
            {"variants": [{"price": "40"}]},     # $25-50
            {"variants": [{"price": "75"}]},     # $50-100
            {"variants": [{"price": "150"}]},    # $100-200
            {"variants": [{"price": "300"}]},    # $200+
        ]
        ranges = _build_price_ranges(products)
        assert len(ranges) == 6

    def test_zero_excluded(self):
        products = [{"variants": [{"price": "0"}, {"price": "50"}]}]
        ranges = _build_price_ranges(products)
        total = sum(ranges.values())
        assert total == 1


class TestExportComparisonCSV:
    def test_basic_export(self):
        comparison = {
            "ranking": [
                {"rank": 1, "domain": "a.com", "composite_score": 80, "product_count": 50, "store_score": 8},
                {"rank": 2, "domain": "b.com", "composite_score": 60, "product_count": 30, "store_score": 6},
            ]
        }
        result = export_comparison_csv(comparison)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2

    def test_empty_ranking(self):
        result = export_comparison_csv({"ranking": []})
        assert result == ""

    def test_to_file(self, tmp_path):
        comparison = {
            "ranking": [
                {"rank": 1, "domain": "a.com", "composite_score": 80, "product_count": 50, "store_score": 8},
            ]
        }
        filepath = str(tmp_path / "comp.csv")
        export_comparison_csv(comparison, filepath)
        assert os.path.exists(filepath)


class TestExportReport:
    def test_json_dispatch(self):
        result = export_report(SAMPLE_ANALYSIS, fmt="json")
        parsed = json.loads(result)
        assert parsed["domain"] == "test-store.com"

    def test_csv_dispatch(self):
        result = export_report(SAMPLE_ANALYSIS, fmt="csv")
        assert "id,title" in result

    def test_html_dispatch(self):
        result = export_report(SAMPLE_ANALYSIS, fmt="html")
        assert "<!DOCTYPE html>" in result

    def test_default_json(self):
        result = export_report(SAMPLE_ANALYSIS, fmt="unknown")
        parsed = json.loads(result)
        assert "domain" in parsed

    def test_with_filepath(self, tmp_path):
        filepath = str(tmp_path / "out.json")
        export_report(SAMPLE_ANALYSIS, fmt="json", filepath=filepath)
        assert os.path.exists(filepath)
