# 基金投资工具 - 实现文档

## 一、项目概述

### 1.1 项目名称
**Funds Manager** - 场外基金投资管理工具

### 1.2 项目目标
- 管理个人持有的场外基金（支付宝渠道）
- 查看基金历史走势
- 提供AI + 量化技术面的买入卖出建议

### 1.3 技术栈
| 层级 | 技术选型 |
|------|----------|
| 后端框架 | FastAPI |
| 数据库 | SQLite3 |
| 前端 | 原生 HTML + CSS + JavaScript + ECharts (CDN) |
| 数据源 | AkShare（开源金融数据接口库） |
| AI建议 | DeepSeek API |

### 1.4 前端依赖（CDN）
```html
<!-- ECharts 图表库 -->
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
```

无需 npm/node 环境，直接通过 CDN 引入使用。

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 持仓管理  │ │ 走势图表  │ │ 交易记录  │ │ AI建议   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP/REST API
┌─────────────────────────┴───────────────────────────────┐
│                    FastAPI 后端                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 持仓API   │ │ 行情API   │ │ 交易API   │ │ 建议API   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────┬───┘   │
└─────────────────────────┬─────────────────────────┼─────┘
                          │                         │
┌─────────────────────────┴───────────┐   ┌────────┴─────┐
│            SQLite3 数据库            │   │ DeepSeek API │
│  ┌──────────┐ ┌──────────┐ ┌──────┐ │   │   (AI 分析)   │
│  │ funds表   │ │ holdings表│ │ ...  │ │   └────────────┘
│  └──────────┘ └──────────┘ └──────┘ │
└─────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────┐
│                   AkShare 数据源                         │
│              (基金行情、历史净值数据)                     │
└─────────────────────────────────────────────────────────┘
```

---

## 三、数据库设计

### 3.1 表结构

#### funds 表（基金基础信息）
```sql
CREATE TABLE funds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code VARCHAR(6) UNIQUE NOT NULL,      -- 基金代码
    fund_name VARCHAR(100) NOT NULL,           -- 基金名称
    fund_type VARCHAR(50),                     -- 基金类型（股票型/混合型/债券型等）
    risk_level VARCHAR(10),                    -- 风险等级
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### holdings 表（当前持仓）
```sql
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code VARCHAR(6) NOT NULL,             -- 基金代码
    total_shares DECIMAL(18,4) NOT NULL,       -- 总份额
    cost_price DECIMAL(10,4) NOT NULL,         -- 成本价
    total_cost DECIMAL(18,2) NOT NULL,         -- 总投入金额
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
);
```

#### trades 表（交易记录）
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code VARCHAR(6) NOT NULL,             -- 基金代码
    trade_type VARCHAR(4) NOT NULL,            -- BUY / SELL
    shares DECIMAL(18,4) NOT NULL,             -- 份额
    price DECIMAL(10,4) NOT NULL,              -- 成交净值
    amount DECIMAL(18,2) NOT NULL,             -- 成交金额
    trade_date DATE NOT NULL,                  -- 交易日期
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
);
```

#### prices 表（历史净值缓存）
```sql
CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code VARCHAR(6) NOT NULL,             -- 基金代码
    net_value DECIMAL(10,4) NOT NULL,          -- 单位净值
    accum_value DECIMAL(10,4),                 -- 累计净值
    date DATE NOT NULL,                        -- 净值日期
    growth_rate DECIMAL(8,4),                  -- 日涨跌幅
    UNIQUE(fund_code, date),
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
);
```

---

## 四、API 接口设计

### 4.1 基金管理相关

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/funds` | 获取所有基金列表 |
| POST | `/api/funds` | 添加新基金 |
| GET | `/api/funds/{fund_code}` | 获取单个基金信息 |

### 4.2 持仓管理相关

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/holdings` | 获取所有持仓 |
| GET | `/api/holdings/{fund_code}` | 获取单只基金持仓 |
| PUT | `/api/holdings/{fund_code}` | 更新持仓信息 |

### 4.3 交易记录相关

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/trades` | 获取所有交易记录 |
| POST | `/api/trades` | 新增交易记录（买入/卖出） |
| GET | `/api/trades/{fund_code}` | 获取单只基金交易记录 |
| DELETE | `/api/trades/{trade_id}` | 删除交易记录 |

