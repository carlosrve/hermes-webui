"""Exercise state.db -> sidebar API projection without importing conversations."""

import sqlite3
import pytest
import json
from urllib.parse import urlparse

from api import models, routes, profiles
from tests.test_session_attention_badges import _FakeHandler


@pytest.mark.parametrize("source_tag", ["cli", "desktop", "tui"])
def test_nonindexed_external_session_uses_own_workspace_and_project(
    tmp_path, monkeypatch, source_tag
):
    db = tmp_path / "state.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT, model TEXT, message_count INTEGER, started_at REAL, source TEXT, cwd TEXT, profile_name TEXT)"
        )
        conn.executemany(
            "INSERT INTO sessions VALUES (?, ?, ?, 2, 1, ?, ?, ?)",
            [
                (
                    "owned",
                    "Working session",
                    "model",
                    source_tag,
                    "/work/one",
                    "default",
                ),
                ("unknown", "Unknown workspace", "model", source_tag, None, "default"),
                ("foreign", "Other profile", "model", source_tag, "/work/one", "other"),
            ],
        )
        conn.execute(
            "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp REAL)"
        )
        conn.execute(
            "CREATE INDEX idx_messages_session ON messages(session_id, timestamp)"
        )
        for sid in ("owned", "unknown", "foreign"):
            conn.execute(
                "INSERT INTO messages(session_id,role,content,timestamp) VALUES (?, ?, ?, ?)",
                (sid, "user", "Preserve this real stored message", 1),
            )
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    monkeypatch.setattr(models, "SESSION_DIR", session_dir)
    monkeypatch.setattr(models, "get_last_workspace", lambda: "/work/wrong")
    projects = [
        {
            "project_id": "one",
            "profile": "default",
            "workspaces": ["/work/one"],
            "auto_assign": True,
        }
    ]
    monkeypatch.setattr(routes, "load_projects", lambda: projects)

    def external(**kwargs):
        return models._load_cli_sessions_uncached(
            tmp_path, db, "default", source_filter=source_tag, include_claude_code=False
        )

    monkeypatch.setattr(routes, "get_cli_sessions", external)
    monkeypatch.setattr(routes, "all_sessions", lambda **kwargs: [])
    before = db.read_bytes()
    monkeypatch.setattr(routes, "load_settings", lambda: {"show_cli_sessions": True})
    monkeypatch.setattr(profiles, "get_active_profile_name", lambda: "default")
    routes._session_list_cache_clear()
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/sessions?all_profiles=1"))
    assert handler.status == 200
    payload = handler.json_body()
    rows = {row["session_id"]: row for row in payload["sessions"]}
    assert rows["owned"]["workspace"] == "/work/one"
    assert rows["owned"]["project_id"] == "one"
    assert rows["unknown"]["workspace"] is None
    assert rows["unknown"]["project_id"] is None
    assert rows["foreign"]["profile"] == "other"
    assert rows["foreign"]["project_id"] is None
    assert db.read_bytes() == before
    assert list(session_dir.iterdir()) == []
    # Execute the actual sidebar partition function with the served JSON.
    import subprocess
    from pathlib import Path

    source = (Path(__file__).parents[1] / "static/sessions.js").read_text()
    start = source.index("function _partitionSidebarSessionRows(")
    end = source.index("\n}\n", start) + 2
    script = (
        """
const window={_showCliSessions:true};
const NO_PROJECT_FILTER='__none__';
let _activeProject='one', _showArchived=false, _sessionSourceFilter='cli';
const _archivedCliCount=0, _archivedWebuiCount=0;
const _sidebarRowHasVisibleMessages=s=>s.message_count>0;
const _isCliSession=s=>s.is_cli_session;
"""
        + source[start:end]
        + "\nconst rows="
        + json.dumps(list(rows.values()))
        + """;
const assigned=_partitionSidebarSessionRows(rows,null).sessionsRaw.map(s=>s.session_id);
_activeProject=NO_PROJECT_FILTER;
const unassigned=_partitionSidebarSessionRows(rows,null).sessionsRaw.map(s=>s.session_id);
console.log(JSON.stringify({assigned,unassigned}));
"""
    )
    if source_tag == "desktop":
        script = script.replace(
            "_sessionSourceFilter='cli'", "_sessionSourceFilter='webui'"
        )
    result = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == {
        "assigned": ["owned"],
        "unassigned": ["unknown", "foreign"],
    }


