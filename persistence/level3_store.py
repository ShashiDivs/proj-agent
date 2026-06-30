"""
LEVEL 3 — Long-term, cross-thread memory (the Store)

No API key needed. Run: python3 level3_store.py

Shows the key difference from checkpointers:
- Checkpointer memory is scoped to ONE thread_id (one conversation).
- Store memory is scoped to whatever YOU choose (e.g. a user_id),
  and is visible across many different thread_ids.
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State, config, *, store: BaseStore):
    user_id = config["configurable"]["user_id"]
    namespace = ("preferences", user_id)
    last_msg = state["messages"][-1].content

    # Naive "extraction": if the user says "I like X", remember it permanently.
    if "i like" in last_msg.lower():
        liked_thing = last_msg.lower().split("i like", 1)[1].strip()
        store.put(namespace, "favorite_thing", {"value": liked_thing})
        reply = f"Got it, I'll remember you like {liked_thing}."
    else:
        existing = store.get(namespace, "favorite_thing")
        if existing:
            reply = f"Btw, I recall you like {existing.value['value']}."
        else:
            reply = "I don't have any saved preferences for you yet."

    return {"messages": [{"role": "assistant", "content": reply}]}


builder = StateGraph(State)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

checkpointer = InMemorySaver()   # short-term, per-thread
store = InMemoryStore()          # long-term, per-user, cross-thread
graph = builder.compile(checkpointer=checkpointer, store=store)

user_id = "user-42"

# --- Conversation thread A: user shares a preference ---
config_a = {"configurable": {"thread_id": "thread-A", "user_id": user_id}}
print("=== Thread A ===")
result = graph.invoke({"messages": [{"role": "user", "content": "I like dark chocolate"}]}, config_a)
print(result["messages"][-1].content)

# --- Conversation thread B: completely different thread, SAME user ---
config_b = {"configurable": {"thread_id": "thread-B", "user_id": user_id}}
print("\n=== Thread B (brand new conversation, same user) ===")
result = graph.invoke({"messages": [{"role": "user", "content": "What's up?"}]}, config_b)
print(result["messages"][-1].content)
print("-> Thread B has NO checkpoint history with thread A, yet it still")
print("   knows the preference, because it came from the shared Store, not the checkpoint.")

# --- A different user gets nothing ---
config_c = {"configurable": {"thread_id": "thread-C", "user_id": "user-99"}}
print("\n=== Thread C (a different user entirely) ===")
result = graph.invoke({"messages": [{"role": "user", "content": "What's up?"}]}, config_c)
print(result["messages"][-1].content)
