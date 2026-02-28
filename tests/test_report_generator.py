"""Tests for report_generator module."""
import pytest


def _make_analysis(domain="test.myshopify.com"):
    return {
        "domain": domain,
        "product_count": 150,
        "prices": {
            "min": 9.99, "max": 299.99, "avg": 59.99,
            "median": 49.99, "p25": 24.99, "p75": 89.99, "count": 450,
        },
        "categories": {
            "Electronics": 45, "Clothing": 30, "Home": 25,
            "Sports": 20, "Beauty": 15, "Toys": 10, "Other": 5,
        },
        "tags": {
            "wireless": 30, "bluetooth": 25, "portable": 20,
            "usb-c": 18, "waterproof": 15, "led": 12,
            "organic": 10, "eco-friendly": 8,
        },
        "vendors": {
            "BrandA": 40, "BrandB": 35, "BrandC": 25,
            "BrandD": 20, "BrandE": 15, "NoName": 10,
        },
        "trend": {"recent_products": 12, "growth_rate": 8.5},
        "score": {"score": 78, "breakdown": {
            "Product Diversity": 8, "Pricing Strategy": 7,
            "Update Frequency": 9, "Brand Variety": 6,
        }},
    }


class TestGenerateHtmlReport:
    def test_produces_valid_html(self):
        from app.report_generator import generate_html_report
        html = generate_html_report(_make_analysis())
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "test.myshopify.com" in html

    def test_contains_all_sections(self):
        from app.report_generator import generate_html_report
        html = generate_html_report(_make_analysis())
        assert "Overview" in html
        assert "Price Distribution" in html
        assert "Categories" in html
        assert "Product Tags" in html
        assert "Vendors" in html
        assert "Growth Trend" in html
        assert "Store Score" in html

    def test_score_colors(self):
        from app.report_generator import generate_html_report
        # High score = green
        analysis = _make_analysis()
        analysis["score"]["score"] = 85
        html = generate_html_report(analysis)
        assert "var(--green)" in html

    def test_low_score_color(self):
        from app.report_generator import generate_html_report
        analysis = _make_analysis()
        analysis["score"]["score"] = 30
        html = generate_html_report(analysis)
        assert "var(--red)" in html

    def test_handles_empty_analysis(self):
        from app.report_generator import generate_html_report
        html = generate_html_report({"domain": "empty.com"})
        assert "empty.com" in html
        assert "</html>" in html

    def test_escapes_html(self):
        from app.report_generator import generate_html_report
        analysis = _make_analysis()
        analysis["domain"] = "<script>alert('xss')</script>"
        html = generate_html_report(analysis)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_empty_prices(self):
        from app.report_generator import generate_html_report
        analysis = {"domain": "test.com", "prices": {}}
        html = generate_html_report(analysis)
        assert "</html>" in html

    def test_empty_categories(self):
        from app.report_generator import generate_html_report
        analysis = {"domain": "test.com", "categories": {}}
        html = generate_html_report(analysis)
        assert "</html>" in html

    def test_empty_tags(self):
        from app.report_generator import generate_html_report
        analysis = {"domain": "test.com", "tags": {}}
        html = generate_html_report(analysis)
        assert "</html>" in html

    def test_version_in_footer(self):
        from app.report_generator import generate_html_report
        html = generate_html_report(_make_analysis())
        assert "v3.0.0" in html


