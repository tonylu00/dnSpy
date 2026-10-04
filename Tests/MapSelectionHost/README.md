# Native selected-map composition

Use this host when the validated NameCandidates preflight and the committed
contract-aware map selector were built at different revisions. This links the
committed native selector and path helpers directly, then runs selection through
the independently validated preflight DLL. It does not compile repository
working-tree changes or alter the canonical application map.

Build with `-p:SelectionSourceDirectory=<clean committed tools/NameCandidates>`
and `-p:ValidatedToolDirectory=<validated NameCandidates output>`. Pin those
sources and binaries alongside the resulting host. CS0436 is expected because
the linked selector intentionally supersedes the older selector in that DLL.

Arguments: `<contract-manifest> <application-map> <fresh-selected-map>
<physical-module-path> [...]`. Select complete mapped contract families. The
normal native preflight checks physical identities, SDK bindings and scoped
aliases before publishing the selected map. A failed selection publishes no
map. Assembly simple names never collapse distinct compatibility paths.
