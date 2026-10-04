"""Retire unapplied implementation proposals using native map-bound CLR/SDK proof.

This changes review history only. Native zero-edit/map-equality gates remain
mandatory; no source, binaries, maps or applied scoped aliases are changed here.
"""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from review_ledger import require_identity, proposal_preimage
from sdk_proposal_retirement import digest, key, load_sdk_symbols


def require(value, message):
    if not value:
        raise ValueError(message)


def load_contract_sdk_evidence(map_path, evidence_path, expected_hash, contract_hash):
    require(expected_hash and digest(evidence_path) == expected_hash, 'Stale native SDK contract evidence')
    proof = json.loads(Path(evidence_path).read_text(encoding='utf-8-sig'))
    mapping = ET.parse(map_path).getroot()
    root = Path(mapping.attrib['InputDirectory']).resolve()
    require(proof.get('Format') == 1 and proof.get('Kind') == 'PhysicalSdkContractProtectionEvidence', 'Unsupported native contract evidence')
    require(Path(proof['TargetRoot']).resolve() == root and proof['MapSha256'] == digest(map_path), 'Native contract proof has a different map/root')
    sdk_hash = mapping.attrib['SdkNameWhitelistSha256']
    require(proof['SdkNameWhitelistSha256'] == sdk_hash and proof['ContractReferenceSha256'] == contract_hash,
            'Native contract evidence has stale SDK/contract bindings')
    require(digest(proof['Seeds']) == proof['SeedsSha256'], 'Native contract seed file changed')
    seeds = json.loads(Path(proof['Seeds']).read_text(encoding='utf-8-sig'))
    require(seeds['Format'] == 1 and seeds['Kind'] in ('SymbolReview', 'MethodReview') and
            Path(seeds['TargetRoot']).resolve() == root and seeds['ContractReferenceSha256'] == contract_hash,
            'Native contract seed binding differs')
    seed_index = {}
    for seed in seeds['Methods']:
        sk = key(seed['Module'], seed['Token'])
        require(sk not in seed_index, 'Duplicate native contract seed')
        seed_index[sk] = seed
    scope = {}
    for module in proof['Scope']:
        relative = Path(module['Module'].replace('\\', '/'))
        path = (root / relative).resolve()
        mk = key(module['Module'], '0')[0]
        require(not relative.is_absolute() and path.is_relative_to(root) and mk not in scope, 'Invalid/duplicate native physical scope')
        require(digest(path) == module['Sha256'], 'Native contract physical input changed')
        scope[mk] = module
    sdk = load_sdk_symbols(map_path)

    def validate_definition(definition):
        dk = key(definition['Module'], definition['Token'])
        require(dk[1] >> 24 == 6 and dk[0] in scope, 'Native contract definition leaves its physical scope')
        require(all(definition[k] == scope[dk[0]][k] for k in ('Identity', 'Mvid', 'Sha256')),
                'Native contract definition has a different physical identity')
        require(all(definition.get(k) for k in ('Type', 'Signature', 'OriginalName')), 'Incomplete native contract definition')
        return dk

    result, seen = {}, set()
    for record in proof['Definitions']:
        definition = record['Definition']
        dk = validate_definition(definition)
        require(dk not in seen and dk in seed_index, 'Duplicate/foreign native contract definition')
        seen.add(dk)
        require_identity(seed_index[dk], definition)
        if record['Status'] != 'ProtectedBySdkFamilyMember':
            continue
        require(record['Family'] and not record['Blockers'] and record['ProtectedMembers'], 'Unsupported native SDK family')
        if seed_index[dk].get('ContractFamily'):
            require(seed_index[dk]['ContractFamily'] == record['Family'], 'Native family differs from its seed')
        members = {}
        for member in record['Members']:
            mk = validate_definition(member)
            require(mk not in members, 'Duplicate native family member')
            members[mk] = member
        require(dk in members and members[dk] == definition, 'Native family omits/differs from its requested definition')
        family_bytes = '\n'.join(m['Module'].replace('\\', '/') + '|' + format(int(m['Token'], 16), '08X')
                                 for m in record['Members']).encode('utf-8')
        require(hashlib.sha256(family_bytes).hexdigest().upper() == record['Family'], 'Native family membership hash differs')
        protected_keys = set()
        for member in record['ProtectedMembers']:
            mk = validate_definition(member)
            require(mk in members and members[mk] == member and mk not in protected_keys and member['SdkProtected'],
                    'Protected definition is not an exact member of the native family')
            protected_keys.add(mk)
            binding = sdk.get(mk)
            require(binding and binding['Symbol'] == member['SdkSymbol'], 'Native protected member differs from the current SDK whitelist')
            require(all(binding['Module'][k] == member[k] for k in ('Identity', 'Mvid', 'Sha256')) and
                    binding['Symbol']['Signature'] == member['Signature'] and binding['Symbol']['Name'] == member['OriginalName'],
                    'Native protected member has a foreign SDK identity/signature')
        require({mk for mk, member in members.items() if member['SdkProtected']} == protected_keys,
                'Native family omits a claimed SDK-protected member')
        result[dk] = {'NativeEvidence': {'Path': str(Path(evidence_path).resolve()), 'Sha256': expected_hash,
                                       'SeedsSha256': proof['SeedsSha256'], 'MapSha256': proof['MapSha256']},
                      'ContractReferenceSha256': contract_hash, 'WhitelistSha256': sdk_hash, 'Family': copy.deepcopy(record)}
    require(seen == set(seed_index), 'Native contract proof does not account for every seed')
    return result


