# ETS 6.3 / 6.4 naming pass — checkpoint sink

This directory holds the machine-readable records. It is not the state document.

Read first:

- `D:\knx_analysis\STATE.json` — current maps, hashes, coverage, backlog, next items
- `D:\knx_analysis\POLICY.md` — compatibility policy
- `D:\knx_analysis\PLAYBOOK.md` — pipeline, gates, evidence routes, working rules

What lives here:

- `progress.json` — tool-facing record of the current map paths and checkpoint
- `reviewed63.json` — cumulative behavioural review ledger (the row-level evidence)
- `checkpoint-waveNNN.json`, `checkpoint64-vN.json` — accepted per-block records
- `map-update63.json`, `devkit*63-review-check.json` — last update/check reports
- `archive/` — the former handoff and README journals (history; do not read to resume)

Rules:

- One block = one evidence-backed review and inexpensive map/reference checks.
  Commit validated milestones; defer full `--wave` audits/application and ETS
  export/build until application-wide mapping freezes.
- No per-block narrative, no commit-hash prose, no wave reports. `git log` is the log.
- `AppliedToSource` stays `false` until the consolidated Phase 4 export/build/verification.
  Metadata apply and `--verify-applied` do not prove source rebuilding or ETS runtime behaviour.
