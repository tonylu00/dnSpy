import copy
import unittest

from record_method_alias_withdrawals import verify_withdrawals
from review_ledger import remove_method_alias


class WithdrawalProofTests(unittest.TestCase):
    def setUp(self):
        self.definition = ('library.dll', 'Method', '0x06000001', '')
        self.scope = ('library.dll', 'Parameter', '0x06000001', '1')
        self.other = ('library.dll', 'Method', '0x06000002', '')
        self.before = {self.definition: 'UnsupportedAlias', self.other: 'ReadableHelper'}
        self.after = {self.scope: 'frame', self.other: 'ReadableHelper'}
        self.row = dict(Module='library.dll', Token='0x06000001', Type='Owner/c', Signature='System.Void Owner/c::c(Frame)',
                        Identity='library, Version=1.0.0.0', Mvid='physical-mvid', Sha256='physical-hash', OriginalName='c',
                        NewName='', Unresolved=True, DefinitionOnlyUnresolved=True, Reason='checked body casts',
                        UnresolvedReason='missing printed owner witness', RemoveExistingAlias=True, ExpectedAlias='UnsupportedAlias',
                        ParameterNames=[dict(Sequence=1, OriginalName='x', NewName='frame')], LocalNames=[])
        self.removal = dict(Module='library.dll', Token='0x06000001', Kind='Method', Before='UnsupportedAlias', Requested='', Applied='', Action='RemoveAlias')
        self.changes = [self.removal, dict(Module='library.dll', Token='0x06000001', Kind='Parameter', Before=None, Requested='frame', Applied='frame', ParameterSequence=1)]
        self.prior = dict(Methods=[], Types=[], Fields=[])
        self.current = copy.deepcopy(self.prior)
        self.current['Methods'] = [remove_method_alias(None, self.row, 'UnsupportedAlias', self.removal, '',
                                                     {('ParameterNames', 1): dict(ExpectedName='x', NewName='frame')})]
        self.review = dict(Methods=[self.row], Types=[], Fields=[])

    def verify(self):
        verify_withdrawals(self.before, self.after, self.prior, self.current, self.review, self.changes)

    def test_new_scope_and_explicit_uncertainty_are_recorded(self): self.verify()

    def test_unrelated_alias_or_scope_change_is_rejected(self):
        self.after[self.other] = 'Changed'
        with self.assertRaises(ValueError): self.verify()
        self.after[self.other] = 'ReadableHelper'
        self.after[self.scope] = 'Changed'
        with self.assertRaises(ValueError): self.verify()

    def test_stale_preimage_or_surviving_definition_is_rejected(self):
        self.before[self.definition] = 'Stale'
        with self.assertRaises(ValueError): self.verify()
        self.before[self.definition] = 'UnsupportedAlias'
        self.after[self.definition] = 'UnsupportedAlias'
        with self.assertRaises(ValueError): self.verify()

    def test_suffix_duplicate_or_noop_native_edit_is_rejected(self):
        self.changes[1]['Applied'] = 'frame2'
        with self.assertRaises(ValueError): self.verify()
        self.changes[1]['Applied'] = 'frame'
        self.changes.append(copy.deepcopy(self.changes[1]))
        with self.assertRaises(ValueError): self.verify()
        self.changes.pop()
        self.changes[1]['Before'] = 'frame'
        with self.assertRaises(ValueError): self.verify()

    def test_ledger_annotation_scope_and_evidence_loss_are_rejected(self):
        for key, value in [('UnresolvedReason', ''), ('DefinitionOnlyUnresolved', False), ('AliasWithdrawals', []), ('ParameterNames', [])]:
            with self.subTest(key=key):
                saved = self.current['Methods'][0][key]
                self.current['Methods'][0][key] = value
                with self.assertRaises(ValueError): self.verify()
                self.current['Methods'][0][key] = saved

    def test_unreviewed_decision_change_is_rejected(self):
        self.current['Fields'].append(dict(Module='library.dll', Token='0x04000001', NewName='Guessed'))
        with self.assertRaises(ValueError): self.verify()

    def test_missing_native_withdrawal_or_duplicate_review_is_rejected(self):
        self.changes.remove(self.removal)
        with self.assertRaises(ValueError): self.verify()
        self.changes.insert(0, self.removal)
        self.review['Methods'].append(copy.deepcopy(self.row))
        with self.assertRaises(ValueError): self.verify()

    def test_retained_scope_is_preserved_without_replayed_edit(self):
        self.before[self.scope] = 'frame'
        self.changes.pop()
        self.verify()


if __name__ == '__main__': unittest.main()
