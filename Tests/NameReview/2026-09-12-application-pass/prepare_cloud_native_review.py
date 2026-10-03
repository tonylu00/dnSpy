"""Prepare the reviewed CloudKit native-buffer/header block; never edit ETS files."""
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
    for option in ('state', 'inventory', 'type-evidence', 'method-evidence', 'marshal-evidence', 'extra-evidence', 'graph', 'output'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    state, inventory = read(args.state), read(args.inventory)
    types, bodies, marshal, extra = map(read, (args.type_evidence, args.method_evidence, args.marshal_evidence, args.extra_evidence))
    physical = pathlib.Path(state['Pass']['SourceTree63']) / 'Knx.CloudKit.dll'
    for evidence in (types, bodies, marshal, extra):
        assert pathlib.Path(evidence['Input']).resolve() == physical.resolve()
        assert evidence['Sha256'] == digest(physical) and evidence['Mvid'] == types['Mvid']
    assert inventory['MapSha256'] == state['Maps']['63']['Sha256'] == digest(state['Maps']['63']['Path'])
    reports = [r for r in inventory['Reports'] if r['Module'] == 'Knx.CloudKit.dll']
    assert {r['Kind'] for r in reports} == {'Types', 'Methods', 'Fields'}
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    methods = {m['Token']: m for m in bodies['Methods'] + extra['Methods']}
    field_details = {f['Token']: f for f in marshal['Fields']}
    current = next(m for m in ET.parse(state['Maps']['63']['Path']).getroot().findall('Module') if m.get('Path') == 'Knx.CloudKit.dll')
    mapped_methods = {m.get('Token'): m for m in current.findall('Method')}
    rows = []

    def add(kind, token, name, reason, parameters=None, locals_=None, disposition='rename'):
        row = dict(Kind=kind, Module='Knx.CloudKit.dll', Token=token, Reason=reason, Disposition=disposition)
        if name:
            row['NewName'] = name
        if parameters:
            row['ParameterNames'] = parameters
        if locals_:
            row['LocalNames'] = locals_
        rows.append(row)

    def field(token, name, reason):
        assert field_details[token]['MappingBlocker'] is None
        add('Fields', token, name, reason)

    def method(token, name, reason, parameters=None, locals_=None):
        assert token in methods and methods[token]['HasBody']
        # Carry earlier accepted scope aliases into a newly recorded method row.
        parameters, locals_ = dict(parameters or {}), dict(locals_ or {})
        old = mapped_methods.get(token)
        if old is not None:
            for p in old.findall('Parameter'):
                parameters.setdefault(p.get('Sequence'), p.get('NewName'))
            for local in old.findall('Local'):
                locals_.setdefault(local.get('Index'), local.get('NewName'))
        add('Methods', token, name, reason, parameters, locals_)

    for index in range(11):
        capacity = 1024 << index
        type_token = f'0x{0x0200005A + index:08X}'
        first_field = 0x0400019F + index * 2
        first_method = 0x0600029D + index * 5
        typ = next(t for t in types['Types'] if t['Token'] == type_token)
        assert typ['Layout'] == dict(PackingSize=1, ClassSize=0)
        encoded = field_details[f'0x{first_field + 1:08X}']['Marshal']
        assert encoded['Kind'] == 'FixedArrayMarshalType' and encoded['Size'] == capacity
        assert encoded['IsSizeValid'] and not encoded['IsElementTypeValid']
        reason = (f'Native methods 0x{first_method:08X}-0x{first_method + 4:08X}: factory allocates byte[{capacity}], '
                  f'Array.Clear covers {capacity}, Copy uses Take(count).ToArray, UTF8.GetString consumes the prefix, '
                  f'and capacity getter returns {capacity}. Sequential Pack=1 and fixed marshal Size={capacity} retain '
                  'their original unspecified element type. Distinct buffer owners permit identical behavior aliases.')
        field(f'0x{first_field:08X}', 'Capacity', reason)
        field(f'0x{first_field + 1:08X}', 'bytes', reason)
        names = ['CreateEmptyBuffer', 'ClearBuffer', 'CopyBufferPrefix', 'DecodeUtf8Prefix', 'GetBufferCapacity']
        if index == 10:
            names[3] = 'DecodeUtf8PrefixWithoutTrailingNulls'
        for offset, name in enumerate(names):
            token = f'0x{first_method + offset:08X}'
            instructions = methods[token]['Instructions']
            has_trim = any(isinstance(i['Operand'], dict) and 'System.String::TrimEnd' in i['Operand'].get('Text', '') for i in instructions)
            assert has_trim == (index == 10 and offset == 3)
            detail = reason + (' This decoder calls TrimEnd(new char[1]); embedded NULs remain, so it is not a terminator scan.' if has_trim else '')
            method(token, name, detail, {'1': 'count'} if offset in (2, 3) else None,
                   {'0': 'buffer'} if offset == 0 else None)
    for token, name in zip(range(0x0400019B, 0x0400019F), ('major', 'minor', 'build', 'revision')):
        field(f'0x{token:08X}', name, '0600029C loads these four fields in order into System.Version(Int32,Int32,Int32,Int32); 0600029B initializes all four to zero. Preserve SequentialLayout/Pack=1.')
    method('0x0600029B', 'CreateEmptyNativeVersion', 'initobj/local 0 initializes and returns the native four-part version; local 1 is unused and receives no invented role.', locals_={'0': 'version'})
    method('0x0600029C', 'ToManagedVersion', 'Direct four-field System.Version construction establishes major/minor/build/revision order.')

    loader_fields = {
        '0x040000DD': ('isLoaded', '060001CE reads the volatile flag; 060001D4 sets it after binding exports; unload clears it.'),
        '0x040000DE': ('nativeCallsBlocked', '060001D8/1D9 set/clear it; 060001D6 rejects acquisition while it is set.'),
        '0x040000DF': ('imageBaseAddress', '060001D4 stores VirtualAlloc output here; image headers, exports and entry point are addressed from this base.'),
        '0x040000E0': ('imageHeaders', '060001D4 constructs Struct29 from resource bytes; section/directory/base/entry-point consumers use the parsed record.'),
        '0x040000E1': ('importedLibraryHandles', '060001D4 stores 06000228 output; that helper loads import DLLs with LoadLibrary, adds handles, and unload 060001D5 calls FreeLibrary over the list.'),
        '0x040000E2': ('delegatesByType', '060001CC indexes Type->Delegate; 060001D4 stores resolved exports; unload clears the cache.'),
        '0x040000E3': ('activeNativeCallCount', '060001D6/1D7 use Interlocked.Increment/Decrement; 060001D0 reads the active count.'),
        '0x040000E4': ('nativeLibraryUserCount', '060001D4 increments library users; 060001D3 reads it; unload exchanges the count to zero.'),
        '0x040000E5': ('loadLock', '060001D4 passes this object to Monitor.Enter/Exit around loading.'),
        '0x040000E6': ('exportTypesByName', 'Static initializer maps exact native export-name literals to delegate Types; 060001CD looks up a Type by export name.'),
        '0x04000166': ('isLoaded', '06000246 reads the volatile flag; loader 0600024C sets it after export binding; unload clears it.'),
        '0x04000167': ('nativeCallsBlocked', '06000250/251 set/clear it; 0600024E rejects acquisition while set.'),
        '0x0400016A': ('delegatesByType', '06000244 indexes Type->Delegate; loader binds dlsym output with Marshal.GetDelegateForFunctionPointer and adds by Type; unload clears it.'),
        '0x0400016B': ('activeNativeCallCount', '0600024E/24F use Interlocked.Increment/Decrement; 06000248 tests active calls.'),
        '0x0400016C': ('nativeLibraryUserCount', '0600024C increments users; 0600024B reads the count; unload exchanges it to zero.'),
        '0x0400016D': ('exportTypesByName', '06000252 maps exact native export strings to delegate Types; 06000245 performs name lookup.')
    }
    for token, (name, reason) in loader_fields.items():
        field(token, name, reason + ' Original native export strings remain untouched.')
    for token in ('0x04000168', '0x04000169'):
        add('Fields', token, '', '06000252 only initializes this field (IntPtr.Zero or new List<IntPtr>). Complete physical graph has no read or later write. Dynamic/reflection/external use and intended lifetime role lack evidence; do not infer a library handle or dependency list.', disposition='unresolved')

    pe_url = 'https://learn.microsoft.com/en-us/windows/win32/debug/pe-format'
    elf_url = 'https://gabi.xinuos.com/elf/02-eheader.html'
    definitions = {
        '0x0200003C': ('PeSectionHeader', '0600021F parses the 40-byte PE section row, beginning with an 8-byte name; 06000220 derives page protection from characteristics.'),
        '0x0200003D': ('PeDataDirectory', '06000222 reads consecutive RVA/size Int32 values; export/import/relocation directory getters select these records.'),
        '0x02000040': ('PeExportDirectory', '0600022A reads the 40-byte export table; 0600022B resolves export name/function tables into delegates.'),
        '0x02000041': ('PeImageHeaders', '0600022D unwraps the optional stored SHA1 prefix and parses PE file/optional headers, sections and directories; base/relocation/export helpers consume them.'),
        '0x02000057': ('ElfImageHeader', '06000293 unwraps the stored 13-byte SHA1 prefix and parses ELF identification bytes 4/5/6; loader verifies the digest prefix.'),
        '0x02000029': ('MemoryProtectionFlags', 'Exact UInt32 enum values and FlagsAttribute match PAGE_* constants; VirtualAlloc/VirtualProtect use this parameter type. https://learn.microsoft.com/en-us/windows/win32/memory/memory-protection-constants')
    }
    for token, (name, reason) in definitions.items():
        add('Types', token, name, reason + (' ' + elf_url if token == '0x02000057' else ' ' + pe_url))
    section = ['HeaderSize', 'NameLength', 'numericFieldsOffset', 'name', 'virtualSize', 'virtualAddress', 'sizeOfRawData',
               'pointerToRawData', 'pointerToRelocations', 'pointerToLineNumbers', 'numberOfRelocations', 'numberOfLineNumbers', 'characteristics']
    for offset, name in enumerate(section):
        field(f'0x{0x0400011A + offset:08X}', name, '06000221 assigns size 40/name length 8; 0600021F records numeric-fields offset=section-row offset+8, decodes the name, then reads each documented field in order with Int32/Int16 widths. ' + pe_url)
    for offset, name in enumerate(['EntrySize', 'virtualAddress', 'size']):
        field(f'0x{0x04000127 + offset:08X}', name, '06000223 assigns entry size 8; 06000222 reads RVA at byte 0 and size at byte 4; directory consumers add the RVA to image base. ' + pe_url)
    export = ['DirectorySize', 'AddressEntrySize', 'characteristics', 'timeDateStamp', 'majorVersion', 'minorVersion', 'nameRva',
              'ordinalBase', 'numberOfFunctions', 'numberOfNames', 'addressOfFunctions', 'addressOfNames', 'addressOfNameOrdinals']
    for offset, name in enumerate(export):
        field(f'0x{0x04000136 + offset:08X}', name, '0600022C assigns directory size 40; constant b=4 matches export address-entry width. 0600022A reads export flags/timestamp, Int16 versions, then name RVA/base/counts/table RVAs in exact documented order. ' + pe_url)
    image = ['peHeaderOffset', 'machine', 'numberOfSections', 'sizeOfOptionalHeader', 'addressOfEntryPoint',
             'imageBaseLowOrBaseOfData', 'imageBaseHighOr32BitImageBase', 'sizeOfImage', 'sizeOfHeaders', 'sections', 'dataDirectories', 'storedSha1']
    for offset, name in enumerate(image):
        field(f'0x{0x04000157 + offset:08X}', name, '0600022D parses e_lfanew and documented PE-relative header offsets. 06000231 uses words at +48/+52 as low/high for PE32+ and +52 as PE32 image base (+48 is PE32 BaseOfData). Section/directory lists are populated by their parsers. Loader 060001D4 compares SHA1.ComputeHash(imageBytes) to field af; it is a digest, also used for unwrapping. ' + pe_url)
    for token in range(0x04000143, 0x04000157):
        add('Fields', f'0x{token:08X}', '', 'Constants and static size initializer observed, but these definitions have no static reads in the physical graph. Inlined literals include duplicate offsets and indexes; missing source-level association prevents assigning a unique semantic role to each original field.', disposition='unresolved')
    for offset, name in enumerate(['StoredSha1PrefixLength', 'elfClass', 'dataEncoding', 'identificationVersion', 'storedSha1Prefix']):
        field(f'0x{0x04000193 + offset:08X}', name, '06000293 allocates the 13-byte prefix and parses ELF e_ident[4]/[5]/[6]. Loader 0600024C compares SHA1.ComputeHash(imageBytes).Take(prefix.Length) with that prefix. Preserve original 13-byte truncation and byte mutation. ' + elf_url)
    protection = ['Execute', 'ExecuteRead', 'ExecuteReadWrite', 'ExecuteWriteCopy', 'NoAccess', 'ReadOnly', 'ReadWrite', 'WriteCopy', 'Guard', 'NoCache', 'WriteCombine']
    expected = [16, 32, 64, 128, 1, 2, 4, 8, 256, 512, 1024]
    for offset, (name, value) in enumerate(zip(protection, expected)):
        token = f'0x{0x040000F9 + offset:08X}'
        assert field_details[token]['Constant'] == value
        field(token, name, f'Flags enum literal {value:#x}, checked against the Windows PAGE_{name} constant and native VirtualAlloc/VirtualProtect parameter type. https://learn.microsoft.com/en-us/windows/win32/memory/memory-protection-constants')

    method('0x060001CF', 'Uses64BitPeLayout', 'Wrapper delegates to 0600022E, which selects layout from Machine/Is64BitProcess/IntPtr.Size; it is not solely an image-width assertion.')
    scopes = {
        '0x0600021F': ({'1': 'imageBytes', '2': 'sectionHeaderOffset'}, {}),
        '0x06000222': ({'1': 'imageBytes', '2': 'directoryOffset'}, {}),
        '0x0600022A': ({'1': 'directoryAddress'}, {'0': 'fieldOffset'}),
        '0x0600022D': ({'1': 'imageBytes'}, {'0': 'storedHashPrefixLength', '1': 'encodedByteIndex', '2': 'headerByteIndex', '3': 'sectionIndex', '4': 'directoryIndex'}),
        '0x06000293': ({'1': 'imageBytes'}, {'0': 'encodedByteIndex'}),
        '0x06000234': ({'1': 'sectionIndex'}, {}),
        '0x06000235': ({'1': 'directoryIndex'}, {}),
        '0x06000233': ({'1': 'actualImageBase'}, {'0': 'preferredImageBase'}),
        '0x06000239': ({}, {'0': 'headers'}),
        '0x06000297': ({}, {'0': 'header'})
    }
    for token, (parameters, locals_) in scopes.items():
        method(token, '', 'Complete IL producer/consumer review: byte arrays feed the header parser/unwrapper; offsets select documented rows/fields; loop slots walk encoded bytes/header copies/sections/directories; base helper assembles the preferred address; factories initialize and return their header local. Unused obfuscation locals receive no invented role.', parameters, locals_)

    graph = sqlite3.connect(args.graph)
    graph_meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    graph_module = next(x for x in graph_meta['Modules'] if x['Id'] == 'm0035')
    assert graph_module['Sha256'] == types['Sha256'] and graph_module['Mvid'] == types['Mvid']
    references = {}
    for row in rows:
        if row['Kind'] != 'Fields':
            continue
        edges = [json.loads(x[0]) for x in graph.execute('select data from edges where target=?', ('m0035:' + row['Token'],))]
        # These private/native owners currently have only own-module IL edges.
        assert all(edge['From'].startswith('m0035:') for edge in edges)
        references[row['Token']] = edges
    graph.close()
    for token in ('0x04000168', '0x04000169'):
        assert [(e['From'], e['Operation']) for e in references[token]] == [('m0035:0x06000252', 'stsfld')]
    for token in range(0x04000143, 0x04000157):
        edges = references[f'0x{token:08X}']
        assert not edges or (token == 0x04000143 and len(edges) == 1 and edges[0]['Operation'] == 'stsfld')
    spec = dict(TargetRoot=state['Pass']['SourceTree63'], ContractReferenceSha256=state['Compatibility']['ContractReferences63']['Sha256'],
                Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    evidence = dict(Format=1, Kind='CloudNativeBehaviorReview', Input=str(physical), Sha256=types['Sha256'], Mvid=types['Mvid'],
                    Map=state['Maps']['63']['Path'], MapSha256=state['Maps']['63']['Sha256'],
                    Inputs=[dict(Path=p, Sha256=digest(p)) for p in (args.type_evidence, args.method_evidence, args.marshal_evidence, args.extra_evidence)],
                    FieldReferences=references, ReviewedRows={kind: len(review[kind]) for kind in ('Types', 'Fields', 'Methods')},
                    PendingMethodCorrection=dict(Token='0x06000294', CurrentAlias='Is64BitElfImage',
                        Evidence='No physical incoming IL references. Class=1 returns true on a 64-bit process; unknown class returns true. The alias is not an accurate width predicate. Intended consumer role and guarded alias removal remain unresolved.'),
                    Limits='Private field/static IL evidence does not exclude reflection/dynamic lookup or external consumers. No ETS export/build, native library execution or unchanged-App compatibility claimed.')
    output = pathlib.Path(args.output)
    output.mkdir(exist_ok=False)
    for name, document in (('cloud-native-spec01.json', spec), ('cloud-native-review01.json', review), ('cloud-native-evidence01.json', evidence)):
        with (output / name).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(document, indent=2) + '\n')
    print('Prepared native block:', evidence['ReviewedRows'])


if __name__ == '__main__':
    main()
