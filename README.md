# 🐟 闲鱼 MCP

闲鱼 MCP 服务器 - 实现闲鱼商品搜索、发布、消息、数据的完全自动化

## ✨ 功能特性

- 🔍 **商品搜索** - 关键词搜索、筛选条件、竞品监控
- 📸 **商品发布** - 图文发布、批量上架、定时发布
- 💬 **消息互动** - 自动回复、智能议价、订单通知
- 📊 **数据分析** - 销售统计、流量分析、竞品报告

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

### 3. 登录闲鱼

```bash
# 运行登录脚本
python scripts/login.py
```

扫码登录后，Cookie 会自动保存到 `cookies/` 目录。

### 4. 检查登录状态

```bash
python scripts/check_status.py
```

### 5. 启动 MCP 服务器

```bash
python src/xianyu_mcp/server.py
```

## 📋 MCP 工具列表

### 搜索工具

- `search_items(keyword, price_min, price_max, location)` - 搜索商品
- `get_competitor_prices(item_ids)` - 获取竞品价格
- `get_hot_items(category, limit)` - 获取热门商品

### 发布工具

- `publish_item(title, description, price, images, category)` - 发布商品
- `batch_publish(items)` - 批量发布
- `update_item(item_id, updates)` - 修改商品
- `delete_item(item_id)` - 下架商品

### 消息工具

- `get_messages(limit)` - 获取消息列表
- `send_reply(user_id, content)` - 发送回复
- `get_unread_count()` - 获取未读消息数

### 数据工具

- `get_item_stats(item_id)` - 获取商品数据
- `get_sales_summary(days)` - 销售统计
- `get_traffic_analysis(item_id)` - 流量分析

## 📁 项目结构

```
xianyu-mcp/
├── src/xianyu_mcp/          # 源代码
│   ├── server.py            # MCP 服务器入口
│   ├── xianyu/              # 闲鱼自动化核心
│   │   ├── browser.py       # 浏览器管理
│   │   ├── login.py         # 登录模块
│   │   ├── search.py        # 搜索模块
│   │   ├── publish.py       # 发布模块
│   │   └── message.py       # 消息模块
│   └── mcp_tools/           # MCP 工具定义
├── scripts/                 # 辅助脚本
│   ├── login.py             # 登录脚本
│   └── check_status.py      # 检查状态
├── cookies/                 # Cookie 存储（不上传）
├── tests/                   # 测试用例
└── examples/                # 使用示例
```

## ⚙️ 配置说明

创建 `.env` 文件（参考 `.env.example`）：

```env
# 浏览器配置
XIANIU_HEADLESS=false
XIANIU_BROWSER_PATH=

# Cookie 配置
XIANIU_COOKIE_FILE=./cookies/default.json

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/xianyu.log
```

## ⚠️ 注意事项

### 1. 账号安全
- 控制操作频率，避免被封号
- 搜索间隔 > 3 秒
- 发布间隔 > 30 秒
- 不要用于商业化滥用

### 2. Cookie 管理
- Cookie 存储在本地 `cookies/` 目录
- 不要上传到 Git
- 定期重新登录更新 Cookie

### 3. 反爬措施
- 使用真实浏览器指纹
- 模拟人工操作延迟
- 避免高频请求

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_search.py -v
```

## 📝 使用示例

### 搜索商品

```python
from xianyu_mcp.xianyu.search import XianyuSearch
from xianyu_mcp.xianyu.browser import XianyuBrowser

browser = XianyuBrowser()
await browser.launch()
search = XianyuSearch(browser)

items = await search.search("iPhone 15", {
    "price_min": 3000,
    "price_max": 5000,
    "location": "上海"
})

for item in items:
    print(f"{item.title} - ¥{item.price}")

await browser.close()
```

### 发布商品

```python
from xianyu_mcp.xianyu.publish import XianyuPublish, PublishParams

params = PublishParams(
    title="iPhone 15 Pro 256G 99 新",
    description="自用 iPhone，无划痕，电池 95%",
    price=6500,
    images=["./photos/iphone1.jpg", "./photos/iphone2.jpg"],
    category="手机数码",
    location="上海"
)

publish = XianyuPublish(browser)
item_id = await publish.publish(params)
print(f"发布成功！商品 ID: {item_id}")
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## ⚠️ 免责声明

本项目仅供学习交流使用，请勿用于非法用途。使用本项目造成的任何后果由使用者自行承担。
