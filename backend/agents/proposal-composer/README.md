# proposal-composer

BD/销售跨 jurisdiction 出具 Proposal 的 agent（draft-first proposal composer）。

## 平台集成

| 组件 | 位置 |
|------|------|
| Draft 管线 | `backend/app/proposal/draft.py` |
| MDM catalog | `backend/app/mdm/catalog_service.py` + tools `list_mdm_packages`, `get_mdm_package_services`, `search_mdm_services`, `list_mdm_packages_for_services` |
| Builtin tools | `list_templates`, `read_knowledge`, MDM catalog tools (above), `initialize_proposal_draft`, `get_proposal_draft`, `patch_proposal_draft`, `add_package_to_proposal_draft`, `add_services_to_proposal_draft`, `enable_proposal_draft_section`, `render_preview`, `generate_document` |
| 会话持久化 | `Chat.session_state.proposal_draft` |

## `knowledge/` 布局（运行时数据）

```
knowledge/
  knowledge-index.yaml         # 选型 → required doc / credential（极简）
  templates/{template_id}/
    template.yaml              # draft sections 契约
    blocks/*.md                # static 片段
  peripheral/                  # 知识正文（required-docs、credentials、team-bios）
```

| 数据 | 来源 |
|------|------|
| 产品 SKU / package | PostgreSQL `mdm_*` via **MDM catalog builtin tools** (see `proposal-mdm-catalog` skill) |
| Template 入口、catalog filter、draft sections | `templates/{id}/template.yaml` |
| Agent 读模版契约 | `read_knowledge("templates/{template_id}/template.yaml")` — 见 skill `references/template-contract.md` |
| 触发型知识 | `knowledge-index.yaml` → `peripheral/` |

设计说明：[docs/PROPOSAL_COMPOSER_DESIGN.md](../../../docs/PROPOSAL_COMPOSER_DESIGN.md)

## 已实施模版

| template_id | catalog filter | 说明 |
|-------------|----------|------|
| `harneys-bvi` | `jurisdiction=BVI`, `bu=Harneys` | draft `fee_section` |
| `au-advisory` | `jurisdiction=AU`, `bu=Incorp AU` | draft `fee_section` + optional `payment_options` derived section |
