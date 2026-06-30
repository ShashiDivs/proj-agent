import os
from typing import TypedDict, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")

# =====================================================================
# 1. DEFINE THE GRAPH STATE & ROUTING SCHEMA
# =====================================================================

class IntentClassification(BaseModel):
    """Structured output schema for the Intent Classifier Node."""
    intent: Literal["movie_idea", "vague_or_greeting"] = Field(
        description="Categorize as 'movie_idea' if the user provides a premise, plot, character, or concept. Categorize as 'vague_or_greeting' if it's a hello, too short, or unrelated."
    )

class ScriptState(TypedDict):
    """The state object passed between nodes in the LangGraph workflow."""
    intentions: str
    classification: str
    genre_style: str
    critique: str
    final_script: str

# Initialize the Language Model
llm = ChatOpenAI(model="gpt-4o", temperature=0.7,api_key=api_key)
llm_deterministic = ChatOpenAI(model="gpt-4o", temperature=0.0,api_key=api_key)

# =====================================================================
# 2. DEFINE THE NODES
# =====================================================================

def classifier_node(state: ScriptState) -> dict:
    print("\n🧠 [Node: Classifier] Analyzing user query intent...")
    structured_llm = llm_deterministic.with_structured_output(IntentClassification)
    prompt = f"Analyze this user query and classify its intent: {state['intentions']}"
    result = structured_llm.invoke(prompt)
    print(f"   -> Classified as: {result.intent}")
    return {"classification": result.intent}

def clarification_node(state: ScriptState) -> dict:
    print("❓ [Node: Clarification] Requesting more details...")
    msg = (
        "Hey there! It looks like your prompt was a bit brief or just a greeting. "
        "Could you tell me a little more about your movie idea? For example: What is "
        "the main character's goal, or what's the central conflict?"
    )
    return {"final_script": msg}

def genres_node(state: ScriptState) -> dict:
    print("🎬 [Node: Genres] Brainstorming concepts and picking angles...")
    prompt = (
        f"You are an expert Hollywood screenwriter and genre specialist.\n"
        f"Based on the user's core intentions, brainstorm 2-3 blended film genres that fit perfectly, "
        f"and write a compelling logline and a brief 1-paragraph plot setup.\n\n"
        f"User Intentions: {state['intentions']}"
    )
    response = llm.invoke([
        SystemMessage(content="You are a creative screenwriter."), 
        HumanMessage(content=prompt)
    ])
    return {"genre_style": response.content}

def critique_node(state: ScriptState) -> dict:
    print("🧐 [Node: Critique] Analyzing the concept for flaws...")
    prompt = (
        f"You are a harsh but brilliant film critic and script doctor.\n"
        f"Review the following proposed movie concept. Identify plot holes, cliché tropes, "
        f"and structural weaknesses. Provide 3 specific, constructive recommendations to make it more unique and engaging.\n\n"
        f"Proposed Concept:\n{state['genre_style']}"
    )
    response = llm.invoke([
        SystemMessage(content="You are a critical script doctor."), 
        HumanMessage(content=prompt)
    ])
    return {"critique": response.content}

def final_draft_node(state: ScriptState) -> dict:
    print("✍️ [Node: Final Draft] Formatting and polishing the script...")
    prompt = (
        f"You are an award-winning screenwriter. Write the opening scene script (in industry-standard screenplay format) "
        f"integrating the initial concept and fixing the issues brought up in the critique.\n\n"
        f"Initial Concept:\n{state['genre_style']}\n\n"
        f"Critique & Revisions to apply:\n{state['critique']}\n\n"
        f"Output ONLY the beautifully formatted script scene."
    )
    response = llm.invoke([
        SystemMessage(content="You write flawless industry-standard screenplays."), 
        HumanMessage(content=prompt)
    ])
    return {"final_script": response.content}

# =====================================================================
# 3. ROUTING FUNCTION (CONDITIONAL EDGE)
# =====================================================================

def route_based_on_intent(state: ScriptState) -> Literal["genres", "clarification"]:
    if state["classification"] == "movie_idea":
        return "genres"
    else:
        return "clarification"

# =====================================================================
# 4. BUILD AND COMPILE THE GRAPH
# =====================================================================

workflow = StateGraph(ScriptState)

workflow.add_node("classifier", classifier_node)
workflow.add_node("clarification", clarification_node)
workflow.add_node("genres", genres_node)       
workflow.add_node("critique", critique_node)     
workflow.add_node("final_draft", final_draft_node) 

workflow.add_edge(START, "classifier")

workflow.add_conditional_edges(
    "classifier",
    route_based_on_intent,
    {
        "genres": "genres",
        "clarification": "clarification"
    }
)

workflow.add_edge("clarification", END)
workflow.add_edge("genres", "critique")
workflow.add_edge("critique", "final_draft")
workflow.add_edge("final_draft", END)

app = workflow.compile()

# =====================================================================
# 5. EXECUTION SAMPLES
# =====================================================================

if __name__ == "__main__":
    print("--- Test A: Vague Query Prompt ---")
    test_a_input = {"intentions": "Hey, write me a script!"}
    output_a = app.invoke(test_a_input)
    print("\nRESULT A:")
    print(output_a["final_script"])
    
    print("\n" + "="*50 + "\n")
    
    print("--- Test B: Valid Creative Premise ---")
    test_b_input = {
        "intentions": "A Post Modern Story of a man who is trying to find his purpose in life and how he finds it."
    }
    output_b = app.invoke(test_b_input)
    print("\nRESULT B:")
    print(output_b["final_script"])