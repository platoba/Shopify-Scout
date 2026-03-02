"""
Tests for Price Optimizer
"""
import pytest
from app.price_optimizer import PriceOptimizer, PriceRecommendation

@pytest.fixture
def optimizer():
    return PriceOptimizer(target_margin=0.3, aggressive_mode=False)

@pytest.fixture
def aggressive_optimizer():
    return PriceOptimizer(target_margin=0.3, aggressive_mode=True)

@pytest.fixture
def sample_own_products():
    return [
        {
            'id': '1001',
            'title': 'Wireless Mouse',
            'price': '29.99',
            'product_type': 'Electronics'
        },
        {
            'id': '1002',
            'title': 'USB Cable',
            'price': '9.99',
            'product_type': 'Accessories'
        },
        {
            'id': '1003',
            'title': 'Laptop Stand',
            'price': '49.99',
            'product_type': 'Accessories'
        }
    ]

@pytest.fixture
def sample_competitor_products():
    return [
        {'title': 'Gaming Mouse', 'price': '24.99', 'product_type': 'Electronics'},
        {'title': 'Office Mouse', 'price': '19.99', 'product_type': 'Electronics'},
        {'title': 'USB-C Cable', 'price': '7.99', 'product_type': 'Accessories'},
        {'title': 'Lightning Cable', 'price': '8.99', 'product_type': 'Accessories'},
        {'title': 'Adjustable Stand', 'price': '39.99', 'product_type': 'Accessories'}
    ]

def test_competitive_pricing_analysis(optimizer, sample_own_products, sample_competitor_products):
    """测试竞品价格分析"""
    recommendations = optimizer.analyze_competitive_pricing(
        sample_own_products,
        sample_competitor_products
    )
    
    assert len(recommendations) > 0
    assert all(isinstance(rec, PriceRecommendation) for rec in recommendations)
    
    # 验证价格建议合理性
    for rec in recommendations:
        assert rec.recommended_price > 0
        assert rec.confidence > 0 and rec.confidence <= 1
        assert rec.urgency in ['high', 'medium', 'low']
        assert rec.market_position in ['premium', 'competitive', 'budget']

def test_aggressive_mode(aggressive_optimizer, sample_own_products, sample_competitor_products):
    """测试激进定价模式"""
    recommendations = aggressive_optimizer.analyze_competitive_pricing(
        sample_own_products,
        sample_competitor_products
    )
    
    # 激进模式应该给出更低的价格建议
    for rec in recommendations:
        assert rec.recommended_price < rec.current_price
        assert rec.urgency == 'high'

def test_pricing_report_generation(optimizer, sample_own_products, sample_competitor_products):
    """测试定价报告生成"""
    recommendations = optimizer.analyze_competitive_pricing(
        sample_own_products,
        sample_competitor_products
    )
    
    report = optimizer.generate_pricing_report(recommendations)
    
    assert 'summary' in report
    assert 'recommendations' in report
    assert 'generated_at' in report
    assert report['summary']['total_products'] == len(recommendations)

def test_csv_export(optimizer, sample_own_products, sample_competitor_products, tmp_path):
    """测试CSV导出"""
    recommendations = optimizer.analyze_competitive_pricing(
        sample_own_products,
        sample_competitor_products
    )
    
    output_file = tmp_path / "pricing_recommendations.csv"
    optimizer.export_csv(recommendations, str(output_file))
    
    assert output_file.exists()
    content = output_file.read_text()
    assert 'Product ID' in content
    assert 'Recommended Price' in content
