from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from agents import (
    supervisor_agent,
    places_agent,
    itinerary_agent,
    recommendations_agent,
    formatter_agent,
)
from logs import tracer, get_logger

_log = get_logger("graph")


# ── State ─────────────────────────────────────────────────────────────────────

class TravelState(TypedDict):
    messages:      Annotated[list, add_messages]
    # User inputs
    user_query:    str
    trip_style:    str
    travel_group:  str
    budget:        str
    pace:          str
    accommodation: str
    # Derived by supervisor
    destination:   str
    duration:      str
    interests:     str
    # Agent outputs
    places_found:    str
    itinerary:       str
    recommendations: str
    final_plan:      str
    # HITL fields — set by human review nodes
    selected_places:    str   # user-filtered subset of places_found
    itinerary_feedback: str   # user's revision note after seeing itinerary


# ── HITL review nodes (each calls interrupt() to pause the graph) ─────────────

def supervisor_review_node(state: dict) -> dict:
    """Pause after supervisor so the user can confirm/edit destination & interests."""
    edits = interrupt({
        "stage":       "supervisor_review",
        "destination": state["destination"],
        "duration":    state["duration"],
        "interests":   state["interests"],
    })
    _log.info(
        "supervisor_review | confirmed destination=%s duration=%s",
        edits.get("destination"), edits.get("duration"),
    )
    return {
        "destination": edits.get("destination", state["destination"]),
        "duration":    edits.get("duration",    state["duration"]),
        "interests":   edits.get("interests",   state["interests"]),
    }


def places_review_node(state: dict) -> dict:
    """Pause after places search so the user can pick which places to include."""
    edits = interrupt({
        "stage":        "places_review",
        "places_found": state["places_found"],
    })
    selected = edits.get("selected_places", state["places_found"])
    _log.info("places_review | selected_places length=%d", len(selected))
    return {"selected_places": selected}


def itinerary_review_node(state: dict) -> dict:
    """Pause after itinerary is built so the user can approve or add revision notes."""
    edits = interrupt({
        "stage":     "itinerary_review",
        "itinerary": state["itinerary"],
    })
    feedback = edits.get("feedback", "").strip()
    _log.info("itinerary_review | feedback=%r", feedback[:80] if feedback else "(none)")
    return {"itinerary_feedback": feedback}


# ── Graph wiring ──────────────────────────────────────────────────────────────

builder = StateGraph(TravelState)

# Agent nodes
builder.add_node("supervisor",      supervisor_agent)
builder.add_node("places",          places_agent)
builder.add_node("itinerary",       itinerary_agent)
builder.add_node("recommendations", recommendations_agent)
builder.add_node("formatter",       formatter_agent)

# HITL review nodes
builder.add_node("supervisor_review", supervisor_review_node)
builder.add_node("places_review",     places_review_node)
builder.add_node("itinerary_review",  itinerary_review_node)

# Edges: agent → review → next agent
builder.add_edge(START,               "supervisor")
builder.add_edge("supervisor",        "supervisor_review")
builder.add_edge("supervisor_review", "places")
builder.add_edge("places",            "places_review")
builder.add_edge("places_review",     "itinerary")
builder.add_edge("itinerary",         "itinerary_review")
builder.add_edge("itinerary_review",  "recommendations")
builder.add_edge("recommendations",   "formatter")
builder.add_edge("formatter",         END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_status(config: dict) -> dict:
    """
    Read the current graph state and return a status dict:
      - stage="done"              → plan is ready
      - stage="supervisor_review" → waiting for human at checkpoint 1
      - stage="places_review"     → waiting for human at checkpoint 2
      - stage="itinerary_review"  → waiting for human at checkpoint 3
    """
    state = graph.get_state(config)

    if not state.next:
        # Graph finished
        values = state.values
        summary = tracer.summary()
        tracer.save()
        _log.info(
            "pipeline done | tokens=%d | cost=$%.6f | latency=%.0fms",
            summary["total_tokens"], summary["total_cost_usd"], summary["total_latency_ms"],
        )
        return {
            "stage":   "done",
            "plan":    values.get("final_plan", ""),
            "traces":  list(tracer.traces),
            "summary": summary,
        }

    # Graph is paused at an interrupt — extract the interrupt value
    interrupt_val = None
    for task in state.tasks:
        for intr in task.interrupts:
            interrupt_val = intr.value
            break

    stage = interrupt_val.get("stage", "unknown") if interrupt_val else "unknown"
    _log.info("graph paused at stage=%s", stage)
    return {"stage": stage, "data": interrupt_val}


# ── Public API ────────────────────────────────────────────────────────────────

def plan(
    user_query:    str,
    thread_id:     str,
    trip_style:    str = "Cultural & Historic",
    travel_group:  str = "Solo",
    budget:        str = "Mid-range ($$)",
    pace:          str = "Moderate",
    accommodation: str = "Hotel",
) -> dict:
    """
    Start the pipeline. Runs supervisor then pauses at supervisor_review.
    Returns a status dict (see _get_status).
    """
    tracer.reset(query=user_query, thread_id=thread_id)
    _log.info("pipeline start | query=%r | thread=%s", user_query, thread_id)

    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke(
        {
            "user_query":        user_query,
            "trip_style":        trip_style,
            "travel_group":      travel_group,
            "budget":            budget,
            "pace":              pace,
            "accommodation":     accommodation,
            "messages":          [HumanMessage(content=user_query)],
            "destination":       "",
            "duration":          "",
            "interests":         "",
            "places_found":      "",
            "selected_places":   "",
            "itinerary":         "",
            "itinerary_feedback":"",
            "recommendations":   "",
            "final_plan":        "",
        },
        config,
    )
    return _get_status(config)


def resume(thread_id: str, user_data: dict) -> dict:
    """
    Resume the graph after a human checkpoint.
    `user_data` is passed as the interrupt return value to the review node.
    Returns the next status dict.
    """
    config = {"configurable": {"thread_id": thread_id}}
    _log.info("resume | thread=%s | data_keys=%s", thread_id, list(user_data.keys()))
    graph.invoke(Command(resume=user_data), config)
    return _get_status(config)


def get_history(thread_id: str) -> list[dict]:
    """Return {role, content} message history for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        history = []
        for m in state.values.get("messages", []):
            if isinstance(m, HumanMessage):
                history.append({"role": "user",      "content": m.content})
            elif isinstance(m, AIMessage):
                history.append({"role": "assistant", "content": m.content})
        return history
    except Exception:
        return []
