import copy
import unittest
import xml.etree.ElementTree as ET
from prepare_forwarded_parameter_review import validate_property_anchor, validate_domain_decision


class PropertyParameterEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.native = dict(Call=dict(RoleSource='existing-property-name'), Property=dict(
            PropertyToken='0x17000001', PropertySignature='Byte Frame::SixBitData()',
            PropertyName='SixBitData', ProposedName='sixBitData'))
        self.callee = dict(AccessorOwners=[dict(OwnerKind='Property', AccessorRole='set',
            OwnerToken='0x17000001', OwnerSignature='Byte Frame::SixBitData()', OwnerName='SixBitData')],
            Parameters=[dict(Sequence=None), dict(Sequence=1)])
        self.row = dict(Module='Library.dll', Token='0x06000001', Identity='Library', Mvid='same',
            Sha256='same', Type='Frame', Signature='Void Frame::a(Byte)', OriginalName='a')
        self.parameter = dict(OriginalName='byte_1', NewName='sixBitData')
        self.decision = dict(self.row, Sequence=1, ExpectedParameterName='byte_1', ExpectedProposal='sixBitData',
            Disposition='accept', Reason='Channel validation and checked setter alias establish caller role.',
            AcceptedName='channel', ExpectedCallerAlias='set_Channel')
        self.mapping = ET.Element('Method', ExpectedName='a', Signature=self.row['Signature'], NewName='set_Channel')

    def test_exact_property_owner_and_single_setter_input(self):
        validate_property_anchor(self.native, self.callee, 'sixBitData')
        for name in ('OwnerKind', 'AccessorRole', 'OwnerToken', 'OwnerSignature', 'OwnerName'):
            changed = copy.deepcopy(self.callee)
            changed['AccessorOwners'][0][name] = 'stale'
            with self.subTest(name=name), self.assertRaises(AssertionError):
                validate_property_anchor(self.native, changed, 'sixBitData')
        for owners in ([], self.callee['AccessorOwners'] * 2):
            with self.assertRaises(AssertionError): validate_property_anchor(self.native, dict(self.callee, AccessorOwners=owners), 'sixBitData')
        with self.assertRaises(AssertionError):
            validate_property_anchor(self.native, dict(self.callee, Parameters=[dict(Sequence=1), dict(Sequence=2)]), 'sixBitData')

    def test_property_preimages_and_role_route_cannot_drift(self):
        for name in ('PropertyToken', 'PropertySignature', 'PropertyName', 'ProposedName'):
            changed = copy.deepcopy(self.native)
            changed['Property'][name] = 'stale'
            with self.subTest(name=name), self.assertRaises(AssertionError): validate_property_anchor(changed, self.callee, 'sixBitData')
        with self.assertRaises(AssertionError):
            validate_property_anchor(dict(self.native, Call=dict(RoleSource='method-prefix')), self.callee, 'sixBitData')

    def test_domain_override_requires_reviewed_physical_preimages(self):
        validate_domain_decision(self.decision, self.row, self.parameter, self.mapping, True)
        for name in ('Module', 'Token', 'Identity', 'Type', 'Signature', 'Mvid', 'Sha256', 'OriginalName',
                     'ExpectedParameterName', 'ExpectedProposal', 'ExpectedCallerAlias'):
            with self.subTest(name=name), self.assertRaises((AssertionError, ValueError)):
                validate_domain_decision(dict(self.decision, **{name: 'stale'}), self.row, self.parameter, self.mapping, True)
        with self.assertRaises(AssertionError):
            validate_domain_decision(self.decision, self.row, self.parameter, None, True)

    def test_preserve_defer_and_other_routes_cannot_smuggle_override(self):
        for disposition in ('preserve', 'defer'):
            with self.assertRaises(AssertionError):
                validate_domain_decision(dict(self.decision, Disposition=disposition), self.row, self.parameter, self.mapping, True)
        with self.assertRaises(AssertionError): validate_domain_decision(self.decision, self.row, self.parameter, self.mapping, False)
        for changed in (dict(Reason=''), dict(AcceptedName=''), dict(AcceptedName='invented role')):
            with self.assertRaises(AssertionError): validate_domain_decision(dict(self.decision, **changed), self.row, self.parameter, self.mapping, True)


if __name__ == '__main__':
    unittest.main()
