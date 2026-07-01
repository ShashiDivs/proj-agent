"""
Reflection Chatbot — generate a draft reply, critique it, then send the revised answer.
Uses InMemorySaver checkpointer so each thread_id keeps its own conversation history.
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import os
from dotenv import load_dotenv

load_dotenv(override=True)

llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))


class State(TypedDict):
    messages: Annotated[list, add_messages]
    draft: str
    critique: str


def generate(state: State) -> dict:
    """Generate a first-draft reply to the latest user message."""
    history = state["messages"]
    response = llm.invoke([
        SystemMessage(content="You are a helpful, thoughtful assistant. Write a clear, concise reply."),
        *history,
    ])
    return {"draft": response.content}


def reflect(state: State) -> dict:
    """Critique the draft for clarity, completeness, and accuracy."""
    response = llm.invoke([
        SystemMessage(content=(
            "You are a strict editor. Critique the assistant's draft reply in 1-2 sentences. "
            "Focus only on what's missing, unclear, or could be improved. Be specific."
        )),
        HumanMessage(content=f"Draft reply:\n{state['draft']}"),
    ])
    return {"critique": response.content}


def revise(state: State) -> dict:
    """Rewrite the draft using the critique, then add the final reply to messages."""
    response = llm.invoke([
        SystemMessage(content="You are a helpful assistant. Rewrite the draft reply, fixing all issues from the critique."),
        HumanMessage(content=(
            f"Original draft:\n{state['draft']}\n\n"
            f"Critique:\n{state['critique']}\n\n"
            "Write the improved final reply only. No meta-commentary."
        )),
    ])
    return {"messages": [AIMessage(content=response.content)]}


builder = StateGraph(State)
builder.add_node("generate", generate)
builder.add_node("reflect", reflect)
builder.add_node("revise", revise)

builder.add_edge(START, "generate")
builder.add_edge("generate", "reflect")
builder.add_edge("reflect", "revise")
builder.add_edge("revise", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)


def chat(user_message: str, thread_id: str) -> str:
    """Send a message on a thread and get the final (reflected + revised) reply."""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config,
    )
    return result["messages"][-1].content


def get_thread_history(thread_id: str) -> list[dict]:
    """Return the full message history for a thread as a list of {role, content} dicts."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        messages = state.values.get("messages", [])
        history = []
        for m in messages:
            if isinstance(m, HumanMessage):
                history.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage):
                history.append({"role": "assistant", "content": m.content})
        return history
    except Exception:
        return []
