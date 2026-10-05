"""Reconcile scope evidence when a review resolves its last unknown position.

The historical helpers remain immutable because accepted proofs pin their hashes.
This extension affects ledger records only, never application source or binaries.
"""
import copy
import pathlib
import runpy
import review_ledger

original_merge = review_ledger.merge_scopes


def merge_scopes(previous, reviewed, mapped_name, checked_scopes=None, replacements=None):
    if 'UnresolvedScopeEvidence' in reviewed or not previous.get('UnresolvedScopeEvidence'):
        return original_merge(previous, reviewed, mapped_name, checked_scopes, replacements)
    review = copy.deepcopy(reviewed)
    review['UnresolvedScopeEvidence'] = {}
    result = original_merge(previous, review, mapped_name, checked_scopes, replacements)
    # Retiring an old unknown requires a freshly reviewed alias and native identity,
    # even when the historical scope inventory already contained that position.
    for label, inventory_label, position, preimage, checked_key in (
            ('Parameters', 'ParameterNames', 'Sequence', 'OriginalName', 'ExpectedName'),
            ('Locals', 'LocalNames', 'Index', 'ExpectedType', 'ExpectedType')):
        inventory = {p[position]: p for p in reviewed.get(inventory_label, [])}
        if len(inventory) != len(reviewed.get(inventory_label, [])):
            raise ValueError('Duplicate reviewed scope position')
        retained = {p[position] for p in result['UnresolvedScopeEvidence'].get(label, [])}
        for unknown in previous['UnresolvedScopeEvidence'].get(label, []):
            slot = unknown[position]
            if slot in retained:
                continue
            incoming = inventory.get(slot, {})
            checked = (checked_scopes or {}).get((inventory_label, slot), {})
            if (not incoming.get('NewName') or not reviewed.get('Reason') or
                    unknown.get(preimage) != incoming.get(preimage) or
                    checked.get('NewName') != incoming['NewName'] or
                    checked.get(checked_key) != incoming.get(preimage)):
                raise ValueError('Resolved scope evidence requires a reviewed native-checked alias')
    return result


def reconcile_scope_merge(previous, reviewed, recorded, mapped_name,
                          checked_scopes=None, replacements=None):
    """Repair an already recorded merge only if it exactly matches the old result."""
    expected = original_merge(previous, reviewed, mapped_name, checked_scopes, replacements)
    if expected != recorded:
        raise ValueError('Recorded scope merge differs from its exact historical replay')
    return merge_scopes(previous, reviewed, mapped_name, checked_scopes, replacements)


if __name__ == '__main__':
    from checkpoint_scoped_contract_resolution import resolve_unresolved
    review_ledger.merge_scopes = merge_scopes
    review_ledger.resolve_unresolved = resolve_unresolved
    runpy.run_path(str(pathlib.Path(__file__).with_name('checkpoint_naming_block.py')), run_name='__main__')
