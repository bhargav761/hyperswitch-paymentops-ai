from app.ai.rag_grounding import build_grounded_prompt


def test_build_grounded_prompt_includes_retrieved_guidance():
    context = {
        "recovery_guidance": [
            {
                "id": "network-failure",
                "title": "Network failure",
                "guidance": "Prefer retry or reroute when the failure is transient.",
                "score": 2,
            }
        ]
    }

    prompt = build_grounded_prompt(
        user_prompt="What should we recommend?",
        context=context,
    )

    assert "Network failure" in prompt
    assert "Prefer retry or reroute" in prompt
    assert "Do not invent payment facts" in prompt
    assert "What should we recommend?" in prompt


def test_build_grounded_prompt_handles_missing_guidance():
    prompt = build_grounded_prompt(
        user_prompt="Analyze this payment.",
        context={},
    )

    assert "No matching recovery guidance was retrieved." in prompt
    assert "If the supplied context is insufficient" in prompt
