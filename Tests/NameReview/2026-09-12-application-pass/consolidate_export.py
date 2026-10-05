"""Freeze exact inputs, then export/build a fresh application through native tools.

No generated source or binary edits, process cleanup, or directory removal.
The immutable freeze is reusable after a context reset; each run needs a fresh
report and output directory. Requires psutil for process-tree memory observations.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

import psutil


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def fresh_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def freeze(config, output):
    snapshot = Path(output).resolve().with_suffix(".inputs")
    if Path(output).exists() or Path(output).with_suffix(".contexts.xml").exists() or snapshot.exists():
        raise ValueError("Fresh freeze and context manifest paths required")
    config = Path(config).resolve()
    spec = read(config)
    original_controls = {key: str(Path(spec[key]).resolve()) for key in
                         ("Scope", "ReferenceManifest", "Map", "Ledger", "SdkWhitelist", "ContractReferences", "NativeCheck", "SdkAudit", "Packages")}
    # Mutable review ledgers and orchestration code must not invalidate a
    # completed freeze when naming resumes. Copies retain exact bytes; no map
    # contents, application inputs or binaries are rewritten.
    snapshot.mkdir()
    controls = {}

    def retain(path, name):
        source = Path(path).resolve()
        target = snapshot / name
        expected = digest(source)
        shutil.copyfile(source, target)
        if digest(source) != expected or digest(target) != expected:
            raise ValueError("Control input changed during snapshot: " + str(source))
        controls[str(source)] = {"Path": str(target), "Sha256": expected}
        return str(target)

    for key in ("Scope", "ReferenceManifest", "Map", "Ledger", "SdkWhitelist", "ContractReferences", "NativeCheck", "SdkAudit", "Packages"):
        spec[key] = retain(spec[key], key + Path(spec[key]).suffix)
    spec["AdditionalPins"] = [retain(path, f"additional-{index}" + Path(path).suffix)
                              for index, path in enumerate(spec.get("AdditionalPins", []))]
    code = retain(__file__, "consolidate_export.py")
    original_config = retain(config, "source-config.json")
    config = snapshot / "config.json"
    fresh_json(config, spec)
    scope, context = read(spec["Scope"]), read(spec["ReferenceManifest"])
    tree = Path(scope["Root"]).resolve()
    source_map = ET.parse(spec["Map"]).getroot()
    modules = scope["Modules"]
    paths = {str(Path(m["Input"]).resolve()) for m in modules}
    if len(paths) != len(modules) or tree != Path(source_map.get("InputDirectory")).resolve():
        raise ValueError("Distinct physical scope and map root required")
    if paths != {str(Path(m["Path"]).resolve()) for m in context["Assemblies"] if m.get("ExportInput")}:
        raise ValueError("Physical scope and pinned reference export inputs differ")
    mapped = {str((tree / m.get("Path").replace("\\", "/")).resolve()) for m in source_map.findall("Module")}
    if not mapped <= paths:
        raise ValueError("Map includes modules outside the first-party scope")
    pins = {}

    def pin(path, expected=None):
        path = str(Path(path).resolve())
        value = digest(path)
        if expected and value != expected.upper():
            raise ValueError("Stale physical input: " + path)
        pins[path] = value

    pin(config)
    pin(code)
    for key in ("Scope", "ReferenceManifest", "Map", "Ledger", "SdkWhitelist", "ContractReferences", "NativeCheck", "SdkAudit", "Packages"):
        pin(spec[key])
    pin(spec["SdkWhitelist"], source_map.get("SdkNameWhitelistSha256"))
    # Maps may refer to the original whitelist/contract path internally. Keep
    # these authoritative paths pinned as well as their immutable copies.
    for key in ("SdkWhitelist", "ContractReferences"):
        pin(original_controls[key], pins[str(Path(spec[key]).resolve())])
    for key in ("NativeCheck", "SdkAudit"):
        report = read(spec[key])
        map_hash = report.get("MapSha256") if key == "SdkAudit" else report.get("BaseMapSha256")
        if not report["Success"] or map_hash != pins[str(Path(spec["Map"]).resolve())]:
            raise ValueError("Map check/audit is not bound to this frozen map")
    checked = read(spec["NativeCheck"])
    if checked["ContractReferenceSha256"] != pins[str(Path(spec["ContractReferences"]).resolve())] or checked["SdkNameWhitelistSha256"] != pins[str(Path(spec["SdkWhitelist"]).resolve())]:
        raise ValueError("Native preflight has different contract or SDK identities")
    sdk = read(spec["SdkAudit"])
    if sdk["SdkVisibleRenamed"] or sdk["SdkReferencedTypesRenamed"]:
        raise ValueError("Protected SDK contracts changed")
    for module in modules:
        pin(module["Input"], module["Sha256"])
    for module in context["Assemblies"]:
        pin(module["Path"], module["Sha256"])
    for cfg in context["Configs"]:
        pin(cfg["Path"], cfg["Sha256"])
    tree_files = sorted(str(p.resolve()) for p in tree.rglob("*") if p.is_file())
    for path in tree_files:
        pin(path)
    runtime = Path(spec["Runtime"])
    runtime_files = sorted(str(p.resolve()) for p in runtime.rglob("*") if p.is_file())
    for path in runtime_files:
        pin(path)
    for path in spec.get("AdditionalPins", []):
        pin(path)
    reference_files = {}
    for directory in spec.get("CompileReferenceDirectories", []):
        directory = str(Path(directory).resolve())
        reference_files[directory] = sorted(str(p.resolve()) for p in Path(directory).iterdir()
                                            if p.is_file() and p.suffix.lower() in (".dll", ".exe"))
        for path in reference_files[directory]:
            pin(path)
    pin(original_config)

    # Translate the already pinned per-input contexts, including newly included
    # compatibility assemblies. Scripts only prepare tool input manifests.
    contexts = {str(Path(c["Source"]).resolve()): c for c in context["Contexts"]}
    configs = {str(Path(c["Source"]).resolve()): c["Path"] for c in context["Configs"]}
    doc = ET.Element("AssemblyContexts")
    support = set()
    for module in modules:
        source = str(Path(module["Input"]).resolve())
        directories = contexts[source]["Directories"]
        attrs = {"Source": source, "Directory": directories[0]}
        if source in configs:
            attrs["Config"] = configs[source]
        ET.SubElement(doc, "Context", attrs)
        support.update(directories[1:])
    contexts_path = Path(output).resolve().with_suffix(".contexts.xml")
    with contexts_path.open("xb") as stream:
        ET.ElementTree(doc).write(stream, encoding="utf-8", xml_declaration=True)
    pin(contexts_path)
    value = {"Format": 2, "Kind": "FrozenApplicationExportInputs", "Config": spec,
             "ControlSnapshots": controls, "Orchestrator": code,
             "OriginalConfig": original_config, "RuntimeFiles": runtime_files,
             "CompileReferenceFiles": reference_files,
             "InputRoot": str(tree), "TreeFiles": tree_files, "Modules": modules,
             "AssemblyContexts": str(contexts_path), "SupportDirectories": sorted(support), "Pins": pins,
             "Limits": "Immutable naming/physical input freeze; no compilation or runtime verdict."}
    fresh_json(output, value)
    print(f"FROZEN: {len(modules)} physical first-party modules; {len(mapped)} mapped modules; {len(pins)} file pins", flush=True)


def verify(frozen):
    for path, expected in frozen["Pins"].items():
        if digest(path) != expected:
            raise ValueError("Frozen input changed: " + path)
    files = sorted(str(p.resolve()) for p in Path(frozen["InputRoot"]).rglob("*") if p.is_file())
    if files != frozen["TreeFiles"]:
        raise ValueError("Original application tree file set changed")
    if "RuntimeFiles" in frozen:
        files = sorted(str(p.resolve()) for p in Path(frozen["Config"]["Runtime"]).rglob("*") if p.is_file())
        if files != frozen["RuntimeFiles"]:
            raise ValueError("Exporter runtime file set changed")
    for directory, expected in frozen.get("CompileReferenceFiles", {}).items():
        files = sorted(str(p.resolve()) for p in Path(directory).iterdir()
                       if p.is_file() and p.suffix.lower() in (".dll", ".exe"))
        if files != expected:
            raise ValueError("Compile reference file set changed: " + directory)


def measured(command, environment, log):
    start, last, peak = time.monotonic(), 0, 0
    with Path(log).open("xb") as stream:
        proc = subprocess.Popen(command, env=environment, stdout=stream, stderr=subprocess.STDOUT)
        parent = psutil.Process(proc.pid)
        while proc.poll() is None:
            rss = 0
            try:
                processes = [parent] + parent.children(recursive=True)
                for child in processes:
                    try:
                        rss += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            peak = max(peak, rss)
            elapsed = time.monotonic() - start
            if elapsed - last >= 30:
                print(f"RUNNING pid={proc.pid}, {elapsed:.1f}s, observed process-tree RSS peak={peak / 2**30:.2f} GiB; {log}", flush=True)
                last = elapsed
            time.sleep(0.25)
    return {"Command": command, "ReturnCode": proc.returncode, "ElapsedSeconds": time.monotonic() - start,
            "ObservedPeakProcessTreeRssBytes": peak, "Log": str(Path(log).resolve()), "LogSha256": digest(log),
            "MeasurementLimit": "250ms process-tree samples; observed peak is a lower bound."}


def run(freeze_path, output, report):
    frozen = read(freeze_path)
    verify(frozen)
    if frozen.get("Orchestrator") and digest(__file__) != frozen["Pins"][frozen["Orchestrator"]]:
        raise ValueError("Run with the snapshotted orchestrator: " + frozen["Orchestrator"])
    out, report = Path(output).resolve(), Path(report).resolve()
    if out.exists() or report.exists():
        raise ValueError("Fresh export directory and result report required")
    if out == Path(frozen["InputRoot"]) or Path(frozen["InputRoot"]) in out.parents:
        raise ValueError("Write exports outside the original application tree")
    spec = frozen["Config"]
    environment = dict(os.environ, DNSPY_PACKAGE_MAP=spec["Packages"], DNSPY_SOURCEMAP_REPORT_ALL="1")
    command = [str(Path(spec["Runtime"]) / "dnSpy.Console.exe"), "--sdk-project", "--source-name-map", spec["Map"],
               "--public-sign", "--app-layout", "--threads", str(spec.get("Threads", 2)), "--no-color", "--no-gac",
               "--app-config", spec["AppConfig"], "--assembly-contexts", frozen["AssemblyContexts"], "-r", "-o", str(out)]
    for directory in frozen["SupportDirectories"]:
        command += ["--asm-path", directory]
    command += [m["Input"] for m in frozen["Modules"]]
    result = {"Format": 1, "Kind": "ConsolidatedApplicationExportBuild", "Freeze": str(Path(freeze_path).resolve()),
              "FreezeSha256": digest(freeze_path), "Output": str(out), "Status": "export-failed", "AppliedToSource": False,
              "RuntimeVerified": False}
    result["Export"] = measured(command, environment, str(report) + ".export.log")
    projects = sorted(str(p) for p in out.rglob("*.csproj")) if out.exists() else []
    result["Projects"] = projects
    if result["Export"]["ReturnCode"] == 0 and len(projects) == len(frozen["Modules"]) and (out / "solution.sln").is_file():
        directories = spec.get("CompileReferenceDirectories", [])
        if directories:
            result["ReferenceResolution"] = measured([str(Path(spec["Runtime"]) / "dnSpy.Console.exe"),
                "--resolve-missing-references", str(out), *directories], environment, str(report) + ".references.log")
        references_ok = not directories or result["ReferenceResolution"]["ReturnCode"] == 0
        result["Status"] = "build-failed" if references_ok else "reference-resolution-failed"
    if result["Status"] == "build-failed":
        result["Build"] = measured(["dotnet", "build", str(out / "solution.sln"), "-c", "Release", "--nologo", "-m:2", "-v:minimal"], environment, str(report) + ".build.log")
        log = Path(result["Build"]["Log"]).read_text(encoding="utf-8-sig", errors="replace")
        result["CompilerErrors"] = sorted(set(line.strip() for line in log.splitlines() if re.search(r": error (?:[A-Z]+\d+:|:)", line)))
        if result["Build"]["ReturnCode"] == 0:
            result["Status"] = "compiled"
            result["AppliedToSource"] = True
    verify(frozen)
    result["FrozenInputsPreserved"] = True
    fresh_json(report, result)
    print(f"{result['Status'].upper()}: {len(projects)} projects; report: {report}", flush=True)
    return 0 if result["Status"] == "compiled" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prepare = commands.add_parser("freeze")
    prepare.add_argument("config")
    prepare.add_argument("output")
    execute = commands.add_parser("run")
    execute.add_argument("freeze")
    execute.add_argument("output")
    execute.add_argument("report")
    inspect = commands.add_parser("verify")
    inspect.add_argument("freeze")
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.config, args.output)
    elif args.action == "verify":
        frozen = read(args.freeze)
        verify(frozen)
        print(f"VERIFIED: {len(frozen['Pins'])} frozen file pins; no compilation or runtime verdict", flush=True)
    else:
        raise SystemExit(run(args.freeze, args.output, args.report))
