"""
MCP 搜索功能测试脚本

测试使用 MCP 协议搜索商品
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def test_mcp_search():
    """测试 MCP 搜索功能"""
    print("=" * 60)
    print("MCP 搜索功能测试 - cursor pro")
    print("=" * 60)
    print()
    
    try:
        # 导入 MCP 服务器中的搜索工具
        from xianyu_mcp.server import search_items
        
        print("[1/3] 调用 MCP 搜索工具...")
        results = await search_items(
            keyword="cursor pro",
            limit=5
        )
        
        print(f"[2/3] 收到 {len(results)} 个结果")
        print()
        print("[3/3] 结果详情:")
        print()
        
        if results:
            for i, item in enumerate(results[:5], 1):
                print(f"{i}. {item.get('title', 'N/A')[:50]}")
                print(f"   价格: RMB {item.get('price', 'N/A')}")
                print(f"   位置：{item.get('location', 'N/A')}")
                print(f"   想要：{item.get('want_count', 'N/A')}人")
                print()
        else:
            print("未找到相关商品")
            print()
            print("可能原因:")
            print("1. 关键词无结果")
            print("2. 选择器需要调整")
            print("3. 页面结构变化")
        
        print("=" * 60)
        print("测试完成")
        print("=" * 60)
        
        return results
        
    except Exception as e:
        print(f"[ERROR] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    results = asyncio.run(test_mcp_search())
    
    # 保存结果
    import json
    result_file = Path(__file__).parent / "search_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "keyword": "cursor pro",
            "count": len(results),
            "items": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到：{result_file}")
