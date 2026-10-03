"""Prepare physical CloudKit notification/dispatch reviews; never edit ETS code."""
import argparse
import json
import pathlib
import sqlite3
import xml.etree.ElementTree as ET
from prepare_cloud_crypto_review import read, digest
from prepare_physical_review import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('state', 'inventory', 'ledger', 'bodies', 'producer-bodies', 'session-bodies', 'consumer-bodies', 'types', 'fields', 'graph', 'output'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    state, inventory, ledger = read(args.state), read(args.inventory), read(args.ledger)
    paths = (args.bodies, args.producer_bodies, args.session_bodies, args.types, args.fields)
    documents = list(map(read, paths))
    bodies, producers, sessions, types, fields = documents
    physical = pathlib.Path(state['Pass']['SourceTree63']) / 'Knx.CloudKit.dll'
    physical_hash = digest(physical)
    for document in documents:
        assert pathlib.Path(document['Input']).resolve() == physical.resolve()
        assert document['Sha256'] == physical_hash and document['Mvid'] == bodies['Mvid']
        assert document['Identity'] == bodies['Identity']
    assert inventory['MapSha256'] == state['Maps']['63']['Sha256'] == digest(state['Maps']['63']['Path'])
    reports = [r for r in inventory['Reports'] if r['Module'] == 'Knx.CloudKit.dll']
    assert {r['Kind'] for r in reports} == {'Types', 'Fields', 'Methods'}
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    native = {kind: {r['Token']: r for report in reports if report['Kind'] == kind
                    for r in read(report['Path'])[kind]} for kind in ('Types', 'Fields', 'Methods')}
    methods = {m['Token']: m for document in (bodies, producers, sessions) for m in document['Methods']}
    storage = {f['Token']: f for f in fields['Fields']}
    current = next(m for m in ET.parse(state['Maps']['63']['Path']).getroot() if m.get('Path') == 'Knx.CloudKit.dll')
    aliases = {m.get('Token'): m for m in current}
    previous = {r['Token']: r for kind in ('Types', 'Fields', 'Methods') for r in ledger[kind] if r['Module'] == 'Knx.CloudKit.dll'}
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    module = next(m for m in meta['Modules'] if pathlib.Path(m['Input']).resolve() == physical.resolve())
    assert module['Sha256'] == physical_hash and module['Mvid'] == bodies['Mvid']
    consumer = read(args.consumer_bodies)
    consumer_module = next(m for m in meta['Modules'] if pathlib.Path(m['Input']).resolve() == pathlib.Path(consumer['Input']).resolve())
    assert consumer_module['Sha256'] == consumer['Sha256'] and consumer_module['Mvid'] == consumer['Mvid']
    caller = next(m for m in consumer['Methods'] if m['Token'] == '0x060001C0')
    assert any(i['OpCode'] == 'ldstr' and i['Operand'] == 'Received new session token' for i in caller['Instructions'])
    assert any(isinstance(i['Operand'], dict) and i['Operand'].get('Text') == 'System.String aj9::a()' for i in caller['Instructions'])
    rows, references, unresolved, retained, blockers = [], {}, [], [], []

    def token(number):
        return f'0x{number:08X}'

    def edges(number):
        key = token(number)
        result = [dict(Source=source, Reference=json.loads(data)) for source, data in graph.execute(
            'select source,data from edges where target=?', (module['Id'] + ':' + key,))]
        references[key] = result
        return result

    def add(kind, number, name, reason, parameters=None, locals_=None, disposition='rename', **annotations):
        key = token(number)
        row = dict(Kind=kind, Module='Knx.CloudKit.dll', Token=key, Reason=reason, Disposition=disposition)
        if name:
            row['NewName'] = name
        if parameters:
            row['ParameterNames'] = parameters
        if locals_:
            row['LocalNames'] = locals_
        old = previous.get(key)
        if old and old.get('Unresolved') and disposition == 'rename':
            assert name and not old.get('NewName') and key not in aliases
            annotations.update(ResolveExistingUnresolved=True,
                PreviousUnresolvedEvidence={k: old.get(k, '') for k in ('Reason', 'UnresolvedReason')})
        row.update(annotations)
        rows.append(row)

    def unknown(kind, number, reason):
        key = token(number)
        incoming = edges(number)
        reason = f'no-evidence-in-scope: {reason} Hash-checked physical graph has {len(incoming)} incoming edges across {len(meta["Modules"])} inputs; static analysis excludes reflection and external Apps.'
        unresolved.append(dict(Kind=kind, Token=key, MissingEvidence=reason))
        if previous.get(key, {}).get('Unresolved'):
            retained.append(dict(Token=key, PreviousDecision=previous[key], CurrentMissingEvidence=reason))
        else:
            assert key not in aliases
            add(kind, number, '', reason, disposition='unresolved')

    def field(number, name, reason, literal=False):
        assert storage[token(number)]['MappingBlocker'] is None
        assert edges(number) or literal
        add('Fields', number, name, reason + ' Storage/signature/value and runtime restoration names remain unchanged.')

    def params(*names):
        return {str(i + 1): name for i, name in enumerate(names) if name}

    def scopes(*names):
        return {str(i): name for i, name in enumerate(names) if name}

    def method(number, reason, parameters=None, locals_=None, name=None):
        key = token(number)
        assert methods[key]['HasBody']
        if native['Methods'][key]['ScopedMappingBlocker']:
            blockers.append(dict(Token=key, Signature=methods[key]['Signature'], ScopedMappingBlocker=native['Methods'][key]['ScopedMappingBlocker'],
                Evidence=reason, PendingParameters=parameters, PendingLocals=locals_,
                Limitation='Keep contract bindings; scope changes require full physical family review.'))
            return
        parameters, locals_ = dict(parameters or {}), dict(locals_ or {})
        old = aliases.get(key)
        if old is not None:
            if name is None:
                name = old.get('NewName')
            for child in old.findall('Parameter'):
                parameters.setdefault(child.get('Sequence'), child.get('NewName'))
            for child in old.findall('Local'):
                locals_.setdefault(child.get('Index'), child.get('NewName'))
        # An accepted definition with no new scopes needs no duplicate ledger row.
        prior = previous.get(key)
        if prior and not prior.get('Unresolved') and (not name or name == prior.get('NewName')):
            added = any(value != {str(p[pos]): p.get('NewName') for p in prior.get(label, [])}.get(slot)
                        for label, pos, requested in (('ParameterNames', 'Sequence', parameters), ('LocalNames', 'Index', locals_))
                        for slot, value in requested.items())
            if not added:
                retained.append(dict(Token=key, PreviousDecision=prior, CurrentEvidence=reason))
                return
        add('Methods', number, name, reason + ' Carry forward accepted scoped aliases; unused control/Int16 slots remain unnamed.', parameters, locals_)

    def called(number, target):
        assert any(isinstance(i['Operand'], dict) and i['Operand'].get('Token') == token(target)
                   for i in methods[token(number)]['Instructions']), (token(number), token(target))

    # The import producer increments successes/failures in distinct branches.
    for target in (0x06000012, 0x06000033, 0x06000034, 0x06000035, 0x0600004E, 0x0600004F):
        called(0x0600004A, target)
    assert any(i['Operand'] == '100' for i in methods['0x06000035']['Instructions'])
    for number, name, reason in [
        (0x02000006, 'CertificateProgressEventHandler', 'ai7 Invoke/BeginInvoke accept Object and ai9 CertificateEventArgs; import publisher0600004D delivers certificate-registration progress.'),
        (0x02000007, 'CertificateImportStatus', 'ai8 discriminator belongs to ai9 progress args; import0600004A selects separate registration-success/failure constructors and start/completion publishers.'),
        (0x0200000E, 'CloudResultEventHandler', 'aje Invoke/BeginInvoke accept Object and ajf, whose only payload is the ajd result wrapper. Preserve runtime delegate entry points.'),
        (0x0200000F, 'CloudResultEventArgs', 'ajf derives EventArgs, accepts ajd or wraps raw Int32 in ajd, exposes that result; no unsupported operation-specific purpose assigned.'),
        (0x02000016, 'CloudDongleEventHandler', 'aji Invoke/BeginInvoke accept Object and ajj EventArgs containing ajh dongle and its license-count accessor.'),
        (0x02000017, 'CloudDongleEventArgs', 'ajj constructors store ajh, optional Int64; getters return dongle and its ajq collection count. Int64 purpose/unit is explicitly unresolved.'),
        (0x0200001F, 'CloudLicenseProgressEventHandler', 'ajs Invoke/BeginInvoke accept Object and aju ProgressChangedEventArgs containing ajr definition/list/status/label. Preserve delegate methods.'),
        (0x02000021, 'CloudLicenseProgressEventArgs', 'aju derives ProgressChangedEventArgs; typed definition/status/label/completion/list roles are visible even without callers. Four Int32 roles remain unresolved.'),
        (0x02000022, 'CloudLicenseEventHandler', 'ajv Invoke/BeginInvoke accept Object and ajw LicenseEventArgs, which stores label and license/dongle identifier. Boolean purpose remains unresolved.'),
        (0x02000024, 'CloudManagerEventHandler', 'ajx Invoke/BeginInvoke accept Object and ajy manager payload; enumeration start/completion and additional manager changes publish it.'),
        (0x02000025, 'CloudManagerEventArgs', 'ajy holds ajo manager, enumeration-completed flag, Stopwatch.ElapsedMilliseconds and ajd result. Also used for other manager changes; retain shared payload.'),
        (0x02000071, 'CloudSessionTokenEventHandler', 'aj8 Invoke/BeginInvoke accept Object and aj9 payload. Producer060000C0 decrypts changed native output; hash-checked Common arx060001C0 logs Received new session token then reads this event payload.'),
        (0x02000072, 'CloudSessionTokenEventArgs', 'aj9 holds changed native output from publisher060000B0. Exact Common arx060001C0 getter consumer logs Received new session token and forwards it to ar7; token validity/authentication behavior is not claimed.')]:
        assert token(number) not in aliases
        add('Types', number, name, reason)

    for number, value, name, constructor in [
        (0x04000023, 0, 'Registered', 0x06000033), (0x04000024, 1, 'RegistrationFailed', 0x06000034),
        (0x04000025, 2, 'Started', 0x06000032), (0x04000026, 3, 'Completed', 0x06000035)]:
        assert storage[token(number)]['Constant'] == value
        instructions = methods[token(constructor)]['Instructions']
        index = next(i for i, inst in enumerate(instructions) if inst['OpCode'] == 'stfld' and inst['Operand']['Token'] == '0x0400002A')
        assert instructions[index - 1]['OpCode'] == 'ldc.i4.' + str(value)
        field(number, name, f'Enum literal {value} stored by{token(constructor)}; full import/start/completion caller bodies establish this phase, preserving exact original value.', literal=True)

    for number, name, reason in [
        (0x04000027, 'totalCertificateCount', '0600004A local2=Enumerable.Count(parsed certificates), passed as total to all ai9 constructors.'),
        (0x04000028, 'registeredCertificateCount', '0600004A local3 increments only after certificate.TryRegister06000012 returns true; constructor/getter store/expose that count.'),
        (0x04000029, 'failedCertificateCount', '0600004A local4 increments only after TryRegister false; success/failure/completion constructors receive it.'),
        (0x0400002A, 'status', 'Constructor32 sets Started2,33 Registered0,34 RegistrationFailed1,35 Completed3; getter36 returns ai8.'),
        (0x0400002B, 'isCompleted', 'Only completion constructor35 sets true, at ProgressPercentage100; other constructors false, getter37 returns it.'),
        (0x0400002C, 'certificateName', 'Successful registration branch obtains ai6.GetName0600000B and supplies constructor33 arg5; others store String.Empty.'),
        (0x0400003C, 'changeTimestamp', 'ajc constructor62 stores DateTime.Now; direct timestamp getter63 preserves local time.'),
        (0x0400003D, 'nativeLibraryInstanceCount', 'Class8 publisher1A1 supplies Windows loader Interlocked.Read user/instance count060001D3 to ctor62 arg1; getter64 returns it, not duration.'),
        (0x04000041, 'resultCode', 'ajd stores defined aj7 result enum or fallback1023/599 from raw code; ctor68 stores supplied enum directly.'),
        (0x04000042, 'nativeCode', 'ajd ctor67 retains supplied Int32 even when normalized enum differs; ctor68 casts enum to Int32.'),
        (0x04000045, 'result', 'ajf ctor70 stores ajd; ctor71 constructs it from Int32; getter72 and ToString73 consume same result.'),
        (0x04000082, 'dongle', 'ajj ctor115/116 stores ajh argument1; getter117 returns it and119 reads ajq collection count through060000FC, zero for null.'),
        (0x040000C3, 'isCompleted', 'aju definition-progress ctor175 sets false; terminal ctor176 sets true with base progress100 and empty definition.'),
        (0x040000C4, 'licenseDefinition', 'aju ctor175 stores ajr definition; ctor176 creates empty definition; getters177/17A/17B and setter178 use typed definition semantics.'),
        (0x040000C5, 'licenseDefinitions', 'Both aju constructors create List<ajr>; getter180 returns it and setter181 stores supplied list.'),
        (0x040000C6, 'licenseLabel', 'aju ctor175 stores definition.GetLabel06000163; terminal ctor176 stores String.Empty. Getter17A reads live definition label, not this cached field.'),
        (0x040000C9, 'licenseLabel', 'ajw constructors186/187 store supplied ajq.GetLabel06000143 if nonnull, otherwise Empty; getter188 returns it.'),
        (0x040000CA, 'identifier', 'ajw ctor186 stores license identifier0600013A; ctor187 stores dongle identifier060000FD. Shared field/getter intentionally covers both identities.'),
        (0x040000CE, 'cloudManager', 'ajy constructors190/191 store ajg argument as ajo manager; getter192 returns it and195 delegates dongle count.'),
        (0x040000CF, 'isEnumerationCompleted', 'Only ctor191 sets true; sole producer060000AB completes native dongle enumeration/update/clear in060000C0. Shared simpler ctor190 sets false.'),
        (0x040000D0, 'elapsedMilliseconds', '060000C0 feeds Stopwatch.ElapsedMilliseconds into060000AB and ctor191 arg2; getter194 returns that duration unchanged.'),
        (0x040000D1, 'result', 'ajy ctor191 stores ajd arg3, ctor190 creates raw-zero ajd; getter196 returns it.'),
        (0x040001E5, 'sessionToken', '060000C0 decrypts changed native output andB0 supplies ctor344; getter345 consumer Common arx060001C0 logs Received new session token and forwards it to ar7.'),
        (0x040001F1, 'asyncProbeHandlers', 'Class13 cctor subscribes no-op handler358, calls EventHandler.BeginInvoke, then unsubscribes;355/356 CAS update this probe chain.'),
        (0x040001F2, 'supportsAsyncDelegateInvocation', 'Class13 cctor sets true only if BeginInvoke returns without throwing, false on catch; setters35A/35C are gated by it. Does not prove callback completion.'),
        (0x040001F3, 'useSynchronousCloudEvents', 'Publishers4D,AA,AB,B0 and other event chains read359 to choose Invoke vs BeginInvoke; cctor forces true when async probe throws.')]:
        field(number, name, reason)

    for number, reason in [
        (0x04000083, 'ajj optional Int64 has no constructor callers or semantic consumers; units and purpose missing.'),
        *[(n, 'aju Int32 constructor slots have no callers or nontrivial consumers; total/success/failure/count associations unproven.') for n in range(0x040000BF, 0x040000C3)],
        (0x040000CB, 'ajw Boolean input is stored/read/inverted, but neither constructor has callers; default/custom time-setting association lacks evidence.'),
        (0x040001F4, 'Additional Class13 Boolean option is initialized true and exposed by35B/35C/35D; all three have zero callers. No package/device dispatch behavior establishes its purpose.')]:
        unknown('Fields', number, reason)
    for number in (0x04000021, 0x04000044, 0x04000046, 0x04000081, 0x04000084, 0x040000BA,
                   0x040000C7, 0x040000C8, 0x040000CD, 0x040000D2, 0x040001E4, 0x040001E6, 0x040001F5):
        assert storage[token(number)]['ConstantType'] == 'I1' and storage[token(number)]['Constant'] == 32 and not edges(number)
        unknown('Fields', number, 'String field carries I1(32) constant metadata but is not literal and has no managed token references or observed reads/writes; association to an observable declaration role missing.')

    count_params = ('totalCertificateCount', 'registeredCertificateCount', 'failedCertificateCount')
    for number, names in [(0x06000032, count_params[:1]), (0x06000033, ('progressPercentage', *count_params, 'certificateName')),
                          (0x06000034, ('progressPercentage', *count_params)), (0x06000035, count_params)]:
        method(number, 'Coupled import0600004A and certificate-name getter establish constructor counts/progress/name; phase values kept.', params(*names))
    method(0x06000038, 'Returns successful-registration certificate-name field2C; other phases use Empty. Correct generic detail alias to observed name.', name='GetCertificateName')
    for number, name, field_token in [(0x06000039, 'GetTotalCertificateCount', '0x04000027'),
                                    (0x0600003A, 'GetRegisteredCertificateCount', '0x04000028'),
                                    (0x0600003B, 'GetFailedCertificateCount', '0x04000029')]:
        assert [i['Operand']['Token'] for i in methods[token(number)]['Instructions'] if i['OpCode'] == 'ldfld'] == [field_token]
        method(number, 'Direct count getter now resolved through complete import producer0600004A and exact constructor fields; retain previous missing-producer decision as history.', name=name)
    method(0x06000062, 'Publisher1A1 passes native library instance count as argument1. Boolean role remains outside this review.', {'1': 'nativeLibraryInstanceCount'})
    method(0x06000067, 'Constructor preserves raw Int32 and normalizes known enum/fallback1023/599; parameter is native result code.', params('nativeCode'))
    method(0x06000068, 'Constructor stores typed aj7 result and its Int32 representation.', params('resultCode'))
    method(0x06000070, 'Stores supplied ajd result unchanged.', params('result'))
    method(0x06000071, 'Constructs ajd result wrapper from supplied native Int32.', params('nativeCode'))
    for number in (0x06000115, 0x06000116):
        method(number, 'Typed ajh input is stored and returned; optional Int64 lacks producer/unit evidence and remains unnamed.', {'1': 'dongle'})
    method(0x06000175, 'Base progressPercentage and typed definition are proven by base constructor and label/status methods. Four Int32 fields have no producer roles.', params('progressPercentage', 'licenseDefinition'))
    for number, name in [(0x06000177, 'GetProgressStatus'), (0x06000178, 'SetDefinitionStatus'),
                         (0x06000179, 'IsCompleted'), (0x0600017A, 'GetLicenseLabel'),
                         (0x0600017B, 'GetLicenseDefinition'), (0x06000180, 'GetLicenseDefinitions'),
                         (0x06000181, 'SetLicenseDefinitions')]:
        method(number, 'Typed aju field/definition calls resolve this operation despite no callers. Empty definition returns status0/2 or Empty label; status setter ignores empty definition. Preserve those branches.',
               params('status') if number == 0x06000178 else params('licenseDefinitions') if number == 0x06000181 else None, name=name)
    for number in range(0x0600017C, 0x06000180):
        unknown('Methods', number, 'Direct Int32 getter over unknown aju constructor slot; no caller or count-specific behavior supplies its meaning.')
    unknown('Methods', 0x06000118, 'ajj EventArgs optional Int64 getter has no callers; duration/count semantics and units missing. It is not a license ProgressChangedEventArgs record.')
    method(0x06000186, 'License label/identifier getters establish ajq input; Boolean role remains unresolved.', {'1': 'license'})
    method(0x06000187, 'Dongle/ajq inputs supply dongle identifier and license label; Boolean role remains unresolved.', params('dongle', 'license'))
    method(0x06000190, 'Stores typed manager; creates raw-zero result and false enumeration-completed flag.', params('cloudManager'))
    called(0x060000C0, 0x060000AB)
    assert any(isinstance(i['Operand'], dict) and 'get_ElapsedMilliseconds' in i['Operand'].get('Text', '') for i in methods['0x060000C0']['Instructions'])
    method(0x06000191, 'Native enumeration060000C0 passes Stopwatch.ElapsedMilliseconds and ajd outcome via publisherAB; constructor marks enumeration complete.', params('cloudManager', 'elapsedMilliseconds', 'result'))
    method(0x06000344, 'Native change publisherB0 passes decrypted changed session token; Common arx060001C0 literal corroborates token role. Preserve actual text without claiming validity.', params('sessionToken'))
    method(0x06000345, 'Directly returns session-token field1E5; full physical Common consumer logs Received new session token and forwards the getter result. Preserve meaningful GetToken alias.')
    for number in (0x06000355, 0x06000356):
        method(number, 'CAS async-probe chain update; local0 current chain,1 expected preimage,2 combined/removed chain; unused controls excluded.', params('handler'), scopes('currentHandlers', 'expectedHandlers', 'updatedHandlers'))

    method(0x0600004A, 'Complete import: Count parsed certificates; local3 increments on TryRegister true and4 on false, percentage=(success+failure)*100/total; local5 certificates,6 enumerator,7 certificate. Retain catch/dispose behavior.',
           params('certificateText', 'progressCallback'), scopes('importLock', 'lockTaken', 'totalCertificateCount', 'registeredCertificateCount', 'failedCertificateCount', 'certificates', 'certificateEnumerator', 'certificate'))
    method(0x0600004D, 'Publishes both supplied callback invocation list and shared certificate-progress subscribers; Monitor protects snapshot, handler exceptions ignored and Class13 selects Invoke/BeginInvoke.',
           params('eventArgs', 'progressCallback'), scopes('handlers', 'invocationList', 'handlerIndex', 'callbackDelegate', 'callback', 'eventLock', 'lockTaken', 'handlerDelegate', 'handler'))
    for number in (0x060000AA, 0x060000AB, 0x060000AD, 0x060000AE, 0x060000AF, 0x060000B0):
        method(number, 'Monitor snapshots the exact event handler chain; invocation list iteration and Class13 synchronous/async dispatch preserve existing producer meaning.',
               params('elapsedMilliseconds', 'result') if number == 0x060000AB else params('sessionToken') if number == 0x060000B0 else None,
               scopes('handlers', 'eventLock', 'lockTaken', 'invocationList', 'handlerIndex', 'handlerDelegate', 'handler'))

    for number, reason in [
        (0x0600018A, 'Negates ajw BooleanCB; constructors have zero callers and no time-setting behavior. Default time-setting name unsupported.'),
        (0x0600018B, 'Directly reads ajw BooleanCB; constructors have zero callers and no time-setting behavior. Custom time-setting name unsupported.'),
        (0x0600035B, 'Reads additional Class13 option1F4; no callers or package behavior.'),
        (0x0600035C, 'Stores additional option1F4 only if async probe succeeds; no callers or package behavior.'),
        (0x0600035D, 'Returns option1F4 AND synchronous-events1F3; no callers or device/package behavior.')]:
        incoming = edges(number)
        assert not incoming and not methods[token(number)]['IncomingReferences']
        assert aliases[token(number)].get('NewName') and len(aliases[token(number)]) == 0
        add('Methods', number, '', 'no-evidence-in-scope: ' + reason + f' All {len(meta["Modules"])} physical graph inputs checked. Retain unresolved operation/trigger purpose; withdraw unsupported alias.',
            disposition='unresolved', RemoveExistingAlias=True, ExpectedAlias=aliases[token(number)].get('NewName'))

    for key, body in methods.items():
        original = native['Methods'][key]
        if original['Type'] in {'ajf', 'ajd', 'ajj', 'aju', 'ajy'} and original['ScopedMappingBlocker']:
            blockers.append(dict(Token=key, Signature=body['Signature'], ScopedMappingBlocker=original['ScopedMappingBlocker'],
                Limitation='Preserve runtime/framework overrides; scope changes require full family review.'))
    assert len({(r['Kind'], r['Token']) for r in rows}) == len(rows)
    spec = dict(Format=1, TargetRoot=state['Pass']['SourceTree63'], ContractReferenceSha256=state['Compatibility']['ContractReferences63']['Sha256'], Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    input_state = dict(Pass=dict(SourceTree63=state['Pass']['SourceTree63']), Maps={'63': state['Maps']['63']}, Compatibility=dict(ContractReferences63=state['Compatibility']['ContractReferences63']))
    preimages = dict(Format=ledger['Format'], Types=[], Fields=[], Methods=[])
    for kind in ('Types', 'Fields', 'Methods'):
        preimages[kind] = [r for r in ledger[kind] if r['Module'] == 'Knx.CloudKit.dll' and (r['Token'] in {row['Token'] for row in rows} or r['Token'] in {r['Token'] for r in retained})]
    for name, document in [('cloud-notifications-input-state01.json', input_state), ('cloud-notifications-ledger-preimage01.json', preimages),
            ('cloud-notifications-spec01.json', spec), ('cloud-notifications-review01.json', review), ('cloud-notifications-evidence01.json', dict(
        Format=1, PhysicalPath=str(physical), Sha256=physical_hash, Mvid=bodies['Mvid'], Map=state['Maps']['63']['Path'], MapSha256=inventory['MapSha256'],
        Sources=[dict(Path=path, Sha256=digest(path)) for path in (*paths, args.consumer_bodies, args.graph)], GraphPhysicalInputsVerified=len(meta['Modules']),
        References=references, RemainingUnresolved=unresolved, RetainedDecisions=retained, ScopedMappingBlockers=blockers,
        Methods=[methods[r['Token']] for r in rows if r['Kind'] == 'Methods'], ExternalConsumers=consumer['Methods'], FieldStorage=[storage[r['Token']] for r in rows if r['Kind'] == 'Fields'],
        Limitations='Native map checks mandatory. Static graph excludes reflection/dynamic/external Apps. No ETS source/binary patched; consolidated build/runtime pending.'))]:
        (output / name).write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print('Prepared', {k: len(review[k]) for k in ('Types', 'Fields', 'Methods')}, 'retained unresolved', len(retained), 'protected scopes', len(blockers))


if __name__ == '__main__':
    main()
