# Original/rebuilt serializer behavior

After compiling the exported serializer projects, run the portable RVA tool's `--compare` mode to produce a checked metadata/storage report.

Prepare one physical case manifest per module with `python Tests/prepare_xml_serializer_cases.py --reader <native-reader-IL.json> --writer <native-writer-IL.json> --application-root <tree> --output <fresh-cases.xml>`. Native inventories must have identical physical identities and current hashes. Reader inputs come from reviewed IL string literals plus null/empty/invalid probes; writer inputs include flag boundaries and all declared bits.

Run `Tests/Invoke-XmlSerializerBehaviorRegression.ps1 -MetadataReport <report.json> -CaseManifests <case-files> -OutputDirectory <fresh-directory>`. It builds the .NET Framework probe, runs originals and rebuilds in separate processes, verifies actual loaded bytes and compares results/exception messages. Dependencies resolve in each module's physical context. No ETS source/binary or user profile is modified.

`python Tests/test_xml_serializer_behavior_records.py` verifies the report guards, including distinct physical copies with identical assembly identities, wrong loader paths, missing module coverage, changed results and empty executions. These focused helper cases do not prove complex-document or full ETS/App compatibility.
