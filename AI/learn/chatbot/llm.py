"""模型层 —— 只负责创建 LLM 实例，以后换模型只改这里"""
from langchain_openai import ChatOpenAI

from chatbot.config import API_KEY, BASE_URL, MODEL_NAME, TEMPERATURE

llm = ChatOpenAI(
    temperature=TEMPERATURE,
    model=MODEL_NAME,
    api_key=API_KEY,
    base_url=BASE_URL,
)
