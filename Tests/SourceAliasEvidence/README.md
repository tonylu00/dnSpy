# Trace strict alias differences to source evidence

Build this read-only .NET 10 tool with `-p:RuntimeDirectory=<native-runtime>`.
Run it with a completed `GeneratedSourceInspection audit-scope` report, a
`SourceAliasContracts` report, an `ActualCompiledSourceToNativeObservationJoin`
report, and a fresh output path.

The join verifies physical input hashes, MVIDs, signatures, native report hashes,
the common scope summary, and actual compiled source bytes. It keeps parameter
sequences, printed uses, declarations, state-machine owner records, body witnesses,
and hoisted-field bindings separately. Reports are read one module at a time.

An exact source hash means UTF-8 bytes after BOM removal; split designer files and
other source transformations must stay explicit in the supplied source join.
`NoDirectSourceEvidence` is an investigation queue, not proof of dead storage.
For example, an auto-property can hide an original field from the final AST while
still requiring that field's runtime name for reflection and serialization.

All differences remain unresolved runtime contracts. Compiler-generated markers,
reconstructed bodies, and the absence of printed uses do not waive metadata
compatibility or retire naming candidates. This tool never changes ETS source,
binaries, or maps.
