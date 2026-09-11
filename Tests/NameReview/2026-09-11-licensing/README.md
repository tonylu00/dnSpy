# Reviewed ETS 6.3 licensing and dongle names

This batch adds 12 type aliases, 33 method aliases and 30 parameter aliases.
Names were chosen from inspected method bodies, callers and event subscriptions,
with readable 6.4 counterparts used as supporting evidence where appropriate.
They describe behavior and are not a claim to recover every original identifier.

The Common assembly now exposes source names such as `EtsDongle`,
`EtsDongleManager`, `EtsLicense`, `LicenseFeatureValue`,
`ICloudKitSessionManager`, `ISessionLease` and `LicenseSubordinationChain`.
References throughout the exported project tree use these names. Runtime
metadata retains the original names and namespace layout.

The remaining six ordinary `LicenseManager` helpers are named in both physical
ETS executables: `HandleDongleUnlocked`, `HandleDongleLocked`,
`CheckLicenseImportTimeout`, `StopDongleManagerWithTimeout`,
`LogTimeDefinitionRead` and `DisposeDongleManager`. Lock/unlock handlers have
identical bodies, so their event subscriptions establish their distinct roles.
The 6.3 disposal helper has no null guard, so its name deliberately differs from
the previously reviewed 6.4 `DisposeDongleManagerIfPresent` helper.

Other accepted methods describe cloud-dongle enumeration, collection updates,
event publication, package reads, license-chain construction and list transforms.
All 75 requested aliases were accepted without collision suffixes. Meaningful
public overload names remain intact. Physical ETS6C and ETS6N inputs retain
separate map rows, hashes and dependency contexts despite their shared identity.

`ets63-reviewed.json` is the portable NameCandidates input, and
`ets63-evidence.json` records the reasoning for every accepted symbol. Apply it
to the preceding cumulative family map with:

```text
dotnet NameCandidates.dll --update-map ets63-reviewed.json base63.xml names63.xml update63.json
```

The validated source output is `D:\git\ets63-name-self06`. Its cumulative map
contains 33 type, 139 method and 94 parameter aliases across four physical
modules. All 111 managed projects build. The full comparison against
`ets63-name-self04` checks 194,229 compiled method bodies with zero differences
and no name normalization. SDK contracts, original runtime names and
state-machine attributes also report zero issues. Exact paths and report hashes
are recorded in `validation.json`.

The initial body audit caught two changed fingerprints: an async parameter's
source alias remained in a generated state field used by the kickoff and
`MoveNext` methods. dnSpy now restores fields created from explicitly aliased
parameters, including iterator argument copies and constructed generic field
references. The expanded C# regression reproduces the previous failure and
passes with one/four workers, rebuilt and unchanged callers, reflection checks
and stable incremental hashes. The initial `ets63-name-self05` export is retained
for diagnosis; `ets63-name-self06` contains the correction.

This batch was offline and did not launch ETS or modify an installed runtime.
Cloud session method families remain deferred because the metadata graph lacks
the external `IDisposable` contract; their type names are accepted independently.
The 6.4 private license enumerator still carries unsupported `SpecialName`
metadata. These and earlier explicit-interface/accessor cases remain naming work.
