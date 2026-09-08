# Stack-carried loop inference

Run `Invoke-StackCounterRegression.ps1` with `-DnSpyConsole` and a fresh `-OutputDirectory` (.NET 10 SDK and .NET Framework 4.8 required).

The emitter keeps an integer counter on the evaluation stack across a backward branch, using dup to compare and consume copies and pop at loop exit. Before the fix, the first inference pass prematurely completed an assignment whose producer had no type, causing the counter and its copies to become object.

Unresolved assignment values remain pending until their producer is typed. This allows the integer initializer to seed the loop without forcing a type based on the final C# use site.

The original and rebuilt executables check negative, empty, single-iteration and repeated loops. Exports with one/four workers must build and run, generate deterministic source and preserve input hashes. Reference-coalescing and stack-struct regressions cover identity, short-circuiting, nullable values, value/reference categories and debug spans affected by the shared inference pipeline.
