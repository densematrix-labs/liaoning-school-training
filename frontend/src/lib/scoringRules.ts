export function normalizeScoring(steps:any[], rules:any={}) {
 const converted=steps.map(s=>{
  const factor=rules.scoring_mode==='proportional'?Number(rules.total_score||100)*Number(s.weight||0)/100:!rules.scoring_mode?Number(s.weight??1):1
  const score=rules.scoring_mode==='proportional'?factor:Number(s.score||0)*factor
  const failed=rules.scoring_mode==='proportional'?score*Number(s.failed_ratio||0):Number(s.failed_score||0)*factor
  const {weight,failed_ratio,...rest}=s
  return {...rest,score,failed_score:failed}
 })
 const {total_score,decay,time_decay,...rest}=rules
 return {steps:converted,rules:{...rest,scoring_mode:'absolute'}}
}
