"""Tests for traffic estimator module"""
import pytest
from app.traffic_estimator import TrafficEstimator

def test_basic_estimation():
    """Test basic traffic estimation"""
    store_data = {
        'products': [
            {
                'id': 1,
                'title': 'Product 1 (50 reviews)',
                'variants': [{'price': '29.99'}],
                'created_at': '2026-02-01T00:00:00Z',
                'tags': []
            },
            {
                'id': 2,
                'title': 'Product 2',
                'variants': [{'price': '49.99'}],
                'created_at': '2026-01-01T00:00:00Z',
                'tags': ['reviews:30']
            }
        ],
        'collections': [
            {'id': 1, 'title': 'Collection 1'},
            {'id': 2, 'title': 'Collection 2'}
        ]
    }
    
    estimator = TrafficEstimator(store_data)
    result = estimator.estimate_traffic()
    
    assert 'monthly_visitors' in result
    assert 'confidence' in result
    assert 'traffic_tier' in result
    assert result['monthly_visitors'] > 0
    assert 0 <= result['confidence'] <= 100

def test_review_extraction():
    """Test review count extraction"""
    store_data = {
        'products': [
            {'title': 'Product (100 reviews)', 'variants': [{'price': '10'}], 'tags': []},
            {'title': 'Product', 'variants': [{'price': '10'}], 'tags': ['reviews:50']},
        ],
        'collections': []
    }
    
    estimator = TrafficEstimator(store_data)
    signals = estimator._collect_signals()
    
    assert signals['total_reviews'] == 150
    assert signals['products_with_reviews'] == 2

def test_traffic_tier_classification():
    """Test traffic tier classification"""
    estimator = TrafficEstimator({'products': [], 'collections': []})
    
    assert estimator._classify_tier(500) == 'Micro (< 1K/mo)'
    assert estimator._classify_tier(5000) == 'Small (1K-10K/mo)'
    assert estimator._classify_tier(30000) == 'Medium (10K-50K/mo)'
    assert estimator._classify_tier(100000) == 'Large (50K-200K/mo)'
    assert estimator._classify_tier(500000) == 'Enterprise (200K+/mo)'

def test_compare_traffic():
    """Test multi-store traffic comparison"""
    store1 = {
        'products': [{'title': 'P1 (100 reviews)', 'variants': [{'price': '10'}], 'tags': []}],
        'collections': []
    }
    store2 = {
        'products': [{'title': 'P2 (50 reviews)', 'variants': [{'price': '10'}], 'tags': []}],
        'collections': []
    }
    
    estimator = TrafficEstimator(store1)
    comparison = estimator.compare_traffic([store2])
    
    assert 'ranked_stores' in comparison
    assert len(comparison['ranked_stores']) == 2
    assert comparison['ranked_stores'][0]['monthly_visitors'] >= comparison['ranked_stores'][1]['monthly_visitors']
