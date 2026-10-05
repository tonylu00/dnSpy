"""Checkpoint complete native family resolutions while preserving scoped aliases.

The historical checkpoint helpers are hash-pinned by accepted evidence. This
entry point extends their ledger-only resolution path without changing them or
touching application source/binaries. Unscoped resolutions retain the old path.
"""
import copy
import pathlib
import runpy
import review_ledger


original_resolution = review_ledger.resolve_unresolved


def resolve_unresolved(previous, reviewed, mapped_name, checked_change, checked_name,
                       checked_scopes=None, checked_family=None):
    has_scopes = any(x.get('NewName') for label in ('ParameterNames', 'LocalNames')
                     for x in previous.get(label, []))
    if not has_scopes:
        return original_resolution(previous, reviewed, mapped_name, checked_change,
                                   checked_name, checked_scopes, checked_family)
    review_ledger.require_identity(previous, reviewed)
    if (not previous.get('Unresolved') or not previous.get('DefinitionOnlyUnresolved') or
            previous.get('NewName') or mapped_name or not previous.get('ContractFamily') or
            reviewed.get('ContractFamily') != previous['ContractFamily'] or
            int(reviewed['Token'], 16) >> 24 != 6):
        raise ValueError('Scoped contract resolution requires an unnamed, definition-only unresolved family member')
    if (not reviewed.get('ResolveExistingUnresolved') or reviewed.get('Unresolved') or
            reviewed.get('DefinitionOnlyUnresolved') or reviewed.get('UnresolvedReason') or
            reviewed.get('MappingBlocker') or reviewed.get('ScopedMappingBlocker') or
            not reviewed.get('NewName') or not reviewed.get('Reason') or
            reviewed.get('PreviousUnresolvedEvidence') !=
            {k: previous.get(k, '') for k in ('Reason', 'UnresolvedReason')}):
        raise ValueError('Scoped contract resolution requires exact prior rationale and an unblocked review')
    review_ledger.validate_contract_resolution(reviewed, checked_family)
    if any(x.get('MappingBlocker') or x.get('ScopedMappingBlocker') or x.get('Unresolved')
           for x in checked_family['ReviewedMembers']):
        raise ValueError('Scoped contract resolution requires an unblocked complete family')
    if (not checked_change or 'Before' not in checked_change or
            checked_change['Before'] not in (None, '') or
            any(checked_change.get(k) != v for k, v in (
                ('Kind', 'ContractMethod'), ('Module', reviewed['Module']), ('Token', reviewed['Token']),
                ('Requested', reviewed['NewName']), ('Applied', reviewed['NewName']), ('Action', None))) or
            checked_name != reviewed['NewName']):
        raise ValueError('Scoped contract resolution requires the exact native addition and checked final alias')
    # This operation changes only the definition. Require the complete original
    # scope inventory and aliases verbatim, including unresolved local positions.
    for label, position, preimage, checked_key in (
            ('ParameterNames', 'Sequence', 'OriginalName', 'ExpectedName'),
            ('LocalNames', 'Index', 'ExpectedType', 'ExpectedType')):
        for row in (previous, reviewed):
            positions = [x[position] for x in row.get(label, [])]
            if len(positions) != len(set(positions)):
                raise ValueError('Duplicate scoped contract position')
        if previous.get(label, []) != reviewed.get(label, []):
            raise ValueError('Scoped contract resolution cannot add, remove or change scopes')
        for scope in previous.get(label, []):
            if not scope.get('NewName'):
                continue
            checked = (checked_scopes or {}).get((label, scope[position]), {})
            if (checked.get('NewName') != scope['NewName'] or
                    checked.get(checked_key) != scope.get(preimage)):
                raise ValueError('Scoped contract resolution lost a checked scope identity')
    if reviewed.get('UnresolvedScopeEvidence', {}) != previous.get('UnresolvedScopeEvidence', {}):
        raise ValueError('Scoped contract resolution cannot discard missing scope evidence')
    result = copy.deepcopy(previous)
    result.update(NewName=reviewed['NewName'], Unresolved=False, DefinitionOnlyUnresolved=False,
                  UnresolvedReason='', MappingBlocker=None, ScopedMappingBlocker=None,
                  NeedsReadableName=reviewed['NeedsReadableName'], ReviewDisposition='rename', Reason=reviewed['Reason'])
    result.setdefault('UnresolvedResolutions', []).append(dict(
        Alias=reviewed['NewName'], PreviousReason=previous['Reason'],
        PreviousUnresolvedReason=previous['UnresolvedReason'], Evidence=reviewed['Reason']))
    result.setdefault('ContractFamilyReviews', []).append(dict(
        PreviousContractFamily=previous['ContractFamily'], PreviousMappingBlocker=previous.get('MappingBlocker'),
        ContractFamily=reviewed['ContractFamily'], Evidence=reviewed['Reason']))
    for key in ('ResolveExistingUnresolved', 'PreviousUnresolvedEvidence'):
        result.pop(key, None)
    return result


if __name__ == '__main__':
    review_ledger.resolve_unresolved = resolve_unresolved
    runpy.run_path(str(pathlib.Path(__file__).with_name('checkpoint_naming_block.py')), run_name='__main__')
