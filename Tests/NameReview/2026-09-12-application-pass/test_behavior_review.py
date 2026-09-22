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
        b.usage_sources = {}
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


class UsageSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.path = root / 'inspection.json'
        self.source = root / 'Caller.cs'
        self.source.write_text('class C { void Run() { Use(x => x); } }', encoding='utf-8')
        b = self.review = BehaviorReview.__new__(BehaviorReview)
        b.module_id, b.relative = 'm0002', 'compat/Library.dll'
        b.module = {'Input': str(root / b.relative), 'Mvid': 'physical-mvid', 'Sha256': 'physical-hash'}
        b.source_root, b.verified_sources = root, {}
        b.accessor_sources, b.usage_sources = {}, {}
        b.db = sqlite3.connect(':memory:')
        self.addCleanup(b.db.close)
        b.db.executescript('CREATE TABLE source(id TEXT,data TEXT); CREATE TABLE symbols(id TEXT,data TEXT); CREATE TABLE edges(source TEXT,target TEXT,data TEXT);')
        self.method = {'Token': '0x06000001', 'Identity': 'Library, Version=1.0', 'Signature': 'System.Int32 C::a(System.Int32)'}
        self.caller = {'Token': '0x06000002', 'Signature': 'System.Void C::Run()'}
        self.field = {'Token': '0x04000001', 'Identity': self.method['Identity'], 'Signature': 'System.Int32 C::value'}
        b.entries = {'Methods': {r['Token']: r for r in (self.method, self.caller)}, 'Fields': {self.field['Token']: self.field}}
        self.caller_id = 'm0002:' + self.caller['Token']
        b.db.execute('INSERT INTO source VALUES (?,?)', (self.caller_id, json.dumps({'Source': self.source.name, 'Sha256': sha(self.source), 'Line': 1, 'Kind': 'MethodDeclaration'})))
        self.edges = []
        instructions = []
        for index, (member, op) in enumerate([(self.method, 'ldftn'), (self.field, 'ldfld')]):
            sid = 'm0002:' + member['Token']
            b.db.execute('INSERT INTO symbols VALUES (?,?)', (sid, json.dumps(member)))
            edge = {'From': self.caller_id, 'Offset': index, 'Operation': op, 'Target': {'Id': sid, 'Signature': member['Signature'], 'Assembly': member['Identity'], 'PhysicalModule': b.module['Input'], 'Status': 'input', 'Error': None}}
            self.edges.append(edge)
            instructions.append({'Offset': index, 'OpCode': op, 'Operand': {'Token': member['Token'], 'Text': member['Signature']}})
        self.report = {**b.module, 'Identity': self.method['Identity'], 'Methods': [{**self.method, 'Instructions': []}, {**self.caller, 'Instructions': instructions}]}

    def bind(self):
        b = self.review
        b.db.execute('DELETE FROM edges')
        for e in self.edges:
            b.db.execute('INSERT INTO edges VALUES (?,?,?)', (e['From'], e['Target']['Id'], json.dumps(e)))
        self.path.write_text(json.dumps(self.report), encoding='utf-8')
        b.bind_usage_sources(self.path, {0x06000001: 0x06000002, 0x04000001: 0x06000002})

    def test_exact_delegate_and_field_usage_keep_original_graph(self):
        self.bind()
        for token in (0x06000001, 0x04000001):
            result = self.review.source(token)[0]
            self.assertEqual(result['SourceId'], self.caller_id)
            self.assertEqual(result['UsageEvidence']['Sha256'], sha(self.path))
            self.assertEqual(result['Id'], f'm0002:0x{token:08X}')
        self.assertEqual(self.review.db.execute('SELECT COUNT(*) FROM source').fetchone()[0], 1)

    def test_wrong_physical_module_and_il_are_rejected_atomically(self):
        report, edges = copy.deepcopy(self.report), copy.deepcopy(self.edges)
        for failure in ('mvid', 'path', 'signature', 'il', 'edge', 'missing'):
            self.report, self.edges = copy.deepcopy(report), copy.deepcopy(edges)
            if failure == 'mvid': self.report['Mvid'] = 'another module'
            if failure == 'path': self.edges[0]['Target']['PhysicalModule'] += '.other'
            if failure == 'signature': self.report['Methods'][0]['Signature'] += '.other'
            if failure == 'il': self.report['Methods'][1]['Instructions'][0]['Operand']['Text'] += '.other'
            if failure == 'edge': self.edges[0]['Target']['Status'] = 'unresolved'
            if failure == 'missing': self.edges.clear()
            with self.subTest(failure=failure), self.assertRaises(ValueError): self.bind()
            self.assertFalse(self.review.usage_sources)

    def test_stale_caller_source_is_rejected(self):
        self.source.write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Stale source'): self.bind()


if __name__ == '__main__':
    unittest.main()
