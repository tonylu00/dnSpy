"""Stage extended-copy wizard behavior from physical IL and source evidence.

Usage: python extended_copy_scopes.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
No ETS files are rewritten. Runtime contracts and existing aliases are retained.
"""
from pathlib import Path
import json
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


# Explicit paired definitions, independently inspected in each physical version.
SELECTORS = [
    ('GetSourceDisplayName', 'sourceItem', 'get_DisplayName', None, 0x5592, 0x74AC),
    ('GetPageOptionsToSave', 'page', 'get_Option', None, 0x55E5, 0x750D),
    ('IsLinePageForValidation', 'page', 'get_Parent', 1, 0x55ED, 0x7521),
    ('IsSegmentPageForValidation', 'page', 'get_Parent', 2, 0x55ED, 0x7521),
    ('IsMiddleGroupPageForValidation', 'page', 'get_Parent', 6, 0x55ED, 0x7521),
    ('GetPageOptionsForOperation', 'page', 'get_Option', None, 0x55DF, 0x74FE),
    ('IsAssociationPage', 'page', 'get_Parent', 4, 0x55B8, 0x74D2),
    ('IsFunctionPage', 'page', 'get_Parent', 11, 0x55B8, 0x74D2),
    ('IsAreaControllerPage', 'page', 'get_Parent', 0, 0x55BC, 0x74D6),
    ('IsLineControllerPage', 'page', 'get_Parent', 1, 0x55BC, 0x74D6),
    ('IsMainGroupControllerPage', 'page', 'get_Parent', 5, 0x55BC, 0x74D6),
    ('IsDependentLinePage', 'page', 'get_Parent', 1, 0x55BE, 0x74D8),
    ('IsDependentSegmentPage', 'page', 'get_Parent', 2, 0x55BF, 0x74D9),
    ('IsDependentMiddleGroupPage', 'page', 'get_Parent', 6, 0x55C0, 0x74DA),
]
ROOTS = [
    (0x55AF, 0x74C9, 'RaiseRequestClose', (), {}, {}, 'Marks Closed and invokes RequestClose only when a subscriber exists.'),
    (0x55B0, 0x74CA, 'ExecutePreview', (), {}, {}, 'Opens the extended-copy HTML preview for the source project, then clears the dirty flag.'),
    (0x55B3, 0x74CD, 'TryConfirmLoseElementsFromOperation', (), {0:'previewXml',1:'lostElementKinds',2:'confirmationMessage'}, {3:'previewXml',1:'lostElementKinds',2:'confirmationMessage'}, 'Builds a warning for lost associations/devices/segments/lines/areas from the preview; returns false only for an explicit No response.'),
    (0x55B5, 0x74CF, 'TrySetOperationAsync', ('factory','isPreview','cancellationToken'), {}, {}, 'Recreates a missing or dirty operation, validates it asynchronously, handles security/password retry and compatibility alerts; preserves cancellation and preview-specific messages.'),
    (0x55B6, 0x74D0, 'GetWizard', ('factory',), {}, {}, 'Creates a Copy wizard and awaits the semaphore released by its operation-construction callback.'),
    (0x55B7, 0x74D1, 'SetupPagesPropertyChanged', (), {0:'pagesEnumerator'}, {2:'pagesEnumerator'}, 'Subscribes both page options and renaming options to the dirty-state handler.'),
    (0x55B8, 0x74D2, 'SetupCollapsablePages', (), {}, {}, 'Finds association/function controller pages, initializes dependent visibility and subscribes option-change handlers.'),
    (0x55B9, 0x74D3, 'AssociationsOnPropertyChanged', ('sender','e'), {}, {}, 'Updates group-address/range page visibility from the changed association options.'),
    (0x55BA, 0x74D4, 'FunctionsOnPropertyChanged', ('sender','e'), {}, {}, 'Updates function-group-address visibility from the changed function options.'),
    (0x55BB, 0x74D5, 'SetDependentVisibility', ('master','dependentPages'), {0:'visibilityContext',1:'dependentPagesEnumerator',2:'visiblePagePredicate'}, {3:'visibilityContext',1:'dependentPagesEnumerator',5:'visiblePagePredicate'}, 'Shows matching collapsible pages for Create and collapses them for every other general option.'),
    (0x55BC, 0x74D6, 'SetupLockingOptionBehavior', (), {}, {}, 'Links area to line and line to segment; main to middle group only for three-level addressing, then subscribes current-page changes.'),
    (0x55BD, 0x74D7, 'SetupDependency', ('master','dependentParent','handler'), {0:'dependencyContext',1:'dependentPage'}, {0:'dependencyContext',1:'dependentPage'}, 'For a controller with multiple options, requires the dependent page with First, initializes locking, subscribes changes and propagates Create.'),
    (0x55BE, 0x74D8, 'AreaOnPropertyChanged', ('sender','e'), {}, {}, 'Updates line-page locking from area options.'),
    (0x55BF, 0x74D9, 'LineOnPropertyChanged', ('sender','e'), {}, {}, 'Updates segment-page locking from line options.'),
    (0x55C0, 0x74DA, 'MainGroupOnPropertyChanged', ('sender','e'), {}, {}, 'Updates middle-group-page locking from main-group options.'),
    (0x55C1, 0x74DB, 'SetDependentAbility', ('controller','dependent'), {0:'generalOption'}, {0:'generalOption'}, 'Enables general options for Keep; disables them for Lose/Create without changing other values.'),
    (0x55C2, 0x74DC, 'PagesViewOnCurrentChanged', ('sender','e'), {}, {}, 'Propagates the controller option to the newly selected dependent page.'),
    (0x55C3, 0x74DD, 'SetDependentOption', ('dependent',), {0:'parentCategory'}, {1:'parentCategory'}, 'Selects area/line/main-group controllers for line/segment/middle-group pages respectively.'),
    (0x55C4, 0x74DE, 'SetDependentOption', ('controller','dependent'), {}, {}, 'If both pages exist, propagates only a controller Create option; the 6.4 object parameters retain their runtime casts.'),
    (0x55C5, 0x74DF, 'UnsubscribeEvents', (), {0:'pagesEnumerator'}, {0:'pagesEnumerator'}, 'Detaches controller, selection, option and renaming handlers; clears pages, closes/disposes a live wizard and clears the operation.'),
    (0x55C6, 0x74E0, 'UnsubscribeDependency', ('master','handler'), {}, {}, 'Removes the specified option-change handler only when the page exists.'),
    (0x55C7, 0x74E1, 'PageOnPropertyChanged', ('sender','e'), {}, {}, 'Marks the operation dirty after an option or renaming setting changes.'),
    (0x55C8, 0x74E2, 'RejectOperation', (), {}, {}, 'Sets the dirty flag; does not dispose or clear the operation immediately.'),
]


