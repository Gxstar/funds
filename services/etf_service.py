"""ETF 实时行情服务"""
from datetime import datetime, date
from typing import Optional, List, Dict
import logging
import re
import asyncio

from utils.cache import TTLCache
from utils.helpers import is_market_open

logger = logging.getLogger(__name__)

# 全局缓存
_realtime_cache = TTLCache(ttl=300)    # 盘中 5 分钟
_money_flow_cache = TTLCache(ttl=600)  # 盘中 10 分钟


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
                    "is_trading": is_market_open()
                }
                
        except Exception as e:
            logger.error(f"腾讯接口获取 ETF 行情失败 {etf_code}: {e}")
            return None
    
    @staticmethod
    async def get_etf_realtime(etf_code: str, use_cache: bool = True) -> Optional[dict]:
        """获取 ETF 实时行情（优先腾讯接口，备用东方财富）"""
        # 检查缓存
        if use_cache:
            cached = _realtime_cache.get()
            if cached:
                return cached
        
        # 优先使用腾讯接口
        result = await ETFService.get_etf_realtime_tencent(etf_code)
        if result:
            result['cached_at'] = datetime.now().isoformat()
            _realtime_cache.set(result)
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
                "is_trading": is_market_open()
            }
            
            result['cached_at'] = datetime.now().isoformat()
            _realtime_cache.set(result)
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
    async def get_etf_money_flow(etf_code: str, use_cache: bool = True) -> Optional[dict]:
        """获取 ETF 资金流向"""
        # 检查缓存
        if use_cache:
            cached = _money_flow_cache.get()
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
            
            _money_flow_cache.set(result)
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
    

