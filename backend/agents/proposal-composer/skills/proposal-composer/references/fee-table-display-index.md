# Fee table display index (Preview ↔ draft)

The right-hand **Proposal Preview** adds **display numbers** at render time. They are **not** stored in draft JSON (`tables[].title`, `rows[].service_name` have no `2.2` prefix).

Use this reference when the user points at a line by panel number (e.g. **「2.2」**, **「第二张表第三行」**) or by SOW bullet order.

## Where numbers come from

| What the user sees | Draft field | Numbering rule |
|--------------------|-------------|----------------|
| `### 2. SMSF Services` (AU frequency layout) | `tables[].title` = `SMSF Services` | **Table display index** = order among fee tables that have **≥1 row**, starting at **1** |
| `2.2 Land Title Search` in Service column (AU) | `rows[].service_name` = `Land Title Search` | **Row display ref** = `{tableIndex}.{rowSub}` — `rowSub` is row order **within that table**, starting at **1** |
| Service name only (BVI simple layout) | same | **No row numbers** in preview — use `service_name`, `source.sku`, or row `id` |

AU frequency tables prefix the service cell as `{tableIndex}.{rowSub} {service_name}` (HTML). BVI simple tables show `{service_name}` only.

## Display index ≠ JSON array index

- JSON Pointer row index is **0-based**: `rows/0` is the first row.
- Panel **2.2** means: **2nd non-empty table**, **2nd row** in that table → often `rows/1` in draft, **not** `rows/2`.
- `tables/{ti}` in JSON is the **physical** table slot (empty tables still occupy indices). Preview **skips empty tables** when counting table numbers.

Always resolve through `get_proposal_draft` — do not guess `rows/1` from 「2.2」 without mapping.

## Resolution workflow (required before patch)

1. **`get_proposal_draft`** (full draft or `/document/sections`).
2. Locate the **`fee_section`** (`kind === "fee_section"`, usually `solution_and_fees`).
3. List **non-empty** tables only (`tables.filter(t => t.rows?.length)`), in array order.
4. For each table, assign `tableIndex = 1, 2, 3…` and for each row `rowSub = 1, 2, 3…`.
5. Build a short internal map before patching:

```text
1.1 | table_id=table_setup | row_id=fee_SETUP | sku=SETUP | Setup - SMSF
2.1 | table_id=table_smsf  | row_id=fee_SMSF006 | sku=SMSF006 | ASIC Corporate Compliance Fee
2.2 | table_id=table_smsf  | row_id=fee_SMSF007 | sku=SMSF007 | Land Title Search
```

6. Match the user’s reference to **one row** (`display_ref`, `sku`, or `service_name`).
7. Patch using the **physical** JSON Pointer:

```text
/document/sections/{sectionIndex}/tables/{tableIndexInDraft}/rows/{rowIndexInDraft}/scope_of_work
```

`sectionIndex` = index of the fee section in `document.sections[]` (0-based).  
`tableIndexInDraft` / `rowIndexInDraft` = indices in the **full** `tables[]` / `rows[]` arrays for the matched row.

8. If **ambiguous** (two rows match, or BVI with no numbers), ask once: confirm **SKU** or paste the **service name** / SOW snippet from the panel.

## User phrases → action

| User says | You do |
|-----------|--------|
| 「2.2 的 SOW 去掉第二点」 | Map **2.2** → row → read `scope_of_work` → edit text → patch that row’s `scope_of_work` |
| 「SMSF 表里 Land Title 那行」 | Match by `tables[].title` + `service_name` or `source.sku` |
| 「TA06 / SMSF007」 | Match `rows[].source.sku` (stable; preferred when user gives SKU) |
| 「第一张表」 | `tableIndex = 1` among non-empty tables |

## SOW bullet edits

- Bullets live in **`scope_of_work`** (plain text). Preview may render `- item` or `including: a; b` as HTML lists.
- To remove the **2nd bullet**, edit the string (delete that line or segment), then patch `scope_of_work`. Do not patch preview HTML.
- After patch, optionally re-read the row to confirm; the live panel updates from draft.

## Common mistakes

| Mistake | Why wrong |
|---------|-----------|
| Treat 「2.2」 as `rows[2]` | Display subscript is 1-based; array index is 0-based |
| Treat 「2.2」 as 2nd row in entire proposal | **2** is **table** index, not global row rank |
| Assume `service_name` contains `2.2` | Numbers are render-only |
| Use row order from MCP catalog | Draft row order follows **add order** in `fee_section.tables[].rows[]` |

## Template note

Read `templates/{template_id}/template.yaml` → `fee_layout.table_style`:

- `frequency_columns` (AU): table headings `### {n}. {title}` and row refs `{n}.{m}`.
- default / simple (BVI): no `{n}.{m}` on rows — rely on SKU / name.
