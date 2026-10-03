"""Prepare scoped aliases from manually reviewed native physical call evidence.

Writes review/evidence JSON only. Every proposed scope has an explicit decision;
the native updater remains the only writer of XML maps, source aliases or IL.
"""
import argparse
import json
import pathlib
import re
import sqlite3
import xml.etree.ElementTree as ET
from prepare_physical_review import prepare
from prepare_sdk_property_storage_review import read, digest
from prepare_constructor_parameter_review import argument
from review_ledger import require_identity


def validate_property_anchor(native_evidence, callee, proposed_name):
    anchor = native_evidence['Property']
    assert native_evidence['Call']['RoleSource'] == 'existing-property-name'
    assert anchor['ProposedName'] == proposed_name and re.fullmatch(r'0x17[0-9A-F]{6}', anchor['PropertyToken'])
    owners = callee['AccessorOwners']
    assert len(owners) == 1
    owner = owners[0]
    assert owner['OwnerKind'] == 'Property' and owner['AccessorRole'] == 'set'
    assert owner['OwnerToken'] == anchor['PropertyToken'] and owner['OwnerSignature'] == anchor['PropertySignature']
    assert owner['OwnerName'] == anchor['PropertyName']
    assert [p['Sequence'] for p in callee['Parameters'] if p['Sequence'] is not None] == [1]


