"""Package manual behavior reviews against the portable application graph.

This stages decisions only. It never edits source or binaries, and never builds
ETS. Local occurrences remain review targets until semantic reference binding.
"""
import hashlib
import json
from pathlib import Path
import sys

graph, destination = map(Path, sys.argv[1:3])
manifest = json.loads((graph / 'manifest.json').read_text())
assert not destination.exists(), 'Use a fresh ledger path'
modules = {m['Project'].replace('\\', '/').split('/')[0]: m for m in manifest['Modules']}
expected_modules = {'ETS6N':'1046CFAD6A073108252AE51537750DCA040D21143B0481899C23A0B9CF0C78D5',
                    'ETS6N.2':'633DEFF4A77C53A822DB3BC1C531116C036F94EBB4FEE9FED6BB1C2FECACDD17',
                    'Knx.Ets.ObjectModel':'FBA7D888A6770FDA55FD0E4E43A77700C01F66A31A1DA6FAD169A4DC296212A1',
                    'Knx.Ets.CvNext':'A01E4D30377F1354EB3F37F3B1734E9922CEEDEF30BC9D1C0B9F54634B8C2AB3',
                    'Knx.Ets.Common.3':'13FA6B5577931CC53E8F921F5E75DB434AC5C61EF948AAC037C4E9AE3F0E8F20'}
assert all(modules[p]['Sha256']==h for p,h in expected_modules.items()), 'This recipe requires the reviewed ETS 6.3 input snapshots'
projects = ['ETS6N', 'ETS6N.2', 'Knx.Ets.ObjectModel', 'Knx.Ets.CvNext', 'Knx.Ets.Common.3']
module_ids = {modules[p]['Id'] for p in projects}
symbols = {}
for line in (graph / 'symbols.jsonl').open(encoding='utf-8'):
    row = json.loads(line)
    if row['Id'].split(':')[0] in module_ids: symbols[row['Id']] = row
selected_files = {'ETS/EtsBootstrapper.cs', 'ETS/CheckProjectData.cs', 'ETS/CheckProductData.cs', 'ETS/ProcessExtensions.cs', 'ETS/InternetAvailabilityCounter.cs', 'ManufacturerCacheProvider.cs', 'any.cs', 'an4.cs', 'arn.cs'}
locations = {}
for line in (graph / 'source.jsonl').open(encoding='utf-8'):
    row = json.loads(line)
    if row['Id'].split(':')[0] in module_ids and row['Source'].split('/', 1)[1] in selected_files:
        locations.setdefault(row['Id'], []).append(row)
root = Path(manifest['Export']).parent
hashes = {}
decisions = []

def add(project, token, name, reason, parameters=(), locals_=None, status='reviewed'):
    token = f'0x{token:08X}'
    copies = ['ETS6N', 'ETS6N.2'] if project == 'ETS' else [project]
    members = []
    for copy in copies:
        module = modules[copy]; key = module['Id'] + ':' + token
        symbol = symbols[key]; source = locations.get(key, [])
        assert source, ('No source evidence', key)
        assert all(s['Sha256'] == source[0]['Sha256'] and s['Source'] == source[0]['Source'] for s in source), ('Ambiguous source', key)
        source = source[0]
        path = root / source['Source']
        if path not in hashes: hashes[path] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        assert hashes[path] == source['Sha256'], ('Stale source', path)
        if parameters:
            assert len(parameters) == len(symbol['Parameters']), (key, parameters, symbol['Parameters'])
        local_rows = []
        for old, new in (locals_ or {}).items():
            matches = [b for b in source.get('Bindings', []) or [] if b['Name'] == old]
            assert matches, ('Missing source binding', key, old)
            local_rows.append({'OriginalName': old, 'ProposedName': new, 'Occurrences': matches,
                               'Status': 'source-declarations-located; semantic references pending'})
        members.append({'Module': module['Input'], 'Sha256': module['Sha256'], 'Mvid': module['Mvid'],
                        'Id': key, 'Token': token, 'Kind': symbol['Kind'], 'OriginalName': symbol['OriginalName'],
                        'Signature': symbol['Signature'], 'ExistingAlias': symbol.get('Alias'),
                        'Source': source['Source'], 'SourceSha256': source['Sha256'], 'Line': source['Line'],
                        'ParameterNames': [{'Sequence': p['Sequence'], 'OriginalName': p['OriginalName'], 'NewName': n}
                                           for p, n in zip(symbol.get('Parameters', []), parameters)],
                        'LocalNames': local_rows, 'Family': symbol.get('Family'), 'MapBlocker': symbol.get('Blocker')})
    assert len({m['Signature'] for m in members}) == 1
    assert len({m['SourceSha256'] for m in members}) == 1, 'Copies require separate behavior review'
    assert not any(set(m['Id'] for m in d['Members']) & set(m['Id'] for m in members) for d in decisions)
    decisions.append({'Order': len(decisions)+1, 'ProposedName': name, 'Reason': reason, 'Status': status,
                      'ApplicationStatus': 'staged; application-wide pass in progress', 'Members': members})

