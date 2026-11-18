"""Select a whole unresolved owner from the fixed cohort, excluding verified repairs."""
import argparse
from collections import Counter
from pathlib import Path

from continue_readability import checked, fresh, pin, read, run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assert not args.output.exists(), 'Fresh owner evidence directory required'
state=read(args.state);cursor=read(state['Naming']['BlockCursor']);cohort=checked(cursor['FixedCohorts']['PrivateMetadata'])
delta=checked(cursor['Completed']['PrivateCohortDelta']);current=checked(delta['CurrentAudit'])
original=Counter(cohort['Original']);pending=original & Counter(current['Issues'])
assert sum(pending.values())==delta['OriginalRemaining']
prior=checked(cursor['PreparedPrivateComponent']);module=prior['Module'];initial=read(Path(prior['NativeTypeReport']['Path']).parent/'cohort.json')
observed=checked(initial['CurrentSourceReport'])
module_findings=[f for f in pending if f.startswith(module['Input']+' ')]
choices=[f for f in module_findings if f.startswith(module['Input']+' 06')] or module_findings
assert choices
def finding_token(finding):return finding.removeprefix(module['Input']+' ').split(': ',1)[0].split(' ',1)[0]
first=int(finding_token(choices[0]),16)
definition=next(d for d in observed['Definitions'] if d['Token']==first)
owner=definition['FullName'].split('::',1)[0].rsplit(' ',1)[-1].split('/',1)[0]
assert owner!='arw', 'Do not replay the resolved Dongle component'
args.output.mkdir()
native=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll']
types_path=args.output/'native-types.json'
run(native+['--inspect-type',module['Input'],owner],types_path)
types=read(types_path)['Types']
types=[t for t in types if t['Type']==owner or t['Type'].startswith(owner+'/')]
methods=[m['Token'] for t in types for m in t['Methods']]
assert methods and len(methods)==len(set(methods))
component_tokens={t['Token'] for t in types}
for t in types:
    for category in ('Fields','Methods','Properties','Events'):component_tokens.update(row['Token'] for row in t[category])
selected=[f for f in module_findings if '0x'+finding_token(f) in component_tokens]
body_path=args.output/'native-bodies.json'
run(native+['--inspect-methods',module['Input'],*methods],body_path)
fresh(args.output/'component.json',dict(Kind='FixedRemainingPrivateOwnerComponent',ParentCohort=cursor['FixedCohorts']['PrivateMetadata'],
    CurrentFindingAudit=delta['CurrentAudit'],Module=module,Root=owner,Types=[t['Token'] for t in types],
    NativeTypes=pin(types_path),NativeBodies=pin(body_path),CurrentSourceReport=initial['CurrentSourceReport'],
    FixedOriginalRemainingFindings=selected,OriginalRemainingCount=len(selected),Resolved=0,NewDiscovery=[],
    NativeMethods=len(methods),FixedComponentTokenCount=len(component_tokens),FindingPreviewBasis='All type/field/method findings in the complete physical owner, with a method used only as a navigation anchor.',
    Next='Inspect the complete owner/component, select exact source/compiled counterparts and decide supported names/treatment. Unsupported cases remain explicit.'))
print(dict(Owner=owner,Types=len(types),Methods=len(methods),OriginalRemainingFindings=len(selected),NewDiscovery=0,Component=str(args.output/'component.json')))
