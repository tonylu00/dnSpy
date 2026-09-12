"""Review emitted source names; discovery never authorizes an automatic rename."""
import re

placeholder = re.compile(r'^(?:(?:[gsv]?method|field)_[0-9A-Fa-f]+|Type_[0-9]+|G?(?:Class|Struct|Enum)[0-9]+)$')
short_identifier = re.compile(r'^[a-z]{1,2}(?:_[0-9]+)?$')
numbered_field = re.compile(r'^[A-Za-z][A-Za-z0-9]*_[0-9]+$')

def source_review_reasons(symbol, row):
    name=row.get('Name')
    if not name: return []
    reasons=[]
    if placeholder.fullmatch(name): reasons.append('emitted-source-placeholder')
    if short_identifier.fullmatch(name): reasons.append('short-source-identifier-review')
    if symbol.get('Kind')=='Field' and numbered_field.fullmatch(name):
        reasons.append('numbered-source-field-review')
    # Reconstructed properties and existing method aliases can already be clear.
    if row['Kind']=='MethodDeclaration' and not symbol.get('Alias') and symbol.get('ReviewReason'):
        reasons.append(symbol['ReviewReason'])
    return reasons
