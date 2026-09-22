"""Compatibility import for contributors migrating from the prototype.

New code uses agents/runtime.py plus providers/. There are no model-specific business
functions here. See docs/ADDING_A_PROVIDER.md and docs/AGENT_WORKFLOWS.md.
"""

from .agents.runtime import execute
from .providers.base import ProviderError

__all__ = ["ProviderError", "execute"]
