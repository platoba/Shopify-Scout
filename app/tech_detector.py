"""Shopify tech stack detector - identify themes, apps, and integrations."""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Known Shopify themes
KNOWN_THEMES = {
    "dawn": "Dawn (Shopify default free theme)",
    "debut": "Debut (Classic free theme)",
    "minimal": "Minimal (Free theme)",
    "simple": "Simple (Free theme)",
    "supply": "Supply (Free theme)",
    "brooklyn": "Brooklyn (Free theme)",
    "narrative": "Narrative (Free theme)",
    "venture": "Venture (Free theme)",
    "boundless": "Boundless (Free theme)",
    "express": "Express (Free theme)",
    "sense": "Sense (Free theme)",
    "craft": "Craft (Free theme)",
    "crave": "Crave (Free theme)",
    "ride": "Ride (Free theme)",
    "colorblock": "Colorblock (Free theme)",
    "studio": "Studio (Free theme)",
    "taste": "Taste (Free theme)",
    "publisher": "Publisher (Free theme)",
    "refresh": "Refresh (Free theme)",
    "turbo": "Turbo (Out of the Sandbox - Premium)",
    "prestige": "Prestige (Maestrooo - Premium)",
    "impulse": "Impulse (Archetype Themes - Premium)",
    "warehouse": "Warehouse (Maestrooo - Premium)",
    "ella": "Ella (HaloThemes - Premium)",
    "shella": "Shella (HaloThemes - Premium)",
    "fastor": "Fastor (RoarTheme - Premium)",
    "debutify": "Debutify (Debutify Corp - Free/Premium)",
    "booster": "Booster Theme (Clean Canvas - Premium)",
    "flexon": "Flexon (Out of the Sandbox - Premium)",
    "pipeline": "Pipeline (Groupthought - Premium)",
    "symmetry": "Symmetry (Clean Canvas - Premium)",
}

# Known Shopify apps and services by script/resource patterns
APP_SIGNATURES = {
    "klaviyo": {
        "patterns": [r"klaviyo\.com", r"klaviyo-form", r"_learnq"],
        "name": "Klaviyo",
        "category": "Email Marketing",
    },
    "yotpo": {
        "patterns": [r"yotpo\.com", r"yotpo-widget", r"staticw2\.yotpo"],
        "name": "Yotpo",
        "category": "Reviews",
    },
    "judge_me": {
        "patterns": [r"judge\.me", r"judgeme"],
        "name": "Judge.me",
        "category": "Reviews",
    },
    "loox": {
        "patterns": [r"loox\.io"],
        "name": "Loox",
        "category": "Reviews",
    },
    "stamped": {
        "patterns": [r"stamped\.io"],
        "name": "Stamped.io",
        "category": "Reviews",
    },
    "omnisend": {
        "patterns": [r"omnisend\.com", r"omnisrc"],
        "name": "Omnisend",
        "category": "Email Marketing",
    },
    "privy": {
        "patterns": [r"privy\.com", r"privy-popup"],
        "name": "Privy",
        "category": "Popups/Email",
    },
    "sms_bump": {
        "patterns": [r"smsbump\.com", r"yotpo-sms"],
        "name": "SMSBump",
        "category": "SMS Marketing",
    },
    "aftership": {
        "patterns": [r"aftership\.com", r"track\.aftership"],
        "name": "AfterShip",
        "category": "Order Tracking",
    },
    "recharge": {
        "patterns": [r"recharge(cdn|payments|apps)?\.com", r"rechargepayments"],
        "name": "Recharge",
        "category": "Subscriptions",
    },
    "bold": {
        "patterns": [r"boldcommerce\.com", r"boldapps\.net"],
        "name": "Bold Commerce",
        "category": "Upsell/Pricing",
    },
    "vitals": {
        "patterns": [r"vitals\.co"],
        "name": "Vitals",
        "category": "All-in-one App",
    },
    "pagefly": {
        "patterns": [r"pagefly\.io", r"pagefly"],
        "name": "PageFly",
        "category": "Page Builder",
    },
    "shogun": {
        "patterns": [r"shogun(frontend|landing)?\.com"],
        "name": "Shogun",
        "category": "Page Builder",
    },
    "gempages": {
        "patterns": [r"gempages\.net"],
        "name": "GemPages",
        "category": "Page Builder",
    },
    "oberlo": {
        "patterns": [r"oberlo\.com"],
        "name": "Oberlo (Deprecated)",
        "category": "Dropshipping",
    },
    "dsers": {
        "patterns": [r"dsers\.com"],
        "name": "DSers",
        "category": "Dropshipping",
    },
    "spocket": {
        "patterns": [r"spocket\.co"],
        "name": "Spocket",
        "category": "Dropshipping",
    },
    "facebook_pixel": {
        "patterns": [r"connect\.facebook\.net/.*fbevents", r"fbq\("],
        "name": "Facebook Pixel",
        "category": "Analytics",
    },
    "google_analytics": {
        "patterns": [r"google-analytics\.com", r"googletagmanager\.com", r"gtag\("],
        "name": "Google Analytics/GTM",
        "category": "Analytics",
    },
    "hotjar": {
        "patterns": [r"hotjar\.com", r"hj\("],
        "name": "Hotjar",
        "category": "Analytics",
    },
    "tiktok_pixel": {
        "patterns": [r"analytics\.tiktok\.com", r"ttq\."],
        "name": "TikTok Pixel",
        "category": "Analytics",
    },
    "pinterest": {
        "patterns": [r"pintrk\(", r"ct\.pinterest\.com"],
        "name": "Pinterest Tag",
        "category": "Analytics",
    },
    "shopify_payments": {
        "patterns": [r"shopify[\s_-]?payment", r"checkout\.shopify"],
        "name": "Shopify Payments",
        "category": "Payments",
    },
    "paypal": {
        "patterns": [r"paypal\.com/sdk", r"paypalobjects\.com"],
        "name": "PayPal",
        "category": "Payments",
    },
    "stripe": {
        "patterns": [r"js\.stripe\.com", r"stripe-js"],
        "name": "Stripe",
        "category": "Payments",
    },
    "afterpay": {
        "patterns": [r"afterpay\.com", r"static\.afterpay"],
        "name": "Afterpay",
        "category": "BNPL",
    },
    "klarna": {
        "patterns": [r"klarna\.com", r"klarna-"],
        "name": "Klarna",
        "category": "BNPL",
    },
    "sezzle": {
        "patterns": [r"sezzle\.com", r"widget\.sezzle"],
        "name": "Sezzle",
        "category": "BNPL",
    },
    "tidio": {
        "patterns": [r"tidio\.co", r"tidioChatCode"],
        "name": "Tidio",
        "category": "Live Chat",
    },
    "gorgias": {
        "patterns": [r"gorgias\.chat", r"gorgias-chat"],
        "name": "Gorgias",
        "category": "Customer Support",
    },
    "zendesk": {
        "patterns": [r"zdassets\.com", r"zendesk\.com"],
        "name": "Zendesk",
        "category": "Customer Support",
    },
    "intercom": {
        "patterns": [r"intercom\.io", r"widget\.intercom"],
        "name": "Intercom",
        "category": "Customer Support",
    },
}

