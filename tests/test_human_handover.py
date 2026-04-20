
import sys
import os
import asyncio
import time

# 确保能够正常导入项目内部模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.react_agent import ReactAgent
from utils.log import logger

async def test_human_handover():
    print("="*60)
    print("🚀 开始人工接管机制压力测试")
    print("="*60)
    
    agent = ReactAgent()
    test_thread_id = f"human_test_{int(time.time())}"
    
    # 1. 触发人工转接
    print("\n[步骤 1] 模拟触发人工转接...")
    query = "我对你们的服务非常不满意，我要找人工客服投诉！"
    print(f"用户: {query}")
    
    response = agent.execute(query, thread_id=test_thread_id)
    print(f"Agent 响应: {response}")
    
    # 检查状态是否变为人工模式
    config = {"configurable": {"thread_id": test_thread_id}}
    state = agent.app.get_state(config)
    is_human_mode = state.values.get("human_mode", False)
    print(f"当前是否处于人工模式: {'✅ 是' if is_human_mode else '❌ 否'}")
    
    # 2. 拦截测试：在人工模式下发送指令
    print("\n[步骤 2] 测试人工模式下的指令拦截...")
    query_2 = "帮我把灯打开"
    print(f"用户 (尝试在接管期间操作): {query_2}")
    
    response_2 = agent.execute(query_2, thread_id=test_thread_id)
    print(f"Agent 响应: {response_2}")
    
    if "人工客服" in response_2:
        print("✅ 拦截成功：AI 已停止处理，等待人工回复")
    else:
        print("❌ 拦截失败：AI 在人工模式下仍在执行指令")

    # 3. 恢复测试：模拟人工回复
    print("\n[步骤 3] 模拟人工介入并恢复 AI 模式...")
    human_reply = "您好，我是人工客服小王，我已经记录了您的投诉。现在我将系统切回 AI 模式为您继续服务。"
    print(f"人工回复: {human_reply}")
    
    agent.resume_human_mode(human_reply, thread_id=test_thread_id)
    
    # 检查状态是否已恢复
    state_after = agent.app.get_state(config)
    is_human_mode_after = state_after.values.get("human_mode", False)
    print(f"恢复后是否处于人工模式: {'❌ 否 (已恢复)' if not is_human_mode_after else '✅ 是 (仍未恢复)'}")
    
    # 4. 功能恢复测试
    print("\n[步骤 4] 测试 AI 功能是否完全恢复...")
    query_3 = "现在帮我打开客厅的灯"
    print(f"用户: {query_3}")
    
    response_3 = agent.execute(query_3, thread_id=test_thread_id)
    print(f"Agent 响应: {response_3}")
    
    if "客厅" in response_3 or "灯" in response_3:
        print("✅ 功能恢复：AI 能够继续处理指令")
    else:
        print("❌ 功能异常：AI 恢复后无法正常工作")

    print("\n" + "="*60)
    print("🎉 人工接管机制测试完成！")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_human_handover())
