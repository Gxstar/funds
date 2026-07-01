# 前后端全面优化 — 设计文档

> 日期：2026-07-01 | 状态：设计完成，待评审

## 总原则

- 精确简洁：不引入过度抽象，优先用成熟库（如 DOMPurify），不自造轮子
- 拆分而非重写：保持现有代码风格（后端 `@staticmethod` + 原生 SQL，前端 `<script setup>` + fetch）
- 每个 batch 完成后可独立验证，不阻塞后续

---

## 第一批：Bug 修复 + 性能 + 去重（低风险，快速见效）

### 1. 后端 Bug 修复（4 处）

#### 1.1 `RateLimiter.acquire_async()` 竞态条件

**文件**：`utils/rate_limiter.py:31-39`

**现状**：时间检查在锁外，两个并发协程可能同时通过 sleep 检查。

**方案**：将时间检查纳入 `threading.Lock` 内。AkShare 本身就是串行调用场景，锁内 `await asyncio.sleep(1.5)` 可接受。

```python
async def acquire_async(self):
    with self._lock:
        now = time.monotonic()
        wait_time = self.min_interval - (now - self.last_request_time)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self.last_request_time = time.monotonic()
```

同时将 `market_service.py:133,164` 和 `index_service.py:204,241,272,319` 中 `akshare_limiter.acquire()` (同步) 改为 `await akshare_limiter.acquire_async()`。

#### 1.2 `get_holdings_summary()` 崩溃

**文件**：`services/fund_service.py:136`

**现状**：`shares = Decimal(str(row["total_shares"]))` — 当 `total_shares=None` 时抛 `InvalidOperation`。

**方案**：加 guard：
```python
shares = Decimal(str(row["total_shares"])) if row["total_shares"] else Decimal("0")
```

#### 1.3 `recalculate_holding()` 嵌套事务

**文件**：`services/fund_service.py:406-444`

**现状**：外层 `get_db_context()` 内调 `update_holding()` / `delete_holding()` 各自又开独立事务，事务一致性断裂。

**方案**：新增内部辅助函数 `_update_holding_in_transaction(cursor, fund_code, total_shares, cost_price, total_cost)`，在 `recalculate_holding()` 的同一个 cursor 上直接执行 SQL，不跨事务。

#### 1.4 `AICache.save_cache()` 绕过统一 DB 管理

**文件**：`services/ai_service.py:131-181`

**现状**：自己开 `conn = get_db()`，手动 commit/close，不用项目统一的 `get_db_context()`，还附带一个无意义的 SELECT 验证查询。

**方案**：改用 `get_db_context()`，移除 SELECT 验证。

---

### 2. 前端 Bug 修复（3 处）

#### 2.1 Resize 事件监听器内存泄漏

**文件**：`views/HomeView.vue:534-546`, `views/FundDetailView.vue:412-417`

**现状**：`addEventListener` 和 `removeEventListener` 用了两个不同的匿名箭头函数，永远无法移除。

**方案**：存储回调引用。
```js
const handleResize = () => { instance?.resize(); otherInstance?.resize() }
window.addEventListener('resize', handleResize)
onUnmounted(() => window.removeEventListener('resize', handleResize))
```

#### 2.2 XSS 风险 — `v-html` 无消毒

**文件**：`App.vue:253`, `HomeView.vue:919`, `FundDetailView.vue:591`

**现状**：`marked()` 不消毒输出，AI 响应可注入 `<script>`。

**方案**：安装 `dompurify`，在 `renderMarkdown` 中消毒：
```js
import DOMPurify from 'dompurify'
function renderMarkdown(text) {
  if (!text) return ''
  return DOMPurify.sanitize(marked(text))
}
```

#### 2.3 `App.vue` onMounted 无错误处理

**文件**：`App.vue:41-45`

**方案**：加 try/catch + `ElMessage.error`。

---

### 3. 后端性能优化（3 处）

#### 3.1 全量基金下载问题

**文件**：`services/market_service.py:127-152` (`fetch_fund_info_from_akshare`), `services/market_service.py:287-313` (`search_funds`)

