"""AI-powered product advice using OpenAI-compatible API."""
import json
import logging
import requests
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是跨境电商选品专家，精通Shopify独立站运营。
分析店铺数据时，关注：定价策略、品类机会、竞争壁垒、流量来源推测。
回答简洁有力，用中文。"""


def generate_advice(analysis: dict) -> str:
    """Generate AI product advice from store analysis data."""
    if not OPENAI_API_KEY:
        return "⚠️ 未配置 OPENAI_API_KEY，无法生成AI建议"

    summary = json.dumps({
        "domain": analysis.get("domain"),
        "product_count": analysis.get("product_count", 0),
        "prices": analysis.get("prices", {}),
        "top_categories": dict(list(analysis.get("categories", {}).items())[:8]),
        "top_tags": list(analysis.get("tags", {}).keys())[:15],
        "vendors": dict(list(analysis.get("vendors", {}).items())[:5]),
        "trend": analysis.get("trend", {}),
        "score": analysis.get("score", {}),
    }, ensure_ascii=False, indent=2)

    prompt = f"""分析这个Shopify店铺数据，给出选品建议：

{summary}

请输出：
1. 🎯 店铺定位（一句话）
2. 💰 价格策略评估
3. 📈 3个可以跟卖/差异化的产品方向
4. 🔍 3个该店铺缺失但有机会的品类
5. ⚡ 竞争力评分（1-10）和理由
6. 🚀 一条最关键的行动建议"""

    try:
        r = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1500,
            },
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return f"🧠 *AI选品建议*\n\n{content}"
    except Exception as e:
        logger.error(f"AI advice failed: {e}")
        return f"⚠️ AI分析失败: {e}"


def compare_advice(stores_data: list[dict]) -> str:
    """Generate comparative advice for multiple stores."""
    if not OPENAI_API_KEY:
        return "⚠️ 未配置 OPENAI_API_KEY"

    summaries = []
    for s in stores_data[:5]:
        summaries.append({
            "domain": s.get("domain"),
            "product_count": s.get("product_count", 0),
            "avg_price": s.get("prices", {}).get("avg", 0),
            "top_categories": list(s.get("categories", {}).keys())[:5],
            "score": s.get("score", {}).get("score", 0),
        })

    prompt = f"""对比这些Shopify竞品店铺，给出差异化建议：

{json.dumps(summaries, ensure_ascii=False, indent=2)}

请输出：
1. 各店铺一句话定位
2. 市场空白点
3. 最佳差异化切入方向"""

    try:
        r = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Compare advice failed: {e}")
        return f"⚠️ AI对比分析失败: {e}"
