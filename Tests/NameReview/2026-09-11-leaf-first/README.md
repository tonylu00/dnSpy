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

## Apply the reviewed names

The JSON inputs use the portable C#/.NET NameCandidates tool. Supply the preceding
cumulative map and a fresh destination for each output:

```text
dotnet NameCandidates.dll --update-map ets63-reviewed.json base63.xml names63.xml update63.json
dotnet NameCandidates.dll --check-map names63.xml check63.json
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
