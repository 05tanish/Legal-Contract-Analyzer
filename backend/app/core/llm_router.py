import instructor
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.core.config import settings
from langfuse.decorators import observe, langfuse_context
from langfuse.openai import AsyncOpenAI as AsyncOpenAILangfuse
import logging

logger = logging.getLogger(__name__)

class LLMRouter:
    def __init__(self):
        self._openai_client = None
        self._groq_client = None
        self._instructor_openai = None
        self._instructor_groq = None
        self._anthropic_client = None
        self._instructor_anthropic = None
        self._langfuse_enabled = bool(settings.LANGFUSE_SECRET_KEY)
        
        if self._langfuse_enabled:
            logger.info("Langfuse tracing enabled for Legal Contract Analyzer")

    @property
    def openai(self) -> AsyncOpenAI:
        if self._openai_client is None:
            if self._langfuse_enabled:
                # Use Langfuse-wrapped OpenAI client for automatic tracing
                self._openai_client = AsyncOpenAILangfuse(
                    api_key=settings.OPENAI_API_KEY or "dummy-key"
                )
            else:
                self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or "dummy-key")
        return self._openai_client

    @property
    def groq(self) -> AsyncOpenAI:
        """Groq client (OpenAI-compatible API)"""
        if self._groq_client is None:
            if self._langfuse_enabled:
                self._groq_client = AsyncOpenAILangfuse(
                    api_key=settings.GROQ_API_KEY or "dummy-key",
                    base_url="https://api.groq.com/openai/v1"
                )
            else:
                self._groq_client = AsyncOpenAI(
                    api_key=settings.GROQ_API_KEY or "dummy-key",
                    base_url="https://api.groq.com/openai/v1"
                )
        return self._groq_client

    @property
    def instructor_openai(self):
        if self._instructor_openai is None:
            self._instructor_openai = instructor.from_openai(self.openai)
        return self._instructor_openai

    @property
    def instructor_groq(self):
        if self._instructor_groq is None:
            self._instructor_groq = instructor.from_openai(self.groq)
        return self._instructor_groq

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

    def get_structured_client(self, preferred_provider: str = "groq"):
        """Returns instructor client based on configured keys and preference."""
        # Prefer Groq for fast, cost-effective inference
        if preferred_provider == "groq" and settings.GROQ_API_KEY:
            return self.instructor_groq, settings.DEFAULT_REASONING_LLM
        
        # Fallback to OpenAI
        if settings.OPENAI_API_KEY:
            return self.instructor_openai, settings.DEFAULT_FAST_LLM
        
        # Last resort: Anthropic
        if settings.ANTHROPIC_API_KEY:
            return self.instructor_anthropic, settings.DEFAULT_REASONING_LLM
        
        raise ValueError("No LLM API keys configured. Please set GROQ_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY")

llm_router = LLMRouter()

