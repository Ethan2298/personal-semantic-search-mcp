# Feature: Eager Initialization on Server Startup

## GitHub Issue
[#1](https://github.com/Ethan2298/personal-semantic-search-mcp/issues/1)

## Problem Statement
MCP server responds with empty results because heavy dependencies (sentence-transformers, ChromaDB) are lazily loaded, causing first tool call to timeout.

## Scenarios

### Scenario 1: Server pre-loads embedding model ⬜
Given the MCP server is starting up
When initialization begins
Then the embedding model is loaded before accepting connections
And startup time is logged

**Status:** Not started

### Scenario 2: Tool calls respond immediately after init ⬜
Given the MCP server has completed initialization
When a tool call is made (e.g., get_index_stats)
Then the response is returned within 1 second

**Status:** Not started

### Scenario 3: Search works on first call ⬜
Given the MCP server has completed initialization
And the vault is indexed
When search_notes is called with a query
Then results are returned within 1 second

**Status:** Not started

## Technical Approach
1. Add `warmup()` function that pre-loads:
   - Embedding model via `get_model()`
   - ChromaDB collection via `init_db()`
2. Call `warmup()` in `mcp_server.py` before `mcp.run()`
3. Log timing for visibility

## Acceptance Criteria
- [ ] Embedding model loaded at startup (not on first use)
- [ ] ChromaDB connection established at startup
- [ ] Tool calls respond <1s after server ready
- [ ] Startup time visible in logs
