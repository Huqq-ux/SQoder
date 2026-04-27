from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from Coder.model.model import llm
from Coder.tools.file_tools import file_management_toolkit
from Coder.tools.knowledge_toolkit import knowledge_toolkit
from langgraph.checkpoint.memory import MemorySaver

def create_agent_with_memory():
    memory = MemorySaver()
    agent = create_agent(
        model=llm,
        tools=file_management_toolkit + knowledge_toolkit,
        checkpointer=memory,
        debug=True,
    )
    return agent

def run_agent():
    config = RunnableConfig(configurable = {"thread_id": "1"})
    agent = create_agent_with_memory()
    res = agent.invoke({"messages": [("user", "你好,你是谁")]}, config = config)
    print(res)

if __name__ == "__main__":
    run_agent()
