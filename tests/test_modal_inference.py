import sys
from types import SimpleNamespace

import modal_inference
import pytest


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


@pytest.fixture(autouse=True)
def clear_loader_caches():
    clear_caches()
    yield
    clear_caches()


def clear_caches():
    for loader in (modal_inference._load_model, modal_inference._load_multimodal_model, modal_inference._load_gguf_model):
        if hasattr(loader, "cache_clear"):
            loader.cache_clear()


def test_gemma_4_uses_multimodal_processor_loader(monkeypatch):
    calls = []

    def fail_generic_loader(model_id):
        raise AssertionError(f"generic causal-LM loader used for {model_id}")

    def fake_multimodal_loader(model_id):
        calls.append(("load_multimodal", model_id))
        return object(), object()

    def fake_multimodal_generate(model, processor, prompt, max_new_tokens, temperature, **kwargs):
        calls.append(("generate_multimodal", max_new_tokens, temperature, kwargs))
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
    assert result["commentary"]
    assert calls == [
        ("load_multimodal", "google/gemma-4-12B-it"),
        ("generate_multimodal", 192, 0.0, {"json_prefix": True, "deterministic": True}),
    ]


def test_invalid_decision_output_gets_strict_repair_attempt(monkeypatch):
    calls = []

    def fake_multimodal_loader(model_id):
        return object(), object()

    def fake_multimodal_generate(model, processor, prompt, max_new_tokens, temperature, **kwargs):
        calls.append((max_new_tokens, temperature, prompt))
        if len(calls) == 1:
            return "Thinking Process:\nI should probably call after considering the pot."
        if len(calls) == 2:
            return '{"action":"call","amount":0,"reasoning_hint":"repair obeyed schema"}'
        return "The candlelight keeps me curious."

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
    assert result["explanation"] == "repair obeyed schema"
    assert "repair=" in result["raw_model_output"]
    assert calls[1][0:2] == (96, 0.0)
    assert "previous answer was invalid" in calls[1][2]


def test_invalid_decision_after_repair_returns_legal_fallback(monkeypatch):
    calls = []

    def fake_multimodal_loader(model_id):
        return object(), object()

    def fake_multimodal_generate(model, processor, prompt, max_new_tokens, temperature, **kwargs):
        calls.append((max_new_tokens, temperature, prompt))
        return "Thinking Process:\nNo JSON today."

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
    assert result["action"] in LEGAL["actions"]
    assert result["commentary"]
    assert "used persona fallback action" in result["explanation"]
    assert len(calls) == 2


def test_transformers_loader_commits_modal_cache(monkeypatch):
    calls = []

    class FakeTokenizer:
        pad_token_id = None
        eos_token = "<eos>"

    class FakeModel:
        def eval(self):
            calls.append("eval")

    class FakeAutoTokenizer:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            calls.append(("tokenizer", kwargs["cache_dir"]))
            return FakeTokenizer()

    class FakeAutoModelForCausalLM:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            calls.append(("model", kwargs["cache_dir"]))
            return FakeModel()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoModelForCausalLM=FakeAutoModelForCausalLM, AutoTokenizer=FakeAutoTokenizer),
    )
    monkeypatch.setattr(modal_inference.hf_cache, "commit", lambda: calls.append("commit"))

    model, tokenizer = modal_inference._load_model("text/model")

    assert isinstance(model, FakeModel)
    assert isinstance(tokenizer, FakeTokenizer)
    assert calls == [
        ("tokenizer", modal_inference.MODEL_CACHE_DIR),
        ("model", modal_inference.MODEL_CACHE_DIR),
        "eval",
        "commit",
    ]


