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

# ETS storage rules

The preserved worktree and its sibling evidence directories now live at
`D:/codex-worktrees/ets-disposition-workflow`. Use the checkout at
`D:/codex-worktrees/ets-disposition-workflow/dnSpy` for work. The former
`C:/Users/tony/.codex/worktrees/ets-disposition-workflow` path is a compatibility
junction to D:, with no project data stored on C:. Keep that junction so historical
source/PDB and checkpoint references continue to resolve. Do not replace it with a
physical C: directory, rewrite immutable evidence paths, or create new bulk output
through the C: alias. All new heavy output belongs in the guarded D: scratch area.

The Git checkout and historical evidence are protected. The move's full SHA256
manifest, Git/state checks and C: holding-copy removal receipt are in
`D:/knx_analysis/worktree-migration-2026-10-19`. Future cleanup must review physical
D: targets and validate containment; never recursively delete through the C: alias.

Before heavy work, run:

`python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/storage_guard.py status`

Launch every export, build, runtime preparation and large proof/test generation
through the checked-in launcher. Use one named block directly under
`D:/knx_analysis/workflow-scratch`, and pass that same output directory to the
actual producer. For example:

`python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/storage_guard.py run --output D:/knx_analysis/workflow-scratch/<block> --budget-gib 4 -- python <producer.py> --output D:/knx_analysis/workflow-scratch/<block> <other-arguments>`

Use a measured peak allocation estimate (all copies, intermediates and reports),
not merely input size. The guard reserves 10 GiB on C: and 15 GiB on D:, checks
the peak budget before starting, monitors the output and disks during execution,
and stops only its own command tree on a breach. It does not delete failed work.
Do not bypass it with detached commands, background jobs, separate copy/build
commands, a larger arbitrary budget, or output/temp paths outside the declared
block. For dotnet builds explicitly route OutputPath and BaseIntermediateOutputPath
inside that block; preserve references needed by the existing build.

Reuse hash-valid accepted builds and tool runtimes. Consolidate related changes
before whole-cohort builds. Keep at most current and previous unreferenced
scratch generations; propose verified cleanup before a third. Accepted evidence
dependencies are protected regardless of age. Do not copy complete runtime
trees until a runtime test can actually run. Prepare the latest accepted source
once, not another runtime for each naming checkpoint.

Regression cases must avoid retaining a complete JSON/native/source input copy
for every case. Process one case at a time in owned temporary storage, preserving
the seed pins, mutation recipe, result and diagnostic failures. Keep reports
bounded; do not embed prior ledgers/cursors recursively. Do not use hard links
for files that any exporter, patcher or build might modify.

Manual cleanup is reviewed in D:/knx_analysis/disk-cleanup-2026-10-18. Its deletion
log identifies superseded runtime copies that must be regenerated before reuse;
an old receipt does not make a missing payload valid. Preserve all originals,
current builds, checkpoints, sources, maps, reports, Git data and unrelated work.
Never use blanket git clean, delete the worktree, or change historical evidence
pins to make cleanup pass. Checkpoint or storage maintenance is not full-goal
completion. Continue independent read-only/review work when a heavy run is blocked.

The user authorized additional cleanup on 2026-10-19. Its reviewed file lists,
dependency audit, deletion logs and hash-preserving compression logs are in
`D:/knx_analysis/disk-recovery-2026-10-19`. Cleaned historical runtime/staging
payloads must be regenerated before reuse; retain their maps and receipts. Do not
copy them back merely to make an old directory look complete. For large immutable
generated reports, use lossless filesystem compression with SHA256 checked before
and after. Budget new reports from logical peak size, and measure recovered space
from actual volume free space, without summing overlapping worker measurements.

The 2026-10-21 cleanup audit is in
`D:/knx_analysis/disk-recovery-2026-10-21`. Consult its final verification and exact
manifests before reusing historical build or runtime payloads. The per-run storage
guard does not enforce aggregate retention: count retained generations across all
artifact roots before another heavy run. Reuse valid accepted output; before a
third unreferenced generation, retire an explicitly reviewed superseded generation
within existing cleanup authorization and record the deletion. If its dependencies
or ownership are uncertain, preserve it and avoid creating another full copy.
Keep current acceptance dependencies, the active recovery backup and protected
test fixtures regardless of age. Do not recreate retired payloads solely because
an old receipt mentions them, or change immutable evidence pins to hide retirement.

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
