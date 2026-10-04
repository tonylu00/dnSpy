# Split iterator dispatch and disposal compatibility

`Invoke-IteratorSplitDispatchRegression.ps1` emits synthetic generic iterator
metadata with the entry-state tests split around the yielded loop body, matching
ETS 6.3 CalculatedParameters `r/b::MoveNext`. It exports using the actual dnSpy
plugin, builds the exported SDK projects and executes original and rebuilt
assemblies with one and four export workers. The test covers lazy construction,
cached Current, complete and empty enumeration, exceptions, early disposal,
resumption after disposal and generic/nongeneric enumeration.

The plain variant must reconstruct. A tail-dispatch call with observable effects
must retain its explicit state machine. A variant with an original terminal-state
Dispose must reconstruct without the empty-disposal restoration instruction.

Modern Roslyn writes the terminal state and sometimes clears reference temporaries
in generated Dispose methods. These change older empty-Dispose behavior. The
decompiler records an empty original Dispose only after successful reconstruction;
the native metadata build task restores it on the exact generated local state.
The task accepts only an empty body or local reference nulling followed by the
proven constructor state field's terminal write. It rejects calls, cleanup regions,
unexpected state values/fields and ambiguous or invalid owner instructions.

`IteratorDisposalContractRegression/Invoke-Regression.ps1` compiles the exported
restoration task itself and checks those guards and idempotence against synthetic
metadata in memory. Pass the unmodified compiled fixture from the split regression
and `.dnspy-metadata/RestoreFields.cs` from an export made by the tested runtime.

`Invoke-IteratorSplitDispatchBehaviorProbe.ps1` runs the same checks against the
original and rebuilt ETS CalculatedParameters modules in separate .NET Framework
processes. It also tests the array-argument iterator after early disposal. Original
runtime type/member names and signatures must resolve; dependency assembly identities
must match. This is selected-helper behavior evidence, not ETS startup, project,
unchanged-App compatibility or regenerated-state metadata coverage.
