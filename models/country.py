import sqlalchemy
from sqlalchemy import Column
from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import ARRAY

from infrastructure.db import Base

metadata = sqlalchemy.MetaData()


class Country(Base):  # type: ignore
    __tablename__ = "countries"

    ISO3 = Column("ISO3", String, primary_key=True)
    Country = Column("Country", String)
    Regions = Column("Regions", String)
    Crises = Column("Crises", String)
    Analysts = Column("Analysts", ARRAY(String))  # type: ignore
    DataCollector = Column("DataCollector", ARRAY(String))  # type: ignore
    Email = Column("Email", String)
    Priority = Column("Priority", Boolean)
    AnalystAccount = Column("AnalystAccount", String)
    DataCollectorAccount = Column("DataCollectorAccount", String)
