"""Tests for app.seo_analyzer module."""
import pytest
from datetime import datetime, timedelta
from app.seo_analyzer import SEOAnalyzer, SEOIssue, analyze_store_seo


# ── Fixtures ──────────────────────────────────────────────

def _product(title="Test Product", body_html="<p>Good description with enough content here to pass the minimum.</p>",
             handle="test-product", tags=None, images=None, updated_at=None, pid=1):
    """Create a test product dict."""
    if tags is None:
        tags = ["tag1", "tag2", "tag3", "tag4"]
    if images is None:
        images = [{"src": "http://img.com/1.jpg", "alt": "Product image"}]
    p = {
        "id": pid,
        "title": title,
        "body_html": body_html,
        "handle": handle,
        "tags": tags,
        "images": images,
    }
    if updated_at:
        p["updated_at"] = updated_at
    return p


def _good_products(n=5):
    return [_product(title=f"Great Product Number {i}", pid=i,
                     body_html=f"<p>{'x' * 120}</p>",
                     handle=f"great-product-number-{i}") for i in range(n)]


# ── SEOIssue ──────────────────────────────────────────────

class TestSEOIssue:
    def test_to_dict(self):
        issue = SEOIssue("meta_title", SEOIssue.SEVERITY_CRITICAL, "Bad title", "Fix it")
        d = issue.to_dict()
        assert d["category"] == "meta_title"
        assert d["severity"] == "critical"
        assert d["message"] == "Bad title"
        assert d["recommendation"] == "Fix it"

    def test_severity_constants(self):
        assert SEOIssue.SEVERITY_CRITICAL == "critical"
        assert SEOIssue.SEVERITY_WARNING == "warning"
        assert SEOIssue.SEVERITY_INFO == "info"

    def test_timestamp_set(self):
        issue = SEOIssue("test", "info", "msg")
        assert issue.timestamp is not None


# ── Title Checks ──────────────────────────────────────────

class TestTitleChecks:
    def test_empty_title_critical(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(title="")])
        issues = [i for i in result["issues"] if i["category"] == "meta_title" and i["severity"] == "critical"]
        assert len(issues) >= 1

    def test_short_title_warning(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(title="Short")])
        issues = [i for i in result["issues"] if "short titles" in i["message"]]
        assert len(issues) == 1

    def test_long_title_warning(self):
        analyzer = SEOAnalyzer()
        long = "A" * 80
        result = analyzer.analyze_products_seo([_product(title=long)])
        issues = [i for i in result["issues"] if "long titles" in i["message"]]
        assert len(issues) == 1

    def test_good_title_no_warning(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(title="Perfect SEO Product Title")])
        title_issues = [i for i in result["issues"] if i["category"] == "meta_title"]
        assert len(title_issues) == 0

    def test_duplicate_titles_critical(self):
        analyzer = SEOAnalyzer()
        products = [_product(title="Same Title", pid=1), _product(title="Same Title", pid=2)]
        result = analyzer.analyze_products_seo(products)
        issues = [i for i in result["issues"] if "duplicate" in i["message"].lower()]
        assert len(issues) >= 1

    def test_duplicate_case_insensitive(self):
        analyzer = SEOAnalyzer()
        products = [_product(title="My Product", pid=1), _product(title="my product", pid=2)]
        result = analyzer.analyze_products_seo(products)
        issues = [i for i in result["issues"] if "duplicate" in i["message"].lower()]
        assert len(issues) >= 1


# ── Description Checks ────────────────────────────────────

class TestDescriptionChecks:
    def test_no_description_critical(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(body_html="")])
        issues = [i for i in result["issues"] if "no description" in i["message"]]
        assert len(issues) == 1

    def test_short_description_warning(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(body_html="<p>Short</p>")])
        issues = [i for i in result["issues"] if "short descriptions" in i["message"]]
        assert len(issues) == 1

    def test_good_description_no_issues(self):
        analyzer = SEOAnalyzer()
        long_desc = "<p>" + "x" * 200 + "</p>"
        result = analyzer.analyze_products_seo([_product(body_html=long_desc)])
        desc_issues = [i for i in result["issues"] if i["category"] == "meta_description"]
        assert len(desc_issues) == 0

    def test_html_tags_stripped(self):
        analyzer = SEOAnalyzer()
        # HTML tags should be stripped, leaving short text
        html = "<b>Hi</b><br/><span>there</span>"
        result = analyzer.analyze_products_seo([_product(body_html=html)])
        desc_issues = [i for i in result["issues"] if i["category"] == "meta_description"]
        assert len(desc_issues) >= 1  # "Hi there" is short


