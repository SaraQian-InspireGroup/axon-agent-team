# Proposal state (writable vs derived)

Field dictionary for **what to patch**. **When/how to call tools** → tool descriptions, not this file.

## Writable

| Field | Purpose |
|-------|---------|
| `proposal_meta.category_id` | Routes MDM catalog scope |
| `proposal_meta.template_id` | Document template (auto from category when omitted) |
| `client.*` | Company and contact |
| `pricing_facts.*` | Inputs for TIERED/MATRIX pricing (e.g. `share_count`) |
| `selection.selected_packages` | Package IDs |
| `selection.selected_skus` | Ad-hoc SKUs outside packages |
| `pricing.overrides` | Manual line adjustments `{ sku: { amount, reason } }` |
| `enabled_sections` | Optional template sections |
| `fee_description` | Override fee intro text (defaults from template block) |
| `fee_layout.custom_groups` | Split/reassign fee tables `{ group_id, display_name, skus[] }` |
| `payment_options.options` | Payment option rows/labels (defaults derived from fee tables) |
| `payment_options.overrides` | Adjust option totals without changing SKU pricing |
| `appendix` | Free-form appendix content |

Semantic ops (`set_category`, `add_skus`, …) → **`patch_proposal_state` tool parameter description**.

## Derived (do not patch)

| Field | Source |
|-------|--------|
| `selection.expanded_skus` | Packages expanded + explicit SKUs |
| `pricing.computed` | `compute_pricing` from MDM + facts |
| `line_items` | Fee table grouped by template `fee_layout` |
| `payment_options.resolved` | Payment summary derived from fee tables |
| `resolved_placeholders` | Template + knowledge index |
| `peripheral.required_docs` | Knowledge index triggers |
| `completeness` | Required placeholder scan |
| `proposal_meta.stage` | Derived progress label |

## Completeness (for user-facing gaps)

| Flag / list | Meaning |
|-------------|---------|
| `missing_required` | Required placeholders unfilled — explain in sales language |
| `ready_to_preview` | Required placeholders filled |
| `ready_to_generate` | Required + enabled optional sections filled |
| `enabled_optional_unfilled` | Optional section enabled but content missing |

Live Proposal panel renders draft even when incomplete; **`generate_document`** respects `ready_to_generate` unless `force=true`.
