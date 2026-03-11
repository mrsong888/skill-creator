from unittest.mock import AsyncMock, patch

from src.agent.core import AgentCore


async def test_agent_simple_response():
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "Hello! How can I help?"
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].finish_reason = "stop"

    with patch("litellm.acompletion", return_value=mock_response):
        agent = AgentCore(model="gpt-4o")
        chunks = []
        async for event in agent.run([{"role": "user", "content": "Hi"}]):
            chunks.append(event)

        assert any(e["type"] == "content_delta" for e in chunks)
        assert any(e["type"] == "message_end" for e in chunks)


async def test_agent_with_system_prompt():
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "I'm a reviewer."
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].finish_reason = "stop"

    with patch("litellm.acompletion", return_value=mock_response) as mock_llm:
        agent = AgentCore(model="gpt-4o")
        chunks = []
        async for event in agent.run(
            [{"role": "user", "content": "Who are you?"}],
            system_prompt="You are a code reviewer.",
        ):
            chunks.append(event)

        call_args = mock_llm.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "code reviewer" in messages[0]["content"]
