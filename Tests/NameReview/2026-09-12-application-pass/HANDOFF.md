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
- USB configuration writes committed as `ccf4afe07`. The resumed SDK protection
  checkpoint is `checkpoint-sdk-whitelist184.json`, committed with dnSpy
  protection as `a2681bdde`. Interface configuration committed as `d74c4de2b`.
  RF dispatch and the nested-type scope fix committed as `5e4f854b1`, with
  de4dotEx `5db0d23b`. Connector writes committed as `2c2290feb`.
  Secure receive/timer policy committed as `2fc81dccb`.
  Routing startup/discovery committed as `c8a5bb743`.
  Unicast and programming-mode review committed as `f43016c2a`.
  Statistics aggregation and accessor evidence committed as `fb3528fcd`.
  Explicit-interface support and snapshot providers committed as `b551440d3`.
  Event/exception diagnostics committed as `318443f46`.
  Current naming checkpoint: `checkpoint-wave196.json`, from accepted 195/28.
- Current 6.3 map: `D:/knx_analysis/application-name-pass01/names63-staged-v196.xml`,
  SHA256 `13B9701DB2409E9D925C8B8F681367A5FF3DF30D6EACDA831E803F2C27EA8A32`.
- Current 6.4 map: `names64-staged-v28.xml`, SHA256
  `985460A9DB308044A0484D27B50F2F57036D82735B07E303946A20251B9BF78A`.
  The interrupted v8 file was byte-identical to v7. v9/v10 add independently
  reviewed timeout, USB stack-message and listener names.
- `reviewed63.json` is the cumulative behavioral review. SDK exclusions below
  take precedence over its historical proposals. Earlier aliases and
  parameter/local decisions were checked for preservation. Six compiler-style
  source aliases now have explicit replacement review; every other earlier alias
  was preserved by wave182. Wave187 explicitly replaces one further constructor
  lambda alias with `CreateItemValue`. Wave188 explicitly replaces the state-machine
  constructor selector with `SelectTransitionKey`. Wave191 explicitly replaces
  two discovery-frame length selectors with `GetStructureLength`.
  The last update reports are `map-update63-wave-196.json` and `map-update64-wave-28.json`;
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
- The current contract reference manifest is `contract-references63-v3.json`,
  SHA256 `92F3CAEBC070E7304914F56C2DF7537C67B6D9AB33C687B6DDD2A6B6FE7D1EBA`.
  It preserves the pinned mscorlib/System entries from v2 and adds the exact .NET
  4.8 reference `Facades/netstandard.dll`. Common binds IDisposable through this
  facade, whose forwarder targets the pinned mscorlib. With that metadata context,
  the existing map and six HTTP families pass preflight without weakening guards.
  Framework references supply metadata only and are not renamed or executed.

## Statistics values and aggregation (193)

`statistics_values.py` names the full three-member Clone, Merge and Clear
families and reviews the existing three-member CreateValue family. Interface63
now has the role `Knx.Falcon.Diagnostics.Statistics.IStatisticsValue`. Constructors,
lookup predicates, captured names and actual merge/clear loop locals connect
definitions to values. The two definition indexers retain get_Item and gain
parameter/local names through exact physical accessor ownership evidence.

Counter clones copy the count and share the definition. Histogram clones copy
the counters and share the definition/bucket array. Histogram merge iterates the
source length without checking compatible definitions or equal lengths; a longer
source can fail and a shorter one leaves destination tail counters unchanged.
The histogram definition constructor retains its empty loop, without sorting or
validating boundaries. These observations describe retained behavior.

6.4 was independently reviewed for interval creation, current/start/value getters,
name predicates and oldest-to-newest snapshot aggregation. Its real item-index
local is slot 8, not the unused slot 4; updateScope is slot 2. Selector types and
used fields carry the same roles as 6.3, with obfuscator storage left unchanged.

