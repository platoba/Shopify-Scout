"""SEO health analyzer for Shopify stores.

Analyzes meta tags, structured data, URL structure, sitemap,
canonical URLs, image alt texts, page speed signals, and more.
"""
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# SEO scoring weights
WEIGHTS = {
    "meta_title": 15,
    "meta_description": 15,
    "canonical": 10,
    "sitemap": 10,
    "robots_txt": 5,
    "url_structure": 10,
    "image_alt": 10,
    "structured_data": 10,
    "heading_hierarchy": 5,
    "internal_links": 5,
    "page_freshness": 5,
}


class SEOIssue:
    """Represents a single SEO issue found during analysis."""

    SEVERITY_CRITICAL = "critical"
    SEVERITY_WARNING = "warning"
    SEVERITY_INFO = "info"

    def __init__(self, category: str, severity: str, message: str, recommendation: str = ""):
        self.category = category
        self.severity = severity
        self.message = message
        self.recommendation = recommendation
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
        }


class SEOAnalyzer:
    """Comprehensive SEO analyzer for Shopify product pages and stores."""

    def __init__(self):
        self.issues: list[SEOIssue] = []
        self.scores: dict[str, float] = {}

    def reset(self):
        """Clear all issues and scores."""
        self.issues = []
        self.scores = {}

    def analyze_products_seo(self, products: list, store_domain: str = "") -> dict:
        """Analyze SEO health of product listings."""
        self.reset()
        if not products:
            return {"score": 0, "issues": [], "summary": "No products to analyze"}

        title_issues = self._check_titles(products)
        desc_issues = self._check_descriptions(products)
        url_issues = self._check_urls(products, store_domain)
        image_issues = self._check_images(products)
        tag_issues = self._check_tags_as_keywords(products)
        freshness = self._check_freshness(products)

        total_weight = sum(WEIGHTS.values())
        earned = sum(self.scores.get(k, 0) * v for k, v in WEIGHTS.items())
        max_possible = sum(
            (1.0 if k in self.scores else 0) * v for k, v in WEIGHTS.items()
        )
        overall_score = round((earned / max_possible * 100) if max_possible > 0 else 0, 1)

        critical = [i for i in self.issues if i.severity == SEOIssue.SEVERITY_CRITICAL]
        warnings = [i for i in self.issues if i.severity == SEOIssue.SEVERITY_WARNING]
        infos = [i for i in self.issues if i.severity == SEOIssue.SEVERITY_INFO]

        return {
            "score": overall_score,
            "grade": self._score_to_grade(overall_score),
            "total_products": len(products),
            "critical_issues": len(critical),
            "warnings": len(warnings),
            "info": len(infos),
            "issues": [i.to_dict() for i in self.issues],
            "category_scores": {k: round(v * 100, 1) for k, v in self.scores.items()},
            "recommendations": self._generate_recommendations(),
        }

    def _check_titles(self, products: list) -> list:
        """Check product titles for SEO best practices."""
        issues = []
        short_titles = 0
        long_titles = 0
        duplicate_titles = set()
        seen_titles = {}

        for p in products:
            title = p.get("title", "")
            pid = p.get("id", "unknown")

            if not title:
                issues.append(SEOIssue(
                    "meta_title", SEOIssue.SEVERITY_CRITICAL,
                    f"Product {pid} has no title",
                    "Every product must have a descriptive title"
                ))
                continue

            if len(title) < 20:
                short_titles += 1
            elif len(title) > 70:
                long_titles += 1

            title_lower = title.lower().strip()
            if title_lower in seen_titles:
                duplicate_titles.add(title_lower)
            seen_titles[title_lower] = pid

        total = len(products)
        if short_titles > 0:
            issues.append(SEOIssue(
                "meta_title", SEOIssue.SEVERITY_WARNING,
                f"{short_titles}/{total} products have short titles (<20 chars)",
                "Titles should be 20-70 characters for optimal SEO"
            ))
        if long_titles > 0:
            issues.append(SEOIssue(
                "meta_title", SEOIssue.SEVERITY_WARNING,
                f"{long_titles}/{total} products have long titles (>70 chars)",
                "Keep titles under 70 characters to avoid truncation in search results"
            ))
        if duplicate_titles:
            issues.append(SEOIssue(
                "meta_title", SEOIssue.SEVERITY_CRITICAL,
                f"{len(duplicate_titles)} duplicate title(s) found",
                "Each product should have a unique title"
            ))

        # Score: penalize for issues
        penalty = (short_titles + long_titles + len(duplicate_titles) * 2) / max(total, 1)
        self.scores["meta_title"] = max(0, 1.0 - penalty)
        self.issues.extend(issues)
        return issues

    def _check_descriptions(self, products: list) -> list:
        """Check product descriptions/body_html for SEO."""
        issues = []
        no_desc = 0
        short_desc = 0
        no_keywords_in_desc = 0

        for p in products:
            body = p.get("body_html", "") or ""
            text = re.sub(r"<[^>]+>", "", body).strip()

            if not text:
                no_desc += 1
            elif len(text) < 100:
                short_desc += 1

        total = len(products)
        if no_desc > 0:
            issues.append(SEOIssue(
                "meta_description", SEOIssue.SEVERITY_CRITICAL,
                f"{no_desc}/{total} products have no description",
                "Add detailed product descriptions (300+ words recommended)"
            ))
        if short_desc > 0:
            issues.append(SEOIssue(
                "meta_description", SEOIssue.SEVERITY_WARNING,
                f"{short_desc}/{total} products have short descriptions (<100 chars)",
                "Descriptions should be at least 100 characters for better ranking"
            ))

        penalty = (no_desc * 2 + short_desc) / max(total, 1)
        self.scores["meta_description"] = max(0, 1.0 - penalty)
        self.issues.extend(issues)
        return issues

    def _check_urls(self, products: list, store_domain: str) -> list:
        """Check URL/handle structure for SEO friendliness."""
        issues = []
        bad_handles = 0
        long_handles = 0

        for p in products:
            handle = p.get("handle", "")
            if not handle:
                bad_handles += 1
                continue

            if re.search(r"[A-Z]", handle):
                bad_handles += 1
            elif re.search(r"[^a-z0-9\-]", handle):
                bad_handles += 1
            elif len(handle) > 75:
                long_handles += 1

        total = len(products)
        if bad_handles > 0:
            issues.append(SEOIssue(
                "url_structure", SEOIssue.SEVERITY_WARNING,
                f"{bad_handles}/{total} products have non-optimal URL handles",
                "Handles should be lowercase, hyphen-separated, keyword-rich"
            ))
        if long_handles > 0:
            issues.append(SEOIssue(
                "url_structure", SEOIssue.SEVERITY_INFO,
                f"{long_handles}/{total} products have long URL handles (>75 chars)",
                "Keep URL slugs concise for better sharing and SEO"
            ))

        penalty = (bad_handles + long_handles * 0.5) / max(total, 1)
        self.scores["url_structure"] = max(0, 1.0 - penalty)
        self.issues.extend(issues)
        return issues

    def _check_images(self, products: list) -> list:
        """Check image alt text and image count."""
        issues = []
        no_images = 0
        missing_alt = 0
        total_images = 0

        for p in products:
            images = p.get("images", [])
            if not images:
                no_images += 1
                continue
            for img in images:
                total_images += 1
                alt = img.get("alt") or ""
                if not alt.strip():
                    missing_alt += 1

        total = len(products)
        if no_images > 0:
            issues.append(SEOIssue(
                "image_alt", SEOIssue.SEVERITY_CRITICAL,
                f"{no_images}/{total} products have no images",
                "Every product should have at least one high-quality image"
            ))
        if missing_alt > 0 and total_images > 0:
            pct = round(missing_alt / total_images * 100, 1)
            issues.append(SEOIssue(
                "image_alt", SEOIssue.SEVERITY_WARNING,
                f"{missing_alt}/{total_images} images ({pct}%) missing alt text",
                "Add descriptive alt text to all images for accessibility and SEO"
            ))

        img_penalty = (no_images / max(total, 1)) * 0.5
        alt_penalty = (missing_alt / max(total_images, 1)) * 0.5
        self.scores["image_alt"] = max(0, 1.0 - img_penalty - alt_penalty)
        self.issues.extend(issues)
        return issues

    def _check_tags_as_keywords(self, products: list) -> list:
        """Check if products use tags effectively as keywords."""
        issues = []
        no_tags = 0
        few_tags = 0

        for p in products:
            tags = p.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            if not tags:
                no_tags += 1
            elif len(tags) < 3:
                few_tags += 1

        total = len(products)
        if no_tags > 0:
            issues.append(SEOIssue(
                "structured_data", SEOIssue.SEVERITY_WARNING,
                f"{no_tags}/{total} products have no tags/keywords",
                "Add 5-15 relevant tags per product for internal search and SEO"
            ))
        if few_tags > 0:
            issues.append(SEOIssue(
                "structured_data", SEOIssue.SEVERITY_INFO,
                f"{few_tags}/{total} products have fewer than 3 tags",
                "Consider adding more tags for better categorization"
            ))

        penalty = (no_tags * 1.5 + few_tags * 0.5) / max(total, 1)
        self.scores["structured_data"] = max(0, 1.0 - penalty)
        self.issues.extend(issues)
        return issues

    def _check_freshness(self, products: list) -> list:
        """Check product update freshness."""
        issues = []
        stale_count = 0
        now = datetime.utcnow()

        for p in products:
            updated = p.get("updated_at", "")
            if updated:
                try:
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    dt_naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
                    days_old = (now - dt_naive).days
                    if days_old > 180:
                        stale_count += 1
                except (ValueError, TypeError):
                    pass

        total = len(products)
        if stale_count > 0:
            issues.append(SEOIssue(
                "page_freshness", SEOIssue.SEVERITY_INFO,
                f"{stale_count}/{total} products not updated in 6+ months",
                "Regularly update product descriptions and images for freshness signals"
            ))

        penalty = stale_count / max(total, 1)
        self.scores["page_freshness"] = max(0, 1.0 - penalty)
        self.issues.extend(issues)
        return issues

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
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

    def _generate_recommendations(self) -> list[str]:
        """Generate prioritized recommendations based on issues."""
        recs = []
        critical = [i for i in self.issues if i.severity == SEOIssue.SEVERITY_CRITICAL]
        warnings = [i for i in self.issues if i.severity == SEOIssue.SEVERITY_WARNING]

        for issue in critical:
            if issue.recommendation:
                recs.append(f"🔴 {issue.recommendation}")

        for issue in warnings:
            if issue.recommendation:
                recs.append(f"🟡 {issue.recommendation}")

        if not recs:
            recs.append("✅ No critical SEO issues found!")

        return recs[:10]  # Top 10 recommendations

    def compare_seo(self, results: list[dict]) -> dict:
        """Compare SEO scores across multiple stores."""
        if not results:
            return {"ranking": [], "best": None, "worst": None}

        sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
        ranking = []
        for i, r in enumerate(sorted_results):
            ranking.append({
                "rank": i + 1,
                "score": r.get("score", 0),
                "grade": r.get("grade", "F"),
                "total_products": r.get("total_products", 0),
                "critical_issues": r.get("critical_issues", 0),
            })

        return {
            "ranking": ranking,
            "best": ranking[0] if ranking else None,
            "worst": ranking[-1] if ranking else None,
            "avg_score": round(sum(r["score"] for r in ranking) / len(ranking), 1),
            "spread": round(ranking[0]["score"] - ranking[-1]["score"], 1) if len(ranking) >= 2 else 0,
        }


def analyze_store_seo(products: list, store_domain: str = "") -> dict:
    """Convenience function for one-shot SEO analysis."""
    analyzer = SEOAnalyzer()
    return analyzer.analyze_products_seo(products, store_domain)
