from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
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


class TravelState(TypedDict):
    messages:      Annotated[list, add_messages]
    user_query:    str
    trip_style:    str
    travel_group:  str
    budget:        str
    pace:          str
    accommodation: str
    destination:   str
    duration:      str
    interests:     str
    places_found:    str
    itinerary:       str
    recommendations: str
    final_plan:      str


builder = StateGraph(TravelState)
builder.add_node("supervisor",      supervisor_agent)
builder.add_node("places",          places_agent)
builder.add_node("itinerary",       itinerary_agent)
builder.add_node("recommendations", recommendations_agent)
builder.add_node("formatter",       formatter_agent)

builder.add_edge(START,             "supervisor")
builder.add_edge("supervisor",      "places")
builder.add_edge("places",          "itinerary")
builder.add_edge("itinerary",       "recommendations")
builder.add_edge("recommendations", "formatter")
builder.add_edge("formatter",       END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)


def plan(
    user_query:    str,
    thread_id:     str,
    trip_style:    str = "Cultural & Historic",
    travel_group:  str = "Solo",
    budget:        str = "Mid-range ($$)",
    pace:          str = "Moderate",
    accommodation: str = "Hotel",
) -> tuple[str, list, dict]:
    """
    Run the full 5-agent pipeline.
    Returns (final_plan, agent_traces, summary_dict).
    """
    tracer.reset(query=user_query, thread_id=thread_id)
    _log.info(
        "pipeline start | query=%r | style=%s | group=%s | budget=%s | pace=%s",
        user_query, trip_style, travel_group, budget, pace,
    )

    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {
            "user_query":      user_query,
            "trip_style":      trip_style,
            "travel_group":    travel_group,
            "budget":          budget,
            "pace":            pace,
            "accommodation":   accommodation,
            "messages":        [HumanMessage(content=user_query)],
            "destination":     "",
            "duration":        "",
            "interests":       "",
            "places_found":    "",
            "itinerary":       "",
            "recommendations": "",
            "final_plan":      "",
        },
        config,
    )

    summary = tracer.summary()
    _log.info(
        "pipeline done | total_tokens=%d | cost=$%.6f | latency=%.0fms | searches=%d",
        summary["total_tokens"], summary["total_cost_usd"],
        summary["total_latency_ms"], summary["total_searches"],
    )
    tracer.save()   # persist to run_logs/traces.jsonl
    return result["final_plan"], list(tracer.traces), summary


def get_history(thread_id: str) -> list[dict]:
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