# Leaf methods first. Log message text and concrete library operations establish
# roles; names do not claim to recover vendor identifiers.
for token,name,reason in [
    (0x040000AC,'root','Constructor-supplied IRoot; enumerates its DataStore.ProjectStores for tool/schema compatibility.'),
    (0x040000AD,'messageBoxService','Constructor-supplied service; shows the incompatible project-store error dialog.'),
    (0x040000AE,'logger','CheckProjectData logger; logs the incompatible project-store message.')]:
    add('ETS',token,name,reason)
for token,name in [(0x06000118,'LogManufacturerHashCheckDuration'),(0x06000119,'LogProductStoreCheckDuration'),
                   (0x0600011A,'LogProductStoreLanguageCheckDuration'),(0x0600011B,'LogTemplateStoreCheckDuration'),
                   (0x0600011C,'LogTemplateStoreUpdateDuration')]:
    add('ETS',token,name,'Logs elapsed time with an explicit operation description in the message; retains the existing time formatting.')
add('ETS',0x0600011D,'SelectTemplateFilePath','Identity selector used as the file-path key when mapping templates to schema versions.',('templatePath',))
add('ETS',0x06000123,'ReportCacheRebuildProgress','Chooses the cache-versus-catalog progress message from ManufacturerCacheProvider.RebuildReason; invokes the captured progress callback.')
add('ETS',0x06000110,'DeleteOutdatedDeviceTemplates','Warns for a nonempty obsolete-template list, then SmartDelete is called for each listed file.',('templatePaths',),{'enumerator':'templatePathEnumerator','text':'templatePath'})
add('ETS',0x06000113,'TryDeleteAllDeviceTemplates','Enumerates top-level *.knxtempl files and SmartDeletes them, swallowing failures.',('templateDirectory',),{'files':'templateFiles','i':'fileIndex'})
add('ETS',0x06000112,'TryResetProductStoreForSchemaUpdate','Deletes manufacturer directories M-* and recreates store information in a schema-update transaction; failures are swallowed.',('productStore',),{'directories':'manufacturerDirectories','i':'manufacturerIndex'})
add('ETS',0x06000115,'CreateProductStoreUpdateOperation','Constructs UpdateGlobalProductStoreOperation with the captured component context, factory and supplied progress callback.',('reportProgress',))
add('ETS',0x06000111,'ClassifyDeviceTemplatesBySchemaVersion','Reads each template schema and returns upgradeable and obsolete path lists. Current schema is excluded; 21/22 are upgradeable; older unsupported versions are obsolete. Logs exceptions and returns empty lists.',('templateDirectory',),{'list':'upgradeableTemplates','list2':'outdatedTemplates','enumerable':'templatePaths','func':'templatePathSelector','enumerator':'templateSchemaEnumerator','keyValuePair':'templateSchemaEntry','ex':'schemaReadException'})
add('ETS',0x0600010F,'UpdateDeviceTemplateStore','Reports update progress, validates and executes UpdateDeviceTemplateStoreOperation and logs duration.',('templateDirectory','setProgressText'),{'updateDeviceTemplateStoreOperation':'updateOperation'})
add('ETS',0x0600010A,'CheckProductAndTemplateStoresAsync','Times product schema update, cache language/version checks and template update; returns a completed Task indicating whether product schema update was performed.',('productStore','setProgressText'))
for token,name,reason in [
    (0x04000092,'minimumRequiredSchemaVersion','Initialized from GetCommonSchemaFolderVersion and compared against product/template schema versions.'),
    (0x04000093,'logger','LogManager logger for CheckProductData.'),
    (0x04000094,'globalProductStore','Assigned the constructor globalProductStore and used for manufacturer and cache operations.'),
    (0x04000095,'messageBoxService','Constructor-supplied error dialog service.'),
    (0x04000096,'factory','Constructor-supplied object-model factory for update and cache operations.'),
    (0x0400009A,'sharedCallbacks','Singleton owner of cached logging/path selector delegates.'),
    (0x0400009B,'logManufacturerHashCheckDuration','Cached delegate for the manufacturer hash duration log.'),
    (0x0400009C,'logProductStoreCheckDuration','Cached delegate for the product store check duration log.'),
    (0x0400009D,'logProductStoreLanguageCheckDuration','Cached delegate for the language/version check duration log.'),
    (0x0400009E,'logTemplateStoreCheckDuration','Cached delegate for the template store check duration log.'),
    (0x0400009F,'logTemplateStoreUpdateDuration','Cached delegate for the template update duration log.'),
    (0x040000A0,'selectTemplateFilePath','Cached identity selector for template file paths.')]: add('ETS',token,name,reason)
