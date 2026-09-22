"""Portable guards for retiring unapplied proposals without changing contracts."""
import copy
import unittest
import xml.etree.ElementTree as ET
from checkpoint_behavior import validate_alias_preservation, validate_unapplied_proposal


class UnappliedProposalTests(unittest.TestCase):
    def setUp(self):
        self.old = dict(Module='app.dll', Token='0x06000001', Identity='app, Version=1.0.0.0',
                        Mvid='physical-id', Sha256='physical-hash', Signature='System.Boolean T::a()',
                        OriginalName='a', NewName='CheckPassword')
        self.new = {**self.old, 'NewName': 'a'}
        self.after = ET.Element('Method', Token=self.old['Token'], Signature=self.old['Signature'], ExpectedName='a', NewName='a')
        self.proof = {k: self.old[k] for k in ('Module', 'Token', 'Signature')}
        self.proof.update(Kind='Method', ExpectedProposal='CheckPassword', RetainedName='a', Reason='Preserve the SDK-facing CLR name.')

    def test_unapplied_proposal_can_return_to_original_contract(self):
        validate_unapplied_proposal(self.old, self.new, None, self.after, self.proof)

    def test_proposal_name_cannot_substitute_for_actual_map_alias(self):
        key = ('app.dll', 'Method', '0x06000001')
        before = {key: ET.Element('Method', NewName='ToBytes2')}
        after = {key: ET.Element('Method', NewName='GetCipherBytes')}
        proof = {key: {'ExpectedName': 'ToBytes2', 'ExpectedReviewName': 'ToBytes', 'NewName': 'GetCipherBytes'}}
        validate_alias_preservation(before, after, proof)
        proof[key]['ExpectedName'] = 'ToBytes'
        with self.assertRaises(ValueError):
            validate_alias_preservation(before, after, proof)

    def test_existing_map_or_different_runtime_name_is_rejected(self):
        for before in (copy.deepcopy(self.after), ET.Element('Method', NewName='CheckPassword')):
            with self.assertRaises(ValueError):
                validate_unapplied_proposal(self.old, self.new, before, self.after, self.proof)
        for attribute in ('ExpectedName', 'NewName', 'Signature', 'Token'):
            after = copy.deepcopy(self.after)
            after.set(attribute, 'changed')
            with self.subTest(attribute=attribute), self.assertRaises(ValueError):
                validate_unapplied_proposal(self.old, self.new, None, after, self.proof)

    def test_stale_identity_proposal_or_missing_reason_is_rejected(self):
        for key in ('Module', 'Token', 'Identity', 'Mvid', 'Sha256', 'Signature', 'OriginalName', 'NewName'):
            incoming = {**self.new, key: 'different'}
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_unapplied_proposal(self.old, incoming, None, self.after, self.proof)
        for key in ('ExpectedProposal', 'RetainedName', 'Reason', 'Module', 'Token', 'Signature'):
            proof = {**self.proof, key: ''}
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_unapplied_proposal(self.old, self.new, None, self.after, proof)


if __name__ == '__main__':
    unittest.main()
