from langchain_core.messages import AIMessage
from prompts import get_prompt, get_search_query
from tools import search_travel_tips
from logs import tracer
from ._llm import call_llm, fmt

_NAME = "recommendations"


def recommendations_agent(state: dict) -> dict:
    tracer.start_agent(_NAME)

    def q(key: str) -> str:
        return fmt(get_search_query(_NAME, key), state)

    raw_tips = "\n\n".join([
        f"Visa & Entry:\n{search_travel_tips.invoke(q('search_visa'))}",
        f"Weather:\n{search_travel_tips.invoke(q('search_weather'))}",
        f"Safety & Customs:\n{search_travel_tips.invoke(q('search_safety'))}",
        f"Currency & Budget:\n{search_travel_tips.invoke(q('search_currency'))}",
    ])
    tracer.count_search(_NAME)
    tracer.count_search(_NAME)
    tracer.count_search(_NAME)
    tracer.count_search(_NAME)

    system          = fmt(get_prompt(_NAME, "system"), state)
    user            = fmt(get_prompt(_NAME, "user"), {**state, "raw_tips": raw_tips})
    recommendations = call_llm(_NAME, system, user)

    return {
        "recommendations": recommendations,
        "messages":        [AIMessage(content="Practical recommendations compiled.")],
    }
