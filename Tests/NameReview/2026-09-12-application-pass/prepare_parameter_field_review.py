"""Bind explicit constructor-storage decisions to physical IL and graph evidence.

Writes review, inspection requests and evidence JSON only. Native tools own maps,
source aliases and runtime-name restoration; this script never changes ETS code.
"""
import argparse
import json
import pathlib
import sqlite3
import xml.etree.ElementTree as ET
from prepare_physical_review import prepare
from prepare_constructor_parameter_review import argument
from prepare_sdk_property_storage_review import read, digest
from review_ledger import require_identity


def select_fields(proposals, modules, protected, mapped):
    selected, excluded = [], []
    seen = set()
    for row in proposals['Fields']:
        key = (row['Module'], row['Token'])
        assert key not in seen
        seen.add(key)
        if key[0] not in modules or key in protected:
            excluded.append(dict(Module=key[0], Token=key[1], Reason=
                'outside first-party physical scope' if key[0] not in modules else 'exact SDK whitelist token'))
            continue
        assert key not in mapped and row['NewName'] and not row['MappingBlocker']
        selected.append(row)
    return selected, excluded


def validate_decisions(selected, decisions):
    wanted = {(r['Module'], r['Token']): r for r in selected}
    result = {}
    for decision in decisions:
        key = (decision['Module'], decision['Token'])
        assert key in wanted and key not in result and decision['Reason']
        require_identity(wanted[key], decision)
        assert decision['ExpectedProposal'] == wanted[key]['NewName']
        assert decision['Disposition'] in ('rename', 'preserve', 'unresolved')
        assert bool(decision.get('NewName')) == (decision['Disposition'] == 'rename')
        result[key] = decision
    assert result.keys() == wanted.keys(), 'Every proposed field needs an explicit domain decision'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('state', 'inventory', 'proposals', 'ledger', 'graph', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--bodies', help='Hash-bound native method report index')
    parser.add_argument('--decisions', help='Explicit physical field decisions with domain rationale')
    args = parser.parse_args()
    assert bool(args.bodies) == bool(args.decisions), 'Supply both bodies and decisions, or collect requests first'
    state, inventory, proposals, ledger = map(read, (args.state, args.inventory, args.proposals, args.ledger))
    root = pathlib.Path(state['Pass']['SourceTree63']).resolve()
    assert str(root) == proposals['TargetRoot'] == ledger['TargetRoot']
    assert proposals['InferenceKind'] == 'ParameterField'
    assert digest(state['Maps']['63']['Path']) == state['Maps']['63']['Sha256'] == inventory['MapSha256'] == proposals['BaseMapSha256']
    assert digest(args.ledger) == inventory['LedgerSha256']
    contracts = state['Compatibility']['ContractReferences63']
    whitelist = state['Compatibility']['SdkWhitelist63']
    assert digest(contracts['Path']) == contracts['Sha256']
    assert digest(whitelist['Path']) == whitelist['Sha256']
    protected = {(m.get('Path'), s.get('Token')) for m in ET.parse(whitelist['Path']).getroot() for s in m}
    mapping = ET.parse(state['Maps']['63']['Path']).getroot()
    mapped = {(m.get('Path'), r.get('Token')): r for m in mapping for r in m if r.get('NewName')}
    scoped = {(m.get('Path'), r.get('Token')): r for m in mapping for r in m.findall('Method')}
    modules = {m['Path']: m for m in inventory['Modules']}
    selected, excluded = select_fields(proposals, modules, protected, mapped)
    assert selected
    previous = {(r['Module'], r['Token']): r for r in ledger['Fields']}
    assert all((r['Module'], r['Token']) not in previous for r in selected), 'Historical field decision needs a separate guarded transition'
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    by_id = {m['Id']: m for m in meta['Modules']}
    physical = {pathlib.Path(m['Input']).resolve(): m for m in meta['Modules']}
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    requests, proof = {}, []

    def references(module, token):
        return [dict(Source=s, Reference=json.loads(d)) for s, d in graph.execute(
            'select source,data from edges where target=?', (module['Id'] + ':' + token,))]

    def request_source(edge):
        ident, token = edge['Source'].rsplit(':', 1)
        if token.startswith('0x06'):
            path = pathlib.Path(by_id[ident]['Input']).resolve()
            relative = path.relative_to(root).as_posix()
            requests.setdefault(relative, set()).add(token)

    for field in selected:
        key = (field['Module'], field['Token'])
        module = physical[(root / key[0]).resolve()]
        assert field['Sha256'] == modules[key[0]]['Sha256'] == module['Sha256']
        assert field['Mvid'] == modules[key[0]]['Mvid'] == module['Mvid']
        stores = [e for e in proposals['ParameterFieldEvidence'] if (e['Module'], e['FieldToken']) == key]
        assert stores and all(e['FieldSignature'] == field['Signature'] and e['ProposedName'] == field['NewName'] for e in stores)
        incoming = references(module, key[1])
        callers = []
        for store in stores:
            requests.setdefault(key[0].replace('\\', '/'), set()).add(store['ConstructorToken'])
            callers.extend(references(module, store['ConstructorToken']))
        for edge in incoming + callers:
            request_source(edge)
        proof.append(dict(Field=field, Stores=stores, IncomingReferences=incoming, ConstructorCallers=callers))
    requests = {k: sorted(v) for k, v in sorted(requests.items())}
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if not args.bodies:
        for name, doc in (('parameter-field-body-requests', requests), ('parameter-field-selection', proof)):
            with (output / (name + '.json')).open('x', encoding='utf-8') as stream:
                json.dump(doc, stream, indent=2); stream.write('\n')
        print(dict(Fields=len(selected), Excluded=len(excluded), PhysicalModules=len(requests), Methods=sum(map(len, requests.values()))))
        return
    decisions = validate_decisions(selected, read(args.decisions))
    index, bodies = read(args.bodies), {}
    for entry in index:
        assert digest(entry['Path']) == entry['Sha256']
        document = read(entry['Path'])
        relative = entry['Module'].replace('\\', '/')
        path = (root / relative).resolve()
        assert pathlib.Path(document['Input']).resolve() == path
        assert document['Sha256'] == physical[path]['Sha256'] == digest(path)
        assert document['Mvid'] == physical[path]['Mvid']
        for method in document['Methods']:
            key = (relative, method['Token'])
            assert key not in bodies
            bodies[key] = method
    assert all((module, token) in bodies for module, tokens in requests.items() for token in tokens)
    rows = []
    for entry in proof:
        field = entry['Field']; key = (field['Module'], field['Token']); relative = key[0].replace('\\', '/')
        decision = decisions[key]
        for store in entry['Stores']:
            body = bodies[(relative, store['ConstructorToken'])]
            assert body['Signature'] == store['ConstructorSignature'] and not body['ExceptionHandlers']
            parameter = next(p for p in body['Parameters'] if p['Sequence'] == store['ParameterSequence'])
            assert parameter['Name'] == store['OriginalParameterName']
            if store['RoleSource'] == 'checked-source-alias':
                method = scoped[(key[0], store['ConstructorToken'])]
                scope = next(p for p in method.findall('Parameter') if int(p.get('Sequence')) == store['ParameterSequence'])
                assert method.get('Signature') == body['Signature'] and scope.get('ExpectedName') == parameter['Name'] and scope.get('NewName') == field['NewName']
            else:
                assert store['RoleSource'] == 'existing-metadata-name' and parameter['Name'] == field['NewName']
            il = [i for i in body['Instructions'] if i['OpCode'] != 'nop']
            assert any(i['OpCode'] == 'stfld' and isinstance(i['Operand'], dict) and i['Operand'].get('Token') == key[1] and
                       n >= 2 and il[n-2]['OpCode'] == 'ldarg.0' and argument(il[n-1]) == parameter['ArgumentIndex'] for n, i in enumerate(il))
        related = {(relative, e['ConstructorToken']) for e in entry['Stores']}
        for edge in entry['IncomingReferences'] + entry['ConstructorCallers']:
            ident, token = edge['Source'].rsplit(':', 1)
            if token.startswith('0x06'):
                source = pathlib.Path(by_id[ident]['Input']).resolve().relative_to(root).as_posix()
                related.add((source, token))
        entry['RelatedMethodKeys'] = [dict(Module=m, Token=t) for m, t in sorted(related)]
        entry['Decision'] = decision
        rows.append(dict(Kind='Fields', Module=key[0], Token=key[1], Disposition=decision['Disposition'],
            NewName=decision.get('NewName', ''), Reason=field['Reason'] + '. Domain review: ' + decision['Reason'] +
            ' All resolved field references, constructor stores and incoming constructor callers are retained in the physical evidence. '
            'Keep runtime metadata and reflection/serialization/resource contracts; this decision does not resolve other owner or method scopes.'))
    reports = [r for r in inventory['Reports'] if r['Kind'] == 'Fields' and r['Module'] in {r['Module'] for r in selected}]
    assert len(reports) == len({r['Module'] for r in selected})
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    spec = dict(Format=1, TargetRoot=str(root), ContractReferenceSha256=contracts['Sha256'], Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    source = {(r['Module'], r['Token']): r for r in selected}
    for row in review['Fields']:
        require_identity(source[(row['Module'], row['Token'])], row)
    version = state['Maps']['63']['NextWave']
    evidence = dict(Format=1, Kind='ParameterFieldEvidence', BaseMapSha256=proposals['BaseMapSha256'],
        Inputs=[dict(Path=p, Sha256=digest(p)) for p in (args.state, args.inventory, args.proposals, args.bodies, args.decisions, args.ledger, args.graph)],
        NativeBodyReports=index, GraphInputsVerified=len(meta['Modules']), Fields=proof, Excluded=excluded,
        RelatedMethods=[dict(Module=m, Method=bodies[(m, t)]) for m, tokens in requests.items() for t in tokens],
        Limits='Reviewed private constructor-bound storage only. Visible IL stores do not establish reflection absence or immutability. No method/type/parameter/local renames, ETS export/build or observed App compatibility.')
    for name, doc in ((f'parameter-field-spec-v{version}', spec), (f'parameter-field-review-v{version}', review), (f'parameter-field-evidence-v{version}', evidence)):
        with (output / (name + '.json')).open('x', encoding='utf-8') as stream:
            json.dump(doc, stream, indent=2); stream.write('\n')
    print(dict(Fields=len(rows), Renames=sum(r['Disposition'] == 'rename' for r in rows), Modules=len(reports), Methods=sum(map(len, requests.values())), Excluded=len(excluded)))


if __name__ == '__main__':
    main()
