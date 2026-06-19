from unittest.mock import patch

from app.proposal.draft import (
    add_package_to_draft,
    build_draft_preview,
    enable_draft_section,
    materialize_draft,
    patch_draft,
)


AU_SERVICE = {
    "sku": "TA01",
    "service_name_on_proposal": "Application - Substituted Accounting Period (Standard offer $600 one-off)",
    "product_name": "Application - Substituted Accounting Period",
    "scope_of_work": "Application for Substituted Accounting Period.",
    "billing_frequency": "ONE_TIME",
    "recurring": "ONE_OFF",
    "pricing_type": "FIXED",
    "price_currency": "AUD",
    "price_amount": 600.0,
}


def test_materialize_au_draft_from_template_sections():
    draft = materialize_draft(
        category_id="au-services",
        template_id="au-advisory",
        client={"company_name": "Walking Limited"},
    )

    assert draft["meta"]["template_id"] == "au-advisory"
    ids = [section["id"] for section in draft["document"]["sections"]]
    assert "introduction" in ids
    assert "solution_and_fees" in ids
    assert "terms" in ids


def test_materialize_bvi_draft_from_template_sections():
    draft = materialize_draft(
        category_id="harneys-bvi",
        template_id="harneys-bvi",
        client={"company_name": "BVI Demo Ltd"},
    )

    assert draft["meta"]["template_id"] == "harneys-bvi"
    assert draft["meta"]["title"] == "Proposal - BVI Demo Ltd"
    ids = [section["id"] for section in draft["document"]["sections"]]
    assert "introduction" in ids
    assert "solution_and_fees" in ids
    assert "terms" in ids


def test_add_package_materializes_editable_fee_rows():
    draft = materialize_draft(category_id="au-services", template_id="au-advisory")
    with patch(
        "app.proposal.draft.fetch_packages_by_ids",
        return_value=[
            {
                "package_id": "PKG-AU-1",
                "package_name": "Tax Package 2",
                "linked_skus": ["TA01"],
            }
        ],
    ):
        with patch(
            "app.proposal.draft.resolve_services_for_selection",
        ) as resolve:
            resolve.return_value.services = [AU_SERVICE]
            updated = add_package_to_draft(draft, "PKG-AU-1")

    fee = next(s for s in updated["document"]["sections"] if s["kind"] == "fee_section")
    row = fee["tables"][0]["rows"][0]
    assert fee["tables"][0]["title"] == "Tax Package 2"
    assert row["service_name"] == "Application - Substituted Accounting Period"
    assert row["price"]["amount"] == 600.0


def test_patch_draft_updates_display_row_and_preview():
    draft = materialize_draft(category_id="au-services", template_id="au-advisory")
    fee = next(s for s in draft["document"]["sections"] if s["kind"] == "fee_section")
    fee["tables"] = [
        {
            "id": "table_1",
            "title": "Services",
            "rows": [
                {
                    "id": "fee_TA01",
                    "kind": "fee_row",
                    "source": {"type": "mdm_service", "sku": "TA01"},
                    "service_name": "Old name",
                    "scope_of_work": "Scope.",
                    "price": {
                        "amount": 500.0,
                        "currency": "AUD",
                        "frequency": "ONE_TIME",
                        "recurring": "ONE_OFF",
                    },
                    "edit_state": {},
                }
            ],
        }
    ]

    updated = patch_draft(
        draft,
        [
            {
                "op": "replace",
                "path": "/document/sections/1/tables/0/rows/0/service_name",
                "value": "Application - Substituted Accounting Period",
            },
            {
                "op": "replace",
                "path": "/document/sections/1/tables/0/rows/0/price/amount",
                "value": 600.0,
            },
        ],
    )
    preview = build_draft_preview(updated)
    assert "Application - Substituted Accounting Period" in preview["markdown"]
    assert "Old name" not in preview["markdown"]
    assert "AUD $600.00" in preview["markdown"]


def test_payment_options_derived_from_fee_tables_when_enabled():
    draft = materialize_draft(category_id="au-services", template_id="au-advisory")
    fee = next(s for s in draft["document"]["sections"] if s["kind"] == "fee_section")
    fee["tables"] = [
        {
            "id": "table_setup",
            "title": "Setup of Xero",
            "rows": [
                {
                    "id": "fee_XERO",
                    "kind": "fee_row",
                    "source": {"type": "mdm_service", "sku": "XERO"},
                    "service_name": "Setup of Xero",
                    "scope_of_work": "",
                    "price": {
                        "amount": 500.0,
                        "currency": "AUD",
                        "frequency": "ONE_TIME",
                        "recurring": "ONE_OFF",
                    },
                    "edit_state": {},
                }
            ],
        },
        {
            "id": "table_tax",
            "title": "Tax Package 2",
            "rows": [
                {
                    "id": "fee_TA01",
                    "kind": "fee_row",
                    "source": {"type": "mdm_service", "sku": "TA01"},
                    "service_name": "Application",
                    "scope_of_work": "",
                    "price": {
                        "amount": 400.0,
                        "currency": "AUD",
                        "frequency": "MONTHLY",
                        "recurring": "RECURRING",
                    },
                    "edit_state": {},
                }
            ],
        },
    ]

    disabled_preview = build_draft_preview(draft)
    assert "# Fee summary" not in disabled_preview["markdown"]

    enabled = enable_draft_section(draft, "payment_options")
    preview = build_draft_preview(enabled)
    assert "# Fee summary" in preview["markdown"]
    assert "Payment Option A" in preview["markdown"]
    assert "Setup of Xero" in preview["markdown"]
    assert "Tax Package 2" in preview["markdown"]
    assert "AUD $500.00" in preview["markdown"]
    assert "AUD $4,800.00" in preview["markdown"]


