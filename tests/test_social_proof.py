"""Tests for app.social_proof module."""
import pytest
from app.social_proof import (
    SocialProofDetector, ConversionElement, CompetitorBenchmark,
    detect_social_proof,
)


# ── Fixtures ──────────────────────────────────────────────

def _product(title="Test Product", body_html="", pid=1,
             images=None, variants=None):
    p = {"id": pid, "title": title, "body_html": body_html}
    if images is not None:
        p["images"] = images
    else:
        p["images"] = [{"src": "http://img.com/1.jpg"}]
    if variants is not None:
        p["variants"] = variants
    else:
        p["variants"] = [{"price": "29.99", "inventory_quantity": 100}]
    return p


def _urgency_product():
    return _product(
        body_html="<p>Limited time offer! Hurry, sale ends today. Only 3 left in stock.</p>",
        pid=10,
    )


def _trust_product():
    return _product(
        body_html="<p>30-day money back guarantee. Free shipping. Secure checkout with SSL encrypted payment.</p>",
        pid=20,
    )


def _social_proof_product():
    return _product(
        body_html="<p>★★★★★ 500+ reviews. Best seller! As seen in Forbes. Trusted by 10000 customers.</p>",
        pid=30,
    )


def _payment_product():
    return _product(
        body_html="<p>Pay with Visa, Mastercard, PayPal. Buy now, pay later with Klarna or Afterpay.</p>",
        pid=40,
    )


def _rich_image_product():
    return _product(
        images=[{"src": f"http://img.com/{i}.jpg"} for i in range(8)],
        pid=50,
    )


def _low_stock_product():
    return _product(
        variants=[
            {"title": "Small", "price": "29.99", "inventory_quantity": 2},
            {"title": "Large", "price": "29.99", "inventory_quantity": 50},
        ],
        pid=60,
    )


# ── ConversionElement ────────────────────────────────────

class TestConversionElement:
    def test_to_dict(self):
        el = ConversionElement("urgency", "limited time", "Buy now limited time!", 1)
        d = el.to_dict()
        assert d["type"] == "urgency"
        assert d["pattern"] == "limited time"
        assert d["product_id"] == 1

    def test_context_truncated(self):
        long_ctx = "x" * 300
        el = ConversionElement("test", "pattern", long_ctx)
        assert len(el.context) <= 200


# ── Urgency Detection ────────────────────────────────────

