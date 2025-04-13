# Dual EMA with LLM

基于双均线策略的量化交易系统，集成 LLM 进行策略开仓时机优化。

## 功能特点

- 支持股票、期货、基金等多种资产的数据获取和分析
- 支持日线及分钟级别数据的处理
- 集成 DeepSeek API 进行策略优化和分析
- 提供完整的技术指标计算库
- 数据本地缓存，避免重复请求
- 完整的日志记录系统
- Web 界面展示（基于 Streamlit）
![image](https://github.com/user-attachments/assets/8c014ebc-e207-4a73-8f1e-4e946b4ce0d7)

## 环境要求

- Python 3.8+
- TA-Lib
- Streamlit
- Tushare
- Pandas & NumPy
- Loguru

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/sencloud/Dual_EMA_with_LLM.git
cd Dual_EMA_with_LLM
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
在项目根目录创建 `.env` 文件（参考 `.env.example`）：
```python
TUSHARE_TOKEN = "你的tushare token"
DEEPSEEK_API_KEY = "你的deepseek api key"
LOG_LEVEL = "INFO"
```

## 使用示例

```python
# 数据获取
from data_fetcher import DataFetcher
from config import TUSHARE_TOKEN

fetcher = DataFetcher(TUSHARE_TOKEN)
df = fetcher.get_minute_data("000001.SZ", "20230101", "20241231", "60min")

# EMA 分析
from ema_analyzer import EMAAnalyzer

analyzer = EMAAnalyzer(df)
signals = analyzer.generate_signals()

# 运行 Web 界面
streamlit run app.py
```

## 项目结构

```
.
├── app.py              # Streamlit Web 应用
├── data_fetcher.py     # 数据获取模块
├── ema_analyzer.py     # EMA 策略分析
├── technical_indicators.py  # 技术指标库
├── deepseek_client.py  # DeepSeek API 客户端
├── logger.py           # 日志配置
├── config.py           # 配置文件
├── requirements.txt    # 项目依赖
├── minute_data/        # 分钟数据缓存
├── logs/              # 日志文件
└── README.md          # 说明文档
```

## 主要模块

### 数据获取 (data_fetcher.py)
- 支持多种数据源的数据获取
- 本地数据缓存机制
- 自动错误重试

### EMA 分析 (ema_analyzer.py)
- 双均线策略实现
- 信号生成和回测
- 性能评估

### 技术指标 (technical_indicators.py)
- 常用技术指标计算
- 自定义指标支持
- 高性能实现

### Web 界面 (app.py)
- 数据可视化
- 策略参数调整
- 实时分析展示

## 免责声明
本项目开源仅作爱好，请谨慎使用，本人不对代码产生的任何使用后果负责。

## 其他
如果你喜欢我的项目，可以给我买杯咖啡：
<img src="https://github.com/user-attachments/assets/e75ef971-ff56-41e5-88b9-317595d22f81" alt="image" width="300" height="300">

## License

MIT
