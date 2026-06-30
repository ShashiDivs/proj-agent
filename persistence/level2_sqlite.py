"""
LEVEL 2 — Durable checkpointer (SQLite) — survives process restarts

No API key needed.
Run it TWICE in a row to see persistence across runs:
    python3 level2_sqlite.py
    python3 level2_sqlite.py
The second run will remember what the first run said, because state
is now saved to a file (checkpoints.db) instead of RAM.
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State):
    history = [m.content for m in state["messages"]]
    reply = f"I now remember {len(history)} message(s) total: {history}"
    return {"messages": [{"role": "assistant", "content": reply}]}


builder = StateGraph(State)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

# `with` opens/creates checkpoints.db on disk
with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "durable-convo"}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "ping"}]}, config
    )
    print(result["messages"][-1].content)

print("\nState saved to ./checkpoints.db on disk.")
print("Run this script again — the message count will keep growing,")
print("even though this is a brand-new Python process.")