**现状**：每次搜一只基金下载整个 `fund_name_em()` 全量数据（20,000+ 条）。

**方案**：因为 AkShare 无按代码的单条查询 API，改为：
- 首次调用缓存 `fund_name_em()` 结果到内存（TTL: 1 天）
- 后续调用直接从内存过滤
- 新增 `_fund_name_cache` 全局变量 + 时间戳

#### 3.2 `get_portfolio_history()` O(n*m*k) 优化

**文件**：`services/fund_service.py:446-587`

**现状**：对每个日期、每个持仓、逆序遍历全部交易。

**方案**：
1. 先从 trades 表查出每只基金的全部交易，按日期排序
2. 预计算每日的累计份额和成本（向前累加）
3. 再按日期生成组合净值，总复杂度 O(dates × holdings)

#### 3.3 AI `analyze_portfolio()` N+1 查询

**文件**：`services/ai_service.py:761-800`

**方案**：保持逐个调用的结构（因为 `get_chart_data()` 返回的是完整 chart JSON，短期内改成本高），但将 DB 连接提取到循环外共享。

---

### 4. 前端去重（2 处）

#### 4.1 提取 `renderMarkdown` + `marked.setOptions`

**新增文件**：`frontend/src/utils/markdown.js`

```js
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

export function renderMarkdown(text) {
  if (!text) return ''
  return DOMPurify.sanitize(marked(text))
}
```

**影响文件**：`App.vue`、`HomeView.vue`、`FundDetailView.vue` — 删除各自定义，改 import。

#### 4.2 提取 AI 分析对话框

**新增文件**：`frontend/src/components/AIAnalysisDialog.vue`

**方案**：
- Props: `modelValue` (v-model 控制显隐), `fundCode` (可选，单基金/组合分析)
- 内部方法: `loadCache()`, `refreshAnalysis()`, `emit('update:modelValue', false)` 关闭
- `App.vue` 和 `HomeView.vue` 用 `<AIAnalysisDialog v-model="showAnalysis" />`

---

## 第二批：架构重构（中等风险，要求拆分验证）

### 5. 后端 — 拆分 `FundService` → 3 个类

| 新类 | 文件 | 职责 |
|---|---|---|
| `FundService` | `services/fund_service.py`（保留名） | 基金 CRUD、搜索、信息刷新 |
| `HoldingService` | `services/holding_service.py`（新增） | 持仓 CRUD、汇总、重算、组合历史 |
| `TradeService` | `services/trade_service.py`（新增） | 交易 CRUD、自动更新持仓 |

- 每个方法仍为 `@staticmethod`
- `services/__init__.py` 更新 exports
- `routers/holdings.py` 引入 `HoldingService`，`routers/trades.py` 引入 `TradeService`
- 内部辅助函数（`_calculate_shares_on_date`, `_calculate_cost_on_date`）保持为 `@staticmethod` 放在 `HoldingService` 中

---

### 6. 后端 — 统一缓存 + 交易时间

#### 6.1 通用 `TTLCache`

**新增文件**：`utils/cache.py`

```python
import time, threading, typing

T = typing.TypeVar("T")

class TTLCache(typing.Generic[T]):
    def __init__(self, ttl: float):
        self._ttl = ttl
        self._data: T | None = None
        self._timestamp: float = 0
        self._lock = threading.Lock()

    def get(self) -> T | None:
        with self._lock:
            if self._data is not None and time.monotonic() - self._timestamp < self._ttl:
                return self._data
        return None

    def set(self, data: T):
        with self._lock:
            self._data = data
            self._timestamp = time.monotonic()

    def invalidate(self):
        with self._lock:
            self._data = None
```

