"""Review diagnostic buffering, decorators, source traversal and exception data.

Usage: python exception_diagnostics.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Mapping/evidence only. No ETS source replacement, export, build or execution.
"""
from pathlib import Path
import json
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    batches = {}
    for version, base, prior, inventory in [
        ('63', 194, 'diagnostic63-wave194.cumulative.json', 'falcon63-native-wave176-methods.json'),
        ('64', 27, 'statistics64-wave27.cumulative.json', 'falcon64-native-wave13-methods.json')]:
        b = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)
        batches[version] = b
        old = version == '63'
        path = root / ('exception63-wave195-inspection.json' if old else 'exception64-wave195-full-inspection.json')
        inspection = b.read(path.name)
        assert inspection['Sha256'] == b.module['Sha256'] and inspection['Mvid'] == b.module['Mvid']
        bodies = {int(m['Token'], 16) & 0xFFFFFF: m for m in inspection['Methods']}
        b.bind_usage_sources(path, {0x06002A25: 0x06002A1E, 0x04002B91: 0x06002A1E} if old else {
            0x06002F17: 0x06002F0F, 0x06002F1B: 0x06002F0F,
            0x04001F61: 0x06002F0F, 0x04001F62: 0x06002F0F, 0x04001F64: 0x06002F0F})
        il = {'Path': str(path), 'Sha256': sha(path)}

        def method(token, name, reason, parameters=None, locals_=None, evidence=(), contract=None):
            key = f'0x{0x06000000 + token:08X}'
            body = bodies[token]
            assert body['Signature'] == b.entries['Methods'][key]['Signature']
            for slot in locals_ or {}:
                expected = next(l['ExpectedType'] for l in b.entries['Methods'][key]['LocalNames'] if l['Index'] == slot)
                assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
            b.add('Methods', 0x06000000 + token, name, reason, parameters, locals_,
                  evidence=[0x06000000 + t for t in evidence], contract=contract)
            assert not b.pending, b.pending
            b.decisions[-1]['IL'] = {**il, 'Token': key, 'Slots': locals_ or {}}

        def symbol(kind, token, name, reason, evidence):
            key = f'0x{token:08X}'
            previous = b.aliases.get((b.relative, key))
            if previous is not None and previous.get('NewName') == name:
                return
            if kind == 'Fields':
                uses = [json.loads(r[0]) for r in b.db.execute('SELECT data FROM edges WHERE target=?', (b.module_id + ':' + key,))]
                found = []
                for use in uses:
                    if not use['From'].startswith(b.module_id + ':'):
                        continue
                    owner = int(use['From'].split(':')[1], 16) & 0xFFFFFF
                    if owner not in evidence:
                        continue
                    instruction = next(i for i in bodies[owner]['Instructions'] if i['Offset'] == use['Offset'])
                    assert instruction['OpCode'] == use['Operation'] and instruction['Operand']['Text'] == use['Target']['Signature']
                    assert Path(use['Target']['PhysicalModule']).resolve() == Path(b.module['Input']).resolve()
                    found.append(use)
                assert found, ('No inspected field use', key)
            b.add(kind, token, name, reason, evidence=[0x06000000 + t for t in evidence])
            assert not b.pending, b.pending
            b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x{0x06000000 + t:08X}' for t in evidence]}

        # Queue leaves precede the event collector and its wrapper families.
        ctor, enqueue, to_array = (0x183D, 0x183E, 0x183F) if old else (0x2B1B, 0x2B1C, 0x2B1D)
        method(ctor, None, 'Stores the capacity without validation and initializes a concurrent queue.', ('capacity',))
        method(enqueue, 'Enqueue', 'While Count is at least capacity, attempts to dequeue and disposes a removed IDisposable item, then enqueues the new message. TryDequeue success is not tested; eviction and enqueue are not one atomic capacity check. Nonpositive capacity is not guarded.',
               ('message',), {0: 'removedItem', 1: 'disposableItem'})
        method(to_array, 'ToArray', 'Returns the underlying ConcurrentQueue.ToArray snapshot.', ())
        for token, name in ([(0x13C2, 'queue'), (0x13C3, 'capacity')] if old else [(0x1C37, 'queue'), (0x1C38, 'capacity')]):
            symbol('Fields', 0x04000000 + token, name, 'Queue storage or configured eviction threshold used by Enqueue.', (ctor, enqueue, to_array))
        method(0x1A0C if old else 0x2FA5, None, 'Creates the event collector buffer with the supplied capacity; the default is 100.', ('capacity',))
        symbol('Fields', 0x040015F4 if old else 0x04001FA2, 'events', 'Bounded concurrent buffer holding the diagnostic events.',
               (0x1A0C, 0x1A0D, 0x1A0E) if old else (0x2FA5, 0x2FA6, 0x2FA7))

        for token, parameters in ([(0x1A13, ('innerSink', 'instancePrefix')), (0x1A16, ('innerSink', 'source'))] if old else
                                  [(0x2FB7, ('innerSink', 'instancePrefix')), (0x2FBD, ('innerSink', 'source'))]):
            method(token, None, 'Retains the inner event sink and the instance prefix or source override.', parameters)
        if old:
            families = b.read('explicit63-wave194-families.json')
            assert families['ContractReferenceSha256'] == b.delta['ContractReferenceSha256']
            for seed, members, name, reasons, parameters in [
                (0x1A0F, {0x1A0D, 0x1A0F, 0x1A14, 0x1A17}, 'Add', {
                    0x1A0D: 'Enqueues the diagnostic event in the collector buffer.',
                    0x1A0F: 'Event-sink contract for receiving a diagnostic event.',
                    0x1A14: 'Mutates the same event by prepending instancePrefix to Instance, then forwards it to innerSink.Add. Does not clone or filter a null event.',
                    0x1A17: 'Mutates the same event by replacing Source, then forwards it to innerSink.Add. Does not clone or filter a null event.'}, ('diagEvent',)),
                (0x1A10, {0x1A0E, 0x1A10, 0x1A15, 0x1A18}, 'ToArray', {
                    0x1A0E: 'Returns the collector buffer snapshot.', 0x1A10: 'Event-sink contract for retrieving its recorded event array.',
                    0x1A15: 'Returns innerSink.ToArray without another prefix transformation.',
                    0x1A18: 'Returns innerSink.ToArray without another source transformation.'}, ())]:
                key = f'0x{0x06000000 + seed:08X}'
                fid = next(r['ContractFamily'] for r in families['Methods'] if r['Module'] == b.relative and r['Token'] == key)
                rows = [r for r in families['Methods'] if r['ContractFamily'] == fid]
                assert {int(r['Token'], 16) & 0xFFFFFF for r in rows} == members and all(r['Module'] == b.relative for r in rows)
                for row in rows:
                    token = int(row['Token'], 16) & 0xFFFFFF
                    method(token, name, reasons[token], parameters, contract=row)
            for token, name, proof in [(0x499, 'Knx.Falcon.Diagnostics.Events.DiagEventCollector', (0x1A0C, 0x1A0D, 0x1A0E)),
                                       (0x49A, 'Knx.Falcon.Diagnostics.Events.IDiagEventSink', (0x1A0F, 0x1A10)),
                                       (0x49B, 'Knx.Falcon.Diagnostics.Events.DiagEventSinkExtensions', (0x1A11, 0x1A12))]:
                symbol('Types', 0x02000000 + token, name, 'Role established by the complete event storage/decorator contract and its consumers.', proof)
        for token, name, proof in ([(0x49C, 'InstancePrefixSink', (0x1A13, 0x1A14)), (0x49D, 'SourceOverrideSink', (0x1A16, 0x1A17))] if old else
                                    [(0x60A, 'InstancePrefixSink', (0x2FB7, 0x2FB8)), (0x60B, 'SourceOverrideSink', (0x2FBD, 0x2FBE))]):
            symbol('Types', 0x02000000 + token, name, 'Event-sink decorator whose Add mutates this event property before forwarding.', proof)
        for token, name, proof in ([(0x15F7, 'innerSink', 0x1A14), (0x15F8, 'instancePrefix', 0x1A14), (0x15FA, 'innerSink', 0x1A17), (0x15FB, 'source', 0x1A17)] if old else
                                    [(0x1FA7, 'innerSink', 0x2FB8), (0x1FA8, 'instancePrefix', 0x2FB8), (0x1FAA, 'innerSink', 0x2FBE), (0x1FAB, 'source', 0x2FBE)]):
            symbol('Fields', 0x04000000 + token, name, 'Value used by the reviewed prefix/source event forwarding path.', (proof,))
        method(0x1A11 if old else 0x2FB2, 'WithInstancePrefix', 'Returns a prefixing sink only for a nonnull sink and nonempty prefix; otherwise returns the input sink.', ('sink', 'instancePrefix'))
        method(0x1A12 if old else 0x2FB3, 'WithSource', 'Wraps a nonnull sink with a source-overriding decorator; null stays null.', ('sink', 'source'))

        # Traverse sources before projecting and merging their snapshots.
        method(0x19F3 if old else 0x2F30, 'GetClosure', 'Breadth-first source traversal including the root. List.Contains prevents processing a source twice. Null root returns an empty array; null AdditionalSources is skipped, but null entries within it are not filtered. Pending duplicates may be enqueued more than once.',
               ('rootSource',), ({0: 'sources', 1: 'pendingSources', 2: 'currentSource', 3: 'additionalSources', 4: 'sourceEnumerator', 5: 'additionalSource'} if old else
                                {7: 'sources', 8: 'pendingSources', 2: 'currentSource', 3: 'additionalSources', 4: 'sourceEnumerator', 5: 'additionalSource'}))
        if old:
            symbol('Types', 0x02000492, 'Knx.Falcon.Diagnostics.DiagSourceExtensions', 'Diagnostic source closure traversal helper.', (0x19F3,))
        projection, match, attach = (0x2A23, 0x2A25, 0x2A1E) if old else (0x2F17, 0x2F1B, 0x2F0F)
        method(projection, 'GetSourceSnapshot', 'Calls the source GetStatisticsSnapshot contract; no null check or transformation.', ('source',))
        method(match, 'MatchesSnapshotIdentity', 'Tests reference identity of Definition and string equality of Instance against the captured snapshot. Does not compare values or time range.', ('candidate',))
        symbol('Fields', 0x04002B91 if old else 0x04001F64, 'snapshot', 'Snapshot captured by the definition-reference/instance equality predicate.', (attach, match))
        for token, name in ([(0x2B8E, 'Instance'), (0x2B8F, 'getSnapshot')] if old else [(0x1F61, 'Instance'), (0x1F62, 'getSnapshot')]):
            symbol('Fields', 0x04000000 + token, name, 'Shared projection context or cached source-to-snapshot delegate used during attachment.', (attach,))
        if old:
            symbol('Types', 0x020007D8, 'SnapshotSelector', 'Stateless source-to-snapshot projection context and shared delegate cache.', (projection, attach))
        method(0x2A1B if old else 0x2F0C, 'GetDiagEvents', 'Walks the exception then InnerException chain and returns the first DiagEvent array stored under typeof(DiagEvent); no match returns null.', locals_={0: 'currentException'})
        method(0x2A1D if old else 0x2F0E, 'With', 'For a nonnull diagnostic event sink, stores its ToArray result in Exception.Data under typeof(DiagEvent), replacing any prior entry; returns the same exception.', ('exception', 'diagEventSink'))
        method(attach, 'With', 'For a nonnull diagnostic source, creates/reuses the exception snapshot list, walks its source closure and appends nonnull snapshots not already matching Definition reference plus Instance. Existing matching snapshots retain their older values; a new empty list may remain attached.',
               ('exception', 'diagSource'), {0: 'snapshots', 1: 'snapshotEnumerator', 2: 'snapshotMatch'}, (projection, match, 0x19F3 if old else 0x2F30))
        method(0x2A1F if old else 0x2F10, 'With', 'If no statistics key exists, materializes the supplied sequence and stores it only when nonempty. It neither merges nor enumerates the supplied sequence when the key already exists.', ('exception', 'snapshots'), {0: 'snapshotList'})
        method(0x2A20 if old else 0x2F11, 'WithLocalizedHelpLink', 'For nonzero articleId, uses CurrentUICulture.Name, takes one Parent for a hyphenated locale, maps en to en-us and assigns the KNX support article URL. Zero leaves HelpLink untouched.', ('exception', 'articleId'), {0: 'helpLanguage'})

        # External IEnumerator/IDisposable methods keep their contract names.
        ctor, advance, cleanup, get_enum = (0x2A26, 0x2A28, 0x2A29, 0x2A2D) if old else (0x2F1F, 0x2F21, 0x2F22, 0x2F26)
        method(ctor, None, 'Captures the iterator state and the creating managed thread id.', ('state',))
        method(cleanup, 'DisposeSnapshotEnumerator', 'Resets iterator state to -1 and disposes the active List<StatisticsSnapshot>.Enumerator.', ())
        symbol('Types', 0x020007DA if old else 0x020005F2, 'ExceptionStatisticsEnumerator',
               'Traverses exception Data snapshot lists from outer to inner, yielding each Definition/Instance key at most once and suppressing definitions with zero items. The key is recorded before the zero-item check; exception/dispose paths release the active enumerator.', (advance, cleanup, get_enum))
        first = 0x2B93 if old else 0x1F66
        for offset, name, proof in [(0, 'state', (ctor, advance, get_enum)), (1, 'currentSnapshot', (advance,)),
                                   (2, 'initialThreadId', (ctor, get_enum)), (3, 'exception', (advance, get_enum)),
                                   (4, 'initialException', (get_enum,)), (5, 'reportedSnapshotIdentities', (advance,)),
                                   (6, 'currentException', (advance,)), (7, 'snapshotEnumerator', (advance, cleanup))]:
            symbol('Fields', 0x04000000 + first + offset, name, 'Iterator storage whose role is proven by the outer-to-inner snapshot enumeration and disposal paths.', proof)

    assert all(not b.pending for b in batches.values())
    batches['63'].save(stem63 if stem63.is_absolute() else root / stem63)
    batches['64'].save(stem64 if stem64.is_absolute() else root / stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
