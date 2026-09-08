# Protected block entry regression

`Invoke-TryEntryRegression.ps1` checks source rebuilds with one and four export workers, input/source hashes, and runtime exception identity and cleanup order. The fixture includes an external re-entry and an internal backedge: re-entry must run cleanup for each completed protected execution, while the internal backedge must not run cleanup early.

The control-flow test constructs cases that retain a branch into the first label of a protected block, rather than letting condition reconstruction remove it. It verifies a new outer entry label, reuse of an existing label, collision-safe names, nested protected regions, a try at the beginning of the method, and rejection of jumps into the middle of a protected body. The previous engine fails the new-entry case. The compiler-generated runtime fixture itself also passes the previous engine, so it is supporting behavior coverage rather than the reproducer.
