"""Preserve native parameter spellings during alias corrections in the ledger.

An unchanged parameter has no map entry. Require its exact physical native body
report before supplementing the historical checkpoint's scope proof. This only
updates review records; it never patches application source or binaries.
"""
import argparse
import copy
import hashlib
import json
import pathlib
import runpy
import sys
import review_ledger


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def load_reports(paths):
    reports = {}
    for path in paths:
        report = read(path)
        source = pathlib.Path(report['Input']).resolve()
        if source in reports:
            raise ValueError('Duplicate physical native parameter report')
        digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        if digest != report['Sha256']:
            raise ValueError('Native parameter input hash changed')
        report = copy.deepcopy(report)
        report['Evidence'] = dict(Path=str(pathlib.Path(path).resolve()),
            Sha256=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest().upper())
        reports[source] = report
    return reports


def supplement(previous, reviewed, checked_scopes, target_root, reports):
    review_ledger.require_identity(previous, reviewed)
    checked = copy.deepcopy(checked_scopes or {})
    retained = []
    root = pathlib.Path(target_root).resolve()
    source = (root / reviewed['Module']).resolve()
    if not source.is_relative_to(root):
        raise ValueError('Native parameter module escaped its physical root')
    incoming = reviewed.get('ParameterNames', [])
    if len({x['Sequence'] for x in incoming}) != len(incoming):
        raise ValueError('Duplicate reviewed parameter')
    incoming = {x['Sequence']: x for x in incoming}
    for old in previous.get('ParameterNames', []):
        key = ('ParameterNames', old['Sequence'])
        if not old.get('NewName') or key in checked:
            continue
        fresh = incoming.get(old['Sequence'], {})
        if (not old.get('HasMetadata') or not fresh.get('HasMetadata') or
                old['NewName'] != old.get('OriginalName') or
                any(fresh.get(k) != old.get(k) for k in
                    ('Sequence', 'OriginalName', 'NewName'))):
            raise ValueError('Missing mapped parameter is not an unchanged native name')
        report = reports.get(source)
        if not report or any(report.get(k) != reviewed.get(k)
                             for k in ('Identity', 'Mvid', 'Sha256')):
            raise ValueError('Native parameter physical identity mismatch')
        methods = [x for x in report['Methods'] if x['Token'] == reviewed['Token']]
        if len(methods) != 1 or methods[0]['Signature'] != reviewed['Signature']:
            raise ValueError('Native parameter method identity mismatch')
        parameters = [x for x in methods[0]['Parameters'] if x['Sequence'] is not None]
        if len({x['Sequence'] for x in parameters}) != len(parameters):
            raise ValueError('Duplicate native parameter sequence')
        native = next((x for x in parameters if x['Sequence'] == old['Sequence']), {})
        if native.get('Name') != old['OriginalName']:
            raise ValueError('Native parameter spelling mismatch')
        checked[key] = dict(ExpectedName=old['OriginalName'], NewName=old['NewName'])
        retained.append(dict(Sequence=old['Sequence'], Name=old['NewName'],
            Evidence=report['Evidence']))
    return checked, retained


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--native-parameter-evidence', action='append', required=True)
    options, rest = parser.parse_known_args()
    review_path = rest[rest.index('--review') + 1]
    target_root = read(review_path)['TargetRoot']
    reports = load_reports(options.native_parameter_evidence)
    original = review_ledger.replace_method_alias

    def replace(previous, reviewed, mapped_name, checked_change, checked_scopes,
                replacements=None, checked_family=None):
        scopes, retained = supplement(previous, reviewed, checked_scopes, target_root, reports)
        result = original(previous, reviewed, mapped_name, checked_change, scopes,
                          replacements, checked_family)
        if retained:
            result.setdefault('PreservedOriginalParameters', []).extend(retained)
        return result

    review_ledger.replace_method_alias = replace
    sys.argv = [sys.argv[0]] + rest
    runpy.run_path(str(pathlib.Path(__file__).with_name('checkpoint_scope_evidence_completion.py')),
                  run_name='__main__')


if __name__ == '__main__':
    main()
