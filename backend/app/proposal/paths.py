"""Filesystem paths for proposal-composer knowledge."""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
AGENT_ROOT = _BACKEND_ROOT / "agents" / "proposal-composer"
KNOWLEDGE_ROOT = AGENT_ROOT / "knowledge"

CATEGORIES_PATH = KNOWLEDGE_ROOT / "categories.yaml"
KNOWLEDGE_INDEX_PATH = KNOWLEDGE_ROOT / "knowledge-index.yaml"
TEMPLATES_ROOT = KNOWLEDGE_ROOT / "templates"
PERIPHERAL_ROOT = KNOWLEDGE_ROOT / "peripheral"
