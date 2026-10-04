# Mixed exception regions in protected iterators

`Invoke-IteratorMixedRegionRegression.ps1` builds an iterator containing a
prefix catch, a cached LINQ predicate, a nested non-yielding foreach and a
payload catch/conditional before yielding. It compares original and rebuilt
behavior for unstarted, partial and exhausted enumeration, injected errors,
cached Current and cleanup order.

The synthetic emitter permutes surrounding basic blocks while preserving
complete user EH intervals, their entry fall-through and whole continuation
blocks. It retains the original max-stack bound because dnlib cannot compute
it for these reordered nested handlers. Each emitted input is executed by the
CLR and compared with the compiler baseline before export. ETS inputs are
never changed by this emitter.

Run against a complete console directory containing the newly built ILSpy
plugin:

```powershell
Tests/Invoke-IteratorMixedRegionRegression.ps1 `
  -DnSpyConsole <runtime>/dnSpy.Console.exe `
  -OutputDirectory <fresh-directory>
```

The runner requires reconstructed yields/using blocks, identical source across
workers 1 and 4, successful source builds and matching behavior in plain,
reverse and rotate layouts. The guards reject cross-region entry, non-leave
external exits, exits from cleanup/filter regions, duplicate labels, excessive
depth/size, state/current access, yield/resume work and generated cleanup calls.
The existing exhaustion-store guards additionally cover unrelated preceding
regions and rejection of an intervening region.

`Invoke-AppMenuIteratorBehaviorProbe.ps1` builds one caller against the original
ETS ViewModel identity and runs it against original and rebuilt binaries. It
invokes the exact private manufacturer-menu iterator and exercises real menu
constructors and Rx subscriptions. The manager constructor is bypassed and
dependencies are proxies; this does not prove installed-App or live ETS
compatibility. Loaded assembly identity, physical path and hash are recorded.