add('ETS',0x0200002F,'ProductCheckDelegateCache','Holds stateless logging callbacks, an identity selector and their cached delegates.')
add('ETS',0x02000031,'CacheRebuildProgressReporter','Captures the progress callback and translates cache-rebuild reasons to progress messages.')
add('ETS',0x0600010D,None,'Existing CheckTemplateStoreUpdate name is descriptive; improve its intermediate result names.',locals_={'text':'templateDirectory','valueTuple':'templateClassification'},status='retain-method-name')
add('ETS',0x0600010C,None,'Existing CheckProductStoreLanguageAndVersion name is descriptive; name its captured progress reporter.',locals_={'local_1':'progressReporter'},status='retain-method-name')
add('ETS',0x0600010B,None,'Existing CheckAndUpdateIfRequired name is retained; local names describe version checks and conversion setup.',locals_={'informationExtract':'versionCompatibilityChecker','version':'storeToolVersion','text':'unsupportedVersionMessage','updateGlobalProductStoreOperation':'schemaUpdateOperation','enumerator':'manufacturerEnumerator'},status='retain-method-name')
add('ETS',0x06000109,None,'Existing RunAllChecksAsync is retained; bool return remains acceptance of checks, while inner bool tracks schema update.',locals_={'fileProductStore':'productStore','flag':'checksPassed','flag2':'schemaUpdatePerformed','text':'unsupportedVersionMessage'},status='retain-method-name')
add('ETS',0x060001D3,'FindProcessPerformanceCounterInstance','Looks up the Process performance-counter instance whose ID Process value equals the PID. Preserves the last-instance fallback when no match is found.',('processId',),{'text':'instanceName','i':'instanceIndex'})
add('ETS',0x060001D4,'GetParentProcessFromPerformanceCounterInstance','Reads Creating Process ID from the supplied Process counter instance, then gets that process.',('instanceName',))
add('ETS',0x0400010A,'availabilityCheckCount','Incremented once per periodic internet availability attempt; percentage denominator.')
add('ETS',0x0400010B,'successfulAvailabilityCheckCount','Incremented for successful availability checks; percentage numerator.')