`behavior_review.py.bind_accessor_sources` consumes the existing de4dot
AccessorReview report, checks target path plus exact method identity/hash/MVID/
signature, and binds a missing getter declaration to the recorded property token.
The source hash and property/indexer kind remain mandatory. This supplies source
evidence only and cannot alter a mapping blocker or permission. No graph rebuild,
source substitution or ETS operation is involved. The two selected source links
are preserved in `statistics63-wave193-accessor-sources.json`; their provenance is
`accessors63-wave103.json`. Five portable tests in `test_behavior_review.py` pass
on this Windows host, including physical-copy mismatch, stale source/signature,
ambiguous owner and absent-binding rejection.

Accepted cumulative reviews: `statistics63-wave193.cumulative.json` and
`statistics64-wave27.cumulative.json`. Both map updates contain 43 edits, from
28/27 decisions respectively; existing CreateValue names were reviewed and kept.
Selected checks verify complete families, getter source links, every scoped
decision and prior map preservation. SDK bindings remain, with zero errors or new
suffixes. `statistics-wave193-validation.json` records evidence and tooling test
scope. No ETS apply/export/build/full audit/launch ran.

Next outward chain: IDiagSource snapshot providers and exception statistics.
6.3 Interface30 `0x060006B6` belongs to the thirteen-member family
`28F288B01A7C48F8A506C44BF6BFF2A8B42E62985061DFE117C6D48CE5A38097`
in `usb63-layer-families-v2.json`; every member has the explicit-method-implementation
blocker. Actual 6.4 contract is `Knx.Falcon.Diagnostics.IDiagSource.GetStatisticsSnapshot`
(`0x06002F2E`). Enhance shared qualified-interface mapping with synthetic dispatch/
reference tests before naming the family. Do not override inventory blockers.
This tooling limitation does not block the overall goal; other work remains too.

## Unicast and programming-mode continuation (192)

`unicast_transport.py` starts with WebSocket frame parsing, close notification,
raw-byte sending and the receive loop, then names all ten complete unicast
interface families: Received/Closed add/remove, SendAsync and five endpoint/
transport-policy getters. TCP connection cancellation and initialization, UDP
initialization, and cloud WebSocket connection setup have scoped names and used
backing fields. Eleven async carrier types and their actual captured state have
behavioral names; explicit runtime methods and unused obfuscator storage remain.

The complete eight-member `ReadLocalProgrammingModeAsync` family follows USB
local property/memory reads. USB reads cEMI object 0/property 54 or EMI1 memory 96
bit zero after a capability check. Five unsupported implementations return a
completed nullable result; one returns a null Task itself. These differences,
unchecked result-byte access and cancellation behavior are preserved.

The independently reviewed WebSocket helpers in 6.4 use the same operation names.
Source evidence binds reconstructed async wrappers while IL evidence binds the
actual MoveNext bodies. The 6.4 raw-send wrapper uses local slot 1, while its
receive wrapper uses slot 0; no unused obfuscator locals were named.

Observed behavior remains explicit: TCP uses a 5000ms send timeout; disconnected
UDP/WebSocket disconnect frames can complete without sending; the inner WebSocket
sender catches many errors. WebSocket receive delivers only the current fragment
when EndOfMessage is set, and its socket-error disposal branch may await its own
retained receive task. Compare these with original untransformed IL and runtime
behavior in the final consolidated verification; this naming pass changes neither.

Accepted cumulative artifacts are `unicast63-wave192-rev2.cumulative.json` and
`unicast64-wave26-rev2.cumulative.json`. Initial unicast review artifacts were
unpublished candidates; use the rev2 reviews. The 6.3 cloud connection explanation
uses verified ConnectorId/Target roles, not speculative client/server labels.
Reports contain 259/16 edits from 164/10 decisions, zero errors/new suffixes,
complete physical families and preservation of prior aliases/scopes and SDK
bindings. `unicast-wave192-validation.json` records selected reference evidence
and deferred behavior checks. No ETS apply/export/build/full audit/launch ran.

