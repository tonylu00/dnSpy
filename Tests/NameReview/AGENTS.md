# Current ETS task routing (2026-10-25)

For the user-requested staged ETS6.3 migration task, follow
`D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/PREPARE_ETS63_MACOS_SOURCE.txt`.
That short goal references `D:/git/ets63-source/MIGRATION_WORKFLOW.txt` for the
complete instructions. First update the actual implementation repository to the
latest accepted live baseline, verify it and commit the refresh before migration;
comparison alone is insufficient. Preserve existing work and accepted inputs.
The saved workflow/Git setup is complete only as setup; migration is NOT STARTED.
The future chat must reconcile the baseline and recover editable UI resources,
implement .NET 10 native Avalonia and pass Windows build/startup/selected original
UI/data-roundtrip gates before macOS-specific implementation, then test the same
source/core workflows on actual macOS. An unavailable Mac remains a blocker.
Use `D:/codex-worktrees/ets-disposition-workflow/dnSpy` for tooling, the shared
helpers beside the prompt, and `D:/git/ets63-source` as the migration
implementation/source Git workspace. Its existing older snapshot must be
reconciled with current accepted inputs before use; keep the accepted tree unchanged.
Do not automatically resume the historical ETS63/64 every-symbol audit or Source09
sequence. Preserve historical STATE/GOAL/cursor/pins and unaccepted Source07/08/09.
`D:/knx_analysis/STATE.json` supplies accepted input bindings; compact migration
progress belongs in `D:/knx_analysis/ets63-macos-source-preparation`. The saved
prompt defines completion and deferred scope. All storage/preservation rules apply.

# ETS workflow disk budget

For the ETS naming/readability workflow, all heavy exports, builds, runtime copies
and large proof generation must use
`D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/storage_guard.py run` with an explicit
`--budget-gib` and a named `--output` directly under
`D:/knx_analysis/workflow-scratch`. Pass the same output to the producer, including
its intermediate/temp paths. Do not detach the guarded command or bypass it.
Run the guard's `status` command before heavy work; retain 10 GiB on C: and 15 GiB
on D: in addition to the estimated peak allocation. See ResumeWorkflow/README.md.

Do not create bulk artifacts in C:/Users/tony/.codex/worktrees/ets-disposition-workflow.
That historical path is now only a junction. The preserved files and registered
checkout are at D:/codex-worktrees/ets-disposition-workflow and its dnSpy child.
Use the D: checkout directly, keep the junction for pinned historical references,
and never recreate a physical C: development tree there. Migration evidence is in
D:/knx_analysis/worktree-migration-2026-10-19.
Reuse valid builds and tools. Batch full validations. Prepare a runtime copy only
when it can be tested, not for every map checkpoint. Avoid copying full test inputs
for every case: process one temporary case at a time and retain compact receipts,
seed pins, mutation recipes and failed-case diagnostics. Keep at most current and
previous unreferenced scratch generations; review cleanup before creating a third.
Never infer that a pinned source/export/receipt is disposable from its age.

Cleanup must use an explicitly reviewed file manifest and the user's current
authorization. The 2026-10-19 follow-up authorized actual cleanup; its file lists,
preserved evidence pins and deletion logs are in
`D:/knx_analysis/disk-recovery-2026-10-19`. Do not reuse those manifests for newly
generated files or treat an old runtime receipt as proof its cleaned payload exists.
For retained, immutable generated reports, prefer verified lossless filesystem
compression over another copy. Check SHA256 before and after compression. Measure
storage recovery using actual drive free space; logical sizes double-count hard
links and do not reflect compression. Inspect all artifact roots, including the
C: worktree's sibling directories, when budgeting the workflow's total storage.
Do not alter original files, current builds, checkpoints or historical producer
pins. A storage block is not permission to mark the full readability goal complete.

The 2026-10-21 cleanup audit, frozen manifests and final verification are in
`D:/knx_analysis/disk-recovery-2026-10-21`. The guard bounds individual runs;
it does not retire accumulated generations. Review retained storage across all
artifact roots before a heavy run. Reuse accepted outputs and retire an explicitly
reviewed superseded unreferenced generation, within existing cleanup authorization,
before creating a third. Preserve uncertain dependencies and avoid another full
copy until retention is resolved. Current acceptance dependencies, active recovery
backups and protected test fixtures remain protected. Retired historical payloads
must be regenerated only when needed and revalidated before use; do not recreate
them merely to make an old directory appear complete or rewrite its evidence pins.

The 2026-10-24 file-count cleanup audit is in
`D:/knx_analysis/disk-recovery-2026-10-24`. Verified old source/export payloads are
stored in `D:/knx_analysis/cold-archives-2026-10-24`; their old directories contain
`ARCHIVED_PAYLOAD.txt` with an exact manifest and restore command. Preserve these
archives and manifests. Restore only a required generation into explicitly
budgeted storage, never every archive or an entire old validation cohort.
Keep `workflow-scratch/ets64-capture-complete-runtime-session01` as the fixed
retained duplicate-data baseline for both the October 21 and October 24 cleanup
manifests, alongside the current accepted runtimes and active recovery backups.
Before another full export/runtime generation, inspect retained generation count
and loose file/directory counts as well as bytes; the byte guard alone does not
bound accumulated NTFS entries. Prefer one reused working generation and compact
hash-bound receipts. Do not recreate retired payloads to satisfy an old receipt.

Historical proof source snapshots have been consolidated under
`D:/knx_analysis/cold-proof-archives-2026-10-24`, with the reviewed selection and
verification in `D:/knx_analysis/historical-proof-archive-2026-10-24`. Treat each
root's `ARCHIVED_PAYLOAD.txt` and archive retirement receipt as the availability
record. Historical checkpoint references remain unchanged; they do not imply
that old source files are still loose. Restore the indicated verified archive
only when a specific historical replay/rebuild requires it. Do not automatically
restore every ancestor snapshot. DLLs, PDBs, project files, checkpoints, maps and
receipts remain loose in this source-only consolidation. Current accepted source
trees and active producer inputs are excluded and rechecked on authority changes.

The user clarified on 2026-10-24: "DO NOT simply archive files" and "Just REMOVE
unused source and build file." For freshly reviewed obsolete generated payloads,
delete the unused files directly and retain a compact deletion record; do not
create another archive as a substitute for cleanup. This does not permit deleting
originals, current builds, active inputs, checkpoints or pre-existing archives.
The latest review and verification are in
`D:/knx_analysis/remaining-cleanup-2026-10-24` and
`D:/knx_analysis/remaining-scratch-cleanup-2026-10-24`. Their
`RETIRED_UNUSED_PAYLOAD.txt` markers supersede older availability statements for
the exact retired files, including obsolete DLLs/PDBs/resources. ZIP copies made
by that cleanup pass were removed; associated manifests/receipts are audit
metadata only. Do not restore or regenerate these obsolete trees merely because
an old receipt mentions them. Recheck current state, producer dependencies,
process ownership and exact paths before any new retirement; keep the existing
disk reserves, aggregate generation limits and D: worktree requirements.

Additional direct retirement of unused worktree-sibling exports/tool outputs and
old analysis/performance outputs is recorded in
`D:/knx_analysis/disk-retirement-2026-10-24`. Its exact deletion manifests and
`RETIRED_UNUSED_PAYLOAD.txt` markers supersede old loose-payload availability.
No new payload archives were created. Do not recreate retired generations during
resumption. The Git checkout, current provider/source bindings, maps, checkpoints,
original inputs and active Source07 scratch were preserved; the worktree remains
an operational input even when its parent directory timestamp is old.
