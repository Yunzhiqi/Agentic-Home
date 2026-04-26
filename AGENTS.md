# Agent Instructions

## Project Overview

This repo contains **two systems**:
1. **Legacy**: Robot vacuum customer service chatbot (Streamlit apps)
2. **New**: Smart home multi-agent system (Handoff Architecture)

Both systems coexist. The smart home system is the primary focus.

## Smart Home System (Primary)

### Handoff Architecture

The system uses a **Frontend -> IoT Backend** handoff architecture implemented via LangGraph:

1. **`frontend` Node**: The entry point for all user interactions. It understands intent and decides whether to:
   - Handle the request directly (e.g., greetings, general questions).
   - Use **Frontend Tools** (RAG, human transfer, report context).
   - Handoff to the **IoT Backend** for device control.
2. **`iot_backend` Node (Supervisor)**: Acts as a supervisor that extracts instructions and delegates tasks to a separate **Backend Subgraph**.
3. **Backend Subgraph**: A dedicated environment for executing device control tasks using MCP tools, isolated from the frontend conversation history.
4. **`human` Node**: Handles cases where human intervention is requested or required.

### Key Components

- **`state_models.py`**: Digital twin state machine (Pydantic V2). Manages the global `HomeState`.
- **`mcp_services/home_device_mcp_server.py`**: MCP server wrapping physical/mock devices as tools.
- **`agent/react_agent.py`**: Unified React Agent implementing the Handoff Graph and conversation state management.
- **`main_loop.py`**: Event-driven loop that handles both user input and asynchronous sensor events.

### Critical Commands

```bash
# Run the event-driven main loop (Recommended for testing)
python main_loop.py

# Test individual components
python state_models.py                # Test state machine standalone
python mcp_services/home_device_mcp_server.py # Start MCP server (requires MCP client to use)
python -c "from agent.react_agent import ReactAgent; agent = ReactAgent(); print(agent.execute('打开客厅的灯'))" # Test Agent
```

### API Key Setup

The system uses **DeepSeek by default** (configured in `utils/model_factory.py`):
- Set `DEEPSEEK_API_KEY` environment variable.
- Or set `OPENAI_API_KEY` for OpenAI models.
- State management and mock device logic work **without** API keys.

### MCP Server Pattern

- MCP servers run as **stdio subprocesses** via `UniversalSyncMCPClient`.
- `home_device_mcp_server.py` exposes tools for controlling lights, AC, curtains, TV, and vacuum robots.
- Tools are dynamically discovered and loaded into the Backend Subgraph.

### State Management

- **Global singleton**: `get_home_state()` in `state_models.py`.
- **Persistence**: State is saved to `home_state.txt` for cross-run continuity.
- Shared across MCP server and agents.

---

## File Organization (Git Tracked)

```
Root/
├── main_loop.py            # Main entry point (Event-driven loop)
├── state_models.py         # Digital twin state machine
├── app.py, new_app.py      # Legacy Streamlit applications
├── admin_app.py            # Legacy Admin dashboard
├── requirements.txt        # Project dependencies
├── agent/
│   ├── react_agent.py      # Unified Agent (Handoff Graph)
│   └── tools/
│       ├── agent_tools.py  # Frontend tools (RAG, Transfer, etc.)
│       └── middleware.py   # Context management middleware
├── mcp_services/
│   └── home_device_mcp_server.py # Device control MCP server
├── rag/
│   ├── knowledge_service.py# Knowledge base service
│   └── rag_service.py      # RAG implementation
├── prompts/
│   ├── frontend_prompt.txt # Frontend agent system prompt
│   ├── iot_backend_prompt.txt # Backend agent system prompt
│   └── ...                 # Other prompt templates
├── config/
│   ├── agent.yml, home.yml # Agent and Home configurations
│   ├── system.yml          # Path and server configurations
│   └── ...                 # Other YAML configs
├── utils/
│   ├── model_factory.py    # LLM initialization
│   ├── sync_mcp_server.py  # Synchronous MCP client wrapper
│   └── ...                 # Path, config, and log helpers
└── data/
    └── ...                 # Knowledge base docs and external records
```

## Legacy Customer Service System

### Architecture

- `agent/react_agent.py`: Still supports legacy modes via internal routing.
- `rag/`: Vector DB knowledge base (Chroma) used by the `rag_summarize` tool.
- Uses SQLite (`chat_state.db`) for conversation persistence.

## Common Pitfalls

1. **API keys**: Ensure `DEEPSEEK_API_KEY` is set for any LLM-dependent features.
2. **Path handling**: Always use `utils.path_tool.get_abs_path()` for file access to ensure cross-platform compatibility.
3. **State Sync**: The MCP server and the Agent must access the same `home_state.txt` to maintain consistency.
4. **Windows Encoding**: Rich library usage is optimized to avoid GBK codec errors on Windows terminals.
