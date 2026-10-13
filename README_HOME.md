# Agentic Home：面向 AI 的单篇项目全景文档

> 用途：让 AI 仅阅读本文，就能理解仓库结构、主要类与函数、调用链、数据模型、配置、运行方式以及当前实现的边界，而不必先逐文件探索。
>
> 源码基线：`af1ac5d`；整理日期：2026-10-13。本文依据当前 Python 源码与配置静态核对，不代表端到端运行验收。路径均相对项目根目录；`路径:行号` 指向该源码基线，不要求读者打开源码才能理解正文。未来实现变更后应同步更新本文。
>
> 阅读范围：覆盖全部 Python 模块、八份 YAML、五份提示词及数据资产用途；不复制运行中的家庭事件、个人 CSV 记录、会话或凭据。设备初值来自代码中的 mock 工厂，不代表当前 `home_state.txt` 的实时内容。

## 目录

1. [项目定位与关键事实](#1-项目定位与关键事实)
2. [完整文件地图与依赖关系](#2-完整文件地图与依赖关系)
3. [端到端执行链与隔离边界](#3-端到端执行链与隔离边界)
4. [统一 Agent：状态、类、方法与路由](#4-统一-agent状态类方法与路由)
5. [前台工具、报告占位与遗留中间件](#5-前台工具报告占位与遗留中间件)
6. [事件主循环与自动化配置](#6-事件主循环与自动化配置)
7. [数字孪生模型与持久化](#7-数字孪生模型与持久化)
8. [MCP 服务与全部设备命令](#8-mcp-服务与全部设备命令)
9. [同步 MCP 客户端与生命周期](#9-同步-mcp-客户端与生命周期)
10. [RAG：入库、检索、总结与数据资产](#10-rag入库检索总结与数据资产)
11. [三个 Streamlit 页面与人工接管](#11-三个-streamlit-页面与人工接管)
12. [模型、提示词、配置与工具函数](#12-模型提示词配置与工具函数)
13. [运行方法、依赖与验证现状](#13-运行方法依赖与验证现状)
14. [已知缺陷与排查索引](#14-已知缺陷与排查索引)
15. [修改项目时的影响面与约束](#15-修改项目时的影响面与约束)

## 1. 项目定位与关键事实

这是一个从扫地机器人客服应用演进而来的 Python 智能家居 Agent 原型。核心技术为 LangGraph、LangChain、Pydantic V2、MCP、SQLite、Chroma、Streamlit 和 Rich。

当前主线是 **Frontend → IoT Supervisor → 独立 Backend Subgraph** 的 Handoff 架构：前台理解意图和对话，后台通过 MCP 操作模拟设备。旧客服 UI、知识库和部分报告逻辑仍留在同一仓库，但使用的也是当前统一 Agent，不是另一套独立运行内核。

| 主题 | 当前代码的事实 |
| --- | --- |
| Agent 构造 | `ReactAgent()` 无参数；不存在 `mode='smart_home'` 或 `mode='customer_service'` 构造参数 |
| Agent 组织 | 主图四个节点，后台子图两个节点；没有 Cleaning/Environment/Entertainment/Query 四类 Worker，也没有 `HomeAgentGraph` 类 |
| 设备真实性 | 所有控制均为 mock：修改 Python 状态对象，没有真实设备 SDK、MQTT、串口或物理执行确认 |
| 设备数量 | mock 工厂生成 3 个房间、9 个设备；支持控制其中 5 种类型 |
| 工具数量 | 前台绑定 4 个工具；当前 MCP 服务注册 5 个工具；客户端动态发现工具 |
| 模型 | 同一基础 `ChatOpenAI` 对象分别绑定前台/后台工具；固定 DeepSeek endpoint；embedding 使用 DashScope |
| 主入口默认行为 | `python main_loop.py` 默认 `demo`，不是 `full`；另有 `simple`、`debug` |
| 自动化 | 文本事件 + 首条关键词规则 + LLM 执行；没有可靠的抢占调度，也不是确定性安全联动系统 |
| 对话持久化 | 主图由 SQLite checkpoint 保存；`thread_id` 是会话标识，不是 OS 线程 |
| 后台上下文 | 每次交接从新消息开始，子图不显式配置 checkpointer；只把最后总结返回主图 |
| 家庭持久化 | `home_state.txt` 内为 JSON；默认每次读取都创建新对象，不是跨进程共享内存 |
| 关键阻断 | 设备控制保存了旧对象；传感器和模式更新未保存；工具返回“成功”不等于状态落盘 |
| 人工接管 | `human_mode` 布尔值控制，非图中断；管理页面仍使用旧中断协议，与当前实现失配 |
| 使用报告 | 模板和占位工具存在，但切换状态、取用户记录和 CSV 数据链没有接通 |
| 工程成熟度 | 当前没有自动化断言测试套件、锁文件、CI 或明确 lint/typecheck 命令 |

本文使用三种表述：**实际行为**来自代码；**静态风险**是依据代码可推导、尚未运行验证的情形；**建议**是未来修改方向，不能当作现有能力。

## 2. 完整文件地图与依赖关系

### 2.1 仓库地图

```text
Agentic-Home/
├── README_HOME.md
├── AGENTS.md
├── .gitignore
├── requirements.txt
├── main_loop.py
├── state_models.py
├── app.py
├── new_app.py
├── admin_app.py
├── home_state.txt
├── md5.txt
├── agent/
│   ├── react_agent.py
│   └── tools/
│       ├── agent_tools.py
│       └── middleware.py
├── mcp_services/
│   └── home_device_mcp_server.py
├── rag/
│   ├── knowledge_service.py
│   └── rag_service.py
├── utils/
│   ├── config_hander.py
│   ├── file_hander.py
│   ├── log.py
│   ├── model_factory.py
│   ├── path_tool.py
│   ├── prompt_loader.py
│   └── sync_mcp_server.py
├── config/
│   ├── agent.yml
│   ├── automation.yml
│   ├── chroma.yml
│   ├── debug_commands.yml
│   ├── home.yml
│   ├── prompts.yml
│   ├── rag.yml
│   └── system.yml
├── prompts/
│   ├── frontend_prompt.txt
│   ├── iot_backend_prompt.txt
│   ├── rag_summarize.txt
│   ├── report_prompt.txt
│   └── system_prompt.txt
└── data/
    ├── 扫地机器人100问.pdf
    ├── 扫地机器人100问2.txt
    ├── 故障排除.txt
    ├── 维护保养.txt
    ├── 选购指南.txt
    └── external/
        └── records.csv
```

编写时没有发现 `tests/`、`test_mcp_client.py`、`test_all_phases.py`、根目录 `mcp_server.py`、`pyproject.toml` 或容器部署配置。`chat_state_db/`、`chroma_db/`、`logs/` 是运行时可能创建的目录，并非当前随仓库交付的预建数据库。

### 2.2 各模块职责

| 文件 | 职责与主要使用者 |
| --- | --- |
| `main_loop.py` | CLI、用户输入、模拟传感器、事件队列、优先级、串行调用 Agent、Rich 输出 |
| `agent/react_agent.py` | `AgentState`、`BackendState`、`ReactAgent`；构图、路由、模型调用、会话与人工模式 |
| `agent/tools/agent_tools.py` | 前台知识检索、报告占位、人工交接、IoT 交接工具 |
| `agent/tools/middleware.py` | 旧 LangChain Agent 中间件，当前显式 StateGraph 未接入 |
| `state_models.py` | 设备/房间/家庭模型、mock 初始化、JSON 读写与重置 |
| `mcp_services/home_device_mcp_server.py` | `SmartHomeDeviceHub` 服务、5 个 MCP tools、5 个设备控制辅助函数 |
| `utils/sync_mcp_server.py` | stdio 子进程、专用事件循环、MCP 会话和异步工具同步包装 |
| `rag/knowledge_service.py` | Chroma 初始化、retriever、文件加载、MD5 去重和切块入库 |
| `rag/rag_service.py` | 检索内容拼接后再调用 LLM 总结 |
| `app.py` | 最简 Streamlit 客服聊天页面 |
| `new_app.py` | 增强聊天页，数据库同步、人工状态、换会话、快捷问题 |
| `admin_app.py` | 按 thread ID 查看消息、旧式人工中断处理页面 |
| `utils/config_hander.py` | 导入时加载全部 8 份 YAML；文件名实际为 `hander`，不是 `handler` |
| `utils/prompt_loader.py` | 导入时加载全部 5 份 prompt |
| `utils/model_factory.py` | 导入时创建聊天与 embedding 全局实例 |
| `utils/path_tool.py` | 从源码位置定位项目根目录并拼接路径 |
| `utils/file_hander.py` | MD5、顶层文件枚举、PDF/TXT Loader |
| `utils/log.py` | 控制台和文件日志；导入即有文件系统副作用 |

### 2.3 依赖与导入副作用

```text
main_loop / 三个 Streamlit 页面
    → ReactAgent
        → model_factory → rag_config → 全部 YAML
        → prompt_loader → 全部 prompt
        → agent_tools → rag_service → KnowledgeService
        → UniversalSyncMCPClient
            → MCP 子进程 → state_models + logger

RAG → DashScope embedding + 本地 Chroma + DeepSeek 文本总结
主图 → SQLite checkpoint
MCP 状态 → home_state.txt
logger → stderr + logs/agent_YYYYMMDD.log
```

`main_loop.py` 在解析 `--mode` 前已经导入 Agent。配置和 prompt 文件读取、日志目录/handler 创建、模型对象构造可能在 import 阶段发生。因此 `demo`“不调用 LLM”不意味着“只依赖 Pydantic”，`--help` 也不能当作完全无副作用的环境检查。

`ReactAgent()` 初始化时无条件启动 MCP 并创建 RAG；即使只处理“你好”，也不是按需跳过设备和向量库初始化。来源：`agent/react_agent.py:55`、`main_loop.py:22`、`utils/model_factory.py:15`。

## 3. 端到端执行链与隔离边界

### 3.1 主图与后台子图

```text
主图（有 SQLite checkpointer）
START → frontend
          ├─ 无待执行工具 → END
          └─ frontend_tools
               ├─ transfer_to_iot_controller → iot_backend → frontend
               ├─ transfer_to_human → human → END
               └─ rag_summarize / fill_context_for_report → frontend

后台子图（未显式配置 checkpointer）
START → iot_agent
          ├─ 无 tool_calls → END
          └─ mcp_tools → iot_agent
```

这里的 `iot_backend` 是主图中的 Supervisor 方法，不是后台模型节点本身。它同步调用 `backend_app.invoke(...)`；子图中的模型节点名为 `iot_agent`。主图虽声明 frontend 可直接到 IoT/human 的条件边映射，但当前 `route_frontend()` 只返回 `end` 或 `frontend_tools`，交接实际先经过工具节点。

### 3.2 用户设备请求：以“打开客厅的灯”为例

1. `execute()` 将本轮请求构造成 `HumanMessage`，通过 thread ID 合入已有主图历史。
2. `frontend_node()` 将前台模板与普通客服基础 prompt 组合，再调用绑定前台工具的模型。
3. 模型生成 `transfer_to_iot_controller(instruction=...)` 调用。
4. `frontend_tools` 执行交接工具。该工具只是返回“已移交”的文本，**没有自己调用 MCP 或跳图**。
5. `route_after_frontend_tools()` 根据 ToolMessage 的 `tool_call_id` 找回工具名，转入 Supervisor。
6. Supervisor 从历史中提取交接 instruction，新建仅有一条任务 HumanMessage 的后台输入。
7. 后台模型调用 `control_device("living_light_001", "on")` 等 MCP 工具，工具执行结果成为后台 ToolMessage。
8. 后台模型不再产生工具调用时结束；Supervisor 取最后一条消息，包装为“【后台设备控制执行完毕】…”的主图 AIMessage。
9. 主图回到前台，前台模型再次生成面向用户的回复。

此为控制路径描述，不代表设备已可靠改变；默认文件模式有保存旧快照的确定性缺陷，见第 7、14 节。后端返回的“执行完毕”标题也只是固定包装，不是任务成功校验。

### 3.3 系统传感器请求

```text
模拟器或 debug 快捷命令
  → emit_event(sensor)
  → 匹配首条规则，补 action_hint / rule_priority
  → PriorityQueue
  → process_message 获取 agent_lock
  → execute(自动化文本, system_thread_id, name="system_monitor")
  → frontend 硬编码生成 IoT 交接调用，不调用前台 LLM
  → 后台子图执行
  → 前台总结 → 终端显示
```

是否走硬编码分支只由消息 `name == "system_monitor"` 决定；代码注释称其“真实事件”，但没有来源认证。未匹配规则的 sensor 事件同样会交接。模拟器只发送文本，不自动调用 MCP `report_sensor_data()` 更新房间模型。

### 3.4 知识问答与人工请求

- 知识咨询：前台模型 → `rag_summarize` → query embedding / Chroma → 独立 LLM 总结 → ToolMessage → 前台模型组织最终回答。
- 人工请求：前台模型 → `transfer_to_human` → 提示 ToolMessage → `human_node` 设置 `human_mode=True` → END。后续公开执行入口返回等待提示，直到状态被人工解除。
- 报告请求：可调用 `fill_context_for_report`，但该函数返回 `None`，不改变 `is_report`；当前路径不会因此切换报告 prompt 或读取 CSV。

### 3.5 三种“状态”不能混淆

| 状态 | 位置 | 隔离和共享方式 |
| --- | --- | --- |
| 用户/系统对话 | 主图 AgentState + SQLite | 按 thread ID 区分；默认 UI ID 可能共享 |
| 一次后台任务历史 | BackendState | 每次 Supervisor 新建；主图只收到最终总结，不合并工具轨迹 |
| 家庭设备状态 | HomeState + JSON 文件 | 所有会话/进程使用同一个文件路径；不随 thread ID 隔离 |

更换会话 ID不会重置设备，重置设备不会清空聊天，重新入库也不会重置前两者。前后台隔离是模型工具绑定与消息历史的逻辑隔离，不是权限系统或操作系统沙箱。

## 4. 统一 Agent：状态、类、方法与路由

源码：`agent/react_agent.py:40`。

### 4.1 状态 schema

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    is_report: bool
    human_mode: bool

class BackendState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

- `add_messages` 通常追加新消息，也按消息 ID 更新已有消息；不能简单视为永远追加的 Python list。
- 节点返回的是局部状态更新。`{"messages": []}` 不会清空历史。
- 两个布尔字段没有自定义 reducer；公开执行入口每次输入都设为 False，但会先检查已保存的人工模式并提前返回。
- 这是 `TypedDict`，不是业务校验用的 Pydantic 模型。图中没有设备状态字段、用户身份字段、审批字段或工具次数计数器。

### 4.2 `ReactAgent.__init__(self)`

顺序为：创建 Rich Console → 硬编码 MCP 脚本路径并启动客户端 → 取 `mcp_tools` → 设置 4 个 `frontend_tools` 和全部 `backend_tools` → 创建 `RagSummarizeService` → 同一 chat model 分别 `bind_tools` → 构建后台图 → 构建主图。

主要属性：`console`、`mcp_client`、`mcp_tools`、`frontend_tools`、`backend_tools`、`rag_service`、`frontend_model`、`backend_model`、`backend_app`、`app`。没有 `mode`、`close()`、上下文管理器或统一的请求锁。

### 4.3 构图方法

| 方法 | 逻辑 |
| --- | --- |
| `_build_backend_graph(self)`，`agent/react_agent.py:131` | 添加 `iot_agent`/`mcp_tools`；`tools_condition` 判断继续工具循环或 END；`compile()` 不传 checkpointer |
| `_build_graph(self)`，`agent/react_agent.py:163` | 按第 3 节构建主图；创建数据库父目录；`sqlite3.connect(..., check_same_thread=False)`；`SqliteSaver(conn)` 编译 |

实际数据库路径为 `chat_state_db/chat_state.db`，来自 `system_config['chat_state_db_path']`。`check_same_thread=False` 允许连接跨线程使用，不等价于应用层并发事务安全。代码没有关闭 SQLite 连接的公开接口，也没有配置任何 human 前后中断点。

### 4.4 `_sanitize_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]`

来源：`agent/react_agent.py:94`。

对每条消息做浅拷贝，保持顺序和其余元数据，只整理 content：

1. list 中的字符串直接拼接；字典有 `text` 时取其值；其他块 `str()`。
2. 消息有非空 tool_calls 时，无论原内容为何，都设为 `""`。
3. 否则 `None` 变空字符串，非字符串变 `str()`。
4. 返回新消息列表，不回写 checkpoint。

不修复孤立工具调用、不补结果、不校验调用 ID、不进行历史裁剪。多模态内容会被文本化；`text` 字段非字符串也可能使拼接失败。注释中的“原地清洗”与实际浅拷贝实现不一致。

### 4.5 节点方法

#### `frontend_node(self, state: AgentState)`

来源：`agent/react_agent.py:253`。

优先分支：最后一条消息 `name == "system_monitor"` 时，直接返回带 IoT tool_call 的 AIMessage：

- instruction 为 `系统告警：{原消息}。请根据标准流程立即处理。`。
- tool_call ID 为 `sys_handoff_{int(time.time())}`，只有秒级精度。
- 不调用前台模型，不先判断是否确需操作。

否则选择基础 prompt：`is_report=True` → 报告模板；最后消息含 `【系统自动化指令` 或 `【系统底层自动化` → 内联内核监控提示；其他 → 扫地机器人客服模板。然后执行 `frontend_prompt.format(system_prompt=base_prompt)`，前置 SystemMessage，清洗历史，调用 `frontend_model.invoke()`。

注意：开头直接访问 `messages[-1]`，没有空历史保护；旧系统标记是文本匹配，用户也能输入；后台总结返回后，最后消息通常不再命中旧标记，前台可恢复普通客服 prompt。没有 token 预算或历史压缩。

#### `iot_backend_node(self, state: AgentState)`

来源：`agent/react_agent.py:311`。

从最新到最旧扫描 AI tool_calls，取一个 `transfer_to_iot_controller` 的 `instruction`，默认值为“执行设备控制任务”；构造 `HumanMessage("请执行以下任务：...")`，同步调用后台图。把后台最后 content 包装成主图 AIMessage，**不是 ToolMessage，也不合并后台工具历史**。

- instruction 必须自足；后台无法直接读取前台完整对话来解析“那个”“再调低一点”。
- 没按本次触发路由的 call ID 精确绑定任务；一批多个交接只处理提取到的一个。
- 若 instruction 恰好等于默认字符串，外层停止条件可能继续向旧历史查找。
- 不校验最终消息是否证明完成；异常直接上抛。
- 没显式向 `backend_app.invoke()` 传 config；嵌套运行配置如何继承依赖框架版本，不应断言有独立固定的后台步数预算。

#### `iot_agent_node(self, state: BackendState)`

来源：`agent/react_agent.py:154`。后台模板 SystemMessage + 清洗后的任务历史 → `backend_model.invoke()` → 返回新增消息。没有结构化计划、审批或设备执行后验校验；是否继续由模型 tool_calls 决定。

#### `mcp_tools_node(self, state: BackendState)`

来源：`agent/react_agent.py:216`。

检查最后消息的全部调用。若名称是任意前台工具，生成对应 ID 的错误 ToolMessage；其余调用打印名称/参数。没有拦截错误时执行 `ToolNode(self.backend_tools).invoke(state)`。

关键边界：只要存在一个前台工具误调用，就返回全部错误消息而不执行任何合法调用。局部变量 `valid_tool_calls` 虽收集了合法调用，却没有被使用。因此混合批次可能出现“打印了执行提示、实际未执行，且合法 call 没有配对 ToolMessage”的历史协议问题。其他未知工具名交给 ToolNode 处理。多个合法工具的执行方式由框架决定，项目没有事务、顺序依赖或回滚保证。

#### `human_node(self, state: AgentState)`

来源：`agent/react_agent.py:344`。只返回 `{"messages": [], "human_mode": True}`，随后 END。没有发消息给真人、创建工单或调用 `interrupt()`。

### 4.6 路由方法

| 方法 | 判定过程 | 边界 |
| --- | --- | --- |
| `route_frontend(self, state) -> str`，`agent/react_agent.py:352` | 最后消息无工具 → `end`；收集其工具 ID 与全历史 ToolMessage ID，全部已完成 → `end`；否则 → `frontend_tools` | 不是业务幂等；ID 重复可误判；部分已完成时仍把整批交给 ToolNode，没有过滤已完成调用 |
| `route_after_frontend_tools(self, state) -> str`，`agent/react_agent.py:384` | 逆序找 ToolMessage，再按 ID 找 AI 调用；IoT → 后台，human → 人工，报告/RAG/其他 → 前台；未找到也回前台 | 依据工具名而非结果是否成功；一批多个调用由首个逆序匹配结果决定唯一去向，没有聚合所有交接 |

“每个请求只能交接一次”仅写在 prompt，没有代码计数器。`recursion_limit=20` 是图执行限制，不是最多 20 次设备操作，也不是旧 prompt 宣称的 5 次工具调用。

### 4.7 对外 API

```python
execute(self, query: str, thread_id: str = "user_001", name: str = None) -> str
execute_stream(self, query: str, thread_id: str = "user_001", name: str = None)
resume_human_mode(self, human_response: str, thread_id: str = "user_001")
```

`execute` / `execute_stream` 共同逻辑：

1. config 带 `configurable.thread_id`、`configurable.rag_service`、`recursion_limit=20`。
2. `app.get_state(config)` 查人工模式；为真则直接返回/产出等待提示，不保存这次用户请求。
3. 否则输入本次 HumanMessage，以及 `is_report=False`、`human_mode=False`。
4. 仅专门捕获 `GraphRecursionError` 并返回循环提示；数据库、模型、网络等其他错误一般上抛。读取当前状态发生在 try 之前。

两种执行方式不同：

| 接口 | 返回口径 |
| --- | --- |
| `execute`，`agent/react_agent.py:476` | `app.invoke()` 后取最后消息 content；不保证该消息是 AIMessage，首次转人工常为 ToolMessage；类型注解为 str，但没有统一强制字符串化 |
| `execute_stream`，`agent/react_agent.py:431` | `app.stream(..., stream_mode='messages')`；只产出 content 非空且 `metadata.langgraph_node == 'frontend'` 的内容 |

流式接口不直接展示 MCP ToolMessage 或后台总结，可能展示前台工具前说明和后续最终回答。第一次转人工若前台只产工具调用、不产文字，等待提示未必出现在流里；框架消息流不是“所有节点输出都原样发给 UI”。

流式返回也未做字符串归一化：代码直接 yield `msg.content`，历史清洗不作用于输出。若模型/框架返回内容块列表，增强 UI 的 `''.join(...)` 可能抛 TypeError；基础 UI 的逐字符遍历也不再符合预期。这是条件性兼容风险，不表示当前 DeepSeek 已产生此类输出。

`resume_human_mode`，`agent/react_agent.py:525`：仅在当前人工模式为真时，设为 False、追加 `('assistant', human_response)`、`app.update_state()`。它实际是“追加人工回复并交还 AI”，不是恢复一个中断中的图；不自动再调用模型。当前管理页面没有使用这个方法。

## 5. 前台工具、报告占位与遗留中间件

### 5.1 当前绑定的全部前台工具

源码：`agent/tools/agent_tools.py:17`。函数经 `@tool` 装饰后作为 LangChain 工具使用。

| 工具签名 | 真正执行内容 | 不执行的内容 |
| --- | --- | --- |
| `rag_summarize(quary: str, config: dict = None) -> str` | 从 `configurable.rag_service` 取服务；没有则新建；调用服务的同名总结方法 | 不是只返回原始文档，而是再经 LLM 总结；不自动入库 |
| `fill_context_for_report()` | 裸 `return`，即 None | 不修改 `is_report`，不加载记录、不切换 prompt |
| `transfer_to_human()` | 返回固定“已呼叫人工客服”提示 | 不通知真人、不自行修改图状态 |
| `transfer_to_iot_controller(instruction: str)` | 返回含任务文本的“已移交”提示 | 不自行调用设备、不直接实现跳转 |

RAG 参数名真实拼写为 **`quary`**，不是 `query`。`config` 用 `dict` 而非 `RunnableConfig` 注解，运行时注入是否按预期发生需结合实际 LangChain 版本核验；不能仅因参数名是 config 就认定预初始化服务必定复用。

### 5.2 未接通的中间件

源码：`agent/tools/middleware.py:12`。

| 函数/装饰器 | 若被接入时的逻辑 |
| --- | --- |
| `monitor_tool(request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage \| Command]) -> ToolMessage \| Command`，`@wrap_tool_call` | 打印名称参数 → handler → 若是报告工具则设 `request.runtime.context['report']=True` → 返回结果；异常记录并重抛 |
| `log_before_model(state: AgentState, runtime: Runtime)`，`@before_model` | 记录消息数和最后 content.strip()，返回 None；空消息/非字符串内容可能出错 |
| `report_prompt_switch(request: ModelRequest)`，`@dynamic_prompt` | 看 `runtime.context['report']`，选择报告或普通系统 prompt |

当前 Agent 没导入/注册这些中间件，没有 `create_agent(..., middleware=...)`，而是手工 `StateGraph + ToolNode`。此外，旧中间件写 `runtime.context['report']`，新图读 `state['is_report']`，两者不是同一个状态通道。只启用其中一段不足以修复报告链。

## 6. 事件主循环与自动化配置

源码：`main_loop.py:30`。

### 6.1 全局对象与事件契约

- `automation_rules`、`debug_commands`：导入配置后取得的列表/字典，不热更新。
- `PRIORITY_HIGH=0`，`PRIORITY_NORMAL=1`，数字小的先出队。
- `event_queue=asyncio.PriorityQueue()`，没有最大长度。
- 初始 `user_thread_id='user_chat_001'`、`system_thread_id='system_auto_001'`。
- `agent_lock=asyncio.Lock()`，对该入口的整条 Agent 链串行化。
- `is_priority_processing` 只被赋值，没有读取方实现中断或抢占。

`emit_event()` 入队数据：

```text
(priority, time.time(), {
    "content": 文本,
    "type": "user" 或 "sensor",
    "metadata": 字典,
    "timestamp": "HH:MM:SS"
})
```

第三方传入其他 event_type 也可入队，但 `process_message` 没有对应业务分支。事件结构无 schema 验证、去重 ID、过期时间、用户身份或可靠持久化。

### 6.2 全部主循环函数

| 函数 | 逻辑和副作用 |
| --- | --- |
| `async emit_event(content: str, event_type: str='user', metadata: Dict[str, Any]=None)`，`main_loop.py:56` | sensor 按配置顺序匹配第一个 `event_keyword in content`，补 action_hint/rule_priority 并决定优先级；非 sensor 才读取 metadata.priority；构造事件入队 |
| `async sensor_simulator_loop()`，`main_loop.py:94` | 每次先 sleep 20 秒，再从 10 条硬编码样例随机选择，拼接房间和事件，作为 sensor 入队；不更新 HomeState |
| `async user_input_loop()`，`main_loop.py:127` | 默认线程池读取 input，strip 后入用户队列；exit/quit/退出调用 `os._exit(0)` |
| `async debug_input_loop()`，`main_loop.py:149` | 同样读取输入，增加本地帮助、快捷 sensor 命令、换会话；不匹配的 `/` 命令报错，普通文本入用户队列 |
| `async agentic_main_loop(mode='full')`，`main_loop.py:203` | 初始化 Agent；debug 只启动调试输入，否则启动用户输入与模拟器；不停取事件并 create_task(process_message) |
| 内部 `async process_message(priority, _, event_data)`，`main_loop.py:241` | 获取 agent_lock；用户用 user ID/name=user 执行；sensor 构造含告警与 action_hint 的任务文本，用 system ID/name=system_monitor 执行；通过 executor 避免阻塞主 loop；打印结果和错误 |
| `async simple_main_loop()`，`main_loop.py:329` | 顺序输入与执行；每次重新生成 `user_{int(time.time())}`；没有传感器；退出用 break；每请求捕获一般异常 |
| `async demo_mode()`，`main_loop.py:383` | 直接导入 MCP Python 函数，查询状态、开客厅灯、报告 30 度、开空调并设 24 度、再次查询；不实例化 Agent，不经过 stdio 或 LLM，但调用写状态逻辑 |

`emit_event` 会原地修改调用者提供的 metadata；sensor 不从 metadata.priority 兜底升级。`time.time()` 不是唯一序号，同优先级且时间戳完全相同的极端情况会继续比较字典，可能抛比较错误。

`simple` 通常每轮新会话，因此不是可靠多轮模式；同秒调用又可能意外共享 ID。`full/debug` 使用稳定的用户/系统 ID，但不同启动实例默认仍会复用这些 ID。

### 6.3 规则表：自然语言建议，不是执行器

来源：`config/automation.yml:7`，按下表顺序首条匹配。

| 关键词 | 优先级 | 发给模型的建议 |
| --- | --- | --- |
| `有人进入` | normal | 检查房间灯光，暗时开灯；检查是否需要开启空调到 26 度 |
| `用户离开` | normal | 关闭该房间灯、空调、电视和窗帘 |
| `烟雾` | high | 关闭厨房电器、全屋灯闪烁并通知用户 |
| `燃气泄漏` | high | 关闭燃气阀相关设备、开排风扇、保持照明 |
| `温度达到 30 度` | normal | 开空调、制冷、24 度 |
| `主刷被缠绕` | high | stop 并报告扫地机故障位置 |

没有数值阈值引擎、规则组合、冲突解决或确定性设备动作序列。低温、变暗、空调运行两小时没有匹配规则，但仍送后台处理。燃气阀、排风扇和灯光闪烁不在当前设备/命令能力内；这些配置不能视为安全自动化保障。

### 6.4 Debug 命令

| 命令 | 行为/生成的事件 |
| --- | --- |
| `/?`、`/help` | 本地显示映射与 `/clear` 帮助，不调用模型 |
| `/clear` | 换为 `user_chat_<秒时间戳>`、`system_auto_<秒时间戳>` |
| `/fire` | 厨房烟雾 |
| `/gas` | 厨房燃气泄漏 |
| `/home` | 客厅有人进入 |
| `/away` | 卧室用户离开 |
| `/hot` | 客厅温度达到 30 度 |
| `/cold` | 卧室温度过低，当前 18 度 |
| `/dark` | 客厅光线变暗 |
| `/stuck` | 客厅扫地机器人主刷被缠绕 |
| `/ac_long` | 客厅空调运行 2 小时 |

映射来源：`config/debug_commands.yml:4`。`/clear` 不在 YAML，而在代码硬编码；它不删 SQLite、不清队列、不取消任务、不重置设备，同秒执行可能生成相同 ID。事件没有记录入队时的 thread ID，等待中的事件可能被后来的换 ID 影响。full 模式不解析快捷命令，`/fire` 在其中只是普通用户文本。

### 6.5 优先级与资源管理的真实限制

主循环每次出队后立即创建任务，任务再等普通 `agent_lock`。当普通任务已离开优先队列并排队等锁时，之后的 high 事件不能重新插到它们前面；也无法打断正在进行的模型/工具调用。优先级只影响仍在 PriorityQueue 中的元素。

未保存 task 引用，没有 `task_done/join`、背压、统一取消或完整清理。输入监听器自身的 EOF 等异常没有局部处理。full/debug 使用 `os._exit`，绕过正常 finally 和客户端关闭。`is_priority_processing` 也不是 finally 恢复，但目前没有消费方。

## 7. 数字孪生模型与持久化

源码：`state_models.py:18`。它更接近带约束的可变状态容器，而非有转移表、守卫条件和自动事件机制的严格状态机。

### 7.1 枚举

- `DeviceType(str, Enum)`：`VACUUM='扫地机'`、`LIGHT='灯光'`、`AIR_CONDITIONER='空调'`、`CURTAIN='窗帘'`、`TV='电视'`、`SPEAKER='音箱'`、`SENSOR='传感器'`。
- `DeviceStatus(str, Enum)`：`RUNNING='运行'`、`STANDBY='待机'`、`FAULT='故障'`、`OFFLINE='离线'`。

音箱和传感器只有类型定义，没有默认实例和控制分发。FAULT/OFFLINE 没有自动检测；控制函数也不会因为当前故障/离线而拒绝直接改为运行。

### 7.2 字段 schema

| 类 | 字段 | 类型、默认值与约束 |
| --- | --- | --- |
| `DeviceState`，`state_models.py:37` | `device_id` | str，必填；没有唯一性/非空验证 |
| | `device_type` | DeviceType，必填 |
| | `status` | DeviceStatus，默认待机 |
| | `power_level` | int，默认 0，构造/校验时限定 0..100 |
| | `last_update` | datetime，每实例 datetime.now()；本地无时区；控制后不自动更新 |
| | `extra_attrs` | Dict[str, Any]，新建空字典；没有按设备类型细分 schema |
| `RoomState`，`state_models.py:51` | `room_name` | str，必填 |
| | `temperature` | float，默认 25.0，无范围约束 |
| | `humidity` | float，默认 50.0，0..100 |
| | `is_occupied` | bool，默认 False |
| | `brightness` | int，默认 0，0..100 |
| | `devices` | List[DeviceState]，新建空列表 |
| `HomeState`，`state_models.py:81` | `rooms` | Dict[str, RoomState]，新建空字典；约定 key 为房间名但没有一致性校验 |
| | `active_events` | List[str]，新建空列表；字段本身不限制长度 |
| | `last_user_command` | Optional[str]，默认 None；当前调用链未写入 |
| | `system_mode` | str，默认 normal；模型层不限定四种模式 |

`DeviceState` 使用 `ConfigDict(use_enum_values=True)`；模型未启用赋值验证，后续直接赋值不自动检查范围。也没有默认值验证保证内存枚举全为字符串；直接赋枚举和从文件验证后的值可能混用。序列化仍按枚举值输出。房间亮度与灯亮度、室温与空调设温均无自动物理联动。

三个模型没有开启 strict 或 `extra='forbid'`。按 Pydantic V2 默认行为，载入时会做允许的类型转换，忽略模型未声明字段；`extra_attrs` 字典内部的自定义键不受这一规则限制。拼错的可选字段可能被忽略并采用默认值，新版 schema 的未知字段也可能在旧版代码载入后再次保存时丢失。

### 7.3 全部模型方法

| 签名 | 逻辑 |
| --- | --- |
| `RoomState.get_device(self, device_id: str) -> Optional[DeviceState]` | 顺序返回该房间首个匹配对象，无则 None |
| `RoomState.add_device(self, device: DeviceState)` | 同房间已有 ID 就静默忽略，否则追加原对象 |
| `RoomState.remove_device(self, device_id: str) -> bool` | 删除首个匹配设备；找到 True，否则 False |
| `HomeState.get_room(self, room_name: str) -> Optional[RoomState]` | 字典 get |
| `HomeState.add_room(self, room: RoomState)` | 按 room_name 写入；同名覆盖，不合并 |
| `HomeState.get_device(self, device_id: str) -> Optional[DeviceState]` | 按房间顺序找首个设备；没有全局 ID 索引 |
| `HomeState.add_event(self, event: str)` | 加 `[HH:MM:SS]` 前缀；追加后只保留最后 50 条 |
| `HomeState.clear_events(self)` | 原地清空列表 |
| `HomeState.init_mock_home(cls) -> HomeState`，classmethod | 新建下节所列房间设备及两条初始化事件 |

这些方法都不自动保存。`add_device` 的去重不作用于直接构造/载入列表，不阻止跨房间重名设备。50 条事件上限只在 `add_event` 时裁剪，载入超长列表不会立即裁剪；事件没有日期、ID、来源、等级或结构化 payload。

### 7.4 Mock 工厂的完整初始设备

房间初始值：

| 房间 | 温度 | 湿度 | 有人 | 房间亮度 |
| --- | --- | --- | --- | --- |
| 客厅 | 26.0 | 55.0 | True | 80 |
| 卧室 | 24.0 | 50.0 | False | 0 |
| 厨房 | 28.0 | 60.0 | False | 100 |

设备初始值，来源 `state_models.py:116`：

| 房间 | device_id | 类型 | 状态/功率 | extra_attrs |
| --- | --- | --- | --- | --- |
| 客厅 | `living_light_001` | 灯光 | 运行 / 80 | color=暖白，brightness=80 |
| 客厅 | `living_ac_001` | 空调 | 运行 / 60 | target_temp=26，mode=制冷 |
| 客厅 | `living_tv_001` | 电视 | 待机 / 0 | channel=1，volume=30 |
| 客厅 | `living_curtain_001` | 窗帘 | 待机 / 0 | position=100 |
| 客厅 | `vacuum_robot_001` | 扫地机 | 待机 / 0 | battery=85，cleaning_mode=标准，current_location=客厅 |
| 卧室 | `bedroom_light_001` | 灯光 | 待机 / 0 | color=暖黄，brightness=0 |
| 卧室 | `bedroom_ac_001` | 空调 | 待机 / 0 | target_temp=24，mode=制冷 |
| 卧室 | `bedroom_curtain_001` | 窗帘 | 待机 / 0 | position=0 |
| 厨房 | `kitchen_light_001` | 灯光 | 运行 / 100 | color=冷白，brightness=100 |

初始事件为“系统初始化完成”“客厅检测到有人”，通过 add_event 加时间前缀。系统模式 normal，last_user_command 为 None。初值写在 Python，不来自 `home.yml`。

### 7.5 持久化函数与实际语义

全局：`USE_FILE_BACKED_STATE=True`；`STATE_FILE_PATH` 为模块所在根目录的 `home_state.txt`；`_global_home_state` 初始 None。

| 函数 | 文件模式（默认） | 内存模式 |
| --- | --- | --- |
| `get_home_state() -> HomeState`，`state_models.py:241` | 每次 UTF-8 读 JSON → `HomeState.model_validate()` → 新对象赋给全局；缺文件或读/解析/校验失败就 mock 初始化并保存 | 首次创建对象，之后返回同一全局对象 |
| `save_home_state(home: Optional[HomeState]=None)`，`state_models.py:266` | 传对象则先替换全局；全局非空时 `open('w')` 覆盖，写 `model_dump_json(indent=4)`；异常只 print，不返回成功状态 | 只可能更新全局引用，不写文件 |
| `reset_home_state()`，`state_models.py:280` | 创建 mock 并保存，覆盖原状态，无备份或确认 | 换成新 mock 对象 |

文件为完整 HomeState JSON，包含设备 last_update 和所有现存 active_events。datetime 转字符串，读取时由 Pydantic 恢复。没有 schema 版本、迁移、增量日志或锁。

跨进程同步其实是“各进程重读同一快照文件”，不是共享 Python 单例。没有原子替换、文件锁、版本号或冲突合并；并发时可丢更新、读到截断内容。任何读取失败都回退 mock 并尝试覆盖，可能把暂时性错误变成状态重置。保存失败不会阻止上层返回成功。

保存只序列化、不重新校验。若直接赋值产生越界字段，可能成功写出 JSON，下一次读取却在 model_validate 时失败，进而重置整个家庭，而非修复单字段。另因先以 `w` 打开文件再执行 model_dump_json，若 extra_attrs 含不可序列化对象，失败时旧文件可能已经被截断。这些是静态可推导的边界，不表示正常 MCP 数值分支必然制造越界值。

### 7.6 默认模式下的关键持久化缺陷

`control_device` 与各 `_control_*` 都调用 `get_home_state()`，但保存外层对象：

```text
control_device:
    A = get_home_state()          → 从文件生成 A
    _control_light:
        B = get_home_state()      → 从同一文件生成 B
        修改 B、向 B 加事件
        返回成功文本
    save_home_state(A)            → 保存未修改 A，覆盖全局引用
```

五类设备都有此问题。默认文件模式中，控制响应可能成功，但后续读取仍是原状态。内存模式两次读取为同一对象，不触发这一特定问题，但也不能实现跨进程共享。

另外 `report_sensor_data()` 和 `set_system_mode()` 修改后没有调用保存，下一次文件重读同样丢失变更。来源：`mcp_services/home_device_mcp_server.py:325`、`mcp_services/home_device_mcp_server.py:346`、`mcp_services/home_device_mcp_server.py:373`、`mcp_services/home_device_mcp_server.py:465`。

## 8. MCP 服务与全部设备命令

### 8.1 服务与协议边界

`mcp_services/home_device_mcp_server.py:25` 创建 `FastMCP('SmartHomeDeviceHub')`，脚本入口 `mcp.run()` 使用 stdio 工作方式。Agent 自动以当前 Python 解释器启动该脚本，不需要预先起一个网络服务器。

公开 tools 全部返回 **str**：部分为 JSON 文本、部分为中文业务结果；MCP 和 LangChain 的外层包装由依赖库负责，不能把这些函数的返回值直接当 Python dict。业务失败多为正常返回的“错误/警告”文本，不是统一异常或 success/code/data schema。

### 8.2 五个公开工具的契约

| Tool | 行为与响应 |
| --- | --- |
| `get_home_status() -> str`，`mcp_services/home_device_mcp_server.py:235` | 读 home，返回 JSON：system_mode、rooms、最近 10 条 active_events、last_user_command；rooms 中每房间含温度/湿度/有人/亮度/devices；设备含 ID/type/status/power_level/extra_attrs，不含 last_update |
| `query_device_by_room(room_name: str) -> str`，`mcp_services/home_device_mcp_server.py:401` | 精确匹配房间，返回 JSON：room_name、温度/湿度/有人/devices；不含房间 brightness、事件、模式和设备 last_update；不存在返回 `{"error":"房间 … 不存在"}` |
| `control_device(device_id: str, command: str) -> str`，`mcp_services/home_device_mcp_server.py:280` | 全局找设备，按类型分发五个控制函数；未找到早退；其他情况调用 `save_home_state(home)` 后返回文本，包含不支持类型/非法命令路径；存在旧对象保存缺陷 |
| `report_sensor_data(room_name: str, event_desc: str) -> str`，`mcp_services/home_device_mcp_server.py:351` | 房间存在则加事件，粗略解析人员与温度，返回确认；不保存、不入主循环队列、不自动控制 |
| `set_system_mode(mode: str) -> str`，`mcp_services/home_device_mcp_server.py:443` | 只接受 normal/away/sleep/party；改字段并追加模式切换事件，返回确认；不保存、不联动设备 |

查询工具也不绝对无副作用：首次状态文件不存在/损坏时，`get_home_state()` 会初始化并保存。

`report_sensor_data` 的具体解析：

- `"有人" in event_desc or "进入" in event_desc` → 有人；否则含“离开”或“无人” → 无人。`没有人`、`有人离开` 可被误判。
- 含“温度”时用 `r'(\d+)度'` 提取整数并转 float；`30 度` 不匹配，`26.5度` 可能取到 5，负数可丢负号，不能识别 ℃。
- 未知房间在加事件之前返回“但事件已记录”，实际没有记录。
- 不更新湿度、光照或故障字段。

### 8.3 五个私有控制函数

共同签名为 `(device_id: str, command: str) -> str`，先再次读取 home，查设备并验证类型；成功时修改对象、加事件。都不自行保存、不更新 last_update、不调用真实硬件。下表是对该函数所持对象的修改，**不是落盘承诺**。

#### `_control_light`，`mcp_services/home_device_mcp_server.py:29`

| command | 对象修改 |
| --- | --- |
| `on` | status=运行；power_level=extra_attrs.brightness，缺该键时用 80 |
| `off` | status=待机；power_level=0；保留 brightness 属性 |
| `brightness:N` | 整数 0..100；brightness=N，power_level=N；N>0 运行，0 待机 |

默认卧室灯 brightness=0，所以 `on` 后可能“运行但亮度/功率仍为 0”。房间 brightness 不跟随变化。

#### `_control_air_conditioner`，`mcp_services/home_device_mcp_server.py:70`

| command | 对象修改 |
| --- | --- |
| `on` | 运行，power_level=60；不改 target_temp；回复读取 target_temp，缺省显示 26 |
| `off` | 待机，power_level=0 |
| `temp:N` | 整数 16..30；target_temp=N，同时运行、power_level=60 |
| `mode:M` | M 为制冷/制热/除湿/送风；只改 mode，不自动开机 |

设温不改变 room.temperature；不存在温控模拟或运行两小时后的自动计时处理。

#### `_control_curtain`，`mcp_services/home_device_mcp_server.py:120`

| command | 对象修改 |
| --- | --- |
| `open` | 运行，power_level=100，position=100 |
| `close` | 待机，power_level=0，position=0 |
| `position:N` | 整数 0..100；position=power_level=N；N>0 运行，0 待机 |

没有运动过程或到位后归待机；“位置百分比”被当作 power_level，不能用于真实功耗计算。

#### `_control_vacuum`，`mcp_services/home_device_mcp_server.py:163`

| command | 对象修改 |
| --- | --- |
| `start` / `clean` | 运行，power_level=80；回复含 battery，缺省显示 100 |
| `stop` | 待机，power_level=0 |
| `charge` | 待机，power_level=0；仅文本声称返回充电座 |
| `mode:M` | M 为标准/强力/安静/拖地；只改 cleaning_mode |

没有电量消耗、返航路径、充电进度、清扫完成事件或位置更新。未知命令提示未列 `clean`，但代码确实支持此别名。

#### `_control_tv`，`mcp_services/home_device_mcp_server.py:205`

仅 `on` → 运行/power_level=100，`off` → 待机/0。虽然 extra_attrs 有 channel/volume，但没有控制这两个属性的命令。

### 8.4 命令与错误处理的共同限制

- device_id、room_name、command 均精确匹配；不做设备别名解析、大小写归一化或整体 strip。
- 亮度、温度、位置使用 `int(command.split(':')[1])`，范围越界返回错误文本；数值分支裸 except 会把其他异常也说成格式错误。
- `brightness:50:extra` 只取第二段，可能被当成 50；参数不是结构化 schema 的独立数值字段。
- command 是一个字符串，MCP schema 不直接表达设备类型对应命令集合和数值范围。
- 没有多操作事务、幂等键、执行确认、失败补偿或危险操作审批。
- system_mode 的场景效果只出现在 docstring：设置 away 不等于已经关灯/关空调。

## 9. 同步 MCP 客户端与生命周期

源码：`utils/sync_mcp_server.py:8`。

### 9.1 `UniversalSyncMCPClient`

| 方法 | 具体逻辑 |
| --- | --- |
| `__init__(self, server_script_path: str)`，`utils/sync_mcp_server.py:13` | 保存路径，新建 asyncio loop，daemon 线程运行 loop；初始化 tools/session/stdio_context；同步调用 `_init_sync()` |
| `_init_sync(self)`，`utils/sync_mcp_server.py:28` | 定义 init_mcp coroutine；以 `sys.executable` + 脚本路径启动 stdio 子进程；手工进入 stdio/session context；initialize；sleep 0.1；`load_mcp_tools`；包装工具；外层 run_coroutine_threadsafe + future.result 等待 |
| 内部 `create_sync_run(async_tool)` / `_sync_run(*args, config=None, run_manager=None, **kwargs)`，`utils/sync_mcp_server.py:52` | config None 变 `{}`；将工具 `_arun(..., config=config, run_manager=None)` 提交专用 loop，`.result()` 同步返回；闭包工厂绑定每个工具，再替换工具私有 `_run` |
| `close(self)`，`utils/sync_mcp_server.py:69` | 提交 coroutine 退出 session 与 stdio context，等待完成，再停 loop，thread.join(timeout=2.0) |

主要成员还包括进入 stdio context 后得到的 `read/write` 流。同步包装不解析工具 JSON，不额外提供重试；丢弃传入 run_manager 是显式兼容处理，但可能损失回调链。

### 9.2 线程边界

```text
终端主线程 asyncio loop
    ├─ 模拟器 / 输入调度 / 事件消费
    └─ 默认 executor 线程
         ├─ 阻塞 input()
         └─ 同步 Agent / LLM / ToolNode
              ↓ run_coroutine_threadsafe + result()
MCP 专用 daemon 线程 / asyncio loop
              ↓ stdio
Python MCP 子进程
              ↓ JSON 文件读写
home_state.txt
```

一个 loop 不意味着多个工具的读改写天然串行事务；主循环锁也不覆盖其他 Streamlit 进程和直接工具调用。

### 9.3 生命周期与兼容性风险

- 初始化、每次工具调用、关闭的 `.result()` 都没有项目层 timeout；`join(2.0)` 无法限制前面的无限等待。
- 构造失败没有 finally 回滚已启动线程/子进程/会话；无重连或工具列表刷新。
- Agent 和三个页面未调用客户端 close；没有自动清理或幂等关闭标志；close 后也没调用 loop.close。
- 替换私有 `_run` 并直接调用私有 `_arun`，对 LangChain/adapter 版本敏感。
- 在专用 loop 所在线程调用同步包装会有等待自身的死锁风险。
- 初始化与关闭使用不同 coroutine Task 手动进入/退出 context，若底层 AnyIO 对 cancel scope Task 所有权有限制，可能出现关闭问题；这是需结合安装版本验证的风险。
- 正常日志走 stderr，但 state_models 读写异常用 print，在 MCP 子进程会写 stdout，可能干扰协议流。

## 10. RAG：入库、检索、总结与数据资产

### 10.1 `KnowledgeService`

源码：`rag/knowledge_service.py:10`。

| 方法 | 逻辑 |
| --- | --- |
| `__init__(self)` | 创建 `Chroma(collection_name, embedding_function, persist_directory)`；构造 `RecursiveCharacterTextSplitter`；属性为 `vector_store` 和拼写原样的 `spliter` |
| `get_retriever(self)` | `vector_store.as_retriever(search_kwargs={'k': topk})`；当前 topk=3；没有显式阈值、过滤、MMR、reranker |
| `load_doc(self)` | 顶层列举允许文件 → MD5 去重 → TXT/PDF 加载 → split_documents → add_documents → 追加 MD5；每文件加载/切分/写入异常记录后继续；无统计返回 |
| 内部 `check_md5(md5_str: str)` | 摘要文件不存在则创建空文件并返回 False；否则逐行 strip 比较 |
| 内部 `save_md5(md5_str: str)` | 以 UTF-8 追加一行摘要 |
| 内部 `file_to_doc(file_path: str)` | 小写 `.txt` 交 txt_loader、`.pdf` 交 pdf_loader，其他返回空列表 |

当前 Agent/RAG 构造过程**不调用 load_doc**，也没有自动入库 CLI。仅初始化 Chroma 不代表知识文件已经索引。

默认 collection=`agent`，目录=`chroma_db`，chunk_size=1000、chunk_overlap=100；来源 `config/chroma.yml:1`。这些单位是文本分割器的长度口径，不是模型 token 限额。

### 10.2 MD5 和切块边界

1. 文件枚举只看 `data/` 顶层，不递归；CSV 子目录不被读取。
2. 粗筛使用 `endswith(('txt','pdf'))`，没有点号/文件类型检查；后续 loader 才要求 `.txt/.pdf`。大小写敏感。
3. MD5 是文件字节级：相同字节不同文件会去重；编码/换行修改也会视为新文件。
4. 修改文档后只追加向量，不删除旧片段；删除文件不会删除索引。
5. MD5 未绑定 collection、embedding 或切块设置，配置变化不触发重建。
6. 向量写入与摘要写入非原子；写库成功、写摘要失败会使下次重复；没有并发锁。
7. 文件枚举和 check_md5 在每文件 try 外，失败可中断整个入库；MD5 返回 None 未被及时拒绝。
8. `md5.txt` 已被 Git 跟踪，但编写时没有 `chroma_db/`。若账本命中而索引缺失，可能跳过必要入库；是否命中需另行核验，本文不声称已发生。
9. YAML 的 `seperators: ['\n\n','\n',...]` 为单引号字符串，`\n` 保持反斜杠和字母，不解释为换行；标点、空格和空字符串仍提供后续切分。拼错的键 `seperators` 被代码原样消费，不能只改一侧。

### 10.3 `RagSummarizeService`

源码：`rag/rag_service.py:8`。

- `__init__(self)`：`self.vecotr_store=KnowledgeService()`；`self.retriver=...get_retriever()`；保存 prompt_text/prompt_template/model/chain。`vecotr_store` 实际是 KnowledgeService，不是 Chroma 对象，两个属性拼写均保持源码原样。
- `_init_chain(self)`：`PromptTemplate | print_prompt | chat_model | StrOutputParser()`。
- 内部 `print_prompt(prompt)`：把完整 prompt（含问题、检索正文、metadata）打印到 stdout，再原样返回。
- `rag_summarize(self, quary: str)`：`retriver.invoke(quary)`；将各 Document 编号为参考资料并拼接 page_content 与 metadata；以 `input/context` 调用 chain，返回字符串。

没有检索结果时仍调用模型；无结构化引用、分数、缓存、rerank 或 token 截断。知识检索需要 query embedding，不是纯本地离线查询。一次知识问题可涉及前台多次聊天调用、一次 embedding、一次额外 RAG 聊天总结。

### 10.4 数据资产与持久化职责

| 资产 | 用途 | 是否自动消费 |
| --- | --- | --- |
| data 下 1 PDF + 4 TXT | 机器人问答、故障、保养、选购知识原文 | 仅显式 load_doc 后入库 |
| `data/external/records.csv` | 遗留使用报告数据资产 | agent.yml 有路径，但当前未接通读取工具 |
| `md5.txt` | 入库摘要账本 | load_doc 使用；不是完整性可信来源 |
| `chroma_db/` | Chroma 向量与相关元数据 | KnowledgeService 创建/查询 |
| `chat_state_db/chat_state.db` | LangGraph 会话 checkpoint | ReactAgent 读写 |
| `home_state.txt` | 全局家庭 JSON 快照 | MCP/state_models 读写 |
| `logs/` | 日志 | 导入 logger 与运行时写入 |

`.gitignore` 虽忽略 MD5、数据库、日志等，但不会取消已跟踪文件；当前 home_state、MD5、外部 CSV 都已跟踪。`.env` 规则不自动覆盖所有 `.env.*` 变体。不要将真实家庭事件、个人记录、密钥或会话提交到版本库。

## 11. 三个 Streamlit 页面与人工接管

三个页面都是顶层 Streamlit 脚本，无应用类；各浏览器 session 缓存一个 ReactAgent，但其 SQLite 文件和家庭文件共享。没有登录、用户身份绑定或设备权限隔离。

### 11.1 `app.py`：基础聊天页

来源：`app.py:10`。

- session_state 保存 `agent`、`message`。
- 重跑时渲染本地历史；输入后追加用户消息，调用 `execute_stream(prompt)`，默认 thread ID `user_001`。
- 内部 `capture(generator, cache_list)` 缓存每个 chunk，再每字符 sleep 0.01 秒输出。
- 输出结束后记录回答并 `st.rerun()`。

缺陷：保存的是 `response_messages[-1]`，不是所有 chunk 拼接，多 chunk 时重绘仅剩最后片段；空流会 IndexError。没有 SQLite 同步、人工回复接收、清空或页面级异常兜底。不同浏览器初始会话共用后端 `user_001`，UI 本地列表独立不代表模型历史独立。

### 11.2 `new_app.py`：增强页面

来源：`new_app.py:47`。

| session_state | 用途 |
| --- | --- |
| `agent` | ReactAgent 实例 |
| `thread_id` | 初始 user_001；清空时改为含 UUID 前八位的新 ID |
| `agent_status` | 在线/人工接管中；有数据库消息时按 human_mode 更新 |
| `message` | 欢迎语或从 checkpoint 重建的 human/ai 内容 |
| `chat_started` | 首次输入标记，之后没有有效业务消费者 |
| `example_question` | 快捷问题按钮在重跑间传递输入 |

每次重跑读取 `app.get_state(config)`，有历史则过滤并展示非空 human/user、ai/assistant 消息，忽略 tool。人工模式尝试用 `streamlit_autorefresh` 每 3 秒刷新，缺包时只显示提示。侧栏提供状态、thread ID、统计、5 个快捷问题和换会话按钮。

输入流程先显示固定的“理解/调用工具/完成”状态和 sleep，并非真实 tracing 回调；内部 `stream_generator(generator, cache_list)` 逐 chunk 缓存、逐字符延迟输出，结束后 `''.join(response_messages)` 保存完整回答。内部计算的 `full_chunk` 未使用。

边界：

- 换会话不删数据库、不重建 Agent，也没重置 agent_status/chat_started；新 thread 无历史时可能残留旧状态文字。
- DB 同步不按 frontend 节点筛选 AIMessage，因此会显示后台包装总结或中间 AI 文字，与流式展示口径不同。
- 首次转人工的 ToolMessage 被过滤，等待提示可能缺失；人工期间输入未被 Agent 保存，刷新后可能消失。
- 人工状态读取和自动刷新注册发生在本轮执行请求之前；流结束后不主动重新读状态或 rerun。因此首次转人工后，页面可能仍显示在线且尚未启动轮询，需要用户刷新或其他交互触发重跑。这与管理员协议失配是两个独立问题。
- “最后活跃”是页面当前执行时间，不是持久化活动时间。
- 反馈按钮位于输入分支，重跑时分支可能消失；即使执行也仅提示感谢，没有存储或学习闭环。

### 11.3 `admin_app.py`：旧式人工后台

来源：`admin_app.py:13`。

输入 thread ID（默认 user_001）→ get_state → 展示 human/tool/AI 历史。判断需要人工的条件是 `"human" in current_state.next`，而不是 human_mode。

- “发送回复”：追加带人工前缀的 assistant 消息，human_mode=True，`update_state(..., as_node='human')`，然后消费 `app.stream(None, config)`。
- “交还 AI”：类似，但 human_mode=False，空回复用固定结束语。
- 无等待节点时只提示 AI 正常处理；没有自动轮询或会话列表。

**当前正常转人工后 human 节点已经执行到 END，next 通常为空，因此页面不会展示处理按钮。** 用户端被 human_mode 阻塞，管理员端却认为无需接管。当前真正可解除状态的 `resume_human_mode()` 未被页面调用。修复需要统一人工状态协议，不是简单增加刷新频率。

## 12. 模型、提示词、配置与工具函数

### 12.1 模型工厂与凭据

来源：`utils/model_factory.py:5`。

| 类/方法 | 返回对象 |
| --- | --- |
| `EmbeddingModelFactory.generator(self)` | `DashScopeEmbeddings(model=rag_config['embbeding_fun_name'])` |
| `ChatModelFactory.generator(self)` | `ChatOpenAI(model=rag_config['chat_model_name'], base_url='https://api.deepseek.com/v1')` |

模块末尾立即创建 `chat_model`、`embedding_model`。当前配置分别为 `deepseek-chat`、`text-embedding-v4`。前后台和 RAG 共用基础聊天模型；没有 provider 选择器，也没有显式 temperature、timeout、max_tokens 或 retry 配置，具体默认值来自 SDK。

项目没有显式读取 `DEEPSEEK_API_KEY`、没有 `.env` 加载器，也没有自动切换 OpenAI endpoint。按 ChatOpenAI 通常的凭据约定，需要把适用于该 DeepSeek endpoint 的凭据放入 `OPENAI_API_KEY`，或未来在代码里显式传入；只设置 DEEPSEEK_API_KEY 不会被本项目主动映射。embedding 通常还需要 `DASHSCOPE_API_KEY`。具体构造期校验行为应以安装版本为准。

### 12.2 五份提示词的实际角色

| 模板 | 主要约束 | 与实现的差异 |
| --- | --- | --- |
| `prompts/frontend_prompt.txt:1` | 设备/实时状态必须交接；知识走 RAG；报告先填上下文；复杂问题转人工；后台回来直接总结，每请求一次交接 | 次数限制没有程序保证；报告工具不注入上下文；嵌入旧客服身份 |
| `prompts/iot_backend_prompt.txt:1` | 静态 9 设备清单、控制例子、只调 MCP；操作完成立即总结；结果含成功/失败视为完成 | 声明了不存在的 get_device_info/get_event_history；漏列真实的 report_sensor_data/set_system_mode；可能让多步任务提前结束 |
| `prompts/system_prompt.txt:1` | 扫地机器人专业客服、ReAct 风格、资料不足继续工具、5 次仍不足则不知道；报告按用户/月/记录流程；要求工具前说明 | 声明天气/定位/用户 ID/月/外部数据工具但未实现/绑定；5 次无代码计数；RAG 参数写 query 而非 quary |
| `prompts/report_prompt.txt:1` | 中文 Markdown 使用情况和保养报告，固定标题“扫地机器人使用情况报告与保养建议”；依据记录给建议 | 依赖缺失的用户/月/外部数据工具；正常公开执行链不可因占位工具自动进入 |
| `prompts/rag_summarize.txt:1` | 使用 input/context，中文纯文本，只按检索资料总结，不推断、不追问、不输出 JSON 包装 | 无空结果分支、输出后验校验或引用验证 |

prompt 的工具清单不是能力真相，应以绑定列表和 MCP 注册为准。后台设备表也不是实时发现的家庭清单；改 mock 或已有 JSON 后不自动改模板。文本规则不是安全/权限边界，检索文档和系统事件文本都不应被视作可信控制指令来源。

### 12.3 全部 YAML 与消费者

`load_config(config_path: str, encoding: str='utf-8')` 使用 `yaml.FullLoader` 读取，不做 schema 验证、默认恢复或热更新。导入 `utils/config_hander.py:11` 时一次加载八个文件。

| 文件 | 当前键/值 | 消费位置与注意点 |
| --- | --- | --- |
| `config/rag.yml` | chat_model_name=deepseek-chat；embbeding_fun_name=text-embedding-v4 | model_factory；embedding 键原本就拼错，代码一致 |
| `config/agent.yml` | chat_model_name=deepseek-chat；external_data_path=data/external/records.csv | 配置已加载，当前无有效业务消费者 |
| `config/home.yml` | chat_model_name=deepseek-chat；home_mcp_server_path=mcp_services/home_device_mcp_server.py | 已加载但未被当前 Agent/状态初始化使用；不含设备、房间或模式初值 |
| `config/system.yml` | chat_state_db_path=./chat_state_db/chat_state.db | ReactAgent 真正读取的系统配置项 |
| 同上 | md5_data_path=./md5.txt；chat_history_path=./chat_history；mcp_server_path=./mcp_server.py；home_mcp_server_path=./mcp_services/home_device_mcp_server.py | 这些项当前未消费；Agent 的 MCP 路径硬编码；旧 mcp_server.py 不存在 |
| `config/chroma.yml` | collection_name=agent；persist_path=chroma_db；topk=3；data_path=data；md5_data_path=md5.txt；allow_knowledge_file_type=[txt,pdf] | KnowledgeService 使用 |
| 同上 | chunk_size=1000；chunk_overlap=100；seperators 为换行字面量、英文/中文标点、空格、空字符串列表 | splitter 使用；YAML 单引号换行问题见第 10 节 |
| 同上 | chat_history_path=chat_history；max_split_char_num=1000 | 当前未消费 |
| `config/prompts.yml` | system_prompt_path、rag_summarize_path、report_prompt_path、frontend_prompt_path、iot_backend_prompt_path，指向五份模板 | prompt_loader 读取；具体键与加载函数必须配套 |
| `config/automation.yml` | rules 列表：event_keyword/action_hint/priority | emit_event 首条关键词匹配 |
| `config/debug_commands.yml` | commands 字典，含两项帮助和九个事件命令 | debug_input_loop |

### 12.4 其余工具函数清单

| 函数 | 行为、错误和副作用 |
| --- | --- |
| `get_project_root()`，`utils/path_tool.py:3` | 根据自身源码绝对路径向上定位根目录 |
| `get_abs_path(relative_path: str)`，`utils/path_tool.py:5` | `os.path.join(root, relative_path)`；不检查存在性、不创建目录、不阻止绝对路径或 `..` 越界 |
| `load_prompts(prompt_type: str)`，`utils/prompt_loader.py:5` | 按配置取路径、UTF-8 读取；未知键/读取失败记日志再抛；导入即读五份模板；不是热加载 |
| `get_file_md5(filepath: str)`，`utils/file_hander.py:7` | 文件存在且为文件时每块 4096 字节算 MD5；错误记日志并返回 None |
| `list_dir_with_allow_type(path: str, allow_type: tuple[str])`，`utils/file_hander.py:26` | os.listdir + endswith，返回路径 tuple；不递归、不排序、不滤目录；无效目录只记日志后仍 listdir，可能抛错 |
| `pdf_loader(file_path: str, pwd=None) -> list[Document]`，`utils/file_hander.py:36` | PyPDFLoader(password=pwd).load；没有 OCR 或扫描件专门处理 |
| `txt_loader(filepath: str) -> list[Document]`，`utils/file_hander.py:38` | 整文件先给 chardet 检测，再由 TextLoader 读取；没有置信度检查/编码兜底，大文件会多次读取 |
| `get_logger(name: str='agent', console_level: int=logging.INFO, file_level: int=logging.DEBUG, log_file=None) -> logging.Logger`，`utils/log.py:20` | logger DEBUG；默认 stderr INFO + UTF-8 文件 DEBUG；已有 handlers 直接返回，后续参数不更新 |

日志模块导入时创建 logs 目录和默认 logger。默认 `logs/{name}_{YYYYMMDD}.log`，包含时间、logger、等级、源码位置、消息；没有午夜自动换文件、大小轮转、保留期或脱敏。父进程和 MCP 子进程可能写同一文件，未做多进程日志协调。RAG 另用 print 输出完整 prompt，Agent/MCP 会记录请求和工具参数。

## 13. 运行方法、依赖与验证现状

本节是代码对应的运行说明，不是“以下命令已经在本次文档任务中执行成功”的声明。

### 13.1 环境与依赖

仓库没有明确 Python 版本约束或锁文件。源码使用现代 Python 类型语法和 Pydantic V2，应选择满足所安装 LangChain/LangGraph/MCP 版本要求的 Python 环境，不能只凭宽泛最低版本推断兼容。

`requirements.txt` 当前 14 项：streamlit==1.55.0、langchain>=0.3.0、langchain-core>=0.3.0、langchain-community>=0.3.0、langchain-openai、langchain-chroma、langchain-text-splitters、langgraph>=0.2.0、mcp>=1.0.0、rich、pydantic>=2.0.0、PyYAML、chardet、dashscope。

下列组件被直接使用或为相应功能所需，但未显式列入 requirements：

| 依赖 | 用途 |
| --- | --- |
| `langgraph-checkpoint-sqlite` | `langgraph.checkpoint.sqlite.SqliteSaver` |
| `langchain-mcp-adapters` | `load_mcp_tools` |
| `pypdf` | PyPDFLoader 运行时解析 PDF |
| `streamlit-autorefresh` | 增强页面人工模式自动刷新，可选但影响体验 |

安装示例会修改 Python 环境并联网；补充依赖不等于已验证版本组合，建议在隔离环境中处理：

```powershell
python -m pip install -r requirements.txt
python -m pip install langgraph-checkpoint-sqlite langchain-mcp-adapters pypdf streamlit-autorefresh
```

凭据按第 12 节配置到进程环境，不应写进仓库。设置 OpenAI 官方凭据不会自动把固定 DeepSeek endpoint 改成 OpenAI 服务。

### 13.2 正确入口与副作用

以下均从项目根目录运行：

| 命令 | 功能与注意 |
| --- | --- |
| `python state_models.py` | 构造局部 mock、查设备、改对象、加事件并打印；该脚本演示分支不调用全局状态读写、不请求 LLM；没有断言，不是完整测试 |
| `python main_loop.py --mode demo` | 直接设备函数演示；不调 LLM，但有导入依赖和写状态路径；受持久化缺陷影响 |
| `python main_loop.py --mode simple` | 仅用户，通常每轮新 thread ID |
| `python main_loop.py --mode debug` | 手动用户/系统事件；适合避免随机模拟干扰，仍会调用模型与工具 |
| `python main_loop.py --mode full` | 用户 + 每 20 秒随机传感器事件 |
| `python mcp_services/home_device_mcp_server.py` | stdio MCP 服务入口，等待 MCP 客户端；非 HTTP 服务、非独立验证脚本 |
| `python -m streamlit run app.py` | 基础 UI |
| `python -m streamlit run new_app.py --server.port 8501` | 增强 UI |
| `python -m streamlit run admin_app.py --server.port 8502` | 管理 UI；当前人工协议仍需修复 |
| `python agent/react_agent.py` | 四个演示请求共用默认 user_001，包含设备控制和 RAG；会联网/写状态，不是只读检查 |

不带 mode 的 main_loop 等于 demo。普通 Agent 构造会自动启动 MCP，通常不应额外手工启动一个无关 stdio 服务来“等待连接”。

显式知识入库：

```powershell
python -c "from rag.knowledge_service import KnowledgeService; KnowledgeService().load_doc()"
```

该命令读取知识文件、调用 embedding API、写 Chroma/MD5/日志。先核对 MD5 与实际索引是否一致；不要盲目删除账本后对已有向量库重跑，否则可能重复。

单次 Agent 调用的正确签名：

```powershell
python -c "from agent.react_agent import ReactAgent; agent = ReactAgent(); print(agent.execute('打开客厅的灯', thread_id='manual_demo_001'))"
```

这会请求模型、保存会话并调用模拟控制；固定演示 ID 再运行时会复用旧历史。不是生产设备操作样例或可靠落盘验证。

### 13.3 测试与验证缺口

当前没有仓库定义的 pytest/unittest 测试文件、Ruff/Flake8/Black/Mypy/Pyright 配置、lint/typecheck 脚本、构建命令、CI 或 pre-commit。`.gitignore` 还忽略整个 `tests/`，后续新增测试要同时处理跟踪规则。

旧文档里的 `test_mcp_client.py`、`test_all_phases.py` 在当前仓库不存在，不能作为可执行测试命令。`state_models.py` 和 Agent 文件末尾只是打印式演示，不自动判断业务正确性。`pip check` 也只能检查依赖关系，不能验证对话、路由或设备持久化。

建议后续建立的测试范围（尚未实现）：

- 临时 JSON 路径隔离：控制后重读、sensor/mode 保存、损坏文件恢复、并发冲突。
- Mock 模型/工具：主图路由、一个请求多个 tool_calls、系统 ID 唯一性、人工状态恢复、流式空输出。
- RAG 临时库：账本与索引不一致、文件更新/删除、空检索、切分符实际值。
- MCP 生命周期：构造失败、子进程退出、timeout、close、混合合法/非法工具。
- UI 会话隔离、完整流式历史、人工页一致性。

运行带设备/入库副作用的验证前应隔离状态路径和数据库。读取源码或解析 AST 与 import 项目不同，后者可能触发外部 SDK 校验和日志创建。

## 14. 已知缺陷与排查索引

以下以“确定的代码问题”和“待运行验证的风险”区分，不把设计承诺当作现成功能。

| 现象/关注点 | 根因与状态 | 优先检查位置 |
| --- | --- | --- |
| 工具说已开灯，查询仍未变化 | 确定：helper 修改新对象 B，外层保存旧 A | `state_models.py:241`；`mcp_services/home_device_mcp_server.py:325` |
| sensor 或系统模式改完又恢复 | 确定：修改后未保存，下一次重读覆盖内存 | `mcp_services/home_device_mcp_server.py:373`、`mcp_services/home_device_mcp_server.py:465` |
| 状态偶尔回 mock/丢变更 | 确定缺少原子写和锁；任何读取失败都重置；并发发生频率未测试 | `state_models.py:245`、`state_models.py:272` |
| 30 度示例不更新温度 | 确定：正则要求数字紧邻“度”，项目示例带空格 | `mcp_services/home_device_mcp_server.py:393`；`main_loop.py:410` |
| 未知房间“已记录”但无事件 | 确定：在 add_event 前早退 | `mcp_services/home_device_mcp_server.py:377` |
| 人工用户等待、管理员无入口 | 确定：human_mode 协议与 current_state.next 中断协议不同 | `agent/react_agent.py:344`；`admin_app.py:34` |
| 报告不按记录生成 | 确定：工具为空、middleware 未接通、公开入口重置 is_report、数据工具缺失 | `agent/tools/agent_tools.py:42`；`agent/tools/middleware.py:26`；`agent/react_agent.py:505` |
| 新环境 RAG 没资料 | 确定没有自动 load_doc；另有已跟踪 MD5 与缺失索引不一致风险 | `rag/knowledge_service.py:25`；`rag/rag_service.py:9` |
| 首次初始化缺包/密钥错误 | requirements 未覆盖全部直接依赖；模型导入期构造且 endpoint 固定 | `requirements.txt:1`；`utils/model_factory.py:11` |
| 后台请求不存在的工具 | prompt 清单与真实注册不一致；模型是否调用取决于输出 | `prompts/iot_backend_prompt.txt:15` |
| 多步任务只做第一步 | prompt 要求出现成功/失败即结束，缺少完成目标校验；属模型行为风险 | `prompts/iot_backend_prompt.txt:32` |
| 合法工具没执行却有执行日志 | 混合批次有非法前台调用时，整个批次提前返回且合法结果缺失 | `agent/react_agent.py:229` |
| 系统任务被当成已执行 | 秒级 sys_handoff ID 可能复用，全历史 ToolMessage ID 去重；碰撞待运行验证 | `agent/react_agent.py:273`、`agent/react_agent.py:362` |
| 紧急事件没有立即执行 | 确定不是抢占式；任务出队后等待普通锁，已等待任务不重排 | `main_loop.py:251`、`main_loop.py:316` |
| 同秒清会话不生效/排队事件串入新会话 | 秒级 ID，处理时读全局 ID，无入队时会话快照 | `main_loop.py:170`、`main_loop.py:264` |
| simple 不记得上句话 | 确定每轮重新生成 thread ID | `main_loop.py:366` |
| UI 不同用户共用历史 | 初始固定 user_001，无身份绑定；并发影响需实测 | `app.py:28`；`agent/react_agent.py:431`；`new_app.py:54` |
| 基础 UI 回复只剩末尾或崩溃 | 确定只存最后 chunk；空流索引越界 | `app.py:40` |
| 改 YAML 的 MCP 路径没用 | 确定 Agent 使用硬编码脚本路径 | `agent/react_agent.py:68` |
| MCP 卡住/退出残留资源 | 没本地 timeout、重连和统一 close 调用；异常触发情况待实测 | `utils/sync_mcp_server.py:57`、`utils/sync_mcp_server.py:65`、`utils/sync_mcp_server.py:69` |
| MCP 协议偶发解析失败 | 状态异常 print 可能污染子进程 stdout；属异常路径风险 | `state_models.py:253`、`state_models.py:277` |
| 设备更新时间没变化 | 确定控制函数从未维护 last_update | `state_models.py:45`；MCP 各控制函数 |
| 模式、亮度、功率语义不一致 | 模式只是标记；power_level 混合负载/位置/亮度；无物理模型联动 | `mcp_services/home_device_mcp_server.py:131`、`mcp_services/home_device_mcp_server.py:443` |

### 14.1 安全与运行边界

当前 MCP 是本地 stdio，不应据此声称已暴露公网；但三个 UI 没有应用层身份/授权，默认会话 ID 共享，不能直接作为多租户服务部署。工具名称隔离、消息 name 和自然语言 prompt 都不是权限认证。

日志会记录用户请求和设备指令，RAG 会打印全文上下文；没有脱敏、加密存储、保留期或审计结果 ID。系统未实现危险操作确认、真机执行反馈、幂等和补偿。若未来接真实设备，必须先补这些机制，不能把“修改对象并返回成功”当成物理设备执行契约。

### 14.2 与旧架构描述的纠偏

不要沿用以下过时认知：构造参数选择两种 Agent 模式、四类 Worker、HomeAgentGraph、每 10 秒传感器、home.yml 定义家庭、system.yml 管理日志、DEEPSEEK/OPENAI key 任意二选一、demo 必定无凭据可启动、现成自定义测试套件、当前人工基于图中断、场景模式自动控制设备。

这些差异来自架构演进后代码/模板/辅助页面未完全同步。`AGENTS.md` 可提供项目约定，但涉及实际行为时应以本文所述当前代码为准。

## 15. 修改项目时的影响面与约束

以下是基于现有实现的开发导航，不代表已完成修复。

| 修改目标 | 应覆盖的位置与检查事项 |
| --- | --- |
| 修复设备持久化 | state_models 读写契约 + control_device/helper 的对象所有权 + sensor/mode 保存；同时考虑锁、原子写与失败返回；不能只看成功文本 |
| 增加设备/类型 | DeviceType、mock 工厂、已有状态文件迁移、控制 helper 与分发、后台设备/命令 prompt、能力测试；只改 mock 不会自动更新已存在 JSON |
| 增加 MCP 工具 | 服务 `@mcp.tool`；下次 Agent 初始化动态发现；同步包装兼容；后台 prompt、结果 schema 和权限边界 |
| 增加前台工具 | agent_tools 定义、frontend_tools 绑定、工具后路由、后台禁止调用名单、prompt；不能只加描述 |
| 增加 Agent/节点 | 两个 StateGraph 的状态 schema、节点、边和 reducer；明确是否隔离后台历史、是否保存 checkpoint、错误和多工具路由 |
| 修复人工功能 | 统一 human_mode 与 UI 协议，决定持续人工还是单次回复交回 AI；处理等待期间消息入库和流式提示 |
| 完成报告功能 | 明确 is_report 生命周期；实现数据读取/用户月份参数；处理 CSV 隐私和缺数据；清理未接通 middleware 与不存在工具声明 |
| 添加自动化事件 | automation 关键词与优先级、debug 映射或模拟器输入；若需更新数字孪生还要显式连接 sensor tool；规则建议必须不超出设备能力 |
| 改优先级/取消 | 处理 PriorityQueue 出队与锁等待之间的脱节；补 task 管理、背压、取消与正常退出；不要把布尔标志当抢占机制 |
| 改模型提供方 | model_factory 的 endpoint、凭据、模型名和 bind_tools/消息兼容；当前实际模型名在 rag.yml，而非 agent/home.yml |
| 改 RAG 资料/embedding | 入库去重、旧向量清理、账本一致性、维度/collection、切分符、空检索、上下文打印；不能只替换文件后假设自动更新 |
| 改会话/多用户 | 为前端提供真实独立 thread ID；明确身份授权、SQLite 并发和家庭状态仍共享的边界；换 ID 不等于删除数据 |
| 新建测试 | 先取消 tests/ 忽略障碍；临时目录隔离家庭/数据库/向量库，使用 mock 模型与工具；不要向真实 API 默认发请求 |

维护时保留现有拼写接口（`quary`、`embbeding_fun_name`、`seperators`、`spliter`、`vecotr_store`、`retriver`），或将生产者与全部消费者一起迁移。不要依据 docstring/prompt 声称存在尚未接通的能力。任何业务修改后，同步本文对应的函数契约、状态流与限制，才能继续把本文当作可靠的单文档上下文。
