"""Bounded ETS resume summaries and comparable, identity-bound queue deltas.

Read-only navigation: never substitutes for native map or disposition proof gates.
Uses only the standard library, and deliberately imports no workflow validators.
"""
import argparse
import hashlib
import json
from pathlib import Path
from storage_guard import space_status


WORK = {
    "semantic": ("SemanticDefinitions", "LegacyAliasDefinitions"),
    "projected-values": ("ProjectedValues",),
    "reconstruction": ("ReconstructionDefinitions",),
    "generated-dispositions": ("GeneratedDispositionDefinitions",),
}
METRICS = (
    "RawLexicalCandidateDenominator", "RemainingActionableSemanticDefinitions",
    "ProjectedValuesNeedingReview", "RemainingReconstructionDefinitions",
    "RemainingGeneratedDispositionDefinitions", "NativeGeneratedArtifactUniverse",
    "GeneratedArtifactsVerifiedReconstructed", "FirstPartyParametersImproved",
    "FirstPartyLocalsImproved",
)
LIMITS = ("Navigation only: hashes bind recorded queues; source/behavior proofs are not replayed. "
          "Run existing native/checkpoint/export gates before mutations. Categories overlap; do not sum them.")


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_bytes())


def pinned(binding):
    data = Path(binding["Path"]).read_bytes()
    if digest(data) != binding["Sha256"].upper():
        raise ValueError("Changed pinned file: " + binding["Path"])
    return data


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def physical(path):
    return str(path).replace("\\", "/").casefold()


def token(value):
    return int(value, 16) if isinstance(value, str) else int(value)


def module_id(row):
    return (physical(row["Path"]), row["Sha256"].upper(), row["Mvid"].lower(), row["Identity"])


def load_view(path, binding=None):
    data = pinned(binding) if binding else Path(path).read_bytes()
    manifest = json.loads(data)
    clusters = json.loads(pinned(manifest["OwnerClusters"]))
    modules = {physical(m["Path"]): m for m in manifest["Modules"]}
    if len(modules) != len(manifest["Modules"]):
        raise ValueError("Duplicate physical module")
    for row in clusters:
        if physical(row["Module"]) not in modules:
            raise ValueError("Owner outside physical scope: " + row["Module"])
    return manifest, clusters, modules, digest(data)


def counts(row):
    return {work: sum(len(row.get(field, [])) for field in fields)
            for work, fields in WORK.items()}


def choose(clusters, work, limit):
    selected = [r for r in clusters if counts(r)[work]]
    selected.sort(key=lambda r: (-counts(r)[work], physical(r["Module"]), r["Owner"]))
    # A preview is deliberately not a full owner export or proof replay.
    return [{"Module": r["Module"], "Owner": r["Owner"], "QueueEntries": counts(r)}
            for r in selected[:limit]]


def clip(value, limit=900):
    value = str(value)
    return value if len(value) <= limit else value[:limit] + " [see bound state for remainder]"


def cursor_view(state, issues):
    """Read only the published cursor; never walk PreviousCursor/history links."""
    path = state["Naming"].get("BlockCursor")
    if not path:
        return {}, None, None
    data = Path(path).read_bytes()
    cursor = json.loads(data)
    for key, expected in (("Map", state["Maps"]["63"]),
                          ("Disposition", state["Naming"]["Dispositions"])):
        actual = cursor.get(key)
        if actual and (physical(actual["Path"]) != physical(expected["Path"]) or
                       actual["Sha256"].upper() != expected["Sha256"].upper()):
            issues.append("Cursor " + key + " differs from STATE; publication may be in progress.")
    cohorts = cursor.get("FixedCohorts", {})
    for name in ("SourceRoots", "PrivateMetadata"):
        pin = cohorts.get(name)
        if pin and file_hash(pin["Path"]) != pin["Sha256"].upper():
            issues.append("Changed fixed cohort: " + name)
    return cursor, path, data


def overall_progress(cursor):
    counters, remaining = cursor.get("Counters", {}), cursor.get("Remaining", {})
    return {
        "SourceRoots": {"Original": counters.get("SourceRootsOriginal"),
                        "Verified": counters.get("SourceRootsVerified"),
                        "Remaining": remaining.get("SourcePhysicalRootProjectionObligations")},
        "PrivateMetadata": {"Original": counters.get("PrivateOriginal"),
                            "Resolved": counters.get("PrivateOriginalResolved"),
                            "Remaining": remaining.get("PrivateOriginalFindings"),
                            "PriorDiscovery": remaining.get("PrivatePriorDiscovery")},
        "Remaining": {k: remaining[k] for k in (
            "AuthoritativeGeneratedDispositionRowsPending", "ReconstructionReviewsPending",
            "ProjectedValuesPending", "UnsupportedLegacyAliases", "NativeRepairRuntimePending",
            "BroaderRuntimePending", "Ets64TypeFieldParameterLocalTransferPending",
            "Ets64OriginalBinaryModulesOutsideSourceCohort") if k in remaining},
    }


