"""Validate native pinned-CLR proofs before recording new contract preservation.

Only evidence/review JSON is processed. No ETS map, source or binary mutation.
"""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from sdk_proposal_retirement import key

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def load_framework_contract_evidence(map_path, path, expected_hash, reference_hash):
    assert digest(path) == expected_hash, 'Stale native framework proof'
    proof = read(path)
    assert proof['Format'] == 1 and proof['Kind'] == 'PhysicalFrameworkContractEvidence'
    root = Path(ET.parse(map_path).getroot().get('InputDirectory')).resolve()
    assert Path(proof['TargetRoot']).resolve() == root
    assert proof['ContractReferenceSha256'] == reference_hash == digest(proof['ContractReferences'])
    assert proof['SeedsSha256'] == digest(proof['Seeds'])
    seeds = read(proof['Seeds'])
    assert seeds['Format'] == 1 and Path(seeds['TargetRoot']).resolve() == root and seeds['ContractReferenceSha256'] == reference_hash
    expected = {}
    for seed in seeds['Methods']:
        identity = key(seed['Module'], seed['Token'])
        assert identity not in expected, 'Repeated physical seed'
        expected[identity] = seed
    inputs, references = {}, {}
    for binding in proof['Inputs']:
        physical = Path(binding['Path']).resolve()
        assert physical.is_relative_to(root) and physical != root
        relative = physical.relative_to(root).as_posix().casefold()
        assert relative not in inputs and digest(physical) == binding['Sha256'], 'Stale/duplicate physical input'
        inputs[relative] = binding
    manifest = read(proof['ContractReferences'])
    declared = {}
    for entry in manifest['Assemblies']:
        physical = Path(entry['Path'])
        if not physical.is_absolute(): physical = Path(proof['ContractReferences']).parent / physical
        physical = physical.resolve()
        assert entry['Identity'] not in declared, 'Ambiguous reference identity'
        declared[entry['Identity']] = dict(Path=str(physical), Identity=entry['Identity'], Mvid=entry['Mvid'], Sha256=entry['Sha256'].upper())
    for binding in proof['References']:
        assert binding['Identity'] not in references and binding['Identity'] in declared
        original = declared[binding['Identity']]
        assert Path(binding['Path']).resolve() == Path(original['Path'])
        assert all(binding[k] == original[k] for k in ('Identity', 'Mvid', 'Sha256')) and digest(binding['Path']) == binding['Sha256']
        references[binding['Identity']] = binding
    assert set(references) == set(declared)
    roles = {
        'System.Runtime.CompilerServices.IAsyncStateMachine': {'MoveNext', 'SetStateMachine'},
        'System.IDisposable': {'Dispose'},
        'System.Collections.IEnumerator': {'MoveNext', 'Reset', 'get_Current'},
        'System.Collections.IEnumerable': {'GetEnumerator'},
        'System.Collections.Generic.IEnumerator`1': {'get_Current'},
        'System.Collections.Generic.IEnumerable`1': {'GetEnumerator'},
    }
    results = {}
    for row in proof['Definitions']:
        definition = row['Definition']; identity = key(definition['Module'], definition['Token'])
        assert identity not in results and identity in expected
        original = expected[identity]
        assert all(definition[k] == original[k] for k in ('Module', 'Identity', 'Mvid', 'Sha256', 'Type', 'Token', 'Signature', 'OriginalName'))
        physical = root / definition['Module'].replace('\\', '/')
        assert physical.resolve().is_relative_to(root)
        binding = inputs[identity[0]]
        assert Path(binding['Path']).resolve() == physical.resolve() and all(binding[k] == definition[k] for k in ('Identity', 'Mvid', 'Sha256'))
        assert row['Status'] == 'ProtectedExplicitFrameworkContract' and row['Blocker'] is None
        declaration = row['Declaration']
        assert declaration['BodySignatureValidated'] is True and declaration['OriginalName'] in roles.get(declaration['Type'], set())
        assert declaration['Reference'] == references[declaration['Reference']['Identity']]
        assert int(declaration['MethodToken'], 16) >> 24 == 6 and int(declaration['TypeToken'], 16) >> 24 == 2
        assert declaration['RawAssemblyIdentity'] in references and declaration['Signature'] and declaration['RawSignature'] and declaration['InstantiatedSignature']
        results[identity] = row
    assert set(results) == set(expected), 'Proof does not cover its exact seed set'
    return results

def preserve_framework_contract_method(row, mapped_entry, proof):
    assert row.get('PreserveFrameworkContractMethod') is True and mapped_entry is None, 'Preservation requires an unmapped exact new definition'
    assert row['ReviewDisposition'] == 'preserve' and not row.get('NewName') and not row.get('Unresolved') and not row.get('NeedsReadableName')
    assert not any(s.get('NewName') for label in ('ParameterNames', 'LocalNames') for s in row.get(label, [])), 'Contract preservation cannot carry aliases'
    definition = proof['Definition']
    assert all(row[k] == definition[k] for k in ('Module', 'Identity', 'Mvid', 'Sha256', 'Type', 'Token', 'Signature', 'OriginalName'))
    annotation = row['PreservedExternalFrameworkContract']
    assert annotation['Declaration'] == proof['Declaration'] and annotation['GeneratedSourceMerging'].startswith('Unproven')
    assert row.get('Reason'), 'Preservation needs behavioral/contract rationale'
    recorded = copy.deepcopy(row)
    recorded.pop('PreserveFrameworkContractMethod')
    return recorded

def attach_framework_proofs(review, binding, proofs):
    assert review['Format'] == 1 and not review['Types'] and not review['Fields']
    assert digest(binding['Cli']) == binding['CliSha256']
    assert {key(r['Module'], r['Token']) for r in review['Methods']} == set(proofs)
    result = copy.deepcopy(review)
    result['NativeFrameworkContractEvidence'] = copy.deepcopy(binding)
    for row in result['Methods']:
        proof = proofs[key(row['Module'], row['Token'])]
        row['PreservedExternalFrameworkContract'] = dict(ProofSha256=binding['Sha256'], Declaration=copy.deepcopy(proof['Declaration']),
            GeneratedSourceMerging='Unproven; not a preservation basis or completion claim.')
        row['PreserveFrameworkContractMethod'] = True
        preserve_framework_contract_method(row, None, proof)
    return result

def main():
    import argparse
    from prepare_physical_review import prepare
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('map', 'spec', 'evidence', 'cli', 'output'): parser.add_argument('--'+name, required=True)
    parser.add_argument('--tool-commit')
    args = parser.parse_args()
    spec = read(args.spec)
    binding = dict(Path=str(Path(args.evidence).resolve()), Sha256=digest(args.evidence), Cli=str(Path(args.cli).resolve()), CliSha256=digest(args.cli))
    if args.tool_commit: binding['ToolCommit'] = args.tool_commit
    proofs = load_framework_contract_evidence(args.map, args.evidence, binding['Sha256'], spec['ContractReferenceSha256'])
    result = attach_framework_proofs(prepare(spec), binding, proofs)
    with Path(args.output).open('x', encoding='utf-8') as stream: stream.write(json.dumps(result, indent=2)+'\n')
    print('Prepared', len(result['Methods']), 'exact framework preservation decisions')

if __name__ == '__main__': main()
