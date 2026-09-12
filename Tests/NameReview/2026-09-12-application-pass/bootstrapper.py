"""Behavior review of ETS 6.3 startup, exception handling and shutdown.

Called by stage.py after exact input/source validation. Small callees precede
their orchestration methods. Names describe observed behavior, not vendor names.
"""

def review(add):
    def method(token, name, reason, parameters=(), locals_=None):
        add('ETS', 0x06000000 + token, name, reason, parameters, locals_)

    # Resource strings, library APIs and event registrations establish leaf roles.
    for token,name,message in [
        (0x16F,'LogUsageNormalizationDuration','Checking usages and normalize if required'),
        (0x170,'LogAddInInitializationDuration','Initializing apps'),
        (0x172,'LogDashboardCacheInitializationDuration','Initialize caches'),
        (0x174,'LogOnlineCatalogUpdateDuration','Updating online catalog'),
        (0x176,'LogCoreAssemblyValidationDuration','Verifying application integrity'),
        (0x17B,'LogMetricsWriteDuration','Writing metrics'),
        (0x17D,'LogErrorMetricsWriteDuration','Writing error metrics')]:
        method(token,name,'Logs elapsed milliseconds for '+message+'.',('elapsed',))
    for token,name,reason in [
        (0x18C,'LogContainerBuildDuration','Logs Building IOC container elapsed time.'),
        (0x18D,'LogStartupInformationDuration','Logs Logging startup information elapsed time.'),
        (0x18F,'LogApplicationViewModelResolutionDuration','Logs the IApplicationViewModel type name and resolution duration.'),
        (0x191,'LogProjectArchiveLocationCheckDuration','Logs Checking archive path elapsed time.'),
        (0x192,'LogParallelStartupWaitDuration','Logs Waiting for parallel tasks to complete elapsed time.'),
        (0x194,'LogJumpListSetupDuration','Logs IJumpListManager setup elapsed time.')]: method(token,name,reason)
    method(0x161,'GetDefaultErrorDialogTitle','Returns the localized MessageBoxTitle_Error resource.')
    method(0x160,'ShowNativeMessageDialog','Uses WindowsMessageBoxWrapper.Show with the provided title or the localized default error title.',('message','title','buttons','icon'))
    method(0x15F,'ShowApplicationMessageDialog','Resolves IMessageBoxService when a container exists; otherwise falls back to the native message dialog.',('messageBox',),{'container':'availableContainer','messageBoxService':'dialogService'})
    method(0x15E,'ShowExceptionMessage','Without context, builds an exception message view model; otherwise combines context and exception.Message in a native dialog.',('exception','contextMessage'),{'text':'combinedMessage'})
    method(0x179,'ExecuteFatalTransactionEmergencyShutdown','Calls IShutdownHandlingService.ExecuteEmergencyShutdown with the existing exit code 19.')
    method(0x159,'HandleFatalTransactionException','Shows file-access-denied project details and invokes the fatal transaction emergency shutdown on the dispatcher.',('exception',),{'ets5MessageBoxVM':'failureDialog'})
    method(0x158,'TryHandleApplicationException','Dispatches handling to the UI thread; classifies ignored, fatal and recoverable exceptions, logs telemetry, shows dialogs and returns the handled flag. Preserves all exit codes and the pre-window fatal path.',('exception','contextMessage','dispatchAsynchronously'),{'ex':'fatalTransactionException','ets5MessageBoxVM':'timeoutDialog','loggingContext':'fatalLoggingContext','logEntryBuilder':'fatalLogEntry','container':'availableContainer','loggingContext2':'handledLoggingContext','logEntryBuilder2':'handledLogEntry','logEntryBuilder3':'completedHandledLogEntry'})
    method(0x177,'HandlePostedDispatcherException','Callback supplied to Dispatcher.BeginInvoke by TryHandleApplicationException; forwards with no context message.',('exception','dispatchAsynchronously'))
    method(0x178,'HandleInvokedDispatcherException','Callback supplied to Dispatcher.Invoke by TryHandleApplicationException; forwards with no context message.',('exception','dispatchAsynchronously'))
    method(0x155,'OnDispatcherUnhandledException','Sets DispatcherUnhandledExceptionEventArgs.Handled from the shared exception handler and initiates abnormal shutdown if unhandled.')
    method(0x156,'OnUnobservedTaskException','Uses asynchronous UI dispatch for the task exception, marks handled exceptions observed, and otherwise initiates abnormal shutdown.')
    method(0x154,'SubscribeToUnhandledExceptions','Registers the dispatcher and TaskScheduler exception event handlers.')
    method(0x157,'CloseApplicationAfterStartupFailure','Best-effort CloseApplication through the shutdown service, then InitiateAbnormalApplicationShutdown with existing code 40001.')
    method(0x15D,'EnableBreakOnWpfBindingErrors','Creates a WpfBindingErrorListener whose callback calls Debugger.Break.')
    method(0x175,'ValidateCoreAssemblyStrongNames','Validates the KNX and CloudKit assemblies using their existing strong-name validators; logs and rethrows a localized integrity error.',locals_={'ex':'integrityException'})
    method(0x142,'VerifyApplicationIntegrityWithTiming','Times ValidateCoreAssemblyStrongNames using the corresponding integrity-duration logger.')
    method(0x147,'CorrectSystemWorkingDirectory','Changes the working directory to the application base directory only when it currently equals the System special folder.')
    method(0x14E,'ApplyKnxEnvironmentSettings','Sets Professional KNX environment and the user-selected compatibility-mode flag.')
    method(0x14F,'InstallTelerikLocalizationManager','Assigns CustomLocalizationManager to Telerik LocalizationManager.Manager.')
    method(0x14C,'ConfigureTaskbarApplicationId','Assigns EtsApplicationIds.ApplicationId to TaskbarManager on supported platforms.')
    method(0x18A,'InitializeEnvironmentAndValidateAssemblies','Runs working-directory correction, KNX settings, localization, taskbar setup and timed assembly validation.')
    method(0x140,'ApplyLicensedProjectLoggingConfiguration','Sets Project.EnableExtendedLogging from ExtendedLoggingAvailable and retains the conditional Versioning.AddVersion(3.9) marker.',('services',))
    method(0x14D,'RecordDongleCollectionVersionMarker','Preserves the existing Sum(LicenseCollectionCount)>0 && Count(Dongles)==0 condition and Versioning.AddVersion(4.1). This review does not simplify or repair that unusual condition.',('services',),{'licenseAndAppManager':'licenseManager'})
    method(0x148,'ShowStartupSplashScreen','Creates StartupScreenViewModel and shows a StartupScreen with that DataContext.')
    method(0x162,'CloseAndDisposeSplashScreen','Closes and disposes the startup screen view model if present, then clears its reference.')
    method(0x149,'CloseStartupSplashScreen','Wrapper used by the pre-notification and first-window paths to close and dispose the splash screen.')
    method(0x14A,'SetStartupProgressText','Passes the supplied progress message to the startup-screen view model.',('message',))
    method(0x14B,'UpdateSplashScreenVersionsAsync','Calls the startup-screen view model UpdateVersionsAsync.')
    method(0x15B,'OnFirstWindowShown','Unsubscribes itself, changes ShutdownMode to OnLastWindowClose and closes the splash screen.')
    method(0x15A,'OnAnotherInstanceConnected','For an active initialized bootstrapper, invokes the main window view model BringToFront action when available.',locals_={'mainWindow':'applicationWindow','mainWindowViewModel':'windowViewModel'})
    method(0x138,'UnsubscribeFromApplicationStartup','Removes the application Startup handler registered by SubscribeToApplication.')
    method(0x139,'SubscribeToOtherInstanceNotifications','Registers the other-instance notification handler when a watcher exists.')
    method(0x13A,'UnsubscribeFromOtherInstanceNotifications','Removes the other-instance notification handler when a watcher exists.')
    method(0x15C,'ParseStartupCommandLine','Parses StartupOptions with automatic HelpWriter disabled; invokes the success callback or constructs HelpText for the error callback.',('arguments','onParsed','onError'),{'local_3':'formatParsingErrors','parserResult':'startupParseResult','helpText':'errorHelpText'})
    method(0x198,'CaptureParsedStartupOptions','Stores the parsed StartupOptions in the captured startup task context.')
    method(0x199,'LogParsedStartupInformation','Calls StartupLogging.LogStartupInformation with the captured options and bootstrapper user settings.')
    method(0x153,'NormalizeStoredUsagesAsync','Calls NormalizeUsagesIfRequired.ExecuteAsync for EtsLocalFolders.UsageAbsolutePath.')
    method(0x13C,'NormalizeUsagesWithTimingAsync','Times NormalizeStoredUsagesAsync using the usage-normalization duration logger.')
    method(0x13D,'InitializeAddInsWithTimingAsync','Times IUIAddInManager.InitializeAddInsAsync using the add-in duration logger.')
    method(0x171,'InitializeDashboardCaches','Initializes IProductImagesCacheInitializer and IProductPlacementRssFeedCacheInitializer.')
    method(0x152,'ReadStartupRssFeedIfEnabledAsync','Reads IRssReader asynchronously when LoadFromUrl is enabled; otherwise logs the skipped load and returns a completed task.')
    method(0x13E,'InitializeDashboardCachesAndRssFeedAsync','Reports cache initialization, times both dashboard cache initializers, then returns the configured RSS feed load.')
    method(0x173,'UpdateOnlineCatalogIfRequiredAsync','Calls ICatalogUpdateService.UpdateIfRequiredAsync.')
    method(0x13F,'UpdateOnlineCatalogAndSplashVersionsAsync','Times the online catalog update, then refreshes the versions displayed on the splash screen.')
    method(0x141,'EnsureAndUpdateManagementDataAsync','Ensures management data is present, refreshes splash versions, performs the management-data update and refreshes versions again; reports both startup phases.')
    method(0x143,'CheckProductStoresAsync','Runs CheckProductData.RunAllChecksAsync with the startup-progress callback.')
    method(0x144,'CheckProjectStoresAsync','Runs CheckProjectData.RunAllChecksAsync, which validates project-store tool/schema compatibility.')
    method(0x145,'ValidateStartupDataStoresAsync','Checks products first and projects second; preserves distinct process exit codes for failed checks.',locals_={'flag':'productChecksPassed','flag2':'projectChecksPassed'})
    method(0x146,'CheckProjectArchiveLocationAsync','Tests the configured archive directory asynchronously with the configured timeout and logs a missing location. It does not itself change the configured path.',('storageSettings',),{'flag':'archiveDirectoryExists'})
    method(0x190,'CheckConfiguredProjectArchiveLocationAsync','Supplies the bootstrapper user DataStorage settings to the archive-location check.')
    method(0x18E,'ResolveApplicationViewModel','Resolves IApplicationViewModel from the application container and stores it on the bootstrapper.')
    method(0x193,'ConfigureJumpList','Resolves IJumpListManager and calls Setup.')
    method(0x19A,'WaitForParallelStartupTasksAsync','Reports waiting progress and returns Task.WhenAll for the captured tasks that must finish before the splash screen closes.')
    method(0x17A,'StopMetricsWriterAsync','Stops MetricsWriterBackgroundService using the shutdown cancellation token.')
    method(0x17C,'StopErrorLogWriterAsync','Stops LogWriterBackgroundService using the shutdown cancellation token.')
    method(0x168,'UploadTelemetrySafelyAsync','Times IUploadService.Run, logs aggregate/native uploader errors and partial failure, and swallows the existing cancellation/error paths.',('cancellationToken',),{'flag':'uploadSucceeded','flag2':'attemptSucceeded','flag3':'attemptResult','ex':'aggregateUploadException','ex2':'uploadException','log':'uploadLogger','text':'missingUploaderMessage','innerException':'uploaderInnerException'})
    method(0x150,'InitializeTelemetryServicesAsync','Initializes IGlobalTelemetryProvider and chains metric/log writer starts and upload; observes failures and disables telemetry configuration on background-service initialization errors.',('services',),{'task':'telemetryInitialization','ex':'initializationException'})
    method(0x18B,'BuildContainerAndStartTelemetryAsync','Builds and publishes the Autofac container, initializes telemetry, records previous crashes, starts session/startup timers and internet sampling, and installs dispatcher/mouse/datapoint services.')
    method(0x166,'CompleteSessionTelemetry','Adds internet availability to the session timer, disposes that timer and the component/product-placement/licensing datapoints.')
    method(0x167,'FlushAndUploadTelemetry','Unless disposed, missing a container or cancelled, stops both telemetry writers, waits for them and uploads; catches and logs shutdown failures.',locals_={'task':'metricsWriteTask','task2':'errorLogWriteTask','ex':'telemetryWriteException'})
    method(0x151,'FinalizeTelemetryWithTimeout','Completes session telemetry, starts the flush/upload worker and waits up to 5000 ms; retains warning and Thread.Abort on timeout.',locals_={'thread':'telemetryFlushThread'})
    method(0x169,'DisposeShutdownCancellationTokenSource','Disposes the shutdown cancellation token source when present.',locals_={'cancellationTokenSource':'shutdownTokens'})
    method(0x163,'DisposeApplicationContainer','Disposes and clears the Autofac container, then resets ContainerService to a null context.')
    method(0x164,'DisposeApplicationContainerAsync','Asynchronously disposes and clears the Autofac container, then resets ContainerService to a null context.')
    method(0x165,'DisposeApplicationViewModel','Disposes and clears the application view model when present.')
    method(0x17E,'ReleaseBootstrapperResources','Unsubscribes instance notifications; closes splash/view model; finalizes telemetry; disposes cancellation state and the container; clears the App reference.')
    method(0x17F,'ReleaseBootstrapperResourcesAsync','Performs asynchronous cleanup, including cancellation before token-source disposal and asynchronous container disposal; clears the App reference.')
    method(0x16B,'DisposeBootstrapperResources','Runs the synchronous resource-release callback through the Disposer guard.',('disposing',))
    method(0x16D,'DisposeBootstrapperResourcesAsync','Runs the asynchronous resource-release callback through AsyncDisposer.')
    method(0x13B,'OnApplicationStartupAsync','Application Startup event orchestrator: parses options, initializes environment/container/telemetry, checks and updates stores, awaits startup tasks, handles pre-notifications and opens the first window. Exception and timer-finalization paths are retained.',locals_={'local_1':'startupServices','local_2':'startupWork','preNotificationWindowLauncher1':'notificationLauncher','hasPreNotificationResult':'notificationCheckResult','hasPreNotificationResult2':'availableNotification','result3':'notificationOutcome','result2':'notificationResult','ex':'startupException','startupTimer2':'remainingStartupTimer'})

    add('ETS',0x02000038,'StartupServiceContext','Captured bootstrapper and startup timer, with environment/container initialization and timed service callbacks.')
    add('ETS',0x0200003A,'StartupTaskContext','Captured command-line options, startup task collection and shared startup service context.')
    for token,name,reason in [
        (0xAF,'TelemetryShutdownTimeoutMilliseconds','Constant 5000 ms, matching the telemetry flush-thread join timeout.'),
        (0xB0,'logger','EtsBootstrapper LogManager logger.'),
        (0xB1,'disposer','Synchronous Disposer guard used by DisposeBootstrapperResources and IsDisposed.'),
        (0xB2,'asyncDisposer','AsyncDisposer guard used by DisposeBootstrapperResourcesAsync and IsDisposed.'),
        (0xB3,'application','App supplied by Setup; event, dispatcher, main-window and shutdown owner.'),
        (0xB4,'container','Autofac application container built at startup and disposed at shutdown.'),
        (0xB5,'applicationViewModel','Resolved application view model; starts, opens the first window and is disposed at shutdown.'),
        (0xB6,'startupScreen','Startup-screen view model used for progress/version display and splash closure.'),
        (0xB7,'dispatcher','WpfDispatcherService created from the App dispatcher.'),
        (0xB8,'preNotificationResult','Result of HasPreNotificationAsync used to decide and launch startup pre-notifications.'),
        (0xB9,'sessionTimer','Telemetry timer with context=session and span=overall; finalized with internet availability.'),
        (0xBA,'shutdownCancellationTokenSource','Cancellation source shared by telemetry/background writers, uploader and internet sampling.'),
        (0xBB,'internetAvailabilityCounter','Periodic internet sampler whose percentage is added to the session timer.'),
        (0xCB,'bootstrapper','Captured EtsBootstrapper instance used by the startup service callbacks.'),
        (0xD3,'startupServices','Captured StartupServiceContext shared by startup option/task callbacks.')]:
        add('ETS',0x04000000+token,name,reason)
