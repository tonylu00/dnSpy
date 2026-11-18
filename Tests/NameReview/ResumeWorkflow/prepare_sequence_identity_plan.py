"""Prepare native treatment of the complete frozen EnumerableUtilities component."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from continue_readability import checked, fresh, pin, read

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state', type=Path, required=True)
parser.add_argument('--inspection', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists(), 'Fresh plan directory required'
state = read(args.state); cursor = read(state['Naming']['BlockCursor'])
component = checked(cursor['NextPrivateComponent']); report = read(args.inspection)
assert component['Root'] == 'asw' and component['OriginalRemainingCount'] == 6
for key in ('Original', 'Compiled', 'Inspector'): assert pin(report[key]['Path'])['Sha256'] == report[key]['Sha256']
assert report['Original']['Sha256'] == component['Module']['InputSha256']
assert len(report['Rows']) == 2 and sum(len(row['Fields']) for row in report['Rows']) == 16
bodies = checked(component['NativeBodies'])
methods = {row['Token']: row['Signature'] for row in bodies['Methods']}
old = ET.parse('D:/knx_analysis/ets-readability-v1044-continuation02/private-common-owner-block/generated-method-identity-plan02.xml')
root = old.getroot(); module = root.find('Module')
assert module.get('Sha256') == component['Module']['InputSha256']
assert root.get('MapSha256') == state['Maps']['63']['Sha256']
ET.SubElement(module, 'Method', dict(Token='0x060002AC', Signature=methods['0x060002AC'], OwnerToken='0x060002A5',
    OwnerSignature=methods['0x060002A5'], Treatment='cached-delegate'))
for row in report['Rows']:
    ET.SubElement(module, 'Iterator', dict(OwnerToken='0x' + row['OwnerToken'], OwnerSignature=row['Owner'],
        StateToken=row['StateToken'], OriginalProtocolSha256=row['OriginalProtocolSha256'],
        CompiledReference=report['Compiled']['Path'], CompiledReferenceSha256=report['Compiled']['Sha256'],
        CompiledProtocolSha256=row['CompiledProtocolSha256'], ControlFlowReview='literal-compiled-protocol-identity-only'))
args.output.mkdir(); ET.indent(old); plan = args.output / 'generated-identity-plan.xml'
old.write(plan, encoding='utf-8', xml_declaration=True)
fresh(args.output / 'preparation.json', dict(Kind='FixedSequenceNativeIdentityPlanPreparation', Component=cursor['NextPrivateComponent'],
    ProtocolInspection=pin(args.inspection), Plan=pin(plan), OriginalFindingTokens=['0x060002AC','0x060002AD','0x060002AF','0x060002B0','0x060002B6','0x060002B8'],
    FindingsResolved=0, AddedDiscovery=[], SourceEdited=False, MetadataRestorationVerified=False, RuntimeVerified=False,
    Limits='Two factories bind every state method and eight fields each; compiled literal protocol fingerprints are acceptance guards, not original/compiled behavior-equivalence claims.'))
print(dict(PreparedFindings=6, NativeMethods=39, AddedDiscovery=0, Plan=str(plan)))
