# Template Contract (`template.yaml`)

Each `template_id` has a draft materialization contract at:

```text
templates/{template_id}/template.yaml
```

Read it with **`read_knowledge`** when section ids, section kinds, optional blocks, or derivations are unclear. The platform uses the same file to materialize `proposal_draft`; the agent must align draft patches with it.

## When to read

| Situation | Read template? |
|-----------|----------------|
| Draft was just initialized or template changed | **Yes** — before filling optional sections, derived sections, or custom tables |
| User asks for audit vs advisory (AU) | **Yes** — after choosing `au-advisory` vs future `au-audit` |
| First time on a template with unfamiliar layout | **Yes** |
| Small patch only (e.g. client name) and template already understood this session | Optional |
| Exploring SKU/package prices | **No** — use Postgres MCP + `proposal-mdm-catalog` |

**Path pattern:**

```text
read_knowledge("templates/{template_id}/template.yaml")
```

Use `/meta/template_id` from draft, or `list_templates` when the proposal type is not known yet.

## What is in `template.yaml`

| Template area | Agent use |
|---------|-----------|
| `sections[].id` | Stable section id for `enable_proposal_draft_section` and JSON Pointer targeting |
| `sections[].kind` | How the draft node behaves: `static_block`, `markdown_block`, `fee_section`, `collection`, `derived_section`, future `table_section` |
| `sections[].default_enabled` / `required` | Initial visibility and whether the section can be disabled |
| `sections[].editable` | Whether user/agent may patch visible content |
| `sections[].source` / `intro.source` | Template block or peripheral source for initial content |
| `sections[].fee_layout` | Rendering hints for fee tables (`footnotes: aggregate`, `column_widths`, etc.) |
| `sections[].package_narratives` | Index YAML mapping `package_id` → `blocks/solutions/*.md` (auto-injected before fee tables) |
| `placeholders` | Tokens in introduction/fee blocks resolved from `facts.client`, `facts.inputs`, or selected packages |
| `sections[].derivation` | Derived content rule, e.g. AU `payment_options_from_fee_tables` |
| `document_title` | How draft `meta.title` is built from `facts.client.*` |

There is no separate body markdown template. `template.yaml` is the source of truth for draft structure, section ordering, and patch targets; static prose lives in `blocks/*.md`.

## How to use after reading

1. **`initialize_proposal_draft`** — materialize sections from template.
2. **`template.yaml`** — section ids, kinds, default enabled flags, editability, materializers, derivations.
3. **Draft tools** — use `add_*_to_proposal_draft` for catalog additions and `patch_proposal_draft` for visible copy/table edits.
4. **`get_proposal_draft`** — verify fee tables, rows, optional sections, and client facts after patch.

### `fee_section` (e.g. AU `solution_and_fees`)

- Agent adds packages/services into draft fee tables.
- Platform renders the fee table from draft rows — agent does **not** hand-write the 6-column HTML.
- Read template to know fee section id, optional `payment_options`, and derived sections.

### `derived_section` (e.g. AU `payment_options`)

- Enable with `enable_proposal_draft_section(section_id)`.
- Do not patch generated content directly unless the template explicitly supports overrides.
- Derived content should summarize other draft nodes, such as fee tables.

### `table_section` / collection-style sections

- Template defines table section columns/hints/examples.
- Agent patches draft table rows with objects keyed by column id.
- Required fields in hints (e.g. company name, financial year end) mean **ask user if missing**, then include in cell text.

### `static_block`

- Content lives in `blocks/*.md`; platform injects automatically.
- Usually not editable. Do not patch unless the draft node policy allows it.

### Credentials / CSV (`peripheral/`)

- `read_knowledge("peripheral/.../*.csv")` — full file text; agent filters in reasoning.
- Patch selected content into the relevant editable draft section.

## Examples

**AU advisory — after setting template:**

```text
read_knowledge("templates/au-advisory/template.yaml")
```

Check: `solution_and_fees` is the fee section; `payment_options` is optional derived content; `credentials` and `appendix` are optional editable sections.

## Do not

- Duplicate template rules in skill prose — link here and read the file.
- Treat template rules as prose memory — read `template.yaml` when unsure.
