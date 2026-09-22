"""Stage behavior-reviewed HTTP configuration, pooling and forwarding names.

Usage: python http_client_pool.py ARTIFACT_ROOT NEW_STEM
Metadata/map evidence only; no ETS source replacement or analyzed code execution.
"""
import json
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem):
    b = BehaviorReview(root, '63', 195, 'm0039', {
        'Methods': 'http63-wave196-methods.json', 'Types': 'http63-wave196-types.json',
        'Fields': 'http63-wave196-fields.json'}, root / 'exception63-wave195.cumulative.json')
    old_reference = sha(root / 'contract-references63-v2.json')
    reference = sha(root / 'contract-references63-v3.json')
    assert b.prior['ContractReferenceSha256'] == old_reference
    previous = b.read('contract-references63-v2.json')['Assemblies']
    current = b.read('contract-references63-v3.json')['Assemblies']
    assert current[:-1] == previous and len(current) == len(previous) + 1
    assert current[-1]['Identity'] == 'netstandard, Version=2.0.0.0, Culture=neutral, PublicKeyToken=cc7b13ffcd2ddd51'
    for assembly in current:
        assert sha(assembly['Path']) == assembly['Sha256']
    preflight = b.read('map-check63-wave196-reference-context.json')
    assert preflight['Success'] and not preflight['Errors'] and not preflight['Changes']
    assert preflight['BaseMapSha256'] == b.base_hash and preflight['ContractReferenceSha256'] == reference
    b.prior['ContractReferenceSha256'] = b.delta['ContractReferenceSha256'] = reference

    inspection_path = root / 'http63-wave196-full-inspection.json'
    inspection = b.read(inspection_path.name)
    assert Path(inspection['Input']).resolve() == Path(b.module['Input']).resolve()
    assert all(inspection[k] == b.module[k] for k in ('Sha256', 'Mvid'))
    bodies = {int(m['Token'], 16): m for m in inspection['Methods']}
    families = b.read('http63-wave196-families.json')
    assert families['ContractReferenceSha256'] == reference
    il = {'Path': str(inspection_path), 'Sha256': sha(inspection_path)}

    def method(rid, name, reason, parameters=None, locals_=None, contract=None, replace=None):
        token = 0x06000000 + rid
        row, body = b.entries['Methods'][f'0x{token:08X}'], bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in locals_ or {}:
            expected = next(l['ExpectedType'] for l in row['LocalNames'] if l['Index'] == slot)
            assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
        b.add('Methods', token, name, reason, parameters, locals_, contract=contract, replace_alias=replace)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'Token': f'0x{token:08X}', 'Slots': locals_ or {}}

    def symbol(kind, token, name, reason, proof):
        if kind == 'Fields':
            edges = [json.loads(r[0]) for r in b.db.execute('SELECT data FROM edges WHERE target=?', (b.module_id + f':0x{token:08X}',))]
            matching = []
            for edge in edges:
                if not edge['From'].startswith(b.module_id + ':'):
                    continue
                caller = int(edge['From'].split(':')[1], 16)
                if caller not in {0x06000000 + rid for rid in proof}:
                    continue
                actual = next(i for i in bodies[caller]['Instructions'] if i['Offset'] == edge['Offset'])
                assert actual['OpCode'] == edge['Operation'] and actual['Operand']['Text'] == edge['Target']['Signature']
                assert Path(edge['Target']['PhysicalModule']).resolve() == Path(b.module['Input']).resolve()
                matching.append(edge)
            assert matching, ('Missing inspected field use', token)
        b.add(kind, token, name, reason, evidence=[0x06000000 + rid for rid in proof])
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x{0x06000000 + rid:08X}' for rid in proof]}

    # Configuration and header filtering precede client creation and acquisition.
    method(0x257, None, 'Copies the initial headers through the base constructor and retains a nonblank cloud URL.', ('url', 'headers'))
    method(0x259, 'GetUrl', 'Returns the stored cloud URL. The private default constructor stores n/a.', ())
    method(0x25B, None, 'Copies supplied headers into a new Dictionary, or creates an empty one for null.', ('headers',))
    symbol('Types', 0x02000088, 'Knx.Ets.Common.Http.IHttpClientConfiguration',
           'Contract providing the additional headers consumed when constructing HTTP clients.', (0x260, 0x26F))
    symbol('Fields', 0x0400018F, 'url', 'URL validated by construction and returned unchanged by GetUrl.', (0x257, 0x258, 0x259))
    symbol('Fields', 0x04000193, 'headers', 'Mutable copied dictionary wrapped by GetAdditionalHeaders; the read-only view is not a snapshot.', (0x25B, 0x25C))
    method(0x27F, 'ShouldIncludeHeader',
           'Accepts every header when includeRedirectHeader is true; otherwise rejects only the exact case-sensitive x-knx-redirect key. This is inclusion policy, not a test identifying redirect headers.',
           ('header',), replace='IsRedirectHeader')
    symbol('Types', 0x02000092, 'RequestHeaderFilter', 'Captured header inclusion policy and cached predicate delegate.', (0x27F, 0x26F))
    symbol('Fields', 0x040001C4, 'includeRedirectHeader', 'Controls whether x-knx-redirect is retained, without changing transport redirect handling.', (0x27F, 0x26F))
    symbol('Fields', 0x040001C5, 'shouldIncludeHeader', 'Cached predicate used in Enumerable.Where over configured headers.', (0x26F,))
    method(0x26C, None, 'Retains nonnull configuration and creates separate concurrent stacks for the two header policies.', ('configuration',))
    method(0x271, None, 'Retains nonnull factory and HttpClient plus the header policy used to select its return stack.', ('factory', 'client', 'includeRedirectHeader'))
    method(0x26F, 'CreateClient',
           'Creates a new HttpClient, adds configured headers accepted by ShouldIncludeHeader and wraps it with its factory and header policy. This creates and returns a client rather than collecting headers.',
           ('includeRedirectHeader',), {0: 'headerFilter', 1: 'client', 2: 'headerEnumerator', 3: 'shouldIncludeHeader', 4: 'header'},
           replace='CollectRedirectHeaders')
    method(0x273, 'DisposeHttpClient', 'Disposes the underlying HttpMessageInvoker directly; ordinary wrapper disposal returns the wrapper to its factory stack.', ())

    specifications = [
        ({0x26D, 0x270}, 'AcquireClient', ('includeRedirectHeader',),
         'Selects the matching header-policy stack, tries to pop a wrapper, and creates a new one only when the popped value is null. Checks factory disposal first.'),
        ({0x274, 0x279}, 'SendAsync', ('request', 'cancellationToken'),
         'Forwards the supplied request and cancellation token directly to HttpMessageInvoker.SendAsync.'),
        ({0x275, 0x27C}, 'GetByteArrayAsync', ('requestUri',),
         'Forwards a string URI directly to HttpClient.GetByteArrayAsync, returning its task.'),
        ({0x276, 0x27D}, 'GetByteArrayAsync', ('requestUri',),
         'Forwards a Uri directly to HttpClient.GetByteArrayAsync, returning its task.'),
        ({0x277, 0x27A}, 'GetAsync', ('requestUri', 'cancellationToken'),
         'Forwards a Uri and cancellation token directly to HttpClient.GetAsync.'),
        ({0x278, 0x27B}, 'GetAsync', ('requestUri', 'cancellationToken'),
         'Forwards a string URI and cancellation token directly to HttpClient.GetAsync.')]
    for members, name, parameters, reason in specifications:
        seed = next(r for r in families['Methods'] if r['Module'] == b.relative and int(r['Token'], 16) == 0x06000000 + min(members))
        rows = [r for r in families['Methods'] if r['ContractFamily'] == seed['ContractFamily']]
        assert {int(r['Token'], 16) - 0x06000000 for r in rows} == members and all(r['Module'] == b.relative for r in rows)
        for row in rows:
            rid = int(row['Token'], 16) - 0x06000000
            method(rid, name, reason, parameters, {0: 'client'} if rid == 0x26D else None, contract=row)
    for token, name, reason, proof in [
        (0x0200008E, 'Knx.Ets.Common.Http.PooledHttpClientFactory', 'Maintains separate wrapper pools for requests with or without the KNX redirect header.', (0x26C, 0x26D, 0x26E, 0x26F)),
        (0x0200008F, 'Knx.Ets.Common.Http.IHttpClientFactory', 'Contract acquiring a reusable client for the selected header policy.', (0x270, 0x26D)),
        (0x02000090, 'PooledHttpClient', 'HTTP forwarding wrapper returned to its factory on disposal. Underlying client disposal is a separate method.', (0x271, 0x272, 0x273))]:
        symbol('Types', token, name, reason, proof)
    for rid, name, proof in [
        (0x1BC, 'configuration', (0x26C, 0x26F)),
        (0x1BD, 'clientsWithRedirectHeader', (0x26C, 0x26D, 0x272)),
        (0x1BE, 'clientsWithoutRedirectHeader', (0x26C, 0x26D, 0x272)),
        (0x1C0, 'factory', (0x271, 0x272)),
        (0x1C1, 'client', (0x271, 0x273, 0x274)),
        (0x1C2, 'includeRedirectHeader', (0x271, 0x272))]:
        symbol('Fields', 0x04000000 + rid, name, 'Storage directly used by the reviewed construction, acquisition, forwarding or return-to-pool operation.', proof)
    b.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
