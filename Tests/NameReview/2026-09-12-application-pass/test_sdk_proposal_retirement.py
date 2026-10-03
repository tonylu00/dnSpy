import copy
import pathlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from sdk_proposal_retirement import digest, key, load_sdk_symbols, retire_sdk_proposal
from review_ledger import proposal_preimage


class SdkProposalRetirementTests(unittest.TestCase):
    def setUp(self):
        self.old=dict(Module='a.dll', Token='0x06000001', Identity='assembly', Mvid='mvid', Sha256='sha',
                      Type='Owner', Signature='signature', OriginalName='a', NewName='ReadData', Unresolved=False,
                      Reason='Old proposal', UnresolvedReason='', NeedsReadableName=True, Annotation={'kept':True},
                      ParameterNames=[dict(Sequence=1, OriginalName='p', HasMetadata=True, NewName='buffer')],
                      LocalNames=[dict(Index=0, ExpectedType='System.Int32', NewName='count')])
        self.review=dict(self.old, NewName='', Reason='SDK public method identity is required', ReviewDisposition='preserve',
                         NeedsReadableName=False, RetireRejectedSdkProposal=True, PreviousProposalEvidence=proposal_preimage(self.old),
                         ParameterNames=[dict(self.old['ParameterNames'][0], NewName='')],
                         LocalNames=[dict(self.old['LocalNames'][0], NewName='')])
        self.proof=dict(WhitelistSha256='manifest-sha', Module=dict(Path='a.dll', Identity='assembly', Mvid='mvid', Sha256='sha'),
                        Symbol=dict(Token='06000001', Kind='Method', Name='a', Signature='signature', Reason='sdk-public-method'))

    def test_retirement_preserves_annotations_scope_inventory_and_rejection_history(self):
        r=retire_sdk_proposal(self.old,self.review,None,self.proof,'manifest-sha')
        self.assertEqual('',r['NewName']);self.assertEqual('preserve',r['ReviewDisposition'])
        self.assertEqual(self.old['Annotation'],r['Annotation'])
        self.assertEqual(proposal_preimage(self.old),r['RejectedSdkProposals'][0]['PreviousProposal'])
        self.assertEqual(self.proof,r['SdkProtection'])
        self.assertEqual('p',r['ParameterNames'][0]['OriginalName']);self.assertEqual('',r['ParameterNames'][0]['NewName'])
        self.assertEqual('System.Int32',r['LocalNames'][0]['ExpectedType']);self.assertEqual('',r['LocalNames'][0]['NewName'])
        self.assertEqual('ReadData',self.old['NewName']);self.assertEqual('buffer',self.old['ParameterNames'][0]['NewName'])
        self.assertNotIn('RetireRejectedSdkProposal',r);self.assertNotIn('PreviousProposalEvidence',r)
        with self.assertRaises(ValueError):retire_sdk_proposal(r,self.review,None,self.proof,'manifest-sha')

    def test_requires_exact_previous_decisions_and_current_preservation(self):
        for k,v in [('Module','CV/a.dll'),('Token','0x06000002'),('Identity','other'),('Mvid','twin'),('Sha256','stale'),
                    ('Type','OtherOwner'),('Signature','other'),('OriginalName','b'),('NewName','OtherAlias'),('Reason',''),
                    ('Unresolved',True),('UnresolvedReason','unknown'),('ReviewDisposition','rename'),
                    ('RetireRejectedSdkProposal',False),('PreviousProposalEvidence',{})]:
            with self.subTest(k=k),self.assertRaises(ValueError):retire_sdk_proposal(self.old,dict(self.review,**{k:v}),None,self.proof,'manifest-sha')
        for k,v in [('NewName',''),('Unresolved',True),('Reason','changed')]:
            with self.subTest(previous=k),self.assertRaises(ValueError):retire_sdk_proposal(dict(self.old,**{k:v}),self.review,None,self.proof,'manifest-sha')
        for binding in [{},{'NewName':''},{'NewName':'ReadData'},{'Parameter':{'NewName':'buffer'}}]:
            with self.assertRaises(ValueError):retire_sdk_proposal(self.old,self.review,binding,self.proof,'manifest-sha')

    def test_rejects_wrong_whitelist_physical_twins_and_symbol_shapes(self):
        with self.assertRaises(ValueError):retire_sdk_proposal(self.old,self.review,None,None,'manifest-sha')
        with self.assertRaises(ValueError):retire_sdk_proposal(self.old,self.review,None,self.proof,'different-manifest')
        for group,k,v in [('Module','Path','compat/a.dll'),('Module','Identity','other'),('Module','Mvid','twin'),
                          ('Module','Sha256','stale'),('Symbol','Token','0x06000002'),('Symbol','Kind','Field'),
                          ('Symbol','Name','b'),('Symbol','Signature','other'),('Symbol','Reason','')]:
            bad=copy.deepcopy(self.proof);bad[group][k]=v
            with self.subTest(group=group,k=k),self.assertRaises(ValueError):retire_sdk_proposal(self.old,self.review,None,bad,'manifest-sha')

    def test_rejects_duplicate_stale_missing_or_named_scopes(self):
        for label,pos,field,badvalue in [('ParameterNames','Sequence','OriginalName','other'),('LocalNames','Index','ExpectedType','System.String')]:
            for entries in [[],[dict(self.review[label][0],**{field:badvalue})],self.review[label]*2,[dict(self.review[label][0],NewName='still-named')]]:
                with self.subTest(label=label),self.assertRaises(ValueError):retire_sdk_proposal(self.old,dict(self.review,**{label:entries}),None,self.proof,'manifest-sha')
        old=copy.deepcopy(self.old);old['ParameterNames']*=2
        review=dict(self.review,PreviousProposalEvidence=proposal_preimage(old))
        with self.assertRaises(ValueError):retire_sdk_proposal(old,review,None,self.proof,'manifest-sha')

    def test_supports_types_and_fields_with_their_exact_tables(self):
        for token,kind in [('0x02000001','Type'),('0x04000001','Field')]:
            old=dict(self.old,Token=token,ParameterNames=[],LocalNames=[])
            review=dict(self.review,Token=token,ParameterNames=[],LocalNames=[],PreviousProposalEvidence=proposal_preimage(old))
            proof=copy.deepcopy(self.proof);proof['Symbol'].update(Token=token,Kind=kind)
            r=retire_sdk_proposal(old,review,None,proof,'manifest-sha');self.assertEqual('',r['NewName'])

    def test_map_bound_loader_verifies_physical_paths_manifest_and_numeric_tokens(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);binary=root/'a.dll';binary.write_bytes(b'physical-original')
            whitelist=root/'sdk.xml';map_path=root/'map.xml'
            wr=ET.Element('SdkNameWhitelist',Version='1');mod=ET.SubElement(wr,'Module',Path='a.dll',Identity='assembly',Mvid='mvid',Sha256=digest(binary))
            sym=ET.SubElement(mod,'Symbol',Token='06000001',Kind='Method',Name='a',Signature='signature',Reason='sdk-public-method')
            def save():
                ET.ElementTree(wr).write(whitelist)
                mr=ET.Element('SourceNames',InputDirectory=str(root),SdkNameWhitelist=str(whitelist),SdkNameWhitelistSha256=digest(whitelist));ET.ElementTree(mr).write(map_path)
            save();proof=load_sdk_symbols(map_path)[key('a.dll','0x06000001')];self.assertEqual(digest(binary),proof['Module']['Sha256'])
            whitelist.write_bytes(whitelist.read_bytes()+b' ')
            with self.assertRaises(ValueError):load_sdk_symbols(map_path)
            save();binary.write_bytes(b'changed')
            with self.assertRaises(ValueError):load_sdk_symbols(map_path)
            binary.write_bytes(b'physical-original')
            for k,v in [('Path','../outside.dll'),('Path',str(binary.resolve())),('Identity',''),('Mvid',''),('Sha256','stale')]:
                before=mod.get(k);mod.set(k,v);save()
                with self.subTest(module=k),self.assertRaises(ValueError):load_sdk_symbols(map_path)
                mod.set(k,before)
            for k,v in [('Kind','Field'),('Token','0x01000001'),('Name',''),('Signature',''),('Reason','')]:
                before=sym.get(k);sym.set(k,v);save()
                with self.subTest(symbol=k),self.assertRaises(ValueError):load_sdk_symbols(map_path)
                sym.set(k,before)
            mod.append(copy.deepcopy(sym));save()
            with self.assertRaises(ValueError):load_sdk_symbols(map_path)
            mod.remove(mod[-1]);wr.append(copy.deepcopy(mod));save()
            with self.assertRaises(ValueError):load_sdk_symbols(map_path)


if __name__=='__main__':unittest.main()
