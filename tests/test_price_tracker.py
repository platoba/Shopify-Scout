"""Tests for price_tracker module."""
import time
import pytest


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_price.db")
    monkeypatch.setattr("app.price_tracker.MONITOR_DB", db_path)
    monkeypatch.setattr("app.config.MONITOR_DB", db_path)
    return db_path


def _make_products(n=3, base_price=29.99):
    products = []
    for i in range(n):
        products.append({
            "id": f"prod_{i}",
            "title": f"Product {i}",
            "variants": [
                {
                    "id": f"var_{i}_0",
                    "price": str(base_price + i * 10),
                    "compare_at_price": str(base_price + i * 10 + 20) if i % 2 == 0 else None,
                },
                {
                    "id": f"var_{i}_1",
                    "price": str(base_price + i * 10 + 5),
                },
            ],
        })
    return products


class TestRecordPrices:
    def test_records_all_variants(self):
        from app.price_tracker import record_prices
        products = _make_products(3)
        result = record_prices("test.myshopify.com", products)
        assert result["recorded"] == 6
        assert result["alerts"] == []

    def test_skips_zero_price(self):
        from app.price_tracker import record_prices
        products = [{"id": "p1", "title": "Free", "variants": [
            {"id": "v1", "price": "0"},
            {"id": "v2", "price": "-5"},
        ]}]
        result = record_prices("test.com", products)
        assert result["recorded"] == 0

    def test_skips_invalid_price(self):
        from app.price_tracker import record_prices
        products = [{"id": "p1", "title": "Bad", "variants": [
            {"id": "v1", "price": "abc"},
            {"id": "v2"},
        ]}]
        result = record_prices("test.com", products)
        assert result["recorded"] == 0

    def test_detects_price_drop(self):
        from app.price_tracker import record_prices
        # First recording
        products = [{"id": "p1", "title": "Widget", "variants": [
            {"id": "v1", "price": "100.00"},
        ]}]
        record_prices("shop.com", products)

        # Price drops 15%
        products[0]["variants"][0]["price"] = "85.00"
        result = record_prices("shop.com", products)
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["type"] == "price_drop"
        assert result["alerts"][0]["old_price"] == 100.0
        assert result["alerts"][0]["new_price"] == 85.0

    def test_detects_price_spike(self):
        from app.price_tracker import record_prices
        products = [{"id": "p1", "title": "Widget", "variants": [
            {"id": "v1", "price": "50.00"},
        ]}]
        record_prices("shop.com", products)

        # Price increases 25%
        products[0]["variants"][0]["price"] = "62.50"
        result = record_prices("shop.com", products)
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["type"] == "price_spike"

    def test_no_alert_for_small_change(self):
        from app.price_tracker import record_prices
        products = [{"id": "p1", "title": "Widget", "variants": [
            {"id": "v1", "price": "100.00"},
        ]}]
        record_prices("shop.com", products)

        # Only 5% change - no alert
        products[0]["variants"][0]["price"] = "95.00"
        result = record_prices("shop.com", products)
        assert len(result["alerts"]) == 0

    def test_records_compare_at_price(self):
        from app.price_tracker import record_prices, get_price_history
        products = [{"id": "p1", "title": "Sale", "variants": [
            {"id": "v1", "price": "39.99", "compare_at_price": "59.99"},
        ]}]
        record_prices("shop.com", products)
        history = get_price_history("shop.com", "v1", days=1)
        assert len(history) == 1
        assert history[0]["price"] == 39.99
        assert history[0]["compare_at_price"] == 59.99

    def test_multiple_domains_isolated(self):
        from app.price_tracker import record_prices
        p1 = [{"id": "p1", "title": "A", "variants": [{"id": "v1", "price": "10"}]}]
        p2 = [{"id": "p1", "title": "B", "variants": [{"id": "v1", "price": "20"}]}]
        record_prices("shop1.com", p1)
        record_prices("shop2.com", p2)
        # No cross-domain alerts
        p1[0]["variants"][0]["price"] = "8"
        result = record_prices("shop1.com", p1)
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["domain"] == "shop1.com"


