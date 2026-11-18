"""Bind the complete generic FileCache owner and its nested delete callbacks for native proof."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read,run
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','comparison','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);component=checked(c['NextPrivateComponent']);review=checked(c['NextPrivateWholeSourceReview']);comparison=read(a.comparison)
assert component['Root']=='ata' and component['NativeMethods']==19 and component['OriginalRemainingCount']==5
assert comparison['Compiled']==review['CompiledModule'] and pin(comparison['Compiled']['Path'])==comparison['Compiled']
assert {row['OriginalToken'] for row in comparison['Rows']}=={'0x060002F9','0x060002FA'}
assert all(row['Status']=='no exact candidate' and row['CandidateCount']==1 for row in comparison['Rows'])
types=checked(component['NativeTypes'])['Types'];old_frame=next(t for t in types if t['Type']=='ata/a')
assert len(old_frame['Methods'])==3 and len(old_frame['Fields'])==4
a.output.mkdir();tool='D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll';new_types=a.output/'compiled-types.json'
run(['dotnet',tool,'--inspect-type',comparison['Compiled']['Path'],'ata'],new_types)
current=read(new_types)['Types'];method_tokens=[method['Token'] for type_ in current if type_['Type']=='ata' or type_['Type'].startswith('ata/') for method in type_['Methods']]
new_bodies=a.output/'compiled-complete-bodies.json';run(['dotnet',tool,'--inspect-methods',comparison['Compiled']['Path'],*method_tokens],new_bodies)
fresh(a.output/'protocols.json',dict(Kind='WholeGenericFileCacheNestedCallbackProtocols',Component=c['NextPrivateComponent'],SourceReview=c['NextPrivateWholeSourceReview'],Comparison=pin(a.comparison),OriginalModule=component['Module'],OriginalTypes=component['NativeTypes'],OriginalCompleteBodies=component['NativeBodies'],Compiled=comparison['Compiled'],CompiledTypes=pin(new_types),CompiledCompleteBodies=pin(new_bodies),OwnerSource=review['ActualCurrentOwnerSource'],
    OriginalTypesCount=4,OriginalMethods=19,FixedFindingsPending=5,OwnerToken='0x060002EF',OuterCallbackToken='0x060002F9',InnerCallbackToken='0x060002FA',OriginalCaptureFrameToken='0x020000B6',
    RequiredNativeProof=['Resolve Task.Run outer Func<Result> through exact ordinary owner and follow its nested Action pointer;never match compiler ordinals or a Void helper to the outer Result callback.',
    'Compare complete original/current generic frame constraints/owner/constructor/capture/cache/outer/inner bodies and every live generic MemberRef/MethodSpec.',
    'Preserve cancellation,existing/missing cache file,delete failure and exception mapping behavior using isolated disposable test files.',
    'Restore original two callback and three field metadata contracts only after complete proof;carry async read/write/public contracts as preserved owner members.'],
    SourceEdited=False,FindingsRetired=0,NewOriginalCohortDiscovery=[],NativeIdentityTreatmentPending=True))
print(dict(Owner='ata/FileCache',OriginalMethods=19,FixedFindingsPending=5,FindingsRetired=0,Output=str(a.output/'protocols.json')))
