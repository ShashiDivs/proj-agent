"""
Streamlit UI for the Reflection Chatbot.
Run: streamlit run reflection_chatbot/app.py
"""

import streamlit as st
import uuid
from chatbot import chat, get_thread_history

st.set_page_config(page_title="Reflection Chatbot", page_icon="🤖", layout="centered")

st.title("🤖 Reflection Chatbot")
st.caption("Powered by LangGraph · Each reply is drafted, critiqued, then revised before you see it.")

# --- Sidebar: thread management ---
with st.sidebar:
    st.header("Conversations")

    if "threads" not in st.session_state:
        st.session_state.threads = {}         # {thread_id: label}
    if "active_thread" not in st.session_state:
        st.session_state.active_thread = None

    if st.button("➕ New Conversation", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        label = f"Chat {len(st.session_state.threads) + 1}"
        st.session_state.threads[new_id] = label
        st.session_state.active_thread = new_id
        st.rerun()

    st.divider()

    for tid, label in st.session_state.threads.items():
        is_active = tid == st.session_state.active_thread
        btn_label = f"{'▶ ' if is_active else ''}{label}"
        if st.button(btn_label, key=f"thread_{tid}", use_container_width=True):
            st.session_state.active_thread = tid
            st.rerun()

    if st.session_state.threads:
        st.divider()
        st.caption(f"Active thread ID: `{st.session_state.active_thread}`")

# --- Main area ---
if st.session_state.active_thread is None:
    st.info("Click **➕ New Conversation** in the sidebar to start chatting.")
    st.stop()

thread_id = st.session_state.active_thread
label = st.session_state.threads[thread_id]

st.subheader(label)

# Render existing messages for this thread
history = get_thread_history(thread_id)
for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Type your message…"):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Drafting → reflecting → revising…"):
            reply = chat(prompt, thread_id)
        st.markdown(reply)

    # Auto-label the thread from the first message
    if st.session_state.threads[thread_id].startswith("Chat "):
        st.session_state.threads[thread_id] = prompt[:30] + ("…" if len(prompt) > 30 else "")

    st.rerun()