class TestGetPriceHistory:
    def test_returns_history(self):
        from app.price_tracker import record_prices, get_price_history
        products = [{"id": "p1", "title": "W", "variants": [
            {"id": "v1", "price": "50"},
        ]}]
        record_prices("shop.com", products)
        history = get_price_history("shop.com", "v1", days=1)
        assert len(history) == 1
        assert history[0]["price"] == 50.0
        assert "date" in history[0]

    def test_empty_history(self):
        from app.price_tracker import get_price_history
        history = get_price_history("nonexistent.com", "v999", days=30)
        assert history == []

    def test_respects_days_filter(self):
        from app.price_tracker import record_prices, get_price_history, _get_db
        products = [{"id": "p1", "title": "W", "variants": [
            {"id": "v1", "price": "50"},
        ]}]
        record_prices("shop.com", products)
        # Insert old record
        conn = _get_db()
        old_time = time.time() - 100 * 86400
        conn.execute(
            """INSERT INTO price_history (domain, product_id, variant_id, title, price, currency, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("shop.com", "p1", "v1", "W", 40.0, "USD", old_time)
        )
        conn.commit()
        conn.close()
        # 30-day filter should exclude old record
        history = get_price_history("shop.com", "v1", days=30)
        assert len(history) == 1
        assert history[0]["price"] == 50.0


class TestGetPriceSummary:
    def test_summary_with_data(self):
        from app.price_tracker import record_prices, get_price_summary, _get_db
        products = _make_products(2, base_price=20)
        record_prices("shop.com", products)
        # Add second data point with different prices
        conn = _get_db()
        now = time.time()
        for i in range(2):
            for j in range(2):
                vid = f"var_{i}_{j}"
                conn.execute(
                    """INSERT INTO price_history (domain, product_id, variant_id, title, price, currency, recorded_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ("shop.com", f"prod_{i}", vid, f"Product {i}", 25 + i * 10 + j * 5, "USD", now + 1)
                )
        conn.commit()
        conn.close()

        summary = get_price_summary("shop.com", days=30)
        assert summary["domain"] == "shop.com"
        assert summary["tracked_variants"] > 0

    def test_empty_summary(self):
        from app.price_tracker import get_price_summary
        summary = get_price_summary("empty.com")
        assert summary["tracked_variants"] == 0


class TestPendingAlerts:
    def test_get_and_mark_alerts(self):
        from app.price_tracker import record_prices, get_pending_alerts, mark_alerts_notified
        products = [{"id": "p1", "title": "W", "variants": [
            {"id": "v1", "price": "100"},
        ]}]
        record_prices("shop.com", products)
        products[0]["variants"][0]["price"] = "80"
        record_prices("shop.com", products)

        alerts = get_pending_alerts()
        assert len(alerts) == 1
        assert alerts[0]["type"] == "price_drop"

        # Mark as notified
        count = mark_alerts_notified([alerts[0]["id"]])
        assert count == 1

        # Should be empty now
        alerts2 = get_pending_alerts()
        assert len(alerts2) == 0

    def test_empty_mark(self):
        from app.price_tracker import mark_alerts_notified
        assert mark_alerts_notified([]) == 0


class TestDiscountPatterns:
    def test_finds_patterns(self):
        from app.price_tracker import detect_discount_patterns, _get_db
        # Insert discount records
        conn = _get_db()
        now = time.time()
        for day in range(5):
            conn.execute(
                """INSERT INTO price_history
                   (domain, product_id, variant_id, title, price,
                    compare_at_price, currency, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("shop.com", "p1", "v1", "Sale Item", 29.99, 49.99, "USD",
                 now - day * 86400),
            )
        conn.commit()
        conn.close()

        patterns = detect_discount_patterns("shop.com", days=30)
        assert len(patterns) >= 1
        assert patterns[0]["variant_id"] == "v1"
        assert patterns[0]["discount_count"] >= 2

    def test_no_patterns(self):
        from app.price_tracker import detect_discount_patterns
        patterns = detect_discount_patterns("empty.com")
        assert patterns == []


class TestBestBuyTiming:
    def test_strong_buy_at_low(self):
        from app.price_tracker import get_best_buy_timing, _get_db
        conn = _get_db()
        now = time.time()
        # Create price history: high → low
        prices = [100, 95, 90, 85, 50]
        for i, p in enumerate(prices):
            conn.execute(
                """INSERT INTO price_history
                   (domain, product_id, variant_id, title, price, currency, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("shop.com", "p1", "v1", "Widget", p, "USD", now - (len(prices)-i) * 86400),
            )
        conn.commit()
        conn.close()

        result = get_best_buy_timing("shop.com", "v1", days=30)
        assert result["recommendation"] in ("strong_buy", "buy")
        assert result["current_price"] == 50
        assert result["trend"] == "falling"

    def test_insufficient_data(self):
        from app.price_tracker import get_best_buy_timing
        result = get_best_buy_timing("empty.com", "v999")
        assert result["recommendation"] == "insufficient_data"

    def test_wait_at_high(self):
        from app.price_tracker import get_best_buy_timing, _get_db
        conn = _get_db()
        now = time.time()
        prices = [50, 55, 60, 65, 100]
        for i, p in enumerate(prices):
            conn.execute(
                """INSERT INTO price_history
                   (domain, product_id, variant_id, title, price, currency, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("shop.com", "p1", "v2", "Expensive", p, "USD", now - (len(prices)-i) * 86400),
            )
        conn.commit()
        conn.close()

        result = get_best_buy_timing("shop.com", "v2", days=30)
        assert result["recommendation"] in ("wait", "hold")
        assert result["trend"] == "rising"


class TestCleanup:
    def test_cleanup_old_records(self):
        from app.price_tracker import record_prices, cleanup_old_records, _get_db
        products = [{"id": "p1", "title": "W", "variants": [
            {"id": "v1", "price": "50"},
        ]}]
        record_prices("shop.com", products)

        # Insert old record
        conn = _get_db()
        old_time = time.time() - 200 * 86400
        conn.execute(
            """INSERT INTO price_history (domain, product_id, variant_id, title, price, currency, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("shop.com", "p1", "v_old", "Old", 10, "USD", old_time)
        )
        conn.commit()
        conn.close()

        deleted = cleanup_old_records(days=90)
        assert deleted >= 1


class TestCurrencyHandling:
    def test_records_currency(self):
        from app.price_tracker import record_prices, get_price_history
        products = [{"id": "p1", "title": "Euro", "variants": [
            {"id": "v1", "price": "29.99"},
        ]}]
        record_prices("eu-shop.com", products, currency="EUR")
        history = get_price_history("eu-shop.com", "v1")
        assert history[0]["currency"] == "EUR"

    def test_default_usd(self):
        from app.price_tracker import record_prices, get_price_history
        products = [{"id": "p1", "title": "US", "variants": [
            {"id": "v1", "price": "19.99"},
        ]}]
        record_prices("us-shop.com", products)
        history = get_price_history("us-shop.com", "v1")
        assert history[0]["currency"] == "USD"
