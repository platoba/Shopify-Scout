"""Tests for Shopify Scout monitor module."""
import os
import pytest
import tempfile
from unittest.mock import patch
from app import monitor


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    db_path = str(tmp_path / "test_monitor.db")
    with patch.object(monitor, "MONITOR_DB", db_path):
        yield db_path


class TestWatchOperations:
    def test_add_and_list(self):
        assert monitor.add_watch("test.com", 123)
        watches = monitor.list_watches(123)
        assert len(watches) == 1
        assert watches[0]["domain"] == "test.com"

    def test_add_duplicate_replaces(self):
        monitor.add_watch("test.com", 123)
        monitor.add_watch("test.com", 123)
        watches = monitor.list_watches(123)
        assert len(watches) == 1

    def test_remove_watch(self):
        monitor.add_watch("test.com", 123)
        assert monitor.remove_watch("test.com", 123)
        assert monitor.list_watches(123) == []

    def test_remove_nonexistent(self):
        assert not monitor.remove_watch("nope.com", 123)

    def test_list_empty(self):
        assert monitor.list_watches(999) == []

    def test_multiple_chats(self):
        monitor.add_watch("a.com", 1)
        monitor.add_watch("b.com", 2)
        assert len(monitor.list_watches(1)) == 1
        assert len(monitor.list_watches(2)) == 1

    def test_get_all_watches(self):
        monitor.add_watch("a.com", 1)
        monitor.add_watch("b.com", 2)
        all_w = monitor.get_all_watches()
        assert len(all_w) == 2


class TestChangeDetection:
    def test_detect_new_products(self):
        current = [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]
        last = {"1": "A"}
        result = monitor.detect_changes("test.com", current, last)
        assert len(result["new"]) == 1
        assert result["new"][0]["id"] == "2"
        assert result["changed"]

    def test_detect_removed_products(self):
        current = [{"id": 1, "title": "A"}]
        last = {"1": "A", "2": "B"}
        result = monitor.detect_changes("test.com", current, last)
        assert len(result["removed"]) == 1
        assert result["removed"][0]["id"] == "2"

    def test_no_changes(self):
        current = [{"id": 1, "title": "A"}]
        last = {"1": "A"}
        result = monitor.detect_changes("test.com", current, last)
        assert not result["changed"]

    def test_empty_last_snapshot(self):
        current = [{"id": 1, "title": "A"}]
        result = monitor.detect_changes("test.com", current, {})
        assert len(result["new"]) == 1
