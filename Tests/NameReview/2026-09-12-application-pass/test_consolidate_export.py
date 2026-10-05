"""Exercise immutable replay controls and physical/runtime drift without exporting ETS."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile


def main():
    assertions = 0
    with tempfile.TemporaryDirectory(prefix="ets-freeze-regression-") as folder:
        root = Path(folder)
        code = root / "orchestrator.py"
        shutil.copyfile(Path(__file__).with_name("consolidate_export.py"), code)
        module = importlib.util.spec_from_file_location("frozen_export_fixture", code)
        helper = importlib.util.module_from_spec(module)
        module.loader.exec_module(helper)

        def write(name, value):
            path = root / name
            path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
            return str(path)

        def check(condition):
            nonlocal assertions
            assert condition
            assertions += 1

        def rejects(action):
            try:
                action()
            except ValueError:
                check(True)
            else:
                raise AssertionError("Expected drift/fresh-path rejection")

        tree = root / "application"
        runtime = root / "runtime"
        references = root / "references"
        for directory in (tree, runtime, references):
            directory.mkdir()
        assembly = write("application/Owner.dll", "exact physical owner")
        config = write("application/Owner.dll.config", "original config")
        executable = write("runtime/dnSpy.Console.exe", "exact runtime")
        reference = write("references/Compatibility.dll", "exact compatibility reference")
        whitelist = write("whitelist.xml", "<Whitelist />")
        contracts = write("contracts.json", {})
        source_map = write("map.xml", '<SourceNameMap InputDirectory="' + str(tree) + '" SdkNameWhitelistSha256="' + helper.digest(whitelist) + '"><Module Path="Owner.dll" /></SourceNameMap>')
        scope = write("scope.json", {"Root": str(tree), "Modules": [{"Input": assembly, "Sha256": helper.digest(assembly)}]})
        context = write("context.json", {"Assemblies": [{"Path": assembly, "Sha256": helper.digest(assembly), "ExportInput": True}],
                    "Contexts": [{"Source": assembly, "Directories": [str(tree), str(references)]}],
                    "Configs": [{"Source": assembly, "Path": config, "Sha256": helper.digest(config)}]})
        ledger = write("ledger.json", {"Accepted": "original review"})
        native = write("native.json", {"Success": True, "BaseMapSha256": helper.digest(source_map),
                    "ContractReferenceSha256": helper.digest(contracts), "SdkNameWhitelistSha256": helper.digest(whitelist)})
        audit = write("audit.json", {"Success": True, "MapSha256": helper.digest(source_map), "SdkVisibleRenamed": 0, "SdkReferencedTypesRenamed": 0})
        packages = write("packages.txt", "original package decisions")
        mutable = write("mutable-helper.cs", "original native code")
        spec = {"Scope": scope, "ReferenceManifest": context, "Map": source_map, "Ledger": ledger,
                "SdkWhitelist": whitelist, "ContractReferences": contracts, "NativeCheck": native, "SdkAudit": audit,
                "Packages": packages, "Runtime": str(runtime), "AppConfig": config,
                "CompileReferenceDirectories": [str(references)], "AdditionalPins": [mutable, whitelist]}
        settings = write("input.json", spec)
        freeze_path = root / "freeze.json"
        helper.freeze(settings, freeze_path)
        frozen = helper.read(freeze_path)
        helper.verify(frozen)
        check(frozen["Format"] == 2 and len(frozen["Modules"]) == 1)
        for key in ("Map", "Ledger", "Scope", "ReferenceManifest", "NativeCheck", "SdkAudit", "Packages"):
            check(helper.digest(frozen["Config"][key]) == helper.digest(spec[key]))
        check(helper.digest(frozen["OriginalConfig"]) == helper.digest(settings))
        check(frozen["AssemblyContexts"] in frozen["Pins"])
        check(helper.read(frozen["Config"]["ReferenceManifest"])["Assemblies"][0]["Path"] == assembly)
        for path in (ledger, mutable, settings, code, source_map, scope, context, native, audit, packages):
            Path(path).write_text("later mutable input", encoding="utf-8")
        helper.verify(frozen)
        check(True)
        rejects(lambda: helper.run(freeze_path, root / "unused-export", root / "unused-report"))
        check(not (root / "unused-export").exists())
        rejects(lambda: helper.freeze(settings, freeze_path))

        def drift(path, contents):
            before = Path(path).read_bytes()
            Path(path).write_bytes(contents)
            rejects(lambda: helper.verify(frozen))
            Path(path).write_bytes(before)
            helper.verify(frozen)

        for path in (assembly, config, executable, reference, whitelist, contracts,
                     frozen["Config"]["Ledger"], frozen["Orchestrator"], frozen["AssemblyContexts"]):
            drift(path, b"changed pinned input")
        for directory, name in ((tree, "Added.dll"), (runtime, "Added.dll"), (references, "Added.exe")):
            added = directory / name
            added.write_bytes(b"additional physical input")
            rejects(lambda: helper.verify(frozen))
            added.unlink()
            helper.verify(frozen)
        check(not (root / "unused-report").exists())
        print(f"PASS: {assertions} immutable-control/physical-context/runtime drift guards; no ETS export or build")


if __name__ == "__main__":
    main()
