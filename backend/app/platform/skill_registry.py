import uuid
from pathlib import Path

from agent_framework import SkillsProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentSkill, Skill

# backend/ — skill source_path is relative to this root (e.g. agents/odi-analysis/skills/...)
SKILLS_ROOT = Path(__file__).resolve().parents[2]


class SkillRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_skills(self) -> list[Skill]:
        result = await self._db.execute(select(Skill).order_by(Skill.name))
        return list(result.scalars().all())

    async def resolve_provider_for_agent(self, agent_id: uuid.UUID) -> SkillsProvider | None:
        result = await self._db.execute(
            select(Skill)
            .join(AgentSkill, AgentSkill.skill_id == Skill.id)
            .where(AgentSkill.agent_id == agent_id)
            .order_by(Skill.name)
        )
        paths: list[str | Path] = []
        for row in result.scalars().all():
            path = self._resolve_skill_path(row)
            if path is not None:
                paths.append(path)
        if not paths:
            return None
        return SkillsProvider.from_paths(*paths)

    def _resolve_skill_path(self, row: Skill) -> Path | None:
        if row.source_type != "file" or not row.source_path:
            return None
        path = SKILLS_ROOT / row.source_path
        return path if path.exists() else None
