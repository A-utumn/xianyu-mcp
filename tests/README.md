## Test Scripts

Keep these scripts as the primary manual test entry points:

- `test_all.py`: broad integration smoke test for browser, login, search, message, analytics, and validation.
- `quick_test.py`: fast core sanity check.
- `test_analytics_tools.py`: manual validation for item analytics and competitor analysis MCP helpers.
- `test_message_tools.py`: manual validation for message-related MCP helpers, including sendable conversations and message reads.
- `test_mcp_search.py`: verifies the MCP `search_items` entry point.
- `test_precise_search.py`: verifies search filtering and exact-match behavior.

Removed scripts were one-off debug helpers or overlapping search experiments that duplicated the coverage above.
