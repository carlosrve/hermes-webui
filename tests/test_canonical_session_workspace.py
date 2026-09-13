"""Metadata-only incident replay; never reads production state or calls a model."""
import json
from collections import OrderedDict
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest
from api import models, routes, profiles, streaming
from tests.test_session_attention_badges import _FakeHandler


@pytest.fixture
def incident(tmp_path, monkeypatch):
    rows = json.loads((Path(__file__).parent / 'fixtures/session_workspace_metadata.json').read_text())
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    monkeypatch.setattr(models, 'SESSION_DIR', sessions)
    monkeypatch.setattr(routes, 'SESSION_DIR', sessions)
    monkeypatch.setattr(models, '_get_profile_home', lambda profile: tmp_path)
    monkeypatch.setattr(models, '_active_state_db_path', lambda: tmp_path / 'state.db')
    monkeypatch.setattr(profiles, 'get_active_profile_name', lambda: 'default')
    monkeypatch.setattr(models, 'get_last_workspace', lambda: '/workspace/lfc')
    monkeypatch.setattr(routes, 'get_last_workspace', lambda: '/workspace/lfc')
    monkeypatch.setattr(routes, '_lookup_cli_session_metadata', lambda sid: {})
    monkeypatch.setattr(routes, 'get_cli_session_messages', lambda sid: [])
    monkeypatch.setattr(models, 'SESSIONS', OrderedDict())
    with sqlite3.connect(tmp_path / 'state.db') as conn:
        conn.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, profile_name TEXT, source TEXT)')
        conn.execute('CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp REAL)')
        for row in rows:
            conn.execute('INSERT INTO sessions VALUES (?,?,?,?)', (row['id'], row['cwd'], row['profile_name'], row['source']))
            conn.execute('INSERT INTO messages(session_id,role,content,timestamp) VALUES (?,\'user\',\'Fixture message, not a transcript\',1)', (row['id'],))
            payload = dict(row['sidecar'], session_id=row['id'], title='Incident fixture', messages=[], created_at=1, updated_at=1)
            (sessions / (row['id'] + '.json')).write_text(json.dumps(payload))
    return rows, tmp_path


def workspace_chip(session):
    source = (Path(__file__).parents[1] / 'static/panels.js').read_text()
    start = source.index('function syncWorkspaceDisplays(){')
    end = source.index('\n}\n', start) + 2
    script = "const S={session:" + json.dumps(session) + ",_bootReady:true,_profileDefaultWorkspace:'/workspace/lfc'};"
    script += "const els={}; const $=id=>els[id]||(els[id]={textContent:'',classList:{contains:()=>false,toggle:()=>{}},setAttribute:()=>{}}); const t=k=>k; const getWorkspaceFriendlyName=p=>p; const _setWorkspaceDropdownOpenState=()=>{};"
    script += source[start:end] + ";syncWorkspaceDisplays();console.log(JSON.stringify({path:els.sidebarWsPath.textContent,label:els.composerWorkspaceLabel.textContent,disabled:els.composerWorkspaceChip.disabled}));"
    return json.loads(subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True).stdout)


@pytest.mark.parametrize('row_index', range(7))
def test_real_sidecar_open_chip_execution_and_files_agree(incident, monkeypatch, row_index):
    rows, home = incident
    row = rows[row_index]
    before = (home / 'state.db').read_bytes()
    sidecar = home / 'sessions' / (row['id'] + '.json')
    original = sidecar.read_bytes()
    handler = _FakeHandler()
    routes._handle_session_get(handler, urlparse('/api/session?messages=0&session_id=' + row['id']))
    assert handler.status == 200
    session = handler.json_body()['session']
    assert session['workspace'] == row['cwd']
    assert workspace_chip(session)['path'] == row['cwd']
    # Trust checking is a separate boundary: incident paths are remapped only
    # there so execution never touches the user's actual workspace directories.
    monkeypatch.setattr(routes, 'resolve_trusted_workspace', lambda p: p)
    monkeypatch.setattr(routes, 'resolve_implicit_workspace_with_recovery', lambda p, fallback: (p, False))
    loaded = models.get_session(row['id'], metadata_only=True)
    cwd = routes._resolve_chat_workspace_with_recovery(loaded, session['workspace'])
    assert cwd == row['cwd']
    monkeypatch.setattr('api.workspace.resolve_implicit_workspace_with_recovery', lambda p, fallback: (p, False))
    assert models.get_session_for_file_ops(row['id']).workspace == row['cwd']
    assert (home / 'state.db').read_bytes() == before
    assert sidecar.read_bytes() == original
    runtime_cwd = pytest.importorskip('agent.runtime_cwd', reason='installed Agent required for execution-cwd proof')
    tokens = streaming._set_turn_session_identity(row['id'], workspace=cwd)
    try:
        assert str(runtime_cwd.resolve_agent_cwd()) == row['cwd']
    finally:
        streaming._reset_turn_session_identity(tokens)