### 4.4 行情数据相关

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/market/{fund_code}` | 获取基金实时信息 |
| GET | `/api/market/{fund_code}/history` | 获取历史净值 |
| GET | `/api/market/{fund_code}/chart` | 获取图表数据 |

### 4.5 AI 建议相关

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/ai/suggest/{fund_code}` | 获取单只基金建议 |
| POST | `/api/ai/analyze` | 分析持仓组合 |

---

## 五、前端页面设计

### 5.1 整体布局结构

采用经典的**顶栏 + 左右分栏**布局：

```
┌──────────────────────────────────────────────────────────────────┐
│                         顶部导航栏                                │
│  📊 基金投资管理工具              [添加基金] [刷新] [设置]        │
├────────────────────────┬─────────────────────────────────────────┤
│                        │                                         │
│    左侧基金列表栏       │              右侧详情区域               │
│    (宽度约 280px)       │                                         │
│                        │  ┌─────────────────────────────────────┐│
│  ┌──────────────────┐  │  │          基金基本信息卡片            ││
│  │ 持仓汇总          │  │  │  基金名称 | 代码 | 类型 | 风险等级   ││
│  │ 总投入: ¥50,000   │  │  │  当前净值 | 日涨跌幅 | 更新时间      ││
│  │ 总市值: ¥52,300   │  │  └─────────────────────────────────────┘│
│  │ 总盈亏: +¥2,300   │  │                                         │
│  │ 盈亏比: +4.6%     │  │  ┌─────────────────────────────────────┐│
│  └──────────────────┘  │  │          持仓信息卡片                ││
│                        │  │  持有份额 | 成本价 | 市值 | 盈亏      ││
│  ┌──────────────────┐  │  │  [买入] [卖出] [查看交易]            ││
│  │ 🔍 搜索/添加基金  │  │  └─────────────────────────────────────┘│
│  └──────────────────┘  │                                         │
│                        │  ┌─────────────────────────────────────┐│
│  我的基金 (5)          │  │          净值走势图表                ││
│  ├─ 易方达蓝筹精选     │  │                                     ││
│  │  005827  +2.35%    │  │    [ECharts K线/折线图]              ││
│  ├─ 招商中证白酒       │  │                                     ││
│  │  161725  -1.20%    │  │    时间范围: [1月][3月][6月][1年][全部]│
│  ├─ 兴全合润          │  │  └─────────────────────────────────────┘│
│  │  163406  +0.85%    │  │                                         │
│  ├─ 中欧医疗健康      │  │  ┌─────────────────────────────────────┐│
│  │  003095  +3.12%    │  │          AI 建议卡片                  ││
│  └─ 广发纳斯达克      │  │  ┌───────────────────────────────────┐│
│     270042  +1.56%    │  │  │ 技术指标: MA5/MA10/MA20/MACD/RSI ││
│                        │  │  ├───────────────────────────────────┤│
│                        │  │  │ 买卖信号: 🔴 建议观望             ││
│                        │  │  │ 分析理由: RSI处于中性区间...      ││
│                        │  │  └───────────────────────────────────┘│
│                        │  └─────────────────────────────────────┘│
│                        │                                         │
│                        │  ┌─────────────────────────────────────┐│
│                        │  │          交易记录卡片                ││
│                        │  │  最近5笔交易记录预览                 ││
│                        │  │  [查看全部交易记录]                  ││
│                        │  └─────────────────────────────────────┘│
├────────────────────────┴─────────────────────────────────────────┤
│                         底部状态栏 (可选)                         │
│  最后更新: 2026-02-24 15:00  |  数据来源: AkShare                │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 布局说明

#### 5.2.1 顶部导航栏
- **左侧**：应用 Logo + 名称
- **右侧**：操作按钮（添加基金、刷新数据、设置）
- 高度固定：约 60px
- 背景：深色主题，固定在顶部

#### 5.2.2 左侧基金列表栏
- **持仓汇总卡片**：展示总投入、总市值、总盈亏、盈亏比例
- **搜索/添加输入框**：支持搜索基金代码或名称，快速添加
- **基金列表**：
  - 每个基金项显示：基金简称、代码、当日涨跌幅
  - 涨跌幅颜色区分：红涨绿跌
  - 选中状态高亮
  - 支持右键菜单：删除、查看详情
- 宽度固定：约 280px
- 支持滚动

#### 5.2.3 右侧详情区域
采用卡片式布局，根据选中基金动态展示：

**卡片1：基金基本信息**
- 基金全称、代码、类型、风险等级
- 当前单位净值、累计净值
- 日涨跌幅、更新时间

**卡片2：持仓信息**（仅持有基金显示）
- 持有份额、成本价、当前市值
- 盈亏金额、盈亏比例
- 操作按钮：买入、卖出、查看交易记录

**卡片3：净值走势图表**
- ECharts 图表：支持 K 线图 / 折线图切换
- 时间范围选择：1月、3月、6月、1年、全部
- 支持叠加技术指标（MA、BOLL等）

**卡片4：AI 建议**
- 技术指标面板：MA、MACD、RSI、KDJ 数值
- 买卖信号提示：买入/卖出/观望
- 分析理由说明

**卡片5：交易记录预览**
- 最近5笔交易记录
- "查看全部"按钮跳转到交易详情弹窗

### 5.3 交互设计

#### 5.3.1 基金列表交互
- 点击基金：右侧展示该基金详情
- 双击基金：快速买入弹窗
- 右键菜单：删除基金、导出数据
- 拖拽排序：调整基金显示顺序

#### 5.3.2 详情区域交互
- 卡片支持折叠/展开
- 图表支持缩放、拖动
- 数据支持导出（CSV）

#### 5.3.3 弹窗组件
- **添加基金弹窗**：搜索 → 选择 → 确认添加
- **买入/卖出弹窗**：输入份额/金额 → 确认交易
- **交易记录弹窗**：完整交易流水表格
- **设置弹窗**：DeepSeek API 配置

---

## 六、量化指标实现

### 6.1 技术指标

| 指标 | 计算方法 | 用途 |
|------|----------|------|
| MA5/MA10/MA20 | 移动平均线 | 判断趋势 |
| MACD | 指数平滑异同移动平均线 | 买卖信号 |
| RSI | 相对强弱指标 | 超买超卖 |
| KDJ | 随机指标 | 短期买卖点 |
| 布林带 | BOLL | 波动区间 |

### 6.2 建议规则示例

```
买入信号：
- RSI < 30 (超卖)
- 价格跌破布林带下轨
- MACD金叉

