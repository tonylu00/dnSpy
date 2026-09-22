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
- Native-import review committed as `11a17e96a`. The catalog and saved-address
  continuation uses shared constructor scope validation from de4dotEx `73bcaf9f`.
- Catalog/address review and the dnSpy constructor-scope parser fix committed
  as `be2014c8d`; the next continuation names EMI1 initialization and shutdown.
- EMI1 initialization/shutdown committed as `3e9b9f365`; the current continuation
  follows local-memory response matching through configuration and feature reads.
- Configuration/feature reads committed as `3e57125bd`; this continuation follows
  configuration writes and cEMI initialization, including explicit selector aliases.
- Current 6.3 map: `D:/knx_analysis/application-name-pass01/names63-staged-v182.xml`,
  SHA256 `A1B72930DEAFC5F1488F0C9ECE92E1A5BA21DAD1A47D3773A3A48904F6F4EB77`.
- Current 6.4 map: `names64-staged-v19.xml`, SHA256
  `98876DD21ADA8DA2BF92AB8273F5D17EF59997D01394B877F458B767949444BE`.
  The interrupted v8 file was byte-identical to v7. v9/v10 add independently
  reviewed timeout, USB stack-message and listener names.
- `reviewed63.json` is the cumulative accepted review. Earlier aliases and
  parameter/local decisions were checked for preservation. Six compiler-style
  source aliases now have explicit replacement review; every other earlier alias
  is preserved. The current update reports are `map-update63-wave-182.json`
  and `map-update64-wave-19.json`;
  `map-update63.json` remains historical wave166 evidence.
  `checkpoint-wave182.json` records artifact hashes, exact replacements and limits.
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

`usb_catalog.py` follows discovery into candidate XML catalog selection and
interface parsing, vendor/product lookup, translated display names and the
complete 6.3 `IUsbInterfaceInfoProvider.IsKnxUsbDevice` contract. Both versions
now carry reviewed catalog/record/context names, constructor parameters and
verified parser locals. Localization tries the exact culture, one immediate
parent, then default text; it does not recursively traverse all parents.
Catalog candidates are ordered by version, and parsing failures can fall through
to the next candidate. Earlier file/XML enumeration and version-sort failures
are outside that per-catalog catch. Canonical lambda/iterator names and hidden
automatic-property backing fields remain unchanged.

`usb_addresses.py` follows the volatile configuration branch into
`UsbDeviceAddressPersister`. Its HID-path lookup, Get/Set/Clear behavior,
captured context and verified document/setting/error locals are reviewed in
both versions. Get returns null for missing/caught read failures. Set logs caught
XML/save failures, but directory creation is outside its catch; Clear's file
deletion errors propagate. These details are preserved, not repaired.

The accepted constructor scopes exposed a dnSpy source-map parser defect: it
still applied the constructor method-rename prohibition to parameter/local-only
rows. `ScopedMethodBlocker` is now shared by both tools. The portable
`ConstructorScopeAliasRegression` reproduced the rejection before the fix and
passes afterward; constructor method names stay unchanged, and stale metadata
or constructor renames remain rejected. The full NameCandidates suite and
NativeImportAliasRegression pass too. Fresh checks of maps 178/15 pass without
edits or errors. `constructor-wave178-validation.json` binds this tooling
evidence; it does not claim a consolidated ETS source export or runtime test.

`usb_shutdown.py` extends the same chain through local-interface timeout,
EMI1 write/verification delay, PEI/mode initialization, saved BCU settings,
restoration and reset. `InitializeLocalDeviceEmi1Async` optionally saves settings
before changing them. `UninitializeLocalDeviceAsync` persists the volatile
individual address and restores saved EMI1 settings, then resets an open EMI1
interface in finally. It does not close the HID transport. The reviewed 6.4
bodies and existing canonical async carrier names corroborate the semantic
names; 6.3 bodies were independently followed through their explicit MoveNext
implementations. Six 6.3 carrier types and their state, builder, connector,
owned local interface, awaiters and pending exception have named roles. The
verified wrapper local slot is `stateMachine`; explicit MoveNext locals remain
blocked. No canonical 6.4 carrier names were replaced. Both map updates passed,
preserving earlier decisions without new suffixes.

`usb_configuration.py` now follows PC value header/address/length/payload
helpers and constructors through the complete six-member 6.3 `IsConfirmation`
family and `MatchesPcValueConfirmation`, into `ReadEmi1LocalMemoryAsync`.
The selected physical contract is recorded in
`usb-config63-confirmation-family-v2.json`; the updater revalidated it against
the same v2 reference manifest. A zero-length PC value confirmation matches the
request, then becomes a read failure. Timeouts retry once after 200 ms with an
increased response timeout. The initial send lies outside the response-wait
registration cleanup; its failure does not execute that removal. No logic was
changed to conceal these distinctions.

Those reads now lead into individual/domain address, serial number, local
descriptor and full interface-configuration readers. RF acknowledgement records
are read in chunks of at most 15; a reviewed selector decodes five optional
UInt32 link-layer timeouts. Domain readers retain their exact length checks.
Serial-number reads still ignore the supplied cancellation token. Descriptor
fallback preserves the local-mode unsupported sentinel and PL/RF/TP precedence.
Six 6.3 async carriers and their used captured fields describe requests, retries,
responses, address accumulation, acknowledgement chunks and configuration roles.