def stage(root, version, stem):
    old = version == '63'
    prefix = {'Methods':'clipboard63-wave201-methods.json','Types':'reviewed63-viewmodel01-types.json','Fields':'viewmodel63-fields.json'} if old else 'operations64-wave32'
    b = BehaviorReview(root, version, 209 if old else 37, 'm0082' if old else 'm0146', prefix,
        root / ('dispatch63-wave209.cumulative.json' if old else 'dispatch64-wave37.cumulative.json'))
    path = root / ('extended63-wave210-body-inspection.json' if old else 'extended64-wave38-body-inspection.json')
    report = b.read(path.name)
    assert all(report[k] == b.module[k] for k in ('Input','Mvid','Sha256'))
    bodies = {int(m['Token'],16):m for m in report['Methods']}
    proof = {'Path':str(path),'Sha256':sha(path)}
    b.bind_inspected_accessor_sources(path,[t for t,m in bodies.items() if m['AccessorOwners']])
    b.bind_inspected_state_machine_sources(path,[t for t,m in bodies.items() if m['StateMachineOwners']])

    def method(rid, name, reason, parameters=(), local=None):
        token = 0x06000000 + rid
        row, body = b.entries['Methods'][f'0x{token:08X}'], bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in local or {}:
            typ = next(x['ExpectedType'] for x in row['LocalNames'] if x['Index']==slot)
            assert next(x['Type'] for x in body['Locals'] if x['Slot']==slot)==typ and local_used(body,slot)
        b.add('Methods',token,name,reason,parameters,local)
        assert not b.pending,b.pending
        b.decisions[-1]['IL']={**proof,'Token':body['Token']}

    def bind(token, caller):
        if f'0x{token:08X}' not in b.usage_sources:
            b.bind_usage_sources(path,{token:0x06000000+caller})

    def field(rid,name,caller,reason):
        token=0x04000000+rid
        bind(token,caller)
        b.add('Fields',token,name,reason)
        assert not b.pending,b.pending
        b.decisions[-1]['IL']={**proof,'SupportingTokens':[f'0x0600{caller:04X}']}

    wizard = 0x55DF if old else 0x74FE
    bind(0x06000000+wizard,0x55EB if old else 0x751C)
    for index,(name,param,accessor,category,caller63,caller64) in enumerate(SELECTORS):
        rid=(0x55D0 if old else 0x74ED)+index
        caller=caller63 if old else caller64
        bind(0x06000000+rid,caller)
        body=bodies[0x06000000+rid]
        assert any(i['OpCode']=='callvirt' and f'::{accessor}(' in i.get('Operand',{}).get('Text','') for i in body['Instructions'])
        if category is not None:
            constants=[int(i['OpCode'].split('.')[-1]) if i['OpCode'].startswith('ldc.i4.') and i['OpCode']!='ldc.i4.s' else int(i['Operand']) for i in body['Instructions'] if i['OpCode'].startswith('ldc.i4')]
            assert constants==[category],(rid,constants)
        method(rid,name,'Reads the named page/source property'+(f' and compares OptionParents value {category}' if category is not None else '')+' at the verified caller.',(param,))
        field((0x369B if old else 0x36FB)+index,name+'Callback',caller,'Cached delegate for '+name+' at the exact inspected call site.')
    field(0x369A if old else 0x36FA,'Instance',0x5592 if old else 0x74AC,'Shared stateless selector receiver used by the constructor display-name projection.')
    method(wizard,'CreateExtendedCopyOperationAndSignalReady','Creates and stores one factory operation, returns it in a one-element array, and releases one semaphore permit after creation; null is not filtered.',('reportProgress',),{0:'createdOperation'})
    for index,(name,reason) in enumerate([
        ('CanCancelExtendedCopy','Cancel is enabled exactly when no operation is running.'),
        ('CanConfirmExtendedCopy','OK is enabled exactly when no operation is running.'),
        ('CanPreviewExtendedCopy','Preview is enabled exactly when no operation is running.'),
        ('ValidateCurrentOperation','Calls Validate on the current operation without a null guard.')]):
        rid=(0x55CA if old else 0x74E4)+index
        caller=(0x5592 if old else 0x74AC) if index<3 else (0x55ED if old else 0x7521)
        bind(0x06000000+rid,caller)
        method(rid,name,reason)
    for a,c,name,caller63,caller64 in [(0x55E1,0x7503,'IsDependentPageToShow',0x55BB,0x74D5),(0x55E2,0x7504,'IsDependentPageToCollapse',0x55BB,0x74D5),(0x55E4,0x7509,'MatchesDependentPageCategory',0x55BD,0x74D7)]:
        rid=a if old else c
        bind(0x06000000+rid,caller63 if old else caller64)
        method(rid,name,'Tests the captured dependent category/list against the page Parent; the caller determines whether to show, collapse or initialize locking.',('page',))
    for a,c,name,parameters,locals63,locals64,reason in ROOTS:
        method(a if old else c,name,reason,parameters,locals63 if old else locals64)
    # The surviving 6.3 getter still owns a property; 6.4 has an orphan special-name method.
    method(0x55AE if old else 0x74C8,'get_PreviewSequencer' if old else 'GetPreviewSequencer','Returns the cached preview sequencer, creating it once when null.',(),{0:'previewSequencer'})
    if not old:
        method(0x74C7,'GetOperationFactory','Returns the constructor-supplied operation factory.')
        method(0x74B2,'set_Closed','Metadata-owned setter for Closed.',('value',))
        method(0x74B4,'set_Result','Metadata-owned setter for Result.',('value',))

    for a,c,name,caller63,caller64 in [
        (0x36AA,0x370A,'viewModel',0x55EB,0x751C),
        (0x36AB,0x370B,'factory',0x55EB,0x751C),
        (0x36AC,0x370C,'operationReady',0x55EB,0x751C),
        (0x36AE,0x370E,'dependentPages',0x55BB,0x74D5),
        (0x36AF,0x370F,'showPagePredicate',0x55BB,0x74D5),
        (0x36B0,0x3710,'collapsePagePredicate',0x55BB,0x74D5),
        (0x36B2,0x3712,'dependentParent',0x55BD,0x74D7),
        (0x3686,0x36E6,'requestCloseHandlers',0x55AF,0x74C9)]:
        field(a if old else c,name,caller63 if old else caller64,'Captured value, predicate storage or event handlers established by the owning inspected call chain.')
    if not old:
        for rid,name,caller in [
            (0x36D6,'associationDependentPages',0x74D2),(0x36D7,'functionDependentPages',0x74D2),
            (0x36DF,'areaPage',0x74D6),(0x36E0,'associationPage',0x74D2),(0x36E1,'functionPage',0x74D2),
            (0x36E2,'mainGroupPage',0x74D6),(0x36E3,'linePage',0x74D6),
            (0x36E4,'operation',0x74FE),(0x36E5,'isDirty',0x74E2),(0x36E7,'sourceItems',0x74AF),
            (0x36E9,'closed',0x74B1),(0x36EB,'cancelCommand',0x74B5),(0x36EC,'okCommand',0x74B6),
            (0x36ED,'previewCommand',0x74B7),(0x36EE,'context',0x74B8),(0x36EF,'isRunningOperation',0x74BB),
            (0x36F0,'runningOperationText',0x74BD),(0x36F1,'numberOfCopies',0x74BE),
            (0x36F2,'pages',0x74C0),(0x36F3,'pagesView',0x74C2),(0x36F4,'wizard',0x74C4),
            (0x36F7,'previewSequencer',0x74C8),(0x36F8,'previewLock',0x7517)]:
            field(rid,name,caller,'Role established by the inspected getter, option-controller assignment, operation invalidation or preview lock usage.')
        for token,name,reason in [
            (0x02000CFA,'ExtendedCopyPageSelectors','Shared stateless display-name, option and category predicates.'),
            (0x02000CFB,'ExtendedCopyWizardContext','Captures view model, factory and readiness semaphore for wizard operation construction.'),
            (0x02000CFC,'DependentPageVisibilityContext','Captures dependent categories and caches the show/collapse predicates.'),
            (0x02000CFD,'DependentPageCategoryContext','Captures the parent category used to locate the dependent lockable page.')]:
            b.add('Types',token,name,reason)
            assert not b.pending,b.pending

    # Keep the whole-class inventory visible, including generated non-domain storage.
    unresolved=[]
    prefix='Knx.Ets.ViewModel.Application.Workspace.ExtendedCopy.ExtendedCopyViewModel'
    for key,row in b.entries['Methods'].items():
        if not row['Type'].startswith(prefix) or ('Methods',key) in b.selected: continue
        body=bodies[int(key,16)]
        if row['OriginalName'] in ('MoveNext','SetStateMachine'):
            unresolved.append({'Token':key,'Reason':'Runtime state-machine contract retained; body-local mapping still needs dedicated tooling review.'})
        elif row.get('NeedsReadableName') and not b.aliases.get((b.relative,key),{}).get('NewName'):
            unresolved.append({'Token':key,'Reason':'Generated helper without established application meaning; no guessed domain alias.','Instructions':[i['OpCode'] for i in body['Instructions']]})
    enum_path=b.source_root/('Knx.Ets.ViewModel' if old else 'Knx.Ets.ViewModel.2')/'Enumerations/ExtendedCopy/OptionParents.cs'
    for decision in b.decisions:
        decision['OptionParentsDeclaration']={'Path':str(enum_path),'Sha256':sha(enum_path)}
    b.save(stem)
    with Path(str(stem)+'.remaining.json').open('x',encoding='utf-8') as f:
        json.dump({'PhysicalModule':b.module,'Methods':unresolved,'AppliedToSource':False},f,indent=2)


if __name__=='__main__':
    root=Path(sys.argv[1])
    for version,stem in zip(('63','64'),sys.argv[2:4]):
        stage(root,version,Path(stem) if Path(stem).is_absolute() else root/stem)
