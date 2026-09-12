import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import xml.etree.ElementTree as ET
from stage_correspondence import stage

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory); contexts={}
    for version in ['old','new']:
        source=root/version/'source'; source.mkdir(parents=True)
        inputs=root/version/'input'; inputs.mkdir()
        code=source/'Service.cs'; code.write_text('class Service {}')
        sha=hashlib.sha256(code.read_bytes()).hexdigest().upper()
        database=root/(version+'.sqlite'); db=sqlite3.connect(database)
        db.executescript('CREATE TABLE meta(data TEXT); CREATE TABLE symbols(id TEXT,data TEXT); CREATE TABLE source(id TEXT,data TEXT);')
        module={'Id':'m0000','Input':str(inputs/'Service.dll'),'Mvid':'same-mvid','Sha256':version+'-hash'}
        db.execute('INSERT INTO meta VALUES (?)',(json.dumps({'Export':str(source/'export.xml'),'Modules':[module]}),))
        for index in range(1,4):
            key=f'm0000:0x0600000{index}'; name='a' if version=='new' else 'b'
            symbol={'Kind':'Method','OriginalName':name,'Signature':f'System.Void Service::{name}{index}(System.String)',
                    'Parameters':[{'Sequence':1,'OriginalName':'arg','Type':'System.String','HasMetadata':True}]}
            db.execute('INSERT INTO symbols VALUES (?,?)',(key,json.dumps(symbol)))
            db.execute('INSERT INTO source VALUES (?,?)',(key,json.dumps({'Kind':'MethodDeclaration','Source':'Service.cs','Name':'AlreadyReadable' if index==2 and version=='new' else name,'Line':1,'Sha256':sha})))
        db.commit(); db.close()
        mapping=ET.Element('SourceNameMap',Version='1',InputDirectory=str(inputs))
        module_row=ET.SubElement(mapping,'Module',Path='Service.dll',Mvid='same-mvid',Sha256=version+'-hash')
        for index in range(1,4) if version=='old' else [3]:
            method=ET.SubElement(module_row,'Method',Token=f'0x0600000{index}',ExpectedName='b' if version=='old' else 'a',
                                 Signature=f'System.Void Service::{"b" if version=="old" else "a"}{index}(System.String)',NewName='ReadProjectName' if version=='old' else 'ExistingReviewedName')
            ET.SubElement(method,'Parameter',Sequence='1',ExpectedName='arg',NewName='projectName')
        map_path=root/(version+'.xml'); ET.ElementTree(mapping).write(map_path)
        contexts[version]=(database,inputs,map_path,code)
    old,new=contexts['old'],contexts['new']
    report={'ReferenceRoot':str(old[1]),'TargetRoot':str(new[1]),'ReferenceSourceMap':str(old[2]),
            'ReferenceSourceMapHash':hashlib.sha256(old[2].read_bytes()).hexdigest(),'Candidates':[]}
    for index in range(1,4):
        report['Candidates'].append({'Module':'Service.dll','ReferenceToken':f'0600000{index}','TargetToken':f'0600000{index}',
            'ReferenceMvid':'same-mvid','TargetMvid':'same-mvid','ReferenceHash':'old-hash','TargetHash':'new-hash',
            'Reference':f'System.Void Service::b{index}(System.String)','Target':f'System.Void Service::a{index}(System.String)',
            'SuggestedName':'ReadProjectName','TargetIdentity':'Service'})
    candidates=root/'candidates.json'; candidates.write_text(json.dumps(report))
    output=root/'accepted.json'; stage(old[0],new[0],candidates,new[2],output)
    result=json.loads(output.read_text())
    assert len(result['Methods'])==1 and result['Methods'][0]['ParameterNames'][0]['NewName']=='projectName'
    assert {e['Reason'] for e in result['SourceExclusions']}=={'Existing target source name is readable','Existing staged target alias preserved'}
    new[3].write_text('changed')
    try: stage(old[0],new[0],candidates,new[2],root/'stale-source.json')
    except AssertionError as error: assert 'Stale source' in str(error)
    else: raise AssertionError('Changed source accepted')
    assert not (root/'stale-source.json').exists()
    new[3].write_text('class Service {}')
    report['Candidates'][0]['TargetHash']='different-copy'
    candidates.write_text(json.dumps(report))
    try: stage(old[0],new[0],candidates,new[2],root/'stale-module.json')
    except AssertionError as error: assert 'Physical input changed' in str(error)
    else: raise AssertionError('Same MVID different hash accepted')
    assert not (root/'stale-module.json').exists()
print('PASS source-visible correspondence, reviewed aliases, exact parameter roles, stale source and same-MVID physical hash guards.')
