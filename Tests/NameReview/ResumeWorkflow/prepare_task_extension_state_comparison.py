"""Prepare complete generic TaskExtensions state pairs and role candidates;no equivalence credit."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','roles','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);roles=read(a.roles);protocols=checked(roles['Protocols']);component=checked(protocols['Component'])
assert roles['Kind']=='WholeTaskExtensionsGenericKickoffFieldRoleProof' and roles['GenericOwners']==2 and roles['FindingsRetired']==0 and component['OriginalRemainingCount']==11
old_bodies=checked(protocols['OriginalCompleteBodies'])['Methods'];new_bodies=checked(protocols['CompiledCompleteBodies'])['Methods'];rows=[]
for row in roles['Rows']:
    old=row['Original'];new=row['Compiled'];assert row['KickoffParameterStorageRolesBound'] and row['WholeMoveBodyEquivalencePending']
    pairs=[dict(Role=role,Original=field['Field'],Compiled=new['KickoffRoles'][role]['Field']) for role,field in old['KickoffRoles'].items()]
    remaining_old=[f for f in old['RemainingFields'] if not f['IsOriginalUnusedStorage']];remaining_new=[f for f in new['RemainingFields'] if not f['IsOriginalUnusedStorage']]
    pending=[]
    for field in remaining_old:
        type_=field['Type'];candidates=[f for f in remaining_new if f['Type']==type_]
        if type_.startswith('aqr/a<'):
            candidates=[f for f in remaining_new if 'DisplayClass' in f['Type']]
        if len(candidates)==1:pairs.append(dict(Role='remaining-live-storage:'+type_,Original=field['Field'],Compiled=candidates[0]['Field'],CandidateOnly=True))
        else:pending.append(dict(Original=field,CompiledCandidates=candidates,UnresolvedReason='Storage role requires complete state protocol evidence'))
    old_move=next(m for m in old_bodies if m['Signature']=='System.Void '+old['Frame']+'::MoveNext()');new_move=next(m for m in new_bodies if m['Signature']=='System.Void '+new['Frame']+'::MoveNext()')
    rows.append(dict(Owner=old['Owner'],OriginalFrame=old['Frame'],CompiledFrame=new['Frame'],OriginalMove=old_move,CompiledMove=new_move,FieldRoleCandidates=pairs,UnresolvedStorageRoles=pending,OriginalUnusedStorage=[f for f in old['RemainingFields'] if f['IsOriginalUnusedStorage']],GenericOwnerContract=old['GenericOwnerContract'],GenericFrameContract=old['GenericFrameContract'],OriginalHandlerCount=len(old_move['ExceptionHandlers']),CompiledHandlerCount=len(new_move['ExceptionHandlers']),StateProtocolEquivalenceVerified=False))
fresh(a.output,dict(Kind='WholeTaskExtensionsCompleteStateComparisonInputs',Component=protocols['Component'],Protocols=roles['Protocols'],KickoffRoleProof=pin(a.roles),Original=roles['Original'],Compiled=roles['Compiled'],Rows=rows,WholeOwnerMethods=10,FixedFindingsPending=11,FindingsRetired=0,NewDiscovery=[],SourceEdited=False,RequiredNext='Build a read-only complete symbolic entry/resume/filter/finally comparison,including generic closure lifetime and compiler delegate cache;reject ambiguous role assignments before native metadata integration.'))
print(dict(GenericStatePairs=2,StorageRoleCandidates=sum(len(r['FieldRoleCandidates']) for r in rows),UnresolvedStorageRoles=sum(len(r['UnresolvedStorageRoles']) for r in rows),EquivalenceVerified=False,FindingsRetired=0,Output=str(a.output)))
