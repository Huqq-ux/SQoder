from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的编程专家，擅长解决各种编程问题，并且能够根据用户的问题生成专业的代码。"),
    MessagesPlaceholder(variable_name = "chat_history"),
    ("human", "{question}"),
])
