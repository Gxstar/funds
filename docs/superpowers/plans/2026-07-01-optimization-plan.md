# 前后端全面优化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix bugs, improve performance, deduplicate code, and refactor architecture in both backend and frontend.

**Architecture:** Two batches — Batch 1 fixes bugs/performance/dedup (independent items), Batch 2 refactors service/store/component architecture (sequential). Each task produces independently testable changes.

**Tech Stack:** Python 3.13/FastAPI + Vue 3/Pinia/ECharts + DOMPurify (new dep)

**Key constraint:** Prefer mature libraries over custom code (e.g., DOMPurify, not custom HTML sanitizer). Keep exact/simple. Don't over-abstract.

## Global Constraints

- All Service methods remain `@staticmethod` (no instance pattern change)
- Raw SQL stays (no ORM introduction)
- Frontend stays on native fetch (no axios)
- Red-up/green-down (China convention)
- All UI text in Chinese
- Each task must have separate `git commit`

---

## BATCH 1: Bug 修复 + 性能 + 去重

### Task 1: RateLimiter 竞态条件修复 + 统一 async 调用

**Files:**
- Modify: `utils/rate_limiter.py:31-39`
- Modify: `services/market_service.py:133,164`
- Modify: `services/index_service.py:204,241,272,319`
- Test: Manual verification (no test suite)

**Interface:**
- Consumes: Existing `RateLimiter` class
- Produces: Fixed `acquire_async()` with time check inside lock

**Details from spec:**
1. Move time check into `self._lock` block in `acquire_async()`
2. Use `time.monotonic()` instead of `time.time()`
3. Replace `akshare_limiter.acquire()` (sync) → `await akshare_limiter.acquire_async()` in `market_service.py` and `index_service.py`

**Verification:**
- Run `uv run python main.py` — no import errors
- Spot-check: `acquire_async` now has `time.monotonic()` inside `with self._lock`

---

### Task 2: get_holdings_summary Decimal(None) 崩溃修复

**Files:**
- Modify: `services/fund_service.py:136`

**Details from spec:**
```python
# Before:
shares = Decimal(str(row["total_shares"]))
# After:
shares = Decimal(str(row["total_shares"])) if row["total_shares"] else Decimal("0")
```

**Verification:**
- Scan: no more `Decimal(str(row[...]))` without None guard in `fund_service.py`

---

### Task 3: recalculate_holding 嵌套事务修复

**Files:**
- Modify: `services/fund_service.py:406-444`
- No new files

**Details from spec:**
Add an internal helper `_update_holding_in_transaction(cursor, ...)` that uses the passed cursor (same transaction). Replace `update_holding()` and `delete_holding()` calls inside `recalculate_holding()` with the helper.

```python
@staticmethod
def _update_holding_in_transaction(cursor, fund_code, total_shares, cost_price, total_cost, is_sqlite):
    placeholder = "?" if is_sqlite else "%s"
    cursor.execute(
        f"""UPDATE holdings SET total_shares = {placeholder}, cost_price = {placeholder},
            total_cost = {placeholder}, updated_at = datetime('now')
            WHERE fund_code = {placeholder}""",
        (total_shares, cost_price, total_cost, fund_code)
    )
```

**Verification:**
- `recalculate_holding` no longer calls `update_holding()` or `delete_holding()` directly
- All SQL runs on the same `cursor`

---

### Task 4: AICache.save_cache 改用 get_db_context

**Files:**
- Modify: `services/ai_service.py:131-181`

**Details from spec:**
- Replace manual `conn = get_db()` / `cursor = conn.cursor()` / `conn.commit()` / `conn.close()` with `with get_db_context() as conn: cursor = conn.cursor()`
- Remove the SELECT verification query after INSERT
- Use `cursor.rowcount` to verify if needed

**Verification:**
- No more `conn = get_db()` outside `get_db_context()` in `AICache`
- Code passes lint

---

### Task 5: 前端 Resize 内存泄漏 + App.vue try/catch

**Files:**
- Modify: `views/HomeView.vue:534-550`
- Modify: `views/FundDetailView.vue:412-417`
- Modify: `App.vue:41-45`

