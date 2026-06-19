# Proposal draft schema

`proposal_draft` is the editable display-layer document. The right-side Proposal Preview is rendered directly from this object.

**Guardrails**: patch only concrete draft nodes that the user can see/edit. For catalog additions, use the add-package/add-service materializer tools.

## Template contract

After category/template is known, initialize the draft and read:

```text
templates/{template_id}/template.yaml
```

via `read_knowledge`. That file defines section kinds, default enabled flags, editability, materializers, and derivations. Full workflow: **`references/template-contract.md`**.

## Common paths

| Path | Purpose |
|------|---------|
| `/meta/category_id` | MDM catalog scope |
| `/meta/template_id` | Document template |
| `/facts/client/*` | Company and contact |
| `/document/sections/{index}/enabled` | Section visibility |
| `/document/sections/{index}/content` | Editable markdown/static block content |
| `/document/sections/{index}/tables/{index}/title` | Fee table heading |
| `/document/sections/{index}/tables/{index}/rows/{index}/service_name` | Client-facing service name |
| `/document/sections/{index}/tables/{index}/rows/{index}/scope_of_work` | Client-facing SOW |
| `/document/sections/{index}/tables/{index}/rows/{index}/price/amount` | Manual price amount |
| `/document/sections/{payment_options_index}/options` | Optional derived payment option configurations, e.g. Option A / Option B |
| `/document/sections/{payment_options_index}/options/{index}/rows` | Payment option rows keyed by fee table `group_id`; each row is a fee-table summary, not a service row |

## JSON Patch examples

```json
[
  {"op": "replace", "path": "/facts/client/company_name", "value": "Acme Ltd"},
  {"op": "replace", "path": "/document/sections/1/tables/0/title", "value": "Corporate Advisory"},
  {"op": "replace", "path": "/document/sections/1/tables/0/rows/0/service_name", "value": "Application - Substituted Accounting Period"},
  {"op": "replace", "path": "/document/sections/1/tables/0/rows/0/price/amount", "value": 1200},
  {"op": "add", "path": "/document/sections/2/options", "value": [
    {"option_id": "option_a", "label": "Payment Option A - One-off Payment", "rows": [
      {"group_id": "table_css", "label": "CSS Package 2", "once_off": 4500, "monthly": 0, "quarterly": 0, "annual": 0}
    ]},
    {"option_id": "option_b", "label": "Payment Option B - Monthly Recurring", "rows": [
      {"group_id": "table_css", "label": "CSS Package 2", "once_off": 0, "monthly": 360, "quarterly": 0, "annual": 0}
    ]}
  ]}
]
```

Prefer `add_package_to_proposal_draft` / `add_service_to_proposal_draft` for MDM catalog additions instead of manually constructing rows.

## Readiness

`render_preview` and `generate_document` compute readiness from the draft. Live panel renders the draft even when incomplete.
