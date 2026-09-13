"""Canonical tip identity must survive SQLite lineage -> GET -> sidebar."""
import json
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest

from api import models, profiles, routes
from tests.test_project_assigned_cli_session_limit import _session, _write_state_db
from tests.test_session_attention_badges import _FakeHandler


@pytest.mark.parametrize("root_cwd,tip_cwd,root_profile,tip_profile,expected_project", [
    (None, "/work/one", "default", "default", "one"),
    ("/work/two", "/work/one", "default", "default", "one"),
    ("/work/one", None, "default", "default", None),
    ("/work/one", "/work/one", "default", "other", None),
    ("/work/two", "/work/one", "other", "default", "one"),
    ("/work/two", "/work/one", "other", None, "one"),
])
@pytest.mark.parametrize("end_reason", ["compression", "cli_close"])
def test_served_lineage_uses_tip_workspace_and_profile(
    tmp_path, monkeypatch, root_cwd, tip_cwd, root_profile, tip_profile,
    expected_project, end_reason,
):
    db = tmp_path / "state.db"
    _write_state_db(db, [
        _session("root", 100, ended_at=110, end_reason=end_reason),
        _session("tip", 120, parent="root"),
    ])
    with sqlite3.connect(db) as conn:
        # Match the agent schema so the existing index-healing path is idle.
        conn.execute("CREATE INDEX idx_messages_session ON messages(session_id, timestamp)")
        conn.execute("ALTER TABLE sessions ADD COLUMN cwd TEXT")
        conn.execute("ALTER TABLE sessions ADD COLUMN profile_name TEXT")
        conn.executemany("UPDATE sessions SET cwd=?, profile_name=? WHERE id=?", [
            (root_cwd, root_profile, "root"), (tip_cwd, tip_profile, "tip"),
        ])
    sidecars = tmp_path / "sessions"
    sidecars.mkdir()
    monkeypatch.setattr(models, "SESSION_DIR", sidecars)
    monkeypatch.setattr(routes, "all_sessions", lambda **kw: [])
    monkeypatch.setattr(routes, "get_cli_sessions", lambda **kw:
        models._load_cli_sessions_uncached(tmp_path, db, "default", include_claude_code=False))
    monkeypatch.setattr(routes, "load_projects", lambda: [
        {"project_id": name, "profile": "default", "auto_assign": True,
         "workspaces": ["/work/" + name]} for name in ("one", "two")
    ])
    monkeypatch.setattr(routes, "load_settings", lambda: {"show_cli_sessions": True})
    monkeypatch.setattr(profiles, "get_active_profile_name", lambda: "default")
    before = db.read_bytes()
    routes._session_list_cache_clear()
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/sessions?all_profiles=1"))
    assert handler.status == 200
    rows = handler.json_body()["sessions"]
    assert [r["session_id"] for r in rows] == ["tip"]
    row = rows[0]
    assert row["workspace"] == tip_cwd
    assert row["profile"] == (tip_profile or "default")
    assert row["project_id"] == expected_project
    # The normal active-profile GET must not leak a foreign tip through the
    # root's default profile, even though all-profiles discovery can show it.
    routes._session_list_cache_clear()
    active_handler = _FakeHandler()
    routes.handle_get(active_handler, urlparse("/api/sessions"))
    assert active_handler.status == 200
    assert [r["session_id"] for r in active_handler.json_body()["sessions"]] == (
        [] if tip_profile == "other" else ["tip"]
    )
    assert db.read_bytes() == before
    assert list(sidecars.iterdir()) == []
    source = (Path(__file__).parents[1] / "static/sessions.js").read_text()
    start = source.index("function _partitionSidebarSessionRows(")
    end = source.index("\n}\n", start) + 2
    script = """
const window={_showCliSessions:true};
const NO_PROJECT_FILTER='__none__';
let _activeProject='one', _showArchived=false, _sessionSourceFilter='cli';
const _archivedCliCount=0, _archivedWebuiCount=0;
const _sidebarRowHasVisibleMessages=s=>s.message_count>0;
const _isCliSession=s=>s.is_cli_session;
""" + source[start:end] + "\nconst rows=" + json.dumps(rows) + """;
const groups={};
for (const project of ['one','two',NO_PROJECT_FILTER]) {
  _activeProject=project;
  groups[project]=_partitionSidebarSessionRows(rows,null).sessionsRaw.map(s=>s.session_id);
}
console.log(JSON.stringify(groups));
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {
        "one": ["tip"] if expected_project == "one" else [],
        "two": [],
        "__none__": [] if expected_project else ["tip"],
    }
