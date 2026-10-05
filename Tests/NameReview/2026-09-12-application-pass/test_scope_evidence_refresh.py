"""Lost uncertainty can be restored without changing a single naming decision."""
import copy
import unittest

from review_ledger import refresh_scope_evidence, validate_scope_evidence_only


class ScopeEvidenceRefreshTests(unittest.TestCase):
    def setUp(self):
        self.old = dict(Module='M.dll', Token='0x06000001', Identity='M, Version=1.0.0.0',
                        Mvid='physical', Sha256='hash', Type='T', Signature='void T::a(int)',
                        OriginalName='a', NewName='Process', Reason='Complete body',
                        Unresolved=False, UnresolvedReason='', ContractFamily='family',
                        ParameterNames=[dict(Sequence=1, OriginalName='a', NewName='count', HasMetadata=True)],
                        LocalNames=[dict(Index=0, ExpectedType='System.Int32', NewName='total'),
                                    dict(Index=1, ExpectedType='System.Int16', NewName='')],
                        Annotation={'retained': True})
        self.review = copy.deepcopy(self.old)
        self.review.update(NewName='', Reason='Original native slot 1 is never loaded or stored',
                           PreviousScopeEvidence=dict(Reason=self.old['Reason'], UnresolvedScopeEvidence={}),
                           UnresolvedScopeEvidence=dict(Locals=[dict(Index=1, ExpectedType='System.Int16',
                                                                   MissingEvidence='No IL use')]))
        for label in ('ParameterNames', 'LocalNames'):
            for entry in self.review[label]:
                entry['NewName'] = ''
        self.checked = {('ParameterNames', 1): dict(ExpectedName='a', NewName='count'),
                        ('LocalNames', 0): dict(ExpectedType='System.Int32', NewName='total')}

    def test_exact_refresh_keeps_scopes_contracts_and_history(self):
        before = copy.deepcopy(self.old)
        result = refresh_scope_evidence(self.old, self.review, self.checked)
        for key in self.old.keys() - {'Reason'}:
            self.assertEqual(result[key], self.old[key])
        self.assertEqual(result['UnresolvedScopeEvidence'], self.review['UnresolvedScopeEvidence'])
        self.assertIn(self.old['Reason'], result['Reason'])
        self.assertEqual(result['ScopeEvidenceReviews'][0]['PreviousUnresolvedScopeEvidence'], {})
        self.assertEqual(self.old, before)
        result['UnresolvedScopeEvidence']['Locals'][0]['MissingEvidence'] = 'mutated'
        self.assertEqual(self.review['UnresolvedScopeEvidence']['Locals'][0]['MissingEvidence'], 'No IL use')

    def test_stale_identity_decisions_preimage_and_checked_alias_rejected(self):
        for key, value in [('Module', 'CV/M.dll'), ('Mvid', 'twin'), ('Sha256', 'other'),
                           ('Signature', 'other'), ('NewName', 'Process2'), ('Unresolved', True),
                           ('UnresolvedReason', 'new'), ('ParameterNames', []), ('LocalNames', []),
                           ('PreviousScopeEvidence', {}), ('Reason', '')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                refresh_scope_evidence(self.old, dict(self.review, **{key: value}), self.checked)
        with self.assertRaises(ValueError):
            refresh_scope_evidence(self.old, self.review, {})
        checked = copy.deepcopy(self.checked)
        checked[('LocalNames', 0)]['ExpectedType'] = 'System.Byte'
        with self.assertRaises(ValueError):
            refresh_scope_evidence(self.old, self.review, checked)

    def test_missing_duplicate_aliased_and_malformed_positions_rejected(self):
        entry = self.review['UnresolvedScopeEvidence']['Locals'][0]
        for bad in [dict(entry, Index=9), dict(entry, Index=0, ExpectedType='System.Int32'),
                    dict(entry, Index=True), dict(entry, ExpectedType='System.Byte'),
                    dict(entry, MissingEvidence=' '), dict(entry, Extra=True)]:
            with self.subTest(entry=bad), self.assertRaises(ValueError):
                refresh_scope_evidence(self.old, dict(self.review, UnresolvedScopeEvidence={'Locals': [bad]}), self.checked)
        for evidence in [{'Locals': [entry, entry]}, {}, {'Fields': [entry]}, {'Locals': '1'}]:
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                refresh_scope_evidence(self.old, dict(self.review, UnresolvedScopeEvidence=evidence), self.checked)
        checked = dict(self.checked, **{})
        checked[('LocalNames', 1)] = dict(ExpectedType='System.Int16', NewName='mappedOnly')
        with self.assertRaises(ValueError):
            refresh_scope_evidence(self.old, self.review, checked)

    def test_parameter_preimage_and_alias_guard(self):
        old = copy.deepcopy(self.old)
        old['ParameterNames'].append(dict(Sequence=2, OriginalName='b', NewName='', HasMetadata=True))
        review = copy.deepcopy(self.review)
        review['ParameterNames'] = copy.deepcopy(old['ParameterNames'])
        for entry in review['ParameterNames']:
            entry['NewName'] = ''
        review['UnresolvedScopeEvidence'] = {'Parameters': [dict(Sequence=2, OriginalName='b', MissingEvidence='Unused formal')]}
        self.assertEqual(refresh_scope_evidence(old, review, self.checked)['UnresolvedScopeEvidence'], review['UnresolvedScopeEvidence'])
        review['UnresolvedScopeEvidence']['Parameters'][0]['OriginalName'] = 'stale'
        with self.assertRaises(ValueError):
            refresh_scope_evidence(old, review, self.checked)

    def test_repeat_and_overwrite_rejected(self):
        result = refresh_scope_evidence(self.old, self.review, self.checked)
        review = copy.deepcopy(result)
        review['NewName'] = ''
        for label in ('ParameterNames', 'LocalNames'):
            for entry in review[label]:
                entry['NewName'] = ''
        review['PreviousScopeEvidence'] = dict(Reason=result['Reason'], UnresolvedScopeEvidence=copy.deepcopy(result['UnresolvedScopeEvidence']))
        with self.assertRaisesRegex(ValueError, 'no missing annotations'):
            refresh_scope_evidence(result, review, self.checked)
        review['UnresolvedScopeEvidence']['Locals'][0]['MissingEvidence'] = 'rewritten'
        with self.assertRaisesRegex(ValueError, 'cannot overwrite'):
            refresh_scope_evidence(result, review, self.checked)

    def test_legacy_absent_false_flags_stay_absent(self):
        old = dict(self.old)
        del old['Unresolved']
        del old['UnresolvedReason']
        result = refresh_scope_evidence(old, self.review, self.checked)
        self.assertNotIn('Unresolved', result)
        self.assertNotIn('UnresolvedReason', result)

    def test_missing_unused_inventory_requires_exact_unaliased_evidence(self):
        old = copy.deepcopy(self.old)
        old['LocalNames'] = old['LocalNames'][:1]
        result = refresh_scope_evidence(old, self.review, self.checked)
        self.assertEqual(result['LocalNames'], self.old['LocalNames'])
        self.assertEqual(old['LocalNames'], self.old['LocalNames'][:1])
        for entry in [dict(Index=2, ExpectedType='System.Byte', NewName=''),
                      dict(Index=1, ExpectedType='System.Int16', NewName='invented')]:
            review = copy.deepcopy(self.review)
            review['LocalNames'].append(entry)
            with self.assertRaises(ValueError):
                refresh_scope_evidence(old, review, self.checked)

    def test_review_only_requires_unchanged_native_map_and_method_evidence(self):
        review = dict(Types=[], Fields=[], Methods=[self.review])
        validate_scope_evidence_only(review, [], 'same', 'same')
        for changes, before, after in [([{}], 'same', 'same'), ([], '', ''), ([], 'old', 'new')]:
            with self.assertRaises(ValueError):
                validate_scope_evidence_only(review, changes, before, after)
        for bad in [dict(review, Types=[{}]), dict(review, Fields=[{}]), dict(review, Methods=[]),
                    dict(review, Methods=[self.old])]:
            with self.assertRaises(ValueError):
                validate_scope_evidence_only(bad, [], 'same', 'same')


if __name__ == '__main__':
    unittest.main()
