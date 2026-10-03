"""Prepare native CloudKit loader/ABI reviews from physical evidence; no ETS edits."""
import argparse
import json
import pathlib
import sqlite3
import xml.etree.ElementTree as ET
from prepare_cloud_crypto_review import read, digest
from prepare_physical_review import prepare


PE = 'https://learn.microsoft.com/en-us/windows/win32/debug/pe-format'
DLL = 'https://learn.microsoft.com/en-us/windows/win32/dlls/dllmain'
WIN = 'https://raw.githubusercontent.com/microsoft/win32metadata/main/generation/WinSDK/RecompiledIdlHeaders/um/winnt.h'
MMAP = 'https://raw.githubusercontent.com/bminor/glibc/master/sysdeps/unix/sysv/linux/bits/mman-linux.h'
DL = 'https://raw.githubusercontent.com/bminor/glibc/master/bits/dlfcn.h'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('state', 'inventory', 'ledger', 'types', 'fields', 'native-bodies', 'wrapper-bodies',
                   'session-bodies', 'parser-bodies', 'consumer-bodies', 'graph', 'output'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    state, inventory, ledger = read(args.state), read(args.inventory), read(args.ledger)
    paths = (args.types, args.fields, args.native_bodies, args.wrapper_bodies, args.session_bodies, args.parser_bodies)
    types, fields, native_bodies, wrappers, sessions, parsers = documents = list(map(read, paths))
    physical = pathlib.Path(state['Pass']['SourceTree63']) / 'Knx.CloudKit.dll'
    physical_hash = digest(physical)
    for document in documents:
        assert pathlib.Path(document['Input']).resolve() == physical.resolve()
        assert document['Sha256'] == physical_hash and document['Mvid'] == types['Mvid']
        assert document['Identity'] == types['Identity']
    assert inventory['MapSha256'] == state['Maps']['63']['Sha256'] == digest(state['Maps']['63']['Path'])
    reports = [r for r in inventory['Reports'] if r['Module'] == 'Knx.CloudKit.dll']
    assert {r['Kind'] for r in reports} == {'Types', 'Fields', 'Methods'}
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    native = {kind: {r['Token']: r for report in reports if report['Kind'] == kind
                    for r in read(report['Path'])[kind]} for kind in ('Types', 'Fields', 'Methods')}
    storage = {r['Token']: r for r in fields['Fields']}
    type_rows = {r['Token']: r for r in types['Types']}
    methods = {r['Token']: r for document in documents if 'Methods' in document for r in document['Methods']}
    aliases = {r.get('Token'): r for m in ET.parse(state['Maps']['63']['Path']).getroot() if m.get('Path') == 'Knx.CloudKit.dll' for r in m}
    previous = {r['Token']: r for kind in ('Types', 'Fields', 'Methods') for r in ledger[kind] if r['Module'] == 'Knx.CloudKit.dll'}
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    module = next(m for m in meta['Modules'] if pathlib.Path(m['Input']).resolve() == physical.resolve())
    assert module['Sha256'] == physical_hash and module['Mvid'] == types['Mvid']
    consumer = read(args.consumer_bodies)
    consumer_module = next(m for m in meta['Modules'] if pathlib.Path(m['Input']).resolve() == pathlib.Path(consumer['Input']).resolve())
    assert consumer_module['Sha256'] == consumer['Sha256'] and consumer_module['Mvid'] == consumer['Mvid']
    caller = next(m for m in consumer['Methods'] if m['Token'] == '0x060001C0')
    assert any(i['Operand'] == 'Received new session token' for i in caller['Instructions'])
    rows, references, retained, boundaries, abi_facts = [], {}, [], [], []

    def token(number):
        return f'0x{number:08X}'

    def edges(number):
        key = token(number)
        result = [dict(Source=source, Reference=json.loads(data)) for source, data in graph.execute(
            'select source,data from edges where target=?', (module['Id'] + ':' + key,))]
        references[key] = result
        return result

    def add(kind, number, name, reason, parameters=None, locals_=None, disposition='rename'):
        key = token(number)
        row = dict(Kind=kind, Module='Knx.CloudKit.dll', Token=key, Reason=reason, Disposition=disposition)
        if name:
            row['NewName'] = name
        if parameters:
            row['ParameterNames'] = parameters
        if locals_:
            row['LocalNames'] = locals_
        if previous.get(key, {}).get('Unresolved'):
            if disposition == 'unresolved':
                retained.append(dict(Token=key, PreviousDecision=previous[key], CurrentMissingEvidence=reason))
                return
            assert name and key not in aliases
            row.update(ResolveExistingUnresolved=True,
                       PreviousUnresolvedEvidence={k: previous[key].get(k, '') for k in ('Reason', 'UnresolvedReason')})
        rows.append(row)

    def unknown(kind, number, reason):
        incoming = edges(number)
        assert token(number) not in aliases
        add(kind, number, '', f'no-evidence-in-scope: {reason} Physical graph has {len(incoming)} incoming edges across {len(meta["Modules"])} hash-verified inputs. Keep original identity; reflection/dynamic/external consumers not ruled out.', disposition='unresolved')

    def field(number, name, reason, literal=False):
        assert storage[token(number)]['MappingBlocker'] is None
        assert edges(number) or literal
        add('Fields', number, name, reason + ' Preserve metadata flags, type, numeric/storage bytes and runtime names through restoration.')

    def method(number, reason, parameters=None, locals_=None):
        key = token(number)
        assert methods[key]['HasBody'] and native['Methods'][key]['ScopedMappingBlocker'] is None
        parameters, locals_ = dict(parameters or {}), dict(locals_ or {})
        old = aliases.get(key)
        if old is not None:
            for child in old.findall('Parameter'):
                parameters.setdefault(child.get('Sequence'), child.get('NewName'))
            for child in old.findall('Local'):
                locals_.setdefault(child.get('Index'), child.get('NewName'))
        add('Methods', number, old.get('NewName') if old is not None else None,
            reason + ' Keep accepted definition names and exclude unused control locals.', parameters, locals_)

    def called(number, target):
        assert any(isinstance(i['Operand'], dict) and i['Operand'].get('Token') == token(target)
                   for i in methods[token(number)]['Instructions'] or []), (token(number), token(target))

    def params(*names):
        return {str(i + 1): name for i, name in enumerate(names) if name}

    def scopes(*names):
        return {str(i): name for i, name in enumerate(names) if name}

    # Bind both physical delegate definitions through each wrapper's exact Invoke operands.
    pairs = [
        (0x060001B6, 0x02000030, 0x0200004B, 'ReadSessionTokenFunction', 0x060001F0, 0x06000264,
         'Manager060000C0 decrypts output and publishes changed token; exact Common060001C0 consumer logs Received new session token.'),
        (0x060001B8, 0x02000032, 0x0200004D, 'ReadStateCodeFunction', 0x060001F8, 0x0600026C,
         'Timer manager060000C0 switches on native Int32 state;06000107 reads same code. No unsupported enum phase names assigned.'),
        (0x060001B9, 0x02000033, 0x0200004E, 'ReadLicenseDataFunction', 0x060001FC, 0x06000270,
         '0600015B obtains output/result, decrypts bytes and feeds LIC parser06000129; actual result remains native Int32.'),
        (0x060001BA, 0x02000034, 0x0200004F, 'CreateCertificateFunction', 0x06000200, 0x06000274,
         '0600004B supplies five string inputs, decrypts returned bytes and parses/registers a CERT record; opaque native algorithm not inferred.'),
        (0x060001BB, 0x02000035, 0x02000050, 'ComputeCloudHashFunction', 0x06000204, 0x06000278,
         'ajn constructors06000133/134 hash supplied bytes; certificate/signature verification consumes the resulting hash. No algorithm name claimed.'),
        (0x060001BC, 0x02000036, 0x02000051, 'VerifyCloudSignatureFunction', 0x06000208, 0x0600027C,
         'akb06000026 passes serialized signature and supplied hash; managed zero-result branch determines verification boolean and failure event.'),
        (0x060001BD, 0x02000037, 0x02000052, 'VerifyCloudSignatureWithPublicKeyFunction', 0x0600020C, 0x06000280,
         'akb06000027 passes serialized signature/hash/public-key bytes and publishes on failed managed verification result.'),
        (0x060001C0, 0x0200003A, 0x02000055, 'ReadEncryptedTextValueFunction', 0x06000218, 0x0600028C,
         'Manager060000E6 passes string selector, decrypts returned bytes and returns plaintext String; no specific setting/value domain established.')]
    for wrapper, win, unix, name, win_invoke, unix_invoke, reason in pairs:
        called(wrapper, win_invoke)
        called(wrapper, unix_invoke)
        for number, invoke in ((win, win_invoke), (unix, unix_invoke)):
            assert token(number) not in aliases
            assert type_rows[token(number)]['BaseType'] == 'System.MulticastDelegate'
            assert any(m['Token'] == token(invoke) and m['Name'] == 'Invoke' for m in type_rows[token(number)]['Methods'])
            add('Types', number, name, f'Exact wrapper{token(wrapper)} calls Invoke{token(invoke)} of this physical native delegate. {reason} Keep original Winapi/native signatures and calling convention.')
            boundaries.extend(dict(Token=m['Token'], Signature=m['Signature'], Flags=m['Flags'],
                Limitation='Runtime delegate Invoke/BeginInvoke/EndInvoke and scoped parameters require their complete family route; this type alias does not rename entry points.')
                for m in type_rows[token(number)]['Methods'] if m['Name'] in ('Invoke', 'BeginInvoke', 'EndInvoke'))
    called(0x060000C0, 0x060001B6)
    called(0x0600015B, 0x060001B9)
    called(0x0600004B, 0x060001BA)
    called(0x06000026, 0x060001BC)
    called(0x06000027, 0x060001BD)
    called(0x060000E6, 0x060001C0)

    for wrapper, win, unix in [(0x060001B2, 0x0200002C, 0x02000047), (0x060001B3, 0x0200002D, 0x02000048),
                               (0x060001B4, 0x0200002E, 0x02000049), (0x060001B5, 0x0200002F, 0x0200004A),
                               (0x060001BE, 0x02000038, 0x02000053), (0x060001BF, 0x02000039, 0x02000054),
                               (0x060001C1, 0x0200003B, 0x02000056)]:
        incoming = edges(wrapper)
        for number in (win, unix):
            unknown('Types', number, f'Native delegate wired by{token(wrapper)} with {len(incoming)} wrapper callers. Export strings and typed buffer/status signatures establish ABI only; managed callers expose no semantic operation beyond argument/result forwarding. Existing start/stop/pause/resume/license-status/config labels are not proof, so do not propagate them into type aliases.')

    for number, name, reason in [
        (0x02000028, 'WindowsMemoryFlags', f'Exact kernel32 VirtualAlloc060001C4 allocation argument and VirtualFree060001C6 free argument use this UInt32 Flags enum; authoritative value definitions at {WIN}.'),
        (0x0200002A, 'DllEntryPointReason', f'Native entry-point Invoke060001DC accepts this enum; loader1D4 supplies1 after loading entry-point RVA, unload supplies0. DllMain signature/reasons: {DLL}.'),
        (0x0200002B, 'DllEntryPointFunction', f'Windows loader1D4 reads PE entry-point RVA, creates this function-pointer delegate and invokes it with image base/reason1/null reserved. Preserve BOOL(IntPtr,reason,IntPtr) and Winapi convention. {DLL}'),
        (0x0200003E, 'PeBaseRelocationBlock', f'Constructor224 reads pageRva at0, blockSize at4, then WORD entries; only HIGHLOW3/DIR6410 low12 offsets retained, Apply225 uses them. Observed implementation and {PE}.'),
        (0x0200003F, 'PeImportDescriptor', f'Constructor227 reads five consecutive DWORDs; Resolve228 uses DLL name RVA, lookup/IAT entries and name/ordinal imports. Observed implementation and {PE}.'),
        (0x02000044, 'MemoryProtectionFlags', f'libc.so mmap0600023E protection and mprotect0600023F protection parameter use this enum, corroborated by glibc PROT values at {MMAP}.'),
        (0x02000045, 'MemoryMappingFlags', f'libc.so mmap0600023E flags parameter uses this enum, corroborated by glibc Linux MAP values at {MMAP}; no macOS compatibility asserted.'),
        (0x02000046, 'DynamicLibraryLoadFlags', f'libdl.so dlopen06000240 mode parameter uses this enum, corroborated by glibc RTLD values at {DL}; preserve native library names/ABI.'),
        (0x02000076, 'PePageProtectionData', 'Class14 owns RVA field1F6, consumed by PE section GetPageProtection220 through RuntimeHelpers.InitializeArray. Its other String metadata field has no observed behavior and remains unresolved; do not claim this ordinary container is a compiler closure.')]:
        assert token(number) not in aliases
        add('Types', number, name, reason)
    for number, entry in [(0x060001C4, 'VirtualAlloc'), (0x060001C6, 'VirtualFree'), (0x0600023E, 'mmap'),
                          (0x0600023F, 'mprotect'), (0x06000240, 'dlopen')]:
        assert methods[token(number)]['NativeImport']['EntryPoint'] == entry

    enums = [(0x040000E9,4096,'Commit',WIN), (0x040000EA,8192,'Reserve',WIN), (0x040000EC,32768,'Release',WIN),
             (0x040000ED,65536,'Free',WIN), (0x040000EE,131072,'Private',WIN), (0x040000F0,524288,'Reset',WIN),
             (0x040000F1,1048576,'TopDown',WIN), (0x040000F2,2097152,'WriteWatch',WIN), (0x040000F3,4194304,'Physical',WIN),
             (0x040000F7,536870912,'LargePages',WIN),
             (0x04000105,0,'ProcessDetach',DLL), (0x04000106,1,'ProcessAttach',DLL), (0x04000107,2,'ThreadAttach',DLL), (0x04000108,3,'ThreadDetach',DLL),
             (0x04000170,0,'None',MMAP), (0x04000171,1,'Read',MMAP), (0x04000172,2,'Write',MMAP), (0x04000173,4,'Execute',MMAP),
             (0x04000175,0,'File',MMAP), (0x04000176,1,'Shared',MMAP), (0x04000177,2,'Private',MMAP),
             (0x04000178,15,'TypeMask',MMAP), (0x04000179,16,'Fixed',MMAP), (0x0400017A,32,'Anonymous',MMAP),
             (0x0400017C,0,'Local',DL), (0x0400017D,1,'Lazy',DL), (0x0400017E,2,'Now',DL), (0x0400017F,4,'NoLoad',DL),
             (0x04000180,8,'DeepBind',DL), (0x04000181,256,'Global',DL), (0x04000182,4096,'NoDelete',DL)]
    for number, value, name, url in enums:
        assert storage[token(number)]['IsLiteral'] and storage[token(number)]['Constant'] == value
        field(number, name, f'Literal {value} in exact typed native API enum. Unique observed ABI value/meaning corroborated by {url}; not inferred from declaration order or spelling.', literal=True)
        abi_facts.append(dict(Token=token(number), Value=value, Meaning=name, Source=url))
    for number, reason in [(0x040000EB, 'Value16384 can denote MEM_DECOMMIT or MEM_REPLACE_PLACEHOLDER; no token consumer disambiguates intended declaration meaning.'),
                           (0x040000EF, 'Value262144 can denote MEM_MAPPED or MEM_RESERVE_PLACEHOLDER; unused native enum member lacks disambiguating call evidence.'),
                           (0x040000F4, 'Duplicate8388608 shares native MEM_ROTATE/MEM_DIFFERENT_IMAGE_BASE_OK meanings with siblingF5; no token-to-use/identity association establishes which synonym.'),
                           (0x040000F5, 'Duplicate8388608 shares native MEM_ROTATE/MEM_DIFFERENT_IMAGE_BASE_OK meanings with siblingF4; no token-to-use/identity association establishes which synonym.'),
                           (0x040000F6, 'Value16777216 can denote MEM_RESET_UNDO or MEM_IMAGE. The shared enum includes allocation/free and region-state constants; no token consumer establishes the intended declaration meaning.'),
                           (0x0400012B, 'Unused Int32 default metadata4, zero references; do not invent relocation entry/header role.'),
                           (0x04000130, 'Unused Int32 default metadata2, zero references; no observed hint-size role.'),
                           (0x040001F7, 'String field has I1(32) default metadata, no reads/writes; no behavioral role established.')]:
        assert not edges(number)
        unknown('Fields', number, reason)

    for number, name, reason in [
        (0x0400012A, 'headerByteCount', 'Relocation cctor226 writes8; ctor224 uses this to find WORD entries and compute count=(blockSize-headerBytes)/2.'),
        (0x0400012C, 'pageRva', 'Relocation ctor224 reads first DWORD at0;225 adds pageRva+relocationOffset to loaded image base to find patch address.'),
        (0x0400012D, 'blockByteCount', 'Relocation ctor224 reads DWORD at4; determines entry count and225 advances to next block by this byte count.'),
        (0x0400012E, 'relocationOffsets', 'ctor224 retains only low12 bits for relocation types3/10, not encoded type/offset WORDs;225 enumerates these offsets for address patching.'),
        (0x0400012F, 'descriptorByteCount', 'Import cctor229 writes20;228 walks import descriptors using that size.'),
        (0x04000131, 'lookupTableRva', 'Import ctor227 first DWORD at0;228 uses it to find name/ordinal lookup thunk sequence.'),
        (0x04000132, 'timeDateStamp', 'Import ctor227 second DWORD at4;20-byte import table layout corroborated by PE specification. Preserve raw Int32.'),
        (0x04000133, 'forwarderChain', 'Import ctor227 third DWORD at8;20-byte import table layout corroborated by PE specification.'),
        (0x04000134, 'nameRva', 'Import ctor227 fourth DWORD at12;228 adds it to base and PtrToStringAnsi supplies LoadLibrary path.'),
        (0x04000135, 'addressTableRva', 'Import ctor227 fifth DWORD at16;228 uses it for writing GetProcAddress results to import address table.')]:
        field(number, name, reason + ' Exact constructor/consumer behavior corroborates ' + PE)
    blob = storage['0x040001F6']
    assert blob['InitialValueLength'] == 8 and blob['InitialValuePreviewHex'] == '0108020410402040'
    assert blob['InitialValueSha256'] == '3139481E76ADFE6F90D823AFF88C786BFF7854ADC2713B791EC5F57AE6294CB9'
    assert [(r['Source'], r['Reference']['Offset']) for r in edges(0x040001F6)] == [('m0035:0x06000220',9)]
    field(0x040001F6, 'pageProtectionTable', f'Exact8-byte RVA is initialized into Byte[2,2,2] by220, indexed by execute/read/write section bits to produce Win32 PAGE protection. Preserve full payload SHA and layout; table values corroborated by {WIN}.')
    method(0x06000220, 'Section characteristics masks0x20000000/0x40000000/0x80000000 become Boolean byte indices for execute/read/write protection table, respectively. Keep sign-extension and original initialization behavior.', locals_=scopes('executeIndex','readIndex','writeIndex'))
    method(0x06000224, 'Reads relocation pageRva/block size, WORD count, encoded entry and high4 type; stores low12 offsets only for3/10. Do not change unsupported-type handling.', params('blockAddress'), scopes('entryCount','entryIndex','encodedEntry','relocationType'))
    method(0x06000225, 'Directory RVA cursor walks relocation blocks; image-base argument is supplied by loader but method actually reads static base. Third argument adds relocation delta to32/64-bit targets. Local5 is resulting32-bit value, not original value.',
           params('relocationDirectory','imageBase','relocationDelta'), scopes('blockRva','block','offsetEnumerator','relocationOffset','patchAddress','relocatedValue'))
    method(0x06000227, 'Five consecutive DWORDs at0/4/8/12/16 instantiate import descriptor; field offset local increments by Marshal.SizeOf<Int32>.', params('descriptorAddress'), scopes('fieldOffset'))
    method(0x06000228, 'Loads imported modules and resolves name/ordinal thunks; preserves existing pointer-width/write/fallback behavior. Names follow full GetProcAddress/address-table dataflow.',
           params('importDirectory','imageBase'), scopes('importedModules','descriptorRva','descriptor','moduleHandle','thunkByteOffset','lookupThunkAddress','functionAddress','lookupThunkValue','ordinal','functionName','addressTableByteOffset'))

    assert len({(r['Kind'],r['Token']) for r in rows}) == len(rows)
    spec = dict(Format=1, TargetRoot=state['Pass']['SourceTree63'], ContractReferenceSha256=state['Compatibility']['ContractReferences63']['Sha256'], Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    input_state = dict(Pass=dict(SourceTree63=state['Pass']['SourceTree63']), Maps={'63':state['Maps']['63']}, Compatibility=dict(ContractReferences63=state['Compatibility']['ContractReferences63']))
    selected = {r['Token'] for r in rows} | {r['Token'] for r in retained}
    preimage = dict(Format=ledger['Format'], **{kind:[r for r in ledger[kind] if r['Module']=='Knx.CloudKit.dll' and r['Token'] in selected] for kind in ('Types','Fields','Methods')})
    for name, document in [('cloud-loader-input-state01.json',input_state), ('cloud-loader-ledger-preimage01.json',preimage),
                          ('cloud-loader-spec01.json',spec), ('cloud-loader-review01.json',review), ('cloud-loader-evidence01.json',dict(
        Format=1, PhysicalPath=str(physical), Sha256=physical_hash, Mvid=types['Mvid'], Map=state['Maps']['63']['Path'], MapSha256=inventory['MapSha256'],
        Sources=[dict(Path=p,Sha256=digest(p)) for p in (*paths,args.consumer_bodies,args.graph)], GraphPhysicalInputsVerified=len(meta['Modules']),
        References=references, RetainedUnresolved=retained, RuntimeDelegateBoundaries=boundaries, PlatformFacts=abi_facts,
        Methods=[methods[r['Token']] for r in rows if r['Kind']=='Methods'], SupportingMethods=[methods[token(n)] for n in (0x060001D4,0x060001D5,0x06000226,0x06000229,*[p[0] for p in pairs])],
        ExternalConsumers=consumer['Methods'], FieldStorage=[storage[r['Token']] for r in rows if r['Kind']=='Fields'],
        Limitations='ABI names inferred from exact native signature/producer/storage plus primary sources checked2026-10-03. No native algorithm, missing lifecycle purpose or macOS support inferred. Native map/SDK/contract checks mandatory; no ETS edits/build/runtime claim.'))]:
        (output/name).write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8')
    print('Prepared', {k:len(review[k]) for k in ('Types','Fields','Methods')}, 'runtime delegate boundaries',len(boundaries))


if __name__ == '__main__':
    main()
