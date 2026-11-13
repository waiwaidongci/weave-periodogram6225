from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,JSON,Text,DateTime
from datetime import datetime,timezone
from src.config.database import Base
class SensitivityAnalysis(Base):
 __tablename__='sensitivity_analyses'
 id:Mapped[int]=mapped_column(primary_key=True)
 run_id:Mapped[int]=mapped_column(ForeignKey('spectrum_runs.id'))
 name:Mapped[str]=mapped_column(String(180),unique=True)
 source_snapshot:Mapped[dict]=mapped_column(JSON)
 plan_snapshot:Mapped[dict]=mapped_column(JSON)
 baseline:Mapped[dict]=mapped_column(JSON)
 status:Mapped[str]=mapped_column(String(24),default='queued')
 result:Mapped[dict|None]=mapped_column(JSON,nullable=True)
 error:Mapped[str|None]=mapped_column(Text,nullable=True)
 completed_branches:Mapped[int|None]=mapped_column(nullable=True)
 degenerate_branches:Mapped[int|None]=mapped_column(nullable=True)
 created_by:Mapped[str]=mapped_column(String(120))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
