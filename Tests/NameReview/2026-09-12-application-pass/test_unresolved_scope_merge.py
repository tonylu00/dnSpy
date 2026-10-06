import copy
import unittest
from review_ledger import merge_unresolved_scopes, proposal_preimage


class UnresolvedScopeMergeTests(unittest.TestCase):
    def setUp(self):
        self.previous = dict(Module='a.dll', Token='0x06000001', Identity='a, Version=1.0.0.0',
                             Mvid='physical-mvid', Sha256='physical-hash', Type='T',
                             Signature='System.Void T::a(System.Int32)', OriginalName='a',
                             NewName='', Unresolved=True, UnresolvedReason='Owner behavior is incomplete',
                             Reason='Earlier unknown decision', NeedsReadableName=True,
                             ReviewDisposition='unresolved', Annotation={'kept': True},
                             ParameterNames=[dict(Sequence=1, OriginalName='p', HasMetadata=True, NewName='')],
                             LocalNames=[], UnresolvedScopeEvidence={
                                 'Locals': [dict(Index=0, ExpectedType='System.Int32', MissingEvidence='No data-flow review')]})
        self.review = copy.deepcopy(self.previous)
        self.review.update(Reason='Native IL establishes copied-byte count; owner remains unknown',
                           DefinitionOnlyUnresolved=True, MergeExistingUnresolvedScopes=True,
                           PreviousUnresolvedScopeDecision=proposal_preimage(self.previous),
                           LocalNames=[dict(Index=0, ExpectedType='System.Int32', NewName='copiedByteCount')],
                           UnresolvedScopeEvidence={'Parameters': [dict(Sequence=1, OriginalName='p',
                                                                        MissingEvidence='Mode meaning is still unknown')],
                                                    'Locals': []})
        self.checked = {('LocalNames', 0): dict(ExpectedType='System.Int32', NewName='copiedByteCount')}

    def test_native_body_scopes_retain_unknown_owner_and_prior_evidence(self):
        result = merge_unresolved_scopes(self.previous, self.review, '', self.checked)
        self.assertTrue(result['Unresolved'])
        self.assertTrue(result['DefinitionOnlyUnresolved'])
        self.assertEqual('', result['NewName'])
        self.assertEqual(self.previous['UnresolvedReason'], result['UnresolvedReason'])
        self.assertEqual(self.previous['Annotation'], result['Annotation'])
        self.assertEqual('copiedByteCount', result['LocalNames'][0]['NewName'])
        self.assertEqual([], result['UnresolvedScopeEvidence']['Locals'])
        self.assertEqual(proposal_preimage(self.previous), result['UnresolvedScopeMerges'][0]['PreviousDecision'])
        self.assertEqual([], self.previous['LocalNames'])
        self.assertFalse(self.previous.get('DefinitionOnlyUnresolved', False))

    def test_reject_definition_or_transition_changes(self):
        for key, value in [('Token', '0x04000001'), ('Mvid', 'foreign'), ('Sha256', 'foreign'),
                           ('Signature', 'other'), ('OriginalName', 'other'), ('NewName', 'Invented'),
                           ('Unresolved', False), ('DefinitionOnlyUnresolved', False),
                           ('MergeExistingUnresolvedScopes', False), ('Reason', ''), ('UnresolvedReason', ''),
                           ('PreviousUnresolvedScopeDecision', {})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                bad = copy.deepcopy(self.review); bad[key] = value
                merge_unresolved_scopes(self.previous, bad, '', self.checked)
        with self.assertRaises(ValueError):
            merge_unresolved_scopes(self.previous, self.review, 'ExistingAlias', self.checked)

    def test_reject_unchecked_stale_or_duplicate_scopes(self):
        for checked in [{}, {('LocalNames', 0): dict(ExpectedType='System.String', NewName='copiedByteCount')},
                        {('LocalNames', 0): dict(ExpectedType='System.Int32', NewName='different')}]:
            with self.subTest(checked=checked), self.assertRaises(ValueError):
                merge_unresolved_scopes(self.previous, self.review, '', checked)
        bad = copy.deepcopy(self.review); bad['LocalNames'].append(copy.deepcopy(bad['LocalNames'][0]))
        with self.assertRaises(ValueError): merge_unresolved_scopes(self.previous, bad, '', self.checked)

    def test_retained_aliases_require_native_identity_and_no_replacement(self):
        previous = copy.deepcopy(self.previous)
        previous['LocalNames'] = [dict(Index=1, ExpectedType='System.Int32', NewName='priorCount')]
        reviewed = copy.deepcopy(self.review)
        reviewed['PreviousUnresolvedScopeDecision'] = proposal_preimage(previous)
        with self.assertRaises(ValueError): merge_unresolved_scopes(previous, reviewed, '', self.checked)
        checked = dict(self.checked, **{})
        checked[('LocalNames', 1)] = dict(ExpectedType='System.Int32', NewName='priorCount')
        result = merge_unresolved_scopes(previous, reviewed, '', checked)
        self.assertEqual(['priorCount', 'copiedByteCount'], [x['NewName'] for x in result['LocalNames']])
        bad = copy.deepcopy(reviewed)
        bad['LocalNames'].append(dict(Index=1, ExpectedType='System.Int32', NewName='replacement'))
        with self.assertRaises(ValueError): merge_unresolved_scopes(previous, bad, '', checked)


if __name__ == '__main__': unittest.main()
