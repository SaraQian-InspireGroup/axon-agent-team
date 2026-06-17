from app.platform.profile_loader import load_agent_profile
from app.proposal.paths import AGENT_ROOT
from app.tools import BUILTIN_TOOLS


def test_proposal_composer_profile_loads():
    profile = load_agent_profile(AGENT_ROOT)
    assert profile.slug == "proposal-composer"
    allowed = profile.extra_config.get("allowed_tools") or []
    assert "patch_proposal_state" in allowed
    assert "postgres_query_data" in allowed


def test_proposal_builtin_tools_registered():
    for name in (
        "list_categories",
        "read_knowledge",
        "get_proposal_schema",
        "get_proposal_state",
        "patch_proposal_state",
        "render_preview",
        "generate_document",
    ):
        assert name in BUILTIN_TOOLS
