"""
Shopify Scout - AI选品+竞品监控 Telegram Bot
通过Shopify Storefront API抓取公开店铺数据
"""

import os
import re
import time
import json
import requests
from urllib.parse import urlparse

TOKEN = os.environ.get("BOT_TOKEN", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if not TOKEN:
    raise ValueError("未设置 BOT_TOKEN!")

API_URL = f"https://api.telegram.org/bot{TOKEN}"


def tg_get(method, params=None):
    try:
        r = requests.get(f"{API_URL}/{method}", params=params, timeout=35)
        return r.json()
    except:
        return None


def tg_send(chat_id, text, reply_to=None, parse_mode="Markdown"):
    params = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if reply_to: params["reply_to_message_id"] = reply_to
    if parse_mode: params["parse_mode"] = parse_mode
    result = tg_get("sendMessage", params)
    if not result or not result.get("ok"):
        params.pop("parse_mode", None)
        result = tg_get("sendMessage", params)
    return result


def get_updates(offset=None):
    params = {"timeout": 30}
    if offset: params["offset"] = offset
    return tg_get("getUpdates", params)


# ── Shopify店铺分析 ──────────────────────────────────────
def analyze_shopify_store(store_url):
    """通过公开API分析Shopify店铺"""
    parsed = urlparse(store_url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    if not domain.startswith("http"):
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    results = {"domain": domain, "products": [], "collections": []}

    # 抓取products.json
    try:
        r = requests.get(f"https://{domain}/products.json?limit=250", timeout=15,
                        headers={"User-Agent": "Mozilla/5.0"})
        if r.ok:
            products = r.json().get("products", [])
            results["product_count"] = len(products)
            results["products"] = products[:50]  # 保留前50个

            # 分析价格分布
            prices = []
            for p in products:
                for v in p.get("variants", []):
                    try:
                        prices.append(float(v.get("price", 0)))
                    except:
                        pass

            if prices:
                results["price_min"] = min(prices)
                results["price_max"] = max(prices)
                results["price_avg"] = sum(prices) / len(prices)

            # 分析产品类型
            types = {}
            for p in products:
                pt = p.get("product_type", "Other") or "Other"
                types[pt] = types.get(pt, 0) + 1
            results["product_types"] = dict(sorted(types.items(), key=lambda x: -x[1])[:10])

            # 分析标签
            tags = {}
            for p in products:
                for t in p.get("tags", []):
                    if isinstance(t, str):
                        tags[t] = tags.get(t, 0) + 1
            results["top_tags"] = dict(sorted(tags.items(), key=lambda x: -x[1])[:15])
    except Exception as e:
        results["error_products"] = str(e)

    # 抓取collections
    try:
        r = requests.get(f"https://{domain}/collections.json", timeout=15,
                        headers={"User-Agent": "Mozilla/5.0"})
        if r.ok:
            collections = r.json().get("collections", [])
            results["collections"] = [{"title": c["title"], "id": c["id"]} for c in collections]
    except:
        pass

    # 检测主题和技术栈
    try:
        r = requests.get(f"https://{domain}/meta.json", timeout=10,
                        headers={"User-Agent": "Mozilla/5.0"})
        if r.ok:
            results["meta"] = r.json()
    except:
        pass

    return results


def format_store_report(data):
    """格式化店铺分析报告"""
    lines = [f"🏪 *{data['domain']}*\n"]

    if "product_count" in data:
        lines.append(f"📦 产品数: {data['product_count']}")

    if "price_avg" in data:
        lines.append(f"💰 价格: ${data['price_min']:.0f} - ${data['price_max']:.0f} (均价 ${data['price_avg']:.0f})")

    if data.get("product_types"):
        lines.append(f"\n📂 产品分类:")
        for t, c in list(data["product_types"].items())[:5]:
            lines.append(f"  • {t}: {c}个")

    if data.get("top_tags"):
        lines.append(f"\n🏷️ 热门标签:")
        tags = list(data["top_tags"].keys())[:10]
        lines.append(f"  {', '.join(tags)}")

    if data.get("collections"):
        lines.append(f"\n📁 集合 ({len(data['collections'])}个):")
        for c in data["collections"][:8]:
            lines.append(f"  • {c['title']}")

    # 热卖产品（按created_at排序取最新）
    if data.get("products"):
        lines.append(f"\n🔥 最新产品:")
        for p in data["products"][:5]:
            price = p.get("variants", [{}])[0].get("price", "?")
            lines.append(f"  • ${price} | {p['title'][:50]}")

    return "\n".join(lines)


# ── 选品建议 ──────────────────────────────────────────────
def ai_product_advice(store_data):
    """AI分析选品建议"""
    if not OPENAI_KEY:
        return "⚠️ 未配置 OPENAI_API_KEY，无法生成AI建议"

    summary = json.dumps({
        "domain": store_data.get("domain"),
        "product_count": store_data.get("product_count", 0),
        "price_range": f"${store_data.get('price_min', 0):.0f}-${store_data.get('price_max', 0):.0f}",
        "avg_price": f"${store_data.get('price_avg', 0):.0f}",
        "top_types": store_data.get("product_types", {}),
        "top_tags": list(store_data.get("top_tags", {}).keys())[:10],
    }, ensure_ascii=False)

    prompt = f"""分析这个Shopify店铺数据，给出选品建议：

{summary}

请输出：
1. 店铺定位分析（一句话）
2. 价格策略评估
3. 3个可以跟卖/差异化的产品方向
4. 3个该店铺缺失但有机会的品类
5. 竞争力评分（1-10）和理由"""

    try:
        r = requests.post(f"{OPENAI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={"model": OPENAI_MODEL, "messages": [
                {"role": "system", "content": "你是跨境电商选品专家。"},
                {"role": "user", "content": prompt}
            ], "temperature": 0.7, "max_tokens": 1500}, timeout=60)
        r.raise_for_status()
        return "🧠 *AI选品建议*\n\n" + r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ AI分析失败: {e}"