This was followed by the statistics value/factory continuation above.
Application-wide naming is still incomplete. Keep the previously
recorded routing reconfiguration/construction-order anomalies and other pending
items for consolidated verification.

## Persistent SDK name protection

NameCandidates now creates a reusable whitelist from explicit SDK module paths
and binds it to the map with a SHA256. The same guard runs in review updates,
binary application and dnSpy source alias registration, before publication or
mutation. One reviewed definition still propagates to resolved references;
one contract-family seed expands to all implementations/overrides. References
do not need separate naming decisions.
The de4dotEx tooling milestone is `9f61fc6c`.

The four SDK roots are Knx.Ets.Sdk, Knx.Ets.Sdk.AddIns.AddInViews,
Knx.Ets.Common.Types and Knx.Ets.Common.Resources DLLs. Whitelists protect their
public/protected definitions and parameters, transitive signature/base/interface/
constraint/forwarded types and their public surface, plus SDK private storage
types retained by the older audit policy. Private helper names remain editable.
Custom reflection/plugin loading still requires the deferred final runtime check.

- `sdk-name-whitelist63-v2.xml`: 21,935 symbols in 27 physical modules, SHA256
  `D0CEC1E57AAA5B7373209D86C63142F1816915A9769E5FEB3A0A73E9C9B46459`.
- `sdk-name-whitelist64-v1.xml`: 24,209 symbols in 31 physical modules, SHA256
  `E1F555A155E99C48D1296C09110D25023CF6902E71F3C8A96B98320383DECE34`.
- Binding excludes 1,974 rows from 6.3 v182 and 167 from 6.4 v19. Protected
  contract families are removed together. The checkpoint records every excluded
  alias and verifies all retained rows, scoped aliases and physical identities
  unchanged. Cumulative review ledgers remain historical behavior evidence;
  **only the protected maps are authoritative for effective aliases**.
- Both `map-check63-sdk184-final.json` and `map-check64-sdk20-final.json` passed
  without errors or edits. All six older SDK freeze entries remain protected.
- 6.3 v183 and whitelist63-v1 were candidates only, never accepted. They omit
  the conservative SDK storage-type closure. Do not resume from them.

Same-directory compatibility files remain independent. If multiple copies have
the same assembly identity, the resolver accepts a unique local filename matching
the requested assembly simple name (`Name.dll`/`Name.exe`). This resolves 6.4's
Xml.ObjectModel.dll versus Xml.ObjectModel_orig.dll; other ambiguities still fail
with physical paths. Synthetic fixtures verify independent renaming of both
copies, automatic call references, SDK parameter preservation, whole-family
freezing, stale input/manifest rejection and protected edits rejected before
output. The dnSpy fixture also verifies rejection before any aliases register.
These are tooling tests, not ETS execution or full application equivalence.

`checkpoint_sdk_whitelist.py` checks this policy transition; six portable tests
reject unrelated deletions, partial family removal, alias/scope changes, changed
physical identity and additions. Normal behavior waves continue to use
`checkpoint_behavior.py`, which must retain the SDK binding.

## Interface configuration continuation (185)

`interface_configuration.py` reviews the inner additional-address property
reader/writer and local-address writer before naming the complete eight-member
`SetInterfaceConfigurationAsync` contract. The shared parameters are configuration,
differencesOnly and cancellationToken. Three property-change callbacks, seven
async carrier types, their used fields and verified wrapper locals describe the
same operations. This adds 80 behavior decisions / 122 map edits, with zero
errors or new suffixes. All earlier effective aliases and SDK binding remain.

The implementations differ: USB dispatches EMI1/cEMI/PL/RF operations and leaves
its pending-write flag set after failure; IP tunneling either writes a feature or
edits device/additional addresses; two implementations only clone/store settings;
one always throws NotImplementedException. The additional-address writer swallows
list-shortening failures (including cancellation) but propagates later write
failures. Unused connection-context arguments, obfuscator fields and unsupported
explicit MoveNext mappings remain unchanged. Event delegate temporaries are
decompiler stack variables, not actual IL locals, and were not falsely mapped.

