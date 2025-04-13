import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from deepseek_client import DeepSeekClient
from technical_indicators import TechnicalIndicators
from loguru import logger
from datetime import datetime
import asyncio

class EMAAnalyzer:
    """双均线分析类"""
    
    def __init__(self, df: pd.DataFrame, ema_short_period: int = 5, ema_long_period: int = 8, stock_name: str = "", stock_code: str = ""):
        """初始化EMA分析器
        
        Args:
            df: 包含EMA数据的DataFrame
            ema_short_period: 短期EMA周期
            ema_long_period: 长期EMA周期
            stock_name: 股票名称
            stock_code: 股票代码
        """
        self.df = df.copy()
        self.ema_short_period = ema_short_period
        self.ema_long_period = ema_long_period
        self.stock_name = stock_name
        self.stock_code = stock_code
        self.deepseek = DeepSeekClient()
        
    def detect_crossovers(self) -> List[Dict]:
        """检测EMA金叉和死叉
        
        Returns:
            包含金叉死叉信号的列表
        """
        df = self.df.copy()
        
        # 计算EMA差值
        df['ema_diff'] = df['EMA_short'] - df['EMA_long']
        
        # 检测金叉和死叉
        df['crossover'] = 0
        df.loc[(df['ema_diff'] > 0) & (df['ema_diff'].shift(1) <= 0), 'crossover'] = 1  # 金叉
        df.loc[(df['ema_diff'] < 0) & (df['ema_diff'].shift(1) >= 0), 'crossover'] = -1  # 死叉
        
        # 获取交叉点
        crossovers = []
        for idx in df[df['crossover'] != 0].index:
            # 获取支撑位和压力位
            support_levels, resistance_levels = self.find_support_resistance(current_idx=idx)
            
            # 获取过去5个交易日的数据
            prev_5_days = []
            # 确保 DataFrame 按日期排序
            df_sorted = df.sort_values('date')  # 按日期升序排序
            # 找到当前日期在排序后DataFrame中的位置
            current_idx = df_sorted[df_sorted['date'] == df.loc[idx, 'date']].index[0]
            # 获取当前日期之前的5个交易日数据
            start_idx = max(0, df_sorted.index.get_loc(current_idx) - 5)
            end_idx = df_sorted.index.get_loc(current_idx)
            prev_rows = df_sorted.iloc[start_idx:end_idx]
            
            for _, row in prev_rows.iterrows():
                prev_5_days.append({
                    'date': row['date'],
                    'close': row['close'],
                    'change': row['pct_chg'],
                    'vol': row['vol'],
                    'EMA_short': row['EMA_short'],
                    'EMA_long': row['EMA_long']
                })
            
            crossovers.append({
                'date': df.loc[idx, 'date'],
                'type': 'golden_cross' if df.loc[idx, 'crossover'] == 1 else 'death_cross',
                'indicators': {
                    'close': df.loc[idx, 'close'],
                    'change': df.loc[idx, 'pct_chg'],
                    'vol': df.loc[idx, 'vol'],
                    'EMA_short': df.loc[idx, 'EMA_short'],
                    'EMA_long': df.loc[idx, 'EMA_long'],
                    'RSI': df.loc[idx, 'RSI'],
                    'MACD': df.loc[idx, 'MACD'],
                    'MACD_signal': df.loc[idx, 'MACD_signal'],
                    'MACD_hist': df.loc[idx, 'MACD_hist'],
                    'k': df.loc[idx, 'k'],
                    'd': df.loc[idx, 'd'],
                    'j': df.loc[idx, 'j'],
                    'obv': df.loc[idx, 'obv'],
                    'atr': df.loc[idx, 'atr'],
                    'bb_upper': df.loc[idx, 'bb_upper'],
                    'bb_middle': df.loc[idx, 'bb_middle'],
                    'bb_lower': df.loc[idx, 'bb_lower'],
                    'support_levels': support_levels,
                    'resistance_levels': resistance_levels
                },
                'prev_5_days': prev_5_days
            })
        
        return crossovers
    
    def analyze_trend(self, window: int = 20) -> pd.DataFrame:
        """分析EMA趋势
        
        Args:
            window: 趋势判断窗口
            
        Returns:
            包含趋势分析的DataFrame
        """
        df = self.df.copy()
        
        # 计算EMA斜率
        df['ema_short_slope'] = df['EMA_short'].diff(window) / window
        df['ema_long_slope'] = df['EMA_long'].diff(window) / window
        
        # 判断趋势
        df['trend'] = 0
        df.loc[(df['ema_short_slope'] > 0) & (df['ema_long_slope'] > 0), 'trend'] = 1  # 上升趋势
        df.loc[(df['ema_short_slope'] < 0) & (df['ema_long_slope'] < 0), 'trend'] = -1  # 下降趋势
        
        return df
    
    def find_support_resistance(self, current_idx: Optional[int] = None, window: int = 20) -> Tuple[List[float], List[float]]:
        """寻找支撑位和阻力位
        
        Args:
            current_idx: 当前交叉点的索引
            window: 寻找局部极值的窗口大小
            
        Returns:
            支撑位和阻力位列表（包含5天平均值）
        """
        logger.debug(f"开始查找支撑位和压力位, current_idx: {current_idx}")
        
        # 从DataFrame中获取支撑位和压力位
        if current_idx is not None and current_idx < len(self.df):
            row = self.df.iloc[current_idx]
            logger.debug(f"当前行数据: {row.to_dict()}")
            logger.debug(f"support_levels类型: {type(row['support_levels'])}, 值: {row['support_levels']}")
            logger.debug(f"resistance_levels类型: {type(row['resistance_levels'])}, 值: {row['resistance_levels']}")
            
            # 获取过去5天的支撑位和压力位
            past_5_days_support = []
            past_5_days_resistance = []
            
            # 确保DataFrame按日期排序
            df_sorted = self.df.sort_values('date')
            current_date = row['date']
            current_sorted_idx = df_sorted[df_sorted['date'] == current_date].index[0]
            start_idx = max(0, df_sorted.index.get_loc(current_sorted_idx) - 4)  # 获取前4天（加上当天共5天）
            past_5_days = df_sorted.iloc[start_idx:df_sorted.index.get_loc(current_sorted_idx) + 1]
            
            logger.debug(f"过去5天日期: {past_5_days['date'].tolist()}")
            
            # 收集过去5天的支撑位和压力位
            for _, past_row in past_5_days.iterrows():
                if isinstance(past_row['support_levels'], list) and len(past_row['support_levels']) >= 2:
                    past_5_days_support.append(past_row['support_levels'])
                if isinstance(past_row['resistance_levels'], list) and len(past_row['resistance_levels']) >= 2:
                    past_5_days_resistance.append(past_row['resistance_levels'])
            
            logger.debug(f"过去5天支撑位: {past_5_days_support}")
            logger.debug(f"过去5天压力位: {past_5_days_resistance}")
            
            # 计算平均值
            avg_strong_support = np.mean([levels[0] for levels in past_5_days_support]) if past_5_days_support else None
            avg_support = np.mean([levels[1] for levels in past_5_days_support]) if past_5_days_support else None
            avg_strong_resistance = np.mean([levels[0] for levels in past_5_days_resistance]) if past_5_days_resistance else None
            avg_resistance = np.mean([levels[1] for levels in past_5_days_resistance]) if past_5_days_resistance else None
            
            # 构建返回结果
            support_levels = [avg_strong_support, avg_support] if avg_strong_support is not None and avg_support is not None else []
            resistance_levels = [avg_strong_resistance, avg_resistance] if avg_strong_resistance is not None and avg_resistance is not None else []
            
            logger.debug(f"5天平均支撑位: {support_levels}")
            logger.debug(f"5天平均压力位: {resistance_levels}")
            
            return support_levels, resistance_levels
        
        logger.debug("current_idx无效，返回空列表")
        return [], []
        
    def find_ema_crossovers(self) -> List[int]:
        """寻找EMA交叉点
        
        Returns:
            交叉点的索引列表
        """
        crossovers = []
        
        # 计算EMA的差值
        ema_diff = self.df['EMA_short'] - self.df['EMA_long']
        
        # 寻找交叉点
        for i in range(1, len(ema_diff)):
            if (ema_diff.iloc[i-1] < 0 and ema_diff.iloc[i] > 0) or \
               (ema_diff.iloc[i-1] > 0 and ema_diff.iloc[i] < 0):
                crossovers.append(i)
                
        return crossovers
        
    def generate_signals(self) -> pd.DataFrame:
        """生成交易信号
        
        Returns:
            包含交易信号的DataFrame
        """
        signals = pd.DataFrame(index=self.df.index)
        signals['signal'] = 0
        
        # 计算EMA的差值
        ema_diff = self.df['EMA_short'] - self.df['EMA_long']
        
        # 生成买入信号
        signals.loc[ema_diff > 0, 'signal'] = 1
        
        # 生成卖出信号
        signals.loc[ema_diff < 0, 'signal'] = -1
        
        return signals
    
    def get_signals(self) -> Dict[str, List[Dict]]:
        """获取交易信号
        
        Returns:
            包含交易信号的字典
        """
        df = self.df.copy()
        
        signals = {
            'buy': [],
            'sell': []
        }
        
        # 获取金叉和死叉信号
        crossovers = df[df['crossover'] != 0]
        
        for idx in crossovers.index:
            signal = {
                'date': idx,
                'price': df.loc[idx, 'Close'],
                'ema_short': df.loc[idx, 'EMA_short'],
                'ema_long': df.loc[idx, 'EMA_long']
            }
            
            if df.loc[idx, 'crossover'] == 1:  # 金叉
                signals['buy'].append(signal)
            else:  # 死叉
                signals['sell'].append(signal)
                
        return signals
    
    def get_trading_suggestion(self, crossover: Dict) -> str:
        """获取交易建议
        
        Args:
            crossover: 交叉点信息
            
        Returns:
            交易建议
        """
        cross_type = "金叉" if crossover['type'] == 'golden_cross' else "死叉"
        # 构建提示词
        prompt = self._build_prompt(crossover)
        logger.info(f"获取交易建议: {crossover['date']} EMA均线{cross_type} 技术指标: {prompt}")
        
        # 调用LLM获取建议
        try:
            response = asyncio.run(self.deepseek.chat_completion([
                {"role": "system", "content": "你是一个专业的量化交易分析师，请根据技术指标给出交易建议。"},
                {"role": "user", "content": prompt}
            ]))
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"获取LLM建议失败: {str(e)}")
            return "获取建议失败，请稍后重试"
            
    def _build_prompt(self, crossover: Dict) -> str:
        """构建提示词
        
        Args:
            crossover: 交叉点信息
            
        Returns:
            提示词
        """
        logger.debug("构建LLM提示词")
        indicators = crossover['indicators']
        cross_type = "金叉" if crossover['type'] == 'golden_cross' else "死叉"
        
        # 从indicators中获取支撑位和压力位
        support_levels = indicators.get('support_levels', [])
        resistance_levels = indicators.get('resistance_levels', [])
        
        # 格式化支撑位和压力位
        support_str = f"强支撑位: {support_levels[0]:.2f}, 支撑位: {support_levels[1]:.2f}" if len(support_levels) >= 2 else "无数据"
        resistance_str = f"强压力位: {resistance_levels[0]:.2f}, 压力位: {resistance_levels[1]:.2f}" if len(resistance_levels) >= 2 else "无数据"
        
        # 格式化过去5个交易日的数据
        prev_5_days_str = ""
        if 'prev_5_days' in crossover and crossover['prev_5_days']:
            prev_5_days_str = "\n过去5个交易日的基本情况：\n"
            for i, day in enumerate(crossover['prev_5_days'], 1):
                prev_5_days_str += f"第{i}天 ({day['date']}): 收盘价 {day['close']:.2f}, 成交量 {day['vol']:.2f}, EMA短期 {day['EMA_short']:.2f}, EMA长期 {day['EMA_long']:.2f}, 涨跌幅 {day['change']:.2f}%\n"
        
        return f"""
        {f'股票: {self.stock_name}({self.stock_code})' if self.stock_name and self.stock_code else ''}
        在{crossover['date']}出现了EMA双均线{cross_type}，当前技术指标如下：
        
        收盘价: {indicators['close']:.2f}
        涨跌幅: {indicators['change']:.2f}%
        成交量: {indicators['vol']:.2f}
        EMA短期: {indicators['EMA_short']:.2f}
        EMA长期: {indicators['EMA_long']:.2f}
        MACD: {indicators['MACD']:.2f}
        MACD信号线: {indicators['MACD_signal']:.2f}
        MACD柱状: {indicators['MACD_hist']:.2f}
        RSI: {indicators['RSI']:.2f}
        布林带上轨: {indicators['bb_upper']:.2f}
        布林带中轨: {indicators['bb_middle']:.2f}
        布林带下轨: {indicators['bb_lower']:.2f}
        KDJ-K: {indicators['k']:.2f}
        KDJ-D: {indicators['d']:.2f}
        KDJ-J: {indicators['j']:.2f}
        OBV: {indicators['obv']:.2f}
        ATR: {indicators['atr']:.2f}
        
        {support_str}
        {resistance_str}
        {prev_5_days_str}
        基于以上技术指标，请分析是否应该开仓，并给出具体理由。
        请用中文回答，并给出明确的"建议开仓"、"建议不开仓"的结论。
        """ 