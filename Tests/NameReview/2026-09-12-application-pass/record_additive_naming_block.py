"""Record a checked additive naming block and immutable evidence snapshot.

Native tools alone create maps. This recorder verifies their artifacts, updates
bounded progress records and copies reports; it never edits ETS source/binaries,
maps or review ledgers. Block-specific decisions belong in the JSON input.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from prepare_physical_review import prepare


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest().upper()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def aliases(path):
    result = {}
    for module in ET.parse(path).getroot().findall('Module'):
        for row in module:
            if row.get('NewName'):
                result[(module.get('Path'), row.tag, row.get('Token'), '')] = row.get('NewName')
            for scoped in row:
                if scoped.get('NewName'):
                    position = scoped.get('Sequence') if scoped.tag == 'Parameter' else scoped.get('Index')
                    result[(module.get('Path'), scoped.tag, row.get('Token'), position)] = scoped.get('NewName')
    return result


def encode(value, depth=0):
    if not isinstance(value, (dict, list)) or not value:
        return json.dumps(value, ensure_ascii=False)
    children = list(value.values()) if isinstance(value, dict) else value
    compact = json.dumps(value, ensure_ascii=False)
    if all(not isinstance(v, (dict, list)) for v in children) and len(compact) <= 400:
        return compact
    indent = '  ' * (depth + 1)
    if isinstance(value, dict):
        body = ',\n'.join(indent + json.dumps(k) + ': ' + encode(v, depth + 1) for k, v in value.items())
        return '{\n' + body + '\n' + '  ' * depth + '}'
    return '[\n' + ',\n'.join(indent + encode(v, depth + 1) for v in value) + '\n' + '  ' * depth + ']'


def verify(config):
    checkpoint = read(config['Checkpoint'])
    mapping = checkpoint['Map']
    review = read(checkpoint['Review']['Path'])
    update = read(checkpoint['UpdateReport'])
    check = read(checkpoint['CheckReport'])
    inventory = read(config['Inventory'])
    owners = read(config['Owners'])
    state = read(config['State'])
    sink = Path(config['Sink'])
    ledger = read(sink / 'reviewed63.json')
    prior = read(config['PreviousLedger'])
    require(update['Success'] and check['Success'] and not update['Errors'] and not check['Errors'], 'Native checks failed')
    require(digest(mapping['Path']) == mapping['Sha256'] == check['BaseMapSha256'] == inventory['MapSha256'], 'Current map binding changed')
    require(digest(checkpoint['PreviousMap']['Path']) == update['BaseMapSha256'] == checkpoint['PreviousMap']['Sha256'], 'Previous map binding changed')
    require(digest(checkpoint['Review']['Path']) == checkpoint['Review']['Sha256'] == update['ReviewSha256'], 'Review binding changed')
    require(prepare(read(config['Spec'])) == review, 'Physical review does not reproduce')
    require(not read(config['NativeCoverage'])['Invalid'] and not read(config['NativeCoverage'])['Conflicts'], 'Ledger has invalid/conflicting rows')
    require(digest(sink / 'reviewed63.json') == inventory['LedgerSha256'], 'Current ledger binding changed')
    require(owners['Inputs']['map']['Sha256'] == mapping['Sha256'] and owners['Inputs']['ledger']['Sha256'] == inventory['LedgerSha256'], 'Owner join is stale')
    require(len(inventory['Modules']) == len(owners['Modules']) == config['ExpectedModules'], 'Physical scope differs')
    require(inventory['NativeCalls'] == owners['NativeCalls'] == 0, 'Expected verified cached joins')
    require(inventory['RemainingNativeCandidates'] == owners['RemainingNamingCandidates'], 'Candidate joins differ')
    require(state['Maps']['63']['Sha256'] == mapping['Sha256'] and not state['Maps']['63']['AppliedToSource'], 'State differs from checkpoint')
    require(digest(state['Maps']['64']['Path']) == state['Maps']['64']['Sha256'], 'ETS 6.4 map binding changed')
    for name in ('SdkWhitelist63', 'ContractReferences63'):
        binding = state['Compatibility'][name]
        require(digest(binding['Path']) == binding['Sha256'], name + ' changed')
    require(state['Compatibility']['SdkWhitelist63']['Sha256'] == check['SdkNameWhitelistSha256'], 'SDK whitelist differs')
    require(state['Compatibility']['ContractReferences63']['Sha256'] == check['ContractReferenceSha256'], 'Contract manifest differs')
    before, after = aliases(checkpoint['PreviousMap']['Path']), aliases(mapping['Path'])
    require(all(after.get(k) == v for k, v in before.items()), 'An existing alias/scope changed or disappeared')
    additions = {k: v for k, v in after.items() if k not in before}
    kinds = dict(collections.Counter(k[1] for k in additions))
    require(kinds == config['ExpectedAliasKinds'], 'Addition kinds differ')
    require(len(additions) == len(update['Changes']) == checkpoint['AcceptedDecisions'], 'Native edits differ from additions')
    require(all(c['Requested'] == c['Applied'] and c['Before'] != c['Applied'] for c in update['Changes']), 'Suffix or no-op native edit')
    for kind in ('Types', 'Fields', 'Methods'):
        old = {(r['Module'], r['Token']): r for r in prior[kind]}
        current = {(r['Module'], r['Token']): r for r in ledger[kind]}
        allowed = {(r['Module'], r['Token']) for r in review[kind]}
        require(set(old) <= set(current), 'Prior review rows disappeared')
        require({k for k, v in current.items() if old.get(k) != v} <= allowed, 'Unreviewed ledger change')
    for path in config['EvidenceFiles']:
        require(Path(path).is_file(), 'Missing evidence: ' + path)
    return checkpoint, review, inventory, owners, state, kinds


def record(config, config_path):
    checkpoint, review, inventory, owners, state, kinds = verify(config)
    sink = Path(config['Sink'])
    snapshot = Path(config['Snapshot'])
    destinations = {key: sink / name for key, name in config['Copies'].items()}
    proof_path = sink / config['ProofName']
    require(not snapshot.exists() and not proof_path.exists(), 'Choose fresh snapshot/proof outputs')
    require(all(not p.exists() for p in destinations.values()), 'Choose fresh copied report outputs')
    # Only progress text and measured naming counts are changed here.
    naming = state['Naming']['Backlog']
    naming['ByKind'] = {k: sum(v.get('Candidate' + c, 0) for c in ('Unreviewed', 'ScopedOnly', 'UnappliedLedgerAlias')) for k, v in inventory['Counts'].items()}
    top = collections.Counter(r['Module'] for r in read(Path(config['Inventory']).parent / 'remaining-candidates.json'))
    naming['TopModules'] = dict(top.most_common(5))
    naming['TopModules']['all others'] = sum(top.values()) - sum(v for _, v in top.most_common(5))
    naming.update(Report=str(destinations['Inventory']), GeneratedOwnerReport=str(destinations['Owners']), RemainingNativeCandidates=inventory['RemainingNativeCandidates'], OpenRoute=config['NextRoute'], Shape=config['Shape'])
    state['Maps']['63']['CountBasis'] = config['CountBasis']
    state['Readability']['PhysicalScope63']['NextBlock'] = config['NextRoute']
    state['Naming']['NextItems'][0]['Detail'] = config['Detail']
    state['Naming']['NextItems'][3]['Detail'] = config['UnresolvedDetail']
    state['Deferred']['SourceExport']['Next'][0] = config['NextRoute']
    encoded = encode(state) + '\n'
    require(len(encoded.splitlines()) < 200 and json.loads(encoded) == state, 'State is not bounded/roundtrippable')
    progress = read(sink / 'progress.json')
    progress['GeneratedOwnerInventory63'] = dict(Path=str(destinations['Owners']), Sha256=digest(config['Owners']), MapSha256=inventory['MapSha256'], RemainingNamingCandidates=inventory['RemainingNativeCandidates'], NativeCalls=0, SourceMergeVerified=False)
    progress[config['ProgressKey']] = str(proof_path)
    unresolved = [dict(Kind=k, Token=r['Token'], Type=r['Type'], Reason=r['UnresolvedReason']) for k in ('Types', 'Fields', 'Methods') for r in review[k] if r.get('Unresolved')]
    pins = [Path(p) for p in config['EvidenceFiles']] + [Path(config_path), Path(__file__), Path(config['Checkpoint']), Path(checkpoint['Map']['Path']), Path(checkpoint['PreviousMap']['Path']), Path(checkpoint['Review']['Path']), Path(checkpoint['UpdateReport']), Path(checkpoint['CheckReport'])]
    # Validate everything before the first mutation. Copies/snapshots never overwrite.
    snapshot.mkdir(parents=True, exist_ok=False)
    for key, destination in destinations.items():
        shutil.copyfile(config[key], destination)
        pins.append(destination)
    Path(config['State']).write_text(encoded, encoding='utf-8')
    shutil.copyfile(config['State'], sink / 'STATE.json')
    (sink / 'progress.json').write_text(json.dumps(progress, indent=2) + '\n', encoding='utf-8')
    for name in ('STATE.json', 'progress.json', 'reviewed63.json'):
        shutil.copyfile(sink / name, snapshot / name)
        pins.append(snapshot / name)
    proof = dict(Format=1, Kind='PhysicalNamingBlockCoverage', Block=checkpoint['Block'], Map=checkpoint['Map'], Snapshot=str(snapshot),
                 Pins=[dict(Path=str(p), Sha256=digest(p)) for p in dict.fromkeys(pins)], AcceptedNewAliases=checkpoint['AcceptedDecisions'], AliasKinds=kinds,
                 ReviewedDefinitions=checkpoint['ReviewedDecisions'], ExplicitScopeMerges=checkpoint['ExplicitScopeMerges'], ExplicitUnresolvedDefinitions=len(unresolved),
                 UnresolvedDefinitions=unresolved, PriorAliasesAndScopesPreserved=True, ReviewReproduced=True, NativeSuccess=True, NativeInvalidRows=0, NativeConflicts=0,
                 WholeScope=dict(Modules=len(inventory['Modules']), RemainingBefore=config['RemainingBefore'], RemainingAfter=inventory['RemainingNativeCandidates'], Counts=inventory['Counts'],
                                 InventoryNativeCalls=0, OwnerNativeCalls=0, InventorySeconds=inventory['ElapsedSeconds'], OwnerSeconds=owners['ElapsedSeconds']),
                 EvidenceFacts=copy.deepcopy(config['EvidenceFacts']), SourceMergingVerified=False, AppliedToSource=False,
                 NotProven=['No consolidated ETS export/build, metadata restoration or runtime compatibility is established by this naming block.',
                            'Native lexical flags select work; candidate counts do not prove whole-application readability.',
                            'Structural generated-owner evidence does not establish printed source merging.', 'ETS 6.4 verification follows ETS 6.3 completion.'])
    with proof_path.open('x', encoding='utf-8') as stream:
        json.dump(proof, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(Proof=str(proof_path), Aliases=proof['AcceptedNewAliases'], Kinds=kinds, Unresolved=len(unresolved), Remaining=inventory['RemainingNativeCandidates'], Pins=len(proof['Pins']))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    config = read(args.config)
    if args.verify_only:
        verify(config)
        print('Verified additive naming artifacts without writes')
    else:
        record(config, args.config)


if __name__ == '__main__':
    main()
