"""Load categories, templates, and knowledge index from agent knowledge files."""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from typing import Any

import yaml

from app.proposal.paths import (
    CATEGORIES_PATH,
    KNOWLEDGE_INDEX_PATH,
    KNOWLEDGE_ROOT,
    TEMPLATES_ROOT,
)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def load_categories() -> list[dict[str, Any]]:
    raw = _load_yaml(CATEGORIES_PATH)
    return list(raw.get("categories") or [])


def get_category(category_id: str) -> dict[str, Any] | None:
    for row in load_categories():
        if row.get("category_id") == category_id:
            return row
    return None


def template_dir(template_id: str) -> Path:
    return TEMPLATES_ROOT / template_id


@lru_cache(maxsize=8)
def load_template_yaml(template_id: str) -> dict[str, Any]:
    path = template_dir(template_id) / "template.yaml"
    return _load_yaml(path)


@lru_cache(maxsize=1)
def load_knowledge_index() -> dict[str, Any]:
    return _load_yaml(KNOWLEDGE_INDEX_PATH)


def read_knowledge_file(relative_path: str) -> str:
    """Read a file under knowledge/ after path validation."""
    rel = relative_path.strip().lstrip("/")
    if ".." in rel.split("/"):
        raise ValueError("Invalid knowledge path")
    full = (KNOWLEDGE_ROOT / rel).resolve()
    if not str(full).startswith(str(KNOWLEDGE_ROOT.resolve())):
        raise ValueError("Knowledge path escapes knowledge root")
    if not full.is_file():
        raise FileNotFoundError(f"Knowledge file not found: {relative_path}")
    return full.read_text(encoding="utf-8")


def read_static_block(template_id: str, file_ref: str) -> str:
    rel = file_ref.strip().lstrip("/")
    if ".." in rel.split("/"):
        raise ValueError("Invalid block path")
    base = template_dir(template_id).resolve()
    full = (base / rel).resolve()
    if not str(full).startswith(str(base)):
        raise ValueError("Block path escapes template directory")
    if not full.is_file():
        raise FileNotFoundError(f"Template block not found: {file_ref}")
    return full.read_text(encoding="utf-8")
