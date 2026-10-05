"""Atomic correction audits reject incomplete families and unrelated changes."""
import copy
import unittest

from record_contract_alias_corrections import verify_contract_corrections


class ContractCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.context = dict(Format=1, Kind='SymbolReview', TargetRoot='physical-root',
                            ContractReferenceSha256='manifest-sha', Types=[], Fields=[])
        rows = [dict(Module='library.dll', Token=token, Type=owner,
                     Signature='System.UInt64 ' + owner + '::Next()', OriginalName='Next',
                     Identity='library, Version=1.0.0.0', Mvid='physical-mvid', Sha256='physical-sha',
                     ContractFamily='complete-family', MappingBlocker=None,
                     NewName='', Reason='native family', Unresolved=False,
                     ParameterNames=[], LocalNames=[])
                for token, owner in [('0x06000001', 'ISequence'), ('0x06000002', 'Sequence')]]
        self.families = dict(self.context, Methods=rows)
        self.review = copy.deepcopy(self.families)
        for row in self.review['Methods']:
            row.update(NewName='AllocateNextSequenceNumber', Reason='atomic increment and exhaustion rollback')
        self.prior = dict(Types=[], Fields=[], Methods=[])
        self.current = copy.deepcopy(self.review)
        self.before = {(r['Module'], 'Method', r['Token'], ''): 'LogSequenceNumberExhausted' for r in rows}
        self.after = {k: 'AllocateNextSequenceNumber' for k in self.before}
        self.changes = [dict(Module=r['Module'], Token=r['Token'], Kind='ContractMethod',
                             Before='LogSequenceNumberExhausted', Requested='AllocateNextSequenceNumber',
                             Applied='AllocateNextSequenceNumber') for r in rows]
        self.expected = [dict(Module=r['Module'], Token=r['Token'], PreviousLedgerAlias=None,
                              MappedAlias='LogSequenceNumberExhausted', NewName='AllocateNextSequenceNumber') for r in rows]

    def verify(self):
        verify_contract_corrections(self.before, self.after, self.prior, self.current,
                                    self.review, self.changes, self.expected, self.families)

    def test_complete_family_preserves_native_report(self):
        before = copy.deepcopy(self.changes)
        self.verify()
        self.assertEqual(before, self.changes)

    def test_partial_family_is_rejected(self):
        self.expected.pop()
        self.review['Methods'].pop()
        self.changes.pop()
        with self.assertRaisesRegex(ValueError, 'Partial'): self.verify()

    def test_same_names_in_another_physical_module_are_not_members(self):
        self.families['Methods'][0]['Module'] = 'compat/library.dll'
        with self.assertRaises(ValueError): self.verify()

    def test_family_or_physical_identity_mismatch_is_rejected(self):
        for key in ('ContractFamily', 'Sha256', 'Mvid', 'Signature', 'Identity'):
            with self.subTest(key=key):
                old = self.review['Methods'][0][key]
                self.review['Methods'][0][key] = 'another-identity'
                with self.assertRaises(ValueError): self.verify()
                self.review['Methods'][0][key] = old

    def test_manifest_and_root_mismatch_are_rejected(self):
        for key in ('ContractReferenceSha256', 'TargetRoot'):
            with self.subTest(key=key):
                old = self.families[key]
                self.families[key] = 'another-context'
                with self.assertRaises(ValueError): self.verify()
                self.families[key] = old

    def test_protected_member_is_rejected(self):
        for document in (self.families, self.review):
            document['Methods'][0]['MappingBlocker'] = 'protected-sdk'
            with self.assertRaises(ValueError): self.verify()
            document['Methods'][0]['MappingBlocker'] = None

    def test_wrong_native_kind_member_or_duplicate_is_rejected(self):
        for key, value in [('Kind', 'Method'), ('Token', '0x06000003')]:
            old = self.changes[0][key]
            self.changes[0][key] = value
            with self.assertRaises(ValueError): self.verify()
            self.changes[0][key] = old
        self.changes.append(copy.deepcopy(self.changes[0]))
        with self.assertRaises(ValueError): self.verify()

    def test_duplicate_inventory_member_is_rejected(self):
        self.families['Methods'].append(copy.deepcopy(self.families['Methods'][0]))
        with self.assertRaises(ValueError): self.verify()

    def test_split_aliases_and_native_suffix_are_rejected(self):
        self.review['Methods'][0]['NewName'] = 'AnotherRole'
        with self.assertRaises(ValueError): self.verify()
        self.review['Methods'][0]['NewName'] = 'AllocateNextSequenceNumber'
        self.changes[0]['Applied'] += '2'
        with self.assertRaises(ValueError): self.verify()

    def test_unrelated_scope_or_ledger_edits_are_rejected(self):
        self.after[('library.dll', 'Parameter', '0x06000001', '1')] = 'invented'
        with self.assertRaises(ValueError): self.verify()
        self.after.pop(('library.dll', 'Parameter', '0x06000001', '1'))
        self.current['Fields'].append(dict(Token='0x04000001', NewName='invented'))
        with self.assertRaises(ValueError): self.verify()

    def test_first_correction_cannot_invent_prior_ledger_or_scopes(self):
        self.prior['Methods'] = copy.deepcopy(self.review['Methods'])
        with self.assertRaises(ValueError): self.verify()
        self.prior['Methods'] = []
        for document in (self.current, self.review):
            document['Methods'][0]['LocalNames'] = [dict(Index=0, NewName='invented')]
        with self.assertRaises(ValueError): self.verify()


if __name__ == '__main__': unittest.main()
