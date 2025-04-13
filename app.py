import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import asyncio
from data_fetcher import DataFetcher
from technical_indicators import TechnicalIndicators
from ema_analyzer import EMAAnalyzer
from deepseek_client import DeepSeekClient
from config import DEEPSEEK_API_KEY, TUSHARE_TOKEN
from logger import logger

# 初始化客户端
logger.info("初始化系统组件")
deepseek_client = DeepSeekClient()
data_fetcher = DataFetcher(TUSHARE_TOKEN)

# 页面配置
st.set_page_config(
    page_title="双均线交易策略分析",
    page_icon="📈",
    layout="wide"
)

# 标题
st.title("双均线交易策略分析")

# 侧边栏配置
with st.sidebar:
    st.header("参数配置")
    
    # 资产类型选择
    asset_type = st.selectbox(
        "选择资产类型",
        ["stock", "future", "fund"],
        format_func=lambda x: {"stock": "股票", "future": "期货", "fund": "ETF"}[x]
    )
    
    # 代码输入
    code = st.text_input("输入代码", "000001.SZ")
    
    # 获取股票名称
    if code:
        stock_info = data_fetcher.get_stock_info(code)
        if stock_info is not None:
            st.info(f"股票名称: {stock_info['name']}")
            stock_name = stock_info['name']
        else:
            st.error("获取股票信息失败")
            st.stop()
    
    # 日期选择
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    date_range = st.date_input(
        "选择日期范围",
        value=(start_date, end_date),
        max_value=end_date
    )
    
    # EMA周期配置
    st.subheader("EMA参数")
    ema_short_period = st.number_input("短期EMA周期", min_value=1, max_value=50, value=8)
    ema_long_period = st.number_input("长期EMA周期", min_value=1, max_value=50, value=21)
    
    if ema_short_period >= ema_long_period:
        st.error("短期EMA周期必须小于长期EMA周期")
        st.stop()

    if len(date_range) == 2:
        start_date, end_date = date_range
        start_date = start_date.strftime("%Y%m%d")
        end_date = end_date.strftime("%Y%m%d")

# 主界面
if st.button("开始分析"):
    logger.info(f"开始分析: {code}, 时间范围: {start_date} - {end_date}")
    with st.spinner("正在获取数据..."):
        # 计算扩展的开始日期（往前推50天）
        start_date_dt = datetime.strptime(start_date, "%Y%m%d")
        extended_start_date = (start_date_dt - timedelta(days=60)).strftime("%Y%m%d")
        logger.info(f"扩展数据获取范围: {extended_start_date} - {end_date}")
        
        # 获取数据
        # df = data_fetcher.get_daily_data(code, extended_start_date, end_date, asset_type)
        df = data_fetcher.get_minute_data(
            code=code,
            start_date=start_date,
            end_date=end_date,
            freq="60min",
            save_dir="minute_data"
        )
        
        if df is None:
            logger.error("数据获取失败")
            st.error("获取数据失败，请检查代码和日期是否正确")
        else:
            logger.info(f"数据获取成功, 数据量: {len(df)}")
            # 计算技术指标
            indicators = TechnicalIndicators(df)
            df = indicators.calculate_all(ema_short_period, ema_long_period)
            
            # 只保留实际需要的时间范围的数据
            # 将df中的date列格式化为yyyymmdd格式再比较
            df['date_formatted'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
            df = df[df['date_formatted'] >= start_date]
            df = df.drop(columns=['date_formatted'])  # 删除临时列

            logger.info(f"数据量: {len(df)}, df: {df}")
            
            # 创建EMA分析器
            analyzer = EMAAnalyzer(df, ema_short_period, ema_long_period, stock_name=stock_name, stock_code=code)
            
            # 检测交叉点
            crossovers = analyzer.detect_crossovers()
            
            # 显示结果
            st.subheader("分析结果")
            
            # 创建结果表格
            results = []
            logger.info(f"交叉点数量: {len(crossovers)}， 其中金叉: {len([c for c in crossovers if c['type'] == 'golden_cross'])}， 死叉: {len([c for c in crossovers if c['type'] == 'death_cross'])}")
            for crossover in crossovers:
                # 获取LLM决策
                logger.info(f"获取{crossover['date']}的决策")
                decision = analyzer.get_trading_suggestion(crossover)
                
                results.append({
                    "日期": crossover["date"],
                    "类型": "金叉" if crossover["type"] == "golden_cross" else "死叉",
                    "收盘价": f"{crossover['indicators']['close']:.2f}",
                    f"EMA{ema_short_period}": f"{crossover['indicators']['EMA_short']:.2f}",
                    f"EMA{ema_long_period}": f"{crossover['indicators']['EMA_long']:.2f}",
                    "LLM决策": decision
                })
            
            # 显示结果表格
            if results:
                logger.info(f"分析完成，共{len(results)}个结果")
                st.dataframe(pd.DataFrame(results))
            else:
                logger.info("未检测到交叉点")
                st.info("在选定时间范围内没有检测到金叉或死叉")
            
            # 显示K线图
            st.subheader("K线图")
            fig = go.Figure()
            
            # 添加K线图
            fig.add_trace(go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='K线'
            ))
            
            # 添加均线
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['EMA_short'],
                name=f'EMA{ema_short_period}',
                line=dict(color='blue')
            ))
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['EMA_long'],
                name=f'EMA{ema_long_period}',
                line=dict(color='red')
            ))
            
            # 更新布局
            fig.update_layout(
                title=f"{code}价格走势和均线",
                xaxis_title="日期",
                yaxis_title="价格",
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True) 