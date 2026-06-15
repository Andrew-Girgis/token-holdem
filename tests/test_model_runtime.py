from token_holdem.agents import AgentProfile
from token_holdem.model_runtime import TransformersRuntime, apply_poker_sanity_guard, first_valid_decision, finalize_table_talk, parse_model_json, safe_action, sanitize_table_talk, validate_decision


LEGAL = {
    "actions": ["fold", "call", "raise", "all_in"],
    "to_call": 20,
    "raise_presets": {"min": 40, "half_pot": 80, "pot": 140, "all_in": 500},
}


def test_parse_model_json_extracts_object_from_extra_text():
    parsed = parse_model_json('thinking... {"action":"call","amount":0,"table_talk":"cheers"} done')

    assert parsed == {"action": "call", "amount": 0, "table_talk": "cheers"}


def test_first_valid_decision_skips_invalid_schema_object():
    text = '{"action":"fold|check|call|raise|all_in","amount":0,"table_talk":"schema"}\n{"action":"check","amount":0,"table_talk":"The candle can wait."}'
    legal = {"actions": ["check", "raise", "all_in"], "to_call": 0, "raise_presets": {"min": 20, "half_pot": 40, "pot": 80, "all_in": 980}}

    assert first_valid_decision(text, legal) == {"action": "check", "amount": 0, "reasoning_hint": "", "table_talk": "The candle can wait"}


def test_validate_decision_clamps_raise_to_preset():
    decision = validate_decision({"action": "raise", "amount": 91, "table_talk": "I raise by candlelight."}, LEGAL)

    assert decision == {"action": "raise", "amount": 80, "reasoning_hint": "", "table_talk": "The cards clink like tiny mugs."}


def test_sanitize_table_talk_removes_numbers_and_action_claims():
    talk = sanitize_table_talk("I'm raising 955 to make the pot bigger. Let's see...")

    assert "955" not in talk
    assert "raising" not in talk.lower()
    assert talk == "to make the pot bigger"


def test_sanitize_table_talk_rejects_prompt_leakage():
    assert sanitize_table_talk('No markdown. Your first sentence must be: "take all the chips"') == ""
    assert sanitize_table_talk("Don't mention any other players. Now think carefully.") == ""
    assert sanitize_table_talk("short cozy poker banter") == ""


def test_finalize_table_talk_avoids_recent_repetition():
    profile = AgentProfile("Gemma", "local", "warm", 0.3, 0.1, ())
    state = {"seed": 1, "street": "preflop", "history": [], "recent_chats": ["Gemma: I am curious enough to stay by the fire."]}

    talk = finalize_table_talk(profile, "call", "I am curious enough to stay by the fire.", state)

    assert talk != "I am curious enough to stay by the fire."
    assert len(talk.split()) >= 3


def test_validate_decision_rejects_illegal_action():
    assert validate_decision({"action": "dance", "amount": 0}, LEGAL) is None


def test_safe_action_prefers_call_when_check_unavailable():
    assert safe_action(LEGAL)["action"] == "call"


def test_poker_sanity_guard_folds_weak_hand_to_huge_all_in():
    decision = {"action": "call", "amount": 0, "table_talk": "I call."}
    summary = {
        "hole_cards": ["Kd", "5c"],
        "community_cards": ["Qs", "Ts", "8s", "6s"],
        "pot": 1060,
        "legal": {"actions": ["fold", "call", "all_in"], "to_call": 980, "raise_presets": {"all_in": 980}},
    }

    assert apply_poker_sanity_guard(decision, summary)["action"] == "fold"


def test_poker_sanity_guard_allows_made_flush_call():
    decision = {"action": "call", "amount": 0, "table_talk": "I call."}
    summary = {
        "hole_cards": ["3s", "3d"],
        "community_cards": ["Qs", "Ts", "8s", "6s"],
        "pot": 1060,
        "legal": {"actions": ["fold", "call", "all_in"], "to_call": 980, "raise_presets": {"all_in": 980}},
    }

    assert apply_poker_sanity_guard(decision, summary)["action"] == "call"


def test_transformers_runtime_unsupported_model_uses_persona_fallback():
    runtime = TransformersRuntime()
    profile = AgentProfile("Unknown Seat", "local/unknown", "mysterious", 0.5, 0.1, ("A mysterious chip appears.",))
    result = runtime.decide(
        profile,
        {
            "hand_no": 1,
            "street": "preflop",
            "hole_cards": ["As", "Kd"],
            "community_cards": [],
            "stack": 1000,
            "pot": 30,
            "legal": LEGAL,
            "history": [],
            "seed": 123,
        },
    )

    assert result.source == "fallback"
    assert result.decision["action"] in LEGAL["actions"]
    assert result.decision["table_talk"] not in profile.talk
    assert "No local Transformers mapping" in result.status
