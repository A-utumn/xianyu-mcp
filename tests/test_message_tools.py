"""
消息工具手动测试脚本

用于验证新增的消息类 MCP 工具返回结构是否符合预期。
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def main():
    from xianyu_mcp.server import (
        get_conversations,
        get_messages,
        get_sendable_conversations,
    )

    print("=" * 60)
    print("闲鱼 MCP 消息工具测试")
    print("=" * 60)
    print()

    print("[测试] 获取可发送会话（不预热）...")
    sendable = await get_sendable_conversations(limit=3, warm_context=False)
    print(json.dumps(sendable, ensure_ascii=True))

    if not sendable.get("success"):
        print("[WARN] 获取可发送会话失败，后续测试跳过")
        return

    print()
    print("[测试] 获取可发送会话（预热上下文）...")
    warmed = await get_sendable_conversations(limit=3, warm_context=True)
    print(json.dumps(warmed, ensure_ascii=True))

    target_id = ""
    items = warmed.get("items") or sendable.get("items") or []
    if items:
        target_id = items[0].get("id", "")

    print()
    print("[测试] 获取会话列表（仅可发送）...")
    conversations = await get_conversations(limit=5, sendable_only=True, context_only=False)
    print(json.dumps(conversations, ensure_ascii=True))

    if target_id:
        print()
        print(f"[测试] 获取会话消息：{target_id} ...")
        messages = await get_messages(conversation_id=target_id, limit=3)
        print(json.dumps(messages, ensure_ascii=True))
    else:
        print()
        print("[WARN] 没有可用会话，跳过消息读取测试")

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
