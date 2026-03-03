"""
Inventory Monitor - 竞品库存监控+断货预警系统
监控竞品库存变化，预测断货风险，抓住补货时机
"""
import json
from datetime import datetime, UTC
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class InventorySnapshot:
    """库存快照"""
    product_id: str
    product_title: str
    variant_id: str
    variant_title: str
    available: bool
    inventory_quantity: Optional[int]
    timestamp: str
    
    
@dataclass
class InventoryAlert:
    """库存预警"""
    product_id: str
    product_title: str
    variant_title: str
    alert_type: str  # low_stock, out_of_stock, restocked
    previous_quantity: Optional[int]
    current_quantity: Optional[int]
    urgency: str  # high, medium, low
    recommendation: str
    timestamp: str


class InventoryMonitor:
    """库存监控引擎"""
    
    LOW_STOCK_THRESHOLD = 10  # 低库存阈值
    
    def __init__(self):
        self.snapshots: Dict[str, List[InventorySnapshot]] = {}
        
    def take_snapshot(self, products: List[Dict]) -> List[InventorySnapshot]:
        """
        拍摄库存快照
        
        Args:
            products: 产品列表（来自scraper）
            
        Returns:
            库存快照列表
        """
        snapshots = []
        timestamp = datetime.now(UTC).isoformat() + "Z"
        
        for product in products:
            product_id = str(product.get("id", ""))
            product_title = product.get("title", "Unknown")
            
            for variant in product.get("variants", []):
                snapshot = InventorySnapshot(
                    product_id=product_id,
                    product_title=product_title,
                    variant_id=str(variant.get("id", "")),
                    variant_title=variant.get("title", "Default"),
                    available=variant.get("available", False),
                    inventory_quantity=variant.get("inventory_quantity"),
                    timestamp=timestamp
                )
                snapshots.append(snapshot)
                
        return snapshots
    
    def compare_snapshots(
        self, 
        previous: List[InventorySnapshot], 
        current: List[InventorySnapshot]
    ) -> List[InventoryAlert]:
        """
        对比两次快照，生成预警
        
        Args:
            previous: 上次快照
            current: 本次快照
            
        Returns:
            预警列表
        """
        alerts = []
        
        # 构建上次快照索引
        prev_index = {
            (s.product_id, s.variant_id): s 
            for s in previous
        }
        
        for curr in current:
            key = (curr.product_id, curr.variant_id)
            prev = prev_index.get(key)
            
            if not prev:
                continue
                
            # 检测断货
            if prev.available and not curr.available:
                alerts.append(InventoryAlert(
                    product_id=curr.product_id,
                    product_title=curr.product_title,
                    variant_title=curr.variant_title,
                    alert_type="out_of_stock",
                    previous_quantity=prev.inventory_quantity,
                    current_quantity=curr.inventory_quantity,
                    urgency="high",
                    recommendation="竞品断货！立即推广同类产品抢占市场份额",
                    timestamp=curr.timestamp
                ))
                
            # 检测补货
            elif not prev.available and curr.available:
                alerts.append(InventoryAlert(
                    product_id=curr.product_id,
                    product_title=curr.product_title,
                    variant_title=curr.variant_title,
                    alert_type="restocked",
                    previous_quantity=prev.inventory_quantity,
                    current_quantity=curr.inventory_quantity,
                    urgency="medium",
                    recommendation="竞品已补货，关注其价格和促销策略",
                    timestamp=curr.timestamp
                ))
                
            # 检测低库存
            elif (curr.available and 
                  curr.inventory_quantity is not None and 
                  curr.inventory_quantity <= self.LOW_STOCK_THRESHOLD):
                alerts.append(InventoryAlert(
                    product_id=curr.product_id,
                    product_title=curr.product_title,
                    variant_title=curr.variant_title,
                    alert_type="low_stock",
                    previous_quantity=prev.inventory_quantity,
                    current_quantity=curr.inventory_quantity,
                    urgency="medium",
                    recommendation=f"竞品库存仅剩{curr.inventory_quantity}件，准备抢占市场",
                    timestamp=curr.timestamp
                ))
                
        return alerts
    
    def analyze_inventory_health(self, products: List[Dict]) -> Dict:
        """
        分析整体库存健康度
        
        Args:
            products: 产品列表
            
        Returns:
            库存健康报告
        """
        total_variants = 0
        in_stock = 0
        out_of_stock = 0
        low_stock = 0
        unknown = 0
        
        for product in products:
            for variant in product.get("variants", []):
                total_variants += 1
                
                if variant.get("available"):
                    qty = variant.get("inventory_quantity")
                    if qty is None:
                        unknown += 1
                    elif qty <= self.LOW_STOCK_THRESHOLD:
                        low_stock += 1
                    else:
                        in_stock += 1
                else:
                    out_of_stock += 1
                    
        in_stock_rate = (in_stock / total_variants * 100) if total_variants > 0 else 0
        out_of_stock_rate = (out_of_stock / total_variants * 100) if total_variants > 0 else 0
        
        # 健康度评分
        if out_of_stock_rate > 30:
            health_score = "poor"
            health_message = "库存严重不足，大量产品断货"
        elif out_of_stock_rate > 15:
            health_score = "fair"
            health_message = "库存管理一般，部分产品断货"
        elif low_stock > total_variants * 0.2:
            health_score = "good"
            health_message = "库存健康，但需关注低库存产品"
        else:
            health_score = "excellent"
            health_message = "库存管理优秀"
            
        return {
            "total_variants": total_variants,
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "unknown": unknown,
            "in_stock_rate": round(in_stock_rate, 2),
            "out_of_stock_rate": round(out_of_stock_rate, 2),
            "health_score": health_score,
            "health_message": health_message
        }
    
    def export_report(self, alerts: List[InventoryAlert], health: Dict) -> Dict:
        """
        导出库存监控报告
        
        Args:
            alerts: 预警列表
            health: 健康度报告
            
        Returns:
            完整报告
        """
        return {
            "report_type": "inventory_monitor",
            "generated_at": datetime.now(UTC).isoformat() + "Z",
            "health": health,
            "alerts": [asdict(alert) for alert in alerts],
            "summary": {
                "total_alerts": len(alerts),
                "high_urgency": len([a for a in alerts if a.urgency == "high"]),
                "medium_urgency": len([a for a in alerts if a.urgency == "medium"]),
                "out_of_stock_count": len([a for a in alerts if a.alert_type == "out_of_stock"]),
                "low_stock_count": len([a for a in alerts if a.alert_type == "low_stock"]),
                "restocked_count": len([a for a in alerts if a.alert_type == "restocked"])
            }
        }