**Details from spec:**
1. Store resize callbacks in variables:
```js
const handleResize = () => { chartInstance?.resize(); historyChartInstance?.resize() }
onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))
```
2. Wrap `App.vue` onMounted in try/catch with `ElMessage.error`

**Verification:**
- `removeEventListener` now uses same function reference as `addEventListener`
- `App.vue` onMounted has try/catch

---

### Task 6: XSS 消毒 + 提取 markdown 工具函数

**Files:**
- Create: `frontend/src/utils/markdown.js`
- Modify: `App.vue` (remove duplicate `renderMarkdown` + `marked.setOptions`, import from utils)
- Modify: `HomeView.vue` (same)
- Modify: `FundDetailView.vue` (same)
- Modify: `frontend/package.json` (add `dompurify`)

**Details:**
```js
// frontend/src/utils/markdown.js
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

export function renderMarkdown(text) {
  if (!text) return ''
  return DOMPurify.sanitize(marked(text))
}
```

**Dependencies:** `pnpm add dompurify`

**Verification:**
- `marked.setOptions()` called exactly once (in `markdown.js`)
- `renderMarkdown` defined exactly once (imported, not re-defined)
- Build succeeds: `cd frontend && pnpm build`

---

### Task 7: 后端性能优化 (全量基金缓存 + 组合历史 + AI N+1)

**Files:**
- Modify: `services/market_service.py` (fund_name_em cache + get_portfolio_history)
- Modify: `services/fund_service.py` (get_portfolio_history optimization)
- Modify: `services/ai_service.py` (DB connection sharing)

**Details:**
1. `market_service.py`: Add `_fund_name_cache = None` and `_fund_name_cache_time = 0` at module level. In `fetch_fund_info_from_akshare()` and `search_funds()`, check cache before calling `ak.fund_name_em()`. Cache TTL: 86400s (1 day).

2. `fund_service.py`: In `get_portfolio_history()`, precompute running share/cost balances per fund from trades table (sorted by date), then walk forward once per date per fund.

**Verification:**
- First search still works, second search within 24h hits cache
- Backend starts without errors

---

### Task 8: 提取 AI 分析对话框组件

**Files:**
- Create: `frontend/src/components/AIAnalysisDialog.vue`
- Modify: `App.vue` (replace inline dialog with component)
- Modify: `HomeView.vue` (replace inline dialog with component)

**Components:**
`AIAnalysisDialog.vue` — Props: `modelValue` Boolean, `fundCode` String (optional), `portfolioAnalysis` Object, `portfolioAiLoading` Boolean. Emits: `update:modelValue`. Contains: loading spinner, analysis header/timestamps/cache tags, summary grid, markdown content area with `renderMarkdown`.

**Verification:**
- AI dialog appears and works both from sidebar (App.vue) and HomeView
- No duplicate dialog template exists in either App.vue or HomeView.vue

---

## BATCH 2: 架构重构

### Task 9: 拆分 FundService → FundService + HoldingService + TradeService

**Files:**
- Modify: `services/fund_service.py` (shrink to fund CRUD only)
- Create: `services/holding_service.py`
- Create: `services/trade_service.py`
- Modify: `services/__init__.py`
- Modify: `routers/holdings.py` (import HoldingService)
- Modify: `routers/trades.py` (import TradeService)
- Modify: `routers/funds.py` (unchanged import)
- Modify: `services/market_service.py` (update import)

**Interfaces:**
- `HoldingService.get_holding(cursor, fund_code)` → dict
- `HoldingService.update_holding(...)` → None
- `HoldingService.delete_holding(...)` → None
- `HoldingService.get_holdings_summary()` → dict
- `HoldingService.recalculate_holding(fund_code)` → None
- `HoldingService.get_portfolio_history(...)` → list
- `HoldingService._calculate_shares_on_date(...)` → Decimal
- `HoldingService._calculate_cost_on_date(...)` → Decimal
- `TradeService.add_trade(...)` → dict
- `TradeService.get_trades(...)` → list
- `TradeService.update_trade(...)` → None
- `TradeService.delete_trade(...)` → None