卖出信号：
- RSI > 70 (超买)
- 价格突破布林带上轨
- MACD死叉
- 达到目标收益率
```

---

## 七、项目目录结构

```
funds/
├── main.py                 # FastAPI 应用入口
├── pyproject.toml          # 项目配置
├── database/
│   ├── __init__.py
│   ├── connection.py       # 数据库连接
│   ├── models.py           # 数据模型
│   └── init_db.py          # 初始化脚本
├── routers/
│   ├── __init__.py
│   ├── funds.py            # 基金管理路由
│   ├── holdings.py         # 持仓路由
│   ├── trades.py           # 交易路由
│   ├── market.py           # 行情路由
│   └── ai.py               # AI建议路由
├── services/
│   ├── __init__.py
│   ├── fund_service.py     # 基金业务逻辑
│   ├── market_service.py   # 行情数据服务
│   └── ai_service.py       # AI分析服务
├── utils/
│   ├── __init__.py
│   ├── indicators.py       # 技术指标计算
│   └── helpers.py          # 工具函数
├── static/
│   ├── css/
│   │   └── style.css       # 样式文件
│   └── js/
│       ├── app.js          # 主程序
│       └── api.js          # API封装
└── templates/
    └── index.html          # 主页面（含 ECharts CDN 引入）
```

---

## 八、数据来源与缓存策略

### 8.1 AkShare 特性与限制

AkShare 是优秀的开源金融数据接口库，但需要注意以下问题：

| 问题 | 说明 |
|------|------|
| 访问速度 | 依赖第三方网站，响应较慢（通常 1-3 秒/次） |
| 频率限制 | 高频访问可能触发反爬机制，导致 IP 被封 |
| 数据时效 | 场外基金 T+1 机制，净值每日更新一次 |

### 8.2 缓存策略设计

#### 8.2.1 核心原则
- **T+1 特性**：场外基金净值每日仅更新一次（收盘后）
- **历史数据不变**：历史净值数据不会变化，永久缓存
- **增量更新**：只获取缺失日期的数据

#### 8.2.2 数据分层缓存

```
┌─────────────────────────────────────────────────────────────┐
│                      缓存层级设计                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Level 1: 内存缓存（可选）                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 当前会话的热点数据，如当前查看基金的实时净值            │   │
│  │ 过期时间: 5分钟                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  Level 2: SQLite 本地数据库                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 历史净值数据（永久存储）                               │   │
│  │ 基金基础信息（长期存储）                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  Level 3: AkShare 远程接口                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 仅在本地无数据或数据过期时请求                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 8.2.3 缓存更新规则

