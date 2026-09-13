# External-session project projection (review stack)

The sidebar combines WebUI sidecars and bounded Agent `state.db` projections.
#6836's index backfill cannot classify a never-imported external session.
#6659 retains already project-assigned sessions and fairly budgets their windows;
it does not derive membership from cwd. The separate local delta applies enabled
exact workspace/profile bindings to unassigned served rows, without importing them.

## Authority and preservation

- Agent rows use their canonical `cwd` and `profile_name`. Missing cwd stays
  unknown, never the browser's global/last workspace. Legacy schemas remain readable.
- Indexed sidecars are probed by ID, independently of the recent external window.
  Active streams retain their live workspace. Canonical nonempty cwd takes priority.
  Missing cwd clears stale workspace only with positive external-source evidence;
  native WebUI or ambiguous legacy provenance retains its valid stored workspace.
  Canonical source `webui` counts even when the sidecar has no source tag.
- Probes open only a read-only existing profile DB. Invalid names fail closed
  before the general resolver can fall back to default. Isolated mode rejects
  foreign profile requests instead of resolving them to the pinned home.
- Existing project IDs (manual, system, or previously wrong) are preserved.
  This patch does not decide that a prior explicit assignment should be erased.
- Claude Code has no verified Hermes binding; its workspace remains unknown.

The **new projection** does not persist workspace/project changes, rewrite messages,
create sidecars, or change Agent DB contents. Do not interpret this as a promise
that the whole GET handler is side-effect-free: existing reconciliation/pruning
and project metadata migration paths remain outside this patch.

## Explicit limitations

- Exact configured path/profile equality only. No ancestor-directory membership,
  repository inference, worktree mapping, path canonicalization or matching by title.
- No complete Desktop catalog/ID equivalence or two-way synchronization.
- External sessions without a previously resolved project ID still have bounded
  discovery windows. A newly inferable old nonindexed session outside the window
  is not made discoverable by this patch. #6659's assigned-row recovery only knows
  pre-existing ownership; this does not turn cwd bindings into an unlimited scan.
- Unknown/unbound sessions remain Unassigned. Project IDs already wrong are not
  repaired. Execution/import/file-manager workspace policies are unchanged.
- Tests invoke the actual GET handler and JavaScript partition function; they are
  not a deployed-service/browser-E2E validation. No production change was made.

See [patch ledger](fork-session-patch-ledger.md) for provenance, dependency order
and retirement conditions; [local evidence](fork-session-stack-validation.md)
for exact test commands and red-green results. Only Carlos may merge/deploy.
