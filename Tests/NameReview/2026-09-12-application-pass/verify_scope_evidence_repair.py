"""Replay a review-only uncertainty repair and bind historical control snapshots.

Reads metadata evidence only. Writes a fresh verification report, never ETS files.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from record_additive_naming_block import digest, read, require
from review_ledger import refresh_scope_evidence, validate_scope_evidence_only


def verify(config):
    checkpoint = read(config['Checkpoint'])
    review = read(checkpoint['Review']['Path'])
    update = read(checkpoint['UpdateReport'])
    check = read(checkpoint['CheckReport'])
    previous, repaired = read(config['PreviousLedger']), read(config['RepairedLedger'])
    old_map, new_map = checkpoint['PreviousMap'], checkpoint['Map']
    require(digest(old_map['Path']) == old_map['Sha256'] == digest(new_map['Path']) == new_map['Sha256'], 'Map bytes changed')
    require(digest(checkpoint['Review']['Path']) == checkpoint['Review']['Sha256'] == update['ReviewSha256'], 'Review binding changed')
    require(update['Success'] and check['Success'] and not update['Errors'] and not check['Errors'], 'Native validation failed')
    require(update['BaseMapSha256'] == check['BaseMapSha256'] == new_map['Sha256'], 'Native map binding differs')
    validate_scope_evidence_only(review, update['Changes'], old_map['Sha256'], new_map['Sha256'])
    root = ET.parse(new_map['Path']).getroot()
    scopes = {(m.get('Path'), r.get('Token')):
              {(label, int(s.get(pos))): dict(s.attrib)
               for label, tag, pos in (('ParameterNames', 'Parameter', 'Sequence'), ('LocalNames', 'Local', 'Index'))
               for s in r.findall(tag)} for m in root.findall('Module') for r in m}
    decisions = {(r['Module'], r['Token']): r for r in review['Methods']}
    require(len(decisions) == len(review['Methods']) == checkpoint['ExplicitScopeEvidenceRefreshes'], 'Review count differs')
    expected = dict(previous)
    expected['Methods'] = [refresh_scope_evidence(r, decisions[(r['Module'], r['Token'])], scopes.get((r['Module'], r['Token']), {}))
                           if (r['Module'], r['Token']) in decisions else r for r in previous['Methods']]
    require(expected == repaired, 'Repair changed unrelated ledger data or lost evidence')
    paths = [config['Checkpoint'], config['PreviousLedger'], config['RepairedLedger'],
             old_map['Path'], new_map['Path'], checkpoint['Review']['Path'], checkpoint['UpdateReport'], checkpoint['CheckReport']]
    historical = []
    for proof_path in config['HistoricalProofs']:
        proof = read(proof_path)
        bindings = []
        for pin in proof['Pins']:
            path = Path(pin['Path'])
            if not path.is_file() or digest(path) != pin['Sha256']:
                require(path.suffix == '.py', 'Historical non-control evidence changed: ' + str(path))
                original = path
                path = Path(config['HistoricalControls']) / path.name
                require(path.is_file() and digest(path) == pin['Sha256'], 'Missing exact historical control: ' + str(original))
                bindings.append(dict(SourcePath=str(original), Path=str(path), Sha256=pin['Sha256']))
            paths.append(str(path))
        historical.append(dict(Path=proof_path, Sha256=digest(proof_path), PinsVerified=len(proof['Pins']), ControlBindings=bindings))
        paths.append(proof_path)
    paths.extend(config['EvidenceFiles'])
    return dict(Format=1, Kind='ScopeEvidenceRepairVerification',
                Methods=len(decisions), Annotations=sum(len(v) for r in decisions.values() for v in r['UnresolvedScopeEvidence'].values()),
                MapBytesUnchanged=True, EveryAliasPreserved=True, UnrelatedLedgerDataPreserved=True,
                HistoricalProofs=historical, Pins=[dict(Path=p, Sha256=digest(p)) for p in dict.fromkeys(paths)],
                NotProven=['No new ETS source export, build or runtime verification.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = verify(read(args.config))
    result['Configuration'] = dict(Path=args.config, Sha256=digest(args.config))
    with Path(args.output).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(Methods=result['Methods'], Annotations=result['Annotations'], HistoricalPins=sum(r['PinsVerified'] for r in result['HistoricalProofs']))))
