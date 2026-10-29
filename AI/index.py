import os
import sys

sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台中文/emoji 修复

from langchain_openai import ChatOpenAI
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

# 1. 创建智谱 LLM 实例
llm = ChatOpenAI(
    temperature=0.6,
    model="glm-5.3",
    api_key=os.environ.get("Zhipu_GLM", "Zhipu_GLM-xxx"),
    base_url="https://"
)

# 2. 提示词模板（注意：必须先定义 prompt，才能拼 chain）
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的 数学教师"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

# 3. 用 | 拼出链（这才是 chain，不是 import 来的）
chain = prompt | llm

# 4. 自动记忆：session_id -> 聊天历史
store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# 5. 包一层自动记忆管理
chat = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)


# ========== 怎么调用完成输出 ==========
if __name__ == "__main__":
    cfg = {"configurable": {"session_id": "user-001"}}
    # 方式二：stream —— 流式输出，生成一点打印一点（打字机效果）
    print("流式输出: ", end="")
    for chunk in chat.stream({"input": "用一句话介绍你自己"}, cfg):
        print(chunk.content, end="", flush=True)
    print()
    print("-" * 40)

    # 验证记忆：换个问法，它应该记得小明和 7
    result = chat.invoke({"input": "我叫什么？最喜欢几？"}, cfg)
    print("记忆验证:", result.content)