# 场外基金投资管理工具

持仓管理、交易记录、净值图表、ETF 实时行情关联、AI 智能分析。

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
config/
  prompts.json             # AI 提示词模板
database/
  connection.py            # get_db() / get_db_context() / init_db() — 支持 PostgreSQL + SQLite
  models.py                # Fund, Holding, Trade, Price, CacheMeta, Setting, AIAnalysis 数据类
  init_db.py               # 独立初始化脚本: python -m database.init_db
routers/                   # 薄 API 层，参数校验 → 委托 services
  funds.py                 # /api/funds — CRUD、搜索、信息刷新
  holdings.py              # /api/holdings — CRUD、汇总、组合历史
  trades.py                # /api/trades — CRUD、自动重算
  market.py                # /api/market — 净值、图表、同步
  etf.py                   # /api/etf — 实时行情、资金流向、推荐
  ai.py                    # /api/ai — AI 分析、设置、数据库管理
services/                  # 业务逻辑层，全 @staticmethod，无实例状态
  fund_service.py          # 基金 CRUD、持仓、交易、组合历史
  market_service.py        # 净值存取、AkShare 抓取、图表数据
  ai_service.py            # DeepSeek 客户端、AICache、分析逻辑
  etf_service.py           # ETF 实时行情 + 资金流向（腾讯 / AkShare）
  index_service.py         # 指数数据 + DB 缓存
  market_sentiment_service.py  # 涨跌家数、北向资金（AkShare + 备用源）
  fund_detail_service.py   # 基金经理、规模、成立日
  news_service.py          # 行业新闻
  sync_scheduler.py        # 异步定时器，08:30 / 20:30 自动同步
utils/
  helpers.py               # .env 读写、DB 设置存取、日期工具、盈亏计算、交易日判断
  indicators.py            # MA / EMA / MACD / RSI / 最大回撤 / 波动率 / 夏普比率
  rate_limiter.py          # 线程安全限流器，AkShare 间隔 ≥1.5s
frontend/
  src/
    main.js                # 入口：createApp + Pinia + Router + Element Plus(zhCn) + 图标全局注册
    App.vue                # 主布局：顶栏 + 侧栏(FundList) + 内容区(router-view) + 底栏
    api/index.js           # REST API 封装：fundAPI / holdingAPI / tradeAPI / marketAPI / aiAPI / settingsAPI / etfAPI
    router/index.js        # 路由：/ → HomeView, /fund/:code → FundDetailView
    stores/
      funds.js             # useFundStore：基金列表、持仓汇总、图表、ETF、交易、AI 状态
      settings.js          # useSettingsStore：AI 设置、DB 配置、提示词
    utils/format.js        # formatCurrency / formatPercent / formatDate / formatDateTime
    views/
      HomeView.vue         # 仪表盘：统计卡片、指数、饼图/玫瑰图、历史走势、持仓、交易记录、收益排行
      FundDetailView.vue   # 基金详情：净值图(MA+MACD+RSI)、交易录入、ETF 数据、AI 分析
    components/
      FundList.vue         # 侧栏：基金搜索、列表、汇总卡片、AI 分析入口
      SettingsDrawer.vue   # 设置抽屉：API Key、DB 配置、提示词（懒加载）
      AddFundDialog.vue    # 搜索 + 添加基金对话框
```

## 启动

```bash
# 后端（127.0.0.1:8000，热重载）
uv run python main.py

# 前端（127.0.0.1:3000，代理 /api → 8000）
cd frontend && pnpm dev

# 数据库初始化
uv run python -m database.init_db
```

## 数据库

支持 PostgreSQL（推荐）和 SQLite（零配置回退）。连接参数通过 `.env` 配置，缺省时自动使用 SQLite。

```env
DB_HOST=localhost       # 缺省则使用 SQLite
DB_PORT=5432
DB_NAME=funds
DB_USER=postgres
DB_PASSWORD=your_password

DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

## API 概览

### 基金管理 `/api/funds`
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/` | 全部基金列表 |
| POST | `/` | 添加基金（自动获取信息） |
| GET | `/{code}` | 基金详情含收益 |
| PUT | `/{code}` | 更新基金备注/ETF 关联 |
| DELETE | `/{code}` | 删除基金及关联数据 |
| GET | `/search/{keyword}` | 搜索基金（代码/名称） |
| POST | `/{code}/refresh-info` | 刷新基金基本信息 |

### 持仓管理 `/api/holdings`
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/` | 全部持仓 |
| GET | `/summary` | 持仓汇总（成本、市值、盈亏） |
| GET | `/{code}` | 单只持仓详情 |
| PUT | `/{code}` | 更新备注 |
| DELETE | `/{code}` | 清空持仓 |
| POST | `/{code}/recalculate` | 重新计算持仓数据 |
| GET | `/history/portfolio` | 组合历史走势 |

### 交易记录 `/api/trades`
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/` | 全部交易（支持 code 过滤） |
| POST | `/` | 新增交易（买入/卖出，自动更新持仓） |
| PUT | `/{id}` | 修改交易（自动重算持仓） |
| DELETE | `/{id}` | 删除交易（自动重算持仓） |
| POST | `/{code}/recalculate` | 重算某基金持仓 |

### 行情数据 `/api/market`
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/indices` | 大盘指数（上证/深证/创业板/科创50） |
| GET | `/{code}` | 基金基本信息 |
| GET | `/{code}/history` | 历史净值列表 |
| GET | `/{code}/chart` | 图表数据（含 MA/EMA/MACD/RSI/交易标记） |
| POST | `/{code}/sync` | 同步单只基金净值 |
| POST | `/sync-all` | 全量同步 |

### ETF 行情 `/api/etf`
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/realtime/{code}` | ETF 实时行情（腾讯 API） |
| GET | `/money-flow/{code}` | 主力资金流向 |
| GET | `/analysis/{code}` | 综合分析（含技术指标） |
| GET | `/recommend/{type}` | 按基金类型推荐 ETF |
| GET | `/fund/{code}` | 查询基金关联 ETF 行情 |

### AI 分析 `/api/ai`
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/status` | 配置状态检查 |
| POST | `/suggest/{code}` | 单只基金 AI 分析（含缓存） |
| POST | `/analyze` | 持仓组合综合 AI 分析 |
| GET/POST | `/settings` | AI 设置读写（API Key、模型等） |
| GET/POST | `/prompts` | 提示词模板读写 |
| GET | `/news` | 行业新闻 |
| GET | `/market-sentiment` | 市场情绪（涨跌家数、北向资金） |
| GET | `/fund-detail/{code}` | 基金经理/规模/成立日 |
| GET/POST | `/database-config` | 数据库连接配置 |
| POST | `/database-test` | 测试数据库连接 |
| POST | `/database-init` | 初始化/迁移数据库 |
| GET | `/database-status` | 数据库状态 |

## 核心约定

- **颜色**：红涨绿跌（中国 A 股惯例）
- **限流**：AkShare 调用间隔 ≥1.5 秒
- **缓存**：ETF 30 分钟 / 指数 5 分钟 / 市场情绪当日 / AI 分析 24 小时（持久化到 DB）
- **同步**：每日 08:30（盘前）和 20:30（盘后）自动同步净值
- **配色**：主色 `#6366f1` / `#1890ff`

## License

MIT
