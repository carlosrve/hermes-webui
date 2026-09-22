# Integration validation receipt

Branch: `integration/pr-6836-current-2026-09-22`

Base: `30b407439a22cf02701b30cc803dbc186b4275ce`

This receipt covers local source verification only. It does not claim GitHub CI,
deployment, production state access, or runtime activation.

## Focused results

All commands used the isolated integration worktree. Python tests used
`/workspace/inbox/webui-unassigned/.venv/bin/python`; canonical execution-cwd
proofs added `PYTHONPATH=/workspace/hermes-agent` so `agent.runtime_cwd` was
actually exercised rather than skipped.

- Project bindings: `tests/test_project_bindings.py` plus
  `tests/test_project_bindings_regressions.py`: **26 passed**.
- Assigned CLI limits/performance: `test_project_assigned_cli_session_limit.py`,
  `test_issue2628_cli_sessions_perf.py`, and `test_issue4842_cron_projection_perf.py`:
  **88 passed**.
- External projection and served-tip lineage: the three
  `test_external_project_projection*.py` files: **33 passed**.
- Canonical workspace, external file manager, and durable compressed-session
  resume: `test_canonical_session_workspace.py`,
  `test_file_manager_external_session.py`, and `test_compressed_idle_resume.py`:
  **88 passed, 27 skipped** without Agent on `PYTHONPATH`; the canonical file
  alone was then rerun with the Agent source and gave **65 passed, 0 skipped**.
- Six sibling lineage suites: **100 passed**.
- Remote POSIX/profile preservation, stale recovery, workspace panel/defaults,
  and #7351 task-cwd wakeup coverage: **104 passed** after adapting two obsolete
  fallback expectations to the canonical-cwd contract.
- Project new-session/provider/sidebar/cache sibling sweep: **59 passed**.
- One combined process containing the 17 principal binding, limits/performance,
  external projection/lineage, canonical workspace, file-manager, resume, and
  lineage-sibling files: **362 passed**.

## Static checks

- `python -m compileall -q api`: passed.
- `node --check static/panels.js`: passed.
- `node --check static/sessions.js`: passed.
- `git diff --check` over the integration range: passed.
- Added-line security scan found no hardcoded secret assignments, shell execution,
  pickle loading, or formatted SQL. The two `eval` matches are test-side execution
  of extracted repository JavaScript, not user-controlled runtime input.
- Read-only manual review covered the full local canonical-workspace commit and
  conflict-sensitive models/routes/panels paths. No blocking correctness or
  security finding remained after preserving profile-aware remote-POSIX path
  resolution and adapting the two superseded fallback tests.

## Baseline and environment limitations

`tests/test_issue6611_regeneration_authority.py::test_snapshot_refuses_when_wal_data_version_changes`
failed both on this branch and on a detached worktree at the exact upstream base
`30b407439a22cf02701b30cc803dbc186b4275ce`; it is not introduced by this stack.
The focused regeneration-authority sweep therefore reported **116 passed, 1
baseline failure**.

`tests/browser_session_workspace.py` could not run because no available Python
environment has the optional `playwright` package or Chromium installed. The
real handler/JavaScript/Agent execution-cwd coverage above passed, but no browser
screenshot proof is claimed.
