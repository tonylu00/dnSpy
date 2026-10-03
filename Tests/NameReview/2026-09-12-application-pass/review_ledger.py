"""Merge explicitly reviewed scope additions without losing earlier decisions."""
import copy


def require_identity(previous, reviewed):
    for key in ('Module', 'Token', 'Identity', 'Mvid', 'Sha256', 'Type', 'Signature', 'OriginalName'):
        if previous.get(key) != reviewed.get(key):
            raise ValueError('Ledger identity differs: ' + key)


def replace_alias(previous, reviewed, mapped_name, checked_change):
    require_identity(previous, reviewed)
    if previous.get('Unresolved') or reviewed.get('Unresolved'):
        raise ValueError('Unresolved decisions require separate review')
    if previous.get('NewName') != mapped_name or not reviewed.get('NewName'):
        raise ValueError('Alias replacement requires the current ledger/map decision')
    if not checked_change or checked_change['Before'] != mapped_name or checked_change['Requested'] != reviewed['NewName'] or checked_change['Applied'] != reviewed['NewName']:
        raise ValueError('Alias replacement requires the exact native-checked change')
    result = copy.deepcopy(reviewed)
    result['Reason'] = 'Reviewed correction: ' + reviewed['Reason']
    return result


def merge_scopes(previous, reviewed, mapped_name, checked_scopes=None, replacements=None):
    require_identity(previous, reviewed)
    if reviewed.get('Unresolved') or previous.get('Unresolved'):
        raise ValueError('Unresolved decisions require separate review')
    requested_name = reviewed.get('NewName', '')
    if requested_name and requested_name != mapped_name:
        raise ValueError('Scope merge cannot rename the mapped definition')
    result = copy.deepcopy(previous)
    result['NewName'] = mapped_name or previous.get('NewName', '')
    added = 0
    for label, position in (('ParameterNames', 'Sequence'), ('LocalNames', 'Index')):
        existing = {p[position]: p for p in result.get(label, [])}
        for incoming in reviewed.get(label, []):
            if not incoming.get('NewName'):
                continue
            slot = incoming[position]
            if slot not in existing:
                # Older ledgers predate local inventories. The physical hash/MVID
                # still binds the body; require a native-checked map entry before
                # importing a newly inventoried position.
                checked = (checked_scopes or {}).get((label, slot))
                expected_key = 'ExpectedName' if label == 'ParameterNames' else 'ExpectedType'
                inventory_key = 'OriginalName' if label == 'ParameterNames' else 'ExpectedType'
                if not checked or checked.get('NewName') != incoming['NewName'] or checked.get(expected_key) != incoming.get(inventory_key):
                    raise ValueError('New scope position requires native-checked identity: ' + label + ':' + str(slot))
                result.setdefault(label, []).append(copy.deepcopy(incoming))
                existing[slot] = result[label][-1]
                added += 1
                continue
            old = existing[slot]
            for key in ('OriginalName', 'ExpectedType', 'Type', 'HasMetadata'):
                if old.get(key) != incoming.get(key):
                    raise ValueError('Scope identity differs: ' + key)
            if old.get('NewName') and old['NewName'] != incoming['NewName']:
                change = (replacements or {}).get((label, slot))
                if not change or change['Before'] != old['NewName'] or change['Requested'] != incoming['NewName'] or change['Applied'] != incoming['NewName']:
                    raise ValueError('Scope replacement requires the exact native-checked change')
                old['NewName'] = incoming['NewName']
                added += 1
                continue
            if not old.get('NewName'):
                old['NewName'] = incoming['NewName']
                added += 1
    if not added:
        raise ValueError('Existing row has no new reviewed scope additions')
    result['Reason'] = (previous.get('Reason') or '') + '\nScope review: ' + reviewed['Reason']
    return result