# Coupled ObjectModel cache helpers, beginning with selectors and predicates.
obj='Knx.Ets.ObjectModel'
for token,name,parameter,reason in [
    (0x06000357,'GetLiveParameterCache','entry','Returns the strong/weak wrapper Ref for a parameter-cache dictionary entry.'),
    (0x06000358,'IsParameterCacheAlive','cache','Tests a parameter cache reference for non-null.'),
    (0x06000359,'GetLiveCalculatedParameterCache','entry','Returns the strong/weak wrapper Ref for a calculated-parameter cache entry.'),
    (0x0600035A,'IsCalculatedParameterCacheAlive','cache','Tests a calculated parameter cache reference for non-null.'),
    (0x0600035B,'GetLiveComObjectCache','entry','Returns the strong/weak wrapper Ref for a communication-object cache entry.'),
    (0x0600035C,'IsComObjectCacheAlive','cache','Tests a communication-object cache reference for non-null.'),
    (0x0600035D,'ReloadComObjectCache','cache','Calls Reload on the supplied communication-object cache.')]: add(obj,token,name,reason,(parameter,))
add(obj,0x06000334,'BuildDynamicTranslationDictionary','Adds each translation tuple to a string dictionary; duplicate keys still throw.',('translations',),{'dictionary':'translationsById','enumerator':'translationEnumerator','tuple':'translation'})
add(obj,0x06000335,'GetOrCreateApplicationProgramCache','Under the cache lock, reuses a live strong/weak entry or creates and wraps a cache with the current weak-reference policy.',('applicationProgramId','cacheEntries','createCache'),{'obj':'cacheLock','t':'cache','t2':'result','smartStrongAndWeakRef':'cacheReference'})
add(obj,0x0600033B,'UpdateCacheReferenceStrength','Switches an entry to weak/strong retention; removes entries whose target cannot be retained.',('cacheEntries','entry','allowWeakReferences'))
add(obj,0x06000340,'RequiresCacheRebuild','Returns true for a required missing cache, or an existing cache with mismatched product/default language tags or format version 63. Optional absent caches do not require rebuilding.',('cacheStore','manufacturerDefaultLanguage','requireCacheExists'),{'text':'expectedLanguagePair'})
add(obj,0x0600033F,'RebuildManufacturerCaches','Constructs ProductCacheUpdater with supplied/default Caches provider and optional manufacturer, then calls CreateCaches.',('productStore','factory','manufacturerId','cacheProvider','toolVersion'))
for token,name,cache_type in [(0x06000336,'LoadAllParameterRefCaches','parameter'),(0x06000337,'LoadAllCalculatedParameterCaches','calculated-parameter'),(0x06000338,'LoadAllComObjectRefCaches','communication-object')]:
    add(obj,token,name,f'Uses the bulk provider when present; otherwise enumerates application programs, reuses live {cache_type} entries and creates missing entries.',('manufacturerId',))
