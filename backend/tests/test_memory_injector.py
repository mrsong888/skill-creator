from src.memory.injector import format_memory_for_injection


def test_format_empty_memory():
    memory = {
        "context": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "facts": [],
    }
    result = format_memory_for_injection(memory)
    assert result == ""


def test_format_with_context():
    memory = {
        "context": {
            "workContext": {"summary": "Building AI tools", "updatedAt": "2026-03-12"},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "Launching Chrome extension", "updatedAt": "2026-03-12"},
        },
        "facts": [],
    }
    result = format_memory_for_injection(memory)
    assert "Building AI tools" in result
    assert "Launching Chrome extension" in result


def test_format_with_facts():
    memory = {
        "context": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "facts": [
            {"id": "f1", "content": "Prefers Python", "category": "preference", "confidence": 0.95},
            {"id": "f2", "content": "Uses dark mode", "category": "preference", "confidence": 0.5},
        ],
    }
    result = format_memory_for_injection(memory, min_confidence=0.7)
    assert "Prefers Python" in result
    assert "Uses dark mode" not in result


def test_max_facts_limit():
    memory = {
        "context": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "facts": [
            {"id": f"f{i}", "content": f"Fact {i}", "category": "knowledge", "confidence": 0.9}
            for i in range(20)
        ],
    }
    result = format_memory_for_injection(memory, max_facts=5)
    assert result.count("Fact ") == 5