def test_payment_options_render_multiple_configured_options():
    draft = materialize_draft(category_id="au-services", template_id="au-advisory")
    fee = next(s for s in draft["document"]["sections"] if s["kind"] == "fee_section")
    fee["tables"] = [
        {
            "id": "table_css",
            "title": "CSS Package 2",
            "rows": [
                {
                    "id": "fee_COMPANY",
                    "kind": "fee_row",
                    "source": {"type": "mdm_service", "sku": "COMPANY"},
                    "service_name": "Company Incorporation",
                    "scope_of_work": "",
                    "price": {
                        "amount": 2500.0,
                        "currency": "AUD",
                        "frequency": "ONE_TIME",
                        "recurring": "ONE_OFF",
                    },
                    "edit_state": {},
                },
                {
                    "id": "fee_AUDIT",
                    "kind": "fee_row",
                    "source": {"type": "mdm_service", "sku": "AUDIT"},
                    "service_name": "Application for Audit Relief",
                    "scope_of_work": "",
                    "price": {
                        "amount": 900.0,
                        "currency": "AUD",
                        "frequency": "ONE_TIME",
                        "recurring": "ONE_OFF",
                    },
                    "edit_state": {},
                }
            ],
        }
    ]
    payment = next(s for s in draft["document"]["sections"] if s["id"] == "payment_options")
    payment["enabled"] = True
    payment["options"] = [
        {
            "option_id": "option_a",
            "label": "Payment Option A - One-off Payment",
            "rows": [
                {
                    "group_id": "table_css",
                    "label": "CSS Package 2",
                    "once_off": 2500.0,
                    "monthly": 0.0,
                    "quarterly": 0.0,
                    "annual": 0.0,
                }
            ],
        },
        {
            "option_id": "option_b",
            "label": "Payment Option B - Monthly Recurring",
            "rows": [
                {
                    "group_id": "table_css",
                    "label": "CSS Package 2",
                    "once_off": 0.0,
                    "monthly": 200.0,
                    "quarterly": 0.0,
                    "annual": 0.0,
                }
            ],
        },
    ]

    preview = build_draft_preview(draft)
    assert "Payment Option A - One-off Payment" in preview["markdown"]
    assert "Payment Option B - Monthly Recurring" in preview["markdown"]
    assert "AUD $2,400.00" in preview["markdown"]


def test_payment_options_render_override_only_options():
    draft = materialize_draft(category_id="au-services", template_id="au-advisory")
    fee = next(s for s in draft["document"]["sections"] if s["kind"] == "fee_section")
    fee["tables"] = [
        {
            "id": "table_css",
            "title": "CSS Package 2",
            "rows": [
                {
                    "id": "fee_COMPANY",
                    "kind": "fee_row",
                    "source": {"type": "mdm_service", "sku": "COMPANY"},
                    "service_name": "Company Incorporation",
                    "scope_of_work": "",
                    "price": {
                        "amount": 2500.0,
                        "currency": "AUD",
                        "frequency": "ONE_TIME",
                        "recurring": "ONE_OFF",
                    },
                    "edit_state": {},
                }
            ],
        }
    ]
    payment = next(s for s in draft["document"]["sections"] if s["id"] == "payment_options")
    payment["enabled"] = True
    payment["overrides"] = {
        "option_a": {
            "label": "Option A — One-off Payment",
            "rows": [
                {
                    "sku": "COMPANY",
                    "service_name": "Company Incorporation",
                    "price": {"amount": 2500.0, "currency": "AUD", "frequency": "ONE_TIME"},
                },
                {
                    "sku": "AUDIT",
                    "service_name": "Application for Audit Relief",
                    "price": {"amount": 900.0, "currency": "AUD", "frequency": "ONE_TIME"},
                }
            ],
        },
        "option_b": {
            "label": "Option B — Monthly Recurring",
            "rows": [
                {
                    "sku": "COMPANY",
                    "service_name": "Company Incorporation",
                    "price": {"amount": 200.0, "currency": "AUD", "frequency": "MONTHLY"},
                },
                {
                    "sku": "AUDIT",
                    "service_name": "Application for Audit Relief",
                    "price": {"amount": 70.0, "currency": "AUD", "frequency": "MONTHLY"},
                }
            ],
        },
    }

    preview = build_draft_preview(draft)
    payment_markdown = preview["markdown"].split("# Fee summary", 1)[1]
    assert "Option A — One-off Payment" in payment_markdown
    assert "Option B — Monthly Recurring" in payment_markdown
    assert "CSS Package 2" in payment_markdown
    assert "Company Incorporation" not in payment_markdown
    assert "Application for Audit Relief" not in payment_markdown
    assert "AUD $3,400.00" in payment_markdown
    assert "AUD $3,240.00" in payment_markdown


def test_static_sections_render_template_titles_once():
    draft = materialize_draft(category_id="au-services", template_id="au-advisory")
    preview = build_draft_preview(draft)

    assert "# About Incorp" in preview["markdown"]
    assert "# Terms and conditions" in preview["markdown"]
    assert preview["markdown"].count("# About Incorp") == 1
    assert preview["markdown"].count("# Terms and conditions") == 1
