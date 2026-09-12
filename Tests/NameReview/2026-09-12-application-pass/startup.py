"""Startup, single-instance transport, and directly coupled module roles.

These decisions describe existing behavior, including unusual side effects;
they do not change process handling, script preference or integrity checks.
"""

def review(add):
    # Library leaves read before the startup caller that configures them.
    script = 'Knx.Ets.CalculatedParameters'
    for token, name, reason, parameters in [
        (0x06000010, 'ParseScriptingLanguage', 'Case-insensitive VBScript/JavaScript/JScript recognition; unsupported names throw.', ('languageName',)),
        (0x06000011, 'GetPreferActiveScriptingEngines', 'Returns the static preference initialized true and used by script-engine factories.', ()),
        (0x06000012, 'SetPreferActiveScriptingEngines', 'Sets that preference; Startup passes the parsed PreferActiveScriptingEngines setting.', ('preferActiveScriptingEngines',)),
        (0x06000024, 'GetInputParameters', 'Returns the parameter dictionary read into script variables by both JavaScript and VBScript execution implementations.', ()),
        (0x06000025, 'SetInputParameters', 'Stores the input dictionary selected from left/right parameters according to calculation direction.', ('inputParameters',)),
        (0x06000026, 'GetOutputParameters', 'Returns the dictionary whose facade values receive the execution results.', ()),
        (0x06000027, 'SetOutputParameters', 'Stores the output dictionary selected from left/right parameters according to calculation direction.', ('outputParameters',)),
        (0x06000028, 'GetScriptSource', 'Returns the source text supplied to the selected engine factory.', ()),
        (0x06000029, 'SetScriptSource', 'Stores the source text after the language/platform engine is constructed.', ('scriptSource',)),
        (0x06000013, 'CreateScriptEngine', 'Uses the configured preference and forwards language/source to the explicit engine factory.', ('language', 'scriptSource')),
        (0x06000014, 'CreateScriptEngineWithPreference', 'Selects active scripting only when requested on Win32NT, otherwise selects NiL.JS or the VBScript interpreter, then stores the source. Unsupported languages throw.', ('language', 'preferActiveScriptingEngines', 'scriptSource'))]:
        add(script, token, name, reason, parameters)
    add(script, 0x02000005, 'ParameterScriptEngine', 'Abstract scripting engine used for calculated-parameter transformations, validation and script function invocation; factory selects active or managed JavaScript/VBScript implementations.')
    for token, name, reason in [
        (0x04000007, 'ParameterCalculationFunctionName', 'Literal ParameterCalculation used for generated calculation functions.'),
        (0x04000008, 'logger', 'LogManager logger owned by the scripting-engine base type.'),
        (0x04000009, 'preferActiveScriptingEngines', 'Backing preference read by the default factory and changed by startup configuration.'),
        (0x0400000A, 'inputParameters', 'Facades whose values initialize script variables before execution.'),
        (0x0400000B, 'outputParameters', 'Facades to which script variable values are written after execution.'),
        (0x0400000C, 'scriptSource', 'Backing text read by GetScriptSource and assigned by the factory.')]:
        add(script, token, name, reason)

    for token, name, reason, parameters, locals_ in [
        (0x060001D7, 'RegisterMyKnxLicensingServices', 'Registers the licensing facade singleton with logging and synchronized-access decorators.', ('builder',), None),
        (0x060001D8, 'RegisterMyKnxOAuthServices', 'Registers the OAuth facade singleton with logging and synchronized-access decorators.', ('builder',), None),
        (0x060001D9, 'ConfigureScriptingEnginePreference', 'Parses the PreferActiveScriptingEngines application setting, falls back to false on exception, and calls the reviewed scripting-engine preference setter.', (), {'flag':'preferActiveScriptingEngines'}),
        (0x060001DD, 'TryGetMainWindowHandle', 'Invokes the stored UI dispatcher, ensures the current MainWindow handle, and returns zero with a warning when absent or when lookup throws.', (), {'intPtr':'mainWindowHandle', 'window':'mainWindow', 'ex':'windowLookupException'}),
        (0x060001DC, 'RegisterApplicationModules', 'Registers UI, ObjectModel, MyKnx, metrics, ViewModel, local, plugin-loader and compatibility modules plus the singleton datapoint type service.', ('builder',), None)]:
        add('ETS', token, name, reason, parameters, locals_)
    add('ETS', 0x0400012C, 'logger', 'Startup logger used for failed main-window lookups.')
    add('ETS', 0x0400012D, 'dispatcher', 'Build-supplied IDispatcher used to obtain the window handle on the UI thread.')

    # Named mutex and message transport, with explicit iterator state names.
    add('ETS', 0x060001EB, 'CreateSingleInstanceMutex', 'Creates the fixed local named mutex and grants the world SID full control; preserves the existing access rule.', locals_={'mutexAccessRule':'accessRule', 'mutexSecurity':'security'})
    add('ETS', 0x060001FD, 'FindOtherEtsProcesses', 'Enumerates processes whose names match the existing ETS6[CN]{1} regex and excludes the current PID.', locals_={'process_0':'candidateProcess'})
    add('ETS', 0x060001F4, 'TerminateWindowlessEtsProcessesAndCheckForOthers', 'Kills matching processes without a main window, enumerates again and returns whether another ETS process remains. Existing Task.Delay is unawaited; the name does not imply a waited grace period.', locals_={'list':'otherEtsProcesses', 'process_0':'candidateProcess', 'enumerator':'processEnumerator', 'process':'otherProcess'})
    add('ETS', 0x060001F7, 'WriteLaunchArgumentLines', 'Writes each launch argument as a UTF8 line with AutoFlush to the supplied stream.', ('arguments','destination'), {'streamWriter':'argumentWriter','enumerator':'argumentEnumerator','text':'argument'})
    add('ETS', 0x0600020A, 'DisposeArgumentReader', 'Resets the iterator state to -1 and disposes the active stream reader.')
    add('ETS', 0x060001F8, 'ReadLaunchArgumentLines', 'Creates the reviewed lazy iterator over the received stream. MoveNext seeks to the start, splits CRLF and returns the trailing line after removing the EOF sentinel.', ('source',), {'local_1':'argumentLines'})
    add('ETS', 0x060001F5, 'ForwardLaunchArgumentsToMainInstance', 'Connects to the local single-instance named pipe with a 500 ms timeout and writes argument lines when nonempty.', ('arguments',), {'namedPipeClientStream':'mainInstancePipe'})
    add('ETS', 0x060001F9, 'RaiseAnotherInstanceConnected', 'Invokes the captured NoticedAnotherInstanceConnected subscribers with the supplied event arguments.', ('eventArgs',), {'eventHandler':'connectedHandlers'})
    add('ETS', 0x060001F6, 'ListenForOtherInstanceArgumentsAsync', 'Waits for named-pipe connections until cancellation, copies each payload, parses nonempty argument lines and raises the event; parse failures are logged and listening continues.', ('cancellationToken',), {'namedPipeServerStream':'instancePipe', 'collection':'arguments', 'memoryStream1':'argumentPayload', 'memoryStream':'completedPayload', 'string_0':'argument', 'ex':'argumentParseException'})
    add('ETS', 0x02000057, 'LaunchArgumentLineEnumerator', 'Enumerable/iterator that reads UTF8 CRLF-delimited launch arguments from a received stream and owns reader disposal.')
    for token, name, reason in [
        (0x04000135, 'SingleInstanceMutexName', 'Literal name used by CreateSingleInstanceMutex.'),
        (0x04000136, 'MutexWaitTimeoutMilliseconds', 'The 1000 ms timeout in TryAcquireExclusiveLock.'),
        (0x04000137, 'ownsMutex', 'Set after acquisition or abandoned-mutex recovery and cleared after ReleaseMutex.'),
        (0x04000138, 'instanceMutex', 'Named mutex created during lock construction and released/disposed by the lock owner.'),
        (0x04000139, 'LocalPipeServerName', 'Dot server name passed to NamedPipeClientStream for local transport.'),
        (0x0400013A, 'PipeConnectTimeoutMilliseconds', '500 ms timeout passed to the client Connect call.'),
        (0x0400013B, 'MaximumPipeServerInstances', 'One allowed server instance passed to NamedPipeServerStream.'),
        (0x0400013C, 'SingleInstancePipeName', 'Shared fixed pipe name used by client and server constructors.'),
        (0x0400013D, 'etsProcessNamePattern', 'Existing regex matching ETS6C/ETS6N process names.'),
        (0x0400013E, 'logger', 'Watcher logger for connection/listener/argument parsing failures.'),
        (0x0400013F, 'argumentEncoding', 'UTF8 encoding shared by the writer and iterator reader.'),
        (0x04000140, 'listenerCancellation', 'Cancellation source used by Start and canceled by Stop.'),
        (0x04000141, 'instanceLock', 'SingleInstanceApplicationLock acquired by Start and released by Stop.'),
        (0x04000142, 'anotherInstanceConnectedHandlers', 'Backing subscriber delegate for NoticedAnotherInstanceConnected.'),
        (0x04000143, 'isMainInstance', 'Backing state of the readable IsMainInstance property.'),
        (0x04000150, 'state', 'Iterator state switched by MoveNext, Dispose and GetEnumerator.'),
        (0x04000151, 'currentLine', 'Yielded line returned by both Current accessors.'),
        (0x04000152, 'initialThreadId', 'Creator thread ID used for first-enumerator reuse.'),
        (0x04000153, 'sourceStream', 'Active stream copied from the initial argument on GetEnumerator.'),
        (0x04000154, 'initialSourceStream', 'Original stream argument retained for creating enumerators.'),
        (0x04000155, 'argumentReader', 'UTF8 reader constructed by MoveNext and disposed by DisposeArgumentReader.'),
        (0x04000156, 'lineBuffer', 'Accumulates characters until CRLF or EOF.'),
        (0x04000157, 'currentCharacter', 'Peek/Read result including the -1 EOF sentinel.')]:
        add('ETS', token, name, reason)
    for token, names, reason in [
        (0x060001E9, {'flag':'lockAcquired'}, 'Retain TryAcquireExclusiveLock; false is timeout, true also includes abandoned-mutex acquisition.'),
        (0x06000208, {'num':'iteratorState'}, 'Retain IDisposable.Dispose and name its saved iterator state.'),
        (0x06000209, {'flag':'hasCurrentLine','text':'completedLine'}, 'Retain IEnumerator.MoveNext; name yielded-line state without changing the CRLF/EOF algorithm.'),
        (0x0600020E, {'local_2':'enumerator'}, 'Retain IEnumerable.GetEnumerator and its same-thread reuse contract.')]:
        add('ETS', token, None, reason, locals_=names, status='retain-method-name')

    plugin = 'Knx.Ets.PluginLoader'
    add(plugin, 0x02000015, 'PluginLoaderModule', 'Autofac module that registers IPluginFactory and schedules assembly-identity validation.')
    add(plugin, 0x06000053, 'RecordReferencedAssemblyIdentityMismatches', 'Compares the referenced type assembly public key/token with the plugin loader and expected token; records existing Versioning markers for mismatches.', ('referencedType',), {
        'name':'loaderAssemblyName','publicKey':'loaderPublicKey','publicKeyToken':'loaderPublicKeyToken',
        'location':'referencedAssemblyPath','name2':'referencedAssemblyName','publicKey2':'referencedPublicKey',
        'publicKeyToken2':'referencedPublicKeyToken','text':'loaderTokenText','text2':'referencedTokenText'})
    add(plugin, 0x06000054, 'RecordEntryAssemblyIdentityMismatches', 'Compares the entry assembly with the plugin loader and expected token, recording existing version/schema markers without changing enforcement behavior.', locals_={
        'name':'loaderAssemblyName','publicKey':'loaderPublicKey','publicKeyToken':'loaderPublicKeyToken',
        'text':'entryTokenText','array':'entryPublicKey','location':'entryAssemblyPath','name2':'entryAssemblyName','text2':'loaderTokenText'})
    add(plugin, 0x06000050, 'CheckReferencedAssemblyIdentities', 'Invokes the identity comparison for ObjectModel, plugin facade, SDK Context and plugin-loader dependencies.')
    add(plugin, 0x06000052, 'CheckApplicationAssemblyIdentities', 'Checks the loader token then entry and referenced assembly identities; preserves every Versioning side effect.', locals_={'text':'loaderTokenText'})
    add(plugin, 0x06000051, 'CheckAssemblyIdentitiesAndUpdateLoggingAsync', 'Starts the async-void state machine that runs CheckApplicationAssemblyIdentities, then sets the existing Project.EnableExtendedLogging value from the version components.', locals_={'a':'identityCheckState'})
    add(plugin, 0x02000016, 'AssemblyIdentityCheckStateMachine', 'Async-void state for assembly identity checks and the existing logging-state update.')
    for token, name, reason in [
        (0x04000035,'state','Async state -1/0/-2 used by MoveNext.'),
        (0x04000036,'methodBuilder','AsyncVoidMethodBuilder handling continuation/completion/errors.'),
        (0x04000037,'module','Captured PluginLoaderModule that owns the check methods.'),
        (0x04000038,'identityCheckAwaiter','Awaiter of the background assembly identity check task.')]:
        add(plugin, token, name, reason)
    add(plugin, 0x06000057, None, 'Retain IAsyncStateMachine.MoveNext; identify its task, version components and exception.', locals_={'num':'resumeState','mr':'module','task':'identityCheckTask','array':'versionComponents','ex':'identityCheckException'}, status='retain-method-name')
    add(plugin, 0x06000056, 'DecodeInternedObfuscatedString', 'Transforms successive character bytes with incrementing XOR state, swaps byte order and interns the result; naming only, no decoding algorithm change.', ('encodedText','keyOffset'), {
        'array':'characters','num':'key','num2':'characterIndex','num3':'currentIndex','num4':'writeIndex',
        'array2':'destination','num5':'destinationIndex','c':'encodedCharacter','b':'lowByte','b2':'highByte','b3':'swappedByte'})
    for token in [0x04000034, 0x04000039]:
        add(plugin, token, None, 'Short string field with special storage metadata; role not established by the reviewed startup chain.', status='unresolved-storage-role')

    compat = 'Knx.Ets.Compatibility'
    add(compat, 0x0200000B, 'PluginHostCompatibilityModule', 'Autofac module selects IPluginHostFactory registration based on ApplicationSettings.IsCompatibilityMode and supplies the main-window handle callback.')
    add(compat, 0x04000018, 'getMainWindowHandle', 'Constructor callback registered as the Func<IntPtr> dependency of the compatibility plugin host factory.')
    add(compat, 0x06000039, None, 'Always returns true for the registered window/device delegate; the precise callback role still needs its consumer reviewed.', status='unresolved-callback-role')
