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
    historical = previous.get('NewName') != mapped_name
    if historical and (not mapped_name or reviewed.get('PreviousLedgerAlias') != previous.get('NewName') or
                       reviewed.get('ExpectedMappedAlias') != mapped_name):
        raise ValueError('Historical proposal correction requires exact ledger and checked-map preimages')
    if not historical and any(k in reviewed for k in ('PreviousLedgerAlias', 'ExpectedMappedAlias')):
        raise ValueError('Historical proposal correction annotations are stale')
    if not reviewed.get('NewName'):
        raise ValueError('Alias replacement requires the current ledger/map decision')
    if not checked_change or checked_change['Before'] != mapped_name or checked_change['Requested'] != reviewed['NewName'] or checked_change['Applied'] != reviewed['NewName']:
        raise ValueError('Alias replacement requires the exact native-checked change')
    result = copy.deepcopy(reviewed)
    for key in ('PreviousLedgerAlias', 'ExpectedMappedAlias'):
        result.pop(key, None)
    if historical:
        result.setdefault('LedgerAliasCorrections', []).append(dict(PreviousLedgerAlias=previous['NewName'],
            PreviousMappedAlias=mapped_name, Alias=reviewed['NewName'], Evidence=reviewed['Reason']))
    result['Reason'] = 'Reviewed correction: ' + reviewed['Reason']
    return result


def validate_contract_resolution(reviewed, proof):
    """Require the full reviewed/native/final-map family for a fresh addition."""
    family = reviewed.get('ContractFamily')
    if not family or not proof or proof.get('Id') != family:
        raise ValueError('Contract resolution requires its checked complete family')
    groups = [proof.get(k, []) for k in ('ReviewedMembers', 'Changes', 'FinalRows')]
    keys = [{(r['Module'], r['Token']) for r in rows} for rows in groups]
    if not keys[0] or any(len(rows) != len(keyset) for rows, keyset in zip(groups, keys)):
        raise ValueError('Contract resolution requires unique family members')
    if keys[0] != keys[1] or keys[0] != keys[2] or (reviewed['Module'], reviewed['Token']) not in keys[0]:
        raise ValueError('Contract resolution cannot accept a partial family')
    changes = {(r['Module'], r['Token']): r for r in groups[1]}
    final = {(r['Module'], r['Token']): r for r in groups[2]}
    for member in groups[0]:
        key = (member['Module'], member['Token'])
        if member.get('ContractFamily') != family or member.get('NewName') != reviewed['NewName']:
            raise ValueError('Contract resolution requires consistent reviewed family names')
        change, mapped = changes[key], final[key]
        if ('Before' not in change or change['Before'] not in (None, '') or
                any(change.get(k) != v for k, v in (
                    ('Kind', 'ContractMethod'), ('Action', None),
                    ('Requested', reviewed['NewName']), ('Applied', reviewed['NewName'])))):
            raise ValueError('Contract resolution requires fresh native additions for the whole family')
        for k, value in (('ContractFamily', family), ('NewName', reviewed['NewName']),
                         ('Signature', member['Signature']), ('ExpectedName', member['OriginalName']),
                         ('Mvid', member['Mvid']), ('Sha256', member['Sha256'])):
            if mapped.get(k) != value:
                raise ValueError('Contract resolution requires the exact checked family map: ' + k)


