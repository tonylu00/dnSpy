"""Conversion data collectors reviewed after their XML navigation/node helpers."""

def review(add):
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add('Knx.Ets.CvNext',token,name,reason,parameters,locals_,status)
    def pair(interface,implementation,name,reason,parameters=(),locals_=None):
        record(0x06000000+implementation,name,reason,parameters,locals_)
        record(0x06000000+interface,name,'Complete query contract for the reviewed collector: '+reason,parameters)

    # These names describe collected state, not every eligible input container.
    for token,name,reason in [
        (0x7B,'ProjectAddInDataCollector','Collects AddInData XML while inside a project information section, keyed by ProjectId.'),
        (0x7C,'IProjectAddInDataCollector','Contract exposing the collected AddInData element by project ID.'),
        (0x7D,'IConversionDataCollector','Contract selecting input kinds, collecting current XML nodes and resetting collected state.'),
        (0x7E,'LegacyHelpReferenceCollector','Indexes baggage paths and application programs with legacy help attributes.'),
        (0x7F,'ILegacyHelpReferenceCollector','Queries baggage IDs/paths and whether an application program has legacy help references.'),
        (0x80,'ApplicationProgramStyleCollector','Classifies programs from PreEts4Style/MinEtsVersion and links classifications to hardware-program references.'),
        (0x81,'IApplicationProgramStyleLookup','Looks up application-program style for a hardware-program ID.'),
        (0x82,'ApplicationProgramEtsStyle','Pre-ETS4, ETS4 or ETS5 data style; used by the installation XML conversion branches.'),
        (0x83,'IInstallationPuidCollector','Collects the highest Puid and supplies incremented IDs for conversion.'),
        (0x84,'IProjectUserFilesCollector','Contract exposing a collected UserFiles XML element by project ID.'),
        (0x85,'InstallationPuidCollector','Scans Puid attributes, then allocates increasing Puid values under a lock.'),
        (0x86,'ProjectUserFilesCollector','Collects UserFiles/UserFile nodes inside ProjectInformation, keyed by ProjectId.')]:record(0x02000000+token,name,reason)
    for token,name,reason in [(0x210,'PreEts4','Assigned when PreEts4Style parses as true.'),(0x211,'Ets4','Assigned for MinEtsVersion 4.0 and returned as lookup fallback.'),(0x212,'Ets5','Assigned for MinEtsVersion 5.0.')]:record(0x04000000+token,name,reason)

    record(0x060003A6,'BuildManufacturerBaggagePathKey','Formats manufacturer ID and baggage-relative path as manufacturer/path; does not normalize separators.',('relativePath','manufacturerId'))
    record(0x060003A4,'CollectBaggagePathAndId','Reads Id, Name and TargetPath, indexes the ID by manufacturer/path and restores the reader to the element.',('reader',),{'baggageId':'collectedBaggageId','text':'targetPath','text2':'baggageName'})
    record(0x060003A5,'CollectApplicationProgramHelpReferences','Reads HelpFile, ContextHelpFile, ContextHelp and Id; records a non-null application ID if any help value is nonempty, then restores element position.',('reader',),{'text':'helpFile','text2':'contextHelpFile','text3':'contextHelp','applicationProgramId':'collectedApplicationProgramId'})
    pair(0x3A9,0x3A1,'HasBaggageAtManufacturerPath','Builds the manufacturer/path key and checks the baggage index.',('relativePath','manufacturerId'),{'text':'baggagePathKey'})
    pair(0x3AA,0x3A2,'FindBaggageIdAtManufacturerPath','Returns the indexed BaggageId, or null when the manufacturer/path key is absent.',('relativePath','manufacturerId'),{'text':'baggagePathKey'})
    pair(0x3A8,0x3A3,'HasApplicationProgramLegacyHelp','Checks a non-null program ID against programs collected from nonempty legacy help attributes.',('applicationProgramId',))

    record(0x060003B0,'HasCollectedApplicationProgramStyle','Dictionary membership predicate used to select the FIRST classified program referenced by the hardware-program ID.',('applicationProgramId',))
    pair(0x3B1,0x3AF,'GetHardwareProgramEtsStyle','Returns the style of the first classified application-program reference for the hardware-program ID, or Ets4 if none is found.',('hardwareProgramId',),{'text':'classifiedApplicationProgramId'})
    pair(0x3B2,0x3B8,'AllocateNextInstallationPuid','Locks the allocation object, increments the recorded maximum and returns that value; does not promise a GUID or overflow checking.',locals_={'obj':'allocationLock','num':'allocatedPuid'})
    pair(0x3B3,0x3B9,'GetMaximumInstallationPuid','Returns the current maximum, including IDs allocated after collection.')
    pair(0x39A,0x399,'FindProjectAddInData','Returns the collected AddInData element for the project, or null when not present.',('projectId',))
    pair(0x3B4,0x3C0,'FindProjectUserFiles','Returns the collected UserFiles element for the project, or null when not present.',('projectId',))
    for token,name in [(0x397,'ReadAddInDataCollectionScopeChange'),(0x3BE,'ReadUserFilesCollectionScopeChange')]:
        record(0x06000000+token,name,'For ProjectInformation returns false at an empty/end element, true at a start element, and null for unrelated nodes so the respective collector retains its state.',('reader',))

    # Every member of these three shared contracts has been inspected. The
    # collection result means CONTINUE, as verified by apf removing false results.
    for token,reason in [
        (0x395,'Requires the input container to have the ProjectInfo flag.'),
        (0x39E,'Accepts kinds contained in the application/baggage/store mask, or ManufacturerToolXml; preserves the original HasFlag operand order.'),
        (0x3AC,'Accepts kinds contained in the application/hardware/area/unassigned/store mask; preserves the original HasFlag operand order.'),
        (0x3B5,'Accepts kinds contained in the installation/installation-store/area-store mask; preserves the original HasFlag operand order.'),
        (0x3BC,'Requires the input container to have the ProjectInfo flag.')]:
        record(0x06000000+token,'CanCollectFromContainer',reason,('containerType',))
    record(0x0600039B,'CanCollectFromContainer','Complete six-member contract selecting collectors for each conversion input document kind.',('containerType',))
    for token,reason,locals_ in [
        (0x396,'Tracks ProjectId and ProjectInformation scope; captures AddInData start nodes, prepends subsequent AddInData nodes, and stores the result on a nonempty end. Returns true to continue.',{'text':'localName'}),
        (0x39F,'Dispatches Baggage and ApplicationProgram nodes to the reviewed attribute collectors. Returns true to continue.',None),
        (0x3AD,'On start nodes classifies ApplicationProgram by PreEts4Style/MinEtsVersion and records ApplicationProgramRef IDs for the current Hardware2Program. Returns true to continue.',{'aof':'applicationElement','aoc':'programTypeAttribute','aoc2':'programIdAttribute','text':'applicationProgramId','aoc3':'preEts4StyleAttribute','aoc4':'minimumEtsVersionAttribute','aof2':'hardwareProgramElement','aoc5':'hardwareProgramIdAttribute','aoc6':'applicationProgramRefAttribute'}),
        (0x3B6,'Scans attributes named Puid, parses nonempty values with XmlConvert.ToInt32 and raises the recorded maximum. Returns true; does not restore element position here.',{'text':'puidText','num':'puid'}),
        (0x3BD,'Tracks ProjectId and ProjectInformation scope; captures nonempty UserFiles, prepends UserFile nodes, and stores/clears the collected element on its end. Returns true to continue.',{'text':'localName','flag':'scopeChange'})]:
        record(0x06000000+token,'CollectCurrentNodeAndContinue',reason,('reader',),locals_)
    record(0x0600039C,'CollectCurrentNodeAndContinue','Complete six-member contract: false removes the collector from the active list; all current implementations return true. It is not a conversion success flag.',('reader',))
    for token,reason in [(0x398,'Clears AddInData dictionary, project ID, both scope/capture flags and current element.'),
                         (0x3A0,'Clears baggage-path index and programs with help references.'),
                         (0x3AE,'Clears styles, hardware-program references and current hardware-program ID.'),
                         (0x3B7,'Resets the maximum Puid to zero.'),
                         (0x3BF,'Clears UserFiles dictionary, project ID, current element and scope flag.')]:
        record(0x06000000+token,'ResetCollectedData',reason)
    record(0x0600039D,'ResetCollectedData','Complete six-member contract for resetting each collector state.')
    for token,name,reason in [
        (0x200,'addInDataByProject','Collected AddInData elements keyed by ProjectId.'),(0x201,'elementReader','Materializes current XML nodes for AddInData collection.'),
        (0x202,'currentProjectId','Current Project Id read from XML.'),(0x203,'insideProjectInformation','Scope flag changed at ProjectInformation boundaries.'),
        (0x204,'collectingAddInData','Tracks whether an AddInData element has already been captured.'),(0x205,'collectedAddInData','Current materialized AddInData element.'),
        (0x207,'baggageIdsByManufacturerPath','Baggage IDs indexed by the formatted manufacturer/path key.'),(0x208,'programsWithLegacyHelp','Program IDs with nonempty legacy help attributes.'),
        (0x20A,'stylesByApplicationProgramId','Application styles classified from XML attributes.'),(0x20B,'applicationIdsByHardwareProgramId','Ordered application references grouped by hardware-program ID.'),
        (0x20C,'elementReader','Reads current XML element attributes for style classification.'),(0x20D,'currentHardwareProgramId','Hardware2Program Id used for subsequent application references.'),
        (0x213,'puidAllocationLock','Object locked while allocating a new Puid.'),(0x214,'maximumPuid','Maximum collected or subsequently allocated Puid.'),
        (0x216,'elementReader','Materializes UserFiles/UserFile XML nodes.'),(0x217,'userFilesByProject','Collected UserFiles elements keyed by ProjectId.'),
        (0x218,'insideProjectInformation','Scope flag changed at ProjectInformation boundaries.'),(0x219,'currentProjectId','Project ID read before collecting its UserFiles.'),
        (0x21A,'collectedUserFiles','Current nonempty UserFiles element, cleared when stored or an empty element is encountered.')]:record(0x04000000+token,name,reason)
    return [{'Component':'Conversion data collectors','Symbols':['m0046:'+f'0x{0x04000000+t:08X}' for t in [0x206,0x209,0x20E,0x215,0x21B]],
             'Reason':'Unreferenced fields with metadata.field-data storage contracts remain unresolved rather than receiving invented application roles.'}]
