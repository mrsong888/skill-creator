from src.agent.prompt import build_system_prompt


def test_base_prompt_only():
    prompt = build_system_prompt()
    assert "You are a helpful AI assistant" in prompt


def test_with_memory():
    memory_text = "**Work Context:** Building AI tools"
    prompt = build_system_prompt(memory_text=memory_text)
    assert "<memory>" in prompt
    assert "Building AI tools" in prompt


def test_with_skill():
    skill_content = "You are a code reviewer. Review code carefully."
    prompt = build_system_prompt(skill_content=skill_content)
    assert "<skill>" in prompt
    assert "code reviewer" in prompt


def test_with_page_context():
    page = "Title: Example\nContent: This is a web page about Python."
    prompt = build_system_prompt(page_context=page)
    assert "<page_context>" in prompt
    assert "Python" in prompt


def test_full_assembly():
    prompt = build_system_prompt(
        memory_text="Work: AI",
        skill_content="Review code",
        page_context="Page about JS",
    )
    assert "<memory>" in prompt
    assert "<skill>" in prompt
    assert "<page_context>" in prompt