The 6.4 USB counterpart was read for supporting terminology; no 6.4 aliases changed
in wave185. That checkpoint retained its v20 map. This is a naming checkpoint,
not a behavior change, source export or runtime validation.

## RF info and receive dispatch continuation (186)

`rf_dispatch.py` follows cEMI additional-info parsing, iteration and ID/type
selection through buffer resizing, RF Multi transmission/reception and channel
fields, full/short acknowledgement slots, receive notifications and RF metadata
attachment. Both complete eight-member KnxMessageReceived add/remove contracts
now have consistent names, backing-delegate roles and real IL local names.
The iterator and predicate storage have behavioral names; their external runtime
contracts and unused obfuscator fields remain unchanged. Actual 6.4 bodies supply
supporting vocabulary; the three obfuscated dispatch/offset helpers and their
different local slots were independently reviewed in 6.4.

The review preserves existing behavior: clearing a short-ack slot does not grow
the buffer and may throw for an absent byte; setting one grows first. Trimming
retains at least one byte. Receive event data shares the original byte array.
The additional-info iterator uses the advertised section boundary and skips null
parser results; naming does not add validation or change exception handling.

The first 6.3 preflight rejected existing identical nested async helper names
under different connectors. Synthetic fixtures reproduced two overly broad
uniqueness checks, in de4dotEx and dnSpy. Both now include physical module and
enclosing TypeDef identity. Existing/new aliases survive later updates, source
alias registration and synthetic binary application; genuine same-owner collisions
are still rejected before mutation. de4dotEx fix: `5db0d23b`.
`nested-type-scope-wave186-validation.json` pins the reproductions and passing
tooling test evidence. The failed report did not publish a map. No suffix was
used to hide the bug.
`nested-type-scope-wave186-final-validation.json` additionally records the final
map preflight and dnSpy acceptance of identical top-level aliases in separate
physical files with the same assembly identity.

Accepted reports contain 196 edits for 82 decisions in 6.3 and 19 edits for three
decisions in 6.4, with no errors or new suffixes. These totals describe the reviewed
chain, not application-wide completion. `map-check63-wave186-final.json` additionally
revalidates the accepted map with zero edits/errors. SDK bindings, earlier effective
aliases and scoped decisions remain unchanged. No ETS export/build/apply/launch ran.

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

## Connector writes (6.3 wave187 / 6.4 v22)

`connector_write.py` follows local-reset restoration, routing-busy pacing, raw
message wrapping, routing indication preparation and successful-send statistics
through both complete write contracts. All eight `WriteAsync` implementations/
interface definitions and all five `WriteRawAsync` members were reviewed, including
the unsupported implementation. Shared definitions retain physical identity and
their reference targets; aliases are consumed through the tools' normal reference
propagation, not source replacement. Seven 6.3 async carriers and their used fields
have descriptive names. Explicit MoveNext methods and unused fields remain intact.

The USB reset helper waits the **elapsed** time when it is below a second, clears
the timestamp, and conditionally restores cEMI/PID_COMM_MODE settings. This is the
observed behavior, not a repaired delay calculation. USB writes ignore their
cancellation token. Routing writes pace sends and clone the normal message, may
emit a synthetic confirmation, and swallow/log InvalidKnxMessageException; raw
routing writes do not swallow it. EIBlib writes use timeout/cancellation and update
statistics after a response. These differences are explicit in the evidence.

Counter/histogram helpers now lead through `StatisticsInterval`, `UpdateStatistics`,
`StatisticsCollector.Update` and `GetSnapshot`. The monitor scope, one-minute
interval rotation and ten-interval retention are preserved. The previous
`<.ctor>b__0_0` alias at 6.3 `0x06001A02` has exact replacement evidence for
`CreateItemValue`; all other existing aliases and parameter/local decisions remain.

