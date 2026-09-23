# Goal: make the ETS application readable — merge, name, then verify

Read `D:\knx_analysis\STATE.json` first, then `POLICY.md` and `PLAYBOOK.md`. Those three
files are the complete state, policy and pipeline. Do not read `archive/` and do not write
journals anywhere.

## Objective

The measure is **how readable the decompiled ETS application is**, not how many symbols were
renamed. In priority order:

1. **Compiler-generated code is merged into its owners** — lambdas inline, `async`/`await`
   bodies, state machines and display classes no longer appear as separate obfuscated types.
2. **Semantics-bearing members are named from evidence** — method, type, field, parameter.
3. **Evidence-free private state is recorded unresolved with a reason** — never invented,
   never suffixed, never counted as progress.

## Where the work stands (2026-09-23)

- **Merge: done at the decompiler level.** dnSpy/ILSpy submodule
  `Extensions/ILSpy.Decompiler/ICSharpCode.Decompiler` @ `codex/local-commits`
  `00db96bac` (async `MoveNext` found through its MethodImpl override) and `fd5b322cc`
  (renamed closures/lambdas recognised structurally instead of by name).
  Verified on the 6.3 tree: HawkNET 389 async / 1,190 await / 326 inline lambdas / 0 raw
  stubs / 0 display classes; Falcon 556 / 1,125 / 461; ObjectModel 12 / 9 / 3,340;
  CloudKit 29; DevKit 16. Normal .NET 9 assemblies are unchanged.
- **8 raw stubs remain in Falcon** (`Class1353::a`, `Class1360` ×7) — cause not yet pinned;
  see `STATE.Backlog.CompilerGeneratedMerge.Status.FalconLeftover8`.
- **Naming:** map 6.3 = `names63-staged-v380.xml` (16,694 renamed rows), 6.4 = v178.
  Backlog is 28,105 rows (20,492 fields, 5,778 methods, 2,333 types) whose evidence routes
  are closed with measured numbers, plus one open route (the 6.4 readable-surface anchor
  fixpoint).
- **Phase 4 has never run.** `AppliedToSource` is `false`; the ETS binaries are untouched.

## Task order for this goal

1. **Readability baseline:** run the patched decompiler over the whole 6.3 tree (528
   assemblies) and the 6.4 tree and record per module: files, inline lambdas, async
   methods, awaits, raw builder stubs, display-class declarations, decompiler errors.
   Write it into `STATE.Readability` (per module + totals).
2. **Close the Falcon 8:** instrument or diff `MicrosoftAsyncDecompiler.MatchTaskCreationPattern`
   for the two cases listed in STATE; fix the matcher or record why it cannot be fixed.
3. **Run the open naming route** (6.4 readable-surface anchor fixpoint) and record the
   measured yield per module before accepting or rejecting it.
4. **Settle the evidence-free remainder** per `POLICY.md`: record those rows as unresolved
   with the `no-evidence-in-scope` reason so `--coverage` counts them as decided.
5. **Phase 4:** freeze the map, export the source with `dnSpy.Console --source-name-map <map>
   --public-sign` (the same patched engine, so the export inherits the merge), rebuild,
   overlay `Stage-RecompiledTree`, run the audit battery, and verify against unchanged
   third-party ETS Apps.

## Turn contract

A checkpoint or commit does **not** end a turn.

- Keep working until the current block is exhausted (every row named or recorded as
  blocked), every remaining row carries a hard-blocker code from `STATE.HardBlockers`, or you
  hit a real context limit.
- Floor per turn: one complete block and at least 100 definitions, unless fewer than 100
  unblocked rows remain in scope.
- If you stop early, write the remaining tokens and the exact reason into `STATE.NextItems` —
  never into prose.
- "Nothing to do this turn" is not a valid turn: take the next route, or the next item in the
  task order above.
- Missing evidence is not a blocker; it is an unresolved row with a recorded reason.

## Working rules

- Bounded state: `STATE.json` stays under 200 lines. History is git; no per-block journals,
  no wave reports, no commit-hash prose.
- One block = one review file, one `--wave` run, one checkpoint, one commit.
- Tool changes only when a row or block cannot be consumed, and the next action after a tool
  fix is always the work it unblocked. Decompiler fixes live in the submodule on
  `codex/local-commits` and must be verified with a before/after decompile or map measurement.
- Never modify ETS binaries with scripts. No ETS exports, rebuilds, audits or launches outside
  Phase 4.
- Preserve unrelated work: the dnSpy repo carries an untracked `ILSpy/` folder and a coupled
  `D:\git\de4dotEx` checkout — leave both alone.
- Report per turn: block name, definitions named, readability delta (lambdas / async / raw
  stubs), remaining unblocked count. Nothing else.

## Definition of done

- **Merge:** zero raw builder stubs and zero display-class declarations across the in-scope
  tree, or every leftover recorded with its cause.
- **Naming:** every in-scope definition is exactly one of named | already readable |
  SDK/protected | compiler-generated (merged) | unresolved-no-evidence with a reason.
- **Phase 4:** completed, with compatibility verified against the unchanged third-party ETS
  Apps.

Until Phase 4 has run, do not claim the application is readable, applied or compatible.
