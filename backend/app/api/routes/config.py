from app.config import get_settings
from app.platform.attachment_limits import attachment_limits_dict

from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/attachments")
async def get_attachment_config() -> dict[str, int]:
    """Platform-wide attachment limits (from .env, shared by all agents)."""
    return attachment_limits_dict(get_settings())
