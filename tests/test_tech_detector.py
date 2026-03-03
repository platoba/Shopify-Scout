"""Tests for Shopify Scout tech detector module."""
from app.tech_detector import (
    detect_theme, detect_apps, detect_payments,
    detect_currency, detect_locale, full_tech_scan,
    format_tech_report,
)


SAMPLE_HTML_DAWN = """
<html lang="en">
<head><title>Test Store</title></head>
<body>
<script>
Shopify.theme = {"name":"Dawn","theme_store_id":887,"role":"main"};
</script>
<script src="https://connect.facebook.net/en_US/fbevents.js"></script>
<script src="https://www.googletagmanager.com/gtag/js"></script>
<script src="https://static.klaviyo.com/onsite/js/klaviyo.js"></script>
<script>var _learnq = _learnq || [];</script>
<div class="shopify-payment-button">
<script src="https://js.stripe.com/v3/"></script>
<meta content="USD" name="currency">
"currency":"USD"
</div>
</body>
</html>
"""

SAMPLE_HTML_TURBO = """
<html lang="zh-CN">
<head><title>豪华店铺</title></head>
<body>
<script>
Shopify.theme = {"name":"Turbo Portland","theme_store_id":380};
</script>
<script src="https://loox.io/widget/loox.js"></script>
<script src="https://static.afterpay.com/button.js"></script>
<script>fbq('init', '123456');</script>
<script src="https://widget.intercom.io/widget/abc123"></script>
"currency":"EUR"
</body>
</html>
"""

MINIMAL_HTML = "<html><head></head><body>Hello</body></html>"
EMPTY_HTML = ""


class TestDetectTheme:
    def test_dawn_theme(self):
        result = detect_theme(SAMPLE_HTML_DAWN)
        assert result["theme_name"] == "Dawn"
        assert result["confidence"] == "high"
        assert result["theme_store_id"] == 887
        assert "Dawn" in result["theme_name_full"]

    def test_turbo_theme(self):
        result = detect_theme(SAMPLE_HTML_TURBO)
        assert "Turbo" in result["theme_name"]
        assert result["confidence"] == "high"
        assert result["theme_store_id"] == 380

    def test_unknown_theme(self):
        html = 'Shopify.theme = {"name":"CustomTheme123","theme_store_id":0};'
        result = detect_theme(html)
        assert result["theme_name"] == "CustomTheme123"
        assert result["theme_name_full"] is None

    def test_no_theme(self):
        result = detect_theme(MINIMAL_HTML)
        assert result["theme_name"] is None
        assert result["confidence"] == "none"

    def test_empty_html(self):
        result = detect_theme(EMPTY_HTML)
        assert result["theme_name"] is None

    def test_css_class_detection(self):
        html = '<div class="dawn-theme-wrapper">content</div>'
        result = detect_theme(html)
        assert result["theme_name"] == "dawn"
        assert result["confidence"] == "low"

    def test_theme_store_id_only(self):
        html = 'Shopify.theme = {"theme_store_id":999};'
        result = detect_theme(html)
        assert result["theme_store_id"] == 999
        assert result["confidence"] == "medium"


class TestDetectApps:
    def test_detect_klaviyo(self):
        apps = detect_apps(SAMPLE_HTML_DAWN)
        names = [a["name"] for a in apps]
        assert "Klaviyo" in names

    def test_detect_facebook_pixel(self):
        apps = detect_apps(SAMPLE_HTML_DAWN)
        names = [a["name"] for a in apps]
        assert "Facebook Pixel" in names

    def test_detect_google_analytics(self):
        apps = detect_apps(SAMPLE_HTML_DAWN)
        names = [a["name"] for a in apps]
        assert "Google Analytics/GTM" in names

    def test_detect_loox(self):
        apps = detect_apps(SAMPLE_HTML_TURBO)
        names = [a["name"] for a in apps]
        assert "Loox" in names

    def test_detect_intercom(self):
        apps = detect_apps(SAMPLE_HTML_TURBO)
        names = [a["name"] for a in apps]
        assert "Intercom" in names

    def test_no_apps(self):
        apps = detect_apps(MINIMAL_HTML)
        assert apps == []

    def test_empty_html(self):
        apps = detect_apps(EMPTY_HTML)
        assert apps == []

    def test_multiple_review_apps(self):
        html = '<script src="https://judge.me/widget.js"></script><script src="https://loox.io/w.js"></script>'
        apps = detect_apps(html)
        names = [a["name"] for a in apps]
        assert "Judge.me" in names
        assert "Loox" in names

    def test_app_categories(self):
        apps = detect_apps(SAMPLE_HTML_DAWN)
        categories = {a["category"] for a in apps}
        assert "Email Marketing" in categories
        assert "Analytics" in categories

    def test_yotpo_detection(self):
        html = '<script src="https://staticw2.yotpo.com/v1/widget.js"></script>'
        apps = detect_apps(html)
        assert any(a["name"] == "Yotpo" for a in apps)

    def test_tidio_detection(self):
        html = '<script src="//code.tidio.co/abc123.js"></script>'
        apps = detect_apps(html)
        assert any(a["name"] == "Tidio" for a in apps)

    def test_afterpay_detection(self):
        apps = detect_apps(SAMPLE_HTML_TURBO)
        names = [a["name"] for a in apps]
        assert "Afterpay" in names


