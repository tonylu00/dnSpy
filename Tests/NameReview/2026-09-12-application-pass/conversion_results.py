"""Conversion diagnostic/result leaves and input validation before orchestration."""

def review(add):
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add('Knx.Ets.CvNext',token,name,reason,parameters,locals_,status)

    # Actual log categories and resource keys establish vocabulary independently
    # of obfuscated caller names. Embedded resource base-name strings stay intact.
    record(0x02000012,'ConversionLoggers','Factories for the seven literal Knx.Ets.CvNext logging categories.')
    for token,category in [(0x0600005C,'Container'),(0x0600005D,'Converter'),(0x0600005E,'Patcher'),
                           (0x0600005F,'Dispatcher'),(0x06000060,'Persistence'),(0x06000061,'Signer'),(0x06000062,'Validation')]:
        record(token,'GetConversion'+category+'Logger','Returns LogManager.GetLogger using the calling assembly and literal category Knx.Ets.CvNext.'+category+'.')

    for type_token,type_name,get_manager,get_culture,set_culture,manager_field,culture_field,base_name,entries in [
        (0x02000006,'ConversionDiagnosticResources',0x0600000C,0x0600000D,0x0600000E,0x04000007,0x04000008,'Class160',[
            (0x0600000F,'ContextHelpFileAttributeRemoved'),(0x06000010,'FailedToRemoveEmptyCollection'),
            (0x06000011,'HelpFileAttributeRemoved'),(0x06000012,'HelpFileTranslationRemoved'),
            (0x06000013,'MissingRequiredData'),(0x06000014,'MissingRequiredId')]),
        (0x02000011,'ConversionExceptionResources',0x0600004D,0x0600004E,0x0600004F,0x0400005F,0x04000060,'Class162',[
            (0x06000050,'GenericError'),(0x06000051,'InvalidPassword'),(0x06000052,'KnxMasterDataMissing'),
            (0x06000053,'LegacyConversionFailed'),(0x06000054,'NonReleasedToolVersionUsed'),(0x06000055,'OutdatedMasterData'),
            (0x06000056,'SchemaUpdateNotAllowedNoValidDirectorySignature'),(0x06000057,'TooManyErrors'),
            (0x06000058,'TooManyWarnings'),(0x06000059,'UnknownFileExtension'),(0x0600005A,'UnsupportedSchemaVersion'),
            (0x0600005B,'ValidationFailed')])]:
        group='Diagnostic' if base_name=='Class160' else 'Exception'
        record(type_token,type_name,'Strongly typed resource wrapper for '+base_name+'; the resource lookup base name remains unchanged.')
        record(get_manager,'GetConversion'+group+'ResourceManager','Lazily constructs ResourceManager with unchanged literal base name '+base_name+' and the declaring assembly.')
        record(get_culture,'GetConversion'+group+'ResourceCulture','Returns the optional resource culture override; null allows normal ResourceManager culture fallback.')
        record(set_culture,'SetConversion'+group+'ResourceCulture','Sets the culture override passed to every resource lookup in this wrapper.',('resourceCulture',))
        record(manager_field,'resourceManager','Cached ResourceManager initialized by the reviewed wrapper factory.')
        record(culture_field,'resourceCultureOverride','Optional CultureInfo passed to GetString; preserve null and language fallback behavior.')
        for token,key in entries:
            record(token,'GetConversion'+key+'Message','Reads literal resource key '+key+' with the wrapper culture override. Text, key and formatting remain unchanged.')

    record(0x02000004,'ConversionDiagnostic','Abstract description-bearing base for conversion errors and nonfatal notices.')
    record(0x02000003,'ConversionError','Diagnostic created with Error logging; the dispatcher success predicate rejects this type.')
    record(0x02000005,'ConversionNotice','Nonfatal diagnostic used when invalid help references/translations are removed; factory logs at Info, not Warn.')
    record(0x06000005,'LogAndCreateConversionError','Logs the supplied description with ILog.Error then constructs the error diagnostic.',('description','logger'))
    record(0x0600000A,'LogAndCreateConversionNotice','Logs at ILog.Info then constructs the notice; inspected consumers report removed help attributes and translations.',('description','logger'))
    record(0x06000006,'DecodeAndInternConversionErrorString','XORs each character byte with an incrementing offset-derived key, recombines the bytes and interns the decoded string; never executed during review.',('encodedText','keyOffset'),{
        'array':'decodedCharacters','num':'keyByteCounter','num2':'characterIndex','num3':'currentCharacterIndex',
        'num4':'outputCharacterIndex','array2':'outputCharacters','num5':'targetCharacterIndex','c':'encodedCharacter',
        'b':'firstDecodedByte','b2':'secondDecodedByte','b3':'byteSwapTemporary'})
    for token,reason,params in [(0x06000004,'Passes error description to ConversionDiagnostic.',('description',)),
                                (0x06000007,'Stores the supplied diagnostic Description.',('description',)),
                                (0x06000009,'Passes nonfatal notice description to ConversionDiagnostic.',('description',))]:
        record(token,None,reason,params,status='retain-method-name')

    record(0x02000007,'SchemaConversionResult','Carries success, converted ID mappings, errors and notices. Directory conversion tests success; legacy conversion composes its ID mappings.')
    for token,name,reason in [(0x06000016,'IsConversionSuccessful','Returns the stored success flag.'),
                             (0x06000018,'GetConvertedIdMappings','Returns the old-to-new ID dictionary produced by conversion signing and combined with legacy ID maps.'),
                             (0x06000019,'GetConversionErrors','Returns the ConversionError list supplied from OfType<ant> diagnostics.'),
                             (0x0600001A,'GetConversionNotices','Returns the ConversionNotice list supplied from OfType<anu> diagnostics.')]:record(token,name,reason)
    record(0x06000017,'SetConversionSuccessful','Stores the result success flag; used by construction and result combination.',('succeeded',))
    record(0x0600001B,'CombineConversionResult','ANDs success, keeps existing values for duplicate ID keys, and appends errors/notices; used to aggregate device-template subcontainer conversions.',('otherResult',),{
        'flag':'combinedSuccess','keyValuePair':'idMapping','enumerator2':'errorEnumerator','ant':'conversionError',
        'enumerator3':'noticeEnumerator','anu':'conversionNotice'})
    record(0x06000015,None,'Initializes success and supplies empty collections when ID mappings or diagnostic lists are null.',
           ('succeeded','convertedIdMappings','conversionErrors','conversionNotices'),
           {'dictionary':'idMappingsOrEmpty','list':'errorsOrEmpty'},status='retain-method-name')
    for token,name,reason in [(0x0400000A,'succeeded','Flag combined with logical AND across conversion results.'),
                             (0x0400000B,'convertedIdMappings','Old-to-new converted IDs; first value wins when combining duplicate keys.'),
                             (0x0400000C,'conversionErrors','Diagnostics that cause conversion failure.'),
                             (0x0400000D,'conversionNotices','Nonfatal diagnostics such as removed obsolete help references.')]:record(token,name,reason)

    # The reader returns the FIRST encountered schema version. It validates
    # supported namespaces, but does not enforce identical versions in all files.
    record(0x02000010,'ConversionInputValidator','Validates signatures of immediate input directories and reads supported XML namespaces before conversion.')
    record(0x0400005D,'inputDirectory','Constructor-supplied conversion input directory used for signature and namespace checks.')
    record(0x06000048,None,'Captures the directory to validate before conversion.',('inputDirectory',),status='retain-method-name')
    record(0x0600004A,'ValidateConversionInputDirectorySignatures','Checks each immediate child with CheckDirectorySignature; accepts valid normal/project signatures and otherwise throws the existing schema-update exception.',locals_={
        'directoryInfo':'childDirectory','signatureState':'directorySignatureState'})
    record(0x0600004B,'ReadFirstSchemaVersionAndValidateNamespaces','Enumerates conversion documents, records the first KNX namespace schema, rejects unsupported namespaces, and fails if no version is found; does not require all namespaces to be equal.',locals_={
        'knxXmlSchemaVersion':'firstSchemaVersion','aom':'inputContainer','enumerator':'documentEnumerator','aop':'document',
        'xmlReader':'documentReader','namespaceURI':'documentNamespace'})
    record(0x06000049,'ValidateConversionInputAndReadSchemaVersion','Calls child-directory signature validation then namespace validation/version reading.')
    record(0x06000029,'ExtractAndValidateProjectContainer','ExtractProjectContainerWithKeys writes to the temporary directory, then validates input; maps missing/invalid password to InvalidPassword and other failures to TooManyErrors. Directory containers still throw NotImplementedException.',
           ('inputFilePath','keyProviders','extractionDirectory'),{'aqy':'projectExtractor','result':'extractionResult'})
    record(0x0600002A,'ExtractAndValidateDeviceTemplateContainer','Extracts device templates, appends returned directories and validates each directory before conversion.',
           ('inputFilePath','extractedTemplateDirectories','extractionDirectory'),{'result':'extractionResult','text':'templateDirectoryPath'})
    record(0x0400024C,'LegacyConversionFailed','GetLocalizedMessageFromReason selects the LegacyConversionFailed resource for this exact enum value.')
    record(0x0400024D,'DeviceTemplateExtractionFailed','Thrown by ExtractAndValidateDeviceTemplateContainer when ExtractDeviceTemplateContainer reports failure; existing localized fallback remains generic.')

    # These original fields have storage metadata but no established behavioral
    # role. Keep them unresolved rather than assigning misleading dummy names.
    return [{'Component':'CvNext conversion diagnostics and input validation',
             'Symbols':['m0046:'+f'0x{token:08X}' for token in [0x04000003,0x04000005,0x04000006,0x04000009,0x0400000E,0x0400005E,0x04000061]],
             'Reason':'Unreferenced string fields carry dnSpy metadata.field-data storage contracts; no meaningful role is established. Preserve until original metadata/storage restoration is reviewed.'},
            {'Component':'CvNext conversion orchestration',
             'Reason':'Result, diagnostic/resource and input-validation leaves are reviewed. Dispatcher, conversion graph, document interfaces, validator contract and signing internals still need complete family/caller review before the remaining orchestration names.'}]
