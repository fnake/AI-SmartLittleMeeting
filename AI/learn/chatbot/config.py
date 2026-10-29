"""配置层 —— 所有可调参数集中在这里，改配置不用动其他文件"""
import os

# 模型配置（建议把 key 放进环境变量 Zhipu_GLM，别硬编码到代码里）
API_KEY = os.environ.get("Zhipu_GLM", "530786c07c0d42a69fa67d2157fa1dc8.RbfJ1y2lDFmrhoxm")
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
MODEL_NAME = "glm-5.3"
EMBED_MODEL = "embedding-3"   # 向量模型: 把文字变成一串数字(向量)
TEMPERATURE = 0.6

# 系统提示词：决定 AI 的人设
SYSTEM_PROMPT = "你是一个能帮助您协作工作的 AI 小会"

# Flask 配置
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True
