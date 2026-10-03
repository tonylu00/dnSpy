"""Prepare reviewed constructor scopes from native physical storage evidence.

Writes review/evidence JSON only; ETS code, binaries and XML maps are untouched.
"""
import argparse
import json
import pathlib
import re
import sqlite3
import xml.etree.ElementTree as ET
from prepare_physical_review import prepare
from prepare_sdk_property_storage_review import read, digest
from review_ledger import require_identity


def argument(instruction):
    code = instruction['OpCode']
    if code in ('ldarg.0', 'ldarg.1', 'ldarg.2', 'ldarg.3'):
        return int(code[-1])
    operand = instruction.get('Operand')
    if code in ('ldarg', 'ldarg.s', 'starg', 'starg.s', 'ldarga', 'ldarga.s') and isinstance(operand, dict):
        return operand.get('ArgumentIndex')
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('state', 'inventory', 'proposals', 'bodies', 'ledger', 'graph', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--preservations', help='Explicit reviewed meaningful-parameter preimages and rationale')
    args = parser.parse_args()
    state, inventory, proposals, index, ledger = map(read,
        (args.state, args.inventory, args.proposals, args.bodies, args.ledger))
    root = pathlib.Path(state['Pass']['SourceTree63']).resolve()
    assert str(root) == proposals['TargetRoot'] == ledger['TargetRoot']
    assert digest(state['Maps']['63']['Path']) == state['Maps']['63']['Sha256'] == inventory['MapSha256'] == proposals['BaseMapSha256']
    assert digest(args.ledger) == inventory['LedgerSha256']
    contracts = state['Compatibility']['ContractReferences63']
    assert digest(contracts['Path']) == contracts['Sha256']
    whitelist = state['Compatibility']['SdkWhitelist63']
    assert digest(whitelist['Path']) == whitelist['Sha256']
    protected = {(m.get('Path'), s.get('Token')) for m in ET.parse(whitelist['Path']).getroot() for s in m}
    modules = {m['Path']: m for m in inventory['Modules']}
    selected, excluded = [], []
    old = {(m['Module'], m['Token']): m for m in ledger['Methods']}
    for row in proposals['Methods']:
        key = (row['Module'], row['Token'])
        if key[0] not in modules or key in protected:
            excluded.append(dict(Module=key[0], Token=key[1], Reason='outside first-party scope' if key[0] not in modules else 'exact SDK whitelist token'))
            continue
        assert row['OriginalName'] == '.ctor' and not row['NewName'] and row['ScopedMappingBlocker'] is None
        assert key not in old, 'Existing reviewed scope requires a separate explicit merge decision'
        selected.append(row)
    wanted = {(r['Module'], r['Token']) for r in selected}
    assert len(wanted) == len(selected) and selected
    preservations = read(args.preservations) if args.preservations else []
    preserved = {}
    for entry in preservations:
        key = (entry['Module'], entry['Token'], entry['Sequence'])
        assert key[:2] in wanted and key not in preserved and entry['Reason']
        original = next(r for r in selected if (r['Module'], r['Token']) == key[:2])
        require_identity(entry, original)
        parameter = next(p for p in original['ParameterNames'] if p['Sequence'] == key[2])
        assert parameter['OriginalName'] == entry['ExpectedParameterName'] and parameter['NewName'] == entry['ExpectedProposal']
        preserved[key] = entry
    bodies = {}
    for entry in index:
        assert digest(entry['Path']) == entry['Sha256']
        document = read(entry['Path'])
        module = entry['Module']
        assert pathlib.Path(document['Input']).resolve() == (root / module).resolve()
        assert document['Sha256'] == modules[module]['Sha256'] == digest(root / module)
        assert document['Mvid'] == modules[module]['Mvid']
        for method in document['Methods']:
            key = (module, method['Token'])
            assert key not in bodies
            bodies[key] = method
    assert set(bodies) == wanted
    reports = [r for r in inventory['Reports'] if r['Module'] in {k[0] for k in wanted} and r['Kind'] in ('Fields', 'Methods')]
    field_keys = {(e['Module'], e['FieldToken']) for e in proposals['ConstructorParameterEvidence'] if (e['Module'], e['MethodToken']) in wanted}
    fields = {}
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
        if report['Kind'] == 'Fields':
            catalog = read(report['Path'])
            for field in catalog['Fields']:
                assert (pathlib.Path(catalog['TargetRoot']) / field['Module']).resolve() == (root / report['Module']).resolve()
                key = (report['Module'], field['Token'])
                if key in field_keys:
                    assert key not in fields
                    fields[key] = dict(field, Module=report['Module'])
    mapped = {(m.get('Path'), f.get('Token')): dict(f.attrib) for m in ET.parse(state['Maps']['63']['Path']).getroot() for f in m.findall('Field')}
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    physical = {pathlib.Path(m['Input']).resolve(): m for m in meta['Modules']}
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    rows, proof = [], []
    for row in selected:
        key = (row['Module'], row['Token'])
        body = bodies[key]
        assert row['Signature'] == body['Signature'] and not body['ExceptionHandlers']
        assert row['Sha256'] == modules[key[0]]['Sha256'] == physical[(root / key[0]).resolve()]['Sha256']
        assert row['Mvid'] == modules[key[0]]['Mvid'] == physical[(root / key[0]).resolve()]['Mvid']
        edits = {p['Sequence']: p['NewName'] for p in row['ParameterNames'] if p['NewName']}
        assert edits
        parameter_proof = []
        for sequence, name in edits.items():
            evidence = [e for e in proposals['ConstructorParameterEvidence'] if
                        (e['Module'], e['MethodToken'], e['ParameterSequence']) == (*key, sequence)]
            assert evidence
            metadata = next(p for p in body['Parameters'] if p['Sequence'] == sequence)
            uses = [dict(Instruction=i, Context=body['Instructions'][max(0, n-1):n+4])
                    for n, i in enumerate(body['Instructions']) if argument(i) == sequence]
            assert uses and metadata['Name'] == evidence[0]['OriginalParameterName']
            for e in evidence:
                field = fields[(key[0], e['FieldToken'])]
                assert field['Signature'] == e['FieldSignature'] and field['Type'] == row['Type']
                assert e['ProposedName'] == name and e['MethodSignature'] == row['Signature']
                if e['RoleSource'] == 'checked-source-alias':
                    mapping = mapped[(key[0], e['FieldToken'])]
                    assert mapping['Signature'] == field['Signature'] and mapping['ExpectedName'] == field['OriginalName'] and mapping['NewName'] == name
                else:
                    assert e['RoleSource'] == 'existing-metadata-name'
                    assert field['OriginalName'].lstrip('_').lower() == name.lower()
                instructions = [i for i in body['Instructions'] if i['OpCode'] != 'nop']
                assert any(i['OpCode'] == 'stfld' and isinstance(i['Operand'], dict) and i['Operand'].get('Token') == e['FieldToken'] and
                           n >= 2 and instructions[n-2]['OpCode'] == 'ldarg.0' and argument(instructions[n-1]) == sequence
                           for n, i in enumerate(instructions))
            preservation = preserved.get((*key, sequence))
            parameter_proof.append(dict(Sequence=sequence, ProposedAlias=name, AcceptedAlias='' if preservation else name,
                                        Preservation=preservation, Storage=evidence, AllInputUses=uses))
        accepted = {sequence: name for sequence, name in edits.items() if (*key, sequence) not in preserved}
        preserve_reason = ' '.join(e['Reason'] for k, e in preserved.items() if k[:2] == key)
        rows.append(dict(Kind='Methods', Module=key[0], Token=key[1], ParameterNames=accepted,
            Disposition='rename' if accepted else 'preserve',
            Reason='Reviewed unchanged constructor inputs stored directly in physically checked field roles: ' +
            ', '.join(accepted.values()) + '. ' + preserve_reason + ' Other input uses and incoming references are retained in evidence. '
            'Preserve .ctor/runtime parameter metadata, meaningful existing names, unproposed parameters and body locals. '
            'Opaque owner names and remaining scopes require their own behavioral evidence; this review does not infer those roles.'))
        incoming = [dict(Source=s, Reference=json.loads(d)) for s, d in graph.execute('select source,data from edges where target=?',
                    (physical[(root / key[0]).resolve()]['Id'] + ':' + key[1],))]
        proof.append(dict(Module=key[0], Token=key[1], Signature=row['Signature'], Parameters=parameter_proof,
                          Body=body, PhysicalIncomingReferences=incoming))
    spec = dict(Format=1, TargetRoot=str(root), ContractReferenceSha256=contracts['Sha256'], Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    proposed = {(r['Module'], r['Token']): r for r in selected}
    for row in review['Methods']:
        require_identity(proposed[(row['Module'], row['Token'])], row)
        # Scoped uncertainty is recorded by physical position rather than hidden
        # behind a supported constructor/parameter decision. Domain parameter
        # spellings remain intact; generic typed/short placeholders need proof.
        row['UnresolvedScopeEvidence'] = dict(
            Parameters=[dict(Sequence=p['Sequence'], OriginalName=p['OriginalName'],
                MissingEvidence='No reviewed storage role or named forwarding/caller proof for this input in the current block; preserve metadata and review its owning call chain.')
                for p in row['ParameterNames'] if not p['NewName'] and (row['Module'], row['Token'], p['Sequence']) not in preserved and (p['OriginalName'] or '').lower() not in
                {'id', 'uid', 'rid', 'ip', 'xml', 'url', 'uri', 'mac', 'ttl', 'crc', 'min', 'max', 'key', 'end', 'row', 'idx', 'src', 'dst', 'pos', 'len', 'msg', 'tag', 'sum', 'low'} and
                re.fullmatch(r'(?:A_[0-9]+|(?:string|bool|byte|ushort|uint|short|int|long|double|char|ienumerable|ilist|dictionary|class[0-9]+|interface[0-9]+)_[0-9]+|[a-zA-Z]{1,3})', p['OriginalName'] or '')],
            Locals=[dict(Index=p['Index'], ExpectedType=p['ExpectedType'],
                MissingEvidence='Owning expression, control flow and use sites need behavioral review; no local role was inferred from slot number or type alone.')
                for p in row['LocalNames'] if not p['NewName']])
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    version = state['Maps']['63']['NextWave']
    evidence = dict(Format=1, Kind='ConstructorParameterEvidence', BaseMapSha256=proposals['BaseMapSha256'],
        Inputs=[dict(Path=p, Sha256=digest(p)) for p in (args.state, args.inventory, args.proposals, args.bodies, args.ledger, args.graph, *([args.preservations] if args.preservations else []))],
        NativeBodyReports=index, GraphInputsVerified=len(meta['Modules']), Constructors=proof, Excluded=excluded,
        PreservedParameterDecisions=preservations,
        Limits='Reviewed constructor scopes only. No new method/type/field/local aliases, binary application, ETS export/build or observed unchanged-App compatibility.')
    for name, document in ((f'constructor-parameter-spec-v{version}', spec), (f'constructor-parameter-review-v{version}', review),
                           (f'constructor-parameter-evidence-v{version}', evidence)):
        with (output / (name + '.json')).open('x', encoding='utf-8') as stream:
            json.dump(document, stream, indent=2)
            stream.write('\n')
    print(dict(Constructors=len(selected), Parameters=sum(len(r['ParameterNames']) for r in rows), Modules=len({r['Module'] for r in rows}), Excluded=len(excluded)))


if __name__ == '__main__':
    main()
