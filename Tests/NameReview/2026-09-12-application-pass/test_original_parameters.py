import copy
import hashlib
import json
import pathlib
import tempfile
import unittest
from checkpoint_original_parameters import load_reports, supplement


class NativeOriginalParameters(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        source = self.root / 'compat' / 'Library.dll'
        source.parent.mkdir()
        source.write_bytes(b'exact physical fixture')
        self.row = dict(Module='compat/Library.dll', Token='0x06000001',
            Signature='System.Void Handler::Receive(System.Object)', Identity='Library, Version=1.0.0.0',
            Mvid='fixture-mvid', Sha256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),
            ParameterNames=[dict(Sequence=1, OriginalName='sender', NewName='sender', HasMetadata=True)])
        self.report = dict(Input=str(source), **{k:self.row[k] for k in ('Identity','Mvid','Sha256')},
            Methods=[dict(Token=self.row['Token'], Signature=self.row['Signature'],
                Parameters=[dict(ArgumentIndex=0, Sequence=None, Name='this'),
                            dict(ArgumentIndex=1, Sequence=1, Name='sender')])])
        self.path = self.root / 'native.json'
        self.path.write_text(json.dumps(self.report))
        self.reports = load_reports([self.path])

    def run_supplement(self, fresh=None, scopes=None):
        return supplement(self.row, fresh or copy.deepcopy(self.row), scopes or {}, self.root, self.reports)

    def test_preserves_original_and_uses_sequence_not_receiver_index(self):
        old = copy.deepcopy(self.row)
        scopes, retained = self.run_supplement()
        self.assertEqual(scopes[('ParameterNames',1)], dict(ExpectedName='sender', NewName='sender'))
        self.assertEqual(retained[0]['Name'], 'sender')
        self.assertEqual(self.row, old)

    def test_rejects_name_change_and_missing_metadata(self):
        for key,value in [('NewName','eventSource'),('OriginalName','source'),('HasMetadata',False)]:
            fresh = copy.deepcopy(self.row);fresh['ParameterNames'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):self.run_supplement(fresh)

    def test_rejects_missing_review_and_duplicate_sequence(self):
        for params in [[],self.row['ParameterNames']*2]:
            fresh = copy.deepcopy(self.row);fresh['ParameterNames'] = params
            with self.assertRaises(ValueError):self.run_supplement(fresh)

    def test_does_not_override_existing_checked_scope(self):
        existing = {('ParameterNames',1):dict(ExpectedName='wrong',NewName='different')}
        scopes, retained = self.run_supplement(scopes=existing)
        self.assertEqual(scopes, existing)
        self.assertEqual(retained, [])

    def test_rejects_other_physical_path(self):
        self.reports = {self.root/'Library.dll':next(iter(self.reports.values()))}
        with self.assertRaises(ValueError):self.run_supplement()

    def test_rejects_native_identity_and_signature_drift(self):
        for key in ['Identity','Mvid','Sha256']:
            reports = copy.deepcopy(self.reports);next(iter(reports.values()))[key] = 'other'
            with self.subTest(key=key),self.assertRaises(ValueError):supplement(self.row,self.row,{},self.root,reports)
        for key in ['Token','Signature']:
            reports = copy.deepcopy(self.reports);next(iter(reports.values()))['Methods'][0][key] = 'other'
            with self.subTest(key=key),self.assertRaises(ValueError):supplement(self.row,self.row,{},self.root,reports)

    def test_rejects_native_spelling_and_duplicate_parameters(self):
        for duplicate in [False,True]:
            reports = copy.deepcopy(self.reports);ps = next(iter(reports.values()))['Methods'][0]['Parameters']
            if duplicate:ps.append(copy.deepcopy(ps[1]))
            else:ps[1]['Name'] = 'source'
            with self.assertRaises(ValueError):supplement(self.row,self.row,{},self.root,reports)

    def test_rejects_input_hash_drift_and_duplicate_reports(self):
        with self.assertRaises(ValueError):load_reports([self.path,self.path])
        pathlib.Path(self.report['Input']).write_bytes(b'changed binary')
        with self.assertRaises(ValueError):load_reports([self.path])


if __name__ == '__main__':
    unittest.main()
