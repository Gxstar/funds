# frontend

Vue 3 + Vite 7 SPA，Element Plus 2 中文 UI，ECharts 6 图表。

## 技术选型

| 用途 | 库 |
|---|---|
| 框架 | Vue 3 (Composition API, `<script setup>`) |
| 路由 | Vue Router 5 (createWebHistory) |
| 状态 | Pinia (组合式 API) |
| UI | Element Plus 2.13 + zhCn 中文语言包 |
| 图标 | @element-plus/icons-vue (全局注册) |
| 图表 | ECharts 6 |
| Markdown | marked 15 (AI 分析渲染) |
| 构建 | Vite 7, vite-plugin-vue-devtools |
| HTTP | 原生 fetch (无 axios) |

## 目录结构

```
src/
  main.js              # 入口：createApp + 插件注册 + Element Plus 中文配置
  App.vue              # 主布局：header + sidebar(FundList) + router-view + footer
  api/index.js         # 按领域分组的 fetch 封装：fundAPI, holdingAPI, tradeAPI, marketAPI, aiAPI, settingsAPI, etfAPI
  router/index.js      # 路由：/ → HomeView, /fund/:code → FundDetailView
  stores/
    funds.js           # useFundStore — 基金列表、持仓汇总、图表数据、ETF 数据、交易、AI 分析
    settings.js        # useSettingsStore — AI 设置、数据库配置、提示词
  utils/format.js      # formatCurrency / formatPercent / formatDate / formatDateTime
  views/
    HomeView.vue       # 仪表盘：统计卡片、大盘指数、饼图/玫瑰图、组合净值走势、持仓列表、交易记录、收益排行
    FundDetailView.vue # 基金详情：净值图表(MA+MACD+RSI+买卖标记)、交易录入、ETF 行情、AI 分析
  components/
    FundList.vue       # 侧栏：搜索、基金列表、汇总卡片、AI 分析按钮
    SettingsDrawer.vue # 抽屉设置页：API Key、DB 配置、提示词模板（懒加载）
    AddFundDialog.vue  # 搜索基金 + 添加对话框
```

## 命令

```sh
pnpm dev        # 开发服务器 → port 3000，/api 代理到 localhost:8000
pnpm build      # 构建 → dist/
pnpm preview    # 预览构建产物
```
