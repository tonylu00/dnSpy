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

    def test_unresolved_scope_merge_requires_explicit_prior_decision(self):
        decision = self.spec['Rows'][0]
        decision.pop('NewName')
        decision.update(ParameterNames={'1': 'copiedByteCount'},
                        DefinitionOnlyUnresolvedReason='Owner role remains unknown',
                        MergeExistingUnresolvedScopes=True,
                        PreviousUnresolvedScopeDecision={'Reason': 'prior', 'LocalNames': []})
        row = prepare(self.spec)['Methods'][0]
        self.assertTrue(row['Unresolved'])
        self.assertTrue(row['DefinitionOnlyUnresolved'])
        self.assertTrue(row['MergeExistingUnresolvedScopes'])
        self.assertEqual(decision['PreviousUnresolvedScopeDecision'], row['PreviousUnresolvedScopeDecision'])
        for key in ('DefinitionOnlyUnresolvedReason', 'PreviousUnresolvedScopeDecision'):
            bad = copy.deepcopy(self.spec)
            del bad['Rows'][0][key]
            with self.subTest(key=key), self.assertRaises(ValueError): prepare(bad)
        bad = copy.deepcopy(self.spec)
        del bad['Rows'][0]['MergeExistingUnresolvedScopes']
        with self.assertRaises(ValueError): prepare(bad)

    def test_historical_alias_preimages_are_retained(self):
        self.spec['Rows'][0].update(PreviousLedgerAlias='', ExpectedMappedAlias='OldAlias')
        row = prepare(self.spec)['Methods'][0]
        self.assertEqual(row['PreviousLedgerAlias'], '')
        self.assertEqual(row['ExpectedMappedAlias'], 'OldAlias')

    def test_incomplete_historical_alias_preimages_are_rejected(self):
        for values in ({'PreviousLedgerAlias': ''}, {'ExpectedMappedAlias': 'OldAlias'},
                       {'PreviousLedgerAlias': '', 'ExpectedMappedAlias': ''}):
            spec = copy.deepcopy(self.spec)
            spec['Rows'][0].update(values)
            with self.assertRaises(ValueError):
                prepare(spec)

    def test_unknown_decision_fields_fail_before_evidence_can_be_dropped(self):
        for key in ('ScopeUnresolvedEvidence', 'UnresolvedScopeEvidance', 'ContractFamily', 'PreviousEvidence'):
            with self.subTest(key=key):
                spec = copy.deepcopy(self.spec)
                spec['Rows'][0][key] = {'Locals': []}
                with self.assertRaisesRegex(ValueError, 'Unknown decision keys: ' + key):
                    prepare(spec)

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

    def scope_uncertainty(self):
        self.spec['Rows'][0].update(NewName='', ParameterNames={'1': 'requestCode'},
                                   DefinitionOnlyUnresolvedReason='Missing printed source declaration owner witness')

    def test_definition_uncertainty_retains_positive_scopes(self):
        self.scope_uncertainty()
        row = prepare(self.spec)['Methods'][0]
        self.assertTrue(row['Unresolved'])
        self.assertTrue(row['DefinitionOnlyUnresolved'])
        self.assertEqual(row['NewName'], '')
        self.assertEqual(row['ParameterNames'][0]['NewName'], 'requestCode')
        self.assertIn('Missing printed', row['UnresolvedReason'])

    def test_scoped_withdrawal_requires_definition_uncertainty_and_exact_alias(self):
        self.scope_uncertainty()
        self.spec['Rows'][0].update(RemoveExistingAlias=True, ExpectedAlias='WrongGeneratedName')
        row = prepare(self.spec)['Methods'][0]
        self.assertTrue(row['RemoveExistingAlias'])
        self.assertTrue(row['DefinitionOnlyUnresolved'])
        self.assertEqual('WrongGeneratedName', row['ExpectedAlias'])
        self.assertEqual('requestCode', row['ParameterNames'][0]['NewName'])
        del self.spec['Rows'][0]['DefinitionOnlyUnresolvedReason']
        with self.assertRaisesRegex(ValueError, 'Alias withdrawal'):
            prepare(self.spec)

    def test_definition_uncertainty_requires_missing_evidence(self):
        self.scope_uncertainty()
        for reason in ('', '  ', None, 3):
            self.spec['Rows'][0]['DefinitionOnlyUnresolvedReason'] = reason
            with self.assertRaisesRegex(ValueError, 'Definition-only uncertainty'):
                prepare(self.spec)

    def test_definition_uncertainty_requires_positive_scopes(self):
        self.scope_uncertainty()
        del self.spec['Rows'][0]['ParameterNames']
        with self.assertRaisesRegex(ValueError, 'supported name'):
            prepare(self.spec)

    def test_definition_uncertainty_rejects_definition_alias(self):
        self.scope_uncertainty()
        self.spec['Rows'][0]['NewName'] = 'InventedOwner'
        with self.assertRaisesRegex(ValueError, 'Definition-only uncertainty'):
            prepare(self.spec)

    def test_definition_uncertainty_rejects_other_dispositions(self):
        self.scope_uncertainty()
        for disposition in ('preserve', 'unresolved'):
            self.spec['Rows'][0]['Disposition'] = disposition
            with self.assertRaisesRegex(ValueError, 'Definition-only uncertainty'):
                prepare(self.spec)

    def test_definition_uncertainty_rejects_nonmethods(self):
        self.scope_uncertainty()
        family = json.loads(self.family.read_text())
        family['Fields'] = family.pop('Methods')
        self.family.write_text(json.dumps(family))
        self.spec['Rows'][0]['Kind'] = 'Fields'
        with self.assertRaisesRegex(ValueError, 'Definition-only uncertainty'):
            prepare(self.spec)


