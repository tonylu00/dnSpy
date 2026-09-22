"""Portable checks for explicit replacement review; never loads ETS inputs."""
import copy
import unittest
import xml.etree.ElementTree as ET
from behavior_review import BehaviorReview
from checkpoint_behavior import validate_alias_preservation


class AliasReplacementTests(unittest.TestCase):
    def setUp(self):
        self.key = ('compat/Component.dll', 'Method', '0x06000001')
        row = ET.fromstring('<Method NewName="&lt;MoveNext&gt;b__0">'
                            '<Parameter Sequence="1" ExpectedName="a" NewName="message"/>'
                            '<Local Index="0" ExpectedType="System.Int32" NewName="count"/>'
                            '</Method>')
        self.before = {self.key: row}
        self.after = {self.key: copy.deepcopy(row)}
        self.after[self.key].set('NewName', 'SelectMessageAddress')
        self.replacement = {self.key: {'ExpectedName': '<MoveNext>b__0', 'NewName': 'SelectMessageAddress'}}

    def test_exact_replacement_retains_scopes(self):
        validate_alias_preservation(self.before, self.after, self.replacement)

    def test_requires_review(self):
        with self.assertRaises(ValueError):
            validate_alias_preservation(self.before, self.after, {})

    def test_rejects_stale_old_or_new_name(self):
        for field in ('ExpectedName', 'NewName'):
            with self.subTest(field=field):
                review = copy.deepcopy(self.replacement)
                review[self.key][field] = 'DifferentName'
                with self.assertRaises(ValueError):
                    validate_alias_preservation(self.before, self.after, review)

    def test_does_not_authorize_other_physical_copy(self):
        other = ('Component.dll', self.key[1], self.key[2])
        with self.assertRaises(ValueError):
            validate_alias_preservation(self.before, self.after, {other: self.replacement[self.key]})

    def test_cannot_remove_or_change_scoped_decisions(self):
        for tag in ('Parameter', 'Local'):
            with self.subTest(tag=tag):
                after = copy.deepcopy(self.after)
                after[self.key].find(tag).set('NewName', 'Changed')
                with self.assertRaises(ValueError):
                    validate_alias_preservation(self.before, after, self.replacement)
        with self.assertRaises(ValueError):
            validate_alias_preservation(self.before, {}, self.replacement)

    def test_no_unused_replacement_approvals(self):
        with self.assertRaises(ValueError):
            validate_alias_preservation(self.before, self.before, self.replacement)

    def test_staging_requires_exact_expected_alias(self):
        review = BehaviorReview.__new__(BehaviorReview)
        review.module_id, review.relative = 'm0001', self.key[0]
        review.entries = {'Methods': {self.key[2]: {
            'ParameterNames': [{'Sequence': 1, 'OriginalName': 'a', 'HasMetadata': True}],
            'LocalNames': [{'Index': 0, 'ExpectedType': 'System.Int32'}], 'MappingBlocker': None}}}
        review.aliases = {(review.relative, self.key[2]): self.before[self.key]}
        review.selected, review.decisions, review.pending = set(), [], []
        review.delta = {'Methods': []}
        review.source = lambda token: [{'Id': f'm0001:0x{token:08X}'}]
        for expected in (None, 'stale'):
            review.selected.clear()
            with self.assertRaises(ValueError):
                review.add('Methods', 0x06000001, 'SelectMessageAddress', 'Returns address.', replace_alias=expected)
        review.selected.clear()
        review.add('Methods', 0x06000001, 'SelectMessageAddress', 'Returns address.', replace_alias='<MoveNext>b__0')
        self.assertEqual(review.decisions[0]['Replacement']['ExpectedName'], '<MoveNext>b__0')
        self.assertEqual(review.delta['Methods'][0]['ParameterNames'][0]['NewName'], 'message')
        self.assertEqual(review.delta['Methods'][0]['LocalNames'][0]['NewName'], 'count')


if __name__ == '__main__':
    unittest.main()
