# proposal-composer

BD/销售跨 region 出具 Proposal 的 agent（**P0 已实施**：state/patch 管线 + profile + skills）。

## 平台集成

| 组件 | 位置 |
|------|------|
| 派生管线 | `backend/app/proposal/` |
| Builtin tools | `list_categories`, `read_knowledge`, `get_proposal_schema`, `get_proposal_state`, `patch_proposal_state`, `render_preview`, `generate_document` |
| 会话持久化 | `Chat.session_state.proposal_state` |

## `knowledge/` 布局（运行时数据）

```
knowledge/
  categories.yaml              # category 路由
  knowledge-index.yaml         # 选型 → required doc / credential（极简）
  templates/{template_id}/
    template.yaml              # placeholder 契约
    proposal.md                # 正文 + {{placeholders}}
    blocks/*.md                # static 片段
  peripheral/                  # 知识正文（required-docs、credentials、team-bios）
```

| 数据 | 来源 |
|------|------|
| 产品 SKU / package | PostgreSQL `mdm_*`（Postgres MCP + SQL） |
| Category 路由 | `categories.yaml` |
| 模版骨架与 placeholder | `templates/{id}/template.yaml` + `proposal.md` |
| 触发型知识 | `knowledge-index.yaml` → `peripheral/` |

设计说明：[docs/PROPOSAL_COMPOSER_DESIGN.md](../../../docs/PROPOSAL_COMPOSER_DESIGN.md)

## 已实施模版

| template_id | category | 说明 |
|-------------|----------|------|
| `harneys-bvi` | `harneys-bvi` | 统一 `{{solution_and_price}}`；`fee_layout.group_by: service_group` |
| `au-advisory` | `au-services` | 统一 `{{solution_and_price}}`；`department_team` + scope |
