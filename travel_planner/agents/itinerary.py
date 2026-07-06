from langchain_core.messages import AIMessage
from prompts import get_prompt
from logs import tracer
from ._llm import call_llm, fmt

_NAME = "itinerary"


def itinerary_agent(state: dict) -> dict:
    tracer.start_agent(_NAME)

    # Use user-selected places if the human review filtered them,
    # otherwise fall back to the full places_found.
    places = state.get("selected_places") or state.get("places_found", "")

    system = fmt(get_prompt(_NAME, "system"), state)
    user   = fmt(get_prompt(_NAME, "user"), {**state, "places_found": places})

    itinerary = call_llm(_NAME, system, user)
    return {
        "itinerary": itinerary,
        "messages":  [AIMessage(content="Day-by-day itinerary created.")],
    }
