import instructor
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Safe optional Langfuse import
try:
    from langfuse import observe
    from langfuse.openai import AsyncOpenAI as AsyncOpenAILangfuse
    LANGFUSE_AVAILABLE = True
except Exception as e:
    logger.debug(f"Langfuse optional integration disabled: {e}")
    LANGFUSE_AVAILABLE = False
    def observe(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    AsyncOpenAILangfuse = None

class LLMRouter:
    def __init__(self):
        self._openai_client = None
        self._groq_client = None
        self._instructor_openai = None
        self._instructor_groq = None
        self._anthropic_client = None
        self._instructor_anthropic = None
        self._langfuse_enabled = bool(settings.LANGFUSE_SECRET_KEY) and LANGFUSE_AVAILABLE
        
        if self._langfuse_enabled:
            logger.info("Langfuse tracing enabled for Legal Contract Analyzer")

    @property
    def openai(self) -> AsyncOpenAI:
        if self._openai_client is None:
            if self._langfuse_enabled and AsyncOpenAILangfuse is not None:
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
            if self._langfuse_enabled and AsyncOpenAILangfuse is not None:
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

    def get_structured_client(self, preferred_provider: str = "openai"):
        """Returns instructor client based on configured keys and preference.
        Priority: OpenAI → Groq → Anthropic
        """
        # OpenAI is the primary provider for structured output (Instructor works best)
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
            return self.instructor_openai, settings.DEFAULT_FAST_LLM

        # Groq as fast free-tier fallback (excellent for structured output)
        if settings.GROQ_API_KEY:
            return self.instructor_groq, "llama-3.3-70b-versatile"

        # Last resort: Anthropic
        if settings.ANTHROPIC_API_KEY:
            return self.instructor_anthropic, "claude-3-haiku-20240307"

        raise ValueError("No LLM API keys configured. Please set OPENAI_API_KEY, GROQ_API_KEY, or ANTHROPIC_API_KEY")

llm_router = LLMRouter()

