# Proposal state schema

Machine-readable contract: **`get_proposal_schema`** returns JSON Schema Draft 2020-12.

## Tools

| Tool | Role |
|------|------|
| `get_proposal_schema` | JSON Schema (editable vs `readOnly`) |
| `get_proposal_state` | Read full state or subtree via JSON Pointer |
| `patch_proposal_state` | RFC 6902 JSON Patch (`add` / `remove` / `replace` / …) |

**Guardrails**: only schema paths without `readOnly` accept patches; invalid patches return `http_status: 422` with `errors[]`. After a successful patch the platform recomputes derived fields (`line_items`, `pricing.computed`, `completeness`, …).

## Common paths

| Path | Purpose |
|------|---------|
| `/proposal_meta/category_id` | MDM catalog scope |
| `/proposal_meta/template_id` | Document template |
| `/client/*` | Company and contact |
| `/pricing_facts/*` | TIERED/MATRIX inputs (e.g. `share_count`) |
| `/selection/selected_packages` | Package IDs |
| `/selection/selected_skus` | Ad-hoc SKUs |
| `/pricing/overrides/{sku}` | Manual price override |
| `/enabled_sections` | Optional template sections |
| `/fee_description` | Intro paragraph above fee tables (not `###` table heading) |
| `/fee_layout/group_labels/{group_id}` | Fee table heading override |
| `/fee_layout/custom_groups` | Split/reassign fee tables |
| `/payment_options/options` | Payment option rows; non-empty → auto-enables Fee summary section |
| `/payment_options/overrides` | Payment summary tweaks |
| `/appendix` | Appendix content |

## JSON Patch examples

```json
[
  {"op": "replace", "path": "/proposal_meta/category_id", "value": "au-services"},
  {"op": "replace", "path": "/client/company_name", "value": "Acme Ltd"},
  {"op": "add", "path": "/selection/selected_skus/-", "value": "AU-TAX"},
  {"op": "replace", "path": "/fee_layout/group_labels/additional_services", "value": "Corporate Advisory"}
]
```

Append SKU (keep existing): `add` to `/selection/selected_skus/-`. Replace entire list: `replace` on `/selection/selected_skus`.

## Read-only (derived)

`readOnly` in schema — do not patch; platform fills after write:

- `/selection/expanded_skus`
- `/pricing/computed`, `/pricing/explanations`, `/pricing/recurring_schedule`
- `/line_items`
- `/payment_options/resolved` — empty until Fee summary optional section is active
- `/resolved_placeholders`, `/peripheral`, `/completeness`, `/active_optional_sections`
- `/proposal_meta/stage`, `/artifacts`

## Completeness

Read `/completeness` after patch. `generate_document` respects `ready_to_generate` unless `force=true`. Live panel renders draft even when incomplete.
