"""Compare separately executed serializer helpers against checked binary hashes."""
import argparse
import hashlib
import json
import os
import pathlib
import xml.etree.ElementTree as ET


def compare(metadata, pairs):
    if not metadata.get('Success') or not metadata.get('Modules'): raise ValueError('Metadata comparison has not passed')
    physical = lambda path: os.path.normcase(str(pathlib.Path(path).resolve()))
    expected = {physical(module['Source']): module for module in metadata['Modules']}
    if len(expected) != len(metadata['Modules']): raise ValueError('Repeated physical metadata module')
    modules = []
    failures = []
    seen = set()
    for original_path, rebuilt_path in pairs:
        original = ET.parse(original_path).getroot()
        rebuilt = ET.parse(rebuilt_path).getroot()
        identity = original.get('Identity')
        if not original.get('LoadedPath') or not rebuilt.get('LoadedPath'): raise ValueError('Missing actual loader path evidence')
        key = physical(original.get('LoadedPath'))
        if key in seen: raise ValueError('Repeated physical pair')
        seen.add(key)
        native = expected[key]
        if identity != native['Identity'] or rebuilt.get('Identity') != identity or physical(rebuilt.get('LoadedPath')) != physical(native['Rebuilt']) or original.get('AssemblySha256') != native['OriginalSha256'] or rebuilt.get('AssemblySha256') != native['RebuiltSha256']:
            failures.append({'Identity': identity, 'Reason': 'Loaded physical identities or bytes differ from metadata comparison'})
        before = [dict(row.attrib) for row in original.find('Cases')]
        after = [dict(row.attrib) for row in rebuilt.find('Cases')]
        if not before: failures.append({'Identity': identity, 'Reason': 'No executed cases'})
        if len(before) != len(after): failures.append({'Identity': identity, 'Reason': 'Case count differs'})
        failures.extend({'Identity': identity, 'Case': number, 'Original': a, 'Rebuilt': b} for number, (a, b) in enumerate(zip(before, after)) if a != b)
        digest = lambda path: hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest().upper()
        modules.append({'Identity': identity, 'OriginalSha256': original.get('AssemblySha256'), 'RebuiltSha256': rebuilt.get('AssemblySha256'),
                        'OriginalLoadedPath': original.get('LoadedPath'), 'RebuiltLoadedPath': rebuilt.get('LoadedPath'),
                        'OriginalReportSha256': digest(original_path), 'RebuiltReportSha256': digest(rebuilt_path),
                        'Cases': len(before), 'SuccessfulResults': sum('Result' in row for row in before), 'ExpectedExceptions': sum('Error' in row for row in before),
                        'Methods': len({row['Method'] for row in before})})
    if seen != set(expected): failures.append({'Reason': 'Comparison does not cover the selected physical metadata modules'})
    return {'Format': 1, 'Success': not failures, 'Cases': sum(module['Cases'] for module in modules), 'Modules': modules, 'Failures': failures,
            'Scope': 'Selected dictionary-based enum readers and RVA-backed writers, XML names, null/empty/invalid inputs and flag boundaries. Separate processes with verified loaded bytes. Full ETS/App and complex-document behavior remain pending.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', required=True)
    parser.add_argument('--pair', nargs=2, action='append', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = compare(json.loads(pathlib.Path(args.metadata).read_text(encoding='utf-8-sig')), args.pair)
    with pathlib.Path(args.output).open('x', encoding='utf-8') as stream: stream.write(json.dumps(result, indent=2) + '\n')
    print('PASS' if result['Success'] else 'FAIL', result['Cases'], 'cases;', len(result['Failures']), 'differences')
    raise SystemExit(0 if result['Success'] else 1)
