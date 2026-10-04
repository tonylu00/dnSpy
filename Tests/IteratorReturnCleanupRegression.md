# Protected iterator exhaustion and cleanup

Older iterator compilers may store `false` before calling generated finally
helpers. The native converter recognizes that layout only inside its validated
outer dispose-and-rethrow fault region. It commutes the nonthrowing constant
store across adjacent, exact receiver-only finally calls. The return variable
must not escape by address; helper order, branch targets, node identities and
debug spans stay intact. Constants other than zero, other receivers, unknown
calls, intervening labels and unsupported graphs retain their existing behavior.

Protected flat iterator bodies require proven CFG/resume ordering before the
lexical finally conversion. A successful rewrite witness alone cannot establish
cleanup correctness: an empty finally region outside the yields can still compile.
Unsupported ordering retains the explicit state machine.

`IteratorReturnStoreRegression` checks accepted store/leave/helper-chain layouts,
idempotence, node identity and rejection boundaries against the actual core.
Build it with `RuntimeDirectory` pointing to the frozen tested plugin runtime.
Its helpers use dnlib and the portable IL AST.

Run `Invoke-IteratorReturnCleanupRegression.ps1` with `DnSpyConsole` and a fresh
`OutputDirectory`. The synthetic emitter models the checked older compiler's
terminal reference-reset/disposal shape, places the return store before or after
cleanup, and preserves real edges while reversing or rotating basic blocks.
All six emitted inputs must match the original fixture before export. Each is
exported with one and four workers, rebuilt and compared through 224 event traces:
UTF-8/CRLF/tail behavior, lazy acquisition, cached Current, every early-stop
position, exhaustion, exception identity, acquisition/read/dispose failures,
unstarted disposal and repeated cleanup. Source hashes must agree by worker count.

`Invoke-EtsLaunchArgumentIteratorBehaviorProbe.ps1` uses the same trace harness
as an unchanged caller in separate Framework processes for ETS6N and ETS6C.
It binds the restored private `a(Stream)` parser by exact type/signature and
assembly identity; dependencies must match their full original identities.
It never constructs the watcher or invokes an ETS entry point. Launcher hashes
must remain unchanged. This parser probe does not establish ETS startup,
password-project persistence, unchanged-App compatibility or complete generated
state metadata restoration.

`GeneratedSourceInspection/Inspect-StateSourceGaps.ps1` rechecks retained owners
from the pinned native state-gap worklist. It validates physical/map/context
provenance, uses one child at a time, and snapshots its producer. Partial positive
witnesses do not replace a complete source audit or retire naming candidates.
