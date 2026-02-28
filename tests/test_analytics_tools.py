"""
分析工具手动测试脚本

用于验证商品统计和竞品分析 MCP 工具的返回结构。
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


TEST_ITEM_IDS = [
    "966781426236",
    "963878392731",
]


async def main():
    from xianyu_mcp.server import analyze_competitors, get_item_analytics

    print("=" * 60)
    print("闲鱼 MCP 分析工具测试")
    print("=" * 60)
    print()

    print(f"[测试] 获取商品统计：{TEST_ITEM_IDS[0]} ...")
    item_result = await get_item_analytics(TEST_ITEM_IDS[0])
    print(json.dumps(item_result, ensure_ascii=True))

    print()
    print(f"[测试] 竞品分析：{TEST_ITEM_IDS} ...")
    competitor_result = await analyze_competitors(TEST_ITEM_IDS)
    print(json.dumps(competitor_result, ensure_ascii=True))

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