def brief(state_path, work=None, limit=3):
    state_path = Path(state_path)
    before = state_path.read_bytes()
    state = json.loads(before)
    current = state["Maps"]["63"]
    pinned(current)
    binding = state["Naming"]["Dispositions"]
    manifest, clusters, _, manifest_hash = load_view(binding["Path"], binding)
    inputs = manifest["Inputs"]
    issues = []
    cursor, cursor_path, cursor_bytes = cursor_view(state, issues)
    if current["Sha256"].upper() != inputs["map"]["Sha256"].upper():
        issues.append("Current map and published disposition map differ; publication may be in progress.")
    try:
        if file_hash(inputs["ledger"]["Path"]) != inputs["ledger"]["Sha256"].upper():
            issues.append("Ledger differs from published disposition input; publication may be in progress.")
    except OSError:
        issues.append("Published ledger is unavailable.")
    if before != state_path.read_bytes() or (cursor_path and cursor_bytes != Path(cursor_path).read_bytes()):
        raise ValueError("STATE changed during read; retry after the writer checkpoints")
    progress = manifest["Progress"]  # Never silently mix newer state counts with an older manifest.
    state_progress = state["Naming"].get("Progress", {})
    if any(state_progress.get(k) != progress.get(k) for k in METRICS):
        issues.append("STATE and published disposition counters differ; counters below belong to the manifest.")
    next_items = state["Naming"].get("NextItems", [])
    if cursor.get("NextItems") and cursor["NextItems"] != next_items:
        issues.append("Cursor and STATE next items differ; publication may be in progress.")
    totals = overall_progress(cursor)
    for name, done in (("SourceRoots", "Verified"), ("PrivateMetadata", "Resolved")):
        row = totals[name]
        if all(type(row[k]) is int for k in ("Original", done, "Remaining")):
            if row["Original"] != row[done] + row["Remaining"]:
                issues.append(name + " counters do not reconcile; do not infer progress.")
    result = {
        "Kind": "EtsNamingResumeBrief", "StateSha256": digest(before),
        "Publication": "incomplete-or-stale" if issues else "bindings-consistent",
        "Issues": issues, "Workspace": state["Pass"]["DnspyRepo"],
        "CheckpointDirectory": state["Pass"]["CheckpointDir"],
        "NativeTool": state["Pass"]["ToolCli"],
        "CurrentMap": current["Path"], "CurrentMapSha256": current["Sha256"],
        "AppliedToSource": current.get("AppliedToSource", False),
        "DispositionManifest": binding["Path"], "DispositionSha256": manifest_hash,
        "DispositionMap": inputs["map"]["Path"],
        "RecordedProgress": {k: progress.get(k) for k in METRICS},
        "NextItem": {k: clip(v) for k, v in next_items[0].items()} if next_items else None,
        "WorkCategory": work or (None if cursor else "projected-values"),
        "OwnerPreview": [] if issues or (cursor and work is None) else choose(clusters, work or "projected-values", limit),
        "NextAction": ("Preserve the active writer. Re-read after a completed checkpoint; do not auto-repair shared state."
                       if issues else "Continue the recorded next item; consult a category-specific helper only when needed."),
        "Limits": LIMITS,
    }
    if cursor:
        stage = cursor.get("StageProgress", {})
        command = cursor.get("NextCommand")
        result.update({
            "Cursor": {"Path": cursor_path, "Sha256": digest(cursor_bytes), "Bytes": len(cursor_bytes)},
            "Goal": {"RecordedClosed": cursor.get("BroaderReadabilityGoalClosed"),
                     "StageComplete": cursor.get("CompletedStage"),
                     "CompletionAuthorizedByBrief": False},
            "CurrentWork": {"Stage": clip(cursor.get("CurrentStage", ""), 240),
                            "LastCompleted": clip(stage.get("LastCompleted", ""), 240),
                            "CurrentBlockFindings": stage.get("CurrentBlockFindings"),
                            "CurrentBlockComplete": stage.get("CurrentBlockComplete"),
                            "NextCommand": command if isinstance(command, str) and len(command) <= 4096 and not issues else None},
            "OverallProgress": totals,
            "FixedCohorts": {k: v for k, v in cursor.get("FixedCohorts", {}).items()
                             if k in ("SourceRoots", "PrivateMetadata")},
            "Running": cursor.get("Running", [])[:5],
            "RunningCount": len(cursor.get("Running", [])),
            "RestoreRequired": cursor.get("RestoreRequired"),
        })
        if not issues:
            result["NextAction"] = (
                "Check the recorded job and its owner before resuming; do not launch a duplicate build or steal an active writer."
                if result["RunningCount"] else
                "Execute the current block, checkpoint its outcome, then continue the next ready block. A checkpoint is not a stop condition.")
    volumes = space_status()
    result["Storage"] = {"Volumes": volumes,
                         "HeavyWorkReady": all(v["FreeGiB"] >= v["ReserveGiB"] for v in volumes),
                         "Launcher": str(Path(__file__).with_name("storage_guard.py")),
                         "ScratchRoot": "D:/knx_analysis/workflow-scratch"}
    return result


