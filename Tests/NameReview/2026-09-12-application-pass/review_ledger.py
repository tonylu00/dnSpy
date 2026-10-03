"""Merge explicitly reviewed scope additions without losing earlier decisions."""
import copy


def validate_review_only(review, changes, base_sha, checked_sha):
    """A preservation/unresolved review must leave the checked map byte-identical."""
    if changes or not base_sha or base_sha != checked_sha:
        raise ValueError('Review-only checkpoint cannot change the map')
    rows = [row for kind in ('Types', 'Fields', 'Methods') for row in review[kind]]
    if not rows:
        raise ValueError('Review-only checkpoint requires reviewed decisions')
    for row in rows:
        if row.get('ReviewDisposition') not in ('preserve', 'unresolved') or not row.get('Reason'):
            raise ValueError('Review-only checkpoint requires explicit preservation/unresolved evidence')
        if row.get('NewName') or any(entry.get('NewName') for label in ('ParameterNames', 'LocalNames') for entry in row.get(label, [])):
            raise ValueError('Review-only checkpoint cannot carry aliases')


def require_identity(previous, reviewed):
    for key in ('Module', 'Token', 'Identity', 'Mvid', 'Sha256', 'Type', 'Signature', 'OriginalName'):
        if previous.get(key) != reviewed.get(key):
            raise ValueError('Ledger identity differs: ' + key)


def refresh_evidence(previous, reviewed):
    """Replace reviewed rationale only, with explicit preimages and no decision change."""
    require_identity(previous, reviewed)
    preimage = reviewed.get('PreviousEvidence')
    if preimage != {key: previous.get(key, '') for key in ('Reason', 'UnresolvedReason')}:
        raise ValueError('Evidence refresh requires the exact previous rationale')
    for key in ('NewName', 'Unresolved', 'NeedsReadableName', 'ParameterNames', 'LocalNames', 'ReviewDisposition'):
        if previous.get(key) != reviewed.get(key):
            raise ValueError('Evidence refresh cannot change a naming decision: ' + key)
    if not reviewed.get('Reason') or (reviewed.get('Unresolved') and not reviewed.get('UnresolvedReason')):
        raise ValueError('Evidence refresh requires complete rationale')
    if all(previous.get(key, '') == reviewed.get(key, '') for key in ('Reason', 'UnresolvedReason')):
        raise ValueError('Evidence refresh has no corrected rationale')
    result = copy.deepcopy(previous)
    for key in ('Reason', 'UnresolvedReason'):
        result[key] = reviewed.get(key, '')
    return result


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


def replace_method_alias(previous, reviewed, mapped_name, checked_change, checked_scopes, replacements=None):
    """Correct a method alias while retaining and checking earlier scope decisions."""
    require_identity(previous, reviewed)
    if not checked_change or any(checked_change.get(key) != value for key, value in
                                 (('Kind', 'Method'), ('Module', reviewed['Module']), ('Token', reviewed['Token']))):
        raise ValueError('Method replacement requires its exact native definition change')
    # The generic guard checks current alias, physical identity and exact native
    # before/requested/applied values. Its fresh-row result must not replace the
    # method's historical scope inventory or annotations.
    replace_alias(previous, reviewed, mapped_name, checked_change)
    needs_merge = False
    for label, position in (('ParameterNames', 'Sequence'), ('LocalNames', 'Index')):
        for record in (previous, reviewed):
            positions = [entry[position] for entry in record.get(label, [])]
            if len(positions) != len(set(positions)):
                raise ValueError('Duplicate method scope position: ' + label)
        old = {entry[position]: entry for entry in previous.get(label, [])}
        needs_merge |= any(entry.get('NewName') and entry['NewName'] != old.get(entry[position], {}).get('NewName')
                           for entry in reviewed.get(label, []))
    scope_review = copy.deepcopy(reviewed)
    scope_review['NewName'] = ''
    result = (merge_scopes(previous, scope_review, mapped_name, checked_scopes, replacements)
              if needs_merge else copy.deepcopy(previous))
    for label, position, expected_key, inventory_key in (
            ('ParameterNames', 'Sequence', 'ExpectedName', 'OriginalName'),
            ('LocalNames', 'Index', 'ExpectedType', 'ExpectedType')):
        for entry in result.get(label, []):
            if not entry.get('NewName'):
                continue
            checked = checked_scopes.get((label, entry[position]))
            if not checked or checked.get('NewName') != entry['NewName'] or checked.get(expected_key) != entry.get(inventory_key):
                raise ValueError('Method correction lost a checked scope decision: ' + label)
    result['NewName'] = reviewed['NewName']
    result['Reason'] = (result.get('Reason') or '') + '\nReviewed method correction: ' + reviewed['Reason']
    return result


def remove_method_alias(previous, reviewed, mapped_name, checked_change, checked_name):
    """Record a native-checked withdrawal without replaying its operational marker."""
    if previous is not None:
        require_identity(previous, reviewed)
        if previous.get('Unresolved') or previous.get('NewName') != mapped_name:
            raise ValueError('Alias withdrawal requires the current ledger/map decision')
    if not mapped_name or checked_name or not reviewed.get('RemoveExistingAlias') or reviewed.get('ExpectedAlias') != mapped_name:
        raise ValueError('Alias withdrawal requires exact current and final map names')
    if not reviewed.get('Unresolved') or reviewed.get('NewName') or not reviewed.get('Reason') or not reviewed.get('UnresolvedReason'):
        raise ValueError('Alias withdrawal requires complete unresolved evidence')
    if not checked_change or any(checked_change.get(key) != value for key, value in (
            ('Action', 'RemoveAlias'), ('Kind', 'Method'), ('Module', reviewed['Module']), ('Token', reviewed['Token']),
            ('Before', mapped_name), ('Requested', ''), ('Applied', ''))):
        raise ValueError('Alias withdrawal requires the exact native removal report')
    for record in (previous, reviewed):
        if record and any(scope.get('NewName') for label in ('ParameterNames', 'LocalNames') for scope in record.get(label, [])):
            raise ValueError('Alias withdrawal cannot discard accepted scope names')
    result = copy.deepcopy(previous if previous is not None else reviewed)
    for key in ('RemoveExistingAlias', 'ExpectedAlias'):
        result.pop(key, None)
    result.update(NewName='', Unresolved=True, NeedsReadableName=True, ReviewDisposition='unresolved',
                  Reason=reviewed['Reason'], UnresolvedReason=reviewed['UnresolvedReason'])
    result.setdefault('AliasWithdrawals', []).append(dict(Alias=mapped_name, PreviousReason=(previous or {}).get('Reason', ''),
                                                       Evidence=reviewed['Reason']))
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
