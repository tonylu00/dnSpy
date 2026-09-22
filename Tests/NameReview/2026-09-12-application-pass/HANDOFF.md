# ETS naming handoff — September 22, 2026

Application-wide mapping remains active. Finish the mapping pass before a
consolidated ETS source export, build and runtime verification. During mapping,
use inexpensive identity, map and reference checks. No ETS operations ran in
this continuation. Constructor/native-import tooling used synthetic portable
fixtures; accepted ETS naming changes used metadata and map/reference checks.

## Accepted state

- dnSpy resumed from `7801a5f43` (wave166). The uncheckpointed wave167 artifacts
  were recovered and its current binary identities passed map preflight.
- Recovered timeout/listener milestone committed as `d8d47f14f` before continuing
  into transport lifecycle behavior. Unrelated untracked `ILSpy/` was preserved.
- Lifecycle review committed as `510108d6c`; the subsequent HID review follows
  its transport calls through native streams and platform discovery.
- HID review committed as `4dc71d729`; native-import support and physical
  compatibility resolution followed in de4dotEx `1b062ac0`.
- Current 6.3 map: `D:/knx_analysis/application-name-pass01/names63-staged-v176.xml`,
  SHA256 `85A378CAABD85F090F4D1982BA7162B63C60BC9176AFDA788236AC58C50F3347`.
- Current 6.4 map: `names64-staged-v13.xml`, SHA256
  `DD1C0FCCF4F7AB4BDE418D33A7C692CA5E81B8DBD18E53B2F2A731AEA7C54489`.
  The interrupted v8 file was byte-identical to v7. v9/v10 add independently
  reviewed timeout, USB stack-message and listener names.
- `reviewed63.json` is the cumulative accepted review. Earlier aliases and
  parameter/local decisions were checked for preservation. The current update
  reports are `map-update63-wave-176.json` and `map-update64-wave-13.json`;
  `map-update63.json` remains historical wave166 evidence.
  `checkpoint-wave176.json` records artifact hashes, validation and limits.
  `behavior-reviewed64.json` supplements the earlier 6.4 correspondence/property
  ledgers; it is not claimed to inventory all 6.4 decisions.
- de4dotEx `f1a4eda8` adds constructor parameter/local-only maps. `NewName` stays
  empty for constructor rows. `ScopedMappingBlocker` distinguishes this from
  forbidden constructor renaming, and validation uses actual metadata.
- The NameCandidates suite passed, including two synthetic physical assemblies
  with the same identity. Constructor names, signatures, flags, IL and executed
  constructor/type-initializer behavior were preserved after scoped aliases.
- The current contract reference manifest is `contract-references63-v2.json`,
  SHA256 `75A9047067B893EEADA2C147E01CC573BDD25ED784A591CBA839832358FB654F`.
  It retains the prior mscorlib reference and adds the exact .NET 4.8 reference
  System.dll to resolve INotifyPropertyChanged. Preflight proved the existing map
  still valid; the five internal layer families then resolved without blockers.
  Framework references supply metadata only and are not renamed or executed.

## Reviewed chain

Buffer extraction → feature/start/continuation/telegram report header and body
accessors → feature write/read and response match → bus connection state notification.
The associated `UsbStackMessage` now has named direction, protocol, HID body,
send-completion state and completion/failure helpers. Constructor arguments and
verified used IL locals carry the corresponding roles.

The next portion is now reviewed too: `WithTimeout` callback/captured-state roles
→ `SendAndWaitForCompletionAsync` / `WriteRawHidReportAsync` → `ReadFeatureInfoAsync`
→ cached manufacturer and host-descriptor reads. HID validation and telegram
event subscription/dispatch carry explicit names. The shared listener's expected
message matcher, unexpected-message exception selector, asynchronous cancellation
and completion-source roles are named in both versions.

Layer channel enqueue/completion, running/termination state and QuickReport
dispatch connect that listener to the transport. All members of five internal
ILayer/Layer contract families have one consistent name. Names came from body,
caller and actual counterpart evidence, with no shape-only transfer.

The report getters preserve details that matter: continuation `HidBody` returns
all 61 bytes including padding, and feature GET requests have no value. Stack
message equality compares direction and payload but does not compare protocol.
`Equals`, `GetHashCode`, and `ToString` contract names were left unchanged.
6.3 timeout/listener code does not retain/dispose cancellation registrations;
6.4 does. The 6.4 listener also clears callbacks on Dispose. These implementation
differences are recorded and preserved, not edited to match one another.

`usb_lifecycle.py` continues that chain through timestamped
`UsbReadFailedMessage` delivery, `ReceiveHidReportsAsync`,
`StartCommunicationAsync`, `CloseCommunicationAsync`, restart attempts and
state-machine dispatch. `WriteMessageAndSelectStateAsync` describes the action
that writes ordered HID fragments and returns the next connection state. The
connection lock, receive task/cancellation ownership, timestamps, statistics,
state callbacks and ten obfuscated 6.3 async carriers have corresponding names.
The 6.4 inner transport helpers were independently reviewed and named too.