@pytest.mark.parametrize('known', [True, False])
def test_import_and_file_only_never_attribute_last_workspace(incident, monkeypatch, known):
    rows, home = incident
    row = rows[1]
    sid = row['id']
    (home / 'sessions' / (sid + '.json')).unlink()
    if not known:
        with sqlite3.connect(home / 'state.db') as conn:
            conn.execute('UPDATE sessions SET cwd=NULL WHERE id=?', (sid,))
    monkeypatch.setattr(models, 'state_db_has_session', lambda sid: True)
    if known:
        assert models.get_session_for_file_ops(sid).workspace == row['cwd']
    else:
        with pytest.raises(KeyError):
            models.get_session_for_file_ops(sid)
    imported = models.import_cli_session(sid, 'Fixture', [], profile='default')
    assert imported.workspace == (row['cwd'] if known else None)
    assert workspace_chip(imported.compact())['path'] == (row['cwd'] if known else '')
    assert not workspace_chip(imported.compact())['disabled']


@pytest.mark.parametrize('canonical', [None, '', 'missing-row'])
def test_absent_evidence_preserves_native_explicit(incident, canonical):
    rows, home = incident
    sid = rows[1]['id']
    path = home / 'sessions' / (sid + '.json')
    payload = json.loads(path.read_text())
    payload.update(is_cli_session=False, source_tag='webui', session_source='webui')
    path.write_text(json.dumps(payload))
    with sqlite3.connect(home / 'state.db') as conn:
        if canonical == 'missing-row':
            conn.execute('DELETE FROM sessions WHERE id=?', (sid,))
        else:
            conn.execute('UPDATE sessions SET cwd=?, source=\'webui\' WHERE id=?', (canonical, sid))
    assert models.get_session(sid, metadata_only=True).workspace == '/workspace/lfc'


@pytest.mark.parametrize('helper', [routes._resolve_chat_workspace_with_recovery, routes._resolve_chat_workspace_for_regeneration])
@pytest.mark.parametrize('stored', [None, '/workspace/stale'])
def test_canonical_resolves_before_unknown_and_rejects_stale_request(incident, monkeypatch, helper, stored):
    rows, _ = incident
    row = rows[1]
    s = models.Session(session_id=row['id'], workspace=stored, profile='default')
    monkeypatch.setattr(routes, 'resolve_trusted_workspace', lambda p: p)
    assert helper(s, None) == row['cwd']
    with pytest.raises(ValueError, match='reload|Reload'):
        helper(s, '/workspace/stale')


@pytest.mark.parametrize('imported', [False, True])
def test_unmarked_native_canonical_changes_win(incident, imported):
    rows, home = incident
    sid = rows[1]['id']  # Deliberately not a native-looking id/title heuristic.
    with sqlite3.connect(home / 'state.db') as conn:
        conn.execute("UPDATE sessions SET source='webui' WHERE id=?", (sid,))
    s = models.Session(session_id=sid, workspace='/workspace/manual', profile='default',
                       is_cli_session=imported, source_tag='desktop' if imported else None)
    s.save(touch_updated_at=False)
    models.SESSIONS.clear()
    original = (home / 'sessions' / (sid + '.json')).read_bytes()
    assert models.get_session(sid).workspace == rows[1]['cwd']
    with sqlite3.connect(home / 'state.db') as conn:
        conn.execute('UPDATE sessions SET cwd=? WHERE id=?', ('/workspace/new-canonical', sid))
    assert models.get_session(sid).workspace == '/workspace/new-canonical'
    models.SESSIONS.clear()
    assert models.get_session(sid).workspace == '/workspace/new-canonical'
    assert (home / 'sessions' / (sid + '.json')).read_bytes() == original


