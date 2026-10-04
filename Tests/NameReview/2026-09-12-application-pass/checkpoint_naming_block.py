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
from sdk_proposal_retirement import load_sdk_symbols, key as sdk_key, retire_sdk_proposal
from contract_sdk_proposal_retirement import load_contract_sdk_evidence, retire_contract_sdk_proposal, preserve_contract_sdk_method
from framework_contract_preservation import load_framework_contract_evidence, preserve_framework_contract_method

parser = argparse.ArgumentParser(description=__doc__)
for name in ('state', 'sink', 'map', 'review', 'update', 'check', 'block'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--merge-reviewed-scopes', action='store_true',
                    help='Explicitly merge new parameter/local decisions into existing physical ledger rows')
parser.add_argument('--resolve-reviewed-scoped-definitions', action='store_true',
                    help='Resolve scope-only method definitions with exact prior rationale and native addition proof')
parser.add_argument('--retire-rejected-sdk-proposals', action='store_true',
                    help='Review-only: retire unapplied proposals protected by the physical map-bound SDK whitelist')
parser.add_argument('--retire-rejected-contract-sdk-proposals', action='store_true',
                    help='Review-only: retire unapplied proposals proven protected by native CLR/SDK family evidence')
parser.add_argument('--contract-sdk-evidence', help='Hash-bound native PhysicalSdkContractProtectionEvidence report')
parser.add_argument('--preserve-sdk-contract-methods', action='store_true',
                    help='Review-only: record previously unreviewed methods protected by exact native CLR/SDK families')
parser.add_argument('--preserve-framework-contract-methods', action='store_true',
                    help='Review-only: preserve new explicit CLR async/iterator implementations from pinned native proof')
parser.add_argument('--framework-contract-evidence', help='Hash-bound native PhysicalFrameworkContractEvidence report')
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
assert not args.retire_rejected_sdk_proposals or args.review_only, 'SDK proposal retirement requires a review-only checkpoint'
assert not args.retire_rejected_contract_sdk_proposals or args.review_only, 'SDK contract retirement requires a review-only checkpoint'
assert not args.preserve_sdk_contract_methods or args.review_only, 'SDK contract preservation requires a review-only checkpoint'
assert bool(args.contract_sdk_evidence) == bool(args.retire_rejected_contract_sdk_proposals or args.preserve_sdk_contract_methods), 'Native SDK family evidence requires its explicit flag'
assert not args.preserve_framework_contract_methods or args.review_only, 'Framework preservation requires a review-only checkpoint'
assert bool(args.framework_contract_evidence) == bool(args.preserve_framework_contract_methods), 'Native framework proof requires its explicit flag'
state_path, sink = pathlib.Path(args.state).resolve(), pathlib.Path(args.sink).resolve()
map_path, review_path = pathlib.Path(args.map).resolve(), pathlib.Path(args.review).resolve()
update_path, check_path = pathlib.Path(args.update).resolve(), pathlib.Path(args.check).resolve()
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
sdk_symbols = load_sdk_symbols(map_path) if args.retire_rejected_sdk_proposals else {}
mapped_entries = {sdk_key(module.get('Path'), row.get('Token')): row for module in root.findall('Module') for row in module}
retired_sdk_proposals = 0
retired_contract_sdk_proposals = 0
preserved_sdk_contract_methods = 0
contract_sdk_evidence = {}
framework_contract_evidence = {}
preserved_framework_contract_methods = 0
if args.preserve_framework_contract_methods:
    binding = review['NativeFrameworkContractEvidence']
    assert pathlib.Path(binding['Path']).resolve() == pathlib.Path(args.framework_contract_evidence).resolve()
    assert digest(pathlib.Path(binding['Cli'])) == binding['CliSha256'], 'Native framework inspector changed'
    framework_contract_evidence = load_framework_contract_evidence(map_path, args.framework_contract_evidence, binding['Sha256'], check['ContractReferenceSha256'])
if args.retire_rejected_contract_sdk_proposals or args.preserve_sdk_contract_methods:
    binding = review.get('NativeSdkContractEvidence', {})
    assert pathlib.Path(binding['Path']).resolve() == pathlib.Path(args.contract_sdk_evidence).resolve(), 'Native evidence path differs from review'
    contract_sdk_evidence = load_contract_sdk_evidence(map_path, args.contract_sdk_evidence, binding['Sha256'], check['ContractReferenceSha256'])
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
        if row.get('PreserveFrameworkContractMethod'):
            assert args.preserve_framework_contract_methods and kind == 'Methods' and key not in keys
            proof = framework_contract_evidence[sdk_key(*key)]
            assert row['PreservedExternalFrameworkContract']['ProofSha256'] == review['NativeFrameworkContractEvidence']['Sha256']
            ledger[kind].append(preserve_framework_contract_method(row, mapped_entries.get(sdk_key(*key)), proof))
            keys[key] = len(ledger[kind]) - 1
            preserved_framework_contract_methods += 1
            continue
        if row.get('PreserveSdkContractMethod'):
            assert args.preserve_sdk_contract_methods and kind == 'Methods' and key not in keys, 'New contract preservation requires an unreviewed method and explicit checkpoint flag'
            sk = sdk_key(*key)
            recorded = preserve_contract_sdk_method(row, mapped_entries.get(sk), contract_sdk_evidence.get(sk),
                check['SdkNameWhitelistSha256'], check['ContractReferenceSha256'])
            keys[key] = len(ledger[kind])
            ledger[kind].append(recorded)
            preserved_sdk_contract_methods += 1
            continue
        if row.get('RetireRejectedContractSdkProposal'):
            assert args.retire_rejected_contract_sdk_proposals and kind == 'Methods' and key in keys, 'Contract SDK retirement requires its previous method and explicit checkpoint flag'
            sk = sdk_key(*key)
            ledger[kind][keys[key]] = retire_contract_sdk_proposal(ledger[kind][keys[key]], row, mapped_entries.get(sk),
                contract_sdk_evidence.get(sk), check['SdkNameWhitelistSha256'], check['ContractReferenceSha256'])
            retired_contract_sdk_proposals += 1
            continue
        if row.get('RetireRejectedSdkProposal'):
            assert args.retire_rejected_sdk_proposals and key in keys, 'SDK retirement requires its previous ledger proposal and explicit checkpoint flag'
            sk = sdk_key(*key)
            ledger[kind][keys[key]] = retire_sdk_proposal(ledger[kind][keys[key]], row, mapped_entries.get(sk),
                sdk_symbols.get(sk), check['SdkNameWhitelistSha256'])
            retired_sdk_proposals += 1
            continue
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
              'ExplicitRejectedSdkProposalRetirements': retired_sdk_proposals,
              'ExplicitRejectedContractSdkProposalRetirements': retired_contract_sdk_proposals,
              'ExplicitSdkContractMethodPreservations': preserved_sdk_contract_methods,
              'ExplicitFrameworkContractMethodPreservations': preserved_framework_contract_methods,
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
