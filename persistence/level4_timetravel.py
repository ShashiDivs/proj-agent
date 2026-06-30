"""
LEVEL 4 — Time travel: inspecting and rewinding to past checkpoints

No API key needed. Run: python3 level4_timetravel.py

LangGraph never overwrites a checkpoint — every step creates a new one.
get_state_history() lets you list them all and "rewind" by re-invoking
the graph with an OLD checkpoint_id, forking the conversation from there.
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State):
    n = len(state["messages"])
    return {"messages": [{"role": "assistant", "content": f"This is response #{n}"}]}


builder = StateGraph(State)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "time-travel-demo"}}

# Three turns, building up history
for user_text in ["step one", "step two", "step three"]:
    graph.invoke({"messages": [{"role": "user", "content": user_text}]}, config)

print("=== Full checkpoint history (newest first) ===")
history = list(graph.get_state_history(config))
for i, snap in enumerate(history):
    msg_count = len(snap.values["messages"])
    print(f"[{i}] checkpoint_id={snap.config['configurable']['checkpoint_id'][:8]}... "
          f"messages_so_far={msg_count}")

# Pick a checkpoint from BEFORE "step three" was sent (index 2 below is an example —
# print the list above to see exactly which index corresponds to which point)
rewind_to = history[3]  # adjust based on what you see printed above
print(f"\n=== Rewinding to an earlier checkpoint (messages_so_far={len(rewind_to.values['messages'])}) ===")

rewind_config = rewind_to.config
result = graph.invoke(
    {"messages": [{"role": "user", "content": "a NEW branch from the past"}]},
    rewind_config,
)
print("New branch reply:", result["messages"][-1].content)

print("\n=== History now shows a fork ===")
for i, snap in enumerate(graph.get_state_history(config)):
    msg_count = len(snap.values["messages"])
    last = snap.values["messages"][-1].content if snap.values["messages"] else None
    print(f"[{i}] messages_so_far={msg_count} last_message={last!r}")