@pytest.mark.parametrize('active_profile', ['default', 'research'])
@pytest.mark.parametrize('fallback_profile', [None, 'foreign', 'default', 'research'])
def test_synthesis_fallback_requires_verified_profile(incident, monkeypatch, active_profile, fallback_profile):
    monkeypatch.setattr(profiles, 'get_active_profile_name', lambda: active_profile)
    monkeypatch.setattr(models, 'agent_session_workspace_metadata', lambda *a, **kw: {})
    monkeypatch.setattr(routes, '_session_index_marks_was_webui', lambda sid: False)
    monkeypatch.setattr(routes, '_session_deleted_tombstone_marks_was_webui', lambda sid: False)
    monkeypatch.setattr(routes, 'get_cli_session_messages', lambda sid: [{'role': 'user', 'content': 'fixture'}])
    s, _ = routes._claim_or_synthesize_cli_session('fallback-fixture', {
        'profile': fallback_profile, 'workspace': '/workspace/fallback', 'source_tag': 'cli',
    })
    assert s is not None
    assert s.workspace is None
    assert models.resolve_session_workspace_metadata(s).workspace is None
    for helper in (routes._resolve_chat_workspace_with_recovery, routes._resolve_chat_workspace_for_regeneration):
        with pytest.raises(ValueError, match='unknown'):
            helper(s, None)
    monkeypatch.setattr(models, 'get_session', lambda *a, **kw: s)
    with pytest.raises(KeyError):
        models.get_session_for_file_ops(s.session_id)


@pytest.mark.parametrize('helper', [routes._resolve_chat_workspace_with_recovery, routes._resolve_chat_workspace_for_regeneration])
def test_live_owner_then_canonical_transition(incident, monkeypatch, helper):
    rows, _ = incident
    row = rows[1]
    s = models.Session(session_id=row['id'], workspace='/workspace/accepted', active_stream_id='live')
    monkeypatch.setattr(routes, 'resolve_trusted_workspace', lambda p: p)
    assert helper(s, None) == '/workspace/accepted'
    s.active_stream_id = None
    assert helper(s, None) == row['cwd']


def test_known_canonical_resolves_null_sidecar_on_open_and_files(incident):
    rows, home = incident
    sid = rows[1]['id']
    path = home / 'sessions' / (sid + '.json')
    payload = json.loads(path.read_text())
    payload['workspace'] = None
    path.write_text(json.dumps(payload))
    s = models.get_session(sid)
    assert s.workspace == rows[1]['cwd']
    assert workspace_chip(s.compact())['path'] == s.workspace
    assert models.get_session_for_file_ops(sid).workspace == s.workspace


@pytest.mark.parametrize('helper', [routes._resolve_chat_workspace_with_recovery, routes._resolve_chat_workspace_for_regeneration])
@pytest.mark.parametrize('kind', ['unknown', 'missing', 'untrusted'])
def test_invalid_roots_never_use_browser_fallback(incident, monkeypatch, helper, kind):
    from api import workspace
    rows, home = incident
    sid = rows[1]['id']
    root = home / kind
    if kind == 'untrusted':
        root.mkdir()
    canonical = None if kind == 'unknown' else str(root)
    with sqlite3.connect(home / 'state.db') as conn:
        conn.execute('UPDATE sessions SET cwd=? WHERE id=?', (canonical, sid))
    monkeypatch.setattr(workspace, '_home_path', lambda: home / 'trusted')
    monkeypatch.setattr(workspace, '_BOOT_DEFAULT_WORKSPACE', home / 'trusted')
    monkeypatch.setattr(workspace, 'load_workspaces', lambda: [])
    monkeypatch.setattr(workspace, '_remote_terminal_workspace_candidate', lambda p: None)
    monkeypatch.setattr(routes, 'get_last_workspace', lambda: pytest.fail('global fallback'))
    s = models.Session(session_id=sid, workspace=None)
    with pytest.raises(ValueError):
        helper(s, None)


