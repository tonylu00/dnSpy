"""Prepare reviewed decisions from exact native physical inventories.

Inventory roots may be application subdirectories. Normalize by the actual path,
never a filename or assembly-name fallback. Only review JSON is written.
"""
import argparse
import copy
import hashlib
import json
import pathlib


def prepare(spec):
    root = pathlib.Path(spec['TargetRoot']).resolve()
    requested = {(row['Kind'], row['Module'].replace('\\', '/'), row['Token'].upper())
                 for row in spec['Rows']}
    sources = {pathlib.Path(source).resolve() for source in spec['Inventories']}
    choices = {(row['Kind'], row['Module'].replace('\\', '/'), row['Token'].upper()):
               pathlib.Path(row['Inventory']).resolve()
               for row in spec['Rows'] if row.get('Inventory')}
    if not set(choices.values()).issubset(sources):
        raise ValueError('Selected inventory is not in the bound inventory list')
    scope_choices = {(row['Kind'], row['Module'].replace('\\', '/'), row['Token'].upper()):
                     pathlib.Path(row['ScopeInventory']).resolve()
                     for row in spec['Rows'] if row.get('ScopeInventory')}
    if not set(scope_choices.values()).issubset(sources) or any(key[0] != 'Methods' for key in scope_choices):
        raise ValueError('Scope inventory requires a method and a bound input')
    scope_rows = {}
    index = {}
    for source in spec['Inventories']:
        inventory = json.loads(pathlib.Path(source).read_text(encoding='utf-8-sig'))
        native_root = pathlib.Path(inventory['TargetRoot']).resolve()
        if not native_root.is_relative_to(root):
            raise ValueError('Native inventory root leaves the application tree')
        for kind in ('Types', 'Fields', 'Methods'):
            for original in inventory.get(kind, []):
                native_module = pathlib.Path(original['Module'].replace('\\', '/'))
                if native_module.is_absolute(): raise ValueError('Inventory module must be relative')
                physical = (native_root / native_module).resolve()
                if not physical.is_relative_to(native_root): raise ValueError('Inventory module leaves its native root')
                relative = physical.relative_to(root).as_posix()
                key = (kind, relative, original['Token'].upper())
                # Large method inventories include every local in every body.
                # Retain only explicitly requested definitions; input roots and
                # all physical paths still pass the same escape checks.
                if key not in requested:
                    continue
                if key in scope_choices and pathlib.Path(source).resolve() == scope_choices[key]:
                    scoped = copy.deepcopy(original)
                    scoped['Module'] = relative
                    if key in scope_rows and scope_rows[key] != scoped:
                        raise ValueError('Conflicting native scope inventories')
                    scope_rows[key] = scoped
                if key in choices and pathlib.Path(source).resolve() != choices[key]:
                    continue
                row = copy.deepcopy(original)
                row['Module'] = relative
                if key in index and index[key] != row:
                    raise ValueError('Conflicting native inventories for ' + str(key))
                index[key] = row
    result = dict(Format=1, Kind='SymbolReview', TargetRoot=str(root),
                  ContractReferenceSha256=spec['ContractReferenceSha256'], Types=[], Fields=[], Methods=[], Skips=[])
    seen = set()
    hashes = {}
    for decision in spec['Rows']:
        key = (decision['Kind'], decision['Module'].replace('\\', '/'), decision['Token'].upper())
        if key in seen: raise ValueError('Repeated decision: ' + str(key))
        seen.add(key)
        row = copy.deepcopy(index[key])
        if key in scope_choices:
            scoped = scope_rows[key]
            for label in ('Module', 'Identity', 'Mvid', 'Sha256', 'Token', 'Type', 'Signature', 'OriginalName'):
                if scoped.get(label) != row.get(label):
                    raise ValueError('Native scope identity differs: ' + label)
            for label in ('ParameterNames', 'LocalNames'):
                row[label] = copy.deepcopy(scoped[label])
        physical = root / key[1]
        if key[1] not in hashes:
            hashes[key[1]] = hashlib.sha256(physical.read_bytes()).hexdigest().upper()
        if hashes[key[1]] != row['Sha256'].upper(): raise ValueError('Stale physical inventory: ' + key[1])
        if not decision.get('Reason'): raise ValueError('Behavioral evidence is required')
        row['Reason'] = decision['Reason']
        disposition = decision.get('Disposition', 'rename')
        row['ReviewDisposition'] = disposition
        if disposition == 'preserve':
            if decision.get('NewName') or decision.get('ParameterNames') or decision.get('LocalNames'):
                raise ValueError('Preservation cannot carry aliases')
            row.update(NewName='', NeedsReadableName=False, Unresolved=False, UnresolvedReason='')
        elif disposition == 'unresolved':
            if decision.get('NewName') or decision.get('ParameterNames') or decision.get('LocalNames'):
                raise ValueError('Unresolved decisions cannot carry aliases')
            row.update(NewName='', Unresolved=True, UnresolvedReason=decision['Reason'])
        elif disposition == 'rename':
            row['NewName'] = decision.get('NewName', '')
            row['Unresolved'] = False
            row['UnresolvedReason'] = ''
            for label, position in (('ParameterNames', 'Sequence'), ('LocalNames', 'Index')):
                for number, name in decision.get(label, {}).items():
                    matches = [entry for entry in row[label] if entry[position] == int(number)]
                    if len(matches) != 1: raise ValueError('Missing physical scope position: ' + str(key))
                    if label == 'ParameterNames' and not matches[0]['HasMetadata']:
                        raise ValueError('Parameter has no metadata row')
                    matches[0]['NewName'] = name
            if not row['NewName'] and not any(entry.get('NewName') for label in ('ParameterNames', 'LocalNames') for entry in row.get(label, [])):
                raise ValueError('Rename decision requires a supported name')
        else:
            raise ValueError('Unknown disposition: ' + disposition)
        if decision.get('RemoveExistingAlias'):
            if key[0] != 'Methods' or disposition != 'unresolved' or not decision.get('ExpectedAlias'):
                raise ValueError('Alias withdrawal requires an unresolved method and its exact previous alias')
            row['RemoveExistingAlias'] = True
            row['ExpectedAlias'] = decision['ExpectedAlias']
        if decision.get('ResolveExistingUnresolved'):
            if disposition != 'rename' or not row['NewName'] or not decision.get('PreviousUnresolvedEvidence'):
                raise ValueError('Resolution requires a named definition and previous unresolved evidence')
            row['ResolveExistingUnresolved'] = True
            row['PreviousUnresolvedEvidence'] = decision['PreviousUnresolvedEvidence']
        result[key[0]].append(row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = prepare(json.loads(pathlib.Path(args.spec).read_text(encoding='utf-8-sig')))
    with pathlib.Path(args.output).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print('Prepared physical decisions:', {kind: len(result[kind]) for kind in ('Types', 'Fields', 'Methods')})


if __name__ == '__main__': main()
