"""Provider registry: adding an adapter requires no changes to business services."""

from ..config import settings
from .gemini import GeminiProvider
from .openai import CompatibleProvider, OpenAIProvider
from .sarvam import SarvamProvider

PROVIDERS = {
    "gemini": GeminiProvider(),
    "openai": OpenAIProvider(),
    "compatible": CompatibleProvider(),
    "sarvam": SarvamProvider(),
}

# Test fixtures are excluded from the production image and disabled in normal development.
if settings.demo_login and not settings.production:
    from tests.fixtures.demo_provider import DemoProvider

    PROVIDERS["demo"] = DemoProvider()
