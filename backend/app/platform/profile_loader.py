import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings
from app.platform.model_registry import ModelProvider

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
AGENTS_ROOT = _BACKEND_ROOT / "agents"
_AGENT_MCP_FILENAME = "mcp_servers.yaml"
_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def mcp_storage_name(slug: str, local_name: str) -> str:
    """Globally unique DB key; local_name is the tool name exposed to the model."""
    return f"{slug}:{local_name}"


def mcp_tool_name(storage_name: str, connection: dict[str, Any] | None = None) -> str:
    if connection and connection.get("tool_name"):
        return str(connection["tool_name"])
    if ":" in storage_name:
        return storage_name.split(":", 1)[1]
    return storage_name


@dataclass
class AgentProfile:
    slug: str
    name: str
    description: str | None
    model_provider: str
    model_name: str
    instructions: str
    skill_paths: list[Path]
    mcp_servers: list[str]
    extra_config: dict[str, Any] = field(default_factory=dict)


def _resolve_env(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        env_val = os.environ.get(key)
        if env_val:
            return env_val
        settings = get_settings()
        if hasattr(settings, key.lower()):
            return str(getattr(settings, key.lower()) or "")
        model_fields = {
            "CLAUDE_AZURE_FOUNDRY_MODEL": settings.claude_azure_foundry_model,
            "AZURE_OPENAI_DEPLOYMENT": settings.azure_openai_deployment,
            "ODI_KNOWLEDGE_POSTGRES_URL": settings.odi_knowledge_postgres_url,
            "SG_SP_MYSQL_HOST": settings.sg_sp_mysql_host,
            "SG_SP_MYSQL_PORT": settings.sg_sp_mysql_port,
            "SG_SP_MYSQL_USER": settings.sg_sp_mysql_user,
            "SG_SP_MYSQL_PASSWORD": settings.sg_sp_mysql_password,
            "SG_SP_MYSQL_DATABASE": settings.sg_sp_mysql_database,
        }
        if key in model_fields and model_fields[key]:
            return str(model_fields[key])
        return match.group(0)

    if not isinstance(value, str):
        return value
    return _ENV_PATTERN.sub(repl, value)


def _resolve_env_deep(obj: Any) -> Any:
    if isinstance(obj, str):
        return _resolve_env(obj)
    if isinstance(obj, list):
        return [_resolve_env_deep(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _resolve_env_deep(v) for k, v in obj.items()}
    return obj


def load_agent_mcp_servers(agent_dir: Path) -> dict[str, dict[str, Any]]:
    """Load MCP server definitions from agents/<slug>/mcp_servers.yaml."""
    path = agent_dir / _AGENT_MCP_FILENAME
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    servers = raw.get("servers") or {}
    return {name: _resolve_env_deep(cfg) for name, cfg in servers.items()}


def _discover_skill_paths(agent_dir: Path, skills_dir_name: str) -> list[Path]:
    skills_root = agent_dir / skills_dir_name
    if not skills_root.is_dir():
        return []
    paths: list[Path] = []
    for child in sorted(skills_root.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            paths.append(child)
    return paths


def load_agent_profile(agent_dir: Path) -> AgentProfile:
    profile_path = agent_dir / "profile.yaml"
    if not profile_path.exists():
        raise ValueError(f"Missing profile.yaml in {agent_dir}")

    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    slug = str(raw.get("id") or agent_dir.name).strip()
    if not slug:
        raise ValueError(f"Agent profile in {agent_dir} requires id")
    if slug != agent_dir.name:
        raise ValueError(
            f"Agent profile id '{slug}' must match directory name '{agent_dir.name}' ({profile_path})"
        )

    prompt_file = raw.get("prompt_file") or "system_prompt.md"
    prompt_path = agent_dir / prompt_file
    if not prompt_path.exists():
        raise ValueError(f"Prompt file not found: {prompt_path}")
    instructions = prompt_path.read_text(encoding="utf-8").strip()

    model_provider = raw.get("model_provider")
    if not model_provider:
        model_val = _resolve_env(str(raw.get("model") or ""))
        if "claude" in model_val.lower():
            model_provider = ModelProvider.AZURE_ANTHROPIC.value
        else:
            model_provider = ModelProvider.AZURE_OPENAI.value
    model_name = _resolve_env(str(raw.get("model") or ""))
    if not model_name:
        settings = get_settings()
        if model_provider == ModelProvider.AZURE_ANTHROPIC.value:
            model_name = settings.claude_azure_foundry_model or "claude-sonnet-4-6"
        else:
            model_name = settings.azure_openai_deployment

    skills_dir = raw.get("skills_dir") or "skills"
    skill_paths = _discover_skill_paths(agent_dir, skills_dir)

    reserved = {
        "id",
        "name",
        "description",
        "version",
        "model",
        "model_provider",
        "prompt_file",
        "skills_dir",
        "mcp_servers",
        "invocation_modes",
        "delegates",
    }
    extra_config = {k: v for k, v in raw.items() if k not in reserved}

    return AgentProfile(
        slug=slug,
        name=str(raw.get("name") or slug),
        description=raw.get("description"),
        model_provider=str(model_provider),
        model_name=model_name,
        instructions=instructions,
        skill_paths=skill_paths,
        mcp_servers=list(raw.get("mcp_servers") or []),
        extra_config=extra_config,
    )


def discover_agent_profiles() -> list[AgentProfile]:
    if not AGENTS_ROOT.is_dir():
        return []
    profiles: list[AgentProfile] = []
    for child in sorted(AGENTS_ROOT.iterdir()):
        if child.is_dir() and (child / "profile.yaml").exists():
            profiles.append(load_agent_profile(child))
    return profiles
