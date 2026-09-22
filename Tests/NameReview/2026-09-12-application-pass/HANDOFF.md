# ETS naming handoff — September 22, 2026

Application-wide mapping remains active. Finish the mapping pass before a
consolidated ETS source export, build and runtime verification. During mapping,
use inexpensive identity, map and reference checks. No ETS operations ran in
this continuation; only synthetic NameCandidates fixtures were executed.

## Accepted state

- dnSpy resumed from `7801a5f43` (wave166). The uncheckpointed wave167 artifacts
  were recovered and its current binary identities passed map preflight.
- Current 6.3 map: `D:/knx_analysis/application-name-pass01/names63-staged-v171.xml`,
  SHA256 `C4A82487927C1C5226C5223F408ACE24CC57DB54D88119B71A3824974C720EDD`.
- Current 6.4 map remains `names64-staged-v7.xml`. The interrupted v8 file is
  byte-identical to v7, so it is not a new set of decisions.
- `reviewed63.json` is the cumulative accepted review. Earlier aliases and
  parameter/local decisions were checked for preservation. The current update
  report is `map-update63-wave-171.json`; `map-update63.json` remains historical
  wave166 evidence. `resume-wave171.json` records artifact hashes and limits.
- de4dotEx `f1a4eda8` adds constructor parameter/local-only maps. `NewName` stays
  empty for constructor rows. `ScopedMappingBlocker` distinguishes this from
  forbidden constructor renaming, and validation uses actual metadata.
- The NameCandidates suite passed, including two synthetic physical assemblies
  with the same identity. Constructor names, signatures, flags, IL and executed
  constructor/type-initializer behavior were preserved after scoped aliases.

## Reviewed chain

Buffer extraction → feature/start/continuation/telegram report header and body
accessors → feature write and response match → bus connection state notification.
The associated `UsbStackMessage` now has named direction, protocol, HID body,
send-completion state and completion/failure helpers. Constructor arguments and
verified used IL locals carry the corresponding roles.

The report getters preserve details that matter: continuation `HidBody` returns
all 61 bytes including padding, and feature GET requests have no value. Stack
message equality compares direction and payload but does not compare protocol.
`Equals`, `GetHashCode`, and `ToString` contract names were left unchanged.

Wave170 was a candidate, not an accepted checkpoint: it replaced a restored
lambda method name with a helper name. The preservation check caught that;
wave171 restores `<GetHashCode>b__18_0` and retains the readable `runningHash` /
`nextByte` parameter names. Wave170 was never applied to ETS.

## Remaining work

- Whole-application naming coverage is still incomplete. Alias totals and
  duplicate compatibility copies are not a measure of completed readability.
- Review `ac3`'s timeout/cancellation helper before naming the USB send caller
  `m0088:0x06001BFB`. Continue into send/receive workers only after their helpers.
- Review the 51 inherited requested/applied suffix adjustments listed in
  `inherited-suffix-review.json`. This continuation added none.
- Do not autoaccept the old correspondence queue: its shape normalization can
  erase library identifiers and some scripts collapse module paths to basenames.
  Treat it as a hint and verify actual bodies/callers in physical context.
- The saved public API audit/frozen map describes wave166. It is explicitly
  marked as needing refresh against the eventual final staged map. Historical
  binary applies and `--verify-applied` checks do not prove source rebuilding or
  ETS runtime behavior.
- Use `graph63-v3.sqlite` and `graph64-v3.sqlite`; keep compatibility paths,
  SHA256, MVID and exact dependency scope. Pass `contract-references63.json`
  to NameCandidates map updates/checks. Do not pick a map by newest filename.
- Leave uncertain storage fields and unsupported external contracts unresolved.
  Preserve compiler-generated aliases used by dnSpy to reconstruct lambdas.

The four Python recipes in this checkpoint operate on review data only; they do
not rewrite ETS source files. Their inputs are exact snapshots. Move/rebind graph
roots explicitly when using another OS; do not substitute same-named assemblies.