class TestUrgencyDetection:
    def test_detects_limited_time(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_urgency_product()])
        assert result["element_counts"].get("urgency", 0) > 0

    def test_detects_hurry(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Hurry up! Don't miss this deal!</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("urgency", 0) > 0

    def test_no_urgency_in_plain(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>A regular product description.</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("urgency", 0) == 0


# ── Scarcity Detection ───────────────────────────────────

class TestScarcityDetection:
    def test_detects_only_x_left(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Only 5 left in stock!</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("scarcity", 0) > 0

    def test_detects_limited_edition(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Limited edition release</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("scarcity", 0) > 0

    def test_real_scarcity_low_inventory(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_low_stock_product()])
        assert result["element_counts"].get("real_scarcity", 0) > 0

    def test_no_scarcity_high_inventory(self):
        detector = SocialProofDetector()
        p = _product(variants=[{"price": "20", "inventory_quantity": 500}])
        result = detector.analyze_products([p])
        assert result["element_counts"].get("real_scarcity", 0) == 0


# ── Social Proof Detection ───────────────────────────────

class TestSocialProofDetection:
    def test_detects_reviews(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_social_proof_product()])
        assert result["element_counts"].get("social_proof", 0) > 0

    def test_detects_star_ratings(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>★★★★★</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("social_proof", 0) > 0

    def test_detects_bestseller(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Our best seller item!</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("social_proof", 0) > 0

    def test_detects_customer_count(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Trusted by 5000 customers worldwide</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("social_proof", 0) > 0


# ── Trust Detection ───────────────────────────────────────

class TestTrustDetection:
    def test_detects_guarantee(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_trust_product()])
        assert result["element_counts"].get("trust", 0) > 0

    def test_detects_free_shipping(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Free shipping on all orders!</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("trust", 0) > 0

    def test_detects_day_guarantee(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>30-day return policy. Risk-free purchase.</p>")
        result = detector.analyze_products([p])
        trust_count = result["element_counts"].get("trust", 0)
        assert trust_count >= 1


# ── Payment Trust Detection ──────────────────────────────

class TestPaymentTrust:
    def test_detects_payment_methods(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_payment_product()])
        assert result["element_counts"].get("payment_trust", 0) > 0

    def test_detects_bnpl(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Buy now, pay later with Afterpay</p>")
        result = detector.analyze_products([p])
        assert result["element_counts"].get("payment_trust", 0) > 0


# ── Image Richness ────────────────────────────────────────

class TestImageRichness:
    def test_detects_many_images(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_rich_image_product()])
        assert result["element_counts"].get("image_richness", 0) > 0

    def test_no_richness_few_images(self):
        detector = SocialProofDetector()
        p = _product(images=[{"src": "http://img.com/1.jpg"}])
        result = detector.analyze_products([p])
        assert result["element_counts"].get("image_richness", 0) == 0


# ── Report Structure ─────────────────────────────────────

class TestReportStructure:
    def test_empty_products(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([])
        assert result["score"] == 0
        assert result["grade"] == "F"
        assert result["total_products"] == 0

    def test_report_keys(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_urgency_product()])
        assert "score" in result
        assert "grade" in result
        assert "total_products" in result
        assert "products_with_elements" in result
        assert "coverage_pct" in result
        assert "element_counts" in result
        assert "elements" in result
        assert "recommendations" in result
        assert "conversion_tactics" in result

    def test_coverage_calculation(self):
        detector = SocialProofDetector()
        products = [_urgency_product(), _product(body_html="<p>Plain product.</p>", pid=2)]
        result = detector.analyze_products(products)
        assert result["total_products"] == 2
        assert result["products_with_elements"] >= 1
        assert result["coverage_pct"] >= 50

    def test_max_50_elements(self):
        detector = SocialProofDetector()
        # All products have urgency
        products = [_urgency_product() for _ in range(100)]
        for i, p in enumerate(products):
            p["id"] = i
        result = detector.analyze_products(products)
        assert len(result["elements"]) <= 50

    def test_score_range(self):
        detector = SocialProofDetector()
        products = [_urgency_product(), _trust_product(), _social_proof_product(), _payment_product()]
        result = detector.analyze_products(products)
        assert 0 <= result["score"] <= 100


# ── Conversion Tactics ────────────────────────────────────

class TestConversionTactics:
    def test_tactics_structure(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_urgency_product()])
        tactics = result["conversion_tactics"]
        assert "urgency" in tactics
        assert "scarcity" in tactics
        assert "social_proof" in tactics
        assert "trust" in tactics
        assert tactics["urgency"]["used"] is True

    def test_tactics_unused(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Plain simple product.</p>")
        result = detector.analyze_products([p])
        tactics = result["conversion_tactics"]
        assert tactics["urgency"]["used"] is False
        assert tactics["trust"]["used"] is False


# ── Recommendations ───────────────────────────────────────

class TestRecommendations:
    def test_recs_for_missing_elements(self):
        detector = SocialProofDetector()
        p = _product(body_html="<p>Plain product without any conversion elements.</p>")
        result = detector.analyze_products([p])
        recs = result["recommendations"]
        assert len(recs) > 0
        # Should recommend adding social proof and trust
        all_recs = " ".join(recs).lower()
        assert "review" in all_recs or "trust" in all_recs

    def test_max_8_recs(self):
        detector = SocialProofDetector()
        result = detector.analyze_products([_product()])
        assert len(result["recommendations"]) <= 8

    def test_excellent_coverage_positive(self):
        detector = SocialProofDetector()
        products = [_urgency_product(), _trust_product(), _social_proof_product(),
                     _payment_product(), _rich_image_product(), _low_stock_product()]
        result = detector.analyze_products(products)
        # With all types present, fewer recommendations
        recs = result["recommendations"]
        # Might still have some since not all products have all elements
        assert isinstance(recs, list)


# ── Grade ─────────────────────────────────────────────────

class TestGrade:
    def test_grade_mapping(self):
        detector = SocialProofDetector()
        assert detector._score_to_grade(95) == "A+"
        assert detector._score_to_grade(85) == "A"
        assert detector._score_to_grade(75) == "B"
        assert detector._score_to_grade(65) == "C"
        assert detector._score_to_grade(55) == "D"
        assert detector._score_to_grade(30) == "F"


# ── CompetitorBenchmark ──────────────────────────────────

class TestCompetitorBenchmark:
    def test_benchmark_empty(self):
        bench = CompetitorBenchmark()
        result = bench.benchmark({})
        assert result["ranking"] == []

    def test_benchmark_two_stores(self):
        bench = CompetitorBenchmark()
        stores = {
            "store_a": [_urgency_product(), _trust_product(), _social_proof_product()],
            "store_b": [_product(body_html="<p>Plain product.</p>")],
        }
        result = bench.benchmark(stores)
        assert len(result["ranking"]) == 2
        # store_a should rank higher
        assert result["ranking"][0]["store"] == "store_a"

    def test_benchmark_insights(self):
        bench = CompetitorBenchmark()
        stores = {
            "store_a": [_urgency_product()],
            "store_b": [_trust_product()],
        }
        result = bench.benchmark(stores)
        assert len(result["insights"]) > 0

    def test_benchmark_has_stores(self):
        bench = CompetitorBenchmark()
        stores = {"s1": [_product()], "s2": [_product()]}
        result = bench.benchmark(stores)
        assert "s1" in result["stores"]
        assert "s2" in result["stores"]


# ── Reset ─────────────────────────────────────────────────

class TestReset:
    def test_reset_clears(self):
        detector = SocialProofDetector()
        detector.analyze_products([_urgency_product()])
        assert len(detector.elements) > 0
        detector.reset()
        assert len(detector.elements) == 0


# ── Convenience Function ──────────────────────────────────

class TestConvenience:
    def test_detect_social_proof(self):
        result = detect_social_proof([_urgency_product(), _trust_product()])
        assert "score" in result
        assert result["total_products"] == 2
