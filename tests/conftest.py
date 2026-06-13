import json
import pytest

from burndown.config import Config


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    # never touch the real ~/.config during tests
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    yield


@pytest.fixture
def log_dir(tmp_path):
    """A fake Claude log tree exercising dedup / synthetic / no-usage / garbage."""
    d = tmp_path / "projects" / "proj-a"
    d.mkdir(parents=True)
    ts = "2026-06-10T12:00:00Z"
    lines = [
        {"type": "assistant", "uuid": "A", "timestamp": ts, "sessionId": "s1",
         "cwd": "/x/proj-a", "gitBranch": "main", "entrypoint": "claude-desktop",
         "message": {"model": "claude-opus-4-8", "content": "SECRET PROMPT — must never be read",
                     "usage": {"input_tokens": 1000, "output_tokens": 2000,
                               "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}},
        # duplicate uuid A -> must be de-duped
        {"type": "assistant", "uuid": "A", "timestamp": ts, "sessionId": "s1", "cwd": "/x/proj-a",
         "entrypoint": "claude-desktop",
         "message": {"model": "claude-opus-4-8",
                     "usage": {"input_tokens": 1000, "output_tokens": 2000,
                               "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}},
        {"type": "assistant", "uuid": "B", "timestamp": ts, "sessionId": "s1", "cwd": "/x/proj-a",
         "entrypoint": "sdk-cli",
         "message": {"model": "claude-sonnet-4-6",
                     "usage": {"input_tokens": 500, "output_tokens": 100,
                               "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}},
        # synthetic model -> skipped (no real cost)
        {"type": "assistant", "uuid": "C", "timestamp": ts,
         "message": {"model": "<synthetic>", "usage": {"input_tokens": 1, "output_tokens": 1,
                     "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}},
        # user line, no usage -> skipped
        {"type": "user", "uuid": "D", "timestamp": ts, "message": {"content": "hi"}},
        # assistant, no usage block -> skipped
        {"type": "assistant", "uuid": "E", "timestamp": ts, "message": {"model": "claude-opus-4-8"}},
    ]
    (d / "session.jsonl").write_text(
        "\n".join(json.dumps(o) for o in lines) + "\ngarbage not json\n")
    return str(tmp_path / "projects")


@pytest.fixture
def cfg(log_dir):
    return Config(log_dirs=[log_dir],
                  pricing={"opus": [15, 75, 18.75, 1.5], "sonnet": [3, 15, 3.75, 0.3]})
