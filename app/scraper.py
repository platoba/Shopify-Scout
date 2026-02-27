"""Shopify store scraper with retry logic and proxy support."""
import time
import logging
import requests
from urllib.parse import urlparse
from typing import Optional
from app.config import REQUEST_TIMEOUT, MAX_RETRIES, PROXY_URL, USER_AGENT

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def _get_proxies() -> dict:
    if PROXY_URL:
        return {"http": PROXY_URL, "https": PROXY_URL}
    return {}


def _request_with_retry(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
    """HTTP GET with exponential backoff retry."""
    proxies = _get_proxies()
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, proxies=proxies, timeout=timeout)
            if r.status_code == 429:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited on {url}, waiting {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt+1}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return None


def normalize_domain(url: str) -> str:
    """Extract clean domain from URL or domain string."""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    return domain.lower().rstrip("/")


def fetch_products(domain: str, limit: int = 250) -> list:
    """Fetch products from Shopify's public products.json endpoint."""
    all_products = []
    page = 1
    while True:
        url = f"https://{domain}/products.json?limit={min(limit, 250)}&page={page}"
        r = _request_with_retry(url)
        if not r:
            break
        products = r.json().get("products", [])
        if not products:
            break
        all_products.extend(products)
        if len(products) < 250 or len(all_products) >= limit:
            break
        page += 1
        time.sleep(0.5)  # polite delay
    return all_products


def fetch_collections(domain: str) -> list:
    """Fetch collections from Shopify's public endpoint."""
    url = f"https://{domain}/collections.json"
    r = _request_with_retry(url)
    if r:
        return r.json().get("collections", [])
    return []


def fetch_meta(domain: str) -> dict:
    """Fetch store meta.json for theme/tech info."""
    url = f"https://{domain}/meta.json"
    r = _request_with_retry(url)
    if r:
        return r.json()
    return {}


def fetch_store_data(store_url: str) -> dict:
    """Full store data fetch: products + collections + meta."""
    domain = normalize_domain(store_url)
    logger.info(f"Scanning store: {domain}")

    result = {"domain": domain, "products": [], "collections": [], "meta": {}}

    products = fetch_products(domain)
    result["products"] = products
    result["product_count"] = len(products)

    collections = fetch_collections(domain)
    result["collections"] = [{"title": c.get("title", ""), "id": c.get("id")} for c in collections]

    meta = fetch_meta(domain)
    if meta:
        result["meta"] = meta

    return result
