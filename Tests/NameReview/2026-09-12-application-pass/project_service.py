"""Behavior review of the visible ProjectService helper chains in ETS 6.3.

Public contracts already have useful names. Compiler-generated identifiers in
the metadata do not guarantee that the emitted source remains readable.
"""

def review(add):
    project = 'Knx.Ets.ViewModel'
    def record(token, name, reason, parameters=(), locals_=None, status='reviewed'):
        add(project, token, name, reason, parameters, locals_, status)

    # Stateless selectors: framework operations identify the returned values.
    for token, name, reason in [
        (0x060012DB, 'GetInstalledDcaAppId', 'Returns installedDca.AppId; used as the DCA export dictionary key.'),
        (0x060012DC, 'GetInstalledDcaApplicationProgramIds', 'Returns installedDca.DcaApplicationProgramIds; values in the DCA export dictionary.'),
        (0x060012DE, 'GetProjectStore', 'Returns IProject.Store before selecting versioned stores for local project metrics.'),
        (0x060012DF, 'GetStoreSchemaVersion', 'Returns IStoreVersionInfo.SchemaVersion for the local project metrics grouping.'),
        (0x060012E0, 'SelectSchemaVersionGroupKey', 'Identity selector used to group project stores by schema version.'),
        (0x060012E1, 'CountProjectsForSchemaVersion', 'Returns a key/value pair containing the schema group key and its element count.')]:
        record(token, name, reason)
    record(0x060012DD, 'IsProjectCurrentlyOpen', 'Predicate returns Project.IsOpen in GetOpenProjects.', ('project',))

    # Read the innermost callbacks before their operation/dialog factories.
    record(0x060012E7, 'RejectProjectDeviceActivityCalculation', 'Forwards the captured project and device count to RejectActivityCalculationOfDevices, which shows an informational dialog and returns false.', ('deviceCount',))
    record(0x060012EB, 'ReportProjectOpenProgress', 'Forwards the same progress event to the dialog callback and ProjectService.ProgressCallback.')
    record(0x060012E8, 'PauseTaskbarOnProjectOpenFailure', 'Sets taskbar progress to paused when the validation result did not succeed.')
    record(0x060012EA, 'OpenProjectAndSubscribeToChanges', 'Waits for pending app integrity checks with progress, sets tracing mode, calls project.Open with progress and activity callbacks, and subscribes PropertyChanged/OpenChanged.', locals_={'e':'integrityCheckProgress', 'project':'concreteProject'})
    record(0x060012E6, 'CreateProjectOpenOperations', 'Captures the dialog progress callback and professional tracing mode, and wraps OpenProjectAndSubscribeToChanges in one DummyOperation.', ('reportDialogProgress',), {'local_8':'openOperation', 'e':'integrityCheckProgress', 'project':'concreteProject'})
    record(0x060012E5, 'AuthenticateAndOpenProjectWithProgress', 'Blocking OpenProject body: validates access keys or prompts for a password, applies user settings, checks store integrity, updates recent-project state when requested, and shows the open operation dialog. Existing permission checks and return semantics are preserved.', locals_={
        'result3':'storedAccessKeyResult', 'result2':'passwordDialogResult', 'text':'installerGuid',
        'flag':'hasKnxSupportLicense', 'enumerator':'supportLicenseEnumerator', 'ar':'supportLicense',
        'local_7':'openOperation', 'e':'integrityCheckProgress', 'project':'concreteProject', 'action':'reportDialogProgress'})

    record(0x060012F6, 'ReportProjectStoreUpdateProgress', 'Reports the localized StoreUpdateUpdatingProjectData text; the numeric progress event is unused.')
    record(0x060012F5, 'ValidateAndExecuteProjectStoreUpdate', 'Creates UpdateProjectStoreOperation, executes only when Validate succeeds, then calls MarkSchemaUpdateRequired.', locals_={'updateProjectStoreOperation':'updateOperation'})
    record(0x060012F3, 'RunProjectStoreUpdateAsync', 'Captures the text progress reporter and runs ValidateAndExecuteProjectStoreUpdate with Task.Run.')

    record(0x060012FD, 'CreateProjectAndCaptureResult', 'Calls InternalCreateNewProject with the captured operation and stores the resulting Project.')
    record(0x060012FC, 'CreateProjectCreationOperations', 'Returns one DummyOperation using the create-operation description and CreateProjectAndCaptureResult callback; supplied progress callback is unused.')
    record(0x060012FE, 'ApplyPasswordToCreatedProject', 'If a password and created project exist, opens a closed project, validates and executes ChangeProjectPasswordOperation, and closes it only if it was originally closed. The supplied validation result is unused and existing early-return behavior is preserved.', locals_={'isOpen':'wasProjectOpen', 'changeProjectPasswordOperation':'passwordChangeOperation'})
    record(0x060012FA, 'CreateProjectWithProgressAndPassword', 'Builds CreateNewProjectOperation with default-name fallback and requested topology/building/type settings, shows its progress dialog, applies the optional password callback, notifies project-list change, and returns the captured project.', locals_={
        'local_9':'creationOperation', 'local_10':'operationReceiver', 'text':'projectName',
        'flag':'createDefaultTopology', 'flag2':'createBuilding', 'isOpen':'wasProjectOpen',
        'changeProjectPasswordOperation':'passwordChangeOperation'})

    for token, name, reason in [
        (0x020002A9, 'ProjectServiceDelegateCache', 'Stateless DCA/project/schema selectors and their cached delegates.'),
        (0x020002AB, 'ProjectOpenContext', 'Captures the service, project, access keys, password dialog type and recent-project flag for the blocking open body.'),
        (0x020002AC, 'ProjectOpenOperationContext', 'Captures the parent open context, dialog progress callback and tracing mode for the actual open operation.'),
        (0x020002B0, 'ProjectStoreUpdateContext', 'Captures the project for the asynchronous store update.'),
        (0x020002B1, 'ProjectStoreUpdateProgressContext', 'Captures the store-update context and text progress reporter for the background update operation.'),
        (0x020002B3, 'ProjectCreationContext', 'Captures the service and requested name/password/topology/building/type settings.'),
        (0x020002B4, 'ProjectCreationOperationContext', 'Captures the creation settings context, concrete create operation, created project and execution delegate.')]:
        record(token, name, reason)

    for token, name, reason in [
        (0x04000BD1, 'isBlockingOperationRunning', 'Backing storage for the existing IsBlockingOperationRunning property.'),
        (0x04000BD3, 'sharedCallbacks', 'Singleton ProjectServiceDelegateCache instance.'),
        (0x04000BD4, 'getInstalledDcaAppId', 'Cached GetInstalledDcaAppId delegate.'),
        (0x04000BD5, 'getInstalledDcaApplicationProgramIds', 'Cached GetInstalledDcaApplicationProgramIds delegate.'),
        (0x04000BD6, 'isProjectCurrentlyOpen', 'Cached IsProjectCurrentlyOpen predicate.'),
        (0x04000BD7, 'getProjectStore', 'Cached GetProjectStore selector.'),
        (0x04000BD8, 'getStoreSchemaVersion', 'Cached GetStoreSchemaVersion selector.'),
        (0x04000BD9, 'selectSchemaVersionGroupKey', 'Cached schema-version group key selector.'),
        (0x04000BDA, 'countProjectsForSchemaVersion', 'Cached CountProjectsForSchemaVersion selector.'),
        (0x04000BDF, 'projectService', 'Captured owner of the public OpenProject invocation.'),
        (0x04000BE3, 'rejectDeviceActivityCalculation', 'Cached RejectProjectDeviceActivityCalculation callback passed to project.Open.'),
        (0x04000BE4, 'createProjectOpenOperations', 'Cached operation factory passed to the open progress dialog.'),
        (0x04000BE5, 'pauseTaskbarOnOpenFailure', 'Cached validation-result callback for the open progress dialog.'),
        (0x04000BE7, 'reportDialogProgress', 'Progress delegate supplied by the dialog; forwarded alongside the taskbar callback.'),
        (0x04000BE9, 'openContext', 'Parent ProjectOpenContext captured by its operation context.'),
        (0x04000BEA, 'reportProjectOpenProgress', 'Cached ReportProjectOpenProgress callback passed to project.Open.'),
        (0x04000BFB, 'updateContext', 'Parent ProjectStoreUpdateContext captured by its progress context.'),
        (0x04000BFC, 'reportProjectStoreUpdateProgress', 'Cached localized update-text callback passed to UpdateProjectStoreOperation.'),
        (0x04000C01, 'projectService', 'Captured owner of the public CreateNewProject invocation.'),
        (0x04000C0A, 'creationContext', 'Parent ProjectCreationContext captured by its operation context.'),
        (0x04000C0B, 'createProjectAndCaptureResult', 'Cached callback invoking InternalCreateNewProject and assigning the returned project.')]:
        record(token, name, reason)

    # Retain established contracts; binding-specific local decisions also cover
    # lambdas inlined by the decompiler into the public methods.
    for token, reason, names in [
        (0x060012AC, 'Retain OpenProject; local roles match its reviewed authentication and progress helper chain.', {
            'local_1':'openContext', 'local_2':'openOperation', 'flag':'openSucceeded',
            'flag2':'hasKnxSupportLicense', 'result3':'storedAccessKeyResult', 'result2':'passwordDialogResult',
            'text':'installerGuid', 'enumerator':'supportLicenseEnumerator', 'ar':'supportLicense',
            'e':'integrityCheckProgress', 'project2':'concreteProject', 'action':'reportDialogProgress'}),
        (0x060012AD, 'Retain OpenProjectSilently; identify the selected key and the two distinct authentication results.', {
            'aq':'projectAccessKey', 'result':'storedAccessKeyResult', 'result2':'passwordDialogResult'}),
        (0x060012B5, 'Retain ImportProject; name collection tracking, wizard completion and the version-assignment failure.', {
            'notifyCollectionChangedGrabber':'importedProjectTracker', 'valueOrDefault':'importResult', 'ex':'versionAssignmentException'}),
        (0x060012B6, 'Retain AddDcaAsUserFile; dictionary maps installed app IDs to their DCA application-program IDs.', {
            'enumerable':'installedDcaAddIns', 'dictionary':'applicationProgramIdsByDcaAppId'}),
        (0x060012B7, 'Retain UpdateProjectStoreIfNecessaryWithProgressAsync; true means an update was attempted, preserving the existing validation behavior.', {
            'local_3':'updateContext', 'storeVersionInfo':'storeVersion', 'flag':'updateAttempted'}),
        (0x060012BD, 'Retain CreateNewProject; name the captured request and operation contexts.', {
            'local_4':'creationContext', 'local_5':'creationOperation', 'local_6':'operationReceiver',
            'text':'projectName', 'flag':'createDefaultTopologyValue', 'flag2':'createBuildingValue',
            'isOpen':'wasProjectOpen', 'changeProjectPasswordOperation':'passwordChangeOperation'}),
        (0x060012CD, 'Retain InternalCreateNewProject; name the validation-failure message builder.', {'stringBuilder':'validationFailureMessage'}),
        (0x060012D4, 'Retain RecordLocalProjectsMetrics; distinguish grouped counts from the serialized metric metadata.', {
            'func':'getProjectStore', 'list':'projectCountsBySchemaVersion', 'list2':'schemaCountMetadata', 'keyValuePair':'schemaProjectCount'})]:
        record(token, None, reason, locals_=names, status='retain-method-name')

    # The short string fields have special storage restoration constraints.
    # No behavioral name has been established; keep them explicit, unresolved.
    for token in [0x04000BD2, 0x04000BDB, 0x04000BE6, 0x04000BEB, 0x04000BF9, 0x04000BFD, 0x04000C07, 0x04000C0C]:
        record(token, None, 'Short string field with nonstandard storage metadata; no supported behavioral role established in this chain.', status='unresolved-storage-role')
