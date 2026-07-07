"""
HUMAN IN THE LOOP — Pattern 3: ASK FOR CLARIFICATION

The agent starts processing a task.
Midway, it realises it doesn't have enough information and PAUSES
to ask the human a specific question.
The human's answer is injected back into state so the agent can finish.

This pattern is different from 1 & 2:
  - The agent doesn't just need a yes/no or a text edit.
  - It needs a FACT it doesn't have (e.g. a budget, a name, a date).
  - The graph resumes with that fact baked into the state.

Flow:
  analyse_task --> [PAUSE: "I need more info"]
                   human answers the question
               --> complete_task  (using the new info)

Install: pip install langgraph
Run:     python 3_hitl_clarify.py
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command


class State(TypedDict):
    task: str
    clarification: str   # filled by human mid-run
    output: str


# --- nodes ------------------------------------------------------------------

def analyse_task(state: State) -> dict:
    """Agent starts working on the task, then realizes it needs more info."""
    print(f"\n  Analysing task: '{state['task']}'")
    print("  ... I need to know the budget before I can proceed.")
    return {}


def ask_clarification(state: State) -> dict:
    """
    PAUSE: agent asks the human a specific question it needs answered.
    The human's answer comes back as the return value of interrupt().
    """
    answer = interrupt(
        "\n  Agent needs clarification:\n"
        "  What is the maximum budget for this task (in USD)? "
    )
    return {"clarification": answer}


def complete_task(state: State) -> dict:
    """Agent finishes the task using the human-provided clarification."""
    output = (
        f"Task '{state['task']}' completed.\n"
        f"Budget allocated: {state['clarification']}.\n"
        f"Plan: Sourced vendors within the approved budget and scheduled delivery."
    )
    print(f"\n  {output}")
    return {"output": output}


# --- graph ------------------------------------------------------------------

builder = StateGraph(State)
builder.add_node("analyse_task", analyse_task)
builder.add_node("ask_clarification", ask_clarification)
builder.add_node("complete_task", complete_task)

builder.add_edge(START, "analyse_task")
builder.add_edge("analyse_task", "ask_clarification")
builder.add_edge("ask_clarification", "complete_task")
builder.add_edge("complete_task", END)

graph = builder.compile(checkpointer=InMemorySaver())


# --- run --------------------------------------------------------------------

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "hitl-clarify-1"}}

    print("=" * 50)
    print("HITL Pattern 3: Ask for Clarification")
    print("=" * 50)

    # STEP 1: Run until interrupt
    result = graph.invoke(
        {"task": "Organise team offsite event", "clarification": "", "output": ""},
        config,
    )

    # STEP 2: Show the agent's question to the human
    interrupt_msg = result["__interrupt__"][0].value
    print(interrupt_msg, end="")

    # STEP 3: Human answers
    human_input = input()

    # STEP 4: Resume — the answer is injected into state via the return of interrupt()
    graph.invoke(Command(resume=human_input), config)

    print("\n  Done.")
