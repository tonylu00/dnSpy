"""Read-only native inventories for an explicit physical application scope.

Run one module/kind at a time to bound dnlib and JSON retention. This script
does not classify spelling, infer aliases, or modify application/source maps.
Native NeedsReadableName flags select review work, never prove readability.
"""
import argparse
import collections
import hashlib
import json
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    with Path(path).open('rb') as stream:
        value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest().upper()


def relative(root, path):
    return Path(path).resolve().relative_to(root).as_posix().casefold()


def key(module, token):
    return module.replace('\\', '/').casefold(), int(token, 16)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scope', 'cli', 'map', 'ledger', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--reuse-inventory', type=Path,
                        help='Reuse hash-bound native reports from an earlier identical scope/tool inventory')
    args = parser.parse_args()
    input_hashes = {name: digest(getattr(args, name)) for name in ('scope', 'cli', 'map', 'ledger')}
    scope = read(args.scope)
    assert scope['Format'] == 1 and scope['Kind'] == 'PhysicalApplicationScope'
    root = Path(scope['Root']).resolve()
    mapping = ET.parse(args.map).getroot()
    assert Path(mapping.attrib['InputDirectory']).resolve() == root
    ledger = read(args.ledger)
    assert Path(ledger['TargetRoot']).resolve() == root
    physical = {}
    for row in scope['Modules']:
        path = (root / row['Path']).resolve()
        module = relative(root, path)
        assert module not in physical and row['Sha256'] == digest(path)
        physical[module] = row
    aliases = {}
    scoped = {}
    for module in mapping.findall('Module'):
        name = module.attrib['Path'].replace('\\', '/').casefold()
        assert name in physical, ('Mapped module outside explicit scope', name)
        assert module.attrib['Sha256'] == physical[name]['Sha256']
        assert module.attrib['Mvid'].casefold() == physical[name]['Mvid'].casefold()
        for entry in module:
            k = key(name, entry.attrib['Token'])
            assert k not in aliases and k not in scoped
            if entry.attrib.get('NewName'):
                aliases[k] = entry.attrib
            scoped[k] = {
                'ParameterNames': {int(p.attrib['Sequence']) for p in entry.findall('Parameter')},
                'LocalNames': {int(p.attrib['Index']) for p in entry.findall('Local')},
            }
    decisions = {}
    excluded = {row['Path'].replace('\\', '/').casefold(): row
                for row in scope.get('ExcludedGraphModules', [])}
    excluded_decisions = []
    for kind in ('Types', 'Fields', 'Methods'):
        for row in ledger.get(kind, []):
            k = key(row['Module'], row['Token'])
            assert k not in decisions
            if k[0] not in physical:
                assert k[0] in excluded, ('Ledger module outside declared scope', k[0])
                assert row['Sha256'] == excluded[k[0]]['Sha256'] == digest(root / excluded[k[0]]['Path'])
                assert row['Mvid'].casefold() == excluded[k[0]]['Mvid'].casefold()
                excluded_decisions.append({'Module': row['Module'], 'Kind': kind, 'Token': row['Token'],
                                           'Reason': 'Explicitly excluded third-party binary'})
                continue
            assert row['Sha256'] == physical[k[0]]['Sha256']
            assert row['Mvid'].casefold() == physical[k[0]]['Mvid'].casefold()
            decisions[k] = row
    args.output.mkdir(parents=True, exist_ok=False)
    cached = {}
    if args.reuse_inventory:
        cache = read(args.reuse_inventory)
        assert cache['ScopeSha256'] == input_hashes['scope'] and cache['CliSha256'] == input_hashes['cli']
        for row in cache['Reports']:
            k = (row['Module'].replace('\\', '/').casefold(), row['Kind'])
            assert k not in cached and digest(row['Path']) == row['Sha256']
            cached[k] = row
        assert set(cached) == {(module, kind) for module in physical for kind in all_counts_kinds()}
    started = time.monotonic()
    all_counts = {kind: collections.Counter() for kind in ('Types', 'Fields', 'Methods')}
    modules, remaining, reports, unapplied = [], [], [], []
    seen_aliases, seen_decisions = set(), set()
    for number, (name, physical_row) in enumerate(physical.items(), 1):
        path = root / physical_row['Path']
        module_counts = {}
        for kind, command in (('Types', '--review-types'), ('Fields', '--review-fields'), ('Methods', '--review')):
            if cached:
                destination = Path(cached[(name, kind)]['Path'])
                assert digest(destination) == cached[(name, kind)]['Sha256']
            else:
                destination = args.output / (f'{number:03d}-' + kind.lower() + '.json')
                run = subprocess.run(['dotnet', str(args.cli), command, str(path), str(destination)],
                                     capture_output=True, text=True)
                if run.returncode:
                    raise RuntimeError((path, command, run.stdout, run.stderr))
            inventory = read(destination)
            assert inventory['Skips'] == []
            counts = collections.Counter()
            for row in inventory[kind]:
                assert relative(root, Path(inventory['TargetRoot']) / row['Module']) == name
                assert row['Sha256'] == physical_row['Sha256']
                assert row['Mvid'].casefold() == physical_row['Mvid'].casefold()
                k = key(name, row['Token'])
                alias, decision = aliases.get(k), decisions.get(k)
                if alias:
                    assert alias['Signature'] == row['Signature']
                    assert alias['ExpectedName'] == row['OriginalName']
                    seen_aliases.add(k)
                if decision:
                    for column in ('Identity', 'Mvid', 'Sha256', 'Type', 'Signature', 'OriginalName'):
                        assert decision[column] == row[column], (k, column)
                    seen_decisions.add(k)
                counts['Definitions'] += 1
                counts['NativeReviewCandidates'] += bool(row['NeedsReadableName'])
                counts['MappedNames'] += bool(alias)
                disposition = ('Mapped' if alias else 'UnappliedLedgerAlias' if decision and decision.get('NewName')
                               else 'ScopedOnly' if decision and decision.get('UnresolvedDefinitionEvidence')
                               else 'Unresolved' if decision and decision.get('Unresolved')
                               else 'Preserved' if decision and not decision.get('NewName') else 'Unreviewed')
                counts[disposition] += 1
                if disposition == 'UnappliedLedgerAlias':
                    unapplied.append({'Module': physical_row['Path'], 'Kind': kind, 'Token': row['Token'],
                                      'Signature': row['Signature'], 'OriginalName': row['OriginalName'],
                                      'RecordedAlias': decision['NewName'], 'NativeReviewCandidate': row['NeedsReadableName']})
                if row['NeedsReadableName']:
                    counts['Candidate' + disposition] += 1
                    if disposition in ('Unreviewed', 'UnappliedLedgerAlias', 'ScopedOnly'):
                        remaining.append({**row, 'Module': physical_row['Path'], 'Kind': kind})
                if kind == 'Methods':
                    for column, total in (('ParameterNames', 'Parameters'), ('LocalNames', 'Locals')):
                        entries = row.get(column) or []
                        indices = scoped.get(k, {}).get(column, set())
                        index_column = 'Sequence' if column == 'ParameterNames' else 'Index'
                        assert indices <= {p[index_column] for p in entries}
                        counts[total] += len(entries)
                        counts['Aliased' + total] += len(indices)
                        if column == 'ParameterNames':
                            counts['MetadataParameters'] += sum(p['HasMetadata'] for p in entries)
            all_counts[kind].update(counts)
            module_counts[kind] = dict(counts)
            reports.append({'Module': physical_row['Path'], 'Kind': kind,
                            'Path': str(destination), 'Sha256': digest(destination)})
            del inventory
        assert digest(path) == physical_row['Sha256'], ('Input changed during scan', path)
        modules.append({**physical_row, 'Counts': module_counts})
        print(json.dumps({'Completed': number, 'Total': len(physical), 'Module': physical_row['Path'],
                          'Seconds': round(time.monotonic() - started, 2)}), flush=True)
    assert seen_aliases == aliases.keys(), ('Missing mapped definitions', aliases.keys() - seen_aliases)
    assert seen_decisions == decisions.keys(), ('Missing ledger definitions', decisions.keys() - seen_decisions)
    for name, expected in input_hashes.items():
        assert digest(getattr(args, name)) == expected, ('Inventory input changed during scan', name)
    result = {
        'Format': 1, 'Kind': 'PhysicalApplicationInventory', 'Root': str(root),
        'Scope': str(args.scope), 'ScopeSha256': digest(args.scope),
        'Cli': str(args.cli), 'CliSha256': digest(args.cli),
        'Map': str(args.map), 'MapSha256': digest(args.map),
        'Ledger': str(args.ledger), 'LedgerSha256': digest(args.ledger),
        'ElapsedSeconds': round(time.monotonic() - started, 2),
        'ReusedInventory': str(args.reuse_inventory) if args.reuse_inventory else None,
        'NativeCalls': 0 if cached else len(physical) * 3,
        'LargestNativeReportBytes': max(Path(r['Path']).stat().st_size for r in reports),
        'Counts': {kind: dict(counts) for kind, counts in all_counts.items()},
        'Modules': modules, 'Reports': reports, 'ExcludedLedgerRows': excluded_decisions,
        'RemainingNativeCandidates': len(remaining),
        'UnappliedLedgerAliases': unapplied,
        'Limits': [scope['Limit'], 'Native lexical flags select work; unflagged or unreviewed names are not proven meaningful.',
                   'No source export, build, applied-map audit or runtime compatibility is established by this inventory.',
                   'Parameter/local totals include unaliased original and compiler roles; missing aliases do not prove obfuscation.',
                   'UnappliedLedgerAlias records historical proposals absent from the current map; they are not applied names or new unreviewed definitions.'],
    }
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (args.output / 'remaining-candidates.json').write_text(json.dumps(remaining, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'Counts': result['Counts'], 'Remaining': len(remaining), 'Seconds': result['ElapsedSeconds']}))


def all_counts_kinds():
    return ('Types', 'Fields', 'Methods')


if __name__ == '__main__':
    main()