# Payment gateway indicators
PAYMENT_GATEWAYS = {
    "shopify_payments": "Shopify Payments",
    "paypal": "PayPal",
    "stripe": "Stripe",
    "afterpay": "Afterpay/Clearpay",
    "klarna": "Klarna",
    "sezzle": "Sezzle",
    "affirm": "Affirm",
    "amazon_pay": "Amazon Pay",
    "apple_pay": "Apple Pay",
    "google_pay": "Google Pay",
}


def detect_theme(html_content: str) -> dict:
    """Detect Shopify theme from HTML content.

    Args:
        html_content: Raw HTML of the store homepage.

    Returns:
        Dict with theme name, version, and confidence.
    """
    result = {
        "theme_name": None,
        "theme_name_full": None,
        "theme_store_id": None,
        "confidence": "none",
    }

    if not html_content:
        return result

    # Method 1: Shopify.theme in script
    theme_match = re.search(
        r'Shopify\.theme\s*=\s*\{[^}]*"name"\s*:\s*"([^"]+)"', html_content
    )
    if theme_match:
        raw_name = theme_match.group(1).strip()
        result["theme_name"] = raw_name
        result["confidence"] = "high"

        # Try to match to known themes
        lower = raw_name.lower()
        for key, desc in KNOWN_THEMES.items():
            if key in lower:
                result["theme_name_full"] = desc
                break

    # Method 2: theme store ID
    store_id_match = re.search(
        r'Shopify\.theme\s*=\s*\{[^}]*"theme_store_id"\s*:\s*(\d+)', html_content
    )
    if store_id_match:
        result["theme_store_id"] = int(store_id_match.group(1))
        if result["confidence"] == "none":
            result["confidence"] = "medium"

    # Method 3: CSS class hints
    if result["theme_name"] is None:
        for key in KNOWN_THEMES:
            if re.search(rf'class="[^"]*{key}[^"]*"', html_content, re.IGNORECASE):
                result["theme_name"] = key
                result["theme_name_full"] = KNOWN_THEMES[key]
                result["confidence"] = "low"
                break

    return result


