"""XML adapters: library operations first, complete reader/writer contracts next."""

def review(add):
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add('Knx.Ets.CvNext',token,name,reason,parameters,locals_,status)
    def pair(interface,implementation,name,reason,parameters=(),locals_=None):
        record(implementation,name,reason,parameters,locals_)
        record(interface,name,'Complete interface contract for the reviewed implementation: '+reason,parameters)

    record(0x060000B7,'CreateConversionXmlReaderSettings','Creates fragment-mode settings that close input and ignore comments/whitespace.')
    record(0x0200001B,'HexAttributeByteDecoder','Captures hexadecimal attribute text for two-character byte parsing.')
    record(0x040000A6,'hexText','Hexadecimal text captured by the optional byte-array attribute reader.')
    record(0x060000F8,'ParseHexAttributeByte','Parses the two characters at twice the byte index using NumberStyles.HexNumber.',('byteIndex',))
    record(0x02000016,'IConversionXmlReader','Conversion reader contract for XML navigation, attributes, typed values and subtree reading.')
    record(0x0200001A,'ConversionXmlReader','XmlReader adapter with content-node filtering, subtree views and typed attribute parsing.')
    for token,name,reason in [(0x040000A2,'xmlReader','Underlying XmlReader owned by the adapter.'),
                             (0x040000A3,'reuseCurrentNode','Set after seeking/skipping so the next content read returns the current node without advancing again.'),
                             (0x040000A4,'minimumElementDepth','Initially -1; seeking sets this depth. Content reads compare it only when the current node is an Element.')]:record(token,name,reason)
    for token,params,reason in [(0x060000B4,('inputStream',),'Creates an XmlReader using the conversion fragment settings.'),
                                (0x060000B5,('sourceReader',),'Uses the source adapter reader to create a subtree view.'),
                                (0x060000B6,('sourceXmlReader',),'Moves an initial reader to content, creates a subtree reader and primes it with Read.')]:
        record(token,None,reason,params,status='retain-method-name')
    for interface,implementation,name,reason,params in [
        (0x6C,0xBC,'OpenXmlSubtreeReader','Wraps ReadSubtree in another conversion reader.',()),
        (0x6D,0xBF,'ReadToNamedXmlNode','Reads until LocalName matches, records its depth and reuses that node on the next read; disposes and returns null when no match is found.',('localName',)),
        (0x6E,0xC0,'MoveFromAttributeToXmlElement','Calls MoveToElement only when positioned on an attribute.',()),
        (0x6F,0xBD,'ReadInnerXmlContent','Forwards XmlReader.ReadInnerXml.',()),
        (0x70,0xBE,'ReadOuterXmlContent','Forwards XmlReader.ReadOuterXml.',()),
        (0x71,0xC1,'ReadNextXmlContentNode','Returns Element, EndElement, Text or CDATA nodes; honors reuseCurrentNode and applies the minimum-depth check only to Element nodes.',()),
        (0x72,0xC2,'SkipCurrentXmlContent','Calls Skip unless empty/end element, then reuses the resulting node on the next content read.',()),
        (0x73,0xC3,'ReadNextXmlText','Advances until Text/CDATA and returns Value, otherwise null at end; clears node reuse first.',()),
        (0x74,0xC4,'GetXmlLocalName','Returns LocalName, or null when the underlying reader is null.',()),
        (0x75,0xC5,'GetXmlPrefix','Returns XmlReader.Prefix.',()),
        (0x76,0xC6,'GetXmlNamespace','Returns XmlReader.NamespaceURI.',()),
        (0x77,0xC7,'IsEmptyXmlElement','Returns XmlReader.IsEmptyElement.',()),
        (0x78,0xC9,'IsXmlEndElement','Tests NodeType == EndElement.',()),
        (0x79,0xC8,'IsXmlStartElement','Tests NodeType == Element.',()),
        (0x7A,0xCA,'HasXmlAttributes','Returns XmlReader.HasAttributes.',()),
        (0xA5,0xB8,'GetXmlNodeType','Returns XmlReader.NodeType.',()),
        (0xA6,0xB9,'MoveToNextXmlAttribute','Forwards MoveToNextAttribute.',()),
        (0xA7,0xBA,'GetXmlNodeValue','Returns XmlReader.Value.',()),
        (0xA8,0xBB,'TryReadXmlIdAttribute','Moves to the element, finds Id and calls IdCache.Create<T>; returns false when absent, does not catch invalid-ID exceptions.',('id',))]:
        pair(0x06000000+interface,0x06000000+implementation,name,reason,params)
    pair(0x0600007C,0x060000CC,'ReadRequiredStringAttribute','Reads XmlReader[name]; missing attribute throws the existing ArgumentOutOfRangeException.',('attributeName',),{'text':'attributeValue'})
    pair(0x0600007B,0x060000CB,'ReadRequiredTruncatedStringAttribute','Reads the required attribute and truncates only when maximumLength > 0 and the value is longer.',('attributeName','maximumLength'),{'text':'attributeValue'})
    pair(0x0600008C,0x060000DC,'ReadStringAttributeOrDefault','Reads XmlReader[name], using defaultValue only when missing.',('attributeName','defaultValue'))
    pair(0x0600008B,0x060000DB,'ReadTruncatedStringAttributeOrDefault','Uses the provided fallback when absent, then truncates either result only for a positive maximumLength.',('attributeName','defaultValue','maximumLength'),{'text':'attributeValue'})

    # These are explicit reviewed tables. Required bytes use Base64 while the
    # optional byte-array overload uses HEX; do not infer equivalence by type.
    required=[(0x7D,0xCD,'Boolean','XmlConvert.ToBoolean'),(0x7E,0xCE,'UtcDateTime','XmlConvert.ToDateTime in Utc mode'),
              (0x7F,0xCF,'Double','XmlConvert.ToDouble'),(0x80,0xD0,'Single','XmlConvert.ToSingle'),
              (0x81,0xD1,'UInt16','XmlConvert.ToUInt16'),(0x82,0xD2,'UInt32','XmlConvert.ToUInt32'),
              (0x83,0xD3,'UInt64','XmlConvert.ToUInt64'),(0x84,0xD4,'Int16','XmlConvert.ToInt16'),
              (0x85,0xD5,'Int32','XmlConvert.ToInt32'),(0x86,0xD6,'Int64','XmlConvert.ToInt64'),
              (0x87,0xD7,'Byte','XmlConvert.ToByte'),(0x88,0xD8,'Base64','Convert.FromBase64String'),(0x8A,0xDA,'IPAddress','IPAddress.Parse')]
    for interface,implementation,kind,parser in required:
        pair(0x06000000+interface,0x06000000+implementation,'ReadRequired'+kind+'Attribute','Reads a required attribute then uses '+parser+'; preserves parse exceptions.',('attributeName',))
    defaults=[(0x8D,0xDD,'Boolean','XmlConvert.ToBoolean'),(0x8E,0xDE,'UtcDateTime','XmlConvert.ToDateTime in Utc mode'),
              (0x8F,0xDF,'Double','XmlConvert.ToDouble'),(0x90,0xE0,'NullableDouble','XmlConvert.ToDouble'),
              (0x91,0xE1,'Single','XmlConvert.ToSingle'),(0x92,0xE2,'UInt16','XmlConvert.ToUInt16'),
              (0x93,0xE3,'UInt32','XmlConvert.ToUInt32'),(0x94,0xE4,'UInt64','XmlConvert.ToUInt64'),
              (0x95,0xE5,'NullableUInt64','XmlConvert.ToUInt64'),(0x96,0xE6,'Int16','XmlConvert.ToInt16'),
              (0x97,0xE7,'Int32','XmlConvert.ToInt32'),(0x98,0xE8,'NullableInt32','XmlConvert.ToInt32'),
              (0x99,0xE9,'Int64','XmlConvert.ToInt64'),(0x9A,0xEA,'Byte','XmlConvert.ToByte'),
              (0x9B,0xEB,'NullableByte','XmlConvert.ToByte'),(0x9E,0xEE,'IPAddress','IPAddress.Parse'),
              (0xA0,0xF0,'NullableUInt16','XmlConvert.ToUInt16'),(0xA1,0xF1,'NullableSingle','XmlConvert.ToSingle'),
              (0xA2,0xF2,'NullableBoolean','XmlConvert.ToBoolean'),(0xA4,0xF4,'NullableUtcDateTime','XmlConvert.ToDateTime in Utc mode')]
    for interface,implementation,kind,parser in defaults:
        pair(0x06000000+interface,0x06000000+implementation,'Read'+kind+'AttributeOrDefault','Missing attribute returns defaultValue; present text is parsed with '+parser+'. Invalid or empty present text is not silently replaced.',('attributeName','defaultValue'),{'text':'attributeValue'})
    pair(0x0600009F,0x060000EF,'ReadEnabledAttributeOrDefault','Returns the nullable fallback when missing; any present value compares case-sensitively to the literal Enabled.',('attributeName','defaultValue'),{'text':'attributeValue'})
    pair(0x0600009C,0x060000EC,'ReadHexBytesAttributeOrDefault','Missing attribute returns the supplied bytes; present text is parsed in pairs as hexadecimal. An odd trailing character is ignored by Length / 2.',('attributeName','defaultValue'),{'a':'hexDecoder'})
    for interface,implementation,name,params,reason in [
        (0x89,0xD9,'ReadRequiredConvertedAttribute',('attributeName','useTypeConverter'),'Requires attribute presence.'),
        (0x9D,0xED,'ReadConvertedAttributeOrDefault',('attributeName','defaultValue','useTypeConverter'),'Uses fallback only when absent.'),
        (0xA3,0xF3,'ReadNullableConvertedAttributeOrDefault',('attributeName','defaultValue','useTypeConverter'),'Uses fallback when absent OR empty.')]:
        pair(0x06000000+interface,0x06000000+implementation,name,reason+' Unless useTypeConverter, first tries case-sensitive Enum.TryParse<T>; otherwise uses TypeDescriptor converter and preserves exceptions.',params,{'text':'attributeValue','t':'parsedEnumValue'})
    record(0x060000F6,None,'Retain ToString diagnostic override; describes reader state, local name and depth.',locals_={'stringBuilder':'readerDescription'},status='retain-method-name')

    record(0x02000017,'IConversionXmlWriter','Contract for serializing current reader nodes and materialized conversion XML elements/attributes.')
    record(0x0200001C,'ConversionXmlWriter','Owns UTF-8 XmlWriter and output stream, with shared disposal and write-request tracking.')
    record(0x06000107,'FlushAndDisposeConversionXmlOutput','Flushes/disposes the writer, clears its field, then disposes the output stream.')
    record(0x06000106,'DisposeConversionXmlOutput','Passes disposing and the reviewed cleanup callback to Disposer.',('disposing',))
    record(0x06000104,'FlushConversionXmlOutput','Flushes the underlying writer when present.',locals_={'xmlWriter':'outputWriter'})
    record(0x060000FB,'SetXmlWriteRequestReceived','Sets the tracking flag used by every writer API; it can be true even when a node kind is ignored.',('writeRequested',))
    for interface,implementation,name,reason,params,locals_ in [
        (0xA9,0xFA,'HasReceivedXmlWriteRequest','Returns the tracking flag; it does not prove that bytes were written.',(),None),
        (0xAA,0xFC,'WriteCurrentConversionXmlNode','Dispatches Element/Attribute/Text/CDATA/EndElement from the current reader node; unsupported listed kinds are ignored after setting the write-request flag.',('reader',),None),
        (0xAB,0xFD,'WriteConversionElementStart','Writes prefix/local-name/namespace then all attributes; leaves the element open.',('element',),{'aoc':'attribute'}),
        (0xAC,0xFE,'WriteConversionElementTree','Writes an element start, recursively writes its children, then writes its end.',('element',),{'enumerator':'childEnumerator','aof':'childElement'}),
        (0xAD,0xFF,'WriteConversionXmlAttribute','Writes prefix/local-name/namespace/value from the supplied attribute.',('attribute',),None),
        (0xAE,0x100,'WriteConversionXmlEndElement','Forwards XmlWriter.WriteEndElement and records a write request.',(),None),
        (0xAF,0x101,'WriteConversionXmlText','Forwards XmlWriter.WriteString and records a write request.',('text',),None),
        (0xB0,0x102,'WriteConversionXmlCData','Forwards XmlWriter.WriteCData and records a write request.',('text',),None),
        (0xB1,0x103,'WriteUnqualifiedConversionXmlAttribute','Writes the supplied local-name/value with empty namespace.',('localName','value'),None)]:
        pair(0x06000000+interface,0x06000000+implementation,name,reason,params,locals_)
    for token,name,reason in [(0x040000A8,'disposer','Coordinates idempotent disposal of the XML writer/output stream.'),
                             (0x040000A9,'outputStream','Constructor-provided output stream; XML settings also close output.'),
                             (0x040000AA,'xmlWriter','UTF-8 indented writer with Entitize newline handling.'),
                             (0x040000AB,'writeRequestReceived','Set before handling write requests, including ignored current-node kinds.')]:record(token,name,reason)
    record(0x060000F9,None,'Creates UTF-8 indented XmlWriter with CloseOutput and Entitize newlines, then writes the document start.',('outputStream',),status='retain-method-name')

    record(0x0200001E,'IConversionXmlNodeName','Mutable prefix/namespace/local-name contract shared by elements and attributes.')
    record(0x02000022,'ConversionXmlNodeName','Stores the three XML name components populated from the reader or explicit constructor values.')
    for interface,implementation,field,part,parameter in [(0x10B,0x132,0xAF,'Prefix','prefix'),
                                                          (0x10D,0x134,0xB0,'Namespace','xmlNamespace'),
                                                          (0x10F,0x136,0xB1,'LocalName','localName')]:
        pair(0x06000000+interface,0x06000000+implementation,'GetConversionNode'+part,'Returns the stored XML '+part+' used by XmlWriter overloads.')
        pair(0x06000001+interface,0x06000001+implementation,'SetConversionNode'+part,'Sets the XML '+part+' component.',(parameter,))
        record(0x04000000+field,parameter,'Stored XML '+part+' component; constructor order and XmlWriter call order establish the role.')
    record(0x06000130,None,'Copies prefix, namespace URI and local name from the current reader node.',('reader',),status='retain-method-name')
    record(0x06000131,None,'Stores the supplied prefix, namespace and local name.',('prefix','xmlNamespace','localName'),status='retain-method-name')
    record(0x0200001F,'IConversionElementReader','Contract for materializing the current node, optionally including its subtree.')
    record(0x02000023,'ConversionElementReader','Builds a conversion element and recursively materializes children in Subtree mode.')
    record(0x02000057,'XmlNodeMaterializationMode','Controls current-node-only versus recursive child materialization; it does not select an encoding or schema version.')
    record(0x04000187,'CurrentNode','Default mode creates the current element and its attributes without recursively reading children.')
    record(0x04000188,'Subtree','Mode that recursively reads child elements through a subtree reader.')
    pair(0x06000111,0x06000138,'ReadConversionElement','Constructs the current element; in Subtree mode on a start element, recursively reads children until the subtree end.',
         ('reader','materializationMode'),{'aof':'element','an':'subtreeReader'})

    record(0x0200002D,'IConversionDocumentValidator','Contract invoked for modified conversion documents before converted files are committed.')
    record(0x0200002E,'ConversionDocumentSchemaValidator','Validates file XML using the embedded target-schema XSD and checks every element namespace.')
    record(0x0200002F,'ConversionSchemaValidationContext','Captures the document for schema validation event diagnostics.')
    record(0x040000CB,'document','Document whose path is reported in validation errors and warnings.')
    record(0x06000166,'OnConversionSchemaValidation','Logs and throws ValidationFailedException for schema errors; logs warnings without throwing and rejects unknown severities.',
           ('sender','validationEvent'),{'severity':'validationSeverity','text':'validationErrorMessage'})
    record(0x06000164,'OpenConversionTargetSchemaStream','Opens the embedded Knx.Ets.CvNext.knx_project-{version}.xsd resource for the configured target schema.',locals_={'text':'schemaResourceName'})
    pair(0x06000161,0x06000163,'ValidateConversionDocumentSchema','Null document returns; missing file throws; otherwise validates against the target XSD and requires the target namespace on each XML element.',('document',),{
        'a':'validationContext','fullName':'documentPath','stream':'schemaStream','xmlReader':'schemaReader',
        'xmlReaderSettings':'validationSettings','fullName2':'validationInputPath','xmlReader2':'documentReader',
        'text':'namespaceMismatchMessage','text2':'missingFileMessage'})
    record(0x040000C8,'targetSchemaVersion','Constructor version used to select the embedded validation schema; versions below 20 are rejected.')
    record(0x040000C9,'targetXmlNamespace','Namespace.GetXmlNamespace of the configured target schema.')
    record(0x06000162,None,'Rejects schema versions below 20 and stores target schema and namespace.',('targetSchemaVersion',),status='retain-method-name')
    return [{'Component':'CvNext XML adapters','Symbols':['m0046:0x040000A5','m0046:0x040000A7','m0046:0x040000AC','m0046:0x040000B2','m0046:0x040000B3','m0046:0x040000CA','m0046:0x040000CC'],
             'Reason':'String fields carry original storage metadata without an established role; preserve until that metadata contract is reviewed.'}]
