# Temporary fork patch ledger: sessions / projects

## Order and provenance

Base: `eea6993654832d9080952ae21c88dea8c5b344ee`, branch
`integration/pr-6836-current-2026-09-12`, verified unchanged on origin.
It already contains #6836 (`12453f00` integration; upstream head
`f1b8c91d0cffd96ec9dfd487a9022998acc4ef87`) plus the fork workflow-removal commit.
Do not copy these changes onto master. This task leaves master untouched.
Final inventory found pre-existing fork commit `090b235154a405e2f2553af920baa25fa39ed1bc`
(removes inherited workflows) on origin/master beyond upstream `b1286878`.
Thus master was already not strictly pure upstream; repairing that shared history
requires a separate approved action. No new divergence is added to master here.

1. Backport **all 28 commits** of [upstream #6659](https://github.com/nesquena/hermes-webui/pull/6659),
   head `cf82b06e1ed9dc200229d8bb70b223ee6268750c`, from its merge base
   `b1286878a437d374d2bfb6db3e3d084e33d3fe5d`, in original order with `git cherry-pick -x`.
   All apply cleanly. Original author and dates retained:
   Rodrigo Gomes da Silva <rodrigo.smscom@gmail.com>. No squash, no local edits
   inside those commits. PR remained open/unmerged at verification.
2. Local correction `5d21950f4778f109b228c2d496cf81ee3e9004a9` depends on #6836's
   exact bindings and #6659's bounded/profile-aware session projection. Adds
   canonical cwd/profile projection, optional read-only by-ID sidecar probes,
   source-aware native-workspace preservation, and fail-closed profile probes.
   Keeps existing project IDs. It does not replace #6659's scheduling algorithm.
3. Documentation-only commits follow. Review-only branch:
   `review/6659-canonical-projection`. Supersedes the approach of fork draft PR1,
   without rewriting its branch or the shared integration branch.
4. Additive lineage correction after `f2ad935ee65a0f523e2ed643b8135f3d1a8cead7`
   (the commit containing this entry): `_project_agent_session_rows` now copies
   the served tip's `cwd` and `profile_name`, including NULL/absent values, rather
   than pairing its ID with root routing metadata. Root title/time and upstream
   lineage project ownership remain unchanged. The 28 cherry-picks above and
   the original local correction are untouched. Regression gates live in
   `tests/test_external_project_projection_lineage.py`.

## Retirement / future updates

- When #6659 merges, sync pure upstream master normally and start a **new** review
  branch from the maintained integration baseline. Determine the merged SHA and
  compare patches (squash merges may have different IDs). Omit this entire 28-commit
  backport group once its behavior is present; do not blindly cherry-pick it again.
- Reapply only the local corrections if still needed. Retire them only when upstream
  passes the external projection + independent review + lineage regressions, including GET
  and sidebar classification, NULL/different root cwd versus served tip, tip-profile
  isolation and NULL-profile DB fallback, absent cwd preservation, invalid/isolated profiles,
  and no message/sidecar mutation. #6659 alone does not meet those tests.
- #6836 is an existing independent dependency: retire its backport when upstream
  includes bindings. #5771 (catalog) and #7037 (lineage writes) are NOT added here.
- Never squash the upstream group together with the local correction. Never
  force-push a shared integration branch. Carlos reviews/merges; this stack does
  not authorize merge, deployment, restarts, imports, or changes to live state.

## Exact backport mapping (application order)

| Upstream commit | Fork cherry-pick |
| --- | --- |
| `20ad4bec81dd9426d8f1330c3b1bef46be6aacc7` | `760375e5648c820b54890734141a8b2751283965` |
| `70bd1ae792d202221a9ff1e1ab311b31ea1cfa1a` | `80ba9d2adc2041f8b9ba1ebd24b245795d899dcf` |
| `d8cea75678f64183983d95d414c8c26b994c87c2` | `a4e9763c2de8819a150869cc807c099dbc6c6be0` |
| `22f5433d3648700e9a4881d0e25da8b127e894f0` | `f6207dd18623a5a6131750fcc5ba716de678d1aa` |
| `8be6ad69afb388d5e1ca44b5e3bb52c13953434e` | `b699cd242b0ed65b77c54070b12616ed7effe329` |
| `7247e25f73d7e8e2e6135541635fefecb19852fc` | `04d2c2112c77021e89630f7eceb54308eb9148b0` |
| `cd7bcaa80c6b51bc1b1708d821a286cc9759c58b` | `4bfaff878d0fd613f5f5f9f02981a18998fe17c8` |
| `a734710168c34ce8f256ab4440ac74808dd229c3` | `3e1cffbfd5ce3adc71417fecaa12f5e7ba30a678` |
| `209d478a9695b27bb6cb1f977fc8d88ece5b62eb` | `4d1bda4c0d788346700c9e3fe4e5c778c700bddf` |
| `25e5484c14e58b920b486566b871fc2089b54135` | `527df44cd7cd0a264ba6510ea7748d42c7a02cd7` |
| `f7811af52bd08f414d7f9bb84d8a4eda34fd489d` | `55a01f6c73b240fff3b82c82847d710e2c907001` |
| `4523a7d1df17ba25cdea2d83ab7b9465f6f64158` | `bf53b987c7a223044be0f8353497fc475e804acb` |
| `28d8a844763198f0d02870b1f849af52f70bc9ab` | `22f08bec670841657280bf1882981022aedd2157` |
| `9b768628dac5d330f0bf382742114263e1dde631` | `16e2bf25392a21ca2e7e53a283aa16812a7fbc2e` |
| `5123ef68edef369ce0279d933a35051e48471eb4` | `2771731a7d3eca682163aa0622462dd02557e50d` |
| `ea325c2cb363d73030084baed6dfdeeffc9637e0` | `b04d8d4ba7cb14b837482a09fdbc1b51c9b9559d` |
| `a70002cafd51f568ebf168d56e83a7a58ef80482` | `d1d0dffb1462915a8019bdf99e3cd871af7bd999` |
| `3ea5d57a1a7ccd904ac2f3f339985544094aa78c` | `60883de618813bef9188c7844742a6d62d5ff786` |
| `d7dcf63b5e70d90ee6a2b272e5da26de7fe15815` | `8386155e5b1f98621dc8b22d64df82e737d2db06` |
| `300cb5a5bd5a413d220441b43235783c29b96fbe` | `43caf30c325e4941e57255bd87afb4c40afef7fd` |
| `0ced2d335a027de4f25a3c63c0cf4684ad86ba7e` | `40b01d06c12857c8091b63c443bec53f8e86f47f` |
| `73b5543b7aaff143ab28641f154c01c265dc7a7b` | `ec184d45776cb13911b8522d67d25fe6bf4f2358` |
| `3e3092cfbbc8ec57f97bef366dd055f5619ac946` | `70b1059b6cf11518cdf33250c5ca1698d81bbca0` |
| `50c2bdfddf807eaa9da3cac5bed7ca0c5a4cd0af` | `d31a4231b7f77b74676d694319cb5af14977aaa3` |
| `ccc3475ebdec2a9dec89ca3876fd5cdd7e9029c8` | `be0706266091cb227928c016903b3c2dab6a4ac7` |
| `ac6b9904decbbee496c7085de67587c8413d9a2d` | `f5916596e481a4367f314f06d9c10000dd9dcdc9` |
| `7ace34f538672fb3344314a44575c40d449bc4d7` | `df30eec6690153a0d3770493483449b162063672` |
| `cf82b06e1ed9dc200229d8bb70b223ee6268750c` | `4fbcf25b884a45dd8ea9f4c7dcf4d2a88ce175e1` |
