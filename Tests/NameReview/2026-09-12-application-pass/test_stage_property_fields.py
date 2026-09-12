"""Portable source eligibility and physical identity tests for getter proposals."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from stage_property_fields import stage

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory); source=root/'source'; source.mkdir(); inputs=root/'input'; inputs.mkdir()
    path=source/'Service.cs'; path.write_text('class Service { private int a; private int alreadyReadable; }')
    sha=hashlib.sha256(path.read_bytes()).hexdigest().upper()
    database=root/'graph.sqlite'; db=sqlite3.connect(database)
    db.executescript('CREATE TABLE meta(data TEXT); CREATE TABLE symbols(id TEXT,data TEXT); CREATE TABLE source(id TEXT,data TEXT);')
    manifest={'Export':str(source/'export.xml'),'Modules':[{'Id':'m0000','Input':str(inputs/'Main.dll'),'Mvid':'mvid','Sha256':'hash'}]}
    db.execute('INSERT INTO meta VALUES (?)',(json.dumps(manifest),))
    fields=[]; evidence=[]
    for index,name in [(1,'a'),(2,'alreadyReadable'),(3,'b')]:
        token=f'0x0400000{index}'; symbol_id='m0000:'+token
        symbol={'Kind':'Field','Id':symbol_id,'OriginalName':name,'Signature':'System.Int32 Service::'+name}
        db.execute('INSERT INTO symbols VALUES (?,?)',(symbol_id,json.dumps(symbol)))
        db.execute('INSERT INTO source VALUES (?,?)',(symbol_id,json.dumps({'Source':'Service.cs','Name':name,'Kind':'VariableDeclarator','Line':1,'Sha256':sha})))
        getter='0x0600000'+str(index)
        db.execute('INSERT INTO symbols VALUES (?,?)',('m0000:'+getter,json.dumps({'Signature':'System.Int32 Service::get_Count'+str(index)+'()'})))
        fields.append({'Module':'Main.dll','Token':token,'Mvid':'mvid','Sha256':'hash','OriginalName':name,'Signature':symbol['Signature'],'NewName':'count'+str(index)})
        evidence.append({'Module':'Main.dll','FieldToken':token,'GetterToken':getter,'GetterSignature':'System.Int32 Service::get_Count'+str(index)+'()'})
    db.commit(); db.close()
    proposals=root/'proposals.json'
    proposals.write_text(json.dumps({'Format':1,'Kind':'SymbolReview','TargetRoot':str(inputs),'Methods':[],'Types':[],'Fields':fields,'PropertyEvidence':evidence}))
    manual=root/'manual.json'; manual.write_text(json.dumps({'Decisions':[{'Members':[{'Id':'m0000:0x04000003'}]}]}))
    output=root/'review.json'; stage(database,proposals,output,[manual])
    result=json.loads(output.read_text())
    assert [f['Token'] for f in result['Fields']]==['0x04000001']
    assert {e['Reason'] for e in result['SourceExclusions']}=={'Existing source field name is already readable','Existing manual decision preserved'}
    path.write_text('changed source')
    try: stage(database,proposals,root/'stale.json',[manual])
    except AssertionError as error: assert 'Stale source' in str(error)
    else: raise AssertionError('Changed source was accepted')
    assert not (root/'stale.json').exists()
    path.write_text('class Service { private int a; private int alreadyReadable; }')
    fields[0]['Sha256']='different-copy'
    proposals.write_text(json.dumps({'Format':1,'Kind':'SymbolReview','TargetRoot':str(inputs),'Methods':[],'Types':[],'Fields':fields,'PropertyEvidence':evidence}))
    try: stage(database,proposals,root/'different-copy.json',[manual])
    except AssertionError as error: assert 'Stale physical module' in str(error)
    else: raise AssertionError('Different physical assembly was accepted')
    assert not (root/'different-copy.json').exists()
    # The same source guards apply to ordinary accessors inferred from mapped
    # field roles; a readable method and a mismatched field proof stay excluded.
    db=sqlite3.connect(database)
    methods=[]; access_evidence=[]
    for index,name in [(1,'a'),(2,'AlreadyReadable')]:
        token=f'0x0600001{index}'; symbol_id='m0000:'+token
        signature=f'System.Int32 Service::{name}()'
        db.execute('INSERT INTO symbols VALUES (?,?)',(symbol_id,json.dumps({'Kind':'Method','OriginalName':name,'Signature':signature})))
        db.execute('INSERT INTO source VALUES (?,?)',(symbol_id,json.dumps({'Source':'Service.cs','Name':name,'Kind':'MethodDeclaration','Line':1,'Sha256':sha})))
        methods.append({'Module':'Main.dll','Token':token,'Mvid':'mvid','Sha256':'hash','OriginalName':name,'Signature':signature,'NewName':'GetCount'})
        access_evidence.append({'Module':'Main.dll','MethodToken':token,'MethodSignature':signature,'FieldToken':'0x04000001','FieldSignature':'System.Int32 Service::a'})
    db.commit(); db.close()
    accessor={'Format':1,'Kind':'SymbolReview','InferenceKind':'FieldAccessor','TargetRoot':str(inputs),'Methods':methods,'Types':[],'Fields':[],'PropertyEvidence':[],'FieldAccessorEvidence':access_evidence}
    proposals.write_text(json.dumps(accessor))
    stage(database,proposals,root/'accessors.json')
    result=json.loads((root/'accessors.json').read_text())
    assert [m['Token'] for m in result['Methods']]==['0x06000011']
    assert result['SourceExclusions'][0]['Reason']=='Existing source method name is already readable'
    access_evidence[0]['FieldSignature']='System.Int32 DifferentCopy::a'
    proposals.write_text(json.dumps(accessor))
    try: stage(database,proposals,root/'wrong-field.json')
    except AssertionError as error: assert 'Access evidence identity mismatch' in str(error)
    else: raise AssertionError('Different accessed field was accepted')
    assert not (root/'wrong-field.json').exists()
print('PASS source visibility/readability, manual decisions, stale source and physical assembly identity guards.')
