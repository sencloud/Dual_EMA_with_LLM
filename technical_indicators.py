import talib
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from loguru import logger

class TechnicalIndicators:
    """技术指标计算类"""
    
    def __init__(self, df: pd.DataFrame):
        """初始化技术指标计算器
        
        Args:
            df: 包含OHLCV数据的DataFrame
        """
        self.df = df.copy()
        
    def calculate_ema(self, period: int, column: str = 'close') -> pd.Series:
        """计算EMA
        
        Args:
            period: EMA周期
            column: 用于计算的列名
            
        Returns:
            EMA序列
        """
        return self.df[column].ewm(span=period, adjust=False).mean()
        
    def calculate_all(self, ema_short_period: int = 5, ema_long_period: int = 8) -> pd.DataFrame:
        """计算所有技术指标
        
        Args:
            ema_short_period: 短期EMA周期
            ema_long_period: 长期EMA周期
            
        Returns:
            包含所有技术指标的DataFrame
        """
        logger.info("开始计算技术指标")
        # 确保数据格式正确
        self.df['close'] = self.df['close'].astype(float)
        self.df['high'] = self.df['high'].astype(float)
        self.df['low'] = self.df['low'].astype(float)
        self.df['open'] = self.df['open'].astype(float)
        self.df['vol'] = self.df['vol'].astype(float)
        
        # 计算EMA
        logger.debug(f"计算EMA指标: 短期={ema_short_period}, 长期={ema_long_period}")
        self.df['EMA_short'] = self.calculate_ema(ema_short_period)
        self.df['EMA_long'] = self.calculate_ema(ema_long_period)
        
        # 计算MACD
        logger.debug("计算MACD指标")
        self.df['MACD'], self.df['MACD_signal'], self.df['MACD_hist'] = self.calculate_macd()
        
        # 计算RSI
        logger.debug("计算RSI指标")
        self.df['RSI'] = self.calculate_rsi()
        
        # 计算布林带
        logger.debug("计算布林带指标")
        self.df['bb_middle'], self.df['bb_upper'], self.df['bb_lower'] = self.calculate_bollinger_bands(self.df['close'])
        
        # 计算KDJ
        logger.debug("计算KDJ指标")
        self.df['k'], self.df['d'], self.df['j'] = self.calculate_kdj(self.df['high'], self.df['low'], self.df['close'])
        
        # 计算成交量指标
        logger.debug("计算OBV指标")
        self.df['obv'] = talib.OBV(self.df['close'], self.df['vol'])
        
        # 计算ATR
        logger.debug("计算ATR指标")
        self.df['atr'] = talib.ATR(self.df['high'], self.df['low'], self.df['close'])
        
        # 计算压力位和支撑位
        logger.debug("计算压力位和支撑位")
        self.df['support_levels'] = None
        self.df['resistance_levels'] = None
        
        # 为每个数据点计算压力位和支撑位
        for i in range(len(self.df)):
            if i >= 34:  # 确保有足够的数据计算
                support_levels, resistance_levels = self.find_key_levels(
                    self.df.iloc[i-34:i+1]
                )
                # 将numpy数组转换为列表
                self.df.at[i, 'support_levels'] = support_levels.tolist() if isinstance(support_levels, np.ndarray) else support_levels
                self.df.at[i, 'resistance_levels'] = resistance_levels.tolist() if isinstance(resistance_levels, np.ndarray) else resistance_levels
        
        logger.info("技术指标计算完成")
        return self.df
    
    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """计算RSI
        
        Args:
            period: RSI周期
            
        Returns:
            RSI序列
        """
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
        
    def calculate_macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD
        
        Args:
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            MACD线、信号线和柱状图
        """
        exp1 = self.df['close'].ewm(span=fast_period, adjust=False).mean()
        exp2 = self.df['close'].ewm(span=slow_period, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
        
    def calculate_kdj(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                     n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算KDJ
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            n: RSV周期
            m1: K值平滑系数
            m2: D值平滑系数
            
        Returns:
            (K值, D值, J值)
        """
        low_list = low.rolling(window=n, min_periods=n).min()
        high_list = high.rolling(window=n, min_periods=n).max()
        
        rsv = (close - low_list) / (high_list - low_list) * 100
        
        k = pd.DataFrame(rsv).ewm(com=m1-1, adjust=True, min_periods=n).mean()
        d = k.ewm(com=m2-1, adjust=True, min_periods=n).mean()
        j = 3 * k - 2 * d
        
        return k[0], d[0], j[0]
        
    def calculate_bollinger_bands(self, data: pd.Series, period: int = 20, 
                                std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带
        
        Args:
            data: 价格数据
            period: 移动平均周期
            std_dev: 标准差倍数
            
        Returns:
            (中轨, 上轨, 下轨)
        """
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return middle, upper, lower
    
    def get_indicators_at_point(self, index: int) -> Dict[str, Any]:
        """获取某个时间点的所有技术指标
        
        Args:
            index: 数据点索引
            
        Returns:
            技术指标字典
        """
        logger.debug(f"获取第{index}个数据点的技术指标")
        point = self.df.iloc[index]
        
        # 获取支撑位和压力位
        support_levels = point['support_levels']
        resistance_levels = point['resistance_levels']
        
        # 处理None值
        if support_levels is None:
            support_levels = []
        elif isinstance(support_levels, np.ndarray):
            support_levels = support_levels.tolist()
            
        if resistance_levels is None:
            resistance_levels = []
        elif isinstance(resistance_levels, np.ndarray):
            resistance_levels = resistance_levels.tolist()
        
        return {
            'close': point['close'],
            'vol': point['vol'],
            'EMA_short': point['EMA_short'],
            'EMA_long': point['EMA_long'],
            'MACD': point['MACD'],
            'MACD_signal': point['MACD_signal'],
            'MACD_hist': point['MACD_hist'],
            'RSI': point['RSI'],
            'bb_upper': point['bb_upper'],
            'bb_middle': point['bb_middle'],
            'bb_lower': point['bb_lower'],
            'k': point['k'],
            'd': point['d'],
            'j': point['j'],
            'obv': point['obv'],
            'atr': point['atr'],
            'support_levels': support_levels,
            'resistance_levels': resistance_levels
        }
        
    def find_key_levels(self, df: pd.DataFrame, lookback: int = 34) -> Tuple[List[float], List[float]]:
        """计算压力位和支撑位
        
        Args:
            df: 包含OHLCV数据的DataFrame
            lookback: 回看周期
            
        Returns:
            (支撑位列表, 压力位列表)
        """
        logger.debug(f"计算压力位和支撑位，回看周期: {lookback}")
        
        # 确保数据足够
        if len(df) < lookback:
            logger.warning(f"数据量不足{lookback}条，无法计算压力位和支撑位")
            return [], []
            
        # 获取最近lookback周期的数据
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # 计算ATR
        atr = talib.ATR(high, low, close, 14)[-1]
        
        # 计算PP（中枢点）
        pp = (high.max() + low.min() + close[-1]) / 3
        
        # 计算R1和S1
        r1 = 2 * pp - low.min()
        s1 = 2 * pp - high.max()
        
        # 计算支撑位和压力位
        support_levels = np.array([s1 - 0.5 * atr, pp - atr])
        resistance_levels = np.array([r1 + 0.5 * atr, pp + atr])
        
        logger.debug(f"支撑位: {support_levels}, 压力位: {resistance_levels}")
        return support_levels, resistance_levels 