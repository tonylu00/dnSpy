"""Join native whole-scope AST observations to pinned structural review candidates.

Read-only discovery: no aliases, source/binary/map/ledger writes or retirement.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def token(value):
    return int(value, 16) if isinstance(value, str) else value


def path_key(value):
    return str(Path(value).resolve()).replace('\\', '/').casefold()


def source_index(report):
    states = collections.defaultdict(list)
    anonymous = collections.defaultdict(list)
    fields = collections.defaultdict(list)
    for root in report['Roots']:
        for witness in root['BodyWitnesses']:
            if witness['Kind'] == 'AnonymousMethod':
                anonymous[witness['ImplementationToken']].append(witness)
            elif witness['Kind'] in ('AsyncMethod', 'IteratorMethod', 'AsyncIteratorMethod'):
                states[witness['ImplementationTypeToken']].append(witness)
        for binding in root['FieldBindings']:
            fields[binding['FieldToken']].append(binding)
    return {'Definitions': {d['Token']: d for d in report['Definitions']},
            'Declared': set(t for r in report['Roots'] for t in r['DeclarationTokens']),
            'Referenced': set(t for r in report['Roots'] for t in r['ReferenceTokens']),
            'PrintedCoverage': all(r.get('PrintedReferenceCoverage', False) for r in report['Roots']),
            'PrintedReferenced': set(t for r in report['Roots'] for t in r.get('PrintedReferenceTokens', [])),
            'States': states, 'Anonymous': anonymous, 'Fields': fields}


def join_candidate(candidate, index, cross_references, cross_printed=None):
    ident = token(candidate['Token'])
    definitions = index['Definitions']
    require(ident in definitions and definitions[ident]['FullName'] == candidate['Signature']
            and definitions[ident]['OriginalName'] == candidate['OriginalName'], 'Candidate definition mismatch')
    evidence = candidate.get('Evidence') or {}
    type_token = ident if candidate['Kind'] == 'Types' else token(evidence.get('DeclaringType', {}).get('Token', 0))
    declared, referenced = index['Declared'], index['Referenced']
    bindings = index['Fields'].get(ident, [])
    state_owners = set(token(o['Definition']['Token']) for o in evidence.get('StateMachineOwners', []))
    delegate_owners = set(token(o['Definition']['Token']) for o in evidence.get('DelegateOwners', []))
    state = [w for w in index['States'].get(type_token, []) if w['OwnerToken'] in state_owners]
    anonymous = index['Anonymous'].get(ident, [])
    facts = []
    for present, label in ((ident in declared, 'SourceDeclarationRetained'), (ident in referenced, 'LocalSourceReferenceRetained'),
                           (ident in cross_references, 'CrossModuleSourceReferenceRetained'), (bool(bindings), 'HoistedFieldProjected'),
                           (bool(state), 'StateMachineBodyReconstructed'), (bool(anonymous), 'AnonymousBodyReconstructed')):
        if present:
            facts.append(label)
    if index['PrintedCoverage'] and ident in index['PrintedReferenced']:
        facts.append('LocalPrintedSourceReferenceRetained')
    if cross_printed is not None and cross_printed.get(ident, 0) > 0:
        facts.append('CrossModulePrintedSourceReferenceRetained')
    if not facts:
        facts.append('NoPositiveSourceObservation')
    return {'Facts': facts, 'StateMachineBodyWitnesses': state, 'AnonymousBodyWitnesses': anonymous,
            'MatchedDelegateOwners': sorted(set(w['OwnerToken'] for w in anonymous) & delegate_owners),
            'FieldBindings': bindings, 'CrossModuleUseRecords': cross_references.get(ident, 0),
            'PrintedReferenceCoverage': index['PrintedCoverage'],
            'CrossModulePrintedReferenceCoverage': cross_printed is not None,
            'CrossModulePrintedUseRecords': None if cross_printed is None else cross_printed.get(ident, 0),
            'ReferenceTokenSemantics': 'Conservative AST member annotations can include declaration identifiers and inlined implementation/debug annotations; not a count or proof of printed member accesses.',
            'Limits': 'Observed source facts only. Absence does not prove merging, semantic names or restoration contracts. No candidate retirement.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('owners', 'source-audit', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), 'Choose a fresh output directory')
    inputs = {n: {'Path': str(p.resolve()), 'Sha256': digest(p)} for n, p in
              (('owners', args.owners), ('sourceAudit', args.source_audit), ('joiner', Path(__file__)))}
    owners, audit = read(args.owners), read(args.source_audit)
    require(owners['Kind'] == 'PhysicalGeneratedOwnerInventory' and audit['Kind'] == 'PhysicalScopeFinalAstCoverageAudit', 'Wrong native input kinds')
    require(owners['Inputs']['map']['Sha256'] == audit['SourceMapSha256'], 'Different mapping snapshots')
    worklist = Path(owners['Worklist'])
    require(digest(worklist) == owners['WorklistSha256'], 'Structural worklist changed')
    inputs['worklist'] = {'Path': str(worklist), 'Sha256': digest(worklist)}
    root = Path(owners['Root']).resolve()
    catalog = {path_key(root / m['Module']): m for m in owners['Modules']}
    modules = {path_key(m['Input']): m for m in audit['Modules']}
    require(len(modules) == audit['TotalModules'] and set(modules) == set(catalog), 'Physical source/structural scope mismatch')
    candidates = collections.defaultdict(list)
    seen = set()
    with worklist.open(encoding='utf-8-sig') as stream:
        for line in stream:
            row = json.loads(line)
            key = path_key(root / row['Module'])
            identity = key, token(row['Token'])
            require(key in modules and identity not in seen, 'Foreign/duplicate candidate')
            require(all(row[n] == modules[key][n] for n in ('Mvid', 'Sha256', 'Identity')), 'Candidate physical mismatch')
            seen.add(identity); candidates[key].append(row)
    require(len(seen) == owners['Candidates'], 'Structural candidate count mismatch')
    cross = collections.defaultdict(dict)
    for reference in audit['CrossModuleFirstPartyDefinitions']:
        key = path_key(reference['Module'])
        require(key in modules, 'Foreign first-party reference target')
        cross[key][reference['Token']] = reference['UseRecords']
    printed_coverage = audit.get('PrintedReferenceCoverage', False)
    cross_printed = collections.defaultdict(dict)
    if printed_coverage:
        require(all(m.get('PrintedReferenceCoverage', False) for m in modules.values()), 'Incomplete audited writer coverage')
        for reference in audit['CrossModuleFirstPartyPrintedDefinitions']:
            key = path_key(reference['Module'])
            require(key in modules and reference['UseRecords'] > 0, 'Invalid first-party printed reference target/count')
            require(reference['Token'] not in cross_printed[key], 'Duplicate first-party printed reference')
            cross_printed[key][reference['Token']] = reference['UseRecords']
    args.output.mkdir(parents=True)
    output = args.output / 'candidate-source-observations.jsonl'
    counts = collections.Counter(); categories = collections.defaultdict(collections.Counter); module_counts = []
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        for key, module in modules.items():
            require(digest(module['Input']) == module['Sha256'] and digest(module['Report']) == module['ReportSha256'], 'Native physical input/report changed')
            report = read(module['Report'])
            require(report['InputSha256'] == module['Sha256'] and report['Mvid'] == module['Mvid'] and report['MapSha256'] == audit['SourceMapSha256'], 'Native module report mismatch')
            local = collections.Counter()
            index = source_index(report)
            if printed_coverage:
                require(index['PrintedCoverage'] and index['PrintedReferenced'] == set(module['LocalPrintedReferenceTokens']), 'Audited printed module classification mismatch')
            for candidate in candidates[key]:
                observation = join_candidate(candidate, index, cross[key], cross_printed[key] if printed_coverage else None)
                for fact in observation['Facts']:
                    counts[fact] += 1; local[fact] += 1; categories[candidate['Category']][fact] += 1
                row = dict(candidate, SourceObservations=observation,
                           SourceReport={'Path': module['Report'], 'Sha256': module['ReportSha256']})
                stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            module_counts.append({'Module': catalog[key]['Module'], 'Candidates': len(candidates[key]), 'Facts': dict(local)})
            require(digest(module['Report']) == module['ReportSha256'], 'Native report changed during join')
            del index, report
    for pin in inputs.values():
        require(digest(pin['Path']) == pin['Sha256'], 'Join input changed')
    summary = {'Format': 1, 'Kind': 'PhysicalGeneratedSourceCandidateObservations', 'Inputs': inputs,
               'Modules': module_counts, 'Candidates': len(seen), 'OverlappingSourceFacts': dict(counts),
               'WholeScopePrintedReferenceCoverage': printed_coverage,
               'ByStructuralCategory': {k: dict(v) for k, v in categories.items()}, 'Worklist': str(output.resolve()),
               'WorklistSha256': digest(output), 'CandidatesRetired': 0,
               'Limits': 'Whole supplied physical scope source observations joined to structural candidates. Facts overlap. Unknown names, references, owner chains and restoration/runtime contracts require review; absence alone never retires a candidate.'}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'Candidates': len(seen), 'SourceFacts': dict(counts), 'CandidatesRetired': 0}))


if __name__ == '__main__':
    main()
