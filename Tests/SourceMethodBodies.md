# Comparing rebuilt method bodies

`Invoke-SourceMethodBodyAudit.ps1` compares two complete SDK export trees using
the shared fingerprint implementation in de4dotEx's NameCandidates tool:

```powershell
./Tests/Invoke-SourceMethodBodyAudit.ps1 -BeforeExport <baseline-export> -AfterExport <candidate-export> -NameCandidatesProject <de4dotEx>/tools/NameCandidates/NameCandidates.csproj -OutputDirectory <new-audit-folder>
```

Both export maps must have zero export errors and the same physical source
paths. Missing, added or duplicate projects fail the audit. Assemblies with the
same identity in different compatibility directories remain separate. Each
project must have exactly one matching Release output, including platform-specific
output folders. Reports include binary hashes and every differing method; no
input binaries are written.

When expanding an application export, `-AdditionalBeforeExports` accepts
previously validated isolated exports for the added components. Their physical
source paths must be disjoint from the primary baseline and each other. The
complete union must exactly match the candidate's project set; additions or
removals without a baseline still fail. Reports retain every baseline root and
the exact binary paths/hashes. This supports testing integration without dropping
coverage checks or accepting unverified new assemblies.

By default all method and generated type names must match. The optional
`-AlignStateOwners` switch permits only the generated state-type name correction
associated with the same uniquely matched owner method and its state-machine
attribute. Both types must be local compiler-generated children of that method's
declaring type. The corrected name must contain the original owner method name
(with the compiler's dot-to-hyphen escape) and unchanged ordinal/arity suffix.
Every correction is reported. This does not permit arbitrary aliases or ignore
generated names globally.

The fingerprints normalize short IL forms, assembly versions and unused locals.
They retain method flags, generic constraints, dependency name/culture/key,
signatures, field and method references, instructions, used locals and exception
regions. They compare every body, including constructors and generated methods.
Equal fingerprints prove equality under these documented normalizations, not
general semantic equivalence or complete application behavior. Use contract,
resource, compilation and live tests alongside this audit.

`Invoke-SourceMethodBodyAuditRegression.ps1` takes `-NameCandidatesProject` and
`-OutputDirectory`. It emits two physical assemblies with identical identities
but different implementations, checks a matching export, then requires rejection
of a changed compatibility body and a missing project. All fixture input hashes
must remain unchanged.