def resolve_unresolved(previous, reviewed, mapped_name, checked_change, checked_name, checked_scopes=None, checked_family=None):
    """Accept fresh native proof for an explicit previously unresolved definition."""
    require_identity(previous, reviewed)
    if not previous.get('Unresolved') or previous.get('NewName') or mapped_name:
        raise ValueError('Resolution requires an unresolved, unmapped previous definition')
    if any(scope.get('NewName') for label in ('ParameterNames', 'LocalNames') for scope in previous.get(label, [])):
        raise ValueError('Resolution cannot discard previous scoped aliases')
    if (not reviewed.get('ResolveExistingUnresolved') or reviewed.get('Unresolved') or
            not reviewed.get('NewName') or not reviewed.get('Reason') or reviewed.get('UnresolvedReason')):
        raise ValueError('Resolution requires an explicit supported alias and evidence')
    if reviewed.get('PreviousUnresolvedEvidence') != {key: previous.get(key, '') for key in ('Reason', 'UnresolvedReason')}:
        raise ValueError('Resolution requires the exact previous unresolved rationale')
    kind = {2: 'Type', 4: 'Field', 6: 'Method'}.get(int(reviewed['Token'], 16) >> 24)
    native_kind = kind
    if kind == 'Method' and reviewed.get('ContractFamily'):
        validate_contract_resolution(reviewed, checked_family)
        native_kind = 'ContractMethod'
    if (not kind or not checked_change or 'Before' not in checked_change or checked_change['Before'] not in (None, '') or
            any(checked_change.get(key) != value for key, value in (
            ('Kind', native_kind), ('Module', reviewed['Module']), ('Token', reviewed['Token']),
            ('Requested', reviewed['NewName']), ('Applied', reviewed['NewName']), ('Action', None)))):
        raise ValueError('Resolution requires the exact native definition addition')
    if checked_name != reviewed['NewName']:
        raise ValueError('Resolution requires the checked final map alias')
    result = copy.deepcopy(previous)
    result['Unresolved'] = False
    for label, position in (('ParameterNames', 'Sequence'), ('LocalNames', 'Index')):
        for record in (previous, reviewed):
            positions = [entry[position] for entry in record.get(label, [])]
            if len(positions) != len(set(positions)):
                raise ValueError('Duplicate resolution scope position: ' + label)
    scope_review = copy.deepcopy(reviewed)
    scope_review['NewName'] = ''
    if any(scope.get('NewName') for label in ('ParameterNames', 'LocalNames') for scope in reviewed.get(label, [])):
        result = merge_scopes(result, scope_review, '', checked_scopes)
    for label, position, expected_key, inventory_key in (
            ('ParameterNames', 'Sequence', 'ExpectedName', 'OriginalName'),
            ('LocalNames', 'Index', 'ExpectedType', 'ExpectedType')):
        for scope in result.get(label, []):
            if not scope.get('NewName'):
                continue
            checked = (checked_scopes or {}).get((label, scope[position]))
            if not checked or checked.get('NewName') != scope['NewName'] or checked.get(expected_key) != scope.get(inventory_key):
                raise ValueError('Resolution requires checked scoped identity: ' + label)
    result.update(NewName=reviewed['NewName'], UnresolvedReason='', NeedsReadableName=reviewed['NeedsReadableName'],
                  ReviewDisposition='rename', Reason=reviewed['Reason'])
    if reviewed.get('ContractFamily'):
        result['ContractFamily'] = reviewed['ContractFamily']
        result['MappingBlocker'] = reviewed.get('MappingBlocker')
    result.setdefault('UnresolvedResolutions', []).append(dict(Alias=reviewed['NewName'],
        PreviousReason=previous.get('Reason', ''), PreviousUnresolvedReason=previous.get('UnresolvedReason', ''), Evidence=reviewed['Reason']))
    for key in ('ResolveExistingUnresolved', 'PreviousUnresolvedEvidence'):
        result.pop(key, None)
    return result


def proposal_preimage(row):
    """Bind a proposal application to the prior decision and scope inventory."""
    return copy.deepcopy({key: row.get(key, '' if key not in ('ParameterNames', 'LocalNames') else [])
                          for key in ('NewName', 'Reason', 'UnresolvedReason', 'ParameterNames', 'LocalNames')})


