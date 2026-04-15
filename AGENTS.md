# Agent Instructions

## Project Overview

This repo contains **two systems**:
1. **Legacy**: Robot vacuum customer service chatbot (Streamlit apps)
2. **New**: Smart home multi-agent system (4-phase architecture)

Both systems coexist. The smart home system is the primary focus.

## Smart Home System (Primary)

### Architecture (4 phases)

1. **`state_models.py`**: Digital twin state machine (Pydantic V2)
2. **`home_device_mcp_server.py`**: MCP server wrapping devices as tools
3. **`agent/react_agent.py`**: Unified React Agent with two modes (customer_service and smart_home)
4. **`main_loop.py`**: Event-driven loop with 3 modes

### Critical Commands

```bash
# Test without LLM (no API key needed)
python main_loop.py --mode demo

# Test with LLM (requires OPENAI_API_KEY or DEEPSEEK_API_KEY)
python main_loop.py --mode simple

# Test individual phases
python state_models.py                # Phase 1
python test_mcp_client.py             # Phase 2
python -c "from agent.react_agent import ReactAgent; agent = ReactAgent(mode='smart_home'); print(agent.execute('打开客厅的灯'))"  # Phase 3 (needs API key)
python test_all_phases.py --phase 1   # Run specific test
```

### API Key Setup

The system uses **DeepSeek by default** (configured in `utils/model_factory.py`):
- Set `DEEPSEEK_API_KEY` environment variable
- Or set `OPENAI_API_KEY` for OpenAI models
- Phase 1, 2, and demo mode work **without** API keys

### MCP Server Pattern

- MCP servers run as **stdio subprocesses**
- `home_device_mcp_server.py` exposes 5 tools for device control
- `SyncMCPClient` in `agent/react_agent.py` wraps async MCP calls for sync LangGraph
- Tools are dynamically loaded via `langchain_mcp_adapters`

### State Management

- **Global singleton**: `get_home_state()` in `state_models.py`
- Shared across MCP server and agents
- State persists in memory during runtime
- Reset with `reset_home_state()`

### Device IDs

Hardcoded device IDs in mock data:
- `living_light_001`, `living_ac_001`, `living_tv_001`, `living_curtain_001`
- `bedroom_light_001`, `bedroom_ac_001`, `bedroom_curtain_001`
- `kitchen_light_001`
- `vacuum_robot_001`

### Windows Quirks

- **Encoding issues**: Rich library emojis removed due to GBK codec errors
- **PowerShell**: Use `workdir` parameter instead of `cd && command`
- Test output shows garbled Chinese but tests pass

## Legacy Customer Service System

### Run Commands

```bash
streamlit run app.py         # Basic version
streamlit run new_app.py     # Enhanced version
streamlit run admin_app.py   # Admin version
```

### Architecture

- `agent/react_agent.py`: Unified LangGraph-based agent with two modes:
  - `customer_service`: Original chatbot with tools and RAG
  - `smart_home`: Multi-agent orchestration (Supervisor + 4 Workers)
- `mcp_server.py`: Original MCP server for robot vacuum data
- `rag/`: Vector DB knowledge base (Chroma)
- Uses SQLite checkpointer for conversation state

## Config System

All configs in `config/*.yml`:
- `rag.yml`: Model names (deepseek-chat, text-embedding-v4)
- `system.yml`: Paths to MCP servers and DB
- `agent.yml`: External data paths
- `home.yml`: Smart home specific config

Loaded via `utils/config_hander.py` using `get_abs_path()` helper.

## Testing

- **Phase tests**: `test_all_phases.py --phase N` (1-4)
- **MCP client test**: `test_mcp_client.py` (async, needs MCP server)
- **State machine test**: `python state_models.py` (standalone)
- Tests use `[OK]`, `[FAIL]`, `[SKIP]` markers (no Unicode checkmarks)

## Common Pitfalls

1. **API key errors**: Phase 3+ need `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`
2. **Import paths**: All modules use `project_root` injection via `sys.path.insert(0, project_root)`
3. **MCP server path**: Must use `get_abs_path()` for cross-platform compatibility
4. **Async/sync mixing**: MCP tools are async but LangGraph nodes are sync - use `SyncMCPClient`
5. **State isolation**: Each test run shares global state - reset if needed

## File Organization

```
Root level: Smart home system (state_models.py, home_device_mcp_server.py, main_loop.py)
agent/: Unified React Agent (supports both customer service and smart home modes)
utils/: Shared utilities (config, logging, path helpers)
config/: YAML configs
rag/: Vector DB for legacy system
```

## Development Notes

- **No requirements.txt**: Dependencies listed in README_HOME.md
- **Pydantic V2**: Use `ConfigDict` not `class Config`
- **LangGraph**: Uses `StateGraph` with conditional edges
- **Rich output**: Avoid emojis on Windows terminals
