"""Select declaration evidence; this never performs a textual rename."""

def local_reviews(source, names, identity):
    result=[]
    for old, proposal in (names or {}).items():
        matches=[b for b in source.get('Bindings',[]) or [] if b['Name']==old]
        if isinstance(proposal,dict):
            new=proposal['NewName']
            selectors={k:v for k,v in proposal.items() if k!='NewName'}
            assert selectors and set(selectors)<= {'Kind','Start','Line'}, ('Invalid binding selector',identity,proposal)
            matches=[b for b in matches if all(b.get(k)==v for k,v in selectors.items())]
            assert len(matches)==1, ('Binding selector must identify one declaration',identity,old,proposal)
        else: new=proposal
        assert matches, ('Missing source binding',identity,old)
        result.append({'OriginalName':old,'ProposedName':new,'Occurrences':matches,
                       'Status':'source-declarations-located; semantic references pending'})
    return result
