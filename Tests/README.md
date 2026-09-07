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
.\Tests\Invoke-StructuredFilterRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-structured-filter-check
.\Tests\Invoke-TypedAwaitCatchRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-typed-catch-check
```

The structured-filter test checks 8,390 cases in compiler-produced and reordered
filter bodies, with both one and four export workers. It verifies exception
identity, filtering before unwinding, acceptance, rejection, throwing filters,
property preparation, null checks without overloaded equality, and real async
suspension. Twenty filters retain their debugger offsets; 216 shape/scope checks
cover branch polarity, nested negations, exposed locals, unsupported preparation,
numeric predicates, typed/boxed exception-copy chains, overwritten aliases and
unchanged IL when a match fails. Preparation stays in the filter expression so it
also executes when the handler is not selected.
Nested Boolean decisions include an out-of-line comparison that branches back to
a shared result. Property reads execute once, and rejecting or throwing predicates
still run before unwind. The checks reject cycles, incoming join branches, missing
or inconsistent result stores, and preparation that would cross an earlier call/read.
Conditional Boolean updates include AND/OR paths with callbacks that read and
mutate the local by reference, including throwing before the final assignment.
The emitted fixture inlines four helper predicates into the filter; values seen
during callbacks and subsequent unwind must match the compiler-produced original.
Nullable preparation retains one getter evaluation and the stored value for the
later HasValue check, including null, zero-valued enums and throwing getters.
Only the known readonly Nullable operations accept an assignment as their receiver;
foreign types, mutable/ref calls and incompatible signatures remain guarded.
Private constant comparison temporaries may be folded only when they have one read
and no uses outside the filter. Nullable integer and enum array loops, including
jagged arrays, must retain nullable element types when reconstructed as foreach.
Unnamed typed catches include nested address-space decisions, changing property
values, throwing getters and unsigned bounds overflow. The runtime fixture may
collapse to a straight-line Boolean predicate; separate IL guards retain ETS's
shared-label form with integer 0/1 stores and a computed Boolean leaf. They reject
escaping exception inputs, inconsistent stores, incoming joins and cycles. The
fixture also retains a local-function helper with captured value-type environments;
all helper declarations and references must receive matching legal source names.
Conditional preparation covers repeated getters, shared rejection/acceptance labels,
direct local-address stores, and the prepared value observed by reference during
unwind. Only the selected path may consume an exception retained outside the filter;
its flag must have an adjacent reset and no other uses. Incoming branches, cycles,
foreign addresses, volatile stores and preparation across earlier reads are rejected.
Async handlers with another catch and a normal alternative preserve rethrow identity,
cleanup failures and cancellation, including suspension before and inside the catch.

The typed-await-catch test runs 26,204 cases for each exception-wrapping setting:
enabled, disabled, absent, and an attribute with no named arguments. Original and
rebuilt exports with one/four workers must preserve the setting, typed/derived/
generic catch selection, immediate and suspended failures, exception identity and
stack, cancellation, cleanup ordering, and errors on the normal path outside the
catch. Readonly exception observations before/after awaits retain the original
typed capture; callback failures and cancellation preserve their identity and order.
Filtered handlers preserve accepting, rejecting and throwing predicates, including
generic captures, exception reads after awaits, and filtering before stack unwind.
Deliberately unwrapped payloads are tested at a synchronous boundary so they cannot
escape onto the thread pool; typed filters preserve raw payload selection and identity.
One hundred fourteen scope/debug checks cover readonly captures, copied selection flags,
mandatory filter captures and retained filter resets. They reject incoming jumps,
exposed dispatch/capture locals, writes/ref access, escaping flag copies, conditional
or missing filter captures, fallthrough guards and incompatible catch-local casts.
Alternative paths remain outside the recovered catch, retaining their selection flag;
other handlers cannot read, write or filter on that flag. The checks also verify that
normal-path effects and exceptions stay outside all catch boundaries.
The export retains RuntimeCompatibility and
explicitly disables compiler-added wrapping when the input attribute is absent.

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
The detached fixture also places result collection before both resume bookkeeping
and the await factory. Its branched resume must recover as async source, execute
the factory once, and preserve success, failure, cancellation and bypass paths.
Loop cases place the factory between result collection and resume bookkeeping.
They check repeated factory calls, suspension and failure on either iteration,
and cancellation after resuming the first iteration. A resume-only application
effect keeps its original state machine. Both one- and four-worker exports rebuild
and execute; debug checks retain await spans and leave input IL unchanged.

`Invoke-GuardedAwaitRegression.ps1` covers a detached suspension after a nested
try/catch whose paths all exit, and state dispatch into a reordered try entry.
Original and one/four-worker source rebuilds run 325 cases with 1,297 assertions:
repeated suspension, synchronous factory faults, task faults and cancellation,
filtered and ordinary handlers, cleanup order, exception identity and bypass.
Compiler state guards in nested catch/finally cleanup are removed throughout the
method. Conditional application cleanup, nested cleanup and cleanup exceptions
must keep their effect order, selection and precedence over the pending failure.
Twenty-three guards check fallthrough rejection, entry boundaries, switch edges,
internal targets, bounded normalization, debug spans and disabled async recovery.

`Invoke-JumpedAwaitCatchRegression.ps1` checks catch continuations reached by a
jump past a normal exit, including a shared jump after the try/catch. Original
and one/four-worker source rebuilds run 22,500 cases and 134,712 assertions for
loop break/continue/return, suspension, faults, cancellation, raw wrapped payloads,
exception identity and rethrow stacks. Thirty guards preserve the normal exit,
join and jump spans, and reject other entries, fallthrough, capture/flag writes,
cross-region targets and unsupported dispatch alternatives.

`Invoke-FallThroughAwaitRegression.ps1` covers a loop whose negative completion
test falls through to GetResult while suspension and resume bookkeeping occupy
separate blocks. Original and one/four-worker source rebuilds run 8,000 cases with
35,440 assertions for zero to three iterations, repeated suspension, synchronous
and task faults, result observers, cancellation and cleanup precedence. Twenty
guards verify explicit/fallthrough completion paths, input IL and debug spans,
and reject extra incoming edges, resume effects, escaping writes, wrong awaiter
operations and mismatched exception regions. Existing async layout and iterator
regressions also cover the shared normalization path.

`Invoke-SplitCatchRegression.ps1` covers a lifted catch fragment that branches to
an awaited fallback outside the fragment. An exact captured rethrow permits
reconstruction even when the fragment itself has no await. Original, emitted
raw-throw input and one/four-worker source rebuilds each run 20,480 cases with
106,264 assertions for generic typed selection, normal/fallback execution,
suspension, observer faults, cancellation, raw wrapped values and rethrow stacks.
Eighteen guards preserve loop break/continue and return targets, capture identity
and debug spans; they reject outside entries, capture/selector mutation, escaping
temporaries, nested functions/handlers and missing or mismatched rethrow evidence.

`Invoke-GroupedAwaitCatchRegression.ps1` covers multiple typed or generic catch
handlers sharing a selector and pending-exception storage. It verifies both
if/else and switch dispatch, independent capture names, and switch exits during
partial recovery. Original and one/four-worker source rebuilds run 76,832 cases
with 472,240 assertions for retries, suspension, handler selection, exceptions
escaping sibling catches, cancellation, wrapped raw values and rethrow identity.
Ninety-two guards reject ambiguous selectors, unowned or escaping captures,
external entries, normal-path effects and unsafe switch exits; they also check
name collisions, sparse selector values and debug metadata.
Incomplete reconstruction also retains the original implementation. The tests
cover side effects before await result collection, nested iterator cleanup,
early disposal, captured owner references and valid names for retained helpers.
Awaited finally blocks check cleanup after success, failure and cancellation,
suspended cleanup, and cleanup exceptions taking precedence over body exceptions.
Captured delegate caches retain their original zero-initialized storage.

`Invoke-NestedAwaitFinallyRegression.ps1` checks 8,750 cases / 34,986 assertions
for nested, conditional, mutually exclusive and sequential cleanup. Original and
rebuilt one/four-worker exports must agree on suspension, cleanup order, skipped
later regions, exact exception or raw payload identity, stack preservation and
cancellation. Twenty AST checks cover debug spans, observed/captured temporaries,
missing initialization, resets inside protected/cleanup code and outside jumps.
Independent cleanup regions may share a compiler exception temporary only when
each initializes and consumes its own capture. Initialization can precede constant
return-flag stores; calls and control-flow edges cannot intervene. Resets needed by
another unrecovered region remain until that region is recovered.

`Invoke-IndependentAwaitCatchRegression.ps1` verifies sequential and mutually
exclusive catches that share compiler exception storage. Original and rebuilt
one/four-worker exports pass 22,500 cases / 132,744 assertions for success, faults,
cancellation, raw thrown payloads, suspension, repeated observation and optional
rethrow. Each catch observes the same exception before and after its await; a
failure stops later work and retains its original stack. Twenty-two AST guards
check independent initialization/selection, outside reads, captures, references,
writes, incoming jumps, rethrow observers, debug fields and naming collisions.
Readonly captures receive a separate local identity only after proving that the
other catch stores its own exception before selecting its continuation. Resets
needed by another region stay in place; input assembly bytes remain unchanged.

`Invoke-SavedStructAwaitRegression.ps1` checks ordinary async methods that clear a
saved struct on success and failure. Original and rebuilt one/four-worker exports
pass 128 cases / 632 assertions, including generic structs, value/reference/null
contents, suspension, synchronous/task failures, cancellation, observer failures
and constructor counts. Sixteen guards verify both completion paths reject shared
static clearing, mismatched types and extra calls, preserve await debug spans and
leave input IL unchanged. Exact-type initialization of a state-machine-owned field
is recognized as cleanup without calling its struct constructor.

`Invoke-DetachedRethrowRegression.ps1` moves seven compiler raw-object rethrows to
detached tails, with two sharing an existing tail. The original, reordered input
and rebuilt one/four-worker exports must agree on all 8,750 cleanup cases / 34,986
assertions. Ten AST guards cover shared tails, dead incoming jumps, extra effects,
fallthrough, wrong values, exception-region boundaries, nested functions,
duplicate labels, other live entries and cleanup debug spans. The transform
requires a complete captured-rethrow sequence and matching exception regions;
tail removal also requires no fallthrough or remaining live entry. The existing
dead-jump proof runs before rethrow recovery so unreachable branches cannot keep
an otherwise unused tail alive. Both input assembly hashes remain unchanged.

`Invoke-SingleIterationTryLoopRegression.ps1` verifies removal of an artificial loop
whose try and every catch end with a break targeting that loop. It preserves nested
breaks and finally blocks, rejects continues, early exits, labels, local declarations,
repeated iterations, gotos and trailing statements, and retains debug spans. It
compiles original/transformed syntax and compares 36 runtime traces, including a
throwing finally. Exposing the adjacent cleanup lets async iterator recovery restore
the awaited finally instead of emitting a yield inside a catch-protected try.

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
ordered boolean comparisons and unsigned negation. Its 315 checks cover integer
boundaries, signed and unsigned ordering, small enum promotion, signed shifts, both operand evaluations and
exceptions from the second operand. These IL operations need valid C# numeric
operands while preserving their original width and evaluation order.
Boolean stack values converted to single/double precision also retain one operand
evaluation, exceptions, numeric overload selection and their boxed result type.
Boolean-to-byte/sbyte/short/ushort conversions also retain their narrow result
types in returns, boxing, overload resolution and byte-array stores. Null and
out-of-range arrays must still evaluate the value before throwing.
Unsigned widening from a signed 32-bit stack value must zero-extend through uint;
the tests include negative constants, signed enums, small integers, callback
failures and a checked addition nested inside the unchecked conversion. Existing
64-bit input conversions must preserve all their original bits.

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
One- and four-worker exports also preserve parameterless default properties on
ordinary and imported types, including their names, dispatch IDs and return
marshalling. `IndexerName` is synthesized only for a real indexer; named and
explicit-interface indexers retain their metadata names and runtime dispatch.

`Invoke-EmbeddedEventRegression.ps1` builds real embedded interop types through
the C# compiler's `EmbedInteropTypes` option. Empty event wrappers carry an import
flag without a GUID in that metadata. Their compilable C# declarations retain
the explicit type-identity scope/name and event-source/provider attributes while
omitting `ComImport`. Raw metadata and the "show all members" view retain the flag.
This applies only to empty, nongeneric, top-level wrappers with well-formed
identity/event attributes; ordinary COM contracts keep their GUID and import flag.

Original and one/four-worker rebuilt assemblies pass 54 checks for runtime type
equivalence, GUIDs, event-source/provider identity, inheritance, and casts across
assemblies using managed implementations. Thirteen source guards check malformed or
missing attributes, added members/bases, nested/generic types, and unchanged input
metadata. The rebuilt wrapper's `IsImport` reflection flag is deliberately absent;
no COM server is activated and no new GUID is invented.

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

`Invoke-ConstructorInitializerRegression.ps1` covers preparation after instance
field initialization. A preparation method in the first base argument returns that
argument and declares an `out` state variable shared by the remaining arguments
and constructor body. This preserves field initialization before preparation,
including what the base constructor sees through virtual calls. It requires a
first argument passed by value (not a `ref`/`out` parameter) and keeps the existing
closed-control-flow and instance-access guards.

Its emitted fixture retains a renamed capture with an observable constructor.
Original and one/four-worker rebuilt executions check 201 assertions for ordered
initializers, parameter updates, generic/null values, shared escaped callbacks,
and exact failures at each step. Twelve debug/guard checks cover declaration
matching/output, unavailable initializer recovery, invalid argument boundaries,
and unchanged input IL. Adjacent preparation tests also cover lambdas using saved
locals without capturing the preparation method's `out` parameter. The added out
declaration support is for AST/source output; it does not extend the legacy parser.

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

`Invoke-ConverterSourceRegression.ps1` checks repeated namespace components,
namespace prefixes, and same-name types alongside arrays stored in object locals.
SDK exports with one/four workers must match the original's 64 array cases,
including aliases, null paths, generic/value/reference elements, side effects and
injected exceptions. Five full/nested/isolated AST scope cases verify imports and
debugger namespaces; three array methods must retain typed temporaries and debug
spans. Explicit namespace syntax supplies the traversal scope when present.
Combining a local store into an assignment expression requires matching variable
types, preserving the original duplicated stack value's type after a wider store.

`Invoke-AsyncIteratorRegression.ps1` verifies C# async enumerable/enumerator
reconstruction, including generic instance methods, lazy execution, real await
suspension, multiple yields, early disposal, awaited cleanup, exceptions and
cancellation. Original and rebuilt one/four-worker exports each pass 14,348 checks.
The filtered iterator covers 576 combinations of synchronous/suspended moves and
disposal, skipped values, early stops, exceptions and cancellation. It checks exact
input/read counts, output order, failure identity and cleanup precedence.
Four additional inputs rearrange cancellation selection, disposal, completion,
yield signalling and the shared return, including a completion path split around
the yield signal. They also cache the state at each yield and rename the seven state
machines, their fields and interface implementation methods. All five inputs must
produce the same results. The emitter updates both metadata-table member references
and generic-context references embedded in method bodies.

Another 60 checks per input verify source/debug spans, unchanged input IL, disabled
settings/language capabilities, unexpected constructor effects, invalid yield
signals, altered token predicates, missing cancellation attributes and changed
token cleanup calls, extra completion effects, cyclic exit branches, shared-data
clearing and mismatched struct cleanup types. These
unsupported shapes keep the original state machine.
The Visual Basic frontend retains state machines because it cannot express C#
async-iterator syntax. Other unsupported iterator layouts also remain available
for further recovery; passing these tests does not establish complete ETS behavior.

The iterator pass identifies fields through their constructor, interface methods,
promise completion and token flow rather than generated names. It checks all nine
symbolic default/equal/distinct token combinations before replacing cancellation
selection, and validates the corresponding linked-token disposal. Successful
recovery shares the existing await conversion and awaited-finally restoration,
emits `async` with `yield return`, and hides the inlined state machine. Both async
and iterator decompilation settings must be enabled. Exit matching follows branches
without changing the input IL, checks both cancellation-disposal paths converge,
and requires every node outside the main handler to belong to a validated exit.
Redundant branches to the immediately following resume label are removed before
counting incoming edges; other incoming edges and exception-region exits remain.
Completion recognizes exact-type initialization of the state machine's own saved
struct fields, including configured enumerators, without discarding calls or
clearing shared data.

`Invoke-EtsAsyncChannelRegression.ps1` takes original/processed Falcon assemblies,
the untouched exported `Async.cs`, and a new output folder. It compiles that source
and runs only the channel reader helper in separate processes for all three targets.
Each target must pass 198 cases / 1,697 checks with identical records: immediate and
suspended waits/reads, fault identity, swallowed cancellation, all nine token pairs,
linked-token cancellation, completion and early disposal. The runner verifies the
source and assembly-copy hashes. It does not start ETS, open a project, or connect to
a network or bus; these results establish helper behavior, not whole-application
equivalence.
