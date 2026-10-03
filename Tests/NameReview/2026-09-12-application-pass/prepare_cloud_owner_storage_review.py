"""Prepare physical CloudKit owner/storage reviews; never patch ETS artifacts."""
import argparse
import json
import pathlib
import sqlite3
import xml.etree.ElementTree as ET
from prepare_cloud_crypto_review import read, digest
from prepare_physical_review import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('state', 'inventory', 'ledger', 'bodies', 'platform-bodies', 'native-bodies',
                   'types', 'fields', 'families', 'graph', 'output'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    state, inventory, ledger = read(args.state), read(args.inventory), read(args.ledger)
    physical = pathlib.Path(state['Pass']['SourceTree63']) / 'Knx.CloudKit.dll'
    paths = [args.bodies, args.platform_bodies, args.native_bodies, args.types, args.fields]
    documents = list(map(read, paths))
    bodies, platform, native, types, fields = documents
    for document in documents:
        assert pathlib.Path(document['Input']).resolve() == physical.resolve()
        assert document['Sha256'] == digest(physical) and document['Mvid'] == types['Mvid']
        assert document['Identity'] == types['Identity']
    assert inventory['MapSha256'] == state['Maps']['63']['Sha256'] == digest(state['Maps']['63']['Path'])
    reports = [r for r in inventory['Reports'] if r['Module'] == 'Knx.CloudKit.dll']
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    catalog = {kind: {r['Token']: r for report in reports if report['Kind'] == kind
                     for r in read(report['Path'])[kind]} for kind in ('Types', 'Fields', 'Methods')}
    methods = {m['Token']: m for document in documents for m in document.get('Methods', [])}
    storage = {f['Token']: f for f in fields['Fields']}
    type_rows = {t['Token']: t for t in types['Types']}
    aliases = {r.get('Token'): r for m in ET.parse(state['Maps']['63']['Path']).getroot()
               if m.get('Path') == 'Knx.CloudKit.dll' for r in m}
    previous = {r['Token']: r for k in ('Types', 'Fields', 'Methods') for r in ledger[k] if r['Module'] == 'Knx.CloudKit.dll'}
    families = read(args.families)
    assert families['ContractReferenceSha256'] == state['Compatibility']['ContractReferences63']['Sha256']
    contract_rows = {r['Token']: r for r in families['Methods'] if r['Module'] == 'Knx.CloudKit.dll'}
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    module = next(m for m in meta['Modules'] if pathlib.Path(m['Input']).resolve() == physical.resolve())
    assert module['Mvid'] == types['Mvid']
    rows, references, closures, pending = [], {}, [], []

    def token(number):
        return f'0x{number:08X}'

    def edges(number):
        key = token(number)
        found = [dict(Source=s, Reference=json.loads(d)) for s, d in graph.execute(
            'select source,data from edges where target=?', (module['Id'] + ':' + key,))]
        references[key] = found
        return found

    def instructions(number):
        return methods[token(number)]['Instructions'] or []

    def uses(number, target, operation=None):
        assert any(isinstance(i['Operand'], dict) and i['Operand'].get('Token') == token(target)
                   and (operation is None or i['OpCode'] == operation) for i in instructions(number))

    def add(kind, number, name, reason, parameters=None, locals_=None, disposition='rename'):
        key = token(number)
        row = dict(Kind=kind, Module='Knx.CloudKit.dll', Token=key, Reason=reason, Disposition=disposition)
        if name:
            row['NewName'] = name
        if parameters:
            row['ParameterNames'] = parameters
        if locals_:
            row['LocalNames'] = locals_
        if previous.get(key, {}).get('Unresolved'):
            assert name and key not in aliases
            row.update(ResolveExistingUnresolved=True,
                       PreviousUnresolvedEvidence={k: previous[key].get(k, '') for k in ('Reason', 'UnresolvedReason')})
        rows.append(row)

    def field(number, name, reason):
        assert storage[token(number)]['MappingBlocker'] is None
        incoming = edges(number)
        assert incoming or storage[token(number)]['IsLiteral']
        add('Fields', number, name, reason + ' Preserve original runtime metadata, flags, storage and values through restoration.')

    def unknown(number, reason):
        incoming = edges(number)
        add('Fields', number, '', f'no-evidence-in-scope: {reason} {len(incoming)} physical incoming edges across {len(meta["Modules"])} hash-verified inputs; reflection/external users are not ruled out.', disposition='unresolved')

    def method(number, reason, parameters=None, locals_=None, name=None, family=False):
        key = token(number)
        assert methods[key]['HasBody'] or family
        parameters, locals_ = dict(parameters or {}), dict(locals_ or {})
        mapped = aliases.get(key)
        if mapped is not None:
            for child in mapped.findall('Parameter'):
                if not (number == 0x06000062 and child.get('Sequence') == '1'):
                    parameters[child.get('Sequence')] = child.get('NewName')
            for child in mapped.findall('Local'):
                locals_[child.get('Index')] = child.get('NewName')
        else:
            assert name or parameters or locals_
        if not family:
            assert catalog['Methods'][key]['ScopedMappingBlocker'] is None
        add('Methods', number, name or (mapped.get('NewName') if mapped is not None else None),
            reason + ' Preserve accepted scopes and exclude unused boilerplate locals.', parameters, locals_)

    for number, name, reason in [
        (0x0200000B, 'CloudNativeChangeEventHandler', 'Delegate Invoke5F(Object,ajc) carries the timestamp/count/mutex/architecture record through native-library and manager notifications.'),
        (0x02000012, 'PackagePayloadLoadedHandler', 'Delegate InvokeF3(Class11) receives the exact payload newly admitted by ConcurrentDictionary.TryAdd inD8; synchronous/asynchronous handlers keep original calling conventions.'),
        (0x02000011, 'Knx.CloudKit.Secure.ICloudManager', 'Interface is implemented by physical CloudManager ajg; seven exact slots expose dongle count, native version, availability/control and enumeration lifecycle. Preserve the complete runtime interface contract.'),
        (0x02000018, 'FeatureValueAggregation', 'Enum argument3 in126 selects maximum/minimum/rounded arithmetic mean/sum/first matching feature branches; do not alter sentinel, overflow or iteration behavior.'),
        (0x0200006D, 'CloudPackageProgressEventHandler', 'Delegate Invoke320(Object,aj4) carries CloudPackageProgressEventArgs through package parsing/import/progress notifications.')]:
        assert token(number) not in aliases
        add('Types', number, name, reason)

    for owner, closure, target, captured in [(0x06000049,0x0200000A,0x0600005D,[0x04000038,0x04000039]),
                                            (0x060000CC,0x02000013,0x060000F7,[0x0400006F,0x04000070,0x04000071]),
                                            (0x060000D7,0x02000014,0x060000F9,[0x04000073,0x04000074])]:
        assert 'System.Runtime.CompilerServices.CompilerGeneratedAttribute' in type_rows[token(closure)]['Attributes']
        uses(owner, target, 'ldftn')
        assert [i['Operand']['Token'] for i in instructions(owner) if i['OpCode'] in ('ldftn','ldvirtftn')] == [token(target)]
        assert type_rows[token(closure)]['Type'].startswith(catalog['Methods'][token(owner)]['Type'] + '/')
        for captured_field in captured:
            uses(owner, captured_field, 'stfld')
            uses(target, captured_field, 'ldfld')
        owner_name = aliases[token(owner)].get('NewName')
        add('Types', closure, '', f'Compiler-generated closure instantiated by{token(owner)} ({owner_name}); exact ldftn{token(target)} and captured stores/loads bind this owner. Preserve compiler container identity for structural reconstruction; do not invent an ordinary semantic type.', disposition='preserve')
        method(target, f'Unique generated delegate target in{token(owner)}; restore the first lambda pattern of its exact owner for reconstruction, retaining runtime name/signature.', name=f'<{owner_name}>b__0')
        closures.append(dict(Owner=token(owner), OwnerAlias=owner_name, Container=token(closure), Target=token(target), Captures=[token(n) for n in captured]))

    field_roles = {
        0x2E:('certificates','4C registers into Class12<ai6>;53 enumerates,55 counts,58/59 query names,5A refreshes.'),
        0x2F:('certificateLoadLock','48/4A Monitor.Enter/Exit serialize single and batch certificate parsing.'),
        0x30:('certificateNotificationLock','4D..52 Monitor.Enter/Exit take snapshots of certificate notification handlers.'),
        0x31:('resultProgressHandlers','3C/3D Combine/Remove/CompareExchange;4D forwards ai9 result to these listeners after the explicit callback.'),
        0x32:('progressChangedHandlers','3E/3F subscription pair;4E invokes with initial certificate-count progress record.'),
        0x36:('certificateLoadFailedHandlers','46/47 subscription pair;52 invokes on load failure.'),
        0x38:('certificatePayload','49 captures String argument1;5D forwards it unchanged as4A parser input.'),
        0x39:('callback','49 captures Action argument2;5D forwards it to4A result dispatch.'),
        0x3D:('instanceCount','62 stores argument1;64 reads it. Library-load events and manager construction/shutdown supply their respective instance counters, not timer duration.'),
        0x3E:('usesLocalMutex','62 stores argument2;65 reads it; native runtime loading paths provide their local-mutex flag.'),
        0x3F:('isNativeLibrary64Bit','62 stores1AA result;66 reads. 1AA Windows branch reaches22E Is64BitProcess/UInt64-pointer-size checks; ARM architecture branch also sets this bit. Preserve Unix fallback behavior.'),
        0x47:('packageEventHandlers','74/75 subscription pair;B1 builds package message event and invokes.'),
        0x48:('packagesLoadedHandlers','76/77 subscription pair;B2 invokes after D8 completes the package batch.'),
        0x49:('packageProgressHandlers','78/79 subscription pair;B3 forwards package progress records.'),
        0x4A:('packagesParsedHandlers','7A/7B subscription pair;B4 emits parsed package list before import.'),
        0x4B:('packageImportProgressHandlers','7C/7D subscription pair;B5 emits import totals/results.'),
        0x4D:('nativeManagerLoadingHandlers','80/81 subscription pair;B7 forwards library-loading notification A8.'),
        0x4E:('nativeManagerLoadedHandlers','82/83 subscription pair;B8 forwards library-loaded notification A7.'),
        0x4F:('nativeManagerUnloadingHandlers','84/85 subscription pair;B9 forwards library-unloading notification A6.'),
        0x50:('nativeManagerUnloadedHandlers','86/87 subscription pair;BA forwards library-unloaded notification A5.'),
        0x53:('managerCreatedHandlers','8C/8D subscription pair;only constructorA0 calls BD, which emits this manager and global instance count after increment.'),
        0x54:('managerShutdownHandlers','8E/8F subscription pair;only ShutdownE8 calls BE after decrement, invalidation and optional shared cleanup.'),
        0x55:('packagePayloadLoadedHandlers','90/91 subscription pair;D8 supplies newly added Class11 payload to each typed handler.'),
        0x57:('packageNotificationLock','B1..BE Monitor.Enter/Exit snapshot package and native/manager notification delegates.'),
        0x59:('managerInstanceCount','A0 Interlocked.Increment;E8 reads/decrements;C6 Interlocked.Read. C6 does not read interval field65.'),
        0x5E:('enumerationStartingHandlers','92/93 subscription pair;AA emits enumeration-start event.'),
        0x5F:('enumerationCompletedHandlers','94/95 subscription pair;AB emits elapsed/count result.'),
        0x61:('licenseChangedHandlers','98/99 subscription pair;AD supplies a changed license.'),
        0x62:('donglesChangedHandlers','9A/9B subscription pair;AE emits dongle change notification.'),
        0x63:('nativeManagerLoadFailedHandlers','9C/9D subscription pair;AF emits manager failure.'),
        0x65:('keepAliveIntervalMilliseconds','BF Interlocked.Exchange then Timer.Change;C0 reschedules the same interval with infinite period.'),
        0x66:('keepAliveTimer','A0 creates Timer targetingC0;BF/C0 Change andE9 Dispose.'),
        0x67:('licensePayloadLock','D9/DB/DC Monitor.Enter/Exit serialize attaching/reloading package payloads on licenses.'),
        0x68:('dongleEnumerationLock','C0/D1 Monitor.Enter/Exit serialize BuildSubDongleMap and refresh shared dongles.'),
        0x69:('dongleNotificationLock','AA..B0 Monitor.Enter/Exit snapshot dongle/session/signature handlers.'),
        0x6A:('isInvalidated','A0/C5 set flag on initialization failure or deactivation;C4 returns inverse, C5 propagates it into dongle invalidation;E8 sets on shutdown.'),
        0x6B:('lastNativeStateCode','C0 compares current1B8 result to previous code, stores1/10 and emits other state changes.'),
        0x6C:('sessionToken','C0 stores changed nonempty decrypted1B6 token and suppliesB0; constructor initializes empty.'),
        0x6F:('manager','CC captures this ajg forF7 instance callCD.'),
        0x70:('featureLabel','CC captures argument1;F7 forwardsCD to CB filtering exact active feature label.'),
        0x71:('callback','CC captures typed result callback;F7 forwardsCD which invokes(label,licenses).'),
        0x73:('packageText','D7 captures string input;F9 forwards unchanged toD8/Class7 package parsing.'),
        0x74:('progressCallback','D7 captures package progress callback;F9 forwards unchanged toD8 result dispatch.'),
        0x76:('licenses','FA allocates Class12<ajq>;FB enumerates/FC counts/108 adds/106 clears invalidated entries.'),
        0x79:('parent','103/104 getter/setter;subordination-chain methods connect dongle ownership.'),
        0x7A:('dongleIdentifier','FA stores argument1;FD returns it;BuildSubDongleMap keys dongles with this identifier.'),
        0x7B:('displayName','FA stores argument2;FE returns it for dongle display.'),
        0x7C:('isInvalidated','106 writes and clears licenses when true;105 reads;107 returns -1 if invalidated.'),
        0x7D:('isUpdated','109 sets true/restarts stopwatch only on transition;10A clears,102 reads.'),
        0x8B:('featureLabel','11A stores argument1;11C returns;122 validates membership and checksum against it.'),
        0x8C:('featureValue','11A stores UInt16 argument2;11D returns;11E/11F test none/unlimited sentinels.'),
        0x8D:('parent','120/121 getter/setter;122 resolves containing license through subordination chain.'),
        0x8E:('checksum','11A stores11B ASCII-label/value-byte checksum;122 compares recomputed result.'),
        0xA8:('featuresByLabel','137 allocates ConcurrentDictionary, assigns each feature parent and adds by11C label;14D retrieves by label,138 returns Count.'),
        0xA9:('packagePayload','137 null-initializes;151 attaches exact matching Class11 and its features;146 tests missing payload.'),
        0xAA:('definition','137 stores ajr constructor argument;139..150 delegate typed license properties/definition to it.'),
        0xAB:('parent','148/149 getter/setter;subordination-chain helpers use license ownership.'),
        0x1B5:('useLocalMutex','2E4 reads,2E5 writes only before initialization;2DF supplies1AC library initialization.'),
        0x1B6:('initializationAttempted','2DF sets BEFORE trying1AC;2E2 requires it plus not-failed. Reset2E1 clears only after nonfailed attempt; do not call this a success flag.'),
        0x1B7:('initializationFailed','2DF sets when1AC fails;2E2 rejects it and2E1 avoids unload on failure.'),
        0x1B8:('nativeRuntimeNotificationLock','2E6..2EA Monitor.Enter/Exit snapshot forwarded native event delegates.'),
        0x1B9:('nativeRuntimeLoadingHandlers','2D4/2D5 subscription pair;2EA forwards original library loading.'),
        0x1BA:('nativeRuntimeLoadedHandlers','2D6/2D7 subscription pair;2E9 forwards loaded.'),
        0x1BB:('nativeRuntimeUnloadingHandlers','2D8/2D9 subscription pair;2E8 forwards unloading.'),
        0x1BC:('nativeRuntimeUnloadedHandlers','2DA/2DB subscription pair;2E7 forwards unloaded.'),
        0x1BD:('nativeRuntimeLoadFailedHandlers','2DC/2DD subscription pair;2E6 forwards failed load.')}
    for number, (name, reason) in field_roles.items():
        field(0x04000000 + number, name, reason)
    for number, name, value, behavior in [(0x86,'Maximum',0,'406 excludes no-value and310 stores greater value'),
                                        (0x87,'Minimum',1,'466 seeds unlimited,320 tests smaller values and373 stores minimum'),
                                        (0x88,'Average',2,'440..403 sums finite values/counts,56 rounds sum/count; unlimited overrides'),
                                        (0x89,'Sum',3,'352..370 adds finite values;433 flags unlimited'),
                                        (0x8A,'First',4,'296..305 returns first eligible matching feature value')]:
        assert storage[token(0x04000000 + number)]['Constant'] == value
        field(0x04000000 + number, name, f'Literal{value} in126 aggregation enum: branch{behavior}. Keep sentinel/iteration/overflow semantics.')
    for number, reason in [(1,'Attribute stores constructor string and exposes opaque Property:A; value evidence is insufficient to prove version/product meaning.'),
                           (2,'Attribute stores constructor integer and exposes opaque Property:C; no semantic consumer establishes its purpose.'),
                           (0x52,'BB forwards ajc but has zero managed callers; subscription pair8A/8B alone does not establish notification purpose.'),
                           (0x5A,'Unused Int32 constant metadata; no semantic token consumers.'), (0x5B,'Unused Int32 constant metadata; no semantic token consumers.'),
                           (0x5C,'Unused Int32 constant metadata; no semantic token consumers.'), (0x5D,'Unused Int32 constant metadata; no semantic token consumers.'),
                           (0x77,'FA allocates object but no reader uses it; do not invent a lock role.'),
                           (0x78,'FA allocates object but no reader uses it; do not invent a lock role.'),
                           (0x7E,'FA allocates object but no reader uses it; no supported ownership or synchronization role.'),
                           (0xA7,'Unused Int32 constant metadata has no semantic token consumers.')]:
        unknown(0x04000000 + number, reason)
    add('Fields',0x040001F9,'','CloudKitResultCode.OK is a meaningful existing status name. Preserve it; native short-name flag alone is not evidence of obfuscation.', disposition='preserve')

    params = lambda *names: {str(i): name for i, name in enumerate(names, 1)}
    locals_ = lambda *names: {str(i): name for i, name in enumerate(names)}
    method(0x060000C6,'Reads global manager counter59 with Interlocked.Read; constructor increments and Shutdown decrements. Earlier interval label contradicts field65 Timer.Change dataflow.', name='GetManagerInstanceCount')
    method(0x06000138,'Body returns ConcurrentDictionary featuresByLabel.Count; it does not compute any hash.', name='GetFeatureCount')
    method(0x06000064,'Returns ctor-supplied instance count3D used by both native loading and manager construction/shutdown notifications; no timer interval role.', name='GetInstanceCount')
    method(0x060001AA,'Windows path reads PE64 flag22E, requiring Is64BitProcess and UInt64 pointer size; ARM path tests64-bit architecture, generic Unix path preserves false fallback. This bit is consumed as64-bit flag by eventargs66, not as general support status.', name='IsNativeLibrary64Bit')
    uses(0x060000A0,0x060000BD,'call')
    uses(0x060000E8,0x060000BE,'call')
    for number, field_number, name in [(0x8C,0x53,'SubscribeManagerCreated'),(0x8D,0x53,'UnsubscribeManagerCreated'),
                                      (0x8E,0x54,'SubscribeManagerShutdown'),(0x8F,0x54,'UnsubscribeManagerShutdown')]:
        uses(0x06000000+number,0x04000000+field_number,'ldsflda')
        method(0x06000000+number,f'Exact handler field{token(0x04000000+field_number)} is emitted only at manager construction or shutdown; delegate CAS loop retains subscription semantics.',params('handler'),locals_('currentHandlers','previousHandlers','updatedHandlers'),name=name)
    method(0x060000BD,'Sole caller is manager ctorA0 after global instance-count increment. Emits this sender and current instance-count record to field53 handlers.',params('manager'),name='RaiseManagerCreated')
    method(0x060000BE,'Sole caller is ShutdownE8 after global count decrement and invalidation; emits updated count with null sender to field54 handlers.',name='RaiseManagerShutdown')
    for number in (0x060000C3,0x060000EC):
        method(number,'Exact complete interface/implementation family returns1B7 native CloudKit Version, default Version on failure; physical family review removes obsolete historical blocker.', name='GetNativeCloudLibraryVersion', family=True)
    method(0x06000062,'Stores instance count and mutex arguments into event record;64/65 expose them.', params('instanceCount','usesLocalMutex'))
    method(0x06000049,'Captures parser input and result callback for exact5D lambda.', params('certificatePayload','callback'))
    method(0x060000CC,'Captures feature selector and callback into exact F7 owner; result invokes selector and active-license sequence.', params('featureLabel','callback'))
    method(0x060000CD,'CB filters active feature label; callback receives unchanged label and licenses.', params('featureLabel','callback'))
    method(0x060000D7,'Captures package parser input and progress callback into exact F9 owner.', params('packageText','progressCallback'))
    method(0x060000D8,'Class7 parses payload; dictionary TryAdd separates added/rejected counts and supplies current definition/payload to callbacks.', params('packagePayload','callback'),
           locals_('packageCount','addedCount','rejectedCount','definitions','definitionEnumerator','definition','payload','payloadHandlers','handlerIndex','untypedHandler','payloadHandler'))
    method(0x060000BF,'Nonzero interval or infinite(-1) stored into65; Timer.Change uses milliseconds and infinite periodic interval.', params('intervalMilliseconds'))
    method(0x060000FA,'Stores stable dongle identifier/display name and initializes license storage/invalidation/update flags.', params('dongleIdentifier','displayName'))
    method(0x06000104,'Stores parent link used by subordination chain.', params('parent'))
    method(0x06000106,'Sets invalidation flag and clears licenses only when true.', params('invalidated'))
    method(0x0600011A,'Stores feature label/value, null parent and recomputed checksum.', params('featureLabel','featureValue'))
    method(0x0600011B,'Checksum sums first16 ASCII label bytes followed by BitConverter UInt16 bytes, then returns bitwise complement of sum+1.', params('featureLabel','featureValue'), locals_('sum','checksumBytes','byteIndex','currentByte'))
    method(0x06000121,'Stores feature parent used for license membership.', params('parent'))
    method(0x06000126,'Feature aggregation selector controls observed maximum/minimum/mean/sum/first branches over unexpired licenses; preserves all sentinel and overflow cases.', params('featureLabel','licenses','aggregation'),
           locals_('resultValue','hasUnlimitedValue','finiteValueSum','licenseEnumerator','license','feature','firstValue'))
    method(0x06000137,'Constructs feature dictionary from definition, assigns feature parents and skips expired license initialization.', params('definition'), locals_('licenseKind','featureEnumerator','feature'))
    method(0x06000149,'Stores license parent used by subordination chain.', params('parent'))
    method(0x06000151,'Attaches payload when package name matches and licenses support feature population; preserves existing validation.', params('payload'), locals_('licenseKind','featureEnumerator','feature'))
    method(0x060002E0,'Sets local-mutex option then attempts native initialization.', params('useLocalMutex'))
    method(0x060002E5,'Writes local-mutex option only before initialization has been attempted.', params('useLocalMutex'))

    for number in [*range(0x74,0x80),*range(0x80,0x8A),0x90,0x91,*range(0x92,0xA0),*range(0x2D4,0x2DE)]:
        key = token(0x06000000 + number)
        if key not in aliases:
            continue
        body = instructions(0x06000000 + number)
        assert any('System.Threading.Interlocked::CompareExchange' in i['Operand'].get('Text','') for i in body if isinstance(i['Operand'],dict))
        method(0x06000000 + number,'Delegate Combine/Remove computes updatedHandlers from previousHandlers; CompareExchange returns currentHandlers and retries on disagreement. Slots3+ are unused boilerplate.', params('handler'), locals_('currentHandlers','previousHandlers','updatedHandlers'))

    changed_rows = []
    for row in rows:
        old = previous.get(row['Token'])
        if row['Kind'] == 'Methods' and old and not old.get('Unresolved') and row.get('NewName', '') == old.get('NewName', ''):
            old_scopes = {label:{str(c[position]):c.get('NewName') for c in old.get(label, [])}
                          for label,position in (('ParameterNames','Sequence'),('LocalNames','Index'))}
            if all(all(old_scopes[label].get(i) == name for i,name in row.get(label, {}).items()) for label in old_scopes):
                pending.append(dict(Token=row['Token'], Decision='Existing scopes retained', Review=row))
                continue
        changed_rows.append(row)
    rows = changed_rows
    spec = dict(Format=1,TargetRoot=state['Pass']['SourceTree63'],ContractReferenceSha256=state['Compatibility']['ContractReferences63']['Sha256'],Inventories=[r['Path'] for r in reports],Rows=rows)
    review = prepare(spec)
    for r in review['Methods']:
        old = previous.get(r['Token'])
        mapped = aliases.get(r['Token'])
        if old and mapped is not None and not old.get('Unresolved') and old.get('NewName', '') != mapped.get('NewName', ''):
            assert r['NewName'] != mapped.get('NewName') and r['Token'] == '0x06000138'
            r.update(PreviousLedgerAlias=old['NewName'], ExpectedMappedAlias=mapped.get('NewName'))
        if r['Token'] in ('0x060000C3','0x060000EC'):
            native_family = contract_rows[r['Token']]
            for key in ('Module','Token','Identity','Mvid','Sha256','Type','Signature','OriginalName'):
                assert r[key] == native_family[key]
            assert native_family['MappingBlocker'] is None and native_family['ContractFamily']
            family = native_family['ContractFamily']
            complete = [m for m in families['Methods'] if m.get('ContractFamily') == family]
            assert {(m['Module'],m['Token']) for m in complete} == {('Knx.CloudKit.dll','0x060000C3'),('Knx.CloudKit.dll','0x060000EC')}
            r.update(ContractFamily=family,MappingBlocker=None,ScopedMappingBlocker=None)
    assert len({(r['Kind'],r['Token']) for r in rows}) == len(rows)
    wanted = {r['Token'] for r in rows} | {r['Token'] for r in pending}
    remaining_fields = {r['Token'] for r in catalog['Fields'].values() if r['NeedsReadableName'] and r['Token'] not in aliases and r['Token'] not in previous}
    assert remaining_fields <= wanted
    out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=False)
    input_state=dict(Pass=dict(SourceTree63=state['Pass']['SourceTree63']),Maps={'63':state['Maps']['63']},Compatibility=dict(ContractReferences63=state['Compatibility']['ContractReferences63']))
    preimage=dict(Format=ledger['Format'],**{k:[r for r in ledger[k] if r['Module']=='Knx.CloudKit.dll' and (k=='Fields' or r['Token'] in wanted)] for k in ('Types','Fields','Methods')})
    evidence=dict(Format=1,PhysicalPath=str(physical),Sha256=digest(physical),Mvid=types['Mvid'],Map=state['Maps']['63']['Path'],MapSha256=inventory['MapSha256'],
                  Sources=[dict(Path=p,Sha256=digest(p)) for p in (*paths,args.families,args.graph)],GraphPhysicalInputsVerified=len(meta['Modules']),References=references,Closures=closures,
                  Methods=[methods[r['Token']] for r in rows if r['Kind']=='Methods'],RetainedReviewedScopes=pending,SupportingMethods=[methods[r['Token']] for r in pending],FieldStorage=[storage[r['Token']] for r in rows if r['Kind']=='Fields'],
                  ContractMembers=[contract_rows[t] for t in ('0x060000C3','0x060000EC')],
                  Limitations='Map-only review. Structural closure reconstruction is supported by owner/ldftn/capture evidence; full export/build/runtime and unchanged-App compatibility await consolidated verification. Runtime delegate entry-point scopes and other protected-family scopes remain pending.')
    for name,document in [('input-state',input_state),('ledger-preimage',preimage),('spec',spec),('review',review),('evidence',evidence)]:
        (out/f'cloud-owner-storage-{name}01.json').write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8')
    print('Prepared',{k:len(review[k]) for k in ('Types','Fields','Methods')},'closures',len(closures))


if __name__ == '__main__':
    main()
