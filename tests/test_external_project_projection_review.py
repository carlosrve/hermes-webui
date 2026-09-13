"""Independent review: ambiguous native provenance and invalid profile scope."""
import sqlite3

import pytest

from api import models, profiles, routes
from tests.test_session_attention_badges import _FakeHandler
from urllib.parse import urlparse


@pytest.mark.parametrize("canonical_source", ["webui", None])
def test_native_sidecar_without_source_keeps_workspace_when_canonical_cwd_missing(tmp_path, monkeypatch, canonical_source):
    with sqlite3.connect(tmp_path / "state.db") as conn:
        conn.execute("CREATE TABLE sessions(id TEXT, cwd TEXT, source TEXT)")
        conn.execute("INSERT INTO sessions VALUES ('native', NULL, ?)", (canonical_source,))
    monkeypatch.setattr(models, "_get_profile_home", lambda profile: tmp_path)
    original = {"session_id": "native", "workspace": "/work/native", "profile": "default",
                "message_count": 1, "source_tag": None, "updated_at": 1}
    monkeypatch.setattr(routes, "all_sessions", lambda **kwargs: [dict(original)])
    monkeypatch.setattr(routes, "load_projects", lambda: [
        {"project_id": "native-project", "profile": "default", "auto_assign": True,
         "workspaces": ["/work/native"]}])
    monkeypatch.setattr(routes, "load_settings", lambda: {"show_cli_sessions": False})
    monkeypatch.setattr(profiles, "get_active_profile_name", lambda: "default")
    before = (tmp_path / "state.db").read_bytes()
    routes._session_list_cache_clear()
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/sessions"))
    assert handler.status == 200
    payload = handler.json_body()
    row = next(row for row in payload["sessions"] if row["session_id"] == "native")
    assert row["workspace"] == "/work/native"
    assert row["project_id"] == "native-project"
    assert (tmp_path / "state.db").read_bytes() == before
    assert original["workspace"] == "/work/native"


@pytest.mark.parametrize("profile", ["../other", "bad/profile"])
def test_invalid_named_profile_must_not_probe_default_database(tmp_path, monkeypatch, profile):
    with sqlite3.connect(tmp_path / "state.db") as conn:
        conn.execute("CREATE TABLE sessions(id TEXT, cwd TEXT, profile_name TEXT)")
        conn.execute("INSERT INTO sessions VALUES ('same-id', '/private/default', 'default')")
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", tmp_path)
    assert models.agent_session_workspace_metadata(["same-id"], profile=profile) == {}


def test_isolated_profile_probe_does_not_read_pinned_home_for_foreign_name(tmp_path, monkeypatch):
    with sqlite3.connect(tmp_path / "state.db") as conn:
        conn.execute("CREATE TABLE sessions(id TEXT, cwd TEXT)")
        conn.execute("INSERT INTO sessions VALUES ('same-id', '/private/pinned')")
    monkeypatch.setattr(profiles, "_is_isolated_profile_mode", lambda: True)
    monkeypatch.setattr(profiles, "_isolated_profile_name", lambda: "pinned")
    monkeypatch.setattr(profiles, "_INITIAL_HERMES_HOME", str(tmp_path))
    assert models.agent_session_workspace_metadata(["same-id"], profile="foreign") == {}
    assert models.agent_session_workspace_metadata(["same-id"], profile="pinned") == {
        "same-id": {"workspace": "/private/pinned", "profile": "pinned"}
    }
