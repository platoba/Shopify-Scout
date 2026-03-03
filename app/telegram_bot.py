"""Telegram Bot handlers for Shopify Scout."""
import logging
import requests
from app.config import BOT_TOKEN
from app.scraper import fetch_store_data, normalize_domain
from app.analyzer import full_analysis
from app.ai_advisor import generate_advice, compare_advice
from app.monitor import add_watch, remove_watch, list_watches

logger = logging.getLogger(__name__)
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def tg_request(method: str, params: dict = None) -> dict | None:
    try:
        r = requests.get(f"{API_URL}/{method}", params=params, timeout=35)
        return r.json()
    except Exception:
        return None


def send(chat_id: int, text: str, reply_to: int = None, parse_mode: str = "Markdown") -> dict | None:
    params = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    if parse_mode:
        params["parse_mode"] = parse_mode
    result = tg_request("sendMessage", params)
    if not result or not result.get("ok"):
        params.pop("parse_mode", None)
        result = tg_request("sendMessage", params)
    return result


def format_report(analysis: dict) -> str:
    """Format full analysis into a readable Telegram message."""
    lines = [f"🏪 *{analysis['domain']}*\n"]

    lines.append(f"📦 产品数: {analysis['product_count']}")

    p = analysis.get("prices", {})
    if p:
        lines.append(f"💰 价格: ${p['min']:.0f} - ${p['max']:.0f} (均价 ${p['avg']:.0f}, 中位 ${p['median']:.0f})")
        lines.append(f"📊 P25-P75: ${p['p25']:.0f} - ${p['p75']:.0f}")

    score = analysis.get("score", {})
    if score:
        lines.append(f"\n⭐ 竞争力: {score['score']}/10")
        for r in score.get("reasons", []):
            lines.append(f"  • {r}")

    cats = analysis.get("categories", {})
    if cats:
        lines.append(f"\n📂 品类 ({len(cats)}种):")
        for t, c in list(cats.items())[:6]:
            lines.append(f"  • {t}: {c}个")

    tags = analysis.get("tags", {})
    if tags:
        lines.append("\n🏷️ 热门标签:")
        lines.append(f"  {', '.join(list(tags.keys())[:12])}")

    vendors = analysis.get("vendors", {})
    if vendors and len(vendors) > 1:
        lines.append(f"\n🏭 供应商 ({len(vendors)}家):")
        for v, c in list(vendors.items())[:5]:
            lines.append(f"  • {v}: {c}个")

    trend = analysis.get("trend", {})
    if trend:
        lines.append("\n📈 上新趋势:")
        lines.append(f"  7天: {trend.get('last_7d', 0)} | 30天: {trend.get('last_30d', 0)} | 90天: {trend.get('last_90d', 0)}")
        lines.append(f"  月均上新: {trend.get('avg_per_month', 0)}款")

    colls = analysis.get("collections", [])
    if colls:
        lines.append(f"\n📁 集合 ({len(colls)}个):")
        for c in colls[:8]:
            lines.append(f"  • {c['title']}")

    return "\n".join(lines)


def format_compare(analyses: list[dict]) -> str:
    """Format comparison table."""
    lines = ["📊 *竞品对比*\n"]
    for a in sorted(analyses, key=lambda x: -x.get("product_count", 0)):
        p = a.get("prices", {})
        s = a.get("score", {})
        lines.append(
            f"🏪 {a['domain']}\n"
            f"  📦 {a.get('product_count', 0)}产品 | "
            f"💰 ${p.get('avg', 0):.0f}均价 | "
            f"⭐ {s.get('score', '?')}/10"
        )
    return "\n".join(lines)


