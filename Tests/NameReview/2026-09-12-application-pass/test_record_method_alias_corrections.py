"""Administrative correction proofs must reject unreviewed native/ledger edits."""
import copy
import unittest

from record_method_alias_corrections import verify_corrections


class MethodCorrectionProofTests(unittest.TestCase):
    def setUp(self):
        self.key = ('library.dll', 'Method', '0x06000001', '')
        self.scope = ('library.dll', 'Parameter', '0x06000001', '1')
        self.before = {self.key: 'ToString2', self.scope: 'request',
                       ('library.dll', 'Method', '0x06000002', ''): 'ToString'}
        self.after = dict(self.before, **{})
        self.after[self.key] = 'GetConnectionDescription'
        row = dict(Module='library.dll', Token='0x06000001', Type='Connection', Signature='System.String Connection::method_11()',
                   Identity='library, Version=1.0.0.0', Mvid='verified-mvid', Sha256='verified-sha', OriginalName='method_11',
                   NewName='ToString', Reason='old evidence', Unresolved=False, ContractFamily=None,
                   ParameterNames=[dict(Sequence=1, NewName='request')], LocalNames=[])
        self.prior = dict(Methods=[row], Types=[], Fields=[])
        self.current = copy.deepcopy(self.prior)
        self.review = dict(Methods=[copy.deepcopy(row)], Types=[], Fields=[])
        self.review['Methods'][0].update(NewName='GetConnectionDescription', Reason='endpoint and channel formatting',
                                         PreviousLedgerAlias='ToString', ExpectedMappedAlias='ToString2')
        self.current['Methods'][0].update(NewName='GetConnectionDescription',
            Reason='old evidence\nReviewed method correction: endpoint and channel formatting',
            LedgerAliasCorrections=[dict(PreviousLedgerAlias='ToString', PreviousMappedAlias='ToString2',
                                        Alias='GetConnectionDescription', Evidence='endpoint and channel formatting')])
        self.changes = [dict(Module='library.dll', Token='0x06000001', Kind='Method', Before='ToString2',
                             Requested='GetConnectionDescription', Applied='GetConnectionDescription')]
        self.expected = [dict(Module='library.dll', Token='0x06000001', PreviousLedgerAlias='ToString',
                              MappedAlias='ToString2', NewName='GetConnectionDescription')]

    def verify(self):
        verify_corrections(self.before, self.after, self.prior, self.current, self.review, self.changes, self.expected)

    def test_historical_collision_correction_preserves_real_override_and_scopes(self):
        self.verify()

    def test_actual_override_or_unrelated_scope_change_is_rejected(self):
        for key in (self.scope, ('library.dll', 'Method', '0x06000002', '')):
            with self.subTest(key=key):
                original = self.after[key]
                self.after[key] = 'Changed'
                with self.assertRaises(ValueError): self.verify()
                self.after[key] = original

    def test_stale_map_or_ledger_preimage_is_rejected(self):
        for label in ('PreviousLedgerAlias', 'MappedAlias'):
            with self.subTest(label=label):
                original = self.expected[0][label]
                self.expected[0][label] = 'stale'
                with self.assertRaises(ValueError): self.verify()
                self.expected[0][label] = original

    def test_missing_historical_annotations_or_history_is_rejected(self):
        for key in ('PreviousLedgerAlias', 'ExpectedMappedAlias'):
            with self.subTest(key=key):
                original = self.review['Methods'][0].pop(key)
                with self.assertRaises(ValueError): self.verify()
                self.review['Methods'][0][key] = original
        self.current['Methods'][0]['LedgerAliasCorrections'] = []
        with self.assertRaises(ValueError): self.verify()

    def test_native_suffix_extra_edit_or_wrong_physical_identity_is_rejected(self):
        self.changes[0]['Applied'] += '2'
        with self.assertRaises(ValueError): self.verify()
        self.changes[0]['Applied'] = self.expected[0]['NewName']
        self.changes.append(copy.deepcopy(self.changes[0]))
        with self.assertRaises(ValueError): self.verify()
        self.changes.pop()
        self.review['Methods'][0]['Mvid'] = 'other-module'
        with self.assertRaises(ValueError): self.verify()

    def test_scope_inventory_annotation_or_old_evidence_loss_is_rejected(self):
        for key, value in [('LocalNames', [dict(Index=0, NewName='new')]),
                           ('ContractFamily', 'invented-family'), ('Reason', 'replacement only')]:
            with self.subTest(key=key):
                original = self.current['Methods'][0][key]
                self.current['Methods'][0][key] = value
                with self.assertRaises(ValueError): self.verify()
                self.current['Methods'][0][key] = original

    def test_unreviewed_ledger_decision_or_duplicate_correction_is_rejected(self):
        self.current['Fields'].append(dict(Token='0x04000001', NewName='invented'))
        with self.assertRaises(ValueError): self.verify()
        self.current['Fields'].clear()
        self.expected.append(copy.deepcopy(self.expected[0]))
        with self.assertRaises(ValueError): self.verify()


if __name__ == '__main__': unittest.main()
