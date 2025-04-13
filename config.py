import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = "https://ark.cn-beijing.volces.com/api/v3/bots"

# Tushare配置
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")

# Streamlit配置
STREAMLIT_PORT = 8501 