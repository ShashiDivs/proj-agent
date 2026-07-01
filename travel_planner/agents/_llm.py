"""Shared Azure LLM client + tracer wiring used by all agent modules."""

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from config import AZURE_ENDPOINT, AZURE_DEPLOYMENT, AZURE_SCOPE
from logs import tracer, get_logger

load_dotenv(override=True)

_token_provider = get_bearer_token_provider(DefaultAzureCredential(), AZURE_SCOPE)
_client = OpenAI(base_url=AZURE_ENDPOINT, api_key=_token_provider)
_log    = get_logger("agents.llm")


def call_llm(agent_name: str, system: str, user: str) -> str:
    """
    Call Azure chat completions, record token usage + latency in the tracer,
    and return the reply text.
    """
    _log.info("%s | prompt_chars=%d", agent_name, len(system) + len(user))
    response = _client.chat.completions.create(
        model=AZURE_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    usage = response.usage
    tracer.end_agent(
        agent_name,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )
    return response.choices[0].message.content.strip()


def fmt(template: str, state: dict) -> str:
    """Format a prompt template with state fields, skipping missing keys."""
    try:
        return template.format(**state)
    except KeyError:
        for k, v in state.items():
            template = template.replace("{" + k + "}", str(v) if v else "")
        return template
