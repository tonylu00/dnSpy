"""Parameter dependency ordering, execution and validation, reviewed from leaves.

Names describe observed behavior. In particular, cycle detection logs an error
and returns the ordered portion; missing scripts and unimplemented engines are
not silently described as successful validation or repaired by this recipe.
"""

def review(add):
    project='Knx.Ets.CalculatedParameters'
    def record(token,name,reason,parameters=(),locals_=None,status='reviewed'):
        add(project,token,name,reason,parameters,locals_,status)

    # Identity predicates and node access precede graph traversal callers.
    record(0x060000CF,'MatchesCalculationParameterReferenceId','Compares a binding parameter-reference ID to the captured ID; used to find the left-hand calculation input.',('binding',))
    record(0x060000CD,'GetDirectionForChangedParameter','Returns LR when the changed parameter reference appears among left parameters, otherwise RL; no separate right-side membership check.',('changedParameter',),{'a':'parameterMatch'})
    record(0x060000EC,'GetParameterReference','Returns the parameter-reference facade carried by a dependency node.')
    record(0x060000DF,'GetOrderedCalculationSteps','Returns the calculation-node array stored in the ordered chain.')
    record(0x060000E3,'FormatCalculationStep','Calls the step ToString representation used by the chain description.',('step',))
    record(0x060000FE,'MatchesValidationTargetParameter','Tests reference identity against the parameter currently being validated.',('binding',))
    record(0x06000100,'IsDependencyParameterInLeftBinding','Tests binding parameter reference identity against the dependency node; used in LParameters.Any.',('binding',))
    record(0x06000101,'IsDependencyParameterInRightBinding','Tests the same reference identity in RParameters.Any, establishing the reverse calculation direction.',('binding',))
    for token,name,reason,parameters in [
        (0x060000EF,'EnumerateCalculationParameterBindings','Returns the union of left and right parameter bindings for the calculation lookup.',('calculation',)),
        (0x060000F0,'PairCalculationWithParameterReference','Pairs the calculation with the binding parameter reference.',('calculation','binding')),
        (0x060000F1,'SelectCalculationLookupParameter','Returns the parameter-reference key from a calculation/reference pair.',('entry',)),
        (0x060000F2,'SelectCalculationLookupValue','Returns the calculation value from that pair.',('entry',)),
        (0x060000F3,'EnumerateValidationParameterBindings','Returns validation parameter bindings for the validation lookup.',('validation',)),
        (0x060000F4,'PairValidationWithParameterReference','Pairs the validation with the binding parameter reference.',('validation','binding')),
        (0x060000F5,'SelectValidationLookupParameter','Returns the parameter-reference key from a validation/reference pair.',('entry',)),
        (0x060000F6,'SelectValidationLookupValue','Returns the validation value from that pair.',('entry',)),
        (0x060000F7,'SelectCalculationModuleForModuleId','Returns Calculation.ModuleDef for the module-definition ID projection.',('step',)),
        (0x060000F8,'HasCalculationModuleForModuleId','Rejects null module facades in the module-definition ID projection.',('moduleDefinition',)),
        (0x060000F9,'SelectCalculationModuleDefinitionId','Returns ModuleDefinitionId from the retained module facade.',('moduleDefinition',)),
        (0x060000FA,'SelectCalculationModuleForSubmoduleId','Returns Calculation.ModuleDef for the separate submodule-definition ID projection.',('step',)),
        (0x060000FB,'HasCalculationModuleForSubmoduleId','Rejects null module facades in the submodule-definition ID projection.',('moduleDefinition',)),
        (0x060000FC,'SelectCalculationSubmoduleDefinitionId','Returns SubmoduleDefinitionId from the retained module facade.',('moduleDefinition',))]:
        record(token,name,reason,parameters)

    record(0x060000DB,'AddDependentCalculationNodes','Finds calculations consuming the parameter, chooses LR/RL from membership, links parameter to calculation and recursively expands newly encountered calculations. Conflicting directions for an existing node are skipped.',
           ('parameterNode','calculationNodes','parameterNodes','rootParameter'),
           {'class':'dependencyMatch','enumerator':'calculationEnumerator','t':'calculation','parameterCalculationDirection':'direction','flag':'isNewCalculation','c':'calculationNode'})
    record(0x060000DC,'AddCalculationOutputParameterNodes','Links a calculation to parameters on its output side, creates missing nodes and recursively expands dependencies from newly seen output parameters.',
           ('calculationNode','calculationNodes','parameterNodes','rootParameter'),
           {'g':'outputBinding','flag':'isNewParameter','d':'parameterNode'})
    record(0x060000DA,'BuildOrderedCalculationChain','Builds alternating parameter/calculation nodes, then removes predecessor edges while ordering reachable nodes. Cycles are logged; the ordered calculation portion is returned, and an unreferenced starting parameter returns null.',
           ('changedParameter',),{'dictionary':'calculationNodes','dictionary2':'parameterNodes','d':'startingNode','list':'readyNodes','list2':'orderedNodes','hashSet':'visitedNodes','b':'currentNode','b2':'successor'})
    record(0x060000D4,'GetOrBuildCalculationChain','For a parameter present in the calculation lookup, reuses or builds its chain under the shared lock. Returns null when no calculations reference it.',
           ('changedParameter',),{'obj':'syncRoot','a':'chain'})
    record(0x060000D5,'GetCalculationModuleDefinitionIds','Concatenates distinct module-definition IDs and distinct submodule-definition IDs from non-null calculation module facades.',
           ('chain',),{'enumerable':'moduleDefinitionIds','enumerable2':'submoduleDefinitionIds'})
    record(0x060000D6,'ExecuteCalculationChain','Runs ordered calculations under the shared lock. Clones each definition for the current device and uses a static script function or a new inline engine according to its transformation fields. Logs and rethrows inline execution failures.',
           ('chain','device','moduleInstanceId'),{'obj':'syncRoot','c':'step','t':'functionCalculation','t2':'inlineCalculation','z':'scriptEngine','ex':'scriptException','d':'errorSeverity','text':'diagnosticCategory','parameterCalculationId':'calculationId'})
    record(0x060000D7,'ValidateParameterChange','Finds validations for the changed parameter, clones each for the current device and invokes its script with the proposed value. Stops on the first false result. A missing static script logs and exits the loop; the existing true result remains.',
           ('device','changedParameter','moduleInstanceId','proposedValue','validationMessage'),
           {'e':'validationTarget','enumerable':'validations','obj':'syncRoot','enumerator':'validationEnumerator','x':'definition','x2':'deviceValidation','g':'targetBinding'})
    record(0x060000D8,'ExecuteDeviceEventHandler','Serializes a static-script event call. Exact SDK caller Knx.Ets.Sdk.Project.Device.ExecuteEventHandler supplies the device facade, management facade and asynchronous progress object; absent static script only logs.',
           ('eventHandlerName','argumentTemplate','deviceFacade','deviceManagement','asyncProgress','moduleInstanceId'),{'obj':'syncRoot'})

    for token,name,reason in [
        (0x0200001B,'CalculationParameterIdMatch','Captures a changed parameter-reference ID for calculation-direction selection.'),
        (0x0200001D,'ParameterCalculationCoordinator','Indexes calculation/validation definitions, caches ordered dependency chains, and serializes script execution and parameter-change validation.'),
        (0x0200001E,'ParameterCalculationChain','Holds calculation nodes in execution order and formats the chain description.'),
        (0x0200001F,'CalculationChainFormattingCallbacks','Cached selector for formatting each ordered step.'),
        (0x02000020,'CalculationDependencyNode','Base graph node with mutable predecessor and successor lists.'),
        (0x02000021,'DirectedCalculationNode','Graph node carrying a calculation definition and LR/RL direction.'),
        (0x02000022,'CalculationParameterNode','Graph node carrying a parameter-reference facade.'),
        (0x02000023,'CalculationLookupCallbacks','Stateless lookup, module-ID and submodule-ID selectors.'),
        (0x02000024,'ValidationTargetParameterMatch','Captures the parameter being validated and its binding predicate.'),
        (0x02000025,'CalculationDependencyParameterMatch','Captures a dependency parameter node and left/right membership predicates.')]:
        record(token,name,reason)
    for token,name,reason in [
        (0x0400003F,'language','Calculation.Language backing value.'),
        (0x04000040,'calculationId','Calculation.Id backing value.'),
        (0x04000041,'applicationProgram','Calculation.ApplicationProgram context.'),
        (0x04000042,'moduleDefinition','Calculation.ModuleDef context.'),
        (0x04000043,'device','Calculation.Device context.'),
        (0x04000044,'name','Calculation.Name backing text.'),
        (0x04000045,'leftToRightScriptSource','LRTransformation inline source.'),
        (0x04000046,'rightToLeftScriptSource','RLTransformation inline source.'),
        (0x04000047,'leftToRightFunctionName','LRTransformationFunc function name.'),
        (0x04000048,'rightToLeftFunctionName','RLTransformationFunc function name.'),
        (0x04000049,'leftToRightArgumentTemplate','LRTransformationParameters text expanded before JSON parsing.'),
        (0x0400004A,'rightToLeftArgumentTemplate','RLTransformationParameters text expanded before JSON parsing.'),
        (0x0400004B,'leftParameterBindings','LParameters list.'),
        (0x0400004C,'rightParameterBindings','RParameters list.'),
        (0x0400004E,'parameterReferenceId','Captured ID compared by calculation-direction predicate.'),
        (0x04000051,'logger','Coordinator calculation-chain and missing-script logger.'),
        (0x04000052,'calculationsByParameter','Calculation lookup keyed by referenced parameter facade.'),
        (0x04000053,'cachedCalculationChains','Per-parameter ordered chain cache.'),
        (0x04000054,'validationsByParameter','Validation lookup keyed by referenced parameter facade.'),
        (0x04000055,'staticScriptEngine','Engine created from the application static JavaScript source.'),
        (0x04000056,'executionSyncRoot','Lock shared by chain caching and static/inline script operations.'),
        (0x04000058,'orderedSteps','Calculation-node array returned by the chain getter.'),
        (0x0400005A,'sharedCallbacks','Singleton step-formatting callbacks.'),
        (0x0400005B,'formatStep','Cached step-to-description selector.'),
        (0x0400005D,'successors','Dependency-node outgoing edges.'),
        (0x0400005E,'predecessors','Dependency-node incoming edges removed by topological ordering.'),
        (0x04000060,'calculation','Definition carried by a directed calculation node.'),
        (0x04000061,'direction','LR/RL direction carried by a directed calculation node.'),
        (0x04000063,'parameterReference','Parameter facade carried by a dependency node.'),
        (0x04000065,'sharedCallbacks','Singleton coordinator lookup and module selectors.'),
        (0x04000075,'targetParameter','Captured validation target facade.'),
        (0x04000076,'matchesTargetParameter','Cached validation target identity predicate.'),
        (0x04000078,'parameterNode','Captured dependency node used for left/right membership.'),
        (0x04000079,'matchesLeftBinding','Cached LParameters membership predicate.'),
        (0x0400007A,'matchesRightBinding','Cached RParameters membership predicate.'),
        (0x0400007D,'applicationProgram','Validation.ApplicationProgram context.'),
        (0x0400007E,'moduleDefinition','Validation.ModuleDef context.'),
        (0x0400007F,'device','Validation.Device context.'),
        (0x04000080,'validationId','Validation.Id backing value.'),
        (0x04000081,'name','Validation.Name backing text.'),
        (0x04000082,'functionName','ValidationFunc invoked by the engine.'),
        (0x04000083,'argumentTemplate','ValidationParameters text expanded before JSON parsing.'),
        (0x04000084,'parameterBindings','Parameters used to construct the proposed script values.')]:
        record(token,name,reason)
    for offset,name in enumerate([
        'enumerateCalculationBindings','pairCalculationWithParameter','selectCalculationParameter','selectCalculation',
        'enumerateValidationBindings','pairValidationWithParameter','selectValidationParameter','selectValidation',
        'selectModuleForModuleId','hasModuleForModuleId','selectModuleDefinitionId',
        'selectModuleForSubmoduleId','hasModuleForSubmoduleId','selectSubmoduleDefinitionId']):
        record(0x04000066+offset,name,'Cached delegate for the corresponding reviewed calculation/validation lookup or module-ID projection.')

    # Constructors keep their CLR names. Their formal parameter proposals must
    # remain visible while constructor parameter-only mapping is unsupported.
    for token,parameters in [
        (0x060000CA,('language','calculationId','name','leftToRightScriptSource','rightToLeftScriptSource','applicationProgram','moduleDefinition','device')),
        (0x060000CB,('calculationId','name','leftToRightFunctionName','rightToLeftFunctionName','leftToRightArgumentTemplate','rightToLeftArgumentTemplate','applicationProgram','moduleDefinition','device')),
        (0x0600010C,('validationId','name','functionName','argumentTemplate','applicationProgram','moduleDefinition','device')),
        (0x060000D2,('calculations',)),
        (0x060000D3,('calculations','validations','staticScriptSource')),
        (0x060000DE,('orderedSteps',)),
        (0x060000E7,('calculation','direction')),
        (0x060000EB,('parameterReference',))]:
        record(token,None,'Constructor argument roles verified from assignments and reviewed callers; preserve the constructor name.',parameters,status='retain-constructor-name')