**受影响的 service**：
- `etf_service.py`：删除 `ETFCache` 类，改为 `_realtime_cache = TTLCache(ttl=5)` + `_money_flow_cache = TTLCache(ttl=60)` 等。动态 TTL 在 `ETFService` 方法内根据交易时段选择。
- `market_sentiment_service.py`：删除 `MarketSentimentCache`，改为 `_cache = TTLCache(ttl=10)`。
- `fund_detail_service.py`：删除 `FundDetailCache`，改为 `_cache = TTLCache(ttl=86400)`。
- `news_service.py`：删除 `NewsCache`，改为 `_cache = TTLCache(ttl=600)`。

#### 6.2 统一交易时间函数

**文件**：`utils/helpers.py`（扩展现有文件）

新增：
```python
from datetime import datetime, time, date, timedelta

TRADING_SESSIONS = [
    (time(9, 30), time(11, 30)),
    (time(13, 0), time(15, 0)),
]

def is_trading_day(d: date = None) -> bool:
    """判断是否为 A 股交易日（简化版：周一到周五，不含节假日）"""
    d = d or date.today()
    return d.weekday() < 5

def is_market_open(dt: datetime = None) -> bool:
    """判断是否在交易时段内"""
    if not is_trading_day(dt.date() if dt else date.today()):
        return False
    t = (dt or datetime.now()).time()
    return any(start <= t <= end for start, end in TRADING_SESSIONS)

def is_after_market_close(dt: datetime = None) -> bool:
    """判断是否已收盘"""
    t = (dt or datetime.now()).time()
    return t > TRADING_SESSIONS[-1][1]

def next_sync_time() -> datetime:
    """返回下一个同步时间"""
    ...
```

**受影响文件**：`etf_service.py`、`market_sentiment_service.py`、`index_service.py`、`ai_service.py`、`sync_scheduler.py` — 替换各自实现为 import。

---

### 7. 后端 — 清理死代码

| 删除内容 | 位置 |
|---|---|
| `format_decimal()` | `utils/helpers.py:160-162` |
| `format_currency()` | `utils/helpers.py:165-167` |
| `format_percent()` | `utils/helpers.py:170-173` |
| `parse_date()` | `utils/helpers.py:176-185` |
| `calculate_profit()` | `utils/helpers.py:188-200` |
| `get_trade_days()` | `utils/helpers.py:203-213` |
| `AIAnalysis` 类 | `database/models.py:158-179` |
| 未使用的 `date` import | `services/market_sentiment_service.py:2` |
| 未使用的 `computed` import | `frontend/src/components/FundList.vue:2` |

---

### 8. 前端 — 拆分 God Store

**现状**：`stores/funds.js` 372 行，混合 6 个领域。

**方案**：拆成 4 个 store：

| Store | 文件 | State | Actions |
|---|---|---|---|
| `useFundStore` | `stores/funds.js` | `funds`, `currentFund` | `loadFunds`, `addFund`, `deleteFund`, `selectFund`, `searchFunds`, `refreshFundInfo`, `syncAll` |
| `useHoldingStore` | `stores/holdings.js` (新增) | `holdingsSummary`, `recentTrades` | `loadHoldingsSummary`, `refreshAll`, `loadTradePreview`, `loadPortfolioHistory` |
| `useChartStore` | `stores/chart.js` (新增) | `chartData`, `etfData` | `loadChartData`, `loadETFData` |
| `useAIStore` | `stores/ai.js` (新增) | `aiAnalysis`, `aiLoading`, `aiSettings` | `loadAICache`, `getAISuggestion`, `loadAISettings` |

**`aiSettings` 去重**：`stores/settings.js` 保留 DB/提示词相关设置，`aiSettings` 归 `useAIStore` 独占。`SettingsDrawer.vue` 需要时从 `useAIStore` 获取。

---

### 9. 前端 — 拆分 `HomeView.vue`（1891 → ~150 行编排层）

