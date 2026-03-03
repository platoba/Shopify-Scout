"""HTML report generator for Shopify Scout analysis.

Generates rich, self-contained HTML reports with:
- Store overview cards
- Price distribution charts (CSS-only)
- Category breakdown
- Competitive comparison tables
- Trend signals
- Export-ready format
"""
import html
from datetime import datetime
from typing import Optional


def generate_html_report(analysis: dict, store_data: Optional[dict] = None) -> str:
    """Generate a complete HTML report for a store analysis."""
    domain = analysis.get("domain", "unknown")
    now = datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections = [
        _header(domain, now),
        _overview_card(analysis),
        _price_distribution(analysis.get("prices", {})),
        _category_breakdown(analysis.get("categories", {})),
        _tag_cloud(analysis.get("tags", {})),
        _vendor_table(analysis.get("vendors", {})),
        _trend_section(analysis.get("trend", {})),
        _score_card(analysis.get("score", {})),
        _footer(domain),
    ]

    return _wrap_html(domain, "\n".join(sections))


def generate_comparison_report(stores: list[dict]) -> str:
    """Generate comparison report for multiple stores."""
    now = datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    domains = [s.get("domain", "?") for s in stores]

    sections = [
        _comparison_header(domains, now),
        _comparison_table(stores),
        _price_comparison_bars(stores),
        _category_overlap(stores),
        _footer("comparison"),
    ]

    return _wrap_html("Store Comparison", "\n".join(sections))


def generate_trend_report_html(trend_data: dict) -> str:
    """Generate HTML trend report from trend detector data."""
    now = datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    days = trend_data.get("period_days", 14)

    sections = [
        f'<div class="header"><h1>📊 Trend Report ({days} days)</h1>'
        f'<p class="subtitle">Generated: {now}</p></div>',
        _hot_categories_section(trend_data.get("hot_categories", [])),
        _trending_tags_section(trend_data.get("trending_tags", [])),
        _vendor_landscape_section(trend_data.get("top_vendors", [])),
        _footer("trends"),
    ]

    return _wrap_html("Trend Report", "\n".join(sections))


