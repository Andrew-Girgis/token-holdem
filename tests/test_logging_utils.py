import json

from token_holdem.logging_utils import get_logger, log_event


def test_json_logger_writes_structured_event(tmp_path, monkeypatch):
    import token_holdem.logging_utils as logging_utils

    log_file = tmp_path / "token_holdem.jsonl"
    monkeypatch.setattr(logging_utils, "LOG_DIR", tmp_path)
    monkeypatch.setattr(logging_utils, "LOG_FILE", log_file)

    logger = get_logger("token_holdem.test_logger")
    log_event(logger, "test_event", answer=42)

    payload = json.loads(log_file.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["message"] == "test_event"
    assert payload["answer"] == 42
