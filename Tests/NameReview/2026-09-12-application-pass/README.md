# Application-wide naming pass — in progress

The objective is readable call chains throughout ETS and its coupled components.
The source trees have **not** been renamed or rebuilt by this pass. Decisions are
being accumulated before one consolidated application/verification phase. The
prior `CheckProjectData` fix is already in the 6.3 baseline.

The graph covers 111 managed source projects plus four retained binary dependencies
in 6.3, and 178 plus four in 6.4. Those are physical coverage counts, not readable
methods or completed work. Graphs and query databases live in
`D:/knx_analysis/application-name-pass01` (`graph63-v2`, `graph64-v2`,
`graph63.sqlite`, `graph64.sqlite`). Graph-local IDs always resolve through their
own manifest; same-name compatibility assemblies stay distinct.

Current reviewed chains include:

- ETS product/template checks → manufacturer cache language/version checks →
  cache rebuild creation, live reference selection and weak/strong retention.
- Template classification → CvNext namespace helpers and XML attribute names →
  reading the extracted project's `Name` attribute.
- Parent-process performance counters and the internet availability sampling
  loop, with the shared terminology carried into the inspected 6.4 main executable.

For example, `RequiresCacheRebuild` describes both language-pair and cache-format
checks, including the distinction between optional and required missing caches.
Three otherwise identical predicates receive separate names from their actual
callers: communication-object, parameter and calculated-parameter cache checks.
The ledger records methods, types, fields, formal parameters and proposed local
bindings together. Existing meaningful method names are retained.

`decisions63.json` and `decisions64.json` are behavioral reviews, not proof that
the application is readable. Physical copies are listed within a shared decision
only after matching the reviewed source/signature. `stage.py` and `stage64.py`
are exact-snapshot recipes with input hash and source checks; they fail on other
versions rather than guessing by token. They only write a new review ledger.

`to_review.py` turns accepted methods/types into the existing portable .NET
NameCandidates review format using fresh metadata inventories. It writes an
explicit pending list for fields, locals and unsupported contracts. These cannot
silently disappear from completion accounting. Local occurrences need semantic
reference binding before edits. Contract-family IDs must be bound to map roots
before those families are published. The .NET updater validates the exact input
identities and reports requested/applied names and collisions.

## Current limitations and next work

- This is still a partial review of the full indexed application. ETS bootstrap,
  command handling, project loading, conversion internals and many other call
  chains remain. Do not use the ledger count as an application readability metric.
- Field/local application support is unfinished. Source declarations are located,
  but a semantic reference pass must carry renames through all affected uses.
- The CvNext field `any.a` has an unresolved cross-component field signature.
  Common's equal-valued schema getters need their complete caller roles reviewed.
- **ETS 6.4's ETS6C input is not interchangeable with ETS6N.** Its process counter
  methods contain empty string literals where ETS6N has `Process`, `ID Process`,
  `Creating Process ID` and `#`. Names also differ despite equal MVID/token layout.
  `ets64-counter-string-discrepancy.json` records evidence from the input metadata.
  This discrepancy is unresolved; no string restoration or behavior equivalence
  is claimed. The current 6.4 decisions apply only to the main ETS6N input.
- No ETS exports, builds, full audits or live launches were performed for this
  pass. Only graph-tool regression and identity/mapping/reference checks ran.

Continue the complete naming pass before exports/builds. Keep unclear roles as
explicit work items. Completion requires applied readable source, consistent
references/contracts and consolidated verification over the whole intended tree.
