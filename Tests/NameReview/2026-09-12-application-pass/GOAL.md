# Goal: finish the ETS 6.3 application-wide naming pass

Read `D:\knx_analysis\STATE.json` first, then `D:\knx_analysis\POLICY.md` and
`D:\knx_analysis\PLAYBOOK.md`. Those three files are the complete state and rules.
Do not read the archived journals in `D:\knx_analysis\archive\` and do not write to them.

## Mission

Give ETS 6.3 (and its 6.4 counterpart) one readable, consistently named implementation
across the executable and every coupled assembly, while every existing precompiled
third-party ETS App keeps working. Names must describe real behaviour and be consistent
across related components. Tool work in dnSpy/de4dotEx happens only when a specific row
cannot be consumed by the tool, and the next action after a tool fix is always more naming.

Readability, not rename counts, is the measure. In particular the compiler-generated members
are **merged** into their owners in the reader's view by restoring the compiler's own entry
points — state machine `MoveNext`, `<Owner>d__N` state machine types, `<>c`/`<>c__DisplayClass`
closures and `<Owner>b__N` lambdas (`STATE.Backlog.CompilerGeneratedMerge`). Without that, async
methods render as raw `AsyncTaskMethodBuilder.Start<T>(ref struct)` stubs and lambdas never
inline, which is exactly the barrier this pass exists to remove.

## Turn contract

This is the part that keeps being missed. A committed checkpoint does **not** end a turn.

1. Keep working until one of these is true:
   - the current block is exhausted (every row named or recorded as hard-blocked), or
   - every remaining row in the block carries a hard-blocker code from
     `STATE.HardBlockers`, or
   - you hit a real context limit.
2. Floor per turn: complete at least one block and name at least 100 definitions, unless
   fewer than 100 unblocked rows remain in the whole scope.
3. If you stop before the block is exhausted, write the exact remaining tokens and the
   exact reason into `STATE.NextItems` — never into prose.
4. "No wave this turn" is not a valid turn. When a route is exhausted, record it in
   `STATE.Backlog.ExhaustedRoutes` and immediately take the next route or the next block.
5. Missing evidence is not a blocker: switch route, take the next row, or mark the row
   unresolved with its `UnresolvedReason`. Only the hard-blocker codes stop a row.

## How work is done

- Follow `PLAYBOOK.md`: one block = one review file, one `--wave` run, one checkpoint, one
  commit. The pipeline is already a single tool command that runs update, check, audits,
  apply and the applied-tree gate in one process.
- Cheap checks only while naming. Do not export ETS, rebuild, launch ETS, or run whole-tree
  audits during the naming phase; those belong to Phase 4.
- A mapping row names a definition once and carries its evidence in `Reason`. The tool
  propagates references. Never enumerate reference tokens or call sites by hand.
- Keep `STATE.json` current and under 200 lines: map paths and hashes, next wave numbers,
  counters, the backlog worklists, the next items. Git history is the log — do not write
  per-wave journals, wave reports, or commit-hash prose anywhere.
- Commit at the end of each block with the block name. Do not commit per sub-step, and do
  not stop after committing.

## Compatibility (non-negotiable)

- The SDK whitelist in `STATE.Compatibility` is binding, together with `POLICY.md`. SDK
  modules, whitelisted symbols, their contract families, and anything reachable through
  reflection/serialization or a non-resolvable string contract are never renamed.
- If compatibility and readability disagree, keep the existing name.
- Third-party Apps cannot be rebuilt; verify against the unchanged binaries in Phase 4.
  Never accept a numeric collision suffix (`Foo2`) to get past a gate.

## Reporting

One short report per turn: the block name, definitions named, and the remaining unblocked
count per module from `--coverage`. No per-row lists, no restated git log, no narrative
about the process.

## Definition of done

The pass is done when every in-scope definition sits in exactly one terminal category —
named, already readable, SDK/protected, compiler-generated, or **unresolved with a recorded
reason** (`STATE.Closure`) — and Phase 4 has run: frozen map, source export via dnSpy
`--source-name-map` + `--public-sign`, rebuild, `Stage-RecompiledTree` overlay, audit battery,
and compatibility checked against unchanged third-party ETS Apps.

`NotYetNamedRows` is a progress metric, not the goal. A row may be recorded unresolved once
its evidence routes are exhausted *with a measured number*, exactly as the mission allows:
"Leave uncertain decisions explicitly unresolved, with a brief explanation of what evidence is
missing." What is never acceptable is an unmeasured route, a placeholder name, or a numeric
suffix. Until Phase 4, do not claim the application is readable, applied, or compatible —
`AppliedToSource` is still `false` and the ETS binaries are unchanged.

Before closing, run the one route that is still open (`STATE.Backlog.Routes`, last entry): the
6.4 readable-surface anchor fixpoint. Reporting a blocked goal while an unmeasured route with
bulk potential remains is premature.

Priority order for every decision: preserve third-party compatibility → advance
evidence-based naming across the whole tree → make only the tool corrections that unblock a
row → run the consolidated Phase-4 verification.
