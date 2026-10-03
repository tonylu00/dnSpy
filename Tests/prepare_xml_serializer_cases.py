"""Prepare case XML from native physical reader/writer IL inventories.

Writes test manifests only. Never modifies source or binaries.
"""
import argparse
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET


def prepare(reader, writer, application_root):
    source = pathlib.Path(reader['Input']).resolve()
    root = pathlib.Path(application_root).resolve()
    if source != pathlib.Path(writer['Input']).resolve() or not source.is_relative_to(root):
        raise ValueError('Reader/writer inventories must identify one physical application module')
    for key in ('Identity', 'Mvid', 'Sha256'):
        if reader[key] != writer[key]: raise ValueError('Conflicting physical inventories')
    if hashlib.sha256(source.read_bytes()).hexdigest().upper() != reader['Sha256']:
        raise ValueError('Stale physical inventory')
    doc = ET.Element('Tests', Source=str(source), Identity=reader['Identity'], Mvid=reader['Mvid'], Sha256=reader['Sha256'])
    dependencies = ET.SubElement(doc, 'Dependencies')
    for directory in dict.fromkeys([source.parent, root]):
        ET.SubElement(dependencies, 'Directory').text = str(directory)
    for kind, inventory in [('reader', reader), ('writer', writer)]:
        for method in inventory['Methods']:
            owner, method_name = method['Signature'].split(' ', 1)[1].split('::', 1)
            method_name = method_name.split('(', 1)[0]
            if method_name == 'InitCallbacks': continue
            arguments = [p for p in method['Parameters'] if p['Sequence'] is not None]
            if len(arguments) != 1: raise ValueError('Expected a single-value enum helper')
            row = ET.SubElement(doc, 'Method', Type=owner, Name=method_name, Kind=kind, Token=method['Token'])
            if kind == 'reader':
                if arguments[0]['Type'] != 'System.String': raise ValueError('Reader input is not XML text')
                calls = [i['Operand'].get('Text', '') for i in method['Instructions'] if isinstance(i.get('Operand'), dict)]
                if not any('::TryGetValue(System.String,System.Int32&)' in c for c in calls):
                    raise ValueError('Reader lacks reviewed enum dispatch evidence')
                keys = list(dict.fromkeys(i['Operand'] for i in method['Instructions'] if i['OpCode'] == 'ldstr' and isinstance(i['Operand'], str)))
                invalid = '__DNSpy_INVALID_XML_ENUM_VALUE__'
                if invalid in keys: raise ValueError('Invalid probe value is a real XML key')
                for value in keys + [invalid, '']:
                    ET.SubElement(row, 'Case').text = value
                ET.SubElement(row, 'Case', Null='true')
            else:
                calls = [i['Operand'].get('Text', '') for i in method['Instructions'] if isinstance(i.get('Operand'), dict)]
                if not any('RuntimeHelpers::InitializeArray' in c for c in calls) or not any('XmlSerializationWriter::FromEnum' in c for c in calls):
                    raise ValueError('Writer lacks reviewed RVA enum evidence')
                for value in ['0', '1', '2', '4', '8', '16', '32', '64', '-1', '9223372036854775807']:
                    ET.SubElement(row, 'Case').text = value
                ET.SubElement(row, 'Case', AllFlags='true')
    return doc


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('reader', 'writer', 'application-root', 'output'): parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    read = lambda path: json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))
    document = prepare(read(args.reader), read(args.writer), args.application_root)
    ET.indent(document)
    with pathlib.Path(args.output).open('xb') as stream:
        ET.ElementTree(document).write(stream, encoding='utf-8', xml_declaration=True)
    print('Prepared exact enum cases:', len(document.findall('Method/Case')))