def _wrap_html(title: str, body: str) -> str:
    """Wrap content in HTML document with embedded CSS."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shopify Scout - {html.escape(title)}</title>
<style>
:root {{
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #c9d1d9; --heading: #f0f6fc; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922;
    --purple: #bc8cff; --orange: #f0883e;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: var(--bg); color: var(--text); padding: 24px; max-width: 1200px; margin: 0 auto; }}
.header {{ text-align: center; margin-bottom: 32px; padding: 24px; background: var(--card);
           border-radius: 12px; border: 1px solid var(--border); }}
h1 {{ color: var(--heading); font-size: 28px; margin-bottom: 8px; }}
h2 {{ color: var(--heading); font-size: 20px; margin-bottom: 16px; padding-bottom: 8px;
      border-bottom: 1px solid var(--border); }}
.subtitle {{ color: var(--accent); font-size: 14px; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px;
         padding: 20px; margin-bottom: 20px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }}
.stat {{ text-align: center; padding: 16px; background: var(--bg); border-radius: 8px; }}
.stat-value {{ font-size: 28px; font-weight: 700; color: var(--accent); }}
.stat-label {{ font-size: 12px; color: var(--text); margin-top: 4px; }}
.bar {{ height: 24px; border-radius: 4px; margin: 4px 0; display: flex; align-items: center;
        padding: 0 8px; font-size: 12px; color: var(--heading); min-width: 40px; }}
.bar-container {{ margin-bottom: 8px; }}
.bar-label {{ font-size: 13px; margin-bottom: 2px; display: flex; justify-content: space-between; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
th {{ text-align: left; padding: 10px 12px; font-size: 12px; text-transform: uppercase;
     color: var(--accent); border-bottom: 2px solid var(--border); }}
td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 14px; }}
tr:hover {{ background: rgba(88, 166, 255, 0.05); }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px;
          font-weight: 600; margin-left: 6px; }}
.badge-hot {{ background: rgba(248,81,73,0.2); color: var(--red); }}
.badge-warm {{ background: rgba(210,153,34,0.2); color: var(--yellow); }}
.badge-cool {{ background: rgba(63,185,80,0.2); color: var(--green); }}
.tag {{ display: inline-block; padding: 4px 10px; margin: 3px; border-radius: 16px;
        background: rgba(88,166,255,0.1); color: var(--accent); font-size: 12px; }}
.score-ring {{ width: 100px; height: 100px; border-radius: 50%; display: flex; align-items: center;
               justify-content: center; font-size: 32px; font-weight: 700; margin: 0 auto 8px; }}
.footer {{ text-align: center; padding: 20px; font-size: 12px; color: #484f58; margin-top: 32px; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _header(domain: str, timestamp: str) -> str:
    return f'''<div class="header">
<h1>🔍 Shopify Scout Report</h1>
<p style="font-size:20px; color: var(--heading); margin: 8px 0;">{html.escape(domain)}</p>
<p class="subtitle">Generated: {timestamp}</p>
</div>'''


def _overview_card(analysis: dict) -> str:
    pc = analysis.get("product_count", 0)
    prices = analysis.get("prices", {})
    cats = len(analysis.get("categories", {}))
    vendors = len(analysis.get("vendors", {}))

    return f'''<div class="card">
<h2>📋 Overview</h2>
<div class="grid">
<div class="stat"><div class="stat-value">{pc}</div><div class="stat-label">Products</div></div>
<div class="stat"><div class="stat-value">{cats}</div><div class="stat-label">Categories</div></div>
<div class="stat"><div class="stat-value">{vendors}</div><div class="stat-label">Vendors</div></div>
<div class="stat"><div class="stat-value">${prices.get("avg", 0):.0f}</div><div class="stat-label">Avg Price</div></div>
<div class="stat"><div class="stat-value">${prices.get("min", 0):.0f}</div><div class="stat-label">Min Price</div></div>
<div class="stat"><div class="stat-value">${prices.get("max", 0):.0f}</div><div class="stat-label">Max Price</div></div>
</div></div>'''


def _price_distribution(prices: dict) -> str:
    if not prices:
        return ""
    p25 = prices.get("p25", 0)
    median = prices.get("median", 0)
    p75 = prices.get("p75", 0)
    mx = prices.get("max", 1) or 1

    bars = [
        ("Budget (< P25)", p25, "var(--green)"),
        ("Mid-range (P25-Median)", median - p25, "var(--accent)"),
        ("Premium (Median-P75)", p75 - median, "var(--purple)"),
        ("Luxury (> P75)", mx - p75, "var(--orange)"),
    ]

    bar_html = ""
    for label, value, color in bars:
        width = max(5, min(100, (value / mx) * 100))
        bar_html += f'''<div class="bar-container">
<div class="bar-label"><span>{label}</span><span>${value:.0f}</span></div>
<div class="bar" style="width:{width}%; background:{color};">${value:.0f}</div>
</div>\n'''

    return f'''<div class="card">
<h2>💰 Price Distribution</h2>
<div class="grid">
<div class="stat"><div class="stat-value">${p25:.0f}</div><div class="stat-label">P25</div></div>
<div class="stat"><div class="stat-value">${median:.0f}</div><div class="stat-label">Median</div></div>
<div class="stat"><div class="stat-value">${p75:.0f}</div><div class="stat-label">P75</div></div>
</div>
{bar_html}
</div>'''


def _category_breakdown(categories: dict) -> str:
    if not categories:
        return ""
    total = sum(categories.values()) or 1
    rows = ""
    colors = ["var(--accent)", "var(--green)", "var(--purple)",
              "var(--orange)", "var(--yellow)", "var(--red)"]
    for i, (cat, count) in enumerate(list(categories.items())[:15]):
        pct = (count / total) * 100
        color = colors[i % len(colors)]
        rows += f'''<div class="bar-container">
<div class="bar-label"><span>{html.escape(cat)}</span><span>{count} ({pct:.0f}%)</span></div>
<div class="bar" style="width:{pct}%; background:{color};">{count}</div>
</div>\n'''

    return f'<div class="card"><h2>📦 Categories</h2>{rows}</div>'


def _tag_cloud(tags: dict) -> str:
    if not tags:
        return ""
    top_tags = list(tags.items())[:30]
    tags_html = "".join(
        f'<span class="tag">{html.escape(tag)} ({c})</span>' for tag, c in top_tags
    )
    return f'<div class="card"><h2>🏷️ Product Tags</h2><div>{tags_html}</div></div>'


def _vendor_table(vendors: dict) -> str:
    if not vendors:
        return ""
    total = sum(vendors.values()) or 1
    rows = ""
    for vendor, count in list(vendors.items())[:10]:
        pct = (count / total) * 100
        rows += f"<tr><td>{html.escape(vendor)}</td><td>{count}</td><td>{pct:.1f}%</td></tr>\n"

    return f'''<div class="card"><h2>🏭 Vendors</h2>
<table><thead><tr><th>Vendor</th><th>Products</th><th>Share</th></tr></thead>
<tbody>{rows}</tbody></table></div>'''


def _trend_section(trend: dict) -> str:
    if not trend:
        return ""
    recent = trend.get("recent_products", 0)
    growth = trend.get("growth_rate", 0)
    arrow = "📈" if growth > 0 else "📉" if growth < 0 else "➡️"

    return f'''<div class="card"><h2>{arrow} Growth Trend</h2>
<div class="grid">
<div class="stat"><div class="stat-value">{recent}</div><div class="stat-label">New Products (30d)</div></div>
<div class="stat"><div class="stat-value">{growth:+.1f}%</div><div class="stat-label">Growth Rate</div></div>
</div></div>'''


def _score_card(score: dict) -> str:
    if not score:
        return ""
    s = score.get("score", 0)
    if s >= 80:
        color = "var(--green)"
        border_color = "rgba(63,185,80,0.3)"
    elif s >= 50:
        color = "var(--yellow)"
        border_color = "rgba(210,153,34,0.3)"
    else:
        color = "var(--red)"
        border_color = "rgba(248,81,73,0.3)"

    breakdown = score.get("breakdown", {})
    items = "".join(
        f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>"
        for k, v in breakdown.items()
    )

    return f'''<div class="card"><h2>⭐ Store Score</h2>
<div class="score-ring" style="border: 4px solid {color}; color: {color};">{s}</div>
<p style="text-align:center; color:{color};">/100</p>
{f'<table><tbody>{items}</tbody></table>' if items else ''}
</div>'''


def _comparison_header(domains: list, timestamp: str) -> str:
    names = ", ".join(html.escape(d) for d in domains[:5])
    return f'''<div class="header">
<h1>⚔️ Store Comparison</h1>
<p style="color: var(--heading); margin: 8px 0;">{names}</p>
<p class="subtitle">Generated: {timestamp}</p>
</div>'''


def _comparison_table(stores: list) -> str:
    if not stores:
        return ""
    headers = "<th>Metric</th>" + "".join(
        f"<th>{html.escape(s.get('domain', '?'))}</th>" for s in stores[:5]
    )

    metrics = [
        ("Products", "product_count"),
        ("Avg Price", "prices.avg"),
        ("Categories", "categories"),
        ("Score", "score.score"),
    ]

    rows = ""
    for label, key in metrics:
        cells = ""
        for s in stores[:5]:
            if "." in key:
                parts = key.split(".")
                val = s.get(parts[0], {})
                if isinstance(val, dict):
                    val = val.get(parts[1], "-")
                elif isinstance(val, (list, set)):
                    val = len(val)
            else:
                val = s.get(key, "-")
                if isinstance(val, dict):
                    val = len(val)
            if isinstance(val, float):
                val = f"${val:.0f}" if "price" in key.lower() else f"{val:.0f}"
            cells += f"<td>{val}</td>"
        rows += f"<tr><td><strong>{label}</strong></td>{cells}</tr>\n"

    return f'''<div class="card"><h2>📊 Comparison</h2>
<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>'''


def _price_comparison_bars(stores: list) -> str:
    if not stores:
        return ""
    colors = ["var(--accent)", "var(--green)", "var(--purple)",
              "var(--orange)", "var(--yellow)"]
    bars = ""
    max_price = max(
        (s.get("prices", {}).get("max", 0) for s in stores), default=100
    ) or 100

    for i, s in enumerate(stores[:5]):
        domain = s.get("domain", "?")
        prices = s.get("prices", {})
        avg = prices.get("avg", 0)
        color = colors[i % len(colors)]
        width = max(5, (avg / max_price) * 100)
        bars += f'''<div class="bar-container">
<div class="bar-label"><span>{html.escape(domain)}</span><span>${avg:.0f} avg</span></div>
<div class="bar" style="width:{width}%; background:{color};">${avg:.0f}</div>
</div>\n'''

    return f'<div class="card"><h2>💰 Price Comparison</h2>{bars}</div>'


def _category_overlap(stores: list) -> str:
    if len(stores) < 2:
        return ""
    all_cats = set()
    store_cats = {}
    for s in stores[:5]:
        cats = s.get("categories", {})
        if isinstance(cats, dict):
            store_cats[s.get("domain", "?")] = set(cats.keys())
            all_cats.update(cats.keys())
        elif isinstance(cats, list):
            store_cats[s.get("domain", "?")] = set(cats)
            all_cats.update(cats)

    if not all_cats:
        return ""

    headers = "<th>Category</th>" + "".join(
        f"<th>{html.escape(d)}</th>" for d in store_cats
    )

    rows = ""
    for cat in sorted(all_cats):
        cells = ""
        for d, cats in store_cats.items():
            cells += f"<td>{'✅' if cat in cats else '—'}</td>"
        rows += f"<tr><td>{html.escape(cat)}</td>{cells}</tr>\n"

    return f'''<div class="card"><h2>🔀 Category Overlap</h2>
<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>'''


def _hot_categories_section(categories: list) -> str:
    if not categories:
        return ""
    rows = ""
    for c in categories[:15]:
        badge_class = "badge-hot" if "HOT" in c.get("heat_score", "") else \
                      "badge-warm" if "WARM" in c.get("heat_score", "") else "badge-cool"
        rows += f"""<tr>
