"""Calculated-parameter engines: value conversion, execution and script objects.

Every editable override in each selected family is reviewed explicitly. Names
describe each shared contract; reasons retain differences between implementations.
"""

def review(add):
    project='Knx.Ets.CalculatedParameters'
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add(project,token,name,reason,parameters,locals_,status)

    # Recognizable framework conversions establish direction before callers.
    for token,reason in [
        (0x0600002E,'Abstract conversion from parameter values to the representation expected by a script engine.'),
        (0x06000095,'Active JavaScript converts large integer types to double, Color to ARGB, DateTime to date text, IPAddress to text and byte arrays using the helper dispatch eval.'),
        (0x0600009F,'NiL.JS performs the JavaScript scalar conversions and turns byte arrays into object arrays.'),
        (0x060000B9,'VBScript interpreter keeps signed/unsigned integer values in int range as int and widens larger values to decimal or double.'),
        (0x06000141,'Active VBScript uses the same range-sensitive integer conversion as the interpreter.')]:
        record(token,'ConvertParameterValueToScript',reason,('parameterValue',))
    for token,reason in [
        (0x0600002F,'Base conversion handles Color, textual IPAddress and byte arrays, then Convert.ChangeType; failed conversions return the original value.'),
        (0x06000096,'Active JavaScript additionally reads COM array elements as bytes and converts date text or epoch milliseconds to DateTime, then falls back to the base conversion.'),
        (0x060000A0,'NiL.JS unwraps JSValue, rounds selected integral targets, converts JS arrays to bytes and falls back to the base conversion.')]:
        record(token,'ConvertScriptValueToParameterType',reason,('scriptValue','targetType'))
    for token,reason in [
        (0x06000008,'Abstract COM type selected by ActiveScript engine construction.'),
        (0x06000098,'Returns Type.GetTypeFromProgID("JScript") cached by the JavaScript implementation.'),
        (0x06000142,'Returns Type.GetTypeFromProgID("VBScript") cached by the VBScript implementation.')]:
        record(token,'GetActiveScriptComType',reason)

    record(0x060000A5,'ConvertJavaScriptArrayElementToByte','Converts the JSValue element value to byte for the byte-array projection.',('element',))
    record(0x06000033,'HasScriptErrors','Returns the flag set by the script-site error callback.')
    record(0x06000034,'GetScriptErrorDetails','Returns the formatted error buffer including source line and position.')
    record(0x06000035,'GetScriptErrorMessages','Returns the short error-description buffer used when wrapping execution failures.')
    record(0x0600003E,'AddNamedScriptObject','Lazily creates the script-site dictionary and adds a named host object; duplicate names still throw.',('name','value'))
    record(0x06000007,'CreateParsedActiveScriptSession','Creates the COM engine and host site, initializes the parser, parses the stored source and wraps parser/site failures in the scripting exception. Returns both engine and site.',locals_={
        'i':'engine','a':'scriptSite','class':'parser','obj':'parseResult','excepinfo':'parseExceptionInfo','ex':'parseException','text':'parseError','text2':'siteError'})
    record(0x06000097,'GetOrCreateConversionScriptDispatch','Creates and caches a JScript helper dispatch/site used by value conversion, parses the helper source and reports parse errors.',locals_={
        'i':'engine','a':'scriptSite','class':'parser','obj':'parseResult','excepinfo':'parseExceptionInfo','ex':'parseException','text':'parseError','text2':'siteError','p':'scriptDispatch'})
    record(0x060000BB,'EnsureVbScriptParsed','Parses the stored source once into a StatementList; logs and wraps parse errors.',locals_={'ex':'parseException'})
    record(0x0600009D,'EnumerateRemainingItems','Wraps the supplied enumerator as an enumerable. Its iterator advances/yields and disposes the input on normal completion; early Dispose remains empty.',('sourceEnumerator',),{'b':'enumerableAdapter'})
    record(0x0600009E,'ConvertFunctionArgumentsToJavaScriptObjects','Converts reflected script parameter objects to ExpandoObject dictionaries and passes other arguments through.',('argumentValues',),{
        'obj':'argument','dictionary':'scriptObject','enumerator':'fieldEnumerator','keyValuePair':'fieldValue','array':'completedArguments'})

    for token,reason in [
        (0x0600001B,'Abstract contract executing the configured script against input/output parameter facades.'),
        (0x06000005,'ActiveScript writes converted input properties, invokes ParameterCalculation and reads/converts output properties; closes/releases the COM engine in finally.'),
        (0x0600009B,'NiL.JS defines input variables, evaluates source, copies defined output variables to facades and wraps JSException.'),
        (0x060000B8,'VBScript interpreter ensures the syntax tree is parsed, populates RunEnvironment variables, runs the tree and copies outputs through parameter conversion.')]:
        record(token,'ExecuteParameterScript',reason)
    for token,reason in [
        (0x06000030,'Abstract function invocation with a name, positional values and named host objects.'),
        (0x06000006,'ActiveScript adds named host objects, invokes the selected dispatch method with the supplied arguments, wraps site errors and closes/releases the COM engine.'),
        (0x0600009C,'NiL.JS defines host globals, evaluates source, calls the named Function, writes reflected argument changes back into ScriptParameterObject fields, and returns the JS result value.'),
        (0x060000BA,'VBScript interpreter does not implement named function calls and throws NotImplementedException; that limitation remains unchanged.')]:
        record(token,'InvokeParameterScriptFunction',reason,('functionName','argumentValues','namedHostObjects'))
    for token,reason in [
        (0x0600001A,'Abstract validation/diagnostic contract called before using the shared static script; null/empty indicate no reported errors.'),
        (0x06000004,'ActiveScript creates/parses a session, adds host objects, sets the existing script state and returns site details or an exception message on failure; success returns null.'),
        (0x0600009A,'NiL.JS implementation returns empty text without validating. Preserve this behavior.'),
        (0x060000B7,'VBScript interpreter throws NotImplementedException for this diagnostic contract. Preserve this behavior.')]:
        record(token,'ValidateScriptAndGetErrors',reason,('namedHostObjects',))

    # Reflective script argument storage; existing IReflect names remain intact.
    record(0x0600006B,'ReadStoredScriptFieldValue','Returns the mutable value held by the FieldInfo adapter.')
    record(0x0600006C,'WriteStoredScriptFieldValue','Assigns the mutable value held by the FieldInfo adapter.',('value',))
    record(0x0600007A,'SelectScriptFieldName','Returns the dictionary key for a stored script field.',('entry',))
    record(0x0600007B,'SelectScriptFieldValue','Returns the field adapter stored value for a dictionary entry.',('entry',))
    record(0x06000050,'SnapshotScriptFieldValues','Projects the field dictionary into a new name/value dictionary using the reviewed selectors.')
    record(0x06000051,'SetTypedScriptField','Creates a FieldInfo adapter with an explicit type, assigns its value and replaces the named dictionary entry.',('name','fieldType','value'),{'dictionary':'fields','a':'field'})
    record(0x06000052,'SetScriptField','Creates a FieldInfo adapter using the value runtime type or object for null, then replaces the named entry.',('name','value'),{'dictionary':'fields','a':'field'})
    record(0x06000053,'GetScriptFieldValueOrNull','Looks up a field by name and returns its stored value or null.',('name',),{'a':'field'})
    record(0x06000056,'ConvertJsonTokenToScriptValue','Recursively converts JSON objects and arrays into reflective script objects; scalar token kinds use the existing typed conversions and unhandled kinds return null.',('token',),{
        'obj':'scriptValue','h2':'scriptObject','jarray':'jsonArray','h3':'scriptArray','i':'elementIndex'})
    record(0x06000055,'LoadJsonObjectFields','Converts each JSON property and stores non-null values with their runtime type.',('jsonObject',),{'enumerator':'propertyEnumerator','jproperty':'property','obj':'value'})
    record(0x06000054,'LoadScriptFieldsFromJson','Parses text as a JObject then loads its property values.',('json',))
    record(0x06000058,'RejectDynamicScriptMethodCreation','Throws an error naming the method that the script attempted to add.',('name','implementation'))
    record(0x06000059,'RejectDynamicScriptPropertyCreation','Throws an error naming the property that the script attempted to add.',('name',))
    # The two Interface0 members have external reflection contracts. Keep them
    # explicitly pending until the complete contract can be named safely.
    record(0x06000057,'RejectDynamicScriptFieldCreation','Throws an error naming the field that the script attempted to add.',('name',))
    record(0x06000068,'RejectDynamicScriptFieldCreation','Interface declaration of the rejected dynamic field-creation request.',('name',))
    record(0x0600005A,'RejectDynamicScriptMemberRemoval','Throws NotImplementedException for member removal.',('member',))
    record(0x06000069,'RejectDynamicScriptMemberRemoval','Interface declaration of the unimplemented dynamic member-removal request.',('member',))

    for token,name,reason in [
        (0x02000003,'ActiveParameterScriptEngine','Shared COM-backed implementation for parameter script validation, execution and function calls.'),
        (0x02000006,'ActiveScriptHostSite','Stores named host objects and records script errors with source positions for the COM engine.'),
        (0x02000014,'ActiveJavaScriptParameterEngine','JScript COM engine selection and JavaScript-specific value conversion.'),
        (0x02000015,'NiLJavaScriptParameterEngine','Managed JavaScript implementation using NiL.JS contexts, functions and JSValue conversion.'),
        (0x02000016,'JavaScriptConversionDelegateCache','Singleton and cached byte-array element conversion callback.'),
        (0x02000018,'EnumeratorEnumerableAdapter','Generic adapter wrapping an existing IEnumerator as IEnumerable for JavaScript argument traversal.'),
        (0x02000019,'InterpretedVbScriptParameterEngine','Managed VBScript execution through the local parser, StatementList and RunEnvironment.'),
        (0x02000039,'ActiveVbScriptParameterEngine','VBScript COM engine selection and integer conversion.'),
        (0x0200000A,'ScriptParameterObject','COM-visible reflective object whose mutable named fields carry script inputs, outputs and parsed JSON arguments.'),
        (0x0200000C,'ScriptValueField','FieldInfo adapter storing a field name, declared type and mutable script value.'),
        (0x0200000D,'ScriptFieldProjectionDelegateCache','Cached selectors for field-name/value snapshots.'),
        (0x0200001C,'ParameterScriptException','Exception used to wrap parsing and execution failures in all reviewed engine implementations.'),
        (0x02000009,'ScriptParameterBinding','Pairs a parameter-reference facade with its optional script alias.'),
        (0x0200001A,'ParameterCalculationDefinition','Holds language, left/right parameters, transformation source/functions and calculation/device/module context.'),
        (0x02000027,'ParameterValidationDefinition','Holds validation function/argument text, referenced parameters and validation/device/module context.')]:
        record(token,name,reason)
    for token,name,reason in [
        (0x0400000E,'scriptErrorDetails','Formatted error descriptions with source line and position.'),
        (0x0400000F,'scriptErrorMessages','Short error descriptions used when wrapping failures.'),
        (0x04000010,'hasScriptErrors','Flag set by the script error callback.'),
        (0x04000011,'namedHostObjects','Host objects returned to the COM engine by name.'),
        (0x04000016,'parameterReference','Facade returned by ScriptParameterBinding.ParameterRef.'),
        (0x04000017,'scriptAlias','Optional script name returned by ScriptParameterBinding.AliasName.'),
        (0x04000019,'fieldsByName','Mutable name-to-FieldInfo dictionary exposed by the reflective script object.'),
        (0x0400001B,'fieldName','FieldInfo.Name backing text.'),
        (0x0400001C,'declaredFieldType','FieldInfo.FieldType backing type.'),
        (0x0400001D,'storedValue','Mutable value shared by reflection GetValue/SetValue and direct helpers.'),
        (0x0400001F,'sharedCallbacks','Singleton script-field projection callbacks.'),
        (0x04000020,'selectFieldName','Cached field-name selector.'),
        (0x04000021,'selectFieldValue','Cached stored-value selector.'),
        (0x04000023,'ConversionHelperScriptSource','Literal JScript source loaded for the cached conversion dispatch.'),
        (0x04000024,'jscriptComType','Cached Type.GetTypeFromProgID("JScript").'),
        (0x04000025,'conversionScriptDispatch','Cached COM dispatch used for JavaScript value conversion.'),
        (0x04000026,'conversionScriptSite','Site retained with the cached conversion dispatch.'),
        (0x04000027,'localUnixEpoch','Local-time epoch used for millisecond-to-DateTime conversion.'),
        (0x04000029,'javaScriptLogger','NiL.JS engine logger for missing reflected output fields; distinct from the inherited base logger.'),
        (0x0400002A,'localUnixEpoch','Stored local-time epoch; no usage inferred beyond the initializer.'),
        (0x0400002C,'sharedCallbacks','Singleton JavaScript conversion callbacks.'),
        (0x0400002D,'convertArrayElementToByte','Cached JS array element-to-byte conversion.'),
        (0x04000037,'state','Iterator state for the existing-enumerator wrapper.'),
        (0x04000038,'currentItem','Current yielded item.'),
        (0x04000039,'initialThreadId','Thread ID controlling first-enumerator reuse.'),
        (0x0400003A,'sourceEnumerator','Enumerator actively advanced by MoveNext.'),
        (0x0400003B,'initialSourceEnumerator','Original enumerator copied into active state by GetEnumerator.'),
        (0x0400003D,'parsedStatements','Cached VBScript syntax tree, populated once and passed to VBScript.Run.'),
        (0x040000D6,'vbScriptComType','Cached Type.GetTypeFromProgID("VBScript").')]:
        record(token,name,reason)

    # These engine-independent callers use the now reviewed virtual contracts.
    record(0x0600002A,'ConvertValueForScript','Forwards a parameter value to the engine-specific conversion contract.',('parameterValue',))
    record(0x0600002B,'ConvertScriptResultToType','Forwards a result and desired CLR type to the engine-specific output conversion contract.',('scriptValue','targetType'))
    record(0x060000D9,'ValidateStaticScriptAndGetErrors','Returns null without a static script engine, otherwise validates with an ApplicationProgram host wrapper.')
