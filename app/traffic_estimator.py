"""
Traffic Estimator - Shopify store traffic estimation module
Estimates monthly traffic using heuristic signals from public data
"""
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics

class TrafficEstimator:
    """Estimate store traffic from public signals"""
    
    # Traffic multipliers based on signals
    REVIEW_MULTIPLIER = 150  # avg visitors per review
    PRODUCT_BASE_TRAFFIC = 50  # base monthly traffic per product
    COLLECTION_MULTIPLIER = 200  # traffic per collection
    
    def __init__(self, store_data: Dict):
        self.store_data = store_data
        self.products = store_data.get('products', [])
        self.collections = store_data.get('collections', [])
        
    def estimate_traffic(self) -> Dict:
        """Generate traffic estimate with confidence score"""
        signals = self._collect_signals()
        estimate = self._calculate_estimate(signals)
        
        return {
            'monthly_visitors': estimate['visitors'],
            'daily_visitors': estimate['visitors'] // 30,
            'confidence': estimate['confidence'],
            'signals_used': signals,
            'traffic_tier': self._classify_tier(estimate['visitors']),
            'estimated_at': datetime.now().isoformat()
        }
    
    def _collect_signals(self) -> Dict:
        """Collect all available traffic signals"""
        signals = {
            'product_count': len(self.products),
            'collection_count': len(self.collections),
            'total_reviews': 0,
            'avg_reviews_per_product': 0,
            'products_with_reviews': 0,
            'recent_products': 0,  # products added in last 90 days
            'high_variant_products': 0,  # products with 10+ variants
            'price_range': {'min': float('inf'), 'max': 0},
        }
        
        review_counts = []
        prices = []
        now = datetime.now()
        ninety_days_ago = now - timedelta(days=90)
        
        for product in self.products:
            # Review signals
            review_count = self._extract_review_count(product)
            if review_count > 0:
                signals['total_reviews'] += review_count
                signals['products_with_reviews'] += 1
                review_counts.append(review_count)
            
            # Recency signals
            created_at = product.get('created_at', '')
            if created_at:
                try:
                    created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created > ninety_days_ago:
                        signals['recent_products'] += 1
                except:
                    pass
            
            # Variant signals (high variants = popular/active store)
            variants = product.get('variants', [])
            if len(variants) >= 10:
                signals['high_variant_products'] += 1
            
            # Price signals
            if variants:
                price = float(variants[0].get('price', 0))
                prices.append(price)
                signals['price_range']['min'] = min(signals['price_range']['min'], price)
                signals['price_range']['max'] = max(signals['price_range']['max'], price)
        
        if review_counts:
            signals['avg_reviews_per_product'] = statistics.mean(review_counts)
        
        if prices:
            signals['avg_price'] = statistics.mean(prices)
            signals['median_price'] = statistics.median(prices)
        
        return signals
    
    def _extract_review_count(self, product: Dict) -> int:
        """Extract review count from product data"""
        # Check common review app patterns in tags/metafields
        tags = product.get('tags', [])
        for tag in tags:
            if 'reviews:' in tag.lower():
                match = re.search(r'(\d+)', tag)
                if match:
                    return int(match.group(1))
        
        # Check title for review mentions
        title = product.get('title', '')
        review_match = re.search(r'\((\d+)\s*reviews?\)', title, re.I)
        if review_match:
            return int(review_match.group(1))
        
        return 0
    
    def _calculate_estimate(self, signals: Dict) -> Dict:
        """Calculate traffic estimate from signals"""
        estimates = []
        confidence_factors = []
        
        # Signal 1: Review-based estimate (most reliable)
        if signals['total_reviews'] > 0:
            review_estimate = signals['total_reviews'] * self.REVIEW_MULTIPLIER
            estimates.append(review_estimate)
            confidence_factors.append(0.4)  # 40% weight
        
        # Signal 2: Product count baseline
        product_estimate = signals['product_count'] * self.PRODUCT_BASE_TRAFFIC
        estimates.append(product_estimate)
        confidence_factors.append(0.2)  # 20% weight
        
        # Signal 3: Collection-based estimate
        if signals['collection_count'] > 0:
            collection_estimate = signals['collection_count'] * self.COLLECTION_MULTIPLIER
            estimates.append(collection_estimate)
            confidence_factors.append(0.15)  # 15% weight
        
        # Signal 4: Activity multiplier (recent products = active store)
        if signals['recent_products'] > 0:
            activity_multiplier = 1 + (signals['recent_products'] / signals['product_count'])
            activity_estimate = product_estimate * activity_multiplier
            estimates.append(activity_estimate)
            confidence_factors.append(0.15)  # 15% weight
        
        # Signal 5: Variant complexity (high variants = established store)
        if signals['high_variant_products'] > 0:
            variant_boost = signals['high_variant_products'] * 300
            estimates.append(variant_boost)
            confidence_factors.append(0.1)  # 10% weight
        
        # Weighted average
        if estimates:
            # Normalize confidence factors
            total_weight = sum(confidence_factors)
            normalized_weights = [w / total_weight for w in confidence_factors]
            
            weighted_estimate = sum(e * w for e, w in zip(estimates, normalized_weights))
            confidence = min(total_weight, 1.0) * 100  # max 100%
        else:
            weighted_estimate = 1000  # fallback minimum
            confidence = 10
        
        return {
            'visitors': int(weighted_estimate),
            'confidence': round(confidence, 1)
        }
    
    def _classify_tier(self, monthly_visitors: int) -> str:
        """Classify traffic tier"""
        if monthly_visitors < 1000:
            return 'Micro (< 1K/mo)'
        elif monthly_visitors < 10000:
            return 'Small (1K-10K/mo)'
        elif monthly_visitors < 50000:
            return 'Medium (10K-50K/mo)'
        elif monthly_visitors < 200000:
            return 'Large (50K-200K/mo)'
        else:
            return 'Enterprise (200K+/mo)'
    
    def compare_traffic(self, other_stores: List[Dict]) -> Dict:
        """Compare traffic estimates across multiple stores"""
        all_estimates = [self.estimate_traffic()]
        
        for store_data in other_stores:
            estimator = TrafficEstimator(store_data)
            all_estimates.append(estimator.estimate_traffic())
        
        # Rank by traffic
        ranked = sorted(all_estimates, key=lambda x: x['monthly_visitors'], reverse=True)
        
        return {
            'ranked_stores': ranked,
            'total_stores': len(ranked),
            'avg_traffic': statistics.mean([s['monthly_visitors'] for s in ranked]),
            'median_traffic': statistics.median([s['monthly_visitors'] for s in ranked])
        }