@pytest.mark.parametrize('entry', ['chat', 'sync', 'regenerate'])
def test_stale_request_rejected_at_route_before_runtime(incident, monkeypatch, entry):
    from api.session_ops import plan_regeneration
    rows, _ = incident
    s = models.get_session(rows[1]['id'])
    from api.process_event_utils import build_active_turn_token
    s.messages = [{'role': 'user', 'content': 'fixture', '_source': 'webui',
                   '_active_turn_token': build_active_turn_token('fixture-stream', 1)},
                  {'role': 'assistant', 'content': 'fixture reply'}]
    s.context_messages = list(s.messages)
    monkeypatch.setattr(routes, '_agent_runtime_barrier_response', lambda **kw: None)
    monkeypatch.setattr(routes, '_session_is_subagent_view_only', lambda sid: False)
    monkeypatch.setattr(routes, '_get_or_materialize_session', lambda *a, **kw: s)
    monkeypatch.setattr(routes, 'get_session', lambda *a, **kw: s)
    monkeypatch.setattr(routes, '_session_visible_to_active_profile', lambda *a: True)
    monkeypatch.setattr(routes, '_start_run', lambda *a, **kw: pytest.fail('stale runtime start'))
    monkeypatch.setattr(routes, 'require_ai_agent_class', lambda: pytest.fail('model access'))
    body = {'session_id': s.session_id, 'workspace': '/workspace/stale', 'message': 'fixture'}
    if entry == 'regenerate':
        body.pop('message')
        body.update(regenerate=True, regeneration_revision=plan_regeneration(s).turn.revision)
    handler = _FakeHandler()
    (routes._handle_chat_sync if entry == 'sync' else routes._handle_chat_start)(handler, body)
    assert handler.status == 400
    assert 'reload' in handler.json_body()['error']
    assert len(s.messages) == 2


def test_current_explicit_selection_survives_until_canonical_changes(incident):
    rows, home = incident
    row = rows[1]
    sid = row['id']
    s = models.get_session(sid)
    s.workspace = '/workspace/manual'
    s.workspace_binding_source = 'explicit'
    s.workspace_canonical_baseline = row['cwd']
    s.save(touch_updated_at=False)
    models.SESSIONS.clear()
    assert models.get_session(sid, metadata_only=True).workspace == '/workspace/manual'
    with sqlite3.connect(home / 'state.db') as conn:
        conn.execute('UPDATE sessions SET cwd=\'/workspace/new-canonical\' WHERE id=?', (sid,))
    assert models.get_session(sid, metadata_only=True).workspace == '/workspace/new-canonical'


def remove_evidence(home, sid, absence):
    if absence == 'missing-store':
        (home / 'state.db').unlink()
        return
    with sqlite3.connect(home / 'state.db') as conn:
        if absence == 'missing-row':
            conn.execute('DELETE FROM sessions WHERE id=?', (sid,))
        elif absence == 'missing-columns':
            conn.execute('ALTER TABLE sessions DROP COLUMN cwd')
        elif absence == 'profile-mismatch':
            conn.execute("UPDATE sessions SET profile_name='foreign' WHERE id=?", (sid,))
        else:
            conn.execute('UPDATE sessions SET cwd=NULL WHERE id=?', (sid,))


