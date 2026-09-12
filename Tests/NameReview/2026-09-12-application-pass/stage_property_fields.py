"""Stage verified field/property-access proposals for unreadable visible source.

Usage: stage_property_fields.py GRAPH_DB PROPOSALS NEW_REVIEW [MANUAL_LEDGER ...]
The .NET scanner supplies field-access evidence. This pass binds it to the physical
source graph and its unchanged files, preserving readable source and prior
manual decisions. It does not apply aliases or build/export the application.
"""
import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ApplicationNameGraph'))
from review_candidates import source_review_reasons

def stage(database, proposals, output, ledgers=()):
    database,proposals,output=map(Path,(database,proposals,output))
    assert not output.exists(), 'Choose a new review output'
    inventory=json.loads(proposals.read_text(encoding='utf-8-sig'))
    assert inventory['Format']==1 and inventory['Kind']=='SymbolReview'
    accessor=inventory.get('InferenceKind')=='FieldAccessor'
    assert not inventory['Types'] and not inventory['Fields' if accessor else 'Methods'], 'Expected one inference kind only'
    with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        result=select_fields(db,database,proposals,inventory,ledgers)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(f'Staged {len(result["Fields"])+len(result["Methods"])} visible roles from field/property-access evidence; {len(result["SourceExclusions"])} proposals excluded by source/manual scope. No source or binary changes.')

def select_fields(db,database,proposals,inventory,ledgers):
    manifest=json.loads(db.execute('SELECT data FROM meta').fetchone()[0])
    source_root=Path(manifest['Export']).resolve().parent
    input_root=Path(inventory['TargetRoot']).resolve()
    modules={Path(m['Input']).resolve():m for m in manifest['Modules']}
    assert len(modules)==len(manifest['Modules']), 'Duplicate physical graph modules'
    manual={m['Id'] for path in ledgers for d in json.loads(Path(path).read_text())['Decisions'] for m in d['Members']}
    accessor=inventory.get('InferenceKind')=='FieldAccessor'
    category,kind,evidence_name,proof_token=('Methods','Method','FieldAccessorEvidence','MethodToken') if accessor else ('Fields','Field','PropertyEvidence','FieldToken')
    evidence={(e['Module'],e[proof_token]):e for e in inventory[evidence_name]}
    assert len(evidence)==len(inventory[evidence_name])==len(inventory[category]), 'Expected one access proof per proposal'
    fields=[]; accepted_evidence=[]; source_evidence=[]; exclusions=[]; hashes={}; seen=set()
    for field in inventory[category]:
        key=(field['Module'],field['Token'])
        assert key not in seen, ('Duplicate proposal',key)
        seen.add(key)
        physical=(input_root/field['Module']).resolve()
        assert physical.is_relative_to(input_root), 'Proposal leaves input root'
        module=modules.get(physical)
        if module is None:
            exclusions.append({'Module':field['Module'],'Token':field['Token'],'Reason':'No source module at this physical path in the graph'}); continue
        assert module['Mvid']==field['Mvid'] and module['Sha256']==field['Sha256'], ('Stale physical module',physical)
        symbol_id=module['Id']+':'+field['Token']
        if symbol_id in manual:
            exclusions.append({'Id':symbol_id,'Reason':'Existing manual decision preserved'}); continue
        symbol_row=db.execute('SELECT data FROM symbols WHERE id=?',(symbol_id,)).fetchone()
        assert symbol_row, ('Missing graph symbol',symbol_id)
        symbol=json.loads(symbol_row[0])
        assert symbol['Kind']==kind and symbol['OriginalName']==field['OriginalName'] and symbol['Signature']==field['Signature'], ('Symbol identity mismatch',symbol_id)
        declarations=[json.loads(row[0]) for row in db.execute('SELECT data FROM source WHERE id=?',(symbol_id,))]
        if not declarations:
            exclusions.append({'Id':symbol_id,'Reason':f'No emitted source {kind.lower()} declaration'}); continue
        if not all(source_review_reasons(symbol,row) for row in declarations):
            exclusions.append({'Id':symbol_id,'Reason':f'Existing source {kind.lower()} name is already readable'}); continue
        proof=evidence[key]
        if accessor:
            assert proof['MethodSignature']==symbol['Signature'], ('Accessor identity mismatch',symbol_id)
        getter_id=module['Id']+':'+proof['FieldToken' if accessor else 'GetterToken']
        getter_row=db.execute('SELECT data FROM symbols WHERE id=?',(getter_id,)).fetchone()
        assert getter_row and json.loads(getter_row[0])['Signature']==proof['FieldSignature' if accessor else 'GetterSignature'], ('Access evidence identity mismatch',getter_id)
        for row in declarations:
            path=(source_root/row['Source']).resolve()
            assert path.is_relative_to(source_root), 'Source leaves export root'
            if path not in hashes: hashes[path]=hashlib.sha256(path.read_bytes()).hexdigest().upper()
            assert hashes[path]==row['Sha256'].upper(), ('Stale source',path)
        fields.append(field); accepted_evidence.append(proof)
        source_evidence.append({'Id':symbol_id,'Declarations':[{k:r[k] for k in ('Source','Name','Line','Sha256')} for r in declarations],
                                'Status':'staged from field/property-access evidence; not applied'})
    result=dict(inventory,SourceEvidence=source_evidence,
                SourceExclusions=exclusions,Graph=str(database),ProposalSha256=hashlib.sha256(proposals.read_bytes()).hexdigest(),
                ApplicationStatus='staged; full application-wide naming pass remains incomplete')
    result[category]=fields
    result[evidence_name]=accepted_evidence
    return result

if __name__=='__main__': stage(*sys.argv[1:4],sys.argv[4:])
