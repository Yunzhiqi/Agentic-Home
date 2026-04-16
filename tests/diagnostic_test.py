
import time
import asyncio
from agent.react_agent import ReactAgent
from utils.log import logger
import logging

# 屏蔽无关日志以看清性能数据
logging.getLogger("httpx").setLevel(logging.WARNING)

async def run_diagnostic():
    print("="*50)
    print("🚀 开始 Agent 性能与逻辑诊断测试")
    print("="*50)
    
    agent = ReactAgent()
    stable_thread_id = "test_session_001"
    
    # 测试 1: 基础响应延迟
    print("\n[测试 1] 基础交互延迟 (闲聊)")
    start = time.time()
    resp = agent.execute("你好", thread_id=stable_thread_id)
    end = time.time()
    print(f"响应内容: {resp}")
    print(f"⏱️ 耗时: {end - start:.2f}s")
    
    # 测试 2: 设备控制延迟 (涉及 Handoff 到后台)
    print("\n[测试 2] 设备控制延迟 (涉及多节点流转)")
    start = time.time()
    resp = agent.execute("打开客厅的灯", thread_id=stable_thread_id)
    end = time.time()
    print(f"响应内容: {resp}")
    print(f"⏱️ 耗时: {end - start:.2f}s")
    
    # 测试 3: 记忆功能测试 (在 stable_thread_id 下)
    print("\n[测试 3] 上下文记忆测试")
    print("请求: '把它调到最亮'")
    start = time.time()
    resp = agent.execute("把它调到最亮", thread_id=stable_thread_id)
    end = time.time()
    print(f"响应内容: {resp}")
    print(f"⏱️ 耗时: {end - start:.2f}s")
    if "客厅" in resp or "灯" in resp:
        print("✅ 记忆功能正常")
    else:
        print("❌ 记忆可能丢失 (无法关联上文的灯)")

    # 测试 4: 系统事件处理混淆测试
    print("\n[测试 4] 系统事件处理模拟")
    system_event = "【系统底层自动化事件，非人类对话】\n当前家居环境状态更新：'厨房检测到烟雾'\n要求：立即调用指令处理。"
    start = time.time()
    resp = agent.execute(system_event, thread_id="system_event_thread")
    end = time.time()
    print(f"系统事件响应: {resp}")
    print(f"⏱️ 耗时: {end - start:.2f}s")
    if "确认" in resp or "需要我" in resp:
        print("❌ 存在角色混淆 (Agent 仍以接待员口吻回复)")
    else:
        print("✅ 决策逻辑正确")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
