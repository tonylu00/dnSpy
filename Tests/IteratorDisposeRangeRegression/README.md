# Iterator Dispose state ranges

Build with `dotnet build -c Release -p:RuntimeDirectory=<frozen plugin runtime>` and
run the resulting executable. The runtime must include the actual ILSpy core,
dnlib and dnSpy.Contracts.Logic DLLs built for the plugin.

The interval tests compare native range membership against independent integer
sets, including duplicate separated intervals, clipping, self union and both
integer limits. Large duplicate sets must compact; genuinely large disjoint
sets must retain the original state machine through symbolic-analysis failure.

The flow tests use the same conditional cleanup region in forward and backward
physical dispatch layouts. They check the exact state set and original node
identities. Cycles, missing targets, malformed region exits, excessive graphs,
distinct duplicate calls and helpers with incompatible receivers/signatures
must be rejected.

Signed comparison tests partition states using ordinary C# predicates as the
oracle. They cover all four relations, reversed operands, negation, offsets
that wrap at both Int32 limits, and threshold neighbours. Checked arithmetic
that may throw an overflow exception must remain unsupported.

`../Invoke-XmlDescendantsBehaviorProbe.ps1` additionally compiles an unchanged
caller against the original CV/5.6.241.33672 XML assembly. Run it in separate
processes against the original and a native exported/rebuilt module. It checks
ordered object identities and cleanup/exception traces for all five Manufacturer
collection groups. Use untouched physical dependencies from that compatibility
folder; never substitute a similarly named assembly from another folder.
The same caller checks Hawk memory-segment Location/AccessRights traversal and
inner cleanup, exercising its original signed Dispose dispatch predicate.
Pass `-ParameterItems` for the current ETS 6.3 XML module to check Parameter and
ModuleDefParameter item traversal too. Older CV5.6 modules have different public
item types; do not compile a caller for the newer API against those binaries.

`../Invoke-CommonPartitionBehaviorProbe.ps1` does the same for Common.Partition,
including lazy input access, invalid arguments, chunk materialization and
cleanup. Its rebuilt Common DLL targets the original netstandard2.0 framework.
