# ETS6.3 functional migration workflow (2026-11-02)

The short goal is PREPARE_ETS63_MACOS_SOURCE.txt. Its full milestone contract is
D:/git/ets63-source/MIGRATION_WORKFLOW.txt. The source refresh already passed in
commit 72ed4380; resume from the live MIGRATION_CHECKPOINT.json in
D:/knx_analysis/ets63-macos-source-preparation and preserve ongoing work.

The bounded parameter edit/save/normal-close/fresh-process-reopen flow passed.
Reuse its evidence and current connection/download/catalog/application-update work.
The current PC goal ends at PC_HANDOFF_READY in the handoff contract. Fix the
project-open modal and Download clipping; source-build Falcon/retained backends
and verify their selected outputs in a bounded Windows baseline. Old naming/
NuGet skips are not portability acceptance. Deliver portable source/fixture/
dependencies and MACOS_CONTINUATION.txt, then complete this PC goal and STOP.
Keep unfinished diagnostics/product/platform work for the Mac continuation;
full M8/M9-M11 and actual Mac execution are not required before leaving. Remove
working Token/RVA comments after redirecting token-based preparers; preserve required
semantic restoration support. Retain all named device/product, tunneling/routing/
USB and security gates without another naming/export chain. Preserve master data, the online
product catalog and required APIs/authentication/update/download/import/cache.
Master-data and catalog startup updates each have a saved switch, OFF by default
when unset. Use cached data without update traffic or network delays when disabled.
Preserve manual updates/online catalog actions; enabled updates must not block
startup and must respect metered/cellular preferences.
Remove application licensing/activation, telemetry and unrelated cloud integrations;
keep shared dependencies required by retained functions, local data/security,
KNX Secure and native MCP. The workflow's product-data clarification overrides
earlier blanket local-only/cloud-removal instructions.

The toolbar/connection-dialog/Download correction is required within the current
connection slice, not deferred shell polish. Restore original glyphs, groups and
responsive labels, the compact connection popup with dedicated manager dialogs,
and the Download split-button/menu (main action Partial). Use consumed Python
conversion and paired screenshot/interaction checks. The bounded findings and
existing capture paths are in ETS63_TOOLBAR_GAP_REVIEW_2026-10-30.txt; the detailed
workflow is authoritative. These saved requirements do not claim a runtime fix.

The 2026-10-31 connection/detail correction and Mac development handoff are in
D:/git/ets63-source/CONNECTION_AND_MACOS_HANDOFF.txt. Require usable selected-row
manager/detail layouts, applicable APDU/SN/IP/KNX fields and real Test behavior.
The user has ETS in Parallels on the Mac for future reference comparisons.
Version the verified "test" project P-01C0 as the specified Git fixture; preserve
protection and keep mutable stores/actual credentials outside Git. Restore the
KNX security sidebar's certificate/FDSK, project protection, confirmation and
applicable IP-security workflows. After PC_HANDOFF_READY, continue remaining work
and native Mac validation in the next goal, independent of VM/ETS runtime services.
Preserve existing work, references and host-appropriate disk safeguards.

The user authorizes safe unused generated-build retirement on 2026-10-29. Apply
the full workflow's Build retirement protocol with fresh exact-path dependency
and ownership checks. Retain current builds/providers, original/source data and
evidence; retire proven obsolete payloads without new archives or arbitrary size
caps. Legacy generic preservation labels are not permanent dependencies. The
active owner must serialize cleanup and reconcile the live retention ledger.

Use .NET 10/native Avalonia and preserve original ETS UI layout and functions.
Original ETS may be opened for reference screenshots; use repeatable Python XAML
conversion with explicit adapters instead of a redesigned handwritten shell.
M1-M11 remain the overall roadmap: storage-policy correction, references, conversion, device management,
parameters, connection manager, real download, integrated Windows acceptance,
then actual macOS, Android tablet and iPadOS validation.

Device/KNX-IP/download exclusions and tablet-preparation-only completion in older
instructions are superseded. Artifact sizes are not optimization targets:
forecasts may grow with measured work; keep actual C: 10 GiB / D: 15 GiB reserves,
peak headroom, aggregate retention and ownership protection. Remove arbitrary
source/preparation/publication caps. Do not minify useful code/comments/diagnostics
or bypass the storage guard. M1 describes the required budget-policy correction.

The review and framework comparison are in ETS63_MIGRATION_REVIEW_2026-10-28.txt.
START.json and migration-setup snapshots retain historical starting evidence;
they do not supply current progress or override the revised contract. No active
checkpoint, old naming STATE/GOAL/pins, producer or unrelated work is to be reset.

