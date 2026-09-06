# Decompiler regression checks

After building `dnSpy.sln` in Release, run these scripts with a new output folder
outside the repository (so repository build settings do not affect the fixtures):

```powershell
.\Tests\Invoke-LogicalChainRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-logical-check
.\Tests\Invoke-ProjectExportRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-export-check
.\Tests\Invoke-AsyncLayoutRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-async-check
.\Tests\Invoke-NullableAliasRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-nullable-check
.\Tests\Invoke-ValueTaskRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-valuetask-check
.\Tests\Invoke-ApplicationConfigRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-binding-check
.\Tests\Invoke-DelegateReceiverRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-delegate-check
.\Tests\Invoke-CollisionNamesRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-collision-check
.\Tests\Invoke-SourceMetadataRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-source-metadata-check
.\Tests\Invoke-LoopControlRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-loop-control-check
.\Tests\Invoke-LargeMethodRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-large-method-check
.\Tests\Invoke-DefiniteAssignmentRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-assignment-check
.\Tests\Invoke-NumericOperandsRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-numeric-check
.\Tests\Invoke-ExceptionFilterRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-filter-check
```

The first test compiles long AND/OR expressions, exports them, rebuilds them and
checks 1,538 evaluation paths, including operand order and every short-circuit
position. It reproduces the stack failure seen in ETS's generated XML serializer.
The second checks a consumer without `TargetFrameworkAttribute` and an implicit
conversion used as an array receiver. Both original and rebuilt programs execute.
The async fixture reproduces reordered suspension/resume blocks and unrelated
branches between resume and result collection. It checks completed, suspended,
faulted and cancelled tasks, the unrelated branch, and finally execution before
and after export and recompilation. Two-await cases exercise backward layouts,
shared state dispatch, every completed/suspended combination and both failure
positions. An unsupported kickoff pattern checks that its referenced state-machine
implementation remains in the export.
Detached suspension blocks with earlier resume/result blocks cover both branch
polarities. Their kickoff methods must reconstruct as async source, preserve
factory evaluation counts, and retain an unrelated branch around the await.
Forward resume bookkeeping after the result path checks the same behavior,
including completed, suspended, faulted and cancelled tasks.
Incomplete reconstruction also retains the original implementation. The tests
cover side effects before await result collection, nested iterator cleanup,
early disposal, captured owner references and valid names for retained helpers.
Awaited finally blocks check cleanup after success, failure and cancellation,
suspended cleanup, and cleanup exceptions taking precedence over body exceptions.
Captured delegate caches retain their original zero-initialized storage.

The nullable fixture emits IL that copies a local's managed pointer across a
branch. It checks present and absent values and ensures the source is evaluated
once. The ValueTask fixture checks typed results from ordinary and configured
awaits, actual suspension, and exception behavior. It uses the framework support
libraries from dnSpy's `net48` build; `-TasksExtensionsPath` can select another copy.
The delegate fixture reproduces an object-typed field invoked without `castclass`
in the input IL. It checks the returned value, invocation count and null failure
before and after export and recompilation.
It also removes receiver casts from generic field reads, writes and managed
addresses, property and protected method calls, and reference returns. Rebuilt
code must preserve mutations, reference identity, call counts and null failures.
Emitted reference comparisons also check a generic class with overloaded equality:
the rebuilt identity comparison must not invoke its operator or cast the other
object to the generic class.
Unconstrained generic null tests cover reference values, integers and nullable
integers so boxing semantics survive reconstruction without an invalid `(T)null`.

The application configuration fixture checks a signed library version redirect
and a transitive dependency exposed by an overload in the newer library. The
original and rebuilt consumer must select the same overload and return the same
result. It also verifies traditional project references and rejects redirects
whose token, culture or version range does not match. For application exports,
pass `--app-config path\Application.exe.config`
to use that host's binding redirects. Without this option, normal assembly
resolution remains unchanged. File dependencies needed for overload resolution
are included in both SDK and traditional project exports.
Batch exports also follow dependencies through exported projects, so their
consumers retain binary support libraries needed to compile overloads.

