# Temporary fork integration ledger: projects, sessions, and workspace authority

## Integration identity

- Branch: `integration/pr-6836-current-2026-09-22`
- Upstream base: `30b407439a22cf02701b30cc803dbc186b4275ce`
- The shared `master`, the prior integration branch, and their worktrees were not modified.
- This stack is local and unpublished. Carlos retains merge and deployment authority.

## Ordered stack

1. Replay the 13 functional, non-merge commits of upstream PR #6836, from
   `f8030121c4b45cc504a2884c4b17fa0675121563` through
   `f69d64b75053d1064f3f25378bf5da54ddac85da`, with `cherry-pick -x`.
   The PR head `f1b8c91d0cffd96ec9dfd487a9022998acc4ef87` also contains master merges;
   those merges are intentionally excluded.
2. Preserve the fork policy that inherited upstream workflows must not run by
   replaying `01ef04e82d9e76c35c392a64886869a0a31e2da0`. The current upstream base
   still tracked all seven deleted workflows, so this commit remains necessary.
3. Replay all 29 functional commits of the current PR #6659 head
   `e1fc35b49da9b531970f794eb53d4ddb91537dea`, after its merge base
   `91044fc18d037166bf786444fe99245749a3dd76`, in original order with
   `cherry-pick -x`. This replaces the prior 28-commit snapshot; no old snapshot
   commit or master merge is included.
4. Replay the local canonical projection and served-tip lineage fixes from
   `00864775b5ae66e41de161fe16ab62446726e821` and
   `8db7dad97b4f5e65937110dce932a979c92df363`. Their obsolete ledger edits were
   intentionally dropped and replaced by this document.
5. Port the behavioral delta from `2c66360020d7025fedc465007427c2ad8a1ce69a`
   onto current upstream. The port keeps upstream profile-aware/remote-POSIX path
   resolution, durable compressed-session resume, and #7351's task-local Agent cwd
   binding. Canonical cwd remains authoritative for open/import, file-manager root,
   chat/regeneration, and explicit selector updates without reverting current
   models/routes/panels behavior.

## PR #6836 exact mapping

| Upstream | Integration |
| --- | --- |
| `f8030121c4b45cc504a2884c4b17fa0675121563` | `b25aeddf042151c282350d4a2f74c2a5dab078ca` |
| `4ccc4b6a2c7ddb5f23af4005dbd0ad622ad42212` | `ed52fbe1221449324f1c8f67e29d1c59d8548076` |
| `a5f560f685b75c3d6cfcb3fe11e796a68406d896` | `ebf7d5381c73366e8091ea157bdc0ac2e861926f` |
| `1e95023ff103a8b1b4b215a4d2ddecf05113fbdf` | `7c2528b1c1f35317e65154b84fe4f3fb214c4d27` |
| `b53450e2572963ba8c1efd5c7993f59c517f776f` | `50d641891827d40f8ef7b3ca001a941285d985a8` |
| `2c7de9f979296b927f9891b5e2d54e25044754c2` | `0c6255689648c7e951f0a98e88096b696829d3a6` |
| `5f0d8fd2bcb10c161f04cc64405943e270df4e3d` | `7fb9eb364af692cc0cc136503c7a0555caae6c7c` |
| `7f18651492b00d8fb60a61cd79291f8220b695dd` | `a9707c9f9a9acc0fd68020395c64a16e3ab512ae` |
| `52fcf5f3bc1c223bd5dfac4a3f5490b08af212c0` | `58b6c81b388bdd37724fc7f3e985341e94cb194f` |
| `6bdee54f4f0470acb74bcf0b83d119dfba17aa7d` | `fe4c851a678f42b92e532d6e17c7808212a88a0f` |
| `20b75266e585d3144fc232ff870c2d45bfe02f4f` | `a12908238658e26d2532791ae35a1c3e23e3f9a2` |
| `c6e76d748bd2af6ed6b9c4e68938743b37332798` | `719cebe9d517a66022aaeda2c56c9ffcd43e68c4` |
| `f69d64b75053d1064f3f25378bf5da54ddac85da` | `a6c182faf28455133b448bd3e928f9c4fce190bd` |

Workflow policy mapping: `01ef04e82d9e76c35c392a64886869a0a31e2da0` →
`8bcaf72533e566630801ad11e5a9b59fbbf5e1f2`.

## PR #6659 exact mapping

