"""Publish exact native generated-method acceptance against the frozen finding cohort."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from continue_readability import checked, fresh, now, pin, publish_navigation, read


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("--block", type=Path, required=True)
parser.add_argument("--regression", type=Path, required=True)
parser.add_argument("--next-command", required=True)
args = parser.parse_args()
before = pin(args.state)
state = read(args.state)
cursor = copy.deepcopy(read(state["Naming"]["BlockCursor"]))
result = read(args.block / "result.json")
assert result["Projects"] == 109 and result["AppliedToSource"] and not result["GeneratedSourceEdited"]
inputs = result["Inputs"]
for key in ("Plan", "Core", "Contracts", "SelectedMap", "PackageAuthority", "BuildLog"):
    binding = result[key] if key == "BuildLog" else inputs[key]
    assert pin(binding["Path"]) == binding, key
assert inputs["ParentMap"]["Sha256"] == state["Maps"]["63"]["Sha256"] == inputs["SelectedMap"]["Sha256"]
plan = ET.parse(inputs["Plan"]["Path"]).getroot()
proof = read(args.block / "actual-method-contract-proof.json")
assert proof["Plan"] == inputs["Plan"]
for key in ("Original", "Compiled", "Inspector"):
    assert pin(proof[key]["Path"]) == proof[key], key
regression = read(args.regression)
assert regression["PlanSha256"] == inputs["Plan"]["Sha256"]
assert regression["ProducerSha256"] == inputs["Core"]["Sha256"]
methods = plan.find("Module").findall("Method")
tokens = {int(row.get("Token"), 16) for row in methods}
assert tokens == {row["OriginalToken"] for row in proof["Rows"]}
assert len(tokens) == proof["OriginalFixedFindingsResolved"] == len(regression["Rows"])
assert all(row["ExactNormalizedBehavior"] and row["OriginalMethodMetadataRestored"] for row in proof["Rows"])
assert not proof["RuntimeVerified"]
for folder in ("visible-contract-audit", "sdk-contract-audit"):
    audit = read(args.block / folder / "result.json")
    assert audit["Projects"] == 109 and audit["IssueCount"] == 0
cohort = checked(cursor["FixedCohorts"]["PrivateMetadata"])
original = Counter(cohort["Original"])
discoveries = Counter(cohort["AddedDiscovery"])
audit_path = args.block / "private-alias-contract.json"
current = Counter(read(audit_path)["Issues"])
assert not current - (original + discoveries), "New findings require separate review"
resolved = original - current
expected = Counter({f'{proof["Original"]["Path"]} {token:08X}: original method name/signature missing or ambiguous': 1 for token in tokens})
assert resolved == expected, "Only the exact proved fixed findings can be credited"
assert discoveries & current == discoveries, "Prior discoveries are a separate unresolved cohort"
delta_path = args.block / "fixed-private-cohort-delta.json"
delta = {"Format": 1, "Kind": "FixedIdentityBoundPrivateFindingDelta", "OriginalCohort": cursor["FixedCohorts"]["PrivateMetadata"],
    "CurrentAudit": pin(audit_path), "Acceptance": pin(args.block / "actual-method-contract-proof.json"),
    "Original": sum(original.values()), "OriginalResolved": sum(resolved.values()),
    "OriginalRemaining": sum((original & current).values()), "ExistingAddedDiscovery": sum(discoveries.values()),
    "NewFailures": 0, "NewAddedDiscovery": 0, "CurrentRemaining": sum(current.values()), "ResolvedFindings": dict(resolved)}
fresh(delta_path, delta)
component = checked(cursor["PreparedPrivateComponent"])
pending = [finding for finding in component["OriginalPendingFindings"] if finding in current]
component_result = args.block / "dongle-component-acceptance.json"
fresh(component_result, {"Format": 1, "Kind": "FixedDongleLicenseComponentAcceptance", "Component": cursor["PreparedPrivateComponent"],
    "OriginalFindings": component["OriginalPendingCount"], "Resolved": sum(resolved.values()), "Remaining": pending,
    "Plan": inputs["Plan"], "NativeRegression": pin(args.regression), "ActualMetadataAcceptance": pin(args.block / "actual-method-contract-proof.json"),
    "CohortDelta": pin(delta_path), "AddedDiscovery": [], "SemanticNamesAdded": 0,
    "GeneratedSourceModified": False, "RuntimeVerified": False,
    "Boundary": "Original runtime identities restored by the native build task; lambda bodies remain reconstructed in their readable owners. Authoritative generated-disposition counters require normal proof replay."})
cursor.update(UpdatedUtc=now(), CurrentStage="dongle-generated-method-native-source-acceptance",
    CompletedStage=not pending, BroaderReadabilityGoalClosed=False, Running=[], RestoreRequired=False)
if "PreparedDongleNativeAcceptance" in cursor:
    cursor["PreparedDongleNativeAcceptance"].update(FixedPrivateCohortCreditPendingFinalAudit=False,
        FixedPrivateCohortDelta=pin(delta_path), FinalSourceAcceptanceVerified=True)
cursor["Completed"].update(DongleComponent=pin(component_result), PrivateCohortDelta=pin(delta_path),
    New109ProjectBuild=pin(args.block / "result.json"), CurrentNativeBuildInputs=pin(args.block / "inputs.json"),
    Staging=pin(args.block / "stage-manifest.json"), SdkContracts=pin(args.block / "sdk-contract-audit/result.json"),
    VisibleContracts=pin(args.block / "visible-contract-audit/result.json"))
cursor["GeneratedIdentityTreatment"] = {"Authority": "Supplemental exact physical-method treatment, bound to the unchanged authoritative naming map and dependency dispositions.",
    "Plan": inputs["Plan"], "Map": inputs["ParentMap"], "PackageAuthority": inputs["PackageAuthority"],
    "ApplyWith": "DNSPY_GENERATED_IDENTITY_PLAN", "NativeRuntime": str(Path(inputs["Core"]["Path"]).parent),
    "NoSemanticNamingOrDispositionCounterCredit": True}
cursor["Remaining"].update(PrivateOriginalFindings=delta["OriginalRemaining"], PrivatePriorDiscovery=delta["ExistingAddedDiscovery"],
    DongleComponentOriginalFindings=pending, NativeRepairRuntimePending=True, BroaderRuntimePending=True)
cursor["Counters"].update(StrictPrivateAliasFindingsRemaining=delta["CurrentRemaining"],
    PrivateOriginalFindingsResolved=delta["OriginalResolved"], DongleOriginalMethodsVerified=len(tokens),
    GeneratedDispositionRowsRetired=0, NewSemanticNames=0)
sentinel = args.block / "actual-sentinel-metadata-proof.json"
if sentinel.exists():
    receipt = read(sentinel)
    assert len(receipt["Rows"]) == 2 and not receipt["RuntimeVerified"]
    assert all(row["OriginalTypeNamesAndPrivateFieldStorageVerified"] and not row["AdditionalMetadataDiscovery"] for row in receipt["Rows"])
    cursor["Completed"]["ActualSentinelMetadata"] = pin(sentinel)
cursor["NextItems"] = [
    {"Task": "review exact native treatments against authoritative generated dispositions", "Detail": args.next_command},
    {"Task": "new-tool runtime and broader runtime gates", "Detail": "Use the separate native stage and test-mcp; preserve running original ETS, original binaries and profile. Language switching and broader Apps/physical scenarios remain open."},
    {"Task": "remaining private metadata owner groups and ETS6.4 non-method transfer", "Detail": f'{delta["OriginalRemaining"]} fixed original findings and {delta["ExistingAddedDiscovery"]} prior discoveries remain separate; type/field/parameter/local transfer and four binary modules remain open.'}]
cursor["NextCommand"] = args.next_command
cursor["Status"] = f'Active broader goal. Dongle fixed component {sum(resolved.values())}/{component["OriginalPendingCount"]} original findings resolved, current109 builds and SDK/visible contracts pass. Fixed private cohort {delta["OriginalRemaining"]}/{delta["Original"]} remains, plus {delta["ExistingAddedDiscovery"]} prior discoveries. Native runtime, generated proof reconciliation, naming/value queues and ETS6.4 transfer remain open.'
detail = state["Naming"]["ConsolidatedVerification"]
detail.update(FixedPriorPrivateMetadataIssues=delta["OriginalRemaining"], PrivateMetadataMeaning=f'{delta["OriginalRemaining"]} retained original unresolved findings; {delta["OriginalResolved"]} exact original findings resolved; {delta["ExistingAddedDiscovery"]} prior discoveries remain; zero new findings.',
    NativeGeneratedMethodAcceptance=pin(component_result))
publish_navigation(args.state, before, state, args.block / "cursor-native-method-acceptance.json", cursor)
print(json.dumps({"StageComplete": not pending, "BroaderReadabilityGoalClosed": False, "FixedOriginalResolved": sum(resolved.values()),
    "FixedOriginalRemaining": delta["OriginalRemaining"], "PriorDiscovery": delta["ExistingAddedDiscovery"], "NewDiscovery": 0, "NextCommand": args.next_command}))
