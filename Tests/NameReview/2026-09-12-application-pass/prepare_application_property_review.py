"""Bind reviewed property storage/accessors to physical IL, families and contracts.

Only review inputs and evidence are written. Native tools produce/check the map.
"""
import argparse
import json
import pathlib
import sqlite3
import xml.etree.ElementTree as ET
from prepare_physical_review import prepare
from review_ledger import require_identity, proposal_preimage
from prepare_sdk_property_storage_review import read, digest


def select_accessors(accessors, properties, protected):
    """Expand whole native families, then exclude exact SDK tokens indivisibly."""
    rows = {(r['Module'], r['Token']): r for r in accessors['Methods']}
    evidence = {(e['Module'], e['MethodToken']): e for e in accessors['AccessorEvidence']}
    families = {f['Id']: f for f in accessors['Families']}
    selected = {key for key, e in evidence.items() if e['OwnerKind'] == 'Property' and
                (e['Module'], e['OwnerToken']) in properties and not e['MappedName']}
    touched = {rows[k]['ContractFamily'] for k in selected if rows[k]['ContractFamily']}
    for family in touched:
        family = families[family]
        assert not family['Blockers'] and len({m['DerivedName'] for m in family['Members']}) == 1
        assert all(not m['MappedName'] for m in family['Members'])
        selected.update((m['Module'], m['Token']) for m in family['Members'])
    excluded_families = {rows[k]['ContractFamily'] for k in selected if k in protected and rows[k]['ContractFamily']}
    excluded = sorted(k for k in selected if k in protected or rows[k]['ContractFamily'] in excluded_families)
    selected.difference_update(excluded)
    return selected, {rows[k]['ContractFamily'] for k in selected if rows[k]['ContractFamily']}, excluded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('state', 'inventory', 'proposals', 'bodies', 'accessors', 'ledger', 'graph', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--clarifications', help='Explicit physical field preimages, role evidence and inspected-input hashes')
    args = parser.parse_args()
    state, inventory, proposals, body_index, accessors, ledger = map(read,
        (args.state, args.inventory, args.proposals, args.bodies, args.accessors, args.ledger))
    root = pathlib.Path(state['Pass']['SourceTree63']).resolve()
    base_sha = state['Maps']['63']['Sha256']
    assert base_sha == digest(state['Maps']['63']['Path']) == inventory['MapSha256'] == proposals['BaseMapSha256'] == accessors['BaseMapSha256']
    assert ledger['TargetRoot'] == proposals['TargetRoot'] == accessors['TargetRoot'] == str(root)
    assert digest(args.ledger) == inventory['LedgerSha256']
    contract = state['Compatibility']['ContractReferences63']
    assert digest(contract['Path']) == contract['Sha256'] == accessors['ContractReferenceSha256']
    whitelist = state['Compatibility']['SdkWhitelist63']
    assert digest(whitelist['Path']) == whitelist['Sha256']
    protected = {(m.get('Path'), s.get('Token')) for m in ET.parse(whitelist['Path']).getroot() for s in m}
    modules = {m['Path']: m for m in inventory['Modules']}
    old = {kind: {(r['Module'], r['Token']): r for r in ledger[kind]} for kind in ('Fields', 'Methods')}
    mapped = {(m.get('Path'), r.get('Token')) for m in ET.parse(state['Maps']['63']['Path']).getroot().findall('Module')
              for r in m if r.get('NewName')}
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    physical_graph = {pathlib.Path(m['Input']).resolve(): m for m in meta['Modules']}
    for m in meta['Modules']:
        assert digest(m['Input']) == m['Sha256']
    getters = {}
    for entry in body_index:
        assert digest(entry['Path']) == entry['Sha256']
        doc = read(entry['Path'])
        physical = (root / entry['Module']).resolve()
        assert pathlib.Path(doc['Input']).resolve() == physical
        assert doc['Sha256'] == modules[entry['Module']]['Sha256'] == digest(physical)
        assert doc['Mvid'] == modules[entry['Module']]['Mvid']
        for method in doc['Methods']:
            key = (entry['Module'], method['Token'])
            assert key not in getters
            getters[key] = method
    fields = [r for r in proposals['Fields'] if r['Module'] in modules]
    field_keys = {(r['Module'], r['Token']) for r in fields}
    assert len(field_keys) == len(fields) and fields
    clarifications = read(args.clarifications) if args.clarifications else []
    clarified = {}
    for item in clarifications:
        key = (item['Module'], item['Token'])
        assert key in field_keys and key not in clarified and item['Reason'] and item['NewName']
        assert item['NewName'] != item['ExpectedProposal'] and item['InspectedInputs']
        for document in item['InspectedInputs']:
            assert digest(document['Path']) == document['Sha256']
        clarified[key] = item
    properties, rows, proof = set(), [], []

    def references(key, row):
        assert key not in protected and key not in mapped, 'Protected or already mapped definition: ' + str(key)
        physical = (root / key[0]).resolve()
        assert row['Sha256'] == modules[key[0]]['Sha256'] == physical_graph[physical]['Sha256']
        assert row['Mvid'] == modules[key[0]]['Mvid'] == physical_graph[physical]['Mvid']
        return [dict(Source=s, Reference=json.loads(d)) for s, d in graph.execute(
            'select source,data from edges where target=?', (physical_graph[physical]['Id'] + ':' + key[1],))]

    for row in fields:
        key = (row['Module'], row['Token'])
        assert key not in old['Fields'] and not row['MappingBlocker']
        incoming = references(key, row)
        assert incoming
        evidence = [e for e in proposals['PropertyEvidence'] if (e['Module'], e['FieldToken']) == key]
        assert len(evidence) == 1
        evidence = evidence[0]
        getter = getters[(key[0], evidence['GetterToken'])]
        assert getter['Signature'] == evidence['GetterSignature']
        assert any(o['OwnerKind'] == 'Property' and o['OwnerToken'] == evidence['PropertyToken'] and
                   o['OwnerName'] == evidence['PropertyName'] and o['OwnerSignature'] == evidence['PropertySignature'] and
                   o['AccessorRole'] == 'get' for o in getter['AccessorOwners'])
        assert any(i['OpCode'] in ('ldfld', 'ldsfld') and isinstance(i['Operand'], dict) and
                   i['Operand'].get('Token') == key[1] for i in getter['Instructions'])
        properties.add((key[0], evidence['PropertyToken']))
        clarification = clarified.get(key)
        if clarification:
            require_identity(row, clarification)
            assert clarification['ExpectedProposal'] == row['NewName']
        accepted_name = clarification['NewName'] if clarification else row['NewName']
        detail = ' Reviewed storage distinction: ' + clarification['Reason'] if clarification else ''
        rows.append(dict(Kind='Fields', Module=key[0], Token=key[1], NewName=accepted_name,
            Reason=row['Reason'] + '. Reviewed domain role: ' + evidence['PropertyName'] +
            '. Every normal return reloads this exact physical field; retain guards, initialization, setter logic and runtime metadata. '
            'Public property spelling is preserved. Exact SDK tokens and external contracts remain enforced.' + detail))
        proof.append(dict(Module=key[0], FieldToken=key[1], Property=evidence, GetterSignature=getter['Signature'],
                          IncomingReferences=incoming, AcceptedName=accepted_name, Clarification=clarification))
    accessor_rows = {(r['Module'], r['Token']): r for r in accessors['Methods']}
    accessor_evidence = {(e['Module'], e['MethodToken']): e for e in accessors['AccessorEvidence']}
    families = {f['Id']: f for f in accessors['Families']}
    selected, touched, excluded = select_accessors(accessors, properties, protected)
    method_proof, preimages = [], []
    for key in sorted(selected):
        row = accessor_rows[key]
        assert key[0] in modules and not row['MappingBlocker']
        incoming = references(key, row)
        evidence = accessor_evidence[key]
        assert evidence['DerivedName'] == row['NewName'] and not evidence['MappedName']
        assert not evidence['FamilyBlockers']
        decision = dict(Kind='Methods', Module=key[0], Token=key[1], NewName=row['NewName'],
            Reason=row['Reason'] + '. The exact property row and accessor signature prove conventional C# ownership. '
            'Complete editable physical interface/override families are included together; preserve runtime special names and public property contracts.')
        previous = old['Methods'].get(key)
        if previous:
            require_identity(previous, row)
            preimages.append(previous)
            if previous.get('Unresolved'):
                assert not previous.get('NewName')
                decision.update(ResolveExistingUnresolved=True,
                    PreviousUnresolvedEvidence={k: previous.get(k, '') for k in ('Reason', 'UnresolvedReason')})
            else:
                assert previous['NewName'] == row['NewName']
                decision.update(ApplyExistingProposal=True, PreviousProposalEvidence=proposal_preimage(previous))
            for label, position in (('ParameterNames', 'Sequence'), ('LocalNames', 'Index')):
                decision[label] = {p[position]: p['NewName'] for p in previous.get(label, []) if p.get('NewName')}
        rows.append(decision)
        method_proof.append(dict(Module=key[0], Token=key[1], Accessor=evidence, IncomingReferences=incoming))
    selected_modules = {r['Module'] for r in rows}
    reports = [r for r in inventory['Reports'] if r['Module'] in selected_modules and r['Kind'] in ('Fields', 'Methods')]
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    spec = dict(Format=1, TargetRoot=str(root), ContractReferenceSha256=contract['Sha256'],
                Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    proposed_fields = {(r['Module'], r['Token']): r for r in fields}
    for row in review['Fields']:
        require_identity(proposed_fields[(row['Module'], row['Token'])], row)
    decisions = {(r['Kind'], r['Module'], r['Token']): r for r in rows}
    for row in review['Methods']:
        key = (row['Module'], row['Token'])
        native = accessor_rows[key]
        require_identity(native, row)
        row.update(ContractFamily=native['ContractFamily'], MappingBlocker=native['MappingBlocker'])
        decision = decisions[('Methods', *key)]
        if decision.get('ApplyExistingProposal'):
            row.update(ApplyExistingProposal=True, PreviousProposalEvidence=decision['PreviousProposalEvidence'])
        previous = old['Methods'].get(key)
        if previous:
            for label, position, expected in (('ParameterNames', 'Sequence', 'OriginalName'), ('LocalNames', 'Index', 'ExpectedType')):
                actual = {p[position]: p for p in row.get(label, [])}
                for p in previous.get(label, []):
                    if p.get('NewName'):
                        assert actual[p[position]][expected] == p[expected]
                        assert actual[p[position]]['NewName'] == p['NewName']
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    evidence = dict(Format=1, Kind='ApplicationPropertyEvidence', BaseMapSha256=base_sha,
        Inputs=[dict(Path=p, Sha256=digest(p)) for p in (args.state, args.inventory, args.proposals, args.bodies, args.accessors, args.ledger, args.graph)],
        GetterReports=body_index, GraphInputsVerified=len(meta['Modules']), Fields=proof, Methods=method_proof,
        ExcludedAccessors=[dict(Module=k[0], Token=k[1], ProposedName=accessor_rows[k]['NewName'],
            ContractFamily=accessor_rows[k]['ContractFamily'], Reason='Exact SDK whitelist token or its indivisible interface/override family; preserve current runtime metadata and historical review decision.') for k in excluded],
        Families=[families[f] for f in sorted(touched)],
        Limits='Reviewed physical property storage and conventional accessors only. Unflagged names, remaining method scopes, full export/build and unchanged-App runtime compatibility remain pending.')
    version = state['Maps']['63']['NextWave']
    old_version = int(pathlib.Path(state['Maps']['63']['Path']).stem.rsplit('-v', 1)[1])
    for name, document in ((f'application-property-spec-v{version}', spec), (f'application-property-review-v{version}', review),
                           (f'application-property-evidence-v{version}', evidence), (f'application-property-preimages-v{old_version}', preimages)):
        with (output / (name + '.json')).open('x', encoding='utf-8') as stream:
            json.dump(document, stream, indent=2)
            stream.write('\n')
    print(dict(Fields=len(fields), Methods=len(selected), Families=len(touched), PreviousDecisions=len(preimages)))


if __name__ == '__main__':
    main()
