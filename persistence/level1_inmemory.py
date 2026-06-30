"""
LEVEL 1 — In-memory checkpointer (short-term, thread-scoped memory)

No API key needed. Run: python3 level1_inmemory.py
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State):
    last_user_msg = state["messages"][-1].content
    # toy "model": just echoes back what it remembers
    history = [m.content for m in state["messages"]]
    reply = f"You said: {last_user_msg!r}. Full history so far: {history}"
    return {"messages": [{"role": "assistant", "content": reply}]}


builder = StateGraph(State)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# --- Run two turns on the SAME thread_id ---
config = {"configurable": {"thread_id": "convo-1"}}

print("=== Turn 1 ===")
result = graph.invoke({"messages": [{"role": "user", "content": "My name is Alice"}]}, config)
print(result["messages"][-1].content)

print("\n=== Turn 2 (same thread) ===")
result = graph.invoke({"messages": [{"role": "user", "content": "What did I just tell you?"}]}, config)
print(result["messages"][-1].content)

# --- Now switch to a DIFFERENT thread_id ---
other_config = {"configurable": {"thread_id": "convo-2"}}
print("\n=== Turn 1 on a NEW thread (convo-2) ===")
result = graph.invoke({"messages": [{"role": "user", "content": "Who are you talking to?"}]}, other_config)
print(result["messages"][-1].content)
print("\n-> Notice convo-2 has no idea about 'Alice'. Threads are isolated.")

# --- Caveat: this all disappears once the process exits ---
print("\n(This was all in RAM — restart this script and convo-1's memory is gone.)")
