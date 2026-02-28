"""Multi-format export engine for Shopify Scout reports."""
import csv
import json
import io
import os
from datetime import datetime, timezone
from typing import Optional


def export_json(data: dict, filepath: Optional[str] = None) -> str:
    """Export analysis data as JSON.

    Args:
        data: Analysis data dict.
        filepath: Optional file path to write to.

    Returns:
        JSON string.
    """
    output = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if filepath:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output)
    return output


def export_csv(data: dict, filepath: Optional[str] = None) -> str:
    """Export product data as CSV.

    Args:
        data: Store data with 'products' list.
        filepath: Optional file path to write to.

    Returns:
        CSV string.
    """
    products = data.get("products", [])
    if not products:
        return ""

    output = io.StringIO()
    fieldnames = [
        "id", "title", "product_type", "vendor", "tags",
        "price_min", "price_max", "variant_count", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for p in products:
        variants = p.get("variants", [])
        prices = []
        for v in variants:
            try:
                price = float(v.get("price", 0))
                if price > 0:
                    prices.append(price)
            except (ValueError, TypeError):
                pass

        tags = p.get("tags", [])
        if isinstance(tags, list):
            tags_str = ", ".join(tags)
        else:
            tags_str = str(tags)

        writer.writerow({
            "id": p.get("id", ""),
            "title": p.get("title", ""),
            "product_type": p.get("product_type", ""),
            "vendor": p.get("vendor", ""),
            "tags": tags_str,
            "price_min": min(prices) if prices else 0,
            "price_max": max(prices) if prices else 0,
            "variant_count": len(variants),
            "created_at": p.get("created_at", ""),
        })

    csv_str = output.getvalue()
    if filepath:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(csv_str)
    return csv_str


def export_html(analysis: dict, filepath: Optional[str] = None) -> str:
    """Export full analysis as an HTML report.

    Args:
        analysis: Full analysis result dict.
        filepath: Optional file path to write to.

    Returns:
        HTML string.
    """
    domain = analysis.get("domain", "Unknown Store")
    prices = analysis.get("prices", {})
    categories = analysis.get("categories", {})
    vendors = analysis.get("vendors", {})
    tags = analysis.get("tags", {})
    score = analysis.get("score", {})
    trend = analysis.get("trend", {})

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build category rows
    cat_rows = ""
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        pct = round(count / sum(categories.values()) * 100, 1) if categories else 0
        cat_rows += f"<tr><td>{cat}</td><td>{count}</td><td>{pct}%</td></tr>\n"

    # Build vendor rows
    vendor_rows = ""
    for v, count in sorted(vendors.items(), key=lambda x: x[1], reverse=True)[:15]:
        vendor_rows += f"<tr><td>{v}</td><td>{count}</td></tr>\n"

    # Build tag cloud
    sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:30]
    tag_items = ""
    max_count = sorted_tags[0][1] if sorted_tags else 1
    for tag, count in sorted_tags:
        size = max(12, min(36, int(14 + (count / max_count) * 22)))
        opacity = max(0.4, min(1.0, 0.3 + count / max_count * 0.7))
        tag_items += (
            f'<span style="font-size:{size}px;opacity:{opacity};'
            f'margin:4px;display:inline-block">{tag} ({count})</span>\n'
        )

    # Price distribution bars
    price_bars = ""
    if prices:
        ranges = _build_price_ranges(analysis.get("products", []))
        max_bar = max(ranges.values()) if ranges else 1
        for label, count in ranges.items():
            width = max(2, int(count / max_bar * 300))
            price_bars += (
                f'<div style="margin:2px 0">'
                f'<span style="display:inline-block;width:100px">{label}</span>'
                f'<span style="display:inline-block;width:{width}px;height:20px;'
                f'background:#4CAF50;margin-right:8px"></span>'
                f'{count}</div>\n'
            )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shopify Scout Report - {domain}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }}
  h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
  h2 {{ color: #333; margin-top: 30px; }}
  .card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 15px 0;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .score {{ font-size: 48px; font-weight: bold; color: #1a73e8; }}
  .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
  .metric .value {{ font-size: 28px; font-weight: bold; color: #1a73e8; }}
  .metric .label {{ font-size: 12px; color: #666; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #eee; }}
  th {{ background: #f1f3f4; font-weight: 600; }}
  .tag-cloud {{ padding: 15px; line-height: 2; }}
  .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee;
             font-size: 12px; color: #999; }}
</style>
</head>
<body>
<h1>🔍 Shopify Scout Report</h1>
<p style="color:#666">Store: <strong>{domain}</strong> | Generated: {now}</p>

<div class="card">
  <div class="metric">
    <div class="value">{score.get("score", "?")}</div>
    <div class="label">Store Score</div>
  </div>
  <div class="metric">
    <div class="value">{analysis.get("product_count", 0)}</div>
    <div class="label">Products</div>
  </div>
  <div class="metric">
    <div class="value">{len(categories)}</div>
    <div class="label">Categories</div>
  </div>
  <div class="metric">
    <div class="value">{len(vendors)}</div>
    <div class="label">Vendors</div>
  </div>
  <div class="metric">
    <div class="value">${prices.get("avg", 0):.0f}</div>
    <div class="label">Avg Price</div>
  </div>
</div>

<h2>💰 Price Analysis</h2>
<div class="card">
  <div class="metric">
    <div class="value">${prices.get("min", 0):.2f}</div>
    <div class="label">Min</div>
  </div>
  <div class="metric">
    <div class="value">${prices.get("median", 0):.2f}</div>
    <div class="label">Median</div>
  </div>
  <div class="metric">
    <div class="value">${prices.get("avg", 0):.2f}</div>
    <div class="label">Average</div>
  </div>
  <div class="metric">
    <div class="value">${prices.get("max", 0):.2f}</div>
    <div class="label">Max</div>
  </div>
  <h3>Distribution</h3>
  {price_bars}
</div>

<h2>🏷️ Categories</h2>
<div class="card">
  <table>
    <tr><th>Category</th><th>Count</th><th>%</th></tr>
    {cat_rows}
  </table>
</div>

<h2>🏭 Vendors</h2>
<div class="card">
  <table>
    <tr><th>Vendor</th><th>Products</th></tr>
    {vendor_rows}
  </table>
</div>

<h2>🏷️ Tag Cloud</h2>
<div class="card tag-cloud">
  {tag_items}
</div>

<h2>📈 Trends</h2>
<div class="card">
  <p>New products (30d): <strong>{trend.get("new_30d", "N/A")}</strong></p>
  <p>New products (90d): <strong>{trend.get("new_90d", "N/A")}</strong></p>
</div>

<div class="footer">
  Generated by Shopify Scout v2.0.0 | github.com/platoba/Shopify-Scout
</div>
</body>
</html>"""

    if filepath:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
    return html


def _build_price_ranges(products: list) -> dict:
    """Build price range distribution."""
    ranges = {
        "$0-10": 0, "$10-25": 0, "$25-50": 0,
        "$50-100": 0, "$100-200": 0, "$200+": 0,
    }

    for p in products:
        for v in p.get("variants", []):
            try:
                price = float(v.get("price", 0))
                if price <= 0:
                    continue
                if price < 10:
                    ranges["$0-10"] += 1
                elif price < 25:
                    ranges["$10-25"] += 1
                elif price < 50:
                    ranges["$25-50"] += 1
                elif price < 100:
                    ranges["$50-100"] += 1
                elif price < 200:
                    ranges["$100-200"] += 1
                else:
                    ranges["$200+"] += 1
            except (ValueError, TypeError):
                pass

    # Remove empty ranges
    return {k: v for k, v in ranges.items() if v > 0}


def export_comparison_csv(comparison: dict, filepath: Optional[str] = None) -> str:
    """Export store comparison as CSV."""
    ranking = comparison.get("ranking", [])
    if not ranking:
        return ""

    output = io.StringIO()
    fieldnames = ["rank", "domain", "composite_score", "product_count", "store_score"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in ranking:
        writer.writerow(r)

    csv_str = output.getvalue()
    if filepath:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(csv_str)
    return csv_str


def export_report(
    analysis: dict,
    fmt: str = "json",
    filepath: Optional[str] = None,
) -> str:
    """Universal export dispatcher.

    Args:
        analysis: Analysis data.
        fmt: Format - 'json', 'csv', 'html'.
        filepath: Optional output path.

    Returns:
        Exported string content.
    """
    fmt = fmt.lower().strip()
    if fmt == "csv":
        return export_csv(analysis, filepath)
    elif fmt == "html":
        return export_html(analysis, filepath)
    else:
        return export_json(analysis, filepath)
