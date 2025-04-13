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
    
    def __init__(self, df: pd.DataFrame, ema_short_period: int = 5, ema_long_period: int = 8):
        """初始化EMA分析器
        
        Args:
            df: 包含EMA数据的DataFrame
            ema_short_period: 短期EMA周期
            ema_long_period: 长期EMA周期
        """
        self.df = df.copy()
        self.ema_short_period = ema_short_period
        self.ema_long_period = ema_long_period
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
            support_levels, resistance_levels = self.find_support_resistance()
            
            crossovers.append({
                'date': df.loc[idx, 'date'],
                'type': 'golden_cross' if df.loc[idx, 'crossover'] == 1 else 'death_cross',
                'indicators': {
                    'close': df.loc[idx, 'close'],
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
                }
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
    
    def find_support_resistance(self, window: int = 20) -> Tuple[List[float], List[float]]:
        """寻找支撑位和阻力位
        
        Args:
            window: 寻找局部极值的窗口大小
            
        Returns:
            支撑位和阻力位列表
        """
        # 使用EMA交叉点作为潜在的支撑/阻力位
        cross_points = self.find_ema_crossovers()
        
        # 在交叉点附近寻找局部极值
        support_levels = []
        resistance_levels = []
        
        for point in cross_points:
            start_idx = max(0, point - window)
            end_idx = min(len(self.df), point + window)
            window_data = self.df.iloc[start_idx:end_idx]
            
            # 寻找局部最小值作为支撑位
            if window_data['low'].min() == window_data['low'].iloc[window//2]:
                support_levels.append(window_data['low'].min())
                
            # 寻找局部最大值作为阻力位
            if window_data['high'].max() == window_data['high'].iloc[window//2]:
                resistance_levels.append(window_data['high'].max())
                
        return support_levels, resistance_levels
        
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
        
        # 获取前一交易日的支撑位和压力位
        prev_support_levels = crossover.get('prev_support_levels', [])
        prev_resistance_levels = crossover.get('prev_resistance_levels', [])
        
        # 格式化支撑位和压力位
        support_str = ", ".join([f"{level:.2f}" for level in prev_support_levels]) if prev_support_levels else "无数据"
        resistance_str = ", ".join([f"{level:.2f}" for level in prev_resistance_levels]) if prev_resistance_levels else "无数据"
        
        return f"""
        在{crossover['date']}出现了EMA双均线{cross_type}，当前技术指标如下：
        
        收盘价: {indicators['close']:.2f}
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
        
        前一交易日支撑位: {support_str}
        前一交易日压力位: {resistance_str}
        
        基于以上技术指标，请分析是否应该开仓，并给出具体理由。
        请用中文回答，并给出明确的"建议开仓"、"建议不开仓"的结论。
        """ 