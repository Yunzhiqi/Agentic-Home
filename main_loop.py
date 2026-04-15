"""
智能家居事件驱动主循环
支持用户输入和传感器事件的双向触发
使用 rich 库美化输出，区分用户对话和系统主动事件
"""
import asyncio
import sys
import os
import random
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# 确保能够正常导入项目内部模块
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.react_agent import ReactAgent
from state_models import get_home_state
from utils.log import logger

# 初始化 Rich Console
console = Console()

# 事件队列：用于存储传感器事件
event_queue = asyncio.Queue()


# ==========================================
# 传感器模拟器
# ==========================================
async def sensor_simulator_loop():
    """
    传感器模拟器：每隔 10 秒随机生成一个环境事件
    """
    # 预定义的传感器事件
    sensor_events = [
        ("客厅", "检测到有人进入"),
        ("客厅", "温度达到 30 度"),
        ("卧室", "检测到用户离开"),
        ("卧室", "温度过低，当前 18 度"),
        ("厨房", "检测到烟雾"),
        ("客厅", "扫地机器人报告主刷被缠绕"),
        ("客厅", "检测到光线变暗"),
        ("卧室", "检测到有人进入"),
        ("客厅", "空调已运行 2 小时"),
        ("厨房", "检测到燃气泄漏"),
    ]
    
    while True:
        await asyncio.sleep(60)  # 每 10 秒触发一次
        
        # 随机选择一个事件
        room, event_desc = random.choice(sensor_events)
        
        # 将事件放入队列
        event_message = f"[传感器事件] {room}: {event_desc}"
        await event_queue.put(event_message)
        
        logger.info(f"[Sensor Simulator] 生成事件: {event_message}")


# ==========================================
# 用户输入监听器
# ==========================================
async def user_input_loop():
    """
    用户输入监听器：监听终端输入
    """
    loop = asyncio.get_event_loop()
    
    while True:
        # 在异步环境中读取用户输入
        user_input = await loop.run_in_executor(None, input, "")
        
        if user_input.strip():
            if user_input.strip().lower() in ["exit", "quit", "退出"]:
                console.print("[bold red]系统退出[/bold red]")
                os._exit(0)
            
            # 将用户输入放入队列
            await event_queue.put(f"[用户请求] {user_input.strip()}")


