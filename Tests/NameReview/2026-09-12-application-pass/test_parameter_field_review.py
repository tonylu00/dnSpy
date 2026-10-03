import copy
import unittest
from prepare_parameter_field_review import select_fields, validate_decisions, validate_graph_storage


class ParameterStorageDecisionTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(Module=module, Token='0x04000001', Identity='Library', Mvid='same',
            Sha256='same', Type='Owner', Signature='Int32 Owner::a', OriginalName='a',
            NewName='capacity', MappingBlocker=None) for module in ('Library.dll', 'CV/Library.dll', 'ThirdParty.dll')]
        self.proposals = dict(Fields=self.rows)
        self.modules = {'Library.dll', 'CV/Library.dll'}
        self.decision = dict(self.rows[0], ExpectedProposal='capacity', Disposition='rename',
            Reason='Constructor role and reader use agree')

    def test_exact_physical_scope_and_sdk_token(self):
        selected, excluded = select_fields(self.proposals, self.modules, {('CV/Library.dll', '0x04000001')}, {})
        self.assertEqual([self.rows[0]], selected)
        self.assertEqual(2, len(excluded))
        self.assertNotEqual(excluded[0]['Reason'], excluded[1]['Reason'])

    def test_existing_alias_or_duplicate_cannot_be_reproposed(self):
        with self.assertRaises(AssertionError):
            select_fields(self.proposals, self.modules, set(), {('Library.dll', '0x04000001'): 'accepted'})
        duplicate = dict(Fields=[self.rows[0], copy.deepcopy(self.rows[0])])
        with self.assertRaises(AssertionError): select_fields(duplicate, self.modules, set(), {})

    def test_every_field_requires_one_domain_decision(self):
        with self.assertRaises(AssertionError): validate_decisions(self.rows[:2], [self.decision])
        with self.assertRaises(AssertionError): validate_decisions(self.rows[:1], [self.decision, self.decision])
        self.assertEqual(1, len(validate_decisions(self.rows[:1], [self.decision])))

    def test_alias_or_physical_preimage_drift_rejected(self):
        for name in ('Module', 'Token', 'Identity', 'Type', 'Signature', 'Mvid', 'Sha256', 'OriginalName', 'ExpectedProposal'):
            changed = dict(self.decision, **{name: 'stale'})
            with self.subTest(name=name), self.assertRaises((AssertionError, ValueError)): validate_decisions(self.rows[:1], [changed])

    def test_preservation_and_uncertainty_cannot_smuggle_aliases(self):
        for disposition in ('preserve', 'unresolved'):
            with self.assertRaises(AssertionError): validate_decisions(self.rows[:1], [dict(self.decision, Disposition=disposition)])
            accepted = dict(self.decision, Disposition=disposition, NewName='')
            self.assertEqual(1, len(validate_decisions(self.rows[:1], [accepted])))
        with self.assertRaises(AssertionError): validate_decisions(self.rows[:1], [dict(self.decision, Reason='')])

    def test_resolved_foreign_writer_or_address_cannot_hide_in_local_proof(self):
        stores = [dict(ConstructorToken='0x06000001', StoreInstructions=['IL_000A: stfld Int32 Owner::a'])]
        write = dict(Source='m0:0x06000001', Reference=dict(Operation='stfld', Offset=10))
        validate_graph_storage(dict(Id='m0'), stores, [write])
        for changed in (dict(Source='m1:0x06000001', Reference=write['Reference']),
                        dict(Source='m0:0x06000002', Reference=write['Reference']),
                        dict(Source=write['Source'], Reference=dict(Operation='stfld', Offset=11)),
                        dict(Source=write['Source'], Reference=dict(Operation='ldflda', Offset=10)),
                        dict(Source=write['Source'], Reference=dict(Operation='stsfld', Offset=10))):
            with self.assertRaises(AssertionError): validate_graph_storage(dict(Id='m0'), stores, [write, changed])
        with self.assertRaises(AssertionError): validate_graph_storage(dict(Id='m0'), stores, [])


if __name__ == '__main__':
    unittest.main()
