import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import litellm

from src.agent.tools import BUILT_IN_TOOLS, execute_tool


class AgentCore:
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.7, max_tokens: int = 4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def run(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        workspace_root: Path | None = None,
        max_tool_rounds: int = 10,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run the agent loop, yielding SSE-compatible events."""
        all_tools = list(BUILT_IN_TOOLS)
        if tools:
            all_tools.extend(tools)

        llm_messages = []
        if system_prompt:
            llm_messages.append({"role": "system", "content": system_prompt})
        llm_messages.extend(messages)

        for _ in range(max_tool_rounds):
            response = await litellm.acompletion(
                model=self.model,
                messages=llm_messages,
                tools=all_tools if all_tools else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            if assistant_msg.tool_calls:
                llm_messages.append({
                    "role": "assistant",
                    "content": assistant_msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in assistant_msg.tool_calls
                    ],
                })

                for tc in assistant_msg.tool_calls:
                    yield {
                        "type": "tool_use",
                        "data": {"tool": tc.function.name, "input": json.loads(tc.function.arguments), "status": "running"},
                    }

                    args = json.loads(tc.function.arguments)
                    result = await execute_tool(tc.function.name, args, workspace_root)

                    yield {
                        "type": "tool_result",
                        "data": {"tool": tc.function.name, "output": result},
                    }

                    llm_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

                continue

            if assistant_msg.content:
                yield {"type": "content_delta", "data": {"delta": assistant_msg.content}}

            yield {"type": "message_end", "data": {"finish_reason": choice.finish_reason}}
            return

        yield {"type": "message_end", "data": {"finish_reason": "max_tool_rounds"}}
