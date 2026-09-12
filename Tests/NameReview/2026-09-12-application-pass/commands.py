"""Reviewed ETS 6.3 command routing, panel context and clipboard behavior."""

def review(add, inspect):
    roles = {'ipanelContentViewModel_0':'panelContent', 'icontextMenuViewModel_0':'contextMenu',
             'ipanelListViewModel_0':'panelList', 'iworkplaceViewModel_0':'workplace',
             'ipanelViewModel_0':'panel', 'idetailViewTab_0':'detailTab', 'device_0':'device'}
    def method(token, name, reason, parameters=(), locals_=None):
        token += 0x06000000
        symbol, bindings = inspect(token)
        formal = {p['OriginalName'] for p in symbol['Parameters']} if parameters else set()
        # These callback roles were inspected in these bodies. This stages
        # declaration proposals, never a project-wide spelling replacement.
        local = {b['Name']:roles[b['Name']] for b in bindings if b['Name'] in roles and b['Name'] not in formal}
        local.update(locals_ or {})
        add('ETS',token,name,reason,parameters,local)

    method(0x30,'OnCommandWindowClosed','Window.Closed handler; detaches the closed window command bindings.')
    method(0x35,'AddShortcutCommandBinding','Adds a CommandBinding only when the routed command has input gestures, preserving the optional CanExecute handler.',('element','command','onExecuted','onCanExecute'))
    method(0x38,'OnCommandCanExecuteWithoutDialog','Sets CanExecute solely from IsNotBlockedByDialog.')
    method(0x39,'SetCanExecuteFromCommand','Requires ICommand, then combines CanExecute(null) with the dialog check.',('sender','args','command'))
    method(0x4A,'HasActiveWorkplace','Tests GetActiveWorkplaceViewModel for non-null.')
    method(0x4E,'GetActiveCommandPanel','Returns the resolver active panel.')
    method(0x4F,'GetActiveCommandPanelContent','Returns the resolver active panel content.')
    method(0x4B,'GetActiveProjectPanelList','Returns the active workplace ProjectsViewModel.PanelList, or null.',locals_={'activeWorkplaceViewModel':'activeWorkplace','projectsViewModel':'activeProjects'})
    method(0x45,'RunActivePanelAction','Invokes the callback only when an active panel exists.',('action',),{'panelViewModel':'activePanel'})
    method(0x4C,'RunActivePanelListAction','Invokes the callback only when an active project panel list exists.',('action',),{'panelListViewModel':'activePanelList'})
    method(0x4D,'RunActiveWorkplaceAction','Invokes the callback only when an active workplace exists.',('action',),{'activeWorkplaceViewModel':'activeWorkplace'})
    method(0x46,'RunActiveProjectScopeAction','Supplies the active project ID and its lifetime scope to the callback; retains the active-workplace precondition.',('action',),{'id':'projectId','scope':'projectScope'})
    method(0x47,'RunCommandInSelectedContextMenu','Parses the routed parameter as ContextMenuParent; uses that parent or the default context menu.',('panelContent','commandParameter','action'),{'contextMenuParent':'menuParent'})
    method(0x51,'SwitchActivePanelContent','Executes SwitchContentCommand only when the active panel descriptor differs.',('contentDescriptor',),{'panelViewModel':'activePanel'})
    method(0x3D,'FindCatalogPanelContent','Returns the first CatalogPanelViewModel among panel contents, or null.',('panelList',),{'panelViewModel':'catalogPanel'})
    method(0x3E,'CreateAndShowApplicationWindow','Creates a window through IMainWindowService and shows it.',locals_={'mainWindowViewModel':'newWindow'})
    method(0x3F,'OpenAnotherActiveProjectTab','Adds another tab for the selected project; excludes dashboard tabs.')
    method(0x40,'SelectPreviousApplicationTab','Selects the previous active-window tab.')
    method(0x41,'SelectNextApplicationTab','Selects the next active-window tab.')
    method(0x42,'CreateProjectFromDashboard','Executes the active window dashboard NewProjectCommand.')
    method(0x43,'CloseActiveProject','Closes the resolver project ID through the shutdown service when present; preserves the true option.')
    method(0x44,'HasUsableExtendedCopyLicense','Checks ExtendedCopy feature subordination chains against their owning licenses; exceptions return false. Called before extended paste.',locals_={'licensesForFeatureName':'extendedCopyLicenses','flag':'licenseCheckResult','enumerator':'licenseEnumerator','ar':'license'})
    method(0x5C,'ExecuteConfiguredPaste','Selects normal, special-with-normal-fallback or extended paste. Retains the extended-copy chain check and unlicensed dialog.',('contextMenu',))
    method(0x5B,'PasteIntoPanelContextMenu','Runs ExecuteConfiguredPaste within the supplied panel default context menu.',('panelContent',))
    method(0xA7,'LinkCurrentSelectionInProjectScope','Resolves ILinkWithCommand and executes it on the active panel selection when CanExecute succeeds.',('projectId','projectScope'),{'linkWithCommand':'linkSelectionCommand'})
    method(0x3C,'LinkCurrentSelection','Supplies the active project scope to the selection-linking helper.')
    method(0xA6,'AddToPanelOrLinkSelection','Executes AddCommand when available; otherwise links the current selection.',('panelContent',))
    method(0x9E,'ApplyDefaultProjectWorkspace','Resolves the scoped IWorkspaceManager and applies WorkspaceCollection.DefaultWorkspace.',('projectId','projectScope'))

    for leaf,outer,operation,local_id in [(0xD2,0xD0,'Delete',13),(0xF8,0xF6,'Cut',10),(0xFE,0xFC,'Copy',11),(0x102,0x100,'Paste',12)]:
        detail = {
            'Delete':'Combines shortcut permission, dialog state and availability of DeleteCommand or UnlinkCommand.',
            'Cut':'Combines shortcut permission with the shared dialog/CutCommand check.',
            'Copy':'Combines shortcut permission with the shared dialog/CopyCommand check.',
            'Paste':'Combines shortcut permission and the configured paste mode; extended mode uses IsExtendedCopyLicensed.'}[operation]
        method(leaf,'Evaluate'+operation+'ContextMenuAvailability',detail,('contextMenu',))
        method(outer,'Evaluate'+operation+'PanelAvailability','Captures the panel and enters its context menu before the '+operation.lower()+' availability callback.',('panelContent',),{'local_'+str(local_id):operation.lower()+'PanelQuery'})

    # Handlers were checked against both bindings and bodies. Route names do not
    # claim stronger effects than the actual implementation (e.g. Print/Import).
    handlers = [
        (0x3B,'InsertOrAdd','Runs the active-panel AddCommand/link-selection fallback.'),
        (0x52,'Undo','Calls ProjectsViewModel.OnUndoExecuted in the active workplace.'),
        (0x54,'Redo','Calls IWorkplaceViewModel.OnRedoExecuted.'),
        (0x56,'Cut','Executes CutCommand in the parameter-selected context menu.'),
        (0x58,'Copy','Executes CopyCommand in the parameter-selected context menu.'),
        (0x5A,'Paste','Runs the configured paste behavior in the active panel context menu.'),
        (0x5E,'DeleteOrUnlink','Honors a supplied DeleteOrUnlinkBehavior; otherwise prefers delete and falls back to unlink.'),
        (0x61,'Help','Calls IHelpProvider.OpenHelp with the sender.'),
        (0x62,'NewProject','Invokes dashboard project creation.'),
        (0x63,'CloseProject','Invokes active-project closure.'),
        (0x64,'EditParameter','Selects the first Parameter detail tab.'),
        (0x66,'OpenAddMenu','Sets active panel AddMenuIsOpen.'),
        (0x67,'Import','Imports catalog products through an existing/new catalog panel when a project panel list exists; otherwise calls ImportProject.'),
        (0x68,'DownloadAll','Executes DownloadCommand(All).'),
        (0x6A,'DownloadPartial','Executes DownloadCommand(Partial).'),
        (0x6C,'DownloadIndividualAddress','Executes DownloadCommand(PhysicalAddress).'),
        (0x6E,'DownloadApplication','Executes DownloadCommand(Application).'),
        (0x70,'OverwriteIndividualAddress','Executes DownloadCommand(PhysicalAddressOverwrite).'),
        (0x72,'ResetDevice','Executes ResetCommand.'),
        (0x74,'UnloadDevice','Executes UnloadCommand(All).'),
        (0x76,'DeviceInfo','Executes DeviceInfoCommand.'),
        (0x78,'ShowBuildingsPanel','Switches to BuildingsPanelDescriptor.'),
        (0x79,'ShowDevicesPanel','Switches to DevicesPanelDescriptor.'),
        (0x7A,'ShowGroupAddressesPanel','Switches to GroupAddressPanelDescriptor.'),
        (0x7B,'ShowProjectRootPanel','Switches to ProjectRootPanelDescriptor.'),
        (0x7C,'ShowReportsPanel','Switches to ReportsPanelDescriptor.'),
        (0x7D,'ShowTopologyPanel','Switches to TopologyPanelDescriptor.'),
        (0x7E,'Print','Switches to ReportsPanelDescriptor; does not directly print.'),
        (0x7F,'NextPane','Executes the panel list NextPanelCommand.'),
        (0x81,'PreviousPane','Executes the panel list PreviousPanelCommand.'),
        (0x83,'ClosePane','Executes current-panel CloseCommand when a panel exists.'),
        (0x85,'MaximizePane','Executes the current panel ContentSwitcherDropDown.OpenAsNewTabCommand.'),
        (0x87,'NewWindow','Creates and shows an application window.'),
        (0x88,'NewTab','Adds another active-project tab; excludes the dashboard.'),
        (0x89,'NextTab','Selects the next active-window tab.'),
        (0x8A,'PreviousTab','Selects the previous active-window tab.'),
        (0x8B,'NextMatch','Executes current-sidebar FindAndReplaceViewModel.FindNext.'),
        (0x8D,'ShowBusMonitor','Opens BusMonitorDescriptor.'),
        (0x8F,'ShowGroupMonitor','Opens GroupMonitorDescriptor.'),
        (0x91,'ShowSettings','Executes the built settings command with e.Parameter.'),
        (0x93,'NavigateForward','Navigates the active panel Forward.'),
        (0x94,'NavigateBackward','Navigates the active panel Backward.'),
        (0x95,'ShowPropertiesSidebar','Expands Properties.'),
        (0x97,'ShowOperationsSidebar','Expands PendingOperations.'),
        (0x99,'ShowUndoSidebar','Expands UndoHistory.'),
        (0x9B,'ShowWorkspaceSidebar','Expands Workspaces.'),
        (0x9D,'UseDefaultWorkspace','Applies the default workspace in the active project scope.'),
        (0xA0,'SplitPanelHorizontal','Executes OrientationHorizontal.'),
        (0xA2,'SplitPanelVertical','Executes OrientationVertical.'),
        (0xA4,'ToggleSidebar','Executes current-sidebar ToggleSidebar.')]
    local_overrides = {
        0x57:{'local_1':'cutQuery','local_2':'cutPanelQuery'},
        0x59:{'local_3':'copyQuery','local_4':'copyPanelQuery'},
        0x5D:{'local_5':'pasteQuery','local_6':'pastePanelQuery'},
        0x5E:{'local_7':'deleteOrUnlinkAction','parameter':'commandParameter','isinstValue':'boxedBehavior','deleteOrUnlinkBehavior':'requestedBehavior','deleteOrUnlinkBehavior2':'selectedBehavior'},
        0x5F:{'local_8':'deleteQuery','local_9':'deletePanelQuery'},
        0x67:{'panelListViewModel':'activePanelList','catalogPanelViewModel':'catalogContent','onlineCatalogPanelDescriptor':'catalogDescriptor'},
        0x84:{'applicationCommandHandler':'commandHandler','obj':'commandSender','e2':'queryArgs'},
        0x86:{'applicationCommandHandler':'commandHandler','obj':'commandSender','e2':'queryArgs'},
        0x8C:{'sidebarViewModel':'sidebar'}}
    for token,name,reason in handlers:
        method(token,'On'+name+'CommandExecuted',reason,locals_=local_overrides.get(token))
    queries = [
        (0x53,'Undo','Combines dialog state with ProjectsViewModel.OnUndoCanExecute.'),
        (0x55,'Redo','Combines dialog state with IWorkplaceViewModel.OnRedoCanExecute.'),
        (0x57,'Cut','Evaluates shortcut/dialog/CutCommand availability in the selected context menu.'),
        (0x59,'Copy','Evaluates shortcut/dialog/CopyCommand availability in the selected context menu.'),
        (0x5D,'Paste','Rejects open dialogs, then evaluates shortcut permission and configured paste mode.'),
        (0x5F,'DeleteOrUnlink','Checks shortcuts, dialog state and availability of delete or unlink.'),
        (0x60,'Insert','Requires panel shortcut permission and no open dialog.'),
        (0x65,'EditParameter','Requires no dialog and a Parameter detail tab.'),
        (0x69,'DownloadAll','Checks DownloadCommand(All) and dialog state.'),
        (0x6B,'DownloadPartial','Checks DownloadCommand(Partial) and dialog state.'),
        (0x6D,'DownloadIndividualAddress','Checks DownloadCommand(PhysicalAddress) and dialog state.'),
        (0x6F,'DownloadApplication','Checks DownloadCommand(Application) and dialog state.'),
        (0x71,'OverwriteIndividualAddress','Checks DownloadCommand(PhysicalAddressOverwrite) and dialog state.'),
        (0x73,'ResetDevice','Checks ResetCommand and dialog state.'),
        (0x75,'UnloadDevice','Checks UnloadCommand(All) and dialog state.'),
        (0x77,'DeviceInfo','Checks DeviceInfoCommand and dialog state.'),
        (0x80,'NextPane','Uses the shared command/dialog check for NextPanelCommand.'),
        (0x82,'PreviousPane','Uses the shared command/dialog check for PreviousPanelCommand.'),
        (0x84,'ClosePane','Checks current-panel CloseCommand; preserves the shared helper null-command validation.'),
        (0x86,'MaximizePane','Checks OpenAsNewTabCommand; preserves the null-command validation behavior.'),
        (0x8C,'NextMatch','Requires expanded FindAndReplace and FindNext.CanExecute; preserves the absent dialog check.'),
        (0x8E,'ShowBusMonitor','Requires no dialog and an active workplace.'),
        (0x90,'ShowGroupMonitor','Requires no dialog and an active workplace.'),
        (0x92,'ShowSettings','Checks the built settings command through the shared command/dialog helper.'),
        (0x96,'ShowPropertiesSidebar','Requires no dialog and no broken Device in the last selection.'),
        (0x98,'ShowOperationsSidebar','Requires no dialog and an active workplace.'),
        (0x9A,'ShowUndoSidebar','Requires no dialog and an active workplace.'),
        (0x9C,'ShowWorkspaceSidebar','Requires no dialog and an active workplace.'),
        (0x9F,'UseDefaultWorkspace','Requires no dialog and an active workplace.'),
        (0xA1,'SplitPanelHorizontal','Requires no dialog, a panel list and OrientationHorizontal.CanExecute.'),
        (0xA3,'SplitPanelVertical','Requires no dialog, a panel list and OrientationVertical.CanExecute.'),
        (0xA5,'ToggleSidebar','Requires no dialog and an active workplace.')]
    for token,name,reason in queries:
        method(token,'On'+name+'CanExecute',reason,locals_=local_overrides.get(token))
    method(0x3A,'SetApplicationShortcutBindings','Clears bindings and registers the reviewed commands when gestures exist. Shared Insert/Add routes and the empty CloseTab handler are retained.',('element',))

    for token,name,reason in [
        (0x24,'activeViewModelResolver','Constructor resolver for the active project/workplace/panel/content.'),
        (0x25,'userSettings','Constructor settings used for command initialization and PasteBehaviour.'),
        (0x26,'messageBoxService','Constructor service used by the unlicensed extended-paste dialog.'),
        (0x27,'licenseManager','Constructor license/app manager for extended-copy checks.'),
        (0x28,'mainWindowService','Constructor window service for tabs, windows and dashboard commands.'),
        (0x29,'dialogService','Constructor tabbed-dialog service supplying dialog-blocking state.'),
        (0x2A,'projectService','Constructor service for project import without an active project panel.'),
        (0x2B,'shutdownHandlingService','Constructor service for closing projects.'),
        (0x2C,'tabCreationService','Constructor service for adding project tabs.'),
        (0x2D,'helpProvider','Constructor help provider.'),
        (0x2E,'showSettingsCommand','CommandBuilder-built IShowSettingsCommandHandler command.')]:
        add('ETS',0x04000000+token,name,reason)
    for query_type,panel_type,handler_field,panel_field,parent_field,operation in [
        (0x12,0x13,0x58,0x59,0x5A,'Delete'), (0x25,0x26,0x83,0x84,0x85,'Cut'),
        (0x28,0x29,0x8A,0x8B,0x8C,'Copy'), (0x2A,0x2B,0x8E,0x8F,0x90,'Paste')]:
        add('ETS',0x02000000+query_type,operation+'CommandQueryContext','Captures the handler and routed '+operation.lower()+' query state.')
        add('ETS',0x02000000+panel_type,operation+'PanelQueryContext','Captures a panel and its parent '+operation.lower()+' query context.')
        add('ETS',0x04000000+handler_field,'commandHandler','Captured command handler for '+operation.lower()+' availability.')
        add('ETS',0x04000000+panel_field,'panelContent','Captured panel for '+operation.lower()+' shortcuts/context menu.')
        add('ETS',0x04000000+parent_field,'queryContext','Captured parent '+operation.lower()+' command query.')
