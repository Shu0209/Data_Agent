"""NeMo Guardrails runtime manager and evaluation rails for AI Data Agent.

This module initializes the LLMRails engine using Colang rules and YAML configs,
providing both synchronous and asynchronous interfaces for input validation,
security filtering, and topic moderation.
"""

from openai.types.beta import beta_response_format_text_config_param
import os
from typing import Optional, Dict, Any
from nemoguardrails import LLMRails, RailsConfig
from data_agent.config import settings
from data_agent.guardrails.colang_rules import COLANG_RULES, YAML_CONFIG
from data_agent.models.schemas import AgentSchema


# Ensure OpenAI client within NeMo Guardrails points to Groq API
if settings.groq_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.groq_api_key)
if settings.groq_model_api_base:
    os.environ.setdefault("OPENAI_BASE_URL", settings.groq_model_api_base)


_rails_instance: Optional[LLMRails] = None


def get_rails(force_reload: bool = False) -> LLMRails:
    """Initialize and return the singleton LLMRails engine instance.

    Args:
        force_reload (bool): If True, reinstantiates the RailsConfig and LLMRails.

    Returns:
        LLMRails: The initialized NeMo Guardrails execution runtime.
    """
    global _rails_instance
    if _rails_instance is None or force_reload:
        config = RailsConfig.from_content(
            colang_content=COLANG_RULES, yaml_content=YAML_CONFIG
        )
        _rails_instance = LLMRails(config)
    return _rails_instance


def check_guardrails(user_input: str) -> Dict[str, Any]:
    """Evaluate user input against defined guardrails synchronously.

    Args:
        user_input (str): The raw user query or prompt.

    Returns:
        Dict[str, Any]: Assessment outcome with keys:
            - is_allowed (bool): True if the query is a valid data request.
            - bot_response (str): The guardrail response (refusal or direct reply).
            - flagged (bool): True if input triggered off-topic, jailbreak, or destructive rule.
            - reason (str): Human-readable explanation.
    """
    rails = get_rails()
    response = rails.generate(messages=[{"role": "user", "content": user_input}])

    # Extract textual response
    if isinstance(response, dict):
        bot_text = response.get("content", "").strip()
    else:
        bot_text = str(response).strip()

    # Determine if a guardrail refusal or direct response was triggered
    refusal_keywords = [
        "security violation",
        "cannot assist with general",
        "strictly forbidden",
        "cannot comply with requests that attempt to override",
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
    ]

    is_refusal = any(keyword in bot_text.lower() for keyword in refusal_keywords)

    is_greeting_or_info = any(
        keyword in bot_text.lower()
        for keyword in [
            "hello! i am your ai data agent",
            "hello! how can i assist you today?",
            "autonomous sql analytics agent",
            "i can help you with a wide range of tasks",
        ]
    )

    if is_refusal:
        return {
            "is_allowed": False,
            "bot_response": bot_text,
            "flagged": True,
            "reason": "Input violated security, destructive SQL, or off-topic guardrails.",
        }
    elif is_greeting_or_info:
        return {
            "is_allowed": False,
            "bot_response": bot_text,
            "flagged": False,
            "reason": "Direct greeting or capabilities query handled by guardrails.",
        }
    else:
        return {
            "is_allowed": True,
            "bot_response": bot_text,
            "flagged": False,
            "reason": "Query conforms to data analytics guardrails.",
        }


async def async_check_guardrails(user_input: str) -> Dict[str, Any]:
    """Evaluate user input against defined guardrails asynchronously.

    Args:
        user_input (str): The raw user prompt.

    Returns:
        Dict[str, Any]: Assessment outcome matching check_guardrails.
    """
    rails = get_rails()
    response = await rails.generate_async(
        messages=[{"role": "user", "content": user_input}]
    )

    if isinstance(response, dict):
        bot_text = response.get("content", "").strip()
    else:
        bot_text = str(response).strip()

    refusal_keywords = [
        "security violation",
        "cannot assist with general",
        "strictly forbidden",
        "cannot comply with requests that attempt to override",
        "i am an ai data agent specifically designed",
        "i'm sorry, i can't respond to that",
        "i am sorry, but i cannot",
        "cannot answer",
        "can't respond",
        "i cannot fulfill this request",
    ]

    is_refusal = any(keyword in bot_text.lower() for keyword in refusal_keywords)
    is_greeting_or_info = any(
        k in bot_text.lower()
        for k in ["hello! i am your ai data agent", "autonomous sql analytics agent"]
    )

    if is_refusal:
        return {
            "is_allowed": False,
            "bot_response": bot_text,
            "flagged": True,
            "reason": "Input violated security, destructive SQL, or off-topic guardrails.",
        }
    elif is_greeting_or_info:
        return {
            "is_allowed": False,
            "bot_response": bot_text,
            "flagged": False,
            "reason": "Direct greeting or capabilities query handled by guardrails.",
        }
    else:
        return {
            "is_allowed": True,
            "bot_response": bot_text,
            "flagged": False,
            "reason": "Query conforms to data analytics guardrails.",
        }


def guardrails_node(state: AgentSchema) -> AgentSchema:
    """LangGraph node to integrate NeMo Guardrails as an input filter.

    If input is rejected by safety or off-topic guardrails, halts execution
    and populates final_answer with the guardrail response.
    """
    user_query = state.user_input
    result = check_guardrails(user_query)

    if not result["is_allowed"]:
        state.is_safe = "No"
        state.comments = result["reason"]
        state.final_answer = result["bot_response"]
    else:
        state.is_safe = "Yes"

    return state
