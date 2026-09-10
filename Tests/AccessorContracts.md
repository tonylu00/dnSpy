# Restoring accessor contracts after source compilation

CLR property getter/setter names need not follow C#'s `get_`/`set_` convention.
Recompiling a property can otherwise break unchanged binary clients and virtual
dispatch even when all source projects compile.

SDK export attaches original raw method names and method flags to the final
accessor syntax. Source reference assemblies retain these instructions. The
restoration task uses the actual compilation reference files, full assembly
identity, declaring type and complete method signature to repair MemberRefs and
MethodImpl declarations before changing local definitions. This distinguishes
overloaded indexers and supports generic owners and cross-assembly overrides.
Runtime outputs remove the instructions; source reference assemblies keep them.
Matching contracts in duplicate reference copies are accepted; genuinely
conflicting matches cannot be chosen from a filename or assembly name alone.

Run `Invoke-AccessorContractRegression.ps1 -DnSpyConsole <exe>
-OutputDirectory <new folder>`. The fixture rewrites getter/setter names in both
library and binary client, then tests auto-properties, overloaded indexers,
generic virtual dispatch, inherited generic storage, a client-defined override,
nondefault method flags, and an explicit interface
implementation. Rebuilt and unchanged binary callers must both pass. Input
hashes, one/four-worker source determinism and incremental DLL/PDB hashes are
checked. This fixture does not establish whole-application ETS equivalence.
