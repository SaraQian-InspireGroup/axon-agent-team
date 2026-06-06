"""Pre-SSO identity: every request is attributed to the seeded dev user."""

import uuid

from app.db.models import DEV_USER_EMAIL, DEV_USER_ID, DEV_USER_NAME

__all__ = ["DEV_USER_EMAIL", "DEV_USER_ID", "DEV_USER_NAME", "get_current_user_id"]


def get_current_user_id() -> uuid.UUID:
    return DEV_USER_ID
