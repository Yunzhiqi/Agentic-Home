"""
智能家居系统核心工具集
包含知识库查询、报告生成、人工转接和设备控制移交功能
"""
import sys
import os
from langchain_core.tools import tool

# 确保能够正常导入项目内部模块
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from rag import rag_service


@tool(description='从向量数据库中检索参考资料')
def rag_summarize(quary: str, config: dict = None) -> str:
    """
    从 RAG 知识库中检索相关信息
    
    Args:
        quary: 查询问题
        config: 运行时配置，用于获取 pre-initialized 的 RAG 服务
        
    Returns:
        检索到的参考资料
    """
    # 尝试从 config 中获取预初始化的 rag_service，以提高性能
    rag = None
    if config and 'configurable' in config:
        rag = config['configurable'].get('rag_service')
    
    if not rag:
        from rag import rag_service
        rag = rag_service.RagSummarizeService()
        
    return rag.rag_summarize(quary)


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    """
    触发报告生成模式
    调用此工具后，系统会切换到报告生成的提示词模式
    """
    return


@tool(description="当用户遇到复杂设备故障、表达强烈不满，或主动要求转接人工客服时调用此工具。无入参。")
def transfer_to_human():
    """
    转接人工客服
    
    Returns:
        转接提示信息
    """
    # 这个返回值会记录到上下文中，实际上前端可以通过识别图的中断状态来给用户提示
    return "系统提示：已为您呼叫人工客服，请耐心等待。"


@tool(description="当用户的意图是控制家里的智能设备（如开灯、扫地、调空调等）或查询实时物理环境状态时，必须调用此工具。入参 instruction 包含你要交办给后台的明确具体的指令。")
def transfer_to_iot_controller(instruction: str):
    """
    移交智能家居控制中枢
    将设备控制任务从前台移交给后台 IoT 控制系统
    
    Args:
        instruction: 明确交给后台执行的指令。例如：“请打开客厅的灯”或“请查询卧室空调状态”
        
    Returns:
        移交提示信息
    """
    return f"系统提示：任务（{instruction}）已移交智能家居控制中枢。"