# ── URL/Handle Checks ─────────────────────────────────────

class TestURLChecks:
    def test_good_handle(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(handle="nice-seo-handle")])
        url_issues = [i for i in result["issues"] if i["category"] == "url_structure"]
        assert len(url_issues) == 0

    def test_uppercase_handle_warning(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(handle="Bad-Handle")])
        url_issues = [i for i in result["issues"] if i["category"] == "url_structure"]
        assert len(url_issues) >= 1

    def test_special_chars_handle(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(handle="bad handle!")])
        url_issues = [i for i in result["issues"] if i["category"] == "url_structure"]
        assert len(url_issues) >= 1

    def test_long_handle_info(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(handle="a" * 80)])
        url_issues = [i for i in result["issues"] if "long URL" in i["message"]]
        assert len(url_issues) == 1

    def test_empty_handle(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(handle="")])
        url_issues = [i for i in result["issues"] if i["category"] == "url_structure"]
        assert len(url_issues) >= 1


# ── Image Checks ──────────────────────────────────────────

class TestImageChecks:
    def test_no_images_critical(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(images=[])])
        img_issues = [i for i in result["issues"] if "no images" in i["message"]]
        assert len(img_issues) == 1

    def test_missing_alt_warning(self):
        analyzer = SEOAnalyzer()
        images = [{"src": "http://img.com/1.jpg", "alt": ""}]
        result = analyzer.analyze_products_seo([_product(images=images)])
        alt_issues = [i for i in result["issues"] if "alt text" in i["message"]]
        assert len(alt_issues) == 1

    def test_good_images(self):
        analyzer = SEOAnalyzer()
        images = [
            {"src": "http://img.com/1.jpg", "alt": "Blue running shoes"},
            {"src": "http://img.com/2.jpg", "alt": "Side view"},
        ]
        result = analyzer.analyze_products_seo([_product(images=images)])
        img_issues = [i for i in result["issues"] if i["category"] == "image_alt"]
        assert len(img_issues) == 0

    def test_partial_alt_missing(self):
        analyzer = SEOAnalyzer()
        images = [
            {"src": "http://img.com/1.jpg", "alt": "Good alt"},
            {"src": "http://img.com/2.jpg", "alt": ""},
            {"src": "http://img.com/3.jpg"},
        ]
        result = analyzer.analyze_products_seo([_product(images=images)])
        alt_issues = [i for i in result["issues"] if "alt text" in i["message"]]
        assert len(alt_issues) == 1
        assert "2/3" in alt_issues[0]["message"]


# ── Tag/Keyword Checks ────────────────────────────────────

