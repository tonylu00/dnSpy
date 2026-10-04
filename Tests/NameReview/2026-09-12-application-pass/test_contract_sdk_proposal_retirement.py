import copy,json,pathlib,tempfile,unittest,sys
from contract_sdk_proposal_retirement import load_contract_sdk_evidence,retire_contract_sdk_proposal,preserve_contract_sdk_method
from sdk_proposal_retirement import digest,key
from review_ledger import proposal_preimage
FIXTURE=pathlib.Path(sys.argv.pop(1)) if len(sys.argv)>1 else None
class ContractSdkTests(unittest.TestCase):
 def setUp(self):
  self.report=json.loads((FIXTURE/'evidence.json').read_text());self.map=FIXTURE/'map.xml';self.ref=self.report['ContractReferenceSha256'];self.sdk=self.report['SdkNameWhitelistSha256']
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.file=pathlib.Path(self.temp.name)/'proof.json'
  self.save();self.proofs=self.load();self.proof=next(iter(self.proofs.values()))
  self.old=dict(self.proof['Family']['Definition'],NewName='ReadValue',Reason='Prior proposal',Unresolved=False,NeedsReadableName=True,ContractFamily=self.proof['Family']['Family'],Annotation={'keep':True},ParameterNames=[dict(Sequence=1,OriginalName='p',HasMetadata=True,NewName='value')],LocalNames=[dict(Index=0,ExpectedType='System.Int32',NewName='result')])
  self.review=dict(self.old,NewName='',UnresolvedReason='',NeedsReadableName=False,Reason='Exact SDK interface family requires original runtime member name',ReviewDisposition='preserve',RetireRejectedContractSdkProposal=True,PreviousProposalEvidence=proposal_preimage(self.old),ParameterNames=[dict(self.old['ParameterNames'][0],NewName='')],LocalNames=[dict(self.old['LocalNames'][0],NewName='')])
 def save(self):self.file.write_text(json.dumps(self.report))
 def load(self):return load_contract_sdk_evidence(self.map,self.file,digest(self.file),self.ref)
 def retire(self,**kw):return retire_contract_sdk_proposal(kw.get('old',self.old),kw.get('review',self.review),kw.get('mapped'),kw.get('proof',self.proof),self.sdk,self.ref)
 def test_native_protected_implementation_and_identical_physical_twin(self):
  self.assertEqual(1,len(self.proofs));self.assertIn(key('Library.dll','0x06000002'),self.proofs);self.assertNotIn(key('compatibility/Library.dll','0x06000002'),self.proofs)
 def test_preserves_history_and_original_scopes_without_mutation(self):
  old=copy.deepcopy(self.old);review=copy.deepcopy(self.review);result=self.retire();self.assertEqual(old,self.old);self.assertEqual(review,self.review)
  self.assertEqual('',result['NewName']);self.assertEqual('preserve',result['ReviewDisposition']);self.assertEqual(old['Annotation'],result['Annotation']);self.assertEqual(proposal_preimage(old),result['RejectedSdkContractProposals'][0]['PreviousProposal']);self.assertEqual(self.proof,result['SdkContractProtection']);self.assertNotIn('PreviousProposalEvidence',result);self.assertEqual('',result['ParameterNames'][0]['NewName'])
 def test_new_preservation_requires_native_proof_and_no_proposal_or_alias(self):
  row=copy.deepcopy(self.review);row.pop('RetireRejectedContractSdkProposal');row.pop('PreviousProposalEvidence');row['PreserveSdkContractMethod']=True
  result=preserve_contract_sdk_method(row,None,self.proof,self.sdk,self.ref);self.assertNotIn('PreserveSdkContractMethod',result);self.assertEqual(self.proof,result['SdkContractProtection'])
  for field,value in [('Module','compatibility/Library.dll'),('NewName','ReadValue'),('NeedsReadableName',True),('Reason',''),('PreserveSdkContractMethod',False),('PreviousProposalEvidence',{'old':'alias'}),('ContractFamily','wrong')]:
   with self.subTest(field=field),self.assertRaises(ValueError):preserve_contract_sdk_method(dict(row,**{field:value}),None,self.proof,self.sdk,self.ref)
  for mapped in ({},{'NewName':'existing'}):
   with self.assertRaises(ValueError):preserve_contract_sdk_method(row,mapped,self.proof,self.sdk,self.ref)
  with self.assertRaises(ValueError):preserve_contract_sdk_method(row,None,None,self.sdk,self.ref)
 def test_rejects_applied_or_scoped_only_maps(self):
  for mapped in ({},{'NewName':'ReadValue'},{'Parameter':{'NewName':'value'}}):
   with self.subTest(mapped=mapped),self.assertRaises(ValueError):self.retire(mapped=mapped)
 def test_requires_exact_prior_identity_and_decision(self):
  for field,value in [('Module','compatibility/Library.dll'),('Signature','wrong'),('Mvid','wrong'),('PreviousProposalEvidence',{}),('NewName','Other'),('NeedsReadableName',True),('Unresolved',True),('Reason',''),('RetireRejectedContractSdkProposal',False)]:
   with self.subTest(field=field),self.assertRaises(ValueError):self.retire(review=dict(self.review,**{field:value}))
 def test_requires_complete_current_family(self):
  for field,value in [('WhitelistSha256','wrong'),('ContractReferenceSha256','wrong')]:
   bad=copy.deepcopy(self.proof);bad[field]=value
   with self.assertRaises(ValueError):self.retire(proof=bad)
  for field,value in [('Status','UnresolvedOrExternalContract'),('Blockers',['external']),('ProtectedMembers',[]),('Family','wrong')]:
   bad=copy.deepcopy(self.proof);bad['Family'][field]=value
   with self.assertRaises(ValueError):self.retire(proof=bad)
 def test_scope_inventory_cannot_change(self):
  for label in ('ParameterNames','LocalNames'):
   for entries in ([],self.review[label]*2,[dict(self.review[label][0],NewName='alias')],self.review[label]+[dict(self.review[label][0],**({'Sequence':2} if label=='ParameterNames' else {'Index':1}))]):
    with self.subTest(label=label),self.assertRaises(ValueError):self.retire(review=dict(self.review,**{label:entries}))
 def test_evidence_hash_and_bindings(self):
  with self.assertRaises(ValueError):load_contract_sdk_evidence(self.map,self.file,'wrong',self.ref)
  for field,value in [('Format',2),('MapSha256','wrong'),('SeedsSha256','wrong'),('SdkNameWhitelistSha256','wrong'),('ContractReferenceSha256','wrong')]:
   original=self.report[field];self.report[field]=value;self.save()
   with self.subTest(field=field),self.assertRaises(ValueError):self.load()
   self.report[field]=original
 def test_physical_scope_duplicate_escape_and_stale_hash(self):
  before=copy.deepcopy(self.report['Scope'])
  for scope in (before*2,[dict(before[0],Module='../outside.dll')], [dict(before[0],Sha256='wrong')]+before[1:]):
   self.report['Scope']=scope;self.save()
   with self.assertRaises(ValueError):self.load()
  self.report['Scope']=before
 def test_every_seed_must_be_accounted_once(self):
  rows=copy.deepcopy(self.report['Definitions'])
  for defs in (rows[:-1],rows+rows[:1]):
   self.report['Definitions']=defs;self.save()
   with self.assertRaises(ValueError):self.load()
 def test_family_membership_and_sdk_member_exactness(self):
  original=copy.deepcopy(self.report)
  for field,value in [('Family','wrong'),('Blockers',['external']),('ProtectedMembers',[]),('Members',[])]:
   self.report=copy.deepcopy(original);self.report['Definitions'][0][field]=value;self.save()
   with self.subTest(field=field),self.assertRaises(ValueError):self.load()
  self.report=copy.deepcopy(original);self.report['Definitions'][0]['ProtectedMembers'][0]['SdkSymbol']['Name']='wrong';self.save()
  with self.assertRaises(ValueError):self.load()
if __name__=='__main__':
 if FIXTURE is None:raise SystemExit('Pass fresh native tests/SdkContractInspection fixture directory')
 unittest.main()