def apply_proposal(previous, reviewed, mapped_name, checked_change, checked_name, checked_scopes=None, checked_family=None):
    """Apply the same historical proposal only after a fresh complete native check."""
    require_identity(previous, reviewed)
    alias = previous.get('NewName')
    if (not alias or previous.get('Unresolved') or mapped_name or
            not reviewed.get('ApplyExistingProposal') or reviewed.get('NewName') != alias or
            reviewed.get('Unresolved') or reviewed.get('UnresolvedReason') or not reviewed.get('Reason')):
        raise ValueError('Proposal application requires an explicit unchanged, supported, unmapped proposal')
    if reviewed.get('PreviousProposalEvidence') != proposal_preimage(previous):
        raise ValueError('Proposal application requires the exact previous decision and scopes')
    kind = {2: 'Type', 4: 'Field', 6: 'Method'}.get(int(reviewed['Token'], 16) >> 24)
    if kind == 'Method' and reviewed.get('ContractFamily'):
        validate_contract_resolution(reviewed, checked_family)
        kind = 'ContractMethod'
    if (not kind or not checked_change or 'Before' not in checked_change or checked_change['Before'] not in (None, '') or
            any(checked_change.get(key) != value for key, value in (
                ('Kind', kind), ('Module', reviewed['Module']), ('Token', reviewed['Token']),
                ('Requested', alias), ('Applied', alias), ('Action', None))) or checked_name != alias):
        raise ValueError('Proposal application requires the exact fresh native addition and checked final alias')
    needs_merge = False
    for label, position in (('ParameterNames', 'Sequence'), ('LocalNames', 'Index')):
        for record in (previous, reviewed):
            positions = [entry[position] for entry in record.get(label, [])]
            if len(positions) != len(set(positions)):
                raise ValueError('Duplicate proposal scope position: ' + label)
        old = {entry[position]: entry for entry in previous.get(label, [])}
        needs_merge |= any(entry.get('NewName') and entry['NewName'] != old.get(entry[position], {}).get('NewName')
                           for entry in reviewed.get(label, []))
    scope_review = copy.deepcopy(reviewed)
    scope_review['NewName'] = ''
    result = merge_scopes(previous, scope_review, '', checked_scopes) if needs_merge else copy.deepcopy(previous)
    for label, position, expected_key, inventory_key in (
            ('ParameterNames', 'Sequence', 'ExpectedName', 'OriginalName'),
            ('LocalNames', 'Index', 'ExpectedType', 'ExpectedType')):
        for entry in result.get(label, []):
            if not entry.get('NewName'):
                continue
            checked = (checked_scopes or {}).get((label, entry[position]))
            if not checked or checked.get('NewName') != entry['NewName'] or checked.get(expected_key) != entry.get(inventory_key):
                raise ValueError('Proposal application lost a checked scope decision: ' + label)
    result.update(Reason=reviewed['Reason'], UnresolvedReason='', ReviewDisposition='rename',
                  NeedsReadableName=reviewed['NeedsReadableName'], ContractFamily=reviewed.get('ContractFamily'),
                  MappingBlocker=reviewed.get('MappingBlocker'))
    result.setdefault('ProposalApplications', []).append(dict(Alias=alias, PreviousReason=previous.get('Reason', ''),
                                                              Evidence=reviewed['Reason']))
    for key in ('ApplyExistingProposal', 'PreviousProposalEvidence'):
        result.pop(key, None)
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
    checked_replacement = replace_alias(previous, reviewed, mapped_name, checked_change)
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
    if previous.get('NewName') != mapped_name:
        result.setdefault('LedgerAliasCorrections', []).append(checked_replacement['LedgerAliasCorrections'][-1])
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
    if 'UnresolvedScopeEvidence' in reviewed:
        # Keep earlier unknown positions unless fresh positional evidence
        # replaces them. Accepted aliases retire their active missing-evidence
        # entries, while the previous evidence remains in the review history.
        current = {}
        for label, inventory_label, position, preimage in (
                ('Parameters', 'ParameterNames', 'Sequence', 'OriginalName'),
                ('Locals', 'LocalNames', 'Index', 'ExpectedType')):
            inventory = {p[position]: p for p in reviewed.get(inventory_label, [])}
            aliases = {p[position] for p in result.get(inventory_label, []) if p.get('NewName')}
            merged = {}
            for document in (previous.get('UnresolvedScopeEvidence', {}), reviewed['UnresolvedScopeEvidence']):
                seen = set()
                for entry in document.get(label, []):
                    slot = entry[position]
                    if slot in seen or not entry.get('MissingEvidence'):
                        raise ValueError('Duplicate or empty unresolved scope evidence')
                    seen.add(slot)
                    if slot in inventory and inventory[slot].get(preimage) != entry.get(preimage):
                        raise ValueError('Unresolved scope preimage differs: ' + label)
                    if document is reviewed['UnresolvedScopeEvidence'] and slot not in inventory:
                        raise ValueError('Unresolved scope is absent from reviewed inventory')
                    merged[slot] = copy.deepcopy(entry)
            current[label] = [entry for slot, entry in sorted(merged.items()) if slot not in aliases]
        if current != previous.get('UnresolvedScopeEvidence'):
            result.setdefault('ScopeEvidenceReviews', []).append(dict(
                PreviousUnresolvedScopeEvidence=copy.deepcopy(previous.get('UnresolvedScopeEvidence', {})),
                Evidence=reviewed['Reason']))
        result['UnresolvedScopeEvidence'] = current
    if reviewed.get('UnresolvedDefinitionEvidence') and not result['NewName']:
        result['UnresolvedDefinitionEvidence'] = reviewed['UnresolvedDefinitionEvidence']
    result['Reason'] = (previous.get('Reason') or '') + '\nScope review: ' + reviewed['Reason']
    return result
