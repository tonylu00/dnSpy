# Decompiler regression checks

After building `dnSpy.sln` in Release, run these scripts with a new output folder
outside the repository (so repository build settings do not affect the fixtures):

Build the complete solution, including its plug-ins. Building only
`dnSpy/dnSpy/dnSpy.csproj` does not rebuild the ILSpy extension and can leave an
older decompiler in the application output. Use a fresh copy of the complete
output for concurrent regression runs; do not replace DLLs while a run uses them.

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
Forward and backward jumps from switches and conditional branches also preserve
one shared local across their assignment and read sites (40 value/cleanup cases).
Unrelated branch locals keep their own scopes, and sibling collection loops still
reconstruct without conflicting with shared iterator storage.
`Invoke-JumpLocalRegression.ps1` additionally exports and rebuilds 65 ordinary and
retained-iterator scenarios covering value flow, evaluation counts, exception
identity, resumption and disposal.

The numeric fixture rebuilds enum multiplication, division, remainder and shifts,
ordered boolean comparisons and unsigned negation. Its 272 checks cover integer
boundaries, signed and unsigned ordering, small enum promotion, signed shifts, both operand evaluations and
exceptions from the second operand. These IL operations need valid C# numeric
operands while preserving their original width and evaluation order.
Boolean stack values converted to single/double precision also retain one operand
evaluation, exceptions, numeric overload selection and their boxed result type.
Boolean-to-byte/sbyte/short/ushort conversions also retain their narrow result
types in returns, boxing, overload resolution and byte-array stores. Null and
out-of-range arrays must still evaluate the value before throwing.

`Invoke-NullCoalescingRegression.ps1` reverses seven reference null branches and
adds empty branch blocks. Exported base/this constructor calls must retain their
argument scope. Its 33 scenarios also check lazy fallback evaluation, exceptions,
object/array identity, unchanged arguments and numeric branch behavior.

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
Existing implementation property rows are also renamed independently of their
interface rows and accessor names; the exported property must bind to the
interface's declared property name.

`Invoke-InterfacePropertyMethodRegression.ps1` emits private property accessors
that implement ordinary interface methods. Its 62 checks retain property
metadata, generic storage, multiple MethodImpl slots, direct accessor calls,
derived interface reimplementations, boxed structs, indexers, mutable and readonly
references, exceptions, and delegate receiver evaluation. Both one-worker and
four-worker exports are rebuilt and executed. Interface methods forward to the
retained property body so direct access does not acquire interface dispatch.

`Invoke-EventStorageRegression.ps1` checks WPF routed-event identifiers, automatic
instance/static/generic events, and custom accessors with observable side effects.
Emitted metadata includes VB-style backing-field names and a public field sharing
an event name. Rebuilt code must preserve direct field use, object initialization,
subscriptions, removals and concurrent registration without losing event storage.

`Invoke-ComImportRegression.ps1` checks COM class/interface identity and the
compiler-generated public runtime constructor after export and recompilation.
It does not activate a COM server. Ordinary constructor bodies are also executed
to verify that the special handling stays limited to COM import metadata.

`Invoke-BamlReferencesRegression.ps1` loads a resource whose static value comes
from an assembly referenced only by BAML. SDK and traditional single/batch exports
must retain a resolved binary or project reference. Both SDK outputs are rebuilt
and executed, and the fixture verifies that no IL assembly reference masks the case.

`Invoke-BamlTemplateScopeRegression.ps1` preserves dependency property owners inside
templates instead of borrowing the enclosing style's target. Original and rebuilt
resources retain absent/explicit template targets, trigger and setter identities,
template bindings, and named trigger activation/reset on an isolated control.

`Invoke-GacReferencesRegression.ps1` checks a System.Management dependency resolved
from the installed GAC. The .NET Framework export retains its framework reference;
the .NET Standard export retains the resolved file path. Both rebuilt libraries
are loaded by their original .NET Framework host without making a WMI query.
Emitted System.Core references also exercise LINQ and crypto types without mixing
framework implementations into the exact .NET Standard reference surface. Reference
sets come from installed matching SDK packs or the NuGet package cache; the original
reference behavior is retained when no matching set is available.

