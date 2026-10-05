import copy
import unittest
from checkpoint_scoped_contract_resolution import resolve_unresolved


class ScopedContractResolutionTests(unittest.TestCase):
    def fixture(self):
        from test_review_ledger import LedgerScopeMergeTests
        old, review, change, proof = LedgerScopeMergeTests().contract_resolution_fixture()
        old.update(DefinitionOnlyUnresolved=True, ContractFamily=review['ContractFamily'])
        old['ParameterNames']=[dict(Sequence=1, OriginalName='a', HasMetadata=True, NewName='policy')]
        old['LocalNames']=[dict(Index=0, ExpectedType='System.Int32', NewName='count'),
                           dict(Index=1, ExpectedType='System.Int16', NewName='')]
        old['UnresolvedScopeEvidence']={'Locals':[dict(Index=1, ExpectedType='System.Int16', MissingEvidence='Residual slot')]} 
        for key in ('ParameterNames','LocalNames','UnresolvedScopeEvidence'):
            review[key]=copy.deepcopy(old[key])
        checked={('ParameterNames',1):dict(NewName='policy',ExpectedName='a'),
                 ('LocalNames',0):dict(NewName='count',ExpectedType='System.Int32')}
        return old,review,change,checked,proof

    def test_preserves_scopes_history_and_unknowns(self):
        old,r,c,s,f=self.fixture();before=copy.deepcopy(old)
        result=resolve_unresolved(old,r,'',c,r['NewName'],s,f)
        for key in ('ParameterNames','LocalNames','UnresolvedScopeEvidence','Annotation'):
            self.assertEqual(old[key],result[key])
        self.assertEqual(before,old)
        self.assertFalse(result['Unresolved']);self.assertFalse(result['DefinitionOnlyUnresolved'])
        self.assertEqual(old['MappingBlocker'],result['ContractFamilyReviews'][-1]['PreviousMappingBlocker'])
        self.assertNotIn('ResolveExistingUnresolved',result)
        with self.assertRaises(ValueError):resolve_unresolved(result,r,'',c,r['NewName'],s,f)

    def test_rejects_stale_identity_evidence_and_changed_scopes(self):
        old,r,c,s,f=self.fixture()
        for key,value in [('Mvid','other'),('Sha256','stale'),('Signature','wrong'),('ContractFamily','other'),
                          ('MappingBlocker','external'),('ScopedMappingBlocker','SDK'),('Unresolved',True),
                          ('DefinitionOnlyUnresolved',True),('PreviousUnresolvedEvidence',{}),
                          ('ResolveExistingUnresolved',False),('Reason',''),('ParameterNames',[]),
                          ('LocalNames',[]),('UnresolvedScopeEvidence',{})]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                resolve_unresolved(old,dict(r,**{key:value}),'',c,r['NewName'],s,f)
        for label in ('ParameterNames','LocalNames'):
            bad=copy.deepcopy(r);bad[label][0]['NewName']='different'
            with self.assertRaises(ValueError):resolve_unresolved(old,bad,'',c,r['NewName'],s,f)
            bad=copy.deepcopy(r);bad[label].append(copy.deepcopy(bad[label][0]))
            with self.assertRaises(ValueError):resolve_unresolved(old,bad,'',c,r['NewName'],s,f)
        with self.assertRaises(ValueError):resolve_unresolved(dict(old,DefinitionOnlyUnresolved=False),r,'',c,r['NewName'],s,f)

    def test_requires_checked_scopes_and_atomic_family_proof(self):
        old,r,c,s,f=self.fixture()
        for checked in ({},{('ParameterNames',1):s[('ParameterNames',1)]}):
            with self.assertRaises(ValueError):resolve_unresolved(old,r,'',c,r['NewName'],checked,f)
        bad=copy.deepcopy(s);bad[('LocalNames',0)]['ExpectedType']='System.String'
        with self.assertRaises(ValueError):resolve_unresolved(old,r,'',c,r['NewName'],bad,f)
        for group in ('ReviewedMembers','Changes','FinalRows'):
            bad=copy.deepcopy(f);bad[group]=bad[group][:1]
            with self.assertRaises(ValueError):resolve_unresolved(old,r,'',c,r['NewName'],s,bad)
        for group,key,value in [('ReviewedMembers','MappingBlocker','external'),('FinalRows','Mvid','twin'),
                                ('Changes','Applied','inventedSuffix2')]:
            bad=copy.deepcopy(f);bad[group][1][key]=value
            with self.assertRaises(ValueError):resolve_unresolved(old,r,'',c,r['NewName'],s,bad)
        for key,value in [('Before','previous'),('Kind','Method'),('Applied','suffix2'),('Token','0x06000002')]:
            with self.assertRaises(ValueError):resolve_unresolved(old,r,'',dict(c,**{key:value}),r['NewName'],s,f)
        with self.assertRaises(ValueError):resolve_unresolved(old,r,'existing',c,r['NewName'],s,f)
        with self.assertRaises(ValueError):resolve_unresolved(old,r,'',c,'unchecked',s,f)

    def test_unscoped_resolution_keeps_existing_path(self):
        from test_review_ledger import LedgerScopeMergeTests
        old,r,c=LedgerScopeMergeTests().resolution_fixture('Field','0x04000001')
        self.assertEqual(r['NewName'],resolve_unresolved(old,r,'',c,r['NewName'])['NewName'])


if __name__=='__main__':unittest.main()
