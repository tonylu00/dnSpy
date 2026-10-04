import copy
import unittest
from join_generated_source_observations import join_candidate, source_index, path_key


class SourceObservationTests(unittest.TestCase):
    def setUp(self):
        self.field = {'Module': 'a.dll', 'Kind': 'Fields', 'Token': '0x04000001', 'Signature': 'int Owner/State::a', 'OriginalName': 'a',
                      'Evidence': {'DeclaringType': {'Token': '0x02000003'}, 'StateMachineOwners': [{'Definition': {'Token': '0x06000002'}}]}}
        self.witness = {'Kind': 'AsyncMethod', 'OwnerToken': 0x06000002, 'ImplementationToken': 0x06000003, 'ImplementationTypeToken': 0x02000003}
        self.report = {'Definitions': [{'Token': 0x04000001, 'FullName': self.field['Signature'], 'OriginalName': 'a'}],
                       'Roots': [{'DeclarationTokens': [], 'ReferenceTokens': [], 'BodyWitnesses': [self.witness], 'FieldBindings': []}]}

    def observe(self, candidate=None, report=None, cross=None):
        return join_candidate(candidate or self.field, source_index(report or self.report), cross or {})

    def test_state_body_requires_matching_owner_and_type(self):
        self.assertIn('StateMachineBodyReconstructed', self.observe()['Facts'])
        for name in ('OwnerToken', 'ImplementationTypeToken'):
            report = copy.deepcopy(self.report); report['Roots'][0]['BodyWitnesses'][0][name] += 1
            self.assertEqual(self.observe(report=report)['Facts'], ['NoPositiveSourceObservation'])

    def test_retained_projection_and_reconstruction_overlap(self):
        report = copy.deepcopy(self.report); root = report['Roots'][0]
        root['DeclarationTokens'] = [0x04000001]; root['ReferenceTokens'] = [0x04000001]
        root['FieldBindings'] = [{'FieldToken': 0x04000001, 'OwnerToken': 0x06000002, 'SourceName': 'value'}]
        facts = self.observe(report=report, cross={0x04000001: 3})['Facts']
        self.assertEqual(set(facts), {'SourceDeclarationRetained', 'LocalSourceReferenceRetained', 'CrossModuleSourceReferenceRetained', 'HoistedFieldProjected', 'StateMachineBodyReconstructed'})

    def test_wrong_definition_is_rejected(self):
        for name in ('Token', 'Signature', 'OriginalName'):
            row = copy.deepcopy(self.field); row[name] = '0x04000002' if name == 'Token' else 'wrong'
            with self.assertRaisesRegex(ValueError, 'definition mismatch'):
                self.observe(candidate=row)

    def test_anonymous_body_and_owner_match_are_separate(self):
        row = {'Kind': 'Methods', 'Token': '0x06000004', 'Signature': 'void Owner::a()', 'OriginalName': 'a',
               'Evidence': {'DelegateOwners': [{'Definition': {'Token': '0x06000002'}}]}}
        report = {'Definitions': [{'Token': 0x06000004, 'FullName': row['Signature'], 'OriginalName': 'a'}],
                  'Roots': [{'DeclarationTokens': [], 'ReferenceTokens': [], 'FieldBindings': [],
                             'BodyWitnesses': [{'Kind': 'AnonymousMethod', 'OwnerToken': 0, 'ImplementationToken': 0x06000004, 'ImplementationTypeToken': 0x02000003}]}]}
        result = self.observe(row, report)
        self.assertEqual(result['Facts'], ['AnonymousBodyReconstructed'])
        self.assertEqual(result['MatchedDelegateOwners'], [])
        self.assertIn('No candidate retirement', result['Limits'])

    def test_empty_structural_evidence_has_no_invented_owner(self):
        row = copy.deepcopy(self.field); row['Evidence'] = None
        self.assertEqual(self.observe(row)['Facts'], ['NoPositiveSourceObservation'])

    def test_physical_twins_stay_distinct(self):
        self.assertNotEqual(path_key('left/shared.dll'), path_key('right/shared.dll'))

    def test_printed_uses_require_explicit_complete_writer_coverage(self):
        report = copy.deepcopy(self.report)
        report['Roots'][0]['PrintedReferenceTokens'] = [0x04000001]
        self.assertFalse(self.observe(report=report)['PrintedReferenceCoverage'])
        self.assertNotIn('LocalPrintedSourceReferenceRetained', self.observe(report=report)['Facts'])
        report['Roots'][0]['PrintedReferenceCoverage'] = True
        self.assertIn('LocalPrintedSourceReferenceRetained', self.observe(report=report)['Facts'])
        report['Roots'].append({'DeclarationTokens': [], 'ReferenceTokens': [], 'BodyWitnesses': [], 'FieldBindings': []})
        self.assertFalse(self.observe(report=report)['PrintedReferenceCoverage'])
        self.assertNotIn('LocalPrintedSourceReferenceRetained', self.observe(report=report)['Facts'])

    def test_annotations_do_not_invent_printed_uses(self):
        report = copy.deepcopy(self.report)
        report['Roots'][0].update(ReferenceTokens=[0x04000001], PrintedReferenceCoverage=True, PrintedReferenceTokens=[])
        result = self.observe(report=report)
        self.assertIn('LocalSourceReferenceRetained', result['Facts'])
        self.assertNotIn('LocalPrintedSourceReferenceRetained', result['Facts'])

    def test_cross_annotations_and_printed_uses_are_separate(self):
        index = source_index(self.report)
        annotation_only = join_candidate(self.field, index, {0x04000001: 3})
        self.assertIsNone(annotation_only['CrossModulePrintedUseRecords'])
        self.assertFalse(annotation_only['CrossModulePrintedReferenceCoverage'])
        self.assertNotIn('CrossModulePrintedSourceReferenceRetained', annotation_only['Facts'])
        printed = join_candidate(self.field, index, {0x04000001: 3}, {0x04000001: 1})
        self.assertTrue(printed['CrossModulePrintedReferenceCoverage'])
        self.assertEqual(printed['CrossModulePrintedUseRecords'], 1)
        self.assertIn('CrossModulePrintedSourceReferenceRetained', printed['Facts'])
        no_printed_use = join_candidate(self.field, index, {0x04000001: 3}, {})
        self.assertEqual(no_printed_use['CrossModulePrintedUseRecords'], 0)
        self.assertNotIn('CrossModulePrintedSourceReferenceRetained', no_printed_use['Facts'])


if __name__ == '__main__':
    unittest.main()
