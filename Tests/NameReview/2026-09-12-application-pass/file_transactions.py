"""File transaction lifecycle, commit journal and startup recovery evidence."""

def review(add):
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add('Knx.Ets.ObjectModel',token,name,reason,parameters,locals_,status)
    def retain(token,reason,names): record(token,None,reason,locals_=names,status='retain-method-name')

    retain(0x06005E5B,'Retain Retryable.Create; attempts creation up to times, sleeps after each exception, logs recovery, then throws the last exception or returns default for no attempts.',{
        'ex':'lastCreationException','i':'attemptIndex','t':'createdValue','t2':'creationResult'})
    record(0x04002BEB,'MaximumCreationAttempts','Literal five passed to Retryable.Create by every file-stream factory.')
    record(0x04002BEC,'CreationRetryDelay','Fifty-millisecond delay passed to Retryable.Create by every file-stream factory.')

    record(0x06005E77,'CreateMissingAncestorDirectories','Walks upward to an existing ancestor, reverses the missing-directory list and creates each in parent-first order; Rollback deletes the first newly created ancestor.',locals_={'parent':'directoryToCreate','info':'missingDirectory'})
    record(0x04002C01,'createdDirectories','Tracks only missing directories created by this instance, in parent-first order after reversal.')
    retain(0x06005E7B,'Retain directory Rollback; remove the highest newly created directory recursively when it still exists.',{'directoryInfo':'createdAncestorDirectory'})

    record(0x06005E83,'CloseWriteStreamAndRefreshTransactionFile','Unless disposed, flushes and closes the write stream, then refreshes the transaction FileInfo; used by prepare and rollback.')
    for token,name,reason in [
        (0x04002C04,'originalFile','FileInfo supplied by the caller; target of committed writes.'),
        (0x04002C05,'allowMultipleWrites','Constructor flag permits another stream for a file already participating in the transaction.'),
        (0x04002C06,'transactionFile','Dollar-prefixed temporary file used during an ambient transaction.'),
        (0x04002C07,'writeStream','Underlying normal/hashed stream, directed to original or temporary file depending on transaction state.'),
        (0x04002C08,'isDisposed','Set by Dispose and checked before closing the underlying stream during prepare/rollback.')]: record(token,name,reason)
    retain(0x06005E81,'Retain TransactionalFileStream constructor; track whether the file already belongs to the active transaction.',{'flag':'fileAlreadyEnlisted'})
    retain(0x06005E84,'Retain Commit; remove active-file tracking and queue a nonempty temporary file for copy, otherwise queue deletion. Existing multi-write rules and cleanup remain.',{'flag':'fileWasEnlisted','ex':'commitException'})
    retain(0x06005E85,'Retain Rollback; remove active-file tracking, close the stream and delete the temporary file when this enlistment owns it.',{'flag':'fileWasEnlisted'})

    # Journal leaf operations first, then the commit and recovery coordinators.
    record(0x06005E9F,'TryCleanupFileSystemEntry','Invokes a cleanup action and logs/swallow exceptions. Used for files, hash sidecars and directories despite its original log text saying file.',('cleanup',),{'ex':'cleanupException'})
    record(0x06005E94,'EndFileTransactionTracking','Logs and clears leftover active files, then clears the current TransactionKeeper.')
    record(0x06005EA5,'NotifyStoreRepairState','Invokes the optional store-repair event with root path and Started/Finished state.',('storeRootPath','repairState'),{'storeRepairEventDelegate':'repairHandler'})
    record(0x06005EAA,'HasPendingFileChangesUnderRoot','Tests temporary-file keys in both copy and deletion queues using StartsWith against the supplied root.',('storeRootPath',))
    record(0x06005EB9,'IsExistingRootWithPendingFileChanges','Requires an existing directory and pending copy/deletion keys under that root; filters the roots processed by Dispose.',('storeRootPath',))
    record(0x06005EAC,'RecreateCommitJournalDirectory','Deletes an existing indexed commit folder, then creates it again.',('rootIndex',),{'text':'commitDirectory'})
    record(0x06005EB1,'GetCommitBackupFilePath','Removes the indexed root prefix and leading directory separators from a file path, then places that relative path under the matching commit directory.',('originalFilePath','rootIndex'),{'text':'relativeFilePath'})
    record(0x06005EB3,'WriteNewFileRollbackList','Writes newline-separated newly created file paths to $$newfiles$$ as UTF-8 and flushes to disk.',('newFilePaths','commitDirectory'),{'fileStream':'newFileListStream','bytes':'encodedFileList'})
    record(0x06005EB2,'WriteOrClearCommitStatus','Empty status deletes $$status$$ through the cleanup helper; otherwise writes the UTF-8 status and flushes to disk.',('status','commitDirectory'),{'fileStream':'statusStream','bytes':'encodedStatus'})
    record(0x06005EAF,'CopyFlushedThenDeleteTransactionFile','Copies an existing temporary file to its target with disk flush, then attempts to delete the source; logs a warning if source is already absent.',('transactionFilePath','targetFilePath'))
    record(0x06005EAE,'CommitPendingChangesForRoot','Backs up existing targets and records new paths, writes Committing status, applies queued copies/deletions, removes empty directories, then clears status and the commit folder.',('rootIndex',),{
        'text':'commitDirectory','currentRootPath':'storeRootPath','enumerable':'pendingCopies','list':'newFilePaths','enumerable2':'pendingDeletions',
        'enumerator1':'copyBackupEnumerator','keyValuePair':'copyToBackup','text2':'copyBackupPath',
        'enumerator2':'deletionBackupEnumerator','keyValuePair2':'deletionToBackup','text3':'deletionBackupPath',
        'enumerator3':'copyCommitEnumerator','keyValuePair3':'copyToCommit','list2':'removedDirectories',
        'enumerator':'deletionCommitEnumerator','keyValuePair4':'deletionToCommit','directoryName':'emptyParentDirectory',
        'keyValuePair_0':'pendingChange'})
    record(0x06005E99,'ValidateFileTransactionScope','Requires an active keeper and a root that prefixes the captured fullName. Input lambda IL loads captured field 0x04002C1A before ldarg.1 and String.StartsWith(InvariantCultureIgnoreCase); the current source incorrectly prints identical parameter names.',('filePath',),{
        'string_0':{'NewName':'transactionRootPath','Kind':'Parameter','Start':8965}})
    for token,name,reason in [
        (0x04002C09,'activeFilesWereNew','Maps active original file paths to whether they were absent when Add enlisted them.'),
        (0x04002C0A,'transactionStateLock','Shared lock protecting keeper state, active files and queued copies/deletions.'),
        (0x04002C0B,'currentTransaction','Single active TransactionKeeper; cleared at the end of disposal.'),
        (0x04002C0C,'pendingFileCopies','Maps temporary file paths to original destination paths queued for commit.'),
        (0x04002C0D,'pendingFileDeletions','Maps temporary file paths to original paths that commit should delete.'),
        (0x04002C0E,'storeRepairHandlers','Event storage for store-repair Started/Finished notifications.'),
        (0x04002C0F,'CommitDirectoryName','Literal $$commit$$ identifying the per-root rollback journal directory.'),
        (0x04002C10,'commitDirectories','Commit-directory paths indexed in parallel with the filtered RootPaths array.')]: record(token,name,reason)
    for token,names in [
        (0x06005E93,{'obj':'transactionLock','disposable':'transactionLifetime'}),
        (0x06005E96,{'obj':'transactionLock','flag2':'fileParticipatesInTransaction'}),
        (0x06005E97,{'obj':'transactionLock'}),(0x06005E98,{'obj':'transactionLock'}),
        (0x06005E9A,{'obj':'transactionLock'}),(0x06005E9B,{'obj':'transactionLock'}),
        (0x06005E9C,{'text':'currentFilePath','obj':'transactionLock'}),
        (0x06005E9D,{'flag':'deletedTransactionFile','obj':'transactionLock','fullName':'transactionFilePath'}),
        (0x06005EA9,{'obj':'transactionLock','i':'rootIndex','ex':'commitException','text':'fatalCommitMessage'}),
        (0x06005EAD,{'flag':'commitDirectoryExisted'}),
        (0x06005EB0,{'directoryName':'targetDirectory','fileStream':'sourceStream','fileStream2':'targetStream'}),
        (0x06005EB5,{'text':'commitStatusPath'}),
        (0x06005EB8,{'obj':'transactionLock','array':'expandedRootPaths'})]:
        retain(token,'Retain the existing transaction API name; local roles follow the reviewed tracking, journal and commit helpers.',names)
    retain(0x06005E95,'Retain CleanupOrFixBrokenTransactionsBeforeOpen; restore journal backups and remove new files for an interrupted commit, then clean temporary/empty entries and caches. Existing error swallowing and repair notifications remain.',{
        'flag':'repairStarted','commitFolderName':'commitDirectory','enumerator1':'backupFileEnumerator',
        'text':'backupFilePath','text2':'relativeBackupPath','text3':'originalFilePath',
        'enumerator4':'temporaryFileEnumerator','info2':'temporaryFilePath','enumerator':'applicationDirectoryEnumerator',
        'enumerator2':'rootFileEnumerator','fileInfo':'emptyRootFile','enumerator3':'manufacturerDirectoryEnumerator',
        'directoryInfo':'manufacturerDirectory','info':'applicationDirectoryPath','ex':'repairException'})
    return [{'Component':'ObjectModel file transactions','Symbol':'m0057:0x06005E99',
             'Source':'Knx.Ets.ObjectModel/FileSystemStore/TransactionalFileStreamManager.cs:233',
             'Reason':'Existing source shadows captured file path with identically named lambda parameter. Input method 0x06005ECB calls captured fullName.StartsWith(lambda argument, InvariantCultureIgnoreCase). Outer filePath alias and exact lambda transactionRootPath binding are staged; exporter/reference binding and consolidated verification must prove the repaired expression.'}]
