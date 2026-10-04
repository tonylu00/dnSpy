import copy
import json
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from framework_contract_preservation import attach_framework_proofs, digest, load_framework_contract_evidence, preserve_framework_contract_method

class FrameworkProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name); self.root = self.folder/'input'; self.root.mkdir()
        self.binary = self.root/'Library.dll'; self.binary.write_bytes(b'physical-source')
        self.reference = self.folder/'core.dll'; self.reference.write_bytes(b'pinned-reference')
        self.map = self.folder/'map.xml'
        ET.ElementTree(ET.Element('SourceNameMap', InputDirectory=str(self.root))).write(self.map)
        self.manifest = self.folder/'manifest.json'; self.seed_path = self.folder/'seeds.json'; self.proof_path = self.folder/'proof.json'
        self.binding = dict(Path=str(self.reference), Identity='mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089', Mvid='00000000-0000-0000-0000-000000000002', Sha256=digest(self.reference))
        self.manifest.write_text(json.dumps(dict(Format=1, Assemblies=[self.binding])))
        self.definition = dict(Module='Library.dll', Identity='Library, Version=1.0.0.0', Mvid='00000000-0000-0000-0000-000000000001', Sha256=digest(self.binary), Type='Example.Machine', Token='0x06000001', Signature='System.Void Example.Machine::a()', OriginalName='a')
        self.seeds = dict(Format=1, TargetRoot=str(self.root), ContractReferenceSha256=digest(self.manifest), Methods=[self.definition])
        self.seed_path.write_text(json.dumps(self.seeds))
        self.declaration = dict(RawToken='0x0A000001', RawSignature='System.Void System.IDisposable::Dispose()', RawAssemblyIdentity=self.binding['Identity'], Interface='System.IDisposable', Reference=self.binding, TypeToken='0x02000001', Type='System.IDisposable', MethodToken='0x06000010', Signature='System.Void System.IDisposable::Dispose()', OriginalName='Dispose', InstantiatedSignature='System.Void ()', BodySignatureValidated=True)
        self.proven = dict(Definition=self.definition, Status='ProtectedExplicitFrameworkContract', Blocker=None, Declaration=self.declaration)
        self.proof = dict(Format=1, Kind='PhysicalFrameworkContractEvidence', TargetRoot=str(self.root), Seeds=str(self.seed_path), SeedsSha256=digest(self.seed_path), ContractReferences=str(self.manifest), ContractReferenceSha256=digest(self.manifest), Inputs=[dict(Path=str(self.binary), **{k:self.definition[k] for k in ('Identity','Mvid','Sha256')})], References=[self.binding], Definitions=[self.proven])
        self.row = dict(self.definition, ReviewDisposition='preserve', NewName='', Unresolved=False, NeedsReadableName=False, Reason='Exact CLR MethodImpl contract', ParameterNames=[], LocalNames=[], PreserveFrameworkContractMethod=True, PreservedExternalFrameworkContract=dict(Declaration=self.declaration, GeneratedSourceMerging='Unproven; separate consolidated source evidence required.'))
    def load(self):
        self.proof_path.write_text(json.dumps(self.proof))
        return load_framework_contract_evidence(self.map, self.proof_path, digest(self.proof_path), digest(self.manifest))
    def test_exact_physical_proof_and_marker_retirement(self):
        evidence = self.load(); result = preserve_framework_contract_method(self.row, None, evidence[('library.dll', 0x06000001)])
        self.assertNotIn('PreserveFrameworkContractMethod', result); self.assertEqual(result['PreservedExternalFrameworkContract'], self.row['PreservedExternalFrameworkContract'])
    def test_stale_source(self):
        self.binary.write_bytes(b'changed')
        with self.assertRaises(AssertionError): self.load()
    def test_stale_reference(self):
        self.reference.write_bytes(b'changed')
        with self.assertRaises(AssertionError): self.load()
    def test_stale_proof(self):
        self.proof_path.write_text(json.dumps(self.proof))
        with self.assertRaises(AssertionError): load_framework_contract_evidence(self.map, self.proof_path, '0'*64, digest(self.manifest))
    def test_duplicate_physical_definition(self):
        self.proof['Definitions'].append(copy.deepcopy(self.proven))
        with self.assertRaises(AssertionError): self.load()
    def test_unresolved_or_unsupported_role(self):
        for change in ({'Status':'UnresolvedFrameworkContract'}, {'Declaration':dict(self.declaration, OriginalName='Invented')}):
            original = copy.deepcopy(self.proof['Definitions']); self.proof['Definitions'][0].update(change)
            with self.assertRaises(AssertionError): self.load()
            self.proof['Definitions'] = original
    def test_seed_signature_conflict(self):
        self.proof['Definitions'][0] = copy.deepcopy(self.proven); self.proof['Definitions'][0]['Definition']['Signature']='Different'
        with self.assertRaises(AssertionError): self.load()
    def test_wrong_reference_binding(self):
        self.proof['Definitions'][0] = copy.deepcopy(self.proven); self.proof['Definitions'][0]['Declaration']['Reference']['Mvid']='Wrong'
        with self.assertRaises(AssertionError): self.load()
    def test_aliases_mapped_definition_and_merge_claim_rejected(self):
        for change, mapped in [({'NewName':'Dispose'},None), ({'ParameterNames':[{'Sequence':1,'NewName':'state'}]},None), ({},ET.Element('Method')), ({'PreservedExternalFrameworkContract':dict(Declaration=self.declaration, GeneratedSourceMerging='Merged')},None)]:
            with self.assertRaises(AssertionError): preserve_framework_contract_method(dict(self.row, **change), mapped, self.proven)
    def test_twin_identity_requires_its_own_physical_input(self):
        twin=self.root/'compatibility'; twin.mkdir(); (twin/'Library.dll').write_bytes(self.binary.read_bytes())
        seed=dict(self.definition, Module='compatibility/Library.dll'); self.seeds['Methods'].append(seed);self.seed_path.write_text(json.dumps(self.seeds));self.proof['SeedsSha256']=digest(self.seed_path)
        self.proof['Definitions'].append(dict(self.proven, Definition=seed))
        with self.assertRaises(KeyError): self.load()
        self.proof['Inputs'].append(dict(self.proof['Inputs'][0], Path=str(twin/'Library.dll')))
        self.assertEqual(len(self.load()),2)
    def test_preparation_retains_scopes_and_exact_provenance(self):
        proofs=self.load(); row=copy.deepcopy(self.row); row.pop('PreserveFrameworkContractMethod'); row.pop('PreservedExternalFrameworkContract')
        row['ParameterNames']=[dict(Sequence=1, OriginalName='a', NewName='')]
        review=dict(Format=1, Types=[], Fields=[], Methods=[row]); binding=dict(Cli=str(self.reference), CliSha256=digest(self.reference), Sha256=digest(self.proof_path))
        result=attach_framework_proofs(review,binding,proofs)
        self.assertEqual(result['Methods'][0]['ParameterNames'],row['ParameterNames']);self.assertNotIn('PreserveFrameworkContractMethod',row)
        self.assertTrue(result['Methods'][0]['PreserveFrameworkContractMethod']);self.assertEqual(result['Methods'][0]['PreservedExternalFrameworkContract']['Declaration'],self.declaration)
    def test_preparation_rejects_stale_tool_or_incomplete_review(self):
        proofs=self.load(); review=dict(Format=1, Types=[], Fields=[], Methods=[self.row]); binding=dict(Cli=str(self.reference), CliSha256='0'*64, Sha256=digest(self.proof_path))
        with self.assertRaises(AssertionError):attach_framework_proofs(review,binding,proofs)
        binding['CliSha256']=digest(self.reference)
        with self.assertRaises(AssertionError):attach_framework_proofs(dict(review,Methods=[]),binding,proofs)

if __name__ == '__main__': unittest.main()
