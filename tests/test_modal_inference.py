import modal_inference


LEGAL = {
    "actions": ["fold", "call", "raise", "all_in"],
    "to_call": 20,
    "raise_presets": {"min": 40, "half_pot": 80, "pot": 140, "all_in": 500},
}


def summary():
    return {
        "hand_no": 1,
        "street": "preflop",
        "hole_cards": ["As", "Kd"],
        "community_cards": [],
        "stack": 1000,
        "pot": 30,
        "legal": LEGAL,
        "history": [],
        "recent_chats": [],
        "seed": 123,
        "session_id": "test-session",
        "hand_id": "test-hand",
        "orbit_id": "test-orbit",
    }


def test_gemma_4_uses_multimodal_processor_loader(monkeypatch):
    calls = []

    def fail_generic_loader(model_id):
        raise AssertionError(f"generic causal-LM loader used for {model_id}")

    def fake_multimodal_loader(model_id):
        calls.append(("load_multimodal", model_id))
        return object(), object()

    def fake_multimodal_generate(model, processor, prompt, max_new_tokens, temperature):
        calls.append(("generate_multimodal", max_new_tokens, temperature))
        if max_new_tokens == 192:
            return '{"action":"call","amount":0,"reasoning_hint":"priced in"}'
        return "The candlelight keeps me curious."

    monkeypatch.setattr(modal_inference, "_load_model", fail_generic_loader)
    monkeypatch.setattr(modal_inference, "_load_multimodal_model", fake_multimodal_loader)
    monkeypatch.setattr(modal_inference, "_generate_multimodal_text", fake_multimodal_generate)

    result = modal_inference._run_agent_decision_impl(
        summary(),
        "Gemma",
        "cautious, methodical, warm",
        "google/gemma-4-12B-it",
        LEGAL,
        "visible poker state",
    )

    assert result["error"] is None
    assert result["action"] == "call"
    assert result["commentary"] == "The candlelight keeps me curious"
    assert calls == [
        ("load_multimodal", "google/gemma-4-12B-it"),
        ("generate_multimodal", 192, 0.7),
        ("generate_multimodal", 48, 0.9),
    ]
