"""
精确搜索测试 - 带关键词过滤
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def precise_search():
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.search import XianyuSearch
    
    print("=" * 60)
    print("Precise Search Test")
    print("=" * 60)
    print()
    
    browser = XianyuBrowser(headless=True)
    try:
        await browser.launch()
        search = XianyuSearch(browser)
        
        # 测试 1: 精确匹配
        print("Test 1: Searching 'cursor pro' with exact match")
        print("-" * 60)
        items1 = await search.search(
            keyword="cursor pro",
            limit=10,
            exact_match=True
        )
        print(f"Found {len(items1)} items (exact match)")
        for i, item in enumerate(items1[:5], 1):
            print(f"  {i}. {item.title[:50]}")
        print()
        
        # 测试 2: 带过滤关键词
        print("Test 2: Searching 'cursor' with filter keywords")
        print("-" * 60)
        items2 = await search.search(
            keyword="cursor",
            limit=10,
            filter_keywords=["账号", "pro", "会员", "订阅"]
        )
        print(f"Found {len(items2)} items (filtered)")
        for i, item in enumerate(items2[:5], 1):
            print(f"  {i}. {item.title[:50]}")
        print()
        
        # 测试 3: 普通搜索（对比）
        print("Test 3: Searching 'cursor' without filter (comparison)")
        print("-" * 60)
        items3 = await search.search(
            keyword="cursor",
            limit=10
        )
        print(f"Found {len(items3)} items (no filter)")
        for i, item in enumerate(items3[:5], 1):
            print(f"  {i}. {item.title[:50]}")
        print()
        
        # Save results
        result_file = Path(__file__).parent / "precise_search_results.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump({
                "exact_match": {
                    "keyword": "cursor pro",
                    "count": len(items1),
                    "items": [item.to_dict() for item in items1]
                },
                "filtered": {
                    "keyword": "cursor",
                    "filters": ["账号", "pro", "会员", "订阅"],
                    "count": len(items2),
                    "items": [item.to_dict() for item in items2]
                },
                "no_filter": {
                    "keyword": "cursor",
                    "count": len(items3),
                    "items": [item.to_dict() for item in items3]
                }
            }, f, ensure_ascii=False, indent=2)
        
        print(f"Results saved to: {result_file}")
        
        # Summary
        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Exact match: {len(items1)} items")
        print(f"Filtered: {len(items2)} items")
        print(f"No filter: {len(items3)} items")
        print()
        print("Conclusion:")
        if len(items2) > 0:
            print("  [OK] Filtered search found relevant items!")
        else:
            print("  [WARN] No relevant items found, try different keywords")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(precise_search())