6.4 reset and routing helpers were reviewed independently. The review also records
the existing 6.4 raw-write differences as background: it permits Busmonitor and
examines outgoing property-write data; no change to that readable method was made.
Both map updates and `map-check63-wave187.json` / `map-check64-wave22.json` passed,
with SDK bindings intact and no new suffixes. `connector-write-wave187-validation.json`
checks every proposed decision in the maps and complete membership of both write
families. No ETS source export, binary apply, build or launch ran.

## Secure routing and receive policy (6.3 wave189 / 6.4 v24)

`routing_timer.py` names the IP CCM block/counter transformations, wrapper and
timer-notification authentication helpers, and secure routing receive/dispatch.
It follows the generic state machine through event contexts, every reviewed
transition action, one-shot scheduling, timer acceptance and synchronization waits.
6.3 carrier types/used fields and parameters/actual IL locals are included;
canonical 6.4 async metadata remains intact. The constructor-lambda alias at
6.3 `0x06001867` has exact replacement evidence for `SelectTransitionKey`.

The evidence records behavior without changing it: successful wrapper decryption
is cached and a later different key only logs; the counter increments only its
last byte; synchronization waits can complete after swallowed timeouts without a
valid response; transition actions do not await their sends. Receive echo
suppression compares source/destination/length/APCI, not the full payload. The
6.3 timer trigger `E11` (`0x04001B16`) remains unresolved because no firing caller
establishes its meaning. Trigger E01..E10 have actual dispatch/action evidence.

`routing_policy.py` completes the inner system-broadcast message fields before
their classifier callers. It includes security-control bit access, domain/serial
payloads, network-parameter payloads and their typed construction. Filtering
retains the unchecked first test-byte access. The raw-message add/remove and
reset-suppression contracts include all five physical members of each family,
their backing fields and all four raw notification raisers.

Both final map preflights passed with no new collision suffixes and unchanged SDK
bindings. `routing-receive-wave189-validation.json` verifies each proposed name
and scope, all four contract families, physical identities and the unresolved
trigger. The only omitted no-op parameter row retains its original `sender` name.
All unreviewed aliases/scopes are preserved. No ETS apply, export, build, full audit
or launch ran. These checks do not establish ETS runtime equivalence.

## Routing startup and discovery (6.3 wave191 / 6.4 v25)

`routing_open.py` follows the communication factory through multicast socket
adaptation, complete receive/close/send contracts and routing initialization.
Frame parsing and optional keyed transforms connect to multicast callbacks,
system-broadcast forwarding and discovery replies. HPAI address/protocol handling,
device-information/search-parameter block decoding, frame constructors and typed
selectors/iterators are reviewed together. Eight 6.3 async carriers and their used
fields connect factory/open/send/dispose/reconfigure operations. The two
constructor-lambda replacements are 6.3 `0x0600098A` and `0x060009A2`.

Both versions' discovery callbacks and inner address predicates were read.
Discovery responses use a fixed fallback MAC when no network interface matches,
route-back requests use the packet source endpoint, and SendAsync is not awaited
before disposing the temporary UDP client. The source/IL behavior is preserved.
The local-slot guard rejected an unused 6.4 slot 2; `localPort` uses actual slot 10.
The initial partial `routing-open63-wave190.*` files were never mapped. Its rev2
candidate was withdrawn before commit when semantic review found the unicast
factory endpoint was mislabeled as local. Its argument and captured field now use
`controlEndpoint`, corroborated by the TCP/UDP callers and canonical 6.4 factory.
V191 was built again from committed v189, not by overwriting the scoped-name guard.
Use `routing-open63-wave191.*` and `routing-open64-wave25-rev3.*`; 6.4 rev3 is
byte-identical to its checked rev2 review and reuses the unchanged v25 checks.

