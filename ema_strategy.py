import pandas as pd
import numpy as np
import talib
from pathlib import Path

class DualEMAStrategy:
    def __init__(self):
        # 基础参数
        self.short_ema_length = 13
        self.mid_ema_length = 25
        self.long_ema_length = 33
        self.sma200_length = 200
        self.atr_length = 14
        
        # 交易状态
        self.position = 0
        self.entry_price = 0
        self.atr_value = 0
        
    def calculate_indicators(self, df):
        # 计算EMA指标
        df['short_ema'] = talib.EMA(df['close'], timeperiod=self.short_ema_length)
        df['mid_ema'] = talib.EMA(df['close'], timeperiod=self.mid_ema_length)
        df['long_ema'] = talib.EMA(df['close'], timeperiod=self.long_ema_length)
        df['sma200'] = talib.SMA(df['close'], timeperiod=self.sma200_length)
        
        # 计算ATR
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=self.atr_length)
        
        # 计算OBV
        df['obv'] = talib.OBV(df['close'], df['vol'])
        df['obv_ma'] = talib.SMA(df['obv'], timeperiod=20)
        
        return df
    
    def generate_signals(self, df_15min, df_60min):
        # 对齐时间索引
        df_60min = df_60min.reindex(df_15min.index, method='ffill')
        
        # 60分钟趋势判断
        df_15min['h1_bull_market'] = df_60min['close'] > df_60min['sma200']
        df_15min['h1_bear_market'] = df_60min['close'] < df_60min['sma200']
        
        # 15分钟EMA三线共振
        df_15min['ema_up_trend'] = (
            (df_15min['short_ema'] > df_15min['mid_ema']) & 
            (df_15min['mid_ema'] > df_15min['long_ema']) &
            (df_15min['short_ema'].diff() > 0) &
            (df_15min['mid_ema'].diff() > 0) &
            (df_15min['long_ema'].diff() > 0)
        )
        
        df_15min['ema_down_trend'] = (
            (df_15min['short_ema'] < df_15min['mid_ema']) & 
            (df_15min['mid_ema'] < df_15min['long_ema']) &
            (df_15min['short_ema'].diff() < 0) &
            (df_15min['mid_ema'].diff() < 0) &
            (df_15min['long_ema'].diff() < 0)
        )
        
        # 生成交易信号
        df_15min['long_signal'] = (
            df_15min['h1_bull_market'] & 
            df_15min['ema_up_trend'] & 
            (df_15min['obv'] > df_15min['obv_ma'])
        )
        
        df_15min['short_signal'] = (
            df_15min['h1_bear_market'] & 
            df_15min['ema_down_trend'] & 
            (df_15min['obv'] < df_15min['obv_ma'])
        )
        
        return df_15min
    
    def run_strategy(self, df_15min, df_60min):
        df_15min = self.calculate_indicators(df_15min)
        df_60min = self.calculate_indicators(df_60min)
        df_15min = self.generate_signals(df_15min, df_60min)
        
        positions = []
        trades = []
        
        for i in range(len(df_15min)):
            current_bar = df_15min.iloc[i]
            
            # ATR止盈止损设置
            if self.position != 0:
                atr = self.atr_value
                if self.position > 0:
                    profit_level = self.entry_price + (atr * 3.0)
                    stop_loss = self.entry_price - (atr * 2.5)
                    
                    if current_bar['high'] >= profit_level or current_bar['low'] <= stop_loss:
                        trades.append({
                            'entry_time': self.entry_time,
                            'exit_time': current_bar.name,
                            'type': 'LONG',
                            'entry_price': self.entry_price,
                            'exit_price': current_bar['close'],
                            'pnl': current_bar['close'] - self.entry_price,
                            'exit_type': '止盈' if current_bar['high'] >= profit_level else '止损'
                        })
                        self.position = 0
                
                else:  # short position
                    profit_level = self.entry_price - (atr * 3.0)
                    stop_loss = self.entry_price + (atr * 2.5)
                    
                    if current_bar['low'] <= profit_level or current_bar['high'] >= stop_loss:
                        trades.append({
                            'entry_time': self.entry_time,
                            'exit_time': current_bar.name,
                            'type': 'SHORT',
                            'entry_price': self.entry_price,
                            'exit_price': current_bar['close'],
                            'pnl': self.entry_price - current_bar['close'],
                            'exit_type': '止盈' if current_bar['low'] <= profit_level else '止损'
                        })
                        self.position = 0
            
            # 开仓信号
            if self.position == 0:
                if current_bar['long_signal']:
                    self.position = 1
                    self.entry_price = current_bar['close']
                    self.entry_time = current_bar.name
                    self.atr_value = current_bar['atr']
                
                elif current_bar['short_signal']:
                    self.position = -1
                    self.entry_price = current_bar['close']
                    self.entry_time = current_bar.name
                    self.atr_value = current_bar['atr']
            
            positions.append(self.position)
        
        df_15min['position'] = positions
        return df_15min, pd.DataFrame(trades)

def load_and_process_data(file_path):
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

def main():
    # 加载数据
    data_dir = Path('minute_data')
    df_15min = load_and_process_data(data_dir / 'RB2505.SHF_future_15min_20240101_20251231.csv')
    df_60min = load_and_process_data(data_dir / 'RB2505.SHF_future_60min_20240101_20251231.csv')
    
    # 运行策略
    strategy = DualEMAStrategy()
    results_15min, trades_15min = strategy.run_strategy(df_15min, df_60min)
    
    # 输出交易统计
    print("\n15分钟周期交易统计:")
    print(f"总交易次数: {len(trades_15min)}")
    if len(trades_15min) > 0:
        print(f"平均收益: {trades_15min['pnl'].mean():.2f}")
        print(f"胜率: {(trades_15min['pnl'] > 0).mean():.2%}")
        print(f"最大收益: {trades_15min['pnl'].max():.2f}")
        print(f"最大亏损: {trades_15min['pnl'].min():.2f}")
        
        # 打印交易明细
        print("\n交易明细:")
        print("序号  开仓时间              平仓时间              方向    开仓价    平仓价    盈亏     平仓类型")
        print("-" * 95)
        for idx, trade in trades_15min.iterrows():
            print(f"{idx+1:3d}  {trade['entry_time']:%Y-%m-%d %H:%M}  {trade['exit_time']:%Y-%m-%d %H:%M}  {'做多' if trade['type']=='LONG' else '做空'}  {trade['entry_price']:8.2f}  {trade['exit_price']:8.2f}  {trade['pnl']:8.2f}  {trade['exit_type']}")
        
        # 计算连续盈亏
        trades_15min['is_profit'] = trades_15min['pnl'] > 0
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_streak = 0
        
        for is_profit in trades_15min['is_profit']:
            if is_profit:
                if current_streak > 0:
                    current_streak += 1
                else:
                    current_streak = 1
                max_consecutive_wins = max(max_consecutive_wins, current_streak)
            else:
                if current_streak < 0:
                    current_streak -= 1
                else:
                    current_streak = -1
                max_consecutive_losses = min(max_consecutive_losses, current_streak)
        
        print(f"\n最大连续盈利次数: {max_consecutive_wins}")
        print(f"最大连续亏损次数: {abs(max_consecutive_losses)}")
        
        # 计算月度收益
        trades_15min['month'] = trades_15min['exit_time'].dt.to_period('M')
        monthly_pnl = trades_15min.groupby('month')['pnl'].sum()
        
        print("\n月度收益:")
        for month, pnl in monthly_pnl.items():
            print(f"{month}: {pnl:8.2f}")

if __name__ == "__main__":
    main() 