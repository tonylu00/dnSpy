"""Review PBKDF2, trace comments and salted cipher envelopes in both versions.

Usage: python security_envelopes.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only review/map evidence is written. Public SDK names and parameters stay intact.
"""
import json
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    for version, base, module, prior, prefix, inspection_name, stem in [
        ('63', 196, 'm0039', 'http63-wave196.cumulative.json', 'http63-wave196', 'security63-wave197-inspection.json', stem63),
        ('64', 28, 'm0102', 'exception64-wave28.cumulative.json', 'security64-wave29', 'security64-wave29-inspection.json', stem64)]:
        old = version == '63'
        b = BehaviorReview(root, version, base, module, prefix, root / prior)
        inspection = b.read(inspection_name)
        assert Path(inspection['Input']).resolve() == Path(b.module['Input']).resolve()
        assert all(inspection[k] == b.module[k] for k in ('Mvid', 'Sha256'))
        bodies = {int(m['Token'], 16): m for m in inspection['Methods']}
        il = {'Path': str(root / inspection_name), 'Sha256': sha(root / inspection_name)}
        families = b.read(f'security{version}-wave197-selected-families.json')
        assert families['ContractReferenceSha256'] == b.delta.get('ContractReferenceSha256')

        def method(rid, name, reason, parameters=None, locals_=None, replace=None, family=False):
            token = 0x06000000 + rid
            row, body = b.entries['Methods'][f'0x{token:08X}'], bodies[token]
            assert row['Signature'] == body['Signature']
            for slot in locals_ or {}:
                expected = next(l['ExpectedType'] for l in row['LocalNames'] if l['Index'] == slot)
                assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
            contract = next(r for r in families['Methods'] if r['Module'] == b.relative and r['Token'] == row['Token']) if family else None
            if family:
                # Scopes only: retain the method's exact CLR contract spelling.
                assert name == row['OriginalName'] and parameters is None and replace is None
            b.add('Methods', token, name, reason, parameters, locals_, contract=contract, replace_alias=replace)
            assert not b.pending, b.pending
            b.decisions[-1]['IL'] = {**il, 'Token': row['Token'], 'Slots': locals_ or {}}

        def field(rid, name, reason, proof, literal=False):
            token = 0x04000000 + rid
            symbol = json.loads(b.db.execute('SELECT data FROM symbols WHERE id=?', (module + f':0x{token:08X}',)).fetchone()[0])
            assert symbol['IsLiteral'] == literal
            if not literal:
                found = []
                for raw in b.db.execute('SELECT data FROM edges WHERE target=?', (module + f':0x{token:08X}',)):
                    edge = json.loads(raw[0])
                    if not edge['From'].startswith(module + ':'):
                        continue
                    caller = int(edge['From'].split(':')[1], 16)
                    if caller not in {0x06000000 + rid for rid in proof}:
                        continue
                    actual = next(i for i in bodies[caller]['Instructions'] if i['Offset'] == edge['Offset'])
                    assert actual['OpCode'] == edge['Operation'] and actual['Operand']['Text'] == edge['Target']['Signature']
                    assert Path(edge['Target']['PhysicalModule']).resolve() == Path(b.module['Input']).resolve()
                    found.append(edge)
                assert found, ('No inspected storage use', rid)
            b.add('Fields', token, name, reason, evidence=[0x06000000 + rid for rid in proof])
            assert not b.pending, b.pending
            b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x{0x06000000 + rid:08X}' for rid in proof],
                                    'LiteralDeclarationEvidence': literal}

        # Native entry points retain names and imports; only parameter roles change.
        for rid, name, parameters in [
            (0xAC if old else 0x351, 'BCryptDeriveKeyPBKDF2', ('algorithmHandle', 'password', 'passwordLength', 'salt', 'saltLength', 'iterationCount', 'derivedKey', 'derivedKeyLength', 'flags')),
            (0xAD if old else 0x352, 'BCryptOpenAlgorithmProvider', ('algorithmHandle', 'algorithmId', 'implementation', 'flags')),
            (0xAE if old else 0x353, 'BCryptCloseAlgorithmProvider', ('algorithmHandle', 'flags'))]:
            method(rid, name, 'Preserves the native import and assigns parameter roles from the reviewed derivation/provider/open/close call sites.', parameters)
        for rid, parameters, reason in [
            (0xA4 if old else 0x346, ('password', 'salt', 'iterationCount', 'algorithm'), 'Retains nonnull password bytes, rejects nonpositive iterations and stores algorithm and salt without copying the bytes.'),
            (0xA5 if old else 0x347, ('password', 'salt', 'iterationCount', 'algorithm'), 'Encodes the nonnull password as UTF-8 and delegates to the byte-array constructor.'),
            (0xA6 if old else 0x348, ('password', 'saltSize', 'iterationCount', 'algorithm'), 'Generates the salt before delegating, then rejects nonpositive saltSize; does not move validation before generation.')]:
            method(rid, None, reason, parameters)
        method(0xAB if old else 0x34D, 'EnsurePbkdf2AlgorithmProvider',
               'Lazily opens the configured algorithm with flag value 8; on nonzero status resets the provider and throws CryptographicException with that status.',
               (), {0: 'status', 1: 'algorithm'})
        for rid, name, proof in ([(0x99, 'passwordBytes', (0xA4, 0xA8)), (0x9A, 'iterationCount', (0xA4, 0xA8)),
                                  (0x9B, 'algorithm', (0xA4, 0xAB)), (0x9C, 'algorithmHandle', (0xA8, 0xA9, 0xAB)), (0x9D, 'salt', (0xA4, 0xA7))] if old else
                                 [(0x193, 'passwordBytes', (0x346, 0x34A)), (0x194, 'iterationCount', (0x346, 0x34A)), (0x196, 'algorithmHandle', (0x34A, 0x34B, 0x34D))]):
            field(rid, name, 'Stored input or provider resource used directly by PBKDF2 derivation and reset.', proof)

        # Independent trace format; its public Encrypt/Decrypt contract stays intact.
        method(0xB1 if old else 0x364, None, 'Rejects iterations below one and retains the selected trace derivation count.', ('iterations',))
        method(0xB2 if old else 0x365, 'GetTraceKeyDerivation', 'Lazily creates the trace Rfc2898DeriveBytes with the fixed ProjectTrace input, stored UTF-8 salt and configured iterations.', ())
        method(0xBB if old else 0x36E, 'InitializeTraceAesKeyAndIv', 'Consumes 32 then 16 bytes from the supplied derivation to set AES Key and IV; returns the same AES instance.', ('aes', 'derivation'))
        method(0xB3 if old else 0x366, 'GetTraceAes', 'Lazily creates and configures the cached trace AES instance from the cached derivation.', ())
        method(0xB9 if old else 0x36C, 'HasEncryptedTracePrefix', 'Null-safe StartsWith check for the exact trace-comment marker; no namespace or XML behavior.',
               ('comment',), replace='IsDefaultNamespace' if old else None)
        method(0xB5 if old else 0x368, 'EncryptTraceCommentOrReturnInput',
               'Encrypts UTF-8 comment bytes with the supplied AES and returns the marker plus Base64 ciphertext. Encryption exceptions are logged and return input; argument validation and UTF-8 conversion precede the try.',
               ('comment', 'aes'), {0: 'plainBytes', 1: 'output', 2: 'encryptor', 3: 'cryptoStream', 4: 'encryptedComment', 5: 'error'})
        method(0xB7 if old else 0x36A, 'DecryptTraceCommentOrReturnInput',
               'Returns unmarked input unchanged; removes marker length minus one before Base64 decoding, then decrypts and decodes UTF-8. Base64 parsing occurs outside the catch; caught decryption errors log and return the input.',
               ('encryptedComment', 'aes'), {0: 'cipherBytes', 1: 'output', 2: 'decryptor', 3: 'cryptoStream', 4: 'comment', 5: 'error'})
        for rid, name, proof in ([(0xA6, 'log', (0xB5, 0xB7)), (0xA7, 'iterations', (0xB1, 0xB2)), (0xA8, 'saltBytes', (0xB1, 0xB2)),
                                  (0xA9, 'keyDerivation', (0xB2, 0xBA)), (0xAA, 'aes', (0xB3, 0xBA))] if old else
                                 [(0x19E, 'log', (0x368, 0x36A)), (0x1A0, 'saltBytes', (0x364, 0x365)), (0x1A1, 'keyDerivation', (0x365, 0x36D)), (0x1A2, 'aes', (0x366, 0x36D))]):
            field(rid, name, 'Trace encryptor storage proven by its construction, transform or disposal path.', proof)

        # Salt + IV + cipher serialization is distinct from either array getter.
        method(0xBD if old else 0x382, None, 'Stores salt and nonnull IV/cipher arrays without cloning or checking their lengths.',
               ('salt', 'initVector', 'cipher'))
        if old:
            method(0xBE, 'GetEnvelopeSalt', 'Returns the stored salt.', ())
            method(0xBF, 'GetEnvelopeInitializationVector', 'Returns the stored initialization-vector array, not a serialized envelope.', (), replace='ToBytes')
            method(0xC0, 'GetEnvelopeCipherBytes', 'Returns the stored ciphertext array, not a serialized envelope.', (), replace='ToBytes2')
        method(0xC2 if old else 0x387, 'SerializeCipherEnvelope' if old else 'ToBytes',
               'Allocates and concatenates salt bytes, initialization vector and cipher bytes in that order; the stored arrays are not length-validated here.',
               (), {0: 'envelopeBytes', 1: 'salt'}, replace='ToBytes3' if old else None)
        method(0xC3 if old else 0x388, 'LooksLikeCipherEnvelope' if old else 'CanParse',
               'Checks nonempty text, an ordinal colon prefix and length greater than 28; this does not validate Base64 or cryptographic data.',
               ('encoded',) if old else None, {0: 'marker'}, replace='CanParse' if old else None)
        method(0xC4 if old else 0x389, 'HasCipherEnvelopeHeaderLength' if old else 'CanParse',
               'Checks only whether the array length is at least 20, with no null guard, decoding or authentication.',
               ('data',) if old else None, replace='CanParse' if old else None)
        method(0xC6 if old else 0x38B, 'DecodeCipherEnvelopeBytes',
               'Copies the first 8 bytes as salt, next 12 as initialization vector and the remainder as ciphertext. Invalid lengths fail through array allocation/copy; this routine has no preceding length guard.',
               ('data',), {0: 'saltBytes', 1: 'initializationVector', 2: 'cipherBytes'})
        method(0xC5 if old else 0x38A, 'ParseCipherEnvelopeIfRecognized' if old else 'TryParse',
               'Returns false/default only when the text shape is unrecognized; otherwise decodes Base64 after the colon and splits the envelope. Malformed Base64/length exceptions escape despite the original TryParse name.',
               ('encoded', 'envelope') if old else None, replace='TryParse' if old else None)
        if old:
            for rid, name, proof in [(0xB0, 'salt', (0xBD, 0xBE)), (0xB1, 'initializationVector', (0xBD, 0xBF)), (0xB2, 'cipherBytes', (0xBD, 0xC0))]:
                field(rid, name, 'Retained envelope component returned by its corresponding getter and consumed during serialization.', proof)

        method(0xCA if old else 0x392, 'DeriveSaltedPasswordHash',
               'Derives 32 bytes with PBKDF2-SHA256 and 100000 iterations, then returns salt concatenated with derived bytes. The result includes the salt; it is not just a key.',
               ('salt', 'password'), {0: 'derivation', 1: 'derivedHash', 2: 'saltedHash', 3: 'result'}, replace='DerivePasswordKey' if old else None)
        method(0xC9 if old else 0x391, 'acw' if old else 'Validate',
               'Decodes the stored Base64 salt/hash, requires at least 16 salt bytes, rederives the full salt/hash and ORs every compared byte difference. The extracted trailing hash copy is not used in comparison. Public name and parameters are retained.',
               locals_={0: 'storedSaltedHash', 1: 'saltLength', 2: 'saltBytes', 3: 'storedHashCopy', 4: 'derivedSaltedHash', 5: 'difference', 6: 'index'}, family=True)
        method(0xCF if old else 0x397, None, 'Stores nonempty passwordHash, supplied/default UTF-8 encoding and the caller-selected legacy flag.', ('passwordHash', 'isLegacy', 'encoding'))
        method(0xD3 if old else 0x39E, None, 'Stores nonempty passwordHash and supplied/default UTF-8 encoding; owns a SecureRandom for initialization vectors.', ('passwordHash', 'encoding'))
        method(0xD2 if old else 0x39A, 'ReadValue',
               'Parses the envelope; empty cipher means null. Otherwise derives a 32-byte key using one SHA256 PBKDF2 iteration, authenticates/decrypts AES-CCM with a 128-bit tag and salt as associated data, then decodes the full plaintext buffer. InvalidCipherTextException becomes InvalidOperationException. Public name and parameters stay unchanged.',
               locals_={0: 'envelope', 1: 'value', 2: 'derivation', 3: 'key', 4: 'ccmCipher', 5: 'plainBytes', 6: 'processedBytes'}, family=True)
        method(0xD4 if old else 0x39F, 'WriteValue',
               'Creates an 8-byte salt and 12-byte nonce, derives a 32-byte key with one SHA256 PBKDF2 iteration, and encrypts/authenticates nonnull input using AES-CCM with a 128-bit tag and salt as associated data. Null input retains an empty cipher; output is the colon/Base64 envelope. Public name and parameters stay unchanged.',
               locals_={0: 'derivation', 1: 'key', 2: 'salt', 3: 'initializationVector', 4: 'ccmCipher', 5: 'cipherBytes', 6: 'plainBytes', 7: 'processedBytes', 8: 'envelope', 9: 'encodedEnvelope'}, family=True)
        for rid, name, proof in ([(0xBA, 'passwordHash', (0xCF, 0xD2)), (0xBB, 'encoding', (0xCF, 0xD2)), (0xBC, 'isLegacy', (0xCF, 0xD1)),
                                  (0xC1, 'passwordHash', (0xD3, 0xD4)), (0xC2, 'encoding', (0xD3, 0xD4)), (0xC3, 'random', (0xD3, 0xD4))] if old else
                                 [(0x1AF, 'passwordHash', (0x397, 0x39A)), (0x1B0, 'encoding', (0x397, 0x39A)), (0x1B3, 'passwordHash', (0x39E, 0x39F)),
                                  (0x1B4, 'encoding', (0x39E, 0x39F)), (0x1B5, 'random', (0x39E, 0x39F))]):
            field(rid, name, 'Reader/writer state whose role is proven by construction and authenticated envelope processing.', proof)
        if old:
            for rid, name, reason, proof in [
                (0xA3, 'EncryptedTracePrefix', 'Exact trace marker used by prefix detection and encode/decode.', (0xB5, 0xB7, 0xB9)),
                (0xA4, 'SaltText', 'Text encoded as the fixed trace salt at construction.', (0xB1,)),
                (0xA5, 'DefaultIterations', 'Default trace derivation count of one.', (0xB1,)),
                (0xAC, 'Base64HeaderLength', 'Twenty salt/IV bytes occupy 28 Base64 characters; the shape check requires a longer string including its marker.', (0xC3,)),
                (0xAD, 'SaltLength', 'Eight-byte salt split from the serialized envelope.', (0xC6,)),
                (0xAE, 'InitializationVectorLength', 'Twelve-byte initialization vector split after the salt.', (0xC6,)),
                (0xAF, 'Marker', 'Colon text-format marker checked before Base64 decoding.', (0xC1, 0xC3, 0xC5)),
                (0xB3, 'MinimumSaltLength', 'The password generator requires at least sixteen salt bytes.', (0xC7, 0xC9)),
                (0xB4, 'DerivedHashLength', 'Thirty-two derived bytes follow the salt.', (0xCA, 0xC9)),
                (0xB5, 'IterationCount', 'The password hash helper uses 100000 iterations.', (0xCA,))]:
                field(rid, name, reason, proof, literal=True)
        b.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
