"""Bind a selected whole owner to current source and native original owner witnesses."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--component',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--inspector',type=Path,default=Path('D:/knx_analysis/sequence-closure-inspector-preservation01/GeneratedClosureIdentityInspection.dll'))
parser.add_argument('--read-only',action='store_true',help='Prepare complete evidence/command without publishing navigation state.')
args=parser.parse_args();assert not args.output.exists()
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']));component=read(args.component)
types=checked(component['NativeTypes'])['Types'];bodies=checked(component['NativeBodies'])
assert component['NativeMethods']==sum(len(t['Methods']) for t in types)==len(bodies['Methods'])
build=checked(cursor['Completed']['New109ProjectBuild']);export=Path(build['Export']);source=export/'Knx.Ets.Common.3'/(component['Root']+'.cs')
reuse=checked(build['Inputs']['ExportReuse']);assert reuse['Files'][source.relative_to(export).as_posix()]==pin(source)['Sha256']
report=checked(component['CurrentSourceReport']);root_token=int(next(t['Token'] for t in types if t['Type']==component['Root']),16)
root=next(r for r in report['Roots'] if r['RootTypeToken']==root_token)
method_tokens={int(m['Token'],16) for t in types for m in t['Methods']}
method_findings=[f for f in component['FixedOriginalRemainingFindings'] if f.startswith(component['Module']['Input']+' 06')]
assert method_findings
args.output.mkdir();review=args.output/'complete-component-review.json'
fresh(review,dict(Kind='FixedPrivateWholeOwnerSourceReviewInputs',Component=pin(args.component),Module=component['Module'],Root=component['Root'],NativeTypes=component['NativeTypes'],NativeCompleteBodies=component['NativeBodies'],
    ActualCurrentOwnerSource=pin(source),CurrentBuild=cursor['Completed']['New109ProjectBuild'],CompiledModule=pin(export/'bin/Knx.Ets.Common.dll'),
    NativeOwnerWitnesses=[w for w in root['BodyWitnesses'] if w['ImplementationToken'] in method_tokens],
    OriginalPendingFindings=method_findings,CompleteFixedFindings=component['FixedOriginalRemainingFindings'],OriginalRemainingCount=component['OriginalRemainingCount'],
    OriginalMethods=component['NativeMethods'],FindingsResolved=0,NewDiscovery=[],Limits='Method-only pointer inspection preview; all type/field/parameter findings remain in CompleteFixedFindings and receive no credit.'))
next_report=args.output/'compiled-closure-identity.json'
command=f'dotnet {args.inspector.as_posix()} {review.as_posix()} {(export/"bin/Knx.Ets.Common.dll").as_posix()} {next_report.as_posix()}'
if args.read_only:
    print(dict(Owner=component['Root'],OriginalMethods=component['NativeMethods'],FixedFindings=component['OriginalRemainingCount'],FindingsResolved=0,Review=str(review),NextCommand=command,StateEdited=False))
    raise SystemExit(0)
cursor.update(UpdatedUtc=now(),CurrentStage='next-private-whole-component-prepared',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
cursor['NextPrivateComponent']=pin(args.component);cursor['NextPrivateWholeSourceReview']=pin(review)
cursor['NextPrivateComponentFixedFindings']=component['OriginalRemainingCount'];cursor['NextPrivateComponentFindingsResolved']=0
for obsolete in ('NextPrivateCompiledTypes','NextPrivateCompiledBodies','NextPrivateFactoryEvidence','NextPrivateProtocolInputsProbe'):cursor.pop(obsolete,None)
cursor['NextItems'][0]={'Task':'compare exact generated owner/body/capture roles for the complete '+component['Root']+' component','Detail':command};cursor['NextCommand']=command
remaining=checked(cursor['Completed']['PrivateCohortDelta'])['OriginalRemaining']
cursor['Status']='Active broader goal. Accepted prior stage receipts preserved. Next fixed owner: '+component['Root']+f" ({len(types)} types/{component['NativeMethods']} methods/{component['OriginalRemainingCount']} original findings). Private{remaining} plus prior discovery96, generated/naming queues, ETS6.4 transfer and wider runtime remain open."
publish_navigation(args.state,before,state,args.output/'cursor-private-component-ready.json',cursor)
print(dict(Owner=component['Root'],OriginalMethods=component['NativeMethods'],FixedFindings=component['OriginalRemainingCount'],FindingsResolved=0,NextCommand=command,OverallComplete=False))
