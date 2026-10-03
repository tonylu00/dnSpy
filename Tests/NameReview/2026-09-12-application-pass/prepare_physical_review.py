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
