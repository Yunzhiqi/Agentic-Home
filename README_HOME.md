# 智能家居系统 README

## 项目概述

本项目已从智能客服系统升级为**智能家居系统**，实现了多智能体协作、全局状态机、主动规划与事件驱动、扩展 MCP 生态。

## 核心架构

### 四大核心模块

1. **数字孪生全局状态机** (`state_models.py`)
   - 使用 Pydantic V2 定义家庭环境的虚拟状态
   - 包含设备状态、房间状态、家庭全局状态
   - 支持设备类型：扫地机、灯光、空调、窗帘、电视、音箱、传感器

2. **虚拟设备总线 MCP Server** (`home_device_mcp_server.py`)
   - 基于 MCP 协议将智能设备包装成独立服务
   - 提供 5 个核心工具：
     - `get_home_status`: 获取完整家居状态
     - `control_device`: 控制指定设备
     - `report_sensor_data`: 报告传感器事件
     - `query_device_by_room`: 查询房间设备
     - `set_system_mode`: 设置系统模式

3. **统一 React Agent** (`agent/react_agent.py`)
   - 支持两种运行模式：
     - `customer_service`: 客服模式（原有功能）
     - `smart_home`: 智能家居模式（多智能体协作）
   - 智能家居模式基于 LangGraph 构建 Supervisor + Worker 架构
   - Supervisor：任务路由和协调
   - Worker Agents：
     - `Cleaning_Agent`: 清洁任务（扫地机器人）
     - `Environment_Agent`: 环境控制（灯光、空调、窗帘）
     - `Entertainment_Agent`: 娱乐设备（电视、音箱）
     - `Query_Agent`: 状态查询

4. **事件驱动主循环** (`main_loop.py`)
   - 使用统一的 ReactAgent（智能家居模式）
   - 支持用户输入和传感器事件双向触发
   - 三种运行模式：
     - `full`: 完整模式（用户 + 传感器模拟）
     - `simple`: 简化模式（仅用户对话）
     - `demo`: 演示模式（无需 LLM）

## 快速开始

### 1. 环境配置

```bash
# 安装依赖
pip install pydantic langchain langgraph langchain-openai mcp rich

# 配置 API 密钥（二选一）
export OPENAI_API_KEY="your-api-key"
export DEEPSEEK_API_KEY="your-deepseek-key"
```

### 2. 测试各阶段功能

```bash
# 阶段一：测试数字孪生状态机
python state_models.py

# 阶段二：测试 MCP Server
python test_mcp_client.py

# 阶段三：测试统一 Agent（需要配置 API 密钥）
python -c "from agent.react_agent import ReactAgent; agent = ReactAgent(mode='smart_home'); print(agent.execute('打开客厅的灯'))"

# 阶段四：运行主循环
python main_loop.py --mode demo    # 演示模式（无需 LLM）
python main_loop.py --mode simple  # 简化模式（需要 API 密钥）
python main_loop.py --mode full    # 完整模式（需要 API 密钥）

# 运行完整测试套件
python test_all_phases.py --phase 1   # 测试阶段一
python test_all_phases.py --phase 2   # 测试阶段二
python test_all_phases.py --phase 3   # 测试阶段三（需要 API 密钥）
python test_all_phases.py --phase 4   # 测试阶段四（需要 API 密钥）
```

## 项目结构

```
Agentic Home/
├── state_models.py              # 阶段一：数字孪生状态机
├── home_device_mcp_server.py    # 阶段二：MCP Server（位于 mcp_services/）
├── main_loop.py                 # 阶段四：事件驱动主循环
├── test_mcp_client.py           # MCP Server 测试脚本
├── test_all_phases.py           # 完整测试套件
├── config/
│   ├── home.yml                 # 智能家居配置
│   ├── system.yml               # 系统配置
│   ├── rag.yml                  # RAG 配置
│   └── agent.yml                # Agent 配置
├── agent/
│   ├── react_agent.py           # 阶段三：统一 React Agent（支持客服和智能家居两种模式）
│   └── tools/
│       └── agent_tools.py       # 原客服工具集（保留）
├── mcp_services/
│   └── home_device_mcp_server.py # MCP Server 主文件
├── utils/
│   ├── model_factory.py         # 模型工厂（默认使用 DeepSeek）
│   ├── config_hander.py         # 配置处理
│   ├── log.py                   # 日志工具
│   ├── sync_mcp_server.py       # MCP 同步客户端
│   ├── file_hander.py           # 文件处理工具
│   ├── path_tool.py             # 路径工具
│   └── prompt_loader.py         # Prompt 加载器
├── prompts/                     # Prompt 模板目录
├── data/                        # 数据文件目录
├── rag/                         # RAG 向量数据库（原客服系统）
├── tests/                       # 测试文件目录
├── chat_state_db/               # 对话状态数据库
├── chroma_db/                   # Chroma 向量数据库
├── logs/                        # 日志目录
├── .gitignore                   # Git 忽略规则
├── AGENTS.md                    # Agent 指令文档
└── README_HOME.md               # 本文档
```

## 使用示例

### 演示模式（无需 API 密钥）

```bash
python main_loop.py --mode demo
```

输出示例：
```
1. 查看初始家居状态
系统模式: normal
房间数量: 3

2. 模拟用户指令：打开客厅灯光
执行结果: 成功：灯光 living_light_001 已打开，亮度 80%

3. 模拟传感器事件：检测到客厅温度过高
事件记录: 成功：已记录事件 [客厅] 温度达到 30 度

4. 模拟自动响应：打开客厅空调
执行结果: 成功：空调 living_ac_001 已开启，目标温度 26°C
温度调节: 成功：空调 living_ac_001 温度已设置为 24°C
```

