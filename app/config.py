"""Configuration from environment variables."""
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# Scraper settings
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "15"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
PROXY_URL = os.environ.get("PROXY_URL", "")  # SOCKS5 or HTTP proxy

# Monitoring
MONITOR_DB = os.environ.get("MONITOR_DB", "data/monitor.db")
MONITOR_INTERVAL = int(os.environ.get("MONITOR_INTERVAL", "3600"))  # seconds

# Rate limiting
RATE_LIMIT_PER_USER = int(os.environ.get("RATE_LIMIT_PER_USER", "30"))  # per minute

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
