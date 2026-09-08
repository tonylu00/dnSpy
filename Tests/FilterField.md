# Field captures in exception filters

Run `Invoke-FilterFieldRegression.ps1` with `-DnSpyConsole` and a fresh `-OutputDirectory` (.NET 10 SDK and .NET Framework 4.8 required).

The emitter creates a conditional filter that first checks the exception type, copies the exception to a local and to instance/static fields, then evaluates its predicate. This models hoisted exception storage in obfuscated async state machines. A nested finally records unwind order.

Recovery retains the field assignments inside the filter expression. Only stores whose values are known copies of the successfully matched, non-null exception are sequenced this way; arbitrary field writes are not assumed non-null. Reference comparisons avoid invoking overloaded equality operators.

The original and rebuilt executables check field identity, accepted/rejected predicates, predicate exceptions, handler selection, and filter-before-unwind order. One- and four-worker exports must build and run, produce deterministic source, and preserve input hashes. `Invoke-ExceptionFilterRegression.ps1` additionally covers generic filter behavior and suspension.
