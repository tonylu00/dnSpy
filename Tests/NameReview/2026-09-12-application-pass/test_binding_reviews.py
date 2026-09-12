from binding_reviews import local_reviews

source={'Bindings':[{'Kind':'Parameter','Name':'string_0','Line':227,'Start':8662},
                    {'Kind':'Parameter','Name':'string_0','Line':233,'Start':8965}]}
result=local_reviews(source,{'string_0':{'NewName':'transactionRootPath','Kind':'Parameter','Start':8965}},'method')
assert result[0]['Occurrences']==[source['Bindings'][1]]
assert result[0]['ProposedName']=='transactionRootPath'
for selection in [{'NewName':'wrong','Kind':'Parameter'}, {'NewName':'wrong','Start':1}, {'NewName':'wrong','Unsupported':1}]:
    try: local_reviews(source,{'string_0':selection},'method')
    except AssertionError: pass
    else: raise AssertionError('Ambiguous, stale or unsupported selector was accepted')
assert local_reviews(source,{'string_0':'reviewTogether'},'method')[0]['Occurrences']==source['Bindings']
print('PASS distinct shadowed parameter selection, ambiguous/stale selector rejection and existing review preservation.')
