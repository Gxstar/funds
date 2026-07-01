# 场外基金投资管理工具 — 开发指南

## 项目概述

场外基金（非ETF）投资管理工具。支持持仓管理、交易记录、净值图表与技术指标、ETF 实时行情关联、AI 智能分析（DeepSeek）。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.13, FastAPI, Uvicorn |
| 数据库 | PostgreSQL（首选）/ SQLite（回退），原生 SQL（无 ORM） |
| 前端 | Vue 3 (`<script setup>`), Pinia, Vue Router 5, Element Plus 2, ECharts 6, marked |
| 构建 | Vite 7 (前端), uv (后端) |
| 数据源 | AkShare（东方财富）, 腾讯行情 API, DeepSeek API |
| HTTP | httpx (异步) |

## 目录结构

```
main.py                    # FastAPI 入口 + lifespan
config/prompts.json        # AI 提示词模板
database/
  connection.py            # get_db(), get_db_context(), init_db() — 支持 SQLite / PostgreSQL
  models.py                # Fund, Holding, Trade, Price, CacheMeta, Setting, AIAnalysis
routers/                   # 薄 API 层
  funds.py                 # /api/funds
  holdings.py              # /api/holdings
  trades.py                # /api/trades
  market.py                # /api/market
  etf.py                   # /api/etf
  ai.py                    # /api/ai
services/                  # 业务逻辑层（全静态方法）
  fund_service.py          # 基金 CRUD、持仓、交易、组合历史
  market_service.py        # 净值存取、AkShare 抓取、图表数据
  ai_service.py            # AI 分析 + 缓存
  etf_service.py           # ETF 实时行情 + 资金流向
  index_service.py         # 指数数据 + DB 缓存
  market_sentiment_service.py  # 涨跌家数、北向资金
  fund_detail_service.py   # 基金经理、规模、成立日
  news_service.py          # 行业新闻
  sync_scheduler.py        # 定时同步（08:30, 20:30）
utils/
  helpers.py               # .env 读写、设置存取、格式化、交易日判断
  indicators.py            # MA, EMA, MACD, RSI, 最大回撤, 波动率, 夏普比率
  rate_limiter.py          # AkShare 限流（1.5s 间隔）
frontend/
  src/
    main.js                # 应用入口
    App.vue                # 主布局
    api/index.js           # REST API 封装（fetch，无 axios）
    router/index.js        # 路由：/ 和 /fund/:code
    stores/funds.js        # useFundStore
    stores/settings.js     # useSettingsStore
    views/HomeView.vue     # 仪表盘
    views/FundDetailView.vue  # 基金详情
    components/            # FundList, SettingsDrawer, AddFundDialog
    utils/format.js        # 格式化工具
```

## 核心约定

### 后端

- **命名**: 文件/函数/变量 `snake_case`，类 `PascalCase`
- **架构**: `router/`（参数校验 + 路由）→ `services/`（纯业务逻辑）→ `database/`（数据存取）
- **Service**: 所有方法为 `@staticmethod`，无实例状态
- **DB**: 原生 SQL，`get_db_context()` 管理事务，`dict(row)` 转结果。`is_sqlite` 标志做条件 SQL
- **错误**: `ValueError` → `HTTPException(400)`，404 未找到，500 未预期
- **导入顺序**: 标准库 → 第三方 → 本地（全路径，如 `from services.fund_service import FundService`）
- **异步**: `async/await` + `asyncio.gather`，AkShare 用 `run_in_executor`
- **限流**: `RateLimiter` 保证 AkShare 调用间隔 ≥1.5s
- **缓存**: 内存缓存 + TTL（按交易时段调整），AI 结果额外持久化到 DB
- **颜色**: 绿涨红跌（中国惯例）

### 前端

- **组件**: Vue 3 Composition API + `<script setup>`，`ref` / `computed` / `watch` / `onMounted`
- **命名**: `.vue` 文件 `PascalCase`，`.js` 文件 `camelCase`
- **Store**: Pinia 组合式 API（`defineStore` 的 setup 函数）
- **API**: 原生 `fetch` 封装，按领域分组（`fundAPI`、`etfAPI` 等）
- **别名**: `@/` → `frontend/src/`
- **样式**: `<style scoped>`，纯 CSS + 动画，无预处理器
- **配色**: 主色 `#6366f1` / `#1890ff`，红涨绿跌
- **主题**: 红涨绿跌（与中国股市惯例一致）

## 启动命令

```bash
# 后端（端口 8000）
uv run python main.py

# 前端（端口 3000，代理 /api → 8000）
cd frontend && pnpm dev

# 数据库初始化
uv run python -m database.init_db
```

## API 概览

| 前缀 | 主要功能 |
|---|---|
| `/api/funds` | 基金 CRUD、搜索、信息刷新 |
| `/api/holdings` | 持仓 CRUD、汇总、组合历史 |
| `/api/trades` | 交易 CRUD、自动重算 |
| `/api/market` | 净值、图表、同步 |
| `/api/etf` | 实时行情、资金流向、分析 |
| `/api/ai` | AI 分析、设置、数据库配置 |

## 注意事项

- 无测试框架配置，但有 `.pytest_cache/` 和 `.coverage` 在 gitignore 中
- 无 lint/typecheck 配置
- `.env` 文件存放敏感信息（数据库凭据、API key）
- 所有 UI 文本为中文
- 前端 `pnpm build` 输出到 `frontend/dist/`
