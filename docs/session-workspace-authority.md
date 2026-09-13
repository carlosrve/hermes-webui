# Session-open workspace authority (local integration delta)

## Contract

For an existing session, sidebar project membership is not a working-directory
selection. `get_session()` overlays the same-profile Agent `state.db` `cwd`
using the existing read-only metadata reader; it does not import transcripts,
rewrite history, or perform a bulk sidecar migration. Cache hits and cold
metadata/full reads share this resolution. Missing columns, missing profile
stores, mismatched profiles and missing cwd provide no authority to override an
existing native/manual workspace. When canonical cwd is known, it supersedes
unmarked historical settings regardless of source. Only recorded selector intent
against that canonical baseline overrides it; absent evidence preserves native
legacy settings. This avoids guessing intent from stale non-null sidecars.

New external imports and synthesized external sessions use canonical cwd only,
never unverified source-metadata roots or the browser's last selected workspace.
With no evidence, workspace is `null`, the UI says No workspace, and implicit
execution/file operations fail closed until the user selects one. A native new
chat may still use the configured new-chat default; that is a different contract.

A deliberate workspace-selector update sends `workspace_explicit: true` and records
`workspace_binding_source=explicit` and `workspace_canonical_baseline`
in the WebUI sidecar. That choice survives reopen while canonical cwd is
unchanged. A subsequent canonical cwd change supersedes it. Preexisting sidecars
have no such marker: their historical global-default pollution is not treated as
an explicit user choice. An active accepted run retains its workspace until it
settles. A browser-carried workspace that conflicts with a fresh authoritative session
resolution is rejected with a reload/select error before chat or regeneration
can start. Use the selector/session-update endpoint for deliberate changes.
Without canonical cwd evidence, legacy native explicit request workspaces retain
their prior trust-validated semantics. Unverified external sidecars require a
selector action; stale browser echoes are not evidence. Canonical binding markers
remain distinct from legacy native choices across successive cwd changes. Null or
omitted update workspaces cannot silently assign the boot default.

File-manager reads and implicit chat/regeneration must not silently recover a
known canonical root to an unrelated last workspace. Native deleted-root
recovery without canonical evidence remains supported. This does not widen the
saved-workspace/path-trust policy. Historical `created_workspace` and system
prompt snapshots remain unchanged intentionally.

## Provenance ledger

Base: `06673a9d4b18` on `integration/pr-6836-current-2026-09-12`.
This delta is local; no additional upstream authorship is claimed.

Upstream PR search preceded implementation (open and closed PRs, queries for
workspace/session/import and canonical/cwd). Relevant actual diffs inspected:

- **#7351**, released by **#7504**, already present in the base as `394ab31e`:
  binds Agent's task-local cwd at the execution seam. Reuse, do not cherry-pick
  twice. It cannot correct the stale value passed by session-open/import.
- **#7168**, head `33998d53482ea45d01d28906715ab780def6231b`:
  remote POSIX normalization and profile-aware path resolution. Its import
  still calls `get_last_workspace(profile=profile)`, so it does not fix this
  session attribution bug. Broad unrelated backend changes not backported.
- **#7440**, head `61275aef88c059dd70b0a224ebec83770d9ded37`:
  gateway workspace relay plus steer lifecycle changes, not sidecar/open
  authority. Not backported; remote Gateway execution remains outside this
  local in-process proof.
- **#6307**, merged: deleted-workspace recovery already in the base. It solves
  missing paths, not incorrect-but-existing roots. Preserve native recovery.
- **#6659** and the existing local canonical/lineage projection are already in
  the base. They affect sidebar rows, not the open/import/file-manager paths.

## Incident fixture and reproduction

`tests/fixtures/session_workspace_metadata.json` contains only the seven actual
incident IDs and their observed cwd/profile/source/workspace/project fields.
No message text, titles, credentials, or production configuration is included.
Six sidecars had `/workspace/lfc` despite canonical cwd in coopebrisas, gnc,
support, hermes-repo (two) and vx.ai. The UNED session
`20260729_160636_03274f23` had `/workspace` versus `/workspace/uned-plan`.
Project IDs were already corrected separately; workspace fields were not.

- `tests/test_canonical_session_workspace.py`: isolated SQLite plus metadata
  sidecars -> real GET handler -> actual JS workspace display -> chat workspace
  resolution -> installed Agent `resolve_agent_cwd()` -> file-manager resolver.
  Canonical DB and sidecar bytes remain unchanged in the metadata-open replay.
  The Agent seam requires an installed checkout on PYTHONPATH; it skips when
  absent rather than pretending an execution binding was tested.
- `tests/browser_session_workspace.py`: starts a real isolated WebUI and runs
  real `loadSession()` in Chromium, checks accepted `S.session.workspace`, chip
  and `/api/list` root, at desktop and narrow widths, then tests an explicit
  selector function action and hard reload, unknown-root fail-closed/selection, and
non-default profiles (`WORKSPACE_PROOF_PROFILE=proof`). Incident paths are remapped beneath a
  temporary workspace root. Chat routes are blocked and no provider is called.

The handler test failed on base with `/workspace/lfc` instead of
`/workspace/coopebrisas`. The browser proof also failed on base with the same
session's state, chip and file listing all pointing at the remapped LFC root.
Run the browser proof with Playwright installed; optional
`WORKSPACE_PROOF_ARTIFACTS` retains screenshots, structured results and logs.

## Review boundaries

No merge, deployment, process restart, production session opening, production
chat, production config edit, or production metadata write is part of this PR.
Only metadata-only read probes were used against production. Fixtures and
servers are local. Browser screenshots prove desktop/narrow rendering, not
native mobile interaction. Remote Gateway/Docker/SSH execution, unknown legacy
cwd recovery UX beyond fail-closed behavior, and historical prompt correction
are not certified by this proof. Full repository suite and cross-platform CI
must be reported separately from focused test results.

Local final validation: 306 passed, one preexisting Claude WAL-cache invalidation
failure reproduced unchanged on base (241 passed, same failure). The focused
canonical suite passes without Agent skips. Chromium proof passes 14 incident
open/chip/file-root cases per profile at two widths (default and isolated `proof`),
plus selector/reload and unknown-root checks. No accepted model execution is
claimed: the installed Agent task-local cwd resolver is exercised with the same
workspace returned by the real session-open and chat-resolution handlers.