Both update reports passed with zero errors and no new suffixes; the checkpoint
compared the entire before/after maps and cumulative reviews for preservation.
The receive loop delivers on the end flag and valid sequence, without an extra
byte-count equality check. Only 6.4 invokes Reconnected subscribers after restart.
These are existing behaviors, not runtime fixes or equivalence-test results.
Canonical 6.4 async metadata names remain intact. Explicit MoveNext contract
blockers still prevent local-only decisions inside those bodies; 6.3 captured
fields establish the logical local roles without bypassing those guards.

`hid_devices.py` now connects those calls through five full 6.3 HID contract
families: OpenAsync, Close, WriteAsync, ReadAsync and EnumerateDevices. The base
64-byte stream operations, Unix polling, task callbacks, platform discovery,
device-path predicate/factory and 6.4 feature-response matcher have reviewed
names. IL evidence binds local slots to the exact module: report buffers,
bytes read, polling descriptor, exceptions, SetupAPI detail structures and
access-probe handle/capabilities. Unused obfuscator locals are not named.

Windows interface enumeration returns true for an existing index even if detail
retrieval leaves a null path. The Unix sysfs fallback does not apply the requested
VID/PID filters used by its uevent branch. Base reads rethrow I/O errors after
closing; Unix polled reads log and return null. Naming preserves these details.
Native structure roles and 6.3 iterator storage are named with layout/marshaling
intact; external iterator method contracts remain unchanged.

The four libc imports RealPath/Open/Close/Poll were pending in wave175. They are
now accepted through `native_imports.py`, using fresh inventories and exact
native-import metadata. 6.4 keeps its existing method names while receiving the
same readable parameter terminology. The 6.3 errno exception helper keeps its
accepted method alias and gains the `errno` parameter. Native entry points,
libraries, flags and marshaling are preserved; malformed imports/runtime methods
remain blocked. The shared guard files are identical in de4dotEx and dnSpy.

The portable NameCandidates suite and NativeImportAliasRegression passed.
The latter exercises the actual source-map parser, pseudo-attribute emitter and
signature-qualified restoration instruction writer, including originally implicit
native entry points. These are synthetic metadata/binary-map checks, without
native calls or consolidated source/runtime verification.

The new duplicate-identity fixture exposed caller misbinding in ApplyMap's
in-memory resolver. It now retains physical paths and binds a caller to the
unique same-directory copy. The assembly-name cache cannot replace that binding.
A caller with no unique physical binding fails before rewritten images are
emitted; it still needs explicit dependency context. `native-wave176-validation.json`
binds test evidence and fresh inventories to the tooling milestone. Both ETS
map updates passed with zero errors, no new suffixes and prior decisions retained.

Wave170 was a candidate, not an accepted checkpoint: it replaced a restored
lambda method name with a helper name. The preservation check caught that;
wave171 restores `<GetHashCode>b__18_0` and retains the readable `runningHash` /
`nextByte` parameter names. Wave170 was never applied to ETS.

## Remaining work

- Whole-application naming coverage is still incomplete. Alias totals and
  duplicate compatibility copies are not a measure of completed readability.
- HID contracts, platform implementations/discovery and the remaining USB
  path/feature-response closure helpers have been reviewed. Continue into the
  coupled discovery/connector callers and other application components.
- Native import proposals from wave175 are resolved. Continue from
  `native63-wave176.cumulative.json` and `native64-wave13.cumulative.json`; do not
  reuse inventories that still report the old blanket native-method blocker.
- Review the 51 inherited requested/applied suffix adjustments listed in
  `inherited-suffix-review.json`. This continuation added none.
- Do not autoaccept the old correspondence queue: its shape normalization can
  erase library identifiers and some scripts collapse module paths to basenames.
  Treat it as a hint and verify actual bodies/callers in physical context.
- Saved public API audits/frozen maps describe 6.3 wave166 and 6.4 v7. Both are
  marked as needing refresh against the eventual final staged maps. Historical
  binary applies and `--verify-applied` checks do not prove source rebuilding or
  ETS runtime behavior.
- Use `graph63-v3.sqlite` and `graph64-v3.sqlite`; keep compatibility paths,
  SHA256, MVID and exact dependency scope. Pass `contract-references63-v2.json`
  to NameCandidates map updates/checks. Do not pick a map by
  newest filename. The current cumulative 6.3 review binds the v2 manifest hash.
- Leave uncertain storage fields and unsupported external contracts unresolved.
  Preserve compiler-generated aliases used by dnSpy to reconstruct lambdas.

The Python recipes operate on review data only; they do not rewrite ETS source.
`behavior_review.py` rejects implicit replacement of existing aliases (including
restored lambda names), retains old parameter/local choices and validates source
hashes. `checkpoint_behavior.py` uses an explicit plan to preserve prior map
decisions and validate the update/reference hashes. The actual canonical-alias
replacement guard and checkpoint hashes were checked without ETS execution.
Inputs are exact snapshots. Move/rebind graph roots explicitly on another OS;
do not substitute same-named assemblies.
