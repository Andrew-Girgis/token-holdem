from token_holdem.agents import AgentProfile, ROSTER
import pytest

from token_holdem.model_runtime import (
    LocalRuntime,
    ModalRuntime,
    ModelRuntimeUnavailable,
    SUPPORTED_TRANSFORMERS_MODELS,
    TransformersRuntime,
    apply_poker_sanity_guard,
    finalize_table_talk,
    first_valid_decision,
    get_model_runtime,
    parse_model_json,
    requires_gguf_runtime,
    safe_action,
    sanitize_table_talk,
    validate_decision,
)


LEGAL = {
    "actions": ["fold", "call", "raise", "all_in"],
    "to_call": 20,
    "raise_presets": {"min": 40, "half_pot": 80, "pot": 140, "all_in": 500},
}


def summary(**overrides):
    value = {
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
    value.update(overrides)
    return value


class FakeModalCall:
    def __init__(self, response):
        self.response = response
        self.timeout = None

    def get(self, timeout=None):
        self.timeout = timeout
        return self.response


class FakeModalFunction:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []
        self.last_call = None

    def spawn(self, *args):
        self.calls.append(args)
        if self.error:
            raise self.error
        self.last_call = FakeModalCall(self.response)
        return self.last_call


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


def test_supported_model_mapping_uses_roster_model_ids():
    roster_model_ids = {profile.name: profile.model_id for profile in ROSTER}

    assert SUPPORTED_TRANSFORMERS_MODELS == roster_model_ids
    assert len(set(SUPPORTED_TRANSFORMERS_MODELS.values())) == len(SUPPORTED_TRANSFORMERS_MODELS)


def test_transformers_runtime_unsupported_model_fails_without_dev_fallback():
    runtime = TransformersRuntime()
    profile = AgentProfile("Unknown Seat", "local/unknown", "mysterious", 0.5, 0.1, ("A mysterious chip appears.",))

    with pytest.raises(ModelRuntimeUnavailable, match="No local Transformers mapping"):
        runtime.decide(profile, summary())


def test_transformers_runtime_dev_fallback_is_explicit():
    runtime = TransformersRuntime(allow_fallback=True)
    profile = AgentProfile("Unknown Seat", "local/unknown", "mysterious", 0.5, 0.1, ("A mysterious chip appears.",))

    result = runtime.decide(profile, summary())

    assert result.source == "fallback"
    assert result.decision["action"] in LEGAL["actions"]
    assert result.decision["table_talk"] not in profile.talk
    assert "No local Transformers mapping" in result.status


def test_transformers_runtime_gguf_model_fails_without_dev_fallback():
    runtime = TransformersRuntime()
    profile = next(profile for profile in ROSTER if requires_gguf_runtime(profile.model_id))

    with pytest.raises(ModelRuntimeUnavailable, match="local runtime cannot call it"):
        runtime.decide(profile, summary())


def test_transformers_runtime_gguf_model_dev_fallback_is_explicit():
    runtime = TransformersRuntime(allow_fallback=True)
    profile = next(profile for profile in ROSTER if requires_gguf_runtime(profile.model_id))

    result = runtime.decide(profile, summary())

    assert result.source == "fallback"
    assert result.decision["action"] in LEGAL["actions"]
    assert "local runtime cannot call it" in result.status


def test_transformers_runtime_alias_keeps_local_runtime_compatibility():
    assert TransformersRuntime is LocalRuntime


def test_explicit_deterministic_bot_env_selects_dev_runtime(monkeypatch):
    monkeypatch.setenv("TOKEN_HOLDEM_ALLOW_DETERMINISTIC_BOTS", "1")
    monkeypatch.delenv("USE_MODAL_INFERENCE", raising=False)
    profile = next(profile for profile in ROSTER if profile.name == "Gemma")

    result = get_model_runtime().decide(profile, summary())

    assert result.source == "deterministic_dev"
    assert result.decision["action"] in LEGAL["actions"]


def test_modal_runtime_success_uses_structured_remote_decision():
    remote = FakeModalFunction(
        {
            "action": "call",
            "bet_amount": 0,
            "explanation": "priced in",
            "commentary": "The candlelight keeps me curious.",
            "raw_model_output": '{"action":"call","amount":0}',
            "error": None,
        }
    )
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_function=remote, timeout_seconds=3)
    profile = next(profile for profile in ROSTER if profile.name == "Gemma")

    result = runtime.decide(profile, summary())

    assert result.source == "modal_model"
    assert result.status == profile.model_id
    assert result.decision["action"] == "call"
    assert result.decision["table_talk"] == "The candlelight keeps me curious"
    assert remote.last_call.timeout == 3
    assert remote.calls[0][1:5] == (profile.name, profile.persona, profile.model_id, LEGAL)


def test_modal_runtime_failure_raises_instead_of_falling_back():
    remote = FakeModalFunction(error=TimeoutError("modal timed out"))
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_function=remote)
    profile = next(profile for profile in ROSTER if profile.name == "Gemma")

    with pytest.raises(ModelRuntimeUnavailable, match="Modal inference unavailable"):
        runtime.decide(profile, summary())


def test_modal_runtime_remote_error_raises_instead_of_falling_back():
    remote = FakeModalFunction(
        {
            "action": None,
            "bet_amount": None,
            "explanation": "",
            "commentary": "",
            "raw_model_output": "",
            "error": "model did not return valid decision JSON",
        }
    )
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_function=remote)
    profile = next(profile for profile in ROSTER if profile.name == "Gemma")

    with pytest.raises(ModelRuntimeUnavailable, match="Modal inference returned an error"):
        runtime.decide(profile, summary())


def test_modal_runtime_disabled_model_raises():
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_function=FakeModalFunction({}))
    profile = next(profile for profile in ROSTER if profile.name == "Qwen")

    with pytest.raises(ModelRuntimeUnavailable, match="disabled"):
        runtime.decide(profile, summary())


def test_modal_runtime_all_enabled_models_spawn_remote_calls():
    remote = FakeModalFunction(
        {
            "action": "call",
            "bet_amount": 0,
            "explanation": "priced in",
            "commentary": "The candlelight keeps me curious.",
            "raw_model_output": '{"action":"call","amount":0}',
            "error": None,
        }
    )
    runtime = ModalRuntime(enabled_model_names={profile.name for profile in ROSTER}, remote_function=remote)

    for profile in ROSTER:
        result = runtime.decide(profile, summary())
        assert result.source == "modal_model"

    called_names = [call[1] for call in remote.calls]
    assert called_names == [profile.name for profile in ROSTER]
