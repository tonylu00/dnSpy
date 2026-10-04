"""Exact inventory selection must retain native contract evidence and reject drift."""
import copy
import hashlib
import json
import pathlib
import tempfile
import unittest

from prepare_physical_review import prepare


class InventorySelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / 'Module.dll').write_bytes(b'physical fixture input')
        self.row = dict(Module='Module.dll', Token='0x06000001', Signature='System.Void T::M()',
                        OriginalName='M', Identity='Module, Version=1.0.0.0', Mvid='physical-mvid',
                        Sha256=hashlib.sha256((self.root / 'Module.dll').read_bytes()).hexdigest().upper(),
                        ParameterNames=[dict(Sequence=1, OriginalName='arg', HasMetadata=True, NewName='')],
                        LocalNames=[], ContractFamily=None, MappingBlocker='virtual: requires family',
                        NewName='', Unresolved=False)
        self.ordinary = self.write('ordinary.json', self.row)
        family = dict(self.row, ContractFamily='native-family', MappingBlocker=None)
        self.family = self.write('family.json', family)
        self.spec = dict(TargetRoot=str(self.root), ContractReferenceSha256='bound-contract',
                         Inventories=[str(self.ordinary), str(self.family)],
                         Rows=[dict(Kind='Methods', Module='Module.dll', Token='0x06000001',
                                    Inventory=str(self.family), NewName='UpdateState', Reason='native body evidence')])

    def write(self, name, row):
        path = self.root / name
        path.write_text(json.dumps(dict(TargetRoot=str(self.root), Methods=[row])))
        return path

    def test_explicit_family_keeps_native_guards(self):
        row = prepare(self.spec)['Methods'][0]
        self.assertEqual(row['ContractFamily'], 'native-family')
        self.assertIsNone(row['MappingBlocker'])
        self.assertEqual(row['Signature'], self.row['Signature'])

    def test_explicit_ordinary_keeps_blocker(self):
        self.spec['Rows'][0]['Inventory'] = str(self.ordinary)
        self.assertEqual(prepare(self.spec)['Methods'][0]['MappingBlocker'], self.row['MappingBlocker'])

    def test_implicit_conflict_still_rejected(self):
        del self.spec['Rows'][0]['Inventory']
        with self.assertRaisesRegex(ValueError, 'Conflicting native inventories'):
            prepare(self.spec)

    def test_unbound_choice_rejected(self):
        self.spec['Rows'][0]['Inventory'] = str(self.root / 'unbound.json')
        with self.assertRaisesRegex(ValueError, 'not in the bound inventory list'):
            prepare(self.spec)

    def test_selection_does_not_bypass_physical_hash(self):
        (self.root / 'Module.dll').write_bytes(b'changed input')
        with self.assertRaisesRegex(ValueError, 'Stale physical inventory'):
            prepare(self.spec)

    def test_selection_does_not_bypass_scope_position(self):
        self.spec['Rows'][0]['ParameterNames'] = {'2': 'state'}
        with self.assertRaisesRegex(ValueError, 'Missing physical scope position'):
            prepare(self.spec)

    def test_selection_does_not_bypass_metadata_requirement(self):
        family = dict(self.row, ContractFamily='native-family', MappingBlocker=None)
        family['ParameterNames'] = [dict(self.row['ParameterNames'][0], HasMetadata=False)]
        self.write('family.json', family)
        self.spec['Rows'][0]['ParameterNames'] = {'1': 'state'}
        with self.assertRaisesRegex(ValueError, 'no metadata row'):
            prepare(self.spec)

    def test_duplicate_decision_rejected(self):
        self.spec['Rows'].append(copy.deepcopy(self.spec['Rows'][0]))
        with self.assertRaisesRegex(ValueError, 'Repeated decision'):
            prepare(self.spec)

    def test_scope_join_retains_family_guard(self):
        ordinary = dict(self.row, LocalNames=[dict(Index=0, ExpectedType='System.Boolean', NewName='')])
        self.write('ordinary.json', ordinary)
        self.spec['Rows'][0].update(ScopeInventory=str(self.ordinary), LocalNames={'0': 'useTcp'})
        row = prepare(self.spec)['Methods'][0]
        self.assertEqual(row['ContractFamily'], 'native-family')
        self.assertIsNone(row['MappingBlocker'])
        self.assertEqual(row['LocalNames'][0]['NewName'], 'useTcp')

    def test_scope_join_rejects_other_definition(self):
        self.spec['Rows'][0]['ScopeInventory'] = str(self.ordinary)
        for label in ('Identity', 'Mvid', 'Sha256', 'Signature', 'OriginalName'):
            with self.subTest(label=label):
                row = dict(self.row)
                row[label] += '-different'
                self.write('ordinary.json', row)
                with self.assertRaisesRegex(ValueError, 'Native scope identity differs: ' + label):
                    prepare(self.spec)

    def test_scope_join_requires_bound_input(self):
        self.spec['Rows'][0]['ScopeInventory'] = str(self.root / 'unbound.json')
        with self.assertRaisesRegex(ValueError, 'Scope inventory requires'):
            prepare(self.spec)


if __name__ == '__main__':
    unittest.main()
