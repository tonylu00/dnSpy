"""Reviewed ETS 6.3 storage helpers, from file operations to project callers.

Only names are proposed. Hash algorithms, copy markers, error handling and
restore-point rollback behavior are recorded as observed, without repairs.
"""

def review(add):
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add('Knx.Ets.ObjectModel',token,name,reason,parameters,locals_,status)
    def retain(token,reason,names):
        record(token,None,reason,locals_=names,status='retain-method-name')

    # Installation GUID persistence is the leaf of both new-store and clone HMAC
    # creation. BlockCopy describes the actual character-byte representation.
    record(0x06005E56,'CopyStringCharacterBytes','Allocates two bytes per character and Buffer.BlockCopy copies the char array; used for the HMAC key and store-ID message.',('text',),{'array':'characterBytes'})
    record(0x06005E54,'CreateAndWriteInstallerGuid','Creates a new Guid, writes its text as UTF-8 at the supplied path, and returns it.',('installerGuidPath',),{'guid':'installerGuid'})
    record(0x06005E53,'EnsureInstallerDataDirectory','Creates the configured root directory when absent and returns its DirectoryInfo.')
    record(0x06005E50,'ReplaceStoreHmacFile','Deletes any existing file then writes the supplied HMAC text as UTF-8; this is not an atomic replace.',('hmacFilePath','hmacText'))
    record(0x06005E52,'LoadOrCreateInstallerGuid','Ensures the directory, reads and parses installer.guid, or recreates it when missing or unreadable; returns normalized Guid text.',locals_={'text':'installerGuidPath','text2':'storedGuidText','guid':'installerGuid'})
    record(0x04002BE7,'installerDataDirectory','Constructor root directory used for installer.guid storage.')
    retain(0x06005E4D,'Retain ApplyStoreHmac; the implicit-installer overload loads or creates installer.guid before writing the store HMAC.',{'text':'installerGuid','text2':'storeHmac','text3':'hmacFilePath'})
    retain(0x06005E4E,'Retain ApplyStoreHmac; explicit installer GUID is used to calculate the store HMAC.',{'text':'storeHmac','text2':'hmacFilePath'})
    retain(0x06005E51,'Retain InstallerGuid accessor; it ensures the directory but returns empty and logs if installer.guid is absent, unlike LoadOrCreateInstallerGuid.',{'text':'installerGuidPath'})

    # File hash naming follows SHA1 -> byte transform -> mask -> Base64, and the
    # matching reader. The return from Seek is zero, not the old stream position.
    record(0x06005DD3,'GetConsistencyHashFilePath','Appends the initialized .ets5hash extension, removing a leading $ from transactional data filenames.',locals_={'fileName':'dataFileName','text':'hashFilePath'})
    record(0x06005DD5,'ComputeMaskedConsistencyHashBase64','Seeks to the beginning, hashes with the shared SHA1 provider, adds 41 modulo 256, XORs alternating mask bytes and encodes Base64. The later Seek uses the first Seek result (zero), not the original position.',('dataStream','integrityMask'),{
        'num':'hashStartPosition','sha1CryptoServiceProvider':'hashProviderLock','array':'hashBytes',
        'i':'hashByteIndex','array2':'incrementedHashBytes','num2':'incrementedByteIndex',
        'array3':'wrappedHashBytes','num3':'wrappedByteIndex','array4':'maskBytes',
        'j':'maskedByteIndex','num4':'maskByteIndex'})
    for token,name,reason in [
        (0x04002BD1,'dataFilePath','Constructor filename; source of the transactional consistency-hash path.'),
        (0x04002BD2,'dataStream','RetryableFileStream underlying all Stream operations; closed after hash persistence.'),
        (0x04002BD3,'sharedSha1Provider','Shared SHA1 provider; locked around ComputeHash in writing and checking.'),
        (0x04002BD4,'consistencyHashExtension','Initially a dot, lazily expanded to .ets5hash before path operations.'),
        (0x04002BD5,'integrityMask','Constructor mask applied to alternating consistency-hash bytes.')]: record(token,name,reason)
    retain(0x06005DD2,'Retain HashedFileStream constructor; initialization flag indicates that the hash suffix has not yet been expanded.',{'flag':'needsHashExtensionInitialization'})
    retain(0x06005DD4,'Retain Check; names distinguish stored hash, transformed computed hash and allowed files without hash sidecars. Validation and all exceptions remain unchanged.',{
        'text':'storedHashBase64','array':'storedHashBytes','ex':'invalidHashEncodingException','fileStream':'dataStream',
        'sha1CryptoServiceProvider':'hashProviderLock','array2':'computedHashBytes','i':'hashByteIndex',
        'array3':'incrementedHashBytes','num':'incrementedByteIndex','array4':'wrappedHashBytes','num2':'wrappedByteIndex',
        'array5':'maskBytes','j':'maskedByteIndex','num3':'maskByteIndex','file':'dataFileName',
        'array6':'hashExemptFileNames','array7':'hashExemptExtensions','string_0':'hashExemption'})
    retain(0x06005DD6,'Retain HashFile; distinguish source data and the UTF-8 Base64 sidecar streams.',{'fileStream':'dataStream','fileStream2':'hashFileStream','bytes':'encodedHashBytes'})
    retain(0x06005DD9,'Retain Close; flush data, write its consistency hash transactionally, then dispose and clear the underlying stream.',{'transactionalFileStream':'hashFileStream','bytes':'encodedHashBytes'})
    retain(0x06005DE4,'Retain DeleteHashFile; suffix initialization is separate from existence checking.',{'flag':'needsHashExtensionInitialization'})

    record(0x06005DCD,'OpenStoreReadOrTransactionStream','Writable requests create TransactionalFileStream with the multi-write flag. Reads resolve the current transaction path, check hashes only for non-copy/non-$ files when enabled, or return VoidStream when absent.',('readOnly','allowMultipleWritesInTransaction'),{'text':'currentDataFilePath'})
    record(0x04002BCE,'checkIntegrityOnRead','Constructor check flag used before HashedFileStream.Check; copied/transactional temporary files have separate conditions.')
    record(0x04002BCD,'originalFileInfo','Constructor file identity returned by OriginalFileInfo; FileInfo may instead resolve to the active transaction path.')
    record(0x04002BCF,'integrityMask','Mask setter storage, supplied to HashedFileStream.Check and TransactionalFileStream; MaxValue also activates CopyActive.')
    retain(0x06005DC4,'Retain FileInfo accessor; resolve an active transactional path or return the original FileInfo.',{'text':'currentDataFilePath'})

    # These leaf selectors and copy-state setters are used by every file-backed
    # project view. MaxValue sets FileStreamStore.CopyActive before real mask.
    record(0x06005D82,'EnsureProjectStoreDirectory','Creates and refreshes a missing supplied directory, returning the same instance.',('directory',))
    record(0x06005D89,'ApplyProjectMaskToStreamStore','If copy state was marked, assign MaxValue first to activate FileStreamStore.CopyActive; then assign the actual mask and return the stream store.',('streamStore',))
    record(0x06005D8A,'ApplyProjectMaskToObjectStore','Same copy marker and actual mask assignments through IStreamStore, preserving the IStore return type.',('objectStore',))
    record(0x06005DB2,'CreateUserFileIdFromStoredFile','Uses this project ID and removes the leading U prefix from the stored filename.',('storedFile',))
    record(0x06005DB3,'CreateAddinDataIdFromStoredFile','Uses project ID, parent directory name as add-in ID and the complete filename as data name.',('storedFile',))
    record(0x06005DAB,'GetProjectIntegrityFiles','Collects top-level *.-matching project files and adds project.jpg if it exists; caller excludes storeversion before hash checks.',locals_={'list':'integrityFiles','fileInfo':'projectImageFile'})
    record(0x06005DB4,'CheckProjectFileConsistencyHashes','Enumerates GetProjectIntegrityFiles, skips storeversion case-insensitively, and calls HashedFileStream.Check with the project mask.',locals_={'enumerator':'integrityFileEnumerator','fileInfo':'integrityFile'})
    record(0x06005DAE,'GetCurrentProjectHmacFilePath','Combines the project root directory with its project ID plus .store.')
    record(0x06005DAF,'ReadStoreHmacOrEmpty','Reads the supplied file when it exists; otherwise returns empty text. CheckStoreHmac supplies the .store path.',('hmacFilePath',))
    record(0x06005DB1,'InitializeLegacyProjectStoreHmac','Only when the store HMAC is absent: inspect the first manufacturer directory/version file, retain absence for a parsed version >=3, otherwise ApplyStoreHmac.',('installerGuid',),{
        'directories':'manufacturerDirectories','directoryInfo':'firstManufacturerDirectory','fileInfo':'manufacturerVersionFile',
        'text':'manufacturerVersionText','num':'manufacturerStoreVersion'})
    for token,name,reason in [
        (0x04002BB7,'ConsistencyHashExtension','Literal .ets5hash excluded from data-file enumeration.'),
        (0x04002BB8,'UserFileNamePrefix','Literal U prepended to stored user-file names and removed by the ID selector.'),
        (0x04002BB9,'MinimumManufacturerStoreVersionRequiringHmac','Literal 3; versions at least this value do not receive a missing-HMAC legacy fallback.'),
        (0x04002BBA,'projectStoreFactories','Metadata-bearing store constructors; Areas selects the factory whose Type metadata is Areas, and Clone preserves the collection.'),
        (0x04002BBB,'installationGuidWriter','Constructor service creates, reads and verifies installer/store HMAC information.'),
        (0x04002BBC,'projectDirectory','Created project root holding object stores and project.jpg.'),
        (0x04002BBD,'binaryDataDirectory','Created BinaryData subdirectory used for device binary .dat files.'),
        (0x04002BBE,'addinDataDirectory','Created AddinData subdirectory; add-in IDs form its child directories.'),
        (0x04002BBF,'userFilesDirectory','Created UserFiles subdirectory used for U-prefixed user files.'),
        (0x04002BC0,'projectMask','Computed from ProjectGuid and project ID, returned by Mask and assigned to each project stream/object store.'),
        (0x04002BC2,'isProjectCopy','Set when ProjectGuid receives Guid.Empty, including Clone; causes the MaxValue mask marker that activates CopyActive in FileStreamStore.')]: record(token,name,reason)
    retain(0x06005D86,'Retain GetProjectMaskFromGuid; sum Guid bytes and UTF-8 bytes of the long project ID into a ushort.',{'num':'projectMask','b':'guidByte','b2':'projectIdByte'})
    retain(0x06005D95,'Retain Areas accessor; select the factory registered with Type=Areas.',{'meta2':'areaStoreFactory','meta':'storeFactory'})
    retain(0x06005D96,'Retain AllAreas accessor; exclude hash sidecars and construct AreaId values.',{'fileInfo_0':'areaFile','info':'areaFile'})
    retain(0x06005D97,'Retain AllUserFiles accessor; exclude hash sidecars before the reviewed ID selector.',{'fileInfo_0':'userFile'})
    retain(0x06005D98,'Retain AllDeviceBinaryData accessor; filename without .dat becomes GuidId when parseable, otherwise DeviceBinaryDataId.',{'fileInfo_0':'binaryDataFile','info':'binaryDataFile','text':'binaryDataIdText','guid':'parsedBinaryDataGuid'})
    retain(0x06005D99,'Retain AllAddInData accessor; recursively enumerate .dat files before the reviewed ID selector.',{'fileInfo_0':'addinDataFile'})
    retain(0x06005D9C,'Retain Area; create a missing area file before opening its masked store.',{'fileInfo':'areaFile'})
    retain(0x06005DA7,'Retain Clone; transactionally copy and patch IDs, mark copied-store state, assign a new project GUID and apply its HMAC.',{'projectStore':'clonedStore','transactionScope':'cloneTransaction','projectIdPatcher':'idPatcher','transactionalDirectoryInfo':'cloneDirectory','fileProjectStore2':'clonedFileStore'})
    retain(0x06005DA9,'Retain LoadName; read ProjectInformation Name from the P file, preserving the dash fallback.',{'text':'projectName','fileStream':'projectFileStream','xmlReader':'projectReader'})
    retain(0x06005DB0,'Retain CheckStoreHmac; initialize only eligible legacy stores, then compare stored and expected HMAC text.',{'text':'expectedStoreHmac'})
    for token,name,reason in [
        (0x04002A65,'oldProjectIdText','Long-form old project ID matched at the beginning of strings in Patch.'),
        (0x04002A66,'newProjectIdText','Long-form replacement project ID prepended to the unmodified suffix.'),
        (0x04002A67,'projectIdsMatch','Invariant-culture case-insensitive equality result; bypasses replacement when IDs already match.')]: record(token,name,reason)

    # Data-store startup and restore callers use the same version-file helpers.
    record(0x06005CDC,'OpenStoreVersionReaderIfPresent','Combines the supplied store directory with storeVersion and opens a StreamReader if the existing repeated existence check succeeds.',('storeDirectoryPath',),{'text':'storeVersionPath'})
    record(0x06005CDA,'ReadStoredProjectSchemaVersion','Reads and parses the first storeVersion line as a KNX schema version; absent file returns null, parse/read errors log and rethrow.',('storeDirectoryPath',),{'streamReader':'storeVersionReader','knxXmlSchemaVersion':'schemaVersion','ex':'versionReadException'})
    record(0x06005CDB,'ReadStoredProjectToolVersion','Reads the second storeVersion line after skipping schema version; absent file and read errors return null, with errors logged.',('storeDirectoryPath',),{'streamReader':'storeVersionReader','text':'toolVersion','ex':'versionReadException'})
    record(0x06005CD5,'GetProjectStoreHmacPath','Combines data-store root, long project ID directory, and project ID plus .store; supplied to the new-store HMAC writer.',('projectId',))
    record(0x06005CE1,'OpenProjectStoreDirectory','Invokes the constructor-supplied project store factory for each enumerated P-???? directory.',('projectDirectory',))
    record(0x06005CE2,'MoveUnsupportedProjectStoreToBackup','Reads stored schema version; if it differs from current and is below 21, moves the directory to a schema-version-prefixed sibling and logs the backup.',('projectDirectory',),{
        'knxXmlSchemaVersion':'storedSchemaVersion','knxXmlSchemaVersion2':'versionToCompare','knxXmlSchemaVersion3':'currentSchemaVersion','text':'backupDirectoryName'})
    record(0x06005CE0,'CleanDataStoreAtStartup','Deletes root *.tmp files and invokes the unsupported-store backup helper for P-???? directories. The outer catch logs and swallows failures.',locals_={'file':'temporaryFile','ex':'cleanupException'})
    for token,name,reason in [
        (0x04002B66,'RestorePointExtension','Literal .restorepoint used by backup creation and lookup.'),
        (0x04002B67,'dataStoreDirectory','Constructor root for project directories, restore-point files and cleanup.'),
        (0x04002B68,'createProjectStore','Constructor factory used by new-project creation and existing-directory enumeration.'),
        (0x04002B69,'installationGuidWriter','Writes the HMAC for a newly created project store.'),
        (0x02000D07,'RestorePointFailureContext','Captures the restore exception for a deferred error-message expression.'),
        (0x04002B70,'restoreException','Exception stored in RestorePointFailureContext and accessed by the deferred Message expression; original runtime metadata name remains required by its reflection string.')]: record(token,name,reason)
    retain(0x06005CD4,'Retain Create; reject duplicate IDs, create a transactional project directory and apply its store HMAC.',{'store':'existingStore','directory':'projectDirectory'})
    retain(0x06005CD7,'Retain CreateRestorePoint; execute its operation only after successful validation.',{'createRestorePointOperation':'restorePointOperation'})
    retain(0x06005CD8,'Retain GetRestorePoints; parse UTC filename timestamps, log invalid entries and order newest first.',{'list':'restorePointFiles','result':'restorePoints','fileInfo_0':'restorePointFile','ex':'restorePointInfoException','projectRestorePointInfo_0':'restorePoint'})
    retain(0x06005CD9,'Retain RestoreRestorePoint; move the current directory aside, extract the selected archive, read the previous tool version and roll back on failure. Existing final cleanup and reflected error-message behavior remain unchanged.',{
        'text':'previousProjectDirectory','text2':'restoredProjectDirectory','flag':'previousProjectWasMoved','text3':'previousToolVersion',
        'zipWrapper':'restorePointArchive','enumerator':'archiveEntryEnumerator','zipEntry':'archiveEntry',
        'ex':'restoreException','local_1':'failureContext','ex2':'capturedRestoreException'})
    retain(0x06005CDD,'Retain ClearAllRestorePoints; each listed restore-point path is deleted.',{'projectRestorePointInfo_0':'restorePoint'})
    retain(0x06005CDE,'Retain CreateBackup; UTF-8 is the default zip encoding, and existing exception logging/swallowing remains.',{'encoding2':'selectedArchiveEncoding','zipWrapper':'backupArchive','ex':'backupException'})

    # The archive implementations already have descriptive methods. Complete
    # their field/local vocabulary without changing those public/private names.
    for token,name,reason in [
        (0x04000172,'projectArchive','Constructor ZIP wrapper used to find signature entries and add certificate/validation entries.'),
        (0x04000173,'projectName','Constructor name or ProjectInformation Name; exposed by ExtraData and FilePath in this archive implementation.'),
        (0x04000174,'projectSignatureCreator','Created from the project ID; collects written ZIP entries and is returned with other signature creators.'),
        (0x04000176,'projectMask','Backing storage for the archive project Mask property; no additional mask behavior is inferred.'),
        (0x0400016E,'outerProjectArchive','ZIP archive containing the nested project ZIP; disposed alongside the nested wrapper.'),
        (0x0400016F,'requestProjectPassword','Constructor callback invoked when opening the nested archive.'),
        (0x04000170,'suppliedProjectName','Constructor name is stored but not read by the inspected implementation.'),
        (0x04000171,'nestedProjectArchive','In-memory ZIP wrapper loaded from the project-ID .zip entry and assigned the requested password.')]: record(token,name,reason)
    retain(0x0600051A,'Retain CreateValidProjectCertificateWithRetries; distinguish certificate attempt number and returned certificate.',{'i':'certificateAttempt','art':'projectCertificate'})
    retain(0x0600051B,'Retain AddCertificate; names follow signature entry -> certificate creation -> archive write -> verification report.',{
        'certFile':'signatureEntryName','zipEntry':'signatureEntry','izipEntry_0':'archiveEntry','text':'projectSignature',
        'art':'projectCertificate','flag':'certificateDataVerified','stringBuilder':'validationReportBuilder','text2':'validationReport'})
    retain(0x0600051D,'Retain CreateRewoundTextStream; distinguish the result memory buffer and text writer.',{'memoryStream':'textBuffer','streamWriter':'textWriter'})
    retain(0x060004E9,'Retain OpenNestedProjectZipAndGetPassword; copy the nested entry to memory, open its wrapper and assign the callback password.',{'zipEntry':'nestedZipEntry','memoryStream':'nestedZipBuffer','stream':'nestedZipEntryStream','text':'projectPassword'})
    retain(0x060004EA,'Retain Project accessor; open project.xml from the nested archive with its password.',{'text':'projectPassword'})
    retain(0x060004ED,'Retain Dispose; the outer archive and nested archive are distinct owned resources.',{'zipWrapper':'outerArchiveToDispose','zipWrapper2':'nestedArchiveToDispose'})
