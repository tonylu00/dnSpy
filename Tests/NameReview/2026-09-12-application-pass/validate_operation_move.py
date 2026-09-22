"""Validate the reviewed move scopes against exact maps, sources and IL edges.

Usage: python validate_operation_move.py ARTIFACT_ROOT
Creates fresh checkpoint evidence only; never applies names to ETS.
"""
from pathlib import Path
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from behavior_review import sha
from operation_move_scopes import SCOPES


def validate(root):
    checks, caller_edges = [], []
    for version, stem, number in [
        ('63', 'operations63-wave203', 204),
        ('64', 'operations64-wave32', 32),
    ]:
        with sqlite3.connect((root / f'graph{version}-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
            source = Path(json.loads(db.execute('SELECT data FROM meta').fetchone()[0])['Export']).parent
        read = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
        review, evidence = read(stem + '.review.json'), read(stem + '.evidence.json')
        update = read(f'map-update{version}-wave-{number}.json')
        preflight = read(f'map-check{version}-wave{number}.json')
        assert update['Success'] and not update['Errors']
        assert all(c['Requested'] == c['Applied'] for c in update['Changes'])
        assert preflight['Success'] and not preflight['Changes'] and not preflight['Errors']
        physical = evidence['PhysicalModule']
        assert sha(Path(physical['Input'])) == physical['Sha256']
        doc = ET.parse(root / f'names{version}-staged-v{number}.xml').getroot()
        modules = {m.get('Path'): m for m in doc}
        for kind in ('Methods', 'Types', 'Fields'):
            for row in review[kind]:
                module = modules[row['Module']]
                assert all(module.get(k) == row[k] for k in ('Mvid', 'Sha256'))
                mapped = next(r for r in module if r.tag == kind[:-1] and r.get('Token') == row['Token'])
                assert mapped.get('Signature') == row['Signature']
                assert mapped.get('NewName') == row['NewName']
                for values, tag, position in [('ParameterNames', 'Parameter', 'Sequence'), ('LocalNames', 'Local', 'Index')]:
                    scoped = {int(p.get(position)): p for p in mapped.findall(tag)}
                    for p in row.get(values, []):
                        if not p.get('NewName'):
                            continue
                        if tag == 'Parameter' and p['NewName'] == p['OriginalName'] and p[position] not in scoped:
                            continue
                        assert scoped[p[position]].get('NewName') == p['NewName']
            checks.append({'Review': stem, 'Kind': kind, 'Decisions': len(review[kind])})
        for decision in evidence['Decisions']:
            assert decision['Source']
            for reference in decision['Source']:
                assert sha(source / reference['Path']) == reference['Sha256']
            if 'IL' in decision:
                assert sha(Path(decision['IL']['Path'])) == decision['IL']['Sha256']

        full = read(stem + '-inspection.json')
        assert all(full[k] == physical[k] for k in ('Input', 'Mvid', 'Sha256'))
        bodies = {m['Token']: m for m in full['Methods']}
        caller = physical['Id'] + (':0x06004C82' if version == '63' else ':0x060067C2')
        body = bodies[caller.split(':')[1]]
        with sqlite3.connect((root / f'graph{version}-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
            for _, p63, p64, *_ in SCOPES[1:]:
                token = f'0x0600{p63 if version == "63" else p64:04X}'
                edges = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE source=? AND target=?', (caller, physical['Id'] + ':' + token))]
                assert edges
                for edge in edges:
                    ins = next(i for i in body['Instructions'] if i['Offset'] == edge['Offset'])
                    assert ins['OpCode'] == edge['Operation'] and ins['Operand']['Text'] == edge['Target']['Signature']
                    assert Path(edge['Target']['PhysicalModule']).resolve() == Path(physical['Input']).resolve()
                caller_edges.extend(edges)

    # Compiler/obfuscator sentinel helpers have no demonstrated domain role.
    # Keep exact fields, IL and incoming uses visible instead of inventing names.
    full = read('operations64-wave32-inspection.json')
    bodies = {m['Token']: m for m in full['Methods']}
    inventory = read('operations64-wave32-methods.json')
    fields = read('operations64-wave32-fields.json')
    selected = read('operations64-wave32-unresolved.json')
    tokens = {m['Token'] for m in selected['Methods']} | {'0x060067E4', '0x060067E5'}
    unresolved = {'PhysicalModule': selected['PhysicalModule'], 'Methods': [], 'Fields': []}
    with sqlite3.connect((root / 'graph64-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
        field_tokens = set()
        for row in inventory['Methods']:
            if row['Token'] not in tokens:
                continue
            body = bodies[row['Token']]
            assert body['Signature'] == row['Signature']
            incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', ('m0146:' + row['Token'],))]
            assert not incoming
            unresolved['Methods'].append({**row, 'Unresolved': True, 'UnresolvedReason': 'Static null/sentinel helper; no application caller or domain role demonstrated.', 'IncomingUses': incoming, 'IL': body})
            field_tokens.update(i['Operand']['Token'] for i in body['Instructions'] if i['OpCode'] == 'ldsfld')
        for row in fields['Fields']:
            if row['Token'] not in field_tokens:
                continue
            incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', ('m0146:' + row['Token'],))]
            assert all(e['From'].split(':')[1] in tokens for e in incoming)
            unresolved['Fields'].append({**row, 'Unresolved': True, 'UnresolvedReason': 'Self-typed static field used only by the unresolved sentinel helpers.', 'IncomingUses': incoming})
    assert len(unresolved['Methods']) == 16 and len(unresolved['Fields']) == 8
    report = {
        'Checks': checks, 'PhysicalCallerEdges': caller_edges,
        'ToolCommit': '5470ad2b',
        'ToolValidation': 'NameCandidates full suite and dnSpy SourceFieldAliasRegression passed on Windows, including original-name restoration and real peer/inherited collisions. No macOS/Linux execution.',
        'RejectedMap': 'names63-staged-v203.xml: 11 self-collision suffixes. Never checkpointed or used as a base. v204 is rebuilt from accepted v202 with the same reviewed decisions.',
        'AppliedToSource': False, 'EtsRuntimeExecuted': False,
        'UnresolvedMethods': 16, 'UnresolvedFields': 8,
        'BehaviorNotes': [
            'Cross-project planners return ordered copy/move then delete operations; they do not execute them.',
            'Project branching uses reference identity. Deletion password callbacks still check the target project.',
            'Line strategies preserve WithOffset across projects and FirstFree within one project.',
            'Segment imports use the source store; deletion filters concrete Segment instances.',
            'Building/range moves reject same-project Installation targets, while trade moves still construct MoveTradeOperation.',
            'Device moves cast every source item; same-project targets select segment, line main segment, building part or trade links. Unsupported targets return null.',
            'Option lookup uses a GeneralOption.Lose fallback without appending it.',
            'Progress publishes then invokes the callback without a null guard; 6.4 retains its explicit object cast.',
            'Certificate message-bus construction is fresh on each invocation.',
            'Confirmation methods retain nullable and OK/Yes handling; the group count threshold is strictly less than the limit.',
        ],
    }
    for filename, data in [('operations-wave204-validation.json', report), ('operations64-wave32-unresolved-complete.json', unresolved)]:
        with (root / filename).open('x', encoding='utf-8', newline='\n') as output:
            json.dump(data, output, indent=2)
            output.write('\n')
    print('Validated exact decisions, used scopes, source/IL hashes, physical caller edges and explicit unresolved helpers.')


if __name__ == '__main__':
    validate(Path(sys.argv[1]))
