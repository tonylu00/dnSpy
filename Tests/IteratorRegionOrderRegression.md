# Iterator exception regions after block permutation

The native Microsoft iterator converter first tries its existing reconstruction.
If that fails on a flat body with proven Dispose/finally contracts, it retries
after ordering the basic blocks of the actual control-flow graph. Fall-through
edges become explicit. A yielded state's proven resume target is an additional
ordering edge; it does not replace any real branch. Dominators and natural loops
keep complete loop bodies before cleanup, independent of branch polarity.

The retry accepts at most 1,024 blocks, supports only locally proven constant
yield-state assignments, and retains unreachable blocks. It keeps the existing
exception-region branch and residual state-read guards. Unknown targets, state
transitions, nested IL regions or unsupported graphs retain the explicit state
machine. Input assemblies and source-name maps are never modified.

Run `Invoke-IteratorRegionOrderRegression.ps1` with the tested console and a fresh
output directory. Its synthetic emitter models older compiler Dispose bodies by
removing Roslyn's checked tail reference resets and terminal write, then reverses
or rotates blocks inside the original fault region. Real fall-through branches,
branch targets and exception-handler boundaries are preserved. Original and
permuted inputs must produce the same baseline before testing exported code.

The fixture exercises nested and sequential enumerations, both loop branch
polarities, lazy construction, cached Current, every early-stop position, natural
exhaustion and failures during acquisition, MoveNext, Current, Dispose and tail
work. Each run compares 176 complete event traces through a SHA256 digest. Plain,
reversed and rotated inputs are exported with one and four workers, compiled and
executed. These cases do not cover resumption after disposing an unstarted
protected iterator or arbitrary generated-state metadata contracts.

`Invoke-CvNextStoreIteratorBehaviorProbe.ps1` compiles one unchanged caller against
the original ETS 6.3 CvNext binary. The identical caller then runs against original
and rebuilt modules in separate Framework processes, resolving original
dependencies by exact assembly identity. It checks ten store-file results and
types, every early-stop prefix, cached Current, repeated disposal, stable
exhaustion, empty/missing stores and nongeneric enumeration. All file fixtures
stay under a fresh test directory. This validates one real iterator and its
restored callable metadata, not full ETS startup, project conversion, SDK/App
compatibility or complete generated-state contracts.

The checked 39-owner ETS evidence and actual CvNext compilation are recorded in
`NameReview/2026-09-12-application-pass/iterator-region-order-verification.json`.
Whole-application naming, consolidated compilation and runtime validation remain
separate requirements.
