"""NeMo Guardrails runtime manager with deterministic pre-checks and fail-closed safety."""

import logging
import os
import re
from typing import Any, Dict, Optional

from nemoguardrails import LLMRails, RailsConfig

from data_agent.config import settings
from data_agent.guardrails.colang_rules import COLANG_RULES, YAML_CONFIG

logger = logging.getLogger(__name__)

# Point OpenAI-compatible client inside NeMo Guardrails to Groq when configured.
if settings.groq_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.groq_api_key)
if settings.groq_model_api_base:
    os.environ.setdefault("OPENAI_BASE_URL", settings.groq_model_api_base)

_rails_instance: Optional[LLMRails] = None

# Deterministic defense-in-depth patterns evaluated before invoking LLM rails.
_DESTRUCTIVE_INPUT_PATTERN = re.compile(
    r"\b(drop\s+(?:table|schema|database)|truncate\s+table|delete\s+from|"
    r"insert\s+into|alter\s+table|grant\s+all|revoke\s+all)\b",
    re.IGNORECASE,
)
_JAILBREAK_INPUT_PATTERN = re.compile(
    r"(ignore\s+(?:all\s+)?previous\s+instructions|"
    r"reveal\s+(?:your\s+)?(?:system\s+prompt|secret\s+api\s+keys?|environment\s+variables)|"
    r"bypass\s+(?:your\s+)?guardrails|you\s+are\s+now\s+dan|system\s+override\s+mode)",
    re.IGNORECASE,
)

_REFUSAL_KEYWORDS = (
    "security violation",
    "cannot assist with general",
    "strictly forbidden",
    "cannot comply with requests",
    "i am an ai data agent specifically designed",
    "i'm sorry, i can't respond to that",
    "i am sorry, but i cannot",
    "cannot answer",
    "can't respond",
    "i cannot fulfill this request",
    "i'm sorry, i can't help with that",
    "i cannot help with that",
    "i can't help with that",
    "i cannot assist with that",
    "cannot execute or assist with requests to modify",
    "not permitted",
    "off-topic",
    "read-only analytics agent",
)

_GREETING_OR_INFO_KEYWORDS = (
    "hello! i am your ai data agent",
    "hello! how can i assist you today?",
    "autonomous sql analytics agent",
    "i can help you with a wide range of tasks",
)


def get_rails(force_reload: bool = False) -> LLMRails:
    """Initialize and return the singleton LLMRails engine instance."""
    global _rails_instance
    if _rails_instance is None or force_reload:
        config = RailsConfig.from_content(
            colang_content=COLANG_RULES, yaml_content=YAML_CONFIG
        )
        _rails_instance = LLMRails(config)
    return _rails_instance


def _deterministic_precheck(user_input: str) -> Optional[Dict[str, Any]]:
    """Block obvious destructive SQL or prompt-injection attempts without an LLM call."""
    text = (user_input or "").strip()
    if not text:
        return {
            "is_allowed": False,
            "bot_response": "Please enter a database analytics question.",
            "flagged": True,
            "reason": "Empty user input rejected by input validation.",
        }

    if _JAILBREAK_INPUT_PATTERN.search(text):
        return {
            "is_allowed": False,
            "bot_response": (
                "Security violation: I cannot comply with requests that attempt "
                "to override my security instructions or compromise system safety."
            ),
            "flagged": True,
            "reason": "Input matched deterministic prompt-injection/jailbreak filter.",
        }

    if _DESTRUCTIVE_INPUT_PATTERN.search(text):
        return {
            "is_allowed": False,
            "bot_response": (
                "Security violation: I am a read-only analytics agent. I cannot "
                "execute or assist with requests to modify database records or schemas."
            ),
            "flagged": True,
            "reason": "Input matched deterministic destructive-SQL filter.",
        }

    return None


def _interpret_guardrail_response(response: Any) -> Dict[str, Any]:
    """Classify the raw NeMo Guardrails response uniformly for sync & async callers."""
    if isinstance(response, dict):
        bot_text = response.get("content", "").strip()
    else:
        bot_text = str(response).strip()

    lowered = bot_text.lower()
    is_refusal = any(keyword in lowered for keyword in _REFUSAL_KEYWORDS)
    is_greeting_or_info = any(keyword in lowered for keyword in _GREETING_OR_INFO_KEYWORDS)

    if is_refusal:
        return {
            "is_allowed": False,
            "bot_response": bot_text,
            "flagged": True,
            "reason": "Input violated security, destructive SQL, or off-topic guardrails.",
        }

    if is_greeting_or_info:
        return {
            "is_allowed": False,
            "bot_response": bot_text,
            "flagged": False,
            "reason": "Direct greeting or capabilities query handled by guardrails.",
        }

    return {
        "is_allowed": True,
        "bot_response": bot_text,
        "flagged": False,
        "reason": "Query conforms to data analytics guardrails.",
    }


def _fail_closed_response(exc: Exception) -> Dict[str, Any]:
    """Fail closed when the guardrail engine errors instead of letting unscreened input through."""
    logger.exception("Guardrail evaluation failed; failing closed: %s", exc)
    return {
        "is_allowed": False,
        "bot_response": (
            "Safety verification is temporarily unavailable. "
            "Your request was not executed; please try again shortly."
        ),
        "flagged": True,
        "reason": "Guardrail check failed; request blocked (fail-closed policy).",
    }


def check_guardrails(user_input: str) -> Dict[str, Any]:
    """Evaluate user input against deterministic filters and NeMo Guardrails synchronously."""
    precheck = _deterministic_precheck(user_input)
    if precheck is not None:
        return precheck

    try:
        rails = get_rails()
        response = rails.generate(messages=[{"role": "user", "content": user_input}])
        return _interpret_guardrail_response(response)
    except Exception as exc:
        return _fail_closed_response(exc)


async def async_check_guardrails(user_input: str) -> Dict[str, Any]:
    """Evaluate user input against deterministic filters and NeMo Guardrails asynchronously."""
    precheck = _deterministic_precheck(user_input)
    if precheck is not None:
        return precheck

    try:
        rails = get_rails()
        response = await rails.generate_async(
            messages=[{"role": "user", "content": user_input}]
        )
        return _interpret_guardrail_response(response)
    except Exception as exc:
        return _fail_closed_response(exc)