def test_multimodal_loader_commits_modal_cache(monkeypatch):
    calls = []

    class FakeProcessor:
        pass

    class FakeModel:
        def eval(self):
            calls.append("eval")

    class FakeAutoProcessor:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            calls.append(("processor", kwargs["cache_dir"]))
            return FakeProcessor()

    class FakeAutoModelForMultimodalLM:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            calls.append(("model", kwargs["cache_dir"]))
            return FakeModel()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoModelForMultimodalLM=FakeAutoModelForMultimodalLM, AutoProcessor=FakeAutoProcessor),
    )
    monkeypatch.setattr(modal_inference.hf_cache, "commit", lambda: calls.append("commit"))

    model, processor = modal_inference._load_multimodal_model("google/gemma-4-12B-it")

    assert isinstance(model, FakeModel)
    assert isinstance(processor, FakeProcessor)
    assert calls == [
        ("processor", modal_inference.MODEL_CACHE_DIR),
        ("model", modal_inference.MODEL_CACHE_DIR),
        "eval",
        "commit",
    ]


def test_gguf_loader_commits_modal_cache_after_download(monkeypatch):
    calls = []

    def fake_hf_hub_download(**kwargs):
        calls.append(("download", kwargs["repo_id"], kwargs["filename"], kwargs["cache_dir"]))
        return "/cache/huggingface/model.gguf"

    class FakeLlama:
        def __init__(self, **kwargs):
            calls.append(("llama", kwargs["model_path"]))

    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(hf_hub_download=fake_hf_hub_download))
    monkeypatch.setitem(sys.modules, "llama_cpp", SimpleNamespace(Llama=FakeLlama))
    monkeypatch.setattr(modal_inference.hf_cache, "commit", lambda: calls.append("commit"))

    model = modal_inference._load_gguf_model("nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF")

    assert isinstance(model, FakeLlama)
    assert calls == [
        (
            "download",
            "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF",
            "NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf",
            modal_inference.MODEL_CACHE_DIR,
        ),
        "commit",
        ("llama", "/cache/huggingface/model.gguf"),
    ]


def test_modal_sets_huggingface_cache_environment():
    for name in ("HF_HOME", "TRANSFORMERS_CACHE", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
        assert modal_inference.HF_CACHE_ENV[name] == modal_inference.MODEL_CACHE_DIR


def test_collect_spawned_calls_handles_result_model_name(monkeypatch):
    logs = []

    class FakeCall:
        def get(self, timeout=None):
            return {"model_name": "Tiny Seat", "loaded": True}

    monkeypatch.setattr(modal_inference, "_modal_log", lambda message, **fields: logs.append((message, fields)))

    results = modal_inference._collect_spawned_calls([("Tiny Seat", 0.0, FakeCall())])

    assert results[0]["model_name"] == "Tiny Seat"
    assert logs[0][0] == "modal_parallel_call_complete"
    assert logs[0][1]["model_name"] == "Tiny Seat"


def test_snapshot_predownload_commits_modal_cache(monkeypatch):
    calls = []

    def fake_snapshot_download(**kwargs):
        calls.append(("snapshot", kwargs["repo_id"], kwargs["cache_dir"], kwargs["allow_patterns"]))
        return "/cache/huggingface/snapshot"

    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(snapshot_download=fake_snapshot_download))
    monkeypatch.setattr(modal_inference.hf_cache, "commit", lambda: calls.append("commit"))

    result = modal_inference._download_model_snapshot("nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF")

    assert result["model_id"] == "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF"
    assert calls == [
        (
            "snapshot",
            "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF",
            modal_inference.MODEL_CACHE_DIR,
            ["NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf"],
        ),
        "commit",
    ]


def test_demo_mode_uses_longer_default_scaledown_window():
    if modal_inference.DEMO_MODE:
        assert modal_inference.DEFAULT_SCALEDOWN_WINDOW_SECONDS == 1800


def test_gguf_generation_uses_short_demo_token_budgets():
    assert modal_inference.GGUF_DECISION_MAX_TOKENS == 96
    assert modal_inference.GGUF_TALK_MAX_TOKENS == 24
