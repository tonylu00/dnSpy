"""Atomic family replacements preserve scopes and fail on partial native proof."""
import copy
import unittest

from review_ledger import replace_method_alias
from record_method_alias_corrections import verify_corrections


class ContractAliasCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.previous = []
        self.reviewed = []
        self.changes = []
        self.final = []
        self.expected = []
        self.scopes = {('ParameterNames', 1): dict(ExpectedName='a', NewName='diagnosticSink')}
        for token, name in [('0x06000001', 'Base'), ('0x06000002', 'Derived')]:
            old = dict(Module='M.dll', Identity='M, Version=1.0.0.0', Mvid='mvid', Sha256='hash',
                       Type=name, Token=token, Signature='void ' + name + '::a(Sink)', OriginalName='a',
                       MappingBlocker='virtual requires review', ContractFamily=None,
                       NewName='', Reason='Scopes only', Unresolved=False, UnresolvedReason='',
                       ParameterNames=[dict(Sequence=1, OriginalName='a', HasMetadata=True, NewName='diagnosticSink')],
                       LocalNames=[dict(Index=0, ExpectedType='System.Int16', NewName='')],
                       UnresolvedScopeEvidence={'Locals': [dict(Index=0, ExpectedType='System.Int16', MissingEvidence='No IL use')]})
            reviewed = dict(copy.deepcopy(old), NewName='VerifyStatusBytes', MappingBlocker=None,
                            ContractFamily='family', Reason='Synchronous validation in the complete family',
                            PreviousLedgerAlias='', ExpectedMappedAlias='ValidateAsync', ParameterNames=[], LocalNames=[])
            change = dict(Module='M.dll', Token=token, Kind='ContractMethod', Before='ValidateAsync',
                          Requested='VerifyStatusBytes', Applied='VerifyStatusBytes')
            final = dict(Module='M.dll', Token=token, ContractFamily='family', NewName='VerifyStatusBytes',
                         Signature=old['Signature'], ExpectedName='a', Mvid='mvid', Sha256='hash')
            self.previous.append(old)
            self.reviewed.append(reviewed)
            self.changes.append(change)
            self.final.append(final)
            self.expected.append(dict(Module='M.dll', Token=token, ContractFamily='family',
                                      PreviousLedgerAlias='', MappedAlias='ValidateAsync', NewName='VerifyStatusBytes'))
        self.proof = dict(Id='family', ReviewedMembers=self.reviewed, Changes=self.changes, FinalRows=self.final)

    def apply(self, proof=None):
        return [replace_method_alias(old, row, 'ValidateAsync', change, self.scopes, checked_family=proof or self.proof)
                for old, row, change in zip(self.previous, self.reviewed, self.changes)]

    def test_complete_family_keeps_uncertainty_scopes_and_prior_contract_state(self):
        result = self.apply()
        for old, row in zip(self.previous, result):
            for key in ('ParameterNames', 'LocalNames', 'UnresolvedScopeEvidence'):
                self.assertEqual(old[key], row[key])
            self.assertEqual(row['ContractFamily'], 'family')
            self.assertIsNone(row['MappingBlocker'])
            self.assertEqual(row['LedgerAliasCorrections'][0]['PreviousLedgerAlias'], '')
            self.assertEqual(row['ContractFamilyReviews'][0]['PreviousMappingBlocker'], old['MappingBlocker'])
        doc = lambda rows: dict(Methods=rows, Types=[], Fields=[])
        before = {('M.dll', 'Method', r['Token'], ''): 'ValidateAsync' for r in self.previous}
        after = {key: 'VerifyStatusBytes' for key in before}
        verify_corrections(before, after, doc(self.previous), doc(result), doc(self.reviewed), self.changes,
                           self.expected, {'family': self.proof})
        with self.assertRaises(ValueError):
            verify_corrections(before, after, doc(self.previous), doc(result), doc(self.reviewed), self.changes, self.expected)

    def test_partial_duplicate_and_wrong_family_rejected(self):
        for key in ('ReviewedMembers', 'Changes', 'FinalRows'):
            for replacement in ([], self.proof[key][:1], self.proof[key] + self.proof[key][:1]):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    self.apply(dict(self.proof, **{key: replacement}))
        for proof in (dict(self.proof, Id='other'), {}):
            with self.assertRaises(ValueError):
                replace_method_alias(self.previous[0], self.reviewed[0], 'ValidateAsync', self.changes[0], self.scopes, checked_family=proof)

    def test_stale_native_final_identity_and_suffixes_rejected(self):
        for section, key, value in [('Changes', 'Kind', 'Method'), ('Changes', 'Before', None),
                                    ('Changes', 'Applied', 'VerifyStatusBytes2'), ('Changes', 'Action', 'RemoveAlias'),
                                    ('FinalRows', 'Mvid', 'twin'), ('FinalRows', 'Sha256', 'other'),
                                    ('FinalRows', 'Signature', 'other'), ('FinalRows', 'ExpectedName', 'b'),
                                    ('FinalRows', 'ContractFamily', 'other'), ('ReviewedMembers', 'MappingBlocker', 'SDK')]:
            proof = copy.deepcopy(self.proof)
            proof[section][1][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                self.apply(proof)
        with self.assertRaises(ValueError):
            replace_method_alias(self.previous[0], self.reviewed[0], 'WrongPriorAlias', self.changes[0], self.scopes, checked_family=self.proof)


if __name__ == '__main__':
    unittest.main()
