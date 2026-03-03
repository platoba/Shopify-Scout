"""
CLI command for inventory monitoring
"""
import json
from app.scraper import ShopifyScraper
from app.inventory_monitor import InventoryMonitor


def cmd_inventory_check(args):
    """Check inventory health for a store."""
    from app.cli import normalize_domain
    
    domain = normalize_domain(args.domain)
    print(f"🔍 Fetching inventory data from {domain}...")
    
    scraper = ShopifyScraper()
    products = scraper.scrape_products(domain)
    
    if not products:
        print(f"❌ No products found for {domain}")
        return 1
    
    monitor = InventoryMonitor()
    
    # Take snapshot
    snapshots = monitor.take_snapshot(products)
    print(f"📸 Captured {len(snapshots)} variant snapshots")
    
    # Analyze health
    health = monitor.analyze_inventory_health(products)
    
    print(f"\n📊 Inventory Health Report")
    print(f"{'='*50}")
    print(f"Total Variants: {health['total_variants']}")
    print(f"In Stock: {health['in_stock']} ({health['in_stock_rate']}%)")
    print(f"Out of Stock: {health['out_of_stock']} ({health['out_of_stock_rate']}%)")
    print(f"Low Stock: {health['low_stock']}")
    print(f"Unknown: {health['unknown']}")
    print(f"\n🏥 Health Score: {health['health_score'].upper()}")
    print(f"💡 {health['health_message']}")
    
    if args.output:
        report = {
            "domain": domain,
            "health": health,
            "snapshots": [
                {
                    "product_title": s.product_title,
                    "variant_title": s.variant_title,
                    "available": s.available,
                    "inventory_quantity": s.inventory_quantity
                }
                for s in snapshots
            ]
        }
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✅ Report saved to {args.output}")
    
    return 0


def cmd_inventory_compare(args):
    """Compare inventory snapshots to detect changes."""
    print(f"🔍 Comparing inventory snapshots...")
    
    # Load previous snapshot
    try:
        with open(args.previous, 'r') as f:
            prev_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Previous snapshot not found: {args.previous}")
        return 1
    
    # Load current snapshot
    try:
        with open(args.current, 'r') as f:
            curr_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Current snapshot not found: {args.current}")
        return 1
    
    # Convert to InventorySnapshot objects
    from app.inventory_monitor import InventorySnapshot
    
    prev_snapshots = [
        InventorySnapshot(
            product_id=s.get("product_id", ""),
            product_title=s["product_title"],
            variant_id=s.get("variant_id", ""),
            variant_title=s["variant_title"],
            available=s["available"],
            inventory_quantity=s.get("inventory_quantity"),
            timestamp=prev_data.get("timestamp", "")
        )
        for s in prev_data.get("snapshots", [])
    ]
    
    curr_snapshots = [
        InventorySnapshot(
            product_id=s.get("product_id", ""),
            product_title=s["product_title"],
            variant_id=s.get("variant_id", ""),
            variant_title=s["variant_title"],
            available=s["available"],
            inventory_quantity=s.get("inventory_quantity"),
            timestamp=curr_data.get("timestamp", "")
        )
        for s in curr_data.get("snapshots", [])
    ]
    
    monitor = InventoryMonitor()
    alerts = monitor.compare_snapshots(prev_snapshots, curr_snapshots)
    
    if not alerts:
        print("✅ No inventory changes detected")
        return 0
    
    print(f"\n🚨 {len(alerts)} Inventory Alerts")
    print(f"{'='*50}")
    
    for alert in alerts:
        emoji = "🔴" if alert.urgency == "high" else "🟡"
        print(f"\n{emoji} {alert.alert_type.upper()}")
        print(f"Product: {alert.product_title}")
        print(f"Variant: {alert.variant_title}")
        print(f"Previous: {alert.previous_quantity} → Current: {alert.current_quantity}")
        print(f"💡 {alert.recommendation}")
    
    if args.output:
        health = curr_data.get("health", {})
        report = monitor.export_report(alerts, health)
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✅ Alert report saved to {args.output}")
    
    return 0
