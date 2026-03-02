"""
Price Optimizer - 竞品价格监控+自动降价建议引擎
基于竞品价格、历史趋势、库存状态生成动态定价策略
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class PriceRecommendation:
    """定价建议"""
    product_id: str
    product_title: str
    current_price: float
    recommended_price: float
    price_change_pct: float
    reason: str
    confidence: float  # 0-1
    competitor_prices: List[float]
    market_position: str  # "premium" | "competitive" | "budget"
    urgency: str  # "high" | "medium" | "low"
    
class PriceOptimizer:
    """价格优化引擎"""
    
    def __init__(self, target_margin: float = 0.3, aggressive_mode: bool = False):
        """
        Args:
            target_margin: 目标利润率 (0-1)
            aggressive_mode: 激进模式（更低价格抢市场）
        """
        self.target_margin = target_margin
        self.aggressive_mode = aggressive_mode
        
    def analyze_competitive_pricing(
        self,
        own_products: List[Dict],
        competitor_products: List[Dict],
        match_threshold: float = 0.8
    ) -> List[PriceRecommendation]:
        """
        竞品价格分析+降价建议
        
        Args:
            own_products: 自己店铺的产品列表
            competitor_products: 竞品店铺的产品列表
            match_threshold: 产品匹配相似度阈值
            
        Returns:
            定价建议列表
        """
        recommendations = []
        
        # 按类别分组竞品价格
        competitor_price_map = self._build_competitor_price_map(competitor_products)
        
        for product in own_products:
            # 查找同类竞品
            category = product.get('product_type', 'Unknown')
            competitor_prices = competitor_price_map.get(category, [])
            
            if not competitor_prices:
                continue
                
            current_price = float(product.get('price', 0))
            if current_price == 0:
                continue
                
            # 计算市场价格统计
            avg_price = sum(competitor_prices) / len(competitor_prices)
            min_price = min(competitor_prices)
            max_price = max(competitor_prices)
            
            # 生成定价建议
            recommendation = self._generate_recommendation(
                product_id=str(product.get('id', '')),
                product_title=product.get('title', ''),
                current_price=current_price,
                competitor_prices=competitor_prices,
                avg_price=avg_price,
                min_price=min_price,
                max_price=max_price
            )
            
            if recommendation:
                recommendations.append(recommendation)
                
        # 按紧急度排序
        recommendations.sort(key=lambda x: (
            {'high': 0, 'medium': 1, 'low': 2}[x.urgency],
            -x.confidence
        ))
        
        return recommendations
        
    def _build_competitor_price_map(self, products: List[Dict]) -> Dict[str, List[float]]:
        """构建竞品价格映射表"""
        price_map = defaultdict(list)
        
        for product in products:
            category = product.get('product_type', 'Unknown')
            try:
                price = float(product.get('price', 0))
                if price > 0:
                    price_map[category].append(price)
            except (ValueError, TypeError):
                continue
                
        return dict(price_map)
        
    def _generate_recommendation(
        self,
        product_id: str,
        product_title: str,
        current_price: float,
        competitor_prices: List[float],
        avg_price: float,
        min_price: float,
        max_price: float
    ) -> Optional[PriceRecommendation]:
        """生成单个产品的定价建议"""
        
        # 计算市场位置
        if current_price > avg_price * 1.2:
            market_position = "premium"
        elif current_price < avg_price * 0.8:
            market_position = "budget"
        else:
            market_position = "competitive"
            
        # 定价策略
        if self.aggressive_mode:
            # 激进模式：比最低价再低5%
            target_price = min_price * 0.95
            reason = f"激进定价：比市场最低价({min_price:.2f})低5%抢占市场"
            urgency = "high"
            confidence = 0.85
        else:
            # 保守模式：略低于平均价
            if current_price > avg_price * 1.1:
                # 当前价格偏高，建议降至平均价附近
                target_price = avg_price * 0.95
                reason = f"当前价格({current_price:.2f})高于市场均价({avg_price:.2f})，建议降价"
                urgency = "high"
                confidence = 0.9
            elif current_price > avg_price:
                # 略高于平均，微调
                target_price = avg_price * 0.98
                reason = f"微调至市场均价({avg_price:.2f})附近"
                urgency = "medium"
                confidence = 0.75
            else:
                # 价格已经有竞争力，不建议调整
                return None
                
        # 计算价格变化百分比
        price_change_pct = ((target_price - current_price) / current_price) * 100
        
        # 过滤掉变化太小的建议（<2%）
        if abs(price_change_pct) < 2:
            return None
            
        return PriceRecommendation(
            product_id=product_id,
            product_title=product_title,
            current_price=current_price,
            recommended_price=round(target_price, 2),
            price_change_pct=round(price_change_pct, 2),
            reason=reason,
            confidence=confidence,
            competitor_prices=competitor_prices,
            market_position=market_position,
            urgency=urgency
        )
        
    def generate_pricing_report(
        self,
        recommendations: List[PriceRecommendation]
    ) -> Dict:
        """生成定价报告"""
        
        if not recommendations:
            return {
                'summary': {
                    'total_products': 0,
                    'high_urgency': 0,
                    'medium_urgency': 0,
                    'low_urgency': 0,
                    'avg_price_change_pct': 0,
                    'potential_revenue_impact': 0
                },
                'recommendations': []
            }
            
        # 统计
        urgency_counts = defaultdict(int)
        total_price_change = 0
        
        for rec in recommendations:
            urgency_counts[rec.urgency] += 1
            total_price_change += rec.price_change_pct
            
        avg_price_change = total_price_change / len(recommendations)
        
        return {
            'summary': {
                'total_products': len(recommendations),
                'high_urgency': urgency_counts['high'],
                'medium_urgency': urgency_counts['medium'],
                'low_urgency': urgency_counts['low'],
                'avg_price_change_pct': round(avg_price_change, 2),
                'potential_revenue_impact': 'Estimated based on price elasticity'
            },
            'recommendations': [asdict(rec) for rec in recommendations],
            'generated_at': datetime.now().isoformat()
        }
        
    def export_csv(self, recommendations: List[PriceRecommendation], output_path: str):
        """导出CSV格式的定价建议"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Product ID', 'Product Title', 'Current Price', 
                'Recommended Price', 'Change %', 'Reason', 
                'Confidence', 'Urgency', 'Market Position'
            ])
            
            for rec in recommendations:
                writer.writerow([
                    rec.product_id,
                    rec.product_title,
                    rec.current_price,
                    rec.recommended_price,
                    f"{rec.price_change_pct:+.2f}%",
                    rec.reason,
                    f"{rec.confidence:.0%}",
                    rec.urgency,
                    rec.market_position
                ])
