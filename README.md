# 场外基金投资管理工具

一个简洁实用的场外基金投资管理工具，支持持仓管理、行情查看、交易记录和多维度 AI 投资建议。

## 功能特性

### 核心功能
- **基金管理**：添加、删除基金，自动获取基金信息
- **持仓管理**：记录持仓份额、成本，实时计算盈亏
- **交易记录**：买入卖出记录，自动更新持仓
- **行情数据**：历史净值图表，技术指标（MA/RSI/MACD/布林带）

### ETF 关联
- **关联 ETF**：为基金设置关联 ETF，实时跟踪场内行情
- **实时行情**：ETF 当日价格、涨跌幅、主力资金流向
- **智能推荐**：根据基金类型自动推荐关联 ETF

### AI 智能分析
- **技术面分析**：趋势判断、均线支撑压力、RSI 超买超卖
- **风险评估**：最大回撤、波动率、夏普比率
- **市场情绪**：涨跌家数比、北向资金流向
- **行业新闻**：自动获取相关行业资讯
- **综合建议**：买入/持有/卖出建议及仓位配置建议

### 数据同步
- **定时同步**：每日自动同步最新净值数据
- **缓存机制**：智能缓存减少重复请求

## 技术栈

- **后端**：Python 3.13 + FastAPI + Uvicorn
- **数据库**：PostgreSQL
- **前端**：原生 HTML/CSS/JavaScript + ECharts
- **数据源**：AkShare、腾讯行情接口
- **AI**：DeepSeek API

## 项目结构

```
funds/
├── main.py                 # 应用入口
├── pyproject.toml          # 项目配置
├── .env                    # 环境变量配置
├── config/
│   └── prompts.json        # AI 提示词配置
├── database/               # 数据库模块
│   ├── connection.py       # 数据库连接
│   ├── models.py           # 数据模型
│   └── init_db.py          # 初始化脚本
├── routers/                # API 路由
│   ├── funds.py            # 基金管理
│   ├── holdings.py         # 持仓管理
│   ├── trades.py           # 交易记录
│   ├── market.py           # 行情数据
│   ├── etf.py              # ETF 行情
│   └── ai.py               # AI 建议
├── services/               # 业务逻辑
│   ├── fund_service.py     # 基金业务
│   ├── market_service.py   # 行情服务
│   ├── etf_service.py      # ETF 服务
│   ├── ai_service.py       # AI 服务
│   ├── market_sentiment_service.py  # 市场情绪
│   ├── fund_detail_service.py       # 基金详情
│   ├── news_service.py     # 行业新闻
│   └── sync_scheduler.py   # 定时同步
├── utils/                  # 工具函数
│   ├── helpers.py          # 通用工具
│   ├── indicators.py       # 技术指标计算
│   └── rate_limiter.py     # 请求限流
├── static/                 # 静态资源
│   ├── css/style.css       # 样式
│   └── js/                 # JavaScript
└── templates/              # 页面模板
    └── index.html          # 主页面
```

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置数据库

#### PostgreSQL 安装

**Windows:**
下载安装 [PostgreSQL](https://www.postgresql.org/download/windows/)

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu):**
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### 创建数据库

```sql
-- 登录 PostgreSQL
psql -U postgres

-- 创建数据库
CREATE DATABASE funds;

-- 创建用户（可选）
CREATE USER funds_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE funds TO funds_user;
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
# PostgreSQL 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=funds
DB_USER=postgres
DB_PASSWORD=your_password

# DeepSeek API 配置（可选，用于 AI 建议）
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

### 4. 启动应用

```bash
# 开发模式
uv run python main.py

# 或使用 uvicorn
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 即可使用。

## API 接口

### 基金管理
| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/funds` | GET | 获取所有基金 |
| `/api/funds` | POST | 添加基金 |
| `/api/funds/{code}` | GET/PUT/DELETE | 获取/更新/删除基金 |
| `/api/funds/search/{keyword}` | GET | 搜索基金 |

### 持仓与交易
| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/holdings` | GET | 获取所有持仓 |
| `/api/holdings/summary` | GET | 持仓汇总 |
| `/api/trades` | GET/POST | 交易记录 |

### 行情数据
| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/market/{code}/chart` | GET | 图表数据 |
| `/api/market/{code}/sync` | POST | 同步单只基金 |
| `/api/market/sync-all` | POST | 同步所有数据 |

### ETF 行情
| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/etf/analysis/{code}` | GET | ETF 分析数据（实时行情+资金流向） |

### AI 建议
| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/ai/suggest/{code}` | POST | 单只基金 AI 分析 |
| `/api/ai/analyze` | POST | 持仓组合分析 |
| `/api/ai/settings` | GET/POST | AI 配置 |
| `/api/ai/market-sentiment` | GET | 市场情绪数据 |
| `/api/ai/fund-detail/{code}` | GET | 基金详情 |
| `/api/ai/news` | GET | 相关行业新闻 |

## 使用说明

### 添加基金

1. 点击左侧「添加基金」按钮
2. 输入基金代码或名称搜索
3. 选择基金后自动添加并同步历史数据

### 设置关联 ETF

1. 选择一只基金
2. 点击「设置 ETF」按钮
3. 输入 ETF 代码（如 515030）
4. 系统自动获取 ETF 实时行情

### 记录交易

1. 选择一只基金
2. 点击「买入」或「卖出」按钮
3. 填写购买时间、金额、确认净值等信息
4. 系统自动计算份额并更新持仓

### AI 分析

1. 配置 DeepSeek API Key（设置按钮）
2. 选择基金后点击「分析」
3. 获取多维度综合分析：
   - 技术面分析（MA、RSI、MACD）
   - 风险评估（最大回撤、波动率、夏普比率）
   - ETF 行情分析（资金流向）
   - 市场情绪（涨跌家数、北向资金）
   - 行业新闻分析
   - 买卖建议和仓位配置

## AI 分析维度

| 维度 | 数据来源 | 说明 |
|------|---------|------|
| 技术指标 | 历史净值计算 | MA5/10/20、RSI、MACD |
| 风险指标 | 历史净值计算 | 最大回撤、波动率、夏普比率 |
| ETF 行情 | 腾讯行情接口 | 当日涨跌、主力资金流向 |
| 市场情绪 | AkShare | 涨跌家数比、北向资金 |
| 基金详情 | AkShare | 基金经理、规模、成立时间 |
| 行业新闻 | 东方财富 | 相关行业最新资讯 |

## 定时同步

系统会在以下时间自动同步净值数据：
- **14:50** - 盘中决策同步
- **15:30** - 收盘后同步

## 数据安全

- 数据库仅存储公开的基金数据和用户交易记录
- API Key 存储在本地 `.env` 文件中，不上传数据库
- 建议定期备份数据库

## License

MIT
