import tushare as ts
import pandas as pd
from typing import Optional, Tuple, Dict
from loguru import logger
import os

class DataFetcher:
    """数据获取类"""
    
    def __init__(self, token: str):
        """初始化
        
        Args:
            token: tushare token
        """
        logger.info("初始化数据获取器")
        ts.set_token(token)
        self.pro = ts.pro_api()
        
    def get_daily_data(
        self,
        code: str,
        start_date: str,
        end_date: str,
        asset_type: str = "stock"
    ) -> Optional[pd.DataFrame]:
        """获取日线数据
        
        Args:
            code: 证券代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            asset_type: 资产类型，可选：stock/future/fund
            
        Returns:
            日线数据DataFrame
        """
        logger.info(f"开始获取{asset_type}数据: {code}, 时间范围: {start_date} - {end_date}")
        try:
            if asset_type == "stock":
                logger.debug("获取股票日线数据")
                df = self.pro.daily(ts_code=code, start_date=start_date, end_date=end_date)
            elif asset_type == "future":
                logger.debug("获取期货日线数据")
                df = self.pro.fut_daily(ts_code=code, start_date=start_date, end_date=end_date)
            elif asset_type == "fund":
                logger.debug("获取ETF日线数据")
                df = self.pro.fund_daily(ts_code=code, start_date=start_date, end_date=end_date)
            else:
                logger.error(f"不支持的资产类型: {asset_type}")
                raise ValueError(f"Unsupported asset type: {asset_type}")
                
            # 统一日期列名为date
            if "trade_date" in df.columns:
                df = df.rename(columns={"trade_date": "date"})

            # 按日期升序排序
            df = df.sort_values("date")
            
            logger.info(f"成功获取数据，共{len(df)}条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取数据失败: {str(e)}")
            return None 

    def get_stock_info(self, code: str) -> Optional[Dict]:
        """获取股票基本信息
        
        Args:
            code: 股票代码
            
        Returns:
            股票基本信息字典
        """
        logger.info(f"获取股票基本信息: {code}")
        try:
            # 获取股票基本信息
            df = self.pro.stock_basic(ts_code=code, fields='ts_code,name,area,industry')
            if len(df) > 0:
                return df.iloc[0].to_dict()
            else:
                logger.warning(f"未找到股票信息: {code}")
                return None
        except Exception as e:
            logger.error(f"获取股票信息失败: {str(e)}")
            return None 

    def get_minute_data(
        self,
        code: str,
        start_date: str,
        end_date: str,
        freq: str = '60min',
        save_dir: str = 'minute_data',
        asset_type: str = "stock"
    ) -> Optional[pd.DataFrame]:
        """获取分钟级数据并保存到csv
        
        Args:
            code: 证券代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            freq: 频率，可选：1min/5min/15min/30min/60min
            save_dir: 保存目录
            asset_type: 资产类型，可选：stock/future/fund
            
        Returns:
            DataFrame数据，获取失败返回None
        """
        logger.info(f"开始获取{asset_type}分钟数据: {code}, 频率: {freq}, 时间范围: {start_date} - {end_date}")
        try:
            # 创建保存目录
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # 检查是否存在已有文件
            filename = f"{code}_{asset_type}_{freq}_{start_date}_{end_date}.csv"
            filepath = os.path.join(save_dir, filename)
            if os.path.exists(filepath):
                logger.info(f"找到已存在的数据文件: {filename}")
                return pd.read_csv(filepath)
                
            # 根据资产类型获取分钟数据
            if asset_type == "stock":
                logger.debug("获取股票分钟数据")
                df = self.pro.pro_bar(ts_code=code, start_date=start_date, end_date=end_date, freq=freq)
            elif asset_type == "future":
                logger.debug("获取期货分钟数据")
                df = self.pro.ft_mins(ts_code=code, start_date=start_date, end_date=end_date, freq=freq)
            elif asset_type == "fund":
                logger.debug("获取ETF分钟数据")
                df = self.pro.pro_bar(ts_code=code, start_date=start_date, end_date=end_date, freq=freq, asset="FD")
            else:
                logger.error(f"不支持的资产类型: {asset_type}")
                return None
            
            if df is None or len(df) == 0:
                logger.warning(f"未获取到数据")
                return None
                
            # 统一日期列名
            if "trade_time" in df.columns:
                df = df.rename(columns={"trade_time": "date"})
                
            # 按时间升序排序
            df = df.sort_values("date")
            
            # 保存到csv
            df.to_csv(filepath, index=False)
            logger.info(f"成功保存{len(df)}条记录到: {filepath}")
            return df
            
        except Exception as e:
            logger.error(f"获取或保存分钟数据失败: {str(e)}")
            return None

if __name__ == "__main__":
    from config import TUSHARE_TOKEN
    
    # 初始化数据获取器
    fetcher = DataFetcher(TUSHARE_TOKEN)
    
    # 测试参数
    code = "RB2505.SHF"
    start_date = "20240101"
    end_date = "20251231"
    freq = "15min"
    save_dir = "minute_data"
    asset_type = "future"
    
    # 获取并保存分钟数据
    df = fetcher.get_minute_data(
        code=code,
        start_date=start_date,
        end_date=end_date,
        freq=freq,
        save_dir=save_dir,
        asset_type=asset_type
    )
    
    logger.info("数据获取并保存成功")