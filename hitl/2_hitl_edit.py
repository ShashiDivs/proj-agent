"""
HUMAN IN THE LOOP — Pattern 2: EDIT BEFORE CONTINUE

The agent writes a draft email.
It PAUSES and shows the human the draft.
The human can edit it (or press Enter to keep it as-is).
The agent then sends the (possibly edited) version.

Key concept here: interrupt() returns whatever the human types.
If the human types an edit, we use that.
If they just press Enter, we keep the original draft.

Flow:
  write_draft --> [PAUSE: show draft, let human edit]
              --> send_email (with the final version)

Install: pip install langgraph
Run:     python 2_hitl_edit.py
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command


class State(TypedDict):
    topic: str
    draft: str
    final_email: str


# --- nodes ------------------------------------------------------------------

def write_draft(state: State) -> dict:
    """Agent writes a first draft (fake, no LLM needed for the demo)."""
    draft = (
        f"Subject: Update on {state['topic']}\n\n"
        f"Hi team,\n\n"
        f"I wanted to share a quick update regarding {state['topic']}. "
        f"Everything is on track and we expect to meet our deadline.\n\n"
        f"Best regards,\nAgent"
    )
    print(f"\n  Draft written.")
    return {"draft": draft}


def human_review(state: State) -> dict:
    """
    PAUSE. Show the draft to the human.
    They can type an edited version, or just press Enter to keep the draft.
    """
    edited = interrupt(
        f"\n--- DRAFT EMAIL ---\n{state['draft']}\n-------------------\n"
        "Press Enter to send as-is, or type your edited version: "
    )
    # If human pressed Enter (empty string), keep the original draft.
    final = edited.strip() if edited.strip() else state["draft"]
    return {"final_email": final}


def send_email(state: State) -> dict:
    """Send the final (possibly human-edited) email."""
    print(f"\n  Sending email:\n{state['final_email']}")
    return {}


# --- graph ------------------------------------------------------------------

builder = StateGraph(State)
builder.add_node("write_draft", write_draft)
builder.add_node("human_review", human_review)
builder.add_node("send_email", send_email)

builder.add_edge(START, "write_draft")
builder.add_edge("write_draft", "human_review")
builder.add_edge("human_review", "send_email")
builder.add_edge("send_email", END)

graph = builder.compile(checkpointer=InMemorySaver())


# --- run --------------------------------------------------------------------

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "hitl-edit-1"}}

    print("=" * 50)
    print("HITL Pattern 2: Edit Before Continue")
    print("=" * 50)

    # STEP 1: Run until interrupt (after draft is written)
    result = graph.invoke({"topic": "Q3 Project Status"}, config)

    # STEP 2: Show interrupt prompt to human
    interrupt_msg = result["__interrupt__"][0].value
    print(interrupt_msg, end="")

    # STEP 3: Human edits (or just presses Enter)
    human_input = input()

    # STEP 4: Resume with human's input
    graph.invoke(Command(resume=human_input), config)

    print("\n  Email sent!")
