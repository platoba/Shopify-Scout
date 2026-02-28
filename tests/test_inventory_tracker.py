"""Tests for inventory_tracker module."""
import os
import time
import pytest


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_inv.db")
    monkeypatch.setattr("app.inventory_tracker.MONITOR_DB", db_path)
    monkeypatch.setattr("app.config.MONITOR_DB", db_path)
    return db_path


def _make_products(n=3, stock=50):
    products = []
    for i in range(n):
        products.append({
            "id": f"prod_{i}",
            "title": f"Product {i}",
            "variants": [
                {
                    "id": f"var_{i}_0",
                    "sku": f"SKU-{i}-A",
                    "price": str(29.99 + i * 10),
                    "inventory_quantity": stock - i * 10,
                    "inventory_policy": "deny",
                },
            ],
        })
    return products


class TestRecordInventory:
    def test_records_all(self):
        from app.inventory_tracker import record_inventory
        products = _make_products(3, stock=50)
        result = record_inventory("shop.com", products)
        assert result["recorded"] == 3
        assert result["events"] == []

    def test_detects_sold_event(self):
        from app.inventory_tracker import record_inventory
        products = _make_products(1, stock=50)
        record_inventory("shop.com", products)

        # Sell some units
        products[0]["variants"][0]["inventory_quantity"] = 45
        result = record_inventory("shop.com", products)
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "sold"
        assert result["events"][0]["delta"] == -5

    def test_detects_stockout(self):
        from app.inventory_tracker import record_inventory
        products = [{"id": "p1", "title": "W", "variants": [
            {"id": "v1", "inventory_quantity": 5}
        ]}]
        record_inventory("shop.com", products)

        products[0]["variants"][0]["inventory_quantity"] = 0
        result = record_inventory("shop.com", products)
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "stockout"

    def test_detects_restock(self):
        from app.inventory_tracker import record_inventory
        products = [{"id": "p1", "title": "W", "variants": [
            {"id": "v1", "inventory_quantity": 0}
        ]}]
        record_inventory("shop.com", products)

        products[0]["variants"][0]["inventory_quantity"] = 100
        result = record_inventory("shop.com", products)
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "restock"

    def test_no_event_same_stock(self):
        from app.inventory_tracker import record_inventory
        products = _make_products(1, stock=50)
        record_inventory("shop.com", products)
        result = record_inventory("shop.com", products)
        assert result["events"] == []

    def test_handles_available_flag(self):
        from app.inventory_tracker import record_inventory
        products = [{"id": "p1", "title": "W", "variants": [
            {"id": "v1", "available": True}
        ]}]
        result = record_inventory("shop.com", products)
        assert result["recorded"] == 1

    def test_handles_no_inventory(self):
        from app.inventory_tracker import record_inventory
        products = [{"id": "p1", "title": "W", "variants": [
            {"id": "v1", "price": "10"}
        ]}]
        result = record_inventory("shop.com", products)
        assert result["recorded"] == 1
        assert result["events"] == []


class TestGetAvailability:
    def test_from_quantity(self):
        from app.inventory_tracker import _get_availability
        assert _get_availability({"inventory_quantity": 42}) == 42

    def test_from_available_true(self):
        from app.inventory_tracker import _get_availability
        assert _get_availability({"available": True}) == 1

    def test_from_available_false(self):
        from app.inventory_tracker import _get_availability
        assert _get_availability({"available": False}) == 0

    def test_none_if_missing(self):
        from app.inventory_tracker import _get_availability
        assert _get_availability({"price": "10"}) is None

    def test_quantity_priority(self):
        from app.inventory_tracker import _get_availability
        # inventory_quantity takes priority
        assert _get_availability({"inventory_quantity": 5, "available": True}) == 5

    def test_invalid_quantity(self):
        from app.inventory_tracker import _get_availability
        assert _get_availability({"inventory_quantity": "abc"}) is None


class TestBestsellers:
    def test_finds_bestsellers(self):
        from app.inventory_tracker import record_inventory, get_bestsellers
        # Simulate sales over time
        for stock in [50, 40, 30, 20, 10]:
            products = [{"id": "p1", "title": "Hot Item", "variants": [
                {"id": "v1", "inventory_quantity": stock}
            ]}]
            record_inventory("shop.com", products)

        sellers = get_bestsellers("shop.com", days=30)
        assert len(sellers) >= 1
        assert sellers[0]["variant_id"] == "v1"
        assert sellers[0]["total_sold"] >= 10

    def test_velocity_labels(self):
        from app.inventory_tracker import _velocity_label
        assert "VIRAL" in _velocity_label(15)
        assert "HOT" in _velocity_label(7)
        assert "FAST" in _velocity_label(3)
        assert "STEADY" in _velocity_label(1)
        assert "SLOW" in _velocity_label(0.2)
        assert "DEAD" in _velocity_label(0.01)

    def test_empty_bestsellers(self):
        from app.inventory_tracker import get_bestsellers
        sellers = get_bestsellers("empty.com")
        assert sellers == []


