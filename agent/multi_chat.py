import os
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_community.chat_message_histories import FileChatMessageHistory
from Coder.model import llm
from Coder.prompt import prompt

base_dir = os.path.dirname(os.path.abspath(__file__))

def get_session_history(session_id : str):
    try:
        history_file = os.path.join(base_dir, f"chat_history_{session_id}.json")
        return FileChatMessageHistory(history_file)
    except Exception as e:
        print(f"加载聊天历史失败: {e}")
        return FileChatMessageHistory(os.path.join(base_dir, f"chat_history_{session_id}.json"))

chain = prompt | llm | StrOutputParser()

chain_with_history = RunnableWithMessageHistory(
    runnable = chain,
    get_session_history = get_session_history,
    input_messages_key = "question",
    history_messages_key = "chat_history",
)

session_id = 1
while True:
    try:
        user_input = input("用户: ")
        if user_input.lower() == "exit" or user_input.lower() == "quit":
            break
        print("助手:")
        for chunk in chain_with_history.stream(
            {"question": user_input},
            config = {"configurable": {"session_id": str(session_id)}}
        ):
            print(chunk, end = "", flush = True)
        print("\n")
    except KeyboardInterrupt:
        print("\n程序已中断")
        break
    except Exception as e:
        print(f"\n发生错误: {e}")
        continue