class TestTagChecks:
    def test_no_tags_warning(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(tags=[])])
        tag_issues = [i for i in result["issues"] if "no tags" in i["message"]]
        assert len(tag_issues) == 1

    def test_few_tags_info(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(tags=["one", "two"])])
        tag_issues = [i for i in result["issues"] if "fewer than 3" in i["message"]]
        assert len(tag_issues) == 1

    def test_good_tags(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(tags=["a", "b", "c", "d", "e"])])
        tag_issues = [i for i in result["issues"] if i["category"] == "structured_data"]
        assert len(tag_issues) == 0

    def test_string_tags_split(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([_product(tags="a, b, c, d")])
        tag_issues = [i for i in result["issues"] if "no tags" in i["message"]]
        # String tags get split by comma in the checker
        assert len(tag_issues) == 0


# ── Freshness Checks ──────────────────────────────────────

class TestFreshness:
    def test_stale_products_info(self):
        analyzer = SEOAnalyzer()
        old_date = (datetime.utcnow() - timedelta(days=200)).isoformat()
        result = analyzer.analyze_products_seo([_product(updated_at=old_date)])
        fresh_issues = [i for i in result["issues"] if "6+ months" in i["message"]]
        assert len(fresh_issues) == 1

    def test_fresh_products_no_issue(self):
        analyzer = SEOAnalyzer()
        recent = datetime.utcnow().isoformat()
        result = analyzer.analyze_products_seo([_product(updated_at=recent)])
        fresh_issues = [i for i in result["issues"] if i["category"] == "page_freshness"]
        assert len(fresh_issues) == 0


# ── Overall Score & Grade ─────────────────────────────────

class TestScoring:
    def test_perfect_score_high(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo(_good_products(10))
        assert result["score"] >= 70
        assert result["grade"] in ("A+", "A", "B")

    def test_terrible_score_low(self):
        analyzer = SEOAnalyzer()
        bad_products = [_product(title="", body_html="", handle="BAD!", tags=[], images=[]) for _ in range(5)]
        result = analyzer.analyze_products_seo(bad_products)
        assert result["score"] < 50
        assert result["grade"] in ("D", "F")

    def test_grade_mapping(self):
        analyzer = SEOAnalyzer()
        assert analyzer._score_to_grade(95) == "A+"
        assert analyzer._score_to_grade(85) == "A"
        assert analyzer._score_to_grade(75) == "B"
        assert analyzer._score_to_grade(65) == "C"
        assert analyzer._score_to_grade(55) == "D"
        assert analyzer._score_to_grade(40) == "F"

    def test_empty_products(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo([])
        assert result["score"] == 0

    def test_result_structure(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo(_good_products(3))
        assert "score" in result
        assert "grade" in result
        assert "total_products" in result
        assert "critical_issues" in result
        assert "warnings" in result
        assert "issues" in result
        assert "category_scores" in result
        assert "recommendations" in result

    def test_recommendations_generated(self):
        analyzer = SEOAnalyzer()
        bad = [_product(title="", body_html="", images=[], tags=[])]
        result = analyzer.analyze_products_seo(bad)
        assert len(result["recommendations"]) > 0

    def test_recommendations_max_10(self):
        analyzer = SEOAnalyzer()
        result = analyzer.analyze_products_seo(_good_products(3))
        assert len(result["recommendations"]) <= 10


# ── Compare SEO ───────────────────────────────────────────

class TestCompareSEO:
    def test_compare_empty(self):
        analyzer = SEOAnalyzer()
        result = analyzer.compare_seo([])
        assert result["ranking"] == []

    def test_compare_ranking(self):
        analyzer = SEOAnalyzer()
        results = [
            {"score": 80, "grade": "A", "total_products": 10, "critical_issues": 0},
            {"score": 60, "grade": "C", "total_products": 5, "critical_issues": 2},
            {"score": 90, "grade": "A+", "total_products": 8, "critical_issues": 0},
        ]
        compared = analyzer.compare_seo(results)
        assert compared["ranking"][0]["rank"] == 1
        assert compared["ranking"][0]["score"] == 90
        assert compared["best"]["score"] == 90
        assert compared["worst"]["score"] == 60
        assert compared["avg_score"] == pytest.approx(76.7, abs=0.1)
        assert compared["spread"] == 30

    def test_compare_single(self):
        analyzer = SEOAnalyzer()
        results = [{"score": 75, "grade": "B", "total_products": 5, "critical_issues": 0}]
        compared = analyzer.compare_seo(results)
        assert len(compared["ranking"]) == 1
        assert compared["spread"] == 0


# ── Reset ─────────────────────────────────────────────────

class TestReset:
    def test_reset_clears_state(self):
        analyzer = SEOAnalyzer()
        analyzer.analyze_products_seo(_good_products(3))
        assert len(analyzer.scores) > 0
        analyzer.reset()
        assert len(analyzer.issues) == 0
        assert len(analyzer.scores) == 0


# ── Convenience Function ──────────────────────────────────

class TestConvenience:
    def test_analyze_store_seo(self):
        result = analyze_store_seo(_good_products(3), "test.myshopify.com")
        assert "score" in result
        assert "grade" in result
        assert result["total_products"] == 3