The storage history below explains earlier safeguards/implementation. Where it
describes fixed artifact quotas, the 2026-10-28 policy above takes precedence;
actual free-space, path, process and accepted-input protections remain in force.

Storage prevention (2026-10-18): run `python storage_guard.py status` before heavy
work. `brief` also reports free space and reserve readiness. All new bulk output
belongs under `D:/knx_analysis/workflow-scratch/<block>`, outside the C: worktree.
Launch the actual producer through:

```powershell
python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/storage_guard.py run --output D:/knx_analysis/workflow-scratch/<block> --budget-gib 4 -- python <producer.py> --output D:/knx_analysis/workflow-scratch/<block> <arguments>
```

The budget is the peak total logical block size, including copies, reports,
intermediates and logs; choose it from measured inputs. Before launching, the guard
requires that budget plus 15 GiB free on D: and 10 GiB free on C:. It periodically
checks disk reserves and block size, and stops only its owned command tree if
either is exceeded. A single-owner lock prevents competing guarded heavy jobs.
The output must be fresh, or explicitly `--resume` the same owned block. Completed
and failed work is retained for inspection, with a small receipt in `.storage`.
Inspect the PID in a stale lock before manually removing that lock. This is a
sampled process guard, not a filesystem quota; it cannot control unrelated or
detached writers. All output/temp/intermediate paths must stay inside the declared
block. Do not raise a budget just to bypass a storage failure.

Reuse existing tool builds and unchanged hash-bound receipts. Batch full exports
and validations. Prepare only the latest runtime when a test can actually run.
Keep at most current and previous unreferenced scratch generations and review
cleanup before allocating another. Keep compact test receipts and process copied
test input one case at a time instead of retaining every full input. Never remove
accepted dependencies just because they are old or overwrite pinned producers to
retrofit a guard: the external launcher preserves their historical hashes.

Manual cleanup: `Clear-VerifiedEtsTemp.ps1` defaults to metadata/evidence checks
and CSV preview. `-VerifyContent` adds the full C: copy/counterpart hash scan;
`-Apply` always performs it, before deleting anything. Hashing many cold copies
can take substantially longer than a metadata preview.
The exact reviewed list and evidence pins are in
`D:/knx_analysis/disk-cleanup-2026-10-18`. Use PowerShell 7 (`pwsh`). `-Apply`
deletes only the individually listed DLL/EXE copies; `-Drive C` or `-Drive D`
limits the selection. It refuses changed state/evidence/files, linked paths and
active workflow producers. Pause the owning task before applying. Historical
runtime preparations cleaned this way must be regenerated before reuse; original
trees, source/build/stage outputs, maps, checkpoints and native overlays remain.
Logical bytes are not physical recovery estimates because of compression and
hard links. The apply log reports the observed free-space change.

The user authorized a broader cleanup on 2026-10-19, recorded separately in
`D:/knx_analysis/disk-recovery-2026-10-19`. Consult its reviewed manifests and
deletion logs before trying to reuse historical test or staging payloads. Keep
their seed/map/provenance receipts; regenerate disposable payloads only when a
specific test needs them, inside a guarded scratch block. Retained immutable
generated reports can use lossless Windows filesystem compression, checking their
SHA256 before and after; do not create a second archive copy. Compression saves
allocated space but does not reduce the producer's peak logical budget. Audit all
output locations, including siblings of the C: checkout. Report actual before/after
drive free space, not summed logical directory sizes or overlapping worker deltas.

Physical relocation (2026-10-19): the retained worktree and all sibling artifacts
were copied and SHA256-verified at `D:/codex-worktrees/ets-disposition-workflow`.
The registered Git checkout is its `dnSpy` child. The former C: root is a junction
to D: so existing source/PDB/checkpoint paths retain their meanings and hashes.
Use the D: checkout for work; never replace the compatibility junction with a
physical C: directory or generate bulk output through the alias. New heavy output
still belongs under the guarded D: scratch root. Migration and holding-copy removal
receipts are in `D:/knx_analysis/worktree-migration-2026-10-19`.

Start a new chat or resume after compaction with:

```powershell
python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/resume_naming.py brief --state D:/knx_analysis/STATE.json
```

This reads the current state, bound map, disposition manifest, ledger hash,
owner queue and current cursor. It prints current bindings, separate naming and
reconstruction counters, fixed source/private-metadata progress, running work,
the actual next command and the overall-versus-stage completion flags. Historical
cursor sections and predecessor cursors are not printed or followed. With a current
cursor, owner previews are opt-in, so resuming does not select a competing block.
It never imports full proof validators or modifies shared state. For the staged
migration, read the saved prompt and START.json, using POLICY/GOAL/PLAYBOOK only
for applicable preservation and evidence rules; their historical objectives do
not replace the migration scope. For a historical naming task, read POLICY and
GOAL once per new chat and consult only a relevant PLAYBOOK section as needed.
After compaction, resume the current block rather than rereading the history.