def handle_message(chat_id: int, msg_id: int, text: str):
    """Route incoming messages to handlers."""
    parts = text.split()
    cmd = parts[0].lower().split("@")[0]  # strip @botname
    args = " ".join(parts[1:]).strip()

    if cmd == "/start" or cmd == "/help":
        send(chat_id,
             "🔍 *Shopify Scout* v1.0\n\n"
             "AI选品+竞品监控工具\n\n"
             "📊 *分析*\n"
             "  /scan <URL> — 全面分析店铺\n"
             "  /advice <URL> — AI选品建议\n"
             "  /compare <URL1> <URL2> ... — 竞品对比\n"
             "  /score <URL> — 竞争力评分\n\n"
             "👀 *监控*\n"
             "  /watch <URL> — 添加监控\n"
             "  /unwatch <URL> — 取消监控\n"
             "  /watched — 查看监控列表\n\n"
             "💡 直接发送Shopify店铺链接也能自动分析", msg_id)

    elif cmd == "/scan":
        if not args:
            send(chat_id, "用法: /scan <shopify店铺URL>\n例: /scan allbirds.com", msg_id)
            return
        send(chat_id, "🔍 正在扫描...", msg_id)
        data = fetch_store_data(args)
        if not data.get("product_count"):
            send(chat_id, f"⚠️ 无法分析 {args}，可能不是Shopify店铺或已关闭products.json", msg_id)
            return
        analysis = full_analysis(data)
        send(chat_id, format_report(analysis), msg_id)

    elif cmd == "/advice":
        if not args:
            send(chat_id, "用法: /advice <shopify店铺URL>", msg_id)
            return
        send(chat_id, "🧠 正在分析...", msg_id)
        data = fetch_store_data(args)
        if not data.get("product_count"):
            send(chat_id, "⚠️ 无法获取店铺数据", msg_id)
            return
        analysis = full_analysis(data)
        send(chat_id, format_report(analysis), msg_id)
        advice = generate_advice(analysis)
        send(chat_id, advice)

    elif cmd == "/score":
        if not args:
            send(chat_id, "用法: /score <shopify店铺URL>", msg_id)
            return
        send(chat_id, "⭐ 评分中...", msg_id)
        data = fetch_store_data(args)
        if not data.get("product_count"):
            send(chat_id, "⚠️ 无法获取店铺数据", msg_id)
            return
        analysis = full_analysis(data)
        s = analysis["score"]
        lines = [f"⭐ *{analysis['domain']}* — {s['score']}/10\n"]
        for r in s.get("reasons", []):
            lines.append(f"  • {r}")
        send(chat_id, "\n".join(lines), msg_id)

    elif cmd == "/compare":
        domains = args.split()
        if len(domains) < 2:
            send(chat_id, "用法: /compare <URL1> <URL2> ...\n至少2个店铺", msg_id)
            return
        send(chat_id, f"📊 正在对比 {len(domains)} 个店铺...", msg_id)
        analyses = []
        for d in domains[:5]:
            data = fetch_store_data(d)
            if data.get("product_count"):
                analyses.append(full_analysis(data))
        if len(analyses) < 2:
            send(chat_id, "⚠️ 至少需要2个有效店铺", msg_id)
            return
        send(chat_id, format_compare(analyses), msg_id)
        ai_compare = compare_advice(analyses)
        send(chat_id, f"🧠 *AI对比分析*\n\n{ai_compare}")

    elif cmd == "/watch":
        if not args:
            send(chat_id, "用法: /watch <shopify店铺URL>", msg_id)
            return
        domain = normalize_domain(args)
        if add_watch(domain, chat_id):
            send(chat_id, f"👀 已添加监控: {domain}", msg_id)
        else:
            send(chat_id, "⚠️ 添加失败", msg_id)

    elif cmd == "/unwatch":
        if not args:
            send(chat_id, "用法: /unwatch <shopify店铺URL>", msg_id)
            return
        domain = normalize_domain(args)
        if remove_watch(domain, chat_id):
            send(chat_id, f"✅ 已取消监控: {domain}", msg_id)
        else:
            send(chat_id, "⚠️ 未找到该监控", msg_id)

    elif cmd == "/watched":
        watches = list_watches(chat_id)
        if not watches:
            send(chat_id, "📋 暂无监控店铺\n使用 /watch <URL> 添加", msg_id)
        else:
            lines = [f"👀 监控列表 ({len(watches)}个)\n"]
            for w in watches:
                lines.append(f"  • {w['domain']} ({w['last_product_count']}产品)")
            send(chat_id, "\n".join(lines), msg_id)

    elif not text.startswith("/"):
        # Auto-detect Shopify URLs
        if any(kw in text.lower() for kw in [".myshopify.com", "shopify", ".com"]):
            url = text.strip().split()[0]
            send(chat_id, "🔍 检测到链接，正在分析...", msg_id)
            data = fetch_store_data(url)
            if data.get("product_count"):
                analysis = full_analysis(data)
                send(chat_id, format_report(analysis), msg_id)
            else:
                send(chat_id, f"⚠️ 无法分析 {url}，可能不是Shopify店铺", msg_id)
