from token_holdem.agents import AgentProfile, ROSTER
import pytest

from token_holdem.model_runtime import (
    DEFAULT_MODAL_MODEL_NAMES,
    DEFAULT_MODAL_TIMEOUT_SECONDS,
    LocalRuntime,
    ModalRuntime,
    ModelRuntimeUnavailable,
    SUPPORTED_TRANSFORMERS_MODELS,
    TransformersRuntime,
    apply_poker_sanity_guard,
    configured_modal_model_names,
    finalize_table_talk,
    first_valid_decision,
    get_model_runtime,
    modal_worker_class_name,
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


class FakeRemoteMethod:
    def __init__(self, worker, response=None, error=None):
        self.worker = worker
        self.response = response
        self.error = error

    def spawn(self, *args):
        self.worker.calls.append(args)
        if self.error:
            raise self.error
        self.worker.last_call = FakeModalCall(self.response)
        return self.worker.last_call


class FakeModalWorker:
    def __init__(self, model_id=None, response=None, error=None):
        self.model_id = model_id
        self.calls = []
        self.last_call = None
        self.decide = FakeRemoteMethod(self, response=response, error=error)


class FakeModalWorkerClass:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.instances = []

    def __call__(self, *, model_id):
        worker = FakeModalWorker(model_id=model_id, response=self.response, error=self.error)
        self.instances.append(worker)
        return worker


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


def test_sanitize_table_talk_strips_outer_quotes():
    assert sanitize_table_talk('"That is a fine bluff, lad.') == "That is a fine bluff, lad"


def test_sanitize_table_talk_rejects_prompt_leakage():
    assert sanitize_table_talk('No markdown. Your first sentence must be: "take all the chips"') == ""
    assert sanitize_table_talk("Don't mention any other players. Now think carefully.") == ""
    assert sanitize_table_talk("short cozy poker banter") == ""
    assert sanitize_table_talk("If you're not already, let me know in this response what your name is and what color hat you're wearing") == ""


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


def test_configured_modal_model_names_default_includes_cohere_command(monkeypatch):
    monkeypatch.delenv("TOKEN_HOLDEM_MODAL_MODEL_NAMES", raising=False)

    names = configured_modal_model_names()

    assert names == DEFAULT_MODAL_MODEL_NAMES
    assert "Cohere Command R7B" in names
    assert "Gemma" in names


def test_configured_modal_model_names_all_explicitly_includes_cohere():
    names = configured_modal_model_names("all")

    assert names == {profile.name for profile in ROSTER}
    assert "Cohere Command R7B" in names


def test_modal_worker_class_name_routes_by_runtime_family():
    assert modal_worker_class_name("nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF") == "GgufModelWorker"
    assert modal_worker_class_name("unsloth/North-Mini-Code-1.0-GGUF") == "GgufModelWorker"
    assert modal_worker_class_name("Qwen/Qwen3-0.6B") == "CausalModelWorker"
    assert modal_worker_class_name("mistralai/Mistral-7B-Instruct-v0.2") == "CausalModelWorker"
    assert modal_worker_class_name("CohereLabs/c4ai-command-r7b-12-2024") == "CausalModelWorker"
    assert modal_worker_class_name("google/gemma-4-12B-it") == "MultimodalModelWorker"
    assert modal_worker_class_name("openai/gpt-oss-20b") == "HeavyCausalModelWorker"


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
    worker_class = FakeModalWorkerClass(
        {
            "action": "call",
            "bet_amount": 0,
            "explanation": "priced in",
            "commentary": "The candlelight keeps me curious.",
            "raw_model_output": '{"action":"call","amount":0}',
            "error": None,
        }
    )
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_workers={"MultimodalModelWorker": worker_class}, timeout_seconds=3)
    profile = next(profile for profile in ROSTER if profile.name == "Gemma")

    result = runtime.decide(profile, summary())

    worker = worker_class.instances[0]
    assert result.source == "modal_model"
    assert result.status == profile.model_id
    assert result.decision["action"] == "call"
    assert result.decision["table_talk"] == "The candlelight keeps me curious"
    assert worker.model_id == profile.model_id
    assert worker.last_call.timeout == 3
    assert worker.calls[0][1:4] == (profile.name, profile.persona, LEGAL)


def test_modal_runtime_failure_raises_instead_of_falling_back():
    worker_class = FakeModalWorkerClass(error=TimeoutError("modal timed out"))
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_workers={"MultimodalModelWorker": worker_class})
    profile = next(profile for profile in ROSTER if profile.name == "Gemma")

    with pytest.raises(ModelRuntimeUnavailable, match="Modal inference unavailable"):
        runtime.decide(profile, summary())


def test_modal_runtime_remote_error_raises_instead_of_falling_back():
    worker_class = FakeModalWorkerClass(
        {
            "action": None,
            "bet_amount": None,
            "explanation": "",
            "commentary": "",
            "raw_model_output": "",
            "error": "model did not return valid decision JSON",
        }
    )
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_workers={"MultimodalModelWorker": worker_class})
    profile = next(profile for profile in ROSTER if profile.name == "Gemma")

    with pytest.raises(ModelRuntimeUnavailable, match="Modal inference returned an error"):
        runtime.decide(profile, summary())


def test_modal_runtime_disabled_model_raises():
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_function=FakeModalFunction({}))
    profile = next(profile for profile in ROSTER if profile.name == "Qwen")

    with pytest.raises(ModelRuntimeUnavailable, match="disabled"):
        runtime.decide(profile, summary())


def test_modal_runtime_all_enabled_models_spawn_remote_calls():
    response = {
        "action": "call",
        "bet_amount": 0,
        "explanation": "priced in",
        "commentary": "The candlelight keeps me curious.",
        "raw_model_output": '{"action":"call","amount":0}',
        "error": None,
    }
    workers = {
        "GgufModelWorker": FakeModalWorkerClass(response),
        "MultimodalModelWorker": FakeModalWorkerClass(response),
        "CausalModelWorker": FakeModalWorkerClass(response),
        "HeavyCausalModelWorker": FakeModalWorkerClass(response),
    }
    runtime = ModalRuntime(enabled_model_names={profile.name for profile in ROSTER}, remote_workers=workers)

    for profile in ROSTER:
        result = runtime.decide(profile, summary())
        assert result.source == "modal_model"

    called_model_ids = [
        instance.model_id
        for worker_class in workers.values()
        for instance in worker_class.instances
    ]
    assert sorted(called_model_ids) == sorted(profile.model_id for profile in ROSTER)


def test_modal_runtime_default_timeout_matches_modal_worker_timeout():
    worker_class = FakeModalWorkerClass(
        {
            "action": "call",
            "bet_amount": 0,
            "explanation": "priced in",
            "commentary": "The candlelight keeps me curious.",
            "raw_model_output": '{"action":"call","amount":0}',
            "error": None,
        }
    )
    runtime = ModalRuntime(enabled_model_names={"Gemma"}, remote_workers={"MultimodalModelWorker": worker_class})
    profile = next(profile for profile in ROSTER if profile.name == "Gemma")

    runtime.decide(profile, summary())

    assert worker_class.instances[0].last_call.timeout == DEFAULT_MODAL_TIMEOUT_SECONDS
