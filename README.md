# Shopify Scout v2.0.0 🔍

AI-powered Shopify store analysis, competitive intelligence, and niche opportunity detection.

## Features

### Core Analysis
- 📊 **Store Analysis** - Full product catalog analysis with pricing, categories, vendors, and scoring
- 🔍 **Multi-Store Comparison** - Side-by-side competitive analysis with rankings and gap detection
- 🎯 **Niche Analysis** - Market positioning, opportunity scoring, and strategic recommendations
- 🔧 **Tech Stack Detection** - Identify Shopify themes, apps, payment gateways, and integrations

### Monitoring & Alerts
- 👁️ **Store Monitoring** - Track product changes with SQLite persistence
- 🔔 **Change Detection** - Alerts for new/removed products and price changes

### Export & Reporting
- 📄 **Multi-format Export** - JSON, CSV, HTML reports
- 📊 **HTML Reports** - Beautiful visual reports with charts and tag clouds
- 📋 **Batch Analysis** - Process multiple stores from file

### AI Features
- 🤖 **AI Advisor** - GPT-powered product selection advice
- 💡 **Smart Recommendations** - Actionable insights based on data analysis

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Analyze a store
shopify-scout analyze allbirds.com

# Compare stores
shopify-scout compare allbirds.com gymshark.com fashionnova.com

# Niche analysis
shopify-scout niche allbirds.com

# Export report
shopify-scout export allbirds.com -f html -o report.html

# Batch analyze
shopify-scout batch stores.txt -d reports/
```

## Telegram Bot

```bash
# Set environment variables
export BOT_TOKEN=your_telegram_bot_token
export OPENAI_API_KEY=your_openai_key

# Run bot
python bot.py
```

### Bot Commands
- `/start` - Welcome message
- `/scan <domain>` - Full store analysis
- `/compare <domain1> <domain2>` - Compare stores
- `/niche <domain>` - Niche analysis
- `/watch <domain>` - Monitor store changes
- `/unwatch <domain>` - Stop monitoring
- `/list` - List watched stores

## Docker

```bash
# Build and run
docker compose up -d

# Run tests
docker compose run --rm test
```

## Architecture

```
app/
├── analyzer.py        # Price/category/trend analysis engine
├── comparator.py      # Multi-store comparison engine
├── niche_analyzer.py  # Niche scoring & opportunity detection
├── tech_detector.py   # Theme/app/payment detection
├── exporter.py        # JSON/CSV/HTML export engine
├── scraper.py         # Shopify API scraper with retry
├── monitor.py         # SQLite-based store monitoring
├── ai_advisor.py      # AI-powered recommendations
├── telegram_bot.py    # Telegram bot handlers
├── cli.py             # CLI tool (5 commands)
└── config.py          # Environment configuration
```

## Testing

```bash
# Run all tests
make test

# With coverage
make test-cov

# Lint
make lint
```

## License

MIT