# ==========================================
# 主事件循环
# ==========================================
async def agentic_main_loop():
    """
    主事件循环：同时监听用户输入和传感器事件
    """
    console.print(Panel.fit(
        "[bold cyan]智能家居事件驱动系统[/bold cyan]\n"
        "支持用户对话和传感器事件的双向触发\n"
        "[green]用户输入[/green] | [red]系统事件[/red]",
        title="Agentic Home",
        border_style="cyan"
    ))
    
    # 初始化智能家居 Agent
    console.print("[yellow]正在初始化智能家居系统...[/yellow]")
    try:
        agent = ReactAgent()
        console.print("[bold green]✓ 系统初始化完成[/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]✗ 系统初始化失败: {e}[/bold red]")
        console.print("[yellow]提示：请确保已配置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 环境变量[/yellow]")
        
        return
    
    # 启动传感器模拟器
    asyncio.create_task(sensor_simulator_loop())
    
    # 启动用户输入监听器
    asyncio.create_task(user_input_loop())
    
    console.print("[dim]输入您的指令，或等待传感器事件触发...[/dim]")
    console.print("[dim]输入 'exit' 或 'quit' 退出系统[/dim]\n")
    
    # 主循环：处理队列中的事件
    while True:
        # 从队列中获取事件（阻塞等待）
        message = await event_queue.get()
        
        # 解析事件类型
        if message.startswith("[用户请求]"):
            # 用户输入事件
            user_input = message.replace("[用户请求]", "").strip()
            
            # 使用绿色显示用户输入
            console.print(Panel(
                Text(user_input, style="bold green"),
                title=f"User [{datetime.now().strftime('%H:%M:%S')}]",
                border_style="green"
            ))
            
            try:
                # 调用 Agent 处理用户请求（使用线程池避免阻塞）
                loop = asyncio.get_event_loop()
                # 为用户请求使用唯一的 thread_id，避免状态污染
                import time
                user_thread_id = f"user_{int(time.time())}"
                response = await loop.run_in_executor(None, lambda: agent.execute(user_input, thread_id=user_thread_id))
                
                # 显示 Agent 回复
                console.print(Panel(
                    Text(response, style="white"),
                    title=f"Agent [{datetime.now().strftime('%H:%M:%S')}]",
                    border_style="blue"
                ))
            except Exception as e:
                console.print(f"[bold red]处理失败: {e}[/bold red]")
        
        elif message.startswith("[传感器事件]"):
            # 传感器事件
            event_content = message.replace("[传感器事件]", "").strip()
            
            # 使用红色显示系统事件
            console.print(Panel(
                Text(event_content, style="bold red"),
                title=f"System Event [{datetime.now().strftime('%H:%M:%S')}]",
                border_style="red"
            ))
            
            try:
                # 调用 Agent 处理传感器事件
                # 将传感器事件转换为自然语言请求
                prompt = (
                    f"【系统底层自动化事件，非人类对话】\n"
                    f"当前家居环境状态更新：'{event_content}'\n"
                    f"指令要求：\n"
                    f"1. 你必须直接自主决策。绝对不要向系统或用户反问“需要我做什么”。\n"
                    f"2. 如果该事件需要设备响应（如有人进入需开灯/调空调，或设备故障如缠绕需紧急停机），请必须立即调用 transfer_to_iot_controller 工具下达控制指令。\n"
                    f"3. 绝对不要调用 rag_summarize 查阅说明书，除非人类用户明确提问。\n"
                    f"4. 决策完成后，用一句话简要汇报你的处理结果。"
                )
                loop = asyncio.get_event_loop()
                # 为传感器事件使用唯一的 thread_id，避免状态污染
                import time
                sensor_thread_id = f"sensor_{int(time.time())}"
                response = await loop.run_in_executor(None, lambda: agent.execute(prompt, thread_id=sensor_thread_id))
                
                # 显示 Agent 的主动响应
                console.print(Panel(
                    Text(response, style="yellow"),
                    title=f"Agent (Auto) [{datetime.now().strftime('%H:%M:%S')}]",
                    border_style="yellow"
                ))
            except Exception as e:
                console.print(f"[bold red]处理失败: {e}[/bold red]")
        
        console.print()  # 空行分隔


# ==========================================
# 简化版主循环（仅用户输入，不含传感器模拟）
# ==========================================
async def simple_main_loop():
    """
    简化版主循环：仅支持用户输入，不启动传感器模拟器
    适合测试和演示
    """
    console.print(Panel.fit(
        "[bold cyan]智能家居交互系统（简化版）[/bold cyan]\n"
        "仅支持用户对话模式",
        title="Agentic Home",
        border_style="cyan"
    ))
    
    # 初始化智能家居 Agent
    console.print("[yellow]正在初始化智能家居系统...[/yellow]")
    # try:
    #     agent = ReactAgent()
    #     console.print("[bold green]✓ 系统初始化完成[/bold green]\n")
    # except Exception as e:
    #     console.print(f"[bold red]✗ 系统初始化失败: {e}[/bold red]")
    #     console.print("[yellow]提示：请确保已配置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 环境变量[/yellow]")
    #     return
    agent = ReactAgent()
    
    console.print("[dim]输入您的指令开始对话...[/dim]")
    console.print("[dim]输入 'exit' 或 'quit' 退出系统[/dim]\n")
    
    loop = asyncio.get_event_loop()
    
    while True:
        # 读取用户输入
        user_input = await loop.run_in_executor(None, input, "You: ")
        
        if user_input.strip().lower() in ["exit", "quit", "退出"]:
            console.print("[bold red]系统退出[/bold red]")
            break
        
        if not user_input.strip():
            continue
        
        try:
            # 调用 Agent 处理用户请求（使用线程池避免阻塞）
            console.print("[dim]处理中...[/dim]")
            loop = asyncio.get_event_loop()
            # 为用户请求使用唯一的 thread_id，避免状态污染
            import time
            user_thread_id = f"user_{int(time.time())}"
            response = await loop.run_in_executor(None, lambda: agent.execute(user_input.strip(), thread_id=user_thread_id))
            
            # 显示 Agent 回复
            console.print(Panel(
                Text(response, style="white"),
                title=f"Agent [{datetime.now().strftime('%H:%M:%S')}]",
                border_style="blue"
            ))
            console.print()
        except Exception as e:
            console.print(f"[bold red]处理失败: {e}[/bold red]\n")


