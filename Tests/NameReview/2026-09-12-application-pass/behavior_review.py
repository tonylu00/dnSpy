"""Portable staging support for explicit, evidence-backed naming decisions.

Never infers names or modifies ETS. Each batch binds a specific base map,
physical module, metadata inventory and graph. Existing aliases cannot be
replaced implicitly; parameter/local decisions are merged without dropping old
ones. Unmappable decisions remain visible in the pending evidence ledger.
"""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


class BehaviorReview:
    def __init__(self, root, version, base_version, module_id, prefix, prior_review=None):
        self.root = Path(root)
        self.version = version
        self.base = self.root / f'names{version}-staged-v{base_version}.xml'
        self.base_hash = sha(self.base)
        document = ET.parse(self.base).getroot()
        self.target = Path(document.attrib['InputDirectory'])
        self.db = sqlite3.connect((self.root / f'graph{version}-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
        manifest = json.loads(self.db.execute('SELECT data FROM meta').fetchone()[0])
        self.module = next(m for m in manifest['Modules'] if m['Id'] == module_id)
        self.module_id = module_id
        self.source_root = Path(manifest['Export']).parent
        self.verified_sources = {}
        binary = Path(self.module['Input'])
        self.relative = binary.relative_to(self.target).as_posix()
        if sha(binary) != self.module['Sha256']:
            raise ValueError('Stale physical input: ' + str(binary))
        self.entries = {}
        for kind, suffix in [('Methods', 'methods'), ('Types', 'types'), ('Fields', 'fields')]:
            inventory = self.read(prefix[kind] if isinstance(prefix, dict) else f'{prefix}-{suffix}.json')
            self.entries[kind] = {r['Token']: r for r in inventory[kind]}
            for row in self.entries[kind].values():
                if row['Module'].replace('\\', '/') != self.relative or row['Sha256'] != self.module['Sha256'] or row['Mvid'] != self.module['Mvid']:
                    raise ValueError('Inventory is from a different physical module')
        self.aliases = {}
        for module in document:
            if module.attrib['Path'].replace('\\', '/') == self.relative and (
                    module.get('Sha256') != self.module['Sha256'] or module.get('Mvid') != self.module['Mvid']):
                raise ValueError('Base map selects a different physical module')
            for row in module:
                self.aliases[(module.attrib['Path'].replace('\\', '/'), row.attrib['Token'])] = row
        self.prior = json.loads(Path(prior_review).read_text(encoding='utf-8')) if prior_review else {
            'Format': 1, 'Kind': 'SymbolReview', 'TargetRoot': str(self.target), 'Methods': [], 'Types': [], 'Fields': []}
        if Path(self.prior['TargetRoot']).resolve() != self.target.resolve():
            raise ValueError('Prior review belongs to a different target tree')
        self.delta = {k: copy.deepcopy(v) for k, v in self.prior.items() if k in ['Format', 'Kind', 'TargetRoot', 'ContractReferenceSha256']}
        self.delta.update(Methods=[], Types=[], Fields=[])
        self.decisions, self.pending = [], []
        self.selected = set()
        self.accessor_sources = {}
        self.usage_sources = {}

    def read(self, name):
        return json.loads((self.root / name).read_text(encoding='utf-8-sig'))

    def bind_accessor_sources(self, report_path, tokens):
        """Use tool-derived property/event ownership when source omits a getter token.

        This supplies source evidence only, never a naming permission or blocker
        override. The report's physical method identity must match the inventory.
        Cached graphs and ETS source remain unchanged.
        """
        path = Path(report_path)
        report = json.loads(path.read_text(encoding='utf-8-sig'))
        if report['Kind'] != 'AccessorReview' or Path(report['TargetRoot']).resolve() != self.target.resolve():
            raise ValueError('Accessor evidence belongs to a different target tree')
        report_hash = sha(path)
        staged = {}
        for token in tokens:
            key = f'0x{token:08X}'
            rows = [r for r in report['Methods'] if r['Module'].replace('\\', '/') == self.relative and r['Token'] == key]
            proofs = [r for r in report['AccessorEvidence'] if r['Module'].replace('\\', '/') == self.relative and r['MethodToken'] == key]
            if len(rows) != 1 or len(proofs) != 1:
                raise ValueError('Missing or ambiguous accessor evidence: ' + key)
            row, proof = rows[0], proofs[0]
            entry = self.entries['Methods'][key]
            if any(row[k] != entry[k] for k in ('Identity', 'Mvid', 'Sha256', 'Signature', 'OriginalName')):
                raise ValueError('Accessor evidence selects a different physical method: ' + key)
            if proof['MethodSignature'] != entry['Signature'] or proof['MethodName'] != entry['OriginalName']:
                raise ValueError('Accessor evidence signature mismatch: ' + key)
            table = {'Property': 0x17000000, 'Event': 0x14000000}.get(proof['OwnerKind'])
            if table is None or int(proof['OwnerToken'], 16) & 0xFF000000 != table:
                raise ValueError('Accessor evidence owner kind mismatch: ' + key)
            if proof['AccessorRole'] not in ({'get', 'set'} if proof['OwnerKind'] == 'Property' else {'add', 'remove', 'raise'}):
                raise ValueError('Accessor evidence role mismatch: ' + key)
            if key in self.accessor_sources:
                raise ValueError('Accessor source already bound: ' + key)
            staged[key] = {'Path': str(path), 'Sha256': report_hash, **proof}
        self.accessor_sources.update(staged)

    def bind_usage_sources(self, inspection_path, bindings):
        """Bind an inlined method/field to an exact, inspected caller location.

        Decompilation can hide a lambda implementation or captured field. Its
        physical graph edge and current IL must agree before caller source is
        accepted as evidence. This never changes naming eligibility or metadata.
        """
        path = Path(inspection_path)
        report = json.loads(path.read_text(encoding='utf-8-sig'))
        if Path(report['Input']).resolve() != Path(self.module['Input']).resolve() or any(
                report[k] != self.module[k] for k in ('Mvid', 'Sha256')):
            raise ValueError('Usage inspection selects a different physical module')
        methods = {r['Token']: r for r in report['Methods']}
        if len(methods) != len(report['Methods']):
            raise ValueError('Duplicate inspected method')
        staged = {}
        for token, caller_token in bindings.items():
            key, caller_key = f'0x{token:08X}', f'0x{caller_token:08X}'
            kind = {0x06000000: 'Methods', 0x04000000: 'Fields'}.get(token & 0xFF000000)
            if kind is None or key in self.usage_sources:
                raise ValueError('Unsupported or duplicate usage binding')
            entry = self.entries[kind][key]
            caller = self.entries['Methods'][caller_key]
            if report['Identity'] != entry['Identity'] or methods[caller_key]['Signature'] != caller['Signature']:
                raise ValueError('Usage inspection signature mismatch')
            if kind == 'Methods' and methods[key]['Signature'] != entry['Signature']:
                raise ValueError('Implementation inspection signature mismatch')
            sid, caller_id = self.module_id + ':' + key, self.module_id + ':' + caller_key
            symbols = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM symbols WHERE id=?', (sid,))]
            if len(symbols) != 1 or symbols[0]['Signature'] != entry['Signature']:
                raise ValueError('Usage graph selects a different definition')
            allowed = {'ldftn', 'ldvirtftn', 'newobj'} if kind == 'Methods' else {'ldfld', 'ldflda', 'stfld', 'ldsfld', 'ldsflda', 'stsfld'}
            edges = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM edges WHERE source=? AND target=?', (caller_id, sid))]
            edges = [e for e in edges if e['Operation'] in allowed]
            if not edges:
                raise ValueError('No exact implementation usage edge')
            instructions = {i['Offset']: i for i in methods[caller_key]['Instructions']}
            for edge in edges:
                target = edge['Target']
                if target['Id'] != sid or target['Status'] != 'input' or target.get('Error') or target['Assembly'] != entry['Identity'] or Path(target['PhysicalModule']).resolve() != Path(report['Input']).resolve():
                    raise ValueError('Usage edge leaves the selected physical module')
                instruction = instructions.get(edge['Offset'])
                if not instruction or instruction['OpCode'] != edge['Operation'] or instruction.get('Operand', {}).get('Text') != target['Signature']:
                    raise ValueError('Usage graph and inspected IL disagree')
            rows = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM source WHERE id=?', (caller_id,))]
            if not rows or any(r['Kind'] not in ('MethodDeclaration', 'ConstructorDeclaration') for r in rows):
                raise ValueError('Usage caller has no direct source declaration')
            self.source(caller_token)  # Apply the normal source root/hash checks.
            staged[key] = {'Inspection': str(path), 'Sha256': sha(path), 'SourceId': caller_id, 'Edges': edges}
        self.usage_sources.update(staged)

    def source(self, token):
        key = f'0x{token:08X}'
        sid = self.module_id + ':' + key
        rows = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM source WHERE id=?', (sid,))]
        accessor = usage = None
        if not rows and key in self.accessor_sources:
            accessor = self.accessor_sources[key]
            owner = self.module_id + ':' + accessor['OwnerToken']
            rows = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM source WHERE id=?', (owner,))]
            allowed = {'PropertyDeclaration', 'IndexerDeclaration'} if accessor['OwnerKind'] == 'Property' else {'EventDeclaration', 'EventFieldDeclaration'}
            if any(row['Kind'] not in allowed for row in rows):
                raise ValueError('Accessor source declaration kind mismatch: ' + sid)
        if not rows and key in self.usage_sources:
            usage = self.usage_sources[key]
            rows = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM source WHERE id=?', (usage['SourceId'],))]
        if not rows:
            raise ValueError('No source declaration: ' + sid)
        for row in rows:
            path = (self.source_root / row['Source']).resolve()
            if not path.is_relative_to(self.source_root.resolve()):
                raise ValueError('Source leaves export root')
            if path not in self.verified_sources:
                self.verified_sources[path] = sha(path)
            if self.verified_sources[path] != row['Sha256']:
                raise ValueError('Stale source: ' + str(path))
        return [{'Id': sid, 'Path': r['Source'], 'Line': r['Line'], 'Sha256': r['Sha256'],
                 **({'DeclarationId': self.module_id + ':' + accessor['OwnerToken'], 'AccessorEvidence': accessor} if accessor else {}),
                 **({'SourceId': usage['SourceId'], 'UsageEvidence': usage} if usage else {})} for r in rows]

    def add(self, kind, token, name, reason, parameters=None, locals_=None, evidence=(), contract=None, replace_alias=None):
        key = f'0x{token:08X}'
        if (kind, key) in self.selected:
            raise ValueError('Duplicate decision: ' + key)
        self.selected.add((kind, key))
        row = copy.deepcopy(self.entries[kind][key])
        if contract is not None:
            if kind != 'Methods' or any(row[k] != contract[k] for k in ['Module', 'Token', 'Signature', 'Identity', 'Mvid', 'Sha256']):
                raise ValueError('Family inventory does not bind this exact method')
            row['ContractFamily'] = contract['ContractFamily']
            row['MappingBlocker'] = contract['MappingBlocker']
        base = self.aliases.get((self.relative, key))
        existing = base.get('NewName') if base is not None else None
        if replace_alias is not None and (not existing or existing != replace_alias or not name or name == existing):
            raise ValueError('Stale or unnecessary alias replacement: ' + key)
        if name and existing and name != existing and replace_alias is None:
            raise ValueError(f'Explicit replacement review required: {key} {existing} -> {name}')
        row.update(NewName=name or existing or '', Reason=reason)
        # Restore prior scoped decisions from the map, even when an inventory
        # contains blank placeholders or the old cumulative review was partial.
        if base is not None:
            for p in base.findall('Parameter'):
                match = next(r for r in row['ParameterNames'] if r['Sequence'] == int(p.get('Sequence')))
                if match['OriginalName'] != p.get('ExpectedName'):
                    raise ValueError('Stale parameter in base map')
                match['NewName'] = p.get('NewName')
            for local in base.findall('Local'):
                match = next(r for r in row['LocalNames'] if r['Index'] == int(local.get('Index')))
                if match['ExpectedType'] != local.get('ExpectedType'):
                    raise ValueError('Stale local in base map')
                match['NewName'] = local.get('NewName')
        if parameters is not None:
            if len(parameters) != len(row['ParameterNames']):
                raise ValueError('Parameter count mismatch: ' + key)
            for p, alias in zip(row['ParameterNames'], parameters):
                if not p['HasMetadata'] or p.get('NewName') and p['NewName'] != alias:
                    raise ValueError('Missing metadata or conflicting prior parameter decision')
                p['NewName'] = alias
        for index, alias in (locals_ or {}).items():
            local = next(l for l in row['LocalNames'] if l['Index'] == index)
            if local.get('NewName') and local['NewName'] != alias:
                raise ValueError('Conflicting prior local decision')
            local['NewName'] = alias
        row['LocalNames'] = [r for r in row.get('LocalNames', []) if r.get('NewName')]
        locations = self.source(token)
        for supporting in evidence:
            locations += self.source(supporting)
        proof = {'Id': self.module_id + ':' + key, 'ProposedName': row['NewName'], 'Reason': reason,
                 'Source': locations, 'Parameters': row['ParameterNames'], 'Locals': row['LocalNames']}
        if replace_alias is not None:
            proof['Replacement'] = {'Module': self.relative, 'Kind': kind[:-1], 'Token': key,
                                    'ExpectedName': replace_alias, 'NewName': name, 'Reason': reason}
            previous = next((r for r in self.prior[kind] if r['Module'] == self.relative and r['Token'] == key), None)
            if previous and previous.get('NewName') and previous['NewName'] != replace_alias:
                # A historical proposal can differ from its applied collision
                # suffix. Record both exact names; never infer one from the other.
                if any(previous.get(k) != row.get(k) for k in ('Identity', 'Mvid', 'Sha256', 'Signature', 'OriginalName')):
                    raise ValueError('Historical replacement proposal belongs to another physical symbol')
                proof['Replacement']['ExpectedReviewName'] = previous['NewName']
        blocker = row.get('MappingBlocker')
        if kind == 'Methods' and not row['NewName']:
            blocker = row['ScopedMappingBlocker']
        if blocker:
            proof['Blocker'] = blocker
            self.pending.append(proof)
        else:
            self.delta[kind].append(row)
            self.decisions.append(proof)

    def save(self, stem):
        cumulative = copy.deepcopy(self.prior)
        for kind in ['Methods', 'Types', 'Fields']:
            changes = {(r['Module'], r['Token']): r for r in self.delta[kind]}
            rows = []
            for old in cumulative[kind]:
                rows.append(changes.pop((old['Module'], old['Token']), old))
            cumulative[kind] = rows + list(changes.values())
        outputs = {'.review.json': self.delta, '.cumulative.json': cumulative, '.evidence.json': {
            'Format': 1, 'BaseMap': str(self.base), 'BaseMapSha256': self.base_hash,
            'PhysicalModule': self.module, 'Decisions': self.decisions, 'Pending': self.pending,
            'Status': 'Reviewed and staged; no ETS source/binary application or runtime validation'}}
        paths = [Path(str(stem) + suffix) for suffix in outputs]
        if any(p.exists() for p in paths):
            raise ValueError('Choose a fresh output stem')
        for suffix, data in outputs.items():
            Path(str(stem) + suffix).write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')
        print(f'{self.version}: staged {len(self.decisions)} decisions, {len(self.pending)} explicit pending decisions; no ETS writes.')
