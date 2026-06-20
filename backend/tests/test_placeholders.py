from app.proposal.draft import add_package_to_draft, build_draft_preview, materialize_draft
from app.proposal.placeholders import apply_template_placeholders, sync_draft_template_placeholders


def test_introduction_placeholders_resolve_client_and_packages():
    draft = materialize_draft(
        template_id="harneys-bvi",
        client={"contract_name": "Jane Doe"},
    )
    updated = add_package_to_draft(
        draft,
        {"package_id": "PKG003", "package_name": "Approval Manager"},
        [
            {
                "sku": "AM001",
                "description": "Formation fee",
                "department_team": "Corporate Secretarial Services",
                "pricing_type": "FIXED",
                "price_amount": 100.0,
                "price_currency": "USD",
                "billing_frequency": "ONE_TIME",
                "recurring": "ONE_OFF",
            },
        ],
    )
    intro = next(s for s in updated["document"]["sections"] if s["id"] == "introduction")
    assert "Jane Doe" in intro["content"]
    assert "- Approval Manager" in intro["content"]
    assert "{{client.contract_name}}" not in intro["content"]
    assert "{{selected_packages_bullet_list}}" not in intro["content"]


def test_package_narrative_renders_in_fee_section():
    draft = materialize_draft(template_id="harneys-bvi")
    updated = add_package_to_draft(
        draft,
        {"package_id": "PKG003", "package_name": "Approval Manager"},
        [
            {
                "sku": "AM001",
                "description": "Formation fee",
                "department_team": "Corporate Secretarial Services",
                "pricing_type": "FIXED",
                "price_amount": 100.0,
                "price_currency": "USD",
                "billing_frequency": "ONE_TIME",
                "recurring": "ONE_OFF",
            },
        ],
    )
    markdown = build_draft_preview(updated)["markdown"]
    assert "## Approved Manager" in markdown
    assert "streamlined route for investment managers" in markdown


def test_fee_tables_heading_separates_narratives_from_tables():
    draft = materialize_draft(template_id="harneys-bvi")
    updated = add_package_to_draft(
        draft,
        {"package_id": "PKG003", "package_name": "Approval Manager"},
        [
            {
                "sku": "AM001",
                "description": "Formation fee",
                "department_team": "Corporate Secretarial Services",
                "pricing_type": "FIXED",
                "price_amount": 100.0,
                "price_currency": "USD",
                "billing_frequency": "ONE_TIME",
                "recurring": "ONE_OFF",
            },
        ],
    )
    markdown = build_draft_preview(updated)["markdown"]
    solution = markdown.split("# Solution and pricing", 1)[1]
    assert "## Fees" in solution
    assert solution.index("streamlined route for investment managers") < solution.index("## Fees")
    assert solution.index("## Fees") < solution.index("### Approval Manager")


def test_add_package_materializes_narrative_block():
    draft = materialize_draft(template_id="harneys-bvi")
    updated = add_package_to_draft(
        draft,
        {"package_id": "PKG003", "package_name": "Approval Manager"},
        [
            {
                "sku": "AM001",
                "description": "Formation fee",
                "department_team": "Corporate Secretarial Services",
                "pricing_type": "FIXED",
                "price_amount": 100.0,
                "price_currency": "USD",
                "billing_frequency": "ONE_TIME",
                "recurring": "ONE_OFF",
            },
        ],
    )
    fee = next(s for s in updated["document"]["sections"] if s["kind"] == "fee_section")
    assert len(fee["narratives"]) == 1
    narrative = fee["narratives"][0]
    assert narrative["kind"] == "package_narrative"
    assert narrative["package_id"] == "PKG003"
    assert "streamlined route for investment managers" in narrative["content"]
    assert fee["tables"][0]["kind"] == "fee_table"


def test_sync_after_client_patch():
    draft = materialize_draft(template_id="harneys-bvi")
    draft = sync_draft_template_placeholders(draft)
    draft["facts"]["client"]["contract_name"] = "Updated Name"
    draft = sync_draft_template_placeholders(draft)
    intro = next(s for s in draft["document"]["sections"] if s["id"] == "introduction")
    assert "Updated Name" in intro["content"]


def test_fee_year_placeholder_in_narrative():
    draft = materialize_draft(template_id="harneys-bvi")
    draft["facts"].setdefault("inputs", {})["fee_year"] = "2027"
    updated = add_package_to_draft(
        draft,
        {"package_id": "PKG001", "package_name": "Incorporation"},
        [
            {
                "sku": "CSS001",
                "description": "Formation",
                "department_team": "Corporate Services",
                "pricing_type": "FIXED",
                "price_amount": 100.0,
                "price_currency": "USD",
                "billing_frequency": "ONE_TIME",
                "recurring": "ONE_OFF",
            },
        ],
    )
    text = apply_template_placeholders(
        "Fees for {{fee_year}}",
        updated,
        "harneys-bvi",
        "fee_table",
    )
    assert text == "Fees for 2027"
