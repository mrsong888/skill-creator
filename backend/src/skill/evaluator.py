import json
import logging

import litellm

logger = logging.getLogger(__name__)

EVALUATION_PROMPT = """You are a skill quality evaluator. Analyze the following SKILL.md content and evaluate it across these dimensions:

1. **Clarity** (0-10): Is the skill's purpose and behavior clearly described?
2. **Completeness** (0-10): Does it cover all necessary instructions for the agent?
3. **Actionability** (0-10): Can an AI agent follow these instructions without ambiguity?
4. **Structure** (0-10): Is the content well-organized with proper formatting?
5. **Best Practices** (0-10): Does it follow skill authoring best practices?

SKILL.md content:
```
{skill_md}
```

Respond with ONLY a JSON object (no markdown code fences) in this exact format:
{{
  "score": <overall score 0-10>,
  "dimensions": {{
    "clarity": {{"score": <0-10>, "feedback": "<brief feedback>"}},
    "completeness": {{"score": <0-10>, "feedback": "<brief feedback>"}},
    "actionability": {{"score": <0-10>, "feedback": "<brief feedback>"}},
    "structure": {{"score": <0-10>, "feedback": "<brief feedback>"}},
    "best_practices": {{"score": <0-10>, "feedback": "<brief feedback>"}}
  }},
  "suggestions": ["<suggestion 1>", "<suggestion 2>"]
}}"""


async def evaluate_skill_quality(
    skill_md: str,
    model: str = "gpt-4o",
    api_key: str = "",
    base_url: str = "",
) -> dict:
    """Evaluate skill quality using LLM."""
    prompt = EVALUATION_PROMPT.format(skill_md=skill_md)

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["api_base"] = base_url

    try:
        response = await litellm.acompletion(**kwargs)
        text = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM evaluation response: {e}")
        return {"score": 0, "suggestions": ["Evaluation failed: could not parse LLM response"], "error": str(e)}
    except Exception as e:
        logger.error(f"Skill evaluation failed: {e}", exc_info=True)
        return {"score": 0, "suggestions": [f"Evaluation failed: {e}"], "error": str(e)}
