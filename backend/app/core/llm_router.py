import instructor
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class LLMRouter:
    def __init__(self):
        self._openai_client = None
        self._instructor_openai = None
        self._anthropic_client = None
        self._instructor_anthropic = None

    @property
    def openai(self) -> AsyncOpenAI:
        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or "dummy-key")
        return self._openai_client

    @property
    def instructor_openai(self):
        if self._instructor_openai is None:
            self._instructor_openai = instructor.from_openai(self.openai)
        return self._instructor_openai

    @property
    def anthropic(self) -> AsyncAnthropic:
        if self._anthropic_client is None:
            self._anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY or "dummy-key")
        return self._anthropic_client

    @property
    def instructor_anthropic(self):
        if self._instructor_anthropic is None:
            self._instructor_anthropic = instructor.from_anthropic(self.anthropic)
        return self._instructor_anthropic

    def get_structured_client(self, preferred_provider: str = "openai"):
        """Returns instructor client based on configured keys and preference."""
        if preferred_provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            return self.instructor_anthropic, settings.DEFAULT_REASONING_LLM
        
        # Default to OpenAI or OpenAI-compatible endpoint
        return self.instructor_openai, settings.DEFAULT_FAST_LLM

llm_router = LLMRouter()

