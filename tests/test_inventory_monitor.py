"""
Tests for inventory_monitor.py
"""
import pytest
from app.inventory_monitor import InventoryMonitor, InventorySnapshot, InventoryAlert


@pytest.fixture
def monitor():
    return InventoryMonitor()


@pytest.fixture
def sample_products():
    return [
        {
            "id": 1001,
            "title": "Running Shoes",
            "variants": [
                {
                    "id": 10011,
                    "title": "Size 8",
                    "available": True,
                    "inventory_quantity": 50
                },
                {
                    "id": 10012,
                    "title": "Size 9",
                    "available": True,
                    "inventory_quantity": 5  # Low stock
                }
            ]
        },
        {
            "id": 1002,
            "title": "T-Shirt",
            "variants": [
                {
                    "id": 10021,
                    "title": "Medium",
                    "available": False,
                    "inventory_quantity": 0  # Out of stock
                }
            ]
        }
    ]


def test_take_snapshot(monitor, sample_products):
    """测试拍摄库存快照"""
    snapshots = monitor.take_snapshot(sample_products)
    
    assert len(snapshots) == 3
    assert snapshots[0].product_title == "Running Shoes"
    assert snapshots[0].available is True
    assert snapshots[0].inventory_quantity == 50
    assert snapshots[1].inventory_quantity == 5
    assert snapshots[2].available is False


def test_compare_snapshots_out_of_stock(monitor):
    """测试检测断货"""
    previous = [
        InventorySnapshot(
            product_id="1001",
            product_title="Running Shoes",
            variant_id="10011",
            variant_title="Size 8",
            available=True,
            inventory_quantity=50,
            timestamp="2026-03-01T00:00:00Z"
        )
    ]
    
    current = [
        InventorySnapshot(
            product_id="1001",
            product_title="Running Shoes",
            variant_id="10011",
            variant_title="Size 8",
            available=False,
            inventory_quantity=0,
            timestamp="2026-03-02T00:00:00Z"
        )
    ]
    
    alerts = monitor.compare_snapshots(previous, current)
    
    assert len(alerts) == 1
    assert alerts[0].alert_type == "out_of_stock"
    assert alerts[0].urgency == "high"
    assert "断货" in alerts[0].recommendation


def test_compare_snapshots_restocked(monitor):
    """测试检测补货"""
    previous = [
        InventorySnapshot(
            product_id="1001",
            product_title="Running Shoes",
            variant_id="10011",
            variant_title="Size 8",
            available=False,
            inventory_quantity=0,
            timestamp="2026-03-01T00:00:00Z"
        )
    ]
    
    current = [
        InventorySnapshot(
            product_id="1001",
            product_title="Running Shoes",
            variant_id="10011",
            variant_title="Size 8",
            available=True,
            inventory_quantity=100,
            timestamp="2026-03-02T00:00:00Z"
        )
    ]
    
    alerts = monitor.compare_snapshots(previous, current)
    
    assert len(alerts) == 1
    assert alerts[0].alert_type == "restocked"
    assert alerts[0].urgency == "medium"


def test_compare_snapshots_low_stock(monitor):
    """测试检测低库存"""
    previous = [
        InventorySnapshot(
            product_id="1001",
            product_title="Running Shoes",
            variant_id="10011",
            variant_title="Size 8",
            available=True,
            inventory_quantity=50,
            timestamp="2026-03-01T00:00:00Z"
        )
    ]
    
    current = [
        InventorySnapshot(
            product_id="1001",
            product_title="Running Shoes",
            variant_id="10011",
            variant_title="Size 8",
            available=True,
            inventory_quantity=5,
            timestamp="2026-03-02T00:00:00Z"
        )
    ]
    
    alerts = monitor.compare_snapshots(previous, current)
    
    assert len(alerts) == 1
    assert alerts[0].alert_type == "low_stock"
    assert alerts[0].current_quantity == 5


def test_analyze_inventory_health_excellent(monitor):
    """测试库存健康度分析 - 优秀"""
    products = [
        {
            "id": 1001,
            "variants": [
                {"available": True, "inventory_quantity": 100},
                {"available": True, "inventory_quantity": 50}
            ]
        }
    ]
    
    health = monitor.analyze_inventory_health(products)
    
    assert health["total_variants"] == 2
    assert health["in_stock"] == 2
    assert health["out_of_stock"] == 0
    assert health["health_score"] == "excellent"


def test_analyze_inventory_health_poor(monitor):
    """测试库存健康度分析 - 差"""
    products = [
        {
            "id": 1001,
            "variants": [
                {"available": False, "inventory_quantity": 0},
                {"available": False, "inventory_quantity": 0},
                {"available": False, "inventory_quantity": 0},
                {"available": True, "inventory_quantity": 50}
            ]
        }
    ]
    
    health = monitor.analyze_inventory_health(products)
    
    assert health["total_variants"] == 4
    assert health["out_of_stock"] == 3
    assert health["out_of_stock_rate"] == 75.0
    assert health["health_score"] == "poor"


def test_export_report(monitor):
    """测试导出报告"""
    alerts = [
        InventoryAlert(
            product_id="1001",
            product_title="Running Shoes",
            variant_title="Size 8",
            alert_type="out_of_stock",
            previous_quantity=50,
            current_quantity=0,
            urgency="high",
            recommendation="竞品断货！",
            timestamp="2026-03-02T00:00:00Z"
        )
    ]
    
    health = {
        "total_variants": 10,
        "in_stock": 7,
        "out_of_stock": 3,
        "health_score": "good"
    }
    
    report = monitor.export_report(alerts, health)
    
    assert report["report_type"] == "inventory_monitor"
    assert report["health"]["health_score"] == "good"
    assert report["summary"]["total_alerts"] == 1
    assert report["summary"]["high_urgency"] == 1
    assert len(report["alerts"]) == 1
