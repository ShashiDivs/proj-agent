from config import ACTIVE_PROMPT_VERSIONS
from . import supervisor, places, itinerary, recommendations, formatter

_REGISTRY = {
    "supervisor":      supervisor.VERSIONS,
    "places":          places.VERSIONS,
    "itinerary":       itinerary.VERSIONS,
    "recommendations": recommendations.VERSIONS,
    "formatter":       formatter.VERSIONS,
}


def get_prompt(agent: str, role: str) -> str:
    """Return system or user prompt for an agent using its active version."""
    version = ACTIVE_PROMPT_VERSIONS[agent]
    return _REGISTRY[agent][version][role]


def get_search_query(agent: str, key: str) -> str:
    """Return a Tavily search query template for places or recommendations agents."""
    version = ACTIVE_PROMPT_VERSIONS[agent]
    return _REGISTRY[agent][version][key]
