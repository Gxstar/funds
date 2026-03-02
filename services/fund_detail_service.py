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