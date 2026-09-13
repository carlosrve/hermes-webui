# Local validation / review evidence

Code under review: `5d21950f4778f109b228c2d496cf81ee3e9004a9`.
Worktree: `/workspace/inbox/webui-6659-stack`.
Original independent findings were read from
`/workspace/inbox/upstream-project-review/REVIEW.md`; this is the implementer's
verification, **not** a replacement for the requested independent final review.

## Observed RED -> GREEN

- Upstream #6659 alone + prior external projection tests: **16 failed, 73 passed**.
  Twelve failures are missing behavior; four are absent local helper interfaces.
  Log: `/workspace/inbox/6659-baseline-tests.log`.
- Applying the prior functional local delta separately: **89 passed** (same files).
- Independent review reproductions: **3 failed** before correction: native sidecar
  with no source lost `/work/native` on canonical NULL cwd; `../other` and
  `bad/profile` returned default DB metadata. Log: `/workspace/inbox/6659-review-red.log`.
- Source-aware preservation: native reproduction **1 passed**. Fail-closed invalid
  names then gave **92 passed** across upstream, projection and review files.
- Additional isolated-profile regression: **1 failed** before the isolation guard;
  the general resolver mapped foreign name onto pinned home. Log:
  `/workspace/inbox/6659-isolated-red.log`. Guard added: review tests **4 passed**.
- Expanded the native test to actual `/api/sessions` GET handler with both canonical
  `webui` and absent source and unchanged SQLite bytes. Final suites below include
  that expanded coverage.

## Final commands and results

Python environment reused read-only from the prior isolated review checkout:
`/workspace/inbox/webui-unassigned/.venv/bin/python` (Python 3.12). Execute from this
worktree, not the deployed checkout. Test fixtures redirect state to temporary homes.

```sh
/workspace/inbox/webui-unassigned/.venv/bin/python -m pytest \
  tests/test_external_project_projection.py \
  tests/test_external_project_projection_review.py \
  tests/test_project_assigned_cli_session_limit.py \
  tests/test_project_bindings.py tests/test_project_bindings_regressions.py \
  tests/test_issue1614_project_profile_filtering.py \
  tests/test_issue4842_cron_projection_perf.py tests/test_issue2628_cli_sessions_perf.py \
  tests/test_webhook_project_sessions.py tests/test_issue3019_cron_project_sessions.py \
  tests/test_issue5379_cron_project_optin.py tests/test_session_attention_badges.py -q
```

**171 passed**, 3.75s. Log: `/workspace/inbox/6659-stack-green.log`.

```sh
/workspace/inbox/webui-unassigned/.venv/bin/python -m pytest \
  tests/test_session_sidebar_cache.py tests/test_session_cache_ownership.py \
  tests/test_cli_sessions_cache_cap.py tests/test_sidebar_session_partition.py \
  tests/test_file_manager_external_session.py tests/test_session_import_workspace_validation.py \
  tests/test_session_active_profile_authorization.py tests/test_issue1611_session_profile_filtering.py \
  tests/test_session_metadata_fast_path.py tests/test_session_cli_scan_fast_path.py \
  tests/test_session_metadata_cli_lookup.py tests/test_cli_sessions_cache_fingerprint.py -q
```

**122 passed**, 3.16s. Log: `/workspace/inbox/6659-related-green.log`.

`git diff --check`, Python compileall on the three changed API modules and
`node --check static/sessions.js` also pass. No frontend source/build pipeline
changed. Full repository suite, deployed browser E2E and production validation
were not run. No CI success is inferred from these local results.

## Review boundaries

- Read actual upstream and local diffs, not PR titles. `git range-diff
  b1286878..cf82b06e eea69936..4fbcf25b` shows only added cherry-pick trailers;
  upstream code changes and authorship were not modified.
- Tests exercise real SQLite -> GET handler -> actual sidebar partition JavaScript,
  manual ownership, missing/legacy/named DBs, invalid and isolated profiles,
  NULL cwd native preservation and stored-content invariants.
- No live DB reads/writes, imports, deletions, restarts, deployment or merge.
- Request an independent review of the exact final PR head before Carlos merges.
- Unsupported ancestor/worktree rules, external discovery caps and other limits
  are explicit in `external-session-project-projection.md`.