<td>{html.escape(c.get('category', ''))}</td>
<td>{c.get('store_count', 0)}</td>
<td>{c.get('product_count', 0)}</td>
<td>${c.get('avg_price', 0):.0f}</td>
<td>{c.get('price_range', '')}</td>
<td><span class="badge {badge_class}">{c.get('heat_score', '')}</span></td>
</tr>\n"""

    return f'''<div class="card"><h2>🔥 Hot Categories</h2>
<table><thead><tr><th>Category</th><th>Stores</th><th>Products</th>
<th>Avg Price</th><th>Range</th><th>Heat</th></tr></thead>
<tbody>{rows}</tbody></table></div>'''


def _trending_tags_section(tags: list) -> str:
    if not tags:
        return ""
    tags_html = ""
    for t in tags[:25]:
        size = min(20, 12 + t.get("count", 1))
        tags_html += (
            f'<span class="tag" style="font-size:{size}px;">'
            f'{html.escape(t["tag"])} ({t["count"]})</span>'
        )
    return f'<div class="card"><h2>🏷️ Trending Tags</h2><div>{tags_html}</div></div>'


def _vendor_landscape_section(vendors: list) -> str:
    if not vendors:
        return ""
    rows = ""
    for v in vendors[:15]:
        cats = ", ".join(v.get("categories", [])[:3])
        rows += f"""<tr>
<td>{html.escape(v.get('vendor', ''))}</td>
<td>{v.get('store_count', 0)}</td>
<td>{v.get('product_count', 0)}</td>
<td>${v.get('avg_price', 0):.0f}</td>
<td>{html.escape(cats)}</td>
</tr>\n"""

    return f'''<div class="card"><h2>🏭 Vendor Landscape</h2>
<table><thead><tr><th>Vendor</th><th>Stores</th><th>Products</th>
<th>Avg Price</th><th>Categories</th></tr></thead>
<tbody>{rows}</tbody></table></div>'''


def _footer(context: str) -> str:
    return '''<div class="footer">
<p>Generated by <strong>Shopify Scout</strong> v3.0.0 — AI-Powered Shopify Intelligence</p>
<p>🕷️ Powered by C-Line Crawler Engine</p>
</div>'''