class TestDetectPayments:
    def test_stripe(self):
        payments = detect_payments(SAMPLE_HTML_DAWN)
        assert "Stripe" in payments

    def test_shopify_payments(self):
        payments = detect_payments(SAMPLE_HTML_DAWN)
        assert "Shopify Payments" in payments

    def test_afterpay(self):
        payments = detect_payments(SAMPLE_HTML_TURBO)
        assert "Afterpay/Clearpay" in payments

    def test_no_payments(self):
        payments = detect_payments(MINIMAL_HTML)
        assert payments == []

    def test_empty_html(self):
        payments = detect_payments(EMPTY_HTML)
        assert payments == []

    def test_paypal(self):
        html = '<script src="https://www.paypal.com/sdk/js?client-id=abc"></script>'
        payments = detect_payments(html)
        assert "PayPal" in payments


class TestDetectCurrency:
    def test_usd(self):
        assert detect_currency(SAMPLE_HTML_DAWN) == "USD"

    def test_eur(self):
        assert detect_currency(SAMPLE_HTML_TURBO) == "EUR"

    def test_no_currency(self):
        assert detect_currency(MINIMAL_HTML) is None

    def test_empty_html(self):
        assert detect_currency(EMPTY_HTML) is None

    def test_gbp_symbol(self):
        html = '<span>£49.99</span>'
        assert detect_currency(html) == "GBP"

    def test_cad_meta(self):
        html = '"currency":"CAD"'
        assert detect_currency(html) == "CAD"


class TestDetectLocale:
    def test_english(self):
        assert detect_locale(SAMPLE_HTML_DAWN) == "en"

    def test_chinese(self):
        assert detect_locale(SAMPLE_HTML_TURBO) == "zh-CN"

    def test_no_locale(self):
        html = "<html><body>test</body></html>"
        assert detect_locale(html) is None

    def test_empty(self):
        assert detect_locale(EMPTY_HTML) is None


class TestFullTechScan:
    def test_dawn_full_scan(self):
        result = full_tech_scan(SAMPLE_HTML_DAWN)
        assert result["theme"]["theme_name"] == "Dawn"
        assert result["app_count"] >= 3
        assert "Email Marketing" in result["app_categories"]
        assert result["currency"] == "USD"
        assert result["locale"] == "en"

    def test_turbo_full_scan(self):
        result = full_tech_scan(SAMPLE_HTML_TURBO)
        assert "Turbo" in result["theme"]["theme_name"]
        assert result["app_count"] >= 3
        assert result["currency"] == "EUR"

    def test_empty_scan(self):
        result = full_tech_scan(EMPTY_HTML)
        assert result["app_count"] == 0
        assert result["currency"] is None

    def test_minimal_scan(self):
        result = full_tech_scan(MINIMAL_HTML)
        assert result["theme"]["confidence"] == "none"


class TestFormatTechReport:
    def test_format_with_apps(self):
        data = full_tech_scan(SAMPLE_HTML_DAWN)
        report = format_tech_report(data, "test.com")
        assert "test.com" in report
        assert "Dawn" in report
        assert "Klaviyo" in report

    def test_format_empty(self):
        data = full_tech_scan(EMPTY_HTML)
        report = format_tech_report(data)
        assert "未检测到" in report

    def test_format_no_domain(self):
        data = full_tech_scan(SAMPLE_HTML_DAWN)
        report = format_tech_report(data)
        assert "技术栈分析" in report
