from langgraph.checkpoint.memory import InMemorySaver

from movie_script import workflow

checkpointer = InMemorySaver()

workflow_graph = workflow.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "thread-1"}}

result = workflow_graph.invoke(
    {"intentions": "A Post Modern Story of a man who is trying to find his purpose in life and how he finds it."},
    config,
)

print(result["final_script"])

# simple chatbot with memory and use thread_id to keep track of the conversation and find the thread_id's along with the conversation
