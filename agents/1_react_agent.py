"""
1) REACT AGENT — reason, act (use a tool), observe, repeat until done.
No self-critique. Just keeps acting until it has an answer.

Install: pip install langgraph langchain langchain-openai
Run:     export OPENAI_API_KEY=sk-...  &&  python 1_react_agent.py
"""
from langchain_community.tools import TavilySearchResults
from requests import Response
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv(override=True)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = TavilyClient(api_key=TAVILY_API_KEY)

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")

# use tavily api to get the weather

@tool
def get_weather_tavily(city: str) -> str:
    """Get the current weather for a given city."""
    response = client.search(query=f"weather in {city}")
    return str(response.get("results", "No results found."))



model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)

# One line builds the whole loop: model -> maybe call tool -> model again -> ...
agent = create_agent(model=model, tools=[get_weather_tavily])

if __name__ == "__main__":
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in Hyderabad India?"}]}
    )
    print(result["messages"][-1].content)

# use wikipedia api to get the information then create a chatbot that can answer questions about the information
# use 4 tools movies, books, music, games