"""
LangGraph chatbot backed by an Azure-hosted OpenAI model (o4-mini),
with a checkpointer giving it memory across turns.

Same idea as checkpointer_bot.py, but the fake rule-based "model" is
replaced with a real call to your Azure AI Foundry deployment, using the
client setup you provided.

Prerequisites:
    pip install langgraph openai azure-identity
    az login          (or any other auth DefaultAzureCredential supports)

Run:
    python llm_checkpointer_bot.py
"""

from typing import TypedDict, Annotated
from operator import add

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


# --- Azure OpenAI client (from your snippet) -------------------------------
endpoint = "https://proj-app.services.ai.azure.com/openai/v1"
deployment_name = "DeepSeek-V3.2"
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://ai.azure.com/.default"
)

client = OpenAI(base_url=endpoint, api_key=token_provider)


# --- LangGraph state --------------------------------------------------------
# `messages` is a list of {"role": ..., "content": ...} dicts -- the exact
# shape the Responses API expects as `input`. The reducer (add) means new
# messages append to history rather than overwrite it.
class State(TypedDict):
    messages: Annotated[list[dict], add]


def extract_text(response) -> str:
    """Pull plain text out of a Responses API result, defensively
    (SDK versions differ slightly in how output is shaped)."""
    if getattr(response, "output_text", None):
        return response.output_text
    chunks = []
    for item in response.output:
        if getattr(item, "type", None) == "message":
            for content in item.content:
                if getattr(content, "type", None) in ("output_text", "text"):
                    chunks.append(content.text)
    return "".join(chunks) if chunks else str(response.output[0])


def call_model(state: State) -> dict:
    # state["messages"] is the FULL conversation, reconstructed from the
    # checkpoint -- this replay is exactly what the checkpointer enables.
    response = client.responses.create(
        model=deployment_name,
        input=state["messages"],
    )
    reply = extract_text(response)
    return {"messages": [{"role": "assistant", "content": reply}]}


# --- Graph: one node, compiled with a checkpointer for memory --------------
builder = StateGraph(State)
builder.add_node("call_model", call_model)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)


def run():
    thread_id = "1"
    print("LangGraph + Azure OpenAI checkpointer bot.")
    print("Commands: /new = start a fresh thread, /quit = exit\n")

    while True:
        user_input = input("You: ").strip()

        if user_input == "/quit":
            break
        if user_input == "/new":
            thread_id = str(int(thread_id) + 1)
            print(f"--- new thread started (thread_id={thread_id}) ---\n")
            continue

        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config,
        )
        print("Bot:", result["messages"][-1]["content"], "\n")


if __name__ == "__main__":
    run()