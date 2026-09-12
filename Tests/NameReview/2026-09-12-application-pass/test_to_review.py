"""Portable bookkeeping test: unresolved decisions must survive conversion."""
import json
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
