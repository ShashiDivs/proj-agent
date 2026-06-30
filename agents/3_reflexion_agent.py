"""
3) REFLEXION AGENT — like Reflection, but the critique is grounded in
real evidence from a tool instead of just the model's opinion.

Roles:
  - actor: writes the first answer
  - tool check: verifies claims against an external source (here, a
    fake fact database — swap for real web search in production)
  - revisor: rewrites the answer using the actor's draft + the tool's
    findings, explicitly fixing anything wrong or missing

This is the key difference from basic Reflection: the critique isn't
just "this sounds off" — it's "this claim was checked and is false."

Install: pip install langgraph langchain-openai
Run:     export OPENAI_API_KEY=sk-...  &&  python 3_reflexion_agent.py
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")

model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)



# Fake fact-checking "tool" — in a real app this would be a web search
# or a database lookup. Keeping it fake here so the example runs
# instantly and deterministically.
def fact_check(claim: str) -> str:
    facts = {
        "eiffel tower": "Built in 1889, located in Paris, 330 meters tall.",
    }
    for key, fact in facts.items():
        if key in claim.lower():
            return fact
    return "No external data found for this claim."


class State(TypedDict):
    question: str
    draft: str
    tool_findings: str
    final: str


def actor(state: State) -> dict:
    """Write a first-pass answer."""
    response = model.invoke(f"Answer briefly: {state['question']}")
    return {"draft": response.content}


def check_facts(state: State) -> dict:
    """Ground the draft's claims against the external 'tool'."""
    findings = fact_check(state["draft"])
    return {"tool_findings": findings}


def revisor(state: State) -> dict:
    """Rewrite the answer, correcting anything the tool contradicts."""
    prompt = (
        "Revise the draft answer below using the verified facts. "
        "Correct any wrong details and remove anything not supported.\n\n"
        f"Question: {state['question']}\n"
        f"Draft answer: {state['draft']}\n"
        f"Verified facts: {state['tool_findings']}"
    )
    response = model.invoke(prompt)
    return {"final": response.content}


builder = StateGraph(State)
builder.add_node("actor", actor)
builder.add_node("check_facts", check_facts)
builder.add_node("revisor", revisor)
builder.add_edge(START, "actor")
builder.add_edge("actor", "check_facts")
builder.add_edge("check_facts", "revisor")
builder.add_edge("revisor", END)

graph = builder.compile()

if __name__ == "__main__":
    result = graph.invoke({"question": "How tall is the Eiffel Tower and when was it built?"})
    print("DRAFT:\n", result["draft"])
    print("\nTOOL FINDINGS:\n", result["tool_findings"])
    print("\nFINAL (corrected):\n", result["final"])
