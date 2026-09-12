"""Script argument resolution and binding, reviewed through SDK callers.

Actual conversion/dispatch semantics are preserved, including empty-string
fallbacks, missing module failures and callback adapters returning null.
"""

def review(add):
    project='Knx.Ets.CalculatedParameters'
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add(project,token,name,reason,parameters,locals_,status)

    record(0x0600012E,'MatchesScriptModuleInstanceId','Compares a module instance ID to the captured ID in the module-argument iterator.',('moduleInstance',))
    record(0x0600013A,'DisposeModuleArgumentEnumerator','Marks iteration complete and disposes the inner argument enumerator when present.')
    record(0x0600001F,'EnumerateModuleInstanceArguments','Creates the reviewed iterator, which selects the device module by ID and yields its Arguments. Missing modules still fail on dereference.',('device','moduleInstanceId'),{'class':'argumentIterator'})
    record(0x0600012C,'MatchesScriptArgumentName','Compares IArgument.Name to the captured placeholder name.',('argument',))
    record(0x0600001E,'ResolveScriptArgumentValue','Looks up a named argument in the selected device module or delegates to Interface3 on a script facade. The existing fallback is the string containing two double quotes.',
           ('argumentName','argumentSource','moduleInstanceId'),{'e':'argumentMatch','text':'emptyJsonString','b':'device','argument':'matchingArgument','interface':'argumentProvider'})
    record(0x0600012A,'ExpandScriptArgumentMatch','Resolves the regex arg group through the engine and calls ToString for template substitution; no JSON escaping is added.',('match',))
    record(0x0600001D,'ExpandScriptArgumentTemplate','Replaces double-braced word placeholders with resolved module argument text before callers parse the resulting JSON.',('argumentTemplate','argumentSource','moduleInstanceId'),{'d':'expansionContext'})
    record(0x06000015,'GetParameterInstanceByReferenceId','Forwards the parameter-reference ID and module-instance ID to GetParameterInstanceFacadeByRefId.',('device','parameterReferenceId','moduleInstanceId'))
    record(0x06000031,'GetScriptParameterName','Uses a nonempty binding alias, otherwise the parameter-reference facade Name.',('binding','parameterReference'))
    record(0x06000125,'BindLeftCalculationParameter','Resolves a left-side binding to the current device/module parameter instance and pairs it with the effective script name.',('binding',),{'parameterInstanceRefDynamicFacade':'parameterInstance'})
    record(0x06000126,'BindRightCalculationParameter','Resolves a right-side binding using the same device/module context; its caller constructs the right-side dictionary.',('binding',),{'parameterInstanceRefDynamicFacade':'parameterInstance'})
    for token,name,reason in [
        (0x0600011D,'SelectLeftScriptParameterName','Returns the name key for the left-side parameter dictionary.'),
        (0x0600011E,'SelectLeftScriptParameterInstance','Returns the parameter-instance value for the left-side dictionary.'),
        (0x0600011F,'SelectRightScriptParameterName','Returns the name key for the right-side parameter dictionary.'),
        (0x06000120,'SelectRightScriptParameterInstance','Returns the parameter-instance value for the right-side dictionary.'),
        (0x06000121,'SelectInputValueName','Returns the input dictionary entry key.'),
        (0x06000122,'SelectOutputValueName','Returns the output dictionary entry key.'),
        (0x06000123,'WrapOutputValueAsParameter','Creates a mutable value-only parameter facade from an output dictionary entry.'),
        (0x06000128,'ConvertInputValueToParameter','Converts an input dictionary value for the selected engine and wraps it in a value-only parameter facade.')]:
        record(token,name,reason,('entry',))
    record(0x06000017,'CreateInlineCalculationEngineWithWrapper','Builds left/right parameter dictionaries, declares their script names, optionally wraps the selected transformation in ParameterCalculation and assigns input/output dictionaries by direction. Engine selection still uses the global preference.',
           ('wrapInFunction','calculation','direction','moduleInstanceId'),{'b':'bindingContext','dictionary':'leftParameters','dictionary2':'rightParameters','stringBuilder':'scriptBuilder','text':'declarationFormat','enumerator':'parameterNameEnumerator','text2':'parameterName','z':'scriptEngine'})
    record(0x06000016,'CreateInlineCalculationEngine','Uses the global ActiveScript preference as the wrapper flag when constructing the inline calculation engine.',('calculation','direction','moduleInstanceId'))
    record(0x06000019,'ExecuteScriptWithValueDictionariesAndWrapper','Declares input/output keys, optionally wraps the source, adapts dictionaries to parameter facades, executes, then copies output values back. The engine factory independently uses its global preference.',
           ('language','wrapInFunction','scriptSource','inputValues','outputValues'),{'c':'inputConversion','stringBuilder':'scriptBuilder','text':'declarationFormat','enumerator':'parameterNameEnumerator','text2':'parameterName','ex':'scriptException','text3':'outputName'})
    record(0x06000018,'ExecuteScriptWithValueDictionaries','Forwards value dictionaries and source using the global ActiveScript preference as the wrapper flag.',('language','scriptSource','inputValues','outputValues'))
    record(0x0600001C,'ExecuteCalculationFunction','Builds converted input and output script objects for the selected direction, expands the argument JSON, invokes the configured function, then converts output fields back into live parameter instances.',
           ('calculation','direction','moduleInstanceId'),{'text':'functionName','text2':'argumentTemplate','list':'inputBindings','list2':'outputBindings','h':'scriptInputs','h2':'scriptOutputs','h3':'scriptArguments','g':'inputBinding','g2':'initialOutputBinding','g3':'outputBinding','parameterInstanceRefDynamicFacade':'inputParameter','parameterInstanceRefDynamicFacade2':'initialOutputParameter','parameterInstanceRefDynamicFacade3':'outputParameter','text3':'invokedFunctionName','array':'functionArguments','ex':'scriptException','d':'errorSeverity','text4':'diagnosticCategory','parameterCalculationId':'calculationId'})
    record(0x06000020,'ValidateProposedParameterValue','Builds script values with the proposed replacement, invokes the validation function with the old value and expanded arguments, then interprets bool/numeric/string results. Strings are failure messages; null and other result types retain the existing success behavior.',
           ('validation','moduleInstanceId','parameterName','proposedValue','validationMessage'),{'h':'scriptValues','h2':'scriptArguments','obj':'previousValue','g':'binding','parameterInstanceRefDynamicFacade':'parameterInstance','obj2':'effectiveValue','obj3':'validationResult','ex':'scriptException','d':'errorSeverity','text':'diagnosticCategory','parameterValidationId':'validationId'})
    record(0x06000021,'InvokeDeviceEventHandlerFunction','Expands event argument JSON and invokes the selected function with device facade, management facade, async progress and script arguments. The SDK Device.ExecuteEventHandler caller establishes the three object roles.',
           ('eventHandlerName','argumentTemplate','deviceFacade','deviceManagement','asyncProgress','moduleInstanceId'),{'h':'scriptArguments','ex':'scriptException'})
    record(0x06000022,'FormatOrderNumberWithScript','Wraps the supplied script as OrderNumberFormattingScript, converts the raw bytes for JavaScript and returns displayOrderNumber through the function result.',('formattingScript','rawOrderNumber'),{'z':'scriptEngine'})

    # Standard reflection and NiL.JS calls establish callback roles first.
    record(0x06000130,'InvokeComScriptAction','Invokes the COM object default member with no arguments using invariant culture.')
    record(0x06000132,'InvokeJavaScriptAction','Calls the captured NiL.JS Function with null this/arguments and discards the result.')
    record(0x06000134,'InvokeComScriptFunctionAndConvertResult','Invokes the COM default member and converts the result through the engine to T.')
    record(0x06000136,'InvokeJavaScriptFunctionAndConvertResult','Calls the captured NiL.JS Function and converts the returned JSValue through the engine to T.')
    record(0x0600002C,'CreateScriptActionOrNull','Creates an Action for a NiL.JS Function or a runtime type named __ComObject; returns null for null or unsupported inputs.',('scriptCallable',),{'class':'comCallback','jsvalue':'javaScriptValue','class2':'javaScriptCallback','value':'unwrappedValue'})
    record(0x0600002D,'CreateScriptFunctionOrNull','Creates a Func<T> for a NiL.JS Function or COM default member, converting the result through this engine; returns null for unsupported inputs.',('scriptCallable',),{'i':'conversionContext','jsvalue':'javaScriptValue','class':'javaScriptCallback','value':'unwrappedValue'})

    for token,name,reason in [
        (0x02000029,'ScriptValueParameterFacade','Mutable Value wrapper implementing the parameter-instance facade for dictionary execution; unrelated properties keep their default values.'),
        (0x0200002A,'ScriptBindingSelectors','Cached dictionary selectors for parameter names, instances and output wrappers.'),
        (0x0200002B,'CalculationParameterBindingContext','Captures calculation/device and module instance for left/right binding projections.'),
        (0x0200002C,'ScriptInputConversionContext','Captures the engine used to convert dictionary inputs to parameter wrappers.'),
        (0x0200002D,'ScriptArgumentExpansionContext','Captures engine, argument source and module instance for template matches.'),
        (0x0200002E,'ScriptArgumentNameMatch','Captured name predicate over module IArgument values.'),
        (0x0200002F,'ScriptModuleInstanceIdMatch','Captured module-ID predicate used while enumerating script arguments.'),
        (0x02000030,'ComScriptActionCallback','Captured COM object invoked through its default member.'),
        (0x02000031,'JavaScriptActionCallback','Captured NiL.JS Function used as an Action.'),
        (0x02000032,'ScriptFunctionConversionContext','Generic context holding engine and callable for Func<T> conversion. The type alias remains pending until generic type mapping is supported.'),
        (0x02000033,'JavaScriptFunctionCallback','Generic NiL.JS callback sharing the result-conversion context; generic type alias remains pending.'),
        (0x02000034,'ModuleInstanceArgumentIterator','State machine enumerating Arguments from the selected device module and disposing the inner enumerator.')]:
        record(token,name,reason)
    for token,name,reason in [
        (0x0400008A,'parameterInstanceReferenceId','Value-only facade Id backing field; no nondefault assignment inferred.'),
        (0x0400008B,'parameterReference','Value-only facade ParameterRefFacade backing field; remains default.'),
        (0x0400008C,'isActive','Facade IsActive backing value.'),
        (0x0400008D,'value','Mutable script value.'),
        (0x0400008E,'indentation','Facade Indentation backing value.'),
        (0x0400008F,'uniqueId','Facade UniqueId backing field; remains default.'),
        (0x04000090,'hasDefaultValues','Facade HasDefaultValues backing field; remains default.'),
        (0x04000091,'baseValue','Facade BaseValue backing field; remains default.'),
        (0x04000092,'initialValue','Facade InitialValue backing field; remains default.'),
        (0x04000094,'sharedCallbacks','Singleton script-binding selectors.'),
        (0x04000095,'selectLeftParameterName','Cached left-dictionary name selector.'),
        (0x04000096,'selectLeftParameterInstance','Cached left-dictionary instance selector.'),
        (0x04000097,'selectRightParameterName','Cached right-dictionary name selector.'),
        (0x04000098,'selectRightParameterInstance','Cached right-dictionary instance selector.'),
        (0x04000099,'selectInputValueName','Cached input dictionary key selector.'),
        (0x0400009A,'selectOutputValueName','Cached output dictionary key selector.'),
        (0x0400009B,'wrapOutputValue','Cached output value facade constructor callback.'),
        (0x0400009D,'calculation','Calculation supplying device and parameter bindings.'),
        (0x0400009E,'moduleInstanceId','Instance used when resolving calculation parameter bindings.'),
        (0x040000A0,'scriptEngine','Engine converting input dictionary values.'),
        (0x040000A2,'scriptEngine','Engine resolving argument template matches.'),
        (0x040000A3,'argumentSource','Device or argument-provider facade for template values.'),
        (0x040000A4,'moduleInstanceId','Instance used to resolve template arguments.'),
        (0x040000A6,'argumentName','Captured IArgument.Name match.'),
        (0x040000A8,'moduleInstanceId','Captured module ID match.'),
        (0x040000AA,'comCallable','COM object invoked by the Action callback.'),
        (0x040000AC,'javaScriptFunction','NiL.JS Function invoked by the Action callback.'),
        (0x040000AE,'scriptEngine','Engine performing generic callback result conversion.'),
        (0x040000AF,'scriptCallable','Callable captured for generic COM callback construction.'),
        (0x040000B1,'javaScriptFunction','NiL.JS Function invoked by the Func<T> callback.'),
        (0x040000B2,'conversionContext','Engine/callable context shared with the generic JavaScript callback.'),
        (0x040000B4,'state','Argument iterator state.'),
        (0x040000B5,'currentArgument','Current yielded module argument.'),
        (0x040000B6,'initialThreadId','Thread ID used for initial iterator reuse.'),
        (0x040000B7,'moduleInstanceId','Active iteration module ID.'),
        (0x040000B8,'initialModuleInstanceId','Module ID copied into an active enumerator.'),
        (0x040000B9,'device','Active iteration device.'),
        (0x040000BA,'initialDevice','Device copied into an active enumerator.'),
        (0x040000BB,'argumentEnumerator','Enumerator over the selected module Arguments.')]:
        record(token,name,reason)

    # Public framework contract names stay intact; only local bindings are proposed.
    record(0x06000139,None,'Preserve IEnumerator.MoveNext; locate iterator body locals for semantic application.',locals_={'flag':'hasNextArgument','num':'currentState','class2':'moduleMatch','b':'moduleInstance','argument':'nextArgument'},status='retain-method-name')
    record(0x0600013E,None,'Preserve IEnumerable<IArgument>.GetEnumerator; locate the returned iterator local.',locals_={'class2':'enumerator'},status='retain-method-name')
