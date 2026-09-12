"""Portable bookkeeping test: unresolved decisions must survive conversion."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    metadata = {'Module':'Example.dll', 'Token':'0x06000001', 'OriginalName':'a',
                'Signature':'System.Boolean Example::a()', 'Identity':'Example', 'Mvid':'reviewed-mvid',
                'Sha256':'reviewed-hash', 'ParameterNames':[], 'Type':'Example'}
    inventory = {'TargetRoot':str(root), 'Methods':[metadata], 'Fields':[]}
    member = {'Module':str(root/'Example.dll'), 'Mvid':'reviewed-mvid', 'Sha256':'reviewed-hash',
              'Id':'m0000:0x06000001', 'Token':'0x06000001', 'Kind':'Method', 'LocalNames':[],
              'ParameterNames':[], 'MapBlocker':None, 'Family':None,
              'Signature':metadata['Signature'], 'OriginalName':'a'}
    reason = 'Always true callback; its consumer role remains unresolved.'
    ledger = {'Decisions':[{'Status':'unresolved-callback-role', 'ProposedName':None,
                            'Reason':reason, 'Members':[member]}]}
    inventory_path = root/'inventory.json'; inventory_path.write_text(json.dumps(inventory))
    ledger_path = root/'ledger.json'; ledger_path.write_text(json.dumps(ledger))
    output = root/'review.json'
    command = [sys.executable, str(Path(__file__).with_name('to_review.py')), str(ledger_path),
               str(output), str(inventory_path)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert not json.loads(output.read_text())['Methods']
    pending = json.loads(output.with_suffix('.pending.json').read_text())['Pending']
    assert len(pending)==1 and pending[0]['Reason']==reason and pending[0]['NewName'] is None, pending
    # A changed physical snapshot must fail before publishing another review.
    member['Sha256']='changed-input'
    ledger_path.write_text(json.dumps(ledger))
    command[3]=str(root/'stale-review.json')
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode!=0 and 'Stale module' in result.stderr
    assert not (root/'stale-review.json').exists()
print('PASS unresolved callback remains pending without an alias; changed physical input is rejected.')

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    entries=[]; members=[]
    for index,module in enumerate(['A/Engine.dll','B/Engine.dll'],1):
        entry={'Module':module,'Token':f'0x0600000{index}','OriginalName':'a',
               'Signature':f'System.Void Engine{index}::a()','Identity':'Engine','Mvid':f'mvid-{index}',
               'Sha256':f'hash-{index}','ParameterNames':[],'Type':f'Engine{index}','MappingBlocker':None}
        entries.append(entry)
        members.append({'Module':str(root/module),'Mvid':entry['Mvid'],'Sha256':entry['Sha256'],
                        'Id':f'm000{index}:'+entry['Token'],'Token':entry['Token'],'Kind':'Method',
                        'LocalNames':[],'ParameterNames':[],'MapBlocker':None,'Family':'graph-family',
                        'Signature':entry['Signature'],'OriginalName':'a'})
    family=hashlib.sha256('\n'.join(e['Module']+'|'+e['Token'][2:] for e in entries).encode()).hexdigest().upper()
    for entry in entries: entry['ContractFamily']=family
    inventory={'TargetRoot':str(root),'Methods':entries,'Fields':[]}
    decisions=[{'Status':'reviewed','ProposedName':'ExecuteParameterScript','Reason':'Reviewed body','Members':[m]} for m in members]
    tool=Path(__file__).with_name('to_review.py')
    def convert(label,selected,inventory_entries):
        inventory_path=root/(label+'-inventory.json')
        inventory_path.write_text(json.dumps(dict(inventory,Methods=inventory_entries)))
        ledger_path=root/(label+'-ledger.json'); ledger_path.write_text(json.dumps({'Decisions':selected}))
        output=root/(label+'-review.json')
        result=subprocess.run([sys.executable,str(tool),str(ledger_path),str(output),str(inventory_path)],capture_output=True,text=True)
        return result,output
    run,output=convert('complete',decisions,entries)
    assert run.returncode==0,run.stderr
    rows=json.loads(output.read_text())['Methods']
    assert {r['Module'] for r in rows}=={'A/Engine.dll','B/Engine.dll'} and all(r['ContractFamily']==family for r in rows)
    assert not json.loads(output.with_suffix('.pending.json').read_text())['Pending']
    run,output=convert('unreviewed-override',decisions[:1],entries)
    assert run.returncode==0 and not json.loads(output.read_text())['Methods'],run.stderr
    assert 'Every physical family member' in json.loads(output.with_suffix('.pending.json').read_text())['Pending'][0]['Reason']
    run,output=convert('trimmed-inventory',decisions[:1],entries[:1])
    assert run.returncode!=0 and 'Incomplete family inventory' in run.stderr and not output.exists()
    decisions[1]['ProposedName']='RunDifferentBehavior'
    run,output=convert('conflicting-names',decisions,entries)
    assert run.returncode==0 and not json.loads(output.read_text())['Methods'],run.stderr
    assert len(json.loads(output.with_suffix('.pending.json').read_text())['Pending'])==2
print('PASS physical family binding requires complete matching reviews; trimmed inventories and conflicting names cannot publish partial aliases.')

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    entry={'Module':'Example.dll','Token':'0x02000002','OriginalName':'a`1',
           'Signature':'a`1','Identity':'Example','Mvid':'mvid','Sha256':'hash',
           'MappingBlocker':'generic-type'}
    member={'Module':str(root/'Example.dll'),'Token':entry['Token'],'Id':'m0000:'+entry['Token'],
            'Mvid':'mvid','Sha256':'hash','Signature':entry['Signature'],'OriginalName':entry['OriginalName'],
            'Kind':'Type','MapBlocker':None,'Family':None,'LocalNames':[],'ParameterNames':[]}
    ledger={'Decisions':[{'Status':'reviewed','ProposedName':'EnumeratorEnumerableAdapter',
                         'Reason':'Wraps an enumerator as an enumerable.','Members':[member]}]}
    inventory=root/'types.json'
    inventory.write_text(json.dumps({'TargetRoot':str(root),'Methods':[],'Types':[entry]}))
    ledger_path=root/'ledger.json'; ledger_path.write_text(json.dumps(ledger))
    output=root/'review.json'
    run=subprocess.run([sys.executable,str(Path(__file__).with_name('to_review.py')),
                        str(ledger_path),str(output),str(inventory)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    assert not json.loads(output.read_text())['Types']
    pending=json.loads(output.with_suffix('.pending.json').read_text())['Pending']
    assert pending==[{'Id':member['Id'],'Reason':'generic-type','NewName':'EnumeratorEnumerableAdapter'}],pending
print('PASS unsupported generic type aliases retain their reviewed names in pending work.')

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    names=[{'Sequence':1,'OriginalName':'A_0','NewName':'orderedSteps'}]
    entry={'Module':'Example.dll','Token':'0x06000001','OriginalName':'.ctor',
           'Signature':'System.Void Chain::.ctor(System.Object[])','Identity':'Example',
           'Mvid':'mvid','Sha256':'hash','MappingBlocker':'constructor'}
    member={'Module':str(root/'Example.dll'),'Token':entry['Token'],'Id':'m0000:'+entry['Token'],
            'Mvid':'mvid','Sha256':'hash','Signature':entry['Signature'],'OriginalName':'.ctor',
            'Kind':'Method','MapBlocker':'constructor','Family':None,'LocalNames':[],'ParameterNames':names}
    inventory=root/'inventory.json'; inventory.write_text(json.dumps({'TargetRoot':str(root),'Methods':[entry]}))
    ledger=root/'ledger.json'; ledger.write_text(json.dumps({'Decisions':[{
        'Status':'retain-constructor-name','ProposedName':None,'Reason':'Constructor argument roles reviewed.','Members':[member]}]}))
    output=root/'review.json'
    run=subprocess.run([sys.executable,str(Path(__file__).with_name('to_review.py')),str(ledger),str(output),str(inventory)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    assert not json.loads(output.read_text())['Methods']
    pending=json.loads(output.with_suffix('.pending.json').read_text())['Pending']
    assert len(pending)==1 and pending[0]['ParameterNames']==names and pending[0]['NewName'] is None,pending
print('PASS retained constructor names cannot hide reviewed formal parameter proposals.')
