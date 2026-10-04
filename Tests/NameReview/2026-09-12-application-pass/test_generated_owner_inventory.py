"""Physical-twin and stale-cache guards; requires a native inspector and its synthetic fixture directory."""
import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch
import inventory_generated_owners as inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cli', 'fixture', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    originals = [args.fixture / 'Twin.dll', args.fixture / 'compatibility' / 'Twin.dll']
    original_hashes = [inventory.digest(path) for path in originals]
    scope_modules, catalog, candidates = [], [], []
    for i, (path, report_name) in enumerate(zip(originals, ('report.json', 'twin.json'))):
        report = inventory.read(args.fixture / report_name)
        module = path.relative_to(args.fixture).as_posix()
        binding = {'Path': module, 'Input': str(path.resolve()), 'Mvid': report['Mvid'], 'Sha256': report['Sha256'], 'GraphId': str(i)}
        scope_modules.append(binding)
        catalog.append({**binding, 'Counts': {kind: {'Definitions': report['Scope'][kind]} for kind in ('Types', 'Fields', 'Methods')}})
        target = next(m for m in report['Methods'] if m['Definition']['Signature'] == 'System.Void Ordinary/Opaque::x()')
        candidates.append({'Module': module, 'Identity': report['Identity'], 'Mvid': report['Mvid'], 'Sha256': report['Sha256'],
                           'Token': target['Definition']['Token'], 'Signature': target['Definition']['Signature'], 'Kind': 'Methods',
                           'OriginalName': 'x', 'Reason': 'fixture placeholder', 'NeedsReadableName': True})
    inventory.write(args.output / 'scope.json', {'Kind': 'PhysicalApplicationScope', 'Root': str(args.fixture.resolve()), 'Modules': scope_modules})
    (args.output / 'map.xml').write_text('<FixtureMap/>', encoding='utf-8')
    inventory.write(args.output / 'ledger.json', {})
    summary = {'Kind': 'PhysicalApplicationInventory', 'Root': str(args.fixture.resolve()), 'Modules': catalog, 'RemainingNativeCandidates': 2,
               **{name.title() + 'Sha256': inventory.digest(args.output / file) for name, file in
                  (('scope', 'scope.json'), ('map', 'map.xml'), ('ledger', 'ledger.json'))}}
    inventory.write(args.output / 'summary.json', summary)
    inventory.write(args.output / 'remaining-candidates.json', candidates)
    checks = 0

    def run(name, reuse=None, inventory_path=None, expect_error=False):
        nonlocal checks
        destination = args.output / name
        command = ['inventory_generated_owners.py', '--scope', str(args.output / 'scope.json'), '--cli', str(args.cli),
                   '--inventory', str(inventory_path or args.output / 'summary.json'), '--map', str(args.output / 'map.xml'),
                   '--ledger', str(args.output / 'ledger.json'), '--output', str(destination)]
        if reuse:
            command += ['--reuse-inventory', str(reuse)]
        try:
            with patch.object(sys, 'argv', command), contextlib.redirect_stdout(io.StringIO()):
                inventory.main()
        except (ValueError, FileExistsError):
            if not expect_error:
                raise
            checks += 1
            return
        if expect_error:
            raise AssertionError('Guard accepted: ' + name)
        checks += 1
        return inventory.read(destination / 'summary.json')

    cold = run('cold')
    warm = run('warm', args.output / 'cold' / 'summary.json')
    assert cold['NativeCalls'] == 2 and warm['NativeCalls'] == 0 and warm['ReusedNativeReports'] == 2
    assert cold['WorklistSha256'] == warm['WorklistSha256']
    joined = [json.loads(line) for line in Path(warm['Worklist']).read_text(encoding='utf-8').splitlines()]
    assert len({row['Module'] for row in joined}) == 2 and len({row['Token'] for row in joined}) == 1
    assert all(row['Category'] == 'DelegateOwners' and row['DistinctOwnersByEvidence']['DelegateOwners'] == 1 for row in joined)
    checks += 3
    run('warm', args.output / 'cold' / 'summary.json', expect_error=True)
    for name, edit in (
        ('wrong-tool', lambda data: data['Inputs']['cli'].update(Sha256='0' * 64)),
        ('wrong-mvid', lambda data: data['Modules'][0].update(Mvid='wrong')),
        ('wrong-scope', lambda data: data['Modules'].pop()),
    ):
        altered = copy.deepcopy(cold)
        edit(altered)
        path = args.output / (name + '.json')
        inventory.write(path, altered)
        run(name, path, expect_error=True)
        assert not (args.output / name).exists()
    altered = copy.deepcopy(cold)
    corrupt = args.output / 'corrupt-native.json'
    corrupt.write_bytes(Path(cold['Modules'][0]['NativeReport']).read_bytes() + b'\n')
    altered['Modules'][0]['NativeReport'] = str(corrupt)
    inventory.write(args.output / 'wrong-report.json', altered)
    run('wrong-report', args.output / 'wrong-report.json', expect_error=True)
    for name, edit in (
        ('wrong-signature', lambda rows: rows[0].update(Signature='Wrong()')),
        ('foreign-path', lambda rows: rows[0].update(Module='../Twin.dll')),
        ('duplicate-token', lambda rows: rows[1].update(Module=rows[0]['Module'])),
    ):
        directory = args.output / (name + '-inputs')
        directory.mkdir()
        altered_candidates = copy.deepcopy(candidates)
        edit(altered_candidates)
        inventory.write(directory / 'remaining-candidates.json', altered_candidates)
        inventory.write(directory / 'summary.json', summary)
        run(name, args.output / 'cold' / 'summary.json', directory / 'summary.json', expect_error=True)
        assert not (args.output / name / 'summary.json').exists()
    assert [inventory.digest(path) for path in originals] == original_hashes
    checks += 1
    print(f'PASS: {checks} cold/warm, physical-twin, stale tool/module/report, path, duplicate, signature and immutability checks.')


if __name__ == '__main__':
    main()