@pytest.mark.parametrize("source", ["desktop", "webui"])
@pytest.mark.parametrize("show_external", [True, False])
@pytest.mark.parametrize("existing_project", [None, "manual"])
def test_indexed_session_uses_canonical_cwd_beyond_external_window(
    tmp_path,
    monkeypatch,
    source,
    show_external,
    existing_project,
):
    db = tmp_path / "state.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, profile_name TEXT)"
        )
        conn.execute("INSERT INTO sessions VALUES ('old', '/work/one', 'default')")
    monkeypatch.setattr(models, "_get_profile_home", lambda profile: tmp_path)
    original = {
        "session_id": "old",
        "title": "Previously imported",
        "workspace": "/work/wrong",
        "profile": "default",
        "message_count": 2,
        "source_tag": source,
        "updated_at": 1,
        "project_id": existing_project,
    }
    monkeypatch.setattr(routes, "all_sessions", lambda **kwargs: [dict(original)])
    monkeypatch.setattr(routes, "get_cli_sessions", lambda **kwargs: [])
    monkeypatch.setattr(
        routes,
        "load_projects",
        lambda: [
            {
                "project_id": "one",
                "profile": "default",
                "auto_assign": True,
                "workspaces": ["/work/one"],
            }
        ],
    )
    before = db.read_bytes()
    payload = routes._build_session_list_cache_payload(
        active_profile="default",
        all_profiles=False,
        show_cli_sessions=show_external,
        show_previous_messaging_sessions=True,
        show_cron_sessions=False,
    )
    row = next(row for row in payload["sessions"] if row["session_id"] == "old")
    assert row["workspace"] == "/work/one"
    assert row["project_id"] == (existing_project or "one")
    assert db.read_bytes() == before
    assert original["workspace"] == "/work/wrong"


def test_claude_projection_does_not_invent_workspace(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "session.jsonl").write_text(
        json.dumps(
            {
                "type": "user",
                "message": {"role": "user", "content": "hello"},
            }
        )
        + "\n"
    )
    monkeypatch.setattr(models, "get_last_workspace", lambda: "/work/wrong")
    rows = models.get_claude_code_sessions(tmp_path)
    assert len(rows) == 1
    assert rows[0]["workspace"] is None


@pytest.mark.parametrize("schema", ["missing", "legacy", "modern"])
def test_workspace_probe_is_profile_scoped_readonly_and_optional(
    tmp_path, monkeypatch, schema
):
    root = tmp_path / "default"
    root.mkdir()
    named = tmp_path / "other"
    named.mkdir()
    with sqlite3.connect(root / "state.db") as conn:
        conn.execute("CREATE TABLE sessions(id TEXT, cwd TEXT)")
        conn.execute("INSERT INTO sessions VALUES ('same-id', '/wrong-profile')")
    if schema != "missing":
        with sqlite3.connect(named / "state.db") as conn:
            conn.execute(
                "CREATE TABLE sessions(id TEXT"
                + (", cwd TEXT" if schema == "modern" else "")
                + ")"
            )
            if schema == "modern":
                conn.execute(
                    "INSERT INTO sessions VALUES ('same-id', '/right-profile')"
                )
    monkeypatch.setattr(
        models,
        "_get_profile_home",
        lambda profile: named if profile == "other" else root,
    )
    result = models.agent_session_workspace_metadata(["same-id"], profile="other")
    assert result == (
        {"same-id": {"workspace": "/right-profile", "profile": "other"}}
        if schema == "modern"
        else {}
    )
    if schema == "missing":
        assert not (named / "state.db").exists()


def test_auto_assignment_requires_exact_enabled_binding(monkeypatch):
    projects = [
        {
            "project_id": "disabled",
            "auto_assign": False,
            "workspaces": ["/work/one"],
            "profile": "default",
        },
        {
            "project_id": "other",
            "auto_assign": True,
            "workspaces": ["/work/one"],
            "profile": "other",
        },
        {
            "project_id": "chosen",
            "auto_assign": True,
            "workspaces": ["/work/one"],
            "profile": "default",
        },
    ]
    assert (
        routes._auto_assign_project_for_workspace(
            "/work/one", "default", projects=projects
        )
        == "chosen"
    )
    assert (
        routes._auto_assign_project_for_workspace(
            "/work/one/subdir", "default", projects=projects
        )
        is None
    )
    assert (
        routes._auto_assign_project_for_workspace(
            "/elsewhere/one", "default", projects=projects
        )
        is None
    )
    assert (
        routes._auto_assign_project_for_workspace(None, "default", projects=projects)
        is None
    )
