"""Prepare reviewed SDK storage decisions; never patch ETS source or binaries."""
import argparse
import hashlib
import json
import pathlib
import sqlite3
import xml.etree.ElementTree as ET
from prepare_physical_review import prepare


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest().upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('state', 'inventory', 'proposals', 'types', 'bodies', 'extra', 'graph', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    state, inventory, proposals, types, bodies, extra = map(read,
        (args.state, args.inventory, args.proposals, args.types, args.bodies, args.extra))
    root = pathlib.Path(state['Pass']['SourceTree63'])
    physical = root / 'Knx.Ets.Sdk.dll'
    assert inventory['MapSha256'] == proposals['BaseMapSha256'] == state['Maps']['63']['Sha256'] == digest(state['Maps']['63']['Path'])
    for document in (types, bodies, extra):
        assert pathlib.Path(document['Input']).resolve() == physical.resolve()
        assert document['Sha256'] == digest(physical) and document['Mvid'] == types['Mvid']
        assert document['Identity'] == types['Identity']
    reports = [r for r in inventory['Reports'] if r['Module'] == 'Knx.Ets.Sdk.dll']
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    catalog = {kind: {r['Token']: r for report in reports if report['Kind'] == kind
                     for r in read(report['Path'])[kind]} for kind in ('Fields', 'Methods')}
    fields = {f['Token']: f for t in types['Types'] for f in t['Fields']}
    methods = {m['Token']: m for doc in (bodies, extra) for m in doc['Methods']}
    whitelist = ET.parse(state['Compatibility']['SdkWhitelist63']['Path']).getroot()
    assert digest(state['Compatibility']['SdkWhitelist63']['Path']) == state['Compatibility']['SdkWhitelist63']['Sha256']
    protected = {s.get('Token') for m in whitelist if m.get('Path') == 'Knx.Ets.Sdk.dll' for s in m}
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    module = next(m for m in meta['Modules'] if pathlib.Path(m['Input']).resolve() == physical.resolve())
    assert module['Mvid'] == types['Mvid']
    rows, proof, references = [], [], {}

    def incoming(token):
        found = [dict(Source=s, Reference=json.loads(d)) for s, d in graph.execute(
            'select source,data from edges where target=?', (module['Id'] + ':' + token,))]
        references[token] = found
        return found

    def add(kind, token, reason, name=None, parameters=None, disposition='rename'):
        row = dict(Kind=kind, Module='Knx.Ets.Sdk.dll', Token=token, Reason=reason, Disposition=disposition)
        if name:
            row['NewName'] = name
        if parameters:
            row['ParameterNames'] = parameters
        rows.append(row)

    selected = [r for r in proposals['Fields'] if r['Module'] == 'Knx.Ets.Sdk.dll']
    assert len(selected) == 354, 'Re-review changed proposal selection'
    memory_parameter = next(t for t in types['Types'] if t['Token'] == '0x0200023F')
    assert memory_parameter['Type'] == 'Knx.Ets.Sdk.Product.MemoryParameter'
    assert memory_parameter['BaseType'] == 'Knx.Ets.Sdk.Product.Parameter'
    # These members describe the derived memory representation, whereas the
    # base Parameter already has accepted bitOffset/offset storage aliases.
    # Specify the behavior-bearing domain rather than accept numeric suffixes.
    storage_names = {'0x0400062D': 'memoryBitOffset', '0x0400062F': 'memoryOffset'}
    for row in selected:
        token = row['Token']
        assert token not in protected and fields[token]['MappingBlocker'] is None
        assert fields[token]['Name'] == row['OriginalName'] and fields[token]['Signature'] == row['Signature']
        evidence = [e for e in proposals['PropertyEvidence'] if e['Module'] == row['Module'] and e['FieldToken'] == token]
        assert len(evidence) == 1
        evidence = evidence[0]
        getter = methods[evidence['GetterToken']]
        assert getter['Signature'] == evidence['GetterSignature']
        assert any(o['OwnerToken'] == evidence['PropertyToken'] and o['OwnerName'] == evidence['PropertyName']
                   and o['OwnerSignature'] == evidence['PropertySignature'] and o['AccessorRole'] == 'get'
                   for o in getter['AccessorOwners'])
        assert incoming(token), 'Missing physical field uses'
        assert any(i['OpCode'] in ('ldfld', 'ldsfld') and isinstance(i['Operand'], dict)
                   and i['Operand'].get('Token') == token for i in getter['Instructions'])
        accepted_name = storage_names.get(token, row['NewName'])
        detail = (' This is MemoryParameter memory-segment storage, distinct from the base Parameter representation.'
                  if token in storage_names else '')
        add('Fields', token, row['Reason'] + '. Reviewed domain role: ' + evidence['PropertyName'] + detail +
            '. Every normal return reloads this same physical field; guards and initialization remain unchanged. '
            'The exact field is outside the SDK whitelist. Preserve runtime metadata, storage and all contract accessor names.', accepted_name)
        proof.append(dict(Field=fields[token], Property=evidence, Getter=getter, AcceptedFieldName=accepted_name))

    def uses(method, token, operation):
        assert any(i['OpCode'] == operation and isinstance(i['Operand'], dict) and i['Operand'].get('Token') == token
                   for i in methods[method]['Instructions'])

    # Named factory -> constructor -> field -> validation call establishes this
    # additional field independently of spelling or the opaque implementation type.
    uses('0x060014A6', '0x060014A3', 'newobj')
    uses('0x060014A3', '0x040006E1', 'stfld')
    uses('0x060014A3', '0x0600020A', 'callvirt')
    assert methods['0x060014A6']['Parameters'][1]['Name'] == 'device'
    assert '0x040006E1' not in protected and fields['0x040006E1']['MappingBlocker'] is None
    incoming('0x040006E1')
    add('Fields', '0x040006E1', 'FromHawkDeviceManagement receives the named device, stores it in b through constructor 060014A3, '
        'derives Root and passes the same device to ValidateDeviceManagementAvailable. Preserve private runtime metadata and original validation behavior.', 'device')
    assert '0x060006ED' not in protected and '0x060014A3' not in protected
    for caller, forwarded in (('0x060006EB', ['entry', 'peiType', 'knxManufacturerId', 'applicationNumber', 'applicationVersion']),
                              ('0x060006EC', ['entry', 'peiType', 'knxManufacturerId', 'applicationNumber', 'applicationVersion'])):
        uses(caller, '0x060006ED', 'call')
        actual = [p['Name'] for p in methods[caller]['Parameters'] if p['Sequence'] is not None]
        assert actual[-5:] == forwarded
        add('Methods', caller, 'Meaningful public TaskSegment overload and all named SDK parameters are preserved. '
            'Its ordered five-argument forwarding call proves the private constructor roles without altering the public contract.', disposition='preserve')
    add('Methods', '0x060006ED', 'Both meaningful public TaskSegment overloads forward entry, peiType, knxManufacturerId, '
        'applicationNumber and applicationVersion in that exact order. The private constructor sets LdCtrlTaskSegment.Address and stores '
        'the values returned by PeiType/KnxManufacturerId/ApplicationNumber/ApplicationVersion. No body locals exist; preserve .ctor metadata.',
        parameters={1: 'entry', 2: 'peiType', 3: 'knxManufacturerId', 4: 'applicationNumber', 5: 'applicationVersion'})
    add('Methods', '0x060014A3', 'FromHawkDeviceManagement forwards its existing deviceManagement and device parameters unchanged. '
        'The private constructor stores them in InternalHawkDeviceManagement and the validated device field; no body locals exist. Preserve .ctor metadata.',
        parameters={1: 'deviceManagement', 2: 'device'})
    add('Methods', '0x060014A6', 'Preserve the meaningful factory name, deviceManagement/device parameter names, null-argument exception literals '
        'and constructor call. Two metadata locals are never read or written and have no established behavior; do not invent roles.', disposition='preserve')
    for token in ('0x060006ED', '0x060014A3', '0x060006EB', '0x060006EC', '0x060014A6'):
        incoming(token)
    spec = dict(Format=1, TargetRoot=str(root), ContractReferenceSha256=state['Compatibility']['ContractReferences63']['Sha256'],
                Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    work = pathlib.Path(args.output)
    work.mkdir(parents=True, exist_ok=True)
    evidence = dict(Format=1, Kind='SdkPropertyStorageEvidence', Input=str(physical), Mvid=types['Mvid'], Sha256=types['Sha256'],
        BaseMapSha256=state['Maps']['63']['Sha256'], GraphInputsVerified=len(meta['Modules']),
        ProposalsSha256=digest(args.proposals), Fields=proof, ConstructorBodies=[methods[t] for t in
        ('0x060006ED', '0x060014A3', '0x060006EB', '0x060006EC', '0x060014A6')],
        AdditionalField=fields['0x040006E1'], PhysicalIncomingReferences=references,
        Limits='355 private field aliases and seven private constructor parameters. SDK/public contract names and meaningful scopes preserved. '
               'Property spelling is only an anchor; the reviewed domains and physical IL/graph establish each decision. '
               'This is mapping evidence, not source export/build or observed unchanged-App compatibility.')
    for name, document in (('spec', spec), ('review', review), ('evidence', evidence)):
        with (work / (name + '.json')).open('x', encoding='utf-8') as stream:
            json.dump(document, stream, indent=2)
            stream.write('\n')
    print({k: len(review[k]) for k in ('Types', 'Fields', 'Methods')})


if __name__ == '__main__':
    main()