| 数据类型 | 更新频率 | 缓存策略 |
|----------|----------|----------|
| 历史净值 | 永不变化 | 永久缓存，增量补充 |
| 当日净值 | 每日一次 | 当日有效，次日重取 |
| 基金基础信息 | 极少变化 | 30天过期重取 |
| 基金列表 | 极少变化 | 本地存储，手动更新 |

### 8.3 增量更新机制

#### 8.3.1 历史净值增量更新

```python
def sync_fund_history(fund_code: str):
    """增量同步基金历史净值"""
    # 1. 查询本地最新净值日期
    last_date = db.get_latest_price_date(fund_code)
    
    # 2. 计算需要获取的日期范围
    start_date = last_date + 1 day if last_date else "基金成立日"
    end_date = today
    
    # 3. 只获取缺失的数据
    if start_date <= end_date:
        new_data = akshare.get_fund_history(fund_code, start_date, end_date)
        db.batch_insert_prices(new_data)
```

#### 8.3.2 启动时同步流程

```
启动应用
    │
    ├── 遍历所有持仓基金
    │       │
    │       ├── 检查本地最新净值日期
    │       │
    │       ├── 如果不是今天且当前时间 > 15:00
    │       │       │
    │       │       └── 请求缺失日期的净值数据
    │       │
    │       └── 更新本地数据库
    │
    └── 返回缓存数据给前端
```

### 8.4 请求频率控制

#### 8.4.1 请求限流器

```python
import time
from threading import Lock

class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval  # 最小请求间隔（秒）
        self.last_request_time = 0
        self.lock = Lock()
    
    def acquire(self):
        """获取请求许可，必要时等待"""
        with self.lock:
            now = time.time()
            wait_time = self.min_interval - (now - self.last_request_time)
            if wait_time > 0:
                time.sleep(wait_time)
            self.last_request_time = time.time()

# 全局限流器实例
akshare_limiter = RateLimiter(min_interval=1.5)  # 1.5秒间隔
```

#### 8.4.2 批量请求优化

```python
async def batch_sync_funds(fund_codes: list[str]):
    """批量同步多只基金（串行+限流）"""
    results = []
    for code in fund_codes:
        akshare_limiter.acquire()  # 限流
        try:
            data = await sync_single_fund(code)
            results.append(data)
        except Exception as e:
            results.append({"code": code, "error": str(e)})
    return results
```

#### 8.4.3 失败重试机制

```python
async def fetch_with_retry(fetch_func, max_retries=3, backoff=2):
    """带退避的重试机制"""
    for attempt in range(max_retries):
        try:
            akshare_limiter.acquire()
            return await fetch_func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff ** attempt  # 指数退避
            await asyncio.sleep(wait_time)
```

### 8.5 数据同步策略

#### 8.5.1 同步时机

| 触发场景 | 同步内容 | 说明 |
|----------|----------|------|
| 应用启动 | 所有持仓基金 | 后台静默同步 |
| 添加新基金 | 该基金历史数据 | 全量获取 |
| 手动刷新 | 当前查看基金 | 强制更新 |
| 定时任务（14:50） | 所有持仓基金 | 盘中同步，为 15:00 前操作决策提供数据 |
| 定时任务（15:30） | 所有持仓基金 | 收盘后同步，获取当日最新净值 |

#### 8.5.2 后台同步服务

```python
import asyncio
from datetime import datetime

class SyncScheduler:
    """后台同步调度器"""
    
    SYNC_TIMES = ["14:50", "15:30"]  # 盘中决策 + 收盘后更新
    SYNCED_TODAY = set()  # 记录今日已同步的时间点
    
    async def start(self):
        """启动定时同步"""
        while True:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            # 检查是否到达同步时间
            for sync_time in self.SYNC_TIMES:
                if current_time == sync_time and sync_time not in self.SYNCED_TODAY:
                    await self.sync_all_funds()
                    self.SYNCED_TODAY.add(sync_time)
            
            # 每天 00:00 重置同步标志
            if current_time == "00:00":
                self.SYNCED_TODAY.clear()
            
            await asyncio.sleep(30)  # 每30秒检查一次
    
    async def sync_all_funds(self):
        """同步所有持仓基金数据"""
        funds = get_all_fund_codes()
        for fund_code in funds:
            await sync_fund_history(fund_code)
```