The exception-filter fixture runs 25 checks on generic synchronous and asynchronous
handlers. It covers accepting, rejecting and throwing filters, exception identity,
first-pass ordering, nested cleanup, completed and suspended tasks, and successful
operations that must bypass the filter.

`Invoke-AwaitCatchRegression.ps1` rebuilds catch-all handlers containing awaits
and conditional rethrows. Its 41 checks preserve retries, exception identity and
stack, cancellation, callback failures, and wrapped non-Exception payloads.
`Invoke-UsingLifetimeRegression.ps1` checks 37 outcomes for reused async resource
storage, enumerator cleanup, initializer reads, nested disposal, shared closures
and ref aliases. Both suites rebuild and execute exports with one and four workers.
The definite-assignment suite also repairs empty forwarding jumps whose labels
were placed inside nested C# blocks. It checks exception/cleanup behavior and
retains jumps across cleanup boundaries, cycles and nested function scopes.

The expression-evaluator submodule and the `RoslynVersion` package setting must
use compatible Roslyn internals. Updating only the package can break dnSpy's build.

`Invoke-RvaSpanRegression.ps1` reconstructs immediate `ReadOnlySpan<T>.ToArray()`
copies from immutable compiler RVA data. It runs 36 original/rebuilt checks with
one and four export workers, including UTF-8 strings, embedded nulls, integer
widths, unused trailing data, independent copies and empty-array identity. Its
20 analysis checks retain unsafe operations when lengths, element types, field
mutability or initialization effects prevent an exact constant reconstruction.
Floating-point and boolean blobs remain unchanged because their raw bit patterns
may not have an equivalent C# constant representation.

`Invoke-IteratorTerminalRegression.ps1` moves the first, middle, last yield or
exhaustion block to the physical end of `MoveNext`, while preserving every control
flow edge. It emits the older compiler's empty `Dispose` body used by ETS. Each
layout must reconstruct as an iterator and pass 241 original/rebuilt checks with
one and four export workers: lazy evaluation, every item, factory exception
identity, early disposal, trailing work, exhaustion and independent enumerators.
The current Roslyn disposal-state store and generic iterator kickoff patterns
remain separate cases and are not covered by this reconstruction test.

`Invoke-CachedArgumentRegression.ps1` checks cached delegates among multiple
base/this constructor arguments. Its 294 checks cover left-to-right evaluation,
lazy cache creation, delegate identity, volatile cache writes, generic base
signatures, constructor-body effects and exceptions at every evaluated operation.
Fallbacks and exception handlers must also observe the original null assignment
to a local, including when that local is passed by reference. Both one-worker and
four-worker exports are rebuilt and executed.
Four methods also run through IL reconstruction with debug-span collection
enabled to check the folded delegate and constructor paths used by the debugger.

`Invoke-RecordWithRegression.ps1` checks native record classes and `with`
initializers, including renamed Reactor clone methods. Each input variant passes
89 original/rebuilt checks with one and four workers: virtual copy dispatch,
custom copy constructors, init-setter side effects, nulls, exception identity and
order, sealed/abstract/generic/nested records, chained and conditional copies,
equality and hash contracts. Reference-valued conditionals also exercise base,
interface and differing generic branches without introducing a downcast.
Two unchanged compiled-consumer checks verify virtual and generic clone calls
against each rebuilt assembly. Eleven recognition guards reject changed equality
or non-copying clone bodies; 25 methods retain debugger IL spans.

Record reconstruction retains custom members, copy constructors and renamed
clone aliases. Only verified compiler equality scaffolding is regenerated. A
renamed record gains the compiler's native `<Clone>$` method beside its retained
alias; the tests cover callers and the rebuilt inheritance hierarchy, not arbitrary
external subclasses that override only the alias. The `RecordClasses` setting
controls this C# output and is disabled by the Visual Basic frontend. This adds
AST/output support; it does not add record parsing to the legacy NRefactory parser.