| 新组件 | 文件 | Props | Events |
|---|---|---|---|
| `DashboardStats` | `components/DashboardStats.vue` | `totalMarketValue`, `totalCost`, `totalProfit`, `positionCount`, `fundCount` | — |
| `MarketIndices` | `components/MarketIndices.vue` | `indices`, `selectedTypes` | `@refresh`, `@open-selection` |
| `PortfolioDistributionChart` | `components/PortfolioDistributionChart.vue` | `holdings` | — |
| `PortfolioHistoryChart` | `components/PortfolioHistoryChart.vue` | `history` | — |
| `HoldingsTable` | `components/HoldingsTable.vue` | `holdings`, `growthType` | `@click-fund` |
| `RecentTrades` | `components/RecentTrades.vue` | `trades` | — |
| `ChangeRanking` | `components/ChangeRanking.vue` | `holdings` | — |

`HomeView.vue` 只负责：
1. 从 stores 聚合数据
2. 传递给子组件
3. 处理页面级操作（同步、刷新索引）

---

### 10. 前端 — 拆分 `FundDetailView.vue`（1148 → ~120 行编排层）

| 新组件 | 文件 | Props | Events |
|---|---|---|---|
| `FundHeader` | `components/FundHeader.vue` | `fund`, `holding` | — |
| `HoldingCard` | `components/HoldingCard.vue` | `fund`, `holding` | — |
| `ETFCard` | `components/ETFCard.vue` | `etfData` | `@set-etf` |
| `NavChart` | `components/NavChart.vue` | `chartData` | — |
| `AIPanel` | `components/AIPanel.vue` | `aiData`, `loading` | `@analyze` |
| `TradeFormDialog` | `components/TradeFormDialog.vue` | `modelValue`, `tradeType`, `fund` | `@save` |

---

### 11. 前端 — 消除 API 直接调用

**规则**：视图组件不 import `xxxAPI`，全部走 store actions。

需要新增的 store actions：
- `useHoldingStore.loadPortfolioHistory()` — 从 `HomeView` 迁入
- `useFundStore.syncAll()` — 从 `HomeView` 迁入
- `useFundStore.loadIndices()` / `refreshIndices()` — 从 `HomeView` 迁入
- `useFundStore.loadTradeHistory()` — 从 `FundDetailView` 迁入
- `aiStore.analyzePortfolio()` — 从 `HomeView`/`App.vue` 迁入

---

### 12. 后端 — `sync_all_funds()` 去重 sleep

**文件**：`services/sync_scheduler.py:78-100`

移除 `await asyncio.sleep(1.5)`，`RateLimiter.acquire_async()` 已做限流。

---

## 不改动的内容（有意保留）

- 所有 Service 方法仍为 `@staticmethod`（不引入实例化模式）
- 原生 SQL 模式不变（不引入 ORM）
- 前端仍用 fetch（不引入 axios）
- `database/connection.py` 的 `load_dotenv()` 副作用保留（影响面太大，移到后续改进）
- 7 个未使用的 formatter 函数直接删除（不保留）
- `AIAnalysis` 模型已确认完全未使用，删除
- `sync_fund_history()` 调用 `FundService.update_fund()` 的跨事务问题保留到后续处理（风险低且改动面大）

---

## 实现顺序

```
第一批（所有改动独立可并行）：
├── 1.1  RateLimiter 修复
├── 1.2  get_holdings_summary 修复
├── 1.3  recalculate_holding 嵌套事务
├── 1.4  AICache.save_cache 标准化
├── 2.1  resize 内存泄漏
├── 2.2  v-html XSS 消毒
├── 2.3  App.vue try/catch
├── 3.1  全量基金缓存
├── 3.2  get_portfolio_history 优化
├── 3.3  AI N+1 DB 共享连接
├── 4.1  提取 markdown 工具
└── 4.2  提取 AI 分析对话框

第二批（顺序依赖，需逐步推进）：
├── 5.  拆分 FundService（先改服务层，再改 router）
├── 6.  统一缓存+交易时间（依赖 5 完成后的稳定代码格局）
├── 7.  清理死代码（无依赖，最后做）
├── 8.  拆分 Store（先拆 store，再逐组件改 import）
├── 9.  拆分 HomeView（依赖 8 完成）
├── 10. 拆分 FundDetailView（依赖 8 完成）
└── 11. 消除 API 直接调用（依赖 9+10 完成）
```