### 简化模式（需要 API 密钥）

```bash
python main_loop.py --mode simple
```

交互示例：
```
You: 我准备看电影了
Agent: 好的，我已经为您调整了客厅环境：
- 客厅灯光亮度降低到 20%
- 客厅窗帘已关闭
现在可以享受观影时光了！
```

### 完整模式（需要 API 密钥）

```bash
python main_loop.py --mode full
```

特点：
- 支持用户输入（绿色显示）
- 自动触发传感器事件（红色显示）
- Agent 主动响应环境变化（黄色显示）

## 设备列表

### 客厅
- `living_light_001`: 灯光
- `living_ac_001`: 空调
- `living_tv_001`: 电视
- `living_curtain_001`: 窗帘
- `vacuum_robot_001`: 扫地机器人

### 卧室
- `bedroom_light_001`: 灯光
- `bedroom_ac_001`: 空调
- `bedroom_curtain_001`: 窗帘

### 厨房
- `kitchen_light_001`: 灯光

## 控制命令

### 灯光
- `on`: 打开
- `off`: 关闭
- `brightness:50`: 调整亮度到 50%

### 空调
- `on`: 打开
- `off`: 关闭
- `temp:26`: 设置温度到 26°C
- `mode:制冷`: 切换模式（制冷/制热/除湿/送风）

### 窗帘
- `open`: 打开
- `close`: 关闭
- `position:50`: 调整位置到 50%

### 扫地机器人
- `start` / `clean`: 开始清扫
- `stop`: 停止清扫
- `charge`: 返回充电
- `mode:标准`: 切换模式（标准/强力/安静/拖地）

### 电视
- `on`: 打开
- `off`: 关闭

## 系统模式

- `normal`: 正常模式
- `away`: 离家模式（关闭大部分设备）
- `sleep`: 睡眠模式（降低灯光，调整空调）
- `party`: 派对模式（增强灯光效果）

## 配置系统

所有配置通过 YAML 文件管理，位于 `config/` 目录：

### 配置文件说明

1. **`home.yml`** - 智能家居配置
   - 设备列表和初始状态
   - 房间配置
   - 系统模式定义

2. **`system.yml`** - 系统配置
   - MCP Server 路径
   - 数据库路径
   - 日志配置

3. **`rag.yml`** - RAG 配置（原客服系统）
   - 模型名称（deepseek-chat, text-embedding-v4）
   - 向量数据库配置

4. **`agent.yml`** - Agent 配置
   - 外部数据路径
   - Agent 参数配置

配置通过 `utils/config_hander.py` 加载，使用 `get_abs_path()` 确保跨平台兼容性。

## 扩展开发

### 添加新设备

1. 在 `state_models.py` 中添加设备类型到 `DeviceType` 枚举
2. 在 `mcp_services/home_device_mcp_server.py` 中添加控制函数
3. 在 `control_device` 工具中添加设备类型分发逻辑

### 添加新 Agent

1. 在 `agent/react_agent.py` 的 `HomeAgentGraph` 类中定义新的 Agent Prompt
2. 创建新的 Agent 节点方法
3. 在图构建中添加节点和路由逻辑

### 添加新传感器事件

在 `main_loop.py` 的 `sensor_simulator_loop` 中添加事件到 `sensor_events` 列表

## 技术栈

- **状态管理**: Pydantic V2
- **MCP 协议**: FastMCP
- **多智能体**: LangGraph
- **LLM**: DeepSeek（默认） / OpenAI
- **UI**: Rich（Windows 下禁用 emoji）
- **异步**: asyncio
- **配置管理**: YAML + 自定义配置处理器
- **数据库**: SQLite（对话状态）, Chroma（向量数据库）
- **测试框架**: 自定义测试套件

## 注意事项

1. **API 密钥**：
   - 演示模式（demo）不需要 API 密钥，可直接运行
   - 简化模式（simple）和完整模式（full）需要配置 DeepSeek 或 OpenAI API 密钥
   - 系统默认使用 DeepSeek（在 `utils/model_factory.py` 中配置）

2. **Windows 系统**：
   - Windows 终端可能需要设置 UTF-8 编码以正确显示中文
   - 使用 PowerShell 时，避免使用 `cd && command` 模式，使用 `workdir` 参数
   - Rich 库的 emoji 已移除，避免 GBK 编码错误

3. **文件路径**：
   - 所有配置路径使用 `utils/config_hander.py` 中的 `get_abs_path()` 函数
   - 确保 MCP Server 路径正确配置在 `config/system.yml` 中

4. **状态管理**：
   - 全局状态通过 `state_models.py` 中的 `get_home_state()` 单例管理
   - 测试时注意状态隔离，可使用 `reset_home_state()` 重置

5. **异步/同步处理**：
   - MCP 工具是异步的，但 LangGraph 节点是同步的
   - 使用 `utils/sync_mcp_server.py` 中的 `SyncMCPClient` 包装异步调用

6. **测试**：
   - 传感器模拟器每 10 秒触发一次事件
   - 测试输出使用 `[OK]`、`[FAIL]`、`[SKIP]` 标记，避免 Unicode 字符问题

## 原客服系统

原智能客服系统的代码已保留，可通过以下方式运行：

```bash
# 运行原客服系统
streamlit run app.py           # 基础版
streamlit run new_app.py       # 增强版
streamlit run admin_app.py     # 管理员版
```

## 开发者

本项目基于原智能客服系统改造，升级为智能家居系统，实现了：
- ✅ 数字孪生全局状态机
- ✅ MCP 设备总线
- ✅ 多智能体协作
- ✅ 事件驱动主循环
- ✅ 主动规划与响应

## License

MIT
