"""Social proof and conversion element detector for Shopify stores.

Detects trust badges, urgency elements, review counts, scarcity signals,
social sharing, payment trust, and conversion optimization elements.
"""
import re
import logging

logger = logging.getLogger(__name__)


# Pattern categories for detection in HTML/body content
URGENCY_PATTERNS = [
    r"limited\s+time", r"hurry", r"only\s+\d+\s+left",
    r"sale\s+ends", r"last\s+chance", r"flash\s+sale",
    r"ending\s+soon", r"don'?t\s+miss", r"act\s+now",
    r"while\s+supplies\s+last", r"countdown", r"timer",
    r"today\s+only", r"expires?\s+(today|soon|in)",
]

SCARCITY_PATTERNS = [
    r"only\s+\d+\s+(left|remaining|in\s+stock)",
    r"low\s+stock", r"selling\s+fast", r"almost\s+gone",
    r"limited\s+(edition|quantity|stock|supply)",
    r"exclusive", r"rare\s+find", r"few\s+left",
    r"out\s+of\s+stock\s+soon",
]

SOCIAL_PROOF_PATTERNS = [
    r"\d+\s+reviews?", r"\d+\s+ratings?", r"★|⭐|☆",
    r"best\s*seller", r"most\s+popular", r"trending",
    r"as\s+seen\s+(on|in)", r"featured\s+in",
    r"\d+k?\+?\s+(customers?|people|buyers?|sold)",
    r"verified\s+(purchase|buyer|review)",
    r"customer\s+favorite", r"top\s+rated",
]

TRUST_PATTERNS = [
    r"money\s*back\s*guarantee", r"free\s+(shipping|returns?|delivery)",
    r"secure\s+(checkout|payment|ordering)",
    r"ssl\s+encrypted", r"satisfaction\s+guarantee",
    r"\d+[\-\s]day\s+(return|refund|guarantee|warranty)",
    r"trusted\s+by", r"certified", r"authentic",
    r"risk[\-\s]free", r"no\s+questions?\s+asked",
]

PAYMENT_TRUST_PATTERNS = [
    r"visa", r"mastercard", r"amex", r"paypal",
    r"apple\s*pay", r"google\s*pay", r"shop\s*pay",
    r"afterpay", r"klarna", r"affirm", r"sezzle",
    r"buy\s+now[\,\s]+pay\s+later", r"bnpl",
    r"installment", r"split\s+payment",
]


class ConversionElement:
    """A detected conversion/social-proof element."""

    def __init__(self, element_type: str, pattern: str, context: str, product_id=None):
        self.element_type = element_type
        self.pattern = pattern
        self.context = context[:200]
        self.product_id = product_id

    def to_dict(self) -> dict:
        return {
            "type": self.element_type,
            "pattern": self.pattern,
            "context": self.context,
            "product_id": self.product_id,
        }