for token,name in [(0x06000352,'UpdateParameterCacheReferenceStrength'),(0x06000353,'UpdateCalculatedParameterCacheReferenceStrength'),(0x06000354,'UpdateComObjectCacheReferenceStrength')]: add(obj,token,name,'Passes the matching cache dictionary and current weak-reference policy to UpdateCacheReferenceStrength.',('entry',))
add(obj,0x0600034C,'EnsureComObjectCachesReloaded','Under the reload lock, clears the pending flag before enumerating and reloading communication-object caches, preventing recursive reload.',locals_={'obj':'reloadLock'})
for token,name in [(0x04000094,'manufacturerId'),(0x04000095,'catalogCache'),(0x04000096,'hardwareCache'),(0x04000097,'applicationProgramCache'),
                   (0x04000098,'createParameterRefCache'),(0x04000099,'loadAllParameterRefCaches'),(0x0400009A,'createComObjectRefCache'),(0x0400009B,'loadAllComObjectRefCaches'),
                   (0x0400009C,'createCalculatedParameterCache'),(0x0400009D,'loadAllCalculatedParameterCaches'),(0x0400009E,'baggageCache'),
                   (0x0400009F,'parameterCacheEntries'),(0x040000A0,'calculatedParameterCacheEntries'),(0x040000A1,'comObjectCacheEntries'),
                   (0x040000A2,'loadDynamicTranslations'),(0x040000A3,'productStore'),(0x040000A4,'reloadAndTranslationLock'),(0x040000A5,'cacheReferenceLock'),
                   (0x040000A6,'dynamicTranslationsByApplicationProgram'),(0x040000A8,'applicationProgramCacheNeedsReload'),(0x040000A9,'comObjectCachesNeedReload')]:
    add(obj,token,name,'Role verified against constructor assignment and cache retrieval/reload/clear callers in ManufacturerCacheProvider.')
add(obj,0x02000076,'ManufacturerCacheDelegateCache','Stateless live-reference selectors, null predicates, reload action and their cached delegates.')
add(obj,0x0200007C,'ManufacturerCacheLanguageCheck','Captures the manufacturer default-language tag for cache-rebuild predicates.')
for token,name,source_call in [(0x0600036C,'RequiresComObjectCacheRebuild','GetAllComObjectCaches'),(0x0600036D,'RequiresParameterCacheRebuild','GetAllParameterCaches'),(0x0600036E,'RequiresCalculatedParameterCacheRebuild','GetAllCalcParameterCaches')]:
    add(obj,token,name,'Forwards the captured default language to RequiresCacheRebuild. The physical caller 0x0600036A constructs this predicate for '+source_call+'; distinct names describe those separate uses.',('cacheStore',))
for token,name in [(0x040000AD,'sharedCallbacks'),(0x040000AE,'getLiveParameterCache'),(0x040000AF,'isParameterCacheAlive'),(0x040000B0,'getLiveCalculatedParameterCache'),(0x040000B1,'isCalculatedParameterCacheAlive'),(0x040000B2,'getLiveComObjectCache'),(0x040000B3,'isComObjectCacheAlive'),(0x040000B4,'reloadComObjectCache')]:
    add(obj,token,name,'Singleton/cached delegate in ManufacturerCacheDelegateCache; matches the corresponding reviewed selector, predicate or reload action.')

# CvNext leaf helpers are recorded before naming its larger conversion callers.
cv='Knx.Ets.CvNext'
add(cv,0x0600001C,'IsSupportedConversionNamespace','Enumerates schema versions >=14 and matches Namespace.GetXmlNamespace against the input.',('xmlNamespace',),{'enumerator':'schemaVersionEnumerator','knxXmlSchemaVersion':'schemaVersion'})
add(cv,0x0600001D,'GetSupportedConversionSchemaVersion','Returns null for unsupported namespace, otherwise Namespace.GetSchemaVersionFromNamespace.',('xmlNamespace',))
add(cv,0x0600001E,'GetConverterToolVersion','Returns the converter tool-version string initialized by the constructor.')
add(cv,0x06000028,'ThrowIfConversionCancellationRequested','Logs Conversion Cancelled and throws OperationCanceledException when cancellation was requested.',('cancellationToken',))
add(cv,0x0600002B,'ReportConversionProgress','Invokes the optional captured progress delegate with phase, detail and percentage.',('phase','detail','percent'))
add(cv,0x0600002F,'IsAccessKeyProvider','Checks whether the key provider implements IAccessKeyProvider.',('keyProvider',))
add(cv,0x06000030,'IsConversionDocumentModified','Returns the conversion document IsModified property.',('document',))
for offset,xml_name in enumerate(['xmlns','ToolVersion','CreatedBy','HelpFile','Id','RefId','Name','Number','AttributeName','Text','IsActivityCalculated','PreEts4Style','MinEtsVersion','ProgramType','ChannelId','GroupAddressRefId','GroupObjectInstances','Hardware2ProgramRefId','IsActive','Links','Type','Acknowledge','Acknowledges','ContextHelpFile','IconFile','TargetPath','Identifier','RFRxCapabilities','RFTxCapabilities','Filename','Comment','AddinId','DoNotCopy','MediumTypeRefId','MediumTypes','DomainAddress','Puid','LastUsedPuid','Parameter','MaxSecurityProxyIndividualAddressTableEntries']):
    add(cv,0x0400006B+offset,'NamespaceDeclaration' if xml_name=='xmlns' else xml_name,'XML attribute-name string literal: '+xml_name+'. The string value stays unchanged.')
