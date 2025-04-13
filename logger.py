import sys
import os
from loguru import logger
from datetime import datetime

# 创建logs目录
if not os.path.exists("logs"):
    os.makedirs("logs")

# 生成日志文件名
log_file = f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"

# 配置日志
logger.remove()  # 移除默认的处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="00:00",  # 每天轮换
    retention="30 days",  # 保留30天
    encoding="utf-8"
) 