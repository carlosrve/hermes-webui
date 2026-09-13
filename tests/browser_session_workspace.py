#!/usr/bin/env python3
"""Real loadSession/restore + file-manager proof, isolated and model-free.

Incident metadata is replayed verbatim except /workspace is remapped beneath
an isolated temporary root. No production messages or credentials are loaded.
"""
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_conversation_lifecycle import _start_webui_server, _terminate_process


def main():
    repo = Path(__file__).resolve().parents[1]
    artifacts = Path(os.environ.get('WORKSPACE_PROOF_ARTIFACTS', tempfile.mkdtemp(prefix='workspace-proof-artifacts-')))
    artifacts.mkdir(parents=True, exist_ok=True)
    profile = os.environ.get('WORKSPACE_PROOF_PROFILE', 'default')
    with tempfile.TemporaryDirectory(prefix='workspace-open-proof-') as tmp:
        root = Path(tmp)
        base_home = root / 'hermes-home'
        home = base_home if profile == 'default' else base_home / 'profiles' / profile
        state = root / 'webui-state'
        sessions = state / 'sessions'
        sessions.mkdir(parents=True)
        home.mkdir(parents=True)
        work = root / 'workspace'
        work.mkdir()
        agent = root / 'no-agent'
        agent.mkdir()
        (agent / 'run_agent.py').write_text('"""No model calls in this proof."""\n')
        rows = json.loads((repo / 'tests/fixtures/session_workspace_metadata.json').read_text())
        with sqlite3.connect(home / 'state.db') as conn:
            conn.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, profile_name TEXT, source TEXT, title TEXT, model TEXT, started_at REAL, message_count INTEGER)')
            conn.execute('CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp REAL)')
            for row in rows:
                if profile != 'default':
                    row['profile_name'] = profile
                row['sidecar']['profile'] = profile
                row['cwd'] = str(work / Path(row['cwd']).name)
                Path(row['cwd']).mkdir(exist_ok=True)
                (Path(row['cwd']) / 'proof.txt').write_text(row['id'])
                row['sidecar']['workspace'] = str(work / 'lfc')
                (work / 'lfc').mkdir(exist_ok=True)
                conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)', (row['id'],row['cwd'],row['profile_name'],row['source'],'Fixture','unknown',1,1))
                conn.execute('INSERT INTO messages(session_id,role,content,timestamp) VALUES (?,\'user\',\'Fixture message\',1)', (row['id'],))
                payload = dict(row['sidecar'], session_id=row['id'], title='Fixture', created_at=1, updated_at=1, messages=[{'role':'user','content':'Fixture message','timestamp':1}])
                (sessions / (row['id'] + '.json')).write_text(json.dumps(payload))
        projects = {}
        for row in rows:
            pid = row['sidecar']['project_id'] or 'd00be5f6f488'
            projects[pid] = {'project_id':pid, 'name':Path(row['cwd']).name,
                             'profile':profile, 'workspaces':[row['cwd']],
                             'auto_assign':True}
        (state / 'projects.json').write_text(json.dumps(list(projects.values())))
        profile_state = home / 'webui_state'
        profile_state.mkdir()
        (profile_state / 'last_workspace.txt').write_text(str(work / 'lfc'))
        # Minimal allowlisted environment, not a copy of the production env.
        env = {k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','HOME')}
        env.update(HERMES_HOME=str(home), HERMES_BASE_HOME=str(base_home), HERMES_WEBUI_ISOLATED_PROFILE='1' if profile != 'default' else '0', HERMES_CONFIG_PATH=str(home/'config.yaml'), HERMES_WEBUI_STATE_DIR=str(state), HERMES_WEBUI_AGENT_DIR=str(agent), HERMES_WEBUI_DEFAULT_WORKSPACE=str(work), HERMES_WEBUI_SKIP_ONBOARDING='1', HERMES_WEBUI_HOST='127.0.0.1', NO_PROXY='127.0.0.1,localhost')
        proc = log = None
        results = []
        try:
            proc, log, _, url = _start_webui_server(repo, env, artifacts)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
                page = browser.new_page()
                # The proof must never submit a chat, even accidentally.
                page.route('**/api/chat/**', lambda route: route.abort())
                page.goto(url, wait_until='domcontentloaded')
                page.wait_for_function('() => typeof loadSession === "function" && S._bootReady === true', timeout=30000)
                for width in (1280, 390):
                    page.set_viewport_size({'width':width,'height':900})
                    for row in rows:
                        result = page.evaluate('''async sid => {
                            await loadSession(sid, {force:true});
                            openWorkspacePanel();
                            await loadDir('.');
                            const listing = await api('/api/list?session_id='+sid);
                            return {sid:S.session.session_id, workspace:S.session.workspace,
                              chip:document.querySelector('#composerWorkspaceChip').title,
                              files:listing.workspace, entries:listing.entries,
                              tree:document.querySelector('#fileTree').innerText};
                        }''', row['id'])
                        if row is rows[0]:
                            page.screenshot(path=str(artifacts / f'first-open-{width}.png'))
                        assert result['sid'] == row['id'], result
                        assert result['workspace'] == row['cwd'], result
                        assert result['chip'] == row['cwd'], result
                        assert result['files'] == row['cwd'], result
                        assert any(entry['name'] == 'proof.txt' for entry in result['entries']), result
                        assert 'proof.txt' in result['tree'], result
                        results.append({'width':width, **result})
                    page.screenshot(path=str(artifacts / f'workspace-{width}.png'))
                last = rows[1]
                chosen = rows[-1]['cwd']
                page.evaluate('''async ({sid, workspace}) => {
                    await loadSession(sid, {force:true});
                    await switchToWorkspace(workspace, 'Proof selection');
                    await loadSession(sid, {force:true});
                }''', {'sid':last['id'], 'workspace':chosen})
                assert page.evaluate('S.session.workspace') == chosen
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('expected => S.session && S.session.workspace === expected', arg=chosen, timeout=30000)
                assert page.evaluate("document.querySelector('#composerWorkspaceChip').title") == chosen
                assert page.evaluate("async () => (await api('/api/list?session_id='+S.session.session_id)).workspace") == chosen
                # Existing external stale sidecar, now without canonical cwd.
                unknown = rows[0]
                with sqlite3.connect(home / 'state.db') as conn:
                    conn.execute('UPDATE sessions SET cwd=NULL WHERE id=?', (unknown['id'],))
                page.evaluate('async sid => { await loadSession(sid, {force:true}); }', unknown['id'])
                assert page.evaluate('S.session.workspace') is None
                assert page.evaluate("document.querySelector('#composerWorkspaceChip').title === t('no_workspace')")
                assert page.evaluate("async () => (await fetch('/api/list?session_id='+S.session.session_id)).status") == 404
                page.evaluate("async workspace => { await switchToWorkspace(workspace, 'Unknown selection'); }", chosen)
                assert page.evaluate('S.session.workspace') == chosen
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('expected => S.session && S.session.workspace === expected', arg=chosen, timeout=30000)
                assert page.evaluate("document.querySelector('#composerWorkspaceChip').title") == chosen
                assert page.evaluate("async () => (await api('/api/list?session_id='+S.session.session_id)).workspace") == chosen
                browser.close()
            (artifacts / 'results.json').write_text(json.dumps(results, indent=2))
            print(f'PASS: {len(results)} real browser open/chip/file-root cases and hard reload; artifacts={artifacts}')
        finally:
            _terminate_process(proc)
            if log:
                log.close()


if __name__ == '__main__':
    main()
