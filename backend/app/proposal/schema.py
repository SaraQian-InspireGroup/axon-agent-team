"""Proposal-composer state JSON Schema and patch validation."""

from __future__ import annotations

import copy
from typing import Any

import jsonpatch
from jsonschema import Draft202012Validator

PROPOSAL_STATE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://ascentium.ai/schemas/proposal-composer-state.json",
    "title": "Proposal Composer State",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "proposal_meta": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "category_id": {"type": "string"},
                "template_id": {"type": "string"},
                "stage": {
                    "type": "string",
                    "readOnly": True,
                    "description": "Derived progress label; do not patch.",
                },
            },
        },
        "client": {
            "type": "object",
            "additionalProperties": {"type": ["string", "null", "number", "boolean"]},
        },
        "pricing_facts": {
            "type": "object",
            "additionalProperties": {"type": ["string", "number", "integer", "boolean", "null"]},
        },
        "selection": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "selected_packages": {"type": "array", "items": {"type": "string"}},
                "selected_skus": {"type": "array", "items": {"type": "string"}},
                "expanded_skus": {
                    "type": "array",
                    "items": {"type": "string"},
                    "readOnly": True,
                },
            },
        },
        "pricing": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "overrides": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": ["number", "null"]},
                            "reason": {"type": "string"},
                        },
                    },
                },
                "computed": {"type": "object", "readOnly": True},
                "explanations": {"type": "object", "readOnly": True},
                "recurring_schedule": {"type": "array", "readOnly": True},
            },
        },
        "line_items": {"type": "object", "readOnly": True},
        "enabled_sections": {"type": "array", "items": {"type": "string"}},
        "fee_description": {
            "type": ["string", "null"],
            "description": "Intro paragraph above fee tables (not the ### table heading).",
        },
        "fee_layout": {
            "type": "object",
            "properties": {
                "group_labels": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Fee table heading overrides keyed by group_id.",
                },
                "custom_groups": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "group_id": {"type": "string"},
                            "display_name": {"type": "string"},
                            "skus": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
            "additionalProperties": True,
        },
        "payment_options": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "options": {"type": "array", "items": {"type": "object"}},
                "overrides": {"type": "object"},
                "resolved": {"type": "array", "readOnly": True},
            },
        },
        "appendix": {"type": ["string", "array", "object", "null"]},
        "resolved_placeholders": {"type": "object", "readOnly": True},
        "completeness": {"type": "object", "readOnly": True},
        "peripheral": {"type": "object", "readOnly": True},
        "active_optional_sections": {
            "type": "array",
            "items": {"type": "string"},
            "readOnly": True,
        },
        "artifacts": {"type": "object", "readOnly": True},
    },
}

_VALIDATOR = Draft202012Validator(PROPOSAL_STATE_SCHEMA)


class PatchValidationError(Exception):
    """Patch rejected before or after apply (HTTP 422 semantics)."""

    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = errors
        message = "; ".join(f"{item['path']}: {item['message']}" for item in errors)
        super().__init__(message)


def empty_proposal_state() -> dict[str, Any]:
    return {
        "proposal_meta": {"stage": "INTAKE"},
        "client": {},
        "pricing_facts": {},
        "selection": {"selected_packages": [], "selected_skus": []},
        "pricing": {
            "computed": {},
            "overrides": {},
            "explanations": {},
            "recurring_schedule": [],
        },
        "line_items": {"groups": []},
        "enabled_sections": [],
        "fee_description": None,
        "fee_layout": {},
        "payment_options": {"options": [], "overrides": {}},
        "appendix": [],
        "resolved_placeholders": {},
        "completeness": {
            "missing_required": [],
            "enabled_optional_unfilled": [],
            "ready_to_preview": False,
            "ready_to_generate": False,
        },
    }


def get_path(state: dict[str, Any], dotted: str) -> Any:
    cur: Any = state
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def validate_state(state: dict[str, Any]) -> list[dict[str, str]]:
    errors = sorted(_VALIDATOR.iter_errors(state), key=lambda err: list(err.path))
    return [
        {
            "path": "/" + "/".join(str(part) for part in error.path),
            "message": error.message,
        }
        for error in errors
    ]


def _unescape_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _pointer_tokens(pointer: str) -> list[str]:
    if pointer in ("", "/"):
        return []
    if not pointer.startswith("/"):
        raise PatchValidationError([{"path": pointer, "message": "Invalid JSON Pointer"}])
    return [_unescape_pointer_token(part) for part in pointer.split("/")[1:] if part != ""]


def _resolve_schema_node(schema: dict[str, Any], pointer: str) -> dict[str, Any] | None:
    current: dict[str, Any] = schema
    for raw in _pointer_tokens(pointer):
        if raw == "-":
            continue
        if not isinstance(current, dict):
            return None

        props = current.get("properties")
        if isinstance(props, dict) and raw in props:
            current = props[raw]
            continue

        if current.get("type") == "array" or "items" in current:
            items = current.get("items")
            current = items if isinstance(items, dict) else {}
            continue

        additional = current.get("additionalProperties")
        if additional is True:
            current = {"type": "string"}
            continue
        if isinstance(additional, dict):
            current = additional
            continue

        return None
    return current


