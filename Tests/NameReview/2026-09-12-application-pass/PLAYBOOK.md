# Naming pass playbook — how work is done

Read `STATE.json` first, then this file. Nothing else from disk is needed to start.
`archive/` holds the old per-wave journals and is **not** read during normal work.

## 1. The loop

A work unit is a **block** (one type cluster, one feature, or one module's worklist
remainder) — not a "wave" of three rows. One block is one review file and one commit.

```powershell
# 0. settings
$pass = 'D:\knx_analysis\application-name-pass01'
$repo = 'D:\git\dnSpy\Tests\NameReview\2026-09-12-application-pass'
$tool = 'D:\git\de4dotEx\tools\NameCandidates\bin\Release\net8.0\NameCandidates.dll'
$W    = 370                       # next 6.3 wave number from STATE.json
$work = "D:\knx_analysis\perf-now\w$W"

# 1. build the review rows (Module, Token, NewName, Reason) for this block.
#    Route builders live in D:\knx_analysis\perf-now (anchor-scan.py, sm-oracle.py,
#    literal-worklist.py, candidates.py ...). Today a small row-builder script writes
#    extended63-wave$W.review.json; the target is one parameterized builder
#    (build-rows.py --spec <rows.json> --wave $W). Do not copy a build-waveNNN.py per wave.
python D:\knx_analysis\perf-now\<row-builder>.py

# 2. one process runs update -> check -> both audits -> filter -> apply -> verify
dotnet $tool --wave "$pass\extended63-wave$W.review.json" "$pass\names63-staged-v$($W-1).xml" $work `
  --contract-references "$pass\contract-references63-v3.json" `
  --sdk-module Knx.Ets.Sdk.dll --sdk-module Knx.Ets.Sdk.AddIns.AddInViews.dll `
  --sdk-module Knx.Ets.Common.Types.dll --sdk-module Knx.Ets.Common.Resources.dll

# 3. checkpoint: copies artifacts, asserts the gates, updates STATE/progress
python "$pass\checkpoint-waveN.py" $W "<block status>" "extended63-wave$W.review.json" "<method-json>" $work

# 4. 6.4 restage (see §4), then:
python "$pass\checkpoint64-vN.py" 168 167 $W
```

`--wave` refuses to overwrite an existing output directory: delete the work directory
before re-running, never edit a map by hand.

## 2. Gates that must pass before a checkpoint

- `update.Success`, no `update.Errors`, and **no `Requested != Applied`** rows
  (a numeric suffix means the block is wrong — fix it and re-run).
- `check.Success`, no `check.Errors`.
- `audit.SdkVisibleRenamed == 0` and `audit.SdkReferencedTypesRenamed == 0`.
- Name-diff expectation: the number of added rows equals the review file's rows
  (removals and renames of previously accepted rows must be explicit).
- `--verify-applied` on the applied tree: all modules load.

`checkpoint-waveN.py` performs these assertions itself; if it throws, the block did not
land and STATE must not be updated.

## 3. Evidence routes (use in this order)

1. **6.4 released-name oracle** — a 6.3 compiler-generated stub joined to a readable 6.4
   owner by its framework-visible shape (`perf-now/sm-oracle.py`; worklists
   `sm-oracle-falcon.json`, `sm-oracle-hawk.json`). Strongest route; corroborate with the
   row's own literal before accepting.
2. **Contract family** — a virtual/interface member inherits the family's name
   (`--review-families`). One row can expand into many names.
3. **Domain-callee anchor** — the row's `Knx.*` callees name the operation
   (`perf-now/anchor-scan.py`); ignore framework-only callees.
4. **Literal / self-naming worklist** — strings and log formats inside the body
   (`perf-now/candidates-*.json`, `literal-worklist.py`).
5. **Structural fallback** — offsets, bitfields, formatters, tables (slow; only after the
   routes above are empty for that block).

Evidence must be recorded in the row's `Reason` (token, literal, callee or peer), so the
checkpoint is self-explaining without a journal.

## 4. 6.4 restage

Artifacts live in `D:\knx_analysis\perfprobe` and are consumed by `checkpoint64-vN.py`:

```
scan63to64-vN.json   # --reference-source-map <v63 map> <63 tree> <64 tree> <scan.json>
generated64-vN.xml   # --source-map <selected candidates> <64 tree> <source-map.xml>
names64-staged-vN.xml# --merge-map <generated map> <base 64 map> <new 64 map> <merge.json>
check64-vN.json      # --check-map <new 64 map> <check.json>
audit64-vN.json      # --public-api-audit <new 64 map> <audit.json> --sdk-module ...
vN-sdkfrozen.xml     # --bind-sdk-whitelist / --filter-map with sdk-name-whitelist64-v1.xml
```

Tree roots: `ETS6.3_api_preserved4` (reference) and `ETS6.4_api_preserved5` (target).
This route has no committed driver script — writing one parameterized
`stage64.py <version> <sourceWave63>` is a legitimate, bounded tooling correction (the
alternatives are re-typing six commands per wave, which is what produced the sprawl).

## 5. Tools worth knowing

| Command | Use |
|---|---|
| `--wave` / `--wave-batch` | whole pipeline for one block / several blocks in parallel |
| `--coverage` | per-module decided / unresolved / open counts (the backlog number) |
| `--review-families` | expand a virtual row into its contract family |
| `--inspect-methods <dll> <token...>` | one call that prints the row's body, literals and callees |
| `--dump-constants` | string/constant evidence per type |
| `--review-obfuscated`, `--suggest-accessors`, `--review-map` | remaining candidate inventory |
| `--apply-map`, `--verify-applied` | 6.3/6.4 binary apply + applied-tree gate (already inside `--wave`) |

## 6. Working rules (the ones that keep getting broken)

- **No per-wave journals.** Do not append narrative sections to a handoff document, do not
  restate commit hashes in prose, do not write a "wave report". History is `git log`; state
  is `STATE.json`; the reason for a row is the row's `Reason`.
- **One builder per block, not one script per wave.** `build-waveNNN.py` files are the
  current pattern; a parameterized builder that reads a row spec is the target. Keeping a
  copy per wave is not acceptable long term.
- **Commit once per block**, with the block name in the message. A commit is a checkpoint,
  not an endpoint.
- **Cheap checks only during naming.** No ETS export, rebuild, launch, or full-tree audit
  during the naming phase, and no repeated whole-tree scans after each block.
- **Do not stop while unblocked rows exist.** If a route is exhausted for a block, record
  it in `STATE.Backlog.ExhaustedRoutes` and take the next route or the next block.
- **`STATE.json` stays under 200 lines.** When it grows, delete detail — do not create a
  second state file.
- **Do not optimize the tools** unless a specific row cannot be consumed by them. A tool fix
  is followed immediately by naming work, not by a measurement round.

## 7. Resume after a context reset

1. Read `STATE.json`. 2. Confirm the current map SHA matches the file on disk (one
   `Get-FileHash`). 3. Open `STATE.NextItems` and continue at the first row whose route is
   not exhausted. Nothing else needs to be rediscovered.