class TestGenerateComparisonReport:
    def test_produces_html(self):
        from app.report_generator import generate_comparison_report
        stores = [_make_analysis("store1.com"), _make_analysis("store2.com")]
        html = generate_comparison_report(stores)
        assert "<!DOCTYPE html>" in html
        assert "store1.com" in html
        assert "store2.com" in html

    def test_comparison_table(self):
        from app.report_generator import generate_comparison_report
        stores = [_make_analysis("s1.com"), _make_analysis("s2.com")]
        html = generate_comparison_report(stores)
        assert "Comparison" in html
        assert "Products" in html

    def test_price_comparison(self):
        from app.report_generator import generate_comparison_report
        s1 = _make_analysis("cheap.com")
        s1["prices"]["avg"] = 19.99
        s2 = _make_analysis("premium.com")
        s2["prices"]["avg"] = 199.99
        html = generate_comparison_report([s1, s2])
        assert "Price Comparison" in html

    def test_category_overlap(self):
        from app.report_generator import generate_comparison_report
        stores = [_make_analysis("s1.com"), _make_analysis("s2.com")]
        html = generate_comparison_report(stores)
        assert "Category Overlap" in html
        assert "✅" in html

    def test_single_store_no_overlap(self):
        from app.report_generator import generate_comparison_report
        html = generate_comparison_report([_make_analysis()])
        assert "</html>" in html

    def test_empty_stores(self):
        from app.report_generator import generate_comparison_report
        html = generate_comparison_report([])
        assert "</html>" in html

    def test_handles_many_stores(self):
        from app.report_generator import generate_comparison_report
        stores = [_make_analysis(f"store{i}.com") for i in range(10)]
        html = generate_comparison_report(stores)
        # Should limit to 5
        assert "store4.com" in html


class TestGenerateTrendReportHtml:
    def test_produces_html(self):
        from app.report_generator import generate_trend_report_html
        data = {
            "period_days": 14,
            "hot_categories": [
                {"category": "Electronics", "store_count": 5,
                 "product_count": 50, "avg_price": 49.99,
                 "price_range": "$10-$200", "heat_score": "🔥🔥🔥 HOT"},
            ],
            "trending_tags": [
                {"tag": "wireless", "count": 30, "store_spread": 4, "stores": ["s1", "s2"]},
            ],
            "top_vendors": [
                {"vendor": "Nike", "store_count": 3, "product_count": 20,
                 "avg_price": 89.99, "categories": ["Shoes", "Clothing"]},
            ],
        }
        html = generate_trend_report_html(data)
        assert "Trend Report" in html
        assert "Hot Categories" in html
        assert "Electronics" in html
        assert "wireless" in html
        assert "Nike" in html

    def test_empty_trend_data(self):
        from app.report_generator import generate_trend_report_html
        html = generate_trend_report_html({"period_days": 7})
        assert "</html>" in html

    def test_badge_classes(self):
        from app.report_generator import generate_trend_report_html
        data = {
            "period_days": 7,
            "hot_categories": [
                {"category": "Hot", "store_count": 5, "product_count": 50,
                 "avg_price": 50, "price_range": "$10-$100",
                 "heat_score": "🔥🔥🔥 HOT"},
                {"category": "Warm", "store_count": 3, "product_count": 20,
                 "avg_price": 30, "price_range": "$5-$80",
                 "heat_score": "🔥🔥 WARM"},
            ],
            "trending_tags": [],
            "top_vendors": [],
        }
        html = generate_trend_report_html(data)
        assert "badge-hot" in html
        assert "badge-warm" in html


class TestHelperFunctions:
    def test_wrap_html_has_css(self):
        from app.report_generator import _wrap_html
        html = _wrap_html("Test", "<p>Hello</p>")
        assert "<style>" in html
        assert "--bg:" in html
        assert "--accent:" in html

    def test_overview_with_all_fields(self):
        from app.report_generator import _overview_card
        card = _overview_card(_make_analysis())
        assert "150" in card
        assert "$60" in card or "$59" in card

    def test_price_distribution_bars(self):
        from app.report_generator import _price_distribution
        prices = {"min": 10, "max": 200, "p25": 30, "median": 60, "p75": 120}
        html = _price_distribution(prices)
        assert "Budget" in html
        assert "Premium" in html

    def test_footer_content(self):
        from app.report_generator import _footer
        footer = _footer("test")
        assert "Shopify Scout" in footer
        assert "C-Line" in footer

    def test_comparison_table_with_nested_keys(self):
        from app.report_generator import _comparison_table
        stores = [
            {"domain": "s1.com", "product_count": 100,
             "prices": {"avg": 50}, "categories": {"A": 1}, "score": {"score": 80}},
            {"domain": "s2.com", "product_count": 200,
             "prices": {"avg": 30}, "categories": {"B": 1, "C": 1}, "score": {"score": 60}},
        ]
        html = _comparison_table(stores)
        assert "100" in html
        assert "200" in html
