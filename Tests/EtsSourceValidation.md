# ETS source recompilation milestones

Validation on 2026-09-10 used original SDK callers and separate rebuilt trees.
The 6.3 regression build and live test passed before the 6.4 live test.

| Check | ETS 6.3 source36 | ETS 6.4 source11 |
| --- | --- | --- |
| Batch inputs | 111 | 176 |
| Managed projects compiled | 107 | 172 |
| Native inputs retained | 4 | 4 |
| SDK contract audit differences | 0 | 0 |
| Staged assemblies and satellites | 377 | 397 |
| Unchanged MCP add-in types loaded | 407 | 410 |
| Live project | test-mcp / P-6790 | isolated copy of test-mcp / P-6790 |

Both live copies opened with Chinese UI and MCP 4.13.1 ready. Read-only SDK
checks returned project details, all 29 devices, 502 group addresses and sampled
communication-object metadata. The 6.4 test also read sampled parameter metadata.
The 6.4 run used copied project/product stores and a temporary settings profile;
cleanup verified the original profile and 1,877 original data-file hashes.
Both ETS processes and test daemons exited, and installed add-ins were restored.

The 6.4 export includes compatibility assemblies in explicit physical contexts.
Its source map contains twelve method aliases, ten derived from reviewed 6.3
reference candidates. Runtime names/signatures are restored by the metadata task.
Shared satellite paths select the original destination's version independently
of project order. Reference-only projects are recorded separately when staging.

Standalone SDK loading must use the host's actual configuration and binding
redirects. An exact-identity probe without ETS6N.exe.config failed equally on
pristine and rebuilt 6.4; applying that configuration resolved the dependency.

Evidence folders on the validation machine are `D:\knx_analysis\ets63-source36-live1`,
`D:\knx_analysis\ets64-source11-live1`, and the corresponding source-validation,
SDK-audit and staging manifests. Source trees are `D:\git\ets63-api-source36`
and `D:\git\ets64-api-source11`.

These are compilation, metadata and exercised-runtime milestones. They do not
prove equivalence of every body/custom attribute, every third-party app, password
projects or physical KNX operations. The test project was not password protected.
Compiler warnings and existing development-add-in/network/MyKNX warnings remain.

## Source-only parameter map follow-up

The subsequent source37 (6.3) and source12 (6.4) builds added a descriptive
`schemaVersionValue` argument alias to the schema helper. The full 6.3 build and
expanded audit passed before starting 6.4. Both retained the same input/project
and staging counts above, with zero SDK contract differences. The expanded audit
also checks enum/string constants and event accessor associations.

Both staged trees loaded the unchanged SDK-built MCP add-ins (407/410 types),
and the automation patcher recognized their hash-verified rebuilt provenance.
Comparisons against the live-tested source36/source11 Common assemblies found no
normalized method-body differences across 1,305 methods in 6.3 and 1,814 in 6.4.
Those comparisons include scoped signatures, method flags, IL, locals and
exception handlers; they do not compare every attribute or resource.

Latest source trees: `D:\git\ets63-api-source37`, `D:\git\ets64-api-source12`.
Staged trees: `D:\knx_analysis\ETS6.3_source37`, `D:\knx_analysis\ETS6.4_source12`.
Evidence: `ets63-api-source-validation37`, `ets64-api-source-validation12`,
`ets-sdk-loader3` and `parameter-alias-bodycheck1` under `D:\knx_analysis`.
These follow-up trees were validated offline; the live checks above remain tied
to source36/source11. Original installations and project data were not changed.

The generic de4dot NameCandidates scanner independently recovered ten of the
reviewed 6.4 method aliases using 6.3 as reference. Its guarded source-map converter
also exported and rebuilt the four affected modules with zero SDK differences.
It retains relative physical module contexts and rejects ambiguous candidates;
it does not claim to recover every original obfuscated name.