`bindings-consistent` is a navigation result, **not** a validation certificate.
Existing native map/checkpoint and export gates still apply before writes.
A map/ledger ahead of the published disposition manifest is reported as
`incomplete-or-stale`, without selecting owners or repairing shared state.
Preserve the active writer; re-read after its checkpoint. Output uses the
manifest's counters so it does not mix versions during partial publication.

Use `--work semantic`, `projected-values`, `reconstruction`, or
`generated-dispositions` and `--limit 1` through `10` for bounded previews.
Continue an existing prepared next block before selecting another. The preview
is not a reason to abandon an in-progress block or a fixed quota for a turn.

Retrieve a needed cursor section without dumping the complete checkpoint:

```powershell
python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/resume_naming.py section --key StageProgress
```

`--key` accepts a dot-separated path, including a specific prepared owner or its
child field. Output over 6,000 characters is refused instead of silently truncated;
choose a smaller field. The explicit maximum is 12,000 characters. A section is
navigation data, not permission to execute stale commands.

Save a small fixed baseline and show subsequent progress:

```powershell
python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/resume_naming.py snapshot --output <new-baseline.json>
python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/resume_naming.py brief --since <new-baseline.json>
```

Snapshots never overwrite an existing file. Source/private-cohort deltas require
the same pinned cohort and denominator. Naming/reconstruction counter changes are
reported separately; use `compare` for exact queue identity changes. Neither a
snapshot nor a brief proves source, runtime, or overall completion. Missing data
stays unknown. Inconsistent publication/counters suppress executable next commands.

The 2026-10-15 investigation found a live overall goal with repeated automatic
turns, not another completed goal. Its cursor had grown to about 83 KB while the
old brief omitted 123 recorded private-finding closures and seven source roots.
Two recent owner blocks rebuilt all 109 projects and replayed disposition evidence
to close four and two findings. Keep required checks, but group related owners and
measure shared validation cost. Use focused checks during preparation; perform
full required validation before publishing accepted changes at the appropriate
integration boundary. Do not rerun unchanged receipts just to finish a turn.

Continue after a successful checkpoint while useful authorized work remains.
Checkpoint frequency and turn length are not completion criteria. A running build
or another active writer must be reconciled before a new chat takes ownership.
Report concrete source/name/disposition changes and fixed-cohort deltas; commits,
test-case counts, prepared work and source acceptance are separate measures.

Compare two published manifests when the backlog appears to grow:

```powershell
python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/resume_naming.py compare --before <old-manifest.json> --after <new-manifest.json>
```

For each work category this reports the fixed original pending cohort, how many
of that cohort remain queued, how many left, and added-or-reopened entries. A
definition is keyed by physical path/SHA/MVID/assembly identity/token; captured
values also retain their source owner and projection. Repeated owner references
do not duplicate a definition. Categories overlap and must not be summed.

Leaving a queue does not prove a rename or reconstruction. New queue entries may
be newly measured scope or reopened work; this tool does not fabricate that
distinction. Changed physical identities or source baselines suppress cohort
claims. Legacy captured-value records without complete source-root/binding identity
also suppress that category's cohort claims. Compare exact disposition history when the cause matters. This helper
does not make the old source baseline evidence apply to a newer naming map.

The 2026-10-11 diagnosis found that discovery had expanded from the lexical
candidate set to the complete generated-artifact inventory. Raw lexical names,
generated reconstruction proofs and surviving captured values are distinct
queues. Report each against its own baseline, and keep new discovery visible
separately. Preserve compatibility proof obligations without repeatedly expanding
the current naming milestone or inventing aliases to reduce a counter.

For an efficient continuation: bind one owner/call-chain block, save its exact
input hashes, reviewed/pending owners, next command and missing evidence in one
small block cursor, and resume that cursor after compaction. Commit a complete
block and proceed to the next supported block. Avoid per-wave journal growth.
Keep strict checks at mutation/export boundaries; do not weaken their evidence.

The shared STATE/PLAYBOOK contents remain unchanged. The retained worktree's
physical location is now D:, with its historical C: paths preserved by the junction.
The staged migration entry point is the saved PREPARE_ETS63_MACOS_SOURCE.txt
prompt; the historical navigation helpers above do not choose its next stage.

Run focused tests:

```powershell
python -m unittest discover -s D:/git/dnSpy/Tests/NameReview/ResumeWorkflow -p test_resume_naming.py -v
```