The collision fixture rewrites metadata with repeated generic and parameter names,
including nested types, constraints, abstract methods and interfaces. The exported
declarations and uses must agree, compile and preserve each argument's behavior.
Nested redeclarations can also have different names from their enclosing type's
parameters; metadata arity preserves their positional binding in that case.
It also checks imported base types whose names match a namespace in the current
or enclosing scope; those uses must retain enough qualification to select the type.
Namespaces elsewhere in the assembly also participate in that lookup even when
the exported file does not import or use any of their types.
The source metadata fixture checks readonly conversion arguments, readonly reference
methods and indexers, mutable reference writes, tuples, static operations on dynamic
fields and stack allocation sizes. It removes the unsafe marker before export and
checks both execution and readonly return metadata after recompilation. Compiler
reserved attributes are projected into C# syntax rather than emitted as illegal
explicit attributes; the input assembly metadata is not changed.
It also covers private nested types exposed by helper signatures, guarded
constructor argument preparation (including null rejection and side-effect order),
and conversions through interfaces with substituted generic type arguments.
Additional emitted IL checks cover zero-initialized local storage and generic
`isinst`/unboxing for reference, value and nullable types, including failure and
single-evaluation behavior. Null arguments retain their selected overload and
generic arguments, while non-disposable enumerators retain conditional cleanup.
Catch variables used after their handler retain their outer lifetime. Filtered
handlers check exception identity and both accepting and rejecting the filter.

The loop-control fixture checks `continue` paths that skip a final assignment,
increment or condition. Moving that operation into a `for`, `foreach` or
`do/while` header must preserve the original control flow. Nested loops are
included so a continue in an inner loop does not change the outer loop's behavior.
Iterator state ranges and prepared enumerators check that normal, throwing and
skipped paths run cleanup exactly once where required.

The large-method fixture generates hundreds of live locals and repeated object
initializers with shared references and conditional values. Original and rebuilt
programs verify side-effect order, values and reference identity. Export time is
recorded in `timing.json`; use `-Count 4000` for a larger performance comparison.
There is no machine-dependent timing threshold in the regression.
Use `-Guarded` to place the generated initialization inside a try/finally and
check that cleanup still runs once. This exercises declaration indexing within
a nested scope as well as at the method root.

Loop tests also preserve writable iteration locals passed by reference through
array, generic and non-generic enumeration, plus async array iteration storage
across completed and suspended awaits. Such loops must not acquire the read-only
storage rules of a C# `foreach` variable.

The definite-assignment fixture checks delayed finally assignments followed by
loops of different sizes, nested and conditional cleanup, outward jumps,
unreachable successors and reuse after cancellation. It reproduces an analysis
loop found in ETS's device-copy operation. Assignment results from a leave must
include its finally blocks before they reach the successor; temporary results
can otherwise circulate indefinitely around a later loop.
An emitted syntax tree also reproduces an external jump to the first instruction
inside a try. Its rebuilt program checks that redirecting the entry preserves
internal back edges and executes the finally only once.

The numeric fixture rebuilds enum multiplication, division, remainder and shifts,
ordered boolean comparisons and unsigned negation. Its 199 checks cover integer
boundaries, signed and unsigned ordering, small enum promotion, signed shifts, both operand evaluations and
exceptions from the second operand. These IL operations need valid C# numeric
operands while preserving their original width and evaluation order.

`Invoke-DiscardedValuesRegression.ps1` checks 26 discarded-result outcomes,
including operator evaluation order, getter effects, invalid casts, null and
array bounds errors, checked overflow, and completed/suspended/faulted/cancelled
awaits. It also checks parameters whose names collide with generated temporaries.

`Invoke-InterfaceEventsRegression.ps1` renames explicit event rows and their
accessors independently. Rebuilt subscriptions and removals must still dispatch
through the original interfaces, including generic interfaces and an interface
whose accessor methods have unconventional names.

`Invoke-FinalizerRegression.ps1` reconstructs finalizers with local declarations
before the protected body. It checks lock execution, nested cleanup, base cleanup
and exception identity on success and failure. Finalization is suppressed and
invoked explicitly so the test does not depend on garbage collection timing.

`Invoke-InheritedPropertyRegression.ps1` emits interface MethodImpl accessors
without implementing property rows. Original and rebuilt programs check inherited
and shadowed base properties, getter/setter effects, exception identity, generic
interfaces and read-only/write-only properties. Declaration accessors and setter
parameters are also renamed. A separate export checks that directly referenced
orphan methods remain visible; their call-site reconstruction is not yet supported.

`Invoke-EventStorageRegression.ps1` checks WPF routed-event identifiers, automatic
instance/static/generic events, and custom accessors with observable side effects.
Emitted metadata includes VB-style backing-field names and a public field sharing
an event name. Rebuilt code must preserve direct field use, object initialization,
subscriptions, removals and concurrent registration without losing event storage.

The exception-filter fixture runs 25 checks on generic synchronous and asynchronous
handlers. It covers accepting, rejecting and throwing filters, exception identity,
first-pass ordering, nested cleanup, completed and suspended tasks, and successful
operations that must bypass the filter.

The expression-evaluator submodule and the `RoslynVersion` package setting must
use compatible Roslyn internals. Updating only the package can break dnSpy's build.
