from app.proposal.loaders import load_template_yaml, load_templates


def test_load_templates():
    templates = load_templates()
    ids = {row["template_id"] for row in templates}
    assert "harneys-bvi" in ids
    assert "au-advisory" in ids


def test_template_declares_catalog_filter():
    tpl = load_template_yaml("harneys-bvi")
    assert tpl["catalog_filter"] == {"jurisdiction": "BVI", "bu": "Harneys"}


def test_harneys_template_has_solution_and_price():
    tpl = load_template_yaml("harneys-bvi")
    sections = {section["id"]: section for section in tpl.get("sections") or []}
    assert "solution_and_fees" in sections
    assert sections["solution_and_fees"]["kind"] == "fee_section"
    assert "group_by" not in sections["solution_and_fees"]["fee_layout"]


def test_au_template_fee_layout():
    tpl = load_template_yaml("au-advisory")
    sections = {section["id"]: section for section in tpl.get("sections") or []}
    layout = sections["solution_and_fees"]["fee_layout"]
    assert layout.get("group_by") == "package"
    assert layout.get("table_style") == "frequency_columns"
    assert "body" not in tpl
    assert tpl.get("document_title", {}).get("prefix") == "INCORP ADVISORY PROPOSAL"

