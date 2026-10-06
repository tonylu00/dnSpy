"""Prepare physical review data from coupled decisions, never modify a map.

Existing aliases are retained. Replacement decisions require a separate explicit
review. Native tools remain responsible for mapping and contract enforcement.
"""
import argparse, json, xml.etree.ElementTree as ET
from pathlib import Path
from prepare_physical_review import prepare

def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def token(value): return '0x'+format(int(value,16),'08X')

def build(decisions, inventories, family_inventory, mapping, module, reason):
    inventory_data={str(Path(q)):read(q) for q in inventories}
    family_data=read(family_inventory)
    roots={q['TargetRoot'] for q in inventory_data.values()}
    assert len(roots)==1, 'Physical inventories must have one target root'
    index={}
    for path,q in inventory_data.items():
        for kind in ('Types','Fields','Methods'):
            for row in q[kind]:
                if row['Module']==module:index[(kind,token(row['Token']))]=(row,path)
    root=ET.parse(mapping).getroot()
    current=next(q for q in root if q.get('Path')==module)
    mapped={token(q.get('Token')):q for q in current}
    rows={}
    def select(kind,t):
        t=token(t);key=(kind,t)
        if key not in rows:
            original,path=index[key]
            rows[key]=dict(Kind=kind,Module=module,Token=t,Inventory=path,Reason=reason)
        return rows[key],index[key][0]
    for kind in ('Types','Fields','Methods'):
        for t,(alias,evidence) in decisions.get(kind,{}).items():
            prior=mapped.get(token(t));old=prior.get('NewName') if prior is not None else None
            if old:continue
            row,_=select(kind,t);row.update(NewName=alias,Reason=reason+' '+evidence)
    for t,names in decisions.get('Parameters',{}).items():
        row,original=select('Methods',t)
        params=original['ParameterNames'];assert len(params)==len(names), t
        prior=mapped.get(token(t));old={} if prior is None else {int(q.get('Sequence')):q.get('NewName') for q in prior.findall('Parameter')}
        row['ParameterNames']={str(q['Sequence']):name for q,name in zip(params,names) if not old.get(q['Sequence'])}
        row['Reason']+=' Parameter roles follow the typed reads, constructor storage, matching getter/setter pair or XML attribute writes in the pinned complete body.'
    for t,names in decisions.get('Locals',{}).items():
        row,_=select('Methods',t);prior=mapped.get(token(t));old={} if prior is None else {int(q.get('Index')):q.get('NewName') for q in prior.findall('Local')}
        row['LocalNames']={i:name for i,name in names.items() if not old.get(int(i))}
        row['Reason']+=' Local slots follow native stloc/ldloc operands and the version/metadata/XML formatting values in the complete body.'
    family=decisions.get('Family')
    if family:
        target=next(q for q in family_data['Methods'] if q['Module']==module and token(q['Token'])==token(family['Token']))
        members=[q for q in family_data['Methods'] if q['ContractFamily']==target['ContractFamily']]
        assert members and all(not q['MappingBlocker'] for q in members), 'Family is protected'
        for q in members:
            assert q['Module']==module, 'Supply inventories for every family module'
            row,_=select('Methods',q['Token']);row.update(Inventory=str(Path(family_inventory)),ScopeInventory=index[('Methods',token(q['Token']))][1],NewName=family['NewName'],Reason=reason+' '+family['Reason'])
    kept=[]
    for key,row in rows.items():
        if not row.get('NewName') and not row.get('ParameterNames') and not row.get('LocalNames'):continue
        if key[0]=='Methods':
            original=index[key][0];prior=mapped.get(key[1]);old={} if prior is None else {int(q.get('Index')):q.get('NewName') for q in prior.findall('Local')}
            missing=[dict(Index=q['Index'],ExpectedType=q['ExpectedType'],MissingEvidence='Retained generated/control or state-machine scaffold slot has no independently proven semantic source value in this block.') for q in original['LocalNames'] if not old.get(q['Index']) and str(q['Index']) not in row.get('LocalNames',{})]
            if missing:row['UnresolvedScopeEvidence']={'Locals':missing}
        kept.append(row)
    return dict(Format=1,TargetRoot=next(iter(roots)),ContractReferenceSha256=family_data['ContractReferenceSha256'],Inventories=[*inventory_data, str(Path(family_inventory))],Rows=kept)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('decisions','family','map','module','reason','spec','review'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--inventory',action='append',required=True);args=ap.parse_args()
    spec=build(read(args.decisions),args.inventory,args.family,args.map,args.module,args.reason)
    review=prepare(spec)
    for q,data in [(args.spec,spec),(args.review,review)]:
        with Path(q).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
    print('Prepared',len(spec['Rows']),'physical decisions; native map enforcement remains required.')
if __name__=='__main__':main()
