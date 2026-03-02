"""CLI tool for Shopify Scout - command-line store analysis."""
import argparse
import sys
import json
import os
from app.scraper import fetch_store_data, normalize_domain
from app.analyzer import full_analysis
from app.comparator import compare_stores, format_comparison_text
from app.niche_analyzer import analyze_niche, format_niche_report
from app.exporter import export_report, export_comparison_csv


def cmd_analyze(args):
    """Analyze a single Shopify store."""
    domain = normalize_domain(args.domain)
    print(f"🔍 Fetching data from {domain}...")

    data = fetch_store_data(domain)
    if data["product_count"] == 0:
        print(f"❌ No products found for {domain}")
        return 1

    analysis = full_analysis(data)

    if args.format == "text":
        _print_analysis_text(analysis)
    else:
        output = export_report(analysis, fmt=args.format, filepath=args.output)
        if not args.output:
            print(output)
        else:
            print(f"✅ Report saved to {args.output}")

    return 0


def cmd_compare(args):
    """Compare multiple Shopify stores."""
    domains = [normalize_domain(d) for d in args.domains]
    if len(domains) < 2:
        print("❌ Need at least 2 stores to compare")
        return 1

    analyses = []
    for domain in domains:
        print(f"🔍 Fetching {domain}...")
        data = fetch_store_data(domain)
        if data["product_count"] > 0:
            analyses.append(full_analysis(data))
        else:
            print(f"⚠️ Skipping {domain} (no products)")

    if len(analyses) < 2:
        print("❌ Not enough valid stores for comparison")
        return 1

    comparison = compare_stores(analyses)

    if args.format == "text":
        print(format_comparison_text(comparison))
    elif args.format == "csv":
        output = export_comparison_csv(comparison, filepath=args.output)
        if not args.output:
            print(output)
    else:
        output = json.dumps(comparison, ensure_ascii=False, indent=2, default=str)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"✅ Comparison saved to {args.output}")
        else:
            print(output)

    return 0


def cmd_niche(args):
    """Analyze niche positioning of a store."""
    domain = normalize_domain(args.domain)
    print(f"🎯 Analyzing niche for {domain}...")

    data = fetch_store_data(domain)
    if data["product_count"] == 0:
        print(f"❌ No products found for {domain}")
        return 1

    analysis = full_analysis(data)
    niche = analyze_niche(analysis)

    if args.format == "text":
        print(format_niche_report(niche))
    else:
        output = json.dumps(niche, ensure_ascii=False, indent=2, default=str)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"✅ Niche report saved to {args.output}")
        else:
            print(output)

    return 0


def cmd_export(args):
    """Export store data in various formats."""
    domain = normalize_domain(args.domain)
    print(f"📦 Exporting {domain} as {args.format}...")

    data = fetch_store_data(domain)
    if data["product_count"] == 0:
        print(f"❌ No products found for {domain}")
        return 1

    analysis = full_analysis(data)

    if not args.output:
        ext_map = {"json": "json", "csv": "csv", "html": "html"}
        ext = ext_map.get(args.format, "json")
        args.output = f"reports/{domain.replace('.', '_')}.{ext}"

    output = export_report(analysis, fmt=args.format, filepath=args.output)
    print(f"✅ Exported to {args.output}")
    return 0


def cmd_batch(args):
    """Batch analyze multiple stores from a file."""
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        return 1

    with open(args.file) as f:
        domains = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"📋 Batch analyzing {len(domains)} stores...")
    results = []

    for i, domain in enumerate(domains, 1):
        domain = normalize_domain(domain)
        print(f"  [{i}/{len(domains)}] {domain}...")
        try:
            data = fetch_store_data(domain)
            if data["product_count"] > 0:
                analysis = full_analysis(data)
                results.append(analysis)
                print(f"    ✅ {data['product_count']} products, score {analysis.get('score', {}).get('score', '?')}")
            else:
                print(f"    ⚠️ No products found")
        except Exception as e:
            print(f"    ❌ Error: {e}")

    if results:
        output_dir = args.output_dir or "reports/batch"
        os.makedirs(output_dir, exist_ok=True)

        # Save individual reports
        for r in results:
            domain = r.get("domain", "unknown")
            filepath = os.path.join(output_dir, f"{domain.replace('.', '_')}.json")
            export_report(r, fmt="json", filepath=filepath)

        # Save summary
        summary_path = os.path.join(output_dir, "summary.json")
        summary = {
            "total": len(domains),
            "successful": len(results),
            "stores": [
                {
                    "domain": r.get("domain"),
                    "product_count": r.get("product_count"),
                    "score": r.get("score", {}).get("score"),
                    "avg_price": round(r.get("prices", {}).get("avg", 0), 2),
                }
                for r in results
            ],
        }
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n📊 Results: {len(results)}/{len(domains)} stores analyzed")
        print(f"📁 Reports saved to {output_dir}/")

    return 0


