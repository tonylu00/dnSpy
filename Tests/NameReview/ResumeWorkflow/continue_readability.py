"""Resume fixed ETS readability obligations without changing generated source.

Only reports and the authoritative navigation state are written. The v1044 map,
disposition queues, exported source, compiled binaries and receipts stay immutable.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import shutil
import xml.etree.ElementTree as ET
import os


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def pin(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest().upper()
    return {"Path": str(path), "Sha256": digest}


def checked(binding):
    assert pin(binding["Path"]) == {k: binding[k] for k in ("Path", "Sha256")}, binding["Path"]
    return read(binding["Path"])


def fresh(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        if Path(path).name.startswith("cursor-"):
            stream.write("{\n" + ",\n".join("  " + json.dumps(k) + ": " + json.dumps(v, ensure_ascii=False)
                                                  for k, v in value.items()) + "\n}")
        else:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def command(stage, state, directory):
    return f'python {Path(__file__).resolve().as_posix()} {stage} --state {Path(state).as_posix()} --output {Path(directory).as_posix()}'


def save_state(path, expected, state):
    # Compare-and-swap preserves an unexpected concurrent publisher.
    assert pin(path) == expected, "STATE changed; preserve the other writer"
    checkpoint = Path(state["Pass"]["CheckpointDir"])
    spec = importlib.util.spec_from_file_location("state_publisher", checkpoint / "publish_dispositions.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(checkpoint))
    spec.loader.exec_module(module)
    text = module.state_text(state) + "\n"
    # Preserve every value while folding the detailed milestone onto one line.
    detail = state["Naming"]["ConsolidatedVerification"]
    text = text.replace(module.state_text(detail, 2), json.dumps(detail, ensure_ascii=False), 1)
    assert len(text.splitlines()) < 200, "Keep authoritative STATE compact"
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def publish_navigation(state_path, expected, state, cursor_path, cursor):
    state["UpdatedUtc"] = now()
    state["Naming"]["BlockCursor"] = str(cursor_path)
    state["Naming"]["NextItems"] = cursor["NextItems"]
    state["Pass"]["ExecutionStatus"] = cursor["Status"]
    state["Readability"]["PhysicalScope63"]["NextBlock"] = cursor["NextItems"][0]["Task"]
    state["Naming"]["Backlog"]["OpenRoute"] = cursor["NextItems"][0]["Task"]
    state["Closure"]["NotClaimed"] = "v1044 build/bounded runtime and v179 reuse remain verified milestones. Private metadata, generated dispositions, unsupported names, ETS6.4 value/type transfer and broader runtime remain open."
    fresh(cursor_path, cursor)
    save_state(state_path, expected, state)


def reconcile(state_path, directory):
    assert not directory.exists(), "Choose a fresh continuation directory"
    before = pin(state_path)
    state = read(state_path)
    old_cursor = read(state["Naming"]["BlockCursor"])
    execution = old_cursor["CurrentConsolidation"]["Execution"]
    assert execution["CompletedStage"] and not execution["BroaderReadabilityGoalClosed"]
    assert not execution["Running"] and not execution["RestoreRequired"]
    receipts = [state["Maps"]["63"], state["Naming"]["Dispositions"],
                execution["SourceVerification"], execution["RuntimeVerification"], execution["Ets64CurrentInputReuse"]]
    for binding in receipts:
        assert pin(binding["Path"])["Sha256"] == binding["Sha256"]
    source = checked(execution["SourceVerification"])
    join_binding = source["Evidence"]["CompiledSourceJoin"]
    join = checked(join_binding)
    build = checked(join["CompileResult"])
    export = Path(build["Output"])
    entries = []
    for row in join["Rows"]:
        for item in row["Sources"]:
            if item["Status"] not in ("SourceHashMismatch", "MultipleExportFragments"):
                continue
            assert pin(row["Module"])["Sha256"] == row["InputSha256"]
            assert pin(export / item["File"])["Sha256"] == item["FileSha256"]
            entries.append({"Module": row["Module"], "RootToken": item["RootToken"], "File": item["File"],
                            "Status": item["Status"], "CurrentSourceSha256": item["SourceSha256"],
                            "CurrentNativeSha256": item["ExpectedSourceSha256"],
                            "Identity": row["Identity"], "Mvid": row["Mvid"], "InputSha256": row["InputSha256"]})
    assert len(entries) == 9 and len({(x["Module"], x["RootToken"]) for x in entries}) == 7
    delta = checked(source["Evidence"]["PrivateAliasDelta"])
    prior = checked(delta["Previous"])
    current = checked(delta["Current"])
    prior_counts, current_counts = Counter(prior["Issues"]), Counter(current["Issues"])
    assert not prior_counts - current_counts and sum(prior_counts.values()) == 7429
    assert sum((current_counts - prior_counts).values()) == 96
    assert pin(state_path) == before, "Concurrent state writer"
    directory.mkdir()
    (directory / "STATE.before.json").write_bytes(Path(state_path).read_bytes())
    fresh(directory / "source-root-cohort.json", {"Format": 1, "Kind": "FixedPhysicalSourceRootCohort",
        "CurrentJoin": join_binding, "Entries": entries, "RootCount": 7, "FileCount": 9, "AddedDiscovery": 0})
    fresh(directory / "private-metadata-cohort.json", {"Format": 1, "Kind": "FixedPrivateMetadataFindingCohort",
        "Prior": delta["Previous"], "Current": delta["Current"], "Original": dict(prior_counts),
        "OriginalUnresolved": 7429, "OriginalResolved": 0, "AddedDiscovery": dict(current_counts - prior_counts),
        "AddedUnresolved": 96, "CurrentUnresolved": 7525,
        "Meaning": "Retained failing findings, not resolved findings. No alias spelling or absent generated storage is automatically accepted."})
    prior_settings = Path(state["Pass"]["CheckpointDir"]) / "consolidated-v1039-settings-source-reconciliation01.json"
    checked(pin(prior_settings))
    scope = read(old_cursor["CurrentConsolidation"]["NativeScope"])
    modules = {x["Module"] for x in entries}
    native = [r for r in scope["Results"] if r["Input"] in modules]
    for row in native:
        assert pin(row["Report"])["Sha256"] == row["ReportSha256"]
    omitted_binding = checked(pin(prior_settings))["OmittedGeneratedRootDispositionBinding"]
    omitted = checked(omitted_binding)
    fresh(directory / "omitted-generated-root-cohort.json", {"Format": 1, "Kind": "FixedOmittedGeneratedRootCohort",
        "Baseline": omitted_binding, "Rows": omitted["Rows"], "Original": 8, "Resolved": 0, "AddedDiscovery": 0})
    next_items = [
        {"Task": "verify seven settings owner projections under v1044", "Detail": command("settings", state_path, directory)},
        {"Task": "eight omitted generated owner roots and fixed private metadata cohort", "Detail": "Review exact source-owner/native bodies; retain 7429 findings plus 96 separate discoveries until classified with evidence."},
        {"Task": "ETS6.4 non-method transfer and wider runtime", "Detail": "Types/fields/parameters/locals remain untransferred; four original-binary modules and language switch, programming, physical KNX and online workflows remain explicit."}]
    cursor = {"Format": 1, "Kind": "BoundedReadabilityContinuationCursor", "UpdatedUtc": now(),
        "Workspace": state["Pass"]["DnspyRepo"], "SharedState": str(state_path),
        "SharedStateWriter": "Current goal agent; writes guarded by exact STATE preimage.",
        "CurrentStage": "v1044-broader-readability-reconciled", "CompletedStage": False,
        "BroaderReadabilityGoalClosed": False, "PreviousCursor": pin(state["Naming"]["BlockCursor"]),
        "VerifiedMilestone": execution, "Map": state["Maps"]["63"], "Disposition": state["Naming"]["Dispositions"],
        "FixedCohorts": {"SourceRoots": pin(directory / "source-root-cohort.json"),
                        "PrivateMetadata": pin(directory / "private-metadata-cohort.json"),
                        "GeneratedOmissions": pin(directory / "omitted-generated-root-cohort.json")},
        "OverallCompletionCriteria": [
            "All fixed physical symbol cohorts have supported names/readable preservation/protected status/verified generated treatment or explicit evidence-exhausted unresolved reasons; new discoveries reported separately.",
            "Generated lambda/closure/async/iterator bodies reconstruct into proved source owners; necessary retained helpers have identity-bound source/behavior dispositions.",
            "All first-party physical source roots and private metadata findings receive exact source/compiled contracts or documented justified boundaries; raw findings remain auditable.",
            "Identity-matching NuGet exclusions and untouched original dependencies are governed by the authoritative disposition manifest; no guessed package equivalence.",
            "ETS6.3 then ETS6.4 complete first-party exports build without code modifications, with SDK/reference/resource/signature audits passed; non-method transfer is verified or explicitly unresolved per identity.",
            "Declared broader runtime scenarios and unchanged Apps pass; unavailable physical/online tests retain explicit limitations and do not become passes."],
        "Status": "Active broader goal; v1044 stage verified. Next: seven current settings projections, then omitted generated owner/private metadata component blocks.",
        "NextItems": next_items, "NextCommand": next_items[0]["Detail"], "Running": [], "RestoreRequired": False,
        "SettingsInputs": {"Join": join_binding, "Export": str(export), "NativeScopeRows": native,
                           "Runtime": scope["Runtime"], "ReferenceManifest": scope["ReferenceManifest"],
                           "Inspector": "D:/knx_analysis/settings-source-projection-inspector12/GeneratedSourceInspection.dll"},
        "Counters": {"SourceRootsOriginal": 7, "SourceRootsVerified": 0, "PrivateOriginal": 7429,
                     "PrivateOriginalResolved": 0, "PrivateAddedDiscovery": 96, "GeneratedOmissionsOriginal": 8,
                     "GeneratedOmissionsResolved": 0, "NamingOrReconstructionCredit": 0}}
    publish_navigation(state_path, before, state, directory / "cursor-reconciled.json", cursor)
    fresh(directory / "reconciliation-publication.json", {"Before": before, "After": pin(state_path),
        "Cursor": pin(directory / "cursor-reconciled.json"), "Producer": pin(__file__),
        "PreviousReceiptsPreserved": receipts, "OverallGoalClosed": False})
    print(json.dumps({"Cursor": str(directory / "cursor-reconciled.json"), "NextCommand": cursor["NextCommand"]}))


def run(args, log, environment=None):
    with Path(log).open("x", encoding="utf-8") as stream:
        completed = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, text=True, env=environment)
    if completed.returncode:
        print(Path(log).read_text(encoding="utf-8", errors="replace")[-6000:])
        raise RuntimeError(f"Native command failed ({completed.returncode}); preserve {log}")


def settings(state_path, directory):
    before = pin(state_path)
    state = read(state_path)
    cursor = read(state["Naming"]["BlockCursor"])
    assert cursor["Kind"] == "BoundedReadabilityContinuationCursor"
    cohort = checked(cursor["FixedCohorts"]["SourceRoots"])
    inputs = cursor["SettingsInputs"]
    checked(inputs["Join"])
    assert pin(cursor["Map"]["Path"])["Sha256"] == cursor["Map"]["Sha256"]
    native = directory / "settings-native"
    native.mkdir(exist_ok=True)
    for module in sorted({x["Module"] for x in cohort["Entries"]}):
        name = Path(module).name
        report = native / (name + ".json")
        if report.exists():
            data = read(report)
            assert data["InputSha256"] == pin(module)["Sha256"] and data["MapSha256"] == cursor["Map"]["Sha256"]
            continue
        roots = sorted({x["RootToken"] for x in cohort["Entries"] if x["Module"] == module})
        args = ["dotnet", inputs["Inspector"], inputs["Runtime"], module, str(report), "inspect",
                "--references=" + inputs["ReferenceManifest"], "--map=" + cursor["Map"]["Path"], "--sdk-source",
                "--roots=" + ",".join(f"0x{x:08X}" for x in roots), "--source-directory=" + str(native / (name + ".source"))]
        fresh(native / (name + ".command.json"), args)
        run(args, native / (name + ".log"))
        print("Verified native settings owners:", name, flush=True)
    projection = directory / "settings-source-projection.json"
    if not projection.exists():
        run(["dotnet", inputs["Inspector"], inputs["Runtime"], cursor["FixedCohorts"]["SourceRoots"]["Path"],
             str(projection), "settings-projection", str(native), inputs["Export"]], directory / "settings-projection.log")
    joined = directory / "settings-reconciled-source-join.json"
    join_tool = Path(state["Pass"]["DnspyRepo"]) / "Tests/GeneratedSourceInspection/Join-CompiledSource.py"
    if not joined.exists():
        run([sys.executable, str(join_tool), "--reconcile-source-join", inputs["Join"]["Path"],
             "--settings-projection", str(projection), "--output", str(joined)], directory / "settings-join.log")
    proof = read(projection)
    result = read(joined)
    assert proof["RootCount"] == 7 and proof["FileCount"] == 9 and result["VerifiedSettingsProjectionRoots"] == 7
    cursor["UpdatedUtc"] = now()
    cursor["CurrentStage"] = "v1044-seven-settings-source-projections-verified"
    cursor["CompletedStage"] = True
    cursor["Counters"].update(SourceRootsVerified=7)
    cursor["Completed"] = {"SettingsProjection": pin(projection), "ReconciledSourceJoin": pin(joined),
                           "SettingsOriginalRootsVerified": 7, "SourceFilesVerified": 9, "AddedDiscovery": 0}
    cursor["NextItems"] = cursor["NextItems"][1:]
    cursor["NextItems"][0]["Detail"] = command("generated", state_path, directory)
    cursor["NextCommand"] = cursor["NextItems"][0]["Detail"]
    cursor["Status"] = "Active broader goal; seven v1044 Settings projections verified, no naming/reconstruction credit. Next: eight omitted generated owner roots; private7429 plus96 and ETS6.4/broader runtime remain."
    state["Naming"]["ConsolidatedVerification"]["RemainingSourcePhysicalRoots"] = 0
    state["Naming"]["ConsolidatedVerification"]["SettingsProjectionVerification"] = pin(joined)
    state["Naming"]["ConsolidatedVerification"]["FixedPriorPrivateMetadataIssues"] = 7429
    state["Naming"]["ConsolidatedVerification"]["PrivateMetadataMeaning"] = "7429 retained unresolved findings; 96 new findings; zero newly failing prior checks."
    publish_navigation(state_path, before, state, directory / "cursor-settings-verified.json", cursor)
    print(json.dumps({"OriginalRoots": 7, "Verified": 7, "AddedDiscovery": 0, "NextCommand": cursor["NextCommand"]}))


def generated(state_path, directory):
    """Reconcile inherited dispositions, then verify changed compiled owner inputs."""
    before = pin(state_path)
    state = read(state_path)
    cursor = read(state["Naming"]["BlockCursor"])
    cohort = checked(cursor["FixedCohorts"]["GeneratedOmissions"])
    old = checked(cursor["PreviousCursor"])
    scope = read(old["CurrentConsolidation"]["NativeScope"])
    source_join = checked(cursor["SettingsInputs"]["Join"])
    manifest = checked(cursor["Disposition"])
    stream = manifest["RemainingNativeGeneratedDispositions"]
    assert pin(stream["Path"]) == stream
    wanted = {(x["Module"], x["Token"]): x for x in cohort["Rows"]}
    current = {}
    with Path(stream["Path"]).open(encoding="utf-8-sig") as rows:
        for line in rows:
            row = json.loads(line)
            key = row["Module"], row["Token"]
            if key in wanted:
                assert all(wanted[key][name] == row[name] for name in
                           ("Module", "Token", "Identity", "Mvid", "Sha256", "Signature", "OriginalName"))
                current[key] = row
    assert len(current) == 8
    output = directory / "generated-owner-evidence"
    output.mkdir(exist_ok=True)
    native_tool = ["dotnet", "D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll"]
    rows = []
    for selected in cohort["Rows"]:
        actual = current[selected["Module"], selected["Token"]]
        inherited = actual.get("SourceScaffoldElision", actual.get("ArtifactSourceDeferredReview"))
        assert inherited, "Selected root needs a fresh evidence route"
        for name in ("Review", "Proof", "CompiledSourceJoin", "NativeReport", "BaselineMap"):
            if name in inherited:
                binding = inherited[name]
                assert pin(binding["Path"]) == binding
        if actual["Disposition"] == "generated-source-elided-scaffold":
            rows.append({"Module": selected["Module"], "RootToken": selected["Token"],
                         "HistoricalOriginalDisposition": selected["Disposition"],
                         "CurrentDisposition": actual["Disposition"], "InheritedProof": inherited,
                         "NamingOrReconstructionCredit": 0})
            continue
        item = next(r for r in scope["Results"] if r["Path"].replace("\\", "/") == selected["Module"].replace("\\", "/"))
        assert pin(item["Input"])["Sha256"] == selected["Sha256"]
        assert item["Mvid"] == selected["Mvid"] and item["Identity"] == selected["Identity"]
        assert pin(item["Report"])["Sha256"] == item["ReportSha256"]
        prefix = selected["Module"].replace("/", "_").replace("\\", "_")
        type_report = output / (prefix + ".type.json")
        if not type_report.exists():
            run(native_tool + ["--inspect-type", item["Input"], selected["Signature"]], type_report)
        types = read(type_report)
        assert types["Sha256"] == selected["Sha256"] and types["Mvid"] == selected["Mvid"]
        root = next(t for t in types["Types"] if t["Token"] == selected["Token"])
        members = {int(t["Token"], 16) for t in types["Types"]}
        method_tokens = []
        for nested in types["Types"]:
            for kind in ("Methods", "Fields", "Properties", "Events"):
                members.update(int(x["Token"], 16) for x in nested[kind])
            method_tokens.extend(x["Token"] for x in nested["Methods"])
        bodies = output / (prefix + ".methods.json")
        if method_tokens and not bodies.exists():
            run(native_tool + ["--inspect-methods", item["Input"], *method_tokens], bodies)
        report = read(item["Report"])
        assert report["MapSha256"] == cursor["Map"]["Sha256"]
        consumers = []
        for observed in report["Roots"]:
            uses = [u for u in observed["PrintedReferences"] if not u["IsDefinition"]
                    and u.get("DefinitionModuleMvid") == selected["Mvid"]
                    and u.get("DefinitionModulePath") == item["Input"] and u.get("DefinitionToken") in members]
            annotations = sorted(set(observed["ReferenceTokens"]) & members)
            if uses or annotations:
                consumers.append({"RootToken": observed["RootTypeToken"], "CompleteTypeScope": observed["CompleteTypeScope"],
                                  "PrintedUses": uses, "AnnotationTokens": annotations})
        compiled = next(r for r in source_join["Rows"] if r["Module"] == item["Input"])
        files = [x for x in compiled["Sources"] if x["RootToken"] in {u["RootToken"] for u in consumers}]
        rows.append({"Module": item["Input"], "Identity": selected["Identity"], "Mvid": selected["Mvid"],
                     "Sha256": selected["Sha256"], "RootToken": selected["Token"], "Signature": selected["Signature"],
                     "HistoricalOriginalDisposition": selected["Disposition"], "CurrentDisposition": actual["Disposition"],
                     "InheritedProof": inherited, "Types": types["Types"],
                     "NativeType": pin(type_report), "NativeBodies": pin(bodies) if method_tokens else None,
                     "CurrentSourceReport": {"Path": item["Report"], "Sha256": item["ReportSha256"]},
                     "SourceConsumers": consumers, "CompiledConsumerFiles": files,
                     "UnmatchedStandaloneRoot": int(selected["Token"], 16) in compiled["UnmatchedObservedRoots"],
                     "Disposition": "pending-owner-and-compiled-behavior-review", "NamingOrReconstructionCredit": 0})
        print("Collected generated component:", selected["Module"], len(method_tokens), "methods", flush=True)
    triage = directory / "generated-owner-triage.json"
    fresh(triage, {"Format": 1, "Kind": "FixedGeneratedOwnerCurrentSourceTriage",
        "Cohort": cursor["FixedCohorts"]["GeneratedOmissions"], "Map": cursor["Map"], "Disposition": cursor["Disposition"],
        "NativeTool": pin(native_tool[1]), "SourceJoin": cursor["SettingsInputs"]["Join"], "Rows": rows,
        "HistoricalOriginal": 8, "InheritedSourceScaffoldDispositions": 6, "MetadataUnresolved": 2,
        "NewlyResolved": 0, "AddedDiscovery": 0,
        "Limits": "Six inherited source scaffolds are not new reconstruction. Two anonymous owner behaviors were verified previously; their original metadata remains open. Authoritative queues unchanged."})
    inspector = "D:/knx_analysis/generated-artifact-projection-inspector19/GeneratedArtifactProjection.dll"
    scan = directory / "generated-member-owner-scan.json"
    joined = cursor["Completed"]["ReconciledSourceJoin"]["Path"]
    if not scan.exists():
        run(["dotnet", inspector, cursor["FixedCohorts"]["GeneratedOmissions"]["Path"], joined,
             old["CurrentConsolidation"]["NativeScope"], str(scan)], directory / "generated-member-owner-scan.log")
    proofs = {}
    for action in ("arrays", "anonymous"):
        destination = directory / ("generated-" + action + "-projection.json")
        if not destination.exists():
            run(["dotnet", inspector, "verify-" + action, str(scan), joined, str(destination)], directory / ("generated-" + action + ".log"))
        proofs[action] = destination
    semantics = directory / "generated-anonymous-semantics.json"
    if not semantics.exists():
        run(["dotnet", inspector, "verify-anonymous-semantics", str(proofs["anonymous"]), str(semantics)], directory / "generated-anonymous-semantics.log")
    workflow = Path(state["Pass"]["CheckpointDir"])
    review = directory / "generated-source-owner-review.json"
    if not review.exists():
        run([sys.executable, str(workflow / "generated_artifact_source_projections.py"), "--scan", str(scan),
             "--arrays", str(proofs["arrays"]), "--anonymous", str(proofs["anonymous"]), "--anonymous-semantics", str(semantics),
             "--source-join", joined, "--output", str(review)], directory / "generated-source-owner-review.log")
    cursor["UpdatedUtc"] = now()
    cursor["CurrentStage"] = "v1044-generated-owner-source-projections-refreshed"
    cursor["Completed"].update(GeneratedTriage=pin(triage), GeneratedReview=pin(review),
                              GeneratedAnonymousSemantics=pin(semantics))
    cursor["Counters"].update(GeneratedOmissionsInheritedSourceResolved=6, GeneratedOmissionsMetadataUnresolved=2,
                             GeneratedOmissionsNewlyResolved=0)
    cursor["NextItems"][0] = {"Task": "anonymous sentinel metadata restoration component",
                              "Detail": command("anonymous-contracts", state_path, directory)}
    cursor["NextCommand"] = cursor["NextItems"][0]["Detail"]
    cursor["Status"] = "Active broader goal; current Settings7 and generated owner source proofs refreshed. Six generated roots inherited as scaffolds; two anonymous metadata identities remain. Next: exact sentinel metadata restoration contracts."
    publish_navigation(state_path, before, state, directory / "cursor-generated-verified.json", cursor)
    print(json.dumps({"HistoricalOriginal": 8, "InheritedScaffolds": 6, "MetadataUnresolved": 2, "NewlyResolved": 0,
                      "NextCommand": cursor["NextCommand"]}))


def anonymous_contracts(state_path, directory):
    before = pin(state_path)
    state = read(state_path)
    cursor = read(state["Naming"]["BlockCursor"])
    proof_path = Path("D:/knx_analysis/anonymous-sentinel-contract-proof07/proof.json")
    proof = read(proof_path)
    assert len(proof["Rows"]) == 2 and len(proof["NegativeCases"]) == 20
    assert proof["ApplicationInputsPreserved"] and not proof["AppliedToCurrentEts"] and not proof["RuntimeVerified"]
    for row in proof["Rows"]:
        for name in ("Original", "Rebuilt", "RestoredTestCopy"):
            assert pin(row[name])["Sha256"] == row[name + "Sha256"]
    workspace = Path(state["Pass"]["DnspyRepo"])
    source_paths = [workspace / p for p in (
        "dnSpy/dnSpy.Contracts.Logic/Decompiler/MetadataAnonymousSentinels.cs",
        "dnSpy/dnSpy.Decompiler/MSBuild/MetadataFieldProjectSupport.cs",
        "dnSpy/dnSpy.Decompiler/MSBuild/MetadataFieldTask.cs.txt",
        "Tests/AnonymousSentinelMetadataRegression/Program.cs",
        "Tests/AnonymousSentinelMetadataRegression/AnonymousSentinelMetadataRegression.csproj")]
    cursor["Completed"]["AnonymousMetadataNativeRegression"] = pin(proof_path)
    cursor["PreparedNativeRepair"] = {"Sources": [pin(p) for p in source_paths],
        "Runtime": "D:/knx_analysis/anonymous-sentinel-native-runtime04",
        "Core": pin("D:/knx_analysis/anonymous-sentinel-native-runtime04/dnSpy.Decompiler.dll"),
        "Contracts": pin("D:/knx_analysis/anonymous-sentinel-native-runtime04/dnSpy.Contracts.Logic.dll"),
        "TaskSource": pin("D:/knx_analysis/anonymous-sentinel-task-source04.cs"),
        "Regression": pin(proof_path), "AppliedToSource": False, "AppliedToCurrentEts": False,
        "Targets": [row["Original"] for row in proof["Rows"]]}
    cursor["CurrentStage"] = "anonymous-sentinel-native-type-storage-repair-validated"
    cursor["NextItems"][0] = {"Task": "export and compile two repaired sentinel components", "Detail": command("anonymous-export", state_path, directory)}
    cursor["NextCommand"] = cursor["NextItems"][0]["Detail"]
    cursor["Status"] = "Active broader goal; native sentinel type/storage repair passed two physical test roundtrips and20 rejection guards. Fresh two-component exporter/build application pending; v1044 whole-app receipts preserved."
    publish_navigation(state_path, before, state, directory / "cursor-anonymous-native-verified.json", cursor)
    print(json.dumps({"NativeTargetsVerified": 2, "RejectionGuards": 20, "AppliedToCurrentSource": False, "NextCommand": cursor["NextCommand"]}))


def anonymous_export(state_path, directory):
    state = read(state_path)
    cursor = read(state["Naming"]["BlockCursor"])
    repair = cursor["PreparedNativeRepair"]
    for source in repair["Sources"]:
        assert pin(source["Path"]) == source
    for name in ("Core", "Contracts", "TaskSource", "Regression"):
        assert pin(repair[name]["Path"]) == repair[name]
    build = checked(cursor["VerifiedMilestone"]["Inputs"]["BuildResult"])
    args = build["Export"]["Command"]
    base_runtime = Path(args[0]).parent
    # Failed runs are retained. A retry always chooses a new output tree.
    attempt_number = 1
    while (directory / f"sentinel-export-attempt{attempt_number:02}").exists():
        attempt_number += 1
    attempt = directory / f"sentinel-export-attempt{attempt_number:02}"
    attempt.mkdir()
    runtime = attempt / "runtime"
    shutil.copytree(base_runtime, runtime)
    for name in ("Core", "Contracts"):
        shutil.copy2(repair[name]["Path"], runtime / Path(repair[name]["Path"]).name)
    output = attempt / "export"
    assert not output.exists(), "Choose a fresh component export"
    # Keep the verified physical loader/reference switches; reduce only input
    # modules. Unrelated first-party projects remain original binary dependencies.
    input_root = Path(state["Pass"]["SourceTree63"])
    # The first focused build identified 24 references to Hawk generated nested
    # contracts. Keep this coupling visible instead of patching consumer source.
    export_inputs = [arg for arg in args[1:] if Path(arg).suffix.lower() in (".dll", ".exe") and Path(arg).is_relative_to(input_root)]
    assert len(export_inputs) == 109, "Reuse the fixed consolidated source cohort"
    coupled_inputs = [p for p in export_inputs if p not in repair["Targets"]]
    print("Sentinel repair source group:", len(repair["Targets"]), "targets and", len(coupled_inputs), "coupled modules", flush=True)
    selected = []
    for arg in args[1:]:
        try:
            path = Path(arg)
            is_module = path.suffix.lower() in (".dll", ".exe") and path.is_relative_to(input_root)
        except ValueError:
            is_module = False
        if not is_module:
            selected.append(arg)
    selected[selected.index("-o") + 1] = str(output)
    context_position = selected.index("--assembly-contexts") + 1
    original_context = selected[context_position]
    contexts = ET.parse(original_context)
    targets = {str(Path(p).resolve()).casefold() for p in export_inputs}
    for context in list(contexts.getroot()):
        if str(Path(context.get("Source")).resolve()).casefold() not in targets:
            contexts.getroot().remove(context)
    assert len(contexts.getroot()) == len(export_inputs)
    context_path = attempt / "contexts.xml"
    contexts.write(context_path, encoding="utf-8", xml_declaration=True)
    selected[context_position] = str(context_path)
    map_position = selected.index("--source-name-map") + 1
    selected_map = attempt / "selected-map.xml"
    contracts = state["Compatibility"]["ContractReferences63"]
    assert pin(contracts["Path"])["Sha256"] == contracts["Sha256"]
    native = ["dotnet", "D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll",
              "--contract-references", contracts["Path"]]
    # The complete existing cohort avoids mixed original/source alias contracts.
    # Copy a checked immutable map; do not alter its rows for this tool repair.
    shutil.copy2(cursor["Map"]["Path"], selected_map)
    run(native + ["--check-map", str(selected_map), str(attempt / "map-check.json")], attempt / "map-check.log")
    selected[map_position] = str(selected_map)
    selected += export_inputs
    executable = runtime / Path(args[0]).name
    invocation = [str(executable), *selected]
    fresh(attempt / "command.json", invocation)
    fresh(attempt / "inputs.json", {"OriginalContexts": pin(original_context), "SelectedContexts": pin(context_path),
        "NativeCore": repair["Core"], "NativeContracts": repair["Contracts"], "ParentMap": cursor["Map"], "SelectedMap": pin(selected_map),
        "RepairTargets": repair["Targets"], "AddedCoupledSourceDependencies": [pin(p) for p in coupled_inputs],
        "AdditionalSemanticOrReconstructionDiscovery": 0})
    freeze = checked(cursor["VerifiedMilestone"]["Inputs"]["Freeze"])
    controls = freeze["Config"]
    environment = dict(os.environ, DNSPY_PACKAGE_MAP=controls["Packages"], DNSPY_SOURCEMAP_REPORT_ALL="1",
                       DNSPY_EMBEDDED_ORIGINAL_PLAN=controls["EmbeddedOriginalBinaryPlan"])
    for name in ("Packages", "EmbeddedOriginalBinaryPlan"):
        assert pin(controls[name])["Sha256"] == freeze["Pins"][controls[name]], "Frozen third-party export control changed"
    fresh(attempt / "dependency-controls.json", {name: pin(controls[name]) for name in ("Packages", "EmbeddedOriginalBinaryPlan")})
    run(invocation, attempt / "export.log", environment)
    projects = sorted(output.rglob("*.csproj"))
    assert len(projects) == len(export_inputs)
    for project in projects:
        marker = project.parent / ".dnspy-metadata/AnonymousSentinels.cs"
        if project.stem in ("Knx.Ets.Ui.UserControls", "Knx.Ets.ViewModel"):
            assert marker.exists(), "Native exporter omitted the exact anonymous restoration contract"
    run(["dotnet", "build", str(output / "solution.sln"), "-c", "Release", "-v:minimal"], attempt / "build.log")
    fresh(directory / "sentinel-component-build.json", {"Format": 1, "Kind": "TargetedSentinelNativeExportAndBuild",
        "Projects": [pin(p) for p in projects], "Output": str(output), "NativeRepair": repair,
        "ExportCommand": pin(attempt / "command.json"), "ExportLog": pin(attempt / "export.log"),
        "SourceEdited": False, "CurrentV1044OutputsModified": False, "RuntimeVerified": False,
        "FixedSourceCohortProjects": 109, "RepairOwnerComponents": 2, "AddedSemanticDiscovery": 0,
        "BuildLog": pin(attempt / "build.log"),
        "Next": "Verify actual exported/rebuilt sentinel identities, field constants and generated behavior before publishing application credit."})
    print(json.dumps({"TargetedProjectsCompiled": len(projects), "SentinelRepairTargets": 2,
                      "AddedCoupledSourceDependencies": len(coupled_inputs), "SourceEdited": False, "Output": str(output)}))


def acceptance(state_path, directory):
    before = pin(state_path)
    state = read(state_path)
    cursor = read(state["Naming"]["BlockCursor"])
    build_path = directory / "sentinel-component-build.json"
    build = read(build_path)
    assert len(build["Projects"]) == 109 and not build["SourceEdited"] and not build["CurrentV1044OutputsModified"]
    for binding in build["Projects"] + [build["BuildLog"], build["ExportLog"]]:
        assert pin(binding["Path"]) == binding
    assert "0 个错误" in Path(build["BuildLog"]["Path"]).read_text(encoding="utf-8-sig")
    metadata_path = directory / "actual-sentinel-metadata-proof.json"
    metadata = read(metadata_path)
    assert metadata["Kind"] == "ActualToolExportedAnonymousSentinelMetadataAcceptance" and len(metadata["Rows"]) == 2
    assert metadata["ApplicationInputsPreserved"] and not metadata["GeneratedSourceEdited"] and not metadata["RuntimeVerified"]
    for row in metadata["Rows"]:
        assert row["ExactFields"] == 2 and row["VerifiedOrdinaryMethodBodies"] == 5 and row["ExactOwnerSource"]
        assert row["OriginalTypeNamesAndPrivateFieldStorageVerified"]
        for name in ("Original", "PriorCompiled", "Rebuilt", "Source"):
            assert pin(row[name]["Path"]) == row[name]
    private = read(directory / "current-private-alias-contract.json")
    fixed = checked(cursor["FixedCohorts"]["PrivateMetadata"])
    original, current = Counter(fixed["Original"]), Counter(private["Issues"])
    prior_current = Counter(checked(fixed["Current"])["Issues"])
    assert not prior_current - current and current == prior_current, "Changed private findings require a separate delta review"
    delta_path = directory / "private-metadata-fixed-cohort-delta.json"
    fresh(delta_path, {"OriginalCohort": cursor["FixedCohorts"]["PrivateMetadata"],
        "CurrentAudit": pin(directory / "current-private-alias-contract.json"), "Original": sum(original.values()),
        "OriginalResolved": 0, "OriginalRemaining": sum(original.values()), "ExistingAddedDiscovery": 96,
        "NewFailures": 0, "NewAddedDiscovery": 0, "CurrentRemaining": len(private["Issues"]),
        "SentinelRepairIncludedInThisAliasFindingCohort": False})
    cursor["Completed"].update(New109ProjectBuild=pin(build_path), ActualSentinelMetadata=pin(metadata_path),
                              PrivateCohortDelta=pin(delta_path))
    cursor["Counters"].update(SentinelTypeNamesVerified=2, SentinelFieldContractsVerified=4,
                             SentinelOrdinaryMethodBodiesPreserved=10, StrictPrivateAliasFindingsRemaining=7525,
                             GeneratedDispositionRowsRetired=0, NewSemanticNames=0)
    cursor["PreparedNativeRepair"].update(AppliedToSource=True, AppliedToNew109ProjectExport=True,
                                        CurrentWholeApplicationRuntimeVerified=False)
    cursor["CurrentStage"] = "native-sentinel-repair-current109-source-build-and-metadata-verified"
    cursor["CompletedStage"] = True
    cursor["Remaining"] = {"SourcePhysicalRootProjectionObligations": 0,
        "AuthoritativeGeneratedDispositionRowsPending": state["Naming"]["Progress"]["RemainingGeneratedDispositionDefinitions"],
        "ReconstructionReviewsPending": state["Naming"]["Progress"]["RemainingReconstructionDefinitions"],
        "ProjectedValuesPending": state["Naming"]["Progress"]["ProjectedValuesNeedingReview"],
        "UnsupportedLegacyAliases": 9, "PrivateOriginalFindings": 7429, "PrivatePriorDiscovery": 96,
        "NativeRepairRuntimePending": True, "BroaderRuntimePending": True,
        "Ets64TypeFieldParameterLocalTransferPending": True, "Ets64OriginalBinaryModulesOutsideSourceCohort": 4}
    cursor["NextItems"] = [
        {"Task": "review a complete Common private-metadata owner component", "Detail": command("private-owner-block", state_path, directory)},
        {"Task": "bind native sentinel metadata proofs into generated dispositions", "Detail": "Four exact type/field contracts are verified in the new tool export. Keep the authoritative pending queue until normal proof replay/reconciliation accepts the evidence; no manual counter changes."},
        {"Task": "new-tool contract/runtime gates and ETS6.4 transfer", "Detail": "Stage current109 separately; run SDK/visible/resource audits and new-tool runtime including language switching. Preserve v1044/v179 receipts as bound baselines; non-method ETS6.4 transfer remains open."}]
    cursor["NextCommand"] = cursor["NextItems"][0]["Detail"]
    cursor["Status"] = "Active broader goal. Settings7 projections verified; native sentinel repair builds109/0 and verifies2 type names/4 fields/10 unchanged method bodies. Private7429+96 and authoritative generated/value/reconstruction queues remain; new-tool runtime and ETS6.4 non-method transfer are pending."
    state["Naming"]["ConsolidatedVerification"]["NativeSentinelRepairAcceptance"] = pin(metadata_path)
    state["Naming"]["ConsolidatedVerification"]["NewNativeToolBuild"] = pin(build_path)
    publish_navigation(state_path, before, state, directory / "cursor-native-sentinel-accepted.json", cursor)
    print(json.dumps({"CompiledProjects": 109, "CompilerErrors": 0, "SentinelTypeNames": 2,
                      "SentinelFieldContracts": 4, "PrivateOriginalRemaining": 7429, "PriorDiscovery": 96,
                      "OverallGoalClosed": False, "NextCommand": cursor["NextCommand"]}))


def private_owner_block(state_path, directory):
    """Freeze and inspect one complete owner group from the fixed failing cohort."""
    state = read(state_path)
    cursor = read(state["Naming"]["BlockCursor"])
    fixed = checked(cursor["FixedCohorts"]["PrivateMetadata"])
    old_cursor = checked(cursor["PreviousCursor"])
    scope = read(old_cursor["CurrentConsolidation"]["NativeScope"])
    module = next(r for r in scope["Results"] if r["Path"] == "Knx.Ets.Common.dll")
    assert pin(module["Report"])["Sha256"] == module["ReportSha256"]
    observed = read(module["Report"])
    candidates = [x for x in fixed["Original"] if x.startswith(module["Input"] + " 06")]
    assert candidates
    first_token = int(candidates[0].split(": ", 1)[0].rsplit(" ", 1)[1], 16)
    definition = next(d for d in observed["Definitions"] if d["Token"] == first_token)
    owner = definition["FullName"].split("::", 1)[0].split(" ", 1)[1]
    members = [d for d in observed["Definitions"] if "::" in d["FullName"] and
               d["FullName"].split("::", 1)[0].split(" ", 1)[1] == owner]
    member_tokens = {d["Token"] for d in members}
    pending = [x for x in fixed["Original"] if x.startswith(module["Input"] + " ") and
               int(x.split(": ", 1)[0].rsplit(" ", 1)[1], 16) in member_tokens]
    output = directory / "private-common-owner-block"
    assert not output.exists(), "Resume the prepared owner block; do not create a duplicate"
    output.mkdir()
    fresh(output / "cohort.json", {"Format": 1, "Kind": "FixedPrivateMetadataOwnerComponent",
        "ParentCohort": cursor["FixedCohorts"]["PrivateMetadata"], "Module": {k: module[k] for k in ("Input", "InputSha256", "Mvid", "Identity")},
        "Owner": owner, "OriginalMembers": members, "OriginalPendingFindings": pending,
        "NewDiscovery": [], "OriginalPendingCount": len(pending), "Resolved": 0,
        "CurrentSourceReport": {"Path": module["Report"], "Sha256": module["ReportSha256"]}})
    native = ["dotnet", "D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll"]
    run(native + ["--inspect-type", module["Input"], owner], output / "native-type.json")
    method_tokens = [f"0x{d['Token']:08X}" for d in members if d["Token"] >> 24 == 6]
    run(native + ["--inspect-methods", module["Input"], *method_tokens], output / "native-bodies.json")
    print(json.dumps({"Owner": owner, "OriginalPending": len(pending), "CompleteNativeMethods": len(method_tokens),
                      "Directory": str(output), "Resolved": 0, "AddedDiscovery": 0}))


def private_owner_review(state_path, directory):
    before = pin(state_path)
    state = read(state_path)
    cursor = read(state["Naming"]["BlockCursor"])
    output = directory / "private-common-owner-block"
    selected = read(output / "cohort.json")
    native = read(output / "native-complete-root.json")
    assert native["Sha256"] == selected["Module"]["InputSha256"] and native["Mvid"] == selected["Module"]["Mvid"]
    owner = selected["Owner"].split("/", 1)[0]
    types = [t for t in native["Types"] if t["Type"] == owner or t["Type"].startswith(owner + "/")]
    assert types and any(t["Type"] == owner for t in types)
    members = {int(t["Token"], 16) for t in types}
    methods = [m["Token"] for t in types for m in t["Methods"]]
    for t in types:
        for kind in ("Methods", "Fields", "Properties", "Events"):
            members.update(int(m["Token"], 16) for m in t[kind])
    fixed = checked(cursor["FixedCohorts"]["PrivateMetadata"])
    pending = [x for x in fixed["Original"] if x.startswith(selected["Module"]["Input"] + " ") and
               int(x.split(": ", 1)[0].rsplit(" ", 1)[1], 16) in members]
    body_path = output / "native-complete-root-bodies.json"
    if not body_path.exists():
        run(["dotnet", "D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll", "--inspect-methods",
             selected["Module"]["Input"], *methods], body_path)
    source = checked(selected["CurrentSourceReport"])
    root_token = int(next(t["Token"] for t in types if t["Type"] == owner), 16)
    observed = next(r for r in source["Roots"] if r["RootTypeToken"] == root_token)
    method_ids = {int(t, 16) for t in methods}
    witnesses = [w for w in observed["BodyWitnesses"] if w["ImplementationToken"] in method_ids]
    joined = checked(cursor["Completed"]["ReconciledSourceJoin"])
    module_join = next(r for r in joined["Rows"] if r["Module"] == selected["Module"]["Input"])
    sources = [s for s in module_join["Sources"] if s["RootToken"] == root_token]
    assert len(sources) == 1
    current_export = Path(read(directory / "sentinel-component-build.json")["Output"])
    source_file = current_export / sources[0]["File"]
    assert pin(source_file)["Sha256"] == sources[0]["FileSha256"]
    prepared = output / "complete-component-review.json"
    fresh(prepared, {"Format": 1, "Kind": "PrivateDongleLicenseOwnerComponentReviewInputs",
        "ParentFixedCohort": cursor["FixedCohorts"]["PrivateMetadata"], "Module": selected["Module"],
        "Root": owner, "Types": [t["Token"] for t in types], "NativeTypeReport": pin(output / "native-complete-root.json"),
        "NativeCompleteBodies": pin(body_path), "ActualCurrentOwnerSource": pin(source_file),
        "ExactCurrentSourceRoot": sources[0], "NativeOwnerWitnesses": witnesses,
        "OriginalPendingFindings": pending, "OriginalPendingCount": len(pending), "Resolved": 0,
        "NewDiscovery": [], "NextEvidenceRoute": "Bind compiled closures/lambda methods to exact native source-owner witnesses; do not match compiler ordinals or invent field-wide aliases."})
    cursor["CurrentStage"] = "private-dongle-license-component-frozen-for-compiled-owner-review"
    cursor["PreparedPrivateComponent"] = pin(prepared)
    cursor["Completed"].update(Staging=pin(directory / "new-native-stage-manifest.json"))
    for name, folder in (("SdkContracts", "sdk-contract-audit"), ("VisibleContracts", "visible-contract-audit")):
        receipt = directory / folder / "result.json"
        if receipt.exists():
            result = read(receipt)
            assert result["IssueCount"] == 0 and result["Projects"] == 109
            cursor["Completed"][name] = pin(receipt)
    cursor["NextItems"][0] = {"Task": "inspect exact compiled counterparts for the Dongle license component",
                              "Detail": command("compiled-owner-evidence", state_path, directory)}
    cursor["NextCommand"] = cursor["NextItems"][0]["Detail"]
    cursor["Status"] = f"Active broader goal. Native repair109/0,Settings7 and sentinel2 type/storage proofs verified. Complete Dongle component ({len(types)} types/{len(methods)} methods/{len(pending)} fixed private findings) is frozen for compiled-owner matching. Runtime, ETS6.4 transfer and authoritative pending queues remain."
    publish_navigation(state_path, before, state, directory / "cursor-private-component-prepared.json", cursor)
    print(json.dumps({"Owner": owner, "Types": len(types), "Methods": len(methods), "OriginalPending": len(pending),
                      "Resolved": 0, "AddedDiscovery": 0, "NextCommand": cursor["NextCommand"]}))


def compiled_owner_evidence(state_path, directory):
    state = read(state_path)
    cursor = read(state["Naming"]["BlockCursor"])
    component = checked(cursor["PreparedPrivateComponent"])
    binary = Path(read(directory / "sentinel-component-build.json")["Output"]) / "bin/Knx.Ets.Common.dll"
    destination = directory / "private-common-owner-block/compiled-root-types.json"
    assert not destination.exists(), "Resume the collected compiled owner evidence"
    run(["dotnet", "D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll", "--inspect-type", str(binary),
         component["Root"]], destination)
    result = read(destination)
    assert result["Sha256"] == pin(binary)["Sha256"]
    print(json.dumps({"CompiledOwnerEvidence": str(destination), "OriginalPending": component["OriginalPendingCount"],
                      "NamesDecided": 0, "MetadataFindingsResolved": 0,
                      "Next": "Read this complete component with its exact original/source witnesses and select structural compiled counterparts; missing helpers remain explicit."}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("reconcile", "settings", "generated", "anonymous-contracts", "anonymous-export", "acceptance", "private-owner-block", "private-owner-review", "compiled-owner-evidence"))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    {"reconcile": reconcile, "settings": settings, "generated": generated,
     "anonymous-contracts": anonymous_contracts, "anonymous-export": anonymous_export,
     "acceptance": acceptance, "private-owner-block": private_owner_block,
     "private-owner-review": private_owner_review, "compiled-owner-evidence": compiled_owner_evidence}[args.stage](args.state, args.output)


if __name__ == "__main__":
    main()
