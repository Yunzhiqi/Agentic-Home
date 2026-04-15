import streamlit as st
from agent.react_agent import ReactAgent

st.set_page_config(page_title="人工客服后台系统", page_icon="👨‍💻", layout="wide")
st.title("👨‍💻 人工客服工单处理后台")
st.divider()

# 初始化 Agent（会连接到同一个 SQLite 数据库）
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

# 允许人工输入需要接管的 Thread ID (可以从用户端侧边栏复制)
THREAD_ID = st.text_input("请输入要监控的用户对话 ID (Thread ID):", value="user_001")
config = {"configurable": {"thread_id": THREAD_ID}}

# 1. 获取该用户当前的图状态
current_state = st.session_state["agent"].app.get_state(config)

# 判断是否存在对话记录
if not current_state.values.get("messages"):
    st.info("当前暂无用户排队请求。")
    st.stop()

# 2. 渲染历史聊天记录
st.subheader("📝 用户历史聊天记录")
with st.container(height=400):
    for msg in current_state.values["messages"]:
        role = "用户" if msg.type == "human" else ("系统/工具" if msg.type == "tool" else "AI 客服")
        if msg.content:
            st.markdown(f"**{role}:** {msg.content}")

st.divider()

# 3. 核心逻辑：判断图是否被挂起在 'human' 节点前
# current_state.next 会返回一个元组，列出图下一步即将进入的节点。如果包含 'human'，说明被打断了。
is_waiting_for_human = "human" in current_state.next

if is_waiting_for_human:
    st.error("🚨 警告：该图已被挂起！用户正在请求人工接管。")
    
    # 提供人工回复输入框
    human_reply = st.text_area("请输入您的人工回复：")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 发送回复 (保持人工模式)", type="primary", use_container_width=True):
            if human_reply:
                st.session_state["agent"].app.update_state(
                    config,
                    {"messages": [("assistant", f"【人工客服】{human_reply}")], "human_mode": True},
                    as_node="human"
                )
                for _ in st.session_state["agent"].app.stream(None, config):
                    pass
                st.success("消息已发送给用户！")
                st.rerun()
            else:
                st.warning("回复内容不能为空！")
                
    with col2:
        if st.button("🤖 结束对话并交还 AI 控制权", type="secondary", use_container_width=True):
            msg = human_reply if human_reply else "人工服务已结束，即将为您转回智能客服。"
            st.session_state["agent"].app.update_state(
                config,
                {"messages": [("assistant", f"【人工客服】{msg}")], "human_mode": False},
                as_node="human"
            )
            for _ in st.session_state["agent"].app.stream(None, config):
                pass
            st.success("控制权已交还给大模型！")
            st.rerun()
else:
    st.success("✅ 当前 AI 客服正在正常处理，无需人工介入。")
    if st.button("刷新状态"):
        st.rerun()