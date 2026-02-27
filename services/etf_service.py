"""ETF 实时行情服务"""
from datetime import datetime, date, time as dt_time
from typing import Optional, List, Dict
import logging
import re
import asyncio
from threading import Lock

logger = logging.getLogger(__name__)


class ETFCache:
    """ETF 数据缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}  # {etf_code: {data, timestamp, type}}
        self._lock = Lock()
        
        # 缓存有效期配置（秒）- 统一使用 30 分钟
        self.CACHE_TTL = 1800  # 30 分钟
    
    def get(self, etf_code: str, data_type: str = 'realtime') -> Optional[dict]:
        """获取缓存数据"""
        with self._lock:
            key = f"{etf_code}_{data_type}"
            if key not in self._cache:
                return None
            
            cached = self._cache[key]
            now = datetime.now()
            age = (now - cached['timestamp']).total_seconds()
            
            if age < self.CACHE_TTL:
                logger.debug(f"缓存命中: {key}, 年龄: {age:.0f}秒")
                # 返回数据时添加缓存时间戳
                result = cached['data'].copy()
                result['cached_at'] = cached['timestamp'].isoformat()
                return result
            
            return None
    
    def set(self, etf_code: str, data: dict, data_type: str = 'realtime'):
        """设置缓存数据"""
        with self._lock:
            key = f"{etf_code}_{data_type}"
            self._cache[key] = {
                'data': data,
                'timestamp': datetime.now(),
                'type': data_type
            }
            logger.debug(f"缓存已更新: {key}")
    
    def get_cache_time(self, etf_code: str, data_type: str = 'realtime') -> Optional[datetime]:
        """获取缓存时间"""
        with self._lock:
            key = f"{etf_code}_{data_type}"
            if key in self._cache:
                return self._cache[key]['timestamp']
            return None


# 全局缓存实例
etf_cache = ETFCache()


class ETFService:
    """ETF 实时行情服务"""
    
    # 常见行业 ETF 映射（基金类型 -> ETF 代码列表）
    ETF_MAPPING = {
        "新能源车": ["515030", "516390", "159806"],
        "新能源汽车": ["515030", "516390"],
        "光伏": ["515790", "159863"],
        "新能源": ["516160", "516850"],
        "医药": ["512010", "159938", "512170"],
        "医疗": ["512170", "159928"],
        "白酒": ["512690"],
        "消费": ["159928", "512200"],
        "半导体": ["512480", "512760"],
        "芯片": ["512480", "512760", "159995"],
        "军工": ["512660", "512810"],
        "证券": ["512880", "159841"],
        "银行": ["512800", "159886"],
        "地产": ["512200", "159940"],
        "科技": ["515000", "159801"],
        "互联网": ["515050", "159607"],
        "人工智能": ["515070", "159819"],
        "机器人": ["159770", "562500"],
        "有色": ["512400", "159980"],
        "煤炭": ["515220", "159898"],
        "钢铁": ["515210", "159897"],
        "化工": ["159870", "159801"],
        "环保": ["159861", "512580"],
        "基建": ["159616", "516970"],
        "传媒": ["512980", "159805"],
        "游戏": ["159869", "515030"],
        "教育": ["516360"],
        "旅游": ["159766"],
        "养殖": ["159865"],
        "农业": ["159825", "516280"],
    }
    
    @staticmethod
    def get_recommended_etfs(fund_type: str) -> List[str]:
        """根据基金类型推荐关联 ETF"""
        if not fund_type:
            return []
        
        # 直接匹配
        if fund_type in ETFService.ETF_MAPPING:
            return ETFService.ETF_MAPPING[fund_type]
        
        # 模糊匹配
        for key, etfs in ETFService.ETF_MAPPING.items():
            if key in fund_type or fund_type in key:
                return etfs
        
        return []
    
    @staticmethod
    def _get_market_prefix(etf_code: str) -> str:
        """获取市场前缀"""
        if etf_code.startswith('5'):
            return 'sh'  # 上海
        else:
            return 'sz'  # 深圳
    
    @staticmethod
    async def get_etf_realtime_tencent(etf_code: str) -> Optional[dict]:
        """通过腾讯接口获取 ETF 实时行情"""
        try:
            import httpx
            
            market = ETFService._get_market_prefix(etf_code)
            url = f"https://web.sqt.gtimg.cn/q={market}{etf_code}"
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                
                text = resp.text
                
                # 解析腾讯数据格式
                # v_sh516810="1~名称~代码~当前价~昨收~...~涨跌幅~..."
                match = re.search(r'v_[^=]+="([^"]+)"', text)
                if not match:
                    return None
                
                parts = match.group(1).split('~')
                if len(parts) < 35:
                    return None
                
                # 解析字段
                name = parts[1]
                code = parts[2]
                current_price = float(parts[3]) if parts[3] else 0
                pre_close = float(parts[4]) if parts[4] else current_price
                # parts[31] 是涨跌额，parts[32] 是涨跌幅
                change_pct = float(parts[32]) if len(parts) > 32 and parts[32] and parts[32] != '-' else 0
                change_amount = float(parts[31]) if len(parts) > 31 and parts[31] and parts[31] != '-' else 0
                # 今开
                open_price = float(parts[5]) if parts[5] else current_price
                # 成交量
                volume = float(parts[6]) if parts[6] else 0
                # 最高价 parts[33]，最低价 parts[34]
                high = float(parts[33]) if len(parts) > 33 and parts[33] else current_price
                low = float(parts[34]) if len(parts) > 34 and parts[34] else current_price
                
                return {
                    "code": code,
                    "name": name,
                    "current_price": current_price,
                    "change_pct": change_pct,
                    "change_amount": round(change_amount, 4),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "pre_close": pre_close,
                    "volume": volume,
                    "amount": 0,  # 腾讯接口不直接提供成交额
                    "update_time": datetime.now().isoformat(),
                    "is_trading": ETFService._is_trading_time()
                }
                
        except Exception as e:
            logger.error(f"腾讯接口获取 ETF 行情失败 {etf_code}: {e}")
            return None
    
    @staticmethod
    async def get_etf_realtime(etf_code: str, use_cache: bool = True) -> Optional[dict]:
        """获取 ETF 实时行情（优先腾讯接口，备用东方财富）"""
        # 检查缓存
        if use_cache:
            cached = etf_cache.get(etf_code, 'realtime')
            if cached:
                return cached
        
        # 优先使用腾讯接口
        result = await ETFService.get_etf_realtime_tencent(etf_code)
        if result:
            etf_cache.set(etf_code, result, 'realtime')
            # 添加缓存时间
            result['cached_at'] = datetime.now().isoformat()
            return result
        
        # 腾讯接口失败，尝试东方财富
        try:
            import akshare as ak
            from utils.rate_limiter import akshare_limiter
            
            # 限流
            await akshare_limiter.acquire_async()
            
            # 获取实时行情
            df = ak.fund_etf_spot_em()
            
            # 查找目标 ETF
            row = df[df['代码'] == etf_code]
            if row.empty:
                logger.warning(f"未找到 ETF: {etf_code}")
                return None
            
            data = row.iloc[0]
            
            # 解析数据
            current_price = float(data['最新价'])
            change_pct = float(data['涨跌幅'])
            change_amount = float(data['涨跌额'])
            volume = float(data['成交量']) if '成交量' in data else 0
            amount = float(data['成交额']) if '成交额' in data else 0
            high = float(data['最高']) if '最高' in data else current_price
            low = float(data['最低']) if '最低' in data else current_price
            open_price = float(data['今开']) if '今开' in data else current_price
            pre_close = float(data['昨收']) if '昨收' in data else current_price
            
            result = {
                "code": etf_code,
                "name": data['名称'],
                "current_price": current_price,
                "change_pct": change_pct,
                "change_amount": change_amount,
                "open": open_price,
                "high": high,
                "low": low,
                "pre_close": pre_close,
                "volume": volume,
                "amount": amount,
                "update_time": datetime.now().isoformat(),
                "is_trading": ETFService._is_trading_time()
            }
            
            etf_cache.set(etf_code, result, 'realtime')
            return result
            
        except Exception as e:
            logger.error(f"获取 ETF 行情失败 {etf_code}: {e}")
            return None
    
    @staticmethod
    async def get_etf_info(etf_code: str) -> Optional[dict]:
        """获取 ETF 基本信息（仅代码和名称）"""
        # 优先使用腾讯接口
        realtime = await ETFService.get_etf_realtime_tencent(etf_code)
        if realtime:
            return {
                "code": etf_code,
                "name": realtime.get('name', '')
            }
        
        # 腾讯接口失败，尝试东方财富
        try:
            import akshare as ak
            
            # 获取 ETF 列表
            df = ak.fund_etf_spot_em()
            
            # 查找目标 ETF
            row = df[df['代码'] == etf_code]
            if row.empty:
                return None
            
            data = row.iloc[0]
            return {
                "code": etf_code,
                "name": data['名称']
            }
            
        except Exception as e:
            logger.error(f"获取 ETF 信息失败 {etf_code}: {e}")
            return None
    
    @staticmethod
    async def get_etf_intraday(etf_code: str) -> Optional[dict]:
        """获取 ETF 分时数据"""
        try:
            import akshare as ak
            
            # 获取分时数据
            df = ak.fund_etf_fund_daily_em(symbol=etf_code)
            
            if df.empty:
                return None
            
            # 转换为列表
            times = []
            prices = []
            volumes = []
            
            for _, row in df.iterrows():
                times.append(row['时间'])
                prices.append(float(row['价格']))
                volumes.append(float(row['成交量']) if '成交量' in row else 0)
            
            return {
                "code": etf_code,
                "times": times,
                "prices": prices,
                "volumes": volumes
            }
            
        except Exception as e:
            logger.error(f"获取 ETF 分时数据失败 {etf_code}: {e}")
            return None
    
    @staticmethod
    async def get_etf_money_flow(etf_code: str, use_cache: bool = True) -> Optional[dict]:
        """获取 ETF 资金流向"""
        # 检查缓存
        if use_cache:
            cached = etf_cache.get(etf_code, 'money_flow')
            if cached:
                return cached
        
        try:
            import akshare as ak
            from utils.rate_limiter import akshare_limiter
            
            # 限流
            await akshare_limiter.acquire_async()
            
            # 获取个股资金流（ETF 也可以用这个接口）
            df = ak.stock_individual_fund_flow(stock=etf_code, market="sh" if etf_code.startswith("5") else "sz")
            
            if df.empty:
                return None
            
            # 取最近的数据
            latest = df.iloc[-1] if len(df) > 0 else None
            if latest is None:
                return None
            
            result = {
                "code": etf_code,
                "main_net_inflow": float(latest.get('主力净流入-净额', 0)) if '主力净流入-净额' in latest else 0,
                "main_net_inflow_pct": float(latest.get('主力净流入-净占比', 0)) if '主力净流入-净占比' in latest else 0,
                "retail_net_inflow": float(latest.get('小单净流入-净额', 0)) if '小单净流入-净额' in latest else 0,
                "retail_net_inflow_pct": float(latest.get('小单净流入-净占比', 0)) if '小单净流入-净占比' in latest else 0,
                "date": str(latest.get('日期', '')) if '日期' in latest else ''
            }
            
            etf_cache.set(etf_code, result, 'money_flow')
            return result
            
        except Exception as e:
            logger.error(f"获取 ETF 资金流向失败 {etf_code}: {e}")
            return None
    
    @staticmethod
    async def get_etf_analysis_data(etf_code: str, use_cache: bool = True) -> dict:
        """获取 ETF 完整分析数据"""
        realtime = await ETFService.get_etf_realtime(etf_code, use_cache)
        money_flow = None
        
        if realtime:
            money_flow = await ETFService.get_etf_money_flow(etf_code, use_cache)
        
        # 如果实时行情不可用，尝试获取基本信息
        basic_info = None
        if not realtime:
            basic_info = await ETFService.get_etf_info(etf_code)
        
        result = {
            "code": etf_code,
            "realtime": realtime,
            "money_flow": money_flow,
            "basic_info": basic_info,
            "available": realtime is not None or basic_info is not None
        }
        
        return result
    
    @staticmethod
    def _is_trading_time() -> bool:
        """判断是否在交易时间"""
        now = datetime.now()
        current_time = now.time()
        
        # 工作日
        if now.weekday() >= 5:  # 周六日
            return False
        
        # 交易时间段: 9:30-11:30, 13:00-15:00
        from datetime import time
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        
        return (morning_start <= current_time <= morning_end or 
                afternoon_start <= current_time <= afternoon_end)
