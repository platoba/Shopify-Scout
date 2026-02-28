# Changelog

## v4.0.0 (2026-03-01)

### New Modules
- **`seo_analyzer.py`** — Comprehensive SEO health analyzer for Shopify stores
  - Product title analysis (length, duplicates, empty checks)
  - Description quality scoring (HTML-stripped text analysis)
  - URL/handle structure validation (case, special chars, length)
  - Image alt text coverage audit
  - Tag/keyword density evaluation
  - Content freshness signals (6-month staleness detection)
  - Weighted multi-category scoring with letter grades (A+ to F)
  - Prioritized recommendations with severity levels
  - Cross-store SEO comparison and ranking

- **`social_proof.py`** — Social proof & conversion element detector
  - 5 detection categories: urgency, scarcity, social proof, trust, payment trust
  - 50+ regex patterns for conversion element discovery
  - Real inventory scarcity detection (low stock variants)
  - Image richness analysis (6+ images = higher conversion)
  - Conversion tactics analysis with used/unused mapping
  - Competitor benchmark: cross-store conversion comparison
  - Actionable recommendations for missing conversion elements
  - Coverage scoring with grade system

- **`pricing_intel.py`** — Competitive pricing intelligence engine
  - Price statistics (min/max/mean/median/stdev/range)
  - Pricing strategy detection (charm/round/discount-heavy/uniform/wide-range)
  - 4-tier price distribution (budget/mid/premium/luxury)
  - Discount analysis (rate, avg discount %, max discount)
  - Category-level pricing breakdown
  - Multi-store price ranking with market position detection
  - Cross-store category gap finder (expansion opportunities)
  - Similar product finder (title similarity matching with price diff)
  - Pricing opportunity alerts (brand erosion, price power signals)

### Tests
- Added 112 new tests across 3 test files
  - `test_seo_analyzer.py` — 47 tests (titles, descriptions, URLs, images, tags, freshness, scoring, comparison)
  - `test_social_proof.py` — 33 tests (urgency, scarcity, trust, payments, images, tactics, benchmark)
  - `test_pricing_intel.py` — 32 tests (loading, analysis, tiers, strategy, comparison, similar products)
- Total tests: 287 → 399

---

## v3.0.0 (2026-03-01)

### New Modules
- **`price_tracker.py`** — Price history tracking with SQLite persistence
  - Automatic price drop/spike alerts (10%/20% thresholds)
  - Price history per variant with currency support
  - Price summary with volatility analysis
  - Discount pattern detection (recurring sales)
  - Best-buy timing recommendations (strong_buy/buy/hold/wait)
  - Alert management (pending/notified lifecycle)
  - Data retention cleanup (90-day default)

- **`trend_detector.py`** — Cross-store trend detection engine
  - Hot category detection across multiple stores (heat scoring: HOT/WARM/RISING/COOL)
  - Trending tag analysis with store spread metrics
  - New product surge detection (launch signals)
  - Cross-store category comparison (overlap + unique niches)
  - Vendor landscape mapping
  - Comprehensive trend report generation

- **`inventory_tracker.py`** — Inventory & sell-through analysis
  - Variant-level stock tracking with event detection
  - Bestseller ranking by sell-through rate (velocity labels: VIRAL/HOT/FAST/STEADY/SLOW/DEAD)
  - Dead stock identification (no-sale detection)
  - Stockout frequency analysis (demand signals)
  - Restock pattern analysis
  - Comprehensive inventory summaries

- **`report_generator.py`** — Self-contained HTML report engine
  - Dark-theme responsive reports with embedded CSS
  - Store analysis reports (overview, prices, categories, tags, vendors, trends, scores)
  - Multi-store comparison reports (side-by-side tables, price bars, category overlap matrix)
  - Trend reports (hot categories, trending tags, vendor landscape)
  - XSS-safe HTML escaping
  - CSS-only bar charts and score rings

### Test Coverage
- 287 total tests (was 192) — **+95 new tests**
  - `test_price_tracker.py` — 30 tests (recording, alerts, history, patterns, timing)
  - `test_trend_detector.py` — 23 tests (signals, hot categories, tags, comparison, vendors)
  - `test_inventory_tracker.py` — 24 tests (inventory, events, bestsellers, dead stock, stockouts)
  - `test_report_generator.py` — 18 tests (HTML generation, comparison, trends, XSS)

## v2.0.0 (2026-02-27)
- Multi-store comparison engine
- Niche analyzer with market scoring
- Tech stack detector (Shopify theme/app detection)
- CSV/JSON/Markdown exporter
- Enhanced CLI with subcommands

## v1.0.0 (2026-02-27)
- Initial release: Shopify store scraper + analyzer + TG Bot
- SQLite monitoring with change detection
- AI-powered product advice
- Docker Compose + CI/CD
