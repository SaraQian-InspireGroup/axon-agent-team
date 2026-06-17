"""Persist generated proposal documents for download."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = _BACKEND_ROOT / "data" / "proposal-artifacts"


def _slugify(value: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return (slug or "proposal")[:max_len]


def build_filename(state: dict, *, extension: str = "md", template_id: str | None = None) -> str:
    from app.proposal.loaders import resolve_document_title, resolve_template_id

    tid = template_id or resolve_template_id(state)
    title = resolve_document_title(state, tid)
    safe = re.sub(r'[<>:"/\\|?*]', "-", title.strip())
    safe = re.sub(r"\s+", " ", safe).strip()
    return f"{safe}.{extension}" if safe else f"proposal.{extension}"


def new_artifact_id() -> str:
    return f"prop-{uuid.uuid4().hex[:12]}"


def save_markdown(chat_id: uuid.UUID, artifact_id: str, content: str, *, filename: str) -> Path:
    chat_dir = ARTIFACTS_ROOT / str(chat_id)
    chat_dir.mkdir(parents=True, exist_ok=True)
    path = chat_dir / f"{artifact_id}.md"
    path.write_text(content, encoding="utf-8")
    meta_path = chat_dir / f"{artifact_id}.meta.json"
    meta_path.write_text(json.dumps({"filename": filename}), encoding="utf-8")
    return path


def artifact_download_filename(chat_id: uuid.UUID, artifact_id: str) -> str:
    meta_path = ARTIFACTS_ROOT / str(chat_id) / f"{artifact_id}.meta.json"
    if meta_path.is_file():
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            name = str(payload.get("filename") or "").strip()
            if name:
                return name
        except (OSError, json.JSONDecodeError):
            pass
    return f"proposal-{artifact_id[:8]}.md"


def resolve_artifact_path(chat_id: uuid.UUID, artifact_id: str) -> Path | None:
    if not artifact_id or ".." in artifact_id or "/" in artifact_id:
        return None
    path = (ARTIFACTS_ROOT / str(chat_id) / f"{artifact_id}.md").resolve()
    root = (ARTIFACTS_ROOT / str(chat_id)).resolve()
    if not str(path).startswith(str(root)):
        return None
    return path if path.is_file() else None
