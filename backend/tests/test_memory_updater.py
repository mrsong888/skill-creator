import json

from src.memory.updater import parse_memory_update_response


def test_parse_update_response_with_facts():
    response = json.dumps({
        "context_updates": {"workContext": "Now building a Chrome extension"},
        "new_facts": [
            {"content": "Prefers TypeScript for frontend", "category": "preference", "confidence": 0.85}
        ],
        "remove_fact_ids": [],
    })
    result = parse_memory_update_response(response)
    assert result["context_updates"]["workContext"] == "Now building a Chrome extension"
    assert len(result["new_facts"]) == 1
    assert result["new_facts"][0]["content"] == "Prefers TypeScript for frontend"


def test_parse_update_response_empty():
    response = json.dumps({"context_updates": {}, "new_facts": [], "remove_fact_ids": []})
    result = parse_memory_update_response(response)
    assert result["context_updates"] == {}
    assert result["new_facts"] == []


def test_parse_invalid_response():
    result = parse_memory_update_response("not json")
    assert result["context_updates"] == {}
    assert result["new_facts"] == []
