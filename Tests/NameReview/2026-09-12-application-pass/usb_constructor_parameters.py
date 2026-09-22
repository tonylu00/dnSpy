"""Resume the ten reviewed USB constructors after scoped-name support is built.

Usage: python usb_constructor_parameters.py PASS_DIRECTORY NEW_OUTPUT_STEM
Consumes the wave168 evidence and a fresh NameCandidates method inventory.
Writes review/map input only; no ETS source or binaries are modified.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys


def stage(root, stem):
    def read(name):
        return json.loads((root / name).read_text(encoding='utf-8'))
    evidence = read('usb63-wave168.evidence.json')
    cumulative = read('usb63-wave168.cumulative.json')
    inventory = read('resume-falcon63-scoped-methods.json')
    by_token = {r['Token']: r for r in inventory['Methods']}
    delta = {k: copy.deepcopy(cumulative[k]) for k in ['Format', 'Kind', 'TargetRoot', 'ContractReferenceSha256']}
    delta.update(Methods=[], Fields=[], Types=[])
    binary = Path(cumulative['TargetRoot']) / 'Knx.Falcon.dll'
    assert hashlib.sha256(binary.read_bytes()).hexdigest().upper() == evidence['ModuleSha256']
    for pending in evidence['PendingUnsupported']:
        row = copy.deepcopy(by_token[pending['Token']])
        for key in ['Module', 'Identity', 'Mvid', 'Sha256', 'Signature', 'OriginalName']:
            assert row[key] == pending[key], (key, pending['Token'])
        assert row['OriginalName'] == '.ctor' and not pending['NewName']
        assert 'ScopedMappingBlocker' in row and row['ScopedMappingBlocker'] is None
        row['ParameterNames'] = copy.deepcopy(pending['ParameterNames'])
        row['LocalNames'] = []
        row['Reason'] = pending['Reason'].replace(
            'Parameter roles reviewed; constructor-only parameter application is still unsupported.',
            'Parameter-only mapping supported; constructor identity remains unchanged.')
        delta['Methods'].append(row)
    assert len(delta['Methods']) == 10
    decisions = {(r['Module'], r['Token']): r for r in delta['Methods']}
    cumulative['Methods'] = [r for r in cumulative['Methods'] if (r['Module'], r['Token']) not in decisions] + list(decisions.values())
    destinations = {'.review.json': delta, '.cumulative.json': cumulative}
    assert not any(Path(str(stem) + suffix).exists() for suffix in destinations), 'Choose a new output stem'
    for suffix, data in destinations.items():
        Path(str(stem) + suffix).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print('Staged reviewed parameter roles for ten constructors; no constructor names changed.')


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
