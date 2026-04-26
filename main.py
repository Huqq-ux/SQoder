import os
from openai import OpenAI


client = OpenAI(
    # 如果没有配置环境变量，请用阿里云百炼API Key替换：api_key="sk-xxx"
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

messages = []

while True:
    user_input = input("\n请输入您的问题（输入 'quit' 退出）：")
    if user_input.lower() == 'quit':
        break
    
    messages.append({"role": "user", "content": user_input})
    
    completion = client.chat.completions.create(
        model="qwen3.6-plus",
        messages=messages,
        extra_body={"enable_thinking": True},
        stream=True
    )
    
    assistant_response = ""
    
    for chunk in completion:
        delta = chunk.choices[0].delta
        if hasattr(delta, "content") and delta.content:
            print(delta.content, end="", flush=True)
            assistant_response += delta.content
    
    messages.append({"role": "assistant", "content": assistant_response})