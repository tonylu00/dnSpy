import copy
import unittest
from checkpoint_scope_evidence_completion import merge_scopes, reconcile_scope_merge, original_merge
from test_review_ledger import LedgerScopeMergeTests


class ScopeEvidenceCompletionTests(unittest.TestCase):
    def fixture(self):
        f = LedgerScopeMergeTests(); f.setUp()
        old, review = copy.deepcopy(f.old), copy.deepcopy(f.review)
        unknown = dict(Sequence=2, OriginalName='b', MissingEvidence='No producer established')
        old['UnresolvedScopeEvidence'] = {'Parameters': [unknown]}
        review.pop('UnresolvedScopeEvidence', None)
        checked = {('ParameterNames', 2): dict(ExpectedName='b', NewName='limit')}
        return old, review, checked

    def test_last_unknown_is_retired_and_history_preserved(self):
        old, review, checked = self.fixture(); before = copy.deepcopy((old, review))
        result = merge_scopes(old, review, old['NewName'], checked)
        self.assertEqual([], result['UnresolvedScopeEvidence']['Parameters'])
        self.assertEqual(old['UnresolvedScopeEvidence'], result['ScopeEvidenceReviews'][-1]['PreviousUnresolvedScopeEvidence'])
        self.assertEqual(before, (old, review))

    def test_unreviewed_unknowns_are_kept(self):
        old, review, checked = self.fixture()
        unknown = dict(Index=9, ExpectedType='System.Int16', MissingEvidence='Residual live range')
        old['UnresolvedScopeEvidence']['Locals'] = [unknown]
        result = merge_scopes(old, review, old['NewName'], checked)
        self.assertEqual([unknown], result['UnresolvedScopeEvidence']['Locals'])

    def test_native_scope_identity_and_review_identity_are_required(self):
        old, review, checked = self.fixture()
        for bad in ({}, {('ParameterNames', 2): dict(ExpectedName='wrong', NewName='limit')},
                    {('ParameterNames', 2): dict(ExpectedName='b', NewName='limit2')}):
            with self.assertRaises(ValueError): merge_scopes(old, review, old['NewName'], bad)
        for key, value in [('Mvid', 'other'), ('Sha256', 'stale'), ('Signature', 'other'), ('Reason', '')]:
            with self.assertRaises(ValueError):
                merge_scopes(old, dict(review, **{key: value}), old['NewName'], checked)
        bad = copy.deepcopy(review); bad['ParameterNames'].append(copy.deepcopy(bad['ParameterNames'][0]))
        with self.assertRaises(ValueError): merge_scopes(old, bad, old['NewName'], checked)

    def test_repair_requires_exact_historical_result(self):
        old, review, checked = self.fixture()
        recorded = original_merge(old, review, old['NewName'], checked)
        fixed = reconcile_scope_merge(old, review, recorded, old['NewName'], checked)
        self.assertEqual([], fixed['UnresolvedScopeEvidence']['Parameters'])
        bad = dict(recorded, Annotation='Unrelated edit')
        with self.assertRaises(ValueError):
            reconcile_scope_merge(old, review, bad, old['NewName'], checked)
        with self.assertRaises(ValueError):
            reconcile_scope_merge(old, review, fixed, old['NewName'], checked)

    def test_explicit_unknown_evidence_keeps_existing_path(self):
        old, review, checked = self.fixture(); review['UnresolvedScopeEvidence'] = {}
        self.assertEqual(original_merge(old, review, old['NewName'], checked),
                         merge_scopes(old, review, old['NewName'], checked))


if __name__ == '__main__':
    unittest.main()
