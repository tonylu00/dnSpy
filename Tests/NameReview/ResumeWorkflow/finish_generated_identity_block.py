"""Resume native output gates and publish a bounded component checkpoint."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from continue_readability import pin, read


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("--block", type=Path, required=True)
parser.add_argument("--regression", type=Path, required=True)
args = parser.parse_args()
receipt = args.block / "result.json"
assert receipt.exists(), "Native export/build is still running or failed; preserve its logs and resume after the build receipt exists."
build = read(receipt)
state = read(args.state)
cursor = read(state["Naming"]["BlockCursor"])
workspace = Path(cursor["Workspace"])
export = Path(build["Export"])


def run(command, log, allowed=(0,)):
    with log.open("x", encoding="utf-8") as output:
        status = subprocess.run([str(value) for value in command], stdout=output, stderr=subprocess.STDOUT).returncode
    assert status in allowed, f"Native gate failed: {status}; {log}"


if not (args.block / "actual-method-contract-proof.json").exists():
    run(["dotnet", "D:/knx_analysis/generated-method-contract-auditor02/GeneratedMethodContractAudit.dll", build["Inputs"]["Plan"]["Path"],
         export / "bin/Knx.Ets.Common.dll", args.block / "actual-method-contract-proof.json"], args.block / "actual-method-contract-audit.log")
if not (args.block / "actual-sentinel-metadata-proof.json").exists():
    construction = read(cursor["Completed"]["ActualSentinelMetadata"]["Path"])["ConstructionProof"]
    assert pin(construction["Path"]) == construction
    run(["dotnet", "D:/knx_analysis/anonymous-sentinel-contract-auditor02/AnonymousSentinelContractAudit.dll", construction["Path"],
         export, args.block / "actual-sentinel-metadata-proof.json"], args.block / "sentinel-contract-audit.log")
if not (args.block / "private-alias-contract.json").exists():
    run(["dotnet", "D:/knx_analysis/anonymous-sentinel-private-contract-auditor01/SourceAliasContracts.dll", export,
         args.block / "private-alias-contract.json"], args.block / "private-alias-audit.log", (0, 1))
private = read(args.block / "private-alias-contract.json")
assert private["Modules"] == 77 and private["IssueCount"] == len(private["Issues"])
manifest = args.block / "stage-manifest.json"
if not manifest.exists():
    run(["pwsh", "-NoProfile", "-File", workspace / "Build/Stage-RecompiledTree.ps1", "-InputDirectory", state["Pass"]["SourceTree63"],
         "-ExportDirectory", export, "-OutputDirectory", args.block / "stage"], args.block / "stage.log")
staging = read(manifest)
for overlay in staging["Overlays"]:
    assert pin(overlay["Built"])["Sha256"] == overlay["Hash"]
    assert pin(Path(staging["Output"]) / overlay["Relative"])["Sha256"] == overlay["Hash"]
for label in ("visible-contract-audit", "sdk-contract-audit"):
    output = args.block / label
    if not (output / "result.json").exists():
        command = ["pwsh", "-NoProfile", "-File", workspace / "Tests/Invoke-SdkSourceContractAudit.ps1", "-DnlibPath",
            "D:/knx_analysis/parent-closure-alias-native-runtime11/dnlib.dll", "-ExportDirectory", export, "-OutputDirectory", output]
        if label == "sdk-contract-audit":
            command += ["-StagingManifest", manifest, "-SdkWhitelist", "D:/knx_analysis/application-name-pass01/sdk-name-whitelist63-v2.xml"]
        run(command, args.block / (label + ".log"))
    audit = read(output / "result.json")
    assert audit["Projects"] == 109 and audit["IssueCount"] == 0
review = args.block / "generated-treatment-disposition-review.json"
next_command = f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/review_native_generated_treatments.py --state {args.state.as_posix()} --output {review.as_posix()}'
subprocess.run([sys.executable, str(Path(__file__).with_name("accept_generated_identity_block.py")), "--state", str(args.state),
    "--block", str(args.block), "--regression", str(args.regression), "--next-command", next_command], check=True)
