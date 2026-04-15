import time
import streamlit as st
import uuid
from agent.react_agent import ReactAgent

# 页面配置
st.set_page_config(
    page_title="扫地机器人智能客服",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .stChatMessage {
        padding: 16px;
        border-radius: 10px;
        margin-bottom: 8px;
    }
    .user-message {
        background-color: #f0f7ff;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
    .stSpinner > div {
        text-align: center;
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .online {
        background-color: #4CAF50;
    }
    .offline {
        background-color: #f44336;
    }
</style>
""", unsafe_allow_html=True)

# 初始化会话状态
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()
    st.session_state["agent_status"] = "在线"

# 初始化后端的会话 ID
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = "user_001"

# 从数据库同步最新的历史记录（包含人工客服的回复）
config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
current_state = st.session_state["agent"].app.get_state(config)

is_human_mode = False
if current_state and current_state.values.get("messages"):
    is_human_mode = current_state.values.get("human_mode", False)
    
    # 动态更新侧边栏的状态显示
    st.session_state["agent_status"] = "人工接管中" if is_human_mode else "在线"
    
    st.session_state["message"] = []
    for msg in current_state.values["messages"]:
        # 只提取有内容的消息用于页面展示
        if msg.content:
            if msg.type in ["human", "user"]:
                st.session_state["message"].append({"role": "user", "content": msg.content})
            elif msg.type in ["ai", "assistant"]:
                st.session_state["message"].append({"role": "assistant", "content": msg.content})

# 如果处于人工接管模式，启用后台自动轮询（每 3 秒刷新一次页面）
if is_human_mode:
    try:
        from streamlit_autorefresh import st_autorefresh
        # interval=3000 代表 3000 毫秒 (3秒)
        st_autorefresh(interval=3000, limit=None, key="human_mode_refresh")
    except ImportError:
        st.error("请在终端运行 `pip install streamlit-autorefresh` 安装自动刷新组件。")

if "message" not in st.session_state:
    st.session_state["message"] = [
        {"role": "assistant", "content": "您好！我是扫地机器人智能客服，我可以帮您解决扫地机器人的各种问题，包括故障诊断、使用指导、功能设置等。有什么可以帮您的吗？"}
    ]

if "chat_started" not in st.session_state:
    st.session_state["chat_started"] = False

# 侧边栏
with st.sidebar:
    st.title("🤖 扫地机器人客服")
    
    # 状态指示器
    col1, col2 = st.columns([1, 4])
    with col1:
        status_class = "online" if st.session_state["agent_status"] == "在线" else "offline"
        st.markdown(f'<div class="status-indicator {status_class}"></div>', unsafe_allow_html=True)
    with col2:
        st.write(f"**状态**: {st.session_state['agent_status']}")
        
    st.caption(f"当前会话ID: `{st.session_state['thread_id']}`")
    
    st.divider()
    
    # 对话统计
    st.subheader("📊 对话统计")
    user_messages = len([m for m in st.session_state["message"] if m["role"] == "user"])
    assistant_messages = len([m for m in st.session_state["message"] if m["role"] == "assistant"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("用户消息", user_messages)
    with col2:
        st.metric("客服回复", assistant_messages)
    
    st.divider()
    
    # 快速问题示例
    st.subheader("💡 常见问题示例")
    example_questions = [
        "扫地机器人不工作了怎么办？",
        "如何设置定时清扫？",
        "扫地机器人无法返回充电座",
        "如何更换扫地机器人的滚刷？",
        "扫地机器人工作时噪音大怎么办？"
    ]
    
    for question in example_questions:
        if st.button(question, key=f"example_{question}", use_container_width=True):
            st.session_state["example_question"] = question
            st.rerun()
    
    st.divider()
    
    # 清空对话按钮
    if st.button("🗑️ 清空对话记录", type="secondary", use_container_width=True):
        # 核心修复：生成新的 thread_id，从底层数据库层面彻底开辟新对话
        st.session_state["thread_id"] = f"user_{str(uuid.uuid4())[:8]}"
        st.session_state["message"] = [
            {"role": "assistant", "content": "对话已清空。您好！我是扫地机器人智能客服，有什么可以帮您的吗？"}
        ]
        st.rerun()
    
    # 客服能力说明
    with st.expander("🔧 客服能力说明", expanded=False):
        st.markdown("""
        **我可以帮您解决以下问题：**
        - 🔍 故障诊断与排除
        - 📅 使用与操作指导
        - ⚙️ 功能设置与调整
        - 🧹 维护与清洁建议
        - 🔋 电池与充电问题
        - 🗺️ 导航与地图问题
        """)

# 主界面
st.title("🧹 扫地机器人智能客服")

# 状态栏
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.caption(f"对话消息数: {len(st.session_state['message'])}")
with col2:
    st.caption(f"最后活跃: {time.strftime('%H:%M')}")
with col3:
    if st.button("🔄 刷新状态"):
        st.rerun()

st.divider()

# 检查是否有示例问题需要处理
if "example_question" in st.session_state:
    prompt = st.session_state["example_question"]
    del st.session_state["example_question"]
else:
    prompt = st.chat_input("请输入您的问题...")

# 显示对话历史
for i, message in enumerate(st.session_state["message"]):
    with st.chat_message(message["role"]):
        # 添加消息索引
        if message["role"] == "user":
            st.markdown(f"**用户**: {message['content']}")
        else:
            # 美化AI回复的显示
            content = message['content']
            
            # 检测是否有步骤或列表格式
            if any(marker in content for marker in ["步骤", "建议", "原因"]):
                lines = content.split('\n')
                for line in lines:
                    if any(marker in line for marker in ["1.", "2.", "3.", "4.", "5.", "- ", "* "]):
                        st.markdown(line)
                    else:
                        st.write(line)
            else:
                st.write(content)
        
        # 在用户消息后添加分隔线（不是最后一个消息时）
        if i < len(st.session_state["message"]) - 1:
            st.divider()

# 处理用户输入
if prompt:
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(f"**用户**: {prompt}")
    st.session_state["message"].append({"role": "user", "content": prompt})
    
    # 设置标志表示聊天已开始
    if not st.session_state["chat_started"]:
        st.session_state["chat_started"] = True
    
    # 创建容器用于流式输出
    response_container = st.empty()
    
    # 显示思考状态
    with st.status("🤔 正在分析您的问题...", expanded=False) as status:
        # 第一步：理解问题
        st.write("🔍 理解您的问题...")
        time.sleep(0.5)
        
        # 第二步：调用工具函数
        st.write("🛠️ 调用相关工具...")
        time.sleep(0.3)
        
        # 收集响应
        response_messages = []
        
        # 执行流式响应
        with response_container.container():
            with st.chat_message("assistant"):
                # 创建消息占位符
                message_placeholder = st.empty()
                
                # 收集完整的响应
                full_response = ""
                
                # 捕获生成器输出
                res_stream = st.session_state["agent"].execute_stream(prompt, thread_id=st.session_state["thread_id"])
                
                # 自定义capture函数，支持更流畅的输出
                def stream_generator(generator, cache_list):
                    for chunk in generator:
                        cache_list.append(chunk)
                        full_chunk = ''.join(cache_list)
                        
                        # 更新显示，模拟打字机效果
                        for i in range(len(chunk)):
                            yield chunk[i]
                            time.sleep(0.01)
                
                # 使用write_stream显示流式输出
                stream_content = stream_generator(res_stream, response_messages)
                
                # 显示流式输出
                message_placeholder.write_stream(stream_content)
                
                # 获取最终响应
                if response_messages:
                    full_response = ''.join(response_messages)
        
        # 第三步：完成响应
        st.write("✅ 生成最终回答...")
        time.sleep(0.2)
        status.update(label="✅ 回答完成", state="complete", expanded=False)
    
    # 将完整响应添加到消息历史
    if full_response:
        st.session_state["message"].append({"role": "assistant", "content": full_response})
    
    # 添加反馈选项
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("👍 有帮助", use_container_width=True):
            st.success("感谢您的反馈！")
    with col2:
        if st.button("👎 没帮助", use_container_width=True):
            st.info("抱歉没能帮到您，我将继续改进。")
    with col3:
        st.caption("您的反馈有助于我们改进服务质量")

# 如果没有消息，显示欢迎信息
if len(st.session_state["message"]) == 1:
    st.info("💡 **提示**: 您可以点击左侧的常见问题示例快速提问，或直接在下方输入您的问题。")

# 页脚
st.divider()
st.caption("""
🔧 **技术支持**: 扫地机器人智能客服系统 v2.0 | 使用先进的Agent技术提供专业解答
""")