class SocialProofDetector:
    """Detect social proof and conversion elements in Shopify stores."""

    def __init__(self):
        self.elements: list[ConversionElement] = []

    def reset(self):
        self.elements = []

    def analyze_products(self, products: list) -> dict:
        """Analyze products for social proof and conversion elements."""
        self.reset()
        if not products:
            return self._empty_result()

        for p in products:
            self._scan_product(p)

        return self._build_report(products)

    def _scan_product(self, product: dict):
        """Scan a single product for conversion elements."""
        pid = product.get("id", "unknown")
        body = product.get("body_html", "") or ""
        title = product.get("title", "") or ""
        combined = f"{title} {body}".lower()

        # Strip HTML tags for pattern matching
        text = re.sub(r"<[^>]+>", " ", combined)
        text = re.sub(r"\s+", " ", text).strip()

        self._match_patterns(text, "urgency", URGENCY_PATTERNS, pid)
        self._match_patterns(text, "scarcity", SCARCITY_PATTERNS, pid)
        self._match_patterns(text, "social_proof", SOCIAL_PROOF_PATTERNS, pid)
        self._match_patterns(text, "trust", TRUST_PATTERNS, pid)
        self._match_patterns(text, "payment_trust", PAYMENT_TRUST_PATTERNS, pid)

        # Check variant inventory for real scarcity
        self._check_inventory_scarcity(product, pid)

        # Check image count (products with many images convert better)
        self._check_image_richness(product, pid)

    def _match_patterns(self, text: str, element_type: str, patterns: list, product_id):
        """Match regex patterns against text."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Get surrounding context
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                context = text[start:end].strip()
                self.elements.append(ConversionElement(
                    element_type=element_type,
                    pattern=pattern,
                    context=context,
                    product_id=product_id,
                ))

    def _check_inventory_scarcity(self, product: dict, pid):
        """Check if real inventory levels create natural scarcity."""
        for variant in product.get("variants", []):
            qty = variant.get("inventory_quantity")
            if qty is not None and isinstance(qty, (int, float)):
                if 0 < qty <= 5:
                    self.elements.append(ConversionElement(
                        element_type="real_scarcity",
                        pattern="low_inventory",
                        context=f"Variant '{variant.get('title', 'N/A')}' has only {qty} units left",
                        product_id=pid,
                    ))

    def _check_image_richness(self, product: dict, pid):
        """Products with 4+ images have higher conversion rates."""
        images = product.get("images", [])
        if len(images) >= 6:
            self.elements.append(ConversionElement(
                element_type="image_richness",
                pattern="many_images",
                context=f"Product has {len(images)} images (excellent for conversion)",
                product_id=pid,
            ))

    def _build_report(self, products: list) -> dict:
        """Build the analysis report."""
        type_counts = {}
        for el in self.elements:
            type_counts[el.element_type] = type_counts.get(el.element_type, 0) + 1

        # Calculate conversion optimization score
        total_products = len(products)
        products_with_elements = len(set(
            el.product_id for el in self.elements if el.product_id
        ))
        coverage = products_with_elements / max(total_products, 1)

        # Score based on diversity and coverage
        type_diversity = len(type_counts) / 7  # 7 possible types
        score = round((coverage * 60 + type_diversity * 40), 1)
        score = min(100, score)

        return {
            "score": score,
            "grade": self._score_to_grade(score),
            "total_products": total_products,
            "products_with_elements": products_with_elements,
            "coverage_pct": round(coverage * 100, 1),
            "element_counts": type_counts,
            "total_elements": len(self.elements),
            "elements": [el.to_dict() for el in self.elements[:50]],  # Top 50
            "recommendations": self._generate_recommendations(type_counts, total_products),
            "conversion_tactics": self._analyze_tactics(type_counts),
        }

    def _analyze_tactics(self, type_counts: dict) -> dict:
        """Analyze which conversion tactics the store uses."""
        all_types = [
            "urgency", "scarcity", "social_proof",
            "trust", "payment_trust", "real_scarcity", "image_richness",
        ]
        tactics = {}
        for t in all_types:
            count = type_counts.get(t, 0)
            tactics[t] = {
                "used": count > 0,
                "count": count,
                "effectiveness": "high" if t in ("social_proof", "trust") else "medium",
            }
        return tactics

    def _generate_recommendations(self, type_counts: dict, total: int) -> list[str]:
        """Generate actionable conversion optimization recommendations."""
        recs = []

        if type_counts.get("urgency", 0) == 0:
            recs.append("🟡 Add urgency elements (countdown timers, limited-time offers)")
        if type_counts.get("scarcity", 0) == 0:
            recs.append("🟡 Show stock levels or 'X left' notices to create scarcity")
        if type_counts.get("social_proof", 0) == 0:
            recs.append("🔴 Add customer reviews and ratings (biggest conversion driver)")
        if type_counts.get("trust", 0) == 0:
            recs.append("🔴 Add trust badges (money-back guarantee, free shipping, secure checkout)")
        if type_counts.get("payment_trust", 0) == 0:
            recs.append("🟡 Display accepted payment methods and BNPL options")
        if type_counts.get("image_richness", 0) < total * 0.3:
            recs.append("🟡 Add more product images (6+ images per product recommended)")

        if not recs:
            recs.append("✅ Store has excellent conversion element coverage!")

        return recs[:8]

    def _score_to_grade(self, score: float) -> str:
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    def _empty_result(self) -> dict:
        return {
            "score": 0,
            "grade": "F",
            "total_products": 0,
            "products_with_elements": 0,
            "coverage_pct": 0,
            "element_counts": {},
            "total_elements": 0,
            "elements": [],
            "recommendations": ["Add products to analyze"],
            "conversion_tactics": {},
        }


class CompetitorBenchmark:
    """Benchmark conversion elements across competitor stores."""

    def __init__(self):
        self.detector = SocialProofDetector()

    def benchmark(self, stores: dict[str, list]) -> dict:
        """Compare conversion tactics across stores.

        Args:
            stores: {store_name: products_list}
        """
        results = {}
        for name, products in stores.items():
            results[name] = self.detector.analyze_products(products)

        if not results:
            return {"stores": {}, "ranking": [], "insights": []}

        ranking = sorted(
            results.items(),
            key=lambda x: x[1].get("score", 0),
            reverse=True,
        )

        insights = self._generate_insights(results)

        return {
            "stores": results,
            "ranking": [
                {"rank": i + 1, "store": name, "score": r.get("score", 0), "grade": r.get("grade", "F")}
                for i, (name, r) in enumerate(ranking)
            ],
            "insights": insights,
        }

    def _generate_insights(self, results: dict) -> list[str]:
        """Generate competitive insights."""
        insights = []
        all_tactics = set()
        for r in results.values():
            tactics = r.get("conversion_tactics", {})
            for t, v in tactics.items():
                if v.get("used"):
                    all_tactics.add(t)

        unused_by_all = {"urgency", "scarcity", "social_proof", "trust", "payment_trust"} - all_tactics
        if unused_by_all:
            insights.append(
                f"💡 No competitor uses: {', '.join(unused_by_all)} — opportunity to differentiate"
            )

        scores = [r.get("score", 0) for r in results.values()]
        avg = sum(scores) / len(scores) if scores else 0
        insights.append(f"📊 Average conversion score: {avg:.1f}/100")

        return insights


def detect_social_proof(products: list) -> dict:
    """Convenience function for one-shot social proof detection."""
    detector = SocialProofDetector()
    return detector.analyze_products(products)
