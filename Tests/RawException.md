# Raw exception operations in SDK exports

Run `Invoke-RawExceptionRegression.ps1` with `-DnSpyConsole`, a fresh `-OutputDirectory`, and `-Wrap false` or `-Wrap true`. Run both wrapping variants. Requires the .NET 10 SDK and .NET Framework 4.8.

The emitter creates legal IL that throws arbitrary objects and captures them with object catch handlers. C# cannot directly express these operations. SDK exports use a marked, collision-free exception type and a ThrowValue placeholder, emitted after normal transformations so async cleanup and rethrow recovery can still inspect the original patterns. The after-CoreCompile task changes catch types and corresponding locals back to System.Object, removes placeholder calls before IL throw, and removes the helper type. Original exception-wrapping attributes are retained. Ordinary views and non-SDK exports still show the original operations.

The regression compares original and rebuilt output with wrapping enabled and disabled, checks thrown object identity through storage, ordinary exceptions, strings, throw-null behavior, and reflected catch metadata. It includes a user type occupying the helper's default name. One- and four-worker exports must build and run, produce deterministic source, preserve inputs, and leave executable/PDB hashes unchanged on incremental builds.

The build task requires unsigned compiler output. Current placeholders target System.Object throws and variable-bearing object catches. They do not by themselves fix every source restriction on handler ordering, exception filters, or yield statements inside try/catch blocks. Full application behavior still requires separate validation.
