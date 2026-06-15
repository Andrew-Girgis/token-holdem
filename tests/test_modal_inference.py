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

    model = modal_inference._load_gguf_model("lm-kit/qwen-3-0.6b-instruct-gguf")

    assert isinstance(model, FakeLlama)
    assert calls == [
        ("download", "lm-kit/qwen-3-0.6b-instruct-gguf", "Qwen3-0.6B-Q4_K_M.gguf", modal_inference.MODEL_CACHE_DIR),
        "commit",
        ("llama", "/cache/huggingface/model.gguf"),
    ]
