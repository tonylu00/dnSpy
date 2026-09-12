"""Bind .NET cross-version body matches to visible source and existing reviews.

Usage: stage_correspondence.py REF_DB TARGET_DB CANDIDATES BASE_MAP NEW_REVIEW
No source application, binary execution or version-wide equivalence is claimed.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ApplicationNameGraph'))
from review_candidates import source_review_reasons

def stage(reference_db,target_db,candidates,base_map,output):
    reference_db,target_db,candidates,base_map,output=map(Path,(reference_db,target_db,candidates,base_map,output))
    assert not output.exists(), 'Choose a fresh review output'
    proposals=json.loads(candidates.read_text(encoding='utf-8-sig'))
    base=ET.parse(base_map).getroot()
    ref_map_path=Path(proposals['ReferenceSourceMap'])
    ref_map_bytes=ref_map_path.read_bytes()
    assert hashlib.sha256(ref_map_bytes).hexdigest().upper()==proposals['ReferenceSourceMapHash'].upper(), 'Reference map changed'
    ref_map=ET.fromstring(ref_map_bytes)
    ref_root,target_root=Path(proposals['ReferenceRoot']).resolve(),Path(proposals['TargetRoot']).resolve()
    assert Path(base.attrib['InputDirectory']).resolve()==target_root
    assert Path(ref_map.attrib['InputDirectory']).resolve()==ref_root
    token=lambda text: f'0x{int(text,16):08X}'
    def mapped_methods(document):
        result={}
        for module in document.findall('Module'):
            for method in module.findall('Method'):
                key=(Path(module.attrib['Path']).as_posix(),token(method.attrib['Token']))
                assert key not in result, ('Duplicate physical map method',key)
                result[key]=method
        return result
    old_aliases,new_aliases=mapped_methods(ref_map),mapped_methods(base)
    with closing(sqlite3.connect(reference_db.resolve().as_uri()+'?mode=ro',uri=True)) as reference, closing(sqlite3.connect(target_db.resolve().as_uri()+'?mode=ro',uri=True)) as target:
        def context(db):
            manifest=json.loads(db.execute('SELECT data FROM meta').fetchone()[0])
            return {Path(m['Input']).resolve():m for m in manifest['Modules']},Path(manifest['Export']).resolve().parent
        old_modules,old_source=context(reference); new_modules,new_source=context(target)
        accepted=[]; proofs=[]; source_proofs=[]; exclusions=[]; hashes={}; seen=set()
        def symbol(db,module,method_token):
            key=module['Id']+':'+method_token
            row=db.execute('SELECT data FROM symbols WHERE id=?',(key,)).fetchone()
            assert row, ('No graph symbol',key)
            return key,json.loads(row[0])
        def declarations(db,key,root):
            rows=[json.loads(row[0]) for row in db.execute('SELECT data FROM source WHERE id=?',(key,))]
            for row in rows:
                path=(root/row['Source']).resolve()
                assert path.is_relative_to(root), 'Source path leaves graph root'
                if path not in hashes: hashes[path]=hashlib.sha256(path.read_bytes()).hexdigest().upper()
                assert hashes[path]==row['Sha256'].upper(), ('Stale source',path)
            return rows
        for proposal in proposals['Candidates']:
            relative=Path(proposal['Module']).as_posix()
            old_token,new_token=token(proposal['ReferenceToken']),token(proposal['TargetToken'])
            key=(relative,new_token)
            assert key not in seen, ('Duplicate target candidate',key)
            seen.add(key)
            old_path,new_path=(ref_root/relative).resolve(),(target_root/relative).resolve()
            assert old_path.is_relative_to(ref_root) and new_path.is_relative_to(target_root), 'Candidate leaves physical root'
            old_module,new_module=old_modules.get(old_path),new_modules.get(new_path)
            if old_module is None or new_module is None:
                exclusions.append({'Module':relative,'Token':new_token,'Reason':'Source graph missing at one physical path'});continue
            for module,version in [(old_module,'Reference'),(new_module,'Target')]:
                assert module['Mvid']==proposal[version+'Mvid'] and module['Sha256'].upper()==proposal[version+'Hash'].upper(), ('Physical input changed',relative,version)
            old_id,old_symbol=symbol(reference,old_module,old_token)
            new_id,new_symbol=symbol(target,new_module,new_token)
            assert old_symbol['Kind']==new_symbol['Kind']=='Method'
            assert old_symbol['Signature']==proposal['Reference'] and new_symbol['Signature']==proposal['Target'], ('Method signature mismatch',key)
            source_name=proposal['SuggestedName']
            reference_alias=old_aliases.get((relative,old_token))
            if reference_alias is not None:
                assert reference_alias.attrib['ExpectedName']==old_symbol['OriginalName'] and reference_alias.attrib['Signature']==old_symbol['Signature']
            assert source_name==(reference_alias.attrib.get('NewName') if reference_alias is not None and reference_alias.attrib.get('NewName') else old_symbol['OriginalName']), ('Reference name mismatch',key)
            old_rows=declarations(reference,old_id,old_source); new_rows=declarations(target,new_id,new_source)
            if not old_rows or not new_rows:
                exclusions.append({'Id':new_id,'Reason':'No visible declaration in one source version'});continue
            if not all(source_review_reasons(new_symbol,row) for row in new_rows):
                exclusions.append({'Id':new_id,'Reason':'Existing target source name is readable'});continue
            existing=new_aliases.get(key)
            if existing is not None and existing.attrib.get('NewName') and not source_review_reasons(dict(new_symbol,Alias=existing.attrib['NewName']),{'Kind':'MethodDeclaration','Name':existing.attrib['NewName']}):
                exclusions.append({'Id':new_id,'Reason':'Existing staged target alias preserved','Alias':existing.attrib['NewName']});continue
            if new_symbol.get('Blocker') or new_symbol.get('Family'):
                exclusions.append({'Id':new_id,'Reason':'Contract needs complete separate review','Blocker':new_symbol.get('Blocker')});continue
            parameters=[]; parameter_exclusions=[]
            for parameter in [] if reference_alias is None else reference_alias.findall('Parameter'):
                sequence=int(parameter.attrib['Sequence'])
                old=next((p for p in old_symbol['Parameters'] if p['Sequence']==sequence),None)
                new=next((p for p in new_symbol['Parameters'] if p['Sequence']==sequence),None)
                assert old and old['OriginalName']==parameter.attrib['ExpectedName'], ('Reference parameter changed',key,sequence)
                if not new or not new['HasMetadata'] or old['Type']!=new['Type']:
                    parameter_exclusions.append({'Sequence':sequence,'Reason':'Exact target parameter type/metadata binding unavailable'});continue
                parameters.append({'Sequence':sequence,'OriginalName':new['OriginalName'],'HasMetadata':True,'NewName':parameter.attrib['NewName']})
            accepted.append({'Module':relative,'Identity':proposal['TargetIdentity'],'Mvid':new_module['Mvid'],'Sha256':new_module['Sha256'],
                             'Token':new_token,'Signature':new_symbol['Signature'],'OriginalName':new_symbol['OriginalName'],
                             'NewName':source_name,'MappingBlocker':None,'ContractFamily':None,'ParameterNames':parameters})
            proofs.append(dict(proposal,ReferenceId=old_id,TargetId=new_id,ParameterExclusions=parameter_exclusions))
            source_proofs.append({'Id':new_id,'ReferenceId':old_id,
                                  'Declarations':[{k:r[k] for k in ('Source','Name','Line','Sha256')} for r in new_rows],
                                  'ReferenceDeclarations':[{k:r[k] for k in ('Source','Name','Line','Sha256')} for r in old_rows],
                                  'Status':'staged from unique IL/call correspondence; source/local application pending'})
        result={'Format':1,'Kind':'SymbolReview','TargetRoot':str(target_root),'Methods':accepted,'Types':[],'Fields':[],
                'CorrespondenceEvidence':proofs,'SourceEvidence':source_proofs,'SourceExclusions':exclusions,
                'ProposalSha256':hashlib.sha256(candidates.read_bytes()).hexdigest(),'BaseMapSha256':hashlib.sha256(base_map.read_bytes()).hexdigest(),
                'ReferenceMap':str(ref_map_path),'ReferenceMapSha256':proposals['ReferenceSourceMapHash'],
                'ApplicationStatus':'staged; application-wide review, local binding and consolidated verification remain incomplete'}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(f'Staged {len(accepted)} source-visible method correspondences; {len(exclusions)} preserved/excluded cases. No source or binary changes.')

if __name__=='__main__': stage(*sys.argv[1:])
