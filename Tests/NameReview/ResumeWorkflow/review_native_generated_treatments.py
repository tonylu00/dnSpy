"""Join a proved owner component to the authoritative generated queues, without credits."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from continue_readability import checked, fresh, pin, read


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists(), "Choose a fresh bounded review file"
state = read(args.state)
cursor = read(state["Naming"]["BlockCursor"])
accepted = checked(cursor["Completed"]["DongleComponent"])
assert not accepted["Remaining"] and accepted["Resolved"] == accepted["OriginalFindings"] == 7
manifest = checked(cursor["Disposition"])
plan_pin = cursor["GeneratedIdentityTreatment"]["Plan"]
assert pin(plan_pin["Path"]) == plan_pin
plan = ET.parse(plan_pin["Path"]).getroot()
assert plan.get("MapSha256") == cursor["Map"]["Sha256"]
module = plan.find("Module")
relative = Path(module.get("Input")).relative_to(Path(manifest["Root"])).as_posix()
targets = {int(row.get("Token"), 16): row for row in module.findall("Method")}
selected = {}
stream_pins = []
for label in ("MappedGeneratedDispositions", "ReviewedGeneratedDispositions", "UnflaggedGeneratedDispositions", "RemainingNativeGeneratedDispositions"):
    binding = manifest[label]
    assert pin(binding["Path"]) == binding
    stream_pins.append(binding)
    with Path(binding["Path"]).open(encoding="utf-8-sig") as stream:
        for line in stream:
            row = json.loads(line)
            token = int(row["Token"], 16) if isinstance(row["Token"], str) else row["Token"]
            if row["Module"].replace("\\", "/") != relative or token not in targets:
                continue
            assert token not in selected, "Fixed physical identity occurs in multiple streams"
            assert all(row[key] == module.get(attribute) for key, attribute in (("Sha256", "Sha256"), ("Mvid", "Mvid"), ("Identity", "Identity")))
            assert row["Signature"] == targets[token].get("Signature")
            selected[token] = {"AuthoritativeStream": label, "Preimage": row, "NativeTreatment": dict(targets[token].attrib)}
assert set(selected) == set(targets)
component = checked(accepted["Component"])
build = checked(cursor["Completed"]["New109ProjectBuild"])
source = Path(build["Export"]) / component["ExactCurrentSourceRoot"]["File"]
assert pin(source)["Sha256"] == component["ActualCurrentOwnerSource"]["Sha256"]
source_binding = {"File": component["ExactCurrentSourceRoot"]["File"], "CurrentSource": pin(source),
                  "OriginalExactNativeRoot": component["ExactCurrentSourceRoot"], "OwnerWitnesses": component["NativeOwnerWitnesses"]}
rows = []
for token in sorted(selected):
    row = selected[token]
    row.update(OriginalToken=token, ActualAcceptance=accepted["ActualMetadataAcceptance"], NativeSourceOwner=source_binding,
        ReconstructionCredit=0, NextEvidenceRoute="Replay the normal reconstruction classifier against this exact current source/native owner and compiled metadata; retain prior proofs and reject additional count changes.")
    rows.append(row)
pending = sum(row["Preimage"]["Disposition"] == "generated-needs-reconstruction" for row in rows)
fresh(args.output, {"Format": 1, "Kind": "BoundedNativeGeneratedTreatmentDispositionReview", "Disposition": cursor["Disposition"],
    "Map": cursor["Map"], "Plan": plan_pin, "ComponentAcceptance": cursor["Completed"]["DongleComponent"],
    "StreamInputs": stream_pins, "Rows": rows, "FixedOriginalMethods": len(rows), "AlreadyReconstructed": len(rows) - pending,
    "AuthoritativePendingMethods": pending, "ProposedCounterCredit": 0, "AddedDiscovery": [],
    "Limits": "Metadata acceptance and source evidence are attached to exact existing rows. This review does not mutate the authoritative manifest or retire its queues. Anonymous sentinel type/storage reconciliation remains a separate fixed cohort."})
print(json.dumps({"Review": str(args.output), "FixedOriginalMethods": len(rows), "AlreadyReconstructed": len(rows) - pending,
    "AuthoritativePendingMethods": pending, "CounterCredit": 0, "AddedDiscovery": 0}))
