"""Tests for Shopify Scout scraper module."""
from unittest.mock import patch, MagicMock
from app.scraper import normalize_domain, fetch_store_data


class TestNormalizeDomain:
    def test_plain_domain(self):
        assert normalize_domain("allbirds.com") == "allbirds.com"

    def test_https_url(self):
        assert normalize_domain("https://allbirds.com/products") == "allbirds.com"

    def test_http_url(self):
        assert normalize_domain("http://store.myshopify.com") == "store.myshopify.com"

    def test_trailing_slash(self):
        assert normalize_domain("allbirds.com/") == "allbirds.com"

    def test_uppercase(self):
        assert normalize_domain("AllBirds.COM") == "allbirds.com"

    def test_whitespace(self):
        assert normalize_domain("  allbirds.com  ") == "allbirds.com"


class TestFetchStoreData:
    @patch("app.scraper._request_with_retry")
    def test_successful_fetch(self, mock_req):
        products_resp = MagicMock()
        products_resp.json.return_value = {
            "products": [
                {
                    "id": 1, "title": "Test Product",
                    "product_type": "Shoes",
                    "tags": ["running", "eco"],
                    "variants": [{"price": "99.00"}],
                    "created_at": "2025-01-01T00:00:00Z",
                    "vendor": "TestBrand",
                }
            ]
        }
        collections_resp = MagicMock()
        collections_resp.json.return_value = {
            "collections": [{"title": "All", "id": 1}]
        }
        meta_resp = MagicMock()
        meta_resp.json.return_value = {"name": "Test Store"}

        mock_req.side_effect = [products_resp, None, meta_resp]  # products, page2=None, meta

        # Need to also mock collections separately
        with patch("app.scraper.fetch_collections", return_value=[{"title": "All", "id": 1}]):
            data = fetch_store_data("test.myshopify.com")

        assert data["domain"] == "test.myshopify.com"
        assert data["product_count"] == 1
        assert len(data["products"]) == 1

    @patch("app.scraper._request_with_retry")
    def test_empty_store(self, mock_req):
        mock_req.return_value = None
        data = fetch_store_data("empty.com")
        assert data["product_count"] == 0
        assert data["products"] == []
