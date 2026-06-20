# Proposal draft schema

`proposal_draft` is the editable display-layer document. The right-side Proposal Preview is rendered directly from this object.

**Guardrails**: patch only concrete draft nodes that the user can see/edit. For catalog additions, use the add-package/add-service materializer tools.

## Preview row numbers (e.g. 2.2)

The live panel shows **`{tableIndex}.{rowSub} service_name`** on AU frequency fee tables. Those numbers are **not** fields in draft JSON.

Before patching a row the user identified by panel number, read the draft and map display ref → physical row. See **`references/fee-table-display-index.md`** (workflow, 0-based JSON Pointer paths, empty-table skip rule, BVI exception).

Stable identifiers when the user provides them: `rows[].source.sku`, `rows[].id`, or `service_name` + table `title`.

## Template contract

After template is known, initialize the draft and read:

```text
templates/{template_id}/template.yaml
```

via `read_knowledge`. That file defines section kinds, default enabled flags, editability, materializers, and derivations. Full workflow: **`references/template-contract.md`**.

## Common paths

| Path | Purpose |
|------|---------|
| `/meta/template_id` | Document template |
| `/facts/client/*` | Company and contact |
| `/facts/client/company_name` | Optional legal/client company name |
| `/facts/client/short_name` | Optional client short name |
| `/facts/client/address` | Optional client address |
| `/facts/client/contract_name` | Optional contract/contact name |
| `/facts/client/contract_title` | Optional contract/contact title |
| `/facts/client/contract_email` | Optional contract/contact email |
| `/document/sections/{index}/enabled` | Section visibility |
| `/document/sections/{index}/content` | Editable markdown/static block content |
| `/document/sections/{index}/tables/{index}/title` | Fee table heading |
| `/document/sections/{index}/tables/{index}/rows/{index}/service_name` | Client-facing service name |
| `/document/sections/{index}/tables/{index}/rows/{index}/description` | MDM `description` (fee table when `fee_layout.service_columns.description: true`) |
| `/document/sections/{index}/tables/{index}/rows/{index}/scope_of_work` | MDM SOW (fee table when `fee_layout.service_columns.scope_of_work: true`) |
| `/document/sections/{index}/tables/{index}/rows/{index}/footnotes` | Client-facing footnote text (from MDM; aggregated at table end when `fee_layout.footnotes: aggregate`) |
| `/document/sections/{index}/tables/{index}/rows/{index}/price/amount` | Numeric total used for summaries (`price_amount` semantics) |
| `/document/sections/{index}/tables/{index}/rows/{index}/price/fee_raw` | Client-facing price text for non-`FIXED` rows; copied from MDM at materialize |
| `/document/sections/{index}/tables/{index}/rows/{index}/price/pricing_type` | `FIXED`, `UNIT_RATE`, `RANGE`, `BASE_PLUS`, `BASE_PLUS_VARIABLE`, `MATRIX_REF` |
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

Prefer `add_package_to_proposal_draft` / `add_services_to_proposal_draft` for MDM catalog additions instead of manually constructing rows.

## Pricing display

- `FIXED`: fee table shows formatted `price.amount`; summaries sum annualised totals from `price.amount`.
- `UNIT_RATE`, `RANGE`, `BASE_PLUS`, `BASE_PLUS_VARIABLE`, `MATRIX_REF`: AU frequency table shows `price.fee_raw` in the billing column (Monthly/Quarterly/Annual/Once-Off); **Total** column always shows the annualised numeric total from `price.amount` (Monthly×12, Quarterly×4, otherwise×1). BVI simple table shows `fee_raw` in Amount.
- **Footnotes**: when template sets `fee_layout.footnotes: aggregate`, non-empty `rows[].footnotes` are deduped, numbered once for the **entire fee section**, rendered in a single block after all fee tables, with `<sup>` refs on the **Service** cell linking to `#fn-N`.
- **Placeholders** (`template.yaml` → `placeholders`): platform resolves `{{client.*}}`, `{{selected_packages_bullet_list}}`, `{{fee_year}}`, etc. on render and after `add_package` / client fact patches (when section `edit_state.content` is `source`).
- **Package narratives** (`fee_section.package_narratives.index`): platform injects `blocks/solutions/PKG*.md` before fee tables for each package in draft fee tables.
- **Column widths** (`fee_layout.column_widths`): per `table_style` keys `simple` / `frequency_columns`, each with `service` and `amount` CSS widths (e.g. `72%` / `28%`). Applied to every grouped sub-table via `table-layout: fixed`.
- **Service cell columns** (`fee_layout.service_columns`): independently toggle `service_name`, `description`, and `scope_of_work` in the fee-table Service cell. BVI default: name + description, no SOW. AU default: name + SOW, no description. Legacy templates may use `include_scope_of_work: true` as alias for `scope_of_work: true`.
- After confirming facts (e.g. rounds, states), patch `price.amount` with the computed total; keep `fee_raw` as the unit/range description unless sales asks to rewrite it.

## Readiness

`render_preview` and `generate_document` compute readiness from the draft. Live panel renders the draft even when incomplete.
