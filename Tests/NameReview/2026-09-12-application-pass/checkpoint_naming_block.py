"""Record a native-checked naming block without rerunning consolidated audits.

Only maps, review ledgers and state records are read/written. ETS source and
binaries are never modified. Run native --update-map and --check-map first.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import shutil
import xml.etree.ElementTree as ET
from review_ledger import merge_scopes, replace_alias, replace_method_alias, remove_method_alias, resolve_unresolved, resolve_scoped_definition, validate_review_only, refresh_evidence, apply_proposal

parser = argparse.ArgumentParser(description=__doc__)
for name in ('state', 'sink', 'map', 'review', 'update', 'check', 'block'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--merge-reviewed-scopes', action='store_true',
                    help='Explicitly merge new parameter/local decisions into existing physical ledger rows')
parser.add_argument('--resolve-reviewed-scoped-definitions', action='store_true',
                    help='Resolve scope-only method definitions with exact prior rationale and native addition proof')
parser.add_argument('--replace-reviewed-aliases', action='store_true',
                    help='Explicitly replace a reviewed definition/parameter alias using its exact native change report')
parser.add_argument('--remove-reviewed-aliases', action='store_true',
                    help='Record explicit native withdrawal of an unsupported standalone unscoped method alias')
parser.add_argument('--resolve-reviewed-unresolved', action='store_true',
                    help='Resolve explicitly reviewed unknown definitions using exact native additions and previous evidence')
parser.add_argument('--apply-reviewed-proposals', action='store_true',
                    help='Apply unchanged historical proposals with exact decision/scope preimages and fresh native additions')
parser.add_argument('--review-only', action='store_true',
                    help='Checkpoint preservation/unresolved decisions with no aliases and a byte-identical checked map')
parser.add_argument('--refresh-reviewed-evidence', action='store_true',
                    help='Review-only rationale correction with exact previous evidence and unchanged naming decisions')
args = parser.parse_args()
assert not args.refresh_reviewed_evidence or args.review_only, 'Evidence refresh requires a review-only checkpoint'
state_path, sink = pathlib.Path(args.state), pathlib.Path(args.sink)
map_path, review_path = pathlib.Path(args.map), pathlib.Path(args.review)
update_path, check_path = pathlib.Path(args.update), pathlib.Path(args.check)
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
state, review, update, check = map(read, (state_path, review_path, update_path, check_path))
previous = state['Maps']['63']
assert digest(pathlib.Path(previous['Path'])) == previous['Sha256'], 'Stale current state map'
assert update['BaseMapSha256'] == previous['Sha256'], 'Block is not based on the current map'
assert update['ReviewSha256'] == digest(review_path), 'Stale review report'
assert check['BaseMapSha256'] == digest(map_path), 'Stale final map check'
assert update['Success'] and check['Success'] and not update['Errors'] and not check['Errors']
if args.review_only:
    assert args.block and all(c.isalnum() or c in '-_' for c in args.block), 'Invalid review checkpoint filename'
    validate_review_only(review, update['Changes'], previous['Sha256'], digest(map_path))
else:
    assert update['Changes'] and all(c['Requested'] == c['Applied'] for c in update['Changes']), 'Rejected or suffixed name'
assert review['ContractReferenceSha256'] == update['ContractReferenceSha256'] == check['ContractReferenceSha256']
root = ET.parse(map_path).getroot()
assert root.get('SdkNameWhitelistSha256') == update['SdkNameWhitelistSha256'] == check['SdkNameWhitelistSha256']
rows = {kind: sum(1 for row in root.iter(tag) if row.get('NewName')) for kind, tag in
        [('Types', 'Type'), ('Methods', 'Method'), ('Fields', 'Field'), ('Parameters', 'Parameter'), ('Locals', 'Local')]}
ledger_path = sink / 'reviewed63.json'
ledger = read(ledger_path)
assert ledger['TargetRoot'] == review['TargetRoot'] == root.get('InputDirectory')
base_root = ET.parse(previous['Path']).getroot()
base_names = {(module.get('Path'), row.get('Token')): row.get('NewName', '')
              for module in base_root.findall('Module') for row in module}
final_names = {(module.get('Path'), row.get('Token')): row.get('NewName', '')
               for module in root.findall('Module') for row in module}
checked_scopes = {(module.get('Path'), row.get('Token')):
                 {(label, int(scope.get(position))): dict(scope.attrib)
                  for label, tag, position in (('ParameterNames', 'Parameter', 'Sequence'), ('LocalNames', 'Local', 'Index'))
                  for scope in row.findall(tag)}
                 for module in root.findall('Module') for row in module}
merged_rows = 0
scoped_definitions_resolved = 0
replaced_rows = 0
refreshed_rows = 0
removed_rows = 0
resolved_rows = 0
applied_proposals = 0
checked_changes = {(c['Module'], c['Token']): c for c in update['Changes'] if c['Kind'] in ('Field', 'Type', 'Method', 'ContractMethod')}
checked_families = {}
for method in review['Methods']:
    family = method.get('ContractFamily')
    if not (method.get('ResolveExistingUnresolved') or method.get('ApplyExistingProposal')) or not family or family in checked_families:
        continue
    members = [m for m in review['Methods'] if m.get('ContractFamily') == family]
    member_keys = {(m['Module'], m['Token']) for m in members}
    checked_families[family] = dict(Id=family, ReviewedMembers=members,
        Changes=[c for c in update['Changes'] if c['Kind'] == 'ContractMethod' and (c['Module'], c['Token']) in member_keys],
        FinalRows=[dict(row.attrib, Module=module.get('Path'), Mvid=module.get('Mvid'), Sha256=module.get('Sha256'))
                   for module in root.findall('Module') for row in module.findall('Method')
                   if row.get('ContractFamily') == family])
scope_replacements = {}
if args.replace_reviewed_aliases:
    for c in update['Changes']:
        if c['Kind'] == 'Parameter':
            scope_replacements.setdefault((c['Module'], c['Token']), {})[('ParameterNames', c['ParameterSequence'])] = c
for kind in ('Types', 'Methods', 'Fields'):
    keys = {(r['Module'], r['Token']): i for i, r in enumerate(ledger[kind])}
    for row in review[kind]:
        key = (row['Module'], row['Token'])
        if row.get('ResolveExistingScopedDefinition'):
            assert args.resolve_reviewed_scoped_definitions and kind == 'Methods' and key in keys, 'Scoped resolution requires its previous method and explicit checkpoint flag'
            ledger[kind][keys[key]] = resolve_scoped_definition(ledger[kind][keys[key]], row, base_names.get(key, ''),
                checked_changes.get(key), final_names.get(key, ''), checked_scopes.get(key, {}))
            scoped_definitions_resolved += 1
            continue
        if row.get('ApplyExistingProposal'):
            assert args.apply_reviewed_proposals and key in keys, 'Proposal application requires explicit authorization and previous ledger row'
            ledger[kind][keys[key]] = apply_proposal(ledger[kind][keys[key]], row, base_names.get(key, ''),
                checked_changes.get(key), final_names.get(key, ''), checked_scopes.get(key, {}), checked_families.get(row.get('ContractFamily')))
            applied_proposals += 1
            continue
        if row.get('ResolveExistingUnresolved'):
            assert args.resolve_reviewed_unresolved and key in keys, 'Resolution requires explicit authorization and previous ledger row'
            ledger[kind][keys[key]] = resolve_unresolved(ledger[kind][keys[key]], row, base_names.get(key, ''),
                checked_changes.get(key), final_names.get(key, ''), checked_scopes.get(key, {}), checked_families.get(row.get('ContractFamily')))
            resolved_rows += 1
            continue
        if row.get('RemoveExistingAlias'):
            assert args.remove_reviewed_aliases and kind == 'Methods', 'Alias withdrawal requires explicit checkpoint authorization'
            old = ledger[kind][keys[key]] if key in keys else None
            recorded = remove_method_alias(old, row, base_names.get(key, ''), checked_changes.get(key), final_names.get(key, ''))
            if key in keys:
                ledger[kind][keys[key]] = recorded
            else:
                keys[key] = len(ledger[kind])
                ledger[kind].append(recorded)
            removed_rows += 1
            continue
        if key in keys:
            if args.refresh_reviewed_evidence and row.get('PreviousEvidence'):
                ledger[kind][keys[key]] = refresh_evidence(ledger[kind][keys[key]], row)
                refreshed_rows += 1
                continue
            if args.replace_reviewed_aliases and kind in ('Types', 'Fields'):
                ledger[kind][keys[key]] = replace_alias(ledger[kind][keys[key]], row, base_names.get(key, ''), checked_changes.get(key))
                replaced_rows += 1
                continue
            if args.replace_reviewed_aliases and kind == 'Methods' and row.get('NewName') and row['NewName'] != base_names.get(key, ''):
                ledger[kind][keys[key]] = replace_method_alias(ledger[kind][keys[key]], row, base_names.get(key, ''),
                                                             checked_changes.get(key), checked_scopes.get(key, {}), scope_replacements.get(key, {}))
                replaced_rows += 1
                continue
            assert args.merge_reviewed_scopes and kind == 'Methods', 'Existing row requires explicit reviewed scope merge'
            ledger[kind][keys[key]] = merge_scopes(ledger[kind][keys[key]], row, base_names.get(key, ''), checked_scopes.get(key, {}), scope_replacements.get(key, {}))
            merged_rows += 1
            continue
        keys[key] = len(ledger[kind])
        ledger[kind].append(row)
version = int(map_path.stem.rsplit('-v', 1)[1])
checkpoint_path = sink / ('checkpoint-review-' + args.block + '.json' if args.review_only else 'checkpoint-naming-v' + str(version) + '.json')
assert not checkpoint_path.exists(), 'Checkpoint already exists'
for original in (review_path, update_path, check_path):
    assert not (sink / original.name).exists(), 'Review/report already published'
checkpoint = {'Format': 1, 'Kind': 'ReviewCheckpoint' if args.review_only else 'NamingCheckpoint', 'Block': args.block,
              'Map': {'Path': str(map_path), 'Sha256': digest(map_path), 'Modules': len(root.findall('Module')), 'Rows': rows},
              'PreviousMap': dict(previous), 'Review': {'Path': str(review_path), 'Sha256': digest(review_path)},
              'UpdateReport': str(update_path), 'CheckReport': str(check_path),
              'AcceptedDecisions': len(update['Changes']), 'SdkNameWhitelistSha256': update['SdkNameWhitelistSha256'],
              'ReviewedDecisions': sum(len(review[kind]) for kind in ('Types', 'Fields', 'Methods')),
              'ExplicitScopeMerges': merged_rows,
              'ExplicitAliasReplacements': replaced_rows,
              'ExplicitEvidenceRefreshes': refreshed_rows,
              'ExplicitAliasWithdrawals': removed_rows,
              'ExplicitUnresolvedResolutions': resolved_rows,
              'ExplicitScopedDefinitionResolutions': scoped_definitions_resolved,
              'ExplicitProposalApplications': applied_proposals,
              'ContractReferenceSha256': update['ContractReferenceSha256'],
              'ConsolidatedVerification': 'Pending application-wide freeze; no new full audit, binary application, ETS export/build or launch is claimed.'}
if args.review_only:
    previous['Checkpoint'] = str(checkpoint_path)
else:
    previous.update(Path=str(map_path), Sha256=digest(map_path), Checkpoint=str(checkpoint_path), NextWave=version + 1, RowsInMap=rows, AppliedToSource=False)
state['UpdatedUtc'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def encode(value, depth=0):
    if not isinstance(value, (dict, list)) or not value:
        return json.dumps(value, ensure_ascii=False)
    children = list(value.values()) if isinstance(value, dict) else value
    compact = json.dumps(value, ensure_ascii=False)
    if all(not isinstance(v, (dict, list)) for v in children) and len(compact) <= 300:
        return compact
    indent = '  ' * (depth + 1)
    if isinstance(value, dict):
        return '{\n' + ',\n'.join(indent + json.dumps(k) + ': ' + encode(v, depth + 1) for k, v in value.items()) + '\n' + '  ' * depth + '}'
    return '[\n' + ',\n'.join(indent + encode(v, depth + 1) for v in value) + '\n' + '  ' * depth + ']'
encoded = encode(state) + '\n'
assert len(encoded.splitlines()) < 200, 'State must stay under 200 lines'
assert json.loads(encoded) == state
progress_path = sink / 'progress.json'
progress = read(progress_path)
progress['Maps']['63'] = {'Path': previous['Path'], 'Sha256': previous['Sha256'], 'AppliedToSource': False}
progress['NamingCheckpoint'] = str(checkpoint_path)
for path, document in ((checkpoint_path, checkpoint), (ledger_path, ledger), (progress_path, progress)):
    path.write_text(json.dumps(document, indent=1 if path == ledger_path else 2, ensure_ascii=path == ledger_path) + '\n', encoding='utf-8')
for original in (review_path, update_path, check_path):
    destination = sink / original.name
    shutil.copyfile(original, destination)
state_path.write_text(encoded, encoding='utf-8')
shutil.copyfile(state_path, sink / 'STATE.json')
print('Naming checkpoint:', checkpoint_path, '; accepted decisions:', len(update['Changes']), '; full verification pending')
