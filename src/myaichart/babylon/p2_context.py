def shadow_decision(context: dict) -> dict:
    if not context:
        return {'decision':'OBSERVE','reasons':['NO_CONTEXT']}
    if context.get('valid') is False:
        return {'decision':'BLOCK','reasons':[context.get('reason','CONTEXT_INVALID')]}
    if context.get('conflict'):
        return {'decision':'OBSERVE','reasons':['CONFLICT']}
    return {'decision':'ALLOW','reasons':[]}
