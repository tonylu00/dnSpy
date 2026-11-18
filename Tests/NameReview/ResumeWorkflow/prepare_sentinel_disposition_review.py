"""Resume the fixed anonymous type/storage obligations from current native receipts."""
import argparse
from pathlib import Path

from continue_readability import checked, fresh, pin, read

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists(), 'Choose a fresh sentinel disposition review'
state = read(args.state)
cursor = read(state['Naming']['BlockCursor'])
receipt = checked(cursor['Completed']['ActualSentinelMetadata'])
assert len(receipt['Rows']) == 2 and not receipt['RuntimeVerified']
manifest = checked(cursor['Disposition'])
selected = {}
for row in receipt['Rows']:
    assert row['ExactFields'] == 2 and row['VerifiedOrdinaryMethodBodies'] == 5
    assert row['OriginalTypeNamesAndPrivateFieldStorageVerified'] and not row['AdditionalMetadataDiscovery']
    for label in ('Original','Rebuilt','Source'):
        assert pin(row[label]['Path']) == row[label]
    module = Path(row['Original']['Path']).relative_to(manifest['Root']).as_posix()
    selected[module] = row
streams = [manifest[name] for name in ('ReviewedGeneratedDispositions','RemainingNativeGeneratedDispositions')]
for stream in streams:
    assert pin(stream['Path']) == stream
rows = []
for stream in streams:
    with Path(stream['Path']).open(encoding='utf-8-sig') as source:
        import json
        for line in source:
            row = json.loads(line)
            if row['Module'].replace('\\','/') not in selected:
                continue
            proof = selected[row['Module'].replace('\\','/')]
            token = int(row['Token'],16)
            if token != proof['OriginalToken'] and not (row['Kind']=='Fields' and proof['ExactTypeName']+'::' in row['Signature']):
                continue
            assert row['Sha256'] == proof['Original']['Sha256']
            rows.append(dict(Preimage=row,AuthoritativeStream=stream,ActualTypeStorageAcceptance=proof,
                NextEvidenceRoute='Replay existing generated-artifact source review with current native type/storage acceptance; unused storage has zero naming/reconstruction credit.'))
assert len([r for r in rows if r['Preimage']['Kind']=='Types']) == 2
assert len(rows) == 6 and len([r for r in rows if r['Preimage']['Signature'].endswith('::a')]) == 2
fresh(args.output,dict(Kind='FixedAnonymousSentinelTypeStorageDispositionInputs',Disposition=cursor['Disposition'],
    SourceMetadataReceipt=cursor['Completed']['ActualSentinelMetadata'],Streams=streams,Rows=rows,
    FixedOriginalTypes=2,NativeTypeFieldContractsVerified=4,CounterCredit=0,AddedDiscovery=[],RuntimeVerified=False))
print(dict(FixedTypes=2,SelectedDispositionRows=len(rows),CounterCredit=0,AddedDiscovery=0,Review=str(args.output)))
