import copy
import unittest
from review_ledger import merge_scopes, replace_alias, validate_review_only


class LedgerScopeMergeTests(unittest.TestCase):
    def setUp(self):
        self.old = dict(Module='a.dll', Token='0x06000001', Identity='a, Version=1.0.0.0',
                        Mvid='physical-mvid', Sha256='physical-hash', Type='T',
                        Signature='System.Void T::a(System.Int32,System.Int32)', OriginalName='a',
                        NewName='HistoricalAlias', Reason='Earlier behavior evidence', Unresolved=False,
                        ParameterNames=[dict(Sequence=1, OriginalName='a', HasMetadata=True, NewName='count'),
                                        dict(Sequence=2, OriginalName='b', HasMetadata=True, NewName='')],
                        LocalNames=[dict(Index=0, ExpectedType='System.Int32', NewName='total')])
        self.review = copy.deepcopy(self.old)
        self.review.update(NewName='', Reason='Second parameter is the upper bound')
        self.review['ParameterNames'][0]['NewName'] = ''
        self.review['ParameterNames'][1]['NewName'] = 'limit'
        self.review['LocalNames'][0]['NewName'] = ''

    def test_review_only_guard(self):
        row = dict(ReviewDisposition='preserve', Reason='Established schema acronym', NewName='', ParameterNames=[], LocalNames=[])
        review = dict(Types=[row], Fields=[], Methods=[])
        validate_review_only(review, [], 'same-sha', 'same-sha')
        for changes, checked in (([dict(Requested='Alias')], 'same-sha'), ([], 'changed-sha')):
            with self.assertRaises(ValueError): validate_review_only(review, changes, 'same-sha', checked)
        row['LocalNames'] = [dict(NewName='hiddenAlias')]
        with self.assertRaises(ValueError): validate_review_only(review, [], 'same-sha', 'same-sha')
        row['LocalNames'] = []
        row['ReviewDisposition'] = 'rename'
        with self.assertRaises(ValueError): validate_review_only(review, [], 'same-sha', 'same-sha')
        with self.assertRaises(ValueError): validate_review_only(dict(Types=[], Fields=[], Methods=[]), [], 'same-sha', 'same-sha')

    def test_keeps_prior_scopes_and_uses_current_map_alias(self):
        merged = merge_scopes(self.old, self.review, 'CurrentAcceptedAlias')
        self.assertEqual('CurrentAcceptedAlias', merged['NewName'])
        self.assertEqual(['count', 'limit'], [p['NewName'] for p in merged['ParameterNames']])
        self.assertEqual('total', merged['LocalNames'][0]['NewName'])
        self.assertIn('Earlier behavior evidence', merged['Reason'])
        self.assertEqual('', self.old['ParameterNames'][1]['NewName'])

    def test_rejects_stale_identity(self):
        self.review['Mvid'] = 'other-physical-module'
        with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias')

    def test_rejects_overwrite(self):
        self.review['ParameterNames'][0]['NewName'] = 'invented'
        with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias')

    def test_rejects_missing_slot_and_definition_rename(self):
        self.review['ParameterNames'][1]['Sequence'] = 3
        with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias')
        self.review = copy.deepcopy(self.old)
        self.review['NewName'] = 'OtherDefinitionAlias'
        with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias')

    def test_rejects_changed_local_signature(self):
        self.review['LocalNames'][0].update(ExpectedType='System.String', NewName='text')
        with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias')

    def test_imports_missing_legacy_locals_only_from_checked_map(self):
        self.old['LocalNames'] = []
        self.review['LocalNames'][0]['NewName'] = 'total'
        checked = {('LocalNames', 0): dict(Index='0', ExpectedType='System.Int32', NewName='total')}
        merged = merge_scopes(self.old, self.review, 'CurrentAcceptedAlias', checked)
        self.assertEqual('total', merged['LocalNames'][0]['NewName'])
        checked[('LocalNames', 0)]['ExpectedType'] = 'System.String'
        with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias', checked)

    def test_alias_correction_requires_exact_native_change(self):
        self.review['NewName'] = 'RefinedBehaviorName'
        change = dict(Before='HistoricalAlias', Requested='RefinedBehaviorName', Applied='RefinedBehaviorName')
        merged = replace_alias(self.old, self.review, 'HistoricalAlias', change)
        self.assertEqual('RefinedBehaviorName', merged['NewName'])
        change['Applied'] = 'RefinedBehaviorName2'
        with self.assertRaises(ValueError): replace_alias(self.old, self.review, 'HistoricalAlias', change)
        with self.assertRaises(ValueError): replace_alias(self.old, self.review, 'OtherMapAlias', change)

    def test_scope_correction_requires_exact_native_before_and_after(self):
        self.review['ParameterNames'][0]['NewName'] = 'textParameterRefId'
        replacements = {('ParameterNames', 1): dict(Before='count', Requested='textParameterRefId', Applied='textParameterRefId')}
        merged = merge_scopes(self.old, self.review, 'CurrentAcceptedAlias', replacements=replacements)
        self.assertEqual('textParameterRefId', merged['ParameterNames'][0]['NewName'])
        replacements[('ParameterNames', 1)]['Before'] = 'otherPreviousAlias'
        with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias', replacements=replacements)


if __name__ == '__main__': unittest.main()
