import json
from pathlib import Path
from celery import Celery
from src.config.database import SessionLocal
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.models import SpectrumRun,SensitivityAnalysis
from src.services.analysis import analyze
from src.services.sensitivity import leave_one_out
from src.services.audit import record
app=Celery('weave_periodogram',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)
@app.task(name='weave.analyze',soft_time_limit=120,time_limit=150)
def analyze_run(id):
 with SessionLocal() as db:
  run=db.get(SpectrumRun,id)
  if not run or run.status=='completed':return
  run.status='running';db.commit()
  try:
   snapshot=run.source_snapshot;result=analyze(snapshot['study'],snapshot['points'],run.plan_snapshot)
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'weave-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False));run.result=result;run.peak_frequency=result['best']['frequency'];run.max_power=result['observed_max_power'];run.global_p=result['global_test']['global_p'];run.status='completed';run.error=None;db.commit();record(db,'worker','run.completed',{'run_id':id,'global_p':run.global_p})
  except Exception as error:
   db.rollback();run=db.get(SpectrumRun,id);run.status='failed';run.error=str(error)[:1000];db.commit();record(db,'worker','run.failed',{'run_id':id,'error':run.error})
@app.task(name='weave.sensitivity',soft_time_limit=600,time_limit=660)
def analyze_sensitivity(id):
 with SessionLocal() as db:
  analysis=db.get(SensitivityAnalysis,id)
  if not analysis or analysis.status=='completed':return
  analysis.status='running';db.commit()
  try:
   snapshot=analysis.source_snapshot;result=leave_one_out(snapshot['study'],snapshot['points'],analysis.plan_snapshot,analysis.baseline)
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'sensitivity-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False));analysis.result=result;analysis.completed_branches=result['completed_branches'];analysis.degenerate_branches=result['degenerate_branches'];analysis.status='completed';analysis.error=None;db.commit();record(db,'worker','sensitivity.completed',{'sensitivity_id':id,'completed':result['completed_branches'],'degenerate':result['degenerate_branches']})
  except Exception as error:
   db.rollback();analysis=db.get(SensitivityAnalysis,id);analysis.status='failed';analysis.error=str(error)[:1000];db.commit();record(db,'worker','sensitivity.failed',{'sensitivity_id':id,'error':analysis.error})