def _schema_path_readonly(schema: dict[str, Any], pointer: str) -> bool:
    if pointer in ("", "/"):
        return True
    current: dict[str, Any] = schema
    for raw in _pointer_tokens(pointer):
        if raw == "-":
            continue
        if not isinstance(current, dict):
            return False

        if current.get("readOnly") is True:
            return True

        props = current.get("properties")
        if isinstance(props, dict) and raw in props:
            current = props[raw]
            continue

        if current.get("type") == "array" or "items" in current:
            items = current.get("items")
            current = items if isinstance(items, dict) else {}
            continue

        additional = current.get("additionalProperties")
        if additional is True:
            current = {"type": "string"}
            continue
        if isinstance(additional, dict):
            current = additional
            continue

        return False

    node = _resolve_schema_node(schema, pointer)
    return bool(isinstance(node, dict) and node.get("readOnly") is True)


def _operation_paths(operation: dict[str, Any]) -> list[str]:
    op = operation.get("op")
    if op in {"add", "replace", "remove", "test"}:
        return [str(operation.get("path") or "")]
    if op == "move":
        return [str(operation.get("from") or ""), str(operation.get("path") or "")]
    if op == "copy":
        return [str(operation.get("path") or "")]
    return []


def _validate_operations_editable(operations: list[dict[str, Any]]) -> None:
    errors: list[dict[str, str]] = []
    allowed_ops = {"add", "remove", "replace", "move", "copy", "test"}
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            errors.append({"path": f"/{index}", "message": "Each patch entry must be an object"})
            continue
        op = operation.get("op")
        if op not in allowed_ops:
            errors.append({"path": f"/{index}/op", "message": f"Unsupported op: {op!r}"})
            continue
        for path in _operation_paths(operation):
            if not path.startswith("/"):
                errors.append({"path": path, "message": "Path must be a JSON Pointer"})
                continue
            if _schema_path_readonly(PROPOSAL_STATE_SCHEMA, path):
                errors.append({"path": path, "message": "Path is read-only"})
    if errors:
        raise PatchValidationError(errors)


def resolve_pointer(state: dict[str, Any], pointer: str) -> Any:
    """Resolve a JSON Pointer against state."""
    if pointer in ("", "/"):
        return state
    current: Any = state
    for raw in _pointer_tokens(pointer):
        if raw == "-":
            raise PatchValidationError([{"path": pointer, "message": "Cannot resolve pointer with '-'"}])
        if isinstance(current, list):
            index = int(raw)
            current = current[index]
        elif isinstance(current, dict):
            if raw not in current:
                raise PatchValidationError([{"path": pointer, "message": f"Missing key: {raw}"}])
            current = current[raw]
        else:
            raise PatchValidationError([{"path": pointer, "message": "Pointer traverses non-container"}])
    return current


def _path_exists(state: dict[str, Any], pointer: str) -> bool:
    try:
        resolve_pointer(state, pointer)
        return True
    except PatchValidationError:
        return False


def _normalize_operations(state: dict[str, Any], operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Allow replace on missing paths (upsert) — common server ergonomics atop RFC 6902."""
    normalized: list[dict[str, Any]] = []
    working = copy.deepcopy(state)
    for operation in operations:
        op = dict(operation)
        if op.get("op") == "replace":
            path = str(op.get("path") or "")
            if path and not _path_exists(working, path):
                op["op"] = "add"
        normalized.append(op)
        try:
            working = jsonpatch.JsonPatch([op]).apply(working, in_place=False)
        except jsonpatch.JsonPatchException:
            pass
    return normalized


def apply_json_patch(state: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply RFC 6902 JSON Patch with strict readOnly guardrails."""
    if not operations:
        return copy.deepcopy(state)
    if not isinstance(operations, list):
        raise PatchValidationError([{"path": "/", "message": "Patch must be a JSON Patch array"}])

    _validate_operations_editable(operations)
    normalized = _normalize_operations(state, operations)
    try:
        patched = jsonpatch.JsonPatch(normalized).apply(copy.deepcopy(state), in_place=False)
    except jsonpatch.JsonPatchException as exc:
        raise PatchValidationError([{"path": "/", "message": str(exc)}]) from exc

    schema_errors = validate_state(patched)
    if schema_errors:
        raise PatchValidationError(schema_errors)
    return patched


def writable_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Extract agent-writable fields for persistence recovery."""
    base = empty_proposal_state()
    meta = dict(state.get("proposal_meta") or {})
    meta.pop("stage", None)
    if meta:
        base["proposal_meta"] = {**base.get("proposal_meta", {}), **meta}

    for key in (
        "client",
        "pricing_facts",
        "selection",
        "enabled_sections",
        "fee_description",
        "fee_layout",
        "appendix",
    ):
        if key in state and state[key] is not None:
            base[key] = copy.deepcopy(state[key])

    selection = base.get("selection") or {}
    selection.pop("expanded_skus", None)

    pricing = state.get("pricing") or {}
    overrides = pricing.get("overrides")
    if overrides:
        base.setdefault("pricing", {})["overrides"] = copy.deepcopy(overrides)

    payment = state.get("payment_options") or {}
    base["payment_options"] = {
        "options": copy.deepcopy(payment.get("options") or []),
        "overrides": copy.deepcopy(payment.get("overrides") or {}),
    }
    return base
