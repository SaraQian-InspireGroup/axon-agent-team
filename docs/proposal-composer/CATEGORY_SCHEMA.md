# Product Category — 数据契约（设计参考）

> 运行时 category 路由：`knowledge/categories.yaml`  
> 运行时模版：`knowledge/templates/{template_id}/`

---

## 分工

| 层 | 位置 |
|----|------|
| 产品目录 | PostgreSQL `mdm_services` / `mdm_packages` |
| Category 路由 | `categories.yaml` |
| 模版（静态 + placeholder） | `templates/{id}/template.yaml` + `proposal.md` |
| 知识检索 | `knowledge-index.yaml`（仅 triggers） |

模版 placeholder 类型见 [PROPOSAL_COMPOSER_DESIGN.md §6](../PROPOSAL_COMPOSER_DESIGN.md#6-模版与知识索引).

---

*整体设计见 [PROPOSAL_COMPOSER_DESIGN.md](../PROPOSAL_COMPOSER_DESIGN.md)*
