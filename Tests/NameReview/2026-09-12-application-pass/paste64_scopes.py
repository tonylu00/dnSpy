"""Stage the independently reviewed ETS 6.4 paste call chain.

Usage: python paste64_scopes.py ARTIFACT_ROOT NEW_STEM
The 6.3 names are vocabulary references, not token or binary substitutions.
"""
from pathlib import Path
import json
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root,stem):
    b=BehaviorReview(root,'64',38,'m0146','operations64-wave32',root/'extended64-wave38.cumulative.json')
    path=root/'paste64-wave39-inspection.json'
    report=b.read(path.name)
    assert all(report[k]==b.module[k] for k in ('Input','Mvid','Sha256'))
    bodies={int(m['Token'],16):m for m in report['Methods']}
    proof={'Path':str(path),'Sha256':sha(path)}

    def method(rid,name,parameters,local,reason,caller=None):
        token=0x06000000+rid
        if caller: b.bind_usage_sources(path,{token:0x06000000+caller})
        body=bodies[token]; row=b.entries['Methods'][f'0x{token:08X}']
        assert body['Signature']==row['Signature']
        for slot in local:
            typ=next(l['ExpectedType'] for l in row['LocalNames'] if l['Index']==slot)
            assert next(l['Type'] for l in body['Locals'] if l['Slot']==slot)==typ and local_used(body,slot)
        b.add('Methods',token,name,reason,parameters,local)
        assert not b.pending,b.pending
        b.decisions[-1]['IL']={**proof,'Token':body['Token']}

    for rid,name,parameters,local,reason,caller in [
        (0x5B75,'GetClipboardItemDisplayName',('item',),{},'Reads IDisplayName.DisplayName for the extended-copy incompatibility message.',0x5B60),
        (0x5B76,'IsInitialPasteTargetCandidate',('item',),{1:'isTargetCandidate'},'Selects a NamedCollection or concrete InstallationDomObject as the first eligible target.',0x5B67),
        (0x5B77,'IsTargetCandidateForUniquenessCheck',('item',),{0:'isTargetCandidate'},'Filters the same concrete target kinds for reference-identity uniqueness checking.',0x5B67),
        (0x5B78,'IsBrokenDevice',('device',),{},'Reads Broken after OfType<Device> filters the selected objects.',0x5B67),
        (0x5B79,'IsDeviceLockedForEditing',('device',),{},'Reads IsLockedForEditing on the devices returned by GetSelfOrParentalDevices; retains the existing lack of a null guard.',0x5B67),
        (0x5B7D,'CreateMoveOperationsAndNotify',('reportProgress',),{1:'moveOperations'},'Creates a move with null options; null becomes Array.Empty<Operation>, otherwise notifies the source selection and returns operations.',0x5B5D),
        (0x5B82,'CreateConfiguredMoveOperationsAndNotify',('reportProgress',),{1:'moveOperations'},'Creates a move with captured paste options; null becomes a newly allocated empty array, otherwise notifies the source selection.',0x5B63),
        (0x5B87,'CreateCopyOperationBatch',('reportProgress',),{},'Returns a one-element factory copy result without filtering null.',0x5B65),
        (0x5B88,'RetryCopyWhenRequiredPasswordIsSet',('validationResult',),{},'Retries the captured copy only when the security service confirms the required password for the target parent project.',0x5B65),
        (0x5B8D,'IsDifferentFromFirstTarget',('item',),{},'Tests reference inequality against the captured first eligible target.',0x5B67),
    ]: method(rid,name,parameters,local,reason,caller)

    for rid,name,parameters,local,reason in [
        (0x5B59,'IsExtendedCopyLicensed',(),{0:'featureLicenses',1:'licenseEnumerator',5:'licenseCheckResult',8:'license'},'Retains the ExtendedCopy feature lookup, chain-license equality and catch-to-false checks.'),
        (0x5B5A,'CanDoPaste',('objects',),{},'Requires a nonempty selection and either valid group-address clipboard text or a permitted ETS clipboard operation.'),
        (0x5B5B,'PasteClipboardCanExecute',('objects',),{1:'singleTarget'},'Requires one target, permitted group-address link type and provider-reported valid group-address content; does not duplicate the provider parser.'),
        (0x5B5C,'PasteClipboardOperationsCanExecute',('objects',),{0:'firstValidTarget'},'Uses the validated first target to check paste or link compatibility.'),
        (0x5B5D,'DoPaste',('objects',),{0:'moveContext'},'Tries group-address text first, then ETS copy/move; clears clipboard after the normal move dialog returns.'),
        (0x5B5E,'TryHandleClipboardPaste',('target',),{0:'matchingAddressesResult'},'Resolves text group addresses in the target project; failed or empty results return false, otherwise opens copy progress.'),
        (0x5B5F,'CanDoPasteExtended',('objects',),{1:'firstValidTarget'},'Keeps license, valid target, copy-data and extended-paste compatibility checks.'),
        (0x5B60,'DoPasteExtended',('objects',),{0:'clipboardData',4:'desiredTarget',2:'extendedCopyDialog'},'Requires compatible group-address styles, opens the extended-copy dialog, then shows its wizard on OK.'),
        (0x5B61,'CanDoPasteSpecial',('objects',),{0:'firstValidTarget'},'Requires a valid target, copy data and special-paste compatibility.'),
        (0x5B62,'GetFirstValidObject',('objects',),{},'Returns FirstOrDefault from the original selection only when IsValid succeeds.'),
        (0x5B63,'DoPasteSpecial',('objects',),{2:'configuredMoveContext',1:'pasteSpecialDialog'},'Uses accepted dialog options for copy or move; preserves the absence of clipboard clearing in this path.'),
        (0x5B64,'ShowPasteCopyProgress',('data','target','pasteOptions'),{},'Forwards the clipboard item sequence and the chosen options to the copy progress overload.'),
        (0x5B65,'ShowPasteCopyProgress',('items','target','pasteOptions'),{0:'copyContext'},'Captures copy input for factory construction and the required-password retry callback.'),
        (0x5B66,'GetTargetInstallationDomObject',('first',),{0:'clipboardData',2:'namedCollection',3:'dropTarget'},'Uses an installation object directly or resolves a named collection target from clipboard item type.'),
        (0x5B67,'IsValid',('objects',),{1:'targetValidation'},'Rejects identical source/target sequences, differing eligible target references, broken devices and locked self/parental devices. Keeps the public-readable original name.'),
        (0x5B68,'TryGetDesiredTarget',('sourceType','targetItem','target'),{0:'namedCollection',1:'resolvedTarget',2:'targetArea'},'Resolves named collections through the default installation, then adapts devices/lines/segments to the backbone area or main line as required.'),
        (0x5B6D,None,('execute','canExecute'),{},'Stores nonnull execution and eligibility delegates; constructor name is unchanged.'),
    ]: method(rid,name,parameters,local,reason)

    fields=[
        (0x2BDC,'messageBoxService',0x5B54),(0x2BDD,'progressService',0x5B54),(0x2BDE,'securityService',0x5B54),
        (0x2BDF,'dialogService',0x5B54),(0x2BE0,'operationFactory',0x5B54),(0x2BE1,'licenseAndAppManager',0x5B54),
        (0x2BE2,'extendedCopyViewModelFactory',0x5B54),(0x2BE3,'clipboardToMatchingDomObjectProvider',0x5B54),
        (0x2BE4,'notificationChain',0x5B7D),(0x2BE5,'pasteCommand',0x5B54),(0x2BE6,'pasteExtendedCommand',0x5B54),(0x2BE7,'pasteSpecialCommand',0x5B54),
        (0x2BE9,'canExecute',0x5B6D),(0x2BEA,'execute',0x5B6D),
        (0x2BEC,'Instance',0x5B60),(0x2BED,'ClipboardItemDisplayNameSelector',0x5B60),
        (0x2BEE,'InitialPasteTargetPredicate',0x5B67),(0x2BEF,'UniquenessTargetPredicate',0x5B67),
        (0x2BF0,'BrokenDevicePredicate',0x5B67),(0x2BF1,'LockedDevicePredicate',0x5B67),
        (0x2BF3,'handler',0x5B5D),(0x2BF4,'clipboardData',0x5B5D),(0x2BF5,'target',0x5B5D),
        (0x2BF7,'handler',0x5B63),(0x2BF8,'clipboardData',0x5B63),(0x2BF9,'target',0x5B63),(0x2BFA,'pasteOptions',0x5B63),
        (0x2BFC,'handler',0x5B65),(0x2BFD,'sourceItems',0x5B65),(0x2BFE,'target',0x5B65),(0x2BFF,'pasteOptions',0x5B65),
        (0x2C01,'firstTarget',0x5B67),
    ]
    for rid,name,caller in fields:
        token=0x04000000+rid
        b.bind_usage_sources(path,{token:0x06000000+caller})
        b.add('Fields',token,name,'Constructor assignment or exact captured/cached usage establishes the field role.')
        assert not b.pending,b.pending
        b.decisions[-1]['IL']={**proof,'SupportingTokens':[f'0x0600{caller:04X}']}
    for token,name,reason in [
        (0x02000A53,'PasteSelectionCommand','Delegates command eligibility/execution and returns Continue; ICommandHandler method names are retained.'),
        (0x02000A54,'PasteSelectionPredicates','Shared display-name and target/device validation predicates.'),
        (0x02000A55,'PasteMoveContext','Captures normal move target and clipboard items for the factory/notification callback.'),
        (0x02000A56,'ConfiguredPasteMoveContext','Captures special-paste move target, clipboard items and selected options.'),
        (0x02000A57,'PasteCopyContext','Captures source, target and options for copy construction and password retry.'),
        (0x02000A58,'PasteTargetValidationContext','Captures first eligible target for the reference-identity uniqueness predicate.')]:
        b.add('Types',token,name,reason)
        assert not b.pending,b.pending
    b.save(stem)
    remaining=[]
    for t,m in bodies.items():
        row=b.entries['Methods'][m['Token']]
        if row.get('NeedsReadableName') and ('Methods',m['Token']) not in b.selected:
            uses=[json.loads(r[0]) for r in b.db.execute('SELECT data FROM edges WHERE target=?',(b.module_id+':'+m['Token'],))]
            remaining.append({'Token':m['Token'],'Signature':m['Signature'],'IncomingEdges':uses,
                'Instructions':[i['OpCode'] for i in m['Instructions']],
                'Reason':'Generated static storage helper; no domain meaning established.'})
    with Path(str(stem)+'.remaining.json').open('x',encoding='utf-8') as f:
        json.dump({'PhysicalModule':b.module,'Methods':remaining,'AppliedToSource':False},f,indent=2)


if __name__=='__main__':
    root=Path(sys.argv[1]); stem=Path(sys.argv[2])
    stage(root,stem if stem.is_absolute() else root/stem)
