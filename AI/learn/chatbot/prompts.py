"""提示词层 —— 所有 prompt 模板集中管理"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from chatbot.config import SYSTEM_PROMPT

chat_prompt = ChatPromptTemplate.from_messages([
    ("system",
     SYSTEM_PROMPT
     + "\n\n以下是从用户历史记忆中检索到的相关内容(可能来自很久以前)，回答时可以参考：\n{memory}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])
