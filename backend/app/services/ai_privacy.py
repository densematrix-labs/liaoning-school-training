"""Allowlisted report inputs with recursive removal of local identity values."""
def report_payload(scores,abilities,environment,facts,report_type,identifiers=()):
    score_fields={'project_name','completed_at','total_score','max_score','percentage','failed_abilities','steps'}
    step_fields={'step_name','passed','score','max_score','reason'}
    ability_fields={'name','score','threshold','range_first_score','range_change'}
    environment_fields={'total_score','summary','review_status','details','suggestions'}
    records=[]
    for row in scores:
        clean={k:v for k,v in row.items() if k in score_fields}
        clean['steps']=[{k:v for k,v in step.items() if k in step_fields} for step in row.get('steps',[])]
        records.append(clean)
    raw={'scores':records,'abilities':[{k:v for k,v in row.items() if k in ability_fields} for row in abilities],
         'environment':[{k:v for k,v in row.items() if k in environment_fields} for row in environment], 'facts':facts,'type':report_type}
    markers=sorted({str(v) for v in identifiers if v},key=len,reverse=True)
    def redact(v):
        if isinstance(v,str):
            for marker in markers:v=v.replace(marker,'[已去标识]')
            return v
        if isinstance(v,list):return [redact(x) for x in v]
        if isinstance(v,dict):return {k:redact(x) for k,x in v.items()}
        return v
    return redact(raw)
