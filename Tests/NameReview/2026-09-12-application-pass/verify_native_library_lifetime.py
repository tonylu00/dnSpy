"""Reproduce review preparation and verify native map additions; read-only ETS inputs."""
import argparse
import collections
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET
from prepare_physical_review import prepare

def read(path): return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest().upper()

def verify(spec_path, review_path, checkpoint_path, update_path, check_path, evidence_path):
    spec, review, checkpoint, update, check, evidence = map(read,
        (spec_path, review_path, checkpoint_path, update_path, check_path, evidence_path))
    previous, current = checkpoint['PreviousMap'], checkpoint['Map']
    assert sha(previous['Path']) == previous['Sha256'] == update['BaseMapSha256']
    assert sha(current['Path']) == current['Sha256'] == check['BaseMapSha256']
    assert sha(review_path) == update['ReviewSha256'] == checkpoint['Review']['Sha256']
    assert update['Success'] and check['Success'] and not update['Errors'] and not check['Errors']
    assert all(c['Requested'] == c['Applied'] for c in update['Changes'])
    assert spec['ContractReferenceSha256'] == review['ContractReferenceSha256'] == update['ContractReferenceSha256'] == check['ContractReferenceSha256']
    reproduced = prepare(spec)
    for annotation in spec['ReviewAnnotations']:
        row = next(r for r in reproduced[annotation['Kind']] if r['Module'] == annotation['Module'] and r['Token'] == annotation['Token'])
        assert not set(annotation['Annotations']).intersection(row)
        row.update(annotation['Annotations'])
    text = json.dumps(reproduced, indent=2) + '\n'
    raw = pathlib.Path(review_path).read_bytes()
    # Account for the recorded host's native newline convention; content is exact.
    if b'\r\n' in raw: text = text.replace('\n', '\r\n')
    assert text.encode('utf-8') == raw
    old, new = map(lambda p: ET.parse(p).getroot(), (previous['Path'], current['Path']))
    assert old.attrib == new.attrib
    for module in old:
        assert module.attrib == next(m for m in new if m.get('Path') == module.get('Path')).attrib
    def index(root):
        result = {}
        for module in root:
            for row in module:
                key = (module.get('Path'), row.tag, row.get('Token'))
                assert key not in result
                scopes = {(s.tag, s.get('Sequence') or s.get('Index')): dict(s.attrib) for s in row}
                assert len(scopes) == len(row)
                result[key] = dict(Attributes=dict(row.attrib), Scopes=scopes)
        return result
    before, after = index(old), index(new)
    for key, value in before.items():
        assert key in after and value['Attributes'] == after[key]['Attributes']
        for scope, attributes in value['Scopes'].items(): assert after[key]['Scopes'][scope] == attributes
    additions = []
    for key, value in after.items():
        if key not in before and value['Attributes'].get('NewName'):
            additions.append(dict(Module=key[0], Kind=key[1], Token=key[2], Alias=value['Attributes']['NewName']))
        for scope, attributes in value['Scopes'].items():
            if key not in before or scope not in before[key]['Scopes']:
                additions.append(dict(Module=key[0], Kind=scope[0], Token=key[2], Position=scope[1], Alias=attributes['NewName']))
    repeated = [c for c in update['Changes'] if c['Before'] == c['Applied']]
    fresh = [c for c in update['Changes'] if c['Before'] != c['Applied']]
    assert len(additions) == len(fresh)
    assert collections.Counter(c['Kind'] for c in additions) == collections.Counter(c['Kind'] for c in fresh)
    assert len(additions) + len(repeated) == len(update['Changes'])
    reviewed_modules = {r['Module'] for k in ('Types', 'Methods', 'Fields') for r in review[k]}
    assert all(c['Module'] in reviewed_modules for c in additions)
    assert evidence['MapSha256'] == previous['Sha256']
    assert sha(evidence['Input']) == evidence['Sha256']
    assert sha(evidence['ContractReferenceManifest']['Path']) == evidence['ContractReferenceManifest']['Sha256'] == spec['ContractReferenceSha256']
    for source in evidence['Inventories']: assert sha(source['Path']) == source['Sha256']
    return dict(Format=1, Kind='NativeLibraryLifetimeVerification', MapSha256=current['Sha256'],
        NewAliases=len(additions), NewAliasCounts=dict(collections.Counter(c['Kind'] for c in additions)),
        NativeAcceptedRequests=len(update['Changes']), RepeatedExistingParameterRequests=sum(c['Kind'] == 'Parameter' for c in repeated),
        RepeatedExistingMethodRequests=sum(c['Kind'] == 'Method' for c in repeated),
        NativeRequestedAppliedExact=True, NativeErrors=0, ByteIdenticalReviewReproduction=True,
        PreviousAliasesAndScopesPreserved=True, PreviousPhysicalModuleBindingsPreserved=True,
        ExplicitUnresolvedDefinitions=sum(r['Unresolved'] for k in ('Types', 'Methods', 'Fields') for r in review[k]),
        ExplicitUnresolvedParameterScopes=sum(len(r.get('UnresolvedScopeEvidence', [])) for r in review['Methods']),
        GraphPhysicalInputsVerified=evidence['GraphPhysicalInputsVerified'],
        ReviewedDecisions=sum(len(review[k]) for k in ('Types', 'Methods', 'Fields')),
        ConsolidatedExportBuildRuntime='Pending'), additions

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('spec', 'review', 'checkpoint', 'update', 'check', 'evidence', 'output', 'difference'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result, additions = verify(args.spec, args.review, args.checkpoint, args.update, args.check, args.evidence)
    for path, value in ((args.output, result), (args.difference, dict(Format=1, Kind='PhysicalAliasDifference', Additions=additions))):
        with pathlib.Path(path).open('x', encoding='utf-8') as stream: stream.write(json.dumps(value, indent=2) + '\n')
    print('Verified', result['NewAliases'], 'new aliases;', result['NativeAcceptedRequests'], 'native requests; all previous bindings preserved')

if __name__ == '__main__': main()
