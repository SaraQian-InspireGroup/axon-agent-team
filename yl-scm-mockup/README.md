# 伊利供应链 Mockup 前端

独立的 Pilot 项目，用于复刻「供应链数字化 OPERATION PLATFORM」界面 Mockup。与仓库内 `frontend/` **无代码依赖**，可单独 `npm install && npm run build` 部署；Nova 对话通过 HTTP 调用同仓库 `backend/` 的 Agent API（运行时依赖，非构建耦合）。

## 技术栈

- React 19 + TypeScript
- Vite 8
- Tailwind CSS 4
- lucide-react
- react-markdown + remark-gfm（Nova 助手回复渲染）

## 开发

```bash
cd yl-scm-mockup
npm install
npm run dev
```

默认端口 **5174**。开发模式下 Vite 将 `/api` 代理到 `http://127.0.0.1:8000`，需同时启动 backend：

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

## 独立部署

```bash
npm run build
npm run preview   # 或把 dist/ 交给任意静态托管
```

生产环境请配置 backend API 地址（二选一）：

1. 复制 `.env.example` 为 `.env`，设置 `VITE_API_BASE_URL=https://your-api-host/api/v1`
2. 或在 Nginx 等反向代理上将 `/api` 转发到 Agent Platform backend

构建产物仅包含静态资源，不依赖 monorepo 内其他前端包。

## Nova（yl-worker1）

- Header 右侧 AI 图标打开 Nova 面板
- 固定绑定 backend agent `yl-worker1`（通过 `/api/v1/agents` 按 slug 解析）
- 支持：会话历史弹窗、新建会话、SSE 流式对话、Reasoning/Tool 折叠步骤、暂停取消
- 助手回复使用 Markdown 渲染（表格、列表、标题等）

## 页面说明

- **计划中心**：正向分货销售仓调拨、全国库存监控等 Tab
- **履约中心**：分仓补录单
- 其余菜单为 disabled 占位

Mock 表格数据来自 `src/data/mockData.ts`；Nova 对话数据来自 backend。
