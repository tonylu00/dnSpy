import copy
import unittest
from review_ledger import merge_scopes, replace_alias, replace_method_alias, remove_method_alias, resolve_unresolved, resolve_scoped_definition, validate_review_only, refresh_evidence, apply_proposal, proposal_preimage


class LedgerScopeMergeTests(unittest.TestCase):
    def scoped_definition_fixture(self):
        old = copy.deepcopy(self.old)
        old.update(NewName='', Unresolved=False, UnresolvedReason='', MappingBlocker=None, ScopedMappingBlocker=None,
                   ContractFamily=None, Annotation={'kept': True}, UnresolvedDefinitionEvidence='Only input forwarding was reviewed')
        reviewed = dict(old, NewName='SetPropertyData', Reason='Verified property header and complete copy/resize behavior',
                        ResolveExistingScopedDefinition=True,
                        PreviousScopedDefinitionEvidence={k: old[k] for k in ('Reason', 'UnresolvedDefinitionEvidence')},
                        ParameterNames=[], LocalNames=[])
        change = dict(Kind='Method', Module=old['Module'], Token=old['Token'], Before=None,
                      Requested=reviewed['NewName'], Applied=reviewed['NewName'])
        checked = {('ParameterNames', 1): dict(ExpectedName='a', NewName='count'),
                   ('LocalNames', 0): dict(ExpectedType='System.Int32', NewName='total')}
        return old, reviewed, change, checked

    def test_scoped_definition_resolution_preserves_scopes_and_retires_uncertainty(self):
        old, reviewed, change, checked = self.scoped_definition_fixture()
        result = resolve_scoped_definition(old, reviewed, '', change, reviewed['NewName'], checked)
        for key in ('ParameterNames', 'LocalNames', 'Annotation'):
            self.assertEqual(old[key], result[key])
        self.assertNotIn('UnresolvedDefinitionEvidence', result)
        self.assertNotIn('ResolveExistingScopedDefinition', result)
        self.assertNotIn('PreviousScopedDefinitionEvidence', result)
        self.assertEqual(old['UnresolvedDefinitionEvidence'], result['ScopedDefinitionResolutions'][0]['PreviousUnresolvedDefinitionEvidence'])
        self.assertIn('UnresolvedDefinitionEvidence', old)
        with self.assertRaises(ValueError): resolve_scoped_definition(result, reviewed, result['NewName'], change, result['NewName'], checked)

    def test_scoped_definition_resolution_requires_physical_preimages_native_and_final_alias(self):
        old, reviewed, change, checked = self.scoped_definition_fixture()
        for key, value in (('Module', 'CV/a.dll'), ('Mvid', 'twin'), ('Sha256', 'stale'), ('Signature', 'other'),
                           ('PreviousScopedDefinitionEvidence', {}), ('ResolveExistingScopedDefinition', False),
                           ('Reason', ''), ('NewName', ''), ('Unresolved', True), ('UnresolvedReason', 'unknown'),
                           ('MappingBlocker', 'SDK'), ('ScopedMappingBlocker', 'virtual'), ('ContractFamily', 'family')):
            with self.subTest(review=key), self.assertRaises(ValueError):
                resolve_scoped_definition(old, dict(reviewed, **{key: value}), '', change, reviewed['NewName'], checked)
        for key, value in (('Before', ''), ('Before', 'oldAlias'), ('Applied', 'SetPropertyData2'), ('Kind', 'Field'),
                           ('Module', 'compat/a.dll'), ('Token', '0x06000002'), ('Action', 'RemoveAlias')):
            with self.subTest(native=key), self.assertRaises(ValueError):
                resolve_scoped_definition(old, reviewed, '', dict(change, **{key: value}), reviewed['NewName'], checked)
        missing = {k: v for k, v in change.items() if k != 'Before'}
        with self.assertRaises(ValueError): resolve_scoped_definition(old, reviewed, '', missing, reviewed['NewName'], checked)
        with self.assertRaises(ValueError): resolve_scoped_definition(old, reviewed, 'already-mapped', change, reviewed['NewName'], checked)
        with self.assertRaises(ValueError): resolve_scoped_definition(old, reviewed, '', change, 'unchecked', checked)
        for key, value in (('NewName', 'already-named'), ('Unresolved', True), ('UnresolvedDefinitionEvidence', ''),
                           ('ParameterNames', []), ('LocalNames', [])):
            bad = dict(old, **{key: value})
            if key in ('ParameterNames','LocalNames'): bad.update(ParameterNames=[], LocalNames=[])
            with self.subTest(previous=key), self.assertRaises(ValueError):
                resolve_scoped_definition(bad, reviewed, '', change, reviewed['NewName'], checked)

    def test_scoped_definition_resolution_checks_old_and_new_scope_positions(self):
        old, reviewed, change, checked = self.scoped_definition_fixture()
        with self.assertRaises(ValueError): resolve_scoped_definition(old, reviewed, '', change, reviewed['NewName'], {})
        bad = copy.deepcopy(checked);bad[('LocalNames', 0)]['ExpectedType']='System.String'
        with self.assertRaises(ValueError): resolve_scoped_definition(old, reviewed, '', change, reviewed['NewName'], bad)
        reviewed['ParameterNames'] = copy.deepcopy(self.review['ParameterNames'])
        checked[('ParameterNames', 2)] = dict(ExpectedName='b', NewName='limit')
        result = resolve_scoped_definition(old, reviewed, '', change, reviewed['NewName'], checked)
        self.assertEqual(['count','limit'], [p['NewName'] for p in result['ParameterNames']])
        checked[('ParameterNames', 2)]['ExpectedName']='wrong'
        with self.assertRaises(ValueError): resolve_scoped_definition(old, reviewed, '', change, reviewed['NewName'], checked)
        checked[('ParameterNames', 2)]['ExpectedName']='b'
        reviewed['ParameterNames'].append(copy.deepcopy(reviewed['ParameterNames'][0]))
        with self.assertRaises(ValueError): resolve_scoped_definition(old, reviewed, '', change, reviewed['NewName'], checked)

    def proposal_fixture(self):
        old = copy.deepcopy(self.old)
        old.update(Annotation={'kept': True}, NeedsReadableName=True)
        reviewed = dict(old, ApplyExistingProposal=True, PreviousProposalEvidence=proposal_preimage(old),
                        Reason='Fresh property ownership and complete physical family evidence', UnresolvedReason='')
        change = dict(Module=old['Module'], Token=old['Token'], Kind='Method', Before=None,
                      Requested=old['NewName'], Applied=old['NewName'])
        checked = {('ParameterNames', 1): dict(ExpectedName='a', NewName='count'),
                   ('LocalNames', 0): dict(ExpectedType='System.Int32', NewName='total')}
        return old, reviewed, change, checked

    def test_proposal_application_preserves_scopes_history_and_annotations(self):
        old, reviewed, change, checked = self.proposal_fixture()
        reviewed.update(ParameterNames=[], LocalNames=[])
        result = apply_proposal(old, reviewed, '', change, old['NewName'], checked)
        for key in ('ParameterNames', 'LocalNames', 'Annotation', 'NewName'):
            self.assertEqual(old[key], result[key])
        self.assertEqual(old['Reason'], result['ProposalApplications'][0]['PreviousReason'])
        self.assertNotIn('ApplyExistingProposal', result)
        self.assertNotIn('PreviousProposalEvidence', result)
        with self.assertRaises(ValueError): apply_proposal(result, reviewed, old['NewName'], change, old['NewName'], checked)

    def test_proposal_application_rejects_stale_preimages_alias_changes_and_native_suffixes(self):
        old, reviewed, change, checked = self.proposal_fixture()
        for key, value in (('Mvid', 'other'), ('Module', 'CV/a.dll'), ('NewName', 'OtherAlias'),
                           ('PreviousProposalEvidence', {}), ('ApplyExistingProposal', False), ('Unresolved', True),
                           ('Reason', ''), ('UnresolvedReason', 'still unknown')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                apply_proposal(old, dict(reviewed, **{key: value}), '', change, old['NewName'], checked)
        for key, value in (('Before', 'mapped'), ('Applied', 'HistoricalAlias2'), ('Kind', 'Field'),
                           ('Module', 'other/a.dll'), ('Token', '0x06000002'), ('Action', 'RemoveAlias')):
            with self.subTest(native=key), self.assertRaises(ValueError):
                apply_proposal(old, reviewed, '', dict(change, **{key: value}), old['NewName'], checked)
        missing = {k: v for k, v in change.items() if k != 'Before'}
        with self.assertRaises(ValueError): apply_proposal(old, reviewed, '', missing, old['NewName'], checked)
        with self.assertRaises(ValueError): apply_proposal(old, reviewed, '', change, 'unchecked', checked)
        with self.assertRaises(ValueError): apply_proposal(old, reviewed, 'already-mapped', change, old['NewName'], checked)
        old['ParameterNames'][0]['NewName'] = 'changed'
        with self.assertRaises(ValueError): apply_proposal(old, reviewed, '', change, old['NewName'], checked)

    def test_proposal_application_requires_all_scope_identities_and_rejects_duplicates(self):
        old, reviewed, change, checked = self.proposal_fixture()
        with self.assertRaises(ValueError): apply_proposal(old, reviewed, '', change, old['NewName'], {})
        checked[('LocalNames', 0)]['ExpectedType'] = 'System.String'
        with self.assertRaises(ValueError): apply_proposal(old, reviewed, '', change, old['NewName'], checked)
        checked[('LocalNames', 0)]['ExpectedType'] = 'System.Int32'
        reviewed['ParameterNames'].append(copy.deepcopy(reviewed['ParameterNames'][0]))
        with self.assertRaises(ValueError): apply_proposal(old, reviewed, '', change, old['NewName'], checked)

    def test_proposal_application_requires_complete_contract_family(self):
        old, reviewed, change, proof = self.contract_resolution_fixture()
        old.update(NewName=reviewed['NewName'], Unresolved=False, UnresolvedReason='')
        reviewed.pop('ResolveExistingUnresolved')
        reviewed.pop('PreviousUnresolvedEvidence')
        reviewed.update(ApplyExistingProposal=True, PreviousProposalEvidence=proposal_preimage(old))
        result = apply_proposal(old, reviewed, '', change, old['NewName'], checked_family=proof)
        self.assertEqual('family-id', result['ContractFamily'])
        self.assertIsNone(result['MappingBlocker'])
        for group in ('ReviewedMembers', 'Changes', 'FinalRows'):
            with self.assertRaises(ValueError):
                apply_proposal(old, reviewed, '', change, old['NewName'], checked_family=dict(proof, **{group: proof[group][:1]}))

    def contract_resolution_fixture(self):
        old, reviewed, change = self.resolution_fixture()
        old['MappingBlocker'] = 'previous unresolved interface family'
        reviewed.update(ContractFamily='family-id', MappingBlocker=None)
        change['Kind'] = 'ContractMethod'
        sibling = dict(reviewed, Token='0x06000002', Type='Interface', Signature='interface-signature')
        changes = [change, dict(change, Token=sibling['Token'])]
        rows = [dict(Module=r['Module'], Token=r['Token'], ContractFamily='family-id', NewName=r['NewName'],
                     Signature=r['Signature'], ExpectedName=r['OriginalName'], Mvid=r['Mvid'], Sha256=r['Sha256'])
                for r in (reviewed, sibling)]
        proof = dict(Id='family-id', ReviewedMembers=[reviewed, sibling], Changes=changes, FinalRows=rows)
        return old, reviewed, change, proof

    def test_complete_contract_resolution_retains_family_history(self):
        old, reviewed, change, proof = self.contract_resolution_fixture()
        result = resolve_unresolved(old, reviewed, '', change, reviewed['NewName'], checked_family=proof)
        self.assertEqual('family-id', result['ContractFamily'])
        self.assertIsNone(result['MappingBlocker'])
        self.assertEqual(old['Annotation'], result['Annotation'])
        self.assertTrue(old['Unresolved'])
        self.assertEqual(old['UnresolvedReason'], result['UnresolvedResolutions'][0]['PreviousUnresolvedReason'])
        self.assertNotIn('ResolveExistingUnresolved', result)

    def test_contract_resolution_rejects_partial_duplicate_and_wrong_physical_family(self):
        old, reviewed, change, proof = self.contract_resolution_fixture()
        invalid = [None, dict(proof, Id='another-family')]
        for group in ('ReviewedMembers', 'Changes', 'FinalRows'):
            invalid.extend([dict(proof, **{group: proof[group][:1]}),
                            dict(proof, **{group: proof[group] + [proof[group][0]]})])
        for group, key, value in (
                ('ReviewedMembers', 'ContractFamily', 'other'), ('ReviewedMembers', 'NewName', 'wrong'),
                ('Changes', 'Before', 'old-alias'), ('Changes', 'Kind', 'Method'),
                ('Changes', 'Applied', 'GetRegisteredCount2'), ('Changes', 'Action', 'RemoveAlias'),
                ('FinalRows', 'Module', 'CV/a.dll'), ('FinalRows', 'Mvid', 'compatibility-twin'),
                ('FinalRows', 'Sha256', 'stale'), ('FinalRows', 'Signature', 'wrong'),
                ('FinalRows', 'ExpectedName', 'wrong'), ('FinalRows', 'ContractFamily', 'other')):
            bad = copy.deepcopy(proof)
            bad[group][1][key] = value
            invalid.append(bad)
        for bad in invalid:
            with self.subTest(proof=bad), self.assertRaises(ValueError):
                resolve_unresolved(old, reviewed, '', change, reviewed['NewName'], checked_family=bad)

    def resolution_fixture(self, kind='Method', token='0x06000001'):
        old = dict(Module='a.dll', Token=token, Identity='a', Mvid='physical-mvid', Sha256='physical-hash',
                   Type='T', Signature='original-signature', OriginalName='a', NewName='', Unresolved=True,
                   Reason='Previous inspection', UnresolvedReason='Missing producer', NeedsReadableName=True,
                   ParameterNames=[], LocalNames=[], Annotation={'kept': True})
        reviewed = copy.deepcopy(old)
        reviewed.update(NewName='GetRegisteredCount', Unresolved=False, UnresolvedReason='', Reason='Producer increments on successful registration',
                        ResolveExistingUnresolved=True, PreviousUnresolvedEvidence={k: old[k] for k in ('Reason', 'UnresolvedReason')})
        change = dict(Module='a.dll', Token=token, Kind=kind, Before=None, Requested='GetRegisteredCount', Applied='GetRegisteredCount')
        return old, reviewed, change

    def test_resolution_preserves_history_and_annotations_without_replay(self):
        for kind, token in (('Method', '0x06000001'), ('Field', '0x04000001'), ('Type', '0x02000001')):
            old, reviewed, change = self.resolution_fixture(kind, token)
            resolved = resolve_unresolved(old, reviewed, '', change, 'GetRegisteredCount')
            self.assertFalse(resolved['Unresolved'])
            self.assertEqual('', resolved['UnresolvedReason'])
            self.assertEqual('Missing producer', resolved['UnresolvedResolutions'][0]['PreviousUnresolvedReason'])
            self.assertEqual(old['Annotation'], resolved['Annotation'])
            self.assertTrue(old['Unresolved'])
            self.assertNotIn('ResolveExistingUnresolved', resolved)
            self.assertNotIn('PreviousUnresolvedEvidence', resolved)
            with self.assertRaises(ValueError): resolve_unresolved(resolved, reviewed, '', change, 'GetRegisteredCount')

    def test_resolution_rejects_stale_preimages_and_wrong_native_proof(self):
        old, reviewed, change = self.resolution_fixture()
        for key, value in (('Sha256', 'stale'), ('Mvid', 'other'), ('Module', 'CV/a.dll'), ('Type', 'other-owner'),
                           ('ResolveExistingUnresolved', False), ('PreviousUnresolvedEvidence', {'Reason': 'stale'}),
                           ('Unresolved', True), ('NewName', ''), ('Reason', ''), ('UnresolvedReason', 'still unknown')):
            bad = dict(reviewed, **{key: value})
            with self.assertRaises(ValueError): resolve_unresolved(old, bad, '', change, 'GetRegisteredCount')
        for key, value in (('Before', 'unexpected'), ('Applied', 'GetRegisteredCount2'), ('Requested', 'other'), ('Action', 'RemoveAlias'),
                           ('Kind', 'Field'), ('Module', 'CV/a.dll'), ('Token', '0x06000002')):
            with self.assertRaises(ValueError): resolve_unresolved(old, reviewed, '', dict(change, **{key: value}), 'GetRegisteredCount')
        with self.assertRaises(ValueError): resolve_unresolved(old, reviewed, 'existing-alias', change, 'GetRegisteredCount')
        with self.assertRaises(ValueError): resolve_unresolved(old, reviewed, '', change, 'unchecked-alias')
        missing = {key: value for key, value in change.items() if key != 'Before'}
        with self.assertRaises(ValueError): resolve_unresolved(old, reviewed, '', missing, 'GetRegisteredCount')
        self.assertEqual('GetRegisteredCount', resolve_unresolved(old, reviewed, '', dict(change, Before=''), 'GetRegisteredCount')['NewName'])

    def test_resolution_scopes_require_checked_identity_and_no_scope_loss(self):
        old, reviewed, change = self.resolution_fixture()
        old['ParameterNames'] = [dict(Sequence=1, OriginalName='a', HasMetadata=True, NewName='')]
        reviewed['ParameterNames'] = [dict(Sequence=1, OriginalName='a', HasMetadata=True, NewName='certificate')]
        checked = {('ParameterNames', 1): dict(ExpectedName='a', NewName='certificate')}
        resolved = resolve_unresolved(old, reviewed, '', change, 'GetRegisteredCount', checked)
        self.assertEqual('certificate', resolved['ParameterNames'][0]['NewName'])
        duplicated = copy.deepcopy(reviewed)
        duplicated['ParameterNames'].append(copy.deepcopy(duplicated['ParameterNames'][0]))
        with self.assertRaises(ValueError): resolve_unresolved(old, duplicated, '', change, 'GetRegisteredCount', checked)
        with self.assertRaises(ValueError): resolve_unresolved(old, reviewed, '', change, 'GetRegisteredCount', {})
        checked[('ParameterNames', 1)]['ExpectedName'] = 'different'
        with self.assertRaises(ValueError): resolve_unresolved(old, reviewed, '', change, 'GetRegisteredCount', checked)
        old['ParameterNames'][0]['NewName'] = 'prior'
        with self.assertRaises(ValueError): resolve_unresolved(old, reviewed, '', change, 'GetRegisteredCount', checked)

    def test_evidence_refresh_keeps_decisions_and_unknown_annotations(self):
        old = dict(Module='a.dll', Token='0x04000001', Identity='a', Mvid='m', Sha256='s', Type='T',
                   Signature='System.String T::a', OriginalName='a', NewName='', Unresolved=True,
                   NeedsReadableName=True, ParameterNames=[], LocalNames=[], ReviewDisposition='unresolved',
                   Reason='Incorrect constant type', UnresolvedReason='Incorrect constant type', Annotation={'kept': True})
        reviewed = copy.deepcopy(old)
        reviewed.update(Reason='Native ConstantType is I1', UnresolvedReason='Native ConstantType is I1',
                        PreviousEvidence={key: old[key] for key in ('Reason', 'UnresolvedReason')})
        merged = refresh_evidence(old, reviewed)
        self.assertEqual('Native ConstantType is I1', merged['Reason'])
        self.assertEqual({'kept': True}, merged['Annotation'])
        self.assertNotIn('PreviousEvidence', merged)
        self.assertEqual('Incorrect constant type', old['Reason'])
        for column, value in (('NewName', 'invented'), ('Mvid', 'other'), ('Unresolved', False),
                              ('ParameterNames', [{'Sequence': 1, 'NewName': 'injected'}]),
                              ('PreviousEvidence', {'Reason': 'stale', 'UnresolvedReason': 'stale'})):
            changed = copy.deepcopy(reviewed)
            changed[column] = value
            with self.assertRaises(ValueError): refresh_evidence(old, changed)
        with self.assertRaises(ValueError): refresh_evidence(old, old)

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

    def test_scope_evidence_retires_resolved_positions_and_keeps_history(self):
        self.old['UnresolvedScopeEvidence'] = dict(Parameters=[dict(Sequence=2, OriginalName='b', MissingEvidence='No role yet')], Locals=[])
        self.review['LocalNames'].append(dict(Index=1, ExpectedType='System.Int32', NewName=''))
        self.review['UnresolvedScopeEvidence'] = dict(Parameters=[], Locals=[dict(Index=1, ExpectedType='System.Int32', MissingEvidence='Loop use not reviewed')])
        result = merge_scopes(self.old, self.review, 'CurrentAcceptedAlias')
        self.assertEqual([], result['UnresolvedScopeEvidence']['Parameters'])
        self.assertEqual(self.review['UnresolvedScopeEvidence']['Locals'], result['UnresolvedScopeEvidence']['Locals'])
        self.assertEqual(self.old['UnresolvedScopeEvidence'], result['ScopeEvidenceReviews'][0]['PreviousUnresolvedScopeEvidence'])
        self.assertEqual('No role yet', self.old['UnresolvedScopeEvidence']['Parameters'][0]['MissingEvidence'])

    def test_scope_evidence_rejects_stale_duplicate_and_unknown_positions(self):
        entry = dict(Sequence=2, OriginalName='b', MissingEvidence='Caller unknown')
        for entries in ([dict(entry, OriginalName='stale')], [entry, entry], [dict(entry, Sequence=9)], [dict(entry, MissingEvidence='')]):
            self.review['UnresolvedScopeEvidence'] = dict(Parameters=entries, Locals=[])
            with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias')

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

    def test_historical_proposal_correction_preserves_checked_scopes(self):
        self.review.update(NewName='GetFeatureCount', ParameterNames=[], LocalNames=[],
                           PreviousLedgerAlias='HistoricalAlias', ExpectedMappedAlias='HistoricalAlias2')
        change = dict(Kind='Method', Module=self.old['Module'], Token=self.old['Token'],
                      Before='HistoricalAlias2', Requested='GetFeatureCount', Applied='GetFeatureCount')
        checked = {('ParameterNames', 1): dict(ExpectedName='a', NewName='count'),
                   ('LocalNames', 0): dict(ExpectedType='System.Int32', NewName='total')}
        corrected = replace_method_alias(self.old, self.review, 'HistoricalAlias2', change, checked)
        self.assertEqual(self.old['ParameterNames'], corrected['ParameterNames'])
        self.assertEqual(self.old['LocalNames'], corrected['LocalNames'])
        self.assertEqual('HistoricalAlias', corrected['LedgerAliasCorrections'][0]['PreviousLedgerAlias'])
        self.assertEqual('HistoricalAlias2', corrected['LedgerAliasCorrections'][0]['PreviousMappedAlias'])
        self.assertNotIn('PreviousLedgerAlias', corrected)
        self.assertNotIn('ExpectedMappedAlias', corrected)
        for key in ('PreviousLedgerAlias', 'ExpectedMappedAlias'):
            for value in (None, 'stale'):
                bad = dict(self.review, **{key:value})
                with self.assertRaises(ValueError):
                    replace_method_alias(self.old, bad, 'HistoricalAlias2', change, checked)
        with self.assertRaises(ValueError):
            replace_method_alias(self.old, self.review, 'HistoricalAlias2', dict(change, Before='HistoricalAlias'), checked)
        with self.assertRaises(ValueError):
            replace_method_alias(self.old, self.review, 'HistoricalAlias', dict(change, Before='HistoricalAlias'), checked)
        with self.assertRaises(ValueError):
            replace_method_alias(self.old, self.review, 'HistoricalAlias2', change, {})

    def test_scope_correction_requires_exact_native_before_and_after(self):
        self.review['ParameterNames'][0]['NewName'] = 'textParameterRefId'
        replacements = {('ParameterNames', 1): dict(Before='count', Requested='textParameterRefId', Applied='textParameterRefId')}
        merged = merge_scopes(self.old, self.review, 'CurrentAcceptedAlias', replacements=replacements)
        self.assertEqual('textParameterRefId', merged['ParameterNames'][0]['NewName'])
        replacements[('ParameterNames', 1)]['Before'] = 'otherPreviousAlias'
        with self.assertRaises(ValueError): merge_scopes(self.old, self.review, 'CurrentAcceptedAlias', replacements=replacements)

    def test_method_correction_preserves_checked_scopes_and_annotations(self):
        self.old['Annotation'] = {'kept': True}
        self.review.update(NewName='CopyBufferPrefix', ParameterNames=[], LocalNames=[])
        change = dict(Kind='Method', Module='a.dll', Token='0x06000001', Before='HistoricalAlias',
                      Requested='CopyBufferPrefix', Applied='CopyBufferPrefix')
        checked = {('ParameterNames', 1): dict(ExpectedName='a', NewName='count'),
                   ('LocalNames', 0): dict(ExpectedType='System.Int32', NewName='total')}
        corrected = replace_method_alias(self.old, self.review, 'HistoricalAlias', change, checked)
        self.assertEqual('CopyBufferPrefix', corrected['NewName'])
        self.assertEqual(self.old['ParameterNames'], corrected['ParameterNames'])
        self.assertEqual(self.old['LocalNames'], corrected['LocalNames'])
        self.assertEqual(self.old['Annotation'], corrected['Annotation'])
        self.assertEqual('HistoricalAlias', self.old['NewName'])
        for column, value in (('Before', 'stale'), ('Applied', 'CopyBufferPrefix2'), ('Token', '0x06000002'),
                              ('Module', 'other/a.dll'), ('Kind', 'Field')):
            bad = dict(change, **{column: value})
            with self.assertRaises(ValueError): replace_method_alias(self.old, self.review, 'HistoricalAlias', bad, checked)
        with self.assertRaises(ValueError): replace_method_alias(self.old, self.review, 'HistoricalAlias', change, {})

    def test_method_correction_accepts_new_scopes_only_with_native_checks(self):
        self.review['NewName'] = 'CopyBufferPrefix'
        change = dict(Kind='Method', Module='a.dll', Token='0x06000001', Before='HistoricalAlias',
                      Requested='CopyBufferPrefix', Applied='CopyBufferPrefix')
        checked = {('ParameterNames', 1): dict(ExpectedName='a', NewName='count'),
                   ('ParameterNames', 2): dict(ExpectedName='b', NewName='limit'),
                   ('LocalNames', 0): dict(ExpectedType='System.Int32', NewName='total')}
        corrected = replace_method_alias(self.old, self.review, 'HistoricalAlias', change, checked)
        self.assertEqual(['count', 'limit'], [p['NewName'] for p in corrected['ParameterNames']])
        self.assertEqual('total', corrected['LocalNames'][0]['NewName'])
        checked[('ParameterNames', 2)]['NewName'] = 'unchecked'
        with self.assertRaises(ValueError): replace_method_alias(self.old, self.review, 'HistoricalAlias', change, checked)
        self.review['ParameterNames'].append(copy.deepcopy(self.review['ParameterNames'][0]))
        with self.assertRaises(ValueError): replace_method_alias(self.old, self.review, 'HistoricalAlias', change, checked)

    def test_alias_withdrawal_keeps_history_but_does_not_replay_request(self):
        self.old['ParameterNames'] = []
        self.old['LocalNames'] = []
        self.old['Annotation'] = {'kept': True}
        reviewed = copy.deepcopy(self.old)
        reviewed.update(RemoveExistingAlias=True, ExpectedAlias='HistoricalAlias', NewName='', Unresolved=True,
                        Reason='Behavior contradicts the alias', UnresolvedReason='Caller role lacks evidence')
        change = dict(Action='RemoveAlias', Kind='Method', Module='a.dll', Token='0x06000001',
                      Before='HistoricalAlias', Requested='', Applied='')
        withdrawn = remove_method_alias(self.old, reviewed, 'HistoricalAlias', change, '')
        self.assertTrue(withdrawn['Unresolved'])
        self.assertEqual('', withdrawn['NewName'])
        self.assertEqual({'kept': True}, withdrawn['Annotation'])
        self.assertEqual('HistoricalAlias', withdrawn['AliasWithdrawals'][0]['Alias'])
        self.assertNotIn('RemoveExistingAlias', withdrawn)
        self.assertNotIn('ExpectedAlias', withdrawn)
        self.assertEqual('HistoricalAlias', self.old['NewName'])
        fresh = remove_method_alias(None, reviewed, 'HistoricalAlias', change, '')
        self.assertNotIn('RemoveExistingAlias', fresh)
        for key, value in (('Action', None), ('Before', 'stale'), ('Applied', 'invented'), ('Kind', 'Field'),
                           ('Module', 'CV/a.dll'), ('Token', '0x06000002')):
            with self.assertRaises(ValueError): remove_method_alias(self.old, reviewed, 'HistoricalAlias', dict(change, **{key: value}), '')
        with self.assertRaises(ValueError): remove_method_alias(self.old, reviewed, 'HistoricalAlias', change, 'HistoricalAlias')
        reviewed['Sha256'] = 'stale'
        with self.assertRaises(ValueError): remove_method_alias(self.old, reviewed, 'HistoricalAlias', change, '')

    def test_alias_withdrawal_rejects_scope_loss_or_missing_evidence(self):
        reviewed = copy.deepcopy(self.old)
        reviewed.update(RemoveExistingAlias=True, ExpectedAlias='HistoricalAlias', NewName='', Unresolved=True,
                        Reason='Behavior contradicts the alias', UnresolvedReason='Caller role lacks evidence')
        change = dict(Action='RemoveAlias', Kind='Method', Module='a.dll', Token='0x06000001',
                      Before='HistoricalAlias', Requested='', Applied='')
        with self.assertRaises(ValueError): remove_method_alias(self.old, reviewed, 'HistoricalAlias', change, '')
        self.old.update(ParameterNames=[], LocalNames=[])
        reviewed.update(ParameterNames=[], LocalNames=[], UnresolvedReason='')
        with self.assertRaises(ValueError): remove_method_alias(self.old, reviewed, 'HistoricalAlias', change, '')


if __name__ == '__main__': unittest.main()
