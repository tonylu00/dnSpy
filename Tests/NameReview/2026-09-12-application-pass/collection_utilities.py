"""Review collection mutation, iterator state and change-mirroring names.

Usage: python collection_utilities.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Writes mapping/evidence only. Both physical versions are inspected independently.
"""
import json
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    for version, base, module, prefix, previous, stem in [
        ('63', 198, 'm0039', 'http63-wave196', 'common63-wave198-rev2.cumulative.json', stem63),
        ('64', 30, 'm0102', 'security64-wave29', 'zip64-wave30-rev2.cumulative.json', stem64)]:
        old = version == '63'
        b = BehaviorReview(root, version, base, module, prefix, root / previous)
        path = root / f'collections{version}-wave199-inspection.json'
        inspection = b.read(path.name)
        assert Path(inspection['Input']).resolve() == Path(b.module['Input']).resolve()
        assert all(inspection[k] == b.module[k] for k in ('Mvid', 'Sha256'))
        bodies = {int(m['Token'], 16): m for m in inspection['Methods']}
        il = {'Path': str(path), 'Sha256': sha(path)}
        if not old:
            # IL and physical graph edges bind inlined callbacks/captures to
            # their enclosing declarations. This does not bypass any blocker.
            b.bind_usage_sources(path, {0x06000750: 0x06000745, 0x06000755: 0x0600074A,
                0x06000788: 0x06000785, 0x06000789: 0x06000785, 0x0600078A: 0x06000785,
                0x040003A0: 0x06000745, 0x040003A1: 0x06000745,
                0x040003A3: 0x0600074A, 0x040003A4: 0x0600074A,
                0x040003BC: 0x06000785, 0x040003BD: 0x06000785})

        def method(rid, name, reason, parameters=None, locals_=None, replace=None):
            token = 0x06000000 + rid
            row, body = b.entries['Methods'][f'0x{token:08X}'], bodies[token]
            assert row['Signature'] == body['Signature']
            for slot in locals_ or {}:
                expected = next(x['ExpectedType'] for x in row['LocalNames'] if x['Index'] == slot)
                assert next(x['Type'] for x in body['Locals'] if x['Slot'] == slot) == expected and local_used(body, slot)
            b.add('Methods', token, name, reason, parameters, locals_, replace_alias=replace)
            assert not b.pending, b.pending
            b.decisions[-1]['IL'] = {**il, 'Token': row['Token'], 'Slots': locals_ or {}}

        def symbol(kind, rid, name, reason, proof):
            token = (0x04000000 if kind == 'Fields' else 0x02000000) + rid
            if kind == 'Fields':
                found = []
                for raw, in b.db.execute('SELECT data FROM edges WHERE target=?', (module + f':0x{token:08X}',)):
                    edge = json.loads(raw)
                    if not edge['From'].startswith(module + ':'):
                        continue
                    caller = int(edge['From'].split(':')[1], 16)
                    if caller not in {0x06000000 + rid for rid in proof}:
                        continue
                    actual = next(i for i in bodies[caller]['Instructions'] if i['Offset'] == edge['Offset'])
                    assert actual['OpCode'] == edge['Operation'] and actual['Operand']['Text'] == edge['Target']['Signature']
                    assert Path(edge['Target']['PhysicalModule']).resolve() == Path(b.module['Input']).resolve()
                    found.append(edge)
                assert found, ('Missing inspected field use', token)
            b.add(kind, token, name, reason, evidence=[0x06000000 + rid for rid in proof])
            assert not b.pending, b.pending
            b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x{0x06000000 + rid:08X}' for rid in proof]}

        # Library operations establish the semantics before outward subscriptions.
        method(0x28F if old else 0x72E, 'SyncFrom',
               'Materializes collection-minus-target removals, removes those values, then adds target-minus-updated-collection values. Uses set difference, not positional/order or multiplicity synchronization.',
               locals_={0: 'itemsToRemove', 1: 'itemsToAdd'})
        for rid in ([0x291, 0x293] if old else [0x730, 0x732]):
            method(rid, 'AddRange' if rid in (0x291, 0x730) else 'RemoveRange',
                   'Enumerates the supplied ICollection directly and adds/removes each item. The enumerable overload snapshots its input first; self-aliasing collection inputs are not copied here.',
                   locals_={0: 'itemEnumerator', 1: 'item'})
        if old:
            method(0x292, 'AddRange', 'Checks the input enumerable and snapshots it to a List before calling the ICollection overload; the overloads have distinct signatures and need no numeric suffix.', ('collection', 'items'), replace='AddRange2')
            for rid, name, before, reason in [
                (0x298, 'IsEmpty', 'None2', 'Validates a nonnull source and returns the negation of Enumerable.Any.'),
                (0x299, 'HasNoMatches', 'None3', 'Validates the source then returns the negation of Enumerable.Any with the predicate; LINQ validates the predicate.'),
                (0x29A, 'IsNullOrEmpty', 'NullOrNone', 'Returns true for null, otherwise invokes the empty-sequence predicate.'),
                (0x29B, 'IsNullOrHasNoMatches', 'NullOrNone2', 'Returns true for null without inspecting the predicate; otherwise tests that no item matches.'),
                (0x29E, 'SingleOrDefaultUnlessMultiple', 'SingleOrNull', 'Returns default(T) for zero or multiple items, including zero for non-nullable value types; exactly one item is fetched by enumerating source again.'),
                (0x2A8, 'GetFirstOrDefaultAndTestNonNull', 'TryGetValue', 'Assigns FirstOrDefault(predicate), boxes it and tests against null. A missing non-nullable value-type match therefore still returns true.'),
                (0x2D0, 'AsCollectionOrEmpty', 'ToCollection', 'Returns Array.Empty<T> for a null value and a new one-element array otherwise.'),
                (0x2C8, 'ToReadOnlySnapshot', 'ToReadOnlyCollection', 'Materializes a new List and wraps it read-only; it is a copied snapshot rather than a live view over the input.')]:
                method(rid, name, reason, replace=before)
        method(0x29D if old else 0x73D, 'IsSingle',
               'Counts up to two items, disposing its enumerator before returning; true only for exactly one item.',
               locals_={0: 'itemCount', 1: 'enumerator', 2: 'hasExactlyOne'})
        method(0x2C7 if old else 0x781, 'IndexOf',
               'Enumerates in order and returns the first index satisfying Predicate<T>, or -1. Source is guarded; a null predicate faults only if an item is visited.',
               locals_={0: 'index', 1: 'enumerator', 2: 'item', 3: 'matchingIndex'})
        method(0x2D2 if old else 0x792, 'InsertRecentItem' if old else 'AddRecentItem',
               'Inserts a missing item at index zero and removes one last value when a positive limit is exceeded; an existing item is removed and reinserted at zero without trimming.',
               ('collection', 'item', 'maxLength') if old else None, {0: 'existingIndex'})
        method(0x2D3 if old else 0x794, 'TryPop',
               'Checks Count then attempts Pop; any exception inside the try becomes false/default(T). This is not a concurrent atomic operation.',
               locals_={0: 'popped'})

        # Preserve MoveNext/Dispose/GetEnumerator runtime contracts. Name their
        # concrete storage and constructors using the independently read bodies.
        for rid in ([0x2AD, 0x2B6] if old else [0x758, 0x764]):
            method(rid, None, 'Stores the supplied iterator state and captures the creating managed thread ID.', ('state',))
        if not old:
            method(0x75B, 'ReleasePartitionEnumerator', 'Sets iterator state to -1 and disposes the retained source enumerator if nonnull; does not clear the field.', ())
        for rid, name, proof in ([(0xA1, 'PartitionIterator', (0x29C, 0x2AF, 0x2B4)),
                                  (0xA2, 'RepeatedGeneratorIterator', (0x297, 0x2B8, 0x2BC))] if old else
                                 [(0x118, 'PartitionIterator', (0x73C, 0x75A, 0x75F)),
                                  (0x119, 'RepeatedGeneratorIterator', (0x737, 0x766, 0x76A))]):
            symbol('Types', rid, name, 'Deferred sequence implementation with separate captured inputs and active enumeration state.', proof)
        fields = ([(0x214, 'state', (0x2AD, 0x2AF)), (0x215, 'currentPartition', (0x2AF,)),
                   (0x216, 'initialThreadId', (0x2AD, 0x2B4)), (0x217, 'source', (0x2AF, 0x2B4)),
                   (0x218, 'initialSource', (0x29C, 0x2B4)), (0x219, 'partitionSize', (0x2AF, 0x2B4)),
                   (0x21A, 'initialPartitionSize', (0x29C, 0x2B4)), (0x21B, 'sourceEnumerator', (0x2AF, 0x2B0)),
                   (0x21D, 'state', (0x2B6, 0x2B8)), (0x21E, 'currentItem', (0x2B8,)),
                   (0x21F, 'initialThreadId', (0x2B6, 0x2BC)), (0x220, 'generator', (0x2B8, 0x2BC)),
                   (0x221, 'initialGenerator', (0x297, 0x2BC)), (0x222, 'count', (0x2B8, 0x2BC)),
                   (0x223, 'initialCount', (0x297, 0x2BC)), (0x224, 'generatedCount', (0x2B8,))] if old else
                  [(0x3A6, 'state', (0x758, 0x75A)), (0x3A7, 'currentPartition', (0x75A,)),
                   (0x3A8, 'initialThreadId', (0x758, 0x75F)), (0x3AA, 'initialSource', (0x73C, 0x75F)),
                   (0x3AC, 'initialPartitionSize', (0x73C, 0x75F)), (0x3AD, 'sourceEnumerator', (0x75A, 0x75B)),
                   (0x3AF, 'state', (0x764, 0x766)), (0x3B0, 'currentItem', (0x766,)),
                   (0x3B1, 'initialThreadId', (0x764, 0x76A)), (0x3B3, 'initialGenerator', (0x737, 0x76A)),
                   (0x3B5, 'initialCount', (0x737, 0x76A)), (0x3B6, 'generatedCount', (0x766,))])
        for rid, name, proof in fields:
            symbol('Fields', rid, name, 'Iterator state/input/current/counter role proven by construction, GetEnumerator input copying, MoveNext or cleanup.', proof)

        method(0x2AC if old else 0x750, 'CreateIndexedItem', 'Constructs a ValueTuple of the input item and its zero-based LINQ index.', ('item', 'index'))
        if old:
            symbol('Types', 0xA0, 'IndexedItemFactory', 'Stateless owner of the cached selector constructing item/index tuples.', (0x2A5, 0x2AC))
        for rid, name, proof in ([(0x211, 'instance', (0x2A5,)), (0x212, 'createIndexedItem', (0x2A5,))] if old else
                                 [(0x3A0, 'instance', (0x745,)), (0x3A1, 'createIndexedItem', (0x745,))]):
            symbol('Fields', rid, name, 'Cached selector instance/delegate consumed by Enumerable.Select with its index overload.', proof)
        if not old:
            method(0x755, 'IsNonNull', 'Boxes the generic item and tests against null; non-nullable value types always pass.', ('item',))
            for rid, name in [(0x3A3, 'instance'), (0x3A4, 'isNonNull')]:
                symbol('Fields', rid, name, 'Cached instance/delegate used by the reviewed NonNull filter.', (0x74A,))

        method(0x2CA if old else 0x785, 'MirrorCollectionChanges' if old else 'SyncTo',
               'Initially replaces target contents if sequences differ, then returns a disposable Rx subscription that casts source items to the target type and applies collection changes.',
               locals_={0: 'subscription'}, replace='MirrorCollectionChanges2' if old else None)
        method(0x2CC if old else 0x788, 'SubscribeToSourceCollection', 'Adds the handler to the retained observable source CollectionChanged event.', ('handler',))
        method(0x2CD if old else 0x789, 'UnsubscribeFromSourceCollection', 'Removes the handler from the retained observable source CollectionChanged event.', ('handler',))
        method(0x2CE if old else 0x78A, 'ApplySourceCollectionChange',
               'Skips equal sequences. Adds/removes by item value; Replace adds new values before removing old values, and other actions rebuild from event Sender. It does not preserve insertion indices for Add/Replace.',
               ('change',), {0: 'eventSource', 1: 'newItems', 2: 'oldItems', 3: 'action'})
        if old:
            symbol('Types', 0xA8, 'CollectionMirrorSubscription', 'Captures the source and target plus Rx event add/remove/change callbacks.', (0x2CA, 0x2CC, 0x2CD, 0x2CE))
        for rid, name, proof in ([(0x22C, 'source', (0x2CA, 0x2CC)), (0x22D, 'target', (0x2CA, 0x2CE))] if old else
                                 [(0x3BC, 'source', (0x785,)), (0x3BD, 'target', (0x785,))]):
            symbol('Fields', rid, name, 'Observable source or writable target retained by the mirroring callbacks.', proof)
        b.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
