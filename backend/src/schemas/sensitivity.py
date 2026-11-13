from pydantic import BaseModel,Field
class SensitivityInput(BaseModel):
 run_id:int=Field(gt=0,strict=True)
 name:str=Field(min_length=2,max_length=180)
