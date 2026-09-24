"""Export the ETS 6.3 first-party modules one process at a time and build each project.

Why one module per process: the MSBuild exporter keeps every decompiled module's AST
alive until the project files are written, so a single export of the whole first-party
set grows past 70 GB. One module per process keeps the peak at a single module.

Third-party assemblies are never decompiled: the writer turns the ones listed in
nuget-packages.txt into PackageReference items and leaves the rest as untouched binaries.

Usage: python export-firstparty.py [--out DIR] [--only m1,m2] [--skip-build]
"""
import argparse, json, os, re, shutil, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path

PASS = Path(r"D:\knx_analysis\application-name-pass01")
TREE = Path(r"D:\knx_analysis\ETS6.3_api_preserved4")
EXE = Path(r"D:\git\dnSpy\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe")
MAP = PASS / "names63-staged-v381.xml"
PACKAGES = Path(r"D:\knx_analysis\perf-now\nuget-packages.txt")


def per_module_maps():
    root = ET.parse(MAP).getroot()
    out = []
    for module in root.findall("Module"):
        rel = (module.get("Path") or "").replace("\\", "/")
        name = rel.rsplit("/", 1)[-1]
        doc = ET.Element("SourceNameMap", dict(root.attrib))
        doc.append(module)
        path = PASS / ("map-" + name + ".xml")
        ET.ElementTree(doc).write(path, encoding="utf-8", xml_declaration=True)
        out.append((name, (TREE / rel).resolve(), path))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"D:\knx_analysis\ets63-source-batch")
    ap.add_argument("--only", default="")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    only = {x for x in args.only.split(",") if x}

    env = dict(os.environ)
    env["DNSPY_PACKAGE_MAP"] = str(PACKAGES)
    env["DNSPY_SOURCEMAP_REPORT_ALL"] = "1"

    results = []
    for name, source, map_path in per_module_maps():
        if only and name not in only:
            continue
        module_out = out_root / name.replace(".dll", "").replace(".exe", "")
        if not source.exists():
            results.append((name, "missing input"))
            continue
        if module_out.exists():
            shutil.rmtree(module_out)
        proc = subprocess.run([str(EXE), "--source-name-map", str(map_path), "--public-sign",
                               "-o", str(module_out), str(source)],
                              env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        projects = list(module_out.rglob("*.csproj"))
        if proc.returncode != 0 or not projects:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()
            results.append((name, "export failed: " + (tail[0] if tail else "?")))
            continue
        if args.skip_build:
            results.append((name, "exported"))
            continue
        build = subprocess.run(["dotnet", "build", str(projects[0]), "-c", "Release", "--nologo", "-v", "q"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
        errors = [l.strip() for l in (build.stdout or "").splitlines() if ": error " in l]
        results.append((name, "build OK" if build.returncode == 0 and not errors else "build failed: " + (errors[0] if errors else str(build.returncode))))

    report = Path(out_root) / "export-report.txt"
    report.write_text("\n".join(f"{n}: {r}" for n, r in results), encoding="utf-8")
    ok = sum(1 for _, r in results if r.startswith("build OK") or r == "exported")
    print(f"modules: {len(results)}  ok: {ok}  report: {report}")
    for n, r in results:
        if not (r.startswith("build OK") or r == "exported"):
            print(f"  FAILED {n}: {r}")


if __name__ == "__main__":
    main()