`usb_features.py` continues through descriptor/version matching into
`ReadBusInterfaceFeaturesAsync`, its seventh 6.3 carrier and the HID-path feature
cache. It names serial/APDU/medium/time-base/communication/RF/filtering feature
roles and records the cancellation/fallback behavior. For non-cEMI interfaces,
the BCU programming-mode test only runs when descriptor fallback was needed.
Cache lookup and insertion use exact path equality, retain at most four entries
and do not refresh order on hits. Canonical 6.4 carriers remain intact; no names
were assigned to unused obfuscator fields. Both update chains passed with no
errors or new suffixes. All prior map and review decisions are preserved.

`usb_configuration_write.py` follows the acknowledgement sort/group/duplicate
selectors into deduplicated property writes, then connects individual-address,
PL domain/repeater, RF acknowledgement/timeout and reception/filtering updates.
Six previously restored `<MoveNext>b__60_*` source aliases now have explicit
behavioral replacements, such as `HasDuplicateAcknowledgements` and
`SelectFirstAcknowledgement`. Distinct grouping uses have distinct names, with
no generated collision suffixes. Physical metadata identities and existing
parameter/local decisions remain intact. These aliases name explicit helpers;
they do not rename the original compiler metadata used for source reconstruction.

Communication-mode encoding, busmonitor time-base reads and RF mode/additional
information setup now lead through cEMI initialization and the EMI1/cEMI
dispatcher. Twelve obfuscated 6.3 async carriers and their used fields describe
the same roles. The actual wrapper local slot is verified: several 6.4 methods
use slot one, unlike the 6.3 wrappers. Canonical 6.4 carrier names are preserved.
The bodies establish an important difference: 6.3 retries rejected Busmonitor
as LinkLayer, while the corresponding 6.4 helper throws its enriched exception.
Acknowledgement count writes use CancellationToken.None, timeout write failures
are swallowed, and requested RF Multi can remain true after a failed mode write.
These are recorded behaviors, not runtime repairs or equivalence results.

Both map updates passed with zero errors and no new suffixes. The checkpoint
validates the entire maps and cumulative reviews, permitting only the six exact,
evidence-bound replacements. Seven portable synthetic Python checks exercise
stale/missing/wrong-physical-path approvals, scope preservation and staging guards.
No ETS exports, builds, binary applications or launches ran.

Wave170 was a candidate, not an accepted checkpoint: it replaced a restored
lambda method name with a helper name. The preservation check caught that;
wave171 restores `<GetHashCode>b__18_0` and retains the readable `runningHash` /
`nextByte` parameter names. Wave170 was never applied to ETS.

## Remaining work

- Whole-application naming coverage is still incomplete. Alias totals and
  duplicate compatibility copies are not a measure of completed readability.
- Catalog parsing/localization, volatile saved addresses, EMI1 initialization/
  shutdown, configuration reads/writes, feature discovery/cache and cEMI
  initialization are reviewed. Continue the complete SetInterfaceConfigurationAsync
  contract (USB 6.3 `0x06001C96`, body `0x06001D0E`; 6.4 `0x0600340E`), then remaining
  open/dispatch callers and other application components. Review the memory-278
  write helper (6.3 `0x06001CB4`, body `0x06001D26`; 6.4 `0x0600342D`) before
  assigning register-specific semantics to it or the three saved register fields.
- Native import proposals from wave175 are resolved. Continue from
  `usb-write63-wave182.cumulative.json` and `usb-write64-wave19.cumulative.json`; do not
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
  Preserve compiler-generated metadata needed for reconstruction. Existing source
  aliases can only change through exact old/new replacement evidence bound to the
  same physical module and base-map hash; no blanket replacement policy applies.
- Explicit MoveNext body-local maps are still rejected by the shared guards.
  A future scope-only enhancement must preserve the runtime method name and
  implementation binding, validate actual IL local slots/types, and use portable
  synthetic fixtures. Never bypass the tool guard by editing inventory flags.

The Python recipes operate on review data only; they do not rewrite ETS source.
Renaming, reference repair and patching belong in dnSpy/de4dotEx. Improve those
tools when a reviewed mapping cannot be consumed; never substitute direct ETS
source replacement scripts. Tooling builds and synthetic fixtures are distinct
from the postponed consolidated ETS export/build/runtime verification.
`behavior_review.py` rejects implicit replacement of existing aliases (including
restored lambda names), retains old parameter/local choices and validates source
hashes. Its optional `replace_alias` requires the exact prior alias and records
the replacement with behavioral/source evidence. `checkpoint_behavior.py` uses
an explicit plan to preserve prior decisions except those exact replacements,
validate their physical identity/base-map hash, and retain update/reference hashes.
Unused replacement approvals and scoped-name changes are rejected. The guards
and checkpoint hashes were checked without ETS execution.
Inputs are exact snapshots. Move/rebind graph roots explicitly on another OS;
do not substitute same-named assemblies.
