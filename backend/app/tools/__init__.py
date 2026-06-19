from app.tools.builtin import platform_time
from app.tools.proposal import (
    add_package_to_proposal_draft,
    add_service_to_proposal_draft,
    enable_proposal_draft_section,
    generate_document,
    get_proposal_draft,
    initialize_proposal_draft,
    list_categories,
    patch_proposal_draft,
    read_knowledge,
    render_preview,
)
from app.tools.viz import list_sql_results, suggest_visualization

BUILTIN_TOOLS = {
    "platform_time": platform_time,
    "list_sql_results": list_sql_results,
    "suggest_visualization": suggest_visualization,
    "list_categories": list_categories,
    "read_knowledge": read_knowledge,
    "initialize_proposal_draft": initialize_proposal_draft,
    "get_proposal_draft": get_proposal_draft,
    "patch_proposal_draft": patch_proposal_draft,
    "add_package_to_proposal_draft": add_package_to_proposal_draft,
    "add_service_to_proposal_draft": add_service_to_proposal_draft,
    "enable_proposal_draft_section": enable_proposal_draft_section,
    "render_preview": render_preview,
    "generate_document": generate_document,
}
