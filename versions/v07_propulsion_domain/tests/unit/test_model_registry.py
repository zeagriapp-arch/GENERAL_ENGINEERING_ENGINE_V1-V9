import pytest

from config.settings import get_settings
from core.models.interfaces import ModelProvider, ModelResponse, ToolSpec
from core.models.registry import ModelRegistry


class FakeModelProvider(ModelProvider):
    """Usado en tests hasta que Phase 6 integre OllamaProvider contra un
    servidor real. Nunca se usa fuera de tests."""

    async def complete(self, messages, *, role="reasoning", response_schema=None, tools=None):
        return ModelResponse(text=f"fake response for role={role}")


def test_resolve_role_from_config():
    settings = get_settings()
    registry = ModelRegistry(settings, FakeModelProvider())
    cfg = registry.resolve_config("reasoning")
    assert cfg.model == "qwen3:32b"


def test_resolve_unknown_role_raises():
    settings = get_settings()
    registry = ModelRegistry(settings, FakeModelProvider())
    with pytest.raises(KeyError):
        registry.resolve_config("does_not_exist")


@pytest.mark.asyncio
async def test_provider_is_swappable():
    settings = get_settings()
    registry = ModelRegistry(settings, FakeModelProvider())
    response = await registry.provider.complete([{"role": "user", "content": "hi"}], role="fast")
    assert "fast" in response.text