`Invoke-ConstructorStateRegression.ps1` rebuilds renamed capture objects created
before a base constructor call. A private forwarding constructor retains the same
capture object through argument evaluation, the base call, and the remaining body.
For longer preparation sequences, a private state object and preparation method
retain saved values and propagate parameter updates before forwarding.

The fixture passes 209 original/rebuilt checks with one and four workers. It covers
generic captures, shared delegate targets, mutations made by the base constructor,
callbacks escaping a failed constructor, cached delegate identity, null values,
existing overload arities, and exact effects/exceptions at allocation, argument,
base-body and derived-body steps. A separate capture used only after the base call
exercises saved arguments and a `ref` update during preparation. Both paths also
run the full AST transformation with debugger spans enabled.

The transformation does not move instance field/property initializers across
preparation, or move preparation that uses `this` into a static helper. The general
preparation path currently handles top-level declarations and expression statements;
it excludes `out` parameters, ref locals, ref-like state fields, and direct parameter
captures that cannot be represented in its helper. Public constructor signatures
remain intact; the generated private helpers add source implementation members.

`Invoke-FriendAssemblyRegression.ps1` checks source export of a signed library and
its friend executable. Exported projects rebuild unsigned, so their assembly-info
files use an unkeyed `InternalsVisibleTo` name when that friend's full public key
matches every exported assembly with the same simple name. Compatible copies and
versions are accepted; absent friends, conflicting keys, unsigned namesakes and
malformed declarations keep their original values. Original assembly metadata and
ordinary C#/VB decompilation remain unchanged. Re-signing exported projects with a
different key requires updating the source friend declarations accordingly.

The original and rebuilt fixture pass 22 runtime checks, covering internal generic
types, an enum, an interface implementation, constructor overload selection,
callbacks and exception identity. Both SDK projects (one/four workers) and legacy
projects are rebuilt and executed. An isolated library export retains keyed grants.
Another 66 checks exercise duplicate versions, conflicting keys, quoted/escaped
names, malformed public keys, and repeated C#/VB export/keep-all/default modes
against the same metadata. The .NET Framework parser reduces a full public key to
a token; projection compares the full declared key instead and leaves invalid keys
for diagnosis without aborting export.

`Invoke-DuplicateAssemblyRegression.ps1` checks console batch export of two
deployments with identical Runner/Plugin/Library assembly identities and different
generic payload types and behavior. Each plugin resides in a subfolder, and a
separately exported `Library_orig.dll` contains another implementation. All seven
inputs must remain in the solution. Both applications rebuild and return their
distinct expected results with SDK projects (one/four workers, reversed input
order) and legacy projects. Another 564 checks use the deployed resolver to verify
type resolution, self references including backups, identity mismatches and
concurrent calls from different deployment folders.

Console resolution selects exact identities from its input set before using the
ordinary resolver. A file named for the assembly takes precedence over backup
filenames. Matching copies are selected by source folder, parent folders, then
nearby subfolders; unresolved ties use a stable path order. Self references stay
with their own input. The index is built once, and selections are cached separately
for each source module without re-reading assembly files. Explicit application
redirects apply before this selection. The application-config regression also
exports both the old and redirected libraries, then verifies SDK/legacy consumers
still use the configured version. This change covers console resolution; the GUI
document resolver has a separate implementation.

`Invoke-LoopExitRegression.ps1` checks a loop whose normal exit forwards to code
also reached by an early body exit. The emitter reorders the shared conditional
tail without changing the input's behavior. Original and rebuilt SDK exports with
one/four workers must agree on all 396 return values, side effects, exceptions and
cleanup sequences. Another 24 control-flow graphs cover forwarding chains,
inverted conditions, cyclic continuations and block ordering. The full debug
pipeline must keep the shared tail outside the loop and retain its source spans.
Loop expansion excludes every block reachable from the normal exit, including
shared blocks that are not dominated by that exit's forwarding branch.