add(cv,0x02000014,'ConversionXmlAttributeNames','String constants used to read and write KNX XML attributes during conversion.')
add(cv,0x06000022,'ReadExtractedProjectName','Reads the Name attribute from ProjectInformation in the first extracted project.xml; an4.g is the literal Name. Returns null when no matching data is found.',('extractedProject',),{'text':'projectXmlPath','text2':'projectName','textReader':'projectTextReader','xmlReader':'projectXmlReader'})
for token,name,reason in [(0x04000010,'minimumConvertibleSchemaVersion','Constant Version14, also the lower bound in namespace support checks.'),
                        (0x04000011,'conversionTempDirectory','Path.Combine(temp, KNX, CvNext).'),
                        (0x04000012,'converterToolName','Constructor tool name or CvNext fallback, used in conversion metadata.'),
                        (0x04000014,'reportConversionProgress','Captured ConversionStepsUserInfoOutput delegate.'),
                        (0x04000016,'supportedContainerExtensions','Explicit list of supported input file extensions.'),
                        (0x04000017,'converterToolVersion','Constructor tool version or executing assembly version, returned by the getter.')]:add(cv,token,name,reason)

from bootstrapper import review as review_bootstrapper
review_bootstrapper(add)
add('Knx.Ets.Common.3',0x060000DD,'GetLatestSupportedConversionSchemaVersion','Returns Version23; initializes the CvNext conversion target and supplies the CLI highest-supported-target diagnostic. All indexed callers were inspected.')
add(cv,0x0400000F,'LatestSupportedConversionSchemaVersion','Initialized by the Common conversion-version getter; used as the default/latest target by conversion entry points, as the template current-version exclusion, and as the import minimum after conversion. The corrected field-reference graph resolves the exact Common/CvNext dependency.')
add(cv,0x04000015,'LatestSupportedConversionXmlNamespace','Namespace.GetXmlNamespace of LatestSupportedConversionSchemaVersion, assigned by the static initializer.')

result={'Format':1,'Kind':'ApplicationBehaviorReview','Graph':str(graph),'GraphManifestSha256':hashlib.sha256((graph/'manifest.json').read_bytes()).hexdigest(),
        'Status':'staged, incomplete application-wide pass; no source application or ETS verification this round',
        'Decisions':decisions,'Unresolved':[{'Component':'Common','Symbol':'CurrentProjectSchemaInformation.f/e','Reason':'The unreferenced constant getter and the XML document/signing getter still need their roles reviewed. Conversion getter d and CvNext field a now have resolved reference evidence and staged names.'},
        {'Component':'Application-wide','Reason':'Source-local references still need semantic application support; declaration locations alone do not authorize text replacement. Field aliases require the field-aware map exporter.'}]}
destination.write_text(json.dumps(result,indent=2)+'\n')
print(f'Staged {len(decisions)} behavior decisions across {len({m["Module"] for d in decisions for m in d["Members"]})} physical inputs. No source or binary changes.')
