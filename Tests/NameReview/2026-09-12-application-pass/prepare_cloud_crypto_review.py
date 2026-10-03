"""Prepare coupled CloudKit parser/crypto/collection reviews; never edit ETS code."""
import argparse
import hashlib
import json
import pathlib
import sqlite3
import xml.etree.ElementTree as ET
from prepare_physical_review import prepare


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('state', 'inventory', 'bodies', 'definition-bodies', 'consumer-bodies', 'types', 'fields', 'graph', 'output'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    state, inventory = read(args.state), read(args.inventory)
    source_paths = (args.bodies, args.definition_bodies, args.consumer_bodies, args.types, args.fields)
    bodies, definitions, consumers, types, fields = map(read, source_paths)
    physical = pathlib.Path(state['Pass']['SourceTree63']) / 'Knx.CloudKit.dll'
    physical_hash = digest(physical)
    for evidence in (bodies, definitions, consumers, types, fields):
        assert pathlib.Path(evidence['Input']).resolve() == physical.resolve()
        assert evidence['Sha256'] == physical_hash and evidence['Mvid'] == bodies['Mvid']
        assert evidence['Identity'] == bodies['Identity']
    assert inventory['MapSha256'] == state['Maps']['63']['Sha256'] == digest(state['Maps']['63']['Path'])
    reports = [r for r in inventory['Reports'] if r['Module'] == 'Knx.CloudKit.dll']
    assert {r['Kind'] for r in reports} == {'Types', 'Methods', 'Fields'}
    for report in reports:
        assert digest(report['Path']) == report['Sha256']
    native = {kind: {r['Token']: r for report in reports if report['Kind'] == kind
                     for r in read(report['Path'])[kind]} for kind in ('Types', 'Fields', 'Methods')}
    methods = {m['Token']: m for document in (bodies, definitions, consumers) for m in document['Methods']}
    storage = {f['Token']: f for f in fields['Fields']}
    current = next(m for m in ET.parse(state['Maps']['63']['Path']).getroot().findall('Module') if m.get('Path') == 'Knx.CloudKit.dll')
    aliases = {m.get('Token'): m for m in current}
    graph = sqlite3.connect(args.graph)
    meta = json.loads(graph.execute('select data from meta').fetchone()[0])
    for module in meta['Modules']:
        assert digest(module['Input']) == module['Sha256']
    module = next(m for m in meta['Modules'] if pathlib.Path(m['Input']).resolve() == physical.resolve())
    assert module['Sha256'] == physical_hash and module['Mvid'] == bodies['Mvid']
    rows, checked_edges, blockers = [], {}, []

    def token(number):
        return f'0x{number:08X}'

    def add(kind, number, name, reason, parameters=None, locals_=None, disposition='rename', **annotations):
        row = dict(Kind=kind, Module='Knx.CloudKit.dll', Token=token(number), Reason=reason, Disposition=disposition)
        if name:
            row['NewName'] = name
        if parameters:
            row['ParameterNames'] = parameters
        if locals_:
            row['LocalNames'] = locals_
        row.update(annotations)
        rows.append(row)

    def references(number):
        result = [dict(Source=source, Reference=json.loads(data)) for source, data in graph.execute(
            'select source,data from edges where target=?', (module['Id'] + ':' + token(number),))]
        checked_edges[token(number)] = result
        return result

    def field(number, name, reason, literal=False):
        assert storage[token(number)]['MappingBlocker'] is None
        assert references(number) or literal, ('Missing field consumers', token(number))
        add('Fields', number, name, reason + ' Exact physical graph references and storage retained; runtime names remain restoration inputs.')

    def unresolved_field(number, reason):
        edges = references(number)
        add('Fields', number, '', f'{reason} Physical graph has {len(edges)} incoming edges across {len(meta["Modules"])} hash-verified inputs; original metadata retained.', disposition='unresolved')

    def method(number, reason, parameters=None, locals_=None, name=None):
        key = token(number)
        assert methods[key]['HasBody'] and native['Methods'][key]['ScopedMappingBlocker'] is None
        parameters, locals_ = dict(parameters or {}), dict(locals_ or {})
        old = aliases.get(key)
        if old is not None:
            if name is None:
                name = old.get('NewName')
            for child in old.findall('Parameter'):
                parameters.setdefault(child.get('Sequence'), child.get('NewName'))
            for child in old.findall('Local'):
                locals_.setdefault(child.get('Index'), child.get('NewName'))
        add('Methods', number, name, reason + ' Carry forward checked scope aliases; unused control/Int16 locals receive no invented role.', parameters, locals_)

    def scopes(*names):
        return {str(index): name for index, name in enumerate(names)}

    def parameters(*names):
        return {str(index + 1): name for index, name in enumerate(names)}

    def called(number, text):
        assert any(isinstance(i['Operand'], dict) and text in i['Operand'].get('Text', '') for i in methods[token(number)]['Instructions']), (token(number), text)

    # Domain types follow actual storage, producers and framework contracts.
    add('Types', 0x02000070, 'ObservableCloudCollection`1', 'Class12<T> implements exact netstandard IEnumerable<T>/IEnumerable/INotifyCollectionChanged contracts. Add/remove/clear/replace publish change notifications, enumeration snapshots its locked List<T>, and optional owner assignment is limited to ajq/ajh. Keep generic arity and contract method names.')
    add('Types', 0x0200001C, 'CloudLicenseKind', 'ajp is the Byte enum stored by ajq/ajr and selected by LIC parser 0600012A; definition formatter 0600016D chooses plain-label vs feature-list rendering. Numeric value meanings remain explicitly unresolved.')
    add('Types', 0x02000020, 'CloudLicenseDefinitionStatus', 'ajt is the Int32 enum stored in ajr field 040000B8, initialized by definition constructor 0600015C and exposed by 06000167/168. No unsupported lifecycle names assigned to its values.')
    add('Types', 0x0200006F, 'CloudPublicKeyType', 'aj5 is the Int32 type discriminator accepted by aj6 public-key constructor 0600001A and returned by 0600001C; PUBLICKEY parser creates aj6. Native algorithm meanings remain unresolved.')

    field_names = {
        0x04000016: ('keyBytes', '0600001A requires a 48-byte constructor input and stores the original array; 0600001B returns it directly. PUBLICKEY= parser supplies these bytes; no copy is implied.'),
        0x04000017: ('keyType', '0600001A stores aj5 argument 2 and 0600001C returns it; PUBLICKEY= parser supplies value 0 without revealing algorithm semantics.'),
        0x04000019: ('firstHalf', '06000020 stores signatureBytes.Take(24).ToArray; 06000021 copies Take(24).ToArray from that field. Native opaque verification does not establish an ECDSA R role.'),
        0x0400001A: ('secondHalf', '06000020 stores signatureBytes.Skip(24).Take(24).ToArray; 06000022 copies Take(24).ToArray from that field. 06000028 concatenates first then second; no ECDSA S role claimed.'),
        0x0400001B: ('signatureType', '06000020 stores aka argument 2; 06000023 returns it, 06000024 casts it to Char and verification 06000026 branches on the value.'),
        0x0400001C: ('eventHandlerLock', '06000025 snapshots field 0400001D under Monitor.Enter/Exit; 0600002C creates this lock. It does not lock native verification.'),
        0x0400001D: ('verificationFailureHandlers', '0600001E/1F Combine/Remove with CompareExchange; 06000025 invokes the snapshot, and 06000026/27 call it on failed signature verification.'),
        0x0400009F: ('versionedHashPrefix', 'Only 0600012C reads/writes this cache: UTF8 of Knx.CloudKit.Secure.v{major}.{minor}.{build}.{revision}:. Callers prepend it to hash inputs.'),
        0x040000A0: ('payloadDecryptionKey', 'Only 0600012B reads/writes the cached first 16 bytes of derived SHA256; its only managed caller 06000128 supplies the result to SymmetricAlgorithm.set_Key.'),
        0x040000A2: ('hashBytes', 'Both ajn constructors compute Class8 native cloud hash; String input is Base64 decoded first. 06000135 returns this byte array and certificate verification appends it to its hash input.'),
        0x04000006: ('headerIdentifier', '06000130 parses the CERT header prefix before the colon into constructor argument 1; 06000008 stores it and 06000015 emits it in that position. Vendor/issuer identity is not established; no invented vendor role.'),
        0x04000007: ('name', '06000130 parses the quoted CERT header name into constructor argument 2; 0600000B returns this field. 06000058/59 compare that getter to the requested name, and 06000009 hashes its UTF8 bytes.'),
        0x04000008: ('classIdentifier', '06000008 fixes this field to CloudLicense; 06000015 emits ID=, 0600000A appends its first 12 ASCII bytes to root verification data, 0600000C returns it. Parsed ID= text is discarded; not a dongle ID.'),
        0x04000009: ('publicKey', 'PUBLICKEY= parser creates aj6 and supplies certificate constructor argument 3; root verification appends its first 48 bytes and certificate signature verification uses this public key.'),
        0x0400000A: ('rootSignature', 'ROOTCERT= parser creates aka value 82 signature, supplies certificate argument 4; 0600000A verifies it against the public-key/class-identifier root hash.'),
        0x0400000B: ('licenseLabel', 'LICENSE= parser supplies argument 5; constructor stores it, formatter emits LICENSE= and certificate hash appends its UTF8 bytes.'),
        0x0400000C: ('customer', 'CUSTOMER= parser supplies argument 6; formatter emits CUSTOMER= and certificate hash appends its UTF8 bytes.'),
        0x0400000D: ('number', 'NUMBER= parser supplies argument 7; formatter emits NUMBER= and certificate hash appends its UTF8 bytes.'),
        0x0400000E: ('timestamp', 'DATE=/TIME= parse into argument 8; constructor preserves ticks while setting DateTimeKind.Utc. Formatter emits date/time and hash uses all six components.'),
        0x0400000F: ('signature', 'SIGN= parser supplies argument 9 as aka value 85; 06000009 verifies this signature with the certificate public key and 06000015 emits SIGN=.'),
        0x04000010: ('isValid', 'Constructor initializes false; 06000009 stores the root/certificate signature verification outcome and 06000011 returns it.'),
        0x04000011: ('eventHandlerLock', '06000013/14 snapshot their handler chains under Monitor.Enter/Exit; static initializer creates this lock.'),
        0x04000012: ('verificationFailureHandlers', '06000004/05 CAS subscribe/unsubscribe; 06000013 publishes from failed root or certificate verification branches in 06000009/0A.'),
        0x040000AD: ('kind', '0600015C stores ajp argument 1; LIC parser selects it and definition formatter branches on 80. Value semantics remain unresolved.'),
        0x040000AE: ('dongleIdentifier', 'LIC ID= parser supplies constructor argument 2; 0600015E returns it and formatter emits ID=.'),
        0x040000AF: ('expirationDate', 'EXPIRE= parser supplies nullable argument 3; 0600015F returns it and formatter conditionally emits EXPIRE=.'),
        0x040000B0: ('issueDate', 'ISSUE= parser supplies nullable argument 4; constructor stores its Value as DateTime, 06000160 returns it and formatter emits ISSUE=. Preserve missing-date exception behavior.'),
        0x040000B1: ('features', 'Constructor stores argument 5; parser creates ajl entries from comma-separated labels/values and formatter enumerates labels with value or unlimited text.'),
        0x040000B2: ('vendor', 'LIC parser takes the prefix before colon into argument 6; formatter emits it immediately after LIC, consistent with the coupled PKG vendor prefix.'),
        0x040000B3: ('label', 'LIC plain/quoted label parser supplies argument 7; formatter emits it and constructor tests IsNullOrEmpty to select initial status.'),
        0x040000B4: ('customer', 'CUSTOMER= parser supplies argument 8; formatter emits this field under CUSTOMER=.'),
        0x040000B5: ('number', 'NUMBER= parser supplies argument 9; formatter emits this field under NUMBER=.'),
        0x040000B6: ('signature', 'LIC SIGN= parser constructs aka value 76 into argument 10; formatter emits SIGN= and constructor derives an object hash code from its first four bytes.'),
        0x040000B7: ('hashCode', 'Constructor stores BitConverter.ToInt32(first signature half,0), or zero for null signature; actual Object.GetHashCode override 06000170 returns this cached value.'),
        0x040000B8: ('status', 'Constructor sets ajt 1 for nonempty label, otherwise 0; 06000167/168 read/write it. Complete lifecycle/value meanings are not established.'),
        0x040001E0: ('collectionChangedHandlers', 'Exact CollectionChanged accessors CAS this delegate; virtual 0600033C snapshots its invocation list and calls handlers after collection mutations.'),
        0x040001E1: ('syncRoot', 'Class12<T> constructors initialize this object; list mutation/count/snapshot/notification bodies enter and exit it through Monitor.'),
        0x040001E2: ('items', 'Constructor creates List<T>; Add/AddRange/Remove/Clear/count/snapshot/enumeration all consume the same exact generic field.')
    }
    for number, (name, reason) in field_names.items():
        field(number, name, reason)
    for number in [0x04000003, 0x04000004, 0x04000005, 0x04000015, 0x0400001E, 0x0400001F, *range(0x04000090, 0x0400009F)]:
        assert storage[token(number)]['IsLiteral'] and not references(number)
        unresolved_field(number, f'Literal {storage[token(number)]["ConstantType"]} value {storage[token(number)]["Constant"]}; numeric uses were inlined. No token-to-use association or distinct declaration responsibility is established; do not invent a length/limit name.')
    for number in [0x040000A5, 0x040000A6, 0x040000BC, 0x040000BD, 0x040000BE, 0x040001DE, 0x040001DF]:
        unresolved_field(number, f'Enum value {storage[token(number)]["Constant"]}. Managed producers expose label/feature format, initial status or public-key discriminator, but intended domain/lifecycle/native algorithm meaning lacks decisive evidence; retain original enum value name.')

    # Exact signature constructor producers identify context without guessing math.
    assert [(r['OwnerToken'], r['Offset']) for r in methods['0x06000020']['IncomingReferences']] == [
        ('0x0600012A', 1419), ('0x0600012E', 180), ('0x06000130', 439), ('0x06000130', 1135)]
    for number, value, name, producer, offset, literal in [
            (0x040001E8, 85, 'Certificate', 0x06000130, 439, 'SIGN='),
            (0x040001E9, 80, 'Package', 0x0600012E, 180, 'SIGN='),
            (0x040001EA, 76, 'License', 0x0600012A, 1419, 'SIGN='),
            (0x040001EB, 82, 'RootCertificate', 0x06000130, 1135, 'ROOTCERT=')]:
        assert storage[token(number)]['Constant'] == value
        instructions = methods[token(producer)]['Instructions']
        position = next(i for i, instruction in enumerate(instructions) if instruction['Offset'] == offset)
        assert instructions[position - 1]['Operand'] == str(value)
        assert any(i['OpCode'] == 'ldstr' and literal in str(i['Operand']) for i in instructions)
        field(number, name, f'Unique aka constant {value}; complete physical constructor references identify {token(producer)}:{offset} from {literal} in this record context. Immediate constant feeds signature constructor; field/runtime value unchanged. Names describe observed signature context, not native cryptographic algorithm.', literal=True)

    method(0x0600001A, 'PUBLICKEY= parser supplies exact raw key bytes and type; constructor validates 48-byte length and retains array without cloning.', parameters('keyBytes', 'keyType'))
    method(0x06000020, 'Wrong length of raw signature requires 48 bytes; constructor stores Take(24) and Skip(24).Take(24) halves and type.', parameters('signatureBytes', 'signatureType'))
    for number, name, field_token in [(0x06000021, 'CopyFirstSignatureHalf', '0x04000019'), (0x06000022, 'CopySecondSignatureHalf', '0x0400001A')]:
        assert [i['Operand']['Token'] for i in methods[token(number)]['Instructions'] if i['OpCode'] == 'ldfld'] == [field_token]
        called(number, 'System.Linq.Enumerable::Take<System.Byte>')
        called(number, 'System.Linq.Enumerable::ToArray<System.Byte>')
        method(number, 'Copies 24 bytes of this field through Take(24).ToArray. Retain the meaningful copy operation; opaque native verification and byte slicing do not prove mathematical R/S roles.', name=name)
    method(0x06000026, 'Native verification result is stored and returned in local 0; zero/failed signature branches publish verification failure. Existing hash parameter retained.', parameters('hash'), scopes('isValid'))
    method(0x06000027, 'Passes serialized signature, supplied hash and public-key bytes to native public-key verification; failure publishes signature event.', parameters('hash', 'publicKey'))
    for number in (0x0600001E, 0x0600001F, 0x06000004, 0x06000005):
        called(number, 'System.Threading.Interlocked::CompareExchange')
        method(number, 'CAS event update: local 0 current handler chain, 1 expected preimage, 2 combined/removed chain; argument is supplied handler.', parameters('handler'), scopes('currentHandlers', 'expectedHandlers', 'updatedHandlers'))
    for number, sender in [(0x06000025, 'signature'), (0x06000013, 'certificate')]:
        called(number, 'System.Delegate::GetInvocationList')
        method(number, 'Snapshot under Monitor then iterate invocation list; event runs synchronously or BeginInvoke according to Class13 setting and catches handler exceptions.', parameters(sender), scopes('handlers', 'eventLock', 'lockTaken', 'invocationList', 'handlerIndex', 'handlerDelegate', 'handler'))

    method(0x06000128, 'AES decrypt: IV=first16 input bytes, key=0600012B; decrypted prefix holds SHA256 and UInt64 length, then UTF8 text at offset40. Local names follow exact calls/offsets; preserve mode, padding, ignored Read count and exceptions.', parameters('encryptedPayload'), scopes('decryptedBytes', 'aes', 'decryptor', 'encryptedStream', 'cryptoStream', 'declaredPayloadByteCount', 'payloadByteCount', 'storedSha256', 'sha256', 'payloadText'))
    called(0x06000128, 'System.Security.Cryptography.SymmetricAlgorithm::set_Key')
    assert len(methods['0x0600012B']['IncomingReferences']) == 1 and methods['0x0600012B']['IncomingReferences'][0]['OwnerToken'] == '0x06000128'
    method(0x0600012B, 'Caches first16 bytes of SHA256(versionedPrefix + UTF8(String.Format(prefix.Length*997))). Only caller supplies result to AES.set_Key; correct misleading ComputePayloadHash alias.', locals_=scopes('keyMaterial', 'sha256'), name='GetPayloadDecryptionKey')
    method(0x0600012C, 'Caches UTF8 Knx.CloudKit.Secure.v{major}.{minor}.{build}.{revision}: from native library Version. Used as hash prefix/key material; no payload composition occurs.', locals_=scopes('version'), name='GetVersionedHashPrefix')
    called(0x06000131, 'System.Text.Encoding::GetByteCount')
    called(0x06000131, 'System.String::Substring')
    method(0x06000131, 'Repeatedly removes the final UTF16 code unit until UTF8.GetByteCount <= argument2. No field extraction. Preserve negative-limit/surrogate behavior.', parameters('text', 'maxByteCount'), scopes('truncatedText'), name='TruncateToUtf8ByteLimit')
    method(0x06000129, 'LIC record loop uses IndexOf/Substring; count increments before parsing and appears in Invalid license/count exception data. Definitions only added when nonnull.', parameters('content'), scopes('definitions', 'recordNumber', 'recordStartIndex', 'nextLicenseOffset', 'remainingText', 'definitionText', 'definition'))
    method(0x0600012D, 'PKG record loop uses relative IndexOf after Substring(4), assembles each definition and skips caught parser errors.', parameters('content'), scopes('definitions', 'recordStartIndex', 'nextPackageOffset', 'remainingText', 'definitionText', 'definition'))
    method(0x0600012F, 'CERT record loop uses relative IndexOf after Substring(5), assembles each certificate and skips caught parser errors.', parameters('content'), scopes('certificates', 'recordStartIndex', 'nextCertificateOffset', 'remainingText', 'certificateText', 'certificate'))
    method(0x0600012E, 'PKG header feeds vendor/name/label/features; comma/equal/unlimited parse assigns feature roles. SIGN= hexadecimal loop fills48 bytes and constructs signature type80.', parameters('definitionText'), scopes('lines', 'vendor', 'name', 'label', 'features', 'signature', 'line', 'lineIndex', 'featureEntries', 'featureEntriesToParse', 'featureIndex', 'featureLabel', 'featureValue', 'featureValueParts', 'signatureHex', 'signatureBytes', 'signatureHexIndex', 'signatureByteIndex'))
    method(0x0600012A, 'LIC/ISSUE/EXPIRE/ID/CUSTOMER/NUMBER/SIGN literals establish data roles; hash input=versioned prefix + original LIC text up to SIGN + final16 signature bytes, compared to first32 signature bytes. Fields feed ajr constructor; failed hash returns null.', parameters('definitionText'), scopes('licenseStartIndex', 'signatureStartIndex', 'lines', 'kind', 'vendor', 'label', 'features', 'dongleIdentifier', 'expirationDate', 'issueDate', 'customer', 'number', 'signature', 'line', 'lineIndex', 'featureEntries', 'featureEntriesToParse', 'featureIndex', 'featureLabel', 'featureValue', 'featureValueParts', 'issueDateText', 'issueDateParts', 'expirationDateText', 'expirationDateParts', 'signatureHex', 'signatureBytes', 'signatureHexIndex', 'signatureByteIndex', 'serializedSignature', 'hashInput', 'storedSha256', 'sha256', 'definition'))
    method(0x06000130, 'CERT header/publickey/rootcert/license/customer/number/date/time/sign parse feeds ai6 constructor; ID text is validated/truncated then discarded and constructor fixes CloudLicense. Preserve this behavior. Each hex loop tracks text index and output byte index separately.', parameters('certificateText'), scopes('lines', 'headerIdentifier', 'name', 'publicKey', 'rootSignature', 'licenseLabel', 'customer', 'number', 'timestamp', 'signature', 'line', 'lineIndex', 'publicKeyHex', 'publicKeyBytes', 'publicKeyHexIndex', 'publicKeyByteIndex', 'rootSignatureHex', 'rootSignatureBytes', 'rootSignatureHexIndex', 'rootSignatureByteIndex', 'dateText', 'dateParts', 'timeText', 'timeParts', 'signatureHex', 'signatureBytes', 'signatureHexIndex', 'signatureByteIndex'))
    method(0x06000133, 'Convert.FromBase64String decodes input into local0, then native cloud hash computes stored bytes; no algorithm is guessed.', parameters('base64Payload'), scopes('payloadBytes'))
    method(0x06000134, 'Native cloud hash computes stored bytes from supplied raw payload; null native result throws original NullReferenceException.', parameters('payloadBytes'))

    method(0x06000008, 'Constructor fields are corroborated by CERT formatter/parser and name lookup consumers; timestamp ticks retained with Utc kind, classIdentifier fixed to CloudLicense.', parameters('headerIdentifier', 'name', 'publicKey', 'rootSignature', 'licenseLabel', 'customer', 'number', 'timestamp', 'signature'))
    method(0x06000009, 'Root verification then public-key signature verification: supplied hash bytes + six timestamp components + name/license/customer/number UTF8 produce local1 hash; local0 validity cached and failure published.', parameters('hash'), scopes('isValid', 'signatureHash'))
    method(0x0600000A, 'Root data=publicKey.Take48 + ASCII classIdentifier.Take12, resized64; local1 native hash passed to root signature verification.', locals_=scopes('rootCertificateBytes', 'rootHash'))
    method(0x0600000C, 'Getter returns field04000008, fixed by constructor to CloudLicense and formatted as ID=. No dongle identifier or dynamic value is returned. Correct unsupported GetCertificateDongleId.', name='GetCertificateClassIdentifier')
    method(0x06000015, 'CERT/ID/PUBLICKEY/ROOTCERT/DATE/TIME/LICENSE/CUSTOMER/NUMBER/SIGN text assembled in local0; local1 repeatedly formats timestamp components.', locals_=scopes('certificateText', 'dateTimeComponent'))
    for number in (0x06000006, 0x06000007, 0x06000014):
        assert not references(number) and not methods[token(number)]['IncomingReferences']
        assert aliases[token(number)].get('NewName') and len(aliases[token(number)]) == 0
        add('Methods', number, '', 'no-evidence-in-scope: event updater/publisher is associated with field04000013 and publisher supplies ajh sender, but no failure condition or signing operation exists in these bodies. Complete module inspection and physical graph yield zero callers. Trigger semantics/reflection/external consumers are missing; withdraw unsupported DongleSigningFailure alias.', disposition='unresolved', RemoveExistingAlias=True, ExpectedAlias=aliases[token(number)].get('NewName'))
    unresolved_field(0x04000013, 'Event handler chain is updated by06000006/07 and published by06000014 with ajh sender, all with zero callers. Intended trigger (including alleged signing failure) has no managed evidence; retain unresolved rather than perpetuate unsupported purpose.')

    method(0x0600015C, 'ISSUE/EXPIRE/ID/CUSTOMER/NUMBER/SIGN parser/formatter corroborate ten constructor roles; preserve nullable issueDate.Value, signature-derived hashCode and status initialization.', parameters('kind', 'dongleIdentifier', 'expirationDate', 'issueDate', 'features', 'vendor', 'label', 'customer', 'number', 'signature'))
    method(0x06000168, 'Stores the supplied status in exact ajt field040000B8 without interpreting enum values.', parameters('status'))
    method(0x0600016A, 'Constructs empty definition with nullable expirationDate default in local0 and nullable DateTime.MinValue issueDate; preserve constructor fields/values.', locals_=scopes('expirationDate'))
    assert not any(i['OpCode'] == 'newobj' for i in methods['0x0600016B']['Instructions'])
    method(0x0600016B, 'Directly returns supplied license.GetDefinition via06000150; does not allocate a definition. Correct CreateDefinitionFromLicense implication.', parameters('license'), name='GetDefinitionFromLicense')
    method(0x0600016D, 'LIC/ID/ISSUE/EXPIRE/CUSTOMER/NUMBER/SIGN formatter iterates features and uses shared DateTime/Int32 component locals to emit issue/expiration dates.', locals_=scopes('definitionText', 'features', 'featureIndex', 'feature', 'date', 'dateComponent'))

    method(0x06000334, 'Add retains meaningful original name. Local0 insertion index from List.Count, optional ajq/ajh owner assignments, then locked Add and collection Add notification.', parameters('item', 'owner'), scopes('insertionIndex', 'license', 'dongle', 'collectionLock', 'lockTaken'))
    for number in (0x06000335, 0x06000336):
        method(number, 'Locked list update enumerates items to assign optional ajq/ajh parent; exact locals are lock/flag/enumerator/item/license/dongle. Replace callback runs before List.AddRange after owner assignment; changes publish after lock.', parameters(*(['items', 'owner', 'beforeAdd'] if number == 0x06000336 else ['items', 'owner'])), scopes('collectionLock', 'lockTaken', 'itemEnumerator', 'item', 'license', 'dongle'))
    method(0x06000337, 'List.IndexOf captures removal index; List.Remove captures boolean result under Monitor, then notification uses item/index.', parameters('item'), scopes('removed', 'itemIndex', 'collectionLock', 'lockTaken'))
    method(0x06000338, 'Monitor guards List.Clear, then publishes reset notification.', locals_=scopes('collectionLock', 'lockTaken'))
    method(0x0600033A, 'Monitor guards ToList snapshot; exact local0 lock,1 flag,2 returned snapshot.', locals_=scopes('collectionLock', 'lockTaken', 'snapshot'))
    method(0x0600033B, 'Monitor guards List.Contains; exact local0 returned boolean,1 lock,2 flag.', parameters('item'), scopes('containsItem', 'collectionLock', 'lockTaken'))
    method(0x0600033D, 'Monitor guards List.Count; exact local0 returned count,1 lock,2 flag.', locals_=scopes('count', 'collectionLock', 'lockTaken'))

    selected_types = {'ai6', 'aj6', 'akb', 'Class7', 'ajn', 'ajr', 'Class12`1'}
    for key, body in methods.items():
        original = native['Methods'][key]
        if original['Type'] in selected_types and original['ScopedMappingBlocker']:
            blockers.append(dict(Token=key, Signature=body['Signature'], ScopedMappingBlocker=original['ScopedMappingBlocker'],
                                 ExistingAlias=aliases[key].get('NewName') if key in aliases else None,
                                 Limitation='Ordinary scope review cannot replace interface/override/family review. Preserve current contract bindings and meaningful original names; family scope review remains required.'))
    assert len({(r['Kind'], r['Token']) for r in rows}) == len(rows)
    spec = dict(Format=1, TargetRoot=state['Pass']['SourceTree63'], ContractReferenceSha256=state['Compatibility']['ContractReferences63']['Sha256'], Inventories=[r['Path'] for r in reports], Rows=rows)
    review = prepare(spec)
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    input_state = dict(Pass=dict(SourceTree63=state['Pass']['SourceTree63']), Maps={'63': state['Maps']['63']}, Compatibility=dict(ContractReferences63=state['Compatibility']['ContractReferences63']))
    documents = [('cloud-crypto-input-state01.json', input_state), ('cloud-crypto-spec01.json', spec), ('cloud-crypto-review01.json', review), ('cloud-crypto-evidence01.json', dict(
        Format=1, PhysicalPath=str(physical), Sha256=physical_hash, Mvid=bodies['Mvid'], Map=state['Maps']['63']['Path'], MapSha256=inventory['MapSha256'],
        Inventory=dict(Path=args.inventory, Sha256=digest(args.inventory)), Sources=[dict(Path=path, Sha256=digest(path)) for path in (*source_paths, args.graph)],
        GraphPhysicalInputsVerified=len(meta['Modules']), References=checked_edges, ScopedMappingBlockers=blockers,
        Methods=[methods[r['Token']] for r in rows if r['Kind'] == 'Methods'], FieldStorage=[storage[r['Token']] for r in rows if r['Kind'] == 'Fields'],
        Limitations='Native map checks mandatory. Static graph excludes reflection/dynamic/external consumers. No ETS source/binary or runtime behavior edited; consolidated rebuilt compatibility remains pending.'))]
    for name, document in documents:
        (output / name).write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print('Prepared', {k: len(review[k]) for k in ('Types', 'Fields', 'Methods')}, 'protected scopes', len(blockers))


if __name__ == '__main__':
    main()
