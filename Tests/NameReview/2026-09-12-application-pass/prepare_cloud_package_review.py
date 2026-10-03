"""Prepare coupled package/native-event review JSON from physical evidence only."""
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
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('state', 'inventory', 'bodies', 'caller-bodies', 'loader-bodies', 'types', 'fields', 'graph', 'output'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    state, inventory = read(args.state), read(args.inventory)
    bodies, callers, loaders, types, fields = map(read, (args.bodies, args.caller_bodies, args.loader_bodies, args.types, args.fields))
    physical = pathlib.Path(state['Pass']['SourceTree63']) / 'Knx.CloudKit.dll'
    for evidence in (bodies, callers, loaders, types, fields):
        assert pathlib.Path(evidence['Input']).resolve() == physical.resolve()
        assert evidence['Sha256'] == digest(physical) and evidence['Mvid'] == bodies['Mvid']
    assert inventory['MapSha256'] == state['Maps']['63']['Sha256'] == digest(state['Maps']['63']['Path'])
    reports = [r for r in inventory['Reports'] if r['Module'] == 'Knx.CloudKit.dll']
    assert {r['Kind'] for r in reports} == {'Types', 'Methods', 'Fields'}
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    native = {kind: {r['Token']: r for report in reports if report['Kind'] == kind
                     for r in read(report['Path'])[kind]} for kind in ('Types', 'Fields', 'Methods')}
    methods = {m['Token']: m for m in bodies['Methods'] + callers['Methods']}
    storage = {f['Token']: f for f in fields['Fields']}
    current = next(m for m in ET.parse(state['Maps']['63']['Path']).getroot().findall('Module') if m.get('Path') == 'Knx.CloudKit.dll')
    aliases = {m.get('Token'): m for m in current}
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    module = next(m for m in meta['Modules'] if pathlib.Path(m['Input']).resolve() == physical.resolve())
    assert module['Sha256'] == bodies['Sha256'] and module['Mvid'] == bodies['Mvid']
    rows, checked_edges = [], {}

    def add(kind, token, name, reason, parameters=None, locals_=None, disposition='rename'):
        row = dict(Kind=kind, Module='Knx.CloudKit.dll', Token=token, Reason=reason, Disposition=disposition)
        if name:
            row['NewName'] = name
        if parameters:
            row['ParameterNames'] = parameters
        if locals_:
            row['LocalNames'] = locals_
        rows.append(row)

    def field(number, name, reason):
        token = f'0x{number:08X}'
        assert storage[token]['MappingBlocker'] is None
        edges = [dict(Source=source, Reference=json.loads(data)) for source, data in graph.execute(
            'select source,data from edges where target=?', (module['Id'] + ':' + token,))]
        assert edges, ('Missing field consumers', token)
        checked_edges[token] = edges
        add('Fields', token, name, reason + ' Full physical graph references retained; layout and runtime metadata names remain restoration inputs.')

    def method(number, reason, parameters=None, locals_=None, name=None):
        token = f'0x{number:08X}'
        assert methods[token]['HasBody'] and native['Methods'][token]['ScopedMappingBlocker'] is None
        parameters, locals_ = dict(parameters or {}), dict(locals_ or {})
        old = aliases.get(token)
        if old is not None:
            if name is None:
                name = old.get('NewName')
            for child in old.findall('Parameter'):
                parameters.setdefault(child.get('Sequence'), child.get('NewName'))
            for child in old.findall('Local'):
                locals_.setdefault(child.get('Index'), child.get('NewName'))
        add('Methods', token, name, reason + ' Existing supported scope aliases are carried forward; unused Int16/Int32 locals receive no invented roles.', parameters, locals_)

    # The lock protects handler snapshots, not output-buffer/native-call access.
    field(0x040000D5, 'outputBuffer', '060001C3 initializes Struct42; 060001B3/B4/B6/B9/BA/BB/C0 clear it, pass its bytes and an in/out count to native delegates, then copy the returned prefix.')
    field(0x040000D6, 'eventHandlerLock', 'All five physical reads are Monitor.Enter/Exit snapshots in 060001A1-A5; 060001C3 creates the object. No graph native-call/output-buffer lock consumers.')
    phases = [('loadingHandlers', 0x06000197, 0x060001A1), ('loadedHandlers', 0x06000199, 0x060001A2),
              ('unloadingHandlers', 0x0600019B, 0x060001A3), ('unloadedHandlers', 0x0600019D, 0x060001A4),
              ('loadFailureHandlers', 0x0600019F, 0x060001A5)]
    loader_methods = {m['Token']: m for m in loaders['Methods']}
    for index, (name, subscribe, publish) in enumerate(phases):
        token = 0x040000D7 + index
        field(token, name, f'{subscribe:08X}/{subscribe + 1:08X} Combine/Remove and Interlocked.CompareExchange this exact field; {publish:08X} snapshots/invokes it. Windows/Unix load/unload bodies establish before/after/failure phase.')
        expected_loader_tokens = [0x060001D4, 0x0600024C] if index in (0, 1, 4) else [0x060001D5, 0x0600024D]
        for loader_token in expected_loader_tokens:
            assert any(isinstance(i['Operand'], dict) and i['Operand'].get('Token') == f'0x{publish:08X}' for i in loader_methods[f'0x{loader_token:08X}']['Instructions'])
        for number in (subscribe, subscribe + 1):
            instructions = methods[f'0x{number:08X}']['Instructions']
            assert any(isinstance(i['Operand'], dict) and 'System.Threading.Interlocked::CompareExchange' in i['Operand'].get('Text', '') for i in instructions)
            method(number, f'CompareExchange loop for {name}: local 0 is the current handlers, 1 is the expected preimage, 2 is the combined/removed replacement; parameter 1 is the supplied handler.', {'1': 'handler'}, {'0': 'currentHandlers', '1': 'expectedHandlers', '2': 'updatedHandlers'})
        method(publish, f'Monitor snapshot for {name}: local 0 is the invoked handler chain, 1 is the lock object and 2 is the Enter by-ref acquisition flag.', locals_={'0': 'handlers', '1': 'eventLock', '2': 'lockTaken'})
    for number in (0x040000D3, 0x040000D4):
        token = f'0x{number:08X}'
        edges = graph.execute('select count(*) from edges where target=?', (module['Id'] + ':' + token,)).fetchone()[0]
        assert edges == 0 and storage[token]['IsLiteral']
        add('Fields', token, '', f'Literal Int32 value {storage[token]["Constant"]}; 111 hash-verified graph inputs yield zero static references. No distinct association with inlined numeric uses or dynamic consumers establishes the intended role. Do not guess a timeout/retry meaning.', disposition='unresolved')

    decoder = methods['0x060001AF']['Instructions']
    assert any(isinstance(i['Operand'], dict) and 'System.String::TrimEnd' in i['Operand'].get('Text', '') for i in decoder)
    assert not any(isinstance(i['Operand'], dict) and ('IndexOf' in i['Operand'].get('Text', '') or 'TakeWhile' in i['Operand'].get('Text', '')) for i in decoder)
    method(0x060001AF, 'Null/empty input returns String.Empty; UTF8.GetString decodes the entire array and TrimEnd(new char[1]) removes trailing NULs only. Embedded NULs remain; replace the unsupported terminator-scan implication.', {'1': 'bytes'}, name='DecodeUtf8WithoutTrailingNulls')
    method(0x060001AE, 'String.IsNullOrEmpty returns byte[0]; nonempty UTF8.GetBytes is concatenated with byte[1] containing a zero terminator.', {'1': 'text'})
    for number in (0x02000031, 0x0200004C):
        token = f'0x{number:08X}'
        typ = next(t for t in types['Types'] if t['Token'] == token)
        assert typ['BaseType'] == 'System.MulticastDelegate'
        assert any('Invoke(Class8/c&)' in m['Signature'] for m in typ['Methods'])
        add('Types', token, 'ReadLibraryVersionFunction', '060001B7 selects this Windows/Unix unmanaged delegate with Class8/c by-ref output, then 0600029C constructs System.Version from its four fields. The two delegate types retain separate physical tokens, owners and calling-convention metadata.')
    method(0x060001B7, 'Local 0 is initialized by 0600029B, passed by ref to the selected native version delegate, and converted through 0600029C into System.Version.', locals_={'0': 'version'})

    package_fields = {
        0x040001BF: ('nextCreationOrder', '060002EB stores the current static value into instance field 040001C2 and increments the static value by one; this is not an Interlocked operation.'),
        0x040001C0: ('payload', '060002EB parses raw bytes into Class11/e; vendor/name/label/features accessors and 060002ED consume that same record.'),
        0x040001C1: ('signature', '060002EB stores constructor signature; 060002F2 returns it and 060002ED passes it into aj2 constructor argument 5. PKG formatting includes SIGN=.'),
        0x040001C2: ('creationOrder', '060002EB captures preincrement static creation order; 060002F3 returns it and IComparable.CompareTo compares it before package names.'),
        0x040001C4: ('utf8Bytes', 'Vendor record 060002F6 encodes UTF8 and truncates to Marshal.SizeOf; fixed-array marshal Size=8, unspecified element type retained. ToString trims NULs at both ends.'),
        0x040001C5: ('utf8Bytes', 'Name record 060002FB encodes UTF8 and truncates to Marshal.SizeOf; fixed-array marshal Size=64. 060002EC No name/Wrong length of name errors corroborate the role.'),
        0x040001C6: ('utf8Bytes', 'Label record 06000300 encodes UTF8 and truncates to Marshal.SizeOf; fixed-array marshal Size=64. 060002EC No label/Wrong length of label errors corroborate the role.'),
        0x040001C7: ('labelBytes', '06000305/306 UTF8 encode the feature label and Take(16); 0600030B serializes these bytes before the UInt16 value. Fixed-array Size=16 retains its original native element metadata.'),
        0x040001C8: ('value', '06000305 stores UInt16 argument 2; 06000306 reads ajl value; 0600030B BitConverter.GetBytes serializes it, 0600030D reconstructs ajl(label,value). Zero/65535 predicates and =unlimited formatting corroborate value semantics.'),
        0x040001C9: ('vendor', '0600030F parses the first vendor-sized UTF8 record; 06000310 emits it first. 060002EC validates No vendor/Wrong length of vendor before filling this slot.'),
        0x040001CA: ('name', '0600030F parses the name after vendor bytes; 06000310 emits it second. 060002EC validates No name/Wrong length of name before filling this slot.'),
        0x040001CB: ('label', '0600030F parses the label after vendor/name bytes; 06000310 emits it third. 060002EC validates No label/Wrong length of label before filling this slot.'),
        0x040001CC: ('features', '0600030F divides the remaining payload into feature-size records and fills this array; 06000310 serializes every record and 06000312 reconstructs only nonempty labels.'),
        0x040001CD: ('vendor', '06000313 stores argument 1; 06000314 feeds No vendor/Wrong length of vendor checks in 060002EC, and PKG formatter emits it before the colon.'),
        0x040001CE: ('name', '06000313 stores argument 2; 06000315 feeds No name/Wrong length of name checks in 060002EC, and PKG formatter emits it after the colon.'),
        0x040001CF: ('label', '06000313 stores argument 3; 06000316 feeds No label/Wrong length of label checks in 060002EC, and PKG formatter emits it in quotes.'),
        0x040001D0: ('features', '06000313 stores argument 4; 060002EC converts it to feature records and 0600031B formats labels with optional values/unlimited.'),
        0x040001D1: ('signature', '06000313 stores argument 5; 060002EC verifies it against serialized payload, throws Wrong signature on failure; 0600031B emits SIGN=.'),
        0x040001D4: ('totalPackageCount', '060000D8 counts parsed definitions into local 0 and passes it to aj4; 06000325 initializes this field from List.Count; 0600032D returns it.'),
        0x040001D5: ('addedPackageCount', '060000D8 increments local 1 only when ConcurrentDictionary.TryAdd succeeds, then passes it through aj4 constructors into this field; 0600032E returns it.'),
        0x040001D6: ('skippedPackageCount', '060000D8 increments local 2 when ConcurrentDictionary.TryAdd fails, then passes it through aj4 constructors into this field; 0600032F returns it.'),
        0x040001D7: ('packageName', '06000323 stores the definition name; 06000324 stores the supplied package name, completion constructors set it empty; 06000327 returns it.'),
        0x040001D8: ('importSucceeded', '060000D8 supplies true for TryAdd success and false for failure to 06000323, which stores it here; 0600032B returns it.'),
        0x040001D9: ('importFinished', '06000323/324/325 set false; aggregate completion constructor 06000326 sets true with progress 100, after import loop in 060000D8; 0600032C returns it.'),
        0x040001DA: ('packageDefinition', 'Per-package progress constructor 06000323 stores its aj2 definition; completion/start constructors store null; 06000328 returns it.'),
        0x040001DB: ('parsedPackages', '06000325 stores the parser result list; 06000326 stores the final list; 06000329/32A read/set it. 060000D8 passes its parsed definitions.'),
        0x040001EC: ('cloudManager', '0600034C-34E climb feature->license->dongle parent links, reject non-ajg parents, and store the ajg cloud manager in this ajo slot; 0600034F rechecks/casts it.'),
        0x040001ED: ('dongle', '06000346/347 read/set the ajh slot; constructors resolve it from license parent and validate its ajg manager parent.'),
        0x040001EE: ('license', '06000348/349 read/set the ajq slot; feature-chain constructor requires the feature parent to be ajq before resolving its dongle parent.'),
        0x040001EF: ('feature', '0600034A/34B read/set the ajl slot; feature constructor stores the input, then resolves license/dongle/manager through checked parent types.')
    }
    for token, (name, reason) in package_fields.items():
        field(token, name, reason)
    for number, size in [(0x040001C4, 8), (0x040001C5, 64), (0x040001C6, 64), (0x040001C7, 16)]:
        shape = storage[f'0x{number:08X}']['Marshal']
        assert shape['Kind'] == 'FixedArrayMarshalType' and shape['Size'] == size and shape['IsSizeValid']

    method(0x060002EB, 'Constructor parses raw payload bytes into field 040001C0 and stores argument 2 as the package signature.', {'1': 'payloadBytes', '2': 'signature'})
    method(0x060002EC, 'No vendor/name/label, Wrong length and Wrong signature checks establish definition roles; locals 0/1/2 are feature list, assembled payload record and feature index.', {'1': 'definition'}, {'0': 'features', '1': 'payload', '2': 'featureIndex'})
    method(0x060002F4, 'Enumerates package features and compares each label to supplied string; preserve the meaningful featureLabel parameter alias. True result local returned after disposing the enumerator.', {'1': 'featureLabel'}, {'0': 'featureEnumerator', '1': 'containsLabel'})
    for constructor, getter, name in [(0x060002F6, 0x060002F8, 'vendor'), (0x060002FB, 0x060002FD, 'name'), (0x06000300, 0x06000302, 'label')]:
        method(constructor, f'UTF8.GetBytes({name}).Take(Marshal.SizeOf(record)).ToArray initializes the fixed-byte record.', {'1': name})
        method(getter, 'Local 0 is the stored UTF8 byte array; positive parameter resizes the returned array to exactly that byte count; nonpositive retains its size. Preserve the meaningful size parameter alias.', {'1': 'size'}, {'0': 'bytes'})
    for number in (0x060002F7, 0x060002FC, 0x06000301, 0x06000307):
        assert any(isinstance(i['Operand'], dict) and 'System.String::get_Length()' in i['Operand'].get('Text', '') for i in methods[f'0x{number:08X}']['Instructions'])
        method(number, 'ToString().Length counts managed string characters after UTF8 decoding/NUL trimming; preserve the existing character-count alias, not an invented byte-count operation.')
    method(0x06000305, 'Constructor UTF8 encodes/truncates label into field 040001C7 and stores UInt16 value in field 040001C8.', {'1': 'label', '2': 'value'})
    method(0x06000306, 'Constructor reads ajl label and UInt16 value into the native feature record.', {'1': 'feature'})
    method(0x0600030B, 'Local 0 is the label byte array resized to 16; local 1 is BitConverter.GetBytes(value) resized to 2; list appends label then value.', locals_={'0': 'labelBytes', '1': 'valueBytes'})
    method(0x0600030F, 'Parser checks header length and feature-size divisibility, decodes each 16-byte label and UInt16 suffix, and constructs feature records; Wrong raw package size guards malformed input.', {'1': 'payloadBytes'}, {'0': 'featureBytes', '1': 'featureCount', '2': 'featureIndex', '3': 'recordBytes', '4': 'label', '5': 'value'})
    method(0x06000310, 'Serializes vendor/name/label then iterates native feature records; catch returns null. Locals follow exact list, array, index, current record and returned byte array.', locals_={'0': 'payloadBytes', '1': 'featureRecords', '2': 'featureIndex', '3': 'featureRecord', '4': 'serializedPayload'})
    method(0x06000312, 'Builds managed feature list from native records; skips empty labels and reconstructs each accepted feature.', locals_={'0': 'features', '1': 'featureRecords', '2': 'featureIndex', '3': 'featureRecord'})
    method(0x06000313, 'Five constructor arguments feed vendor/name/label/features/signature slots; 060002EC validation literals and SIGN= formatting corroborate all roles.', {'1': 'vendor', '2': 'name', '3': 'label', '4': 'features', '5': 'signature'})
    method(0x06000319, 'Calls package payload 060002ED to create its definition.', {'1': 'package'})
    method(0x0600031B, 'PKG/SIGN= and =unlimited formatter iterates feature list; locals 0/1/2/3 are definition text, features, index and current feature.', locals_={'0': 'definitionText', '1': 'features', '2': 'featureIndex', '3': 'feature'})
    method(0x06000323, 'Caller 060000D8 computes (added+skipped)*100/total and supplies definition/counters/TryAdd success; constructor forwards progress to ProgressChangedEventArgs.', {'1': 'progressPercentage', '2': 'definition', '3': 'totalPackageCount', '4': 'addedPackageCount', '5': 'skippedPackageCount', '6': 'importSucceeded'})
    method(0x06000324, 'Start progress constructor stores name with zero progress/counters and no definition.', {'1': 'packageName'})
    method(0x06000325, 'Parsed-list constructor stores packages, total List.Count, progress 100 and importFinished=false.', {'1': 'packages'})
    method(0x06000326, 'Aggregate import completion constructor stores counters/list with progress 100 and importFinished=true.', {'1': 'totalPackageCount', '2': 'addedPackageCount', '3': 'skippedPackageCount', '4': 'packages'})
    method(0x0600032A, 'Stores the supplied parsed-package list in field 040001DB.', {'1': 'packages'})
    for setter, constructor, name in [(0x06000347, 0x0600034C, 'dongle'), (0x06000349, 0x0600034D, 'license'), (0x0600034B, 0x0600034E, 'feature')]:
        method(setter, f'Stores supplied {name} in its exact typed chain slot.', {'1': name})
        method(constructor, f'Starts from supplied {name}, validates parent types and resolves the dongle/license/manager chain; null or incompatible parents throw InvalidOperationException.', {'1': name})
    method(0x060000D8, 'Parser supplies definitions; total=Count, added increments on TryAdd true, skipped on false. Each callback uses these counters; accepted packages invoke the notification delegate list.', {'1': 'packageText', '2': 'progressCallback'}, {'0': 'totalPackageCount', '1': 'addedPackageCount', '2': 'skippedPackageCount', '3': 'definitions', '4': 'definitionEnumerator', '5': 'definition', '6': 'package', '7': 'handlers', '8': 'handlerIndex', '9': 'handlerDelegate', '10': 'packageAddedHandler'})
    method(0x060000B5, 'Snapshots completion handlers under Monitor; constructs aggregate aj4 from supplied counts/list then invokes every handler synchronously or through BeginInvoke.', {'1': 'totalPackageCount', '2': 'addedPackageCount', '3': 'skippedPackageCount', '4': 'packages'}, {'0': 'handlers', '1': 'eventLock', '2': 'lockTaken', '3': 'progress', '4': 'invocationList', '5': 'handlerIndex', '6': 'handlerDelegate', '7': 'completionHandler'})

    spec = dict(Format=1, TargetRoot=state['Pass']['SourceTree63'], ContractReferenceSha256=state['Compatibility']['ContractReferences63']['Sha256'], Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    input_state = dict(Pass=dict(SourceTree63=state['Pass']['SourceTree63']), Maps={'63': state['Maps']['63']},
                       Compatibility=dict(ContractReferences63=state['Compatibility']['ContractReferences63']))
    for name, document in [('cloud-package-input-state01.json', input_state), ('cloud-package-spec01.json', spec), ('cloud-package-review01.json', review), ('cloud-package-evidence01.json', dict(
            Format=1, PhysicalPath=str(physical), Sha256=bodies['Sha256'], Mvid=bodies['Mvid'], Map=state['Maps']['63']['Path'], MapSha256=inventory['MapSha256'],
            Inventory=dict(Path=args.inventory, Sha256=digest(args.inventory)),
            Sources=[dict(Path=path, Sha256=digest(path)) for path in (args.bodies, args.caller_bodies, args.loader_bodies, args.types, args.fields, args.graph)],
            GraphPhysicalInputsVerified=len(meta['Modules']), FieldReferences=checked_edges,
            Methods=[methods[r['Token']] for r in rows if r['Kind'] == 'Methods'],
            FieldStorage=[storage[r['Token']] for r in rows if r['Kind'] == 'Fields'],
            Limitations='Static graph excludes reflection/dynamic/external consumers. No application source or binary is edited. Native map checks remain mandatory; no rebuilt runtime compatibility is claimed.'))]:
        (output / name).write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print('Prepared', {k: len(review[k]) for k in ('Types', 'Fields', 'Methods')})


if __name__ == '__main__':
    main()
