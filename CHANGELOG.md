## v7.0.0 (2026-03-03)

### New Module: Inventory Monitor 📦
- **`inventory_monitor.py`** — 竞品库存监控+断货预警系统
  - 库存快照：拍摄竞品库存状态，记录每个variant的可用性和数量
  - 变化检测：对比两次快照，自动识别断货/补货/低库存事件
  - 断货预警：竞品断货时立即提醒，抓住市场空白期
  - 补货监控：竞品补货时通知，关注其价格和促销策略
  - 低库存预警：竞品库存≤10件时提醒，准备抢占市场
  - 健康度分析：评估整体库存管理水平（excellent/good/fair/poor）
  - 多格式报告：JSON报告 + 预警汇总
  - CLI命令：
    - `shopify-scout inventory-check <domain>` — 检查库存健康度
    - `shopify-scout inventory-compare <prev.json> <curr.json>` — 对比快照生成预警

### Use Cases
- 竞品监控：每日定时抓取竞品库存，发现断货机会
- 市场抢占：竞品断货时立即推广同类产品
- 补货跟踪：竞品补货后关注其价格变化
- 库存优化：学习竞品库存管理策略

### Testing
- 7 new test cases in `test_inventory_monitor.py` (100% pass rate)
- Snapshot capture and comparison validation
- Alert generation for out-of-stock/restocked/low-stock events
- Health score calculation (excellent/good/fair/poor)

## v6.0.0 (2026-03-02)

### New Module: Price Optimizer 💰
- **`price_optimizer.py`** — 竞品价格监控+自动降价建议引擎
  - 竞品价格分析：按类别匹配同类产品，计算市场均价/最低价/最高价
  - 智能定价策略：保守模式（略低于均价）vs 激进模式（比最低价再低5%）
  - 市场位置分析：premium/competitive/budget 三档定位
  - 紧急度评分：high/medium/low 优先级排序
  - 置信度评估：0-1 置信度评分
  - 多格式导出：JSON报告 + CSV批量导入表格
  - CLI命令：`shopify-scout optimize-pricing <own_domain> <competitor1> <competitor2> ...`

### Use Cases
- 电商运营：实时监控竞品价格，自动生成降价建议
- 价格战：激进模式快速抢占市场份额
- 利润优化：保守模式保持竞争力同时维持利润率
- 批量调价：CSV导出后直接导入Shopify后台

### Testing
- 4 new test cases in `test_price_optimizer.py` (100% pass rate)
- Competitive pricing analysis validation
- Aggressive vs conservative mode comparison
- Report generation and CSV export

## v5.0.0 (2026-03-02)

### New Module: Traffic Estimator 📊
- **`traffic_estimator.py`** — Heuristic-based traffic estimation engine
  - Multi-signal collection: review counts, product activity, variant complexity
  - Weighted algorithm for monthly visitor estimation with confidence scoring
  - Traffic tier classification (Micro → Enterprise)
  - Multi-store traffic comparison and ranking
  - CLI command: `shopify-scout traffic <domain>`
  
### Use Cases
- Competitive traffic analysis without third-party tools
- Product selection validation (traffic = market proof)
- Multi-store benchmarking (identify highest-traffic competitors)

### Testing
- 4 new test cases in `test_traffic_estimator.py` (100% pass rate)
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