#### 8.5.3 同步策略说明

```
每日同步时间线：

09:30  开盘
  │
  │
14:50  第一次同步 ← 获取截至昨日的历史数据
  │       └── 目的：为 15:00 前的操作决策提供参考
  │
15:00  交易截止时间（场外基金申购/赎回截止）
  │
  │
15:00-15:30  基金公司计算当日净值
  │
  │
15:30  第二次同步 ← 获取当日最新净值
  │       └── 目的：更新当日收益情况
  │
  │
20:00+  各平台更新净值数据
  │
```

### 8.6 数据库扩展设计

#### 8.6.1 新增缓存元数据表

```sql
CREATE TABLE cache_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code VARCHAR(6) NOT NULL UNIQUE,
    last_sync_date DATE,                    -- 最后同步日期
    last_sync_time TIMESTAMP,               -- 最后同步时间
    sync_status VARCHAR(20),                -- synced / pending / failed
    error_message TEXT,                     -- 错误信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
);
```

#### 8.6.2 基金信息表扩展

```sql
ALTER TABLE funds ADD COLUMN last_price_date DATE;      -- 最新净值日期
ALTER TABLE funds ADD COLUMN last_net_value DECIMAL(10,4); -- 最新净值
ALTER TABLE funds ADD COLUMN last_growth_rate DECIMAL(8,4); -- 最新涨跌幅
ALTER TABLE funds ADD COLUMN info_updated_at TIMESTAMP;    -- 信息更新时间
```

### 8.7 API 层缓存处理

```python
@router.get("/api/market/{fund_code}/history")
async def get_fund_history(
    fund_code: str,
    start_date: str = None,
    end_date: str = None,
    force_refresh: bool = False
):
    """获取历史净值（优先从缓存读取）"""
    
    # 1. 尝试从本地数据库获取
    cached_data = db.get_prices(fund_code, start_date, end_date)
    
    # 2. 检查是否需要更新
    if force_refresh or need_sync(fund_code):
        # 后台异步更新
        asyncio.create_task(sync_fund_history(fund_code))
    
    # 3. 返回缓存数据（即使不是最新）
    return {
        "data": cached_data,
        "is_latest": is_data_latest(fund_code),
        "last_sync": get_last_sync_time(fund_code)
    }
```

### 8.8 错误处理与降级

```python
class DataFetchError(Exception):
    """数据获取异常"""
    pass

async def get_fund_data_with_fallback(fund_code: str):
    """带降级策略的数据获取"""
    try:
        # 尝试从 AkShare 获取
        return await fetch_from_akshare(fund_code)
    except RateLimitError:
        # 降级：返回本地缓存
        cached = get_from_cache(fund_code)
        if cached:
            return cached
        raise DataFetchError("数据获取失败，请稍后重试")
    except NetworkError:
        # 网络错误：返回缓存并标记
        return get_from_cache(fund_code) or raise DataFetchError("网络异常")
```

---

## 九、AI 建议实现方案

### 9.1 方案概述

采用 **DeepSeek API** 实现智能投资建议，结合技术指标数据进行综合分析。

### 9.2 DeepSeek API 集成

#### 9.2.1 API 配置

```python
# config.py
DEEPSEEK_API_KEY = "your-api-key"  # 从环境变量或配置文件读取
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # 或 deepseek-coder
```

#### 9.2.2 API 调用封装

```python
import httpx

class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def chat(self, messages: list, temperature: float = 0.7) -> str:
        """调用 DeepSeek Chat API"""
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature
            }
        )
        result = response.json()
        return result["choices"][0]["message"]["content"]
```

#### 9.2.3 Prompt 模板设计

