import json
from langchain_core.messages import AIMessage
from prompts import get_prompt
from logs import tracer
from ._llm import call_llm, fmt

_NAME = "supervisor"


def supervisor_agent(state: dict) -> dict:
    tracer.start_agent(_NAME)

    system = get_prompt(_NAME, "system")
    user   = fmt(get_prompt(_NAME, "user"), state)
    raw    = call_llm(_NAME, system, user)   # tracer.end_agent called inside call_llm

    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed  = json.loads(cleaned)
        destination = parsed.get("destination", "Unknown")
        duration    = parsed.get("duration",    "3 days")
        interests   = parsed.get("interests",   state.get("trip_style", "sightseeing"))
    except Exception:
        destination = "Unknown"
        duration    = "3 days"
        interests   = state.get("trip_style", "sightseeing")

    summary = (
        f"Planning your **{duration}** trip to **{destination}**.\n"
        f"Style: {state.get('trip_style')} · Group: {state.get('travel_group')} · "
        f"Budget: {state.get('budget')} · Pace: {state.get('pace')} · "
        f"Stay: {state.get('accommodation')}"
    )
    return {
        "destination": destination,
        "duration":    duration,
        "interests":   interests,
        "messages":    [AIMessage(content=summary)],
    }
