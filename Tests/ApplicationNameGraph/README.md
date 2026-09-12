# Application naming graph

Read-only .NET metadata and Roslyn syntax index for reviewing a complete exported
application before applying names or rebuilding it. It uses the exporter's
physical-input, application-config and compatibility-context resolvers. It never
loads an analyzed assembly for execution.

```text
dotnet build Tests/ApplicationNameGraph/ApplicationNameGraph.csproj -c Release
dotnet Tests/ApplicationNameGraph/bin/Release/net8.0/ApplicationNameGraph.dll export/dnspy-export-map.xml names.xml new-graph --contexts contexts.xml --config application.config --asm-path references
python Tests/ApplicationNameGraph/query.py build new-graph graph.sqlite
python Tests/ApplicationNameGraph/query.py show graph.sqlite m0001:0x06000001
python Tests/ApplicationNameGraph/query.py callers graph.sqlite m0001:0x06000001
python Tests/ApplicationNameGraph/query.py methods graph.sqlite m0001 review
python Tests/ApplicationNameGraph/query.py body graph.sqlite m0001:0x06000001
```

The NameCandidates project normally lives in a sibling `de4dotEx` checkout.
Override `-p:NameCandidatesProject=/path/to/NameCandidates.csproj` if needed.
Commands are portable .NET/Python; there is no PowerShell or ETS dependency.
Windows regression was executed locally; macOS/Linux execution remains unverified.

Outputs are JSON Lines plus a manifest, and the optional SQLite index makes
repeated caller/source queries inexpensive. Always choose fresh output paths.
Symbol IDs are graph-local physical-module ID plus metadata token, not assembly
name plus token. The manifest records input SHA256/MVID, source projects, config,
contexts, search paths, retained binary dependencies and per-module coverage.

`symbols.jsonl` contains types, methods, fields, parameters, IL local types and
string constants. `edges.jsonl` records instruction offsets and actual method/
field resolution, including external targets and unresolved edges. `families.jsonl`
contains interface/override groups and their blockers. `source.jsonl` maps tokens
to source hashes, declarations and variable/parameter/foreach/catch/pattern
bindings. Spans use UTF16 code units, as Roslyn does. Query results retain all
source locations; ambiguous declarations must be resolved before editing.
`body` verifies the source hash and reads the exact declaration span, preserving
CRLF and UTF16 offsets before formatting its output. Multiple symbol IDs can be
supplied in one call. `test_query.py` checks BOMs, non-BMP offsets and stale-source
rejection. Python 3.9 or later is required.

This is evidence for a naming pass, not a complete dynamic call graph. Virtual
dispatch, reflection and delegated calls can add runtime targets. An unresolved
edge is never bound by matching a name/signature with its type scope ignored.
Identical MVIDs or hashes do not merge physical modules. Metadata reference
resolution and source-level semantic binding are different checks: syntax
locations alone are not permission to replace every matching identifier.

The regression creates same-identity libraries in separate physical deployments,
valid and wrong-vendor callers, field uses, source bindings and a retained binary.
It proves the wrong-signature edge stays unresolved and verifies UTF16 spans with
a non-BMP character before the declarations.
Field MemberRefs implement both dnlib's method and field interfaces; the graph
uses the metadata signature to classify them. The fixture covers field references
through both compatibility deployments and rejects the wrong vendor's signature.

```text
dotnet run --project Tests/ApplicationNameGraphRegression -c Release -- Tests/ApplicationNameGraph/bin/Release/net8.0/ApplicationNameGraph.dll fresh-regression
```
