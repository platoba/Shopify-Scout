#!/usr/bin/env python3
"""Shopify Scout - AI选品+竞品监控 Telegram Bot (entry point)."""
import logging
from app.config import BOT_TOKEN, OPENAI_API_KEY, OPENAI_MODEL
from app.telegram_bot import tg_request, handle_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("shopify-scout")


def main():
    if not BOT_TOKEN:
        raise ValueError("未设置 BOT_TOKEN!")

    print(f"\n{'='*50}")
    print(f"  Shopify Scout v1.0 - AI选品工具")
    print(f"  AI: {'✅ ' + OPENAI_MODEL if OPENAI_API_KEY else '❌ 未配置'}")
    print(f"{'='*50}")

    me = tg_request("getMe")
    if me and me.get("ok"):
        print(f"\n✅ @{me['result']['username']} 已上线!")
    else:
        print("\n❌ 无法连接Telegram!")
        return

    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            result = tg_request("getUpdates", params)
            if not result or not result.get("ok"):
                import time; time.sleep(5)
                continue
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg:
                    continue
                text = (msg.get("text") or "").strip()
                if text:
                    try:
                        handle_message(msg["chat"]["id"], msg["message_id"], text)
                    except Exception as e:
                        logger.error(f"Handler error: {e}", exc_info=True)
        except KeyboardInterrupt:
            print("\n\n👋 已停止!")
            break
        except Exception as e:
            logger.error(f"Poll error: {e}")
            import time; time.sleep(5)


if __name__ == "__main__":
    main()