Reconfiguration needs an explicit deferred behavior check: 6.3 wrapper
`0x06001D3E` / body `0x06001D83` creates replacement transports in state storage,
but the inspected IL has no stores into the connector transport fields before
`InternalOpenAsync`. The 6.4 `0x0600352F` exported body shows the same anomaly.
Also preserve the constructor order passing the not-yet-assigned statistics field
to the timer. Compare these with untransformed original IL during consolidated
verification; this mapping pass makes no claim that they are intended behavior.

`routing-open-wave191-validation.json` verifies every accepted name/scope, all five
two-member multicast contract families, physical reference uses and SDK bindings.
Both final map preflights pass, all other prior aliases/scopes remain, and there
are no new suffixes. No ETS operations or full audit ran.

## Explicit diagnostic snapshot contracts — checkpoint 194

`diagnostic_sources.py` stages the complete thirteen-member 6.3 snapshot family
as `GetStatisticsSnapshot`, `Interface30` as `Knx.Falcon.Diagnostics.IDiagSource`,
and ten additional collector fields as `statistics`. Every implementing body
passes its own `IDiagSource.Instance` to the previously reviewed `GetSnapshot`.
`diagnostic-wave194-validation.json` records 24 new names, exact physical family
evidence, preserved prior aliases/scopes and SDK binding, and zero new suffixes.
The 6.4 v27 map remains unchanged and passes preflight with the updated tool.

de4dotEx/dnSpy now accept representable, single-target private explicit interface
families. Multi-target bodies, class slots and external/unresolved contracts remain
blocked. Binary apply and metadata restoration visit live MethodImpl references.
The de4dotEx milestone is `304d7a7c`; the ILSpy source projection is `49c38da82`.
dnSpy emits the reviewed interface method/type names and carries the original
body name in a declaration marker, avoiding guesses about C# qualified names.
Two failures found by the new fixture were fixed: stale imports after a namespace
move, and resolver-dependent generic parameter names in restoration keys. New
v3 keys use generic slots and source type identities; v1/v2 remain readable.

The portable NameCandidates suite executes distinct host/compatibility behavior
for same-identity assemblies and confirms untouched compatibility bytes. The
synthetic ContractFamilyRegression exports with one/four workers, rebuilds, runs
rebuilt and original callers, verifies explicit/generic/nested-interface and
renamed generic array signatures, restores reflection names, and checks input
and incremental hashes. Native import alias regression also passes. These are
tool fixtures, not ETS application verification. No ETS export, build, binary
apply, full audit or launch ran.

Resume from `diagnostic63-wave194.cumulative.json` and
`statistics64-wave27.cumulative.json`, with protected maps **194/27**.
The initial map-update report without `-rev2` only records a missing input path;
it published no map. The accepted report is `map-update63-wave-194-rev2.json`.

## Event buffering and exception diagnostics (195)

`exception_diagnostics.py` follows the bounded queue through the complete 6.3
Add/ToArray sink families, prefix/source decorators, source closure traversal,
snapshot selection and identity matching, exception attachment, and the
outer-to-inner statistics iterator. Both physical Falcon versions were inspected;
the 6.4 source is `Knx.Falcon.2/`, while its retained `Knx.Falcon/` source is 6.3.
Constructors, captured values and used local slots carry the same behavioral roles.

The queue does not enforce capacity atomically across threads. Decorators mutate
the supplied event. Matching uses definition reference identity and instance
string equality, retaining older matching snapshots. The iterator records an
identity before skipping empty definitions. These are observed behaviors, not
repairs. The 6.4 decompiled iterator's unreachable unassigned return remains a
final source/runtime verification concern; no compile success is claimed here.

`bind_usage_sources` validates physical identity, inspected signature, IL offset,
opcode and resolved graph target before binding an inlined delegate or captured
field to its caller's current source. It never changes a mapping blocker or the
graph/source. Eight portable tests passed in the preceding continuation, including
wrong physical input, missing/mismatched edges and stale caller-source rejection.

