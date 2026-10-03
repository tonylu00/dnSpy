import hashlib
import json
import pathlib
import tempfile
import unittest
from prepare_physical_review import prepare


class PhysicalReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.legacy = self.root / 'CV' / '4.0'
        self.legacy.mkdir(parents=True)
        self.inventories = []
        for folder, data in ((self.root, b'root'), (self.legacy, b'legacy')):
            (folder / 'Same.dll').write_bytes(data)
            row = dict(Module='Same.dll', Token='0x02000001', Sha256=hashlib.sha256(data).hexdigest().upper(),
                       NewName='', NeedsReadableName=True, ParameterNames=[], LocalNames=[])
            inventory = dict(TargetRoot=str(folder), Types=[row], Fields=[], Methods=[])
            path = folder / 'native.json'
            path.write_text(json.dumps(inventory), encoding='utf-8')
            self.inventories.append(str(path))
        self.spec = dict(TargetRoot=str(self.root), ContractReferenceSha256='manifest', Inventories=self.inventories,
                         Rows=[dict(Kind='Types', Module='Same.dll', Token='0x02000001', NewName='RootRole', Reason='root role'),
                               dict(Kind='Types', Module='CV/4.0/Same.dll', Token='0x02000001', NewName='LegacyRole', Reason='legacy role')])

    def tearDown(self): self.temp.cleanup()

    def test_same_basename_and_token_remain_distinct(self):
        rows = prepare(self.spec)['Types']
        self.assertEqual(['Same.dll', 'CV/4.0/Same.dll'], [r['Module'] for r in rows])
        self.assertEqual(['RootRole', 'LegacyRole'], [r['NewName'] for r in rows])

    def test_stale_input_rejected(self):
        (self.legacy / 'Same.dll').write_bytes(b'changed')
        with self.assertRaises(ValueError): prepare(self.spec)

    def test_preservation_is_explicit_and_has_no_alias(self):
        self.spec['Rows'][0].update(Disposition='preserve', NewName='')
        row = prepare(self.spec)['Types'][0]
        self.assertFalse(row['NeedsReadableName'])
        self.assertFalse(row['Unresolved'])
        self.assertEqual('preserve', row['ReviewDisposition'])

    def test_resolution_carries_explicit_preimage_only_for_named_definition(self):
        decision = self.spec['Rows'][0]
        decision.update(ResolveExistingUnresolved=True, PreviousUnresolvedEvidence={'Reason': 'old', 'UnresolvedReason': 'missing'})
        row = prepare(self.spec)['Types'][0]
        self.assertTrue(row['ResolveExistingUnresolved'])
        self.assertEqual(decision['PreviousUnresolvedEvidence'], row['PreviousUnresolvedEvidence'])
        decision['PreviousUnresolvedEvidence'] = {}
        with self.assertRaises(ValueError): prepare(self.spec)
        decision.update(Disposition='unresolved', NewName='', PreviousUnresolvedEvidence={'Reason': 'old'})
        with self.assertRaises(ValueError): prepare(self.spec)

    def test_unresolved_rejects_alias_and_requires_reason(self):
        self.spec['Rows'][0]['Disposition'] = 'unresolved'
        with self.assertRaises(ValueError): prepare(self.spec)
        self.spec['Rows'][0].update(NewName='', Reason='')
        with self.assertRaises(ValueError): prepare(self.spec)

    def test_escaped_inventory_module_rejected(self):
        path = pathlib.Path(self.inventories[1])
        inventory = json.loads(path.read_text())
        inventory['Types'][0]['Module'] = '../../Same.dll'
        path.write_text(json.dumps(inventory), encoding='utf-8')
        with self.assertRaises(ValueError): prepare(self.spec)

    def test_unselected_rows_still_cannot_escape_and_selected_duplicates_conflict(self):
        path = pathlib.Path(self.inventories[1])
        inventory = json.loads(path.read_text())
        unselected = dict(inventory['Types'][0], Token='0x02000002', Module='../../Same.dll')
        inventory['Types'].append(unselected)
        path.write_text(json.dumps(inventory), encoding='utf-8')
        with self.assertRaises(ValueError): prepare(self.spec)
        inventory['Types'].pop()
        inventory['Types'].append(dict(inventory['Types'][0], NewName='ConflictingAlias'))
        path.write_text(json.dumps(inventory), encoding='utf-8')
        with self.assertRaises(ValueError): prepare(self.spec)

    def test_alias_withdrawal_requires_explicit_method_preimage(self):
        native_path = pathlib.Path(self.inventories[0])
        native = json.loads(native_path.read_text())
        native['Methods'] = [dict(native['Types'][0], Token='0x06000001')]
        native_path.write_text(json.dumps(native), encoding='utf-8')
        self.spec['Rows'] = [dict(Kind='Methods', Module='Same.dll', Token='0x06000001', Disposition='unresolved',
                                 Reason='The predicate role lacks evidence', RemoveExistingAlias=True, ExpectedAlias='BadWidthName')]
        reviewed = prepare(self.spec)['Methods'][0]
        self.assertTrue(reviewed['RemoveExistingAlias'])
        self.assertEqual('BadWidthName', reviewed['ExpectedAlias'])
        self.assertTrue(reviewed['Unresolved'])
        self.spec['Rows'][0]['ExpectedAlias'] = ''
        with self.assertRaises(ValueError): prepare(self.spec)
        self.spec['Rows'][0].update(Kind='Types', Token='0x02000001', ExpectedAlias='BadTypeName')
        with self.assertRaises(ValueError): prepare(self.spec)


if __name__ == '__main__': unittest.main()
