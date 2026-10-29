"""链层 —— 把 模型 + 提示词 + 记忆 组装成完整聊天链"""
from langchain_core.runnables.history import RunnableWithMessageHistory

from chatbot.llm import llm
from chatbot.memory import get_session_history
from chatbot.prompts import chat_prompt

# 基础链：提示词 | 模型
base_chain = chat_prompt | llm

# 包一层自动记忆，得到最终对外使用的 chat
chat = RunnableWithMessageHistory(
    base_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)
