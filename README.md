# 场外基金投资管理工具

一个简洁实用的场外基金投资管理工具，支持持仓管理、行情查看、交易记录和 AI 投资建议。

## 功能特性

- **基金管理**：添加、删除基金，自动获取基金信息
- **持仓管理**：记录持仓份额、成本，实时计算盈亏
- **交易记录**：买入卖出记录，自动更新持仓
- **行情数据**：历史净值图表，技术指标（MA/RSI/MACD）
- **AI 建议**：基于 DeepSeek 的投资分析建议
- **定时同步**：每日自动同步最新净值数据

## 技术栈

- **后端**：Python 3.13 + FastAPI + Uvicorn
- **数据库**：PostgreSQL
- **前端**：原生 HTML/CSS/JavaScript + ECharts
- **数据源**：AkShare
- **AI**：DeepSeek API

## 项目结构

```
funds/
├── main.py              # 应用入口
├── pyproject.toml       # 项目配置
├── .env                 # 环境变量配置
├── database/            # 数据库模块
│   ├── connection.py    # 数据库连接
│   ├── models.py        # 数据模型
│   └── init_db.py       # 初始化脚本
├── routers/             # API 路由
│   ├── funds.py         # 基金管理
│   ├── holdings.py      # 持仓管理
│   ├── trades.py        # 交易记录
│   ├── market.py        # 行情数据
│   └── ai.py            # AI 建议
├── services/            # 业务逻辑
│   ├── fund_service.py  # 基金业务
│   ├── market_service.py# 行情服务
│   ├── ai_service.py    # AI 服务
│   └── sync_scheduler.py# 定时同步
├── utils/               # 工具函数
│   ├── helpers.py       # 通用工具
│   ├── indicators.py    # 技术指标计算
│   └── rate_limiter.py  # 请求限流
├── static/              # 静态资源
│   ├── css/style.css    # 样式
│   └── js/              # JavaScript
└── templates/           # 页面模板
    └── index.html       # 主页面
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

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/funds` | GET | 获取所有基金 |
| `/api/funds` | POST | 添加基金 |
| `/api/funds/{code}` | DELETE | 删除基金 |
| `/api/funds/search/{keyword}` | GET | 搜索基金 |
| `/api/holdings` | GET | 获取所有持仓 |
| `/api/holdings/summary` | GET | 持仓汇总 |
| `/api/trades` | GET/POST | 交易记录 |
| `/api/market/{code}/chart` | GET | 图表数据 |
| `/api/market/sync-all` | POST | 同步所有数据 |
| `/api/ai/suggest/{code}` | POST | AI 分析建议 |
| `/api/ai/settings` | GET/POST | AI 配置 |

## 使用说明

### 添加基金

1. 点击左侧「添加基金」按钮
2. 输入基金代码或名称搜索
3. 选择基金后自动添加并同步历史数据

### 记录交易

1. 选择一只基金
2. 点击「买入」或「卖出」按钮
3. 填写购买时间、金额、确认净值等信息
4. 系统自动计算份额并更新持仓

### 查看 AI 建议

1. 配置 DeepSeek API Key（设置按钮）
2. 选择基金后点击「AI 分析」
3. 获取基于技术指标的投资建议

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