**Verification:**
- All existing endpoints work: holdings summary, trades CRUD, fund CRUD
- No memory of removed methods in `fund_service.py`

---

### Task 10: 统一缓存 + 交易时间函数

**Files:**
- Create: `utils/cache.py` (TTLCache generic class)
- Modify: `utils/helpers.py` (add `is_trading_day`, `is_market_open`, `is_after_market_close`, `next_sync_time`)
- Modify: `services/etf_service.py` (replace ETFCache → TTLCache)
- Modify: `services/market_sentiment_service.py` (replace MarketSentimentCache → TTLCache)
- Modify: `services/fund_detail_service.py` (replace FundDetailCache → TTLCache)
- Modify: `services/news_service.py` (replace NewsCache → TTLCache)
- Modify: `services/index_service.py` (replace inline cache → use helpers)
- Modify: `utils/__init__.py`

**Details from spec:**
`TTLCache` — generic, thread-safe, simple get/set/invalidate. No trading-time awareness inside cache; caller handles dynamic TTL selection.

**Trading time helpers** in `utils/helpers.py`:
- `is_trading_day(d: date = None) -> bool`
- `is_market_open(dt: datetime = None) -> bool`
- `is_after_market_close(dt: datetime = None) -> bool`

**Verification:**
- All 4 separate cache classes replaced by `TTLCache` imports
- `_is_trading_time()` no longer exists in individual services
- No import errors

---

### Task 11: 清理死代码

**Files:**
- Modify: `utils/helpers.py` (remove dead formatters)
- Modify: `database/models.py` (remove AIAnalysis)
- Modify: `services/market_sentiment_service.py` (remove unused import)
- Modify: `frontend/src/components/FundList.vue` (remove unused import)

---

### Task 12: 拆分前端 Store (funds.js → 4 stores)

**Files:**
- Modify: `stores/funds.js` (shrink to fund CRUD only)
- Create: `stores/ai.js`
- Create: `stores/holdings.js`
- Create: `stores/chart.js`
- Modify: `stores/settings.js` (remove aiSettings, keep DB/prompts)
- Modify: `App.vue` (update imports)
- Modify: `HomeView.vue` (update imports)
- Modify: `FundDetailView.vue` (update imports)
- Modify: `FundList.vue` (update imports)
- Modify: `SettingsDrawer.vue` (update imports)

---

### Task 13: 拆分 HomeView.vue (1891 → 8 子组件)

**Files:**
- Create: `components/DashboardStats.vue`
- Create: `components/MarketIndices.vue`
- Create: `components/PortfolioDistributionChart.vue`
- Create: `components/PortfolioHistoryChart.vue`
- Create: `components/HoldingsTable.vue`
- Create: `components/RecentTrades.vue`
- Create: `components/ChangeRanking.vue`
- Modify: `views/HomeView.vue` (remove all business logic, become orchestration only)

---

### Task 14: 拆分 FundDetailView.vue (1148 → 6 子组件)

**Files:**
- Create: `components/FundHeader.vue`
- Create: `components/HoldingCard.vue`
- Create: `components/ETFCard.vue`
- Create: `components/NavChart.vue`
- Create: `components/AIPanel.vue`
- Create: `components/TradeFormDialog.vue`
- Modify: `views/FundDetailView.vue` (become orchestration only)

---

### Task 15: 消除前端 API 直接调用 + sync_all 去重 sleep

**Files:**
- Modify: `HomeView.vue` (remove direct `import { aiAPI, marketAPI, holdingAPI }`)
- Modify: `FundDetailView.vue` (remove direct `import { etfAPI, tradeAPI, marketAPI }`)
- Modify: `stores/funds.js` (add `syncAll`, `loadIndices`, `loadTradeHistory`)
- Modify: `stores/holdings.js` (add `loadPortfolioHistory`)
- Modify: `stores/ai.js` (add `analyzePortfolio`)
- Modify: `services/sync_scheduler.py` (remove explicit `asyncio.sleep(1.5)`)
