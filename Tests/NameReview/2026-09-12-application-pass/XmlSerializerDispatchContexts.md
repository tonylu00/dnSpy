# XML serializer dispatch contexts, map v390

Native incoming-reference inspection covered all 6,718 methods and 496,037
instructions of the root, CV 4.0 and updater serializers independently. The old
type summaries cap displayed callees at 40, which hid attribute readers inside
large methods. de4dotEx `7af4b44d` adds uncapped incoming references to
`--inspect-methods`; it records physical scope and excludes external/dynamic
claims. Portable tests cover operands, metadata, signatures and physical twins.

`xml-dispatch-context-evidence01.json` records the exact physical identities,
tokens, incoming references and native instruction chains for all 26 previously
pending tables. `ReadElementString -> enum helper -> box` proves enum-element
roles. `Reader.Value -> enum helper -> containing-object setter` proves attribute
roles. Generic `Read1_Object` also invokes these helpers; role names do not imply
exclusive use. Existing generated reader method names are preserved.

The checked v390 block adds 109 aliases: 26 table fields, 26 XML input parameters,
52 XML-name/dispatch-index locals and five writer enum snapshots. No requested
name was suffixed by the native updater. Full identity, contract manifest and SDK
whitelist checks pass. Five writer scope rows merge explicitly with their earlier
review; no earlier aliases are replaced.

`xml-serializer-selected-coverage04.json` measures the canonical cumulative ledger
filtered to these physical modules, rather than combining historical delta rows.
It reports 60 named input parameters and 125 aliased locals out of 218 slots; the
other 93 are the proved unused slots. Historical unresolved Dotfuscator support
methods remain explicit. These supplied ledger rows are not whole-application
coverage or a statement that every existing generated symbol needs renaming.

`xml-serializer-local-dispositions01.json` resolves all 60 previously pending
slots: five single-assignment enum snapshots and 55 slots with zero IL references.
It additionally reviews 38 unused slots in the duplicate enum readers. Unused
slots receive no invented alias. These are retained slots in the processed input,
not application state, and this review does not modify IL or binaries.

Reproduction uses `xml-dispatch-context-config01.json`. Generate its native
`--inspect-methods` reports in the physical contexts specified by `Input`:
the selected reader tokens are in the three committed
`xml-serializer-dispatch-bodies-*.json` reports; caller tokens come from their
uncapped `IncomingReferences`; writer bodies are in the three committed
`xml-serializer-array-callers-*.json` reports. Then run:

```text
python prepare_xml_dispatch_contexts.py --config xml-dispatch-context-config01.json --spec <fresh-spec> --evidence <fresh-evidence> --locals <fresh-local-report>
python prepare_physical_review.py --spec <fresh-spec> --output <fresh-review>
dotnet <NameCandidates.dll> --contract-references <contract-references63-v3.json> --update-map <fresh-review> <v389-map> <fresh-map> <fresh-update>
dotnet <NameCandidates.dll> --contract-references <contract-references63-v3.json> --check-map <fresh-map> <fresh-check>
```

Both preparation helpers only write review/evidence files and reject stale input
hashes, wrong physical paths, conflicting native signatures or unsupported roles.
All outputs require fresh paths. The native CLI build includes the existing,
uncommitted delegate-scope changes from another agent; those files were preserved
and excluded from these commits.

This is a naming checkpoint. The prior three focused serializer projects compile
and original/rebuilt helper behavior matches 1,524 cases, but v389/v390 aliases
have not been exported again. The 64-project baseline is a separate export.
Consolidated application build, broad unchanged-App/SDK runtime compatibility
and ETS 6.4 verification remain pending until the application-wide map freeze.
