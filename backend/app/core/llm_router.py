import os
import instructor
from openai import AsyncOpenAI
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
        self._gemini_client = None
        self._instructor_openai = None
        self._instructor_groq = None
        self._instructor_gemini = None
        
        # Only enable Langfuse if both public and secret keys are non-empty
        self._langfuse_enabled = bool(
            settings.LANGFUSE_PUBLIC_KEY and 
            settings.LANGFUSE_SECRET_KEY and 
            LANGFUSE_AVAILABLE
        )
        if self._langfuse_enabled:
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
            os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
            os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST
            logger.info("Langfuse tracing enabled for Legal Contract Analyzer")

    @property
    def openai(self) -> AsyncOpenAI:
        if self._openai_client is None:
            if self._langfuse_enabled and AsyncOpenAILangfuse is not None:
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
            self._groq_client = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY or "dummy-key",
                base_url="https://api.groq.com/openai/v1"
            )
        return self._groq_client

    @property
    def gemini(self) -> AsyncOpenAI:
        """Google Gemini client via official OpenAI-compatible endpoint"""
        if self._gemini_client is None:
            self._gemini_client = AsyncOpenAI(
                api_key=settings.GEMINI_API_KEY or "dummy-key",
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        return self._gemini_client

    @property
    def instructor_openai(self):
        if self._instructor_openai is None:
            self._instructor_openai = instructor.from_openai(self.openai)
        return self._instructor_openai

    @property
    def instructor_groq(self):
        if self._instructor_groq is None:
            # MD_JSON generates structured JSON schema in prompt without requiring native tool-calling,
            # ensuring compatibility with all Groq models including qwen/qwen3.8-27b
            self._instructor_groq = instructor.from_openai(self.groq, mode=instructor.Mode.MD_JSON)
        return self._instructor_groq

    @property
    def instructor_gemini(self):
        if self._instructor_gemini is None:
            self._instructor_gemini = instructor.from_openai(self.gemini, mode=instructor.Mode.MD_JSON)
        return self._instructor_gemini

    def get_structured_client(self, preferred_provider: str = "groq"):
        """Returns instructor client based on configured keys and preference.
        Priority: Groq (fast & active) → OpenAI → Gemini
        """
        # Groq as primary fast LLM inference provider
        if settings.GROQ_API_KEY:
            return self.instructor_groq, settings.DEFAULT_REASONING_LLM

        # OpenAI fallback
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
            return self.instructor_openai, settings.DEFAULT_FAST_LLM

        # Fallback: Google Gemini
        if settings.GEMINI_API_KEY:
            return self.instructor_gemini, "gemini-1.5-flash"

        raise ValueError("No LLM API keys configured. Please set GROQ_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY")

    async def generate_chat_completion(
        self,
        messages: list,
        temperature: float = 0.1,
        max_tokens: int = 1500
    ) -> str:
        """
        Robust multi-provider chat completion:
        1. Tries Groq (Active free-tier with qwen/qwen3.8-27b)
        2. Tries OpenAI (if configured and quota available)
        3. Tries Gemini (fallback)
        4. Raises exception to trigger domain fallback
        """
        # 1. Try Groq
        if settings.GROQ_API_KEY:
            try:
                res = await self.groq.chat.completions.create(
                    model=settings.DEFAULT_REASONING_LLM,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if res.choices and res.choices[0].message.content:
                    return res.choices[0].message.content
            except Exception as e:
                logger.warning(f"Groq chat completion attempt failed: {e}. Trying fallback...")

        # 2. Try OpenAI
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
            try:
                res = await self.openai.chat.completions.create(
                    model=settings.DEFAULT_FAST_LLM,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if res.choices and res.choices[0].message.content:
                    return res.choices[0].message.content
            except Exception as e:
                logger.warning(f"OpenAI chat completion attempt failed: {e}. Trying fallback...")

        # 3. Try Gemini fallback
        if settings.GEMINI_API_KEY:
            try:
                res = await self.gemini.chat.completions.create(
                    model="gemini-1.5-flash",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if res.choices and res.choices[0].message.content:
                    return res.choices[0].message.content
            except Exception as e:
                logger.warning(f"Gemini chat completion attempt failed: {e}")

        raise RuntimeError("All active LLM providers failed or returned empty responses.")

llm_router = LLMRouter()

