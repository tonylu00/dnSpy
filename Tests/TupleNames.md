# Named tuple SDK contracts

SDK source export preserves TupleElementNamesAttribute through temporary metadata
instructions because the legacy AST emits ValueTuple types without tuple syntax.
The build restores names on retained types, fields, properties, events, method
returns and parameters, including runtime delegate methods. Null positions and
nested/long tuple shapes are retained. Reconstructed lambda parameters cannot
carry these source attributes and are excluded.

Reference assemblies receive tuple names before downstream projects compile;
other source aliases and visibility remain unchanged there. Runtime restoration
removes the instructions and rejects conflicting annotations.

Run `Invoke-TupleNamesRegression.ps1 -DnSpyConsole <exe> -OutputDirectory <new-folder>`.
It covers async returns, nested and long tuples, constructors, events, generic
base types, properties, parameters, interfaces and delegates. Both unchanged
binary clients and fresh named-tuple source clients run against rebuilt outputs.
One/four-worker source determinism, input hashes and incremental DLL/PDB hashes
are checked.

ETS 6.3 source22 rebuilt all 76 managed projects with zero errors. The current
MCP source then compiled against that SDK, including RetCode/Data access on
ReadFunctionPropertyAsync and ReadFunctionPropertyExtAsync. This is compile and
focused runtime validation, not a full ETS behavioral equivalence claim.
