# Compatibility policy — ETS naming pass

Binding for every naming decision. Short on purpose. If a decision is not covered
here, treat it as *unresolved* and record the missing evidence; do not invent a name.

## What must never be renamed

1. **Everything on the SDK whitelist.** `sdk-name-whitelist63-v2.xml` (21,935 symbols,
   1,974 map rows excluded) and `sdk-name-whitelist64-v1.xml` (24,209 symbols, 167 map rows
   excluded), both bound in `STATE.json`. The four SDK modules are
   `Knx.Ets.Sdk.dll`, `Knx.Ets.Sdk.AddIns.AddInViews.dll`, `Knx.Ets.Common.Types.dll`,
   `Knx.Ets.Common.Resources.dll`.
2. **Any member whose base or interface declaration is protected**, and the whole
   contract family of such a member (an override cannot take a name the base does not have).
3. **Externally visible contracts of existing precompiled ETS Apps**: assembly, type and
   member identities, signatures, interface and inheritance contracts, and names reached
   through reflection, serialization, or a string contract that is not statically
   resolvable.
4. **Compiler-generated metadata needed for reconstruction** (`.ctor`, `.cctor`, state-machine
   and lambda metadata that the runtime binds by name).

## What may be renamed

Private implementation detail whose name is not reachable through (1)-(4). The tools enforce
the whitelist; `--update-map` drops or blocks excluded rows rather than trusting the review.

## How the boundary is enforced

- The proposal is never the enforcement point. `--wave` (which runs `--update-map`), `--merge-map`,
  `--check-map`, `--public-api-audit` and `--bind-sdk-whitelist` re-check every row against the
  whitelist and the physical module identity.
- Blocked rows must be reported, not silently skipped. `checkpoint-waveN.py` asserts
  `SdkVisibleRenamed == 0` and `SdkReferencedTypesRenamed == 0` before it writes a checkpoint.
- A wave may not add numeric collision suffixes. `Requested != Applied` means the wave is wrong:
  fix the rows and re-run, never accept `Foo2`.

## Third-party Apps

- The Apps ship as binaries and cannot be rebuilt. "Recompile the Apps" is not a solution
  and not an acceptable risk.
- Compatibility is proven against the *unchanged* third-party binaries, and only in the
  consolidated Phase-4 verification — never claimed from a metadata-only check.
- The few Apps on hand do **not** define the compatibility boundary. The whitelist, the
  SDK surface and the graph evidence define it.

## Naming quality

- A name must state a supported behaviour or responsibility. No placeholder names, no
  "Method12", no suffix to make the gate pass.
- Uncertain rows stay explicitly unresolved with the missing evidence recorded in the row's
  `UnresolvedReason`. That is a first-class outcome, not a failure.
- A row whose every evidence route is closed *with a measured number* is recorded unresolved
  with the reason code `no-evidence-in-scope`. Bulk private state — a field that is only read
  and written by unnamed code, with no literal, anchor, accessor or readable counterpart — is
  the normal case for that code, and it does not block the pass from closing.
- Keep genuinely different definitions distinct: overloads, same-named types across
  assemblies, and 6.3/6.4 compatibility twins are different rows even when the displayed
  name matches. Always key by physical module + metadata token/identity.

## What this policy does not authorize

- Editing ETS source, IL, metadata or binaries with a script. Renaming happens only through
  the dnSpy/de4dotEx tooling.
- Running ETS exports, rebuilds, full audits or live ETS scenarios during the naming phase.
  Those belong to Phase 4 and to the user-coordinated live checks.
