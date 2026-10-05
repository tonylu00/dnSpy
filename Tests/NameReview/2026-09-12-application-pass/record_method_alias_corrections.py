"""Verify and record native method alias corrections without editing ETS/maps.

Explicit ledger/map preimages are required. Definition corrections preserve every
other alias, scope and ledger decision. Configuration supplies evidence and text.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil

from record_additive_naming_block import aliases, digest, encode, read, require
from review_ledger import require_identity


def verify_corrections(before, after, prior, current, review, changes, expected):
    require(bool(expected), 'No corrections supplied')
    keys = [(r['Module'], 'Method', r['Token'], '') for r in expected]
    require(len(keys) == len(set(keys)), 'Duplicate correction')
    wanted = dict(before)
    old_rows = {(r['Module'], r['Token']): r for r in prior['Methods']}
    new_rows = {(r['Module'], r['Token']): r for r in current['Methods']}
    reviews = {(r['Module'], r['Token']): r for r in review['Methods']}
    require(len(review['Methods']) == len(reviews) == len(expected) and
            not review['Types'] and not review['Fields'], 'Review differs from corrections')
    require(len(changes) == len(expected), 'Unexpected native edits')
    allowed = set()
    for e, key in zip(expected, keys):
        short = (e['Module'], e['Token'])
        require(short in old_rows and short in new_rows and short in reviews, 'Missing correction row')
        old, new, row = old_rows[short], new_rows[short], reviews[short]
        require_identity(old, row)
        require_identity(old, new)
        require(not old.get('Unresolved') and not row.get('Unresolved'), 'Unresolved alias correction')
        require(old['NewName'] == e['PreviousLedgerAlias'] and before.get(key) == e['MappedAlias'], 'Wrong preimage')
        require(row['NewName'] == new['NewName'] == e['NewName'] != e['MappedAlias'], 'Wrong replacement')
        if old['NewName'] != e['MappedAlias']:
            require(row.get('PreviousLedgerAlias') == old['NewName'] and
                    row.get('ExpectedMappedAlias') == e['MappedAlias'], 'Missing historical preimages')
            history = new.get('LedgerAliasCorrections', [])
            require(bool(history) and history[-1] == dict(PreviousLedgerAlias=old['NewName'],
                    PreviousMappedAlias=e['MappedAlias'], Alias=e['NewName'], Evidence=row['Reason']), 'Missing correction history')
        else:
            require(not any(k in row for k in ('PreviousLedgerAlias', 'ExpectedMappedAlias')), 'Stale historical preimages')
        exact = [c for c in changes if (c['Module'], c['Token']) == short]
        require(len(exact) == 1 and all(exact[0].get(k) == v for k, v in
                dict(Kind='Method', Before=e['MappedAlias'], Requested=e['NewName'], Applied=e['NewName']).items()), 'Wrong native replacement')
        for label in ('ParameterNames', 'LocalNames'):
            require(new.get(label, []) == old.get(label, []), 'Scope inventory changed')
        retained = set(old) | set(new)
        retained -= {'NewName', 'Reason', 'LedgerAliasCorrections'}
        require(all(new.get(k) == old.get(k) for k in retained), 'Correction changed a prior annotation')
        require(new.get('Reason') == (old.get('Reason') or '') + '\nReviewed method correction: ' + row['Reason'], 'Correction lost historical evidence')
        wanted[key] = e['NewName']
        allowed.add(short)
    require(after == wanted, 'An unreviewed alias/scope changed')
    require(set(old_rows) == set(new_rows) and
            all(new_rows[k] == v for k, v in old_rows.items() if k not in allowed), 'Unreviewed method decision changed')
    for kind in ('Types', 'Fields'):
        require(current[kind] == prior[kind], 'Unreviewed definition decision changed')


def verify(config):
    checkpoint = read(config['Checkpoint'])
    mapping = checkpoint['Map']
    update, check = read(checkpoint['UpdateReport']), read(checkpoint['CheckReport'])
    review = read(checkpoint['Review']['Path'])
    state = read(config['State'])
    sink = Path(config['Sink'])
    ledger, prior = read(sink / 'reviewed63.json'), read(config['PreviousLedger'])
    inventory, owners = read(config['Inventory']), read(config['Owners'])
    require(update['Success'] and check['Success'] and not update['Errors'] and not check['Errors'], 'Native checks failed')
    require(digest(mapping['Path']) == mapping['Sha256'] == check['BaseMapSha256'] == inventory['MapSha256'], 'Current map changed')
    require(digest(checkpoint['PreviousMap']['Path']) == update['BaseMapSha256'] == checkpoint['PreviousMap']['Sha256'], 'Previous map changed')
    require(digest(checkpoint['Review']['Path']) == checkpoint['Review']['Sha256'] == update['ReviewSha256'], 'Review changed')
    require(not read(config['NativeCoverage'])['Invalid'] and not read(config['NativeCoverage'])['Conflicts'], 'Invalid/conflicting ledger')
    require(digest(sink / 'reviewed63.json') == inventory['LedgerSha256'], 'Stale inventory ledger')
    require(owners['Inputs']['map']['Sha256'] == mapping['Sha256'] and owners['Inputs']['ledger']['Sha256'] == inventory['LedgerSha256'], 'Stale owner join')
    require(len(inventory['Modules']) == len(owners['Modules']) == config['ExpectedModules'], 'Physical scope differs')
    require(inventory['NativeCalls'] == owners['NativeCalls'] == 0, 'Expected cached joins')
    require(inventory['RemainingNativeCandidates'] == owners['RemainingNamingCandidates'] == config['ExpectedRemaining'], 'Candidate count differs')
    require(state['Maps']['63']['Sha256'] == mapping['Sha256'] and not state['Maps']['63']['AppliedToSource'], 'State differs')
    require(digest(state['Maps']['64']['Path']) == state['Maps']['64']['Sha256'], 'ETS6.4 map changed')
    for name, key in (('SdkWhitelist63', 'SdkNameWhitelistSha256'), ('ContractReferences63', 'ContractReferenceSha256')):
        binding = state['Compatibility'][name]
        require(digest(binding['Path']) == binding['Sha256'] == check[key], 'Compatibility binding differs')
    verify_corrections(aliases(checkpoint['PreviousMap']['Path']), aliases(mapping['Path']), prior, ledger, review, update['Changes'], config['ExpectedCorrections'])
    require(checkpoint['AcceptedDecisions'] == checkpoint['ExplicitAliasReplacements'] == len(config['ExpectedCorrections']), 'Checkpoint differs')
    for path in config['EvidenceFiles']:
        require(Path(path).is_file(), 'Missing evidence: ' + path)
    return checkpoint, state, inventory, owners


def record(config, config_path):
    checkpoint, state, inventory, owners = verify(config)
    sink, snapshot = Path(config['Sink']), Path(config['Snapshot'])
    proof_path = sink / config['ProofName']
    destinations = {key: sink / name for key, name in config['Copies'].items()}
    require(not snapshot.exists() and not proof_path.exists() and all(not p.exists() for p in destinations.values()), 'Choose fresh outputs')
    route = config['NextRoute']
    state['Maps']['63']['CountBasis'] = config['CountBasis']
    state['Naming']['Backlog'].update(Report=str(destinations['Inventory']), GeneratedOwnerReport=str(destinations['Owners']), OpenRoute=route)
    state['Readability']['PhysicalScope63']['NextBlock'] = route
    state['Naming']['NextItems'][0]['Detail'] = config['Detail']
    state['Naming']['NextItems'][3]['Detail'] = config['UnresolvedDetail']
    state['Deferred']['SourceExport']['Next'][0] = route
    encoded = encode(state) + '\n'
    require(len(encoded.splitlines()) < 200 and json.loads(encoded) == state, 'State is not bounded')
    progress = read(sink / 'progress.json')
    progress['GeneratedOwnerInventory63'] = dict(Path=str(destinations['Owners']), Sha256=digest(config['Owners']), MapSha256=inventory['MapSha256'], RemainingNamingCandidates=inventory['RemainingNativeCandidates'], NativeCalls=0, SourceMergeVerified=False)
    progress[config['ProgressKey']] = str(proof_path)
    pins = [Path(p) for p in config['EvidenceFiles']] + [Path(config_path), Path(__file__), Path(__file__).with_name('record_additive_naming_block.py'), Path(__file__).with_name('review_ledger.py'), Path(config['Checkpoint']), Path(checkpoint['Map']['Path']), Path(checkpoint['PreviousMap']['Path']), Path(checkpoint['Review']['Path']), Path(checkpoint['UpdateReport']), Path(checkpoint['CheckReport'])]
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
    proof = dict(Format=1, Kind='PhysicalMethodAliasCorrectionVerification', Map=checkpoint['Map'], Snapshot=str(snapshot),
                 Pins=[dict(Path=str(p), Sha256=digest(p)) for p in dict.fromkeys(pins)], Corrections=copy.deepcopy(config['ExpectedCorrections']),
                 EveryOtherAliasAndScopePreserved=True, EveryOtherLedgerDecisionPreserved=True, NativeSuccess=True,
                 WholeScope=dict(Modules=len(inventory['Modules']), Remaining=inventory['RemainingNativeCandidates'], InventoryNativeCalls=0, OwnerNativeCalls=0, InventorySeconds=inventory['ElapsedSeconds'], OwnerSeconds=owners['ElapsedSeconds']),
                 EvidenceFacts=copy.deepcopy(config['EvidenceFacts']), AppliedToSource=False, SourceMergingVerified=False,
                 NotProven=['No consolidated ETS export/build, metadata restoration or runtime compatibility is established.', 'Lexical counts do not prove whole-app readability.', 'ETS6.4 verification follows ETS6.3 completion.'])
    with proof_path.open('x', encoding='utf-8') as stream:
        json.dump(proof, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(Proof=str(proof_path), Corrections=len(proof['Corrections']), Remaining=inventory['RemainingNativeCandidates'], Pins=len(proof['Pins']))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    config = read(args.config)
    if args.verify_only:
        verify(config)
        print('Verified method corrections without writes')
    else:
        record(config, args.config)


if __name__ == '__main__':
    main()
