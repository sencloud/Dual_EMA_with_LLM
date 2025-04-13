import tushare as ts
import pandas as pd
from typing import Optional, Tuple
from loguru import logger

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