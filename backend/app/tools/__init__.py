from app.tools.builtin import platform_time
from app.tools.proposal import (
    generate_document,
    get_proposal_schema,
    get_proposal_state,
    list_categories,
    patch_proposal_state,
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
    "get_proposal_schema": get_proposal_schema,
    "get_proposal_state": get_proposal_state,
    "patch_proposal_state": patch_proposal_state,
    "render_preview": render_preview,
    "generate_document": generate_document,
}
