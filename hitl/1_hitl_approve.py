"""
HUMAN IN THE LOOP — Pattern 1: APPROVE / REJECT

The agent plans a dangerous action (e.g. delete a file).
It PAUSES and asks the human: approve or reject?
Only if approved does it actually execute.

Key concepts:
  interrupt(payload) — pauses the graph, shows payload to the human.
                       Returns whatever the human sends back.
  Command(resume=...) — how you hand the human's answer back to the graph.
  Checkpointer       — REQUIRED. Saves the state while paused.

Flow:
  plan_action --> [PAUSE: show human what's about to happen]
                  human types "approve" or "reject"
              --> execute_action (if approved)
              --> cancelled     (if rejected)

Install: pip install langgraph
Run:     python 1_hitl_approve.py
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command


class State(TypedDict):
    action: str          # what the agent wants to do
    decision: str        # "approved" or "rejected" — filled by human
    result: str          # outcome


# --- nodes ------------------------------------------------------------------

def plan_action(state: State) -> dict:
    """Agent decides what action it wants to take."""
    action = "DELETE all records older than 30 days from the database"
    print(f"\n  Agent planned: '{action}'")
    return {"action": action}


def get_human_approval(state: State) -> dict:
    """
    PAUSE HERE. Show the human what the agent wants to do.
    The graph freezes until the human resumes it with Command(resume=...).
    """
    # interrupt() pauses the graph and returns the human's response.
    # The string passed to interrupt() is shown to the human as a prompt.
    decision = interrupt(
        f"\nAgent wants to: {state['action']}\n"
        "Type 'approve' to allow, anything else to cancel: "
    )
    return {"decision": decision}


def execute_action(state: State) -> dict:
    """Only reached if human approved."""
    print(f"  Executing: {state['action']}")
    return {"result": "Action executed successfully."}


def cancel_action(state: State) -> dict:
    """Only reached if human rejected."""
    print("  Action cancelled by human.")
    return {"result": "Action was rejected and not executed."}


def route_on_decision(state: State) -> str:
    """Route based on the human's decision."""
    if state["decision"].strip().lower() == "approve":
        return "execute_action"
    return "cancel_action"


# --- graph ------------------------------------------------------------------

builder = StateGraph(State)
builder.add_node("plan_action", plan_action)
builder.add_node("get_human_approval", get_human_approval)
builder.add_node("execute_action", execute_action)
builder.add_node("cancel_action", cancel_action)

builder.add_edge(START, "plan_action")
builder.add_edge("plan_action", "get_human_approval")
builder.add_conditional_edges("get_human_approval", route_on_decision)
builder.add_edge("execute_action", END)
builder.add_edge("cancel_action", END)

graph = builder.compile(checkpointer=InMemorySaver())


# --- run --------------------------------------------------------------------

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "hitl-approve-1"}}

    # STEP 1: Run until the graph hits interrupt()
    print("=" * 50)
    print("HITL Pattern 1: Approve / Reject")
    print("=" * 50)

    result = graph.invoke({"action": "", "decision": "", "result": ""}, config)

    # The graph is now paused. Read the interrupt message from the result.
    interrupt_msg = result["__interrupt__"][0].value
    print(interrupt_msg, end="")

    # STEP 2: Human types their decision
    human_input = input()

    # STEP 3: Resume the graph with the human's answer
    final = graph.invoke(Command(resume=human_input), config)

    print(f"\n  Result: {final['result']}")

