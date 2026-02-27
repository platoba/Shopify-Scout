# Shopify Scout 🔍

AI-powered Shopify store analyzer, product research & competitor monitoring via Telegram Bot.

## Features

- 📊 **Deep Store Analysis** — products, pricing distribution (P25/P50/P75), categories, tags, vendors, launch trends
- 🧠 **AI Product Advice** — niche analysis, pricing strategy, opportunities, competitive scoring
- 📈 **Competitor Comparison** — side-by-side metrics with AI-powered differentiation advice
- ⭐ **Competitiveness Scoring** — automated 1-10 scoring with detailed reasoning
- 👀 **Persistent Monitoring** — SQLite-backed store tracking with change detection (new/removed products)
- 🔗 **Auto-detect** — just paste a Shopify URL, no commands needed

## Architecture

```
app/
├── config.py          # Environment-based configuration
├── scraper.py         # Shopify store scraper with retry/proxy support
├── analyzer.py        # Price/category/trend/score analysis engine
├── ai_advisor.py      # OpenAI-compatible AI product advice
├── monitor.py         # SQLite-backed store monitoring + change detection
└── telegram_bot.py    # Telegram bot command handlers
tests/
├── test_scraper.py    # Scraper unit tests
├── test_analyzer.py   # Analyzer unit tests (15 tests)
└── test_monitor.py    # Monitor unit tests (11 tests)
```

## Quick Start

```bash
git clone https://github.com/platoba/Shopify-Scout.git
cd Shopify-Scout
cp .env.example .env
# Edit .env with your BOT_TOKEN and OPENAI_API_KEY
pip install -r requirements.txt
python bot.py
```

### Docker

```bash
cp .env.example .env
# Edit .env
docker compose up -d
```

## Commands

| Command | Description |
|---------|-------------|
| `/scan <url>` | Full store analysis with pricing, categories, trends |
| `/advice <url>` | AI-powered product recommendations |
| `/compare <url1> <url2> ...` | Compare up to 5 stores with AI analysis |
| `/score <url>` | Quick competitiveness score (1-10) |
| `/watch <url>` | Add store to persistent monitoring |
| `/unwatch <url>` | Remove store from monitoring |
| `/watched` | List all monitored stores |

## How It Works

Uses Shopify's public `/products.json` endpoint (no API key needed) to analyze:
- Product count & pricing distribution (min/max/avg/median/quartiles)
- Category breakdown & popular tags
- Vendor analysis
- New product launch frequency (7d/30d/90d trends)
- Collection structure
- Automated competitiveness scoring

### Proxy Support

Set `PROXY_URL` in `.env` for SOCKS5/HTTP proxy support:
```
PROXY_URL=socks5://user:pass@host:port
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT

## 🔗 Related

- [MultiAffiliateTGBot](https://github.com/platoba/MultiAffiliateTGBot) — Affiliate link bot
- [AI-Listing-Writer](https://github.com/platoba/AI-Listing-Writer) — AI listing generator
- [Amazon-SP-API-Python](https://github.com/platoba/Amazon-SP-API-Python) — Amazon SP-API SDK
