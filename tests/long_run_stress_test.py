
import asyncio
import time
import json
import random
import os
import sys
import logging
from datetime import datetime

# 确保导入路径正确
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.react_agent import ReactAgent
from utils.config_hander import automation_config, debug_commands_config

# 配置日志记录
os.makedirs("logs", exist_ok=True)
journal_path = "logs/stress_test_journal.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(journal_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StressTest")

class AgenticHomeTester:
    def __init__(self):
        self.agent = ReactAgent()
        self.user_thread = f"test_user_{int(time.time())}"
        self.system_thread = f"test_system_{int(time.time())}"
        self.automation_rules = automation_config.get("rules", [])
        self.debug_cmds = debug_commands_config.get("commands", {})
        self.agent_lock = asyncio.Lock()
        self.op_counter = 0

    def record_trace(self, thread_id, error_msg):
        """错误溯源：保存当前线程的所有消息历史"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trace_file = f"logs/error_trace_{thread_id}_{timestamp}.json"
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.agent.app.get_state(config)
            history = []
            if state and state.values.get("messages"):
                for msg in state.values["messages"]:
                    history.append({
                        "type": type(msg).__name__,
                        "content": msg.content,
                        "tool_calls": getattr(msg, "tool_calls", None),
                        "tool_call_id": getattr(msg, "tool_call_id", None)
                    })
            
            trace_data = {
                "error": error_msg,
                "thread_id": thread_id,
                "timestamp": timestamp,
                "history": history
            }
            
            with open(trace_file, "w", encoding="utf-8") as f:
                json.dump(trace_data, f, ensure_ascii=False, indent=2)
            logger.error(f"🚩 错误溯源已完成，快照保存至: {trace_file}")
        except Exception as e:
            logger.error(f"溯源失败: {e}")

    async def run_task(self, msg_type, content, thread_id):
        """执行单个任务并处理异常"""
        self.op_counter += 1
        current_op = f"Op #{self.op_counter} [{msg_type}]"
        
        logger.info(f"🚀 开始执行: {current_op} - {content[:50]}...")
        
        async with self.agent_lock:
            try:
                # 针对系统事件进行 Prompt 增强（模拟 main_loop 逻辑）
                if msg_type == "SYSTEM":
                    prompt = (
                        f"【系统自动化指令 - 优先级：常规】\n环境发生变化：'{content}'\n"
                        f"要求：立即决策并执行，保持专业简练。"
                    )
                    # 模拟紧急事件概率
                    if "烟雾" in content or "泄漏" in content:
                        prompt = prompt.replace("常规", "紧急")
                    
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self.agent.execute(prompt, thread_id=thread_id)
                    )
                else:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self.agent.execute(content, thread_id=thread_id)
                    )
                
                logger.info(f"✅ 执行完成: {current_op}")
                logger.info(f"🤖 Agent响应: {response[:100].replace('\n', ' ')}...")
                return True
            
            except Exception as e:
                err_str = str(e)
                logger.error(f"❌ 执行失败: {current_op} - 错误类型: {type(e).__name__}")
                logger.error(f"错误详情: {err_str}")
                
                # 记录溯源快照
                self.record_trace(thread_id, err_str)
                
                # 自愈：模拟 /clear
                logger.warning(f"♻️ 正在执行自愈重置 (Thread ID 漂移)...")
                if thread_id == self.user_thread:
                    self.user_thread = f"test_user_recovered_{int(time.time())}"
                else:
                    self.system_thread = f"test_system_recovered_{int(time.time())}"
                return False

    async def start_test(self, duration_seconds=600):
        """启动长时间压力测试"""
        logger.info(f"🔥 压力测试启动，计划时长: {duration_seconds}s")
        start_time = time.time()
        
        user_inputs = [
            "打开客厅所有的灯",
            "卧室空调调到24度",
            "帮我看看家里现在情况怎么样",
            "扫地机器人去扫一下厨房",
            "我要睡觉了",
            "调亮客厅的灯",
            "关闭所有的电器",
            "扫地机器人现在电量多少"
        ]
        
        system_events = list(self.debug_cmds.values())

        while time.time() - start_time < duration_seconds:
            # 随机决定是用户输入还是系统事件
            is_user = random.random() > 0.4
            
            if is_user:
                task_content = random.choice(user_inputs)
                asyncio.create_task(self.run_task("USER", task_content, self.user_thread))
            else:
                task_content = random.choice(system_events)
                asyncio.create_task(self.run_task("SYSTEM", task_content, self.system_thread))
            
            # 模拟随机输入间隔 (1-5秒)
            await asyncio.sleep(random.uniform(1, 5))

        logger.info("🏁 测试时长已到，正在等待残余任务完成...")
        async with self.agent_lock:
            logger.info("🌟 所有任务处理完毕，测试结束。")

if __name__ == "__main__":
    tester = AgenticHomeTester()
    try:
        asyncio.run(tester.start_test(duration_seconds=1800)) # 默认运行30分钟
    except KeyboardInterrupt:
        logger.info("测试被用户手动中断")