def detect_apps(html_content: str) -> list[dict]:
    """Detect installed Shopify apps from HTML content.

    Args:
        html_content: Raw HTML of the store page.

    Returns:
        List of detected apps with name and category.
    """
    detected = []

    if not html_content:
        return detected

    for key, info in APP_SIGNATURES.items():
        for pattern in info["patterns"]:
            if re.search(pattern, html_content, re.IGNORECASE):
                detected.append({
                    "id": key,
                    "name": info["name"],
                    "category": info["category"],
                    "confidence": "high" if len(info["patterns"]) > 1 else "medium",
                })
                break

    return detected


def detect_payments(html_content: str) -> list[str]:
    """Detect payment gateways from HTML content."""
    found = []
    if not html_content:
        return found

    content_lower = html_content.lower()

    # Custom patterns for more accurate detection
    payment_patterns = {
        "Shopify Payments": [r"shopify[\s_-]?payment"],
        "PayPal": [r"paypal"],
        "Stripe": [r"stripe\.com", r"stripe[\s_-]js"],
        "Afterpay/Clearpay": [r"afterpay"],
        "Klarna": [r"klarna"],
        "Sezzle": [r"sezzle"],
        "Affirm": [r"affirm"],
        "Amazon Pay": [r"amazon[\s_-]?pay"],
        "Apple Pay": [r"apple[\s_-]?pay"],
        "Google Pay": [r"google[\s_-]?pay"],
    }

    for name, patterns in payment_patterns.items():
        for pattern in patterns:
            if re.search(pattern, content_lower):
                found.append(name)
                break

    return found


def detect_currency(html_content: str) -> Optional[str]:
    """Detect store currency from HTML."""
    if not html_content:
        return None

    match = re.search(r'"currency"\s*:\s*"([A-Z]{3})"', html_content)
    if match:
        return match.group(1)

    # Fallback: look for common currency symbols in meta tags
    currency_patterns = {
        "USD": [r"\$[\d,]+\.\d{2}", r"currency.*USD"],
        "EUR": [r"€[\d,]+\.\d{2}", r"currency.*EUR"],
        "GBP": [r"£[\d,]+\.\d{2}", r"currency.*GBP"],
        "CAD": [r"CA\$[\d,]+", r"currency.*CAD"],
        "AUD": [r"AU\$[\d,]+", r"currency.*AUD"],
    }
    for curr, patterns in currency_patterns.items():
        for p in patterns:
            if re.search(p, html_content):
                return curr

    return None


def detect_locale(html_content: str) -> Optional[str]:
    """Detect store locale from HTML."""
    if not html_content:
        return None

    match = re.search(r'<html[^>]*lang="([^"]+)"', html_content)
    if match:
        return match.group(1)
    return None


def full_tech_scan(html_content: str) -> dict:
    """Run full tech stack detection on store HTML.

    Args:
        html_content: Raw HTML content of the store.

    Returns:
        Complete tech stack report.
    """
    theme = detect_theme(html_content)
    apps = detect_apps(html_content)
    payments = detect_payments(html_content)
    currency = detect_currency(html_content)
    locale = detect_locale(html_content)

    # Categorize apps
    categories = {}
    for app in apps:
        cat = app["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(app["name"])

    return {
        "theme": theme,
        "apps": apps,
        "app_count": len(apps),
        "app_categories": categories,
        "payments": payments,
        "currency": currency,
        "locale": locale,
    }


def format_tech_report(tech_data: dict, domain: str = "") -> str:
    """Format tech stack report as readable text."""
    lines = [f"🔧 **{domain or '店铺'}技术栈分析**\n"]

    # Theme
    theme = tech_data.get("theme", {})
    if theme.get("theme_name"):
        full = theme.get("theme_name_full", theme["theme_name"])
        lines.append(f"🎨 **主题**: {full}")
        if theme.get("theme_store_id"):
            lines.append(f"   Theme Store ID: {theme['theme_store_id']}")
        lines.append(f"   检测置信度: {theme.get('confidence', 'unknown')}")
    else:
        lines.append("🎨 **主题**: 未检测到")
    lines.append("")

    # Apps by category
    categories = tech_data.get("app_categories", {})
    if categories:
        lines.append(f"📦 **检测到 {tech_data.get('app_count', 0)} 个应用**")
        for cat, names in sorted(categories.items()):
            lines.append(f"  [{cat}] {', '.join(names)}")
    else:
        lines.append("📦 **应用**: 未检测到已知应用")
    lines.append("")

    # Payments
    payments = tech_data.get("payments", [])
    if payments:
        lines.append(f"💳 **支付方式**: {', '.join(payments)}")
    lines.append("")

    # Locale & Currency
    if tech_data.get("currency"):
        lines.append(f"💱 **货币**: {tech_data['currency']}")
    if tech_data.get("locale"):
        lines.append(f"🌐 **语言**: {tech_data['locale']}")

    return "\n".join(lines)