| Upstream | Integration |
| --- | --- |
| `d075ec3a0e63afc26ab284aa131ad1e13ca8d6f2` | `cda7e8e435182d6cce6624f6d0afbe67425ea02a` |
| `ad5a42aca5a1dc9431de162e9e9e940ca2f0b57b` | `12e0f9f8a6a59ead6a24a4736932741342616dd5` |
| `badab590a810fbe8a74cd70469abb60208285c58` | `f2d78c6f65a026d3c484c9987286bc70f8c58109` |
| `2f24b4b0f8023c373c93b8dbc1d2fe32f2add078` | `a564d813466bcb38523a0c62146cab12837fe167` |
| `e20cb40087ac3368105acbfd2b25ce282e65546b` | `e2c7ef2f32822d5b4856da67307b6ef93153dc2b` |
| `fbfff49aeed72a7983e8bc4824768aa176e0947d` | `f8b4363fa57597ee6162ba9251f842a6e62ceb77` |
| `9697847a5e20cf8de306204a466b358aba417ecd` | `6948d518681690fcc9306a3665b54f4e2bf971ee` |
| `97c6eafa3fd39fca173072dec7389484aecdeff4` | `5d54960cdcc9ead3aabbb11d6c8abaee92abe993` |
| `456f9a0aa4728fdbf187ae7bc34c274f40d96635` | `2a312041b0f93d05e68598f21e421a6e8d961777` |
| `a4ab7f49444d710c97f4ff4db9cdcb25553447a1` | `5f240aa2bb2d36861b34a2e841acffef850b5c06` |
| `16d23ed8c91a67892a57b04004ea51bd0802cac2` | `cdef0bb8c32d01df1705fa04be1b1e2cede18da0` |
| `d95c016e28292abe539f1a1bcf3e0a0ce8a88f2d` | `eb3fb5a00881a7c9058f56276f73a6377088f377` |
| `6c2c8ce65b1988efc450bc2404a9d25d0e691095` | `b82c256e82570336d56436a4a5c5b12378939460` |
| `1a26994c4db88aff1bd84d07a9c1509358d87c86` | `3e2a1ffcfc470e0b051cf2dccd3771fc966dd1a1` |
| `27ce4b03c1eb67a8dc5ab209fda6734944dcee5d` | `ab9309a0e21de7c94b15d5775a4fb843ee458735` |
| `477b3e78ab07c33a1611fcf0b02fe864259b0705` | `00f6af36049bd8567445fc5fa681ecf5e267c7be` |
| `6f826669779fc0df25487d7246f516cd154de7ef` | `465cfef9129a3851c52d537c3b4c9d1aad5b0ac9` |
| `d4dba3874ef92bef730498ff9ad443a05db95ae4` | `b0105879664e153b73f822a2db47615e83cd506e` |
| `ad54f7a4241c1b8281d14f3e091e4b80d9a64739` | `9280d472adfabd842836b5ad31aa4411e109819b` |
| `734c7b62f7bc85f4fbd602bfe5466cbcd7dfdadd` | `f38d56ecb653ea7e63caf6c00815b674076538c2` |
| `2593cac8868933bedf872628e51b9c8b47f42146` | `eec9b187931d8a99947fe755b7cc98cde4c68329` |
| `c4114b979b2dd229cc63ce88eb57a4ae6bcf738c` | `0ff3de5eeeb813b01db7743ae85ea4d7d965cdde` |
| `f6a75458d2069cd0bad1d346139ae2ab1e0e788b` | `8983e44f7666bc8063acab05c5f56ad9af9b617c` |
| `3254fc6283dc9f038e58a8b3e3945738e838fdf4` | `182a8e55e519ee198c374ba641910f616724d800` |
| `8dbdcca6dbc935def38cf6bc903ee4bf2caf9f8f` | `ce60ce5f78f8e6a8b1bf925a821caef6edc5fa92` |
| `6514915dc21e281808e698e542de769efbed0325` | `2a44693ca908550654cece91f175fb7d35240ce4` |
| `8f45bb97941991e489c8a72d7abfc045764fe86a` | `96f62e5bebd932aa9cb01c4608434ba080fb5af0` |
| `cecbb5116085831c7d54c35ddaa4d774377585e2` | `06bd0722cf123a68c92c31e4eff97852a5d9b90a` |
| `e1fc35b49da9b531970f794eb53d4ddb91537dea` | `68e42806296e1c0368cca1e626061714a63270d5` |

## Local-delta mapping and retirement

| Source | Integration | Retirement condition |
| --- | --- | --- |
| `00864775b5ae66e41de161fe16ab62446726e821` | `1b0a40724085e29b7bd710c9a861847789dc64da` | Upstream must pass canonical external projection, profile isolation, no-write, and native NULL-cwd preservation regressions. |
| `8db7dad97b4f5e65937110dce932a979c92df363` | `9302653fa93d1b871476da5c6eccca24991944d9` | Upstream must classify compressed lineages from the served tip, including NULL cwd/profile transitions. |
| `2c66360020d7025fedc465007427c2ad8a1ce69a` | `d838389e9642eef686077d991c7b86ea6a0e525a` | Upstream must make canonical cwd authoritative across open/import, selector, execution, regeneration, file-manager, and resume while preserving remote POSIX/profile semantics. |

When either upstream PR merges, rebuild a fresh integration stack from updated
upstream and retire only behavior demonstrably present there. Do not squash this
stack if exact upstream-to-fork traceability is required. Do not infer deployment
or runtime activation from this source integration.
