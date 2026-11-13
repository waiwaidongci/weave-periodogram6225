from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.models import SensitivityAnalysis
from src.schemas.sensitivity import SensitivityInput
from src.services.sensitivity import create_sensitivity
from src.utils.serialize import row
router=APIRouter()
@router.get('/sensitivity')
def analyses(db:Session=Depends(get_db),user=Depends(current_user)):return [{k:v for k,v in row(a).items() if k!='result'} for a in db.scalars(select(SensitivityAnalysis).order_by(SensitivityAnalysis.id.desc()))]
@router.get('/sensitivity/{id}')
def one(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
 analysis=db.get(SensitivityAnalysis,id)
 if not analysis:raise HTTPException(404,'留一敏感性分析不存在')
 return row(analysis)
@router.post('/sensitivity')
def create(data:SensitivityInput,db:Session=Depends(get_db),user=Depends(writers)):return create_sensitivity(db,data,user.email)