def validate_domain_decision(decision, row, parameter, mapping, property_parameters):
    require_identity(row, decision)
    assert decision['Reason'] and decision['Disposition'] in ('accept', 'preserve', 'defer')
    assert decision['ExpectedParameterName'] == parameter['OriginalName'] and decision['ExpectedProposal'] == parameter['NewName']
    assert not decision.get('AcceptedName') or property_parameters and decision['Disposition'] == 'accept'
    if 'AcceptedName' in decision:
        assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', decision['AcceptedName'])
    if decision.get('ExpectedCallerAlias'):
        assert mapping is not None
        assert mapping.get('ExpectedName') == row['OriginalName'] and mapping.get('Signature') == row['Signature']
        assert mapping.get('NewName') == decision['ExpectedCallerAlias']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('state', 'inventory', 'proposals', 'bodies', 'ledger', 'graph', 'decisions', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--property-parameters', action='store_true', help='Require exact native property-owner evidence for generic setter inputs')
    args = parser.parse_args()
    state, inventory, proposals, index, ledger, decisions = map(read,
        (args.state, args.inventory, args.proposals, args.bodies, args.ledger, args.decisions))
    root = pathlib.Path(state['Pass']['SourceTree63']).resolve()
    assert proposals['InferenceKind'] == ('PropertyParameter' if args.property_parameters else 'ForwardedParameter')
    assert str(root) == proposals['TargetRoot'] == ledger['TargetRoot']
    assert digest(state['Maps']['63']['Path']) == state['Maps']['63']['Sha256'] == inventory['MapSha256'] == proposals['BaseMapSha256']
    assert digest(args.ledger) == inventory['LedgerSha256']
    contracts = state['Compatibility']['ContractReferences63']
    whitelist = state['Compatibility']['SdkWhitelist63']
    assert digest(contracts['Path']) == contracts['Sha256'] and digest(whitelist['Path']) == whitelist['Sha256']
    modules = {m['Path']: m for m in inventory['Modules']}
    protected = {(m.get('Path'), s.get('Token')) for m in ET.parse(whitelist['Path']).getroot() for s in m}
    mapped = {(m.get('Path'), r.get('Token')): r for m in ET.parse(state['Maps']['63']['Path']).getroot() for r in m.findall('Method')}
    previous = {(m['Module'], m['Token']): m for m in ledger['Methods']}
    selected, excluded = [], []
    for row in proposals['Methods']:
        key = row['Module'], row['Token']
        if key[0] not in modules or key in protected:
            excluded.append(dict(Module=key[0], Token=key[1], Reason='outside first-party source scope' if key[0] not in modules else 'exact SDK whitelist token'))
            continue
        assert not row['NewName'] and row['ScopedMappingBlocker'] is None
        assert not previous.get(key, {}).get('Unresolved'), 'Unknown definitions need their separate guarded review'
        selected.append(row)
    wanted = {(m['Module'], m['Token']): m for m in selected}
    proposed_scopes = {(*key, p['Sequence']): p for key, m in wanted.items() for p in m['ParameterNames'] if p['NewName']}
    reviewed = {}
    for decision in decisions:
        key = decision['Module'], decision['Token'], decision['Sequence']
        assert key in proposed_scopes and key not in reviewed and decision['Reason']
        parameter = proposed_scopes[key]
        validate_domain_decision(decision, wanted[key[:2]], parameter, mapped.get(key[:2]), args.property_parameters)
        reviewed[key] = decision
    assert set(reviewed) == set(proposed_scopes), 'Every eligible proposed input requires an explicit domain decision'
    bodies = {}
    for entry in index:
        assert digest(entry['Path']) == entry['Sha256']
        document = read(entry['Path'])
        module = entry['Module']
        assert pathlib.Path(document['Input']).resolve() == (root / module).resolve()
        assert document['Sha256'] == modules[module]['Sha256'] == digest(root / module)
        assert document['Mvid'] == modules[module]['Mvid']
        for method in document['Methods']:
            key = module, method['Token']
            assert key not in bodies
            bodies[key] = method
    assert set(wanted).issubset(bodies)
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    physical = {pathlib.Path(m['Input']).resolve(): m for m in meta['Modules']}
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    proof, rows = [], []
    for key, row in wanted.items():
        body = bodies[key]
        assert row['Signature'] == body['Signature'] and not body['ExceptionHandlers']
        assert row['Sha256'] == physical[(root / key[0]).resolve()]['Sha256'] and row['Mvid'] == physical[(root / key[0]).resolve()]['Mvid']
        accepted, preserved, scope_proof = {}, [], []
        for scope, parameter in proposed_scopes.items():
            if scope[:2] != key:
                continue
            decision = reviewed[scope]
            metadata = next(p for p in body['Parameters'] if p['Sequence'] == scope[2])
            assert metadata['Name'] == parameter['OriginalName']
            uses = [dict(Instruction=i, Context=body['Instructions'][max(0, n-2):n+5]) for n, i in enumerate(body['Instructions']) if argument(i) == metadata['ArgumentIndex']]
            assert uses and not any(u['Instruction']['OpCode'] in ('starg', 'starg.s', 'ldarga', 'ldarga.s') for u in uses)
            source_evidence = proposals['PropertyParameterEvidence'] if args.property_parameters else proposals['ForwardedParameterEvidence']
            forwarding = [e for e in source_evidence if ((e['Call'] if args.property_parameters else e)['Module'],
                (e['Call'] if args.property_parameters else e)['MethodToken'],
                (e['Call'] if args.property_parameters else e)['ParameterSequence']) == scope]
            assert forwarding
            anchors = []
            for native_evidence in forwarding:
                evidence = native_evidence['Call'] if args.property_parameters else native_evidence
                callee_key = key[0], evidence['CalleeToken']
                callee = bodies[callee_key]
                assert evidence['MethodSignature'] == row['Signature'] and evidence['CalleeSignature'] == callee['Signature']
                assert evidence['ProposedName'] == parameter['NewName']
                target = next(p for p in callee['Parameters'] if p['Sequence'] == evidence['CalleeParameterSequence'])
                assert target['Type'] == metadata['Type']
                role_source = native_evidence['CalleeRoleSource'] if args.property_parameters else evidence['RoleSource']
                expected_role = 'value' if args.property_parameters else parameter['NewName']
                if args.property_parameters:
                    validate_property_anchor(native_evidence, callee, parameter['NewName'])
                if role_source == 'checked-source-alias':
                    mapping = mapped[callee_key]
                    assert mapping.get('Signature') == callee['Signature']
                    name = next(p for p in mapping.findall('Parameter') if int(p.get('Sequence')) == target['Sequence'])
                    assert name.get('ExpectedName') == target['Name'] and name.get('NewName') == expected_role
                else:
                    assert role_source == 'existing-metadata-name' and target['Name'] == expected_role
                assert any(i['OpCode'] in ('call', 'callvirt', 'newobj') and isinstance(i['Operand'], dict) and i['Operand'].get('Token') == evidence['CalleeToken'] for i in body['Instructions'])
                anchors.append(dict(Evidence=native_evidence, Parameter=target, Body=callee))
            if decision['Disposition'] == 'accept':
                accepted[scope[2]] = decision.get('AcceptedName') or parameter['NewName']
            elif decision['Disposition'] == 'preserve':
                preserved.append(decision)
            scope_proof.append(dict(Decision=decision, AllInputUses=uses, PhysicalCallees=anchors))
        # Existing rows are merged only when they gain a checked scope; defer
        # decisions remain in this evidence rather than erasing prior reviews.
        if accepted or preserved and key not in previous:
            rows.append(dict(Kind='Methods', Module=key[0], Token=key[1], ParameterNames=accepted,
                Disposition='rename' if accepted else 'preserve',
                NewName='' if key in previous or not accepted else mapped[key].get('NewName', '') if key in mapped else '',
                Reason='Reviewed direct physical callee roles, every input use and incoming graph references. ' +
                ' '.join(d['Reason'] for d in reviewed.values() if (d['Module'], d['Token']) == key) +
                ' Preserve runtime metadata, existing definition aliases, legitimate short names and all other scopes. No owner or local role follows from the forwarded parameter alone.'))
        incoming = [dict(Source=s, Reference=json.loads(d)) for s, d in graph.execute('select source,data from edges where target=?',
                    (physical[(root / key[0]).resolve()]['Id'] + ':' + key[1],))]
        proof.append(dict(Module=key[0], Token=key[1], Signature=row['Signature'], Parameters=scope_proof, Body=body, PhysicalIncomingReferences=incoming))
    reports = [r for r in inventory['Reports'] if r['Module'] in {r['Module'] for r in rows} and r['Kind'] == 'Methods']
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    spec = dict(Format=1, TargetRoot=str(root), ContractReferenceSha256=contracts['Sha256'], Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    for row in review['Methods']:
        key = row['Module'], row['Token']
        require_identity(wanted[key], row)
        preserved = {d['Sequence'] for d in decisions if (d['Module'], d['Token']) == key and d['Disposition'] == 'preserve'}
        row['UnresolvedScopeEvidence'] = dict(
            Parameters=[dict(Sequence=p['Sequence'], OriginalName=p['OriginalName'], MissingEvidence=
                reviewed[(*key, p['Sequence'])]['Reason'] if (*key, p['Sequence']) in reviewed else
                'No reviewed named callee/storage/caller role for this input; preserve metadata and review its owning call chain.')
                for p in row['ParameterNames'] if not p['NewName'] and p['Sequence'] not in preserved and
                ((*key, p['Sequence']) in reviewed and reviewed[(*key, p['Sequence'])]['Disposition'] == 'defer' or
                 re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*_[0-9]+', p['OriginalName'] or '')) and
                not any(int(scope.get('Sequence')) == p['Sequence'] and scope.get('NewName') for scope in (mapped[key].findall('Parameter') if key in mapped else []))],
            Locals=[dict(Index=p['Index'], ExpectedType=p['ExpectedType'], MissingEvidence='Owning expression, control flow and use sites require behavioral review; no role inferred from slot or type alone.')
                    for p in row['LocalNames'] if not p['NewName']])
        if row['NeedsReadableName'] and not row['NewName'] and not (mapped[key].get('NewName') if key in mapped else ''):
            row['UnresolvedDefinitionEvidence'] = 'Only parameter forwarding was reviewed. Method/owner behavior and its callers still need a domain name; this scoped block does not resolve the definition.'
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    version = state['Maps']['63']['NextWave']
    evidence = dict(Format=1, Kind='PropertyParameterEvidence' if args.property_parameters else 'ForwardedParameterEvidence', BaseMapSha256=proposals['BaseMapSha256'],
        Inputs=[dict(Path=p, Sha256=digest(p)) for p in (args.state, args.inventory, args.proposals, args.bodies, args.ledger, args.graph, args.decisions)],
        GraphInputsVerified=len(meta['Modules']), NativeBodyReports=index, Callers=proof, Excluded=excluded,
        Limits='Source-scope parameter decisions only. Deferrals retain their missing evidence. No new type/field/local alias, runtime metadata edit, ETS export/build or unchanged-App compatibility claim.')
    for label, document in (('spec', spec), ('review', review), ('evidence', evidence)):
        prefix = 'property-parameter' if args.property_parameters else 'forwarded-parameter'
        with (output / f'{prefix}-{label}-v{version}.json').open('x', encoding='utf-8') as stream:
            json.dump(document, stream, indent=2)
            stream.write('\n')
    print(dict(EligibleCallers=len(selected), LedgerRows=len(rows), ScopeMergedRows=sum((r['Module'], r['Token']) in previous for r in rows),
               Accepted=sum(d['Disposition'] == 'accept' for d in decisions), Preserved=sum(d['Disposition'] == 'preserve' for d in decisions), Deferred=sum(d['Disposition'] == 'defer' for d in decisions)))


if __name__ == '__main__':
    main()