@pytest.mark.parametrize('absence', ['null-cwd', 'missing-row', 'missing-store', 'missing-columns', 'profile-mismatch'])
@pytest.mark.parametrize('origin', ['is_cli_session', 'source_tag', 'raw_source', 'session_source'])
def test_external_stale_sidecar_absence_fails_closed(incident, monkeypatch, absence, origin):
    rows, home = incident
    sid = rows[1]['id']
    path = home / 'sessions' / (sid + '.json')
    payload = json.loads(path.read_text())
    payload.update(is_cli_session=False, source_tag=None, raw_source=None, session_source=None)
    payload[origin] = True if origin == 'is_cli_session' else 'desktop'
    path.write_text(json.dumps(payload))
    remove_evidence(home, sid, absence)
    before = path.read_bytes()
    monkeypatch.setattr(models, 'get_last_workspace', lambda: pytest.fail('global fallback'))
    monkeypatch.setattr(routes, 'get_last_workspace', lambda: pytest.fail('global fallback'))
    handler = _FakeHandler()
    routes._handle_session_get(handler, urlparse('/api/session?messages=0&session_id=' + sid))
    assert handler.status == 200
    assert handler.json_body()['session']['workspace'] is None
    for helper in (routes._resolve_chat_workspace_with_recovery, routes._resolve_chat_workspace_for_regeneration):
        for request in (None, '/workspace/lfc'):
            with pytest.raises(ValueError, match='explicitly'):
                helper(models.get_session(sid), request)
    with pytest.raises(KeyError):
        models.get_session_for_file_ops(sid)
    handler = _FakeHandler()
    routes._handle_list_dir(handler, urlparse('/api/list?session_id=' + sid))
    assert handler.status == 404
    assert path.read_bytes() == before


@pytest.mark.parametrize('reload', [False, True])
def test_native_successive_canonical_changes(incident, reload):
    rows, home = incident
    sid = rows[1]['id']
    with sqlite3.connect(home / 'state.db') as conn:
        conn.execute("UPDATE sessions SET source='webui' WHERE id=?", (sid,))
    s = models.Session(session_id=sid, workspace='/workspace/manual', profile='default',
                       workspace_canonical_baseline=rows[1]['cwd'], workspace_binding_source='explicit')
    s.save(touch_updated_at=False)
    models.SESSIONS[sid] = s
    for cwd in ('/workspace/B', '/workspace/C'):
        with sqlite3.connect(home / 'state.db') as conn:
            conn.execute('UPDATE sessions SET cwd=? WHERE id=?', (cwd, sid))
        if reload:
            models.SESSIONS.clear()
        s = models.get_session(sid)
        assert s.workspace == cwd
        s.save(touch_updated_at=False)


def update_workspace(monkeypatch, sid, **body):
    monkeypatch.setattr(routes, 'read_body', lambda h: dict(session_id=sid, **body))
    monkeypatch.setattr(routes, 'resolve_trusted_workspace', lambda p: p if p else '/workspace/BOOT')
    handler = _FakeHandler()
    routes.handle_post(handler, urlparse('/api/session/update'))
    return handler


@pytest.mark.parametrize('known', [False, True])
def test_update_requires_selector_intent(incident, monkeypatch, known):
    rows, home = incident
    sid = rows[1]['id']
    if not known:
        remove_evidence(home, sid, 'null-cwd')
    handler = update_workspace(monkeypatch, sid, workspace='/workspace/lfc')
    assert handler.status == 400
    handler = update_workspace(monkeypatch, sid, workspace='/workspace/manual', workspace_explicit=True)
    assert handler.status == 200
    models.SESSIONS.clear()
    s = models.get_session(sid)
    assert s.workspace == '/workspace/manual'
    assert s.workspace_binding_source == 'explicit'
    remove_evidence(home, sid, 'missing-row')
    models.SESSIONS.clear()
    assert models.get_session(sid, metadata_only=True).workspace == '/workspace/manual'


@pytest.mark.parametrize('body', [{}, {'workspace': None}])
def test_model_only_update_preserves_unknown(incident, monkeypatch, body):
    rows, home = incident
    sid = rows[1]['id']
    remove_evidence(home, sid, 'null-cwd')
    handler = update_workspace(monkeypatch, sid, model='unknown', **body)
    assert handler.status == 200
    models.SESSIONS.clear()
    assert models.get_session(sid).workspace is None
