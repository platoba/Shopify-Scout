"""Tests for app.pricing_intel module."""
import pytest
from app.pricing_intel import PricingIntel, PricePoint, analyze_pricing


# ── Fixtures ──────────────────────────────────────────────

def _variant(price, compare_at=0, title="Default", sku="", inventory=100):
    v = {"price": str(price), "title": title, "sku": sku, "inventory_quantity": inventory}
    if compare_at:
        v["compare_at_price"] = str(compare_at)
    return v


def _product(title="Test Product", product_type="Shoes", vendor="Nike",
             variants=None, pid=1):
    if variants is None:
        variants = [_variant(29.99)]
    return {
        "id": pid,
        "title": title,
        "product_type": product_type,
        "vendor": vendor,
        "variants": variants,
    }


def _shoe_store():
    return [
        _product("Running Shoe A", "Running Shoes", "Nike", [_variant(99.99)], 1),
        _product("Running Shoe B", "Running Shoes", "Adidas", [_variant(89.99)], 2),
        _product("Casual Sneaker", "Casual", "Puma", [_variant(69.99)], 3),
        _product("Boot Classic", "Boots", "Timberland", [_variant(149.99)], 4),
        _product("Sandal Summer", "Sandals", "Birkenstock", [_variant(49.99)], 5),
    ]


def _discount_store():
    return [
        _product("Sale Item 1", "T-Shirts", "Brand", [_variant(19.99, 39.99)], 10),
        _product("Sale Item 2", "Pants", "Brand", [_variant(29.99, 59.99)], 11),
        _product("Regular Item", "Hats", "Brand", [_variant(14.99)], 12),
        _product("Clearance", "Shoes", "Brand", [_variant(9.99, 49.99)], 13),
    ]


def _premium_store():
    return [
        _product("Luxury Watch", "Watches", "Rolex", [_variant(5999.99)], 20),
        _product("Designer Bag", "Bags", "LV", [_variant(2499.99)], 21),
        _product("Fine Jewelry", "Jewelry", "Tiffany", [_variant(1299.99)], 22),
    ]


def _charm_pricing_store():
    return [
        _product("Item A", variants=[_variant(9.99)], pid=30),
        _product("Item B", variants=[_variant(19.95)], pid=31),
        _product("Item C", variants=[_variant(29.99)], pid=32),
        _product("Item D", variants=[_variant(49.99)], pid=33),
        _product("Item E", variants=[_variant(14.95)], pid=34),
    ]


# ── PricePoint ────────────────────────────────────────────

class TestPricePoint:
    def test_basic_creation(self):
        pp = PricePoint("store", "Product", "M", 29.99)
        assert pp.store == "store"
        assert pp.price == 29.99
        assert pp.discount_pct == 0

    def test_discount_calc(self):
        pp = PricePoint("store", "Product", "M", 20.0, compare_at_price=40.0)
        assert pp.discount_pct == 50.0

    def test_no_discount_when_lower_compare(self):
        pp = PricePoint("store", "Product", "M", 40.0, compare_at_price=20.0)
        assert pp.discount_pct == 0

    def test_to_dict(self):
        pp = PricePoint("mystore", "Cool Shoe", "Large", 59.99, 79.99, "Shoes", "Nike", "SKU123")
        d = pp.to_dict()
        assert d["store"] == "mystore"
        assert d["price"] == 59.99
        assert d["compare_at_price"] == 79.99
        assert d["discount_pct"] == pytest.approx(25.0, abs=0.1)
        assert d["product_type"] == "Shoes"
        assert d["sku"] == "SKU123"


# ── Load Store ────────────────────────────────────────────

class TestLoadStore:
    def test_load_products(self):
        intel = PricingIntel()
        intel.load_store("test", _shoe_store())
        assert len(intel.price_points) == 5

    def test_skips_zero_price(self):
        intel = PricingIntel()
        intel.load_store("test", [_product(variants=[_variant(0)])])
        assert len(intel.price_points) == 0

    def test_skips_invalid_price(self):
        intel = PricingIntel()
        p = {"id": 1, "title": "Bad", "variants": [{"price": "invalid"}]}
        intel.load_store("test", [p])
        assert len(intel.price_points) == 0

    def test_multi_variant(self):
        intel = PricingIntel()
        p = _product(variants=[_variant(29.99, title="S"), _variant(39.99, title="L")])
        intel.load_store("test", [p])
        assert len(intel.price_points) == 2

    def test_compare_at_none(self):
        intel = PricingIntel()
        p = {"id": 1, "title": "T", "variants": [{"price": "20", "compare_at_price": None}]}
        intel.load_store("test", [p])
        assert intel.price_points[0].compare_at_price == 0


# ── Single Store Analysis ─────────────────────────────────

