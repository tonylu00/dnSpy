# ETS names reviewed from inner helpers outward

This batch accumulates names before rebuilding the complete application tree.
The review starts with constants, arithmetic, dictionary lookups, fixed-width
records and system-library calls, then names their callers and ETS wrappers.
The evidence files record each decision, its order, source path and source hash.
These are descriptive source aliases, not claims to recover original identifiers.

## ETS 6.3

Added **254 method, 23 type and 93 parameter aliases** in one full export/build.
The validated output is `D:\git\ets63-name-self07`, with the cumulative map at
`D:\knx_analysis\self-name-review05\names63-final.xml`.

The names cover feature constants/checksums, license dictionaries and expiry
helpers, parent chains, package progress data, packed package records, collection
snapshots and dongle event handling. Package helpers distinguish character counts
from byte storage sizes. Event publisher/subscriber relationships and readable
counterparts corroborate lock/unlock roles even where callback bodies match.

The cumulative map has 56 types, 393 methods and 187 parameters across six
physical modules. All 111 managed projects build. Comparing all **194,229 compiled
method bodies** against `ets63-name-self06` found **zero differences and zero
owner-name changes**, without name normalization. SDK, original-name and 3,013
state-machine attribute checks also report zero issues. `validation63.json`
records exact report paths, hashes and totals.

## ETS 6.4

Added **112 method, 12 type and 50 parameter aliases** in one full export/build.
The validated output is `D:\git\ets64-name-self03`, with the cumulative map at
`D:\knx_analysis\self-name-review05\names64-final.xml`.

The review names package-record leaves and their callers, feature validation
helpers and license-query selectors. Both physical ETS executables now use
`SelectDongleLicenseViewModels` and `SelectLicenseViewModelLicense` inside
`EnumerateAllLicenses`. Their separate source-map identities are retained.
Comparisons against missing package-name literals in ETS6C remain deferred;
names from ETS6N were not copied into those ambiguous methods.

The cumulative map has 13 types, 654 methods and 67 parameters across 29
physical modules. All 178 managed projects build. Comparing all **385,538
compiled method bodies** against `ets64-name-self02` found **zero differences
and zero owner-name changes**, without name normalization. SDK, original-name
and 5,891 state-machine attribute checks also report zero issues.
`validation64.json` records exact report paths, hashes and totals.

The additional layout audit passes in both versions: each has ten renamed
layout types, eighteen instance fields and eight fixed arrays. It verifies
packing, class size, instance field order/types/flags/offsets and fixed-array
marshal metadata. The portable checker is in `Tests/SourceAliasLayouts`.

Together this round adds **544 aliases**, with one complete export/build per
ETS version. No collision suffixes were needed. The full cross-version candidate
scan was also reviewed; its sole unmapped result, the ETS6C subscription-disposal
helper, was checked directly before acceptance. Existing aliases were retained.

## Apply the reviewed names

The JSON inputs use the portable C#/.NET NameCandidates tool. Supply the preceding
cumulative map and a fresh destination for each output:

```text
dotnet NameCandidates.dll --update-map ets63-reviewed.json base63.xml names63.xml update63.json
dotnet NameCandidates.dll --check-map names63.xml check63.json
dotnet NameCandidates.dll --update-map ets64-reviewed.json base64.xml names64.xml update64.json
dotnet NameCandidates.dll --check-map names64.xml check64.json
```

Physical paths, tokens, hashes, MVIDs and signatures bind each reviewed symbol.
The updater preserves previous aliases and reports collision adjustments.
Export the complete input set with its dependency contexts so references use the
same aliases. dnSpy's build task restores the original runtime identities.

The accompanying orphan-SpecialName support permits ordinary emitted methods
whose original property/event association is absent. Actual accessor and operator
contracts remain guarded. Metadata and executable regressions passed, including
unchanged binary callers and one/four export workers.

This was an offline naming pass. It did not launch ETS or alter an installed
runtime. The body comparison uses the preceding validated source build, whose
input already contains prior restoration and test patches. It does not claim
equivalence with an untouched vendor installation. Existing mixed UTC/local
expiry behavior is documented and preserved. Unsupported contract families and
names lacking behavioral evidence remain review work.
