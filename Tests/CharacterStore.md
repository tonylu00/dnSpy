# Deferred array-store inference

Run `Invoke-CharacterStoreRegression.ps1` with `-DnSpyConsole` and a fresh `-OutputDirectory` (.NET 10 SDK and .NET Framework 4.8 required).

The emitter keeps a char-array receiver and index on the stack while evaluating a value and an intervening local assignment. The array comes from another expression, so its generated temporary can receive its type after the store is first visited. Completing inference before that receiver is typed leaves conv.u2 rendered as ushort rather than the required char conversion.

Consumers remain pending while a dependency is unresolved, allowing the store to use the eventual array element type. The regression verifies 16-bit truncation, checked conversion overflow, conversion-before-null-array-access order, and the intervening value calculation. One/four-worker exports must build and run, produce deterministic source and preserve input hashes. Reference-coalescing, stack-struct and stack-counter regressions exercise the shared inference pipeline.
