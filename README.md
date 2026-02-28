# 闲鱼 MCP

基于 Playwright 的闲鱼自动化 MCP 服务，当前重点可用能力是搜索、登录状态检查、可发送会话筛选、消息发送/回读，以及基础商品分析。

## 当前状态

- 搜索链路已按当前 `goofish.com` 页面结构修复，可返回真实商品结果。
- MCP 入口可直接调用 `search_items`、`get_conversations`、`get_sendable_conversations`、`get_messages`、`send_message`。
- 消息模块已支持会话来源标记、可发送会话排序、上下文预热和商品上下文回填。
- 分析模块当前已支持真实商品统计和竞品分析；销售、流量、热门商品排行仍有部分 TODO。
- 发布模块仍有部分 TODO，不建议当成完整生产能力使用。

## 快速开始

```bash
uv sync
playwright install chromium
python scripts/login.py
python scripts/check_status.py
python src/xianyu_mcp/server.py
```

扫码登录后，Cookie 会保存在 `cookies/`。

## 配置

参考 `.env.example`，环境变量前缀为 `XIANYU_`。

常用项：

```env
XIANYU_HEADLESS=false
XIANYU_COOKIE_FILE=./cookies/default.json
XIANYU_USER_DATA_DIR=./user_data
```

## 主要工具

- `search_items`: 搜索闲鱼商品
- `check_server_status`: 检查 MCP 服务状态
- `publish_item`: 发布商品（部分流程未完成）
- `get_conversations`: 获取会话列表（支持 `sendable_only` / `context_only` 过滤）
- `get_sendable_conversations`: 获取可发送会话（支持上下文预热）
- `get_unread_messages`: 获取未读消息数
- `get_messages`: 获取会话消息（返回 `source`、商品上下文等）
- `send_message`: 发送消息
- `get_item_analytics`: 获取单个商品的真实统计数据
- `analyze_competitors`: 获取多个商品的竞品对比分析

## 测试

优先使用仓库内的脚本，而不是依赖 `pytest`：

```bash
python tests/quick_test.py
python tests/test_mcp_search.py
python tests/test_precise_search.py
python tests/test_message_tools.py
python tests/test_analytics_tools.py
python tests/test_all.py
```

测试脚本说明见 [tests/README.md](C:/Users/Administrator/.openclaw/workspace/xianyu-mcp/tests/README.md)。

## 目录

- `src/xianyu_mcp/`: 主代码
- `scripts/`: 登录和状态检查脚本
- `tests/`: 保留的手动测试脚本
- `examples/`: 示例

## 说明

本项目仅供学习和自动化研究使用。请自行控制访问频率，并遵守目标平台规则。
