import copy
import unittest
from prepare_application_property_review import select_accessors


class PropertyContractSelectionTests(unittest.TestCase):
    def setUp(self):
        self.family = dict(Id='family', Blockers=[], Members=[
            dict(Module='a.dll', Token='get', DerivedName='get_Value', MappedName=None),
            dict(Module='CV/a.dll', Token='override', DerivedName='get_Value', MappedName=None)])
        self.review = dict(Methods=[dict(Module=m['Module'], Token=m['Token'], ContractFamily='family')
                                   for m in self.family['Members']] + [dict(Module='b.dll', Token='solo', ContractFamily=None)],
                           Families=[self.family], AccessorEvidence=[
            dict(Module='a.dll', MethodToken='get', OwnerKind='Property', OwnerToken='property', MappedName=None),
            dict(Module='b.dll', MethodToken='solo', OwnerKind='Property', OwnerToken='property', MappedName=None)])
        self.properties = {('a.dll', 'property'), ('b.dll', 'property')}

    def test_exact_sdk_token_excludes_whole_family_but_preserves_other_physical_module(self):
        selected, families, excluded = select_accessors(self.review, self.properties, {('CV/a.dll', 'override')})
        self.assertEqual({('b.dll', 'solo')}, selected)
        self.assertEqual(set(), families)
        self.assertEqual([('CV/a.dll', 'override'), ('a.dll', 'get')], excluded)

    def test_complete_editable_family_expands_and_matching_filename_is_not_identity(self):
        selected, families, excluded = select_accessors(self.review, self.properties, {('other/a.dll', 'get')})
        self.assertEqual({('a.dll', 'get'), ('CV/a.dll', 'override'), ('b.dll', 'solo')}, selected)
        self.assertEqual({'family'}, families)
        self.assertEqual([], excluded)

    def test_blocked_mapped_or_inconsistent_family_cannot_be_partially_selected(self):
        for key, value in (('MappedName', 'already'), ('DerivedName', 'get_Other')):
            review = copy.deepcopy(self.review)
            review['Families'][0]['Members'][1][key] = value
            with self.assertRaises(AssertionError): select_accessors(review, self.properties, set())
        self.family['Blockers'] = ['external-contract']
        with self.assertRaises(AssertionError): select_accessors(self.review, self.properties, set())


if __name__ == '__main__':
    unittest.main()