# ==========================================
# 演示模式（不需要 LLM，仅展示事件流转）
# ==========================================
async def demo_mode():
    """
    演示模式：不调用 LLM，仅展示事件流转和状态变化
    """
    console.print(Panel.fit(
        "[bold cyan]智能家居演示模式[/bold cyan]\n"
        "展示事件流转和状态变化（无需 LLM）",
        title="Agentic Home Demo",
        border_style="cyan"
    ))
    
    from state_models import get_home_state
    from mcp_services.home_device_mcp_server import (
        control_device, get_home_status, 
        report_sensor_data, query_device_by_room
    )
    
    console.print("\n[bold green]1. 查看初始家居状态[/bold green]")
    home = get_home_state()
    console.print(f"系统模式: {home.system_mode}")
    console.print(f"房间数量: {len(home.rooms)}")
    
    console.print("\n[bold green]2. 模拟用户指令：打开客厅灯光[/bold green]")
    result = control_device("living_light_001", "on")
    console.print(f"执行结果: {result}")
    
    console.print("\n[bold green]3. 模拟传感器事件：检测到客厅温度过高[/bold green]")
    result = report_sensor_data("客厅", "温度达到 30 度")
    console.print(f"事件记录: {result}")
    
    console.print("\n[bold green]4. 模拟自动响应：打开客厅空调[/bold green]")
    result = control_device("living_ac_001", "on")
    console.print(f"执行结果: {result}")
    result = control_device("living_ac_001", "temp:24")
    console.print(f"温度调节: {result}")
    
    console.print("\n[bold green]5. 查看更新后的家居状态[/bold green]")
    import json
    status = json.loads(get_home_status())
    console.print(f"系统模式: {status['system_mode']}")
    console.print(f"最近事件:")
    for event in status['active_events'][-5:]:
        console.print(f"  - {event}")
    
    console.print("\n[bold green]6. 查询客厅设备状态[/bold green]")
    room_status = json.loads(query_device_by_room("客厅"))
    console.print(f"客厅温度: {room_status['temperature']}°C")
    console.print(f"客厅设备数量: {len(room_status['devices'])}")
    for device in room_status['devices']:
        console.print(f"  - {device['device_id']}: {device['status']} (功率: {device['power_level']}%)")
    
    console.print("\n[bold cyan]演示完成！[/bold cyan]")


# ==========================================
# 主入口
# ==========================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能家居事件驱动系统")
    parser.add_argument(
        "--mode",
        choices=["full", "simple", "demo"],
        default="demo",
        help="运行模式：full=完整模式（用户+传感器），simple=简化模式（仅用户），demo=演示模式（无需LLM）"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "full":
            asyncio.run(agentic_main_loop())
        elif args.mode == "simple":
            asyncio.run(simple_main_loop())
        elif args.mode == "demo":
            asyncio.run(demo_mode())
    except KeyboardInterrupt:
        console.print("\n[bold red]系统被用户中断[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]系统错误: {e}[/bold red]")
        import traceback
        traceback.print_exc()
