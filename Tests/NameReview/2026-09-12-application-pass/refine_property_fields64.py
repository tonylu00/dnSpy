"""Behavioral refinements after inspecting setter/call-site roles in ETS 6.4.

Usage: refine_property_fields64.py SOURCE_ROOT GRAPH_DB REVIEW NEW_REVIEW
Keeps the direct getter proof and records why its first name was insufficient.
"""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
import sys

root,database,review,output=map(Path,sys.argv[1:5]); assert not output.exists()
data=json.loads(review.read_text())
changes=[
    ('Knx.Ets.HawkNET.dll','0x040001C6','currentAccessKey',
     'Knx.Ets.HawkNET.2/Knx/Ets/Hawk/DeviceManagement.cs','5B958C1980C7ACD44A0B61CEDF91195F1E93062FE7D069119FFC49532DCF8C55',
     'The constructor keeps configured accessKey separately. This field resets to uint.MaxValue, is assigned from attempted/chosen keys during authorization, and is reused on reconnect.'),
    ('Knx.Ets.ObjectModel.dll','0x04000F7E','operationProjectName',
     'Knx.Ets.ObjectModel.2/Operations/Operation.cs','B7BBB65F1A49342077C077FEB93B206A394F2DECD625B3724A9EB7966EBF8890',
     'Base Operation storage for its ProjectName getter/setter. The owner-qualified field name distinguishes it from existing names in derived operation scopes.'),
    ('Knx.Ets.ViewModel.dll','0x04003DD8','updateOnlineCatalogCommand',
     'Knx.Ets.ViewModel.2/Application/Wizards/ImportWizard/CatalogDataOutOfDateViewModel.cs','9BAB47740717D7614E51C2A87F30A1C704A692F660803C0BD3563A43FAA24C06',
     'CommandBuilder invokes method_11, which starts and awaits Update. Update refreshes the online-catalog market list and manufacturer catalog for the selected market. Expand the Oc abbreviation from those calls.')]
for module,token,name,source,sha,reason in changes:
    assert hashlib.sha256((root/source).read_bytes()).hexdigest().upper()==sha, ('Stale refinement source',source)
    entry=next(f for f in data['Fields'] if f['Module']==module and f['Token']==token)
    data.setdefault('BehaviorRefinements',[]).append({'Module':module,'Token':token,'Before':entry['NewName'],'NewName':name,
        'Source':source,'SourceSha256':sha,'Reason':reason,'Status':'staged; not applied'})
    entry['NewName']=name
    entry['Reason']+='; '+reason

# Carry the expanded command terminology into the small call chain just read.
command=next(f for f in data['Fields'] if f['Module']=='Knx.Ets.ViewModel.dll' and f['Token']=='0x04003DD8')
command_source=changes[2][3]; command_sha=changes[2][4]
with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
    manifest=json.loads(db.execute('SELECT data FROM meta').fetchone()[0])
    module=next(m for m in manifest['Modules'] if Path(m['Input']).resolve()==(Path(data['TargetRoot'])/command['Module']).resolve())
    assert module['Mvid']==command['Mvid'] and module['Sha256']==command['Sha256']
    for token,name,reason,parameter in [
        ('0x06008455','RunOnlineCatalogUpdateAsync','Starts Update, stores its Task and awaits it.',None),
        ('0x06008456','IsOnlineCatalogUpdateRunning','Returns true only when the saved task exists and IsFinished is false. Preserve this condition exactly, including its use by CommandBuilder.',None),
        ('0x06008457','UpdateOnlineCatalogProgress','Sets wizard Progress to the integer percentage obtained by multiplying the reported fraction by 100.','progress'),
        ('0x04003DD7','onlineCatalogUpdateTask','Task saved by command execution and inspected by the running predicate and progress-bar visibility.',None)]:
        symbol_id=module['Id']+':'+token
        symbol=json.loads(db.execute('SELECT data FROM symbols WHERE id=?',(symbol_id,)).fetchone()[0])
        locations=[json.loads(r[0]) for r in db.execute('SELECT data FROM source WHERE id=?',(symbol_id,))]
        assert locations and all(r['Source']==command_source and r['Sha256']==command_sha for r in locations)
        assert not symbol.get('Blocker') and not symbol.get('Family')
        row={k:command[k] for k in ('Module','Identity','Mvid','Sha256','Type')}
        row.update(Token=token,Signature=symbol['Signature'],OriginalName=symbol['OriginalName'],NewName=name,
                   Reason=reason,MappingBlocker=None,ContractFamily=None,ParameterNames=[])
        if parameter:
            formal=symbol['Parameters']; assert len(formal)==1 and formal[0]['HasMetadata']
            row['ParameterNames']=[{'Sequence':formal[0]['Sequence'],'OriginalName':formal[0]['OriginalName'],'HasMetadata':True,'NewName':parameter}]
        data['Methods' if symbol['Kind']=='Method' else 'Fields'].append(row)
        data['BehaviorRefinements'].append({'Id':symbol_id,'Module':command['Module'],'Token':token,'NewName':name,
            'Source':command_source,'SourceSha256':command_sha,'Reason':reason,'Status':'staged; not applied'})
output.write_text(json.dumps(data,indent=2)+'\n')
print('Refined current authorization state, operation project-name storage and online-catalog command roles; no source changes.')
