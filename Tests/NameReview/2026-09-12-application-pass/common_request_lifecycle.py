"""Stage reviewed request, dongle collection and nested ZIP naming decisions.

Usage: python common_request_lifecycle.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only identity-bound map proposals/evidence are written; no ETS code is executed.
"""
import json
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


class Review:
    def __init__(self, root, version):
        old = version == '63'
        self.b = BehaviorReview(root, version, 197 if old else 29,
                                'm0039' if old else 'm0102',
                                'http63-wave196' if old else 'security64-wave29',
                                root / ('security63-wave197-rev3.cumulative.json' if old else 'security64-wave29-rev3.cumulative.json'))
        path = root / ('common63-wave198-full-inspection.json' if old else 'zip64-wave30-inspection.json')
        report = self.b.read(path.name)
        assert Path(report['Input']).resolve() == Path(self.b.module['Input']).resolve()
        assert all(report[k] == self.b.module[k] for k in ('Mvid', 'Sha256'))
        self.bodies = {int(m['Token'], 16): m for m in report['Methods']}
        self.il = {'Path': str(path), 'Sha256': sha(path)}
        self.families = self.b.read('common63-wave198-selected-families.json') if old else None
        if old:
            assert self.families['ContractReferenceSha256'] == self.b.delta['ContractReferenceSha256']

    def method(self, rid, name, reason, parameters=None, locals_=None, replace=None, family=False):
        token = 0x06000000 + rid
        row, body = self.b.entries['Methods'][f'0x{token:08X}'], self.bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in locals_ or {}:
            expected = next(l['ExpectedType'] for l in row['LocalNames'] if l['Index'] == slot)
            assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
        contract = next(r for r in self.families['Methods'] if r['Module'] == self.b.relative and r['Token'] == row['Token']) if family else None
        self.b.add('Methods', token, name, reason, parameters, locals_, contract=contract, replace_alias=replace)
        assert not self.b.pending, self.b.pending
        self.b.decisions[-1]['IL'] = {**self.il, 'Token': row['Token'], 'Slots': locals_ or {}}

    def symbol(self, kind, rid, name, reason, proof, literal=False):
        token = (0x04000000 if kind == 'Fields' else 0x02000000) + rid
        if kind == 'Fields':
            symbol = json.loads(self.b.db.execute('SELECT data FROM symbols WHERE id=?', (self.b.module_id + f':0x{token:08X}',)).fetchone()[0])
            assert symbol['IsLiteral'] == literal
            if not literal:
                found = []
                for raw, in self.b.db.execute('SELECT data FROM edges WHERE target=?', (self.b.module_id + f':0x{token:08X}',)):
                    edge = json.loads(raw)
                    if not edge['From'].startswith(self.b.module_id + ':'):
                        continue
                    caller = int(edge['From'].split(':')[1], 16)
                    if caller not in {0x06000000 + rid for rid in proof}:
                        continue
                    actual = next(i for i in self.bodies[caller]['Instructions'] if i['Offset'] == edge['Offset'])
                    assert actual['OpCode'] == edge['Operation'] and actual['Operand']['Text'] == edge['Target']['Signature']
                    assert Path(edge['Target']['PhysicalModule']).resolve() == Path(self.b.module['Input']).resolve()
                    found.append(edge)
                assert found, ('No inspected field use', token)
        self.b.add(kind, token, name, reason, evidence=[0x06000000 + rid for rid in proof])
        assert not self.b.pending, self.b.pending
        self.b.decisions[-1]['IL'] = {**self.il, 'SupportingTokens': [f'0x{0x06000000 + rid:08X}' for rid in proof], 'LiteralDeclarationEvidence': literal}


