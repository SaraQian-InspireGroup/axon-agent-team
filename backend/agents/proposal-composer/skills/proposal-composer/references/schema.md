# Proposal state (writable vs derived)

## Writable (patch_proposal_state)

| Field | Purpose |
|-------|---------|
| `proposal_meta.category_id` | Routes MDM catalog scope |
| `proposal_meta.template_id` | Document template (auto from category when omitted) |
| `client.*` | Company and contact |
| `pricing_facts.*` | Inputs for TIERED/MATRIX pricing (e.g. `share_count`) |
| `selection.selected_packages` | Package IDs |
| `selection.selected_skus` | Extra SKUs outside packages |
| `pricing.overrides` | Manual line adjustments `{ sku: { amount, reason } }` |
| `enabled_sections` | Optional template sections |
| `appendix` | Free-form appendix content |

## Derived (do not patch)

| Field | Source |
|-------|--------|
| `selection.expanded_skus` | Packages expanded + explicit SKUs |
| `pricing.computed` | `compute_pricing` from MDM + facts |
| `line_items` | Fee table grouped by template `fee_layout` |
| `resolved_placeholders` | Template + knowledge index |
| `peripheral.required_docs` | Knowledge index triggers |
| `completeness` | Required placeholder scan |
| `proposal_meta.stage` | Derived progress label |

## Completeness

- `missing_required` — required placeholders unfilled
- `ready_to_preview` — required placeholders filled
- `ready_to_generate` — required + enabled optional sections filled