class UnresolvedScopeEvidenceTests(unittest.TestCase):
    write = InventorySelectionTests.write

    def setUp(self):
        InventorySelectionTests.setUp(self)
        row = dict(self.row, LocalNames=[dict(Index=0, ExpectedType='System.UInt16', NewName=''),
                                        dict(Index=1, ExpectedType='System.Byte[]', NewName='')])
        self.write('family.json', row)
        self.spec['Rows'][0]['UnresolvedScopeEvidence'] = dict(
            Locals=[dict(Index=0, ExpectedType='System.UInt16', MissingEvidence='Descriptor and APDU roles reuse one slot; split ownership is unproven.')])

    def test_exact_local_uncertainty_keeps_independent_aliases(self):
        self.spec['Rows'][0]['LocalNames'] = {'1': 'responseData'}
        row = prepare(self.spec)['Methods'][0]
        self.assertEqual(row['UnresolvedScopeEvidence'], self.spec['Rows'][0]['UnresolvedScopeEvidence'])
        self.assertEqual(row['LocalNames'][0]['NewName'], '')
        self.assertEqual(row['LocalNames'][1]['NewName'], 'responseData')
        row['UnresolvedScopeEvidence']['Locals'][0]['MissingEvidence'] = 'changed result'
        self.assertNotEqual(row['UnresolvedScopeEvidence'], self.spec['Rows'][0]['UnresolvedScopeEvidence'])

    def test_stale_type_and_missing_slot_rejected(self):
        entry = self.spec['Rows'][0]['UnresolvedScopeEvidence']['Locals'][0]
        for replacement in (dict(entry, ExpectedType='System.Byte'), dict(entry, Index=7)):
            self.spec['Rows'][0]['UnresolvedScopeEvidence']['Locals'] = [replacement]
            with self.assertRaisesRegex(ValueError, 'duplicate, absent or stale'):
                prepare(self.spec)

    def test_duplicate_position_rejected(self):
        entries = self.spec['Rows'][0]['UnresolvedScopeEvidence']['Locals']
        entries.append(copy.deepcopy(entries[0]))
        with self.assertRaisesRegex(ValueError, 'duplicate, absent or stale'):
            prepare(self.spec)

    def test_positive_alias_conflict_rejected(self):
        self.spec['Rows'][0]['LocalNames'] = {'0': 'maxApduLength'}
        with self.assertRaisesRegex(ValueError, 'cannot carry an alias'):
            prepare(self.spec)

    def test_parameter_preimage_rejected_and_retained(self):
        self.spec['Rows'][0]['UnresolvedScopeEvidence'] = dict(
            Parameters=[dict(Sequence=1, OriginalName='wrongArg', MissingEvidence='Domain meaning unknown')])
        with self.assertRaisesRegex(ValueError, 'duplicate, absent or stale'):
            prepare(self.spec)
        self.spec['Rows'][0]['UnresolvedScopeEvidence']['Parameters'][0]['OriginalName'] = 'arg'
        self.assertEqual(prepare(self.spec)['Methods'][0]['UnresolvedScopeEvidence'], self.spec['Rows'][0]['UnresolvedScopeEvidence'])

    def test_evidence_is_required_and_unknown_keys_rejected(self):
        evidence = copy.deepcopy(self.spec['Rows'][0]['UnresolvedScopeEvidence'])
        for replacement in ({}, {'Locals': []}, {'Fields': []}, [], {'Locals': 'zero'}):
            self.spec['Rows'][0]['UnresolvedScopeEvidence'] = replacement
            with self.assertRaises(ValueError):
                prepare(self.spec)
        for reason in ('', ' ', None, 4):
            self.spec['Rows'][0]['UnresolvedScopeEvidence'] = copy.deepcopy(evidence)
            self.spec['Rows'][0]['UnresolvedScopeEvidence']['Locals'][0]['MissingEvidence'] = reason
            with self.assertRaises(ValueError):
                prepare(self.spec)
        self.spec['Rows'][0]['UnresolvedScopeEvidence'] = evidence
        for position in (True, '0', -1):
            self.spec['Rows'][0]['UnresolvedScopeEvidence']['Locals'][0]['Index'] = position
            with self.assertRaises(ValueError):
                prepare(self.spec)


if __name__ == '__main__':
    unittest.main()
