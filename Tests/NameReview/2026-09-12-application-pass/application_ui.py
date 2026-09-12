"""Behavior names for the application entry point and its window adapters."""

def review(add):
    for token, name, reason, parameters, locals_ in [
        (0x0600000C, 'AppendStartupLogMessage', 'Appends a timestamped message and newline to the ETS6 startup.log under local application data.', ('message',), None),
        (0x0600000D, 'EnsureLauncherParentAndFilterDebugArgument', 'Removes the explicit debug argument; otherwise requires an ETS6 parent, relaunches through ETS6.exe when present and exits the current process. Existing argument quoting and exit behavior are preserved.', ('arguments',), {'text':'launcherPath'}),
        (0x0600000E, 'ConfigureApplicationLogging', 'Configures Log4Net from the troubleshooting log level and refreshes the App logger.', ('userSettings',), None),
        (0x06000010, 'SelectUiCultureFromSettingsOrFallback', 'Constructs EtsLanguageService for the entry-assembly directory with an empty blacklist, then uses its setting/OS/fallback selection.', ('userSettings',), {'list':'cultureBlacklist'}),
        (0x0600000F, 'ApplyApplicationLanguageSettings', 'Sets default/current UI culture, WPF language metadata, resource/settings UI language and preferred product language.', ('userSettings','uiCulture'), None),
        (0x06000011, 'DisableTelerikUiAutomation', 'Sets Telerik AutomationManager.AutomationMode to Disabled.' , (), None),
        (0x06000013, 'TerminateSecondaryApplicationInstance', 'Called when the watcher reports another main instance; kills the current process then calls Shutdown(0), preserving that ordering.', (), None),
        (0x06000014, 'StartSingleInstanceWatcher', 'Creates SingleInstanceApplicationWatcher and passes the filtered launch arguments to Start.', ('arguments',), None),
        (0x0600001C, 'DisposeOwnedApplicationResources', 'Disposes and clears the crash indicator, single-instance watcher and bootstrapper.', (), None),
        (0x0600001D, 'DisposeOwnedApplicationResourcesAsync', 'Tries asynchronous disposal of each owned application resource and clears each reference after completion.', (), None),
        (0x06000016, 'DisposeApplicationCore', 'Uses the Disposer guard with the supplied disposing flag and synchronous owned-resource callback.', ('disposing',), None),
        (0x06000018, 'DisposeApplicationCoreAsync', 'Uses the AsyncDisposer guard with the asynchronous owned-resource callback.', (), None),
        (0x0600001B, 'AwaitApplicationDisposalAsync', 'Task-returning callback awaited by OnExit through PumpWhileWaiting; awaits public DisposeAsync without capturing context.', (), None)]:
        add('ETS', token, name, reason, parameters, locals_)
    for token, name, reason in [
        (0x04000006,'logger','Application startup, exit and emergency-shutdown logger.'),
        (0x04000007,'disposer','Synchronous disposal guard used by DisposeApplicationCore.'),
        (0x04000008,'asyncDisposer','Asynchronous disposal guard used by DisposeApplicationCoreAsync.'),
        (0x04000009,'crashIndicator','Created as EtsCrashIndicator and passed to the bootstrapper.'),
        (0x0400000A,'singleInstanceWatcher','Started with launch arguments, checked for main-instance status, stopped on exit and disposed.'),
        (0x0400000B,'bootstrapper','Created and set up in App constructor; receives startup culture/settings/arguments and owned services.')]:
        add('ETS', token, name, reason)
    add('ETS', 0x0600000A, None, 'Retain WPF OnStartup override; distinguish selected culture, arguments and each startup failure.', locals_={
        'array':'launchArguments','instance':'userSettings','cultureInfo':'uiCulture','exception_0':'operationException',
        'ex':'themeInitializationException','ex2':'typeLoadException','ex3':'startupException'}, status='retain-method-name')
    add('ETS', 0x0600000B, None, 'Retain WPF OnExit override and identify cleanup failures.', locals_={'ex':'disposalException'}, status='retain-method-name')

    # Title setters form an explicit chain; event handlers retain sender/e names.
    for token, name, reason, parameters in [
        (0x06000241,'FormatEtsWindowTitle','Prefixes the given title with ETS6 - .',('title',)),
        (0x06000240,'SetWindowTitleOrEmpty','Assigns Title with an empty-string fallback for null.',('title',)),
        (0x0600023F,'UpdateWindowTitleFromHeader','Passes the optional header title to SetWindowTitleOrEmpty.',('header',)),
        (0x0600023E,'UpdateWindowTitleFromTab','Passes the optional tab header to UpdateWindowTitleFromHeader.',('tab',)),
        (0x0600023D,'UpdateWindowTitleFromSelectedTab','Passes the optional main-window selected tab to UpdateWindowTitleFromTab.',('mainWindow',)),
        (0x06000235,'IsLegacyControlSupportEnabled','Reads Compatibility.EnableLegacyControlSupport; Show negates it for AllowTransparency.',()),
        (0x06000238,'OnWindowActivated','Forwards Activated to adapter subscribers.',()),
        (0x06000239,'OnWindowClosed','Forwards the Telerik closed event to adapter Closed subscribers.',()),
        (0x0600023A,'OnWindowPreviewClosed','Cancels closing while tabs remain, then forwards a copy of the cancellation state to adapter Closing subscribers. Subscriber changes are not copied back in this source.',()),
        (0x0600023C,'OnSelectedTabHeaderPropertyChanged','Updates the window title only for an ITitleTabHeaderViewModel Title property change.',()),
        (0x0600023B,'OnSelectedTabChanged','Detaches the old header handler, updates the title, then attaches the new header handler.',()),
        (0x06000236,'SubscribeToWindowEvents','Attaches the three underlying Telerik window event handlers.',()),
        (0x06000237,'UnsubscribeFromWindowEvents','Detaches the three underlying Telerik window event handlers.',()),
        (0x06000234,'DisposeAfterWindowClosed','Detaches itself from the adapter Closed event then calls base.Dispose.',())]:
        add('ETS',token,name,reason,parameters)
    for token, name, reason in [
        (0x04000163,'userSettings','Constructor-supplied settings used for the legacy-control transparency policy.'),
        (0x04000164,'title','Unprefixed adapter Title backing value; the native title receives FormatEtsWindowTitle.'),
        (0x04000165,'closingHandlers','Subscriber backing delegate for the adapter Closing event.'),
        (0x04000166,'closedHandlers','Subscriber backing delegate for the adapter Closed event.'),
        (0x04000167,'activatedHandlers','Subscriber backing delegate for the adapter Activated event.')]:
        add('ETS',token,name,reason)

    add('ETS',0x06000261,'ShowPreNotificationLicensingError','Displays the localized pre-notification licensing-problem error dialog.',locals_={'ets5MessageBoxVM':'licensingErrorDialog'})
    add('ETS',0x0600025E,'ShowLicensingErrorAndOpenSupportArticleAsync','Awaits the licensing error dialog callback via Task.Run, then opens the LicenseActivation support article.')
    add('ETS',0x0600025F,'OnPreNotificationWindowLoaded','Removes its one-shot Loaded handler and sets the ETS taskbar application ID for the actual window.',locals_={'window':'taskbarWindow'})
    for token, name, reason in [
        (0x0400016E,'logger','Logger for failed pre-notification workflow activation.'),
        (0x0400016F,'window','Constructor-supplied pre-notification window shown by StartAsync.'),
        (0x04000170,'windowViewModel','Constructor-supplied workflow view model started and disposed by StartAsync.'),
        (0x04000171,'webLinkService','Opens the licensing support article after an activation failure.'),
        (0x04000172,'supportLinks','Supplies the LicenseActivation article route.'),
        (0x04000173,'messageBoxService','Displays the localized licensing-problem dialog.')]:
        add('ETS',token,name,reason)
