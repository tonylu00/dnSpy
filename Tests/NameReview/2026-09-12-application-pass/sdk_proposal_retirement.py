"""Retire rejected SDK proposals in the review ledger; never write source/maps."""
import copy
import hashlib
import pathlib
import xml.etree.ElementTree as ET
from review_ledger import require_identity, proposal_preimage


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest().upper()


def key(module, token):
    return module.replace('\\', '/').casefold(), int(token, 16)


def load_sdk_symbols(map_path):
    """Read the map-bound whitelist and verify every physical SDK module hash."""
    mapping = ET.parse(map_path).getroot()
    root = pathlib.Path(mapping.attrib['InputDirectory']).resolve()
    whitelist = pathlib.Path(mapping.attrib['SdkNameWhitelist'])
    expected = mapping.attrib['SdkNameWhitelistSha256']
    if not expected or digest(whitelist) != expected:
        raise ValueError('Stale map-bound SDK whitelist')
    document = ET.parse(whitelist).getroot()
    if document.tag != 'SdkNameWhitelist' or document.get('Version') != '1':
        raise ValueError('Unsupported SDK whitelist')
    result = {}
    modules = set()
    for module in document.findall('Module'):
        relative = pathlib.Path(module.attrib['Path'].replace('\\', '/'))
        physical = (root / relative).resolve()
        if relative.is_absolute() or not physical.is_relative_to(root):
            raise ValueError('SDK module leaves the application tree')
        if not all(module.get(k) for k in ('Identity', 'Mvid', 'Sha256')):
            raise ValueError('SDK module lacks physical identity')
        mk = module.attrib['Path'].replace('\\', '/').casefold()
        if mk in modules or digest(physical) != module.attrib['Sha256']:
            raise ValueError('Duplicate or stale SDK physical module')
        modules.add(mk)
        for symbol in module:
            k = key(module.attrib['Path'], symbol.attrib['Token'])
            kind = {2: 'Type', 4: 'Field', 6: 'Method'}.get(k[1] >> 24)
            if (k in result or kind != symbol.get('Kind') or
                    not all(symbol.get(a) for a in ('Name', 'Signature', 'Reason'))):
                raise ValueError('Duplicate or unsupported SDK symbol identity')
            result[k] = dict(WhitelistSha256=expected, Module=dict(module.attrib), Symbol=dict(symbol.attrib))
    return result


def retire_sdk_proposal(previous, reviewed, mapped_entry, sdk_proof, whitelist_sha):
    """Replace an unapplied alias with explicit preservation and keep its history."""
    require_identity(previous, reviewed)
    if (not previous.get('NewName') or previous.get('Unresolved') or mapped_entry is not None or
            not reviewed.get('RetireRejectedSdkProposal') or reviewed.get('NewName') or reviewed.get('Unresolved') or
            reviewed.get('UnresolvedReason') or reviewed.get('ReviewDisposition') != 'preserve' or not reviewed.get('Reason')):
        raise ValueError('SDK retirement requires an unapplied proposal and explicit preservation')
    if reviewed.get('PreviousProposalEvidence') != proposal_preimage(previous):
        raise ValueError('SDK retirement requires the exact previous decision and scopes')
    if not sdk_proof or sdk_proof.get('WhitelistSha256') != whitelist_sha or not whitelist_sha:
        raise ValueError('SDK retirement requires the current bound whitelist')
    module, symbol = sdk_proof.get('Module', {}), sdk_proof.get('Symbol', {})
    if any(module.get(k) != previous.get(k) for k in ('Identity', 'Mvid', 'Sha256')):
        raise ValueError('SDK retirement has a foreign physical module')
    kind = {2: 'Type', 4: 'Field', 6: 'Method'}.get(int(previous['Token'], 16) >> 24)
    if (key(module.get('Path', ''), symbol.get('Token', '0')) != key(previous['Module'], previous['Token']) or
            not kind or symbol.get('Kind') != kind or symbol.get('Name') != previous['OriginalName'] or
            symbol.get('Signature') != previous['Signature'] or not symbol.get('Reason')):
        raise ValueError('SDK retirement has a different protected symbol')
    for label, position in (('ParameterNames', 'Sequence'), ('LocalNames', 'Index')):
        for record in (previous, reviewed):
            entries = record.get(label, [])
            if len({e[position] for e in entries}) != len(entries):
                raise ValueError('Duplicate SDK proposal scope position')
        current = {e[position]: e for e in reviewed.get(label, [])}
        for old in previous.get(label, []):
            now = current.get(old[position])
            if now is None or any(old.get(k) != now.get(k) for k in ('OriginalName', 'ExpectedType', 'HasMetadata', 'Type') if k in old):
                raise ValueError('SDK proposal scope preimage differs')
        if any(e.get('NewName') for e in reviewed.get(label, [])):
            raise ValueError('SDK preservation cannot carry scope aliases')
    result = copy.deepcopy(previous)
    result.update(NewName='', Unresolved=False, UnresolvedReason='', NeedsReadableName=reviewed['NeedsReadableName'],
                  ReviewDisposition='preserve', Reason=reviewed['Reason'])
    for label in ('ParameterNames', 'LocalNames'):
        if label in previous:
            for entry in result[label]:
                entry['NewName'] = ''
    result.setdefault('RejectedSdkProposals', []).append(dict(
        PreviousProposal=proposal_preimage(previous), SdkProof=copy.deepcopy(sdk_proof), Evidence=reviewed['Reason']))
    result['SdkProtection'] = copy.deepcopy(sdk_proof)
    return result
