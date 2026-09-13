# Local validation / review evidence

Original code under review: `5d21950f4778f109b228c2d496cf81ee3e9004a9`.
The additive lineage correction is recorded below; the original receipt is historical.
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

## Additive lineage correction receipt

Applies to the commit containing this section, directly after PR2 head
`f2ad935ee65a0f523e2ed643b8135f3d1a8cead7`. That head's independently reproduced
bug paired the navigable continuation ID with the root's cwd/profile. The earlier
293-test coverage did not exercise that SQLite lineage boundary.

- RED: `tests/test_external_project_projection_lineage.py` gave **12 failed**
  against the unchanged parent API module (verified with `git diff --exit-code`).
  Failures were real GET workspace/profile assertions, including NULL root cwd
  versus `/work/one` tip and `/work/two` root versus `/work/one` tip.
  Log: `/workspace/inbox/6659-lineage-red.log`.
- GREEN: **12 passed** after the six-line shared projection fix. Tests use real
  SQLite, the real GET handler, and execute the actual sidebar partition function
  in Node. They cover compression and CLI-close continuations, tip NULL cwd,
  foreign tip profile (no default-project assignment or active-profile GET leak),
  reverse profile direction, and tip NULL profile falling back to the queried DB
  rather than inheriting the root. SQLite bytes and sidecar directory stay unchanged.
  Log: `/workspace/inbox/6659-lineage-green.log`.
- Combined run: concatenate the **24 test file arguments in both original commands
  above** into one invocation of the same Python/pytest, then append
  `tests/test_external_project_projection_lineage.py -q`: **305 passed**, 6.65s
  (the original 293 plus 12 new cases, together in one process).
  Log: `/workspace/inbox/6659-lineage-combined-green.log`.
- Additional sibling sweep with the same Python/pytest, `-q`:
  `test_session_lineage_metadata_api.py`, `test_session_lineage_collapse.py`,
  `test_issue4638_lineage_top_n_cap.py`, `test_pr1370_lineage_metadata_perf_and_orphan.py`,
  `test_issue5455_lineage_readonly_reads.py`, `test_import_cli_session_lineage.py`
  (all under `tests/`): **98 passed**, 4.01s.
  Log: `/workspace/inbox/6659-lineage-siblings-green.log`.
- `git diff --check`, Python compileall of the touched API/test module and
  `node --check static/sessions.js` pass. No frontend source changed.

Sibling inspection: ordinary/project-refill queries and cron/webhook/kanban
second passes all consume `read_importable_agent_session_rows` and therefore the
same corrected `_project_agent_session_rows` boundary. The root-is-tip path
already retains that root's own metadata and stays unchanged; upstream empty-tip
project ownership remains intact. The separate by-ID lineage metadata path adds
lineage IDs, not cwd/profile; canonical by-ID workspace probes already target the
served ID. Source-boundary/fork exclusions, TUI title handling, manual project
ownership and native-sidecar NULL-cwd preservation are intentionally unchanged.
No new source-inheritance or cross-source collapse rule was introduced.

Runner limitation: `./scripts/test.sh` was attempted but system Python lacks
working venv/ensurepip. Reused the existing isolated Python 3.12 environment
listed above rather than installing into system Python. The first fixture omitted
an agent messages index and triggered existing index self-healing; the final
fixture includes that index, was rerun RED against unchanged parent code, and
verifies byte-for-byte read-only projection. No production database was involved.
GitHub CLI has no login in this session; public GitHub API can verify PR identity.
No GitHub CI, full-suite, deployed-browser or production success is claimed.

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
