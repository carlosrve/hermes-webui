"""Project/session authority regressions for new-session bindings.

The project row is authoritative for ownership and bound reasoning.  A bound
reasoning effort is session state, never a write to the profile default.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from tests._pytest_port import BASE


def _get(path: str) -> tuple[dict, int]:
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as response:
            return json.loads(response.read()), response.status
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read()), exc.code


def _post(path: str, body: dict) -> tuple[dict, int]:
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read()), response.status
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read()), exc.code


def _session_ids() -> set[str]:
    payload, status = _get("/api/sessions?all_profiles=1")
    assert status == 200
    return {row["session_id"] for row in payload.get("sessions", [])}


def _create_project(name: str, *, profile: str = "default") -> str:
    payload, status = _post("/api/projects/create", {"name": name, "profile": profile})
    assert status == 200, payload
    return payload["project"]["project_id"]


def test_session_new_rejects_unknown_project_before_creating_session():
    before = _session_ids()

    payload, status = _post(
        "/api/session/new",
        {"project_id": "missing-project", "profile": "default", "worktree": False},
    )

    assert status == 404
    assert payload == {"error": "Project not found"}
    assert _session_ids() == before


def test_session_new_hides_cross_profile_project_before_creating_session():
    foreign_project = _create_project("foreign-authority", profile="foreign")
    before = _session_ids()

    payload, status = _post(
        "/api/session/new",
        {"project_id": foreign_project, "profile": "default", "worktree": False},
    )

    assert status == 404
    assert payload == {"error": "Project not found"}
    assert _session_ids() == before


def test_project_reasoning_is_session_local_durable_and_leaves_profile_default_unchanged():
    config_path = Path(os.environ["HERMES_CONFIG_PATH"])
    _, status = _post("/api/reasoning", {"effort": "medium"})
    assert status == 200
    baseline = config_path.read_bytes()

    high_project = _create_project("reasoning-high")
    low_project = _create_project("reasoning-low")
    for project_id, effort in ((high_project, "high"), (low_project, "low")):
        payload, bind_status = _post(
            "/api/projects/bind",
            {"project_id": project_id, "reasoning_effort": effort},
        )
        assert bind_status == 200, payload

    high_payload, high_status = _post(
        "/api/session/new",
        {"project_id": high_project, "profile": "default", "worktree": False},
    )
    low_payload, low_status = _post(
        "/api/session/new",
        {"project_id": low_project, "profile": "default", "worktree": False},
    )
    assert high_status == low_status == 200
    high = high_payload["session"]
    low = low_payload["session"]
    assert high["reasoning_effort"] == "high"
    assert low["reasoning_effort"] == "low"
    assert high["reasoning_effort"] != low["reasoning_effort"]

    # Force the otherwise-empty sessions to their normal durable sidecars, then
    # read them through the public API to prove restart/resume metadata survives.
    for expected, session in (("high", high), ("low", low)):
        updated, update_status = _post(
            "/api/session/update", {"session_id": session["session_id"]}
        )
        assert update_status == 200, updated
        loaded, load_status = _get(
            "/api/session?messages=0&session_id=" + session["session_id"]
        )
        assert load_status == 200, loaded
        assert loaded["session"]["reasoning_effort"] == expected

    assert config_path.read_bytes() == baseline
    status_payload, reasoning_status = _get("/api/reasoning")
    assert reasoning_status == 200
    assert status_payload["reasoning_effort"] == "medium"


def test_session_reasoning_resolution_isolated_from_profile_default():
    from api.config import resolve_session_reasoning_effort
    from api.gateway_chat import _gateway_reasoning_effort_for_request

    config = {"agent": {"reasoning_effort": "medium"}}
    assert resolve_session_reasoning_effort(config, "high", model_id="gpt-5") == "high"
    assert resolve_session_reasoning_effort(config, "low", model_id="gpt-5") == "low"
    assert resolve_session_reasoning_effort(config, None, model_id="gpt-5") == "medium"
    assert (
        _gateway_reasoning_effort_for_request(
            config, session_effort="high", model="gpt-5", model_provider="openai"
        )
        == "high"
    )
    assert (
        _gateway_reasoning_effort_for_request(
            config, session_effort="low", model="gpt-5", model_provider="openai"
        )
        == "low"
    )
    assert config == {"agent": {"reasoning_effort": "medium"}}


def test_session_new_rejects_invalid_local_effort_without_partial_session():
    before = _session_ids()

    payload, status = _post(
        "/api/session/new",
        {"profile": "default", "worktree": False, "reasoning_effort": "invalid"},
    )

    assert status == 400
    assert "reasoning_effort" in payload["error"]
    assert _session_ids() == before


def test_new_session_frontend_never_mutates_profile_reasoning_default():
    source = (Path(__file__).resolve().parents[1] / "static" / "sessions.js").read_text(
        encoding="utf-8"
    )
    start = source.index("async function newSession(")
    end = source.index("\nasync function", start + 1)
    block = source[start:end]

    assert "reqBody.reasoning_effort" in block
    assert "api('/api/reasoning'" not in block
