# Goal: readable, rebuildable and behavior-compatible ETS

Read STATE.json, then POLICY.md and PLAYBOOK.md. These files are the current state
and requirements. Do not use archived handoffs to select maps or restart work.

## Objective

Produce a readable, consistently named ETS application across its executable and
coupled first-party components, export source that actually compiles, and verify
the rebuilt application against original behavior and unchanged third-party ETS Apps.
Complete ETS 6.3 first, then apply and verify the tooling and mapping workflow on 6.4.
ETS 6.3 primarily exercises Dotfuscator restoration; 6.4 exercises the combined
Dotfuscator/NetReactor workflow. Success means rebuilt ETS behavior, not just tool builds.

## Naming and readability

- Treat the complete application tree as a shared symbol/call graph. Identify a symbol
  by physical module path, hash/MVID, metadata token and signature; preserve distinct
  compatibility assemblies even when their assembly names match.
- Follow recognizable framework/library calls through inner helpers to callers. Name
  methods, types, fields, parameters and locals together from demonstrated behavior.
  Apply a mapping across references, interfaces and override families through the tools.
- Detect short names and tool placeholders as review candidates. Preserve meaningful
  existing names and legitimate overloads; spelling or overload count alone is not proof
  of obfuscation. Never replace a placeholder with a, b, c_1 or an invented suffix.
- Keep unsupported guesses explicitly unresolved with missing evidence and the routes
  examined. Record evidence-free private state as no-evidence-in-scope only after the
  relevant evidence routes have been exhausted. Do not restart measured exhausted routes
  without new evidence.
- Reconstruct lambdas, closures, async/await and state machines into their owning source
  methods using structural evidence. Record every necessary leftover with its cause;
  prevent recursive inlining from exhausting memory without broadly reducing readability.

## Compatibility and tool requirements

- Enforce the ETS SDK whitelist and protected contract families. Unchanged third-party
  ETS Apps must remain compatible; rebuilding those Apps is not an acceptable workaround.
- Keep readable source aliases distinct from original runtime metadata identities where
  required. Preserve assembly/member/signature identity, MethodImpl, reflection,
  serialization, resources and XAML/BAML binding contracts. Generated closure restoration
  must identify the actual owner, including overloads, rather than match a name prefix.
- Export only first-party components. Reference known NuGet packages when their assembly
  identities match the original dependencies; otherwise reference untouched original
  binaries. Keep DevExpress, Telerik and other third-party components intact.
- Enhance dnSpy, de4dotEx and NetReactorSlayer when a concrete gap prevents this goal.
  Reusable naming, reference propagation, restoration, export and patching behavior must
  live in the tools. Scripts may explore code, prepare maps and orchestrate tools, but
  must not directly replace names or patch ETS source, IL, metadata or binaries.
- Core helpers must be usable through .NET or another portable language. Do not make the
  naming workflow depend on Windows-only PowerShell parsing or regex replacements.
- Preserve folder structure, skip components without the relevant protection, and resolve
  dependencies in their physical compatibility context. Improve batching, caching and
  parallelism where measurement identifies a bottleneck, with bounded memory usage.

## Execution order and verification

1. Repair the current ETS 6.3 exporter/build blockers: generated closure-owner conflicts
   and XAML resolution against restored runtime type names. Re-export and compile the
   actual ETS solution after a concrete fix; continue through subsequently revealed errors.
2. Measure whole-tree readability, close or explain the eight remaining Falcon async
   stubs, and finish application-wide naming coverage in complete feature/type blocks.
3. Freeze the maps, export the complete first-party source, compile the full solution,
   stage the rebuilt application into a separate output tree, and run consolidated
   identity, contract, resource, reference and compatibility verification.
4. Launch and test rebuilt ETS 6.3 through KNX-ETS-MCP, then verify ETS 6.4. Exercise
   startup, system language, test-mcp project loading, password-protected project loading,
   saving/reopening and available unchanged third-party Apps. Verify string restoration
   and the previously reported failures against original evidence. Do not enable
   ExtendedLogging, which disables saving.

During naming, use inexpensive identity, map and reference checks. Do not export or
rebuild the whole application after each small name change. Targeted tool regressions
and ETS source builds needed to repair concrete exporter/compiler failures are allowed
before naming closes. Consolidated end-to-end verification follows the frozen mapping pass.

## Live ETS authorization

The user authorizes the agent to launch ETS autonomously and control it through the
KNX-ETS-MCP plugin for this goal, without asking again before each launch or test.
Use the test project and staged output tree for mutating scenarios. Preserve original
installations and unrelated work; later user instructions restricting ETS use take
precedence. Fix ETS-MCP tooling gaps when necessary for these tests.

## Current starting point

- Maps: 6.3 names63-staged-v381.xml; 6.4 names64-staged-v178.xml. Check actual hashes
  against STATE before use; v381 removes two conflicting rows from v380.
- Latest recorded export: D:\knx_analysis\ets63-source-v385, 64 projects and 13,296 C#
  files. Its build reported three first-layer errors: two closure-owner conflicts and one
  XAML/runtime-name mismatch. Dependent projects may reveal more errors after those fixes.
- The 6.4 bulk anchor route is measured exhausted. Remaining naming is evidence-led
  per-row/cluster work, not another bulk anchor engine.
- Consolidated rebuilt-application compatibility and live tests are not yet proven.

## Definition of done and progress

- Every in-scope symbol is named, already readable, SDK/protected, compiler-generated
  and reconstructed, or explicitly unresolved with evidence recorded.
- The complete first-party ETS solution builds from tool-exported source with the intended
  dependencies. No manual generated-source edits are needed to reproduce that build.
- Staged rebuilt ETS passes the declared runtime scenarios and unchanged-App compatibility
  checks. Report unavailable tests and every remaining limitation explicitly.
- Progress is whole-application coverage, readable call chains, reconstruction quality,
  successful ETS source builds and observed behavior. Commits, test counts and duplicate
  alias totals are not substitutes. Commit validated milestones and keep STATE under
  200 lines; history belongs in git, not per-wave journals.