def snapshot(summary):
    if summary["Publication"] != "bindings-consistent":
        raise ValueError("Cannot snapshot an inconsistent publication")
    return {"Kind": "EtsReadabilityProgressSnapshot", "Format": 1,
            **{k: summary.get(k) for k in ("StateSha256", "Cursor", "CurrentMapSha256",
                                          "DispositionSha256", "FixedCohorts", "OverallProgress", "RecordedProgress")}}


def progress_since(summary, path):
    old = read(path)
    if old.get("Kind") != "EtsReadabilityProgressSnapshot" or old.get("Format") != 1:
        raise ValueError("Not a supported progress snapshot")
    if summary["Publication"] != "bindings-consistent":
        return {"Comparable": False, "Reason": "Current publication is inconsistent"}
    result = {"Snapshot": str(path), "FixedCohorts": {}, "RecordedCounterChanges": {}}
    for name, done in (("SourceRoots", "Verified"), ("PrivateMetadata", "Resolved")):
        a = (old.get("OverallProgress") or {}).get(name, {})
        b = summary.get("OverallProgress", {}).get(name, {})
        old_pin = (old.get("FixedCohorts") or {}).get(name)
        pin = summary.get("FixedCohorts", {}).get(name)
        comparable = (bool(pin) and pin == old_pin and a.get("Original") == b.get("Original")
                      and all(type(row.get(k)) is int for row in (a, b) for k in (done, "Remaining")))
        row = {"Comparable": comparable}
        if comparable:
            row.update({"CompletedDelta": b[done] - a[done], "RemainingBefore": a["Remaining"],
                        "RemainingNow": b["Remaining"]})
        else:
            row["Reason"] = "Missing or changed fixed cohort/denominator; no closure claim"
        result["FixedCohorts"][name] = row
    for key, value in summary["RecordedProgress"].items():
        previous = (old.get("RecordedProgress") or {}).get(key)
        if type(previous) is int and type(value) is int and previous != value:
            result["RecordedCounterChanges"][key] = {"Before": previous, "Now": value, "Delta": value - previous}
    result["Limits"] = "Recorded counter changes are not exact queue or proof deltas; use compare for identity-bound queue changes."
    return result


def section(state_path, key, max_chars=6000):
    """Explicit cursor field retrieval with an output cap, never silent truncation."""
    before = Path(state_path).read_bytes()
    state = json.loads(before)
    path = state["Naming"]["BlockCursor"]
    data = Path(path).read_bytes()
    value = json.loads(data)
    for part in key.split("."):
        value = value[part]
    result = {"Cursor": path, "CursorSha256": digest(data), "Key": key, "Value": value}
    if before != Path(state_path).read_bytes() or data != Path(path).read_bytes():
        raise ValueError("STATE/cursor changed during read; retry after publication")
    if len(json.dumps(result, ensure_ascii=True, indent=2)) > max_chars:
        children = ", ".join(list(value)[:12]) if isinstance(value, dict) else "select a smaller field"
        raise ValueError("Section exceeds output limit; select a child key: " + children)
    return result


def queues(clusters, modules):
    result = {work: set() for work in WORK}
    for row in clusters:
        prefix = module_id(modules[physical(row["Module"])])
        for work, fields in WORK.items():
            for field in fields:
                for value in row.get(field, []):
                    if work == "projected-values":
                        # Preserve distinct source projections and their owners; do not count
                        # a shared captured field as one interchangeable source value.
                        identity = (token(value["Token"]), token(value["OwnerToken"]),
                                    token(value["RootTypeToken"]) if "RootTypeToken" in value else None,
                                    value.get("BindingKind"), value["SourceName"])
                    else:
                        identity = (token(value),)
                    result[work].add(prefix + identity)
    return result