class TestDeadStock:
    def test_finds_dead_stock(self):
        from app.inventory_tracker import record_inventory, get_dead_stock
        # Product with no sales
        products = [{"id": "p1", "title": "Nobody wants this", "variants": [
            {"id": "v1", "inventory_quantity": 100}
        ]}]
        record_inventory("shop.com", products)
        # Same stock level = no sales
        record_inventory("shop.com", products)

        dead = get_dead_stock("shop.com", days=30, min_days_stale=0)
        assert len(dead) >= 1

    def test_excludes_active(self):
        from app.inventory_tracker import record_inventory, get_dead_stock, _get_db
        import time as _time
        # v1 sells actively, v2 has no sales
        products = [
            {"id": "p1", "title": "Selling", "variants": [
                {"id": "v1", "inventory_quantity": 50}
            ]},
            {"id": "p2", "title": "Stale", "variants": [
                {"id": "v2", "inventory_quantity": 100}
            ]},
        ]
        record_inventory("shop.com", products)
        products[0]["variants"][0]["inventory_quantity"] = 45  # v1 sells
        record_inventory("shop.com", products)

        # Backdate the sold event to make it within stale window
        conn = _get_db()
        conn.execute(
            "UPDATE stock_events SET recorded_at = ? WHERE variant_id = 'v1'",
            (_time.time() - 1,)  # 1 second ago, within stale window
        )
        conn.commit()
        conn.close()

        # min_days_stale=1 → stale_cutoff = now - 1day, sold event is within window
        dead = get_dead_stock("shop.com", days=30, min_days_stale=1)
        dead_ids = [d["variant_id"] for d in dead]
        # v1 had a "sold" event within stale window → not dead
        assert "v1" not in dead_ids
        # v2 had no sales → dead
        assert "v2" in dead_ids


class TestStockoutFrequency:
    def test_counts_stockouts(self):
        from app.inventory_tracker import record_inventory, get_stockout_frequency
        for stock in [10, 0, 20, 0, 15, 0]:
            products = [{"id": "p1", "title": "Flaky", "variants": [
                {"id": "v1", "inventory_quantity": stock}
            ]}]
            record_inventory("shop.com", products)

        stockouts = get_stockout_frequency("shop.com", days=30)
        assert len(stockouts) >= 1
        assert stockouts[0]["stockout_count"] >= 2

    def test_empty_stockouts(self):
        from app.inventory_tracker import get_stockout_frequency
        assert get_stockout_frequency("empty.com") == []


class TestRestockPatterns:
    def test_finds_patterns(self):
        from app.inventory_tracker import record_inventory, get_restock_patterns
        for stock in [0, 50, 0, 50, 0, 50]:
            products = [{"id": "p1", "title": "Regular", "variants": [
                {"id": "v1", "inventory_quantity": stock}
            ]}]
            record_inventory("shop.com", products)

        patterns = get_restock_patterns("shop.com", days=30)
        assert len(patterns) >= 1
        assert patterns[0]["restock_count"] >= 2

    def test_empty_patterns(self):
        from app.inventory_tracker import get_restock_patterns
        assert get_restock_patterns("empty.com") == []


class TestInventorySummary:
    def test_summary(self):
        from app.inventory_tracker import record_inventory, inventory_summary
        # Create some activity
        for stock in [50, 40, 30, 0, 60]:
            products = [{"id": "p1", "title": "Active", "variants": [
                {"id": "v1", "inventory_quantity": stock}
            ]}]
            record_inventory("shop.com", products)

        summary = inventory_summary("shop.com", days=30)
        assert summary["domain"] == "shop.com"
        assert summary["tracked_variants"] >= 1
        assert "top_sellers" in summary
        assert "frequent_stockouts" in summary

    def test_empty_summary(self):
        from app.inventory_tracker import inventory_summary
        summary = inventory_summary("empty.com")
        assert summary["tracked_variants"] == 0
        assert summary["total_units_sold"] == 0
