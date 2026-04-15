"""
统一的 React Agent 系统
采用"前台接待(Frontend) -> 后台执行(IoT Backend)"的 Handoff 交接架构
"""
from typing import Annotated, TypedDict, Sequence
import sys
import os

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError

# 确保能够正常导入项目内部模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.path_tool import get_abs_path
from utils.config_hander import system_config
from utils.model_factory import chat_model
from utils.prompt_loader import system_prompt, report_prompt, frontend_prompt, iot_backend_prompt
from utils.log import logger
from agent.tools.agent_tools import (
    rag_summarize, 
    fill_context_for_report, 
    transfer_to_human,
    transfer_to_iot_controller
)
from utils.sync_mcp_server import UniversalSyncMCPClient


# ==========================================
# 统一状态定义
# ==========================================
class AgentState(TypedDict):
    """统一的 Agent 状态"""
    messages: Annotated[list[BaseMessage], add_messages]
    is_report: bool
    human_mode: bool


# ==========================================
# 统一的 React Agent
# ==========================================
class ReactAgent:
    def __init__(self):
        """
        初始化统一的 React Agent
        采用前台接待 + 后台执行的 Handoff 架构
        """
        logger.info("[ReactAgent] 初始化统一 Agent（Handoff 架构）")
        
        # 初始化 MCP 客户端（智能家居设备控制）
        logger.info("[MCP] 正在连接智能家居 MCP Server...")
        # home_mcp_path = system_config.get("home_mcp_server_path", "home_device_mcp_server.py")
        # self.mcp_client = UniversalSyncMCPClient(get_abs_path(home_mcp_path))
        mcp_server_file = "mcp_services/home_device_mcp_server.py" 
        self.mcp_client = UniversalSyncMCPClient(get_abs_path(mcp_server_file))
        self.mcp_tools = self.mcp_client.tools
        logger.info(f"[MCP] 成功拉取到 {len(self.mcp_tools)} 个智能家居工具")
        
        # 工具物理隔离
        # 前台工具：聊天、知识库、报告、转接
        self.frontend_tools = [
            rag_summarize, 
            fill_context_for_report, 
            transfer_to_human,
            transfer_to_iot_controller
        ]
        
        # 后台工具：仅 MCP 设备控制工具
        self.backend_tools = self.mcp_tools
        
        # 绑定工具到模型
        self.frontend_model = chat_model.bind_tools(self.frontend_tools)
        self.backend_model = chat_model.bind_tools(self.backend_tools)
        
        # 构建统一的 LangGraph
        self._build_graph()
        
        logger.info("[ReactAgent] 初始化完成")
    
    def _build_graph(self):
        """构建统一的 LangGraph"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("frontend", self.frontend_node)
        workflow.add_node("iot_backend", self.iot_backend_node)
        workflow.add_node("frontend_tools", ToolNode(self.frontend_tools))
        workflow.add_node("mcp_tools", ToolNode(self.backend_tools))
        workflow.add_node("human", self.human_node)
        
        # 设置边和路由
        # 起点 -> 前台
        workflow.add_edge(START, "frontend")
        
        # 前台 -> 条件路由
        workflow.add_conditional_edges(
            "frontend",
            self.route_frontend,
            {
                "frontend_tools": "frontend_tools",
                "iot_backend": "iot_backend",
                "human": "human",
                "end": END
            }
        )
        
        # 前台工具执行后 -> 条件路由
        workflow.add_conditional_edges(
            "frontend_tools",
            self.route_after_frontend_tools,
            {
                "iot_backend": "iot_backend",
                "human": "human",
                "frontend": "frontend"
            }
        )
        
        # 后台 -> 条件路由
        workflow.add_conditional_edges(
            "iot_backend",
            self.route_backend,
            {
                "mcp_tools": "mcp_tools",
                "frontend": "frontend"
            }
        )
        
        # MCP 工具执行后 -> 返回后台
        workflow.add_edge("mcp_tools", "iot_backend")
        
        # 人工节点 -> 结束
        workflow.add_edge("human", END)
        
        # 编译图，使用 SQLite checkpointer
        db_path = get_abs_path(system_config["chat_state_db_path"])
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path, check_same_thread=False)
        memory = SqliteSaver(conn)
        
        self.app = workflow.compile(checkpointer=memory)
        logger.info("[Graph] LangGraph 编译完成")
    
    # ==========================================
    # 节点定义
    # ==========================================
    def frontend_node(self, state: AgentState):
        """前台接待节点：负责理解用户需求并分流"""
        logger.info("[Frontend] 处理用户请求...")
        
        messages = state["messages"]
        is_report = state.get("is_report", False)
        
        # 选择[REDACTED]
        if is_report:
            base_prompt = report_prompt
        else:
            base_prompt = system_prompt
        
        # 构建前台提示词
        frontend_system_prompt = frontend_prompt.format(system_prompt=base_prompt)
        system_msg = SystemMessage(content=frontend_system_prompt)
        
        messages_with_system = [system_msg] + list(messages)
        
        # 修复：遍历清理非字符串格式的内容，避免 DeepSeek 报错
        # 只转换 HumanMessage 和 AIMessage 的 content，保留 ToolMessage 的结构
        from langchain_core.messages import HumanMessage, AIMessage
        for msg in messages_with_system:
            if isinstance(msg.content, list):
                # 如果是 HumanMessage 或 AIMessage，转换 content 为字符串
                if isinstance(msg, (HumanMessage, AIMessage)):
                    msg.content = str(msg.content)
                # 注意：ToolMessage 的 content 可能是列表，但不应转换，因为会被 ToolNode 处理
                # SystemMessage 的 content 应该是字符串
        
        # 调试：打印消息类型
        logger.debug(f"[Frontend] 发送给模型的消息数量: {len(messages_with_system)}")
        for i, msg in enumerate(messages_with_system):
            logger.debug(f"[Frontend] 消息 {i}: type={type(msg).__name__}, content_type={type(msg.content).__name__ if hasattr(msg, 'content') else 'N/A'}")
        
        response = self.frontend_model.invoke(messages_with_system)
        
        logger.info(f"[Frontend] 响应生成，是否有工具调用: {bool(getattr(response, 'tool_calls', []))}")
        
        return {"messages": [response]}
    
    def iot_backend_node(self, state: AgentState):
        """后台设备控制节点：负责执行具体的设备操作"""
        logger.info("[IoT Backend] 执行设备控制任务...")
        
        messages = state["messages"]
        
        # 构建后台提示词
        system_msg = SystemMessage(content=iot_backend_prompt)
        messages_with_system = [system_msg] + list(messages)
        
        # 修复：遍历清理非字符串格式的内容，避免 DeepSeek 报错
        # 只转换 HumanMessage 和 AIMessage 的 content，保留 ToolMessage 的结构
        from langchain_core.messages import HumanMessage, AIMessage
        for msg in messages_with_system:
            if isinstance(msg.content, list):
                # 如果是 HumanMessage 或 AIMessage，转换 content 为字符串
                if isinstance(msg, (HumanMessage, AIMessage)):
                    msg.content = str(msg.content)
                # 注意：ToolMessage 的 content 可能是列表，但不应转换，因为会被 ToolNode 处理
        
        response = self.backend_model.invoke(messages_with_system)
        
        logger.info(f"[IoT Backend] 响应生成，是否有工具调用: {bool(getattr(response, 'tool_calls', []))}")
        
        return {"messages": [response]}
    
    def human_node(self, state: AgentState):
        """人工接管节点"""
        logger.info("[Human] 转接人工客服...")
        return {"messages": [], "human_mode": True}
    
    # ==========================================
    # 路由逻辑
    # ==========================================
    def route_frontend(self, state: AgentState) -> str:
        """前台节点的条件路由"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # 检查是否有工具调用
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            logger.info("[Route] 前台无工具调用，结束对话")
            return "end"
        
        # 检查是否所有工具调用都有对应的 ToolMessage
        tool_calls = last_message.tool_calls
        tool_call_ids = {call.get("id") for call in tool_calls}
        
        # 收集所有 ToolMessage 的 tool_call_id
        completed_tool_call_ids = set()
        for msg in messages:
            if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                completed_tool_call_ids.add(msg.tool_call_id)
        
        # 如果所有工具调用都已完成，则结束对话
        if tool_call_ids.issubset(completed_tool_call_ids):
            logger.info(f"[Route] 所有工具调用已完成: {tool_call_ids}，结束对话")
            return "end"
        
        # 否则，路由到 frontend_tools 执行未完成的工具
        pending_ids = tool_call_ids - completed_tool_call_ids
        tool_names = [call.get("name") for call in tool_calls if call.get("id") in pending_ids]
        
        logger.info(f"[Route] 前台工具调用: {tool_names}, 待完成 IDs: {pending_ids}，路由到 frontend_tools 执行")
        return "frontend_tools"
    
    def route_after_frontend_tools(self, state: AgentState) -> str:
        """前台工具执行后的路由"""
        messages = state["messages"]
        
        # 从后往前查找最近执行的工具消息（ToolMessage）
        for msg in reversed(messages):
            # 检查是否是 ToolMessage（通过 tool_call_id 属性判断）
            if hasattr(msg, "tool_call_id"):
                # ToolMessage 可能包含工具执行结果，但我们需要知道是哪个工具
                # 查找对应的 AssistantMessage 中的 tool_calls 来获取工具名称
                tool_call_id = msg.tool_call_id
                
                # 查找对应的 AssistantMessage 中的 tool_call 信息
                for prev_msg in reversed(messages):
                    if hasattr(prev_msg, "tool_calls") and prev_msg.tool_calls:
                        for tool_call in prev_msg.tool_calls:
                            if tool_call.get("id") == tool_call_id:
                                tool_name = tool_call.get("name", "")
                                
                                # 如果执行的是 transfer_to_iot_controller，路由到后台
                                if tool_name == "transfer_to_iot_controller":
                                    logger.info("[Route] 检测到 transfer_to_iot_controller 执行完毕，路由到 iot_backend")
                                    return "iot_backend"
                                
                                # 如果执行的是 transfer_to_human，路由到人工
                                if tool_name == "transfer_to_human":
                                    logger.info("[Route] 检测到 transfer_to_human 执行完毕，路由到 human")
                                    return "human"
                                
                                # 如果执行的是 fill_context_for_report，返回前台
                                if tool_name == "fill_context_for_report":
                                    logger.info("[Route] 检测到 fill_context_for_report 执行完毕，返回前台")
                                    return "frontend"
                                
                                # 其他工具（如 rag_summarize）执行完毕，返回前台
                                logger.info(f"[Route] 工具 {tool_name} 执行完毕，返回前台")
                                return "frontend"
        
        # 如果没有找到有效的 ToolMessage，可能是工具执行有问题
        logger.warning("[Route] 未找到有效的工具执行结果，返回前台")
        return "frontend"
    
    def route_backend(self, state: AgentState) -> str:
        """后台节点的条件路由"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # 检查是否有工具调用
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info("[Route] 后台需要执行 MCP 工具")
            return "mcp_tools"
        
        # 没有工具调用，说明后台任务完成，返回前台组织回复
        logger.info("[Route] 后台任务完成，返回前台")
        return "frontend"
    
    # ==========================================
    # 统一的执行接口
    # ==========================================
    def execute_stream(self, query: str, thread_id: str = "user_001"):
        """
        流式执行（支持 Streamlit 等流式场景）
        
        Args:
            query: 用户查询
            thread_id: 线程ID（用于会话记忆）
            
        Yields:
            Agent 的流式回复
        """
        logger.info(f"[ReactAgent] 收到用户请求: {query}")
        
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
        
        # 检查是否处于人工模式
        current_state = self.app.get_state(config)
        if current_state and current_state.values.get("human_mode", False):
            logger.warning("[Human Mode] 当前处于人工模式，等待人工客服回复")
            yield "系统提示：您的问题已转接人工客服，请耐心等待..."
            return
        
        inputs = {
            "messages": [HumanMessage(content=query)],
            "is_report": False,
            "human_mode": False
        }
        
        try:
            for msg, metadata in self.app.stream(inputs, config=config, stream_mode="messages"):
                # 只输出前台节点的内容
                if msg.content and metadata.get("langgraph_node") == "frontend":
                    yield msg.content
        except GraphRecursionError:
            logger.error("[Graph Error] 触发最大递归限制")
            yield "\n\n【系统提示】抱歉，我遇到了一些复杂的问题，思考过程陷入了循环。请您换一种方式提问，或要求转接人工客服。"
    
    def execute(self, query: str, thread_id: str = "user_001") -> str:
        """
        同步执行
        
        Args:
            query: 用户查询
            thread_id: 线程ID（用于会话记忆）
            
        Returns:
            Agent 的回复
        """
        logger.info(f"[ReactAgent] 收到用户请求: {query}")
        
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
        
        # 检查是否处于人工模式
        current_state = self.app.get_state(config)
        if current_state and current_state.values.get("human_mode", False):
            logger.warning("[Human Mode] 当前处于人工模式，等待人工客服回复")
            return "系统提示：您的问题已转接人工客服，请耐心等待..."
        
        inputs = {
            "messages": [HumanMessage(content=query)],
            "is_report": False,
            "human_mode": False
        }
        
        try:
            result = self.app.invoke(inputs, config=config)
            
            # 提取最终回复
            final_message = result["messages"][-1]
            response = final_message.content if hasattr(final_message, "content") else str(final_message)
            
            logger.info(f"[ReactAgent] 任务完成，回复: {response[:100]}...")
            
            return response
        except GraphRecursionError:
            logger.error("[Graph Error] 触发最大递归限制")
            return "【系统提示】抱歉，我遇到了一些复杂的问题，思考过程陷入了循环。请您换一种方式提问，或要求转接人工客服。"
    
    def resume_human_mode(self, human_response: str, thread_id: str = "user_001"):
        """
        恢复人工模式
        
        Args:
            human_response: 人工客服的回复
            thread_id: 线程ID
        """
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
        current_state = self.app.get_state(config)
        
        if not current_state or not current_state.values.get("human_mode", False):
            logger.warning("[Human Mode] 当前不在人工模式，无法恢复")
            return
        
        current_state.values["human_mode"] = False
        current_state.values["messages"].append(("assistant", human_response))
        
        self.app.update_state(config, current_state.values)
        logger.info("[Human Mode] 人工模式已恢复为 AI 模式")


# ==========================================
# 测试代码
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("React Agent 测试（Handoff 架构）")
    print("=" * 60)
    
    try:
        agent = ReactAgent()
        
        test_cases = [
            "你好",
            "打开客厅的灯",
            "家里现在什么情况",
            "扫地机器人怎么使用"
        ]
        
        for test_input in test_cases:
            print(f"\n用户: {test_input}")
            response = agent.execute(test_input)
            print(f"Agent: {response}")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("提示：需要配置 API 密钥和启动 MCP Server")
