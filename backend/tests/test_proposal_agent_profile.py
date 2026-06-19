from app.platform.profile_loader import load_agent_profile
from app.proposal.paths import AGENT_ROOT
from app.tools import BUILTIN_TOOLS


def test_proposal_composer_profile_loads():
    profile = load_agent_profile(AGENT_ROOT)
    assert profile.slug == "proposal-composer"
    allowed = profile.extra_config.get("allowed_tools") or []
    assert "patch_proposal_draft" in allowed
    assert "postgres_query_data" in allowed


def test_proposal_builtin_tools_registered():
    for name in (
        "list_categories",
        "read_knowledge",
        "initialize_proposal_draft",
        "get_proposal_draft",
        "patch_proposal_draft",
        "add_package_to_proposal_draft",
        "add_service_to_proposal_draft",
        "enable_proposal_draft_section",
        "render_preview",
        "generate_document",
    ):
        assert name in BUILTIN_TOOLS
