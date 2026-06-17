"""Load categories, templates, and knowledge index from agent knowledge files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Any

import yaml

from app.proposal.paths import (
    CATEGORIES_PATH,
    KNOWLEDGE_INDEX_PATH,
    KNOWLEDGE_ROOT,
    TEMPLATES_ROOT,
)
from app.proposal.state import get_path


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


def resolve_template_id(state: dict[str, Any]) -> str | None:
    meta = state.get("proposal_meta") or {}
    template_id = meta.get("template_id")
    if template_id:
        return str(template_id)
    category_id = meta.get("category_id")
    if not category_id:
        return None
    cat = get_category(str(category_id))
    if cat and cat.get("default_template_id"):
        return str(cat["default_template_id"])
    return None


def template_dir(template_id: str) -> Path:
    return TEMPLATES_ROOT / template_id


@lru_cache(maxsize=8)
def load_template_yaml(template_id: str) -> dict[str, Any]:
    path = template_dir(template_id) / "template.yaml"
    return _load_yaml(path)


@lru_cache(maxsize=8)
def load_proposal_body(template_id: str) -> str:
    tpl = load_template_yaml(template_id)
    body_name = tpl.get("body") or "proposal.md"
    path = template_dir(template_id) / str(body_name)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


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


def resolve_document_title(state: dict[str, Any], template_id: str | None) -> str:
    client = state.get("client") or {}
    if not template_id:
        return str(
            client.get("company_name") or client.get("contract_name") or "Proposal"
        )

    tpl = load_template_yaml(template_id)
    cfg = tpl.get("document_title")
    if isinstance(cfg, str) and cfg.strip():
        return _render_title_pattern(cfg.strip(), state)
    if isinstance(cfg, dict):
        prefix = str(cfg.get("prefix") or "Proposal").strip()
        name_fields = cfg.get("name_from") or ["client.company_name", "client.contract_name"]
        for field in name_fields:
            value = get_path(state, str(field)) if "." in str(field) else client.get(field)
            if value:
                return f"{prefix} - {value}" if prefix else str(value)
        fallback = cfg.get("fallback")
        if fallback:
            return str(fallback)
        return prefix
    return str(client.get("company_name") or client.get("contract_name") or "Proposal")


def _render_title_pattern(pattern: str, state: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        parts = [part.strip() for part in expr.split("|")]
        for part in parts:
            if part.startswith("default:"):
                continue
            if part.startswith("client."):
                value = get_path(state, part)
            else:
                value = None
            if value:
                return str(value)
        for part in parts:
            if part.startswith("default:"):
                return part.split(":", 1)[1]
        return ""

    return re.sub(r"\{\{([^}]+)\}\}", replace, pattern)


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