def stage(root, stem63, stem64):
    r = Review(root, '63')
    m, s = r.method, r.symbol
    m(0x32, None, 'Retains a nonnull logger and pooled client factory plus the header inclusion policy passed to AcquireClient.', ('log', 'httpClientFactory', 'includeRedirectHeader'))
    for rid, name, proof in [(0x1A, 'includeRedirectHeader', (0x32,)), (0x1B, 'httpClientFactory', (0x32,)), (0x1C, 'log', (0x32, 0x33))]:
        s('Fields', rid, name, 'Constructor input consumed by the reviewed request path.', proof)
    m(0x49, 'InvokeResponseErrorHandlerAsync', 'Invokes the captured synchronous response handler, then wraps its return value with Task.FromResult. It does not read response content or catch handler exceptions.', ('response',), replace='ReadResponseErrorAsync')
    s('Types', 0x10, 'ResponseErrorTaskAdapter', 'Adapts a synchronous response error factory to the task-returning overload.', (0x3E, 0x49))
    s('Fields', 0x1E, 'responseErrorHandler', 'Delegate retained by the adapter and invoked before Task.FromResult.', (0x3E, 0x49))
    for rid, name, parameters, local, reason in [
        (0x3D, 'SendRequestAsync', ('uri', 'method', 'responseErrorHandler', 'cancellationToken', 'requestBody'), None, 'Constructs a Uri from the string then delegates to the virtual Uri overload.'),
        (0x3E, 'SendUriRequestAsync', ('uri', 'method', 'responseErrorHandler', 'cancellationToken', 'requestBody'), {0: 'errorHandlerAdapter'}, 'Captures the synchronous error handler in a task adapter and forwards to the asynchronous error-handler overload.'),
        (0x40, 'CreateJsonRequestMessage', ('uri', 'method', 'requestBody'), {0: 'request'}, 'Creates a request and, only for a nonnull body, serializes JSON into UTF-8 application/json content.')]:
        family = next(x['ContractFamily'] for x in r.families['Methods'] if x['Module'] == r.b.relative and int(x['Token'], 16) == 0x06000000 + rid)
        assert len([x for x in r.families['Methods'] if x['ContractFamily'] == family]) == 1
        m(rid, name, reason, parameters, local, family=True)
    m(0x3A, 'CreateHttpStatusError', 'Maps status 500 to KnxApiError; all other statuses produce a WebServiceError containing status and reason phrase.', ('response',), replace='RequestFailedWithStatusCodeError')
    for rid, reason in [(0x3B, 'Forwards the absolute Uri string to the generic content-result overload.'), (0x3C, 'Sends GET, propagates a failed HTTP Result, or decodes successful content through ReadContentAsync<T> and returns Result.Ok<T>. The inner read preserves strings and deserializes other types as JSON.')]:
        m(rid, 'GetResponseValueAsync', reason, ('uri', 'responseErrorHandler', 'cancellationToken'), replace='GetFromServerAsync2')

    # Start with the setter and collection helpers, then their event callers.
    m(0x1AB, 'SetIsInitialized', 'Stores the supplied boolean in the initialization backing field; contains no disposal operation.', ('isInitialized',), replace='Dispose2')
    m(0x1E6, 'AddReadyDongleAndUnsubscribe', 'Unsubscribes this callback from the captured DevKit dongle readiness event and appends a new EtsDongle wrapper to its manager collection.', ('sender', 'eventArgs'), replace='HandleDongleCollectionChanged')
    m(0x1B8, 'AddDongleWhenReady', 'Adds an EtsDongle wrapper immediately when the DevKit ready flag is true, otherwise subscribes a callback that adds it once the event fires.', ('dongle',), {0: 'registration'}, replace='AttachDongleManager')
    dependency_path = root / 'common63-wave198-devkit-inspection.json'
    dependency = r.b.read(dependency_path.name)
    manifest = json.loads(r.b.db.execute('SELECT data FROM meta').fetchone()[0])
    devkit = next(x for x in manifest['Modules'] if x['Id'] == 'm0036')
    assert Path(dependency['Input']).resolve() == Path(devkit['Input']).resolve()
    assert sha(dependency['Input']) == dependency['Sha256'] == devkit['Sha256']
    assert dependency['Mvid'] == devkit['Mvid']
    sources = []
    for token in (0x24, 0x25, 0x68, 0x73, 0xA5, 0xA6):
        sid = f'm0036:0x0600{token:04X}'
        rows = [json.loads(x[0]) for x in r.b.db.execute('SELECT data FROM source WHERE id=?', (sid,))]
        assert rows
        for row in rows:
            assert sha(r.b.source_root / row['Source']) == row['Sha256']
            sources.append({'Id': sid, 'Path': row['Source'], 'Line': row['Line'], 'Sha256': row['Sha256']})
    for decision in r.b.decisions[-2:]:
        decision['DependencyEvidence'] = {'Inspection': str(dependency_path), 'Sha256': sha(dependency_path), 'Sources': sources}
    for rid, name, parameters, reason in [
        (0x1D0, 'HandleInitialized', ('sender', 'eventArgs'), 'Sets the manager initialization flag to true.'),
        (0x1D1, 'HandleDongleAttached', ('sender', 'dongleEvent'), 'Passes the event dongle to AddDongleWhenReady.'),
        (0x1D2, 'HandleDongleRemoved', ('sender', 'dongleEvent'), 'Removes the collection entry whose identifier matches the event identifier.'),
        (0x1D3, 'HandleDongleLocked', ('sender', 'dongleEvent'), 'Wraps the event dongle and emits DongleLocked.'),
        (0x1D4, 'HandleDongleUnlocked', ('sender', 'dongleEvent'), 'Wraps the event dongle and emits DongleUnlocked.'),
        (0x1D5, 'HandleSignatureValidationFailed', ('sender', 'eventArgs'), 'Formats the sender signature type and sender value into invalid-signature event arguments.')]:
        m(rid, name, reason, parameters)
    m(0x1AF, 'InitializeAsync', 'Registers callbacks, creates DevKit/CloudKit managers, adds initial dongles and cloud headers, and subscribes to cloud events. Work is synchronous and returns Task.CompletedTask.', (), {0: 'dongleEnumerator', 1: 'dongle', 2: 'headerEnumerator', 3: 'header'})

    # Exact two-member managed contract families, including every interface row.
    for members, name, parameters, reason, local in [
        ((0x1B4, 0x1D6), 'StartCloudSession', ('sessionId', 'token'), 'Validates nonblank session ID/token and starts the cloud session; sets the active flag only when CloudKit reports success.', None),
        ((0x1B5, 0x1D7), 'PauseCloudSession', (), 'Requires an active session; tries pause up to five times with blocking exponential delays and clears the flag only after a nonempty token is returned.', {0: 'sessionToken', 1: 'paused', 2: 'attempt'}),
        ((0x1B6, 0x1D8), 'ResumeCloudSession', ('token',), 'Rejects an already active session, forwards the token to CloudKit and sets the flag on success.', None),
        ((0x1B7, 0x1D9), 'StopCloudSession', (), 'Stops through CloudKit and clears the active flag when the returned token is nonnull, including an empty string.', {0: 'sessionToken'}),
        ((0x1CC, 0x1DA), 'SubscribeNewSessionToken', ('handler',), 'Atomically combines a handler into the delegate field consumed by EmitNewSessionToken.', {0: 'currentHandlers', 1: 'expectedHandlers', 2: 'updatedHandlers'}),
        ((0x1CD, 0x1DB), 'UnsubscribeNewSessionToken', ('handler',), 'Atomically removes a handler from the delegate field consumed by EmitNewSessionToken.', {0: 'currentHandlers', 1: 'expectedHandlers', 2: 'updatedHandlers'})]:
        seed = next(x for x in r.families['Methods'] if x['Module'] == r.b.relative and int(x['Token'], 16) == 0x06000000 + members[0])
        rows = [x for x in r.families['Methods'] if x['ContractFamily'] == seed['ContractFamily']]
        assert {int(x['Token'], 16) - 0x06000000 for x in rows} == set(members) and all(x['Module'] == r.b.relative for x in rows)
        for rid in members:
            m(rid, name, reason, parameters, local if rid == members[0] else None, family=True)
    for rid, name in [(0x1C6, 'SubscribeDongleLocked'), (0x1C7, 'UnsubscribeDongleLocked'), (0x1C8, 'SubscribeDongleUnlocked'), (0x1C9, 'UnsubscribeDongleUnlocked'), (0x1CA, 'SubscribeInvalidDongleSignature'), (0x1CB, 'UnsubscribeInvalidDongleSignature')]:
        m(rid, name, 'Atomic delegate add/remove loop on the exact field used by the corresponding reviewed event emitter.', ('handler',), {0: 'currentHandlers', 1: 'expectedHandlers', 2: 'updatedHandlers'})

    for rid, name, proof in [
        (0x127, 'log', (0x1AF, 0x1C3)), (0x128, 'donglesSyncLock', (0x1C4,)),
        (0x12B, 'licensingDataPoints', (0x1AE, 0x1C2)), (0x12C, 'configuration', (0x1AE, 0x1AF)),
        (0x12D, 'cloudManager', (0x1AF, 0x1B4)), (0x12E, 'dongleManager', (0x1AF, 0x1AC)),
        (0x12F, 'isCloudSessionActive', (0x1B4, 0x1B5, 0x1B6, 0x1B7, 0x1CE)),
        (0x130, 'dongles', (0x1A9,)), (0x131, 'isInitialized', (0x1AA, 0x1AB)),
        (0x132, 'cloudEnumerationGate', (0x1B0, 0x1CE)),
        (0x133, 'dongleLocked', (0x1BC, 0x1C6)), (0x134, 'dongleUnlocked', (0x1BD, 0x1C8)),
        (0x135, 'invalidDongleSignature', (0x1BE, 0x1CA)), (0x136, 'newSessionToken', (0x1BF, 0x1CC))]:
        s('Fields', rid, name, 'Storage role established by the inspected initialization, event dispatch, session lifecycle or synchronization operations.', proof)

    for rid, old in [(0x1DE, '<EnumerateLicensesByFeatureName>b__26_0'), (0x1DF, '<EnumerateLicensesByFeatureName>b__26_1')]:
        m(rid, 'CreateEtsLicense', 'Constructs an EtsLicense wrapper from the supplied DevKit or CloudKit license; the two overloads preserve their distinct parameter types.', ('license',), replace=old)
    m(0x1E0, 'IsSoftwareDongle', 'Compares EtsDongle.Type specifically with LicenseType.SoftwareDongle.', ('dongle',), replace='IsLicenseTypeMatch')
    m(0x1E1, 'GetDongleIdentifier', 'Returns EtsDongle.DongleID.', ('dongle',))
    m(0x1E2, 'GetCloudDongleIdentifier', 'Returns the CloudKit identifier used by collection comparisons.', ('cloudDongle',))
    m(0x1E4, 'ProcessCloudKitResult', 'Enumerates CloudKit, reports non-OK results, refreshes the wrapper collection and completes the retained TaskCompletionSource with the mapped result/count.', (), {0: 'enumerationResult', 1: 'dongleCount'})
    for rid, name, parameters, reason in [
        (0x1E8, 'IsMatchingDongleIdentifier', ('dongle',), 'Matches a wrapper ID with the captured replacement CloudKit dongle ID.'),
        (0x1EA, 'IsDongleIdentifierMatch', ('dongle',), 'Matches a wrapper ID against the captured removal ID.'),
        (0x1EC, 'IsCloudDongleIdentifierMatch', ('cloudDongle',), 'Matches an enumerated CloudKit ID against the captured ID for an existing entry.'),
        (0x1EE, 'IsCloudDongleIdentifierMatch', ('cloudDongle',), 'Matches an enumerated CloudKit ID against the captured ID of a newly discovered entry.'),
        (0x1F0, 'IsDongleIdentifierEqual', ('dongle',), 'Matches the wrapper ID selected for replacement by a cloud error state.')]:
        m(rid, name, reason, parameters, replace='IsCloudDongleNameMatch' if rid == 0x1EE else None)
    for rid, name, local in [
        (0x1BA, 'ReplaceChangedCloudDongle', {0: 'lookup', 1: 'existingDongle', 2: 'dongleIndex', 3: 'replacementDongle'}),
        (0x1BB, 'RemoveDongleByIdentifier', {0: 'lookup', 1: 'dongle'}),
        (0x1C3, 'RefreshCloudDonglesFromEnumerationResult', {0: 'cloudDongles', 1: 'dongleCount', 2: 'error'}),
        (0x1C4, 'SynchronizeCloudDongleCollection', {0: 'syncLock', 1: 'lockTaken', 2: 'existingIds', 3: 'enumeratedIds', 4: 'idEnumerator', 5: 'removedId', 6: 'existingLookup', 7: 'changedDongle', 8: 'existingIdEnumerator', 9: 'failedId', 10: 'newLookup', 11: 'newDongle'}),
        (0x1C5, 'ReplaceCloudDongleWithErrorState', {0: 'lookup', 1: 'existingDongle', 2: 'dongleIndex'})]:
        m(rid, name, 'Names actual IL locals in the reviewed identifier-based collection update path; TLS_Error preserves existing IDs and replaces wrappers with error state.', locals_=local)
    for rid, name, proof in [
        (0x62, 'DongleSelectors', (0x1DE, 0x1DF, 0x1E0, 0x1E1, 0x1E2)),
        (0x63, 'CloudEnumerationCompletion', (0x1E4,)), (0x64, 'PendingDongleRegistration', (0x1B8, 0x1E6)),
        (0x65, 'ChangedCloudDongleLookup', (0x1BA, 0x1E8)), (0x66, 'RemovedDongleLookup', (0x1BB, 0x1EA)),
        (0x67, 'ExistingCloudDongleLookup', (0x1C4, 0x1EC)), (0x68, 'NewCloudDongleLookup', (0x1C4, 0x1EE)),
        (0x69, 'FailedCloudDongleLookup', (0x1C5, 0x1F0))]:
        s('Types', rid, name, 'Captured operation or selectors used by the reviewed dongle collection call chain.', proof)
    for rid, name, proof in [
        (0x138, 'instance', (0x1C4,)), (0x139, 'createDongleLicense', (0x1B3,)), (0x13A, 'createCloudLicense', (0x1B3,)),
        (0x13B, 'isSoftwareDongle', (0x1C4,)), (0x13C, 'getDongleIdentifier', (0x1C4,)), (0x13D, 'getCloudDongleIdentifier', (0x1C4,)),
        (0x13F, 'manager', (0x1E4,)), (0x140, 'completion', (0x1E4,)),
        (0x142, 'dongle', (0x1B8, 0x1E6)), (0x143, 'manager', (0x1B8, 0x1E6)), (0x145, 'cloudDongle', (0x1BA, 0x1E8)),
        (0x147, 'dongleId', (0x1BB, 0x1EA)), (0x149, 'dongleId', (0x1C4, 0x1EC)),
        (0x14B, 'dongleId', (0x1C4, 0x1EE)), (0x14D, 'dongleId', (0x1C5, 0x1F0))]:
        s('Fields', rid, name, 'Retained delegate, identifier, manager or completion source used directly by the inspected callback.', proof)

    # ZIP observations are independently checked against each physical version.
    for review, old, stem in [(r, True, stem63), (Review(root, '64'), False, stem64)]:
        m, s = review.method, review.symbol
        m(0x7F if old else 0x30A, 'TryExtractNestedZipWithKey',
          'Sets the supplied key, creates an output directory using the archive basename and extracts there. Only BadPasswordException/ZlibException are converted to InvalidPasswordError; other exceptions escape.',
          ('workingDirectory', 'zipFile', 'keyProvider'), {0: 'archive', 1: 'outputDirectory', 2: 'result', 3: 'error', 4: 'isPasswordOrCompressionError'}, replace='ExtractZipFile' if old else None)
        m(0x7E if old else 0x309, 'ExtractNestedZipFiles',
          'Tries provided keys for each matching archive, retains the latest successful key, deletes extracted archives and returns paths with exactly nine final characters removed. A failed Result removes the working directory; an empty key list leaves a null Result that is dereferenced.',
          locals_={0: 'extractedPaths', 1: 'matchingFiles', 2: 'files', 3: 'fileIndex', 4: 'zipFile', 5: 'extractionResult', 6: 'keyEnumerator', 7: 'keyProvider'})
        m(0x79 if old else 0x2F4, 'ExtractDeviceTemplateContainer' if old else 'Extract',
          'Requires an existing container file, extracts it using ZipProtection.Password, then extracts Device/*.knxtempl with the same key if Device exists; otherwise returns the target directory. Directory input returns an empty list only after the file check.',
          locals_={0: 'deviceDirectory', 1: 'archive', 2: 'password', 3: 'validAccessKey', 4: 'result'}, replace='FindTemplateFiles' if old else None)
        if old:
            s('Fields', 0x85, 'NestedArchiveExtensionLength', 'Literal nine used when removing the suffix from extracted archive paths; does not measure the supplied pattern dynamically.', (0x7E,), literal=True)
            s('Fields', 0x86, 'log', 'Logger used for nested extraction password/compression failures.', (0x7F,))
            s('Fields', 0x87, 'zipContainerPath', 'Container path returned by its getter and assigned by its setter.', (0x7B, 0x7C))
        review.b.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