def retire_contract_sdk_proposal(previous, reviewed, mapped_entry, proof, whitelist_hash, contract_hash):
    require_identity(previous, reviewed)
    require(previous.get('NewName') and not previous.get('Unresolved') and mapped_entry is None,
            'SDK contract retirement requires an entirely unmapped prior proposal')
    require(reviewed.get('RetireRejectedContractSdkProposal') and reviewed.get('ReviewDisposition') == 'preserve' and
            not reviewed.get('NewName') and not reviewed.get('Unresolved') and not reviewed.get('UnresolvedReason') and
            not reviewed.get('NeedsReadableName') and reviewed.get('Reason'), 'SDK contract retirement requires explicit preservation')
    require(reviewed.get('PreviousProposalEvidence') == proposal_preimage(previous), 'SDK contract retirement requires the exact prior decision/scopes')
    require(proof and proof['WhitelistSha256'] == whitelist_hash and proof['ContractReferenceSha256'] == contract_hash,
            'SDK contract retirement requires current native SDK/family proof')
    require_identity(previous, proof['Family']['Definition'])
    require(proof['Family']['Status'] == 'ProtectedBySdkFamilyMember' and proof['Family']['Family'] and
            not proof['Family']['Blockers'] and proof['Family']['ProtectedMembers'], 'SDK contract family protection is unresolved')
    if previous.get('ContractFamily'):
        require(previous['ContractFamily'] == proof['Family']['Family'], 'Previous proposal belongs to a different contract family')
    for label, position in (('ParameterNames', 'Sequence'), ('LocalNames', 'Index')):
        for record in (previous, reviewed):
            entries = record.get(label, [])
            require(len({entry[position] for entry in entries}) == len(entries), 'Duplicate contract proposal scope position')
        current = {entry[position]: entry for entry in reviewed.get(label, [])}
        require(set(current) == {entry[position] for entry in previous.get(label, [])}, 'Contract preservation cannot add/drop scope positions')
        for old in previous.get(label, []):
            now = current.get(old[position])
            require(now is not None and all(old.get(k) == now.get(k) for k in
                    ('OriginalName', 'ExpectedType', 'HasMetadata', 'Type') if k in old), 'Contract proposal scope preimage differs')
        require(not any(entry.get('NewName') for entry in reviewed.get(label, [])), 'Contract preservation cannot carry scope aliases')
    result = copy.deepcopy(previous)
    result.update(NewName='', Unresolved=False, UnresolvedReason='', NeedsReadableName=False,
                  ReviewDisposition='preserve', Reason=reviewed['Reason'])
    for label in ('ParameterNames', 'LocalNames'):
        for entry in result.get(label, []):
            entry['NewName'] = ''
    result.setdefault('RejectedSdkContractProposals', []).append({'PreviousProposal': proposal_preimage(previous),
                                                                 'NativeProof': copy.deepcopy(proof), 'Evidence': reviewed['Reason']})
    result['SdkContractProtection'] = copy.deepcopy(proof)
    return result


def preserve_contract_sdk_method(reviewed, mapped_entry, proof, whitelist_hash, contract_hash):
    """Record a new preservation decision only for an exact complete SDK family."""
    require(mapped_entry is None and reviewed.get('PreserveSdkContractMethod') and
            reviewed.get('ReviewDisposition') == 'preserve' and reviewed.get('Reason') and
            not any(reviewed.get(k) for k in ('NewName', 'Unresolved', 'UnresolvedReason', 'NeedsReadableName',
                                             'RetireRejectedContractSdkProposal', 'PreviousProposalEvidence')),
            'New SDK contract preservation requires an unmapped explicit preservation decision')
    require(not any(entry.get('NewName') for label in ('ParameterNames', 'LocalNames') for entry in reviewed.get(label, [])),
            'SDK contract preservation cannot carry scope aliases')
    require(proof and proof['WhitelistSha256'] == whitelist_hash and proof['ContractReferenceSha256'] == contract_hash,
            'New SDK contract preservation requires current native proof')
    family = proof['Family']
    require_identity(reviewed, family['Definition'])
    require(family['Status'] == 'ProtectedBySdkFamilyMember' and family['Family'] and
            not family['Blockers'] and family['ProtectedMembers'], 'New SDK contract preservation is unresolved')
    require(not reviewed.get('ContractFamily') or reviewed['ContractFamily'] == family['Family'], 'New preservation family differs')
    result = copy.deepcopy(reviewed)
    result.pop('PreserveSdkContractMethod')
    result['SdkContractProtection'] = copy.deepcopy(proof)
    return result