# ── 批量竞品对比 ──────────────────────────────────────────
watched_stores = {}


def compare_stores(domains):
    """对比多个店铺"""
    results = []
    for d in domains[:5]:
        data = analyze_shopify_store(d)
        results.append({
            "domain": d,
            "products": data.get("product_count", 0),
            "avg_price": data.get("price_avg", 0),
            "types": len(data.get("product_types", {})),
        })

    lines = ["📊 *竞品对比*\n"]
    lines.append(f"{'店铺':<25} {'产品数':<8} {'均价':<10} {'品类'}")
    lines.append("-" * 55)
    for r in sorted(results, key=lambda x: -x["products"]):
        lines.append(f"{r['domain'][:24]:<25} {r['products']:<8} ${r['avg_price']:<9.0f} {r['types']}")
    return "\n".join(lines)


# ── 命令处理 ──────────────────────────────────────────────
def handle(chat_id, msg_id, text):
    cmd = text.split()[0].lower()
    args = text[len(cmd):].strip()

    if cmd == "/start":
        tg_send(chat_id,
            "🔍 *Shopify Scout*\n\n"
            "AI选品+竞品监控工具\n\n"
            "📊 *分析*\n"
            "  /scan <店铺URL> — 分析Shopify店铺\n"
            "  /advice <店铺URL> — AI选品建议\n"
            "  /compare <URL1> <URL2> ... — 竞品对比\n\n"
            "👀 *监控*\n"
            "  /watch <店铺URL> — 添加监控\n"
            "  /watched — 查看监控列表\n\n"
            "💡 直接发送Shopify店铺链接也能自动分析", msg_id)

    elif cmd == "/scan":
        if not args:
            tg_send(chat_id, "用法: /scan <shopify店铺URL>\n例: /scan allbirds.com", msg_id)
            return
        tg_send(chat_id, "🔍 正在扫描...", msg_id)
        data = analyze_shopify_store(args)
        tg_send(chat_id, format_store_report(data), msg_id)

    elif cmd == "/advice":
        if not args:
            tg_send(chat_id, "用法: /advice <shopify店铺URL>", msg_id)
            return
        tg_send(chat_id, "🧠 正在分析...", msg_id)
        data = analyze_shopify_store(args)
        report = format_store_report(data)
        advice = ai_product_advice(data)
        tg_send(chat_id, report, msg_id)
        tg_send(chat_id, advice)

    elif cmd == "/compare":
        domains = args.split()
        if len(domains) < 2:
            tg_send(chat_id, "用法: /compare <URL1> <URL2> ...\n至少2个店铺", msg_id)
            return
        tg_send(chat_id, "📊 正在对比...", msg_id)
        tg_send(chat_id, compare_stores(domains), msg_id)

    elif cmd == "/watch":
        if not args:
            tg_send(chat_id, "用法: /watch <shopify店铺URL>", msg_id)
            return
        watched_stores[args] = {"added": time.time()}
        tg_send(chat_id, f"👀 已添加监控: {args}", msg_id)

    elif cmd == "/watched":
        if not watched_stores:
            tg_send(chat_id, "📋 暂无监控店铺", msg_id)
        else:
            lines = ["👀 监控列表\n"]
            for s in watched_stores:
                lines.append(f"  • {s}")
            tg_send(chat_id, "\n".join(lines), msg_id)

    elif not text.startswith("/"):
        # 自动检测Shopify链接
        if any(kw in text.lower() for kw in [".myshopify.com", "shopify", ".com"]):
            url = text.strip().split()[0]
            tg_send(chat_id, "🔍 检测到店铺链接，正在分析...", msg_id)
            data = analyze_shopify_store(url)
            if data.get("product_count"):
                tg_send(chat_id, format_store_report(data), msg_id)
            else:
                tg_send(chat_id, f"⚠️ 无法分析 {url}，可能不是Shopify店铺或已关闭products.json", msg_id)


def main():
    print(f"\n{'='*50}")
    print(f"  Shopify Scout - AI选品工具")
    print(f"  AI: {'✅ ' + OPENAI_MODEL if OPENAI_KEY else '❌ 未配置'}")
    print(f"{'='*50}")

    me = tg_get("getMe")
    if me and me.get("ok"):
        print(f"\n✅ @{me['result']['username']} 已上线!")
    else:
        print("\n❌ 无法连接Telegram!")
        return

    offset = None
    while True:
        try:
            result = get_updates(offset)
            if not result or not result.get("ok"):
                time.sleep(5)
                continue
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg: continue
                text = (msg.get("text") or "").strip()
                if text:
                    handle(msg["chat"]["id"], msg["message_id"], text)
        except KeyboardInterrupt:
            print("\n\n👋 已停止!")
            break
        except Exception as e:
            print(f"[错误] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
