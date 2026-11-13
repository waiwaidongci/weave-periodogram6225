import copy
from sqlalchemy import select
from fastapi import HTTPException
from src.models import SpectrumRun,SensitivityAnalysis
from src.utils.serialize import row
from .validation import validate_points,validate_plan
from .qr_cache import build_cache
from .spectrum import observed_spectrum
from .permutation import global_permutation
from .fingerprint import fingerprint
from .audit import record

def leave_one_out(study,points,plan,baseline):
 points=validate_points(points);frequencies=validate_plan(plan);branches=[]
 for removed in points:
  branch={'reference':removed['reference'],'position':removed['position']}
  try:
   subset=validate_points([p for p in points if p['reference']!=removed['reference']])
   cache=build_cache([p['position'] for p in subset],frequencies)
   observed,centered=observed_spectrum(cache,[p['thickness'] for p in subset])
   test=global_permutation(cache,centered,observed['rss0'],observed['observed_max_power'],plan['permutations'],plan['seed'])
   branch.update(status='completed',reason=None,n=len(subset),best=observed['best'],observed_max_power=observed['observed_max_power'],global_test=test,included_frequencies=observed['included_frequencies'],excluded_frequencies=observed['excluded_frequencies'],delta={'period':observed['best']['period']-baseline['period'],'power':observed['observed_max_power']-baseline['power'],'global_p':test['global_p']-baseline['global_p']})
  except Exception as error:
   branch.update(status='degenerate',reason=str(error))
  branches.append(branch)
 completed=[b for b in branches if b['status']=='completed']
 return {'kind':'leave-one-out-sensitivity','source_study':study,'plan':plan,'n':len(points),'baseline':baseline,'branches':branches,'completed_branches':len(completed),'degenerate_branches':len(branches)-len(completed),'qr_cache_builds':len(completed),'fingerprint':fingerprint(study,points,plan),'tie_rule':'lowest frequency within absolute power tolerance 1e-12 of maximum; upper-tail null ties use same tolerance','interpretation':'Leave-one-out refit of the frozen grid and frozen permutation plan; each branch drops exactly one point from the queued snapshot and keeps its complete null maxima. Degenerate branches keep their reason. Source edits after queueing do not affect this analysis; the parent run and notes are not rewritten.'}

def create_sensitivity(db,data,actor):
 run=db.get(SpectrumRun,data.run_id)
 if not run or run.status!='completed' or not run.result:raise HTTPException(422,'仅已完成谱研究可发起留一敏感性分析')
 try:validate_points(run.source_snapshot['points']);validate_plan(run.plan_snapshot)
 except ValueError as error:raise HTTPException(422,str(error))
 if db.scalar(select(SensitivityAnalysis).where(SensitivityAnalysis.name==data.name)):raise HTTPException(409,'分析名已存在')
 result=run.result;baseline={'frequency':result['best']['frequency'],'period':result['best']['period'],'power':result['observed_max_power'],'global_p':result['global_test']['global_p'],'n':result['n']}
 analysis=SensitivityAnalysis(run_id=run.id,name=data.name,source_snapshot=copy.deepcopy(run.source_snapshot),plan_snapshot=copy.deepcopy(run.plan_snapshot),baseline=baseline,created_by=actor);db.add(analysis);db.commit()
 try:
  from src.worker import analyze_sensitivity
  analyze_sensitivity.delay(analysis.id)
 except Exception:
  analysis.status='failed';analysis.error='队列不可用，请稍后重建';db.commit();raise HTTPException(503,analysis.error)
 record(db,actor,'sensitivity.queued',{'sensitivity_id':analysis.id,'run_id':run.id});return row(analysis)
