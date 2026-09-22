"""Check wizard/paste maps and evidence only; never export, build or run ETS."""
from pathlib import Path
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from behavior_review import sha


def validate(root):
    read=lambda name:json.loads((root/name).read_text(encoding='utf-8'))
    verified={}
    def verify(path,expected):
        path=Path(path).resolve()
        if path not in verified:verified[path]=sha(path)
        assert verified[path]==expected,path
    summary=[]
    for version,base,number,final,stem,inspection in [
        ('63',209,210,210,'extended63-wave210','extended63-wave210-body-inspection.json'),
        ('64',37,38,39,'extended64-wave38','extended64-wave38-body-inspection.json'),
        ('64',38,39,39,'paste64-wave39','paste64-wave39-inspection.json')]:
        evidence=read(stem+'.evidence.json');review=read(stem+'.review.json')
        update=read(f'map-update{version}-wave-{number}.json')
        preflight=read(f'map-check{version}-wave{final}.json')
        assert update['Success'] and not update['Errors'] and all(c['Requested']==c['Applied'] for c in update['Changes'])
        assert preflight['Success'] and not preflight['Errors'] and not preflight['Changes']
        verify(root/f'names{version}-staged-v{base}.xml',update['BaseMapSha256'])
        verify(root/(stem+'.review.json'),update['ReviewSha256'])
        physical=evidence['PhysicalModule'];verify(physical['Input'],physical['Sha256'])
        inspected=read(inspection)
        assert all(inspected[k]==physical[k] for k in ('Input','Mvid','Sha256'))
        bodies={m['Token']:m for m in inspected['Methods']}
        doc=ET.parse(root/f'names{version}-staged-v{final}.xml').getroot()
        mapped={(m.get('Path'),r.tag,r.get('Token')):r for m in doc for r in m}
        db=sqlite3.connect((root/f'graph{version}-v3.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
        manifest=json.loads(db.execute('SELECT data FROM meta').fetchone()[0])
        source_root=Path(manifest['Export']).parent
        usage_edges=set();state_owners=set()

        def check_usage(usage):
            verify(usage['Inspection'],usage['Sha256'])
            caller=usage['SourceId'];token=caller.split(':')[1]
            available=[json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE source=?',(caller,))]
            ops={i['Offset']:i for i in bodies[token]['Instructions']}
            for edge in usage['Edges']:
                assert edge in available
                target=edge['Target']
                assert target['Status']=='input' and not target.get('Error')
                assert target['Id'].split(':')[0]==physical['Id'] and Path(target['PhysicalModule']).resolve()==Path(physical['Input']).resolve()
                assert ops[edge['Offset']]['Operand']['Text']==target['Signature'] and ops[edge['Offset']]['OpCode']==edge['Operation']
                usage_edges.add((caller,edge['Offset'],target['Id']))
            if usage.get('CallerUsage'):check_usage(usage['CallerUsage'])
            if usage.get('CallerStateMachine'):
                owner=usage['CallerStateMachine'];verify(owner['Path'],owner['Sha256'])
                actual=bodies[owner['MethodToken']]['StateMachineOwners']
                assert len(actual)==1 and all(owner[k]==v for k,v in actual[0].items())
                state_owners.add((owner['MethodToken'],owner['OwnerToken']))

        for d in evidence['Decisions']:
            for location in d['Source']:
                verify(source_root/location['Path'],location['Sha256'])
                if location.get('UsageEvidence'):check_usage(location['UsageEvidence'])
            for key in ('IL','OptionParentsDeclaration'):
                if key in d:verify(d[key]['Path'],d[key]['Sha256'])
        for kind in ('Methods','Types','Fields'):
            for row in review[kind]:
                m=mapped.get((row['Module'],kind[:-1],row['Token']))
                # Constructor scopes have an empty name and remain constructors.
                assert m is not None and m.get('Signature')==row['Signature'] and (m.get('NewName') or '')==row['NewName']
                for collection,tag,position in [('ParameterNames','Parameter','Sequence'),('LocalNames','Local','Index')]:
                    scopes={int(s.get(position)):s for s in m.findall(tag)}
                    for scope in row.get(collection,[]):
                        if not scope.get('NewName'):continue
                        if tag=='Parameter' and scope['NewName']==scope['OriginalName'] and scope[position] not in scopes:continue
                        assert scopes[scope[position]].get('NewName')==scope['NewName']
                        if tag=='Local':assert scopes[scope[position]].get('ExpectedType')==scope['ExpectedType']
        prefix='Knx.Ets.ViewModel.Application.Workspace.ExtendedCopy.ExtendedCopyViewModel' if stem.startswith('extended') else 'Knx.Ets.ViewModel.ContextMenu.PasteCommandHandler'
        methods=read('clipboard63-wave201-methods.json' if version=='63' else 'operations64-wave32-methods.json')['Methods']
        fields=read('viewmodel63-fields.json' if version=='63' else 'operations64-wave32-fields.json')['Fields']
        remaining=[]
        for kind,rows in [('Method',methods),('Field',fields)]:
            for row in rows:
                if not row['Type'].startswith(prefix) or not row['NeedsReadableName'] or (row['Module'],kind,row['Token']) in mapped:continue
                uses=[json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?',(physical['Id']+':'+row['Token'],))]
                remaining.append({'Kind':kind,'Token':row['Token'],'Signature':row['Signature'],'IncomingUses':uses,
                    'Reason':'Unresolved generated storage/helper or state-machine implementation; no domain alias inferred.'})
        summary.append({'Version':version,'Stem':stem,'PhysicalModule':physical,'MapSha256':sha(root/f'names{version}-staged-v{final}.xml'),
            'Decisions':{k:len(review[k]) for k in ('Methods','Types','Fields')},'VerifiedUsageEdges':len(usage_edges),
            'VerifiedStateMachineOwners':sorted(state_owners),'RemainingInventoryCandidates':remaining})
        db.close()
    result={'Scopes':summary,'AppliedToSource':False,'EtsRuntimeExecuted':False,
        'Limits':['This checks the selected wizard and paste classes, not full application coverage or runtime behavior.',
                  'SDK whitelist bindings and all previous aliases/scopes are checked by checkpoint_behavior before publication.',
                  'Async/iterator source evidence does not authorize renaming runtime contract methods or their blocked body locals.'],
        'BehaviorNotes':['Extended-copy operation creation releases one readiness semaphore permit after storing the result.',
            'Option categories retain Line=1, Segment=2 and MiddleGroup=6; Create visibility/propagation and Keep versus Lose/Create locking are unchanged.',
            'Normal paste clears clipboard after a move dialog; special paste does not. Both notify only for a nonnull move operation sequence.',
            'Paste text uses the 6.4 matching-object provider. Device lock checks use GetSelfOrParentalDevices rather than the 6.3 local iterator.',
            'Existing license, password, validation and cancellation gates remain intact; this work stages names only.'],
        'ToolValidation':{'De4dotCommit':'1de232c4','NameCandidatesSuite':'passed on Windows with portable synthetic fixtures',
            'BehaviorReviewUnitTests':16,'CrossPlatformExecution':'not run locally'}}
    with (root/'wizard-paste-wave210-validation.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps([{k:s[k] for k in ('Version','Stem','Decisions','VerifiedUsageEdges','VerifiedStateMachineOwners')} for s in summary],indent=2))


if __name__=='__main__':validate(Path(sys.argv[1]))
