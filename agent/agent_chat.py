from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis import RedisSaver
from Coder.model.model import llm
from Coder.tools.file_tools import file_management_toolkit


def create_redis_agent():
    with RedisSaver.from_conn_string("redis://localhost:6379") as memory:
        memory.setup()
        agent = create_agent(
            model = llm,
            tools = file_management_toolkit,
            checkpointer = memory,
            debug = True,
        )
        return agent

def run_agent():
    config = RunnableConfig(configurable = {"thread_id": "1"})
    agent = create_redis_agent()
    res = agent.invoke({"messages": [("user", "你好,你是谁")]}, config = config)
    print(res)

if __name__ == "__main__":
    run_agent()