def comparison(before_path, after_path):
    old, old_clusters, old_modules, old_hash = load_view(before_path)
    new, new_clusters, new_modules, new_hash = load_view(after_path)
    left, right = queues(old_clusters, old_modules), queues(new_clusters, new_modules)
    old_ids = {module_id(m) for m in old_modules.values()}
    new_ids = {module_id(m) for m in new_modules.values()}
    changed_modules = {p for p in old_modules.keys() & new_modules.keys()
                       if module_id(old_modules[p]) != module_id(new_modules[p])}
    baseline_changes = sorted(p for p in old_modules.keys() & new_modules.keys()
                              if old_modules[p].get("SourceBaselineMapSha256") !=
                              new_modules[p].get("SourceBaselineMapSha256"))
    compatible = not changed_modules and not baseline_changes
    projection_identity_complete = all("RootTypeToken" in v and "BindingKind" in v
                                       for c in (old_clusters, new_clusters)
                                       for row in c for v in row.get("ProjectedValues", []))
    categories = {}
    for work in WORK:
        a, b = left[work], right[work]
        can_compare = compatible and (work != "projected-values" or projection_identity_complete)
        row = {"Unit": "source projection" if work == "projected-values" else "physical definition",
               "BeforePending": len(a), "AfterPending": len(b), "NetChange": len(b) - len(a),
               "Comparable": can_compare}
        if work == "projected-values" and not projection_identity_complete:
            row["Limitation"] = "Legacy projection records lack full source-root/binding identity; no exact cohort claim."
        if can_compare:
            row.update({"OriginalPendingCohort": len(a), "OriginalCohortStillQueued": len(a & b),
                        "OriginalCohortNoLongerQueued": len(a - b),
                        "AddedOrReopenedQueueEntries": len(b - a)})
        categories[work] = row
    return {
        "Kind": "EtsNamingQueueComparison",
        "Before": {"Path": str(before_path), "Sha256": old_hash},
        "After": {"Path": str(after_path), "Sha256": new_hash},
        "Comparable": compatible and projection_identity_complete,
        "PhysicalAndSourceBaselineComparable": compatible,
        "ChangedPhysicalModules": sorted(changed_modules),
        "ChangedSourceBaselines": baseline_changes,
        "AddedPhysicalModules": len(new_ids - old_ids), "RemovedPhysicalModules": len(old_ids - new_ids),
        "Categories": categories,
        "RecordedCounterChanges": {k: {"Before": old["Progress"].get(k), "After": new["Progress"].get(k)}
                                   for k in METRICS if old["Progress"].get(k) != new["Progress"].get(k)},
        "Limits": (LIMITS + " No-longer-queued is not proof of a rename/reconstruction. Added-or-reopened "
                   "cannot distinguish discovery from regression without earlier disposition history. "
                   "Changed source baselines/physical identities suppress cohort claims."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("brief", help="Bounded startup navigation; no full proof replay")
    p.add_argument("--state", type=Path, default=Path("D:/knx_analysis/STATE.json"))
    p.add_argument("--work", choices=tuple(WORK), help="Opt in to owner selection; active block takes priority")
    p.add_argument("--limit", type=int, choices=range(1, 11), default=3)
    p.add_argument("--since", type=Path, help="Compare recorded progress with a small saved snapshot")
    p = commands.add_parser("snapshot", help="Save a small comparison baseline; does not publish shared state")
    p.add_argument("--state", type=Path, default=Path("D:/knx_analysis/STATE.json"))
    p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser("section", help="Read one current cursor field without loading history into context")
    p.add_argument("--state", type=Path, default=Path("D:/knx_analysis/STATE.json"))
    p.add_argument("--key", required=True, help="Dot-separated cursor key, for example StageProgress")
    p.add_argument("--max-chars", type=int, choices=range(1000, 12001), default=6000)
    p = commands.add_parser("compare", help="Compare exact pending cohorts using pinned owner queues")
    p.add_argument("--before", type=Path, required=True)
    p.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "brief":
            result = brief(args.state, args.work, args.limit)
            if args.since:
                result["SinceSnapshot"] = progress_since(result, args.since)
        elif args.command == "snapshot":
            result = snapshot(brief(args.state))
            # Never overwrite a baseline or an active writer's file.
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, ensure_ascii=True)
            result = {"Snapshot": str(args.output), "Sha256": file_hash(args.output)}
        elif args.command == "section":
            result = section(args.state, args.key, args.max_chars)
        else:
            result = comparison(args.before, args.after)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, "Resume summary unavailable: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
