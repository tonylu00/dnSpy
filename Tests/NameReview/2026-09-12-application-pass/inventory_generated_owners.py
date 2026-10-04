"""Orchestrate native physical-owner inspection and join an immutable review inventory.

No naming decisions, candidate retirement, source/binary/map/ledger mutations.
The native tool supplies all structural evidence; Python verifies and joins it.
"""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest().upper()


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(',', ':'))
        stream.write('\n')


def physical_key(module):
    return module.replace('\\', '/').casefold()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scope', 'cli', 'inventory', 'map', 'ledger', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--workers', type=int, default=2, choices=(1, 2))
    parser.add_argument('--reuse-inventory', type=Path, help='Reuse native reports only after exact physical/tool/dependency hash checks')
    args = parser.parse_args()
    bindings = {name: {'Path': str(getattr(args, name).resolve()), 'Sha256': digest(getattr(args, name))}
                for name in ('scope', 'cli', 'inventory', 'map', 'ledger')}
    candidates_path = args.inventory.parent / 'remaining-candidates.json'
    bindings['candidates'] = {'Path': str(candidates_path.resolve()), 'Sha256': digest(candidates_path)}
    bindings['orchestrator'] = {'Path': str(Path(__file__).resolve()), 'Sha256': digest(__file__)}
    for dependency in ('dnlib.dll', 'GeneratedOwnerInspection.deps.json', 'GeneratedOwnerInspection.runtimeconfig.json'):
        path = args.cli.parent / dependency
        bindings[dependency] = {'Path': str(path.resolve()), 'Sha256': digest(path)}
    scope, inventory = read(args.scope), read(args.inventory)
    require(scope['Kind'] == 'PhysicalApplicationScope' and inventory['Kind'] == 'PhysicalApplicationInventory', 'Wrong inventory format')
    root = Path(scope['Root']).resolve()
    require(Path(inventory['Root']).resolve() == root, 'Root mismatch')
    for name in ('scope', 'map', 'ledger'):
        require(inventory[name.title() + 'Sha256'] == bindings[name]['Sha256'], 'Stale ' + name + ' binding')
    physical, catalog = {}, {physical_key(m['Path']): m for m in inventory['Modules']}
    for module in scope['Modules']:
        key = physical_key(module['Path'])
        path = (root / module['Path']).resolve()
        require(path.is_relative_to(root) and key not in physical, 'Invalid/duplicate physical path')
        require(path == Path(module['Input']).resolve() and digest(path) == module['Sha256'], 'Physical input changed: ' + key)
        require(key in catalog and all(catalog[key][k] == module[k] for k in ('Sha256', 'Mvid', 'GraphId')), 'Inventory module mismatch')
        physical[key] = module
    require(set(physical) == set(catalog), 'Scope/catalog mismatch')
    remaining = read(candidates_path)
    require(len(remaining) == inventory['RemainingNativeCandidates'], 'Candidate count mismatch')
    grouped, seen = collections.defaultdict(list), set()
    for candidate in remaining:
        key = physical_key(candidate['Module'])
        identity = (key, int(candidate['Token'], 16))
        require(key in physical and identity not in seen, 'Foreign/duplicate candidate')
        require(candidate['NeedsReadableName'] and all(candidate[k] == physical[key][k] for k in ('Sha256', 'Mvid')), 'Stale candidate')
        seen.add(identity)
        grouped[key].append(candidate)
    reports = {}
    report_hashes = {}
    if args.reuse_inventory:
        bindings['reuse'] = {'Path': str(args.reuse_inventory.resolve()), 'Sha256': digest(args.reuse_inventory)}
        reuse = read(args.reuse_inventory)
        require(reuse['Kind'] == 'PhysicalGeneratedOwnerInventory' and Path(reuse['Root']).resolve() == root, 'Wrong reuse inventory')
        for name in ('scope', 'cli', 'dnlib.dll', 'GeneratedOwnerInspection.deps.json', 'GeneratedOwnerInspection.runtimeconfig.json'):
            require(reuse['Inputs'][name]['Sha256'] == bindings[name]['Sha256'], 'Stale reuse ' + name)
        reused_modules = {physical_key(m['Module']): m for m in reuse['Modules']}
        require(set(reused_modules) == set(physical), 'Reuse scope mismatch')
        for key, module in physical.items():
            old = reused_modules[key]
            require(all(old[k] == module[k] for k in ('Sha256', 'Mvid', 'GraphId')), 'Stale reused physical module')
            path = Path(old['NativeReport'])
            require(digest(path) == old['NativeReportSha256'], 'Reused native report changed')
            reports[key] = path
            report_hashes[key] = old['NativeReportSha256']
    args.output.mkdir(parents=True, exist_ok=False)
    native_directory = args.output / 'native'
    native_directory.mkdir()
    try:
        import psutil
    except ImportError:
        psutil = None
    started = time.perf_counter()
    environment = dict(os.environ, DOTNET_PROCESSOR_COUNT='2')
    jobs = [(i, key, module) for i, (key, module) in enumerate(physical.items()) if key not in reports]

    def inspect(job):
        i, key, module = job
        report = native_directory / (str(i).zfill(3) + '.json')
        with (native_directory / (str(i).zfill(3) + '.log')).open('x', encoding='utf-8') as log:
            subprocess.run(['dotnet', str(args.cli), module['Input'], str(report)], env=environment,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        return key, report

    peak_children = 0
    peak_orchestrator = psutil.Process().memory_info().rss if psutil else 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(inspect, job) for job in jobs}
        while pending:
            done, pending = concurrent.futures.wait(pending, timeout=0.02, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                key, report = future.result()
                reports[key] = report
                report_hashes[key] = digest(report)
            if psutil:
                process = psutil.Process()
                peak_orchestrator = max(peak_orchestrator, process.memory_info().rss)
                total = 0
                for child in process.children(recursive=True):
                    try:
                        total += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                peak_children = max(peak_children, total)
    native_elapsed = round(time.perf_counter() - started, 3)
    scope_counts = collections.Counter()
    categories = collections.Counter()
    facts = collections.Counter()
    multiple_owners = collections.Counter()
    ambiguities = collections.Counter()
    kinds = collections.defaultdict(collections.Counter)
    module_counts = []
    worklist_path = args.output / 'candidate-owners.jsonl'
    with worklist_path.open('x', encoding='utf-8', newline='\n') as worklist:
        for key, module in physical.items():
            report = read(reports[key])
            if psutil:
                peak_orchestrator = max(peak_orchestrator, psutil.Process().memory_info().rss)
            require(report['Kind'] == 'PhysicalGeneratedOwnerEvidence', 'Wrong native report')
            require(Path(report['Input']).resolve() == Path(module['Input']).resolve(), 'Native input mismatch')
            require(report['Sha256'] == module['Sha256'] and report['Mvid'].casefold() == module['Mvid'].casefold(), 'Native identity mismatch')
            for kind in ('Types', 'Methods', 'Fields'):
                require(report['Scope'][kind] == catalog[key]['Counts'][kind].get('Definitions', 0), 'Definition count mismatch: ' + key + '/' + kind)
            scope_counts.update(report['Scope'])
            index = {}
            for kind in ('Types', 'Methods', 'Fields'):
                for entry in report[kind]:
                    token = int(entry['Definition']['Token'], 16)
                    require(token not in index, 'Duplicate native definition')
                    index[token] = (kind, entry)
            for entry in report['AmbiguousEvidence']:
                ambiguities[entry['Evidence']] += 1
            local = collections.Counter()
            for candidate in grouped[key]:
                result = index.get(int(candidate['Token'], 16))
                evidence = result[1] if result else None
                if evidence:
                    require(result[0] == candidate['Kind'] and evidence['Definition']['Signature'] == candidate['Signature'], 'Signature mismatch')
                require(candidate['Identity'] == report['Identity'], 'Candidate assembly identity mismatch')
                labels = []
                owners = []
                owner_counts = {}
                if evidence:
                    for label in ('DirectPropertyStorageOwners', 'StateMachineOwners', 'AccessorOwners', 'DelegateOwners'):
                        if evidence.get(label):
                            labels.append(label)
                            owners.extend(evidence[label])
                            owner_counts[label] = len({(o['Definition']['Kind'], o['Definition']['Token'], o['Definition']['Signature'])
                                                       for o in evidence[label]})
                            if owner_counts[label] > 1:
                                multiple_owners[label] += 1
                    for label in ('CompilerGenerated', 'GeneratedContainer', 'GeneratedAncestor', 'UntrustedGeneratedAttribute'):
                        if evidence.get(label):
                            labels.append(label)
                    if evidence.get('AccessorFieldUses'):
                        labels.append('AccessorFieldUses')
                category = next((label for label in ('DirectPropertyStorageOwners', 'StateMachineOwners', 'AccessorOwners', 'DelegateOwners',
                                'GeneratedContainer', 'GeneratedAncestor', 'CompilerGenerated', 'UntrustedGeneratedAttribute') if label in labels), 'NoStructuralOwnerEvidence')
                unique_owners = {(o['Definition']['Kind'], o['Definition']['Token'], o['Definition']['Signature']) for o in owners}
                categories[category] += 1
                local[category] += 1
                kinds[candidate['Kind']][category] += 1
                facts.update(labels)
                if len(unique_owners) > 1:
                    facts['MultipleDistinctOwnerDefinitions'] += 1
                row = {'Module': module['Path'], 'Identity': report['Identity'], 'Mvid': report['Mvid'], 'Sha256': report['Sha256'],
                       'Kind': candidate['Kind'], 'Token': candidate['Token'], 'Signature': candidate['Signature'],
                       'OriginalName': candidate['OriginalName'], 'CandidateReason': candidate['Reason'],
                       'Category': category, 'Facts': labels, 'DistinctOwnerDefinitions': len(unique_owners),
                       'DistinctOwnersByEvidence': owner_counts, 'Evidence': evidence}
                worklist.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            module_counts.append({'Module': module['Path'], 'GraphId': module['GraphId'], 'Sha256': module['Sha256'], 'Mvid': module['Mvid'],
                                  'NativeReport': str(reports[key].resolve()), 'NativeReportSha256': report_hashes[key],
                                  'Scope': report['Scope'], 'Candidates': sum(local.values()), 'Categories': dict(local),
                                  'AmbiguousEdges': len(report['AmbiguousEvidence'])})
            if psutil:
                peak_orchestrator = max(peak_orchestrator, psutil.Process().memory_info().rss)
            del report, index
    require(sum(categories.values()) == len(remaining), 'Join lost candidates')
    for binding in bindings.values():
        require(digest(binding['Path']) == binding['Sha256'], 'Inspection input changed')
    for module in physical.values():
        require(digest(module['Input']) == module['Sha256'], 'Physical input changed during inspection')
    for key, report in reports.items():
        require(digest(report) == report_hashes[key], 'Native report changed during join')
    summary = {'Format': 1, 'Kind': 'PhysicalGeneratedOwnerInventory', 'Root': str(root), 'Inputs': bindings, 'Modules': module_counts,
               'Workers': args.workers, 'NativeCalls': len(jobs), 'ReusedNativeReports': len(physical) - len(jobs), 'NativeElapsedSeconds': native_elapsed,
               'ElapsedSeconds': round(time.perf_counter() - started, 3),
               'ObservedPeakChildRssBytes': peak_children if psutil else None,
               'ObservedPeakOrchestratorRssBytes': peak_orchestrator if psutil else None,
               'Sampling': 'Child RSS sampled every 20 ms while native jobs run; orchestrator sampled there and after each module parse/join. Observed peaks may miss brief allocations.',
               'ScopeCounts': dict(scope_counts), 'Candidates': len(remaining), 'Categories': dict(categories),
               'ByKind': {kind: dict(counts) for kind, counts in kinds.items()}, 'OverlappingFacts': dict(facts),
               'CandidatesWithMultipleOwnersWithinEvidence': dict(multiple_owners), 'AmbiguousEdges': dict(ambiguities),
               'Worklist': str(worklist_path.resolve()), 'WorklistSha256': digest(worklist_path), 'RemainingNamingCandidates': len(remaining),
               'Limits': 'Structural evidence only. No candidates retired, aliases assigned, definitions merged, source exported or runtime compatibility established. No reflection/external-call absence proof. Categories are exclusive for counting; Facts retain overlaps. Multiple metadata owners remain explicit. Single RSS/time measurement is not a performance guarantee.'}
    write(args.output / 'summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('NativeCalls', 'NativeElapsedSeconds', 'ElapsedSeconds', 'ObservedPeakChildRssBytes',
                                           'ScopeCounts', 'Candidates', 'Categories', 'OverlappingFacts', 'AmbiguousEdges')}))


if __name__ == '__main__':
    main()
