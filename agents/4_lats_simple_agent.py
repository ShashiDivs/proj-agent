"""
4) LATS (simplified) — Language Agent Tree Search.

Instead of one draft -> one critique -> one revision (Reflection/Reflexion),
LATS explores MULTIPLE candidate answers in parallel, scores each one,
keeps the best, and refines further from there — like a tree of
possibilities instead of a single path.

This is a SIMPLIFIED  version (2 candidates, 1 level of
expansion). Real LATS does proper tree search with backpropagation of
scores across many branches and depths — see the LangChain blog post
"Reflection Agents" for the full version.

Install: pip install langgraph langchain-openai
Run:     export OPENAI_API_KEY=sk-...  &&  python 4_lats_simple_agent.py
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini")

NUM_CANDIDATES = 2  # "branches" explored at each step


class Candidate(TypedDict):
    text: str
    score: float


class State(TypedDict):
    question: str
    round1_candidates: list[Candidate]
    best_so_far: str
    round2_candidates: list[Candidate]
    final: str


def score(question: str, answer: str) -> float:
    """Ask the model to rate an answer 1-10. A real LATS would also use
    tool/environment feedback here, not just an LLM judge."""
    prompt = (
        f"Question: {question}\nAnswer: {answer}\n"
        "Rate this answer's quality from 1-10. Reply with ONLY the number."
    )
    response = model.invoke(prompt)
    try:
        return float(response.content.strip())
    except ValueError:
        return 5.0  # fallback if the model didn't return a clean number


def expand_round1(state: State) -> dict:
    """Generate several different candidate answers (the tree's branches)."""
    candidates = []
    for i in range(NUM_CANDIDATES):
        response = model.invoke(
            f"Answer this question, attempt #{i+1} with a different angle: "
            f"{state['question']}"
        )
        candidates.append({"text": response.content, "score": score(state["question"], response.content)})
    return {"round1_candidates": candidates}


def pick_best_round1(state: State) -> dict:
    """Keep only the highest-scoring branch — this is the 'search' part."""
    best = max(state["round1_candidates"], key=lambda c: c["score"])
    return {"best_so_far": best["text"]}


def expand_round2(state: State) -> dict:
    """From the best branch, generate refined follow-up candidates
    (one more level of the tree)."""
    candidates = []
    for i in range(NUM_CANDIDATES):
        response = model.invoke(
            f"Improve this answer further (variation #{i+1}):\n{state['best_so_far']}"
        )
        candidates.append({"text": response.content, "score": score(state["question"], response.content)})
    return {"round2_candidates": candidates}


def pick_final(state: State) -> dict:
    """Final selection: best of round 2, or fall back to round 1 if
    nothing improved."""
    best = max(state["round2_candidates"], key=lambda c: c["score"])
    return {"final": best["text"]}


builder = StateGraph(State)
builder.add_node("expand_round1", expand_round1)
builder.add_node("pick_best_round1", pick_best_round1)
builder.add_node("expand_round2", expand_round2)
builder.add_node("pick_final", pick_final)

builder.add_edge(START, "expand_round1")
builder.add_edge("expand_round1", "pick_best_round1")
builder.add_edge("pick_best_round1", "expand_round2")
builder.add_edge("expand_round2", "pick_final")
builder.add_edge("pick_final", END)

graph = builder.compile()

if __name__ == "__main__":
    result = graph.invoke({"question": "What's a good way to explain recursion to a beginner?"})
    print("FINAL ANSWER:\n", result["final"])
