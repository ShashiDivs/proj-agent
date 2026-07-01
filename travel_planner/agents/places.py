from langchain_core.messages import AIMessage
from prompts import get_search_query
from tools import search_travel
from logs import tracer
from ._llm import fmt

_NAME = "places"


def places_agent(state: dict) -> dict:
    tracer.start_agent(_NAME)

    def q(key: str) -> str:
        return fmt(get_search_query(_NAME, key), state)

    attractions = search_travel.invoke(q("search_attractions")); tracer.count_search(_NAME)
    food        = search_travel.invoke(q("search_food"));        tracer.count_search(_NAME)
    hidden      = search_travel.invoke(q("search_hidden"));      tracer.count_search(_NAME)
    stay        = search_travel.invoke(q("search_stay"));        tracer.count_search(_NAME)

    places_found = (
        f"### 🏛️ Attractions & Activities\n{attractions}\n\n"
        f"### 🍽️ Food & Dining\n{food}\n\n"
        f"### 💎 Hidden Gems\n{hidden}\n\n"
        f"### 🏨 Where to Stay\n{stay}"
    )

    tracer.end_agent_no_llm(_NAME, search_calls=4)
    return {
        "places_found": places_found,
        "messages":     [AIMessage(content="Searched attractions, dining, hidden gems, and accommodation.")],
    }
