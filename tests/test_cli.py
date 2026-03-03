"""Tests for Shopify Scout CLI module."""
import pytest
from unittest.mock import patch, MagicMock
from app.cli import main, cmd_analyze, cmd_compare, cmd_niche, cmd_export, cmd_batch


MOCK_STORE_DATA = {
    "domain": "test.myshopify.com",
    "product_count": 3,
    "products": [
        {
            "id": 1, "title": "Prod A",
            "product_type": "Shoes", "vendor": "Brand",
            "tags": ["tag1"],
            "variants": [{"price": "99.00"}],
            "created_at": "2025-12-01T00:00:00Z",
        },
        {
            "id": 2, "title": "Prod B",
            "product_type": "Shoes", "vendor": "Brand",
            "tags": ["tag2"],
            "variants": [{"price": "149.00"}],
            "created_at": "2025-11-01T00:00:00Z",
        },
        {
            "id": 3, "title": "Prod C",
            "product_type": "Apparel", "vendor": "Other",
            "tags": ["tag1"],
            "variants": [{"price": "35.00"}],
            "created_at": "2025-10-01T00:00:00Z",
        },
    ],
    "collections": [{"title": "All", "id": 1}],
}


class TestCLIAnalyze:
    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_text_output(self, mock_fetch, capsys):
        args = MagicMock(domain="test.myshopify.com", format="text", output=None)
        result = cmd_analyze(args)
        assert result == 0
        output = capsys.readouterr().out
        assert "test.myshopify.com" in output

    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_json_output(self, mock_fetch, capsys):
        args = MagicMock(domain="test.myshopify.com", format="json", output=None)
        result = cmd_analyze(args)
        assert result == 0

    @patch("app.cli.fetch_store_data")
    def test_empty_store(self, mock_fetch, capsys):
        mock_fetch.return_value = {"domain": "empty.com", "product_count": 0, "products": [], "collections": []}
        args = MagicMock(domain="empty.com", format="text", output=None)
        result = cmd_analyze(args)
        assert result == 1

    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_file_output(self, mock_fetch, tmp_path):
        filepath = str(tmp_path / "out.json")
        args = MagicMock(domain="test.myshopify.com", format="json", output=filepath)
        result = cmd_analyze(args)
        assert result == 0


class TestCLICompare:
    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_compare_two(self, mock_fetch, capsys):
        args = MagicMock(
            domains=["store1.com", "store2.com"],
            format="text", output=None,
        )
        result = cmd_compare(args)
        assert result == 0

    def test_compare_single(self, capsys):
        args = MagicMock(domains=["only-one.com"], format="text", output=None)
        result = cmd_compare(args)
        assert result == 1

    @patch("app.cli.fetch_store_data")
    def test_compare_all_empty(self, mock_fetch, capsys):
        mock_fetch.return_value = {"domain": "e.com", "product_count": 0, "products": [], "collections": []}
        args = MagicMock(domains=["a.com", "b.com"], format="text", output=None)
        result = cmd_compare(args)
        assert result == 1

    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_compare_json(self, mock_fetch, capsys):
        args = MagicMock(
            domains=["a.com", "b.com"],
            format="json", output=None,
        )
        result = cmd_compare(args)
        assert result == 0

    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_compare_csv(self, mock_fetch, capsys):
        args = MagicMock(
            domains=["a.com", "b.com"],
            format="csv", output=None,
        )
        result = cmd_compare(args)
        assert result == 0


class TestCLINiche:
    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_niche_text(self, mock_fetch, capsys):
        args = MagicMock(domain="test.com", format="text", output=None)
        result = cmd_niche(args)
        assert result == 0

    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_niche_json(self, mock_fetch, capsys):
        args = MagicMock(domain="test.com", format="json", output=None)
        result = cmd_niche(args)
        assert result == 0

    @patch("app.cli.fetch_store_data")
    def test_niche_empty(self, mock_fetch, capsys):
        mock_fetch.return_value = {"domain": "e.com", "product_count": 0, "products": [], "collections": []}
        args = MagicMock(domain="e.com", format="text", output=None)
        result = cmd_niche(args)
        assert result == 1


class TestCLIExport:
    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_export_json(self, mock_fetch, tmp_path):
        args = MagicMock(domain="test.com", format="json", output=str(tmp_path / "out.json"))
        result = cmd_export(args)
        assert result == 0

    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_export_html(self, mock_fetch, tmp_path):
        args = MagicMock(domain="test.com", format="html", output=str(tmp_path / "out.html"))
        result = cmd_export(args)
        assert result == 0

    @patch("app.cli.fetch_store_data")
    def test_export_empty(self, mock_fetch):
        mock_fetch.return_value = {"domain": "e.com", "product_count": 0, "products": [], "collections": []}
        args = MagicMock(domain="e.com", format="json", output=None)
        result = cmd_export(args)
        assert result == 1


class TestCLIBatch:
    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_batch_from_file(self, mock_fetch, tmp_path):
        domains_file = tmp_path / "domains.txt"
        domains_file.write_text("store1.com\nstore2.com\n# comment\n\nstore3.com\n")
        output_dir = str(tmp_path / "reports")
        args = MagicMock(file=str(domains_file), output_dir=output_dir)
        result = cmd_batch(args)
        assert result == 0

    def test_batch_missing_file(self, capsys):
        args = MagicMock(file="/nonexistent/file.txt", output_dir=None)
        result = cmd_batch(args)
        assert result == 1

    @patch("app.cli.fetch_store_data", return_value=MOCK_STORE_DATA)
    def test_batch_default_output(self, mock_fetch, tmp_path):
        domains_file = tmp_path / "d.txt"
        domains_file.write_text("a.com\n")
        args = MagicMock(file=str(domains_file), output_dir=None)
        # Should use default "reports/batch"
        result = cmd_batch(args)
        assert result == 0


class TestCLIMain:
    def test_no_command(self, capsys):
        with patch("sys.argv", ["shopify-scout"]):
            result = main()
            assert result == 1

    def test_version(self):
        with patch("sys.argv", ["shopify-scout", "--version"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
