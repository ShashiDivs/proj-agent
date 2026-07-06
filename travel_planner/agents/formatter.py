from langchain_core.messages import AIMessage
from prompts import get_prompt
from logs import tracer
from ._llm import call_llm, fmt

_NAME = "formatter"


def formatter_agent(state: dict) -> dict:
    tracer.start_agent(_NAME)

    system = fmt(get_prompt(_NAME, "system"), state)

    # Append user's itinerary revision note if they provided one
    feedback = state.get("itinerary_feedback", "").strip()
    feedback_section = (
        f"\n\nUser revision note (incorporate this into the final plan):\n{feedback}"
        if feedback else ""
    )

    user = fmt(get_prompt(_NAME, "user"), state) + feedback_section

    final_plan = call_llm(_NAME, system, user)
    return {
        "final_plan": final_plan,
        "messages":   [AIMessage(content=final_plan)],
    }