```python
ANALYSIS_PROMPT = """你是一位专业的基金投资顾问。请根据以下数据分析该基金的投资建议。

## 基金基本信息
- 基金名称: {fund_name}
- 基金代码: {fund_code}
- 基金类型: {fund_type}
- 风险等级: {risk_level}

## 技术指标数据
- 当前净值: {current_value}
- 近5日涨跌幅: {change_5d}%
- 近20日涨跌幅: {change_20d}%
- MA5: {ma5}
- MA10: {ma10}
- MA20: {ma20}
- RSI(14): {rsi}
- MACD: {macd}
- MACD Signal: {macd_signal}

## 持仓信息（如有）
- 持有份额: {shares}
- 成本价: {cost_price}
- 当前市值: {market_value}
- 盈亏比例: {profit_ratio}%

## 请回答
1. 当前技术面分析（趋势判断、支撑压力位）
2. 买卖建议（强烈买入/买入/持有/卖出/强烈卖出）
3. 建议理由（分点说明）
4. 风险提示

请用简洁专业的语言回答，不要过于冗长。
"""
```

### 9.3 AI 服务实现

```python
# services/ai_service.py

class AIService:
    def __init__(self, deepseek_client: DeepSeekClient):
        self.client = deepseek_client
    
    async def analyze_fund(self, fund_code: str) -> dict:
        """分析单只基金"""
        # 1. 获取基金数据
        fund_info = await self.get_fund_info(fund_code)
        indicators = await self.calculate_indicators(fund_code)
        holding = await self.get_holding_info(fund_code)
        
        # 2. 构建提示词
        prompt = ANALYSIS_PROMPT.format(
            fund_name=fund_info["name"],
            fund_code=fund_code,
            # ... 其他参数
        )
        
        # 3. 调用 AI 分析
        analysis = await self.client.chat([
            {"role": "system", "content": "你是专业的基金投资顾问。"},
            {"role": "user", "content": prompt}
        ])
        
        return {
            "fund_code": fund_code,
            "analysis": analysis,
            "indicators": indicators,
            "timestamp": datetime.now()
        }
```

### 9.4 设置页面配置

用户可在设置页面配置自己的 DeepSeek API Key：

```
┌─────────────────────────────────┐
│         设置                    │
├─────────────────────────────────┤
│  DeepSeek API Key:              │
│  ┌───────────────────────────┐  │
│  │ sk-xxxxxxxxxxxxxxxxxxxxx  │  │
│  └───────────────────────────┘  │
│                                 │
│  API 地址:                      │
│  ┌───────────────────────────┐  │
│  │ https://api.deepseek.com  │  │
│  └───────────────────────────┘  │
│                                 │
│  模型选择:                      │
│  ○ deepseek-chat               │
│  ○ deepseek-coder              │
│                                 │
│        [保存配置]               │
└─────────────────────────────────┘
```

### 9.5 数据库新增配置表

```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(50) UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 存储敏感信息时建议加密
INSERT INTO settings (key, value) VALUES ('deepseek_api_key', '');
INSERT INTO settings (key, value) VALUES ('deepseek_base_url', 'https://api.deepseek.com/v1');
INSERT INTO settings (key, value) VALUES ('deepseek_model', 'deepseek-chat');
```

---

## 十、开发计划

### 第一阶段：基础框架
1. 项目结构搭建
2. 数据库设计与初始化（含缓存元数据表）
3. FastAPI 基础路由
4. 请求限流器实现

### 第二阶段：核心功能
1. 基金管理（增删改查）
2. 交易记录管理
3. 持仓计算逻辑
4. 本地数据持久化

### 第三阶段：数据同步与缓存
1. AkShare 接口封装
2. 增量更新机制实现
3. 后台同步调度器
4. 失败重试与降级策略
5. API 层缓存处理

### 第四阶段：行情展示
1. ECharts 图表集成
2. 历史走势展示
3. 时间范围切换
4. 数据导出功能

### 第五阶段：AI建议
1. 技术指标计算
2. 买卖信号规则
3. 建议页面展示
4. LLM 接口集成（可选）

### 第六阶段：优化完善
1. 前端美化
2. 性能优化
3. 错误处理
4. 用户体验改进

---

## 十一、已确认事项

以下事项已确认，无需再讨论：

| 事项 | 确认结果 |
|------|----------|
| AI 建议方案 | 使用 DeepSeek API，用户自行配置 API Key |
| 多用户支持 | 不需要，单机个人使用 |
| 定投功能 | 不需要，用户自行查看操作 |
| 移动端适配 | 不需要，仅桌面浏览器使用 |
| 同步时间 | 每日两次：14:50（盘中决策）、15:30（收盘更新） |
