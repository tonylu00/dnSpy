"""Materialized XML nodes: predicates before element mutations and collectors."""

def review(add):
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add('Knx.Ets.CvNext',token,name,reason,parameters,locals_,status)
    def pair(interface,implementation,name,reason,parameters=(),locals_=None):
        record(0x06000000+implementation,name,reason,parameters,locals_)
        record(0x06000000+interface,name,'Complete interface contract: '+reason,parameters)

    record(0x0200001D,'IConversionXmlAttribute','XML name plus string value and nullable Boolean interpretation.')
    record(0x02000021,'ConversionXmlAttribute','Stores an XML attribute and compares prefix, namespace, local name and value ordinally.')
    record(0x0600012C,'HasEqualAttributeNameAndValue','Ordinal comparison of all four components; called by Equals after checking the interface type.',('attribute',))
    for token,params in [(0x125,('reader',)),(0x126,('localName','value')),(0x127,('prefix','xmlNamespace','localName','value'))]:
        record(0x06000000+token,None,'Constructs an attribute from the reader or the supplied XML name components/value.',params,status='retain-method-name')
    record(0x0600012E,None,'Retain AsBool accessor: lowercases invariantly, accepts true/1 and false/0, returns null otherwise; this differs from required XmlConvert parsing.',locals_={'text':'normalizedAttributeValue'},status='retain-method-name')

    record(0x02000020,'IConversionXmlElement','Materialized XML element with attributes, children, lookup, insertion and pruning operations.')
    record(0x02000024,'ConversionXmlElement','Mutable XML element whose insertion helpers prepend by default and optionally follow named siblings.')
    for token,name,reason in [
        (0x02000025,'NamespaceDeclarationPredicateCache','Caches the default-namespace attribute predicate.'),
        (0x02000026,'ChildInsertionPredecessorSelector','Captures names of siblings which may precede one inserted child.'),
        (0x02000027,'ChildInsertionNameMatch','Captures one existing child for comparison with predecessor names.'),
        (0x02000028,'ChildrenInsertionPredecessorSelector','Captures predecessor names for inserting multiple children.'),
        (0x02000029,'ChildrenInsertionNameMatch','Captures one existing child during multi-child insertion.'),
        (0x0200002A,'RetainedElementNameMatch','Captures an element tested against names of subtrees to retain.'),
        (0x0200002B,'ChildElementNameFilter','Captures a NamingPair for deferred filtering of immediate children.'),
        (0x0200002C,'AttributeLocalNameFilter','Captures the ordinal local-name criterion for attribute lookup.')]:record(token,name,reason)
    record(0x06000152,'IsDefaultNamespaceDeclaration','Tests local name xmlns and empty prefix; used to decide whether the element retains its prefix/namespace.',('attribute',))
    for token,name in [(0x156,'MatchesSingleChildPredecessorName'),(0x15A,'MatchesChildRangePredecessorName'),(0x15C,'MatchesRetainedSubtreeName')]:
        record(0x06000000+token,name,'Uses NamingPair.IsEqual against the captured element local name; the name identifies the insertion/retention caller.',('elementName',))
    for token,local,name in [(0x154,'b','IsSingleChildInsertionPredecessor'),(0x158,'d','IsChildRangeInsertionPredecessor')]:
        record(0x06000000+token,name,'Returns whether any supplied predecessor name matches the child local name.',('child',),{local:'elementNameMatch'})
    record(0x0600015E,'MatchesChildElementName','Uses the captured NamingPair to test the immediate child local name.',('child',))
    record(0x06000160,'MatchesAttributeLocalName','Compares attribute local name with the captured criterion using StringComparison.Ordinal.',('attribute',))
    record(0x06000148,'PruneToNamedSubtrees','A matching element keeps its entire subtree. Otherwise recursively removes children with no matching subtree; returns null when no children remain.',
           ('element','retainedElementNames'),{'e':'retainedNameMatch','list':'childrenToRemove','enumerator':'childEnumerator','aof':'child','enumerator2':'removalEnumerator','aof2':'childToRemove'})
    for interface,implementation,name,reason,params,locals_ in [
        (0x118,0x142,'InsertChildAfterNamedSiblings','Inserts at index zero by default; with predecessor names, inserts after the LAST existing child matching any name.',('child','predecessorNames'),{'a':'predecessorSelector','num':'insertionIndex','aof':'lastPredecessor'}),
        (0x119,0x143,'InsertChildrenAfterNamedSiblings','Uses the same predecessor rule, then increments the insertion index so supplied children retain their order.',('children','predecessorNames'),{'c':'predecessorSelector','num':'insertionIndex','aof':'lastPredecessor','enumerator':'childEnumerator','aof2':'child'}),
        (0x11A,0x144,'RemoveChildElement','Removes this child when the collection exists; returns the collection removal result.',('child',),None),
        (0x11B,0x145,'RemoveChildIfLeaf','Null and non-leaf children return true without removal. A leaf returns RemoveChildElement result; attributes do not affect eligibility.',('child',),None),
        (0x11C,0x146,'RetainNamedSubtrees','For nonempty names, recursively retains named subtrees and their ancestors; with no names, clears Children without a null guard.',('retainedElementNames',),None),
        (0x11D,0x147,'RemoveChildElements','Removes each supplied child from the existing Children collection, preserving existing null/argument behavior.',('children',),{'enumerator':'childEnumerator','aof':'child'}),
        (0x11E,0x149,'FindChildrenByElementName','Returns deferred filtering of immediate children by NamingPair, or an empty list when Children is null.',('elementName',),{'class':'childNameFilter'}),
        (0x11F,0x14A,'FindAttributeByLocalName','Returns the first ordinal local-name match, ignoring namespace/prefix, or null.',('localName',),{'class':'attributeNameFilter'}),
        (0x120,0x14B,'RemoveXmlAttribute','Removes the supplied attribute when attributes exist, using its equality implementation.',('attribute',),None),
        (0x121,0x14C,'RemoveAttributeByLocalName','Finds the first local-name match and passes it to List.Remove when attributes exist.',('localName',),None),
        (0x122,0x14D,'SetAttributeByLocalName','Updates the first local-name match; otherwise creates an unqualified attribute, initializing Attributes if needed.',('localName','value'),{'aoc':'existingAttribute'}),
        (0x123,0x14E,'TryReadElementId','Returns false for missing/empty Id; otherwise calls IdCache.Create and tests non-null. Does not catch invalid-ID exceptions.',('id',),{'aoc':'idAttribute'})]:
        pair(interface,implementation,name,reason,params,locals_)
    record(0x0600013B,None,'Copies node name and attributes; restores the reader to its element and clears prefix/namespace unless a default xmlns declaration is present.',('reader',),status='retain-method-name')
    for token,name,reason in [
        (0xB4,'attributes','Backing collection exposed by Attributes.'),(0xB5,'children','Backing collection exposed by Children.'),
        (0xB7,'sharedPredicates','Singleton holder of the namespace declaration predicate.'),(0xB8,'isDefaultNamespaceDeclaration','Cached predicate used while constructing materialized elements.'),
        (0xBA,'predecessorNames','Named siblings allowed before the inserted child.'),(0xBC,'element','Existing sibling tested for a predecessor name.'),
        (0xBE,'predecessorNames','Named siblings allowed before the inserted children.'),(0xC0,'element','Existing sibling tested for a predecessor name.'),
        (0xC2,'element','Element being tested for subtree retention.'),(0xC4,'elementName','NamingPair used to filter child local names.'),
        (0xC6,'localName','Ordinal attribute local-name criterion.')]:record(0x04000000+token,name,reason)
    return [{'Component':'Materialized conversion XML nodes','Symbols':['m0046:'+f'0x{0x04000000+t:08X}' for t in [0xAE,0xB6,0xB9,0xBB,0xBD,0xBF,0xC1,0xC3,0xC5,0xC7]],
             'Reason':'Unreferenced fields with metadata.field-data storage contracts remain unresolved; no application data role is established.'}]
