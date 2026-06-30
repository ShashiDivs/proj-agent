"""
2) REFLECTION AGENT — generate, critique, revise. Repeat a few times.

Two roles, both played by the same model with different prompts:
  - generator: writes/revises the answer
  - reflector: critiques it

No tools, no grounding in facts — the critique is just the model's
own opinion of its own work ("vibes-based" self-correction).

Install: pip install langgraph langchain-openai
Run:     export OPENAI_API_KEY=sk-...  &&  python 2_reflection_agent.py
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")

model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)

MAX_ITERATIONS = 2  # how many times to critique + revise before stopping


class State(TypedDict):
    topic: str
    draft: str
    critique: str
    iteration: int


def generate(state: State) -> dict:
    """Write a first draft, or revise based on the latest critique."""
    if state.get("draft"):
        prompt = (
            f"Revise this draft based on the critique.\n\n"
            f"Draft:\n{state['draft']}\n\nCritique:\n{state['critique']}"
        )
    else:
        prompt = f"Write a short, 3-sentence explanation of: {state['topic']}"

    response = model.invoke(prompt)
    return {"draft": response.content, "iteration": state.get("iteration", 0) + 1}


def reflect(state: State) -> dict:
    """Critique the current draft."""
    prompt = (
        "You are a strict editor. Critique this draft in 2-3 sentences. "
        "Point out anything unclear, missing, or wrong.\n\n"
        f"Draft:\n{state['draft']}"
    )
    response = model.invoke(prompt)
    return {"critique": response.content}


def should_continue(state: State) -> str:
    """Loop back to 'generate' to revise, or stop after MAX_ITERATIONS."""
    if state["iteration"] >= MAX_ITERATIONS:
        return END
    return "generate"


builder = StateGraph(State)
builder.add_node("generate", generate)
builder.add_node("reflect", reflect)
builder.add_edge(START, "generate")
builder.add_edge("generate", "reflect")
builder.add_conditional_edges("reflect", should_continue)

graph = builder.compile()

if __name__ == "__main__":
    result = graph.invoke({"topic": "why AI is the future", "iteration": 0})
    print("FINAL DRAFT:\n", result["draft"])
    print("\nLAST CRITIQUE:\n", result["critique"])
