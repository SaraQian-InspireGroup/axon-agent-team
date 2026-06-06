import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import AgentModel
from app.memory.postgres_history import PostgresHistoryProvider
from app.platform.agent_bundle import AgentBundle
from app.platform.hook_registry import resolve_middleware
from app.platform.mcp_registry import McpRegistry
from app.platform.model_registry import ModelProvider, ModelProviderRegistry
from app.platform.skill_registry import SkillRegistry
from app.platform.tool_registry import ToolRegistry


class AgentFactory:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._registry = ModelProviderRegistry()
        self._tools = ToolRegistry(db)
        self._mcp = McpRegistry(db)
        self._skills = SkillRegistry(db)

    async def get_agent_row(self, agent_id: uuid.UUID) -> AgentModel:
        result = await self._db.execute(select(AgentModel).where(AgentModel.id == agent_id))
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"Agent not found: {agent_id}")
        return row

    async def build(self, agent_id: uuid.UUID, *, chat_id: uuid.UUID | None = None) -> AgentBundle:
        row = await self.get_agent_row(agent_id)
        provider = ModelProvider(row.model_provider)
        settings = get_settings()
        if provider == ModelProvider.AZURE_OPENAI:
            model_name = row.model_name or settings.azure_openai_deployment
        else:
            model_name = row.model_name or settings.claude_azure_foundry_model or ""

        history = PostgresHistoryProvider(self._db)
        context_providers: list = [history]
        skills_provider = await self._skills.resolve_provider_for_agent(agent_id)
        skill_tools: set[str] = set()
        if skills_provider is not None:
            context_providers.append(skills_provider)
            skill_tools.update({"load_skill", "read_skill_resource"})

        middleware = resolve_middleware(
            row.config,
            self._db,
            chat_id=chat_id,
            extra_allowed_tools=skill_tools or None,
        )

        function_tools = await self._tools.resolve_for_agent(agent_id)
        mcp_tools = await self._mcp.resolve_for_agent(agent_id, agent_config=row.config)
        combined_tools = [*list(function_tools or []), *mcp_tools]

        agent = self._registry.create_agent(
            name=row.name,
            instructions=row.instructions,
            model_provider=provider,
            model_name=model_name,
            context_providers=context_providers,
            middleware=middleware,
            tools=combined_tools or None,
            require_per_service_call_history_persistence=False,
        )
        return AgentBundle(agent=agent)
