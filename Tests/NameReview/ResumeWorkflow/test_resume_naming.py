import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import resume_naming as r


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return {"Path": str(path), "Sha256": r.file_hash(path)}

    def fixture(self, name, tokens=("0x06000001",), extra_modules=(), baseline="B"):
        module = dict(Path="a.dll", Sha256="A", Mvid="M", Identity="Same, Version=1", SourceBaselineMapSha256=baseline)
        clusters = [dict(Module="a.dll", Owner="root:0x02000001", SemanticDefinitions=list(tokens))]
        map_pin = self.save(name + "-map.json", {})
        ledger = self.save(name + "-ledger.json", {})
        manifest = dict(Inputs=dict(map=map_pin, ledger=ledger), Modules=[module, *extra_modules],
                        OwnerClusters=self.save(name + "-owners.json", clusters),
                        Progress={"RemainingActionableSemanticDefinitions": len(tokens)})
        pin = self.save(name + ".json", manifest)
        state = dict(Pass=dict(DnspyRepo="repo", CheckpointDir="checks", ToolCli="dotnet tool"),
                     Maps={"63": dict(map_pin, AppliedToSource=False)},
                     Naming=dict(Dispositions=pin, Progress=manifest["Progress"],
                                 NextItems=[dict(Task="finish prepared batch", Detail="x" * 10000)]))
        state_pin = self.save(name + "-state.json", state)
        return pin, state_pin, manifest, state

    def test_fixed_cohort_separates_progress_from_new_work(self):
        old, *_ = self.fixture("old", ("0x06000001", "0x06000002"))
        new, *_ = self.fixture("new", ("0x06000002", "0x06000003", "0x06000004"))
        c = r.comparison(old["Path"], new["Path"])["Categories"]["semantic"]
        self.assertEqual((c["NetChange"], c["OriginalCohortNoLongerQueued"], c["AddedOrReopenedQueueEntries"]), (1, 1, 2))

    def test_physical_twins_are_distinct_and_owners_do_not_duplicate_definitions(self):
        _, _, manifest, _ = self.fixture("twins")
        a = manifest["Modules"][0]
        b = dict(a, Path="CV/a.dll")
        clusters = [dict(Module=p, Owner=owner, SemanticDefinitions=["0x06000001"])
                    for p, owner in [("a.dll", "root:1"), ("a.dll", "root:2"), ("CV/a.dll", "root:1")]]
        self.assertEqual(len(r.queues(clusters, {r.physical(m["Path"]): m for m in (a, b)})["semantic"]), 2)

    def test_changed_baseline_suppresses_cohort_claims(self):
        old, *_ = self.fixture("old")
        new, *_ = self.fixture("new", baseline="different")
        out = r.comparison(old["Path"], new["Path"])
        self.assertFalse(out["Comparable"])
        self.assertNotIn("OriginalCohortNoLongerQueued", out["Categories"]["semantic"])

    def test_changed_physical_hash_suppresses_cohort_claims(self):
        old, *_ = self.fixture("old")
        new, _, manifest, _ = self.fixture("new")
        manifest["Modules"][0]["Sha256"] = "changed"
        self.save("new.json", manifest)
        self.assertFalse(r.comparison(old["Path"], new["Path"])["Comparable"])

    def test_tampered_owner_queue_is_rejected(self):
        pin, _, manifest, _ = self.fixture("bad")
        Path(manifest["OwnerClusters"]["Path"]).write_text("[]")
        with self.assertRaisesRegex(ValueError, "Changed pinned file"):
            r.load_view(pin["Path"])

    def test_tampered_manifest_is_rejected(self):
        pin, state, _, _ = self.fixture("bad")
        Path(pin["Path"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "Changed pinned file"):
            r.brief(state["Path"])

    def test_brief_is_bounded_and_uses_correct_nested_next_item(self):
        _, state, _, _ = self.fixture("good")
        out = r.brief(state["Path"], "semantic")
        self.assertEqual(out["Publication"], "bindings-consistent")
        self.assertEqual(out["NextItem"]["Task"], "finish prepared batch")
        self.assertLess(len(json.dumps(out)), 6000)
        self.assertEqual(len(out["OwnerPreview"]), 1)

    def test_partial_publication_does_not_select_from_old_manifest(self):
        _, pin, _, state = self.fixture("partial")
        state["Maps"]["63"] = self.save("next-map.json", {"next": True})
        pin = self.save("partial-state.json", state)
        out = r.brief(pin["Path"])
        self.assertEqual(out["Publication"], "incomplete-or-stale")
        self.assertEqual(out["OwnerPreview"], [])

    def test_mutating_ledger_is_detected(self):
        _, state, manifest, _ = self.fixture("ledger")
        Path(manifest["Inputs"]["ledger"]["Path"]).write_text("[]")
        self.assertEqual(r.brief(state["Path"])["Publication"], "incomplete-or-stale")

    def test_source_projections_keep_distinct_roles(self):
        _, _, manifest, _ = self.fixture("projected")
        values = [dict(Token="0x04000001", OwnerToken=0x06000001, RootTypeToken=0x02000001,
                       BindingKind="Variable", SourceName=name) for name in ("first", "second")]
        clusters = [dict(Module="a.dll", Owner="owner:1", ProjectedValues=values * 2)]
        self.assertEqual(len(r.queues(clusters, {"a.dll": manifest["Modules"][0]})["projected-values"]), 2)

    def test_unknown_physical_owner_is_rejected(self):
        pin, _, manifest, _ = self.fixture("unknown")
        manifest["OwnerClusters"] = self.save("unknown-owners2.json", [dict(Module="unknown.dll")])
        pin = self.save("unknown.json", manifest)
        with self.assertRaisesRegex(ValueError, "outside physical scope"):
            r.load_view(pin["Path"])

    def test_legacy_projection_does_not_create_false_cohort_changes(self):
        old, _, manifest, _ = self.fixture("legacy")
        manifest["OwnerClusters"] = self.save("legacy-owners2.json", [dict(Module="a.dll", Owner="owner:1",
            ProjectedValues=[dict(Token="0x04000001", OwnerToken=0x06000001, SourceName="value")])])
        old = self.save("legacy.json", manifest)
        new, *_ = self.fixture("new")
        out = r.comparison(old["Path"], new["Path"])
        self.assertFalse(out["Categories"]["projected-values"]["Comparable"])
        self.assertNotIn("OriginalCohortNoLongerQueued", out["Categories"]["projected-values"])
        self.assertTrue(out["Categories"]["semantic"]["Comparable"])

    def test_same_field_in_different_source_roots_remains_distinct(self):
        _, _, manifest, _ = self.fixture("roots")
        values = [dict(Token="0x04000001", OwnerToken=0x06000001, RootTypeToken=root,
                       BindingKind="Variable", SourceName="value") for root in (0x02000001, 0x02000002)]
        clusters = [dict(Module="a.dll", Owner="owner:1", ProjectedValues=values)]
        self.assertEqual(len(r.queues(clusters, {"a.dll": manifest["Modules"][0]})["projected-values"]), 2)

    def continuation(self):
        _, state_pin, _, state = self.fixture("continuation")
        cursor = dict(Map=state["Maps"]["63"], Disposition=state["Naming"]["Dispositions"],
                      BroaderReadabilityGoalClosed=False, CompletedStage=True,
                      NextItems=state["Naming"]["NextItems"], NextCommand="python next.py",
                      FixedCohorts={"PrivateMetadata": self.save("private-cohort.json", [1, 2, 3])},
                      Counters=dict(PrivateOriginal=3, PrivateOriginalResolved=1),
                      Remaining=dict(PrivateOriginalFindings=2, PrivatePriorDiscovery=1,
                                     Ets64TypeFieldParameterLocalTransferPending=True),
                      StageProgress=dict(LastCompleted="one block", CurrentBlockFindings=2),
                      Running=[], Completed={"HistoricalOutput": "history" * 20000})
        state["Naming"]["BlockCursor"] = self.save("cursor.json", cursor)["Path"]
        self.save("continuation-state.json", state)
        return state_pin["Path"], state, cursor

    def test_stage_complete_does_not_authorize_goal_completion_or_dump_history(self):
        path, _, _ = self.continuation()
        out = r.brief(path)
        self.assertTrue(out["Goal"]["StageComplete"])
        self.assertFalse(out["Goal"]["RecordedClosed"])
        self.assertFalse(out["Goal"]["CompletionAuthorizedByBrief"])
        self.assertEqual(out["OverallProgress"]["PrivateMetadata"]["Resolved"], 1)
        self.assertEqual(out["OwnerPreview"], [])
        self.assertNotIn("HistoricalOutput", json.dumps(out))
        self.assertLess(len(json.dumps(out)), 10000)
        self.assertEqual(out["CurrentWork"]["NextCommand"], "python next.py")

    def test_running_work_is_visible_and_does_not_select_another_owner(self):
        path, _, cursor = self.continuation()
        cursor["Running"] = [dict(Kind="build", ExecSessionId=123)]
        self.save("cursor.json", cursor)
        out = r.brief(path)
        self.assertEqual(out["RunningCount"], 1)
        self.assertIn("do not launch a duplicate", out["NextAction"])
        self.assertEqual(out["OwnerPreview"], [])

    def test_cursor_publication_mismatch_suppresses_next_command(self):
        path, _, cursor = self.continuation()
        cursor["Disposition"]["Sha256"] = "different"
        self.save("cursor.json", cursor)
        out = r.brief(path)
        self.assertEqual(out["Publication"], "incomplete-or-stale")
        self.assertIsNone(out["CurrentWork"]["NextCommand"])
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            r.snapshot(out)

    def test_fixed_progress_delta_excludes_prior_discovery(self):
        path, _, cursor = self.continuation()
        baseline = self.save("baseline.json", r.snapshot(r.brief(path)))
        cursor["Counters"]["PrivateOriginalResolved"] = 2
        cursor["Remaining"]["PrivateOriginalFindings"] = 1
        cursor["Remaining"]["PrivatePriorDiscovery"] = 100
        self.save("cursor.json", cursor)
        delta = r.progress_since(r.brief(path), baseline["Path"])
        self.assertEqual(delta["FixedCohorts"]["PrivateMetadata"]["CompletedDelta"], 1)

    def test_changed_cohort_does_not_claim_progress(self):
        path, _, cursor = self.continuation()
        baseline = self.save("baseline.json", r.snapshot(r.brief(path)))
        cursor["FixedCohorts"]["PrivateMetadata"] = self.save("new-cohort.json", [4, 5, 6])
        self.save("cursor.json", cursor)
        row = r.progress_since(r.brief(path), baseline["Path"])["FixedCohorts"]["PrivateMetadata"]
        self.assertFalse(row["Comparable"])
        self.assertNotIn("CompletedDelta", row)

    def test_inconsistent_totals_do_not_claim_completion(self):
        path, _, cursor = self.continuation()
        cursor["Counters"]["PrivateOriginalResolved"] = 3
        self.save("cursor.json", cursor)
        self.assertEqual(r.brief(path)["Publication"], "incomplete-or-stale")

    def test_changed_cursor_during_read_is_rejected(self):
        path, _, cursor = self.continuation()
        original = r.cursor_view
        def change_after_read(state, issues):
            result = original(state, issues)
            self.save("cursor.json", dict(cursor, UpdatedUtc="changed"))
            return result
        with patch.object(r, "cursor_view", side_effect=change_after_read):
            with self.assertRaisesRegex(ValueError, "changed during read"):
                r.brief(path)

    def test_section_refuses_large_history_instead_of_truncating(self):
        path, _, _ = self.continuation()
        with self.assertRaisesRegex(ValueError, "exceeds output limit"):
            r.section(path, "Completed")
        self.assertEqual(r.section(path, "Counters.PrivateOriginal")["Value"], 3)


if __name__ == "__main__":
    unittest.main()
