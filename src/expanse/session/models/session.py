from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped

from expanse.database.orm import column
from expanse.database.orm.model import Model


class Session(Model):
    id: Mapped[str] = column(String(40), primary_key=True)
    payload: Mapped[str] = column(Text(), nullable=False)
    ip_address: Mapped[str] = column(String(45), nullable=True)
    user_agent: Mapped[str] = column(String(), nullable=True)
    last_activity: Mapped[datetime] = column(DateTime(timezone=True), nullable=False)
