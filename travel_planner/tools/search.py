import os
from tavily import TavilyClient
from langchain_core.tools import tool
from dotenv import load_dotenv
from config import TAVILY_MAX_RESULTS, TAVILY_SEARCH_DEPTH
from logs import get_logger

load_dotenv(override=True)

_tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
_log    = get_logger("tools.search")


def _search(query: str, max_results: int = TAVILY_MAX_RESULTS) -> str:
    _log.info("search | query=%r | max_results=%d", query, max_results)
    results = _tavily.search(
        query=query,
        max_results=max_results,
        search_depth=TAVILY_SEARCH_DEPTH,
    )
    items = results.get("results", [])
    if not items:
        _log.warning("no results for query=%r", query)
        return "No results found."

    lines = []
    for r in items:
        title   = r.get("title",   "")
        content = r.get("content", "")[:280]
        url     = r.get("url",     "")
        lines.append(f"- **{title}**: {content}\n  📎 [{url}]({url})")

    _log.info("search | returned %d results", len(items))
    return "\n".join(lines)


@tool
def search_travel(query: str) -> str:
    """Search for travel destinations, attractions, and experiences."""
    return _search(query)


@tool
def search_travel_tips(query: str) -> str:
    """Search for practical travel tips: visa, weather, safety, currency."""
    return _search(query, max_results=4)