class TestAnalyzeStore:
    def test_basic_analysis(self):
        intel = PricingIntel()
        intel.load_store("shoes", _shoe_store())
        result = intel.analyze_store("shoes")
        assert result["store"] == "shoes"
        assert result["total_variants"] == 5
        assert "price_stats" in result
        assert "pricing_strategy" in result
        assert "discount_analysis" in result
        assert "price_tiers" in result
        assert "category_pricing" in result

    def test_price_stats(self):
        intel = PricingIntel()
        intel.load_store("shoes", _shoe_store())
        stats = intel.analyze_store("shoes")["price_stats"]
        assert stats["min"] == 49.99
        assert stats["max"] == 149.99
        assert stats["count"] == 5
        assert stats["mean"] > 0
        assert stats["median"] > 0

    def test_discount_analysis(self):
        intel = PricingIntel()
        intel.load_store("disc", _discount_store())
        disc = intel.analyze_store("disc")["discount_analysis"]
        assert disc["discounted_items"] == 3
        assert disc["discount_rate"] == 75.0
        assert disc["avg_discount"] > 0
        assert disc["max_discount"] > 0

    def test_no_discounts(self):
        intel = PricingIntel()
        intel.load_store("shoes", _shoe_store())
        disc = intel.analyze_store("shoes")["discount_analysis"]
        assert disc["discounted_items"] == 0
        assert disc["discount_rate"] == 0
        assert disc["avg_discount"] == 0

    def test_unknown_store(self):
        intel = PricingIntel()
        result = intel.analyze_store("nonexistent")
        assert "error" in result

    def test_category_pricing(self):
        intel = PricingIntel()
        intel.load_store("shoes", _shoe_store())
        cats = intel.analyze_store("shoes")["category_pricing"]
        assert "Running Shoes" in cats
        assert cats["Running Shoes"]["count"] == 2
        assert cats["Running Shoes"]["avg_price"] > 0


# ── Price Tiers ───────────────────────────────────────────

class TestPriceTiers:
    def test_tier_distribution(self):
        intel = PricingIntel()
        intel.load_store("shoes", _shoe_store())
        tiers = intel.analyze_store("shoes")["price_tiers"]
        assert "tiers" in tiers
        assert "dominant_tier" in tiers
        total_pct = sum(t["pct"] for t in tiers["tiers"].values())
        assert total_pct == pytest.approx(100, abs=0.5)

    def test_premium_tiers(self):
        intel = PricingIntel()
        intel.load_store("luxury", _premium_store())
        tiers = intel.analyze_store("luxury")["price_tiers"]
        assert tiers["dominant_tier"] == "luxury"
        assert tiers["tiers"]["luxury"]["count"] == 3

    def test_budget_tiers(self):
        intel = PricingIntel()
        intel.load_store("budget", [
            _product(variants=[_variant(5.99)], pid=1),
            _product(variants=[_variant(9.99)], pid=2),
            _product(variants=[_variant(15.99)], pid=3),
        ])
        tiers = intel.analyze_store("budget")["price_tiers"]
        assert tiers["dominant_tier"] == "budget"


# ── Strategy Detection ────────────────────────────────────

class TestStrategyDetection:
    def test_charm_pricing(self):
        intel = PricingIntel()
        intel.load_store("charm", _charm_pricing_store())
        strategy = intel.analyze_store("charm")["pricing_strategy"]
        assert strategy["charm_pricing_pct"] >= 80

    def test_discount_heavy(self):
        intel = PricingIntel()
        intel.load_store("disc", _discount_store())
        strategy = intel.analyze_store("disc")["pricing_strategy"]
        assert strategy["discount_heavy_pct"] >= 50

    def test_strategy_has_type(self):
        intel = PricingIntel()
        intel.load_store("test", _shoe_store())
        strategy = intel.analyze_store("test")["pricing_strategy"]
        assert "type" in strategy
        assert strategy["type"] in (
            "charm_pricing", "round_pricing", "discount_heavy",
            "uniform_pricing", "wide_range", "mixed",
        )


# ── Compare Stores ────────────────────────────────────────

