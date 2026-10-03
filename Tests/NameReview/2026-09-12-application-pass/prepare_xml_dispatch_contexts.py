"""Prepare naming evidence from native physical serializer reference/body reports.

Writes review specifications and evidence only; never modifies source or binaries.
Element and attribute roles require a proved XML reader -> helper -> boxed value
or property setter chain. Local-slot dispositions use exhaustive original IL uses.
"""
import argparse
import hashlib
import json
import pathlib
import re


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    with pathlib.Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def operand(instruction):
    value = instruction['Operand']
    return value if isinstance(value, dict) else {}


def slot(instruction):
    if instruction['OpCode'].startswith(('ldloc.', 'stloc.')):
        suffix = instruction['OpCode'].rsplit('.', 1)[1]
        if suffix.isdigit():
            return int(suffix)
    return operand(instruction).get('LocalSlot')


def prepare(config):
    root = pathlib.Path(config['TargetRoot']).resolve()
    snapshots = {}
    provenance = []
    for module, paths in config['Reports'].items():
        physical = (root / module).resolve()
        if not physical.is_relative_to(root):
            raise ValueError('Module leaves physical application tree')
        sha = hashlib.sha256(physical.read_bytes()).hexdigest().upper()
        snapshots[module] = {'Methods': {}, 'Reports': []}
        for path in paths:
            data = read(path)
            if pathlib.Path(data['Input']).resolve() != physical or data['Sha256'] != sha:
                raise ValueError('Stale or wrong physical body report: ' + path)
            identity = (data['Identity'], data['Mvid'], data['Sha256'])
            previous = snapshots[module].get('Identity')
            if previous and identity != previous:
                raise ValueError('Mixed physical report identities')
            snapshots[module]['Identity'] = identity
            snapshots[module]['Reports'].append(path)
            provenance.append(dict(Path=path, Sha256=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest().upper()))
            if 'ReferenceScope' in data:
                scope = data['ReferenceScope']
                if scope['Kind'] != 'CompleteStaticReferencesInPhysicalModule':
                    raise ValueError('Capped reference evidence is insufficient')
                snapshots[module]['ReferenceScope'] = scope
            for method in data['Methods']:
                old = snapshots[module]['Methods'].get(method['Token'])
                if old and (old['Signature'] != method['Signature'] or old['Instructions'] != method['Instructions']):
                    raise ValueError('Conflicting native method bodies')
                snapshots[module]['Methods'][method['Token']] = method
    decisions, contexts, local_dispositions = [], [], []
    pending = read(config['PendingContexts'])['Pending']
    for row in pending:
        module = row['Module']
        snap = snapshots[module]
        if snap['Identity'] != (row['Identity'], row['Mvid'], row['Sha256']):
            raise ValueError('Stale pending physical row')
        method = snap['Methods'][row['ReaderToken']]
        if method['Signature'].split(' ', 1)[0] != row['Enum']:
            raise ValueError('Incorrect enum return contract')
        if not any(operand(i).get('Token') == row['FieldToken'] and i['OpCode'] == 'ldsfld' for i in method['Instructions']):
            raise ValueError('No exact helper/table reference')
        roles, chains = set(), []
        for reference in method['IncomingReferences']:
            if reference['Kind'] != 'Instruction':
                continue
            caller = snap['Methods'][reference['OwnerToken']]
            ins = caller['Instructions']
            positions = [i for i, value in enumerate(ins) if value['Offset'] == reference['Offset']]
            if len(positions) != 1:
                raise ValueError('Reference offset missing from caller')
            i = positions[0]
            if operand(ins[i]).get('Token') != row['ReaderToken']:
                raise ValueError('Wrong physical caller operand')
            before, after = operand(ins[i-1]).get('Text', ''), operand(ins[i+1]).get('Text', '')
            role = None
            if before == 'System.String System.Xml.XmlReader::ReadElementString()' and ins[i+1]['OpCode'] == 'box' and after == row['Enum']:
                role = row['Enum'].split('Knx.Ets.Xml.ObjectModel.', 1)[-1].replace('.', '').replace('/', '') + 'Element'
            elif before == 'System.String System.Xml.XmlReader::get_Value()':
                match = re.fullmatch(r'System.Void Knx.Ets.Xml.ObjectModel\.(.+)::set_(\w+)\(' + re.escape(row['Enum']) + r'\)', after)
                if match and ins[i+1]['OpCode'] == 'callvirt':
                    role = match[1].replace('.', '').replace('/', '') + match[2] + 'Attribute'
            if role:
                roles.add(role)
                chains.append(dict(CallerToken=caller['Token'], CallerSignature=caller['Signature'],
                                   Instructions=ins[max(0, i-2):i+3], Role=role))
        if len(roles) != 1:
            raise ValueError('Missing or ambiguous reader role: ' + str(row))
        name = roles.pop() + 'XmlNameDispatchTable'
        decisions.append(dict(Kind='Fields', Module=module, Token=row['FieldToken'], NewName=name,
                              Reason=f"Exact reader {row['ReaderToken']} initializes and queries this XML-name dispatch dictionary. Complete static references in the physical module prove its {name.removesuffix('XmlNameDispatchTable')} role through XML ReadElementString/box or Reader.Value/property-setter chains. Generic Read1_Object also calls the reader; this role does not imply exclusivity. Runtime field names remain original."))
        # Verify the same parameter/local flow as the previously reviewed unique tables.
        ins = method['Instructions']
        if [i['OpCode'] for i in ins[:3]] != ['ldarg.1', 'dup', 'stloc.0']:
            raise ValueError('Unexpected serialized-name input dataflow')
        lookup = [i for i, value in enumerate(ins) if '::TryGetValue(System.String,System.Int32&)' in operand(value).get('Text', '')]
        if len(lookup) != 1 or slot(ins[lookup[0]-2]) != 0 or slot(ins[lookup[0]-1]) != 1 or not ins[lookup[0]-1]['OpCode'].startswith('ldloca'):
            raise ValueError('Unproved name/dispatch-index local flow')
        decisions.append(dict(Kind='Methods', Module=module, Token=method['Token'],
                              ParameterNames={'1': 'xmlValue'}, LocalNames={'0': 'xmlName', '1': 'dispatchIndex'},
                              Reason=f"Preserve generated reader name {method['Signature'].split('::')[-1]}. Parameter 1 is the serialized enum value copied to local 0; exact table {row['FieldToken']} receives local 0 as XML name and local 1 by address for the TryGetValue dispatch index. Caller chains prove {name.removesuffix('XmlNameDispatchTable')} context."))
        contexts.append(dict(**row, ResolvedFieldAlias=name, ReferenceScope=snap['ReferenceScope'],
                             IncomingReferences=method['IncomingReferences'], RoleChains=chains))
        for local in method['Locals']:
            if local['Slot'] < 2:
                continue
            uses = [i for i in ins if slot(i) == local['Slot']]
            if uses:
                raise ValueError('Unexpected additional live enum-reader local')
            local_dispositions.append(dict(Module=module, Token=method['Token'], Signature=method['Signature'],
                                          LocalIndex=local['Slot'], ExpectedType=local['Type'],
                                          Disposition='UnusedLocalSlot', IlReferences=0,
                                          Reason='The complete native method body has no load/store/address operand for this slot. It carries no application dataflow and receives no invented semantic alias.'))
    previous_pending = read(config['PendingLocals'])['Pending']
    for row in previous_pending:
        snap = snapshots[row['Module']]
        if snap['Identity'] != (row['Identity'], row['Mvid'], row['Sha256']):
            raise ValueError('Stale pending local')
        method = snap['Methods'][row['Token']]
        local = next(l for l in method['Locals'] if l['Slot'] == row['LocalIndex'])
        if method['Signature'] != row['Signature'] or local['Type'] != row['ExpectedType']:
            raise ValueError('Local signature mismatch')
        ins = method['Instructions']
        uses = [i for i in ins if slot(i) == row['LocalIndex']]
        disposition = dict(row, IlReferences=len(uses))
        if not uses:
            disposition.update(Disposition='UnusedLocalSlot', Reason='Zero load/store/address references in the complete native IL body. Retained unused slot, no semantic alias needed; source decompilation eliminates it.')
        else:
            if row['LocalIndex'] != 1 or [i['OpCode'] for i in ins[2:5]] != ['ldarg.1', 'stloc.1', 'ldloc.1'] or sum(i['OpCode'].startswith('stloc') for i in uses) != 1:
                raise ValueError('Unproved enum snapshot local')
            enum = row['ExpectedType'].rsplit('.', 1)[-1]
            alias = {'SCRIPTITEM': 'scriptItemValue', 'ElementPropertyFlags': 'elementPropertyFlagValue', 'MoveFileFlag': 'moveFileFlagValue'}[enum]
            disposition.update(Disposition='rename', NewName=alias, Reason='Local 1 is assigned once from enum parameter 1 and used for switch/equality selection of an XML name. It is the enum input snapshot, not an injected control-flow state.')
            decisions.append(dict(Kind='Methods', Module=row['Module'], Token=row['Token'], LocalNames={'1': alias}, Reason=disposition['Reason']))
        local_dispositions.append(disposition)
    spec = {key: config[key] for key in ('TargetRoot', 'ContractReferenceSha256', 'Inventories')}
    spec['Rows'] = decisions
    return spec, dict(Format=1, Resolved=contexts, NativeReports=provenance), dict(Format=1, PreviousPending=len(previous_pending), Reviewed=local_dispositions)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('config', 'spec', 'evidence', 'locals'):
        parser.add_argument('--' + flag, required=True)
    args = parser.parse_args()
    spec, evidence, locals_ = prepare(read(args.config))
    for path, value in ((args.spec, spec), (args.evidence, evidence), (args.locals, locals_)):
        write(path, value)
    print('Decisions:', len(spec['Rows']), 'resolved tables:', len(evidence['Resolved']), 'reviewed local slots:', len(locals_['Reviewed']))