The accepted 52/39 decisions produced 88/71 map edits. The selected validation
rechecked physical input and source hashes, effective aliases/scopes, complete
sink families, SDK bindings and prior-map preservation. Both map preflights pass
with zero errors and zero new suffixes. `exception-wave195-validation.json`
records scope and hashes. No ETS apply/export/build/full audit/launch occurred.

## HTTP client configuration and pooling (196)

`http_client_pool.py` reviews the physical root Common module m0039, separately
from its compatibility copies. It traces header configuration and the inclusion
predicate through client creation, acquisition from two concurrent stacks, HTTP
forwarding and return-to-pool behavior. Six complete families now use AcquireClient,
SendAsync, GetByteArrayAsync (string/Uri), and GetAsync (string/Uri). The factory,
interfaces, wrapper, predicate capture and used storage/scopes have role names.

Two earlier aliases were inaccurate: CollectRedirectHeaders created a client,
and IsRedirectHeader accepted any header under the selected policy. Exact
old/new replacement evidence corrects them to CreateClient and ShouldIncludeHeader.
All other prior aliases and every scoped decision remain intact. Header filtering
compares the exact case-sensitive x-knx-redirect key and does not configure HTTP
redirect handling. The read-only dictionary wraps mutable copied storage.

The missing IDisposable contract was a netstandard reference. The pinned v3
manifest resolves its forwarder through the already pinned mscorlib; old-map
preflight passed before any new decisions. The selected six families contain 12
members, with graph reference uses verified in their exact physical context.
Full inventory `http63-wave196-families.json` is provenance for the compact retained
family evidence; use v3 for future family reviews and map checks.

35 decisions produced 64 edits with no suffix changes. Input/source/IL hashes,
SDK binding, effective names/scopes and map preflight pass. The inherited wrapper
base marks it disposed, while acquisition does not reset that state; the forwarding
methods do not check disposal. Keep this as a final original-IL/runtime comparison
item, not a repaired or verified lifecycle. No ETS operation ran. 6.4 stays at v28.

## Remaining work

- Whole-application naming coverage is still incomplete. Alias totals and
  duplicate compatibility copies are not a measure of completed readability.
- Catalog parsing/localization, volatile saved addresses, EMI1 initialization/
  shutdown, configuration reads/writes, feature discovery/cache and cEMI
  initialization and the complete SetInterfaceConfigurationAsync contract are
  reviewed (USB 6.3 `0x06001C96`, body `0x06001D0E`; 6.4 `0x0600340E`). RF receive
  dispatch, subscription and complete write/raw-write contracts are reviewed.
  Secure-wrapper/receive handling and system-broadcast policy are now reviewed.
  Routing open/receive/discovery wiring, local programming mode and unicast
  transport contracts, statistics value/factory and snapshot-provider chains are now reviewed.
  Diagnostic exception attachment/enumeration is now reviewed. Continue the ETS
  executable and other application components. Review the memory-278
  write helper (6.3 `0x06001CB4`, body `0x06001D26`; 6.4 `0x0600342D`) before
  assigning register-specific semantics to it or the three saved register fields.
- IDiagSource snapshot providers now use the complete reviewed family. The fresh
  `explicit63-wave194-families.json` supersedes blanket explicit-method blockers
  in older inventories. Filter by physical module and token together.
  Multicast receive/close/send, all ten unicast families and the programming-mode
  read family are complete. Their implementations retain their behavioral differences.
- Native import proposals from wave175 are resolved. Continue from
  `http63-wave196.cumulative.json` and `exception64-wave28.cumulative.json`; do not
  reuse inventories that still report the old blanket native-method blocker.
  Use protected maps **196/28** as the bases. Do not reintroduce SDK-excluded
  proposals from those historical ledgers.
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
  SHA256, MVID and exact dependency scope. Pass `contract-references63-v3.json`
  to NameCandidates map updates/checks. Do not pick a map by
  newest filename. The current cumulative 6.3 review binds the v3 manifest hash.
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
