"""Portable regressions for physical accessor-to-source evidence binding."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from behavior_review import BehaviorReview, sha


class AccessorSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / 'Definitions.cs'
        self.source.write_text('class D { public int this[int index] => index; }', encoding='utf-8')
        self.review = BehaviorReview.__new__(BehaviorReview)
        b = self.review
        b.target = root / 'input'
        b.relative = 'compat/Library.dll'
        b.module_id = 'm0002'
        b.source_root = root
        b.verified_sources = {}
        b.accessor_sources = {}
        b.db = sqlite3.connect(':memory:')
        self.addCleanup(b.db.close)
        b.db.execute('CREATE TABLE source(id TEXT, data TEXT)')
        b.db.execute('INSERT INTO source VALUES (?,?)', ('m0002:0x17000001', json.dumps({
            'Source': self.source.name, 'Sha256': sha(self.source), 'Line': 1, 'Kind': 'IndexerDeclaration'})))
        self.method = {'Module': b.relative, 'Token': '0x06000001', 'Identity': 'Library, Version=1.0.0.0',
                       'Mvid': 'physical-mvid', 'Sha256': 'physical-hash', 'Signature': 'System.Int32 D::a(System.Int32)', 'OriginalName': 'a'}
        b.entries = {'Methods': {self.method['Token']: self.method}}
        self.report = {'Kind': 'AccessorReview', 'TargetRoot': str(b.target), 'Methods': [copy.deepcopy(self.method)],
                       'AccessorEvidence': [{'Module': b.relative, 'MethodToken': self.method['Token'],
                           'MethodSignature': self.method['Signature'], 'MethodName': 'a', 'OwnerKind': 'Property',
                           'OwnerToken': '0x17000001', 'OwnerSignature': 'System.Int32 D::Item(System.Int32)', 'AccessorRole': 'get'}]}
        self.path = root / 'accessors.json'

    def bind(self):
        self.path.write_text(json.dumps(self.report), encoding='utf-8')
        self.review.bind_accessor_sources(self.path, [0x06000001])

    def test_exact_physical_owner_supplies_missing_source(self):
        self.bind()
        result = self.review.source(0x06000001)[0]
        self.assertEqual(result['Id'], 'm0002:0x06000001')
        self.assertEqual(result['DeclarationId'], 'm0002:0x17000001')
        self.assertEqual(result['AccessorEvidence']['Sha256'], sha(self.path))
        self.assertEqual(self.review.db.execute('SELECT COUNT(*) FROM source').fetchone()[0], 1)

    def test_same_identity_different_physical_input_is_rejected(self):
        for key, value in [('Module', 'other/Library.dll'), ('Mvid', 'other-mvid'), ('Sha256', 'other-hash')]:
            with self.subTest(key=key):
                saved = self.report['Methods'][0][key]
                self.report['Methods'][0][key] = value
                with self.assertRaises(ValueError): self.bind()
                self.report['Methods'][0][key] = saved
                self.assertFalse(self.review.accessor_sources)

    def test_stale_signature_ambiguous_owner_and_wrong_kind_are_rejected(self):
        original = copy.deepcopy(self.report)
        for change in ('signature', 'duplicate', 'kind'):
            self.report = copy.deepcopy(original)
            if change == 'signature': self.report['AccessorEvidence'][0]['MethodSignature'] = 'other overload'
            if change == 'duplicate': self.report['AccessorEvidence'] *= 2
            if change == 'kind': self.report['AccessorEvidence'][0]['OwnerToken'] = '0x02000001'
            with self.subTest(change=change), self.assertRaises(ValueError): self.bind()
            self.assertFalse(self.review.accessor_sources)

    def test_source_hash_still_required(self):
        self.bind()
        self.source.write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Stale source'): self.review.source(0x06000001)

    def test_no_binding_does_not_guess_from_name(self):
        with self.assertRaisesRegex(ValueError, 'No source declaration'): self.review.source(0x06000001)


if __name__ == '__main__':
    unittest.main()