def _print_analysis_text(analysis: dict):
    """Print analysis as formatted text."""
    print(f"\n🔍 Store Analysis: {analysis.get('domain', '?')}")
    print(f"📦 Products: {analysis.get('product_count', 0)}")
    print(f"📊 Score: {analysis.get('score', {}).get('score', '?')}/10")
    print()

    prices = analysis.get("prices", {})
    if prices:
        print("💰 Prices:")
        print(f"  Min: ${prices.get('min', 0):.2f}")
        print(f"  Max: ${prices.get('max', 0):.2f}")
        print(f"  Avg: ${prices.get('avg', 0):.2f}")
        print(f"  Median: ${prices.get('median', 0):.2f}")
        print()

    categories = analysis.get("categories", {})
    if categories:
        print("🏷️ Categories:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat}: {count}")
        print()

    vendors = analysis.get("vendors", {})
    if vendors:
        print("🏭 Vendors:")
        for v, count in sorted(vendors.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {v}: {count}")
        print()

    reasons = analysis.get("score", {}).get("reasons", [])
    if reasons:
        print("📝 Score Reasons:")
        for r in reasons:
            print(f"  • {r}")


def main():
    parser = argparse.ArgumentParser(
        prog="shopify-scout",
        description="🔍 Shopify Scout - AI选品+竞品监控+多店对比工具",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 2.0.0")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze a Shopify store")
    p_analyze.add_argument("domain", help="Store domain (e.g. allbirds.com)")
    p_analyze.add_argument("-f", "--format", choices=["text", "json", "csv", "html"], default="text")
    p_analyze.add_argument("-o", "--output", help="Output file path")
    p_analyze.set_defaults(func=cmd_analyze)

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare multiple stores")
    p_compare.add_argument("domains", nargs="+", help="Store domains to compare")
    p_compare.add_argument("-f", "--format", choices=["text", "json", "csv"], default="text")
    p_compare.add_argument("-o", "--output", help="Output file path")
    p_compare.set_defaults(func=cmd_compare)

    # niche
    p_niche = subparsers.add_parser("niche", help="Niche analysis for a store")
    p_niche.add_argument("domain", help="Store domain")
    p_niche.add_argument("-f", "--format", choices=["text", "json"], default="text")
    p_niche.add_argument("-o", "--output", help="Output file path")
    p_niche.set_defaults(func=cmd_niche)

    # export
    p_export = subparsers.add_parser("export", help="Export store data")
    p_export.add_argument("domain", help="Store domain")
    p_export.add_argument("-f", "--format", choices=["json", "csv", "html"], default="json")
    p_export.add_argument("-o", "--output", help="Output file path")
    p_export.set_defaults(func=cmd_export)

    # batch
    p_batch = subparsers.add_parser("batch", help="Batch analyze from file")
    p_batch.add_argument("file", help="Text file with one domain per line")
    p_batch.add_argument("-d", "--output-dir", help="Output directory")
    p_batch.set_defaults(func=cmd_batch)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)


def cmd_traffic(args):
    """Estimate store traffic from public signals."""
    from app.traffic_estimator import TrafficEstimator
    
    domain = normalize_domain(args.domain)
    print(f"🔍 Fetching data from {domain}...")
    
    data = fetch_store_data(domain)
    if data["product_count"] == 0:
        print(f"❌ No products found for {domain}")
        return 1
    
    estimator = TrafficEstimator(data)
    result = estimator.estimate_traffic()
    
    print(f"\n📊 Traffic Estimate for {domain}")
    print(f"{'='*50}")
    print(f"Monthly Visitors: {result['monthly_visitors']:,}")
    print(f"Daily Visitors: {result['daily_visitors']:,}")
    print(f"Traffic Tier: {result['traffic_tier']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\n🔍 Signals Used:")
    for key, value in result['signals_used'].items():
        if isinstance(value, dict):
            print(f"  {key}: {json.dumps(value, indent=4)}")
        else:
            print(f"  {key}: {value}")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ Report saved to {args.output}")
    
    return 0

    # traffic
    p_traffic = subparsers.add_parser("traffic", help="Estimate store traffic")
    p_traffic.add_argument("domain", help="Store domain (e.g. allbirds.com)")
    p_traffic.add_argument("-o", "--output", help="Output JSON file path")
    p_traffic.set_defaults(func=cmd_traffic)