class TestCompareStores:
    def test_compare_basic(self):
        intel = PricingIntel()
        intel.load_store("budget", [_product(variants=[_variant(9.99)], pid=1)])
        intel.load_store("premium", [_product(variants=[_variant(99.99)], pid=2)])
        result = intel.compare_stores()
        assert len(result["price_ranking"]) == 2
        # Budget should rank first (lowest median)
        assert result["price_ranking"][0]["store"] == "budget"
        assert result["price_ranking"][1]["store"] == "premium"

    def test_compare_needs_two(self):
        intel = PricingIntel()
        intel.load_store("only", _shoe_store())
        result = intel.compare_stores()
        assert "error" in result

    def test_compare_specific_stores(self):
        intel = PricingIntel()
        intel.load_store("a", _shoe_store())
        intel.load_store("b", _discount_store())
        intel.load_store("c", _premium_store())
        result = intel.compare_stores(["a", "b"])
        assert len(result["price_ranking"]) == 2

    def test_price_position(self):
        intel = PricingIntel()
        intel.load_store("cheap", [_product(variants=[_variant(5)], pid=1)])
        intel.load_store("mid", [_product(variants=[_variant(50)], pid=2)])
        intel.load_store("expensive", [_product(variants=[_variant(200)], pid=3)])
        result = intel.compare_stores()
        positions = {r["store"]: r["position"] for r in result["price_ranking"]}
        assert positions["cheap"] == "budget"
        assert positions["expensive"] == "premium"

    def test_category_gaps(self):
        intel = PricingIntel()
        intel.load_store("a", [_product(product_type="Shoes", pid=1)])
        intel.load_store("b", [_product(product_type="Hats", pid=2)])
        result = intel.compare_stores()
        gaps = result["category_gaps"]
        assert len(gaps) >= 1
        # Shoes missing from b, Hats missing from a
        gap_cats = {g["category"] for g in gaps}
        assert "Shoes" in gap_cats or "Hats" in gap_cats

    def test_opportunities(self):
        intel = PricingIntel()
        intel.load_store("a", _shoe_store())
        intel.load_store("b", _discount_store())
        result = intel.compare_stores()
        assert "opportunities" in result
        assert isinstance(result["opportunities"], list)

    def test_compare_result_structure(self):
        intel = PricingIntel()
        intel.load_store("a", _shoe_store())
        intel.load_store("b", _discount_store())
        result = intel.compare_stores()
        assert "stores" in result
        assert "price_ranking" in result
        assert "category_gaps" in result
        assert "opportunities" in result
        for r in result["price_ranking"]:
            assert "rank" in r
            assert "store" in r
            assert "median_price" in r
            assert "position" in r


# ── Similar Products ──────────────────────────────────────

class TestSimilarProducts:
    def test_finds_similar(self):
        intel = PricingIntel()
        intel.load_store("a", [_product(title="Nike Air Max 90", pid=1)])
        intel.load_store("b", [_product(title="Nike Air Max 90 Black", pid=2)])
        matches = intel.find_similar_products(threshold=0.7)
        assert len(matches) >= 1
        assert matches[0]["similarity"] >= 0.7

    def test_no_match_different(self):
        intel = PricingIntel()
        intel.load_store("a", [_product(title="Apple iPhone 15", pid=1)])
        intel.load_store("b", [_product(title="Samsung Galaxy S24", pid=2)])
        matches = intel.find_similar_products(threshold=0.8)
        assert len(matches) == 0

    def test_price_diff_calculated(self):
        intel = PricingIntel()
        intel.load_store("a", [_product(title="Same Product", variants=[_variant(50)], pid=1)])
        intel.load_store("b", [_product(title="Same Product", variants=[_variant(70)], pid=2)])
        matches = intel.find_similar_products(threshold=0.9)
        assert len(matches) >= 1
        assert matches[0]["price_diff"] == pytest.approx(20, abs=0.1)
        assert matches[0]["price_diff_pct"] == pytest.approx(40, abs=0.1)
        assert matches[0]["cheaper_store"] == "a"

    def test_max_20_results(self):
        intel = PricingIntel()
        for i in range(30):
            intel.load_store(f"store_{i}", [_product(title="Common Product", pid=i)])
        matches = intel.find_similar_products(threshold=0.9)
        assert len(matches) <= 20

    def test_sorted_by_price_diff(self):
        intel = PricingIntel()
        intel.load_store("a", [
            _product(title="Widget Alpha", variants=[_variant(10)], pid=1),
            _product(title="Gadget Beta", variants=[_variant(100)], pid=2),
        ])
        intel.load_store("b", [
            _product(title="Widget Alpha Pro", variants=[_variant(15)], pid=3),
            _product(title="Gadget Beta Plus", variants=[_variant(200)], pid=4),
        ])
        matches = intel.find_similar_products(threshold=0.6)
        if len(matches) >= 2:
            assert abs(matches[0]["price_diff_pct"]) >= abs(matches[1]["price_diff_pct"])


# ── Reset ─────────────────────────────────────────────────

class TestReset:
    def test_reset_clears(self):
        intel = PricingIntel()
        intel.load_store("test", _shoe_store())
        assert len(intel.price_points) > 0
        intel.reset()
        assert len(intel.price_points) == 0


# ── Convenience Function ──────────────────────────────────

class TestConvenience:
    def test_analyze_pricing(self):
        result = analyze_pricing("test", _shoe_store())
        assert result["store"] == "test"
        assert result["total_variants"] == 5
        assert "price_stats" in result
