# External-session project projection

The session sidebar combines WebUI sidecars with a bounded window of sessions
from the Agent's `state.db`. Project binding backfill only visits the WebUI
index; it cannot classify a session that has never been imported. The served
session-list projection therefore also applies enabled workspace bindings to
unassigned rows. It uses the same exact workspace/profile matching rule as
new-session auto-assignment. Existing project IDs, including manual and system
assignments, are retained.

## Metadata authority

* Agent rows carry their own `cwd` and `profile_name`. Legacy schemas without
  these columns remain readable. Missing cwd is unknown, not the last workspace
  selected in a browser. A missing profile uses the database's profile scope.
* Indexed sessions are probed by ID, independently of the recent external-session
  window, so old imported sidecars can display canonical workspace metadata.
  Active streams retain their live workspace. Legacy native WebUI rows without
  canonical cwd retain their stored workspace.
* The probe opens only the requested profile's database, read-only; a missing
  named-profile database does not fall back to the active/default database.
* Claude Code's separate bridge has no verified Hermes workspace/profile binding;
  its workspace remains unknown instead of borrowing a global selection.

These are **sidebar metadata projections**, not a migration or an import. GET
listing does not save the projected workspace/project ID, rewrite transcripts,
materialize nonindexed sessions, or change the source Agent databases. Existing
import, execution, and file-manager workspace policies are outside this change.

## Desktop membership is not the same contract

The Agent Desktop project tree derives membership from project folders and
session cwd/repository metadata, including ancestor-folder and worktree rules.
Its project IDs are not WebUI project IDs. This change does not guess an ID by
project name, infer an external synchronizer's ownership, or claim full Desktop
membership replication. WebUI's explicitly configured exact path/profile
bindings are the supported classification contract here. Sessions without a
matching binding remain Unassigned; add a verified binding or explicitly move
such a session rather than assigning it by title or global workspace.

## Verification and rollout

Run `./scripts/test.sh tests/test_external_project_projection.py -q`. The suite
exercises a real SQLite store through the sessions GET handler and executes the
actual JavaScript sidebar partition function against the served JSON. It also
covers old indexed sessions outside the external window, enabled/disabled and
cross-profile bindings, existing project ownership, missing/legacy databases,
and unchanged stored messages/no sidecar creation.

Deploy the reviewed WebUI revision, preserving the current state volume and
Agent profile database mounts, and restart/recreate **WebUI** so its Python
modules and session-list cache are replaced. Reload the browser, verify the
served session workspace/project IDs and project/Unassigned filters. Merging
source or restarting only the Agent/synchronizer does not load this WebUI fix.
No database migration or conversation-import sweep is required. Unknown/unbound
sessions are expected to remain Unassigned.
