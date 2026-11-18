"""Inspect complete fixed sequence-state protocols from already collected native bodies."""
import argparse
from pathlib import Path

from continue_readability import checked, fresh, pin, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assert not args.output.exists(), 'Fresh protocol review required'
state=read(args.state);cursor=read(state['Naming']['BlockCursor'])
component=checked(cursor['NextPrivateComponent'])
original=checked(component['NativeTypes']);compiled=checked(cursor['NextPrivateCompiledTypes'])
original_bodies=checked(component['NativeBodies']);compiled_bodies=checked(cursor['NextPrivateCompiledBodies'])
factories=checked(cursor['NextPrivateFactoryEvidence'])
assert component['Root']=='asw' and component['NativeMethods']==39 and component['OriginalRemainingCount']==6
by_original={m['Signature']:m for m in original_bodies['Methods']}
by_compiled={m['Signature']:m for m in compiled_bodies['Methods']}
rows=[]
for factory in factories['Rows']:
    def type_name(text):return text.removeprefix('System.Void ').split('::.ctor',1)[0].removesuffix('<T>')
    old_name=type_name(factory['OriginalStateConstructor']);new_name=type_name(factory['CompiledStateConstructor'])
    old=next(t for t in original['Types'] if t['Type']==old_name)
    new=next(t for t in compiled['Types'] if t['Type']==new_name)
    rows.append(dict(OwnerSignature=factory['OwnerSignature'],FactoryEvidence=factory,
        OriginalState=old,CompiledState=new,
        OriginalCompleteBodies=[by_original[m['Signature']] for m in old['Methods']],
        CompiledCompleteBodies=[by_compiled[m['Signature']] for m in new['Methods']],
        MetadataNameRestorationVerified=False,BehaviorEquivalenceVerified=False,
        Next='Bind state/current/thread/input/local/disposal fields by complete instruction uses and interface contracts, compare MoveNext/finally protocols, then implement native exact metadata treatment. Never match compiler ordinals.'))
fresh(args.output,dict(Kind='FixedSequenceIteratorCompleteProtocolReviewInputs',Component=cursor['NextPrivateComponent'],
    FactoryEvidence=cursor['NextPrivateFactoryEvidence'],OriginalBodies=component['NativeBodies'],CompiledBodies=cursor['NextPrivateCompiledBodies'],
    Rows=rows,GenericLambdaFinding='0x060002AC',OriginalRemainingFindings=6,FindingsResolved=0,AddedDiscovery=[],RuntimeVerified=False))
print(dict(StateProtocols=len(rows),CompleteOriginalStateMethods=sum(len(r['OriginalCompleteBodies']) for r in rows),
    CompleteCompiledStateMethods=sum(len(r['CompiledCompleteBodies']) for r in rows),FindingsResolved=0,Output=str(args.output)))
