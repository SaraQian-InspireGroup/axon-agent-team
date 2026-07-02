# 伊利供应链 Mockup 前端

独立的 Pilot 项目，用于复刻「供应链数字化 OPERATION PLATFORM」界面 Mockup。与仓库内 `frontend/` 和 `backend/` **无任何代码或构建关联**，可随时迁移或删除。

## 技术栈

与主 `frontend` 一致：

- React 19 + TypeScript
- Vite 8
- Tailwind CSS 4
- lucide-react

## 开发

```bash
cd yl-scm-mockup
npm install
npm run dev
```

默认端口 **5174**（避免与主 frontend 的 5173 冲突）。

## 构建

```bash
npm run build
npm run preview
```

## 页面说明

- **顶部 Header**：平台名称、计划中心/履约中心 Tab、用户信息（固定）
- **左侧 Side Nav**：完整菜单结构；仅「补货管理 → 正向分货销售仓调拨」高亮可用；底部可折叠/展开
- **内容 Tab**（冻结不随页面滚动）：
  1. **正向分货销售仓调拨** — 筛选：事业部/产品名称/基地仓/销售分仓/产品系列
  2. **全国库存监控** — 筛选：日期/事业部/产品名称/产品系列
  3. 其余 Tab 为 disabled 占位

## 未来对接

可在 `panel-scroll` 区域或独立路由嵌入 backend agent 面板；当前数据来自 `src/data/mockData.ts`。
