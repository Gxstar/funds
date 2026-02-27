"""基金详情增强服务"""
from datetime import datetime
from typing import Optional, Dict
import logging
import threading

logger = logging.getLogger(__name__)


class FundDetailCache:
    """基金详情缓存"""
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self.CACHE_TTL = 86400  # 24 小时缓存
    
    def get(self, fund_code: str) -> Optional[Dict]:
        with self._lock:
            if fund_code not in self._cache:
                return None
            cached = self._cache[fund_code]
            age = (datetime.now() - cached['timestamp']).total_seconds()
            if age < self.CACHE_TTL:
                return cached['data']
            return None
    
    def set(self, fund_code: str, data: Dict):
        with self._lock:
            self._cache[fund_code] = {
                'data': data,
                'timestamp': datetime.now()
            }


# 全局缓存实例
fund_detail_cache = FundDetailCache()


class FundDetailService:
    """基金详情增强服务"""
    
    # 指数基金类型与对应指数的映射
    INDEX_FUND_MAPPING = {
        # 科技类
        "人工智能": {"index": "科创50", "code": "sh000688"},
        "科技": {"index": "科技龙头", "code": "custom"},
        "芯片": {"index": "国证芯片", "code": "custom"},
        "半导体": {"index": "国证芯片", "code": "custom"},
        
        # 医药类
        "医药": {"index": "中证医药", "code": "custom"},
        "医疗": {"index": "中证医疗", "code": "custom"},
        "生物": {"index": "中证生物科技", "code": "custom"},
        
        # 消费类
        "白酒": {"index": "中证白酒", "code": "custom"},
        "消费": {"index": "中证消费", "code": "custom"},
        
        # 金融类
        "证券": {"index": "证券公司", "code": "custom"},
        "银行": {"index": "中证银行", "code": "custom"},
        
        # 新能源
        "新能源车": {"index": "新能源车", "code": "custom"},
        "光伏": {"index": "光伏产业", "code": "custom"},
        "新能源": {"index": "中证新能", "code": "custom"},
        
        # 其他
        "军工": {"index": "中证军工", "code": "custom"},
        "有色": {"index": "有色金属", "code": "custom"},
        "传媒": {"index": "中证传媒", "code": "custom"},
        "恒生科技": {"index": "恒生科技", "code": "hkHSTECH"},
    }
    
    @staticmethod
    async def get_fund_detail(fund_code: str) -> Dict:
        """获取基金详细信息（经理、规模、成立时间等）"""
        # 检查缓存
        cached = fund_detail_cache.get(fund_code)
        if cached:
            return cached
        
        result = {
            "fund_code": fund_code,
            "available": False,
            "manager": None,
            "company": None,
            "scale": None,
            "establish_date": None,
            "invest_strategy": None,
            "benchmark": None,
            "index_info": None,
        }
        
        try:
            import akshare as ak
            from utils.rate_limiter import akshare_limiter
            
            await akshare_limiter.acquire_async()
            
            # 获取基金详细信息
            df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            
            if df is not None and not df.empty:
                # 解析数据
                data_dict = dict(zip(df['item'], df['value']))
                
                result["available"] = True
                result["manager"] = data_dict.get('基金经理')
                result["company"] = data_dict.get('基金公司')
                result["scale"] = data_dict.get('最新规模')
                result["establish_date"] = data_dict.get('成立时间')
                result["invest_strategy"] = data_dict.get('投资策略')
                result["benchmark"] = data_dict.get('业绩比较基准')
                
                # 缓存结果
                fund_detail_cache.set(fund_code, result)
                
        except Exception as e:
            logger.error(f"获取基金详情失败 {fund_code}: {e}")
        
        return result
    
    @staticmethod
    def get_related_index(fund_type: str, fund_name: str = "") -> Optional[Dict]:
        """根据基金类型/名称获取相关指数信息"""
        # 优先从基金名称匹配
        for keyword, index_info in FundDetailService.INDEX_FUND_MAPPING.items():
            if keyword in fund_name or (fund_type and keyword in fund_type):
                return index_info
        
        return None
    
    @staticmethod
    def format_detail_for_ai(detail: Dict) -> str:
        """格式化基金详情用于 AI 分析"""
        if not detail.get("available"):
            return "基金详情数据暂不可用"
        
        lines = ["### 基金详细信息"]
        
        if detail.get("manager"):
            lines.append(f"- 基金经理: {detail['manager']}")
        if detail.get("company"):
            lines.append(f"- 基金公司: {detail['company']}")
        if detail.get("scale"):
            lines.append(f"- 基金规模: {detail['scale']}")
        if detail.get("establish_date"):
            lines.append(f"- 成立时间: {detail['establish_date']}")
        if detail.get("benchmark"):
            # 截断过长的基准描述
            benchmark = detail['benchmark']
            if len(benchmark) > 100:
                benchmark = benchmark[:100] + "..."
            lines.append(f"- 业绩基准: {benchmark}")
        
        return "\n".join(lines)


class ValuationService:
    """估值服务（简化版）"""
    
    # 主要指数估值区间参考（历史经验值，实际应从数据源获取）
    VALUATION_REFERENCE = {
        "上证指数": {"pe_low": 10, "pe_high": 20, "pe_median": 13},
        "深证成指": {"pe_low": 15, "pe_high": 35, "pe_median": 22},
        "创业板指": {"pe_low": 25, "pe_high": 60, "pe_median": 40},
        "沪深300": {"pe_low": 10, "pe_high": 18, "pe_median": 12},
        "中证500": {"pe_low": 15, "pe_high": 35, "pe_median": 22},
        "科创50": {"pe_low": 30, "pe_high": 80, "pe_median": 50},
    }
    
    @staticmethod
    def estimate_valuation_level(index_name: str, current_change_pct: float) -> Dict:
        """
        根据近期涨跌幅估算估值水平（简化方法）
        实际应用中应该获取真实 PE/PB 数据
        """
        # 基于近期涨跌判断大致位置
        if current_change_pct > 5:
            level = "偏高"
            suggestion = "短期涨幅较大，注意回调风险"
        elif current_change_pct > 2:
            level = "中等偏上"
            suggestion = "走势偏强，可继续持有"
        elif current_change_pct < -5:
            level = "偏低"
            suggestion = "短期跌幅较大，可能存在机会"
        elif current_change_pct < -2:
            level = "中等偏下"
            suggestion = "走势偏弱，可考虑逢低布局"
        else:
            level = "中等"
            suggestion = "走势平稳，可维持原策略"
        
        return {
            "index_name": index_name,
            "estimated_level": level,
            "suggestion": suggestion,
            "note": "估值判断基于近期涨跌幅估算，仅供参考"
        }
    
    @staticmethod
    def format_valuation_for_ai(valuation: Dict) -> str:
        """格式化估值信息用于 AI 分析"""
        lines = [f"### 估值参考（{valuation['index_name']}）"]
        lines.append(f"- 估值水平: {valuation['estimated_level']}")
        lines.append(f"- 建议: {valuation['suggestion']}")
        lines.append(f"- 备注: {valuation['note']}")
        return "\n".join(lines)