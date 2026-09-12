"""Product-store factories, cache tracking and manufacturer integrity chains."""

def review(add):
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add('Knx.Ets.ObjectModel',token,name,reason,parameters,locals_,status)
    def retain(token,reason,names): record(token,None,reason,locals_=names,status='retain-method-name')

    # Cache stores and metadata factories; identical selector bodies get names
    # from their separate COC/PC/CPC callers, not from token order.
    record(0x06005D48,'IsRegistrationOrderMetadata','Tests whether the metadata key contains RegistrationOrder.',('metadataEntry',))
    record(0x06005D47,'HasOnlyRegistrationOrderMetadata','Requires All metadata keys to contain RegistrationOrder; an empty dictionary also satisfies this predicate.',('storeFactory',),{'keyValuePair_0':'metadataEntry'})
    for token,name in [(0x06005D49,'IsComObjectCacheReferenceObsolete'),(0x06005D4B,'IsParameterCacheReferenceObsolete'),(0x06005D4D,'IsCalculatedParameterCacheReferenceObsolete')]:
        record(token,name,'The corresponding GetAll cache caller removes entries when the weak reference is dead or the target store now exists on disk.',('cacheReference',))
    for token,name in [(0x06005D4A,'GetComObjectCacheReferenceTarget'),(0x06005D4C,'GetParameterCacheReferenceTarget'),(0x06005D4E,'GetCalculatedParameterCacheReferenceTarget')]:
        record(token,name,'Returns the weak-reference Target as ICacheStreamStore after the matching cache-list cleanup.',('cacheReference',))
    record(0x06005D4F,'IsConsistencyHashSidecar','Tests the filename suffix .ets5hash; DeleteAllCaches checks whether all remaining top-level files are sidecars.',('hashFile',))
    record(0x06005D55,'HasResolvedHashFilePath','Tests non-null/nonempty path before the manufacturer master-hash text is read.',('filePath',))
    record(0x06005D54,'ResolveCurrentConsistencyHashPath','Uses TransactionalFileStreamManager.Exists to prefer the current transaction file when present.',('hashFile',))
    record(0x06005D51,'CreateApplicationProgramIdFromDirectory','Creates an ApplicationProgramId from a directory name in the manufacturer program listing.',('applicationDirectory',))
    record(0x06005D52,'CreateManufacturerIdFromDirectory','Creates a ManufacturerId from a directory name in Manufacturers.',('manufacturerDirectory',))
    record(0x06005D53,'CreateShapeApplicationProgramId','Creates an ApplicationProgramId from each directory selected by GetShapes.',('shapeDirectory',))
    record(0x06005D73,'IsApplicationDirectoryForManufacturer','Matches the captured manufacturer directory name followed by _A- against the child directory name.',('applicationDirectory',))
    record(0x06005D50,'ListApplicationIdsInManufacturerDirectory','Enumerates child directories matching the captured manufacturer prefix and converts their names to ApplicationProgramId values.',('manufacturerDirectory',),{'local_5':'directoryFilter','dirInfo':'applicationDirectory'})
    record(0x02000D1A,'ManufacturerApplicationDirectoryFilter','Captures the manufacturer directory for the _A- child directory predicate.')
    record(0x04002BAD,'manufacturerDirectory','Directory captured for matching its manufacturer prefix in child application directories.')
    record(0x02000D0E,'ProductStoreDelegateCache','Owns stateless factory, weak-cache, path and directory selectors and their cached delegates.')

    for token,name,code,caller in [
        (0x06005D3B,'CreateCatalogStoreInDirectory','C','Catalog'),
        (0x06005D3C,'CreateHardwareStoreInDirectory','H','Hardware'),
        (0x06005D3D,'CreateBaggageIndexStoreInDirectory','B','Baggages'),
        (0x06005D3E,'CreateApplicationProgramStoreInDirectory','A','ApplicationProgram'),
        (0x06005D3F,'CreateApplicationTranslationStoreInDirectory','AT','ApplicationProgramTranslation'),
        (0x06005D40,'CreateDynamicTranslationStoreInDirectory','ADT','ApplicationProgramDynamicTranslation'),
        (0x06005D41,'CreateCatalogTranslationStoreInDirectory','CT','CatalogTranslation'),
        (0x06005D42,'CreateHardwareTranslationStoreInDirectory','HT','HardwareTranslation')]:
        record(token,name,f'Invokes StoreCreator for file code {code}; its concrete caller is {caller}.',('storeDirectory',))
    record(0x06005D2D,'InvokeWithManufacturerDirectory','Combines store root with the long manufacturer ID and invokes the supplied factory/query with that DirectoryInfo.',('manufacturerId','useDirectory'),{'text':'manufacturerDirectoryName'})
    record(0x06005D2C,'InvokeWithApplicationProgramDirectory','Uses the manufacturer-directory helper, appends the long application-program ID and invokes the supplied factory/query.',('applicationProgramId','useDirectory'),{'info':'manufacturerDirectory'})
    record(0x06005D2E,'InvokeWithBaggageDirectory','Combines store root, long manufacturer ID and Baggages before invoking the supplied stream factory.',('manufacturerId','useDirectory'),{'text':'manufacturerDirectoryName'})
    record(0x06005D13,'TryDeleteProductStoreFile','Calls FileInfo.Delete and silently swallows any exception; shared by cache and version-file cleanup.',('file',))
    record(0x06005D12,'DeleteMatchingCacheFilesAndHashes','Enumerates the cache pattern and its .ets5hash companion pattern using the requested search depth, then attempts deletion of each.',('manufacturerDirectory','cacheFilePattern','includeSubdirectories'))

    # Master hashes sum the UTF-8 bytes of existing hash texts. This is not a
    # new cryptographic hash algorithm; preserve the vendor's MasterHash role.
    record(0x06005D2F,'GetManufacturerMasterHashFileName','Formats manufacturer ID followed by -Master.ets5hash.',('manufacturerId',))
    record(0x06005D31,'IsDuplicateTransactionHashFile','Recognizes a $-prefixed file whose unprefixed counterpart already occurs in the enumerated path dictionary.',('hashFile','knownHashFiles'),{'text':'originalHashPath'})
    record(0x06005D30,'ComputeManufacturerMasterHash','Finds the manufacturer directory, excludes master/duplicate temporary hash files, resolves current transaction paths, sums UTF-8 bytes of their text into uint, and returns Base64 of its bytes; absent directory returns null.',('manufacturerId',),{
        'directoryInfo':'manufacturerDirectory','directoryInfo_0':'candidateDirectory','array':'hashFiles','fileNames':'knownHashFiles',
        'fileInfo':'hashFile','fileInfo_0':'hashFile','num':'hashTextByteSum','enumerable':'currentHashPaths','func':'hasResolvedPath',
        'enumerator':'hashPathEnumerator','text':'hashFileText','b':'hashTextByte','fileName':'hashPath'})
    record(0x06005D32,'ReadManufacturerMasterHash','Reads the current master-hash file as UTF-8; absent manufacturer returns null and absent file returns Base64 of a zero int.',('manufacturerId',),{'directoryInfo':'manufacturerDirectory','directoryInfo_0':'candidateDirectory','text':'masterHashPath'})
    record(0x06005D37,'CopyStoreHmacCharacterBytes','Allocates two bytes per input character and BlockCopy copies the char array for manufacturer HMAC key/message construction.',('text',),{'array':'characterBytes'})
    record(0x06005D36,'ComputeManufacturerStoreHmac','Uses installer GUID character bytes as HMACSHA256 key and repeated manufacturer ID separated by a colon as message; encodes the result as Base64.',('installerGuid','manufacturerId'))
    record(0x06005D35,'GetManufacturerStoreHmacPath','Combines the root directory with manufacturer ID plus .store.',('manufacturerId',))
    record(0x06005D38,'ReadManufacturerHmacFileOrEmpty','Reads an existing supplied HMAC file, otherwise returns empty text.',('hmacFilePath',))

    for token,name,reason in [
        (0x04002B79,'BaggageFileNamePrefix','Literal B prefixed to individual baggage filenames.'),
        (0x04002B7A,'ProductConsistencyHashExtension','Literal .ets5hash used by product cache cleanup and master-hash aggregation.'),
        (0x04002B7B,'rootDirectory','Transactional root directory for manufacturers and storeVersion.'),
        (0x04002B7C,'storeCreator','Selected object-store factory exposed by StoreCreator.'),
        (0x04002B7D,'streamStoreCreator','Constructor stream factory exposed by StreamStoreCreator.'),
        (0x04002B7E,'cacheStreamStoreCreator','Constructor cache factory used with manufacturer IDs and cache file codes.'),
        (0x04002B7F,'unpersistedParameterCacheReferences','Weak references to parameter caches whose files were absent when requested; removed when dead or persisted.'),
        (0x04002B80,'unpersistedCalculatedParameterCacheReferences','Same weak tracking for calculated-parameter cache stores.'),
        (0x04002B81,'unpersistedComObjectCacheReferences','Same weak tracking for communication-object cache stores.'),
        (0x04002B82,'cacheReferenceLock','Protects all three weak-reference lists during additions, cleanup and result merging.'),
        (0x04002B83,'storeVersionFileName','Literal storeVersion returned by VersionInfoFileName.')]: record(token,name,reason)
    for token,name in [
        (0x04002B84,'sharedCallbacks'),(0x04002B85,'isRegistrationOrderMetadata'),(0x04002B86,'hasOnlyRegistrationOrderMetadata'),
        (0x04002B87,'isComObjectCacheReferenceObsolete'),(0x04002B88,'getComObjectCacheReferenceTarget'),
        (0x04002B89,'isParameterCacheReferenceObsolete'),(0x04002B8A,'getParameterCacheReferenceTarget'),
        (0x04002B8B,'isCalculatedParameterCacheReferenceObsolete'),(0x04002B8C,'getCalculatedParameterCacheReferenceTarget'),
        (0x04002B8D,'isConsistencyHashSidecar'),(0x04002B8E,'createApplicationProgramIdFromDirectory'),
        (0x04002B8F,'listApplicationIdsInManufacturerDirectory'),(0x04002B90,'createManufacturerIdFromDirectory'),
        (0x04002B91,'createShapeApplicationProgramId'),(0x04002B92,'resolveCurrentConsistencyHashPath'),(0x04002B93,'hasResolvedHashFilePath')]:
        record(token,name,'Singleton/cached delegate in ProductStoreDelegateCache, paired with the corresponding reviewed method and concrete caller.')

    retain(0x06005D01,'Retain FileProductStore constructor; distinguish new/empty store initialization and the selected metadata-only factory.',{'flag':'needsInitialStoreVersion','meta':'storeFactory','keyValuePair_0':'metadataEntry'})
    for token,cache in [(0x06005D04,'comObjectCache'),(0x06005D09,'parameterCache'),(0x06005D0B,'calculatedParameterCache')]:
        retain(token,'Retain the public cache getter; track an unpersisted cache by weak reference under the shared lock.',{'cacheStreamStore':cache,'obj':'cacheLock','info':'applicationDirectory'})
    for token,local,cache in [(0x06005D05,'local_1','comObjectCaches'),(0x06005D0A,'local_2','parameterCaches'),(0x06005D0C,'local_3','calculatedParameterCaches')]:
        retain(token,'Retain the bulk cache getter; combine disk-backed stores with surviving unpersisted weak targets after cleanup.',{
            local:'createCacheFromFile','list':cache,'directoryInfo_0':'manufacturerDirectory','file':'cacheFile','obj':'cacheLock','_':'cacheReference'})
    retain(0x06005D0E,'Retain DeleteApplicationProgram; preserve duplicate-directory warning and deletion behavior, including the existing First call when count is not one.',{'directories':'applicationDirectories','array':'directoriesToDelete','i':'directoryIndex'})
    retain(0x06005D0F,'Retain DeleteAllCachesForManufacturer; delete only for one matching directory and log if multiple are found.',{'directories':'manufacturerDirectories'})
    retain(0x06005D1D,'Retain Baggage; append target path and the B-prefixed filename under the manufacturer baggage directory.',{'info':'baggageRootDirectory','directoryInfo':'baggageTargetDirectory'})
    retain(0x06005D1F,'Retain ApplicationPrograms; the inlined query shares terminology with its explicit helper.',{'info':'manufacturerDirectory','local_4':'directoryFilter','dirInfo':'applicationDirectory'})
    retain(0x06005D20,'Retain Manufacturers accessor; M-???? directory names establish manufacturer IDs.',{'directoryInfo_0':'manufacturerDirectory'})
    retain(0x06005D24,'Retain GetShapes; select application directories by ID without fingerprint/original manufacturer and preserve the original-ID fallback.',{'directoryInfo':'manufacturerDirectory','list':'matchingShapeIds','directoryInfo_0':'applicationDirectory'})
    retain(0x06005D25,'Retain SchemaVersion accessor; default to Version12 and use the shared version reader when present.',{'b':'schemaVersionByte','streamReader':'storeVersionReader','text':'toolVersion'})
    retain(0x06005D26,'Retain ToolVersion accessor; preserve the default version string and optional file read.',{'toolVersionIfNoVersionInfoExists':'toolVersion','streamReader':'storeVersionReader'})
    retain(0x06005D27,'Retain CreateInfo; write current schema and tool version.',{'streamWriter':'storeVersionWriter'})
    retain(0x06005D28,'Retain transactional version update; keep the hash-disabled and single-write flags.',{'transactionalFileStream':'storeVersionStream','streamWriter':'storeVersionWriter'})
    retain(0x06005D2A,'Retain ReadVersionInfo; read schema byte followed by tool text, logging errors while retaining fallback state.',{'b':'schemaVersionByte','b2':'parsedSchemaVersion','ex':'versionReadException'})
    retain(0x06005D33,'Retain CreateMasterHash; calculate then write the hash text through a hash-disabled transaction stream.',{'text':'masterHash','directoryInfo':'manufacturerDirectory','directoryInfo_0':'candidateDirectory','transactionalFileStream':'masterHashStream','bytes':'encodedMasterHash'})
    retain(0x06005D34,'Retain CheckMasterHash; mismatch throws or deletes the manufacturer store according to the existing flag.',{'text':'computedMasterHash','text2':'storedMasterHash','directoryInfo':'manufacturerDirectory','directoryInfo_0':'candidateDirectory'})
    retain(0x06005D39,'Retain CheckStoreHmac; compare expected and stored HMAC for every manufacturer and combine results without early exit.',{'flag':'allManufacturerHmacsMatch','enumerator':'manufacturerEnumerator','text':'expectedHmac','text2':'storedHmac'})
