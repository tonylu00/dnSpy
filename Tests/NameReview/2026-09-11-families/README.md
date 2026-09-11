# Reviewed ETS 6.3 security and ZIP method families

This batch applies nine manually reviewed method-family names to 19 interface,
implementation and override members, plus 30 parameter aliases. It completes
the nine family naming decisions deferred in the preceding security batch.

| Source alias | Reviewed behavior |
| --- | --- |
| `GetPasswordKey` | PBKDF2-SHA256 password key with the supplied salt |
| `CreateKnxZip` | Shared project/device-template ZIP creation contract |
| `ExtractProjectContainerWithKey` | Extract using one optional access key |
| `ExtractProjectContainerWithKeys` | Extract using a sequence of candidate keys |
| `CalculateStoreCompareHash` | Derive a store comparison hash from a password |
| `CalculateStoreCompareHashFromAccessKey` | Derive that hash from an access key |
| `CalculateAccessKey` | Derive a project access key from a password |
| `CheckStorePassword` | Check the supported stored password hash forms |
| `CheckAccessKey` | Check provider keys directly and through the store hash |

The choices come from inspected 6.3 implementations and readable 6.4 counterparts.
These names describe behavior; inferred identifiers are not claimed to be the
original source names. Exact evidence, physical paths, hashes, MVIDs, tokens and
signatures are recorded in `ets63-evidence.json` and `ets63-reviewed.json`.

NameCandidates now expands a selected family from authoritative metadata and
applies one alias across all declarations and implementations. Partial families,
conflicting names, stale inputs and ambiguous physical dependencies fail before
publication. dnSpy independently validates the complete family before export.
The original runtime method and parameter names are restored during compilation.

Apply the reviewed JSON to the preceding cumulative map using the portable tool:

```text
dotnet NameCandidates.dll --update-map ets63-reviewed.json base63.xml names63.xml update63.json
dotnet NameCandidates.dll --check-map names63.xml check63.json
```

`validation.json` records the exact local paths and report hashes. The source
output is `D:\git\ets63-name-self04`; its cumulative map contains 21 type,
106 method and 64 parameter aliases across four physical modules. All 111
managed projects build. Comparing 194,229 compiled method bodies against the
preceding validated export finds zero differences without name normalization.
SDK contracts, runtime alias restoration and 3,013 state-machine attributes
also pass. Input and rebuilt password helpers each pass five synthetic vectors.

The portable metadata regression additionally covers generic substitution,
virtual overrides, overload separation, separate duplicate-identity branches,
family-wide collision repair, parameter-only edits, explicit contract blockers,
unresolved external interfaces and invalid-map rejection. The C# dnSpy regression
exports with one/four workers and executes both rebuilt and unchanged callers,
including generic, inherited, override, overload and async dispatch.

Further ETS naming remains in progress. Explicit `MethodImpl` families and
accessors still need additional restoration support; the 6.4 ETS6C string
ambiguity remains deferred. This offline batch did not launch ETS or replace an
installed application.
