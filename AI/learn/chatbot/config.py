"""配置层 —— 所有可调参数集中在这里，改配置不用动其他文件"""
import os

# 模型配置：API Key 只从环境变量 Zhipu_GLM 读取，禁止写入代码仓库
API_KEY = os.environ.get("Zhipu_GLM", "").strip()
if not API_KEY:
    raise RuntimeError(
        "缺少智谱 API Key：请先设置环境变量 Zhipu_GLM，"
        "例如 PowerShell 中执行 $env:Zhipu_GLM = \"你的智谱 API Key\""
    )

BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
MODEL_NAME = "glm-5.3"
EMBED_MODEL = "embedding-3"   # 向量模型：把文字变成一个数字向量
TEMPERATURE = 0.6

# 系统提示词：决定 AI 的性格
SYSTEM_PROMPT = "你是一个能帮助您协作工作的 AI 小会"

# Flask 配置
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True