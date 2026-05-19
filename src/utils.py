import os
from openai import OpenAI

def get_client():
    return OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
    )

def call_llm(prompt, system_prompt="", model=None):
    client = get_client()
    model = model or os.getenv("DEEPSEEK_MODEL", "mimo-v2.5")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model=model, messages=messages, temperature=0.7)
    return response.choices[0].message.content
