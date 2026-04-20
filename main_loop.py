"""
智能家居事件驱动主循环
支持用户输入和传感器事件的双向触发
使用 rich 库美化输出，区分用户对话和系统主动事件
"""
import asyncio
import sys
import os
import random
import time
from datetime import datetime
from typing import Dict, Any
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
from utils.config_hander import automation_config, debug_commands_config

# 初始化 Rich Console
console = Console()

# 载入规则和指令映射
automation_rules = automation_config.get("rules", [])
debug_commands = debug_commands_config.get("commands", {})

logger.info(f"[MainLoop] 成功载入 {len(automation_rules)} 条自动化规则和 {len(debug_commands)} 条调试指令")

# 优先级定义
PRIORITY_HIGH = 0
PRIORITY_NORMAL = 1

# 事件队列：使用优先队列，存储格式为 (priority, timestamp, message_dict)
event_queue = asyncio.PriorityQueue()

# 稳定的 thread_id 以保留会话记忆 (设为全局以便 /clear 修改)
user_thread_id = "user_chat_001"
system_thread_id = "system_auto_001"

# 任务执行锁：确保 Agent 同一时间只处理一个逻辑链条
agent_lock = asyncio.Lock()
# 紧急任务标记
is_priority_processing = False


# ==========================================
# 辅助函数：将事件放入队列
# ==========================================
async def emit_event(content: str, event_type: str = "user", metadata: Dict[str, Any] = None):
    """
    统一的事件发送函数
    """
    if metadata is None:
        metadata = {}
    
    priority = PRIORITY_NORMAL
    
    # 根据元数据确定优先级
    if event_type == "sensor":
        # 匹配自动化规则确定优先级
        for rule in automation_rules:
            if rule["event_keyword"] in content:
                if rule.get("priority") == "high":
                    priority = PRIORITY_HIGH
                metadata["action_hint"] = rule.get("action_hint", "")
                metadata["rule_priority"] = rule.get("priority", "normal")
                break
    elif metadata.get("priority") == "high":
        priority = PRIORITY_HIGH

    event_data = {
        "content": content,
        "type": event_type,
        "metadata": metadata,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    
    # 放入优先队列：(优先级, 时间戳, 数据)
    # 使用 time.time() 确保相同优先级下按时间顺序
    await event_queue.put((priority, time.time(), event_data))
    logger.debug(f"[Queue] 已放入事件: {content} (优先级: {priority})")


# ==========================================
# 传感器模拟器
# ==========================================
async def sensor_simulator_loop():
    """
    传感器模拟器：每隔 20 秒随机生成一个环境事件
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
        await asyncio.sleep(20)  # 每 20 秒触发一次
        
        # 随机选择一个事件
        room, event_desc = random.choice(sensor_events)
        
        content = f"{room}: {event_desc}"
        await emit_event(content, event_type="sensor", metadata={"room": room})
        
        logger.info(f"[Sensor Simulator] 生成事件: {content}")


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
            await emit_event(user_input.strip(), event_type="user")


# ==========================================
# 调试输入监听器 (支持 / 命令)
# ==========================================
async def debug_input_loop():
    """
    调试输入监听器：支持通过 / 命令模拟系统事件
    """
    loop = asyncio.get_event_loop()
    
    # 引用外部变量以便修改 thread_id 实现 /clear
    global user_thread_id, system_thread_id
    
    while True:
        # 在异步环境中快速读取用户输入
        user_input = await loop.run_in_executor(None, input, "Debug Mode > ")
        
        cmd = user_input.strip()
        if not cmd:
            continue
            
        if cmd.lower() in ["exit", "quit", "退出"]:
            console.print("[bold red]系统退出[/bold red]")
            os._exit(0)
            
        if cmd == "/clear":
            # 通过更换 thread_id 变相清除历史记录
            new_suffix = int(time.time())
            user_thread_id = f"user_chat_{new_suffix}"
            system_thread_id = f"system_auto_{new_suffix}"
            console.print(f"[bold green]✓ 对话历史已重置 (新 Thread ID: {new_suffix})[/bold green]")
            continue

        if cmd in ["/?", "/help"]:
            # 本地处理帮助信息，不发给大模型
            console.print(Panel(
                Text("\n".join([f"{k}: {v}" for k, v in debug_commands.items()]) + "\n/clear: 重置对话历史记录", style="cyan"),
                title="调试模式指令帮助",
                border_style="cyan"
            ))
            continue
            
        if cmd.startswith("/"):
            # 尝试匹配快捷命令
            event_desc = debug_commands.get(cmd)
            if event_desc:
                console.print(f"[dim]快捷指令匹配成功: {cmd} -> {event_desc}[/dim]")
                await emit_event(event_desc, event_type="sensor")
            else:
                console.print(f"[bold red]错误：未找到快捷指令 {cmd}[/bold red]")
        else:
            # 普通输入视为用户请求
            await emit_event(cmd, event_type="user")


# ==========================================
# 主事件循环
# ==========================================
async def agentic_main_loop(mode="full"):
    """
    主事件循环：同时监听用户输入和传感器事件
    """
    is_debug = mode == "debug"

    console.print(Panel.fit(
        f"[bold cyan]智能家居事件驱动系统 ({'调试模式' if is_debug else '完整模式'})[/bold cyan]\n"
        "支持用户对话和传感器事件的双向触发\n"
        "[green]用户输入[/green] | [red]系统事件[/red] | [yellow]自动化联动[/yellow]",
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

    # 根据模式启动不同的输入监听器
    if is_debug:
        console.print("[bold magenta]调试模式已启动：传感器模拟器已禁用，请通过 / 指令手动模拟事件[/bold magenta]")
        asyncio.create_task(debug_input_loop())
    else:
        # 启动传感器模拟器
        asyncio.create_task(sensor_simulator_loop())
        # 启动标准用户输入监听器
        asyncio.create_task(user_input_loop())

    console.print("[dim]输入您的指令，或使用 /command 模拟事件...[/dim]")
    console.print("[dim]输入 'exit' 或 'quit' 退出系统[/dim]\n")

    # 定义异步处理函数，内部通过 agent_lock 实现串行化
    async def process_message(priority, _, event_data):
        global is_priority_processing
        
        content = event_data["content"]
        event_type = event_data["type"]
        metadata = event_data["metadata"]
        timestamp = event_data["timestamp"]
        
        is_high_priority = priority == PRIORITY_HIGH

        # 竞争执行锁 (确保串行执行)
        async with agent_lock:
            if is_high_priority:
                is_priority_processing = True
                
            if event_type == "user":
                console.print(Panel(
                    Text(content, style="bold green"),
                    title=f"User [{timestamp}]",
                    border_style="green"
                ))
                try:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(None, lambda: agent.execute(content, thread_id=user_thread_id, name="user"))
                    console.print(Panel(
                        Text(response, style="white"),
                        title=f"Agent [{datetime.now().strftime('%H:%M:%S')}]",
                        border_style="blue"
                    ))
                except Exception as e:
                    console.print(f"[bold red]处理失败: {e}[/bold red]")
            
            elif event_type == "sensor":
                matched_action = metadata.get("action_hint", "")
                rule_priority = metadata.get("rule_priority", "normal")
                
                current_event_is_high = rule_priority == "high"
                display_style = "bold red" if current_event_is_high else "bold yellow"
                title_prefix = "🚨 系统紧急事件" if current_event_is_high else "📡 系统环境事件"
                
                console.print(Panel(
                    Text(f"{content}\n" + (f"[dim]匹配规则: {matched_action}[/dim]" if matched_action else ""), style=display_style),
                    title=f"{title_prefix} [{timestamp}]",
                    border_style="red" if current_event_is_high else "yellow"
                ))
                
                try:
                    prompt_prefix = "【系统自动化指令 - 优先级：紧急】" if current_event_is_high else "【系统自动化指令 - 优先级：常规】"
                    action_suggestion = f"\n[建议操作建议]: {matched_action}" if matched_action else ""
                    
                    prompt = (
                        f"{prompt_prefix}\n"
                        f"环境发生变化：'{content}'"
                        f"{action_suggestion}\n"
                        f"你的任务：\n"
                        f"1. 立即判断是否需要操作设备。\n"
                        f"2. 直接调用 transfer_to_iot_controller 移交执行，不要询问用户。\n"
                        f"3. 保持专业简练。"
                    )
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(None, lambda: agent.execute(prompt, thread_id=system_thread_id, name="system_monitor"))
                    console.print(Panel(
                        Text(response, style="yellow"),
                        title=f"Agent (Auto) [{datetime.now().strftime('%H:%M:%S')}]",
                        border_style="yellow"
                    ))
                except Exception as e:
                    console.print(f"[bold red]处理失败: {e}[/bold red]")
            
            # 任务结束，释放紧急标记
            if is_high_priority:
                is_priority_processing = False
        
        console.print()

    # 主循环：从队列获取消息并启动协程
    while True:
        # 获取优先级、内部时间戳和数据
        priority, ts, event_data = await event_queue.get()
        # 仍然使用 create_task，但内部受 agent_lock 约束实现串行执行
        asyncio.create_task(process_message(priority, ts, event_data))
        
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
        choices=["full", "simple", "demo", "debug"],
        default="demo",
        help="运行模式：full=完整模式，simple=仅用户，demo=演示模式，debug=调试模式"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode in ["full", "debug"]:
            asyncio.run(agentic_main_loop(mode=args.mode))
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
