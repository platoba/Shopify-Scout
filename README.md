# Shopify Scout

🔍 AI-powered Shopify store analyzer & product research tool via Telegram Bot.

## Features

- 📊 Store analysis: products, pricing, categories, tags
- 🧠 AI product advice: niche analysis, pricing strategy, opportunities
- 📈 Competitor comparison: side-by-side store metrics
- 👀 Store monitoring: track competitor changes
- 🔗 Auto-detect: just paste a Shopify URL

## Quick Start

```bash
git clone https://github.com/platoba/Shopify-Scout.git
cd Shopify-Scout
cp .env.example .env
pip install -r requirements.txt
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/scan <url>` | Full store analysis |
| `/advice <url>` | AI product recommendations |
| `/compare <url1> <url2>` | Compare stores |
| `/watch <url>` | Monitor store |

## How It Works

Uses Shopify's public `/products.json` endpoint (no API key needed) to analyze:
- Product count & pricing distribution
- Category breakdown & popular tags
- New product launches
- Collection structure

## License

MIT

## 🔗 Related

- [MultiAffiliateTGBot](https://github.com/platoba/MultiAffiliateTGBot) - Affiliate link bot
- [AI-Listing-Writer](https://github.com/platoba/AI-Listing-Writer) - AI listing generator
- [Amazon-SP-API-Python](https://github.com/platoba/Amazon-SP-API-Python) - Amazon SP-API SDK
