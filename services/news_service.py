"""财经新闻服务"""
from datetime import datetime
from typing import Optional, List, Dict
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class NewsCache:
    """新闻缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._lock = Lock()
        self.CACHE_TTL = 1800  # 30 分钟缓存
    
    def get(self, key: str) -> Optional[List[dict]]:
        with self._lock:
            if key not in self._cache:
                return None
            cached = self._cache[key]
            age = (datetime.now() - cached["timestamp"]).total_seconds()
            if age < self.CACHE_TTL:
                return cached["data"]
            return None
    
    def set(self, key: str, data: List[dict]):
        with self._lock:
            self._cache[key] = {
                "data": data,
                "timestamp": datetime.now()
            }


news_cache = NewsCache()


class NewsService:
    """财经新闻服务"""
    
    # 基金类型到新闻关键词的映射
    FUND_TYPE_KEYWORDS = {
        "新能源车": ["新能源汽车", "电动车", "锂电池"],
        "新能源汽车": ["新能源汽车", "电动车", "锂电池"],
        "光伏": ["光伏", "太阳能", "新能源"],
        "新能源": ["新能源", "光伏", "储能"],
        "医药": ["医药", "医疗", "生物制药"],
        "医疗": ["医疗", "医药", "医疗器械"],
        "白酒": ["白酒", "消费", "酒类"],
        "消费": ["消费", "零售", "电商"],
        "半导体": ["半导体", "芯片", "集成电路"],
        "芯片": ["芯片", "半导体", "集成电路"],
        "军工": ["军工", "国防", "航空航天"],
        "证券": ["证券", "券商", "金融"],
        "银行": ["银行", "金融", "利率"],
        "地产": ["地产", "房地产", "楼市"],
        "科技": ["科技", "互联网", "人工智能"],
        "互联网": ["互联网", "电商", "科技"],
        "人工智能": ["人工智能", "AI", "ChatGPT"],
        "机器人": ["机器人", "自动化", "智能制造"],
        "恒生科技": ["恒生科技", "港股", "科技股"],
        "储能": ["储能", "电池", "新能源"],
        "农业": ["农业", "种植", "养殖"],
    }
    
    @staticmethod
    def get_keywords_for_fund(fund_type: str, related_etf_name: str = None) -> List[str]:
        """根据基金类型获取新闻关键词"""
        keywords = []
        
        if fund_type:
            for key, words in NewsService.FUND_TYPE_KEYWORDS.items():
                if key in fund_type or fund_type in key:
                    keywords.extend(words)
        
        if related_etf_name:
            for key, words in NewsService.FUND_TYPE_KEYWORDS.items():
                if key in related_etf_name:
                    keywords.extend(words[:2])
        
        keywords = list(set(keywords))
        
        if not keywords:
            keywords = ["A股", "基金"]
        
        return keywords[:3]
    
    @staticmethod
    async def fetch_news_by_keyword(keyword: str, max_count: int = 5) -> List[dict]:
        """根据关键词获取新闻"""
        cache_key = f"news_{keyword}"
        cached = news_cache.get(cache_key)
        if cached:
            return cached
        
        try:
            import akshare as ak
            
            df = ak.stock_news_em(symbol=keyword)
            
            if df.empty:
                return []
            
            news_list = []
            for _, row in df.head(max_count).iterrows():
                news_list.append({
                    "title": row.get("新闻标题", ""),
                    "content": row.get("新闻内容", "")[:500],
                    "time": row.get("发布时间", ""),
                    "source": row.get("文章来源", ""),
                    "url": row.get("新闻链接", ""),
                })
            
            news_cache.set(cache_key, news_list)
            return news_list
            
        except Exception as e:
            logger.error(f"获取新闻失败 {keyword}: {e}")
            return []
    
    @staticmethod
    async def get_fund_related_news(
        fund_type: str = None,
        related_etf_name: str = None,
        max_news: int = 5
    ) -> List[dict]:
        """获取基金相关新闻"""
        keywords = NewsService.get_keywords_for_fund(fund_type, related_etf_name)
        
        all_news = []
        for keyword in keywords:
            news = await NewsService.fetch_news_by_keyword(keyword, max_count=3)
            all_news.extend(news)
        
        all_news.sort(key=lambda x: x.get("time", ""), reverse=True)
        return all_news[:max_news]
    
    @staticmethod
    def format_news_for_ai(news_list: List[dict]) -> str:
        """格式化新闻信息供 AI 分析"""
        if not news_list:
            return "暂无相关新闻"
        
        lines = []
        for i, news in enumerate(news_list, 1):
            lines.append(f"{i}. [{news.get('source', '未知')}] {news.get('title', '')}")
            lines.append(f"   时间: {news.get('time', '')}")
            content = news.get('content', '')
            if content:
                lines.append(f"   摘要: {content[:200]}...")
            lines.append("")
        
        return "\n".join(lines)